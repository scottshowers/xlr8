"""
Document Library Page
Manage all uploaded and generated documents
"""

import streamlit as st
from datetime import datetime
import pandas as pd


def render_library_page():
    """Render document library page"""
    
    st.markdown("## 📁 Document Library")
    
    st.markdown("""
    <div class='info-box'>
        <strong>Document Library:</strong> View and manage all documents uploaded to XLR8,
        including source files, parsed results, and generated templates.
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize library if needed
    if 'doc_library' not in st.session_state:
        st.session_state.doc_library = []
    
    # Stats
    total_docs = len(st.session_state.get('doc_library', []))
    
    if total_docs > 0:
        # Document type breakdown
        doc_types = {}
        for doc in st.session_state.get('doc_library', []):
            doc_type = doc.get('type', 'Unknown')
            doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📄 Total Documents", total_docs)
        with col2:
            pdf_count = doc_types.get('pdf', 0)
            st.metric("📕 PDFs", pdf_count)
        with col3:
            excel_count = doc_types.get('excel', 0)
            st.metric("📊 Excel", excel_count)
        with col4:
            template_count = doc_types.get('template', 0)
            st.metric("📋 Templates", template_count)
        
        st.markdown("---")
        
        # Filter and sort options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            filter_type = st.selectbox(
                "Filter by Type",
                ["All"] + list(doc_types.keys())
            )
        
        with col2:
            filter_project = st.selectbox(
                "Filter by Project",
                ["All"] + list(st.session_state.get('projects', {}).keys()) if st.session_state.get('projects') else ["All"]
            )
        
        with col3:
            sort_by = st.selectbox(
                "Sort by",
                ["Newest First", "Oldest First", "Name A-Z", "Name Z-A"]
            )
        
        # Apply filters
        filtered_docs = st.session_state.get('doc_library', [])
        
        if filter_type != "All":
            filtered_docs = [d for d in filtered_docs if d.get('type') == filter_type]
        
        if filter_project != "All":
            filtered_docs = [d for d in filtered_docs if d.get('project') == filter_project]
        
        # Apply sort
        if sort_by == "Newest First":
            filtered_docs = sorted(filtered_docs, key=lambda x: x.get('timestamp', ''), reverse=True)
        elif sort_by == "Oldest First":
            filtered_docs = sorted(filtered_docs, key=lambda x: x.get('timestamp', ''))
        elif sort_by == "Name A-Z":
            filtered_docs = sorted(filtered_docs, key=lambda x: x.get('name', ''))
        else:  # Name Z-A
            filtered_docs = sorted(filtered_docs, key=lambda x: x.get('name', ''), reverse=True)
        
        st.markdown(f"**Showing {len(filtered_docs)} of {total_docs} documents**")
        
        # Display documents
        for idx, doc in enumerate(filtered_docs):
            with st.expander(f"{_get_icon(doc.get('type'))} {doc.get('name', 'Unnamed Document')}"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"**Type:** {doc.get('type', 'Unknown')}")
                    st.markdown(f"**Project:** {doc.get('project', 'None')}")
                    st.markdown(f"**Uploaded:** {doc.get('timestamp', 'Unknown')}")
                    
                    if doc.get('description'):
                        st.markdown(f"**Description:** {doc.get('description')}")
                    
                    if doc.get('size'):
                        st.markdown(f"**Size:** {doc.get('size')} bytes")
                
                with col2:
                    if doc.get('download_url'):
                        st.download_button(
                            "⬇️ Download",
                            data=doc.get('data', b''),
                            file_name=doc.get('name', 'document'),
                            key=f"download_{idx}"
                        )
                    
                    if st.button("🗑️ Delete", key=f"delete_doc_{idx}"):
                        if 'doc_library' in st.session_state:
                            st.session_state.doc_library.pop(idx)
                        st.rerun()
    
    else:
        st.info("📁 No documents in library yet. Upload documents in the Analysis or Knowledge Base tabs.")


def _get_icon(doc_type: str) -> str:
    """Get icon for document type"""
    icons = {
        'pdf': '📕',
        'excel': '📊',
        'word': '📝',
        'template': '📋',
        'csv': '📈',
        'txt': '📄'
    }
    return icons.get(doc_type, '📄')


if __name__ == "__main__":
    st.title("Library - Test")
    render_library_page()
