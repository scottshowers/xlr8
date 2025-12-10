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
import requests
from requests.auth import HTTPBasicAuth
from typing import List, Dict, Any, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


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
    Select local model for employee data queries
    
    DeepSeek: Data extraction, tables, lists, calculations
    Mistral: General HR understanding, policy interpretation
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
        logger.info("Selected model: DeepSeek (data extraction)")
        return 'deepseek-coder:6.7b'
    
    logger.info("Selected model: Mistral (general)")
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
        except:
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
    
    def _call_ollama(self, model: str, prompt: str, system_prompt: str = None) -> Tuple[Optional[str], bool]:
        """Call local Ollama instance"""
        if not self.ollama_url:
            logger.error("LLM_ENDPOINT not configured!")
            return "LLM_ENDPOINT not configured", False
        
        try:
            url = f"{self.ollama_url}/api/generate"
            
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            
            payload = {
                "model": model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 2048
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
            
            if response.status_code != 200:
                logger.error(f"Ollama error {response.status_code}: {response.text[:200]}")
                return f"Ollama error: {response.status_code}", False
            
            result = response.json().get("response", "")
            logger.info(f"Ollama response: {len(result)} chars")
            return result, True
            
        except requests.exceptions.Timeout:
            logger.error("Ollama timeout")
            return None, False
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            return str(e), False
    
    def _call_claude(self, prompt: str, system_prompt: str, project_id: str = None, operation: str = "chat") -> Tuple[str, bool]:
        """Call Claude API with retry for rate limits"""
        if not self.claude_api_key:
            return "Claude API key not configured", False
        
        import time
        max_retries = 3
        
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
                logger.info(f"Claude response: {len(result)} chars")
                
                # Log cost
                try:
                    from backend.utils.cost_tracker import log_cost, CostService
                    usage = response.usage
                    log_cost(
                        service=CostService.CLAUDE,
                        operation=operation,
                        tokens_in=usage.input_tokens if usage else 0,
                        tokens_out=usage.output_tokens if usage else 0,
                        project_id=project_id,
                        metadata={"model": self.claude_model}
                    )
                except Exception as cost_err:
                    logger.debug(f"Cost tracking failed: {cost_err}")
                
                return result, True
                
            except anthropic.RateLimitError as e:
                wait_time = (attempt + 1) * 30  # 30s, 60s, 90s
                logger.warning(f"Rate limit hit, waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
                else:
                    return f"Rate limit exceeded after {max_retries} retries. Please wait a minute and try again.", False
                    
            except Exception as e:
                logger.error(f"Claude error: {e}")
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
        Generate SQL using local LLM with validation, retry, and auto-correction.
        """
        if not self.ollama_url:
            return {"sql": None, "error": "No LLM configured", "success": False}
        
        # Try DeepSeek twice (with different prompts) before falling back
        attempts = [
            ('deepseek-coder:6.7b', 'initial'),
            ('deepseek-coder:6.7b', 'simplified'),
            ('mistral:7b', 'fallback')
        ]
        last_invalid_cols = []
        best_sql = None
        best_invalid = None
        
        for attempt, (model, prompt_type) in enumerate(attempts):
            try:
                # Build prompt based on attempt type
                if prompt_type == 'initial':
                    local_prompt = f"""You are a SQL generator. Output ONLY a valid SQL SELECT statement. No explanations.

{prompt}

Output ONLY the SQL starting with SELECT:"""

                elif prompt_type == 'simplified':
                    col_list = ', '.join(sorted(schema_columns)[:50]) if schema_columns else ''
                    local_prompt = f"""Generate SQL. Output ONLY the SELECT statement.

VALID COLUMNS: {col_list}

INVALID (do not use): {', '.join(last_invalid_cols)}

{prompt}

SELECT"""

                else:  # fallback
                    local_prompt = f"""SQL query only. No explanation. Start with SELECT.

{prompt}

SELECT"""
                
                response, success = self._call_ollama(model, local_prompt)
                
                if success and response:
                    sql = response.strip()
                    
                    if prompt_type in ['simplified', 'fallback'] and not sql.upper().startswith('SELECT'):
                        sql = 'SELECT ' + sql
                    
                    if sql.startswith("```"):
                        sql = sql.split("```")[1]
                        if sql.startswith("sql"):
                            sql = sql[3:]
                    sql = sql.strip().rstrip(';')
                    
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
            logger.warning(f"[SQL-LOCAL] Attempting auto-correction of {len(best_invalid)} invalid columns")
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
    
    def _auto_correct_columns(self, sql: str, invalid_cols: List[str], valid_columns: set) -> Optional[str]:
        """
        Try to fix invalid columns by fuzzy matching to valid ones.
        """
        from difflib import SequenceMatcher
        
        corrected_sql = sql
        valid_lower = {c.lower(): c for c in valid_columns}
        
        # Common column name mappings (LLM hallucinations → actual columns)
        known_fixes = {
            'hourly_rate': 'hourly_pay_rate',
            'hourly': 'hourly_pay_rate', 
            'rate': 'hourly_pay_rate',
            'employee_id': 'employee_number',
            'emp_id': 'employee_number',
            'id': 'employee_number',
            'employment_status': 'fullpart_time_code',
            'status': 'employment_status_code',
            'pt_ft': 'fullpart_time_code',
        }
        
        for invalid in set(invalid_cols):  # dedupe
            invalid_lower = invalid.lower()
            
            # Skip very short or common SQL noise
            if len(invalid_lower) < 3 or invalid_lower in ['db', 'com', 'id', 'code', 'the', 'and', 'for']:
                continue
            
            # Check known fixes first
            if invalid_lower in known_fixes:
                target = known_fixes[invalid_lower]
                if target.lower() in valid_lower:
                    best_match = valid_lower[target.lower()]
                    logger.info(f"[SQL-AUTO] Known fix: '{invalid}' → '{best_match}'")
                    corrected_sql = re.sub(
                        r'\.\"?' + re.escape(invalid) + r'\"?',
                        f'."{best_match}"',
                        corrected_sql,
                        flags=re.IGNORECASE
                    )
                    continue
            
            # Fuzzy match
            best_match = None
            best_score = 0.6  # Higher threshold
            
            for valid_col in valid_lower.keys():
                if invalid_lower in valid_col:
                    score = 0.85
                elif valid_col in invalid_lower:
                    score = 0.75
                else:
                    score = SequenceMatcher(None, invalid_lower, valid_col).ratio()
                
                if score > best_score:
                    best_score = score
                    best_match = valid_lower[valid_col]
            
            if best_match:
                logger.info(f"[SQL-AUTO] Fuzzy fix: '{invalid}' → '{best_match}' (score: {best_score:.2f})")
                corrected_sql = re.sub(
                    r'\.\"?' + re.escape(invalid) + r'\"?',
                    f'."{best_match}"',
                    corrected_sql,
                    flags=re.IGNORECASE
                )
        
        # Clean up any remaining "column1 column2" patterns (two words that should be one)
        # Pattern: word followed by space and another word after a dot
        corrected_sql = re.sub(r'\"(\w+)\s+(\w+)\"', r'"\1_\2"', corrected_sql)
        
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
            'try_cast', 'double', 'integer', 'varchar', 'ilike', 'like'
        ])
        
        # Extract column references after dots: table.column or table."column"
        dot_cols = re.findall(r'\.\"?([a-z][a-z0-9_]*)\"?', sql.lower())
        
        invalid = []
        for col in dot_cols:
            # Skip if it looks like a table name part (has double underscore pattern)
            if '__' in col:
                continue
            # Skip very short (likely parsing artifacts)
            if len(col) < 3:
                continue
            if col not in valid_cols:
                invalid.append(col)
        
        return list(set(invalid))  # dedupe
