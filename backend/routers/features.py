"""
Features Router - Comparison and Export API
============================================

Endpoints:
- POST /api/compare - Compare two tables
- POST /api/export/comparison - Export comparison result
- POST /api/export/data - Export generic data

Used by: Chat, BI, Playbooks, Analytics
"""

import logging
import io
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(tags=["features"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class CompareRequest(BaseModel):
    """Request to compare two tables."""
    table_a: str
    table_b: str
    join_keys: Optional[List[str]] = None
    compare_columns: Optional[List[str]] = None
    project_id: Optional[str] = None
    limit: int = 100


class CompareResponse(BaseModel):
    """Comparison result."""
    success: bool
    summary: str
    match_rate: float
    has_differences: bool
    matches: int
    mismatches: List[Dict[str, Any]]
    only_in_a: List[Dict[str, Any]]
    only_in_b: List[Dict[str, Any]]
    provenance: Dict[str, Any]


class ExportComparisonRequest(BaseModel):
    """Request to export a comparison."""
    table_a: str
    table_b: str
    join_keys: Optional[List[str]] = None
    compare_columns: Optional[List[str]] = None
    project_id: Optional[str] = None
    format: str = "xlsx"  # xlsx, csv, json
    limit: int = 100


class ExportDataRequest(BaseModel):
    """Request to export generic data."""
    data: List[Dict[str, Any]]
    format: str = "xlsx"
    sheet_name: str = "Data"
    title: Optional[str] = None
    provenance: Optional[Dict[str, Any]] = None


# =============================================================================
# COMPARISON ENDPOINTS
# =============================================================================

@router.post("/compare", response_model=CompareResponse)
async def compare_tables(request: CompareRequest):
    """
    Compare two DuckDB tables and return differences.
    
    Auto-detects join keys if not provided.
    Returns mismatches, only-in-A, only-in-B, and match statistics.
    
    Used by:
    - Chat: "Compare my Q1 vs Q2 payroll"
    - BI: Variance detection
    - Playbooks: Automatic comparison tasks
    """
    try:
        from utils.features.comparison_engine import compare
        
        logger.info(f"[COMPARE API] Comparing {request.table_a} vs {request.table_b}")
        
        result = compare(
            table_a=request.table_a,
            table_b=request.table_b,
            join_keys=request.join_keys,
            compare_columns=request.compare_columns,
            project_id=request.project_id,
            limit=request.limit
        )
        
        logger.info(f"[COMPARE API] Result: {result.summary}")
        
        return CompareResponse(
            success=True,
            summary=result.summary,
            match_rate=result.match_rate,
            has_differences=result.has_differences,
            matches=result.matches,
            mismatches=result.mismatches,
            only_in_a=result.only_in_a,
            only_in_b=result.only_in_b,
            provenance={
                "source_a": result.source_a,
                "source_b": result.source_b,
                "source_a_rows": result.source_a_rows,
                "source_b_rows": result.source_b_rows,
                "join_keys": result.join_keys,
                "compared_columns": result.compared_columns,
                "project_id": result.project_id,
                "comparison_id": result.comparison_id,
                "executed_at": result.executed_at
            }
        )
        
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"[COMPARE API] Error: {e}")
        raise HTTPException(500, f"Comparison failed: {str(e)}")


@router.get("/compare/tables")
async def list_comparable_tables(project_id: Optional[str] = None):
    """
    List tables available for comparison.
    
    Returns table names with row counts and column info.
    """
    try:
        from utils.structured_data_handler import get_read_handler
        
        handler = get_read_handler()
        
        # Get tables from schema metadata
        tables = handler.query("""
            SELECT table_name, file_name, row_count, columns, display_name
            FROM _schema_metadata
            WHERE is_current = TRUE
            ORDER BY file_name
        """)
        
        result = []
        for t in tables:
            # Parse columns
            columns = []
            if t.get('columns'):
                try:
                    import json
                    cols_data = json.loads(t['columns'])
                    if cols_data and isinstance(cols_data[0], dict):
                        columns = [c.get('name', '') for c in cols_data]
                    else:
                        columns = cols_data
                except Exception:
                    pass
            
            result.append({
                "table_name": t['table_name'],
                "file_name": t.get('file_name', ''),
                "display_name": t.get('display_name', t['table_name']),
                "row_count": t.get('row_count', 0),
                "columns": columns[:20]  # Limit columns returned
            })
        
        return {
            "tables": result,
            "count": len(result)
        }
        
    except Exception as e:
        logger.error(f"[COMPARE API] List tables error: {e}")
        raise HTTPException(500, str(e))


# =============================================================================
# EXPORT ENDPOINTS
# =============================================================================

@router.post("/export/comparison")
async def export_comparison(request: ExportComparisonRequest):
    """
    Compare two tables and export the results.
    
    Returns downloadable file in specified format.
    """
    try:
        from utils.features.comparison_engine import compare
        from utils.features.export_engine import export_comparison
        
        logger.info(f"[EXPORT API] Comparing and exporting {request.table_a} vs {request.table_b}")
        
        # Run comparison
        result = compare(
            table_a=request.table_a,
            table_b=request.table_b,
            join_keys=request.join_keys,
            compare_columns=request.compare_columns,
            project_id=request.project_id,
            limit=request.limit
        )
        
        # Export to file
        buffer = export_comparison(result, format=request.format)
        
        # Determine content type and filename
        if request.format == "xlsx":
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ext = "xlsx"
        elif request.format == "csv":
            media_type = "text/csv"
            ext = "csv"
        else:
            media_type = "application/json"
            ext = "json"
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"comparison_{timestamp}.{ext}"
        
        return StreamingResponse(
            iter([buffer.getvalue()]),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"[EXPORT API] Error: {e}")
        raise HTTPException(500, f"Export failed: {str(e)}")


@router.post("/export/data")
async def export_data(request: ExportDataRequest):
    """
    Export generic data to file.
    
    Accepts list of dicts and exports to specified format.
    Used by Chat, BI, Analytics for data exports.
    """
    try:
        from utils.features.export_engine import export_data
        
        if not request.data:
            raise HTTPException(400, "No data provided")
        
        logger.info(f"[EXPORT API] Exporting {len(request.data)} rows as {request.format}")
        
        buffer = export_data(
            data=request.data,
            format=request.format,
            sheet_name=request.sheet_name,
            title=request.title,
            provenance=request.provenance
        )
        
        # Determine content type and filename
        if request.format == "xlsx":
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ext = "xlsx"
        elif request.format == "csv":
            media_type = "text/csv"
            ext = "csv"
        else:
            media_type = "application/json"
            ext = "json"
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"export_{timestamp}.{ext}"
        
        return StreamingResponse(
            iter([buffer.getvalue()]),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"[EXPORT API] Error: {e}")
        raise HTTPException(500, f"Export failed: {str(e)}")


@router.get("/export/formats")
async def list_export_formats():
    """
    List available export formats and templates.
    """
    return {
        "formats": [
            {"id": "xlsx", "name": "Excel", "extension": ".xlsx", "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
            {"id": "csv", "name": "CSV", "extension": ".csv", "mime_type": "text/csv"},
            {"id": "json", "name": "JSON", "extension": ".json", "mime_type": "application/json"}
        ],
        "templates": [
            {"id": "comparison_report", "name": "Comparison Report", "formats": ["xlsx", "csv", "json"], "built_in": True},
            {"id": "data_extract", "name": "Data Extract", "formats": ["xlsx", "csv", "json"], "built_in": True}
        ]
    }
