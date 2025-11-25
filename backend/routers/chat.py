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
    max_results: Optional[int] = 30  # Increased from 15 for better coverage


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
        
        # SMART RETRIEVAL: Get more chunks for comprehensive answers
        n_results = request.max_results or 30
        
        # Search
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
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
        
        # SMART FILTERING: Prioritize chunks from relevant sheets
        query_lower = request.message.lower()
        
        # Map keywords to expected sheet names
        sheet_keywords = {
            'earning': ['earnings', 'earning'],
            'deduction': ['deductions', 'deduction'],
            'benefit': ['benefits', 'benefit'],
            'accrual': ['accruals', 'accrual', 'pto', 'time off'],
            'tax': ['taxes', 'tax', 'withholding'],
            'gl': ['gl rules', 'gl mapping', 'general ledger'],
            'pay code': ['pay codes', 'pay code'],
        }
        
        # Find which sheets to prioritize
        priority_sheets = []
        for keyword, sheets in sheet_keywords.items():
            if keyword in query_lower:
                priority_sheets.extend(sheets)
        
        # Sort chunks: priority sheets first, then by relevance
        if priority_sheets:
            logger.info(f"Prioritizing sheets containing: {priority_sheets}")
            
            def chunk_priority(item):
                doc, meta, dist = item
                sheet = str(meta.get('parent_section', '')).lower()
                # Check if sheet name contains any priority keyword
                is_priority = any(ps in sheet for ps in priority_sheets)
                # Priority chunks get distance bonus (lower = better)
                return (0 if is_priority else 1, dist)
            
            combined = list(zip(documents, metadatas, distances))
            combined.sort(key=chunk_priority)
            documents, metadatas, distances = zip(*combined) if combined else ([], [], [])
            documents, metadatas, distances = list(documents), list(metadatas), list(distances)
        
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


@router.get("/chat/debug-chunks")
async def debug_chunks(
    search: str = "earnings",
    project: Optional[str] = None,
    n: int = 50
):
    """Debug: See what chunks exist for a search term"""
    try:
        rag = RAGHandler()
        collection = rag.client.get_collection("documents")
        
        # Get embedding for search
        query_embedding = rag.get_embedding(search)
        
        # Build filter
        where_filter = {"project": project} if project else None
        
        # Search
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )
        
        if not results or not results['documents'][0]:
            return {"message": "No chunks found", "total": 0}
        
        # Group by sheet
        sheets = {}
        for doc, meta, dist in zip(results['documents'][0], results['metadatas'][0], results['distances'][0]):
            sheet = meta.get('parent_section', 'Unknown')
            if sheet not in sheets:
                sheets[sheet] = {
                    "count": 0,
                    "samples": [],
                    "avg_distance": 0
                }
            sheets[sheet]["count"] += 1
            sheets[sheet]["avg_distance"] += dist
            if len(sheets[sheet]["samples"]) < 2:
                sheets[sheet]["samples"].append({
                    "text": doc[:200] + "..." if len(doc) > 200 else doc,
                    "distance": round(dist, 3)
                })
        
        # Calculate averages
        for sheet in sheets:
            sheets[sheet]["avg_distance"] = round(sheets[sheet]["avg_distance"] / sheets[sheet]["count"], 3)
        
        return {
            "search_term": search,
            "project": project,
            "total_chunks": len(results['documents'][0]),
            "sheets": sheets
        }
        
    except Exception as e:
        return {"error": str(e)}
