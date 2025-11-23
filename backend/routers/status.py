from fastapi import APIRouter, HTTPException
import sys

sys.path.insert(0, '/app')
sys.path.insert(0, '/data')

from utils.rag_handler import RAGHandler

router = APIRouter()

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
