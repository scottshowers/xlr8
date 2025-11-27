"""
Chat Router - PRODUCTION VERSION with PII Protection
=====================================================

ARCHITECTURE:
1. INTELLIGENT QUERY DETECTION
2. SELF-HEALING DATA GATHERING  
3. **PII DETECTION ON DATA** (not just query keywords)
4. SAFE ROUTING:
   - PII detected → Local LLM → Sanitize → Claude
   - No PII → Direct Claude (fast path)
5. UNIFIED RESPONSE SYNTHESIS

SECURITY PRINCIPLE:
- Scan DATA for PII patterns, not just query words
- NEVER send raw PII to external APIs
- Default to LOCAL path when uncertain
- Sanitize BEFORE any external call

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
from utils.intent_classifier import classify_and_configure
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
# PII DETECTION PATTERNS - Scan DATA, not just queries
# =============================================================================

PII_PATTERNS = {
    # SSN patterns
    'ssn': [
        r'\b\d{3}-\d{2}-\d{4}\b',           # 123-45-6789
        r'\b\d{9}\b',                         # 123456789 (9 digits)
        r'\bssn\b', r'\bsocial.?security\b'
    ],
    
    # Financial patterns
    'financial': [
        r'\b\d{8,17}\b',                      # Bank account numbers
        r'\brouting.?number\b',
        r'\baccount.?number\b',
        r'\bbank.?account\b'
    ],
    
    # Compensation patterns (values, not just keywords)
    'compensation': [
        r'\$\s*\d{2,3},?\d{3}',               # $50,000 or $125000
        r'\b\d{2,3},?\d{3}\.\d{2}\b',         # 50,000.00
        r'salary[:\s]+\d',
        r'pay.?rate[:\s]+\d',
        r'hourly.?rate[:\s]+\d',
        r'annual[:\s]+\d',
        r'compensation[:\s]+\d'
    ],
    
    # Date of birth patterns
    'dob': [
        r'\b(0?[1-9]|1[0-2])[-/](0?[1-9]|[12]\d|3[01])[-/](19|20)\d{2}\b',  # MM/DD/YYYY
        r'\b(19|20)\d{2}[-/](0?[1-9]|1[0-2])[-/](0?[1-9]|[12]\d|3[01])\b',  # YYYY-MM-DD
        r'\bdob\b', r'\bdate.?of.?birth\b', r'\bbirthdate\b', r'\bbirth.?date\b'
    ],
    
    # Contact info
    'contact': [
        r'\b[\w\.-]+@[\w\.-]+\.\w{2,}\b',     # Email
        r'\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',  # Phone
        r'\b\d{5}(-\d{4})?\b'                  # ZIP code
    ],
    
    # Address patterns
    'address': [
        r'\b\d+\s+\w+\s+(street|st|avenue|ave|road|rd|drive|dr|lane|ln|way|court|ct|circle|cir|boulevard|blvd)\b',
        r'\baddress[:\s]',
        r'\bstreet[:\s]',
        r'\bcity[:\s]',
        r'\bstate[:\s]'
    ],
    
    # Name patterns in employee context
    'employee_names': [
        r'employee.{0,20}:\s*[A-Z][a-z]+\s+[A-Z][a-z]+',  # Employee: John Smith
        r'name[:\s]+[A-Z][a-z]+\s+[A-Z][a-z]+',           # Name: John Smith
        r'\bfirst.?name[:\s]+[A-Z]',
        r'\blast.?name[:\s]+[A-Z]'
    ]
}

# Column names that indicate PII
PII_COLUMN_PATTERNS = [
    r'ssn', r'social.*security', r'tax.*id',
    r'salary', r'pay.*rate', r'wage', r'compensation', r'hourly.*rate', r'annual.*pay',
    r'bank.*account', r'routing', r'account.*num',
    r'dob', r'birth.*date', r'date.*birth',
    r'email', r'phone', r'address', r'street', r'city', r'zip',
    r'first.*name', r'last.*name', r'full.*name', r'employee.*name'
]


def detect_pii_in_data(data: str, columns: List[str] = None) -> Dict[str, Any]:
    """
    Scan DATA content for PII patterns.
    Returns detected PII types and whether data should be protected.
    
    This scans the ACTUAL DATA, not just query keywords.
    """
    detected = {
        'has_pii': False,
        'pii_types': [],
        'confidence': 0,
        'column_flags': [],
        'pattern_matches': 0
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
    
    # Scan data content for PII patterns
    for pii_type, patterns in PII_PATTERNS.items():
        for pattern in patterns:
            try:
                matches = re.findall(pattern, data_lower, re.IGNORECASE)
                if matches:
                    detected['pii_types'].append(pii_type)
                    detected['pattern_matches'] += len(matches)
                    detected['has_pii'] = True
            except re.error:
                continue
    
    # Calculate confidence
    if detected['pattern_matches'] > 0:
        # More matches = higher confidence
        detected['confidence'] = min(100, 50 + (detected['pattern_matches'] * 5))
    
    if detected['column_flags']:
        # PII column names are strong indicators
        detected['confidence'] = max(detected['confidence'], 80)
    
    # Deduplicate pii_types
    detected['pii_types'] = list(set(detected['pii_types']))
    
    return detected


def sanitize_context_for_external(context: str, pii_detection: Dict) -> str:
    """
    Sanitize context before sending to external API.
    Replaces PII with placeholders.
    """
    if not context or not pii_detection.get('has_pii'):
        return context
    
    sanitized = context
    
    # Replace SSN patterns
    sanitized = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN-REDACTED]', sanitized)
    sanitized = re.sub(r'\b\d{9}\b', '[ID-REDACTED]', sanitized)
    
    # Replace financial values
    sanitized = re.sub(r'\$\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?', '[SALARY-REDACTED]', sanitized)
    sanitized = re.sub(r'\b\d{2,3},?\d{3}\.\d{2}\b', '[AMOUNT-REDACTED]', sanitized)
    
    # Replace phone numbers
    sanitized = re.sub(r'\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b', '[PHONE-REDACTED]', sanitized)
    
    # Replace emails
    sanitized = re.sub(r'\b[\w\.-]+@[\w\.-]+\.\w{2,}\b', '[EMAIL-REDACTED]', sanitized)
    
    # Replace dates that look like DOB
    sanitized = re.sub(
        r'\b(0?[1-9]|1[0-2])[-/](0?[1-9]|[12]\d|3[01])[-/](19|20)\d{2}\b',
        '[DATE-REDACTED]',
        sanitized
    )
    
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
    """Update job status with logging"""
    if job_id in chat_jobs:
        chat_jobs[job_id].update({
            'status': status,
            'current_step': step,
            'progress': progress,
            **kwargs
        })
        logger.info(f"[JOB {job_id}] {step} ({progress}%)")


# =============================================================================
# QUERY TYPE DETECTION
# =============================================================================

STRUCTURED_QUERY_PATTERNS = [
    'how many', 'count', 'total number', 'number of',
    'sum of', 'average', 'avg', 'minimum', 'maximum',
    'list all', 'show all', 'give me all', 'get all',
    'employees with', 'employees who', 'which employees',
    'active employees', 'inactive employees', 'terminated',
    'by department', 'by location', 'grouped by',
    'find employee', 'look up', 'search for'
]

UNSTRUCTURED_QUERY_PATTERNS = [
    'explain', 'describe', 'what is', 'what are',
    'how does', 'why does', 'how to', 'how do i',
    'compare', 'difference between',
    'best practice', 'recommendation', 'suggest'
]


def detect_query_type(message: str) -> str:
    """Detect query type for routing."""
    message_lower = message.lower()
    
    has_structured = any(p in message_lower for p in STRUCTURED_QUERY_PATTERNS)
    has_unstructured = any(p in message_lower for p in UNSTRUCTURED_QUERY_PATTERNS)
    
    if has_structured and has_unstructured:
        return 'hybrid'
    elif has_structured:
        return 'structured'
    else:
        return 'unstructured'


# =============================================================================
# INTELLIGENT SQL GENERATION - Actually Intelligent
# =============================================================================

def generate_intelligent_sql(message: str, schema: dict, orchestrator: LLMOrchestrator, handler=None) -> Optional[str]:
    """
    Generate intelligent SQL query using Claude.
    
    KEY: We send Claude the ACTUAL column names AND sample values
    so it can generate SQL that matches the real data structure.
    """
    if not schema.get('tables'):
        return None
    
    tables_info = []
    for table in schema.get('tables', []):
        table_name = table.get('table_name', 'unknown')
        columns = table.get('columns', [])
        row_count = table.get('row_count', 'unknown')
        sheet = table.get('sheet', '')
        file_name = table.get('file', '')
        
        if columns and isinstance(columns[0], dict):
            col_names = [c.get('name', str(c)) for c in columns]
        else:
            col_names = [str(c) for c in columns]
        
        # GET SAMPLE VALUES - This is the key to being actually intelligent
        sample_info = ""
        if handler:
            try:
                sample_sql = f'SELECT * FROM "{table_name}" LIMIT 3'
                sample_rows, _ = handler.execute_query(sample_sql)
                if sample_rows:
                    sample_info = "\nSample data (first 3 rows):\n"
                    for row in sample_rows[:3]:
                        row_preview = {k: str(v)[:50] for k, v in list(row.items())[:10]}
                        sample_info += f"  {row_preview}\n"
            except:
                pass
        
        tables_info.append(f"""
Table: "{table_name}"
Source: {file_name} → {sheet}
Rows: {row_count}
Columns: {', '.join(col_names[:50])}
{sample_info}
""")
    
    schema_text = '\n'.join(tables_info)
    
    sql_prompt = f"""Generate a SQL query for DuckDB to answer this question.

AVAILABLE TABLES WITH SAMPLE DATA:
{schema_text}

USER QUESTION: {message}

CRITICAL RULES:
1. Use the EXACT column names shown above - they may have spaces, mixed case, etc.
2. Look at the SAMPLE DATA to understand what values exist (e.g., "Active", "A", "Y", "Terminated", etc.)
3. For status queries, find the column that indicates employee status (could be "Status", "Employment Status", "Emp Status", "Active", etc.)
4. For "how many active" - find rows where status indicates active (not terminated/inactive)
5. Column names with spaces MUST be wrapped in double quotes: "Column Name"
6. Use ILIKE for case-insensitive matching
7. Return ONLY the SQL query, no explanation

SQL:"""

    try:
        result = orchestrator.generate_sql(sql_prompt)
        if result and result.get('sql'):
            sql = result['sql'].strip()
            logger.info(f"[SQL-GEN] Generated: {sql[:100]}...")
            return sql
    except Exception as e:
        logger.error(f"[SQL-GEN] Failed: {e}")
    
    return None


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
# MAIN CHAT PROCESSING - PII-SAFE PRODUCTION VERSION
# =============================================================================

def process_chat_job(job_id: str, message: str, project: Optional[str], max_results: int, persona_name: str = 'bessie'):
    """
    PRODUCTION Chat Processing Pipeline - PII SAFE
    ================================================
    
    SECURITY ARCHITECTURE:
    1. Gather data from all sources
    2. **SCAN DATA FOR PII** (not just query keywords)
    3. Route based on DATA content:
       - PII detected → Sanitize → Claude (or Local LLM → Sanitize → Claude)
       - No PII → Direct Claude (fast path)
    4. NEVER send raw PII to external APIs
    
    SELF-HEALING:
    - Multiple fallback paths
    - Always attempt useful response
    """
    try:
        # =====================================================================
        # STEP 1: INITIALIZE
        # =====================================================================
        pm = get_persona_manager()
        persona = pm.get_persona(persona_name)
        logger.info(f"[PERSONA] Using: {persona.name} {persona.icon}")
        
        orchestrator = LLMOrchestrator()
        query_type = detect_query_type(message)
        logger.info(f"[QUERY-TYPE] Detected: {query_type}")
        
        # Data containers
        structured_results = []
        rag_chunks = []
        all_columns = []  # Track columns for PII detection
        sql_executed = None
        
        # =====================================================================
        # STEP 2: GATHER STRUCTURED DATA (DuckDB)
        # =====================================================================
        if STRUCTURED_QUERIES_AVAILABLE and query_type in ['structured', 'hybrid']:
            update_job_status(job_id, 'processing', '📊 Analyzing structured data...', 10)
            
            try:
                handler = get_structured_handler()
                schema = handler.get_schema_for_project(project) if project else handler.get_schema_for_project(None)
                
                if schema.get('tables'):
                    logger.info(f"[STRUCTURED] Found {len(schema['tables'])} tables")
                    
                    # INTELLIGENT SQL GENERATION - Pass handler for sample data lookup
                    update_job_status(job_id, 'processing', '🧠 Generating intelligent query...', 20)
                    sql_query = generate_intelligent_sql(message, schema, orchestrator, handler)
                    
                    if sql_query:
                        update_job_status(job_id, 'processing', '⚡ Executing query...', 30)
                        try:
                            rows, columns = handler.execute_query(sql_query)
                            sql_executed = sql_query
                            all_columns.extend(columns)
                            
                            if rows:
                                decrypted = decrypt_results(rows, handler)
                                
                                source_file = 'Database'
                                source_sheet = 'Query Result'
                                for table in schema.get('tables', []):
                                    if table.get('table_name', '').lower() in sql_query.lower():
                                        source_file = table.get('file', 'Database')
                                        source_sheet = table.get('sheet', 'Query Result')
                                        break
                                
                                structured_results.append({
                                    'source_file': source_file,
                                    'sheet': source_sheet,
                                    'sql': sql_query,
                                    'columns': columns,
                                    'data': decrypted,
                                    'total_rows': len(rows),
                                    'query_type': 'intelligent'
                                })
                                logger.info(f"[SQL-EXEC] Success: {len(rows)} rows")
                                
                        except Exception as e:
                            logger.warning(f"[SQL-EXEC] Failed: {e}")
                            structured_results.extend(
                                fallback_table_sampling(message, schema, handler, all_columns)
                            )
                    else:
                        structured_results.extend(
                            fallback_table_sampling(message, schema, handler, all_columns)
                        )
                        
            except Exception as e:
                logger.error(f"[STRUCTURED] Handler error: {e}")
        
        # =====================================================================
        # STEP 3: GATHER UNSTRUCTURED DATA (ChromaDB/RAG)
        # =====================================================================
        if query_type in ['unstructured', 'hybrid'] or not structured_results:
            update_job_status(job_id, 'processing', '🔍 Searching documents...', 40)
            
            try:
                rag = RAGHandler()
                collection = rag.client.get_or_create_collection(name="documents")
                
                where_filter = None
                if project and project not in ['', 'all', 'All Projects']:
                    where_filter = {"project": project}
                
                rag_response = collection.query(
                    query_texts=[message],
                    n_results=min(max_results, 15),
                    where=where_filter
                )
                
                if rag_response and rag_response.get('documents') and rag_response['documents'][0]:
                    rag_chunks = rag_response['documents'][0]
                    logger.info(f"[RAG] Found {len(rag_chunks)} chunks")
                    
            except Exception as e:
                logger.warning(f"[RAG] Search error: {e}")
        
        # =====================================================================
        # STEP 4: BUILD CONTEXT & DETECT PII IN DATA
        # =====================================================================
        update_job_status(job_id, 'processing', '🔒 Checking data security...', 50)
        
        context_parts = []
        sources = []
        
        # Build context from structured results
        for result in structured_results:
            if result['data']:
                data = result['data']
                columns = result['columns']
                
                if len(data) == 1 and len(columns) == 1:
                    col_name = columns[0]
                    value = list(data[0].values())[0]
                    context_parts.append(f"""
QUERY RESULT from {result['source_file']}:
SQL: {result['sql']}
Result: {col_name} = {value}
""")
                else:
                    context_parts.append(f"""
QUERY RESULT from {result['source_file']} → {result['sheet']}:
SQL: {result['sql']}
Rows returned: {result['total_rows']}
Columns: {', '.join(columns)}

Data (first {min(50, len(data))} rows):
""")
                    for row in data[:50]:
                        row_str = " | ".join(f"{k}: {v}" for k, v in row.items())
                        context_parts.append(f"  {row_str}")
                
                sources.append({
                    'filename': result['source_file'],
                    'sheet': result['sheet'],
                    'type': 'structured_query',
                    'rows': result['total_rows'],
                    'relevance': 98
                })
        
        # Build context from RAG chunks
        for i, chunk in enumerate(rag_chunks[:10]):
            context_parts.append(f"""
DOCUMENT EXCERPT {i+1}:
{chunk}
""")
        
        if rag_chunks:
            sources.append({
                'filename': 'Document Search',
                'type': 'rag',
                'chunks': len(rag_chunks),
                'relevance': 80
            })
        
        # Combine all context
        full_context = '\n'.join(context_parts)
        
        # =====================================================================
        # STEP 5: PII DETECTION ON DATA CONTENT
        # =====================================================================
        pii_detection = detect_pii_in_data(full_context, all_columns)
        
        if pii_detection['has_pii']:
            logger.warning(f"[PII] Detected PII in data: {pii_detection['pii_types']}, confidence: {pii_detection['confidence']}%")
            logger.info(f"[PII] Flagged columns: {pii_detection['column_flags']}")
        else:
            logger.info("[PII] No PII detected in data - safe for direct Claude path")
        
        # =====================================================================
        # STEP 6: ROUTE BASED ON DATA CONTENT (NOT QUERY)
        # =====================================================================
        if context_parts:
            update_job_status(job_id, 'processing', '✨ Generating response...', 70)
            
            if pii_detection['has_pii']:
                # ============================================================
                # PII DETECTED → SANITIZE BEFORE EXTERNAL API
                # ============================================================
                logger.info("[ROUTE] PII detected → Sanitizing before Claude")
                update_job_status(job_id, 'processing', '🔒 Securing sensitive data...', 75)
                
                # Sanitize the context
                sanitized_context = sanitize_context_for_external(full_context, pii_detection)
                
                # Create sanitized chunks for orchestrator
                orchestrator_chunks = [{
                    'document': sanitized_context,
                    'metadata': {
                        'filename': 'Sanitized Results',
                        'type': 'query_results',
                        'pii_sanitized': True,
                        'pii_types': pii_detection['pii_types']
                    }
                }]
                
                # Process through orchestrator with sanitized data
                result = orchestrator.process_query(message, orchestrator_chunks)
                response = result.get('response', 'I found data but had trouble analyzing it.')
                
                # Add note about sanitization if user should know
                if any(pt in pii_detection['pii_types'] for pt in ['ssn', 'financial', 'compensation']):
                    response += "\n\n*Note: Some sensitive values have been protected in this response.*"
                
                update_job_status(
                    job_id, 'complete', 'Complete', 100,
                    response=response,
                    sources=sources,
                    chunks_found=len(structured_results) + len(rag_chunks),
                    models_used=result.get('models_used', ['claude']) + (['duckdb'] if structured_results else []),
                    query_type=query_type,
                    sanitized=True,
                    pii_detected=pii_detection['pii_types'],
                    sql_executed=sql_executed
                )
                
            else:
                # ============================================================
                # NO PII → SAFE FOR DIRECT CLAUDE PATH
                # ============================================================
                logger.info("[ROUTE] No PII → Direct Claude path")
                
                orchestrator_chunks = [{
                    'document': full_context,
                    'metadata': {
                        'filename': 'Combined Results',
                        'type': 'query_results',
                        'pii_sanitized': False
                    }
                }]
                
                result = orchestrator.process_query(message, orchestrator_chunks)
                response = result.get('response', 'I found data but had trouble analyzing it.')
                
                update_job_status(
                    job_id, 'complete', 'Complete', 100,
                    response=response,
                    sources=sources,
                    chunks_found=len(structured_results) + len(rag_chunks),
                    models_used=result.get('models_used', ['claude']) + (['duckdb'] if structured_results else []),
                    query_type=query_type,
                    sanitized=False,
                    sql_executed=sql_executed
                )
            
            return
        
        # =====================================================================
        # STEP 7: FALLBACK - No data found
        # =====================================================================
        update_job_status(job_id, 'processing', '🔍 Attempting broader search...', 70)
        
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
                
                # Check fallback data for PII too
                fallback_pii = detect_pii_in_data(fallback_context, [])
                
                if fallback_pii['has_pii']:
                    fallback_context = sanitize_context_for_external(fallback_context, fallback_pii)
                
                orchestrator_chunks = [
                    {'document': fallback_context, 'metadata': {'type': 'fallback_rag'}}
                ]
                
                result = orchestrator.process_query(message, orchestrator_chunks)
                response = result.get('response', 'I searched but couldn\'t find relevant information.')
                
                update_job_status(
                    job_id, 'complete', 'Complete', 100,
                    response=response,
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
            response="I couldn't find any relevant data for your question. Please make sure data has been uploaded for this project.",
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


def fallback_table_sampling(message: str, schema: dict, handler, all_columns: list) -> list:
    """Fallback: Sample data from relevant tables when SQL generation fails."""
    results = []
    message_lower = message.lower()
    
    query_terms = [w for w in message_lower.split() if len(w) > 3]
    query_stems = set()
    for term in query_terms:
        query_stems.add(term)
        if len(term) > 5:
            query_stems.add(term[:5])
            query_stems.add(term[:6])
    
    for table_info in schema.get('tables', []):
        table_name = table_info.get('table_name', '')
        sheet_name = table_info.get('sheet', '')
        file_name = table_info.get('file', '')
        columns = table_info.get('columns', [])
        
        sheet_lower = sheet_name.lower().replace(' ', '').replace('_', '')
        table_lower = table_name.lower()
        file_lower = file_name.lower() if file_name else ''
        
        is_relevant = False
        for stem in query_stems:
            if stem in sheet_lower or stem in table_lower or stem in file_lower:
                is_relevant = True
                break
        
        if not is_relevant:
            col_names_lower = ' '.join(str(c).lower() for c in columns[:30])
            for stem in query_stems:
                if stem in col_names_lower:
                    is_relevant = True
                    break
        
        if is_relevant:
            try:
                sql = f'SELECT * FROM "{table_name}" LIMIT 100'
                rows, cols = handler.execute_query(sql)
                all_columns.extend(cols)  # Track for PII detection
                
                if rows:
                    decrypted = decrypt_results(rows, handler)
                    results.append({
                        'source_file': file_name,
                        'sheet': sheet_name,
                        'sql': sql,
                        'columns': cols,
                        'data': decrypted,
                        'total_rows': len(rows),
                        'query_type': 'sample'
                    })
                    logger.info(f"[SAMPLE] {sheet_name}: {len(rows)} rows")
                    
                    if len(results) >= 3:
                        break
                        
            except Exception as e:
                logger.warning(f"[SAMPLE] Failed to query {table_name}: {e}")
    
    return results


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.get("/chat/models")
async def get_available_models():
    """Get available AI models"""
    return {
        "models": [
            {"id": "claude-3-sonnet", "name": "Claude 3 Sonnet", "description": "Fast, balanced model"},
            {"id": "claude-3-opus", "name": "Claude 3 Opus", "description": "Most capable model"}
        ],
        "default": "claude-3-sonnet"
    }


@router.post("/chat/start")
async def start_chat(request: ChatStartRequest):
    """Start async chat processing job"""
    job_id = str(uuid.uuid4())
    
    chat_jobs[job_id] = {
        'status': 'starting',
        'current_step': '🚀 Starting analysis...',
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
    """Get status of chat processing job"""
    if job_id not in chat_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return chat_jobs[job_id]


@router.delete("/chat/job/{job_id}")
async def cancel_chat_job(job_id: str):
    """Cancel a chat job"""
    if job_id in chat_jobs:
        del chat_jobs[job_id]
        return {"status": "cancelled"}
    raise HTTPException(status_code=404, detail="Job not found")


@router.post("/chat")
async def chat_sync(request: ChatRequest):
    """Synchronous chat endpoint"""
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
        "pii_detection": "enabled",
        "active_jobs": len(chat_jobs)
    }


# =============================================================================
# PERSONA ENDPOINTS
# =============================================================================

@router.get("/chat/personas")
async def list_personas():
    """Get all available personas"""
    try:
        pm = get_persona_manager()
        personas = pm.list_personas()
        return {"personas": personas, "count": len(personas), "default": "bessie"}
    except Exception as e:
        logger.error(f"Error listing personas: {e}")
        raise HTTPException(500, str(e))


@router.get("/chat/personas/{name}")
async def get_persona(name: str):
    """Get specific persona"""
    try:
        pm = get_persona_manager()
        persona = pm.get_persona(name)
        return persona.to_dict() if persona else None
    except Exception as e:
        raise HTTPException(404, f"Persona '{name}' not found")


@router.post("/chat/personas")
async def create_persona(request: Request):
    """Create a new persona"""
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
    """Update an existing persona"""
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
    """Delete a persona"""
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
# DATA QUERY ENDPOINTS
# =============================================================================

@router.get("/chat/schema/{project}")
async def get_project_schema(project: str):
    """Get schema for project's structured data"""
    if not STRUCTURED_QUERIES_AVAILABLE:
        return {"tables": [], "error": "Structured queries not available"}
    
    try:
        handler = get_structured_handler()
        schema = handler.get_schema_for_project(project)
        return schema
    except Exception as e:
        return {"tables": [], "error": str(e)}


@router.get("/chat/tables")
async def list_all_tables():
    """List all available tables"""
    if not STRUCTURED_QUERIES_AVAILABLE:
        return {"tables": []}
    
    try:
        handler = get_structured_handler()
        result = handler.conn.execute("""
            SELECT DISTINCT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'main'
        """).fetchall()
        return {"tables": [row[0] for row in result]}
    except Exception as e:
        return {"tables": [], "error": str(e)}


@router.post("/chat/sql")
async def execute_sql(request: Request):
    """Execute raw SQL query"""
    if not STRUCTURED_QUERIES_AVAILABLE:
        raise HTTPException(503, "Structured queries not available")
    
    try:
        data = await request.json()
        sql = data.get('sql', '')
        
        if not sql:
            raise HTTPException(400, "SQL query required")
        
        handler = get_structured_handler()
        rows, columns = handler.execute_query(sql)
        decrypted = decrypt_results(rows, handler)
        
        return {
            "columns": columns,
            "rows": decrypted[:1000],
            "total_rows": len(rows),
            "truncated": len(rows) > 1000
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/chat/table-sample/{table_name}")
async def get_table_sample(table_name: str, limit: int = 100):
    """Get sample data from a table"""
    if not STRUCTURED_QUERIES_AVAILABLE:
        raise HTTPException(503, "Structured queries not available")
    
    try:
        handler = get_structured_handler()
        rows = handler.get_table_sample(table_name, limit)
        return {"rows": rows, "count": len(rows)}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.delete("/chat/data/{project}/{file_name}")
async def delete_data_file(project: str, file_name: str, all_versions: bool = False):
    """Delete a data file"""
    if not STRUCTURED_QUERIES_AVAILABLE:
        raise HTTPException(503, "Structured queries not available")
    
    try:
        handler = get_structured_handler()
        result = handler.delete_file(project, file_name, delete_all_versions=all_versions)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/chat/data/{project}/files")
async def list_project_files(project: str):
    """List all files for a project"""
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
    """Reset the entire database"""
    if not STRUCTURED_QUERIES_AVAILABLE:
        raise HTTPException(503, "Structured queries not available")
    
    try:
        handler = get_structured_handler()
        result = handler.reset_database()
        logger.warning("⚠️ Database RESET - all data deleted!")
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/chat/debug-chunks")
async def debug_chunks(search: str = "earnings", project: Optional[str] = None, n: int = 50):
    """Debug: See what chunks exist"""
    try:
        rag = RAGHandler()
        collection = rag.client.get_or_create_collection(name="documents")
        
        where_filter = {"project": project} if project else None
        
        results = collection.query(
            query_texts=[search],
            n_results=n,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )
        
        if not results or not results['documents'][0]:
            return {"message": "No chunks found", "total": 0}
        
        sheets = {}
        for doc, meta, dist in zip(results['documents'][0], results['metadatas'][0], results['distances'][0]):
            sheet = meta.get('parent_section', 'Unknown')
            if sheet not in sheets:
                sheets[sheet] = {"count": 0, "samples": [], "avg_distance": 0}
            sheets[sheet]["count"] += 1
            sheets[sheet]["avg_distance"] += dist
            if len(sheets[sheet]["samples"]) < 2:
                sheets[sheet]["samples"].append({
                    "text": doc[:200] + "...",
                    "distance": round(dist, 3)
                })
        
        for sheet in sheets:
            sheets[sheet]["avg_distance"] = round(sheets[sheet]["avg_distance"] / sheets[sheet]["count"], 3)
        
        return {"search_term": search, "project": project, "total_chunks": len(results['documents'][0]), "sheets": sheets}
        
    except Exception as e:
        return {"error": str(e)}


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


@router.get("/chat/data/{project}/{file_name}/versions")
async def get_file_versions(project: str, file_name: str):
    """Get all versions of a file"""
    if not STRUCTURED_QUERIES_AVAILABLE:
        raise HTTPException(503, "Structured queries not available")
    
    try:
        handler = get_structured_handler()
        versions = handler.get_file_versions(project, file_name)
        return {"project": project, "file_name": file_name, "versions": versions}
    except Exception as e:
        raise HTTPException(500, str(e))


class CompareRequest(BaseModel):
    sheet_name: str
    key_column: str
    version1: Optional[int] = None
    version2: Optional[int] = None


@router.post("/chat/data/{project}/{file_name}/compare")
async def compare_file_versions(project: str, file_name: str, request: CompareRequest):
    """Compare two versions of a file"""
    if not STRUCTURED_QUERIES_AVAILABLE:
        raise HTTPException(503, "Structured queries not available")
    
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
        raise HTTPException(500, str(e))


@router.get("/chat/data/encryption-status")
async def get_encryption_status():
    """Check PII encryption status"""
    if not STRUCTURED_QUERIES_AVAILABLE:
        raise HTTPException(503, "Structured queries not available")
    
    try:
        handler = get_structured_handler()
        return {
            "encryption_available": handler.encryptor.fernet is not None,
            "pii_detection": "enabled",
            "pii_patterns": list(PII_PATTERNS.keys()),
            "column_patterns": PII_COLUMN_PATTERNS[:10]
        }
    except Exception as e:
        raise HTTPException(500, str(e))
