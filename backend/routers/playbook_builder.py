"""
PLAYBOOK BUILDER ROUTER
========================

Admin API for creating, editing, and managing playbook configurations.

Supports three creation modes:
  A. Template-based: Pick type, fill in blanks
  B. Component-based: Mix and match modules  
  C. Clone and modify: Copy existing, customize

Deploy to: backend/routers/playbook_builder.py

Add to main.py:
    from routers import playbook_builder
    app.include_router(playbook_builder.router, prefix="/api", tags=["playbook-builder"])
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

sys.path.insert(0, '/app')

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# MODELS
# =============================================================================

class ActionModel(BaseModel):
    """Single action in a playbook step."""
    action_id: str
    description: str
    action_type: str = "recommended"
    reports_needed: List[str] = []
    keywords: List[str] = []
    categories: List[str] = []
    guidance: Optional[str] = None


class StepModel(BaseModel):
    """Step containing multiple actions (for checklist-style)."""
    step_number: str
    step_name: str
    phase: str = "Analysis"
    actions: List[ActionModel] = []


class PlaybookConfigCreate(BaseModel):
    """Create a new playbook configuration."""
    playbook_id: str
    name: str
    description: str = ""
    playbook_type: str = "checklist"  # checklist | analysis | compliance | hybrid
    
    # Display
    category: str = "Custom"
    icon: str = "📋"
    estimated_time: str = "10-15 minutes"
    modules: List[str] = ["All"]
    
    # Inputs
    inputs: Dict[str, Any] = {}
    
    # Structure (checklist-style)
    steps: List[StepModel] = []
    
    # Analysis config
    analysis_config: Dict[str, Any] = {}
    
    # Compliance config
    compliance_config: Dict[str, Any] = {}
    
    # Domain config
    consultative_prompts: Dict[str, str] = {}
    dependent_guidance: Dict[str, str] = {}
    action_keywords: Dict[str, Dict[str, List[str]]] = {}
    
    # Output config
    output_config: Dict[str, Any] = {}
    
    # Components
    components: List[str] = []


class PlaybookConfigUpdate(BaseModel):
    """Update playbook configuration (all fields optional)."""
    name: Optional[str] = None
    description: Optional[str] = None
    playbook_type: Optional[str] = None
    category: Optional[str] = None
    icon: Optional[str] = None
    estimated_time: Optional[str] = None
    modules: Optional[List[str]] = None
    inputs: Optional[Dict[str, Any]] = None
    steps: Optional[List[StepModel]] = None
    analysis_config: Optional[Dict[str, Any]] = None
    compliance_config: Optional[Dict[str, Any]] = None
    consultative_prompts: Optional[Dict[str, str]] = None
    dependent_guidance: Optional[Dict[str, str]] = None
    action_keywords: Optional[Dict[str, Dict[str, List[str]]]] = None
    output_config: Optional[Dict[str, Any]] = None
    components: Optional[List[str]] = None
    is_active: Optional[bool] = None


class CloneRequest(BaseModel):
    """Clone an existing playbook."""
    source_playbook_id: str
    new_playbook_id: str
    new_name: str
    new_description: Optional[str] = None


# =============================================================================
# SUPABASE CLIENT
# =============================================================================

_supabase_client = None

def _get_supabase():
    """Get Supabase client."""
    global _supabase_client
    if _supabase_client is None:
        try:
            from supabase import create_client
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
            if url and key:
                _supabase_client = create_client(url, key)
                logger.info("[PLAYBOOK-BUILDER] Supabase initialized")
        except Exception as e:
            logger.warning(f"[PLAYBOOK-BUILDER] Supabase not available: {e}")
    return _supabase_client


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/playbook-builder/health")
async def builder_health():
    """Health check for playbook builder."""
    supabase = _get_supabase()
    return {
        "available": True,
        "supabase_connected": supabase is not None
    }


# -----------------------------------------------------------------------------
# LIST PLAYBOOKS
# -----------------------------------------------------------------------------

@router.get("/playbook-builder/configs")
async def list_playbook_configs(
    include_inactive: bool = False,
    playbook_type: Optional[str] = None,
    category: Optional[str] = None,
    templates_only: bool = False
):
    """
    List all playbook configurations.
    
    Query params:
      - include_inactive: Include disabled playbooks
      - playbook_type: Filter by type (checklist, analysis, compliance, hybrid)
      - category: Filter by category
      - templates_only: Only return templates (for clone modal)
    """
    supabase = _get_supabase()
    if not supabase:
        # Fallback to hardcoded
        return {
            "configs": [
                {
                    "playbook_id": "year-end-checklist",
                    "name": "Year-End Checklist",
                    "description": "Comprehensive year-end processing workbook",
                    "playbook_type": "checklist",
                    "category": "Year-End",
                    "icon": "📅",
                    "is_builtin": True,
                    "is_template": True,
                    "is_active": True
                }
            ],
            "total": 1,
            "supabase_available": False
        }
    
    try:
        query = supabase.table("playbook_configs").select("*")
        
        if not include_inactive:
            query = query.eq("is_active", True)
        
        if playbook_type:
            query = query.eq("playbook_type", playbook_type)
        
        if category:
            query = query.eq("category", category)
        
        if templates_only:
            query = query.eq("is_template", True)
        
        result = query.order("name").execute()
        
        return {
            "configs": result.data or [],
            "total": len(result.data or []),
            "supabase_available": True
        }
        
    except Exception as e:
        logger.error(f"[PLAYBOOK-BUILDER] List failed: {e}")
        raise HTTPException(500, f"Failed to list configs: {e}")


# -----------------------------------------------------------------------------
# GET SINGLE PLAYBOOK
# -----------------------------------------------------------------------------

@router.get("/playbook-builder/configs/{playbook_id}")
async def get_playbook_config(playbook_id: str):
    """Get a single playbook configuration with full details."""
    supabase = _get_supabase()
    if not supabase:
        raise HTTPException(503, "Supabase not available")
    
    try:
        result = supabase.table("playbook_configs").select("*").eq("playbook_id", playbook_id).single().execute()
        
        if not result.data:
            raise HTTPException(404, f"Playbook not found: {playbook_id}")
        
        return result.data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[PLAYBOOK-BUILDER] Get failed: {e}")
        raise HTTPException(500, f"Failed to get config: {e}")


# -----------------------------------------------------------------------------
# GET COMPONENTS
# -----------------------------------------------------------------------------

@router.get("/playbook-builder/components")
async def list_components(component_type: Optional[str] = None):
    """
    List available playbook components.
    
    Components are the building blocks: scanners, analyzers, extractors, hooks.
    """
    supabase = _get_supabase()
    if not supabase:
        # Fallback to hardcoded
        return {
            "components": [
                {"component_id": "document_scanner", "name": "Document Scanner", "component_type": "scanner"},
                {"component_id": "data_analyzer", "name": "Data Analyzer", "component_type": "analyzer"},
                {"component_id": "rule_checker", "name": "Rule Checker", "component_type": "checker"},
                {"component_id": "findings_extractor", "name": "Findings Extractor", "component_type": "extractor"},
                {"component_id": "intelligence_hook", "name": "Intelligence Hook", "component_type": "hook"},
                {"component_id": "learning_hook", "name": "Learning Hook", "component_type": "hook"},
                {"component_id": "conflict_detector", "name": "Conflict Detector", "component_type": "hook"},
            ]
        }
    
    try:
        query = supabase.table("playbook_components").select("*").eq("is_active", True)
        
        if component_type:
            query = query.eq("component_type", component_type)
        
        result = query.order("name").execute()
        
        return {"components": result.data or []}
        
    except Exception as e:
        logger.error(f"[PLAYBOOK-BUILDER] List components failed: {e}")
        raise HTTPException(500, f"Failed to list components: {e}")


# -----------------------------------------------------------------------------
# CREATE PLAYBOOK
# -----------------------------------------------------------------------------

@router.post("/playbook-builder/configs")
async def create_playbook_config(config: PlaybookConfigCreate):
    """
    Create a new playbook configuration.
    
    This stores the config in Supabase. The playbook becomes available
    immediately for assignment to projects.
    """
    supabase = _get_supabase()
    if not supabase:
        raise HTTPException(503, "Supabase not available")
    
    try:
        # Convert steps to JSON-serializable format
        steps_data = []
        for s in config.steps:
            steps_data.append({
                "step_number": s.step_number,
                "step_name": s.step_name,
                "phase": s.phase,
                "actions": [
                    {
                        "action_id": a.action_id,
                        "description": a.description,
                        "action_type": a.action_type,
                        "reports_needed": a.reports_needed,
                        "keywords": a.keywords,
                        "categories": a.categories,
                        "guidance": a.guidance
                    }
                    for a in s.actions
                ]
            })
        
        data = {
            "playbook_id": config.playbook_id,
            "name": config.name,
            "description": config.description,
            "playbook_type": config.playbook_type,
            "category": config.category,
            "icon": config.icon,
            "estimated_time": config.estimated_time,
            "modules": config.modules,
            "inputs": config.inputs,
            "steps": steps_data,
            "analysis_config": config.analysis_config,
            "compliance_config": config.compliance_config,
            "consultative_prompts": config.consultative_prompts,
            "dependent_guidance": config.dependent_guidance,
            "action_keywords": config.action_keywords,
            "output_config": config.output_config,
            "components": config.components,
            "is_builtin": False,
            "is_template": False,
            "is_active": True
        }
        
        supabase.table("playbook_configs").insert(data).execute()
        
        logger.info(f"[PLAYBOOK-BUILDER] Created playbook: {config.playbook_id}")
        
        # Auto-register with framework so it's immediately available
        try:
            from utils.playbook_loader import reload_single_playbook
            reload_single_playbook(config.playbook_id)
        except ImportError:
            try:
                from backend.utils.playbook_loader import reload_single_playbook
                reload_single_playbook(config.playbook_id)
            except ImportError:
                logger.warning("[PLAYBOOK-BUILDER] Could not auto-register - restart required")
        
        return {
            "success": True,
            "playbook_id": config.playbook_id,
            "message": f"Playbook '{config.name}' created and registered"
        }
        
    except Exception as e:
        logger.error(f"[PLAYBOOK-BUILDER] Create failed: {e}")
        if "duplicate key" in str(e).lower():
            raise HTTPException(400, f"Playbook ID '{config.playbook_id}' already exists")
        raise HTTPException(500, f"Failed to create: {e}")


# -----------------------------------------------------------------------------
# UPDATE PLAYBOOK
# -----------------------------------------------------------------------------

@router.put("/playbook-builder/configs/{playbook_id}")
async def update_playbook_config(playbook_id: str, config: PlaybookConfigUpdate):
    """Update an existing playbook configuration."""
    supabase = _get_supabase()
    if not supabase:
        raise HTTPException(503, "Supabase not available")
    
    try:
        # Check exists and not built-in
        existing = supabase.table("playbook_configs").select("is_builtin").eq("playbook_id", playbook_id).single().execute()
        
        if not existing.data:
            raise HTTPException(404, f"Playbook not found: {playbook_id}")
        
        if existing.data.get("is_builtin"):
            raise HTTPException(403, "Cannot modify built-in playbooks. Clone it instead.")
        
        # Build update dict
        update_data = {}
        
        for field in ["name", "description", "playbook_type", "category", "icon", 
                      "estimated_time", "modules", "inputs", "analysis_config",
                      "compliance_config", "consultative_prompts", "dependent_guidance",
                      "action_keywords", "output_config", "components", "is_active"]:
            value = getattr(config, field, None)
            if value is not None:
                update_data[field] = value
        
        # Handle steps specially
        if config.steps is not None:
            update_data["steps"] = [
                {
                    "step_number": s.step_number,
                    "step_name": s.step_name,
                    "phase": s.phase,
                    "actions": [
                        {
                            "action_id": a.action_id,
                            "description": a.description,
                            "action_type": a.action_type,
                            "reports_needed": a.reports_needed,
                            "keywords": a.keywords,
                            "categories": a.categories,
                            "guidance": a.guidance
                        }
                        for a in s.actions
                    ]
                }
                for s in config.steps
            ]
        
        if not update_data:
            return {"success": True, "message": "No changes"}
        
        supabase.table("playbook_configs").update(update_data).eq("playbook_id", playbook_id).execute()
        
        logger.info(f"[PLAYBOOK-BUILDER] Updated playbook: {playbook_id}")
        
        return {"success": True, "playbook_id": playbook_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[PLAYBOOK-BUILDER] Update failed: {e}")
        raise HTTPException(500, f"Failed to update: {e}")


# -----------------------------------------------------------------------------
# CLONE PLAYBOOK
# -----------------------------------------------------------------------------

@router.post("/playbook-builder/clone")
async def clone_playbook(request: CloneRequest):
    """
    Clone an existing playbook as a starting point.
    
    Copies all configuration from source, creates new playbook with new ID.
    Cloned playbooks are editable (not built-in).
    """
    supabase = _get_supabase()
    if not supabase:
        raise HTTPException(503, "Supabase not available")
    
    try:
        # Get source playbook
        source = supabase.table("playbook_configs").select("*").eq("playbook_id", request.source_playbook_id).single().execute()
        
        if not source.data:
            raise HTTPException(404, f"Source playbook not found: {request.source_playbook_id}")
        
        # Check new ID doesn't exist
        existing = supabase.table("playbook_configs").select("playbook_id").eq("playbook_id", request.new_playbook_id).execute()
        if existing.data:
            raise HTTPException(400, f"Playbook ID '{request.new_playbook_id}' already exists")
        
        # Create clone
        clone_data = {
            "playbook_id": request.new_playbook_id,
            "name": request.new_name,
            "description": request.new_description or source.data.get("description", ""),
            "playbook_type": source.data.get("playbook_type", "checklist"),
            "category": source.data.get("category", "Custom"),
            "icon": source.data.get("icon", "📋"),
            "estimated_time": source.data.get("estimated_time", "10-15 minutes"),
            "modules": source.data.get("modules", ["All"]),
            "inputs": source.data.get("inputs", {}),
            "steps": source.data.get("steps", []),
            "analysis_config": source.data.get("analysis_config", {}),
            "compliance_config": source.data.get("compliance_config", {}),
            "consultative_prompts": source.data.get("consultative_prompts", {}),
            "dependent_guidance": source.data.get("dependent_guidance", {}),
            "action_keywords": source.data.get("action_keywords", {}),
            "output_config": source.data.get("output_config", {}),
            "components": source.data.get("components", []),
            "cloned_from": request.source_playbook_id,
            "is_builtin": False,
            "is_template": False,
            "is_active": True
        }
        
        supabase.table("playbook_configs").insert(clone_data).execute()
        
        logger.info(f"[PLAYBOOK-BUILDER] Cloned {request.source_playbook_id} → {request.new_playbook_id}")
        
        # Auto-register with framework
        try:
            from utils.playbook_loader import reload_single_playbook
            reload_single_playbook(request.new_playbook_id)
        except ImportError:
            try:
                from backend.utils.playbook_loader import reload_single_playbook
                reload_single_playbook(request.new_playbook_id)
            except ImportError:
                pass
        
        return {
            "success": True,
            "playbook_id": request.new_playbook_id,
            "cloned_from": request.source_playbook_id,
            "message": f"Cloned as '{request.new_name}' and registered"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[PLAYBOOK-BUILDER] Clone failed: {e}")
        raise HTTPException(500, f"Failed to clone: {e}")


# -----------------------------------------------------------------------------
# DELETE PLAYBOOK
# -----------------------------------------------------------------------------

@router.delete("/playbook-builder/configs/{playbook_id}")
async def delete_playbook_config(playbook_id: str):
    """Delete a custom playbook configuration."""
    supabase = _get_supabase()
    if not supabase:
        raise HTTPException(503, "Supabase not available")
    
    try:
        # Check exists and not built-in
        existing = supabase.table("playbook_configs").select("is_builtin, name").eq("playbook_id", playbook_id).single().execute()
        
        if not existing.data:
            raise HTTPException(404, f"Playbook not found: {playbook_id}")
        
        if existing.data.get("is_builtin"):
            raise HTTPException(403, "Cannot delete built-in playbooks")
        
        supabase.table("playbook_configs").delete().eq("playbook_id", playbook_id).execute()
        
        logger.info(f"[PLAYBOOK-BUILDER] Deleted playbook: {playbook_id}")
        
        return {
            "success": True,
            "playbook_id": playbook_id,
            "message": f"Deleted '{existing.data.get('name')}'"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[PLAYBOOK-BUILDER] Delete failed: {e}")
        raise HTTPException(500, f"Failed to delete: {e}")


# -----------------------------------------------------------------------------
# TOGGLE ACTIVE STATUS
# -----------------------------------------------------------------------------

@router.post("/playbook-builder/configs/{playbook_id}/toggle")
async def toggle_playbook_active(playbook_id: str):
    """Toggle a playbook's active status."""
    supabase = _get_supabase()
    if not supabase:
        raise HTTPException(503, "Supabase not available")
    
    try:
        existing = supabase.table("playbook_configs").select("is_active, is_builtin").eq("playbook_id", playbook_id).single().execute()
        
        if not existing.data:
            raise HTTPException(404, f"Playbook not found: {playbook_id}")
        
        if existing.data.get("is_builtin"):
            raise HTTPException(403, "Cannot disable built-in playbooks")
        
        new_status = not existing.data.get("is_active", True)
        
        supabase.table("playbook_configs").update({"is_active": new_status}).eq("playbook_id", playbook_id).execute()
        
        return {
            "success": True,
            "playbook_id": playbook_id,
            "is_active": new_status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[PLAYBOOK-BUILDER] Toggle failed: {e}")
        raise HTTPException(500, f"Failed to toggle: {e}")
