"""
Complete Knowledge Management Page - WITH PROJECT ISOLATION
4 tabs: Upload | Status | Search | Intelligent Parser

CHANGES FOR PROJECT ISOLATION:
- Line 64: Tags uploads with current_project metadata
- Line 140: Filters search by current_project (optional)
- All existing functionality preserved
"""

import streamlit as st
from pathlib import Path
import logging
from datetime import datetime
from typing import Optional  # ← ADDED: Required for Optional[str]

logger = logging.getLogger(__name__)


def render_knowledge_page():
    """
    Main render function for knowledge page with 4 tabs.
    """
    st.title("🗄️ HCMPACT LLM Seeding & Document Management")
    
    # Show current project context at top
    current_project = st.session_state.get('current_project')
    if current_project:
        st.success(f"📁 Active Project: **{current_project}** - Documents will be tagged to this project")
    else:
        st.info("💡 No project selected - Documents will be uploaded as global/shared knowledge")
    
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
    NOW INCLUDES PROJECT TAGGING
    """
    st.header("Upload Documents to Knowledge Base")
    
    st.markdown("""
    Upload documents to seed the HCMPACT LLM knowledge base. Supported formats:
    - **PDF** - Payroll registers, configuration guides, manuals
    - **DOCX** - Word documents, procedures, templates
    - **TXT/MD** - Text files, markdown documentation
    - **XLS/XLSX/CSV** - Excel
    - **JPG/JPEG/PNG** - Images
    
    Documents are automatically:
    1. **Tagged with current project** (if selected)
    2. Chunked into searchable segments
    3. Embedded using Ollama
    4. Stored in ChromaDB for RAG
    5. Saved to `/data/uploads/` for parsing
    """)
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Select files to upload",
        type=['pdf', 'docx', 'txt', 'md', 'xlsx', 'xls', 'csv', 'png', 'jpg', 'jpeg'],
        accept_multiple_files=True,
        help="Upload one or more documents"
    )
    
    if uploaded_files:
        st.info(f"Selected {len(uploaded_files)} file(s)")
        
        if st.button("✨ Upload and Process", type="primary", use_container_width=True):
            process_uploads(uploaded_files)


def process_uploads(uploaded_files):
    """
    Process uploaded files: save and chunk to ChromaDB.
    NOW TAGS WITH PROJECT_ID
    """
    from utils.document_processor import DocumentProcessor
    
    processor = DocumentProcessor()
    
    # Get current project (optional)
    current_project = st.session_state.get('current_project')
    
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
            
            # CHANGE: Add project_id to metadata if project selected
            metadata = {}
            if current_project:
                metadata['project_id'] = current_project
                logger.info(f"Tagging upload '{uploaded_file.name}' with project_id: {current_project}")
            
            # Process document WITH PROJECT METADATA
            result = processor.process_document(
                uploaded_file,
                collection_name='hcmpact_knowledge',
                metadata=metadata  # ← CHANGED: Pass project_id
            )
            
            results.append({
                'filename': uploaded_file.name,
                'status': 'success' if result.get('status') == 'success' else 'error',
                'chunks': result.get('num_chunks', 0),
                'project': current_project if current_project else 'Global',
                'message': result.get('message', '')
            })
            
        except Exception as e:
            logger.error(f"Upload error for {uploaded_file.name}: {str(e)}", exc_info=True)
            results.append({
                'filename': uploaded_file.name,
                'status': 'error',
                'chunks': 0,
                'project': current_project if current_project else 'Global',
                'message': str(e)
            })
    
    # Show results
    progress_bar.progress(1.0)
    status_text.empty()
    
    # Summary
    success_count = sum(1 for r in results if r['status'] == 'success')
    total_chunks = sum(r['chunks'] for r in results)
    
    if success_count == total:
        st.success(f"✅ Successfully processed {success_count} file(s) - {total_chunks} chunks created")
    elif success_count > 0:
        st.warning(f"⚠️ Processed {success_count}/{total} files - {total_chunks} chunks created")
    else:
        st.error("❌ All uploads failed")
    
    # Detailed results
    with results_container.expander("📋 View Details"):
        for result in results:
            if result['status'] == 'success':
                st.write(f"✅ {result['filename']} - {result['chunks']} chunks - Project: {result['project']}")
            else:
                st.write(f"❌ {result['filename']} - {result['message']}")


def render_status_tab():
    """
    Tab 2: Show collection status and statistics.
    UNCHANGED - Shows all documents regardless of project
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
        collection = rag.client.get_or_create_collection('hcmpact_knowledge')
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
        st.subheader("📄 Recent Documents")
        
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
    NOW SUPPORTS PROJECT FILTERING
    """
    st.header("🔍 Test Knowledge Base Search")
    
    st.markdown("""
    Test the RAG search capabilities. This searches the embedded chunks in ChromaDB
    and returns the most relevant content.
    """)
    
    # Project filter option
    current_project = st.session_state.get('current_project')
    
    col1, col2 = st.columns([3, 1])
    with col1:
        # Search input
        query = st.text_input(
            "Enter search query",
            placeholder="e.g., How do I configure absence types?",
            help="Search the knowledge base"
        )
    
    with col2:
        n_results = st.slider("Results", 1, 20, 10)
    
    # Project filtering checkbox
    filter_by_project = False
    if current_project:
        filter_by_project = st.checkbox(
            f"🔒 Only search '{current_project}' documents",
            value=True,
            help="Restrict search to current project's documents only"
        )
    
    if st.button("🔍 Search", type="primary", disabled=not query):
        if query:
            # CHANGE: Pass project_id if filtering enabled
            project_filter = current_project if filter_by_project else None
            perform_search(query, n_results, project_filter)


def perform_search(query: str, n_results: int, project_id: Optional[str] = None):
    """
    Perform test search on knowledge base.
    NOW SUPPORTS PROJECT FILTERING
    """
    try:
        from utils.rag_handler import AdvancedRAGHandler
        
        # Initialize RAG
        rag = AdvancedRAGHandler(
            ollama_endpoint=st.session_state.get('llm_endpoint', 'http://178.156.190.64:11435'),
            collection_name='hcmpact_knowledge'
        )
        
        # Search WITH PROJECT FILTER
        with st.spinner("🔍 Searching..."):
            # CHANGE: Pass project_id parameter
            results = rag.search(
                query, 
                n_results=n_results,
                project_id=project_id  # ← CHANGED: Filter by project
            )
        
        if not results:
            st.warning("No results found")
            return
        
        # Display results
        if project_id:
            st.success(f"✅ Found {len(results)} results for project '{project_id}'")
        else:
            st.success(f"✅ Found {len(results)} results (all projects)")
        
        for idx, result in enumerate(results, 1):
            with st.expander(f"Result {idx} - {result.get('similarity', 0):.1%} match"):
                st.markdown(f"**Source:** {result.get('source', 'Unknown')}")
                st.markdown(f"**Chunk:** {result.get('chunk_id', 'N/A')}")
                
                # CHANGE: Show project if available
                if result.get('metadata', {}).get('project_id'):
                    st.markdown(f"**Project:** {result['metadata']['project_id']}")
                
                st.markdown("---")
                st.markdown(result.get('text', 'No content'))
        
    except Exception as e:
        st.error(f"Search error: {str(e)}")
        logger.error(f"Search error: {str(e)}", exc_info=True)


def render_parser_tab():
    """
    Tab 4: Intelligent PDF parser.
    UNCHANGED
    """
    try:
        from utils.parsers.intelligent_parser_ui import render_intelligent_parser_ui
        render_intelligent_parser_ui()
        
    except ImportError as e:
        st.error(f"Intelligent parser module not found: {str(e)}")
        logger.error(f"Import error: {str(e)}", exc_info=True)
        
        st.info("""
        The intelligent parser module is not yet deployed. 
        
        To enable:
        1. Deploy intelligent_parser_ui.py to utils/parsers/
        2. Deploy intelligent_parser_orchestrator.py to utils/parsers/
        3. Deploy dayforce_parser_enhanced.py to utils/parsers/
        4. Restart application
        """)
    
    except Exception as e:
        st.error(f"Parser error: {str(e)}")
        logger.error(f"Parser error: {str(e)}", exc_info=True)


if __name__ == "__main__":
    render_knowledge_page()
