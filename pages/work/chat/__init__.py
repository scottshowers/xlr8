"""
Chat Interface Page - WITH EMPTY STATE ✨
RAG-powered chat with UKG knowledge base
Quick Win #4: Added empty state when no chat history
"""

import streamlit as st
from utils.rag.query_handler import query_knowledge_base
from utils.error_handler import handle_error
from utils.toast import show_toast


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
    
    # Stats
    total_messages = len(st.session_state.get('chat_history', []))
    knowledge_items = len(st.session_state.get('knowledge_base', []))
    
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
                        st.markdown(f"**Source {idx}:** {source.get('title', 'Unknown')}")
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
        # Check if knowledge base exists
        if not st.session_state.get('knowledge_base'):
            show_toast("⚠️ No Knowledge Base", "Please add documents to the knowledge base first", "warning")
            return
        
        try:
            # Add user message
            st.session_state.chat_history.append({
                'role': 'user',
                'content': user_question
            })
            
            # Show loading state
            with st.spinner("🔍 Searching knowledge base..."):
                # Check cache first
                cache_key = user_question.lower().strip()
                if cache_key in st.session_state.get('query_cache', {}):
                    result = st.session_state.query_cache[cache_key]
                    show_toast("⚡ Cached Response", "Retrieved from cache", "info")
                else:
                    # Query RAG system
                    result = query_knowledge_base(user_question)
                    
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
            
            show_toast("✅ Response Generated", "Answer added to chat", "success")
            st.rerun()
            
        except Exception as e:
            error_msg = handle_error(
                e,
                context="Chat Query",
                user_message="Failed to process your question. Please try again.",
                show_toast_notification=True
            )
            st.error(error_msg)


if __name__ == "__main__":
    st.title("Chat - Test")
    render_chat_page()
