"""
XLR8 Intelligence Engine - SQL Generator v4.1
==============================================

Generates SQL queries from natural language questions.

v4.1 CHANGES:
- CROSS-DOMAIN JOIN DETECTION: _needs_join() now checks ALL tables in schema,
  not just pre-selected ones. Discovers and adds missing tables automatically.
- Example: "employees in Texas with 401k" now correctly adds Deductions table
  even if only Personal was initially selected, then builds the JOIN.

v4.0 CHANGES:
- SEMANTIC JOIN DETECTION: _needs_join() now uses Context Graph to detect
  when question concepts span multiple tables, not hardcoded patterns
- Example: "employees in Texas with 401k" now correctly triggers JOIN
  because "Texas" maps to Personal.stateprovince and "401k" maps to
  Deductions.deductionbenefit_code, and both share employee_number hub

v3.0 CHANGES:
- CONTEXT GRAPH JOINS: Uses Context Graph hub/spoke relationships
  to automatically suggest and build JOIN clauses
- Gets join columns from semantic type mappings
- Prefers high-coverage spokes for better query performance

v2.0 CHANGES:
- SMART FILTER DETECTION: Detects question keywords that match column VALUES
  and injects WHERE clauses (e.g., "SUI rates" → WHERE type_of_tax ILIKE '%SUI%')
- SMART FALLBACK: When LLM fails, uses filtered query instead of SELECT *
- Filter hints in LLM prompt guide better query generation

Key features:
- Cross-domain JOIN discovery via Context Graph (v4.1)
- Semantic JOIN detection via Context Graph (v4.0)
- Context Graph-aware join generation (v3.0)
- Question-aware value filtering (the key to useful queries)
- Simple vs complex query detection
- CREATE TABLE schema format for better LLM accuracy
- Column name fixing and validation
- DuckDB syntax corrections

Deploy to: backend/utils/intelligence/sql_generator.py
"""

import re
import json
import logging
from typing import Dict, List, Optional, Set, Tuple, Any
from difflib import SequenceMatcher

from .types import SynthesizedAnswer
from .table_selector import TableSelector

logger = logging.getLogger(__name__)


# =============================================================================
# SQL KEYWORDS (for column validation)
# =============================================================================

SQL_KEYWORDS = {
    'select', 'from', 'where', 'and', 'or', 'not', 'in', 'is', 'null',
    'like', 'ilike', 'as', 'on', 'join', 'left', 'right', 'inner', 'outer',
    'group', 'by', 'order', 'asc', 'desc', 'limit', 'offset', 'having',
    'count', 'sum', 'avg', 'min', 'max', 'distinct', 'case', 'when', 'then',
    'else', 'end', 'cast', 'nulls', 'last', 'first', 'true', 'false',
    'between', 'exists', 'all', 'any', 'union', 'except', 'intersect',
    'coalesce', 'upper', 'lower', 'trim', 'substring', 'concat'
}

# State name to code mapping
US_STATE_CODES = {
    'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR',
    'california': 'CA', 'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE',
    'florida': 'FL', 'georgia': 'GA', 'hawaii': 'HI', 'idaho': 'ID',
    'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA', 'kansas': 'KS',
    'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
    'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS',
    'missouri': 'MO', 'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV',
    'new hampshire': 'NH', 'new jersey': 'NJ', 'new mexico': 'NM', 'new york': 'NY',
    'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH', 'oklahoma': 'OK',
    'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
    'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT',
    'vermont': 'VT', 'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV',
    'wisconsin': 'WI', 'wyoming': 'WY'
}


class SQLGenerator:
    """
    Generates SQL queries from natural language using LLMs.
    
    Uses a two-path approach:
    1. Simple queries: CREATE TABLE format, single table
    2. Complex queries: Multi-table schema with relationships
    
    Post-processes LLM output to:
    - Expand table aliases to full names
    - Fix column names using semantic mappings
    - Inject status filters automatically
    - Fix DuckDB-specific syntax
    """
    
    def __init__(self, structured_handler=None, schema: Dict = None,
                 table_selector: TableSelector = None,
                 filter_candidates: Dict = None,
                 confirmed_facts: Dict = None,
                 relationships: List = None):
        """
        Initialize the SQL generator.
        
        Args:
            structured_handler: DuckDB handler for schema queries
            schema: Schema metadata (tables, columns)
            table_selector: TableSelector instance
            filter_candidates: Dict of filter category → candidates
            confirmed_facts: Dict of confirmed filters (status=active, etc.)
            relationships: Detected table relationships
        """
        self.handler = structured_handler
        self.schema = schema or {}
        self.table_selector = table_selector
        self.filter_candidates = filter_candidates or {}
        self.confirmed_facts = confirmed_facts or {}
        self.relationships = relationships or []
        
        # State tracking
        self._table_aliases: Dict[str, str] = {}
        self._column_mappings: Dict[str, str] = {}
        self._orchestrator = None
        self._filter_translations: List[Dict] = []  # v5.0: Semantic value translations
    
    def _needs_join(self, question: str, tables: List[Dict]) -> Tuple[bool, List[Dict]]:
        """
        Detect if a question requires a JOIN query.
        
        v4.1 SEMANTIC DETECTION:
        Instead of pattern matching, detect when question concepts span multiple
        tables that share a hub connection in the Context Graph.
        
        CRITICAL: Checks ALL tables in schema, not just selected ones!
        This allows detection of cross-domain queries like "employees in Texas with 401k"
        even if only the Personal table was initially selected.
        
        Example: "employees in Texas with 401k"
        - "Texas" → matches values in Personal.stateprovince
        - "401k" → matches values in Deductions.deductionbenefit_code
        - Both tables share employee_number hub → needs JOIN
        
        Returns:
            Tuple of (needs_join: bool, additional_tables: List[Dict])
            - needs_join: True if JOIN is needed
            - additional_tables: Tables to add to the query (if not already included)
        """
        q_lower = question.lower()
        
        # =================================================================
        # EXPLICIT JOIN PATTERNS (keep as fast-path)
        # =================================================================
        explicit_patterns = [
            r'\bjoin\s+with\b',           # "join with"
            r'\bcombine\b',               # "combine"
            r'\bcross.?reference',        # "cross-reference"
            r'\blink\w*\s+(to|with)',     # "link to", "linked with"
            r'\bfrom\s+(\w+)\s+and\s+(\w+)',  # "from employees and departments"
        ]
        
        for pattern in explicit_patterns:
            if re.search(pattern, q_lower):
                logger.info(f"[SQL-GEN] JOIN needed: explicit pattern '{pattern}' matched")
                return True, []
        
        # =================================================================
        # v4.1 SEMANTIC DETECTION - check ALL tables in schema
        # =================================================================
        if not self.table_selector:
            logger.debug("[SQL-GEN] No table_selector - skipping semantic JOIN detection")
            return False, []
        
        if not self.handler or not hasattr(self.handler, 'conn'):
            logger.debug("[SQL-GEN] No handler.conn - skipping semantic JOIN detection")
            return False, []
        
        # Get ALL tables from schema, not just the selected ones
        all_tables = self.schema.get('tables', [])
        
        if not all_tables:
            logger.debug("[SQL-GEN] _needs_join: NO TABLES IN SCHEMA")
            return False, []
        
        # Track which tables were originally selected
        selected_table_names = {t.get('table_name', '').lower() for t in tables}
        
        # Extract significant words from question
        words = re.findall(r'\b[a-z0-9]+\b', q_lower)
        skip_words = {
            'the', 'a', 'an', 'is', 'are', 'my', 'our', 'your', 'what', 'how', 
            'show', 'list', 'get', 'find', 'check', 'verify', 'configured', 
            'setup', 'with', 'and', 'or', 'in', 'on', 'for', 'to', 'from',
            'all', 'any', 'employees', 'employee', 'who', 'have', 'has', 'their'
        }
        significant_words = [w for w in words if len(w) >= 2 and w not in skip_words]
        
        if not significant_words:
            logger.warning("[SQL-GEN] _needs_join: No significant words")
            return False, []
        
        logger.warning(f"[SQL-GEN] _needs_join: words={significant_words}, {len(all_tables)} tables")
        
        # Map each significant word to tables that have matching column values
        word_to_tables: Dict[str, Set[str]] = {}
        table_lookup: Dict[str, Dict] = {}  # For retrieving table metadata later
        profiles_checked = 0
        
        for table in all_tables:
            table_name = table.get('table_name', '')
            if not table_name:
                continue
            
            table_lookup[table_name.lower()] = table
            
            try:
                # Get column profiles for this table
                # First try with top_values_json (newer schema)
                try:
                    profiles = self.handler.conn.execute("""
                        SELECT column_name, distinct_values, top_values_json
                        FROM _column_profiles 
                        WHERE LOWER(table_name) = LOWER(?)
                        AND (distinct_values IS NOT NULL OR top_values_json IS NOT NULL)
                    """, [table_name]).fetchall()
                except Exception:
                    # Fallback for tables without top_values_json column
                    profiles = self.handler.conn.execute("""
                        SELECT column_name, distinct_values, NULL as top_values_json
                        FROM _column_profiles 
                        WHERE LOWER(table_name) = LOWER(?)
                        AND distinct_values IS NOT NULL
                    """, [table_name]).fetchall()
                
                profiles_checked += len(profiles)
                
                for col_name, distinct_values_json, top_values_json in profiles:
                    # Try top_values_json first (more complete), fallback to distinct_values
                    values_json = top_values_json or distinct_values_json
                    if not values_json or values_json == '[]':
                        continue
                    
                    try:
                        values = json.loads(values_json)
                        
                        for val_info in values:
                            val = str(val_info.get('value', '') if isinstance(val_info, dict) else val_info).lower().strip()
                            
                            if not val or len(val) < 2:
                                continue
                            
                            # Check each significant word against this value
                            for word in significant_words:
                                # Match conditions:
                                # 1. Exact match
                                # 2. Word is substantial substring of value (3+ chars)
                                # 3. Value is substantial substring of word (3+ chars)
                                # 4. State name to code mapping (Texas → TX)
                                is_match = False
                                
                                if word == val:
                                    is_match = True
                                elif len(word) >= 3 and word in val:
                                    is_match = True
                                elif len(val) >= 3 and val in word:
                                    is_match = True
                                # State name matching (Texas → TX, etc.)
                                elif word in US_STATE_CODES and US_STATE_CODES[word].lower() == val:
                                    is_match = True
                                elif word in US_STATE_CODES and US_STATE_CODES[word].lower() in val:
                                    is_match = True
                                
                                if is_match:
                                    if word not in word_to_tables:
                                        word_to_tables[word] = set()
                                    word_to_tables[word].add(table_name)
                                    in_selected = "✓" if table_name.lower() in selected_table_names else "NEW"
                                    logger.info(f"[SQL-GEN] [{in_selected}] Word '{word}' → table '{table_name[-40:]}' via {col_name}='{val[:30]}'")
                                    break  # Move to next value
                                    
                    except (json.JSONDecodeError, TypeError):
                        pass
                        
            except Exception as e:
                logger.warning(f"[SQL-GEN] _needs_join error checking {table_name[-30:]}: {e}")
        
        # Now check if we have words mapping to different tables that share a hub
        all_matched_tables = set()
        for word, matched_tables in word_to_tables.items():
            all_matched_tables.update(matched_tables)
        
        # Single summary log - only log if we found something interesting
        if word_to_tables:
            matches_summary = {w: [t[-25:] for t in ts] for w, ts in word_to_tables.items()}
            logger.info(f"[SQL-GEN] JOIN check: {len(all_tables)} tables, {profiles_checked} profiles. Matches: {matches_summary}")
        else:
            logger.warning(f"[SQL-GEN] _needs_join: NO VALUE MATCHES found in {profiles_checked} profiles across {len(all_tables)} tables")
        
        if len(all_matched_tables) < 2:
            logger.warning(f"[SQL-GEN] _needs_join: Only {len(all_matched_tables)} tables matched - need 2+ for JOIN")
            return False, []
        
        # v4.2: Prioritize tables - check selected tables and master tables first
        # This prevents config tables from being matched before employee tables
        def table_priority(tname: str) -> int:
            """Lower score = higher priority"""
            score = 100
            # Highest priority: already selected by TableSelector
            if tname.lower() in selected_table_names:
                score -= 50
            # High priority: master tables (employee data)
            meta = table_lookup.get(tname.lower(), {})
            if meta.get('table_type') == 'master':
                score -= 30
            # Deprioritize config tables
            if 'config' in tname.lower() or 'validation' in tname.lower():
                score += 20
            return score
        
        matched_list = sorted(all_matched_tables, key=table_priority)
        logger.warning(f"[SQL-GEN] _needs_join: Checking {len(matched_list)} tables, priority order: {[t[-25:] for t in matched_list[:4]]}")
        
        additional_tables = []
        
        # v4.2: First pass - look for employee_number joins (preferred for cross-domain)
        for i, t1 in enumerate(matched_list):
            for t2 in matched_list[i+1:]:
                join_path = self.table_selector.get_join_path(t1, t2)
                if join_path:
                    sem_type = join_path.get('semantic_type', 'unknown')
                    # Prefer employee_number joins for cross-domain employee queries
                    if sem_type == 'employee_number':
                        logger.warning(f"[SQL-GEN] ✅ JOIN (preferred): {t1[-25:]} ↔ {t2[-25:]} via {sem_type}")
                        for t in [t1, t2]:
                            if t.lower() not in selected_table_names:
                                table_meta = table_lookup.get(t.lower())
                                if table_meta:
                                    additional_tables.append(table_meta)
                                    logger.warning(f"[SQL-GEN] ➕ Added: {t[-35:]}")
                        return True, additional_tables
        
        # Second pass - accept any join path
        for i, t1 in enumerate(matched_list):
            for t2 in matched_list[i+1:]:
                join_path = self.table_selector.get_join_path(t1, t2)
                if join_path:
                    sem_type = join_path.get('semantic_type', 'unknown')
                    logger.warning(f"[SQL-GEN] ✅ JOIN (fallback): {t1[-25:]} ↔ {t2[-25:]} via {sem_type}")
                    
                    # Add any matched tables that weren't in the original selection
                    for t in [t1, t2]:
                        if t.lower() not in selected_table_names:
                            table_meta = table_lookup.get(t.lower())
                            if table_meta:
                                additional_tables.append(table_meta)
                                logger.warning(f"[SQL-GEN] ➕ Added: {t[-35:]}")
                    
                    return True, additional_tables
        
        return False, []
    
    def _build_relationship_hints(self, tables: List[Dict]) -> str:
        """
        Build relationship hints for the LLM prompt.
        
        v3.0: Also uses Context Graph for join hints.
        
        Tells the LLM how tables can be joined based on:
        1. Context Graph hub/spoke relationships (highest priority)
        2. Detected relationships from Supabase
        
        Handles both:
        - Object format (from project_intelligence): rel.from_table, rel.to_table
        - Dict format (from Supabase): rel['source_table'], rel['target_table']
        """
        table_names = {t.get('table_name', '').lower() for t in tables}
        hints = []
        seen_joins = set()  # Avoid duplicates
        
        # =================================================================
        # v3.0: Context Graph joins (highest priority)
        # =================================================================
        if self.table_selector and hasattr(self.table_selector, 'get_join_path'):
            table_list = list(table_names)
            for i, t1 in enumerate(table_list):
                for t2 in table_list[i+1:]:
                    join_path = self.table_selector.get_join_path(t1, t2)
                    if join_path:
                        sem_type = join_path.get('semantic_type', '')
                        from_col = join_path.get('from_column', '')
                        to_col = join_path.get('to_column', '')
                        join_key = tuple(sorted([f"{t1}.{from_col}", f"{t2}.{to_col}"]))
                        
                        if join_key not in seen_joins:
                            seen_joins.add(join_key)
                            if join_path.get('join_type') == 'via_hub':
                                hint = f"  - {t1}.{from_col} → {t2}.{to_col} (via {join_path.get('via_hub')}, semantic: {sem_type})"
                            else:
                                hint = f"  - {t1}.{from_col} → {t2}.{to_col} (semantic: {sem_type})"
                            hints.append(hint)
                            logger.info(f"[SQL-GEN] Context Graph join: {hint}")
        
        # =================================================================
        # Legacy relationships from Supabase
        # =================================================================
        if self.relationships:
            for rel in self.relationships:
                # Handle both object and dict formats
                if hasattr(rel, 'from_table'):
                    # Object format
                    from_table = rel.from_table
                    from_col = rel.from_column
                    to_table = rel.to_table
                    to_col = rel.to_column
                    confidence = getattr(rel, 'confidence', 0.9)
                elif isinstance(rel, dict):
                    # Dict format from Supabase
                    from_table = rel.get('source_table', '')
                    from_col = rel.get('source_column', '')
                    to_table = rel.get('target_table', '')
                    to_col = rel.get('target_column', '')
                    confidence = rel.get('confidence', 0.9)
                else:
                    continue
                
                from_lower = from_table.lower() if from_table else ''
                to_lower = to_table.lower() if to_table else ''
                
                # Check if relationship involves selected tables
                if from_lower in table_names and to_lower in table_names:
                    join_key = tuple(sorted([f"{from_lower}.{from_col}", f"{to_lower}.{to_col}"]))
                    if join_key not in seen_joins:
                        seen_joins.add(join_key)
                        hint = f"  - {from_table}.{from_col} → {to_table}.{to_col}"
                        if confidence < 0.8:
                            hint += " (low confidence)"
                        hints.append(hint)
        
        if hints:
            return "\n\nRELATIONSHIPS (use for JOINs):\n" + "\n".join(hints)
        return ""

    def generate(self, question: str, context: Dict[str, Any]) -> Optional[Dict]:
        """
        Generate SQL for a question.
        
        v4.1: Check for cross-domain JOIN need BEFORE simple/complex decision
        v3.0: Uses entity_scope from context to add scoping filters.
        v9.1: Added defensive error handling
        
        Args:
            question: User's question
            context: Analysis context (domains, tables, entity_scope, etc.)
            
        Returns:
            Dict with sql, table, query_type, all_columns
            Or None if generation fails
        """
        try:
            logger.debug(f"[SQL-GEN] Generating for: {question[:60]}...")
            
            if not self.handler or not self.schema:
                return None
            
            tables = self.schema.get('tables', [])
            if not tables:
                return None
            
            # Get orchestrator
            orchestrator = self._get_orchestrator()
            if not orchestrator:
                return None
            
            q_lower = question.lower()
            
            # v3.0: Extract entity scope from context
            entity_scope = context.get('entity_scope') if context else None
            
            # Select relevant tables
            if self.table_selector:
                relevant_tables = self.table_selector.select(tables, question)
            else:
                relevant_tables = tables[:5]
            
            # =================================================================
            # v4.1: Check for cross-domain JOIN BEFORE simple/complex decision
            # This prevents simple queries from missing JOIN opportunities
            # =================================================================
            needs_join, additional_tables = self._needs_join(question, relevant_tables)
            
            # Track what happened in JOIN detection (for debugging via API response)
            self._join_detection_debug = {
                'needs_join': needs_join,
                'additional_tables_count': len(additional_tables),
                'schema_tables_count': len(self.schema.get('tables', [])),
            }
            
            if needs_join:
                # Add discovered tables
                if additional_tables:
                    existing_names = {t.get('table_name', '').lower() for t in relevant_tables}
                    for add_table in additional_tables:
                        if add_table.get('table_name', '').lower() not in existing_names:
                            relevant_tables = relevant_tables + [add_table]
                
                # Force complex path for JOIN queries
                result = self._generate_complex_with_join(question, relevant_tables, orchestrator, q_lower)
                if result and entity_scope:
                    result = self._apply_entity_scope(result, entity_scope)
                if result:
                    result['_join_debug'] = self._join_detection_debug
                return result
            
            # Try simple query path first (only if no JOIN needed)
            if self._is_simple_query(question) and relevant_tables:
                result = self._generate_simple(question, relevant_tables[0], orchestrator)
                if result:
                    result['_join_debug'] = self._join_detection_debug
                    if entity_scope:
                        result = self._apply_entity_scope(result, entity_scope)
                    return result
            
            # Complex query path
            result = self._generate_complex(question, relevant_tables, orchestrator, q_lower)
            
            if result and entity_scope:
                result = self._apply_entity_scope(result, entity_scope)
            
            if result:
                result['_join_debug'] = self._join_detection_debug
            
            return result
            
        except Exception as e:
            logger.error(f"[SQL-GEN] EXCEPTION in generate(): {e}")
            import traceback
            logger.error(f"[SQL-GEN] Traceback: {traceback.format_exc()}")
            return None
    
    def _apply_entity_scope(self, result: Dict, entity_scope: Dict) -> Dict:
        """
        Apply entity scoping filter to generated SQL.
        
        Uses Context Graph to find the scoping column in the target table
        and adds a WHERE clause.
        
        Args:
            result: SQL generation result with 'sql' key
            entity_scope: Dict with semantic_type, value, hub_column
        """
        sql = result.get('sql', '')
        if not sql:
            return result
        
        semantic_type = entity_scope.get('semantic_type')
        scope_value = entity_scope.get('value')
        hub_column = entity_scope.get('hub_column')
        scope_column = entity_scope.get('scope_column')  # v4.0: Direct column name
        
        if not scope_value:
            return result
        
        # Find the scoping column in the target table(s)
        # Look for columns with matching semantic_type in _column_mappings
        target_table = result.get('table', '')
        
        try:
            if self.handler and target_table:
                col_name = None
                
                # v4.0: First try direct column name match
                if scope_column:
                    check_col = self.handler.conn.execute(f"""
                        SELECT column_name FROM (
                            SELECT column_name FROM pragma_table_info('{target_table}')
                        ) WHERE LOWER(column_name) = LOWER(?)
                    """, [scope_column]).fetchone()
                    if check_col:
                        col_name = check_col[0]
                        logger.warning(f"[SQL-GEN] Found scope column directly: {col_name}")
                
                # Fallback: Find column by semantic type mapping
                if not col_name and semantic_type:
                    scope_col = self.handler.conn.execute("""
                        SELECT original_column FROM _column_mappings
                        WHERE LOWER(table_name) = LOWER(?)
                        AND semantic_type = ?
                        LIMIT 1
                    """, [target_table, semantic_type]).fetchone()
                    
                    if scope_col:
                        col_name = scope_col[0]
                
                if col_name:
                    # Add WHERE clause
                    scope_filter = f'"{col_name}" = \'{scope_value}\''
                    sql = self._inject_where_clause(sql, scope_filter)
                    result['sql'] = sql
                    result['entity_scope_applied'] = {
                        'column': col_name,
                        'value': scope_value,
                        'semantic_type': semantic_type
                    }
                    logger.warning(f"[SQL-GEN] Applied entity scope: {col_name}='{scope_value}'")
                else:
                    # Fallback: try hub_column directly if table has it
                    if hub_column:
                        columns = result.get('all_columns', set())
                        if hub_column in columns or hub_column.lower() in {c.lower() for c in columns}:
                            scope_filter = f'"{hub_column}" = \'{scope_value}\''
                            sql = self._inject_where_clause(sql, scope_filter)
                            result['sql'] = sql
                            result['entity_scope_applied'] = {
                                'column': hub_column,
                                'value': scope_value,
                                'semantic_type': semantic_type
                            }
                            logger.warning(f"[SQL-GEN] Applied entity scope (fallback): {hub_column}='{scope_value}'")
        except Exception as e:
            logger.debug(f"[SQL-GEN] Entity scope application failed: {e}")
        
        return result
    
    def _get_orchestrator(self):
        """Get or create LLMOrchestrator."""
        if self._orchestrator:
            return self._orchestrator
        
        try:
            try:
                from utils.llm_orchestrator import LLMOrchestrator
            except ImportError:
                from backend.utils.llm_orchestrator import LLMOrchestrator
            
            self._orchestrator = LLMOrchestrator()
            return self._orchestrator
        except Exception as e:
            logger.error(f"[SQL-GEN] Could not load LLMOrchestrator: {e}")
            return None
    
    def _is_simple_query(self, question: str) -> bool:
        """Detect if question is a simple single-table query."""
        q_lower = question.lower()
        
        # Simple patterns
        simple_patterns = [
            r'^show\s+(me\s+)?(the\s+)?',
            r'^list\s+(all\s+)?(the\s+)?',
            r'^what\s+are\s+(the\s+)?',
            r'^give\s+me\s+(the\s+)?',
            r'^display\s+(the\s+)?',
            r'^get\s+(me\s+)?(the\s+)?',
        ]
        
        # Complex patterns
        complex_patterns = [
            r'\bcompare\b',
            r'\bjoin\b',
            r'\bcross.?reference\b',
            r'\bvs\.?\b',
            r'\bversus\b',
            r'\bfrom\s+\w+\s+and\s+',
            r'\bbetween\s+\w+\s+and\s+',
        ]
        
        for pattern in complex_patterns:
            if re.search(pattern, q_lower):
                return False
        
        for pattern in simple_patterns:
            if re.search(pattern, q_lower):
                return True
        
        return len(question.split()) <= 8
    
    def _detect_value_filters(self, question: str, table_name: str) -> List[Dict]:
        """
        Detect filters based on question keywords matching column VALUES.
        
        If question contains "SUI" and the table has a column where "SUI" is a value,
        return a filter like {"column": "type_of_tax", "value": "SUI"}.
        
        This is the key to smart SQL generation - we filter BEFORE sending to LLM.
        """
        filters = []
        
        logger.warning(f"[SQL-GEN] Detecting value filters for: {question[:40]}... table={table_name[-40:]}")
        
        if not self.handler or not hasattr(self.handler, 'conn'):
            logger.warning("[SQL-GEN] No handler.conn - skipping filter detection")
            return filters
        
        # Extract significant words from question
        q_lower = question.lower()
        words = re.findall(r'\b[a-z]+\b', q_lower)
        skip_words = {'the', 'a', 'an', 'is', 'are', 'my', 'our', 'your', 'what', 
                     'how', 'show', 'list', 'get', 'find', 'check', 'verify',
                     'configured', 'setup', 'correct', 'correctly', 'valid'}
        
        significant_words = [w for w in words if len(w) >= 3 and w not in skip_words]
        
        logger.warning(f"[SQL-GEN] Significant words from question: {significant_words}")
        
        if not significant_words:
            logger.warning("[SQL-GEN] No significant words found - skipping filter detection")
            return filters
        
        try:
            # Check column profiles for value matches
            profiles = self.handler.conn.execute("""
                SELECT column_name, distinct_values
                FROM _column_profiles 
                WHERE LOWER(table_name) = LOWER(?)
                AND distinct_values IS NOT NULL
                AND distinct_values != '[]'
            """, [table_name]).fetchall()
            
            logger.warning(f"[SQL-GEN] Found {len(profiles)} column profiles with values")
            
            for col_name, distinct_values_json in profiles:
                if not distinct_values_json:
                    continue
                
                try:
                    values = json.loads(distinct_values_json)
                    
                    # Log first few values for debugging
                    sample_vals = [str(v.get('value', v) if isinstance(v, dict) else v)[:30] for v in values[:5]]
                    logger.warning(f"[SQL-GEN] Column {col_name}: {len(values)} values, sample: {sample_vals}")
                    
                    for val_info in values:
                        val = str(val_info.get('value', '') if isinstance(val_info, dict) else val_info).lower().strip()
                        
                        if not val or len(val) < 2:
                            continue
                        
                        # Check if any question word matches this value
                        for word in significant_words:
                            # Match: exact, or word is substring of value, or value is substring of word
                            if word == val or (len(word) >= 3 and word in val) or (len(val) >= 3 and val in word):
                                filters.append({
                                    "column": col_name,
                                    "value": val_info.get('value', val_info) if isinstance(val_info, dict) else val_info,
                                    "match_word": word
                                })
                                logger.warning(f"[SQL-GEN] FILTER DETECTED: {col_name} contains '{val}' (from '{word}')")
                                break
                                
                except (json.JSONDecodeError, TypeError):
                    pass
                    
        except Exception as e:
            logger.warning(f"[SQL-GEN] Filter detection failed: {e}")
        
        logger.warning(f"[SQL-GEN] Detected {len(filters)} filters: {[f['column'] + '=' + str(f['value'])[:20] for f in filters]}")
        return filters

    def _build_smart_fallback(self, table_name: str, filters: List[Dict], 
                               valid_columns: Set[str]) -> str:
        """
        Build a smart fallback SQL with filters instead of SELECT *.
        
        If we detected that the question is about "SUI", generate:
        SELECT * FROM table WHERE type_of_tax ILIKE '%SUI%' LIMIT 100
        
        This gives the synthesis LLM clean, relevant data instead of garbage.
        """
        # Start with basic select
        base = f'SELECT * FROM "{table_name}"'
        
        # Group filters by column - only keep ONE filter per column (prefer shorter/more specific values)
        column_filters = {}
        for f in filters:
            col = f.get('column', '')
            val = str(f.get('value', ''))
            if col in valid_columns and val:
                # If column already has a filter, keep the shorter (more specific) value
                if col not in column_filters or len(val) < len(column_filters[col]):
                    column_filters[col] = val
        
        # Build WHERE clauses - one per column, combined with OR (any match is useful)
        where_clauses = []
        for col, val in list(column_filters.items())[:2]:  # Max 2 columns
            where_clauses.append(f'"{col}" ILIKE \'%{val}%\'')
        
        if where_clauses:
            base += " WHERE (" + " OR ".join(where_clauses) + ")"
            logger.warning(f"[SQL-GEN] Smart WHERE: ({' OR '.join(where_clauses)})")
        
        base += " LIMIT 100"
        
        return base
    
    def _generate_simple(self, question: str, table: Dict, 
                        orchestrator) -> Optional[Dict]:
        """
        Generate SQL for simple single-table query using CREATE TABLE format.
        
        v2.0: Now detects value-based filters from question keywords.
        If question mentions "SUI", we add WHERE type_of_tax ILIKE '%SUI%'.
        """
        table_name = table.get('table_name', '')
        
        # Create short alias
        short_alias = self._create_short_alias(table_name)
        
        # Build CREATE TABLE schema
        schema_str, valid_columns = self._build_create_table_schema(table_name, short_alias)
        
        if not schema_str or not valid_columns:
            return None
        
        logger.warning(f"[SQL-GEN] Simple query: {len(valid_columns)} columns")
        
        self._table_aliases = {short_alias: table_name}
        
        # =====================================================================
        # SMART FILTER DETECTION - the key to useful queries
        # =====================================================================
        detected_filters = self._detect_value_filters(question, table_name)
        
        # Build filter hints for LLM prompt
        filter_hints = ""
        if detected_filters:
            filter_hints = "\n### Filter Hints (from question keywords)\n"
            for f in detected_filters[:3]:
                col = f.get('column', '')
                val = f.get('value', '')
                filter_hints += f"- Column '{col}' contains value '{val}' - consider filtering on this\n"
        
        # =====================================================================
        # v5.0: SEMANTIC TRANSLATIONS - tell LLM what terms mean
        # =====================================================================
        translation_hints = self._build_translation_hints(question)
        
        prompt = f"""### Task
Generate a SQL query to answer: {question}

### Database Schema
{schema_str}
{filter_hints}{translation_hints}
### Rules
- Use ONLY columns from the schema above
- Table name: {short_alias}
- For text search, use ILIKE '%term%'
- Use the FILTER TRANSLATIONS below to convert user terms to correct column values
- Return relevant columns, not SELECT *
- Add LIMIT 100

### Answer
Given the schema, here is the SQL query:
```sql
SELECT"""
        
        result = orchestrator.generate_sql(prompt, valid_columns)
        
        if result.get('success') and result.get('sql'):
            sql = self._clean_and_process_sql(result['sql'], short_alias, 
                                               table_name, valid_columns)
            
            if sql:
                invalid = self._check_sql_columns(sql, valid_columns)
                if not invalid:
                    return {
                        'sql': sql,
                        'table': table_name,  # v4.4 FIX: Use full table name, not alias
                        'query_type': 'list',
                        'all_columns': valid_columns
                    }
                else:
                    logger.warning(f"[SQL-GEN] Invalid columns: {invalid}")
        
        # =====================================================================
        # SMART FALLBACK - use detected filters instead of SELECT *
        # =====================================================================
        logger.warning(f"[SQL-GEN] LLM failed, using SMART fallback for {table_name[-40:]}")
        fallback_sql = self._build_smart_fallback(table_name, detected_filters, valid_columns)
        logger.warning(f"[SQL-GEN] Fallback SQL: {fallback_sql[:100]}...")
        
        return {
            'sql': fallback_sql,
            'table': table_name,  # v4.4 FIX: Use full table name, not alias
            'query_type': 'list',
            'all_columns': valid_columns
        }
    
    def _generate_complex_with_join(self, question: str, tables: List[Dict],
                                    orchestrator, q_lower: str) -> Optional[Dict]:
        """
        Generate SQL for a query that we already know needs a JOIN.
        
        v4.1: Called when cross-domain JOIN is detected before simple/complex decision.
        Tables have already been augmented with discovered tables.
        """
        logger.warning(f"[SQL-GEN] Generating JOIN query with {len(tables)} tables")
        return self._generate_complex(question, tables, orchestrator, q_lower)
    
    def _generate_complex(self, question: str, tables: List[Dict],
                         orchestrator, q_lower: str) -> Optional[Dict]:
        """Generate SQL for complex multi-table query."""
        
        # =================================================================
        # v4.1: Check if JOIN is needed FIRST (before building schema)
        # This allows us to add missing tables to the query
        # =================================================================
        needs_join, additional_tables = self._needs_join(question, tables)
        
        # Add any additional tables that were discovered by semantic analysis
        if additional_tables:
            logger.warning(f"[SQL-GEN] Adding {len(additional_tables)} tables discovered by semantic JOIN detection")
            # Avoid duplicates
            existing_names = {t.get('table_name', '').lower() for t in tables}
            for add_table in additional_tables:
                if add_table.get('table_name', '').lower() not in existing_names:
                    tables = tables + [add_table]
                    logger.warning(f"[SQL-GEN] ➕ Added table: {add_table.get('table_name', '')[-40:]}")
        
        # Build schema with aliases
        tables_info = []
        all_columns: Set[str] = set()
        table_aliases: Dict[str, str] = {}
        used_aliases: Set[str] = set()
        primary_table = None
        
        for i, table in enumerate(tables):
            table_name = table.get('table_name', '')
            columns = table.get('columns', [])
            col_names = self._extract_column_names(columns)
            row_count = table.get('row_count', 0)
            
            all_columns.update(col_names)
            
            short_alias = self._create_short_alias(table_name, used_aliases)
            used_aliases.add(short_alias)
            table_aliases[short_alias] = table_name
            
            if i == 0:
                primary_table = short_alias
            
            # Sample for primary table
            sample_str = ""
            if i == 0:
                sample_str = self._get_sample_str(table_name)
            
            col_str = ', '.join(col_names[:15])
            if len(col_names) > 15:
                col_str += f" (+{len(col_names) - 15} more)"
            
            tables_info.append(
                f"Table: {short_alias}\n  Columns: {col_str}\n  Rows: {row_count}{sample_str}"
            )
        
        self._table_aliases = table_aliases
        schema_text = '\n\n'.join(tables_info)
        
        # Build semantic hints
        semantic_text = self._build_semantic_hints(tables, primary_table, q_lower)
        
        # Build relationship hints if JOIN is needed
        relationship_hints = ""
        
        if needs_join and len(tables) > 1:
            relationship_hints = self._build_relationship_hints(tables)
            if relationship_hints:
                logger.info("[SQL-GEN] Including relationship hints for JOIN query")
        
        # Build query hints
        query_hints = self._build_query_hints(q_lower, primary_table)
        query_hint = ""
        if query_hints:
            query_hint = "\n\nHINTS:\n" + "\n".join(f"- {h}" for h in query_hints)
        
        # Build filter instructions
        filter_instructions = self._build_filter_instructions(tables)
        
        # Adjust rules based on whether JOIN is needed
        if needs_join and relationship_hints:
            # Determine JOIN strategy:
            # - INNER JOIN when filtering by joined table (WHERE uses joined column)
            # - LEFT JOIN when just enriching output (lookup descriptions)
            join_instruction = """4. JOIN STRATEGY:
   - Use INNER JOIN when filtering BY a related table (e.g., "employees in Texas" needs location table)
   - Use LEFT JOIN when only enriching output with descriptions (e.g., adding location names to employee list)
   - If WHERE clause references joined table → INNER JOIN
   - If just adding columns for display → LEFT JOIN"""
            
            rules = f"""RULES:
1. Use ONLY columns from SCHEMA - never invent columns
2. DO NOT add WHERE for status/active/termed - filters injected automatically
3. For "show X by Y" queries: SELECT Y, COUNT(*) FROM table GROUP BY Y
{join_instruction}
5. ILIKE for text matching"""
        else:
            rules = """RULES:
1. Use ONLY columns from SCHEMA - never invent columns
2. DO NOT add WHERE for status/active/termed - filters injected automatically
3. For "show X by Y" queries: SELECT Y, COUNT(*) FROM table GROUP BY Y
4. Keep queries SIMPLE - avoid JOINs unless absolutely needed
5. ILIKE for text matching"""
        
        prompt = f"""SCHEMA:
{schema_text}{semantic_text}{relationship_hints}
{query_hint}

QUESTION: {question}

{rules}

SQL:"""
        
        result = orchestrator.generate_sql(prompt, all_columns)
        
        if result.get('success') and result.get('sql'):
            sql = result['sql'].strip()
            sql = self._clean_sql(sql)
            sql = self._expand_aliases(sql, table_aliases)
            sql = self._fix_column_names(sql, all_columns)
            sql = self._strip_status_filters(sql)
            
            if filter_instructions:
                if self._can_inject_filter(sql, filter_instructions, all_columns):
                    sql = self._inject_where_clause(sql, filter_instructions)
            
            sql = self._fix_state_names(sql)
            sql = self._fix_duckdb_syntax(sql, q_lower)
            sql = self._auto_add_grouping(sql, q_lower)
            
            query_type = self._detect_query_type(sql)
            
            table_match = re.search(r'FROM\s+"?([^"\s]+)"?', sql, re.IGNORECASE)
            table_name = table_match.group(1) if table_match else 'unknown'
            
            return {
                'sql': sql,
                'table': table_name,
                'query_type': query_type,
                'all_columns': all_columns
            }
        
        return None
    
    def fix_from_error(self, sql: str, error_msg: str, 
                       all_columns: Set[str]) -> Optional[str]:
        """Try to fix SQL based on error message."""
        # Fix VARCHAR with date functions
        if 'date_part' in error_msg.lower() and 'VARCHAR' in error_msg:
            pattern = r"EXTRACT\s*\(\s*(\w+)\s+FROM\s+(\w+)\s*\)"
            match = re.search(pattern, sql, re.IGNORECASE)
            if match:
                part, col = match.group(1), match.group(2)
                fixed = re.sub(pattern, f"EXTRACT({part} FROM TRY_CAST({col} AS DATE))",
                              sql, flags=re.IGNORECASE)
                logger.warning(f"[SQL-FIX] Added TRY_CAST for {col}")
                return fixed
        
        # Fix column not found
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
        
        # Get DuckDB suggestions
        candidates = []
        candidate_match = re.search(r'Candidate bindings:\s*([^\n]+)', error_msg)
        if candidate_match:
            candidates = re.findall(r'"([^"]+)"', candidate_match.group(1))
        
        # Find best match
        valid_cols = set(c.lower() for c in candidates) | set(c.lower() for c in all_columns)
        best_score = 0.4
        best_match = None
        
        for candidate in candidates:
            score = SequenceMatcher(None, bad_col.lower(), candidate.lower()).ratio()
            if score > best_score:
                best_score = score
                best_match = candidate
        
        if best_match:
            fixed = re.sub(r'\b' + re.escape(bad_col) + r'\b', 
                          f'"{best_match}"', sql, flags=re.IGNORECASE)
            logger.warning(f"[SQL-FIX] {bad_col} → {best_match}")
            return fixed
        
        return None
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _create_short_alias(self, table_name: str, 
                            used: Set[str] = None) -> str:
        """Create a short alias for a table name."""
        used = used or set()
        
        def ensure_valid(alias: str) -> str:
            if alias and alias[0].isdigit():
                return 't_' + alias
            return alias
        
        # Try last 2 segments
        parts = table_name.split('_')
        if len(parts) >= 2:
            candidate = '_'.join(parts[-2:])
            candidate = ensure_valid(candidate)[:25]
            if candidate not in used:
                return candidate
        
        # Try last segment
        if parts:
            candidate = ensure_valid(parts[-1])
            if candidate not in used:
                return candidate
        
        # Truncate
        base = ensure_valid(table_name[:15])
        if base not in used:
            return base
        
        for i in range(2, 100):
            candidate = f"{base}_{i}"
            if candidate not in used:
                return candidate
        
        return ensure_valid(table_name)
    
    def _extract_column_names(self, columns: List) -> List[str]:
        """Extract column names from various formats."""
        if not columns:
            return []
        if isinstance(columns[0], dict):
            return [c.get('name', str(c)) for c in columns]
        return [str(c) for c in columns]
    
    def _build_create_table_schema(self, table_name: str, 
                                   alias: str) -> Tuple[str, Set[str]]:
        """
        Build CREATE TABLE schema from DuckDB WITH intelligence.
        
        v5.0: Now includes filter categories, valid values, and descriptions
        from _column_profiles and _intelligence_lookups.
        """
        try:
            col_info = self.handler.conn.execute(
                f'PRAGMA table_info("{table_name}")'
            ).fetchall()
            
            if not col_info:
                return "", set()
            
            # ================================================================
            # STEP 1: Get column intelligence from _column_profiles
            # ================================================================
            column_intelligence = {}
            try:
                profiles = self.handler.conn.execute("""
                    SELECT column_name, filter_category, distinct_count, 
                           distinct_values, inferred_type
                    FROM _column_profiles
                    WHERE LOWER(table_name) = LOWER(?)
                """, [table_name]).fetchall()
                
                for col_name, filter_cat, distinct_count, distinct_vals, inferred_type in profiles:
                    column_intelligence[col_name] = {
                        'filter_category': filter_cat,
                        'distinct_count': distinct_count,
                        'distinct_values': distinct_vals,
                        'inferred_type': inferred_type
                    }
            except Exception as e:
                logger.debug(f"[SQL-GEN] Column profiles query failed: {e}")
            
            # ================================================================
            # STEP 2: Get value descriptions from _intelligence_lookups
            # ================================================================
            value_descriptions = {}
            try:
                lookups = self.handler.conn.execute("""
                    SELECT hub_column, lookup_data
                    FROM _intelligence_lookups
                    WHERE LOWER(table_name) = LOWER(?)
                """, [table_name]).fetchall()
                
                for hub_col, lookup_json in lookups:
                    if lookup_json:
                        import json
                        try:
                            value_descriptions[hub_col] = json.loads(lookup_json)
                        except:
                            pass
            except Exception as e:
                logger.debug(f"[SQL-GEN] Intelligence lookups query failed: {e}")
            
            columns = []
            valid_cols = set()
            filter_translations = []  # Build translation hints
            
            for row in col_info:
                col_name = row[1]
                col_type = row[2]
                
                if col_name.lower() in ['nan', 'none', ''] or col_name.lower().startswith('unnamed'):
                    continue
                
                valid_cols.add(col_name)
                
                # Simplify type
                simple_type = col_type.split('(')[0].upper()
                if simple_type in ['VARCHAR', 'TEXT', 'STRING']:
                    simple_type = 'TEXT'
                elif simple_type in ['INTEGER', 'INT', 'BIGINT', 'SMALLINT']:
                    simple_type = 'INTEGER'
                elif simple_type in ['FLOAT', 'DOUBLE', 'DECIMAL', 'NUMERIC', 'REAL']:
                    simple_type = 'DECIMAL'
                elif simple_type in ['BOOLEAN', 'BOOL']:
                    simple_type = 'BOOLEAN'
                elif 'DATE' in simple_type or 'TIME' in simple_type:
                    simple_type = 'DATE'
                
                # ============================================================
                # STEP 3: Add intelligence as column comments
                # ============================================================
                comment_parts = []
                intel = column_intelligence.get(col_name, {})
                
                # Filter category
                filter_cat = intel.get('filter_category')
                if filter_cat:
                    comment_parts.append(f"Filter:{filter_cat}")
                
                # Distinct values (if reasonable count)
                distinct_count = intel.get('distinct_count', 0)
                if distinct_count and distinct_count <= 20:
                    try:
                        import json
                        vals_json = intel.get('distinct_values', '[]')
                        if vals_json:
                            vals = json.loads(vals_json) if isinstance(vals_json, str) else vals_json
                            # Extract just values if they're dicts
                            val_list = []
                            for v in vals[:10]:
                                if isinstance(v, dict):
                                    val_list.append(str(v.get('value', v)))
                                else:
                                    val_list.append(str(v))
                            if val_list:
                                comment_parts.append(f"Values:[{','.join(val_list)}]")
                                
                                # Add descriptions if available
                                descs = value_descriptions.get(col_name, {})
                                if descs and filter_cat:
                                    desc_hints = []
                                    for val in val_list[:5]:
                                        desc = descs.get(val)
                                        if desc:
                                            desc_hints.append(f"{val}={desc}")
                                            # Build filter translation
                                            filter_translations.append({
                                                'category': filter_cat,
                                                'column': col_name,
                                                'value': val,
                                                'meaning': desc.lower()
                                            })
                                    if desc_hints:
                                        comment_parts.append(' | '.join(desc_hints[:3]))
                    except:
                        pass
                
                # Build column definition with comment
                if comment_parts:
                    columns.append(f"    {col_name} {simple_type},  -- {' | '.join(comment_parts)}")
                else:
                    columns.append(f"    {col_name} {simple_type}")
            
            schema = f"CREATE TABLE {alias} (\n" + "\n".join(columns) + "\n);"
            
            # Store filter translations for use in prompt
            self._filter_translations = filter_translations
            
            return schema, valid_cols
            
        except Exception as e:
            logger.error(f"[SQL-GEN] Error building schema: {e}")
            import traceback
            traceback.print_exc()
            return "", set()
    
    def _get_sample_str(self, table_name: str) -> str:
        """Get sample data string for prompt."""
        try:
            rows = self.handler.query(f'SELECT * FROM "{table_name}" LIMIT 2')
            if rows:
                cols = list(rows[0].keys())[:4]
                samples = []
                for col in cols:
                    vals = set(str(r.get(col, ''))[:15] for r in rows if r.get(col))
                    if vals:
                        samples.append(f"    {col}: {', '.join(list(vals)[:2])}")
                if samples:
                    return "\n  Sample:\n" + "\n".join(samples[:4])
        except Exception:
            pass
        return ""
    
    def _build_translation_hints(self, question: str) -> str:
        """
        Build semantic translation hints for the LLM.
        
        v5.0: Uses _filter_translations built during schema creation,
        plus common semantic mappings for status, location, etc.
        
        Returns a prompt section like:
        ### FILTER TRANSLATIONS (use these exact values)
        - "active" → employment_status_code = 'A'
        - "texas" → state_province_code = 'TX'
        """
        hints = []
        q_lower = question.lower()
        
        # ================================================================
        # 1. Use translations from schema building
        # ================================================================
        translations = getattr(self, '_filter_translations', [])
        for t in translations:
            meaning = t.get('meaning', '')
            if meaning and meaning in q_lower:
                col = t.get('column', '')
                val = t.get('value', '')
                hints.append(f'- "{meaning}" → {col} = \'{val}\'')
        
        # ================================================================
        # 2. Common status translations (fallback patterns)
        # ================================================================
        status_mappings = {
            'active': ['A', 'Active', 'ACT'],
            'terminated': ['T', 'Terminated', 'TERM', 'Inactive'],
            'leave': ['L', 'LOA', 'Leave'],
            'full time': ['FT', 'F', 'Full'],
            'part time': ['PT', 'P', 'Part'],
        }
        
        for term, vals in status_mappings.items():
            if term in q_lower:
                # Find status column from filter_candidates
                status_col = None
                if self.filter_candidates and 'status' in self.filter_candidates:
                    for cand in self.filter_candidates['status']:
                        status_col = cand.get('column_name', cand.get('column', ''))
                        break
                
                if status_col:
                    hints.append(f'- "{term}" → {status_col} = \'{vals[0]}\' (or one of: {vals})')
        
        # ================================================================
        # 3. Geographic translations (US states)
        # ================================================================
        state_mappings = {
            'texas': 'TX', 'california': 'CA', 'new york': 'NY', 'florida': 'FL',
            'illinois': 'IL', 'pennsylvania': 'PA', 'ohio': 'OH', 'georgia': 'GA',
            'north carolina': 'NC', 'michigan': 'MI', 'new jersey': 'NJ',
            'virginia': 'VA', 'washington': 'WA', 'arizona': 'AZ', 'massachusetts': 'MA',
            'tennessee': 'TN', 'indiana': 'IN', 'missouri': 'MO', 'maryland': 'MD',
            'wisconsin': 'WI', 'colorado': 'CO', 'minnesota': 'MN', 'alabama': 'AL',
            'south carolina': 'SC', 'louisiana': 'LA', 'kentucky': 'KY', 'oregon': 'OR',
            'oklahoma': 'OK', 'connecticut': 'CT', 'iowa': 'IA', 'nevada': 'NV',
            'arkansas': 'AR', 'utah': 'UT', 'mississippi': 'MS', 'kansas': 'KS',
            'new mexico': 'NM', 'nebraska': 'NE', 'idaho': 'ID', 'hawaii': 'HI',
            'maine': 'ME', 'montana': 'MT', 'delaware': 'DE', 'south dakota': 'SD',
            'north dakota': 'ND', 'alaska': 'AK', 'vermont': 'VT', 'wyoming': 'WY',
            'west virginia': 'WV', 'rhode island': 'RI', 'new hampshire': 'NH',
            # Canadian provinces
            'ontario': 'ON', 'quebec': 'QC', 'british columbia': 'BC', 'alberta': 'AB',
            'manitoba': 'MB', 'saskatchewan': 'SK', 'nova scotia': 'NS',
            'new brunswick': 'NB', 'newfoundland': 'NL', 'prince edward island': 'PE',
        }
        
        for state, code in state_mappings.items():
            if state in q_lower:
                # Find location column
                loc_col = None
                if self.filter_candidates and 'location' in self.filter_candidates:
                    for cand in self.filter_candidates['location']:
                        col = cand.get('column_name', cand.get('column', ''))
                        if 'state' in col.lower() or 'province' in col.lower():
                            loc_col = col
                            break
                
                if loc_col:
                    hints.append(f'- "{state}" → {loc_col} = \'{code}\'')
                else:
                    hints.append(f'- "{state}" → state/province column = \'{code}\'')
        
        # ================================================================
        # Build the hints section
        # ================================================================
        if hints:
            return "\n### FILTER TRANSLATIONS (use these exact values)\n" + "\n".join(hints) + "\n"
        
        return ""
    
    def _build_semantic_hints(self, tables: List[Dict], primary_table: str,
                             q_lower: str) -> str:
        """Build semantic column hints from filter candidates."""
        hints = []
        
        if not self.filter_candidates:
            return ""
        
        for category, candidates in self.filter_candidates.items():
            if not candidates:
                continue
            
            if category == 'status':
                # Find status columns
                for cand in candidates:
                    col = cand.get('column_name', cand.get('column', ''))
                    table = cand.get('table_name', '').split('_')[-1]
                    if 'employment_status' in col.lower():
                        hints.append(f"- For employee status: use {table}.{col}")
                        break
            else:
                best = candidates[0]
                col = best.get('column_name', best.get('column', ''))
                table = best.get('table_name', '').split('_')[-1]
                
                if category == 'location':
                    hints.append(f"- For location/state: use {table}.{col}")
                elif category == 'company':
                    hints.append(f"- For company: use {table}.{col}")
        
        if hints:
            hints.insert(0, "NOTE: Status filtering applied automatically")
            return "\n\nCOLUMN USAGE:\n" + "\n".join(hints)
        
        return ""
    
    def _build_query_hints(self, q_lower: str, primary_table: str) -> List[str]:
        """Build query hints based on question patterns."""
        hints = []
        
        if re.search(r'\bshow\s+\w+\s+\w*\s*by\s+\w+', q_lower):
            hints.append(f"Use simple aggregation: SELECT column, COUNT(*) FROM {primary_table} GROUP BY column")
            hints.append("Do NOT use JOINs for simple counts")
        
        if 'how many' in q_lower or 'count' in q_lower:
            hints.append(f"For COUNT: SELECT COUNT(*) FROM \"{primary_table}\"")
        
        return hints
    
    def _build_filter_instructions(self, tables: List[Dict]) -> str:
        """Build filter instructions from confirmed facts."""
        if not self.confirmed_facts:
            return ""
        
        status = self.confirmed_facts.get('status')
        if not status or status == 'all':
            return ""
        
        # Normalize status to lowercase for comparison
        status_lower = str(status).lower().strip()
        
        # Find status column
        for category, candidates in self.filter_candidates.items():
            if category != 'status':
                continue
            for cand in candidates:
                col = cand.get('column_name', cand.get('column', ''))
                vals = cand.get('value_distribution', {})
                
                # v9.1: Handle both VALUE codes ('A') and LABELS ('active')
                # Check if status IS already the value code (e.g., 'A')
                if status in vals:
                    return f'"{col}" = \'{status}\''
                
                # Check if status is a friendly label
                if status_lower in ['active', 'a']:
                    # Find active code
                    for val, count in vals.items():
                        if val.upper() in ['A', 'ACTIVE', 'ACT']:
                            return f'"{col}" = \'{val}\''
                elif status_lower in ['termed', 'terminated', 't']:
                    for val, count in vals.items():
                        if val.upper() in ['T', 'TERM', 'TERMINATED']:
                            return f'"{col}" = \'{val}\''
                elif status_lower in ['leave', 'loa', 'l']:
                    for val, count in vals.items():
                        if val.upper() in ['L', 'LOA', 'LEAVE']:
                            return f'"{col}" = \'{val}\''
        
        return ""
    
    def _clean_sql(self, sql: str) -> str:
        """Clean markdown and formatting from SQL."""
        if '```' in sql:
            sql = re.sub(r'```sql\s*', '', sql, flags=re.IGNORECASE)
            sql = re.sub(r'```\s*$', '', sql)
            sql = sql.replace('```', '')
        return sql.strip()
    
    def _clean_and_process_sql(self, sql: str, alias: str, 
                               full_name: str, valid_columns: Set[str]) -> str:
        """Clean and process SQL for simple queries."""
        sql = self._clean_sql(sql)
        
        if not sql.upper().startswith('SELECT') and not sql.upper().startswith('WITH'):
            sql = 'SELECT ' + sql
        
        # Expand alias
        sql = re.sub(
            rf'\bFROM\s+{re.escape(alias)}\b(?!\s+AS)',
            f'FROM "{full_name}" AS {alias}',
            sql, flags=re.IGNORECASE
        )
        
        return sql
    
    def _expand_aliases(self, sql: str, aliases: Dict[str, str]) -> str:
        """Expand short aliases to full table names."""
        for short, full in aliases.items():
            sql = re.sub(
                rf'\bFROM\s+{re.escape(short)}\b(?!\.)(?!\s+AS)',
                f'FROM "{full}" AS {short}',
                sql, flags=re.IGNORECASE
            )
            sql = re.sub(
                rf'\bJOIN\s+{re.escape(short)}\b(?!\.)(?!\s+AS)',
                f'JOIN "{full}" AS {short}',
                sql, flags=re.IGNORECASE
            )
        return sql
    
    def _fix_column_names(self, sql: str, all_columns: Set[str]) -> str:
        """Fix generic column names using mappings."""
        if not self._column_mappings:
            return sql
        
        all_lower = {c.lower() for c in all_columns}
        
        for generic, actual in self._column_mappings.items():
            if generic.lower() != actual.lower() and actual.lower() in all_lower:
                pattern = rf'\b{re.escape(generic)}\b(?!\w)'
                if re.search(pattern, sql, re.IGNORECASE):
                    sql = re.sub(pattern, actual, sql, flags=re.IGNORECASE)
                    logger.warning(f"[SQL-GEN] Fixed: {generic} → {actual}")
        
        return sql
    
    def _strip_status_filters(self, sql: str) -> str:
        """Remove LLM-generated status filters (we inject our own)."""
        patterns = [
            r"\bWHERE\s+\w*\.?employment_status_code\s*=\s*'[^']*'\s*",
            r"\bAND\s+\w*\.?employment_status_code\s*=\s*'[^']*'\s*",
            r"\bWHERE\s+\w*\.?employment_status\s*=\s*'[^']*'\s*",
            r"\bAND\s+\w*\.?employment_status\s*=\s*'[^']*'\s*",
        ]
        
        for pattern in patterns:
            if re.search(pattern, sql, re.IGNORECASE):
                sql = re.sub(pattern, 'WHERE ', sql, count=1, flags=re.IGNORECASE)
                sql = re.sub(r'\bWHERE\s+WHERE\b', 'WHERE', sql, flags=re.IGNORECASE)
                sql = re.sub(r'\bWHERE\s+AND\b', 'WHERE', sql, flags=re.IGNORECASE)
                sql = re.sub(r'\bWHERE\s+GROUP\b', 'GROUP', sql, flags=re.IGNORECASE)
                sql = re.sub(r'\bWHERE\s+ORDER\b', 'ORDER', sql, flags=re.IGNORECASE)
                sql = re.sub(r'\bWHERE\s*$', '', sql, flags=re.IGNORECASE)
        
        return sql
    
    def _can_inject_filter(self, sql: str, filter_str: str, 
                          all_columns: Set[str]) -> bool:
        """Check if filter can be injected (column exists)."""
        col_match = re.search(r'"([^"]+)"', filter_str)
        if col_match:
            col = col_match.group(1)
            return col in all_columns or col.lower() in {c.lower() for c in all_columns}
        return False
    
    def _inject_where_clause(self, sql: str, filter_clause: str) -> str:
        """Inject WHERE clause into SQL."""
        sql_upper = sql.upper()
        
        if 'WHERE' in sql_upper:
            # Add to existing WHERE
            match = re.search(r'\bWHERE\b', sql, re.IGNORECASE)
            if match:
                pos = match.end()
                sql = sql[:pos] + f" {filter_clause} AND" + sql[pos:]
        else:
            # Add new WHERE before GROUP BY, ORDER BY, or LIMIT
            for keyword in ['GROUP BY', 'ORDER BY', 'LIMIT']:
                if keyword in sql_upper:
                    pos = sql_upper.index(keyword)
                    sql = sql[:pos] + f" WHERE {filter_clause} " + sql[pos:]
                    break
            else:
                sql = sql.rstrip(';') + f" WHERE {filter_clause}"
        
        return sql
    
    def _fix_state_names(self, sql: str) -> str:
        """Convert state names to codes in ILIKE clauses."""
        for name, code in US_STATE_CODES.items():
            pattern = rf"ILIKE\s+'%{name}%'"
            if re.search(pattern, sql, re.IGNORECASE):
                sql = re.sub(pattern, f"ILIKE '%{code}%'", sql, flags=re.IGNORECASE)
        return sql
    
    def _fix_duckdb_syntax(self, sql: str, q_lower: str) -> str:
        """Fix DuckDB-specific syntax issues."""
        # MONTH(x) → EXTRACT(MONTH FROM x)
        sql = re.sub(r'\bMONTH\s*\(\s*([^)]+)\s*\)', 
                    r'EXTRACT(MONTH FROM \1)', sql, flags=re.IGNORECASE)
        sql = re.sub(r'\bYEAR\s*\(\s*([^)]+)\s*\)', 
                    r'EXTRACT(YEAR FROM \1)', sql, flags=re.IGNORECASE)
        
        # Wrap date columns in TRY_CAST
        sql = re.sub(
            r"DATE_TRUNC\s*\(\s*'(\w+)'\s*,\s*(\w*date\w*)\s*\)",
            r"DATE_TRUNC('\1', TRY_CAST(\2 AS DATE))",
            sql, flags=re.IGNORECASE
        )
        sql = re.sub(
            r"EXTRACT\s*\(\s*(\w+)\s+FROM\s+(\w*date\w*)\s*\)",
            r"EXTRACT(\1 FROM TRY_CAST(\2 AS DATE))",
            sql, flags=re.IGNORECASE
        )
        
        # For month queries, use strftime for year-month format
        if 'by month' in q_lower or 'per month' in q_lower:
            sql = re.sub(
                r"EXTRACT\s*\(\s*MONTH\s+FROM\s+TRY_CAST\s*\(\s*([^)]+)\s+AS\s+DATE\s*\)\s*\)",
                r"strftime('%Y-%m', TRY_CAST(\1 AS DATE))",
                sql, flags=re.IGNORECASE
            )
        
        return sql
    
    def _auto_add_grouping(self, sql: str, q_lower: str) -> str:
        """Auto-add GROUP BY and ORDER BY if missing."""
        sql_upper = sql.upper()
        
        # Add GROUP BY if needed
        if 'GROUP BY' not in sql_upper:
            group_match = re.search(r'\bby\s+(month|year|state|location|company)\b', q_lower)
            if group_match:
                alias_match = re.search(rf'\bAS\s+(\w*{group_match.group(1)}\w*)', 
                                       sql, re.IGNORECASE)
                if alias_match:
                    alias = alias_match.group(1)
                    if 'ORDER BY' in sql_upper:
                        sql = re.sub(r'\bORDER BY\b', f'GROUP BY {alias} ORDER BY', 
                                    sql, flags=re.IGNORECASE)
                    else:
                        sql = sql.rstrip(';') + f' GROUP BY {alias}'
        
        # Add ORDER BY if needed
        sql_upper = sql.upper()
        if 'GROUP BY' in sql_upper and 'ORDER BY' not in sql_upper:
            if 'month' in q_lower or 'year' in q_lower:
                month_match = re.search(r'\bAS\s+(\w*month\w*)', sql, re.IGNORECASE)
                if month_match:
                    sql = sql.rstrip(';') + f' ORDER BY {month_match.group(1)} ASC'
            else:
                count_match = re.search(r'COUNT\s*\([^)]*\)(?:\s+AS\s+(\w+))?', 
                                       sql, re.IGNORECASE)
                if count_match:
                    count_alias = count_match.group(1) or 'COUNT(*)'
                    sql = sql.rstrip(';') + f' ORDER BY {count_alias} DESC'
        
        return sql
    
    def _detect_query_type(self, sql: str) -> str:
        """Detect query type from SQL."""
        sql_upper = sql.upper()
        has_group = 'GROUP BY' in sql_upper
        
        if has_group:
            return 'group'
        elif 'COUNT(' in sql_upper:
            return 'count'
        elif 'SUM(' in sql_upper:
            return 'sum'
        elif 'AVG(' in sql_upper:
            return 'average'
        return 'list'
    
    def _check_sql_columns(self, sql: str, valid_columns: Set[str]) -> List[str]:
        """Check SQL for invalid column references."""
        if not valid_columns:
            return []
        
        valid_lower = {c.lower() for c in valid_columns}
        tokens = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', sql)
        invalid = []
        
        for token in tokens:
            token_lower = token.lower()
            if token_lower in SQL_KEYWORDS:
                continue
            if token_lower in valid_lower:
                continue
            if len(token) < 4:
                continue
            if token_lower.startswith('t_'):
                continue
            
            if '_' in token or token_lower.endswith('_code') or token_lower.endswith('_id'):
                if token_lower not in valid_lower:
                    invalid.append(token)
        
        return list(set(invalid))[:5]
