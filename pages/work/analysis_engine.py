"""
Analysis & Templates Page - XLR8 Analysis Engine
COMPLETE VERSION - Question Browser + RAG Analysis
BUILD 20251118-2315
"""

import streamlit as st
import json
from pathlib import Path
import logging
from typing import List, Dict, Any
import os
import sys

# Import RAG handler for document querying
try:
    from utils.rag_handler import RAGHandler
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    st.error("RAG Handler not available")

logger = logging.getLogger(__name__)

# Print to logs
print("=" * 80)
print("🚀 ANALYSIS_ENGINE.PY LOADING - COMPLETE VERSION - BUILD 2315")
print("=" * 80)


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
    
    logger.warning("Questions database not found")
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


def save_questions(questions_data: Dict[str, Any]) -> bool:
    """Save updated questions back to JSON file."""
    try:
        db_path = find_questions_database()
        if db_path is None:
            logger.error("Cannot save - database path not found")
            return False
        
        with open(db_path, 'w') as f:
            json.dump(questions_data, f, indent=2)
        
        logger.info("Questions database saved successfully")
        return True
    except Exception as e:
        logger.error(f"Error saving questions: {e}")
        return False


def analyze_single_question(question: Dict[str, Any], rag_handler: RAGHandler) -> Dict[str, Any]:
    """
    Analyze a single question using RAG to query customer documents.
    
    Args:
        question: Question dictionary with 'question', 'keywords', etc.
        rag_handler: RAG handler instance for querying documents
    
    Returns:
        Dictionary with 'answer', 'sources', 'confidence', 'status'
    """
    try:
        # Build search query from question and keywords
        query_text = question['question']
        
        # Add keywords to enhance search
        if question.get('keywords'):
            query_text += " " + " ".join(question['keywords'][:5])
        
        logger.info(f"Analyzing question {question['id']}: {question['question'][:50]}...")
        
        # Get the collection
        collection = rag_handler.client.get_collection(name="hcmpact_docs")
        
        # Generate embedding for query
        query_embedding = rag_handler.get_embedding(query_text)
        
        if query_embedding is None:
            return {
                'answer': 'Error: Could not generate embedding for query.',
                'sources': [],
                'confidence': 0.0,
                'status': 'pending'
            }
        
        # Query collection directly
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=5,
            include=['documents', 'metadatas', 'distances']
        )
        
        if not results or not results.get('documents'):
            return {
                'answer': 'No relevant information found in uploaded documents.',
                'sources': [],
                'confidence': 0.0,
                'status': 'analyzed'
            }
        
        # Extract documents and metadata
        documents = results['documents'][0] if results['documents'] else []
        metadatas = results['metadatas'][0] if results.get('metadatas') else []
        distances = results['distances'][0] if results.get('distances') else []
        
        if not documents:
            return {
                'answer': 'No relevant information found.',
                'sources': [],
                'confidence': 0.0,
                'status': 'analyzed'
            }
        
        # Calculate confidence based on distances (lower distance = higher confidence)
        # ChromaDB uses cosine distance, so 0 = perfect match, 2 = opposite
        if distances:
            avg_distance = sum(distances) / len(distances)
            confidence = max(0.0, min(1.0, 1.0 - (avg_distance / 2.0)))
        else:
            confidence = 0.5
        
        # Filter out template documents (optional - improves quality)
        filtered_results = []
        for doc, meta, dist in zip(documents, metadatas, distances):
            source = meta.get('source', '')
            # Skip template documents
            if 'Analysis_Workbook' not in source and 'BRIT' not in source:
                filtered_results.append((doc, meta, dist))
        
        # If we filtered out everything, use original results
        if not filtered_results:
            filtered_results = list(zip(documents, metadatas, distances))
        
        # Build answer from top chunks
        answer_parts = []
        sources = []
        
        for i, (doc, meta, dist) in enumerate(filtered_results[:3]):
            # Extract source information
            source_name = meta.get('source', 'Unknown')
            if source_name not in sources:
                sources.append(source_name)
            
            # Add chunk content to answer
            chunk_text = doc.strip()
            if chunk_text and len(chunk_text) > 20:
                answer_parts.append(f"**From {source_name}:**\n{chunk_text[:300]}...")
        
        # Combine answer parts
        if answer_parts:
            answer = "\n\n".join(answer_parts)
        else:
            answer = "Information found but could not extract meaningful content."
        
        return {
            'answer': answer,
            'sources': sources,
            'confidence': confidence,
            'status': 'analyzed'
        }
        
    except Exception as e:
        logger.error(f"Error analyzing question: {e}", exc_info=True)
        return {
            'answer': f'Error during analysis: {str(e)}',
            'sources': [],
            'confidence': 0.0,
            'status': 'pending'
        }


def render_analysis_page():
    """Main analysis page render function."""
    
    st.title("📊 UKG Analysis Engine")
    st.markdown("""
    <div style='color: #6B7280; font-size: 0.9rem; margin-bottom: 1.5rem;'>
    Automated analysis question answering using RAG-powered document intelligence.
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize RAG handler
    rag_handler = None
    if RAG_AVAILABLE:
        try:
            rag_handler = RAGHandler()
            # Test connection
            count = rag_handler.get_collection_count("hcmpact_docs")
            st.success(f"✅ Connected to RAG system: {count:,} chunks available")
        except Exception as e:
            st.error(f"⚠️ RAG system error: {e}")
            rag_handler = None
    
    # Load questions
    questions_data = load_questions()
    questions = questions_data.get('questions', [])
    total_questions = questions_data.get('metadata', {}).get('total_questions', 0)
    error = questions_data.get('metadata', {}).get('error')
    
    # Show error if questions failed to load
    if error:
        st.error(f"⚠️ Error loading questions database: {error}")
        st.info("**File should be at:** `data/questions_database.json` (root of repo)")
        return
    
    if total_questions == 0:
        st.warning("⚠️ No questions loaded yet.")
        return
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs([
        "📋 Question Browser",
        "⚡ Batch Analysis",
        "📤 Export & Review"
    ])
    
    # TAB 1: QUESTION BROWSER
    with tab1:
        render_question_browser(questions, questions_data, rag_handler)
    
    # TAB 2: BATCH ANALYSIS
    with tab2:
        render_batch_analysis(questions, questions_data, rag_handler)
    
    # TAB 3: EXPORT & REVIEW
    with tab3:
        render_export_review(questions)


def render_question_browser(questions: List[Dict[str, Any]], questions_data: Dict[str, Any], rag_handler):
    """Render the question browser interface with analysis capability."""
    
    st.subheader("📋 Question Browser")
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    analyzed_count = sum(1 for q in questions if q.get('status') == 'analyzed')
    pending_count = sum(1 for q in questions if q.get('status') == 'pending')
    required_count = sum(1 for q in questions if q.get('required'))
    
    with col1:
        st.metric("Total Questions", len(questions))
    with col2:
        st.metric("Analyzed", analyzed_count, delta=f"{analyzed_count/len(questions)*100:.0f}%")
    with col3:
        st.metric("Pending", pending_count)
    with col4:
        st.metric("Required", required_count)
    
    st.markdown("---")
    
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
    
    # Pagination
    questions_per_page = 10
    total_pages = max(1, (len(filtered_questions) + questions_per_page - 1) // questions_per_page)
    
    # Use unique key to avoid conflicts with other parts of the app
    page_key = 'analysis_questions_page'
    
    # Initialize or validate current page
    if page_key not in st.session_state:
        st.session_state[page_key] = 0
    
    # Ensure current_page is valid integer within range
    try:
        current_page = int(st.session_state[page_key])
        if current_page >= total_pages or current_page < 0:
            current_page = 0
            st.session_state[page_key] = 0
    except (ValueError, TypeError):
        current_page = 0
        st.session_state[page_key] = 0
    
    # Page controls
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        page = st.selectbox(
            f"Page (showing {questions_per_page} per page)",
            options=list(range(total_pages)),
            index=current_page,
            format_func=lambda x: f"Page {x+1} of {total_pages}",
            key="analysis_page_selector"
        )
        st.session_state[page_key] = int(page)
    
    # Get questions for current page
    start_idx = page * questions_per_page
    end_idx = start_idx + questions_per_page
    page_questions = filtered_questions[start_idx:end_idx]
    
    # Display questions
    for q in page_questions:
        with st.expander(
            f"**{q['id']}** - {q['question'][:80]}{'...' if len(q['question']) > 80 else ''}", 
            expanded=False
        ):
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
            
            # Show existing answer if available
            if q.get('answer'):
                st.success(f"**Answer:**  \n{q['answer']}")
                
                if q.get('sources'):
                    st.markdown("**Sources:**")
                    for source in q['sources']:
                        st.caption(f"📄 {source}")
                
                if q.get('confidence'):
                    confidence = q['confidence']
                    confidence_color = "🟢" if confidence > 0.8 else "🟡" if confidence > 0.6 else "🔴"
                    st.markdown(f"**Confidence:** {confidence_color} {confidence*100:.0f}%")
            
            # Action buttons
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if rag_handler and st.button("🔍 Analyze This Question", key=f"analyze_{q['id']}"):
                    with st.spinner("Analyzing..."):
                        # Analyze the question
                        result = analyze_single_question(q, rag_handler)
                        
                        # Update question with results
                        q['answer'] = result['answer']
                        q['sources'] = result['sources']
                        q['confidence'] = result['confidence']
                        q['status'] = result['status']
                        
                        # Save updated questions
                        if save_questions(questions_data):
                            st.success("✅ Analysis complete!")
                            st.rerun()
                        else:
                            st.error("⚠️ Could not save results")
            
            with col2:
                if q.get('answer') and st.button("✏️ Edit Answer", key=f"edit_{q['id']}"):
                    st.info("💡 Edit feature: Open the answer in a text area for manual editing (coming soon)")
            
            with col3:
                if q.get('answer') and st.button("✅ Mark Reviewed", key=f"review_{q['id']}"):
                    q['status'] = 'reviewed'
                    if save_questions(questions_data):
                        st.success("✅ Marked as reviewed!")
                        st.rerun()


def render_batch_analysis(questions: List[Dict[str, Any]], questions_data: Dict[str, Any], rag_handler):
    """Render the batch analysis interface."""
    
    st.subheader("⚡ Batch Analysis")
    
    if not rag_handler:
        st.error("⚠️ RAG system not available. Cannot perform batch analysis.")
        return
    
    st.info("🚧 **Batch analysis coming in next conversation!**")
    
    st.markdown("""
    ### Batch Analysis Features:
    
    **🎯 What it will do:**
    - Analyze ALL 254 questions automatically
    - Process in batches of 10 (to avoid timeout)
    - Real-time progress bar
    - Auto-save every 10 questions
    - Estimated time: ~30-45 minutes for all questions
    
    **💾 Smart Features:**
    - Skip already-analyzed questions
    - Resume from last checkpoint
    - Pause/resume capability
    - Never lose progress
    
    **🔍 Quality Control:**
    - Confidence scores for each answer
    - Flag low-confidence answers for review
    - Detect conflicting information
    - Source citation tracking
    """)
    
    # Show stats
    pending = sum(1 for q in questions if q.get('status') == 'pending')
    st.metric("Pending Questions", pending, help="Questions not yet analyzed")
    
    if pending > 0:
        st.info(f"💡 You can analyze all {pending} pending questions manually one by one for now, or wait for batch analysis in the next conversation.")


def render_export_review(questions: List[Dict[str, Any]]):
    """Render the export and review interface."""
    
    st.subheader("📤 Export & Review")
    
    st.info("🚧 **Export feature coming in next conversation!**")
    
    # Show summary of analyzed questions
    analyzed = [q for q in questions if q.get('answer')]
    
    if not analyzed:
        st.warning("No analyzed questions to export yet.")
        return
    
    st.success(f"✅ {len(analyzed)} questions have been analyzed!")
    
    # Confidence breakdown
    high_conf = sum(1 for q in analyzed if q.get('confidence', 0) > 0.8)
    med_conf = sum(1 for q in analyzed if 0.6 < q.get('confidence', 0) <= 0.8)
    low_conf = sum(1 for q in analyzed if q.get('confidence', 0) <= 0.6)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("High Confidence", high_conf, help=">80%", delta="✅")
    with col2:
        st.metric("Medium Confidence", med_conf, help="60-80%", delta="⚠️")
    with col3:
        st.metric("Low Confidence", low_conf, help="<60%", delta="⚠️")
    
    st.markdown("---")
    st.markdown("### Coming Features:")
    st.markdown("""
    - **Excel Export:** Export to Analysis_Workbook.xlsx format with answers populated
    - **Confidence Color Coding:** Green/Yellow/Red based on confidence
    - **Source Citations:** Include all sources in export
    - **Review Workflow:** Filter and review low-confidence answers
    - **Bulk Operations:** Approve multiple answers at once
    """)


# Entry point
if __name__ == "__main__":
    print("⚠️ analysis_engine.py running in standalone mode - BUILD 2315")
    render_analysis_page()
