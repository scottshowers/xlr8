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
    description: Optional[str] = None

class Project(BaseModel):
    id: str
    name: str
    customer: Optional[str] = None  # FastAPI calls it 'description' but DB has 'customer'
    created_at: str

@router.post("/projects")
async def create_project(project: ProjectCreate):
    """Create a new project using existing Supabase models"""
    try:
        # Use YOUR existing ProjectModel
        result = ProjectModel.create(
            name=project.name,
            client_name=project.description,  # Maps description -> customer
            project_type='Implementation',
            notes=None
        )
        
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
