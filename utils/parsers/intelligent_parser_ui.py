"""
Intelligent Parser UI - Enhanced with V2 Support
Provides UI for intelligent PDF parsing with V1/V2 selection
"""

import streamlit as st
import os
from pathlib import Path
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Import both orchestrator versions
try:
    from .intelligent_parser_orchestrator import IntelligentParserOrchestrator
    V1_AVAILABLE = True
except ImportError:
    V1_AVAILABLE = False
    logger.warning("V1 orchestrator not available")

try:
    from .intelligent_parser_orchestrator_v2 import IntelligentParserOrchestratorV2
    V2_AVAILABLE = True
except ImportError:
    V2_AVAILABLE = False
    logger.warning("V2 orchestrator not available")


def render_intelligent_parser_ui():
    """
    Render the intelligent parser UI with V1/V2 selection.
    """
    st.markdown("### Intelligent PDF Parser")
    st.markdown("Automatically detects structure and extracts data from payroll PDFs")
    
    # Check if any parser available
    if not V1_AVAILABLE and not V2_AVAILABLE:
        st.error("No parser versions available. Please ensure parser files are deployed.")
        return
    
    # Directory setup
    upload_dir = "/data/uploads"
    output_dir = "/data/parsed_registers"
    
    # Check for uploaded PDFs
    if not os.path.exists(upload_dir):
        st.warning("Upload directory not found. Upload documents in the Upload tab first.")
        return
    
    pdf_files = [f for f in os.listdir(upload_dir) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        st.info("No PDFs uploaded yet. Upload documents in the Upload tab first.")
        return
    
    # Parser version selection
    st.markdown("#### Parser Version")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        if V2_AVAILABLE:
            use_v2 = st.checkbox(
                "Use V2",
                value=True,
                help="V2: Section-based multi-method (higher accuracy, slower). V1: Single method (faster)."
            )
        else:
            use_v2 = False
            st.info("V2 not available, using V1")
    
    with col2:
        if use_v2 and V2_AVAILABLE:
            st.markdown("""
            **V2 Enhanced Parser**
            - Detects 4 sections independently
            - Tests multiple extraction methods per section
            - Picks best method per section
            - Higher accuracy (typically 75-90%)
            - Slower (10-20 seconds)
            """)
        elif V1_AVAILABLE:
            st.markdown("""
            **V1 Standard Parser**
            - 4-stage system (custom → adaptive → generated → fallback)
            - Single method per document
            - Good accuracy (typically 60-75%)
            - Faster (2-5 seconds)
            """)
    
    st.markdown("---")
    
    # File selection
    st.markdown("#### Select PDF")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        selected_pdf = st.selectbox(
            "PDF to parse:",
            pdf_files,
            help="Choose which PDF to parse"
        )
    
    with col2:
        if use_v2 and V2_AVAILABLE:
            force_v2 = st.checkbox(
                "Force V2",
                value=False,
                help="Don't fall back to V1 even if section detection fails"
            )
        else:
            force_v2 = False
            force_regenerate = st.checkbox(
                "Force regenerate",
                help="Skip saved parsers, force new generation"
            )
    
    # Parse button
    if st.button("Parse Document", type="primary", use_container_width=True):
        pdf_path = os.path.join(upload_dir, selected_pdf)
        
        # Create progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Initialize appropriate orchestrator
            status_text.info(f"Initializing {'V2 Enhanced' if use_v2 else 'V1 Standard'} parser...")
            progress_bar.progress(10)
            
            if use_v2 and V2_AVAILABLE:
                orchestrator = IntelligentParserOrchestratorV2(custom_parsers_dir="/data/custom_parsers")
                result = orchestrator.parse(pdf_path, output_dir=output_dir, force_v2=force_v2)
            elif V1_AVAILABLE:
                orchestrator = IntelligentParserOrchestrator(custom_parsers_dir="/data/custom_parsers")
                result = orchestrator.parse(pdf_path, force_regenerate=force_regenerate if not use_v2 else False)
            else:
                st.error("No parser available")
                return
            
            progress_bar.progress(90)
            
            # Clear progress
            progress_bar.progress(100)
            status_text.empty()
            progress_bar.empty()
            
            # Display results
            _display_parsing_results(result, selected_pdf, output_dir, use_v2)
            
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            st.error(f"Parsing error: {str(e)}")
            logger.error(f"Intelligent parsing error: {e}", exc_info=True)
    
    # Show previously parsed files
    st.markdown("---")
    st.markdown("### Previously Parsed Documents")
    
    _display_parsed_files(output_dir)
    
    # Show custom parsers library (V1 only)
    if V1_AVAILABLE:
        st.markdown("---")
        st.markdown("### Custom Parser Library")
        _display_custom_parsers("/data/custom_parsers")


def _display_parsing_results(result, filename: str, output_dir: str, is_v2: bool = False):
    """Display parsing results with version-specific formatting."""
    
    if result.get('status') == 'success':
        # Success banner
        version_label = result.get('version', 'v2' if is_v2 else 'v1')
        
        st.success(f"Parsing completed successfully! ({version_label.upper()})")
        
        # Metrics
        cols = st.columns(4)
        
        with cols[0]:
            accuracy = result.get('overall_accuracy', result.get('accuracy', 0))
            st.metric("Accuracy", f"{accuracy:.0f}%")
        
        with cols[1]:
            employee_count = result.get('employee_count', 0)
            st.metric("Employees", employee_count)
        
        with cols[2]:
            if is_v2:
                sections_found = result.get('sections_found', {})
                found_count = sum(1 for v in sections_found.values() if v)
                st.metric("Sections Found", f"{found_count}/4")
            else:
                stage = result.get('stage_used', result.get('stage', 'Unknown'))
                st.metric("Stage Used", stage)
        
        with cols[3]:
            tabs = result.get('tabs', {})
            total_rows = sum(tabs.values()) if tabs else 0
            st.metric("Total Rows", total_rows)
        
        # V2-specific: Method per section
        if is_v2 and result.get('methods_used'):
            st.markdown("#### Methods Used Per Section")
            methods = result['methods_used']
            accuracy_per_section = result.get('accuracy_per_section', {})
            
            method_cols = st.columns(4)
            section_names = ['employee_info', 'earnings', 'taxes', 'deductions']
            display_names = ['Employee Info', 'Earnings', 'Taxes', 'Deductions']
            
            for col, section, display_name in zip(method_cols, section_names, display_names):
                with col:
                    if section in methods:
                        method = methods[section]
                        acc = accuracy_per_section.get(section, 0)
                        st.markdown(f"**{display_name}**")
                        st.markdown(f"`{method}`")
                        st.markdown(f"{acc:.0f}% accuracy")
                    else:
                        st.markdown(f"**{display_name}**")
                        st.markdown("Not found")
        
        # Download button
        output_path = result.get('output_path')
        if output_path and os.path.exists(output_path):
            with open(output_path, 'rb') as f:
                st.download_button(
                    label="Download Excel",
                    data=f.read(),
                    file_name=os.path.basename(output_path),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
        
        # Show tabs info
        if tabs:
            st.markdown("#### Extracted Data")
            tab_info = st.columns(4)
            tab_names = ['Employee Summary', 'Earnings', 'Taxes', 'Deductions']
            
            for col, tab_name in zip(tab_info, tab_names):
                with col:
                    row_count = tabs.get(tab_name, 0)
                    st.metric(tab_name, f"{row_count} rows")
    
    elif result.get('status') == 'error':
        st.error(f"Parsing failed: {result.get('message', 'Unknown error')}")
        
        # Show attempted stages/methods
        if is_v2:
            sections = result.get('sections_found', {})
            if sections:
                st.info(f"Sections detected: {sum(1 for v in sections.values() if v)}/4")
        else:
            stages = result.get('stages_attempted', [])
            if stages:
                st.info(f"Attempted {len(stages)} stages")
    
    else:
        st.warning(f"Parsing status: {result.get('status', 'Unknown')}")


def _display_parsed_files(output_dir: str):
    """Display list of previously parsed files."""
    
    if not os.path.exists(output_dir):
        st.info("No parsed files yet")
        return
    
    excel_files = [f for f in os.listdir(output_dir) if f.endswith('.xlsx')]
    
    if not excel_files:
        st.info("No parsed files yet")
        return
    
    # Sort by modification time (newest first)
    excel_files.sort(
        key=lambda x: os.path.getmtime(os.path.join(output_dir, x)),
        reverse=True
    )
    
    # Show recent files
    recent_files = excel_files[:5]
    
    for filename in recent_files:
        filepath = os.path.join(output_dir, filename)
        file_size = os.path.getsize(filepath) / 1024  # KB
        mod_time = datetime.fromtimestamp(os.path.getmtime(filepath))
        
        col1, col2, col3 = st.columns([3, 2, 1])
        
        with col1:
            # Indicate V2 if in filename
            version_badge = " (V2)" if "_v2_" in filename else ""
            st.text(f"{filename}{version_badge}")
        
        with col2:
            st.text(f"{file_size:.1f} KB | {mod_time.strftime('%Y-%m-%d %H:%M')}")
        
        with col3:
            with open(filepath, 'rb') as f:
                st.download_button(
                    "Download",
                    data=f.read(),
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"download_{filename}"
                )


def _display_custom_parsers(parsers_dir: str):
    """Display saved custom parsers (V1 only)."""
    
    if not os.path.exists(parsers_dir):
        st.info("No custom parsers saved yet")
        return
    
    parser_files = [f for f in os.listdir(parsers_dir) if f.endswith('.py')]
    
    if not parser_files:
        st.info("No custom parsers saved yet")
        return
    
    st.text(f"Total custom parsers: {len(parser_files)}")
    
    # Show first few
    for parser_file in parser_files[:5]:
        parser_path = os.path.join(parsers_dir, parser_file)
        file_size = os.path.getsize(parser_path) / 1024  # KB
        
        # Extract accuracy from filename if present
        import re
        acc_match = re.search(r'_(\d+)\.py$', parser_file)
        accuracy = acc_match.group(1) if acc_match else "Unknown"
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.text(f"{parser_file} ({accuracy}% accuracy)")
        
        with col2:
            if st.button("Delete", key=f"delete_{parser_file}"):
                os.remove(parser_path)
                st.rerun()


# Convenience function for backward compatibility
def render_intelligent_parser(orchestrator=None):
    """Legacy function name"""
    render_intelligent_parser_ui()
