"""
JOB MANAGEMENT ENDPOINTS
========================

Add these endpoints to your jobs router or create a new one.

Provides:
- DELETE /jobs/{job_id} - Delete single job
- DELETE /jobs/all - Delete all jobs
- DELETE /jobs/range - Delete jobs in date range
"""

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta
import logging
import os

logger = logging.getLogger(__name__)
router = APIRouter()

# Supabase client
_supabase = None

def _get_supabase():
    global _supabase
    if _supabase is None:
        try:
            from supabase import create_client
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
            if url and key:
                _supabase = create_client(url, key)
        except Exception as e:
            logger.warning(f"[JOBS] Supabase not available: {e}")
    return _supabase


# =============================================================================
# DELETE SINGLE JOB
# =============================================================================

@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """
    Delete a single job by ID.
    """
    supabase = _get_supabase()
    if not supabase:
        raise HTTPException(503, "Database not available")
    
    try:
        # Check if job exists
        check = supabase.table("jobs").select("id").eq("id", job_id).execute()
        if not check.data:
            raise HTTPException(404, f"Job not found: {job_id}")
        
        # Delete the job
        supabase.table("jobs").delete().eq("id", job_id).execute()
        
        logger.info(f"[JOBS] Deleted job: {job_id}")
        return {"success": True, "message": f"Job {job_id} deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[JOBS] Delete failed: {e}")
        raise HTTPException(500, f"Failed to delete job: {str(e)}")


# =============================================================================
# DELETE ALL JOBS
# =============================================================================

@router.delete("/jobs/all")
async def delete_all_jobs(project_id: str = Query(None, description="Optional: only delete jobs for this project")):
    """
    Delete all jobs, optionally filtered by project.
    """
    supabase = _get_supabase()
    if not supabase:
        raise HTTPException(503, "Database not available")
    
    try:
        query = supabase.table("jobs").delete()
        
        if project_id:
            query = query.eq("project_id", project_id)
        
        # Need to add a filter to delete (Supabase requires it for safety)
        # Delete jobs older than 1 second ago (effectively all)
        query = query.lt("created_at", datetime.utcnow().isoformat())
        
        result = query.execute()
        
        count = len(result.data) if result.data else 0
        logger.info(f"[JOBS] Deleted {count} jobs")
        return {"success": True, "deleted": count}
        
    except Exception as e:
        logger.error(f"[JOBS] Delete all failed: {e}")
        raise HTTPException(500, f"Failed to delete jobs: {str(e)}")


# =============================================================================
# DELETE JOBS IN DATE RANGE
# =============================================================================

@router.delete("/jobs/range")
async def delete_jobs_in_range(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    project_id: str = Query(None, description="Optional: only delete jobs for this project")
):
    """
    Delete jobs within a date range.
    """
    supabase = _get_supabase()
    if not supabase:
        raise HTTPException(503, "Database not available")
    
    try:
        # Parse dates
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)  # Include end date
        
        query = supabase.table("jobs").delete()\
            .gte("created_at", start.isoformat())\
            .lt("created_at", end.isoformat())
        
        if project_id:
            query = query.eq("project_id", project_id)
        
        result = query.execute()
        
        count = len(result.data) if result.data else 0
        logger.info(f"[JOBS] Deleted {count} jobs in range {start_date} to {end_date}")
        return {"success": True, "deleted": count, "start_date": start_date, "end_date": end_date}
        
    except ValueError as e:
        raise HTTPException(400, f"Invalid date format: {e}")
    except Exception as e:
        logger.error(f"[JOBS] Delete range failed: {e}")
        raise HTTPException(500, f"Failed to delete jobs: {str(e)}")


# =============================================================================
# INTEGRATION INSTRUCTIONS
# =============================================================================
"""
If you already have a jobs router, add these endpoints to it.

If not, add to main.py:

    from routers import jobs_management
    app.include_router(jobs_management.router, prefix="/api", tags=["jobs"])

The DataPage frontend expects these endpoints:
- DELETE /api/jobs/{job_id}
- DELETE /api/jobs/all
- DELETE /api/jobs/range?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
"""
