"""
Projects Router - Complete CRUD
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import sys
import logging

sys.path.insert(0, '/app')
sys.path.insert(0, '/data')

from utils.database.models import ProjectModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str
    customer: str
    project_type: str
    start_date: Optional[str] = None
    notes: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    customer: Optional[str] = None
    project_type: Optional[str] = None
    start_date: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


@router.get("/list")
async def list_projects():
    try:
        projects = ProjectModel.get_all(status=None)  # Get all, not just active
        
        formatted = []
        for proj in projects:
            formatted.append({
                'id': proj.get('id'),
                'name': proj.get('name'),
                'customer': proj.get('customer'),
                'start_date': proj.get('start_date'),
                'status': proj.get('status', 'active'),
                'is_active': proj.get('is_active', False),
                'created_at': proj.get('created_at'),
                'updated_at': proj.get('updated_at'),
                'created_by': proj.get('created_by'),
                'metadata': proj.get('metadata', {})
            })
        
        return {"projects": formatted}
        
    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create")
async def create_project(project: ProjectCreate):
    try:
        logger.info(f"Creating project: {project.name}")
        
        new_project = ProjectModel.create(
            name=project.name,
            client_name=project.customer,
            project_type=project.project_type,
            notes=project.notes or ""
        )
        
        if not new_project:
            raise HTTPException(status_code=500, detail="Failed to create project")
        
        return {
            "success": True,
            "project": new_project,
            "message": f"Project '{project.name}' created successfully"
        }
        
    except Exception as e:
        logger.error(f"Error creating project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{project_id}")
async def update_project(project_id: str, updates: ProjectUpdate):
    try:
        logger.info(f"Updating project {project_id}")
        
        update_dict = updates.dict(exclude_unset=True)
        
        if 'customer' in update_dict:
            update_dict['client_name'] = update_dict.pop('customer')
        
        if 'project_type' in update_dict:
            if 'metadata' not in update_dict:
                update_dict['metadata'] = {}
            update_dict['metadata']['type'] = update_dict.pop('project_type')
        
        if 'notes' in update_dict:
            if 'metadata' not in update_dict:
                update_dict['metadata'] = {}
            update_dict['metadata']['notes'] = update_dict.pop('notes')
        
        updated = ProjectModel.update(project_id, **update_dict)
        
        if not updated:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return {
            "success": True,
            "project": updated,
            "message": "Project updated successfully"
        }
        
    except Exception as e:
        logger.error(f"Error updating project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    try:
        logger.info(f"Deleting project {project_id}")
        
        success = ProjectModel.delete(project_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return {
            "success": True,
            "message": "Project deleted successfully"
        }
        
    except Exception as e:
        logger.error(f"Error deleting project: {e}")
        raise HTTPException(status_code=500, detail=str(e))
