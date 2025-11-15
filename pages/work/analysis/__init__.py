"""
Analysis & Templates Page - Main Work Feature
Orchestrates: Upload → Parse → Analyze → Generate Templates
NOW WIRED TO ACTUAL WORKING CODE
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
    NOW USES ACTUAL WORKING IMPLEMENTATIONS
    """
    
    st.markdown("## 📊 Document Analysis & Template Generation")
    
    st.markdown("""
    <div class='info-box'>
        <strong>Workflow:</strong> Upload customer document → AI analyzes against HCMPACT standards → 
        Generate UKG-ready templates (pay codes, deductions, org structure)
    </div>
    """, unsafe_allow_html=True)
    
    # Check for active project
    if st.session_state.current_project:
        st.success(f"📁 Active Project: {st.session_state.current_project}")
    else:
        st.info("💡 No project selected - analyzing in standalone mode")
    
    st.markdown("---")
    
    # STEP 1: Upload
    st.markdown("### Step 1: Upload Document")
    uploaded_file = render_upload_section()
    
    if not uploaded_file:
        st.info("👆 Upload a customer document to begin analysis")
        return
    
    st.markdown("---")
    
    # STEP 2: Parse (automatic) - NOW USES ACTUAL PARSER
    st.markdown("### Step 2: Extract Content")
    
    with st.spinner("📄 Extracting text from document using EnhancedPayrollParser..."):
        parsed_data = parse_document(uploaded_file)
    
    if not parsed_data:
        st.error("Failed to parse document. Please try another file.")
        return
    
    # CRITICAL: Store parsed results in session state for template generation
    st.session_state.parsed_results = parsed_data.get('raw_result', parsed_data)
    
    st.success(f"✅ Extracted {len(parsed_data.get('text', ''))} characters")
    
    # Show parsing details
    if parsed_data.get('metadata'):
        meta = parsed_data['metadata']
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Parsing Method", meta.get('method', 'N/A'))
        with col2:
            if 'total_pages' in meta:
                st.metric("Pages", meta['total_pages'])
        with col3:
            if 'processing_time' in meta:
                st.metric("Processing Time", f"{meta['processing_time']:.2f}s")
    
    # Show tables found
    if parsed_data.get('tables'):
        st.info(f"📊 Found {len(parsed_data['tables'])} table(s) in document")
    
    # Show preview
    with st.expander("👁️ View Extracted Content"):
        st.text_area(
            "Content Preview",
            parsed_data.get('text', '')[:1000] + "...",
            height=200
        )
    
    st.markdown("---")
    
    # STEP 3: AI Analysis - NOW USES ACTUAL LLM
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
            with st.spinner("🧠 AI is analyzing your document with Ollama + RAG..."):
                analysis_results = analyze_document(
                    parsed_data=parsed_data,
                    depth=analysis_depth
                )
            
            if analysis_results and analysis_results.get('success'):
                st.session_state.current_analysis = analysis_results
                st.success("✅ Analysis complete!")
                st.rerun()
            else:
                st.error("❌ Analysis failed: " + analysis_results.get('message', 'Unknown error'))
    
    # Show existing analysis if available
    if st.session_state.get('current_analysis'):
        st.markdown("---")
        
        # Display analysis results immediately
        st.markdown("### 📊 Analysis Results")
        analysis = st.session_state.current_analysis
        
        if analysis.get('analysis'):
            with st.expander("📄 Full Analysis", expanded=False):
                st.markdown(analysis['analysis'])
        
        if analysis.get('findings'):
            st.markdown("#### 🔍 Key Findings")
            for i, finding in enumerate(analysis['findings'], 1):
                st.markdown(f"{i}. {finding}")
        
        st.markdown("---")
        
        # STEP 4: Generate Templates - NOW USES ACTUAL UKG EXPORT
        st.markdown("### Step 4: Generate UKG Templates")
        
        if st.button("📋 Generate Templates", type="primary", use_container_width=True):
            with st.spinner("📝 Generating UKG-ready templates with process_parsed_pdf_for_ukg..."):
                templates = generate_templates(st.session_state.current_analysis)
            
            if templates:
                st.session_state.current_templates = templates
                st.success(f"✅ Generated {len(templates)} template(s)!")
                st.rerun()
            else:
                st.warning("No templates generated. Make sure document was successfully parsed.")
        
        st.markdown("---")
        
        # STEP 5: Display Results
        st.markdown("### 📥 Results & Downloads")
        display_results(
            analysis=st.session_state.get('current_analysis'),
            templates=st.session_state.get('current_templates')
        )
