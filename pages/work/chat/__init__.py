"""
Intelligent Chat Page for XLR8

Features:
- Automatic PII detection and protection
- Intelligent model routing (Mistral, DeepSeek, Claude API)
- ChromaDB context enhancement with detailed citations
- Chat input at bottom, conversation flows above
- Detailed source attribution

Author: HCMPACT
Version: 1.1
"""

import streamlit as st
import time
import logging
from typing import Dict, Any, Optional

# Import our intelligent chat system
from utils.ai.intelligent_router import IntelligentRouter, RouterDecision
from utils.ai.llm_caller import LLMCaller
from utils.ai.response_synthesizer import ResponseSynthesizer
from utils.ai.pii_handler import PIIHandler

logger = logging.getLogger(__name__)


def render_chat_page():
    """Main chat page function"""
    
    st.title(" Intelligent Chat Assistant")
    
    # Compact subtitle
    st.markdown("""
    <div style='color: #6B7280; font-size: 0.9rem; margin-bottom: 1.5rem;'>
    AI assistant with automatic PII protection, intelligent model selection, and HCMPACT knowledge enhancement.
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize chat system
    init_result = _initialize_chat_system()
    if not init_result['success']:
        st.error(init_result['message'])
        return
    
    # Show configuration status
    if init_result.get('warnings'):
        for warning in init_result['warnings']:
            st.warning(warning)
    
    # Sidebar settings
    _render_sidebar_settings()
    
    # Main chat interface
    _render_chat_interface()


def _initialize_chat_system() -> Dict[str, Any]:
    """
    Initialize the intelligent chat system components.
    
    Returns:
        Dict with success, message, and warnings
    """
    try:
        warnings = []
        
        # Get configuration from session state
        config = st.session_state.get('config', {})
        
        # Ollama endpoint
        ollama_endpoint = st.session_state.get('llm_endpoint', '')
        if not ollama_endpoint:
            return {
                'success': False,
                'message': " Local LLM endpoint not configured. Please configure in Connectivity tab."
            }
        
        # Ollama auth (if configured)
        ollama_auth = None
        llm_username = st.session_state.get('llm_username', '').strip()
        llm_password = st.session_state.get('llm_password', '').strip()
        if llm_username and llm_password:
            ollama_auth = (llm_username, llm_password)
        
        # Claude API key (optional but recommended)
        claude_api_key = st.session_state.get('claude_api_key', '').strip()
        if not claude_api_key:
            warnings.append(" Claude API key not configured - all queries will use local LLM. Add API key in Connectivity tab for faster general knowledge responses.")
        
        # ChromaDB handler (if available)
        chromadb_handler = st.session_state.get('rag_handler')
        if not chromadb_handler:
            warnings.append(" ChromaDB not initialized - responses won't include HCMPACT knowledge. Upload documents in Knowledge tab.")
        
        # Initialize components if not already done
        if 'intelligent_router' not in st.session_state:
            st.session_state.intelligent_router = IntelligentRouter(
                ollama_endpoint=ollama_endpoint,
                ollama_auth=ollama_auth,
                claude_api_key=claude_api_key,
                chromadb_handler=chromadb_handler
            )
        
        if 'llm_caller' not in st.session_state:
            st.session_state.llm_caller = LLMCaller(
                ollama_endpoint=ollama_endpoint,
                ollama_auth=ollama_auth,
                claude_api_key=claude_api_key
            )
        
        if 'response_synthesizer' not in st.session_state:
            st.session_state.response_synthesizer = ResponseSynthesizer()
        
        # Initialize chat history
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        
        return {
            'success': True,
            'message': 'Chat system initialized',
            'warnings': warnings
        }
        
    except Exception as e:
        logger.error(f"Chat initialization error: {e}", exc_info=True)
        return {
            'success': False,
            'message': f"Error initializing chat system: {e}"
        }


def _render_sidebar_settings():
    """Render chat settings in sidebar"""
    
    with st.sidebar:
        st.markdown("###  Chat Settings")
        
        # Debug mode
        debug_mode = st.checkbox(
            " Debug Mode",
            value=st.session_state.get('chat_debug_mode', False),
            help="Show routing decisions and system info"
        )
        st.session_state.chat_debug_mode = debug_mode
        
        st.markdown("---")
        
        # Show/hide settings
        show_sources = st.checkbox(
            " Show Knowledge Sources",
            value=st.session_state.get('show_chat_sources', True),
            help="Display HCMPACT knowledge sources used (inline with response)"
        )
        st.session_state.show_chat_sources = show_sources
        
        show_metadata = st.checkbox(
            " Show Response Metadata",
            value=st.session_state.get('show_chat_metadata', True),
            help="Display model used, response time, complexity, etc."
        )
        st.session_state.show_chat_metadata = show_metadata
        
        # ChromaDB sources
        st.markdown("---")
        num_sources = st.slider(
            "Knowledge Sources to Retrieve",
            min_value=1,
            max_value=150,
            value=st.session_state.get('num_chromadb_sources', 50),
            help="Number of HCMPACT documents to use for context (increase for large multi-sheet files)"
        )
        st.session_state.num_chromadb_sources = num_sources
        
        # Clear chat button
        st.markdown("---")
        if st.button(" Clear Chat History", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()


def _render_chat_interface():
    """Render the main chat interface"""
    
    # Container for chat messages (scrollable)
    chat_container = st.container()
    
    with chat_container:
        # Display chat history
        for message in st.session_state.get('chat_history', []):
            _render_message(message)
    
    # ACTION BUTTONS AND PROMPT LIBRARY (above chat input)
    st.markdown("---")
    
    # Row 1: Action Buttons
    col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
    
    with col1:
        if st.button("🗑️ Clear Chat & Memory", type="secondary", use_container_width=True):
            st.session_state.chat_history = []
            # Clear any cached data
            if 'intelligent_router' in st.session_state:
                st.session_state.intelligent_router = None
            st.success("✅ Chat cleared!")
            st.rerun()
    
    with col2:
        if st.button("💾 Save Current Prompt", type="secondary", use_container_width=True):
            _show_save_prompt_dialog()
    
    with col3:
        if st.button("📋 Load Saved Prompt", type="secondary", use_container_width=True):
            _show_load_prompt_dialog()
    
    with col4:
        if st.button("📊 Export to Excel", type="secondary", use_container_width=True):
            _export_chat_to_excel()
    
    # Row 2: Prompt Library (if managing prompts)
    if st.session_state.get('show_prompt_manager', False):
        _render_prompt_manager()
    
    # Row 3: Loaded prompt preview (if available)
    if st.session_state.get('loaded_prompt'):
        st.info("📋 Prompt loaded from library - modify below or press Enter to send:")
        user_input_area = st.text_area(
            "Edit prompt before sending:",
            value=st.session_state.loaded_prompt,
            height=100,
            key="prompt_editor"
        )
        if st.button("📤 Send Prompt", type="primary", use_container_width=True):
            user_input = user_input_area
            st.session_state.loaded_prompt = None  # Clear after use
        else:
            user_input = None
    else:
        # Chat input at bottom (always visible)
        user_input = st.chat_input("Ask me anything about UKG implementations...")
    
    if user_input:
        # Add user message to history
        user_message = {
            'role': 'user',
            'content': user_input,
            'timestamp': time.time()
        }
        st.session_state.chat_history.append(user_message)
        
        # Generate and display assistant response
        with chat_container:
            # Display user message
            with st.chat_message("user"):
                st.markdown(user_input)
            
            # Generate response
            _generate_and_display_response(user_input)
        
        # Rerun to update the display
        st.rerun()


def _render_message(message: Dict[str, Any]):
    """
    Render a single chat message.
    
    Args:
        message: Message dict with role, content, and optional metadata
    """
    role = message.get('role', 'assistant')
    content = message.get('content', '')
    
    with st.chat_message(role):
        # Main response
        st.markdown(content)
        
        # Show inline citations if available
        if (role == 'assistant' and 
            st.session_state.get('show_chat_sources', True) and 
            message.get('sources')):
            
            st.markdown("---")
            st.markdown("** Sources:**")
            
            for source in message['sources']:
                # Detailed source citation
                source_text = f"**[{source['index']}]** {source['document_name']}"
                
                if source.get('category'):
                    source_text += f" *({source['category']})*"
                
                if source.get('relevance_score'):
                    score = 1.0 - source['relevance_score']
                    if score >= 0.8:
                        relevance = " Highly Relevant"
                    elif score >= 0.6:
                        relevance = " Relevant"
                    else:
                        relevance = " Somewhat Relevant"
                    source_text += f" - {relevance} ({score:.0%})"
                
                st.markdown(source_text)
                
                # Show excerpt
                if source.get('excerpt'):
                    st.caption(f" *{source['excerpt']}*")
                
                # Show metadata if available
                if source.get('metadata'):
                    metadata = source['metadata']
                    details = []
                    if metadata.get('page'):
                        details.append(f"Page {metadata['page']}")
                    if metadata.get('section'):
                        details.append(f"Section: {metadata['section']}")
                    if metadata.get('file_path'):
                        details.append(f"File: {metadata['file_path'].split('/')[-1]}")
                    
                    if details:
                        st.caption(f" {' | '.join(details)}")
                
                st.markdown("")
        
        # Show debug info if enabled
        if (role == 'assistant' and 
            st.session_state.get('chat_debug_mode', False) and 
            message.get('debug_info')):
            
            with st.expander(" Debug Information", expanded=False):
                debug = message['debug_info']
                st.json(debug)
        
        # Show metadata if available and enabled
        if (role == 'assistant' and 
            st.session_state.get('show_chat_metadata', True) and 
            message.get('metadata')):
            
            st.markdown("---")
            metadata = message['metadata']
            
            cols = st.columns(5)
            with cols[0]:
                st.metric("Model", metadata.get('model_display', 'Unknown'))
            with cols[1]:
                st.metric("Time", f"{metadata.get('processing_time', 0):.1f}s")
            with cols[2]:
                complexity = metadata.get('complexity', 'Unknown').capitalize()
                st.metric("Complexity", complexity)
            with cols[3]:
                confidence = metadata.get('confidence_level', 'medium')
                emoji = {'high': '', 'medium': '', 'low': ''}.get(confidence, '')
                st.metric("Confidence", f"{emoji} {confidence.capitalize()}")
            with cols[4]:
                routing = metadata.get('routing_type', 'Unknown')
                st.metric("Route", routing)


def _generate_and_display_response(user_query: str):
    """
    Generate and display assistant response.
    
    Args:
        user_query: User's query text
    """
    start_time = time.time()
    
    with st.chat_message("assistant"):
        # Create placeholder for response
        response_placeholder = st.empty()
        
        try:
            # Get router and other components
            router = st.session_state.intelligent_router
            llm_caller = st.session_state.llm_caller
            synthesizer = st.session_state.response_synthesizer
            
            # Show initial status
            with response_placeholder.container():
                st.info(" Analyzing query and selecting best approach...")
            
            # STEP 1: Make routing decision
            num_sources = st.session_state.get('num_chromadb_sources', 50)
            
            # Get current project for document filtering
            current_project = st.session_state.get('current_project')
            
            # Make routing decision with project filter
            decision = router.make_routing_decision(user_query, num_sources, project_id=current_project)
            
            # Debug info
            debug_info = {
                'routing_decision': {
                    'use_local_llm': decision.use_local_llm,
                    'model': decision.model_name,
                    'reason': decision.reason,
                    'has_pii': decision.has_pii,
                    'complexity': decision.complexity,
                    'chromadb_sources': len(decision.chromadb_context) if decision.chromadb_context else 0
                }
            }
            
            # Show routing decision
            if st.session_state.get('chat_debug_mode', False):
                with response_placeholder.container():
                    decision_text = router.get_decision_explanation(decision)
                    st.info(f"**Routing Decision:** {decision_text}")
                    st.caption(f"Reason: {decision.reason}")
            
            # STEP 2: Determine the query to send (anonymized if PII detected)
            query_to_send = decision.anonymized_query if decision.anonymized_query else user_query
            
            # STEP 3: Build enhanced prompt with ChromaDB context if available
            with response_placeholder.container():
                if decision.chromadb_context:
                    st.info(f" Found {len(decision.chromadb_context)} relevant knowledge sources. Building enhanced prompt...")
                else:
                    st.info(" Generating response...")
            
            if decision.chromadb_context:
                enhanced_prompt = synthesizer.build_enhanced_prompt(
                    user_query=query_to_send,
                    chromadb_context=decision.chromadb_context,
                    system_context="You are an expert UKG implementation consultant from HCMPACT. Use the provided knowledge sources to give accurate, detailed answers. Always cite which sources you're referencing."
                )
            else:
                enhanced_prompt = query_to_send
            
            # STEP 4: Call appropriate LLM
            if decision.use_local_llm:
                # Local Ollama call
                with response_placeholder.container():
                    model_display = decision.model_name.replace(":7b", "").replace(":latest", "")
                    st.info(f" Using {model_display}...")
                
                llm_response = llm_caller.call_ollama(
                    prompt=enhanced_prompt,
                    model=decision.model_name,
                    system_prompt="You are an expert UKG implementation consultant from HCMPACT. Provide accurate, helpful answers. When using provided knowledge sources, cite them specifically (e.g., 'According to the UKG Pro Configuration Guide...').",
                    temperature=0.7,
                    max_tokens=4096
                )
                response_text = llm_response['response']
                routing_type = "Local LLM"
            else:
                # Claude API call
                with response_placeholder.container():
                    st.info(f" Using Claude API...")
                
                llm_response = llm_caller.call_claude_api(
                    prompt=enhanced_prompt,
                    system_prompt="You are an expert UKG implementation consultant from HCMPACT. Provide accurate, helpful answers.",
                    max_tokens=4096,
                    temperature=0.7
                )
                response_text = llm_response['response']
                routing_type = "Claude API"
            
            # STEP 5: Process response (de-anonymize if needed)
            final_response = router.process_response(response_text, decision)
            
            # STEP 6: Synthesize final response with metadata
            processing_time = time.time() - start_time
            
            synthesized = synthesizer.synthesize(
                llm_response=final_response,
                chromadb_context=decision.chromadb_context,
                model_used=decision.model_name,
                has_pii_protection=decision.has_pii,
                complexity=decision.complexity,
                processing_time=processing_time
            )
            
            # Clear status and show final response
            response_placeholder.markdown(synthesized.text)
            
            # Prepare model display name
            model_display = decision.model_name.replace(":7b", "").replace(":latest", "").replace("-", " ").title()
            
            # Save to chat history
            assistant_message = {
                'role': 'assistant',
                'content': synthesized.text,
                'timestamp': time.time(),
                'sources': synthesized.sources,
                'metadata': {
                    'model': decision.model_name,
                    'model_display': model_display,
                    'processing_time': synthesized.processing_time,
                    'complexity': synthesized.complexity,
                    'confidence_level': synthesized.confidence_level,
                    'pii_protected': synthesized.has_pii_protection,
                    'routing_type': routing_type
                },
                'debug_info': debug_info if st.session_state.get('chat_debug_mode', False) else None
            }
            
            st.session_state.chat_history.append(assistant_message)
            
        except Exception as e:
            response_placeholder.error(f" Error generating response: {str(e)}")
            logger.error(f"Response generation error: {e}", exc_info=True)
            
            # Save error to history
            error_message = {
                'role': 'assistant',
                'content': f"I apologize, but I encountered an error while processing your request:\n\n```\n{str(e)}\n```\n\nPlease try rephrasing your question or contact support if the issue persists.",
                'timestamp': time.time(),
                'error': True
            }
            st.session_state.chat_history.append(error_message)


# ============================================================================
# PROMPT LIBRARY FUNCTIONS
# ============================================================================

def _initialize_prompt_library():
    """Initialize prompt library in session state"""
    if 'saved_prompts' not in st.session_state:
        st.session_state.saved_prompts = {}
    if 'show_prompt_manager' not in st.session_state:
        st.session_state.show_prompt_manager = False


def _show_save_prompt_dialog():
    """Show dialog to save current prompt"""
    _initialize_prompt_library()
    
    # Get the last user message
    user_messages = [msg for msg in st.session_state.chat_history if msg['role'] == 'user']
    if not user_messages:
        st.warning("No prompts to save. Ask a question first!")
        return
    
    last_prompt = user_messages[-1]['content']
    
    # Show save dialog
    with st.form("save_prompt_form"):
        st.subheader("💾 Save Prompt")
        prompt_name = st.text_input("Prompt Name", placeholder="e.g., 'OBBB Tax Impact Analysis'")
        prompt_category = st.selectbox("Category", ["General", "Tax", "Configuration", "Implementation", "Custom"])
        prompt_text = st.text_area("Prompt Text", value=last_prompt, height=150)
        
        col1, col2 = st.columns(2)
        with col1:
            save_btn = st.form_submit_button("💾 Save", type="primary", use_container_width=True)
        with col2:
            cancel_btn = st.form_submit_button("❌ Cancel", use_container_width=True)
        
        if save_btn and prompt_name:
            st.session_state.saved_prompts[prompt_name] = {
                'text': prompt_text,
                'category': prompt_category,
                'created': time.time()
            }
            st.success(f"✅ Saved prompt: {prompt_name}")
            st.rerun()


def _show_load_prompt_dialog():
    """Show dialog to load saved prompt"""
    _initialize_prompt_library()
    
    if not st.session_state.saved_prompts:
        st.info("📋 No saved prompts yet. Save a prompt first using the '💾 Save Current Prompt' button.")
        return
    
    st.session_state.show_prompt_manager = True
    st.rerun()


def _render_prompt_manager():
    """Render the prompt library manager"""
    _initialize_prompt_library()
    
    st.markdown("### 📚 Prompt Library")
    
    if not st.session_state.saved_prompts:
        st.info("No saved prompts yet.")
        if st.button("❌ Close"):
            st.session_state.show_prompt_manager = False
            st.rerun()
        return
    
    # Group prompts by category
    prompts_by_category = {}
    for name, data in st.session_state.saved_prompts.items():
        category = data.get('category', 'General')
        if category not in prompts_by_category:
            prompts_by_category[category] = []
        prompts_by_category[category].append((name, data))
    
    # Display prompts by category
    for category, prompts in prompts_by_category.items():
        st.markdown(f"**{category}**")
        
        for name, data in prompts:
            col1, col2, col3, col4 = st.columns([4, 1, 1, 1])
            
            with col1:
                st.write(f"📝 {name}")
            
            with col2:
                if st.button("📋 Use", key=f"use_{name}"):
                    st.session_state.loaded_prompt = data['text']
                    st.session_state.show_prompt_manager = False
                    st.rerun()
            
            with col3:
                if st.button("✏️ Edit", key=f"edit_{name}"):
                    _show_edit_prompt_dialog(name, data)
            
            with col4:
                if st.button("🗑️", key=f"delete_{name}"):
                    del st.session_state.saved_prompts[name]
                    st.success(f"Deleted: {name}")
                    st.rerun()
            
            # Show preview
            with st.expander("Preview", expanded=False):
                st.text(data['text'][:200] + "..." if len(data['text']) > 200 else data['text'])
    
    st.markdown("---")
    if st.button("❌ Close Prompt Library", use_container_width=True):
        st.session_state.show_prompt_manager = False
        st.rerun()


def _show_edit_prompt_dialog(name, data):
    """Show dialog to edit a saved prompt"""
    with st.form(f"edit_prompt_{name}"):
        st.subheader(f"✏️ Edit: {name}")
        
        new_name = st.text_input("Prompt Name", value=name)
        new_category = st.selectbox("Category", 
                                    ["General", "Tax", "Configuration", "Implementation", "Custom"],
                                    index=["General", "Tax", "Configuration", "Implementation", "Custom"].index(data.get('category', 'General')))
        new_text = st.text_area("Prompt Text", value=data['text'], height=150)
        
        col1, col2 = st.columns(2)
        with col1:
            save_btn = st.form_submit_button("💾 Save Changes", type="primary", use_container_width=True)
        with col2:
            cancel_btn = st.form_submit_button("❌ Cancel", use_container_width=True)
        
        if save_btn:
            # Delete old if name changed
            if new_name != name:
                del st.session_state.saved_prompts[name]
            
            # Save updated prompt
            st.session_state.saved_prompts[new_name] = {
                'text': new_text,
                'category': new_category,
                'created': data.get('created', time.time())
            }
            st.success(f"✅ Updated: {new_name}")
            st.rerun()


# ============================================================================
# EXPORT FUNCTIONS
# ============================================================================

def _export_chat_to_excel():
    """Export chat history to Excel file"""
    import pandas as pd
    from io import BytesIO
    from datetime import datetime
    
    if not st.session_state.get('chat_history'):
        st.warning("No chat history to export!")
        return
    
    # Prepare data for export
    export_data = []
    
    for idx, message in enumerate(st.session_state.chat_history, 1):
        role = message.get('role', 'unknown')
        content = message.get('content', '')
        timestamp = message.get('timestamp', time.time())
        
        # Format timestamp
        dt = datetime.fromtimestamp(timestamp)
        
        # Extract metadata if available
        metadata = message.get('metadata', {})
        sources = message.get('sources', [])
        
        # Build source list
        source_list = []
        if sources:
            for source in sources:
                source_name = source.get('document_name', 'Unknown')
                project = source.get('project_id', 'Global')
                relevance = source.get('relevance_score', 0)
                similarity = (1.0 - min(relevance, 1.0)) * 100
                source_list.append(f"{source_name} ({project}) - {similarity:.0f}%")
        
        export_data.append({
            'Index': idx,
            'Role': role.capitalize(),
            'Timestamp': dt.strftime('%Y-%m-%d %H:%M:%S'),
            'Content': content,
            'Model': metadata.get('model_display', ''),
            'Processing Time (s)': metadata.get('processing_time', ''),
            'Complexity': metadata.get('complexity', ''),
            'Confidence': metadata.get('confidence_level', ''),
            'Sources': '\n'.join(source_list) if source_list else ''
        })
    
    # Create DataFrame
    df = pd.DataFrame(export_data)
    
    # Create Excel file in memory
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Chat History', index=False)
        
        # Auto-adjust column widths
        worksheet = writer.sheets['Chat History']
        for idx, col in enumerate(df.columns):
            max_length = max(
                df[col].astype(str).apply(len).max(),
                len(col)
            )
            worksheet.column_dimensions[chr(65 + idx)].width = min(max_length + 2, 50)
    
    output.seek(0)
    
    # Generate filename
    current_project = st.session_state.get('current_project', 'General')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"XLR8_Chat_{current_project}_{timestamp}.xlsx"
    
    # Offer download
    st.download_button(
        label="📥 Download Excel File",
        data=output.getvalue(),
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        use_container_width=True
    )
    
    st.success(f"✅ Excel file ready: {filename}")


# Entry point
if __name__ == "__main__":
    render_chat_page()
