"""
Analysis Questions Manager - Admin Section
FIXED: Saves uploaded files to disk for future selection
"""

import streamlit as st
import pandas as pd
import json
from pathlib import Path
from datetime import datetime
import logging
from typing import List, Dict, Any
from io import BytesIO
import shutil

logger = logging.getLogger(__name__)

# Storage paths
QUESTIONS_DB = Path("/data/analysis_questions.json")
UPLOADS_DIR = Path("/mnt/user-data/uploads")  # FIXED: Correct path


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
    """Upload questions from Excel - with SAVE to disk feature."""
    
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
    
    # Download template button
    if st.button("📥 Download Template Excel", use_container_width=True):
        template_df = create_template()
        
        buffer = BytesIO()
        template_df.to_excel(buffer, index=False, engine='openpyxl')
        buffer.seek(0)
        
        st.download_button(
            label="⬇️ Click to Download Template",
            data=buffer.getvalue(),
            file_name=f"analysis_questions_template_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    st.markdown("---")
    
    # TWO OPTIONS: Upload new OR select existing
    upload_option = st.radio(
        "Choose source:",
        ["📤 Upload New File", "📁 Select from Existing Uploads"],
        horizontal=True
    )
    
    df = None
    file_path = None
    
    if upload_option == "📤 Upload New File":
        # File upload widget
        uploaded_file = st.file_uploader(
            "Upload Excel File",
            type=['xlsx', 'xls'],
            help="Upload questions Excel - will be saved and processed"
        )
        
        if uploaded_file:
            try:
                # CRITICAL FIX: Save file to disk first
                # Ensure directory exists
                UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"analysis_questions_{timestamp}.xlsx"
                file_path = UPLOADS_DIR / filename
                
                # Save uploaded file
                with open(file_path, 'wb') as f:
                    f.write(uploaded_file.getvalue())
                
                st.success(f"✅ Saved to: {filename}")
                
                # Now read it
                df = pd.read_excel(file_path)
                
            except Exception as e:
                st.error(f"❌ Error saving/reading file: {str(e)}")
                logger.error(f"Upload error: {str(e)}", exc_info=True)
                return
    
    else:
        # Select from existing uploads
        if not UPLOADS_DIR.exists():
            st.warning(f"📁 Uploads directory not found: {UPLOADS_DIR}")
            return
        
        # Find Excel files
        excel_files = sorted(
            list(UPLOADS_DIR.glob('*.xlsx')) + list(UPLOADS_DIR.glob('*.xls')),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        if not excel_files:
            st.warning("📁 No Excel files found in uploads. Upload a file first in Setup → HCMPACT LLM Seeding")
            return
        
        # Dropdown to select file
        selected_file = st.selectbox(
            "Select Excel file:",
            options=excel_files,
            format_func=lambda x: f"{x.name} ({datetime.fromtimestamp(x.stat().st_mtime).strftime('%Y-%m-%d %H:%M')})"
        )
        
        if selected_file:
            try:
                df = pd.read_excel(selected_file)
                file_path = selected_file
                st.success(f"✅ Loaded: {selected_file.name}")
            except Exception as e:
                st.error(f"❌ Error reading file: {str(e)}")
                logger.error(f"File read error: {str(e)}", exc_info=True)
                return
    
    # Process the file (common for both paths)
    if df is not None:
        # Preview
        st.success(f"📊 Loaded {len(df)} rows")
        
        with st.expander("👁️ Preview Data"):
            st.dataframe(df, use_container_width=True)
        
        # Validate required columns
        required_cols = ['Category', 'Question', 'Required']
        missing = [col for col in required_cols if col not in df.columns]
        
        if missing:
            st.error(f"❌ Missing required columns: {', '.join(missing)}")
            st.info(f"Found columns: {', '.join(df.columns)}")
            return
        
        # Import button
        col1, col2 = st.columns([2, 1])
        
        with col1:
            if st.button("🚀 Import & Replace All Questions", type="primary", use_container_width=True):
                count = import_from_excel(df)
                if count > 0:
                    st.success(f"✅ Imported {count} questions successfully!")
                    st.rerun()
                else:
                    st.error("❌ Import failed")
        
        with col2:
            st.warning("⚠️ Replaces ALL existing questions")


def render_edit_tab():
    """Edit questions in-app."""
    
    st.header("Edit Questions")
    
    questions = load_questions()
    
    if not questions:
        st.info("📝 No questions yet. Upload Excel to get started.")
        return
    
    # Group by category
    categories = {}
    for q in questions:
        cat = q.get('category', 'Uncategorized')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(q)
    
    # Filter by category
    all_cats = ['All Categories'] + sorted(categories.keys())
    selected_cat = st.selectbox("Filter by category:", all_cats)
    
    # Show questions
    questions_to_show = questions if selected_cat == 'All Categories' else categories.get(selected_cat, [])
    
    st.markdown(f"**Showing {len(questions_to_show)} questions**")
    st.markdown("---")
    
    # Add new question form
    with st.expander("➕ Add New Question"):
        with st.form("add_question_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_cat = st.text_input("Category*", placeholder="e.g., Payroll")
                new_question = st.text_area("Question*", placeholder="What is...")
                new_required = st.selectbox("Required*", ["Yes", "No"])
            
            with col2:
                new_format = st.text_input("Expected Format", placeholder="e.g., Weekly, Bi-weekly")
                new_keywords = st.text_input("Keywords", placeholder="comma, separated")
                new_notes = st.text_area("Notes", placeholder="Additional context")
            
            if st.form_submit_button("💾 Save Question", use_container_width=True):
                if new_cat and new_question:
                    new_q = {
                        'id': f"Q{len(questions) + 1:04d}",
                        'category': new_cat.strip(),
                        'question': new_question.strip(),
                        'required': new_required == "Yes",
                        'expected_format': new_format.strip(),
                        'keywords': new_keywords.strip(),
                        'notes': new_notes.strip(),
                        'created_at': datetime.now().isoformat()
                    }
                    questions.append(new_q)
                    save_questions(questions)
                    st.success("✅ Question added!")
                    st.rerun()
                else:
                    st.error("❌ Category and Question are required")
    
    # Display existing questions
    for i, q in enumerate(questions_to_show):
        with st.expander(f"**{q.get('category', 'N/A')}** - {q.get('question', 'N/A')[:80]}..."):
            
            # Display current values
            col1, col2 = st.columns(2)
            
            with col1:
                st.text_input("ID", value=q.get('id', ''), disabled=True, key=f"id_{i}")
                st.text_input("Category", value=q.get('category', ''), key=f"cat_{i}")
                st.text_area("Question", value=q.get('question', ''), key=f"q_{i}")
            
            with col2:
                st.selectbox("Required", ["Yes", "No"], 
                           index=0 if q.get('required') else 1, 
                           key=f"req_{i}")
                st.text_input("Expected Format", value=q.get('expected_format', ''), key=f"fmt_{i}")
                st.text_input("Keywords", value=q.get('keywords', ''), key=f"kw_{i}")
            
            st.text_area("Notes", value=q.get('notes', ''), key=f"notes_{i}")
            
            # Action buttons
            btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 2])
            
            with btn_col1:
                if st.button("✏️ Edit", key=f"edit_{i}"):
                    st.info("Edit mode - update values above, then click Save Changes")
            
            with btn_col2:
                if st.button("🗑️ Delete", key=f"del_{i}", type="secondary"):
                    questions = [x for x in questions if x.get('id') != q.get('id')]
                    save_questions(questions)
                    st.success("✅ Deleted!")
                    st.rerun()


def render_export_tab():
    """Export questions to Excel or JSON."""
    
    st.header("Export Questions")
    
    questions = load_questions()
    
    if not questions:
        st.info("📝 No questions to export. Upload or add questions first.")
        return
    
    st.success(f"📊 {len(questions)} questions available for export")
    
    # Export as Excel
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📥 Export as Excel")
        
        if st.button("Download Excel", use_container_width=True):
            df = pd.DataFrame(questions)
            
            # Reorder columns
            cols = ['id', 'category', 'question', 'required', 'expected_format', 'keywords', 'notes']
            df = df[[c for c in cols if c in df.columns]]
            
            # Create buffer
            buffer = BytesIO()
            df.to_excel(buffer, index=False, engine='openpyxl')
            buffer.seek(0)
            
            st.download_button(
                label="⬇️ Download Excel File",
                data=buffer.getvalue(),
                file_name=f"analysis_questions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
    
    with col2:
        st.subheader("📥 Export as JSON")
        
        if st.button("Download JSON", use_container_width=True):
            json_str = json.dumps(questions, indent=2)
            
            st.download_button(
                label="⬇️ Download JSON File",
                data=json_str,
                file_name=f"analysis_questions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True
            )


# Helper functions

def create_template() -> pd.DataFrame:
    """Create sample template for download."""
    return pd.DataFrame({
        'Category': ['Payroll', 'Payroll', 'Benefits'],
        'Question': [
            'What is the pay frequency?',
            'What are the standard pay codes?',
            'What health insurance plans are offered?'
        ],
        'Required': ['Yes', 'Yes', 'No'],
        'Expected_Format': [
            'Weekly, Bi-weekly, Semi-monthly, Monthly',
            'List of pay code names',
            'List of plan names and types'
        ],
        'Keywords': [
            'pay period, frequency, schedule',
            'earnings, pay types, regular, overtime',
            'medical, health, insurance, plans'
        ],
        'Notes': [
            'Critical for payroll setup',
            'Needed for earnings configuration',
            'For benefits module setup'
        ]
    })


def load_questions() -> List[Dict]:
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


def save_questions(questions: List[Dict]) -> bool:
    """Save questions to JSON file."""
    try:
        # Ensure directory exists
        QUESTIONS_DB.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'version': '1.0',
            'updated_at': datetime.now().isoformat(),
            'questions': questions
        }
        
        with open(QUESTIONS_DB, 'w') as f:
            json.dump(data, f, indent=2)
        
        return True
    except Exception as e:
        logger.error(f"Error saving questions: {str(e)}")
        st.error(f"Failed to save: {str(e)}")
        return False


def import_from_excel(df: pd.DataFrame) -> int:
    """Import questions from dataframe."""
    questions = []
    
    for idx, row in df.iterrows():
        q = {
            'id': f"Q{idx + 1:04d}",
            'category': str(row.get('Category', '')).strip(),
            'question': str(row.get('Question', '')).strip(),
            'required': str(row.get('Required', 'No')).strip().lower() in ['yes', 'true', '1'],
            'expected_format': str(row.get('Expected_Format', '')).strip(),
            'keywords': str(row.get('Keywords', '')).strip(),
            'notes': str(row.get('Notes', '')).strip(),
            'created_at': datetime.now().isoformat()
        }
        
        if q['category'] and q['question']:
            questions.append(q)
    
    if save_questions(questions):
        return len(questions)
    return 0
