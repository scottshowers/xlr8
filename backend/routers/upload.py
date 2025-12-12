"""
Async Upload Router for XLR8
============================

FEATURES:
- Returns immediately after file save (no timeout!)
- Processes in background thread
- Real-time status updates via job polling
- Handles large files gracefully
- Smart Excel parsing (detects blue/colored headers)
- SMART PDF ROUTING - tabular PDFs go to DuckDB!
- CONTENT-BASED ROUTING - routes by content, not file extension
- INTELLIGENCE ANALYSIS - runs on upload for instant insights (Phase 3)

ROUTING LOGIC:
- XLSX/XLS/CSV → DuckDB ONLY (never ChromaDB - structured data doesn't chunk)
- PDF → Smart analysis → DuckDB (tables) + ChromaDB (text)
- DOCX/TXT/MD → Content analysis:
    - If TABULAR → Extract tables → DuckDB
    - If NARRATIVE → ChromaDB
- Other → ChromaDB

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

# Import smart PDF analyzer for tabular PDFs
try:
    from backend.utils.smart_pdf_analyzer import process_pdf_intelligently
    SMART_PDF_AVAILABLE = True
except ImportError:
    SMART_PDF_AVAILABLE = False
    logger_temp = logging.getLogger(__name__)
    logger_temp.warning("Smart PDF analyzer not available - PDFs will use RAG only")

# Import document analyzer for content-based routing
try:
    from backend.utils.document_analyzer import DocumentAnalyzer, DocumentStructure
    DOCUMENT_ANALYZER_AVAILABLE = True
except ImportError:
    DOCUMENT_ANALYZER_AVAILABLE = False
    logger_temp = logging.getLogger(__name__)
    logger_temp.warning("Document analyzer not available - DOCX/TXT will use extension-based routing")

# Import intelligence service for Phase 3 analysis
try:
    from utils.project_intelligence import ProjectIntelligenceService, AnalysisTier
    INTELLIGENCE_AVAILABLE = True
except ImportError:
    INTELLIGENCE_AVAILABLE = False
    logger_temp = logging.getLogger(__name__)
    logger_temp.warning("Project intelligence not available - upload analysis disabled")

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# DEBUG ENDPOINT - Check what's available
# =============================================================================
@router.get("/upload/debug")
async def debug_features():
    """Debug endpoint to check what features are available"""
    import os
    
    results = {
        "version": "2025-12-12-v10-with-intelligence",  # Update this when deploying
        "smart_pdf_available": SMART_PDF_AVAILABLE,
        "structured_handler_available": STRUCTURED_HANDLER_AVAILABLE,
        "openpyxl_available": OPENPYXL_AVAILABLE,
        "intelligence_available": INTELLIGENCE_AVAILABLE,
        "files_in_utils": [],
        "import_errors": []
    }
    
    # Check what files exist in /app/utils
    try:
        utils_path = "/app/utils"
        if os.path.exists(utils_path):
            results["files_in_utils"] = os.listdir(utils_path)
        else:
            results["files_in_utils"] = ["DIRECTORY NOT FOUND"]
    except Exception as e:
        results["files_in_utils"] = [f"ERROR: {e}"]
    
    # Try imports and capture specific errors
    try:
        from backend.utils.smart_pdf_analyzer import process_pdf_intelligently
        results["smart_pdf_import"] = "SUCCESS"
    except ImportError as e:
        results["smart_pdf_import"] = f"FAILED: {e}"
        results["import_errors"].append(f"smart_pdf_analyzer: {e}")
    except Exception as e:
        results["smart_pdf_import"] = f"ERROR: {e}"
        results["import_errors"].append(f"smart_pdf_analyzer: {e}")
    
    try:
        from utils.structured_data_handler import get_structured_handler
        results["structured_handler_import"] = "SUCCESS"
    except ImportError as e:
        results["structured_handler_import"] = f"FAILED: {e}"
        results["import_errors"].append(f"structured_data_handler: {e}")
    except Exception as e:
        results["structured_handler_import"] = f"ERROR: {e}"
        results["import_errors"].append(f"structured_data_handler: {e}")
    
    try:
        from utils.project_intelligence import ProjectIntelligenceService
        results["intelligence_import"] = "SUCCESS"
    except ImportError as e:
        results["intelligence_import"] = f"FAILED: {e}"
        results["import_errors"].append(f"project_intelligence: {e}")
    except Exception as e:
        results["intelligence_import"] = f"ERROR: {e}"
        results["import_errors"].append(f"project_intelligence: {e}")
    
    # Check pdfplumber
    try:
        import pdfplumber
        results["pdfplumber_available"] = True
    except ImportError:
        results["pdfplumber_available"] = False
        results["import_errors"].append("pdfplumber not installed")
    
    return results


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
            if len(text) < 100:
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
            
            # Log final result
            if len(text) < 100:
                logger.error(f"[PDF] All extraction methods failed or returned minimal text ({len(text)} chars)")
            else:
                logger.info(f"[PDF] Final extraction: {len(text)} chars from {pages_extracted} pages")
                
            return text
            
        elif ext == 'docx':
            doc = docx.Document(file_path)
            return '\n'.join([para.text for para in doc.paragraphs])
        elif ext == 'txt':
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
        elif ext == 'md':
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
        elif ext in ['xlsx', 'xls']:
            # For structured data, return a text representation
            df = pd.read_excel(file_path)
            return df.to_string()
        elif ext == 'csv':
            df = pd.read_csv(file_path)
            return df.to_string()
        else:
            # Try to read as text
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
    except Exception as e:
        logger.error(f"Error extracting text from {file_path}: {e}")
        return ""


def detect_excel_header_row(file_path: str) -> int:
    """
    Intelligently detect the header row in an Excel file by looking for:
    - Colored/styled rows (often headers have background colors)
    - Rows with bold text
    - Rows where all cells contain text (not numbers)
    - Common header patterns
    
    Returns the 0-based row index of the likely header row.
    """
    if not OPENPYXL_AVAILABLE:
        return 0  # Default to first row if openpyxl not available
        
    try:
        wb = load_workbook(file_path, data_only=True)
        ws = wb.active
        
        if ws.max_row is None or ws.max_row < 2:
            return 0
            
        # Check first 15 rows for header characteristics
        max_check = min(15, ws.max_row)
        
        for row_idx in range(1, max_check + 1):
            row_cells = list(ws.iter_rows(min_row=row_idx, max_row=row_idx, values_only=False))[0]
            
            # Check for fill color (background color)
            has_fill = False
            has_bold = False
            non_empty_count = 0
            all_text = True
            
            for cell in row_cells:
                if cell.value is not None:
                    non_empty_count += 1
                    
                    # Check if it looks like a number
                    if isinstance(cell.value, (int, float)):
                        all_text = False
                    
                    # Check for fill color
                    if cell.fill and cell.fill.fgColor and cell.fill.fgColor.rgb:
                        rgb = cell.fill.fgColor.rgb
                        # Check if it's not white or transparent
                        if rgb not in ['00000000', 'FFFFFFFF', '00FFFFFF', None]:
                            has_fill = True
                    
                    # Check for bold
                    if cell.font and cell.font.bold:
                        has_bold = True
            
            # If this row has 3+ non-empty cells, has styling, and is mostly text
            if non_empty_count >= 3 and (has_fill or has_bold) and all_text:
                logger.info(f"[EXCEL] Detected header at row {row_idx} (fill={has_fill}, bold={has_bold})")
                wb.close()
                return row_idx - 1  # Convert to 0-based index
        
        wb.close()
        return 0  # Default to first row
        
    except Exception as e:
        logger.warning(f"[EXCEL] Header detection failed: {e}, using row 0")
        return 0


# =============================================================================
# JOB QUEUE FOR SEQUENTIAL PROCESSING
# =============================================================================
import queue
from dataclasses import dataclass, field
from typing import Callable, Any, Tuple

@dataclass(order=True)
class QueuedJob:
    """A job waiting in the queue"""
    priority: int
    job_id: str = field(compare=False)
    func: Callable = field(compare=False)
    args: Tuple = field(compare=False)
    kwargs: dict = field(compare=False, default_factory=dict)
    queued_at: datetime = field(compare=False, default_factory=datetime.now)


class JobQueue:
    """
    Sequential job queue - processes ONE job at a time.
    Prevents Ollama from being overloaded with concurrent requests.
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
            
        self._queue = queue.PriorityQueue()
        self._current_job = None
        self._processed_count = 0
        self._worker_thread = None
        self._running = True
        self._job_positions = {}  # job_id -> position
        
        # Start worker thread
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
        
        self._initialized = True
        logger.info("[QUEUE] Job queue initialized with sequential processing")
    
    def enqueue(self, job_id: str, func: Callable, args: Tuple = (), kwargs: dict = None, priority: int = 10) -> dict:
        """Add a job to the queue. Returns immediately with queue position."""
        if kwargs is None:
            kwargs = {}
            
        job = QueuedJob(
            priority=priority,
            job_id=job_id,
            func=func,
            args=args,
            kwargs=kwargs
        )
        
        self._queue.put(job)
        position = self._queue.qsize()
        self._job_positions[job_id] = position
        
        logger.info(f"[QUEUE] Job {job_id} queued at position {position}")
        
        return {
            'queued': True,
            'position': position,
            'queue_size': position,
            'message': f'Queued at position {position}'
        }
    
    def get_position(self, job_id: str) -> int:
        """Get current queue position for a job (0 = processing now)"""
        if self._current_job and self._current_job.job_id == job_id:
            return 0
        return self._job_positions.get(job_id, -1)
    
    def get_status(self) -> dict:
        """Get queue status"""
        return {
            'queue_size': self._queue.qsize(),
            'currently_processing': self._current_job.job_id if self._current_job else None,
            'processed_count': self._processed_count,
            'worker_alive': self._worker_thread.is_alive() if self._worker_thread else False
        }
    
    def _worker_loop(self):
        """Background worker that processes jobs one at a time"""
        logger.info("[QUEUE] Worker thread started")
        
        while self._running:
            try:
                # Wait for a job (timeout allows checking _running flag)
                try:
                    job = self._queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                self._current_job = job
                logger.info(f"[QUEUE] Processing job {job.job_id}")
                
                try:
                    # Execute the job function
                    job.func(*job.args, **job.kwargs)
                    self._processed_count += 1
                    logger.info(f"[QUEUE] Job {job.job_id} completed")
                except Exception as e:
                    logger.error(f"[QUEUE] Job {job.job_id} failed: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                finally:
                    self._current_job = None
                    if job.job_id in self._job_positions:
                        del self._job_positions[job_id]
                    self._queue.task_done()
                    self._update_positions()
                    
            except Exception as e:
                logger.error(f"[QUEUE] Worker error: {e}")
    
    def _update_positions(self):
        """Update position tracking after a job completes"""
        # Positions shift down as jobs complete
        for job_id in list(self._job_positions.keys()):
            if self._job_positions[job_id] > 0:
                self._job_positions[job_id] -= 1


# Global queue instance
job_queue = JobQueue()


# =============================================================================
# INTELLIGENCE ANALYSIS HELPER
# =============================================================================

def run_intelligence_analysis(project: str, handler, job_id: str) -> dict:
    """
    Run intelligence analysis on uploaded data.
    
    This is the Phase 3 Universal Analysis Engine integration.
    Runs Tier 1 (instant) and Tier 2 (fast) analysis.
    
    Returns summary of findings, tasks, and alerts.
    """
    if not INTELLIGENCE_AVAILABLE:
        logger.warning("[INTELLIGENCE] Intelligence module not available, skipping analysis")
        return None
    
    try:
        ProcessingJobModel.update_progress(job_id, 72, "Running intelligence analysis...")
        
        intelligence = ProjectIntelligenceService(project, handler)
        analysis = intelligence.analyze(tiers=[AnalysisTier.TIER_1, AnalysisTier.TIER_2])
        
        if 'error' in analysis:
            logger.warning(f"[INTELLIGENCE] Analysis returned error: {analysis.get('error')}")
            return None
        
        # Extract summary
        findings_count = len(analysis.get('findings', []))
        tasks_count = analysis.get('tasks', {}).get('total', 0)
        critical_count = analysis.get('findings_summary', {}).get('critical', 0)
        warning_count = analysis.get('findings_summary', {}).get('warning', 0)
        lookups_count = len(analysis.get('lookups', []))
        relationships_count = len(analysis.get('structure', {}).get('relationships', []))
        
        intelligence_summary = {
            'findings': findings_count,
            'tasks': tasks_count,
            'critical': critical_count,
            'warning': warning_count,
            'lookups_detected': lookups_count,
            'relationships_detected': relationships_count,
            'analyzed_at': analysis.get('analyzed_at'),
            'analysis_time_seconds': analysis.get('analysis_time_seconds')
        }
        
        # Build status message
        if critical_count > 0:
            status_msg = f"⚠️ Intelligence: {critical_count} critical, {warning_count} warnings, {tasks_count} tasks"
        elif findings_count > 0:
            status_msg = f"✅ Intelligence: {findings_count} findings, {tasks_count} tasks"
        else:
            status_msg = f"✅ Intelligence: Data looks clean"
        
        ProcessingJobModel.update_progress(job_id, 78, status_msg)
        logger.info(f"[INTELLIGENCE] Analysis complete: {findings_count} findings, {tasks_count} tasks, {critical_count} critical")
        
        return intelligence_summary
        
    except Exception as e:
        logger.warning(f"[INTELLIGENCE] Analysis failed: {e}")
        import traceback
        logger.warning(traceback.format_exc())
        return None


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
    Background processing function - runs in separate thread
    
    This is where all the heavy lifting happens:
    1. For Excel/CSV: Store in DuckDB (structured queries)
    2. Run intelligence analysis (Phase 3)
    3. For TABULAR PDFs: Smart detection → DuckDB + ChromaDB
    4. For TEXT PDFs/Docs: Extract text, chunk, embed in ChromaDB
    5. Update job status throughout
    """
    try:
        logger.warning(f"[BACKGROUND] === STARTING JOB {job_id} ===")
        logger.warning(f"[BACKGROUND] filename={filename}, project={project}, project_id={project_id}")
        
        file_ext = filename.split('.')[-1].lower()
        logger.warning(f"[BACKGROUND] Detected file extension: '{file_ext}'")
        
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
                
                # =====================================================
                # INTELLIGENCE ANALYSIS - Phase 3
                # Run Tier 1 + 2 analysis on uploaded data
                # =====================================================
                intelligence_summary = run_intelligence_analysis(project, handler, job_id)
                if intelligence_summary:
                    result['intelligence'] = intelligence_summary
                
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
                                'functional_area': functional_area,
                                'intelligence': intelligence_summary
                            }
                        )
                        logger.info(f"[BACKGROUND] Saved structured data metadata to database")
                    except Exception as e:
                        logger.warning(f"[BACKGROUND] Could not save to documents table: {e}")
                
                # Register in document registry
                try:
                    from utils.database.models import DocumentRegistryModel
                    
                    # Determine usage type
                    filename_lower = filename.lower()
                    is_global = project.lower() in ['global', '__global__', 'global/universal']
                    
                    # Check if this is a playbook source file
                    is_playbook = any(kw in filename_lower for kw in ['year-end', 'yearend', 'year_end', 'checklist'])
                    
                    if is_playbook and is_global:
                        usage_type = DocumentRegistryModel.USAGE_PLAYBOOK_SOURCE
                    elif is_global:
                        usage_type = DocumentRegistryModel.USAGE_TEMPLATE
                    else:
                        usage_type = DocumentRegistryModel.USAGE_STRUCTURED_DATA
                    
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
                        metadata={
                            'project_name': project,
                            'functional_area': functional_area,
                            'file_size': file_size,
                            'intelligence': intelligence_summary
                        }
                    )
                    logger.info(f"[BACKGROUND] Registered document in registry: {filename} ({usage_type})")
                except Exception as e:
                    logger.warning(f"[BACKGROUND] Could not register document: {e}")
                
                # Cleanup
                ProcessingJobModel.update_progress(job_id, 90, "Cleaning up...")
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except:
                        pass
                
                # Build completion result
                completion_result = {
                    'filename': filename,
                    'type': 'structured',
                    'tables_created': tables_created,
                    'total_rows': total_rows,
                    'project': project,
                    'functional_area': functional_area
                }
                
                # Add intelligence summary to completion
                if intelligence_summary:
                    completion_result['intelligence'] = intelligence_summary
                
                # Complete!
                ProcessingJobModel.complete(job_id, completion_result)
                
                logger.info(f"[BACKGROUND] Structured data job {job_id} completed!")
                return
                
            except Exception as e:
                # XLSX/CSV should NEVER go to ChromaDB - structured data doesn't chunk well
                logger.error(f"[BACKGROUND] Structured storage failed: {e}")
                ProcessingJobModel.fail(job_id, f"Failed to process structured data: {str(e)}")
                
                # Cleanup
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except:
                        pass
                return  # Do NOT fall through to RAG
        
        # =================================================================
        # ROUTE 1.5: SMART PDF ROUTING - Check if PDF is tabular
        # =================================================================
        logger.warning(f"[BACKGROUND] Route 1.5 check: file_ext='{file_ext}', SMART_PDF_AVAILABLE={SMART_PDF_AVAILABLE}")
        
        if file_ext == 'pdf' and SMART_PDF_AVAILABLE:
            ProcessingJobModel.update_progress(job_id, 5, "Analyzing PDF structure...")
            logger.warning(f"[BACKGROUND] >>> ENTERING SMART PDF ROUTE for {filename}")
            
            try:
                def status_callback(msg, progress=None):
                    if progress:
                        # Map smart PDF progress (0-100) to our range (5-50)
                        mapped = 5 + int(progress * 0.45)
                        ProcessingJobModel.update_progress(job_id, mapped, msg)
                    else:
                        logger.warning(f"[SMART-PDF] {msg}")
                
                logger.warning(f"[BACKGROUND] Calling process_pdf_intelligently...")
                
                # Run smart PDF analysis and routing
                pdf_result = process_pdf_intelligently(
                    file_path=file_path,
                    project=project,
                    filename=filename,
                    project_id=project_id,
                    status_callback=status_callback
                )
                
                logger.warning(f"[BACKGROUND] Smart PDF result: success={pdf_result.get('success')}, storage={pdf_result.get('storage_used', [])}")
                
                if pdf_result.get('error'):
                    logger.warning(f"[BACKGROUND] Smart PDF error: {pdf_result.get('error')}")
                
                # Check if DuckDB storage was successful
                duckdb_success = 'duckdb' in pdf_result.get('storage_used', [])
                
                if duckdb_success:
                    # Run intelligence analysis on PDF tables
                    try:
                        handler = get_structured_handler()
                        intelligence_summary = run_intelligence_analysis(project, handler, job_id)
                        if intelligence_summary:
                            pdf_result['intelligence'] = intelligence_summary
                    except Exception as int_e:
                        logger.warning(f"[BACKGROUND] PDF intelligence analysis failed: {int_e}")
                    
                    # Register in document registry
                    try:
                        from utils.database.models import DocumentRegistryModel
                        
                        duckdb_result = pdf_result.get('duckdb_result', {})
                        analysis = pdf_result.get('analysis', {})
                        
                        DocumentRegistryModel.register(
                            filename=filename,
                            file_type='pdf',
                            storage_type=DocumentRegistryModel.STORAGE_DUCKDB,  # Primary storage
                            usage_type=DocumentRegistryModel.USAGE_STRUCTURED_DATA,
                            project_id=project_id,
                            is_global=project.lower() in ['global', '__global__'],
                            duckdb_tables=duckdb_result.get('tables_created', []),
                            row_count=duckdb_result.get('total_rows', 0),
                            metadata={
                                'project_name': project,
                                'functional_area': functional_area,
                                'file_size': file_size,
                                'pdf_analysis': {
                                    'is_tabular': analysis.get('is_tabular', False),
                                    'confidence': analysis.get('confidence', 0),
                                    'table_pages': len(analysis.get('table_pages', []))
                                },
                                'intelligence': pdf_result.get('intelligence')
                            }
                        )
                        logger.info(f"[BACKGROUND] Registered PDF in registry with DuckDB tables")
                    except Exception as e:
                        logger.warning(f"[BACKGROUND] Could not register PDF: {e}")
                
                # Get text content for ChromaDB (either from analysis or re-extract)
                chromadb_result = pdf_result.get('chromadb_result', {})
                text = chromadb_result.get('text_content', '')
                
                if not text:
                    # Fallback: extract text normally
                    text = extract_text(file_path)
                
                # If we got DuckDB storage but no text, we can complete here
                if duckdb_success and (not text or len(text.strip()) < 100):
                    ProcessingJobModel.update_progress(job_id, 90, "Cleaning up...")
                    if file_path and os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                        except:
                            pass
                    
                    ProcessingJobModel.complete(job_id, {
                        'filename': filename,
                        'type': 'smart_pdf',
                        'storage': pdf_result.get('storage_used', []),
                        'duckdb_rows': pdf_result.get('duckdb_result', {}).get('total_rows', 0),
                        'project': project,
                        'intelligence': pdf_result.get('intelligence')
                    })
                    logger.info(f"[BACKGROUND] Smart PDF job {job_id} completed (DuckDB only)")
                    return
                
                # Check if smart_pdf_analyzer says to skip ChromaDB (large tabular PDFs)
                skip_chromadb = 'chromadb' not in pdf_result.get('storage_used', [])
                
                if skip_chromadb and duckdb_success:
                    # Large tabular PDF - DuckDB only, skip ChromaDB
                    ProcessingJobModel.update_progress(job_id, 90, "Cleaning up (skipping semantic search for large table)...")
                    if file_path and os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                        except:
                            pass
                    
                    ProcessingJobModel.complete(job_id, {
                        'filename': filename,
                        'type': 'smart_pdf_tabular_only',
                        'storage': pdf_result.get('storage_used', []),
                        'duckdb_rows': pdf_result.get('duckdb_result', {}).get('total_rows', 0),
                        'project': project,
                        'note': 'ChromaDB skipped - large tabular PDF',
                        'intelligence': pdf_result.get('intelligence')
                    })
                    logger.info(f"[BACKGROUND] Smart PDF job {job_id} completed (DuckDB only - large tabular)")
                    return
                
                # Continue with ChromaDB using extracted text
                # (Fall through to ROUTE 2 below, but we already have text)
                if text:
                    logger.warning(f"[BACKGROUND] Smart PDF: continuing to ChromaDB with {len(text)} chars")
                    ProcessingJobModel.update_progress(job_id, 50, f"Adding to semantic search ({len(text):,} chars)...")
                
            except Exception as e:
                logger.warning(f"[BACKGROUND] !!! Smart PDF EXCEPTION: {e}")
                import traceback
                logger.warning(traceback.format_exc())
                text = None  # Force re-extraction below
        else:
            text = None
        
        # =================================================================
        # ROUTE 1.75: DOCX/TXT CONTENT ANALYSIS - Route by content, not extension
        # =================================================================
        if file_ext in ['docx', 'txt', 'md'] and DOCUMENT_ANALYZER_AVAILABLE and STRUCTURED_HANDLER_AVAILABLE:
            logger.warning(f"[BACKGROUND] Route 1.75: Analyzing {file_ext} content structure...")
            ProcessingJobModel.update_progress(job_id, 5, "Analyzing document structure...")
            
            try:
                # Extract text first
                text = extract_text(file_path)
                
                if text and len(text.strip()) > 100:
                    # Analyze content structure
                    analyzer = DocumentAnalyzer()
                    analysis = analyzer.analyze(text, filename, file_ext)
                    
                    logger.warning(f"[BACKGROUND] Content analysis: structure={analysis.structure.value}, "
                                   f"patterns={analysis.patterns}")
                    
                    # If content is TABULAR, route to DuckDB
                    if analysis.structure == DocumentStructure.TABULAR:
                        logger.warning(f"[BACKGROUND] >>> TABULAR content detected in {file_ext}! Routing to DuckDB")
                        ProcessingJobModel.update_progress(job_id, 15, "Detected tabular data - converting for SQL queries...")
                        
                        try:
                            # Convert text to structured format and store in DuckDB
                            handler = get_structured_handler()
                            
                            # Parse the tabular content
                            # Try to detect delimiter and parse as table
                            lines = [l for l in text.strip().split('\n') if l.strip()]
                            
                            if lines:
                                # Detect delimiter
                                first_lines = '\n'.join(lines[:10])
                                if '\t' in first_lines:
                                    delimiter = '\t'
                                elif '|' in first_lines:
                                    delimiter = '|'
                                elif ',' in first_lines and first_lines.count(',') > 3:
                                    delimiter = ','
                                else:
                                    delimiter = None
                                
                                if delimiter:
                                    # Parse as delimited data
                                    import io
                                    
                                    # Clean up pipe-delimited format
                                    if delimiter == '|':
                                        cleaned_lines = []
                                        for line in lines:
                                            # Remove leading/trailing pipes and strip
                                            cleaned = line.strip().strip('|').strip()
                                            if cleaned and not cleaned.startswith('-'):  # Skip separator lines
                                                cleaned_lines.append(cleaned)
                                        text_for_parsing = '\n'.join(cleaned_lines)
                                        delimiter = '|'
                                    else:
                                        text_for_parsing = '\n'.join(lines)
                                    
                                    try:
                                        df = pd.read_csv(io.StringIO(text_for_parsing), sep=delimiter, skipinitialspace=True)
                                        
                                        if len(df) > 0 and len(df.columns) > 1:
                                            # Save as temp CSV and store
                                            temp_csv = f"/tmp/{job_id}_converted.csv"
                                            df.to_csv(temp_csv, index=False)
                                            
                                            result = handler.store_csv(temp_csv, project, f"{filename}_extracted.csv")
                                            
                                            # Cleanup temp file
                                            try:
                                                os.remove(temp_csv)
                                            except:
                                                pass
                                            
                                            ProcessingJobModel.update_progress(job_id, 70, 
                                                f"Created table with {result.get('row_count', 0):,} rows")
                                            
                                            # Run intelligence analysis
                                            intelligence_summary = run_intelligence_analysis(project, handler, job_id)
                                            
                                            # Register in document registry
                                            try:
                                                from utils.database.models import DocumentRegistryModel
                                                
                                                DocumentRegistryModel.register(
                                                    filename=filename,
                                                    file_type=file_ext,
                                                    storage_type=DocumentRegistryModel.STORAGE_DUCKDB,
                                                    usage_type=DocumentRegistryModel.USAGE_STRUCTURED_DATA,
                                                    project_id=project_id,
                                                    is_global=project.lower() in ['global', '__global__'],
                                                    row_count=result.get('row_count', 0),
                                                    metadata={
                                                        'project_name': project,
                                                        'functional_area': functional_area,
                                                        'original_type': file_ext,
                                                        'detected_structure': 'tabular',
                                                        'delimiter': delimiter,
                                                        'intelligence': intelligence_summary
                                                    }
                                                )
                                            except Exception as reg_e:
                                                logger.warning(f"[BACKGROUND] Could not register: {reg_e}")
                                            
                                            # Cleanup and complete
                                            if file_path and os.path.exists(file_path):
                                                try:
                                                    os.remove(file_path)
                                                except:
                                                    pass
                                            
                                            ProcessingJobModel.complete(job_id, {
                                                'filename': filename,
                                                'type': 'structured_from_text',
                                                'original_format': file_ext,
                                                'rows': result.get('row_count', 0),
                                                'project': project,
                                                'intelligence': intelligence_summary
                                            })
                                            
                                            logger.info(f"[BACKGROUND] Converted {file_ext} to structured data!")
                                            return
                                    
                                    except Exception as parse_e:
                                        logger.warning(f"[BACKGROUND] Could not parse as delimited: {parse_e}")
                                
                                # If delimiter parsing failed, try Word table extraction for DOCX
                                if file_ext == 'docx':
                                    try:
                                        doc = docx.Document(file_path)
                                        tables_data = []
                                        
                                        for table in doc.tables:
                                            table_rows = []
                                            for row in table.rows:
                                                row_data = [cell.text.strip() for cell in row.cells]
                                                table_rows.append(row_data)
                                            
                                            if table_rows:
                                                tables_data.append(table_rows)
                                        
                                        if tables_data:
                                            # Convert first table to DataFrame
                                            first_table = tables_data[0]
                                            if len(first_table) > 1:
                                                df = pd.DataFrame(first_table[1:], columns=first_table[0])
                                                
                                                temp_csv = f"/tmp/{job_id}_docx_table.csv"
                                                df.to_csv(temp_csv, index=False)
                                                
                                                result = handler.store_csv(temp_csv, project, f"{filename}_table.csv")
                                                
                                                try:
                                                    os.remove(temp_csv)
                                                except:
                                                    pass
                                                
                                                # Run intelligence analysis
                                                intelligence_summary = run_intelligence_analysis(project, handler, job_id)
                                                
                                                # Complete as structured
                                                if file_path and os.path.exists(file_path):
                                                    try:
                                                        os.remove(file_path)
                                                    except:
                                                        pass
                                                
                                                ProcessingJobModel.complete(job_id, {
                                                    'filename': filename,
                                                    'type': 'structured_from_docx_table',
                                                    'tables_found': len(tables_data),
                                                    'rows': result.get('row_count', 0),
                                                    'project': project,
                                                    'intelligence': intelligence_summary
                                                })
                                                
                                                logger.info(f"[BACKGROUND] Extracted {len(tables_data)} tables from DOCX!")
                                                return
                                    
                                    except Exception as docx_e:
                                        logger.warning(f"[BACKGROUND] DOCX table extraction failed: {docx_e}")
                        
                        except Exception as struct_e:
                            logger.warning(f"[BACKGROUND] Structured conversion failed: {struct_e}, continuing to ChromaDB")
                    
                    # If we get here, content is not tabular or conversion failed
                    # Continue to Route 2 with the already-extracted text
                    logger.warning(f"[BACKGROUND] Content is {analysis.structure.value}, continuing to ChromaDB")
                    
            except Exception as analyze_e:
                logger.warning(f"[BACKGROUND] Content analysis failed: {analyze_e}, continuing to ChromaDB")
                text = None  # Force re-extraction
        
        # ROUTE 2: UNSTRUCTURED DATA (PDF/Word/Text) → ChromaDB
        logger.warning(f"[BACKGROUND] Route 2 check: text is {'set' if text else 'None'}")
        if text is None:
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
        
        # Register in document registry
        try:
            from utils.database.models import DocumentRegistryModel
            
            filename_lower = filename.lower()
            is_global = project.lower() in ['global', '__global__', 'global/universal']
            
            DocumentRegistryModel.register(
                filename=filename,
                file_type=file_ext,
                storage_type=DocumentRegistryModel.STORAGE_CHROMADB,
                usage_type=DocumentRegistryModel.USAGE_RAG_KNOWLEDGE,
                project_id=project_id if not is_global else None,
                is_global=is_global,
                chunk_count=len(text) // 500,  # Approximate
                metadata={
                    'project_name': project,
                    'functional_area': functional_area,
                    'file_size': file_size,
                    'char_count': len(text)
                }
            )
            logger.info(f"[BACKGROUND] Registered document in registry")
        except Exception as e:
            logger.warning(f"[BACKGROUND] Could not register document: {e}")
        
        # Cleanup
        ProcessingJobModel.update_progress(job_id, 95, "Cleaning up...")
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        
        # Complete!
        ProcessingJobModel.complete(job_id, {
            'filename': filename,
            'type': 'unstructured',
            'chunks_created': len(text) // 500,
            'project': project,
            'functional_area': functional_area
        })
        
        logger.info(f"[BACKGROUND] Job {job_id} completed!")
        
    except Exception as e:
        error_msg = f"Processing failed: {str(e)}"
        logger.error(f"[BACKGROUND] {error_msg}")
        logger.error(traceback.format_exc())
        ProcessingJobModel.fail(job_id, error_msg)
        
        # Cleanup on failure too
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
    Upload a file for async processing
    
    Returns immediately with job_id for status polling
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # Check file extension
        allowed_extensions = ['pdf', 'docx', 'doc', 'txt', 'md', 'xlsx', 'xls', 'csv']
        ext = file.filename.split('.')[-1].lower()
        if ext not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"File type '{ext}' not supported. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Look up project to get UUID
        project_id = None
        try:
            # Handle global project
            if project.lower() in ['global', '__global__', 'global/universal']:
                project_id = None
                logger.info(f"[UPLOAD] Using GLOBAL project (no project_id)")
            else:
                # Check if project is already a UUID (frontend might send ID directly)
                import re
                uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
                if re.match(uuid_pattern, project.lower()):
                    # It's a UUID - verify it exists and use it directly
                    project_record = ProjectModel.get_by_id(project)
                    if project_record:
                        project_id = project
                        logger.info(f"[UPLOAD] Using project UUID directly: {project_id}")
                    else:
                        logger.warning(f"[UPLOAD] Project UUID '{project}' not found in database")
                else:
                    # It's a name - look up by name
                    project_record = ProjectModel.get_by_name(project)
                    if project_record:
                        project_id = project_record.get('id')
                        logger.info(f"[UPLOAD] Found project '{project}' with id: {project_id}")
                    else:
                        logger.warning(f"[UPLOAD] Project '{project}' not found in database")
        except Exception as e:
            logger.warning(f"[UPLOAD] Could not look up project: {e}")
        
        # Save file temporarily
        file_path = f"/tmp/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
        
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        # Write to temp file
        with open(file_path, 'wb') as f:
            f.write(content)
        
        logger.info(f"[UPLOAD] Saved {file.filename} ({file_size} bytes) to {file_path}")
        
        # Create job record
        job_result = ProcessingJobModel.create(
            job_type='upload',
            project_id=project_id,
            input_data={'filename': file.filename, 'functional_area': functional_area, 'project_name': project}
        )
        
        if not job_result:
            raise HTTPException(status_code=500, detail="Failed to create processing job")
        
        job_id = job_result['id']
        
        logger.info(f"[UPLOAD] Created job {job_id} for project_id={project_id}")
        
        # Queue for background processing (sequential!)
        queue_info = job_queue.enqueue(
            job_id,
            process_file_background,
            (job_id, file_path, file.filename, project, project_id, functional_area, file_size)
        )
        
        return {
            "job_id": job_id,
            "status": "queued",
            "queue_position": queue_info.get('position', 1),
            "queue_size": queue_info.get('queue_size', 1),
            "message": f"File '{file.filename}' queued for processing",
            "project": project,
            "project_id": project_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[UPLOAD] Upload failed: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/upload/queue-status")
async def get_queue_status():
    """Get current queue status"""
    return job_queue.get_status()


@router.get("/upload/status/{job_id}")
async def get_job_status(job_id: str):
    """Get processing status for a specific job"""
    try:
        job = ProcessingJobModel.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Add queue position if still queued
        if job.get('status') in ['pending', 'queued']:
            position = job_queue.get_position(job_id)
            job['queue_position'] = position
        
        return job
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[STATUS] Error getting job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
