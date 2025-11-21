"""
Intelligent Parser UI - WITH V4 ADAPTIVE LEARNING
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
        
        # Parser version selection (at top)
        st.markdown("#### Parser Version")
        
        # NEW: V4 Adaptive option
        use_v4 = st.checkbox(
            "🧠 Use V4 Adaptive Learning (RECOMMENDED - Self-Healing)",
            value=True,  # Default to V4!
            help="V4: Iterative learning system - tries up to 10 times, adapts strategies until 90%+ accuracy. Best for unknown/difficult formats."
        )
        
        use_v3 = st.checkbox(
            "🌟 Use V3 Parser (Universal Multi-Vendor)",
            value=False,
            help="V3: Auto-detects vendor, tries multiple strategies (3-5 attempts max)"
        )

        use_v2 = st.checkbox(
            "✨ Use V2 Parser (Table-Based Extraction)",
            value=False,
            help="V2: Table extraction (better for Dayforce). V1: Text extraction (faster)."
        )
        
        st.markdown("---")
        
        # TWO OPTIONS: Upload new OR select existing
        upload_option = st.radio(
            "Choose PDF source:",
            ["📤 Upload New PDF", "📁 Select from Existing Files"],
            horizontal=True
        )
        
        pdf_path = None
        selected_pdf_name = None
        
        if upload_option == "📤 Upload New PDF":
            # Direct file upload
            uploaded_file = st.file_uploader(
                "Upload PDF File",
                type=['pdf'],
                help="Upload a PDF directly for parsing (no Knowledge Base chunking)"
            )
            
            if uploaded_file:
                # Save to temporary location
                try:
                    os.makedirs(self.upload_dir, exist_ok=True)
                    temp_path = os.path.join(self.upload_dir, uploaded_file.name)
                    
                    with open(temp_path, 'wb') as f:
                        f.write(uploaded_file.getvalue())
                    
                    pdf_path = temp_path
                    selected_pdf_name = uploaded_file.name
                    st.success(f"✅ Uploaded: {uploaded_file.name}")
                    
                except Exception as e:
                    st.error(f"❌ Error saving file: {str(e)}")
                    logger.error(f"Upload error: {str(e)}", exc_info=True)
                    return
        
        else:
            # Select from existing files
            if not os.path.exists(self.upload_dir):
                st.warning("📁 Upload directory not found. Upload a file first using the option above.")
                return
            
            pdf_files = [f for f in os.listdir(self.upload_dir) if f.lower().endswith('.pdf')]
            
            if not pdf_files:
                st.info("📁 No PDFs found. Upload a file using the option above.")
                return
            
            selected_pdf = st.selectbox(
                "Choose PDF:",
                options=pdf_files,
                format_func=lambda x: f"📄 {x}"
            )
            
            if selected_pdf:
                pdf_path = os.path.join(self.upload_dir, selected_pdf)
                selected_pdf_name = selected_pdf
        
        # Parse button (only show if file is selected)
        if pdf_path:
            st.markdown("---")
            if st.button("🚀 Parse Document", type="primary", use_container_width=True):
                
                with st.spinner(f"Parsing {selected_pdf_name}..."):
                    try:
                        # Select parser based on checkboxes
                        if use_v4:
                            from .adaptive_orchestrator import AdaptiveParserOrchestrator
                            orchestrator = AdaptiveParserOrchestrator()
                            parser_version = "V4 Adaptive"
                            st.info("🧠 Using Adaptive Learning - May take 2-5 minutes for difficult formats")
                        elif use_v3:
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
                            
                            # Metrics - Enhanced for V4
                            if use_v4:
                                col1, col2, col3, col4, col5 = st.columns(5)
                                
                                with col1:
                                    st.metric("Accuracy", f"{accuracy}%")
                                
                                with col2:
                                    iterations = result.get('iterations', 1)
                                    st.metric("Iterations", iterations)
                                
                                with col3:
                                    employees = result.get('employees_found', 0)
                                    st.metric("Employees", employees)
                                
                                with col4:
                                    target = "✅" if result.get('target_achieved', False) else "⚠️"
                                    st.metric("Target (90%)", target)
                                
                                with col5:
                                    method = result.get('method', 'Unknown')
                                    st.metric("Best Method", method.replace('adaptive_', ''))
                                
                                # Show learning path for V4
                                if result.get('learning_path'):
                                    with st.expander("🎓 Learning Path - How It Figured It Out"):
                                        for step in result['learning_path']:
                                            iter_num = step.get('iteration', 0)
                                            score = step.get('score', 0)
                                            diagnosis = step.get('diagnosis', {})
                                            
                                            st.markdown(f"**Iteration {iter_num}:** {score}%")
                                            
                                            # Show what was found wrong
                                            root_causes = diagnosis.get('root_causes', [])
                                            if root_causes:
                                                st.caption("Issues found:")
                                                for cause in root_causes:
                                                    st.caption(f"  • {cause.replace('_', ' ').title()}")
                                            
                                            # Show what mutations were applied
                                            mutations = diagnosis.get('mutations', [])
                                            if mutations:
                                                st.caption("Adaptations applied:")
                                                for mutation in mutations:
                                                    priority = mutation.get('priority', 'medium')
                                                    m_type = mutation.get('type', 'unknown')
                                                    st.caption(f"  • [{priority.upper()}] {m_type.replace('_', ' ').title()}")
                                            
                                            st.markdown("---")
                            else:
                                # Standard metrics for V1-V3
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
                            
                            # Show learning path even on failure for V4
                            if use_v4 and result.get('learning_path'):
                                st.warning(f"Attempted {len(result['learning_path'])} iterations")
                                with st.expander("🔍 What Went Wrong"):
                                    for step in result['learning_path']:
                                        st.write(f"Iteration {step.get('iteration')}: {step.get('score', 0)}%")
                            
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
