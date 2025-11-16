"""
Projects Page - Professional & Polished
Beautiful project cards, visual indicators, professional polish
Version: 3.0
"""

import streamlit as st
from datetime import datetime
import sys
from pathlib import Path
import time

# Import utilities
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from utils.error_handler import ErrorHandler
from utils.toast import ToastManager, ProjectToasts


def render_projects_page():
    """Render projects management page with professional polish"""
    
    # Initialize delete confirmation tracking
    if 'delete_confirmations' not in st.session_state:
        st.session_state.delete_confirmations = {}
    
    st.markdown("## 📁 Projects & Client Management")
    
    st.markdown("""
    <div style='background: linear-gradient(135deg, #f5f7f9 0%, #e8eef3 100%); padding: 1rem; border-radius: 12px; border-left: 4px solid #8ca6be; margin-bottom: 1.5rem; box-shadow: 0 2px 8px rgba(0,0,0,0.05);'>
        <div style='display: flex; align-items: center; gap: 0.75rem;'>
            <div style='font-size: 1.3rem;'>🏗️</div>
            <div>
                <strong style='color: #6d8aa0; font-size: 1rem;'>Project Management</strong><br>
                <span style='color: #7d96a8; font-size: 0.9rem;'>Create and manage UKG implementation projects, track client information, and organize your work by customer.</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Quick stats dashboard
    if st.session_state.get('projects'):
        st.markdown("""
        <div style='margin-bottom: 1.5rem;'>
            <h3 style='color: #6d8aa0; margin-bottom: 1rem; font-size: 1.1rem; display: flex; align-items: center; gap: 0.5rem;'>
                📊 Dashboard
            </h3>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total = len(st.session_state.get('projects', {}))
            st.markdown(f"""
            <div style='background: white; padding: 1.5rem; border-radius: 12px; border: 2px solid #e8eef3; box-shadow: 0 4px 12px rgba(0,0,0,0.08); text-align: center;'>
                <div style='font-size: 2.5rem; margin-bottom: 0.5rem;'>📁</div>
                <div style='font-size: 2rem; font-weight: 700; color: #6d8aa0; margin-bottom: 0.25rem;'>{total}</div>
                <div style='color: #7d96a8; font-size: 0.9rem; font-weight: 500;'>Total Projects</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            active_project = st.session_state.get('current_project') or "None"
            display_name = active_project if len(active_project) < 12 else active_project[:9] + "..."
            st.markdown(f"""
            <div style='background: white; padding: 1.5rem; border-radius: 12px; border: 2px solid #e8f5e9; box-shadow: 0 4px 12px rgba(0,0,0,0.08); text-align: center;'>
                <div style='font-size: 2.5rem; margin-bottom: 0.5rem;'>📌</div>
                <div style='font-size: 1.2rem; font-weight: 600; color: #28a745; margin-bottom: 0.25rem;'>{display_name}</div>
                <div style='color: #7d96a8; font-size: 0.9rem; font-weight: 500;'>Active Project</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            pro_count = sum(1 for p in st.session_state.get('projects', {}).values() 
                          if 'Pro' in p.get('implementation_type', ''))
            st.markdown(f"""
            <div style='background: white; padding: 1.5rem; border-radius: 12px; border: 2px solid #e3f2fd; box-shadow: 0 4px 12px rgba(0,0,0,0.08); text-align: center;'>
                <div style='font-size: 2.5rem; margin-bottom: 0.5rem;'>🔵</div>
                <div style='font-size: 2rem; font-weight: 700; color: #2196F3; margin-bottom: 0.25rem;'>{pro_count}</div>
                <div style='color: #7d96a8; font-size: 0.9rem; font-weight: 500;'>UKG Pro</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            wfm_count = sum(1 for p in st.session_state.get('projects', {}).values() 
                          if 'WFM' in p.get('implementation_type', ''))
            st.markdown(f"""
            <div style='background: white; padding: 1.5rem; border-radius: 12px; border: 2px solid #e8f5e9; box-shadow: 0 4px 12px rgba(0,0,0,0.08); text-align: center;'>
                <div style='font-size: 2.5rem; margin-bottom: 0.5rem;'>🟢</div>
                <div style='font-size: 2rem; font-weight: 700; color: #4caf50; margin-bottom: 0.25rem;'>{wfm_count}</div>
                <div style='color: #7d96a8; font-size: 0.9rem; font-weight: 500;'>UKG WFM</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<div style='margin-bottom: 1.5rem;'></div>", unsafe_allow_html=True)
    
    # Two column layout
    col_left, col_right = st.columns([3, 2])
    
    with col_left:
        # Create New Project Section - COMPACT & PROFESSIONAL
        st.markdown("""
        <div style='background: linear-gradient(135deg, #8ca6be 0%, #6d8aa0 100%); padding: 1rem; border-radius: 12px; margin-bottom: 1.5rem; box-shadow: 0 4px 16px rgba(140, 166, 190, 0.25);'>
            <h3 style='color: white; margin: 0; font-size: 1.1rem; display: flex; align-items: center; gap: 0.5rem;'>
                ✨ Create New Project
            </h3>
        </div>
        """, unsafe_allow_html=True)
        
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
            
            submitted = st.form_submit_button("✨ Create Project", use_container_width=True, type="primary")
            
            if submitted:
                # Validation
                if not project_name or not customer_id:
                    st.markdown("""
                    <div style='background: #fff3cd; padding: 1rem; border-radius: 8px; border-left: 4px solid #ffc107; margin-top: 1rem;'>
                        <strong style='color: #856404;'>⚠️ Required Fields Missing</strong><br>
                        <span style='color: #856404; font-size: 0.9rem;'>Please fill in both <strong>Project Name</strong> and <strong>Customer ID</strong> to create a project.</span>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    # Check for duplicates
                    if 'projects' not in st.session_state:
                        st.session_state.projects = {}
                    
                    if project_name in st.session_state.projects:
                        st.markdown("""
                        <div style='background: #fff3cd; padding: 1rem; border-radius: 8px; border-left: 4px solid #ffc107; margin-top: 1rem;'>
                            <strong style='color: #856404;'>⚠️ Project Already Exists</strong><br>
                            <span style='color: #856404; font-size: 0.9rem;'>A project with this name already exists. Please choose a different name.</span>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        # Create project
                        try:
                            new_project = {
                                'customer_id': customer_id,
                                'implementation_type': implementation_type,
                                'description': project_description if project_description else None,
                                'go_live_date': str(go_live_date) if go_live_date else None,
                                'consultant': consultant_name if consultant_name else None,
                                'created_date': datetime.now().strftime("%Y-%m-%d"),
                                'status': 'Active',
                                'notes': []
                            }
                            
                            st.session_state.projects[project_name] = new_project
                            
                            # Try to save to Supabase if enabled
                            try:
                                from utils.data.supabase_handler import save_project
                                from config import AppConfig
                                if AppConfig.USE_SUPABASE_PERSISTENCE:
                                    save_project(project_name, new_project)
                            except Exception as e:
                                ErrorHandler.handle_supabase_error(e, operation="save project")
                            
                            ProjectToasts.created(project_name)
                            time.sleep(0.5)
                            st.rerun()
                            
                        except Exception as e:
                            ErrorHandler.handle_generic_error(e, context="creating project")
                            ToastManager.error("Failed to create project", "❌")
    
    with col_right:
        # Existing Projects List
        st.markdown("""
        <h3 style='color: #6d8aa0; margin-bottom: 1rem; font-size: 1.1rem; display: flex; align-items: center; gap: 0.5rem;'>
            📋 Projects List
        </h3>
        """, unsafe_allow_html=True)
        
        if st.session_state.get('projects'):
            # Sort projects - active first
            sorted_projects = sorted(
                st.session_state.projects.items(),
                key=lambda x: (x[0] != st.session_state.get('current_project'), x[0])
            )
            
            for proj_name, proj_data in sorted_projects:
                is_active = (proj_name == st.session_state.get('current_project'))
                _render_project_card(proj_name, proj_data, is_active, st.container())
        else:
            st.markdown("""
            <div style='background: linear-gradient(135deg, #f5f7f9 0%, #e8eef3 100%); padding: 2rem; border-radius: 12px; text-align: center; border: 2px solid rgba(140, 166, 190, 0.2);'>
                <div style='font-size: 2.5rem; margin-bottom: 0.75rem; opacity: 0.8;'>📋</div>
                <div style='color: #6d8aa0; font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem;'>No Projects Yet</div>
                <div style='color: #7d96a8; font-size: 0.9rem;'>Create your first project using the form on the left</div>
            </div>
            """, unsafe_allow_html=True)


def _render_project_card(proj_name: str, proj_data: dict, is_active: bool, container):
    """Render a single project card with professional styling"""
    
    # Get type-specific styling
    impl_type = proj_data.get('implementation_type', 'N/A')
    if 'Pro' in impl_type and 'WFM' in impl_type:
        type_icon = "🔵🟢"
        type_color = "#6d8aa0"
        border_color = "#6d8aa0"
    elif 'Pro' in impl_type:
        type_icon = "🔵"
        type_color = "#2196F3"
        border_color = "#2196F3"
    elif 'WFM' in impl_type:
        type_icon = "🟢"
        type_color = "#4caf50"
        border_color = "#4caf50"
    else:
        type_icon = "📁"
        type_color = "#8ca6be"
        border_color = "#8ca6be"
    
    # Active project styling
    if is_active:
        card_bg = "linear-gradient(135deg, #fff9e6 0%, #fffef0 100%)"
        border_style = f"3px solid {type_color}"
        badge_html = f"<div style='background: {type_color}; color: white; padding: 0.25rem 0.75rem; border-radius: 12px; font-size: 0.75rem; font-weight: 600; display: inline-block;'>✓ ACTIVE</div>"
    else:
        card_bg = "white"
        border_style = f"2px solid #e8eef3"
        badge_html = ""
    
    with container:
        st.markdown(f"""
        <div style='background: {card_bg}; padding: 1.5rem; border-radius: 12px; border: {border_style}; box-shadow: 0 4px 12px rgba(0,0,0,0.08); margin-bottom: 1rem; transition: transform 0.2s;'>
            <div style='display: flex; justify-content: space-between; align-items: start; margin-bottom: 1rem;'>
                <div style='flex: 1;'>
                    <div style='font-size: 1.5rem; margin-bottom: 0.5rem;'>{type_icon}</div>
                    <h4 style='margin: 0 0 0.5rem 0; color: #6d8aa0; font-size: 1.1rem;'>{proj_name}</h4>
                    {badge_html}
                </div>
            </div>
            
            <div style='background: rgba(109, 138, 160, 0.05); padding: 1rem; border-radius: 8px; margin-bottom: 1rem;'>
                <div style='color: #6c757d; font-size: 0.9rem; line-height: 1.8;'>
                    <div><strong style='color: #8ca6be;'>Customer:</strong> {proj_data.get('customer_id', 'N/A')}</div>
                    <div><strong style='color: #8ca6be;'>Type:</strong> {impl_type}</div>
                    <div><strong style='color: #8ca6be;'>Created:</strong> {proj_data.get('created_date', 'N/A')}</div>
                    {f"<div><strong style='color: #8ca6be;'>Consultant:</strong> {proj_data.get('consultant')}</div>" if proj_data.get('consultant') else ""}
                    {f"<div><strong style='color: #8ca6be;'>Go-Live:</strong> {proj_data.get('go_live_date')}</div>" if proj_data.get('go_live_date') else ""}
                </div>
            </div>
            
            {f"<div style='color: #6c757d; font-size: 0.9rem; margin-bottom: 1rem; font-style: italic;'>{proj_data.get('description')}</div>" if proj_data.get('description') else ""}
        </div>
        """, unsafe_allow_html=True)
        
        # Action buttons
        col1, col2 = st.columns(2)
        
        with col1:
            if not is_active:
                if st.button("📌 Activate", key=f"activate_{proj_name}_{id(proj_data)}", use_container_width=True, type="primary"):
                    st.session_state.current_project = proj_name
                    ProjectToasts.activated(proj_name)
                    st.rerun()
            else:
                st.markdown("""
                <div style='background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; padding: 0.5rem; border-radius: 6px; text-align: center; font-weight: 600;'>
                    ✓ Active
                </div>
                """, unsafe_allow_html=True)
        
        with col2:
            if st.button("🗑️ Delete", key=f"delete_{proj_name}_{id(proj_data)}", use_container_width=True, type="secondary"):
                st.session_state.delete_confirmations[proj_name] = True
                st.rerun()
        
        # Delete confirmation
        if st.session_state.delete_confirmations.get(proj_name, False):
            st.markdown(f"""
            <div style='background: #fff3cd; padding: 1rem; border-radius: 8px; border-left: 4px solid #ffc107; margin-top: 0.5rem;'>
                <strong style='color: #856404;'>⚠️ Confirm Delete</strong><br>
                <span style='color: #856404; font-size: 0.9rem;'>Delete '{proj_name}'? This cannot be undone.</span>
            </div>
            """, unsafe_allow_html=True)
            
            col_confirm, col_cancel = st.columns(2)
            
            with col_confirm:
                if st.button("✓ Confirm", key=f"confirm_del_{proj_name}_{id(proj_data)}", type="primary", use_container_width=True):
                    try:
                        ToastManager.info(f"Deleting '{proj_name}'...", "🗑️")
                        
                        if 'projects' in st.session_state and proj_name in st.session_state.projects:
                            del st.session_state.projects[proj_name]
                        
                        if st.session_state.get('current_project') == proj_name:
                            st.session_state.current_project = None
                        
                        st.session_state.delete_confirmations[proj_name] = False
                        
                        try:
                            from utils.data.supabase_handler import delete_project
                            from config import AppConfig
                            if AppConfig.USE_SUPABASE_PERSISTENCE:
                                delete_project(proj_name)
                                ProjectToasts.deleted(proj_name)
                        except Exception as e:
                            ErrorHandler.handle_supabase_error(e, operation="delete project")
                            ProjectToasts.deleted(proj_name)
                        
                        time.sleep(0.3)
                        st.rerun()
                        
                    except Exception as e:
                        ErrorHandler.handle_generic_error(e, context="deleting project")
                        ToastManager.error("Failed to delete", "❌")
            
            with col_cancel:
                if st.button("✗ Cancel", key=f"cancel_del_{proj_name}_{id(proj_data)}", use_container_width=True):
                    st.session_state.delete_confirmations[proj_name] = False
                    ToastManager.info("Delete cancelled", "↩️")
                    st.rerun()
        
        # Notes section
        with st.expander("📝 Project Notes"):
            new_note = st.text_area(
                "Add a note",
                key=f"note_input_{proj_name}_{id(proj_data)}",
                height=60,
                placeholder="Add implementation notes, decisions, or reminders..."
            )
            
            if st.button("Add Note", key=f"add_note_{proj_name}_{id(proj_data)}"):
                if new_note:
                    try:
                        if 'notes' not in proj_data:
                            proj_data['notes'] = []
                        proj_data['notes'].append({
                            'text': new_note,
                            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        ProjectToasts.note_added()
                        time.sleep(0.2)
                        st.rerun()
                    except Exception as e:
                        ErrorHandler.handle_generic_error(e, context="adding note")
                        ToastManager.error("Failed to add note", "❌")
            
            # Display existing notes
            if proj_data.get('notes'):
                st.markdown("**Recent Notes:**")
                for note in proj_data['notes'][-3:]:
                    if isinstance(note, dict):
                        timestamp = note.get('timestamp', 'Unknown')
                        text = note.get('text', '')
                        st.markdown(f"""
                        <div style='background: #f8f9fa; padding: 0.75rem; border-radius: 6px; border-left: 3px solid #8ca6be; margin-bottom: 0.5rem;'>
                            <small><strong style='color: #6d8aa0;'>{timestamp}:</strong> {text}</small>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"<small>{note}</small>", unsafe_allow_html=True)


if __name__ == "__main__":
    st.title("Projects - Professional")
    render_projects_page()
