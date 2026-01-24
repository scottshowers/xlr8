"""
XLR8 Query Engine - The Simple Path
====================================

This module replaces the entire intelligence layer with a straightforward approach:

1. CONTEXT ASSEMBLY: Find relevant tables, pull their schemas
2. SQL GENERATION: Give LLM the context, let it write SQL
3. EXECUTION: Run the SQL, handle errors gracefully
4. SYNTHESIS: Turn results into natural language

That's it. No term indexes, no hub-spoke detection, no deterministic SQL assembly.
Just good context + capable LLM = working queries.

Author: XLR8 Team
Date: January 22, 2026
Version: 1.0.0

REPLACES:
- engine.py (3,834 lines)
- query_resolver.py (3,232 lines)
- term_index.py (2,538 lines)
- sql_generator.py (1,997 lines)
- sql_assembler.py (1,566 lines)
- table_selector.py (1,032 lines)
- query_resolver_v2.py (748 lines)
- relationship_resolver.py (657 lines)
- metadata_reasoner.py (588 lines)
- value_parser.py (549 lines)
- intent_parser.py (478 lines)
Total replaced: ~17,000+ lines
"""

import re
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import traceback

logger = logging.getLogger(__name__)


# =============================================================================
# DATA TYPES
# =============================================================================

class QueryIntent(Enum):
    """What the user is trying to do."""
    COUNT = "count"           # How many X
    LIST = "list"             # Show me X
    AGGREGATE = "aggregate"   # Sum/avg/min/max of X
    COMPARE = "compare"       # X by Y (grouped)
    LOOKUP = "lookup"         # Find specific X
    GENERAL = "general"       # General question


@dataclass
class TableSchema:
    """Schema information for a single table."""
    table_name: str
    columns: List[str]
    column_types: Dict[str, str]  # column -> type
    sample_values: Dict[str, List[str]]  # column -> sample values
    row_count: int
    filter_columns: Dict[str, str]  # column -> filter_category (status, location, etc)


@dataclass
class QueryContext:
    """All the context needed for SQL generation."""
    question: str
    tables: List[TableSchema]
    join_paths: List[Dict[str, str]]  # [{from: "t1.col", to: "t2.col"}, ...]
    detected_intent: QueryIntent
    detected_entities: List[str]  # ["employee", "deduction", etc]
    detected_filters: Dict[str, str]  # {"state": "Texas", "status": "active"}
    business_rules: List['BusinessRule'] = field(default_factory=list)  # From BusinessRuleInterpreter


@dataclass
class QueryResult:
    """Result of a query execution."""
    success: bool
    sql: str
    data: List[Dict[str, Any]] = field(default_factory=list)
    row_count: int = 0
    columns: List[str] = field(default_factory=list)
    error: Optional[str] = None
    error_type: Optional[str] = None  # "no_table", "bad_column", "syntax", "empty"


# =============================================================================
# BUSINESS RULE INTERPRETER (Learning-based)
# =============================================================================

@dataclass
class BusinessRule:
    """A business rule - either learned or pending confirmation."""
    pattern: str           # Pattern key (e.g., "by_date", "as_of")
    description: str       # Human-readable explanation
    sql_template: str      # SQL fragment to apply
    parameters: Dict[str, str]  # e.g., {"column": "lastHireDate", "grouping": "year"}
    source: str = "learned"  # "learned", "pending", "default"


@dataclass
class ClarificationRequest:
    """A request for user clarification."""
    pattern: str
    question: str
    options: List[Dict[str, str]]  # [{display, value, description}, ...]
    context: str  # Additional context for the user


class BusinessRuleInterpreter:
    """
    Learns business rules through clarification questions.
    
    Empty on day 1, smart by day 30.
    """
    
    # Patterns we can detect and need rules for
    DETECTABLE_PATTERNS = {
        'by_date': {
            'regex': r'\bby\s+date\b',
            'question': "Which date field do you want to use?",
            'options_query': "date",  # Search for date columns
        },
        'as_of': {
            'regex': r'\bas\s+of\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})',
            'question': "How should I interpret 'as of {date}'?",
            'options': [
                {'display': 'Hired on/before that date AND not terminated before it', 'value': 'point_in_time_hire_term'},
                {'display': 'Status was Active on that date', 'value': 'status_on_date'},
                {'display': 'Let me explain...', 'value': 'custom'},
            ]
        },
        'active': {
            'regex': r'\bactive\b',
            'question': "How do you define 'active' employees?",
            'options_query': "status",  # Search for status columns and values
        },
        'terminated': {
            'regex': r'\bterminated\b',
            'question': "How do you define 'terminated' employees?",
            'options_query': "status",
        },
        'headcount': {
            'regex': r'\bheadcount\b',
            'question': "What should headcount include?",
            'options': [
                {'display': 'Active employees only (status A or L)', 'value': 'active_only'},
                {'display': 'All employees regardless of status', 'value': 'all'},
                {'display': 'Let me explain...', 'value': 'custom'},
            ]
        },
        'by_company': {
            'regex': r'\bby\s+company\b',
            'question': "How should I display company?",
            'options_query': "company",  # Search for company columns
        },
        'by_department': {
            'regex': r'\bby\s+(?:department|dept)\b',
            'question': "How should I display department?",
            'options_query': "department",
        },
    }
    
    def __init__(self, conn=None, project: str = None, vendor: str = None, product: str = None):
        self.conn = conn
        self.project = project
        self.vendor = vendor
        self.product = product
        self._rules_cache = {}
        self._column_cache = {}
        if conn and project:
            self._load_learned_rules()
            self._load_schema_info()
    
    def _load_learned_rules(self):
        """Load previously learned business rules from database.
        
        Cascades: customer-specific → product-level → vendor-level
        """
        try:
            # Check if table exists
            tables = self.conn.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_name = '_business_rules'
            """).fetchall()
            
            if not tables:
                # Create the table with vendor/product columns
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS _business_rules (
                        id INTEGER PRIMARY KEY,
                        project VARCHAR,
                        vendor VARCHAR,
                        product VARCHAR,
                        pattern VARCHAR,
                        description VARCHAR,
                        sql_template VARCHAR,
                        parameters VARCHAR,
                        source_level VARCHAR DEFAULT 'customer',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(project, vendor, product, pattern)
                    )
                """)
                logger.info("[BUSINESS_RULES] Created _business_rules table")
                return
            
            # Check if vendor/product columns exist, add if missing
            try:
                self.conn.execute("SELECT vendor FROM _business_rules LIMIT 1")
            except:
                logger.info("[BUSINESS_RULES] Adding vendor/product columns to _business_rules")
                self.conn.execute("ALTER TABLE _business_rules ADD COLUMN vendor VARCHAR")
                self.conn.execute("ALTER TABLE _business_rules ADD COLUMN product VARCHAR")
                self.conn.execute("ALTER TABLE _business_rules ADD COLUMN source_level VARCHAR DEFAULT 'customer'")
            
            # Load rules with cascade priority: customer > product > vendor
            # We query all applicable rules and take the most specific one per pattern
            results = self.conn.execute("""
                SELECT pattern, description, sql_template, parameters, 
                       CASE 
                           WHEN project = ? THEN 3  -- Customer-specific (highest priority)
                           WHEN project IS NULL AND product = ? THEN 2  -- Product-level
                           WHEN project IS NULL AND product IS NULL AND vendor = ? THEN 1  -- Vendor-level
                           ELSE 0
                       END as priority
                FROM _business_rules
                WHERE (project = ? OR project IS NULL)
                  AND (product = ? OR product IS NULL)
                  AND (vendor = ? OR vendor IS NULL)
                ORDER BY pattern, priority DESC
            """, [self.project, self.product, self.vendor, 
                  self.project, self.product, self.vendor]).fetchall()
            
            # Take highest priority rule per pattern
            seen_patterns = set()
            for pattern, description, sql_template, parameters, priority in results:
                if pattern not in seen_patterns:
                    self._rules_cache[pattern] = BusinessRule(
                        pattern=pattern,
                        description=description,
                        sql_template=sql_template,
                        parameters=json.loads(parameters) if parameters else {},
                        source="learned"
                    )
                    seen_patterns.add(pattern)
            
            logger.warning(f"[BUSINESS_RULES] Loaded {len(self._rules_cache)} rules for project={self.project}, vendor={self.vendor}, product={self.product}")
            
        except Exception as e:
            logger.warning(f"[BUSINESS_RULES] Could not load rules: {e}")
    
    def _load_schema_info(self):
        """Load column info for building dynamic options."""
        try:
            results = self.conn.execute("""
                SELECT table_name, column_name, data_type
                FROM _column_profiles
                WHERE project = ?
            """, [self.project]).fetchall()
            
            for table, column, dtype in results:
                col_lower = column.lower()
                # Categorize columns
                if 'date' in col_lower or dtype in ('DATE', 'TIMESTAMP'):
                    self._column_cache.setdefault('date', []).append((table, column))
                if 'status' in col_lower:
                    self._column_cache.setdefault('status', []).append((table, column))
                if 'company' in col_lower:
                    self._column_cache.setdefault('company', []).append((table, column))
                if 'department' in col_lower or 'dept' in col_lower:
                    self._column_cache.setdefault('department', []).append((table, column))
            
            logger.warning(f"[BUSINESS_RULES] Schema cache: {list(self._column_cache.keys())}")
            
        except Exception as e:
            logger.warning(f"[BUSINESS_RULES] Could not load schema: {e}")
    
    def interpret(self, question: str) -> Tuple[List[BusinessRule], Optional[ClarificationRequest]]:
        """
        Interpret a question using learned rules.
        
        Returns:
            Tuple of (rules_to_apply, clarification_needed)
            - If clarification_needed is not None, ask the user first
            - If rules_to_apply has items, apply them to SQL generation
        """
        q_lower = question.lower()
        rules_to_apply = []
        
        # Detect all patterns in the question
        detected_patterns = []
        for pattern_key, pattern_info in self.DETECTABLE_PATTERNS.items():
            match = re.search(pattern_info['regex'], q_lower)
            if match:
                detected_patterns.append({
                    'key': pattern_key,
                    'match': match,
                    'info': pattern_info
                })
        
        logger.warning(f"[BUSINESS_RULES] Detected patterns: {[p['key'] for p in detected_patterns]}")
        
        # For each detected pattern, check if we have a learned rule
        for detected in detected_patterns:
            pattern_key = detected['key']
            
            if pattern_key in self._rules_cache:
                # We have a learned rule - add it for confirmation
                rule = self._rules_cache[pattern_key]
                rules_to_apply.append(rule)
                logger.warning(f"[BUSINESS_RULES] Found learned rule for '{pattern_key}': {rule.description}")
            else:
                # No rule yet - need to ask
                clarification = self._build_clarification(detected)
                if clarification:
                    logger.warning(f"[BUSINESS_RULES] Need clarification for '{pattern_key}'")
                    return ([], clarification)
        
        return (rules_to_apply, None)
    
    def _build_clarification(self, detected: Dict) -> Optional[ClarificationRequest]:
        """Build a clarification request for an unlearned pattern."""
        pattern_key = detected['key']
        pattern_info = detected['info']
        match = detected['match']
        
        question = pattern_info['question']
        
        # Handle date extraction for as_of pattern
        if pattern_key == 'as_of' and match.groups():
            date_str = match.group(1)
            question = question.format(date=date_str)
        
        # Build options - either static or dynamic from schema
        options = []
        if 'options' in pattern_info:
            options = pattern_info['options']
        elif 'options_query' in pattern_info:
            # Dynamic options from schema
            category = pattern_info['options_query']
            columns = self._column_cache.get(category, [])
            
            for table, column in columns[:5]:  # Max 5 options
                # Make human-readable
                display = self._humanize_column(column)
                options.append({
                    'display': f"{display} (from {table})",
                    'value': f"{table}.{column}",
                    'description': f"Use {column} column"
                })
            
            if not options:
                # No columns found - offer generic options
                options = [
                    {'display': 'Let me explain what I need...', 'value': 'custom'}
                ]
        
        return ClarificationRequest(
            pattern=pattern_key,
            question=question,
            options=options,
            context=f"Pattern: {pattern_key}"
        )
    
    def _humanize_column(self, column: str) -> str:
        """Convert column name to human-readable."""
        # Handle camelCase
        s = re.sub('(.)([A-Z][a-z]+)', r'\1 \2', column)
        s = re.sub('([a-z0-9])([A-Z])', r'\1 \2', s)
        # Handle snake_case
        s = s.replace('_', ' ')
        return s.title()
    
    def save_rule(self, pattern: str, description: str, sql_template: str, parameters: Dict, 
                  level: str = 'customer') -> bool:
        """Save a learned business rule.
        
        Args:
            pattern: Rule pattern key (e.g., 'by_date')
            description: Human-readable description
            sql_template: SQL fragment to apply
            parameters: Parameters dict
            level: Where to save - 'customer', 'product', or 'vendor'
        """
        try:
            # Determine project/vendor/product based on level
            if level == 'customer':
                project_val = self.project
                vendor_val = self.vendor
                product_val = self.product
            elif level == 'product':
                project_val = None  # Applies to all customers with this product
                vendor_val = self.vendor
                product_val = self.product
            elif level == 'vendor':
                project_val = None  # Applies to all customers with this vendor
                vendor_val = self.vendor
                product_val = None
            else:
                project_val = self.project
                vendor_val = self.vendor
                product_val = self.product
            
            self.conn.execute("""
                INSERT INTO _business_rules (project, vendor, product, pattern, description, sql_template, parameters, source_level, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT (project, vendor, product, pattern) DO UPDATE SET
                    description = EXCLUDED.description,
                    sql_template = EXCLUDED.sql_template,
                    parameters = EXCLUDED.parameters,
                    source_level = EXCLUDED.source_level,
                    updated_at = CURRENT_TIMESTAMP
            """, [project_val, vendor_val, product_val, pattern, description, sql_template, json.dumps(parameters), level])
            
            # Update cache
            self._rules_cache[pattern] = BusinessRule(
                pattern=pattern,
                description=description,
                sql_template=sql_template,
                parameters=parameters,
                source="learned"
            )
            
            logger.warning(f"[BUSINESS_RULES] Saved rule at {level} level: {pattern} = {description}")
            return True
            
        except Exception as e:
            logger.error(f"[BUSINESS_RULES] Failed to save rule: {e}")
            return False
    
    def format_interpretation(self, rules: List[BusinessRule], for_confirmation: bool = True) -> str:
        """Format rules as human-readable interpretation."""
        if not rules:
            return ""
        
        if for_confirmation:
            lines = ["Here's how I'll interpret your question:", ""]
        else:
            lines = ["Based on these interpretations:", ""]
        
        for rule in rules:
            lines.append(f"• **{rule.pattern}**: {rule.description}")
        
        if for_confirmation:
            lines.append("")
            lines.append("Should I proceed?")
        
        return "\n".join(lines)
    
    def build_sql_conditions(self, rules: List[BusinessRule], question: str) -> List[str]:
        """Build SQL WHERE conditions from rules."""
        conditions = []
        
        for rule in rules:
            if rule.sql_template:
                # Substitute parameters
                sql = rule.sql_template
                for key, value in rule.parameters.items():
                    sql = sql.replace(f"{{{key}}}", value)
                conditions.append(sql)
        
        return conditions


@dataclass 
class SynthesizedResponse:
    """
    Final response to the user.
    
    Compatible with old SynthesizedAnswer interface for unified_chat.py
    """
    answer: str
    sql: str
    confidence: float
    data_summary: Optional[Dict] = None
    suggestions: List[str] = field(default_factory=list)
    citations: List[str] = field(default_factory=list)
    
    # Clarification fields
    needs_clarification: bool = False
    clarification_question: Optional[str] = None
    clarification_options: List[Dict] = field(default_factory=list)
    clarification_key: Optional[str] = None  # For storing preference after answer
    
    # =========================================================================
    # COMPATIBILITY PROPERTIES (for old code expecting SynthesizedAnswer)
    # =========================================================================
    
    @property
    def question(self) -> str:
        """Compatibility: old code expects .question to echo back the question."""
        return getattr(self, '_question', '')
    
    @question.setter
    def question(self, value: str):
        self._question = value
    
    @property
    def reasoning(self) -> List[str]:
        """Compatibility: old code expects .reasoning list."""
        reasons = []
        if self.sql:
            reasons.append(f"SQL executed: {self.sql[:100]}...")
        if self.data_summary:
            reasons.append(f"Data summary: {self.data_summary}")
        return reasons
    
    @property
    def structured_output(self) -> Optional[Dict]:
        """Compatibility: old code checks structured_output for clarification."""
        # Handle clarification responses
        if self.needs_clarification:
            # Transform options to frontend format: {display, value} -> {id, label}
            frontend_options = []
            for opt in (self.clarification_options or []):
                frontend_options.append({
                    'id': opt.get('value', ''),
                    'label': opt.get('display', ''),
                    'description': opt.get('description', '')
                })
            
            return {
                'type': 'clarification_needed',
                'questions': [{
                    'id': self.clarification_key,  # Frontend uses this as question ID
                    'question': self.clarification_question,
                    'type': 'radio',  # Default to radio buttons
                    'options': frontend_options,
                    'learning_key': self.clarification_key  # Keep for backward compat
                }],
                'detected_domains': ['data']
            }
        # Regular data response
        if self.suggestions:
            return {
                'type': 'data_response',
                'suggestions': self.suggestions,
                'sql': self.sql
            }
        return {'type': 'data_response', 'sql': self.sql}
    
    @property
    def truths(self) -> List:
        """Compatibility: old code expects .truths list."""
        return []
    
    @property
    def conflicts(self) -> List:
        """Compatibility: old code expects .conflicts list."""
        return []
    
    @property
    def insights(self) -> List:
        """Compatibility: old code expects .insights list."""
        return []
    
    @property
    def from_reality(self) -> List:
        """Compatibility: old code expects .from_reality list."""
        return []
    
    @property
    def from_intent(self) -> List:
        """Compatibility: old code expects .from_intent list."""
        return []
    
    @property
    def from_configuration(self) -> List:
        """Compatibility: old code expects .from_configuration list."""
        return []
    
    @property
    def from_reference(self) -> List:
        """Compatibility: old code expects .from_reference list."""
        return []
    
    @property
    def from_regulatory(self) -> List:
        """Compatibility: old code expects .from_regulatory list."""
        return []
    
    @property
    def from_compliance(self) -> List:
        """Compatibility: old code expects .from_compliance list."""
        return []


# =============================================================================
# CONTEXT ASSEMBLER
# =============================================================================

class ContextAssembler:
    """
    Finds relevant tables and assembles schema context for LLM.
    
    Uses existing profiling data from:
    - _schema_metadata: Table-level info
    - _column_profiles: Column details and sample values
    - _column_mappings: Join relationships
    """
    
    # Keywords that suggest which entity types are relevant
    ENTITY_KEYWORDS = {
        'employee': ['employee', 'employees', 'worker', 'workers', 'people', 'person', 'staff', 'headcount'],
        'deduction': ['deduction', 'deductions', 'benefit', 'benefits', '401k', 'medical', 'dental', 'insurance'],
        'earning': ['earning', 'earnings', 'pay', 'salary', 'wage', 'wages', 'compensation', 'bonus'],
        'location': ['location', 'state', 'city', 'office', 'site', 'region'],
        'department': ['department', 'dept', 'division', 'team', 'group', 'org'],
        'job': ['job', 'position', 'title', 'role'],
    }
    
    # Filter value patterns
    FILTER_PATTERNS = {
        'status': ['active', 'terminated', 'inactive', 'leave', 'on leave'],
        'location': [],  # Populated from data
    }
    
    def __init__(self, conn, project: str):
        """
        Args:
            conn: DuckDB connection (from structured_data_handler)
            project: Project ID/name
        """
        self.conn = conn
        self.project = project
        self._table_cache: Dict[str, TableSchema] = {}
        self._join_cache: List[Dict] = []
        self._term_mappings: Dict[str, Dict] = {}  # term_lower -> mapping info
        self._load_term_mappings()
    
    def _load_term_mappings(self):
        """Load term mappings from _term_mappings table."""
        try:
            # Check if table exists
            tables = self.conn.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_name = '_term_mappings'
            """).fetchall()
            
            if not tables:
                logger.info("[CONTEXT] No _term_mappings table found")
                return
            
            # Try to load with source_table column (new schema)
            try:
                mappings = self.conn.execute("""
                    SELECT term, term_lower, source_table, employee_column, lookup_table, 
                           lookup_key_column, lookup_display_column, lookup_filter, mapping_type
                    FROM _term_mappings
                    WHERE project = ?
                """, [self.project]).fetchall()
                
                for row in mappings:
                    term, term_lower, source_tbl, emp_col, lookup_tbl, lookup_key, lookup_disp, lookup_filter, map_type = row
                    self._term_mappings[term_lower] = {
                        'term': term,
                        'source_table': source_tbl,
                        'employee_column': emp_col,
                        'lookup_table': lookup_tbl,
                        'lookup_key_column': lookup_key,
                        'lookup_display_column': lookup_disp,
                        'lookup_filter': lookup_filter,
                        'mapping_type': map_type
                    }
            except Exception as schema_err:
                # Fallback to old schema without source_table
                logger.warning(f"[CONTEXT] Using legacy schema (no source_table): {schema_err}")
                mappings = self.conn.execute("""
                    SELECT term, term_lower, employee_column, lookup_table, 
                           lookup_key_column, lookup_display_column, lookup_filter, mapping_type
                    FROM _term_mappings
                    WHERE project = ?
                """, [self.project]).fetchall()
                
                for row in mappings:
                    term, term_lower, emp_col, lookup_tbl, lookup_key, lookup_disp, lookup_filter, map_type = row
                    self._term_mappings[term_lower] = {
                        'term': term,
                        'source_table': None,  # Will be guessed later
                        'employee_column': emp_col,
                        'lookup_table': lookup_tbl,
                        'lookup_key_column': lookup_key,
                        'lookup_display_column': lookup_disp,
                        'lookup_filter': lookup_filter,
                        'mapping_type': map_type
                    }
            
            if self._term_mappings:
                logger.warning(f"[CONTEXT] Loaded {len(self._term_mappings)} term mappings: {list(self._term_mappings.keys())}")
                for term, mapping in self._term_mappings.items():
                    logger.warning(f"[CONTEXT]   '{term}' -> {mapping.get('source_table', 'UNKNOWN')}.{mapping['employee_column']}")
        except Exception as e:
            logger.warning(f"[CONTEXT] Could not load term mappings: {e}")
        
    def assemble(self, question: str) -> QueryContext:
        """
        Main entry point. Analyzes question and assembles context.
        
        Args:
            question: User's natural language question
            
        Returns:
            QueryContext with all info needed for SQL generation
        """
        logger.warning(f"[CONTEXT] ========== ASSEMBLING CONTEXT ==========")
        logger.warning(f"[CONTEXT] Question: {question}")
        
        # Step 1: Detect intent
        intent = self._detect_intent(question)
        logger.warning(f"[CONTEXT] Detected intent: {intent.value}")
        
        # Step 2: Detect entities mentioned
        entities = self._detect_entities(question)
        logger.warning(f"[CONTEXT] Detected entities: {entities}")
        
        # Step 3: Detect filter values
        filters = self._detect_filters(question)
        logger.warning(f"[CONTEXT] Detected filters: {filters}")
        
        # Step 3.5: Check for term mappings (e.g., "department" -> orgLevel2 with lookup)
        term_mapping_info = self._find_term_mappings(question)
        if term_mapping_info:
            logger.warning(f"[CONTEXT] Found term mappings: {term_mapping_info}")
        
        # Step 4: Find relevant tables
        tables = self._find_relevant_tables(entities, filters, question)
        
        # Step 4.5: Handle term mappings
        # For filter_value mappings (like 'active' -> status column), DON'T replace tables
        # For lookup mappings (like 'department' -> org_levels), add the lookup table
        if term_mapping_info:
            lookup_tables_to_add = []
            filter_column_hints = []  # For LLM context
            
            for mapping in term_mapping_info:
                mapping_type = mapping.get('mapping_type', 'unknown')
                source_table = mapping.get('source_table')
                
                if mapping_type == 'filter_value':
                    # Don't replace tables - just note which column has the filter
                    # The LLM will use the status column from whatever table has it
                    filter_column_hints.append({
                        'term': mapping.get('term'),
                        'column': mapping.get('employee_column'),
                        'table': source_table
                    })
                    logger.warning(f"[CONTEXT] Filter hint: '{mapping.get('term')}' -> {source_table}.{mapping.get('employee_column')}")
                    
                    # If the source table isn't already selected, add it BUT don't remove others
                    if source_table and not any(t.table_name == source_table for t in tables):
                        source_schema = self._get_table_schema(source_table, 0)
                        if source_schema:
                            tables.append(source_schema)
                            logger.warning(f"[CONTEXT] Added filter source table: {source_table}")
                else:
                    # For lookup mappings, add both source and lookup tables
                    if source_table and not any(t.table_name == source_table for t in lookup_tables_to_add):
                        source_schema = self._get_table_schema(source_table, 0)
                        if source_schema:
                            lookup_tables_to_add.append(source_schema)
                            logger.warning(f"[CONTEXT] Term mapping source table: {source_table}")
                    
                    lookup_table = mapping.get('lookup_table')
                    if lookup_table and not any(t.table_name == lookup_table for t in lookup_tables_to_add):
                        lookup_schema = self._get_table_schema(lookup_table, 0)
                        if lookup_schema:
                            lookup_tables_to_add.append(lookup_schema)
                            logger.warning(f"[CONTEXT] Term mapping lookup table: {lookup_table}")
            
            # For lookup mappings, replace tables (focused context for "by department" queries)
            # But ONLY if there are actual lookup tables (not just filter_value mappings)
            if lookup_tables_to_add:
                logger.warning(f"[CONTEXT] Using term mapping tables for lookup query (was {len(tables)} tables, now {len(lookup_tables_to_add)})")
                tables = lookup_tables_to_add
        
        logger.warning(f"[CONTEXT] Final table list ({len(tables)} tables): {[t.table_name for t in tables]}")
        
        # Log table details
        for t in tables:
            logger.warning(f"[CONTEXT]   Table '{t.table_name}': {len(t.columns)} columns, {t.row_count} rows")
            logger.warning(f"[CONTEXT]     Columns: {t.columns[:10]}{'...' if len(t.columns) > 10 else ''}")
            if t.filter_columns:
                logger.warning(f"[CONTEXT]     Filter columns: {t.filter_columns}")
        
        # Step 5: Get join paths between tables
        join_paths = self._find_join_paths([t.table_name for t in tables])
        
        # Step 5.5: Add join paths from term mappings
        if term_mapping_info:
            for mapping in term_mapping_info:
                source_table = mapping.get('source_table')
                
                if not source_table:
                    # Legacy fallback: guess the employee table
                    for t in tables:
                        if 'employee' in t.table_name.lower() or 'person' in t.table_name.lower():
                            source_table = t.table_name
                            break
                    logger.warning(f"[CONTEXT] No source_table in mapping, guessed: {source_table}")
                
                if source_table and mapping.get('lookup_table'):
                    join_path = {
                        'from': f"{source_table}.{mapping['employee_column']}",
                        'to': f"{mapping['lookup_table']}.{mapping['lookup_key_column']}",
                        'type': 'term_mapping',
                        'display_column': mapping.get('lookup_display_column'),
                        'filter': mapping.get('lookup_filter'),
                        'term': mapping.get('term')
                    }
                    join_paths.append(join_path)
                    logger.warning(f"[CONTEXT] Added term mapping join: {join_path}")
        
        logger.warning(f"[CONTEXT] Found {len(join_paths)} join paths: {join_paths}")
        logger.warning(f"[CONTEXT] ========== CONTEXT COMPLETE ==========")
        
        return QueryContext(
            question=question,
            tables=tables,
            join_paths=join_paths,
            detected_intent=intent,
            detected_entities=entities,
            detected_filters=filters
        )
    
    def _find_term_mappings(self, question: str) -> List[Dict]:
        """Find any term mappings that apply to this question."""
        if not self._term_mappings:
            return []
        
        q_lower = question.lower()
        found = []
        
        for term_lower, mapping in self._term_mappings.items():
            if term_lower in q_lower:
                found.append(mapping)
                logger.warning(f"[CONTEXT] Matched term mapping: '{term_lower}' -> {mapping['employee_column']}")
        
        return found
    
    def _detect_intent(self, question: str) -> QueryIntent:
        """Detect what the user wants to do."""
        q = question.lower()
        
        # Count patterns
        if any(p in q for p in ['how many', 'count', 'total number', 'headcount']):
            return QueryIntent.COUNT
            
        # Aggregate patterns
        if any(p in q for p in ['average', 'avg', 'sum', 'total', 'minimum', 'min', 'maximum', 'max']):
            return QueryIntent.AGGREGATE
            
        # Compare/group patterns
        if any(p in q for p in [' by ', ' per ', ' for each ', ' grouped by', ' broken down']):
            return QueryIntent.COMPARE
            
        # List patterns
        if any(p in q for p in ['list', 'show', 'display', 'give me', 'what are', 'who are', 'which']):
            return QueryIntent.LIST
            
        # Lookup patterns (specific)
        if any(p in q for p in ['find', 'look up', 'search for', 'where is']):
            return QueryIntent.LOOKUP
            
        return QueryIntent.GENERAL
    
    def _detect_entities(self, question: str) -> List[str]:
        """Detect which entity types are mentioned."""
        q = question.lower()
        entities = []
        
        for entity, keywords in self.ENTITY_KEYWORDS.items():
            if any(kw in q for kw in keywords):
                entities.append(entity)
        
        # Default to employee if nothing detected but seems like a data question
        if not entities and any(w in q for w in ['how many', 'list', 'show', 'count']):
            entities = ['employee']
            
        return entities
    
    def _detect_filters(self, question: str) -> Dict[str, str]:
        """Detect filter values mentioned in the question."""
        filters = {}
        q = question.lower()
        
        # Status filters
        if 'active' in q and 'inactive' not in q:
            filters['status'] = 'active'
        elif 'terminated' in q or 'termed' in q:
            filters['status'] = 'terminated'
        elif 'inactive' in q:
            filters['status'] = 'inactive'
            
        # State filters - look for state names
        state_pattern = r'\b(alabama|alaska|arizona|arkansas|california|colorado|connecticut|delaware|florida|georgia|hawaii|idaho|illinois|indiana|iowa|kansas|kentucky|louisiana|maine|maryland|massachusetts|michigan|minnesota|mississippi|missouri|montana|nebraska|nevada|new hampshire|new jersey|new mexico|new york|north carolina|north dakota|ohio|oklahoma|oregon|pennsylvania|rhode island|south carolina|south dakota|tennessee|texas|utah|vermont|virginia|washington|west virginia|wisconsin|wyoming)\b'
        state_match = re.search(state_pattern, q)
        if state_match:
            filters['state'] = state_match.group(1).title()
        
        # Year filters
        year_match = re.search(r'\b(20\d{2})\b', question)
        if year_match:
            filters['year'] = year_match.group(1)
            
        return filters
    
    def _find_relevant_tables(self, entities: List[str], filters: Dict[str, str], question: str = "") -> List[TableSchema]:
        """Find tables that match the detected entities and filters."""
        tables = []
        
        # VERSION MARKER: v2024.01.24.5 - STRPTIME for date parsing
        logger.warning(f"[CONTEXT] _find_relevant_tables v2024.01.24.5 - question='{question[:50]}...'")
        
        try:
            # Get all tables for this project
            result = self.conn.execute("""
                SELECT DISTINCT table_name, entity_type, row_count
                FROM _schema_metadata
                WHERE LOWER(project) = LOWER(?)
                  AND is_current = TRUE
            """, [self.project]).fetchall()
            
            all_tables = {row[0]: {'entity_type': row[1], 'row_count': row[2]} for row in result}
            logger.warning(f"[CONTEXT] Project '{self.project}' has {len(all_tables)} tables")
            logger.warning(f"[CONTEXT] All tables: {list(all_tables.keys())}")
            
            if not all_tables:
                logger.error(f"[CONTEXT] NO TABLES FOUND for project '{self.project}'")
                return tables
            
            # Score tables by relevance to entities
            scored_tables = []
            for table_name, info in all_tables.items():
                score = 0
                table_lower = table_name.lower()
                entity_type = (info['entity_type'] or '').lower()
                
                for entity in entities:
                    # Direct name match
                    if entity in table_lower:
                        score += 10
                    # Entity type match
                    if entity in entity_type:
                        score += 8
                    # Partial match
                    if any(kw in table_lower for kw in self.ENTITY_KEYWORDS.get(entity, [])):
                        score += 5
                
                # Boost tables that might have filter columns
                if filters:
                    filter_cols = self._get_filter_columns(table_name)
                    for filter_key in filters:
                        if filter_key in [fc.lower() for fc in filter_cols]:
                            score += 3
                
                # TEMPORAL/PIT QUERY HANDLING
                # For queries about "active", "hired", "terminated" + a date, we NEED hire/term date columns
                q_lower = question.lower()
                is_pit_query = (
                    ('active' in q_lower and filters.get('year')) or
                    'headcount' in q_lower or
                    ('hired' in q_lower and ('in' in q_lower or 'during' in q_lower or filters.get('year'))) or
                    ('terminated' in q_lower and ('in' in q_lower or 'during' in q_lower or filters.get('year')))
                )
                
                if is_pit_query:
                    hire_term_cols = self._get_hire_term_columns(table_name)
                    if hire_term_cols:
                        # Tables with hire/term columns get MASSIVE boost for PIT queries
                        score += 50
                        logger.warning(f"[CONTEXT]   PIT BOOST +50 for '{table_name}': has {hire_term_cols}")
                    elif 'employment' in table_lower or 'employee_change' in table_lower:
                        # Employment tables get strong boost even without exact column match
                        score += 30
                        logger.warning(f"[CONTEXT]   EMPLOYMENT TABLE BOOST +30 for '{table_name}'")
                    else:
                        # Other tables get PENALIZED for PIT queries - we don't want compensation_details
                        score -= 20
                        logger.warning(f"[CONTEXT]   PIT PENALTY -20 for '{table_name}': no hire/term columns")
                
                if score > 0:
                    scored_tables.append((table_name, score, info['row_count']))
                    logger.warning(f"[CONTEXT]   Scored '{table_name}': {score} points")
            
            if not scored_tables:
                logger.warning(f"[CONTEXT] No tables matched entities {entities}. Taking first 3 tables as fallback.")
                # Take first 3 tables if nothing matched
                for table_name, info in list(all_tables.items())[:3]:
                    scored_tables.append((table_name, 1, info['row_count']))
            
            # Sort by score and take top tables
            scored_tables.sort(key=lambda x: x[1], reverse=True)
            top_tables = scored_tables[:5]  # Max 5 tables for context
            
            logger.warning(f"[CONTEXT] Selected tables: {[(t[0], t[1]) for t in top_tables]}")
            
            # Build full schemas for selected tables
            for table_name, score, row_count in top_tables:
                schema = self._get_table_schema(table_name, row_count or 0)
                if schema:
                    tables.append(schema)
                    
        except Exception as e:
            logger.error(f"[CONTEXT] Error finding tables: {e}")
            logger.error(traceback.format_exc())
            
        return tables
    
    def _get_filter_columns(self, table_name: str) -> List[str]:
        """Get columns that have filter_category set."""
        try:
            result = self.conn.execute("""
                SELECT column_name, filter_category
                FROM _column_profiles
                WHERE LOWER(project) = LOWER(?)
                  AND table_name = ?
                  AND filter_category IS NOT NULL
            """, [self.project, table_name]).fetchall()
            return [row[0] for row in result]
        except:
            return []
    
    def _get_date_columns(self, table_name: str) -> List[str]:
        """Get columns that look like date columns by name pattern."""
        try:
            result = self.conn.execute("""
                SELECT column_name
                FROM _column_profiles
                WHERE LOWER(project) = LOWER(?)
                  AND table_name = ?
                  AND (
                    LOWER(column_name) LIKE '%date%'
                    OR LOWER(column_name) LIKE '%hire%'
                    OR LOWER(column_name) LIKE '%term%'
                    OR LOWER(column_name) LIKE '%effective%'
                    OR LOWER(column_name) LIKE '%start%'
                    OR LOWER(column_name) LIKE '%end%'
                  )
            """, [self.project, table_name]).fetchall()
            return [row[0] for row in result]
        except:
            return []
    
    def _get_hire_term_columns(self, table_name: str) -> List[str]:
        """Get columns specifically for hire/termination dates (for PIT queries)."""
        try:
            result = self.conn.execute("""
                SELECT column_name
                FROM _column_profiles
                WHERE LOWER(project) = LOWER(?)
                  AND table_name = ?
                  AND (
                    LOWER(column_name) LIKE '%hire%date%'
                    OR LOWER(column_name) LIKE '%hiredate%'
                    OR LOWER(column_name) LIKE '%term%date%'
                    OR LOWER(column_name) LIKE '%terminationdate%'
                    OR LOWER(column_name) LIKE '%dateofterm%'
                    OR LOWER(column_name) LIKE '%separation%date%'
                  )
            """, [self.project, table_name]).fetchall()
            return [row[0] for row in result]
        except:
            return []
    
    def _get_table_schema(self, table_name: str, row_count: int) -> Optional[TableSchema]:
        """Get full schema for a table."""
        if table_name in self._table_cache:
            return self._table_cache[table_name]
            
        try:
            # Get column profiles
            result = self.conn.execute("""
                SELECT 
                    column_name,
                    inferred_type,
                    distinct_values,
                    sample_values,
                    filter_category
                FROM _column_profiles
                WHERE LOWER(project) = LOWER(?)
                  AND table_name = ?
            """, [self.project, table_name]).fetchall()
            
            if not result:
                # Fall back to DESCRIBE
                result = self.conn.execute(f'DESCRIBE "{table_name}"').fetchall()
                columns = [r[0] for r in result]
                column_types = {r[0]: r[1] for r in result}
                sample_values = {}
                filter_columns = {}
            else:
                columns = [r[0] for r in result]
                column_types = {r[0]: r[1] or 'VARCHAR' for r in result}
                sample_values = {}
                filter_columns = {}
                
                for row in result:
                    col_name, inferred_type, distinct_vals, sample_vals, filter_cat = row
                    
                    # Parse sample values
                    if sample_vals:
                        try:
                            if isinstance(sample_vals, str):
                                sample_values[col_name] = json.loads(sample_vals)[:5]
                            else:
                                sample_values[col_name] = list(sample_vals)[:5]
                        except:
                            pass
                    
                    # Parse distinct values for low-cardinality columns
                    if distinct_vals and not sample_values.get(col_name):
                        try:
                            if isinstance(distinct_vals, str):
                                sample_values[col_name] = json.loads(distinct_vals)[:5]
                            else:
                                sample_values[col_name] = list(distinct_vals)[:5]
                        except:
                            pass
                    
                    if filter_cat:
                        filter_columns[col_name] = filter_cat
            
            schema = TableSchema(
                table_name=table_name,
                columns=columns,
                column_types=column_types,
                sample_values=sample_values,
                row_count=row_count,
                filter_columns=filter_columns
            )
            
            self._table_cache[table_name] = schema
            return schema
            
        except Exception as e:
            logger.error(f"[CONTEXT] Error getting schema for {table_name}: {e}")
            return None
    
    def _find_join_paths(self, table_names: List[str]) -> List[Dict[str, str]]:
        """Find join paths between the selected tables."""
        if len(table_names) < 2:
            return []
            
        join_paths = []
        
        try:
            # Look for hub-spoke relationships in _column_mappings
            for table in table_names:
                result = self.conn.execute("""
                    SELECT 
                        table_name,
                        original_column,
                        hub_table,
                        hub_column,
                        semantic_type
                    FROM _column_mappings
                    WHERE LOWER(project) = LOWER(?)
                      AND table_name = ?
                      AND hub_table IS NOT NULL
                """, [self.project, table]).fetchall()
                
                for row in result:
                    spoke_table, spoke_col, hub_table, hub_col, sem_type = row
                    
                    # Only include if hub table is in our selected tables
                    if hub_table in table_names:
                        join_paths.append({
                            'from': f"{spoke_table}.{spoke_col}",
                            'to': f"{hub_table}.{hub_col}",
                            'type': sem_type or 'unknown'
                        })
            
            # Also check for common column names between tables (fallback)
            if not join_paths:
                common_keys = ['employee_number', 'employee_id', 'emp_id', 'id', 'code']
                for i, t1 in enumerate(table_names):
                    for t2 in table_names[i+1:]:
                        schema1 = self._table_cache.get(t1)
                        schema2 = self._table_cache.get(t2)
                        
                        if schema1 and schema2:
                            common = set(c.lower() for c in schema1.columns) & set(c.lower() for c in schema2.columns)
                            for col in common:
                                if any(k in col for k in common_keys):
                                    # Find actual column names (case-sensitive)
                                    col1 = next((c for c in schema1.columns if c.lower() == col), col)
                                    col2 = next((c for c in schema2.columns if c.lower() == col), col)
                                    join_paths.append({
                                        'from': f"{t1}.{col1}",
                                        'to': f"{t2}.{col2}",
                                        'type': 'inferred'
                                    })
                                    break  # One join per table pair
                                    
        except Exception as e:
            logger.error(f"[CONTEXT] Error finding join paths: {e}")
            
        return join_paths


# =============================================================================
# SQL GENERATOR
# =============================================================================

class SQLGenerator:
    """
    Generates SQL by prompting an LLM with schema context.
    
    NO FALLBACK. If LLM fails, we fail. Period.
    
    The LLM is GOOD at writing SQL when you tell it exactly what's available.
    We just need to give it the right context.
    """
    
    def __init__(self, llm_orchestrator=None):
        """
        Args:
            llm_orchestrator: LLM caller (from utils/llm_orchestrator.py)
        """
        self.llm = llm_orchestrator
        
    def generate(self, context: QueryContext, intent_context: str = "") -> Tuple[str, Optional[str]]:
        """
        Generate SQL for the given context.
        
        NO FALLBACK. Returns (sql, error) tuple.
        
        Args:
            context: QueryContext with tables, schemas, joins
            intent_context: Optional resolved intent context from IntentEngine
            
        Returns:
            Tuple of (sql_string, error_message)
            - Success: ("SELECT ...", None)
            - Failure: ("", "Error description")
        """
        logger.warning(f"[SQL_GEN] ========== GENERATING SQL ==========")
        logger.warning(f"[SQL_GEN] Intent: {context.detected_intent.value}")
        logger.warning(f"[SQL_GEN] Tables: {[t.table_name for t in context.tables]}")
        logger.warning(f"[SQL_GEN] Filters: {context.detected_filters}")
        logger.warning(f"[SQL_GEN] Joins: {context.join_paths}")
        if intent_context:
            logger.warning(f"[SQL_GEN] Intent context provided: {len(intent_context)} chars")
        
        # NEW: Check for deterministic SQL template first
        deterministic_sql = self._get_deterministic_sql(context, intent_context)
        if deterministic_sql:
            logger.warning(f"[SQL_GEN] USING DETERMINISTIC SQL (bypassing LLM)")
            logger.warning(f"[SQL_GEN] SQL: {deterministic_sql}")
            return deterministic_sql, None
        
        if not self.llm:
            error = "NO LLM CONFIGURED. Cannot generate SQL without LLM."
            logger.error(f"[SQL_GEN] FAILURE: {error}")
            return "", error
        
        prompt = self._build_prompt(context, intent_context=intent_context)
        logger.warning(f"[SQL_GEN] Prompt length: {len(prompt)} chars")
        
        # Log the actual prompt for debugging
        logger.warning(f"[SQL_GEN] ===== PROMPT START =====")
        for line in prompt.split('\n')[:50]:  # First 50 lines
            logger.warning(f"[SQL_GEN] {line}")
        if prompt.count('\n') > 50:
            logger.warning(f"[SQL_GEN] ... ({prompt.count(chr(10)) - 50} more lines)")
        logger.warning(f"[SQL_GEN] ===== PROMPT END =====")
        
        try:
            # Call LLM - use generate_sql which returns {'sql': ..., 'success': ...}
            logger.warning(f"[SQL_GEN] Calling LLM.generate_sql()...")
            result = self.llm.generate_sql(prompt)
            
            logger.warning(f"[SQL_GEN] LLM result: {result}")
            
            success = result.get('success', False)
            sql_response = result.get('sql', '')
            error_msg = result.get('error', '')
            
            if not success:
                error = f"LLM generate_sql failed: {error_msg}"
                logger.error(f"[SQL_GEN] FAILURE: {error}")
                return "", error
            
            if not sql_response:
                error = "LLM returned empty SQL"
                logger.error(f"[SQL_GEN] FAILURE: {error}")
                return "", error
            
            sql = self._clean_sql(sql_response)
            
            if not sql:
                error = f"Could not extract SQL from LLM response: {sql_response[:200]}"
                logger.error(f"[SQL_GEN] FAILURE: {error}")
                return "", error
            
            # Ensure table names are properly quoted (safety net)
            table_names = [t.table_name for t in context.tables]
            sql = self._ensure_quoted_identifiers(sql, table_names)
            
            logger.warning(f"[SQL_GEN] SUCCESS: {sql}")
            return sql, None
            
        except Exception as e:
            error = f"LLM exception: {str(e)}"
            logger.error(f"[SQL_GEN] FAILURE: {error}")
            logger.error(traceback.format_exc())
            return "", error
    
    def _get_deterministic_sql(self, context: QueryContext, intent_context: str) -> Optional[str]:
        """
        Generate deterministic SQL for well-defined query patterns.
        
        Returns SQL string if pattern is recognized, None otherwise (will fall back to LLM).
        """
        if not intent_context:
            logger.warning(f"[SQL_GEN] DETERMINISTIC: No intent_context, skipping")
            return None
        
        # Collect all columns across tables
        all_columns = {}
        for table in context.tables:
            for col in table.columns:
                col_lower = col.lower()
                all_columns[col_lower] = (table.table_name, col)
        
        logger.warning(f"[SQL_GEN] DETERMINISTIC: Checking patterns in intent_context")
        logger.warning(f"[SQL_GEN] DETERMINISTIC: pit_logic={('pit_logic' in intent_context)}, active_on_date={('active_on_date' in intent_context)}")
        
        # Point-in-time headcount query
        if "pit_logic" in intent_context and "active_on_date" in intent_context:
            import re
            date_match = re.search(r'as_of_date[\'"]?\s*[:=]\s*[\'"]?(\d{4}-\d{2}-\d{2})', intent_context)
            as_of_date = date_match.group(1) if date_match else None
            
            if not as_of_date:
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', intent_context)
                as_of_date = date_match.group(1) if date_match else None
            
            logger.warning(f"[SQL_GEN] DETERMINISTIC: Extracted as_of_date={as_of_date}")
            
            if as_of_date:
                # Find columns
                hire_cols = [c for c in all_columns.keys() if 'hire' in c and ('date' in c or 'dt' in c)]
                term_cols = [c for c in all_columns.keys() if ('term' in c or 'separation' in c) and ('date' in c or 'dt' in c)]
                status_cols = [c for c in all_columns.keys() if 'status' in c and 'empl' in c]
                if not status_cols:
                    status_cols = [c for c in all_columns.keys() if 'employeestatus' in c]
                
                logger.warning(f"[SQL_GEN] DETERMINISTIC: hire_cols={hire_cols[:3] if hire_cols else 'NONE'}")
                logger.warning(f"[SQL_GEN] DETERMINISTIC: term_cols={term_cols[:3] if term_cols else 'NONE'}")
                logger.warning(f"[SQL_GEN] DETERMINISTIC: status_cols={status_cols[:3] if status_cols else 'NONE'}")
                
                hire_table = hire_col = term_table = term_col = status_table = status_col = None
                
                if hire_cols:
                    hire_table, hire_col = all_columns[hire_cols[0]]
                    logger.warning(f"[SQL_GEN] DETERMINISTIC: hire_col={hire_col} in table={hire_table}")
                if term_cols:
                    term_table, term_col = all_columns[term_cols[0]]
                    logger.warning(f"[SQL_GEN] DETERMINISTIC: term_col={term_col} in table={term_table}")
                if status_cols:
                    status_table, status_col = all_columns[status_cols[0]]
                    logger.warning(f"[SQL_GEN] DETERMINISTIC: status_col={status_col} in table={status_table}")
                
                # Build SQL based on available columns
                # Use TRY_STRPTIME for flexible date parsing (handles M/D/YYYY H:MM:SS AM format)
                if hire_table:
                    # Case 1: Same table has hire and term (or status)
                    if term_table == hire_table:
                        return f'''SELECT COUNT(DISTINCT "employeeId") AS headcount
FROM "{hire_table}"
WHERE COALESCE(TRY_STRPTIME("{hire_col}", '%m/%d/%Y %I:%M:%S %p')::DATE, TRY_CAST("{hire_col}" AS DATE)) <= '{as_of_date}'
  AND ("{term_col}" IS NULL OR TRIM("{term_col}") = '' OR COALESCE(TRY_STRPTIME("{term_col}", '%m/%d/%Y %I:%M:%S %p')::DATE, TRY_CAST("{term_col}" AS DATE)) > '{as_of_date}')'''
                    
                    elif status_table == hire_table:
                        return f'''SELECT COUNT(DISTINCT "employeeId") AS headcount
FROM "{hire_table}"
WHERE COALESCE(TRY_STRPTIME("{hire_col}", '%m/%d/%Y %I:%M:%S %p')::DATE, TRY_CAST("{hire_col}" AS DATE)) <= '{as_of_date}'
  AND "{status_col}" IN ('A', 'L')'''
                    
                    # Case 2: Need JOIN for term date
                    elif term_table:
                        return f'''SELECT COUNT(DISTINCT h."employeeId") AS headcount
FROM "{hire_table}" AS h
JOIN "{term_table}" AS t ON h."employeeId" = t."employeeId"
WHERE COALESCE(TRY_STRPTIME(h."{hire_col}", '%m/%d/%Y %I:%M:%S %p')::DATE, TRY_CAST(h."{hire_col}" AS DATE)) <= '{as_of_date}'
  AND (t."{term_col}" IS NULL OR TRIM(t."{term_col}") = '' OR COALESCE(TRY_STRPTIME(t."{term_col}", '%m/%d/%Y %I:%M:%S %p')::DATE, TRY_CAST(t."{term_col}" AS DATE)) > '{as_of_date}')'''
                    
                    # Case 3: Need JOIN for status
                    elif status_table:
                        return f'''SELECT COUNT(DISTINCT h."employeeId") AS headcount
FROM "{hire_table}" AS h
JOIN "{status_table}" AS s ON h."employeeId" = s."employeeId"
WHERE COALESCE(TRY_STRPTIME(h."{hire_col}", '%m/%d/%Y %I:%M:%S %p')::DATE, TRY_CAST(h."{hire_col}" AS DATE)) <= '{as_of_date}'
  AND s."{status_col}" IN ('A', 'L')'''
                    
                    # Case 4: Just hire date, no term/status filter
                    else:
                        return f'''SELECT COUNT(DISTINCT "employeeId") AS headcount
FROM "{hire_table}"
WHERE CAST("{hire_col}" AS DATE) <= '{as_of_date}\''''
        
        # Hired by date query
        if "pit_logic" in intent_context and "hired_by_date" in intent_context:
            import re
            date_match = re.search(r'as_of_date[\'"]?\s*[:=]\s*[\'"]?(\d{4}-\d{2}-\d{2})', intent_context)
            as_of_date = date_match.group(1) if date_match else None
            
            if as_of_date:
                hire_cols = [c for c in all_columns.keys() if 'hire' in c and ('date' in c or 'dt' in c)]
                if hire_cols:
                    hire_table, hire_col = all_columns[hire_cols[0]]
                    return f'''SELECT COUNT(DISTINCT "employeeId") AS count
FROM "{hire_table}"
WHERE CAST("{hire_col}" AS DATE) <= '{as_of_date}\''''
        
        return None
    
    def _map_intent_to_columns(self, intent_context: str, tables: List[TableSchema]) -> str:
        """
        Map abstract intent parameters to actual column names in schema.
        
        Returns explicit SQL instructions based on intent + available columns.
        
        Priority:
        1. Use specific column if already clarified (hire_date_column, term_date_column)
        2. Fall back to searching schema for matching columns
        """
        if not intent_context:
            return ""
        
        instructions = []
        
        # Collect all columns across tables
        all_columns = {}
        for table in tables:
            for col in table.columns:
                col_lower = col.lower()
                all_columns[col_lower] = (table.table_name, col)
        
        # Helper to get short table alias
        def get_short_name(table_name: str) -> str:
            # Extract meaningful part after UUID prefix
            parts = table_name.split('_')
            if len(parts) > 2:
                return '_'.join(parts[-3:])  # e.g., "api_employee_job_history"
            return table_name
        
        # Helper to extract specific column from intent context
        def extract_specific_column(column_key: str) -> Optional[Tuple[str, str]]:
            """Extract table.column from intent context if specified."""
            import re
            # Look for pattern like: hire_date_column: Use column "hireDate" from table "..."
            pattern = rf'{column_key}:.*?"([^"]+)".*?table\s+"([^"]+)"'
            match = re.search(pattern, intent_context)
            if match:
                col_name, table_name = match.group(1), match.group(2)
                return (table_name, col_name)
            
            # Also try simpler format: hire_date_column: table.column
            pattern2 = rf'{column_key}:\s*([^\s,\n]+\.[^\s,\n]+)'
            match2 = re.search(pattern2, intent_context)
            if match2:
                full_ref = match2.group(1)
                if '.' in full_ref:
                    parts = full_ref.rsplit('.', 1)
                    return (parts[0], parts[1])
            
            return None
        
        # Detect time_grouping from intent
        time_grouping = "year"  # default
        if "time_grouping: month" in intent_context:
            time_grouping = "month"
        elif "time_grouping: quarter" in intent_context:
            time_grouping = "quarter"
        elif "time_grouping: year" in intent_context:
            time_grouping = "year"
        
        # Helper to build grouping instructions
        def build_time_grouping_instructions(table_name: str, col_name: str, short_name: str) -> List[str]:
            """Build SQL instructions for time-based grouping."""
            instr = []
            # Note: Cast to DATE in case column is stored as VARCHAR
            if time_grouping == "year":
                instr.append(f'EXTRACT YEAR from the date: SELECT EXTRACT(YEAR FROM CAST("{col_name}" AS DATE)) AS year')
                instr.append(f'GROUP BY EXTRACT(YEAR FROM CAST("{col_name}" AS DATE))')
                instr.append(f'ORDER BY year')
            elif time_grouping == "month":
                instr.append(f'EXTRACT YEAR and MONTH: SELECT EXTRACT(YEAR FROM CAST("{col_name}" AS DATE)) AS year, EXTRACT(MONTH FROM CAST("{col_name}" AS DATE)) AS month')
                instr.append(f'GROUP BY EXTRACT(YEAR FROM CAST("{col_name}" AS DATE)), EXTRACT(MONTH FROM CAST("{col_name}" AS DATE))')
                instr.append(f'ORDER BY year, month')
            elif time_grouping == "quarter":
                instr.append(f'EXTRACT YEAR and QUARTER: SELECT EXTRACT(YEAR FROM CAST("{col_name}" AS DATE)) AS year, EXTRACT(QUARTER FROM CAST("{col_name}" AS DATE)) AS quarter')
                instr.append(f'GROUP BY EXTRACT(YEAR FROM CAST("{col_name}" AS DATE)), EXTRACT(QUARTER FROM CAST("{col_name}" AS DATE))')
                instr.append(f'ORDER BY year, quarter')
            instr.append(f'IMPORTANT: Always CAST date columns to DATE type - they may be stored as VARCHAR')
            instr.append(f'DO NOT group by the raw date - that creates thousands of useless groups')
            return instr
        
        # Check for specific hire date column from clarification
        specific_hire = extract_specific_column("hire_date_column")
        specific_term = extract_specific_column("term_date_column")
        
        # Map time_dimension to actual date columns
        if "time_dimension: hire_date" in intent_context or "time_dimension: hire" in intent_context:
            if specific_hire:
                # Use the clarified column
                table_name, col_name = specific_hire
                short_name = get_short_name(table_name)
                instructions.append(f'SPECIFIC COLUMN SELECTED: Use "{col_name}" from table "{table_name}" ({short_name})')
                instructions.extend(build_time_grouping_instructions(table_name, col_name, short_name))
                instructions.append(f'The column "{col_name}" is ONLY in {short_name} - use proper table alias')
            else:
                # Fall back to searching
                hire_cols = [c for c in all_columns.keys() if 'hire' in c and 'date' in c]
                if not hire_cols:
                    hire_cols = [c for c in all_columns.keys() if 'hire' in c]
                if hire_cols:
                    table_name, col_name = all_columns[hire_cols[0]]
                    short_name = get_short_name(table_name)
                    instructions.append(f'The hire date column is "{col_name}" in table "{table_name}" ({short_name})')
                    instructions.extend(build_time_grouping_instructions(table_name, col_name, short_name))
                    instructions.append(f'The column "{col_name}" is ONLY in {short_name} - use proper table alias')
        
        elif "time_dimension: term_date" in intent_context or "time_dimension: term" in intent_context:
            if specific_term:
                # Use the clarified column
                table_name, col_name = specific_term
                short_name = get_short_name(table_name)
                instructions.append(f'SPECIFIC COLUMN SELECTED: Use "{col_name}" from table "{table_name}" ({short_name})')
                instructions.extend(build_time_grouping_instructions(table_name, col_name, short_name))
                instructions.append(f'The column "{col_name}" is ONLY in {short_name} - use proper table alias')
                instructions.append(f'Only include rows WHERE "{col_name}" IS NOT NULL')
            else:
                # Fall back to searching
                term_cols = [c for c in all_columns.keys() if ('term' in c or 'separation' in c) and 'date' in c]
                if not term_cols:
                    term_cols = [c for c in all_columns.keys() if 'term' in c or 'separation' in c]
                if term_cols:
                    table_name, col_name = all_columns[term_cols[0]]
                    short_name = get_short_name(table_name)
                    instructions.append(f'The termination date column is "{col_name}" in table "{table_name}" ({short_name})')
                    instructions.extend(build_time_grouping_instructions(table_name, col_name, short_name))
                    instructions.append(f'The column "{col_name}" is ONLY in {short_name} - use proper table alias')
                    instructions.append(f'Only include rows WHERE "{col_name}" IS NOT NULL')
        
        # Map status filters to actual column
        if "status_filter" in intent_context:
            status_cols = [c for c in all_columns.keys() if 'status' in c and 'employee' not in c]
            if not status_cols:
                status_cols = [c for c in all_columns.keys() if 'status' in c]
            if status_cols:
                table_name, col_name = all_columns[status_cols[0]]
                short_name = get_short_name(table_name)
                # Extract the filter values from intent
                import re
                match = re.search(r"status_filter['\"]?\s*[:=]\s*\[([^\]]+)\]", intent_context)
                if match:
                    values = match.group(1).replace("'", "").replace('"', '').split(',')
                    values = [v.strip() for v in values]
                    if len(values) == 1:
                        instructions.append(f'Filter WHERE "{table_name}"."{col_name}" = \'{values[0]}\' (column is in {short_name})')
                    else:
                        vals_str = ", ".join(f"'{v}'" for v in values)
                        instructions.append(f'Filter WHERE "{table_name}"."{col_name}" IN ({vals_str}) (column is in {short_name})')
        
        # Handle point-in-time logic - ONLY if we find actual columns
        if "pit_logic" in intent_context:
            # Extract the date from intent params
            import re
            date_match = re.search(r'as_of_date[\'"]?\s*[:=]\s*[\'"]?(\d{4}-\d{2}-\d{2})', intent_context)
            as_of_date = date_match.group(1) if date_match else None
            
            if not as_of_date:
                # Try alternate formats
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', intent_context)
                as_of_date = date_match.group(1) if date_match else None
            
            # Find hire date columns - be flexible about naming
            hire_cols = [c for c in all_columns.keys() if 'hire' in c and ('date' in c or 'dt' in c)]
            if not hire_cols:
                hire_cols = [c for c in all_columns.keys() if 'hire' in c]
            
            # Find termination date columns
            term_cols = [c for c in all_columns.keys() if ('term' in c or 'separation' in c) and ('date' in c or 'dt' in c)]
            
            # Find status column for fallback
            status_cols = [c for c in all_columns.keys() if 'status' in c and 'empl' in c]
            if not status_cols:
                status_cols = [c for c in all_columns.keys() if 'employeestatus' in c]
            
            if "active_on_date" in intent_context and as_of_date:
                instructions.append(f'=== POINT-IN-TIME HEADCOUNT AS OF {as_of_date} ===')
                
                hire_table = hire_col = term_table = term_col = status_table = status_col = None
                
                if hire_cols:
                    hire_table, hire_col = all_columns[hire_cols[0]]
                    instructions.append(f'HIRE DATE: "{hire_col}" in table "{hire_table}"')
                
                if term_cols:
                    term_table, term_col = all_columns[term_cols[0]]
                    instructions.append(f'TERM DATE: "{term_col}" in table "{term_table}"')
                elif status_cols:
                    status_table, status_col = all_columns[status_cols[0]]
                    instructions.append(f'STATUS (no term date found): "{status_col}" in table "{status_table}"')
                
                # Build SQL based on where columns are
                if hire_table and (term_table == hire_table or status_table == hire_table or (not term_table and not status_table)):
                    # All needed columns are in the same table - simple query
                    from_table = hire_table
                    where_parts = [f'CAST("{hire_col}" AS DATE) <= \'{as_of_date}\'']
                    if term_col and term_table == hire_table:
                        where_parts.append(f'("{term_col}" IS NULL OR CAST("{term_col}" AS DATE) > \'{as_of_date}\')')
                    elif status_col and status_table == hire_table:
                        where_parts.append(f'"{status_col}" IN (\'A\', \'L\')')
                    
                    complete_sql = f'''SELECT COUNT(DISTINCT "employeeId") AS headcount
FROM "{from_table}"
WHERE {" AND ".join(where_parts)}'''
                    
                    instructions.append(f'\n*** COMPLETE SQL - USE EXACTLY AS SHOWN: ***')
                    instructions.append(complete_sql)
                    instructions.append(f'*** END SQL ***\n')
                    
                elif hire_table and term_table and term_table != hire_table:
                    # Columns in different tables - need JOIN
                    complete_sql = f'''SELECT COUNT(DISTINCT h."employeeId") AS headcount
FROM "{hire_table}" AS h
JOIN "{term_table}" AS t ON h."employeeId" = t."employeeId"
WHERE CAST(h."{hire_col}" AS DATE) <= '{as_of_date}'
  AND (t."{term_col}" IS NULL OR CAST(t."{term_col}" AS DATE) > '{as_of_date}')'''
                    
                    instructions.append(f'\n*** COMPLETE SQL (with JOIN) - USE EXACTLY AS SHOWN: ***')
                    instructions.append(complete_sql)
                    instructions.append(f'*** END SQL ***\n')
                    
                elif hire_table and status_table and status_table != hire_table:
                    # Hire + status in different tables
                    complete_sql = f'''SELECT COUNT(DISTINCT h."employeeId") AS headcount
FROM "{hire_table}" AS h
JOIN "{status_table}" AS s ON h."employeeId" = s."employeeId"
WHERE CAST(h."{hire_col}" AS DATE) <= '{as_of_date}'
  AND s."{status_col}" IN ('A', 'L')'''
                    
                    instructions.append(f'\n*** COMPLETE SQL (with JOIN) - USE EXACTLY AS SHOWN: ***')
                    instructions.append(complete_sql)
                    instructions.append(f'*** END SQL ***\n')
                else:
                    instructions.append('WARNING: Could not build complete SQL template - use columns listed above carefully')
            
            elif "hired_by_date" in intent_context and as_of_date:
                instructions.append(f'=== EMPLOYEES HIRED BY {as_of_date} ===')
                if hire_cols:
                    hire_table, hire_col = all_columns[hire_cols[0]]
                    complete_sql = f'''SELECT COUNT(DISTINCT "employeeId") AS count
FROM "{hire_table}"
WHERE CAST("{hire_col}" AS DATE) <= '{as_of_date}\''''
                    instructions.append(f'*** USE THIS EXACT SQL: ***')
                    instructions.append(complete_sql)
                    instructions.append(f'*** END SQL ***')
        
        # General reminder
        if instructions:
            instructions.append('CRITICAL: Use the SQL template exactly as provided above. Do not modify table or column names.')
        
        if instructions:
            return "\n\n=== EXPLICIT COLUMN INSTRUCTIONS (MUST FOLLOW) ===\n" + "\n".join(f"- {i}" for i in instructions) + "\n"
        
        return ""
    
    def _build_prompt(self, context: QueryContext, intent_context: str = "") -> str:
        """Build the prompt for SQL generation."""
        
        # NEW: Map intent parameters to actual columns
        column_instructions = self._map_intent_to_columns(intent_context, context.tables)
        
        # Format table schemas - show quoted names so LLM uses them
        schema_text = ""
        for table in context.tables:
            # Show the table name in quotes so LLM knows to use quotes
            schema_text += f'\n\nTable: "{table.table_name}" ({table.row_count:,} rows)\n'
            schema_text += "Columns:\n"
            for col in table.columns:
                col_type = table.column_types.get(col, 'VARCHAR')
                samples = table.sample_values.get(col, [])
                filter_cat = table.filter_columns.get(col, '')
                
                sample_str = f" -- Examples: {samples[:3]}" if samples else ""
                filter_str = f" [FILTER: {filter_cat}]" if filter_cat else ""
                
                schema_text += f'  - "{col}" ({col_type}){filter_str}{sample_str}\n'
        
        # Format join paths - include term mapping details
        join_text = ""
        term_mapping_text = ""
        if context.join_paths:
            join_text = "\n\nJoin Relationships:\n"
            for jp in context.join_paths:
                join_text += f"  - {jp['from']} = {jp['to']}\n"
                
                # If this is a term mapping join, add clear instructions
                if jp.get('type') == 'term_mapping':
                    term = jp.get('term', 'this term')
                    display_col = jp.get('display_column', 'description')
                    filter_clause = jp.get('filter', '')
                    lookup_table = jp['to'].split('.')[0]
                    
                    term_mapping_text += f"\n\nFor '{term}' queries:\n"
                    term_mapping_text += f"  - JOIN to lookup table: {lookup_table}\n"
                    term_mapping_text += f"  - Use alias like 'cd' for the lookup table\n"
                    if filter_clause:
                        term_mapping_text += f"  - Add WHERE {filter_clause}\n"
                    term_mapping_text += f"  - GROUP BY cd.\"{display_col}\" (use the lookup table alias)\n"
                    term_mapping_text += f"  - SELECT cd.\"{display_col}\" (qualified with alias)\n"
        
        # Format detected filters
        filter_text = ""
        if context.detected_filters:
            filter_text = "\n\nDetected Filters (apply these as WHERE conditions):\n"
            for key, value in context.detected_filters.items():
                filter_text += f"  - {key}: {value}\n"
        
        # NEW: Format intent context (from IntentEngine)
        intent_text = ""
        if intent_context:
            intent_text = f"\n\n{intent_context}\n"
        
        # Format business rules (legacy - will be deprecated)
        business_rules_text = ""
        if hasattr(context, 'business_rules') and context.business_rules:
            business_rules_text = "\n\n=== BUSINESS RULES (MUST APPLY) ===\n"
            business_rules_text += "The following interpretations MUST be used:\n"
            for rule in context.business_rules:
                business_rules_text += f"\n**{rule.pattern}**: {rule.description}\n"
                if rule.sql_template:
                    # Substitute parameters into template
                    sql_condition = rule.sql_template
                    for key, value in rule.parameters.items():
                        sql_condition = sql_condition.replace(f"{{{key}}}", value)
                    business_rules_text += f"  SQL: {sql_condition}\n"
                elif hasattr(rule, 'sql_conditions') and rule.sql_conditions:
                    # Legacy format
                    for condition in rule.sql_conditions:
                        business_rules_text += f"  SQL: {condition}\n"
            business_rules_text += "\nThese conditions are NON-NEGOTIABLE - they define the correct business logic.\n"
        
        prompt = f"""Given these database tables:
{schema_text}
{join_text}
{term_mapping_text}
{filter_text}
{intent_text}
{column_instructions}
{business_rules_text}

User Question: {context.question}

Write a DuckDB SQL query to answer this question.

CRITICAL RULES:
1. You can ONLY use columns that are listed above. Do NOT invent column names.
2. ALWAYS wrap table names in double quotes: "table_name"
3. ALWAYS wrap column names in double quotes: "column_name"
4. For "how many" questions, use COUNT(*) to count ALL rows
5. For "by X" questions, use GROUP BY with the appropriate column
6. Use the join relationships provided above
7. Return ONLY the SQL, no explanations, no markdown, no code fences
8. WHEN JOINING TABLES: Always qualify column names with table alias (e.g., cd."companyName" not just "companyName")
9. Use short aliases like ed, cd, pd for tables
10. If EXPLICIT COLUMN INSTRUCTIONS are provided above, you MUST follow them exactly
11. DATE COLUMNS ARE OFTEN STORED AS VARCHAR - Always use CAST("column" AS DATE) or TRY_CAST("column" AS DATE) when using YEAR(), EXTRACT(), or date comparisons

EXAMPLE with JOIN:
SELECT cd."companyName", COUNT(*) AS count
FROM "employment_table" AS ed
JOIN "company_table" AS cd ON ed."companyId" = cd."companyId"
WHERE ed."status" = 'A'
GROUP BY cd."companyName"

EXAMPLE with DATE:
SELECT EXTRACT(YEAR FROM CAST("hireDate" AS DATE)) AS year, COUNT(*) AS count
FROM "employees"
WHERE CAST("hireDate" AS DATE) <= '2025-12-31'
GROUP BY EXTRACT(YEAR FROM CAST("hireDate" AS DATE))

SQL:"""
        
        return prompt
    
    def _ensure_quoted_identifiers(self, sql: str, table_names: List[str]) -> str:
        """Ensure table names are quoted in the SQL."""
        for table_name in table_names:
            # If table name appears unquoted, quote it
            # Match table name that's not already in quotes
            # This handles FROM table, JOIN table, etc.
            pattern = rf'(?<!")\b{re.escape(table_name)}\b(?!")'
            replacement = f'"{table_name}"'
            sql = re.sub(pattern, replacement, sql)
        return sql
    
    def _clean_sql(self, response: str) -> str:
        """Clean LLM response to extract just the SQL."""
        sql = response.strip()
        
        logger.warning(f"[SQL_GEN] Cleaning SQL, input: {sql[:200]}...")
        
        # Remove ALL markdown code fences anywhere in the string
        sql = re.sub(r'```sql', '', sql, flags=re.IGNORECASE)
        sql = re.sub(r'```', '', sql)
        
        # Find the LAST occurrence of SELECT (the real query, not garbage prefix)
        # Split by SELECT and take from the last complete statement
        upper_sql = sql.upper()
        
        # Find all SELECT positions
        select_positions = [m.start() for m in re.finditer(r'\bSELECT\b', upper_sql)]
        
        if select_positions:
            # Take from the last SELECT that's followed by actual query content
            # Usually the real query is the last one, or the one with FROM after it
            for pos in reversed(select_positions):
                candidate = sql[pos:].strip()
                # Check if this looks like a real query (has FROM or is a simple aggregate)
                if 'FROM' in candidate.upper() or 'COUNT' in candidate.upper():
                    sql = candidate
                    break
        
        # Remove trailing semicolon for DuckDB
        sql = sql.rstrip(';').strip()
        
        # Final cleanup - remove any remaining newlines at start
        sql = sql.lstrip('\n').strip()
        
        logger.warning(f"[SQL_GEN] Cleaned SQL: {sql}")
        
        return sql
    
    # NOTE: _generate_fallback REMOVED
    # No fallback. LLM generates SQL or we fail. Period.
    # "Honest failure > Silent garbage"


# =============================================================================
# QUERY EXECUTOR
# =============================================================================

class QueryExecutor:
    """
    Executes SQL and handles errors gracefully.
    
    NO FALLBACK. SQL works or it doesn't.
    """
    
    def __init__(self, conn):
        """
        Args:
            conn: DuckDB connection
        """
        self.conn = conn
        
    def execute(self, sql: str) -> QueryResult:
        """
        Execute SQL and return results.
        
        Args:
            sql: SQL query string
            
        Returns:
            QueryResult with data or error info
        """
        logger.warning(f"[EXECUTOR] ========== EXECUTING SQL ==========")
        logger.warning(f"[EXECUTOR] SQL: {sql}")
        
        if not sql:
            logger.error(f"[EXECUTOR] FAILURE: No SQL provided")
            return QueryResult(
                success=False,
                sql="",
                error="No SQL generated",
                error_type="no_sql"
            )
        
        try:
            result = self.conn.execute(sql)
            
            # Get column names
            columns = [desc[0] for desc in result.description] if result.description else []
            
            # Fetch data
            rows = result.fetchall()
            
            # Convert to list of dicts
            data = []
            for row in rows:
                row_dict = {}
                for i, col in enumerate(columns):
                    val = row[i]
                    # Handle non-JSON-serializable types
                    if hasattr(val, 'isoformat'):
                        val = val.isoformat()
                    elif isinstance(val, bytes):
                        val = val.decode('utf-8', errors='replace')
                    row_dict[col] = val
                data.append(row_dict)
            
            logger.warning(f"[EXECUTOR] SUCCESS: {len(data)} rows, {len(columns)} columns")
            if data and len(data) <= 5:
                logger.warning(f"[EXECUTOR] Data: {data}")
            elif data:
                logger.warning(f"[EXECUTOR] First row: {data[0]}")
            
            return QueryResult(
                success=True,
                sql=sql,
                data=data,
                row_count=len(data),
                columns=columns
            )
            
        except Exception as e:
            error_str = str(e).lower()
            logger.error(f"[EXECUTOR] FAILURE: {e}")
            
            # Categorize error
            error_type = "unknown"
            if 'does not exist' in error_str or 'not found' in error_str:
                if 'table' in error_str:
                    error_type = "no_table"
                else:
                    error_type = "bad_column"
            elif 'syntax' in error_str:
                error_type = "syntax"
            
            logger.error(f"[EXECUTOR] Error type: {error_type}")
            
            return QueryResult(
                success=False,
                sql=sql,
                error=str(e),
                error_type=error_type
            )


# =============================================================================
# RESPONSE SYNTHESIZER
# =============================================================================

class ResponseSynthesizer:
    """
    Turns query results into natural language responses.
    """
    
    def __init__(self, llm_orchestrator=None):
        """
        Args:
            llm_orchestrator: LLM caller for synthesis
        """
        self.llm = llm_orchestrator
        
    def synthesize(self, context: QueryContext, result: QueryResult, intent: 'ResolvedIntent' = None) -> SynthesizedResponse:
        """
        Create a natural language response from query results.
        
        Args:
            context: Original query context
            result: Query execution result
            intent: Optional resolved intent from IntentEngine
            
        Returns:
            SynthesizedResponse with answer and metadata
        """
        # Handle errors
        if not result.success:
            return self._handle_error(context, result)
        
        # Handle empty results
        if result.row_count == 0:
            return SynthesizedResponse(
                answer=f"No results found for your query. The data might not contain records matching your criteria.",
                sql=result.sql,
                confidence=0.7,
                suggestions=[
                    "Try broadening your search criteria",
                    "Check if the filter values exist in the data"
                ]
            )
        
        # Generate response based on intent
        if context.detected_intent == QueryIntent.COUNT:
            response = self._synthesize_count(context, result)
        elif context.detected_intent == QueryIntent.AGGREGATE:
            response = self._synthesize_aggregate(context, result)
        elif context.detected_intent == QueryIntent.COMPARE:
            response = self._synthesize_comparison(context, result)
        else:
            response = self._synthesize_list(context, result)
        
        # Add intent interpretation to the answer (if resolved)
        if intent and intent.description and intent.confidence > 0.5:
            intent_note = f"\n\n_Analysis based on: {intent.description}_"
            if intent.parameters:
                param_parts = [f"{k}={v}" for k, v in intent.parameters.items() if v]
                if param_parts:
                    intent_note += f"\n_Parameters: {', '.join(param_parts)}_"
            response.answer = response.answer + intent_note
        
        # Legacy: Add business rules interpretation (will be deprecated)
        elif hasattr(context, 'business_rules') and context.business_rules:
            rules_note = "\n\n_Based on these interpretations:_\n"
            for rule in context.business_rules:
                rules_note += f"• _{rule.description}_\n"
            response.answer = response.answer + rules_note
        
        return response
    
    def _handle_error(self, context: QueryContext, result: QueryResult) -> SynthesizedResponse:
        """Handle query errors with helpful messages."""
        
        if result.error_type == "no_table":
            answer = f"I couldn't find a table matching your query. The available data might not include the information you're looking for."
        elif result.error_type == "bad_column":
            answer = f"The query referenced a column that doesn't exist. This might be a mismatch between the question and available data."
        elif result.error_type == "syntax":
            answer = f"There was an issue generating the SQL query. Please try rephrasing your question."
        else:
            answer = f"I encountered an error running the query: {result.error}"
        
        return SynthesizedResponse(
            answer=answer,
            sql=result.sql,
            confidence=0.0,
            suggestions=["Try rephrasing your question", "Ask about a different aspect of the data"]
        )
    
    def _synthesize_count(self, context: QueryContext, result: QueryResult) -> SynthesizedResponse:
        """Synthesize a count response."""
        if result.data and len(result.data) > 0:
            # Check if this is a grouped result (multiple rows) vs single count
            if len(result.data) > 1:
                # This is a GROUP BY result - use comparison synthesis
                return self._synthesize_comparison(context, result)
            
            # Single count result
            first_row = result.data[0]
            count_val = first_row.get('count', first_row.get('employee_count', first_row.get(result.columns[0], 0)))
            
            # Ensure it's an integer
            try:
                count_val = int(count_val)
            except (ValueError, TypeError):
                count_val = 0
            
            # Build natural answer
            filters_desc = ""
            if context.detected_filters:
                filter_parts = [f"{k}: {v}" for k, v in context.detected_filters.items()]
                filters_desc = f" with {', '.join(filter_parts)}"
            
            entity = context.detected_entities[0] if context.detected_entities else "records"
            
            answer = f"There are **{count_val:,}** {entity}{filters_desc}."
            
            return SynthesizedResponse(
                answer=answer,
                sql=result.sql,
                confidence=0.95,
                data_summary={'count': count_val},
                suggestions=[
                    f"Break this down by department",
                    f"Show me the list of these {entity}",
                    f"Compare this to last year"
                ]
            )
        
        return SynthesizedResponse(
            answer="Unable to determine count from results.",
            sql=result.sql,
            confidence=0.5
        )
    
    def _synthesize_aggregate(self, context: QueryContext, result: QueryResult) -> SynthesizedResponse:
        """Synthesize an aggregate response (sum, avg, etc.)."""
        if result.data and len(result.data) > 0:
            first_row = result.data[0]
            
            # Format the aggregate values
            parts = []
            for col, val in first_row.items():
                if isinstance(val, (int, float)):
                    if 'avg' in col.lower() or 'average' in col.lower():
                        parts.append(f"Average: **${val:,.2f}**" if val > 100 else f"Average: **{val:,.2f}**")
                    elif 'sum' in col.lower() or 'total' in col.lower():
                        parts.append(f"Total: **${val:,.2f}**" if val > 100 else f"Total: **{val:,.2f}**")
                    elif 'min' in col.lower():
                        parts.append(f"Minimum: **{val:,.2f}**")
                    elif 'max' in col.lower():
                        parts.append(f"Maximum: **{val:,.2f}**")
                    else:
                        parts.append(f"{col}: **{val:,.2f}**")
            
            answer = "\n".join(parts) if parts else "Results: " + str(first_row)
            
            return SynthesizedResponse(
                answer=answer,
                sql=result.sql,
                confidence=0.9,
                data_summary=first_row
            )
        
        return SynthesizedResponse(
            answer="Unable to calculate aggregate.",
            sql=result.sql,
            confidence=0.5
        )
    
    def _synthesize_comparison(self, context: QueryContext, result: QueryResult) -> SynthesizedResponse:
        """Synthesize a grouped comparison response."""
        if not result.data:
            return SynthesizedResponse(
                answer="No data for comparison.",
                sql=result.sql,
                confidence=0.5
            )
        
        # Build a table-like response
        lines = []
        for row in result.data[:20]:  # Limit to 20 groups
            parts = []
            for col, val in row.items():
                if isinstance(val, (int, float)):
                    parts.append(f"{col}: {val:,.0f}")
                else:
                    parts.append(f"{col}: {val}")
            lines.append(" | ".join(parts))
        
        answer = "**Breakdown:**\n\n" + "\n".join(lines)
        
        if result.row_count > 20:
            answer += f"\n\n_(Showing 20 of {result.row_count} groups)_"
        
        return SynthesizedResponse(
            answer=answer,
            sql=result.sql,
            confidence=0.9,
            data_summary={'groups': result.row_count}
        )
    
    def _synthesize_list(self, context: QueryContext, result: QueryResult) -> SynthesizedResponse:
        """Synthesize a list response."""
        if not result.data:
            return SynthesizedResponse(
                answer="No records found.",
                sql=result.sql,
                confidence=0.7
            )
        
        # Show count and sample
        count = result.row_count
        
        # Find good display columns (not IDs, not too long)
        display_cols = []
        for col in result.columns[:5]:  # Max 5 columns
            if not any(skip in col.lower() for skip in ['id', 'key', 'guid', 'uuid']):
                display_cols.append(col)
        
        if not display_cols:
            display_cols = result.columns[:3]
        
        # Build sample rows
        sample_lines = []
        for row in result.data[:10]:
            parts = [str(row.get(col, ''))[:30] for col in display_cols]
            sample_lines.append(" | ".join(parts))
        
        header = " | ".join(display_cols)
        separator = "-" * len(header)
        
        answer = f"**Found {count:,} records.**\n\n"
        answer += f"{header}\n{separator}\n"
        answer += "\n".join(sample_lines)
        
        if count > 10:
            answer += f"\n\n_(Showing 10 of {count} records)_"
        
        return SynthesizedResponse(
            answer=answer,
            sql=result.sql,
            confidence=0.9,
            data_summary={'total': count, 'columns': result.columns}
        )


# =============================================================================
# MAIN QUERY ENGINE
# =============================================================================

class QueryEngine:
    """
    Main orchestrator - the replacement for IntelligenceEngineV2.
    
    Usage:
        engine = QueryEngine(project, conn, llm_orchestrator)
        response = engine.ask("how many employees in Texas?")
    """
    
    def __init__(self, project: str, conn=None, llm_orchestrator=None, vendor: str = None, product: str = None):
        """
        Args:
            project: Project ID/name
            conn: DuckDB connection (optional, will try to get from handler)
            llm_orchestrator: LLM caller (optional)
            vendor: Vendor name (e.g., 'ukg') for rule inheritance
            product: Product name (e.g., 'pro') for rule inheritance
        """
        self.project = project
        self.conn = conn
        self.llm = llm_orchestrator
        self.vendor = vendor
        self.product = product
        
        # Components
        self.assembler: Optional[ContextAssembler] = None
        self.generator: Optional[SQLGenerator] = None
        self.executor: Optional[QueryExecutor] = None
        self.synthesizer: Optional[ResponseSynthesizer] = None
        self.intent_engine: Optional['IntentEngine'] = None  # NEW: Replaces rule_interpreter
        
        # Backward compatibility alias
        self.rule_interpreter = None  # Will point to intent_engine
        
        # Initialize if we have a connection
        if conn:
            self._init_components()
    
    def _init_components(self):
        """Initialize all components."""
        from backend.utils.intelligence.intent_engine import IntentEngine
        
        self.assembler = ContextAssembler(self.conn, self.project)
        self.generator = SQLGenerator(self.llm)
        self.executor = QueryExecutor(self.conn)
        self.synthesizer = ResponseSynthesizer(self.llm)
        
        # Preserve IntentEngine across requests - don't recreate
        # This keeps session memory (_confirmed_intents) intact
        if self.intent_engine is None:
            self.intent_engine = IntentEngine(
                conn=self.conn, 
                project=self.project,
                vendor=self.vendor,
                product=self.product
            )
            self.rule_interpreter = self.intent_engine
            logger.warning(f"[ENGINE] Created NEW IntentEngine for project: {self.project}")
        else:
            # Update connection on existing engine but preserve memory
            self.intent_engine.conn = self.conn
            logger.warning(f"[ENGINE] REUSING IntentEngine (confirmed intents: {list(self.intent_engine._confirmed_intents.keys())})")
        
        logger.warning(f"[ENGINE] Initialized for project: {self.project}, vendor: {self.vendor}, product: {self.product}")
    
    def set_vendor_product(self, vendor: str = None, product: str = None):
        """Set vendor/product after initialization (for dynamic loading)."""
        from backend.utils.intelligence.intent_engine import IntentEngine
        
        if vendor:
            self.vendor = vendor
        if product:
            self.product = product
        # Reinitialize intent engine with new values
        if self.conn and (vendor or product):
            self.intent_engine = IntentEngine(
                conn=self.conn,
                project=self.project,
                vendor=self.vendor,
                product=self.product
            )
            self.rule_interpreter = self.intent_engine  # Backward compatibility
            logger.info(f"[ENGINE] Updated vendor/product: {self.vendor}/{self.product}")
    
    def load_context(self, structured_handler=None, **kwargs):
        """
        Load context from structured handler.
        
        This method exists for compatibility with the old engine interface.
        """
        if structured_handler and hasattr(structured_handler, 'conn'):
            self.conn = structured_handler.conn
            self._init_components()
            logger.info("[ENGINE] Loaded context from structured handler")
    
    def ask(self, question: str, mode=None, context: Dict = None, skip_confirmation: bool = False, session_id: str = None) -> SynthesizedResponse:
        """
        Answer a question.
        
        This is the main entry point - compatible with old engine.ask() interface.
        
        Args:
            question: Natural language question
            mode: Ignored (for compatibility)
            context: Additional context (for compatibility)
            skip_confirmation: If True, skip confirmation step (user already confirmed)
            session_id: Session ID for workflow capture
            
        Returns:
            SynthesizedResponse (compatible with old SynthesizedAnswer)
        """
        logger.warning(f"[ENGINE] ==========================================")
        logger.warning(f"[ENGINE] NEW QUESTION: {question}")
        logger.warning(f"[ENGINE] Project: {self.project}")
        logger.warning(f"[ENGINE] ==========================================")
        
        if not self.conn or not self.assembler:
            error_msg = "Database not connected. Please upload data first."
            logger.error(f"[ENGINE] FAILURE: {error_msg}")
            response = SynthesizedResponse(
                answer=error_msg,
                sql="",
                confidence=0.0
            )
            response._question = question
            return response
        
        try:
            # Step 1: Assemble context
            logger.warning(f"[ENGINE] STEP 1: Assembling context...")
            query_context = self.assembler.assemble(question)
            
            if not query_context.tables:
                error_msg = "No relevant tables found. Available tables may not match your question."
                logger.error(f"[ENGINE] FAILURE: {error_msg}")
                response = SynthesizedResponse(
                    answer=f"I couldn't find any relevant tables for your question. Please make sure data has been uploaded.",
                    sql="",
                    confidence=0.0,
                    suggestions=["Upload data files first", "Try asking about the data you've uploaded"]
                )
                response._question = question
                return response
            
            logger.warning(f"[ENGINE] STEP 1 COMPLETE: Found {len(query_context.tables)} tables: {[t.table_name for t in query_context.tables]}")
            
            # Step 1.5: Analyze Intent (NEW - Consultative Clarification)
            logger.warning(f"[ENGINE] STEP 1.5: Analyzing user intent...")
            resolved_intent = None
            
            if self.intent_engine:
                resolved_intent, clarification = self.intent_engine.analyze(question)
                
                # Check if clarification needed
                if clarification:
                    logger.warning(f"[ENGINE] CLARIFICATION NEEDED: {clarification.question}")
                    response = SynthesizedResponse(
                        answer=None,
                        sql="",
                        confidence=0.0,
                        needs_clarification=True,
                        clarification_question=clarification.question,
                        clarification_options=clarification.options,
                        clarification_key=clarification.key
                    )
                    response._question = question
                    return response
                
                # We have resolved intent
                if resolved_intent:
                    logger.warning(f"[ENGINE] STEP 1.5 COMPLETE: Intent resolved - {resolved_intent.description}")
                    logger.warning(f"[ENGINE]   Category: {resolved_intent.category.value}")
                    logger.warning(f"[ENGINE]   Parameters: {resolved_intent.parameters}")
                    logger.warning(f"[ENGINE]   Confidence: {resolved_intent.confidence}")
                    
                    # Record step for workflow capture
                    if session_id:
                        self.intent_engine.record_step(session_id, resolved_intent, question)
                else:
                    logger.warning(f"[ENGINE] STEP 1.5 COMPLETE: No specific intent patterns detected")
            
            # Step 2: Generate SQL with intent context
            logger.warning(f"[ENGINE] STEP 2: Generating SQL...")
            
            # Build intent context for LLM
            intent_context = ""
            if resolved_intent and self.intent_engine:
                intent_context = self.intent_engine.format_for_llm(resolved_intent)
            
            sql, sql_error = self.generator.generate(query_context, intent_context=intent_context)
            
            if sql_error:
                error_msg = f"SQL generation failed: {sql_error}"
                logger.error(f"[ENGINE] FAILURE: {error_msg}")
                response = SynthesizedResponse(
                    answer=f"I couldn't generate a query for your question. Error: {sql_error}",
                    sql="",
                    confidence=0.0
                )
                response._question = question
                return response
            
            if not sql:
                error_msg = "SQL generator returned empty SQL with no error"
                logger.error(f"[ENGINE] FAILURE: {error_msg}")
                response = SynthesizedResponse(
                    answer="I couldn't generate a query for your question. Please try rephrasing.",
                    sql="",
                    confidence=0.0
                )
                response._question = question
                return response
            
            logger.warning(f"[ENGINE] STEP 2 COMPLETE: SQL generated")
            
            # Step 3: Execute SQL
            logger.warning(f"[ENGINE] STEP 3: Executing SQL...")
            result = self.executor.execute(sql)
            
            if not result.success:
                logger.error(f"[ENGINE] STEP 3 FAILED: {result.error}")
            else:
                logger.warning(f"[ENGINE] STEP 3 COMPLETE: {result.row_count} rows returned")
            
            # Step 4: Synthesize response
            logger.warning(f"[ENGINE] STEP 4: Synthesizing response...")
            response = self.synthesizer.synthesize(query_context, result, intent=resolved_intent)
            
            # Set question for compatibility with old interface
            response._question = question
            
            # Add intent metadata to response
            if resolved_intent:
                response._intent = resolved_intent
            
            logger.warning(f"[ENGINE] STEP 4 COMPLETE: Confidence {response.confidence}")
            logger.warning(f"[ENGINE] ==========================================")
            logger.warning(f"[ENGINE] FINAL ANSWER: {response.answer[:200] if response.answer else 'None'}...")
            logger.warning(f"[ENGINE] ==========================================")
            
            return response
            
        except Exception as e:
            logger.error(f"[ENGINE] EXCEPTION: {e}")
            logger.error(traceback.format_exc())
            
            response = SynthesizedResponse(
                answer=f"I encountered an error processing your question: {str(e)}",
                sql="",
                confidence=0.0
            )
            response._question = question
            return response
    
    def _check_intent_confirmation(self, question: str, context: QueryContext, sql: str) -> Optional[Dict]:
        """
        Check if we should confirm our interpretation before executing.
        
        For complex queries, we explain what we're about to do in plain English
        and ask for confirmation. This builds trust and captures business rules.
        
        Returns:
            Dict with confirmation message and interpreted logic, or None if no confirmation needed
        """
        try:
            q_lower = question.lower()
            
            # Skip confirmation for simple queries or explicit "just do it" phrases
            skip_phrases = ['just', 'simply', 'quick', 'exactly']
            if any(phrase in q_lower for phrase in skip_phrases):
                return None
            
            # Detect queries that warrant confirmation
            needs_confirmation = False
            interpretation_parts = []
            
            # 1. "As of" date queries - complex business logic
            if 'as of' in q_lower:
                needs_confirmation = True
                # Extract the date
                import re
                date_match = re.search(r'as of\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})', q_lower)
                if date_match:
                    date_str = date_match.group(1)
                    interpretation_parts.append(f"Point-in-time as of {date_str}")
                    interpretation_parts.append("Including employees with status Active (A) or Leave (L)")
                    interpretation_parts.append(f"With hire date on or before {date_str}")
            
            # 2. Status terms that have implicit meaning
            status_terms = {
                'active': "status = 'A' (Active)",
                'terminated': "status = 'T' (Terminated)",
                'on leave': "status = 'L' (Leave)",
                'inactive': "status NOT IN ('A', 'L')"
            }
            for term, meaning in status_terms.items():
                if term in q_lower and 'as of' not in q_lower:  # as of handles its own status
                    interpretation_parts.append(f"Filtering to {meaning}")
            
            # 3. Aggregations with groupings
            if any(word in q_lower for word in ['average', 'total', 'sum', 'by']):
                # Extract what we're aggregating
                if 'salary' in q_lower:
                    interpretation_parts.append("Calculating salary figures")
                if 'count' in q_lower or 'how many' in q_lower:
                    interpretation_parts.append("Counting employees")
                
                # Extract grouping
                by_match = re.search(r'\bby\s+(\w+)', q_lower)
                if by_match:
                    dimension = by_match.group(1)
                    interpretation_parts.append(f"Grouped by {dimension}")
            
            # 4. Time-based comparisons
            if any(word in q_lower for word in ['last year', 'this year', 'ytd', 'year to date', 'previous']):
                needs_confirmation = True
                interpretation_parts.append("Using time-based comparison logic")
            
            # Only confirm if we have complex interpretation to share
            if needs_confirmation or len(interpretation_parts) >= 2:
                # Build the confirmation message
                interpretation = "\n".join(f"• {part}" for part in interpretation_parts)
                
                # Add SQL summary (simplified)
                sql_summary = self._summarize_sql_logic(sql)
                if sql_summary:
                    interpretation += f"\n\nSQL approach: {sql_summary}"
                
                return {
                    'type': 'intent_confirmation',
                    'message': f"Here's how I'm interpreting your question:\n\n{interpretation}\n\nShould I proceed with this?",
                    'interpretation': interpretation_parts,
                    'sql_preview': sql[:200] + '...' if len(sql) > 200 else sql,
                    'original_question': question
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"[ENGINE] Intent confirmation check failed: {e}")
            return None
    
    def _summarize_sql_logic(self, sql: str) -> str:
        """Convert SQL to a brief plain-English summary."""
        try:
            sql_upper = sql.upper()
            parts = []
            
            # Detect aggregation
            if 'COUNT(*)' in sql_upper:
                parts.append("counting records")
            elif 'AVG(' in sql_upper:
                parts.append("calculating average")
            elif 'SUM(' in sql_upper:
                parts.append("calculating total")
            
            # Detect grouping
            if 'GROUP BY' in sql_upper:
                parts.append("grouped by dimension")
            
            # Detect filtering
            if 'WHERE' in sql_upper:
                parts.append("with filters applied")
            
            # Detect joins
            if 'JOIN' in sql_upper:
                parts.append("joining related tables")
            
            return ", ".join(parts) if parts else None
            
        except:
            return None
    
    def _load_preferences(self) -> Dict[str, str]:
        """Load stored user preferences from _term_mappings."""
        preferences = {}
        try:
            results = self.conn.execute("""
                SELECT term, employee_column 
                FROM _term_mappings 
                WHERE project = ? AND mapping_type = 'user_preference'
            """, [self.project]).fetchall()
            
            for term, value in results:
                preferences[term] = value
            
            if preferences:
                logger.warning(f"[ENGINE] Loaded {len(preferences)} user preferences")
        except Exception as e:
            logger.debug(f"[ENGINE] Could not load preferences: {e}")
        
        return preferences
    
    # =========================================================================
    # COMPATIBILITY PROPERTIES (for old code that accesses engine properties)
    # =========================================================================
    
    @property
    def confirmed_facts(self) -> Dict:
        """Compatibility with old engine."""
        return {}
    
    @confirmed_facts.setter
    def confirmed_facts(self, value: Dict):
        """Compatibility with old engine."""
        pass
    
    @property
    def structured_handler(self):
        """Compatibility with old engine."""
        return None
    
    @property
    def conversation_context(self) -> Dict:
        """Compatibility with old engine."""
        return {}
    
    @conversation_context.setter
    def conversation_context(self, value: Dict):
        """Compatibility with old engine."""
        pass


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_query_engine(project: str, structured_handler=None, llm_orchestrator=None) -> QueryEngine:
    """
    Factory function to create a QueryEngine.
    
    Args:
        project: Project ID/name
        structured_handler: StructuredDataHandler instance
        llm_orchestrator: LLMOrchestrator instance
        
    Returns:
        Configured QueryEngine
    """
    conn = structured_handler.conn if structured_handler else None
    engine = QueryEngine(project, conn, llm_orchestrator)
    return engine
