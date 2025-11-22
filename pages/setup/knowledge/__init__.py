"""
Complete Knowledge Management Page - WITH PROJECT ISOLATION
4 tabs: Upload | Status | Search | Intelligent Parser

CHANGES FOR PROJECT ISOLATION:
- Project selector dropdown (instead of assuming active project)
- Tags uploads with selected project_id
- Bypasses DocumentProcessor to add metadata directly
- All existing functionality preserved

REQUIRED LIBRARIES:
- pdfplumber (for PDF)
- python-docx (for DOCX)
- pandas (for Excel/CSV)
- openpyxl (for Excel)
"""

import streamlit as st
from pathlib import Path
import logging
import time
from datetime import datetime
from typing import Optional  # ← ADDED: Required for Optional[str]

logger = logging.getLogger(__name__)


def render_knowledge_page():
    """
    Main render function for knowledge page with 4 tabs.
    """
    st.title("🗄️ HCMPACT LLM Seeding & Document Management")
    
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
    NOW INCLUDES PROJECT SELECTOR DROPDOWN
    """
    st.header("Upload Documents to Knowledge Base")
    
    st.markdown("""
    Upload documents to seed the HCMPACT LLM knowledge base. Supported formats:
    - **PDF** - Payroll registers, configuration guides, manuals
    - **DOCX** - Word documents, procedures, templates
    - **TXT/MD** - Text files, markdown documentation
    - **XLS/XLSX/CSV** - Excel spreadsheets
    - **JPG/JPEG/PNG** - Images
    
    **⚠️ IMPORTANT FOR EXCEL FILES:**
    - Each worksheet takes 2-5 minutes to process (chunking + embeddings)
    - Files with 10+ sheets may cause UI timeout (process continues in background)
    - **Recommendation:** Upload Excel files with <10 sheets at a time
    - Check logs to verify completion if UI times out
    
    Documents are automatically:
    1. **Tagged with selected project** (or marked as Global)
    2. Chunked into searchable segments (2000 chars for Excel, 800 for others)
    3. Embedded using Ollama (this is the slow part - ~30-60s per chunk)
    4. Stored in ChromaDB for RAG
    5. Saved to `/data/uploads/` for parsing
    """)
    
    # PROJECT SELECTOR DROPDOWN
    st.markdown("---")
    st.subheader("📁 Project Assignment")
    
    # Build project options
    projects = st.session_state.get('projects', {})
    project_options = ["🌐 Global (All Projects)"] + [f"📁 {name}" for name in projects.keys()]
    
    # Default to active project if exists
    current_project = st.session_state.get('current_project')
    default_index = 0
    if current_project and current_project in projects:
        default_index = project_options.index(f"📁 {current_project}")
    
    selected_option = st.selectbox(
        "Assign documents to:",
        options=project_options,
        index=default_index,
        help="Select which project these documents belong to, or choose Global for shared resources"
    )
    
    # Parse selection
    if selected_option == "🌐 Global (All Projects)":
        selected_project = None
        st.info("💡 Documents will be available to ALL projects (config docs, regulations, shared resources)")
    else:
        selected_project = selected_option.replace("📁 ", "")
        st.success(f"✅ Documents will be tagged to project: **{selected_project}**")
    
    st.markdown("---")
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Select files to upload",
        type=['pdf', 'docx', 'txt', 'md', 'xlsx', 'xls', 'csv', 'png', 'jpg', 'jpeg'],
        accept_multiple_files=True,
        help="Upload one or more documents"
    )
    
    if uploaded_files:
        st.info(f"📄 Selected {len(uploaded_files)} file(s)")
        
        if st.button("✨ Upload and Process", type="primary", use_container_width=True):
            submit_upload_jobs(uploaded_files, selected_project)


def submit_upload_jobs(uploaded_files, selected_project: Optional[str] = None):
    """
    Submit document upload jobs for background processing
    NO MORE UI TIMEOUT!
    
    Args:
        uploaded_files: List of uploaded files
        selected_project: Project name or None for global
    """
    from utils.background.job_manager import get_job_manager
    from utils.background.document_handler import process_document_upload
    from utils.database.supabase_client import get_supabase
    
    # Get dependencies
    rag_handler = st.session_state.get('rag_handler')
    if not rag_handler:
        st.error("❌ RAG handler not initialized. Please refresh the page.")
        return
    
    supabase = get_supabase()
    if not supabase:
        st.error("❌ Supabase not configured. Background processing requires Supabase.")
        return
    
    job_manager = get_job_manager()
    
    # Submit each file as a job
    job_ids = []
    
    for uploaded_file in uploaded_files:
        try:
            # Read file
            file_bytes = uploaded_file.read()
            filename = uploaded_file.name
            file_ext = Path(filename).suffix.lower()
            
            # Prepare input data (passed to worker)
            input_data = {
                'file_bytes': file_bytes,  # Raw bytes
                'filename': filename,
                'file_ext': file_ext,
                'selected_project': selected_project
                # rag_handler will be recreated in worker
            }
            
            # Submit job
            job_id = job_manager.submit_job(
                job_type='document_upload',
                handler=process_document_upload,
                input_data=input_data,
                project_id=selected_project,
                supabase_client=supabase
            )
            
            job_ids.append({
                'job_id': job_id,
                'filename': filename
            })
            
            st.success(f"✅ Queued: {filename} (Job ID: {job_id[:8]}...)")
        
        except Exception as e:
            st.error(f"❌ Failed to queue {uploaded_file.name}: {str(e)}")
    
    if job_ids:
        # Store in session for monitoring
        if 'active_jobs' not in st.session_state:
            st.session_state.active_jobs = []
        
        st.session_state.active_jobs.extend(job_ids)
        
        st.success(f"🚀 {len(job_ids)} job(s) submitted for background processing!")
        st.info("💡 Go to 'Collection Status' tab to monitor progress. Your UI will not freeze!")
        
        # Auto-switch to status tab (store preference)
        st.session_state.show_job_monitor = True


def render_status_tab():
    """
    Tab 2: Show collection status, statistics, AND JOB MONITOR
    """
    st.header("Knowledge Base Status")
    
    # ═══════════════════════════════════════════════════════════
    # JOB MONITOR - Real-time progress updates
    # ═══════════════════════════════════════════════════════════
    if st.session_state.get('active_jobs'):
        st.markdown("### 🔄 Background Jobs")
        
        from utils.database.supabase_client import get_supabase
        from utils.background.job_manager import get_job_manager
        
        supabase = get_supabase()
        job_manager = get_job_manager()
        
        if supabase:
            active_jobs = st.session_state.active_jobs
            completed_jobs = []
            
            for job_info in active_jobs:
                job_id = job_info['job_id']
                filename = job_info['filename']
                
                # Get current status
                job_data = job_manager.get_job_status(job_id, supabase)
                
                if job_data:
                    status = job_data['status']
                    progress = job_data.get('progress', {})
                    current = progress.get('current', 0)
                    total = progress.get('total', 100)
                    message = progress.get('message', '')
                    
                    # Display job status
                    with st.expander(f"{'✅' if status == 'completed' else '🔄' if status == 'processing' else '⏳'} {filename} - {status.upper()}", expanded=(status == 'processing')):
                        st.text(f"Job ID: {job_id}")
                        
                        if status == 'processing':
                            st.progress(current / max(total, 1))
                            st.info(f"📊 {message}")
                        
                        elif status == 'completed':
                            result = job_data.get('result_data', {})
                            st.success(f"✅ Complete! Added {result.get('chunks_added', '?')} chunks")
                            if result.get('sheets_processed'):
                                st.text(f"Sheets: {', '.join(result['sheets_processed'])}")
                            completed_jobs.append(job_info)
                        
                        elif status == 'failed':
                            st.error(f"❌ Failed: {job_data.get('error_message', 'Unknown error')}")
                            completed_jobs.append(job_info)
                        
                        elif status == 'queued':
                            st.info("⏳ Waiting in queue...")
            
            # Remove completed/failed jobs from active list
            for job_info in completed_jobs:
                st.session_state.active_jobs.remove(job_info)
            
            # Auto-refresh every 2 seconds if jobs are processing
            if any(j for j in active_jobs if j not in completed_jobs):
                st.markdown("🔄 *Auto-refreshing every 2 seconds...*")
                time.sleep(2)
                st.rerun()
        
        st.markdown("---")
    
    # ═══════════════════════════════════════════════════════════
    # Regular Status Display
    # ═══════════════════════════════════════════════════════════
    try:
        from utils.rag_handler import RAGHandler
        
        # Initialize RAG handler
        rag = RAGHandler(
            llm_endpoint=st.session_state.get('llm_endpoint', 'http://178.156.190.64:11435')
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
        
        # DEBUG: Sample chunk metadata
        st.markdown("---")
        with st.expander("🔍 Debug: Sample Chunk Metadata"):
            try:
                sample_results = collection.get(limit=3, include=["metadatas"])
                if sample_results and sample_results['metadatas']:
                    for i, meta in enumerate(sample_results['metadatas'], 1):
                        st.json({
                            f"Chunk {i}": {
                                "project_id": meta.get('project_id', '❌ MISSING'),
                                "source": meta.get('source', '❌ MISSING'),
                                "functional_area": meta.get('functional_area', '❌ MISSING'),
                                "sheet_name": meta.get('sheet_name', 'N/A')
                            }
                        })
                else:
                    st.info("No chunks to inspect")
            except Exception as e:
                st.error(f"Error inspecting metadata: {e}")
        
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
        
        # CLEAN SLATE: Delete old collection button
        st.markdown("---")
        st.subheader("🗑️ Database Cleanup")
        
        st.warning("""
        ⚠️ **Clean Slate Migration Tool**
        
        If you have an old `hcmpact_docs` collection from before project isolation was implemented,
        you can delete it here. This will allow you to start fresh with properly tagged documents.
        
        **Important:**
        - This only deletes the OLD collection (`hcmpact_docs`)
        - Your current collection (`hcmpact_knowledge`) remains safe
        - You'll need to re-upload documents after deletion
        - **This action cannot be undone!**
        """)
        
        # Check if old collection exists
        try:
            collections = rag.client.list_collections()
            collection_names = [col.name for col in collections]
            old_collection_exists = 'hcmpact_docs' in collection_names
            
            if old_collection_exists:
                # Get count
                old_col = rag.client.get_collection('hcmpact_docs')
                old_count = old_col.count()
                
                st.info(f"📊 Old collection `hcmpact_docs` found: **{old_count:,} chunks**")
                
                # Confirmation checkbox
                confirm_delete = st.checkbox(
                    f"⚠️ I understand that deleting {old_count:,} chunks is permanent",
                    key="confirm_delete_old_collection"
                )
                
                col1, col2 = st.columns([1, 3])
                with col1:
                    if st.button(
                        "🗑️ Delete Old Collection",
                        type="primary",
                        disabled=not confirm_delete,
                        use_container_width=True
                    ):
                        try:
                            rag.client.delete_collection('hcmpact_docs')
                            st.success(f"✅ Successfully deleted `hcmpact_docs` ({old_count:,} chunks)")
                            st.info("""
                            **Next steps:**
                            1. Go to Setup → Projects and activate your project
                            2. Go to Document Upload tab
                            3. Re-upload your documents with proper project tags
                            4. They'll be added to `hcmpact_knowledge` with project isolation
                            """)
                            logger.info(f"Deleted old collection hcmpact_docs ({old_count} chunks)")
                            # Page will auto-refresh on next interaction
                        except Exception as del_error:
                            st.error(f"❌ Failed to delete collection: {del_error}")
                            logger.error(f"Collection deletion error: {del_error}", exc_info=True)
                
                with col2:
                    st.caption("Checkbox must be checked to enable deletion")
            else:
                st.success("✅ No old collection found. You're using clean project isolation!")
                
        except Exception as check_error:
            st.info("Could not check for old collections. This is normal if you're starting fresh.")
            logger.debug(f"Collection check error: {check_error}")
        
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
        from utils.rag_handler import RAGHandler
        
        # Initialize RAG
        rag = RAGHandler(
            llm_endpoint=st.session_state.get('llm_endpoint', 'http://178.156.190.64:11435')
        )
        
        # Search WITH PROJECT FILTER
        with st.spinner("🔍 Searching..."):
            results = rag.search(
                collection_name='hcmpact_knowledge',
                query=query, 
                n_results=n_results,
                project_id=project_id
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
