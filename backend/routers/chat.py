"""
Chat Router for XLR8 - Multi-Model Orchestration
================================================

ARCHITECTURE:
1. Search ChromaDB for relevant chunks
2. Route to local LLM (Mistral/DeepSeek) - can see PII
3. SANITIZE output (strip all PII)
4. Send to Claude for synthesis - NEVER sees PII
5. Return response with sources

Author: XLR8 Team
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import sys
import os
import logging

sys.path.insert(0, '/app')
sys.path.insert(0, '/data')

from utils.rag_handler import RAGHandler
from utils.llm_orchestrator import LLMOrchestrator, PIISanitizer

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize orchestrator
orchestrator = LLMOrchestrator()


class ChatRequest(BaseModel):
    """Chat request model"""
    message: str
    project: Optional[str] = None
    project_id: Optional[str] = None
    functional_area: Optional[str] = None
    max_results: Optional[int] = 10
    use_claude: Optional[bool] = True  # Use Claude for synthesis


class ChatResponse(BaseModel):
    """Chat response model"""
    response: str
    sources: List[Dict[str, Any]]
    chunks_found: int
    models_used: List[str]
    sanitized: bool


def build_no_context_response(question: str) -> str:
    """Build response when no relevant documents are found"""
    return f"""I couldn't find any relevant documents to answer your question: "{question}"

This could mean:
1. No documents have been uploaded yet for this project
2. The uploaded documents don't contain information about this topic
3. Try rephrasing your question with different keywords

**Suggestions:**
- Check the Status page to see uploaded documents
- Upload relevant documents via the Upload page
- Try a more general search term"""


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint - Multi-model orchestration with PII protection
    
    FLOW:
    1. Search ChromaDB for relevant chunks
    2. Local LLM (Mistral/DeepSeek) analyzes with FULL context (can see PII)
    3. Response is SANITIZED (all PII removed)
    4. Claude synthesizes final response (NEVER sees PII)
    5. Return to user with sources
    """
    try:
        logger.info(f"Chat request: '{request.message[:100]}...' project={request.project}")
        
        # Initialize RAG handler
        rag = RAGHandler()
        
        # Get collection
        try:
            collection = rag.client.get_collection("documents")
        except Exception as e:
            logger.error(f"Failed to get collection: {e}")
            return ChatResponse(
                response="No documents have been uploaded yet. Please upload some documents first.",
                sources=[],
                chunks_found=0,
                models_used=[],
                sanitized=False
            )
        
        # Get query embedding
        query_embedding = rag.get_embedding(request.message)
        if query_embedding is None:
            raise HTTPException(status_code=500, detail="Failed to create query embedding")
        
        # Build where filter
        where_filter = None
        if request.project and request.project not in ['global', '__GLOBAL__', '', 'all', 'All Projects']:
            where_filter = {"project": request.project}
            logger.info(f"Filtering by project: {request.project}")
            
            if request.functional_area:
                where_filter = {
                    "$and": [
                        {"project": request.project},
                        {"functional_area": request.functional_area}
                    ]
                }
        
        # Search ChromaDB
        logger.info("Searching ChromaDB for relevant chunks...")
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=request.max_results or 10,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )
        
        # Check for results
        if not results or not results.get('documents') or not results['documents'][0]:
            logger.warning("No relevant documents found")
            return ChatResponse(
                response=build_no_context_response(request.message),
                sources=[],
                chunks_found=0,
                models_used=[],
                sanitized=False
            )
        
        # Extract results
        documents = results['documents'][0]
        metadatas = results.get('metadatas', [[]])[0]
        distances = results.get('distances', [[]])[0]
        
        chunks_found = len(documents)
        logger.info(f"Found {chunks_found} relevant chunks")
        
        # Build chunks for orchestrator
        chunks = []
        sources = []
        
        for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances)):
            chunks.append({
                'document': doc,
                'metadata': meta,
                'distance': dist
            })
            
            sources.append({
                'index': i + 1,
                'filename': meta.get('filename', meta.get('source', 'Unknown')),
                'functional_area': meta.get('functional_area', ''),
                'sheet': meta.get('parent_section', ''),
                'chunk_type': meta.get('chunk_type', 'unknown'),
                'relevance': round((1 - dist) * 100, 1) if dist else 0,
                'preview': doc[:200] + '...' if len(doc) > 200 else doc
            })
        
        # Call orchestrator for multi-model processing
        logger.info("Starting multi-model orchestration...")
        result = orchestrator.process_query(
            query=request.message,
            chunks=chunks,
            use_claude_synthesis=request.use_claude and bool(os.getenv("ANTHROPIC_API_KEY"))
        )
        
        if result.get("error"):
            logger.error(f"Orchestration error: {result['error']}")
        
        return ChatResponse(
            response=result.get("response", "Failed to generate response"),
            sources=sources,
            chunks_found=chunks_found,
            models_used=result.get("models_used", []),
            sanitized=result.get("sanitized", False)
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/simple")
async def chat_simple(request: ChatRequest):
    """
    Simple chat endpoint - Returns chunks without LLM processing
    
    Useful for testing RAG retrieval
    """
    try:
        rag = RAGHandler()
        
        try:
            collection = rag.client.get_collection("documents")
        except:
            return {"chunks": [], "message": "No documents collection found"}
        
        query_embedding = rag.get_embedding(request.message)
        if query_embedding is None:
            return {"chunks": [], "message": "Failed to create query embedding"}
        
        where_filter = None
        if request.project and request.project not in ['global', '__GLOBAL__', '', 'all']:
            where_filter = {"project": request.project}
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=request.max_results or 10,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )
        
        if not results or not results.get('documents') or not results['documents'][0]:
            return {"chunks": [], "message": "No relevant documents found"}
        
        documents = results['documents'][0]
        metadatas = results.get('metadatas', [[]])[0]
        distances = results.get('distances', [[]])[0]
        
        chunks = []
        for doc, meta, dist in zip(documents, metadatas, distances):
            chunks.append({
                'text': doc,
                'metadata': meta,
                'relevance': round((1 - dist) * 100, 1) if dist else 0
            })
        
        return {
            "chunks": chunks,
            "count": len(chunks),
            "message": f"Found {len(chunks)} relevant chunks"
        }
        
    except Exception as e:
        logger.error(f"Simple chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/health")
async def chat_health():
    """Health check for chat system including all models"""
    try:
        # Check RAG
        rag = RAGHandler()
        collection = rag.client.get_or_create_collection("documents")
        chunk_count = collection.count()
        
        # Check models
        model_status = orchestrator.check_models_available()
        
        return {
            "status": "healthy",
            "chromadb_chunks": chunk_count,
            "models": {
                "local": {
                    "available": model_status.get("local", False),
                    "model": model_status.get("local_model", "unknown"),
                    "all_models": model_status.get("available_models", [])
                },
                "claude": "configured" if model_status.get("claude") else "not configured"
            },
            "privacy": {
                "pii_sanitization": "enabled",
                "claude_receives": "sanitized data only",
                "local_llm_receives": "full context with PII"
            }
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@router.get("/chat/models")
async def chat_models():
    """List available models and their purposes"""
    model_status = orchestrator.check_models_available()
    
    return {
        "models": [
            {
                "name": model_status.get("local_model", "mistral:7b"),
                "type": "local",
                "purpose": "Document analysis, data extraction, HR queries",
                "can_see_pii": True,
                "available": model_status.get("local", False),
                "location": "Hetzner (your server)"
            },
            {
                "name": "claude-sonnet",
                "type": "cloud",
                "purpose": "Final synthesis, response formatting, best practice recommendations",
                "can_see_pii": False,
                "note": "Only receives SANITIZED data - never sees PII",
                "available": model_status.get("claude", False),
                "location": "Anthropic API"
            }
        ],
        "available_ollama_models": model_status.get("available_models", []),
        "ollama_error": model_status.get("ollama_error"),
        "flow": [
            "1. User query → Search documents in ChromaDB",
            "2. Documents → Local LLM (can see PII)",
            "3. Local analysis → SANITIZE (remove all PII)",
            "4. Sanitized analysis → Claude (synthesis)",
            "5. Final response → User"
        ]
    }


@router.get("/chat/test-ollama")
async def test_ollama():
    """Test Ollama connectivity directly"""
    import os
    
    config = {
        "LLM_ENDPOINT": os.getenv("LLM_ENDPOINT", "NOT SET"),
        "LLM_MODEL": os.getenv("LLM_MODEL", "NOT SET"),
        "LLM_USERNAME": os.getenv("LLM_USERNAME", "NOT SET"),
        "LLM_PASSWORD": "***" if os.getenv("LLM_PASSWORD") else "NOT SET",
        "CLAUDE_API_KEY": "***" if os.getenv("CLAUDE_API_KEY") else "NOT SET"
    }
    
    # Test Ollama connection
    ollama_test = {"status": "unknown"}
    try:
        import requests
        from requests.auth import HTTPBasicAuth
        
        url = os.getenv("LLM_ENDPOINT", "") + "/api/tags"
        response = requests.get(
            url,
            auth=HTTPBasicAuth(
                os.getenv("LLM_USERNAME", ""),
                os.getenv("LLM_PASSWORD", "")
            ),
            timeout=10
        )
        
        ollama_test["status_code"] = response.status_code
        if response.status_code == 200:
            ollama_test["status"] = "connected"
            ollama_test["models"] = [m.get("name") for m in response.json().get("models", [])]
        elif response.status_code == 401:
            ollama_test["status"] = "auth_failed"
        else:
            ollama_test["status"] = f"error_{response.status_code}"
            
    except requests.exceptions.Timeout:
        ollama_test["status"] = "timeout"
    except requests.exceptions.ConnectionError as e:
        ollama_test["status"] = "connection_failed"
        ollama_test["error"] = str(e)
    except Exception as e:
        ollama_test["status"] = "error"
        ollama_test["error"] = str(e)
    
    return {
        "config": config,
        "ollama_test": ollama_test
    }
