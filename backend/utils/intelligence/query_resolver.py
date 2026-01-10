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
    
    # Extract filter hints (phrases like "in Texas", "in Pasadena", "at location X")
    filter_hints = []
    
    import re
    
    # Pattern 1: "in/at/for/from <something>" - greedy match to end of phrase
    # Handles: "in Pasadena", "in TNC", "at Hammond division"
    in_matches = re.findall(r'\b(?:in|at|for|from)\s+([A-Za-z][A-Za-z0-9\s\-]*?)(?:\s+(?:division|department|location|team|region|org|area|pay\s*group)|[,\.\?]|$)', q_lower)
    for match in in_matches:
        cleaned = match.strip()
        if len(cleaned) >= 2:  # Allow 2+ char codes like "IT"
            filter_hints.append(cleaned)
    
    # Pattern 2: "who are <status>" or "who is <status>"
    status_patterns = re.findall(r'\bwho\s+(?:are|is)\s+(\w+)', q_lower)
    filter_hints.extend([p.strip() for p in status_patterns])
    
    # Pattern 3: ALL CAPS codes that might be pay groups, company codes, etc.
    # E.g., "TNC", "R2S", "USA"
    caps_codes = re.findall(r'\b([A-Z][A-Z0-9]{1,5})\b', question)  # Original case
    for code in caps_codes:
        if code.lower() not in filter_hints and code.lower() not in {'how', 'the', 'and', 'for'}:
            filter_hints.append(code.lower())
    
    # Pattern 4: Capitalized words (proper nouns) - fallback
    if not filter_hints:
        common_words = {'how', 'many', 'employees', 'are', 'there', 'in', 'the', 'what', 'is', 'count', 'total', 'number', 'of'}
        words = question.split()
        for word in words:
            if len(word) > 2 and word[0].isupper() and word.lower() not in common_words:
                filter_hints.append(word.lower())
    
    return ParsedIntent(
        intent=intent,
        domain=domain,
        raw_question=question,
        filter_hints=filter_hints,
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
        
        # LOOKUP 5: Resolve dimension filters from parsed hints
        dimension_filters = []
        if parsed.filter_hints:
            result.resolution_path.append(f"FILTER HINTS: {parsed.filter_hints}")
            
            for hint in parsed.filter_hints:
                resolved = self._resolve_dimension_filter(project, hint)
                if resolved:
                    # Find which column in employee data matches this semantic type
                    column_info = self._find_employee_column_for_dimension(
                        project, table_name, resolved['semantic_type']
                    )
                    if column_info:
                        dimension_filters.append({
                            'column': column_info['column'],
                            'table': column_info['table'],
                            'same_table': column_info['same_table'],
                            'codes': resolved['codes'],
                            'hint': hint,
                            'semantic_type': resolved['semantic_type'],
                            'descriptions': resolved.get('matched_descriptions', [])
                        })
                        result.resolution_path.append(
                            f"RESOLVED: '{hint}' -> {column_info['table']}.{column_info['column']} IN {resolved['codes'][:3]}..."
                        )
        
        # Check if we need cross-table JOINs
        needs_join = any(not f['same_table'] for f in dimension_filters)
        join_tables = set(f['table'] for f in dimension_filters if not f['same_table'])
        
        # GENERATE SQL
        if needs_join and join_tables:
            # Need to JOIN to filter tables
            # Get join keys from Context Graph
            join_parts = []
            from_tables = [f'"{table_name}" p']
            
            for i, join_table in enumerate(join_tables):
                alias = f'd{i}'
                join_keys = self._get_join_keys_from_context_graph(project, table_name, join_table)
                
                if join_keys:
                    join_conditions = []
                    for p_col, d_col in join_keys:
                        join_conditions.append(f'TRIM(p."{p_col}") = TRIM({alias}."{d_col}")')
                    join_clause = ' AND '.join(join_conditions)
                    from_tables.append(f'JOIN "{join_table}" {alias} ON {join_clause}')
            
            from_sql = '\n'.join(from_tables)
            
            where_clauses = []
            
            # Status filter (always on primary table)
            if active_values:
                values_sql = ', '.join(f"'{v}'" for v in active_values)
                where_clauses.append(f'p."{status_column["column_name"]}" IN ({values_sql})')
            
            # Dimension filters
            for dim_filter in dimension_filters:
                codes_sql = ', '.join(f"'{c}'" for c in dim_filter['codes'])
                if dim_filter['same_table']:
                    where_clauses.append(f'TRIM(p."{dim_filter["column"]}") IN ({codes_sql})')
                else:
                    # Find the alias for this table
                    alias_idx = list(join_tables).index(dim_filter['table'])
                    alias = f'd{alias_idx}'
                    where_clauses.append(f'TRIM({alias}."{dim_filter["column"]}") IN ({codes_sql})')
            
            where_sql = ' AND '.join(where_clauses) if where_clauses else '1=1'
            
            result.sql = f'''SELECT COUNT(DISTINCT p."employee_number") as headcount 
FROM {from_sql}
WHERE {where_sql}'''
            
        else:
            # Simple case - all filters in same table
            where_clauses = []
            
            # Status filter
            if active_values:
                values_sql = ', '.join(f"'{v}'" for v in active_values)
                where_clauses.append(f'"{status_column["column_name"]}" IN ({values_sql})')
            
            # Dimension filters
            for dim_filter in dimension_filters:
                codes_sql = ', '.join(f"'{c}'" for c in dim_filter['codes'])
                where_clauses.append(f'TRIM("{dim_filter["column"]}") IN ({codes_sql})')
            
            if where_clauses:
                where_sql = ' AND '.join(where_clauses)
                result.sql = f'''SELECT COUNT(*) as headcount 
FROM "{table_name}" 
WHERE {where_sql}'''
            else:
                result.sql = f'SELECT COUNT(*) as headcount FROM "{table_name}"'
        
        # Build explanation
        explanation_parts = []
        if active_values:
            explanation_parts.append(f"{status_column['column_name']} in {active_values}")
        for dim_filter in dimension_filters:
            desc_preview = dim_filter['descriptions'][0] if dim_filter['descriptions'] else dim_filter['codes'][0]
            explanation_parts.append(f"{dim_filter['hint']} ({desc_preview})")
        
        if explanation_parts:
            result.explanation = f"Counting active employees where {' and '.join(explanation_parts)}"
        else:
            result.explanation = f"Counting all rows in {table_name}"
        
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
        
        v2.0: Uses Context Graph for ALL segmentation axes (8-12 dimensions).
        
        This is what separates a $5/hr data dump from a $500/hr consultant.
        We don't just answer the question - we provide the context needed
        to understand what the answer MEANS.
        
        Runs queries to get breakdowns for ALL organizational dimensions:
        1. Status breakdown (A/L/T)
        2. Company breakdown
        3. Country/Region breakdown  
        4. Location breakdown (top 10)
        5. Org Level 1-4 breakdowns
        6. Pay Group breakdown
        7. Employee Type breakdown (FT/PT)
        8. Hourly/Salary breakdown
        9. Union breakdown (if applicable)
        
        Args:
            project: Project name
            table_name: The employee table
            status_column: Status column name (if found)
            active_values: Values that mean "active"
            
        Returns:
            Dict with answer, breakdowns (all dimensions), and total
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
                breakdown = self._run_breakdown_query(table_name, status_column, project=project)
                if breakdown:
                    context['breakdowns']['by_status'] = breakdown
            
            # Query 4+: Dimensional breakdowns from Context Graph
            # v3.0: Query the SOURCE TABLE for each dimension (not just primary table)
            MAX_BREAKDOWNS = 12  # All segmentation axes: status, company, location, org_levels, pay_group, etc.
            
            for dim_col in dimensional_columns:
                # Stop if we have enough breakdowns
                if len(context['breakdowns']) >= MAX_BREAKDOWNS:
                    break
                    
                col_name = dim_col['column_name']
                semantic_type = dim_col.get('semantic_type', 'general')
                distinct_count = dim_col.get('distinct_count', 0)
                source_table = dim_col.get('source_table', table_name)  # Use source table, fallback to primary
                hub_table = dim_col.get('hub_table')
                hub_column = dim_col.get('hub_column')
                
                # Skip status column if it's from the primary table (already handled above)
                if col_name == status_column and source_table.lower() == table_name.lower():
                    continue
                
                # Skip if cardinality too high (except location which we limit)
                is_location = 'location' in semantic_type.lower()
                if distinct_count > 50 and not is_location:
                    continue
                
                # Build breakdown key from semantic_type
                key = f"by_{semantic_type.lower()}"
                
                # Skip if we already have this breakdown type
                if key in context['breakdowns']:
                    continue
                
                # Run the breakdown query AGAINST THE SOURCE TABLE
                # For dimensions from other tables (like Company), we still want active employees
                # so we need to join back or query with employee filter
                breakdown = self._run_breakdown_query_cross_table(
                    project=project,
                    primary_table=table_name,
                    dimension_table=source_table,
                    dimension_column=col_name,
                    status_column=status_column,
                    active_values=active_values,
                    hub_table=hub_table,
                    hub_column=hub_column,
                    limit=10 if is_location else None
                )
                
                if breakdown:
                    context['breakdowns'][key] = breakdown
                    logger.info(f"[RESOLVER] Added breakdown: {key} from {source_table[:40]} with {len(breakdown)} values")
                    
        except Exception as e:
            logger.error(f"[RESOLVER] Error gathering reality context: {e}")
        
        return context
    
    def _lookup_dimensional_columns(self, project: str, table_name: str) -> List[Dict]:
        """
        Find columns suitable for dimensional breakdowns via Context Graph LOOKUP.
        
        v3.0 REWRITE: Finds dimensions from ALL reality tables, not just primary.
        
        The personal table has status/company, but Company table has org_levels,
        location, etc. We need to merge dimensions across all related employee tables.
        
        This captures ALL 8-12 segmentation axes:
        - Company, Country, Location
        - Org Level 1-4
        - Pay Group, Employee Type, Hourly/Salary
        - Status, Union (if applicable)
        
        EXCLUDES sensitive demographic columns (race, ethnicity, gender, etc.)
        """
        # Columns to exclude from automatic breakdowns (sensitive demographics)
        EXCLUDED_PATTERNS = [
            'ethnic', 'ethnicity', 'race', 'gender', 'sex', 'religion',
            'disability', 'veteran', 'marital', 'nationality'
        ]
        
        # Segmentation dimension priority (determines order of breakdowns)
        SEGMENTATION_PRIORITY = {
            'employee_status': 1,
            'employment_status': 1,
            'status': 1,
            'company': 2,
            'company_code': 2,
            'home_company': 2,
            'home_company_code': 2,
            'component_company': 2,
            'component_company_code': 2,
            'country': 3,
            'country_code': 3,
            'location': 4,
            'location_code': 4,
            'work_location': 4,
            'primary_work_location': 4,
            'primary_work_location_code': 4,
            'org_level_1': 5,
            'org_level_1_code': 5,
            'org_level_2': 6,
            'org_level_2_code': 6,
            'org_level_3': 7,
            'org_level_3_code': 7,
            'org_level_4': 8,
            'org_level_4_code': 8,
            'suborg_levels': 5,
            'suborg_levels_code': 5,
            'pay_group': 9,
            'pay_group_code': 9,
            'employee_type': 10,
            'employee_type_code': 10,
            'emp_type': 10,
            'hourly_salary': 11,
            'hourly_or_salaried': 11,
            'flsa_status': 11,
            'exempt_status': 11,
            'full_part_time': 12,
            'full_time_or_part_time': 12,
            'ft_pt': 12,
            'union': 13,
            'union_code': 13,
        }
        
        dimensions = []
        seen_semantic_types = set()
        
        try:
            # LOOKUP: Get Context Graph
            if not hasattr(self.handler, 'get_context_graph'):
                logger.warning("[RESOLVER] Handler missing get_context_graph")
                return []
            
            graph = self.handler.get_context_graph(project)
            relationships = graph.get('relationships', [])
            
            logger.info(f"[RESOLVER] Context Graph has {len(relationships)} relationships")
            
            # STEP 1: Find ALL reality tables
            # Strategy: Start with primary table, then find ALL tables that share employee relationships
            reality_tables = set()
            reality_tables.add(table_name.lower())  # Always include primary table
            
            # Find other reality tables from relationships
            # A reality table is any spoke that ISN'T a config hub
            hubs = set(h.get('table', '').lower() for h in graph.get('hubs', []))
            
            for rel in relationships:
                spoke_table = rel.get('spoke_table', '').lower()
                truth_type = rel.get('truth_type', '')
                
                # Skip if this spoke IS a hub (config table referencing another config)
                if spoke_table in hubs:
                    continue
                
                # Add if explicitly marked as reality
                if truth_type == 'reality':
                    reality_tables.add(spoke_table)
                    continue
                
                # Also add if it looks like an employee table (has employee patterns in name)
                employee_patterns = ['personal', 'company', 'job', 'employee', 'worker', 'payroll', 'compensation']
                if any(p in spoke_table for p in employee_patterns):
                    reality_tables.add(spoke_table)
            
            logger.warning(f"[RESOLVER] Found {len(reality_tables)} reality tables: {list(reality_tables)[:8]}")
            
            # STEP 2: Get dimensional columns from ALL reality tables
            # WHITELIST ONLY - semantic_type MUST be in SEGMENTATION_PRIORITY
            # No fallbacks, no guessing, no garbage
            for rel in relationships:
                spoke_table = rel.get('spoke_table', '')
                spoke_column = rel.get('spoke_column', '')
                semantic_type = rel.get('semantic_type', '')
                spoke_cardinality = rel.get('spoke_cardinality', 0)
                
                # Only include dimensions from reality tables
                if spoke_table.lower() not in reality_tables:
                    continue
                
                # WHITELIST ONLY - semantic_type must be in priority list
                # No column name fallback - that lets garbage through
                priority = SEGMENTATION_PRIORITY.get(semantic_type.lower(), None)
                if priority is None:
                    continue  # Not a known segmentation axis - skip
                
                # Skip if already have this semantic type
                if semantic_type.lower() in seen_semantic_types:
                    continue
                
                # Skip sensitive columns
                if any(pattern in spoke_column.lower() for pattern in EXCLUDED_PATTERNS):
                    continue
                
                # Skip very high cardinality (> 100 means it's not a useful breakdown)
                # But allow 0 (schema-matched, cardinality unknown)
                if spoke_cardinality > 100:
                    continue
                
                # Skip cardinality of exactly 1 (useless breakdown - only one value)
                # But allow 0 (schema-matched, cardinality unknown - we'll query it)
                if spoke_cardinality == 1:
                    continue
                
                seen_semantic_types.add(semantic_type.lower())
                
                dimensions.append({
                    'column_name': spoke_column,
                    'semantic_type': semantic_type,
                    'source_table': spoke_table,  # Track which table this comes from
                    'hub_table': rel.get('hub_table'),
                    'hub_column': rel.get('hub_column'),
                    'distinct_count': spoke_cardinality,
                    'priority': priority,
                    'hub_cardinality': rel.get('hub_cardinality', 0),
                    'coverage_pct': rel.get('coverage_pct', 0),
                })
            
            # Sort by priority
            dimensions.sort(key=lambda x: x.get('priority', 50))
            
            # Log what we found
            if dimensions:
                logger.warning(f"[RESOLVER] Found {len(dimensions)} segmentation dimensions from {len(reality_tables)} reality tables")
                logger.warning(f"[RESOLVER] Dimensions: {[d['semantic_type'] for d in dimensions]}")
                logger.warning(f"[RESOLVER] From tables: {set(d['source_table'][:40] for d in dimensions)}")
            else:
                logger.warning(f"[RESOLVER] NO segmentation dimensions found! Reality tables: {list(reality_tables)[:5]}")
            
            return dimensions
            
        except Exception as e:
            logger.error(f"[RESOLVER] Error looking up dimensional columns: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _run_breakdown_query(
        self, 
        table_name: str, 
        group_column: str,
        filter_column: Optional[str] = None,
        filter_values: Optional[List[str]] = None,
        hub_table: Optional[str] = None,
        hub_column: Optional[str] = None,
        project: Optional[str] = None,
        limit: Optional[int] = None
    ) -> Optional[Dict]:
        """
        Run a GROUP BY query to get breakdown counts.
        
        v4.0: Enriches breakdown with descriptions from hub table when available.
        v4.1: Special handling for org_level lookups (filtered join on level column).
        
        Args:
            table_name: Table to query
            group_column: Column to group by
            filter_column: Optional column to filter on (e.g., status)
            filter_values: Optional values to filter for (e.g., ['A'])
            hub_table: Optional hub table for description lookup
            hub_column: Optional hub key column
            project: Optional project name (needed for org_level lookup)
            limit: Optional limit on results (for high-cardinality dimensions)
            
        Returns:
            Dict mapping dimension values to counts, e.g., {'A': 3976, 'T': 10462}
            With hub: {'A (Active)': 3976, 'T (Terminated)': 10462}
        """
        try:
            # Check for org_level special handling (filtered lookup)
            org_level_info = None
            if project:
                org_level_info = self._get_org_level_lookup_info(project, group_column)
            
            # Check if we can get description from hub (or org_level table)
            desc_column = None
            hub_join = ""
            hub_select = ""
            hub_group = ""
            
            if org_level_info:
                # Use org_level filtered lookup
                # NOTE: TRIM needed because employee data often has padded org codes
                org_table = org_level_info['table']
                org_level_num = org_level_info['level']
                hub_join = f'LEFT JOIN "{org_table}" h ON TRIM(t."{group_column}") = TRIM(h."code") AND h."level" = \'{org_level_num}\''
                hub_select = ', h."description" as description'
                hub_group = ', h."description"'
                desc_column = 'description'
                logger.info(f"[RESOLVER] Using org_level filtered lookup: level={org_level_num}")
            elif hub_table and hub_column and not hub_table.startswith('_virtual_'):
                desc_column = self._find_description_column(hub_table, hub_column)
                if desc_column:
                    # TRIM both sides - UKG data often has padded codes
                    hub_join = f'LEFT JOIN "{hub_table}" h ON TRIM(t."{group_column}") = TRIM(h."{hub_column}")'
                    hub_select = f', h."{desc_column}" as description'
                    hub_group = f', h."{desc_column}"'
            
            # Build query
            if filter_column and filter_values:
                values_sql = ', '.join(f"'{v}'" for v in filter_values)
                if hub_join:
                    sql = f'''
                        SELECT t."{group_column}"{hub_select}, COUNT(*) as cnt 
                        FROM "{table_name}" t
                        {hub_join}
                        WHERE t."{filter_column}" IN ({values_sql})
                        GROUP BY t."{group_column}"{hub_group}
                        ORDER BY cnt DESC
                    '''
                else:
                    sql = f'''
                        SELECT "{group_column}", COUNT(*) as cnt 
                        FROM "{table_name}" 
                        WHERE "{filter_column}" IN ({values_sql})
                        GROUP BY "{group_column}"
                        ORDER BY cnt DESC
                    '''
            else:
                if hub_join:
                    sql = f'''
                        SELECT t."{group_column}"{hub_select}, COUNT(*) as cnt 
                        FROM "{table_name}" t
                        {hub_join}
                        GROUP BY t."{group_column}"{hub_group}
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
            
            # Convert to dict - include description if available
            breakdown = {}
            for row in results:
                code = str(row[0]) if row[0] is not None else '(null)'
                count = row[-1]  # Count is always last
                
                if desc_column and len(row) > 2:
                    desc = row[1]
                    if desc and str(desc).strip():
                        key = f"{code} ({desc})"
                    else:
                        key = code
                else:
                    key = code
                    
                breakdown[key] = count
            
            return breakdown if breakdown else None
            
        except Exception as e:
            logger.warning(f"[RESOLVER] Breakdown query failed for {group_column}: {e}")
            return None
    
    def _run_breakdown_query_cross_table(
        self,
        project: str,
        primary_table: str,
        dimension_table: str,
        dimension_column: str,
        status_column: Optional[str],
        active_values: Optional[List[str]],
        hub_table: Optional[str] = None,
        hub_column: Optional[str] = None,
        limit: Optional[int] = None
    ) -> Optional[Dict]:
        """
        Run breakdown query that may span multiple tables.
        
        v3.0: Handles dimensions in related employee tables (e.g., Company table
        has org_levels while Personal table has status).
        
        v4.0: Enriches breakdown with descriptions from hub table when available.
        
        v4.1: Special handling for org_level lookups (filtered join on level column).
        
        Strategy:
        1. If dimension_table == primary_table, simple query
        2. If different tables, find shared hubs from Context Graph → join keys
        3. Apply active filter from primary table
        4. If hub_table provided, join to get description
        5. For org_level columns, use filtered join on organization table
        
        Args:
            project: Project name
            primary_table: The main employee table (has status column)
            dimension_table: Table containing the dimension column
            dimension_column: Column to group by
            status_column: Status column in primary table (for filtering)
            active_values: Active status values
            hub_table: Optional hub table for description lookup
            hub_column: Optional hub key column
            limit: Max results
        """
        try:
            # Same table - simple query
            if dimension_table.lower() == primary_table.lower():
                return self._run_breakdown_query(
                    primary_table, 
                    dimension_column,
                    filter_column=status_column,
                    filter_values=active_values,
                    hub_table=hub_table,
                    hub_column=hub_column,
                    project=project,
                    limit=limit
                )
            
            # Different tables - find join keys from Context Graph
            join_keys = self._get_join_keys_from_context_graph(project, primary_table, dimension_table)
            
            if not join_keys:
                logger.warning(f"[RESOLVER] No shared hubs between {primary_table[:30]} and {dimension_table[:30]}")
                # Fallback: query dimension table without filter
                return self._run_breakdown_query(dimension_table, dimension_column, hub_table=hub_table, hub_column=hub_column, project=project, limit=limit)
            
            # Build JOIN clause for all shared hub columns
            # TRIM both sides - UKG data often has padded codes/numbers
            join_conditions = []
            for primary_col, dimension_col in join_keys:
                join_conditions.append(f'TRIM(p."{primary_col}") = TRIM(d."{dimension_col}")')
            
            join_clause = ' AND '.join(join_conditions)
            
            # Use first join key for COUNT DISTINCT (usually employee_number)
            count_column = join_keys[0][0]
            
            # Check for org_level special handling (filtered lookup)
            org_level_info = self._get_org_level_lookup_info(project, dimension_column)
            
            # Check if we can get description from hub (or org_level table)
            desc_column = None
            hub_join = ""
            hub_select = ""
            hub_group = ""
            
            if org_level_info:
                # Use org_level filtered lookup
                # NOTE: TRIM needed because employee data often has padded org codes
                org_table = org_level_info['table']
                org_level_num = org_level_info['level']
                hub_join = f'LEFT JOIN "{org_table}" h ON TRIM(d."{dimension_column}") = TRIM(h."code") AND h."level" = \'{org_level_num}\''
                hub_select = ', h."description" as description'
                hub_group = ', h."description"'
                desc_column = 'description'
                logger.info(f"[RESOLVER] Using org_level filtered lookup: level={org_level_num}")
            elif hub_table and hub_column and not hub_table.startswith('_virtual_'):
                desc_column = self._find_description_column(hub_table, hub_column)
                if desc_column:
                    # TRIM both sides - UKG data often has padded codes
                    hub_join = f'LEFT JOIN "{hub_table}" h ON TRIM(d."{dimension_column}") = TRIM(h."{hub_column}")'
                    hub_select = f', h."{desc_column}" as description'
                    hub_group = f', h."{desc_column}"'
            
            # Build JOIN query with active filter
            if status_column and active_values:
                values_sql = ', '.join(f"'{v}'" for v in active_values)
                sql = f'''
                    SELECT d."{dimension_column}"{hub_select}, COUNT(DISTINCT p."{count_column}") as cnt
                    FROM "{primary_table}" p
                    JOIN "{dimension_table}" d ON {join_clause}
                    {hub_join}
                    WHERE p."{status_column}" IN ({values_sql})
                    GROUP BY d."{dimension_column}"{hub_group}
                    ORDER BY cnt DESC
                '''
            else:
                sql = f'''
                    SELECT d."{dimension_column}"{hub_select}, COUNT(DISTINCT p."{count_column}") as cnt
                    FROM "{primary_table}" p
                    JOIN "{dimension_table}" d ON {join_clause}
                    {hub_join}
                    GROUP BY d."{dimension_column}"{hub_group}
                    ORDER BY cnt DESC
                '''
            
            if limit:
                sql += f' LIMIT {limit}'
            
            logger.info(f"[RESOLVER] Cross-table breakdown: {dimension_column} from {dimension_table[:30]}" + 
                       (f" with desc from {hub_table[:30]}" if desc_column else ""))
            
            results = self.conn.execute(sql).fetchall()
            
            # Convert to dict - include description if available
            breakdown = {}
            for row in results:
                code = str(row[0]) if row[0] is not None else '(null)'
                count = row[-1]  # Count is always last
                
                if desc_column and len(row) > 2:
                    desc = row[1]
                    if desc and str(desc).strip():
                        key = f"{code} ({desc})"
                    else:
                        key = code
                else:
                    key = code
                    
                breakdown[key] = count
            
            return breakdown if breakdown else None
            
        except Exception as e:
            logger.warning(f"[RESOLVER] Cross-table breakdown failed for {dimension_column}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            # Fallback: simple query on dimension table (no org level lookup in error case)
            return self._run_breakdown_query(dimension_table, dimension_column, project=project, limit=limit)
    
    def _get_table_columns(self, table_name: str) -> List[str]:
        """Get column names for a table."""
        try:
            # Use description to get column names (works with DuckDB)
            cursor = self.conn.execute(f'SELECT * FROM "{table_name}" LIMIT 1')
            if cursor.description:
                cols = [desc[0] for desc in cursor.description]
                return cols
            logger.warning(f"[RESOLVER] _get_table_columns: no description for {table_name[-30:]}")
            return []
        except Exception as e:
            logger.warning(f"[RESOLVER] _get_table_columns FAILED for {table_name[-30:]}: {e}")
            return []
    
    def _find_description_column(self, table_name: str, key_column: Optional[str] = None) -> Optional[str]:
        """
        Find a description/name column in a hub table.
        
        Common patterns: description, name, desc, label, title
        Also: if key_column is 'pay_group_code', look for 'pay_group'
        
        Returns the column name if found, None otherwise.
        """
        try:
            columns = self._get_table_columns(table_name)
            if not columns:
                logger.warning(f"[RESOLVER] _find_description_column: no columns for {table_name[-30:]}")
                return None
            
            # Priority order for description columns
            desc_patterns = [
                'description',  # Most common
                'name',         # e.g., location_name, job_name
                'desc',         # Short form
                'label',        # UI labels
                'title',        # Job titles
            ]
            
            cols_lower = {c.lower(): c for c in columns}
            
            # First: check for key_column without '_code' suffix
            # e.g., pay_group_code -> pay_group
            if key_column:
                key_lower = key_column.lower()
                if key_lower.endswith('_code'):
                    base_name = key_lower[:-5]  # Remove '_code'
                    if base_name in cols_lower:
                        return cols_lower[base_name]
                elif key_lower.endswith('_id'):
                    base_name = key_lower[:-3]  # Remove '_id'
                    if base_name in cols_lower:
                        return cols_lower[base_name]
            
            # Second: exact match on common patterns
            for pattern in desc_patterns:
                if pattern in cols_lower:
                    return cols_lower[pattern]
            
            # Third: contains pattern (e.g., job_description, location_name)
            for pattern in desc_patterns:
                for col_lower, col_original in cols_lower.items():
                    if pattern in col_lower and col_lower not in ['id', 'code']:
                        return col_original
            
            return None
            
        except Exception as e:
            logger.debug(f"[RESOLVER] Error finding description column in {table_name}: {e}")
            return None
    
    def _get_org_level_lookup_info(self, project: str, dimension_column: str) -> Optional[Dict]:
        """
        Check if this dimension needs org_level filtered lookup.
        
        Org levels in UKG are stored in a single Organization table with a 'level' column
        that indicates which org level (1, 2, 3, 4) each code belongs to.
        
        Returns:
            Dict with 'table' and 'level' if this is an org_level column, None otherwise.
        """
        # Check if this is an org_level column
        col_lower = dimension_column.lower().replace('_', '').replace(' ', '')
        
        org_level_map = {
            'orglevel1code': '1',
            'orglevel1': '1',
            'org1': '1',
            'orglevel2code': '2',
            'orglevel2': '2',
            'org2': '2',
            'orglevel3code': '3',
            'orglevel3': '3',
            'org3': '3',
            'orglevel4code': '4',
            'orglevel4': '4',
            'org4': '4',
        }
        
        level_num = org_level_map.get(col_lower)
        if not level_num:
            return None
        
        # Find the organization table for this project
        try:
            result = self.conn.execute("""
                SELECT table_name 
                FROM _schema_metadata 
                WHERE project = ? 
                  AND is_current = TRUE
                  AND LOWER(table_name) LIKE '%organization%'
                  AND LOWER(table_name) NOT LIKE '%virtual%'
                LIMIT 1
            """, [project]).fetchone()
            
            if result:
                org_table = result[0]
                # Verify it has the expected columns (level, code, description)
                try:
                    cols = self.conn.execute(f"PRAGMA table_info('{org_table}')").fetchall()
                    col_names = [c[1].lower() for c in cols]
                    if 'level' in col_names and 'code' in col_names and 'description' in col_names:
                        logger.debug(f"[RESOLVER] Found org_level table: {org_table}")
                        return {'table': org_table, 'level': level_num}
                except:
                    pass
                    
        except Exception as e:
            logger.debug(f"[RESOLVER] Error finding org_level table: {e}")
        
        return None
    
    def _resolve_dimension_filter(self, project: str, filter_hint: str) -> Optional[Dict]:
        """
        Resolve a filter hint (e.g., "Texas", "Pasadena") to dimension column + codes.
        
        Searches hub tables for matching descriptions and returns the codes to filter by.
        
        Args:
            project: Project name
            filter_hint: User's filter phrase (e.g., "texas", "pasadena", "engineering")
            
        Returns:
            Dict with 'column', 'codes', 'hub_table', 'matched_descriptions' if found, None otherwise.
        """
        try:
            if not hasattr(self.handler, 'get_context_graph'):
                logger.warning(f"[RESOLVER] No get_context_graph method on handler")
                return None
            
            graph = self.handler.get_context_graph(project)
            hubs = graph.get('hubs', [])
            
            hint_lower = filter_hint.lower().strip()
            best_match = None
            best_match_count = 0
            
            logger.warning(f"[RESOLVER] Searching {len(hubs)} hubs for '{hint_lower}'")
            logger.warning(f"[RESOLVER] First 3 hubs: {[h.get('table', '')[-30:] for h in hubs[:3]]}")
            
            skipped_virtual = 0
            skipped_no_desc = 0
            checked = 0
            
            # Search each hub table for matching descriptions
            for hub in hubs:
                hub_table = hub.get('table', '')
                hub_column = hub.get('column', '')
                semantic_type = hub.get('semantic_type', '')
                
                # Skip virtual hubs
                if hub_table.startswith('_virtual_'):
                    skipped_virtual += 1
                    continue
                
                # Find description column
                desc_column = self._find_description_column(hub_table, hub_column)
                if not desc_column:
                    skipped_no_desc += 1
                    continue
                
                checked += 1
                logger.warning(f"[RESOLVER] Checking hub {hub_table[-30:]}: key={hub_column}, desc={desc_column}")
                
                # Search for matching descriptions
                try:
                    # Use LIKE for partial matching
                    results = self.conn.execute(f'''
                        SELECT TRIM("{hub_column}") as code, "{desc_column}" as description
                        FROM "{hub_table}"
                        WHERE LOWER("{desc_column}") LIKE ?
                           OR LOWER(TRIM("{hub_column}")) LIKE ?
                    ''', [f'%{hint_lower}%', f'%{hint_lower}%']).fetchall()
                    
                    if results:
                        codes = [str(r[0]) for r in results if r[0]]
                        descriptions = [str(r[1]) for r in results if r[1]]
                        
                        logger.warning(f"[RESOLVER] Found {len(results)} matches for '{hint_lower}' in {hub_table[-30:]}: codes={codes[:3]}")
                        
                        # Prefer matches with more results (more specific)
                        # But also prefer exact matches
                        match_quality = len(results)
                        
                        # Boost for exact description match
                        for desc in descriptions:
                            if hint_lower == desc.lower().strip():
                                match_quality += 100
                            elif hint_lower in desc.lower():
                                match_quality += 10
                        
                        if match_quality > best_match_count:
                            best_match_count = match_quality
                            best_match = {
                                'hub_table': hub_table,
                                'hub_column': hub_column,
                                'semantic_type': semantic_type,
                                'codes': codes,
                                'matched_descriptions': descriptions[:5],  # Limit for logging
                            }
                            
                except Exception as e:
                    logger.warning(f"[RESOLVER] Error searching hub {hub_table}: {e}")
                    continue
            
            logger.warning(f"[RESOLVER] Hub scan: checked={checked}, skipped_virtual={skipped_virtual}, skipped_no_desc={skipped_no_desc}")
            
            # Also check org_level table specially (filtered by level)
            org_table = None
            try:
                result = self.conn.execute("""
                    SELECT table_name 
                    FROM _schema_metadata 
                    WHERE project = ? 
                      AND is_current = TRUE
                      AND LOWER(table_name) LIKE '%organization%'
                      AND LOWER(table_name) NOT LIKE '%virtual%'
                    LIMIT 1
                """, [project]).fetchone()
                if result:
                    org_table = result[0]
            except:
                pass
            
            if org_table:
                try:
                    # Search across all org levels
                    results = self.conn.execute(f'''
                        SELECT level, TRIM(code) as code, description
                        FROM "{org_table}"
                        WHERE LOWER(description) LIKE ?
                           OR LOWER(TRIM(code)) LIKE ?
                    ''', [f'%{hint_lower}%', f'%{hint_lower}%']).fetchall()
                    
                    if results:
                        # Group by level
                        by_level = {}
                        for level, code, desc in results:
                            if level not in by_level:
                                by_level[level] = {'codes': [], 'descriptions': []}
                            by_level[level]['codes'].append(str(code))
                            by_level[level]['descriptions'].append(str(desc))
                        
                        # Take the level with most matches
                        best_level = max(by_level.keys(), key=lambda l: len(by_level[l]['codes']))
                        level_data = by_level[best_level]
                        
                        match_quality = len(level_data['codes']) + 50  # Boost org matches
                        
                        if match_quality > best_match_count:
                            best_match = {
                                'hub_table': org_table,
                                'hub_column': 'code',
                                'semantic_type': f'org_level_{best_level}_code',
                                'org_level': best_level,
                                'codes': level_data['codes'],
                                'matched_descriptions': level_data['descriptions'][:5],
                            }
                            
                except Exception as e:
                    logger.debug(f"[RESOLVER] Error searching org table: {e}")
            
            if best_match:
                logger.info(f"[RESOLVER] Resolved '{filter_hint}' -> {best_match['semantic_type']}: {best_match['codes'][:3]}...")
            else:
                logger.warning(f"[RESOLVER] No match found for '{filter_hint}' in any hub")
                
            return best_match
            
        except Exception as e:
            logger.warning(f"[RESOLVER] Error resolving dimension filter '{filter_hint}': {e}")
            return None
    
    def _find_employee_column_for_dimension(self, project: str, employee_table: str, semantic_type: str) -> Optional[Dict]:
        """
        Find which column in the employee table (or related tables) matches a semantic type.
        
        Uses Context Graph relationships to find the spoke column.
        
        Args:
            project: Project name
            employee_table: Primary employee table name
            semantic_type: The semantic type to find (e.g., 'org_level_1_code', 'location_code')
            
        Returns:
            Dict with 'column' and 'table' if found, None otherwise.
            If 'table' differs from employee_table, a JOIN is needed.
        """
        try:
            if not hasattr(self.handler, 'get_context_graph'):
                return None
            
            graph = self.handler.get_context_graph(project)
            relationships = graph.get('relationships', [])
            
            employee_table_lower = employee_table.lower()
            semantic_type_lower = semantic_type.lower()
            
            logger.warning(f"[RESOLVER] Looking for {semantic_type} column in/near {employee_table[-30:]}")
            
            # First: look for exact table match
            for rel in relationships:
                spoke_table = rel.get('spoke_table', '').lower()
                spoke_column = rel.get('spoke_column', '')
                rel_semantic = rel.get('semantic_type', '').lower()
                
                if spoke_table == employee_table_lower and rel_semantic == semantic_type_lower:
                    logger.warning(f"[RESOLVER] Found dimension column in primary table: {spoke_column}")
                    return {'column': spoke_column, 'table': employee_table, 'same_table': True}
            
            # Second: look in any employee-related table (Personal, Company, etc.)
            employee_patterns = ['personal', 'company', 'employee', 'worker', 'job', 'conversion']
            
            for rel in relationships:
                spoke_table = rel.get('spoke_table', '')
                spoke_column = rel.get('spoke_column', '')
                rel_semantic = rel.get('semantic_type', '').lower()
                
                if rel_semantic == semantic_type_lower:
                    # Check if this is an employee-related table
                    if any(p in spoke_table.lower() for p in employee_patterns):
                        logger.warning(f"[RESOLVER] Found dimension in related table: {spoke_table[-30:]}.{spoke_column}")
                        return {
                            'column': spoke_column, 
                            'table': spoke_table,
                            'same_table': spoke_table.lower() == employee_table_lower
                        }
            
            logger.warning(f"[RESOLVER] No column found for {semantic_type} in employee-related tables")
            return None
            
        except Exception as e:
            logger.warning(f"[RESOLVER] Error finding employee column for {semantic_type}: {e}")
            return None
    
    def _get_join_keys_from_context_graph(self, project: str, table_a: str, table_b: str) -> List[Tuple[str, str]]:
        """
        Find join keys between two tables by looking for shared hubs in Context Graph.
        
        If both tables have spokes to the same hub (e.g., both have employee_number 
        pointing to Personal hub), those columns are join keys.
        
        Returns:
            List of (table_a_column, table_b_column) tuples for join conditions.
            Ordered with identity columns (employee_number) first, then FK columns.
        """
        try:
            if not hasattr(self.handler, 'get_context_graph'):
                return []
            
            graph = self.handler.get_context_graph(project)
            relationships = graph.get('relationships', [])
            
            # Build lookup: table -> {semantic_type: column_name}
            table_a_lower = table_a.lower()
            table_b_lower = table_b.lower()
            
            table_a_spokes = {}  # semantic_type -> column_name
            table_b_spokes = {}
            
            for rel in relationships:
                spoke_table = rel.get('spoke_table', '').lower()
                spoke_column = rel.get('spoke_column', '')
                semantic_type = rel.get('semantic_type', '').lower()
                
                if spoke_table == table_a_lower:
                    table_a_spokes[semantic_type] = spoke_column
                elif spoke_table == table_b_lower:
                    table_b_spokes[semantic_type] = spoke_column
            
            # Also check if either table IS a hub (for identity hubs)
            for hub in graph.get('hubs', []):
                hub_table = hub.get('table', '').lower()
                hub_column = hub.get('column', '')
                semantic_type = hub.get('semantic_type', '').lower()
                
                if hub_table == table_a_lower:
                    table_a_spokes[semantic_type] = hub_column
                elif hub_table == table_b_lower:
                    table_b_spokes[semantic_type] = hub_column
            
            # Find shared semantic types
            shared_types = set(table_a_spokes.keys()) & set(table_b_spokes.keys())
            
            if not shared_types:
                logger.debug(f"[RESOLVER] No shared hubs between {table_a[:30]} and {table_b[:30]}")
                return []
            
            # Build join key pairs, prioritizing identity columns
            join_keys = []
            identity_patterns = ['employee_number', 'employee_id', 'emp_id', 'worker_id', 'person_id']
            
            # First pass: identity columns
            for sem_type in shared_types:
                col_a = table_a_spokes[sem_type]
                col_b = table_b_spokes[sem_type]
                
                # Check if this is an identity column
                is_identity = any(p in sem_type or p in col_a.lower() for p in identity_patterns)
                if is_identity:
                    join_keys.append((col_a, col_b))
            
            # Second pass: FK columns (company_code, etc.)
            for sem_type in shared_types:
                col_a = table_a_spokes[sem_type]
                col_b = table_b_spokes[sem_type]
                
                # Skip if already added as identity
                if (col_a, col_b) in join_keys:
                    continue
                    
                join_keys.append((col_a, col_b))
            
            if join_keys:
                logger.info(f"[RESOLVER] Join keys from Context Graph: {table_a[:25]} <-> {table_b[:25]}: {join_keys}")
            
            return join_keys
            
        except Exception as e:
            logger.warning(f"[RESOLVER] Failed to get join keys from Context Graph: {e}")
            return []
    
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
