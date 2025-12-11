"""
XLR8 INTELLIGENCE ENGINE v2
============================

Deploy to: backend/utils/intelligence_engine.py

PROPERLY INTELLIGENT:
- Question analysis done by LOCAL LLM (Mistral), not regex
- Clarification decisions made by LLM based on context
- Domain detection is LLM-powered
- Zero hardcoded patterns for classification

LOCAL LLM = FREE, FAST, UNLIMITED
"""

import os
import re
import json
import logging
import requests
from requests.auth import HTTPBasicAuth
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Truth:
    """A piece of information from one source of truth."""
    source_type: str  # 'reality', 'intent', 'best_practice'
    source_name: str
    content: Any
    confidence: float
    location: str


@dataclass  
class Conflict:
    """A detected conflict between sources of truth."""
    description: str
    reality: Optional[Truth] = None
    intent: Optional[Truth] = None
    best_practice: Optional[Truth] = None
    severity: str = "medium"
    recommendation: str = ""


@dataclass
class Insight:
    """A proactive insight discovered while processing."""
    type: str
    title: str
    description: str
    data: Any
    severity: str
    action_required: bool = False


@dataclass
class SynthesizedAnswer:
    """A complete answer synthesized from all sources."""
    question: str
    answer: str
    confidence: float
    from_reality: List[Truth] = field(default_factory=list)
    from_intent: List[Truth] = field(default_factory=list)
    from_best_practice: List[Truth] = field(default_factory=list)
    conflicts: List[Conflict] = field(default_factory=list)
    insights: List[Insight] = field(default_factory=list)
    structured_output: Optional[Dict] = None
    reasoning: List[str] = field(default_factory=list)
    executed_sql: Optional[str] = None


class IntelligenceMode(Enum):
    SEARCH = "search"
    ANALYZE = "analyze"
    COMPARE = "compare"
    VALIDATE = "validate"
    CONFIGURE = "configure"
    INTERVIEW = "interview"
    WORKFLOW = "workflow"
    POPULATE = "populate"
    REPORT = "report"


# =============================================================================
# SEMANTIC PATTERNS (kept for column matching, NOT for question analysis)
# =============================================================================

SEMANTIC_TYPES = {
    'employee_id': [
        r'^emp.*id', r'^ee.*num', r'^employee.*number', r'^worker.*id',
        r'^person.*id', r'^emp.*num', r'^emp.*no$', r'^ee.*id',
        r'^employee.*id', r'^staff.*id', r'^associate.*id', r'^emp.*key',
    ],
    'company_code': [
        r'^comp.*code', r'^co.*code', r'^company.*id', r'^org.*code',
        r'^entity.*code', r'^legal.*entity', r'^business.*unit',
        r'^company$', r'^comp$',
    ],
    'department': [
        r'dept.*code', r'department.*code', r'^div.*code', r'division.*code',
        r'cost.*center', r'^dept$', r'^department$',
    ],
    'job_code': [
        r'^job.*code', r'^job.*id', r'^position.*code', r'^title.*code',
        r'^job.*class', r'^occupation', r'^job$',
    ],
    'location': [
        r'^loc.*code', r'^location.*code', r'^work.*loc', r'^site.*code',
        r'^branch.*code', r'^office.*code', r'^location$',
    ],
    'earning_code': [
        r'^earn.*code', r'^earning.*type', r'^pay.*code', r'^wage.*type',
        r'^earning$', r'^earn_cd',
    ],
    'deduction_code': [
        r'^ded.*code', r'^deduction.*type', r'^deduct.*code',
        r'^deduction$', r'^ded_cd', r'^benefit.*code',
    ],
}


# =============================================================================
# LOCAL LLM CLIENT
# =============================================================================

class LocalLLM:
    """Client for calling local Ollama instance."""
    
    def __init__(self):
        self.ollama_url = os.getenv("LLM_ENDPOINT", "").rstrip('/')
        self.ollama_username = os.getenv("LLM_USERNAME", "")
        self.ollama_password = os.getenv("LLM_PASSWORD", "")
        
        # Model selection
        self.analysis_model = "mistral:7b"  # For question analysis
        self.sql_model = "deepseek-coder:6.7b"  # For SQL generation
        self.synthesis_model = "mistral:7b"  # For answer synthesis
        
    def call(self, prompt: str, model: str = None, temperature: float = 0.3, max_tokens: int = 2048) -> Tuple[Optional[str], bool]:
        """
        Call local Ollama instance.
        
        Returns:
            Tuple of (response_text, success_bool)
        """
        if not self.ollama_url:
            logger.error("LLM_ENDPOINT not configured!")
            return None, False
        
        model = model or self.analysis_model
        
        try:
            url = f"{self.ollama_url}/api/generate"
            
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }
            
            logger.info(f"[LOCAL-LLM] Calling {model} ({len(prompt)} chars)")
            
            # Use auth if configured
            if self.ollama_username and self.ollama_password:
                response = requests.post(
                    url, json=payload,
                    auth=HTTPBasicAuth(self.ollama_username, self.ollama_password),
                    timeout=60
                )
            else:
                response = requests.post(url, json=payload, timeout=60)
            
            if response.status_code != 200:
                logger.error(f"[LOCAL-LLM] Error {response.status_code}: {response.text[:200]}")
                return None, False
            
            result = response.json().get("response", "")
            logger.info(f"[LOCAL-LLM] Response: {len(result)} chars")
            return result, True
            
        except requests.exceptions.Timeout:
            logger.error("[LOCAL-LLM] Timeout")
            return None, False
        except Exception as e:
            logger.error(f"[LOCAL-LLM] Error: {e}")
            return None, False
    
    def analyze_question(self, question: str, schema_summary: str = "", confirmed_facts: Dict = None) -> Dict:
        """
        Use LLM to analyze the question and determine what's needed.
        
        Returns dict with:
            - mode: search/analyze/compare/validate/configure/report
            - domains: list of data domains involved
            - needs_clarification: bool
            - clarification_questions: list of questions to ask (if needed)
            - entities: extracted specific entities
            - reasoning: why these decisions were made
        """
        confirmed_facts = confirmed_facts or {}
        
        prompt = f"""Analyze this HR/payroll system question and return JSON only.

QUESTION: {question}

SCHEMA AVAILABLE: {schema_summary if schema_summary else "Employee data, earnings, deductions, jobs, taxes"}

ALREADY ANSWERED BY USER: {json.dumps(confirmed_facts) if confirmed_facts else "Nothing yet"}

Return ONLY valid JSON (no markdown, no explanation):
{{
    "mode": "search|analyze|compare|validate|configure|report",
    "domains": ["employees", "earnings", "deductions", "taxes", "jobs", "benefits"],
    "needs_clarification": true/false,
    "clarification_questions": [
        {{
            "id": "unique_id",
            "question": "What to ask the user",
            "type": "radio",
            "options": [
                {{"id": "opt1", "label": "Option 1", "default": true}},
                {{"id": "opt2", "label": "Option 2"}}
            ],
            "reason": "Why this matters"
        }}
    ],
    "entities": {{
        "employee_id": null,
        "company_code": null,
        "status_filter": null,
        "numeric_threshold": null
    }},
    "reasoning": "Brief explanation of analysis"
}}

RULES FOR CLARIFICATION:
1. If asking about EMPLOYEES and user hasn't specified status → ask active/terminated/all
2. If asking about MONEY but unclear if rates vs YTD vs history → ask scope
3. If asking about DEDUCTIONS but type unclear → ask type
4. If user already answered a clarification for this domain → DON'T ask again
5. If question is crystal clear with no ambiguity → needs_clarification: false
6. Keep clarification questions SHORT and RELEVANT

JSON only:"""

        response, success = self.call(prompt, model=self.analysis_model, temperature=0.1)
        
        if not success or not response:
            logger.warning("[LOCAL-LLM] Analysis failed, using fallback")
            return self._fallback_analysis(question, confirmed_facts)
        
        # Parse JSON from response
        try:
            # Try to extract JSON from response (handle markdown wrapping)
            json_str = response.strip()
            if json_str.startswith('```'):
                json_str = re.sub(r'^```json?\s*', '', json_str)
                json_str = re.sub(r'\s*```$', '', json_str)
            
            result = json.loads(json_str)
            logger.info(f"[LOCAL-LLM] Analysis: mode={result.get('mode')}, domains={result.get('domains')}, needs_clarification={result.get('needs_clarification')}")
            return result
            
        except json.JSONDecodeError as e:
            logger.warning(f"[LOCAL-LLM] JSON parse failed: {e}, using fallback")
            return self._fallback_analysis(question, confirmed_facts)
    
    def _fallback_analysis(self, question: str, confirmed_facts: Dict) -> Dict:
        """
        Simple fallback if LLM analysis fails.
        This is the ONLY place with hardcoded patterns - as emergency backup.
        """
        q_lower = question.lower()
        
        # Detect mode
        mode = "search"
        if any(w in q_lower for w in ['validate', 'check', 'verify']):
            mode = "validate"
        elif any(w in q_lower for w in ['configure', 'set up', 'setup']):
            mode = "configure"
        elif any(w in q_lower for w in ['compare', 'versus', 'vs']):
            mode = "compare"
        elif any(w in q_lower for w in ['report', 'summary']):
            mode = "report"
        elif any(w in q_lower for w in ['analyze', 'trend', 'pattern']):
            mode = "analyze"
        
        # Detect domains
        domains = []
        if any(w in q_lower for w in ['employee', 'worker', 'staff', 'people', 'how many', 'count']):
            domains.append('employees')
        if any(w in q_lower for w in ['earn', 'pay', 'salary', 'wage', 'rate', 'hour', '$']):
            domains.append('earnings')
        if any(w in q_lower for w in ['deduction', 'benefit', '401k', 'insurance']):
            domains.append('deductions')
        if any(w in q_lower for w in ['tax', 'withhold']):
            domains.append('taxes')
        if any(w in q_lower for w in ['job', 'position', 'title', 'department']):
            domains.append('jobs')
        
        if not domains:
            domains = ['general']
        
        # Determine if clarification needed
        needs_clarification = False
        clarification_questions = []
        
        if 'employees' in domains and 'employee_status' not in confirmed_facts:
            if not any(w in q_lower for w in ['active', 'terminated', 'all employees']):
                needs_clarification = True
                clarification_questions.append({
                    'id': 'employee_status',
                    'question': 'Which employees should I include?',
                    'type': 'radio',
                    'options': [
                        {'id': 'active', 'label': 'Active only', 'default': True},
                        {'id': 'termed', 'label': 'Terminated only'},
                        {'id': 'all', 'label': 'All employees'}
                    ],
                    'reason': 'Need to know employment status scope'
                })
        
        return {
            'mode': mode,
            'domains': domains,
            'needs_clarification': needs_clarification,
            'clarification_questions': clarification_questions,
            'entities': {},
            'reasoning': 'Fallback analysis (LLM unavailable)'
        }


# =============================================================================
# INTELLIGENCE ENGINE
# =============================================================================

class IntelligenceEngine:
    """The brain of XLR8 - now actually intelligent."""
    
    def __init__(self, project_name: str):
        self.project = project_name
        self.structured_handler = None
        self.rag_handler = None
        self.schema = {}
        self.relationships = []
        self.conversation_history = []
        self.confirmed_facts = {}
        self.pending_questions = []
        self.conversation_context = {}
        self.last_executed_sql = None
        
        # Initialize local LLM client
        self.llm = LocalLLM()
    
    def load_context(
        self, 
        structured_handler=None, 
        rag_handler=None,
        schema: Dict = None,
        relationships: List[Dict] = None
    ):
        """Load data context for this project."""
        self.structured_handler = structured_handler
        self.rag_handler = rag_handler
        self.schema = schema or {}
        self.relationships = relationships or []
    
    def _get_schema_summary(self) -> str:
        """Get a brief summary of available schema for LLM context."""
        if not self.schema or not self.schema.get('tables'):
            return "No schema loaded"
        
        tables = self.schema.get('tables', [])
        summary_parts = []
        
        for table in tables[:10]:  # Limit to 10 tables
            table_name = table.get('table_name', '')
            # Get short name
            short_name = table_name.split('__')[-1] if '__' in table_name else table_name
            columns = table.get('columns', [])
            
            # Get column names
            if columns and isinstance(columns[0], dict):
                col_names = [c.get('name', str(c)) for c in columns[:10]]
            else:
                col_names = [str(c) for c in columns[:10]]
            
            summary_parts.append(f"{short_name}: {', '.join(col_names)}")
        
        return "; ".join(summary_parts)
    
    def ask(
        self, 
        question: str,
        mode: IntelligenceMode = None,
        context: Dict = None
    ) -> SynthesizedAnswer:
        """Main entry point - ask the engine a question."""
        logger.info(f"[INTELLIGENCE] Question: {question[:100]}...")
        
        # Use LOCAL LLM to analyze the question
        schema_summary = self._get_schema_summary()
        analysis = self.llm.analyze_question(question, schema_summary, self.confirmed_facts)
        
        # Convert mode string to enum if needed
        if mode is None and analysis.get('mode'):
            try:
                mode = IntelligenceMode(analysis['mode'])
            except ValueError:
                mode = IntelligenceMode.SEARCH
        
        # Check if clarification needed
        if analysis.get('needs_clarification') and analysis.get('clarification_questions'):
            logger.info(f"[INTELLIGENCE] Clarification needed: {len(analysis['clarification_questions'])} questions")
            return self._request_clarification(question, analysis)
        
        logger.info(f"[INTELLIGENCE] Gathering truths - no clarification needed")
        
        # Gather the three truths
        reality = self._gather_reality(question, analysis)
        logger.info(f"[INTELLIGENCE] Reality gathered: {len(reality)} truths")
        
        intent = self._gather_intent(question, analysis)
        best_practice = self._gather_best_practice(question, analysis)
        
        # Detect conflicts
        conflicts = self._detect_conflicts(reality, intent, best_practice)
        
        # Run proactive checks
        insights = self._run_proactive_checks(analysis)
        
        # Synthesize answer
        answer = self._synthesize_answer(
            question=question,
            mode=mode,
            reality=reality,
            intent=intent,
            best_practice=best_practice,
            conflicts=conflicts,
            insights=insights,
            context=context
        )
        
        # Store in history
        self.conversation_history.append({
            'question': question,
            'answer_preview': answer.answer[:200] if answer.answer else '',
            'mode': mode.value if mode else 'search',
            'timestamp': datetime.now().isoformat()
        })
        
        return answer
    
    def _request_clarification(self, question: str, analysis: Dict) -> SynthesizedAnswer:
        """Return a response that asks for clarification."""
        # Convert analysis format to expected output format
        questions = analysis.get('clarification_questions', [])
        
        return SynthesizedAnswer(
            question=question,
            answer="",
            confidence=0.0,
            structured_output={
                'type': 'clarification_needed',
                'questions': questions,
                'original_question': question,
                'detected_mode': analysis.get('mode', 'search'),
                'detected_domains': analysis.get('domains', ['general']),
                'reasoning': analysis.get('reasoning', '')
            },
            reasoning=[analysis.get('reasoning', 'Need more information')]
        )
    
    def _generate_sql_for_question(self, question: str, analysis: Dict) -> Optional[Dict]:
        """Generate SQL query using LLMOrchestrator with smart model selection and validation."""
        logger.warning(f"[SQL-GEN] Starting SQL generation via orchestrator")
        
        if not self.structured_handler:
            logger.warning("[SQL-GEN] No structured handler")
            return None
        
        if not self.schema:
            logger.warning("[SQL-GEN] No schema")
            return None
        
        tables = self.schema.get('tables', [])
        if not tables:
            logger.warning("[SQL-GEN] No tables in schema")
            return None
        
        # Get LLMOrchestrator - smart routing, validation, retry
        try:
            try:
                from utils.llm_orchestrator import LLMOrchestrator
            except ImportError:
                from backend.utils.llm_orchestrator import LLMOrchestrator
            
            orchestrator = LLMOrchestrator()
            logger.warning("[SQL-GEN] LLMOrchestrator loaded")
        except Exception as e:
            logger.error(f"[SQL-GEN] Could not load LLMOrchestrator: {e}")
            return None
        
        # Build schema and collect all columns for validation
        tables_info = []
        all_columns = set()
        
        # BUILD COLUMN INDEX - which table(s) has each column
        column_index = {}
        table_short_names = {}
        
        for table in tables:
            table_name = table.get('table_name', '')
            columns = table.get('columns', [])
            if columns and isinstance(columns[0], dict):
                col_names = [c.get('name', str(c)) for c in columns]
            else:
                col_names = [str(c) for c in columns] if columns else []
            row_count = table.get('row_count', 0)
            
            all_columns.update(col_names)
            
            short_name = table_name.split('__')[-1] if '__' in table_name else table_name
            table_short_names[table_name] = short_name
            
            for col in col_names:
                col_lower = col.lower()
                if col_lower not in column_index:
                    column_index[col_lower] = []
                if short_name not in column_index[col_lower]:
                    column_index[col_lower].append(short_name)
            
            # Get sample values
            sample_str = ""
            try:
                rows, cols = self.structured_handler.execute_query(f'SELECT * FROM "{table_name}" LIMIT 3')
                if rows and cols:
                    samples = []
                    for col in cols[:5]:
                        vals = set(str(row.get(col, ''))[:20] for row in rows if row.get(col) is not None)
                        if vals:
                            samples.append(f"    {col}: {', '.join(list(vals)[:3])}")
                    sample_str = "\n  Samples:\n" + "\n".join(samples) if samples else ""
            except:
                pass
            
            tables_info.append(f"Table: {table_name}\n  Columns: {', '.join(col_names)}\n  Rows: {row_count}{sample_str}")
        
        schema_text = '\n\n'.join(tables_info)
        logger.warning(f"[SQL-GEN] Built schema with {len(tables_info)} tables, {len(all_columns)} columns")
        
        self._column_index = column_index
        self._table_short_names = table_short_names
        
        # Build relationships text
        relationships_text = ""
        if self.relationships:
            rel_lines = []
            skipped = 0
            for rel in self.relationships[:100]:
                src_table = rel.get('source_table', '').lower()
                src_col = rel.get('source_column', '').lower()
                tgt_table = rel.get('target_table', '').lower()
                tgt_col = rel.get('target_column', '').lower()
                
                src_short = src_table.split('__')[-1] if '__' in src_table else src_table
                tgt_short = tgt_table.split('__')[-1] if '__' in tgt_table else tgt_table
                
                src_tables = column_index.get(src_col, [])
                tgt_tables = column_index.get(tgt_col, [])
                
                src_valid = src_short in [t.lower() for t in src_tables]
                tgt_valid = tgt_short in [t.lower() for t in tgt_tables]
                
                if src_valid and tgt_valid:
                    src = f"{rel.get('source_table')}.{rel.get('source_column')}"
                    tgt = f"{rel.get('target_table')}.{rel.get('target_column')}"
                    rel_lines.append(f"  {src} → {tgt}")
                else:
                    skipped += 1
                
                if len(rel_lines) >= 15:
                    break
            
            if rel_lines:
                relationships_text = "\n\nRELATIONSHIPS:\n" + "\n".join(rel_lines)
        
        # Build column location hints
        column_location_text = "\n\nJOIN KEYS:\n"
        shared_cols = []
        for col, tables_list in sorted(column_index.items()):
            if len(tables_list) > 1:
                shared_cols.append(f"  {col}: {', '.join(tables_list)}")
        if shared_cols:
            column_location_text += "\n".join(shared_cols[:10]) + "\n"
        
        # Add user's confirmed answers as filters
        filter_instructions = ""
        if self.confirmed_facts:
            filters = []
            
            if self.confirmed_facts.get('employee_status') in ['active', 'termed']:
                status_col = None
                status_table = None
                for t in tables:
                    tname = t.get('table_name', '')
                    cols = t.get('columns', [])
                    for c in cols:
                        c_str = str(c).lower()
                        if any(x in c_str for x in ['employment_status', 'emp_status', 'status_code', 'termination']):
                            status_col = str(c)
                            status_table = tname.split('__')[-1] if '__' in tname else tname
                            break
                    if status_col:
                        break
                
                if status_col:
                    if self.confirmed_facts.get('employee_status') == 'active':
                        filters.append(f"Filter to active employees using {status_table}.{status_col}")
                    else:
                        filters.append(f"Filter to terminated employees using {status_table}.{status_col}")
            
            if filters:
                filter_instructions = "\n\nFILTERS:\n" + "\n".join(f"- {f}" for f in filters)
        
        prompt = f"""SCHEMA:
{schema_text}{relationships_text}
{column_location_text}
{filter_instructions}

QUESTION: {question}

RULES:
1. Use ONLY columns from schema
2. Use ILIKE for text matching
3. COUNT(*) for "how many"  
4. JOIN on shared columns (employee_number is typical key)
5. TRY_CAST for numeric comparisons

Return ONLY the SQL, no explanation."""
        
        logger.warning(f"[SQL-GEN] Prompt length: {len(prompt)} chars")
        
        result = orchestrator.generate_sql(prompt, all_columns)
        
        if result.get('success') and result.get('sql'):
            sql = result['sql']
            model = result.get('model', 'local')
            
            # Clean SQL
            sql = sql.strip()
            if '```sql' in sql.lower():
                sql = re.sub(r'```sql\s*', '', sql, flags=re.IGNORECASE)
                sql = re.sub(r'```\s*$', '', sql)
            elif '```' in sql:
                sql = sql.replace('```', '').strip()
            
            sql = sql.strip()
            logger.warning(f"[SQL-GEN] {model} generated: {sql[:150]}")
            
            # Detect query type
            sql_upper = sql.upper()
            if 'COUNT(*)' in sql_upper or 'COUNT(' in sql_upper:
                query_type = 'count'
            elif 'SUM(' in sql_upper:
                query_type = 'sum'
            elif 'AVG(' in sql_upper:
                query_type = 'average'
            else:
                query_type = 'list'
            
            table_match = re.search(r'FROM\s+"?([^"\s]+)"?', sql, re.IGNORECASE)
            table_name = table_match.group(1) if table_match else 'unknown'
            
            return {
                'sql': sql,
                'table': table_name,
                'query_type': query_type,
                'model': model,
                'all_columns': all_columns
            }
        else:
            error = result.get('error', 'Unknown')
            logger.warning(f"[SQL-GEN] Failed: {error}")
            return None
    
    def _try_fix_sql_from_error(self, sql: str, error_msg: str, all_columns: set) -> Optional[str]:
        """Try to fix SQL based on DuckDB error message."""
        from difflib import SequenceMatcher
        
        patterns = [
            r'does not have a column named "([^"]+)"',
            r'Referenced column "([^"]+)" not found',
            r'column "([^"]+)" not found',
        ]
        
        bad_col = None
        for pattern in patterns:
            match = re.search(pattern, error_msg, re.IGNORECASE)
            if match:
                bad_col = match.group(1)
                break
        
        if not bad_col:
            return None
        
        logger.info(f"[SQL-FIX] Attempting to fix column: {bad_col}")
        
        valid_cols_lower = {c.lower() for c in all_columns}
        
        # Known fixes
        known_fixes = {
            'rate': 'hourly_pay_rate',
            'hourly_rate': 'hourly_pay_rate',
            'pay_rate': 'hourly_pay_rate',
            'employee_id': 'employee_number',
            'emp_id': 'employee_number',
        }
        
        fix = None
        
        if bad_col.lower() in known_fixes:
            fix = known_fixes[bad_col.lower()]
            if fix.lower() not in valid_cols_lower:
                fix = None
        
        if not fix and '_' in bad_col:
            best_score = 0.6
            for col in all_columns:
                score = SequenceMatcher(None, bad_col.lower(), col.lower()).ratio()
                if score > best_score:
                    best_score = score
                    fix = col
        
        if fix:
            logger.info(f"[SQL-FIX] Fixing: {bad_col} → {fix}")
            fixed_sql = re.sub(
                r'\b' + re.escape(bad_col) + r'\b',
                f'"{fix}"',
                sql,
                flags=re.IGNORECASE
            )
            return fixed_sql
        
        return None
    
    def _gather_reality(self, question: str, analysis: Dict) -> List[Truth]:
        """Gather REALITY - what the customer's DATA shows."""
        logger.warning(f"[REALITY] Starting")
        
        if not self.structured_handler:
            return []
        
        if not self.schema or not self.schema.get('tables'):
            return []
        
        truths = []
        domains = analysis.get('domains', ['general'])
        
        # Get pattern cache
        pattern_cache = None
        try:
            from utils.sql_pattern_cache import initialize_patterns
            if self.project:
                pattern_cache = initialize_patterns(self.project, self.schema)
        except ImportError:
            try:
                from backend.utils.sql_pattern_cache import initialize_patterns
                if self.project:
                    pattern_cache = initialize_patterns(self.project, self.schema)
            except:
                pass
        except:
            pass
        
        try:
            sql = None
            sql_source = None
            sql_info = None
            
            # Check pattern cache first
            if pattern_cache:
                cached_pattern = pattern_cache.find_matching_pattern(question)
                if cached_pattern and cached_pattern.get('sql'):
                    sql = cached_pattern['sql']
                    sql_source = 'pattern_cache'
                    logger.warning(f"[INTELLIGENCE] Pattern cache HIT!")
            
            # Generate via LLM if no cache
            if not sql:
                sql_info = self._generate_sql_for_question(question, analysis)
                if sql_info and sql_info.get('sql'):
                    sql = sql_info['sql']
                    sql_source = 'llm_generated'
            
            # Execute SQL
            if sql:
                max_retries = 2
                
                for attempt in range(max_retries + 1):
                    try:
                        rows, cols = self.structured_handler.execute_query(sql)
                        self.last_executed_sql = sql
                        
                        if rows:
                            table_name = 'query_result'
                            if sql_info:
                                table_name = sql_info.get('table', 'query_result')
                            else:
                                table_match = re.search(r'FROM\s+"?([^"\s]+)"?', sql, re.IGNORECASE)
                                if table_match:
                                    table_name = table_match.group(1)
                            
                            truths.append(Truth(
                                source_type='reality',
                                source_name=f"SQL Query: {table_name}",
                                content={
                                    'sql': sql,
                                    'columns': cols,
                                    'rows': rows,
                                    'total': len(rows),
                                    'query_type': sql_info.get('query_type', 'unknown') if sql_info else 'cached',
                                    'table': table_name,
                                    'is_targeted_query': True,
                                    'sql_source': sql_source
                                },
                                confidence=0.98,
                                location=f"Query: {sql}"
                            ))
                            
                            # Learn pattern
                            if pattern_cache and sql_source == 'llm_generated':
                                pattern_cache.learn_pattern(question, sql, success=True)
                            
                            return truths
                        break
                        
                    except Exception as sql_e:
                        error_msg = str(sql_e)
                        logger.warning(f"[INTELLIGENCE] SQL failed (attempt {attempt + 1}): {error_msg}")
                        
                        if pattern_cache and sql_source == 'pattern_cache' and attempt == 0:
                            pattern_cache.record_failure(question)
                            sql_info = self._generate_sql_for_question(question, analysis)
                            if sql_info and sql_info.get('sql'):
                                sql = sql_info['sql']
                                sql_source = 'llm_fallback'
                                continue
                        
                        if attempt < max_retries and sql_info:
                            fixed_sql = self._try_fix_sql_from_error(sql, error_msg, sql_info.get('all_columns', set()))
                            if fixed_sql and fixed_sql != sql:
                                sql = fixed_sql
                                continue
                        break
            
            # Fallback: sample from relevant tables
            tables = self.schema.get('tables', [])
            for table in tables:
                table_name = table.get('table_name', '')
                
                relevant = False
                if 'employees' in domains and any(c in table_name.lower() for c in ['personal', 'employee']):
                    relevant = True
                if 'earnings' in domains and any(c in table_name.lower() for c in ['earning', 'pay', 'rate']):
                    relevant = True
                if 'deductions' in domains and 'deduction' in table_name.lower():
                    relevant = True
                
                if not relevant and domains != ['general']:
                    continue
                
                try:
                    sql = f'SELECT * FROM "{table_name}" LIMIT 100'
                    rows, cols = self.structured_handler.execute_query(sql)
                    
                    if rows:
                        truths.append(Truth(
                            source_type='reality',
                            source_name=table_name,
                            content={
                                'columns': cols,
                                'rows': rows,
                                'total': len(rows),
                                'table': table_name,
                                'is_targeted_query': False
                            },
                            confidence=0.95,
                            location=f"Table: {table_name}"
                        ))
                except:
                    pass
        
        except Exception as e:
            logger.error(f"Error gathering reality: {e}")
        
        return truths
    
    def _gather_intent(self, question: str, analysis: Dict) -> List[Truth]:
        """Gather INTENT - what customer's DOCUMENTS say."""
        if not self.rag_handler:
            return []
        
        truths = []
        
        try:
            collection_name = self._get_document_collection_name()
            if not collection_name:
                return []
            
            results = self.rag_handler.search(
                collection_name=collection_name,
                query=question,
                n_results=10,
                project_id=self.project if self.project else None
            )
            
            for result in results:
                metadata = result.get('metadata', {})
                distance = result.get('distance', 1.0)
                doc = result.get('document', '')
                
                project_id = metadata.get('project_id', '').lower()
                if project_id in ['global', '__global__', 'global/universal']:
                    continue
                
                truths.append(Truth(
                    source_type='intent',
                    source_name=metadata.get('filename', 'Document'),
                    content=doc,
                    confidence=max(0.3, 1.0 - distance) if distance else 0.7,
                    location=f"Page {metadata.get('page', '?')}"
                ))
        
        except Exception as e:
            logger.error(f"Error gathering intent: {e}")
        
        return truths
    
    def _get_document_collection_name(self) -> Optional[str]:
        """Find the document collection name."""
        if not self.rag_handler:
            return None
        
        if hasattr(self, '_doc_collection_name'):
            return self._doc_collection_name
        
        try:
            collections = self.rag_handler.list_collections()
            preferred = ['hcmpact_docs', 'documents', 'hcm_docs', 'xlr8_docs']
            
            for name in preferred:
                if name in collections:
                    self._doc_collection_name = name
                    return name
            
            for name in collections:
                if 'doc' in name.lower() or 'hcm' in name.lower():
                    self._doc_collection_name = name
                    return name
            
            if collections:
                self._doc_collection_name = collections[0]
                return collections[0]
                
        except Exception as e:
            logger.error(f"Error finding document collection: {e}")
        
        return None
    
    def _gather_best_practice(self, question: str, analysis: Dict) -> List[Truth]:
        """Gather BEST PRACTICE - what UKG docs say SHOULD be done."""
        if not self.rag_handler:
            return []
        
        truths = []
        
        try:
            collection_name = self._get_document_collection_name()
            if not collection_name:
                return []
            
            results = self.rag_handler.search(
                collection_name=collection_name,
                query=question,
                n_results=10,
                project_id="Global/Universal"
            )
            
            for result in results:
                metadata = result.get('metadata', {})
                distance = result.get('distance', 1.0)
                doc = result.get('document', '')
                
                truths.append(Truth(
                    source_type='best_practice',
                    source_name=metadata.get('filename', 'UKG Documentation'),
                    content=doc,
                    confidence=max(0.3, 1.0 - distance) if distance else 0.7,
                    location=f"Page {metadata.get('page', '?')}"
                ))
        
        except Exception as e:
            logger.error(f"Error gathering best practice: {e}")
        
        return truths
    
    def _detect_conflicts(self, reality, intent, best_practice) -> List[Conflict]:
        """Detect conflicts between the three truths."""
        return []
    
    def _run_proactive_checks(self, analysis: Dict) -> List[Insight]:
        """Run proactive checks while answering."""
        insights = []
        domains = analysis.get('domains', ['general'])
        
        if not self.structured_handler:
            return insights
        
        try:
            tables = self.schema.get('tables', [])
            
            if 'employees' in domains or domains == ['general']:
                for table in tables:
                    table_name = table.get('table_name', '')
                    
                    if any(c in table_name.lower() for c in ['personal', 'employee']):
                        try:
                            sql = f'SELECT COUNT(*) as cnt FROM "{table_name}" WHERE ssn IS NULL OR ssn = \'\''
                            result = self.structured_handler.conn.execute(sql).fetchone()
                            if result and result[0] > 0:
                                insights.append(Insight(
                                    type='anomaly',
                                    title='Missing SSN',
                                    description=f'{result[0]} employees missing SSN',
                                    data={'count': result[0], 'table': table_name},
                                    severity='high',
                                    action_required=True
                                ))
                        except:
                            pass
                        break
        
        except Exception as e:
            logger.error(f"Error in proactive checks: {e}")
        
        return insights
    
    def _synthesize_answer(
        self,
        question: str,
        mode: IntelligenceMode,
        reality: List[Truth],
        intent: List[Truth],
        best_practice: List[Truth],
        conflicts: List[Conflict],
        insights: List[Insight],
        context: Dict = None
    ) -> SynthesizedAnswer:
        """Synthesize a complete answer from all sources."""
        reasoning = []
        context_parts = []
        
        if reality:
            context_parts.append("=== CUSTOMER DATA (QUERY RESULTS) ===")
            for truth in reality[:3]:
                if isinstance(truth.content, dict) and 'rows' in truth.content:
                    rows = truth.content['rows']
                    cols = truth.content['columns']
                    query_type = truth.content.get('query_type', 'unknown')
                    
                    if query_type == 'count' and rows:
                        count_val = list(rows[0].values())[0] if rows[0] else 0
                        context_parts.append(f"\n**ANSWER: {count_val}**")
                        context_parts.append(f"SQL: {truth.content.get('sql', 'N/A')[:200]}")
                    elif query_type in ['sum', 'average'] and rows:
                        result_val = list(rows[0].values())[0] if rows[0] else 0
                        context_parts.append(f"\n**RESULT: {result_val}**")
                        context_parts.append(f"SQL: {truth.content.get('sql', 'N/A')[:200]}")
                    else:
                        context_parts.append(f"\nSource: {truth.source_name}")
                        context_parts.append(f"Columns: {', '.join(cols[:10])}")
                        context_parts.append(f"Results ({len(rows)} rows):")
                        for row in rows[:10]:
                            row_str = " | ".join(f"{k}: {v}" for k, v in list(row.items())[:6])
                            context_parts.append(f"  {row_str}")
            reasoning.append(f"Found {len(reality)} data query results")
        
        if intent:
            context_parts.append("\n=== CUSTOMER DOCUMENTS ===")
            for truth in intent[:3]:
                context_parts.append(f"\nSource: {truth.source_name} ({truth.location})")
                context_parts.append(str(truth.content)[:500])
            reasoning.append(f"Found {len(intent)} relevant customer documents")
        
        if best_practice:
            context_parts.append("\n=== UKG BEST PRACTICE ===")
            for truth in best_practice[:3]:
                context_parts.append(f"\nSource: {truth.source_name}")
                context_parts.append(str(truth.content)[:500])
            reasoning.append(f"Found {len(best_practice)} UKG best practice documents")
        
        if insights:
            context_parts.append("\n=== PROACTIVE INSIGHTS ===")
            for insight in insights:
                icon = '🔴' if insight.severity == 'high' else '🟡'
                context_parts.append(f"{icon} {insight.title}: {insight.description}")
        
        combined_context = '\n'.join(context_parts)
        
        confidence = 0.5
        if reality:
            confidence += 0.2
        if intent:
            confidence += 0.15
        if best_practice:
            confidence += 0.1
        confidence = min(confidence, 0.95)
        
        return SynthesizedAnswer(
            question=question,
            answer=combined_context,
            confidence=confidence,
            from_reality=reality,
            from_intent=intent,
            from_best_practice=best_practice,
            conflicts=conflicts,
            insights=insights,
            structured_output=None,
            reasoning=reasoning,
            executed_sql=self.last_executed_sql
        )
    
    def clear_clarifications(self):
        """Clear all confirmed facts to start fresh."""
        self.confirmed_facts = {}
        logger.info("[INTELLIGENCE] Cleared all confirmed facts")
