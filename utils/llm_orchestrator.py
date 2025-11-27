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
    
    def _call_claude(self, prompt: str, system_prompt: str) -> Tuple[str, bool]:
        """Call Claude API"""
        if not self.claude_api_key:
            return "Claude API key not configured", False
        
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.claude_api_key)
            
            logger.info(f"Calling Claude ({len(prompt)} chars)")
            
            response = client.messages.create(
                model=self.claude_model,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result = response.content[0].text
            logger.info(f"Claude response: {len(result)} chars")
            return result, True
            
        except Exception as e:
            logger.error(f"Claude error: {e}")
            return str(e), False
    
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
4. If listing, show real values from the data (limit to 25 if many)
5. Never describe what to do - just do it and give the answer"""

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
4. If listing, show real values from the data (limit to 25 if many)
5. Never describe what to do - just do it and give the answer
6. Keep any [REDACTED] or sanitized placeholders as-is - those are for privacy"""

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
    
    def generate_sql(self, prompt: str) -> Dict[str, Any]:
        """
        Generate SQL query from natural language using Claude.
        
        Used by structured data handler to convert user questions
        into DuckDB SQL queries.
        
        Args:
            prompt: Natural language query with schema context
            
        Returns:
            {'sql': 'SELECT ...', 'model': '...', 'success': True/False}
        """
        if not self.claude_api_key:
            # Try local LLM as fallback
            return self._generate_sql_local(prompt)
        
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.claude_api_key)
            
            system_prompt = """You are a SQL expert. Generate valid DuckDB SQL queries.

RULES:
1. Return ONLY the SQL query, no explanations or markdown
2. Use the exact table and column names provided
3. For text searches, use ILIKE for case-insensitive matching
4. Limit results to 1000 rows unless it's a COUNT query
5. Use proper JOIN syntax when combining tables
6. Handle NULL values appropriately
7. Column and table names are case-sensitive - use exactly as provided

Output ONLY the SQL query, nothing else."""

            logger.info(f"Generating SQL from prompt ({len(prompt)} chars)")
            
            response = client.messages.create(
                model=self.claude_model,
                max_tokens=1024,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}]
            )
            
            sql = response.content[0].text.strip()
            
            # Clean up markdown if present
            if sql.startswith("```sql"):
                sql = sql[6:]
            if sql.startswith("```"):
                sql = sql[3:]
            if sql.endswith("```"):
                sql = sql[:-3]
            sql = sql.strip()
            
            logger.info(f"Generated SQL: {sql[:100]}...")
            
            return {
                "sql": sql,
                "model": self.claude_model,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"SQL generation error: {e}")
            return {
                "sql": None,
                "error": str(e),
                "success": False
            }
    
    def _generate_sql_local(self, prompt: str) -> Dict[str, Any]:
        """
        Generate SQL using local Ollama LLM (fallback if no Claude API key)
        """
        if not self.ollama_url:
            return {"sql": None, "error": "No LLM configured", "success": False}
        
        try:
            local_prompt = f"""Generate a SQL query for this question. Return ONLY the SQL, no explanation.

{prompt}

SQL:"""
            
            response, success = self._call_ollama('mistral:7b', local_prompt)
            
            if success and response:
                sql = response.strip()
                
                # Clean up markdown
                if sql.startswith("```"):
                    sql = sql.split("```")[1]
                    if sql.startswith("sql"):
                        sql = sql[3:]
                sql = sql.strip()
                
                return {"sql": sql, "model": "mistral:7b", "success": True}
            else:
                return {"sql": None, "error": "Local LLM failed", "success": False}
                
        except Exception as e:
            logger.error(f"Local SQL generation error: {e}")
            return {"sql": None, "error": str(e), "success": False}
