"""
Projects & Clients Management Page - COMPLETE FIXED VERSION
Fixes: HTML rendering with unsafe_allow_html=True, removed all debug code
"""

import streamlit as st
from datetime import datetime


def render_projects_page():
    """Render projects management page with full functionality"""
    
    st.markdown("## 📁 Projects & Client Management")
    
    st.markdown("""
    <div class='info-box'>
        <strong>Project Management:</strong> Create and manage UKG implementation projects,
        track client information, and organize your work by customer.
    </div>
    """, unsafe_allow_html=True)
    
    # Quick stats if projects exist
    if st.session_state.get('projects'):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📁 Total Projects", len(st.session_state.get('projects', {})))
        with col2:
            active_project = st.session_state.get('current_project') or "None"
            display_name = active_project if len(active_project) < 15 else active_project[:12] + "..."
            st.metric("📌 Active Project", display_name)
        with col3:
            pro_count = sum(1 for p in st.session_state.get('projects', {}).values() 
                          if 'Pro' in p.get('implementation_type', ''))
            st.metric("🔵 UKG Pro", pro_count)
        with col4:
            wfm_count = sum(1 for p in st.session_state.get('projects', {}).values() 
                          if 'WFM' in p.get('implementation_type', ''))
            st.metric("🟢 UKG WFM", wfm_count)
        
        st.markdown("---")
    
    # Two column layout
    col_left, col_right = st.columns([3, 2])
    
    with col_left:
        # Create New Project Section
        st.markdown("### 📋 Create New Project")
        
        with st.form("new_project_form"):
            project_name = st.text_input(
                "Project Name *",
                placeholder="e.g., Acme Corp - UKG Pro Implementation",
                help="Descriptive name for this implementation project"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                customer_id = st.text_input(
                    "Customer ID *",
                    placeholder="e.g., ACME001",
                    help="Unique identifier for this customer"
                )
            with col2:
                implementation_type = st.selectbox(
                    "Implementation Type *",
                    ["UKG Pro", "UKG WFM", "UKG Pro + WFM"],
                    help="Which UKG product(s) are being implemented"
                )
            
            project_description = st.text_area(
                "Project Description (Optional)",
                placeholder="Brief description of implementation scope, timeline, or special requirements...",
                height=100
            )
            
            col1, col2 = st.columns(2)
            with col1:
                go_live_date = st.date_input(
                    "Target Go-Live Date (Optional)",
                    value=None
                )
            with col2:
                consultant_name = st.text_input(
                    "Lead Consultant (Optional)",
                    placeholder="Your name"
                )
            
            submitted = st.form_submit_button("✨ Create Project", use_container_width=True)
            
            if submitted:
                if not project_name or not customer_id:
                    st.error("❌ Project Name and Customer ID are required!")
                elif project_name in st.session_state.get('projects', {}):
                    st.error(f"❌ Project '{project_name}' already exists!")
                else:
                    # Ensure projects dict exists
                    if 'projects' not in st.session_state:
                        st.session_state.projects = {}
                    
                    # Create project
                    st.session_state.projects[project_name] = {
                        'customer_id': customer_id,
                        'implementation_type': implementation_type,
                        'description': project_description,
                        'go_live_date': str(go_live_date) if go_live_date else None,
                        'consultant': consultant_name,
                        'created_date': datetime.now().strftime("%Y-%m-%d"),
                        'created_time': datetime.now().strftime("%H:%M:%S"),
                        'data_sources': [],
                        'notes': []
                    }
                    st.session_state.current_project = project_name
                    st.success(f"✅ Project '{project_name}' created successfully!")
                    st.rerun()
    
    with col_right:
        st.markdown("### 🚀 Quick Start Guide")
        st.markdown("""
        <div class='info-box'>
            <h4 style='margin-top: 0;'>Getting Started</h4>
            <ol style='margin-left: 1.5rem; line-height: 2;'>
                <li><strong>Create a project</strong> ← Start here</li>
                <li><strong>Upload documents</strong> in Analysis tab</li>
                <li><strong>Run AI analysis</strong> with your data</li>
                <li><strong>Generate templates</strong> for UKG</li>
                <li><strong>Download results</strong> and implement</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### ✨ Project Features")
        st.markdown("""
        <div class='success-box'>
            <ul style='list-style: none; padding-left: 0; line-height: 2;'>
                <li>✓ Multi-project organization</li>
                <li>✓ Client information tracking</li>
                <li>✓ Document association</li>
                <li>✓ Implementation timeline</li>
                <li>✓ Consultant assignment</li>
                <li>✓ Project notes & history</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # Existing Projects List
    if st.session_state.get('projects'):
        st.markdown("---")
        st.markdown("### 📂 Your Projects")
        
        for proj_name, proj_data in st.session_state.get('projects', {}).items():
            is_active = proj_name == st.session_state.get('current_project')
            
            with st.expander(f"{'📌 ' if is_active else '📁 '}{proj_name}", expanded=is_active):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"""
                    **Customer ID:** {proj_data['customer_id']}  
                    **Type:** {proj_data['implementation_type']}  
                    **Created:** {proj_data['created_date']}  
                    **Consultant:** {proj_data.get('consultant', 'Not specified')}
                    """)
                    
                    if proj_data.get('description'):
                        st.markdown(f"**Description:** {proj_data['description']}")
                    
                    if proj_data.get('go_live_date'):
                        st.markdown(f"**Target Go-Live:** {proj_data['go_live_date']}")
                    
                    # Project notes
                    if proj_data.get('notes'):
                        st.markdown(f"**Notes:** {len(proj_data['notes'])} note(s)")
                
                with col2:
                    if not is_active:
                        if st.button(f"Activate", key=f"activate_{proj_name}", use_container_width=True):
                            st.session_state.current_project = proj_name
                            st.rerun()
                    else:
                        st.success("✓ Active")
                    
                    if st.button(f"Delete", key=f"delete_{proj_name}", use_container_width=True):
                        if st.checkbox(f"Confirm delete {proj_name}?", key=f"confirm_del_{proj_name}"):
                            if 'projects' in st.session_state:
                                del st.session_state.projects[proj_name]
                            if st.session_state.get('current_project') == proj_name:
                                st.session_state.current_project = None
                            st.rerun()
                
                # Add note functionality
                st.markdown("##### 📝 Project Notes")
                new_note = st.text_area(
                    "Add a note",
                    key=f"note_input_{proj_name}",
                    height=60,
                    placeholder="Add implementation notes, decisions, or reminders..."
                )
                
                if st.button("Add Note", key=f"add_note_{proj_name}"):
                    if new_note:
                        if 'notes' not in proj_data:
                            proj_data['notes'] = []
                        proj_data['notes'].append({
                            'text': new_note,
                            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        st.success("✅ Note added")
                        st.rerun()
                
                # Display existing notes
                if proj_data.get('notes'):
                    for note in proj_data['notes'][-3:]:  # Show last 3
                        # Handle both old string format and new dict format
                        if isinstance(note, dict):
                            st.markdown(f"<small>**{note['timestamp']}:** {note['text']}</small>", 
                                      unsafe_allow_html=True)
                        else:
                            # Legacy string format
                            st.markdown(f"<small>{note}</small>", 
                                      unsafe_allow_html=True)
