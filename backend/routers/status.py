"""Status API Router"""
from fastapi import APIRouter, HTTPException
import sys

sys.path.insert(0, '/app')
sys.path.insert(0, '/data')

from utils.rag_handler import RAGHandler
from utils.database.supabase_client import get_supabase_client

router = APIRouter()

@router.get("/status/jobs")
async def get_jobs():
    try:
        supabase = get_supabase_client()
        result = supabase.table("processing_jobs").select("*").order("created_at", desc=True).limit(50).execute()
        return {"jobs": result.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/chromadb")
async def get_chromadb_stats():
    try:
        rag = RAGHandler()
        stats = rag.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/status/chromadb/reset")
async def reset_chromadb():
    try:
        rag = RAGHandler()
        rag.reset_collection()
        return {"status": "reset_complete"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/job/{job_id}")
async def get_job_status(job_id: str):
    try:
        supabase = get_supabase_client()
        result = supabase.table("processing_jobs").select("*").eq("job_id", job_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Job not found")
        return result.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
