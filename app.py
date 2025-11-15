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
from pages.work.analysis import render_analysis_page
from pages.work.chat import render_chat_page
from pages.work.library import render_library_page
from pages.setup.projects import render_projects_page
from pages.setup.knowledge import render_knowledge_page
from pages.setup.connections import render_connections_page
from pages.qa.sit import render_sit_page
from pages.qa.uat import render_uat_page
from pages.qa.scenarios import render_scenarios_page
from pages.admin.users import render_users_page
from pages.admin.audit import render_audit_page
from pages.admin.settings import render_settings_page

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
    setup_subtab1, setup_subtab2, setup_subtab3 = st.tabs([
        "📁 Projects & Clients",
        "🧠 HCMPACT Knowledge Base",
        "🔌 Connections"
    ])
    
    with setup_subtab1:
        render_projects_page()
    
    with setup_subtab2:
        render_knowledge_page()
    
    with setup_subtab3:
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

# TAB 4: ADMIN (Administration)
with tab4:
    admin_subtab1, admin_subtab2, admin_subtab3 = st.tabs([
        "User Management",
        "Audit Logs",
        "System Settings"
    ])
    
    with admin_subtab1:
        render_users_page()
    
    with admin_subtab2:
        render_audit_page()
    
    with admin_subtab3:
        render_settings_page()

# Footer
st.markdown("---")
st.markdown(f"""
<div style="text-align: center; color: #6c757d; padding: 1rem;">
    <small>{AppConfig.APP_NAME} v{AppConfig.VERSION} | {AppConfig.TAGLINE}</small>
</div>
""", unsafe_allow_html=True)
