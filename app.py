import streamlit as st
import pandas as pd
import PyPDF2
import io
import os
import json
import re
from datetime import datetime
import requests

# Page config
st.set_page_config(page_title="XLR8", layout="wide", initial_sidebar_state="collapsed")

# Initialize session state
if 'projects' not in st.session_state:
    st.session_state.projects = []
if 'current_project' not in st.session_state:
    st.session_state.current_project = None
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = {}
if 'hcmpact_files' not in st.session_state:
    st.session_state.hcmpact_files = {}

# HCMPACT Categories
HCMPACT_CATEGORIES = [
    "PRO Core",
    "WFM",
    "Templates",
    "Prompts",
    "Ben Admin",
    "Recruiting",
    "Onboarding",
    "Performance",
    "Compensation",
    "Succession",
    "Doc Manager",
    "UKG Service Delivery",
    "Project Management",
    "Search & Selection",
    "Change Management",
    "HCMPACT Service Delivery",
    "Industry Research"
]

def extract_text_from_pdf(pdf_file):
    """Extract text from PDF file"""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        st.error(f"Error extracting text from PDF: {str(e)}")
        return None

def call_local_llm(prompt, context="", base_url=None, model=None, username=None, password=None):
    """Call local Ollama LLM with optional authentication"""
    try:
        # Get configuration from session state or parameters
        if base_url is None:
            base_url = st.session_state.get('llm_base_url', 'http://localhost:11434')
        if model is None:
            model = st.session_state.get('llm_model', 'mixtral:8x7b')
        if username is None:
            username = st.session_state.get('llm_username', '')
        if password is None:
            password = st.session_state.get('llm_password', '')
        
        # Build the full prompt with context
        full_prompt = f"{context}\n\n{prompt}" if context else prompt
        
        # Prepare request
        url = f"{base_url}/api/generate"
        payload = {
            "model": model,
            "prompt": full_prompt,
            "stream": False
        }
        
        # Add authentication if credentials provided
        auth = None
        if username and password:
            auth = (username, password)
        
        # Make request
        response = requests.post(url, json=payload, auth=auth, timeout=300)
        response.raise_for_status()
        
        result = response.json()
        return result.get('response', 'No response from LLM')
        
    except requests.exceptions.RequestException as e:
        return f"Error calling LLM: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"

def get_hcmpact_context():
    """Get context from enabled HCMPACT files"""
    context_parts = []
    
    for category, files in st.session_state.hcmpact_files.items():
        for file_info in files:
            if file_info.get('enabled', False):
                context_parts.append(f"=== {category}: {file_info['name']} ===\n{file_info['content']}\n")
    
    if context_parts:
        return "HCMPACT Standards and Best Practices:\n\n" + "\n".join(context_parts)
    return ""

# Main app
st.title("🚀 XLR8 - UKG Implementation Accelerator")

# Create tabs
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🏠 Home & Projects",
    "⚙️ Admin",
    "🔌 Connectivity",
    "📄 AI PDF Parser",
    "📋 Templated Parser",
    "🤖 AI Analysis & Intelligence",
    "🧪 Testing"
])

# TAB 1: Home & Projects
with tab1:
    st.header("Project Management")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Create New Project")
        with st.form("new_project_form"):
            project_name = st.text_input("Project Name")
            project_desc = st.text_area("Description")
            submit = st.form_submit_button("Create Project")
            
            if submit and project_name:
                new_project = {
                    'name': project_name,
                    'description': project_desc,
                    'created': datetime.now().strftime("%Y-%m-%d %H:%M"),
                    'files': []
                }
                st.session_state.projects.append(new_project)
                st.success(f"Project '{project_name}' created!")
    
    with col2:
        st.subheader("Active Project")
        if st.session_state.projects:
            project_names = [p['name'] for p in st.session_state.projects]
            selected = st.selectbox("Select Project", ["None"] + project_names)
            
            if selected != "None":
                st.session_state.current_project = selected
                st.success(f"Active: {selected}")
            else:
                st.session_state.current_project = None
        else:
            st.info("No projects yet")
    
    # Display existing projects
    if st.session_state.projects:
        st.subheader("Existing Projects")
        for project in st.session_state.projects:
            with st.expander(f"📁 {project['name']}"):
                st.write(f"**Description:** {project['description']}")
                st.write(f"**Created:** {project['created']}")
                st.write(f"**Files:** {len(project.get('files', []))}")

# TAB 2: Admin
with tab2:
    st.header("Admin Settings")
    
    admin_tab1, admin_tab2, admin_tab3 = st.tabs(["Users", "Roles", "Audit Log"])
    
    with admin_tab1:
        st.subheader("User Management")
        st.info("User management features coming soon")
    
    with admin_tab2:
        st.subheader("Role Management")
        st.info("Role management features coming soon")
    
    with admin_tab3:
        st.subheader("Audit Log")
        st.info("Audit log features coming soon")

# TAB 3: Connectivity
with tab3:
    st.header("Connectivity Configuration")
    
    config_tab1, config_tab2, config_tab3 = st.tabs(["Local LLM", "UKG APIs", "Other Integrations"])
    
    with config_tab1:
        st.subheader("Local LLM Configuration")
        
        col1, col2 = st.columns(2)
        with col1:
            llm_base_url = st.text_input(
                "Base URL",
                value=st.session_state.get('llm_base_url', 'http://localhost:11434'),
                help="URL of your Ollama server"
            )
            llm_model = st.text_input(
                "Model",
                value=st.session_state.get('llm_model', 'mixtral:8x7b'),
                help="Model name to use"
            )
        
        with col2:
            llm_username = st.text_input(
                "Username (optional)",
                value=st.session_state.get('llm_username', ''),
                help="Username for authenticated endpoints"
            )
            llm_password = st.text_input(
                "Password (optional)",
                value=st.session_state.get('llm_password', ''),
                type="password",
                help="Password for authenticated endpoints"
            )
        
        if st.button("Save & Test LLM Connection"):
            st.session_state.llm_base_url = llm_base_url
            st.session_state.llm_model = llm_model
            st.session_state.llm_username = llm_username
            st.session_state.llm_password = llm_password
            
            with st.spinner("Testing connection..."):
                test_response = call_local_llm(
                    "Say 'Connection successful' if you can read this.",
                    base_url=llm_base_url,
                    model=llm_model,
                    username=llm_username,
                    password=llm_password
                )
                
                if "Error" in test_response:
                    st.error(f"Connection failed: {test_response}")
                else:
                    st.success("✅ LLM Connection successful!")
                    st.info(f"Response: {test_response}")
        
        # Display current config
        if 'llm_base_url' in st.session_state:
            st.divider()
            st.write("**Current Configuration:**")
            st.write(f"- Base URL: `{st.session_state.llm_base_url}`")
            st.write(f"- Model: `{st.session_state.llm_model}`")
            if st.session_state.get('llm_username'):
                st.write(f"- Username: `{st.session_state.llm_username}`")
                st.write(f"- Authentication: ✅ Enabled")
    
    with config_tab2:
        st.subheader("UKG API Configuration")
        st.info("UKG API configuration coming soon")
    
    with config_tab3:
        st.subheader("Other Integrations")
        st.info("Additional integrations coming soon")

# TAB 4: AI PDF Parser
with tab4:
    st.header("AI-Powered PDF Document Parser")
    
    if st.session_state.current_project:
        st.success(f"Active Project: {st.session_state.current_project}")
    else:
        st.warning("⚠️ No active project selected. Go to Home & Projects to create/select a project.")
    
    uploaded_file = st.file_uploader("Upload PDF Document", type=['pdf'], key="ai_pdf_upload")
    
    if uploaded_file:
        st.success(f"Uploaded: {uploaded_file.name}")
        
        # Extract text
        with st.spinner("Extracting text from PDF..."):
            text_content = extract_text_from_pdf(uploaded_file)
        
        if text_content:
            st.info(f"Extracted {len(text_content)} characters")
            
            # Show preview
            with st.expander("View Extracted Text"):
                st.text_area("Content Preview", text_content[:1000] + "...", height=200)
            
            # AI Analysis options
            st.subheader("AI Analysis Options")
            
            analysis_type = st.selectbox(
                "Select Analysis Type",
                ["Document Summary", "Extract Key Information", "Identify Data Fields", "Custom Prompt"]
            )
            
            if analysis_type == "Custom Prompt":
                custom_prompt = st.text_area("Enter your custom prompt")
            
            if st.button("🤖 Analyze with AI"):
                # Get HCMPACT context
                hcmpact_context = get_hcmpact_context()
                
                # Build prompt based on analysis type
                if analysis_type == "Document Summary":
                    prompt = f"Please provide a concise summary of this document:\n\n{text_content[:4000]}"
                elif analysis_type == "Extract Key Information":
                    prompt = f"Extract and list all key information from this document:\n\n{text_content[:4000]}"
                elif analysis_type == "Identify Data Fields":
                    prompt = f"Identify all data fields, columns, and structured information in this document:\n\n{text_content[:4000]}"
                else:
                    prompt = f"{custom_prompt}\n\nDocument content:\n\n{text_content[:4000]}"
                
                with st.spinner("Analyzing with AI..."):
                    result = call_local_llm(prompt, context=hcmpact_context)
                    
                    st.subheader("Analysis Result")
                    st.write(result)
                    
                    # Save to project if active
                    if st.session_state.current_project:
                        if st.button("💾 Save Analysis to Project"):
                            # Find current project
                            for project in st.session_state.projects:
                                if project['name'] == st.session_state.current_project:
                                    if 'analyses' not in project:
                                        project['analyses'] = []
                                    project['analyses'].append({
                                        'file': uploaded_file.name,
                                        'type': analysis_type,
                                        'result': result,
                                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M")
                                    })
                                    st.success("✅ Analysis saved to project!")
                                    break

# TAB 5: Templated Parser
with tab5:
    st.header("Template-Based Document Parser")
    
    if st.session_state.current_project:
        st.success(f"Active Project: {st.session_state.current_project}")
    else:
        st.warning("⚠️ No active project selected. Go to Home & Projects to create/select a project.")
    
    template_type = st.selectbox(
        "Select Document Template",
        ["Pay Code Mapping", "Deduction Mapping", "Org Structure", "Employee Data", "Custom Template"]
    )
    
    st.info(f"Template-based parsing for {template_type} coming soon")
    
    uploaded_file = st.file_uploader("Upload Document for Template Parsing", type=['pdf', 'xlsx', 'csv'], key="template_upload")

# TAB 6: AI Analysis & Intelligence
with tab6:
    st.header("AI Analysis & Intelligence")
    
    analysis_tab1, analysis_tab2, analysis_tab3, analysis_tab4 = st.tabs([
        "Document Intelligence",
        "Data Analysis",
        "Report Generation",
        "Seed HCMPACT LLM"
    ])
    
    with analysis_tab1:
        st.subheader("Document Intelligence")
        st.info("Advanced document analysis features coming soon")
    
    with analysis_tab2:
        st.subheader("Data Analysis")
        st.info("Data analysis features coming soon")
    
    with analysis_tab3:
        st.subheader("Report Generation")
        st.info("Automated report generation coming soon")
    
    with analysis_tab4:
        st.subheader("Seed HCMPACT LLM with Standards")
        st.write("Upload HCMPACT standard documents to enhance AI analysis with industry best practices.")
        
        # Category selection
        selected_category = st.selectbox(
            "Select Document Category",
            HCMPACT_CATEGORIES,
            key="hcmpact_category"
        )
        
        # File uploader
        uploaded_standards = st.file_uploader(
            f"Upload {selected_category} Documents",
            type=['pdf', 'txt', 'md', 'docx'],
            accept_multiple_files=True,
            key=f"hcmpact_upload_{selected_category}"
        )
        
        if uploaded_standards:
            if st.button("Process & Save HCMPACT Documents"):
                with st.spinner("Processing documents..."):
                    # Initialize category if not exists
                    if selected_category not in st.session_state.hcmpact_files:
                        st.session_state.hcmpact_files[selected_category] = []
                    
                    for file in uploaded_standards:
                        # Extract content based on file type
                        if file.name.endswith('.pdf'):
                            content = extract_text_from_pdf(file)
                        else:
                            content = file.read().decode('utf-8', errors='ignore')
                        
                        # Save file info
                        file_info = {
                            'name': file.name,
                            'content': content,
                            'uploaded': datetime.now().strftime("%Y-%m-%d %H:%M"),
                            'enabled': True
                        }
                        st.session_state.hcmpact_files[selected_category].append(file_info)
                    
                    st.success(f"✅ Processed {len(uploaded_standards)} document(s) for {selected_category}")
        
        # Display existing HCMPACT files
        st.divider()
        st.subheader("HCMPACT Knowledge Base")
        
        if st.session_state.hcmpact_files:
            total_files = sum(len(files) for files in st.session_state.hcmpact_files.values())
            enabled_files = sum(
                sum(1 for f in files if f.get('enabled', False))
                for files in st.session_state.hcmpact_files.values()
            )
            
            st.info(f"📚 Total: {total_files} documents | ✅ Enabled: {enabled_files}")
            
            for category, files in st.session_state.hcmpact_files.items():
                if files:
                    with st.expander(f"📁 {category} ({len(files)} documents)"):
                        for idx, file_info in enumerate(files):
                            col1, col2, col3 = st.columns([3, 1, 1])
                            
                            with col1:
                                st.write(f"**{file_info['name']}**")
                                st.caption(f"Uploaded: {file_info['uploaded']}")
                            
                            with col2:
                                enabled = st.checkbox(
                                    "Enabled",
                                    value=file_info.get('enabled', True),
                                    key=f"enable_{category}_{idx}"
                                )
                                file_info['enabled'] = enabled
                            
                            with col3:
                                if st.button("🗑️ Delete", key=f"delete_{category}_{idx}"):
                                    st.session_state.hcmpact_files[category].pop(idx)
                                    st.rerun()
        else:
            st.info("No HCMPACT documents uploaded yet. Upload documents above to get started.")

# TAB 7: Testing
with tab7:
    st.header("Testing & Quality Assurance")
    
    test_tab1, test_tab2, test_tab3 = st.tabs(["SIT", "UAT", "Test Scenarios"])
    
    with test_tab1:
        st.subheader("System Integration Testing (SIT)")
        st.info("SIT features coming soon")
        
        if st.session_state.current_project:
            st.write(f"**Active Project:** {st.session_state.current_project}")
    
    with test_tab2:
        st.subheader("User Acceptance Testing (UAT)")
        st.info("UAT features coming soon")
        
        if st.session_state.current_project:
            st.write(f"**Active Project:** {st.session_state.current_project}")
    
    with test_tab3:
        st.subheader("Test Scenarios")
        st.info("Test scenario management coming soon")
        
        if st.session_state.current_project:
            st.write(f"**Active Project:** {st.session_state.current_project}")

# Footer
st.divider()
st.caption("XLR8 - Accelerating UKG Implementations with AI • Powered by HCMPACT")
