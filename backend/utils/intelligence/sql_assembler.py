"""
XLR8 SQL Assembler - Deterministic SQL from Term Matches
=========================================================

This is the NEW primary path for SQL generation.

OLD: Score tables → LLM guesses SQL → hope it works
NEW: Term matches → lookup joins → assemble SQL → execute

NO LLM. NO SCORING. JUST LOOKUP + ASSEMBLY.

INPUTS:
- ParsedIntent: What the user wants (COUNT, LIST, SUM, COMPARE)
- List[TermMatch]: Resolved terms from term_index (table, column, operator, value)

OUTPUTS:
- Deterministic SQL string

FLOW:
1. Extract tables from term matches
2. If single table → simple query
3. If multiple tables → lookup join path by priority
4. Build SELECT based on intent type
5. Build WHERE from term matches
6. Return SQL

Author: XLR8 Team
Version: 1.0.0
Date: 2026-01-11
"""

import logging
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import duckdb

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

class QueryIntent(Enum):
    """What the user is trying to accomplish."""
    COUNT = "count"
    LIST = "list"
    LOOKUP = "lookup"
    SUM = "sum"
    COMPARE = "compare"
    FILTER = "filter"
    VALIDATE = "validate"
    UNKNOWN = "unknown"


@dataclass
class TermMatch:
    """A matched term with its SQL filter information."""
    term: str
    table_name: str
    column_name: str
    operator: str  # '=', 'ILIKE', '>', '<', 'IN'
    match_value: str
    domain: Optional[str] = None
    entity: Optional[str] = None
    confidence: float = 1.0
    term_type: str = 'value'


@dataclass
class JoinPath:
    """A join path between two tables."""
    table1: str
    column1: str
    table2: str
    column2: str
    semantic_type: str
    priority: int = 50


@dataclass
class AssembledQuery:
    """Result of SQL assembly."""
    sql: str
    tables: List[str]
    joins: List[JoinPath]
    filters: List[Dict]
    intent: QueryIntent
    primary_table: str
    success: bool = True
    error: Optional[str] = None


# =============================================================================
# SQL ASSEMBLER
# =============================================================================

class SQLAssembler:
    """
    Assembles SQL deterministically from term matches.
    
    NO LLM. NO SCORING. JUST LOOKUP + ASSEMBLY.
    
    Usage:
        assembler = SQLAssembler(conn, project)
        result = assembler.assemble(intent, term_matches, domain)
        if result.success:
            execute(result.sql)
    """
    
    def __init__(self, conn: duckdb.DuckDBPyConnection, project: str):
        self.conn = conn
        self.project = project
        
        # Cache for join paths
        self._join_cache: Dict[Tuple[str, str], JoinPath] = {}
        
        # Cache for entity primary tables
        self._entity_primary: Dict[str, str] = {}
        
        # Load caches
        self._load_entity_primaries()
    
    def _load_entity_primaries(self):
        """Load primary tables for each entity from _entity_tables."""
        try:
            # Case-insensitive project match
            results = self.conn.execute("""
                SELECT entity, table_name
                FROM _entity_tables
                WHERE LOWER(project) = ? AND is_primary = TRUE
            """, [self.project.lower()]).fetchall()
            
            for entity, table_name in results:
                self._entity_primary[entity] = table_name
                
            logger.warning(f"[SQL_ASSEMBLER] Loaded {len(self._entity_primary)} entity primaries")
        except Exception as e:
            logger.warning(f"[SQL_ASSEMBLER] Could not load entity primaries: {e}")
        
        # If no entity primaries loaded, find common tables from the database
        if not self._entity_primary:
            self._find_fallback_tables()
    
    def _find_fallback_tables(self):
        """Find actual table names when _entity_tables is empty."""
        project_lower = self.project.lower()
        try:
            # Look for personal/employee table (case-insensitive match on project_name)
            results = self.conn.execute("""
                SELECT table_name FROM _table_classifications
                WHERE LOWER(project_name) = ? AND LOWER(table_name) LIKE '%personal%'
                LIMIT 1
            """, [project_lower]).fetchall()
            
            if results:
                self._entity_primary['employee'] = results[0][0]
                self._entity_primary['demographics'] = results[0][0]
                logger.warning(f"[SQL_ASSEMBLER] Fallback: Found personal table: {results[0][0]}")
            
            # Look for deductions table
            results = self.conn.execute("""
                SELECT table_name FROM _table_classifications
                WHERE LOWER(project_name) = ? AND LOWER(table_name) LIKE '%deduction%'
                LIMIT 1
            """, [project_lower]).fetchall()
            
            if results:
                self._entity_primary['deductions'] = results[0][0]
                logger.warning(f"[SQL_ASSEMBLER] Fallback: Found deductions table: {results[0][0]}")
            
            # Look for earnings table
            results = self.conn.execute("""
                SELECT table_name FROM _table_classifications
                WHERE LOWER(project_name) = ? AND LOWER(table_name) LIKE '%earning%'
                LIMIT 1
            """, [project_lower]).fetchall()
            
            if results:
                self._entity_primary['earnings'] = results[0][0]
                logger.warning(f"[SQL_ASSEMBLER] Fallback: Found earnings table: {results[0][0]}")
                
        except Exception as e:
            logger.warning(f"[SQL_ASSEMBLER] Fallback table lookup failed: {e}")
    
    def assemble(self, 
                 intent: QueryIntent,
                 term_matches: List[TermMatch],
                 domain: str = None,
                 group_by_column: str = None) -> AssembledQuery:
        """
        Assemble SQL from intent and term matches.
        
        Args:
            intent: What the user wants (COUNT, LIST, etc.)
            term_matches: Resolved terms from term_index
            domain: Optional domain hint (demographics, earnings, etc.)
            group_by_column: Optional column for COMPARE queries
            
        Returns:
            AssembledQuery with SQL and metadata
        """
        logger.warning(f"[SQL_ASSEMBLER] Assembling {intent.value} query with {len(term_matches)} term matches")
        
        # Extract tables from term matches (before dedup)
        tables_from_matches = list(set(m.table_name for m in term_matches))
        
        # Determine primary table FIRST
        primary_table = self._get_primary_table(tables_from_matches, domain, term_matches)
        
        if not primary_table:
            return AssembledQuery(
                sql="",
                tables=[],
                joins=[],
                filters=[],
                intent=intent,
                primary_table="",
                success=False,
                error="Could not determine primary table"
            )
        
        # ==========================================================================
        # CRITICAL FIX: Deduplicate term matches by term
        # ==========================================================================
        # Problem: "texas" matches 4 tables → JOINs all 4 → WHERE requires TX everywhere → 0 rows
        # Solution: For each term, keep ONE match, preferring the primary table
        #
        # Example: "employees in Texas with 401k"
        #   BEFORE: texas→Personal, texas→WorkersComp, texas→CompanyTax, texas→Locations
        #   AFTER:  texas→Personal (primary), 401k→Deductions (needs JOIN)
        # ==========================================================================
        term_matches = self._deduplicate_term_matches(term_matches, primary_table)
        
        # Re-extract tables after deduplication
        tables_from_matches = list(set(m.table_name for m in term_matches))
        
        if len(tables_from_matches) == 1:
            logger.warning(f"[SQL_ASSEMBLER] SINGLE TABLE: All {len(term_matches)} matches from {tables_from_matches[0]}")
        else:
            logger.warning(f"[SQL_ASSEMBLER] CROSS-DOMAIN: {len(term_matches)} matches across {len(tables_from_matches)} tables: {tables_from_matches}")
        
        # Build query based on intent
        if intent == QueryIntent.COUNT:
            return self._build_count(primary_table, term_matches, tables_from_matches)
        elif intent == QueryIntent.LIST:
            return self._build_list(primary_table, term_matches, tables_from_matches)
        elif intent == QueryIntent.SUM:
            return self._build_sum(primary_table, term_matches, tables_from_matches)
        elif intent == QueryIntent.COMPARE:
            return self._build_compare(primary_table, term_matches, tables_from_matches, group_by_column)
        else:
            # Default to LIST for unknown intents
            return self._build_list(primary_table, term_matches, tables_from_matches)
    
    def _deduplicate_term_matches(self, 
                                   term_matches: List[TermMatch], 
                                   primary_table: str) -> List[TermMatch]:
        """
        Deduplicate term matches: one match per term, preferring primary table.
        
        This prevents over-constraining queries when the same term (e.g., "texas")
        matches multiple tables. We want:
        - "texas" in Personal.stateprovince (use this, ignore WorkersComp, CompanyTax, etc.)
        - "401k" only in Deductions (keep it, will need JOIN)
        
        Args:
            term_matches: All matches from term_index
            primary_table: The identified primary table for this query
            
        Returns:
            Deduplicated list with one match per term
        """
        # Group matches by term
        by_term: Dict[str, List[TermMatch]] = {}
        for match in term_matches:
            term_key = match.term.lower()
            if term_key not in by_term:
                by_term[term_key] = []
            by_term[term_key].append(match)
        
        # Select best match for each term
        deduplicated = []
        for term, matches in by_term.items():
            if len(matches) == 1:
                # Only one match, use it
                deduplicated.append(matches[0])
                continue
            
            # Multiple matches - prefer primary table
            primary_matches = [m for m in matches if m.table_name == primary_table]
            if primary_matches:
                # Use primary table match (take first if multiple columns match)
                best = primary_matches[0]
                logger.warning(f"[SQL_ASSEMBLER] DEDUP: '{term}' → using primary table {best.table_name}.{best.column_name} (dropped {len(matches)-1} other matches)")
                deduplicated.append(best)
            else:
                # Term not in primary - pick best non-primary match
                # Prefer higher confidence, then by table name for determinism
                sorted_matches = sorted(matches, key=lambda m: (-m.confidence, m.table_name))
                best = sorted_matches[0]
                logger.warning(f"[SQL_ASSEMBLER] DEDUP: '{term}' → using {best.table_name}.{best.column_name} (not in primary, will need JOIN)")
                deduplicated.append(best)
        
        logger.warning(f"[SQL_ASSEMBLER] Deduplicated: {len(term_matches)} matches → {len(deduplicated)} unique terms")
        return deduplicated
    
    def _get_primary_table(self, 
                           tables_from_matches: List[str],
                           domain: str,
                           term_matches: List[TermMatch]) -> Optional[str]:
        """
        Determine the primary table for the query.
        
        Priority:
        1. If domain specified and has primary table → use it
        2. Look for 'personal' table in matches (common primary for employee data)
        3. If single table in matches → use it
        4. If employee domain → Personal
        5. First table from matches
        """
        # Domain-based primary from entity tables
        if domain and domain in self._entity_primary:
            return self._entity_primary[domain]
        
        # FALLBACK: Look for 'personal' table in matches (very common primary)
        # This handles the case where entity_primary is empty
        for table in tables_from_matches:
            if 'personal' in table.lower():
                logger.warning(f"[SQL_ASSEMBLER] Found 'personal' table as primary: {table}")
                return table
        
        # Check for employee/demographics domain in matches
        for match in term_matches:
            if match.domain in ('demographics', 'employee'):
                if 'demographics' in self._entity_primary:
                    return self._entity_primary['demographics']
                if 'employee' in self._entity_primary:
                    return self._entity_primary['employee']
                # Fallback: look for personal table again
                for table in tables_from_matches:
                    if 'personal' in table.lower():
                        return table
        
        # Single table
        if len(tables_from_matches) == 1:
            return tables_from_matches[0]
        
        # Default to Personal for employee queries
        if any(m.entity == 'employee' for m in term_matches):
            primary = self._entity_primary.get('employee')
            if primary:
                return primary
        
        # First table
        if tables_from_matches:
            return tables_from_matches[0]
        
        # Final fallback - use employee/demographics primary if available
        if 'employee' in self._entity_primary:
            return self._entity_primary['employee']
        if 'demographics' in self._entity_primary:
            return self._entity_primary['demographics']
        
        # Nothing found - return None and let caller handle
        logger.warning("[SQL_ASSEMBLER] No primary table found - entity_primary is empty and no matches")
        return None
    
    def _build_count(self,
                     primary_table: str,
                     term_matches: List[TermMatch],
                     all_tables: List[str]) -> AssembledQuery:
        """Build COUNT query."""
        
        # Get tables and joins
        tables, joins, aliases = self._resolve_tables_and_joins(primary_table, term_matches, all_tables)
        
        # Build SELECT
        sql = f'SELECT COUNT(*) as count'
        
        # Build FROM with JOINs
        sql += self._build_from_clause(primary_table, joins, aliases)
        
        # Build WHERE
        where_clause, filters = self._build_where_clause(term_matches, aliases)
        if where_clause:
            sql += f'\n{where_clause}'
        
        return AssembledQuery(
            sql=sql,
            tables=tables,
            joins=joins,
            filters=filters,
            intent=QueryIntent.COUNT,
            primary_table=primary_table,
            success=True
        )
    
    def _build_list(self,
                    primary_table: str,
                    term_matches: List[TermMatch],
                    all_tables: List[str]) -> AssembledQuery:
        """Build LIST query (SELECT *)."""
        
        # Get tables and joins
        tables, joins, aliases = self._resolve_tables_and_joins(primary_table, term_matches, all_tables)
        
        # Build SELECT - use primary table alias for columns
        primary_alias = aliases.get(primary_table, primary_table)
        sql = f'SELECT {primary_alias}.*'
        
        # Build FROM with JOINs
        sql += self._build_from_clause(primary_table, joins, aliases)
        
        # Build WHERE
        where_clause, filters = self._build_where_clause(term_matches, aliases)
        if where_clause:
            sql += f'\n{where_clause}'
        
        # Add LIMIT
        sql += '\nLIMIT 100'
        
        return AssembledQuery(
            sql=sql,
            tables=tables,
            joins=joins,
            filters=filters,
            intent=QueryIntent.LIST,
            primary_table=primary_table,
            success=True
        )
    
    def _build_sum(self,
                   primary_table: str,
                   term_matches: List[TermMatch],
                   all_tables: List[str]) -> AssembledQuery:
        """Build SUM query."""
        
        # Find numeric column to sum (from term matches or default)
        sum_column = None
        for match in term_matches:
            # Look for amount/value columns
            col_lower = match.column_name.lower()
            if any(word in col_lower for word in ['amount', 'total', 'sum', 'rate', 'hours', 'salary', 'wage']):
                sum_column = match.column_name
                break
        
        # Get tables and joins
        tables, joins, aliases = self._resolve_tables_and_joins(primary_table, term_matches, all_tables)
        
        # Build SELECT
        primary_alias = aliases.get(primary_table, primary_table)
        if sum_column:
            sql = f'SELECT SUM({primary_alias}."{sum_column}") as total'
        else:
            sql = f'SELECT COUNT(*) as count'
        
        # Build FROM with JOINs
        sql += self._build_from_clause(primary_table, joins, aliases)
        
        # Build WHERE
        where_clause, filters = self._build_where_clause(term_matches, aliases)
        if where_clause:
            sql += f'\n{where_clause}'
        
        return AssembledQuery(
            sql=sql,
            tables=tables,
            joins=joins,
            filters=filters,
            intent=QueryIntent.SUM,
            primary_table=primary_table,
            success=True
        )
    
    def _build_compare(self,
                       primary_table: str,
                       term_matches: List[TermMatch],
                       all_tables: List[str],
                       group_by_column: str = None) -> AssembledQuery:
        """Build COMPARE query (GROUP BY)."""
        
        # Find group by column from matches or parameter
        if not group_by_column:
            for match in term_matches:
                col_lower = match.column_name.lower()
                # Good grouping columns
                if any(word in col_lower for word in ['state', 'location', 'company', 'department', 'status', 'type', 'code']):
                    group_by_column = match.column_name
                    break
        
        # Get tables and joins
        tables, joins, aliases = self._resolve_tables_and_joins(primary_table, term_matches, all_tables)
        
        # Build SELECT with GROUP BY
        primary_alias = aliases.get(primary_table, primary_table)
        
        if group_by_column:
            # Find which table has this column
            group_alias = primary_alias
            for match in term_matches:
                if match.column_name == group_by_column:
                    group_alias = aliases.get(match.table_name, match.table_name)
                    break
            
            sql = f'SELECT {group_alias}."{group_by_column}", COUNT(*) as count'
            sql += self._build_from_clause(primary_table, joins, aliases)
            
            # Build WHERE (excluding the group by column from filters)
            where_clause, filters = self._build_where_clause(
                [m for m in term_matches if m.column_name != group_by_column],
                aliases
            )
            if where_clause:
                sql += f'\n{where_clause}'
            
            sql += f'\nGROUP BY {group_alias}."{group_by_column}"'
            sql += f'\nORDER BY count DESC'
        else:
            # Fallback to COUNT
            sql = f'SELECT COUNT(*) as count'
            sql += self._build_from_clause(primary_table, joins, aliases)
            where_clause, filters = self._build_where_clause(term_matches, aliases)
            if where_clause:
                sql += f'\n{where_clause}'
        
        return AssembledQuery(
            sql=sql,
            tables=tables,
            joins=joins,
            filters=filters,
            intent=QueryIntent.COMPARE,
            primary_table=primary_table,
            success=True
        )
    
    def _resolve_tables_and_joins(self,
                                   primary_table: str,
                                   term_matches: List[TermMatch],
                                   all_tables: List[str]) -> Tuple[List[str], List[JoinPath], Dict[str, str]]:
        """
        Resolve which tables need to be joined and how.
        
        Returns:
            (tables, joins, aliases)
        """
        # Get unique tables from matches
        tables_needed = set()
        tables_needed.add(primary_table)
        for match in term_matches:
            tables_needed.add(match.table_name)
        
        tables = list(tables_needed)
        joins = []
        aliases = {t: f't{i}' for i, t in enumerate(tables)}
        
        # If multiple tables, find join paths
        if len(tables) > 1:
            for table in tables:
                if table != primary_table:
                    join_path = self._get_join_path(primary_table, table)
                    if join_path:
                        joins.append(join_path)
                    else:
                        logger.warning(f"[SQL_ASSEMBLER] No join path from {primary_table} to {table}")
        
        return tables, joins, aliases
    
    def _get_join_path(self, table1: str, table2: str) -> Optional[JoinPath]:
        """
        Get the best join path between two tables.
        Uses join_priority from _column_mappings.
        """
        cache_key = (table1, table2)
        if cache_key in self._join_cache:
            return self._join_cache[cache_key]
        
        # Also check reverse
        reverse_key = (table2, table1)
        if reverse_key in self._join_cache:
            jp = self._join_cache[reverse_key]
            return JoinPath(
                table1=table1,
                column1=jp.column2,
                table2=table2,
                column2=jp.column1,
                semantic_type=jp.semantic_type,
                priority=jp.priority
            )
        
        try:
            # Find matching semantic types between tables, ordered by priority
            result = self.conn.execute("""
                SELECT 
                    m1.original_column as col1,
                    m2.original_column as col2,
                    m1.semantic_type,
                    COALESCE(m1.join_priority, 50) as priority
                FROM _column_mappings m1
                JOIN _column_mappings m2 ON m1.semantic_type = m2.semantic_type
                WHERE m1.project = ? AND m2.project = ?
                  AND m1.table_name = ? AND m2.table_name = ?
                  AND m1.semantic_type IS NOT NULL
                ORDER BY COALESCE(m1.join_priority, 50) DESC
                LIMIT 1
            """, [self.project, self.project, table1, table2]).fetchone()
            
            if result:
                join_path = JoinPath(
                    table1=table1,
                    column1=result[0],
                    table2=table2,
                    column2=result[1],
                    semantic_type=result[2],
                    priority=result[3]
                )
                self._join_cache[cache_key] = join_path
                logger.warning(f"[SQL_ASSEMBLER] Join path: {table1}.{result[0]} = {table2}.{result[1]} (priority {result[3]})")
                return join_path
            
            # Fallback: Try common join columns
            common_keys = ['employee_number', 'empno', 'emp_no', 'person_number', 'worker_id']
            for key in common_keys:
                check = self.conn.execute("""
                    SELECT 1 FROM _column_profiles
                    WHERE project = ? AND table_name = ? AND LOWER(column_name) = ?
                """, [self.project, table1, key]).fetchone()
                
                if check:
                    check2 = self.conn.execute("""
                        SELECT 1 FROM _column_profiles
                        WHERE project = ? AND table_name = ? AND LOWER(column_name) = ?
                    """, [self.project, table2, key]).fetchone()
                    
                    if check2:
                        join_path = JoinPath(
                            table1=table1,
                            column1=key,
                            table2=table2,
                            column2=key,
                            semantic_type='employee_number',
                            priority=100
                        )
                        self._join_cache[cache_key] = join_path
                        logger.warning(f"[SQL_ASSEMBLER] Fallback join: {table1}.{key} = {table2}.{key}")
                        return join_path
        
        except Exception as e:
            logger.error(f"[SQL_ASSEMBLER] Error finding join path: {e}")
        
        return None
    
    def _build_from_clause(self,
                           primary_table: str,
                           joins: List[JoinPath],
                           aliases: Dict[str, str]) -> str:
        """Build FROM clause with JOINs."""
        primary_alias = aliases.get(primary_table, 't0')
        sql = f'\nFROM "{primary_table}" {primary_alias}'
        
        for join in joins:
            other_table = join.table2 if join.table1 == primary_table else join.table1
            other_alias = aliases.get(other_table, other_table)
            other_col = join.column2 if join.table1 == primary_table else join.column1
            primary_col = join.column1 if join.table1 == primary_table else join.column2
            
            sql += f'\nJOIN "{other_table}" {other_alias} ON {primary_alias}."{primary_col}" = {other_alias}."{other_col}"'
        
        return sql
    
    def _build_where_clause(self,
                            term_matches: List[TermMatch],
                            aliases: Dict[str, str]) -> Tuple[str, List[Dict]]:
        """Build WHERE clause from term matches."""
        if not term_matches:
            return "", []
        
        conditions = []
        filters = []
        
        for match in term_matches:
            alias = aliases.get(match.table_name, match.table_name)
            
            # Build condition based on operator
            if match.operator == 'ILIKE':
                condition = f'{alias}."{match.column_name}" ILIKE \'{match.match_value}\''
            elif match.operator == 'IN':
                condition = f'{alias}."{match.column_name}" IN ({match.match_value})'
            else:
                # Escape single quotes in value
                safe_value = str(match.match_value).replace("'", "''")
                condition = f'{alias}."{match.column_name}" {match.operator} \'{safe_value}\''
            
            conditions.append(condition)
            filters.append({
                'table': match.table_name,
                'column': match.column_name,
                'operator': match.operator,
                'value': match.match_value,
                'term': match.term,
                'source': 'term_index'
            })
        
        where_clause = 'WHERE ' + ' AND '.join(conditions) if conditions else ""
        return where_clause, filters


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

def assemble_query(conn: duckdb.DuckDBPyConnection,
                   project: str,
                   intent: str,
                   term_matches: List[Dict],
                   domain: str = None) -> Dict:
    """
    Convenience function to assemble a query.
    
    Args:
        conn: DuckDB connection
        project: Project ID
        intent: Intent string (count, list, sum, compare)
        term_matches: List of term match dicts
        domain: Optional domain hint
        
    Returns:
        Dict with sql, tables, success, error
    """
    assembler = SQLAssembler(conn, project)
    
    # Convert intent string to enum
    intent_map = {
        'count': QueryIntent.COUNT,
        'list': QueryIntent.LIST,
        'sum': QueryIntent.SUM,
        'compare': QueryIntent.COMPARE,
        'lookup': QueryIntent.LOOKUP,
        'filter': QueryIntent.FILTER,
    }
    query_intent = intent_map.get(intent.lower(), QueryIntent.LIST)
    
    # Convert dict matches to TermMatch objects
    matches = []
    for m in term_matches:
        matches.append(TermMatch(
            term=m.get('term', ''),
            table_name=m.get('table_name', m.get('table', '')),
            column_name=m.get('column_name', m.get('column', '')),
            operator=m.get('operator', '='),
            match_value=m.get('match_value', m.get('value', '')),
            domain=m.get('domain'),
            entity=m.get('entity'),
            confidence=m.get('confidence', 1.0),
            term_type=m.get('term_type', 'value')
        ))
    
    result = assembler.assemble(query_intent, matches, domain)
    
    return {
        'sql': result.sql,
        'tables': result.tables,
        'joins': [{'table1': j.table1, 'column1': j.column1, 'table2': j.table2, 'column2': j.column2} for j in result.joins],
        'filters': result.filters,
        'intent': result.intent.value,
        'primary_table': result.primary_table,
        'success': result.success,
        'error': result.error
    }
