"""
Session State Manager
Initializes advanced RAG handler and all session variables
"""

import streamlit as st
from config import AppConfig


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
        st.session_state.llm_model = AppConfig.LLM_DEFAULT_MODEL
    
    if 'llm_username' not in st.session_state:
        st.session_state.llm_username = AppConfig.LLM_USERNAME
    
    if 'llm_password' not in st.session_state:
        st.session_state.llm_password = AppConfig.LLM_PASSWORD
    
    if 'llm_provider' not in st.session_state:
        st.session_state.llm_provider = 'local'
    
    # Chat History
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # AI Analysis Results
    if 'ai_analysis_results' not in st.session_state:
        st.session_state.ai_analysis_results = None
    
    if 'current_analysis' not in st.session_state:
        st.session_state.current_analysis = None
    
    if 'current_templates' not in st.session_state:
        st.session_state.current_templates = None
    
    # Document Library
    if 'doc_library' not in st.session_state:
        st.session_state.doc_library = []
    
    # Testing Module
    if 'sit_tests' not in st.session_state:
        st.session_state.sit_tests = []
    
    if 'uat_tests' not in st.session_state:
        st.session_state.uat_tests = []
    
    if 'scenario_library' not in st.session_state:
        st.session_state.scenario_library = []
    
    # UKG API tokens (session-based)
    if 'ukg_wfm_token' not in st.session_state:
        st.session_state.ukg_wfm_token = None
    
    if 'ukg_wfm_token_expiry' not in st.session_state:
        st.session_state.ukg_wfm_token_expiry = None
    
    if 'ukg_wfm_refresh_token' not in st.session_state:
        st.session_state.ukg_wfm_refresh_token = None
    
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
