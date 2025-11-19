"""
Intelligent Parser UI Component for XLR8
Streamlit interface for intelligent PDF parsing with accuracy display
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class IntelligentParserUI:
    """Streamlit UI component for intelligent PDF parsing"""
    
    def __init__(self, orchestrator):
        """
        Initialize UI component
        
        Args:
            orchestrator: IntelligentParserOrchestrator instance
        """
        self.orchestrator = orchestrator
        
    def render(self):
        """Render the intelligent parser interface"""
        st.header("Intelligent PDF Parser")
        st.markdown("""
        Upload a PDF register and the intelligent parser will automatically:
        1. Try custom parsers saved from previous successful parses
        2. Try adaptive parsers optimized for register documents
        3. Generate and test a new custom parser if needed
        
        The system reports parsing accuracy (0-100%) based on data quality.
        """)
        
        # File upload
        uploaded_file = st.file_uploader(
            "Upload PDF Register",
            type=['pdf'],
            help="Upload a payroll or employee register PDF"
        )
        
        # Parsing options
        col1, col2 = st.columns(2)
        with col1:
            auto_save = st.checkbox(
                "Auto-save successful parsers",
                value=True,
                help="Automatically save parsers with accuracy >= 70%"
            )
        with col2:
            min_accuracy = st.slider(
                "Minimum accuracy to save (%)",
                min_value=50,
                max_value=100,
                value=70,
                help="Only save parsers meeting this accuracy threshold"
            )
        
        # Parse button
        if uploaded_file is not None:
            if st.button("Parse PDF", type="primary"):
                self._handle_parsing(uploaded_file, auto_save, min_accuracy)
        
        # Display saved parsers
        self._display_saved_parsers()
    
    def _handle_parsing(self, uploaded_file, auto_save: bool, min_accuracy: int):
        """Handle PDF parsing workflow"""
        try:
            # Save uploaded file
            upload_dir = Path("/data/uploads")
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            pdf_path = upload_dir / uploaded_file.name
            with open(pdf_path, 'wb') as f:
                f.write(uploaded_file.getbuffer())
            
            st.info(f"Processing: {uploaded_file.name}")
            
            # Create progress indicators
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Stage 1: Custom parsers
            status_text.text("Stage 1: Trying custom parsers...")
            progress_bar.progress(10)
            
            result = self.orchestrator.parse_with_intelligence(
                str(pdf_path),
                auto_save=auto_save,
                min_accuracy_to_save=min_accuracy
            )
            
            progress_bar.progress(100)
            status_text.empty()
            
            # Display results
            self._display_parsing_results(result, uploaded_file.name)
            
        except Exception as e:
            st.error(f"Parsing failed: {str(e)}")
            logger.error(f"Parsing error: {str(e)}", exc_info=True)
    
    def _display_parsing_results(self, result: dict, filename: str):
        """Display parsing results with accuracy metrics"""
        
        if not result.get('success'):
            st.error("Parsing failed")
            if 'error' in result:
                st.error(f"Error: {result['error']}")
            return
        
        # Success header with accuracy
        accuracy = result.get('accuracy', 0)
        stage = result.get('stage_used', 'unknown')
        
        # Color-coded accuracy display
        if accuracy >= 80:
            accuracy_color = "green"
            accuracy_label = "Excellent"
        elif accuracy >= 70:
            accuracy_color = "blue"
            accuracy_label = "Good"
        elif accuracy >= 50:
            accuracy_color = "orange"
            accuracy_label = "Fair"
        else:
            accuracy_color = "red"
            accuracy_label = "Poor"
        
        st.success(f"Parsing completed using: {stage}")
        
        # Accuracy metrics card
        st.markdown(f"""
        <div style="padding: 20px; border-radius: 10px; background-color: #f0f2f6; margin: 10px 0;">
            <h3 style="margin: 0; color: #1f1f1f;">Parsing Accuracy</h3>
            <div style="display: flex; align-items: center; margin-top: 10px;">
                <div style="font-size: 48px; font-weight: bold; color: {accuracy_color}; margin-right: 20px;">
                    {accuracy}%
                </div>
                <div>
                    <div style="font-size: 20px; color: {accuracy_color}; font-weight: bold;">
                        {accuracy_label}
                    </div>
                    <div style="font-size: 14px; color: #666;">
                        Parser: {stage}
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Accuracy breakdown
        if 'accuracy_breakdown' in result:
            breakdown = result['accuracy_breakdown']
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Basic Success", f"{breakdown.get('basic_success', 0)}%")
            with col2:
                st.metric("Table Quality", f"{breakdown.get('table_quality', 0)}%")
            with col3:
                st.metric("Text Extraction", f"{breakdown.get('text_extraction', 0)}%")
            with col4:
                st.metric("Data Quality", f"{breakdown.get('data_quality', 0)}%")
        
        # Parser details
        with st.expander("Parser Details"):
            st.write(f"**Stage Used:** {stage}")
            if 'parser_name' in result:
                st.write(f"**Parser Name:** {result['parser_name']}")
            if 'execution_time' in result:
                st.write(f"**Execution Time:** {result['execution_time']:.2f}s")
            if 'was_saved' in result and result['was_saved']:
                st.success("Parser saved for future use")
        
        # Display parsed data
        if 'output_file' in result and Path(result['output_file']).exists():
            st.subheader("Parsed Data Preview")
            
            try:
                df = pd.read_excel(result['output_file'])
                
                # Show summary stats
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Rows", len(df))
                with col2:
                    st.metric("Total Columns", len(df.columns))
                with col3:
                    non_empty = df.count().sum()
                    total_cells = len(df) * len(df.columns)
                    fill_rate = (non_empty / total_cells * 100) if total_cells > 0 else 0
                    st.metric("Fill Rate", f"{fill_rate:.1f}%")
                
                # Show data preview
                st.dataframe(df.head(20), use_container_width=True)
                
                # Download button
                with open(result['output_file'], 'rb') as f:
                    st.download_button(
                        label="Download Parsed Excel",
                        data=f.read(),
                        file_name=Path(result['output_file']).name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    
            except Exception as e:
                st.error(f"Could not preview data: {str(e)}")
        
        # Show any warnings or issues
        if 'warnings' in result and result['warnings']:
            with st.expander("Warnings"):
                for warning in result['warnings']:
                    st.warning(warning)
    
    def _display_saved_parsers(self):
        """Display list of saved custom parsers"""
        st.subheader("Saved Custom Parsers")
        
        parsers_dir = Path("/data/custom_parsers")
        if not parsers_dir.exists():
            st.info("No custom parsers saved yet")
            return
        
        parser_files = list(parsers_dir.glob("*.py"))
        if not parser_files:
            st.info("No custom parsers saved yet")
            return
        
        # Create a table of saved parsers
        parser_data = []
        for parser_file in sorted(parser_files, key=lambda x: x.stat().st_mtime, reverse=True):
            stat = parser_file.stat()
            parser_data.append({
                'Name': parser_file.stem,
                'Created': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M'),
                'Size': f"{stat.st_size / 1024:.1f} KB"
            })
        
        if parser_data:
            df = pd.DataFrame(parser_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            st.caption(f"Total custom parsers: {len(parser_data)}")
        
        # Parser management
        with st.expander("Manage Parsers"):
            selected_parser = st.selectbox(
                "Select parser",
                options=[p['Name'] for p in parser_data] if parser_data else []
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("View Code"):
                    if selected_parser:
                        parser_path = parsers_dir / f"{selected_parser}.py"
                        if parser_path.exists():
                            with open(parser_path, 'r') as f:
                                code = f.read()
                            st.code(code, language='python')
            
            with col2:
                if st.button("Delete Parser", type="secondary"):
                    if selected_parser:
                        parser_path = parsers_dir / f"{selected_parser}.py"
                        if parser_path.exists():
                            parser_path.unlink()
                            st.success(f"Deleted {selected_parser}")
                            st.rerun()


def render_intelligent_parser(orchestrator):
    """
    Convenience function to render intelligent parser UI
    
    Args:
        orchestrator: IntelligentParserOrchestrator instance
    """
    ui = IntelligentParserUI(orchestrator)
    ui.render()
