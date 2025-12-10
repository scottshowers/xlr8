"""
XLR8 INTELLIGENCE ENGINE
=========================

Deploy to: backend/utils/intelligence_engine.py
"""

import re
import json
import logging
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
    executed_sql: Optional[str] = None  # SQL that was generated and executed


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
# SEMANTIC PATTERNS
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
# INTELLIGENCE ENGINE
# =============================================================================

class IntelligenceEngine:
    """The brain of XLR8."""
    
    def __init__(self, project_name: str):
        self.project = project_name
        self.structured_handler = None
        self.rag_handler = None
        self.schema = {}
        self.relationships = []
        self.conversation_history = []
        self.confirmed_facts = {}
        self.pending_questions = []
        self.conversation_context = {}  # For follow-up questions
        self.last_executed_sql = None  # Track last SQL for session context
    
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
    
    def ask(
        self, 
        question: str,
        mode: IntelligenceMode = None,
        context: Dict = None
    ) -> SynthesizedAnswer:
        """Main entry point - ask the engine a question."""
        logger.info(f"[INTELLIGENCE] Question: {question[:100]}...")
        
        # Analyze the question
        analysis = self._analyze_question(question)
        mode = mode or analysis['mode']
        
        # Check if clarification needed
        if analysis['needs_clarification']:
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
    
    def _analyze_question(self, question: str) -> Dict:
        """Analyze what the question is asking for."""
        q_lower = question.lower()
        
        mode = self._detect_mode(q_lower)
        entities = self._extract_entities(question)
        domains = self._detect_domains(q_lower)
        needs_clarification = self._needs_clarification(mode, entities, domains, q_lower)
        
        confidence = 0.7
        if entities:
            confidence += 0.1
        if len(domains) == 1:
            confidence += 0.1
        
        return {
            'mode': mode,
            'entities': entities,
            'domains': domains,
            'needs_clarification': needs_clarification,
            'clarification_questions': self._get_clarification_questions(mode, domains) if needs_clarification else [],
            'confidence': min(confidence, 0.95)
        }
    
    def _detect_mode(self, q_lower: str) -> IntelligenceMode:
        """Detect the appropriate intelligence mode."""
        if any(w in q_lower for w in ['configure', 'set up', 'setup', 'create', 'build']):
            if any(w in q_lower for w in ['rule', 'business rule', 'earning', 'deduction']):
                return IntelligenceMode.CONFIGURE
        
        if any(w in q_lower for w in ['validate', 'check', 'verify', 'issues', 'problems', 'errors']):
            return IntelligenceMode.VALIDATE
        
        if any(w in q_lower for w in ['compare', 'difference', 'versus', 'vs', 'match']):
            return IntelligenceMode.COMPARE
        
        if any(w in q_lower for w in ['fill in', 'populate', 'template', 'generate']):
            return IntelligenceMode.POPULATE
        
        if any(w in q_lower for w in ['report', 'summary', 'overview', 'status']):
            return IntelligenceMode.REPORT
        
        if any(w in q_lower for w in ['analyze', 'analysis', 'pattern', 'trend', 'insight']):
            return IntelligenceMode.ANALYZE
        
        if any(w in q_lower for w in ['help me', 'walk me through', 'guide', 'step by step']):
            return IntelligenceMode.WORKFLOW
        
        return IntelligenceMode.SEARCH
    
    def _extract_entities(self, question: str) -> Dict[str, Any]:
        """Extract specific entities from the question."""
        entities = {}
        
        emp_match = re.search(r'employee\s*(?:#|id|number|num)?\s*(\d+)', question, re.I)
        if emp_match:
            entities['employee_id'] = emp_match.group(1)
        
        company_match = re.search(r'company\s*(?:code)?\s*([A-Z0-9]{2,10})', question, re.I)
        if company_match:
            entities['company_code'] = company_match.group(1)
        
        if 'active' in question.lower():
            entities['status'] = 'active'
        elif 'terminated' in question.lower() or 'termed' in question.lower():
            entities['status'] = 'terminated'
        
        return entities
    
    def _detect_domains(self, q_lower: str) -> List[str]:
        """Detect which data domains are relevant."""
        domains = []
        
        domain_patterns = {
            'employees': r'\b(employee|worker|staff|people|person|pt|ft|part.?time|full.?time)\b',
            'earnings': r'(\b(earning|pay|salary|wage|compensation|overtime|ot|hour|rate|hourly|make|makes|paid)\b|\$)',
            'deductions': r'\b(deduction|benefit|401k|insurance|health|dental)\b',
            'taxes': r'\b(tax|withhold|federal|state|local|w-?4|fit|sit)\b',
            'jobs': r'\b(job|position|title|department|location)\b',
        }
        
        for domain, pattern in domain_patterns.items():
            if re.search(pattern, q_lower):
                domains.append(domain)
        
        return domains if domains else ['general']
    
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
        
        for table in tables:
            table_name = table.get('table_name', '')
            columns = table.get('columns', [])
            if columns and isinstance(columns[0], dict):
                col_names = [c.get('name', str(c)) for c in columns]
            else:
                col_names = [str(c) for c in columns] if columns else []
            row_count = table.get('row_count', 0)
            
            # Track all columns for validation
            all_columns.update(col_names)
            
            # Get sample values
            sample_str = ""
            try:
                rows, cols = self.structured_handler.execute_query(f'SELECT * FROM "{table_name}" LIMIT 5')
                if rows and cols:
                    samples = []
                    for col in cols:
                        vals = set(str(row.get(col, ''))[:30] for row in rows if row.get(col) is not None)
                        if vals:
                            samples.append(f"    {col}: {', '.join(list(vals)[:5])}")
                    sample_str = "\n  Sample values:\n" + "\n".join(samples) if samples else ""
            except Exception as sample_e:
                pass  # Non-critical
            
            tables_info.append(f"Table: {table_name}\n  Columns: {', '.join(col_names)}\n  Rows: {row_count}{sample_str}")
        
        schema_text = '\n\n'.join(tables_info)
        logger.warning(f"[SQL-GEN] Built schema with {len(tables_info)} tables, {len(all_columns)} columns")
        
        # Log key tables for debugging
        for t in tables:
            tname = t.get('table_name', '')
            cols = t.get('columns', [])
            cols_lower = [str(c).lower() for c in cols]
            
            if 'personal' in tname.lower():
                ptft_cols = [c for c in cols if any(x in str(c).lower() for x in ['part', 'full', 'time', 'ft', 'pt'])]
                if ptft_cols:
                    logger.warning(f"[SQL-GEN] PERSONAL PT/FT columns: {ptft_cols}")
            
            if 'company' in tname.lower() and 'master' not in tname.lower() and 'tax' not in tname.lower():
                rate_cols = [c for c in cols if any(x in str(c).lower() for x in ['rate', 'hour', 'pay', 'salary'])]
                if rate_cols:
                    logger.warning(f"[SQL-GEN] COMPANY rate columns: {rate_cols}")
        
        # Build relationships text
        relationships_text = ""
        if self.relationships:
            rel_lines = []
            for rel in self.relationships[:50]:
                src = f"{rel.get('source_table')}.{rel.get('source_column')}"
                tgt = f"{rel.get('target_table')}.{rel.get('target_column')}"
                rel_lines.append(f"  {src} → {tgt}")
            if rel_lines:
                relationships_text = "\n\nRELATIONSHIPS (use these for JOINs):\n" + "\n".join(rel_lines)
                logger.warning(f"[SQL-GEN] Including {len(rel_lines)} relationships")
        
        # Build conversation context
        context_str = ""
        if hasattr(self, 'conversation_context') and self.conversation_context:
            last_q = self.conversation_context.get('last_question', '')
            last_sql = self.conversation_context.get('last_sql', '')
            last_result = self.conversation_context.get('last_result', '')
            
            if last_q or last_sql:
                context_str = f"""
PREVIOUS CONVERSATION:
Previous question: {last_q}
Previous SQL: {last_sql}
Previous result: {last_result[:300] if last_result else 'None'}

If this references previous results, use the same tables/conditions.
"""
        
        # Build prompt for orchestrator
        prompt = f"""{context_str}
SCHEMA (with sample values):
{schema_text}{relationships_text}

QUESTION: {question}

RULES:
1. ONLY use column names from the schema - never invent columns
2. Use ILIKE for text matching
3. COUNT(*) for "how many" questions  
4. Wrap names in double quotes
5. JOIN tables using the relationships
6. TRY_CAST for numeric comparisons
7. LIMIT 1000 unless counting"""
        
        logger.warning(f"[SQL-GEN] Calling orchestrator...")
        
        # Call orchestrator - handles model selection, validation, retry
        result = orchestrator.generate_sql(prompt, all_columns)
        
        if result.get('success') and result.get('sql'):
            sql = result['sql']
            model = result.get('model', 'local')
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
            
            # Extract table name
            table_match = re.search(r'FROM\s+"?([^"\s]+)"?', sql, re.IGNORECASE)
            table_name = table_match.group(1) if table_match else 'unknown'
            
            return {
                'sql': sql,
                'table': table_name,
                'query_type': query_type,
                'model': model,
                'all_columns': all_columns  # For self-healing at execution
            }
        else:
            error = result.get('error', 'Unknown')
            logger.warning(f"[SQL-GEN] Failed: {error}")
            return None
    
    def _try_fix_sql_from_error(self, sql: str, error_msg: str, all_columns: set) -> Optional[str]:
        """
        Try to fix SQL based on DuckDB error message.
        
        Example error: 'Table "x" does not have a column named "rate"'
        """
        import re
        from difflib import SequenceMatcher
        
        # Extract the bad column name from error
        match = re.search(r'does not have a column named "([^"]+)"', error_msg)
        if not match:
            return None
        
        bad_col = match.group(1)
        logger.info(f"[SQL-FIX] Attempting to fix column: {bad_col}")
        
        # Known fixes
        known_fixes = {
            'rate': 'hourly_pay_rate',
            'hourly_rate': 'hourly_pay_rate',
            'pay_rate': 'hourly_pay_rate',
            'employee_id': 'employee_number',
            'emp_id': 'employee_number',
            'id': 'employee_number',
            'status': 'employment_status_code',
        }
        
        if bad_col.lower() in known_fixes:
            fix = known_fixes[bad_col.lower()]
            # Verify the fix exists in schema
            if fix.lower() in {c.lower() for c in all_columns}:
                logger.info(f"[SQL-FIX] Known fix: {bad_col} → {fix}")
                return re.sub(
                    r'\.\"?' + re.escape(bad_col) + r'\"?',
                    f'."{fix}"',
                    sql,
                    flags=re.IGNORECASE
                )
        
        # Fuzzy match
        best_match = None
        best_score = 0.5
        
        for col in all_columns:
            if bad_col.lower() in col.lower():
                score = 0.8
            else:
                score = SequenceMatcher(None, bad_col.lower(), col.lower()).ratio()
            
            if score > best_score:
                best_score = score
                best_match = col
        
        if best_match:
            logger.info(f"[SQL-FIX] Fuzzy fix: {bad_col} → {best_match} (score: {best_score:.2f})")
            return re.sub(
                r'\.\"?' + re.escape(bad_col) + r'\"?',
                f'."{best_match}"',
                sql,
                flags=re.IGNORECASE
            )
        
        logger.warning(f"[SQL-FIX] Could not find fix for: {bad_col}")
        return None
    
    def _needs_clarification(self, mode, entities, domains, q_lower) -> bool:
        """Determine if we need to ask clarifying questions."""
        
        # CRITICAL: If we already have clarification answers, DON'T ask again
        if self.confirmed_facts:
            logger.info(f"[INTELLIGENCE] Skipping clarification - already have answers: {list(self.confirmed_facts.keys())}")
            return False
        
        # ALWAYS ask for configuration tasks
        if mode == IntelligenceMode.CONFIGURE:
            return True
        
        # ALWAYS ask for validation without clear context
        if mode == IntelligenceMode.VALIDATE:
            return True
        
        # For data queries - check if question is specific enough
        is_specific = False
        
        # Check if they specified employee filters
        has_employee_filter = any(w in q_lower for w in [
            'pt ', 'ft ', 'part-time', 'part time', 'full-time', 'full time',
            'active', 'terminated', 'termed', 'all employees', 'hourly', 'salaried'
        ])
        
        # Check if they specified a clear numeric condition
        has_numeric_condition = any(w in q_lower for w in [
            'more than', 'less than', 'over', 'under', 'above', 'below',
            'at least', 'greater than', 'equal to', '$'
        ])
        
        # Check if it's a simple count/list with clear criteria
        is_simple_query = any(w in q_lower for w in ['how many', 'count', 'list', 'show me'])
        
        # Question is specific if it has filters AND is a simple query type
        if is_simple_query and (has_employee_filter or has_numeric_condition):
            is_specific = True
        
        # Question is specific if it mentions specific entities
        if entities and len(entities) > 0:
            is_specific = True
        
        # If not specific, ask clarification
        if not is_specific and 'employees' in domains:
            return True
        
        # For earnings/deductions, ask if no clear criteria
        if 'earnings' in domains and not has_numeric_condition:
            return True
        
        return False
    
    def _get_clarification_questions(self, mode, domains) -> List[Dict]:
        """Get clarification questions for the given mode/domains."""
        questions = []
        
        if 'employees' in domains:
            questions.append({
                'id': 'employee_status',
                'question': 'Which employees should I include?',
                'type': 'radio',
                'options': [
                    {'id': 'active', 'label': 'Active only', 'default': True},
                    {'id': 'termed', 'label': 'Terminated only'},
                    {'id': 'all', 'label': 'All employees'},
                ]
            })
        
        if 'earnings' in domains:
            questions.append({
                'id': 'earnings_scope',
                'question': 'What earnings data are you interested in?',
                'type': 'radio',
                'options': [
                    {'id': 'current_rates', 'label': 'Current pay rates', 'default': True},
                    {'id': 'ytd', 'label': 'Year-to-date earnings'},
                    {'id': 'history', 'label': 'Historical earnings'},
                ]
            })
        
        if 'deductions' in domains:
            questions.append({
                'id': 'deduction_type',
                'question': 'What type of deductions?',
                'type': 'radio',
                'options': [
                    {'id': 'all', 'label': 'All deductions', 'default': True},
                    {'id': 'benefits', 'label': 'Benefits only (medical, dental, etc.)'},
                    {'id': 'retirement', 'label': 'Retirement only (401k, pension)'},
                    {'id': 'other', 'label': 'Other deductions'},
                ]
            })
        
        if mode == IntelligenceMode.CONFIGURE:
            questions.append({
                'id': 'config_type',
                'question': 'What are you trying to configure?',
                'type': 'radio',
                'options': [
                    {'id': 'earning', 'label': 'Earning code/calculation'},
                    {'id': 'deduction', 'label': 'Deduction setup'},
                    {'id': 'tax', 'label': 'Tax configuration'},
                    {'id': 'other', 'label': 'Something else'},
                ]
            })
        
        if mode == IntelligenceMode.VALIDATE:
            questions.append({
                'id': 'validation_type',
                'question': 'What would you like me to validate?',
                'type': 'radio',
                'options': [
                    {'id': 'data_quality', 'label': 'Data quality/completeness'},
                    {'id': 'business_rules', 'label': 'Business rule compliance'},
                    {'id': 'config', 'label': 'Configuration accuracy'},
                    {'id': 'comparison', 'label': 'Compare against source'},
                ]
            })
        
        return questions
    
    def _request_clarification(self, question: str, analysis: Dict) -> SynthesizedAnswer:
        """Return a response that asks for clarification."""
        return SynthesizedAnswer(
            question=question,
            answer="",
            confidence=0.0,
            structured_output={
                'type': 'clarification_needed',
                'questions': analysis['clarification_questions'],
                'original_question': question,
                'detected_mode': analysis['mode'].value,
                'detected_domains': analysis['domains']
            },
            reasoning=['Need more information to provide accurate answer']
        )
    
    def _gather_reality(self, question: str, analysis: Dict) -> List[Truth]:
        """Gather REALITY - what the customer's DATA shows."""
        logger.warning(f"[REALITY] Starting - handler: {self.structured_handler is not None}, schema tables: {len(self.schema.get('tables', [])) if self.schema else 0}")
        
        if not self.structured_handler:
            logger.warning("[REALITY] No structured handler - returning empty")
            return []
        
        if not self.schema or not self.schema.get('tables'):
            logger.warning("[REALITY] No schema tables - returning empty")
            return []
        
        truths = []
        domains = analysis['domains']
        entities = analysis['entities']
        
        try:
            # FIRST: Try to generate and execute targeted SQL
            sql_info = self._generate_sql_for_question(question, analysis)
            if sql_info:
                sql = sql_info['sql']
                logger.info(f"[INTELLIGENCE] Generated SQL: {sql}")
                
                # Try to execute with self-healing on column errors
                max_retries = 2
                for attempt in range(max_retries + 1):
                    try:
                        rows, cols = self.structured_handler.execute_query(sql)
                        
                        # Store the SQL for session context
                        self.last_executed_sql = sql
                        
                        if rows:
                            truths.append(Truth(
                                source_type='reality',
                                source_name=f"SQL Query: {sql_info['table']}",
                                content={
                                    'sql': sql,
                                    'columns': cols,
                                    'rows': rows,
                                    'total': len(rows),
                                    'query_type': sql_info['query_type'],
                                    'table': sql_info['table'],
                                    'is_targeted_query': True
                                },
                                confidence=0.98,
                                location=f"Query: {sql}"
                            ))
                            logger.info(f"[INTELLIGENCE] SQL returned {len(rows)} rows")
                            return truths
                        break  # Success but no rows
                        
                    except Exception as sql_e:
                        error_msg = str(sql_e)
                        logger.warning(f"[INTELLIGENCE] SQL query failed (attempt {attempt + 1}): {error_msg}")
                        
                        # Try to extract and fix the column name from the error
                        if attempt < max_retries and 'does not have a column named' in error_msg:
                            fixed_sql = self._try_fix_sql_from_error(sql, error_msg, sql_info.get('all_columns', set()))
                            if fixed_sql and fixed_sql != sql:
                                logger.info(f"[INTELLIGENCE] Attempting auto-fix: {fixed_sql[:100]}...")
                                sql = fixed_sql
                                continue
                        break  # Can't fix or out of retries
            
            # FALLBACK: Sample data from relevant tables
            tables = self.schema.get('tables', [])
            
            for table in tables:
                table_name = table.get('table_name', '')
                columns = table.get('columns', [])
                
                # Filter to relevant tables
                relevant = False
                if 'employees' in domains and any(c in table_name.lower() for c in ['personal', 'employee', 'demographic']):
                    relevant = True
                if 'earnings' in domains and any(c in table_name.lower() for c in ['earning', 'pay', 'rate', 'salary', 'compensation']):
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
                except Exception as e:
                    logger.debug(f"Query failed for {table_name}: {e}")
        
        except Exception as e:
            logger.error(f"Error gathering reality: {e}")
        
        return truths
    
    def _gather_intent(self, question: str, analysis: Dict) -> List[Truth]:
        """Gather INTENT - what customer's DOCUMENTS say."""
        if not self.rag_handler:
            return []
        
        truths = []
        
        try:
            # Try to find the right collection name
            collection_name = self._get_document_collection_name()
            if not collection_name:
                logger.warning("No document collection found")
                return []
            
            # Use rag_handler.search() which properly handles embeddings
            # Filter by project to get customer-specific docs (excludes Global/Universal)
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
                
                # Skip global docs - we want customer-specific intent
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
        """Find the document collection name from available collections."""
        if not self.rag_handler:
            return None
        
        # Cache the result
        if hasattr(self, '_doc_collection_name'):
            return self._doc_collection_name
        
        try:
            collections = self.rag_handler.list_collections()
            
            # Priority order for document collections
            preferred = ['hcmpact_docs', 'documents', 'hcm_docs', 'xlr8_docs']
            
            for name in preferred:
                if name in collections:
                    self._doc_collection_name = name
                    logger.info(f"Using document collection: {name}")
                    return name
            
            # Fall back to any collection that might have docs
            for name in collections:
                if 'doc' in name.lower() or 'hcm' in name.lower():
                    self._doc_collection_name = name
                    logger.info(f"Using document collection (fallback): {name}")
                    return name
            
            # Last resort - use first collection if any
            if collections:
                self._doc_collection_name = collections[0]
                logger.warning(f"Using first available collection: {collections[0]}")
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
            # Try to find the right collection name
            collection_name = self._get_document_collection_name()
            if not collection_name:
                logger.warning("No document collection found for best practices")
                return []
            
            # Use rag_handler.search() with Global/Universal to get only UKG best practices
            results = self.rag_handler.search(
                collection_name=collection_name,
                query=question,
                n_results=10,
                project_id="Global/Universal"  # Only get global/UKG docs
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
        # Placeholder - return empty for now
        return []
    
    def _run_proactive_checks(self, analysis: Dict) -> List[Insight]:
        """Run proactive checks while answering."""
        insights = []
        domains = analysis['domains']
        
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
            context_parts.append("=== CUSTOMER DATA ===")
            for truth in reality[:3]:
                if isinstance(truth.content, dict) and 'rows' in truth.content:
                    rows = truth.content['rows']
                    cols = truth.content['columns']
                    context_parts.append(f"\nSource: {truth.source_name}")
                    context_parts.append(f"Columns: {', '.join(cols[:10])}")
                    context_parts.append(f"Sample data ({len(rows)} rows):")
                    for row in rows[:5]:
                        row_str = " | ".join(f"{k}: {v}" for k, v in list(row.items())[:6])
                        context_parts.append(f"  {row_str}")
            reasoning.append(f"Found {len(reality)} relevant data sources")
        
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
