"""Upload API Router"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from typing import Optional
import sys
import uuid
from datetime import datetime

sys.path.insert(0, '/app')
sys.path.insert(0, '/data')

from utils.background.job_manager import JobManager
from utils.background.document_handler import DocumentHandler
from utils.database.supabase_client import get_supabase_client
from backend.websocket_manager import ws_manager

router = APIRouter()
job_manager = JobManager()
document_handler = DocumentHandler()

@router.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    project: str = Form(...),
    functional_area: Optional[str] = Form(None)
):
    try:
        job_id = str(uuid.uuid4())
        supabase = get_supabase_client()
        
        # Create job record
        supabase.table("processing_jobs").insert({
            "job_id": job_id,
            "filename": file.filename,
            "project": project,
            "functional_area": functional_area,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        }).execute()
        
        # Save file
        file_path = f"/data/uploads/{job_id}_{file.filename}"
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Queue background job
        background_tasks.add_task(
            process_document,
            job_id=job_id,
            file_path=file_path,
            project=project,
            functional_area=functional_area
        )
        
        return {"job_id": job_id, "status": "queued"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def process_document(job_id: str, file_path: str, project: str, functional_area: Optional[str]):
    try:
        supabase = get_supabase_client()
        
        # Update status to processing
        supabase.table("processing_jobs").update({
            "status": "processing"
        }).eq("job_id", job_id).execute()
        
        await ws_manager.broadcast({
            "job_id": job_id,
            "status": "processing",
            "progress": 0
        })
        
        # Process document
        result = document_handler.process_document(
            file_path=file_path,
            project=project,
            functional_area=functional_area,
            job_id=job_id,
            progress_callback=lambda p: ws_manager.broadcast({
                "job_id": job_id,
                "status": "processing",
                "progress": p
            })
        )
        
        # Update completion
        supabase.table("processing_jobs").update({
            "status": "completed",
            "chunks_processed": result.get("chunks", 0),
            "completed_at": datetime.utcnow().isoformat()
        }).eq("job_id", job_id).execute()
        
        await ws_manager.broadcast({
            "job_id": job_id,
            "status": "completed",
            "progress": 100,
            "chunks": result.get("chunks", 0)
        })
    except Exception as e:
        supabase.table("processing_jobs").update({
            "status": "failed",
            "error": str(e)
        }).eq("job_id", job_id).execute()
        
        await ws_manager.broadcast({
            "job_id": job_id,
            "status": "failed",
            "error": str(e)
        })
