"""
Session State Manager  
Initializes advanced RAG handler and all session variables
PROPERLY FIXED: Detects when env vars are not set vs empty, proper error handling
"""

import streamlit as st
from config import AppConfig
import os


def load_projects_from_supabase():
    """Load all projects from Supabase into session state"""
    if not AppConfig.USE_SUPABASE_PERSISTENCE:
        return
    
    # Check if Supabase is actually configured
    if not AppConfig.SUPABASE_URL or not AppConfig.SUPABASE_KEY:
        print("⚠️ Supabase persistence enabled but credentials not set - skipping")
        return
    
    try:
        from utils.data.supabase_handler import get_all_projects
        
        # Load projects from Supabase
        projects_list = get_all_projects()
        
        # Convert to dict format for session state
        if projects_list:
            st.session_state.projects = {}
            for project in projects_list:
                project_name = project.get('name')
                if project_name:
                    st.session_state.projects[project_name] = project
        
        print(f"✅ Loaded {len(st.session_state.projects)} projects from Supabase")
        
    except Exception as e:
        print(f"⚠️ Could not connect to Supabase: {e}")
        print("   Continuing with local-only storage...")


def initialize_session_state():
    """
    Initialize all session state variables
    Called once at app startup
    """
    
    # Project Management
    if 'current_project' not in st.session_state:
        st.session_state.current_project = None
    
    if 'projects' not in st.session_state:
        st.session_state.projects = {}
    
    # Load projects from Supabase (with proper error handling)
    try:
        load_projects_from_supabase()
    except Exception as e:
        print(f"⚠️ Supabase initialization failed: {e}")
    
    # API Credentials (not persisted - session only)
    if 'api_credentials' not in st.session_state:
        st.session_state.api_credentials = {'pro': {}, 'wfm': {}}
    
    # PDF Parser - use EnhancedPayrollParser from secure_pdf_parser
    if 'pdf_parser' not in st.session_state:
        try:
            from utils.secure_pdf_parser import EnhancedPayrollParser
            st.session_state.pdf_parser = EnhancedPayrollParser()
        except Exception as e:
            print(f"⚠️ Could not initialize PDF parser: {e}")
            st.session_state.pdf_parser = None
    
    if 'parsed_results' not in st.session_state:
        st.session_state.parsed_results = None
    
    # RAG Handler - use Advanced version if available
    if 'rag_handler' not in st.session_state:
        try:
            # Try to import advanced RAG handler
            from utils.rag.handler import AdvancedRAGHandler
            st.session_state.rag_handler = AdvancedRAGHandler(
                persist_directory=AppConfig.RAG_PERSIST_DIR
            )
            st.session_state.rag_type = 'advanced'
            print("✅ Advanced RAG handler initialized")
        except ImportError:
            # Fallback to basic RAG handler
            try:
                from utils.rag.handler import RAGHandler
                st.session_state.rag_handler = RAGHandler(
                    persist_directory=AppConfig.RAG_PERSIST_DIR
                )
                st.session_state.rag_type = 'basic'
                print("✅ Basic RAG handler initialized")
            except Exception as e:
                print(f"⚠️ Could not initialize RAG handler: {e}")
                st.session_state.rag_handler = None
                st.session_state.rag_type = None
    
    # LLM Configuration - PROPER HANDLING
    # Check if env var is actually set (not just empty)
    if 'llm_endpoint' not in st.session_state:
        endpoint = AppConfig.LLM_ENDPOINT
        
        # Check if actually set in environment
        if 'LLM_ENDPOINT' not in os.environ:
            print("❌ CRITICAL: LLM_ENDPOINT environment variable not set in Railway!")
            print("   Set LLM_ENDPOINT=http://178.156.190.64:11435 in Railway Variables")
            # Don't use fallback - let it fail visibly so user knows to fix it
            endpoint = ""
        elif not endpoint:
            print("❌ CRITICAL: LLM_ENDPOINT is empty string!")
            endpoint = ""
        elif not endpoint.startswith(('http://', 'https://')):
            # Add http:// if missing
            print(f"⚠️ Adding http:// prefix to LLM_ENDPOINT: {endpoint}")
            endpoint = f"http://{endpoint}"
        
        st.session_state.llm_endpoint = endpoint
        if endpoint:
            print(f"✅ LLM endpoint: {endpoint}")
    
    if 'llm_model' not in st.session_state:
        model = AppConfig.LLM_DEFAULT_MODEL
        if not model:
            print("⚠️ LLM_DEFAULT_MODEL not set, using fallback: deepseek-r1:7b")
            model = 'deepseek-r1:7b'
        st.session_state.llm_model = model
        print(f"✅ LLM model: {model}")
    
    if 'llm_username' not in st.session_state:
        username = AppConfig.LLM_USERNAME
        if not username:
            print("⚠️ LLM_USERNAME not set, using fallback: xlr8")
            username = 'xlr8'
        st.session_state.llm_username = username
    
    if 'llm_password' not in st.session_state:
        password = AppConfig.LLM_PASSWORD
        if not password:
            print("⚠️ LLM_PASSWORD not set, using fallback")
            password = 'Argyle76226#'
        st.session_state.llm_password = password
    
    if 'llm_provider' not in st.session_state:
        st.session_state.llm_provider = 'local'
    
    # Chat History
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # Document Library
    if 'doc_library' not in st.session_state:
        st.session_state.doc_library = []
    
    # UKG API Credentials
    if 'ukg_pro_auth' not in st.session_state:
        st.session_state.ukg_pro_auth = None
    
    if 'ukg_wfm_auth' not in st.session_state:
        st.session_state.ukg_wfm_auth = None
    
    if 'ukg_hcm_auth' not in st.session_state:
        st.session_state.ukg_hcm_auth = None
    
    # Configuration validation warning
    if not st.session_state.llm_endpoint:
        print("\n" + "="*60)
        print("⚠️  CONFIGURATION ERROR")
        print("="*60)
        print("LLM_ENDPOINT is not set!")
        print("\nTo fix:")
        print("1. Go to Railway dashboard")
        print("2. Click on your XLR8 service")
        print("3. Go to Variables tab")
        print("4. Add: LLM_ENDPOINT=http://178.156.190.64:11435")
        print("5. Redeploy")
        print("="*60 + "\n")


def get_current_project():
    """Get current active project"""
    return st.session_state.get('current_project')


def set_current_project(project_name):
    """Set current active project"""
    st.session_state.current_project = project_name


def get_project_data(project_name=None):
    """
    Get project data
    
    Args:
        project_name: Specific project or None for current project
    
    Returns:
        Project dictionary or None
    """
    if project_name is None:
        project_name = get_current_project()
    
    if project_name and project_name in st.session_state.projects:
        return st.session_state.projects[project_name]
    
    return None


def save_project_data(project_name, data):
    """
    Save project data
    
    Args:
        project_name: Project name
        data: Project data dictionary
    """
    st.session_state.projects[project_name] = data


def add_to_doc_library(doc_info):
    """
    Add document to library
    
    Args:
        doc_info: Dictionary with doc metadata
    """
    st.session_state.doc_library.append(doc_info)


def get_doc_library():
    """Get all documents in library"""
    return st.session_state.doc_library


def clear_chat_history():
    """Clear chat history"""
    st.session_state.chat_history = []


def add_chat_message(role, content, sources=None):
    """
    Add message to chat history
    
    Args:
        role: 'user' or 'assistant'
        content: Message content
        sources: Optional list of sources used
    """
    message = {
        'role': role,
        'content': content
    }
    
    if sources:
        message['sources'] = sources
    
    st.session_state.chat_history.append(message)


def get_rag_handler():
    """Get RAG handler with type info"""
    return st.session_state.get('rag_handler'), st.session_state.get('rag_type')
