"""
AI Assistant Chat Page - HIGHLY OPTIMIZED
Streaming responses, query caching, parallel processing
"""

import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
from typing import List, Dict, Any
import time
import hashlib
from concurrent.futures import ThreadPoolExecutor
import asyncio


def render_chat_page():
    """Render highly optimized chat interface"""
    
    # Initialize query cache FIRST
    if 'query_cache' not in st.session_state:
        st.session_state.query_cache = {}
    
    st.markdown("## 💬 AI Assistant")
    
    st.markdown("""
    <div class='info-box'>
        <strong>Advanced RAG Chat:</strong> Ask questions about UKG implementation.
        Optimized for speed with streaming responses and smart caching.
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize chat history
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # Compact settings in sidebar
    with st.sidebar:
        st.markdown("### 🎛️ Chat Settings")
        
        retrieval_method = st.selectbox(
            "Retrieval",
            ["Hybrid", "Semantic", "MMR"],
            help="Search method"
        )
        
        num_sources = st.slider("Sources", 1, 10, 3)
        
        use_compression = st.checkbox("Compression", value=False)
        show_sources = st.checkbox("Show Sources", value=True)
        
        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_history = []
            st.session_state.query_cache = {}
            st.rerun()
    
    # Display chat history (compact)
    for message in st.session_state.chat_history:
        with st.chat_message(message['role']):
            st.markdown(message['content'])
            
            if show_sources and message.get('sources'):
                with st.expander(f"📚 {len(message['sources'])} sources", expanded=False):
                    for i, source in enumerate(message['sources'], 1):
                        st.caption(f"**{i}. {source['doc_name']}** ({source['category']}) - {source.get('score', 0):.2f}")
    
    # Chat input
    if prompt := st.chat_input("Ask about UKG..."):
        # Add user message
        st.session_state.chat_history.append({'role': 'user', 'content': prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate response with streaming
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            sources_placeholder = st.empty()
            
            # Generate response
            response, sources = _generate_optimized_response(
                prompt=prompt,
                retrieval_method=retrieval_method,
                num_sources=num_sources,
                use_compression=use_compression,
                response_placeholder=response_placeholder
            )
            
            # Show final response
            response_placeholder.markdown(response)
            
            # Show sources
            if show_sources and sources:
                with sources_placeholder.expander(f"📚 {len(sources)} sources", expanded=False):
                    for i, source in enumerate(sources, 1):
                        st.caption(f"**{i}. {source['doc_name']}** ({source['category']}) - {source.get('score', 0):.2f}")
        
        # Add to history
        st.session_state.chat_history.append({
            'role': 'assistant',
            'content': response,
            'sources': sources
        })


def _generate_optimized_response(prompt: str, 
                                retrieval_method: str,
                                num_sources: int,
                                use_compression: bool,
                                response_placeholder) -> tuple[str, List[Dict[str, Any]]]:
    """
    Highly optimized response generation with:
    - Query caching
    - Parallel RAG search
    - Streaming LLM responses
    - Smart prompt optimization
    """
    
    start_time = time.time()
    
    # Get RAG handler
    rag_handler = st.session_state.get('rag_handler')
    
    if not rag_handler:
        return "RAG system not initialized. Upload documents to Knowledge Base first.", []
    
    # Ensure cache exists
    if 'query_cache' not in st.session_state:
        st.session_state.query_cache = {}
    
    # Check cache (60 second TTL)
    cache_key = hashlib.md5(f"{prompt}_{retrieval_method}_{num_sources}".encode()).hexdigest()
    cache_entry = st.session_state.query_cache.get(cache_key)
    
    if cache_entry and (time.time() - cache_entry['timestamp']) < 60:
        # Cache hit!
        return cache_entry['response'], cache_entry['sources']
    
    # Parallel operations: Get sources while preparing prompt
    with ThreadPoolExecutor(max_workers=2) as executor:
        # Start RAG search in background
        rag_future = executor.submit(_get_rag_sources, rag_handler, prompt, retrieval_method, num_sources, use_compression)
        
        # Prepare prompt template (happens in parallel)
        system_prompt = _build_optimized_prompt()
        
        # Wait for RAG results
        sources = rag_future.result()
    
    if not sources:
        return "No relevant information found. Upload more documents to the Knowledge Base.", []
    
    # Build compact context
    context = _build_compact_context(sources)
    
    # Build final prompt
    full_prompt = f"{system_prompt}\n\nCONTEXT:\n{context}\n\nQUESTION: {prompt}\n\nANSWER:"
    
    # Call LLM with streaming
    response = _call_llm_streaming(full_prompt, response_placeholder)
    
    # Cache result
    st.session_state.query_cache[cache_key] = {
        'response': response,
        'sources': sources,
        'timestamp': time.time()
    }
    
    # Cleanup old cache entries (keep last 10)
    if len(st.session_state.query_cache) > 10:
        oldest_key = min(st.session_state.query_cache.keys(), 
                        key=lambda k: st.session_state.query_cache[k]['timestamp'])
        del st.session_state.query_cache[oldest_key]
    
    return response, sources


def _get_rag_sources(rag_handler, prompt: str, method: str, n: int, compress: bool) -> List[Dict]:
    """Get sources from RAG (optimized)"""
    
    try:
        # Use fastest appropriate method
        if method == "Semantic":
            results = rag_handler.hybrid_search(prompt, n, alpha=1.0, strategy='semantic')
        elif method == "MMR":
            results = rag_handler.mmr_search(prompt, n, lambda_param=0.5, strategy='semantic')
        else:  # Hybrid
            results = rag_handler.hybrid_search(prompt, n, alpha=0.5, strategy='semantic')
        
        # Compress if needed (but only if context is large)
        if compress and results:
            total_length = sum(len(r.get('content', '')) for r in results)
            if total_length > 2000:  # Only compress if >2000 chars
                results = rag_handler.contextual_compression(prompt, results, 0.6)
        
        # Format sources
        sources = []
        for r in results:
            sources.append({
                'doc_name': r.get('metadata', {}).get('doc_name', 'Unknown'),
                'category': r.get('metadata', {}).get('category', 'Unknown'),
                'content': r.get('content', ''),
                'score': r.get('score', r.get('distance', 0))
            })
        
        return sources
        
    except Exception as e:
        st.error(f"RAG error: {str(e)}")
        return []


def _build_optimized_prompt() -> str:
    """Compact system prompt (fewer tokens = faster)"""
    return """You're a UKG expert. Use the context to answer. Be concise. Cite sources."""


def _build_compact_context(sources: List[Dict]) -> str:
    """Build minimal context (reduce tokens)"""
    # Limit each source to 200 chars max
    context_parts = []
    for i, source in enumerate(sources, 1):
        content = source['content'][:200] + "..." if len(source['content']) > 200 else source['content']
        context_parts.append(f"[{i}] {content}")
    
    return "\n\n".join(context_parts)


def _call_llm_streaming(prompt: str, placeholder) -> str:
    """Call LLM with streaming for perceived speed boost"""
    
    llm_endpoint = st.session_state.get('llm_endpoint', 'http://localhost:11435')
    llm_model = st.session_state.get('llm_model', 'deepseek-r1:7b')  # ← CHANGED TO DEEPSEEK!
    llm_username = st.session_state.get('llm_username', 'xlr8')
    llm_password = st.session_state.get('llm_password', 'Argyle76226#')
    
    try:
        url = f"{llm_endpoint}/api/generate"
        
        payload = {
            "model": llm_model,
            "prompt": prompt,
            "stream": True,  # Enable streaming
            "options": {
                "temperature": 0.7,
                "num_predict": 500,  # Limit response length for speed
                "num_ctx": 2048,     # Smaller context window
                "top_p": 0.9,
                "top_k": 40
            }
        }
        
        auth = HTTPBasicAuth(llm_username, llm_password)
        
        response = requests.post(url, json=payload, auth=auth, timeout=120, stream=True)
        response.raise_for_status()
        
        # Stream response token by token
        full_response = ""
        for line in response.iter_lines():
            if line:
                import json
                chunk = json.loads(line)
                token = chunk.get('response', '')
                full_response += token
                
                # Update placeholder with growing response
                placeholder.markdown(full_response + "▌")
        
        return full_response
        
    except Exception as e:
        return f"Error: {str(e)}"


if __name__ == "__main__":
    st.title("Optimized Chat - Test")
    render_chat_page()
