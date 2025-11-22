"""
XLR8 by HCMPACT - Main Application Entry Point
Version: 3.0 - Modular Architecture


This file is INTENTIONALLY MINIMAL - it only handles:
1. Page configuration
2. Session state initialization
3. Routing to page modules

DO NOT add business logic here - put it in appropriate modules!
"""

import streamlit as st
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import AppConfig
from components.sidebar import render_sidebar
from utils.data.session import initialize_session_state

# Page imports
from pages.work.analysis_engine import render_analysis_page
from pages.work.chat import render_chat_page
from pages.work.library import render_library_page
from pages.setup.projects import render_projects_page
from pages.setup.knowledge import render_knowledge_page
from pages.setup.manage import render_manage_page
from pages.setup.connections import render_connections_page
from pages.qa.sit import render_sit_page
from pages.qa.uat import render_uat_page
from pages.qa.scenarios import render_scenarios_page
from pages.admin.analysis_questions import render_analysis_questions
from pages.admin.users import render_users_page
from pages.admin.audit import render_audit_page
from pages.admin.settings import render_settings_page
from pages.admin.global_knowledge import render_global_knowledge_page

# Page configuration
st.set_page_config(
    page_title=AppConfig.APP_NAME,
    page_icon=AppConfig.APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
initialize_session_state()

# Apply custom CSS
st.markdown(AppConfig.CUSTOM_CSS, unsafe_allow_html=True)

# Render sidebar (always visible)
render_sidebar()

# WELCOME DASHBOARD - COMPACT & PROFESSIONAL
st.markdown("""
<div style='background: linear-gradient(135deg, #8ca6be 0%, #6d8aa0 100%); padding: 0.75rem; border-radius: 12px; margin-bottom: 1.5rem; box-shadow: 0 4px 16px rgba(140, 166, 190, 0.25);'>
    <div style='text-align: center;'>
        <h1 style='color: white; margin: 0 0 0.25rem 0; font-size: 1.8rem; font-weight: 700;'>⚡ XLR8 LFG Platform</h1>
        <p style='color: rgba(255,255,255,0.95); font-size: 1rem; margin: 0;'>Implementation Accelerator</p>
    </div>
</div>
""", unsafe_allow_html=True)

# Quick Stats Dashboard
if st.session_state.get('projects') or st.session_state.get('knowledge_base'):
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        project_count = len(st.session_state.get('projects', {}))
        st.markdown(f"""
        <div style='background: white; padding: 1.5rem; border-radius: 12px; border: 2px solid #e8eef3; box-shadow: 0 4px 12px rgba(0,0,0,0.08); text-align: center;'>
            <div style='font-size: 2.5rem; margin-bottom: 0.5rem;'>📁</div>
            <div style='font-size: 2rem; font-weight: 700; color: #6d8aa0;'>{project_count}</div>
            <div style='color: #7d96a8; font-size: 0.9rem; font-weight: 500;'>Projects</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        kb_count = len(st.session_state.get('knowledge_base', []))
        st.markdown(f"""
        <div style='background: white; padding: 1.5rem; border-radius: 12px; border: 2px solid #e3f2fd; box-shadow: 0 4px 12px rgba(0,0,0,0.08); text-align: center;'>
            <div style='font-size: 2.5rem; margin-bottom: 0.5rem;'>📚</div>
            <div style='font-size: 2rem; font-weight: 700; color: #2196F3;'>{kb_count}</div>
            <div style='color: #7d96a8; font-size: 0.9rem; font-weight: 500;'>LLM Documents</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        active_project = st.session_state.get('current_project')
        st.markdown(f"""
        <div style='background: white; padding: 1.5rem; border-radius: 12px; border: 2px solid #e8f5e9; box-shadow: 0 4px 12px rgba(0,0,0,0.08); text-align: center;'>
            <div style='font-size: 2.5rem; margin-bottom: 0.5rem;'>{'📌' if active_project else '⚪'}</div>
            <div style='font-size: 1.2rem; font-weight: 600; color: {'#28a745' if active_project else '#6c757d'};'>{'Active' if active_project else 'None'}</div>
            <div style='color: #7d96a8; font-size: 0.9rem; font-weight: 500;'>Active Project</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        llm_provider = st.session_state.get('llm_provider', 'local')
        provider_name = 'Local LLM' if llm_provider == 'local' else 'Claude API'
        st.markdown(f"""
        <div style='background: white; padding: 1.5rem; border-radius: 12px; border: 2px solid #f3e5f5; box-shadow: 0 4px 12px rgba(0,0,0,0.08); text-align: center;'>
            <div style='font-size: 2.5rem; margin-bottom: 0.5rem;'>🤖</div>
            <div style='font-size: 1.2rem; font-weight: 600; color: #8ca6be;'>{provider_name.split()[0]}</div>
            <div style='color: #7d96a8; font-size: 0.9rem; font-weight: 500;'>AI Provider</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<div style='margin-bottom: 2rem;'></div>", unsafe_allow_html=True)

# Main content area with tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "🚀 WORK",
    "⚙️ SETUP", 
    "🧪 QA",
    "👤 ADMIN"
])

# TAB 1: WORK (Primary daily use)
with tab1:
    work_subtab1, work_subtab2, work_subtab3 = st.tabs([
        "📊 Analysis & Templates",
        "💬 AI Assistant",
        "📁 Document Library"
    ])
    
    with work_subtab1:
        render_analysis_page()
    
    with work_subtab2:
        render_chat_page()
    
    with work_subtab3:
        render_library_page()

# TAB 2: SETUP (Configuration)
with tab2:
    setup_subtab1, setup_subtab2, setup_subtab3, setup_subtab4 = st.tabs([
        "📁 Projects & Clients",
        "🧠 HCMPACT LLM Seeding",
        "📊 Document Management",
        "🔌 Connections"
    ])
    
    with setup_subtab1:
        render_projects_page()
    
    with setup_subtab2:
        render_knowledge_page()
    
    with setup_subtab3:
        render_manage_page()
    
    with setup_subtab4:
        render_connections_page()

# TAB 3: QA (Testing)
with tab3:
    qa_subtab1, qa_subtab2, qa_subtab3 = st.tabs([
        "SIT Testing",
        "UAT Testing",
        "Test Scenarios"
    ])
    
    with qa_subtab1:
        render_sit_page()
    
    with qa_subtab2:
        render_uat_page()
    
    with qa_subtab3:
        render_scenarios_page()

# TAB 4: ADMIN (Administration) - NOW WITH 5 TABS
with tab4:
    admin_subtab1, admin_subtab2, admin_subtab3, admin_subtab4, admin_subtab5 = st.tabs([
        "📋 Analysis Questions",
        "🌐 Global Knowledge",
        "👥 User Management",
        "📊 Audit Logs",
        "⚙️ System Settings"
    ])
    
    with admin_subtab1:
        render_analysis_questions()
    
    with admin_subtab2:
        render_global_knowledge_page()
    
    with admin_subtab3:
        render_users_page()
    
    with admin_subtab4:
        render_audit_page()
    
    with admin_subtab5:
        render_settings_page()

# Footer - PROFESSIONAL & COMPACT
st.markdown("---")
st.markdown(f"""
<div style='background: linear-gradient(135deg, #f5f7f9 0%, #e8eef3 100%); padding: 1rem; border-radius: 12px; text-align: center; margin-top: 1.5rem; border: 2px solid rgba(109, 138, 160, 0.15);'>
    <div style='display: flex; align-items: center; justify-content: center; gap: 1rem; flex-wrap: wrap;'>
        <div style='color: #6d8aa0; font-weight: 700; font-size: 1rem;'>⚡ {AppConfig.APP_NAME} v{AppConfig.VERSION}</div>
        <div style='color: #7d96a8;'>|</div>
        <div style='color: #7d96a8; font-weight: 500;'>{AppConfig.TAGLINE}</div>
    </div>
</div>
""", unsafe_allow_html=True)
