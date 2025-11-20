"""
Intelligent Parser UI - FIXED with correct class interface
"""

import streamlit as st
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class IntelligentParserUI:
    """Class-based UI for intelligent parser."""
    
    def __init__(self):
        self.upload_dir = "/data/uploads"
        self.output_dir = "/data/parsed_registers"
    
    def render(self):
        """Render the parser UI."""
        
        st.markdown("### 📄 Intelligent PDF Parser")
        st.markdown("Automatically detects structure and extracts payroll data")
        
        # Check for PDFs
        if not os.path.exists(self.upload_dir):
            st.warning("📁 Upload directory not found. Upload documents in the Upload tab first.")
            return
        
        pdf_files = [f for f in os.listdir(self.upload_dir) if f.lower().endswith('.pdf')]
        
        if not pdf_files:
            st.info("📁 No PDFs uploaded yet. Upload documents in the Upload tab first.")
            return

        use_v3 = st.checkbox(
            "🌟 Use V3 Parser (Universal Multi-Vendor)",
            value=False,
            help="V3: Auto-detects vendor, tries multiple strategies until 90%+ accuracy"
        )

        # V2 CHECKBOX (ACTUALLY WORKS NOW)
        use_v2 = st.checkbox(
            "✨ Use V2 Parser (Table-Based Extraction)",
            value=False,
            help="V2: Table extraction (better for Dayforce). V1: Text extraction (faster)."
        )
        
        # File selection
        st.markdown("#### Select PDF to Parse")
        selected_pdf = st.selectbox(
            "Choose PDF:",
            options=pdf_files,
            format_func=lambda x: f"📄 {x}"
        )
        
        # Parse button
        if st.button("🚀 Parse Document", type="primary", use_container_width=True):
            if not selected_pdf:
                st.error("Please select a PDF file")
                return
            
            pdf_path = os.path.join(self.upload_dir, selected_pdf)
            
            with st.spinner(f"Parsing {selected_pdf}..."):
                try:
                    # CRITICAL FIX: Actually import and use the selected version
                    if use_v3:
                        from .intelligent_parser_orchestrator_v3 import IntelligentParserOrchestratorV3
                        orchestrator = IntelligentParserOrchestratorV3()
                        parser_version = "V3"
                    elif use_v2:
                        from .intelligent_parser_orchestrator_v2 import IntelligentParserOrchestratorV2
                        orchestrator = IntelligentParserOrchestratorV2()
                        parser_version = "V2"
                    else:
                        from .intelligent_parser_orchestrator import IntelligentParserOrchestrator
                        orchestrator = IntelligentParserOrchestrator()
                        parser_version = "V1"
                     
                    # Parse
                    result = orchestrator.parse(pdf_path, self.output_dir)
                    
                    # Display results
                    if result.get('success'):
                        accuracy = result.get('accuracy', 0)
                        
                        # Color-coded success banner
                        if accuracy >= 90:
                            st.success(f"✅ SUCCESS - Excellent")
                        elif accuracy >= 70:
                            st.success(f"✅ SUCCESS - Good")
                        else:
                            st.warning(f"⚠️ SUCCESS - Fair")
                        
                        # Show parser info
                        st.markdown(f"**Parser:** {parser_version} | **Accuracy:** {accuracy}%")
                        
                        # Metrics
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.metric("Accuracy", f"{accuracy}%")
                        
                        with col2:
                            method = result.get('method', 'Unknown')
                            st.metric("Method", method)
                        
                        with col3:
                            employees = result.get('employees_found', 0)
                            st.metric("Employees", employees)
                        
                        with col4:
                            stage = result.get('stage_used', 'Unknown')
                            st.metric("Stage Used", stage)
                        
                        # Download button
                        excel_path = result.get('excel_path')
                        if excel_path and os.path.exists(excel_path):
                            st.success(f"✅ Excel file created: {os.path.basename(excel_path)}")
                            
                            with open(excel_path, 'rb') as f:
                                st.download_button(
                                    label="📥 Download Excel",
                                    data=f.read(),
                                    file_name=os.path.basename(excel_path),
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    use_container_width=True
                                )
                            
                            # Preview data
                            with st.expander("📊 Preview Parsed Data"):
                                import pandas as pd
                                xl = pd.ExcelFile(excel_path)
                                
                                for sheet in xl.sheet_names:
                                    df = pd.read_excel(excel_path, sheet_name=sheet)
                                    st.markdown(f"**{sheet}** ({len(df)} rows)")
                                    st.dataframe(df.head(10), use_container_width=True)
                        
                        # Technical details
                        with st.expander("🔍 Technical Details"):
                            st.json(result)
                    
                    else:
                        error_msg = result.get('error', 'Unknown error')
                        st.error(f"❌ FAILED: {error_msg}")
                        
                        with st.expander("🔍 Error Details"):
                            st.json(result)
                
                except Exception as e:
                    st.error(f"❌ Error during parsing: {str(e)}")
                    logger.error(f"Parser error: {e}", exc_info=True)


# Backward compatibility functions
def render_intelligent_parser_ui():
    """Function wrapper for class-based UI."""
    ui = IntelligentParserUI()
    ui.render()


def render_intelligent_parser(orchestrator=None):
    """Legacy function name."""
    render_intelligent_parser_ui()
