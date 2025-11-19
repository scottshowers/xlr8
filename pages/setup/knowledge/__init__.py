"""
Knowledge Page with Intelligent Parser Integration
Modified to include Intelligent Parser as a new tab
"""

import streamlit as st
from utils.rag_interface import add_document, query_knowledge_base
from utils.pdf_parser_interface import parse_pdf_to_excel
from utils.parsers.intelligent_parser_orchestrator import IntelligentParserOrchestrator
from utils.parsers.intelligent_parser_ui import render_intelligent_parser
import os


def render_knowledge_page():
    """Render the knowledge management page with multiple tabs"""
    
    st.title("Knowledge Management")
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs([
        "Document Upload",
        "Knowledge Query", 
        "Intelligent Parser"
    ])
    
    # Tab 1: Document Upload
    with tab1:
        render_document_upload()
    
    # Tab 2: Knowledge Query
    with tab2:
        render_knowledge_query()
    
    # Tab 3: Intelligent Parser
    with tab3:
        render_intelligent_parser_tab()


def render_document_upload():
    """Render document upload interface"""
    st.header("Upload Documents")
    st.markdown("""
    Upload PDF, Word, or text documents to add them to the knowledge base.
    The system will process and index the content for future queries.
    """)
    
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=['pdf', 'docx', 'txt'],
        help="Supported formats: PDF, Word (.docx), Text (.txt)"
    )
    
    if uploaded_file is not None:
        # Display file info
        st.info(f"File: {uploaded_file.name} ({uploaded_file.size} bytes)")
        
        # Add document button
        if st.button("Add to Knowledge Base", type="primary"):
            try:
                with st.spinner("Processing document..."):
                    # Save file temporarily
                    temp_path = f"/tmp/{uploaded_file.name}"
                    with open(temp_path, 'wb') as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # Add to knowledge base
                    result = add_document(temp_path, uploaded_file.name)
                    
                    # Clean up
                    os.remove(temp_path)
                    
                    if result.get('success'):
                        st.success(f"Successfully added {uploaded_file.name} to knowledge base!")
                        st.info(f"Processed {result.get('chunks', 0)} text chunks")
                    else:
                        st.error(f"Failed to add document: {result.get('error', 'Unknown error')}")
                        
            except Exception as e:
                st.error(f"Error processing document: {str(e)}")


def render_knowledge_query():
    """Render knowledge query interface"""
    st.header("Query Knowledge Base")
    st.markdown("""
    Ask questions about the documents in your knowledge base.
    The system will search relevant content and provide answers.
    """)
    
    # Query input
    query = st.text_area(
        "Enter your question:",
        height=100,
        placeholder="Example: What are the key requirements for UKG implementation?"
    )
    
    # Query options
    col1, col2 = st.columns(2)
    with col1:
        max_results = st.slider("Max results", min_value=1, max_value=10, value=5)
    with col2:
        include_sources = st.checkbox("Include source references", value=True)
    
    # Query button
    if st.button("Search Knowledge Base", type="primary", disabled=not query):
        try:
            with st.spinner("Searching knowledge base..."):
                results = query_knowledge_base(
                    query,
                    max_results=max_results,
                    include_sources=include_sources
                )
                
                if results.get('success'):
                    st.success(f"Found {len(results.get('results', []))} relevant results")
                    
                    # Display results
                    for i, result in enumerate(results.get('results', []), 1):
                        with st.expander(f"Result {i} - Relevance: {result.get('score', 0):.2f}"):
                            st.markdown(result.get('content', ''))
                            
                            if include_sources and 'source' in result:
                                st.caption(f"Source: {result['source']}")
                                
                else:
                    st.warning("No results found or knowledge base is empty")
                    
        except Exception as e:
            st.error(f"Error querying knowledge base: {str(e)}")


def render_intelligent_parser_tab():
    """Render intelligent parser interface"""
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
