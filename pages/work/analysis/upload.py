"""
File Upload Module
Handles document upload UI and validation

Owner: Person A - Upload Team
Dependencies: streamlit, config
Testing: Can run standalone with mock data
"""

import streamlit as st
from typing import Optional
from config import AppConfig


def render_upload_section() -> Optional[st.runtime.uploaded_file_manager.UploadedFile]:
    """
    Render file upload widget with validation
    
    Returns:
        UploadedFile object or None
        
    Example Usage:
        uploaded_file = render_upload_section()
        if uploaded_file:
            process_file(uploaded_file)
    """
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Choose customer document",
        type=['pdf', 'xlsx', 'xls', 'csv', 'docx'],
        help=f"Supported formats: PDF, Excel, Word. Max size: {AppConfig.MAX_FILE_SIZE_MB}MB",
        key="analysis_file_upload"
    )
    
    if uploaded_file:
        # Validate file size
        file_size_mb = uploaded_file.size / (1024 * 1024)
        
        if file_size_mb > AppConfig.MAX_FILE_SIZE_MB:
            st.error(f"❌ File too large ({file_size_mb:.1f}MB). Maximum: {AppConfig.MAX_FILE_SIZE_MB}MB")
            return None
        
        # Display file info
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("File Name", uploaded_file.name)
        with col2:
            st.metric("Size", f"{file_size_mb:.2f} MB")
        with col3:
            st.metric("Type", uploaded_file.type)
        
        st.success(f"✅ File uploaded successfully")
        
        return uploaded_file
    
    return None


# Standalone testing
if __name__ == "__main__":
    st.set_page_config(page_title="Upload Module Test", layout="wide")
    st.title("Upload Module - Standalone Test")
    
    result = render_upload_section()
    
    if result:
        st.write("File would be passed to parser module:")
        st.json({
            "name": result.name,
            "size": result.size,
            "type": result.type
        })
