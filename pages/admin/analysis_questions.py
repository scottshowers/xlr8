"""
Analysis Questions Manager - Admin Section
Upload via Excel OR manage in-app
"""

import streamlit as st
import pandas as pd
import json
from pathlib import Path
from datetime import datetime
import logging
from typing import List, Dict, Any
from io import BytesIO

logger = logging.getLogger(__name__)

QUESTIONS_DB = Path("/data/analysis_questions.json")


def render_analysis_questions():
    """Main render function for analysis questions management."""
    
    st.title("📋 Analysis Questions Manager")
    st.markdown("Manage UKG implementation analysis questions - upload via Excel or edit in-app")
    
    # Tabs
    tab1, tab2, tab3 = st.tabs([
        "📤 Upload Excel",
        "✏️ Edit Questions",
        "💾 Export"
    ])
    
    with tab1:
        render_upload_tab()
    
    with tab2:
        render_edit_tab()
    
    with tab3:
        render_export_tab()


def render_upload_tab():
    """Upload and replace questions from Excel."""
    
    st.header("Upload Questions from Excel")
    
    st.info("""
    **Upload an Excel file to replace all current questions.**
    
    Required columns:
    - `Category` - Group name (e.g., "Payroll", "Benefits")
    - `Question` - The question text
    - `Required` - "Yes" or "No"
    
    Optional columns:
    - `Expected_Format` - Description of expected answer
    - `Keywords` - Comma-separated keywords
    - `Notes` - Additional context
    """)
    
    # Download template
    if st.button("📥 Download Template Excel", use_container_width=True):
        template_df = create_template()
        
        # Create buffer for Excel
        buffer = BytesIO()
        template_df.to_excel(buffer, index=False, engine='openpyxl')
        buffer.seek(0)
        
        st.download_button(
            label="Click to Download Template",
            data=buffer.getvalue(),
            file_name="analysis_questions_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    st.markdown("---")
    
    # File upload
    uploaded_file = st.file_uploader(
        "Upload Excel File",
        type=['xlsx', 'xls'],
        help="Upload questions Excel - will replace existing"
    )
    
    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)
            
            # Preview
            st.success(f"✓ Loaded {len(df)} rows")
            
            with st.expander("Preview Data"):
                st.dataframe(df, use_container_width=True)
            
            # Validate
            required_cols = ['Category', 'Question', 'Required']
            missing = [col for col in required_cols if col not in df.columns]
            
            if missing:
                st.error(f"❌ Missing required columns: {', '.join(missing)}")
                return
            
            # Import button
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🚀 Import & Replace All Questions", type="primary", use_container_width=True):
                    count = import_from_excel(df)
                    st.success(f"✅ Imported {count} questions successfully!")
                    st.rerun()
            
            with col2:
                st.warning("⚠️ This will replace ALL existing questions")
        
        except Exception as e:
            st.error(f"Error reading Excel: {str(e)}")
            logger.error(f"Excel read error: {str(e)}", exc_info=True)


def render_edit_tab():
    """Edit questions in-app."""
    
    st.header("Edit Questions")
    
    # Load questions
    questions = load_questions()
    
    if not questions:
        st.warning("No questions found. Upload Excel in the Upload tab.")
        return
    
    # Group by category
    categories = {}
    for q in questions:
        cat = q.get('category', 'Uncategorized')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(q)
    
    # Filter by category
    all_cats = ['All'] + sorted(categories.keys())
    selected_cat = st.selectbox("Filter by Category", all_cats)
    
    # Display questions
    if selected_cat == 'All':
        display_questions = questions
    else:
        display_questions = categories.get(selected_cat, [])
    
    st.markdown(f"**Showing {len(display_questions)} questions**")
    
    # Add new question button
    if st.button("➕ Add New Question", use_container_width=True):
        st.session_state['adding_question'] = True
    
    # Add new question form
    if st.session_state.get('adding_question', False):
        with st.form("new_question"):
            st.markdown("### Add New Question")
            
            col1, col2 = st.columns(2)
            with col1:
                new_cat = st.text_input("Category", value="Payroll")
            with col2:
                new_req = st.selectbox("Required?", ["Yes", "No"])
            
            new_question = st.text_area("Question", height=100)
            new_format = st.text_input("Expected Format (optional)")
            new_keywords = st.text_input("Keywords (comma-separated, optional)")
            new_notes = st.text_area("Notes (optional)")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("Save Question", type="primary", use_container_width=True):
                    if new_question:
                        add_question(
                            category=new_cat,
                            question=new_question,
                            required=(new_req == "Yes"),
                            expected_format=new_format,
                            keywords=new_keywords,
                            notes=new_notes
                        )
                        st.session_state['adding_question'] = False
                        st.success("✅ Question added!")
                        st.rerun()
                    else:
                        st.error("Question text is required")
            
            with col2:
                if st.form_submit_button("Cancel", use_container_width=True):
                    st.session_state['adding_question'] = False
                    st.rerun()
    
    st.markdown("---")
    
    # Display existing questions
    for idx, q in enumerate(display_questions):
        with st.expander(f"**{q.get('category')}** | {q.get('question')[:80]}..."):
            # Display question details
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**Question:** {q.get('question')}")
                st.markdown(f"**Category:** {q.get('category')}")
                st.markdown(f"**Required:** {'Yes' if q.get('required') else 'No'}")
                
                if q.get('expected_format'):
                    st.markdown(f"**Expected Format:** {q.get('expected_format')}")
                
                if q.get('keywords'):
                    st.markdown(f"**Keywords:** {q.get('keywords')}")
                
                if q.get('notes'):
                    st.markdown(f"**Notes:** {q.get('notes')}")
            
            with col2:
                # Edit button
                if st.button("✏️ Edit", key=f"edit_{idx}"):
                    st.session_state[f'editing_{idx}'] = True
                    st.rerun()
                
                # Delete button
                if st.button("🗑️ Delete", key=f"delete_{idx}"):
                    if st.session_state.get(f'confirm_delete_{idx}', False):
                        delete_question(q.get('id'))
                        st.success("Question deleted")
                        st.rerun()
                    else:
                        st.session_state[f'confirm_delete_{idx}'] = True
                        st.warning("Click again to confirm delete")


def render_export_tab():
    """Export questions."""
    
    st.header("Export Questions")
    
    questions = load_questions()
    
    if not questions:
        st.warning("No questions to export")
        return
    
    st.success(f"✓ {len(questions)} questions loaded")
    
    # Convert to DataFrame
    df = pd.DataFrame(questions)
    
    # Reorder columns
    cols = ['category', 'question', 'required', 'expected_format', 'keywords', 'notes']
    df = df[[col for col in cols if col in df.columns]]
    
    # Preview
    with st.expander("Preview Data"):
        st.dataframe(df, use_container_width=True)
    
    # Export buttons
    col1, col2 = st.columns(2)
    
    with col1:
        # Excel export
        buffer = BytesIO()
        df.to_excel(buffer, index=False, engine='openpyxl')
        buffer.seek(0)
        
        st.download_button(
            label="📥 Download as Excel",
            data=buffer.getvalue(),
            file_name=f"analysis_questions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    with col2:
        # JSON export
        json_str = json.dumps(questions, indent=2)
        st.download_button(
            label="📥 Download as JSON",
            data=json_str,
            file_name=f"analysis_questions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )


# ==================== DATA FUNCTIONS ====================

def load_questions() -> List[Dict[str, Any]]:
    """Load questions from JSON file."""
    if not QUESTIONS_DB.exists():
        return []
    
    try:
        with open(QUESTIONS_DB, 'r') as f:
            data = json.load(f)
        return data.get('questions', [])
    except Exception as e:
        logger.error(f"Error loading questions: {str(e)}")
        return []


def save_questions(questions: List[Dict[str, Any]]):
    """Save questions to JSON file."""
    QUESTIONS_DB.parent.mkdir(parents=True, exist_ok=True)
    
    data = {
        'version': '1.0',
        'updated_at': datetime.now().isoformat(),
        'questions': questions
    }
    
    with open(QUESTIONS_DB, 'w') as f:
        json.dump(data, f, indent=2)


def import_from_excel(df: pd.DataFrame) -> int:
    """Import questions from Excel DataFrame."""
    questions = []
    
    for idx, row in df.iterrows():
        q = {
            'id': f"Q{idx+1:04d}",
            'category': str(row.get('Category', 'Uncategorized')),
            'question': str(row.get('Question', '')),
            'required': str(row.get('Required', 'No')).lower() == 'yes',
            'expected_format': str(row.get('Expected_Format', '')),
            'keywords': str(row.get('Keywords', '')),
            'notes': str(row.get('Notes', '')),
            'created_at': datetime.now().isoformat()
        }
        
        if q['question']:
            questions.append(q)
    
    save_questions(questions)
    return len(questions)


def add_question(category: str, question: str, required: bool,
                expected_format: str = '', keywords: str = '', notes: str = ''):
    """Add a new question."""
    questions = load_questions()
    
    new_id = f"Q{len(questions)+1:04d}"
    
    new_q = {
        'id': new_id,
        'category': category,
        'question': question,
        'required': required,
        'expected_format': expected_format,
        'keywords': keywords,
        'notes': notes,
        'created_at': datetime.now().isoformat()
    }
    
    questions.append(new_q)
    save_questions(questions)


def delete_question(question_id: str):
    """Delete a question by ID."""
    questions = load_questions()
    questions = [q for q in questions if q.get('id') != question_id]
    save_questions(questions)


def create_template() -> pd.DataFrame:
    """Create sample template DataFrame."""
    template_data = {
        'Category': ['Payroll', 'Payroll', 'Benefits', 'Time & Attendance'],
        'Question': [
            'What is the pay frequency?',
            'What are the standard pay codes used?',
            'What health insurance plans are offered?',
            'What is the standard work week?'
        ],
        'Required': ['Yes', 'Yes', 'No', 'Yes'],
        'Expected_Format': [
            'Weekly, Bi-weekly, Semi-monthly, Monthly',
            'List all pay code names and descriptions',
            'List plan names and coverage details',
            'Number of hours per week'
        ],
        'Keywords': [
            'pay period, frequency, schedule',
            'earnings, pay types, compensation',
            'medical, insurance, coverage',
            'hours, schedule, workweek'
        ],
        'Notes': ['', '', 'Include both medical and dental', '']
    }
    
    return pd.DataFrame(template_data)


if __name__ == "__main__":
    render_analysis_questions()
