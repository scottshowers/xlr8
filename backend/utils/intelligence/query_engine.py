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
        # We don't use clarification in QueryEngine, so return None
        # unless we have suggestions (which could be exposed as follow-ups)
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
        tables = self._find_relevant_tables(entities, filters)
        
        # Step 4.5: If term mappings exist, FILTER to only source + lookup tables
        # This dramatically reduces noise for the LLM
        if term_mapping_info:
            term_mapping_tables = []
            for mapping in term_mapping_info:
                # Add source table
                source_table = mapping.get('source_table')
                if source_table and not any(t.table_name == source_table for t in term_mapping_tables):
                    source_schema = self._get_table_schema(source_table, 0)
                    if source_schema:
                        term_mapping_tables.append(source_schema)
                        logger.warning(f"[CONTEXT] Term mapping source table: {source_table}")
                
                # Add lookup table
                lookup_table = mapping.get('lookup_table')
                if lookup_table and not any(t.table_name == lookup_table for t in term_mapping_tables):
                    lookup_schema = self._get_table_schema(lookup_table, 0)
                    if lookup_schema:
                        term_mapping_tables.append(lookup_schema)
                        logger.warning(f"[CONTEXT] Term mapping lookup table: {lookup_table}")
            
            # Replace full table list with just term mapping tables
            if term_mapping_tables:
                logger.warning(f"[CONTEXT] Using ONLY term mapping tables (was {len(tables)} tables, now {len(term_mapping_tables)})")
                tables = term_mapping_tables
        
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
    
    def _find_relevant_tables(self, entities: List[str], filters: Dict[str, str]) -> List[TableSchema]:
        """Find tables that match the detected entities and filters."""
        tables = []
        
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
        
    def generate(self, context: QueryContext) -> Tuple[str, Optional[str]]:
        """
        Generate SQL for the given context.
        
        NO FALLBACK. Returns (sql, error) tuple.
        
        Args:
            context: QueryContext with tables, schemas, joins
            
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
        
        if not self.llm:
            error = "NO LLM CONFIGURED. Cannot generate SQL without LLM."
            logger.error(f"[SQL_GEN] FAILURE: {error}")
            return "", error
        
        prompt = self._build_prompt(context)
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
    
    def _build_prompt(self, context: QueryContext) -> str:
        """Build the prompt for SQL generation."""
        
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
                    term_mapping_text += f"  - Use the join relationship above\n"
                    term_mapping_text += f"  - Add WHERE {filter_clause}\n"
                    term_mapping_text += f"  - GROUP BY and SELECT the \"{display_col}\" column from the lookup table\n"
        
        # Format detected filters
        filter_text = ""
        if context.detected_filters:
            filter_text = "\n\nDetected Filters (apply these as WHERE conditions):\n"
            for key, value in context.detected_filters.items():
                filter_text += f"  - {key}: {value}\n"
        
        prompt = f"""Given these database tables:
{schema_text}
{join_text}
{term_mapping_text}
{filter_text}

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
        
    def synthesize(self, context: QueryContext, result: QueryResult) -> SynthesizedResponse:
        """
        Create a natural language response from query results.
        
        Args:
            context: Original query context
            result: Query execution result
            
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
            return self._synthesize_count(context, result)
        elif context.detected_intent == QueryIntent.AGGREGATE:
            return self._synthesize_aggregate(context, result)
        elif context.detected_intent == QueryIntent.COMPARE:
            return self._synthesize_comparison(context, result)
        else:
            return self._synthesize_list(context, result)
    
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
    
    def __init__(self, project: str, conn=None, llm_orchestrator=None):
        """
        Args:
            project: Project ID/name
            conn: DuckDB connection (optional, will try to get from handler)
            llm_orchestrator: LLM caller (optional)
        """
        self.project = project
        self.conn = conn
        self.llm = llm_orchestrator
        
        # Components
        self.assembler: Optional[ContextAssembler] = None
        self.generator: Optional[SQLGenerator] = None
        self.executor: Optional[QueryExecutor] = None
        self.synthesizer: Optional[ResponseSynthesizer] = None
        
        # Initialize if we have a connection
        if conn:
            self._init_components()
    
    def _init_components(self):
        """Initialize all components."""
        self.assembler = ContextAssembler(self.conn, self.project)
        self.generator = SQLGenerator(self.llm)
        self.executor = QueryExecutor(self.conn)
        self.synthesizer = ResponseSynthesizer(self.llm)
        logger.info(f"[ENGINE] Initialized for project: {self.project}")
    
    def load_context(self, structured_handler=None, **kwargs):
        """
        Load context from structured handler.
        
        This method exists for compatibility with the old engine interface.
        """
        if structured_handler and hasattr(structured_handler, 'conn'):
            self.conn = structured_handler.conn
            self._init_components()
            logger.info("[ENGINE] Loaded context from structured handler")
    
    def ask(self, question: str, mode=None, context: Dict = None) -> SynthesizedResponse:
        """
        Answer a question.
        
        This is the main entry point - compatible with old engine.ask() interface.
        
        Args:
            question: Natural language question
            mode: Ignored (for compatibility)
            context: Additional context (for compatibility)
            
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
            
            # Step 2: Generate SQL (NO FALLBACK)
            logger.warning(f"[ENGINE] STEP 2: Generating SQL...")
            sql, sql_error = self.generator.generate(query_context)
            
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
            response = self.synthesizer.synthesize(query_context, result)
            
            # Set question for compatibility with old interface
            response._question = question
            
            logger.warning(f"[ENGINE] STEP 4 COMPLETE: Confidence {response.confidence}")
            logger.warning(f"[ENGINE] ==========================================")
            logger.warning(f"[ENGINE] FINAL ANSWER: {response.answer[:200]}...")
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
