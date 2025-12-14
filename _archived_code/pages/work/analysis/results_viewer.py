"""
Results Display Module
Shows analysis results and provides downloads for templates
"""

import streamlit as st
from typing import Dict, Any, Optional, List


def display_results(analysis: Optional[Dict[str, Any]], templates: Optional[List[Dict[str, Any]]]):
    """
    Display analysis results and templates with proper download buttons
    
    Args:
        analysis: Analysis results dictionary
        templates: List of template dictionaries with download info
    """
    
    if not analysis and not templates:
        st.info("No results to display yet. Complete the analysis workflow above.")
        return
    
    # Display Analysis Results
    if analysis and analysis.get('success'):
        st.subheader("📊 Analysis Results")
        
        # Show analysis text
        if analysis.get('analysis'):
            with st.expander("📄 Full Analysis", expanded=True):
                st.markdown(analysis['analysis'])
        
        # Show key findings
        if analysis.get('findings'):
            st.markdown("#### 🔍 Key Findings")
            for i, finding in enumerate(analysis['findings'], 1):
                st.markdown(f"{i}. {finding}")
        
        # Show recommendations
        if analysis.get('recommendations'):
            st.markdown("#### 💡 Recommendations")
            for i, rec in enumerate(analysis['recommendations'], 1):
                st.markdown(f"{i}. {rec}")
        
        st.markdown("---")
    
    # Display Templates
    if templates:
        st.subheader("📋 Generated Templates")
        
        st.success(f"✅ {len(templates)} template(s) generated and ready for download")
        
        for template in templates:
            with st.expander(f"📄 {template['name']}", expanded=True):
                st.markdown(f"**Description:** {template['description']}")
                st.markdown(f"**Type:** {template['type'].upper()}")
                st.markdown(f"**Filename:** `{template['filename']}`")
                
                # Download button
                st.download_button(
                    label=f"⬇️ Download {template['name']}",
                    data=template['content'],
                    file_name=template['filename'],
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    key=f"download_{template['filename']}",
                    use_container_width=True
                )
        
        st.markdown("---")
        
        # Bulk download option if multiple templates
        if len(templates) > 1:
            st.markdown("#### 📦 Bulk Download")
            
            if st.button("⬇️ Download All Templates as ZIP", use_container_width=True):
                zip_buffer = _create_zip_archive(templates)
                if zip_buffer:
                    st.download_button(
                        label="⬇️ Download ZIP Archive",
                        data=zip_buffer,
                        file_name="XLR8_Templates.zip",
                        mime="application/zip",
                        use_container_width=True
                    )
    
    # Show parsed data summary if available
    if 'parsed_results' in st.session_state and st.session_state.parsed_results:
        parsed = st.session_state.parsed_results
        
        with st.expander("📊 Document Parsing Summary"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Parsing Method", parsed.get('method', 'unknown'))
            with col2:
                st.metric("Tables Found", len(parsed.get('tables', [])))
            with col3:
                st.metric("Processing Time", f"{parsed.get('processing_time', 0):.2f}s")
            
            if parsed.get('tables'):
                st.markdown("##### Tables Extracted:")
                for i, table in enumerate(parsed['tables'], 1):
                    st.markdown(f"- Table {i}: {table['row_count']} rows × {table['col_count']} columns")


def _create_zip_archive(templates: List[Dict[str, Any]]) -> bytes:
    """Create ZIP archive of all templates"""
    import zipfile
    from io import BytesIO
    
    try:
        zip_buffer = BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for template in templates:
                zip_file.writestr(
                    template['filename'],
                    template['content']
                )
        
        zip_buffer.seek(0)
        return zip_buffer.getvalue()
    
    except Exception as e:
        st.error(f"Error creating ZIP: {str(e)}")
        return None


def display_comparison_results(comparison_data: Dict[str, Any]):
    """Display results from parser comparison mode"""
    
    if not comparison_data or comparison_data.get('mode') != 'comparison':
        return
    
    st.subheader("📊 Parser Strategy Comparison")
    
    all_results = comparison_data.get('all_results', {})
    
    # Summary metrics
    col1, col2, col3 = st.columns(3)
    
    successful = sum(1 for r in all_results.values() if r.get('success'))
    total = len(all_results)
    
    with col1:
        st.metric("Strategies Tested", total)
    with col2:
        st.metric("Successful", successful)
    with col3:
        st.metric("Processing Time", f"{comparison_data.get('processing_time', 0):.2f}s")
    
    # Detailed results per strategy
    for strategy_name, result in all_results.items():
        status = "✅" if result.get('success') else "❌"
        
        with st.expander(f"{status} {strategy_name.upper()}", expanded=result.get('success')):
            if result.get('success'):
                st.success(f"Found {result.get('num_tables', 0)} tables")
                
                # Show first table preview
                if result.get('tables') and len(result['tables']) > 0:
                    st.markdown("**First table preview:**")
                    st.dataframe(result['tables'][0].head(10))
            else:
                st.error(f"Failed: {result.get('error', 'Unknown error')}")


# Standalone testing
if __name__ == "__main__":
    st.title("Results Viewer - Test Module")
    
    # Mock analysis
    mock_analysis = {
        'success': True,
        'analysis': "This is a sample payroll document with employee data.",
        'findings': [
            'Document contains 50 employee records',
            'Pay codes: REG, OT, BONUS identified',
            'Federal and state tax withholdings present'
        ],
        'recommendations': [
            'Map employee IDs to UKG Person Numbers',
            'Configure identified pay codes in UKG',
            'Set up tax calculation rules'
        ]
    }
    
    # Mock templates
    mock_templates = [
        {
            'name': 'UKG Employee Template',
            'type': 'excel',
            'content': b'mock excel data',
            'filename': 'employees.xlsx',
            'description': 'Employee information formatted for UKG import'
        },
        {
            'name': 'Pay Codes Template',
            'type': 'excel',
            'content': b'mock excel data',
            'filename': 'pay_codes.xlsx',
            'description': 'Pay code definitions'
        }
    ]
    
    display_results(mock_analysis, mock_templates)
