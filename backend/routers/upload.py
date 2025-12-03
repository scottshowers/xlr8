"""
Async Upload Router for XLR8
============================

FEATURES:
- Returns immediately after file save (no timeout!)
- Processes in QUEUED background thread (sequential, no overlap!)
- Real-time status updates via job polling
- Handles large files gracefully
- Smart Excel parsing (detects blue/colored headers)

CHANGE LOG:
- v2: Added job queue to prevent multi-file overlap/hang

Author: XLR8 Team
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from typing import Optional
from datetime import datetime
import sys
import os
import json
import threading
import queue
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


# =============================================================================
# JOB QUEUE - Prevents multi-file overlap and hangs
# =============================================================================
class JobQueue:
    """
    Sequential job queue - processes one file at a time.
    Solves: Multiple uploads hitting Ollama simultaneously → hangs
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._queue = queue.Queue()
        self._worker_thread = None
        self._running = False
        self._current_job_id = None
        self._processed_count = 0
        self._initialized = True
        
        self._start_worker()
        logger.info("[JOB_QUEUE] Initialized sequential processing queue")
    
    def _start_worker(self):
        """Start single worker thread"""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._running = True
            self._worker_thread = threading.Thread(
                target=self._worker_loop,
                daemon=True,
                name="UploadQueueWorker"
            )
            self._worker_thread.start()
    
    def _worker_loop(self):
        """Process jobs one at a time"""
        while self._running:
            try:
                job = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue
            
            job_id, func, args = job
            self._current_job_id = job_id
            
            logger.info(f"[JOB_QUEUE] 🚀 Processing job {job_id} (queue size: {self._queue.qsize()})")
            
            try:
                func(*args)
                self._processed_count += 1
            except Exception as e:
                logger.error(f"[JOB_QUEUE] Job {job_id} failed: {e}")
                logger.error(traceback.format_exc())
            finally:
                self._current_job_id = None
                self._queue.task_done()
    
    def enqueue(self, job_id: str, func, args: tuple) -> dict:
        """Add job to queue - returns immediately with position"""
        position = self._queue.qsize() + 1
        self._queue.put((job_id, func, args))
        
        logger.info(f"[JOB_QUEUE] 📥 Enqueued job {job_id} at position {position}")
        
        self._start_worker()  # Ensure worker is running
        
        return {
            'queue_position': position,
            'currently_processing': self._current_job_id,
            'queue_size': position
        }
    
    def get_status(self) -> dict:
        """Get queue status for status endpoint"""
        return {
            'queue_size': self._queue.qsize(),
            'currently_processing': self._current_job_id,
            'processed_count': self._processed_count,
            'worker_alive': self._worker_thread.is_alive() if self._worker_thread else False
        }


# Singleton queue instance
job_queue = JobQueue()


# =============================================================================
# TEXT EXTRACTION
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
            # SMART EXCEL READER with header detection
            texts = []
            
            if not OPENPYXL_AVAILABLE:
                # Fallback to simple pandas
                logger.info("[EXCEL] Using pandas fallback")
                excel = pd.ExcelFile(file_path)
                for sheet in excel.sheet_names:
                    df = pd.read_excel(file_path, sheet_name=sheet, header=1)
                    df = df.dropna(how='all')
                    texts.append(f"[SHEET: {sheet}]\n{df.to_string()}")
                return "\n\n".join(texts)
            
            try:
                wb = load_workbook(file_path, data_only=True)
                
                for sheet_name in wb.sheetnames:
                    ws = wb[sheet_name]
                    sheet_texts = [f"[SHEET: {sheet_name}]"]
                    
                    # Find header rows by color
                    header_rows = []
                    for row_idx, row in enumerate(ws.iter_rows(min_row=1, max_row=min(ws.max_row, 500)), start=1):
                        colored_cells = 0
                        non_empty = 0
                        
                        for cell in row[:20]:
                            if cell.value and str(cell.value).strip():
                                non_empty += 1
                            try:
                                if cell.fill and cell.fill.fgColor and cell.fill.patternType and cell.fill.patternType != 'none':
                                    color = cell.fill.fgColor
                                    if color.type == 'rgb' and color.rgb:
                                        rgb = str(color.rgb).upper()
                                        if rgb not in ['FFFFFFFF', '00FFFFFF', 'FFFFFF', '00000000']:
                                            colored_cells += 1
                                    elif color.type == 'theme' and color.theme is not None:
                                        colored_cells += 1
                                    elif color.type == 'indexed' and color.indexed not in [0, 64]:
                                        colored_cells += 1
                            except:
                                pass
                        
                        if colored_cells >= 2 and non_empty >= 2:
                            header_rows.append(row_idx)
                    
                    # Fallback: first row with data
                    if not header_rows:
                        for row_idx, row in enumerate(ws.iter_rows(min_row=1, max_row=10), start=1):
                            non_empty = sum(1 for cell in row[:20] if cell.value and str(cell.value).strip())
                            if non_empty >= 3:
                                header_rows.append(row_idx)
                                break
                    
                    if not header_rows:
                        texts.append(f"[SHEET: {sheet_name}]\nNo Data\n")
                        continue
                    
                    # Process sections
                    for sec_idx, header_row in enumerate(header_rows):
                        end_row = header_rows[sec_idx + 1] - 1 if sec_idx + 1 < len(header_rows) else ws.max_row
                        
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
                        
                        if len(header_rows) > 1:
                            sheet_texts.append(f"\n--- Section {sec_idx + 1} ---")
                        
                        sheet_texts.append(f"Columns: {' | '.join(headers)}")
                        
                        # Data rows
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
                                        if header.startswith('Col'):
                                            row_data.append(val_str)
                                        else:
                                            row_data.append(f"{header}: {val_str}")
                            
                            if has_data and row_data:
                                sheet_texts.append(" | ".join(row_data))
                    
                    if len(sheet_texts) > 2:
                        texts.append("\n".join(sheet_texts))
                    else:
                        texts.append(f"[SHEET: {sheet_name}]\nNo Data\n")
                
                wb.close()
                
            except Exception as e:
                logger.error(f"[EXCEL] openpyxl error: {e}")
                excel = pd.ExcelFile(file_path)
                texts = []
                for sheet in excel.sheet_names:
                    try:
                        df = pd.read_excel(file_path, sheet_name=sheet, header=1)
                        df = df.dropna(how='all')
                        texts.append(f"[SHEET: {sheet}]\n{df.to_string()}")
                    except:
                        texts.append(f"[SHEET: {sheet}]\nError\n")
            
            return "\n\n".join(texts)
        
        elif ext == 'csv':
            df = pd.read_csv(file_path)
            return f"WORKSHEET: CSV Data\n{'=' * 40}\n{df.to_string()}"
        
        elif ext in ['txt', 'md']:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        
        else:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
                
    except Exception as e:
        logger.error(f"Text extraction failed for {file_path}: {e}")
        raise


# =============================================================================
# BACKGROUND PROCESSING
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
    Background processing function - runs in job queue worker thread
    
    Routes:
    1. Excel/CSV → DuckDB (structured queries)
    2. PDFs/Docs → ChromaDB (vector search)
    """
    try:
        logger.info(f"[BACKGROUND] Starting job {job_id}")
        
        file_ext = filename.split('.')[-1].lower()
        
        # ROUTE 1: STRUCTURED DATA (Excel/CSV) → DuckDB
        if file_ext in ['xlsx', 'xls', 'csv'] and STRUCTURED_HANDLER_AVAILABLE:
            ProcessingJobModel.update_progress(job_id, 10, "Storing tabular data...")
            
            try:
                handler = get_structured_handler()
                ProcessingJobModel.update_progress(job_id, 20, "Parsing structure...")
                
                if file_ext == 'csv':
                    result = handler.store_csv(file_path, project, filename)
                    tables_created = 1
                    total_rows = result.get('row_count', 0)
                else:
                    result = handler.store_excel(file_path, project, filename)
                    tables_created = len(result.get('tables_created', []))
                    total_rows = result.get('total_rows', 0)
                
                ProcessingJobModel.update_progress(job_id, 70, f"Created {tables_created} table(s)")
                
                # Save metadata
                if project_id:
                    try:
                        DocumentModel.create(
                            project_id=project_id,
                            name=filename,
                            category=functional_area or 'Structured Data',
                            file_type=file_ext,
                            file_size=file_size,
                            content=f"STRUCTURED DATA\nTables: {tables_created}\nRows: {total_rows}",
                            metadata={'type': 'structured', 'storage': 'duckdb'}
                        )
                    except Exception as e:
                        logger.warning(f"Could not save metadata: {e}")
                
                # Register document
                try:
                    from utils.database.models import DocumentRegistryModel
                    is_global = project.lower() in ['global', '__global__', 'global/universal']
                    filename_lower = filename.lower()
                    is_playbook = any(kw in filename_lower for kw in ['year-end', 'yearend', 'checklist'])
                    
                    usage_type = (
                        DocumentRegistryModel.USAGE_PLAYBOOK_SOURCE if is_playbook and is_global
                        else DocumentRegistryModel.USAGE_TEMPLATE if is_global
                        else DocumentRegistryModel.USAGE_STRUCTURED_DATA
                    )
                    
                    DocumentRegistryModel.register(
                        filename=filename,
                        file_type=file_ext,
                        storage_type=DocumentRegistryModel.STORAGE_DUCKDB,
                        usage_type=usage_type,
                        project_id=project_id if not is_global else None,
                        is_global=is_global,
                        duckdb_tables=result.get('tables_created', []),
                        row_count=total_rows,
                        sheet_count=tables_created,
                        metadata={'project_name': project, 'functional_area': functional_area}
                    )
                except Exception as e:
                    logger.warning(f"Could not register: {e}")
                
                # Cleanup
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except:
                        pass
                
                ProcessingJobModel.complete(job_id, {
                    'filename': filename,
                    'type': 'structured',
                    'tables_created': tables_created,
                    'total_rows': total_rows
                })
                return
                
            except Exception as e:
                logger.error(f"Structured storage failed: {e}, falling back to RAG")
        
        # ROUTE 2: UNSTRUCTURED DATA → ChromaDB
        ProcessingJobModel.update_progress(job_id, 5, "Extracting text...")
        text = extract_text(file_path)
        
        if not text or len(text.strip()) < 10:
            ProcessingJobModel.fail(job_id, "No text extracted")
            return
        
        ProcessingJobModel.update_progress(job_id, 15, f"Extracted {len(text):,} chars")
        
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
        
        ProcessingJobModel.update_progress(job_id, 20, "Processing document...")
        
        def update_progress(current: int, total: int, message: str):
            percent = 20 + int(current * 0.70)
            ProcessingJobModel.update_progress(job_id, percent, message)
        
        rag = RAGHandler()
        ProcessingJobModel.update_progress(job_id, 25, "Chunking...")
        
        success = rag.add_document(
            collection_name="documents",
            text=text,
            metadata=metadata,
            progress_callback=update_progress
        )
        
        if not success:
            ProcessingJobModel.fail(job_id, "Failed to add to vector store")
            return
        
        # Save to database
        ProcessingJobModel.update_progress(job_id, 92, "Saving...")
        
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
                logger.warning(f"Could not save: {e}")
        
        # Register document
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
                metadata={'project_name': project, 'text_length': len(text)}
            )
        except Exception as e:
            logger.warning(f"Could not register: {e}")
        
        # Cleanup
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        
        # Auto-scan playbook
        if project_id:
            ProcessingJobModel.update_progress(job_id, 97, "Updating playbook...")
            try:
                for module_path in ['routers.playbooks', 'backend.routers.playbooks', 'playbooks']:
                    try:
                        module = __import__(module_path, fromlist=['trigger_auto_scan_sync'])
                        func = getattr(module, 'trigger_auto_scan_sync', None)
                        if func:
                            func(project_id, filename)
                            break
                    except ImportError:
                        continue
            except:
                pass
        
        # Check for Year-End file in Global
        project_lower = (project or "").lower()
        is_global = project_lower in ['global', 'global/universal', '__global__']
        
        if is_global:
            filename_lower = filename.lower()
            is_year_end = (
                ('year' in filename_lower and 'end' in filename_lower) or
                'year-end' in filename_lower or 'yearend' in filename_lower
            ) and filename_lower.endswith(('.xlsx', '.xls', '.xlsm', '.docx'))
            
            if is_year_end:
                try:
                    global_dir = '/data/global'
                    os.makedirs(global_dir, exist_ok=True)
                    if file_path and os.path.exists(file_path):
                        import shutil
                        shutil.copy2(file_path, os.path.join(global_dir, filename))
                except:
                    pass
        
        ProcessingJobModel.complete(job_id, {
            'filename': filename,
            'characters': len(text),
            'project': project
        })
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        logger.error(traceback.format_exc())
        ProcessingJobModel.fail(job_id, str(e))
        
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass


# =============================================================================
# API ENDPOINTS
# =============================================================================
@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    project: str = Form(...),
    functional_area: Optional[str] = Form(None)
):
    """
    Upload endpoint - returns immediately, processes via job queue
    
    CHANGE: Uses job queue instead of spawning threads
    → No more overlap/hang with multiple files!
    """
    file_path = None
    
    try:
        # Look up project UUID
        project_id = None
        
        if project and project not in ['global', '__GLOBAL__', 'GLOBAL', '']:
            projects = ProjectModel.get_all(status='active')
            matching = next((p for p in projects if p.get('name') == project), None)
            if not matching:
                matching = next((p for p in projects if p.get('id') == project), None)
            if matching:
                project_id = matching['id']
        
        # Create job record
        job = ProcessingJobModel.create(
            job_type='file_upload',
            project_id=project_id,  # Use UUID, not project name
            filename=file.filename,
            input_data={'filename': file.filename, 'functional_area': functional_area, 'project_name': project}
        )
        
        if not job:
            raise HTTPException(status_code=500, detail="Failed to create job")
        
        job_id = job['id']
        logger.info(f"[UPLOAD] Created job {job_id}")
        
        # Save file
        ProcessingJobModel.update_progress(job_id, 2, "Saving file...")
        os.makedirs("/data/uploads", exist_ok=True)
        file_path = f"/data/uploads/{job_id}_{file.filename}"
        
        content = await file.read()
        file_size = len(content)
        
        with open(file_path, "wb") as f:
            f.write(content)
        
        ProcessingJobModel.update_progress(job_id, 4, f"Saved ({file_size:,} bytes)")
        
        # =====================================================
        # KEY CHANGE: Queue instead of thread.start()
        # =====================================================
        queue_info = job_queue.enqueue(
            job_id,
            process_file_background,
            (job_id, file_path, file.filename, project, project_id, functional_area, file_size)
        )
        
        # Update status with queue position
        if queue_info['queue_position'] > 1:
            ProcessingJobModel.update_progress(
                job_id, 4, 
                f"Queued at position {queue_info['queue_position']} (waiting for {queue_info['queue_position'] - 1} file(s))"
            )
        
        return {
            "job_id": job_id,
            "status": "queued",
            "message": f"File '{file.filename}' queued for processing",
            "queue_position": queue_info['queue_position'],
            "queue_size": queue_info['queue_size'],
            "async": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/upload/queue-status")
async def get_upload_queue_status():
    """Get current upload queue status"""
    return job_queue.get_status()
