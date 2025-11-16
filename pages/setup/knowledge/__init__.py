
"""
HCMPACT Knowledge Base Management
Upload and manage documents for RAG system
"""

import streamlit as st
from datetime import datetime
import PyPDF2
from docx import Document
import pandas as pd


def render_knowledge_page():
    """Render knowledge base management page"""
    
    st.markdown("## 🧠 HCMPACT Local LLM Seeding")
    
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
    
    # Stats
    stats = rag_handler.get_stats()
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_docs = sum(s['unique_documents'] for s in stats.values())
    total_chunks = sum(s['total_chunks'] for s in stats.values())
    
    with col1:
        st.metric("📚 Documents", total_docs)
    with col2:
        st.metric("📝 Total Chunks", total_chunks)
    with col3:
        strategies_used = len([s for s in stats.values() if s['total_chunks'] > 0])
        st.metric("🔧 Strategies", strategies_used)
    with col4:
        all_categories = set()
        for s in stats.values():
            all_categories.update(s['categories'].keys())
        st.metric("📁 Categories", len(all_categories))
    
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
             "Best Practices", "Technical", "Implementation Guides", "Other"],
            help="Categorize your document"
        )
        
        chunking_strategy = st.selectbox(
            "Chunking Strategy",
            ["adaptive", "semantic", "recursive", "sliding", "paragraph", "all"],
            help="How to split the document. 'adaptive' automatically chooses best method."
        )
    
    if uploaded_files:
        if st.button("🚀 Process and Add to Knowledge Base", type="primary", use_container_width=True):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for idx, uploaded_file in enumerate(uploaded_files):
                status_text.info(f"Processing {uploaded_file.name}...")
                
                # Extract text based on file type
                content = _extract_text(uploaded_file)
                
                if content:
                    # Add to knowledge base
                    counts = rag_handler.add_document(
                        name=uploaded_file.name,
                        content=content,
                        category=category,
                        metadata={
                            'upload_date': datetime.now().isoformat(),
                            'file_type': uploaded_file.type
                        },
                        chunking_strategy=chunking_strategy
                    )
                    
                    status_text.success(f"✅ Added {uploaded_file.name} - {sum(counts.values())} chunks")
                else:
                    status_text.error(f"❌ Failed to extract text from {uploaded_file.name}")
                
                progress_bar.progress((idx + 1) / len(uploaded_files))
            
            st.success(f"✅ Processed {len(uploaded_files)} document(s)")
            st.rerun()
    
    # Display statistics by strategy
    if total_chunks > 0:
        st.markdown("---")
        st.markdown("### 📊 Knowledge Base Statistics")
        
        # Strategy breakdown
        strategy_tab, category_tab = st.tabs(["By Strategy", "By Category"])
        
        with strategy_tab:
            strategy_data = []
            for strategy_name, strategy_stats in stats.items():
                if strategy_stats['total_chunks'] > 0:
                    strategy_data.append({
                        'Strategy': strategy_name.title(),
                        'Documents': strategy_stats['unique_documents'],
                        'Chunks': strategy_stats['total_chunks']
                    })
            
            if strategy_data:
                st.dataframe(pd.DataFrame(strategy_data), use_container_width=True, hide_index=True)
        
        with category_tab:
            # Aggregate categories across all strategies
            all_categories = {}
            for strategy_stats in stats.values():
                for cat, count in strategy_stats['categories'].items():
                    all_categories[cat] = all_categories.get(cat, 0) + count
            
            if all_categories:
                category_data = [
                    {'Category': cat, 'Chunks': count}
                    for cat, count in sorted(all_categories.items(), key=lambda x: x[1], reverse=True)
                ]
                st.dataframe(pd.DataFrame(category_data), use_container_width=True, hide_index=True)
        
        # Clear knowledge base option
        st.markdown("---")
        st.markdown("### 🗑️ Manage Knowledge Base")
        
        if st.button("⚠️ Clear All Documents", help="Removes all documents from knowledge base"):
            if st.checkbox("I understand this will delete all knowledge base documents"):
                for collection in rag_handler.collections.values():
                    try:
                        # Clear collection
                        all_ids = collection.get()['ids']
                        if all_ids:
                            collection.delete(ids=all_ids)
                    except:
                        pass
                st.success("✅ Knowledge base cleared")
                st.rerun()


def _extract_text(uploaded_file) -> str:
    """Extract text from uploaded file"""
    
    try:
        file_type = uploaded_file.name.split('.')[-1].lower()
        
        if file_type == 'pdf':
            # PDF extraction
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n\n"
            return text
        
        elif file_type == 'docx':
            # Word document
            doc = Document(uploaded_file)
            text = "\n\n".join([para.text for para in doc.paragraphs])
            return text
        
        elif file_type in ['txt', 'md']:
            # Plain text
            text = uploaded_file.read().decode('utf-8')
            return text
        
        else:
            return None
            
    except Exception as e:
        st.error(f"Error extracting text: {str(e)}")
        return None


if __name__ == "__main__":
    st.title("Knowledge Base - Test")
    render_knowledge_page()
