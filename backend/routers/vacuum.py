"""
Vacuum Router v5 - Clean Slate
================================
Simple API for the new SmartExtractor.

No manual mapping. No legacy fallbacks. Just:
- Upload → Extract → Done

Deploy to: backend/routers/vacuum.py
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from dataclasses import asdict
import os
import logging
import tempfile
import shutil

logger = logging.getLogger(__name__)

router = APIRouter()

# =============================================================================
# IMPORT SMART EXTRACTOR
# =============================================================================

EXTRACTOR_AVAILABLE = False
SmartExtractor = None
get_smart_extractor = None

for import_path in ['extraction.smart_extractor', 'backend.extraction.smart_extractor', 'smart_extractor']:
    try:
        module = __import__(import_path, fromlist=['SmartExtractor', 'get_smart_extractor'])
        SmartExtractor = module.SmartExtractor
        get_smart_extractor = module.get_smart_extractor
        EXTRACTOR_AVAILABLE = True
        logger.info(f"✅ SmartExtractor loaded from {import_path}")
        break
    except ImportError as e:
        logger.debug(f"Could not import from {import_path}: {e}")

if not EXTRACTOR_AVAILABLE:
    logger.error("❌ SmartExtractor not available - extraction will fail")


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.get("/vacuum/status")
async def vacuum_status():
    """Check extraction system status"""
    status = {
        "available": EXTRACTOR_AVAILABLE,
        "version": "5.0",
        "system": "SmartExtractor",
        "features": {
            "auto_format_learning": True,
            "pii_protection": True,
            "math_validation": True,
            "format_reuse": True
        }
    }
    
    if EXTRACTOR_AVAILABLE:
        try:
            extractor = get_smart_extractor()
            formats = extractor.get_formats()
            status["learned_formats"] = len(formats)
            status["format_names"] = [f["format_name"] for f in formats]
        except Exception as e:
            status["error"] = str(e)
    
    return status


@router.post("/vacuum/upload")
async def vacuum_upload(
    file: UploadFile = File(...),
    vendor_hint: Optional[str] = Form(None),
    force_relearn: bool = Form(False)
):
    """
    Upload and extract a pay register.
    
    The system will:
    1. Analyze the document structure (3 pages via Textract)
    2. Check if format is already learned
    3. If new format: Send redacted structure to Claude to learn rules
    4. Apply rules to all pages locally (free)
    5. Validate the math
    
    Cost: ~$0.10-0.15 for new formats, $0.05 for known formats
    PII: Never sent to cloud - only structure patterns
    
    Args:
        file: The PDF file to process
        vendor_hint: Optional hint like "Paycom" or "ADP"
        force_relearn: Force re-learning even if format is known
    """
    if not EXTRACTOR_AVAILABLE:
        raise HTTPException(503, "Extraction system not available")
    
    filename = file.filename
    file_ext = filename.split('.')[-1].lower()
    
    if file_ext not in ['pdf']:
        raise HTTPException(400, f"Only PDF files supported currently. Got: {file_ext}")
    
    # Save to temp file
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, filename)
    
    try:
        with open(temp_path, 'wb') as f:
            shutil.copyfileobj(file.file, f)
        
        # Extract
        extractor = get_smart_extractor()
        result = extractor.extract(
            file_path=temp_path,
            vendor_hint=vendor_hint,
            force_relearn=force_relearn
        )
        
        # Build response
        return {
            "success": result.success,
            "source_file": result.source_file,
            
            # Format info
            "format": {
                "id": result.format_id,
                "name": result.format_name,
                "learned_now": result.format_learned
            },
            
            # Results
            "employee_count": result.employee_count,
            "employees": [
                {
                    "name": emp.employee_name,
                    "id": emp.employee_id,
                    "department": emp.department,
                    "gross_pay": emp.gross_pay,
                    "net_pay": emp.net_pay,
                    "total_taxes": emp.total_taxes,
                    "total_deductions": emp.total_deductions,
                    "earnings": emp.earnings,
                    "taxes": emp.taxes,
                    "deductions": emp.deductions,
                    "check_number": emp.check_number,
                    "pay_method": emp.pay_method,
                    "is_valid": emp.is_valid,
                    "validation_errors": emp.validation_errors
                }
                for emp in result.employees
            ],
            
            # Quality
            "confidence": result.confidence,
            "validation_passed": result.validation_passed,
            "validation_errors": result.validation_errors,
            
            # Cost & Performance
            "pages_processed": result.pages_processed,
            "cloud_pages_used": result.cloud_pages_used,
            "ai_calls_used": result.ai_calls_used,
            "estimated_cost_usd": round(result.estimated_cost, 4),
            "processing_time_ms": result.processing_time_ms
        }
        
    except Exception as e:
        logger.error(f"Extraction failed: {e}", exc_info=True)
        raise HTTPException(500, str(e))
        
    finally:
        # Cleanup
        try:
            shutil.rmtree(temp_dir)
        except:
            pass


@router.post("/vacuum/extract")
async def vacuum_extract(
    file: UploadFile = File(...),
    vendor_hint: Optional[str] = Form(None),
    force_relearn: bool = Form(False)
):
    """Alias for /vacuum/upload for backwards compatibility"""
    return await vacuum_upload(file, vendor_hint, force_relearn)


@router.get("/vacuum/formats")
async def get_formats():
    """Get all learned document formats"""
    if not EXTRACTOR_AVAILABLE:
        return {"formats": [], "count": 0}
    
    try:
        extractor = get_smart_extractor()
        formats = extractor.get_formats()
        
        return {
            "formats": [
                {
                    "id": f["format_id"],
                    "name": f["format_name"],
                    "vendor": f["vendor"],
                    "created_at": f["created_at"],
                    "times_used": f["times_used"],
                    "last_used": f["last_used"],
                    "column_count": f["column_count"]
                }
                for f in formats
            ],
            "count": len(formats)
        }
    except Exception as e:
        logger.error(f"Error getting formats: {e}")
        return {"formats": [], "count": 0, "error": str(e)}


@router.delete("/vacuum/format/{format_id}")
async def delete_format(format_id: str):
    """Delete a learned format"""
    if not EXTRACTOR_AVAILABLE:
        raise HTTPException(503, "Extraction system not available")
    
    try:
        extractor = get_smart_extractor()
        success = extractor.delete_format(format_id)
        return {"success": success, "format_id": format_id}
    except Exception as e:
        logger.error(f"Error deleting format: {e}")
        raise HTTPException(500, str(e))


@router.get("/vacuum/format/{format_id}/delete")
async def delete_format_get(format_id: str):
    """Delete a learned format (GET for browser use)"""
    return await delete_format(format_id)


@router.get("/vacuum/reset-formats")
async def reset_all_formats():
    """Delete ALL learned formats and start fresh"""
    if not EXTRACTOR_AVAILABLE:
        raise HTTPException(503, "Extraction system not available")
    
    try:
        extractor = get_smart_extractor()
        formats = extractor.get_formats()
        deleted = []
        for fmt in formats:
            if extractor.delete_format(fmt["format_id"]):
                deleted.append(fmt["format_id"])
        return {"success": True, "deleted": deleted, "count": len(deleted)}
    except Exception as e:
        logger.error(f"Error resetting formats: {e}")
        raise HTTPException(500, str(e))


@router.get("/vacuum/validation-rules")
async def get_validation_rules():
    """Get the validation rules being applied"""
    return {
        "rules": [
            {
                "name": "earnings_sum",
                "description": "Sum of individual earnings should equal Gross Pay",
                "tolerance": "$0.02"
            },
            {
                "name": "net_pay_calculation",
                "description": "Gross - Taxes - Deductions should equal Net Pay",
                "tolerance": "$0.02"
            },
            {
                "name": "required_fields",
                "description": "Employee name is required",
                "severity": "error"
            }
        ],
        "confidence_target": 0.90
    }


# =============================================================================
# SIMPLE HEALTH CHECK
# =============================================================================

@router.get("/vacuum/health")
async def health():
    """Simple health check"""
    return {
        "status": "ok",
        "extractor_available": EXTRACTOR_AVAILABLE,
        "timestamp": datetime.now().isoformat()
    }
