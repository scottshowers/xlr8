"""
Vacuum Upload Router - API endpoints for vacuum extraction
==========================================================

Separate from normal uploads. Used for complex files where
we need to extract everything and map later.

Author: XLR8 Team
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict
import os
import logging
import tempfile
import shutil

logger = logging.getLogger(__name__)

router = APIRouter()

# Import vacuum extractor
try:
    from utils.vacuum_extractor import get_vacuum_extractor, VacuumExtractor
    VACUUM_AVAILABLE = True
except ImportError as e:
    VACUUM_AVAILABLE = False
    logger.warning(f"Vacuum extractor not available: {e}")


@router.get("/vacuum/status")
async def vacuum_status():
    """Check if vacuum extractor is available"""
    if not VACUUM_AVAILABLE:
        return {
            "available": False,
            "message": "Vacuum extractor not available. Check dependencies."
        }
    
    try:
        extractor = get_vacuum_extractor()
        files = extractor.get_files_summary()
        
        return {
            "available": True,
            "files_count": len(files),
            "total_tables": sum(f['table_count'] for f in files),
            "total_rows": sum(f['total_rows'] for f in files)
        }
    except Exception as e:
        return {
            "available": False,
            "error": str(e)
        }


@router.post("/vacuum/upload")
async def vacuum_upload(
    file: UploadFile = File(...),
    project: Optional[str] = Form(None)
):
    """
    Upload a file for vacuum extraction.
    
    Extracts ALL tables and data without interpretation.
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
        
        # Extract everything
        extractor = get_vacuum_extractor()
        result = extractor.vacuum_file(temp_path, project)
        
        return {
            "success": True,
            "source_file": filename,
            "project": project,
            "tables_found": result['tables_found'],
            "total_rows": result['total_rows'],
            "extracts": result['extracts'],
            "errors": result['errors']
        }
        
    except Exception as e:
        logger.error(f"Vacuum upload error: {e}", exc_info=True)
        raise HTTPException(500, str(e))
    
    finally:
        # Cleanup temp file
        shutil.rmtree(temp_dir, ignore_errors=True)


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
    """Get all extracts, optionally filtered"""
    if not VACUUM_AVAILABLE:
        raise HTTPException(501, "Vacuum extractor not available")
    
    try:
        extractor = get_vacuum_extractor()
        extracts = extractor.get_extracts(project, source_file)
        
        # Limit data size for response (don't send all rows)
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
    """Get full detail for a single extract"""
    if not VACUUM_AVAILABLE:
        raise HTTPException(501, "Vacuum extractor not available")
    
    try:
        extractor = get_vacuum_extractor()
        extract = extractor.get_extract_by_id(extract_id)
        
        if not extract:
            raise HTTPException(404, "Extract not found")
        
        # Limit data for preview
        if extract.get('raw_data') and len(extract['raw_data']) > preview_rows:
            extract['preview'] = extract['raw_data'][:preview_rows]
            extract['truncated'] = True
            extract['full_row_count'] = len(extract['raw_data'])
            # Keep full data available but note it's large
        else:
            extract['preview'] = extract.get('raw_data', [])
            extract['truncated'] = False
        
        return extract
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting extract: {e}")
        raise HTTPException(500, str(e))


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
    """Delete all vacuum extracts"""
    if not VACUUM_AVAILABLE:
        raise HTTPException(501, "Vacuum extractor not available")
    
    try:
        extractor = get_vacuum_extractor()
        count = extractor.delete_all_extracts()
        
        logger.warning(f"Vacuum data reset - {count} extracts deleted")
        
        return {
            "success": True,
            "deleted_extracts": count
        }
    except Exception as e:
        logger.error(f"Error resetting vacuum: {e}")
        raise HTTPException(500, str(e))


@router.post("/vacuum/extract/{extract_id}/map")
async def apply_mapping(
    extract_id: int,
    column_map: Dict[str, str],
    target_table: str
):
    """
    Apply column mapping to create a structured table.
    
    column_map: {"original_column": "target_column", ...}
    target_table: Name for the new table
    """
    if not VACUUM_AVAILABLE:
        raise HTTPException(501, "Vacuum extractor not available")
    
    try:
        extractor = get_vacuum_extractor()
        success = extractor.apply_mapping(extract_id, column_map, target_table)
        
        if success:
            return {
                "success": True,
                "message": f"Created table '{target_table}' from extract {extract_id}",
                "target_table": target_table
            }
        else:
            raise HTTPException(400, "Failed to apply mapping")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying mapping: {e}")
        raise HTTPException(500, str(e))


@router.post("/vacuum/suggest-mappings")
async def suggest_mappings(headers: List[str]):
    """Get mapping suggestions for column headers"""
    if not VACUUM_AVAILABLE:
        raise HTTPException(501, "Vacuum extractor not available")
    
    try:
        extractor = get_vacuum_extractor()
        suggestions = extractor.suggest_mappings(headers)
        
        return {
            "headers": headers,
            "suggestions": suggestions
        }
    except Exception as e:
        logger.error(f"Error getting suggestions: {e}")
        raise HTTPException(500, str(e))
