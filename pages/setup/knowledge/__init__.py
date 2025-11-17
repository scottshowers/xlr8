"""
HCMPACT LLM Seeding Management - FIXED VERSION
Upload and manage documents for RAG system with chunking strategy support
"""

import streamlit as st
from datetime import datetime
import PyPDF2
from docx import Document
import pandas as pd


def render_knowledge_page():
    """Render LLM seeding management page"""
    
    st.markdown("##  HCMPACT LLM Seeding")
    
    st.markdown("""
    <div class='info-box'>
        <strong>LLM Seeding:</strong> Upload HCMPACT standards, best practices,
        and technical documentation. These documents power the AI Assistant's responses.
    </div>
    """, unsafe_allow_html=True)
    
    # Get RAG handler
    rag_handler = st.session_state.get('rag_handler')
    rag_type = st.session_state.get('rag_type', 'basic')
    
    if not rag_handler:
        st.error(" RAG system not initialized")
        st.info(" Make sure the RAG handler is properly configured in session.py")
        return
    
    # Detect if this is advanced RAG
    is_advanced = hasattr(rag_handler, 'chunking_strategies') and rag_handler.chunking_strategies
    
    # Stats - handle both formats
    try:
        stats = rag_handler.get_stats()
        
        # Determine format and calculate totals
        if isinstance(stats, dict) and any(isinstance(v, dict) for v in stats.values()):
            # Advanced RAG format (dict of dicts)
            total_docs = sum(s.get('unique_documents', 0) for s in stats.values() if isinstance(s, dict))
            total_chunks = sum(s.get('total_chunks', 0) for s in stats.values() if isinstance(s, dict))
            strategies_used = len([s for s in stats.values() if isinstance(s, dict) and s.get('total_chunks', 0) > 0])
            
            all_categories = set()
            for s in stats.values():
                if isinstance(s, dict):
                    all_categories.update(s.get('categories', {}).keys())
            category_count = len(all_categories)
        else:
            # Basic RAG format (single dict)
            total_docs = stats.get('unique_documents', 0)
            total_chunks = stats.get('total_chunks', 0)
            strategies_used = 1 if total_chunks > 0 else 0
            category_count = len(stats.get('categories', {}))
    except Exception as e:
        st.error(f"Error getting stats: {str(e)}")
        total_docs = 0
        total_chunks = 0
        strategies_used = 0
        category_count = 0
    
    # Display stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(" Documents", total_docs)
    with col2:
        st.metric(" Total Chunks", total_chunks)
    with col3:
        metric_label = " Strategies" if is_advanced else " Collections"
        st.metric(metric_label, strategies_used)
    with col4:
        st.metric(" Categories", category_count)
    
    # Show RAG type info
    if is_advanced:
        st.success("... Advanced RAG with multiple chunking strategies enabled")
        with st.expander(" Available Chunking Strategies"):
            st.markdown("""
            - **Adaptive** (Recommended): Automatically chooses best strategy based on content
            - **Semantic**: Groups semantically related sentences together
            - **Recursive**: Hierarchical splitting (paragraphs  sentences  words)
            - **Sliding**: Fixed-size chunks with overlap for context preservation
            - **Paragraph**: Maintains paragraph integrity
            - **All**: Uses ALL strategies (creates multiple representations)
            """)
    else:
        st.info(" Using basic RAG (single chunking method)")
    
    st.markdown("---")
    
    # Upload section
    st.markdown("###  Upload Documents")
    
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
        
        # Show chunking strategy selector ONLY for advanced RAG
        if is_advanced:
            chunking_strategy = st.selectbox(
                "Chunking Strategy",
                ["adaptive", "semantic", "recursive", "sliding", "paragraph", "all"],
                help="How to split the document. 'adaptive' automatically chooses the best method."
            )
        else:
            chunking_strategy = None
    
    if uploaded_files:
        if st.button(" Process and Seed LLM", type="primary", use_container_width=True):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            total_files = len(uploaded_files)
            
            for idx, uploaded_file in enumerate(uploaded_files):
                status_text.info(f"Processing {uploaded_file.name}... ({idx+1}/{total_files})")
                
                # Extract text
                content = _extract_text(uploaded_file)
                
                if content:
                    try:
                        # Build kwargs for add_document
                        kwargs = {
                            'name': uploaded_file.name,
                            'content': content,
                            'category': category,
                            'metadata': {
                                'upload_date': datetime.now().isoformat(),
                                'file_type': uploaded_file.type,
                                'file_size': len(content)
                            }
                        }
                        
                        # Add chunking_strategy ONLY if advanced RAG
                        if is_advanced and chunking_strategy:
                            kwargs['chunking_strategy'] = chunking_strategy
                        
                        # Call add_document
                        result = rag_handler.add_document(**kwargs)
                        
                        # Handle return value (int for basic, dict for advanced)
                        if isinstance(result, dict):
                            # Advanced RAG: dict of strategy -> chunk_count
                            total_chunk_count = sum(result.values())
                            strategy_info = ", ".join([f"{k}: {v}" for k, v in result.items()])
                            status_text.success(f"... {uploaded_file.name}: {total_chunk_count} chunks ({strategy_info})")
                        else:
                            # Basic RAG: just a number
                            status_text.success(f"... {uploaded_file.name}: {result} chunks")
                    
                    except Exception as e:
                        status_text.error(f" Error processing {uploaded_file.name}: {str(e)}")
                        import traceback
                        with st.expander("Error details"):
                            st.code(traceback.format_exc())
                else:
                    status_text.error(f" Failed to extract text from {uploaded_file.name}")
                
                progress_bar.progress((idx + 1) / total_files)
            
            st.success(f"... Processed {total_files} document(s)")
            st.balloons()
            
            # Small delay to show success message
            import time
            time.sleep(1)
            
            # Rerun to refresh stats
            st.rerun()
    
    # Display detailed statistics
    if total_chunks > 0:
        st.markdown("---")
        st.markdown("###  LLM Base Statistics")
        
        try:
            if is_advanced:
                # Advanced RAG - show strategy breakdown and categories
                strategy_tab, category_tab = st.tabs([" By Strategy", " By Category"])
                
                with strategy_tab:
                    st.markdown("#### Chunks by Chunking Strategy")
                    strategy_data = []
                    
                    for strategy_name, strategy_stats in stats.items():
                        if isinstance(strategy_stats, dict) and strategy_stats.get('total_chunks', 0) > 0:
                            strategy_data.append({
                                'Strategy': strategy_name.title(),
                                'Documents': strategy_stats.get('unique_documents', 0),
                                'Chunks': strategy_stats.get('total_chunks', 0),
                                'Avg Chunks/Doc': round(strategy_stats.get('total_chunks', 0) / 
                                                       max(strategy_stats.get('unique_documents', 1), 1), 1)
                            })
                    
                    if strategy_data:
                        df = pd.DataFrame(strategy_data)
                        st.dataframe(df, use_container_width=True, hide_index=True)
                        
                        # Visual chart
                        st.bar_chart(df.set_index('Strategy')['Chunks'])
                
                with category_tab:
                    st.markdown("#### Chunks by Category")
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
                        df = pd.DataFrame(category_data)
                        st.dataframe(df, use_container_width=True, hide_index=True)
                        
                        # Visual chart
                        st.bar_chart(df.set_index('Category')['Chunks'])
            else:
                # Basic RAG - just show categories
                st.markdown("#### Chunks by Category")
                categories = stats.get('categories', {})
                if categories:
                    category_data = [
                        {'Category': cat, 'Chunks': count}
                        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)
                    ]
                    df = pd.DataFrame(category_data)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    
                    # Visual chart
                    st.bar_chart(df.set_index('Category')['Chunks'])
        
        except Exception as e:
            st.warning(f"Could not display detailed statistics: {str(e)}")
        
        # Management section
        st.markdown("---")
        st.markdown("### - Manage Knowledge Base")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.warning(" **Clear All Documents**: This will permanently delete all documents from the knowledge base.")
        
        with col2:
            if st.button("- Clear All", type="secondary", use_container_width=True):
                # Use a confirmation checkbox
                st.session_state.confirm_clear = True
        
        if st.session_state.get('confirm_clear', False):
            st.error(" **Are you sure?** This action cannot be undone!")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("... Yes, Clear All", type="primary"):
                    try:
                        rag_handler.clear_all()
                        st.success("... All documents cleared from knowledge base")
                        st.session_state.confirm_clear = False
                        import time
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f" Failed to clear: {str(e)}")
            
            with col2:
                if st.button(" Cancel"):
                    st.session_state.confirm_clear = False
                    st.rerun()


def _extract_text(uploaded_file) -> str:
    """
    Extract text from uploaded file
    
    Args:
        uploaded_file: Streamlit uploaded file object
        
    Returns:
        Extracted text content or None if failed
    """
    
    try:
        file_type = uploaded_file.name.split('.')[-1].lower()
        
        if file_type == 'pdf':
            # Extract from PDF
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            text = ""
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"
            return text.strip()
        
        elif file_type == 'docx':
            # Extract from Word document
            doc = Document(uploaded_file)
            text = "\n\n".join([para.text for para in doc.paragraphs if para.text.strip()])
            return text
        
        elif file_type in ['txt', 'md']:
            # Plain text or markdown
            text = uploaded_file.read().decode('utf-8')
            return text
        
        else:
            st.error(f"Unsupported file type: {file_type}")
            return None
            
    except Exception as e:
        st.error(f"Error extracting text: {str(e)}")
        import traceback
        with st.expander("Error details"):
            st.code(traceback.format_exc())
        return None


# For testing
if __name__ == "__main__":
    st.set_page_config(page_title="HCMPACT LLM Seeding - Test", layout="wide")
    st.title("HCMPACT LLM Seeding - Test Mode")
    render_knowledge_page()
