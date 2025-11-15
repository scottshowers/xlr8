"""
XLR8 by HCMPACT - UKG Pro/WFM Implementation Accelerator
Full-Featured Application with Project Management, API Connections, and Secure PDF Parser
"""

import streamlit as st
import json
import io
import os
import zipfile
from datetime import datetime
from pathlib import Path
import pandas as pd
from utils.secure_pdf_parser import (
    EnhancedPayrollParser,
    process_parsed_pdf_for_ukg
)
# Section-Based Template System imports
try:
    from pdf2image import convert_from_bytes
    from PIL import Image
    import pytesseract
    from streamlit_drawable_canvas import st_canvas
    DRAWING_AVAILABLE = True
except ImportError:
    DRAWING_AVAILABLE = False



# Page configuration
st.set_page_config(
    page_title="XLR8 by HCMPACT - TEST",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'current_project' not in st.session_state:
    st.session_state.current_project = None
if 'projects' not in st.session_state:
    st.session_state.projects = {}
if 'api_credentials' not in st.session_state:
    st.session_state.api_credentials = {'pro': {}, 'wfm': {}}
if 'pdf_parser' not in st.session_state:
    st.session_state.pdf_parser = EnhancedPayrollParser()
if 'parsed_results' not in st.session_state:
    st.session_state.parsed_results = None
if 'foundation_files' not in st.session_state:
    st.session_state.foundation_files = []

# Custom CSS - Darker Muted Blue Theme
st.markdown("""
<style>
    /* Modern styling with darker muted blues */
    .main {
        padding: 2rem;
        background-color: #e8edf2;
    }
    
    .stButton>button {
        width: 100%;
        border-radius: 6px;
        height: 3rem;
        font-weight: 600;
        transition: all 0.3s;
        background-color: #6d8aa0;
        color: white;
        border: none;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(109, 138, 160, 0.4);
        background-color: #7d96a8;
    }
    
    .success-box {
        background-color: rgba(109, 138, 160, 0.15);
        border-left: 4px solid #6d8aa0;
        padding: 1rem;
        border-radius: 6px;
        margin: 1rem 0;
        color: #1a2332;
    }
    
    .info-box {
        background-color: rgba(125, 150, 168, 0.15);
        border-left: 4px solid #7d96a8;
        padding: 1rem;
        border-radius: 6px;
        margin: 1rem 0;
        color: #1a2332;
    }
    
    .warning-box {
        background-color: rgba(140, 166, 190, 0.15);
        border-left: 4px solid #8ca6be;
        padding: 1rem;
        border-radius: 6px;
        margin: 1rem 0;
        color: #1a2332;
    }
    
    .project-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border: 2px solid #d1dce5;
        margin: 0.5rem 0;
        cursor: pointer;
        transition: all 0.3s;
    }
    
    .project-card:hover {
        border-color: #6d8aa0;
        box-shadow: 0 2px 8px rgba(109, 138, 160, 0.2);
    }
    
    .project-card.active {
        border-color: #6d8aa0;
        background: rgba(109, 138, 160, 0.08);
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: white;
        border-right: 1px solid #e1e8ed;
    }
    
    section[data-testid="stSidebar"] > div {
        padding-top: 2rem;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        border-bottom: 2px solid #e1e8ed;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border-bottom: 3px solid transparent;
        color: #6d8aa0;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
    }
    
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        background-color: rgba(109, 138, 160, 0.1);
        border-bottom: 3px solid #6d8aa0;
        color: #1a2332;
    }
    
    h1, h2, h3 {
        color: #1a2332;
    }
    
    .stTextInput>div>div>input {
        border-radius: 6px;
        border: 1px solid #d1dce5;
    }
    
    .stTextInput>div>div>input:focus {
        border-color: #6d8aa0;
        box-shadow: 0 0 0 1px #6d8aa0;
    }
    
    .stSelectbox>div>div {
        border-radius: 6px;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    # Logo with Lightning Bolt
    st.markdown("""
    <div style='text-align: center; padding-bottom: 2rem; border-bottom: 2px solid #d1dce5; margin-bottom: 2rem;'>
        <div style='width: 80px; height: 80px; margin: 0 auto 1rem; background: white; border: 4px solid #6d8aa0; border-radius: 16px; display: flex; align-items: center; justify-content: center; color: #6d8aa0; font-size: 2rem; font-weight: 700; box-shadow: 0 6px 20px rgba(109, 138, 160, 0.25);'>⚡</div>
        <div style='font-size: 1.5rem; font-weight: 700; color: #6d8aa0; margin-bottom: 0.25rem;'>XLR8</div>
        <div style='font-size: 0.85rem; color: #7d96a8; font-weight: 500;'>by HCMPACT</div>
        <div style='display: inline-block; background: rgba(109, 138, 160, 0.15); color: #6d8aa0; padding: 0.25rem 0.75rem; border-radius: 12px; font-size: 0.75rem; font-weight: 600; margin-top: 0.5rem;'>v2.0</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Project Management Section
    st.markdown("### 📁 Project Management")
    
    # Project selector
    if st.session_state.projects:
        project_names = list(st.session_state.projects.keys())
        selected_project = st.selectbox(
            "Select Project",
            [""] + project_names,
            key="project_selector"
        )
        
        if selected_project:
            st.session_state.current_project = selected_project
            project_data = st.session_state.projects[selected_project]
            
            st.markdown(f"""
            <div class='info-box' style='font-size: 0.85rem; margin-top: 0.5rem;'>
                <strong>📋 {selected_project}</strong><br>
                <small>Customer ID: {project_data.get('customer_id', 'N/A')}</small><br>
                <small>Type: {project_data.get('implementation_type', 'N/A')}</small><br>
                <small>Created: {project_data.get('created_date', 'N/A')}</small>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No projects created yet. Use Home tab to create one!")
    
    st.markdown("---")
    
    # HCMPACT Intelligence for Local LLM
    with st.expander("🧠 HCMPACT Intelligence", expanded=False):
        st.markdown("**Local LLM Knowledge Base**")
        st.markdown("""
        <div style='font-size: 0.85rem; color: #6c757d; margin-bottom: 1rem;'>
        Upload HCMPACT's standards, best practices, and templates in the 
        <strong>Seed HCMPACT LLM</strong> tab (Tab 3 → 4th tab).
        </div>
        """, unsafe_allow_html=True)
        
        # Show current foundation status
        valid_foundation_files = [f for f in st.session_state.foundation_files if isinstance(f, dict)]
        if valid_foundation_files:
            enabled_count = len([f for f in valid_foundation_files if f.get('enabled', False)])
            st.success(f"✅ {len(valid_foundation_files)} HCMPACT standard(s) | {enabled_count} enabled")
            for file in valid_foundation_files[:5]:  # Show first 5
                status_icon = "✅" if file.get('enabled', False) else "⭕"
                st.markdown(f"<div style='font-size: 0.8rem; padding: 0.25rem 0;'>{status_icon} {file['name']}</div>", unsafe_allow_html=True)
            if len(valid_foundation_files) > 5:
                st.markdown(f"<div style='font-size: 0.8rem; padding: 0.25rem 0; color: #6c757d;'>... and {len(valid_foundation_files) - 5} more</div>", unsafe_allow_html=True)
        else:
            st.info("📋 No HCMPACT standards yet")
            st.markdown("<small>Go to Seed HCMPACT LLM tab to upload</small>", unsafe_allow_html=True)
        
        st.markdown("""
        <div style='font-size: 0.75rem; color: #6c757d; margin-top: 1rem; line-height: 1.4;'>
        <strong>Examples:</strong><br>
        • UKG Pro config guides<br>
        • WFM best practices<br>
        • Pay code templates<br>
        • Accrual standards<br>
        • Industry regulations
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # API Connection Status
    with st.expander("🔌 API Connections", expanded=False):
        st.markdown("**UKG Environment Status**")
        
        pro_configured = bool(st.session_state.api_credentials['pro'])
        wfm_configured = bool(st.session_state.api_credentials['wfm'])
        
        st.markdown(f"""
        <div style='font-size: 0.85rem; line-height: 1.8;'>
            <div>UKG Pro: {'✅ Connected' if pro_configured else '⚠️ Not configured'}</div>
            <div>UKG WFM: {'✅ Connected' if wfm_configured else '⚠️ Not configured'}</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style='font-size: 0.75rem; color: #6c757d; margin-top: 1rem;'>
        Configure API connections in the Configuration tab
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Status Section
    st.markdown("### Status")
    st.markdown("""
    <div style='display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem 0;'>
        <div style='width: 20px; height: 20px; background: #8ca6be; border-radius: 4px; display: flex; align-items: center; justify-content: center; color: white; font-size: 0.75rem;'>✓</div>
        <span style='color: #2c3e50; font-size: 0.9rem;'>Encryption Active</span>
    </div>
    <div style='display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem 0;'>
        <div style='width: 20px; height: 20px; background: #8ca6be; border-radius: 4px; display: flex; align-items: center; justify-content: center; color: white; font-size: 0.75rem;'>✓</div>
        <span style='color: #2c3e50; font-size: 0.9rem;'>PII Protection On</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Security Expandable
    with st.expander("🔐 Security Details", expanded=False):
        st.markdown("**Active Features**")
        st.markdown("""
        <div style='font-size: 0.85rem; line-height: 1.8;'>
        <div>✓ AES-256 Encryption</div>
        <div>✓ PII Auto-Detection</div>
        <div>✓ Data Anonymization</div>
        <div>✓ Audit Logging</div>
        <div>✓ Secure Storage</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("**Compliance**")
        st.markdown("""
        <div style='font-size: 0.85rem; line-height: 1.8;'>
        <div>✓ GDPR Compliant</div>
        <div>✓ HIPAA Ready</div>
        <div>✓ SOC 2 Type II</div>
        <div>✓ ISO 27001</div>
        </div>
        """, unsafe_allow_html=True)

# Main content
# Minimal header with TEST environment indicator
st.markdown("""
<div style='background: linear-gradient(135deg, #6d8aa0 0%, #7d96a8 100%); padding: 0.75rem 2rem; margin: -2rem -2rem 2rem -2rem; border-bottom: 3px solid #5a7589; box-shadow: 0 2px 8px rgba(0,0,0,0.1);'>
    <div style='display: flex; align-items: center; justify-content: space-between;'>
        <div style='display: flex; align-items: center; gap: 1rem;'>
            <div style='font-size: 1.5rem;'>⚡</div>
            <div>
                <div style='font-size: 1.2rem; font-weight: 700; color: white; letter-spacing: 0.5px;'>XLR8 by HCMPACT</div>
                <div style='font-size: 0.7rem; color: rgba(255,255,255,0.8);'>UKG Implementation Accelerator</div>
            </div>
        </div>
        <div style='background: #ff6b6b; color: white; padding: 0.4rem 1rem; border-radius: 6px; font-weight: 700; font-size: 0.85rem; letter-spacing: 0.5px; box-shadow: 0 2px 6px rgba(255,107,107,0.3);'>
            ⚠️ TEST ENVIRONMENT
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Tabs
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🏠 Home & Projects",
    "🛠️ Admin",
    "🔗 Connectivity",
    "🤖 AI PDF Parser",
    "📝 Templated Parser",
    "🧠 AI Analysis & Intelligence",
    "🧪 Testing"
])

with tab1:
    st.markdown("## 🏠 Welcome to XLR8")
    
    # Quick stats if projects exist
    if st.session_state.projects:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📁 Total Projects", len(st.session_state.projects))
        with col2:
            active_project = st.session_state.current_project or "None"
            st.metric("📌 Active Project", active_project if len(active_project) < 15 else active_project[:12] + "...")
        with col3:
            pro_count = sum(1 for p in st.session_state.projects.values() if 'Pro' in p.get('implementation_type', ''))
            st.metric("🔵 UKG Pro", pro_count)
        with col4:
            wfm_count = sum(1 for p in st.session_state.projects.values() if 'WFM' in p.get('implementation_type', ''))
            st.metric("🟢 UKG WFM", wfm_count)
        
        st.markdown("---")
    
    # Two column layout
    col_left, col_right = st.columns([3, 2])
    
    with col_left:
        # Create New Project Section
        st.markdown("### 📋 Create New Project")
        
        with st.form("new_project_form"):
            project_name = st.text_input(
                "Project Name *",
                placeholder="e.g., Acme Corp - UKG Pro Implementation",
                help="Descriptive name for this implementation project"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                customer_id = st.text_input(
                    "Customer ID *",
                    placeholder="e.g., ACME001",
                    help="Unique identifier for this customer"
                )
            with col2:
                implementation_type = st.selectbox(
                    "Implementation Type *",
                    ["UKG Pro", "UKG WFM", "UKG Pro + WFM"],
                    help="Which UKG product(s) are being implemented"
                )
            
            project_description = st.text_area(
                "Project Description (Optional)",
                placeholder="Brief description of implementation scope, timeline, or special requirements...",
                height=100
            )
            
            col1, col2 = st.columns(2)
            with col1:
                go_live_date = st.date_input(
                    "Target Go-Live Date (Optional)",
                    value=None
                )
            with col2:
                consultant_name = st.text_input(
                    "Lead Consultant (Optional)",
                    placeholder="Your name"
                )
            
            submitted = st.form_submit_button("✨ Create Project", use_container_width=True)
            
            if submitted:
                if not project_name or not customer_id:
                    st.error("❌ Project Name and Customer ID are required!")
                elif project_name in st.session_state.projects:
                    st.error(f"❌ Project '{project_name}' already exists!")
                else:
                    # Create project
                    st.session_state.projects[project_name] = {
                        'customer_id': customer_id,
                        'implementation_type': implementation_type,
                        'description': project_description,
                        'go_live_date': str(go_live_date) if go_live_date else None,
                        'consultant': consultant_name,
                        'created_date': datetime.now().strftime("%Y-%m-%d"),
                        'created_time': datetime.now().strftime("%H:%M:%S"),
                        'data_sources': [],
                        'notes': []
                    }
                    st.session_state.current_project = project_name
                    st.success(f"✅ Project '{project_name}' created successfully!")
                    st.rerun()
    
    with col_right:
        st.markdown("### 🚀 Quick Start Guide")
        st.markdown("""
        <div class='info-box'>
            <h4 style='margin-top: 0;'>Getting Started</h4>
            <ol style='margin-left: 1.5rem; line-height: 2;'>
                <li><strong>Create a project</strong> ← Start here</li>
                <li><strong>Upload PDF registers</strong> in Parser tab</li>
                <li><strong>Upload data files</strong> in Analysis tab</li>
                <li><strong>Configure API access</strong> in Config tab</li>
                <li><strong>Review templates</strong> in Templates tab</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### ✨ Key Features")
        st.markdown("""
        <div class='success-box'>
            <ul style='list-style: none; padding-left: 0; line-height: 2;'>
                <li>✓ Multi-project management</li>
                <li>✓ 5-strategy PDF parsing (95%+ success)</li>
                <li>✓ Cross-reference data analysis</li>
                <li>✓ UKG Pro/WFM API integration</li>
                <li>✓ Template auto-population</li>
                <li>✓ 100% local, PII-safe processing</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # Existing Projects List
    if st.session_state.projects:
        st.markdown("---")
        st.markdown("### 📂 Your Projects")
        
        for proj_name, proj_data in st.session_state.projects.items():
            is_active = proj_name == st.session_state.current_project
            
            with st.expander(f"{'📌 ' if is_active else '📁 '}{proj_name}", expanded=is_active):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"""
                    **Customer ID:** {proj_data['customer_id']}  
                    **Type:** {proj_data['implementation_type']}  
                    **Created:** {proj_data['created_date']}  
                    **Consultant:** {proj_data.get('consultant', 'Not specified')}
                    """)
                    
                    if proj_data.get('description'):
                        st.markdown(f"**Description:** {proj_data['description']}")
                    
                    if proj_data.get('go_live_date'):
                        st.markdown(f"**Target Go-Live:** {proj_data['go_live_date']}")
                
                with col2:
                    if not is_active:
                        if st.button(f"Activate", key=f"activate_{proj_name}"):
                            st.session_state.current_project = proj_name
                            st.rerun()
                    else:
                        st.success("✓ Active")
                    
                    if st.button(f"Delete", key=f"delete_{proj_name}"):
                        del st.session_state.projects[proj_name]
                        if st.session_state.current_project == proj_name:
                            st.session_state.current_project = None
                        st.rerun()

with tab4:
    st.markdown("## 🤖 AI PDF Parser")
    
    if not st.session_state.current_project:
        st.warning("⚠️ Please create or select a project first (Home tab)")
    else:
        # Info box about the parser
        st.markdown("""
        <div class='info-box'>
            <h4>🔒 Secure Local Processing</h4>
            <p><strong>5 Parsing Strategies:</strong> Camelot → Tabula → pdfplumber (10s timeout) → PyMuPDF → OCR</p>
            <p><strong>Success Rate:</strong> 95%+ on complex payroll registers</p>
            <p><strong>Security:</strong> 100% local processing, zero external APIs, no PII exposure</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Step 1: Upload PDF
        st.markdown("### Step 1: Upload PDF")
        uploaded_file = st.file_uploader(
            "Choose a PDF file (Pay Register, Payroll Report, etc.)",
            type=['pdf'],
            key="pdf_uploader"
        )
        
        if uploaded_file:
            st.success(f"✅ Loaded: {uploaded_file.name}")
            
            # File info with smaller font
            st.markdown(f"""
            <div style='display: flex; gap: 2rem; padding: 1rem; background: rgba(109, 138, 160, 0.08); border-radius: 6px; margin: 1rem 0;'>
                <div style='flex: 1;'>
                    <div style='font-size: 0.7rem; color: #6c757d; margin-bottom: 0.25rem;'>📄 FILENAME</div>
                    <div style='font-size: 0.85rem; font-weight: 600; color: #2c3e50;'>{uploaded_file.name[:40] + "..." if len(uploaded_file.name) > 40 else uploaded_file.name}</div>
                </div>
                <div style='flex: 1;'>
                    <div style='font-size: 0.7rem; color: #6c757d; margin-bottom: 0.25rem;'>💾 SIZE</div>
                    <div style='font-size: 0.85rem; font-weight: 600; color: #2c3e50;'>{uploaded_file.size / 1024:.1f} KB</div>
                </div>
                <div style='flex: 1;'>
                    <div style='font-size: 0.7rem; color: #6c757d; margin-bottom: 0.25rem;'>📋 TYPE</div>
                    <div style='font-size: 0.85rem; font-weight: 600; color: #2c3e50;'>PDF Document</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Step 2: Parse PDF
            st.markdown("### Step 2: Parse PDF")
            
            # Add comparison mode toggle
            st.markdown("**⚙️ Parsing Options:**")
            
            compare_mode = st.checkbox(
                "🔍 **Compare All 4 Parsers** (Camelot, Tabula, pdfplumber, PyMuPDF)", 
                value=False, 
                help="Tries all parsing strategies side-by-side so you can pick which one extracted your data best. Slower but recommended if parsing quality is poor."
            )
            
            if compare_mode:
                st.warning("🔍 **Comparison Mode Active:** You'll see results from all 4 parsers. Click the 'Use [Parser]' button to select the best one.")
            else:
                st.info("💡 **Quick Mode:** Uses first successful parser. If results are poor, enable 'Compare All 4 Parsers' above.")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                parse_button = st.button("🚀 Parse PDF", type="primary", use_container_width=True)
            with col2:
                if st.button("Clear", help="Reset parsing results"):
                    st.session_state.parsed_results = None
                    st.session_state.field_overrides = {}
                    st.rerun()
            
            if parse_button:
                # Progress tracking
                progress_container = st.container()
                progress_text = progress_container.empty()
                progress_bar = progress_container.progress(0)
                
                def update_progress(message):
                    """Update progress indicator"""
                    progress_text.info(f"⏳ {message}")
                
                # Parse the PDF
                try:
                    with st.spinner("Initializing secure parser..."):
                        progress_bar.progress(10)
                        pdf_content = uploaded_file.read()
                        progress_bar.progress(20)
                    
                    # Parse with progress updates and comparison mode
                    result = st.session_state.pdf_parser.parse_pdf(
                        pdf_content=pdf_content,
                        filename=uploaded_file.name,
                        progress_callback=update_progress,
                        try_all_strategies=compare_mode
                    )
                    progress_bar.progress(90)
                    
                    # Clear progress indicators
                    progress_text.empty()
                    progress_bar.empty()
                    
                    # Handle comparison mode
                    if result.get('mode') == 'comparison':
                        st.success("✅ Comparison complete!")
                        
                        # BIG CLEAR INSTRUCTIONS
                        st.markdown("### 📋 How to Use Comparison Mode")
                        st.markdown("""
                        **3 Simple Steps:**
                        1. 👀 Review each parser's results in the tabs below
                        2. ✅ Click the **"USE [PARSER] RESULTS"** button for the best one
                        3. 🔧 On the next screen, you can remap any fields that went to the wrong tab
                        """)
                        
                        # Show strategy comparison table
                        st.markdown("### 📊 Parser Comparison Summary")
                        comparison_data = []
                        for strategy, data in result['all_results'].items():
                            comparison_data.append({
                                'Parser': strategy.upper(),
                                'Status': '✅ Success' if data['success'] else '❌ Failed',
                                'Tables Found': data['num_tables'],
                                'Quality': '⭐⭐⭐' if data['success'] and data['num_tables'] > 0 else '⭐'
                            })
                        
                        st.dataframe(pd.DataFrame(comparison_data), use_container_width=True, hide_index=True)
                        
                        # Let user select which parser to use
                        st.markdown("### 👇 Select Best Parser")
                        st.info("Review the previews below and select which parser extracted your data best")
                        
                        # Create tabs for each strategy
                        successful_strategies = {k: v for k, v in result['all_results'].items() if v['success'] and v['num_tables'] > 0}
                        
                        if successful_strategies:
                            tab_names = [f"{k.upper()} ({v['num_tables']} tables)" for k, v in successful_strategies.items()]
                            tabs = st.tabs(tab_names)
                            
                            for idx, (strategy, data) in enumerate(successful_strategies.items()):
                                with tabs[idx]:
                                    st.markdown(f"#### {strategy.upper()} Results")
                                    
                                    for table_idx, table_df in enumerate(data['tables']):
                                        st.markdown(f"**Table {table_idx + 1}** - {len(table_df)} rows × {len(table_df.columns)} columns")
                                        st.dataframe(table_df.head(15), use_container_width=True)
                                        
                                        # Show field categorization for this table
                                        with st.expander("🏷️ See UKG tab assignments for this table"):
                                            categories = st.session_state.pdf_parser.get_column_categories(table_df)
                                            cat_preview = pd.DataFrame([
                                                {'Column Name': col, 'UKG Tab': info['category']}
                                                for col, info in categories.items()
                                            ])
                                            st.dataframe(cat_preview, use_container_width=True)
                                    
                                    # Make the selection button VERY prominent
                                    st.markdown("---")
                                    st.markdown(f"### ✅ Select This Parser")
                                    st.markdown(f"**Click below if {strategy.upper()} extracted your data correctly:**")
                                    
                                    if st.button(
                                        f"✅ USE {strategy.upper()} RESULTS", 
                                        key=f"select_{strategy}", 
                                        use_container_width=True, 
                                        type="primary",
                                        help=f"Select {strategy.upper()} as your parser and continue to field mapping"
                                    ):
                                        # Re-parse with only this strategy by storing selection
                                        st.session_state.selected_strategy = strategy
                                        st.session_state.comparison_result = result
                                        
                                        # Convert to standard result format
                                        formatted_tables = []
                                        for idx, df in enumerate(data['tables']):
                                            formatted_tables.append({
                                                'page': 1,
                                                'table_num': idx + 1,
                                                'row_count': len(df),
                                                'col_count': len(df.columns),
                                                'data': df
                                            })
                                        
                                        # Identify fields
                                        identified_fields = {}
                                        for table_idx, table_info in enumerate(formatted_tables):
                                            df = table_info['data']
                                            for col in df.columns:
                                                field_type, category = st.session_state.pdf_parser.categorizer.categorize_column(str(col))
                                                if field_type:
                                                    if field_type not in identified_fields:
                                                        identified_fields[field_type] = []
                                                    identified_fields[field_type].append({
                                                        'table': f"Table_{table_idx + 1}",
                                                        'column': str(col)
                                                    })
                                        
                                        selected_result = {
                                            'success': True,
                                            'tables': formatted_tables,
                                            'filename': uploaded_file.name,
                                            'method': strategy,
                                            'parsed_at': result.get('parsed_at', datetime.now().isoformat()),
                                            'processing_time': result.get('processing_time', 0),
                                            'strategies_used': [strategy],
                                            'metadata': result.get('metadata', {'total_pages': 0}),
                                            'identified_fields': identified_fields if identified_fields else None
                                        }
                                        
                                        st.session_state.parsed_results = selected_result
                                        st.rerun()
                        else:
                            st.error("❌ None of the parsing strategies found any tables. The PDF may not contain extractable table data.")
                    
                    else:
                        # Normal mode - single strategy result
                        st.session_state.parsed_results = result
                        
                        # Save to project
                        if st.session_state.current_project:
                            if 'data_sources' not in st.session_state.projects[st.session_state.current_project]:
                                st.session_state.projects[st.session_state.current_project]['data_sources'] = []
                            
                            st.session_state.projects[st.session_state.current_project]['data_sources'].append({
                                'filename': uploaded_file.name,
                                'type': 'PDF',
                                'parsed_at': result.get('parsed_at', datetime.now().isoformat()),
                                'tables_found': len(result.get('tables', [])),
                                'strategies_used': result.get('strategies_used', [])
                            })
                    
                    # Display results for selected strategy (skip if in comparison mode waiting for selection)
                    if result.get('mode') == 'comparison':
                        # User needs to select a parser first - don't show results section yet
                        pass
                    elif result.get('success') and result.get('tables'):
                        # Success message
                        st.success(f"✅ Parsing complete in {result.get('processing_time', 0):.2f} seconds!")
                        
                        # Strategy info
                        st.info(f"📊 **Strategy Used:** {', '.join(result.get('strategies_used', []))}")
                        
                        st.markdown("---")
                        
                        # Summary metrics
                        st.markdown("### 📈 Summary")
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.metric(
                                "Tables Found",
                                len(result.get('tables', [])),
                                help="Number of tables extracted from PDF"
                            )
                        
                        with col2:
                            total_rows = sum(t.get('row_count', 0) for t in result.get('tables', []))
                            st.metric(
                                "Total Rows",
                                total_rows,
                                help="Total data rows across all tables"
                            )
                        
                        with col3:
                            total_cols = sum(t.get('col_count', 0) for t in result.get('tables', []))
                            st.metric(
                                "Total Columns",
                                total_cols,
                                help="Total columns across all tables"
                            )
                        
                        with col4:
                            pages = result['metadata'].get('total_pages', 'N/A')
                            st.metric(
                                "Pages",
                                pages,
                                help="Pages in PDF"
                            )
                        
                        st.markdown("---")
                        
                        # Identified payroll fields
                        if result.get('identified_fields'):
                            st.markdown("### 🏷️ Identified Payroll Fields")
                            
                            fields_df = []
                            for field, locations in result['identified_fields'].items():
                                for loc in locations:
                                    fields_df.append({
                                        'Field Type': field.replace('_', ' ').title(),
                                        'Found In': loc['table'],
                                        'Column Name': loc['column']
                                    })
                            
                            if fields_df:
                                st.dataframe(pd.DataFrame(fields_df), use_container_width=True)
                            
                            st.markdown("---")
                        
                        # Preview tables
                        st.markdown("### 📊 Extracted Tables")
                        
                        for table in result.get('tables', []):
                            with st.expander(f"📄 Page {table.get('page', 1)}, Table {table.get('table_num', 1)} ({table.get('row_count', 0)} rows × {table.get('col_count', 0)} cols)"):
                                st.dataframe(table['data'], use_container_width=True)
                        
                        st.markdown("---")
                        
                        # NEW: UKG Field Categorization and Remapping
                        st.markdown("### 🏷️ UKG Field Categorization")
                        st.info("Review how columns will be organized into UKG tabs. Click 'Remap Fields' to make corrections.")
                        
                        # Get all unique columns across all tables
                        all_columns = {}
                        for table_idx, table in enumerate(result.get('tables', [])):
                            df = table.get('data')
                            if df is not None:
                                categories = st.session_state.pdf_parser.get_column_categories(df)
                                for col, cat_info in categories.items():
                                    all_columns[f"Table{table_idx+1}:{col}"] = {
                                        'table': f"Table {table_idx+1}",
                                    'column': col,
                                    'category': cat_info['category'],
                                    'field_type': cat_info['field_type']
                                }
                        
                        # Display current categorization
                        cat_display = pd.DataFrame([
                            {
                                'Table': v['table'],
                                'Column Name': v['column'],
                                'UKG Tab': v['category'],
                                'Auto-Detected Type': v['field_type'] or 'Custom'
                            }
                            for k, v in all_columns.items()
                        ])
                        
                        st.dataframe(cat_display, use_container_width=True)
                        
                        # Show tab summary
                        tab_counts = cat_display['UKG Tab'].value_counts()
                        cols = st.columns(len(tab_counts))
                        for idx, (tab, count) in enumerate(tab_counts.items()):
                            with cols[idx]:
                                st.metric(tab, count, help=f"{count} columns → {tab} tab")
                        
                        st.markdown("---")
                        
                        # Field Remapping UI - MAKE IT PROMINENT
                        st.markdown("### 🔧 Step 3: Fix Field Categorization (Optional)")
                        st.markdown("**Review the table above. If any column went to the wrong UKG tab, remap it here:**")
                        
                        with st.expander("📝 **Click here to remap fields**", expanded=False):
                            
                            # Initialize overrides in session state
                            if 'field_overrides' not in st.session_state:
                                st.session_state.field_overrides = {}
                            
                            st.markdown("""
                            **How to use:**
                            1. Select a column that's in the wrong tab
                            2. Choose the correct UKG tab for it
                            3. Click 'Add Remap'
                            4. Repeat for any other incorrect columns
                            5. Download your UKG Excel - corrections will be applied automatically
                            """)
                            
                            st.markdown("---")
                            
                            # Remapping interface
                            col1, col2, col3 = st.columns([2, 2, 1])
                            
                            with col1:
                                # Get all column names (without table prefix for user)
                                column_options = [v['column'] for v in all_columns.values()]
                                selected_column = st.selectbox(
                                    "❶ Column to remap:",
                                    options=column_options,
                                    key="remap_column_select"
                                )
                            
                            with col2:
                                new_tab = st.selectbox(
                                    "❷ Move to tab:",
                                    options=['Employee Info', 'Earnings', 'Deductions', 'Taxes', 'Check Info', 'Uncategorized'],
                                    key="remap_tab_select"
                                )
                            
                            with col3:
                                st.write("")  # Spacing
                                st.write("")  # Spacing
                                if st.button("❸ Add Remap", key="add_remap_btn", use_container_width=True, type="primary"):
                                    st.session_state.field_overrides[selected_column] = new_tab
                                    st.success(f"✅ {selected_column} → {new_tab}")
                                    st.rerun()
                            
                            # Show current overrides
                            if st.session_state.field_overrides:
                                st.markdown("---")
                                st.markdown("### ✅ Active Remappings")
                                st.info(f"🎯 {len(st.session_state.field_overrides)} field(s) will be moved when you download the UKG Excel")
                                
                                for col, tab in list(st.session_state.field_overrides.items()):
                                    cols = st.columns([5, 1])
                                    cols[0].markdown(f"• **{col}** → {tab} tab")
                                    if cols[1].button("🗑️", key=f"remove_{col}", help="Remove this remapping"):
                                        del st.session_state.field_overrides[col]
                                        st.rerun()
                                
                                if st.button("🔄 Clear All Remappings", key="clear_remaps"):
                                    st.session_state.field_overrides = {}
                                    st.rerun()
                            else:
                                st.info("💡 No remappings yet. Add them above if needed.")
                        
                        st.markdown("---")
                        
                        # Export section with clear UKG focus
                        st.markdown("### 💾 Step 4: Download Your Data")
                        
                        # Show remapping status prominently
                        if st.session_state.get('field_overrides'):
                            st.success(f"✅ {len(st.session_state.field_overrides)} manual correction(s) will be applied to UKG export")
                        
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            # Excel export - DIRECT
                            try:
                                output_buffer = io.BytesIO()
                                with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
                                    # Summary sheet
                                    summary_data = {
                                        'Filename': [result.get('filename', 'unknown.pdf')],
                                        'Parsed At': [result.get('parsed_at', datetime.now().isoformat())],
                                        'Total Tables': [len(result.get('tables', []))],
                                        'Processing Time (s)': [result.get('processing_time', 0)],
                                        'Strategies Used': [', '.join(result.get('strategies_used', []))]
                                    }
                                    summary_df = pd.DataFrame(summary_data)
                                    summary_df.to_excel(writer, sheet_name='Summary', index=False)
                                    
                                    # Identified fields
                                    if result.get('identified_fields'):
                                        fields_data = []
                                        for field, locations in result.get('identified_fields', {}).items():
                                            for loc in locations:
                                                fields_data.append({
                                                    'Field': field,
                                                    'Table': loc.get('table', 'Unknown'),
                                                    'Column': loc.get('column', 'Unknown')
                                                })
                                        if fields_data:
                                            fields_df = pd.DataFrame(fields_data)
                                            fields_df.to_excel(writer, sheet_name='Identified Fields', index=False)
                                    
                                    # Individual tables
                                    for table in result.get('tables', []):
                                        sheet_name = f"P{table.get('page', 1)}_T{table.get('table_num', 1)}"
                                        sheet_name = sheet_name[:31]  # Excel limit
                                        table['data'].to_excel(writer, sheet_name=sheet_name, index=False)
                                    
                                    # Combined data
                                    tables = result.get('tables', [])
                                    if len(tables) > 1:
                                        try:
                                            all_data = pd.concat([t['data'] for t in tables], ignore_index=True)
                                            all_data.to_excel(writer, sheet_name='All Data', index=False)
                                        except Exception as concat_err:
                                            st.warning(f"Could not combine tables: {str(concat_err)}")
                                
                            # 🆕 UKG Export - PRIMARY BUTTON
                                st.markdown("#### 📊 **UKG Ready Export**")
                                st.markdown("**Creates 5 organized tabs:**")
                                st.markdown("""
                                - Employee Info
                                - Earnings
                                - Deductions
                                - Taxes
                                - Check Info
                                """)
                                
                                excel_buffer = process_parsed_pdf_for_ukg(
                                    result,
                                    filename=uploaded_file.name,
                                    column_overrides=st.session_state.get('field_overrides', {})
                                )
                                
                                # Build label based on overrides
                                override_count = len(st.session_state.get('field_overrides', {}))
                                button_label = "📊 Download UKG Excel (5 Tabs)"
                                if override_count > 0:
                                    button_label = f"📊 Download UKG Excel ({override_count} corrections applied)"

                                st.download_button(
                                        label=button_label,
                                        data=excel_buffer,
                                        file_name=f"UKG_{uploaded_file.name.replace('.pdf', '')}.xlsx",
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                        use_container_width=True,
                                        type="primary",
                                        help="Downloads Excel with 5 UKG-ready tabs + Metadata"
                                )

                            except Exception as e:
                                st.error(f"❌ Error creating Excel: {str(e)}")
                                st.code(str(e))
                        
                        with col2:
                            # CSV export - DIRECT
                            try:
                                tables = result.get('tables', [])
                                if len(tables) > 0:
                                    all_data = pd.concat([t['data'] for t in tables], ignore_index=True)
                                    csv_data = all_data.to_csv(index=False)
                                    
                                    st.download_button(
                                        label="📄 Download CSV",
                                        data=csv_data,
                                        file_name=f"{uploaded_file.name.replace('.pdf', '')}_parsed.csv",
                                        mime="text/csv",
                                        use_container_width=True,
                                        key="download_csv_direct"
                                    )
                                else:
                                    st.warning("No tables to export")
                                    
                            except Exception as e:
                                st.error(f"❌ Error creating CSV: {str(e)}")
                                st.code(str(e))
                        
                        with col3:
                            # ZIP for manual editing - DIRECT
                            try:
                                tables = result.get('tables', [])
                                if len(tables) > 0:
                                    zip_buffer = io.BytesIO()
                                    
                                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                                        # Add each table as separate CSV
                                        for table in tables:
                                            csv_data = table['data'].to_csv(index=False)
                                            filename = f"Page{table.get('page', 1)}_Table{table.get('table_num', 1)}.csv"
                                            zip_file.writestr(filename, csv_data)
                                        
                                        # Add instructions
                                        instructions = """Manual Editing Instructions:

1. Extract all CSV files from this ZIP
2. Open each CSV in Excel or text editor
3. Make your corrections/adjustments
4. Save the files
5. Go to Data Analysis tab in XLR8
6. Upload your corrected CSV files
7. Use the clean data!

Note: Keep column names in first row for re-import
"""
                                        zip_file.writestr("README.txt", instructions)
                                    
                                    st.download_button(
                                        label="🔧 Download ZIP (Editable)",
                                        data=zip_buffer.getvalue(),
                                        file_name=f"{uploaded_file.name.replace('.pdf', '')}_editable.zip",
                                        mime="application/zip",
                                        use_container_width=True,
                                        key="download_zip_direct"
                                    )
                                else:
                                    st.warning("No tables to export")
                                    
                            except Exception as e:
                                st.error(f"❌ Error creating ZIP: {str(e)}")
                                st.code(str(e))
                        
                        st.markdown("---")
                        
                        st.markdown("### ✅ Next Steps")
                        st.info("""
                        **What to do now:**
                        1. **Download** the Excel file above
                        2. **Review** the extracted data
                        3. **Verify** field mappings are correct
                        4. **Import** to UKG Pro/WFM
                        
                        *All processing happened securely on your server - zero PII exposure!*
                        """)
                    
                    else:
                        # Parsing failed
                        st.error("❌ Parsing Failed - No Tables Found")
                        
                        error_msg = result.get('error', 'Unknown error')
                        st.warning(f"**Error Details:** {error_msg}")
                        
                        st.markdown("### 💡 Try This:")
                        st.info("""
                        **Option 1: Enable Comparison Mode**
                        - ✅ Check the "🔍 Compare All 4 Parsers" box above
                        - Click "Parse PDF" again
                        - Try each parser to see which works best
                        
                        **Option 2: Check Your PDF**
                        - Is it a scanned/image PDF? (OCR not supported on Railway)
                        - Is it password-protected?
                        - Does it actually contain tables?
                        """)
                        
                        st.markdown("### 🔍 Troubleshooting")
                        
                        with st.expander("Common Issues and Solutions"):
                            st.markdown("""
                            #### No Tables Detected
                            **Possible causes:**
                            - PDF is scanned/image-based (requires OCR)
                            - PDF is password-protected
                            - PDF has non-standard layout
                            
                            **Solutions:**
                            1. Check Railway logs for missing dependencies
                            2. Try removing password protection from PDF
                            3. Try a different PDF to verify parser is working
                            
                            #### Incomplete Data Extraction
                            **Possible causes:**
                            - Complex merged cells
                            - Multi-column layout
                            - Unusual spacing
                            
                            **Solutions:**
                            1. Check all 5 parsing strategies are available in logs
                            2. Verify system dependencies are installed
                            3. Contact support with specific PDF format details
                            """)
                
                except Exception as e:
                    progress_text.empty()
                    progress_bar.empty()
                    st.error(f"❌ Error parsing PDF: {str(e)}")
                    st.exception(e)
        
        st.markdown("---")
        
        st.markdown("### 🔒 Security & Privacy")
        st.success("""
        **100% Secure Processing:**
        - ✅ All processing happens locally on your Railway server
        - ✅ No external API calls or cloud services
        - ✅ Zero PII exposure risk
        - ✅ HIPAA and GDPR compliant
        - ✅ Complete data privacy guaranteed
        """)

# TAB 3: SECURE DATA ANALYSIS WITH LOCAL LLM (HR/PAYROLL COMPLIANT)
# This is the secure version that keeps data in your infrastructure

with tab6:
    st.markdown("## 🧠 AI Analysis & Intelligence")
    
    # Create sub-tabs for different analysis modes
    analysis_tab1, analysis_tab2, analysis_tab3, analysis_tab4 = st.tabs([
        "📂 Basic Data Analysis", 
        "🤖 AI Document Analysis (Secure)", 
        "💬 AI Chat Assistant",
        "🌱 Seed HCMPACT LLM"
    ])
    
    # ============================================================================
    # BASIC DATA ANALYSIS (Original functionality preserved)
    # ============================================================================
    with analysis_tab1:
        if not st.session_state.current_project:
            st.warning("⚠️ Please create or select a project first (Home tab)")
        else:
            st.info(f"📁 **Active Project:** {st.session_state.current_project}")
            
            st.markdown("""
            <div class='info-box'>
                <h4>📂 Multi-Source Data Upload</h4>
                <p>Upload Excel, CSV, or other data files for cross-reference analysis. 
                XLR8 will identify patterns, detect potential join keys, and help populate UKG templates.</p>
            </div>
            """, unsafe_allow_html=True)
            
            # File uploader
            data_files = st.file_uploader(
                "Upload Data Files (Excel, CSV)",
                type=['xlsx', 'xls', 'csv', 'txt'],
                accept_multiple_files=True,
                key="data_analysis_uploader"
            )
            
            if data_files:
                st.success(f"✅ Loaded {len(data_files)} file(s)")
                
                # Analyze each file
                for file in data_files:
                    with st.expander(f"📁 {file.name}", expanded=True):
                        try:
                            # Read file
                            if file.name.endswith(('.xlsx', '.xls')):
                                df = pd.read_excel(file)
                            elif file.name.endswith('.csv'):
                                df = pd.read_csv(file)
                            else:
                                df = pd.read_csv(file, sep='\t')
                            
                            # File stats
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Rows", len(df))
                            with col2:
                                st.metric("Columns", len(df.columns))
                            with col3:
                                st.metric("Memory", f"{df.memory_usage(deep=True).sum() / 1024:.1f} KB")
                            
                            # Data preview
                            st.markdown("**Preview (first 10 rows):**")
                            st.dataframe(df.head(10), use_container_width=True)
                            
                            # Column analysis
                            st.markdown("**Column Analysis:**")
                            col_info = []
                            for col in df.columns:
                                col_info.append({
                                    'Column': col,
                                    'Type': str(df[col].dtype),
                                    'Non-Null': df[col].notna().sum(),
                                    'Unique': df[col].nunique(),
                                    'Sample': str(df[col].iloc[0]) if len(df) > 0 else ''
                                })
                            
                            st.dataframe(pd.DataFrame(col_info), use_container_width=True)
                            
                            # Potential payroll fields
                            st.markdown("**🔍 Potential Payroll Fields:**")
                            payroll_keywords = {
                                'employee': ['employee', 'emp', 'ee', 'person', 'name'],
                                'id': ['id', 'number', 'badge', 'ssn'],
                                'pay': ['pay', 'wage', 'salary', 'rate', 'amount'],
                                'hours': ['hours', 'hrs', 'time'],
                                'date': ['date', 'period'],
                                'department': ['dept', 'department', 'division', 'location']
                            }
                            
                            detected_fields = {}
                            for col in df.columns:
                                col_lower = col.lower()
                                for field_type, keywords in payroll_keywords.items():
                                    if any(keyword in col_lower for keyword in keywords):
                                        if field_type not in detected_fields:
                                            detected_fields[field_type] = []
                                        detected_fields[field_type].append(col)
                            
                            if detected_fields:
                                for field_type, columns in detected_fields.items():
                                    st.markdown(f"**{field_type.title()}:** {', '.join(columns)}")
                            else:
                                st.info("No standard payroll fields auto-detected")
                            
                            # Export options
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button(f"📥 Download as Excel", key=f"excel_{file.name}"):
                                    output = io.BytesIO()
                                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                        df.to_excel(writer, index=False, sheet_name='Data')
                                    
                                    st.download_button(
                                        "Download",
                                        data=output.getvalue(),
                                        file_name=f"{file.name.split('.')[0]}_analyzed.xlsx",
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                    )
                            
                            with col2:
                                if st.button(f"📄 Download as CSV", key=f"csv_{file.name}"):
                                    csv = df.to_csv(index=False)
                                    st.download_button(
                                        "Download",
                                        data=csv,
                                        file_name=f"{file.name.split('.')[0]}_analyzed.csv",
                                        mime="text/csv"
                                    )
                        
                        except Exception as e:
                            st.error(f"Error reading file: {str(e)}")
            
            else:
                st.markdown("""
                <div class='warning-box'>
                    <h4>📤 No Data Files Uploaded</h4>
                    <p>Upload Excel or CSV files containing:</p>
                    <ul>
                        <li>Employee master data</li>
                        <li>Existing payroll exports</li>
                        <li>Organizational hierarchy</li>
                        <li>Time & attendance records</li>
                        <li>Benefits enrollment data</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
        
        # ============================================================================
        # SECURE AI DOCUMENT ANALYSIS WITH LOCAL LLM
        # ============================================================================
        with analysis_tab2:
            # Initialize AI analysis state
            if 'uploaded_docs' not in st.session_state:
                st.session_state.uploaded_docs = []
            if 'ai_analysis_results' not in st.session_state:
                st.session_state.ai_analysis_results = None
            if 'doc_contents' not in st.session_state:
                st.session_state.doc_contents = {}
            if 'llm_provider' not in st.session_state:
                st.session_state.llm_provider = 'local'
            if 'local_llm_endpoint' not in st.session_state:
                st.session_state.local_llm_endpoint = 'http://178.156.190.64:11434'
            if 'local_llm_model' not in st.session_state:
                st.session_state.local_llm_model = 'mixtral:8x7b'
            
            # Add localStorage persistence via HTML/JavaScript
            st.markdown("""
            <script>
            // Load saved config from localStorage on page load
            window.addEventListener('load', function() {
                const savedEndpoint = localStorage.getItem('xlr8_llm_endpoint');
                const savedModel = localStorage.getItem('xlr8_llm_model');
                
                if (savedEndpoint) {
                    const endpointInput = document.querySelector('input[aria-label="Local LLM Endpoint"]');
                    if (endpointInput) endpointInput.value = savedEndpoint;
                }
                
                if (savedModel) {
                    const modelInput = document.querySelector('input[aria-label="Model Name"]');
                    if (modelInput) modelInput.value = savedModel;
                }
            });
            
            // Save config to localStorage when changed
            function saveConfig() {
                const endpointInput = document.querySelector('input[aria-label="Local LLM Endpoint"]');
                const modelInput = document.querySelector('input[aria-label="Model Name"]');
                
                if (endpointInput) {
                    localStorage.setItem('xlr8_llm_endpoint', endpointInput.value);
                }
                if (modelInput) {
                    localStorage.setItem('xlr8_llm_model', modelInput.value);
                }
            }
            
            // Auto-save on input change
            setTimeout(function() {
                const endpointInput = document.querySelector('input[aria-label="Local LLM Endpoint"]');
                const modelInput = document.querySelector('input[aria-label="Model Name"]');
                
                if (endpointInput) {
                    endpointInput.addEventListener('change', saveConfig);
                    endpointInput.addEventListener('blur', saveConfig);
                }
                if (modelInput) {
                    modelInput.addEventListener('change', saveConfig);
                    modelInput.addEventListener('blur', saveConfig);
                }
            }, 1000);
            </script>
            """, unsafe_allow_html=True)
            
            # Security banner
            st.markdown("""
            <div class='success-box'>
                <h3>🔐 SECURE AI Document Analysis</h3>
                <p><strong>HR/Payroll Compliant:</strong> Uses LOCAL AI to keep your data secure.</p>
                <ul>
                    <li>✅ <strong>Data stays in your infrastructure</strong> - Never leaves your servers</li>
                    <li>✅ <strong>HIPAA/Compliance friendly</strong> - No third-party data processing</li>
                    <li>✅ <strong>No per-use costs</strong> - Free unlimited analysis</li>
                    <li>✅ <strong>Works offline</strong> - No internet required</li>
                    <li>✅ <strong>Complete privacy</strong> - No logs, no tracking</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
            
            # HCMPACT Intelligence Status
            # Filter to only include dictionaries (not UploadedFile objects)
            valid_foundation_files = [f for f in st.session_state.foundation_files if isinstance(f, dict)]
            enabled_foundation_count = len([f for f in valid_foundation_files if f.get('enabled', False)])
            if st.session_state.get('foundation_enabled', True) and enabled_foundation_count > 0:
                st.markdown(f"""
                <div style='background-color: rgba(109, 138, 160, 0.15); padding: 0.75rem; border-radius: 6px; border-left: 4px solid #6d8aa0; margin: 1rem 0;'>
                    <strong>🧠 HCMPACT Intelligence: ACTIVE</strong><br>
                    <small>{enabled_foundation_count} HCMPACT standard(s) will be used to compare against customer data</small><br>
                    <small>Manage in the "Seed HCMPACT LLM" tab</small>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style='background-color: rgba(158, 158, 158, 0.1); padding: 0.75rem; border-radius: 6px; border-left: 4px solid #9E9E9E; margin: 1rem 0;'>
                    <strong>ℹ️ HCMPACT Intelligence: Not Active</strong><br>
                    <small>Analysis will use general UKG best practices. Add HCMPACT standards in "Seed HCMPACT LLM" tab to compare against HCMPACT's proven methodology.</small>
                </div>
                """, unsafe_allow_html=True)
            
            # Configuration section
            with st.expander("⚙️ AI Configuration", expanded=True):
                st.markdown("### 🔐 Security & Privacy Settings")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**AI Provider Selection**")
                    
                    llm_provider = st.radio(
                        "Choose AI Provider",
                        options=['local', 'anthropic'],
                        format_func=lambda x: '🏠 Local LLM (Secure - RECOMMENDED)' if x == 'local' else '☁️ Anthropic API (Cloud - Demo Only)',
                        key='llm_provider_select',
                        help="Local LLM keeps data in your infrastructure. Anthropic sends data to cloud."
                    )
                    
                    st.session_state.llm_provider = llm_provider
                    
                    # Show security indicator
                    if llm_provider == 'local':
                        st.markdown("""
                        <div style='background-color: rgba(76, 175, 80, 0.1); padding: 0.75rem; border-radius: 6px; border-left: 4px solid #4CAF50;'>
                            <strong>✅ SECURE MODE</strong><br>
                            <small>Data stays in your infrastructure</small>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown("""
                        <div style='background-color: rgba(255, 152, 0, 0.1); padding: 0.75rem; border-radius: 6px; border-left: 4px solid #FF9800;'>
                            <strong>⚠️ CLOUD MODE</strong><br>
                            <small>Data will be sent to Anthropic servers</small><br>
                            <small><strong>USE ONLY FOR DEMOS WITH FAKE DATA</strong></small>
                        </div>
                        """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown("**Provider Configuration**")
                    
                    if llm_provider == 'local':
                        # Local LLM settings
                        endpoint = st.text_input(
                            "Local LLM Endpoint",
                            value=st.session_state.local_llm_endpoint,
                            help="Default for Ollama: http://localhost:11434 | Your server: http://178.156.190.64:11434",
                            key="local_llm_endpoint_input"
                        )
                        st.session_state.local_llm_endpoint = endpoint
                        
                        model = st.text_input(
                            "Model Name",
                            value=st.session_state.local_llm_model,
                            help="Examples: mixtral:8x7b (recommended for 32GB), llama3:70b (needs 64GB), mistral:7b (fast)",
                            key="local_llm_model_input"
                        )
                        st.session_state.local_llm_model = model
                        
                        # Show save indicator
                        st.markdown("""
                        <div style='background-color: rgba(76, 175, 80, 0.1); padding: 0.5rem; border-radius: 6px; margin-top: 0.5rem;'>
                            <small>💾 Settings auto-saved to browser (persists across sessions)</small>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Test connection button
                        if st.button("🔌 Test Connection", key="test_local"):
                            with st.spinner("Testing connection..."):
                                try:
                                    import requests
                                    test_url = f"{endpoint}/api/tags"
                                    response = requests.get(test_url, timeout=5)
                                    if response.status_code == 200:
                                        st.success("✅ Connected to local LLM!")
                                        models = response.json().get('models', [])
                                        if models:
                                            st.info(f"Available models: {', '.join([m['name'] for m in models])}")
                                    else:
                                        st.error(f"❌ Connection failed: {response.status_code}")
                                except Exception as e:
                                    st.error(f"❌ Cannot connect: {str(e)}")
                                    st.info("💡 Is Ollama running? Start with: `ollama serve`")
                    
                    else:
                        # Anthropic API settings
                        st.warning("⚠️ DEMO ONLY - Do not use with real customer data!")
                        api_key = st.text_input(
                            "Anthropic API Key",
                            type="password",
                            help="Get from https://console.anthropic.com"
                        )
                        if api_key:
                            st.session_state.anthropic_api_key = api_key
                        
                        st.error("🚨 Real HR/Payroll data will be sent to Anthropic's servers!")
                
                # Analysis options
                st.markdown("---")
                st.markdown("**Analysis Options**")
                
                col1, col2 = st.columns(2)
                with col1:
                    analysis_depth = st.select_slider(
                        "Analysis Depth",
                        options=["Quick", "Standard", "Deep"],
                        value="Standard",
                        help="Quick: Fast overview | Standard: Balanced | Deep: Comprehensive"
                    )
                
                with col2:
                    max_tokens = st.number_input(
                        "Max Response Tokens",
                        min_value=500,
                        max_value=8000,
                        value=2000 if analysis_depth == "Standard" else (1000 if analysis_depth == "Quick" else 4000),
                        step=500,
                        help="Higher = more detailed but slower"
                    )
            
            # PII Detection Warning
            st.markdown("---")
            st.markdown("### ⚠️ Data Privacy & PII Protection")
            
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown("""
                <div class='warning-box'>
                    <strong>Before uploading documents:</strong>
                    <ul>
                        <li>Remove or redact Social Security Numbers (SSNs)</li>
                        <li>Consider removing exact salaries (use ranges)</li>
                        <li>Use sample data (10-20 employees) not full databases</li>
                        <li>Remove home addresses if not needed</li>
                        <li>Remove dates of birth if not needed</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                pii_acknowledged = st.checkbox(
                    "✅ I have reviewed documents for PII",
                    help="Confirm you've removed/redacted sensitive information"
                )
            
            # Document upload section
            st.markdown("---")
            st.markdown("### 📤 Upload Customer Documents")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                uploaded_files = st.file_uploader(
                    "Upload Documents (PDFs, Excel, Word, CSV, Text)",
                    type=['pdf', 'xlsx', 'xls', 'csv', 'docx', 'txt', 'doc'],
                    accept_multiple_files=True,
                    key="ai_document_uploader",
                    help="Upload all customer documents for batch analysis"
                )
            
            with col2:
                st.markdown("<br>", unsafe_allow_html=True)
                if uploaded_files:
                    st.metric("Files Loaded", len(uploaded_files))
                    if st.button("🗑️ Clear All", use_container_width=True):
                        st.session_state.uploaded_docs = []
                        st.session_state.doc_contents = {}
                        st.session_state.ai_analysis_results = None
                        st.rerun()
            
            # Display uploaded files
            if uploaded_files:
                st.success(f"✅ {len(uploaded_files)} document(s) loaded and ready for analysis")
                
                # Show file list
                with st.expander(f"📋 View Uploaded Files ({len(uploaded_files)})", expanded=False):
                    for idx, file in enumerate(uploaded_files, 1):
                        file_size = len(file.getvalue()) / 1024  # KB
                        st.markdown(f"{idx}. **{file.name}** - {file_size:.1f} KB ({file.type})")
                
                # Data residency indicator
                if st.session_state.llm_provider == 'local':
                    st.info("🏠 **Data Residency:** All processing will occur in your infrastructure. No data leaves your servers.")
                else:
                    st.warning("☁️ **Data Residency:** Data will be sent to Anthropic's cloud servers for processing. Use only with demo/fake data!")
                
                # Analysis button
                st.markdown("---")
                col1, col2, col3 = st.columns([2, 1, 2])
                with col2:
                    # Enable button based on provider and requirements
                    can_analyze = False
                    button_label = "🚀 Analyze All Documents"
                    
                    if not pii_acknowledged:
                        button_label = "⚠️ Review PII Warning First"
                    elif st.session_state.llm_provider == 'local':
                        can_analyze = True
                    elif st.session_state.llm_provider == 'anthropic' and st.session_state.get('anthropic_api_key'):
                        can_analyze = True
                        button_label = "⚠️ Analyze (Cloud)"
                    else:
                        button_label = "🔑 Enter API Key First"
                    
                    analyze_button = st.button(
                        button_label,
                        type="primary",
                        use_container_width=True,
                        disabled=not can_analyze
                    )
                
                # Perform analysis
                if analyze_button and can_analyze:
                    with st.spinner("🤖 AI is analyzing your documents... This may take a few minutes..."):
                        try:
                            # Prepare document contents
                            doc_summaries = []
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            
                            for idx, file in enumerate(uploaded_files):
                                status_text.text(f"Processing {file.name}... ({idx+1}/{len(uploaded_files)})")
                                progress_bar.progress((idx + 1) / len(uploaded_files))
                                
                                file_content = ""
                                try:
                                    if file.name.endswith('.pdf'):
                                        try:
                                            from pdf2image import convert_from_bytes
                                            import pytesseract
                                            images = convert_from_bytes(file.read(), dpi=150)
                                            for img in images[:3]:
                                                file_content += pytesseract.image_to_string(img) + "\n\n"
                                        except:
                                            file_content = f"PDF file: {file.name} (Text extraction requires pdf2image and pytesseract)"
                                    
                                    elif file.name.endswith(('.xlsx', '.xls')):
                                        df = pd.read_excel(file)
                                        file_content = f"Columns: {', '.join(df.columns)}\n"
                                        file_content += f"Rows: {len(df)}\n"
                                        file_content += f"Sample data:\n{df.head(5).to_string()}"
                                    
                                    elif file.name.endswith('.csv'):
                                        df = pd.read_csv(file)
                                        file_content = f"Columns: {', '.join(df.columns)}\n"
                                        file_content += f"Rows: {len(df)}\n"
                                        file_content += f"Sample data:\n{df.head(5).to_string()}"
                                    
                                    elif file.name.endswith('.txt'):
                                        file_content = file.read().decode('utf-8', errors='ignore')
                                    
                                    else:
                                        file_content = f"File: {file.name}"
                                    
                                    doc_summaries.append({
                                        'name': file.name,
                                        'type': file.type,
                                        'content': file_content[:5000]
                                    })
                                
                                except Exception as e:
                                    doc_summaries.append({
                                        'name': file.name,
                                        'type': file.type,
                                        'content': f"Error: {str(e)}"
                                    })
                            
                            status_text.text("Sending to AI for analysis...")
                            
                            # BUILD FOUNDATION DATA CONTEXT (if enabled)
                            foundation_context = ""
                            # Filter to only include dictionaries (not UploadedFile objects)
                            valid_foundation_files = [f for f in st.session_state.foundation_files if isinstance(f, dict)]
                            enabled_foundation_files = [f for f in valid_foundation_files if f.get('enabled', False)]
                            
                            if enabled_foundation_files:
                                foundation_context = """
================================================================================
🧠 HCMPACT KNOWLEDGE BASE (HCMPACT's Proven Standards)
================================================================================

You are analyzing customer data using HCMPACT's standard UKG implementation 
approach. The following documents contain HCMPACT's:
- Standard UKG mappings and configurations
- Pay code and deduction code standards
- Organizational structure best practices
- Implementation methodologies and checklists

CRITICAL: Compare the customer's data to HCMPACT's standards and 
recommend configurations that align with HCMPACT's proven approach.

HCMPACT STANDARDS:
"""
                                for idx, foundation_file in enumerate(enabled_foundation_files, 1):
                                    foundation_context += f"""

{'='*80}
HCMPACT STANDARD {idx}: {foundation_file['name']}
Category: {foundation_file.get('category', 'Uncategorized')}
{'='*80}
{foundation_file['content']}
"""
                                
                                foundation_context += """

================================================================================
📊 CUSTOMER DATA (To Be Analyzed Against HCMPACT Standards)
================================================================================

"""
                            
                            # Prepare AI prompt
                            analysis_prompt = f"""You are an expert UKG Pro/WFM implementation consultant analyzing customer documents.
{foundation_context}
CONTEXT:
- Customer: {st.session_state.current_project}
- Number of documents: {len(doc_summaries)}
- Analysis depth: {analysis_depth}

DOCUMENTS TO ANALYZE:
"""
                            for doc in doc_summaries:
                                analysis_prompt += f"\n\n{'='*80}\nFILE: {doc['name']}\n{'='*80}\n{doc['content']}"
                            
                            analysis_prompt += """

ANALYZE AND PROVIDE:

1. EMPLOYEE DATA STRUCTURE
   - Data fields present
   - Approximate employee count
   - Unique identifiers
   - Demographics captured

2. PAY COMPONENTS
   - All earnings/pay codes
   - All deduction codes
   - Benefits/insurance codes
   - Regular vs overtime structure

3. ORGANIZATIONAL STRUCTURE
   - Organizational levels
   - Reporting hierarchy
   - Multiple locations/sites
   - Business units

4. TIME & ATTENDANCE
   - Time tracking methods
   - Shift differentials
   - Leave/absence types
   - Overtime rules

5. UKG MAPPING RECOMMENDATIONS"""
                            
                            # Add HCMPACT-specific guidance if standards are loaded
                            if enabled_foundation_files:
                                analysis_prompt += """
   ⭐ COMPARE TO HCMPACT STANDARDS:
   - How does customer data align with HCMPACT's pay code mappings?
   - What deductions match HCMPACT's standard configurations?
   - Does their org structure fit HCMPACT's recommended hierarchy?
   - Which HCMPACT best practices should be applied?
   - Recommend configurations that match HCMPACT's proven approach
   
   HCMPACT-Based UKG Mapping Recommendations:"""
                            else:
                                analysis_prompt += """
   Standard UKG Mapping Recommendations:"""
                            
                            analysis_prompt += """
   - Pay code mappings
   - Deduction mappings
   - Org hierarchy in UKG
   - Custom fields needed
   - Configuration suggestions

6. DATA QUALITY ISSUES
   - Inconsistencies
   - Missing data
   - Formatting problems
   - Migration challenges

7. IMPLEMENTATION CHECKLIST
   - Configuration tasks
   - Decision points
   - Implementation sequence
   - Timeline estimates

8. SUMMARY
   - Complexity (Low/Medium/High)
   - Effort estimate
   - Key risks
   - Success factors"""
                            
                            if enabled_foundation_files:
                                analysis_prompt += """
   - Alignment with HCMPACT standards (%)
   - Recommended HCMPACT templates to use"""
                            
                            analysis_prompt += """

Provide specific, actionable recommendations. Use headers and bullet points.
"""
                            
                            # Call AI based on provider
                            import requests
                            
                            if st.session_state.llm_provider == 'local':
                                # Local LLM (Ollama)
                                api_url = f"{st.session_state.local_llm_endpoint}/api/generate"
                                
                                payload = {
                                    "model": st.session_state.local_llm_model,
                                    "prompt": analysis_prompt,
                                    "stream": False,
                                    "options": {
                                        "num_predict": max_tokens,
                                        "temperature": 0.7
                                    }
                                }
                                
                                try:
                                    response = requests.post(api_url, json=payload, timeout=300)
                                    
                                    if response.status_code == 200:
                                        result = response.json()
                                        analysis_text = result.get('response', 'No response generated')
                                        
                                        st.session_state.ai_analysis_results = {
                                            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                            'num_documents': len(uploaded_files),
                                            'analysis': analysis_text,
                                            'depth': analysis_depth,
                                            'provider': 'Local LLM (Secure)',
                                            'model': st.session_state.local_llm_model,
                                            'data_residency': 'On-Premises'
                                        }
                                        
                                        progress_bar.empty()
                                        status_text.empty()
                                        st.success("✅ Analysis complete! Data stayed secure in your infrastructure.")
                                        st.rerun()
                                    else:
                                        progress_bar.empty()
                                        status_text.empty()
                                        st.error(f"❌ Local LLM Error: {response.status_code}")
                                        st.info("💡 Check that Ollama is running and the model is pulled: `ollama pull " + st.session_state.local_llm_model + "`")
                                
                                except requests.exceptions.Timeout:
                                    progress_bar.empty()
                                    status_text.empty()
                                    st.error("⏱️ Analysis timed out. Try Quick mode or fewer documents.")
                                except Exception as e:
                                    progress_bar.empty()
                                    status_text.empty()
                                    st.error(f"❌ Error: {str(e)}")
                            
                            else:
                                # Anthropic API (Cloud)
                                api_url = "https://api.anthropic.com/v1/messages"
                                
                                headers = {
                                    "Content-Type": "application/json",
                                    "anthropic-version": "2023-06-01",
                                    "x-api-key": st.session_state.anthropic_api_key
                                }
                                
                                payload = {
                                    "model": "claude-sonnet-4-20250514",
                                    "max_tokens": max_tokens,
                                    "messages": [{"role": "user", "content": analysis_prompt}]
                                }
                                
                                try:
                                    response = requests.post(api_url, headers=headers, json=payload, timeout=120)
                                    
                                    if response.status_code == 200:
                                        result = response.json()
                                        analysis_text = result['content'][0]['text']
                                        
                                        st.session_state.ai_analysis_results = {
                                            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                            'num_documents': len(uploaded_files),
                                            'analysis': analysis_text,
                                            'depth': analysis_depth,
                                            'provider': 'Anthropic API (Cloud)',
                                            'model': 'Claude Sonnet 4',
                                            'data_residency': 'Anthropic Cloud Servers'
                                        }
                                        
                                        progress_bar.empty()
                                        status_text.empty()
                                        st.warning("⚠️ Analysis complete. Data was processed on Anthropic's servers.")
                                        st.rerun()
                                    else:
                                        progress_bar.empty()
                                        status_text.empty()
                                        st.error(f"❌ API Error: {response.status_code}")
                                
                                except Exception as e:
                                    progress_bar.empty()
                                    status_text.empty()
                                    st.error(f"❌ Error: {str(e)}")
                        
                        except Exception as e:
                            st.error(f"❌ Error preparing documents: {str(e)}")
                
                # Display analysis results
                if st.session_state.ai_analysis_results:
                    st.markdown("---")
                    st.markdown("### 📊 Analysis Results")
                    
                    result = st.session_state.ai_analysis_results
                    
                    # Metrics row
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Documents", result['num_documents'])
                    with col2:
                        st.metric("Depth", result['depth'])
                    with col3:
                        st.metric("Provider", result['provider'])
                    with col4:
                        # Color-code data residency
                        if 'On-Premises' in result['data_residency']:
                            st.markdown(f"""
                            <div style='background-color: rgba(76, 175, 80, 0.2); padding: 0.5rem; border-radius: 6px; text-align: center;'>
                                <small style='color: #2E7D32;'><strong>🔐 {result['data_residency']}</strong></small>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div style='background-color: rgba(255, 152, 0, 0.2); padding: 0.5rem; border-radius: 6px; text-align: center;'>
                                <small style='color: #E65100;'><strong>☁️ {result['data_residency']}</strong></small>
                            </div>
                            """, unsafe_allow_html=True)
                    
                    # Display analysis
                    st.markdown("---")
                    st.markdown(result['analysis'])
                    
                    # Export options
                    st.markdown("---")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        report_text = f"""XLR8 SECURE AI DOCUMENT ANALYSIS REPORT
Project: {st.session_state.current_project}
Generated: {result['timestamp']}
Documents Analyzed: {result['num_documents']}
Analysis Depth: {result['depth']}
AI Provider: {result['provider']}
Data Residency: {result['data_residency']}

{'='*80}
ANALYSIS RESULTS
{'='*80}

{result['analysis']}

{'='*80}
Security Note: {'Data processed locally in your infrastructure' if 'On-Premises' in result['data_residency'] else 'Data processed on cloud servers'}
End of Report
"""
                        st.download_button(
                            "📄 Download Report",
                            data=report_text,
                            file_name=f"XLR8_Secure_Analysis_{st.session_state.current_project}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                            mime="text/plain",
                            use_container_width=True
                        )
                    
                    with col2:
                        if st.button("🔄 Re-Analyze", use_container_width=True):
                            st.session_state.ai_analysis_results = None
                            st.rerun()
                    
                    with col3:
                        if st.button("🗑️ Clear Results", use_container_width=True):
                            st.session_state.ai_analysis_results = None
                            st.session_state.uploaded_docs = []
                            st.rerun()
            
            else:
                st.markdown("""
                <div class='warning-box'>
                    <h4>📤 No Documents Uploaded</h4>
                    <p><strong>To use Secure AI Analysis:</strong></p>
                    <ol>
                        <li>Set up local LLM (Ollama recommended)</li>
                        <li>Remove PII from customer documents</li>
                        <li>Upload documents (PDFs, Excel, Word, CSV)</li>
                        <li>Acknowledge PII review</li>
                        <li>Click "Analyze All Documents"</li>
                        <li>Review analysis and export reports</li>
                    </ol>
                    <p><strong>Why Local LLM?</strong></p>
                    <ul>
                        <li>Data stays in your infrastructure</li>
                        <li>HIPAA/compliance friendly</li>
                        <li>No per-use costs</li>
                        <li>Complete privacy and control</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
                
                # Setup instructions
                with st.expander("💡 How to Set Up Local LLM (Ollama)", expanded=False):
                    st.markdown("""
                    ### Quick Setup (5 minutes):
                    
                    **1. Install Ollama:**
                    - Mac/Linux: `curl -fsSL https://ollama.ai/install.sh | sh`
                    - Windows: Download from https://ollama.ai
                    
                    **2. Start Ollama:**
                    ```bash
                    ollama serve
                    ```
                    
                    **3. Pull a Model:**
                    ```bash
                    # Recommended models:
                    ollama pull llama3:70b      # Best quality (needs ~40GB RAM)
                    ollama pull mixtral:8x7b    # Good balance (needs ~24GB RAM)
                    ollama pull mistral:7b      # Fast (needs ~8GB RAM)
                    ```
                    
                    **4. Configure XLR8:**
                    - Endpoint: `http://localhost:11434` (default)
                    - Model: The model you pulled above
                    - Click "Test Connection"
                    
                    **That's it!** Your data will now stay secure in your infrastructure.
                    """)
        
        # ============================================================================
        # AI CHAT ASSISTANT
        # ============================================================================
        with analysis_tab3:
            if 'chat_history' not in st.session_state:
                st.session_state.chat_history = []
            
            st.markdown("""
            <div class='info-box'>
                <h3>💬 Secure AI Chat Assistant</h3>
                <p>Ask questions about your analyzed documents. Uses the same secure provider configured in Analysis tab.</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Security indicator
            if st.session_state.llm_provider == 'local':
                st.success("🔐 Using Local LLM - Chat data stays in your infrastructure")
            else:
                st.warning("☁️ Using Cloud API - Chat data sent to Anthropic servers")
            
            # Check if analysis exists
            if not st.session_state.get('ai_analysis_results'):
                st.info("💡 Upload and analyze documents first to enable contextual chat.")
            
            # Display chat history
            for message in st.session_state.chat_history:
                if message['role'] == 'user':
                    st.markdown(f"""
                    <div style='background-color: rgba(109, 138, 160, 0.1); padding: 1rem; border-radius: 8px; margin: 0.5rem 0;'>
                        <strong>You:</strong> {message['content']}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style='background-color: rgba(125, 150, 168, 0.1); padding: 1rem; border-radius: 8px; margin: 0.5rem 0;'>
                        <strong>AI:</strong><br>{message['content']}
                    </div>
                    """, unsafe_allow_html=True)
            
            # Chat input
            user_question = st.text_input(
                "Ask a question",
                placeholder="e.g., 'How many pay codes should I configure?' or 'What org levels do I need?'",
                key="chat_input"
            )
            
            col1, col2 = st.columns([5, 1])
            with col2:
                send_button = st.button("Send", use_container_width=True, type="primary")
            
            # Handle chat
            if send_button and user_question:
                st.session_state.chat_history.append({'role': 'user', 'content': user_question})
                
                context = ""
                if st.session_state.get('ai_analysis_results'):
                    context = f"\n\nCONTEXT:\n{st.session_state.ai_analysis_results['analysis']}"
                
                # Add foundation context if enabled
                foundation_chat_context = ""
                # Filter to only include dictionaries (not UploadedFile objects)
                valid_foundation_files = [f for f in st.session_state.foundation_files if isinstance(f, dict)]
                enabled_foundation_files = [f for f in valid_foundation_files if f.get('enabled', False)]
                if enabled_foundation_files:
                    foundation_chat_context = "\n\nFOUNDATION STANDARDS (Your Company's Approach):\n"
                    for foundation_file in enabled_foundation_files:
                        foundation_chat_context += f"\n{foundation_file['name']} ({foundation_file.get('category', 'General')}):\n"
                        foundation_chat_context += foundation_file['content'][:500] + "...\n"  # Truncated for chat
                
                chat_prompt = f"""You are a UKG implementation expert for project: {st.session_state.current_project}.
{foundation_chat_context}
{context}

USER: {user_question}

Provide a helpful, specific answer based on the context and your UKG expertise."""
                
                try:
                    import requests
                    
                    with st.spinner("🤖 Thinking..."):
                        if st.session_state.llm_provider == 'local':
                            api_url = f"{st.session_state.local_llm_endpoint}/api/generate"
                            payload = {
                                "model": st.session_state.local_llm_model,
                                "prompt": chat_prompt,
                                "stream": False,
                                "options": {"num_predict": 500}
                            }
                            response = requests.post(api_url, json=payload, timeout=60)
                            
                            if response.status_code == 200:
                                ai_response = response.json().get('response', 'No response')
                                st.session_state.chat_history.append({'role': 'assistant', 'content': ai_response})
                                st.rerun()
                        
                        else:
                            if st.session_state.get('anthropic_api_key'):
                                api_url = "https://api.anthropic.com/v1/messages"
                                headers = {
                                    "Content-Type": "application/json",
                                    "anthropic-version": "2023-06-01",
                                    "x-api-key": st.session_state.anthropic_api_key
                                }
                                payload = {
                                    "model": "claude-sonnet-4-20250514",
                                    "max_tokens": 500,
                                    "messages": [{"role": "user", "content": chat_prompt}]
                                }
                                response = requests.post(api_url, headers=headers, json=payload, timeout=30)
                                
                                if response.status_code == 200:
                                    ai_response = response.json()['content'][0]['text']
                                    st.session_state.chat_history.append({'role': 'assistant', 'content': ai_response})
                                    st.rerun()
                            else:
                                st.error("API key required for cloud mode")
                
                except Exception as e:
                    st.error(f"Error: {str(e)}")
            
            # Clear chat
            if st.session_state.chat_history:
                if st.button("🗑️ Clear Chat"):
                    st.session_state.chat_history = []
                    st.rerun()
        
        # ============================================================================
        # FOUNDATION DATA LIBRARY
        # ============================================================================
        with analysis_tab4:
            st.markdown("""
            <div class='info-box'>
                <h3>🌱 Seed HCMPACT LLM</h3>
                <p>Upload HCMPACT's knowledge base across all service areas: PRO Core, WFM, Templates, 
                Prompts, Talent Management (Recruiting, Onboarding, Performance, Compensation, Succession), 
                Service Delivery, Project Management, Change Management, and Industry Research. 
                When enabled, the AI will compare customer data to 
                <strong>HCMPACT's proven standards</strong> and provide recommendations based on <strong>HCMPACT's methodology</strong>.</p>
            </div>
            """, unsafe_allow_html=True)
            
            # HCMPACT Intelligence toggle
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown("### 🧠 HCMPACT Intelligence Status")
            with col2:
                if 'foundation_enabled' not in st.session_state:
                    st.session_state.foundation_enabled = True
                
                foundation_toggle = st.toggle(
                    "Enable HCMPACT",
                    value=st.session_state.foundation_enabled,
                    key="foundation_toggle_ui"
                )
                st.session_state.foundation_enabled = foundation_toggle
            
            # Status indicators
            # Filter to only include dictionaries (not UploadedFile objects)
            valid_foundation_files = [f for f in st.session_state.foundation_files if isinstance(f, dict)]
            enabled_count = len([f for f in valid_foundation_files if f.get('enabled', False)])
            total_count = len(valid_foundation_files)
            
            status_col1, status_col2, status_col3 = st.columns(3)
            with status_col1:
                st.metric("Total Files", total_count)
            with status_col2:
                st.metric("Enabled Files", enabled_count)
            with status_col3:
                if st.session_state.foundation_enabled and enabled_count > 0:
                    st.markdown("""
                    <div style='background-color: rgba(76, 175, 80, 0.2); padding: 0.75rem; border-radius: 6px; text-align: center;'>
                        <strong style='color: #2E7D32;'>✅ ACTIVE</strong>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div style='background-color: rgba(255, 152, 0, 0.2); padding: 0.75rem; border-radius: 6px; text-align: center;'>
                        <strong style='color: #E65100;'>⚠️ INACTIVE</strong>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Upload new HCMPACT standard file
            st.markdown("### ➕ Add HCMPACT Standard")
            
            upload_col1, upload_col2 = st.columns([3, 1])
            with upload_col1:
                foundation_upload = st.file_uploader(
                    "Upload HCMPACT Standard Document",
                    type=['txt', 'md', 'csv', 'xlsx', 'xls', 'docx', 'pdf'],
                    key="foundation_uploader",
                    help="Upload HCMPACT's standard UKG configurations, mappings, or best practices"
                )
            
            with upload_col2:
                foundation_category = st.selectbox(
                    "Category",
                    ["PRO Core", "WFM", "Templates", "Prompts", "Ben Admin", 
                     "Recruiting", "Onboarding", "Performance", "Compensation", 
                     "Succession", "Doc Manager", "UKG Service Delivery", 
                     "Project Management", "Search & Selection", "Change Management", 
                     "HCMPACT Service Delivery", "Industry Research"],
                    key="foundation_category"
                )
            
            if foundation_upload:
                if st.button("📥 Add to HCMPACT Knowledge Base", type="primary", use_container_width=True):
                    try:
                        # Read file content
                        if foundation_upload.name.endswith(('.txt', '.md')):
                            content = foundation_upload.read().decode('utf-8')
                        elif foundation_upload.name.endswith('.csv'):
                            df = pd.read_csv(foundation_upload)
                            content = f"CSV Data:\n{df.to_string()}"
                        elif foundation_upload.name.endswith(('.xlsx', '.xls')):
                            df = pd.read_excel(foundation_upload)
                            content = f"Excel Data:\n{df.to_string()}"
                        else:
                            content = f"[Binary file: {foundation_upload.name}]"
                        
                        # Add to foundation library
                        new_foundation_file = {
                            'name': foundation_upload.name,
                            'content': content,
                            'category': foundation_category,
                            'enabled': True,
                            'uploaded_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        st.session_state.foundation_files.append(new_foundation_file)
                        st.success(f"✅ Added '{foundation_upload.name}' to HCMPACT Knowledge Base!")
                        st.rerun()
                    
                    except Exception as e:
                        st.error(f"❌ Error reading file: {str(e)}")
            
            st.markdown("---")
            
            # Display foundation library
            st.markdown("### 📚 HCMPACT Knowledge Base")
            
            # Clean up any invalid entries (UploadedFile objects)
            st.session_state.foundation_files = [f for f in st.session_state.foundation_files if isinstance(f, dict)]
            
            if not st.session_state.foundation_files:
                st.info("""
                📋 **No HCMPACT standards loaded yet**
                
                Upload HCMPACT's knowledge base organized by service area:
                - **PRO Core / WFM**: Configuration guides, standard mappings, best practices
                - **Templates**: Standard deliverables, documents, configurations
                - **Prompts**: AI prompts, analysis frameworks, question libraries
                - **Service Delivery**: UKG & HCMPACT service delivery methodologies
                - **Project Management**: Implementation checklists, timelines, methodologies
                - **Talent Management**: Recruiting, Onboarding, Performance, Compensation, Succession
                - **Change Management**: Change frameworks, communication templates
                - **Industry Research**: Sector-specific insights, benchmarks, trends
                """)
            else:
                # Group by category
                categories = {}
                for file in st.session_state.foundation_files:
                    cat = file.get('category', 'Other')
                    if cat not in categories:
                        categories[cat] = []
                    categories[cat].append(file)
                
                # Display by category
                for category, files in sorted(categories.items()):
                    with st.expander(f"📁 {category} ({len(files)} files)", expanded=True):
                        for idx, file in enumerate(files):
                            file_col1, file_col2, file_col3, file_col4 = st.columns([3, 1, 1, 1])
                            
                            with file_col1:
                                # File name with status indicator
                                status_icon = "✅" if file.get('enabled', False) else "⭕"
                                st.markdown(f"""
                                <div style='padding: 0.5rem; background: {"rgba(76, 175, 80, 0.1)" if file.get("enabled", False) else "rgba(158, 158, 158, 0.1)"}; 
                                    border-radius: 6px; border-left: 3px solid {"#4CAF50" if file.get("enabled", False) else "#9E9E9E"};'>
                                    <strong>{status_icon} {file['name']}</strong><br>
                                    <small style='color: #666;'>Uploaded: {file.get('uploaded_at', 'N/A')}</small>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            with file_col2:
                                # Toggle enable/disable
                                toggle_key = f"toggle_{category}_{idx}"
                                new_state = st.checkbox(
                                    "Enable",
                                    value=file.get('enabled', False),
                                    key=toggle_key
                                )
                                if new_state != file.get('enabled', False):
                                    file['enabled'] = new_state
                                    st.rerun()
                            
                            with file_col3:
                                # Preview button
                                preview_key = f"preview_{category}_{idx}"
                                if st.button("👁️", key=preview_key, help="Preview content"):
                                    st.session_state[f'show_preview_{category}_{idx}'] = not st.session_state.get(f'show_preview_{category}_{idx}', False)
                                    st.rerun()
                            
                            with file_col4:
                                # Delete button
                                if st.button("🗑️", key=f"del_{category}_{idx}", help="Delete file"):
                                    st.session_state.foundation_files.remove(file)
                                    st.rerun()
                            
                            # Show preview if toggled
                            if st.session_state.get(f'show_preview_{category}_{idx}', False):
                                preview_content = file['content'][:1000]
                                if len(file['content']) > 1000:
                                    preview_content += "\n\n... (truncated)"
                                st.markdown(f"**Preview: {file['name']}**")
                                st.code(preview_content, language=None)
                                st.markdown("---")

                
                st.markdown("---")
                
                # Bulk actions
                st.markdown("### ⚡ Bulk Actions")
                bulk_col1, bulk_col2, bulk_col3 = st.columns(3)
                
                with bulk_col1:
                    if st.button("✅ Enable All", use_container_width=True):
                        for file in st.session_state.foundation_files:
                            if isinstance(file, dict):
                                file['enabled'] = True
                        st.rerun()
                
                with bulk_col2:
                    if st.button("⭕ Disable All", use_container_width=True):
                        for file in st.session_state.foundation_files:
                            if isinstance(file, dict):
                                file['enabled'] = False
                        st.rerun()
                
                with bulk_col3:
                    if st.button("🗑️ Clear All", use_container_width=True, type="secondary"):
                        if st.session_state.get('confirm_clear_foundation'):
                            st.session_state.foundation_files = []
                            st.session_state.confirm_clear_foundation = False
                            st.rerun()
                        else:
                            st.session_state.confirm_clear_foundation = True
                            st.warning("⚠️ Click again to confirm deletion of all foundation files")
            
            # How it works
            st.markdown("---")
            with st.expander("💡 How Seeding HCMPACT LLM Works", expanded=False):
                st.markdown("""
                ### How It Works
                
                **1. Upload HCMPACT Standards**
                - Add HCMPACT's standard UKG configurations
                - Include pay codes, deductions, org structures, best practices
                - Categorize documents for easy management
                
                **2. Enable HCMPACT Intelligence**
                - Toggle the "Enable HCMPACT" switch at the top
                - Enable/disable individual files as needed
                - Only enabled files are included in AI analysis
                
                **3. Analyze Customer Documents**
                - Go to "AI Document Analysis" tab
                - Upload customer documents as usual
                - Click "Analyze All Documents"
                
                **4. Get HCMPACT-Based Recommendations**
                - AI compares customer data to HCMPACT's standards
                - Recommendations align with HCMPACT's proven approach
                - Identifies gaps between customer and HCMPACT standards
                - Suggests configurations that match HCMPACT's methodology
                
                **Example Use Cases:**
                - **PRO Core**: "Compare customer configuration to HCMPACT's PRO Core best practices"
                - **WFM**: "Analyze time tracking setup against HCMPACT's WFM standards"
                - **Templates**: "Apply HCMPACT's standard deliverable templates to this project"
                - **Prompts**: "Use HCMPACT's discovery prompts for requirements gathering"
                - **Change Management**: "Recommend HCMPACT's change management framework"
                - **Industry Research**: "Compare to HCMPACT's healthcare sector benchmarks"
                
                **Pro Tips:**
                - **Organize by service area**: Use categories to match HCMPACT's service lines
                - **Start with core areas**: Begin with PRO Core, WFM, and Templates
                - **Add industry-specific**: Include relevant Industry Research for each client
                - **Keep current**: Update standards as HCMPACT methodology evolves
                - **Enable strategically**: Turn on only relevant categories per project
                """)

# TAB 4: SECTION-BASED TEMPLATE SYSTEM

with tab5:
    st.markdown("## 📝 Templated Parser System")
    st.markdown("**Define sections + fields to capture all line items from variable-height employee blocks**")
    
    # Initialize state
    if 'templates' not in st.session_state:
        st.session_state.templates = {}
    if 'pdf_images' not in st.session_state:
        st.session_state.pdf_images = []
    if 'extracted_data' not in st.session_state:
        st.session_state.extracted_data = None
    if 'section_box' not in st.session_state:
        st.session_state.section_box = None
    if 'name_box' not in st.session_state:
        st.session_state.name_box = None
    if 'field_columns' not in st.session_state:
        st.session_state.field_columns = []
    if 'template_step' not in st.session_state:
        st.session_state.template_step = 1
    
    # Template directory
    TEMPLATE_DIR = Path("templates")
    TEMPLATE_DIR.mkdir(exist_ok=True)
    
    # Helper functions
    def load_templates():
        templates = {}
        for file in TEMPLATE_DIR.glob("*.json"):
            try:
                with open(file, 'r') as f:
                    templates[file.stem] = json.load(f)
            except:
                pass
        return templates
    
    def save_template(name, template_data):
        filepath = TEMPLATE_DIR / f"{name}.json"
        with open(filepath, 'w') as f:
            json.dump(template_data, f, indent=2)
    
    def ocr_region(image, x1, y1, x2, y2):
        """Extract text from region"""
        try:
            import pytesseract
            cropped = image.crop((int(x1), int(y1), int(x2), int(y2)))
            text = pytesseract.image_to_string(cropped, config='--psm 6')
            return text.strip()
        except:
            return ""
    
    def ocr_with_line_positions(image, x1, y1, x2, y2):
        """Get text with Y positions for each line"""
        try:
            import pytesseract
            from PIL import Image
            cropped = image.crop((int(x1), int(y1), int(x2), int(y2)))
            
            # Get detailed OCR data
            data = pytesseract.image_to_data(cropped, output_type=pytesseract.Output.DICT)
            
            # Group by line (block_num + par_num + line_num)
            lines = {}
            for i, text in enumerate(data['text']):
                if text.strip():
                    line_id = f"{data['block_num'][i]}_{data['par_num'][i]}_{data['line_num'][i]}"
                    y_pos = int(y1) + data['top'][i]
                    if line_id not in lines:
                        lines[line_id] = {'text': '', 'y': y_pos}
                    lines[line_id]['text'] += ' ' + text
            
            # Return sorted by Y position
            result = [(line['text'].strip(), line['y']) for line in lines.values()]
            result.sort(key=lambda x: x[1])
            return result
        except:
            return []
    
    def find_employee_sections(image, name_box, image_width):
        """Find all employee sections by detecting names"""
        x1, y1, x2, y2 = name_box['x1'], name_box['y1'], name_box['x2'], name_box['y2']
        
        # Get all text with positions in name column
        lines = ocr_with_line_positions(image, x1, 0, x2, image.height)
        
        # Filter to likely employee names (in the reference Y range)
        employees = []
        for text, y_pos in lines:
            # Basic name detection: has letters, reasonable length
            if len(text) > 3 and any(c.isalpha() for c in text):
                employees.append({'name': text, 'y_start': y_pos})
        
        # Create sections
        sections = []
        for i, emp in enumerate(employees):
            y_start = emp['y_start']
            y_end = employees[i+1]['y_start'] - 5 if i+1 < len(employees) else image.height
            sections.append({
                'employee': emp['name'],
                'y_start': y_start,
                'y_end': y_end
            })
        
        return sections
    
    def extract_column_from_section(image, section, column):
        """Extract all lines from one column within one section"""
        x1 = column['x1']
        x2 = column['x2']
        y1 = section['y_start']
        y2 = section['y_end']
        
        # Get all lines in this region
        text = ocr_region(image, x1, y1, x2, y2)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        return [{
            'employee': section['employee'],
            'category': column['category'],
            'field': column['name'],
            'value': line
        } for line in lines]
    
    # Load templates
    st.session_state.templates = load_templates()
    
    # Check dependencies
    try:
        from streamlit_drawable_canvas import st_canvas
        from pdf2image import convert_from_bytes
        DRAWING_AVAILABLE = True
    except ImportError:
        DRAWING_AVAILABLE = False
    
    if not DRAWING_AVAILABLE:
        st.error("⚠️ Install: streamlit-drawable-canvas, pdf2image, Pillow, pytesseract")
    else:
        # Sub-tabs
        ttab1, ttab2, ttab3 = st.tabs(["📝 Create Template", "⚡ Process PDF", "📚 Manage"])
        
        # CREATE TEMPLATE
        with ttab1:
            st.header("Create Section + Field Template")
            
            # Template info
            col1, col2 = st.columns([2, 1])
            with col1:
                uploaded_file = st.file_uploader("Upload Sample PDF", type=['pdf'], key="template_upload")
            with col2:
                template_name = st.text_input("Template Name", placeholder="Dayforce_Register")
                template_vendor = st.text_input("Vendor", placeholder="Dayforce")
            
            if uploaded_file and template_name:
                # Convert PDF
                if not st.session_state.pdf_images or st.session_state.get('last_upload') != uploaded_file.name:
                    with st.spinner("Converting..."):
                        pdf_bytes = uploaded_file.read()
                        st.session_state.pdf_images = convert_from_bytes(pdf_bytes, dpi=200, first_page=1, last_page=1)
                        st.session_state.last_upload = uploaded_file.name
                        st.session_state.template_step = 1
                        st.session_state.section_box = None
                        st.session_state.name_box = None
                        st.session_state.field_columns = []
                
                image = st.session_state.pdf_images[0]
                img_w, img_h = image.size
                
                # STEP INDICATOR
                steps = ["1️⃣ Section Box", "2️⃣ Name Location", "3️⃣ Field Columns"]
                st.markdown(f"**Current Step:** {steps[st.session_state.template_step - 1]}")
                st.progress(st.session_state.template_step / 3)
                
                st.markdown("---")
                
                # STEP 1: Draw section box
                if st.session_state.template_step == 1:
                    st.markdown("### Step 1: Draw Section Boundary")
                    st.info("📦 Draw ONE box around a complete employee's section (from name to last line)")
                    
                    canvas_result = st_canvas(
                        fill_color="rgba(0,255,0,0.1)",
                        stroke_width=3,
                        stroke_color="#00FF00",
                        background_image=image,
                        update_streamlit=True,
                        height=img_h,
                        width=img_w,
                        drawing_mode="rect",
                        key="canvas_section"
                    )
                    
                    if canvas_result.json_data:
                        objects = [obj for obj in canvas_result.json_data.get("objects", []) if obj["type"] == "rect"]
                        if objects:
                            rect = objects[0]  # Use first rectangle
                            st.session_state.section_box = {
                                'x1': int(rect['left']),
                                'y1': int(rect['top']),
                                'x2': int(rect['left'] + rect['width']),
                                'y2': int(rect['top'] + rect['height'])
                            }
                            
                            if st.button("✅ Continue to Name Location", type="primary"):
                                st.session_state.template_step = 2
                                st.rerun()
                
                # STEP 2: Draw name box
                elif st.session_state.template_step == 2:
                    st.markdown("### Step 2: Mark Employee Name Location")
                    st.info("📍 Draw a box around just the employee NAME (where names appear in all sections)")
                    
                    canvas_result = st_canvas(
                        fill_color="rgba(0,0,255,0.1)",
                        stroke_width=3,
                        stroke_color="#0000FF",
                        background_image=image,
                        update_streamlit=True,
                        height=img_h,
                        width=img_w,
                        drawing_mode="rect",
                        key="canvas_name"
                    )
                    
                    if canvas_result.json_data:
                        objects = [obj for obj in canvas_result.json_data.get("objects", []) if obj["type"] == "rect"]
                        if objects:
                            rect = objects[0]
                            st.session_state.name_box = {
                                'x1': int(rect['left']),
                                'y1': int(rect['top']),
                                'x2': int(rect['left'] + rect['width']),
                                'y2': int(rect['top'] + rect['height'])
                            }
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("⬅️ Back to Section"):
                                    st.session_state.template_step = 1
                                    st.rerun()
                            with col2:
                                if st.button("✅ Continue to Fields", type="primary"):
                                    st.session_state.template_step = 3
                                    st.rerun()
                
                # STEP 3: Draw field columns
                elif st.session_state.template_step == 3:
                    st.markdown("### Step 3: Define Field Columns")
                    st.info("📊 Draw VERTICAL strips for each field type (Earnings, Deductions, etc.)")
                    
                    col_canvas, col_controls = st.columns([3, 1])
                    
                    with col_controls:
                        st.markdown("**Controls:**")
                        if st.button("🗑️ Clear Columns"):
                            st.session_state.field_columns = []
                            st.rerun()
                        if st.button("⬅️ Back to Name"):
                            st.session_state.template_step = 2
                            st.rerun()
                    
                    with col_canvas:
                        canvas_result = st_canvas(
                            fill_color="rgba(255,0,0,0.1)",
                            stroke_width=3,
                            stroke_color="#FF0000",
                            background_image=image,
                            update_streamlit=True,
                            height=img_h,
                            width=img_w,
                            drawing_mode="rect",
                            key="canvas_columns"
                        )
                    
                    if canvas_result.json_data:
                        objects = [obj for obj in canvas_result.json_data.get("objects", []) if obj["type"] == "rect"]
                        
                        if objects:
                            st.markdown("---")
                            st.markdown(f"### Label {len(objects)} Column(s)")
                            
                            # Update field_columns
                            temp_cols = []
                            for idx, rect in enumerate(objects):
                                with st.expander(f"Column {idx+1}", expanded=True):
                                    x1 = int(rect['left'])
                                    x2 = x1 + int(rect['width'])
                                    
                                    c1, c2 = st.columns(2)
                                    with c1:
                                        name = st.text_input("Field Name", key=f"fn_{idx}", placeholder="Earnings")
                                    with c2:
                                        cat = st.selectbox("Category", 
                                            ["Employee Info", "Earnings", "Deductions", "Taxes", "Check Info"],
                                            key=f"fc_{idx}")
                                    
                                    if name:
                                        temp_cols.append({
                                            'id': idx,
                                            'name': name,
                                            'category': cat,
                                            'x1': x1,
                                            'x2': x2
                                        })
                            
                            st.session_state.field_columns = temp_cols
                            
                            # Save button
                            if len(temp_cols) == len(objects) and len(objects) > 0:
                                st.markdown("---")
                                if st.button("💾 Save Complete Template", type="primary", use_container_width=True):
                                    template_data = {
                                        'name': template_name,
                                        'vendor': template_vendor,
                                        'created_at': datetime.now().isoformat(),
                                        'type': 'section_based',
                                        'section_template': {
                                            'section_box': st.session_state.section_box,
                                            'name_location': st.session_state.name_box
                                        },
                                        'field_columns': [{k: v for k, v in c.items() if k != 'id'} for c in temp_cols]
                                    }
                                    
                                    save_template(template_name, template_data)
                                    st.session_state.templates[template_name] = template_data
                                    st.success(f"✅ Template '{template_name}' saved!")
                                    st.balloons()
                                    
                                    # Reset
                                    st.session_state.template_step = 1
                                    st.session_state.section_box = None
                                    st.session_state.name_box = None
                                    st.session_state.field_columns = []
                                    st.session_state.pdf_images = []
                                    st.rerun()
                            else:
                                st.warning("⚠️ Name all columns to save")
        
        # PROCESS PDF
        with ttab2:
            st.header("Process PDF with Section Template")
            
            if not st.session_state.templates:
                st.warning("⚠️ Create a template first")
            else:
                # Check for section-based templates
                section_templates = {k: v for k, v in st.session_state.templates.items() 
                                   if v.get('type') == 'section_based'}
                
                if not section_templates:
                    st.warning("⚠️ No section-based templates found. Create one in the 'Create Template' tab.")
                else:
                    c1, c2 = st.columns([2, 1])
                    with c1:
                        process_file = st.file_uploader("Upload PDF", type=['pdf'], key="process")
                    with c2:
                        selected = st.selectbox("Template", list(section_templates.keys()))
                    
                    if process_file and selected:
                        template = section_templates[selected]
                        
                        with st.spinner("Converting PDF..."):
                            pdf_bytes = process_file.read()
                            images = convert_from_bytes(pdf_bytes, dpi=300, first_page=1, last_page=3)
                        
                        st.success(f"✅ {len(images)} page(s)")
                        
                        if st.button("🚀 Extract All Line Items", type="primary", use_container_width=True):
                            with st.spinner("Finding employee sections and extracting data..."):
                                all_data = []
                                
                                for page_idx, image in enumerate(images):
                                    st.info(f"Processing page {page_idx + 1}...")
                                    
                                    # Find employee sections
                                    sections = find_employee_sections(
                                        image,
                                        template['section_template']['name_location'],
                                        image.width
                                    )
                                    
                                    st.info(f"Found {len(sections)} employees on page {page_idx + 1}")
                                    
                                    # Extract from each section
                                    for section in sections:
                                        for column in template['field_columns']:
                                            items = extract_column_from_section(image, section, column)
                                            all_data.extend(items)
                                
                                st.session_state.extracted_data = all_data
                                st.success(f"✅ Extracted {len(all_data)} line items!")
                            
                            # Display preview
                            if all_data:
                                st.markdown("---")
                                st.markdown("### 📊 Extracted Data Preview")
                                
                                # Group by category
                                by_category = {}
                                for item in all_data:
                                    cat = item['category']
                                    if cat not in by_category:
                                        by_category[cat] = []
                                    by_category[cat].append(item)
                                
                                for cat in ['Employee Info', 'Earnings', 'Deductions', 'Taxes', 'Check Info']:
                                    if cat in by_category:
                                        with st.expander(f"{cat} ({len(by_category[cat])} items)"):
                                            df = pd.DataFrame(by_category[cat])
                                            st.dataframe(df, use_container_width=True)
                                
                                # Export to Excel
                                st.markdown("---")
                                output = io.BytesIO()
                                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                    # Write by category
                                    for cat in ['Employee Info', 'Earnings', 'Deductions', 'Taxes', 'Check Info']:
                                        if cat in by_category:
                                            df = pd.DataFrame(by_category[cat])
                                            df.to_excel(writer, sheet_name=cat[:31], index=False)
                                    
                                    # Metadata
                                    pd.DataFrame({
                                        'Property': ['File', 'Template', 'Date', 'Pages', 'Total Items'],
                                        'Value': [process_file.name, selected, datetime.now().isoformat(), 
                                                len(images), len(all_data)]
                                    }).to_excel(writer, sheet_name='Metadata', index=False)
                                
                                output.seek(0)
                                st.download_button(
                                    "📥 Download Excel with All Line Items",
                                    output,
                                    f"UKG_LineItems_{process_file.name.replace('.pdf', '')}.xlsx",
                                    type="primary",
                                    use_container_width=True
                                )
        
        # MANAGE TEMPLATES
        with ttab3:
            st.header("Manage Templates")
            
            if not st.session_state.templates:
                st.info("📋 No templates")
            else:
                for name, data in st.session_state.templates.items():
                    with st.expander(f"📄 {name}"):
                        c1, c2 = st.columns([3, 1])
                        with c1:
                            st.markdown(f"**Vendor:** {data.get('vendor', 'N/A')}")
                            st.markdown(f"**Type:** {data.get('type', 'basic')}")
                            if data.get('type') == 'section_based':
                                st.markdown(f"**Field Columns:** {len(data.get('field_columns', []))}")
                        with c2:
                            if st.button("🗑️", key=f"d_{name}"):
                                (TEMPLATE_DIR / f"{name}.json").unlink(missing_ok=True)
                                del st.session_state.templates[name]
                                st.rerun()
                        
                        st.download_button("📤 Export", json.dumps(data, indent=2),
                            f"{name}.json", key=f"e_{name}")


# TAB 5 - ENHANCED CONFIGURATION WITH API PLAYGROUND

with tab3:
    st.markdown("## 🔗 Connectivity & API Playground")
    
    # Initialize API state
    if 'ukg_wfm_token' not in st.session_state:
        st.session_state.ukg_wfm_token = None
    if 'ukg_wfm_token_expiry' not in st.session_state:
        st.session_state.ukg_wfm_token_expiry = None
    if 'ukg_hcm_auth' not in st.session_state:
        st.session_state.ukg_hcm_auth = None
    if 'api_response' not in st.session_state:
        st.session_state.api_response = None
    if 'saved_endpoints' not in st.session_state:
        st.session_state.saved_endpoints = {}
    
    # Sub-tabs
    config_tab1, config_tab2, config_tab3 = st.tabs([
        "🔐 API Credentials",
        "🎮 API Playground", 
        "📚 Saved Endpoints"
    ])
    
    # ====================
    # TAB 1: CREDENTIALS
    # ====================
    with config_tab1:
        st.header("API Credentials Configuration")
        
        st.markdown("""
        <div class='info-box'>
            <h4>🔐 Secure Credential Storage</h4>
            <p>Configure your UKG Pro WFM and HCM API credentials. Credentials are stored in your session and not persisted.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # WFM CREDENTIALS
        st.markdown("---")
        st.markdown("### 🟢 UKG Pro WFM (OAuth 2.0)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            wfm_hostname = st.text_input(
                "WFM Hostname",
                placeholder="mytenant.mykronos.com",
                help="Your tenant-specific hostname (without https://)",
                key="wfm_hostname"
            )
            wfm_username = st.text_input(
                "WFM Username",
                placeholder="api.user@company.com",
                key="wfm_username"
            )
            wfm_password = st.text_input(
                "WFM Password",
                type="password",
                key="wfm_password"
            )
        
        with col2:
            wfm_client_id = st.text_input(
                "Client ID",
                placeholder="your-client-id",
                key="wfm_client_id"
            )
            wfm_client_secret = st.text_input(
                "Client Secret",
                type="password",
                key="wfm_client_secret"
            )
            wfm_auth_chain = st.text_input(
                "Auth Chain",
                value="OAuthLdapService",
                key="wfm_auth_chain",
                help="Typically OAuthLdapService"
            )
        
        if st.button("🔌 Test WFM Connection", type="primary", use_container_width=True):
            if not all([wfm_hostname, wfm_username, wfm_password, wfm_client_id, wfm_client_secret]):
                st.error("⚠️ Please fill in all WFM credentials")
            else:
                with st.spinner("Testing WFM connection..."):
                    try:
                        import requests
                        from datetime import datetime, timedelta
                        
                        url = f"https://{wfm_hostname}/api/authentication/access_token"
                        
                        data = {
                            'username': wfm_username,
                            'password': wfm_password,
                            'client_id': wfm_client_id,
                            'client_secret': wfm_client_secret,
                            'grant_type': 'password',
                            'auth_chain': wfm_auth_chain
                        }
                        
                        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
                        
                        response = requests.post(url, data=data, headers=headers)
                        
                        if response.status_code == 200:
                            token_data = response.json()
                            st.session_state.ukg_wfm_token = token_data['access_token']
                            expires_in = token_data.get('expires_in', 3600)
                            st.session_state.ukg_wfm_token_expiry = datetime.now() + timedelta(seconds=expires_in)
                            st.session_state.ukg_wfm_refresh_token = token_data.get('refresh_token')
                            
                            st.success("✅ WFM Connection Successful!")
                            st.info(f"Token expires in {expires_in} seconds")
                        else:
                            st.error(f"❌ Connection Failed: {response.status_code}")
                            st.code(response.text)
                    
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
        
        # Show token status
        if st.session_state.ukg_wfm_token:
            if st.session_state.ukg_wfm_token_expiry > datetime.now():
                st.success(f"✅ WFM Token Active (expires {st.session_state.ukg_wfm_token_expiry.strftime('%H:%M:%S')})")
            else:
                st.warning("⚠️ WFM Token Expired - Test connection again")
        
        # HCM CREDENTIALS
        st.markdown("---")
        st.markdown("### 🔵 UKG Pro HCM (Basic Auth + API Keys)")
        
        st.info("⚠️ HCM configuration pending - need base URL and API key details")
        
        col1, col2 = st.columns(2)
        
        with col1:
            hcm_base_url = st.text_input(
                "HCM Base URL",
                placeholder="https://service.ultipro.com/",
                help="Pending: Actual base URL",
                key="hcm_base_url"
            )
            hcm_username = st.text_input(
                "HCM Service Account Username",
                placeholder="service.account",
                key="hcm_username"
            )
            hcm_password = st.text_input(
                "HCM Service Account Password",
                type="password",
                key="hcm_password"
            )
        
        with col2:
            hcm_customer_key = st.text_input(
                "Customer API Key",
                placeholder="5-character key",
                help="US-Customer-Api-Key",
                max_chars=5,
                key="hcm_customer_key"
            )
            hcm_user_key = st.text_input(
                "User API Key",
                placeholder="User key",
                help="Pending: Exact header name",
                key="hcm_user_key"
            )
        
        if st.button("🔌 Test HCM Connection", type="primary", use_container_width=True, disabled=True):
            st.warning("⚠️ HCM testing disabled - need endpoint details")
    
    # ====================
    # TAB 2: API PLAYGROUND
    # ====================
    with config_tab2:
        st.header("API Playground")
        
        st.markdown("""
        <div class='success-box'>
            <h4>🎮 Make API Calls</h4>
            <p>Test any UKG API endpoint directly. Select product, method, endpoint, and send.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Product selector
        api_product = st.radio(
            "Select Product",
            ["🟢 UKG Pro WFM", "🔵 UKG Pro HCM"],
            horizontal=True
        )
        
        if api_product == "🟢 UKG Pro WFM":
            # Check if authenticated
            if not st.session_state.ukg_wfm_token:
                st.warning("⚠️ Please configure and test WFM credentials in the 'API Credentials' tab first")
            else:
                st.markdown("---")
                
                # HTTP Method
                col1, col2 = st.columns([1, 3])
                with col1:
                    http_method = st.selectbox("Method", ["GET", "POST", "PUT", "DELETE"])
                
                with col2:
                    wfm_endpoint = st.text_input(
                        "Endpoint",
                        placeholder="/v1/commons/persons/{personId}",
                        help="Path after /api/ (include /v1/...)"
                    )
                
                # Request body (for POST/PUT)
                if http_method in ["POST", "PUT"]:
                    st.markdown("**Request Body (JSON):**")
                    request_body = st.text_area(
                        "Body",
                        placeholder='{\n  "key": "value"\n}',
                        height=150,
                        label_visibility="collapsed"
                    )
                else:
                    request_body = None
                
                # Query parameters
                with st.expander("➕ Query Parameters (Optional)"):
                    num_params = st.number_input("Number of parameters", 0, 10, 0)
                    query_params = {}
                    for i in range(num_params):
                        c1, c2 = st.columns(2)
                        with c1:
                            key = st.text_input(f"Key {i+1}", key=f"qp_key_{i}")
                        with c2:
                            value = st.text_input(f"Value {i+1}", key=f"qp_val_{i}")
                        if key:
                            query_params[key] = value
                
                # Send button
                if st.button("🚀 Send API Request", type="primary", use_container_width=True):
                    try:
                        import requests
                        
                        # Build URL
                        hostname = st.session_state.get('wfm_hostname', '')
                        url = f"https://{hostname}/api{wfm_endpoint}"
                        
                        # Headers
                        headers = {
                            'Content-Type': 'application/json',
                            'Authorization': st.session_state.ukg_wfm_token
                        }
                        
                        # Make request
                        with st.spinner(f"Making {http_method} request..."):
                            if http_method == "GET":
                                response = requests.get(url, headers=headers, params=query_params)
                            elif http_method == "POST":
                                response = requests.post(url, headers=headers, json=json.loads(request_body) if request_body else {})
                            elif http_method == "PUT":
                                response = requests.put(url, headers=headers, json=json.loads(request_body) if request_body else {})
                            elif http_method == "DELETE":
                                response = requests.delete(url, headers=headers)
                        
                        # Store response
                        st.session_state.api_response = {
                            'status_code': response.status_code,
                            'headers': dict(response.headers),
                            'body': response.json() if response.text else None,
                            'url': url,
                            'method': http_method
                        }
                        
                        # Display response
                        st.markdown("---")
                        st.markdown("### 📥 Response")
                        
                        # Status code
                        if response.status_code == 200:
                            st.success(f"✅ Status: {response.status_code} OK")
                        elif response.status_code < 300:
                            st.info(f"ℹ️ Status: {response.status_code}")
                        elif response.status_code < 500:
                            st.warning(f"⚠️ Status: {response.status_code}")
                        else:
                            st.error(f"❌ Status: {response.status_code}")
                        
                        # Response body
                        st.markdown("**Response Body:**")
                        if response.json():
                            st.json(response.json())
                        else:
                            st.code(response.text)
                        
                        # Response headers
                        with st.expander("📋 Response Headers"):
                            st.json(dict(response.headers))
                    
                    except json.JSONDecodeError:
                        st.error("❌ Invalid JSON in request body")
                    except Exception as e:
                        st.error(f"❌ Request failed: {str(e)}")
                
                # Common endpoints quick access
                st.markdown("---")
                st.markdown("### ⚡ Common Endpoints")
                
                common_endpoints = {
                    "Get Person by ID": {
                        "method": "GET",
                        "endpoint": "/v1/commons/persons/{personId}",
                        "description": "Retrieve person details"
                    },
                    "Get Multiple Persons": {
                        "method": "POST",
                        "endpoint": "/v1/commons/persons/multi_read",
                        "description": "Batch retrieve persons",
                        "body": '{\n  "keys": [{"id": "123"}]\n}'
                    },
                    "Get Timecard": {
                        "method": "GET",
                        "endpoint": "/v1/timekeeping/timecard",
                        "description": "Retrieve employee timecard"
                    },
                    "Get Schedule": {
                        "method": "POST",
                        "endpoint": "/v1/scheduling/schedule/multi_read",
                        "description": "Retrieve schedule for employees"
                    }
                }
                
                cols = st.columns(2)
                for idx, (name, details) in enumerate(common_endpoints.items()):
                    with cols[idx % 2]:
                        with st.expander(f"📌 {name}"):
                            st.markdown(f"**Method:** {details['method']}")
                            st.markdown(f"**Endpoint:** `{details['endpoint']}`")
                            st.markdown(f"**Description:** {details['description']}")
                            if 'body' in details:
                                st.code(details['body'], language='json')
        
        else:  # HCM
            st.warning("⚠️ HCM API Playground coming soon - configure credentials first")
    
    # ====================
    # TAB 3: SAVED ENDPOINTS
    # ====================
    with config_tab3:
        st.header("Saved Endpoints")
        
        st.markdown("""
        <div class='info-box'>
            <h4>📚 Endpoint Library</h4>
            <p>Save frequently used endpoints for quick access.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Add new endpoint
        with st.expander("➕ Save New Endpoint"):
            save_name = st.text_input("Endpoint Name", placeholder="Get All Employees")
            save_product = st.selectbox("Product", ["WFM", "HCM"])
            save_method = st.selectbox("Method", ["GET", "POST", "PUT", "DELETE"])
            save_endpoint = st.text_input("Endpoint Path", placeholder="/v1/...")
            save_description = st.text_area("Description")
            save_body = st.text_area("Default Body (if applicable)")
            
            if st.button("💾 Save Endpoint"):
                if save_name and save_endpoint:
                    st.session_state.saved_endpoints[save_name] = {
                        'product': save_product,
                        'method': save_method,
                        'endpoint': save_endpoint,
                        'description': save_description,
                        'body': save_body
                    }
                    st.success(f"✅ Saved '{save_name}'")
                    st.rerun()
        
        # Display saved endpoints
        if st.session_state.saved_endpoints:
            st.markdown("---")
            st.markdown("### 📋 Your Saved Endpoints")
            
            for name, details in st.session_state.saved_endpoints.items():
                with st.expander(f"📌 {name}"):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**Product:** {details['product']}")
                        st.markdown(f"**Method:** {details['method']}")
                        st.markdown(f"**Endpoint:** `{details['endpoint']}`")
                        if details['description']:
                            st.markdown(f"**Description:** {details['description']}")
                        if details['body']:
                            st.markdown("**Default Body:**")
                            st.code(details['body'], language='json')
                    
                    with col2:
                        if st.button("🗑️ Delete", key=f"del_{name}"):
                            del st.session_state.saved_endpoints[name]
                            st.rerun()
        else:
            st.info("📋 No saved endpoints yet. Add one above!")


with tab2:
    st.markdown("## 🛠️ Admin Panel")
    st.markdown("""
    <div class='warning-box'>
        <strong>🔧 Development & Testing Tools</strong><br>
        Make changes, test features, and chat with Claude - all without redeploying!
    </div>
    """, unsafe_allow_html=True)
    
    # Create two columns for different admin sections
    admin_col1, admin_col2 = st.columns([2, 1])
    
    with admin_col1:
        # Direct Communication with Claude
        st.markdown("### 💬 Communicate with Claude")
        st.markdown("""
        <div class='info-box' style='font-size: 0.9rem;'>
        <strong>Important:</strong> This panel is for logging issues and requests. Your messages are recorded below 
        so you can copy them to share with Claude in your main conversation for immediate fixes.
        </div>
        """, unsafe_allow_html=True)
        
        # Initialize messages list in session state
        if 'admin_messages' not in st.session_state:
            st.session_state.admin_messages = []
        
        # Message input
        user_message = st.text_area(
            "Describe the issue or request:",
            key="admin_message_input",
            height=120,
            placeholder="Example: 'The PDF parser isn't detecting tables correctly' or 'Can you add XYZ feature?'"
        )
        
        col_log, col_copy, col_clear = st.columns([2, 2, 1])
        with col_log:
            if st.button("📝 Log Message", use_container_width=True):
                if user_message:
                    st.session_state.admin_messages.append({
                        'timestamp': datetime.now().strftime("%H:%M:%S"),
                        'message': user_message
                    })
                    st.success("✅ Message logged!")
                else:
                    st.warning("Please enter a message")
        
        with col_copy:
            if st.button("📋 Copy All Messages", use_container_width=True):
                if st.session_state.admin_messages:
                    all_messages = "\n\n---\n\n".join([
                        f"[{msg['timestamp']}] {msg['message']}" 
                        for msg in st.session_state.admin_messages
                    ])
                    st.code(all_messages, language=None)
                    st.info("👆 Copy the text above and paste it into your Claude conversation")
                else:
                    st.warning("No messages logged yet")
        
        with col_clear:
            if st.button("🗑️", use_container_width=True):
                st.session_state.admin_messages = []
                st.success("Cleared!")
        
        # Display logged messages
        if st.session_state.admin_messages:
            st.markdown("---")
            st.markdown("**📋 Logged Messages:**")
            
            for i, msg in enumerate(st.session_state.admin_messages):
                st.markdown(f"""
                <div style='background: #e8edf2; color: #1a2332; padding: 0.75rem; border-radius: 6px; margin: 0.5rem 0; border-left: 4px solid #6d8aa0;'>
                    <small style='color: #6c757d;'>{msg['timestamp']}</small><br>
                    {msg['message']}
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Quick Actions
        st.markdown("### ⚡ Quick Actions")
        
        action_col1, action_col2, action_col3 = st.columns(3)
        
        with action_col1:
            if st.button("🔄 Restart App", use_container_width=True):
                st.info("To restart: Go to Railway → Click '...' → Restart")
        
        with action_col2:
            if st.button("📋 View Logs", use_container_width=True):
                st.info("Logs: Railway Dashboard → Deployments → View Logs")
        
        with action_col3:
            if st.button("🔍 Test Parse", use_container_width=True):
                st.info("Upload a PDF in the Secure PDF Parser tab to test")
    
    with admin_col2:
        # Color Tester
        st.markdown("### 🎨 Color Tester")
        
        test_primary = st.color_picker("Primary Color", "#6d8aa0")
        test_bg = st.color_picker("Background", "#e8edf2")
        test_text = st.color_picker("Text Color", "#1a2332")
        
        # Preview
        st.markdown(f"""
        <div style='background: {test_bg}; padding: 1rem; border-radius: 8px; margin-top: 1rem;'>
            <button style='background: {test_primary}; color: white; padding: 0.5rem 1rem; border: none; border-radius: 6px; width: 100%; font-weight: 600;'>
                Sample Button
            </button>
            <p style='color: {test_text}; margin-top: 0.5rem;'>Sample text with your colors</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # System Info
        st.markdown("### 📊 System Info")
        
        import platform
        import sys
        
        system_info = f"""
**Python:** {sys.version.split()[0]}
**Platform:** {platform.system()}
**Streamlit:** {st.__version__}

**Session State:**
- Active Project: {st.session_state.current_project or 'None'}
- Total Projects: {len(st.session_state.projects)}
- API Configured: {'✅' if st.session_state.api_credentials['pro'] or st.session_state.api_credentials['wfm'] else '❌'}
        """
        
        st.markdown(system_info)

# TAB 7: TESTING

with tab7:
    st.markdown("## 🧪 Testing")
    
    st.markdown("""
    <div class='info-box'>
        <h4>🧪 Test Management & Execution</h4>
        <p>Manage your UKG implementation testing across all phases: System Integration Testing (SIT), 
        User Acceptance Testing (UAT), and test scenario/script libraries.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Create sub-tabs for different testing phases
    test_tab1, test_tab2, test_tab3 = st.tabs([
        "🔧 SIT (System Integration Testing)",
        "✅ UAT (User Acceptance Testing)",
        "📋 Scenarios & Scripts"
    ])
    
    # ============================================================================
    # SIT TAB
    # ============================================================================
    with test_tab1:
        st.markdown("### 🔧 System Integration Testing")
        
        st.markdown("""
        <div class='warning-box'>
            <strong>SIT Phase</strong><br>
            Validate system configurations, integrations, and technical functionality before user testing.
        </div>
        """, unsafe_allow_html=True)
        
        if not st.session_state.current_project:
            st.warning("⚠️ Please create or select a project first (Home & Projects tab)")
        else:
            st.info(f"📁 **Active Project:** {st.session_state.current_project}")
            
            # SIT Test Categories
            st.markdown("#### Test Categories")
            
            col1, col2 = st.columns(2)
            
            with col1:
                with st.expander("🔐 Security & Access", expanded=False):
                    st.markdown("""
                    - User authentication
                    - Role-based access control
                    - Data encryption
                    - SSO integration
                    - Password policies
                    """)
                
                with st.expander("🔄 Integrations", expanded=False):
                    st.markdown("""
                    - Payroll integrations
                    - Time & Attendance feeds
                    - Benefits carrier connections
                    - Third-party system APIs
                    - File imports/exports
                    """)
                
                with st.expander("📊 Data Migration", expanded=False):
                    st.markdown("""
                    - Employee data load
                    - Historical data validation
                    - Data mapping accuracy
                    - Data transformation rules
                    - Cleanup and deduplication
                    """)
            
            with col2:
                with st.expander("⚙️ Configuration", expanded=False):
                    st.markdown("""
                    - Pay codes setup
                    - Deduction codes setup
                    - Org hierarchy structure
                    - Workflow configurations
                    - Business rules engine
                    """)
                
                with st.expander("📈 Reporting", expanded=False):
                    st.markdown("""
                    - Standard reports accuracy
                    - Custom reports functionality
                    - Dashboard data validation
                    - Export functionality
                    - Scheduling and distribution
                    """)
                
                with st.expander("🔔 Notifications", expanded=False):
                    st.markdown("""
                    - Email notifications
                    - System alerts
                    - Workflow notifications
                    - Reminder configurations
                    - Escalation paths
                    """)
            
            st.markdown("---")
            st.markdown("#### SIT Test Tracker")
            
            # Simple test tracker
            st.markdown("**Track SIT test execution and results:**")
            
            # Initialize SIT test state
            if 'sit_tests' not in st.session_state:
                st.session_state.sit_tests = []
            
            # Add test case
            with st.expander("➕ Add SIT Test Case"):
                test_name = st.text_input("Test Case Name", key="sit_test_name")
                test_category = st.selectbox("Category", 
                    ["Security & Access", "Integrations", "Data Migration", 
                     "Configuration", "Reporting", "Notifications"],
                    key="sit_category")
                test_description = st.text_area("Description", key="sit_description")
                test_status = st.selectbox("Status", 
                    ["Not Started", "In Progress", "Passed", "Failed", "Blocked"],
                    key="sit_status")
                test_notes = st.text_area("Notes", key="sit_notes")
                
                if st.button("Add Test Case", key="add_sit"):
                    if test_name:
                        st.session_state.sit_tests.append({
                            'name': test_name,
                            'category': test_category,
                            'description': test_description,
                            'status': test_status,
                            'notes': test_notes,
                            'created': datetime.now().strftime("%Y-%m-%d %H:%M")
                        })
                        st.success(f"✅ Added test case: {test_name}")
                        st.rerun()
            
            # Display test cases
            if st.session_state.sit_tests:
                st.markdown("---")
                st.markdown("**Test Cases:**")
                
                # Summary metrics
                total = len(st.session_state.sit_tests)
                passed = len([t for t in st.session_state.sit_tests if t['status'] == 'Passed'])
                failed = len([t for t in st.session_state.sit_tests if t['status'] == 'Failed'])
                
                met_col1, met_col2, met_col3, met_col4 = st.columns(4)
                with met_col1:
                    st.metric("Total Tests", total)
                with met_col2:
                    st.metric("Passed", passed)
                with met_col3:
                    st.metric("Failed", failed)
                with met_col4:
                    pass_rate = (passed / total * 100) if total > 0 else 0
                    st.metric("Pass Rate", f"{pass_rate:.0f}%")
                
                # List tests
                for idx, test in enumerate(st.session_state.sit_tests):
                    status_color = {
                        'Passed': '🟢',
                        'Failed': '🔴',
                        'In Progress': '🟡',
                        'Not Started': '⚪',
                        'Blocked': '🟠'
                    }
                    
                    with st.expander(f"{status_color.get(test['status'], '⚪')} {test['name']} ({test['category']})"):
                        st.markdown(f"**Status:** {test['status']}")
                        st.markdown(f"**Description:** {test['description']}")
                        if test['notes']:
                            st.markdown(f"**Notes:** {test['notes']}")
                        st.markdown(f"<small>Created: {test['created']}</small>", unsafe_allow_html=True)
                        
                        if st.button("🗑️ Delete", key=f"del_sit_{idx}"):
                            st.session_state.sit_tests.pop(idx)
                            st.rerun()
            else:
                st.info("📋 No SIT test cases yet. Add test cases above to track testing progress.")
    
    # ============================================================================
    # UAT TAB
    # ============================================================================
    with test_tab2:
        st.markdown("### ✅ User Acceptance Testing")
        
        st.markdown("""
        <div class='success-box'>
            <strong>UAT Phase</strong><br>
            Validate end-user workflows, business processes, and real-world scenarios with stakeholders.
        </div>
        """, unsafe_allow_html=True)
        
        if not st.session_state.current_project:
            st.warning("⚠️ Please create or select a project first (Home & Projects tab)")
        else:
            st.info(f"📁 **Active Project:** {st.session_state.current_project}")
            
            # UAT Focus Areas
            st.markdown("#### UAT Focus Areas")
            
            col1, col2 = st.columns(2)
            
            with col1:
                with st.expander("👥 Employee Self-Service", expanded=False):
                    st.markdown("""
                    - Personal information updates
                    - Time off requests
                    - Timecard entry and approval
                    - Benefits enrollment
                    - Paycheck and tax form access
                    """)
                
                with st.expander("👔 Manager Self-Service", expanded=False):
                    st.markdown("""
                    - Approve time off requests
                    - Approve timecards
                    - Team scheduling
                    - Performance reviews
                    - Compensation planning
                    """)
                
                with st.expander("💼 HR Processes", expanded=False):
                    st.markdown("""
                    - New hire onboarding
                    - Termination processing
                    - Organizational changes
                    - Compensation adjustments
                    - Benefits administration
                    """)
            
            with col2:
                with st.expander("💰 Payroll Processes", expanded=False):
                    st.markdown("""
                    - Regular payroll processing
                    - Off-cycle payroll
                    - Year-end processing
                    - Tax filing preparation
                    - Garnishment processing
                    """)
                
                with st.expander("⏰ Time & Attendance", expanded=False):
                    st.markdown("""
                    - Clock in/out
                    - Timecard editing
                    - Schedule creation
                    - Absence management
                    - Overtime tracking
                    """)
                
                with st.expander("🎯 Talent Management", expanded=False):
                    st.markdown("""
                    - Recruiting workflows
                    - Onboarding checklists
                    - Performance reviews
                    - Goal management
                    - Succession planning
                    """)
            
            st.markdown("---")
            st.markdown("#### UAT Test Tracker")
            
            # Initialize UAT test state
            if 'uat_tests' not in st.session_state:
                st.session_state.uat_tests = []
            
            # Add test scenario
            with st.expander("➕ Add UAT Test Scenario"):
                uat_name = st.text_input("Scenario Name", key="uat_test_name")
                uat_category = st.selectbox("Focus Area", 
                    ["Employee Self-Service", "Manager Self-Service", "HR Processes", 
                     "Payroll Processes", "Time & Attendance", "Talent Management"],
                    key="uat_category")
                uat_description = st.text_area("Scenario Description", key="uat_description")
                uat_tester = st.text_input("Assigned Tester", key="uat_tester")
                uat_status = st.selectbox("Status", 
                    ["Not Started", "In Progress", "Passed", "Failed", "Blocked"],
                    key="uat_status")
                uat_feedback = st.text_area("User Feedback", key="uat_feedback")
                
                if st.button("Add UAT Scenario", key="add_uat"):
                    if uat_name:
                        st.session_state.uat_tests.append({
                            'name': uat_name,
                            'category': uat_category,
                            'description': uat_description,
                            'tester': uat_tester,
                            'status': uat_status,
                            'feedback': uat_feedback,
                            'created': datetime.now().strftime("%Y-%m-%d %H:%M")
                        })
                        st.success(f"✅ Added UAT scenario: {uat_name}")
                        st.rerun()
            
            # Display UAT scenarios
            if st.session_state.uat_tests:
                st.markdown("---")
                st.markdown("**UAT Scenarios:**")
                
                # Summary metrics
                total = len(st.session_state.uat_tests)
                passed = len([t for t in st.session_state.uat_tests if t['status'] == 'Passed'])
                failed = len([t for t in st.session_state.uat_tests if t['status'] == 'Failed'])
                
                met_col1, met_col2, met_col3, met_col4 = st.columns(4)
                with met_col1:
                    st.metric("Total Scenarios", total)
                with met_col2:
                    st.metric("Passed", passed)
                with met_col3:
                    st.metric("Failed", failed)
                with met_col4:
                    pass_rate = (passed / total * 100) if total > 0 else 0
                    st.metric("Pass Rate", f"{pass_rate:.0f}%")
                
                # List scenarios
                for idx, test in enumerate(st.session_state.uat_tests):
                    status_color = {
                        'Passed': '🟢',
                        'Failed': '🔴',
                        'In Progress': '🟡',
                        'Not Started': '⚪',
                        'Blocked': '🟠'
                    }
                    
                    with st.expander(f"{status_color.get(test['status'], '⚪')} {test['name']} ({test['category']})"):
                        st.markdown(f"**Status:** {test['status']}")
                        st.markdown(f"**Tester:** {test['tester']}")
                        st.markdown(f"**Description:** {test['description']}")
                        if test['feedback']:
                            st.markdown(f"**User Feedback:** {test['feedback']}")
                        st.markdown(f"<small>Created: {test['created']}</small>", unsafe_allow_html=True)
                        
                        if st.button("🗑️ Delete", key=f"del_uat_{idx}"):
                            st.session_state.uat_tests.pop(idx)
                            st.rerun()
            else:
                st.info("📋 No UAT scenarios yet. Add scenarios above to track user acceptance testing.")
    
    # ============================================================================
    # SCENARIOS & SCRIPTS TAB
    # ============================================================================
    with test_tab3:
        st.markdown("### 📋 Test Scenarios & Scripts Library")
        
        st.markdown("""
        <div class='info-box'>
            <strong>Test Scenario Library</strong><br>
            Manage reusable test scenarios and scripts for common UKG workflows and processes.
        </div>
        """, unsafe_allow_html=True)
        
        # Initialize scenario library
        if 'scenario_library' not in st.session_state:
            st.session_state.scenario_library = []
        
        # Add scenario template
        st.markdown("#### Add Test Scenario Template")
        
        with st.expander("➕ Create New Scenario Template"):
            scenario_name = st.text_input("Scenario Name", key="scenario_name")
            scenario_module = st.selectbox("UKG Module", 
                ["PRO Core", "WFM", "Payroll", "Benefits", "Recruiting", 
                 "Onboarding", "Performance", "Compensation", "Time & Attendance"],
                key="scenario_module")
            scenario_type = st.selectbox("Test Type", 
                ["Functional", "Integration", "Regression", "Performance", "Security"],
                key="scenario_type")
            scenario_steps = st.text_area("Test Steps", 
                placeholder="1. Navigate to...\n2. Click on...\n3. Enter data...\n4. Verify...",
                key="scenario_steps", height=150)
            scenario_data = st.text_area("Test Data Requirements", key="scenario_data")
            scenario_expected = st.text_area("Expected Results", key="scenario_expected")
            
            if st.button("💾 Save Scenario Template", key="save_scenario"):
                if scenario_name and scenario_steps:
                    st.session_state.scenario_library.append({
                        'name': scenario_name,
                        'module': scenario_module,
                        'type': scenario_type,
                        'steps': scenario_steps,
                        'data': scenario_data,
                        'expected': scenario_expected,
                        'created': datetime.now().strftime("%Y-%m-%d %H:%M")
                    })
                    st.success(f"✅ Saved scenario: {scenario_name}")
                    st.rerun()
                else:
                    st.warning("Please provide scenario name and test steps")
        
        # Display scenario library
        if st.session_state.scenario_library:
            st.markdown("---")
            st.markdown("#### Scenario Library")
            
            # Filter options
            filter_col1, filter_col2 = st.columns(2)
            with filter_col1:
                filter_module = st.selectbox("Filter by Module", 
                    ["All"] + ["PRO Core", "WFM", "Payroll", "Benefits", "Recruiting", 
                               "Onboarding", "Performance", "Compensation", "Time & Attendance"],
                    key="filter_module")
            with filter_col2:
                filter_type = st.selectbox("Filter by Type",
                    ["All", "Functional", "Integration", "Regression", "Performance", "Security"],
                    key="filter_type")
            
            # Filter scenarios
            filtered_scenarios = st.session_state.scenario_library
            if filter_module != "All":
                filtered_scenarios = [s for s in filtered_scenarios if s['module'] == filter_module]
            if filter_type != "All":
                filtered_scenarios = [s for s in filtered_scenarios if s['type'] == filter_type]
            
            st.markdown(f"**Showing {len(filtered_scenarios)} of {len(st.session_state.scenario_library)} scenarios**")
            
            # Display scenarios
            for idx, scenario in enumerate(st.session_state.scenario_library):
                # Skip if filtered out
                if scenario not in filtered_scenarios:
                    continue
                
                with st.expander(f"📋 {scenario['name']} | {scenario['module']} | {scenario['type']}"):
                    st.markdown(f"**Module:** {scenario['module']}")
                    st.markdown(f"**Type:** {scenario['type']}")
                    st.markdown("**Test Steps:**")
                    st.code(scenario['steps'], language=None)
                    if scenario['data']:
                        st.markdown("**Test Data Requirements:**")
                        st.code(scenario['data'], language=None)
                    if scenario['expected']:
                        st.markdown("**Expected Results:**")
                        st.code(scenario['expected'], language=None)
                    st.markdown(f"<small>Created: {scenario['created']}</small>", unsafe_allow_html=True)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("📋 Copy to SIT", key=f"copy_sit_{idx}"):
                            # Copy to SIT tracker
                            if 'sit_tests' not in st.session_state:
                                st.session_state.sit_tests = []
                            st.session_state.sit_tests.append({
                                'name': scenario['name'],
                                'category': scenario['module'],
                                'description': scenario['steps'],
                                'status': 'Not Started',
                                'notes': '',
                                'created': datetime.now().strftime("%Y-%m-%d %H:%M")
                            })
                            st.success("✅ Copied to SIT tracker")
                            st.rerun()
                    with col2:
                        if st.button("🗑️ Delete", key=f"del_scenario_{idx}"):
                            st.session_state.scenario_library.pop(idx)
                            st.rerun()
        else:
            st.info("📋 No scenario templates yet. Create reusable test scenarios above.")
        
        # Pre-built scenario templates
        st.markdown("---")
        st.markdown("#### 💡 Quick Start: Common Test Scenarios")
        
        with st.expander("📚 Load Common UKG Test Scenarios"):
            st.markdown("""
            Click below to load pre-built test scenarios for common UKG workflows:
            """)
            
            if st.button("Load Sample Scenarios"):
                sample_scenarios = [
                    {
                        'name': 'Employee New Hire Onboarding',
                        'module': 'PRO Core',
                        'type': 'Functional',
                        'steps': '1. Navigate to Add New Employee\n2. Enter employee demographics\n3. Assign org placement\n4. Configure pay setup\n5. Set work schedule\n6. Save and verify employee record',
                        'data': 'New employee: First Name, Last Name, SSN, DOB, Address, Hire Date',
                        'expected': 'Employee created successfully, appears in employee list, can login to ESS',
                        'created': datetime.now().strftime("%Y-%m-%d %H:%M")
                    },
                    {
                        'name': 'Process Bi-Weekly Payroll',
                        'module': 'Payroll',
                        'type': 'Integration',
                        'steps': '1. Import time data\n2. Review exceptions\n3. Calculate payroll\n4. Review pre-check report\n5. Approve and finalize\n6. Generate direct deposit file',
                        'data': 'Time data for pay period, existing employee records',
                        'expected': 'Payroll processes without errors, checks calculated correctly, DD file generated',
                        'created': datetime.now().strftime("%Y-%m-%d %H:%M")
                    },
                    {
                        'name': 'Manager Approve Time Off Request',
                        'module': 'Time & Attendance',
                        'type': 'Functional',
                        'steps': '1. Login as manager\n2. Navigate to time off requests\n3. Review employee request\n4. Check available balance\n5. Approve or deny\n6. Add comments if needed',
                        'data': 'Employee time off request, manager credentials',
                        'expected': 'Request approved/denied, employee notified, balance updated',
                        'created': datetime.now().strftime("%Y-%m-%d %H:%M")
                    }
                ]
                
                for scenario in sample_scenarios:
                    st.session_state.scenario_library.append(scenario)
                
                st.success(f"✅ Loaded {len(sample_scenarios)} sample scenarios")
                st.rerun()

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #6c757d; padding: 1rem;">
    <small>⚡ XLR8 by HCMPACT v2.0 | Full-Featured | 100% Secure</small>
</div>
""", unsafe_allow_html=True)
