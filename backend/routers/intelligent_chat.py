"""
INTELLIGENT CHAT ROUTER
========================

A NEW endpoint that provides revolutionary chat capabilities:
- THREE TRUTHS synthesis (Reality/Intent/Best Practice)
- Smart clarification questions before querying
- Proactive insight detection
- Conflict identification
- Structured output (business rules, config specs)

DEPLOY: backend/routers/intelligent_chat.py

THEN ADD TO main.py:
    from routers import intelligent_chat
    app.include_router(intelligent_chat.router, prefix="/api")

Author: XLR8 Team
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import logging
import uuid
import json

logger = logging.getLogger(__name__)

router = APIRouter(tags=["intelligent-chat"])

# Initialize learning module
try:
    from utils.learning import get_learning_module
    LEARNING_AVAILABLE = True
except ImportError:
    try:
        from backend.utils.learning import get_learning_module
        LEARNING_AVAILABLE = True
    except ImportError:
        LEARNING_AVAILABLE = False
        logger.warning("[INTELLIGENT] Learning module not available")


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class IntelligentChatRequest(BaseModel):
    """Request for intelligent chat."""
    message: str
    project: Optional[str] = None
    persona: Optional[str] = 'bessie'
    scope: Optional[str] = 'project'
    
    # Intelligence options
    mode: Optional[str] = None  # Force specific mode
    clarifications: Optional[Dict[str, Any]] = None  # Answers to clarification questions
    session_id: Optional[str] = None  # For conversation continuity


class ClarificationAnswer(BaseModel):
    """User's answers to clarification questions."""
    session_id: str
    original_question: str
    answers: Dict[str, Any]


# =============================================================================
# SESSION STORAGE
# =============================================================================

# In-memory session storage (in production, use Redis)
intelligence_sessions: Dict[str, Any] = {}


# =============================================================================
# MAIN ENDPOINT
# =============================================================================

@router.post("/chat/intelligent")
async def intelligent_chat(request: IntelligentChatRequest):
    """
    INTELLIGENT CHAT - The Revolutionary Endpoint
    
    This endpoint:
    1. Analyzes the question to understand intent
    2. Checks if clarification is needed
    3. Gathers from THREE sources (data, docs, UKG knowledge)
    4. Detects conflicts between sources
    5. Runs proactive checks for issues
    6. Synthesizes a complete, reasoned answer
    
    Returns structured response for rich frontend display.
    """
    project = request.project
    message = request.message
    session_id = request.session_id or f"session_{uuid.uuid4().hex[:8]}"
    
    logger.info(f"[INTELLIGENT] Question: {message[:100]}...")
    logger.info(f"[INTELLIGENT] Project: {project}, Session: {session_id}")
    
    try:
        # Import intelligence engine
        try:
            from utils.intelligence_engine import IntelligenceEngine, IntelligenceMode
            INTELLIGENCE_AVAILABLE = True
        except ImportError:
            try:
                from backend.utils.intelligence_engine import IntelligenceEngine, IntelligenceMode
                INTELLIGENCE_AVAILABLE = True
            except ImportError:
                INTELLIGENCE_AVAILABLE = False
        
        if not INTELLIGENCE_AVAILABLE:
            # Fallback to simple response
            return {
                "session_id": session_id,
                "answer": "Intelligence engine not available. Please check deployment.",
                "needs_clarification": False,
                "confidence": 0.0,
                "from_reality": [],
                "from_intent": [],
                "from_best_practice": [],
                "conflicts": [],
                "insights": [],
            }
        
        # Get or create engine for this session
        if session_id in intelligence_sessions:
            engine = intelligence_sessions[session_id]
        else:
            engine = IntelligenceEngine(project or 'default')
            
            # Load structured data handler
            try:
                from utils.structured_data_handler import get_structured_handler
                handler = get_structured_handler()
                
                # Get schema for project
                schema = await get_project_schema(project, request.scope)
                engine.load_context(structured_handler=handler, schema=schema)
                logger.info(f"[INTELLIGENT] Loaded structured handler with {len(schema.get('tables', []))} tables")
            except Exception as e:
                logger.warning(f"[INTELLIGENT] Could not load structured handler: {e}")
            
            # Load RAG handler
            try:
                from utils.rag_handler import RAGHandler
                rag = RAGHandler()
                engine.rag_handler = rag
                logger.info("[INTELLIGENT] Loaded RAG handler")
            except Exception as e:
                logger.warning(f"[INTELLIGENT] Could not load RAG handler: {e}")
            
            # Load relationships from data model
            try:
                try:
                    from utils.database.supabase_client import get_supabase_client
                except ImportError:
                    from backend.utils.database.supabase_client import get_supabase_client
                supabase = get_supabase_client()
                result = supabase.table('project_relationships').select('*').eq('project_name', project).eq('status', 'confirmed').execute()
                if result.data:
                    engine.relationships = result.data
                    logger.info(f"[INTELLIGENT] Loaded {len(result.data)} confirmed relationships")
            except Exception as e:
                logger.warning(f"[INTELLIGENT] Could not load relationships: {e}")
            
            # Store session
            intelligence_sessions[session_id] = engine
            
            # Cleanup old sessions (keep last 50)
            if len(intelligence_sessions) > 50:
                oldest = list(intelligence_sessions.keys())[0]
                del intelligence_sessions[oldest]
        
        # Apply any clarification answers
        if request.clarifications:
            engine.confirmed_facts.update(request.clarifications)
            logger.info(f"[INTELLIGENT] Applied clarifications: {list(request.clarifications.keys())}")
            
            # LEARNING: Record clarification choices
            if LEARNING_AVAILABLE:
                try:
                    learning = get_learning_module()
                    for q_id, choice in request.clarifications.items():
                        learning.record_clarification_choice(
                            question_id=q_id,
                            chosen_option=choice if isinstance(choice, str) else str(choice),
                            domain=request.clarifications.get('_domain'),
                            intent=request.clarifications.get('_intent'),
                            project=project,
                            user_id=None  # TODO: Get from auth
                        )
                except Exception as e:
                    logger.warning(f"[LEARNING] Failed to record clarification: {e}")
        
        # Determine mode
        mode = None
        if request.mode:
            try:
                mode = IntelligenceMode(request.mode)
            except:
                pass
        
        # LEARNING: Check for similar successful query
        learned_sql = None
        if LEARNING_AVAILABLE and not request.clarifications:
            try:
                learning = get_learning_module()
                similar = learning.find_similar_query(
                    question=message,
                    intent=mode.value if mode else None,
                    project=project
                )
                if similar and similar.get('successful_sql'):
                    learned_sql = similar['successful_sql']
                    logger.info(f"[LEARNING] Found learned query pattern (score: {similar.get('match_score', 0):.2f})")
            except Exception as e:
                logger.warning(f"[LEARNING] Error checking learned queries: {e}")
        
        # ASK THE ENGINE
        answer = engine.ask(message, mode=mode, context={'learned_sql': learned_sql} if learned_sql else None)
        
        # LEARNING: Check if we can skip clarification
        if answer.structured_output and answer.structured_output.get('type') == 'clarification_needed':
            if LEARNING_AVAILABLE:
                try:
                    learning = get_learning_module()
                    questions = answer.structured_output.get('questions', [])
                    detected_domain = answer.structured_output.get('detected_domains', ['general'])[0]
                    
                    can_skip, learned_answers = learning.should_skip_clarification(
                        questions=questions,
                        domain=detected_domain,
                        project=project,
                        user_id=None  # TODO: Get from auth
                    )
                    
                    if can_skip and learned_answers:
                        logger.info(f"[LEARNING] Skipping clarification - using learned answers: {learned_answers}")
                        engine.confirmed_facts.update(learned_answers)
                        # Re-ask with learned answers
                        answer = engine.ask(message, mode=mode)
                except Exception as e:
                    logger.warning(f"[LEARNING] Error checking skip clarification: {e}")
        
        # Build response
        response = {
            "session_id": session_id,
            "question": answer.question,
            "confidence": answer.confidence,
            "reasoning": answer.reasoning,
            
            # Clarification
            "needs_clarification": (
                answer.structured_output and 
                answer.structured_output.get('type') == 'clarification_needed'
            ),
            "clarification_questions": (
                answer.structured_output.get('questions', []) 
                if answer.structured_output else []
            ),
            
            # The THREE TRUTHS
            "from_reality": [serialize_truth(t) for t in answer.from_reality],
            "from_intent": [serialize_truth(t) for t in answer.from_intent],
            "from_best_practice": [serialize_truth(t) for t in answer.from_best_practice],
            
            # Conflicts and insights
            "conflicts": [
                {
                    "description": c.description,
                    "severity": c.severity,
                    "recommendation": c.recommendation
                }
                for c in answer.conflicts
            ],
            "insights": [
                {
                    "type": i.type,
                    "title": i.title,
                    "description": i.description,
                    "severity": i.severity,
                    "action_required": i.action_required,
                    "data": i.data if isinstance(i.data, (dict, list, str, int, float, bool, type(None))) else str(i.data)
                }
                for i in answer.insights
            ],
            
            # Structured output
            "structured_output": answer.structured_output,
            
            # Learning metadata
            "used_learning": learned_sql is not None,
            
            # The synthesized answer
            "answer": None
        }
        
        # If we don't need clarification, generate the full answer
        if not response["needs_clarification"] and answer.answer:
            # Use Claude to generate final synthesized response
            response["answer"] = await generate_intelligent_answer(
                question=message,
                context=answer.answer,
                persona=request.persona,
                insights=answer.insights,
                conflicts=answer.conflicts
            )
            
            # LEARNING: Record successful query pattern
            if LEARNING_AVAILABLE and response["answer"]:
                try:
                    learning = get_learning_module()
                    detected_domain = 'general'
                    if answer.structured_output and 'detected_domains' in answer.structured_output:
                        detected_domain = answer.structured_output['detected_domains'][0]
                    
                    learning.record_successful_query(
                        question=message,
                        sql=learned_sql,  # Will be None if we didn't use SQL
                        response=response["answer"][:500],
                        intent=mode.value if mode else 'search',
                        domain=detected_domain,
                        project=project,
                        sources=['reality' if answer.from_reality else None,
                                'intent' if answer.from_intent else None,
                                'best_practice' if answer.from_best_practice else None]
                    )
                except Exception as e:
                    logger.warning(f"[LEARNING] Failed to record query: {e}")
        
        return response
        
    except Exception as e:
        logger.error(f"[INTELLIGENT] Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(500, f"Intelligence error: {str(e)}")


# =============================================================================
# SESSION MANAGEMENT
# =============================================================================

@router.get("/chat/intelligent/session/{session_id}")
async def get_session(session_id: str):
    """Get current state of an intelligence session."""
    if session_id not in intelligence_sessions:
        raise HTTPException(404, "Session not found")
    
    engine = intelligence_sessions[session_id]
    
    return {
        "session_id": session_id,
        "project": engine.project,
        "conversation_length": len(engine.conversation_history),
        "confirmed_facts": engine.confirmed_facts,
    }


@router.delete("/chat/intelligent/session/{session_id}")
async def end_session(session_id: str):
    """End an intelligence session."""
    if session_id in intelligence_sessions:
        del intelligence_sessions[session_id]
    return {"success": True}


@router.post("/chat/intelligent/clarify")
async def submit_clarification(request: ClarificationAnswer):
    """Submit answers to clarification questions and get the real answer."""
    if request.session_id not in intelligence_sessions:
        raise HTTPException(404, "Session not found")
    
    engine = intelligence_sessions[request.session_id]
    
    # Store confirmed facts
    engine.confirmed_facts.update(request.answers)
    
    # Re-ask the original question with clarifications applied
    answer = engine.ask(request.original_question)
    
    return {
        "session_id": request.session_id,
        "question": answer.question,
        "confidence": answer.confidence,
        "answer": answer.answer,
        "from_reality": [serialize_truth(t) for t in answer.from_reality],
        "from_intent": [serialize_truth(t) for t in answer.from_intent],
        "from_best_practice": [serialize_truth(t) for t in answer.from_best_practice],
        "conflicts": [{"description": c.description, "severity": c.severity, "recommendation": c.recommendation} for c in answer.conflicts],
        "insights": [{"type": i.type, "title": i.title, "description": i.description, "severity": i.severity} for i in answer.insights],
    }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def serialize_truth(truth) -> Dict:
    """Serialize a Truth object for JSON response."""
    content = truth.content
    
    # Handle data content (rows from DuckDB)
    if isinstance(content, dict) and 'rows' in content:
        content = {
            'columns': content.get('columns', []),
            'rows': content.get('rows', [])[:20],  # Limit to 20 rows
            'total': content.get('total', len(content.get('rows', [])))
        }
    elif not isinstance(content, (dict, list, str, int, float, bool, type(None))):
        content = str(content)[:2000]
    
    return {
        "source_type": truth.source_type,
        "source_name": truth.source_name,
        "content": content,
        "confidence": truth.confidence,
        "location": truth.location
    }


async def get_project_schema(project: str, scope: str) -> Dict:
    """Get schema for project from DuckDB."""
    tables = []
    
    try:
        from utils.structured_data_handler import get_structured_handler
        handler = get_structured_handler()
        
        # Query _schema_metadata
        result = handler.conn.execute("""
            SELECT table_name, project, columns, row_count
            FROM _schema_metadata 
            WHERE is_current = TRUE
        """).fetchall()
        
        for row in result:
            table_name, proj, columns_json, row_count = row
            
            # Filter by scope
            if scope == 'project' and proj.lower() != (project or '').lower():
                continue
            
            columns = json.loads(columns_json) if columns_json else []
            
            tables.append({
                'table_name': table_name,
                'project': proj,
                'columns': columns,
                'row_count': row_count
            })
        
        # Also check _pdf_tables
        try:
            pdf_result = handler.conn.execute("""
                SELECT table_name, project, columns, row_count
                FROM _pdf_tables
            """).fetchall()
            
            for row in pdf_result:
                table_name, proj, columns_json, row_count = row
                
                if scope == 'project' and proj.lower() != (project or '').lower():
                    continue
                
                columns = json.loads(columns_json) if columns_json else []
                
                tables.append({
                    'table_name': table_name,
                    'project': proj,
                    'columns': columns,
                    'row_count': row_count
                })
        except:
            pass  # _pdf_tables might not exist
            
    except Exception as e:
        logger.warning(f"Could not get project schema: {e}")
    
    return {'tables': tables}


async def generate_intelligent_answer(
    question: str,
    context: str,
    persona: str,
    insights: list,
    conflicts: list
) -> str:
    """
    Generate the final synthesized answer using Claude.
    
    Takes the gathered context and produces a coherent, helpful response.
    """
    try:
        # Try to get Claude API
        from utils.llm_orchestrator import LLMOrchestrator
        orchestrator = LLMOrchestrator()
        
        if not orchestrator.claude_api_key:
            logger.warning("[INTELLIGENT] No Claude API key, returning raw context")
            return context[:3000]
        
        import anthropic
        client = anthropic.Anthropic(api_key=orchestrator.claude_api_key)
        
        # Build prompt
        system_prompt = """You are an expert UKG implementation consultant helping another consultant analyze customer data and configuration.

You have access to THREE SOURCES OF TRUTH:
1. CUSTOMER DATA (Reality) - What their actual data shows
2. CUSTOMER DOCUMENTS (Intent) - What they say they do or want
3. UKG BEST PRACTICE - How things should be done according to UKG standards

Your job is to SYNTHESIZE these into clear, actionable guidance.

IMPORTANT RULES:
- If sources conflict, point it out clearly
- If data shows issues, mention them proactively  
- Give specific, actionable recommendations
- Reference which source supports each claim
- Be concise but complete
- Use tables and lists when helpful
- Speak as a knowledgeable colleague, not a generic AI"""

        # Add insights
        insight_text = ""
        if insights:
            insight_text = "\n\n⚠️ PROACTIVE INSIGHTS:\n"
            for i in insights:
                severity = getattr(i, 'severity', 'medium')
                title = getattr(i, 'title', 'Issue')
                desc = getattr(i, 'description', '')
                insight_text += f"- [{severity.upper()}] {title}: {desc}\n"
        
        # Add conflicts
        conflict_text = ""
        if conflicts:
            conflict_text = "\n\n⚡ CONFLICTS DETECTED:\n"
            for c in conflicts:
                desc = getattr(c, 'description', str(c))
                rec = getattr(c, 'recommendation', '')
                conflict_text += f"- {desc}\n  Recommendation: {rec}\n"
        
        user_prompt = f"""QUESTION: {question}

{context}
{insight_text}
{conflict_text}

Based on all sources above, provide a clear, synthesized answer. Address any issues or conflicts proactively. Be specific and actionable."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        
        return response.content[0].text
        
    except Exception as e:
        logger.error(f"[INTELLIGENT] Claude generation failed: {e}")
        # Return the raw context as fallback
        return f"Here's what I found:\n\n{context[:3000]}"


# =============================================================================
# LEARNING ENDPOINTS
# =============================================================================

@router.get("/chat/intelligent/learning/stats")
async def get_learning_stats():
    """Get statistics about what the system has learned."""
    if not LEARNING_AVAILABLE:
        return {"available": False, "message": "Learning module not available"}
    
    try:
        learning = get_learning_module()
        return learning.get_learning_stats()
    except Exception as e:
        logger.error(f"[LEARNING] Error getting stats: {e}")
        return {"available": False, "error": str(e)}


@router.post("/chat/intelligent/feedback")
async def record_intelligent_feedback(
    question: str,
    feedback: str,  # 'positive' or 'negative'
    project: str = None,
    job_id: str = None,
    intent: str = None
):
    """Record feedback for a response to improve future answers."""
    if not LEARNING_AVAILABLE:
        return {"success": False, "message": "Learning module not available"}
    
    try:
        learning = get_learning_module()
        learning.record_feedback(
            question=question,
            feedback=feedback,
            project=project,
            job_id=job_id,
            intent=intent,
            was_intelligent=True
        )
        return {"success": True, "message": f"Recorded {feedback} feedback"}
    except Exception as e:
        logger.error(f"[LEARNING] Error recording feedback: {e}")
        return {"success": False, "error": str(e)}


@router.get("/chat/intelligent/preferences/{user_id}")
async def get_user_preferences(user_id: str, project: str = None):
    """Get learned preferences for a user."""
    if not LEARNING_AVAILABLE:
        return {"preferences": {}}
    
    try:
        from utils.database.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        query = supabase.table('user_preferences').select('*').eq('user_id', user_id)
        if project:
            query = query.eq('project', project)
        
        result = query.execute()
        
        prefs = {}
        for p in result.data or []:
            key = p['preference_key']
            prefs[key] = {
                'value': p['preference_value'],
                'confidence': p['confidence'],
                'learned_from': p['learned_from']
            }
        
        return {"preferences": prefs}
    except Exception as e:
        logger.error(f"[LEARNING] Error getting preferences: {e}")
        return {"preferences": {}, "error": str(e)}
