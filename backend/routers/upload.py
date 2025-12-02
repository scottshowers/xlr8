"""
Async Upload Router for XLR8
============================

FEATURES:
- Returns immediately after file save (no timeout!)
- Processes in background thread
- Real-time status updates via job polling
- Handles large files gracefully
- Smart Excel parsing (detects blue/colored headers)

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

logger = logging.getLogger(__name__)

router = APIRouter()


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
            
            # Method 3: Fallback to PyPDF2 if others failed
            if len(text) < 500:
                try:
                    logger.info("[PDF] Trying PyPDF2 extraction...")
                    with open(file_path, 'rb') as f:
                        pdf = PyPDF2.PdfReader(f)
                        page_texts = []
                        for i, page in enumerate(pdf.pages):
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
            
            # Final check
            if len(text) < 100:
                logger.error(f"[PDF] All extraction methods failed or returned minimal text ({len(text)} chars)")
            else:
                logger.info(f"[PDF] Final extraction: {len(text)} chars from {pages_extracted} pages")
            
            return text
        
        elif ext == 'docx':
            doc = docx.Document(file_path)
            return "\n".join([p.text for p in doc.paragraphs])
        
        elif ext in ['xlsx', 'xls']:
            # SMART EXCEL READER
            # - Detects blue/colored header rows (by cell formatting)
            # - Handles multiple data sections per sheet
            # - Properly structures each table
            
            texts = []
            
            if not OPENPYXL_AVAILABLE:
                # Fallback to simple pandas if openpyxl not available
                logger.info("[EXCEL] Using pandas fallback (openpyxl not available)")
                excel = pd.ExcelFile(file_path)
                for sheet in excel.sheet_names:
                    df = pd.read_excel(file_path, sheet_name=sheet, header=1)
                    df = df.dropna(how='all')
                    texts.append(f"[SHEET: {sheet}]\n{df.to_string()}")
                return "\n\n".join(texts)
            
            try:
                # Load with openpyxl to access formatting
                wb = load_workbook(file_path, data_only=True)
                
                for sheet_name in wb.sheetnames:
                    ws = wb[sheet_name]
                    logger.info(f"[EXCEL] Processing sheet: {sheet_name}")
                    
                    sheet_texts = [f"[SHEET: {sheet_name}]"]
                    
                    # Find all header rows (blue/colored background)
                    header_rows = []
                    
                    for row_idx, row in enumerate(ws.iter_rows(min_row=1, max_row=min(ws.max_row, 500)), start=1):
                        # Check first cells for colored fill
                        colored_cell_count = 0
                        non_empty_count = 0
                        
                        for cell in row[:20]:  # Check first 20 columns
                            if cell.value is not None and str(cell.value).strip():
                                non_empty_count += 1
                            
                            # Check for fill color (any non-white/non-empty fill)
                            try:
                                if cell.fill and cell.fill.fgColor and cell.fill.patternType and cell.fill.patternType != 'none':
                                    color = cell.fill.fgColor
                                    
                                    # RGB color
                                    if color.type == 'rgb' and color.rgb:
                                        rgb = str(color.rgb).upper()
                                        # Skip white/near-white colors
                                        if rgb not in ['FFFFFFFF', '00FFFFFF', 'FFFFFF', '00000000']:
                                            colored_cell_count += 1
                                    
                                    # Theme color (typically headers use theme colors)
                                    elif color.type == 'theme' and color.theme is not None:
                                        colored_cell_count += 1
                                    
                                    # Indexed color
                                    elif color.type == 'indexed' and color.indexed is not None:
                                        if color.indexed not in [0, 64]:  # Not black or white
                                            colored_cell_count += 1
                            except:
                                pass
                        
                        # If multiple cells have color fill and row has content, it's likely a header
                        if colored_cell_count >= 2 and non_empty_count >= 2:
                            header_rows.append(row_idx)
                            logger.info(f"[EXCEL] Found header row at {row_idx} ({colored_cell_count} colored cells, {non_empty_count} with data)")
                    
                    # If no colored headers found, fall back to first row with substantial data
                    if not header_rows:
                        logger.info(f"[EXCEL] No colored headers in '{sheet_name}', detecting by content")
                        for row_idx, row in enumerate(ws.iter_rows(min_row=1, max_row=10), start=1):
                            non_empty = sum(1 for cell in row[:20] if cell.value and str(cell.value).strip())
                            if non_empty >= 3:  # At least 3 non-empty cells
                                header_rows.append(row_idx)
                                break
                    
                    if not header_rows:
                        texts.append(f"[SHEET: {sheet_name}]\nNo Data Available\n")
                        continue
                    
                    # Process each data section (header + data until next header or end)
                    for section_idx, header_row in enumerate(header_rows):
                        # Determine where this section ends
                        if section_idx + 1 < len(header_rows):
                            end_row = header_rows[section_idx + 1] - 1
                        else:
                            end_row = ws.max_row
                        
                        # Get header values
                        headers = []
                        for cell in ws[header_row]:
                            val = str(cell.value).strip() if cell.value else ''
                            if val and val.lower() not in ['none', 'nan']:
                                headers.append(val)
                            elif cell.column <= 20:  # Only add placeholder for first 20 cols
                                headers.append(f"Col{cell.column}")
                        
                        # Clean up trailing empty headers
                        while headers and (headers[-1].startswith('Col') or not headers[-1]):
                            headers.pop()
                        
                        if not headers:
                            continue
                        
                        # Add section marker if multiple sections
                        if len(header_rows) > 1:
                            sheet_texts.append(f"\n--- Section {section_idx + 1} ---")
                        
                        sheet_texts.append(f"Columns: {' | '.join(headers)}")
                        
                        # Get data rows
                        data_row_count = 0
                        for row_idx in range(header_row + 1, min(end_row + 1, header_row + 1000)):  # Limit rows
                            row_data = []
                            has_data = False
                            
                            for col_idx, header in enumerate(headers, start=1):
                                cell = ws.cell(row=row_idx, column=col_idx)
                                val = cell.value
                                
                                if val is not None:
                                    val_str = str(val).strip()
                                    if val_str and val_str.lower() not in ['none', 'nan', '']:
                                        has_data = True
                                        if header.startswith('Col'):
                                            row_data.append(val_str)
                                        else:
                                            row_data.append(f"{header}: {val_str}")
                            
                            if has_data and row_data:
                                sheet_texts.append(" | ".join(row_data))
                                data_row_count += 1
                        
                        logger.info(f"[EXCEL] Sheet '{sheet_name}' Section {section_idx + 1}: {data_row_count} data rows")
                    
                    # Only add sheet if it has content beyond just the header
                    if len(sheet_texts) > 2:  # More than just [SHEET:] and Columns:
                        texts.append("\n".join(sheet_texts))
                    else:
                        texts.append(f"[SHEET: {sheet_name}]\nNo Data Available\n")
                
                wb.close()
                
            except Exception as e:
                logger.error(f"[EXCEL] openpyxl error: {e}, falling back to pandas")
                import traceback
                logger.error(traceback.format_exc())
                
                # Fallback to pandas
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
        
        else:
            # Try as text
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
                
    except Exception as e:
        logger.error(f"Text extraction failed for {file_path}: {e}")
        raise


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
    2. For PDFs/Docs: Extract text, chunk, embed in ChromaDB
    3. Update job status throughout
    """
    try:
        logger.info(f"[BACKGROUND] Starting processing for job {job_id}")
        logger.info(f"[BACKGROUND] project={project}, project_id={project_id}")
        
        file_ext = filename.split('.')[-1].lower()
        
        # ROUTE 1: STRUCTURED DATA (Excel/CSV) → DuckDB
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
                    tables_created = len(result.get('tables_created', []))
                    total_rows = result.get('total_rows', 0)
                
                ProcessingJobModel.update_progress(
                    job_id, 70, 
                    f"Created {tables_created} table(s) with {total_rows:,} rows"
                )
                
                # Store schema summary in documents table for reference
                if project_id:
                    try:
                        schema_summary = json.dumps(result, indent=2)
                        DocumentModel.create(
                            project_id=project_id,
                            name=filename,
                            category=functional_area or 'Structured Data',
                            file_type=file_ext,
                            file_size=file_size,
                            content=f"STRUCTURED DATA FILE\n\nSchema:\n{schema_summary[:4000]}",
                            metadata={
                                'type': 'structured',
                                'storage': 'duckdb',
                                'tables': result.get('tables_created', []),
                                'total_rows': total_rows,
                                'project': project,
                                'functional_area': functional_area
                            }
                        )
                        logger.info(f"[BACKGROUND] Saved structured data metadata to database")
                    except Exception as e:
                        logger.warning(f"[BACKGROUND] Could not save metadata: {e}")
                
                # Cleanup
                ProcessingJobModel.update_progress(job_id, 90, "Cleaning up...")
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except:
                        pass
                
                # Complete!
                ProcessingJobModel.complete(job_id, {
                    'filename': filename,
                    'type': 'structured',
                    'tables_created': tables_created,
                    'total_rows': total_rows,
                    'project': project,
                    'functional_area': functional_area
                })
                
                logger.info(f"[BACKGROUND] Structured data job {job_id} completed!")
                return
                
            except Exception as e:
                logger.error(f"[BACKGROUND] Structured storage failed: {e}, falling back to RAG")
                # Fall through to RAG processing
        
        # ROUTE 2: UNSTRUCTURED DATA (PDF/Word/Text) → ChromaDB
        ProcessingJobModel.update_progress(job_id, 5, "Extracting text from file...")
        text = extract_text(file_path)
        
        if not text or len(text.strip()) < 10:
            ProcessingJobModel.fail(job_id, "No text could be extracted from file")
            return
        
        logger.info(f"[BACKGROUND] Extracted {len(text)} characters")
        ProcessingJobModel.update_progress(job_id, 15, f"Extracted {len(text):,} characters")
        
        # Step 2: Prepare metadata
        file_ext = filename.split('.')[-1].lower()
        
        metadata = {
            "project": project,
            "filename": filename,
            "file_type": file_ext,
            "source": filename,
            "upload_date": datetime.now().isoformat()
        }
        
        if project_id:
            metadata["project_id"] = project_id
            logger.info(f"[BACKGROUND] ✓ Metadata includes project_id: {project_id}")
        else:
            logger.warning(f"[BACKGROUND] ✗ No project_id in metadata!")
        
        if functional_area:
            metadata["functional_area"] = functional_area
        
        # Step 3: Initialize RAG and process
        ProcessingJobModel.update_progress(job_id, 20, "Initializing document processor...")
        
        def update_progress(current: int, total: int, message: str):
            """Callback for RAG handler progress updates"""
            # Map RAG progress (0-100) to our range (20-90)
            overall_percent = 20 + int(current * 0.70)
            ProcessingJobModel.update_progress(job_id, overall_percent, message)
        
        rag = RAGHandler()
        
        ProcessingJobModel.update_progress(job_id, 25, "Chunking document...")
        
        success = rag.add_document(
            collection_name="documents",
            text=text,
            metadata=metadata,
            progress_callback=update_progress
        )
        
        if not success:
            ProcessingJobModel.fail(job_id, "Failed to add document to vector store")
            return
        
        # Step 4: Save to documents table (if we have project UUID)
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
                logger.info(f"[BACKGROUND] Saved document to database")
            except Exception as e:
                logger.warning(f"[BACKGROUND] Could not save to documents table: {e}")
        
        # Step 5: Cleanup
        ProcessingJobModel.update_progress(job_id, 96, "Cleaning up...")
        
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"[BACKGROUND] Cleaned up temp file")
            except Exception as e:
                logger.warning(f"[BACKGROUND] Could not delete temp file: {e}")
        
        # Step 6: Complete!
        ProcessingJobModel.complete(job_id, {
            'filename': filename,
            'characters': len(text),
            'project': project,
            'functional_area': functional_area
        })
        
        logger.info(f"[BACKGROUND] Job {job_id} completed successfully!")
        
    except Exception as e:
        logger.error(f"[BACKGROUND] Job {job_id} failed: {e}")
        logger.error(traceback.format_exc())
        
        ProcessingJobModel.fail(job_id, str(e))
        
        # Cleanup on failure
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    project: str = Form(...),
    functional_area: Optional[str] = Form(None)
):
    """
    Async upload endpoint - returns immediately, processes in background
    
    Flow:
    1. Save file to disk
    2. Create job record
    3. Start background thread
    4. Return job_id immediately
    5. Client polls /api/jobs/{job_id} for progress
    """
    file_path = None
    
    try:
        # Look up project UUID from project name OR project ID
        project_id = None
        logger.info(f"[UPLOAD] Received project value: '{project}'")
        
        if project and project not in ['global', '__GLOBAL__', 'GLOBAL', '']:
            projects = ProjectModel.get_all(status='active')
            logger.info(f"[UPLOAD] Found {len(projects)} active projects")
            
            # Try to match by name first
            matching_project = next((p for p in projects if p.get('name') == project), None)
            logger.info(f"[UPLOAD] Match by name: {matching_project is not None}")
            
            # If not found by name, try by ID (frontend may send UUID directly)
            if not matching_project:
                matching_project = next((p for p in projects if p.get('id') == project), None)
                logger.info(f"[UPLOAD] Match by ID: {matching_project is not None}")
            
            if matching_project:
                project_id = matching_project['id']
                logger.info(f"[UPLOAD] ✓ Found project UUID: {project_id} for input: {project}")
            else:
                logger.warning(f"[UPLOAD] ✗ No project found for: {project}")
                # Log available projects for debugging
                for p in projects[:3]:
                    logger.info(f"[UPLOAD] Available: id={p.get('id')}, name={p.get('name')}")
        
        # Create job record FIRST (so we have job_id)
        job = ProcessingJobModel.create(
            job_type='file_upload',
            project_id=project,
            filename=file.filename,
            input_data={
                'filename': file.filename,
                'functional_area': functional_area,
                'async': True
            }
        )
        
        if not job:
            raise HTTPException(status_code=500, detail="Failed to create processing job")
        
        job_id = job['id']
        logger.info(f"[ASYNC] Created job {job_id} for {file.filename}")
        
        # Save file to disk
        ProcessingJobModel.update_progress(job_id, 2, "Saving file...")
        
        os.makedirs("/data/uploads", exist_ok=True)
        file_path = f"/data/uploads/{job_id}_{file.filename}"
        
        content = await file.read()
        file_size = len(content)
        
        with open(file_path, "wb") as f:
            f.write(content)
        
        logger.info(f"[ASYNC] Saved {file_size:,} bytes to {file_path}")
        ProcessingJobModel.update_progress(job_id, 4, f"File saved ({file_size:,} bytes)")
        
        # Start background processing thread
        thread = threading.Thread(
            target=process_file_background,
            args=(job_id, file_path, file.filename, project, project_id, functional_area, file_size),
            daemon=True
        )
        thread.start()
        
        logger.info(f"[ASYNC] Started background thread for job {job_id}")
        
        # Return immediately!
        return {
            "job_id": job_id,
            "status": "processing",
            "message": f"File '{file.filename}' queued for processing. Check status page for progress.",
            "async": True
        }
        
    except HTTPException:
        raise
        
    except Exception as e:
        logger.error(f"[ASYNC] Upload failed: {e}")
        logger.error(traceback.format_exc())
        
        # Cleanup on failure
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        
        raise HTTPException(status_code=500, detail=str(e))
