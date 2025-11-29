"""
Vacuum Router - Simple Version
===============================
Deploy to: backend/routers/vacuum.py
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from datetime import datetime
from dataclasses import asdict
import os
import logging
import tempfile
import shutil

logger = logging.getLogger(__name__)
router = APIRouter()

# Import extractor
EXTRACTOR_AVAILABLE = False
get_simple_extractor = None

for path in ['extraction.simple_extractor', 'backend.extraction.simple_extractor', 'simple_extractor']:
    try:
        module = __import__(path, fromlist=['get_simple_extractor'])
        get_simple_extractor = module.get_simple_extractor
        EXTRACTOR_AVAILABLE = True
        logger.info(f"✅ SimpleExtractor loaded from {path}")
        break
    except ImportError as e:
        logger.debug(f"Could not import from {path}: {e}")


@router.get("/vacuum/status")
async def status():
    return {
        "available": EXTRACTOR_AVAILABLE,
        "version": "6.0-simple",
        "method": "Textract + Claude"
    }


@router.post("/vacuum/upload")
async def upload(
    file: UploadFile = File(...),
    max_pages: int = Form(10)
):
    """
    Upload and extract pay register.
    
    1. Textract extracts text (limited to max_pages for cost control)
    2. Claude parses the data
    3. Validation checks the math
    
    Cost: ~$0.015/page (Textract) + ~$0.03 (Claude)
    Default 10 pages = ~$0.18
    """
    if not EXTRACTOR_AVAILABLE:
        raise HTTPException(503, "Extractor not available")
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, "Only PDF files supported")
    
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, file.filename)
    
    try:
        with open(temp_path, 'wb') as f:
            shutil.copyfileobj(file.file, f)
        
        extractor = get_simple_extractor()
        result = extractor.extract(temp_path, max_pages=max_pages)
        
        return {
            "success": result.success,
            "source_file": result.source_file,
            "employee_count": result.employee_count,
            "employees": [
                {
                    "name": e.name,
                    "id": e.employee_id,
                    "department": e.department,
                    "gross_pay": e.gross_pay,
                    "net_pay": e.net_pay,
                    "total_taxes": e.total_taxes,
                    "total_deductions": e.total_deductions,
                    "earnings": e.earnings,
                    "taxes": e.taxes,
                    "deductions": e.deductions,
                    "check_number": e.check_number,
                    "pay_method": e.pay_method,
                    "is_valid": e.is_valid,
                    "validation_errors": e.validation_errors
                }
                for e in result.employees
            ],
            "confidence": result.confidence,
            "validation_passed": result.validation_passed,
            "validation_errors": result.validation_errors,
            "pages_processed": result.pages_processed,
            "processing_time_ms": result.processing_time_ms,
            "cost_usd": result.cost_usd
        }
        
    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        raise HTTPException(500, str(e))
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@router.post("/vacuum/extract")
async def extract(file: UploadFile = File(...)):
    """Alias for /vacuum/upload"""
    return await upload(file)


@router.get("/vacuum/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}
