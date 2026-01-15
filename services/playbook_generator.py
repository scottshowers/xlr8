"""
Playbook Generator Service
==========================

Generates playbooks from findings. Converts selected findings
into actionable playbook items with assignments, due dates, and estimates.

Phase 4A.6: Playbook Wire-up

Created: January 15, 2026
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from uuid import uuid4
from enum import Enum
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ActionStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETE = "complete"


class PlaybookAction(BaseModel):
    id: str
    sequence: int
    title: str
    description: str
    finding_id: Optional[str] = None
    finding_title: Optional[str] = None
    assignee_name: str = "Unassigned"
    assignee_id: Optional[str] = None
    due_date: str
    effort_hours: float = 2.0
    status: ActionStatus = ActionStatus.PENDING
    blocked_reason: Optional[str] = None
    completed_at: Optional[str] = None
    notes: Optional[str] = None


class Playbook(BaseModel):
    id: str
    project_id: str
    project_name: str
    customer_name: str
    name: str
    description: str
    actions: List[PlaybookAction]
    total_effort_hours: float
    status: str = "active"
    created_at: str
    created_by: Optional[str] = None
    completed_at: Optional[str] = None


class PlaybookProgress(BaseModel):
    playbook_id: str
    total: int
    complete: int
    in_progress: int
    blocked: int
    pending: int
    completion_percentage: float
    risk_mitigated: float
    go_live_readiness: float


def estimate_effort(action_text: str) -> float:
    """Estimate effort hours based on action keywords."""
    action_lower = action_text.lower()
    
    if any(kw in action_lower for kw in ['verify', 'check', 'confirm', 'export']):
        return 0.5
    if any(kw in action_lower for kw in ['investigate', 'analyze', 'research']):
        return 3.0
    if any(kw in action_lower for kw in ['correct', 'fix', 'update', 'modify']):
        return 2.0
    if any(kw in action_lower for kw in ['document', 'prepare', 'compile']):
        return 2.5
    if any(kw in action_lower for kw in ['implement', 'configure', 'migrate']):
        return 4.0
    return 2.0


def calculate_due_date(sequence: int, base_date: datetime = None) -> str:
    """Calculate staggered due date based on sequence."""
    if base_date is None:
        base_date = datetime.now()
    
    days_offset = 3 + (sequence - 1) * 2
    due = base_date + timedelta(days=days_offset)
    
    while due.weekday() >= 5:
        due += timedelta(days=1)
    
    return due.strftime('%Y-%m-%d')


def generate_playbook_from_findings(
    project_id: str,
    project_name: str,
    customer_name: str,
    findings: List[Dict[str, Any]],
    default_assignee: str = "Project Lead",
    playbook_name: Optional[str] = None
) -> Playbook:
    """
    Generate a playbook from selected findings.
    Each finding's recommended_actions become action items.
    """
    actions = []
    sequence = 1
    
    for finding in findings:
        finding_id = finding.get('id', str(uuid4()))
        finding_title = finding.get('title', 'Unknown Finding')
        recommended = finding.get('recommended_actions', [])
        
        if not recommended:
            recommended = [f"Address: {finding_title}"]
        
        for action_text in recommended:
            effort = estimate_effort(action_text)
            due = calculate_due_date(sequence)
            
            actions.append(PlaybookAction(
                id=str(uuid4()),
                sequence=sequence,
                title=action_text,
                description=f"From finding: {finding_title}",
                finding_id=finding_id,
                finding_title=finding_title,
                assignee_name=default_assignee,
                due_date=due,
                effort_hours=effort,
                status=ActionStatus.PENDING
            ))
            sequence += 1
    
    total_hours = sum(a.effort_hours for a in actions)
    name = playbook_name or f"{customer_name} — Remediation Playbook"
    
    return Playbook(
        id=str(uuid4()),
        project_id=project_id,
        project_name=project_name,
        customer_name=customer_name,
        name=name,
        description=f"Generated from {len(findings)} findings",
        actions=actions,
        total_effort_hours=total_hours,
        created_at=datetime.now().isoformat()
    )


def calculate_progress(playbook: Playbook) -> PlaybookProgress:
    """Calculate progress stats for a playbook."""
    actions = playbook.actions
    total = len(actions)
    
    complete = len([a for a in actions if a.status == ActionStatus.COMPLETE])
    in_progress = len([a for a in actions if a.status == ActionStatus.IN_PROGRESS])
    blocked = len([a for a in actions if a.status == ActionStatus.BLOCKED])
    pending = len([a for a in actions if a.status == ActionStatus.PENDING])
    
    completion_pct = (complete / total * 100) if total > 0 else 0
    
    # Risk mitigated = completed hours * $250/hr
    completed_hours = sum(a.effort_hours for a in actions if a.status == ActionStatus.COMPLETE)
    risk_mitigated = completed_hours * 250
    
    # Go-live readiness based on completion + blocked penalty
    readiness = completion_pct - (blocked * 5)
    readiness = max(0, min(100, readiness))
    
    return PlaybookProgress(
        playbook_id=playbook.id,
        total=total,
        complete=complete,
        in_progress=in_progress,
        blocked=blocked,
        pending=pending,
        completion_percentage=round(completion_pct, 1),
        risk_mitigated=risk_mitigated,
        go_live_readiness=round(readiness, 1)
    )


# Alias for backwards compatibility
calculate_playbook_progress = calculate_progress


# =============================================================================
# IN-MEMORY STORAGE (Replace with Supabase in production)
# =============================================================================

_playbooks: Dict[str, Playbook] = {}


def save_playbook(playbook: Playbook) -> Playbook:
    """Save a playbook to storage."""
    _playbooks[playbook.id] = playbook
    logger.info(f"Saved playbook {playbook.id}: {playbook.name}")
    return playbook


def get_playbook(playbook_id: str) -> Optional[Playbook]:
    """Get a playbook by ID."""
    return _playbooks.get(playbook_id)


def get_project_playbooks(project_id: str) -> List[Playbook]:
    """Get all playbooks for a project."""
    return [pb for pb in _playbooks.values() if pb.project_id == project_id]


def update_action_status(
    playbook_id: str, 
    action_id: str, 
    status: ActionStatus,
    blocked_reason: Optional[str] = None,
    notes: Optional[str] = None
) -> Optional[PlaybookAction]:
    """Update an action's status."""
    playbook = _playbooks.get(playbook_id)
    if not playbook:
        return None
    
    for action in playbook.actions:
        if action.id == action_id:
            action.status = status
            if status == ActionStatus.BLOCKED and blocked_reason:
                action.blocked_reason = blocked_reason
            elif status != ActionStatus.BLOCKED:
                action.blocked_reason = None
            if status == ActionStatus.COMPLETE:
                action.completed_at = datetime.now().isoformat()
            if notes:
                action.notes = notes
            return action
    
    return None


def delete_playbook(playbook_id: str) -> bool:
    """Delete a playbook."""
    if playbook_id in _playbooks:
        del _playbooks[playbook_id]
        logger.info(f"Deleted playbook {playbook_id}")
        return True
    return False
