from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import sys

# Add paths for imports
sys.path.insert(0, '/app')
sys.path.insert(0, '/data')

# Import YOUR existing Supabase models
from utils.database.models import ProjectModel

router = APIRouter(tags=["projects"])

class ProjectCreate(BaseModel):
    name: str
    customer: Optional[str] = None
    project_type: Optional[str] = 'Implementation'
    start_date: Optional[str] = None
    notes: Optional[str] = None

class Project(BaseModel):
    id: str
    name: str
    customer: Optional[str] = None
    start_date: Optional[str] = None
    status: Optional[str] = None
    created_at: str

@router.post("/projects")
async def create_project(project: ProjectCreate):
    """Create a new project using existing Supabase models"""
    try:
        # Use YOUR existing ProjectModel with all fields
        result = ProjectModel.create(
            name=project.name,
            client_name=project.customer,
            project_type=project.project_type,
            notes=project.notes
        )
        
        # Also update start_date if provided (not in create method)
        if result and project.start_date:
            from utils.database.supabase_client import get_supabase
            supabase = get_supabase()
            if supabase:
                supabase.table('projects').update({
                    'start_date': project.start_date
                }).eq('id', result['id']).execute()
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to create project")
        
        return result
    except Exception as e:
        if "already exists" in str(e).lower():
            raise HTTPException(status_code=400, detail="Project name already exists")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/projects")
async def get_projects():
    """Get all projects using existing Supabase models"""
    try:
        projects = ProjectModel.get_all()
        return {"projects": projects}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/projects/{project_id}")
async def get_project(project_id: str):
    """Get a specific project"""
    try:
        project = ProjectModel.get_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete a project"""
    try:
        success = ProjectModel.delete(project_id)
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")
        return {"message": "Project deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/functional-areas")
async def get_functional_areas():
    """Get list of functional areas"""
    return {
        "functional_areas": [
            "Payroll",
            "Benefits", 
            "Time & Attendance",
            "HR",
            "Recruiting",
            "Performance",
            "Compensation"
        ]
    }
