"""
HCMPACT LLM Seeding Management
Upload and manage documents for RAG system
"""

import streamlit as st
from datetime import datetime
import PyPDF2
from docx import Document
import pandas as pd


def render_knowledge_page():
    """Render LLM seeding management page"""
    
    st.markdown("## 🧠 HCMPACT LLM Seeding")
    
    st.markdown("""
    <div class='info-box'>
        <strong>LLM Seeding:</strong> Upload HCMPACT standards, best practices,
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
    
    # Handle both basic and advanced RAG formats
    if isinstance(stats, dict) and any(isinstance(v, dict) for v in stats.values()):
        # Advanced RAG format - aggregate across strategies
        total_docs = sum(s.get('unique_documents', 0) for s in stats.values() if isinstance(s, dict))
        total_chunks = sum(s.get('total_chunks', 0) for s in stats.values() if isinstance(s, dict))
    else:
        # Basic RAG format (single collection)
        total_docs = stats.get('unique_documents', 0)
        total_chunks = stats.get('total_chunks', 0)
    
    with col1:
        st.metric("📚 LLM Documents", total_docs)
    with col2:
        st.metric("📝 Total Chunks", total_chunks)
    with col3:
        # Count strategies/collections
        if isinstance(stats, dict) and any(isinstance(v, dict) for v in stats.values()):
            strategies_used = len([s for s in stats.values() if isinstance(s, dict) and s.get('total_chunks', 0) > 0])
        else:
            strategies_used = 1 if total_chunks > 0 else 0
        st.metric("🔧 Strategies", strategies_used)
    with col4:
        # Count categories
        if isinstance(stats, dict) and any(isinstance(v, dict) for v in stats.values()):
            all_categories = set()
            for s in stats.values():
                if isinstance(s, dict):
                    all_categories.update(s.get('categories', {}).keys())
            category_count = len(all_categories)
        else:
            category_count = len(stats.get('categories', {}))
        st.metric("📁 Categories", category_count)
    
    st.markdown("---")
    
    # Upload section
    st.markdown("### 📤 Upload Documents")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_files = st.file_uploader(
            "Upload HCMPACT documents for LLM seeding",
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
        if st.button("🚀 Process and Seed LLM", type="primary", use_container_width=True):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for idx, uploaded_file in enumerate(uploaded_files):
                status_text.info(f"Processing {uploaded_file.name}...")
                
                # Extract text based on file type
                content = _extract_text(uploaded_file)
                
                if content:
                    # Add to LLM seeding
                    result = rag_handler.add_document(
                        name=uploaded_file.name,
                        content=content,
                        category=category,
                        metadata={
                            'upload_date': datetime.now().isoformat(),
                            'file_type': uploaded_file.type
                        },
                        chunking_strategy=chunking_strategy
                    )
                    
                    # Handle both int (basic RAG) and dict (advanced RAG) return values
                    if isinstance(result, dict):
                        chunk_count = sum(result.values())
                    else:
                        chunk_count = result
                    
                    status_text.success(f"✅ Added {uploaded_file.name} - {chunk_count} chunks")
                else:
                    status_text.error(f"❌ Failed to extract text from {uploaded_file.name}")
                
                progress_bar.progress((idx + 1) / len(uploaded_files))
            
            st.success(f"✅ Processed {len(uploaded_files)} document(s)")
            st.rerun()
    
    # Display statistics
    if total_chunks > 0:
        st.markdown("---")
        st.markdown("### 📊 LLM Seeding Statistics")
        
        # Only show strategy breakdown if advanced RAG (multiple strategies)
        if isinstance(stats, dict) and any(isinstance(v, dict) for v in stats.values()):
            # Advanced RAG with multiple strategies
            strategy_tab, category_tab = st.tabs(["By Strategy", "By Category"])
            
            with strategy_tab:
                strategy_data = []
                for strategy_name, strategy_stats in stats.items():
                    if isinstance(strategy_stats, dict) and strategy_stats.get('total_chunks', 0) > 0:
                        strategy_data.append({
                            'Strategy': strategy_name.title(),
                            'Documents': strategy_stats.get('unique_documents', 0),
                            'Chunks': strategy_stats.get('total_chunks', 0)
                        })
                
                if strategy_data:
                    st.dataframe(pd.DataFrame(strategy_data), use_container_width=True, hide_index=True)
            
            with category_tab:
                # Aggregate categories across all strategies
                all_categories = {}
                for strategy_stats in stats.values():
                    if isinstance(strategy_stats, dict):
                        for cat, count in strategy_stats.get('categories', {}).items():
                            all_categories[cat] = all_categories.get(cat, 0) + count
                
                if all_categories:
                    category_data = [
                        {'Category': cat, 'Chunks': count}
                        for cat, count in sorted(all_categories.items(), key=lambda x: x[1], reverse=True)
                    ]
                    st.dataframe(pd.DataFrame(category_data), use_container_width=True, hide_index=True)
        else:
            # Basic RAG - just show categories
            categories = stats.get('categories', {})
            if categories:
                category_data = [
                    {'Category': cat, 'Chunks': count}
                    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)
                ]
                st.dataframe(pd.DataFrame(category_data), use_container_width=True, hide_index=True)
        
        # Clear LLM documents option
        st.markdown("---")
        st.markdown("### 🗑️ Manage LLM Documents")
        
        if st.button("⚠️ Clear All Documents", help="Removes all documents from LLM seeding"):
            if st.checkbox("I understand this will delete all LLM documents"):
                try:
                    # Use clear_all method if available
                    rag_handler.clear_all()
                    st.success("✅ LLM documents cleared")
                    st.rerun()
                except AttributeError:
                    # Fallback for basic RAG without clear_all method
                    try:
                        if hasattr(rag_handler, 'collection'):
                            all_ids = rag_handler.collection.get()['ids']
                            if all_ids:
                                rag_handler.collection.delete(ids=all_ids)
                        st.success("✅ LLM documents cleared")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to clear documents: {str(e)}")


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
    st.title("HCMPACT LLM Seeding - Test")
    render_knowledge_page()
