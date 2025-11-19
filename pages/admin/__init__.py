"""
Admin Section Router
Routes to different admin functions
"""

import streamlit as st


def render_admin():
    """Main admin page with sub-tabs."""
    
    st.title("👤 Administration")
    
    # Sub-tabs
    tabs = st.tabs([
        "📋 Analysis Questions",
        "👥 Users",
        "📊 Audit Logs",
        "⚙️ Settings"
    ])
    
    # Tab 1: Analysis Questions
    with tabs[0]:
        from pages.admin.analysis_questions import render_analysis_questions
        render_analysis_questions()
    
    # Tab 2: Users (placeholder)
    with tabs[1]:
        st.info("User management - Coming soon")
    
    # Tab 3: Audit (placeholder)
    with tabs[2]:
        st.info("Audit logs - Coming soon")
    
    # Tab 4: Settings (placeholder)
    with tabs[3]:
        st.info("System settings - Coming soon")


if __name__ == "__main__":
    render_admin()
