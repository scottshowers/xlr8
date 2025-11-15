"""Projects & Clients Management"""
import streamlit as st
from datetime import datetime

def render_projects_page():
    st.markdown("## 📁 Projects & Clients")
    
    # Quick create section
    st.markdown("### Create New Project")
    
    col1, col2 = st.columns(2)
    
    with col1:
        project_name = st.text_input("Project Name", placeholder="e.g., Acme Corp Implementation")
    
    with col2:
        customer_id = st.text_input("Customer ID", placeholder="e.g., ACME001")
    
    impl_type = st.selectbox(
        "Implementation Type",
        ["New Implementation", "Upgrade", "Enhancement", "Support"]
    )
    
    if st.button("Create Project", type="primary"):
        if project_name:
            # Add to session state
            if 'projects' not in st.session_state:
                st.session_state.projects = {}
            
            st.session_state.projects[project_name] = {
                'customer_id': customer_id,
                'implementation_type': impl_type,
                'created_date': datetime.now().strftime("%Y-%m-%d"),
                'status': 'Active'
            }
            
            # Set as current project
            st.session_state.current_project = project_name
            
            st.success(f"✅ Project '{project_name}' created and activated!")
            st.rerun()
        else:
            st.error("Project name is required")
    
    # Show existing projects
    if st.session_state.get('projects'):
        st.markdown("---")
        st.markdown("### Existing Projects")
        
        for name, data in st.session_state.projects.items():
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.write(f"**{name}**")
                st.caption(f"Customer: {data.get('customer_id', 'N/A')} | Type: {data.get('implementation_type', 'N/A')}")
            
            with col2:
                if st.session_state.current_project == name:
                    st.success("Active")
                else:
                    if st.button("Activate", key=f"activate_{name}"):
                        st.session_state.current_project = name
                        st.rerun()
            
            with col3:
                if st.button("Delete", key=f"delete_{name}"):
                    del st.session_state.projects[name]
                    if st.session_state.current_project == name:
                        st.session_state.current_project = None
                    st.rerun()
