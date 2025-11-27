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
    """
    
    SSN_PATTERN = r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b'
    PHONE_PATTERN = r'\b(?:\+1[-\s]?)?\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{4}\b'
    EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    DOB_PATTERN = r'\b(?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b'
    SALARY_PATTERN = r'\$[\d,]+(?:\.\d{2})?'
    
    # Common name patterns (First Last)
    NAME_PATTERN = r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b'
    
    def __init__(self):
        self.name_counter = 0
        self.name_map = {}
    
    def _get_placeholder(self, name: str) -> str:
        if name not in self.name_map:
            self.name_counter += 1
            letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            idx = (self.name_counter - 1) % 26
            self.name_map[name] = f"[Employee {letters[idx]}]"
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
        """Remove PII from text"""
        if not text:
            return text
        
        result = text
        
        # Remove obvious PII patterns
        result = re.sub(self.SSN_PATTERN, '[SSN]', result)
        result = re.sub(self.PHONE_PATTERN, '[PHONE]', result)
        result = re.sub(self.EMAIL_PATTERN, '[EMAIL]', result)
        result = re.sub(self.DOB_PATTERN, '[DOB]', result)
        result = re.sub(self.SALARY_PATTERN, self._salary_to_range, result)
        
        # Replace names (be careful - might catch non-names)
        # Only do this for employee-focused responses
        names = re.findall(self.NAME_PATTERN, result)
        for name in names:
            # Skip common non-name phrases
            if name.lower() in ['new york', 'los angeles', 'san francisco', 'united states',
                               'general ledger', 'human resources', 'time off']:
                continue
            result = result.replace(name, self._get_placeholder(name))
        
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
            
            system_prompt = """You are an expert UKG/HCM implementation consultant helping analyze customer data.

CRITICAL RULES:
1. DIRECTLY ANSWER the question using the data provided
2. NEVER give code examples, Python snippets, or "how to analyze" suggestions
3. NEVER say "you could use pandas" or "here's how to count" - just DO the counting/analysis
4. If asked "how many", COUNT the items in the data and give a NUMBER
5. If asked to "list", LIST the actual items from the data
6. Be concise and direct - the user wants an ANSWER, not instructions

For counts/aggregates:
- Count the actual records in the data
- Give a specific number as the answer
- Don't explain how to count - just count and respond

Example:
- User asks: "How many employees are active?"
- WRONG: "To count active employees, you could use Python..."
- RIGHT: "There are 349 active employees in the data."

Formatting:
- Keep responses focused and concise
- Use tables/lists only when listing multiple items
- Lead with the direct answer, then add context if helpful"""

            user_prompt = f"""Question: {query}

DATA FROM CUSTOMER'S SYSTEM:

{context}

IMPORTANT: Analyze the above data and directly answer the question. Do NOT provide code or instructions - provide the actual answer based on the data."""

            response, success = self._call_claude(user_prompt, system_prompt)
            result["models_used"].append("claude-sonnet-4")
            
            if success:
                result["response"] = response
            else:
                result["error"] = response
                result["response"] = f"Error: {response}"
            
            return result
        
        # =================================================================
        # EMPLOYEE QUERY: Local LLM → Sanitize → Claude
        # =================================================================
        logger.info("EMPLOYEE path: Local LLM → Sanitize → Claude")
        
        # Select local model
        local_model = select_local_model(query, chunks)
        
        # Call local LLM
        local_system = """You are an expert HCM analyst. DIRECTLY answer the question using the data.

CRITICAL RULES:
1. NEVER give code examples or "how to" instructions
2. If asked "how many", COUNT the records and give a NUMBER
3. If asked to "list", LIST the actual items
4. Be concise and direct - give the ANSWER, not instructions"""

        local_prompt = f"""Question: {query}

DATA:
{context}

Directly answer using the data above. If counting, give the actual count. No code examples."""

        local_response, local_success = self._call_ollama(local_model, local_prompt, local_system)
        result["models_used"].append(local_model)
        
        # Handle timeout - fallback to Claude with sanitized context
        if local_response is None:
            logger.warning("Local LLM timeout - falling back to Claude with sanitized context")
            
            sanitized_context = self.sanitizer.sanitize(context)
            result["sanitized"] = True
            
            system_prompt = """You are an expert HCM analyst. DIRECTLY answer using the data provided.

CRITICAL: 
- Do NOT give code examples or Python snippets
- If asked "how many", count and give a NUMBER
- If asked to "list", list the actual items
- Be concise - answer first, then add context if needed"""

            user_prompt = f"""Question: {query}

DATA (sanitized for privacy):
{sanitized_context}

Give a direct answer. Count records if asked "how many". No code examples."""

            response, success = self._call_claude(user_prompt, system_prompt)
            result["models_used"].append("claude-sonnet-4 (fallback)")
            
            if success:
                result["response"] = response
            else:
                result["error"] = f"Both local LLM and Claude failed"
                result["response"] = "Unable to process query. Please try again."
            
            return result
        
        # Handle local LLM failure
        if not local_success:
            result["error"] = local_response
            result["response"] = f"Error: {local_response}"
            return result
        
        # Sanitize local response
        logger.info("Sanitizing local LLM response")
        sanitized_response = self.sanitizer.sanitize(local_response)
        result["sanitized"] = True
        
        if self.sanitizer.name_map:
            logger.info(f"Sanitized {len(self.sanitizer.name_map)} names")
        
        # Send to Claude for polish
        if self.claude_api_key:
            logger.info("Sending to Claude for synthesis")
            
            claude_system = """You are an expert HCM consultant polishing a response.

RULES:
1. Keep the ANSWER - don't add code examples or "how to" instructions
2. Clean up formatting but keep all facts/numbers intact
3. Keep sanitized placeholders like [Employee A] as-is
4. Be concise - if there's a count, lead with the number
5. Never suggest Python/pandas/code approaches"""

            claude_prompt = f"""Question: {query}

Analysis to polish:
{sanitized_response}

Clean up this response. Keep the direct answer. No code examples. Keep [Employee X] placeholders."""

            claude_response, claude_success = self._call_claude(claude_prompt, claude_system)
            result["models_used"].append("claude-sonnet-4")
            
            if claude_success:
                result["response"] = claude_response
            else:
                # Fall back to sanitized local response
                result["response"] = sanitized_response
        else:
            result["response"] = sanitized_response
        
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
