"""
PLAYBOOK LOADER - Bridge between Supabase configs and runtime framework
========================================================================

Loads playbook configurations from Supabase and registers them with
the PlaybookRegistry so they can be executed.

Call load_playbooks_from_supabase() on app startup.

Deploy to: backend/utils/playbook_loader.py

Add to main.py startup:
    from utils.playbook_loader import load_playbooks_from_supabase
    load_playbooks_from_supabase()
"""

import os
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


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
        except Exception as e:
            logger.warning(f"[PLAYBOOK-LOADER] Supabase not available: {e}")
    return _supabase_client


# =============================================================================
# CONVERSION: Supabase Row -> PlaybookDefinition
# =============================================================================

def _convert_to_playbook_definition(config: Dict) -> Optional[Any]:
    """
    Convert a Supabase config row to a PlaybookDefinition.
    
    Returns None if conversion fails.
    """
    try:
        # Import framework classes
        try:
            from utils.playbook_framework import (
                PlaybookDefinition,
                StepDefinition,
                ActionDefinition,
                ActionType
            )
        except ImportError:
            from backend.utils.playbook_framework import (
                PlaybookDefinition,
                StepDefinition,
                ActionDefinition,
                ActionType
            )
        
        playbook_id = config.get("playbook_id")
        if not playbook_id:
            return None
        
        # Convert steps from JSON to StepDefinition objects
        steps = []
        steps_data = config.get("steps") or []
        
        for step_data in steps_data:
            # Convert actions
            actions = []
            for action_data in step_data.get("actions", []):
                # Parse action type
                action_type_str = action_data.get("action_type", "recommended")
                try:
                    action_type = ActionType(action_type_str)
                except ValueError:
                    action_type = ActionType.RECOMMENDED
                
                action = ActionDefinition(
                    action_id=action_data.get("action_id", ""),
                    description=action_data.get("description", ""),
                    action_type=action_type,
                    reports_needed=action_data.get("reports_needed", []),
                    keywords=action_data.get("keywords", []),
                    categories=action_data.get("categories", []),
                    guidance=action_data.get("guidance"),
                )
                actions.append(action)
            
            step = StepDefinition(
                step_number=step_data.get("step_number", ""),
                step_name=step_data.get("step_name", ""),
                phase=step_data.get("phase", "Analysis"),
                actions=actions
            )
            steps.append(step)
        
        # Build PlaybookDefinition
        playbook = PlaybookDefinition(
            playbook_id=playbook_id,
            name=config.get("name", playbook_id),
            description=config.get("description", ""),
            version=config.get("version", "1.0.0"),
            steps=steps,
            consultative_prompts=config.get("consultative_prompts") or {},
            dependent_guidance=config.get("dependent_guidance") or {},
            action_keywords=config.get("action_keywords") or {},
            export_tabs=config.get("output_config", {}).get("export_tabs") or config.get("export_tabs") or [],
        )
        
        # Store additional metadata as attributes for runtime use
        playbook._playbook_type = config.get("playbook_type", "checklist")
        playbook._category = config.get("category", "Custom")
        playbook._icon = config.get("icon", "📋")
        playbook._estimated_time = config.get("estimated_time", "10-15 minutes")
        playbook._modules = config.get("modules") or ["All"]
        playbook._inputs = config.get("inputs") or {}
        playbook._analysis_config = config.get("analysis_config") or {}
        playbook._compliance_config = config.get("compliance_config") or {}
        playbook._components = config.get("components") or []
        playbook._is_builtin = config.get("is_builtin", False)
        
        return playbook
        
    except Exception as e:
        logger.error(f"[PLAYBOOK-LOADER] Failed to convert config {config.get('playbook_id')}: {e}")
        return None


# =============================================================================
# MAIN LOADER FUNCTION
# =============================================================================

def load_playbooks_from_supabase(force_reload: bool = False) -> Dict[str, bool]:
    """
    Load all active playbook configurations from Supabase and register them.
    
    This should be called on app startup.
    
    Args:
        force_reload: If True, reload even if already loaded
    
    Returns:
        Dict mapping playbook_id to success status
    """
    # Get registry
    try:
        from utils.playbook_framework import PLAYBOOK_REGISTRY
    except ImportError:
        try:
            from backend.utils.playbook_framework import PLAYBOOK_REGISTRY
        except ImportError:
            logger.error("[PLAYBOOK-LOADER] PlaybookRegistry not available")
            return {}
    
    # Check if already loaded (unless force)
    if not force_reload and len(PLAYBOOK_REGISTRY.list_all()) > 0:
        logger.info(f"[PLAYBOOK-LOADER] Playbooks already loaded: {PLAYBOOK_REGISTRY.list_all()}")
        return {pid: True for pid in PLAYBOOK_REGISTRY.list_all()}
    
    supabase = _get_supabase()
    results = {}
    
    if not supabase:
        logger.warning("[PLAYBOOK-LOADER] Supabase not available - using built-in playbooks only")
        # Try to load Year-End from code as fallback
        try:
            from utils.year_end_playbook import register_year_end_playbook
            register_year_end_playbook()
            results["year-end"] = True
            logger.info("[PLAYBOOK-LOADER] Loaded year-end playbook from code")
        except ImportError:
            try:
                from backend.utils.year_end_playbook import register_year_end_playbook
                register_year_end_playbook()
                results["year-end"] = True
            except ImportError:
                logger.warning("[PLAYBOOK-LOADER] Year-end playbook not available")
        return results
    
    try:
        # Fetch all active configs
        result = supabase.table("playbook_configs").select("*").eq("is_active", True).execute()
        
        configs = result.data or []
        logger.info(f"[PLAYBOOK-LOADER] Found {len(configs)} active playbook configs in Supabase")
        
        for config in configs:
            playbook_id = config.get("playbook_id")
            
            # Skip built-in if we have code version (year-end has special handling)
            if config.get("is_builtin") and playbook_id in ["year-end-checklist", "year-end"]:
                # Try to load from code for full functionality
                try:
                    from utils.year_end_playbook import register_year_end_playbook
                    register_year_end_playbook()
                    results[playbook_id] = True
                    logger.info(f"[PLAYBOOK-LOADER] Loaded {playbook_id} from code (built-in)")
                    continue
                except ImportError:
                    try:
                        from backend.utils.year_end_playbook import register_year_end_playbook
                        register_year_end_playbook()
                        results[playbook_id] = True
                        continue
                    except ImportError:
                        pass  # Fall through to load from config
            
            # Convert and register
            playbook = _convert_to_playbook_definition(config)
            
            if playbook:
                PLAYBOOK_REGISTRY.register(playbook)
                results[playbook_id] = True
                logger.info(f"[PLAYBOOK-LOADER] Registered: {playbook_id} ({config.get('name')})")
            else:
                results[playbook_id] = False
                logger.warning(f"[PLAYBOOK-LOADER] Failed to load: {playbook_id}")
        
        logger.info(f"[PLAYBOOK-LOADER] Loaded {sum(results.values())}/{len(configs)} playbooks")
        
    except Exception as e:
        logger.error(f"[PLAYBOOK-LOADER] Failed to load from Supabase: {e}")
    
    return results


def reload_single_playbook(playbook_id: str) -> bool:
    """
    Reload a single playbook from Supabase.
    
    Useful when a playbook is created or updated via the builder.
    """
    try:
        from utils.playbook_framework import PLAYBOOK_REGISTRY
    except ImportError:
        from backend.utils.playbook_framework import PLAYBOOK_REGISTRY
    
    supabase = _get_supabase()
    if not supabase:
        return False
    
    try:
        result = supabase.table("playbook_configs").select("*").eq("playbook_id", playbook_id).single().execute()
        
        if not result.data:
            logger.warning(f"[PLAYBOOK-LOADER] Playbook not found: {playbook_id}")
            return False
        
        playbook = _convert_to_playbook_definition(result.data)
        
        if playbook:
            PLAYBOOK_REGISTRY.register(playbook)
            logger.info(f"[PLAYBOOK-LOADER] Reloaded: {playbook_id}")
            return True
        
    except Exception as e:
        logger.error(f"[PLAYBOOK-LOADER] Failed to reload {playbook_id}: {e}")
    
    return False


def get_playbook_card_info(playbook_id: str) -> Optional[Dict]:
    """
    Get display info for a playbook (for UI cards).
    
    Returns icon, category, estimated_time, etc.
    """
    try:
        from utils.playbook_framework import PLAYBOOK_REGISTRY
    except ImportError:
        from backend.utils.playbook_framework import PLAYBOOK_REGISTRY
    
    playbook = PLAYBOOK_REGISTRY.get(playbook_id)
    
    if not playbook:
        return None
    
    return {
        "playbook_id": playbook.playbook_id,
        "name": playbook.name,
        "description": playbook.description,
        "version": playbook.version,
        "playbook_type": getattr(playbook, '_playbook_type', 'checklist'),
        "category": getattr(playbook, '_category', 'Custom'),
        "icon": getattr(playbook, '_icon', '📋'),
        "estimated_time": getattr(playbook, '_estimated_time', '10-15 minutes'),
        "modules": getattr(playbook, '_modules', ['All']),
        "is_builtin": getattr(playbook, '_is_builtin', False),
        "step_count": len(playbook.steps),
        "action_count": sum(len(s.actions) for s in playbook.steps),
    }


def list_available_playbooks() -> List[Dict]:
    """
    List all registered playbooks with their card info.
    
    For use in UI playbook selection.
    """
    try:
        from utils.playbook_framework import PLAYBOOK_REGISTRY
    except ImportError:
        from backend.utils.playbook_framework import PLAYBOOK_REGISTRY
    
    playbooks = []
    
    for playbook_id in PLAYBOOK_REGISTRY.list_all():
        info = get_playbook_card_info(playbook_id)
        if info:
            playbooks.append(info)
    
    return playbooks
