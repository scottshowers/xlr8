"""
Vacuum Upload Router v4 - NOW USING THE NEW EXTRACTION SYSTEM
==============================================================
Deploy to: backend/routers/vacuum.py

This version actually connects to the extraction orchestrator!
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import os
import sys
import logging
import tempfile
import shutil

# Add paths
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/backend')

logger = logging.getLogger(__name__)

router = APIRouter()

# =============================================================================
# IMPORT NEW EXTRACTION SYSTEM
# =============================================================================

EXTRACTION_AVAILABLE = False
get_extraction_orchestrator = None
ExtractionStatus = None

# Try to import the new extraction orchestrator
for import_path in ['extraction', 'backend.extraction']:
    try:
        module = __import__(import_path, fromlist=[
            'get_extraction_orchestrator', 
            'ExtractionStatus',
            'CONFIDENCE_THRESHOLD'
        ])
        get_extraction_orchestrator = module.get_extraction_orchestrator
        ExtractionStatus = module.ExtractionStatus
        EXTRACTION_AVAILABLE = True
        logger.info(f"✅ New extraction orchestrator loaded from {import_path}")
        break
    except ImportError as e:
        logger.debug(f"Could not import from {import_path}: {e}")

if not EXTRACTION_AVAILABLE:
    logger.warning("❌ New extraction system not available, falling back to legacy")

# Legacy imports (fallback)
LEGACY_AVAILABLE = False
get_vacuum_extractor = None
VacuumExtractor = None

for import_path in ['backend.utils.vacuum_extractor', 'utils.vacuum_extractor']:
    try:
        module = __import__(import_path, fromlist=['get_vacuum_extractor', 'VacuumExtractor'])
        get_vacuum_extractor = module.get_vacuum_extractor
        VacuumExtractor = module.VacuumExtractor
        LEGACY_AVAILABLE = True
        logger.info(f"Legacy vacuum extractor loaded from {import_path}")
        break
    except ImportError as e:
        logger.debug(f"Could not import legacy from {import_path}: {e}")


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class SplitColumnRequest(BaseModel):
    extract_id: int
    column_index: int
    split_method: str
    pattern: Optional[str] = None
    new_headers: Optional[List[str]] = None
    positions: Optional[List[int]] = None
    delimiter: Optional[str] = None


class DetectPatternRequest(BaseModel):
    sample_values: List[str]
    section_type: Optional[str] = 'unknown'


class ApplyMappingsRequest(BaseModel):
    source_file: str
    header_metadata: Dict[str, str]
    section_mappings: Dict[str, Any]
    remember_for_vendor: bool = True


# =============================================================================
# STATUS ENDPOINT
# =============================================================================

@router.get("/vacuum/status")
async def vacuum_status():
    """Check vacuum extractor status and capabilities"""
    status = {
        "available": EXTRACTION_AVAILABLE or LEGACY_AVAILABLE,
        "version": "4.0",
        "new_extraction_system": EXTRACTION_AVAILABLE,
        "legacy_fallback": LEGACY_AVAILABLE,
    }
    
    if EXTRACTION_AVAILABLE:
        try:
            orchestrator = get_extraction_orchestrator()
            status["extractors_loaded"] = list(orchestrator.extractors.keys())
            status["cloud_available"] = orchestrator.cloud_analyzer is not None and orchestrator.cloud_analyzer.is_available
            status["template_manager"] = orchestrator.template_manager is not None
            status["validator"] = orchestrator.validator is not None
            status["pii_redactor"] = orchestrator.pii_redactor is not None
        except Exception as e:
            status["orchestrator_error"] = str(e)
    
    if LEGACY_AVAILABLE:
        try:
            extractor = get_vacuum_extractor()
            files = extractor.get_files_summary()
            stats = extractor.get_pattern_stats()
            status["files_count"] = len(files)
            status["total_tables"] = sum(f['table_count'] for f in files)
            status["total_rows"] = sum(f['total_rows'] for f in files)
            status["learning_stats"] = stats
        except Exception as e:
            status["legacy_error"] = str(e)
    
    return status


# =============================================================================
# MAIN UPLOAD ENDPOINT - USES NEW EXTRACTION SYSTEM
# =============================================================================

@router.post("/vacuum/upload")
async def vacuum_upload(
    file: UploadFile = File(...),
    project: Optional[str] = Form(None),
    force_cloud: bool = Form(False)
):
    """
    Upload a file for extraction using the new multi-layer system.
    
    The new system:
    1. Detects document layout
    2. Matches against learned templates
    3. Runs multiple extractors
    4. Falls back to AWS Textract if confidence < 80%
    5. Validates results (Earnings=Gross, Gross-Tax-Ded=Net)
    6. Targets 98% confidence
    """
    
    filename = file.filename
    file_ext = filename.split('.')[-1].lower()
    
    if file_ext not in ['pdf', 'xlsx', 'xls', 'csv']:
        raise HTTPException(400, f"Unsupported file type: {file_ext}")
    
    # Save to temp file
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, filename)
    
    try:
        with open(temp_path, 'wb') as f:
            shutil.copyfileobj(file.file, f)
        
        # =====================================================================
        # USE NEW EXTRACTION SYSTEM
        # =====================================================================
        if EXTRACTION_AVAILABLE:
            logger.info(f"🚀 Using NEW extraction orchestrator for {filename}")
            
            orchestrator = get_extraction_orchestrator()
            result = orchestrator.extract_document(
                file_path=temp_path,
                project=project,
                force_cloud=force_cloud
            )
            
            # Convert to API response format
            sections_response = {}
            for section_name, section_data in result.sections.items():
                sections_response[section_name] = {
                    "row_count": section_data.row_count,
                    "column_count": section_data.column_count,
                    "headers": section_data.headers,
                    "confidence": section_data.confidence,
                    "extraction_method": section_data.extraction_method,
                    "layout_type": section_data.layout_type.value,
                    "needs_review": section_data.needs_review,
                    "issues": section_data.issues,
                    "preview": section_data.data[:10] if section_data.data else []
                }
            
            # Also store in legacy system for UI compatibility
            if LEGACY_AVAILABLE:
                try:
                    legacy_extractor = get_vacuum_extractor()
                    legacy_result = legacy_extractor.vacuum_file(temp_path, project)
                except Exception as e:
                    logger.warning(f"Legacy storage failed: {e}")
            
            return {
                "success": result.status in [ExtractionStatus.SUCCESS, ExtractionStatus.NEEDS_REVIEW],
                "source_file": filename,
                "project": project,
                "extraction_system": "v4_orchestrator",
                
                # Key metrics
                "status": result.status.value,
                "overall_confidence": result.overall_confidence,
                "employee_count": result.employee_count,
                "processing_time_ms": result.processing_time_ms,
                
                # Validation
                "validation_passed": result.validation_passed,
                "validation_errors": result.validation_errors,
                
                # Template info
                "template_matched": result.template_matched,
                "template_id": result.template_id,
                "cloud_used": result.cloud_used,
                
                # Sections
                "sections": sections_response,
                "section_count": len(sections_response),
                
                # Metadata
                "metadata": result.metadata
            }
        
        # =====================================================================
        # FALLBACK TO LEGACY SYSTEM
        # =====================================================================
        elif LEGACY_AVAILABLE:
            logger.info(f"📦 Using LEGACY extractor for {filename}")
            
            extractor = get_vacuum_extractor()
            result = extractor.vacuum_file(temp_path, project)
            
            return {
                "success": True,
                "source_file": filename,
                "project": project,
                "extraction_system": "legacy",
                "tables_found": result['tables_found'],
                "total_rows": result['total_rows'],
                "extracts": result['extracts'],
                "errors": result['errors']
            }
        
        else:
            raise HTTPException(501, "No extraction system available")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}", exc_info=True)
        raise HTTPException(500, str(e))
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# =============================================================================
# FORCE CLOUD EXTRACTION
# =============================================================================

@router.post("/vacuum/upload-with-cloud")
async def vacuum_upload_force_cloud(
    file: UploadFile = File(...),
    project: Optional[str] = Form(None)
):
    """Force cloud (AWS Textract) analysis regardless of local confidence"""
    return await vacuum_upload(file, project, force_cloud=True)


# =============================================================================
# SECTION TYPES & COLUMN TYPES
# =============================================================================

@router.get("/vacuum/section-types")
async def get_section_types():
    """Get all available section types"""
    return {
        "section_types": [
            {"value": "employee_info", "label": "Employee Information", "layout": "key_value"},
            {"value": "earnings", "label": "Earnings", "layout": "table"},
            {"value": "taxes", "label": "Taxes", "layout": "table"},
            {"value": "deductions", "label": "Deductions", "layout": "table"},
            {"value": "pay_totals", "label": "Pay Totals", "layout": "key_value"},
        ]
    }


@router.get("/vacuum/column-types")
async def get_column_types():
    """Get all available column types grouped by section"""
    return {
        "column_types": {
            "employee_info": [
                {"value": "employee_id", "label": "Employee ID"},
                {"value": "employee_name", "label": "Employee Name"},
                {"value": "first_name", "label": "First Name"},
                {"value": "last_name", "label": "Last Name"},
                {"value": "ssn", "label": "SSN"},
                {"value": "department", "label": "Department"},
                {"value": "location", "label": "Location"},
                {"value": "job_title", "label": "Job Title"},
                {"value": "hire_date", "label": "Hire Date"},
                {"value": "tax_status", "label": "Tax Status (Fed/State/Local)"},
            ],
            "earnings": [
                {"value": "earning_code", "label": "Earning Code"},
                {"value": "earning_description", "label": "Description"},
                {"value": "hours_current", "label": "Current Hours"},
                {"value": "hours_ytd", "label": "YTD Hours"},
                {"value": "rate", "label": "Rate"},
                {"value": "amount_current", "label": "Current Amount"},
                {"value": "amount_ytd", "label": "YTD Amount"},
            ],
            "taxes": [
                {"value": "tax_code", "label": "Tax Code"},
                {"value": "tax_description", "label": "Description"},
                {"value": "taxable_wages", "label": "Taxable Wages"},
                {"value": "tax_amount_current", "label": "Current Amount"},
                {"value": "tax_amount_ytd", "label": "YTD Amount"},
            ],
            "deductions": [
                {"value": "deduction_code", "label": "Deduction Code"},
                {"value": "deduction_description", "label": "Description"},
                {"value": "deduction_ee_current", "label": "Employee Current"},
                {"value": "deduction_ee_ytd", "label": "Employee YTD"},
                {"value": "deduction_er_current", "label": "Employer Current"},
                {"value": "deduction_er_ytd", "label": "Employer YTD"},
            ],
            "pay_totals": [
                {"value": "gross_pay", "label": "Gross Pay"},
                {"value": "net_pay", "label": "Net Pay"},
                {"value": "total_taxes", "label": "Total Taxes"},
                {"value": "total_deductions", "label": "Total Deductions"},
                {"value": "check_number", "label": "Check Number"},
                {"value": "direct_deposit", "label": "Direct Deposit Amount"},
            ],
        }
    }


# =============================================================================
# FILES & EXTRACTS (uses legacy storage for now)
# =============================================================================

@router.get("/vacuum/files")
async def get_vacuum_files(project: Optional[str] = None):
    """Get summary of all vacuumed files"""
    if not LEGACY_AVAILABLE:
        return {"files": [], "total": 0}
    
    try:
        extractor = get_vacuum_extractor()
        files = extractor.get_files_summary(project)
        return {"files": files, "total": len(files)}
    except Exception as e:
        logger.error(f"Error getting files: {e}")
        return {"files": [], "total": 0, "error": str(e)}


@router.get("/vacuum/extracts")
async def get_extracts(
    project: Optional[str] = None,
    source_file: Optional[str] = None
):
    """Get all extracts with optional filters"""
    if not LEGACY_AVAILABLE:
        return {"extracts": [], "total": 0}
    
    try:
        extractor = get_vacuum_extractor()
        extracts = extractor.get_extracts(project, source_file)
        
        # Truncate large data for response
        for ext in extracts:
            if ext.get('raw_data') and len(ext['raw_data']) > 10:
                ext['preview'] = ext['raw_data'][:10]
                ext['raw_data'] = None
        
        return {"extracts": extracts, "total": len(extracts)}
    except Exception as e:
        logger.error(f"Error getting extracts: {e}")
        return {"extracts": [], "total": 0, "error": str(e)}


@router.get("/vacuum/extract/{extract_id}")
async def get_extract_detail(extract_id: int, preview_rows: int = 50):
    """Get full detail for a single extract"""
    if not LEGACY_AVAILABLE:
        raise HTTPException(501, "Legacy extractor not available")
    
    try:
        extractor = get_vacuum_extractor()
        extract = extractor.get_extract_by_id(extract_id)
        
        if not extract:
            raise HTTPException(404, "Extract not found")
        
        return extract
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting extract: {e}")
        raise HTTPException(500, str(e))


# =============================================================================
# TEMPLATE MANAGEMENT
# =============================================================================

@router.get("/vacuum/templates")
async def get_templates():
    """Get all learned extraction templates"""
    if not EXTRACTION_AVAILABLE:
        return {"templates": [], "message": "New extraction system not available"}
    
    try:
        orchestrator = get_extraction_orchestrator()
        if orchestrator.template_manager:
            templates = orchestrator.template_manager._get_all_templates()
            return {"templates": templates, "count": len(templates)}
        return {"templates": [], "message": "Template manager not available"}
    except Exception as e:
        logger.error(f"Error getting templates: {e}")
        return {"templates": [], "error": str(e)}


@router.delete("/vacuum/template/{template_id}")
async def delete_template(template_id: str):
    """Delete a learned template"""
    if not EXTRACTION_AVAILABLE:
        raise HTTPException(501, "New extraction system not available")
    
    try:
        orchestrator = get_extraction_orchestrator()
        if orchestrator.template_manager:
            success = orchestrator.template_manager.delete_template(template_id)
            return {"success": success, "template_id": template_id}
        raise HTTPException(501, "Template manager not available")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting template: {e}")
        raise HTTPException(500, str(e))


# =============================================================================
# VALIDATION INFO
# =============================================================================

@router.get("/vacuum/validation-rules")
async def get_validation_rules():
    """Get the validation rules being applied"""
    return {
        "rules": [
            {
                "name": "earnings_gross_match",
                "description": "Sum of earnings should equal Gross Pay",
                "tolerance": "$0.02"
            },
            {
                "name": "math_check", 
                "description": "Gross - Taxes - Deductions should equal Net Pay",
                "tolerance": "$0.02"
            },
            {
                "name": "required_employee_fields",
                "description": "Every employee must have Name and Employee ID",
                "fields": ["employee_name", "employee_id"]
            },
            {
                "name": "tax_indicators",
                "description": "Employees should have tax filing status (Fed/State/Local)",
                "severity": "warning"
            },
            {
                "name": "value_ranges",
                "description": "Hours should not exceed 744 (max in a month)",
                "severity": "warning"
            }
        ],
        "confidence_threshold": 0.98,
        "cloud_fallback_threshold": 0.80
    }


# =============================================================================
# DELETE OPERATIONS
# =============================================================================

@router.delete("/vacuum/file/{source_file}")
async def delete_vacuum_file(source_file: str, project: Optional[str] = None):
    """Delete all extracts for a file"""
    if not LEGACY_AVAILABLE:
        raise HTTPException(501, "Legacy extractor not available")
    
    try:
        extractor = get_vacuum_extractor()
        count = extractor.delete_file_extracts(source_file, project)
        return {"success": True, "deleted_extracts": count, "source_file": source_file}
    except Exception as e:
        logger.error(f"Error deleting file: {e}")
        raise HTTPException(500, str(e))


@router.post("/vacuum/reset")
async def reset_vacuum():
    """Delete all vacuum extracts"""
    if not LEGACY_AVAILABLE:
        raise HTTPException(501, "Legacy extractor not available")
    
    try:
        extractor = get_vacuum_extractor()
        count = extractor.delete_all_extracts()
        return {"success": True, "deleted_extracts": count}
    except Exception as e:
        logger.error(f"Error resetting: {e}")
        raise HTTPException(500, str(e))


# =============================================================================
# HEADER METADATA
# =============================================================================

@router.get("/vacuum/header-metadata")
async def get_header_metadata(source_file: str):
    """Extract header metadata from a document"""
    if not LEGACY_AVAILABLE:
        return {"success": False, "metadata": {}}
    
    try:
        extractor = get_vacuum_extractor()
        metadata = extractor.extract_header_metadata(source_file)
        return {"success": True, "source_file": source_file, "metadata": metadata}
    except Exception as e:
        logger.error(f"Error extracting metadata: {e}")
        return {"success": False, "metadata": {}}


# =============================================================================
# MAPPINGS
# =============================================================================

@router.post("/vacuum/apply-mappings")
async def apply_all_mappings(request: ApplyMappingsRequest):
    """Apply all section mappings for a pay register"""
    if not LEGACY_AVAILABLE:
        raise HTTPException(501, "Legacy extractor not available")
    
    try:
        extractor = get_vacuum_extractor()
        results = []
        
        for section, mapping_data in request.section_mappings.items():
            if not mapping_data or not mapping_data.get('columns'):
                continue
            
            extract_id = mapping_data.get('extract_id')
            if not extract_id:
                continue
            
            column_map = {}
            for header, col_data in mapping_data.get('columns', {}).items():
                target = col_data.get('confirmed', 'skip')
                if target and target != 'skip':
                    column_map[header] = target
            
            if column_map:
                result = extractor.apply_section_mapping(
                    extract_id=extract_id,
                    section_type=section,
                    column_map=column_map,
                    header_metadata=request.header_metadata if section == 'employee_info' else None
                )
                results.append({
                    "section": section,
                    "extract_id": extract_id,
                    "columns_mapped": len(column_map),
                    "success": result.get('success', False)
                })
        
        return {
            "success": True,
            "source_file": request.source_file,
            "sections_processed": len(results),
            "results": results
        }
    except Exception as e:
        logger.error(f"Error applying mappings: {e}")
        raise HTTPException(500, str(e))
