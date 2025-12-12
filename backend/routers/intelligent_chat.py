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
        
        # Get or create session - KEEP conversation context
        if session_id in intelligence_sessions:
            session = intelligence_sessions[session_id]
            engine = session.get('engine')
            last_sql = session.get('last_sql')
            last_result = session.get('last_result')
            last_question = session.get('last_question')
            logger.info(f"[INTELLIGENT] Resuming session, last_sql: {last_sql[:50] if last_sql else 'None'}...")
        else:
            engine = None
            last_sql = None
            last_result = None
            last_question = None
        
        # Create fresh engine if needed (but keep session data)
        if not engine:
            engine = IntelligenceEngine(project or 'default')
        
        # ALWAYS refresh schema/handler (don't use stale connections)
        structured_loaded = False
        try:
            from utils.structured_data_handler import get_structured_handler
            handler = get_structured_handler()
            
            if handler and handler.conn:
                # Get schema for project - direct query, no metadata dependency
                schema = await get_project_schema_direct(project, request.scope, handler)
                
                if schema.get('tables'):
                    engine.load_context(structured_handler=handler, schema=schema)
                    structured_loaded = True
                    logger.warning(f"[INTELLIGENT] Loaded {len(schema['tables'])} tables for {project}")
                else:
                    logger.warning(f"[INTELLIGENT] No tables found for project {project}")
        except Exception as e:
            logger.error(f"[INTELLIGENT] Structured handler failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        # Pass conversation context to engine
        if last_sql or last_result or last_question:
            engine.conversation_context = {
                'last_sql': last_sql,
                'last_result': last_result,
                'last_question': last_question
            }
        
        # Load RAG handler
        try:
            from utils.rag_handler import RAGHandler
            rag = RAGHandler()
            engine.rag_handler = rag
        except Exception as e:
            logger.warning(f"[INTELLIGENT] Could not load RAG handler: {e}")
        
        # Load relationships from data model
        try:
            try:
                from utils.database.supabase_client import get_supabase
            except ImportError:
                from utils.database.supabase_client import get_supabase
            supabase = get_supabase()
            # Load BOTH confirmed and auto_confirmed relationships
            result = supabase.table('project_relationships').select('*').eq('project_name', project).in_('status', ['confirmed', 'auto_confirmed']).execute()
            if result.data:
                engine.relationships = result.data
                logger.warning(f"[INTELLIGENT] Loaded {len(result.data)} relationships for {project}")
            else:
                logger.warning(f"[INTELLIGENT] No relationships found for {project}")
        except Exception as e:
            logger.warning(f"[INTELLIGENT] Failed to load relationships: {e}")
        
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
        auto_applied_facts = {}  # Track what was auto-applied
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
                        # Normalize keys: convert legacy 'employee_status' to 'status'
                        if 'employee_status' in learned_answers and 'status' not in learned_answers:
                            learned_answers['status'] = learned_answers.pop('employee_status')
                        
                        logger.info(f"[LEARNING] Skipping clarification - using learned answers: {learned_answers}")
                        engine.confirmed_facts.update(learned_answers)
                        auto_applied_facts = learned_answers.copy()  # Remember what we auto-applied
                        # Re-ask with learned answers
                        answer = engine.ask(message, mode=mode)
                except Exception as e:
                    logger.warning(f"[LEARNING] Error checking skip clarification: {e}")
        
        # Build human-readable description of auto-applied facts
        auto_applied_note = ""
        if auto_applied_facts:
            notes = []
            for key, value in auto_applied_facts.items():
                if key in ['employee_status', 'status']:
                    if value == 'active':
                        notes.append("Active employees only")
                    elif value == 'termed':
                        notes.append("Terminated employees only")
                    elif value == 'all':
                        notes.append("All employees (active + terminated)")
                    else:
                        notes.append(f"Employee status: {value}")
                else:
                    notes.append(f"{key}: {value}")
            if notes:
                auto_applied_note = "📌 *Remembered: " + ", ".join(notes) + "*"
        
        # Build response
        response = {
            "session_id": session_id,
            "question": answer.question,
            "confidence": answer.confidence,
            "reasoning": answer.reasoning,
            
            # Auto-applied facts reminder
            "auto_applied_note": auto_applied_note,
            "auto_applied_facts": auto_applied_facts,
            
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
        
        # If we don't need clarification, generate the answer
        if not response["needs_clarification"] and answer.answer:
            
            # CHECK: Is this a simple count/sum query with a clear result?
            # If so, just return it directly without Claude overhead
            simple_answer = None
            if answer.from_reality:
                for truth in answer.from_reality:
                    if isinstance(truth.content, dict):
                        query_type = truth.content.get('query_type', '')
                        rows = truth.content.get('rows', [])
                        sql = truth.content.get('sql', '')
                        cols = truth.content.get('columns', [])
                        
                        if query_type == 'count' and rows:
                            count_val = list(rows[0].values())[0] if rows[0] else 0
                            # Build simple direct answer
                            simple_answer = f"**{count_val:,}** employees match your criteria."
                            if sql:
                                simple_answer += f"\n\n*Query executed:* `{sql[:300]}`"
                            break
                        elif query_type in ['sum', 'average'] and rows:
                            result_val = list(rows[0].values())[0] if rows[0] else 0
                            label = "Total" if query_type == 'sum' else "Average"
                            simple_answer = f"**{label}: {result_val:,.2f}**"
                            if sql:
                                simple_answer += f"\n\n*Query executed:* `{sql[:300]}`"
                            break
                        elif query_type == 'list' and rows and cols:
                            # Format as markdown table
                            table_lines = []
                            # Header
                            display_cols = cols[:6]  # Limit columns for readability
                            table_lines.append("| " + " | ".join(display_cols) + " |")
                            table_lines.append("|" + "|".join(["---"] * len(display_cols)) + "|")
                            # Rows (limit to 20)
                            for row in rows[:20]:
                                vals = [str(row.get(c, ''))[:30] for c in display_cols]
                                table_lines.append("| " + " | ".join(vals) + " |")
                            
                            simple_answer = f"**Found {len(rows)} results:**\n\n" + "\n".join(table_lines)
                            if len(rows) > 20:
                                simple_answer += f"\n\n*Showing first 20 of {len(rows)} results*"
                            if sql:
                                simple_answer += f"\n\n*Query:* `{sql[:200]}`"
                            break
            
            if simple_answer:
                # Direct answer - no Claude needed
                # Prepend auto-applied note if any
                if auto_applied_note:
                    simple_answer = auto_applied_note + "\n\n" + simple_answer
                response["answer"] = simple_answer
                logger.info(f"[INTELLIGENT] Direct answer (no Claude): {simple_answer[:100]}")
            else:
                # Complex query - use Claude to synthesize
                claude_answer = await generate_intelligent_answer(
                    question=message,
                    context=answer.answer,
                    persona=request.persona,
                    insights=answer.insights,
                    conflicts=answer.conflicts
                )
                # Prepend auto-applied note if any
                if auto_applied_note and claude_answer:
                    response["answer"] = auto_applied_note + "\n\n" + claude_answer
                else:
                    response["answer"] = claude_answer
            
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
        
        # SAVE SESSION - preserve context for follow-up questions
        # Prefer executed_sql from engine, fall back to learned_sql
        actual_sql = getattr(answer, 'executed_sql', None) or learned_sql
        intelligence_sessions[session_id] = {
            'engine': engine,
            'last_sql': actual_sql,
            'last_result': response["answer"][:1000] if response.get("answer") else None,
            'last_question': message
        }
        logger.info(f"[INTELLIGENT] Saved session {session_id}, sql: {actual_sql[:50] if actual_sql else 'None'}...")
        
        # Handle case where we have no answer at all
        if response["answer"] is None and not response["needs_clarification"]:
            # Check if we have any data at all
            if answer.from_reality or answer.from_intent or answer.from_best_practice:
                response["answer"] = "I found some related information but couldn't generate a complete answer. Please try rephrasing your question."
            else:
                response["answer"] = "I couldn't find any data matching your query. Please check that data has been uploaded for this project."
            response["confidence"] = 0.3
        
        # Add helpful message for clarification responses
        if response["needs_clarification"]:
            questions = response.get("clarification_questions", [])
            if questions:
                q_text = questions[0].get('question', 'I need more information')
                response["answer"] = f"Before I can answer, {q_text.lower()}"
        
        # Cleanup old sessions (keep last 100)
        if len(intelligence_sessions) > 100:
            oldest = list(intelligence_sessions.keys())[0]
            del intelligence_sessions[oldest]
        
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


async def get_project_schema_direct(project: str, scope: str, handler) -> Dict:
    """Get schema by querying DuckDB directly - no metadata tables needed."""
    tables = []
    
    if not handler or not handler.conn:
        logger.error("[SCHEMA] No handler connection")
        return {'tables': []}
    
    try:
        # Get all tables directly from DuckDB
        all_tables = handler.conn.execute("SHOW TABLES").fetchall()
        logger.warning(f"[SCHEMA] DuckDB has {len(all_tables)} total tables")
        
        # Build project prefix for filtering (try multiple formats)
        project_clean = (project or '').strip()
        project_prefixes = [
            project_clean.lower(),
            project_clean.lower().replace(' ', '_'),
            project_clean.lower().replace(' ', '_').replace('-', '_'),
            project_clean.upper(),
            project_clean,
        ]
        
        matched_tables = []
        all_valid_tables = []
        
        for (table_name,) in all_tables:
            # Skip system/metadata tables
            if table_name.startswith('_'):
                continue
            
            all_valid_tables.append(table_name)
            
            # Check if matches any project prefix
            table_lower = table_name.lower()
            matches_project = any(table_lower.startswith(prefix.lower()) for prefix in project_prefixes if prefix)
            
            if matches_project:
                matched_tables.append(table_name)
        
        # Use matched tables if found, otherwise use ALL tables (better than nothing)
        tables_to_process = matched_tables if matched_tables else all_valid_tables
        
        if not matched_tables and all_valid_tables:
            logger.warning(f"[SCHEMA] No tables match project '{project}', using all {len(all_valid_tables)} tables")
        
        for table_name in tables_to_process:
            try:
                # Get columns - try multiple methods
                columns = []
                
                # Method 1: PRAGMA
                try:
                    col_result = handler.conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
                    columns = [row[1] for row in col_result]
                except:
                    pass
                
                # Method 2: DESCRIBE
                if not columns:
                    try:
                        col_result = handler.conn.execute(f'DESCRIBE "{table_name}"').fetchall()
                        columns = [row[0] for row in col_result]
                    except:
                        pass
                
                # Method 3: SELECT * LIMIT 0
                if not columns:
                    try:
                        result = handler.conn.execute(f'SELECT * FROM "{table_name}" LIMIT 0')
                        columns = [desc[0] for desc in result.description]
                    except:
                        pass
                
                if not columns:
                    logger.warning(f"[SCHEMA] Could not get columns for {table_name}")
                    continue
                
                # Get row count
                try:
                    count_result = handler.conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()
                    row_count = count_result[0] if count_result else 0
                except:
                    row_count = 0
                
                # Get column profiles (Phase 2: Data-driven clarification)
                categorical_columns = []
                column_profiles = {}
                try:
                    profile_result = handler.conn.execute("""
                        SELECT column_name, inferred_type, distinct_count, 
                               distinct_values, value_distribution, is_categorical,
                               min_value, max_value
                        FROM _column_profiles 
                        WHERE table_name = ?
                    """, [table_name]).fetchall()
                    
                    for prow in profile_result:
                        col_name, inf_type, distinct_cnt, distinct_vals, val_dist, is_cat, min_val, max_val = prow
                        
                        profile = {
                            'inferred_type': inf_type,
                            'distinct_count': distinct_cnt,
                            'is_categorical': is_cat
                        }
                        
                        # Parse JSON fields
                        if distinct_vals:
                            try:
                                profile['distinct_values'] = json.loads(distinct_vals)
                            except:
                                pass
                        
                        if val_dist:
                            try:
                                profile['value_distribution'] = json.loads(val_dist)
                            except:
                                pass
                        
                        if inf_type == 'numeric':
                            profile['min_value'] = min_val
                            profile['max_value'] = max_val
                        
                        column_profiles[col_name] = profile
                        
                        # Track categorical columns for clarification
                        if is_cat and distinct_cnt and distinct_cnt <= 20:
                            categorical_columns.append({
                                'column': col_name,
                                'values': profile.get('distinct_values', []),
                                'distribution': profile.get('value_distribution', {})
                            })
                    
                    if categorical_columns:
                        logger.warning(f"[SCHEMA] {table_name.split('__')[-1]}: {len(categorical_columns)} categorical columns, {len(column_profiles)} total profiles")
                    elif column_profiles:
                        logger.warning(f"[SCHEMA] {table_name.split('__')[-1]}: {len(column_profiles)} profiles (no categorical)")
                        
                except Exception as profile_e:
                    logger.warning(f"[SCHEMA] No profiles for {table_name}: {profile_e}")
                
                tables.append({
                    'table_name': table_name,
                    'project': project or 'unknown',
                    'columns': columns,
                    'row_count': row_count,
                    'column_profiles': column_profiles,
                    'categorical_columns': categorical_columns
                })
                
                # Log first few columns
                col_preview = columns[:8]
                logger.info(f"[SCHEMA] {table_name}: {col_preview}{'...' if len(columns) > 8 else ''} ({row_count} rows)")
                
            except Exception as col_e:
                logger.warning(f"[SCHEMA] Error processing {table_name}: {col_e}")
        
        logger.warning(f"[SCHEMA] Returning {len(tables)} tables for project '{project}'")
        
        # Get filter candidates for intelligent clarification
        filter_candidates = {}
        try:
            filter_candidates = handler.get_filter_candidates(project)
            if filter_candidates:
                logger.warning(f"[SCHEMA] Filter candidates: {list(filter_candidates.keys())}")
        except Exception as fc_e:
            logger.warning(f"[SCHEMA] Could not get filter candidates: {fc_e}")
        
    except Exception as e:
        logger.error(f"[SCHEMA] Failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    return {'tables': tables, 'filter_candidates': filter_candidates}


async def get_project_schema(project: str, scope: str) -> Dict:
    """Get schema for project from DuckDB."""
    tables = []
    
    try:
        from utils.structured_data_handler import get_structured_handler
        handler = get_structured_handler()
        
        # FIRST: Try _schema_metadata
        try:
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
        except Exception as meta_e:
            logger.warning(f"Could not query _schema_metadata: {meta_e}")
        
        # SECOND: Also check _pdf_tables
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
        
        # THIRD: DIRECT QUERY - If we found nothing, query DuckDB directly for tables
        if not tables:
            logger.warning(f"[SCHEMA] No tables from metadata - querying DuckDB directly")
            try:
                # Get all tables
                all_tables = handler.conn.execute("SHOW TABLES").fetchall()
                project_prefix = (project or '').lower().replace(' ', '_').replace('-', '_')
                
                for (table_name,) in all_tables:
                    # Skip system tables
                    if table_name.startswith('_'):
                        continue
                    
                    # Filter by project prefix if scope is project
                    if scope == 'project' and project_prefix:
                        if not table_name.lower().startswith(project_prefix.lower()):
                            continue
                    
                    # Get columns for this table
                    try:
                        col_result = handler.conn.execute(f'DESCRIBE "{table_name}"').fetchall()
                        columns = [row[0] for row in col_result]  # column_name is first field
                        
                        # Get row count
                        count_result = handler.conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()
                        row_count = count_result[0] if count_result else 0
                        
                        tables.append({
                            'table_name': table_name,
                            'project': project or 'unknown',
                            'columns': columns,
                            'row_count': row_count
                        })
                        logger.info(f"[SCHEMA] Found table {table_name} with {len(columns)} columns, {row_count} rows")
                    except Exception as col_e:
                        logger.warning(f"[SCHEMA] Could not describe {table_name}: {col_e}")
                
                logger.info(f"[SCHEMA] Direct query found {len(tables)} tables for project {project}")
                
            except Exception as direct_e:
                logger.error(f"[SCHEMA] Direct table query failed: {direct_e}")
            
    except Exception as e:
        logger.warning(f"Could not get project schema: {e}")
    
    logger.warning(f"[SCHEMA] Returning {len(tables)} tables for project {project}")
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
        from utils.database.supabase_client import get_supabase
        supabase = get_supabase()
        
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


# =============================================================================
# DIAGNOSTIC ENDPOINTS
# =============================================================================

@router.get("/chat/intelligent/diagnostics/profiles")
async def check_profiles(project: str = None):
    """
    Check if column profiles exist and show filter candidates.
    GET /api/chat/intelligent/diagnostics/profiles?project=TEA1000
    """
    try:
        from utils.structured_data_handler import get_structured_handler
    except ImportError:
        from backend.utils.structured_data_handler import get_structured_handler
    
    handler = get_structured_handler()
    
    result = {
        "profiles_table_exists": False,
        "total_profiles": 0,
        "profiles_by_project": {},
        "filter_candidates": {},
        "sample_profiles": []
    }
    
    try:
        # Check if table exists
        tables = handler.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='_column_profiles'").fetchall()
        if not tables:
            # Try DuckDB syntax
            tables = handler.conn.execute("SELECT table_name FROM information_schema.tables WHERE table_name = '_column_profiles'").fetchall()
        
        result["profiles_table_exists"] = len(tables) > 0
        
        if result["profiles_table_exists"]:
            # Count total
            count = handler.conn.execute("SELECT COUNT(*) FROM _column_profiles").fetchone()
            result["total_profiles"] = count[0] if count else 0
            
            # Count by project
            by_project = handler.conn.execute("""
                SELECT project, COUNT(*) as cnt 
                FROM _column_profiles 
                GROUP BY project
            """).fetchall()
            result["profiles_by_project"] = {p[0]: p[1] for p in by_project}
            
            # Get filter candidates
            if project:
                result["filter_candidates"] = handler.get_filter_candidates(project)
            
            # Sample profiles
            if project:
                samples = handler.conn.execute("""
                    SELECT table_name, column_name, inferred_type, distinct_count, is_categorical, filter_category
                    FROM _column_profiles 
                    WHERE project = ?
                    LIMIT 15
                """, [project]).fetchall()
            else:
                samples = handler.conn.execute("""
                    SELECT table_name, column_name, inferred_type, distinct_count, is_categorical, filter_category
                    FROM _column_profiles 
                    LIMIT 15
                """).fetchall()
            
            result["sample_profiles"] = [
                {
                    "table": s[0].split('__')[-1] if s[0] else '',
                    "column": s[1],
                    "type": s[2],
                    "distinct_count": s[3],
                    "is_categorical": s[4],
                    "filter_category": s[5]
                }
                for s in samples
            ]
    except Exception as e:
        result["error"] = str(e)
    
    return result


@router.post("/chat/intelligent/diagnostics/backfill")
async def run_backfill(project: str = None):
    """
    Run profile backfill for existing tables.
    POST /api/chat/intelligent/diagnostics/backfill?project=TEA1000
    """
    try:
        from utils.structured_data_handler import get_structured_handler
    except ImportError:
        from backend.utils.structured_data_handler import get_structured_handler
    
    handler = get_structured_handler()
    
    # Check if backfill method exists
    if not hasattr(handler, 'backfill_profiles'):
        return {"error": "backfill_profiles method not found - deploy latest structured_data_handler.py"}
    
    result = handler.backfill_profiles(project)
    return result
