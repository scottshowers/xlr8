"""
Analysis & Templates Page - 🎸 CRANKED TO 11! 🎸
Beautiful cards, enhanced visuals, professional polish
Version: 11/10 - "This one goes to 11!"
"""

import streamlit as st
from pages.work.analysis.upload import render_upload_section
from pages.work.analysis.parser import parse_document
from pages.work.analysis.ai_analyzer import analyze_document
from pages.work.analysis.template_filler import generate_templates
from pages.work.analysis.results_viewer import display_results
import time


def render_analysis_page():
    """
    Main analysis page with PROFESSIONAL POLISH
    """
    
    st.markdown("## 📊 Document Analysis & Template Generation")
    
    st.markdown("""
    <div style='background: linear-gradient(135deg, #f5f7f9 0%, #e8eef3 100%); padding: 1.25rem; border-radius: 12px; border-left: 4px solid #667eea; margin-bottom: 1.5rem; box-shadow: 0 2px 8px rgba(0,0,0,0.05);'>
        <div style='display: flex; align-items: center; gap: 0.75rem;'>
            <div style='font-size: 1.5rem;'>🚀</div>
            <div>
                <strong style='color: #6d8aa0; font-size: 1.05rem;'>AI-Powered Workflow</strong><br>
                <span style='color: #7d96a8; font-size: 0.9rem;'>Upload customer document → AI analyzes against HCMPACT standards → Generate UKG-ready templates (pay codes, deductions, org structure)</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Check for active project - AMPLIFIED! 🎸
    if st.session_state.get('current_project'):
        project_name = st.session_state.current_project
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #e8f5e9 0%, #f1f8f4 100%); padding: 1rem; border-radius: 10px; border: 2px solid #28a745; margin-bottom: 1rem; box-shadow: 0 2px 8px rgba(40, 167, 69, 0.1);'>
            <div style='display: flex; align-items: center; gap: 0.5rem;'>
                <span style='font-size: 1.2rem;'>📁</span>
                <div>
                    <strong style='color: #28a745;'>Active Project:</strong>
                    <span style='color: #155724; margin-left: 0.5rem; font-weight: 600;'>{project_name}</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style='background: linear-gradient(135deg, #fff3cd 0%, #fffef0 100%); padding: 1rem; border-radius: 10px; border: 2px solid #ffc107; margin-bottom: 1rem;'>
            <div style='display: flex; align-items: center; gap: 0.5rem;'>
                <span style='font-size: 1.2rem;'>💡</span>
                <span style='color: #856404; font-weight: 600;'>No project selected - analyzing in standalone mode</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ==== STEP 1: Upload (with empty state) ====
    st.markdown("### Step 1: Upload Document")
    uploaded_file = render_upload_section()
    
    # EMPTY STATE ✨
    if not uploaded_file:
        st.markdown("""
        <div style='text-align: center; padding: 3rem 1rem; background: #f8f9fa; border-radius: 12px; border: 2px dashed #dee2e6;'>
            <div style='font-size: 3rem; margin-bottom: 1rem;'>📄</div>
            <h3 style='color: #6c757d; margin-bottom: 0.5rem;'>No Document Uploaded</h3>
            <p style='color: #6c757d; margin-bottom: 1.5rem;'>Upload a customer document to begin analysis</p>
            <div style='font-size: 0.9rem; color: #6c757d;'>
                <strong>Supported formats:</strong> PDF, Excel, Word, CSV<br>
                <strong>Max size:</strong> 200MB
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Show example of what can be uploaded
        with st.expander("💡 What documents can I analyze?"):
            st.markdown("""
            **Common documents for UKG implementation:**
            - Pay registers and earnings statements
            - Time and attendance reports
            - Employee master data files
            - Organizational charts
            - Benefits enrollment data
            - Payroll deduction reports
            - Custom pay code configurations
            
            **The AI will:**
            1. Extract data from your document
            2. Analyze against UKG best practices
            3. Identify gaps and recommendations
            4. Generate UKG-ready configuration templates
            """)
        
        return
    
    st.markdown("---")
    
    # ==== STEP 2: Parse (with professional loading state) ====
    st.markdown("### Step 2: Extract Content")
    
    # LOADING STATE with progress ✨
    with st.spinner(""):  # Empty spinner, we'll use custom messages
        progress_placeholder = st.empty()
        
        # Show multi-step progress
        progress_placeholder.info("📄 Reading document...")
        time.sleep(0.2)  # Brief pause for visual feedback
        
        progress_placeholder.info("🔍 Detecting tables and structure...")
        time.sleep(0.2)
        
        progress_placeholder.info("✨ Extracting text and data...")
        parsed_data = parse_document(uploaded_file)
        
        progress_placeholder.empty()
    
    if not parsed_data:
        st.error("❌ Failed to parse document. Please try another file.")
        
        # HELPFUL ERROR STATE ✨
        with st.expander("😕 What went wrong?"):
            st.markdown("""
            **Possible issues:**
            - File might be corrupted
            - Format not fully supported
            - Document is password protected
            - File contains only images (no text)
            
            **Try this:**
            1. Check if file opens normally outside the app
            2. Try saving as a different format
            3. Make sure file isn't password protected
            4. Contact support if problem persists
            """)
        return
    
    # Store parsed results
    st.session_state.parsed_results = parsed_data.get('raw_result', parsed_data)
    
    # SUCCESS STATE ✨
    st.success(f"✅ Successfully extracted {len(parsed_data.get('text', '')):,} characters")
    
    # Show parsing details in clean metrics
    if parsed_data.get('metadata'):
        meta = parsed_data['metadata']
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📋 Method", meta.get('method', 'N/A'))
        with col2:
            if 'total_pages' in meta:
                st.metric("📄 Pages", meta['total_pages'])
        with col3:
            if 'processing_time' in meta:
                st.metric("⏱️ Time", f"{meta['processing_time']:.1f}s")
        with col4:
            if parsed_data.get('tables'):
                st.metric("📊 Tables", len(parsed_data['tables']))
    
    # Show preview with better UX
    with st.expander("👁️ View Extracted Content", expanded=False):
        preview_text = parsed_data.get('text', '')
        if len(preview_text) > 1000:
            st.text_area(
                "Content Preview (first 1000 characters)",
                preview_text[:1000] + "\n\n... (truncated)",
                height=200,
                disabled=True
            )
            st.caption(f"Total length: {len(preview_text):,} characters")
        else:
            st.text_area(
                "Full Content",
                preview_text,
                height=200,
                disabled=True
            )
    
    st.markdown("---")
    
    # ==== STEP 3: AI Analysis (with professional loading) ====
    st.markdown("### Step 3: AI Analysis")
    
    analysis_col1, analysis_col2 = st.columns([3, 1])
    
    with analysis_col1:
        analysis_depth = st.selectbox(
            "Analysis Depth",
            ["Quick Overview", "Standard Analysis", "Deep Analysis"],
            index=1,
            help="Choose analysis depth - deeper analysis takes longer but provides more insights"
        )
    
    with analysis_col2:
        if st.button("🤖 Analyze", type="primary", use_container_width=True):
            # PROFESSIONAL LOADING STATE with steps ✨
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Step 1: RAG Search
            status_text.info("🔍 Step 1/3: Searching knowledge base for relevant standards...")
            progress_bar.progress(10)
            time.sleep(0.5)
            
            # Step 2: Analysis
            status_text.info("🧠 Step 2/3: AI analyzing document against best practices...")
            progress_bar.progress(30)
            
            analysis_results = analyze_document(
                parsed_data=parsed_data,
                depth=analysis_depth
            )
            
            progress_bar.progress(70)
            
            # Step 3: Formatting
            status_text.info("✨ Step 3/3: Formatting results...")
            progress_bar.progress(90)
            time.sleep(0.3)
            
            progress_bar.progress(100)
            status_text.empty()
            progress_bar.empty()
            
            if analysis_results and analysis_results.get('success'):
                st.session_state.current_analysis = analysis_results
                st.success("✅ Analysis complete!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("❌ Analysis failed: " + analysis_results.get('message', 'Unknown error'))
                
                # HELPFUL ERROR STATE ✨
                with st.expander("😕 Need help?"):
                    st.markdown("""
                    **Common issues:**
                    - LLM connection might be down
                    - Document text was not extracted properly
                    - Knowledge base is empty (upload documents first)
                    
                    **Try this:**
                    1. Check Connections tab - verify LLM is connected
                    2. Upload some HCMPACT standards to Knowledge Base
                    3. Try a different document
                    4. Check Railway logs for detailed errors
                    """)
    
    # ==== SHOW EXISTING ANALYSIS ====
    if st.session_state.get('current_analysis'):
        st.markdown("---")
        
        # SUCCESS BANNER ✨
        st.markdown("""
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1.5rem; border-radius: 12px; color: white; margin-bottom: 2rem;'>
            <h3 style='margin: 0 0 0.5rem 0; color: white;'>✨ Analysis Complete</h3>
            <p style='margin: 0; opacity: 0.9;'>Review findings and generate UKG templates below</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 📊 Analysis Results")
        analysis = st.session_state.current_analysis
        
        # Show full analysis in expandable
        if analysis.get('analysis'):
            with st.expander("📄 Full Analysis Report", expanded=True):
                st.markdown(analysis['analysis'])
        
        # Show findings as cards ✨
        if analysis.get('findings'):
            st.markdown("#### 🔍 Key Findings")
            for i, finding in enumerate(analysis['findings'], 1):
                st.markdown(f"""
                <div style='background: #f8f9fa; padding: 1rem; border-radius: 8px; border-left: 4px solid #667eea; margin-bottom: 0.5rem;'>
                    <strong>{i}.</strong> {finding}
                </div>
                """, unsafe_allow_html=True)
        
        # Show recommendations as action items ✨
        if analysis.get('recommendations'):
            st.markdown("#### 💡 Recommendations")
            for i, rec in enumerate(analysis['recommendations'], 1):
                st.markdown(f"""
                <div style='background: #e7f3ff; padding: 1rem; border-radius: 8px; border-left: 4px solid #2196F3; margin-bottom: 0.5rem;'>
                    <strong>Action {i}:</strong> {rec}
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # ==== STEP 4: Template Generation ====
        st.markdown("### Step 4: Generate Templates")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown("Generate UKG-ready configuration templates based on analysis")
        
        with col2:
            if st.button("⚡ Generate", type="primary", use_container_width=True):
                # LOADING STATE for template generation ✨
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                status_text.info("📋 Generating pay code templates...")
                progress_bar.progress(25)
                time.sleep(0.3)
                
                status_text.info("🏢 Creating org structure templates...")
                progress_bar.progress(50)
                time.sleep(0.3)
                
                status_text.info("💰 Building deduction templates...")
                progress_bar.progress(75)
                
                templates = generate_templates(
                    analysis_results=analysis,
                    parsed_data=parsed_data
                )
                
                progress_bar.progress(100)
                status_text.empty()
                progress_bar.empty()
                
                if templates:
                    st.session_state.current_templates = templates
                    st.success("✅ Templates generated!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("❌ Failed to generate templates")
        
        # Show existing templates
        if st.session_state.get('current_templates'):
            st.markdown("---")
            st.success("✅ Templates ready for download!")
            
            display_results(
                analysis_results=analysis,
                templates=st.session_state.current_templates
            )
    
    # Show hint if no analysis yet
    elif uploaded_file:
        st.info("👆 Click 'Analyze' above to start AI analysis")


if __name__ == "__main__":
    st.title("Analysis Page - Polished")
    render_analysis_page()
