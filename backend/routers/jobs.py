"""
Jobs Router - Processing Job Management
=======================================

Provides job listing, cancellation, and cleanup functionality.

Endpoints:
- GET /jobs - List all jobs with stuck detection
- GET /jobs/{job_id} - Get specific job
- POST /jobs/{job_id}/cancel - Cancel a running job
- POST /jobs/cleanup - Cancel all stuck jobs
- POST /jobs/clear-all - Delete all job history
- DELETE /jobs/{job_id} - Delete a job from history
- DELETE /jobs - Clear completed/failed job history
"""

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timezone
import sys
import logging
import json

logger = logging.getLogger(__name__)

sys.path.insert(0, '/app')
sys.path.insert(0, '/data')

from utils.database.models import ProcessingJobModel

router = APIRouter()


def calculate_is_stuck(status: str, created_at: str, threshold_minutes: int = 15) -> bool:
    """Check if a job is stuck (processing/queued for too long)."""
    if status not in ['processing', 'queued']:
        return False
    if not created_at:
        return False
    try:
        created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        age_minutes = (datetime.now(timezone.utc) - created).total_seconds() / 60
        return age_minutes > threshold_minutes
    except:
        return False


@router.get("/jobs")
async def get_jobs(limit: int = 50):
    """
    Get recent processing jobs with stuck detection.
    
    Returns jobs with is_stuck and can_cancel flags.
    """
    try:
        jobs = ProcessingJobModel.get_all(limit=limit)
        
        formatted_jobs = []
        stuck_count = 0
        active_count = 0
        
        for job in jobs:
            # Handle result_data
            result_data = job.get('result_data') or {}
            if isinstance(result_data, str):
                try:
                    result_data = json.loads(result_data)
                except:
                    result_data = {}
            
            # Handle input_data
            input_data = job.get('input_data') or {}
            if isinstance(input_data, str):
                try:
                    input_data = json.loads(input_data)
                except:
                    input_data = {}
            
            # Get filename from multiple locations
            filename = (
                input_data.get('filename') or 
                result_data.get('filename') or 
                job.get('filename') or
                input_data.get('project_name')
            )
            if not filename or filename == 'Unknown':
                job_type = job.get('job_type', 'upload')
                filename = f"{job_type.title()} job"
            
            # Build result message
            result_msg = None
            if result_data:
                tables = result_data.get('tables_created', 0)
                rows = result_data.get('total_rows', 0)
                if tables or rows:
                    result_msg = f"{tables} table(s), {rows:,} rows loaded"
                else:
                    result_msg = result_data.get('message') or result_data.get('filename')
            
            status = job.get('status', 'unknown')
            created_at = job.get('created_at')
            
            # Determine stuck and cancellable status
            is_stuck = calculate_is_stuck(status, created_at)
            can_cancel = status in ['queued', 'processing']
            can_delete = status in ['completed', 'failed', 'cancelled']
            
            if is_stuck:
                stuck_count += 1
            if status in ['queued', 'processing']:
                active_count += 1
            
            formatted_jobs.append({
                'id': job['id'],
                'filename': filename,
                'type': job.get('job_type', 'upload'),
                'project': input_data.get('project_name') or job.get('project_id') or 'Unknown',
                'project_id': job.get('project_id'),
                'status': status,
                'progress': job.get('progress', {}).get('percent', 0) if job.get('progress') else 0,
                'current_step': job.get('progress', {}).get('step', '') if job.get('progress') else '',
                'error': job.get('error_message'),
                'result': result_msg,
                'tables_created': result_data.get('tables_created'),
                'total_rows': result_data.get('total_rows'),
                'created_at': created_at,
                'updated_at': job.get('updated_at'),
                'is_stuck': is_stuck,
                'can_cancel': can_cancel,
                'can_delete': can_delete
            })
        
        return {
            "jobs": formatted_jobs,
            "total": len(formatted_jobs),
            "active": active_count,
            "stuck": stuck_count
        }
    except Exception as e:
        logger.exception(f"[JOBS] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Get a specific job with full details."""
    try:
        job = ProcessingJobModel.get_by_id(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        input_data = job.get('input_data') or {}
        if isinstance(input_data, str):
            try:
                input_data = json.loads(input_data)
            except:
                input_data = {}
        
        status = job.get('status', 'unknown')
        created_at = job.get('created_at')
        
        return {
            'id': job['id'],
            'filename': input_data.get('filename', 'Unknown'),
            'type': job.get('job_type', 'upload'),
            'project': job.get('project_id', 'Unknown'),
            'status': status,
            'progress': job.get('progress', {}).get('percent', 0),
            'current_step': job.get('progress', {}).get('step', ''),
            'error': job.get('error_message'),
            'result': job.get('result_data'),
            'created_at': created_at,
            'updated_at': job.get('updated_at'),
            'is_stuck': calculate_is_stuck(status, created_at),
            'can_cancel': status in ['queued', 'processing'],
            'can_delete': status in ['completed', 'failed', 'cancelled']
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Cancel a running/queued job."""
    try:
        # Check job exists and is cancellable
        job = ProcessingJobModel.get_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job.get('status') not in ['queued', 'processing']:
            raise HTTPException(
                status_code=400, 
                detail=f"Job is already {job.get('status')} - cannot cancel"
            )
        
        success = ProcessingJobModel.cancel(job_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to cancel job")
        
        logger.info(f"[JOBS] Cancelled job {job_id}")
        return {"success": True, "job_id": job_id, "message": "Job cancelled"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[JOBS] Cancel error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/cleanup")
async def cleanup_stuck_jobs(
    max_age_minutes: int = Query(15, description="Cancel jobs older than this many minutes")
):
    """
    Cancel all stuck jobs.
    
    Jobs in 'processing' or 'queued' status for longer than max_age_minutes
    will be marked as cancelled.
    """
    try:
        cancelled = ProcessingJobModel.cancel_stuck(max_age_minutes)
        logger.info(f"[JOBS] Cleanup cancelled {cancelled} stuck jobs")
        return {
            "success": True,
            "jobs_cancelled": cancelled,
            "cutoff_minutes": max_age_minutes
        }
    except Exception as e:
        logger.exception(f"[JOBS] Cleanup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/clear-all")
async def delete_all_jobs():
    """Delete all processing jobs from history."""
    try:
        deleted = ProcessingJobModel.delete_all()
        logger.info(f"[JOBS] Deleted {deleted} jobs")
        return {"success": True, "deleted": deleted}
    except Exception as e:
        logger.exception(f"[JOBS] Clear all error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a specific job from history."""
    try:
        # Check job exists
        job = ProcessingJobModel.get_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Don't allow deleting active jobs
        if job.get('status') in ['queued', 'processing']:
            raise HTTPException(
                status_code=400, 
                detail="Cannot delete active job - cancel it first"
            )
        
        success = ProcessingJobModel.delete(job_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete job")
        
        logger.info(f"[JOBS] Deleted job {job_id}")
        return {"success": True, "job_id": job_id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/jobs")
async def clear_job_history(
    status: str = Query(None, description="Only delete jobs with this status"),
    older_than_hours: int = Query(0, description="Only delete jobs older than this many hours (0 = all)")
):
    """
    Clear job history - delete completed/failed/cancelled jobs.
    
    Does NOT delete active (queued/processing) jobs.
    """
    try:
        from utils.supabase_client import get_supabase
        supabase = get_supabase()
        if not supabase:
            raise HTTPException(status_code=503, detail="Database not available")
        
        from datetime import timedelta
        
        # Build query for deletable jobs
        deletable_statuses = ['completed', 'failed', 'cancelled']
        if status and status in deletable_statuses:
            deletable_statuses = [status]
        
        # Time filter
        query = supabase.table("processing_jobs").select("id").in_("status", deletable_statuses)
        
        if older_than_hours > 0:
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=older_than_hours)).isoformat()
            query = query.lt("created_at", cutoff)
        
        jobs = query.execute()
        
        deleted = 0
        for job in (jobs.data or []):
            try:
                supabase.table("processing_jobs").delete().eq("id", job['id']).execute()
                deleted += 1
            except:
                pass
        
        logger.info(f"[JOBS] Cleared {deleted} jobs from history")
        return {
            "success": True,
            "jobs_deleted": deleted,
            "status_filter": status,
            "older_than_hours": older_than_hours
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[JOBS] Clear history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
