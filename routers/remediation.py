"""
Remediation Router
==================

API endpoints for:
- Generating playbooks from findings (4A.6)
- Tracking playbook progress (4A.7)

Phase 4A.6 & 4A.7: Playbook Wire-up + Progress Tracker

Created: January 15, 2026
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

try:
    from services.playbook_generator import (
        generate_playbook_from_findings,
        calculate_playbook_progress,
        save_playbook,
        get_playbook,
        get_project_playbooks,
        update_action_status,
        delete_playbook,
        ActionStatus,
        Playbook,
        PlaybookProgress,
        PlaybookAction
    )
except ImportError:
    from backend.services.playbook_generator import (
        generate_playbook_from_findings,
        calculate_playbook_progress,
        save_playbook,
        get_playbook,
        get_project_playbooks,
        update_action_status,
        delete_playbook,
        ActionStatus,
        Playbook,
        PlaybookProgress,
        PlaybookAction
    )

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class FindingInput(BaseModel):
    """Finding data for playbook generation."""
    id: str
    title: str
    severity: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    impact_value: Optional[str] = None
    recommended_actions: List[str] = []


class GeneratePlaybookRequest(BaseModel):
    """Request to generate a playbook from findings."""
    customer_id: str
    customer_id: str
    customer_name: str
    findings: List[FindingInput]
    default_assignee: str = "Project Lead"
    playbook_name: Optional[str] = None


class UpdateActionRequest(BaseModel):
    """Request to update an action's status."""
    status: str  # pending, in_progress, blocked, complete
    blocked_reason: Optional[str] = None
    notes: Optional[str] = None


class UpdateAssigneeRequest(BaseModel):
    """Request to update action assignee."""
    assignee_name: str
    assignee_id: Optional[str] = None


class UpdateDueDateRequest(BaseModel):
    """Request to update action due date."""
    due_date: str  # ISO format


# =============================================================================
# PLAYBOOK GENERATION ENDPOINTS
# =============================================================================

@router.post("/remediation/generate", response_model=Playbook)
async def generate_remediation_playbook(request: GeneratePlaybookRequest):
    """
    Generate a remediation playbook from selected findings.
    
    Each finding's recommended_actions become action items.
    Actions are auto-assigned due dates and effort estimates.
    
    Returns the generated playbook with all actions.
    """
    try:
        if not request.findings:
            raise HTTPException(400, "No findings provided")
        
        # Convert to dicts for generator
        findings_data = [f.model_dump() for f in request.findings]
        
        playbook = generate_playbook_from_findings(
            customer_id=request.customer_id,
            customer_id=request.customer_id,
            customer_name=request.customer_name,
            findings=findings_data,
            default_assignee=request.default_assignee,
            playbook_name=request.playbook_name
        )
        
        # Save to store
        save_playbook(playbook)
        
        logger.info(f"[REMEDIATION] Generated playbook {playbook.id} with {len(playbook.actions)} actions")
        
        return playbook
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[REMEDIATION] Generation failed: {e}")
        raise HTTPException(500, f"Failed to generate playbook: {e}")


@router.get("/remediation/playbooks/{customer_id}")
async def list_project_playbooks(customer_id: str):
    """
    List all remediation playbooks for a project.
    """
    try:
        playbooks = get_project_playbooks(customer_id)
        
        # Include progress summary for each
        result = []
        for pb in playbooks:
            progress = calculate_playbook_progress(pb)
            result.append({
                "playbook": pb,
                "progress": progress
            })
        
        return {
            "customer_id": customer_id,
            "playbooks": result,
            "total": len(result)
        }
        
    except Exception as e:
        logger.error(f"[REMEDIATION] List failed: {e}")
        raise HTTPException(500, str(e))


# =============================================================================
# PLAYBOOK DETAIL ENDPOINTS
# =============================================================================

@router.get("/remediation/playbook/{playbook_id}", response_model=Playbook)
async def get_playbook_detail(playbook_id: str):
    """
    Get a specific playbook with all actions.
    """
    playbook = get_playbook(playbook_id)
    if not playbook:
        raise HTTPException(404, f"Playbook not found: {playbook_id}")
    return playbook


@router.get("/remediation/playbook/{playbook_id}/progress", response_model=PlaybookProgress)
async def get_playbook_progress_endpoint(playbook_id: str):
    """
    Get progress summary for a playbook.
    
    Returns:
    - Complete / In Progress / Blocked / Pending counts
    - Completion percentage
    - Risk mitigated ($ value)
    - Go-live readiness percentage
    """
    playbook = get_playbook(playbook_id)
    if not playbook:
        raise HTTPException(404, f"Playbook not found: {playbook_id}")
    
    progress = calculate_playbook_progress(playbook)
    return progress


@router.delete("/remediation/playbook/{playbook_id}")
async def delete_playbook_endpoint(playbook_id: str):
    """Delete a playbook."""
    success = delete_playbook(playbook_id)
    if not success:
        raise HTTPException(404, f"Playbook not found: {playbook_id}")
    return {"success": True, "playbook_id": playbook_id}


# =============================================================================
# ACTION UPDATE ENDPOINTS
# =============================================================================

@router.patch("/remediation/playbook/{playbook_id}/action/{action_id}/status")
async def update_action_status_endpoint(
    playbook_id: str,
    action_id: str,
    request: UpdateActionRequest
):
    """
    Update an action's status.
    
    Valid statuses: pending, in_progress, blocked, complete
    
    If status is 'blocked', provide blocked_reason.
    """
    try:
        # Validate status
        try:
            status = ActionStatus(request.status)
        except ValueError:
            raise HTTPException(400, f"Invalid status: {request.status}. Must be one of: pending, in_progress, blocked, complete")
        
        action = update_action_status(
            playbook_id=playbook_id,
            action_id=action_id,
            status=status,
            blocked_reason=request.blocked_reason,
            notes=request.notes
        )
        
        if not action:
            raise HTTPException(404, "Action or playbook not found")
        
        # Return updated progress
        playbook = get_playbook(playbook_id)
        progress = calculate_playbook_progress(playbook)
        
        return {
            "success": True,
            "action": action,
            "progress": progress
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[REMEDIATION] Status update failed: {e}")
        raise HTTPException(500, str(e))


@router.patch("/remediation/playbook/{playbook_id}/action/{action_id}/assignee")
async def update_action_assignee(
    playbook_id: str,
    action_id: str,
    request: UpdateAssigneeRequest
):
    """
    Update an action's assignee.
    """
    playbook = get_playbook(playbook_id)
    if not playbook:
        raise HTTPException(404, f"Playbook not found: {playbook_id}")
    
    for action in playbook.actions:
        if action.id == action_id:
            action.assignee_name = request.assignee_name
            if request.assignee_id:
                action.assignee_id = request.assignee_id
            return {"success": True, "action": action}
    
    raise HTTPException(404, f"Action not found: {action_id}")


@router.patch("/remediation/playbook/{playbook_id}/action/{action_id}/due-date")
async def update_action_due_date(
    playbook_id: str,
    action_id: str,
    request: UpdateDueDateRequest
):
    """
    Update an action's due date.
    """
    playbook = get_playbook(playbook_id)
    if not playbook:
        raise HTTPException(404, f"Playbook not found: {playbook_id}")
    
    for action in playbook.actions:
        if action.id == action_id:
            action.due_date = request.due_date
            return {"success": True, "action": action}
    
    raise HTTPException(404, f"Action not found: {action_id}")


# =============================================================================
# BULK OPERATIONS
# =============================================================================

@router.post("/remediation/playbook/{playbook_id}/bulk-update")
async def bulk_update_actions(
    playbook_id: str,
    action_ids: List[str],
    status: Optional[str] = None,
    assignee_name: Optional[str] = None
):
    """
    Bulk update multiple actions.
    """
    playbook = get_playbook(playbook_id)
    if not playbook:
        raise HTTPException(404, f"Playbook not found: {playbook_id}")
    
    updated = []
    for action in playbook.actions:
        if action.id in action_ids:
            if status:
                try:
                    action.status = ActionStatus(status)
                except ValueError:
                    pass
            if assignee_name:
                action.assignee_name = assignee_name
            updated.append(action.id)
    
    progress = calculate_playbook_progress(playbook)
    
    return {
        "success": True,
        "updated_count": len(updated),
        "updated_ids": updated,
        "progress": progress
    }
