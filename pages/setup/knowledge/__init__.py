"""
HCMPACT LLM Seeding - With visible error tracking
"""

import streamlit as st
from datetime import datetime
import PyPDF2
from docx import Document
import pandas as pd
import time
import traceback


def render_knowledge_page():
    """Render LLM seeding page"""
    
    st.markdown("## [*] HCMPACT LLM Seeding")
    
    st.markdown("""
    <div class='info-box'>
        <strong>LLM Seeding:</strong> Upload HCMPACT standards and documentation.
    </div>
    """, unsafe_allow_html=True)
    
    rag_handler = st.session_state.get('rag_handler')
    
    if not rag_handler:
        st.error("[X] RAG system not initialized")
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
        st.error(f"[X] Error getting stats: {str(e)}")
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
        st.success("[OK] Advanced RAG enabled")
    
    st.markdown("---")
    st.markdown("### [UP] Upload Documents")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_files = st.file_uploader(
            "Upload HCMPACT documents",
            type=['pdf', 'txt', 'md', 'docx'],
            accept_multiple_files=True
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
                ["adaptive", "semantic", "recursive", "sliding", "paragraph", "all"]
            )
        else:
            chunking_strategy = None
    
    if uploaded_files:
        if st.button("[>>] Process and Seed LLM", type="primary", use_container_width=True):
            
            # Create VISIBLE status area
            status_area = st.empty()
            progress_area = st.empty()
            error_area = st.empty()
            
            total_files = len(uploaded_files)
            
            with status_area.container():
                st.info(f"Starting upload of {total_files} file(s)...")
            
            for idx, uploaded_file in enumerate(uploaded_files):
                try:
                    # Show current file
                    with status_area.container():
                        st.info(f"[{idx+1}/{total_files}] Processing: {uploaded_file.name}")
                    
                    with progress_area.container():
                        st.progress((idx) / total_files)
                    
                    # STEP 1: Extract text
                    with status_area.container():
                        st.info(f"[{idx+1}/{total_files}] Extracting text from {uploaded_file.name}...")
                    
                    extract_start = time.time()
                    content = _extract_text(uploaded_file)
                    extract_time = time.time() - extract_start
                    
                    if not content:
                        with error_area.container():
                            st.error(f"[X] Failed to extract text from {uploaded_file.name}")
                        continue
                    
                    with status_area.container():
                        st.info(f"[{idx+1}/{total_files}] Extracted {len(content)} characters in {extract_time:.1f}s")
                    
                    # STEP 2: Chunk and embed
                    with status_area.container():
                        st.info(f"[{idx+1}/{total_files}] Chunking and embedding {uploaded_file.name}... (this may take 30-60 seconds)")
                    
                    chunk_start = time.time()
                    
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
                    
                    # THE CRITICAL CALL - wrap in try/catch
                    try:
                        result = rag_handler.add_document(**kwargs)
                    except Exception as chunk_error:
                        with error_area.container():
                            st.error(f"[X] CHUNKING ERROR for {uploaded_file.name}")
                            st.error(f"Error: {str(chunk_error)}")
                            with st.expander("Full Error Details"):
                                st.code(traceback.format_exc())
                        continue
                    
                    chunk_time = time.time() - chunk_start
                    
                    # Show success
                    with status_area.container():
                        if isinstance(result, dict):
                            total_chunk_count = sum(result.values())
                            strategy_info = ", ".join([f"{k}: {v}" for k, v in result.items()])
                            st.success(f"[OK] {uploaded_file.name}: {total_chunk_count} chunks ({strategy_info}) - took {chunk_time:.1f}s")
                        else:
                            st.success(f"[OK] {uploaded_file.name}: {result} chunks - took {chunk_time:.1f}s")
                
                except Exception as file_error:
                    with error_area.container():
                        st.error(f"[X] UNEXPECTED ERROR processing {uploaded_file.name}")
                        st.error(f"Error: {str(file_error)}")
                        with st.expander("Full Error Details"):
                            st.code(traceback.format_exc())
                
                with progress_area.container():
                    st.progress((idx + 1) / total_files)
            
            # Final success
            with status_area.container():
                st.success(f"[OK] Completed processing {total_files} document(s)")
            
            st.balloons()
            time.sleep(2)
            st.rerun()
    
    # Statistics section (collapsed for space)
    if total_chunks > 0:
        with st.expander("View LLM Base Statistics"):
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
            return None
            
    except Exception as e:
        st.error(f"[X] Text extraction error: {str(e)}")
        return None
