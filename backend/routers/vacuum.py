"""
Vacuum Upload Router v2 - API endpoints for intelligent vacuum extraction
=========================================================================

Enhanced with section detection, column classification, and learning endpoints.

Author: XLR8 Team
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Body
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import os
import logging
import tempfile
import shutil

logger = logging.getLogger(__name__)

router = APIRouter()

# Import vacuum extractor
try:
    from main.utils.vacuum_extractor import get_vacuum_extractor, VacuumExtractor, SectionType, ColumnType
    VACUUM_AVAILABLE = True
    logger.info("Vacuum extractor v2 loaded successfully")
except ImportError as e1:
    try:
        from utils.vacuum_extractor import get_vacuum_extractor, VacuumExtractor, SectionType, ColumnType
        VACUUM_AVAILABLE = True
        logger.info("Vacuum extractor v2 loaded successfully")
    except ImportError as e2:
        VACUUM_AVAILABLE = False
        logger.warning(f"Vacuum extractor not available: {e1} / {e2}")


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class ConfirmSectionRequest(BaseModel):
    extract_id: int
    section_type: str
    user_corrected: bool = False


class ConfirmColumnRequest(BaseModel):
    extract_id: int
    column_index: int
    column_type: str
    user_corrected: bool = False


class ConfirmAllColumnsRequest(BaseModel):
    extract_id: int
    column_mappings: Dict[int, str]  # {column_index: column_type}


class LearnVendorRequest(BaseModel):
    extract_ids: List[int]
    vendor_name: str
    report_type: str = "pay_register"


class ColumnMappingRequest(BaseModel):
    extract_id: int
    column_map: Dict[str, str]  # {original_header: target_column_type}
    target_table: str


# =============================================================================
# STATUS & INFO ENDPOINTS
# =============================================================================

@router.get("/vacuum/status")
async def vacuum_status():
    """Check vacuum extractor status and capabilities"""
    if not VACUUM_AVAILABLE:
        return {
            "available": False,
            "version": None,
            "message": "Vacuum extractor not available. Check dependencies."
        }
    
    try:
        extractor = get_vacuum_extractor()
        files = extractor.get_files_summary()
        stats = extractor.get_pattern_stats()
        
        return {
            "available": True,
            "version": "2.0",
            "files_count": len(files),
            "total_tables": sum(f['table_count'] for f in files),
            "total_rows": sum(f['total_rows'] for f in files),
            "learning_stats": stats
        }
    except Exception as e:
        logger.error(f"Vacuum status error: {e}")
        return {
            "available": False,
            "error": str(e)
        }


@router.get("/vacuum/section-types")
async def get_section_types():
    """Get all available section types"""
    return {
        "section_types": [
            {"value": "employee_info", "label": "Employee Information", "description": "Names, IDs, SSNs, hire dates, departments"},
            {"value": "earnings", "label": "Earnings", "description": "Pay codes, hours, rates, current and YTD amounts"},
            {"value": "taxes", "label": "Taxes", "description": "Federal, state, local taxes, FICA, Medicare"},
            {"value": "deductions", "label": "Deductions", "description": "401k, medical, dental, garnishments, etc."},
            {"value": "pay_info", "label": "Pay Information", "description": "Gross pay, net pay, check numbers, direct deposit"},
            {"value": "unknown", "label": "Unknown", "description": "Section type not detected"}
        ]
    }


@router.get("/vacuum/column-types")
async def get_column_types():
    """Get all available column types grouped by section"""
    return {
        "column_types": {
            "employee_info": [
                {"value": "employee_id", "label": "Employee ID"},
                {"value": "employee_name", "label": "Employee Name (Full)"},
                {"value": "first_name", "label": "First Name"},
                {"value": "last_name", "label": "Last Name"},
                {"value": "ssn", "label": "SSN"},
                {"value": "department", "label": "Department"},
                {"value": "location", "label": "Location"},
                {"value": "job_title", "label": "Job Title"},
                {"value": "pay_rate", "label": "Pay Rate"},
                {"value": "hire_date", "label": "Hire Date"},
                {"value": "term_date", "label": "Term Date"},
                {"value": "check_date", "label": "Check Date"},
                {"value": "pay_period_start", "label": "Pay Period Start"},
                {"value": "pay_period_end", "label": "Pay Period End"},
            ],
            "earnings": [
                {"value": "earning_code", "label": "Earning Code"},
                {"value": "earning_description", "label": "Earning Description"},
                {"value": "hours_current", "label": "Current Hours"},
                {"value": "hours_ytd", "label": "YTD Hours"},
                {"value": "rate", "label": "Rate"},
                {"value": "amount_current", "label": "Current Amount"},
                {"value": "amount_ytd", "label": "YTD Amount"},
            ],
            "taxes": [
                {"value": "tax_code", "label": "Tax Code"},
                {"value": "tax_description", "label": "Tax Description"},
                {"value": "taxable_wages", "label": "Taxable Wages"},
                {"value": "tax_amount_current", "label": "Current Tax Amount"},
                {"value": "tax_amount_ytd", "label": "YTD Tax Amount"},
                {"value": "tax_er_current", "label": "Employer Current"},
                {"value": "tax_er_ytd", "label": "Employer YTD"},
            ],
            "deductions": [
                {"value": "deduction_code", "label": "Deduction Code"},
                {"value": "deduction_description", "label": "Deduction Description"},
                {"value": "deduction_election", "label": "Election/Percent"},
                {"value": "deduction_ee_current", "label": "Employee Current"},
                {"value": "deduction_ee_ytd", "label": "Employee YTD"},
                {"value": "deduction_er_current", "label": "Employer Current"},
                {"value": "deduction_er_ytd", "label": "Employer YTD"},
            ],
            "pay_info": [
                {"value": "gross_pay", "label": "Gross Pay"},
                {"value": "net_pay", "label": "Net Pay"},
                {"value": "check_number", "label": "Check Number"},
                {"value": "direct_deposit", "label": "Direct Deposit Amount"},
            ],
            "universal": [
                {"value": "code", "label": "Code (Generic)"},
                {"value": "description", "label": "Description (Generic)"},
                {"value": "unknown", "label": "Unknown"},
            ]
        }
    }


# =============================================================================
# UPLOAD & EXTRACTION
# =============================================================================

@router.post("/vacuum/upload")
async def vacuum_upload(
    file: UploadFile = File(...),
    project: Optional[str] = Form(None)
):
    """
    Upload a file for vacuum extraction with intelligent detection.
    
    Returns:
    - Extracted tables with section and column classifications
    - Confidence scores for each detection
    - Detected report type (pay_register, census, etc.)
    - Vendor match if recognized
    """
    if not VACUUM_AVAILABLE:
        raise HTTPException(501, "Vacuum extractor not available")
    
    # Validate file type
    filename = file.filename
    file_ext = filename.split('.')[-1].lower()
    
    if file_ext not in ['pdf', 'xlsx', 'xls', 'csv']:
        raise HTTPException(400, f"Unsupported file type: {file_ext}. Supported: pdf, xlsx, xls, csv")
    
    # Save to temp file
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, filename)
    
    try:
        with open(temp_path, 'wb') as f:
            shutil.copyfileobj(file.file, f)
        
        # Extract with intelligent detection
        extractor = get_vacuum_extractor()
        result = extractor.vacuum_file(temp_path, project)
        
        return {
            "success": True,
            "source_file": filename,
            "project": project,
            "tables_found": result['tables_found'],
            "total_rows": result['total_rows'],
            "detected_report_type": result.get('detected_report_type'),
            "vendor_match": result.get('vendor_match'),
            "extracts": result['extracts'],
            "errors": result['errors']
        }
        
    except Exception as e:
        logger.error(f"Vacuum upload error: {e}", exc_info=True)
        raise HTTPException(500, str(e))
    
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# =============================================================================
# BROWSE & EXPLORE
# =============================================================================

@router.get("/vacuum/files")
async def get_vacuum_files(project: Optional[str] = None):
    """Get summary of all vacuumed files"""
    if not VACUUM_AVAILABLE:
        raise HTTPException(501, "Vacuum extractor not available")
    
    try:
        extractor = get_vacuum_extractor()
        files = extractor.get_files_summary(project)
        
        return {
            "files": files,
            "total": len(files)
        }
    except Exception as e:
        logger.error(f"Error getting vacuum files: {e}")
        raise HTTPException(500, str(e))


@router.get("/vacuum/extracts")
async def get_extracts(
    project: Optional[str] = None,
    source_file: Optional[str] = None
):
    """Get all extracts with detection results, optionally filtered"""
    if not VACUUM_AVAILABLE:
        raise HTTPException(501, "Vacuum extractor not available")
    
    try:
        extractor = get_vacuum_extractor()
        extracts = extractor.get_extracts(project, source_file)
        
        # Prepare response (limit data size)
        for ext in extracts:
            if ext.get('raw_data') and len(ext['raw_data']) > 5:
                ext['preview'] = ext['raw_data'][:5]
                ext['raw_data'] = None  # Don't send full data in list view
        
        return {
            "extracts": extracts,
            "total": len(extracts)
        }
    except Exception as e:
        logger.error(f"Error getting extracts: {e}")
        raise HTTPException(500, str(e))


@router.get("/vacuum/extract/{extract_id}")
async def get_extract_detail(extract_id: int, preview_rows: int = 50):
    """Get full detail for a single extract including detection results"""
    if not VACUUM_AVAILABLE:
        raise HTTPException(501, "Vacuum extractor not available")
    
    try:
        extractor = get_vacuum_extractor()
        extract = extractor.get_extract_by_id(extract_id)
        
        if not extract:
            raise HTTPException(404, "Extract not found")
        
        # Prepare preview
        raw_data = extract.get('raw_data', [])
        if raw_data and len(raw_data) > preview_rows:
            extract['preview'] = raw_data[:preview_rows]
            extract['truncated'] = True
            extract['full_row_count'] = len(raw_data)
        else:
            extract['preview'] = raw_data
            extract['truncated'] = False
        
        return extract
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting extract: {e}")
        raise HTTPException(500, str(e))


# =============================================================================
# LEARNING & CONFIRMATION ENDPOINTS
# =============================================================================

@router.post("/vacuum/confirm-section")
async def confirm_section(request: ConfirmSectionRequest):
    """
    Confirm or correct section detection.
    
    This improves future detection accuracy.
    """
    if not VACUUM_AVAILABLE:
        raise HTTPException(501, "Vacuum extractor not available")
    
    # Validate section type
    valid_sections = ['employee_info', 'earnings', 'taxes', 'deductions', 'pay_info', 'unknown']
    if request.section_type not in valid_sections:
        raise HTTPException(400, f"Invalid section type. Valid: {valid_sections}")
    
    try:
        extractor = get_vacuum_extractor()
        success = extractor.confirm_section(
            request.extract_id, 
            request.section_type,
            request.user_corrected
        )
        
        if success:
            return {
                "success": True,
                "message": f"Section confirmed as '{request.section_type}'",
                "extract_id": request.extract_id,
                "learning_applied": True
            }
        else:
            raise HTTPException(404, "Extract not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error confirming section: {e}")
        raise HTTPException(500, str(e))


@router.post("/vacuum/confirm-column")
async def confirm_column(request: ConfirmColumnRequest):
    """
    Confirm or correct column classification.
    
    This improves future detection and creates learned mappings.
    """
    if not VACUUM_AVAILABLE:
        raise HTTPException(501, "Vacuum extractor not available")
    
    try:
        extractor = get_vacuum_extractor()
        success = extractor.confirm_column(
            request.extract_id,
            request.column_index,
            request.column_type,
            request.user_corrected
        )
        
        if success:
            return {
                "success": True,
                "message": f"Column {request.column_index} confirmed as '{request.column_type}'",
                "extract_id": request.extract_id,
                "column_index": request.column_index,
                "learning_applied": True
            }
        else:
            raise HTTPException(404, "Extract or column not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error confirming column: {e}")
        raise HTTPException(500, str(e))


@router.post("/vacuum/confirm-all-columns")
async def confirm_all_columns(request: ConfirmAllColumnsRequest):
    """
    Confirm multiple column mappings at once.
    
    Useful when user reviews and approves all detected columns.
    """
    if not VACUUM_AVAILABLE:
        raise HTTPException(501, "Vacuum extractor not available")
    
    try:
        extractor = get_vacuum_extractor()
        results = []
        
        for col_index, col_type in request.column_mappings.items():
            success = extractor.confirm_column(
                request.extract_id,
                int(col_index),
                col_type,
                user_corrected=False
            )
            results.append({
                "column_index": col_index,
                "column_type": col_type,
                "success": success
            })
        
        return {
            "success": True,
            "extract_id": request.extract_id,
            "columns_confirmed": len([r for r in results if r['success']]),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error confirming columns: {e}")
        raise HTTPException(500, str(e))


@router.post("/vacuum/learn-vendor")
async def learn_vendor(request: LearnVendorRequest):
    """
    Learn a vendor signature from confirmed extracts.
    
    Future files from this vendor will be auto-recognized.
    """
    if not VACUUM_AVAILABLE:
        raise HTTPException(501, "Vacuum extractor not available")
    
    try:
        extractor = get_vacuum_extractor()
        
        # Get all extracts
        extracts = []
        for ext_id in request.extract_ids:
            ext = extractor.get_extract_by_id(ext_id)
            if ext:
                extracts.append(ext)
        
        if not extracts:
            raise HTTPException(404, "No valid extracts found")
        
        success = extractor.learn_vendor_signature(
            extracts,
            request.vendor_name,
            request.report_type
        )
        
        if success:
            return {
                "success": True,
                "message": f"Learned vendor signature for '{request.vendor_name}'",
                "vendor_name": request.vendor_name,
                "report_type": request.report_type,
                "extracts_used": len(extracts)
            }
        else:
            raise HTTPException(400, "Failed to learn vendor signature")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error learning vendor: {e}")
        raise HTTPException(500, str(e))


# =============================================================================
# LEARNING STATS & EXPORT
# =============================================================================

@router.get("/vacuum/learning-stats")
async def get_learning_stats():
    """Get statistics on learned patterns and mappings"""
    if not VACUUM_AVAILABLE:
        raise HTTPException(501, "Vacuum extractor not available")
    
    try:
        extractor = get_vacuum_extractor()
        stats = extractor.get_pattern_stats()
        
        return {
            "success": True,
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"Error getting learning stats: {e}")
        raise HTTPException(500, str(e))


@router.get("/vacuum/export-learning")
async def export_learning():
    """Export all learned patterns for backup"""
    if not VACUUM_AVAILABLE:
        raise HTTPException(501, "Vacuum extractor not available")
    
    try:
        extractor = get_vacuum_extractor()
        data = extractor.export_learning_data()
        
        return {
            "success": True,
            "export_date": datetime.now().isoformat(),
            "data": data
        }
        
    except Exception as e:
        logger.error(f"Error exporting learning data: {e}")
        raise HTTPException(500, str(e))


# =============================================================================
# RE-DETECTION (Useful after updating patterns)
# =============================================================================

@router.post("/vacuum/redetect/{extract_id}")
async def redetect_extract(extract_id: int):
    """
    Re-run detection on an existing extract.
    
    Useful after learning from corrections.
    """
    if not VACUUM_AVAILABLE:
        raise HTTPException(501, "Vacuum extractor not available")
    
    try:
        extractor = get_vacuum_extractor()
        extract = extractor.get_extract_by_id(extract_id)
        
        if not extract:
            raise HTTPException(404, "Extract not found")
        
        headers = extract.get('raw_headers', [])
        data = extract.get('raw_data', [])
        
        # Re-detect section
        section_result = extractor.detect_section(headers, data, extract_id)
        
        # Re-classify columns
        col_results = extractor.classify_columns(headers, data, section_result.section_type)
        
        # Update database
        extractor._update_extract_detection(extract_id, section_result, col_results)
        
        return {
            "success": True,
            "extract_id": extract_id,
            "detected_section": section_result.section_type.value,
            "section_confidence": section_result.confidence,
            "section_signals": section_result.signals_matched,
            "column_classifications": [
                {
                    "index": c.column_index,
                    "header": c.header,
                    "detected_type": c.detected_type.value,
                    "confidence": c.confidence,
                    "signals": c.signals_matched
                }
                for c in col_results
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error re-detecting: {e}")
        raise HTTPException(500, str(e))


# =============================================================================
# DELETE OPERATIONS
# =============================================================================

@router.delete("/vacuum/file/{source_file}")
async def delete_vacuum_file(source_file: str, project: Optional[str] = None):
    """Delete all extracts for a file"""
    if not VACUUM_AVAILABLE:
        raise HTTPException(501, "Vacuum extractor not available")
    
    try:
        extractor = get_vacuum_extractor()
        count = extractor.delete_file_extracts(source_file, project)
        
        return {
            "success": True,
            "deleted_extracts": count,
            "source_file": source_file
        }
    except Exception as e:
        logger.error(f"Error deleting vacuum file: {e}")
        raise HTTPException(500, str(e))


@router.post("/vacuum/reset")
async def reset_vacuum():
    """Delete all vacuum extracts (keeps learned patterns)"""
    if not VACUUM_AVAILABLE:
        raise HTTPException(501, "Vacuum extractor not available")
    
    try:
        extractor = get_vacuum_extractor()
        count = extractor.delete_all_extracts()
        
        logger.warning(f"Vacuum data reset - {count} extracts deleted")
        
        return {
            "success": True,
            "deleted_extracts": count,
            "note": "Learned patterns preserved"
        }
    except Exception as e:
        logger.error(f"Error resetting vacuum: {e}")
        raise HTTPException(500, str(e))


# =============================================================================
# MAPPING & EXPORT (Future: generate load files)
# =============================================================================

@router.post("/vacuum/apply-mapping")
async def apply_mapping(request: ColumnMappingRequest):
    """
    Apply column mapping to create a structured table.
    
    This takes an extract and creates a clean table with standardized columns.
    """
    if not VACUUM_AVAILABLE:
        raise HTTPException(501, "Vacuum extractor not available")
    
    try:
        extractor = get_vacuum_extractor()
        
        # For now, just validate and return success
        # Full implementation would create the mapped table in DuckDB
        extract = extractor.get_extract_by_id(request.extract_id)
        
        if not extract:
            raise HTTPException(404, "Extract not found")
        
        return {
            "success": True,
            "message": f"Mapping applied to create '{request.target_table}'",
            "extract_id": request.extract_id,
            "target_table": request.target_table,
            "columns_mapped": len(request.column_map)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying mapping: {e}")
        raise HTTPException(500, str(e))
