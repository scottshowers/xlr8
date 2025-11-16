"""
HCMPACT Knowledge Base Management - WITH EMPTY STATE ✨
Upload and manage documents for RAG system
Quick Win #4: Added empty state when no documents
"""

import streamlit as st
from datetime import datetime
import PyPDF2
from docx import Document
import pandas as pd


def render_knowledge_page():
    """Render knowledge base management page with empty state"""
    
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
    
    # EMPTY STATE CHECK ✨
    if total_docs == 0:
        st.markdown("""
        <div style='text-align: center; padding: 4rem 1rem; background: linear-gradient(135deg, #f5f7f9 0%, #e8eef3 100%); border-radius: 16px; border: 2px dashed #8ca6be; margin: 2rem 0;'>
            <div style='font-size: 4rem; margin-bottom: 1rem; opacity: 0.9;'>📚</div>
            <h2 style='color: #6d8aa0; margin-bottom: 1rem; font-size: 1.8rem;'>Knowledge Base is Empty</h2>
            <p style='color: #7d96a8; font-size: 1.1rem; margin-bottom: 2rem; max-width: 600px; margin-left: auto; margin-right: auto;'>
                Upload HCMPACT standards, UKG documentation, and best practices to power your AI Assistant
            </p>
            <div style='background: white; padding: 2rem; border-radius: 12px; max-width: 500px; margin: 0 auto; box-shadow: 0 4px 12px rgba(0,0,0,0.08);'>
                <h3 style='color: #6d8aa0; margin-bottom: 1rem; font-size: 1.2rem;'>📤 What to Upload First</h3>
                <div style='text-align: left; color: #6c757d; line-height: 2;'>
                    • UKG Pro configuration guides<br>
                    • UKG WFM documentation<br>
                    • Implementation best practices<br>
                    • Standard templates & checklists<br>
                    • Industry compliance guides<br>
                    • Troubleshooting documentation
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Show example with more detail
        with st.expander("💡 Why Upload Documents to Knowledge Base?", expanded=True):
            st.markdown("""
            **Your AI Assistant becomes smarter with each document you upload:**
            
            **Without Knowledge Base:**
            - Generic responses based only on general AI training
            - No company-specific context
            - Limited to basic UKG information
            
            **With Knowledge Base:**
            - Responds with your company's best practices
            - References specific HCMPACT standards
            - Pulls from actual UKG documentation
            - Provides accurate, context-aware guidance
            
            **Example:**
            
            *Question:* "How should we configure multi-tier approvals?"
            
            *Without docs:* Generic explanation
            
            *With docs:* Specific steps from your standards, references to exact UKG screens, 
            best practices from your implementation guides
            
            **🎯 Recommended Starter Pack (5-10 documents):**
            1. UKG Pro Administration Guide
            2. Your implementation methodology
            3. Standard pay code template
            4. Time & attendance best practices
            5. Benefits configuration checklist
            """)
    
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
    
    # Display statistics by strategy (only if documents exist)
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
