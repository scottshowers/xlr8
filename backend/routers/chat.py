"""
Chat Router for XLR8 - PRODUCTION VERSION
=========================================

Smart routing:
- CONFIG queries → Claude direct (fast)
- EMPLOYEE queries → Local LLM → Sanitize → Claude

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
from utils.llm_orchestrator import LLMOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize orchestrator
orchestrator = LLMOrchestrator()


class ChatRequest(BaseModel):
    message: str
    project: Optional[str] = None
    functional_area: Optional[str] = None
    max_results: Optional[int] = 15


class ChatResponse(BaseModel):
    response: str
    sources: List[Dict[str, Any]]
    chunks_found: int
    models_used: List[str]
    query_type: str
    sanitized: bool


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Smart chat endpoint with query classification
    """
    try:
        logger.info(f"Chat: '{request.message[:80]}...' project={request.project}")
        
        # Initialize RAG
        rag = RAGHandler()
        
        # Get collection
        try:
            collection = rag.client.get_collection("documents")
        except:
            return ChatResponse(
                response="No documents uploaded yet. Please upload documents first.",
                sources=[],
                chunks_found=0,
                models_used=[],
                query_type="none",
                sanitized=False
            )
        
        # Get embedding
        query_embedding = rag.get_embedding(request.message)
        if not query_embedding:
            raise HTTPException(500, "Failed to create embedding")
        
        # Build filter
        where_filter = None
        if request.project and request.project not in ['', 'all', 'All Projects']:
            where_filter = {"project": request.project}
        
        # Search
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=request.max_results or 15,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )
        
        # Check results
        if not results or not results.get('documents') or not results['documents'][0]:
            return ChatResponse(
                response=f"No relevant documents found for: '{request.message}'",
                sources=[],
                chunks_found=0,
                models_used=[],
                query_type="none",
                sanitized=False
            )
        
        # Extract results
        documents = results['documents'][0]
        metadatas = results['metadatas'][0] if results.get('metadatas') else [{}] * len(documents)
        distances = results['distances'][0] if results.get('distances') else [0] * len(documents)
        
        logger.info(f"Found {len(documents)} chunks")
        
        # Build chunks for orchestrator
        chunks = []
        for doc, meta, dist in zip(documents, metadatas, distances):
            chunks.append({
                'document': doc,
                'metadata': meta,
                'distance': dist
            })
        
        # Build sources (grouped by file)
        source_map = {}
        for doc, meta, dist in zip(documents, metadatas, distances):
            filename = meta.get('filename', meta.get('source', 'Unknown'))
            
            if filename not in source_map:
                source_map[filename] = {
                    'filename': filename,
                    'functional_area': meta.get('functional_area', ''),
                    'sheets': set(),
                    'chunk_count': 0,
                    'max_relevance': 0
                }
            
            source_map[filename]['chunk_count'] += 1
            relevance = round((1 - dist) * 100, 1) if dist else 0
            source_map[filename]['max_relevance'] = max(source_map[filename]['max_relevance'], relevance)
            
            sheet = meta.get('parent_section', '')
            if sheet:
                source_map[filename]['sheets'].add(sheet)
        
        sources = []
        for fname, info in source_map.items():
            sources.append({
                'filename': fname,
                'functional_area': info['functional_area'],
                'sheets': list(info['sheets']),
                'chunk_count': info['chunk_count'],
                'relevance': info['max_relevance']
            })
        sources.sort(key=lambda x: x['relevance'], reverse=True)
        
        # Process with orchestrator
        result = orchestrator.process_query(request.message, chunks)
        
        return ChatResponse(
            response=result.get("response", "No response generated"),
            sources=sources,
            chunks_found=len(documents),
            models_used=result.get("models_used", []),
            query_type=result.get("query_type", "unknown"),
            sanitized=result.get("sanitized", False)
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(500, str(e))


@router.get("/chat/health")
async def health():
    """Health check"""
    try:
        rag = RAGHandler()
        collection = rag.client.get_or_create_collection("documents")
        chunk_count = collection.count()
        
        llm_status = orchestrator.check_status()
        
        return {
            "status": "healthy",
            "chromadb_chunks": chunk_count,
            "llm": llm_status
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/chat/test-ollama")
async def test_ollama():
    """Test Ollama connectivity"""
    status = orchestrator.check_status()
    
    return {
        "endpoint": os.getenv("LLM_ENDPOINT", "NOT SET"),
        "status": status.get("ollama_status", "unknown"),
        "models": status.get("models", []),
        "claude_configured": status.get("claude_configured", False)
    }
