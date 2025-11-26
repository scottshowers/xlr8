"""
Chat Router for XLR8 - ADVANCED RAG FEATURES + BESSIE! 🐮
==========================================================

Features:
- ✅ Real-time status updates
- ✅ Query decomposition (compound questions)
- ✅ Smart aggregation (count/sum queries)
- ✅ Intent classification (optimal routing)
- ✅ Persona system (Bessie and friends!)

Author: XLR8 Team
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import sys
import os
import logging
import uuid
import threading
import time

sys.path.insert(0, '/app')
sys.path.insert(0, '/data')

from utils.rag_handler import RAGHandler
from utils.llm_orchestrator import LLMOrchestrator
from utils.query_decomposition import DiverseRetriever
from utils.smart_aggregation import handle_aggregation
from utils.intent_classifier import classify_and_configure
from utils.persona_manager import get_persona_manager

# Import structured data handling (DuckDB for Excel/CSV queries)
try:
    from utils.structured_data_handler import get_structured_handler
    STRUCTURED_QUERIES_AVAILABLE = True
except ImportError as e:
    STRUCTURED_QUERIES_AVAILABLE = False
    logger_temp = logging.getLogger(__name__)
    logger_temp.warning(f"Structured queries not available: {e}")

# Import intelligent query router
try:
    from utils.query_router_intelligent import get_query_router, QueryType, detect_query_type
    INTELLIGENT_ROUTING = True
    logger_temp = logging.getLogger(__name__)
    logger_temp.info("Intelligent query routing enabled")
except ImportError:
    INTELLIGENT_ROUTING = False
    # Define QueryType enum for fallback
    from enum import Enum
    class QueryType(Enum):
        STRUCTURED = "structured"
        UNSTRUCTURED = "unstructured"
        HYBRID = "hybrid"
        GENERAL = "general"
    
    def detect_query_type(*args, **kwargs):
        return {'route': QueryType.GENERAL, 'reasoning': ['Fallback mode']}
    
    def get_query_router():
        return None
    
    logger_temp = logging.getLogger(__name__)
    logger_temp.warning("Intelligent routing not available, using fallback")

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize orchestrator
orchestrator = LLMOrchestrator()

# In-memory job storage (for status tracking)
chat_jobs = {}


class ChatRequest(BaseModel):
    message: str
    project: Optional[str] = None
    functional_area: Optional[str] = None
    max_results: Optional[int] = 50  # Increased from 30 to get more chunks
    persona: Optional[str] = 'bessie'  # NEW: Default to Bessie 🐮


class PersonaCreate(BaseModel):
    name: str
    icon: str
    description: str
    system_prompt: str
    expertise: List[str]
    tone: str


class PersonaUpdate(BaseModel):
    icon: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    expertise: Optional[List[str]] = None
    tone: Optional[str] = None


class ChatJobStatus(BaseModel):
    job_id: str
    status: str  # 'processing', 'complete', 'error'
    current_step: str
    progress: int  # 0-100
    response: Optional[str] = None
    sources: Optional[List[Dict]] = None
    chunks_found: Optional[int] = None
    models_used: Optional[List[str]] = None
    query_type: Optional[str] = None
    sanitized: Optional[bool] = None
    error: Optional[str] = None


def update_job_status(job_id: str, status: str, step: str, progress: int, **kwargs):
    """Update job status"""
    if job_id in chat_jobs:
        chat_jobs[job_id].update({
            'status': status,
            'current_step': step,
            'progress': progress,
            **kwargs
        })
        logger.info(f"[JOB {job_id}] {step} ({progress}%)")


def handle_structured_query(job_id: str, message: str, project: Optional[str], persona, routing_meta: dict) -> bool:
    """
    Handle structured data queries via DuckDB SQL.
    Returns True if handled, False to fall through to RAG.
    """
    try:
        update_job_status(job_id, 'processing', '📊 Detected data query - checking tables...', 10)
        
        handler = get_structured_handler()
        router = get_query_router()
        
        # Get schema for this project
        schema = handler.get_schema_for_project(project) if project else {'tables': []}
        
        if not schema.get('tables'):
            logger.info(f"[STRUCTURED] No tables found for project '{project}', falling back to RAG")
            return False
        
        update_job_status(job_id, 'processing', '🔧 Generating SQL query...', 20)
        
        # Build SQL prompt with schema
        sql_prompt = router.build_sql_prompt(message, schema)
        
        # Use orchestrator to generate SQL
        orchestrator_instance = LLMOrchestrator()
        sql_result = orchestrator_instance.generate_sql(sql_prompt)
        
        if not sql_result or not sql_result.get('sql'):
            logger.warning("[STRUCTURED] Failed to generate SQL")
            return False
        
        sql_query = sql_result['sql'].strip()
        logger.info(f"[STRUCTURED] Generated SQL: {sql_query[:200]}...")
        
        update_job_status(job_id, 'processing', '⚡ Executing query...', 40)
        
        # Execute query
        try:
            rows, columns = handler.execute_query(sql_query)
        except Exception as e:
            logger.error(f"[STRUCTURED] SQL execution error: {e}")
            # Return error but don't fall through - tell user the query failed
            update_job_status(
                job_id, 'complete', 'Complete', 100,
                response=f"I tried to query your data but encountered an error: {str(e)}\n\nGenerated SQL:\n```sql\n{sql_query}\n```\n\nThis might mean the data doesn't have the columns I expected. Could you rephrase your question?",
                sources=[],
                chunks_found=0,
                models_used=['sql_generation', 'duckdb'],
                query_type='structured_error',
                sanitized=False
            )
            return True
        
        update_job_status(job_id, 'processing', '📝 Formatting results...', 70)
        
        # Check if export requested
        needs_export = router.needs_export(message)
        export_path = None
        
        if needs_export and rows:
            update_job_status(job_id, 'processing', '📥 Creating export file...', 80)
            import os
            from datetime import datetime
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            export_dir = '/data/exports'
            os.makedirs(export_dir, exist_ok=True)
            
            if 'csv' in message.lower():
                export_path = f"{export_dir}/query_result_{timestamp}.csv"
                handler.export_to_csv(sql_query, export_path)
            else:
                export_path = f"{export_dir}/query_result_{timestamp}.xlsx"
                handler.export_to_excel(sql_query, export_path)
            
            logger.info(f"[STRUCTURED] Exported to {export_path}")
        
        # Format response
        update_job_status(job_id, 'processing', '✨ Generating response...', 90)
        
        response = format_structured_response(message, rows, columns, persona, sql_query, export_path)
        
        # Build source info
        sources = [{
            'filename': 'DuckDB Query',
            'type': 'structured_data',
            'tables_queried': [t['table_name'] for t in schema.get('tables', [])[:5]],
            'rows_returned': len(rows),
            'relevance': 100
        }]
        
        update_job_status(
            job_id, 'complete', 'Complete', 100,
            response=response,
            sources=sources,
            chunks_found=len(rows),
            models_used=['sql_generation', 'duckdb'],
            query_type='structured',
            sanitized=False,
            export_path=export_path
        )
        
        return True
        
    except Exception as e:
        logger.error(f"[STRUCTURED] Error: {e}", exc_info=True)
        return False


def format_structured_response(message: str, rows: list, columns: list, persona, sql_query: str, export_path: str = None) -> str:
    """Format SQL query results into a nice response"""
    
    if not rows:
        return f"I searched your data but didn't find any matching records. The query I used was:\n\n```sql\n{sql_query}\n```\n\nTry rephrasing your question or check if the data has been uploaded."
    
    # Count query
    if len(rows) == 1 and len(columns) == 1 and columns[0].lower() in ['count', 'total', 'cnt']:
        count = list(rows[0].values())[0]
        return f"**{count}** records match your criteria."
    
    # List query - format as table
    response_parts = []
    
    # Summary
    response_parts.append(f"Found **{len(rows)}** records:\n")
    
    # Table header
    if len(columns) <= 6:  # Narrow enough for markdown table
        header = "| " + " | ".join(str(c) for c in columns) + " |"
        separator = "| " + " | ".join("---" for _ in columns) + " |"
        response_parts.append(header)
        response_parts.append(separator)
        
        # Rows (limit to 50 for display)
        for row in rows[:50]:
            row_str = "| " + " | ".join(str(row.get(c, '')) for c in columns) + " |"
            response_parts.append(row_str)
        
        if len(rows) > 50:
            response_parts.append(f"\n*...and {len(rows) - 50} more rows*")
    else:
        # Too many columns - show as list
        for i, row in enumerate(rows[:20], 1):
            items = [f"**{k}**: {v}" for k, v in row.items() if v is not None]
            response_parts.append(f"{i}. " + " | ".join(items[:6]))
        
        if len(rows) > 20:
            response_parts.append(f"\n*...and {len(rows) - 20} more rows*")
    
    # Export link
    if export_path:
        filename = export_path.split('/')[-1]
        response_parts.append(f"\n\n📥 **[Download {filename}]({export_path})**")
    
    return "\n".join(response_parts)


def handle_hybrid_query(job_id: str, message: str, project: Optional[str], persona, routing_meta: dict, max_results: int) -> bool:
    """
    Handle hybrid queries that need both structured data AND explanations.
    Example: "List employees in REG earning group and explain what REG means"
    """
    try:
        update_job_status(job_id, 'processing', '🔀 Hybrid query - getting data + context...', 10)
        
        # Part 1: Try structured query for the data part
        structured_result = None
        try:
            handler = get_structured_handler()
            schema = handler.get_schema_for_project(project) if project else {'tables': []}
            
            if schema.get('tables'):
                router = get_query_router()
                sql_prompt = router.build_sql_prompt(message, schema)
                
                orchestrator_instance = LLMOrchestrator()
                sql_result = orchestrator_instance.generate_sql(sql_prompt)
                
                if sql_result and sql_result.get('sql'):
                    rows, columns = handler.execute_query(sql_result['sql'])
                    structured_result = {
                        'rows': rows,
                        'columns': columns,
                        'sql': sql_result['sql']
                    }
                    logger.info(f"[HYBRID] Got {len(rows)} rows from structured query")
        except Exception as e:
            logger.warning(f"[HYBRID] Structured part failed: {e}")
        
        update_job_status(job_id, 'processing', '📚 Searching knowledge base...', 40)
        
        # Part 2: RAG search for explanations/context
        rag = RAGHandler()
        try:
            collection = rag.client.get_collection("documents")
        except:
            collection = None
        
        rag_context = ""
        if collection:
            where_filter = None
            if project and project not in ['', 'all', 'All Projects']:
                where_filter = {
                    "$or": [
                        {"project": project},
                        {"project": "Global/Universal"}
                    ]
                }
            
            query_embedding = rag.get_embedding(message)
            if query_embedding:
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=10,
                    where=where_filter,
                    include=["documents", "metadatas"]
                )
                
                if results and results.get('documents') and results['documents'][0]:
                    rag_context = "\n\n".join(results['documents'][0][:5])
        
        update_job_status(job_id, 'processing', '✨ Generating response...', 70)
        
        # Combine results
        combined_prompt = f"""[SYSTEM: You are {persona.name}. {persona.system_prompt}]

User Question: {message}

"""
        
        if structured_result and structured_result['rows']:
            combined_prompt += f"""DATA FROM DATABASE ({len(structured_result['rows'])} rows):
{format_structured_response(message, structured_result['rows'][:20], structured_result['columns'], persona, structured_result['sql'])}

"""
        
        if rag_context:
            combined_prompt += f"""RELEVANT DOCUMENTATION:
{rag_context[:3000]}

"""
        
        combined_prompt += "Please provide a comprehensive answer combining the data and any relevant explanations."
        
        # Generate combined response
        orchestrator_instance = LLMOrchestrator()
        result = orchestrator_instance.process_query(combined_prompt, [])
        
        response = result.get('response', 'Could not generate response')
        
        # Add data summary if we have structured results
        if structured_result and structured_result['rows']:
            if len(structured_result['rows']) > 20:
                response += f"\n\n*Note: Showing first 20 of {len(structured_result['rows'])} total rows.*"
        
        update_job_status(
            job_id, 'complete', 'Complete', 100,
            response=response,
            sources=[{'filename': 'Hybrid Query', 'type': 'hybrid'}],
            chunks_found=len(structured_result['rows']) if structured_result else 0,
            models_used=['sql_generation', 'duckdb', 'rag', result.get('models_used', ['claude'])[-1]],
            query_type='hybrid',
            sanitized=False
        )
        
        return True
        
    except Exception as e:
        logger.error(f"[HYBRID] Error: {e}", exc_info=True)
        return False


def process_chat_job(job_id: str, message: str, project: Optional[str], max_results: int, persona_name: str = 'bessie'):
    """Background processing for chat with ADVANCED FEATURES + BESSIE! 🐮
    
    NOW WITH SMART ROUTING:
    - Structured queries (count, list, filter) → DuckDB SQL
    - Unstructured queries (explain, how-to) → RAG + LLM
    - Hybrid queries → Both!
    """
    try:
        # STEP 0: LOAD PERSONA
        pm = get_persona_manager()
        persona = pm.get_persona(persona_name)
        logger.info(f"[PERSONA] Using: {persona.name} {persona.icon}")
        
        # STEP 0.5: INTELLIGENT QUERY ROUTING
        if STRUCTURED_QUERIES_AVAILABLE:
            update_job_status(job_id, 'processing', '🧠 Analyzing query type...', 3)
            
            # Check what data is available for this project
            try:
                handler = get_structured_handler()
                schema = handler.get_schema_for_project(project) if project else {}
                has_structured = bool(schema.get('tables'))
                table_names = list(schema.get('tables', {}).keys())
            except:
                has_structured = False
                table_names = []
            
            # Check if RAG has data
            try:
                rag_check = RAGHandler()
                rag_collection = rag_check.client.get_collection("documents")
                has_rag = rag_collection.count() > 0
            except:
                has_rag = False
            
            # Use intelligent routing
            if INTELLIGENT_ROUTING:
                routing_result = detect_query_type(
                    message, 
                    has_structured=has_structured, 
                    has_rag=has_rag,
                    tables=table_names
                )
                query_type = routing_result['route']
                logger.info(f"[ROUTING] {query_type.value} | Reasoning: {', '.join(routing_result['reasoning'])}")
            else:
                # Simple fallback - if structured data exists, try SQL first
                if has_structured:
                    query_type = QueryType.STRUCTURED
                    logger.info(f"[ROUTING] STRUCTURED (fallback - structured data exists)")
                elif has_rag:
                    query_type = QueryType.UNSTRUCTURED
                    logger.info(f"[ROUTING] UNSTRUCTURED (fallback - RAG data exists)")
                else:
                    query_type = QueryType.GENERAL
                    logger.info(f"[ROUTING] GENERAL (fallback - no data)")
            
            # STRUCTURED QUERY PATH (SQL) - TRY FIRST IF DATA EXISTS
            if query_type == QueryType.STRUCTURED or (has_structured and query_type != QueryType.UNSTRUCTURED):
                result = handle_structured_query(job_id, message, project, persona, {'tables': table_names})
                if result:
                    return  # Structured query handled successfully
                # If structured failed, fall through to RAG
                logger.warning("[ROUTING] Structured query failed, falling back to RAG")
            
            # HYBRID QUERY PATH (SQL + RAG)
            elif query_type == QueryType.HYBRID:
                result = handle_hybrid_query(job_id, message, project, persona, {}, max_results)
                if result:
                    return
                logger.warning("[ROUTING] Hybrid query failed, falling back to RAG")
        
        # UNSTRUCTURED/GENERAL PATH continues below (existing RAG flow)
        
        # STEP 1: INTENT CLASSIFICATION
        update_job_status(job_id, 'processing', '🧠 Understanding query...', 5)
        
        intent_config = classify_and_configure(message)
        logger.info(f"[INTENT] {intent_config['intent']} - Strategy: {intent_config['strategy']}")
        
        # Override max_results based on intent
        n_results = intent_config.get('n_results', max_results)
        
        update_job_status(job_id, 'processing', '🔵 Searching documents...', 10)
        
        # Initialize RAG
        rag = RAGHandler()
        
        try:
            collection = rag.client.get_collection("documents")
        except:
            update_job_status(job_id, 'error', 'Error', 100, error='No documents uploaded')
            return
        
        # Build filter
        where_filter = None
        if project and project not in ['', 'all', 'All Projects']:
            where_filter = {"project": project}
        
        # STEP 2: CHECK FOR AGGREGATION QUERIES
        if intent_config['use_aggregation']:
            update_job_status(job_id, 'processing', '🔢 Computing aggregation...', 15)
            
            agg_result = handle_aggregation(rag, collection, message, where_filter)
            
            if agg_result and agg_result.get('needs_agg'):
                # Aggregation handled, return formatted response
                update_job_status(
                    job_id, 'complete', 'Complete', 100,
                    response=agg_result['formatted_response'],
                    sources=[],
                    chunks_found=agg_result.get('total_chunks', 0),
                    models_used=['aggregation'],
                    query_type='aggregation',
                    sanitized=False
                )
                return
        
        update_job_status(job_id, 'processing', '📊 Retrieving chunks...', 20)
        
        # STEP 3: DIVERSE RETRIEVAL (if compound query or intent suggests)
        # Example: "Give me deduction groups and pay groups" 
        # → Searches both sheets separately and merges results
        
        use_decomposition = intent_config.get('use_decomposition', False)
        
        try:
            from utils.query_decomposition import QueryDecomposer
            
            decomposer = QueryDecomposer()
            
            # Check if compound query OR intent requires decomposition
            is_compound = decomposer.is_compound_query(message)
            
            if is_compound or use_decomposition:
                # COMPOUND QUERY: Split and search each separately
                sub_queries = decomposer.decompose_query(message)
                logger.info(f"[DIVERSE] Compound query detected: {len(sub_queries)} sub-queries")
                
                # Retrieve for each sub-query
                results_per_query = n_results // len(sub_queries)
                all_documents = []
                all_metadatas = []
                all_distances = []
                seen_ids = set()
                
                for i, sub_query in enumerate(sub_queries):
                    logger.info(f"[DIVERSE] Sub-query {i+1}: {sub_query}")
                    
                    # Get embedding for sub-query
                    sub_embedding = rag.get_embedding(sub_query)
                    if not sub_embedding:
                        continue
                    
                    # Search for this sub-query
                    sub_results = collection.query(
                        query_embeddings=[sub_embedding],
                        n_results=results_per_query + 10,  # Extra for deduplication
                        where=where_filter,
                        include=["documents", "metadatas", "distances"]
                    )
                    
                    # Add results, deduplicating by content hash
                    if sub_results and sub_results.get('documents') and sub_results['documents'][0]:
                        for j in range(len(sub_results['documents'][0])):
                            doc = sub_results['documents'][0][j]
                            doc_hash = hash(doc[:100])  # Simple deduplication
                            
                            if doc_hash in seen_ids:
                                continue
                            
                            seen_ids.add(doc_hash)
                            all_documents.append(doc)
                            all_metadatas.append(sub_results['metadatas'][0][j])
                            all_distances.append(sub_results['distances'][0][j])
                            
                            if len(all_documents) >= n_results:
                                break
                    
                    if len(all_documents) >= n_results:
                        break
                
                # Format as ChromaDB result
                results = {
                    'documents': [all_documents],
                    'metadatas': [all_metadatas],
                    'distances': [all_distances]
                }
                
                # Log diversity
                sheets_found = set()
                for meta in all_metadatas:
                    if 'parent_section' in meta:
                        sheets_found.add(meta['parent_section'])
                logger.info(f"[DIVERSE] Retrieved {len(all_documents)} chunks from {len(sheets_found)} sheets: {', '.join(sorted(sheets_found))}")
                
            else:
                # SIMPLE QUERY: Use normal search
                logger.info(f"[SIMPLE] Single-topic query, using standard search")
                
                # Get embedding
                query_embedding = rag.get_embedding(message)
                if not query_embedding:
                    update_job_status(job_id, 'error', 'Error', 100, error='Failed to create embedding')
                    return
                
                # Search
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=n_results,
                    where=where_filter,
                    include=["documents", "metadatas", "distances"]
                )
        
        except Exception as e:
            # Fallback to standard search if decomposition fails
            logger.warning(f"[DIVERSE] Decomposition failed, using standard search: {e}")
            
            query_embedding = rag.get_embedding(message)
            if not query_embedding:
                update_job_status(job_id, 'error', 'Error', 100, error='Failed to create embedding')
                return
            
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )
        
        if not results or not results.get('documents') or not results['documents'][0]:
            update_job_status(job_id, 'error', 'Error', 100, error='No relevant documents found')
            return
        
        documents = results['documents'][0]
        metadatas = results['metadatas'][0] if results.get('metadatas') else [{}] * len(documents)
        distances = results['distances'][0] if results.get('distances') else [0] * len(documents)
        
        logger.info(f"Found {len(documents)} chunks")
        
        # Smart sheet filtering
        query_lower = message.lower()
        sheet_keywords = {
            'earning': ['earnings', 'earning'],
            'deduction': ['deductions', 'deduction'],
            'benefit': ['benefits', 'benefit'],
            'accrual': ['accruals', 'accrual', 'pto', 'time off'],
            'tax': ['taxes', 'tax', 'withholding'],
            'gl': ['gl rules', 'gl mapping', 'general ledger'],
            'pay code': ['pay codes', 'pay code'],
        }
        
        priority_sheets = []
        for keyword, sheets in sheet_keywords.items():
            if keyword in query_lower:
                priority_sheets.extend(sheets)
        
        if priority_sheets:
            def chunk_priority(item):
                doc, meta, dist = item
                sheet = str(meta.get('parent_section', '')).lower()
                is_priority = any(ps in sheet for ps in priority_sheets)
                return (0 if is_priority else 1, dist)
            
            combined = list(zip(documents, metadatas, distances))
            combined.sort(key=chunk_priority)
            documents, metadatas, distances = zip(*combined) if combined else ([], [], [])
            documents, metadatas, distances = list(documents), list(metadatas), list(distances)
        
        # Build chunks
        chunks = []
        for doc, meta, dist in zip(documents, metadatas, distances):
            chunks.append({'document': doc, 'metadata': meta, 'distance': dist})
        
        # Build sources
        source_map = {}
        for doc, meta, dist in zip(documents, metadatas, distances):
            filename = meta.get('filename', meta.get('source', 'Unknown'))
            if filename not in source_map:
                source_map[filename] = {
                    'filename': filename,
                    'functional_area': meta.get('functional_area', ''),
                    'sheets': set(),
                    'chunk_count': 0,
                    'max_relevance': 0
                }
            source_map[filename]['chunk_count'] += 1
            
            # Calculate relevance with keyword boost
            relevance = round((1 - dist) * 100, 1) if dist else 0
            
            # BOOST: If query keyword matches sheet name, boost relevance to ~100%
            sheet_name = str(meta.get('parent_section', '')).lower()
            query_keywords = message.lower().split()
            for keyword in query_keywords:
                if len(keyword) > 3 and keyword in sheet_name:
                    # Major boost for exact sheet name match (boost by 30 points, cap at 99)
                    relevance = min(99, relevance + 30)
                    logger.info(f"Boosted relevance for '{keyword}' → '{sheet_name}': {relevance}%")
                    break
            
            source_map[filename]['max_relevance'] = max(source_map[filename]['max_relevance'], relevance)
            sheet = meta.get('parent_section', '')
            if sheet:
                source_map[filename]['sheets'].add(sheet)
        
        sources = []
        for fname, info in source_map.items():
            sources.append({
                'filename': fname,
                'functional_area': info['functional_area'],
                'sheets': list(info['sheets']),
                'chunk_count': info['chunk_count'],
                'relevance': info['max_relevance']
            })
        sources.sort(key=lambda x: x['relevance'], reverse=True)
        
        # Classify query
        from utils.llm_orchestrator import classify_query
        query_type = classify_query(message, chunks)
        
        if query_type == 'config':
            update_job_status(job_id, 'processing', '⚡ Calling Claude (config)...', 40)
        else:
            update_job_status(job_id, 'processing', '🔵 Calling local LLM...', 40)
        
        time.sleep(0.5)  # Brief pause so user sees status
        
        # INJECT PERSONA: Enhance message with persona's personality
        # NOTE: This prepends persona context to the message for the LLM
        enhanced_message = f"""[SYSTEM: You are {persona.name}. {persona.system_prompt}]

User Question: {message}"""
        
        # Process with orchestrator (using enhanced message with persona)
        result = orchestrator.process_query(enhanced_message, chunks)
        
        if result.get('query_type') == 'employee' and result.get('sanitized'):
            update_job_status(job_id, 'processing', '🔒 Sanitizing PII...', 70)
            time.sleep(0.3)
        
        update_job_status(job_id, 'processing', '✅ Finalizing response...', 90)
        time.sleep(0.2)
        
        # Complete
        update_job_status(
            job_id, 'complete', 'Complete', 100,
            response=result.get("response", "No response generated"),
            sources=sources,
            chunks_found=len(documents),
            models_used=result.get("models_used", []),
            query_type=result.get("query_type", "unknown"),
            sanitized=result.get("sanitized", False)
        )
        
    except Exception as e:
        logger.error(f"Chat job error: {e}", exc_info=True)
        update_job_status(job_id, 'error', 'Error', 100, error=str(e))


@router.post("/chat/start")
async def chat_start(request: ChatRequest):
    """Start a chat job and return job_id for polling"""
    job_id = str(uuid.uuid4())
    
    # Initialize job
    chat_jobs[job_id] = {
        'job_id': job_id,
        'status': 'processing',
        'current_step': 'Starting...',
        'progress': 0,
        'created_at': time.time()
    }
    
    # Start background processing
    thread = threading.Thread(
        target=process_chat_job,
        args=(job_id, request.message, request.project, request.max_results or 30, request.persona or 'bessie')
    )
    thread.daemon = True
    thread.start()
    
    return {"job_id": job_id}


@router.get("/chat/status/{job_id}")
async def chat_status(job_id: str):
    """Get status of a chat job"""
    if job_id not in chat_jobs:
        raise HTTPException(404, "Job not found")
    
    return chat_jobs[job_id]


@router.delete("/chat/job/{job_id}")
async def delete_chat_job(job_id: str):
    """Clean up completed job"""
    if job_id in chat_jobs:
        del chat_jobs[job_id]
    return {"status": "deleted"}


# Keep the old endpoint for backward compatibility (non-streaming)
@router.post("/chat")
async def chat_legacy(request: ChatRequest):
    """Legacy chat endpoint - processes synchronously"""
    job_id = str(uuid.uuid4())
    chat_jobs[job_id] = {'job_id': job_id, 'status': 'processing', 'current_step': 'Processing...', 'progress': 0}
    
    # Process synchronously
    process_chat_job(job_id, request.message, request.project, request.max_results or 30, request.persona or 'bessie')
    
    # Wait for completion
    result = chat_jobs[job_id]
    del chat_jobs[job_id]
    
    if result['status'] == 'error':
        raise HTTPException(500, result.get('error', 'Unknown error'))
    
    return {
        "response": result.get('response'),
        "sources": result.get('sources', []),
        "chunks_found": result.get('chunks_found', 0),
        "models_used": result.get('models_used', []),
        "query_type": result.get('query_type', 'unknown'),
        "sanitized": result.get('sanitized', False)
    }


@router.get("/chat/health")
async def health():
    """Health check"""
    try:
        rag = RAGHandler()
        collection = rag.client.get_or_create_collection("documents")
        chunk_count = collection.count()
        
        llm_status = orchestrator.check_status()
        
        return {
            "status": "healthy",
            "chromadb_chunks": chunk_count,
            "llm": llm_status
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/chat/debug-chunks")
async def debug_chunks(
    search: str = "earnings",
    project: Optional[str] = None,
    n: int = 50
):
    """Debug: See what chunks exist for a search term"""
    try:
        rag = RAGHandler()
        collection = rag.client.get_collection("documents")
        
        query_embedding = rag.get_embedding(search)
        where_filter = {"project": project} if project else None
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )
        
        if not results or not results['documents'][0]:
            return {"message": "No chunks found", "total": 0}
        
        # Group by sheet
        sheets = {}
        for doc, meta, dist in zip(results['documents'][0], results['metadatas'][0], results['distances'][0]):
            sheet = meta.get('parent_section', 'Unknown')
            if sheet not in sheets:
                sheets[sheet] = {"count": 0, "samples": [], "avg_distance": 0}
            sheets[sheet]["count"] += 1
            sheets[sheet]["avg_distance"] += dist
            if len(sheets[sheet]["samples"]) < 2:
                sheets[sheet]["samples"].append({
                    "text": doc[:200] + "..." if len(doc) > 200 else doc,
                    "distance": round(dist, 3)
                })
        
        for sheet in sheets:
            sheets[sheet]["avg_distance"] = round(sheets[sheet]["avg_distance"] / sheets[sheet]["count"], 3)
        
        return {
            "search_term": search,
            "project": project,
            "total_chunks": len(results['documents'][0]),
            "sheets": sheets
        }
        
    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# PERSONA MANAGEMENT ENDPOINTS - Meet Bessie! 🐮
# ============================================================================

@router.get("/chat/personas")
async def list_personas():
    """Get all available personas"""
    try:
        pm = get_persona_manager()
        personas = pm.list_personas()
        
        return {
            "personas": personas,
            "count": len(personas),
            "default": "bessie"
        }
    except Exception as e:
        logger.error(f"Error listing personas: {e}")
        raise HTTPException(500, str(e))


@router.get("/chat/personas/{name}")
async def get_persona(name: str):
    """Get specific persona details"""
    try:
        pm = get_persona_manager()
        persona = pm.get_persona(name)
        
        return persona.to_dict()
    except Exception as e:
        logger.error(f"Error getting persona: {e}")
        raise HTTPException(500, str(e))


@router.post("/chat/personas")
async def create_persona(persona: PersonaCreate):
    """Create a new custom persona"""
    try:
        pm = get_persona_manager()
        new_persona = pm.create_persona(
            name=persona.name,
            icon=persona.icon,
            description=persona.description,
            system_prompt=persona.system_prompt,
            expertise=persona.expertise,
            tone=persona.tone
        )
        
        logger.info(f"[PERSONA] Created custom persona: {persona.name}")
        
        return {
            "status": "created",
            "persona": new_persona.to_dict()
        }
    except Exception as e:
        logger.error(f"Error creating persona: {e}")
        raise HTTPException(500, str(e))


@router.put("/chat/personas/{name}")
async def update_persona(name: str, updates: PersonaUpdate):
    """Update a custom persona"""
    try:
        pm = get_persona_manager()
        
        # Filter out None values
        update_dict = {k: v for k, v in updates.dict().items() if v is not None}
        
        persona = pm.update_persona(name, **update_dict)
        
        if not persona:
            raise HTTPException(404, f"Persona '{name}' not found or cannot be updated (built-in personas cannot be modified)")
        
        logger.info(f"[PERSONA] Updated custom persona: {name}")
        
        return {
            "status": "updated",
            "persona": persona.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating persona: {e}")
        raise HTTPException(500, str(e))


@router.delete("/chat/personas/{name}")
async def delete_persona(name: str):
    """Delete a custom persona (cannot delete built-in personas)"""
    try:
        pm = get_persona_manager()
        
        success = pm.delete_persona(name)
        
        if not success:
            raise HTTPException(404, f"Persona '{name}' not found or cannot be deleted (built-in personas cannot be deleted)")
        
        logger.info(f"[PERSONA] Deleted custom persona: {name}")
        
        return {"status": "deleted", "name": name}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting persona: {e}")
        raise HTTPException(500, str(e))


# ============================================================================
# STRUCTURED DATA ENDPOINTS - SQL Queries for Excel/CSV
# ============================================================================

@router.get("/chat/schema/{project}")
async def get_project_schema(project: str):
    """Get the data schema for a project (tables, columns, row counts)"""
    if not STRUCTURED_QUERIES_AVAILABLE:
        raise HTTPException(501, "Structured queries not available")
    
    try:
        handler = get_structured_handler()
        schema = handler.get_schema_for_project(project)
        
        return {
            "project": project,
            "tables": schema.get('tables', []),
            "table_count": len(schema.get('tables', []))
        }
    except Exception as e:
        logger.error(f"Error getting schema: {e}")
        raise HTTPException(500, str(e))


@router.get("/chat/tables")
async def list_all_tables():
    """List all tables across all projects"""
    if not STRUCTURED_QUERIES_AVAILABLE:
        raise HTTPException(501, "Structured queries not available")
    
    try:
        handler = get_structured_handler()
        
        # Query metadata table
        result = handler.conn.execute("""
            SELECT project, file_name, sheet_name, table_name, row_count
            FROM _schema_metadata
            ORDER BY project, file_name, sheet_name
        """).fetchall()
        
        tables = []
        for row in result:
            tables.append({
                'project': row[0],
                'file': row[1],
                'sheet': row[2],
                'table_name': row[3],
                'row_count': row[4]
            })
        
        return {
            "tables": tables,
            "total": len(tables)
        }
    except Exception as e:
        logger.error(f"Error listing tables: {e}")
        raise HTTPException(500, str(e))


@router.post("/chat/sql")
async def execute_sql_query(sql: str, project: Optional[str] = None):
    """Execute a raw SQL query (admin/debug use)"""
    if not STRUCTURED_QUERIES_AVAILABLE:
        raise HTTPException(501, "Structured queries not available")
    
    try:
        handler = get_structured_handler()
        rows, columns = handler.execute_query(sql)
        
        return {
            "columns": columns,
            "rows": rows[:1000],  # Limit results
            "total_rows": len(rows),
            "truncated": len(rows) > 1000
        }
    except Exception as e:
        logger.error(f"SQL execution error: {e}")
        raise HTTPException(400, f"SQL Error: {str(e)}")


@router.get("/chat/export/{filename}")
async def download_export(filename: str):
    """Download an exported file"""
    from fastapi.responses import FileResponse
    import os
    
    export_path = f"/data/exports/{filename}"
    
    if not os.path.exists(export_path):
        raise HTTPException(404, "Export file not found")
    
    return FileResponse(
        path=export_path,
        filename=filename,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' 
            if filename.endswith('.xlsx') else 'text/csv'
    )


@router.get("/chat/table-sample/{table_name}")
async def get_table_sample(table_name: str, limit: int = 10):
    """Get sample rows from a table"""
    if not STRUCTURED_QUERIES_AVAILABLE:
        raise HTTPException(501, "Structured queries not available")
    
    try:
        handler = get_structured_handler()
        rows = handler.get_table_sample(table_name, limit)
        
        return {
            "table_name": table_name,
            "sample": rows,
            "count": len(rows)
        }
    except Exception as e:
        logger.error(f"Error getting sample: {e}")
        raise HTTPException(500, str(e))


# ============================================================================
# DATA MANAGEMENT ENDPOINTS - Delete, Refresh, Compare
# ============================================================================

@router.delete("/chat/data/{project}/{file_name}")
async def delete_file_data(project: str, file_name: str, all_versions: bool = True):
    """
    Delete all data for a specific file.
    
    Use this to:
    - Remove outdated data
    - Refresh by deleting then re-uploading
    - Clean up test data
    """
    if not STRUCTURED_QUERIES_AVAILABLE:
        raise HTTPException(501, "Structured queries not available")
    
    try:
        handler = get_structured_handler()
        result = handler.delete_file(project, file_name, delete_all_versions=all_versions)
        
        logger.info(f"[DELETE] Removed {len(result['tables_deleted'])} tables for {project}/{file_name}")
        
        return {
            "status": "deleted",
            "project": project,
            "file_name": file_name,
            "tables_deleted": result['tables_deleted'],
            "versions_deleted": result['versions_deleted']
        }
    except Exception as e:
        logger.error(f"Error deleting file data: {e}")
        raise HTTPException(500, str(e))


@router.get("/chat/data/{project}/files")
async def list_project_files(project: str):
    """List all files in a project with version info"""
    if not STRUCTURED_QUERIES_AVAILABLE:
        raise HTTPException(501, "Structured queries not available")
    
    try:
        handler = get_structured_handler()
        files = handler.list_files(project)
        
        return {
            "project": project,
            "files": files,
            "count": len(files)
        }
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        raise HTTPException(500, str(e))


@router.get("/chat/data/{project}/{file_name}/versions")
async def get_file_versions(project: str, file_name: str):
    """Get all versions of a file"""
    if not STRUCTURED_QUERIES_AVAILABLE:
        raise HTTPException(501, "Structured queries not available")
    
    try:
        handler = get_structured_handler()
        versions = handler.get_file_versions(project, file_name)
        
        return {
            "project": project,
            "file_name": file_name,
            "versions": versions,
            "count": len(versions)
        }
    except Exception as e:
        logger.error(f"Error getting versions: {e}")
        raise HTTPException(500, str(e))


class CompareRequest(BaseModel):
    sheet_name: str
    key_column: str
    version1: Optional[int] = None
    version2: Optional[int] = None


@router.post("/chat/data/{project}/{file_name}/compare")
async def compare_file_versions(project: str, file_name: str, request: CompareRequest):
    """
    Compare two versions of a file to find changes.
    
    Returns:
    - added: Records in new version but not old
    - removed: Records in old version but not new  
    - changed: Records that exist in both but have different values
    
    Use cases:
    - "Show me new hires since last load"
    - "Who was terminated?"
    - "What earning codes changed?"
    """
    if not STRUCTURED_QUERIES_AVAILABLE:
        raise HTTPException(501, "Structured queries not available")
    
    try:
        handler = get_structured_handler()
        result = handler.compare_versions(
            project=project,
            file_name=file_name,
            sheet_name=request.sheet_name,
            key_column=request.key_column,
            version1=request.version1,
            version2=request.version2
        )
        
        if 'error' in result:
            raise HTTPException(400, result['error'])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing versions: {e}")
        raise HTTPException(500, str(e))


@router.get("/chat/data/encryption-status")
async def get_encryption_status():
    """Check if PII encryption is enabled"""
    if not STRUCTURED_QUERIES_AVAILABLE:
        raise HTTPException(501, "Structured queries not available")
    
    try:
        handler = get_structured_handler()
        
        return {
            "encryption_available": handler.encryptor.fernet is not None,
            "pii_patterns": [
                "ssn", "social_security", "tax_id", 
                "bank_account", "routing_number",
                "salary", "pay_rate", "dob", "birthdate"
            ],
            "note": "PII columns matching these patterns are automatically encrypted at rest"
        }
    except Exception as e:
        logger.error(f"Error checking encryption: {e}")
        raise HTTPException(500, str(e))


@router.post("/chat/data/reset-database")
async def reset_structured_database(confirm: bool = False):
    """
    Reset the entire structured data database.
    WARNING: This deletes ALL uploaded Excel/CSV data!
    
    Must pass confirm=true to execute.
    """
    if not STRUCTURED_QUERIES_AVAILABLE:
        raise HTTPException(501, "Structured queries not available")
    
    if not confirm:
        return {
            "warning": "This will DELETE ALL structured data (Excel/CSV uploads)!",
            "action_required": "Pass ?confirm=true to proceed",
            "example": "POST /api/chat/data/reset-database?confirm=true"
        }
    
    try:
        handler = get_structured_handler()
        result = handler.reset_database()
        
        if result.get('success'):
            logger.info(f"[RESET] Database reset complete - {len(result.get('tables_dropped', []))} tables dropped")
            return {
                "status": "reset_complete",
                "tables_dropped": result.get('tables_dropped', []),
                "message": "Database reset. You can now re-upload your files."
            }
        else:
            raise HTTPException(500, result.get('error', 'Reset failed'))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting database: {e}")
        raise HTTPException(500, str(e))
