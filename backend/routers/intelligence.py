"""
Intelligence Router - API Endpoints for Universal Analysis Engine
==================================================================

Exposes the ProjectIntelligenceService via REST API.

ENDPOINTS:
- GET  /intelligence/{project}/summary      - Get analysis summary
- GET  /intelligence/{project}/findings     - Get findings with filters
- GET  /intelligence/{project}/tasks        - Get tasks with filters
- GET  /intelligence/{project}/evidence/{id} - Get evidence package for finding
- POST /intelligence/{project}/analyze      - Trigger analysis (usually auto on upload)
- GET  /intelligence/{project}/lookups      - Get detected lookup tables
- GET  /intelligence/{project}/relationships - Get detected relationships
- POST /intelligence/{project}/stuck        - "I'm stuck" helper
- GET  /intelligence/{project}/work-trail   - Get work trail
- POST /intelligence/{project}/task/{id}/complete - Mark task complete
- POST /intelligence/{project}/collision-check - Check collision before action

Author: XLR8 Team
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel
import logging
import sys

sys.path.insert(0, '/app')

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Intelligence"])


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class AnalyzeRequest(BaseModel):
    """Request to trigger analysis."""
    tiers: Optional[List[str]] = ["instant", "fast"]  # tier1, tier2, tier3


class StuckRequest(BaseModel):
    """Request for 'I'm stuck' helper."""
    description: str


class CollisionCheckRequest(BaseModel):
    """Request to check collision before action."""
    action: str
    table: str
    filter_sql: Optional[str] = None
    affected_ids: Optional[List[str]] = None


class TaskCompleteRequest(BaseModel):
    """Request to mark task complete."""
    resolution_notes: Optional[str] = None
    resolution_type: Optional[str] = "completed"  # completed, skipped, false_positive


# =============================================================================
# HELPER - Get Intelligence Service
# =============================================================================

def _get_intelligence_service(project: str):
    """Get or create intelligence service for a project."""
    try:
        from backend.utils.project_intelligence import ProjectIntelligenceService, get_project_intelligence
        from utils.structured_data_handler import get_structured_handler
        
        handler = get_structured_handler()
        service = get_project_intelligence(project, handler)
        return service
        
    except ImportError as e:
        logger.error(f"[INTELLIGENCE_API] Import error: {e}")
        raise HTTPException(status_code=500, detail=f"Intelligence service not available: {e}")
    except Exception as e:
        logger.error(f"[INTELLIGENCE_API] Error getting service: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/{project}/summary")
async def get_summary(project: str):
    """
    Get intelligence summary for a project.
    
    Returns high-level stats: tables, rows, findings, tasks, scores.
    """
    try:
        service = _get_intelligence_service(project)
        
        # If not analyzed yet, return empty summary
        if not service.analyzed_at:
            return {
                'project': project,
                'analyzed': False,
                'message': 'Project not yet analyzed. Upload data or call /analyze.'
            }
        
        return {
            'project': project,
            'analyzed': True,
            'analyzed_at': service.analyzed_at.isoformat() if service.analyzed_at else None,
            'structure': {
                'total_tables': service.total_tables,
                'total_rows': service.total_rows,
                'total_columns': service.total_columns,
                'relationships': len(service.relationships),
                'lookups': len(service.lookups)
            },
            'findings': {
                'total': len(service.findings),
                'critical': len([f for f in service.findings if f.severity.value == 'critical']),
                'warning': len([f for f in service.findings if f.severity.value == 'warning']),
                'info': len([f for f in service.findings if f.severity.value == 'info'])
            },
            'tasks': {
                'total': len(service.tasks),
                'pending': len([t for t in service.tasks if t.status.value == 'pending']),
                'complete': len([t for t in service.tasks if t.status.value == 'complete'])
            },
            'tiers_complete': {
                'tier1': service.tier1_complete,
                'tier2': service.tier2_complete,
                'tier3': service.tier3_complete
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[INTELLIGENCE_API] Summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project}/findings")
async def get_findings(
    project: str,
    severity: Optional[str] = Query(None, description="Filter by severity: critical, warning, info"),
    category: Optional[str] = Query(None, description="Filter by category: STRUCTURE, QUALITY, RELATIONSHIP, PATTERN"),
    table: Optional[str] = Query(None, description="Filter by table name (partial match)")
):
    """
    Get findings for a project with optional filters.
    """
    try:
        service = _get_intelligence_service(project)
        findings = service.get_findings(severity=severity, category=category, table=table)
        
        return {
            'project': project,
            'total': len(findings),
            'filters': {
                'severity': severity,
                'category': category,
                'table': table
            },
            'findings': [f.to_dict() for f in findings]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[INTELLIGENCE_API] Findings error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project}/tasks")
async def get_tasks(
    project: str,
    status: Optional[str] = Query(None, description="Filter by status: pending, in_progress, complete, skipped"),
    severity: Optional[str] = Query(None, description="Filter by severity: critical, warning, info")
):
    """
    Get tasks for a project with optional filters.
    
    Tasks are actionable items generated from findings.
    Each task has a shortcut - the fastest way to resolve it.
    """
    try:
        service = _get_intelligence_service(project)
        tasks = service.get_tasks(status=status, severity=severity)
        
        return {
            'project': project,
            'total': len(tasks),
            'filters': {
                'status': status,
                'severity': severity
            },
            'tasks': [t.to_dict() for t in tasks]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[INTELLIGENCE_API] Tasks error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project}/evidence/{finding_id}")
async def get_evidence(project: str, finding_id: str):
    """
    Get full evidence package for a finding.
    
    ONE-CLICK DEFENSIBILITY:
    - The exact SQL query
    - The affected records
    - The standard/rule (if applicable)
    - Timestamp and data hash for proof
    """
    try:
        service = _get_intelligence_service(project)
        evidence = service.get_evidence(finding_id)
        
        if not evidence:
            raise HTTPException(status_code=404, detail=f"Finding '{finding_id}' not found")
        
        return {
            'project': project,
            'finding_id': finding_id,
            'evidence': evidence.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[INTELLIGENCE_API] Evidence error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project}/analyze")
async def analyze_project(project: str, request: AnalyzeRequest = None):
    """
    Trigger analysis for a project.
    
    Usually runs automatically on upload, but can be triggered manually.
    
    Tiers:
    - instant (Tier 1): ~5 seconds - structure, basic quality
    - fast (Tier 2): ~30 seconds - relationships, duplicates, lookups
    - background (Tier 3): ~2-3 minutes - patterns, correlations, anomalies
    """
    try:
        from backend.utils.project_intelligence import ProjectIntelligenceService, AnalysisTier
        from utils.structured_data_handler import get_structured_handler
        
        handler = get_structured_handler()
        service = ProjectIntelligenceService(project, handler)
        
        # Map tier names to enum
        tier_map = {
            'instant': AnalysisTier.TIER_1,
            'tier1': AnalysisTier.TIER_1,
            'fast': AnalysisTier.TIER_2,
            'tier2': AnalysisTier.TIER_2,
            'background': AnalysisTier.TIER_3,
            'tier3': AnalysisTier.TIER_3
        }
        
        tiers = []
        if request and request.tiers:
            for t in request.tiers:
                if t.lower() in tier_map:
                    tiers.append(tier_map[t.lower()])
        
        if not tiers:
            tiers = [AnalysisTier.TIER_1, AnalysisTier.TIER_2]
        
        # Run analysis
        result = service.analyze(tiers=tiers)
        
        # Track lineage: table → analysis, analysis → findings
        try:
            from utils.database.models import LineageModel, ProjectModel
            import uuid
            
            # Get project_id
            project_record = ProjectModel.get_by_name(project)
            project_id = project_record.get('id') if project_record else None
            
            # Generate analysis ID
            analysis_id = str(uuid.uuid4())[:8]
            
            # Get tables analyzed
            tables_analyzed = []
            if hasattr(service, 'tables') and service.tables:
                tables_analyzed = [t.get('name') or t.get('table_name') for t in service.tables if isinstance(t, dict)]
            elif hasattr(service, 'table_names'):
                tables_analyzed = service.table_names
            
            # Track table → analysis edges
            for table_name in tables_analyzed:
                LineageModel.track(
                    source_type=LineageModel.NODE_TABLE,
                    source_id=table_name,
                    target_type=LineageModel.NODE_ANALYSIS,
                    target_id=f"analysis_{analysis_id}",
                    relationship=LineageModel.REL_ANALYZED,
                    project_id=project_id,
                    metadata={'tiers': [t.value for t in tiers], 'project': project}
                )
            
            # Track analysis → findings edges
            findings_count = 0
            if hasattr(service, 'findings') and service.findings:
                findings_count = len(service.findings)
                for finding in service.findings[:50]:  # Limit to prevent too many edges
                    finding_id = getattr(finding, 'id', None) or str(uuid.uuid4())[:8]
                    LineageModel.track(
                        source_type=LineageModel.NODE_ANALYSIS,
                        source_id=f"analysis_{analysis_id}",
                        target_type=LineageModel.NODE_FINDING,
                        target_id=finding_id,
                        relationship=LineageModel.REL_GENERATED,
                        project_id=project_id,
                        metadata={
                            'severity': getattr(finding, 'severity', {}).value if hasattr(getattr(finding, 'severity', None), 'value') else 'unknown',
                            'category': getattr(finding, 'category', 'unknown')
                        }
                    )
            
            logger.info(f"[INTELLIGENCE_API] Tracked lineage: {len(tables_analyzed)} tables -> analysis -> {findings_count} findings")
            
        except Exception as lineage_error:
            logger.warning(f"[INTELLIGENCE_API] Lineage tracking failed (non-fatal): {lineage_error}")
        
        return {
            'project': project,
            'success': 'error' not in result,
            'analysis': result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[INTELLIGENCE_API] Analyze error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project}/lookups")
async def get_lookups(
    project: str,
    lookup_type: Optional[str] = Query(None, description="Filter by type: location, department, status, etc.")
):
    """
    Get detected lookup/reference tables.
    
    These are auto-decoded: "LOC001" → "Houston, TX (LOC001)"
    """
    try:
        service = _get_intelligence_service(project)
        lookups = service.lookups
        
        if lookup_type:
            lookups = [l for l in lookups if l.lookup_type == lookup_type]
        
        return {
            'project': project,
            'total': len(lookups),
            'lookups': [l.to_dict() for l in lookups]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[INTELLIGENCE_API] Lookups error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project}/metrics")
async def get_organizational_metrics(
    project: str,
    category: Optional[str] = Query(None, description="Filter by category: workforce, compensation, benefits, demographics, configuration, dimensional")
):
    """
    Get organizational metrics computed from data.
    
    These are the metrics every HR/Payroll/Benefits leader wants:
    - Headcount (total and by dimension)
    - Hub usage (configured vs in use)
    - Participation rates
    - Coverage gaps
    
    All computed dynamically from Context Graph and Lookups.
    """
    try:
        service = _get_intelligence_service(project)
        metrics = service.get_organizational_metrics(category)
        
        # Group by category for easier consumption
        by_category = {}
        for m in metrics:
            cat = m.category.value
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(m.to_dict())
        
        return {
            'project': project,
            'total': len(metrics),
            'by_category': by_category,
            'metrics': [m.to_dict() for m in metrics]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[INTELLIGENCE_API] Metrics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project}/relationships")
async def get_relationships(project: str):
    """
    Get detected table relationships.
    
    Shows how tables connect (foreign keys, join paths).
    """
    try:
        service = _get_intelligence_service(project)
        
        return {
            'project': project,
            'total': len(service.relationships),
            'relationships': [r.to_dict() for r in service.relationships]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[INTELLIGENCE_API] Relationships error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project}/stuck")
async def help_stuck(project: str, request: StuckRequest):
    """
    The "I'M STUCK" button.
    
    Describe what you're trying to do, get guided help.
    """
    try:
        service = _get_intelligence_service(project)
        result = service.help_stuck(request.description)
        
        return {
            'project': project,
            'query': request.description,
            'help': result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[INTELLIGENCE_API] Stuck error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project}/work-trail")
async def get_work_trail(
    project: str,
    limit: int = Query(50, description="Number of entries to return")
):
    """
    Get work trail - auto-documentation of what was done.
    """
    try:
        service = _get_intelligence_service(project)
        entries = service.get_work_trail(limit=limit)
        
        return {
            'project': project,
            'total': len(entries),
            'entries': [e.to_dict() for e in entries]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[INTELLIGENCE_API] Work trail error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project}/task/{task_id}/complete")
async def complete_task(project: str, task_id: str, request: TaskCompleteRequest = None):
    """
    Mark a task as complete.
    """
    try:
        service = _get_intelligence_service(project)
        
        # Find the task
        task = next((t for t in service.tasks if t.id == task_id), None)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
        
        # Update task status
        from backend.utils.project_intelligence import TaskStatus
        from datetime import datetime
        
        task.status = TaskStatus.COMPLETE
        task.completed_at = datetime.now()
        
        # Log to work trail
        notes = request.resolution_notes if request else None
        service.log_action(
            action_type='task_complete',
            action_description=f"Completed task: {task.title}",
            actor='user',  # TODO: Get from auth
            task_id=task_id,
            details={
                'resolution_notes': notes,
                'resolution_type': request.resolution_type if request else 'completed'
            }
        )
        
        return {
            'project': project,
            'task_id': task_id,
            'status': 'complete',
            'message': f"Task '{task.title}' marked as complete"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[INTELLIGENCE_API] Task complete error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project}/collision-check")
async def check_collision(project: str, request: CollisionCheckRequest):
    """
    Check what will break if an action is taken.
    
    PROACTIVE COLLISION DETECTION:
    Before making changes, see the downstream impact.
    """
    try:
        service = _get_intelligence_service(project)
        warning = service.check_collision(
            action=request.action,
            table=request.table,
            filter_sql=request.filter_sql,
            affected_ids=request.affected_ids
        )
        
        if not warning:
            return {
                'project': project,
                'collision_detected': False,
                'message': 'No downstream impacts detected. Safe to proceed.'
            }
        
        return {
            'project': project,
            'collision_detected': True,
            'warning': warning.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[INTELLIGENCE_API] Collision check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project}/decode/{column}/{value}")
async def decode_value(project: str, column: str, value: str):
    """
    Decode a coded value using detected lookups.
    
    Example: /decode/location_code/LOC001 → "Houston, TX (LOC001)"
    """
    try:
        service = _get_intelligence_service(project)
        decoded = service.decode_value(column, value)
        
        return {
            'project': project,
            'column': column,
            'original': value,
            'decoded': decoded,
            'was_decoded': decoded != value
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[INTELLIGENCE_API] Decode error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# DIAGNOSTIC ENDPOINTS
# =============================================================================

@router.get("/{project}/diag/numeric-columns")
async def diag_numeric_columns(project: str):
    """
    Diagnostic: Show all numeric columns found for a project.
    
    This helps debug Evolution 3 (numeric comparisons) by showing
    what columns _find_numeric_columns() actually returns.
    """
    try:
        from utils.structured_data_handler import get_structured_handler
        from backend.utils.intelligence.term_index import TermIndex
        
        handler = get_structured_handler()
        conn = handler.conn
        
        # Get numeric columns via TermIndex
        term_index = TermIndex(conn, project)
        numeric_cols = []
        debug_info = {}
        try:
            numeric_cols = term_index._find_numeric_columns()
            debug_info['method'] = 'success'
        except Exception as e:
            debug_info['method'] = 'error'
            debug_info['error'] = str(e)
        
        # Also test the raw query directly
        try:
            raw_test = conn.execute("""
                SELECT DISTINCT table_name, column_name
                FROM _column_profiles
                WHERE project = ?
                  AND (LOWER(column_name) LIKE '%salary%' OR LOWER(column_name) LIKE '%amount%')
                LIMIT 10
            """, [project]).fetchall()
            debug_info['raw_query_results'] = len(raw_test)
            debug_info['raw_sample'] = [{'t': r[0], 'c': r[1]} for r in raw_test[:3]]
        except Exception as e:
            debug_info['raw_query_error'] = str(e)
        
        # Also query directly for salary/annual columns
        salary_cols = conn.execute("""
            SELECT table_name, column_name, inferred_type, distinct_count
            FROM _column_profiles
            WHERE project = ? AND LOWER(column_name) LIKE '%salary%'
            ORDER BY table_name
        """, [project]).fetchall()
        
        annual_cols = conn.execute("""
            SELECT table_name, column_name, inferred_type, distinct_count
            FROM _column_profiles
            WHERE project = ? AND LOWER(column_name) LIKE '%annual%'
            ORDER BY table_name
        """, [project]).fetchall()
        
        # Get all columns with numeric type
        numeric_type_cols = conn.execute("""
            SELECT table_name, column_name, inferred_type, min_value, max_value
            FROM _column_profiles
            WHERE project = ? AND inferred_type = 'numeric'
            ORDER BY table_name
            LIMIT 50
        """, [project]).fetchall()
        
        return {
            'project': project,
            'debug': debug_info,
            'numeric_by_pattern': [{'table': r[0], 'column': r[1]} for r in numeric_cols],
            'numeric_by_pattern_count': len(numeric_cols),
            'salary_columns': [{'table': r[0], 'column': r[1], 'type': r[2], 'distinct': r[3]} for r in salary_cols],
            'annual_columns': [{'table': r[0], 'column': r[1], 'type': r[2], 'distinct': r[3]} for r in annual_cols],
            'numeric_type_columns': [{'table': r[0], 'column': r[1], 'type': r[2], 'min': r[3], 'max': r[4]} for r in numeric_type_cols],
        }
        
    except Exception as e:
        logger.error(f"[DIAG] Numeric columns error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project}/diag/test-numeric")
async def diag_test_numeric(project: str, q: str = "salary above 75000"):
    """
    Diagnostic: Test numeric expression resolution directly.
    
    Example: /diag/test-numeric?q=salary above 75000
    """
    try:
        from utils.structured_data_handler import get_structured_handler
        from backend.utils.intelligence.term_index import TermIndex
        
        handler = get_structured_handler()
        conn = handler.conn
        term_index = TermIndex(conn, project)
        
        # Call resolve_numeric_expression directly
        matches = term_index.resolve_numeric_expression(q, full_question=q)
        
        return {
            'project': project,
            'query': q,
            'matches': [
                {
                    'table': m.table_name,
                    'column': m.column_name,
                    'operator': m.operator,
                    'value': m.match_value,
                    'confidence': m.confidence
                }
                for m in matches
            ],
            'match_count': len(matches)
        }
        
    except Exception as e:
        logger.error(f"[DIAG] Test numeric error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project}/diag/date-columns")
async def diag_date_columns(project: str):
    """
    Diagnostic: Show all date columns for Evolution 4.
    """
    try:
        from utils.structured_data_handler import get_structured_handler
        
        handler = get_structured_handler()
        conn = handler.conn
        
        # Get columns with date type
        date_type_cols = conn.execute("""
            SELECT table_name, column_name, inferred_type, distinct_count
            FROM _column_profiles
            WHERE project = ? AND inferred_type = 'date'
            ORDER BY table_name, column_name
        """, [project]).fetchall()
        
        # Get columns with date-like names
        date_name_cols = conn.execute("""
            SELECT table_name, column_name, inferred_type, distinct_count
            FROM _column_profiles
            WHERE project = ? 
              AND (LOWER(column_name) LIKE '%date%' 
                   OR LOWER(column_name) LIKE '%hire%'
                   OR LOWER(column_name) LIKE '%term%'
                   OR LOWER(column_name) LIKE '%birth%'
                   OR LOWER(column_name) LIKE '%effective%'
                   OR LOWER(column_name) LIKE '%start%'
                   OR LOWER(column_name) LIKE '%end%')
            ORDER BY table_name, column_name
            LIMIT 50
        """, [project]).fetchall()
        
        return {
            'project': project,
            'date_type_columns': [
                {'table': r[0], 'column': r[1], 'type': r[2], 'distinct': r[3]} 
                for r in date_type_cols
            ],
            'date_type_count': len(date_type_cols),
            'date_name_columns': [
                {'table': r[0], 'column': r[1], 'type': r[2], 'distinct': r[3]} 
                for r in date_name_cols
            ],
            'date_name_count': len(date_name_cols),
        }
        
    except Exception as e:
        logger.error(f"[DIAG] Date columns error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project}/diag/test-date")
async def diag_test_date(project: str, q: str = "last year"):
    """
    Diagnostic: Test date expression resolution directly.
    
    Example: /diag/test-date?q=last year
    Example: /diag/test-date?q=hired last year
    """
    try:
        from utils.structured_data_handler import get_structured_handler
        from backend.utils.intelligence.term_index import TermIndex
        
        handler = get_structured_handler()
        conn = handler.conn
        term_index = TermIndex(conn, project)
        
        # Call resolve_date_expression directly
        matches = term_index.resolve_date_expression(q, full_question=q)
        
        return {
            'project': project,
            'query': q,
            'matches': [
                {
                    'table': m.table_name,
                    'column': m.column_name,
                    'operator': m.operator,
                    'value': m.match_value,
                    'confidence': m.confidence,
                    'term_type': m.term_type
                }
                for m in matches
            ],
            'match_count': len(matches)
        }
        
    except Exception as e:
        logger.error(f"[DIAG] Test date error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project}/diag/test-deterministic")
async def diag_test_deterministic(project: str, q: str = "employees hired last year"):
    """
    Diagnostic: Test full deterministic path for a question.
    
    Shows what phrases are extracted and what term matches result.
    """
    import re
    try:
        from utils.structured_data_handler import get_structured_handler
        from backend.utils.intelligence.term_index import TermIndex
        
        handler = get_structured_handler()
        conn = handler.conn
        term_index = TermIndex(conn, project)
        
        question = q.lower()
        
        # Extract words
        words = [w.strip().lower() for w in re.split(r'\s+', question) if w.strip()]
        
        # Numeric phrase patterns
        numeric_phrase_patterns = [
            r'(?:above|over|more than|greater than|exceeds?)\s+[\$]?\d[\d,]*[kKmM]?',
            r'(?:below|under|less than)\s+[\$]?\d[\d,]*[kKmM]?',
            r'(?:at least|minimum|min)\s+[\$]?\d[\d,]*[kKmM]?',
            r'(?:at most|maximum|max)\s+[\$]?\d[\d,]*[kKmM]?',
            r'between\s+[\$]?\d[\d,]*[kKmM]?\s+and\s+[\$]?\d[\d,]*[kKmM]?',
        ]
        numeric_phrases = []
        for pattern in numeric_phrase_patterns:
            matches = re.findall(pattern, question)
            numeric_phrases.extend(matches)
        
        # Date phrase patterns
        date_phrase_patterns = [
            r'(?:hired|terminated|started|ended|born)\s+(?:last|this|next)\s+(?:year|month|quarter|week)',
            r'(?:hired|terminated|started|ended|born)\s+(?:in|during)\s+(?:20\d{2})',
            r'(?:last|this|next)\s+(?:year|month|quarter|week)',
            r'(?:in|during)\s+(?:20\d{2})',
        ]
        date_phrases = []
        for pattern in date_phrase_patterns:
            matches = re.findall(pattern, question)
            date_phrases.extend(matches)
        
        # EVOLUTION 5: OR phrase patterns
        or_pattern = r'(\w+)\s+or\s+(\w+)'
        or_matches = re.findall(or_pattern, question)
        or_phrases = [f"{m[0]} or {m[1]}" for m in or_matches]
        or_terms = []  # Individual terms from OR groups
        for m in or_matches:
            or_terms.extend([m[0], m[1]])
        
        # EVOLUTION 6: Negation phrase patterns (with position tracking to avoid duplicates)
        negation_phrases = []
        matched_positions = set()
        
        # First: "not in X" pattern (most specific)
        for match in re.finditer(r'not\s+in\s+(\w+)', question):
            negation_phrases.append(f"not {match.group(1)}")
            matched_positions.add(match.start())
        
        # Second: "not X" but skip if already matched by "not in X"
        for match in re.finditer(r'not\s+(\w+)', question):
            if match.start() not in matched_positions:
                term = match.group(1)
                if term != 'in':  # Skip standalone "not in"
                    negation_phrases.append(f"not {term}")
        
        # Other negation keywords
        for pattern in [r'excluding\s+(\w+)', r'except\s+(\w+)', r'without\s+(\w+)']:
            for match in re.finditer(pattern, question):
                negation_phrases.append(f"not {match.group(1)}")
        
        # Filter words
        phrase_words = set()
        for phrase in numeric_phrases + date_phrases + or_phrases + negation_phrases:
            phrase_words.update(phrase.split())
        if negation_phrases:
            phrase_words.update(['not', 'in', 'excluding', 'except', 'without'])
        filtered_words = [w for w in words if w not in phrase_words]
        
        # Combine terms - include all phrase types for resolution
        terms_to_resolve = filtered_words + numeric_phrases + date_phrases + or_phrases + negation_phrases
        
        # Resolve all terms
        term_matches = term_index.resolve_terms_enhanced(terms_to_resolve, detect_numeric=True, detect_dates=True, detect_or=True, detect_negation=True, full_question=q)
        
        # Resolve OR terms separately to check if they map to same column
        or_term_matches = []
        if or_terms:
            or_term_matches = term_index.resolve_terms(or_terms)
        
        return {
            'project': project,
            'question': q,
            'words_original': words,
            'numeric_phrases': numeric_phrases,
            'date_phrases': date_phrases,
            'or_phrases': or_phrases,
            'or_terms': or_terms,
            'negation_phrases': negation_phrases,
            'phrase_words_removed': list(phrase_words),
            'filtered_words': filtered_words,
            'terms_to_resolve': terms_to_resolve,
            'term_matches': [
                {
                    'term': m.term,
                    'table': m.table_name,
                    'column': m.column_name,
                    'operator': m.operator,
                    'value': m.match_value,
                    'confidence': m.confidence,
                    'term_type': getattr(m, 'term_type', None)
                }
                for m in term_matches
            ],
            'or_term_matches': [
                {
                    'term': m.term,
                    'table': m.table_name,
                    'column': m.column_name,
                    'operator': m.operator,
                    'value': m.match_value,
                    'confidence': m.confidence
                }
                for m in or_term_matches
            ],
            'match_count': len(term_matches)
        }
        
    except Exception as e:
        logger.error(f"[DIAG] Test deterministic error: {e}")
        import traceback
        return {
            'error': str(e),
            'traceback': traceback.format_exc()
        }


@router.get("/{project}/diag/test-aggregation")
async def diag_test_aggregation(project: str, q: str = "average salary"):
    """
    Diagnostic: Test aggregation intent detection.
    
    EVOLUTION 7: Shows detected aggregation keywords and target columns.
    """
    try:
        question_lower = q.lower()
        
        # Detect aggregation intent
        detected_intent = None
        if any(kw in question_lower for kw in ['average', 'avg ', 'mean ']):
            detected_intent = 'average'
        elif any(kw in question_lower for kw in ['minimum', 'min ', 'lowest ', 'smallest ']):
            detected_intent = 'minimum'
        elif any(kw in question_lower for kw in ['maximum', 'max ', 'highest ', 'largest ', 'biggest ']):
            detected_intent = 'maximum'
        elif any(kw in question_lower for kw in ['total ', 'sum ', 'sum of']):
            detected_intent = 'sum'
        elif any(kw in question_lower for kw in ['count', 'how many']):
            detected_intent = 'count'
        
        # Find numeric column candidates
        from utils.structured_data_handler import get_structured_handler
        handler = get_structured_handler()
        conn = handler.conn
        
        # Get column profiles for numeric columns
        numeric_query = f"""
            SELECT table_name, column_name, inferred_type, sample_values
            FROM _column_profiles
            WHERE LOWER(project) = LOWER('{project}')
            AND inferred_type IN ('float', 'integer', 'numeric')
            ORDER BY table_name, column_name
            LIMIT 50
        """
        numeric_cols = conn.execute(numeric_query).fetchall()
        
        return {
            'project': project,
            'question': q,
            'detected_intent': detected_intent,
            'agg_keywords_found': {
                'sum': any(kw in question_lower for kw in ['total ', 'sum ', 'sum of']),
                'average': any(kw in question_lower for kw in ['average', 'avg ', 'mean ']),
                'minimum': any(kw in question_lower for kw in ['minimum', 'min ', 'lowest ']),
                'maximum': any(kw in question_lower for kw in ['maximum', 'max ', 'highest ']),
                'count': any(kw in question_lower for kw in ['count', 'how many']),
            },
            'numeric_columns': [
                {
                    'table': row[0],
                    'column': row[1],
                    'type': row[2]
                }
                for row in numeric_cols
            ]
        }
        
    except Exception as e:
        logger.error(f"[DIAG] Test aggregation error: {e}")
        import traceback
        return {
            'error': str(e),
            'traceback': traceback.format_exc()
        }


# =============================================================================
# HEALTH CHECK
# =============================================================================

@router.get("/health")
async def health_check():
    """Health check for intelligence service."""
    return {
        'status': 'healthy',
        'service': 'intelligence',
        'version': '1.0.0'
    }
