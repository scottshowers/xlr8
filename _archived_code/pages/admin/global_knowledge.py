"""
Global Knowledge Management Page
Universal documents that apply across all projects
"""

import streamlit as st
from utils.rag_handler import RAGHandler
import logging

logger = logging.getLogger(__name__)


def render_global_knowledge_page():
    """Render global knowledge management page"""
    
    st.markdown("## 🌐 Global Knowledge Base")
    
    st.markdown("""
    <div class='info-box'>
        <strong>Global Knowledge:</strong> Upload universal documents, templates, 
        best practices, and reference materials that apply across all projects.
        These documents will be available for AI assistance in any project context.
    </div>
    """, unsafe_allow_html=True)
    
    # Quick stats
    try:
        rag = RAGHandler()
        collections = rag.list_collections()
        
        # Count global docs (hcmpact_knowledge collection)
        global_count = 0
        if 'hcmpact_knowledge' in collections:
            global_count = rag.get_collection_count('hcmpact_knowledge')
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("🌐 Global Documents", global_count)
        with col2:
            st.metric("📚 Collections", len([c for c in collections if 'knowledge' in c.lower()]))
        
        st.markdown("---")
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
    
    # Upload section
    st.markdown("### 📤 Upload Global Documents")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_files = st.file_uploader(
            "Upload files (PDF, DOCX, TXT, MD, CSV, XLSX)",
            type=['pdf', 'docx', 'txt', 'md', 'csv', 'xlsx'],
            accept_multiple_files=True,
            help="These documents will be available across all projects"
        )
    
    with col2:
        st.markdown("### 📋 Document Types")
        st.markdown("""
        - Templates
        - Best Practices
        - Policies
        - Standards
        - Reference Guides
        - Training Materials
        """)
    
    if uploaded_files:
        st.info(f"📁 {len(uploaded_files)} file(s) ready to process")
        
        if st.button("🚀 Process Global Documents", type="primary", use_container_width=True):
            with st.spinner("Processing documents..."):
                try:
                    rag = RAGHandler()
                    success_count = 0
                    error_count = 0
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    for idx, file in enumerate(uploaded_files):
                        try:
                            status_text.text(f"Processing {file.name}...")
                            
                            # Read file content
                            content = file.read()
                            
                            if isinstance(content, bytes):
                                content = content.decode('utf-8', errors='ignore')
                            
                            # Determine file type
                            file_type = file.name.split('.')[-1].lower()
                            
                            # Add to global knowledge collection
                            metadata = {
                                'source': file.name,
                                'file_type': file_type,
                                'is_global': True,
                                'category': 'global_knowledge'
                            }
                            
                            success = rag.add_document(
                                collection_name='hcmpact_knowledge',
                                document=content,
                                metadata=metadata,
                                file_type=file_type
                            )
                            
                            if success:
                                success_count += 1
                            else:
                                error_count += 1
                            
                            # Update progress
                            progress_bar.progress((idx + 1) / len(uploaded_files))
                        
                        except Exception as e:
                            logger.error(f"Error processing {file.name}: {e}")
                            error_count += 1
                    
                    progress_bar.empty()
                    status_text.empty()
                    
                    # Show results
                    if success_count > 0:
                        st.success(f"✅ Processed {success_count} document(s) successfully!")
                    if error_count > 0:
                        st.warning(f"⚠️ {error_count} document(s) failed to process")
                    
                    st.rerun()
                
                except Exception as e:
                    st.error(f"❌ Error processing documents: {str(e)}")
                    logger.error(f"Global knowledge upload error: {e}", exc_info=True)
    
    # View existing global documents
    st.markdown("---")
    st.markdown("### 📚 Current Global Knowledge Base")
    
    try:
        rag = RAGHandler()
        
        # Search for sample docs
        if st.button("🔍 Preview Global Documents"):
            results = rag.search('hcmpact_knowledge', 'template best practice', n_results=10)
            
            if results:
                st.success(f"Found {len(results)} global documents")
                
                for idx, result in enumerate(results[:5], 1):
                    with st.expander(f"📄 {result['metadata'].get('source', 'Unknown')}"):
                        st.markdown(f"**Content Preview:**")
                        preview = result['document'][:300] + "..." if len(result['document']) > 300 else result['document']
                        st.text(preview)
                        
                        st.markdown(f"**Metadata:**")
                        st.json(result['metadata'])
            else:
                st.info("No global documents found. Upload some to get started!")
    
    except Exception as e:
        st.error(f"Error loading documents: {str(e)}")
        logger.error(f"Error in global knowledge page: {e}", exc_info=True)
    
    # Management section
    st.markdown("---")
    st.markdown("### ⚙️ Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Refresh Stats", use_container_width=True):
            st.rerun()
    
    with col2:
        if st.button("⚠️ Clear Global Knowledge", use_container_width=True, type="secondary"):
            if st.checkbox("⚠️ Confirm: This will delete ALL global documents"):
                try:
                    rag = RAGHandler()
                    rag.delete_collection('hcmpact_knowledge')
                    st.success("✅ Global knowledge cleared")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
