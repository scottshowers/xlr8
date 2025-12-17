from fastapi import APIRouter, HTTPException
import sys
import logging
import json

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
            # Handle result_data - could be string or dict
            result_data = job.get('result_data') or {}
            if isinstance(result_data, str):
                try:
                    result_data = json.loads(result_data)
                except:
                    result_data = {}
            
            # Handle input_data - could be string or dict
            input_data = job.get('input_data') or {}
            if isinstance(input_data, str):
                try:
                    input_data = json.loads(input_data)
                except:
                    input_data = {}
            
            # Debug log for first few jobs
            if len(formatted_jobs) < 3:
                logger.warning(f"[JOBS] Raw job: id={job.get('id')[:8] if job.get('id') else 'none'}, input_data type={type(input_data).__name__}, input_data={input_data}")
            
            # Get filename from multiple possible locations
            filename = None
            if input_data.get('filename') and input_data.get('filename') != 'Unknown':
                filename = input_data.get('filename')
            elif result_data.get('filename') and result_data.get('filename') != 'Unknown':
                filename = result_data.get('filename')
            elif input_data.get('project_name'):
                filename = input_data.get('project_name')
            elif job.get('filename'):
                filename = job.get('filename')
            
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


@router.post("/jobs/clear-all")
async def delete_all_jobs():
    """Delete all processing jobs"""
    try:
        deleted = ProcessingJobModel.delete_all()
        logger.info(f"[JOBS] Deleted {deleted} jobs")
        return {"success": True, "deleted": deleted}
    except Exception as e:
        logger.exception(f"[JOBS] Clear all error: {e}")
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
