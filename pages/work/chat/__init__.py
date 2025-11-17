"""
Intelligent Chat Page for XLR8

Features:
- Automatic PII detection and protection
- Intelligent model routing (Mistral, DeepSeek, Claude API)
- ChromaDB context enhancement
- Real-time response streaming
- Source attribution
- Professional UX with status indicators

Author: HCMPACT
Version: 1.0
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


def show():
    """Main chat page function"""
    
    st.title("💬 Intelligent Chat Assistant")
    
    # Compact subtitle
    st.markdown("""
    <div style='color: #6B7280; font-size: 0.9rem; margin-bottom: 1.5rem;'>
    AI assistant with automatic PII protection, intelligent model selection, and HCMPACT knowledge enhancement.
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize chat system
    if not _initialize_chat_system():
        return
    
    # Sidebar settings
    _render_sidebar_settings()
    
    # Main chat interface
    _render_chat_interface()


def _initialize_chat_system() -> bool:
    """
    Initialize the intelligent chat system components.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get configuration from session state
        config = st.session_state.get('config', {})
        
        # Ollama endpoint
        ollama_endpoint = st.session_state.get('llm_endpoint', '')
        if not ollama_endpoint:
            st.warning("⚠️ Local LLM endpoint not configured. Please configure in Connectivity tab.")
            return False
        
        # Ollama auth (if configured)
        ollama_auth = None
        llm_username = st.session_state.get('llm_username', '').strip()
        llm_password = st.session_state.get('llm_password', '').strip()
        if llm_username and llm_password:
            ollama_auth = (llm_username, llm_password)
        
        # Claude API key (optional)
        claude_api_key = st.session_state.get('claude_api_key', '').strip()
        
        # ChromaDB handler (if available)
        chromadb_handler = st.session_state.get('rag_handler')
        
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
        
        return True
        
    except Exception as e:
        st.error(f"Error initializing chat system: {e}")
        logger.error(f"Chat initialization error: {e}", exc_info=True)
        return False


def _render_sidebar_settings():
    """Render chat settings in sidebar"""
    
    with st.sidebar:
        st.markdown("### ⚙️ Chat Settings")
        
        # Show/hide settings
        show_metadata = st.checkbox(
            "Show Response Metadata",
            value=st.session_state.get('show_chat_metadata', True),
            help="Display model used, response time, complexity, etc."
        )
        st.session_state.show_chat_metadata = show_metadata
        
        show_sources = st.checkbox(
            "Show Knowledge Sources",
            value=st.session_state.get('show_chat_sources', True),
            help="Display HCMPACT knowledge sources used"
        )
        st.session_state.show_chat_sources = show_sources
        
        show_decision = st.checkbox(
            "Show Routing Decision",
            value=st.session_state.get('show_routing_decision', True),
            help="Display which model was selected and why"
        )
        st.session_state.show_routing_decision = show_decision
        
        # ChromaDB sources
        st.markdown("---")
        num_sources = st.slider(
            "Knowledge Sources to Retrieve",
            min_value=1,
            max_value=10,
            value=st.session_state.get('num_chromadb_sources', 5),
            help="Number of HCMPACT documents to use for context"
        )
        st.session_state.num_chromadb_sources = num_sources
        
        # Clear chat button
        st.markdown("---")
        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()


def _render_chat_interface():
    """Render the main chat interface"""
    
    # Display chat history
    for message in st.session_state.get('chat_history', []):
        _render_message(message)
    
    # Chat input
    user_input = st.chat_input("Ask me anything about UKG implementations...")
    
    if user_input:
        # Add user message to history
        user_message = {
            'role': 'user',
            'content': user_input,
            'timestamp': time.time()
        }
        st.session_state.chat_history.append(user_message)
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(user_input)
        
        # Generate and display assistant response
        _generate_and_display_response(user_input)


def _render_message(message: Dict[str, Any]):
    """
    Render a single chat message.
    
    Args:
        message: Message dict with role, content, and optional metadata
    """
    role = message.get('role', 'assistant')
    content = message.get('content', '')
    
    with st.chat_message(role):
        st.markdown(content)
        
        # Show routing decision if available and enabled
        if (role == 'assistant' and 
            st.session_state.get('show_routing_decision', True) and 
            message.get('routing_decision')):
            
            decision = message['routing_decision']
            st.info(decision)
        
        # Show sources if available and enabled
        if (role == 'assistant' and 
            st.session_state.get('show_chat_sources', True) and 
            message.get('sources')):
            
            with st.expander(f"📚 {len(message['sources'])} Knowledge Sources", expanded=False):
                for source in message['sources']:
                    st.markdown(f"**{source['index']}. {source['document_name']}** ({source['category']})")
                    if source.get('excerpt'):
                        st.caption(source['excerpt'])
                    st.markdown("")
        
        # Show metadata if available and enabled
        if (role == 'assistant' and 
            st.session_state.get('show_chat_metadata', True) and 
            message.get('metadata')):
            
            metadata = message['metadata']
            
            cols = st.columns(4)
            with cols[0]:
                st.metric("Model", metadata.get('model', 'Unknown'))
            with cols[1]:
                st.metric("Time", f"{metadata.get('processing_time', 0):.1f}s")
            with cols[2]:
                st.metric("Complexity", metadata.get('complexity', 'Unknown').capitalize())
            with cols[3]:
                confidence = metadata.get('confidence_level', 'medium')
                emoji = {'high': '🟢', 'medium': '🟡', 'low': '🟠'}.get(confidence, '⚪')
                st.metric("Confidence", f"{emoji} {confidence.capitalize()}")


def _generate_and_display_response(user_query: str):
    """
    Generate and display assistant response.
    
    Args:
        user_query: User's query text
    """
    start_time = time.time()
    
    with st.chat_message("assistant"):
        # Create placeholders for progressive display
        status_placeholder = st.empty()
        response_placeholder = st.empty()
        
        try:
            # Get router and other components
            router = st.session_state.intelligent_router
            llm_caller = st.session_state.llm_caller
            synthesizer = st.session_state.response_synthesizer
            
            # STEP 1: Make routing decision
            status_placeholder.info("🧠 Analyzing query and selecting best model...")
            
            num_sources = st.session_state.get('num_chromadb_sources', 5)
            decision = router.make_routing_decision(user_query, num_sources)
            
            # Show decision if enabled
            if st.session_state.get('show_routing_decision', True):
                decision_text = router.get_decision_explanation(decision)
                status_placeholder.info(decision_text)
            else:
                status_placeholder.info("🤖 Generating response...")
            
            # STEP 2: Determine the query to send (anonymized if PII detected)
            query_to_send = decision.anonymized_query if decision.anonymized_query else user_query
            
            # STEP 3: Build enhanced prompt with ChromaDB context if available
            if decision.chromadb_context:
                enhanced_prompt = synthesizer.build_enhanced_prompt(
                    user_query=query_to_send,
                    chromadb_context=decision.chromadb_context,
                    system_context="You are an expert UKG implementation consultant from HCMPACT."
                )
            else:
                enhanced_prompt = query_to_send
            
            # STEP 4: Call appropriate LLM
            if decision.use_local_llm:
                # Local Ollama call
                llm_response = llm_caller.call_ollama(
                    prompt=enhanced_prompt,
                    model=decision.model_name,
                    system_prompt="You are an expert UKG implementation consultant from HCMPACT. Provide accurate, helpful answers.",
                    temperature=0.7,
                    max_tokens=4096
                )
                response_text = llm_response['response']
            else:
                # Claude API call
                llm_response = llm_caller.call_claude_api(
                    prompt=enhanced_prompt,
                    system_prompt="You are an expert UKG implementation consultant from HCMPACT. Provide accurate, helpful answers.",
                    max_tokens=4096,
                    temperature=0.7
                )
                response_text = llm_response['response']
            
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
            status_placeholder.empty()
            response_placeholder.markdown(synthesized.text)
            
            # Save to chat history
            assistant_message = {
                'role': 'assistant',
                'content': synthesized.text,
                'timestamp': time.time(),
                'routing_decision': router.get_decision_explanation(decision) if st.session_state.get('show_routing_decision', True) else None,
                'sources': synthesized.sources if st.session_state.get('show_chat_sources', True) else None,
                'metadata': {
                    'model': synthesized.model_used,
                    'processing_time': synthesized.processing_time,
                    'complexity': synthesized.complexity,
                    'confidence_level': synthesized.confidence_level,
                    'pii_protected': synthesized.has_pii_protection
                } if st.session_state.get('show_chat_metadata', True) else None
            }
            
            st.session_state.chat_history.append(assistant_message)
            
        except Exception as e:
            status_placeholder.empty()
            response_placeholder.error(f"Error generating response: {str(e)}")
            logger.error(f"Response generation error: {e}", exc_info=True)
            
            # Save error to history
            error_message = {
                'role': 'assistant',
                'content': f"I apologize, but I encountered an error: {str(e)}",
                'timestamp': time.time(),
                'error': True
            }
            st.session_state.chat_history.append(error_message)


# Entry point
if __name__ == "__main__":
    show()
