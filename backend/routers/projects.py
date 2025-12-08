"""
Projects Router - Complete CRUD
Fixed to use correct ProjectModel methods: get_all(), create(), update(), delete()
Updated: Added playbooks array support
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import sys
import logging

sys.path.insert(0, '/app')
sys.path.insert(0, '/data')

from utils.database.models import ProjectModel

logger = logging.getLogger(__name__)

router = APIRouter()


class ProjectCreate(BaseModel):
    """Schema for creating a project"""
    name: str
    customer: str
    product: Optional[str] = None  # UKG Pro, WFM Dimensions, UKG Ready
    type: str  # Frontend sends 'type'
    start_date: Optional[str] = None
    notes: Optional[str] = None
    playbooks: Optional[List[str]] = []  # Array of playbook IDs


class ProjectUpdate(BaseModel):
    """Schema for updating a project"""
    name: Optional[str] = None
    customer: Optional[str] = None
    product: Optional[str] = None
    type: Optional[str] = None
    start_date: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    playbooks: Optional[List[str]] = None  # Array of playbook IDs


@router.get("/list")
async def list_projects():
    """Get all projects"""
    try:
        # ✅ Correct method: get_all() not list_all()
        projects = ProjectModel.get_all(status='active')
        
        # Format for frontend
        formatted = []
        for proj in projects:
            # Extract type and notes from metadata
            metadata = proj.get('metadata', {})
            
            formatted.append({
                'id': proj.get('id'),
                'name': proj.get('name'),
                'customer': proj.get('customer'),  # ✅ Column is 'customer' not 'client_name'
                'product': metadata.get('product', ''),
                'type': metadata.get('type', 'Implementation'),
                'start_date': proj.get('start_date'),
                'status': proj.get('status', 'active'),
                'notes': metadata.get('notes', ''),
                'playbooks': metadata.get('playbooks', []),  # ✅ Include playbooks
                'is_active': proj.get('is_active', False),
                'created_at': proj.get('created_at'),
                'updated_at': proj.get('updated_at'),
                'created_by': proj.get('created_by'),
                'metadata': metadata
            })
        
        # Return array directly (frontend expects this)
        return formatted
        
    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create")
async def create_project(project: ProjectCreate):
    """Create a new project"""
    try:
        logger.info(f"Creating project: {project.name}")
        
        # ✅ Correct parameters matching models.py create() signature
        new_project = ProjectModel.create(
            name=project.name,
            client_name=project.customer,      # Maps to 'customer' column
            project_type=project.type,         # Stored in metadata.type
            notes=project.notes or "",         # Stored in metadata.notes
            product=project.product or ""      # Stored in metadata.product
        )
        
        if not new_project:
            raise HTTPException(status_code=500, detail="Failed to create project")
        
        # ✅ Update metadata with playbooks if provided
        if project.playbooks:
            existing_metadata = new_project.get('metadata', {})
            existing_metadata['playbooks'] = project.playbooks
            ProjectModel.update(new_project['id'], metadata=existing_metadata)
            new_project['metadata'] = existing_metadata
        
        # Extract metadata for response
        metadata = new_project.get('metadata', {})
        
        return {
            "success": True,
            "project": {
                'id': new_project.get('id'),
                'name': new_project.get('name'),
                'customer': new_project.get('customer'),
                'product': metadata.get('product', ''),
                'type': metadata.get('type', 'Implementation'),
                'notes': metadata.get('notes', ''),
                'playbooks': metadata.get('playbooks', []),  # ✅ Include playbooks
                'status': new_project.get('status', 'active'),
                'created_at': new_project.get('created_at')
            },
            "message": f"Project '{project.name}' created successfully"
        }
        
    except Exception as e:
        logger.error(f"Error creating project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{project_id}")
async def update_project(project_id: str, updates: ProjectUpdate):
    """Update project"""
    try:
        logger.info(f"Updating project {project_id}")
        
        # Build update dict
        update_dict = {}
        
        # Direct column updates
        if updates.name is not None:
            update_dict['name'] = updates.name
        
        if updates.customer is not None:
            update_dict['customer'] = updates.customer
        
        if updates.status is not None:
            update_dict['status'] = updates.status
        
        if updates.start_date is not None:
            update_dict['start_date'] = updates.start_date
        
        # Metadata updates (type, product, notes, and playbooks go in metadata JSON)
        if updates.type is not None or updates.notes is not None or updates.product is not None or updates.playbooks is not None:
            # Get existing project to merge metadata
            existing = ProjectModel.get_by_id(project_id)
            if existing:
                existing_metadata = existing.get('metadata', {})
                
                if updates.type is not None:
                    existing_metadata['type'] = updates.type
                
                if updates.notes is not None:
                    existing_metadata['notes'] = updates.notes
                
                if updates.product is not None:
                    existing_metadata['product'] = updates.product
                
                # ✅ Handle playbooks update
                if updates.playbooks is not None:
                    existing_metadata['playbooks'] = updates.playbooks
                
                update_dict['metadata'] = existing_metadata
        
        # Perform update
        updated = ProjectModel.update(project_id, **update_dict)
        
        if not updated:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Format response
        metadata = updated.get('metadata', {})
        
        return {
            "success": True,
            "project": {
                'id': updated.get('id'),
                'name': updated.get('name'),
                'customer': updated.get('customer'),
                'product': metadata.get('product', ''),
                'type': metadata.get('type', 'Implementation'),
                'notes': metadata.get('notes', ''),
                'playbooks': metadata.get('playbooks', []),  # ✅ Include playbooks
                'status': updated.get('status', 'active'),
                'updated_at': updated.get('updated_at')
            },
            "message": "Project updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """Delete project (soft delete)"""
    try:
        logger.info(f"Deleting project {project_id}")
        
        # ✅ Correct method: delete()
        success = ProjectModel.delete(project_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return {
            "success": True,
            "message": "Project deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}")
async def get_project(project_id: str):
    """Get single project by ID"""
    try:
        project = ProjectModel.get_by_id(project_id)
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Format response
        metadata = project.get('metadata', {})
        
        return {
            'id': project.get('id'),
            'name': project.get('name'),
            'customer': project.get('customer'),
            'product': metadata.get('product', ''),
            'type': metadata.get('type', 'Implementation'),
            'notes': metadata.get('notes', ''),
            'playbooks': metadata.get('playbooks', []),  # ✅ Include playbooks
            'status': project.get('status', 'active'),
            'start_date': project.get('start_date'),
            'created_at': project.get('created_at'),
            'updated_at': project.get('updated_at')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project: {e}")
        raise HTTPException(status_code=500, detail=str(e))
