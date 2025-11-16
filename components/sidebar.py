"""
Sidebar Component - Fixed for Advanced RAG
"""

import streamlit as st


def render_sidebar():
    """Render the main sidebar"""
    
    with st.sidebar:
        # Logo
        st.markdown("""
        <div style='text-align: center; padding-bottom: 2rem; border-bottom: 2px solid #d1dce5; margin-bottom: 2rem;'>
            <div style='width: 80px; height: 80px; margin: 0 auto 1rem; background: white; border: 4px solid #6d8aa0; border-radius: 16px; display: flex; align-items: center; justify-content: center; color: #6d8aa0; font-size: 2rem; font-weight: 700; box-shadow: 0 6px 20px rgba(109, 138, 160, 0.25);'>⚡</div>
            <div style='font-size: 1.5rem; font-weight: 700; color: #6d8aa0; margin-bottom: 0.25rem;'>XLR8</div>
            <div style='font-size: 0.85rem; color: #7d96a8; font-weight: 500;'>by HCMPACT</div>
            <div style='display: inline-block; background: rgba(109, 138, 160, 0.15); color: #6d8aa0; padding: 0.25rem 0.75rem; border-radius: 12px; font-size: 0.75rem; font-weight: 600; margin-top: 0.5rem;'>v3.0</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Project selector
        _render_project_selector()
        
        st.markdown("---")
        
        # AI/RAG status
        _render_ai_selector()
        
        st.markdown("---")
        
        # Status
        _render_status()


def _render_project_selector():
    """Render project selector"""
    st.markdown("### 📁 Project")
    
    if st.session_state.projects:
        project_names = list(st.session_state.projects.keys())
        current = st.session_state.current_project
        
        selected = st.selectbox(
            "Select Project",
            [""] + project_names,
            index=project_names.index(current) + 1 if current in project_names else 0,
            key="sidebar_project_selector"
        )
        
        if selected and selected != st.session_state.current_project:
            st.session_state.current_project = selected
            st.rerun()
        
        if current:
            project_data = st.session_state.projects[current]
            st.markdown(f"""
            <div style='font-size: 0.85rem; color: #6c757d; margin-top: 0.5rem;'>
                <strong>Type:</strong> {project_data.get('implementation_type', 'N/A')}<br>
                <strong>Customer:</strong> {project_data.get('customer_id', 'N/A')}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No projects yet")


def _render_ai_selector():
    """Render AI/RAG status and LLM provider selector"""
    st.markdown("### 🧠 AI System")
    
    # LLM Provider Selection
    llm_provider = st.selectbox(
        "🤖 AI Provider",
        ["Local LLM", "Claude API"],
        index=0 if st.session_state.get('llm_provider', 'local') == 'local' else 1,
        help="Choose between local DeepSeek or Claude API"
    )
    
    # Update session state
    new_provider = 'local' if llm_provider == "Local LLM" else 'claude'
    if st.session_state.get('llm_provider') != new_provider:
        st.session_state.llm_provider = new_provider
    
    # Show provider-specific config
    if llm_provider == "Local LLM":
        st.markdown("""
        <div style='font-size: 0.8rem; color: #28a745; padding: 0.5rem; background: rgba(40, 167, 69, 0.1); border-radius: 4px; margin-bottom: 0.5rem;'>
            ⚡ <strong>Local DeepSeek</strong><br>
            • Free, Private<br>
            • Good for detailed docs<br>
            • Model: deepseek-r1:7b
        </div>
        """, unsafe_allow_html=True)
    else:  # Claude API
        # API Key input
        api_key = st.text_input(
            "Claude API Key",
            type="password",
            value=st.session_state.get('claude_api_key', ''),
            help="Get your key at console.anthropic.com",
            key="claude_api_key_input"
        )
        
        # Save button
        if st.button("💾 Save API Key", type="primary"):
            st.session_state.claude_api_key = api_key
            st.success("API Key saved!")
            st.rerun()
        
        # Show status
        if st.session_state.get('claude_api_key'):
            st.markdown("""
            <div style='font-size: 0.8rem; color: #007bff; padding: 0.5rem; background: rgba(0, 123, 255, 0.1); border-radius: 4px; margin-top: 0.5rem;'>
                🧠 <strong>Claude API</strong><br>
                • Excellent quality<br>
                • ~$0.015 per response<br>
                • Model: Claude Sonnet 4
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("⚠️ API key required")
            st.markdown("[Get API key →](https://console.anthropic.com/)", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # RAG Status (existing code)
    # Check RAG handler
    rag_handler = st.session_state.get('rag_handler')
    rag_type = st.session_state.get('rag_type', 'none')
    
    if rag_handler:
        try:
            # Get stats - handle both basic and advanced formats
            rag_stats = rag_handler.get_stats()
            
            # Check if advanced format (nested dict)
            if isinstance(rag_stats, dict) and any(isinstance(v, dict) for v in rag_stats.values()):
                # Advanced RAG format - aggregate across strategies
                total_docs = sum(s.get('unique_documents', 0) for s in rag_stats.values() if isinstance(s, dict))
                total_chunks = sum(s.get('total_chunks', 0) for s in rag_stats.values() if isinstance(s, dict))
            else:
                # Basic RAG format
                total_docs = rag_stats.get('unique_documents', 0)
                total_chunks = rag_stats.get('total_chunks', 0)
            
            if total_docs > 0:
                st.success(f"✅ {total_docs} docs | {total_chunks} chunks")
                
                # Show RAG type
                if rag_type == 'advanced':
                    st.markdown("<small>🚀 Advanced RAG Active</small>", unsafe_allow_html=True)
                else:
                    st.markdown("<small>📚 RAG Active</small>", unsafe_allow_html=True)
            else:
                st.info("📋 No documents yet")
                st.markdown("<small>Upload in Knowledge Base</small>", unsafe_allow_html=True)
                
        except Exception as e:
            st.warning(f"⚠️ RAG status unavailable")
            st.markdown(f"<small>{str(e)[:50]}</small>", unsafe_allow_html=True)
    else:
        st.warning("⚠️ RAG not initialized")
    
    # LLM status
    llm_endpoint = st.session_state.get('llm_endpoint', 'Not configured')
    llm_model = st.session_state.get('llm_model', 'Not configured')
    
    with st.expander("🤖 LLM Config"):
        st.markdown(f"""
        <div style='font-size: 0.8rem;'>
            <strong>Endpoint:</strong> {llm_endpoint}<br>
            <strong>Model:</strong> {llm_model}
        </div>
        """, unsafe_allow_html=True)


def _render_status():
    """Render system status"""
    st.markdown("### ⚡ Status")
    
    # API status
    pro_configured = bool(st.session_state.api_credentials.get('pro'))
    wfm_configured = bool(st.session_state.api_credentials.get('wfm'))
    
    st.markdown(f"""
    <div style='font-size: 0.85rem; line-height: 1.8;'>
        <div>UKG Pro: {'✅' if pro_configured else '⚪'}</div>
        <div>UKG WFM: {'✅' if wfm_configured else '⚪'}</div>
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander("🔒 Security"):
        st.markdown("""
        <div style='font-size: 0.8rem; line-height: 1.6;'>
        ✓ Local Processing<br>
        ✓ Session-Only Storage<br>
        ✓ No External APIs<br>
        ✓ PII Protected
        </div>
        """, unsafe_allow_html=True)
