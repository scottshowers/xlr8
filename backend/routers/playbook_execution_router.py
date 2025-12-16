"""
PLAYBOOK EXECUTION API
======================

Endpoints for running playbooks and managing standard linkages.

Endpoints:
- POST /api/playbooks/execute/{playbook_id}  - Run a playbook
- GET  /api/playbooks/{playbook_id}/standards - Get linked standards
- POST /api/playbooks/{playbook_id}/standards - Link a standard
- DELETE /api/playbooks/{playbook_id}/standards/{standard_id} - Unlink
- GET  /api/playbooks/runs/{project_id} - Get run history
- GET  /api/playbooks/run/{run_id} - Get run details
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# MODELS
# =============================================================================

class ExecutePlaybookRequest(BaseModel):
    """Request to execute a playbook."""
    project_id: Optional[str] = None  # Can come from header
    run_by: str = "user"


class LinkStandardRequest(BaseModel):
    """Request to link a standard to a playbook."""
    standard_id: int
    usage_type: str = "compliance"  # compliance | reference | validation


class ExecutePlaybookResponse(BaseModel):
    """Response from playbook execution."""
    run_id: str
    playbook_id: str
    project_id: str
    status: str
    total_rules_checked: int
    violations_found: int
    warnings_found: int
    findings_summary: dict


# =============================================================================
# IMPORT ENGINE
# =============================================================================

def _get_engine():
    """Import the execution engine."""
    try:
        from utils.playbook_execution_engine import (
            execute_playbook,
            get_rules_for_playbook,
            get_linked_standards,
            link_standard_to_playbook,
            unlink_standard_from_playbook,
            get_available_standards,
            get_playbook_config
        )
        return {
            "execute_playbook": execute_playbook,
            "get_rules_for_playbook": get_rules_for_playbook,
            "get_linked_standards": get_linked_standards,
            "link_standard_to_playbook": link_standard_to_playbook,
            "unlink_standard_from_playbook": unlink_standard_from_playbook,
            "get_available_standards": get_available_standards,
            "get_playbook_config": get_playbook_config
        }
    except ImportError:
        try:
            from backend.utils.playbook_execution_engine import (
                execute_playbook,
                get_rules_for_playbook,
                get_linked_standards,
                link_standard_to_playbook,
                unlink_standard_from_playbook,
                get_available_standards,
                get_playbook_config
            )
            return {
                "execute_playbook": execute_playbook,
                "get_rules_for_playbook": get_rules_for_playbook,
                "get_linked_standards": get_linked_standards,
                "link_standard_to_playbook": link_standard_to_playbook,
                "unlink_standard_from_playbook": unlink_standard_from_playbook,
                "get_available_standards": get_available_standards,
                "get_playbook_config": get_playbook_config
            }
        except ImportError as e:
            logger.error(f"[PLAYBOOK-API] Could not import engine: {e}")
            return None


def _get_supabase():
    """Get Supabase client."""
    import os
    try:
        from supabase import create_client
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
        if url and key:
            return create_client(url, key)
    except Exception as e:
        logger.warning(f"[PLAYBOOK-API] Supabase not available: {e}")
    return None


# =============================================================================
# EXECUTE PLAYBOOK
# =============================================================================

@router.post("/playbooks/execute/{playbook_id}")
async def execute_playbook_endpoint(
    playbook_id: str,
    request: ExecutePlaybookRequest,
    x_project_id: Optional[str] = Header(None, alias="X-Project-ID")
):
    """
    Execute a playbook against a project.
    
    This runs all steps in the playbook, using rules from linked standards
    to perform compliance checks against the project's data.
    
    Returns run results including findings.
    """
    engine = _get_engine()
    if not engine:
        raise HTTPException(503, "Playbook engine not available")
    
    # Get project ID from request or header
    project_id = request.project_id or x_project_id
    if not project_id:
        raise HTTPException(400, "Project ID required (in body or X-Project-ID header)")
    
    logger.info(f"[PLAYBOOK-API] Executing {playbook_id} for project {project_id}")
    
    try:
        result = engine["execute_playbook"](
            playbook_id=playbook_id,
            project_id=project_id,
            run_by=request.run_by
        )
        
        return {
            "run_id": result.run_id,
            "playbook_id": result.playbook_id,
            "project_id": result.project_id,
            "status": result.status,
            "started_at": result.started_at,
            "completed_at": result.completed_at,
            "total_rules_checked": result.total_rules_checked,
            "violations_found": result.violations_found,
            "warnings_found": result.warnings_found,
            "findings_summary": result.deliverables.get("compliance_summary", {}),
            "findings_by_severity": result.deliverables.get("findings_by_severity", {}),
            "findings": [
                {
                    "finding_id": f.finding_id,
                    "title": f.title,
                    "severity": f.severity,
                    "category": f.category,
                    "condition": f.condition,
                    "criteria": f.criteria,
                    "corrective_action": f.corrective_action,
                    "affected_count": f.affected_count,
                    "source_document": f.source_document
                }
                for f in result.all_findings
            ]
        }
        
    except Exception as e:
        logger.error(f"[PLAYBOOK-API] Execution failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(500, f"Playbook execution failed: {str(e)}")


# =============================================================================
# STANDARD LINKAGE
# =============================================================================

@router.get("/playbooks/{playbook_id}/standards")
async def get_playbook_standards(playbook_id: str):
    """
    Get standards linked to a playbook.
    
    Returns list of linked standards with their rule counts.
    """
    engine = _get_engine()
    if not engine:
        raise HTTPException(503, "Playbook engine not available")
    
    try:
        linked = engine["get_linked_standards"](playbook_id)
        rules = engine["get_rules_for_playbook"](playbook_id)
        
        return {
            "playbook_id": playbook_id,
            "linked_standards": [
                {
                    "standard_id": ls.get("standard_id"),
                    "usage_type": ls.get("usage_type"),
                    "standard": ls.get("standards", {})
                }
                for ls in linked
            ],
            "total_rules": len(rules),
            "rules_summary": {
                "by_severity": {},
                "by_category": {}
            }
        }
        
    except Exception as e:
        logger.error(f"[PLAYBOOK-API] Failed to get standards: {e}")
        raise HTTPException(500, f"Failed to get linked standards: {str(e)}")


@router.post("/playbooks/{playbook_id}/standards")
async def link_standard(playbook_id: str, request: LinkStandardRequest):
    """
    Link a standard to a playbook.
    
    The playbook will use rules from this standard during compliance checks.
    """
    engine = _get_engine()
    if not engine:
        raise HTTPException(503, "Playbook engine not available")
    
    try:
        success = engine["link_standard_to_playbook"](
            playbook_id=playbook_id,
            standard_id=request.standard_id,
            usage_type=request.usage_type
        )
        
        if success:
            return {
                "success": True,
                "message": f"Standard {request.standard_id} linked to playbook {playbook_id}"
            }
        else:
            raise HTTPException(500, "Failed to link standard")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[PLAYBOOK-API] Failed to link standard: {e}")
        raise HTTPException(500, f"Failed to link standard: {str(e)}")


@router.delete("/playbooks/{playbook_id}/standards/{standard_id}")
async def unlink_standard(playbook_id: str, standard_id: int):
    """
    Unlink a standard from a playbook.
    """
    engine = _get_engine()
    if not engine:
        raise HTTPException(503, "Playbook engine not available")
    
    try:
        success = engine["unlink_standard_from_playbook"](
            playbook_id=playbook_id,
            standard_id=standard_id
        )
        
        if success:
            return {"success": True, "message": "Standard unlinked"}
        else:
            raise HTTPException(500, "Failed to unlink standard")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[PLAYBOOK-API] Failed to unlink standard: {e}")
        raise HTTPException(500, f"Failed to unlink standard: {str(e)}")


@router.get("/playbooks/available-standards")
async def list_available_standards():
    """
    Get all standards available for linking to playbooks.
    """
    engine = _get_engine()
    if not engine:
        raise HTTPException(503, "Playbook engine not available")
    
    try:
        standards = engine["get_available_standards"]()
        return {
            "standards": standards,
            "count": len(standards)
        }
    except Exception as e:
        logger.error(f"[PLAYBOOK-API] Failed to list standards: {e}")
        raise HTTPException(500, str(e))


# =============================================================================
# RUN HISTORY
# =============================================================================

@router.get("/playbooks/runs/{project_id}")
async def get_project_runs(project_id: str, limit: int = 20):
    """
    Get playbook run history for a project.
    """
    supabase = _get_supabase()
    if not supabase:
        raise HTTPException(503, "Database not available")
    
    try:
        result = supabase.table("playbook_runs")\
            .select("run_id, playbook_id, status, started_at, completed_at, "
                   "total_rules_checked, violations_found, warnings_found")\
            .eq("project_id", project_id)\
            .order("started_at", desc=True)\
            .limit(limit)\
            .execute()
        
        return {
            "project_id": project_id,
            "runs": result.data or [],
            "count": len(result.data or [])
        }
        
    except Exception as e:
        logger.error(f"[PLAYBOOK-API] Failed to get runs: {e}")
        raise HTTPException(500, str(e))


@router.get("/playbooks/run/{run_id}")
async def get_run_details(run_id: str):
    """
    Get detailed results of a specific playbook run.
    """
    supabase = _get_supabase()
    if not supabase:
        raise HTTPException(503, "Database not available")
    
    try:
        result = supabase.table("playbook_runs")\
            .select("*")\
            .eq("run_id", run_id)\
            .single()\
            .execute()
        
        if not result.data:
            raise HTTPException(404, f"Run not found: {run_id}")
        
        return result.data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[PLAYBOOK-API] Failed to get run: {e}")
        raise HTTPException(500, str(e))


# =============================================================================
# PLAYBOOK INFO WITH STANDARDS
# =============================================================================

@router.get("/playbooks/{playbook_id}/info")
async def get_playbook_info(playbook_id: str):
    """
    Get full playbook info including linked standards and rules.
    
    This is useful for the UI to show what a playbook will check.
    """
    engine = _get_engine()
    if not engine:
        raise HTTPException(503, "Playbook engine not available")
    
    try:
        config = engine["get_playbook_config"](playbook_id)
        if not config:
            raise HTTPException(404, f"Playbook not found: {playbook_id}")
        
        linked = engine["get_linked_standards"](playbook_id)
        rules = engine["get_rules_for_playbook"](playbook_id)
        
        return {
            "playbook_id": config.get("playbook_id"),
            "name": config.get("name"),
            "description": config.get("description"),
            "category": config.get("category"),
            "estimated_time": config.get("estimated_time"),
            "steps": config.get("steps", []),
            "linked_standards": [
                {
                    "id": ls.get("standard_id"),
                    "name": ls.get("standards", {}).get("title") or ls.get("standards", {}).get("filename"),
                    "domain": ls.get("standards", {}).get("domain")
                }
                for ls in linked
            ],
            "rules": [
                {
                    "rule_id": r.rule_id,
                    "title": r.title,
                    "severity": r.severity,
                    "category": r.category,
                    "source": r.source_document
                }
                for r in rules
            ],
            "total_rules": len(rules)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[PLAYBOOK-API] Failed to get info: {e}")
        raise HTTPException(500, str(e))
