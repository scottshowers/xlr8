"""
AI Assistant Chat Page - Claude.ai Style Interface (SIDEBAR FIXED)
Clean, modern chat interface with auto-expanding input
"""

import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
from typing import List, Dict, Any
import time
import hashlib
from concurrent.futures import ThreadPoolExecutor


# Custom CSS to match Claude.ai style - FIXED FOR SIDEBAR
CLAUDE_STYLE_CSS = """
<style>
/* Main chat container - NO centering, respect sidebar */
.main .block-container {
    padding-top: 2rem;
    padding-bottom: 6rem;
    max-width: 100%;
    padding-left: 2rem;
    padding-right: 2rem;
}

/* Chat messages */
.stChatMessage {
    padding: 1.5rem 1rem;
    margin-bottom: 0;
    border-bottom: 1px solid #e5e7eb;
    max-width: 48rem;
}

.stChatMessage:last-child {
    border-bottom: none;
}

/* Message content */
.stChatMessage [data-testid="stMarkdownContainer"] {
    font-size: 0.95rem;
    line-height: 1.6;
    color: #1f2937;
}

/* User messages - slightly different background */
.stChatMessage[data-testid="user"] {
    background-color: #f9fafb;
}

/* Assistant messages */
.stChatMessage[data-testid="assistant"] {
    background-color: #ffffff;
}

/* Chat input container - FIXED to respect sidebar */
.stChatInput {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    padding: 1rem 2rem;
    background: linear-gradient(to top, white 80%, transparent);
    border-top: 1px solid #e5e7eb;
    z-index: 100;
}

/* Adjust for sidebar when open */
@media (min-width: 768px) {
    .stChatInput {
        left: auto;
        /* Streamlit sidebar is ~21rem wide */
        margin-left: 21rem;
    }
}

.stChatInput > div {
    max-width: 48rem;
}

.stChatInput textarea {
    border-radius: 24px !important;
    border: 1px solid #d1d5db !important;
    padding: 12px 48px 12px 16px !important;
    font-size: 0.95rem !important;
    box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05) !important;
    resize: none !important;
}

.stChatInput textarea:focus {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1) !important;
}

/* Send button styling */
.stChatInput button {
    background-color: #6366f1 !important;
    border-radius: 50% !important;
    padding: 8px !important;
    right: 20px !important;
}

.stChatInput button:hover {
    background-color: #4f46e5 !important;
}

/* Expander for sources */
.streamlit-expanderHeader {
    font-size: 0.875rem;
    color: #6b7280;
    font-weight: 500;
}

.streamlit-expanderHeader:hover {
    color: #4b5563;
}

/* Source citations */
.source-citation {
    font-size: 0.813rem;
    color: #6b7280;
    padding: 0.5rem;
    background-color: #f9fafb;
    border-radius: 6px;
    margin-bottom: 0.5rem;
}

/* Sidebar styling */
section[data-testid="stSidebar"] {
    background-color: #f9fafb;
}

section[data-testid="stSidebar"] > div {
    padding-top: 2rem;
}

/* Compact sidebar headers */
section[data-testid="stSidebar"] h3 {
    font-size: 0.875rem;
    font-weight: 600;
    color: #374151;
    margin-top: 1.5rem;
    margin-bottom: 0.5rem;
}

/* Sidebar widgets */
section[data-testid="stSidebar"] .stSelectbox,
section[data-testid="stSidebar"] .stSlider,
section[data-testid="stSidebar"] .stCheckbox {
    font-size: 0.875rem;
}

/* Hide Streamlit branding */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""


def render_chat_page():
    """Render Claude.ai style chat interface"""
    
    # Apply custom CSS
    st.markdown(CLAUDE_STYLE_CSS, unsafe_allow_html=True)
    
    # Initialize query cache
    if 'query_cache' not in st.session_state:
        st.session_state.query_cache = {}
    
    # Initialize chat history
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # Compact settings in sidebar
    with st.sidebar:
        st.markdown("### ⚙️ Settings")
        
        retrieval_method = st.selectbox(
            "Search Method",
            ["Hybrid", "Semantic", "MMR"],
            help="How to search documents"
        )
        
        num_sources = st.slider(
            "Number of Sources", 
            min_value=1, 
            max_value=10, 
            value=5,
            help="Sources to retrieve per query"
        )
        
        show_sources = st.checkbox(
            "Show Sources", 
            value=True,
            help="Display source documents"
        )
        
        use_compression = st.checkbox(
            "Compress Context",
            value=False,
            help="Reduce context size (experimental)"
        )
        
        st.markdown("---")
        
        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state.chat_history = []
            st.session_state.query_cache = {}
            st.rerun()
    
    # Display chat history
    for message in st.session_state.chat_history:
        with st.chat_message(message['role']):
            st.markdown(message['content'])
            
            # Show sources if available
            if show_sources and message.get('sources'):
                with st.expander(f"📚 {len(message['sources'])} sources used", expanded=False):
                    for i, source in enumerate(message['sources'], 1):
                        score = source.get('score', 0)
                        st.markdown(
                            f"""<div class='source-citation'>
                            <strong>{i}.</strong> {source['doc_name']} 
                            <span style='color: #9ca3af;'>({source['category']})</span>
                            <span style='color: #9ca3af; float: right;'>Score: {score:.2f}</span>
                            </div>""",
                            unsafe_allow_html=True
                        )
    
    # Chat input - using Streamlit's built-in chat input (Claude-style)
    prompt = st.chat_input(
        placeholder="Ask about UKG implementation...",
        key="chat_input"
    )
    
    # Process new message
    if prompt:
        # Add user message to history
        st.session_state.chat_history.append({
            'role': 'user',
            'content': prompt
        })
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate response
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            sources_placeholder = st.empty()
            
            # Generate response with streaming
            response, sources = _generate_optimized_response(
                prompt=prompt,
                retrieval_method=retrieval_method,
                num_sources=num_sources,
                use_compression=use_compression,
                response_placeholder=response_placeholder
            )
            
            # Display final response
            response_placeholder.markdown(response)
            
            # Show sources
            if show_sources and sources:
                with sources_placeholder.expander(f"📚 {len(sources)} sources used", expanded=False):
                    for i, source in enumerate(sources, 1):
                        score = source.get('score', 0)
                        st.markdown(
                            f"""<div class='source-citation'>
                            <strong>{i}.</strong> {source['doc_name']} 
                            <span style='color: #9ca3af;'>({source['category']})</span>
                            <span style='color: #9ca3af; float: right;'>Score: {score:.2f}</span>
                            </div>""",
                            unsafe_allow_html=True
                        )
        
        # Add assistant response to history
        st.session_state.chat_history.append({
            'role': 'assistant',
            'content': response,
            'sources': sources
        })
        
        # Rerun to clear input and update display
        st.rerun()


def _generate_optimized_response(
    prompt: str,
    retrieval_method: str,
    num_sources: int,
    use_compression: bool,
    response_placeholder
) -> tuple[str, List[Dict[str, Any]]]:
    """
    Generate response with RAG context
    Optimized with caching and parallel processing
    """
    
    start_time = time.time()
    
    # Get RAG handler using AppConfig (respects feature flags!)
    try:
        from config import AppConfig
        rag_handler = st.session_state.get('rag_handler')
        
        if not rag_handler:
            # Try to initialize from AppConfig
            try:
                rag_handler = AppConfig.get_rag_handler()
                st.session_state.rag_handler = rag_handler
            except Exception:
                pass
        
        if not rag_handler:
            return "⚠️ Please upload documents to the Knowledge Base first.", []
    except Exception as e:
        return f"⚠️ Configuration error: {str(e)}", []
    
    # Check query cache (60 second TTL)
    cache_key = hashlib.md5(f"{prompt}_{retrieval_method}_{num_sources}".encode()).hexdigest()
    cached = st.session_state.query_cache.get(cache_key)
    
    if cached and (time.time() - cached['timestamp'] < 60):
        return cached['response'], cached['sources']
    
    # Get LLM provider early (needed for fallback if no docs)
    provider = st.session_state.get('llm_provider', 'local')
    
    # Parallel RAG search in background
    with ThreadPoolExecutor(max_workers=1) as executor:
        # Try to call search with method parameter (for advanced handlers)
        # Fall back to basic search if method parameter not supported
        def safe_search():
            try:
                # Try advanced search with method parameter
                return rag_handler.search(
                    prompt,
                    method=retrieval_method.lower(),
                    n_results=num_sources
                )
            except TypeError:
                # Handler doesn't support 'method' parameter, use basic search
                try:
                    return rag_handler.search(
                        prompt,
                        n_results=num_sources
                    )
                except Exception:
                    # Last resort: just query with no params
                    return rag_handler.search(prompt)
        
        search_future = executor.submit(safe_search)
        
        # Get search results
        try:
            sources = search_future.result(timeout=10)
        except Exception as e:
            return f"⚠️ Search error: {str(e)}", []
    
    if not sources:
        # No documents found - use LLM's general knowledge instead
        # Build a prompt without RAG context
        if provider == 'claude':
            prompt_without_docs = f"""You are an expert UKG implementation consultant. 

QUESTION: {prompt}

Provide a comprehensive answer using your general knowledge:"""
        else:
            prompt_without_docs = f"""You are an expert UKG implementation consultant. Answer the following question using your knowledge.

QUESTION: {prompt}

Provide a detailed answer:"""
        
        # Call LLM without documents
        if provider == 'claude':
            response = _call_claude_api(prompt_without_docs, response_placeholder)
        else:
            response = _call_local_llm(prompt_without_docs, response_placeholder)
        
        return response, []  # Return response with no sources
    
    # Build context from sources
    context_parts = []
    for i, source in enumerate(sources, 1):
        # Get more text per source (1000 chars)
        text = source.get('text', '')[:1000]
        doc_name = source.get('doc_name', 'Unknown')
        category = source.get('category', 'Unknown')
        
        context_parts.append(
            f"[Source {i}: {doc_name} ({category})]\n{text}\n"
        )
    
    context = "\n".join(context_parts)
    
    # Optional context compression
    if use_compression and len(context) > 2000:
        context = context[:2000] + "...[truncated]"
    
    # Build prompt based on provider
    if provider == 'claude':
        # Hybrid mode - Claude can use docs + training knowledge
        system_prompt = """You are an expert UKG implementation consultant. Answer questions using:
1. PRIMARY: Information from the provided documents
2. SECONDARY: Your general knowledge about UKG systems

Be thorough and detailed. If documents don't fully answer the question, you can supplement with general UKG knowledge."""
        
        full_prompt = f"""{system_prompt}

DOCUMENTS:
{context}

QUESTION: {prompt}

Provide a comprehensive, detailed answer:"""
    else:
        # Local LLM - strict RAG mode
        full_prompt = f"""You are an expert UKG implementation consultant. Answer the following question using ONLY the information provided in the documents below.

DOCUMENTS:
{context}

QUESTION: {prompt}

Provide a thorough, detailed answer based on the documents:"""
    
    # Generate response
    if provider == 'claude':
        response = _call_claude_api(full_prompt, response_placeholder)
    else:
        response = _call_local_llm(full_prompt, response_placeholder)
    
    # Cache the result
    st.session_state.query_cache[cache_key] = {
        'response': response,
        'sources': sources,
        'timestamp': time.time()
    }
    
    # Trim cache to last 10 queries
    if len(st.session_state.query_cache) > 10:
        oldest_key = min(
            st.session_state.query_cache.keys(),
            key=lambda k: st.session_state.query_cache[k]['timestamp']
        )
        del st.session_state.query_cache[oldest_key]
    
    return response, sources


def _call_local_llm(prompt: str, placeholder) -> str:
    """Call local LLM with streaming"""
    from config import AppConfig
    
    try:
        response = requests.post(
            f"{AppConfig.LLM_ENDPOINT}/api/generate",
            json={
                "model": AppConfig.LLM_DEFAULT_MODEL,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": 0.7,
                    "num_ctx": 8192  # Large context window
                }
            },
            auth=HTTPBasicAuth(AppConfig.LLM_USERNAME, AppConfig.LLM_PASSWORD),
            stream=True,
            timeout=120
        )
        
        response.raise_for_status()
        
        # Stream the response
        full_response = ""
        for line in response.iter_lines():
            if line:
                import json
                try:
                    chunk = json.loads(line)
                    if 'response' in chunk:
                        token = chunk['response']
                        full_response += token
                        placeholder.markdown(full_response + "▌")
                except json.JSONDecodeError:
                    continue
        
        return full_response
        
    except Exception as e:
        return f"⚠️ Error calling local LLM: {str(e)}"


def _call_claude_api(prompt: str, placeholder) -> str:
    """Call Claude API with streaming"""
    
    # Get API key from session state
    api_key = st.session_state.get('claude_api_key')
    
    if not api_key:
        return "⚠️ Please enter your Claude API key in the sidebar."
    
    try:
        import anthropic
        
        client = anthropic.Anthropic(api_key=api_key)
        
        # Stream the response
        full_response = ""
        
        with client.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        ) as stream:
            for text in stream.text_stream:
                full_response += text
                placeholder.markdown(full_response + "▌")
        
        return full_response
        
    except Exception as e:
        return f"⚠️ Error calling Claude API: {str(e)}\n\nPlease check your API key."


# For standalone testing
if __name__ == "__main__":
    st.set_page_config(
        page_title="Chat Test",
        page_icon="💬",
        layout="wide"
    )
    render_chat_page()
