"""
Async Upload Router for XLR8 - v2 with Smart PDF Processing
============================================================

FEATURES:
- Returns immediately after file save (no timeout!)
- Processes in background thread
- Real-time status updates via job polling
- Handles large files gracefully
- Smart Excel parsing (detects blue/colored headers)
- **NEW: Smart PDF table detection → DuckDB for SQL queries**

CHANGES FROM v1:
- Added smart_process_pdf_file() for tabular PDFs
- PDFs with tables go to BOTH DuckDB (structured) AND ChromaDB (semantic)
- Always shows status - no silent processing

Author: XLR8 Team
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from typing import Optional
from datetime import datetime
import sys
import os
import json
import threading
import traceback
import PyPDF2
import docx
import pandas as pd
import logging
import tempfile

# Try to import openpyxl for smart Excel parsing
try:
    from openpyxl import load_workbook
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False
    logger_temp = logging.getLogger(__name__)
    logger_temp.warning("openpyxl not available - Excel color detection disabled")

sys.path.insert(0, '/app')
sys.path.insert(0, '/data')

from utils.rag_handler import RAGHandler
from utils.database.models import ProcessingJobModel, DocumentModel, ProjectModel

# Import structured data handler for Excel/CSV
try:
    from utils.structured_data_handler import get_structured_handler
    STRUCTURED_HANDLER_AVAILABLE = True
except ImportError:
    STRUCTURED_HANDLER_AVAILABLE = False
    logger_temp = logging.getLogger(__name__)
    logger_temp.warning("Structured data handler not available - Excel/CSV will use RAG only")

# NEW: Import smart PDF analyzer
try:
    from utils.smart_pdf_analyzer import SmartPDFAnalyzer, smart_process_pdf
    SMART_PDF_AVAILABLE = True
except ImportError:
    SMART_PDF_AVAILABLE = False
    # Will be created as part of this deployment

# Import pdfplumber for table extraction
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# SMART PDF TABLE EXTRACTION - NEW
# =============================================================================

def analyze_pdf_for_tables(file_path: str) -> dict:
    """
    Analyze a PDF to detect if it contains tables.
    
    Returns:
        {
            'has_tables': bool,
            'table_ratio': float (0-1),
            'tables': [DataFrame, ...],
            'combined_table': DataFrame or None,
            'text_content': str,
            'recommendation': 'duckdb' | 'chromadb' | 'both'
        }
    """
    if not PDFPLUMBER_AVAILABLE:
        logger.warning("[SMART-PDF] pdfplumber not available, skipping table detection")
        return {'has_tables': False, 'recommendation': 'chromadb'}
    
    try:
        logger.info(f"[SMART-PDF] Analyzing PDF for tables: {file_path}")
        
        with pdfplumber.open(file_path) as pdf:
            total_pages = len(pdf.pages)
            if total_pages == 0:
                return {'has_tables': False, 'recommendation': 'chromadb'}
            
            all_tables = []
            table_pages = []
            all_text = []
            column_signatures = []
            
            for page_num, page in enumerate(pdf.pages, start=1):
                # Extract tables
                tables = page.extract_tables()
                
                if tables:
                    for table in tables:
                        if table and len(table) > 1:  # Has header + data
                            try:
                                # Clean up table
                                headers = [str(h).strip() if h else f'Col_{i}' for i, h in enumerate(table[0])]
                                data = table[1:]
                                
                                df = pd.DataFrame(data, columns=headers)
                                df = df.dropna(how='all')
                                
                                # Remove duplicate header rows
                                header_as_list = [str(h).lower().strip() for h in headers]
                                mask = df.apply(lambda row: [str(v).lower().strip() if v else '' for v in row] != header_as_list, axis=1)
                                df = df[mask]
                                
                                if len(df) > 0:
                                    all_tables.append(df)
                                    table_pages.append(page_num)
                                    column_signatures.append(tuple(headers))
                            except Exception as e:
                                logger.debug(f"[SMART-PDF] Table parse error on page {page_num}: {e}")
                
                # Extract text
                text = page.extract_text() or ''
                if text.strip():
                    all_text.append(f"--- Page {page_num} ---\n{text}")
            
            # Calculate metrics
            table_ratio = len(table_pages) / total_pages if total_pages > 0 else 0
            
            # Check column consistency (same table structure across pages)
            column_consistent = len(set(column_signatures)) == 1 if column_signatures else False
            
            # Try to combine tables if consistent structure
            combined_table = None
            if all_tables and column_consistent:
                try:
                    combined_table = pd.concat(all_tables, ignore_index=True)
                    logger.info(f"[SMART-PDF] Combined {len(all_tables)} tables → {len(combined_table)} rows")
                except Exception as e:
                    logger.warning(f"[SMART-PDF] Could not combine tables: {e}")
            
            # Determine recommendation
            if table_ratio > 0.5 or (table_ratio > 0.3 and column_consistent):
                recommendation = 'duckdb'  # Primarily tabular
            elif table_ratio > 0.1:
                recommendation = 'both'    # Mixed content
            else:
                recommendation = 'chromadb'  # Primarily text
            
            result = {
                'has_tables': len(all_tables) > 0,
                'table_ratio': table_ratio,
                'table_pages': table_pages,
                'tables': all_tables,
                'combined_table': combined_table,
                'text_content': '\n\n'.join(all_text),
                'total_rows': len(combined_table) if combined_table is not None else sum(len(t) for t in all_tables),
                'recommendation': recommendation,
                'column_consistent': column_consistent
            }
            
            logger.info(f"[SMART-PDF] Analysis: {len(all_tables)} tables, {result['total_rows']} rows, recommendation={recommendation}")
            
            return result
            
    except Exception as e:
        logger.error(f"[SMART-PDF] Analysis failed: {e}")
        return {'has_tables': False, 'recommendation': 'chromadb', 'error': str(e)}


def store_pdf_tables_to_duckdb(
    tables: list,
    combined_table,  # DataFrame or None
    project: str,
    filename: str,
    job_id: str
) -> dict:
    """
    Store extracted PDF tables in DuckDB.
    Uses temp CSV file since store_csv expects file path.
    """
    if not STRUCTURED_HANDLER_AVAILABLE:
        return {'success': False, 'error': 'DuckDB handler not available'}
    
    try:
        handler = get_structured_handler()
        
        # Use combined table if available
        df = combined_table if combined_table is not None else (tables[0] if tables else None)
        
        if df is None or len(df) == 0:
            return {'success': False, 'error': 'No table data to store'}
        
        ProcessingJobModel.update_progress(job_id, 40, f"Storing {len(df)} rows in DuckDB...")
        
        # Clean column names
        df.columns = [str(c).strip().replace(' ', '_').replace('-', '_')[:50] for c in df.columns]
        
        # Convert all to string (safer for mixed types)
        for col in df.columns:
            df[col] = df[col].fillna('').astype(str)
        
        # Save to temp CSV
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            temp_path = f.name
            df.to_csv(f, index=False)
        
        try:
            # Use existing store_csv method
            result = handler.store_csv(temp_path, project, filename.replace('.pdf', '_table'))
            
            ProcessingJobModel.update_progress(job_id, 50, f"✓ Stored {len(df)} rows as '{result.get('table_name', 'table')}'")
            
            return {
                'success': True,
                'tables_created': [result.get('table_name')],
                'total_rows': len(df),
                'columns': list(df.columns)
            }
        finally:
            # Cleanup temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
    except Exception as e:
        logger.error(f"[SMART-PDF] DuckDB storage failed: {e}")
        return {'success': False, 'error': str(e)}


# =============================================================================
# EXISTING TEXT EXTRACTION (unchanged)
# =============================================================================

def extract_text(file_path: str) -> str:
    """Extract text from file based on extension"""
    ext = file_path.split('.')[-1].lower()
    
    try:
        if ext == 'pdf':
            # ENHANCED PDF EXTRACTION - try multiple methods
            text = ""
            pages_extracted = 0
            
            # Method 1: Try pdfplumber first (best for tables and structured PDFs)
            try:
                import pdfplumber
                logger.info("[PDF] Trying pdfplumber extraction...")
                with pdfplumber.open(file_path) as pdf:
                    page_texts = []
                    for i, page in enumerate(pdf.pages):
                        page_text = page.extract_text() or ''
                        if page_text.strip():
                            page_texts.append(f"--- Page {i+1} ---\n{page_text}")
                            pages_extracted += 1
                    text = "\n\n".join(page_texts)
                    logger.info(f"[PDF] pdfplumber extracted {pages_extracted} pages, {len(text)} chars")
            except Exception as e:
                logger.warning(f"[PDF] pdfplumber failed: {e}")
            
            # Method 2: If pdfplumber got little/no content, try PyMuPDF
            if len(text) < 500:
                try:
                    import fitz  # PyMuPDF
                    logger.info("[PDF] Trying PyMuPDF extraction...")
                    doc = fitz.open(file_path)
                    page_texts = []
                    for i, page in enumerate(doc):
                        page_text = page.get_text()
                        if page_text.strip():
                            page_texts.append(f"--- Page {i+1} ---\n{page_text}")
                            pages_extracted += 1
                    doc.close()
                    fitz_text = "\n\n".join(page_texts)
                    if len(fitz_text) > len(text):
                        text = fitz_text
                        logger.info(f"[PDF] PyMuPDF extracted {pages_extracted} pages, {len(text)} chars")
                except Exception as e:
                    logger.warning(f"[PDF] PyMuPDF failed: {e}")
            
            # Method 3: Fall back to PyPDF2
            if len(text) < 500:
                try:
                    logger.info("[PDF] Falling back to PyPDF2...")
                    with open(file_path, 'rb') as f:
                        reader = PyPDF2.PdfReader(f)
                        page_texts = []
                        for i, page in enumerate(reader.pages):
                            page_text = page.extract_text() or ''
                            if page_text.strip():
                                page_texts.append(f"--- Page {i+1} ---\n{page_text}")
                                pages_extracted += 1
                        pypdf_text = "\n\n".join(page_texts)
                        if len(pypdf_text) > len(text):
                            text = pypdf_text
                            logger.info(f"[PDF] PyPDF2 extracted {pages_extracted} pages, {len(text)} chars")
                except Exception as e:
                    logger.warning(f"[PDF] PyPDF2 failed: {e}")
            
            return text
        
        elif ext in ['xlsx', 'xls']:
            # Smart Excel extraction with colored header detection
            texts = []
            
            if not OPENPYXL_AVAILABLE:
                # Fall back to pandas
                excel = pd.ExcelFile(file_path)
                for sheet in excel.sheet_names:
                    try:
                        df = pd.read_excel(file_path, sheet_name=sheet, header=1)
                        df = df.dropna(how='all')
                        texts.append(f"[SHEET: {sheet}]\n{df.to_string()}")
                    except:
                        texts.append(f"[SHEET: {sheet}]\nError reading sheet\n")
                return "\n\n".join(texts)
            
            try:
                wb = load_workbook(file_path, data_only=True)
                
                for sheet_name in wb.sheetnames:
                    ws = wb[sheet_name]
                    sheet_texts = [f"[SHEET: {sheet_name}]"]
                    
                    if ws.max_row is None or ws.max_row < 1:
                        texts.append(f"[SHEET: {sheet_name}]\nEmpty Sheet\n")
                        continue
                    
                    # Find header rows by looking for colored cells
                    header_rows = []
                    for row_idx, row in enumerate(ws.iter_rows(min_row=1, max_row=min(20, ws.max_row)), start=1):
                        colored_cell_count = 0
                        non_empty_count = 0
                        
                        for cell in row[:20]:  # Check first 20 columns
                            if cell.value and str(cell.value).strip():
                                non_empty_count += 1
                            if cell.fill and cell.fill.fgColor:
                                color = cell.fill.fgColor
                                if hasattr(color, 'rgb') and color.rgb and color.rgb != '00000000':
                                    colored_cell_count += 1
                        
                        if colored_cell_count >= 3 and non_empty_count >= 3:
                            header_rows.append(row_idx)
                            logger.info(f"[EXCEL] Found header row at {row_idx} ({colored_cell_count} colored cells)")
                    
                    # If no colored headers, use first row with data
                    if not header_rows:
                        for row_idx, row in enumerate(ws.iter_rows(min_row=1, max_row=10), start=1):
                            non_empty = sum(1 for cell in row[:20] if cell.value and str(cell.value).strip())
                            if non_empty >= 3:
                                header_rows.append(row_idx)
                                break
                    
                    if not header_rows:
                        texts.append(f"[SHEET: {sheet_name}]\nNo Data Available\n")
                        continue
                    
                    # Process each section
                    for section_idx, header_row in enumerate(header_rows):
                        if section_idx + 1 < len(header_rows):
                            end_row = header_rows[section_idx + 1] - 1
                        else:
                            end_row = ws.max_row
                        
                        headers = []
                        for cell in ws[header_row]:
                            val = str(cell.value).strip() if cell.value else ''
                            if val and val.lower() not in ['none', 'nan']:
                                headers.append(val)
                            elif cell.column <= 20:
                                headers.append(f"Col{cell.column}")
                        
                        while headers and (headers[-1].startswith('Col') or not headers[-1]):
                            headers.pop()
                        
                        if not headers:
                            continue
                        
                        sheet_texts.append(f"Columns: {' | '.join(headers)}")
                        
                        data_row_count = 0
                        for row_idx in range(header_row + 1, min(end_row + 1, header_row + 1000)):
                            row_data = []
                            has_data = False
                            
                            for col_idx, header in enumerate(headers, start=1):
                                cell = ws.cell(row=row_idx, column=col_idx)
                                val = cell.value
                                
                                if val is not None:
                                    val_str = str(val).strip()
                                    if val_str and val_str.lower() not in ['none', 'nan', '']:
                                        has_data = True
                                        row_data.append(f"{header}: {val_str}")
                            
                            if has_data and row_data:
                                sheet_texts.append(" | ".join(row_data))
                                data_row_count += 1
                    
                    if len(sheet_texts) > 2:
                        texts.append("\n".join(sheet_texts))
                    else:
                        texts.append(f"[SHEET: {sheet_name}]\nNo Data Available\n")
                
                wb.close()
                
            except Exception as e:
                logger.error(f"[EXCEL] openpyxl error: {e}, falling back to pandas")
                excel = pd.ExcelFile(file_path)
                texts = []
                for sheet in excel.sheet_names:
                    try:
                        df = pd.read_excel(file_path, sheet_name=sheet, header=1)
                        df = df.dropna(how='all')
                        texts.append(f"[SHEET: {sheet}]\n{df.to_string()}")
                    except:
                        texts.append(f"[SHEET: {sheet}]\nError reading sheet\n")
            
            return "\n\n".join(texts)
        
        elif ext == 'csv':
            df = pd.read_csv(file_path)
            return f"WORKSHEET: CSV Data\n{'=' * 40}\n{df.to_string()}"
        
        elif ext in ['txt', 'md']:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        
        elif ext in ['doc', 'docx']:
            doc = docx.Document(file_path)
            return '\n'.join([para.text for para in doc.paragraphs])
        
        else:
            # Try as text
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
                
    except Exception as e:
        logger.error(f"Text extraction failed for {file_path}: {e}")
        raise


# =============================================================================
# BACKGROUND PROCESSING (UPDATED with smart PDF handling)
# =============================================================================

def process_file_background(
    job_id: str,
    file_path: str,
    filename: str,
    project: str,
    project_id: Optional[str],
    functional_area: Optional[str],
    file_size: int
):
    """
    Background processing function - runs in separate thread
    
    This is where all the heavy lifting happens:
    1. For Excel/CSV: Store in DuckDB (structured queries)
    2. For PDFs with tables: Store tables in DuckDB + text in ChromaDB
    3. For PDFs/Docs without tables: Extract text, chunk, embed in ChromaDB
    4. Update job status throughout - NEVER silent
    """
    try:
        logger.info(f"[BACKGROUND] Starting processing for job {job_id}")
        logger.info(f"[BACKGROUND] project={project}, project_id={project_id}")
        
        file_ext = filename.split('.')[-1].lower()
        
        # =====================================================================
        # ROUTE 1: STRUCTURED DATA (Excel/CSV) → DuckDB
        # =====================================================================
        if file_ext in ['xlsx', 'xls', 'csv'] and STRUCTURED_HANDLER_AVAILABLE:
            ProcessingJobModel.update_progress(job_id, 10, "Detected tabular data - storing for SQL queries...")
            
            try:
                handler = get_structured_handler()
                
                ProcessingJobModel.update_progress(job_id, 20, "Parsing spreadsheet structure...")
                
                if file_ext == 'csv':
                    result = handler.store_csv(file_path, project, filename)
                    tables_created = 1
                    total_rows = result.get('row_count', 0)
                else:
                    result = handler.store_excel(file_path, project, filename)
                    tables_created = result.get('sheets_processed', 1)
                    total_rows = result.get('total_rows', 0)
                
                ProcessingJobModel.update_progress(
                    job_id, 80,
                    f"Created {tables_created} table(s) with {total_rows:,} total rows"
                )
                
                # Save metadata
                if project_id:
                    try:
                        DocumentModel.create(
                            project_id=project_id,
                            name=filename,
                            category=functional_area or 'Data',
                            file_type=file_ext,
                            file_size=file_size,
                            content=f"Structured data: {tables_created} tables, {total_rows} rows",
                            metadata={
                                'storage': 'duckdb',
                                'tables_created': result.get('tables_created', []),
                                'total_rows': total_rows
                            }
                        )
                    except Exception as e:
                        logger.warning(f"[BACKGROUND] Could not save metadata: {e}")
                
                # Register in document registry
                try:
                    from utils.database.models import DocumentRegistryModel
                    
                    is_global = project.lower() in ['global', '__global__', 'global/universal']
                    
                    DocumentRegistryModel.register(
                        filename=filename,
                        file_type=file_ext,
                        storage_type=DocumentRegistryModel.STORAGE_DUCKDB,
                        usage_type=DocumentRegistryModel.USAGE_STRUCTURED_DATA,
                        project_id=project_id if not is_global else None,
                        is_global=is_global,
                        duckdb_tables=result.get('tables_created', []),
                        row_count=total_rows,
                        sheet_count=tables_created,
                        metadata={'project_name': project, 'functional_area': functional_area, 'file_size': file_size}
                    )
                except Exception as e:
                    logger.warning(f"[BACKGROUND] Could not register document: {e}")
                
                # Cleanup
                ProcessingJobModel.update_progress(job_id, 90, "Cleaning up...")
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except:
                        pass
                
                ProcessingJobModel.complete(job_id, {
                    'filename': filename,
                    'type': 'structured',
                    'tables_created': tables_created,
                    'total_rows': total_rows,
                    'project': project
                })
                
                logger.info(f"[BACKGROUND] Structured data job {job_id} completed!")
                return
                
            except Exception as e:
                logger.error(f"[BACKGROUND] Structured storage failed: {e}, falling back to RAG")
                ProcessingJobModel.update_progress(job_id, 15, f"DuckDB storage failed, using text extraction...")
        
        # =====================================================================
        # ROUTE 2: PDF WITH TABLES → DuckDB + ChromaDB (NEW!)
        # =====================================================================
        if file_ext == 'pdf' and PDFPLUMBER_AVAILABLE and STRUCTURED_HANDLER_AVAILABLE:
            ProcessingJobModel.update_progress(job_id, 10, "Analyzing PDF structure for tables...")
            
            analysis = analyze_pdf_for_tables(file_path)
            
            if analysis.get('has_tables') and analysis.get('recommendation') in ['duckdb', 'both']:
                total_rows = analysis.get('total_rows', 0)
                ProcessingJobModel.update_progress(
                    job_id, 20, 
                    f"Found {total_rows} rows of tabular data - storing in DuckDB..."
                )
                
                # Store tables in DuckDB
                duckdb_result = store_pdf_tables_to_duckdb(
                    tables=analysis.get('tables', []),
                    combined_table=analysis.get('combined_table'),
                    project=project,
                    filename=filename,
                    job_id=job_id
                )
                
                if duckdb_result.get('success'):
                    logger.info(f"[BACKGROUND] PDF tables stored in DuckDB: {duckdb_result}")
                    
                    # If ONLY tables (not mixed), we're done
                    if analysis.get('recommendation') == 'duckdb' and analysis.get('table_ratio', 0) > 0.7:
                        ProcessingJobModel.update_progress(job_id, 90, "Registering document...")
                        
                        # Register
                        try:
                            from utils.database.models import DocumentRegistryModel
                            is_global = project.lower() in ['global', '__global__', 'global/universal']
                            
                            DocumentRegistryModel.register(
                                filename=filename,
                                file_type='pdf',
                                storage_type=DocumentRegistryModel.STORAGE_DUCKDB,
                                usage_type=DocumentRegistryModel.USAGE_STRUCTURED_DATA,
                                project_id=project_id if not is_global else None,
                                is_global=is_global,
                                duckdb_tables=duckdb_result.get('tables_created', []),
                                row_count=duckdb_result.get('total_rows', 0),
                                metadata={
                                    'project_name': project,
                                    'source': 'pdf_table_extraction',
                                    'file_size': file_size
                                }
                            )
                        except Exception as e:
                            logger.warning(f"[BACKGROUND] Could not register: {e}")
                        
                        # Cleanup
                        if file_path and os.path.exists(file_path):
                            try:
                                os.remove(file_path)
                            except:
                                pass
                        
                        ProcessingJobModel.complete(job_id, {
                            'filename': filename,
                            'type': 'pdf_tabular',
                            'tables_created': duckdb_result.get('tables_created', []),
                            'total_rows': duckdb_result.get('total_rows', 0),
                            'storage': 'duckdb',
                            'project': project
                        })
                        
                        logger.info(f"[BACKGROUND] PDF table job {job_id} completed!")
                        return
                    
                    # For 'both', continue to also add to ChromaDB
                    ProcessingJobModel.update_progress(job_id, 55, "Also indexing text for semantic search...")
                else:
                    ProcessingJobModel.update_progress(
                        job_id, 25, 
                        f"Table storage failed ({duckdb_result.get('error')}), using text extraction..."
                    )
        
        # =====================================================================
        # ROUTE 3: UNSTRUCTURED DATA (PDF/Word/Text) → ChromaDB
        # =====================================================================
        ProcessingJobModel.update_progress(job_id, 30 if file_ext == 'pdf' else 5, "Extracting text from file...")
        text = extract_text(file_path)
        
        if not text or len(text.strip()) < 10:
            ProcessingJobModel.fail(job_id, "No text could be extracted from file")
            return
        
        logger.info(f"[BACKGROUND] Extracted {len(text)} characters")
        ProcessingJobModel.update_progress(job_id, 35, f"Extracted {len(text):,} characters")
        
        # Prepare metadata
        metadata = {
            "project": project,
            "filename": filename,
            "file_type": file_ext,
            "source": filename,
            "upload_date": datetime.now().isoformat()
        }
        
        if project_id:
            metadata["project_id"] = project_id
        
        if functional_area:
            metadata["functional_area"] = functional_area
        
        # Initialize RAG and process
        ProcessingJobModel.update_progress(job_id, 40, "Initializing document processor...")
        
        def update_progress(current: int, total: int, message: str):
            """Callback for RAG handler progress updates"""
            overall_percent = 40 + int(current * 0.50)
            ProcessingJobModel.update_progress(job_id, overall_percent, message)
        
        rag = RAGHandler()
        
        ProcessingJobModel.update_progress(job_id, 45, "Chunking document...")
        
        success = rag.add_document(
            collection_name="documents",
            text=text,
            metadata=metadata,
            progress_callback=update_progress
        )
        
        if not success:
            ProcessingJobModel.fail(job_id, "Failed to add document to vector store")
            return
        
        # Save to documents table
        ProcessingJobModel.update_progress(job_id, 92, "Saving to database...")
        
        if project_id:
            try:
                DocumentModel.create(
                    project_id=project_id,
                    name=filename,
                    category=functional_area or 'General',
                    file_type=file_ext,
                    file_size=file_size,
                    content=text[:5000],
                    metadata=metadata
                )
            except Exception as e:
                logger.warning(f"[BACKGROUND] Could not save to documents table: {e}")
        
        # Register in document registry
        try:
            from utils.database.models import DocumentRegistryModel
            
            is_global = project.lower() in ['global', '__global__', 'global/universal']
            
            DocumentRegistryModel.register(
                filename=filename,
                file_type=file_ext,
                storage_type=DocumentRegistryModel.STORAGE_CHROMADB,
                usage_type=DocumentRegistryModel.USAGE_RAG_KNOWLEDGE,
                project_id=project_id if not is_global else None,
                is_global=is_global,
                chromadb_collection='documents',
                chunk_count=len(text) // 1000,
                metadata={
                    'project_name': project,
                    'functional_area': functional_area,
                    'file_size': file_size,
                    'text_length': len(text)
                }
            )
        except Exception as e:
            logger.warning(f"[BACKGROUND] Could not register document: {e}")
        
        # Cleanup
        ProcessingJobModel.update_progress(job_id, 96, "Cleaning up...")
        
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        
        ProcessingJobModel.complete(job_id, {
            'filename': filename,
            'type': 'unstructured',
            'chunks_created': len(text) // 1000,
            'text_length': len(text),
            'project': project
        })
        
        logger.info(f"[BACKGROUND] RAG job {job_id} completed!")
        
    except Exception as e:
        logger.error(f"[BACKGROUND] Job {job_id} failed: {e}")
        logger.error(traceback.format_exc())
        ProcessingJobModel.fail(job_id, str(e))


# =============================================================================
# API ENDPOINTS (keep existing, add status polling)
# =============================================================================

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    project: str = Form(...),
    project_id: Optional[str] = Form(None),
    functional_area: Optional[str] = Form(None)
):
    """
    Upload a file for processing.
    
    Returns job_id immediately - poll /upload/status/{job_id} for progress.
    """
    try:
        # Validate
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Create job FIRST so user sees immediate feedback
        job_id = ProcessingJobModel.create(
            filename=file.filename,
            project=project,
            project_id=project_id
        )
        
        logger.info(f"[UPLOAD] Created job {job_id} for {file.filename}")
        ProcessingJobModel.update_progress(job_id, 1, "Receiving file...")
        
        # Save file
        upload_dir = "/data/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_filename = file.filename.replace(' ', '_').replace('/', '_')
        file_path = os.path.join(upload_dir, f"{timestamp}_{safe_filename}")
        
        content = await file.read()
        file_size = len(content)
        
        with open(file_path, 'wb') as f:
            f.write(content)
        
        ProcessingJobModel.update_progress(job_id, 3, f"File saved ({file_size:,} bytes), starting processing...")
        
        # Start background processing
        thread = threading.Thread(
            target=process_file_background,
            args=(job_id, file_path, file.filename, project, project_id, functional_area, file_size),
            daemon=True
        )
        thread.start()
        
        return {
            "success": True,
            "job_id": job_id,
            "message": f"Processing started for {file.filename}",
            "poll_url": f"/upload/status/{job_id}"
        }
        
    except Exception as e:
        logger.error(f"[UPLOAD] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/upload/status/{job_id}")
async def get_upload_status(job_id: str):
    """
    Get status of an upload job.
    
    Poll this endpoint to track progress.
    """
    try:
        job = ProcessingJobModel.get(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {
            "job_id": job_id,
            "status": job.get('status', 'unknown'),
            "progress": job.get('progress', 0),
            "message": job.get('message', ''),
            "filename": job.get('filename', ''),
            "result": job.get('result'),
            "error": job.get('error'),
            "created_at": job.get('created_at'),
            "updated_at": job.get('updated_at')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[STATUS] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/upload/jobs")
async def list_upload_jobs(
    project_id: Optional[str] = None,
    limit: int = 20
):
    """List recent upload jobs"""
    try:
        jobs = ProcessingJobModel.list_recent(project_id=project_id, limit=limit)
        return {"jobs": jobs}
    except Exception as e:
        logger.error(f"[JOBS] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
