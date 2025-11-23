from fastapi import APIRouter
from typing import List, Dict
from datetime import datetime

router = APIRouter()

# In-memory job storage (replace with Redis or DB later)
jobs_db: Dict[str, dict] = {}

@router.get("/jobs")
async def get_jobs():
    """Get all jobs, sorted by most recent"""
    sorted_jobs = sorted(
        jobs_db.values(),
        key=lambda x: x.get('started_at', ''),
        reverse=True
    )
    return {"jobs": sorted_jobs}

@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Get a specific job"""
    if job_id not in jobs_db:
        return {"error": "Job not found"}
    return jobs_db[job_id]

def create_job(job_id: str, filename: str, project: str):
    """Create a new job"""
    jobs_db[job_id] = {
        "id": job_id,
        "filename": filename,
        "project": project,
        "status": "queued",
        "progress": 0,
        "started_at": datetime.utcnow().isoformat(),
        "current_step": "Queued..."
    }
    return jobs_db[job_id]

def update_job(job_id: str, **kwargs):
    """Update job status"""
    if job_id in jobs_db:
        jobs_db[job_id].update(kwargs)
        jobs_db[job_id]["updated_at"] = datetime.utcnow().isoformat()

def complete_job(job_id: str, result: str = None):
    """Mark job as completed"""
    if job_id in jobs_db:
        jobs_db[job_id].update({
            "status": "completed",
            "progress": 100,
            "result": result,
            "completed_at": datetime.utcnow().isoformat()
        })

def fail_job(job_id: str, error: str):
    """Mark job as failed"""
    if job_id in jobs_db:
        jobs_db[job_id].update({
            "status": "failed",
            "error": error,
            "failed_at": datetime.utcnow().isoformat()
        })
