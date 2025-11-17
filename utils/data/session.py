"""
XLR8 Session Management - FIXED VERSION
Properly initializes AdvancedRAGHandler with all chunking strategies
"""

import streamlit as st
from datetime import datetime
import os
from pathlib import Path

# CRITICAL: Import AdvancedRAGHandler (not basic RAGHandler)
try:
    from utils.rag_handler import AdvancedRAGHandler
    RAG_AVAILABLE = True
    RAG_TYPE = 'advanced'
except ImportError:
    try:
        from utils.rag_handler import RAGHandler as AdvancedRAGHandler
        RAG_AVAILABLE = True
        RAG_TYPE = 'basic'
    except ImportError:
        RAG_AVAILABLE = False
        RAG_TYPE = None
        AdvancedRAGHandler = None


def initialize_session():
    """Initialize session state variables"""
    
    # Basic session info
    if 'session_id' not in st.session_state:
        st.session_state.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if 'initialized' not in st.session_state:
        st.session_state.initialized = False
    
    # User preferences
    if 'theme' not in st.session_state:
        st.session_state.theme = 'light'
    
    if 'llm_enabled' not in st.session_state:
        st.session_state.llm_enabled = False
    
    # LLM settings
    if 'ollama_base_url' not in st.session_state:
        st.session_state.ollama_base_url = "http://localhost:11435"
    
    if 'ollama_username' not in st.session_state:
        st.session_state.ollama_username = "xlr8"
    
    if 'ollama_password' not in st.session_state:
        st.session_state.ollama_password = "Argyle76226#"
    
    if 'llm_model' not in st.session_state:
        st.session_state.llm_model = "llama3.2"
    
    if 'llm_temperature' not in st.session_state:
        st.session_state.llm_temperature = 0.7
    
    if 'llm_max_tokens' not in st.session_state:
        st.session_state.llm_max_tokens = 2048
    
    # RAG settings - CRITICAL: Set rag_type to 'advanced'
    if 'rag_type' not in st.session_state:
        st.session_state.rag_type = RAG_TYPE
    
    if 'rag_enabled' not in st.session_state:
        st.session_state.rag_enabled = RAG_AVAILABLE
    
    # Initialize AdvancedRAGHandler if available
    if RAG_AVAILABLE and 'rag_handler' not in st.session_state:
        try:
            # Determine persist directory
            persist_dir = os.path.expanduser("~/.xlr8_chroma")
            
            # Initialize AdvancedRAGHandler
            st.session_state.rag_handler = AdvancedRAGHandler(
                persist_directory=persist_dir
            )
            
            # Verify it's actually the advanced handler
            if hasattr(st.session_state.rag_handler, 'chunking_strategies'):
                st.session_state.rag_type = 'advanced'
                st.session_state.rag_enabled = True
            else:
                st.session_state.rag_type = 'basic'
                st.session_state.rag_enabled = True
                
        except Exception as e:
            st.session_state.rag_enabled = False
            st.session_state.rag_handler = None
            st.session_state.rag_type = None
            print(f"Failed to initialize RAG handler: {e}")
    
    # Project management
    if 'current_project' not in st.session_state:
        st.session_state.current_project = None
    
    if 'projects' not in st.session_state:
        st.session_state.projects = []
    
    # Navigation
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'home'
    
    # UKG connection settings
    if 'ukg_environment' not in st.session_state:
        st.session_state.ukg_environment = None
    
    if 'ukg_connected' not in st.session_state:
        st.session_state.ukg_connected = False
    
    if 'ukg_base_url' not in st.session_state:
        st.session_state.ukg_base_url = ""
    
    if 'ukg_api_key' not in st.session_state:
        st.session_state.ukg_api_key = ""
    
    if 'ukg_username' not in st.session_state:
        st.session_state.ukg_username = ""
    
    if 'ukg_password' not in st.session_state:
        st.session_state.ukg_password = ""
    
    # Analysis cache
    if 'analysis_cache' not in st.session_state:
        st.session_state.analysis_cache = {}
    
    # Chat history
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # Comparison results
    if 'comparison_results' not in st.session_state:
        st.session_state.comparison_results = None
    
    # Export settings
    if 'export_format' not in st.session_state:
        st.session_state.export_format = 'excel'
    
    # Notification settings
    if 'show_notifications' not in st.session_state:
        st.session_state.show_notifications = True
    
    # Advanced features
    if 'debug_mode' not in st.session_state:
        st.session_state.debug_mode = False
    
    if 'auto_save' not in st.session_state:
        st.session_state.auto_save = True
    
    # Mark as initialized
    st.session_state.initialized = True


def reset_session():
    """Reset session state"""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    initialize_session()


def get_session_info():
    """Get current session information"""
    return {
        'session_id': st.session_state.get('session_id', 'unknown'),
        'initialized': st.session_state.get('initialized', False),
        'current_project': st.session_state.get('current_project'),
        'llm_enabled': st.session_state.get('llm_enabled', False),
        'rag_enabled': st.session_state.get('rag_enabled', False),
        'rag_type': st.session_state.get('rag_type', 'unknown'),
        'ukg_connected': st.session_state.get('ukg_connected', False),
        'current_page': st.session_state.get('current_page', 'home')
    }


def update_session_setting(key: str, value):
    """Update a session setting"""
    st.session_state[key] = value


def get_rag_handler():
    """
    Get the RAG handler instance
    Returns None if not available or not initialized
    """
    return st.session_state.get('rag_handler')


def get_rag_status():
    """
    Get detailed RAG status information
    """
    handler = get_rag_handler()
    
    status = {
        'available': RAG_AVAILABLE,
        'enabled': st.session_state.get('rag_enabled', False),
        'type': st.session_state.get('rag_type', 'unknown'),
        'handler_initialized': handler is not None,
        'has_chunking_strategies': False,
        'strategies': []
    }
    
    if handler and hasattr(handler, 'chunking_strategies'):
        status['has_chunking_strategies'] = True
        status['strategies'] = list(handler.chunking_strategies.keys())
    
    return status


def verify_advanced_rag():
    """
    Verify that AdvancedRAGHandler is properly loaded
    Returns True if advanced RAG with chunking strategies is available
    """
    handler = get_rag_handler()
    
    if not handler:
        return False
    
    # Check if it has chunking_strategies attribute (advanced)
    if not hasattr(handler, 'chunking_strategies'):
        return False
    
    # Verify chunking strategies are populated
    if not handler.chunking_strategies or len(handler.chunking_strategies) == 0:
        return False
    
    return True


# Auto-initialize on import
initialize_session()
