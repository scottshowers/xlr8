"""
Resumable Document Processor
Processes documents with state persistence - can resume after navigation
"""

import streamlit as st
import os
import json
from pathlib import Path
from typing import List, Dict, Any
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Path for storing processing state
STATE_DIR = Path("/tmp/xlr8_processing_state")
STATE_DIR.mkdir(exist_ok=True)


class ProcessingState:
    """Manages processing state that persists across page navigation."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.state_file = STATE_DIR / f"{session_id}.json"
    
    def save_state(self, state: Dict[str, Any]):
        """Save processing state to file."""
        try:
            state['last_updated'] = datetime.now().isoformat()
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
            logger.info(f"Saved processing state for session {self.session_id}")
        except Exception as e:
            logger.error(f"Error saving state: {e}")
    
    def load_state(self) -> Dict[str, Any]:
        """Load processing state from file."""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                logger.info(f"Loaded processing state for session {self.session_id}")
                return state
            return {}
        except Exception as e:
            logger.error(f"Error loading state: {e}")
            return {}
    
    def clear_state(self):
        """Clear processing state."""
        try:
            if self.state_file.exists():
                self.state_file.unlink()
            logger.info(f"Cleared processing state for session {self.session_id}")
        except Exception as e:
            logger.error(f"Error clearing state: {e}")


def get_session_id() -> str:
    """Get or create a unique session ID."""
    if 'processing_session_id' not in st.session_state:
        import uuid
        st.session_state.processing_session_id = str(uuid.uuid4())
    return st.session_state.processing_session_id


def render_resumable_upload_interface():
    """
    Render upload interface with resumable processing.
    Shows progress that persists across navigation.
    """
    
    st.subheader("📤 Resumable Document Upload")
    
    # Get session ID
    session_id = get_session_id()
    state_manager = ProcessingState(session_id)
    
    # Load any existing state
    current_state = state_manager.load_state()
    
    # Check if there's an in-progress upload
    if current_state and current_state.get('status') == 'in_progress':
        st.info("✅ **Resumable Processing Available**")
        st.markdown(f"""
        You have an upload in progress:
        - **Started:** {current_state.get('started_at', 'Unknown')}
        - **Files:** {current_state.get('total_files', 0)} total
        - **Processed:** {current_state.get('processed_count', 0)} files
        - **Status:** {current_state.get('current_file', 'Ready')}
        """)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("▶️ Resume Processing", type="primary"):
                st.session_state.resume_upload = True
                st.rerun()
        with col2:
            if st.button("🗑️ Cancel & Start Fresh"):
                state_manager.clear_state()
                st.success("Previous upload cancelled")
                st.rerun()
        
        st.markdown("---")
    
    # File upload
    category = st.selectbox(
        "Document Category",
        ["Customer Documents", "UKG Templates", "UKG Pro", "WFM", "Implementation Guide", "Best Practices", "Configuration", "General"],
        help="Select the category for better organization"
    )
    
    uploaded_files = st.file_uploader(
        "Choose files",
        type=['pdf', 'docx', 'txt', 'md', 'xlsx', 'xls'],
        accept_multiple_files=True,
        help="Supported formats: PDF, DOCX, TXT, MD, XLSX, XLS"
    )
    
    if uploaded_files:
        st.info(f"📁 {len(uploaded_files)} file(s) selected")
        
        with st.expander("📄 Selected Files"):
            for file in uploaded_files:
                st.write(f"- {file.name} ({file.size:,} bytes)")
        
        if st.button("🚀 Start Processing", type="primary"):
            # Initialize state
            initial_state = {
                'status': 'in_progress',
                'started_at': datetime.now().isoformat(),
                'total_files': len(uploaded_files),
                'processed_count': 0,
                'failed_count': 0,
                'files': [f.name for f in uploaded_files],
                'processed_files': [],
                'failed_files': [],
                'current_file': None,
                'category': category
            }
            state_manager.save_state(initial_state)
            st.session_state.start_processing = True
            st.rerun()
    
    # Process files if triggered
    if st.session_state.get('start_processing') or st.session_state.get('resume_upload'):
        process_files_with_state(state_manager, uploaded_files, category)


def process_files_with_state(
    state_manager: ProcessingState,
    uploaded_files: List[Any],
    category: str
):
    """
    Process files with state tracking and resumability.
    """
    
    from utils.document_processor import DocumentProcessor
    
    # Load current state
    state = state_manager.load_state()
    
    if not state:
        st.error("No processing state found")
        return
    
    # Get list of files already processed
    processed_files = set(state.get('processed_files', []))
    
    # Filter to only unprocessed files
    if uploaded_files:
        files_to_process = [f for f in uploaded_files if f.name not in processed_files]
    else:
        # Resuming without file objects - can't continue
        st.warning("⚠️ Cannot resume without re-uploading files. Please upload files again to continue.")
        st.button("🔄 Clear State", on_click=state_manager.clear_state)
        return
    
    if not files_to_process:
        st.success("✅ All files already processed!")
        state_manager.clear_state()
        return
    
    st.markdown("### 📊 Processing Progress")
    
    # Overall progress
    total_files = state['total_files']
    processed_count = state['processed_count']
    progress = processed_count / total_files if total_files > 0 else 0
    
    progress_bar = st.progress(progress)
    status_text = st.empty()
    
    # Initialize processor
    try:
        processor = DocumentProcessor()
    except Exception as e:
        st.error(f"Failed to initialize processor: {e}")
        return
    
    # Process remaining files
    for idx, file in enumerate(files_to_process):
        # Update state
        state['current_file'] = file.name
        state_manager.save_state(state)
        
        # Update UI
        current_num = processed_count + idx + 1
        status_text.info(f"📄 Processing file {current_num}/{total_files}: **{file.name}**")
        
        # Process file
        file.seek(0)
        result = processor.process_document(
            file=file,
            filename=file.name,
            collection_name="hcmpact_docs",
            category=category
        )
        
        # Update state based on result
        if result.get('success'):
            state['processed_files'].append(file.name)
            state['processed_count'] += 1
        else:
            state['failed_files'].append({
                'filename': file.name,
                'error': result.get('error', 'Unknown error')
            })
            state['failed_count'] += 1
        
        # Save state after each file
        state_manager.save_state(state)
        
        # Update progress
        progress = state['processed_count'] / total_files
        progress_bar.progress(progress)
    
    # Completion
    state['status'] = 'completed'
    state['completed_at'] = datetime.now().isoformat()
    state_manager.save_state(state)
    
    status_text.success(f"✅ Processing complete!")
    
    # Show summary
    st.markdown("---")
    st.markdown("### 📊 Processing Summary")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Files", total_files)
    with col2:
        st.metric("Successful", state['processed_count'], delta="✅")
    with col3:
        st.metric("Failed", state['failed_count'], delta="❌" if state['failed_count'] > 0 else None)
    
    if state['failed_files']:
        with st.expander("❌ Failed Files"):
            for failed in state['failed_files']:
                st.error(f"**{failed['filename']}:** {failed['error']}")
    
    # Clear state
    if st.button("✅ Clear State & Finish"):
        state_manager.clear_state()
        st.session_state.pop('start_processing', None)
        st.session_state.pop('resume_upload', None)
        st.rerun()


# Add this to knowledge.py to replace the regular upload interface
def render_knowledge_page_with_resumable():
    """Enhanced knowledge page with resumable upload."""
    
    st.title("🧠 HCMPACT LLM Seeding")
    
    tabs = st.tabs(["📤 Upload (Resumable)", "📊 Status", "🗑️ Manage"])
    
    with tabs[0]:
        render_resumable_upload_interface()
    
    with tabs[1]:
        # Existing status tab code
        from pages.setup.knowledge import render_status_tab
        render_status_tab()
    
    with tabs[2]:
        # Existing manage tab code
        from pages.setup.knowledge import render_manage_tab
        render_manage_tab()
