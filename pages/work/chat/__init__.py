"""
Chat Interface Page - FIXED + WITH EMPTY STATE ✨
RAG-powered chat with UKG knowledge base
Quick Win #4: Added empty state when no chat history
"""

import streamlit as st
import requests
from requests.auth import HTTPBasicAuth


def render_chat_page():
    """Render chat interface page with RAG and empty state"""
    
    st.markdown("## 💬 Chat with Knowledge Base")
    
    st.markdown("""
    <div class='info-box'>
        <strong>AI-Powered Chat:</strong> Ask questions about UKG implementation and get answers
        from your knowledge base using advanced RAG (Retrieval-Augmented Generation).
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'query_cache' not in st.session_state:
        st.session_state.query_cache = {}
    
    # Get RAG handler
    rag_handler = st.session_state.get('rag_handler')
    
    # Stats
    total_messages = len(st.session_state.get('chat_history', []))
    
    # Count knowledge items from RAG if available
    knowledge_items = 0
    if rag_handler:
        try:
            stats = rag_handler.get_stats()
            if isinstance(stats, dict):
                # Count across all strategies
                knowledge_items = sum(s.get('unique_documents', 0) for s in stats.values() if isinstance(s, dict))
                if knowledge_items == 0:
                    knowledge_items = stats.get('unique_documents', 0)
        except:
            knowledge_items = 0
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("💬 Messages", total_messages)
    with col2:
        st.metric("📚 Knowledge Items", knowledge_items)
    with col3:
        cached_queries = len(st.session_state.get('query_cache', {}))
        st.metric("⚡ Cached Queries", cached_queries)
    
    st.markdown("---")
    
    # Clear chat button
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_history = []
            st.session_state.query_cache = {}
            st.rerun()
    
    # EMPTY STATE ✨
    if not st.session_state.get('chat_history'):
        st.markdown("""
        <div style='text-align: center; padding: 3rem 1rem; background: linear-gradient(135deg, #f5f7f9 0%, #e8eef3 100%); border-radius: 16px; border: 2px dashed #8ca6be; margin: 2rem 0;'>
            <div style='font-size: 4rem; margin-bottom: 1rem;'>💬</div>
            <h2 style='color: #6d8aa0; margin-bottom: 1rem;'>Start a Conversation</h2>
            <p style='color: #7d96a8; font-size: 1.1rem; max-width: 500px; margin: 0 auto 2rem;'>
                Ask questions about UKG implementation and I'll search the knowledge base for relevant information
            </p>
            <div style='background: white; padding: 1.5rem; border-radius: 12px; max-width: 450px; margin: 0 auto; box-shadow: 0 4px 12px rgba(0,0,0,0.08);'>
                <h3 style='color: #6d8aa0; margin-bottom: 1rem; font-size: 1.1rem;'>💡 Example Questions</h3>
                <div style='text-align: left; color: #6c757d; line-height: 2;'>
                    • "How do I configure pay codes?"<br>
                    • "What are best practices for time entry?"<br>
                    • "How should I set up accruals?"<br>
                    • "What's the approval workflow process?"<br>
                    • "How do I handle overtime rules?"
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Display chat history
    for message in st.session_state.get('chat_history', []):
        role = message.get('role', 'user')
        content = message.get('content', '')
        
        if role == 'user':
            st.markdown(f"""
            <div style='background: #e8f4f8; padding: 1rem; border-radius: 8px; margin: 0.5rem 0;'>
                <strong style='color: #6d8aa0;'>👤 You:</strong><br>
                {content}
            </div>
            """, unsafe_allow_html=True)
        else:
            sources = message.get('sources', [])
            st.markdown(f"""
            <div style='background: #f8f9fa; padding: 1rem; border-radius: 8px; margin: 0.5rem 0; border-left: 4px solid #8ca6be;'>
                <strong style='color: #6d8aa0;'>🤖 Assistant:</strong><br>
                {content}
            </div>
            """, unsafe_allow_html=True)
            
            if sources:
                with st.expander(f"📚 View {len(sources)} Sources"):
                    for idx, source in enumerate(sources, 1):
                        st.markdown(f"**Source {idx}:** {source.get('doc_name', 'Unknown')}")
                        st.markdown(f"_{source.get('content', '')[:200]}..._")
                        st.markdown("---")
    
    # Chat input
    st.markdown("---")
    
    with st.form(key="chat_form", clear_on_submit=True):
        user_question = st.text_area(
            "Ask a question",
            placeholder="e.g., How do I configure pay codes in UKG Pro?",
            height=100,
            key="chat_input"
        )
        
        col1, col2 = st.columns([5, 1])
        with col2:
            submit_button = st.form_submit_button("Send 💬", use_container_width=True)
    
    if submit_button and user_question:
        # Check if RAG handler exists
        if not rag_handler:
            st.error("⚠️ Knowledge base not initialized. Please check system configuration.")
            return
        
        # Check if knowledge base has documents
        if knowledge_items == 0:
            st.warning("⚠️ No documents in knowledge base. Please add documents in the Knowledge Base tab first.")
            return
        
        try:
            # Add user message
            st.session_state.chat_history.append({
                'role': 'user',
                'content': user_question
            })
            
            # Show loading state
            with st.spinner("🔍 Searching knowledge base and generating response..."):
                # Check cache first
                cache_key = user_question.lower().strip()
                if cache_key in st.session_state.get('query_cache', {}):
                    result = st.session_state.query_cache[cache_key]
                    st.info("⚡ Retrieved from cache")
                else:
                    # Query RAG system
                    result = _query_knowledge_base(user_question, rag_handler)
                    
                    # Cache the result
                    if 'query_cache' not in st.session_state:
                        st.session_state.query_cache = {}
                    st.session_state.query_cache[cache_key] = result
            
            # Add assistant response
            st.session_state.chat_history.append({
                'role': 'assistant',
                'content': result.get('answer', 'No answer generated'),
                'sources': result.get('sources', [])
            })
            
            st.success("✅ Response generated!")
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            st.markdown("""
            <div style='background: #fff3cd; padding: 1rem; border-radius: 8px; border-left: 4px solid #ffc107; margin-top: 1rem;'>
                <strong style='color: #856404;'>💡 Troubleshooting Tips:</strong><br>
                <span style='color: #856404; font-size: 0.9rem;'>
                • Check if LLM service is running<br>
                • Verify knowledge base has documents<br>
                • Try a simpler question<br>
                • Check Railway logs for detailed errors
                </span>
            </div>
            """, unsafe_allow_html=True)


def _query_knowledge_base(query: str, rag_handler) -> dict:
    """
    Query the knowledge base and generate an answer using LLM
    
    Args:
        query: User's question
        rag_handler: RAG handler instance
        
    Returns:
        Dictionary with answer and sources
    """
    
    # Get LLM config
    llm_endpoint = st.session_state.get('llm_endpoint', 'http://localhost:11435')
    llm_model = st.session_state.get('llm_model', 'llama3.2:latest')
    llm_username = st.session_state.get('llm_username', 'xlr8')
    llm_password = st.session_state.get('llm_password', 'Argyle76226#')
    
    # Check for Claude API preference
    llm_provider = st.session_state.get('llm_provider', 'local')
    
    try:
        # Search knowledge base
        search_results = rag_handler.search(query, n_results=5)
        
        if not search_results:
            return {
                'answer': "I couldn't find relevant information in the knowledge base. Please try rephrasing your question or add more documents to the knowledge base.",
                'sources': []
            }
        
        # Build context from search results
        context = "\n\n".join([
            f"[{r['metadata'].get('doc_name', 'Unknown')}]: {r['content']}"
            for r in search_results
        ])
        
        # Build prompt
        prompt = f"""You are an expert UKG implementation consultant. Answer the user's question using ONLY the provided context from HCMPACT standards and documentation.

CONTEXT FROM KNOWLEDGE BASE:
{context}

USER QUESTION:
{query}

INSTRUCTIONS:
- Answer based ONLY on the context provided above
- Be specific and reference the source documents when possible
- If the context doesn't contain enough information, say so
- Provide actionable guidance where applicable
- Keep the answer concise but complete

ANSWER:"""
        
        # Generate answer using LLM
        if llm_provider == 'claude' and st.session_state.get('claude_api_key'):
            # Use Claude API
            answer = _call_claude_api(prompt, st.session_state.get('claude_api_key'))
        else:
            # Use local LLM (Ollama)
            answer = _call_local_llm(prompt, llm_endpoint, llm_model, llm_username, llm_password)
        
        return {
            'answer': answer,
            'sources': search_results
        }
        
    except Exception as e:
        raise Exception(f"Knowledge base query failed: {str(e)}")


def _call_local_llm(prompt: str, endpoint: str, model: str, username: str, password: str) -> str:
    """Call local Ollama LLM"""
    
    try:
        url = f"{endpoint}/api/generate"
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        
        auth = HTTPBasicAuth(username, password)
        response = requests.post(url, json=payload, auth=auth, timeout=120)
        response.raise_for_status()
        
        result = response.json()
        return result.get('response', 'No response from LLM')
        
    except Exception as e:
        raise Exception(f"Local LLM error: {str(e)}")


def _call_claude_api(prompt: str, api_key: str) -> str:
    """Call Claude API"""
    
    try:
        import anthropic
        
        client = anthropic.Anthropic(api_key=api_key)
        
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return message.content[0].text
        
    except Exception as e:
        # Fall back to local LLM if Claude API fails
        st.warning(f"Claude API failed ({str(e)}), falling back to local LLM...")
        llm_endpoint = st.session_state.get('llm_endpoint', 'http://localhost:11435')
        llm_model = st.session_state.get('llm_model', 'llama3.2:latest')
        llm_username = st.session_state.get('llm_username', 'xlr8')
        llm_password = st.session_state.get('llm_password', 'Argyle76226#')
        return _call_local_llm(prompt, llm_endpoint, llm_model, llm_username, llm_password)


if __name__ == "__main__":
    st.title("Chat - Test")
    render_chat_page()
