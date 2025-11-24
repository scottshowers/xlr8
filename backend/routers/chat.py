"""
Chat Router for XLR8 - RAG + LLM Integration
============================================

FEATURES:
- Searches ChromaDB for relevant chunks
- Sends context + question to LLM (Ollama or Claude)
- Returns response with source citations
- Supports project filtering

Author: XLR8 Team
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import sys
import os
import requests
from requests.auth import HTTPBasicAuth
import logging
import json

sys.path.insert(0, '/app')
sys.path.insert(0, '/data')

from utils.rag_handler import RAGHandler

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatRequest(BaseModel):
    """Chat request model"""
    message: str
    project: Optional[str] = None
    project_id: Optional[str] = None
    functional_area: Optional[str] = None
    conversation_history: Optional[List[Dict[str, str]]] = None
    max_results: Optional[int] = 10


class ChatResponse(BaseModel):
    """Chat response model"""
    response: str
    sources: List[Dict[str, Any]]
    chunks_found: int
    model_used: str


class LLMCaller:
    """Handles LLM calls to Ollama or Claude"""
    
    def __init__(self):
        # Ollama configuration
        self.ollama_url = os.getenv("LLM_ENDPOINT", "http://178.156.190.64:11435")
        self.ollama_username = os.getenv("LLM_USERNAME", "xlr8")
        self.ollama_password = os.getenv("LLM_PASSWORD", "Argyle76226#")
        self.ollama_model = os.getenv("LLM_MODEL", "llama3.1:8b")
        
        # Claude configuration (optional)
        self.claude_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.use_claude = os.getenv("USE_CLAUDE", "false").lower() == "true"
        
        logger.info(f"LLMCaller initialized - Ollama: {self.ollama_url}, Claude enabled: {self.use_claude}")
    
    def call_ollama(self, prompt: str, system_prompt: str = None) -> str:
        """Call Ollama LLM"""
        try:
            url = f"{self.ollama_url}/api/generate"
            
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
            
            payload = {
                "model": self.ollama_model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 2048
                }
            }
            
            logger.info(f"Calling Ollama at {url} with model {self.ollama_model}")
            
            response = requests.post(
                url,
                json=payload,
                auth=HTTPBasicAuth(self.ollama_username, self.ollama_password),
                timeout=120
            )
            
            if response.status_code != 200:
                logger.error(f"Ollama returned {response.status_code}: {response.text}")
                raise Exception(f"Ollama error: {response.status_code}")
            
            result = response.json()
            return result.get("response", "")
            
        except requests.exceptions.Timeout:
            logger.error("Ollama request timed out")
            raise Exception("LLM request timed out")
        except Exception as e:
            logger.error(f"Ollama call failed: {e}")
            raise
    
    def call_claude(self, prompt: str, system_prompt: str = None) -> str:
        """Call Claude API"""
        if not self.claude_api_key:
            raise Exception("Claude API key not configured")
        
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.claude_api_key)
            
            messages = [{"role": "user", "content": prompt}]
            
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                system=system_prompt or "You are a helpful assistant.",
                messages=messages
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Claude call failed: {e}")
            raise
    
    def generate(self, prompt: str, system_prompt: str = None) -> tuple[str, str]:
        """
        Generate response using configured LLM
        
        Returns: (response_text, model_name)
        """
        if self.use_claude and self.claude_api_key:
            try:
                response = self.call_claude(prompt, system_prompt)
                return response, "claude-sonnet"
            except Exception as e:
                logger.warning(f"Claude failed, falling back to Ollama: {e}")
        
        # Default to Ollama
        response = self.call_ollama(prompt, system_prompt)
        return response, self.ollama_model


def build_rag_prompt(question: str, context_chunks: List[Dict[str, Any]]) -> tuple[str, str]:
    """
    Build prompt for RAG query
    
    Returns: (user_prompt, system_prompt)
    """
    
    system_prompt = """You are an expert HCM implementation consultant analyzing customer documents. 
Your role is to provide accurate, helpful answers based ONLY on the provided context.

RULES:
1. Answer based ONLY on the provided context. If the context doesn't contain the answer, say so.
2. Be specific and cite which document/source your information comes from.
3. If multiple documents mention the topic, synthesize the information.
4. Use clear, professional language appropriate for HCM consultants.
5. If asked about configuration or data, provide specific details from the documents.
6. Format responses clearly with bullet points or numbered lists when appropriate.

Do not make up information. Do not use knowledge outside the provided context."""

    # Build context section
    context_parts = []
    for i, chunk in enumerate(context_chunks, 1):
        source = chunk.get('metadata', {}).get('source', chunk.get('metadata', {}).get('filename', 'Unknown'))
        sheet = chunk.get('metadata', {}).get('parent_section', '')
        area = chunk.get('metadata', {}).get('functional_area', '')
        
        header = f"[Source {i}: {source}"
        if sheet:
            header += f" - {sheet}"
        if area:
            header += f" ({area})"
        header += "]"
        
        context_parts.append(f"{header}\n{chunk.get('document', chunk.get('text', ''))}\n")
    
    context_text = "\n---\n".join(context_parts)
    
    user_prompt = f"""Based on the following documents, please answer this question:

QUESTION: {question}

CONTEXT FROM DOCUMENTS:
{context_text}

Please provide a clear, accurate answer based on the context above. Include source citations."""

    return user_prompt, system_prompt


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
    Main chat endpoint - RAG + LLM integration
    
    Flow:
    1. Search ChromaDB for relevant chunks
    2. Build prompt with context
    3. Call LLM for response
    4. Return response with sources
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
                model_used="none"
            )
        
        # Get query embedding
        query_embedding = rag.get_embedding(request.message)
        if query_embedding is None:
            raise HTTPException(status_code=500, detail="Failed to create query embedding")
        
        # Build where filter - filter by "project" field (stores project name)
        where_filter = None
        if request.project and request.project not in ['global', '__GLOBAL__', '', 'all', 'All Projects']:
            where_filter = {"project": request.project}
            logger.info(f"Filtering by project name: {request.project}")
            
            # Add functional area filter if specified
            if request.functional_area:
                where_filter = {
                    "$and": [
                        {"project": request.project},
                        {"functional_area": request.functional_area}
                    ]
                }
                logger.info(f"Also filtering by functional area: {request.functional_area}")
        
        # Search ChromaDB directly
        logger.info(f"Searching ChromaDB with filter: {where_filter}")
        
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
                model_used="none"
            )
        
        # Extract results
        documents = results['documents'][0]
        metadatas = results.get('metadatas', [[]])[0]
        distances = results.get('distances', [[]])[0]
        
        chunks_found = len(documents)
        logger.info(f"Found {chunks_found} relevant chunks")
        
        # Build context for LLM
        context_chunks = []
        sources = []
        
        for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances)):
            context_chunks.append({
                'document': doc,
                'metadata': meta,
                'distance': dist
            })
            
            # Build source info for response
            sources.append({
                'index': i + 1,
                'filename': meta.get('filename', meta.get('source', 'Unknown')),
                'functional_area': meta.get('functional_area', ''),
                'sheet': meta.get('parent_section', ''),
                'chunk_type': meta.get('chunk_type', 'unknown'),
                'relevance': round((1 - dist) * 100, 1) if dist else 0,
                'preview': doc[:200] + '...' if len(doc) > 200 else doc
            })
        
        # Build RAG prompt
        user_prompt, system_prompt = build_rag_prompt(request.message, context_chunks)
        
        # Call LLM
        logger.info("Calling LLM for response generation...")
        llm = LLMCaller()
        
        try:
            response_text, model_used = llm.generate(user_prompt, system_prompt)
            logger.info(f"LLM response generated using {model_used}")
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            # Return context without LLM synthesis
            response_text = f"""I found {chunks_found} relevant document sections, but couldn't generate a synthesis.

**Relevant Sources Found:**
"""
            for source in sources[:5]:
                response_text += f"\n- **{source['filename']}**"
                if source['sheet']:
                    response_text += f" ({source['sheet']})"
                response_text += f": {source['preview'][:100]}..."
            
            model_used = "fallback"
        
        return ChatResponse(
            response=response_text,
            sources=sources,
            chunks_found=chunks_found,
            model_used=model_used
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/simple")
async def chat_simple(request: ChatRequest):
    """
    Simple chat endpoint - just returns relevant chunks without LLM
    
    Useful for testing RAG retrieval
    """
    try:
        rag = RAGHandler()
        
        # Get collection
        try:
            collection = rag.client.get_collection("documents")
        except:
            return {
                "chunks": [],
                "message": "No documents collection found"
            }
        
        # Get query embedding
        query_embedding = rag.get_embedding(request.message)
        if query_embedding is None:
            return {
                "chunks": [],
                "message": "Failed to create query embedding"
            }
        
        # Build filter
        where_filter = None
        if request.project and request.project not in ['global', '__GLOBAL__', '', 'all']:
            where_filter = {"project": request.project}
        
        # Search
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=request.max_results or 10,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )
        
        if not results or not results.get('documents') or not results['documents'][0]:
            return {
                "chunks": [],
                "message": "No relevant documents found"
            }
        
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
    """Health check for chat system"""
    try:
        # Check RAG
        rag = RAGHandler()
        collection = rag.client.get_or_create_collection("documents")
        chunk_count = collection.count()
        
        # Check LLM connectivity
        llm = LLMCaller()
        llm_status = "unknown"
        try:
            # Quick test
            test_response = requests.get(
                f"{llm.ollama_url}/api/tags",
                auth=HTTPBasicAuth(llm.ollama_username, llm.ollama_password),
                timeout=5
            )
            llm_status = "connected" if test_response.status_code == 200 else "error"
        except:
            llm_status = "unreachable"
        
        return {
            "status": "healthy",
            "chromadb_chunks": chunk_count,
            "llm_status": llm_status,
            "llm_endpoint": llm.ollama_url,
            "llm_model": llm.ollama_model
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
