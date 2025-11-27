"""
Chat Router - SELF-HEALING with FULL INSTRUMENTATION
=====================================================

Every step logged. No silent failures. Production ready.

Author: XLR8 Team
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import threading
import uuid
import logging
import sys
import time
import re
import traceback
import io

sys.path.insert(0, '/app')
sys.path.insert(0, '/data')

from utils.rag_handler import RAGHandler
from utils.llm_orchestrator import LLMOrchestrator
from utils.persona_manager import get_persona_manager

# Import structured data handling
try:
    from utils.structured_data_handler import get_structured_handler
    STRUCTURED_QUERIES_AVAILABLE = True
    logging.getLogger(__name__).info("✅ Structured data handler loaded")
except ImportError as e:
    STRUCTURED_QUERIES_AVAILABLE = False
    logging.getLogger(__name__).warning(f"❌ Structured data handler NOT available: {e}")

logger = logging.getLogger(__name__)

router = APIRouter()

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
    detected = {'has_pii': False, 'pii_types': [], 'column_flags': []}
    
    if not data:
        return detected
    
    # Check column names
    if columns:
        for col in columns:
            col_lower = str(col).lower()
            for pattern in PII_COLUMN_PATTERNS:
                if re.search(pattern, col_lower):
                    detected['column_flags'].append(col)
                    detected['has_pii'] = True
    
    # Check data patterns
    if re.search(r'\b\d{3}-\d{2}-\d{4}\b', data):
        detected['pii_types'].append('ssn')
        detected['has_pii'] = True
    if re.search(r'\$\s*\d{2,3},?\d{3}', data):
        detected['pii_types'].append('compensation')
        detected['has_pii'] = True
    if re.search(r'\b[\w\.-]+@[\w\.-]+\.\w{2,}\b', data):
        detected['pii_types'].append('email')
        detected['has_pii'] = True
    if re.search(r'\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b', data):
        detected['pii_types'].append('phone')
        detected['has_pii'] = True
    
    detected['pii_types'] = list(set(detected['pii_types']))
    return detected


def sanitize_pii(context: str) -> str:
    """Sanitize PII from context."""
    sanitized = context
    sanitized = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN-REDACTED]', sanitized)
    sanitized = re.sub(r'\$\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?', '[SALARY-REDACTED]', sanitized)
    sanitized = re.sub(r'\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b', '[PHONE-REDACTED]', sanitized)
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


def update_job_status(job_id: str, status: str, step: str, progress: int, **kwargs):
    if job_id in chat_jobs:
        chat_jobs[job_id].update({'status': status, 'current_step': step, 'progress': progress, **kwargs})
        logger.info(f"[JOB {job_id[:8]}] {step} ({progress}%)")


def decrypt_results(rows: list, handler) -> list:
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
                    except:
                        decrypted_row[key] = '[encrypted]'
                else:
                    decrypted_row[key] = value
            decrypted_rows.append(decrypted_row)
        return decrypted_rows
    except Exception as e:
        logger.warning(f"[DECRYPT] Error: {e}")
        return rows


# =============================================================================
# MAIN PROCESSING - SELF-HEALING WITH FULL LOGGING
# =============================================================================

def process_chat_job(job_id: str, message: str, project: Optional[str], max_results: int, persona_name: str = 'bessie'):
    """
    Self-Healing Chat Pipeline - FULLY INSTRUMENTED
    ================================================
    
    Flow:
    1. Get schema, build table summaries
    2. Ask Claude to pick best table(s)  
    3. Query selected tables
    4. Detect & sanitize PII
    5. Send to Claude for answer
    
    Every step logged. No silent failures.
    """
    logger.warning(f"{'='*60}")
    logger.warning(f"[START] Job {job_id[:8]} | Query: {message[:50]}...")
    logger.warning(f"[START] Project: {project} | Persona: {persona_name}")
    logger.warning(f"{'='*60}")
    
    try:
        # =====================================================================
        # STEP 1: INITIALIZE
        # =====================================================================
        logger.warning("[STEP 1] Initializing...")
        
        pm = get_persona_manager()
        persona = pm.get_persona(persona_name)
        logger.warning(f"[STEP 1] Persona loaded: {persona.name} {persona.icon}")
        
        sql_results_list = []
        rag_chunks = []
        all_columns = []
        
        # =====================================================================
        # STEP 2: GET SCHEMA & BUILD TABLE SUMMARIES
        # =====================================================================
        logger.warning(f"[STEP 2] STRUCTURED_QUERIES_AVAILABLE = {STRUCTURED_QUERIES_AVAILABLE}")
        
        if STRUCTURED_QUERIES_AVAILABLE:
            update_job_status(job_id, 'processing', '📊 Loading schema...', 10)
            
            try:
                logger.warning("[STEP 2] Getting structured handler...")
                handler = get_structured_handler()
                logger.warning("[STEP 2] Handler obtained, getting schema...")
                
                schema = handler.get_schema_for_project(project) if project else handler.get_schema_for_project(None)
                tables_list = schema.get('tables', [])
                
                logger.warning(f"[STEP 2] Schema returned {len(tables_list)} tables")
                
                if not tables_list:
                    logger.warning("[STEP 2] ⚠️ NO TABLES IN SCHEMA!")
                    try:
                        direct_result = handler.conn.execute("""
                            SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'
                        """).fetchall()
                        logger.warning(f"[STEP 2] Direct DuckDB found {len(direct_result)} tables: {[r[0] for r in direct_result[:5]]}")
                    except Exception as ddb_e:
                        logger.error(f"[STEP 2] Direct DuckDB query failed: {ddb_e}")
                
                if tables_list:
                    logger.warning("[STEP 2] Building table summaries...")
                    table_summaries = []
                    table_lookup = {}
                    
                    for idx, table_info in enumerate(tables_list):
                        table_name = table_info.get('table_name', '')
                        sheet_name = table_info.get('sheet', '')
                        file_name = table_info.get('file', '')
                        columns = table_info.get('columns', [])
                        row_count = table_info.get('row_count', 0)
                        
                        logger.warning(f"[STEP 2] Table {idx}: {file_name} → {sheet_name} ({row_count} rows)")
                        
                        if columns and isinstance(columns[0], dict):
                            col_names = [c.get('name', str(c)) for c in columns]
                        else:
                            col_names = [str(c) for c in columns]
                        
                        sample_preview = ""
                        try:
                            sample_sql = f'SELECT * FROM "{table_name}" LIMIT 2'
                            sample_rows, _ = handler.execute_query(sample_sql)
                            if sample_rows:
                                for row in sample_rows[:2]:
                                    preview = {k: str(v)[:20] for k, v in list(row.items())[:5]}
                                    sample_preview += f"    {preview}\n"
                        except Exception as sample_e:
                            logger.warning(f"[STEP 2] Sample query failed for {table_name}: {sample_e}")
                        
                        summary = f"[{idx}] {file_name} → {sheet_name}\n  Rows: {row_count}, Cols: {', '.join(col_names[:8])}{'...' if len(col_names) > 8 else ''}\n{sample_preview}"
                        table_summaries.append(summary)
                        table_lookup[idx] = table_info
                    
                    logger.warning(f"[STEP 2] Built {len(table_summaries)} summaries")
                    
                    # =========================================================
                    # STEP 3: ASK CLAUDE TO PICK TABLES
                    # =========================================================
                    update_job_status(job_id, 'processing', '🧠 Selecting best data source...', 20)
                    logger.warning("[STEP 3] Preparing Claude table selection...")
                    
                    selection_prompt = f"""Question: "{message}"

TASK: Pick the table number(s) that contain data to answer this question.

KEY DISTINCTION:
- Tables with "Configuration", "Validation", "Reasons", "Setup", "Plans" = CODE DEFINITIONS (not employee records)
- Tables with "Company", "Personal", "Conversion", "Employee" in Employee Conversion file = ACTUAL EMPLOYEE DATA

For questions about ACTUAL PEOPLE (list employees, count active, who is on leave):
→ Pick tables from "Employee Conversion" file (Company, Personal)

For questions about CODE MEANINGS (what does code X mean):
→ Pick Configuration/Validation tables

Available tables:
{chr(10).join(table_summaries)}

RESPOND WITH ONLY THE TABLE NUMBERS. NO EXPLANATION. NO REASONING.
Just the number(s) like: 47,53

Table numbers:"""
                    
                    logger.warning(f"[STEP 3] Selection prompt length: {len(selection_prompt)} chars")
                    
                    selected_indices = []
                    
                    try:
                        logger.warning("[STEP 3] Creating Anthropic client...")
                        import anthropic
                        
                        orchestrator = LLMOrchestrator()
                        if not orchestrator.claude_api_key:
                            raise ValueError("No Claude API key available")
                        
                        client = anthropic.Anthropic(api_key=orchestrator.claude_api_key)
                        
                        logger.warning("[STEP 3] Calling Claude for table selection...")
                        selection_response = client.messages.create(
                            model="claude-sonnet-4-20250514",
                            max_tokens=50,
                            messages=[{"role": "user", "content": selection_prompt}]
                        )
                        
                        selection_text = selection_response.content[0].text.strip()
                        logger.warning(f"[STEP 3] ✅ Claude responded: '{selection_text[:200]}'")
                        
                        # Try simple comma-split first
                        for part in selection_text.replace(' ', '').split(','):
                            try:
                                idx = int(part.strip('[]()'))
                                if idx in table_lookup:
                                    selected_indices.append(idx)
                                    logger.warning(f"[STEP 3] Selected table index: {idx}")
                            except ValueError:
                                pass
                        
                        # If simple parsing failed, try to extract any numbers from the response
                        if not selected_indices:
                            numbers = re.findall(r'\b(\d{1,2})\b', selection_text)
                            for num_str in numbers:
                                idx = int(num_str)
                                if idx in table_lookup:
                                    selected_indices.append(idx)
                                    logger.warning(f"[STEP 3] Extracted table index: {idx}")
                        
                        # If still nothing, use smart fallback for employee questions
                        if not selected_indices:
                            logger.warning(f"[STEP 3] Could not parse numbers, checking for employee query...")
                            query_lower = message.lower()
                            
                            # For employee-related questions, find employee data tables
                            if any(kw in query_lower for kw in ['employee', 'active', 'leave', 'terminated', 'staff', 'worker', 'list', 'count', 'how many', 'who']):
                                for idx, table_info in table_lookup.items():
                                    file_lower = table_info.get('file', '').lower()
                                    sheet_lower = table_info.get('sheet', '').lower()
                                    
                                    # Prioritize Employee Conversion Company/Personal tables
                                    if 'employee_conversion' in file_lower or 'conversion' in file_lower:
                                        if 'company' in sheet_lower or 'personal' in sheet_lower:
                                            selected_indices.append(idx)
                                            logger.warning(f"[STEP 3] Smart fallback selected: {idx} ({sheet_lower})")
                            
                            if not selected_indices:
                                selected_indices = [0]
                                logger.warning(f"[STEP 3] Final fallback to table 0")
                            
                    except Exception as claude_e:
                        logger.error(f"[STEP 3] ❌ Claude selection FAILED: {claude_e}")
                        logger.error(f"[STEP 3] Traceback: {traceback.format_exc()}")
                        
                        logger.warning("[STEP 3] Using keyword fallback...")
                        query_lower = message.lower()
                        
                        for idx, table_info in table_lookup.items():
                            file_lower = table_info.get('file', '').lower()
                            sheet_lower = table_info.get('sheet', '').lower()
                            
                            if any(kw in query_lower for kw in ['employee', 'active', 'list', 'count', 'how many']):
                                if 'employee' in file_lower or 'conversion' in file_lower:
                                    selected_indices.append(idx)
                                    logger.warning(f"[STEP 3] Fallback selected: {idx} (employee file)")
                            else:
                                for term in query_lower.split():
                                    if len(term) > 3 and (term in file_lower or term in sheet_lower):
                                        selected_indices.append(idx)
                                        logger.warning(f"[STEP 3] Fallback selected: {idx} (keyword match)")
                                        break
                        
                        if not selected_indices:
                            selected_indices = list(table_lookup.keys())[:2]
                            logger.warning(f"[STEP 3] No matches, using first 2 tables: {selected_indices}")
                    
                    # =========================================================
                    # STEP 4: QUERY SELECTED TABLES
                    # =========================================================
                    update_job_status(job_id, 'processing', '📊 Retrieving data...', 35)
                    logger.warning(f"[STEP 4] Querying {len(selected_indices)} selected tables: {selected_indices}")
                    
                    # Check query type
                    query_lower = message.lower()
                    is_count_query = any(kw in query_lower for kw in ['how many', 'count', 'total', 'number of'])
                    is_list_query = any(kw in query_lower for kw in ['list', 'show', 'give me', 'who', 'active', 'employee'])
                    row_limit = 2000 if is_count_query else 500
                    
                    for idx in selected_indices[:3]:
                        table_info = table_lookup[idx]
                        table_name = table_info.get('table_name', '')
                        sheet_name = table_info.get('sheet', '')
                        file_name = table_info.get('file', '')
                        
                        logger.warning(f"[STEP 4] Querying table {idx}: {table_name} (limit {row_limit})")
                        
                        try:
                            # ALWAYS get value distributions for status-like columns
                            value_summary = ""
                            cols_result = handler.conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
                            all_cols = [col[1] for col in cols_result]
                            
                            logger.warning(f"[STEP 4] Table {idx} has {len(all_cols)} columns: {all_cols[:15]}")
                            
                            # Wider pattern to catch employment_status_code, status, active, terminated, etc.
                            status_cols = [c for c in all_cols if any(s in c.lower() for s in 
                                          ['status', 'active', 'type', 'term', 'employed'])]
                            
                            logger.warning(f"[STEP 4] Status-like columns found: {status_cols}")
                            
                            if status_cols:
                                value_summary = "\n** ACTUAL VALUE COUNTS (from full table, not sample): **\n"
                                for col in status_cols[:5]:  # Up to 5 status columns
                                    try:
                                        dist_sql = f'SELECT "{col}", COUNT(*) as cnt FROM "{table_name}" GROUP BY "{col}" ORDER BY cnt DESC'
                                        dist_result = handler.conn.execute(dist_sql).fetchall()
                                        if dist_result:
                                            dist_str = ", ".join([f"'{row[0]}'={row[1]}" for row in dist_result[:10]])
                                            value_summary += f"  {col}: {dist_str}\n"
                                    except Exception as de:
                                        logger.warning(f"[STEP 4] Distribution query failed for {col}: {de}")
                                logger.warning(f"[STEP 4] Value distributions: {value_summary.strip()}")
                            
                            # Get total row count
                            total_count_result = handler.conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()
                            total_row_count = total_count_result[0] if total_count_result else 0
                            
                            # Get sample data
                            sql = f'SELECT * FROM "{table_name}" LIMIT {row_limit}'
                            rows, cols = handler.execute_query(sql)
                            all_columns.extend(cols)
                            
                            logger.warning(f"[STEP 4] ✅ Got {len(rows)} sample rows, {total_row_count} total rows, {len(cols)} columns")
                            
                            if rows:
                                decrypted = decrypt_results(rows, handler)
                                sql_results_list.append({
                                    'source_file': file_name,
                                    'sheet': sheet_name,
                                    'table': table_name,
                                    'columns': cols,
                                    'data': decrypted,
                                    'total_rows': total_row_count,
                                    'sample_size': len(rows),
                                    'value_summary': value_summary
                                })
                        except Exception as query_e:
                            logger.error(f"[STEP 4] ❌ Query failed for {table_name}: {query_e}")
                    
                    logger.warning(f"[STEP 4] Total results collected: {len(sql_results_list)}")
                    
            except Exception as handler_e:
                logger.error(f"[STEP 2-4] ❌ Handler error: {handler_e}")
                logger.error(f"[STEP 2-4] Traceback: {traceback.format_exc()}")
        else:
            logger.warning("[STEP 2] Structured queries NOT available, skipping to RAG")
        
        # =====================================================================
        # STEP 5: RAG SEARCH
        # =====================================================================
        update_job_status(job_id, 'processing', '🔍 Searching documents...', 45)
        logger.warning("[STEP 5] Starting RAG search...")
        
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
                logger.warning(f"[STEP 5] ✅ RAG found {len(rag_chunks)} chunks")
            else:
                logger.warning("[STEP 5] RAG returned no results")
                
        except Exception as rag_e:
            logger.error(f"[STEP 5] ❌ RAG error: {rag_e}")
        
        # =====================================================================
        # STEP 6: BUILD CONTEXT
        # =====================================================================
        update_job_status(job_id, 'processing', '🧠 Building context...', 55)
        logger.warning(f"[STEP 6] Building context from {len(sql_results_list)} SQL results, {len(rag_chunks)} RAG chunks")
        
        context_parts = []
        sources = []
        
        # Add UKG Reference Data (standard codes)
        ukg_reference = """
** UKG STANDARD REFERENCE CODES **
Employment Status Codes:
  A = Active
  L = Leave of Absence
  T = Terminated
  S = Suspended

Use these codes to interpret employment_status_code or similar fields.
"""
        context_parts.append(ukg_reference)
        
        for result in sql_results_list:
            data_text = f"Source: {result['source_file']} → {result['sheet']}\n"
            data_text += f"Columns: {', '.join(result['columns'])}\n"
            data_text += f"Total rows in table: {result['total_rows']}\n"
            data_text += f"Sample rows shown below: {result.get('sample_size', len(result['data']))}\n"
            
            # Include ACTUAL value distributions from full table (not sample)
            if result.get('value_summary'):
                data_text += result['value_summary']
            
            data_text += "\nSample Data:\n"
            
            # Show sample rows with key columns - limit to 50 to manage token count
            row_limit_for_context = 50
            for row in result['data'][:row_limit_for_context]:
                key_cols = [c for c in result['columns'] if any(s in c.lower() for s in 
                           ['employee', 'status', 'name', 'number', 'id', 'type', 'active', 'term', 'department', 'job', 'title'])]
                if not key_cols:
                    key_cols = result['columns'][:8]  # Fewer columns too
                
                row_str = " | ".join(f"{k}: {row.get(k, '')}" for k in key_cols if k in row)
                data_text += f"  {row_str}\n"
            
            if len(result['data']) > 50:
                data_text += f"  ... and {len(result['data']) - 50} more rows in sample\n"
            
            context_parts.append(data_text)
            sources.append({
                'filename': result['source_file'],
                'sheet': result['sheet'],
                'type': 'structured',
                'rows': result['total_rows'],
                'relevance': 95
            })
        
        for i, chunk in enumerate(rag_chunks[:5]):
            context_parts.append(f"Document {i+1}:\n{chunk}")
        
        if rag_chunks:
            sources.append({'filename': 'Documents', 'type': 'rag', 'chunks': len(rag_chunks), 'relevance': 80})
        
        logger.warning(f"[STEP 6] Context parts: {len(context_parts)}, Total sources: {len(sources)}")
        
        # =====================================================================
        # STEP 7: PII DETECTION & SANITIZATION
        # =====================================================================
        full_context = '\n\n'.join(context_parts)
        logger.warning(f"[STEP 7] Context length: {len(full_context)} chars")
        
        pii_detection = detect_pii_in_data(full_context, all_columns)
        
        if pii_detection['has_pii']:
            logger.warning(f"[STEP 7] PII detected: {pii_detection['pii_types']}, columns: {pii_detection['column_flags']}")
            update_job_status(job_id, 'processing', '🔒 Securing data...', 65)
            full_context = sanitize_pii(full_context)
            sanitized = True
        else:
            logger.warning("[STEP 7] No PII detected")
            sanitized = False
        
        # =====================================================================
        # STEP 8: SEND TO CLAUDE FOR ANSWER
        # =====================================================================
        logger.warning(f"[STEP 8] context_parts count: {len(context_parts)}")
        
        if context_parts:
            update_job_status(job_id, 'processing', '✨ Generating response...', 75)
            logger.warning("[STEP 8] Sending to orchestrator...")
            logger.warning(f"[STEP 8] Context to send: {len(full_context)} chars")
            
            orchestrator_chunks = [{
                'document': full_context,
                'metadata': {'filename': 'Query Results', 'type': 'combined', 'pii_sanitized': sanitized}
            }]
            
            try:
                orchestrator = LLMOrchestrator()
                logger.warning("[STEP 8] Calling orchestrator.process_query...")
                result = orchestrator.process_query(message, orchestrator_chunks)
                logger.warning(f"[STEP 8] Orchestrator returned: {list(result.keys())}")
                
                response = result.get('response', 'I found data but had trouble analyzing it.')
                logger.warning(f"[STEP 8] ✅ Got response: {len(response)} chars, first 100: {response[:100]}")
                
                if sanitized:
                    response += "\n\n*Note: Some sensitive values have been protected.*"
                
                update_job_status(
                    job_id, 'complete', 'Complete', 100,
                    response=response,
                    sources=sources,
                    chunks_found=len(sql_results_list) + len(rag_chunks),
                    models_used=result.get('models_used', ['claude']),
                    query_type='self_healing',
                    sanitized=sanitized,
                    pii_detected=pii_detection['pii_types'] if pii_detection['has_pii'] else []
                )
                logger.warning(f"[COMPLETE] Job {job_id[:8]} finished successfully")
                return
                
            except Exception as orch_e:
                logger.error(f"[STEP 8] ❌ Orchestrator FAILED: {orch_e}")
                logger.error(f"[STEP 8] Traceback: {traceback.format_exc()}")
        else:
            logger.warning("[STEP 8] ⚠️ NO CONTEXT PARTS - skipping to fallback")
        
        # =====================================================================
        # STEP 9: FALLBACK - No data found
        # =====================================================================
        logger.warning("[STEP 9] No context built, attempting fallback...")
        update_job_status(job_id, 'processing', '🔍 Broader search...', 80)
        
        try:
            rag = RAGHandler()
            collection = rag.client.get_or_create_collection(name="documents")
            rag_response = collection.query(query_texts=[message], n_results=20, where=None)
            
            if rag_response and rag_response.get('documents') and rag_response['documents'][0]:
                chunks = rag_response['documents'][0]
                fallback_context = '\n\n'.join(chunks[:10])
                
                fallback_pii = detect_pii_in_data(fallback_context, [])
                if fallback_pii['has_pii']:
                    fallback_context = sanitize_pii(fallback_context)
                
                orchestrator = LLMOrchestrator()
                result = orchestrator.process_query(message, [{'document': fallback_context, 'metadata': {'type': 'fallback'}}])
                
                update_job_status(
                    job_id, 'complete', 'Complete', 100,
                    response=result.get('response', 'Could not find relevant information.'),
                    sources=[{'filename': 'Fallback Search', 'type': 'rag', 'chunks': len(chunks)}],
                    chunks_found=len(chunks),
                    models_used=['claude'],
                    query_type='fallback',
                    sanitized=fallback_pii['has_pii']
                )
                logger.warning(f"[COMPLETE] Job {job_id[:8]} finished via fallback")
                return
                
        except Exception as fallback_e:
            logger.error(f"[STEP 9] Fallback error: {fallback_e}")
        
        # No data at all
        logger.error(f"[FAIL] Job {job_id[:8]} - no data found anywhere")
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
        logger.error(f"[FATAL] Job {job_id[:8]} crashed: {e}")
        logger.error(f"[FATAL] Traceback: {traceback.format_exc()}")
        update_job_status(job_id, 'error', 'Error', 100, error=str(e), response=f"An error occurred: {str(e)}")


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.get("/chat/models")
async def get_available_models():
    return {"models": [{"id": "claude-3-sonnet", "name": "Claude 3 Sonnet"}], "default": "claude-3-sonnet"}


@router.post("/chat/start")
async def start_chat(request: ChatStartRequest):
    job_id = str(uuid.uuid4())
    chat_jobs[job_id] = {'status': 'starting', 'current_step': '🚀 Starting...', 'progress': 0, 'created_at': time.time()}
    thread = threading.Thread(target=process_chat_job, args=(job_id, request.message, request.project, request.max_results or 50, request.persona or 'bessie'))
    thread.daemon = True
    thread.start()
    return {"job_id": job_id, "status": "starting"}


@router.get("/chat/status/{job_id}")
async def get_chat_status(job_id: str):
    if job_id not in chat_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return chat_jobs[job_id]


@router.delete("/chat/job/{job_id}")
async def cancel_chat_job(job_id: str):
    if job_id in chat_jobs:
        del chat_jobs[job_id]
        return {"status": "cancelled"}
    raise HTTPException(status_code=404, detail="Job not found")


@router.post("/chat")
async def chat_sync(request: ChatRequest):
    job_id = str(uuid.uuid4())
    chat_jobs[job_id] = {'status': 'processing', 'progress': 0}
    process_chat_job(job_id, request.message, request.project, request.max_results or 30, request.persona or 'bessie')
    return chat_jobs.get(job_id, {'error': 'Job failed'})


@router.get("/chat/health")
async def chat_health():
    return {"status": "healthy", "structured": STRUCTURED_QUERIES_AVAILABLE, "pii": "enabled", "jobs": len(chat_jobs)}


# =============================================================================
# PERSONA ENDPOINTS
# =============================================================================

@router.get("/chat/personas")
async def list_personas():
    try:
        pm = get_persona_manager()
        return {"personas": pm.list_personas(), "default": "bessie"}
    except Exception as e:
        raise HTTPException(500, str(e))

@router.get("/chat/personas/{name}")
async def get_persona(name: str):
    try:
        pm = get_persona_manager()
        persona = pm.get_persona(name)
        return persona.to_dict() if persona else None
    except:
        raise HTTPException(404, f"Persona '{name}' not found")

@router.post("/chat/personas")
async def create_persona(request: Request):
    try:
        data = await request.json()
        pm = get_persona_manager()
        persona = pm.create_persona(name=data['name'], icon=data.get('icon', '🤖'), description=data.get('description', ''), system_prompt=data.get('system_prompt', ''), expertise=data.get('expertise', []), tone=data.get('tone', 'Professional'))
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
        if pm.delete_persona(name):
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
        return {"tables": []}
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
        result = handler.conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'").fetchall()
        return {"tables": [r[0] for r in result]}
    except Exception as e:
        return {"tables": [], "error": str(e)}

@router.post("/chat/sql")
async def execute_sql(request: Request):
    if not STRUCTURED_QUERIES_AVAILABLE:
        raise HTTPException(503, "Not available")
    try:
        data = await request.json()
        handler = get_structured_handler()
        rows, cols = handler.execute_query(data.get('sql', ''))
        return {"columns": cols, "rows": decrypt_results(rows, handler)[:1000], "total": len(rows)}
    except Exception as e:
        raise HTTPException(500, str(e))

@router.get("/chat/table-sample/{table_name}")
async def get_table_sample(table_name: str, limit: int = 100):
    if not STRUCTURED_QUERIES_AVAILABLE:
        raise HTTPException(503, "Not available")
    try:
        handler = get_structured_handler()
        return {"rows": handler.get_table_sample(table_name, limit)}
    except Exception as e:
        raise HTTPException(500, str(e))

@router.delete("/chat/data/{project}/{file_name}")
async def delete_data_file(project: str, file_name: str):
    if not STRUCTURED_QUERIES_AVAILABLE:
        raise HTTPException(503, "Not available")
    try:
        handler = get_structured_handler()
        return {"success": True, "result": handler.delete_file(project, file_name)}
    except Exception as e:
        raise HTTPException(500, str(e))

@router.get("/chat/data/{project}/files")
async def list_project_files(project: str):
    if not STRUCTURED_QUERIES_AVAILABLE:
        return {"files": []}
    try:
        handler = get_structured_handler()
        return {"files": handler.list_files(project)}
    except Exception as e:
        return {"files": [], "error": str(e)}

@router.post("/chat/data/reset-database")
async def reset_database():
    if not STRUCTURED_QUERIES_AVAILABLE:
        raise HTTPException(503, "Not available")
    try:
        handler = get_structured_handler()
        return {"success": True, "result": handler.reset_database()}
    except Exception as e:
        raise HTTPException(500, str(e))

@router.get("/chat/debug-chunks")
async def debug_chunks(search: str = "test", project: Optional[str] = None):
    try:
        rag = RAGHandler()
        collection = rag.client.get_or_create_collection(name="documents")
        results = collection.query(query_texts=[search], n_results=10, where={"project": project} if project else None)
        return {"chunks": len(results.get('documents', [[]])[0]) if results else 0}
    except Exception as e:
        return {"error": str(e)}


@router.post("/chat/debug")
async def debug_query(request: Request):
    """
    Debug endpoint - shows exactly what happens at each step WITHOUT calling Claude.
    Returns raw data so we can see what's broken.
    """
    try:
        data = await request.json()
        message = data.get('message', 'list active employees')
        project = data.get('project', None)
        
        debug_output = {
            "query": message,
            "project": project,
            "steps": {}
        }
        
        # STEP 1: Query Classification
        from utils.llm_orchestrator import classify_query
        query_type = classify_query(message, [])
        debug_output["steps"]["1_classification"] = {
            "query_type": query_type,
            "note": "employee = sanitizer path, config = direct to Claude"
        }
        
        # STEP 2: Get Schema
        if STRUCTURED_QUERIES_AVAILABLE:
            handler = get_structured_handler()
            schema = handler.get_schema_for_project(project) if project else handler.get_schema_for_project(None)
            tables_list = schema.get('tables', [])
            
            debug_output["steps"]["2_schema"] = {
                "tables_found": len(tables_list),
                "table_names": [t.get('sheet', t.get('table_name', ''))[:50] for t in tables_list[:10]]
            }
            
            # STEP 3: Build summaries (what Claude sees for table selection)
            table_summaries = []
            table_lookup = {}
            
            for idx, table_info in enumerate(tables_list):
                table_name = table_info.get('table_name', '')
                sheet_name = table_info.get('sheet', '')
                file_name = table_info.get('file', '')
                row_count = table_info.get('row_count', 0)
                columns = table_info.get('columns', [])
                
                if columns and isinstance(columns[0], dict):
                    col_names = [c.get('name', str(c)) for c in columns[:10]]
                else:
                    col_names = [str(c) for c in columns[:10]]
                
                summary = f"[{idx}] {file_name} → {sheet_name} ({row_count} rows) | Cols: {', '.join(col_names)}"
                table_summaries.append(summary)
                table_lookup[idx] = table_info
            
            debug_output["steps"]["3_table_summaries"] = table_summaries[:15]
            
            # STEP 4: Simulate table selection (keyword-based, not Claude)
            query_lower = message.lower()
            selected = []
            for idx, info in table_lookup.items():
                file_lower = info.get('file', '').lower()
                if 'employee' in query_lower and ('employee' in file_lower or 'conversion' in file_lower):
                    selected.append(idx)
            
            if not selected:
                selected = list(table_lookup.keys())[:2]
            
            debug_output["steps"]["4_selected_tables"] = {
                "indices": selected[:3],
                "names": [table_lookup[i].get('sheet', '') for i in selected[:3]]
            }
            
            # STEP 5: Query actual data
            raw_data_samples = []
            all_columns = []
            
            for idx in selected[:2]:
                table_info = table_lookup[idx]
                table_name = table_info.get('table_name', '')
                
                try:
                    sql = f'SELECT * FROM "{table_name}" LIMIT 5'
                    rows, cols = handler.execute_query(sql)
                    all_columns.extend(cols)
                    
                    # Decrypt if needed
                    decrypted = decrypt_results(rows, handler)
                    
                    raw_data_samples.append({
                        "table": table_info.get('sheet', ''),
                        "columns": cols,
                        "row_count": len(rows),
                        "sample_rows": decrypted[:3]  # First 3 rows
                    })
                except Exception as e:
                    raw_data_samples.append({"table": table_name, "error": str(e)})
            
            debug_output["steps"]["5_raw_data"] = raw_data_samples
            
            # STEP 6: Build context (what would be sent to LLM)
            context_parts = []
            for sample in raw_data_samples:
                if "error" not in sample:
                    data_text = f"Table: {sample['table']}\nColumns: {', '.join(sample['columns'])}\n"
                    for row in sample.get('sample_rows', []):
                        row_str = " | ".join(f"{k}: {v}" for k, v in list(row.items())[:8])
                        data_text += f"  {row_str}\n"
                    context_parts.append(data_text)
            
            full_context = '\n\n'.join(context_parts)
            debug_output["steps"]["6_context_preview"] = full_context[:2000]
            
            # STEP 7: PII Detection
            pii_result = detect_pii_in_data(full_context, all_columns)
            debug_output["steps"]["7_pii_detection"] = pii_result
            
            # STEP 8: Sanitization preview (if employee path)
            if query_type == 'employee':
                sanitized_preview = sanitize_pii(full_context[:1000])
                debug_output["steps"]["8_sanitized_preview"] = sanitized_preview[:1000]
            else:
                debug_output["steps"]["8_sanitized_preview"] = "N/A - config path, no sanitization"
        
        else:
            debug_output["steps"]["error"] = "STRUCTURED_QUERIES_AVAILABLE = False"
        
        return debug_output
        
    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}

@router.get("/chat/export/{filename}")
async def download_export(filename: str):
    from fastapi.responses import FileResponse
    import os
    path = f"/data/exports/{filename}"
    if not os.path.exists(path):
        raise HTTPException(404, "Not found")
    return FileResponse(path=path, filename=filename)


# =============================================================================
# EXCEL EXPORT ENDPOINT
# =============================================================================

class ExportRequest(BaseModel):
    query: str
    project: Optional[str] = None
    tables: Optional[List[str]] = None  # Optional: specific tables to export

@router.post("/chat/export-excel")
async def export_to_excel(request: ExportRequest):
    """
    Export query results to Excel with 2 tabs:
    - Results: The actual data
    - Sources: Files/sheets referenced
    """
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
        
        if not STRUCTURED_QUERIES_AVAILABLE:
            raise HTTPException(503, "Structured data not available")
        
        handler = get_structured_handler()
        query = request.query.lower()
        project = request.project
        
        logger.warning(f"[EXPORT] Starting export for query: {query[:50]}...")
        
        # Get schema and find relevant tables (same logic as chat)
        schema = handler.get_schema_for_project(project)
        tables_list = schema.get('tables', [])
        
        if not tables_list:
            raise HTTPException(404, "No tables found for project")
        
        # Use provided tables or find relevant ones
        tables_to_query = []
        if request.tables:
            for t in tables_list:
                if t.get('table_name') in request.tables:
                    tables_to_query.append(t)
        else:
            # Simple keyword matching for table selection
            keywords = ['employee', 'company', 'personal', 'conversion']
            if any(kw in query for kw in ['active', 'employee', 'staff', 'worker']):
                for t in tables_list:
                    table_name = t.get('table_name', '').lower()
                    if any(kw in table_name for kw in keywords):
                        tables_to_query.append(t)
            
            # Fallback to first 3 tables if nothing matched
            if not tables_to_query:
                tables_to_query = tables_list[:3]
        
        # Create workbook
        wb = Workbook()
        
        # ========== RESULTS TAB ==========
        ws_results = wb.active
        ws_results.title = "Results"
        
        # Styling
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        current_row = 1
        sources_info = []
        
        for table_info in tables_to_query[:5]:  # Limit to 5 tables
            table_name = table_info.get('table_name', '')
            sheet_name = table_info.get('sheet', '')
            file_name = table_info.get('file', '')
            
            try:
                # Get all data (no limit for export)
                sql = f'SELECT * FROM "{table_name}"'
                rows, cols = handler.execute_query(sql)
                
                if not rows:
                    continue
                
                # Decrypt if needed
                decrypted = decrypt_results(rows, handler)
                
                # Add section header
                ws_results.cell(row=current_row, column=1, value=f"📊 {file_name} → {sheet_name}")
                ws_results.cell(row=current_row, column=1).font = Font(bold=True, size=12)
                ws_results.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=min(len(cols), 10))
                current_row += 1
                
                # Add column headers
                for col_idx, col_name in enumerate(cols, 1):
                    cell = ws_results.cell(row=current_row, column=col_idx, value=col_name)
                    cell.font = header_font
                    cell.fill = header_fill
                    cell.border = thin_border
                    cell.alignment = Alignment(horizontal='center')
                current_row += 1
                
                # Add data rows
                for row_data in decrypted:
                    for col_idx, col_name in enumerate(cols, 1):
                        cell = ws_results.cell(row=current_row, column=col_idx, value=row_data.get(col_name, ''))
                        cell.border = thin_border
                    current_row += 1
                
                # Track sources
                sources_info.append({
                    'file': file_name,
                    'sheet': sheet_name,
                    'table': table_name,
                    'rows': len(decrypted),
                    'columns': len(cols)
                })
                
                current_row += 2  # Gap between tables
                
            except Exception as te:
                logger.error(f"[EXPORT] Error querying {table_name}: {te}")
                continue
        
        # Auto-adjust column widths (Results tab)
        for col_idx in range(1, ws_results.max_column + 1):
            max_length = 0
            column_letter = get_column_letter(col_idx)
            for row_idx in range(1, min(ws_results.max_row + 1, 100)):  # Check first 100 rows
                cell = ws_results.cell(row=row_idx, column=col_idx)
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            ws_results.column_dimensions[column_letter].width = min(max_length + 2, 50)
        
        # ========== SOURCES TAB ==========
        ws_sources = wb.create_sheet(title="Sources")
        
        # Headers
        source_headers = ["File", "Sheet", "Table Name", "Rows", "Columns"]
        for col_idx, header in enumerate(source_headers, 1):
            cell = ws_sources.cell(row=1, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = thin_border
        
        # Source data
        for row_idx, source in enumerate(sources_info, 2):
            ws_sources.cell(row=row_idx, column=1, value=source['file']).border = thin_border
            ws_sources.cell(row=row_idx, column=2, value=source['sheet']).border = thin_border
            ws_sources.cell(row=row_idx, column=3, value=source['table']).border = thin_border
            ws_sources.cell(row=row_idx, column=4, value=source['rows']).border = thin_border
            ws_sources.cell(row=row_idx, column=5, value=source['columns']).border = thin_border
        
        # Auto-adjust source columns
        for col_idx in range(1, 6):
            ws_sources.column_dimensions[get_column_letter(col_idx)].width = 25
        
        # Add metadata row
        metadata_row = len(sources_info) + 3
        ws_sources.cell(row=metadata_row, column=1, value="Export Info:")
        ws_sources.cell(row=metadata_row, column=1).font = Font(bold=True)
        ws_sources.cell(row=metadata_row + 1, column=1, value="Query:")
        ws_sources.cell(row=metadata_row + 1, column=2, value=request.query)
        ws_sources.cell(row=metadata_row + 2, column=1, value="Project:")
        ws_sources.cell(row=metadata_row + 2, column=2, value=project or "All")
        ws_sources.cell(row=metadata_row + 3, column=1, value="Generated:")
        ws_sources.cell(row=metadata_row + 3, column=2, value=time.strftime("%Y-%m-%d %H:%M:%S"))
        
        # Save to memory buffer
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        # Generate filename
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        safe_query = re.sub(r'[^\w\s]', '', request.query[:30]).strip().replace(' ', '_')
        filename = f"export_{safe_query}_{timestamp}.xlsx"
        
        logger.warning(f"[EXPORT] Generated {filename} with {len(sources_info)} tables, {sum(s['rows'] for s in sources_info)} total rows")
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[EXPORT] Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(500, f"Export failed: {str(e)}")

@router.get("/chat/data/{project}/{file_name}/versions")
async def get_file_versions(project: str, file_name: str):
    if not STRUCTURED_QUERIES_AVAILABLE:
        raise HTTPException(503, "Not available")
    try:
        handler = get_structured_handler()
        return {"versions": handler.get_file_versions(project, file_name)}
    except Exception as e:
        raise HTTPException(500, str(e))

class CompareRequest(BaseModel):
    sheet_name: str
    key_column: str
    version1: Optional[int] = None
    version2: Optional[int] = None

@router.post("/chat/data/{project}/{file_name}/compare")
async def compare_versions(project: str, file_name: str, request: CompareRequest):
    if not STRUCTURED_QUERIES_AVAILABLE:
        raise HTTPException(503, "Not available")
    try:
        handler = get_structured_handler()
        result = handler.compare_versions(project=project, file_name=file_name, sheet_name=request.sheet_name, key_column=request.key_column, version1=request.version1, version2=request.version2)
        if 'error' in result:
            raise HTTPException(400, result['error'])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

@router.get("/chat/data/encryption-status")
async def encryption_status():
    if not STRUCTURED_QUERIES_AVAILABLE:
        raise HTTPException(503, "Not available")
    try:
        handler = get_structured_handler()
        return {"encryption": handler.encryptor.fernet is not None, "pii": "enabled"}
    except Exception as e:
        raise HTTPException(500, str(e))
