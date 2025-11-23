from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import datetime

router = APIRouter(prefix="/projects", tags=["projects"])

# In-memory storage for now (replace with DB later)
projects_db = []

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None

class Project(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: str

@router.post("", response_model=Project)
async def create_project(project: ProjectCreate):
    """Create a new project/customer"""
    
    # Check if project name already exists
    if any(p["name"].lower() == project.name.lower() for p in projects_db):
        raise HTTPException(status_code=400, detail="Project name already exists")
    
    new_project = {
        "id": str(uuid.uuid4()),
        "name": project.name,
        "description": project.description,
        "created_at": datetime.utcnow().isoformat()
    }
    
    projects_db.append(new_project)
    
    return new_project

@router.get("")
async def get_projects():
    """Get all projects"""
    return {"projects": projects_db}

@router.get("/{project_id}")
async def get_project(project_id: str):
    """Get a specific project"""
    project = next((p for p in projects_db if p["id"] == project_id), None)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """Delete a project"""
    global projects_db
    projects_db = [p for p in projects_db if p["id"] != project_id]
    return {"message": "Project deleted"}
