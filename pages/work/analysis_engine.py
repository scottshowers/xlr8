"""
UKG Analysis Engine - V3 with Batch Analysis Fix
Fixes: Correct pending count, always show buttons, re-analyze option
"""

import streamlit as st
import json
from pathlib import Path
import logging
from typing import List, Dict, Any
import os
import sys
import time
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Print to logs
print("=" * 80)
print("🚀 ANALYSIS_ENGINE.PY LOADING - V3 BATCH ANALYSIS FIX - BUILD 2345")
print("=" * 80)


def load_questions():
    """Load questions from JSON file."""
    questions_file = Path("/data/analysis_questions.json")
    
    if not questions_file.exists():
        logger.warning(f"Questions file not found: {questions_file}")
        return {"version": "1.0", "questions": []}
    
    try:
        with open(questions_file, 'r') as f:
            data = json.load(f)
            
        # Handle both formats
        if isinstance(data, dict) and 'questions' in data:
            logger.info(f"Loaded {len(data['questions'])} questions (new format)")
            return data
        elif isinstance(data, list):
            logger.info(f"Loaded {len(data)} questions (legacy format)")
            return {"version": "1.0", "questions": data}
        else:
            logger.error(f"Unknown format in {questions_file}")
            return {"version": "1.0", "questions": []}
            
    except Exception as e:
        logger.error(f"Error loading questions: {e}")
        return {"version": "1.0", "questions": []}


def save_questions(questions_data: Dict[str, Any]):
    """Save questions to JSON file."""
    questions_file = Path("/data/analysis_questions.json")
    
    try:
        questions_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(questions_file, 'w') as f:
            json.dump(questions_data, f, indent=2)
        
        logger.info(f"Saved {len(questions_data.get('questions', []))} questions")
        return True
        
    except Exception as e:
        logger.error(f"Error saving questions: {e}")
        st.error(f"Failed to save questions: {e}")
        return False


def render_question_browser(questions: List[Dict[str, Any]], rag_handler=None):
    """Render the question browser interface."""
    
    st.subheader("📋 Question Browser")
    
    if not questions:
        st.warning("⚠️ No questions loaded. Go to Admin → Analysis Questions to import questions.")
        return
    
    # Summary metrics
    total = len(questions)
    analyzed = len([q for q in questions if q.get('answer')])
    pending = total - analyzed
    required = len([q for q in questions if q.get('required', True)])
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Questions", total)
    with col2:
        st.metric("Analyzed", analyzed, delta=f"{analyzed/total*100:.0f}%" if total > 0 else "0%")
    with col3:
        st.metric("Pending", pending)
    with col4:
        st.metric("Required", required)
    
    st.markdown("---")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        categories = sorted(list(set(q.get('category', 'Uncategorized') for q in questions)))
        category_filter = st.selectbox("Category", ["All"] + categories)
    
    with col2:
        status_filter = st.selectbox("Status", ["All", "Pending", "Analyzed", "Reviewed"])
    
    with col3:
        required_filter = st.selectbox("Required", ["All", "Required Only", "Optional Only"])
    
    # Apply filters
    filtered = questions.copy()
    
    if category_filter != "All":
        filtered = [q for q in filtered if q.get('category') == category_filter]
    
    if status_filter == "Pending":
        filtered = [q for q in filtered if not q.get('answer')]
    elif status_filter == "Analyzed":
        filtered = [q for q in filtered if q.get('answer') and q.get('status') in ['analyzed', 'reviewed']]
    elif status_filter == "Reviewed":
        filtered = [q for q in filtered if q.get('status') == 'reviewed']
    
    if required_filter == "Required Only":
        filtered = [q for q in filtered if q.get('required', True)]
    elif required_filter == "Optional Only":
        filtered = [q for q in filtered if not q.get('required', True)]
    
    st.caption(f"Showing {len(filtered)} of {total} questions")
    
    # Pagination
    questions_per_page = 10
    total_pages = (len(filtered) + questions_per_page - 1) // questions_per_page
    
    if total_pages > 1:
        page = st.number_input("Page", min_value=1, max_value=total_pages, value=1) - 1
    else:
        page = 0
    
    start_idx = page * questions_per_page
    end_idx = min(start_idx + questions_per_page, len(filtered))
    page_questions = filtered[start_idx:end_idx]
    
    # Display questions
    for idx, question in enumerate(page_questions, start=start_idx + 1):
        with st.expander(f"Q{idx}: {question.get('question', 'No question text')[:80]}..."):
            
            # Question details
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**Question:** {question.get('question', 'N/A')}")
                st.caption(f"Category: {question.get('category', 'Uncategorized')} | Required: {'Yes' if question.get('required', True) else 'No'}")
            
            with col2:
                if question.get('answer'):
                    confidence = question.get('confidence', 0)
                    st.metric("Confidence", f"{confidence*100:.0f}%")
            
            # Answer section
            if question.get('answer'):
                st.markdown("**Answer:**")
                st.info(question['answer'])
                
                # Sources
                if question.get('sources'):
                    with st.expander("📚 Sources"):
                        for i, source in enumerate(question['sources'], 1):
                            st.caption(f"{i}. {source.get('source', 'Unknown')} (score: {source.get('score', 0):.2f})")
                
                # Status controls
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"✓ Mark Reviewed", key=f"review_{idx}"):
                        question['status'] = 'reviewed'
                        st.success("Marked as reviewed")
                        st.rerun()
                
                with col2:
                    if st.button(f"🔄 Re-analyze", key=f"reanalyze_{idx}"):
                        if rag_handler:
                            with st.spinner("Re-analyzing..."):
                                # Re-run analysis
                                result = analyze_single_question(question, rag_handler)
                                if result:
                                    question.update(result)
                                    st.success("Re-analyzed!")
                                    st.rerun()
                        else:
                            st.error("RAG system not available")
            
            else:
                st.warning("⏳ Not yet analyzed")
                
                if rag_handler and st.button(f"🔍 Analyze This Question", key=f"analyze_{idx}"):
                    with st.spinner("Analyzing..."):
                        result = analyze_single_question(question, rag_handler)
                        if result:
                            question.update(result)
                            st.success("Analysis complete!")
                            st.rerun()


def analyze_single_question(question: Dict[str, Any], rag_handler) -> Dict[str, Any]:
    """Analyze a single question using RAG."""
    
    try:
        # Query RAG system
        query = question.get('question', '')
        num_sources = 8
        
        logger.info(f"Analyzing question: {query[:50]}...")
        
        # Get relevant sources from RAG
        results = rag_handler.hybrid_search(
            query=query,
            num_results=num_sources
        )
        
        if not results:
            logger.warning("No sources found")
            return {
                'answer': "No relevant information found in knowledge base.",
                'confidence': 0.0,
                'sources': [],
                'status': 'analyzed',
                'analyzed_at': datetime.now().isoformat()
            }
        
        # Try to use LLM synthesizer if available
        try:
            from utils.ai.llm_synthesizer import synthesize_answer
            
            answer_data = synthesize_answer(
                question=query,
                sources=results,
                llm_endpoint=os.getenv('LLM_ENDPOINT', 'http://localhost:11434'),
                llm_username=os.getenv('LLM_USERNAME', ''),
                llm_password=os.getenv('LLM_PASSWORD', '')
            )
            
            return {
                'answer': answer_data['answer'],
                'confidence': answer_data['confidence'],
                'sources': [{'source': r.get('source', 'Unknown'), 'score': r.get('score', 0)} for r in results],
                'status': 'analyzed',
                'analyzed_at': datetime.now().isoformat()
            }
            
        except ImportError:
            logger.warning("LLM synthesizer not available, using fallback")
            # Fallback: concatenate top sources
            answer = "\n\n".join([r.get('text', '')[:300] for r in results[:3]])
            
            return {
                'answer': answer,
                'confidence': 0.6,
                'sources': [{'source': r.get('source', 'Unknown'), 'score': r.get('score', 0)} for r in results],
                'status': 'analyzed',
                'analyzed_at': datetime.now().isoformat()
            }
    
    except Exception as e:
        logger.error(f"Error analyzing question: {e}")
        return {
            'answer': f"Error during analysis: {str(e)}",
            'confidence': 0.0,
            'sources': [],
            'status': 'error',
            'analyzed_at': datetime.now().isoformat()
        }


def render_batch_analysis(questions: List[Dict[str, Any]], questions_data: Dict[str, Any], rag_handler=None):
    """Render the batch analysis interface - FIXED VERSION."""
    
    st.subheader("⚡ Batch Analysis")
    
    if not rag_handler:
        st.error("⚠️ RAG system not available. Cannot perform batch analysis.")
        st.info("👉 Make sure documents are uploaded in Setup → HCMPACT LLM Seeding")
        return
    
    # Calculate stats - FIXED: count questions WITHOUT answers as pending
    # Not just status='pending', because imported questions don't have status field
    pending = [q for q in questions if not q.get('answer') or q.get('status') == 'pending']
    analyzed = [q for q in questions if q.get('answer') and q.get('status') in ['analyzed', 'reviewed']]
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Questions", len(questions))
    with col2:
        st.metric("Analyzed", len(analyzed), delta=f"{len(analyzed)/len(questions)*100:.0f}%" if questions else "0%")
    with col3:
        st.metric("Pending", len(pending))
    with col4:
        avg_conf = sum(q.get('confidence', 0) for q in analyzed) / len(analyzed) if analyzed else 0
        st.metric("Avg Confidence", f"{avg_conf*100:.0f}%")
    
    st.markdown("---")
    
    # FIXED: Don't hide buttons, just show appropriate message
    show_batch_controls = True
    questions_to_process = pending
    
    if len(pending) == 0:
        st.success("✅ All questions have been analyzed!")
        st.info("👉 Go to Export & Review tab to download results")
        
        # Option to re-analyze all
        if st.checkbox("🔄 Re-analyze all questions?"):
            st.warning("⚠️ This will overwrite existing answers")
            questions_to_process = questions
            show_batch_controls = True
        else:
            show_batch_controls = False
    
    if not show_batch_controls:
        return
    
    # Batch processing controls
    st.markdown("### 🚀 Batch Processing")
    
    # Options
    col1, col2 = st.columns(2)
    with col1:
        batch_size = st.selectbox(
            "Batch Size",
            [5, 10, 20, 50, 100],
            index=1,
            help="Process this many questions before auto-saving"
        )
    
    with col2:
        process_mode = st.selectbox(
            "Process",
            ["All Pending", "By Category", "Required Only"],
            help="Choose which questions to process"
        )
    
    # Filter questions based on mode
    if process_mode == "By Category":
        available_questions = questions_to_process if len(pending) > 0 else questions
        categories = sorted(list(set(q.get('category', 'Uncategorized') for q in available_questions)))
        
        if not categories:
            st.warning("No categories found")
            return
        
        selected_category = st.selectbox("Select Category", categories)
        questions_to_process = [q for q in questions_to_process if q.get('category') == selected_category]
    
    elif process_mode == "Required Only":
        questions_to_process = [q for q in questions_to_process if q.get('required', True)]
    
    # Show what will be processed
    if len(questions_to_process) == 0:
        st.warning("⚠️ No questions match the selected filters")
        return
    
    st.info(f"📊 **{len(questions_to_process)} questions** will be processed")
    
    # Estimate time
    time_per_question = 12  # seconds (with LLM synthesis)
    estimated_seconds = len(questions_to_process) * time_per_question
    
    if estimated_seconds > 3600:
        estimated_time = f"~{estimated_seconds/3600:.1f} hours"
    elif estimated_seconds > 60:
        estimated_time = f"~{estimated_seconds/60:.0f} minutes"
    else:
        estimated_time = f"~{estimated_seconds:.0f} seconds"
    
    st.caption(f"⏱️ Estimated time: {estimated_time}")
    
    # Action buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🚀 Start Batch Analysis", type="primary", disabled=len(questions_to_process)==0):
            st.session_state.batch_processing = True
            st.session_state.batch_questions = questions_to_process
            st.session_state.batch_size = batch_size
            st.rerun()
    
    with col2:
        if st.button("🛑 Clear Queue", disabled=len(pending)==0):
            # Clear all pending status
            for q in questions:
                if q.get('status') == 'pending':
                    q['status'] = 'cleared'
            save_questions(questions_data)
            st.success("Queue cleared!")
            st.rerun()
    
    # Process if triggered
    if st.session_state.get('batch_processing'):
        run_batch_analysis(
            questions_to_process=st.session_state.batch_questions,
            questions_data=questions_data,
            rag_handler=rag_handler,
            batch_size=st.session_state.batch_size
        )


def run_batch_analysis(questions_to_process: List[Dict[str, Any]], 
                       questions_data: Dict[str, Any],
                       rag_handler,
                       batch_size: int):
    """Run batch analysis on questions."""
    
    total = len(questions_to_process)
    
    # Progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Metrics
    col1, col2, col3 = st.columns(3)
    processed_metric = col1.empty()
    success_metric = col2.empty()
    failed_metric = col3.empty()
    
    # Process questions
    processed = 0
    success = 0
    failed = 0
    
    start_time = time.time()
    
    for idx, question in enumerate(questions_to_process):
        # Update status
        status_text.text(f"Processing question {idx+1}/{total}: {question.get('question', '')[:60]}...")
        
        # Analyze question
        result = analyze_single_question(question, rag_handler)
        
        if result and result.get('answer'):
            question.update(result)
            success += 1
        else:
            failed += 1
        
        processed += 1
        
        # Update progress
        progress = processed / total
        progress_bar.progress(progress)
        processed_metric.metric("Processed", f"{processed}/{total}")
        success_metric.metric("Success", success)
        failed_metric.metric("Failed", failed)
        
        # Auto-save every N questions
        if processed % batch_size == 0:
            status_text.text(f"💾 Auto-saving progress... ({processed}/{total})")
            save_questions(questions_data)
    
    # Final save
    status_text.text("💾 Saving final results...")
    save_questions(questions_data)
    
    # Clear batch processing flag
    st.session_state.batch_processing = False
    
    # Show completion summary
    elapsed_time = time.time() - start_time
    
    st.success(f"✅ Batch analysis complete!")
    st.info(f"""
    **Summary:**
    - Total processed: {processed}
    - Successful: {success}
    - Failed: {failed}
    - Time elapsed: {elapsed_time/60:.1f} minutes
    - Average per question: {elapsed_time/processed:.1f} seconds
    """)
    
    # Offer to continue
    if st.button("🔄 Run Another Batch"):
        st.rerun()


def render_export_review(questions: List[Dict[str, Any]]):
    """Render the export and review interface."""
    
    st.subheader("📤 Export & Review")
    
    # Show summary of analyzed questions
    analyzed = [q for q in questions if q.get('answer')]
    pending = [q for q in questions if not q.get('answer')]
    
    if not analyzed:
        st.warning("⚠️ No analyzed questions to export yet.")
        st.info("👉 Go to Question Browser or Batch Analysis to analyze questions first")
        return
    
    st.success(f"✅ {len(analyzed)} questions have been analyzed and are ready for export!")
    
    # Confidence breakdown
    high_conf = sum(1 for q in analyzed if q.get('confidence', 0) > 0.8)
    med_conf = sum(1 for q in analyzed if 0.6 < q.get('confidence', 0) <= 0.8)
    low_conf = sum(1 for q in analyzed if q.get('confidence', 0) <= 0.6)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("High Confidence", high_conf, help=">80%")
    with col2:
        st.metric("Medium Confidence", med_conf, help="60-80%")
    with col3:
        st.metric("Low Confidence", low_conf, help="<60%")
    
    st.markdown("---")
    
    # Export options
    st.markdown("### 📥 Export Options")
    
    export_format = st.radio(
        "Format",
        ["Excel (.xlsx)", "JSON (.json)", "CSV (.csv)"],
        horizontal=True
    )
    
    include_sources = st.checkbox("Include source citations", value=True)
    include_confidence = st.checkbox("Include confidence scores", value=True)
    
    # Export button
    if st.button("📥 Export Analyzed Questions", type="primary"):
        
        if export_format == "Excel (.xlsx)":
            try:
                import pandas as pd
                from io import BytesIO
                
                # Prepare data for Excel
                export_data = []
                for q in analyzed:
                    row = {
                        'Category': q.get('category', 'Uncategorized'),
                        'Question': q.get('question', ''),
                        'Answer': q.get('answer', ''),
                        'Required': 'Yes' if q.get('required', True) else 'No',
                        'Status': q.get('status', 'analyzed')
                    }
                    
                    if include_confidence:
                        row['Confidence'] = f"{q.get('confidence', 0)*100:.0f}%"
                    
                    if include_sources and q.get('sources'):
                        sources_text = "; ".join([s.get('source', 'Unknown') for s in q.get('sources', [])])
                        row['Sources'] = sources_text
                    
                    export_data.append(row)
                
                # Create DataFrame
                df = pd.DataFrame(export_data)
                
                # Create Excel file in memory
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='Analysis Results', index=False)
                
                output.seek(0)
                
                # Download button
                st.download_button(
                    label="⬇️ Download Excel File",
                    data=output,
                    file_name=f"analysis_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
                st.success("✅ Excel file ready for download!")
                
            except Exception as e:
                st.error(f"Error creating Excel export: {e}")
        
        elif export_format == "JSON (.json)":
            import json
            
            # Prepare JSON export
            export_data = {
                'exported_at': datetime.now().isoformat(),
                'total_questions': len(analyzed),
                'questions': analyzed
            }
            
            json_str = json.dumps(export_data, indent=2)
            
            st.download_button(
                label="⬇️ Download JSON File",
                data=json_str,
                file_name=f"analysis_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
            
            st.success("✅ JSON file ready for download!")
        
        elif export_format == "CSV (.csv)":
            import pandas as pd
            
            # Prepare CSV export
            export_data = []
            for q in analyzed:
                row = {
                    'Category': q.get('category', 'Uncategorized'),
                    'Question': q.get('question', ''),
                    'Answer': q.get('answer', ''),
                    'Required': 'Yes' if q.get('required', True) else 'No',
                    'Status': q.get('status', 'analyzed')
                }
                
                if include_confidence:
                    row['Confidence'] = f"{q.get('confidence', 0)*100:.0f}%"
                
                if include_sources and q.get('sources'):
                    sources_text = "; ".join([s.get('source', 'Unknown') for s in q.get('sources', [])])
                    row['Sources'] = sources_text
                
                export_data.append(row)
            
            df = pd.DataFrame(export_data)
            csv = df.to_csv(index=False)
            
            st.download_button(
                label="⬇️ Download CSV File",
                data=csv,
                file_name=f"analysis_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            
            st.success("✅ CSV file ready for download!")
    
    st.markdown("---")
    
    # Review low confidence answers
    if low_conf > 0:
        st.markdown("### ⚠️ Review Low Confidence Answers")
        
        low_conf_questions = [q for q in analyzed if q.get('confidence', 0) <= 0.6]
        
        for idx, question in enumerate(low_conf_questions, 1):
            with st.expander(f"{idx}. {question.get('question', '')[:60]}... (Confidence: {question.get('confidence', 0)*100:.0f}%)"):
                st.markdown(f"**Question:** {question.get('question', '')}")
                st.markdown(f"**Answer:** {question.get('answer', '')}")
                
                if question.get('sources'):
                    st.caption("**Sources:**")
                    for s in question.get('sources', []):
                        st.caption(f"- {s.get('source', 'Unknown')}")
                
                if st.button(f"✓ Approve", key=f"approve_{idx}"):
                    question['status'] = 'reviewed'
                    st.success("Approved!")
                    st.rerun()


def render_analysis_page():
    """Main render function for analysis engine page."""
    
    st.title("🎯 UKG Analysis Engine")
    
    # Load questions
    questions_data = load_questions()
    questions = questions_data.get('questions', [])
    
    if not questions:
        st.warning("⚠️ No questions loaded.")
        st.info("👉 Go to **Admin → Analysis Questions** to import questions from Excel")
        return
    
    # Get RAG handler from session state
    rag_handler = st.session_state.get('rag_handler')
    
    # Tabs
    tab1, tab2, tab3 = st.tabs([
        "📋 Question Browser",
        "⚡ Batch Analysis", 
        "📤 Export & Review"
    ])
    
    with tab1:
        render_question_browser(questions, rag_handler)
    
    with tab2:
        render_batch_analysis(questions, questions_data, rag_handler)
    
    with tab3:
        render_export_review(questions)


# Entry point
if __name__ == "__main__":
    print("⚠️ analysis_engine.py running in standalone mode - BUILD 2345 - BATCH FIX")
    render_analysis_page()
