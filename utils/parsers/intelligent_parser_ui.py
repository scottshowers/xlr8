"""
Intelligent Parser UI - Complete with Class and Function
Shows parsing results with clear success/failure status
"""

import streamlit as st
from pathlib import Path
import pandas as pd
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class IntelligentParserUI:
    """
    UI class for intelligent PDF parsing.
    Wrapper for backwards compatibility.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def render(self):
        """Render the parser UI."""
        render_intelligent_parser_ui()


def render_intelligent_parser_ui():
    """
    Main UI for intelligent PDF parsing with status display.
    """
    st.header("Intelligent PDF Parser")
    
    st.markdown("""
    Advanced PDF parsing with multi-stage fallback:
    - **Stage 1:** Custom parsers (saved from previous parses)
    - **Stage 2:** Adaptive parsers (payroll/register specific)
    - **Stage 3:** Generated parsers (auto-creates custom code)
    
    Analyzes structure and picks the best parsing strategy automatically.
    """)
    
    # Check for uploaded PDFs
    uploads_dir = Path('/data/uploads')
    if not uploads_dir.exists() or not list(uploads_dir.glob('*.pdf')):
        st.warning("📁 No PDFs found. Upload PDFs in the 'Document Upload' tab first.")
        return
    
    # PDF selection
    pdf_files = sorted(uploads_dir.glob('*.pdf'))
    pdf_names = [f.name for f in pdf_files]
    
    selected_pdf = st.selectbox(
        "Select PDF to parse",
        pdf_names,
        help="Choose a PDF from uploaded documents"
    )
    
    if not selected_pdf:
        return
    
    pdf_path = uploads_dir / selected_pdf
    
    # Parsing options
    col1, col2 = st.columns([3, 1])
    with col1:
        output_dir = st.text_input(
            "Output directory",
            value="/data/parsed_registers",
            help="Where to save parsed Excel file"
        )
    
    with col2:
        force_v2 = st.checkbox(
            "Force V2 Parser",
            value=False,
            help="Use V2 keyword-based parser"
        )
    
    # Parse button
    if st.button("🚀 Parse PDF", type="primary", use_container_width=True):
        parse_and_display(str(pdf_path), output_dir, force_v2)


def parse_and_display(pdf_path: str, output_dir: str, force_v2: bool = False):
    """
    Parse PDF and display results with clear status.
    """
    
    # Try to import orchestrator
    try:
        if force_v2:
            from utils.parsers.intelligent_parser_orchestrator_v2 import parse_pdf_intelligent_v2
            parse_func = parse_pdf_intelligent_v2
            parser_version = "V2"
        else:
            from utils.parsers.intelligent_parser_orchestrator import parse_pdf_intelligent
            parse_func = parse_pdf_intelligent
            parser_version = "V1"
    except ImportError as e:
        st.error(f"❌ Parser module not found: {str(e)}")
        st.info("""
        **To fix:**
        1. Deploy `intelligent_parser_orchestrator.py` to `utils/parsers/`
        2. Deploy `intelligent_parser_orchestrator_v2.py` to `utils/parsers/`
        3. Restart application
        """)
        return
    
    # Progress container
    with st.spinner(f"Parsing with {parser_version}..."):
        try:
            result = parse_func(pdf_path, output_dir)
        except Exception as e:
            st.error(f"❌ Parsing error: {str(e)}")
            logger.error(f"Parse error: {str(e)}", exc_info=True)
            return
    
    # Display result
    display_parsing_result(result, parser_version)


def display_parsing_result(result: Dict[str, Any], parser_version: str):
    """
    Display parsing result with clear status.
    """
    
    # Check if result exists
    if not result:
        st.error("❌ No result returned from parser")
        return
    
    # Determine status
    success = result.get('success', False)
    accuracy = result.get('accuracy', 0)
    
    # Status banner
    if success:
        if accuracy >= 90:
            status_color = "#28a745"
            status_emoji = "🎉"
            status_text = "SUCCESS - Excellent"
        elif accuracy >= 70:
            status_color = "#ffc107"
            status_emoji = "✅"
            status_text = "SUCCESS - Good"
        else:
            status_color = "#ff9800"
            status_emoji = "⚠️"
            status_text = "SUCCESS - Fair"
    else:
        status_color = "#dc3545"
        status_emoji = "❌"
        status_text = "FAILED"
    
    # Display status banner
    st.markdown(f"""
    <div style='background: {status_color}; padding: 1.5rem; border-radius: 8px; color: white; margin-bottom: 1rem;'>
        <div style='display: flex; align-items: center; justify-content: space-between;'>
            <div>
                <h3 style='margin: 0; color: white;'>{status_emoji} {status_text}</h3>
                <p style='margin: 0.5rem 0 0 0; opacity: 0.95;'>
                    Parser: {parser_version} | Accuracy: {accuracy:.0f}%
                </p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Show details
    if success:
        display_success_details(result)
    else:
        display_failure_details(result)


def display_success_details(result: Dict[str, Any]):
    """Display details for successful parse."""
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        accuracy = result.get('accuracy', 0)
        st.metric("Accuracy", f"{accuracy:.0f}%")
    
    with col2:
        stage = result.get('stage', 'Unknown')
        st.metric("Stage Used", stage)
    
    with col3:
        method = result.get('method', 'Unknown')
        st.metric("Method", method)
    
    with col4:
        employee_count = result.get('employee_count', 0)
        st.metric("Employees", employee_count)
    
    # Output file
    output_path = result.get('excel_path') or result.get('output_path') or result.get('output_file')
    
    if output_path and Path(output_path).exists():
        st.success(f"✅ Excel file created: `{Path(output_path).name}`")
        
        # Download button
        with open(output_path, 'rb') as f:
            st.download_button(
                label="📥 Download Excel",
                data=f.read(),
                file_name=Path(output_path).name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        # Preview data
        try:
            with st.expander("📊 Preview Parsed Data"):
                xl_file = pd.ExcelFile(output_path)
                
                for sheet_name in xl_file.sheet_names:
                    st.markdown(f"**{sheet_name}**")
                    df = pd.read_excel(output_path, sheet_name=sheet_name)
                    
                    if not df.empty:
                        st.dataframe(df.head(10), use_container_width=True)
                        st.caption(f"Showing 10 of {len(df)} rows")
                    else:
                        st.info("No data in this sheet")
                    
                    st.markdown("---")
        except Exception as e:
            st.warning(f"Could not preview data: {str(e)}")
    else:
        st.warning("⚠️ Excel file path not found in result")
    
    # Additional details
    with st.expander("🔍 Technical Details"):
        st.json(result)


def display_failure_details(result: Dict[str, Any]):
    """Display details for failed parse."""
    
    error = result.get('error') or result.get('message', 'Unknown error')
    st.error(f"**Error:** {error}")
    
    # Recommendations
    recommendations = result.get('recommendations', [])
    if recommendations:
        st.markdown("**Recommendations:**")
        for rec in recommendations:
            st.markdown(f"- {rec}")
    
    # Stages attempted
    attempts = result.get('attempts', [])
    if attempts:
        st.markdown("**Stages Attempted:**")
        for attempt in attempts:
            status = "✅" if attempt.get('success') else "❌"
            parser = attempt.get('parser', 'Unknown')
            strategy = attempt.get('strategy', 'Unknown')
            accuracy = attempt.get('accuracy', 0)
            st.caption(f"{status} {parser} ({strategy}) - {accuracy:.0f}% accuracy")
    
    # Full result for debugging
    with st.expander("🔍 Full Error Details"):
        st.json(result)


if __name__ == "__main__":
    render_intelligent_parser_ui()
