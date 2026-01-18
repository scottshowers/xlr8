"""
PLAYBOOK FRAMEWORK ROUTER
=========================

API endpoints for the playbook framework.

Endpoints:
- GET  /api/playbooks/list                    - List available playbooks
- GET  /api/playbooks/{id}/definition         - Get playbook definition
- POST /api/playbooks/{id}/instance/{project} - Get or create instance
- GET  /api/playbooks/instance/{instance_id}  - Get instance details
- GET  /api/playbooks/instance/{instance_id}/progress - Get progress summary
- POST /api/playbooks/instance/{instance_id}/match    - Match files to requirements
- POST /api/playbooks/instance/{instance_id}/step/{step_id}/execute - Execute step
- POST /api/playbooks/instance/{instance_id}/execute-all - Execute all steps
- PUT  /api/playbooks/instance/{instance_id}/step/{step_id}/status - Update status
- PUT  /api/playbooks/instance/{instance_id}/finding/{finding_id}  - Update finding

Author: XLR8 Team
Created: January 18, 2026
"""

import logging
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/playbooks", tags=["playbook-framework"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class InstanceRequest(BaseModel):
    """Request to get or create an instance."""
    create_if_missing: bool = True


class MatchRequest(BaseModel):
    """Request to match files to requirements."""
    uploaded_files: List[str]


class ExecuteStepRequest(BaseModel):
    """Request to execute a step."""
    force_refresh: bool = False
    ai_context: Optional[str] = None


class UpdateStatusRequest(BaseModel):
    """Request to update step status."""
    status: str
    notes: Optional[str] = None
    ai_context: Optional[str] = None


class UpdateFindingRequest(BaseModel):
    """Request to update a finding."""
    status: str  # active, acknowledged, suppressed, resolved
    note: Optional[str] = None


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _get_framework():
    """Import framework components."""
    try:
        from backend.playbooks.framework import (
            get_query_service, get_match_service, 
            get_progress_service, get_execution_service,
            PlaybookType, StepStatus, FindingStatus
        )
        return {
            'query': get_query_service,
            'match': get_match_service,
            'progress': get_progress_service,
            'execution': get_execution_service,
            'PlaybookType': PlaybookType,
            'StepStatus': StepStatus,
            'FindingStatus': FindingStatus
        }
    except ImportError:
        try:
            from playbooks.framework import (
                get_query_service, get_match_service,
                get_progress_service, get_execution_service,
                PlaybookType, StepStatus, FindingStatus
            )
            return {
                'query': get_query_service,
                'match': get_match_service,
                'progress': get_progress_service,
                'execution': get_execution_service,
                'PlaybookType': PlaybookType,
                'StepStatus': StepStatus,
                'FindingStatus': FindingStatus
            }
        except ImportError as e:
            logger.error(f"[FRAMEWORK] Import failed: {e}")
            return None


# =============================================================================
# PLAYBOOK DEFINITION ENDPOINTS
# =============================================================================

@router.get("/list")
async def list_playbooks():
    """List all available playbooks."""
    fw = _get_framework()
    if not fw:
        raise HTTPException(status_code=500, detail="Framework not available")
    
    query_service = fw['query']()
    playbooks = query_service.list_available_playbooks()
    
    return {
        'success': True,
        'playbooks': playbooks
    }


@router.get("/{playbook_id}/definition")
async def get_playbook_definition(playbook_id: str):
    """Get playbook definition (steps, requirements, etc.)."""
    fw = _get_framework()
    if not fw:
        raise HTTPException(status_code=500, detail="Framework not available")
    
    query_service = fw['query']()
    definition = query_service.load_playbook(playbook_id)
    
    if not definition:
        raise HTTPException(status_code=404, detail=f"Playbook '{playbook_id}' not found")
    
    # Convert to dict for JSON response
    return {
        'success': True,
        'playbook': {
            'id': definition.id,
            'name': definition.name,
            'type': definition.type.value,
            'description': definition.description,
            'version': definition.version,
            'total_steps': len(definition.steps),
            'has_expert_path': definition.expert_path is not None,
            'steps': [
                {
                    'id': step.id,
                    'name': step.name,
                    'description': step.description,
                    'required_data': step.required_data,
                    'phase': step.phase,
                    'sequence': step.sequence,
                    'expert_path_skip': step.expert_path_skip,
                    'guidance': step.guidance,
                    'analysis_count': len(step.analysis),
                    'analysis': [
                        {
                            'engine': cfg.engine,
                            'config': cfg.config,
                            'description': cfg.description
                        }
                        for cfg in step.analysis
                    ]
                }
                for step in definition.steps
            ],
            'expert_path': definition.expert_path
        }
    }


# =============================================================================
# INSTANCE ENDPOINTS
# =============================================================================

@router.post("/{playbook_id}/instance/{project_id}")
async def get_or_create_instance(
    playbook_id: str, 
    project_id: str,
    request: InstanceRequest = InstanceRequest()
):
    """Get or create a playbook instance for a project."""
    fw = _get_framework()
    if not fw:
        raise HTTPException(status_code=500, detail="Framework not available")
    
    query_service = fw['query']()
    progress_service = fw['progress']()
    
    # Load playbook definition
    definition = query_service.load_playbook(playbook_id)
    if not definition:
        raise HTTPException(status_code=404, detail=f"Playbook '{playbook_id}' not found")
    
    # Get or create instance
    if request.create_if_missing:
        instance = progress_service.get_or_create_instance(definition, project_id)
    else:
        instance = progress_service.get_instance_for_project(playbook_id, project_id)
        if not instance:
            raise HTTPException(status_code=404, detail="Instance not found")
    
    return {
        'success': True,
        'instance_id': instance.id,
        'playbook_id': instance.playbook_id,
        'project_id': instance.project_id,
        'total_steps': instance.total_steps,
        'completed_steps': instance.completed_steps,
        'blocked_steps': instance.blocked_steps
    }


@router.get("/instance/{instance_id}")
async def get_instance(instance_id: str):
    """Get instance details."""
    fw = _get_framework()
    if not fw:
        raise HTTPException(status_code=500, detail="Framework not available")
    
    progress_service = fw['progress']()
    instance = progress_service.get_instance(instance_id)
    
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")
    
    return {
        'success': True,
        'instance': {
            'id': instance.id,
            'playbook_id': instance.playbook_id,
            'project_id': instance.project_id,
            'total_steps': instance.total_steps,
            'completed_steps': instance.completed_steps,
            'blocked_steps': instance.blocked_steps,
            'using_expert_path': instance.using_expert_path
        }
    }


@router.get("/instance/{instance_id}/progress")
async def get_instance_progress(instance_id: str):
    """Get progress summary for an instance."""
    fw = _get_framework()
    if not fw:
        raise HTTPException(status_code=500, detail="Framework not available")
    
    progress_service = fw['progress']()
    summary = progress_service.get_progress_summary(instance_id)
    
    if not summary:
        raise HTTPException(status_code=404, detail="Instance not found")
    
    return {
        'success': True,
        'progress': summary
    }


@router.get("/instance/{instance_id}/step/{step_id}")
async def get_step_progress(instance_id: str, step_id: str):
    """Get progress for a specific step."""
    fw = _get_framework()
    if not fw:
        raise HTTPException(status_code=500, detail="Framework not available")
    
    progress_service = fw['progress']()
    step_progress = progress_service.get_step_progress(instance_id, step_id)
    
    if not step_progress:
        raise HTTPException(status_code=404, detail="Step not found")
    
    return {
        'success': True,
        'step': step_progress
    }


# =============================================================================
# FILE MATCHING
# =============================================================================

@router.post("/instance/{instance_id}/match")
async def match_files(instance_id: str, request: MatchRequest):
    """Match uploaded files to step requirements."""
    fw = _get_framework()
    if not fw:
        raise HTTPException(status_code=500, detail="Framework not available")
    
    progress_service = fw['progress']()
    match_service = fw['match']()
    query_service = fw['query']()
    
    # Get instance
    instance = progress_service.get_instance(instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")
    
    # Get playbook definition
    definition = query_service.load_playbook(instance.playbook_id)
    if not definition:
        raise HTTPException(status_code=404, detail="Playbook not found")
    
    # Build step requirements map
    step_requirements = {}
    for step in definition.steps:
        if step.required_data:
            step_requirements[step.id] = step.required_data
    
    # Match files
    match_results = match_service.match_step_requirements(
        step_requirements, 
        request.uploaded_files
    )
    
    # Update progress for each step
    results = {}
    for step_id, step_matches in match_results.items():
        matched_files = [m.matched_file for m in step_matches.values() if m.matched_file]
        missing_data = [m.requirement for m in step_matches.values() if not m.matched_file]
        
        progress_service.update_step_files(instance_id, step_id, matched_files, missing_data)
        
        summary = match_service.get_match_summary(step_matches)
        results[step_id] = summary
    
    return {
        'success': True,
        'step_matches': results,
        'total_files': len(request.uploaded_files)
    }


# =============================================================================
# EXECUTION
# =============================================================================

@router.post("/instance/{instance_id}/step/{step_id}/execute")
async def execute_step(
    instance_id: str, 
    step_id: str,
    request: ExecuteStepRequest = ExecuteStepRequest()
):
    """Execute analysis for a specific step."""
    fw = _get_framework()
    if not fw:
        raise HTTPException(status_code=500, detail="Framework not available")
    
    progress_service = fw['progress']()
    query_service = fw['query']()
    
    # Get instance
    instance = progress_service.get_instance(instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")
    
    # Get playbook definition
    definition = query_service.load_playbook(instance.playbook_id)
    if not definition:
        raise HTTPException(status_code=404, detail="Playbook not found")
    
    # Find step
    step = None
    for s in definition.steps:
        if s.id == step_id:
            step = s
            break
    
    if not step:
        raise HTTPException(status_code=404, detail=f"Step '{step_id}' not found")
    
    # Execute
    execution_service = fw['execution'](instance.project_id)
    result = execution_service.execute_step(
        instance, 
        step,
        force_refresh=request.force_refresh,
        ai_context=request.ai_context
    )
    
    return result


@router.post("/instance/{instance_id}/execute-all")
async def execute_all_steps(instance_id: str):
    """Execute all steps in the playbook."""
    fw = _get_framework()
    if not fw:
        raise HTTPException(status_code=500, detail="Framework not available")
    
    progress_service = fw['progress']()
    query_service = fw['query']()
    
    # Get instance
    instance = progress_service.get_instance(instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")
    
    # Get playbook definition
    definition = query_service.load_playbook(instance.playbook_id)
    if not definition:
        raise HTTPException(status_code=404, detail="Playbook not found")
    
    # Execute all
    execution_service = fw['execution'](instance.project_id)
    result = execution_service.execute_all_steps(instance, definition)
    
    return result


# =============================================================================
# STATUS UPDATES
# =============================================================================

@router.put("/instance/{instance_id}/step/{step_id}/status")
async def update_step_status(
    instance_id: str,
    step_id: str,
    request: UpdateStatusRequest
):
    """Update status for a step."""
    fw = _get_framework()
    if not fw:
        raise HTTPException(status_code=500, detail="Framework not available")
    
    progress_service = fw['progress']()
    StepStatus = fw['StepStatus']
    
    try:
        status = StepStatus(request.status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {request.status}")
    
    success = progress_service.update_step_status(
        instance_id, step_id, status,
        notes=request.notes,
        ai_context=request.ai_context
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Step not found")
    
    return {'success': True}


@router.put("/instance/{instance_id}/finding/{finding_id}")
async def update_finding(
    instance_id: str,
    finding_id: str,
    request: UpdateFindingRequest
):
    """Update a finding (acknowledge, suppress, etc.)."""
    fw = _get_framework()
    if not fw:
        raise HTTPException(status_code=500, detail="Framework not available")
    
    progress_service = fw['progress']()
    FindingStatus = fw['FindingStatus']
    
    # Get instance to find the step containing this finding
    instance = progress_service.get_instance(instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")
    
    # Find the step containing this finding
    target_step_id = None
    for step_id, step_progress in instance.progress.items():
        for finding in step_progress.findings:
            if finding.id == finding_id:
                target_step_id = step_id
                break
        if target_step_id:
            break
    
    if not target_step_id:
        raise HTTPException(status_code=404, detail="Finding not found")
    
    try:
        status = FindingStatus(request.status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {request.status}")
    
    success = progress_service.update_finding_status(
        instance_id, target_step_id, finding_id,
        status, request.note
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Finding not found")
    
    return {'success': True}


# =============================================================================
# HEALTH CHECK
# =============================================================================

@router.get("/health")
async def framework_health():
    """Health check for the playbook framework."""
    fw = _get_framework()
    
    return {
        'status': 'healthy' if fw else 'degraded',
        'framework_available': fw is not None,
        'services': {
            'query': fw is not None,
            'match': fw is not None,
            'progress': fw is not None,
            'execution': fw is not None
        } if fw else {}
    }
