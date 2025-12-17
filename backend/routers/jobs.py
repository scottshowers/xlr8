from fastapi import APIRouter, HTTPException
import sys
import logging

logger = logging.getLogger(__name__)

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
            result_data = job.get('result_data') or {}
            input_data = job.get('input_data') or {}
            
            # Debug log for first few jobs
            if len(formatted_jobs) < 3:
                logger.warning(f"[JOBS] Raw job: id={job.get('id')[:8]}, input_data={input_data}, result_data keys={list(result_data.keys()) if result_data else 'None'}")
            
            # Get filename from multiple possible locations
            filename = (
                input_data.get('filename') or 
                result_data.get('filename') or 
                input_data.get('project_name') or
                job.get('filename')
            )
            
            # Build a useful result message
            result_msg = None
            if result_data:
                tables = result_data.get('tables_created', 0)
                rows = result_data.get('total_rows', 0)
                if tables or rows:
                    result_msg = f"{tables} table(s), {rows:,} rows loaded"
                else:
                    result_msg = result_data.get('message') or result_data.get('filename')
            
            # Better display name fallback based on job type
            job_type = job.get('job_type', 'upload')
            if not filename or filename == 'Unknown':
                if job_type == 'upload':
                    filename = 'File upload'
                elif job_type == 'analysis':
                    filename = 'Document analysis'
                elif job_type == 'extraction':
                    filename = 'Data extraction'
                else:
                    filename = f"{job_type.title()} job"
            
            formatted_jobs.append({
                'id': job['id'],
                'filename': filename,
                'project': input_data.get('project_name') or job.get('project_id') or 'Unknown',
                'project_id': job.get('project_id'),
                'status': job['status'],
                'progress': job.get('progress', {}).get('percent', 0) if job.get('progress') else 0,
                'current_step': job.get('progress', {}).get('step', '') if job.get('progress') else '',
                'error': job.get('error_message'),
                'result': result_msg,
                'tables_created': result_data.get('tables_created'),
                'total_rows': result_data.get('total_rows'),
                'created_at': job.get('created_at'),
                'updated_at': job.get('updated_at')
            })
        
        return {"jobs": formatted_jobs}
    except Exception as e:
        logger.exception(f"[JOBS] Error: {e}")
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


@router.delete("/jobs/all")
async def delete_all_jobs():
    """Delete all processing jobs"""
    try:
        deleted = ProcessingJobModel.delete_all()
        return {"success": True, "deleted": deleted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a specific job"""
    try:
        success = ProcessingJobModel.delete(job_id)
        if not success:
            raise HTTPException(status_code=404, detail="Job not found")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
