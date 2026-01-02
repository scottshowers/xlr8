"""
XLR8 Intelligence Engine - SQL Generator v2.0
==============================================

Generates SQL queries from natural language questions.

v2.0 CHANGES:
- SMART FILTER DETECTION: Detects question keywords that match column VALUES
  and injects WHERE clauses (e.g., "SUI rates" → WHERE type_of_tax ILIKE '%SUI%')
- SMART FALLBACK: When LLM fails, uses filtered query instead of SELECT *
- Filter hints in LLM prompt guide better query generation

Key features:
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
    
    def _needs_join(self, question: str, tables: List[Dict]) -> bool:
        """
        Detect if a question requires a JOIN query.
        
        Returns True when:
        - User explicitly asks to combine/join/cross-reference data
        - Question references columns from multiple tables
        - Question asks for enriched/detailed data (e.g., "with department name")
        """
        q_lower = question.lower()
        
        # Explicit join patterns
        join_patterns = [
            r'\bwith\s+(their|the)\s+\w+\s+name',     # "employees with their department name"
            r'\bincluding\s+\w+\s+(name|description)', # "including location name"
            r'\bfull\s+(details|information)',         # "full details"
            r'\benriched?\b',                          # "enriched data"
            r'\bfrom\s+(\w+)\s+and\s+(\w+)',          # "from employees and departments"
            r'\bjoin\s+with\b',                        # "join with"
            r'\bcombine\b',                            # "combine"
            r'\bcross.?reference',                     # "cross-reference"
            r'\blink\w*\s+(to|with)',                 # "link to", "linked with"
        ]
        
        for pattern in join_patterns:
            if re.search(pattern, q_lower):
                logger.info(f"[SQL-GEN] JOIN needed: pattern '{pattern}' matched")
                return True
        
        return False
    
    def _build_relationship_hints(self, tables: List[Dict]) -> str:
        """
        Build relationship hints for the LLM prompt.
        
        Tells the LLM how tables can be joined based on detected relationships.
        
        Handles both:
        - Object format (from project_intelligence): rel.from_table, rel.to_table
        - Dict format (from Supabase): rel['source_table'], rel['target_table']
        """
        if not self.relationships:
            return ""
        
        table_names = {t.get('table_name', '').lower() for t in tables}
        
        hints = []
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
        
        Args:
            question: User's question
            context: Analysis context (domains, tables, etc.)
            
        Returns:
            Dict with sql, table, query_type, all_columns
            Or None if generation fails
        """
        logger.warning(f"[SQL-GEN] Starting generation for: {question[:60]}...")
        
        if not self.handler or not self.schema:
            logger.warning("[SQL-GEN] No handler or schema")
            return None
        
        tables = self.schema.get('tables', [])
        if not tables:
            return None
        
        # Get orchestrator
        orchestrator = self._get_orchestrator()
        if not orchestrator:
            return None
        
        q_lower = question.lower()
        
        # Select relevant tables
        if self.table_selector:
            relevant_tables = self.table_selector.select(tables, question)
        else:
            relevant_tables = tables[:5]
        
        # Try simple query path first
        if self._is_simple_query(question) and relevant_tables:
            result = self._generate_simple(question, relevant_tables[0], orchestrator)
            if result:
                return result
        
        # Complex query path
        return self._generate_complex(question, relevant_tables, orchestrator, q_lower)
    
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
        
        prompt = f"""### Task
Generate a SQL query to answer: {question}

### Database Schema
{schema_str}
{filter_hints}
### Rules
- Use ONLY columns from the schema above
- Table name: {short_alias}
- For text search, use ILIKE '%term%'
- If the question asks about specific values (like SUI, FED, etc.), ADD a WHERE clause
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
                        'table': short_alias,
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
            'table': short_alias,
            'query_type': 'list',
            'all_columns': valid_columns
        }
    
    def _generate_complex(self, question: str, tables: List[Dict],
                         orchestrator, q_lower: str) -> Optional[Dict]:
        """Generate SQL for complex multi-table query."""
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
        
        # Check if JOIN is needed and include relationship hints
        needs_join = self._needs_join(question, tables)
        relationship_hints = ""
        join_rules = ""
        
        if needs_join and len(tables) > 1:
            relationship_hints = self._build_relationship_hints(tables)
            if relationship_hints:
                join_rules = "\n4. Use LEFT JOIN with relationships provided above"
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
            rules = """RULES:
1. Use ONLY columns from SCHEMA - never invent columns
2. DO NOT add WHERE for status/active/termed - filters injected automatically
3. For "show X by Y" queries: SELECT Y, COUNT(*) FROM table GROUP BY Y
4. Use LEFT JOIN with the relationships provided to combine tables
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
        """Build CREATE TABLE schema from DuckDB."""
        try:
            col_info = self.handler.conn.execute(
                f'PRAGMA table_info("{table_name}")'
            ).fetchall()
            
            if not col_info:
                return "", set()
            
            columns = []
            valid_cols = set()
            
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
                
                columns.append(f"    {col_name} {simple_type}")
            
            schema = f"CREATE TABLE {alias} (\n" + ",\n".join(columns) + "\n);"
            return schema, valid_cols
            
        except Exception as e:
            logger.error(f"[SQL-GEN] Error building schema: {e}")
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
        except:
            pass
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
        
        # Find status column
        for category, candidates in self.filter_candidates.items():
            if category != 'status':
                continue
            for cand in candidates:
                col = cand.get('column_name', cand.get('column', ''))
                vals = cand.get('value_distribution', {})
                
                if status == 'active':
                    # Find active code
                    for val, count in vals.items():
                        if val.upper() in ['A', 'ACTIVE', 'ACT']:
                            return f'"{col}" = \'{val}\''
                elif status == 'termed':
                    for val, count in vals.items():
                        if val.upper() in ['T', 'TERM', 'TERMINATED']:
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
