"""
Knowledge Page with Intelligent Parser Integration
Modified to include Intelligent Parser as a new tab
"""

import streamlit as st
from pathlib import Path
import os

# Import RAG handler from correct location
try:
    from utils.rag_handler import RAGHandler
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False

# Import intelligent parser components
try:
    from utils.parsers.intelligent_parser_orchestrator import IntelligentParserOrchestrator
    from utils.parsers.intelligent_parser_ui import render_intelligent_parser
    INTELLIGENT_PARSER_AVAILABLE = True
except ImportError:
    INTELLIGENT_PARSER_AVAILABLE = False


def render_knowledge_page():
    """Render the knowledge management page with Intelligent Parser tab"""
    
    st.title("Knowledge Management")
    
    # For now, just show Intelligent Parser
    # RAG document upload will be handled elsewhere
    render_intelligent_parser_tab()


def render_intelligent_parser_tab():
    """Render intelligent parser interface"""
    
    if not INTELLIGENT_PARSER_AVAILABLE:
        st.error("Intelligent Parser not available")
        st.info("Missing required components. Please ensure parser files are properly deployed.")
        return
    
    try:
        # Initialize orchestrator
        orchestrator = IntelligentParserOrchestrator()
        
        # Render the intelligent parser UI
        render_intelligent_parser(orchestrator)
        
    except Exception as e:
        st.error(f"Failed to initialize intelligent parser: {str(e)}")
        st.info("Please ensure all parser components are properly installed")


# For backward compatibility
def render():
    """Legacy render function"""
    render_knowledge_page()
