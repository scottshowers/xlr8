"""
Results Display Module
Shows analysis results and downloadable templates

Owner: Person E - UI Team
Dependencies: streamlit, components
"""

import streamlit as st
from typing import Dict, Any, Optional, List

def display_results(analysis: Optional[Dict[str, Any]], templates: Optional[List[Dict[str, Any]]]):
    """Display analysis results and templates"""
    if analysis:
        st.subheader("📊 Analysis Results")
        st.json(analysis)
    
    if templates:
        st.subheader("📋 Generated Templates")
        for template in templates:
            with st.expander(f"📄 {template.get('name', 'Template')}"):
                st.download_button(
                    "Download",
                    data=template.get('content', ''),
                    file_name=template.get('filename', 'template.xlsx')
                )

if __name__ == "__main__":
    st.title("Results Viewer - Test Module")
