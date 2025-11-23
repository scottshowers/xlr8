from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import sys

sys.path.insert(0, '/app')
sys.path.insert(0, '/data')

from utils.rag_handler import RAGHandler

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    project: Optional[str] = None
    functional_area: Optional[str] = None

@router.post("/chat")
async def chat(request: ChatRequest):
    try:
        rag = RAGHandler()
        
        metadata_filter = {}
        if request.project:
            metadata_filter["project"] = request.project
        if request.functional_area:
            metadata_filter["functional_area"] = request.functional_area
        
        results = rag.search(
            query=request.message,
            n_results=5,
            metadata_filter=metadata_filter if metadata_filter else None
        )
        
        # Simple response without intelligent routing for now
        docs = results.get("documents", [[]])[0] if results else []
        context = "\n\n".join(docs[:3]) if docs else "No relevant documents found."
        
        response_text = f"Based on {len(docs)} sources:\n\n{context}"
        
        return {
            "response": response_text,
            "routing_decision": "local",
            "sources_count": len(docs)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
