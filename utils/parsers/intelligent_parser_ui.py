"""
Enhanced Intelligent Parser UI
Shows parsing stages, accuracy, and save functionality
"""

import streamlit as st
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class IntelligentParserUI:
    """
    UI component for intelligent PDF parsing with stage visibility.
    """
    
    def __init__(self):
        self.uploads_dir = Path('/data/uploads')
        self.parsed_dir = Path('/data/parsed_registers')
        
        # Ensure directories exist
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.parsed_dir.mkdir(parents=True, exist_ok=True)
    
    def render(self):
        """
        Render the intelligent parser UI.
        """
        st.header("Intelligent PDF Parser")
        
        st.markdown("""
        **Multi-stage parsing system for complex payroll registers:**
        1. Custom parsers (saved from previous successes)
        2. Specialized parsers (Dayforce, ADP, etc.)
        3. Adaptive parsers (general purpose)
        4. Generated parsers (analyze and create new)
        """)
        
        # Get uploaded files
        uploaded_files = self._get_uploaded_files()
        
        if not uploaded_files:
            st.info("No PDF files uploaded yet. Upload files in the 'Document Upload' tab first.")
            return
        
        # File selection
        col1, col2 = st.columns([2, 1])
        
        with col1:
            selected_file = st.selectbox(
                "Select PDF to Parse",
                options=[f['name'] for f in uploaded_files],
                help="Choose a PDF file from your uploads"
            )
        
        with col2:
            document_type = st.selectbox(
                "Document Type (optional)",
                options=['Auto-detect', 'Dayforce', 'ADP', 'Paychex', 'Other'],
                help="Select document type for specialized parsing"
            )
        
        # Parse button
        if st.button("Parse Document", type="primary", use_container_width=True):
            self._run_parser(selected_file, document_type)
        
        # Show saved parsers
        st.markdown("---")
        self._show_saved_parsers()
    
    def _get_uploaded_files(self) -> list:
        """
        Get list of uploaded PDF files.
        """
        pdf_files = list(self.uploads_dir.glob('*.pdf'))
        
        return [
            {
                'name': f.name,
                'path': str(f),
                'size': f.stat().st_size,
                'modified': f.stat().st_mtime
            }
            for f in pdf_files
        ]
    
    def _run_parser(self, filename: str, document_type: str):
        """
        Run intelligent parser on selected file.
        """
        pdf_path = self.uploads_dir / filename
        
        if not pdf_path.exists():
            st.error(f"File not found: {filename}")
            return
        
        # Convert document type
        doc_type = None if document_type == 'Auto-detect' else document_type.lower()
        
        # Show progress container
        progress_container = st.container()
        
        with progress_container:
            st.info(f"Parsing: {filename}")
            
            # Stage indicators
            stage_cols = st.columns(4)
            stage_status = {}
            
            for i, col in enumerate(stage_cols, 1):
                with col:
                    stage_status[i] = st.empty()
                    stage_status[i].markdown(f"**Stage {i}**\n\nPending...")
            
            # Run parser
            try:
                from utils.parsers.intelligent_parser_orchestrator_enhanced import parse_pdf_intelligent
                
                result = parse_pdf_intelligent(str(pdf_path), doc_type)
                
                # Update stage indicators
                for stage_info in result.get('stages_attempted', []):
                    stage_num = stage_info['stage']
                    
                    if stage_info['success']:
                        emoji = "✅"
                        status = f"Success\n{stage_info.get('accuracy', 0)}%"
                        color = "green"
                    elif stage_info['attempted']:
                        emoji = "❌"
                        status = "Failed"
                        color = "red"
                    else:
                        emoji = "⏭️"
                        status = "Skipped"
                        color = "gray"
                    
                    stage_status[stage_num].markdown(
                        f"**Stage {stage_num}** {emoji}\n\n{status}"
                    )
                
                # Show results
                st.markdown("---")
                
                if result.get('status') == 'success':
                    self._show_success_result(result)
                else:
                    self._show_error_result(result)
                
            except Exception as e:
                st.error(f"Parser error: {str(e)}")
                logger.error(f"Parser error: {str(e)}", exc_info=True)
    
    def _show_success_result(self, result: Dict[str, Any]):
        """
        Display successful parse results.
        """
        st.success(f"Parsing completed successfully! (Stage {result['stage_used']})")
        
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Accuracy", f"{result.get('accuracy', 0)}%")
        
        with col2:
            st.metric("Employees", result.get('employee_count', 0))
        
        with col3:
            st.metric("Stage Used", result.get('stage_used', 'N/A'))
        
        with col4:
            tabs_info = result.get('tabs', {})
            total_rows = sum(tabs_info.values()) if tabs_info else 0
            st.metric("Total Rows", total_rows)
        
        # Download link
        if result.get('output_path'):
            output_path = Path(result['output_path'])
            
            if output_path.exists():
                st.markdown("---")
                
                with open(output_path, 'rb') as f:
                    st.download_button(
                        label="Download Excel File",
                        data=f,
                        file_name=output_path.name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
        
        # Save parser option
        if result.get('save_recommended'):
            st.markdown("---")
            st.info(f"High accuracy achieved! Reason: {result.get('save_reason', 'Unknown')}")
            
            with st.expander("Save Parser for Future Use"):
                parser_name = st.text_input(
                    "Parser Name",
                    value=f"custom_{Path(result['pdf_path']).stem}",
                    help="Name for saving this parser"
                )
                
                if st.button("Save Parser"):
                    self._save_parser(result, parser_name)
    
    def _show_error_result(self, result: Dict[str, Any]):
        """
        Display error results.
        """
        st.error("Parsing failed")
        
        st.markdown("**Stages Attempted:**")
        for stage_info in result.get('stages_attempted', []):
            st.write(f"- Stage {stage_info['stage']} ({stage_info['name']}): {'Success' if stage_info['success'] else 'Failed'}")
        
        if result.get('errors'):
            st.markdown("**Errors:**")
            for error in result['errors']:
                st.write(f"- {error}")
        
        st.info("Try selecting a different document type or uploading a clearer PDF.")
    
    def _save_parser(self, result: Dict[str, Any], parser_name: str):
        """
        Save a successful parser.
        """
        try:
            from utils.parsers.intelligent_parser_orchestrator_enhanced import IntelligentParserOrchestrator
            
            orchestrator = IntelligentParserOrchestrator()
            
            # Get parser code
            parser_code = result.get('parser_code')
            
            if not parser_code:
                st.error("No parser code available to save")
                return
            
            # Save with metadata
            metadata = {
                'accuracy': result.get('accuracy'),
                'stage': result.get('stage_used'),
                'employee_count': result.get('employee_count'),
                'source_pdf': Path(result['pdf_path']).name
            }
            
            success = orchestrator.save_parser(parser_name, parser_code, metadata)
            
            if success:
                st.success(f"Parser saved as: {parser_name}")
                st.balloons()
            else:
                st.error("Failed to save parser")
                
        except Exception as e:
            st.error(f"Save error: {str(e)}")
            logger.error(f"Save error: {str(e)}", exc_info=True)
    
    def _show_saved_parsers(self):
        """
        Display list of saved custom parsers.
        """
        st.subheader("Saved Custom Parsers")
        
        try:
            from utils.parsers.intelligent_parser_orchestrator_enhanced import IntelligentParserOrchestrator
            
            orchestrator = IntelligentParserOrchestrator()
            parsers = orchestrator.list_custom_parsers()
            
            if not parsers:
                st.info("No custom parsers saved yet. Parse documents successfully to save parsers.")
                return
            
            for parser in parsers:
                with st.expander(f"{parser['name']}"):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**Modified:** {parser['modified'].strftime('%Y-%m-%d %H:%M')}")
                        st.write(f"**Size:** {parser['size']:,} bytes")
                    
                    with col2:
                        if st.button("Delete", key=f"delete_{parser['name']}"):
                            if orchestrator.delete_parser(parser['name']):
                                st.success(f"Deleted: {parser['name']}")
                                st.rerun()
                            else:
                                st.error("Delete failed")
        
        except Exception as e:
            st.error(f"Error loading parsers: {str(e)}")
            logger.error(f"Error loading parsers: {str(e)}", exc_info=True)


def render_intelligent_parser_ui():
    """
    Convenience function to render the UI.
    """
    ui = IntelligentParserUI()
    ui.render()
