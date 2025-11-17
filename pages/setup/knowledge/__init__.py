"""
HCMPACT Knowledge Base Management
Upload and manage documents for RAG system

FIXED VERSION - November 17, 2025
Handles both basic RAGHandler and AdvancedRAGHandler stats formats
"""

import streamlit as st
from datetime import datetime
import PyPDF2
from docx import Document
import pandas as pd


def render_knowledge_page():
    """Render knowledge base management page"""
    
    st.markdown("## 🧠 HCMPACT Knowledge Base")
    
    st.markdown("""
    <div class='info-box'>
        <strong>Knowledge Base:</strong> Upload HCMPACT standards, best practices,
        and technical documentation. These documents power the AI Assistant's responses.
    </div>
    """, unsafe_allow_html=True)
    
    # Get RAG handler
    rag_handler = st.session_state.get('rag_handler')
    
    if not rag_handler:
        st.error("❌ RAG system not initialized")
        return
    
    # Get stats - handle both basic and advanced RAG handler formats
    try:
        stats = rag_handler.get_stats()
        
        # Check if this is basic RAGHandler (single dict) or AdvancedRAGHandler (dict of dicts)
        if stats and 'total_chunks' in stats:
            # Basic RAGHandler format
            total_docs = stats.get('unique_documents', 0)
            total_chunks = stats.get('total_chunks', 0)
            categories = stats.get('categories', {})
            strategies_used = 1  # Only one collection
        else:
            # AdvancedRAGHandler format (dict of dicts per strategy)
            total_docs = sum(s.get('unique_documents', 0) for s in stats.values() if isinstance(s, dict))
            total_chunks = sum(s.get('total_chunks', 0) for s in stats.values() if isinstance(s, dict))
            
            # Merge categories from all strategies
            categories = {}
            for s in stats.values():
                if isinstance(s, dict) and 'categories' in s:
                    for cat, count in s['categories'].items():
                        categories[cat] = categories.get(cat, 0) + count
            
            strategies_used = len([s for s in stats.values() if isinstance(s, dict) and s.get('total_chunks', 0) > 0])
    except Exception as e:
        st.error(f"Error getting stats: {e}")
        total_docs = 0
        total_chunks = 0
        categories = {}
        strategies_used = 0
    
    # Display stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📚 Documents", total_docs)
    with col2:
        st.metric("📝 Total Chunks", total_chunks)
    with col3:
        st.metric("🔧 Strategies", strategies_used)
    with col4:
        st.metric("📁 Categories", len(categories))
    
    st.markdown("---")
    
    # Upload section
    st.markdown("### 📤 Upload Documents")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_files = st.file_uploader(
            "Upload HCMPACT documents",
            type=['pdf', 'txt', 'md', 'docx'],
            accept_multiple_files=True,
            help="Upload standards, best practices, guides, or technical documentation"
        )
    
    with col2:
        category = st.selectbox(
            "Category",
            ["PRO Core", "WFM", "Payroll", "Benefits", "Time & Attendance", 
             "Best Practices", "Technical", "Implementation Guides", "Templates",
             "Configuration", "Other"],
            help="Categorize your document"
        )
    
    if uploaded_files:
        if st.button("📤 Upload & Index Documents", type="primary"):
            with st.spinner("Processing documents..."):
                success_count = 0
                error_count = 0
                
                for uploaded_file in uploaded_files:
                    try:
                        # Extract text based on file type
                        if uploaded_file.name.endswith('.pdf'):
                            content = _extract_pdf_text(uploaded_file)
                        elif uploaded_file.name.endswith('.docx'):
                            content = _extract_docx_text(uploaded_file)
                        elif uploaded_file.name.endswith(('.txt', '.md')):
                            content = uploaded_file.read().decode('utf-8')
                        else:
                            st.warning(f"Skipping {uploaded_file.name} - unsupported format")
                            continue
                        
                        if not content or len(content.strip()) < 50:
                            st.warning(f"Skipping {uploaded_file.name} - no content extracted")
                            error_count += 1
                            continue
                        
                        # Add to RAG handler
                        num_chunks = rag_handler.add_document(
                            name=uploaded_file.name,
                            content=content,
                            category=category,
                            metadata={
                                'upload_date': datetime.now().isoformat(),
                                'file_size': len(content)
                            }
                        )
                        
                        st.success(f"✅ Indexed {num_chunks} chunks from **{uploaded_file.name}**")
                        success_count += 1
                        
                    except Exception as e:
                        st.error(f"❌ Error processing {uploaded_file.name}: {str(e)}")
                        error_count += 1
                
                # Summary
                st.markdown("---")
                if success_count > 0:
                    st.success(f"🎉 Successfully uploaded {success_count} document(s)")
                if error_count > 0:
                    st.warning(f"⚠️ {error_count} document(s) had errors")
                
                # Refresh stats
                st.rerun()
    
    st.markdown("---")
    
    # Current documents section
    st.markdown("### 📚 Current Knowledge Base")
    
    if total_docs == 0:
        st.info("📭 No documents uploaded yet. Upload HCMPACT standards above to get started!")
    else:
        # Show categories breakdown
        if categories:
            st.markdown("**Documents by Category:**")
            for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
                st.markdown(f"- **{cat}:** {count} chunks")
        
        # Management options
        st.markdown("---")
        st.markdown("### 🔧 Management")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔍 Test Search", use_container_width=True):
                st.session_state.show_search_test = True
        
        with col2:
            if st.button("🗑️ Clear All Documents", use_container_width=True, type="secondary"):
                st.session_state.confirm_clear = True
        
        # Search test
        if st.session_state.get('show_search_test', False):
            st.markdown("---")
            st.markdown("### 🔍 Test Search")
            
            test_query = st.text_input("Enter a test query", value="earnings configuration")
            num_results = st.slider("Number of results", 1, 20, 8)
            
            if st.button("Search"):
                with st.spinner("Searching..."):
                    try:
                        results = rag_handler.search(test_query, n_results=num_results)
                        
                        if results:
                            st.success(f"✅ Found {len(results)} results")
                            
                            for i, result in enumerate(results, 1):
                                with st.expander(f"Result {i}: {result.get('document', 'Unknown')}", expanded=(i<=3)):
                                    st.markdown(f"**Document:** {result.get('document', 'N/A')}")
                                    st.markdown(f"**Category:** {result.get('category', 'N/A')}")
                                    
                                    if 'distance' in result:
                                        similarity = 1.0 - result['distance']
                                        st.markdown(f"**Relevance:** {similarity:.0%}")
                                    
                                    if 'content' in result:
                                        content = result['content']
                                        preview = content[:300] + "..." if len(content) > 300 else content
                                        st.markdown("**Content:**")
                                        st.text(preview)
                        else:
                            st.warning("⚠️ No results found")
                            st.markdown("""
                            **Possible reasons:**
                            - Query too specific
                            - No relevant documents uploaded
                            - Try broader search terms
                            """)
                    except Exception as e:
                        st.error(f"Search error: {e}")
        
        # Clear confirmation
        if st.session_state.get('confirm_clear', False):
            st.markdown("---")
            st.warning("⚠️ **Warning:** This will delete ALL documents from the knowledge base!")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Yes, Clear Everything", type="primary"):
                    try:
                        rag_handler.clear_collection()
                        st.success("✅ All documents cleared")
                        st.session_state.confirm_clear = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error clearing: {e}")
            
            with col2:
                if st.button("❌ Cancel"):
                    st.session_state.confirm_clear = False
                    st.rerun()


def _extract_pdf_text(uploaded_file) -> str:
    """Extract text from PDF file"""
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        raise Exception(f"PDF extraction failed: {str(e)}")


def _extract_docx_text(uploaded_file) -> str:
    """Extract text from DOCX file"""
    try:
        doc = Document(uploaded_file)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text
    except Exception as e:
        raise Exception(f"DOCX extraction failed: {str(e)}")


# Main entry point
if __name__ == "__main__":
    render_knowledge_page()
