"""
Analysis & Templates Page - XLR8 Analysis Engine
Main interface for automated UKG analysis question answering


ROBUST VERSION: Won't fail if questions_database.json is missing
"""

import streamlit as st
import pandas as pd
import json
from pathlib import Path
import logging
from typing import List, Dict, Any
import os

logger = logging.getLogger(__name__)


def find_questions_database() -> Path:
    """
    Find questions_database.json by checking multiple possible locations.
    Returns Path object or None if not found.
    """
    # Try multiple possible locations
    possible_paths = [
        Path(__file__).parent.parent.parent / "data" / "questions_database.json",  # Root/data/
        Path(__file__).parent / "questions_database.json",  # Same directory as this file
        Path.cwd() / "data" / "questions_database.json",  # Current working directory
        Path("/app/data/questions_database.json"),  # Railway absolute path
    ]
    
    for path in possible_paths:
        if path.exists():
            logger.info(f"Found questions database at: {path}")
            return path
    
    logger.warning("Questions database not found in any expected location")
    return None


def load_questions() -> Dict[str, Any]:
    """
    Load questions database from JSON file.
    Returns empty structure if file not found (graceful degradation).
    """
    try:
        db_path = find_questions_database()
        
        if db_path is None:
            logger.warning("Questions database not found")
            return {
                'metadata': {
                    'total_questions': 0,
                    'error': 'questions_database.json not found'
                },
                'questions': []
            }
        
        with open(db_path, 'r') as f:
            data = json.load(f)
            logger.info(f"Loaded {data['metadata']['total_questions']} questions")
            return data
            
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return {
            'metadata': {
                'total_questions': 0,
                'error': f'Invalid JSON: {str(e)}'
            },
            'questions': []
        }
    except Exception as e:
        logger.error(f"Error loading questions: {e}")
        return {
            'metadata': {
                'total_questions': 0,
                'error': str(e)
            },
            'questions': []
        }


def render_analysis_page():
    """Main analysis page render function."""
    
    st.title("📊 UKG Analysis Engine")
    st.markdown("""
    <div style='color: #6B7280; font-size: 0.9rem; margin-bottom: 1.5rem;'>
    Automated analysis question answering using RAG-powered document intelligence.
    </div>
    """, unsafe_allow_html=True)
    
    # Load questions
    questions_data = load_questions()
    questions = questions_data.get('questions', [])
    total_questions = questions_data.get('metadata', {}).get('total_questions', 0)
    error = questions_data.get('metadata', {}).get('error')
    
    # Show error if questions failed to load
    if error:
        st.error(f"⚠️ Error loading questions database: {error}")
        st.info("**Troubleshooting:**")
        st.code("""
# Expected file location:
data/questions_database.json

# File should be at root of your repository:
your-repo/
├── app.py
├── data/
│   └── questions_database.json  ← Here!
├── pages/
│   └── work/
│       └── analysis.py
        """)
        
        # Show debug info
        with st.expander("🔍 Debug Information"):
            st.write("**Current working directory:**", os.getcwd())
            st.write("**This file location:**", __file__)
            st.write("**Checked paths:**")
            for path in [
                Path(__file__).parent.parent.parent / "data" / "questions_database.json",
                Path.cwd() / "data" / "questions_database.json",
            ]:
                exists = "✅" if path.exists() else "❌"
                st.write(f"{exists} {path}")
        
        return
    
    if total_questions == 0:
        st.warning("⚠️ No questions loaded yet.")
        st.info("""
        **To set up the Analysis Engine:**
        
        1. Download `questions_database.json` from your conversation history
        2. Create `data/` folder at root of your GitHub repo
        3. Place `questions_database.json` inside it
        4. Push to GitHub
        5. Railway will redeploy automatically
        """)
        return
    
    # SUCCESS - Questions loaded!
    st.success(f"✅ Loaded {total_questions} analysis questions")
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs([
        "📋 Question Browser",
        "⚡ Batch Analysis",
        "📤 Export & Review"
    ])
    
    # TAB 1: QUESTION BROWSER
    with tab1:
        render_question_browser(questions)
    
    # TAB 2: BATCH ANALYSIS
    with tab2:
        render_batch_analysis(questions)
    
    # TAB 3: EXPORT & REVIEW
    with tab3:
        render_export_review(questions)


def render_question_browser(questions: List[Dict[str, Any]]):
    """Render the question browser interface."""
    
    st.subheader("📋 Question Browser")
    
    # Get unique categories
    categories = sorted(list(set(q['category'] for q in questions)))
    
    # Filters
    col1, col2, col3 = st.columns([2, 2, 2])
    
    with col1:
        selected_category = st.selectbox(
            "Filter by Category",
            ["All Categories"] + categories,
            key="question_browser_category"
        )
    
    with col2:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All Status", "Pending", "Analyzed", "Reviewed"],
            key="question_browser_status"
        )
    
    with col3:
        required_filter = st.selectbox(
            "Required Only?",
            ["All Questions", "Required Only", "Optional Only"],
            key="question_browser_required"
        )
    
    # Apply filters
    filtered_questions = questions
    
    if selected_category != "All Categories":
        filtered_questions = [q for q in filtered_questions if q['category'] == selected_category]
    
    if status_filter != "All Status":
        filtered_questions = [q for q in filtered_questions if q['status'] == status_filter.lower()]
    
    if required_filter == "Required Only":
        filtered_questions = [q for q in filtered_questions if q.get('required', False)]
    elif required_filter == "Optional Only":
        filtered_questions = [q for q in filtered_questions if not q.get('required', False)]
    
    # Display count
    st.metric("Questions Matching Filters", len(filtered_questions))
    
    # Display questions as expandable cards
    st.markdown("---")
    
    if not filtered_questions:
        st.info("No questions match the current filters.")
        return
    
    for q in filtered_questions:
        with st.expander(f"**{q['id']}** - {q['question'][:80]}{'...' if len(q['question']) > 80 else ''}", expanded=False):
            # Question details
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**Category:** {q['category']}")
                if q.get('section'):
                    st.markdown(f"**Section:** {q['section']}")
                st.markdown(f"**Required:** {'✅ Yes' if q.get('required') else '❌ No'}")
            
            with col2:
                status_color = {
                    'pending': '🟡',
                    'analyzed': '🔵',
                    'reviewed': '🟢'
                }.get(q.get('status', 'pending'), '⚪')
                st.markdown(f"**Status:** {status_color} {q.get('status', 'pending').capitalize()}")
            
            st.markdown("---")
            st.markdown(f"**Question:**  \n{q['question']}")
            
            if q.get('reason'):
                st.markdown(f"**Why we ask this:**  \n{q['reason']}")
            
            if q.get('answer'):
                st.success(f"**Answer:**  \n{q['answer']}")
                
                if q.get('sources'):
                    st.markdown("**Sources:**")
                    for source in q['sources'][:3]:
                        st.caption(f"📄 {source}")
                
                if q.get('confidence'):
                    confidence = q['confidence']
                    confidence_color = "🟢" if confidence > 0.8 else "🟡" if confidence > 0.6 else "🔴"
                    st.markdown(f"**Confidence:** {confidence_color} {confidence*100:.0f}%")
            else:
                st.info("Not yet analyzed")
            
            # Action buttons
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("🔍 Analyze This Question", key=f"analyze_{q['id']}"):
                    st.info("✨ Analysis feature coming next! (Within the hour)")
            with col2:
                if st.button("✏️ Edit Answer", key=f"edit_{q['id']}"):
                    st.info("Edit feature coming soon!")
            with col3:
                if st.button("✅ Mark Reviewed", key=f"review_{q['id']}"):
                    st.info("Review tracking coming soon!")


def render_batch_analysis(questions: List[Dict[str, Any]]):
    """Render the batch analysis interface."""
    
    st.subheader("⚡ Batch Analysis")
    
    st.info("🚧 **Coming Within the Hour:** Automated batch analysis of all questions!")
    
    # Show what's coming
    st.markdown("""
    ### Features in Development:
    
    **🎯 Smart Analysis:**
    - Query all customer documents via RAG
    - Extract answers using local LLM (PII-safe)
    - Calculate confidence scores
    - Detect conflicts across sources
    
    **📊 Progress Tracking:**
    - Real-time progress bar
    - Batch processing (10 questions at a time)
    - Pause/Resume capability
    - Estimated time remaining
    
    **💾 Checkpoint System:**
    - Auto-save every 10 questions
    - Resume from last checkpoint
    - Never lose progress
    """)
    
    # Placeholder UI
    st.markdown("---")
    st.markdown("### Preview: Batch Analysis Interface")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Questions", len(questions))
    with col2:
        st.metric("Analyzed", 0)
    with col3:
        st.metric("Remaining", len(questions))
    
    st.progress(0.0, text="Ready to analyze...")
    
    if st.button("🚀 Start Batch Analysis", type="primary", disabled=True):
        st.info("Coming within the hour!")


def render_export_review(questions: List[Dict[str, Any]]):
    """Render the export and review interface."""
    
    st.subheader("📤 Export & Review")
    
    st.info("🚧 **Coming Within the Hour:** Export completed analysis to Excel!")
    
    # Show what's coming
    st.markdown("""
    ### Features in Development:
    
    **📊 Excel Export:**
    - Export to Analysis_Workbook format
    - All answers populated in "HCMPACT Notes" column
    - Confidence color coding (Green/Yellow/Red)
    - Source citations included
    
    **🔍 Review Workflow:**
    - Filter by confidence level
    - Bulk approve high-confidence answers
    - Flag low-confidence for manual review
    - Resolve conflicts
    
    **✅ Quality Control:**
    - Validation checks
    - Required fields verification
    - Conflict resolution interface
    """)
    
    # Placeholder metrics
    st.markdown("---")
    st.markdown("### Analysis Summary (Preview)")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("High Confidence", "0", help=">80%")
    with col2:
        st.metric("Medium Confidence", "0", help="60-80%")
    with col3:
        st.metric("Low Confidence", "0", help="<60%")
    with col4:
        st.metric("Conflicts", "0", help="Multiple conflicting answers")
    
    st.markdown("---")
    
    if st.button("📥 Export to Excel", type="primary", disabled=True):
        st.info("Coming within the hour!")


# Entry point
if __name__ == "__main__":
    render_analysis_page()
