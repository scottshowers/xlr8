"""
Progress Streaming Router
=========================

SSE (Server-Sent Events) endpoint for real-time progress updates.
Allows frontend to see live chunk-by-chunk progress without polling.

Usage:
  const eventSource = new EventSource('/api/progress/stream/job-id-123');
  eventSource.onmessage = (e) => console.log(JSON.parse(e.data));
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import asyncio
import json
import sys
import logging
from typing import AsyncGenerator
from datetime import datetime

sys.path.insert(0, '/app')
sys.path.insert(0, '/data')

from utils.database.models import ProcessingJobModel

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory store for real-time chunk progress (not just job-level)
# Structure: { job_id: { chunks_total, chunks_done, current_chunk, rows_so_far, updates: [] } }
_chunk_progress = {}


def update_chunk_progress(job_id: str, chunk_index: int, total_chunks: int, 
                          rows_found: int, method: str, status: str = "processing"):
    """
    Called from smart_pdf_analyzer to report chunk-level progress.
    """
    if job_id not in _chunk_progress:
        _chunk_progress[job_id] = {
            "chunks_total": total_chunks,
            "chunks_done": 0,
            "rows_so_far": 0,
            "updates": [],
            "started_at": datetime.now().isoformat()
        }
    
    progress = _chunk_progress[job_id]
    
    if status == "done":
        progress["chunks_done"] += 1
        progress["rows_so_far"] += rows_found
    
    update = {
        "chunk_index": chunk_index,
        "total_chunks": total_chunks,
        "rows_found": rows_found,
        "method": method,
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "percent": int((progress["chunks_done"] / total_chunks) * 100) if total_chunks > 0 else 0
    }
    
    progress["updates"].append(update)
    progress["latest"] = update


def get_chunk_progress(job_id: str) -> dict:
    """Get current chunk progress for a job."""
    return _chunk_progress.get(job_id, {})


def clear_chunk_progress(job_id: str):
    """Clean up progress data when job completes."""
    if job_id in _chunk_progress:
        del _chunk_progress[job_id]


async def progress_generator(job_id: str) -> AsyncGenerator[str, None]:
    """
    Generator for SSE stream. Yields progress updates until job completes.
    """
    last_update_idx = 0
    no_update_count = 0
    max_no_updates = 120  # 2 minutes of no updates = timeout
    
    while True:
        try:
            # Get job status from database
            job = ProcessingJobModel.get_by_id(job_id)
            
            if not job:
                yield f"data: {json.dumps({'error': 'Job not found', 'job_id': job_id})}\n\n"
                break
            
            # Get chunk-level progress
            chunk_progress = get_chunk_progress(job_id)
            
            # Build update payload
            payload = {
                "job_id": job_id,
                "status": job.get("status", "unknown"),
                "progress_percent": job.get("progress", {}).get("percent", 0),
                "current_step": job.get("progress", {}).get("step", ""),
                "timestamp": datetime.now().isoformat()
            }
            
            # Add chunk details if available
            if chunk_progress:
                payload["chunks"] = {
                    "total": chunk_progress.get("chunks_total", 0),
                    "done": chunk_progress.get("chunks_done", 0),
                    "rows_so_far": chunk_progress.get("rows_so_far", 0)
                }
                
                # Send any new chunk updates
                updates = chunk_progress.get("updates", [])
                if len(updates) > last_update_idx:
                    payload["chunk_updates"] = updates[last_update_idx:]
                    last_update_idx = len(updates)
                    no_update_count = 0
                else:
                    no_update_count += 1
            else:
                no_update_count += 1
            
            # Check for completion
            if job.get("status") in ["completed", "failed", "error"]:
                payload["final"] = True
                if job.get("status") == "completed":
                    payload["result"] = job.get("result_data", {})
                elif job.get("error_message"):
                    payload["error"] = job.get("error_message")
                
                yield f"data: {json.dumps(payload)}\n\n"
                clear_chunk_progress(job_id)
                break
            
            # Timeout check
            if no_update_count > max_no_updates:
                payload["timeout"] = True
                payload["message"] = "No updates received for 2 minutes"
                yield f"data: {json.dumps(payload)}\n\n"
                break
            
            yield f"data: {json.dumps(payload)}\n\n"
            
            # Wait before next update
            await asyncio.sleep(1.0)
            
        except Exception as e:
            logger.error(f"[SSE] Error in progress stream: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            break


@router.get("/progress/stream/{job_id}")
async def stream_progress(job_id: str):
    """
    SSE endpoint for real-time job progress.
    
    Usage:
        const es = new EventSource('/api/progress/stream/job-123');
        es.onmessage = (e) => {
            const data = JSON.parse(e.data);
            console.log(data.progress_percent, data.chunks);
        };
    """
    return StreamingResponse(
        progress_generator(job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.get("/progress/{job_id}")
async def get_progress(job_id: str):
    """
    REST endpoint for job progress (for polling fallback).
    """
    job = ProcessingJobModel.get_by_id(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    chunk_progress = get_chunk_progress(job_id)
    
    return {
        "job_id": job_id,
        "status": job.get("status", "unknown"),
        "progress_percent": job.get("progress", {}).get("percent", 0),
        "current_step": job.get("progress", {}).get("step", ""),
        "chunks": {
            "total": chunk_progress.get("chunks_total", 0),
            "done": chunk_progress.get("chunks_done", 0),
            "rows_so_far": chunk_progress.get("rows_so_far", 0)
        } if chunk_progress else None,
        "result": job.get("result_data") if job.get("status") == "completed" else None,
        "error": job.get("error_message") if job.get("status") in ["failed", "error"] else None
    }


@router.get("/progress/active")
async def get_active_jobs():
    """
    Get all currently active jobs with progress.
    """
    active = []
    
    for job_id, progress in _chunk_progress.items():
        job = ProcessingJobModel.get_by_id(job_id)
        if job and job.get("status") not in ["completed", "failed", "error"]:
            active.append({
                "job_id": job_id,
                "filename": job.get("input_data", {}).get("filename", "Unknown"),
                "status": job.get("status"),
                "progress_percent": job.get("progress", {}).get("percent", 0),
                "chunks_done": progress.get("chunks_done", 0),
                "chunks_total": progress.get("chunks_total", 0),
                "rows_so_far": progress.get("rows_so_far", 0)
            })
    
    return {"active_jobs": active}
