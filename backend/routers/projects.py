from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import logging
import sys

sys.path.insert(0, '/app')
sys.path.insert(0, '/data')

from utils.database.models import ProjectModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["projects"])


# Pydantic models for request bodies
class ProjectCreateRequest(BaseModel):
    customer: str
    name: str
    type: str = "Implementation"
    start_date: Optional[str] = None
    notes: Optional[str] = None
    status: str = "active"


class ProjectUpdateRequest(BaseModel):
    customer: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None
    start_date: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


@router.get("/list")
async def list_projects(status: Optional[str] = None):
    """List all projects, optionally filtered by status"""
    try:
        projects = ProjectModel.get_all(status=status)
        # Return array directly
        return projects
    except Exception as e:
        logger.error(f"Failed to list projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create")
async def create_project(request: ProjectCreateRequest):
    """Create a new project"""
    try:
        # Parse start_date if provided
        parsed_start_date = None
        if request.start_date:
            try:
                parsed_start_date = datetime.fromisoformat(request.start_date.replace('Z', '+00:00'))
            except ValueError:
                logger.warning(f"Invalid start_date format: {request.start_date}")
        
        # Prepare metadata
        metadata = {
            "type": request.type,
            "notes": request.notes
        }
        
        # Create project
        project = ProjectModel.create(
            name=request.name,
            customer=request.customer,
            start_date=parsed_start_date,
            status=request.status,
            metadata=metadata
        )
        
        logger.info(f"Created project: {project['id']} - {request.customer}")
        return project
        
    except Exception as e:
        logger.error(f"Failed to create project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{project_id}")
async def update_project(project_id: str, request: ProjectUpdateRequest):
    """Update an existing project"""
    try:
        # Get existing project
        project = ProjectModel.get_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Build update dict
        update_dict = {}
        
        if request.customer is not None:
            update_dict["customer"] = request.customer
        if request.name is not None:
            update_dict["name"] = request.name
        if request.status is not None:
            update_dict["status"] = request.status
            
        # Handle start_date
        if request.start_date is not None:
            try:
                update_dict["start_date"] = datetime.fromisoformat(request.start_date.replace('Z', '+00:00'))
            except ValueError:
                logger.warning(f"Invalid start_date format: {request.start_date}")
        
        # Handle metadata fields
        if request.type is not None or request.notes is not None:
            current_metadata = project.get('metadata', {})
            if request.type is not None:
                current_metadata["type"] = request.type
            if request.notes is not None:
                current_metadata["notes"] = request.notes
            update_dict["metadata"] = current_metadata
        
        # Update project
        updated_project = ProjectModel.update(project_id, **update_dict)
        
        logger.info(f"Updated project: {project_id}")
        return updated_project
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """Delete a project"""
    try:
        # Check if project exists
        project = ProjectModel.get_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Delete project
        ProjectModel.delete(project_id)
        
        logger.info(f"Deleted project: {project_id}")
        return {"success": True, "message": "Project deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
