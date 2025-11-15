"""
Sidebar Component
Always-visible sidebar with project info, AI status, and quick stats

Owner: UI Team
Dependencies: streamlit, config, session
"""

import streamlit as st
from config import AppConfig
from utils.data.session import get_current_project, get_project_data


def render_sidebar():
    """Render the main sidebar"""
    
    with st.sidebar:
        # Logo and branding
        st.markdown("""
        <div style='text-align: center; padding-bottom: 2rem; border-bottom: 2px solid #d1dce5; margin-bottom: 2rem;'>
            <div style='width: 80px; height: 80px; margin: 0 auto 1rem; background: white; border: 4px solid #6d8aa0; border-radius: 16px; display: flex; align-items: center; justify-content: center; color: #6d8aa0; font-size: 2rem; font-weight: 700; box-shadow: 0 6px 20px rgba(109, 138, 160, 0.25);'>⚡</div>
            <div style='font-size: 1.5rem; font-weight: 700; color: #6d8aa0; margin-bottom: 0.25rem;'>XLR8</div>
            <div style='font-size: 0.85rem; color: #7d96a8; font-weight: 500;'>by HCMPACT</div>
            <div style='display: inline-block; background: rgba(109, 138, 160, 0.15); color: #6d8aa0; padding: 0.25rem 0.75rem; border-radius: 12px; font-size: 0.75rem; font-weight: 600; margin-top: 0.5rem;'>v3.0</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Active Project Section
        _render_project_section()
        
        st.markdown("---")
        
        # AI Model Selector
        _render_ai_selector()
        
        st.markdown("---")
        
        # Quick Stats
        _render_quick_stats()
        
        st.markdown("---")
        
        # Quick Links
        _render_quick_links()


def _render_project_section():
    """Render project selection and info"""
    st.markdown("### 📁 Active Project")
    
    current_project = get_current_project()
    
    if st.session_state.projects:
        project_names = list(st.session_state.projects.keys())
        
        # Current index
        current_idx = 0
        if current_project and current_project in project_names:
            current_idx = project_names.index(current_project) + 1
        
        selected = st.selectbox(
            "Select Project",
            ["None"] + project_names,
            index=current_idx,
            key="sidebar_project_selector"
        )
        
        if selected != "None":
            st.session_state.current_project = selected
            project_data = get_project_data(selected)
            
            if project_data:
                st.markdown(f"""
                <div class='info-box' style='font-size: 0.85rem; margin-top: 0.5rem;'>
                    <strong>📋 {selected}</strong><br>
                    <small>Customer: {project_data.get('customer_id', 'N/A')}</small><br>
                    <small>Type: {project_data.get('implementation_type', 'N/A')}</small><br>
                    <small>Created: {project_data.get('created_date', 'N/A')}</small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.session_state.current_project = None
            st.info("No project selected")
    else:
        st.info("No projects created yet")
        st.caption("Create one in Setup → Projects")


def _render_ai_selector():
    """Render AI model selector"""
    st.markdown("### 🤖 AI Model")
    
    # Model choice
    model_options = list(AppConfig.LLM_MODELS.keys())
    model_display = [AppConfig.LLM_MODELS[m]["name"] for m in model_options]
    
    current_model = st.session_state.llm_model
    current_idx = model_options.index(current_model) if current_model in model_options else 0
    
    selected_display = st.radio(
        "Choose Speed",
        model_display,
        index=current_idx,
        key="sidebar_model_selector"
    )
    
    # Map back to actual model name
    selected_model = model_options[model_display.index(selected_display)]
    
    if selected_model != st.session_state.llm_model:
        st.session_state.llm_model = selected_model
        st.rerun()
    
    # Show model info
    model_info = AppConfig.LLM_MODELS[selected_model]
    st.markdown(f"""
    <div class='success-box' style='font-size: 0.75rem; margin-top: 0.5rem; padding: 0.5rem;'>
        <strong>{model_info['description']}</strong><br>
        <small>RAM: {model_info['ram']} • Speed: {model_info['speed']}</small>
    </div>
    """, unsafe_allow_html=True)
    
    # RAG status
    rag_stats = st.session_state.rag_handler.get_stats()
    if rag_stats['unique_documents'] > 0:
        st.markdown(f"""
        <div style='background-color: rgba(76, 175, 80, 0.1); padding: 0.5rem; border-radius: 6px; margin-top: 0.5rem; font-size: 0.75rem;'>
            🧠 <strong>RAG Active</strong><br>
            <small>{rag_stats['unique_documents']} docs • {rag_stats['total_chunks']} chunks</small>
        </div>
        """, unsafe_allow_html=True)


def _render_quick_stats():
    """Render quick statistics"""
    st.markdown("### 📊 Quick Stats")
    
    # Project count
    project_count = len(st.session_state.projects)
    st.metric("Projects", project_count)
    
    # Document count
    doc_count = len(st.session_state.get('doc_library', []))
    st.metric("Documents", doc_count)
    
    # RAG documents
    rag_stats = st.session_state.rag_handler.get_stats()
    st.metric("HCMPACT Docs", rag_stats['unique_documents'])


def _render_quick_links():
    """Render quick action links"""
    st.markdown("### 🔗 Quick Actions")
    
    if st.button("📤 Upload Document", use_container_width=True):
        # Set flag to jump to upload (handled by main app)
        st.session_state.quick_action = 'upload'
        st.rerun()
    
    if st.button("🤖 Run Analysis", use_container_width=True):
        st.session_state.quick_action = 'analyze'
        st.rerun()
    
    if st.button("💬 Open Chat", use_container_width=True):
        st.session_state.quick_action = 'chat'
        st.rerun()
