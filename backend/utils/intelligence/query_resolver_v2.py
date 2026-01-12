"""
XLR8 Query Resolver - Thin Wrapper Around TermIndex + SQLAssembler
===================================================================

REFACTORED: This is now a thin orchestration layer.

OLD: 3,233 lines with parallel SQL building logic
NEW: ~500 lines - just parses intent and calls TermIndex + SQLAssembler

The heavy lifting is done by:
- TermIndex: term → table/column/value lookup
- SQLAssembler: term matches → deterministic SQL

Query Resolver just:
1. Parses user intent
2. Extracts filter terms from question
3. Calls TermIndex.resolve_terms()
4. Calls SQLAssembler.assemble()
5. Returns results

EVOLUTION 3: Now detects numeric expressions ("above 50000", "between 20 and 40")

Author: XLR8 Team
Version: 2.1.0 (Added numeric parsing)
Date: 2026-01-11
"""

import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

# Import value_parser for numeric expression detection
try:
    from .value_parser import parse_numeric_expression, ParsedValue, ComparisonOp
    HAS_VALUE_PARSER = True
except ImportError:
    HAS_VALUE_PARSER = False
    logger.warning("[RESOLVER] value_parser not available - numeric expressions won't be detected")


# =============================================================================
# INTENT TYPES - What is the user trying to do?
# =============================================================================

class QueryIntent(Enum):
    """What the user is trying to accomplish."""
    COUNT = "count"              # How many X? Headcount?
    LIST = "list"                # Show me all X, List X
    LOOKUP = "lookup"            # What is X? Find X
    SUM = "sum"                  # Total X, Sum of X
    AVERAGE = "average"          # Average X
    COMPARE = "compare"          # X vs Y, Compare X to Y, X by Y
    FILTER = "filter"            # X where Y
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
# INTENT DETECTION - Simple keyword mapping
# =============================================================================

# Keywords that indicate COUNT intent
COUNT_KEYWORDS = [
    'how many', 'count', 'headcount', 'head count', 'total number',
    'number of', 'quantity'
]

# Keywords that indicate LIST intent  
LIST_KEYWORDS = [
    'list', 'show', 'display', 'what are', 'which', 'all the',
    'give me', 'show me', 'find', 'get'
]

# Keywords that indicate SUM intent
SUM_KEYWORDS = [
    'total', 'sum', 'aggregate', 'combined', 'overall'
]

# Keywords that indicate COMPARE/GROUP BY intent
COMPARE_KEYWORDS = [
    'by state', 'by location', 'by department', 'by company',
    'per state', 'per location', 'per department',
    'breakdown', 'group by', 'for each'
]

# Domain keyword mapping
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


# =============================================================================
# GEOGRAPHIC NORMALIZATION
# =============================================================================

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
    'wisconsin': 'WI', 'wyoming': 'WY', 'district of columbia': 'DC',
}

CA_PROVINCE_CODES = {
    'alberta': 'AB', 'british columbia': 'BC', 'manitoba': 'MB',
    'new brunswick': 'NB', 'newfoundland': 'NL', 'nova scotia': 'NS',
    'ontario': 'ON', 'prince edward island': 'PE', 'quebec': 'QC',
    'saskatchewan': 'SK', 'yukon': 'YT',
}

# Reverse lookup
STATE_CODE_TO_NAME = {v: k.title() for k, v in US_STATE_CODES.items() if len(k) > 2}


def normalize_geographic_term(term: str) -> Optional[Dict]:
    """
    Normalize a geographic term to its standard code.
    
    Examples:
        "Texas" → {'code': 'TX', 'type': 'state', 'name': 'Texas'}
        "Ontario" → {'code': 'ON', 'type': 'province', 'name': 'Ontario'}
    """
    term_lower = term.lower().strip()
    
    if term_lower in US_STATE_CODES:
        code = US_STATE_CODES[term_lower]
        return {'code': code, 'type': 'state', 'name': STATE_CODE_TO_NAME.get(code, term.title())}
    
    if term_lower in CA_PROVINCE_CODES:
        code = CA_PROVINCE_CODES[term_lower]
        return {'code': code, 'type': 'province', 'name': term.title()}
    
    # Check if already a valid code
    if len(term) == 2 and term.upper() in STATE_CODE_TO_NAME:
        return {'code': term.upper(), 'type': 'state', 'name': STATE_CODE_TO_NAME[term.upper()]}
    
    return None


# =============================================================================
# PARSED INTENT RESULT
# =============================================================================

@dataclass
class ParsedIntent:
    """Result of parsing user's question."""
    intent: QueryIntent
    domain: EntityDomain
    raw_question: str
    
    # Extracted specifics
    filter_terms: List[str] = field(default_factory=list)  # Terms to resolve
    group_by_hint: Optional[str] = None  # For COMPARE queries
    
    # Date filtering (future: Duckling)
    date_filter: Optional[Dict] = None
    
    # Confidence
    intent_confidence: float = 0.0
    domain_confidence: float = 0.0
    
    def __str__(self):
        return f"Intent({self.intent.value}, {self.domain.value}, terms={self.filter_terms})"


# =============================================================================
# RESOLVED QUERY RESULT
# =============================================================================

@dataclass
class ResolvedQuery:
    """Result of query resolution."""
    success: bool = False
    sql: str = ""
    explanation: str = ""
    
    # Metadata
    table_name: str = ""
    tables_used: List[str] = field(default_factory=list)
    filter_column: str = ""
    filter_value: str = ""
    filters_applied: List[Dict] = field(default_factory=list)
    
    # Results (if executed)
    row_count: int = 0
    data: List[Dict] = field(default_factory=list)
    
    # Debug
    resolution_path: List[str] = field(default_factory=list)
    term_matches: List[Any] = field(default_factory=list)


# =============================================================================
# INTENT PARSING
# =============================================================================

def parse_intent(question: str) -> ParsedIntent:
    """
    Parse the user's question to determine intent, domain, and filter terms.
    
    This is KEYWORD MATCHING, not fuzzy scoring.
    """
    q_lower = question.lower().strip()
    
    # Detect intent
    intent = QueryIntent.UNKNOWN
    intent_confidence = 0.0
    group_by_hint = None
    
    # Check for COMPARE first (has group by hints)
    for kw in COMPARE_KEYWORDS:
        if kw in q_lower:
            intent = QueryIntent.COMPARE
            intent_confidence = 1.0
            # Extract the grouping dimension
            group_by_hint = kw.replace('by ', '').replace('per ', '').replace('for each ', '')
            break
    
    if intent == QueryIntent.UNKNOWN:
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
                domain_matches.append((dom, len(kw)))
    
    if domain_matches:
        domain_matches.sort(key=lambda x: -x[1])  # Longest match first
        domain = domain_matches[0][0]
        domain_confidence = 1.0
    
    # Special case: "headcount" implies EMPLOYEES + COUNT
    if 'headcount' in q_lower or 'head count' in q_lower:
        intent = QueryIntent.COUNT
        domain = EntityDomain.EMPLOYEES
        intent_confidence = 1.0
        domain_confidence = 1.0
    
    # Default: EMPLOYEES domain with unknown intent → LIST
    if domain == EntityDomain.EMPLOYEES and intent == QueryIntent.UNKNOWN:
        intent = QueryIntent.LIST
        intent_confidence = 0.8
    
    # Extract filter terms
    filter_terms = extract_filter_terms(question, domain)
    
    return ParsedIntent(
        intent=intent,
        domain=domain,
        raw_question=question,
        filter_terms=filter_terms,
        group_by_hint=group_by_hint,
        intent_confidence=intent_confidence,
        domain_confidence=domain_confidence
    )


def extract_filter_terms(question: str, domain: EntityDomain) -> List[str]:
    """
    Extract potential filter terms from a question.
    
    Examples:
        "employees in Texas with 401k" → ['texas', '401k']
        "active employees" → ['active']
    """
    terms = []
    q_lower = question.lower()
    
    # Pattern 1: "in/at/for/from <something>"
    in_matches = re.findall(r'\b(?:in|at|for|from)\s+([A-Za-z][A-Za-z0-9\s\-]*?)(?:\s+(?:with|who|that|and)|[,\.\?]|$)', q_lower)
    for match in in_matches:
        cleaned = match.strip()
        if len(cleaned) >= 2 and cleaned not in ('the', 'all', 'any'):
            terms.append(cleaned)
    
    # Pattern 2: "who are <status>"
    status_patterns = re.findall(r'\bwho\s+(?:are|is)\s+(\w+)', q_lower)
    terms.extend([p.strip() for p in status_patterns])
    
    # Pattern 3: Status words at start
    status_words = ['active', 'terminated', 'inactive', 'on leave', 'pending']
    for word in status_words:
        if q_lower.startswith(word) or f' {word} ' in q_lower:
            terms.append(word)
    
    # Pattern 4: "with <something>" - especially for deductions/benefits
    with_matches = re.findall(r'\bwith\s+([A-Za-z0-9]+)', q_lower)
    for match in with_matches:
        if match not in ('the', 'a', 'an', 'all', 'any'):
            terms.append(match)
    
    # Pattern 5: ALL CAPS codes (company codes, pay groups, etc.)
    caps_codes = re.findall(r'\b([A-Z][A-Z0-9]{1,5})\b', question)
    for code in caps_codes:
        if code.lower() not in terms and code.lower() not in ('how', 'the', 'and', 'for', 'are', 'all'):
            terms.append(code.lower())
    
    # Deduplicate while preserving order
    seen = set()
    unique_terms = []
    for t in terms:
        t_lower = t.lower()
        if t_lower not in seen:
            seen.add(t_lower)
            unique_terms.append(t_lower)
    
    return unique_terms


# =============================================================================
# NUMERIC EXPRESSION DETECTION (Evolution 3)
# =============================================================================

# Column indicator words → likely column name patterns
NUMERIC_COLUMN_INDICATORS = {
    # Salary/Pay related
    'salary': ['salary', 'pay', 'annual_rate', 'rate', 'wage'],
    'earning': ['amount', 'earnings', 'gross', 'net'],
    'rate': ['rate', 'hourly_rate', 'pay_rate'],
    
    # Hours related
    'hour': ['hours', 'hrs', 'time', 'regular_hours', 'overtime'],
    'pto': ['pto', 'vacation', 'sick', 'balance'],
    
    # General amounts
    'amount': ['amount', 'total', 'balance', 'value'],
    'percent': ['percent', 'pct', 'rate', 'percentage'],
    
    # Age/service
    'age': ['age'],
    'tenure': ['tenure', 'service_years', 'years_of_service'],
}


def extract_numeric_expressions(question: str, conn=None, project: str = None) -> List[Dict]:
    """
    Extract numeric expressions from a question.
    
    Returns list of dicts with:
    - operator: '>', '<', '>=', '<=', 'BETWEEN', '='
    - value: the numeric value (or "start|end" for BETWEEN)
    - column_hint: likely column name pattern
    - original_text: the matched text
    
    Examples:
        "employees earning above 50000" → [{'operator': '>', 'value': 50000, 'column_hint': 'amount'}]
        "workers with at least 40 hours" → [{'operator': '>=', 'value': 40, 'column_hint': 'hours'}]
    """
    if not HAS_VALUE_PARSER:
        return []
    
    results = []
    q_lower = question.lower()
    
    # Try to parse numeric expression from the full question
    parsed = parse_numeric_expression(question)
    
    if parsed:
        # Determine column hint from context words
        column_hint = None
        
        for indicator, patterns in NUMERIC_COLUMN_INDICATORS.items():
            if indicator in q_lower:
                column_hint = patterns[0]  # Use first pattern as default
                break
        
        # If no indicator found, try to find any numeric column patterns
        if not column_hint:
            # Default hints based on value magnitude
            if parsed.value >= 10000:
                column_hint = 'salary'  # Large numbers likely salary
            elif parsed.value <= 100 and parsed.value > 0:
                column_hint = 'hours'  # Small numbers likely hours/rates
            else:
                column_hint = 'amount'  # Generic
        
        # Map ComparisonOp to SQL operator string
        op_map = {
            ComparisonOp.GT: '>',
            ComparisonOp.GTE: '>=',
            ComparisonOp.LT: '<',
            ComparisonOp.LTE: '<=',
            ComparisonOp.EQ: '=',
            ComparisonOp.NE: '!=',
            ComparisonOp.BETWEEN: 'BETWEEN',
        }
        
        # Build result
        result = {
            'operator': op_map.get(parsed.operator, '='),
            'value': parsed.value if parsed.operator != ComparisonOp.BETWEEN else f"{parsed.value}|{parsed.value_end}",
            'column_hint': column_hint,
            'original_text': parsed.original_text,
            'confidence': parsed.confidence,
        }
        
        results.append(result)
        logger.warning(f"[RESOLVER] Detected numeric expression: {result}")
    
    return results


def find_numeric_column(conn, project: str, column_hint: str) -> Optional[Tuple[str, str]]:
    """
    Find a numeric column matching the hint in the project's tables.
    
    Returns:
        (table_name, column_name) or None if not found
    """
    if not conn or not project:
        return None
    
    try:
        # Search for columns matching the hint pattern
        results = conn.execute("""
            SELECT table_name, column_name, data_type
            FROM _column_profiles
            WHERE LOWER(project) = LOWER(?)
              AND (
                  LOWER(column_name) LIKE ?
                  OR LOWER(column_name) LIKE ?
              )
              AND (
                  data_type IN ('INTEGER', 'BIGINT', 'DOUBLE', 'FLOAT', 'DECIMAL', 'NUMERIC')
                  OR data_type LIKE '%INT%'
                  OR data_type LIKE '%FLOAT%'
                  OR data_type LIKE '%DOUBLE%'
                  OR data_type LIKE '%DECIMAL%'
                  OR data_type LIKE '%NUM%'
              )
            ORDER BY 
                CASE WHEN LOWER(column_name) = ? THEN 1 ELSE 2 END,
                LENGTH(column_name)
            LIMIT 1
        """, [project, f'%{column_hint}%', f'{column_hint}%', column_hint]).fetchone()
        
        if results:
            logger.warning(f"[RESOLVER] Found numeric column: {results[0]}.{results[1]} ({results[2]})")
            return (results[0], results[1])
        
        # Fallback: Try related patterns
        for indicator, patterns in NUMERIC_COLUMN_INDICATORS.items():
            if column_hint in patterns:
                for pattern in patterns:
                    results = conn.execute("""
                        SELECT table_name, column_name
                        FROM _column_profiles
                        WHERE LOWER(project) = LOWER(?)
                          AND LOWER(column_name) LIKE ?
                          AND (
                              data_type IN ('INTEGER', 'BIGINT', 'DOUBLE', 'FLOAT', 'DECIMAL', 'NUMERIC')
                              OR data_type LIKE '%INT%'
                              OR data_type LIKE '%NUM%'
                          )
                        LIMIT 1
                    """, [project, f'%{pattern}%']).fetchone()
                    
                    if results:
                        logger.warning(f"[RESOLVER] Fallback found column: {results[0]}.{results[1]}")
                        return (results[0], results[1])
        
    except Exception as e:
        logger.warning(f"[RESOLVER] Error finding numeric column: {e}")
    
    return None


# =============================================================================
# QUERY RESOLVER CLASS
# =============================================================================

class QueryResolver:
    """
    Thin wrapper around TermIndex + SQLAssembler.
    
    Usage:
        resolver = QueryResolver(handler)
        result = resolver.resolve("employees in Texas with 401k", "tea1000")
        if result.success:
            execute(result.sql)
    """
    
    def __init__(self, handler):
        """
        Initialize resolver with database handler.
        
        Args:
            handler: StructuredDataHandler with DuckDB connection
        """
        self.handler = handler
        self.conn = handler.conn if handler else None
        self._term_index = None
        self._sql_assembler = None
    
    def _get_term_index(self, project: str):
        """Get or create TermIndex for project."""
        if self._term_index is None:
            try:
                from .term_index import TermIndex
                self._term_index = TermIndex(self.conn, project)
            except ImportError:
                logger.warning("[RESOLVER] TermIndex not available")
                return None
            except Exception as e:
                logger.warning(f"[RESOLVER] Could not create TermIndex: {e}")
                return None
        return self._term_index
    
    def _get_sql_assembler(self, project: str):
        """Get or create SQLAssembler for project."""
        if self._sql_assembler is None:
            try:
                from .sql_assembler import SQLAssembler
                self._sql_assembler = SQLAssembler(self.conn, project)
            except ImportError:
                logger.warning("[RESOLVER] SQLAssembler not available")
                return None
            except Exception as e:
                logger.warning(f"[RESOLVER] Could not create SQLAssembler: {e}")
                return None
        return self._sql_assembler
    
    def resolve(self, question: str, project: str) -> ResolvedQuery:
        """
        Resolve a question to a SQL query.
        
        Pipeline:
        1. Parse intent from question
        2. Extract filter terms
        3. Call TermIndex.resolve_terms()
        4. Detect numeric expressions (Evolution 3)
        5. Call SQLAssembler.assemble()
        6. Return SQL
        
        Args:
            question: User's question
            project: Project name
            
        Returns:
            ResolvedQuery with SQL and metadata
        """
        result = ResolvedQuery(success=False)
        result.resolution_path.append(f"Question: {question}")
        
        # STEP 1: Parse intent
        parsed = parse_intent(question)
        result.resolution_path.append(f"Parsed: {parsed}")
        logger.warning(f"[RESOLVER] Parsed intent: {parsed}")
        
        if parsed.intent == QueryIntent.UNKNOWN and parsed.domain == EntityDomain.UNKNOWN:
            result.explanation = "Could not understand the question. Try asking about employees, earnings, deductions, or other HCM data."
            return result
        
        # STEP 2: Get TermIndex
        term_index = self._get_term_index(project)
        if not term_index:
            result.explanation = "Term index not available"
            return result
        
        # STEP 3: Resolve filter terms - USE ENHANCED METHOD FOR NUMERIC SUPPORT
        if parsed.filter_terms:
            # Try enhanced resolution first (handles numeric expressions)
            if hasattr(term_index, 'resolve_terms_enhanced'):
                term_matches = term_index.resolve_terms_enhanced(parsed.filter_terms, detect_numeric=True)
            else:
                # Fallback to basic resolution
                term_matches = term_index.resolve_terms(parsed.filter_terms)
            
            result.term_matches = term_matches
            result.resolution_path.append(f"Resolved {len(term_matches)} term matches")
            logger.warning(f"[RESOLVER] Term matches: {[(m.term, m.table_name, m.column_name, m.operator) for m in term_matches]}")
        else:
            term_matches = []
            result.resolution_path.append("No filter terms extracted")
        
        # STEP 3.5 (Evolution 3): Detect numeric expressions
        numeric_expressions = extract_numeric_expressions(question, self.conn, project)
        
        if numeric_expressions:
            from .term_index import TermMatch as IndexTermMatch
            
            for numeric_expr in numeric_expressions:
                # Find a matching column for this numeric expression
                column_info = find_numeric_column(self.conn, project, numeric_expr['column_hint'])
                
                if column_info:
                    table_name, column_name = column_info
                    
                    # Create a TermMatch for this numeric filter
                    numeric_match = IndexTermMatch(
                        term=numeric_expr['original_text'],
                        table_name=table_name,
                        column_name=column_name,
                        operator=numeric_expr['operator'],
                        match_value=str(numeric_expr['value']),
                        domain=parsed.domain.value if parsed.domain != EntityDomain.UNKNOWN else None,
                        entity=None,
                        confidence=numeric_expr.get('confidence', 0.85),
                        term_type='numeric'
                    )
                    term_matches.append(numeric_match)
                    result.resolution_path.append(f"Added numeric filter: {column_name} {numeric_expr['operator']} {numeric_expr['value']}")
                    logger.warning(f"[RESOLVER] Added numeric match: {table_name}.{column_name} {numeric_expr['operator']} {numeric_expr['value']}")
                else:
                    result.resolution_path.append(f"Could not find column for numeric expression: {numeric_expr}")
                    logger.warning(f"[RESOLVER] No column found for numeric hint: {numeric_expr['column_hint']}")
        
        # STEP 4: Get SQLAssembler
        sql_assembler = self._get_sql_assembler(project)
        if not sql_assembler:
            result.explanation = "SQL assembler not available"
            return result
        
        # STEP 5: Map our intent to SQLAssembler intent
        from .sql_assembler import QueryIntent as AssemblerIntent
        intent_map = {
            QueryIntent.COUNT: AssemblerIntent.COUNT,
            QueryIntent.LIST: AssemblerIntent.LIST,
            QueryIntent.SUM: AssemblerIntent.SUM,
            QueryIntent.COMPARE: AssemblerIntent.COMPARE,
            QueryIntent.LOOKUP: AssemblerIntent.LOOKUP,
            QueryIntent.FILTER: AssemblerIntent.FILTER,
        }
        assembler_intent = intent_map.get(parsed.intent, AssemblerIntent.LIST)
        
        # STEP 6: Assemble SQL
        assembled = sql_assembler.assemble(
            intent=assembler_intent,
            term_matches=term_matches,
            domain=parsed.domain.value if parsed.domain != EntityDomain.UNKNOWN else None,
            group_by_column=parsed.group_by_hint
        )
        
        result.resolution_path.append(f"Assembled: success={assembled.success}, tables={assembled.tables}")
        
        if assembled.success:
            result.success = True
            result.sql = assembled.sql
            result.table_name = assembled.primary_table
            result.tables_used = assembled.tables
            result.filters_applied = assembled.filters
            result.explanation = f"Query on {assembled.primary_table} with {len(assembled.filters)} filters"
            logger.warning(f"[RESOLVER] Generated SQL: {assembled.sql[:200]}...")
        else:
            result.explanation = assembled.error or "Could not generate SQL for this query"
            result.resolution_path.append(f"Assembly failed: {assembled.error}")
        
        return result


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

def resolve_query(question: str, project: str, handler) -> ResolvedQuery:
    """
    Convenience function to resolve a query.
    
    Args:
        question: User's question
        project: Project name
        handler: StructuredDataHandler
        
    Returns:
        ResolvedQuery with SQL and metadata
    """
    resolver = QueryResolver(handler)
    return resolver.resolve(question, project)
