"""
Vacuum Upload Router v3 - API endpoints for intelligent vacuum extraction
=========================================================================
Deploy to: backend/routers/vacuum.py

Enhanced with:
- Smart PDF extraction (character-level position analysis)
- Column splitting with pattern detection
- Self-healing for merged columns
- AI-suggested split patterns

Author: XLR8 Team
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Body
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import os
import sys
import logging
import tempfile
import shutil
import re

sys.path.insert(0, '/app')
sys.path.insert(0, '/data')

logger = logging.getLogger(__name__)

router = APIRouter()

# Import vacuum extractor
try:
    from utils.vacuum_extractor import get_vacuum_extractor, VacuumExtractor, SectionType, ColumnType
    VACUUM_AVAILABLE = True
    logger.info("Vacuum extractor v2 loaded successfully")
except ImportError as e:
    VACUUM_AVAILABLE = False
    logger.warning(f"Vacuum extractor not available: {e}")

# Import smart PDF extractor
try:
    from utils.smart_pdf_extractor import (
        SmartPDFExtractor, 
        extract_pdf_smart,
        split_by_pattern,
        split_by_positions,
        split_by_delimiter,
        detect_split_patterns
    )
    SMART_EXTRACTOR_AVAILABLE = True
    logger.info("Smart PDF extractor loaded successfully")
except ImportError as e:
    SMART_EXTRACTOR_AVAILABLE = False
    logger.warning(f"Smart PDF extractor not available: {e}")


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
    column_mappings: Dict[int, str]


class LearnVendorRequest(BaseModel):
    extract_ids: List[int]
    vendor_name: str
    report_type: str = "pay_register"


class ColumnMappingRequest(BaseModel):
    extract_id: int
    column_map: Dict[str, str]
    target_table: str


class SplitColumnRequest(BaseModel):
    extract_id: int
    column_index: int
    split_method: str  # 'pattern', 'positions', 'delimiter'
    pattern: Optional[str] = None
    new_headers: Optional[List[str]] = None
    positions: Optional[List[int]] = None
    delimiter: Optional[str] = None


class DetectPatternRequest(BaseModel):
    sample_values: List[str]
    section_type: Optional[str] = 'unknown'


class SmartExtractRequest(BaseModel):
    filename: str


class ApplyMappingsRequest(BaseModel):
    source_file: str
    header_metadata: Dict[str, str]
    section_mappings: Dict[str, Any]
    remember_for_vendor: bool = True


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
            "version": "3.0",
            "smart_extractor_available": SMART_EXTRACTOR_AVAILABLE,
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
    """
    if not VACUUM_AVAILABLE:
        raise HTTPException(501, "Vacuum extractor not available")
    
    filename = file.filename
    file_ext = filename.split('.')[-1].lower()
    
    if file_ext not in ['pdf', 'xlsx', 'xls', 'csv']:
        raise HTTPException(400, f"Unsupported file type: {file_ext}. Supported: pdf, xlsx, xls, csv")
    
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, filename)
    
    try:
        with open(temp_path, 'wb') as f:
            shutil.copyfileobj(file.file, f)
        
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
# SMART EXTRACTION (NEW)
# =============================================================================

@router.post("/vacuum/smart-extract")
async def smart_extract(request: SmartExtractRequest):
    """
    Perform smart extraction on an uploaded PDF.
    Uses position-based column detection with self-healing.
    """
    if not SMART_EXTRACTOR_AVAILABLE:
        raise HTTPException(501, "Smart PDF extractor not available")
    
    try:
        # Find the file in uploads directory
        upload_dirs = ['/tmp/uploads', '/data/uploads', '/app/uploads']
        filepath = None
        
        for upload_dir in upload_dirs:
            test_path = os.path.join(upload_dir, request.filename)
            if os.path.exists(test_path):
                filepath = test_path
                break
        
        if not filepath:
            raise HTTPException(404, f"File not found: {request.filename}")
        
        result = extract_pdf_smart(filepath)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Smart extract error: {e}", exc_info=True)
        raise HTTPException(500, str(e))


# =============================================================================
# COLUMN SPLITTING (NEW)
# =============================================================================

@router.post("/vacuum/split-column")
async def split_column(request: SplitColumnRequest):
    """
    Manually split a merged column based on user-defined pattern.
    """
    if not VACUUM_AVAILABLE:
        raise HTTPException(501, "Vacuum extractor not available")
    
    try:
        extractor = get_vacuum_extractor()
        
        # Get the extract
        extract = extractor.get_extract_by_id(request.extract_id)
        if not extract:
            raise HTTPException(404, "Extract not found")
        
        raw_data = extract.get('raw_data', [])
        raw_headers = extract.get('raw_headers', [])
        
        if not raw_data:
            raise HTTPException(400, "No data to split")
        
        # Perform the split
        if request.split_method == 'pattern' and request.pattern:
            new_data, new_cols = split_by_pattern(
                raw_data, request.column_index, request.pattern, request.new_headers or []
            )
        elif request.split_method == 'positions' and request.positions:
            new_data, new_cols = split_by_positions(
                raw_data, request.column_index, request.positions, request.new_headers or []
            )
        elif request.split_method == 'delimiter' and request.delimiter:
            new_data, new_cols = split_by_delimiter(
                raw_data, request.column_index, request.delimiter, request.new_headers or []
            )
        else:
            raise HTTPException(400, "Invalid split method or missing parameters")
        
        # Build new headers list
        new_raw_headers = list(raw_headers[:request.column_index]) + new_cols + list(raw_headers[request.column_index + 1:])
        
        # Update the extract in database
        success = extractor.update_extract_data(
            request.extract_id,
            raw_data=new_data,
            raw_headers=new_raw_headers,
            column_count=len(new_raw_headers),
            metadata={
                'was_manually_split': True,
                'split_details': {
                    'method': request.split_method,
                    'original_column': request.column_index,
                    'pattern': request.pattern,
                    'new_columns': new_cols
                }
            }
        )
        
        return {
            "success": success,
            "new_headers": new_raw_headers,
            "new_column_count": len(new_raw_headers),
            "rows_processed": len(new_data),
            "preview": new_data[:5]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error splitting column: {e}", exc_info=True)
        raise HTTPException(500, str(e))


@router.post("/vacuum/detect-pattern")
async def detect_pattern(request: DetectPatternRequest):
    """
    Auto-detect split pattern from sample data.
    Returns suggested patterns and how they would split the data.
    """
    try:
        if not request.sample_values:
            raise HTTPException(400, "No sample values provided")
        
        if SMART_EXTRACTOR_AVAILABLE:
            suggestions = detect_split_patterns(request.sample_values, request.section_type)
        else:
            # Fallback pattern detection
            suggestions = _fallback_detect_patterns(request.sample_values)
        
        return {
            "suggestions": suggestions,
            "sample_analyzed": request.sample_values[0][:100] if request.sample_values else ''
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error detecting pattern: {e}", exc_info=True)
        raise HTTPException(500, str(e))


def _fallback_detect_patterns(sample_values: list) -> list:
    """Simple fallback pattern detection"""
    suggestions = []
    
    if not sample_values:
        return suggestions
    
    first_val = str(sample_values[0])
    
    # Check for code + numbers pattern
    if re.search(r'[A-Z]+\s+[\d.]+', first_val):
        suggestions.append({
            'pattern': r'([A-Za-z]+)\s+([\d,]+\.?\d*)',
            'headers': ['Code', 'Amount'],
            'description': 'Code followed by number'
        })
    
    # Check for multiple numbers
    numbers = re.findall(r'[\d,]+\.?\d*', first_val)
    if len(numbers) >= 3:
        suggestions.append({
            'pattern': r'([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)',
            'headers': ['Value1', 'Value2', 'Value3'],
            'description': '3 numeric values'
        })
    
    return suggestions


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
        
        for ext in extracts:
            if ext.get('raw_data') and len(ext['raw_data']) > 5:
                ext['preview'] = ext['raw_data'][:5]
                ext['raw_data'] = None
        
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
    """Confirm or correct section detection."""
    if not VACUUM_AVAILABLE:
        raise HTTPException(501, "Vacuum extractor not available")
    
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
    """Confirm or correct column classification."""
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
    """Confirm multiple column mappings at once."""
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
    """Learn a vendor signature from confirmed extracts."""
    if not VACUUM_AVAILABLE:
        raise HTTPException(501, "Vacuum extractor not available")
    
    try:
        extractor = get_vacuum_extractor()
        
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
# RE-DETECTION
# =============================================================================

@router.post("/vacuum/redetect/{extract_id}")
async def redetect_extract(extract_id: int):
    """Re-run detection on an existing extract."""
    if not VACUUM_AVAILABLE:
        raise HTTPException(501, "Vacuum extractor not available")
    
    try:
        extractor = get_vacuum_extractor()
        extract = extractor.get_extract_by_id(extract_id)
        
        if not extract:
            raise HTTPException(404, "Extract not found")
        
        headers = extract.get('raw_headers', [])
        data = extract.get('raw_data', [])
        
        section_result = extractor.detect_section(headers, data, extract_id)
        col_results = extractor.classify_columns(headers, data, section_result.section_type)
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
# HEADER METADATA EXTRACTION
# =============================================================================

@router.get("/vacuum/header-metadata")
async def get_header_metadata(source_file: str):
    """Extract header metadata from a pay register document."""
    if not VACUUM_AVAILABLE:
        raise HTTPException(501, "Vacuum extractor not available")
    
    try:
        extractor = get_vacuum_extractor()
        metadata = extractor.extract_header_metadata(source_file)
        
        return {
            "success": True,
            "source_file": source_file,
            "metadata": metadata
        }
        
    except Exception as e:
        logger.error(f"Error extracting header metadata: {e}")
        return {
            "success": False,
            "source_file": source_file,
            "metadata": {
                "company": "",
                "pay_period_start": "",
                "pay_period_end": "",
                "check_date": ""
            }
        }


# =============================================================================
# FULL MAPPING WORKFLOW
# =============================================================================

@router.post("/vacuum/apply-mappings")
async def apply_all_mappings(request: ApplyMappingsRequest):
    """Apply all section mappings for a pay register."""
    if not VACUUM_AVAILABLE:
        raise HTTPException(501, "Vacuum extractor not available")
    
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
            
            if not column_map:
                continue
            
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
            
            if request.remember_for_vendor:
                for header, target in column_map.items():
                    try:
                        extractor.learn_column_mapping(
                            source_header=header,
                            target_column_type=target,
                            section_type=section,
                            source_file=request.source_file
                        )
                    except Exception as e:
                        logger.warning(f"Failed to learn mapping {header} -> {target}: {e}")
        
        return {
            "success": True,
            "source_file": request.source_file,
            "sections_processed": len(results),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error applying mappings: {e}")
        raise HTTPException(500, str(e))


# =============================================================================
# LEGACY MAPPING ENDPOINT
# =============================================================================

@router.post("/vacuum/apply-mapping")
async def apply_mapping(request: ColumnMappingRequest):
    """Apply column mapping to create a structured table (legacy endpoint)."""
    if not VACUUM_AVAILABLE:
        raise HTTPException(501, "Vacuum extractor not available")
    
    try:
        extractor = get_vacuum_extractor()
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
