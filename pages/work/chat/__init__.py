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
            max_value=20,
            value=st.session_state.get('num_chromadb_sources', 12),
            help="Number of HCMPACT documents to use for context"
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
            num_sources = st.session_state.get('num_chromadb_sources', 8)
            decision = router.make_routing_decision(user_query, num_sources)
            
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


# Entry point
if __name__ == "__main__":
    render_chat_page()
