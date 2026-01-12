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
    AVERAGE = "average"  # Evolution 7
    MINIMUM = "minimum"  # Evolution 7
    MAXIMUM = "maximum"  # Evolution 7
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
        
        # Cache for hub tables from context graph
        # Maps table_name -> {'truth_type': 'reality'|'configuration', 'semantic_type': '...'}
        self._hub_tables: Dict[str, Dict[str, str]] = {}
        
        # Load caches
        self._load_entity_primaries()
        self._load_hub_tables()
    
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
    
    def _load_hub_tables(self):
        """
        Load hub tables from context graph (_column_mappings + _schema_metadata).
        
        This leverages the hub-spoke architecture to identify:
        - REALITY hubs: Actual data (personal, deductions, earnings)  
        - CONFIGURATION hubs: Setup/config tables (locations, job_codes)
        
        For employee queries, we prefer REALITY hubs as the primary table.
        
        NOTE: truth_type is stored in _schema_metadata, not _column_mappings,
        so we need to JOIN the tables.
        """
        try:
            # Get all hub tables with their truth_type from _schema_metadata
            results = self.conn.execute("""
                SELECT DISTINCT 
                    cm.table_name, 
                    COALESCE(s.truth_type, 'unknown') as truth_type,
                    cm.semantic_type
                FROM _column_mappings cm
                LEFT JOIN _schema_metadata s 
                    ON cm.table_name = s.table_name 
                    AND LOWER(s.project) = LOWER(cm.project)
                WHERE LOWER(cm.project) = ? AND cm.is_hub = TRUE
            """, [self.project.lower()]).fetchall()
            
            for table_name, truth_type, semantic_type in results:
                self._hub_tables[table_name] = {
                    'truth_type': truth_type or 'unknown',
                    'semantic_type': semantic_type or ''
                }
            
            # Count by truth_type for logging
            reality_count = sum(1 for h in self._hub_tables.values() if h['truth_type'] == 'reality')
            config_count = sum(1 for h in self._hub_tables.values() if h['truth_type'] == 'configuration')
            
            logger.warning(f"[SQL_ASSEMBLER] Loaded {len(self._hub_tables)} hubs: {reality_count} reality, {config_count} configuration")
            
            # Debug: Log employee_number hub if found
            for table, info in self._hub_tables.items():
                if info['semantic_type'] == 'employee_number':
                    logger.warning(f"[SQL_ASSEMBLER] Found employee_number hub: {table} (truth_type={info['truth_type']})")
            
        except Exception as e:
            logger.warning(f"[SQL_ASSEMBLER] Could not load hub tables: {e}")
    
    def assemble(self, 
                 intent: QueryIntent,
                 term_matches: List[TermMatch],
                 domain: str = None,
                 group_by_column: str = None,
                 order_by: str = None,
                 order_direction: str = 'DESC',
                 limit: int = 100) -> AssembledQuery:
        """
        Assemble SQL from intent and term matches.
        
        Args:
            intent: What the user wants (COUNT, LIST, etc.)
            term_matches: Resolved terms from term_index
            domain: Optional domain hint (demographics, earnings, etc.)
            group_by_column: Optional column for COMPARE queries
            order_by: Optional column for ORDER BY (Evolution 9: Superlatives)
            order_direction: ASC or DESC (default DESC for "highest", "top")
            limit: Row limit (default 100, or extracted from "top 5")
            
        Returns:
            AssembledQuery with SQL and metadata
        """
        logger.warning(f"[SQL_ASSEMBLER] Assembling {intent.value} query with {len(term_matches)} term matches, group_by={group_by_column}, order_by={order_by}")
        
        # Extract tables from term matches (before dedup)
        tables_from_matches = list(set(m.table_name for m in term_matches))
        
        # EVOLUTION 8: If group_by_column specifies a table, include it in tables_from_matches
        group_by_table = None
        if group_by_column and '.' in group_by_column:
            group_by_table = group_by_column.split('.', 1)[0]
            if group_by_table not in tables_from_matches:
                tables_from_matches.append(group_by_table)
                logger.warning(f"[SQL_ASSEMBLER] Added GROUP BY table to matches: {group_by_table}")
        
        # Determine primary table FIRST
        # EVOLUTION 8: For GROUP BY queries, prefer the GROUP BY table as primary
        if group_by_table:
            primary_table = group_by_table
            logger.warning(f"[SQL_ASSEMBLER] Using GROUP BY table as primary: {primary_table}")
        else:
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
        
        # EVOLUTION 8: Ensure GROUP BY table is always included
        if group_by_table and group_by_table not in tables_from_matches:
            tables_from_matches.append(group_by_table)
        
        if len(tables_from_matches) == 0:
            # No term matches but we have a GROUP BY table
            if group_by_table:
                tables_from_matches = [group_by_table]
                logger.warning(f"[SQL_ASSEMBLER] No filter terms, using GROUP BY table only: {group_by_table}")
            else:
                logger.warning(f"[SQL_ASSEMBLER] No tables found after deduplication")
        elif len(tables_from_matches) == 1:
            logger.warning(f"[SQL_ASSEMBLER] SINGLE TABLE: All {len(term_matches)} matches from {tables_from_matches[0]}")
        else:
            logger.warning(f"[SQL_ASSEMBLER] CROSS-DOMAIN: {len(term_matches)} matches across {len(tables_from_matches)} tables: {tables_from_matches}")
        
        # Build query based on intent
        if intent == QueryIntent.COUNT:
            return self._build_count(primary_table, term_matches, tables_from_matches, group_by_column)
        elif intent == QueryIntent.LIST:
            return self._build_list(primary_table, term_matches, tables_from_matches, order_by, order_direction, limit)
        elif intent == QueryIntent.SUM:
            return self._build_aggregation(primary_table, term_matches, tables_from_matches, 'SUM', 'total', group_by_column)
        elif intent == QueryIntent.AVERAGE:
            return self._build_aggregation(primary_table, term_matches, tables_from_matches, 'AVG', 'average', group_by_column)
        elif intent == QueryIntent.MINIMUM:
            return self._build_aggregation(primary_table, term_matches, tables_from_matches, 'MIN', 'minimum', group_by_column)
        elif intent == QueryIntent.MAXIMUM:
            return self._build_aggregation(primary_table, term_matches, tables_from_matches, 'MAX', 'maximum', group_by_column)
        elif intent == QueryIntent.COMPARE:
            return self._build_compare(primary_table, term_matches, tables_from_matches, group_by_column)
        else:
            # Default to LIST for unknown intents
            return self._build_list(primary_table, term_matches, tables_from_matches, order_by, order_direction, limit)
    
    def _deduplicate_term_matches(self, 
                                   term_matches: List[TermMatch], 
                                   primary_table: str) -> List[TermMatch]:
        """
        Deduplicate term matches: one match per term, preferring primary table.
        Also filters out domain indicator words that shouldn't be literal searches.
        
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
        # ==========================================================================
        # STEP 1: Filter out domain indicator words
        # ==========================================================================
        # These words indicate WHAT the user wants, not a filter value
        # "employees in Texas" - "employees" = domain, "Texas" = filter
        DOMAIN_INDICATOR_WORDS = {
            # Entity indicators
            'employee', 'employees', 'worker', 'workers', 'staff', 'personnel',
            'person', 'people', 'individual', 'individuals',
            # Action indicators (sometimes indexed)
            'show', 'list', 'find', 'get', 'display', 'count', 'total',
            # Generic domain words
            'data', 'information', 'records', 'entries',
        }
        
        filtered_matches = []
        for match in term_matches:
            if match.term.lower() in DOMAIN_INDICATOR_WORDS:
                logger.warning(f"[SQL_ASSEMBLER] FILTER: Removing domain indicator word '{match.term}'")
                continue
            filtered_matches.append(match)
        
        if len(filtered_matches) < len(term_matches):
            logger.warning(f"[SQL_ASSEMBLER] Filtered {len(term_matches) - len(filtered_matches)} domain indicator terms")
        
        term_matches = filtered_matches
        
        # ==========================================================================
        # STEP 2: Deduplicate by term, preferring primary table
        # ==========================================================================
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
        Determine the primary table for the query using hub-spoke architecture.
        
        Priority:
        1. HUB-BASED: For employee domain, find REALITY hub (personal table)
        2. HUB-BASED: Prefer REALITY hubs over CONFIGURATION hubs
        3. FALLBACK: Domain-based primary from entity tables
        4. FALLBACK: Single table in matches
        5. FALLBACK: First table from matches
        
        The hub-spoke model means:
        - REALITY hubs = actual data (personal, deductions, earnings)
        - CONFIGURATION hubs = setup tables (locations, job_codes)
        
        For queries about entities (employees), we anchor on the REALITY hub.
        """
        # ==========================================================================
        # STEP 1: HUB-BASED SELECTION (preferred - uses context graph knowledge)
        # ==========================================================================
        if self._hub_tables:
            # Separate reality vs configuration hubs
            reality_hubs = [t for t, info in self._hub_tables.items() 
                          if info['truth_type'] == 'reality']
            config_hubs = [t for t, info in self._hub_tables.items() 
                         if info['truth_type'] == 'configuration']
            
            # For EMPLOYEE domain, find the employee_number reality hub (personal table)
            if domain in ('demographics', 'employee', 'employees'):
                # Look for hub with employee_number semantic type
                for table, info in self._hub_tables.items():
                    if (info['truth_type'] == 'reality' and 
                        info['semantic_type'] == 'employee_number'):
                        logger.warning(f"[SQL_ASSEMBLER] HUB-BASED: employee_number hub → {table}")
                        return table
                
                # Fallback: any reality hub with 'personal' in name
                for hub in reality_hubs:
                    if 'personal' in hub.lower():
                        logger.warning(f"[SQL_ASSEMBLER] HUB-BASED: personal reality hub → {hub}")
                        return hub
            
            # For DEDUCTIONS domain, use deductions reality hub if it exists
            if domain in ('deductions', 'benefits'):
                for hub in reality_hubs:
                    if 'deduction' in hub.lower():
                        logger.warning(f"[SQL_ASSEMBLER] HUB-BASED: deductions reality hub → {hub}")
                        return hub
            
            # For EARNINGS domain
            if domain in ('earnings', 'compensation', 'pay'):
                for hub in reality_hubs:
                    if 'earning' in hub.lower():
                        logger.warning(f"[SQL_ASSEMBLER] HUB-BASED: earnings reality hub → {hub}")
                        return hub
            
            # General case: prefer reality hubs from term matches over config hubs
            matched_reality = [t for t in tables_from_matches if t in reality_hubs]
            matched_config = [t for t in tables_from_matches if t in config_hubs]
            
            if matched_reality:
                logger.warning(f"[SQL_ASSEMBLER] HUB-BASED: reality hub from matches → {matched_reality[0]}")
                return matched_reality[0]
        
        # ==========================================================================
        # STEP 2: ENTITY PRIMARY FALLBACK (for projects without full hub data)
        # ==========================================================================
        
        # Employee domain uses demographics/employee primary
        if domain in ('demographics', 'employee', 'employees'):
            for key in ['demographics', 'employee']:
                if key in self._entity_primary:
                    primary = self._entity_primary[key]
                    logger.warning(f"[SQL_ASSEMBLER] ENTITY-BASED: {key} → {primary}")
                    return primary
        
        # Look for 'personal' table in matches
        for table in tables_from_matches:
            if 'personal' in table.lower():
                logger.warning(f"[SQL_ASSEMBLER] PATTERN: 'personal' in table → {table}")
                return table
        
        # Domain-based primary from entity tables
        if domain and domain in self._entity_primary:
            primary = self._entity_primary[domain]
            logger.warning(f"[SQL_ASSEMBLER] ENTITY-BASED: domain '{domain}' → {primary}")
            return primary
        
        # Check for employee domain in term matches
        for match in term_matches:
            if hasattr(match, 'domain') and match.domain in ('demographics', 'employee', 'hr'):
                for key in ['demographics', 'employee', 'hr']:
                    if key in self._entity_primary:
                        primary = self._entity_primary[key]
                        logger.warning(f"[SQL_ASSEMBLER] ENTITY-BASED: match domain → {primary}")
                        return primary
        
        # ==========================================================================
        # STEP 3: SIMPLE FALLBACKS
        # ==========================================================================
        
        # Single table - use it
        if len(tables_from_matches) == 1:
            logger.warning(f"[SQL_ASSEMBLER] SINGLE TABLE: {tables_from_matches[0]}")
            return tables_from_matches[0]
        
        # Use entity_primary fallback
        for key in ['employee', 'demographics', 'hr']:
            if key in self._entity_primary:
                primary = self._entity_primary[key]
                logger.warning(f"[SQL_ASSEMBLER] FALLBACK: entity_primary '{key}' → {primary}")
                return primary
        
        # First table from matches
        if tables_from_matches:
            logger.warning(f"[SQL_ASSEMBLER] FALLBACK: first table → {tables_from_matches[0]}")
            return tables_from_matches[0]
        
        # Nothing found
        logger.warning("[SQL_ASSEMBLER] No primary table found")
        return None
    
    def _build_count(self,
                     primary_table: str,
                     term_matches: List[TermMatch],
                     all_tables: List[str],
                     group_by_column: str = None) -> AssembledQuery:
        """Build COUNT query. EVOLUTION 8: Added GROUP BY support."""
        
        # Get tables and joins
        tables, joins, aliases = self._resolve_tables_and_joins(primary_table, term_matches, all_tables)
        
        # Build SELECT
        if group_by_column:
            # EVOLUTION 8: GROUP BY support
            if '.' in group_by_column:
                group_table, group_col = group_by_column.split('.', 1)
                group_alias = aliases.get(group_table, 't0')
            else:
                group_col = group_by_column
                group_alias = aliases.get(primary_table, 't0')
            sql = f'SELECT {group_alias}."{group_col}", COUNT(*) as count'
            logger.warning(f"[SQL_ASSEMBLER] COUNT with GROUP BY: {group_col}")
        else:
            sql = f'SELECT COUNT(*) as count'
        
        # Build FROM with JOINs
        sql += self._build_from_clause(primary_table, joins, aliases)
        
        # Build WHERE
        where_clause, filters = self._build_where_clause(term_matches, aliases)
        if where_clause:
            sql += f'\n{where_clause}'
        
        # EVOLUTION 8: Add GROUP BY clause
        if group_by_column:
            if '.' in group_by_column:
                group_table, group_col = group_by_column.split('.', 1)
                group_alias = aliases.get(group_table, 't0')
            else:
                group_col = group_by_column
                group_alias = aliases.get(primary_table, 't0')
            sql += f'\nGROUP BY {group_alias}."{group_col}"'
            sql += f'\nORDER BY count DESC'  # Order by count
        
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
                    all_tables: List[str],
                    order_by: str = None,
                    order_direction: str = 'DESC',
                    limit: int = 100) -> AssembledQuery:
        """
        Build LIST query (SELECT *).
        
        EVOLUTION 9: Added ORDER BY support for superlatives.
        
        Args:
            primary_table: Main table for query
            term_matches: Resolved term matches
            all_tables: All tables involved
            order_by: Optional column for ORDER BY (e.g., "salary" for "highest paid")
            order_direction: ASC or DESC
            limit: Row limit (default 100, or from "top 5")
        """
        
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
        
        # EVOLUTION 9: Add ORDER BY for superlatives
        if order_by:
            # Resolve order_by column to correct table alias
            order_col_resolved = self._resolve_order_by_column(order_by, primary_table, aliases)
            sql += f'\nORDER BY {order_col_resolved} {order_direction}'
            logger.warning(f"[SQL_ASSEMBLER] SUPERLATIVE: ORDER BY {order_col_resolved} {order_direction} LIMIT {limit}")
        
        # Add LIMIT
        sql += f'\nLIMIT {limit}'
        
        return AssembledQuery(
            sql=sql,
            tables=tables,
            joins=joins,
            filters=filters,
            intent=QueryIntent.LIST,
            primary_table=primary_table,
            success=True
        )
    
    def _resolve_order_by_column(self, order_by: str, primary_table: str, aliases: Dict[str, str]) -> str:
        """
        Resolve ORDER BY column to correct table alias.
        
        EVOLUTION 9: Supports superlative queries.
        
        Args:
            order_by: Column name or table.column
            primary_table: Primary table for the query
            aliases: Table aliases mapping
            
        Returns:
            Aliased column reference (e.g., t0."salary")
        """
        if '.' in order_by:
            # Already qualified: table.column
            table, col = order_by.split('.', 1)
            alias = aliases.get(table, table)
            return f'{alias}."{col}"'
        else:
            # Unqualified: assume primary table
            alias = aliases.get(primary_table, 't0')
            return f'{alias}."{order_by}"'
    
    def _build_aggregation(self,
                           primary_table: str,
                           term_matches: List[TermMatch],
                           all_tables: List[str],
                           agg_func: str,
                           result_alias: str,
                           group_by_column: str = None) -> AssembledQuery:
        """
        Build aggregation query (SUM, AVG, MIN, MAX).
        
        EVOLUTION 7: Generalized aggregation handler.
        EVOLUTION 8: Added GROUP BY support.
        
        Args:
            primary_table: Main table for query
            term_matches: Resolved term matches
            all_tables: All tables involved
            agg_func: SQL aggregation function (SUM, AVG, MIN, MAX)
            group_by_column: Optional column for GROUP BY (Evolution 8)
            result_alias: Column alias for result (total, average, minimum, maximum)
        """
        
        # Find the aggregation target column
        # EVOLUTION 7: Look for term_type='aggregation_target' first
        agg_column = None
        agg_table = None
        
        for match in term_matches:
            if getattr(match, 'term_type', None) == 'aggregation_target':
                agg_column = match.column_name
                agg_table = match.table_name
                logger.warning(f"[SQL_ASSEMBLER] Using aggregation target: {agg_table}.{agg_column}")
                break
        
        # Fallback: look for numeric columns by name pattern
        if not agg_column:
            for match in term_matches:
                col_lower = match.column_name.lower()
                if any(word in col_lower for word in ['amount', 'total', 'sum', 'rate', 'hours', 'salary', 'wage', 'pay', 'earning', 'annual']):
                    agg_column = match.column_name
                    agg_table = match.table_name
                    logger.warning(f"[SQL_ASSEMBLER] Using fallback numeric column: {agg_table}.{agg_column}")
                    break
        
        # Get tables and joins
        # Filter out aggregation_target matches from join resolution
        filter_matches = [m for m in term_matches if getattr(m, 'term_type', None) != 'aggregation_target']
        
        # If we have an aggregation table and no filter matches, use the agg table as primary
        effective_primary = agg_table if (agg_table and not filter_matches) else primary_table
        
        tables, joins, aliases = self._resolve_tables_and_joins(effective_primary, filter_matches, all_tables)
        
        # Ensure effective primary is in aliases
        if effective_primary not in aliases:
            aliases[effective_primary] = 't0'
        
        # Build SELECT
        # IMPORTANT: Cast to DOUBLE for aggregation since some numeric columns may be stored as VARCHAR
        if agg_column:
            agg_alias = aliases.get(agg_table, aliases.get(effective_primary, effective_primary))
            # Use TRY_CAST to safely handle non-numeric values (returns NULL instead of error)
            agg_expr = f'{agg_func}(TRY_CAST({agg_alias}."{agg_column}" AS DOUBLE)) as {result_alias}'
            
            # EVOLUTION 8: Add GROUP BY column to SELECT if specified
            if group_by_column:
                # group_by_column could be "table.column" or just "column"
                if '.' in group_by_column:
                    group_table, group_col = group_by_column.split('.', 1)
                    group_alias = aliases.get(group_table, 't0')
                else:
                    group_col = group_by_column
                    group_alias = aliases.get(effective_primary, 't0')
                sql = f'SELECT {group_alias}."{group_col}", {agg_expr}'
                logger.warning(f"[SQL_ASSEMBLER] GROUP BY query: {group_col}")
            else:
                sql = f'SELECT {agg_expr}'
        else:
            # Fallback to COUNT if no numeric column found
            primary_alias = aliases.get(effective_primary, effective_primary)
            if group_by_column:
                if '.' in group_by_column:
                    group_table, group_col = group_by_column.split('.', 1)
                    group_alias = aliases.get(group_table, 't0')
                else:
                    group_col = group_by_column
                    group_alias = aliases.get(effective_primary, 't0')
                sql = f'SELECT {group_alias}."{group_col}", COUNT(*) as count'
            else:
                sql = f'SELECT COUNT(*) as count'
            logger.warning(f"[SQL_ASSEMBLER] No numeric column found for {agg_func}, falling back to COUNT")
        
        # Build FROM with JOINs
        sql += self._build_from_clause(effective_primary, joins, aliases)
        
        # Build WHERE (exclude aggregation targets from filters)
        where_clause, filters = self._build_where_clause(filter_matches, aliases)
        if where_clause:
            sql += f'\n{where_clause}'
        
        # EVOLUTION 8: Add GROUP BY clause
        if group_by_column:
            if '.' in group_by_column:
                group_table, group_col = group_by_column.split('.', 1)
                group_alias = aliases.get(group_table, 't0')
            else:
                group_col = group_by_column
                group_alias = aliases.get(effective_primary, 't0')
            sql += f'\nGROUP BY {group_alias}."{group_col}"'
            sql += f'\nORDER BY {result_alias} DESC'  # Order by aggregation result
        
        # Map agg_func back to intent
        intent_map = {
            'SUM': QueryIntent.SUM,
            'AVG': QueryIntent.AVERAGE,
            'MIN': QueryIntent.MINIMUM,
            'MAX': QueryIntent.MAXIMUM,
        }
        
        return AssembledQuery(
            sql=sql,
            tables=tables,
            joins=joins,
            filters=filters,
            intent=intent_map.get(agg_func, QueryIntent.SUM),
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
        
        CRITICAL: Only returns tables that have valid join paths.
        Tables without join paths are excluded to prevent WHERE clause errors.
        
        Returns:
            (tables, joins, aliases) - only tables actually in the query
        """
        # Start with primary table
        tables_with_joins = [primary_table]
        joins = []
        
        # Get unique tables from matches (excluding primary)
        other_tables_needed = set()
        for match in term_matches:
            if match.table_name != primary_table:
                other_tables_needed.add(match.table_name)
        
        # For each other table, check if we can join it
        for table in sorted(other_tables_needed):  # Sort for determinism
            join_path = self._get_join_path(primary_table, table)
            if join_path:
                tables_with_joins.append(table)
                joins.append(join_path)
                logger.warning(f"[SQL_ASSEMBLER] JOIN OK: {primary_table} → {table}")
            else:
                logger.warning(f"[SQL_ASSEMBLER] JOIN FAILED: No path from {primary_table} to {table} - EXCLUDING from query")
        
        # Build aliases ONLY for tables actually in the query
        aliases = {t: f't{i}' for i, t in enumerate(tables_with_joins)}
        
        logger.warning(f"[SQL_ASSEMBLER] Final tables in query: {tables_with_joins}")
        logger.warning(f"[SQL_ASSEMBLER] Aliases: {aliases}")
        
        return tables_with_joins, joins, aliases
    
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
            # NOTE: Using case-insensitive project match for consistency
            result = self.conn.execute("""
                SELECT 
                    m1.original_column as col1,
                    m2.original_column as col2,
                    m1.semantic_type,
                    COALESCE(m1.join_priority, 50) as priority
                FROM _column_mappings m1
                JOIN _column_mappings m2 ON m1.semantic_type = m2.semantic_type
                WHERE LOWER(m1.project) = LOWER(?) AND LOWER(m2.project) = LOWER(?)
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
                    WHERE LOWER(project) = LOWER(?) AND table_name = ? AND LOWER(column_name) = ?
                """, [self.project, table1, key]).fetchone()
                
                if check:
                    check2 = self.conn.execute("""
                        SELECT 1 FROM _column_profiles
                        WHERE LOWER(project) = LOWER(?) AND table_name = ? AND LOWER(column_name) = ?
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
            # SAFETY CHECK: Only include conditions for tables that are in the query
            if match.table_name not in aliases:
                logger.warning(f"[SQL_ASSEMBLER] SKIP: Table '{match.table_name}' not in query aliases, skipping filter for '{match.term}'")
                continue
            
            alias = aliases[match.table_name]
            
            # Build condition based on operator
            if match.operator == 'ILIKE':
                condition = f'{alias}."{match.column_name}" ILIKE \'{match.match_value}\''
            elif match.operator == 'IN':
                condition = f'{alias}."{match.column_name}" IN ({match.match_value})'
            elif match.operator == 'BETWEEN':
                # BETWEEN uses "value1|value2" format
                parts = str(match.match_value).split('|')
                if len(parts) == 2:
                    val1, val2 = parts
                    # Check if values are dates (contain '-') or numeric
                    if '-' in val1:  # Date format YYYY-MM-DD
                        condition = f'{alias}."{match.column_name}" >= \'{val1}\' AND {alias}."{match.column_name}" < \'{val2}\''
                    else:
                        # Numeric BETWEEN
                        condition = f'{alias}."{match.column_name}" BETWEEN {val1} AND {val2}'
                else:
                    logger.warning(f"[SQL_ASSEMBLER] Invalid BETWEEN format: {match.match_value}")
                    continue
            elif match.operator in ('>', '>=', '<', '<='):
                # Numeric comparisons - no quotes
                condition = f'{alias}."{match.column_name}" {match.operator} {match.match_value}'
            elif match.operator == '!=':
                # Negation - with quotes for string values
                safe_value = str(match.match_value).replace("'", "''")
                condition = f'{alias}."{match.column_name}" != \'{safe_value}\''
            elif match.operator == 'NOT IN':
                # Negated IN clause
                condition = f'{alias}."{match.column_name}" NOT IN ({match.match_value})'
            else:
                # Default = with quotes
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
