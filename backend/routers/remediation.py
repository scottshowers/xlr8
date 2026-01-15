"""
Remediation Router - Phase 4A.6/4A.7
====================================

API endpoints for the Playbook Builder Wire-up and Progress Tracker.
Generates playbooks from findings, tracks action completion.

Endpoints:
- POST /remediation/generate - Generate playbook from findings
- GET /remediation/playbook/{playbook_id} - Get playbook details
- GET /remediation/playbook/{playbook_id}/progress - Get progress stats
- PATCH /remediation/playbook/{playbook_id}/action/{action_id}/status - Update action status
- GET /remediation/playbooks - List all playbooks for a project

Created: January 15, 2026 - Phase 4A.6/4A.7
"""

import logging
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
from fastapi import APIRouter, HTTPException, Query, Header
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# MODELS
# =============================================================================

class ActionStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETE = "complete"


class FindingInput(BaseModel):
    """Finding from the FindingsDashboard."""
    id: str
    severity: str
    category: str
    title: str
    subtitle: Optional[str] = None
    description: Optional[str] = None
    affected_count: int = 0
    affected_table: Optional[str] = None
    impact_value: Optional[str] = None
    recommended_actions: List[str] = []


class GeneratePlaybookRequest(BaseModel):
    """Request to generate a playbook from findings."""
    project_id: str
    project_name: str
    customer_name: str
    findings: List[FindingInput]
    default_assignee: str = "Project Lead"


class PlaybookAction(BaseModel):
    """A single action item in a playbook."""
    id: str
    playbook_id: str
    title: str
    description: str
    finding_id: Optional[str] = None
    sequence: int
    assignee_id: Optional[str] = None
    assignee_name: str = "Unassigned"
    due_date: str  # ISO date string
    effort_hours: float = 1.0
    status: ActionStatus = ActionStatus.PENDING
    blocked_reason: Optional[str] = None
    completed_at: Optional[str] = None
    notes: Optional[str] = None


class Playbook(BaseModel):
    """A remediation playbook."""
    id: str
    project_id: str
    project_name: str
    customer_name: str
    name: str
    description: Optional[str] = None
    actions: List[PlaybookAction]
    total_effort_hours: float
    created_at: str
    updated_at: str
    status: str = "active"


class PlaybookProgress(BaseModel):
    """Progress stats for a playbook."""
    playbook_id: str
    total: int
    complete: int
    in_progress: int
    blocked: int
    pending: int
    percent_complete: float
    risk_mitigated: float  # Dollar value
    go_live_readiness: float  # Percentage


class UpdateStatusRequest(BaseModel):
    """Request to update action status."""
    status: ActionStatus
    blocked_reason: Optional[str] = None
    notes: Optional[str] = None


# =============================================================================
# IN-MEMORY STORE
# =============================================================================

# Playbooks stored in memory (would be Supabase in production)
PLAYBOOKS: Dict[str, Playbook] = {}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def estimate_effort(action_text: str) -> float:
    """Estimate effort hours based on action text."""
    text_lower = action_text.lower()

    # Quick tasks
    if any(kw in text_lower for kw in ['review', 'check', 'verify', 'confirm']):
        return 0.5

    # Medium tasks
    if any(kw in text_lower for kw in ['update', 'fix', 'correct', 'modify', 'adjust']):
        return 2.0

    # Longer tasks
    if any(kw in text_lower for kw in ['implement', 'create', 'build', 'develop', 'design']):
        return 4.0

    # Analysis tasks
    if any(kw in text_lower for kw in ['analyze', 'investigate', 'assess', 'audit']):
        return 3.0

    return 1.0  # Default


def calculate_due_date(sequence: int, base_date: datetime = None) -> str:
    """Calculate staggered due dates based on sequence."""
    if base_date is None:
        base_date = datetime.now()

    # Stagger due dates: first few items due sooner
    if sequence <= 3:
        days_offset = sequence * 2
    elif sequence <= 6:
        days_offset = 6 + (sequence - 3) * 3
    else:
        days_offset = 15 + (sequence - 6) * 5

    due = base_date + timedelta(days=days_offset)
    return due.strftime("%Y-%m-%d")


def calculate_risk_value(finding: FindingInput) -> float:
    """Estimate dollar risk value from finding."""
    # Parse impact_value if available
    if finding.impact_value:
        import re
        match = re.search(r'\$?([\d,]+)', finding.impact_value)
        if match:
            try:
                return float(match.group(1).replace(',', ''))
            except ValueError:
                pass

    # Estimate based on severity and affected count
    base_value = {
        'critical': 5000,
        'warning': 1000,
        'info': 200
    }.get(finding.severity, 500)

    # Scale by affected count
    if finding.affected_count > 1000:
        multiplier = 3.0
    elif finding.affected_count > 100:
        multiplier = 2.0
    elif finding.affected_count > 10:
        multiplier = 1.5
    else:
        multiplier = 1.0

    return base_value * multiplier


def calculate_playbook_progress(playbook: Playbook) -> PlaybookProgress:
    """Calculate progress stats for a playbook."""
    actions = playbook.actions
    total = len(actions)

    complete = len([a for a in actions if a.status == ActionStatus.COMPLETE])
    in_progress = len([a for a in actions if a.status == ActionStatus.IN_PROGRESS])
    blocked = len([a for a in actions if a.status == ActionStatus.BLOCKED])
    pending = len([a for a in actions if a.status == ActionStatus.PENDING])

    percent_complete = (complete / total * 100) if total > 0 else 0

    # Calculate risk mitigated (sum of completed action risk values)
    # For now, estimate based on completed percentage of total effort
    total_risk = playbook.total_effort_hours * 250  # $250/hr baseline
    risk_mitigated = total_risk * (percent_complete / 100)

    # Go-live readiness considers blocked items as negative
    if blocked > 0:
        go_live_readiness = max(0, percent_complete - (blocked / total * 20))
    else:
        go_live_readiness = percent_complete

    return PlaybookProgress(
        playbook_id=playbook.id,
        total=total,
        complete=complete,
        in_progress=in_progress,
        blocked=blocked,
        pending=pending,
        percent_complete=round(percent_complete, 1),
        risk_mitigated=round(risk_mitigated, 0),
        go_live_readiness=round(go_live_readiness, 1)
    )


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/generate", response_model=Playbook)
async def generate_playbook(request: GeneratePlaybookRequest):
    """
    Generate a playbook from selected findings.

    Each finding generates 1-3 action items based on its
    recommended_actions field.
    """
    try:
        playbook_id = str(uuid.uuid4())
        actions = []
        total_effort = 0.0
        sequence = 1

        for finding in request.findings:
            # Use recommended actions if available, otherwise generate default
            rec_actions = finding.recommended_actions
            if not rec_actions:
                rec_actions = [f"Review and address: {finding.title}"]

            for rec_action in rec_actions:
                effort = estimate_effort(rec_action)
                total_effort += effort

                action = PlaybookAction(
                    id=str(uuid.uuid4()),
                    playbook_id=playbook_id,
                    title=rec_action,
                    description=f"From finding: {finding.title}",
                    finding_id=finding.id,
                    sequence=sequence,
                    assignee_name=request.default_assignee,
                    due_date=calculate_due_date(sequence),
                    effort_hours=effort,
                    status=ActionStatus.PENDING
                )
                actions.append(action)
                sequence += 1

        # Create playbook
        now = datetime.now().isoformat()
        playbook = Playbook(
            id=playbook_id,
            project_id=request.project_id,
            project_name=request.project_name,
            customer_name=request.customer_name,
            name=f"{request.customer_name} — Remediation Playbook",
            description=f"Generated from {len(request.findings)} findings",
            actions=actions,
            total_effort_hours=round(total_effort, 1),
            created_at=now,
            updated_at=now
        )

        # Store in memory
        PLAYBOOKS[playbook_id] = playbook

        logger.info(f"[REMEDIATION] Generated playbook {playbook_id} with {len(actions)} actions")

        return playbook

    except Exception as e:
        logger.error(f"[REMEDIATION] Error generating playbook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/playbook/{playbook_id}", response_model=Playbook)
async def get_playbook(playbook_id: str):
    """Get playbook details by ID."""
    if playbook_id not in PLAYBOOKS:
        raise HTTPException(status_code=404, detail=f"Playbook not found: {playbook_id}")

    return PLAYBOOKS[playbook_id]


@router.get("/playbook/{playbook_id}/progress", response_model=PlaybookProgress)
async def get_playbook_progress(playbook_id: str):
    """Get progress stats for a playbook."""
    if playbook_id not in PLAYBOOKS:
        raise HTTPException(status_code=404, detail=f"Playbook not found: {playbook_id}")

    playbook = PLAYBOOKS[playbook_id]
    return calculate_playbook_progress(playbook)


@router.patch("/playbook/{playbook_id}/action/{action_id}/status")
async def update_action_status(
    playbook_id: str,
    action_id: str,
    request: UpdateStatusRequest
):
    """Update the status of a playbook action."""
    if playbook_id not in PLAYBOOKS:
        raise HTTPException(status_code=404, detail=f"Playbook not found: {playbook_id}")

    playbook = PLAYBOOKS[playbook_id]

    # Find and update the action
    action_found = False
    for i, action in enumerate(playbook.actions):
        if action.id == action_id:
            # Update status
            playbook.actions[i].status = request.status

            # Handle status-specific updates
            if request.status == ActionStatus.BLOCKED:
                playbook.actions[i].blocked_reason = request.blocked_reason
            elif request.status == ActionStatus.COMPLETE:
                playbook.actions[i].completed_at = datetime.now().isoformat()
                playbook.actions[i].blocked_reason = None
            elif request.status == ActionStatus.IN_PROGRESS:
                playbook.actions[i].blocked_reason = None

            if request.notes:
                playbook.actions[i].notes = request.notes

            action_found = True
            break

    if not action_found:
        raise HTTPException(status_code=404, detail=f"Action not found: {action_id}")

    # Update playbook timestamp
    playbook.updated_at = datetime.now().isoformat()

    # Return updated progress
    progress = calculate_playbook_progress(playbook)

    return {
        "success": True,
        "action_id": action_id,
        "new_status": request.status.value,
        "progress": progress
    }


@router.get("/playbooks")
async def list_playbooks(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    x_project_id: Optional[str] = Header(None, alias="X-Project-ID")
):
    """List all playbooks, optionally filtered by project."""
    filter_project = project_id or x_project_id

    result = []
    for playbook in PLAYBOOKS.values():
        if filter_project and playbook.project_id != filter_project:
            continue

        progress = calculate_playbook_progress(playbook)
        result.append({
            "id": playbook.id,
            "name": playbook.name,
            "customer_name": playbook.customer_name,
            "project_name": playbook.project_name,
            "total_actions": len(playbook.actions),
            "percent_complete": progress.percent_complete,
            "created_at": playbook.created_at,
            "status": playbook.status
        })

    # Sort by created_at descending
    result.sort(key=lambda x: x['created_at'], reverse=True)

    return {
        "playbooks": result,
        "count": len(result)
    }


@router.delete("/playbook/{playbook_id}")
async def delete_playbook(playbook_id: str):
    """Delete a playbook."""
    if playbook_id not in PLAYBOOKS:
        raise HTTPException(status_code=404, detail=f"Playbook not found: {playbook_id}")

    del PLAYBOOKS[playbook_id]

    return {"success": True, "message": f"Playbook {playbook_id} deleted"}
