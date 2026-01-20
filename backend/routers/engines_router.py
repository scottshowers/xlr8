"""
XLR8 ENGINES ROUTER - Universal Analysis Engines API
=====================================================

Deploy to: backend/routers/engines_router.py

Provides direct access to the 5 universal engines:
- AGGREGATE: COUNT, SUM, AVG, GROUP BY
- COMPARE: Diff two datasets
- VALIDATE: Check rules (format, range, referential)
- DETECT: Find patterns (duplicates, orphans, outliers)
- MAP: Transform values (crosswalks, lookups)

ENDPOINTS:
- POST /api/engines/{project}/aggregate  - Run aggregate query
- POST /api/engines/{project}/compare    - Compare two tables
- POST /api/engines/{project}/validate   - Validate data quality
- POST /api/engines/{project}/detect     - Detect patterns
- POST /api/engines/{project}/map        - Map/transform values
- POST /api/engines/{project}/execute    - Generic engine execution
- POST /api/engines/{project}/batch      - Execute multiple engines

Used by: Playbook Builder, Feature Library, automated analysis

Created: January 17, 2026
"""

import logging
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(tags=["engines"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class EngineRequest(BaseModel):
    """Generic engine request."""
    config: Dict[str, Any]


class AggregateRequest(BaseModel):
    """Request for aggregate engine."""
    source_table: Optional[str] = None
    question: Optional[str] = None  # Natural language alternative
    measures: Optional[List[Dict]] = None  # [{"function": "COUNT", "column": "id"}]
    dimensions: Optional[List[str]] = None  # ["state", "department"]
    filters: Optional[List[Dict]] = None  # [{"column": "status", "operator": "=", "value": "A"}]
    order_by: Optional[str] = None
    limit: Optional[int] = None


class CompareRequest(BaseModel):
    """Request for compare engine."""
    source_a: str
    source_b: str
    match_keys: Optional[List[str]] = None  # Auto-detect if not provided
    compare_columns: Optional[List[str]] = None  # All if not provided
    ignore_columns: Optional[List[str]] = None
    limit: Optional[int] = None


class ValidateRequest(BaseModel):
    """Request for validate engine."""
    source_table: str
    rules: List[Dict]  # [{"field": "email", "type": "format", "pattern": "email"}]
    sample_limit: Optional[int] = 10


class DetectRequest(BaseModel):
    """Request for detect engine."""
    source_table: str
    patterns: List[Dict]  # [{"type": "duplicate", "columns": ["ssn"]}]
    sample_limit: Optional[int] = 10


class MapRequest(BaseModel):
    """Request for map engine."""
    mode: str = "transform"  # transform, crosswalk, lookup
    # For transform mode
    source_table: Optional[str] = None
    mappings: Optional[List[Dict]] = None  # [{"column": "state", "type": "state_names"}]
    output_table: Optional[str] = None
    # For crosswalk mode
    target_table: Optional[str] = None
    source_column: Optional[str] = None
    target_column: Optional[str] = None
    match_on: Optional[str] = "description"
    # For lookup mode
    value: Optional[str] = None
    type: Optional[str] = None


class BatchRequest(BaseModel):
    """Request for batch engine execution."""
    operations: List[Dict]  # [{"engine": "aggregate", "config": {...}}, ...]


class EngineResponse(BaseModel):
    """Standard engine response."""
    success: bool
    engine: str
    status: str
    row_count: int
    columns: Optional[List[str]] = None
    data: Optional[List[Dict]] = None
    sql: Optional[str] = None
    summary: Optional[str] = None
    findings: Optional[List[Dict]] = None
    metadata: Optional[Dict] = None
    provenance: Optional[Dict] = None
    error: Optional[str] = None


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _get_engine_module():
    """Import the engines module."""
    try:
        from backend.engines import (
            AggregateEngine, CompareEngine, ValidateEngine,
            DetectEngine, MapEngine, get_engine, EngineType
        )
        return {
            'AggregateEngine': AggregateEngine,
            'CompareEngine': CompareEngine,
            'ValidateEngine': ValidateEngine,
            'DetectEngine': DetectEngine,
            'MapEngine': MapEngine,
            'get_engine': get_engine,
            'EngineType': EngineType
        }
    except ImportError:
        try:
            from engines import (
                AggregateEngine, CompareEngine, ValidateEngine,
                DetectEngine, MapEngine, get_engine, EngineType
            )
            return {
                'AggregateEngine': AggregateEngine,
                'CompareEngine': CompareEngine,
                'ValidateEngine': ValidateEngine,
                'DetectEngine': DetectEngine,
                'MapEngine': MapEngine,
                'get_engine': get_engine,
                'EngineType': EngineType
            }
        except ImportError as e:
            logger.error(f"[ENGINES] Could not import engines: {e}")
            return None


def _get_connection(customer_id: str):
    """Get DuckDB connection for project."""
    try:
        from utils.structured_data_handler import get_structured_handler
        handler = get_structured_handler()
        return handler.conn
    except ImportError:
        from backend.utils.structured_data_handler import get_structured_handler
        handler = get_structured_handler()
        return handler.conn


def _result_to_response(engine_name: str, result) -> Dict:
    """Convert EngineResult to response dict."""
    return {
        'success': result.status.value in ['success', 'partial'],
        'engine': engine_name,
        'status': result.status.value,
        'row_count': result.row_count,
        'columns': result.columns,
        'data': result.data[:1000] if result.data else [],  # Limit response size
        'sql': result.sql,
        'summary': result.summary,
        'findings': [f.to_dict() for f in result.findings] if result.findings else [],
        'metadata': result.metadata,
        'provenance': result.provenance.to_dict() if result.provenance else None
    }


# =============================================================================
# AGGREGATE ENGINE
# =============================================================================

@router.post("/{customer_id}/aggregate")
async def run_aggregate(customer_id: str, request: AggregateRequest):
    """
    Run aggregate query (COUNT, SUM, AVG with GROUP BY).
    
    Example:
    ```json
    {
        "source_table": "employees",
        "measures": [{"function": "COUNT"}],
        "dimensions": ["state"]
    }
    ```
    
    Or with natural language:
    ```json
    {
        "question": "how many employees by state"
    }
    ```
    """
    try:
        engines = _get_engine_module()
        if not engines:
            raise HTTPException(status_code=500, detail="Engines module not available")
        
        conn = _get_connection(customer_id)
        engine = engines['AggregateEngine'](conn, customer_id)
        
        # Build config from request
        config = {}
        if request.question:
            config['question'] = request.question
        if request.source_table:
            config['source_table'] = request.source_table
        if request.measures:
            config['measures'] = request.measures
        if request.dimensions:
            config['dimensions'] = request.dimensions
        if request.filters:
            config['filters'] = request.filters
        if request.order_by:
            config['order_by'] = request.order_by
        if request.limit:
            config['limit'] = request.limit
        
        result = engine.execute(config)
        return _result_to_response('aggregate', result)
        
    except Exception as e:
        logger.error(f"[ENGINES] Aggregate error: {e}")
        import traceback
        return {
            'success': False,
            'engine': 'aggregate',
            'error': str(e),
            'traceback': traceback.format_exc()
        }


# =============================================================================
# COMPARE ENGINE
# =============================================================================

@router.post("/{customer_id}/compare")
async def run_compare(customer_id: str, request: CompareRequest):
    """
    Compare two tables/datasets.
    
    Example:
    ```json
    {
        "source_a": "census_file",
        "source_b": "payroll_file",
        "match_keys": ["employee_id"]
    }
    ```
    """
    try:
        engines = _get_engine_module()
        if not engines:
            raise HTTPException(status_code=500, detail="Engines module not available")
        
        conn = _get_connection(customer_id)
        engine = engines['CompareEngine'](conn, customer_id)
        
        config = {
            'source_a': request.source_a,
            'source_b': request.source_b
        }
        if request.match_keys:
            config['match_keys'] = request.match_keys
        if request.compare_columns:
            config['compare_columns'] = request.compare_columns
        if request.ignore_columns:
            config['ignore_columns'] = request.ignore_columns
        if request.limit:
            config['limit'] = request.limit
        
        result = engine.execute(config)
        return _result_to_response('compare', result)
        
    except Exception as e:
        logger.error(f"[ENGINES] Compare error: {e}")
        import traceback
        return {
            'success': False,
            'engine': 'compare',
            'error': str(e),
            'traceback': traceback.format_exc()
        }


# =============================================================================
# VALIDATE ENGINE
# =============================================================================

@router.post("/{customer_id}/validate")
async def run_validate(customer_id: str, request: ValidateRequest):
    """
    Validate data quality against rules.
    
    Example:
    ```json
    {
        "source_table": "employees",
        "rules": [
            {"field": "email", "type": "format", "pattern": "email"},
            {"field": "ssn", "type": "not_null"},
            {"field": "salary", "type": "range", "min": 0, "max": 1000000}
        ]
    }
    ```
    
    Rule types: format, range, referential, allowed_values, not_null, unique, custom
    """
    try:
        engines = _get_engine_module()
        if not engines:
            raise HTTPException(status_code=500, detail="Engines module not available")
        
        conn = _get_connection(customer_id)
        engine = engines['ValidateEngine'](conn, customer_id)
        
        config = {
            'source_table': request.source_table,
            'rules': request.rules,
            'sample_limit': request.sample_limit
        }
        
        result = engine.execute(config)
        return _result_to_response('validate', result)
        
    except Exception as e:
        logger.error(f"[ENGINES] Validate error: {e}")
        import traceback
        return {
            'success': False,
            'engine': 'validate',
            'error': str(e),
            'traceback': traceback.format_exc()
        }


# =============================================================================
# DETECT ENGINE
# =============================================================================

@router.post("/{customer_id}/detect")
async def run_detect(customer_id: str, request: DetectRequest):
    """
    Detect patterns in data.
    
    Example:
    ```json
    {
        "source_table": "employees",
        "patterns": [
            {"type": "duplicate", "columns": ["ssn"]},
            {"type": "orphan", "column": "department_id", "parent_table": "departments", "parent_column": "id"},
            {"type": "outlier", "column": "salary", "method": "zscore", "threshold": 3}
        ]
    }
    ```
    
    Pattern types: duplicate, orphan, outlier, anomaly, pattern
    """
    try:
        engines = _get_engine_module()
        if not engines:
            raise HTTPException(status_code=500, detail="Engines module not available")
        
        conn = _get_connection(customer_id)
        engine = engines['DetectEngine'](conn, customer_id)
        
        config = {
            'source_table': request.source_table,
            'patterns': request.patterns,
            'sample_limit': request.sample_limit
        }
        
        result = engine.execute(config)
        return _result_to_response('detect', result)
        
    except Exception as e:
        logger.error(f"[ENGINES] Detect error: {e}")
        import traceback
        return {
            'success': False,
            'engine': 'detect',
            'error': str(e),
            'traceback': traceback.format_exc()
        }


# =============================================================================
# MAP ENGINE
# =============================================================================

@router.post("/{customer_id}/map")
async def run_map(customer_id: str, request: MapRequest):
    """
    Map/transform values.
    
    Transform mode (apply mappings to table):
    ```json
    {
        "mode": "transform",
        "source_table": "employees",
        "mappings": [
            {"column": "state", "type": "state_names"},
            {"column": "status", "type": "lookup", "lookup_table": "status_codes"}
        ]
    }
    ```
    
    Crosswalk mode (generate mapping between value sets):
    ```json
    {
        "mode": "crosswalk",
        "source_table": "source_codes",
        "source_column": "code",
        "target_table": "target_codes",
        "target_column": "code"
    }
    ```
    
    Lookup mode (single value lookup):
    ```json
    {
        "mode": "lookup",
        "value": "TX",
        "type": "state_names"
    }
    ```
    """
    try:
        engines = _get_engine_module()
        if not engines:
            raise HTTPException(status_code=500, detail="Engines module not available")
        
        conn = _get_connection(customer_id)
        engine = engines['MapEngine'](conn, customer_id)
        
        config = {'mode': request.mode}
        
        if request.mode == 'transform':
            config['source_table'] = request.source_table
            config['mappings'] = request.mappings
            if request.output_table:
                config['output_table'] = request.output_table
        elif request.mode == 'crosswalk':
            config['source_table'] = request.source_table
            config['source_column'] = request.source_column
            config['target_table'] = request.target_table
            config['target_column'] = request.target_column
            config['match_on'] = request.match_on or 'description'
        elif request.mode == 'lookup':
            config['value'] = request.value
            config['type'] = request.type
        
        result = engine.execute(config)
        return _result_to_response('map', result)
        
    except Exception as e:
        logger.error(f"[ENGINES] Map error: {e}")
        import traceback
        return {
            'success': False,
            'engine': 'map',
            'error': str(e),
            'traceback': traceback.format_exc()
        }


# =============================================================================
# GENERIC EXECUTION
# =============================================================================

@router.post("/{customer_id}/execute")
async def execute_engine(customer_id: str, engine: str, request: EngineRequest):
    """
    Execute any engine with a config dict.
    
    Used by Playbook Builder for dynamic feature execution.
    
    Example:
    ```
    POST /api/engines/TEA1000/execute?engine=aggregate
    {
        "config": {
            "source_table": "employees",
            "measures": [{"function": "COUNT"}],
            "dimensions": ["state"]
        }
    }
    ```
    """
    try:
        engines_module = _get_engine_module()
        if not engines_module:
            raise HTTPException(status_code=500, detail="Engines module not available")
        
        engine_map = {
            'aggregate': engines_module['AggregateEngine'],
            'compare': engines_module['CompareEngine'],
            'validate': engines_module['ValidateEngine'],
            'detect': engines_module['DetectEngine'],
            'map': engines_module['MapEngine']
        }
        
        engine_class = engine_map.get(engine.lower())
        if not engine_class:
            raise HTTPException(
                status_code=400, 
                detail=f"Unknown engine: {engine}. Available: {list(engine_map.keys())}"
            )
        
        conn = _get_connection(customer_id)
        engine_instance = engine_class(conn, customer_id)
        result = engine_instance.execute(request.config)
        
        return _result_to_response(engine, result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ENGINES] Execute error: {e}")
        import traceback
        return {
            'success': False,
            'engine': engine,
            'error': str(e),
            'traceback': traceback.format_exc()
        }


# =============================================================================
# BATCH EXECUTION
# =============================================================================

@router.post("/{customer_id}/batch")
async def execute_batch(customer_id: str, request: BatchRequest):
    """
    Execute multiple engines in sequence.
    
    Used by Playbook Builder to run a full playbook.
    
    Example:
    ```json
    {
        "operations": [
            {
                "id": "step1",
                "engine": "validate",
                "config": {"source_table": "employees", "rules": [...]}
            },
            {
                "id": "step2", 
                "engine": "detect",
                "config": {"source_table": "employees", "patterns": [...]}
            },
            {
                "id": "step3",
                "engine": "aggregate",
                "config": {"source_table": "employees", "measures": [...]}
            }
        ]
    }
    ```
    """
    try:
        engines_module = _get_engine_module()
        if not engines_module:
            raise HTTPException(status_code=500, detail="Engines module not available")
        
        engine_map = {
            'aggregate': engines_module['AggregateEngine'],
            'compare': engines_module['CompareEngine'],
            'validate': engines_module['ValidateEngine'],
            'detect': engines_module['DetectEngine'],
            'map': engines_module['MapEngine']
        }
        
        conn = _get_connection(customer_id)
        results = []
        total_findings = 0
        
        for i, op in enumerate(request.operations):
            op_id = op.get('id', f'step_{i+1}')
            engine_name = op.get('engine', '').lower()
            config = op.get('config', {})
            
            engine_class = engine_map.get(engine_name)
            if not engine_class:
                results.append({
                    'id': op_id,
                    'success': False,
                    'engine': engine_name,
                    'error': f"Unknown engine: {engine_name}"
                })
                continue
            
            try:
                engine_instance = engine_class(conn, customer_id)
                result = engine_instance.execute(config)
                
                response = _result_to_response(engine_name, result)
                response['id'] = op_id
                results.append(response)
                
                if result.findings:
                    total_findings += len(result.findings)
                    
            except Exception as e:
                results.append({
                    'id': op_id,
                    'success': False,
                    'engine': engine_name,
                    'error': str(e)
                })
        
        # Summary
        passed = sum(1 for r in results if r.get('success'))
        
        return {
            'success': passed == len(request.operations),
            'customer_id': customer_id,
            'summary': f"{passed}/{len(request.operations)} operations succeeded",
            'total_findings': total_findings,
            'results': results
        }
        
    except Exception as e:
        logger.error(f"[ENGINES] Batch error: {e}")
        import traceback
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }


# =============================================================================
# SCHEMA/METADATA
# =============================================================================

# /{customer_id}/tables endpoint REMOVED - Use /api/customers/{customer_id}/tables instead


@router.get("/{customer_id}/table/{table_name}/columns")
async def get_table_columns(customer_id: str, table_name: str):
    """Get columns for a specific table."""
    try:
        conn = _get_connection(customer_id)
        
        columns = conn.execute(f"PRAGMA table_info('{table_name}')").fetchall()
        
        return {
            'table': table_name,
            'columns': [
                {
                    'name': col[1],
                    'type': col[2],
                    'nullable': not col[3],
                    'primary_key': bool(col[5])
                }
                for col in columns
            ],
            'count': len(columns)
        }
        
    except Exception as e:
        logger.error(f"[ENGINES] Columns error: {e}")
        return {
            'error': str(e)
        }


# =============================================================================
# EXPORT ENDPOINTS
# =============================================================================

class ExportRequest(BaseModel):
    """Request for export."""
    playbook_results: Dict[str, Any]  # Results from /batch endpoint
    template: str  # executive_summary, findings_report, etc.
    format: Optional[str] = None  # pdf, docx, xlsx, csv, json, html
    context: Optional[Dict[str, Any]] = None  # project_name, client_name, etc.


@router.get("/export/templates")
async def get_export_templates():
    """
    Get list of available export templates.
    
    Returns templates with their supported formats.
    """
    try:
        from backend.engines.export import get_export_templates
        return {
            'templates': get_export_templates()
        }
    except ImportError:
        try:
            from engines.export import get_export_templates
            return {
                'templates': get_export_templates()
            }
        except ImportError as e:
            return {
                'error': f'Export engine not available: {e}'
            }


@router.post("/{customer_id}/export")
async def export_results(customer_id: str, request: ExportRequest):
    """
    Export playbook results using a template.
    
    Example:
    ```json
    {
        "playbook_results": { ... },  // Results from /batch
        "template": "executive_summary",
        "format": "pdf",
        "context": {
            "project_name": "Acme Corp",
            "client_name": "Acme"
        }
    }
    ```
    
    Returns the file content as base64 for download.
    """
    try:
        try:
            from backend.engines.export import export_playbook_results
        except ImportError:
            from engines.export import export_playbook_results
        
        # Add project to context
        context = request.context or {}
        context['project_name'] = context.get('customer_id', customer_id)
        
        result = export_playbook_results(
            playbook_results=request.playbook_results,
            template=request.template,
            format=request.format,
            context=context
        )
        
        if not result.success:
            return {
                'success': False,
                'error': result.error
            }
        
        import base64
        
        return {
            'success': True,
            'template': result.template,
            'format': result.format,
            'filename': result.filename,
            'content_type': result.content_type,
            'content_base64': base64.b64encode(result.content).decode('utf-8'),
            'metadata': result.metadata
        }
        
    except Exception as e:
        logger.error(f"[ENGINES] Export error: {e}")
        import traceback
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }


@router.post("/{customer_id}/export/download")
async def export_download(customer_id: str, request: ExportRequest):
    """
    Export and return as downloadable file (streaming response).
    """
    from fastapi.responses import Response
    
    try:
        try:
            from backend.engines.export import export_playbook_results
        except ImportError:
            from engines.export import export_playbook_results
        
        context = request.context or {}
        context['project_name'] = context.get('customer_id', customer_id)
        
        result = export_playbook_results(
            playbook_results=request.playbook_results,
            template=request.template,
            format=request.format,
            context=context
        )
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.error)
        
        return Response(
            content=result.content,
            media_type=result.content_type,
            headers={
                'Content-Disposition': f'attachment; filename="{result.filename}"'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ENGINES] Export download error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
