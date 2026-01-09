"""
XLR8 Query Resolver - Lookup-Based Query Resolution
====================================================

THIS IS THE FIX.

The old approach: Score 47 tables with fuzzy matching, hope the right one wins.
The new approach: LOOKUP the answer from pre-computed intelligence.

We already computed everything at upload time:
- _table_classifications: table_type (MASTER/TRANSACTION/CONFIG), domain (demographics/earnings/taxes)
- _column_profiles: filter_category (status/company/location), distinct_values
- _column_mappings: semantic_type, hub/spoke relationships
- _schema_metadata: entity_type, row_count

Query resolution is now DETERMINISTIC LOOKUPS, not probabilistic scoring.

Example: "what's the headcount?"
1. INTENT: COUNT query on PEOPLE
2. LOOKUP: demographics domain + MASTER type → employee table
3. LOOKUP: filter_category='status' → employee_status_code column
4. LOOKUP: distinct_values → ['A', 'T', 'L', ...]
5. LOOKUP/INFER: active status values → 'A' (or ask user once, cache forever)
6. SQL: SELECT COUNT(*) FROM employee WHERE employee_status_code = 'A'

NO SCORING. NO FUZZY MATCHING. JUST LOOKUPS.

Author: XLR8 Team
Version: 1.0.0
"""

import logging
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# INTENT TYPES - What is the user trying to do?
# =============================================================================

class QueryIntent(Enum):
    """What the user is trying to accomplish."""
    COUNT = "count"              # How many X? Headcount?
    LIST = "list"                # Show me all X, List X
    LOOKUP = "lookup"            # What is X? Find X
    SUM = "sum"                  # Total X, Sum of X
    COMPARE = "compare"          # X vs Y, Compare X to Y
    FILTER = "filter"            # X where Y, X by Y
    VALIDATE = "validate"        # Is X correct? Check X
    UNKNOWN = "unknown"


class EntityDomain(Enum):
    """What domain/entity is being asked about."""
    EMPLOYEES = "demographics"   # People, headcount, workers
    EARNINGS = "earnings"        # Pay, compensation, wages
    DEDUCTIONS = "deductions"    # Benefits, 401k, deductions
    TAXES = "taxes"              # Tax, withholding, SUI, FUTA
    LOCATIONS = "locations"      # Sites, addresses, work locations
    JOBS = "jobs"                # Positions, titles, roles
    TIME = "time"                # Hours, attendance, PTO
    COMPANIES = "companies"      # Legal entities, employers
    UNKNOWN = "unknown"


# =============================================================================
# INTENT DETECTION - Simple keyword mapping (NOT fuzzy matching)
# =============================================================================

# Keywords that indicate COUNT intent
COUNT_KEYWORDS = [
    'how many', 'count', 'headcount', 'head count', 'total number',
    'number of', 'how much', 'quantity'
]

# Keywords that indicate LIST intent  
LIST_KEYWORDS = [
    'list', 'show', 'display', 'what are', 'which', 'all the',
    'give me', 'show me'
]

# Keywords that indicate SUM intent
SUM_KEYWORDS = [
    'total', 'sum', 'aggregate', 'combined', 'overall'
]

# Domain keyword mapping - these map to _table_classifications.domain
DOMAIN_KEYWORDS = {
    EntityDomain.EMPLOYEES: [
        'employee', 'employees', 'worker', 'workers', 'staff', 'people',
        'headcount', 'head count', 'personnel', 'workforce', 'person',
        'active', 'terminated', 'hired'
    ],
    EntityDomain.EARNINGS: [
        'earning', 'earnings', 'pay', 'salary', 'wage', 'wages',
        'compensation', 'pay code', 'pay rate', 'hourly'
    ],
    EntityDomain.DEDUCTIONS: [
        'deduction', 'deductions', 'benefit', 'benefits', '401k', '401(k)',
        'insurance', 'health', 'dental', 'vision', 'hsa', 'fsa'
    ],
    EntityDomain.TAXES: [
        'tax', 'taxes', 'withholding', 'sui', 'suta', 'futa', 'fica',
        'federal', 'state tax', 'local tax', 'w2', 'w-2'
    ],
    EntityDomain.LOCATIONS: [
        'location', 'locations', 'site', 'sites', 'address', 'work location',
        'office', 'branch', 'region'
    ],
    EntityDomain.JOBS: [
        'job', 'jobs', 'position', 'positions', 'title', 'titles',
        'role', 'roles', 'job code'
    ],
    EntityDomain.TIME: [
        'time', 'hours', 'attendance', 'pto', 'vacation', 'sick',
        'leave', 'accrual', 'schedule'
    ],
    EntityDomain.COMPANIES: [
        'company', 'companies', 'entity', 'entities', 'employer',
        'legal entity', 'business unit'
    ],
}


@dataclass
class ParsedIntent:
    """Result of parsing user's question."""
    intent: QueryIntent
    domain: EntityDomain
    raw_question: str
    
    # Extracted specifics
    count_what: Optional[str] = None       # "active employees", "terminated"
    filter_hints: List[str] = field(default_factory=list)  # "in texas", "last year"
    
    # Confidence
    intent_confidence: float = 0.0
    domain_confidence: float = 0.0
    
    def __str__(self):
        return f"Intent({self.intent.value}, {self.domain.value})"


def parse_intent(question: str) -> ParsedIntent:
    """
    Parse the user's question to determine intent and domain.
    
    This is KEYWORD MATCHING, not fuzzy scoring.
    If we can't determine intent/domain clearly, we say UNKNOWN.
    """
    q_lower = question.lower().strip()
    
    # Detect intent
    intent = QueryIntent.UNKNOWN
    intent_confidence = 0.0
    
    for kw in COUNT_KEYWORDS:
        if kw in q_lower:
            intent = QueryIntent.COUNT
            intent_confidence = 1.0
            break
    
    if intent == QueryIntent.UNKNOWN:
        for kw in SUM_KEYWORDS:
            if kw in q_lower:
                intent = QueryIntent.SUM
                intent_confidence = 1.0
                break
    
    if intent == QueryIntent.UNKNOWN:
        for kw in LIST_KEYWORDS:
            if kw in q_lower:
                intent = QueryIntent.LIST
                intent_confidence = 1.0
                break
    
    # Detect domain
    domain = EntityDomain.UNKNOWN
    domain_confidence = 0.0
    domain_matches = []
    
    for dom, keywords in DOMAIN_KEYWORDS.items():
        for kw in keywords:
            if kw in q_lower:
                domain_matches.append((dom, len(kw)))  # Prefer longer matches
    
    if domain_matches:
        # Take the domain with the longest keyword match
        domain_matches.sort(key=lambda x: -x[1])
        domain = domain_matches[0][0]
        domain_confidence = 1.0
    
    # Special case: "headcount" implies EMPLOYEES + COUNT
    if 'headcount' in q_lower or 'head count' in q_lower:
        intent = QueryIntent.COUNT
        domain = EntityDomain.EMPLOYEES
        intent_confidence = 1.0
        domain_confidence = 1.0
    
    return ParsedIntent(
        intent=intent,
        domain=domain,
        raw_question=question,
        intent_confidence=intent_confidence,
        domain_confidence=domain_confidence
    )


# =============================================================================
# QUERY RESOLVER - The main class that does LOOKUPS
# =============================================================================

@dataclass
class ResolvedQuery:
    """Result of resolving a query against our intelligence."""
    success: bool
    table_name: Optional[str] = None
    columns_needed: List[str] = field(default_factory=list)
    filter_column: Optional[str] = None
    filter_values: List[str] = field(default_factory=list)
    sql: Optional[str] = None
    explanation: str = ""
    
    # For debugging
    resolution_path: List[str] = field(default_factory=list)
    
    # v2: Reality Context - breakdowns for consultative response
    # These are populated automatically for employee count queries
    reality_context: Optional[Dict] = None
    # Structure:
    # {
    #   'answer': 3976,
    #   'answer_label': 'Active employees',
    #   'breakdowns': {
    #     'by_status': {'A': 3976, 'L': 36, 'T': 10462},
    #     'by_company': {'TISI': 3200, 'TCAN': 776},
    #     'by_employee_type': {'FT': 3100, 'PT': 876},
    #     'by_location': {'PA': 500, 'NY': 450, ...}  # top 10
    #   },
    #   'total_in_table': 14474
    # }
    

class QueryResolver:
    """
    Resolves queries using LOOKUPS against pre-computed intelligence.
    
    NO SCORING. NO FUZZY MATCHING. DETERMINISTIC LOOKUPS.
    """
    
    def __init__(self, handler):
        """
        Args:
            handler: StructuredDataHandler with DuckDB connection
        """
        self.handler = handler
        self.conn = handler.conn
        
        # Cache lookups for performance
        self._table_classifications_cache: Dict[str, Dict] = {}
        self._column_profiles_cache: Dict[str, List[Dict]] = {}
        self._status_values_cache: Dict[str, Dict] = {}  # table -> {column, active_values}
        
    # =========================================================================
    # MAIN ENTRY POINT
    # =========================================================================
    
    def resolve(self, question: str, project: str) -> ResolvedQuery:
        """
        Resolve a question to a SQL query using LOOKUPS.
        
        Args:
            question: User's question
            project: Project name
            
        Returns:
            ResolvedQuery with SQL and explanation
        """
        result = ResolvedQuery(success=False)
        result.resolution_path.append(f"Question: {question}")
        
        # STEP 1: Parse intent
        parsed = parse_intent(question)
        result.resolution_path.append(f"Parsed: {parsed}")
        
        if parsed.intent == QueryIntent.UNKNOWN:
            result.explanation = "Could not determine what you're asking for"
            return result
        
        if parsed.domain == EntityDomain.UNKNOWN:
            result.explanation = "Could not determine which data domain you're asking about"
            return result
        
        # STEP 2: Route to appropriate resolver
        if parsed.intent == QueryIntent.COUNT and parsed.domain == EntityDomain.EMPLOYEES:
            return self._resolve_employee_count(project, parsed, result)
        
        elif parsed.intent == QueryIntent.COUNT:
            return self._resolve_generic_count(project, parsed, result)
        
        elif parsed.intent == QueryIntent.LIST:
            return self._resolve_list(project, parsed, result)
        
        else:
            result.explanation = f"Intent '{parsed.intent.value}' not yet implemented"
            return result
    
    # =========================================================================
    # EMPLOYEE COUNT RESOLVER - The canonical example
    # =========================================================================
    
    def _resolve_employee_count(self, project: str, parsed: ParsedIntent, 
                                 result: ResolvedQuery) -> ResolvedQuery:
        """
        Resolve: "How many employees?" / "What's the headcount?"
        
        LOOKUP CHAIN:
        1. Find MASTER table in demographics domain
        2. Find status column (filter_category='status')
        3. Find active status values
        4. Generate SQL
        """
        
        # LOOKUP 1: Find the employee master table
        employee_table = self._lookup_table(
            project=project,
            domain='demographics',
            table_type='master'
        )
        
        if not employee_table:
            # Fallback: try to find any table with 'employee' in name
            employee_table = self._lookup_table_by_name(project, ['employee', 'employees', 'worker'])
        
        if not employee_table:
            result.explanation = "Could not find employee/demographics table"
            result.resolution_path.append("LOOKUP FAILED: No demographics MASTER table found")
            return result
        
        table_name = employee_table['table_name']
        result.table_name = table_name
        result.resolution_path.append(f"LOOKUP 1: Found table '{table_name}'")
        
        # LOOKUP 2: Find the status column
        status_column = self._lookup_status_column(project, table_name)
        
        if not status_column:
            # No status column - just count all rows
            result.sql = f'SELECT COUNT(*) as headcount FROM "{table_name}"'
            result.explanation = f"Counting all rows in {table_name} (no status column found)"
            result.resolution_path.append("LOOKUP 2: No status column - counting all rows")
            result.success = True
            return result
        
        result.filter_column = status_column['column_name']
        result.resolution_path.append(f"LOOKUP 2: Found status column '{status_column['column_name']}'")
        
        # LOOKUP 3: Get distinct values for status column
        distinct_values = status_column.get('distinct_values', [])
        if isinstance(distinct_values, str):
            try:
                distinct_values = json.loads(distinct_values)
            except:
                distinct_values = []
        
        result.resolution_path.append(f"LOOKUP 3: Status values = {distinct_values}")
        
        # LOOKUP 4: Determine which values mean "active"
        active_values = self._infer_active_status_values(distinct_values)
        result.filter_values = active_values
        result.resolution_path.append(f"LOOKUP 4: Active values = {active_values}")
        
        # GENERATE SQL
        if active_values:
            values_sql = ', '.join(f"'{v}'" for v in active_values)
            result.sql = f'''SELECT COUNT(*) as headcount 
FROM "{table_name}" 
WHERE "{status_column['column_name']}" IN ({values_sql})'''
            result.explanation = f"Counting active employees where {status_column['column_name']} in {active_values}"
        else:
            # Can't determine active values - count all
            result.sql = f'SELECT COUNT(*) as headcount FROM "{table_name}"'
            result.explanation = f"Counting all rows in {table_name} (could not determine active status values)"
        
        result.success = True
        
        # v2: Gather Reality Context - breakdowns for consultative response
        result.reality_context = self._gather_reality_context(
            project=project,
            table_name=table_name,
            status_column=status_column['column_name'] if status_column else None,
            active_values=active_values
        )
        result.resolution_path.append(f"CONTEXT: Gathered {len(result.reality_context.get('breakdowns', {}))} breakdowns")
        
        return result
    
    # =========================================================================
    # REALITY CONTEXT - Proactive breakdowns for consultative response
    # =========================================================================
    
    def _gather_reality_context(
        self, 
        project: str, 
        table_name: str, 
        status_column: Optional[str],
        active_values: List[str]
    ) -> Dict:
        """
        Gather comprehensive Reality context for consultative response.
        
        This is what separates a $5/hr data dump from a $500/hr consultant.
        We don't just answer the question - we provide the context needed
        to understand what the answer MEANS.
        
        Runs 4-5 fast queries to get:
        1. The answer (active count)
        2. Status breakdown (all statuses, not just active)
        3. Company breakdown  
        4. Location breakdown (top 10)
        5. Employee type breakdown
        
        Args:
            project: Project name
            table_name: The employee table
            status_column: Status column name (if found)
            active_values: Values that mean "active"
            
        Returns:
            Dict with answer, breakdowns, and total
        """
        context = {
            'answer': None,
            'answer_label': 'Active employees' if active_values else 'Total employees',
            'breakdowns': {},
            'total_in_table': None
        }
        
        try:
            # Find dimensional columns for this table
            dimensional_columns = self._lookup_dimensional_columns(project, table_name)
            logger.warning(f"[RESOLVER] Found {len(dimensional_columns)} dimensional columns for breakdowns")
            
            # Query 1: Get the answer (active count or total)
            if status_column and active_values:
                values_sql = ', '.join(f"'{v}'" for v in active_values)
                answer_sql = f'SELECT COUNT(*) as cnt FROM "{table_name}" WHERE "{status_column}" IN ({values_sql})'
            else:
                answer_sql = f'SELECT COUNT(*) as cnt FROM "{table_name}"'
            
            result = self.conn.execute(answer_sql).fetchone()
            context['answer'] = result[0] if result else 0
            
            # Query 2: Get total in table (for context)
            total_sql = f'SELECT COUNT(*) as cnt FROM "{table_name}"'
            result = self.conn.execute(total_sql).fetchone()
            context['total_in_table'] = result[0] if result else 0
            
            # Query 3: Status breakdown (ALL statuses, not just active)
            if status_column:
                breakdown = self._run_breakdown_query(table_name, status_column)
                if breakdown:
                    context['breakdowns']['by_status'] = breakdown
            
            # Query 4+: Dimensional breakdowns (limit to 4 most useful)
            MAX_BREAKDOWNS = 4  # Status + 3 others
            
            for dim_col in dimensional_columns:
                # Stop if we have enough breakdowns
                if len(context['breakdowns']) >= MAX_BREAKDOWNS:
                    break
                    
                col_name = dim_col['column_name']
                category = dim_col.get('filter_category', 'general')
                distinct_count = dim_col.get('distinct_count', 0)
                
                # Skip status column (already handled above)
                if col_name == status_column:
                    continue
                
                # Skip high-cardinality columns (> 20 distinct values for now, except location)
                if distinct_count > 20 and category != 'location':
                    continue
                
                # Determine breakdown key name
                if category == 'company':
                    key = 'by_company'
                elif category == 'location':
                    key = 'by_location'
                elif 'type' in col_name.lower():
                    key = 'by_employee_type'
                elif 'fullpart' in col_name.lower() or 'ft_pt' in col_name.lower():
                    key = 'by_fullpart_time'
                else:
                    # Skip generic columns we don't recognize
                    # Only include specifically useful dimensions
                    continue
                
                # Skip if we already have this breakdown type
                if key in context['breakdowns']:
                    continue
                
                # Run the breakdown query (with active filter if available)
                breakdown = self._run_breakdown_query(
                    table_name, 
                    col_name, 
                    filter_column=status_column,
                    filter_values=active_values,
                    limit=10 if category == 'location' else None
                )
                
                if breakdown:
                    context['breakdowns'][key] = breakdown
                    
        except Exception as e:
            logger.error(f"[RESOLVER] Error gathering reality context: {e}")
        
        return context
    
    def _lookup_dimensional_columns(self, project: str, table_name: str) -> List[Dict]:
        """
        Find columns suitable for dimensional breakdowns.
        
        Looks for columns with filter_category in (company, location, general)
        and reasonable cardinality (distinct_count <= 100).
        
        EXCLUDES sensitive demographic columns (race, ethnicity, gender, etc.)
        that shouldn't be surfaced unless specifically requested.
        """
        # Columns to exclude from automatic breakdowns (sensitive demographics)
        EXCLUDED_PATTERNS = [
            'ethnic', 'ethnicity', 'race', 'gender', 'sex', 'religion',
            'disability', 'veteran', 'marital', 'nationality'
        ]
        
        try:
            results = self.conn.execute("""
                SELECT column_name, filter_category, distinct_count, inferred_type
                FROM _column_profiles
                WHERE LOWER(project) = LOWER(?)
                  AND LOWER(table_name) = LOWER(?)
                  AND filter_category IN ('company', 'location', 'general', 'status')
                  AND distinct_count > 1
                  AND distinct_count <= 100
                ORDER BY 
                    CASE filter_category 
                        WHEN 'status' THEN 1
                        WHEN 'company' THEN 2 
                        WHEN 'location' THEN 3
                        ELSE 4 
                    END,
                    distinct_count ASC
            """, [project, table_name]).fetchall()
            
            # Filter out sensitive columns
            filtered = []
            for r in results:
                col_name_lower = r[0].lower()
                if any(pattern in col_name_lower for pattern in EXCLUDED_PATTERNS):
                    logger.info(f"[RESOLVER] Excluding sensitive column from breakdowns: {r[0]}")
                    continue
                filtered.append({
                    'column_name': r[0],
                    'filter_category': r[1],
                    'distinct_count': r[2],
                    'inferred_type': r[3]
                })
            
            return filtered
        except Exception as e:
            logger.error(f"[RESOLVER] Error looking up dimensional columns: {e}")
            return []
    
    def _run_breakdown_query(
        self, 
        table_name: str, 
        group_column: str,
        filter_column: Optional[str] = None,
        filter_values: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> Optional[Dict]:
        """
        Run a GROUP BY query to get breakdown counts.
        
        Args:
            table_name: Table to query
            group_column: Column to group by
            filter_column: Optional column to filter on (e.g., status)
            filter_values: Optional values to filter for (e.g., ['A'])
            limit: Optional limit on results (for high-cardinality dimensions)
            
        Returns:
            Dict mapping dimension values to counts, e.g., {'A': 3976, 'T': 10462}
        """
        try:
            # Build query
            if filter_column and filter_values:
                values_sql = ', '.join(f"'{v}'" for v in filter_values)
                sql = f'''
                    SELECT "{group_column}", COUNT(*) as cnt 
                    FROM "{table_name}" 
                    WHERE "{filter_column}" IN ({values_sql})
                    GROUP BY "{group_column}"
                    ORDER BY cnt DESC
                '''
            else:
                sql = f'''
                    SELECT "{group_column}", COUNT(*) as cnt 
                    FROM "{table_name}" 
                    GROUP BY "{group_column}"
                    ORDER BY cnt DESC
                '''
            
            if limit:
                sql += f' LIMIT {limit}'
            
            results = self.conn.execute(sql).fetchall()
            
            # Convert to dict
            breakdown = {}
            for row in results:
                key = str(row[0]) if row[0] is not None else '(null)'
                breakdown[key] = row[1]
            
            return breakdown if breakdown else None
            
        except Exception as e:
            logger.warning(f"[RESOLVER] Breakdown query failed for {group_column}: {e}")
            return None
    
    # =========================================================================
    # LOOKUP METHODS - These query our pre-computed intelligence
    # =========================================================================
    
    def _lookup_table(self, project: str, domain: str, table_type: str) -> Optional[Dict]:
        """
        LOOKUP a table by domain and type.
        
        Since _table_classifications may not exist, we query _schema_metadata
        directly with entity_type and truth_type filtering.
        
        For domain='demographics', table_type='master':
        → Find reality table with entity_type containing 'personal'
        """
        try:
            # Check cache first
            cache_key = f"{project}:{domain}:{table_type}"
            if cache_key in self._table_classifications_cache:
                return self._table_classifications_cache[cache_key]
            
            # Map domain + type to entity_type patterns
            if domain == 'demographics' and table_type == 'master':
                # Employee master table - look for 'personal' entity_type
                result = self.conn.execute("""
                    SELECT table_name, entity_type, row_count, column_count, display_name
                    FROM _schema_metadata
                    WHERE LOWER(project) = LOWER(?)
                      AND truth_type = 'reality'
                      AND is_current = TRUE
                      AND (LOWER(entity_type) LIKE '%personal%')
                    ORDER BY row_count DESC
                    LIMIT 1
                """, [project]).fetchone()
                
                if result:
                    table_info = {
                        'table_name': result[0],
                        'entity_type': result[1],
                        'row_count': result[2],
                        'column_count': result[3],
                        'display_name': result[4] or result[0]
                    }
                    self._table_classifications_cache[cache_key] = table_info
                    logger.info(f"[RESOLVER] LOOKUP table: domain={domain} → {result[0]} (entity_type={result[1]})")
                    return table_info
            
            # Try _table_classifications if it exists (for other domains)
            try:
                result = self.conn.execute("""
                    SELECT table_name, domain, table_type, primary_entity, 
                           row_count, column_count, confidence
                    FROM _table_classifications
                    WHERE project_name = ?
                      AND LOWER(domain) = LOWER(?)
                      AND LOWER(table_type) = LOWER(?)
                    ORDER BY confidence DESC, row_count DESC
                    LIMIT 1
                """, [project, domain, table_type]).fetchone()
                
                if result:
                    table_info = {
                        'table_name': result[0],
                        'domain': result[1],
                        'table_type': result[2],
                        'primary_entity': result[3],
                        'row_count': result[4],
                        'column_count': result[5],
                        'confidence': result[6]
                    }
                    self._table_classifications_cache[cache_key] = table_info
                    logger.info(f"[RESOLVER] LOOKUP table (classifications): domain={domain}, type={table_type} → {result[0]}")
                    return table_info
            except Exception as e:
                # _table_classifications doesn't exist, fall through
                logger.debug(f"[RESOLVER] _table_classifications not available: {e}")
            
            logger.warning(f"[RESOLVER] LOOKUP MISS: No table found for domain={domain}, type={table_type}")
            return None
            
        except Exception as e:
            logger.error(f"[RESOLVER] LOOKUP ERROR: {e}")
            return None
    
    def _lookup_table_by_name(self, project: str, name_patterns: List[str]) -> Optional[Dict]:
        """
        Fallback: LOOKUP table by name pattern from _schema_metadata.
        
        Used when _table_classifications doesn't have what we need.
        """
        try:
            project_prefix = project.lower().replace(' ', '_').replace('-', '_')
            
            for pattern in name_patterns:
                result = self.conn.execute("""
                    SELECT table_name, entity_type, row_count, column_count
                    FROM _schema_metadata
                    WHERE LOWER(project) = LOWER(?)
                      AND (LOWER(table_name) LIKE ? OR LOWER(entity_type) LIKE ?)
                    ORDER BY row_count DESC
                    LIMIT 1
                """, [project, f"%{pattern}%", f"%{pattern}%"]).fetchone()
                
                if result:
                    logger.info(f"[RESOLVER] FALLBACK LOOKUP: pattern={pattern} → {result[0]}")
                    return {
                        'table_name': result[0],
                        'entity_type': result[1],
                        'row_count': result[2],
                        'column_count': result[3]
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"[RESOLVER] FALLBACK LOOKUP ERROR: {e}")
            return None
    
    def _lookup_status_column(self, project: str, table_name: str) -> Optional[Dict]:
        """
        LOOKUP the status column from _column_profiles.
        
        Uses filter_category='status' that we computed at upload time.
        Prioritizes employment_status columns over other status columns.
        """
        try:
            # First: Look for employment_status columns with filter_category='status'
            result = self.conn.execute("""
                SELECT column_name, filter_category, filter_priority,
                       distinct_count, distinct_values, inferred_type
                FROM _column_profiles
                WHERE LOWER(project) = LOWER(?)
                  AND LOWER(table_name) = LOWER(?)
                  AND filter_category = 'status'
                  AND LOWER(column_name) LIKE '%employment%status%'
                ORDER BY filter_priority DESC
                LIMIT 1
            """, [project, table_name]).fetchone()
            
            if result:
                logger.info(f"[RESOLVER] LOOKUP employment status column: {result[0]}")
                return {
                    'column_name': result[0],
                    'filter_category': result[1],
                    'filter_priority': result[2],
                    'distinct_count': result[3],
                    'distinct_values': result[4],
                    'inferred_type': result[5]
                }
            
            # Second: Any column with filter_category='status'
            result = self.conn.execute("""
                SELECT column_name, filter_category, filter_priority,
                       distinct_count, distinct_values, inferred_type
                FROM _column_profiles
                WHERE LOWER(project) = LOWER(?)
                  AND LOWER(table_name) = LOWER(?)
                  AND filter_category = 'status'
                ORDER BY filter_priority DESC
                LIMIT 1
            """, [project, table_name]).fetchone()
            
            if result:
                logger.info(f"[RESOLVER] LOOKUP status column: {result[0]} (filter_category=status)")
                return {
                    'column_name': result[0],
                    'filter_category': result[1],
                    'filter_priority': result[2],
                    'distinct_count': result[3],
                    'distinct_values': result[4],
                    'inferred_type': result[5]
                }
            
            # Fallback: Look for column with 'employment' and 'status' in name
            result = self.conn.execute("""
                SELECT column_name, filter_category, filter_priority,
                       distinct_count, distinct_values, inferred_type
                FROM _column_profiles
                WHERE LOWER(project) = LOWER(?)
                  AND LOWER(table_name) = LOWER(?)
                  AND LOWER(column_name) LIKE '%employment%'
                  AND LOWER(column_name) LIKE '%status%'
                  AND distinct_count <= 20
                ORDER BY distinct_count ASC
                LIMIT 1
            """, [project, table_name]).fetchone()
            
            if result:
                logger.info(f"[RESOLVER] FALLBACK employment status column: {result[0]} (name match)")
                return {
                    'column_name': result[0],
                    'filter_category': result[1],
                    'filter_priority': result[2],
                    'distinct_count': result[3],
                    'distinct_values': result[4],
                    'inferred_type': result[5]
                }
            
            # Last fallback: Any column with 'status' in name and low cardinality
            result = self.conn.execute("""
                SELECT column_name, filter_category, filter_priority,
                       distinct_count, distinct_values, inferred_type
                FROM _column_profiles
                WHERE LOWER(project) = LOWER(?)
                  AND LOWER(table_name) = LOWER(?)
                  AND LOWER(column_name) LIKE '%status%'
                  AND distinct_count <= 20
                ORDER BY distinct_count ASC
                LIMIT 1
            """, [project, table_name]).fetchone()
            
            if result:
                logger.info(f"[RESOLVER] FALLBACK status column: {result[0]} (name match)")
                return {
                    'column_name': result[0],
                    'filter_category': result[1],
                    'filter_priority': result[2],
                    'distinct_count': result[3],
                    'distinct_values': result[4],
                    'inferred_type': result[5]
                }
            
            logger.warning(f"[RESOLVER] No status column found for {table_name}")
            return None
            
        except Exception as e:
            logger.error(f"[RESOLVER] STATUS COLUMN LOOKUP ERROR: {e}")
            return None
    
    def _infer_active_status_values(self, distinct_values: List) -> List[str]:
        """
        Infer which status values mean "active".
        
        This uses simple pattern matching. In the future, this could:
        1. Check _intelligence_lookups for known mappings
        2. Use semantic vocabulary
        3. Cache user confirmations
        
        Common patterns:
        - 'A', 'Active', 'ACT' = active
        - 'T', 'Terminated', 'TERM' = terminated
        - 'L', 'Leave', 'LOA' = leave
        """
        if not distinct_values:
            return []
        
        active_patterns = ['a', 'active', 'act', 'current', 'employed', 'working', 'full', 'part']
        
        active_values = []
        for val in distinct_values:
            val_str = str(val).strip()
            val_lower = val_str.lower()
            
            # Check if this looks like an active status
            if val_lower in active_patterns:
                active_values.append(val_str)
            elif any(pattern in val_lower for pattern in ['active', 'current', 'employed']):
                active_values.append(val_str)
        
        # If we found nothing but there's a single-letter 'A', use it
        if not active_values:
            for val in distinct_values:
                if str(val).strip().upper() == 'A':
                    active_values.append(str(val).strip())
                    break
        
        logger.info(f"[RESOLVER] Inferred active values: {active_values} from {distinct_values}")
        return active_values
    
    # =========================================================================
    # GENERIC RESOLVERS
    # =========================================================================
    
    def _resolve_generic_count(self, project: str, parsed: ParsedIntent,
                                result: ResolvedQuery) -> ResolvedQuery:
        """
        Resolve a COUNT query for non-employee domains.
        """
        domain = parsed.domain.value
        
        # LOOKUP table for this domain
        table = self._lookup_table(project, domain, 'master')
        if not table:
            table = self._lookup_table(project, domain, 'config')
        if not table:
            table = self._lookup_table(project, domain, 'transaction')
        
        if not table:
            result.explanation = f"Could not find table for domain '{domain}'"
            return result
        
        table_name = table['table_name']
        result.table_name = table_name
        result.sql = f'SELECT COUNT(*) as total FROM "{table_name}"'
        result.explanation = f"Counting rows in {table_name}"
        result.success = True
        return result
    
    def _resolve_list(self, project: str, parsed: ParsedIntent,
                      result: ResolvedQuery) -> ResolvedQuery:
        """
        Resolve a LIST query.
        """
        domain = parsed.domain.value
        
        # LOOKUP table for this domain
        table = self._lookup_table(project, domain, 'config')
        if not table:
            table = self._lookup_table(project, domain, 'master')
        
        if not table:
            result.explanation = f"Could not find table for domain '{domain}'"
            return result
        
        table_name = table['table_name']
        result.table_name = table_name
        result.sql = f'SELECT * FROM "{table_name}" LIMIT 100'
        result.explanation = f"Listing rows from {table_name}"
        result.success = True
        return result


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

def resolve_query(question: str, project: str, handler) -> ResolvedQuery:
    """
    Convenience function to resolve a query.
    
    Usage:
        result = resolve_query("what's the headcount?", "TEA1000", handler)
        if result.success:
            rows = handler.conn.execute(result.sql).fetchall()
    """
    resolver = QueryResolver(handler)
    return resolver.resolve(question, project)
