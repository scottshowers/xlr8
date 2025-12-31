"""
Smart Router - Unified Upload Endpoint
======================================
Consolidates all upload paths into a single intelligent router.

v1.3 (December 2025):
- FIXED: Reference Library Excel/CSV files now create DuckDB tables
- Standards route now processes: rules extraction + DuckDB tables
- Routing priority fixed: truth_type overrides extension-based routing
- Added 'regulatory' and 'compliance' to standards routing triggers

v1.2 (December 2025 - GET HEALTHY Week 2):
- Now the CANONICAL upload endpoint - duplicate endpoints removed from upload.py and register_extractor.py
- upload.py and register_extractor.py now contain only supporting endpoints
- All upload traffic routes through this file

BEFORE (3 endpoints):
- /api/upload         → general file upload
- /api/standards/upload → reference documents  
- /api/register/upload  → payroll registers

AFTER (1 endpoint):
- /api/upload         → Smart Router decides destination

ROUTING LOGIC:
1. User can specify processing_type explicitly
2. If auto, Smart Router analyzes:
   - truth_type parameter (reference → standards) - HIGHEST PRIORITY
   - Filename patterns (register, payroll → register extractor)
   - File extension (xlsx/csv → structured, pdf → analyze content)
   - Content analysis for PDFs (tabular vs narrative)

BACKWARD COMPATIBILITY:
- /api/standards/upload → routes to smart_upload with processing_type=standards
- /api/register/upload  → routes to smart_upload with processing_type=register
- /api/vacuum/upload    → routes to smart_upload with processing_type=register

v1.1 - Added MetricsService integration for platform analytics

Deploy to: backend/routers/smart_router.py
Then update main.py to use this instead of separate routers.
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Request
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import os
import re
import json
import logging
import tempfile
import shutil
import hashlib
import time

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# PROCESSING TYPE ENUM
# =============================================================================

class ProcessingType(str, Enum):
    AUTO = "auto"               # Smart routing based on content
    REGISTER = "register"       # Force register extractor (payroll PDFs)
    STANDARDS = "standards"     # Force standards processor (reference docs)
    STRUCTURED = "structured"   # Force DuckDB (tabular data)
    SEMANTIC = "semantic"       # Force ChromaDB (text/semantic search)


# =============================================================================
# IMPORTS - Graceful degradation for each processor
# =============================================================================

# Metrics Service (for analytics)
try:
    from utils.metrics_service import MetricsService
    METRICS_AVAILABLE = True
except ImportError:
    try:
        from backend.utils.metrics_service import MetricsService
        METRICS_AVAILABLE = True
    except ImportError:
        METRICS_AVAILABLE = False
        logger.warning("[SMART-ROUTER] MetricsService not available - metrics will not be recorded")

# Registration Service (always needed)
try:
    from utils.registration_service import RegistrationService, RegistrationSource
    REGISTRATION_AVAILABLE = True
except ImportError:
    try:
        from backend.utils.registration_service import RegistrationService, RegistrationSource
        REGISTRATION_AVAILABLE = True
    except ImportError:
        REGISTRATION_AVAILABLE = False
        logger.warning("[SMART-ROUTER] RegistrationService not available")

# Structured Data Handler (DuckDB)
try:
    from utils.structured_data_handler import get_structured_handler
    STRUCTURED_AVAILABLE = True
except ImportError:
    try:
        from backend.utils.structured_data_handler import get_structured_handler
        STRUCTURED_AVAILABLE = True
    except ImportError:
        STRUCTURED_AVAILABLE = False
        logger.warning("[SMART-ROUTER] Structured handler not available")

# RAG Handler (ChromaDB)
try:
    from utils.rag_handler import RAGHandler
    RAG_AVAILABLE = True
except ImportError:
    try:
        from backend.utils.rag_handler import RAGHandler
        RAG_AVAILABLE = True
    except ImportError:
        RAG_AVAILABLE = False
        logger.warning("[SMART-ROUTER] RAG handler not available")

# Smart PDF Analyzer
try:
    from utils.smart_pdf_analyzer import process_pdf_intelligently
    SMART_PDF_AVAILABLE = True
except ImportError:
    try:
        from backend.utils.smart_pdf_analyzer import process_pdf_intelligently
        SMART_PDF_AVAILABLE = True
    except ImportError:
        SMART_PDF_AVAILABLE = False
        logger.warning("[SMART-ROUTER] Smart PDF analyzer not available")

# Standards Processor
try:
    from utils.standards_processor import process_pdf as standards_process_pdf
    from utils.standards_processor import process_text as standards_process_text
    from utils.standards_processor import get_rule_registry
    from utils.standards_processor import StandardsDocument
    STANDARDS_AVAILABLE = True
except ImportError:
    try:
        from backend.utils.standards_processor import process_pdf as standards_process_pdf
        from backend.utils.standards_processor import process_text as standards_process_text
        from backend.utils.standards_processor import get_rule_registry
        from backend.utils.standards_processor import StandardsDocument
        STANDARDS_AVAILABLE = True
    except ImportError:
        STANDARDS_AVAILABLE = False
        StandardsDocument = None
        logger.warning("[SMART-ROUTER] Standards processor not available")

# Register Extractor
try:
    from routers.register_extractor import get_extractor, create_job, process_extraction_job
    REGISTER_AVAILABLE = True
except ImportError:
    try:
        from backend.routers.register_extractor import get_extractor, create_job, process_extraction_job
        REGISTER_AVAILABLE = True
    except ImportError:
        REGISTER_AVAILABLE = False
        logger.warning("[SMART-ROUTER] Register extractor not available")

# Processing Job Model
try:
    from utils.database.models import ProcessingJobModel, ProjectModel, DocumentModel
    MODELS_AVAILABLE = True
except ImportError:
    try:
        from backend.utils.database.models import ProcessingJobModel, ProjectModel, DocumentModel
        MODELS_AVAILABLE = True
    except ImportError:
        MODELS_AVAILABLE = False
        logger.warning("[SMART-ROUTER] Database models not available")

# Text extraction
try:
    from utils.text_extraction import extract_text
    TEXT_EXTRACTION_AVAILABLE = True
except ImportError:
    try:
        from backend.utils.text_extraction import extract_text
        TEXT_EXTRACTION_AVAILABLE = True
    except ImportError:
        TEXT_EXTRACTION_AVAILABLE = False
        logger.warning("[SMART-ROUTER] Text extraction not available")


# =============================================================================
# ROUTING DETECTION
# =============================================================================

# Filename patterns that indicate register/payroll documents
REGISTER_PATTERNS = [
    r'register',
    r'payroll',
    r'pay[-_]?reg',
    r'pr[-_]?report',
    r'earnings[-_]?report',
    r'paycheck',
]

# Filename patterns that indicate standards/reference documents
STANDARDS_PATTERNS = [
    r'standard',
    r'regulation',
    r'compliance',
    r'policy',
    r'handbook',
    r'guide',
    r'reference',
    r'sop',
    r'procedure',
]


def detect_processing_type(
    filename: str,
    extension: str,
    truth_type: Optional[str] = None,
    content_sample: Optional[str] = None
) -> ProcessingType:
    """
    Detect the appropriate processing type based on file characteristics.
    
    Priority:
    1. truth_type parameter (explicit user intent) - HIGHEST PRIORITY
    2. Filename pattern matching
    3. Extension-based routing (xlsx/csv → structured) 
    4. Content analysis (for PDFs)
    5. Default to auto/semantic
    
    NOTE: truth_type takes precedence over extension. This allows Reference Library
    uploads of Excel files to go through standards processing (with DuckDB added).
    """
    filename_lower = filename.lower()
    
    # 1. Explicit truth_type - HIGHEST PRIORITY
    # User's explicit intent overrides extension-based routing
    if truth_type:
        if truth_type.lower() in ['reference', 'standards', 'best_practice', 'regulatory', 'compliance']:
            logger.info(f"[SMART-ROUTER] Routing to STANDARDS based on truth_type={truth_type}")
            return ProcessingType.STANDARDS
        elif truth_type.lower() in ['reality', 'configuration']:
            logger.info(f"[SMART-ROUTER] Routing to STRUCTURED based on truth_type={truth_type}")
            return ProcessingType.STRUCTURED
    
    # 2. Filename pattern matching (before extension check)
    for pattern in REGISTER_PATTERNS:
        if re.search(pattern, filename_lower):
            logger.info(f"[SMART-ROUTER] Routing to REGISTER based on filename pattern: {pattern}")
            return ProcessingType.REGISTER
    
    for pattern in STANDARDS_PATTERNS:
        if re.search(pattern, filename_lower):
            logger.info(f"[SMART-ROUTER] Routing to STANDARDS based on filename pattern: {pattern}")
            return ProcessingType.STANDARDS
    
    # 3. Extension-based routing (only if no truth_type specified)
    if extension in ['xlsx', 'xls', 'csv']:
        logger.info(f"[SMART-ROUTER] Routing to STRUCTURED based on extension={extension}")
        return ProcessingType.STRUCTURED
    
    # 4. PDF content analysis (if sample provided)
    if extension == 'pdf' and content_sample:
        # Quick heuristics for tabular content
        if _looks_like_register(content_sample):
            logger.info(f"[SMART-ROUTER] Routing to REGISTER based on content analysis")
            return ProcessingType.REGISTER
    
    # 5. Default: Let Smart PDF analyzer decide for PDFs, semantic for others
    if extension == 'pdf':
        logger.info(f"[SMART-ROUTER] Defaulting to AUTO for PDF (will use Smart PDF Analyzer)")
        return ProcessingType.AUTO
    
    logger.info(f"[SMART-ROUTER] Defaulting to SEMANTIC for {extension}")
    return ProcessingType.SEMANTIC


def _looks_like_register(text_sample: str) -> bool:
    """Quick heuristic to detect if content looks like a payroll register."""
    text_lower = text_sample.lower()
    
    # Look for payroll-specific terms
    payroll_terms = ['gross pay', 'net pay', 'earnings', 'deductions', 'taxes', 
                     'employee id', 'check date', 'pay period', 'federal tax',
                     'social security', 'medicare', 'fica']
    
    matches = sum(1 for term in payroll_terms if term in text_lower)
    return matches >= 3  # At least 3 payroll terms = likely a register


# =============================================================================
# UNIFIED UPLOAD ENDPOINT
# =============================================================================

@router.post("/upload")
async def smart_upload(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    project: str = Form(...),
    # Common parameters
    functional_area: Optional[str] = Form(None),
    truth_type: Optional[str] = Form(None),
    content_domain: Optional[str] = Form(None),
    # Routing control
    processing_type: str = Form(default="auto"),
    # Register-specific (passed through if register route)
    max_pages: int = Form(default=0),
    use_textract: bool = Form(default=False),
    vendor_type: str = Form(default="unknown"),
    # Standards-specific (passed through if standards route)
    domain: str = Form(default="general"),
    title: Optional[str] = Form(None),
    # Async control
    async_mode: bool = Form(default=True),
):
    """
    Smart Upload Router - Single entry point for all file uploads.
    
    Processing Types:
    - auto: Smart detection based on file characteristics
    - register: Force Register Extractor (payroll PDFs)
    - standards: Force Standards Processor (reference docs)
    - structured: Force DuckDB storage (tabular data)
    - semantic: Force ChromaDB storage (text/semantic search)
    
    The router analyzes the file and routes to the appropriate processor,
    ensuring consistent registration and lineage tracking regardless of path.
    """
    
    # =================================================================
    # VALIDATE INPUT
    # =================================================================
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    filename = file.filename
    extension = filename.split('.')[-1].lower()
    
    allowed_extensions = ['pdf', 'docx', 'doc', 'txt', 'md', 'xlsx', 'xls', 'csv']
    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{extension}' not supported. Allowed: {', '.join(allowed_extensions)}"
        )
    
    logger.warning(f"[SMART-ROUTER] === UPLOAD: {filename} ===")
    logger.warning(f"[SMART-ROUTER] project={project}, processing_type={processing_type}, truth_type={truth_type}")
    
    # =================================================================
    # EXTRACT USER INFO
    # =================================================================
    uploaded_by_id = None
    uploaded_by_email = None
    
    try:
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            try:
                import base64
                payload = token.split('.')[1]
                payload += '=' * (4 - len(payload) % 4)
                decoded = json.loads(base64.urlsafe_b64decode(payload))
                uploaded_by_id = decoded.get('sub')
                uploaded_by_email = decoded.get('email')
            except Exception:
                pass
        
        if not uploaded_by_id:
            uploaded_by_id = request.headers.get('X-User-Id')
            uploaded_by_email = request.headers.get('X-User-Email')
    except Exception as e:
        logger.warning(f"[SMART-ROUTER] Could not extract user info: {e}")
    
    # =================================================================
    # SAVE FILE TEMPORARILY
    # =================================================================
    content = await file.read()
    file_size = len(content)
    file_hash = hashlib.sha256(content).hexdigest()
    
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, filename)
    
    with open(file_path, 'wb') as f:
        f.write(content)
    
    logger.warning(f"[SMART-ROUTER] Saved {file_size} bytes to {file_path}")
    
    # =================================================================
    # DETECT ROUTING
    # =================================================================
    try:
        proc_type = ProcessingType(processing_type.lower())
    except ValueError:
        proc_type = ProcessingType.AUTO
    
    if proc_type == ProcessingType.AUTO:
        # Smart detection
        content_sample = None
        if extension == 'pdf' and TEXT_EXTRACTION_AVAILABLE:
            try:
                # Quick sample from first page
                content_sample = extract_text(file_path)[:5000]
            except Exception:
                pass
        
        proc_type = detect_processing_type(filename, extension, truth_type, content_sample)
    
    logger.warning(f"[SMART-ROUTER] Routing decision: {proc_type.value}")
    
    # =================================================================
    # RESOLVE PROJECT ID
    # =================================================================
    project_id = None
    if MODELS_AVAILABLE:
        try:
            global_names = ['global', '__global__', 'global/universal', 'reference library', '__standards__']
            if project.lower() in global_names:
                project_id = None
            else:
                uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
                if re.match(uuid_pattern, project.lower()):
                    project_record = ProjectModel.get_by_id(project)
                    if project_record:
                        project_id = project
                else:
                    project_record = ProjectModel.get_by_name(project)
                    if project_record:
                        project_id = project_record.get('id')
        except Exception as e:
            logger.warning(f"[SMART-ROUTER] Could not resolve project: {e}")
    
    # =================================================================
    # ROUTE TO PROCESSOR (with metrics)
    # =================================================================
    
    route_start = time.time()
    route_name = proc_type.value
    result = None
    success = False
    error_msg = None
    
    try:
        if proc_type == ProcessingType.REGISTER:
            result = await _route_to_register(
                background_tasks=background_tasks,
                file_path=file_path,
                filename=filename,
                project_id=project_id,
                max_pages=max_pages,
                use_textract=use_textract,
                vendor_type=vendor_type,
                async_mode=async_mode,
                temp_dir=temp_dir
            )
            route_name = 'register'
        
        elif proc_type == ProcessingType.STANDARDS:
            result = await _route_to_standards(
                file_path=file_path,
                filename=filename,
                content=content,
                file_size=file_size,
                extension=extension,
                domain=domain,
                title=title,
                temp_dir=temp_dir,
                truth_type=truth_type  # Pass truth_type for correct categorization
            )
            route_name = 'standards'
        
        elif proc_type == ProcessingType.STRUCTURED:
            result = await _route_to_structured(
                background_tasks=background_tasks,
                file_path=file_path,
                filename=filename,
                file_size=file_size,
                file_hash=file_hash,
                extension=extension,
                project=project,
                project_id=project_id,
                functional_area=functional_area,
                truth_type=truth_type,
                content_domain=content_domain,
                uploaded_by_id=uploaded_by_id,
                uploaded_by_email=uploaded_by_email,
                async_mode=async_mode,
                temp_dir=temp_dir
            )
            route_name = 'structured'
        
        else:  # SEMANTIC or AUTO (for non-register PDFs)
            result = await _route_to_semantic(
                background_tasks=background_tasks,
                file_path=file_path,
                filename=filename,
                file_size=file_size,
                file_hash=file_hash,
                extension=extension,
                project=project,
                project_id=project_id,
                functional_area=functional_area,
                truth_type=truth_type,
                content_domain=content_domain,
                uploaded_by_id=uploaded_by_id,
                uploaded_by_email=uploaded_by_email,
                async_mode=async_mode,
                temp_dir=temp_dir
            )
            route_name = 'semantic'
        
        # Check success from result
        success = result.get('success', True) if isinstance(result, dict) else True
        
    except Exception as e:
        # Cleanup on error
        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.error(f"[SMART-ROUTER] Routing failed: {e}")
        error_msg = str(e)
        
        # Record error metric
        if METRICS_AVAILABLE:
            duration_ms = int((time.time() - route_start) * 1000)
            MetricsService.record_upload(
                processor=route_name,
                filename=filename,
                duration_ms=duration_ms,
                success=False,
                project_id=project_id,
                file_size_bytes=file_size,
                error_message=error_msg
            )
        
        raise HTTPException(status_code=500, detail=str(e))
    
    # Record success metric
    if METRICS_AVAILABLE and result:
        duration_ms = int((time.time() - route_start) * 1000)
        MetricsService.record_upload(
            processor=route_name,
            filename=filename,
            duration_ms=duration_ms,
            success=success,
            project_id=project_id,
            file_size_bytes=file_size,
            rows_processed=result.get('total_rows') or result.get('row_count'),
            chunks_created=result.get('chunks_added'),
            rules_extracted=result.get('rules_extracted')
        )
    
    return result


# =============================================================================
# ROUTE HANDLERS
# =============================================================================

async def _route_to_register(
    background_tasks: BackgroundTasks,
    file_path: str,
    filename: str,
    project_id: Optional[str],
    max_pages: int,
    use_textract: bool,
    vendor_type: str,
    async_mode: bool,
    temp_dir: str
) -> Dict[str, Any]:
    """Route to Register Extractor for payroll PDFs."""
    
    if not REGISTER_AVAILABLE:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=503, detail="Register extractor not available")
    
    logger.warning(f"[SMART-ROUTER] → REGISTER EXTRACTOR")
    
    ext = get_extractor()
    if not ext.is_available:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return {"success": False, "error": "No LLM configured", "route": "register"}
    
    if async_mode:
        job_id = create_job(filename)
        background_tasks.add_task(
            process_extraction_job,
            job_id, file_path, max_pages, use_textract, project_id,
            vendor_type, None  # customer_id
        )
        
        return {
            "success": True,
            "job_id": job_id,
            "status": "processing",
            "route": "register",
            "message": f"Processing started. Poll /register/job/{job_id} for status."
        }
    else:
        try:
            result = ext.extract(file_path, max_pages=max_pages, use_textract=use_textract, project_id=project_id)
            result['route'] = 'register'
            return result
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


def _extract_text_from_excel(file_path: str) -> str:
    """
    Extract readable text from Excel file for rule processing.
    
    Converts Excel data to a text format suitable for LLM rule extraction.
    Each sheet becomes a section with its data in tabular text format.
    """
    try:
        import pandas as pd
        
        text_parts = []
        
        # Read all sheets
        xlsx = pd.ExcelFile(file_path)
        
        for sheet_name in xlsx.sheet_names:
            try:
                df = pd.read_excel(xlsx, sheet_name=sheet_name)
                
                if df.empty:
                    continue
                
                # Add sheet header
                text_parts.append(f"\n=== SHEET: {sheet_name} ===\n")
                
                # Add column headers
                headers = [str(col) for col in df.columns if not str(col).startswith('Unnamed')]
                if headers:
                    text_parts.append("Columns: " + ", ".join(headers))
                
                # Convert data to readable text (first 500 rows max for rule extraction)
                for idx, row in df.head(500).iterrows():
                    row_text = []
                    for col in df.columns:
                        val = row[col]
                        if pd.notna(val) and str(val).strip():
                            col_name = str(col)
                            if not col_name.startswith('Unnamed'):
                                row_text.append(f"{col_name}: {val}")
                            else:
                                row_text.append(str(val))
                    if row_text:
                        text_parts.append(" | ".join(row_text))
                
            except Exception as sheet_e:
                logger.debug(f"[SMART-ROUTER] Failed to read sheet {sheet_name}: {sheet_e}")
        
        return "\n".join(text_parts)
        
    except ImportError:
        logger.warning("[SMART-ROUTER] pandas not available for Excel text extraction")
        return ""
    except Exception as e:
        logger.warning(f"[SMART-ROUTER] Excel text extraction failed: {e}")
        return ""


async def _route_to_standards(
    file_path: str,
    filename: str,
    content: bytes,
    file_size: int,
    extension: str,
    domain: str,
    title: Optional[str],
    temp_dir: str,
    truth_type: Optional[str] = None  # NEW: Allow explicit truth_type
) -> Dict[str, Any]:
    """Route to Standards Processor for reference documents.
    
    UPDATED: Now also processes Excel/CSV into DuckDB for queryability.
    Reference files get BOTH:
    - Rule extraction (for compliance checking)
    - DuckDB tables (for SQL queries)
    
    FIX v2: Properly extracts text from Excel files (was reading binary as text).
    FIX v3: truth_type parameter for correct categorization (reference/regulatory/compliance).
    """
    
    if not STANDARDS_AVAILABLE:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=503, detail="Standards processor not available")
    
    logger.warning(f"[SMART-ROUTER] → STANDARDS PROCESSOR")
    
    try:
        chunks_added = 0
        tables_created = []
        total_rows = 0
        
        # =====================================================
        # STEP 1: Process Excel/CSV into DuckDB (if applicable)
        # This makes Reference Library files queryable via SQL
        # =====================================================
        if extension in ['xlsx', 'xls', 'csv'] and STRUCTURED_AVAILABLE:
            logger.info(f"[SMART-ROUTER] Standards route: Also processing {extension} into DuckDB")
            try:
                handler = get_structured_handler()
                # Use 'Reference Library' as project name for global scope
                ref_project = 'Reference Library'
                
                if extension == 'csv':
                    struct_result = handler.store_csv(file_path, ref_project, filename)
                    tables_created = [struct_result.get('table_name', filename)]
                    total_rows = struct_result.get('row_count', 0)
                else:
                    struct_result = handler.store_excel(file_path, ref_project, filename)
                    tables_created = struct_result.get('tables_created', [])
                    total_rows = struct_result.get('total_rows', 0)
                
                logger.info(f"[SMART-ROUTER] DuckDB: {len(tables_created)} tables, {total_rows} rows")
            except Exception as struct_e:
                logger.warning(f"[SMART-ROUTER] DuckDB processing failed (continuing with rules): {struct_e}")
        
        # =====================================================
        # STEP 2: Extract text for rule processing
        # FIX: Excel/CSV files need special handling (binary format)
        # =====================================================
        if extension == 'pdf':
            doc = standards_process_pdf(file_path, domain)
            raw_text = getattr(doc, 'raw_text', '') or ''
            if not raw_text and TEXT_EXTRACTION_AVAILABLE:
                raw_text = extract_text(file_path)
        elif extension in ['xlsx', 'xls']:
            # Excel files are binary - extract text properly
            raw_text = _extract_text_from_excel(file_path)
            doc = standards_process_text(raw_text, filename, domain) if raw_text else None
            if not doc:
                # Create empty document if extraction failed
                import hashlib
                doc_id = hashlib.md5(f"{filename}_{datetime.now().isoformat()}".encode()).hexdigest()[:12]
                doc = StandardsDocument(
                    document_id=doc_id,
                    filename=filename,
                    title=title or filename,
                    domain=domain
                )
            logger.info(f"[SMART-ROUTER] Extracted {len(raw_text)} chars from Excel")
        elif extension == 'csv':
            # CSV is text-based, can read directly
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                raw_text = f.read()
            doc = standards_process_text(raw_text, filename, domain)
        elif extension in ['docx', 'doc']:
            # Word docs need proper extraction (NOT plain text)
            if TEXT_EXTRACTION_AVAILABLE:
                raw_text = extract_text(file_path)
                logger.warning(f"[SMART-ROUTER] DOCX text extraction: {len(raw_text) if raw_text else 0} chars")
                doc = standards_process_text(raw_text, filename, domain) if raw_text else None
                if not doc:
                    import hashlib
                    doc_id = hashlib.md5(f"{filename}_{datetime.now().isoformat()}".encode()).hexdigest()[:12]
                    doc = StandardsDocument(
                        document_id=doc_id,
                        filename=filename,
                        title=title or filename,
                        domain=domain
                    )
                logger.warning(f"[SMART-ROUTER] Word doc: {len(raw_text)} chars, {len(doc.rules)} rules extracted")
            else:
                logger.warning(f"[SMART-ROUTER] Cannot extract text from {extension} - text extraction not available")
                import hashlib
                doc_id = hashlib.md5(f"{filename}_{datetime.now().isoformat()}".encode()).hexdigest()[:12]
                doc = StandardsDocument(
                    document_id=doc_id,
                    filename=filename,
                    title=title or filename,
                    domain=domain
                )
                raw_text = ""
        else:
            # Other text files (txt, md, etc.)
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                raw_text = f.read()
            doc = standards_process_text(raw_text, filename, domain)
        
        if title:
            doc.title = title
        
        # Add to rule registry
        registry = get_rule_registry()
        registry.add_document(doc)
        
        logger.warning(f"[SMART-ROUTER] Extracted {len(doc.rules)} rules from {filename}")
        
        # Also add to ChromaDB for semantic search
        if raw_text and len(raw_text.strip()) > 100 and RAG_AVAILABLE:
            try:
                rag = RAGHandler()
                # Use passed truth_type, default to 'reference' for backwards compatibility
                actual_truth_type = truth_type or 'reference'
                metadata = {
                    'source': filename,
                    'filename': filename,
                    'project': '__STANDARDS__',
                    'truth_type': actual_truth_type,
                    'domain': domain,
                    'is_global': True,
                    'document_id': doc.document_id,
                    'rules_extracted': len(doc.rules)
                }
                logger.warning(f"[SMART-ROUTER] Adding to ChromaDB with truth_type={actual_truth_type}")
                chunks_added = rag.add_document(
                    collection_name="documents",
                    text=raw_text,
                    metadata=metadata
                )
                logger.info(f"[SMART-ROUTER] Added {chunks_added} chunks to ChromaDB")
            except Exception as e:
                logger.warning(f"[SMART-ROUTER] ChromaDB chunking failed: {e}")
        
        # Register
        if REGISTRATION_AVAILABLE:
            try:
                RegistrationService.register_standards(
                    filename=filename,
                    document_id=doc.document_id,
                    domain=domain,
                    rules_extracted=len(doc.rules),
                    file_size=file_size,
                    file_type=extension,
                    title=doc.title,
                    page_count=doc.page_count,
                    metadata={
                        'upload_source': 'smart_router', 
                        'chunks_added': chunks_added,
                        'tables_created': tables_created,
                        'total_rows': total_rows
                    }
                )
            except Exception as e:
                logger.warning(f"[SMART-ROUTER] Registration failed: {e}")
        
        return {
            "success": True,
            "route": "standards",
            "filename": filename,
            "rules_extracted": len(doc.rules),
            "chunks_added": chunks_added,
            "document_id": doc.document_id,
            "domain": domain,
            "tables_created": tables_created,
            "total_rows": total_rows
        }
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


async def _route_to_structured(
    background_tasks: BackgroundTasks,
    file_path: str,
    filename: str,
    file_size: int,
    file_hash: str,
    extension: str,
    project: str,
    project_id: Optional[str],
    functional_area: Optional[str],
    truth_type: Optional[str],
    content_domain: Optional[str],
    uploaded_by_id: Optional[str],
    uploaded_by_email: Optional[str],
    async_mode: bool,
    temp_dir: str
) -> Dict[str, Any]:
    """Route to Structured Handler for tabular data."""
    
    if not STRUCTURED_AVAILABLE:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=503, detail="Structured handler not available")
    
    logger.warning(f"[SMART-ROUTER] → STRUCTURED HANDLER (DuckDB)")
    
    if async_mode and MODELS_AVAILABLE:
        # Create job and process in background
        job_result = ProcessingJobModel.create(
            job_type='upload',
            project_id=project_id,
            input_data={
                'filename': filename,
                'functional_area': functional_area,
                'project_name': project,
                'file_hash': file_hash,
                'route': 'structured'
            }
        )
        
        if not job_result:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise HTTPException(status_code=500, detail="Failed to create job")
        
        job_id = job_result['id']
        
        # Import the background processor
        try:
            from routers.upload import process_file_background
        except ImportError:
            from backend.routers.upload import process_file_background
        
        background_tasks.add_task(
            process_file_background,
            job_id, file_path, filename, project, project_id,
            functional_area, file_size, truth_type, content_domain,
            file_hash, uploaded_by_id, uploaded_by_email
        )
        
        return {
            "success": True,
            "job_id": job_id,
            "status": "queued",
            "route": "structured",
            "message": f"File queued for structured processing"
        }
    else:
        # Sync processing
        try:
            handler = get_structured_handler()
            
            if extension == 'csv':
                result = handler.store_csv(file_path, project, filename)
            else:
                result = handler.store_excel(file_path, project, filename)
            
            return {
                "success": True,
                "route": "structured",
                "filename": filename,
                "tables_created": result.get('tables_created', []),
                "total_rows": result.get('total_rows', 0)
            }
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


async def _route_to_semantic(
    background_tasks: BackgroundTasks,
    file_path: str,
    filename: str,
    file_size: int,
    file_hash: str,
    extension: str,
    project: str,
    project_id: Optional[str],
    functional_area: Optional[str],
    truth_type: Optional[str],
    content_domain: Optional[str],
    uploaded_by_id: Optional[str],
    uploaded_by_email: Optional[str],
    async_mode: bool,
    temp_dir: str
) -> Dict[str, Any]:
    """Route to RAG Handler for semantic/text documents."""
    
    logger.warning(f"[SMART-ROUTER] → SEMANTIC HANDLER (ChromaDB)")
    
    # For PDFs, use Smart PDF Analyzer if available (may route to both DuckDB + ChromaDB)
    if extension == 'pdf' and SMART_PDF_AVAILABLE:
        logger.warning(f"[SMART-ROUTER] Using Smart PDF Analyzer")
    
    if async_mode and MODELS_AVAILABLE:
        # Create job and process in background
        job_result = ProcessingJobModel.create(
            job_type='upload',
            project_id=project_id,
            input_data={
                'filename': filename,
                'functional_area': functional_area,
                'project_name': project,
                'file_hash': file_hash,
                'route': 'semantic'
            }
        )
        
        if not job_result:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise HTTPException(status_code=500, detail="Failed to create job")
        
        job_id = job_result['id']
        
        try:
            from routers.upload import process_file_background
        except ImportError:
            from backend.routers.upload import process_file_background
        
        background_tasks.add_task(
            process_file_background,
            job_id, file_path, filename, project, project_id,
            functional_area, file_size, truth_type, content_domain,
            file_hash, uploaded_by_id, uploaded_by_email
        )
        
        return {
            "success": True,
            "job_id": job_id,
            "status": "queued",
            "route": "semantic",
            "message": f"File queued for semantic processing"
        }
    else:
        # Sync processing
        if not RAG_AVAILABLE or not TEXT_EXTRACTION_AVAILABLE:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise HTTPException(status_code=503, detail="Semantic processing not available")
        
        try:
            text = extract_text(file_path)
            if not text or len(text.strip()) < 10:
                return {"success": False, "error": "No text extracted", "route": "semantic"}
            
            rag = RAGHandler()
            metadata = {
                'source': filename,
                'filename': filename,
                'project': project,
                'project_id': project_id,
                'truth_type': truth_type or 'intent',
                'file_type': extension
            }
            
            chunks_added = rag.add_document(
                collection_name="documents",
                text=text,
                metadata=metadata
            )
            
            return {
                "success": True,
                "route": "semantic",
                "filename": filename,
                "chunks_added": chunks_added,
                "char_count": len(text)
            }
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


# =============================================================================
# STATUS ENDPOINT
# =============================================================================

@router.get("/upload/router-status")
async def router_status():
    """Get Smart Router status and available processors."""
    return {
        "status": "ok",
        "processors": {
            "register": REGISTER_AVAILABLE,
            "standards": STANDARDS_AVAILABLE,
            "structured": STRUCTURED_AVAILABLE,
            "semantic": RAG_AVAILABLE,
            "smart_pdf": SMART_PDF_AVAILABLE
        },
        "registration": REGISTRATION_AVAILABLE,
        "models": MODELS_AVAILABLE,
        "text_extraction": TEXT_EXTRACTION_AVAILABLE
    }


# =============================================================================
# BACKWARD COMPATIBILITY ALIASES
# =============================================================================

# These routes call through to the smart router with explicit processing_type

@router.post("/standards/upload")
async def standards_upload_alias(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    domain: str = Form(default="general"),
    title: Optional[str] = Form(None)
):
    """
    DEPRECATED: Use /upload with processing_type=standards instead.
    This alias is kept for backward compatibility.
    """
    logger.warning(f"[SMART-ROUTER] /standards/upload called - routing through smart router")
    
    return await smart_upload(
        request=request,
        background_tasks=background_tasks,
        file=file,
        project="__STANDARDS__",
        processing_type="standards",
        domain=domain,
        title=title
    )


@router.post("/register/upload")
async def register_upload_alias(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    max_pages: int = Form(0),
    project_id: Optional[str] = Form(None),
    use_textract: bool = Form(False),
    async_mode: bool = Form(True),
    vendor_type: str = Form("unknown")
):
    """
    DEPRECATED: Use /upload with processing_type=register instead.
    This alias is kept for backward compatibility.
    """
    logger.warning(f"[SMART-ROUTER] /register/upload called - routing through smart router")
    
    return await smart_upload(
        request=request,
        background_tasks=background_tasks,
        file=file,
        project=project_id or "unknown",
        processing_type="register",
        max_pages=max_pages,
        use_textract=use_textract,
        vendor_type=vendor_type,
        async_mode=async_mode
    )


@router.post("/vacuum/upload")
async def vacuum_upload_alias(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    max_pages: int = Form(0),
    project_id: Optional[str] = Form(None),
    use_textract: bool = Form(False),
    async_mode: bool = Form(True),
    vendor_type: str = Form("unknown")
):
    """
    DEPRECATED: Use /upload with processing_type=register instead.
    Kept for backward compatibility with old 'vacuum' naming.
    """
    logger.warning(f"[SMART-ROUTER] /vacuum/upload called - routing through smart router")
    
    return await smart_upload(
        request=request,
        background_tasks=background_tasks,
        file=file,
        project=project_id or "unknown",
        processing_type="register",
        max_pages=max_pages,
        use_textract=use_textract,
        vendor_type=vendor_type,
        async_mode=async_mode
    )
