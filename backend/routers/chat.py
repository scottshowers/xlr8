"""
Chat Router for XLR8 - With Real-Time Status Updates & Query Decomposition
===========================================================================

Uses job-based processing with status polling (like upload)
NOW with compound question support (multi-sheet queries)

Author: XLR8 Team
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import sys
import os
import logging
import uuid
import threading
import time

sys.path.insert(0, '/app')
sys.path.insert(0, '/data')

from utils.rag_handler import RAGHandler
from utils.llm_orchestrator import LLMOrchestrator
from utils.query_decomposition import DiverseRetriever

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize orchestrator
orchestrator = LLMOrchestrator()

# In-memory job storage (for status tracking)
chat_jobs = {}


class ChatRequest(BaseModel):
    message: str
    project: Optional[str] = None
    functional_area: Optional[str] = None
    max_results: Optional[int] = 50  # Increased from 30 to get more chunks


class ChatJobStatus(BaseModel):
    job_id: str
    status: str  # 'processing', 'complete', 'error'
    current_step: str
    progress: int  # 0-100
    response: Optional[str] = None
    sources: Optional[List[Dict]] = None
    chunks_found: Optional[int] = None
    models_used: Optional[List[str]] = None
    query_type: Optional[str] = None
    sanitized: Optional[bool] = None
    error: Optional[str] = None


def update_job_status(job_id: str, status: str, step: str, progress: int, **kwargs):
    """Update job status"""
    if job_id in chat_jobs:
        chat_jobs[job_id].update({
            'status': status,
            'current_step': step,
            'progress': progress,
            **kwargs
        })
        logger.info(f"[JOB {job_id}] {step} ({progress}%)")


def process_chat_job(job_id: str, message: str, project: Optional[str], max_results: int):
    """Background processing for chat"""
    try:
        update_job_status(job_id, 'processing', '🔵 Searching documents...', 10)
        
        # Initialize RAG
        rag = RAGHandler()
        
        try:
            collection = rag.client.get_collection("documents")
        except:
            update_job_status(job_id, 'error', 'Error', 100, error='No documents uploaded')
            return
        
        # Build filter
        where_filter = None
        if project and project not in ['', 'all', 'All Projects']:
            where_filter = {"project": project}
        
        update_job_status(job_id, 'processing', '📊 Retrieving chunks...', 20)
        
        # DIVERSE RETRIEVAL: Handle compound questions automatically
        # Example: "Give me deduction groups and pay groups" 
        # → Searches both sheets separately and merges results
        
        try:
            from utils.query_decomposition import QueryDecomposer
            
            decomposer = QueryDecomposer()
            
            # Check if compound query
            if decomposer.is_compound_query(message):
                # COMPOUND QUERY: Split and search each separately
                sub_queries = decomposer.decompose_query(message)
                logger.info(f"[DIVERSE] Compound query detected: {len(sub_queries)} sub-queries")
                
                # Retrieve for each sub-query
                results_per_query = max_results // len(sub_queries)
                all_documents = []
                all_metadatas = []
                all_distances = []
                seen_ids = set()
                
                for i, sub_query in enumerate(sub_queries):
                    logger.info(f"[DIVERSE] Sub-query {i+1}: {sub_query}")
                    
                    # Get embedding for sub-query
                    sub_embedding = rag.get_embedding(sub_query)
                    if not sub_embedding:
                        continue
                    
                    # Search for this sub-query
                    sub_results = collection.query(
                        query_embeddings=[sub_embedding],
                        n_results=results_per_query + 10,  # Extra for deduplication
                        where=where_filter,
                        include=["documents", "metadatas", "distances"]
                    )
                    
                    # Add results, deduplicating by content hash
                    if sub_results and sub_results.get('documents') and sub_results['documents'][0]:
                        for j in range(len(sub_results['documents'][0])):
                            doc = sub_results['documents'][0][j]
                            doc_hash = hash(doc[:100])  # Simple deduplication
                            
                            if doc_hash in seen_ids:
                                continue
                            
                            seen_ids.add(doc_hash)
                            all_documents.append(doc)
                            all_metadatas.append(sub_results['metadatas'][0][j])
                            all_distances.append(sub_results['distances'][0][j])
                            
                            if len(all_documents) >= max_results:
                                break
                    
                    if len(all_documents) >= max_results:
                        break
                
                # Format as ChromaDB result
                results = {
                    'documents': [all_documents],
                    'metadatas': [all_metadatas],
                    'distances': [all_distances]
                }
                
                # Log diversity
                sheets_found = set()
                for meta in all_metadatas:
                    if 'parent_section' in meta:
                        sheets_found.add(meta['parent_section'])
                logger.info(f"[DIVERSE] Retrieved {len(all_documents)} chunks from {len(sheets_found)} sheets: {', '.join(sorted(sheets_found))}")
                
            else:
                # SIMPLE QUERY: Use normal search
                logger.info(f"[SIMPLE] Single-topic query, using standard search")
                
                # Get embedding
                query_embedding = rag.get_embedding(message)
                if not query_embedding:
                    update_job_status(job_id, 'error', 'Error', 100, error='Failed to create embedding')
                    return
                
                # Search
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=max_results,
                    where=where_filter,
                    include=["documents", "metadatas", "distances"]
                )
        
        except Exception as e:
            # Fallback to standard search if decomposition fails
            logger.warning(f"[DIVERSE] Decomposition failed, using standard search: {e}")
            
            query_embedding = rag.get_embedding(message)
            if not query_embedding:
                update_job_status(job_id, 'error', 'Error', 100, error='Failed to create embedding')
                return
            
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=max_results,
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )
        
        if not results or not results.get('documents') or not results['documents'][0]:
            update_job_status(job_id, 'error', 'Error', 100, error='No relevant documents found')
            return
        
        documents = results['documents'][0]
        metadatas = results['metadatas'][0] if results.get('metadatas') else [{}] * len(documents)
        distances = results['distances'][0] if results.get('distances') else [0] * len(documents)
        
        logger.info(f"Found {len(documents)} chunks")
        
        # Smart sheet filtering
        query_lower = message.lower()
        sheet_keywords = {
            'earning': ['earnings', 'earning'],
            'deduction': ['deductions', 'deduction'],
            'benefit': ['benefits', 'benefit'],
            'accrual': ['accruals', 'accrual', 'pto', 'time off'],
            'tax': ['taxes', 'tax', 'withholding'],
            'gl': ['gl rules', 'gl mapping', 'general ledger'],
            'pay code': ['pay codes', 'pay code'],
        }
        
        priority_sheets = []
        for keyword, sheets in sheet_keywords.items():
            if keyword in query_lower:
                priority_sheets.extend(sheets)
        
        if priority_sheets:
            def chunk_priority(item):
                doc, meta, dist = item
                sheet = str(meta.get('parent_section', '')).lower()
                is_priority = any(ps in sheet for ps in priority_sheets)
                return (0 if is_priority else 1, dist)
            
            combined = list(zip(documents, metadatas, distances))
            combined.sort(key=chunk_priority)
            documents, metadatas, distances = zip(*combined) if combined else ([], [], [])
            documents, metadatas, distances = list(documents), list(metadatas), list(distances)
        
        # Build chunks
        chunks = []
        for doc, meta, dist in zip(documents, metadatas, distances):
            chunks.append({'document': doc, 'metadata': meta, 'distance': dist})
        
        # Build sources
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
            
            # Calculate relevance with keyword boost
            relevance = round((1 - dist) * 100, 1) if dist else 0
            
            # BOOST: If query keyword matches sheet name, boost relevance to ~100%
            sheet_name = str(meta.get('parent_section', '')).lower()
            query_keywords = message.lower().split()
            for keyword in query_keywords:
                if len(keyword) > 3 and keyword in sheet_name:
                    # Major boost for exact sheet name match (boost by 30 points, cap at 99)
                    relevance = min(99, relevance + 30)
                    logger.info(f"Boosted relevance for '{keyword}' → '{sheet_name}': {relevance}%")
                    break
            
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
        
        # Classify query
        from utils.llm_orchestrator import classify_query
        query_type = classify_query(message, chunks)
        
        if query_type == 'config':
            update_job_status(job_id, 'processing', '⚡ Calling Claude (config)...', 40)
        else:
            update_job_status(job_id, 'processing', '🔵 Calling local LLM...', 40)
        
        time.sleep(0.5)  # Brief pause so user sees status
        
        # Process with orchestrator
        result = orchestrator.process_query(message, chunks)
        
        if result.get('query_type') == 'employee' and result.get('sanitized'):
            update_job_status(job_id, 'processing', '🔒 Sanitizing PII...', 70)
            time.sleep(0.3)
        
        update_job_status(job_id, 'processing', '✅ Finalizing response...', 90)
        time.sleep(0.2)
        
        # Complete
        update_job_status(
            job_id, 'complete', 'Complete', 100,
            response=result.get("response", "No response generated"),
            sources=sources,
            chunks_found=len(documents),
            models_used=result.get("models_used", []),
            query_type=result.get("query_type", "unknown"),
            sanitized=result.get("sanitized", False)
        )
        
    except Exception as e:
        logger.error(f"Chat job error: {e}", exc_info=True)
        update_job_status(job_id, 'error', 'Error', 100, error=str(e))


@router.post("/chat/start")
async def chat_start(request: ChatRequest):
    """Start a chat job and return job_id for polling"""
    job_id = str(uuid.uuid4())
    
    # Initialize job
    chat_jobs[job_id] = {
        'job_id': job_id,
        'status': 'processing',
        'current_step': 'Starting...',
        'progress': 0,
        'created_at': time.time()
    }
    
    # Start background processing
    thread = threading.Thread(
        target=process_chat_job,
        args=(job_id, request.message, request.project, request.max_results or 30)
    )
    thread.daemon = True
    thread.start()
    
    return {"job_id": job_id}


@router.get("/chat/status/{job_id}")
async def chat_status(job_id: str):
    """Get status of a chat job"""
    if job_id not in chat_jobs:
        raise HTTPException(404, "Job not found")
    
    return chat_jobs[job_id]


@router.delete("/chat/job/{job_id}")
async def delete_chat_job(job_id: str):
    """Clean up completed job"""
    if job_id in chat_jobs:
        del chat_jobs[job_id]
    return {"status": "deleted"}


# Keep the old endpoint for backward compatibility (non-streaming)
@router.post("/chat")
async def chat_legacy(request: ChatRequest):
    """Legacy chat endpoint - processes synchronously"""
    job_id = str(uuid.uuid4())
    chat_jobs[job_id] = {'job_id': job_id, 'status': 'processing', 'current_step': 'Processing...', 'progress': 0}
    
    # Process synchronously
    process_chat_job(job_id, request.message, request.project, request.max_results or 30)
    
    # Wait for completion
    result = chat_jobs[job_id]
    del chat_jobs[job_id]
    
    if result['status'] == 'error':
        raise HTTPException(500, result.get('error', 'Unknown error'))
    
    return {
        "response": result.get('response'),
        "sources": result.get('sources', []),
        "chunks_found": result.get('chunks_found', 0),
        "models_used": result.get('models_used', []),
        "query_type": result.get('query_type', 'unknown'),
        "sanitized": result.get('sanitized', False)
    }


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
        
        query_embedding = rag.get_embedding(search)
        where_filter = {"project": project} if project else None
        
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
                sheets[sheet] = {"count": 0, "samples": [], "avg_distance": 0}
            sheets[sheet]["count"] += 1
            sheets[sheet]["avg_distance"] += dist
            if len(sheets[sheet]["samples"]) < 2:
                sheets[sheet]["samples"].append({
                    "text": doc[:200] + "..." if len(doc) > 200 else doc,
                    "distance": round(dist, 3)
                })
        
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
