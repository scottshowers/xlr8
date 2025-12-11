"""
XLR8 INTELLIGENCE ENGINE v3
============================

Deploy to: backend/utils/intelligence_engine.py

SIMPLIFIED:
- Only asks ONE clarification: active/terminated/all employees
- Only when the question is about employees
- Everything else: just query the data
- LLM used for SQL generation only (where it adds value)
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

# LOAD VERIFICATION - this line proves the new file is loaded
logger.warning("[INTELLIGENCE_ENGINE] ====== v3.1 LOADED ======")


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Truth:
    """A piece of information from one source of truth."""
    source_type: str
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
# SEMANTIC PATTERNS (for column matching only)
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
        self.conversation_context = {}
        self.last_executed_sql = None
    
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
        logger.warning(f"[INTELLIGENCE] Question: {question[:100]}...")
        logger.warning(f"[INTELLIGENCE] Current confirmed_facts: {self.confirmed_facts}")
        
        q_lower = question.lower()
        
        # Simple analysis
        mode = mode or self._detect_mode(q_lower)
        is_employee_question = self._is_employee_question(q_lower)
        logger.warning(f"[INTELLIGENCE] is_employee_question: {is_employee_question}")
        
        # ONLY clarification: employee status (active/termed/all)
        # Only ask if:
        # 1. Question involves employees
        # 2. User hasn't already answered
        # 3. User didn't specify in the question
        if is_employee_question and 'employee_status' not in self.confirmed_facts:
            # Check if user specified status in the question itself
            detected_status = self._detect_status_in_question(q_lower)
            logger.warning(f"[INTELLIGENCE] detected_status: {detected_status}")
            if detected_status:
                # User specified - set it and continue
                self.confirmed_facts['employee_status'] = detected_status
                logger.warning(f"[INTELLIGENCE] Detected status in question: {detected_status}")
            else:
                # Need to ask
                logger.warning("[INTELLIGENCE] Asking for employee status clarification")
                return self._request_employee_status_clarification(question)
        
        logger.warning(f"[INTELLIGENCE] Proceeding with facts: {self.confirmed_facts}")
        
        # Gather the three truths
        analysis = {'domains': self._detect_domains(q_lower), 'mode': mode}
        
        reality = self._gather_reality(question, analysis)
        logger.info(f"[INTELLIGENCE] Reality gathered: {len(reality)} truths")
        
        intent = self._gather_intent(question, analysis)
        best_practice = self._gather_best_practice(question, analysis)
        
        conflicts = self._detect_conflicts(reality, intent, best_practice)
        insights = self._run_proactive_checks(analysis)
        
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
        
        self.conversation_history.append({
            'question': question,
            'answer_preview': answer.answer[:200] if answer.answer else '',
            'mode': mode.value if mode else 'search',
            'timestamp': datetime.now().isoformat()
        })
        
        return answer
    
    def _is_employee_question(self, q_lower: str) -> bool:
        """Check if question is about employees/people."""
        employee_words = [
            'employee', 'employees', 'worker', 'workers', 'staff', 
            'people', 'person', 'who ', 'how many', 'count',
            'headcount', 'roster', 'census'
        ]
        return any(w in q_lower for w in employee_words)
    
    def _detect_status_in_question(self, q_lower: str) -> Optional[str]:
        """
        Check if user specified employee status in their question.
        Returns the detected status ('active', 'termed', 'all') or None.
        """
        # Active patterns
        if any(p in q_lower for p in ['active only', 'active employees', 'only active', 'current employees']):
            return 'active'
        
        # Terminated patterns
        if any(p in q_lower for p in ['terminated', 'termed', 'inactive', 'former employees']):
            return 'termed'
        
        # All patterns
        if any(p in q_lower for p in ['all employees', 'everyone', 'all staff', 'all workers', 'total employees']):
            return 'all'
        
        return None
    
    def _request_employee_status_clarification(self, question: str) -> SynthesizedAnswer:
        """Ask for employee status clarification using ACTUAL values from the data."""
        
        # Get actual status values from profile data
        status_options = self._get_status_options_from_profiles()
        
        if not status_options:
            # Fallback to generic options if no profile data
            status_options = [
                {'id': 'active', 'label': 'Active only', 'default': True},
                {'id': 'termed', 'label': 'Terminated only'},
                {'id': 'all', 'label': 'All employees'}
            ]
        
        return SynthesizedAnswer(
            question=question,
            answer="",
            confidence=0.0,
            structured_output={
                'type': 'clarification_needed',
                'questions': [{
                    'id': 'employee_status',
                    'question': 'Which employees should I include?',
                    'type': 'radio',
                    'options': status_options
                }],
                'original_question': question,
                'detected_mode': 'search',
                'detected_domains': ['employees']
            },
            reasoning=['Need to know which employees to include']
        )
    
    def _get_status_options_from_profiles(self) -> List[Dict]:
        """
        Get employee status options from actual profile data.
        This is the key Phase 2 feature - data-driven clarification.
        """
        if not self.schema:
            return []
        
        tables = self.schema.get('tables', [])
        
        # Look for status-related columns in the profiles
        status_patterns = ['status', 'employment_status', 'emp_status', 'employee_status', 
                          'employment_status_code', 'termination_date', 'term_date']
        
        for table in tables:
            categorical_cols = table.get('categorical_columns', [])
            column_profiles = table.get('column_profiles', {})
            
            # Check categorical columns for status-like values
            for cat_col in categorical_cols:
                col_name = cat_col.get('column', '').lower()
                
                # Is this a status column?
                if any(pattern in col_name for pattern in status_patterns):
                    values = cat_col.get('values', [])
                    distribution = cat_col.get('distribution', {})
                    
                    if values:
                        return self._build_status_options(values, distribution, col_name)
            
            # Also check column_profiles directly
            for col_name, profile in column_profiles.items():
                col_lower = col_name.lower()
                if any(pattern in col_lower for pattern in status_patterns):
                    if profile.get('is_categorical') and profile.get('distinct_values'):
                        values = profile['distinct_values']
                        distribution = profile.get('value_distribution', {})
                        return self._build_status_options(values, distribution, col_name)
        
        return []
    
    def _build_status_options(self, values: List[str], distribution: Dict, col_name: str) -> List[Dict]:
        """Build clarification options from actual data values."""
        options = []
        
        # Common status code mappings
        status_labels = {
            'A': 'Active', 'T': 'Terminated', 'L': 'Leave', 'I': 'Inactive',
            'ACTIVE': 'Active', 'TERMED': 'Terminated', 'TERM': 'Terminated',
            'LOA': 'Leave of Absence', 'LEAVE': 'Leave', 'INACTIVE': 'Inactive',
            'REG': 'Regular', 'TEMP': 'Temporary', 'PART': 'Part-time',
            'FT': 'Full-time', 'PT': 'Part-time'
        }
        
        # Build options with counts
        active_values = []
        termed_values = []
        other_values = []
        
        for val in values:
            val_upper = str(val).upper().strip()
            count = distribution.get(val, distribution.get(str(val), 0))
            
            # Categorize
            if val_upper in ['A', 'ACTIVE', 'ACT']:
                active_values.append((val, count))
            elif val_upper in ['T', 'TERMINATED', 'TERM', 'TERMED', 'I', 'INACTIVE']:
                termed_values.append((val, count))
            else:
                other_values.append((val, count))
        
        # Build options with actual counts
        if active_values:
            active_count = sum(c for _, c in active_values)
            active_codes = ', '.join(v for v, _ in active_values)
            options.append({
                'id': 'active',
                'label': f'Active only ({active_count:,} employees)',
                'codes': active_codes,
                'default': True
            })
        
        if termed_values:
            termed_count = sum(c for _, c in termed_values)
            termed_codes = ', '.join(v for v, _ in termed_values)
            options.append({
                'id': 'termed',
                'label': f'Terminated only ({termed_count:,} employees)',
                'codes': termed_codes
            })
        
        # Add "All" option with total
        total_count = sum(distribution.values()) if distribution else 0
        options.append({
            'id': 'all',
            'label': f'All employees ({total_count:,} total)'
        })
        
        # If we couldn't categorize well, show raw values
        if not active_values and not termed_values and other_values:
            options = []
            for val, count in sorted(other_values, key=lambda x: -x[1])[:5]:
                label = status_labels.get(str(val).upper(), str(val))
                options.append({
                    'id': str(val).lower(),
                    'label': f'{label} ({count:,})',
                    'code': val
                })
            options.append({'id': 'all', 'label': f'All ({total_count:,} total)'})
        
        logger.info(f"[CLARIFICATION] Built {len(options)} options from {col_name}: {[o['id'] for o in options]}")
        return options
    
    def _get_status_column_and_codes(self, status_filter: str) -> Tuple[Optional[str], List[str]]:
        """
        Get the actual column name and codes to use for filtering.
        Returns (column_name, [list of codes])
        """
        if not self.schema:
            return None, []
        
        tables = self.schema.get('tables', [])
        status_patterns = ['status', 'employment_status', 'emp_status', 'employee_status', 'employment_status_code']
        
        for table in tables:
            categorical_cols = table.get('categorical_columns', [])
            column_profiles = table.get('column_profiles', {})
            
            for cat_col in categorical_cols:
                col_name = cat_col.get('column', '')
                col_lower = col_name.lower()
                
                if any(pattern in col_lower for pattern in status_patterns):
                    values = cat_col.get('values', [])
                    
                    # Find matching codes based on status_filter
                    if status_filter == 'active':
                        codes = [v for v in values if str(v).upper() in ['A', 'ACTIVE', 'ACT']]
                    elif status_filter == 'termed':
                        codes = [v for v in values if str(v).upper() in ['T', 'TERMINATED', 'TERM', 'TERMED', 'I', 'INACTIVE']]
                    else:
                        # Check if filter matches a specific code
                        codes = [v for v in values if str(v).lower() == status_filter.lower()]
                    
                    if codes:
                        return col_name, codes
            
            # Also check column_profiles
            for col_name, profile in column_profiles.items():
                col_lower = col_name.lower()
                if any(pattern in col_lower for pattern in status_patterns):
                    values = profile.get('distinct_values', [])
                    
                    if status_filter == 'active':
                        codes = [v for v in values if str(v).upper() in ['A', 'ACTIVE', 'ACT']]
                    elif status_filter == 'termed':
                        codes = [v for v in values if str(v).upper() in ['T', 'TERMINATED', 'TERM', 'TERMED', 'I', 'INACTIVE']]
                    else:
                        codes = [v for v in values if str(v).lower() == status_filter.lower()]
                    
                    if codes:
                        return col_name, codes
        
        return None, []
    
    def _detect_mode(self, q_lower: str) -> IntelligenceMode:
        """Detect the appropriate intelligence mode."""
        if any(w in q_lower for w in ['validate', 'check', 'verify', 'issues', 'problems']):
            return IntelligenceMode.VALIDATE
        if any(w in q_lower for w in ['configure', 'set up', 'setup']):
            return IntelligenceMode.CONFIGURE
        if any(w in q_lower for w in ['compare', 'versus', 'vs', 'difference']):
            return IntelligenceMode.COMPARE
        if any(w in q_lower for w in ['report', 'summary', 'overview']):
            return IntelligenceMode.REPORT
        if any(w in q_lower for w in ['analyze', 'trend', 'pattern']):
            return IntelligenceMode.ANALYZE
        return IntelligenceMode.SEARCH
    
    def _detect_domains(self, q_lower: str) -> List[str]:
        """Detect which data domains are relevant."""
        domains = []
        
        if any(w in q_lower for w in ['employee', 'worker', 'staff', 'people', 'who', 'how many', 'count']):
            domains.append('employees')
        if any(w in q_lower for w in ['earn', 'pay', 'salary', 'wage', 'rate', 'hour', '$', 'compensation']):
            domains.append('earnings')
        if any(w in q_lower for w in ['deduction', 'benefit', '401k', 'insurance', 'health']):
            domains.append('deductions')
        if any(w in q_lower for w in ['tax', 'withhold', 'federal', 'state']):
            domains.append('taxes')
        if any(w in q_lower for w in ['job', 'position', 'title', 'department']):
            domains.append('jobs')
        
        return domains if domains else ['general']
    
    def _select_relevant_tables(self, tables: List[Dict], q_lower: str) -> List[Dict]:
        """
        Select only tables relevant to the question.
        This keeps the SQL prompt small and focused.
        """
        if not tables:
            return []
        
        # Priority keywords for table selection
        table_keywords = {
            'personal': ['employee', 'employees', 'person', 'people', 'who', 'name', 'ssn', 'birth', 'hire'],
            'company': ['company', 'organization', 'org', 'entity'],
            'job': ['job', 'position', 'title', 'department', 'dept'],
            'earnings': ['earn', 'earning', 'pay', 'salary', 'wage', 'compensation', 'rate'],
            'deductions': ['deduction', 'benefit', '401k', 'insurance', 'health'],
            'taxes': ['tax', 'withhold', 'federal', 'state'],
            'time': ['time', 'hours', 'attendance', 'schedule'],
            'address': ['address', 'location', 'city', 'state', 'zip'],
        }
        
        # Score each table
        scored_tables = []
        for table in tables:
            table_name = table.get('table_name', '').lower()
            short_name = table_name.split('__')[-1] if '__' in table_name else table_name
            
            score = 0
            
            # Check if table name matches any keyword patterns
            for pattern, keywords in table_keywords.items():
                if pattern in short_name:
                    # Check if any keyword is in the question
                    if any(kw in q_lower for kw in keywords):
                        score += 10
                    else:
                        score += 1  # Table exists but question doesn't directly ask about it
            
            # Boost "personal" table for general employee questions
            if 'personal' in short_name and any(kw in q_lower for kw in ['employee', 'how many', 'count', 'who']):
                score += 20
            
            # Boost tables with high row counts (they're likely the main tables)
            row_count = table.get('row_count', 0)
            if row_count > 1000:
                score += 5
            elif row_count > 100:
                score += 2
            
            scored_tables.append((score, table))
        
        # Sort by score descending
        scored_tables.sort(key=lambda x: -x[0])
        
        # Take top 3 tables max (keeps prompt small)
        relevant = [t for score, t in scored_tables[:3] if score > 0]
        
        # If no relevant tables found, just use first table
        if not relevant:
            relevant = [tables[0]]
        
        logger.info(f"[SQL-GEN] Selected {len(relevant)} relevant tables: {[t.get('table_name', '').split('__')[-1] for t in relevant]}")
        
        return relevant
    
    def _generate_sql_for_question(self, question: str, analysis: Dict) -> Optional[Dict]:
        """Generate SQL query using LLMOrchestrator with SMART table selection."""
        logger.warning(f"[SQL-GEN] v3.1 - Starting SQL generation")
        logger.warning(f"[SQL-GEN] confirmed_facts: {self.confirmed_facts}")
        
        if not self.structured_handler or not self.schema:
            return None
        
        tables = self.schema.get('tables', [])
        if not tables:
            return None
        
        # Get LLMOrchestrator
        try:
            try:
                from utils.llm_orchestrator import LLMOrchestrator
            except ImportError:
                from backend.utils.llm_orchestrator import LLMOrchestrator
            
            orchestrator = LLMOrchestrator()
        except Exception as e:
            logger.error(f"[SQL-GEN] Could not load LLMOrchestrator: {e}")
            return None
        
        # SMART TABLE SELECTION - only include relevant tables
        q_lower = question.lower()
        relevant_tables = self._select_relevant_tables(tables, q_lower)
        
        # Build COMPACT schema - only relevant tables, minimal samples
        tables_info = []
        all_columns = set()
        primary_table = None
        
        for i, table in enumerate(relevant_tables):
            table_name = table.get('table_name', '')
            columns = table.get('columns', [])
            if columns and isinstance(columns[0], dict):
                col_names = [c.get('name', str(c)) for c in columns]
            else:
                col_names = [str(c) for c in columns] if columns else []
            row_count = table.get('row_count', 0)
            
            all_columns.update(col_names)
            
            # First relevant table is "primary"
            if i == 0:
                primary_table = table_name
            
            # Only include sample for primary table
            sample_str = ""
            if i == 0:
                try:
                    rows, cols = self.structured_handler.execute_query(f'SELECT * FROM "{table_name}" LIMIT 2')
                    if rows and cols:
                        samples = []
                        for col in cols[:4]:  # Limit to 4 columns
                            vals = set(str(row.get(col, ''))[:15] for row in rows if row.get(col))
                            if vals:
                                samples.append(f"    {col}: {', '.join(list(vals)[:2])}")
                        sample_str = "\n  Sample:\n" + "\n".join(samples[:4]) if samples else ""
                except:
                    pass
            
            # Compact column list
            col_str = ', '.join(col_names[:15])
            if len(col_names) > 15:
                col_str += f" (+{len(col_names) - 15} more)"
            
            tables_info.append(f"Table: {table_name}\n  Columns: {col_str}\n  Rows: {row_count}{sample_str}")
        
        schema_text = '\n\n'.join(tables_info)
        
        # SIMPLIFIED relationships - only between relevant tables
        relationships_text = ""
        if self.relationships and len(relevant_tables) > 1:
            relevant_table_names = {t.get('table_name', '') for t in relevant_tables}
            rel_lines = []
            for rel in self.relationships[:10]:
                src_table = rel.get('source_table', '')
                tgt_table = rel.get('target_table', '')
                if src_table in relevant_table_names and tgt_table in relevant_table_names:
                    src = f"{src_table.split('__')[-1]}.{rel.get('source_column')}"
                    tgt = f"{tgt_table.split('__')[-1]}.{rel.get('target_column')}"
                    rel_lines.append(f"  {src} → {tgt}")
            if rel_lines:
                relationships_text = "\n\nJOIN ON:\n" + "\n".join(rel_lines[:5])
        
        # Employee status filter
        filter_instructions = ""
        status_filter = self.confirmed_facts.get('employee_status')
        
        if status_filter and status_filter != 'all':
            status_col, status_codes = self._get_status_column_and_codes(status_filter)
            
            if status_col and status_codes:
                codes_str = ', '.join(f"'{c}'" for c in status_codes)
                filter_instructions = f"\n\nFILTER: WHERE {status_col} IN ({codes_str})"
            elif status_filter == 'active':
                filter_instructions = "\n\nFILTER: WHERE termination_date IS NULL OR termination_date = ''"
            elif status_filter == 'termed':
                filter_instructions = "\n\nFILTER: WHERE termination_date IS NOT NULL AND termination_date != ''"
        
        # SIMPLE vs COMPLEX query hint
        query_hint = ""
        if 'how many' in q_lower or 'count' in q_lower:
            query_hint = f"\n\nHINT: For COUNT, use single table: SELECT COUNT(*) FROM \"{primary_table}\""
        
        prompt = f"""SCHEMA:
{schema_text}{relationships_text}
{filter_instructions}{query_hint}

QUESTION: {question}

RULES:
1. Use ONLY columns from schema above
2. For "how many" → SELECT COUNT(*) FROM single_table
3. ILIKE for text matching
4. Quote table names with special chars

SQL:"""
        
        logger.warning(f"[SQL-GEN] Calling orchestrator ({len(prompt)} chars, {len(relevant_tables)} tables)")
        
        result = orchestrator.generate_sql(prompt, all_columns)
        
        if result.get('success') and result.get('sql'):
            sql = result['sql'].strip()
            
            # Clean markdown
            if '```' in sql:
                sql = re.sub(r'```sql\s*', '', sql, flags=re.IGNORECASE)
                sql = re.sub(r'```\s*$', '', sql)
                sql = sql.replace('```', '').strip()
            
            logger.warning(f"[SQL-GEN] Generated: {sql[:150]}")
            
            # Detect query type
            sql_upper = sql.upper()
            if 'COUNT(' in sql_upper:
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
                'all_columns': all_columns
            }
        
        return None
    
    def _try_fix_sql_from_error(self, sql: str, error_msg: str, all_columns: set) -> Optional[str]:
        """Try to fix SQL based on error message."""
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
        
        valid_cols_lower = {c.lower() for c in all_columns}
        
        known_fixes = {
            'rate': 'hourly_pay_rate',
            'hourly_rate': 'hourly_pay_rate',
            'pay_rate': 'hourly_pay_rate',
            'employee_id': 'employee_number',
            'emp_id': 'employee_number',
        }
        
        fix = known_fixes.get(bad_col.lower())
        if fix and fix.lower() in valid_cols_lower:
            logger.info(f"[SQL-FIX] {bad_col} → {fix}")
            return re.sub(r'\b' + re.escape(bad_col) + r'\b', f'"{fix}"', sql, flags=re.IGNORECASE)
        
        # Fuzzy match
        if '_' in bad_col:
            best_score = 0.6
            for col in all_columns:
                score = SequenceMatcher(None, bad_col.lower(), col.lower()).ratio()
                if score > best_score:
                    best_score = score
                    fix = col
            if fix:
                logger.info(f"[SQL-FIX] Fuzzy: {bad_col} → {fix}")
                return re.sub(r'\b' + re.escape(bad_col) + r'\b', f'"{fix}"', sql, flags=re.IGNORECASE)
        
        return None
    
    def _gather_reality(self, question: str, analysis: Dict) -> List[Truth]:
        """Gather REALITY - what the customer's DATA shows."""
        if not self.structured_handler or not self.schema:
            return []
        
        truths = []
        domains = analysis.get('domains', ['general'])
        
        # Pattern cache
        pattern_cache = None
        try:
            from utils.sql_pattern_cache import initialize_patterns
            if self.project:
                pattern_cache = initialize_patterns(self.project, self.schema)
        except:
            try:
                from backend.utils.sql_pattern_cache import initialize_patterns
                if self.project:
                    pattern_cache = initialize_patterns(self.project, self.schema)
            except:
                pass
        
        try:
            sql = None
            sql_source = None
            sql_info = None
            
            # Check cache
            if pattern_cache:
                cached = pattern_cache.find_matching_pattern(question)
                if cached and cached.get('sql'):
                    sql = cached['sql']
                    sql_source = 'cache'
                    logger.warning("[SQL] Cache hit!")
            
            # Generate if no cache
            if not sql:
                sql_info = self._generate_sql_for_question(question, analysis)
                if sql_info:
                    sql = sql_info['sql']
                    sql_source = 'llm'
            
            # Execute
            if sql:
                for attempt in range(3):
                    try:
                        rows, cols = self.structured_handler.execute_query(sql)
                        self.last_executed_sql = sql
                        
                        if rows:
                            table_name = sql_info.get('table', 'query') if sql_info else 'query'
                            
                            truths.append(Truth(
                                source_type='reality',
                                source_name=f"SQL: {table_name}",
                                content={
                                    'sql': sql,
                                    'columns': cols,
                                    'rows': rows,
                                    'total': len(rows),
                                    'query_type': sql_info.get('query_type', 'list') if sql_info else 'list',
                                    'table': table_name,
                                    'is_targeted_query': True
                                },
                                confidence=0.98,
                                location=f"Query: {sql}"
                            ))
                            
                            if pattern_cache and sql_source == 'llm':
                                pattern_cache.learn_pattern(question, sql, success=True)
                            
                            return truths
                        break
                        
                    except Exception as e:
                        error_msg = str(e)
                        logger.warning(f"[SQL] Failed attempt {attempt + 1}: {error_msg}")
                        
                        if sql_info and attempt < 2:
                            fixed = self._try_fix_sql_from_error(sql, error_msg, sql_info.get('all_columns', set()))
                            if fixed and fixed != sql:
                                sql = fixed
                                continue
                        break
        
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
            for name in ['hcmpact_docs', 'documents', 'hcm_docs', 'xlr8_docs']:
                if name in collections:
                    self._doc_collection_name = name
                    return name
            
            for name in collections:
                if 'doc' in name.lower():
                    self._doc_collection_name = name
                    return name
            
            if collections:
                self._doc_collection_name = collections[0]
                return collections[0]
        except:
            pass
        
        return None
    
    def _gather_best_practice(self, question: str, analysis: Dict) -> List[Truth]:
        """Gather BEST PRACTICE - what UKG docs say."""
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
        return []
    
    def _run_proactive_checks(self, analysis: Dict) -> List[Insight]:
        insights = []
        
        if not self.structured_handler:
            return insights
        
        try:
            tables = self.schema.get('tables', [])
            domains = analysis.get('domains', ['general'])
            
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
                                    data={'count': result[0]},
                                    severity='high',
                                    action_required=True
                                ))
                        except:
                            pass
                        break
        except:
            pass
        
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
        """Synthesize answer from all sources."""
        reasoning = []
        context_parts = []
        
        if reality:
            context_parts.append("=== DATA RESULTS ===")
            for truth in reality[:3]:
                if isinstance(truth.content, dict) and 'rows' in truth.content:
                    rows = truth.content['rows']
                    cols = truth.content['columns']
                    query_type = truth.content.get('query_type', 'list')
                    
                    if query_type == 'count' and rows:
                        count_val = list(rows[0].values())[0] if rows[0] else 0
                        context_parts.append(f"\n**ANSWER: {count_val}**")
                        context_parts.append(f"SQL: {truth.content.get('sql', '')[:200]}")
                    elif query_type in ['sum', 'average'] and rows:
                        result_val = list(rows[0].values())[0] if rows[0] else 0
                        context_parts.append(f"\n**RESULT: {result_val}**")
                        context_parts.append(f"SQL: {truth.content.get('sql', '')[:200]}")
                    else:
                        context_parts.append(f"\nResults ({len(rows)} rows):")
                        for row in rows[:10]:
                            row_str = " | ".join(f"{k}: {v}" for k, v in list(row.items())[:6])
                            context_parts.append(f"  {row_str}")
            reasoning.append(f"Found {len(reality)} data results")
        
        if intent:
            context_parts.append("\n=== CUSTOMER DOCS ===")
            for truth in intent[:3]:
                context_parts.append(f"\n{truth.source_name}: {str(truth.content)[:300]}")
            reasoning.append(f"Found {len(intent)} customer documents")
        
        if best_practice:
            context_parts.append("\n=== BEST PRACTICE ===")
            for truth in best_practice[:3]:
                context_parts.append(f"\n{truth.source_name}: {str(truth.content)[:300]}")
            reasoning.append(f"Found {len(best_practice)} best practice docs")
        
        if insights:
            context_parts.append("\n=== INSIGHTS ===")
            for insight in insights:
                icon = '🔴' if insight.severity == 'high' else '🟡'
                context_parts.append(f"{icon} {insight.title}: {insight.description}")
        
        combined = '\n'.join(context_parts)
        
        confidence = 0.5
        if reality:
            confidence += 0.3
        if intent:
            confidence += 0.1
        if best_practice:
            confidence += 0.05
        
        return SynthesizedAnswer(
            question=question,
            answer=combined,
            confidence=min(confidence, 0.95),
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
        """Clear confirmed facts."""
        self.confirmed_facts = {}
