"""
Session State Manager
Initializes advanced RAG handler and all session variables
"""

import streamlit as st
from config import AppConfig


def load_projects_from_supabase():
    """Load all projects from Supabase into session state"""
    if not AppConfig.USE_SUPABASE_PERSISTENCE:
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
        print(f"⚠️ Error loading projects from Supabase: {e}")


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
    
    # Load projects from Supabase on startup
    load_projects_from_supabase()
    
    # API Credentials (not persisted - session only)
    if 'api_credentials' not in st.session_state:
        st.session_state.api_credentials = {'pro': {}, 'wfm': {}}
    
    # PDF Parser - use EnhancedPayrollParser from secure_pdf_parser
    if 'pdf_parser' not in st.session_state:
        from utils.secure_pdf_parser import EnhancedPayrollParser
        st.session_state.pdf_parser = EnhancedPayrollParser()
    
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
        except ImportError:
            # Fallback to basic RAG handler
            try:
                from utils.rag.handler import RAGHandler
                st.session_state.rag_handler = RAGHandler(
                    persist_directory=AppConfig.RAG_PERSIST_DIR
                )
                st.session_state.rag_type = 'basic'
            except:
                st.session_state.rag_handler = None
                st.session_state.rag_type = None
    
    # LLM Configuration (from config)
    if 'llm_endpoint' not in st.session_state:
        st.session_state.llm_endpoint = AppConfig.LLM_ENDPOINT
    
    if 'llm_model' not in st.session_state:
        st.session_state.llm_model = AppConfig.DEFAULT_LLM_MODEL
    
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
