"""
Analysis & Templates Page - XLR8 Analysis Engine
DEPLOYMENT TEST VERSION - BUILD 20251118-2247
IF YOU SEE THIS MESSAGE, NEW CODE IS DEPLOYED!
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
    """Find questions_database.json by checking multiple possible locations."""
    possible_paths = [
        Path(__file__).parent.parent.parent / "data" / "questions_database.json",
        Path(__file__).parent / "questions_database.json",
        Path.cwd() / "data" / "questions_database.json",
        Path("/app/data/questions_database.json"),
    ]
    
    for path in possible_paths:
        if path.exists():
            logger.info(f"Found questions database at: {path}")
            return path
    
    logger.warning("Questions database not found in any expected location")
    return None


def load_questions() -> Dict[str, Any]:
    """Load questions database from JSON file."""
    try:
        db_path = find_questions_database()
        
        if db_path is None:
            return {
                'metadata': {'total_questions': 0, 'error': 'questions_database.json not found'},
                'questions': []
            }
        
        with open(db_path, 'r') as f:
            data = json.load(f)
            logger.info(f"Loaded {data['metadata']['total_questions']} questions")
            return data
            
    except Exception as e:
        logger.error(f"Error loading questions: {e}")
        return {
            'metadata': {'total_questions': 0, 'error': str(e)},
            'questions': []
        }


def render_analysis_page():
    """Main analysis page render function."""
    
    # UNMISTAKABLE MARKER - YOU WILL SEE THIS
    st.markdown("""
    <div style='background: #10b981; color: white; padding: 1rem; border-radius: 8px; margin-bottom: 1rem; text-align: center; font-weight: bold; font-size: 1.2rem;'>
    ✅ NEW CODE DEPLOYED! Build 20251118-2247
    </div>
    """, unsafe_allow_html=True)
    
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
        st.info("**File should be at:** `data/questions_database.json` (root of repo)")
        
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
        
        st.warning("📥 **Download questions_database.json from conversation history and place in data/ folder**")
        return
    
    if total_questions == 0:
        st.warning("⚠️ No questions loaded yet.")
        return
    
    # SUCCESS
    st.success(f"✅ Loaded {total_questions} analysis questions")
    
    # Simple demo for now
    st.markdown("### 🎯 Question Browser Coming Next!")
    st.info("Within the hour, you'll be able to browse and analyze all 254 questions!")
    
    # Show categories
    categories = sorted(list(set(q['category'] for q in questions)))
    st.markdown(f"**Categories available:** {len(categories)}")
    for cat in categories:
        count = sum(1 for q in questions if q['category'] == cat)
        st.write(f"- {cat}: {count} questions")


# Entry point
if __name__ == "__main__":
    render_analysis_page()
