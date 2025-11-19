"""
Complete Knowledge Management Page
4 tabs: Upload | Status | Search | Intelligent Parser
"""

import streamlit as st
from pathlib import Path
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def render_knowledge_page():
    """
    Main render function for knowledge page with 4 tabs.
    """
    st.title("HCMPACT LLM Seeding & Document Management")
    
    # Create tabs
    tabs = st.tabs([
        "📤 Document Upload",
        "📊 Collection Status",
        "🔍 Test Search",
        "🤖 Intelligent Parser"
    ])
    
    # Tab 1: Document Upload
    with tabs[0]:
        render_upload_tab()
    
    # Tab 2: Collection Status
    with tabs[1]:
        render_status_tab()
    
    # Tab 2: Test Search
    with tabs[2]:
        render_search_tab()
    
    # Tab 4: Intelligent Parser
    with tabs[3]:
        render_parser_tab()


def render_upload_tab():
    """
    Tab 1: Document upload with chunking to ChromaDB.
    """
    st.header("Upload Documents to Knowledge Base")
    
    st.markdown("""
    Upload documents to seed the HCMPACT LLM knowledge base. Supported formats:
    - **PDF** - Payroll registers, configuration guides, manuals
    - **DOCX** - Word documents, procedures, templates
    - **TXT/MD** - Text files, markdown documentation
    
    Documents are automatically:
    1. Chunked into searchable segments
    2. Embedded using Ollama
    3. Stored in ChromaDB for RAG
    4. Saved to `/data/uploads/` for parsing
    """)
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Select files to upload",
        type=['pdf', 'docx', 'txt', 'md'],
        accept_multiple_files=True,
        help="Upload one or more documents"
    )
    
    if uploaded_files:
        st.info(f"Selected {len(uploaded_files)} file(s)")
        
        if st.button("Upload and Process", type="primary", use_container_width=True):
            process_uploads(uploaded_files)


def process_uploads(uploaded_files):
    """
    Process uploaded files: save and chunk to ChromaDB.
    """
    from utils.document_processor import DocumentProcessor
    
    processor = DocumentProcessor()
    
    # Create progress containers
    progress_bar = st.progress(0)
    status_text = st.empty()
    results_container = st.empty()
    
    results = []
    total = len(uploaded_files)
    
    for idx, uploaded_file in enumerate(uploaded_files):
        try:
            # Update progress
            progress = (idx + 1) / total
            progress_bar.progress(progress)
            status_text.info(f"Processing {idx + 1}/{total}: {uploaded_file.name}")
            
            # Process document
            result = processor.process_document(
                uploaded_file,
                collection_name='hcmpact_knowledge'
            )
            
            results.append({
                'filename': uploaded_file.name,
                'status': 'success' if result.get('status') == 'success' else 'error',
                'chunks': result.get('num_chunks', 0),
                'message': result.get('message', '')
            })
            
        except Exception as e:
            logger.error(f"Upload error for {uploaded_file.name}: {str(e)}", exc_info=True)
            results.append({
                'filename': uploaded_file.name,
                'status': 'error',
                'chunks': 0,
                'message': str(e)
            })
    
    # Show results
    progress_bar.progress(1.0)
    status_text.empty()
    
    # Summary
    success_count = sum(1 for r in results if r['status'] == 'success')
    total_chunks = sum(r['chunks'] for r in results)
    
    if success_count == total:
        st.success(f"Successfully processed {success_count} file(s) - {total_chunks} chunks created")
    elif success_count > 0:
        st.warning(f"Processed {success_count}/{total} files - {total_chunks} chunks created")
    else:
        st.error("All uploads failed")
    
    # Detailed results
    with results_container.expander("View Details"):
        for result in results:
            if result['status'] == 'success':
                st.write(f"✅ {result['filename']} - {result['chunks']} chunks")
            else:
                st.write(f"❌ {result['filename']} - {result['message']}")


def render_status_tab():
    """
    Tab 2: Show collection status and statistics.
    """
    st.header("Knowledge Base Status")
    
    try:
        from utils.rag_handler import AdvancedRAGHandler
        
        # Initialize RAG handler
        rag = AdvancedRAGHandler(
            ollama_endpoint=st.session_state.get('llm_endpoint', 'http://178.156.190.64:11435'),
            collection_name='hcmpact_knowledge'
        )
        
        # Get collection stats
        collection = rag.client.get_collection('hcmpact_knowledge')
        count = collection.count()
        
        # Metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Chunks", f"{count:,}")
        
        with col2:
            # Count unique documents
            uploads_dir = Path('/data/uploads')
            doc_count = len(list(uploads_dir.glob('*'))) if uploads_dir.exists() else 0
            st.metric("Documents", doc_count)
        
        with col3:
            st.metric("Collection", "hcmpact_knowledge")
        
        # Recent documents
        st.markdown("---")
        st.subheader("Recent Documents")
        
        uploads_dir = Path('/data/uploads')
        if uploads_dir.exists():
            files = sorted(
                uploads_dir.glob('*'),
                key=lambda f: f.stat().st_mtime,
                reverse=True
            )[:10]
            
            if files:
                for f in files:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"📄 {f.name}")
                    with col2:
                        modified = datetime.fromtimestamp(f.stat().st_mtime)
                        st.write(modified.strftime("%Y-%m-%d %H:%M"))
            else:
                st.info("No documents uploaded yet")
        else:
            st.info("Upload directory not found")
        
    except Exception as e:
        st.error(f"Error loading status: {str(e)}")
        logger.error(f"Status error: {str(e)}", exc_info=True)


def render_search_tab():
    """
    Tab 3: Test search functionality.
    """
    st.header("Test Knowledge Base Search")
    
    st.markdown("""
    Test the RAG search capabilities. This searches the embedded chunks in ChromaDB
    and returns the most relevant content.
    """)
    
    # Search input
    query = st.text_input(
        "Enter search query",
        placeholder="e.g., How do I configure absence types?",
        help="Search the knowledge base"
    )
    
    n_results = st.slider("Number of results", 1, 20, 10)
    
    if st.button("Search", type="primary", disabled=not query):
        if query:
            perform_search(query, n_results)


def perform_search(query: str, n_results: int):
    """
    Perform test search on knowledge base.
    """
    try:
        from utils.rag_handler import AdvancedRAGHandler
        
        # Initialize RAG
        rag = AdvancedRAGHandler(
            ollama_endpoint=st.session_state.get('llm_endpoint', 'http://178.156.190.64:11435'),
            collection_name='hcmpact_knowledge'
        )
        
        # Search
        with st.spinner("Searching..."):
            results = rag.search(query, n_results=n_results)
        
        if not results:
            st.warning("No results found")
            return
        
        # Display results
        st.success(f"Found {len(results)} results")
        
        for idx, result in enumerate(results, 1):
            with st.expander(f"Result {idx} - {result.get('similarity', 0):.1%} match"):
                st.markdown(f"**Source:** {result.get('source', 'Unknown')}")
                st.markdown(f"**Chunk:** {result.get('chunk_id', 'N/A')}")
                st.markdown("---")
                st.markdown(result.get('text', 'No content'))
        
    except Exception as e:
        st.error(f"Search error: {str(e)}")
        logger.error(f"Search error: {str(e)}", exc_info=True)


def render_parser_tab():
    """
    Tab 4: Intelligent PDF parser.
    """
    try:
        from utils.parsers.intelligent_parser_ui_enhanced import render_intelligent_parser_ui
        render_intelligent_parser_ui()
        
    except ImportError as e:
        st.error(f"Intelligent parser module not found: {str(e)}")
        logger.error(f"Import error: {str(e)}", exc_info=True)
        
        st.info("""
        The intelligent parser module is not yet deployed. 
        
        To enable:
        1. Deploy intelligent_parser_ui_enhanced.py to utils/parsers/
        2. Deploy intelligent_parser_orchestrator_enhanced.py to utils/parsers/
        3. Deploy dayforce_parser_enhanced.py to utils/parsers/
        4. Restart application
        """)
    
    except Exception as e:
        st.error(f"Parser error: {str(e)}")
        logger.error(f"Parser error: {str(e)}", exc_info=True)


if __name__ == "__main__":
    render_knowledge_page()
