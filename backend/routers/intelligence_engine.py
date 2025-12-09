"""
CHAT INTELLIGENCE INTEGRATION
==============================

This file shows EXACTLY how to integrate the Intelligence Engine into chat.py.
These are the additions/changes needed.

Deploy: Merge these changes into backend/routers/chat.py

Author: XLR8 Team
"""

# =============================================================================
# STEP 1: ADD IMPORTS (at top of chat.py, around line 50)
# =============================================================================

# Add after other imports:
try:
    from utils.intelligence_engine import (
        IntelligenceEngine, 
        IntelligenceMode,
        create_engine,
        SynthesizedAnswer
    )
    INTELLIGENCE_AVAILABLE = True
    logging.getLogger(__name__).info("✅ Intelligence engine loaded")
except ImportError as e:
    INTELLIGENCE_AVAILABLE = False
    logging.getLogger(__name__).warning(f"❌ Intelligence engine NOT available: {e}")


# =============================================================================
# STEP 2: ADD NEW REQUEST MODEL (around line 250)
# =============================================================================

class IntelligentChatRequest(BaseModel):
    """Request for intelligent chat with clarification support."""
    message: str
    project: Optional[str] = None
    persona: Optional[str] = 'bessie'
    scope: Optional[str] = 'project'
    
    # NEW: Intelligence options
    mode: Optional[str] = None  # Force specific mode
    clarifications: Optional[Dict[str, Any]] = None  # Answers to clarification questions
    session_id: Optional[str] = None  # For conversation continuity
    output_format: Optional[str] = None  # Force output format


# =============================================================================
# STEP 3: ADD INTELLIGENCE ENGINE ENDPOINT (new endpoint)
# =============================================================================

# Session storage for conversation continuity
intelligence_sessions: Dict[str, IntelligenceEngine] = {}


@router.post("/chat/intelligent")
async def intelligent_chat(request: IntelligentChatRequest):
    """
    INTELLIGENT CHAT ENDPOINT
    
    This is the REVOLUTIONARY endpoint that:
    1. Analyzes the question
    2. Asks clarifying questions if needed
    3. Gathers from ALL sources (data, docs, UKG knowledge)
    4. Synthesizes a complete answer
    5. Shows conflicts and insights proactively
    
    Returns a structured response that the frontend can display richly.
    """
    if not INTELLIGENCE_AVAILABLE:
        raise HTTPException(503, "Intelligence engine not available")
    
    project = request.project
    message = request.message
    session_id = request.session_id or f"session_{uuid.uuid4().hex[:8]}"
    
    logger.info(f"[INTELLIGENT] Question: {message[:100]}...")
    logger.info(f"[INTELLIGENT] Project: {project}, Session: {session_id}")
    
    try:
        # Get or create intelligence engine for this session
        if session_id in intelligence_sessions:
            engine = intelligence_sessions[session_id]
        else:
            # Create new engine with full context
            engine = IntelligenceEngine(project or 'default')
            
            # Load structured data handler
            if STRUCTURED_QUERIES_AVAILABLE:
                handler = get_structured_handler()
                schema = {'tables': get_duckdb_tables_for_scope(project, request.scope)}
                engine.load_context(
                    structured_handler=handler,
                    schema=schema
                )
            
            # Load RAG handler
            try:
                rag = RAGHandler()
                engine.rag_handler = rag
            except:
                pass
            
            # Load relationships (from data model)
            try:
                from utils.relationship_detector import get_confirmed_relationships
                relationships = get_confirmed_relationships(project)
                engine.relationships = relationships
            except:
                pass
            
            # Store session
            intelligence_sessions[session_id] = engine
            
            # Clean old sessions (keep last 100)
            if len(intelligence_sessions) > 100:
                oldest = list(intelligence_sessions.keys())[0]
                del intelligence_sessions[oldest]
        
        # If user provided clarification answers, add them
        if request.clarifications:
            engine.confirmed_facts.update(request.clarifications)
        
        # Determine mode
        mode = None
        if request.mode:
            try:
                mode = IntelligenceMode(request.mode)
            except:
                pass
        
        # ASK THE ENGINE
        answer = engine.ask(message, mode=mode)
        
        # Convert to JSON-serializable response
        response = {
            'session_id': session_id,
            'question': answer.question,
            'confidence': answer.confidence,
            'reasoning': answer.reasoning,
            
            # Clarification needed?
            'needs_clarification': answer.structured_output and answer.structured_output.get('type') == 'clarification_needed',
            'clarification_questions': answer.structured_output.get('questions', []) if answer.structured_output else [],
            
            # The three truths
            'from_reality': [
                {
                    'source_type': t.source_type,
                    'source_name': t.source_name,
                    'content': _serialize_content(t.content),
                    'confidence': t.confidence,
                    'location': t.location
                }
                for t in answer.from_reality
            ],
            'from_intent': [
                {
                    'source_type': t.source_type,
                    'source_name': t.source_name,
                    'content': _serialize_content(t.content),
                    'confidence': t.confidence,
                    'location': t.location
                }
                for t in answer.from_intent
            ],
            'from_best_practice': [
                {
                    'source_type': t.source_type,
                    'source_name': t.source_name,
                    'content': _serialize_content(t.content),
                    'confidence': t.confidence,
                    'location': t.location
                }
                for t in answer.from_best_practice
            ],
            
            # Conflicts and insights
            'conflicts': [
                {
                    'description': c.description,
                    'severity': c.severity,
                    'recommendation': c.recommendation
                }
                for c in answer.conflicts
            ],
            'insights': [
                {
                    'type': i.type,
                    'title': i.title,
                    'description': i.description,
                    'severity': i.severity,
                    'action_required': i.action_required,
                    'data': i.data
                }
                for i in answer.insights
            ],
            
            # Structured output
            'structured_output': answer.structured_output,
            
            # If clarification NOT needed, generate full answer with Claude
            'answer': None
        }
        
        # If we have enough context and don't need clarification, generate answer
        if not response['needs_clarification'] and answer.answer:
            # Use Claude to synthesize final answer from all sources
            response['answer'] = await _generate_intelligent_answer(
                question=message,
                context=answer.answer,  # The combined context from engine
                persona=request.persona,
                insights=answer.insights,
                conflicts=answer.conflicts
            )
        
        return response
        
    except Exception as e:
        logger.error(f"[INTELLIGENT] Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(500, f"Intelligence error: {str(e)}")


def _serialize_content(content):
    """Serialize content for JSON response."""
    if isinstance(content, dict):
        # Handle data content
        if 'rows' in content:
            return {
                'columns': content.get('columns', []),
                'rows': content.get('rows', [])[:20],  # Limit rows
                'total': content.get('total', len(content.get('rows', [])))
            }
        return content
    return str(content)[:2000]  # Limit text content


async def _generate_intelligent_answer(
    question: str,
    context: str,
    persona: str,
    insights: list,
    conflicts: list
) -> str:
    """
    Generate the final synthesized answer using Claude.
    
    This is where we turn the raw context into a coherent, helpful response.
    """
    try:
        # Build the mega-prompt
        system_prompt = """You are an expert UKG implementation consultant helping another consultant.

You have access to THREE SOURCES OF TRUTH:
1. CUSTOMER DATA - What their actual data shows
2. CUSTOMER DOCUMENTS - What they say they do/want
3. UKG BEST PRACTICE - How things should be done

Your job is to SYNTHESIZE these into clear, actionable guidance.

IMPORTANT RULES:
- If sources conflict, point it out clearly
- If data shows issues, mention them proactively
- Give specific, actionable recommendations
- Reference which source supports each claim
- Be concise but complete
"""
        
        # Add insight context
        insight_text = ""
        if insights:
            insight_text = "\n\n⚠️ PROACTIVE INSIGHTS FOUND:\n"
            for i in insights:
                insight_text += f"- [{i.severity.upper()}] {i.title}: {i.description}\n"
        
        # Add conflict context
        conflict_text = ""
        if conflicts:
            conflict_text = "\n\n⚡ CONFLICTS DETECTED:\n"
            for c in conflicts:
                conflict_text += f"- {c.description}\n  Recommendation: {c.recommendation}\n"
        
        user_prompt = f"""QUESTION: {question}

{context}
{insight_text}
{conflict_text}

Based on all sources above, provide a clear, synthesized answer. If you found issues or conflicts, address them proactively. Be specific and actionable."""

        # Use orchestrator
        orchestrator = LLMOrchestrator()
        
        import anthropic
        client = anthropic.Anthropic(api_key=orchestrator.claude_api_key)
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        
        return response.content[0].text
        
    except Exception as e:
        logger.error(f"[INTELLIGENT] Claude error: {e}")
        return f"I found relevant information but encountered an error generating the response. Here's what I gathered:\n\n{context[:3000]}"


# =============================================================================
# STEP 4: ADD SESSION MANAGEMENT ENDPOINTS
# =============================================================================

@router.get("/chat/intelligent/session/{session_id}")
async def get_session_state(session_id: str):
    """Get current state of an intelligence session."""
    if session_id not in intelligence_sessions:
        raise HTTPException(404, "Session not found")
    
    engine = intelligence_sessions[session_id]
    
    return {
        'session_id': session_id,
        'project': engine.project,
        'conversation_length': len(engine.conversation_history),
        'confirmed_facts': engine.confirmed_facts,
        'last_activity': engine.conversation_history[-1]['timestamp'] if engine.conversation_history else None
    }


@router.delete("/chat/intelligent/session/{session_id}")
async def end_session(session_id: str):
    """End an intelligence session."""
    if session_id in intelligence_sessions:
        del intelligence_sessions[session_id]
    return {'success': True, 'message': 'Session ended'}


@router.post("/chat/intelligent/session/{session_id}/confirm")
async def confirm_facts(session_id: str, facts: Dict[str, Any]):
    """Confirm facts/answers for a session."""
    if session_id not in intelligence_sessions:
        raise HTTPException(404, "Session not found")
    
    engine = intelligence_sessions[session_id]
    engine.confirmed_facts.update(facts)
    
    return {'success': True, 'confirmed_facts': engine.confirmed_facts}


# =============================================================================
# STEP 5: UPDATE EXISTING /chat/start TO USE INTELLIGENCE (optional)
# =============================================================================

# In process_chat_job function, around line 527, after STEP 3 (routing):
#
# Add this block to optionally use intelligence engine:
#
#     # Try intelligence engine first for supported modes
#     if INTELLIGENCE_AVAILABLE and route_info['route'] in ['structured', 'hybrid']:
#         try:
#             engine = IntelligenceEngine(project or 'default')
#             if STRUCTURED_QUERIES_AVAILABLE:
#                 handler = get_structured_handler()
#                 schema = {'tables': get_duckdb_tables_for_scope(project, scope)}
#                 engine.load_context(structured_handler=handler, schema=schema)
#             
#             analysis = engine._analyze_question(message)
#             
#             # If high confidence and doesn't need clarification, use intelligence
#             if analysis['confidence'] > 0.7 and not analysis['needs_clarification']:
#                 answer = engine.ask(message)
#                 
#                 # Add insights to response
#                 if answer.insights:
#                     for insight in answer.insights:
#                         context_parts.append(f"⚠️ {insight.title}: {insight.description}")
#                 
#                 logger.info(f"[INTELLIGENCE] Used for query, confidence: {answer.confidence}")
#         except Exception as ie:
#             logger.warning(f"[INTELLIGENCE] Failed, falling back: {ie}")


# =============================================================================
# USAGE EXAMPLE FROM FRONTEND
# =============================================================================
"""
// In your Chat.jsx component:

const sendIntelligentMessage = async (message) => {
  const response = await fetch(`${API_BASE}/api/chat/intelligent`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      project: activeProject?.name,
      session_id: sessionId,
      clarifications: pendingClarifications  // Any previous answers
    })
  });
  
  const data = await response.json();
  
  if (data.needs_clarification) {
    // Show clarification UI
    setClarificationQuestions(data.clarification_questions);
    setOriginalQuestion(data.question);
  } else {
    // Show full intelligent response
    setMessages(prev => [...prev, {
      role: 'assistant',
      type: 'intelligent',
      content: data.answer,
      from_reality: data.from_reality,
      from_intent: data.from_intent,
      from_best_practice: data.from_best_practice,
      conflicts: data.conflicts,
      insights: data.insights,
      confidence: data.confidence
    }]);
  }
};
"""
