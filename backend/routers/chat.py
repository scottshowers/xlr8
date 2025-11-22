"""Chat API Router"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import sys

sys.path.insert(0, '/app')
sys.path.insert(0, '/data')

from utils.ai.intelligent_router import IntelligentRouter
from utils.rag_handler import RAGHandler

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    project: Optional[str] = None
    functional_area: Optional[str] = None

@router.post("/chat")
async def chat(request: ChatRequest):
    try:
        intelligent_router = IntelligentRouter()
        rag = RAGHandler()
        
        # Build metadata filter
        metadata_filter = {}
        if request.project:
            metadata_filter["project"] = request.project
        if request.functional_area:
            metadata_filter["functional_area"] = request.functional_area
        
        # Search RAG
        results = rag.search(
            query=request.message,
            n_results=5,
            metadata_filter=metadata_filter if metadata_filter else None
        )
        
        # Route to appropriate LLM
        response = intelligent_router.route_query(
            query=request.message,
            context_docs=results.get("documents", [[]])[0] if results else []
        )
        
        return {
            "response": response["response"],
            "routing_decision": response.get("routing_decision", "unknown"),
            "sources_count": len(results.get("documents", [[]])[0]) if results else 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
