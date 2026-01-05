"""
LLM Orchestrator for XLR8 - PRODUCTION VERSION
===============================================

ARCHITECTURE:
- Query Classification: CONFIG vs EMPLOYEE data
- Model Selection: Mistral (general) vs DeepSeek (data extraction)
- PII Protection: Sanitize employee data before Claude
- Smart Routing: Fast path for config, secure path for PII

Author: XLR8 Team
"""

import os
import re
import json
import time
import requests
from requests.auth import HTTPBasicAuth
from typing import List, Dict, Any, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# Import MetricsService for LLM call tracking
try:
    from backend.utils.metrics_service import MetricsService
    METRICS_AVAILABLE = True
except ImportError:
    try:
        from utils.metrics_service import MetricsService
        METRICS_AVAILABLE = True
    except ImportError:
        METRICS_AVAILABLE = False
        logger.debug("[LLM] MetricsService not available - LLM metrics will not be recorded")


# =============================================================================
# QUERY CLASSIFICATION
# =============================================================================

EMPLOYEE_DATA_KEYWORDS = [
    # Direct employee references
    'employee', 'employees', 'worker', 'workers', 'staff', 
    'person', 'people', 'individual', 'individuals',
    'who ', 'whose', 'whom', 'someone',
    
    # PII fields
    'salary', 'salaries', 'pay rate', 'wage', 'wages', 'compensation',
    'ssn', 'social security',
    'address', 'phone', 'email', 'contact info',
    'birth', 'dob', 'age', 'born',
    'hire date', 'termination', 'tenure', 'years of service',
    
    # Census/roster queries
    'census', 'roster', 'headcount', 'head count',
    'how many work', 'list of people', 'employee list',
    'department roster', 'team members',
    
    # Specific lookups
    'specific person', 'particular employee', 'find employee',
    'look up', 'search for employee'
]

CONFIG_KEYWORDS = [
    # Earnings/Deductions
    'earning', 'earnings', 'earning code', 'earn code', 'earning type',
    'deduction', 'deductions', 'deduction code', 'deduction type',
    'benefit', 'benefits', 'benefit plan',
    
    # Pay configuration
    'pay code', 'pay frequency', 'pay group', 'pay rule', 'pay policy',
    'pay period', 'payroll schedule', 'pay cycle',
    
    # System/GL config
    'gl', 'general ledger', 'account code', 'account mapping', 'gl mapping',
    'chart of accounts', 'cost center',
    'tax', 'taxes', 'withholding', 'tax code',
    
    # Time/Leave config
    'accrual', 'pto', 'leave', 'time off', 'vacation', 'sick',
    'time code', 'attendance', 'schedule',
    
    # Rules/Setup
    'rule', 'rules', 'policy', 'policies', 'business rule',
    'configuration', 'config', 'setup', 'setting', 'settings',
    'validation', 'mapping', 'template'
]

DATA_EXTRACTION_KEYWORDS = [
    'list', 'list all', 'show all', 'give me all', 'what are the',
    'how many', 'count', 'total', 'number of',
    'table', 'spreadsheet', 'export', 'data',
    'calculate', 'sum', 'average', 'compare',
    'all the', 'every', 'each'
]


def classify_query(query: str, chunks: List[Dict] = None) -> str:
    """
    Classify query as 'config', 'employee', or 'mixed'
    
    Returns:
        'config' - No PII, can go direct to Claude
        'employee' - Has PII, needs local LLM + sanitization
    """
    query_lower = query.lower()
    
    # Check for employee data indicators
    has_employee_keywords = any(kw in query_lower for kw in EMPLOYEE_DATA_KEYWORDS)
    
    # Check for config indicators
    has_config_keywords = any(kw in query_lower for kw in CONFIG_KEYWORDS)
    
    # If clearly config-related and no employee keywords, it's config
    if has_config_keywords and not has_employee_keywords:
        logger.info(f"Query classified as CONFIG: '{query[:50]}...'")
        return 'config'
    
    # If has employee keywords, treat as employee data
    if has_employee_keywords:
        logger.info(f"Query classified as EMPLOYEE: '{query[:50]}...'")
        return 'employee'
    
    # Default to config (safer for speed, config data isn't PII)
    logger.info(f"Query classified as CONFIG (default): '{query[:50]}...'")
    return 'config'


def select_local_model(query: str, chunks: List[Dict] = None) -> str:
    """
    Select local model for queries
    
    Available models and their use cases:
    - qwen2.5-coder:14b: SQL, JSON, data extraction, tables, lists, calculations
    - mistral:7b: General reasoning, analysis, synthesis, natural language
    - deepseek-r1:14b: Complex reasoning (but outputs <think> tags - use carefully)
    
    DO NOT USE phi3 models - they return garbage responses.
    """
    query_lower = query.lower()
    
    # Check for data extraction patterns
    is_data_extraction = any(kw in query_lower for kw in DATA_EXTRACTION_KEYWORDS)
    
    # Check if chunks are mostly tabular
    if chunks:
        tabular_count = sum(1 for c in chunks 
                          if 'table' in str(c.get('metadata', {}).get('chunk_type', '')).lower())
        mostly_tabular = tabular_count > len(chunks) * 0.3
    else:
        mostly_tabular = False
    
    if is_data_extraction or mostly_tabular:
        logger.info("Selected model: Qwen (data extraction)")
        return 'qwen2.5-coder:14b'
    
    logger.info("Selected model: mistral:7b (general)")
    return 'mistral:7b'


# =============================================================================
# PII SANITIZATION
# =============================================================================

class PIISanitizer:
    """
    Sanitizes PII from text before sending to Claude
    Only sanitizes actual PII - not job titles or departments
    """
    
    SSN_PATTERN = r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b'
    PHONE_PATTERN = r'\b(?:\+1[-\s]?)?\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{4}\b'
    EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    DOB_PATTERN = r'\b(?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b'
    SALARY_PATTERN = r'\$[\d,]+(?:\.\d{2})?'
    
    def __init__(self):
        self.name_counter = 0
        self.name_map = {}
    
    def _get_placeholder(self, name: str) -> str:
        if name not in self.name_map:
            self.name_counter += 1
            letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            idx = (self.name_counter - 1) % 26
            self.name_map[name] = f"[Person {letters[idx]}]"
        return self.name_map[name]
    
    def _salary_to_range(self, match) -> str:
        try:
            amount = float(match.group(0).replace('$', '').replace(',', ''))
            if amount < 30000: return "[under $30K]"
            elif amount < 50000: return "[~$30K-50K]"
            elif amount < 75000: return "[~$50K-75K]"
            elif amount < 100000: return "[~$75K-100K]"
            elif amount < 150000: return "[~$100K-150K]"
            else: return "[~$150K+]"
        except Exception:
            return "[SALARY]"
    
    def sanitize(self, text: str) -> str:
        """Remove PII from text - only SSN, phone, email, DOB, salary"""
        if not text:
            return text
        
        result = text
        
        # Remove obvious PII patterns - these are unambiguous
        result = re.sub(self.SSN_PATTERN, '[SSN]', result)
        result = re.sub(self.PHONE_PATTERN, '[PHONE]', result)
        result = re.sub(self.EMAIL_PATTERN, '[EMAIL]', result)
        result = re.sub(self.DOB_PATTERN, '[DOB]', result)
        result = re.sub(self.SALARY_PATTERN, self._salary_to_range, result)
        
        # NOTE: We do NOT sanitize names anymore - too many false positives
        # Job titles, departments, locations all get wrongly sanitized
        # The data already has employee_number as identifier
        
        return result
    
    def reset(self):
        self.name_counter = 0
        self.name_map = {}


# =============================================================================
# LLM ORCHESTRATOR
# =============================================================================

class LLMOrchestrator:
    """
    Orchestrates LLM calls with smart routing and PII protection
    """
    
    def __init__(self):
        # Ollama configuration (RunPod or Hetzner)
        self.ollama_url = os.getenv("LLM_ENDPOINT", "").rstrip('/')
        self.ollama_username = os.getenv("LLM_USERNAME", "")
        self.ollama_password = os.getenv("LLM_PASSWORD", "")
        
        # Claude configuration
        self.claude_api_key = os.getenv("CLAUDE_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        self.claude_model = "claude-sonnet-4-20250514"
        
        # Sanitizer
        self.sanitizer = PIISanitizer()
        
        logger.info(f"LLMOrchestrator initialized")
        logger.info(f"  Ollama: {self.ollama_url or 'NOT SET!'}")
        logger.info(f"  Claude: {'configured' if self.claude_api_key else 'NOT SET!'}")
    
    def _call_ollama(self, model: str, prompt: str, system_prompt: str = None, project_id: str = None, processor: str = "chat") -> Tuple[Optional[str], bool]:
        """Call local Ollama instance with metrics tracking"""
        if not self.ollama_url:
            logger.error("LLM_ENDPOINT not configured!")
            return "LLM_ENDPOINT not configured", False
        
        start_time = time.time()
        
        try:
            url = f"{self.ollama_url}/api/generate"
            
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            
            payload = {
                "model": model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 4096  # Increased for complex multi-table JOINs
                }
            }
            
            logger.info(f"Calling Ollama: {model} ({len(full_prompt)} chars)")
            
            # Use auth if configured (Hetzner), skip if not (RunPod)
            if self.ollama_username and self.ollama_password:
                response = requests.post(
                    url, json=payload,
                    auth=HTTPBasicAuth(self.ollama_username, self.ollama_password),
                    timeout=60
                )
            else:
                response = requests.post(url, json=payload, timeout=60)
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            if response.status_code != 200:
                logger.error(f"Ollama error {response.status_code}: {response.text[:200]}")
                # Record failed LLM call
                if METRICS_AVAILABLE:
                    MetricsService.record_llm_call(
                        processor=processor,
                        provider='ollama',
                        model=model,
                        duration_ms=duration_ms,
                        success=False,
                        error_message=f"HTTP {response.status_code}",
                        project_id=project_id
                    )
                return f"Ollama error: {response.status_code}", False
            
            result = response.json().get("response", "")
            logger.info(f"Ollama response: {len(result)} chars in {duration_ms}ms")
            
            # Record successful LLM call
            if METRICS_AVAILABLE:
                MetricsService.record_llm_call(
                    processor=processor,
                    provider='ollama',
                    model=model,
                    duration_ms=duration_ms,
                    tokens_in=len(full_prompt) // 4,  # Rough estimate
                    tokens_out=len(result) // 4,
                    success=True,
                    project_id=project_id
                )
            
            return result, True
            
        except requests.exceptions.Timeout:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error("Ollama timeout")
            if METRICS_AVAILABLE:
                MetricsService.record_llm_call(
                    processor=processor,
                    provider='ollama',
                    model=model,
                    duration_ms=duration_ms,
                    success=False,
                    error_message="Timeout",
                    project_id=project_id
                )
            return None, False
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Ollama error: {e}")
            if METRICS_AVAILABLE:
                MetricsService.record_llm_call(
                    processor=processor,
                    provider='ollama',
                    model=model,
                    duration_ms=duration_ms,
                    success=False,
                    error_message=str(e)[:200],
                    project_id=project_id
                )
            return str(e), False
    
    def _call_claude(self, prompt: str, system_prompt: str, project_id: str = None, operation: str = "chat") -> Tuple[str, bool]:
        """Call Claude API with retry for rate limits and metrics tracking"""
        if not self.claude_api_key:
            return "Claude API key not configured", False
        
        import time
        max_retries = 3
        start_time = time.time()
        
        for attempt in range(max_retries):
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=self.claude_api_key)
                
                logger.info(f"Calling Claude ({len(prompt)} chars), attempt {attempt + 1}")
                
                response = client.messages.create(
                    model=self.claude_model,
                    max_tokens=4096,
                    system=system_prompt,
                    messages=[{"role": "user", "content": prompt}]
                )
                
                result = response.content[0].text
                duration_ms = int((time.time() - start_time) * 1000)
                logger.info(f"Claude response: {len(result)} chars in {duration_ms}ms")
                
                # Get usage for metrics
                usage = response.usage
                tokens_in = usage.input_tokens if usage else 0
                tokens_out = usage.output_tokens if usage else 0
                
                # Log cost (existing)
                try:
                    from backend.utils.cost_tracker import log_cost, CostService, calculate_cost
                    log_cost(
                        service=CostService.CLAUDE,
                        operation=operation,
                        tokens_in=tokens_in,
                        tokens_out=tokens_out,
                        project_id=project_id,
                        metadata={"model": self.claude_model}
                    )
                    # Calculate cost for metrics
                    cost_usd = calculate_cost(CostService.CLAUDE, tokens_in=tokens_in, tokens_out=tokens_out)
                except Exception as cost_err:
                    logger.debug(f"Cost tracking failed: {cost_err}")
                    cost_usd = 0
                
                # Record LLM call metrics (NEW)
                if METRICS_AVAILABLE:
                    MetricsService.record_llm_call(
                        processor=operation,
                        provider='claude',
                        model=self.claude_model,
                        duration_ms=duration_ms,
                        tokens_in=tokens_in,
                        tokens_out=tokens_out,
                        cost_usd=cost_usd,
                        success=True,
                        project_id=project_id
                    )
                
                return result, True
                
            except anthropic.RateLimitError as e:
                wait_time = (attempt + 1) * 30  # 30s, 60s, 90s
                logger.warning(f"Rate limit hit, waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
                else:
                    duration_ms = int((time.time() - start_time) * 1000)
                    if METRICS_AVAILABLE:
                        MetricsService.record_llm_call(
                            processor=operation,
                            provider='claude',
                            model=self.claude_model,
                            duration_ms=duration_ms,
                            success=False,
                            error_message="Rate limit exceeded",
                            project_id=project_id
                        )
                    return f"Rate limit exceeded after {max_retries} retries. Please wait a minute and try again.", False
                    
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                logger.error(f"Claude error: {e}")
                if METRICS_AVAILABLE:
                    MetricsService.record_llm_call(
                        processor=operation,
                        provider='claude',
                        model=self.claude_model,
                        duration_ms=duration_ms,
                        success=False,
                        error_message=str(e)[:200],
                        project_id=project_id
                    )
                return str(e), False
        
        return "Unknown error in Claude call", False
    
    def _build_context(self, chunks: List[Dict], max_chunks: int = 30) -> str:
        """Build context string from chunks"""
        context_parts = []
        
        for i, chunk in enumerate(chunks[:max_chunks], 1):
            meta = chunk.get('metadata', {})
            filename = meta.get('filename', meta.get('source', 'Unknown'))
            sheet = meta.get('parent_section', '')
            text = chunk.get('document', chunk.get('text', ''))
            
            source = f"{filename}"
            if sheet:
                source = f"{filename} - {sheet}"
            
            context_parts.append(f"[Source {i}: {source}]\n{text}")
        
        return "\n\n---\n\n".join(context_parts)
    
    def _determine_query_type(self, query: str, chunks: List[Dict]) -> str:
        """
        Public method to classify query type
        Used by chat router for status updates
        """
        from utils.llm_orchestrator import classify_query
        return classify_query(query, chunks)
    
    def process_query(self, query: str, chunks: List[Dict]) -> Dict[str, Any]:
        """
        Main orchestration method
        
        Flow:
        1. Classify query (config vs employee)
        2. Route appropriately:
           - Config: Direct to Claude (fast)
           - Employee: Local LLM → Sanitize → Claude
        """
        self.sanitizer.reset()
        
        result = {
            "response": "",
            "models_used": [],
            "query_type": "",
            "sanitized": False,
            "error": None
        }
        
        # Build context
        context = self._build_context(chunks)
        logger.info(f"Context: {len(chunks)} chunks, {len(context)} chars")
        
        # Classify query
        query_type = classify_query(query, chunks)
        result["query_type"] = query_type
        
        # =================================================================
        # CONFIG QUERY: Direct to Claude (fast, no PII)
        # =================================================================
        if query_type == 'config':
            logger.info("CONFIG path: Direct to Claude")
            
            system_prompt = """You are a data analyst. Analyze the data provided and answer the question.

RULES:
1. Look at the actual column names and data values
2. Figure out what the columns mean from context and values
3. Give actual counts and real data - never placeholders like [Number] or [Employee A]
4. For LIST requests with MORE than 25 results: ASK the user "There are X items. Would you like me to list them all in the chat or export to an Excel file?"
5. For LIST requests with 25 or fewer results: Show all of them
6. Never describe what to do - just do it and give the answer"""

            user_prompt = f"""Question: {query}

DATA:
{context}

Analyze the data. Answer the question with real numbers and real values from the data."""

            response, success = self._call_claude(user_prompt, system_prompt)
            result["models_used"].append("claude-sonnet-4")
            
            if success:
                result["response"] = response
            else:
                result["error"] = response
                result["response"] = f"Error: {response}"
            
            return result
        
        # =================================================================
        # EMPLOYEE QUERY: Direct to Claude with sanitized data
        # (Local LLM disabled - was returning garbage)
        # =================================================================
        logger.info("EMPLOYEE path: Direct to Claude (local LLM disabled)")
        
        # Sanitize context before sending to Claude
        sanitized_context = self.sanitizer.sanitize(context)
        result["sanitized"] = True
        
        system_prompt = """You are a data analyst. Analyze the data provided and answer the question.

RULES:
1. Look at the actual column names and data values
2. Figure out what the columns mean from context and values
3. Give actual counts and real data - never placeholders like [Number] or [Employee A]
4. For LIST requests with MORE than 25 results: Tell the user "There are X items. I can list them all here or you can download as Excel using the download button below."
5. For LIST requests with 25 or fewer results: Show all of them
6. Never describe what to do - just do it and give the answer
7. Keep any [REDACTED] or sanitized placeholders as-is - those are for privacy"""

        user_prompt = f"""Question: {query}

DATA:
{sanitized_context}

Analyze the data. Answer the question with real numbers and real values from the data."""

        response, success = self._call_claude(user_prompt, system_prompt)
        result["models_used"].append("claude-sonnet-4")
        
        if success:
            result["response"] = response
        else:
            result["error"] = response
            result["response"] = f"Error: {response}"
        
        return result
    
    def check_status(self) -> Dict[str, Any]:
        """Check system status"""
        status = {
            "ollama_configured": bool(self.ollama_url),
            "ollama_url": self.ollama_url,
            "claude_configured": bool(self.claude_api_key),
            "models": []
        }
        
        # Check Ollama models
        if self.ollama_url:
            try:
                url = f"{self.ollama_url}/api/tags"
                if self.ollama_username:
                    resp = requests.get(url, auth=HTTPBasicAuth(self.ollama_username, self.ollama_password), timeout=10)
                else:
                    resp = requests.get(url, timeout=10)
                
                if resp.status_code == 200:
                    status["models"] = [m["name"] for m in resp.json().get("models", [])]
                    status["ollama_status"] = "connected"
                else:
                    status["ollama_status"] = f"error: {resp.status_code}"
            except Exception as e:
                status["ollama_status"] = f"error: {e}"
        
        return status
    
    def generate_sql(self, prompt: str, schema_columns: set = None) -> Dict[str, Any]:
        """
        Generate SQL query from natural language using LOCAL LLM.
        
        Strategy:
        1. Try DeepSeek (best for code/SQL)
        2. If invalid columns, retry with Mistral
        3. Claude is NOT used - local LLMs handle SQL
        
        Args:
            prompt: Natural language query with schema context
            schema_columns: Set of valid column names for validation
            
        Returns:
            {'sql': 'SELECT ...', 'model': '...', 'success': True/False}
        """
        # ALWAYS use local LLM for SQL - no Claude needed
        return self._generate_sql_local(prompt, schema_columns)
    
    def _generate_sql_local(self, prompt: str, schema_columns: set = None) -> Dict[str, Any]:
        """
        Generate SQL using SQLCoder (specialized text-to-SQL model).
        
        SQLCoder outperforms GPT-4 on text-to-SQL tasks and is specifically
        trained to avoid column hallucination - our main problem with DeepSeek.
        """
        if not self.ollama_url:
            return {"sql": None, "error": "No LLM configured", "success": False}
        
        # Qwen 14B is best for SQL - try it twice with different prompts
        attempts = [
            ('qwen2.5-coder:14b', 'sqlcoder_format'),
            ('qwen2.5-coder:14b', 'sqlcoder_strict'),
            ('qwen2.5-coder:14b', 'fallback')
        ]
        last_invalid_cols = []
        best_sql = None
        best_invalid = None
        
        for attempt, (model, prompt_type) in enumerate(attempts):
            try:
                # Build prompt based on attempt type
                if prompt_type == 'sqlcoder_format':
                    # SQLCoder's expected format (from Defog documentation)
                    local_prompt = f"""### Task
Generate a SQL query to answer the question below.

### Database Schema
{prompt}

### Answer
Given the database schema, here is the SQL query that answers the question:
```sql
SELECT"""

                elif prompt_type == 'sqlcoder_strict':
                    # Stricter version with explicit column constraints
                    col_list = ', '.join(sorted(schema_columns)[:50]) if schema_columns else ''
                    local_prompt = f"""### Task
Generate a SQL query. Use ONLY these columns: {col_list}

DO NOT USE these columns (they don't exist): {', '.join(last_invalid_cols)}

### Database Schema
{prompt}

### Answer
```sql
SELECT"""

                else:  # fallback prompt style
                    local_prompt = f"""SQL query only. No explanation. Start with SELECT.

{prompt}

SELECT"""
                
                response, success = self._call_ollama(model, local_prompt)
                
                if success and response:
                    sql = response.strip()
                    
                    # FIRST: Check if response is prose (before any modifications)
                    if self._is_prose_not_sql(sql):
                        logger.warning(f"[SQL-LOCAL] {model} ({prompt_type}) returned prose, skipping")
                        continue
                    
                    # SQLCoder and fallback prompts end with "SELECT" - prepend it
                    if prompt_type in ['sqlcoder_format', 'sqlcoder_strict', 'fallback'] and not sql.upper().startswith('SELECT'):
                        sql = 'SELECT ' + sql
                    
                    if sql.startswith("```"):
                        sql = sql.split("```")[1]
                        if sql.startswith("sql"):
                            sql = sql[3:]
                    
                    # CRITICAL: Strip trailing explanations/prose
                    sql = self._clean_sql_output(sql)
                    
                    sql_upper = sql.upper().strip()
                    if not (sql_upper.startswith('SELECT') or sql_upper.startswith('WITH')):
                        logger.warning(f"[SQL-LOCAL] {model} ({prompt_type}) returned non-SQL: {sql[:80]}...")
                        continue
                    
                    if schema_columns:
                        invalid_cols = self._validate_sql_columns(sql, schema_columns)
                        
                        if invalid_cols:
                            logger.warning(f"[SQL-LOCAL] {model} ({prompt_type}) produced invalid columns: {invalid_cols}")
                            last_invalid_cols = invalid_cols
                            
                            # Keep track of best attempt (fewest invalid columns)
                            # But only if it's actually SQL (extra safety check)
                            if not self._is_prose_not_sql(sql):
                                if best_sql is None or len(invalid_cols) < len(best_invalid):
                                    best_sql = sql
                                    best_invalid = invalid_cols
                            continue
                    
                    logger.info(f"[SQL-LOCAL] {model} ({prompt_type}) generated valid SQL")
                    return {"sql": sql, "model": model, "success": True}
                    
            except Exception as e:
                logger.error(f"[SQL-LOCAL] {model} error: {e}")
                continue
        
        # ALL ATTEMPTS FAILED - Try auto-correction on best attempt
        if best_sql and best_invalid and schema_columns:
            logger.warning(f"[SQL-LOCAL] Attempting auto-correction of {len(best_invalid)} invalid columns: {best_invalid}")
            logger.info(f"[SQL-LOCAL] Best SQL preview: {best_sql[:100]}...")
            
            # Clean the SQL first before correcting
            best_sql = self._clean_sql_output(best_sql)
            
            corrected_sql = self._auto_correct_columns(best_sql, best_invalid, schema_columns)
            
            if corrected_sql:
                # Validate corrected SQL
                remaining_invalid = self._validate_sql_columns(corrected_sql, schema_columns)
                if not remaining_invalid:
                    logger.info(f"[SQL-LOCAL] Auto-correction successful!")
                    return {"sql": corrected_sql, "model": "auto-corrected", "success": True}
                else:
                    logger.warning(f"[SQL-LOCAL] Auto-correction still has invalid: {remaining_invalid}")
        
        return {"sql": None, "error": "All local models failed", "success": False}
    
    def _clean_sql_output(self, sql: str) -> str:
        """
        Clean up SQL output from LLM - remove trailing explanations, markdown, etc.
        """
        sql = sql.strip()
        
        # Remove DeepSeek tokenizer artifacts
        sql = re.sub(r'<｜[^｜]+｜>', '', sql)  # Remove <｜...｜> patterns
        sql = re.sub(r'<\|[^|]+\|>', '', sql)   # Remove <|...|> patterns (ASCII variant)
        
        # Remove trailing semicolons
        sql = sql.rstrip(';')
        
        # Cut off at common explanation markers
        cut_markers = [
            '\n###',           # Markdown headers
            '\n##',
            '\n#',
            '\n\nExplanation',
            '\n\nThis query',
            '\n\nNote:',
            '\n\nThe query',
            '\n\n---',
            '\n```',           # Markdown code blocks
            '\nPlease note',
            '\nThis SQL',
        ]
        
        for marker in cut_markers:
            if marker in sql:
                sql = sql.split(marker)[0]
        
        # Remove any lines that start with # (comments/headers)
        lines = sql.split('\n')
        clean_lines = [l for l in lines if not l.strip().startswith('#')]
        sql = '\n'.join(clean_lines)
        
        return sql.strip()
    
    def _is_prose_not_sql(self, text: str) -> bool:
        """
        Detect if LLM response is prose explanation instead of SQL.
        """
        text_lower = text.lower().strip()
        
        # Prose indicators - if text starts with these, it's not SQL
        prose_starts = [
            'to answer',
            'to find',
            'to get',
            'to solve',
            'to query',
            'to determine',
            'to check',
            'to verify',
            'let me',
            'i would',
            'i will',
            'i\'ll',
            'we need',
            'we can',
            'we should',
            'you can',
            'you need',
            'the query',
            'this query',
            'here is',
            'here\'s',
            'first,',
            'based on',
            'assuming',
            'unfortunately',
            'i cannot',
            'i don\'t',
            'in order to',
        ]
        
        for starter in prose_starts:
            if text_lower.startswith(starter):
                return True
        
        # If first word is not a SQL keyword, likely prose
        sql_starters = ['select', 'with', 'insert', 'update', 'delete', 'create', 'drop', 'alter', 'count', '*']
        first_word = text_lower.split()[0] if text_lower.split() else ''
        
        if first_word and first_word not in sql_starters:
            # Common short prose words
            if first_word in ['to', 'in', 'the', 'a', 'an', 'for', 'as', 'if', 'it', 'is', 'are', 'this', 'that']:
                return True
            # Check if it looks like a column/table reference (has underscore or is short)
            if '_' not in first_word and len(first_word) > 10:
                return True
        
        return False
    
    def _auto_correct_columns(self, sql: str, invalid_cols: List[str], valid_columns: set) -> Optional[str]:
        """
        Try to fix invalid columns by fuzzy matching to valid ones.
        CAREFUL: Don't break quoted column names with spaces.
        """
        from difflib import SequenceMatcher
        
        corrected_sql = sql
        valid_lower = {c.lower(): c for c in valid_columns}
        
        # Common column name mappings (LLM hallucinations → actual columns)
        known_fixes = {
            'hourly_rate': 'hourly_pay_rate',
            'hourlyrate': 'hourly_pay_rate',
            'pay_rate': 'hourly_pay_rate',
            'employee_id': 'employee_number',
            'employeeid': 'employee_number',
            'emp_id': 'employee_number',
            'employment_status': 'fullpart_time_code',
            'pt_ft': 'fullpart_time_code',
            'earnings_type': 'type_code',
            'earnings_type_id': 'type_code',
        }
        
        # Skip dangerous partial replacements
        skip_words = {'employee', 'personal', 'status', 'rate', 'hourly', 'type', 'code', 'id', 'name'}
        
        for invalid in set(invalid_cols):  # dedupe
            invalid_lower = invalid.lower()
            
            # Skip very short or common SQL noise
            if len(invalid_lower) < 4 or invalid_lower in ['db', 'com', 'the', 'and', 'for']:
                continue
            
            # Skip single common words that might be parts of multi-word columns
            if invalid_lower in skip_words:
                logger.info(f"[SQL-AUTO] Skipping risky partial: '{invalid}'")
                continue
            
            # Check known fixes first (only full column names)
            if invalid_lower in known_fixes:
                target = known_fixes[invalid_lower]
                if target.lower() in valid_lower:
                    best_match = valid_lower[target.lower()]
                    logger.info(f"[SQL-AUTO] Known fix: '{invalid}' → '{best_match}'")
                    
                    # Pattern: .column_name or ."column_name" (NOT partial match inside quotes)
                    # Use negative lookbehind/ahead to avoid partial matches
                    corrected_sql = re.sub(
                        r'\.(' + re.escape(invalid) + r')(?![a-z_])',  # Not followed by more letters
                        f'."{best_match}"',
                        corrected_sql,
                        flags=re.IGNORECASE
                    )
                    corrected_sql = re.sub(
                        r'\."(' + re.escape(invalid) + r')"',  # Exact quoted match
                        f'."{best_match}"',
                        corrected_sql,
                        flags=re.IGNORECASE
                    )
                    continue
            
            # Fuzzy match - only for underscore-separated names (safe)
            if '_' not in invalid:
                continue  # Skip single words for fuzzy - too risky
            
            best_match = None
            best_score = 0.7  # Higher threshold for fuzzy
            
            for valid_col in valid_lower.keys():
                score = SequenceMatcher(None, invalid_lower, valid_col).ratio()
                if score > best_score:
                    best_score = score
                    best_match = valid_lower[valid_col]
            
            if best_match:
                logger.info(f"[SQL-AUTO] Fuzzy fix: '{invalid}' → '{best_match}' (score: {best_score:.2f})")
                corrected_sql = re.sub(
                    r'\.(' + re.escape(invalid) + r')(?![a-z_])',
                    f'."{best_match}"',
                    corrected_sql,
                    flags=re.IGNORECASE
                )
        
        # Clean up double quotes that might have been introduced
        corrected_sql = corrected_sql.replace('""', '"')
        
        return corrected_sql if corrected_sql != sql else None
    
    def _validate_sql_columns(self, sql: str, schema_columns: set) -> List[str]:
        """
        Validate that column references in SQL exist in schema.
        Returns list of invalid column names.
        """
        import re
        
        # Normalize schema columns to lowercase
        valid_cols = {c.lower() for c in schema_columns}
        
        # Add common SQL keywords and functions
        valid_cols.update([
            'count', 'sum', 'avg', 'min', 'max', 'as', 'and', 'or', 'not', 
            'null', 'true', 'false', 'on', 'where', 'from', 'join', 'select',
            'try_cast', 'double', 'integer', 'varchar', 'ilike', 'like',
            'float', 'int', 'text', 'boolean', 'date', 'timestamp'
        ])
        
        invalid = []
        
        # Pattern 1: Quoted columns after dot: ."column_name"
        quoted_cols = re.findall(r'\."([^"]+)"', sql)
        for col in quoted_cols:
            col_lower = col.lower()
            # Skip multi-word columns (with spaces) - these are custom names
            if ' ' in col:
                continue
            if col_lower not in valid_cols and '__' not in col_lower:
                if len(col_lower) >= 4:  # Skip very short
                    invalid.append(col)
        
        # Pattern 2: Bare columns after dot: .column_name (no quotes)
        bare_cols = re.findall(r'\.([a-z_][a-z0-9_]*)(?!["\w])', sql.lower())
        for col in bare_cols:
            if col not in valid_cols and '__' not in col:
                if len(col) >= 4:  # Skip very short
                    invalid.append(col)
        
        return list(set(invalid))  # dedupe
    
    def synthesize_answer(
        self, 
        question: str, 
        context: str, 
        expert_prompt: str = None,
        use_claude_fallback: bool = True
    ) -> Dict[str, Any]:
        """
        Synthesize an expert answer using local LLMs first.
        
        Flow:
        1. Try Mistral (best for synthesis/reasoning)
        2. Try other Ollama models if available
        3. Fall back to Claude ONLY if local fails and use_claude_fallback=True
        
        Args:
            question: User's question
            context: Data/context to analyze
            expert_prompt: Optional expert system prompt (from expert_context_registry)
            use_claude_fallback: Whether to fall back to Claude if local fails
            
        Returns:
            Dict with: response, model_used, success, error
        """
        result = {
            "response": "",
            "model_used": None,
            "success": False,
            "error": None
        }
        
        # Build system prompt
        if expert_prompt:
            system_prompt = expert_prompt
            logger.warning(f"[SYNTHESIS] Using expert prompt ({len(expert_prompt)} chars)")
        else:
            logger.warning(f"[SYNTHESIS] Using default prompt (no expert)")
            system_prompt = """You are an expert implementation consultant analyzing data.

Your responses should be:
- Direct and actionable
- Backed by the data provided
- Clear about confidence levels
- Professional but conversational

When presenting findings:
- Lead with the key number/insight
- Provide context for what it means
- Note any caveats or limitations
- Be specific about data sources"""
        
        # Build user prompt
        user_prompt = f"""Question: {question}

Data Context:
{context[:12000]}

Analyze the data and provide a clear, direct answer. Focus on the key insight first, then supporting details."""
        
        # ==============================================================
        # STEP 1: Try local models for synthesis
        # mistral:7b is best for natural language synthesis
        # qwen2.5-coder is for structured/JSON output, NOT synthesis
        # deepseek-r1 outputs <think> tags that need stripping
        # ==============================================================
        if self.ollama_url:
            models_to_try = [
                'mistral:7b',
            ]
            
            for model in models_to_try:
                logger.info(f"[SYNTHESIS] Trying {model}...")
                response, success = self._call_ollama(model, user_prompt, system_prompt)
                
                if success and response and len(response.strip()) > 50:
                    # Validate response isn't garbage
                    if not self._is_garbage_synthesis(response):
                        result["response"] = self._clean_unprofessional_language(response)
                        result["model_used"] = model
                        result["success"] = True
                        logger.info(f"[SYNTHESIS] {model} succeeded ({len(response)} chars)")
                        return result
                    else:
                        logger.warning(f"[SYNTHESIS] {model} returned garbage, trying next")
                else:
                    logger.warning(f"[SYNTHESIS] {model} failed or empty response")
        else:
            logger.warning("[SYNTHESIS] Ollama not configured, skipping local models")
        
        # ==============================================================
        # STEP 2: Fall back to Claude ONLY if enabled and local failed
        # ==============================================================
        if use_claude_fallback and self.claude_api_key:
            logger.warning("[SYNTHESIS] Local models failed, falling back to Claude")
            response, success = self._call_claude(user_prompt, system_prompt)
            
            if success:
                result["response"] = self._clean_unprofessional_language(response)
                result["model_used"] = "claude-sonnet-4-fallback"
                result["success"] = True
                logger.info(f"[SYNTHESIS] Claude fallback succeeded ({len(response)} chars)")
                return result
            else:
                result["error"] = response
                logger.error(f"[SYNTHESIS] Claude fallback also failed: {response}")
        else:
            if not use_claude_fallback:
                result["error"] = "Local models failed and Claude fallback disabled"
            else:
                result["error"] = "Local models failed and no Claude API key"
        
        return result
    
    def _is_garbage_synthesis(self, response: str) -> bool:
        """
        Detect if synthesis response is garbage (hallucinated, nonsensical, etc.)
        """
        response_lower = response.lower().strip()
        
        # Too short
        if len(response.strip()) < 50:
            return True
        
        # Refusal patterns
        refusal_patterns = [
            "i cannot",
            "i can't",
            "i don't have",
            "i'm not able",
            "as an ai",
            "i apologize",
            "sorry, but",
            "i need more",
            "please provide",
            "could you clarify",
        ]
        
        if any(pattern in response_lower for pattern in refusal_patterns):
            return True
        
        # Mostly punctuation or repeated characters
        alpha_ratio = sum(c.isalpha() for c in response) / max(len(response), 1)
        if alpha_ratio < 0.5:
            return True
        
        return False
    
    def _clean_unprofessional_language(self, response: str) -> str:
        """
        Remove unprofessional persona language from LLM responses.
        This catches cow/farm themed phrases from the 'bessie' persona
        and other inappropriate casual language for a professional platform.
        """
        if not response:
            return response
        
        # Phrases to remove entirely (usually at start or end of response)
        phrases_to_remove = [
            # Cow/farm themed
            "moo-ving", "moooving", "moo-ve", "udderly", "pasture", 
            "graze", "herd", "stampede", "corral",
            "anything else i can help you wrangle",
            "help you wrangle",
            "wrangle",
            "howdy partner",
            "howdy",
            "yeehaw",
            "giddy up",
            # Overly casual greetings/closings
            "hope you're having a great day",
            "hope you're doing well",
            "hello there!",
        ]
        
        result = response
        for phrase in phrases_to_remove:
            # Case-insensitive replacement
            pattern = re.compile(re.escape(phrase), re.IGNORECASE)
            result = pattern.sub('', result)
        
        # Clean up any double spaces or awkward punctuation left behind
        result = re.sub(r'\s+', ' ', result)
        result = re.sub(r'\s+([.,!?])', r'\1', result)
        result = re.sub(r'([.,!?])\s*([.,!?])', r'\1', result)
        
        # Remove empty sentences
        result = re.sub(r'\.\s*\.', '.', result)
        result = re.sub(r'!\s*!', '!', result)
        
        return result.strip()

    def generate_json(
        self, 
        prompt: str, 
        system_prompt: str = None,
        use_claude_fallback: bool = True,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """
        Generate structured JSON output using local LLMs first.
        
        Use this for:
        - Entity extraction (FEINs, company names)
        - Column type inference
        - Document analysis returning structured findings
        - Any task requiring JSON output
        
        Flow:
        1. Try Mistral (good at following JSON format instructions)
        2. Fall back to Claude ONLY if local fails
        
        Args:
            prompt: The prompt requesting JSON output
            system_prompt: Optional system prompt
            use_claude_fallback: Whether to fall back to Claude if local fails
            max_tokens: Maximum tokens for response
            
        Returns:
            Dict with: response (parsed JSON or raw), raw_text, model_used, success, error
        """
        result = {
            "response": None,
            "raw_text": "",
            "model_used": None,
            "success": False,
            "error": None
        }
        
        # Default system prompt for JSON tasks
        if not system_prompt:
            system_prompt = """You are a precise data extraction assistant.
Always respond with valid JSON only - no explanations, no markdown, no code blocks.
If you cannot extract the requested data, return an appropriate empty JSON structure."""
        
        # ==============================================================
        # STEP 1: Try qwen2.5-coder (best for structured JSON output)
        # phi3 models are unreliable for JSON - skip them
        # ==============================================================
        if self.ollama_url:
            models_to_try = [
                'qwen2.5-coder:14b',
            ]
            
            for model in models_to_try:
                logger.info(f"[JSON-GEN] Trying {model}...")
                response_text, success = self._call_ollama(model, prompt, system_prompt)
                
                if success and response_text and len(response_text.strip()) > 5:
                    # Try to parse as JSON
                    parsed = self._try_parse_json(response_text)
                    if parsed is not None:
                        result["response"] = parsed
                        result["raw_text"] = response_text
                        result["model_used"] = model
                        result["success"] = True
                        logger.info(f"[JSON-GEN] {model} succeeded")
                        return result
                    else:
                        logger.warning(f"[JSON-GEN] {model} returned invalid JSON, trying next")
                else:
                    logger.warning(f"[JSON-GEN] {model} failed or empty response")
        else:
            logger.warning("[JSON-GEN] Ollama not configured, skipping local models")
        
        # ==============================================================
        # STEP 2: Fall back to Claude ONLY if enabled
        # ==============================================================
        if use_claude_fallback and self.claude_api_key:
            logger.warning("[JSON-GEN] Local models failed, falling back to Claude")
            response_text, success = self._call_claude(prompt, system_prompt)
            
            if success:
                parsed = self._try_parse_json(response_text)
                if parsed is not None:
                    result["response"] = parsed
                    result["raw_text"] = response_text
                    result["model_used"] = "claude-sonnet-4-fallback"
                    result["success"] = True
                    logger.info("[JSON-GEN] Claude fallback succeeded")
                    return result
                else:
                    # Return raw text if JSON parsing fails
                    result["response"] = response_text
                    result["raw_text"] = response_text
                    result["model_used"] = "claude-sonnet-4-fallback"
                    result["success"] = True
                    result["error"] = "Response was not valid JSON"
                    logger.warning("[JSON-GEN] Claude returned non-JSON response")
                    return result
            else:
                result["error"] = response_text
                logger.error(f"[JSON-GEN] Claude fallback also failed: {response_text}")
        else:
            if not use_claude_fallback:
                result["error"] = "Local models failed and Claude fallback disabled"
            else:
                result["error"] = "Local models failed and no Claude API key"
        
        return result
    
    def _try_parse_json(self, text: str) -> Optional[Any]:
        """
        Try to parse JSON from text, handling common formatting issues.
        """
        if not text:
            return None
        
        text = text.strip()
        
        # Remove markdown code blocks if present
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            parts = text.split("```")
            if len(parts) >= 2:
                text = parts[1].strip()
        
        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON object/array in text
        try:
            # Find first { or [
            start_obj = text.find('{')
            start_arr = text.find('[')
            
            if start_obj >= 0 and (start_arr < 0 or start_obj < start_arr):
                # Object
                depth = 0
                for i, c in enumerate(text[start_obj:], start_obj):
                    if c == '{':
                        depth += 1
                    elif c == '}':
                        depth -= 1
                        if depth == 0:
                            return json.loads(text[start_obj:i+1])
            elif start_arr >= 0:
                # Array
                depth = 0
                for i, c in enumerate(text[start_arr:], start_arr):
                    if c == '[':
                        depth += 1
                    elif c == ']':
                        depth -= 1
                        if depth == 0:
                            return json.loads(text[start_arr:i+1])
        except (json.JSONDecodeError, ValueError):
            pass
        
        return None
