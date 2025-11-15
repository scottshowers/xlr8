"""
Analysis & Templates Page - Main Work Feature
Orchestrates: Upload → Parse → Analyze → Generate Templates

Owner: Analysis Team Lead
Dependencies: All analysis submodules
"""

import streamlit as st
from pages.work.analysis.upload import render_upload_section
from pages.work.analysis.parser import parse_document
from pages.work.analysis.ai_analyzer import analyze_document
from pages.work.analysis.template_filler import generate_templates
from pages.work.analysis.results_viewer import display_results


def render_analysis_page():
    """
    Main analysis page - orchestrates the analysis workflow
    """
    
    st.markdown("## 📊 Document Analysis & Template Generation")
    
    st.markdown("""
    <div class='info-box'>
        <strong>Workflow:</strong> Upload customer document → AI analyzes against HCMPACT standards → 
        Generate UKG-ready templates (pay codes, deductions, org structure)
    </div>
    """, unsafe_allow_html=True)
    
    # Check for active project
    if not st.session_state.current_project:
        st.warning("⚠️ No active project selected. Please select or create a project in Setup → Projects")
        return
    
    st.success(f"📁 Active Project: {st.session_state.current_project}")
    
    st.markdown("---")
    
    # STEP 1: Upload
    st.markdown("### Step 1: Upload Document")
    uploaded_file = render_upload_section()
    
    if not uploaded_file:
        st.info("👆 Upload a customer document to begin analysis")
        return
    
    st.markdown("---")
    
    # STEP 2: Parse (automatic)
    st.markdown("### Step 2: Extract Content")
    
    with st.spinner("📄 Extracting text from document..."):
        parsed_data = parse_document(uploaded_file)
    
    if not parsed_data:
        st.error("Failed to parse document. Please try another file.")
        return
    
    st.success(f"✅ Extracted {len(parsed_data.get('text', ''))} characters")
    
    # Show preview
    with st.expander("👁️ View Extracted Content"):
        st.text_area(
            "Content Preview",
            parsed_data.get('text', '')[:1000] + "...",
            height=200
        )
    
    st.markdown("---")
    
    # STEP 3: AI Analysis
    st.markdown("### Step 3: AI Analysis")
    
    analysis_col1, analysis_col2 = st.columns([3, 1])
    
    with analysis_col1:
        analysis_depth = st.selectbox(
            "Analysis Depth",
            ["Quick Overview", "Standard Analysis", "Deep Analysis"],
            index=1
        )
    
    with analysis_col2:
        if st.button("🤖 Analyze", type="primary", use_container_width=True):
            with st.spinner("🧠 AI is analyzing your document against HCMPACT standards..."):
                analysis_results = analyze_document(
                    parsed_data=parsed_data,
                    depth=analysis_depth
                )
            
            if analysis_results:
                st.session_state.current_analysis = analysis_results
                st.success("✅ Analysis complete!")
                st.rerun()
    
    # Show existing analysis if available
    if st.session_state.get('current_analysis'):
        st.markdown("---")
        
        # STEP 4: Generate Templates
        st.markdown("### Step 4: Generate UKG Templates")
        
        if st.button("📋 Generate Templates", type="primary", use_container_width=True):
            with st.spinner("📝 Generating UKG-ready templates..."):
                templates = generate_templates(st.session_state.current_analysis)
            
            if templates:
                st.session_state.current_templates = templates
                st.success("✅ Templates generated!")
                st.rerun()
        
        st.markdown("---")
        
        # STEP 5: Display Results
        st.markdown("### Results")
        display_results(
            analysis=st.session_state.get('current_analysis'),
            templates=st.session_state.get('current_templates')
        )
