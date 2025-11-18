"""
Document Management Page - Per-File Processing Status
Shows which documents have been processed and chunked
"""

import streamlit as st
from utils.rag_handler import RAGHandler
from utils.document_processor import DocumentProcessor
import logging
from typing import Dict, List, Any
from collections import defaultdict

logger = logging.getLogger(__name__)


def get_document_status() -> Dict[str, Any]:
    """
    Get detailed status of all documents in ChromaDB.
    Returns dict with document names and their chunk counts.
    """
    try:
        rag = RAGHandler()
        collection = rag.client.get_collection("hcmpact_docs")
        
        # Get all documents
        all_data = collection.get(include=['metadatas'])
        
        if not all_data or not all_data.get('metadatas'):
            return {}
        
        # Count chunks per document
        doc_chunks = defaultdict(int)
        doc_categories = {}
        
        for meta in all_data['metadatas']:
            source = meta.get('source', 'Unknown')
            category = meta.get('category', 'Unknown')
            doc_chunks[source] += 1
            doc_categories[source] = category
        
        # Build status dict
        status = {}
        for doc, count in doc_chunks.items():
            status[doc] = {
                'chunks': count,
                'category': doc_categories[doc],
                'status': 'processed'
            }
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting document status: {e}")
        return {}


def render_manage_page():
    """Render the document management page."""
    
    st.title("📁 Document Management")
    st.markdown("""
    <div style='color: #6B7280; font-size: 0.9rem; margin-bottom: 1.5rem;'>
    View processing status and manage your uploaded documents.
    </div>
    """, unsafe_allow_html=True)
    
    # Get document status
    with st.spinner("Loading document status..."):
        doc_status = get_document_status()
    
    if not doc_status:
        st.warning("⚠️ No documents found in ChromaDB collection.")
        st.info("👉 Go to Setup → HCMPACT LLM Seeding → Upload to add documents")
        return
    
    # Summary metrics
    total_docs = len(doc_status)
    total_chunks = sum(d['chunks'] for d in doc_status.values())
    
    # Categorize documents
    templates = [k for k, v in doc_status.items() if 'UKG Templates' in v.get('category', '')]
    customer_docs = [k for k, v in doc_status.items() if 'UKG Templates' not in v.get('category', '')]
    
    # Top metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Documents", total_docs)
    with col2:
        st.metric("Total Chunks", f"{total_chunks:,}")
    with col3:
        st.metric("Customer Docs", len(customer_docs))
    with col4:
        st.metric("Templates", len(templates))
    
    st.markdown("---")
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs([
        "📊 All Documents",
        "📄 Customer Documents", 
        "📋 Templates"
    ])
    
    # TAB 1: ALL DOCUMENTS
    with tab1:
        st.subheader("All Documents")
        render_document_table(doc_status, total_chunks)
    
    # TAB 2: CUSTOMER DOCUMENTS
    with tab2:
        st.subheader("Customer Documents")
        customer_status = {k: v for k, v in doc_status.items() if k in customer_docs}
        
        if customer_status:
            customer_chunks = sum(d['chunks'] for d in customer_status.values())
            st.info(f"**{len(customer_status)} customer documents** with **{customer_chunks:,} chunks**")
            render_document_table(customer_status, customer_chunks)
        else:
            st.warning("No customer documents found. Templates only.")
            st.info("💡 Upload customer documents to Setup → HCMPACT LLM Seeding")
    
    # TAB 3: TEMPLATES
    with tab3:
        st.subheader("UKG Templates")
        template_status = {k: v for k, v in doc_status.items() if k in templates}
        
        if template_status:
            template_chunks = sum(d['chunks'] for d in template_status.values())
            st.info(f"**{len(template_status)} templates** with **{template_chunks:,} chunks**")
            render_document_table(template_status, template_chunks)
        else:
            st.info("No templates loaded yet.")


def render_document_table(doc_status: Dict[str, Any], total_chunks: int):
    """Render a table of documents with their status."""
    
    if not doc_status:
        st.info("No documents to display.")
        return
    
    # Sort by chunk count (descending)
    sorted_docs = sorted(doc_status.items(), key=lambda x: x[1]['chunks'], reverse=True)
    
    # Build table data
    table_data = []
    for doc_name, info in sorted_docs:
        chunks = info['chunks']
        category = info.get('category', 'Unknown')
        percentage = (chunks / total_chunks * 100) if total_chunks > 0 else 0
        
        # Status indicator
        status_icon = "✅" if chunks > 0 else "❌"
        
        table_data.append({
            'Status': status_icon,
            'Document': doc_name,
            'Category': category,
            'Chunks': f"{chunks:,}",
            '% of Total': f"{percentage:.1f}%"
        })
    
    # Display as dataframe
    import pandas as pd
    df = pd.DataFrame(table_data)
    
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            'Status': st.column_config.TextColumn(width="small"),
            'Document': st.column_config.TextColumn(width="large"),
            'Category': st.column_config.TextColumn(width="medium"),
            'Chunks': st.column_config.TextColumn(width="small"),
            '% of Total': st.column_config.TextColumn(width="small")
        }
    )
    
    # Export option
    st.markdown("---")
    st.markdown("### 📥 Export Document List")
    
    csv = df.to_csv(index=False)
    st.download_button(
        label="Download as CSV",
        data=csv,
        file_name="document_status.csv",
        mime="text/csv",
        help="Download the complete document list with chunk counts"
    )
    
    # Danger zone
    st.markdown("---")
    st.markdown("### ⚠️ Danger Zone")
    
    with st.expander("🗑️ Remove Specific Documents"):
        st.warning("**Warning:** This will delete all chunks for the selected document. This cannot be undone!")
        
        doc_to_remove = st.selectbox(
            "Select document to remove",
            options=[""] + [doc for doc, _ in sorted_docs],
            format_func=lambda x: x if x else "-- Select a document --"
        )
        
        if doc_to_remove:
            st.error(f"You are about to delete all chunks from: **{doc_to_remove}**")
            
            if st.button("🗑️ DELETE THIS DOCUMENT", type="primary"):
                try:
                    rag = RAGHandler()
                    collection = rag.client.get_collection("hcmpact_docs")
                    
                    # Get all IDs for this document
                    all_data = collection.get(include=['metadatas'])
                    ids_to_delete = [
                        id for id, meta in zip(all_data['ids'], all_data['metadatas'])
                        if meta.get('source') == doc_to_remove
                    ]
                    
                    if ids_to_delete:
                        collection.delete(ids=ids_to_delete)
                        st.success(f"✅ Deleted {len(ids_to_delete)} chunks from {doc_to_remove}")
                        st.rerun()
                    else:
                        st.warning("No chunks found for this document")
                        
                except Exception as e:
                    st.error(f"Error deleting document: {e}")


# Entry point
if __name__ == "__main__":
    render_manage_page()
