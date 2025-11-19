"""
Intelligent Parser UI Component
Streamlit interface for 3-stage intelligent parsing system

Integrates with Knowledge page (render_knowledge_page)

Author: HCMPACT
Version: 1.0
"""

import streamlit as st
import os
from pathlib import Path
from intelligent_parser_orchestrator import IntelligentParserOrchestrator
import logging

logger = logging.getLogger(__name__)


def render_intelligent_parser_ui(upload_dir: str = "/data/uploads", output_dir: str = "/data/parsed_registers"):
    """
    Render intelligent parser UI in Knowledge page.
    
    This function should be called from render_knowledge_page() in a new tab.
    
    Args:
        upload_dir: Directory containing uploaded PDFs
        output_dir: Directory for parsed output
    """
    
    st.markdown("### ðŸ§  Intelligent PDF Parser")
    
    st.markdown("""
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1.5rem; border-radius: 12px; color: white; margin-bottom: 1.5rem;'>
        <h4 style='margin: 0 0 0.5rem 0; color: white;'>âš¡ 3-Stage Intelligent Parsing</h4>
        <p style='margin: 0; opacity: 0.95; font-size: 0.95rem;'>
        Automatically selects the best parsing strategy for your document:
        </p>
        <div style='margin-top: 1rem; padding: 0.75rem; background: rgba(255,255,255,0.15); border-radius: 8px;'>
            <strong>Stage 1:</strong> Try saved custom parsers (fastest)<br>
            <strong>Stage 2:</strong> Use adaptive register parsers<br>
            <strong>Stage 3:</strong> Generate new custom parser (learns for next time)
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Ensure directories exist
    os.makedirs(upload_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    # Get list of uploaded PDFs
    pdf_files = [f for f in os.listdir(upload_dir) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        st.info("ðŸ"¤ No PDFs uploaded yet. Upload documents in the **Upload** tab first.")
        return
    
    # File selection
    col1, col2 = st.columns([3, 1])
    
    with col1:
        selected_pdf = st.selectbox(
            "Select PDF to parse:",
            pdf_files,
            help="Choose which PDF to parse with intelligent parser"
        )
    
    with col2:
        force_regenerate = st.checkbox(
            "Force regenerate",
            help="Skip custom/adaptive parsers, force Stage 3 generation"
        )
    
    # Parse button
    if st.button("ðŸš€ Intelligent Parse", type="primary", use_container_width=True):
        pdf_path = os.path.join(upload_dir, selected_pdf)
        
        # Create progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Initialize orchestrator
            status_text.info("ðŸ"§ Initializing intelligent parser...")
            progress_bar.progress(10)
            
            orchestrator = IntelligentParserOrchestrator(custom_parsers_dir="/data/custom_parsers")
            
            # Stage 0: Analyze
            status_text.info("ðŸ" Analyzing PDF structure...")
            progress_bar.progress(20)
            
            # Parse
            status_text.info("âš¡ Parsing with intelligent system...")
            progress_bar.progress(40)
            
            result = orchestrator.parse(pdf_path, force_regenerate=force_regenerate)
            
            progress_bar.progress(90)
            
            # Clear progress
            progress_bar.progress(100)
            status_text.empty()
            progress_bar.empty()
            
            # Display results
            _display_parsing_results(result, selected_pdf, output_dir)
            
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            st.error(f"âŒ Parsing error: {str(e)}")
            logger.error(f"Intelligent parsing error: {e}", exc_info=True)
    
    # Show previously parsed files
    st.markdown("---")
    st.markdown("### ðŸ"‚ Previously Parsed Documents")
    
    _display_parsed_files(output_dir)
    
    # Show custom parsers library
    st.markdown("---")
    st.markdown("### ðŸ"š Custom Parser Library")
    
    _display_custom_parsers("/data/custom_parsers")


def _display_parsing_results(result: Dict[str, Any], filename: str, output_dir: str):
    """Display parsing results with accuracy."""
    
    if not result.get('success'):
        st.error("âŒ Parsing failed")
        st.markdown(f"**Error:** {result.get('error', 'Unknown error')}")
        
        if result.get('recommendations'):
            st.markdown("**Recommendations:**")
            for rec in result['recommendations']:
                st.markdown(f"- {rec}")
        return
    
    # Success banner
    accuracy = result.get('accuracy', 0)
    stage = result.get('stage', 0)
    stage_name = result.get('stage_name', 'unknown')
    method = result.get('method', 'unknown')
    
    # Color based on accuracy
    if accuracy >= 90:
        color = "#28a745"
        emoji = "ðŸŽ‰"
    elif accuracy >= 70:
        color = "#ffc107"
        emoji = "âœ…"
    else:
        color = "#dc3545"
        emoji = "âš ï¸"
    
    st.markdown(f"""
    <div style='background: linear-gradient(135deg, {color} 0%, {color}dd 100%); padding: 1.5rem; border-radius: 12px; color: white; margin-bottom: 1.5rem;'>
        <div style='display: flex; align-items: center; justify-content: space-between;'>
            <div>
                <h3 style='margin: 0; color: white;'>{emoji} Parsing Complete!</h3>
                <p style='margin: 0.5rem 0 0 0; opacity: 0.95;'>
                    Stage {stage}: {stage_name.title()} Parser ({method})
                </p>
            </div>
            <div style='text-align: center; background: rgba(255,255,255,0.2); padding: 1rem; border-radius: 8px;'>
                <div style='font-size: 2.5rem; font-weight: 700;'>{accuracy:.0f}%</div>
                <div style='font-size: 0.9rem; opacity: 0.9;'>Accuracy</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Tables Extracted", len(result.get('tables', [])))
    with col2:
        text_len = len(result.get('text', ''))
        st.metric("Text Length", f"{text_len:,} chars")
    with col3:
        proc_time = result.get('processing_time', 0)
        st.metric("Processing Time", f"{proc_time:.1f}s")
    with col4:
        st.metric("Stage Used", f"Stage {stage}")
    
    # Table details
    tables = result.get('tables', [])
    if tables:
        st.markdown("#### ðŸ"Š Extracted Tables")
        
        for i, table in enumerate(tables, 1):
            with st.expander(f"Table {i}", expanded=(i == 1)):
                if isinstance(table, dict):
                    data = table.get('data')
                    if data is not None:
                        st.dataframe(data.head(10), use_container_width=True)
                        st.caption(f"Showing first 10 of {len(data)} rows")
                else:
                    st.dataframe(table.head(10), use_container_width=True)
    
    # Save to Excel option
    st.markdown("---")
    st.markdown("### ðŸ'¾ Save Results")
    
    if st.button("ðŸ"Š Save as Excel", use_container_width=True):
        try:
            import pandas as pd
            from datetime import datetime
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            excel_filename = f"intelligent_parse_{Path(filename).stem}_{timestamp}.xlsx"
            excel_path = os.path.join(output_dir, excel_filename)
            
            # Save tables to Excel
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                for i, table in enumerate(tables, 1):
                    df = table.get('data') if isinstance(table, dict) else table
                    if df is not None:
                        df.to_excel(writer, sheet_name=f'Table_{i}', index=False)
            
            st.success(f"âœ… Saved to: {excel_filename}")
            
            # Download button
            with open(excel_path, "rb") as f:
                st.download_button(
                    label="ðŸ"¥ Download Excel",
                    data=f.read(),
                    file_name=excel_filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
        
        except Exception as e:
            st.error(f"Error saving: {e}")
    
    # Show parser details
    with st.expander("ðŸ" Parser Details"):
        st.json({
            'stage': stage,
            'stage_name': stage_name,
            'method': method,
            'accuracy': accuracy,
            'processing_time': proc_time,
            'tables_found': len(tables),
            'text_length': text_len
        })


def _display_parsed_files(output_dir: str):
    """Display previously parsed files."""
    
    if not os.path.exists(output_dir):
        st.info("No parsed files yet.")
        return
    
    excel_files = [f for f in os.listdir(output_dir) if f.lower().endswith('.xlsx')]
    
    if not excel_files:
        st.info("No parsed Excel files yet. Parse a PDF above to get started.")
        return
    
    st.success(f"Found {len(excel_files)} parsed file(s)")
    
    for excel_file in sorted(excel_files, reverse=True):
        excel_path = os.path.join(output_dir, excel_file)
        file_size = os.path.getsize(excel_path) / 1024  # KB
        
        col1, col2, col3 = st.columns([4, 1, 1])
        
        with col1:
            st.markdown(f"ðŸ"Š **{excel_file}**")
            st.caption(f"Size: {file_size:.1f} KB")
        
        with col2:
            with open(excel_path, "rb") as f:
                st.download_button(
                    label="ðŸ"¥",
                    data=f.read(),
                    file_name=excel_file,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"dl_intel_{excel_file}"
                )
        
        with col3:
            if st.button("ðŸ—'ï¸", key=f"del_intel_{excel_file}"):
                try:
                    os.remove(excel_path)
                    st.success("Deleted")
                    st.rerun()
                except Exception as e:
                    st.error(f"Delete failed: {e}")


def _display_custom_parsers(parsers_dir: str):
    """Display saved custom parsers."""
    
    if not os.path.exists(parsers_dir):
        st.info("No custom parsers saved yet.")
        return
    
    parser_files = [f for f in os.listdir(parsers_dir) if f.endswith('.py')]
    
    if not parser_files:
        st.info("No custom parsers yet. Successfully parsed documents will be saved as custom parsers for reuse.")
        return
    
    st.success(f"ðŸ"š {len(parser_files)} custom parser(s) available")
    
    for parser_file in sorted(parser_files):
        parser_path = os.path.join(parsers_dir, parser_file)
        
        # Extract info from filename (e.g., custom_payroll_register_85.py)
        parts = parser_file.replace('.py', '').split('_')
        accuracy = parts[-1] if parts[-1].isdigit() else '?'
        doc_type = '_'.join(parts[1:-1]) if len(parts) > 2 else 'unknown'
        
        with st.expander(f"ðŸ" {parser_file} - {doc_type} ({accuracy}% accuracy)"):
            st.markdown(f"**Document Type:** {doc_type}")
            st.markdown(f"**Accuracy:** {accuracy}%")
            st.markdown(f"**Path:** `{parser_path}`")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("ðŸ'€ View Code", key=f"view_{parser_file}"):
                    with open(parser_path, 'r') as f:
                        code = f.read()
                    st.code(code, language='python')
            
            with col2:
                if st.button("ðŸ—'ï¸ Delete", key=f"del_parser_{parser_file}"):
                    try:
                        os.remove(parser_path)
                        st.success("Deleted")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Delete failed: {e}")


# Integration example for render_knowledge_page()
def add_to_knowledge_page():
    """
    Example of how to add this to render_knowledge_page().
    
    In pages/setup/knowledge/__init__.py, add a new tab:
    
    ```python
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "ðŸ"¤ Upload", 
        "ðŸ"Š Status", 
        "ðŸ—'ï¸ Manage", 
        "ðŸ"‹ Parse Registers",
        "ðŸ§  Intelligent Parser"  # NEW TAB
    ])
    
    # ... existing tabs ...
    
    # TAB 5: INTELLIGENT PARSER
    with tab5:
        from utils.parsers.intelligent_parser_ui import render_intelligent_parser_ui
        render_intelligent_parser_ui()
    ```
    """
    pass
