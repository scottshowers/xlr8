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
        
        # Convert to correct parameters
        project_id = request.project if request.project else None
        functional_areas = [request.functional_area] if request.functional_area else None
        
        results = rag.search(
            collection_name="documents",
            query=request.message,
            n_results=5,
            project_id=project_id,
            functional_areas=functional_areas
        )
        
        # Format response
        if not results:
            return {
                "response": "No relevant documents found.",
                "routing_decision": "local",
                "sources_count": 0
            }
        
        docs = [r['document'] for r in results[:3]]
        context = "\n\n".join(docs)
        
        response_text = f"Based on {len(results)} sources:\n\n{context}"
        
        return {
            "response": response_text,
            "routing_decision": "local",
            "sources_count": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
