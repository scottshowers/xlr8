"""
AI Assistant Chat Page
Advanced RAG-powered chat with hybrid retrieval and contextual compression
"""

import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
from typing import List, Dict, Any


def render_chat_page():
    """Render advanced chat interface with RAG"""
    
    st.markdown("## 💬 AI Assistant")
    
    st.markdown("""
    <div class='info-box'>
        <strong>Advanced RAG Chat:</strong> Ask questions about UKG implementation.
        Powered by Ollama LLM with semantic search, hybrid retrieval, and contextual compression.
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize chat history
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # Chat settings in sidebar
    with st.sidebar:
        st.markdown("### 🎛️ Chat Settings")
        
        retrieval_method = st.selectbox(
            "Retrieval Method",
            ["Hybrid Search", "Semantic Only", "MMR (Diverse)", "Keyword Only"],
            help="How to retrieve relevant documents"
        )
        
        num_sources = st.slider(
            "Number of Sources",
            min_value=1,
            max_value=10,
            value=5,
            help="How many documents to retrieve"
        )
        
        use_compression = st.checkbox(
            "Use Contextual Compression",
            value=True,
            help="Extract only relevant parts of documents"
        )
        
        show_sources = st.checkbox(
            "Show Sources",
            value=True,
            help="Display source documents"
        )
        
        if st.button("🗑️ Clear Chat History"):
            st.session_state.chat_history = []
            st.rerun()
    
    # Display chat history
    for message in st.session_state.chat_history:
        with st.chat_message(message['role']):
            st.markdown(message['content'])
            
            if show_sources and message.get('sources'):
                with st.expander(f"📚 {len(message['sources'])} Sources Used"):
                    for i, source in enumerate(message['sources'], 1):
                        st.markdown(f"**Source {i}:** {source['doc_name']}")
                        st.markdown(f"*Category:* {source['category']}")
                        st.markdown(f"*Relevance Score:* {source.get('score', 'N/A'):.3f}")
                        with st.expander(f"View excerpt"):
                            st.text(source['content'][:300] + "...")
    
    # Chat input
    if prompt := st.chat_input("Ask about UKG implementation, best practices, or technical questions..."):
        # Add user message
        st.session_state.chat_history.append({
            'role': 'user',
            'content': prompt
        })
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                # Get response with RAG
                response, sources = _generate_rag_response(
                    prompt=prompt,
                    retrieval_method=retrieval_method,
                    num_sources=num_sources,
                    use_compression=use_compression
                )
                
                st.markdown(response)
                
                if show_sources and sources:
                    with st.expander(f"📚 {len(sources)} Sources Used"):
                        for i, source in enumerate(sources, 1):
                            st.markdown(f"**Source {i}:** {source['doc_name']}")
                            st.markdown(f"*Category:* {source['category']}")
                            st.markdown(f"*Relevance Score:* {source.get('score', 'N/A'):.3f}")
                            with st.expander(f"View excerpt"):
                                st.text(source['content'][:300] + "...")
        
        # Add assistant message to history
        st.session_state.chat_history.append({
            'role': 'assistant',
            'content': response,
            'sources': sources
        })


def _generate_rag_response(prompt: str, 
                          retrieval_method: str,
                          num_sources: int,
                          use_compression: bool) -> tuple[str, List[Dict[str, Any]]]:
    """Generate response using RAG"""
    
    # Get RAG handler
    rag_handler = st.session_state.get('rag_handler')
    
    if not rag_handler:
        return "RAG system not initialized. Please upload knowledge base documents first.", []
    
    # Retrieve relevant documents
    if retrieval_method == "Hybrid Search":
        results = rag_handler.hybrid_search(
            query=prompt,
            n_results=num_sources,
            alpha=0.5,
            strategy='semantic'
        )
    elif retrieval_method == "MMR (Diverse)":
        results = rag_handler.mmr_search(
            query=prompt,
            n_results=num_sources,
            lambda_param=0.5,
            strategy='semantic'
        )
    elif retrieval_method == "Semantic Only":
        results = rag_handler.hybrid_search(
            query=prompt,
            n_results=num_sources,
            alpha=1.0,  # Pure semantic
            strategy='semantic'
        )
    else:  # Keyword Only
        results = rag_handler.hybrid_search(
            query=prompt,
            n_results=num_sources,
            alpha=0.0,  # Pure keyword
            strategy='semantic'
        )
    
    if not results:
        return "I don't have enough information in my knowledge base to answer that question. Please upload relevant documents first.", []
    
    # Apply contextual compression if enabled
    if use_compression:
        results = rag_handler.contextual_compression(
            query=prompt,
            retrieved_docs=results,
            compression_ratio=0.5
        )
    
    # Build context from results
    context = "\n\n".join([
        f"[Source: {r['metadata'].get('doc_name', 'Unknown')}]\n{r['content']}"
        for r in results
    ])
    
    # Build prompt
    system_prompt = """You are an expert UKG implementation consultant with deep knowledge of UKG Pro and WFM.
Use the provided context from HCMPACT's knowledge base to answer questions accurately.
If the context doesn't contain enough information, say so clearly.
Always cite which sources you're using when making claims."""
    
    full_prompt = f"""{system_prompt}

CONTEXT FROM KNOWLEDGE BASE:
{context}

USER QUESTION: {prompt}

ANSWER:"""
    
    # Call LLM
    response = _call_llm(full_prompt)
    
    # Format sources for display
    sources = []
    for result in results:
        sources.append({
            'doc_name': result['metadata'].get('doc_name', 'Unknown'),
            'category': result['metadata'].get('category', 'Unknown'),
            'content': result['content'],
            'score': result.get('score', result.get('distance', 0))
        })
    
    return response, sources


def _call_llm(prompt: str) -> str:
    """Call Ollama LLM"""
    
    llm_endpoint = st.session_state.get('llm_endpoint', 'http://localhost:11435')
    llm_model = st.session_state.get('llm_model', 'llama3.2:latest')
    llm_username = st.session_state.get('llm_username', 'xlr8')
    llm_password = st.session_state.get('llm_password', 'Argyle76226#')
    
    try:
        url = f"{llm_endpoint}/api/generate"
        
        payload = {
            "model": llm_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "top_k": 40
            }
        }
        
        auth = HTTPBasicAuth(llm_username, llm_password)
        
        response = requests.post(url, json=payload, auth=auth, timeout=120)
        response.raise_for_status()
        
        result = response.json()
        return result.get('response', 'No response generated')
        
    except Exception as e:
        return f"Error generating response: {str(e)}"


if __name__ == "__main__":
    st.title("Chat Page - Test")
    render_chat_page()
