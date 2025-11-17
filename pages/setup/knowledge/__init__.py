"""
HCMPACT LLM Seeding - Progress v2 with forced UI updates
"""

import streamlit as st
from datetime import datetime
import PyPDF2
from docx import Document
import pandas as pd
import time


def render_knowledge_page():
    """Render LLM seeding page"""
    
    st.markdown("## HCMPACT LLM Seeding")
    
    st.markdown("""
    <div class='info-box'>
        <strong>LLM Seeding:</strong> Upload HCMPACT standards, best practices,
        and technical documentation.
    </div>
    """, unsafe_allow_html=True)
    
    rag_handler = st.session_state.get('rag_handler')
    
    if not rag_handler:
        st.error("RAG system not initialized")
        return
    
    is_advanced = hasattr(rag_handler, 'chunking_strategies') and rag_handler.chunking_strategies
    
    # Get stats
    try:
        stats = rag_handler.get_stats()
        
        if isinstance(stats, dict) and any(isinstance(v, dict) for v in stats.values()):
            total_docs = sum(s.get('unique_documents', 0) for s in stats.values() if isinstance(s, dict))
            total_chunks = sum(s.get('total_chunks', 0) for s in stats.values() if isinstance(s, dict))
            strategies_used = len([s for s in stats.values() if isinstance(s, dict) and s.get('total_chunks', 0) > 0])
            
            all_categories = set()
            for s in stats.values():
                if isinstance(s, dict):
                    all_categories.update(s.get('categories', {}).keys())
            category_count = len(all_categories)
        else:
            total_docs = stats.get('unique_documents', 0)
            total_chunks = stats.get('total_chunks', 0)
            strategies_used = 1 if total_chunks > 0 else 0
            category_count = len(stats.get('categories', {}))
    except Exception as e:
        st.error(f"Error getting stats: {str(e)}")
        total_docs = total_chunks = strategies_used = category_count = 0
    
    # Display stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Documents", total_docs)
    with col2:
        st.metric("Total Chunks", total_chunks)
    with col3:
        st.metric("Strategies" if is_advanced else "Collections", strategies_used)
    with col4:
        st.metric("Categories", category_count)
    
    if is_advanced:
        st.success("Advanced RAG enabled")
    
    st.markdown("---")
    st.markdown("### Upload Documents")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_files = st.file_uploader(
            "Upload HCMPACT documents",
            type=['pdf', 'txt', 'md', 'docx'],
            accept_multiple_files=True,
            help="Upload standards, best practices, guides"
        )
    
    with col2:
        category = st.selectbox(
            "Category",
            ["PRO Core", "WFM", "Payroll", "Benefits", "Time & Attendance", 
             "Best Practices", "Technical", "Implementation Guides", "Other"]
        )
        
        if is_advanced:
            chunking_strategy = st.selectbox(
                "Chunking Strategy",
                ["adaptive", "semantic", "recursive", "sliding", "paragraph", "all"],
                help="'adaptive' automatically chooses best method"
            )
        else:
            chunking_strategy = None
    
    if uploaded_files:
        if st.button("Process and Seed LLM", type="primary", use_container_width=True):
            print(f"[UPLOAD] Starting upload of {len(uploaded_files)} files")
            
            # Create placeholders OUTSIDE the loop
            progress_placeholder = st.empty()
            status_placeholder = st.empty()
            
            total_files = len(uploaded_files)
            
            for idx, uploaded_file in enumerate(uploaded_files):
                print(f"[UPLOAD] Processing file {idx+1}/{total_files}: {uploaded_file.name}")
                
                # Update status FIRST
                status_placeholder.info(f"Processing {uploaded_file.name}... ({idx+1}/{total_files})")
                progress_placeholder.progress((idx) / total_files)
                
                start_time = time.time()
                
                # Extract text
                content = _extract_text(uploaded_file)
                extract_time = time.time() - start_time
                print(f"[UPLOAD] Text extraction took {extract_time:.2f}s")
                
                if content:
                    try:
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
                        
                        if is_advanced and chunking_strategy:
                            kwargs['chunking_strategy'] = chunking_strategy
                        
                        # Process document
                        chunk_start = time.time()
                        result = rag_handler.add_document(**kwargs)
                        chunk_time = time.time() - chunk_start
                        
                        print(f"[UPLOAD] Chunking/embedding took {chunk_time:.2f}s")
                        
                        # Show result
                        if isinstance(result, dict):
                            total_chunk_count = sum(result.values())
                            strategy_info = ", ".join([f"{k}: {v}" for k, v in result.items()])
                            status_placeholder.success(f"SUCCESS: {uploaded_file.name} - {total_chunk_count} chunks ({strategy_info})")
                        else:
                            status_placeholder.success(f"SUCCESS: {uploaded_file.name} - {result} chunks")
                    
                    except Exception as e:
                        print(f"[UPLOAD] ERROR: {str(e)}")
                        status_placeholder.error(f"ERROR: {uploaded_file.name} - {str(e)}")
                        import traceback
                        traceback.print_exc()
                else:
                    status_placeholder.error(f"Failed to extract text from {uploaded_file.name}")
                
                # Update progress
                progress_placeholder.progress((idx + 1) / total_files)
            
            status_placeholder.success(f"Processed {total_files} document(s)")
            st.balloons()
            
            print("[UPLOAD] Complete, reloading page...")
            time.sleep(2)
            st.rerun()
    
    # Statistics section
    if total_chunks > 0:
        st.markdown("---")
        st.markdown("### LLM Base Statistics")
        
        try:
            if is_advanced:
                strategy_tab, category_tab = st.tabs(["By Strategy", "By Category"])
                
                with strategy_tab:
                    st.markdown("#### Chunks by Strategy")
                    strategy_data = []
                    
                    for strategy_name, strategy_stats in stats.items():
                        if isinstance(strategy_stats, dict) and strategy_stats.get('total_chunks', 0) > 0:
                            strategy_data.append({
                                'Strategy': strategy_name.title(),
                                'Documents': strategy_stats.get('unique_documents', 0),
                                'Chunks': strategy_stats.get('total_chunks', 0)
                            })
                    
                    if strategy_data:
                        df = pd.DataFrame(strategy_data)
                        st.dataframe(df, use_container_width=True, hide_index=True)
                        st.bar_chart(df.set_index('Strategy')['Chunks'])
                
                with category_tab:
                    st.markdown("#### Chunks by Category")
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
                        st.bar_chart(df.set_index('Category')['Chunks'])
        except Exception as e:
            st.warning(f"Could not display statistics: {str(e)}")


def _extract_text(uploaded_file) -> str:
    """Extract text from uploaded file"""
    
    try:
        file_type = uploaded_file.name.split('.')[-1].lower()
        
        if file_type == 'pdf':
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            text = ""
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"
            return text.strip()
        
        elif file_type == 'docx':
            doc = Document(uploaded_file)
            text = "\n\n".join([para.text for para in doc.paragraphs if para.text.strip()])
            return text
        
        elif file_type in ['txt', 'md']:
            text = uploaded_file.read().decode('utf-8')
            return text
        
        else:
            st.error(f"Unsupported file type: {file_type}")
            return None
            
    except Exception as e:
        st.error(f"Error extracting text: {str(e)}")
        return None
