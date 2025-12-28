"""
PROJECT ID HELPER
=================

Utility function to consistently resolve project name → project_id (UUID).

Add this to: backend/utils/project_helper.py

Then import where needed:
    from utils.project_helper import resolve_project_id

This ensures consistent project_id resolution across all code paths.
"""

import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Cache to avoid repeated DB lookups
_project_cache = {}


def resolve_project_id(project: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Resolve a project identifier to (project_id, project_name).
    
    Handles:
    - UUID passed directly → returns (uuid, name from DB)
    - Project name passed → returns (uuid from DB, name)
    - None/empty → returns (None, None)
    
    Args:
        project: Either a project UUID or project name
        
    Returns:
        Tuple of (project_id, project_name)
        Either or both may be None if not found
    """
    if not project:
        return None, None
    
    project = str(project).strip()
    
    # Check cache first
    if project in _project_cache:
        return _project_cache[project]
    
    # Determine if it's likely a UUID (36 chars with dashes)
    is_uuid = len(project) == 36 and project.count('-') == 4
    
    try:
        from utils.database.models import ProjectModel
        
        if is_uuid:
            # It's a UUID - look up by ID
            proj = ProjectModel.get_by_id(project)
            if proj:
                result = (proj.get('id'), proj.get('name'))
                _project_cache[project] = result
                _project_cache[proj.get('name', '')] = result  # Cache by name too
                return result
            else:
                # UUID not found
                return project, None
        else:
            # It's a name - look up by name
            proj = ProjectModel.get_by_name(project)
            if proj:
                result = (proj.get('id'), proj.get('name'))
                _project_cache[project] = result
                _project_cache[proj.get('id', '')] = result  # Cache by ID too
                return result
            else:
                # Name not found - return as-is for legacy compatibility
                return None, project
                
    except Exception as e:
        logger.warning(f"[PROJECT_HELPER] Failed to resolve '{project}': {e}")
        # Return what we can
        if is_uuid:
            return project, None
        else:
            return None, project


def get_project_id(project: str) -> Optional[str]:
    """
    Get just the project_id (UUID) from a project name or ID.
    
    Args:
        project: Project name or UUID
        
    Returns:
        Project UUID or None
    """
    project_id, _ = resolve_project_id(project)
    return project_id


def get_project_name(project: str) -> Optional[str]:
    """
    Get just the project name from a project name or ID.
    
    Args:
        project: Project name or UUID
        
    Returns:
        Project name or None
    """
    _, project_name = resolve_project_id(project)
    return project_name


def clear_project_cache():
    """Clear the project cache (useful after project updates/deletes)."""
    global _project_cache
    _project_cache = {}
    logger.info("[PROJECT_HELPER] Cache cleared")
