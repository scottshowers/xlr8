from fastapi import APIRouter, HTTPException
import sys

sys.path.insert(0, '/app')
sys.path.insert(0, '/data')

from utils.database.models import ProcessingJobModel

router = APIRouter()

@router.get("/jobs")
async def get_jobs(limit: int = 50):
    """Get recent processing jobs from database"""
    try:
        jobs = ProcessingJobModel.get_all(limit=limit)
        
        # Format for frontend
        formatted_jobs = []
        for job in jobs:
            formatted_jobs.append({
                'id': job['id'],
                'filename': job.get('input_data', {}).get('filename', 'Unknown'),
                'project': job.get('project_id', 'Unknown'),
                'status': job['status'],
                'progress': job.get('progress', {}).get('percent', 0),
                'current_step': job.get('progress', {}).get('step', ''),
                'error': job.get('error_message'),
                'result': job.get('result_data', {}).get('message'),
                'created_at': job.get('created_at'),
                'updated_at': job.get('updated_at')
            })
        
        return {"jobs": formatted_jobs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Get a specific job"""
    try:
        job = ProcessingJobModel.get_by_id(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Format for frontend
        return {
            'id': job['id'],
            'filename': job.get('input_data', {}).get('filename', 'Unknown'),
            'project': job.get('project_id', 'Unknown'),
            'status': job['status'],
            'progress': job.get('progress', {}).get('percent', 0),
            'current_step': job.get('progress', {}).get('step', ''),
            'error': job.get('error_message'),
            'result': job.get('result_data'),
            'created_at': job.get('created_at'),
            'updated_at': job.get('updated_at')
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
