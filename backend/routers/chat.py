"""
Chat Router - CLEAN PRODUCTION VERSION
======================================

ARCHITECTURE (Simple & Secure):
1. Find relevant tables (keyword matching)
2. SELECT * LIMIT 200 - get actual data
3. Scan data for PII
4. Sanitize if PII detected
5. Send data + question to Claude
6. Claude sees real data, answers correctly

ONE Claude call, not two. Simple. Works.

Author: XLR8 Team
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import threading
import uuid
import logging
import sys
import time
import re

sys.path.insert(0, '/app')
sys.path.insert(0, '/data')

from utils.rag_handler import RAGHandler
from utils.llm_orchestrator import LLMOrchestrator
from utils.persona_manager import get_persona_manager

# Import structured data handling
try:
    from utils.structured_data_handler import get_structured_handler
    STRUCTURED_QUERIES_AVAILABLE = True
except ImportError as e:
    STRUCTURED_QUERIES_AVAILABLE = False

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory job storage
chat_jobs: Dict[str, Dict[str, Any]] = {}


# =============================================================================
# PII DETECTION & SANITIZATION
# =============================================================================

PII_COLUMN_PATTERNS = [
    r'ssn', r'social.*security', r'tax.*id',
    r'salary', r'pay.*rate', r'wage', r'compensation', r'hourly.*rate', r'annual.*pay',
    r'bank.*account', r'routing', r'account.*num',
    r'dob', r'birth.*date', r'date.*birth',
    r'email', r'phone', r'address', r'street', r'city', r'zip',
    r'first.*name', r'last.*name', r'full.*name', r'employee.*name'
]


def detect_pii_in_data(data: str, columns: List[str] = None) -> Dict[str, Any]:
    """Scan DATA content for PII patterns."""
    detected = {
        'has_pii': False,
        'pii_types': [],
        'column_flags': []
    }
    
    if not data:
        return detected
    
    data_lower = data.lower()
    
    # Check column names for PII indicators
    if columns:
        for col in columns:
            col_lower = str(col).lower()
            for pattern in PII_COLUMN_PATTERNS:
                if re.search(pattern, col_lower):
                    detected['column_flags'].append(col)
                    detected['has_pii'] = True
    
    # Check for SSN patterns
    if re.search(r'\b\d{3}-\d{2}-\d{4}\b', data):
        detected['pii_types'].append('ssn')
        detected['has_pii'] = True
    
    # Check for salary patterns
    if re.search(r'\$\s*\d{2,3},?\d{3}', data):
        detected['pii_types'].append('compensation')
        detected['has_pii'] = True
    
    # Check for email
    if re.search(r'\b[\w\.-]+@[\w\.-]+\.\w{2,}\b', data):
        detected['pii_types'].append('email')
        detected['has_pii'] = True
    
    # Check for phone
    if re.search(r'\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b', data):
        detected['pii_types'].append('phone')
        detected['has_pii'] = True
    
    detected['pii_types'] = list(set(detected['pii_types']))
    return detected


def sanitize_pii(context: str) -> str:
    """Sanitize PII from context before sending to external API."""
    sanitized = context
    
    # SSN
    sanitized = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN-REDACTED]', sanitized)
    
    # Salary values
    sanitized = re.sub(r'\$\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?', '[SALARY-REDACTED]', sanitized)
    
    # Phone
    sanitized = re.sub(r'\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b', '[PHONE-REDACTED]', sanitized)
    
    # Email
    sanitized = re.sub(r'\b[\w\.-]+@[\w\.-]+\.\w{2,}\b', '[EMAIL-REDACTED]', sanitized)
    
    return sanitized


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class ChatRequest(BaseModel):
    message: str
    project: Optional[str] = None
    max_results: Optional[int] = 30
    persona: Optional[str] = 'bessie'


class ChatStartRequest(BaseModel):
    message: str
    project: Optional[str] = None
    max_results: Optional[int] = 50
    persona: Optional[str] = 'bessie'


# =============================================================================
# JOB STATUS MANAGEMENT
# =============================================================================

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


# =============================================================================
# DATA DECRYPTION
# =============================================================================

def decrypt_results(rows: list, handler) -> list:
    """Decrypt any encrypted values in query results."""
    if not rows:
        return rows
    
    try:
        encryptor = handler.encryptor
        if not encryptor or not encryptor.fernet:
            return rows
        
        decrypted_rows = []
        for row in rows:
            decrypted_row = {}
            for key, value in row.items():
                if isinstance(value, str) and value.startswith('ENC:'):
                    try:
                        decrypted_row[key] = encryptor.decrypt(value)
                    except Exception:
                        decrypted_row[key] = '[encrypted]'
                else:
                    decrypted_row[key] = value
            decrypted_rows.append(decrypted_row)
        
        return decrypted_rows
    except Exception as e:
        logger.warning(f"Decryption error: {e}")
        return rows


# =============================================================================
# MAIN CHAT PROCESSING - SIMPLE & SECURE
# =============================================================================

def process_chat_job(job_id: str, message: str, project: Optional[str], max_results: int, persona_name: str = 'bessie'):
    """
    CLEAN Chat Processing Pipeline
    ===============================
    
    Simple approach that works:
    1. Find relevant tables (keyword matching)
    2. SELECT * LIMIT 200 - get actual data
    3. Scan for PII, sanitize if needed
    4. Send data + question to Claude
    5. Claude sees real data, answers correctly
    
    ONE Claude call. Simple. Secure. Works.
    """
    try:
        # =====================================================================
        # STEP 1: INITIALIZE
        # =====================================================================
        pm = get_persona_manager()
        persona = pm.get_persona(persona_name)
        logger.info(f"[PERSONA] Using: {persona.name} {persona.icon}")
        
        sql_results_list = []
        rag_chunks = []
        all_columns = []
        
        # =====================================================================
        # STEP 2: GATHER DATA - Self-Healing Table Selection
        # =====================================================================
        if STRUCTURED_QUERIES_AVAILABLE:
            update_job_status(job_id, 'processing', '📊 Analyzing available data...', 10)
            
            try:
                handler = get_structured_handler()
                schema = handler.get_schema_for_project(project) if project else handler.get_schema_for_project(None)
                tables_list = schema.get('tables', [])
                
                if tables_list:
                    # SELF-HEALING: Build table summaries for Claude to choose from
                    table_summaries = []
                    table_lookup = {}  # Map index to table info
                    
                    for idx, table_info in enumerate(tables_list):
                        table_name = table_info.get('table_name', '')
                        sheet_name = table_info.get('sheet', '')
                        file_name = table_info.get('file', '')
                        columns = table_info.get('columns', [])
                        row_count = table_info.get('row_count', 0)
                        
                        # Get column names
                        if columns and isinstance(columns[0], dict):
                            col_names = [c.get('name', str(c)) for c in columns]
                        else:
                            col_names = [str(c) for c in columns]
                        
                        # Get 2 sample rows to show data structure
                        sample_preview = ""
                        try:
                            sample_sql = f'SELECT * FROM "{table_name}" LIMIT 2'
                            sample_rows, _ = handler.execute_query(sample_sql)
                            if sample_rows:
                                # Show just key-value pairs, truncated
                                for row in sample_rows[:2]:
                                    preview = {k: str(v)[:25] for k, v in list(row.items())[:6]}
                                    sample_preview += f"    {preview}\n"
                        except:
                            pass
                        
                        summary = f"""[{idx}] {file_name} → {sheet_name}
  Rows: {row_count}, Columns: {', '.join(col_names[:10])}{'...' if len(col_names) > 10 else ''}
{sample_preview}"""
                        
                        table_summaries.append(summary)
                        table_lookup[idx] = table_info
                    
                    # SELF-HEALING: Ask Claude which table(s) to use
                    update_job_status(job_id, 'processing', '🧠 Identifying best data source...', 20)
                    
                    selection_prompt = f"""Given this question: "{message}"

Which table(s) should I query? Here are the available tables with sample data:

{chr(10).join(table_summaries)}

Reply with ONLY the table number(s) that best answer the question, comma-separated.
For example: "0" or "0,2" or "3"

If asking about employees/people/headcount, pick tables with actual employee records (not config/validation).
If asking about earnings/deductions/codes, pick configuration tables.

Table number(s):"""

                    orchestrator = LLMOrchestrator()
                    
                    try:
                        # Quick Claude call to pick tables
                        import anthropic
                        client = anthropic.Anthropic(api_key=orchestrator.claude_api_key)
                        
                        selection_response = client.messages.create(
                            model="claude-sonnet-4-20250514",
                            max_tokens=50,
                            messages=[{"role": "user", "content": selection_prompt}]
                        )
                        
                        selection_text = selection_response.content[0].text.strip()
                        logger.info(f"[TABLE-SELECT] Claude chose: {selection_text}")
                        
                        # Parse selected indices
                        selected_indices = []
                        for part in selection_text.replace(' ', '').split(','):
                            try:
                                idx = int(part.strip('[]()'))
                                if idx in table_lookup:
                                    selected_indices.append(idx)
                            except:
                                pass
                        
                        # Fallback: if no valid selection, use first table
                        if not selected_indices and table_lookup:
                            selected_indices = [0]
                            logger.warning("[TABLE-SELECT] No valid selection, using first table")
                        
                    except Exception as e:
                        logger.warning(f"[TABLE-SELECT] Claude selection failed: {e}, using keyword fallback")
                        # Fallback to keyword matching
                        query_lower = message.lower()
                        selected_indices = []
                        for idx, table_info in table_lookup.items():
                            file_lower = table_info.get('file', '').lower()
                            sheet_lower = table_info.get('sheet', '').lower()
                            if any(term in file_lower or term in sheet_lower for term in query_lower.split() if len(term) > 3):
                                selected_indices.append(idx)
                        if not selected_indices:
                            selected_indices = list(table_lookup.keys())[:2]
                    
                    # Query selected tables
                    update_job_status(job_id, 'processing', '📊 Retrieving data...', 35)
                    
                    for idx in selected_indices[:3]:  # Max 3 tables
                        table_info = table_lookup[idx]
                        table_name = table_info.get('table_name', '')
                        sheet_name = table_info.get('sheet', '')
                        file_name = table_info.get('file', '')
                        
                        try:
                            sql = f'SELECT * FROM "{table_name}" LIMIT 200'
                            rows, cols = handler.execute_query(sql)
                            all_columns.extend(cols)
                            
                            if rows:
                                decrypted = decrypt_results(rows, handler)
                                sql_results_list.append({
                                    'source_file': file_name,
                                    'sheet': sheet_name,
                                    'table': table_name,
                                    'columns': cols,
                                    'data': decrypted[:100],
                                    'total_rows': len(rows)
                                })
                                logger.info(f"[SQL] Selected table {idx}: {sheet_name} - {len(rows)} rows")
                        except Exception as e:
                            logger.warning(f"[SQL] Failed to query {table_name}: {e}")
                    
            except Exception as e:
                logger.warning(f"[SQL] Handler error: {e}")
        
        # =====================================================================
        # STEP 3: GATHER RAG DATA
        # =====================================================================
        update_job_status(job_id, 'processing', '🔍 Searching documents...', 30)
        
        try:
            rag = RAGHandler()
            collection = rag.client.get_or_create_collection(name="documents")
            
            where_filter = None
            if project and project not in ['', 'all', 'All Projects']:
                where_filter = {"project": project}
            
            rag_response = collection.query(
                query_texts=[message],
                n_results=min(max_results, 10),
                where=where_filter
            )
            
            if rag_response and rag_response.get('documents') and rag_response['documents'][0]:
                rag_chunks = rag_response['documents'][0]
                logger.info(f"[RAG] Found {len(rag_chunks)} chunks")
                
        except Exception as e:
            logger.warning(f"[RAG] Search error: {e}")
        
        # =====================================================================
        # STEP 4: BUILD CONTEXT
        # =====================================================================
        update_job_status(job_id, 'processing', '🧠 Analyzing data...', 50)
        
        context_parts = []
        sources = []
        
        for result in sql_results_list:
            data_text = f"Source: {result['source_file']} → {result['sheet']}\n"
            data_text += f"Columns: {', '.join(result['columns'])}\n"
            data_text += f"Total rows in table: {result['total_rows']}\n\nData:\n"
            
            for row in result['data'][:50]:  # Limit to 50 rows in context
                row_str = " | ".join(f"{k}: {v}" for k, v in row.items())
                data_text += f"  {row_str}\n"
            
            context_parts.append(data_text)
            
            sources.append({
                'filename': result['source_file'],
                'sheet': result['sheet'],
                'type': 'structured_data',
                'rows': result['total_rows'],
                'relevance': 95
            })
        
        for i, chunk in enumerate(rag_chunks[:5]):
            context_parts.append(f"Document {i+1}:\n{chunk}")
        
        if rag_chunks:
            sources.append({
                'filename': 'Document Search',
                'type': 'rag',
                'chunks': len(rag_chunks),
                'relevance': 80
            })
        
        # =====================================================================
        # STEP 5: PII DETECTION & SANITIZATION
        # =====================================================================
        full_context = '\n\n'.join(context_parts)
        
        pii_detection = detect_pii_in_data(full_context, all_columns)
        
        if pii_detection['has_pii']:
            logger.warning(f"[PII] Detected: {pii_detection['pii_types']}, columns: {pii_detection['column_flags']}")
            update_job_status(job_id, 'processing', '🔒 Securing sensitive data...', 60)
            full_context = sanitize_pii(full_context)
            sanitized = True
        else:
            logger.info("[PII] No PII detected")
            sanitized = False
        
        # =====================================================================
        # STEP 6: SEND TO CLAUDE (ONE CALL)
        # =====================================================================
        if context_parts:
            update_job_status(job_id, 'processing', '✨ Generating response...', 70)
            
            # Build chunks for orchestrator
            orchestrator_chunks = [{
                'document': full_context,
                'metadata': {
                    'filename': 'Query Results',
                    'type': 'combined_data',
                    'pii_sanitized': sanitized
                }
            }]
            
            orchestrator = LLMOrchestrator()
            result = orchestrator.process_query(message, orchestrator_chunks)
            
            response = result.get('response', 'I found data but had trouble analyzing it.')
            
            if sanitized and any(pt in pii_detection['pii_types'] for pt in ['ssn', 'compensation']):
                response += "\n\n*Note: Some sensitive values have been protected in this response.*"
            
            update_job_status(
                job_id, 'complete', 'Complete', 100,
                response=response,
                sources=sources,
                chunks_found=len(sql_results_list) + len(rag_chunks),
                models_used=result.get('models_used', ['claude']) + (['duckdb'] if sql_results_list else []),
                query_type='data_analysis',
                sanitized=sanitized,
                pii_detected=pii_detection['pii_types'] if pii_detection['has_pii'] else []
            )
            return
        
        # =====================================================================
        # STEP 7: FALLBACK - No data found
        # =====================================================================
        update_job_status(job_id, 'processing', '🔍 Broader search...', 70)
        
        try:
            rag = RAGHandler()
            collection = rag.client.get_or_create_collection(name="documents")
            
            rag_response = collection.query(
                query_texts=[message],
                n_results=20,
                where=None
            )
            
            if rag_response and rag_response.get('documents') and rag_response['documents'][0]:
                chunks = rag_response['documents'][0]
                fallback_context = '\n\n'.join(chunks[:10])
                
                # Check & sanitize fallback data too
                fallback_pii = detect_pii_in_data(fallback_context, [])
                if fallback_pii['has_pii']:
                    fallback_context = sanitize_pii(fallback_context)
                
                orchestrator_chunks = [{'document': fallback_context, 'metadata': {'type': 'fallback'}}]
                
                orchestrator = LLMOrchestrator()
                result = orchestrator.process_query(message, orchestrator_chunks)
                
                update_job_status(
                    job_id, 'complete', 'Complete', 100,
                    response=result.get('response', 'Could not find relevant information.'),
                    sources=[{'filename': 'Broad Search', 'type': 'rag', 'chunks': len(chunks)}],
                    chunks_found=len(chunks),
                    models_used=result.get('models_used', ['claude']),
                    query_type='fallback',
                    sanitized=fallback_pii['has_pii']
                )
                return
                
        except Exception as e:
            logger.error(f"[FALLBACK] Error: {e}")
        
        # No data at all
        update_job_status(
            job_id, 'complete', 'Complete', 100,
            response="I couldn't find relevant data. Please ensure data has been uploaded for this project.",
            sources=[],
            chunks_found=0,
            models_used=['none'],
            query_type='no_data',
            sanitized=False
        )
        
    except Exception as e:
        logger.error(f"[CHAT] Fatal error: {e}", exc_info=True)
        update_job_status(
            job_id, 'error', 'Error', 100,
            error=str(e),
            response=f"An error occurred: {str(e)}"
        )


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.get("/chat/models")
async def get_available_models():
    """Get available AI models"""
    return {
        "models": [
            {"id": "claude-3-sonnet", "name": "Claude 3 Sonnet", "description": "Fast, balanced"},
            {"id": "claude-3-opus", "name": "Claude 3 Opus", "description": "Most capable"}
        ],
        "default": "claude-3-sonnet"
    }


@router.post("/chat/start")
async def start_chat(request: ChatStartRequest):
    """Start async chat processing job"""
    job_id = str(uuid.uuid4())
    
    chat_jobs[job_id] = {
        'status': 'starting',
        'current_step': '🚀 Starting...',
        'progress': 0,
        'created_at': time.time()
    }
    
    thread = threading.Thread(
        target=process_chat_job,
        args=(job_id, request.message, request.project, request.max_results or 50, request.persona or 'bessie')
    )
    thread.daemon = True
    thread.start()
    
    return {"job_id": job_id, "status": "starting"}


@router.get("/chat/status/{job_id}")
async def get_chat_status(job_id: str):
    """Get job status"""
    if job_id not in chat_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return chat_jobs[job_id]


@router.delete("/chat/job/{job_id}")
async def cancel_chat_job(job_id: str):
    """Cancel a job"""
    if job_id in chat_jobs:
        del chat_jobs[job_id]
        return {"status": "cancelled"}
    raise HTTPException(status_code=404, detail="Job not found")


@router.post("/chat")
async def chat_sync(request: ChatRequest):
    """Synchronous chat"""
    job_id = str(uuid.uuid4())
    chat_jobs[job_id] = {'status': 'processing', 'progress': 0}
    process_chat_job(job_id, request.message, request.project, request.max_results or 30, request.persona or 'bessie')
    return chat_jobs.get(job_id, {'error': 'Job failed'})


@router.get("/chat/health")
async def chat_health():
    """Health check"""
    return {
        "status": "healthy",
        "structured_queries": STRUCTURED_QUERIES_AVAILABLE,
        "pii_protection": "enabled",
        "active_jobs": len(chat_jobs)
    }


# =============================================================================
# PERSONA ENDPOINTS
# =============================================================================

@router.get("/chat/personas")
async def list_personas():
    try:
        pm = get_persona_manager()
        personas = pm.list_personas()
        return {"personas": personas, "count": len(personas), "default": "bessie"}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/chat/personas/{name}")
async def get_persona(name: str):
    try:
        pm = get_persona_manager()
        persona = pm.get_persona(name)
        return persona.to_dict() if persona else None
    except Exception as e:
        raise HTTPException(404, f"Persona '{name}' not found")


@router.post("/chat/personas")
async def create_persona(request: Request):
    try:
        data = await request.json()
        pm = get_persona_manager()
        persona = pm.create_persona(
            name=data['name'],
            icon=data.get('icon', '🤖'),
            description=data.get('description', ''),
            system_prompt=data.get('system_prompt', ''),
            expertise=data.get('expertise', []),
            tone=data.get('tone', 'Professional')
        )
        return {"success": True, "persona": persona.to_dict()}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.put("/chat/personas/{name}")
async def update_persona(name: str, request: Request):
    try:
        data = await request.json()
        pm = get_persona_manager()
        persona = pm.update_persona(name, **data)
        if persona:
            return {"success": True, "persona": persona.to_dict()}
        raise HTTPException(404, f"Persona '{name}' not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.delete("/chat/personas/{name}")
async def delete_persona(name: str):
    try:
        pm = get_persona_manager()
        if name.lower() in ['bessie', 'analyst', 'consultant']:
            raise HTTPException(400, "Cannot delete default personas")
        success = pm.delete_persona(name)
        if success:
            return {"success": True}
        raise HTTPException(404, f"Persona '{name}' not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


# =============================================================================
# DATA ENDPOINTS
# =============================================================================

@router.get("/chat/schema/{project}")
async def get_project_schema(project: str):
    if not STRUCTURED_QUERIES_AVAILABLE:
        return {"tables": [], "error": "Not available"}
    try:
        handler = get_structured_handler()
        return handler.get_schema_for_project(project)
    except Exception as e:
        return {"tables": [], "error": str(e)}


@router.get("/chat/tables")
async def list_all_tables():
    if not STRUCTURED_QUERIES_AVAILABLE:
        return {"tables": []}
    try:
        handler = get_structured_handler()
        result = handler.conn.execute("""
            SELECT DISTINCT table_name FROM information_schema.tables WHERE table_schema = 'main'
        """).fetchall()
        return {"tables": [row[0] for row in result]}
    except Exception as e:
        return {"tables": [], "error": str(e)}


@router.post("/chat/sql")
async def execute_sql(request: Request):
    if not STRUCTURED_QUERIES_AVAILABLE:
        raise HTTPException(503, "Not available")
    try:
        data = await request.json()
        sql = data.get('sql', '')
        if not sql:
            raise HTTPException(400, "SQL required")
        handler = get_structured_handler()
        rows, columns = handler.execute_query(sql)
        decrypted = decrypt_results(rows, handler)
        return {"columns": columns, "rows": decrypted[:1000], "total_rows": len(rows)}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/chat/table-sample/{table_name}")
async def get_table_sample(table_name: str, limit: int = 100):
    if not STRUCTURED_QUERIES_AVAILABLE:
        raise HTTPException(503, "Not available")
    try:
        handler = get_structured_handler()
        rows = handler.get_table_sample(table_name, limit)
        return {"rows": rows, "count": len(rows)}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.delete("/chat/data/{project}/{file_name}")
async def delete_data_file(project: str, file_name: str, all_versions: bool = False):
    if not STRUCTURED_QUERIES_AVAILABLE:
        raise HTTPException(503, "Not available")
    try:
        handler = get_structured_handler()
        result = handler.delete_file(project, file_name, delete_all_versions=all_versions)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/chat/data/{project}/files")
async def list_project_files(project: str):
    if not STRUCTURED_QUERIES_AVAILABLE:
        return {"files": []}
    try:
        handler = get_structured_handler()
        files = handler.list_files(project)
        return {"files": files}
    except Exception as e:
        return {"files": [], "error": str(e)}


@router.post("/chat/data/reset-database")
async def reset_database():
    if not STRUCTURED_QUERIES_AVAILABLE:
        raise HTTPException(503, "Not available")
    try:
        handler = get_structured_handler()
        result = handler.reset_database()
        logger.warning("⚠️ Database RESET!")
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/chat/debug-chunks")
async def debug_chunks(search: str = "earnings", project: Optional[str] = None, n: int = 50):
    try:
        rag = RAGHandler()
        collection = rag.client.get_or_create_collection(name="documents")
        where_filter = {"project": project} if project else None
        results = collection.query(query_texts=[search], n_results=n, where=where_filter, include=["documents", "metadatas", "distances"])
        if not results or not results['documents'][0]:
            return {"message": "No chunks found", "total": 0}
        return {"search_term": search, "total_chunks": len(results['documents'][0])}
    except Exception as e:
        return {"error": str(e)}


@router.get("/chat/export/{filename}")
async def download_export(filename: str):
    from fastapi.responses import FileResponse
    import os
    export_path = f"/data/exports/{filename}"
    if not os.path.exists(export_path):
        raise HTTPException(404, "Not found")
    return FileResponse(path=export_path, filename=filename)


@router.get("/chat/data/{project}/{file_name}/versions")
async def get_file_versions(project: str, file_name: str):
    if not STRUCTURED_QUERIES_AVAILABLE:
        raise HTTPException(503, "Not available")
    try:
        handler = get_structured_handler()
        versions = handler.get_file_versions(project, file_name)
        return {"versions": versions}
    except Exception as e:
        raise HTTPException(500, str(e))


class CompareRequest(BaseModel):
    sheet_name: str
    key_column: str
    version1: Optional[int] = None
    version2: Optional[int] = None


@router.post("/chat/data/{project}/{file_name}/compare")
async def compare_file_versions(project: str, file_name: str, request: CompareRequest):
    if not STRUCTURED_QUERIES_AVAILABLE:
        raise HTTPException(503, "Not available")
    try:
        handler = get_structured_handler()
        result = handler.compare_versions(
            project=project, file_name=file_name, sheet_name=request.sheet_name,
            key_column=request.key_column, version1=request.version1, version2=request.version2
        )
        if 'error' in result:
            raise HTTPException(400, result['error'])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/chat/data/encryption-status")
async def get_encryption_status():
    if not STRUCTURED_QUERIES_AVAILABLE:
        raise HTTPException(503, "Not available")
    try:
        handler = get_structured_handler()
        return {
            "encryption_available": handler.encryptor.fernet is not None,
            "pii_detection": "enabled"
        }
    except Exception as e:
        raise HTTPException(500, str(e))
