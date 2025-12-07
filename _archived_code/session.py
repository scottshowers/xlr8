"""
XLR8 Session Management - FIXED VERSION
Properly initializes AdvancedRAGHandler with endpoints from environment/session
Uses /data/chromadb to match RAGHandler default - CRITICAL FIX
"""

import streamlit as st
from datetime import datetime
import os
from pathlib import Path

# CRITICAL: Import AdvancedRAGHandler
try:
    from utils.rag_handler import AdvancedRAGHandler
    RAG_AVAILABLE = True
    RAG_TYPE = 'advanced'
except ImportError as e:
    print(f"Warning: Could not import AdvancedRAGHandler: {e}")
    try:
        from utils.rag_handler import RAGHandler as AdvancedRAGHandler
        RAG_AVAILABLE = True
        RAG_TYPE = 'basic'
    except ImportError as e2:
        print(f"Error: Could not import any RAG handler: {e2}")
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
    
    # LLM Provider Selection
    if 'llm_provider' not in st.session_state:
        st.session_state.llm_provider = 'local'  # 'local' or 'claude'
    
    # LLM settings - GET FROM ENVIRONMENT FIRST
    if 'llm_endpoint' not in st.session_state:
        st.session_state.llm_endpoint = os.environ.get('LLM_ENDPOINT', 'http://178.156.190.64:11435')
    
    if 'llm_username' not in st.session_state:
        st.session_state.llm_username = os.environ.get('LLM_USERNAME', 'xlr8')
    
    if 'llm_password' not in st.session_state:
        st.session_state.llm_password = os.environ.get('LLM_PASSWORD', 'Argyle76226#')
    
    if 'llm_model' not in st.session_state:
        st.session_state.llm_model = "deepseek-r1:7b"
    
    if 'llm_temperature' not in st.session_state:
        st.session_state.llm_temperature = 0.7
    
    if 'llm_max_tokens' not in st.session_state:
        st.session_state.llm_max_tokens = 2048
    
    # Claude API Key - PERSISTENT
    if 'claude_api_key' not in st.session_state:
        st.session_state.claude_api_key = os.environ.get('CLAUDE_API_KEY', '')
    
    # RAG settings
    if 'rag_type' not in st.session_state:
        st.session_state.rag_type = RAG_TYPE
    
    if 'rag_enabled' not in st.session_state:
        st.session_state.rag_enabled = RAG_AVAILABLE
    
    # Initialize AdvancedRAGHandler if available - PASS ENDPOINTS
    if RAG_AVAILABLE and 'rag_handler' not in st.session_state:
        try:
            # CRITICAL FIX: Use /data/chromadb to match RAGHandler default
            # This ensures all parts of the app (chat, knowledge page, etc.) 
            # see the same ChromaDB database with the same documents
            persist_dir = "/data/chromadb"
            
            # Get endpoints from session state (already initialized above)
            embed_endpoint = st.session_state.llm_endpoint
            embed_username = st.session_state.llm_username
            embed_password = st.session_state.llm_password
            
            print(f"[RAG] Initializing RAG handler with endpoint: {embed_endpoint}")
            print(f"[RAG] Using persist directory: {persist_dir}")
            
            # Initialize AdvancedRAGHandler WITH ENDPOINTS
            st.session_state.rag_handler = AdvancedRAGHandler(
                persist_directory=persist_dir,
                embed_endpoint=embed_endpoint,
                embed_username=embed_username,
                embed_password=embed_password
            )
            
            # Verify it's the advanced handler
            if hasattr(st.session_state.rag_handler, 'chunking_strategies'):
                st.session_state.rag_type = 'advanced'
                st.session_state.rag_enabled = True
                print(f"[RAG] SUCCESS: Advanced RAG initialized with endpoint: {embed_endpoint}")
                print(f"[RAG] SUCCESS: Using persist directory: {persist_dir}")
            else:
                st.session_state.rag_type = 'basic'
                st.session_state.rag_enabled = True
                print("[RAG] WARNING: Basic RAG initialized (no chunking strategies)")
                
        except Exception as e:
            st.session_state.rag_enabled = False
            st.session_state.rag_handler = None
            st.session_state.rag_type = None
            print(f"[RAG] ERROR: Failed to initialize RAG handler: {e}")
            import traceback
            traceback.print_exc()
    elif not RAG_AVAILABLE:
        print(f"[RAG] WARNING: RAG not available - RAG_AVAILABLE={RAG_AVAILABLE}, RAG_TYPE={RAG_TYPE}")
    elif 'rag_handler' in st.session_state:
        print("[RAG] INFO: RAG handler already initialized")
    
    # Project management
    if 'current_project' not in st.session_state:
        st.session_state.current_project = None
    
    if 'projects' not in st.session_state:
        st.session_state.projects = {}
    
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
    
    # Knowledge base (for backward compatibility)
    if 'knowledge_base' not in st.session_state:
        st.session_state.knowledge_base = []
    
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
        'llm_provider': st.session_state.get('llm_provider', 'local'),
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
        'strategies': [],
        'endpoint': st.session_state.get('llm_endpoint', 'Not configured')
    }
    
    if handler and hasattr(handler, 'chunking_strategies'):
        status['has_chunking_strategies'] = True
        status['strategies'] = list(handler.chunking_strategies.keys())
        status['endpoint'] = handler.embed_endpoint
    
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


# Alias for backward compatibility
initialize_session_state = initialize_session

# DO NOT AUTO-INITIALIZE ON IMPORT
# Let app.py control when initialization happens
