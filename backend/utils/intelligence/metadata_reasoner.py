"""
XLR8 Metadata Reasoner - Intelligent Term Resolution via Existing Metadata
===========================================================================

This is the FALLBACK path for terms not found in the Term Index.

Instead of:
- Pre-computing every possible keyword
- Asking an LLM to generate SQL

We:
- Query the metadata we ALREADY HAVE
- Apply deterministic rules to figure out where to look
- Return a filter specification for the SQLAssembler

FLOW:
1. Term comes in ("job_code") - not found in term_index
2. FIRST: Check if term is an actual COLUMN NAME (highest priority!)
3. MetadataReasoner queries:
   - _column_profiles: Is this term a column name?
   - _table_classifications: What domains/tables exist?
   - _column_mappings: What semantic types exist?
4. Apply rules:
   - Column name match → return as concept/GROUP BY target (highest confidence)
   - Alphanumeric like "401k" → search description columns
   - Looks like a name → search name columns
   - Looks like a code → search code columns
5. Return: table, column, operator, pattern

NO LLM. NO PRE-COMPUTATION. JUST REASONING OVER EXISTING METADATA.

Author: XLR8 Team
Date: 2026-01-14 (Updated with column name matching)
"""

import re
import json
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
import duckdb

logger = logging.getLogger(__name__)


@dataclass
class ReasonedMatch:
    """A match discovered by reasoning over metadata."""
    term: str
    table_name: str
    column_name: str
    operator: str  # '=', 'ILIKE', 'IN', 'GROUP BY'
    match_value: str
    domain: Optional[str] = None
    confidence: float = 0.7  # Lower than term_index matches
    reasoning: str = ''  # Why we chose this


class MetadataReasoner:
    """
    Resolves unknown terms by querying existing metadata.
    
    This is NOT pre-computation. This is query-time reasoning
    using the rich metadata we already have.
    
    Usage:
        reasoner = MetadataReasoner(conn, project)
        matches = reasoner.resolve_unknown_term("401k")
        # Returns: [ReasonedMatch(table='Deductions', column='description', 
        #                         operator='ILIKE', match_value='%401%')]
    """
    
    def __init__(self, conn: duckdb.DuckDBPyConnection, project: str, customer_id: str = None):
        self.conn = conn
        self.project = project.lower() if project else 'default'
        self.customer_id = customer_id  # UUID for precise matching
        
        # Cache metadata on init (small, fast queries)
        self._domain_tables: Dict[str, List[str]] = {}
        self._description_columns: Dict[str, List[str]] = {}  # table -> [desc columns]
        self._code_columns: Dict[str, List[str]] = {}  # table -> [code columns]
        self._name_columns: Dict[str, List[str]] = {}  # table -> [name columns]
        self._all_columns: Dict[str, List[str]] = {}  # table -> [all columns]
        
        self._load_metadata()
    
    def _load_metadata(self):
        """Load and cache metadata for fast reasoning."""
        
        # Check if customer_id column exists
        has_customer_id = False
        try:
            cols = [row[1] for row in self.conn.execute("PRAGMA table_info(_column_profiles)").fetchall()]
            has_customer_id = 'customer_id' in cols
        except Exception:
            pass
        
        # Build project filter - prefer customer_id (UUID) when available
        if has_customer_id and self.customer_id:
            project_filter = "customer_id = ?"
            project_param = self.customer_id
        elif has_customer_id and self.project:
            # Try to match by customer_id OR project name
            project_filter = "(customer_id = ? OR LOWER(project) = LOWER(?))"
            project_param = [self.project, self.project]
        else:
            project_filter = "LOWER(project) = ?"
            project_param = self.project
        
        # 1. Load domain → tables mapping (case-insensitive project match)
        try:
            results = self.conn.execute("""
                SELECT domain, table_name 
                FROM _table_classifications
                WHERE LOWER(project_name) = ?
            """, [self.project]).fetchall()
            
            for domain, table_name in results:
                if domain:
                    domain_lower = domain.lower()
                    if domain_lower not in self._domain_tables:
                        self._domain_tables[domain_lower] = []
                    self._domain_tables[domain_lower].append(table_name)
            
            logger.warning(f"[REASONER] Loaded {len(self._domain_tables)} domains: {list(self._domain_tables.keys())}")
        except Exception as e:
            logger.warning(f"[REASONER] Could not load domain tables: {e}")
        
        # 2. Load column classifications by name patterns
        try:
            # Use customer_id when available
            if isinstance(project_param, list):
                results = self.conn.execute(f"""
                    SELECT table_name, column_name, inferred_type
                    FROM _column_profiles
                    WHERE {project_filter}
                """, project_param).fetchall()
            else:
                results = self.conn.execute(f"""
                    SELECT table_name, column_name, inferred_type
                    FROM _column_profiles
                    WHERE {project_filter}
                """, [project_param]).fetchall()
            
            logger.warning(f"[REASONER] Found {len(results)} column profiles for project '{self.project}' (customer_id={self.customer_id})")
            
            for table_name, column_name, inferred_type in results:
                col_lower = column_name.lower()
                
                # Track ALL columns for column-name matching
                if table_name not in self._all_columns:
                    self._all_columns[table_name] = []
                self._all_columns[table_name].append(column_name)
                
                # Description columns (including *_long which often contains descriptive text)
                if any(pat in col_lower for pat in ['desc', 'description', 'title', 'label', 'text', 'long']):
                    if table_name not in self._description_columns:
                        self._description_columns[table_name] = []
                    self._description_columns[table_name].append(column_name)
                
                # Code columns
                elif any(pat in col_lower for pat in ['code', 'cd', 'type', 'category', 'status']):
                    if table_name not in self._code_columns:
                        self._code_columns[table_name] = []
                    self._code_columns[table_name].append(column_name)
                
                # Name columns
                elif any(pat in col_lower for pat in ['name', 'nm', 'first', 'last', 'full']):
                    if table_name not in self._name_columns:
                        self._name_columns[table_name] = []
                    self._name_columns[table_name].append(column_name)
            
            logger.warning(f"[REASONER] Found description columns in {len(self._description_columns)} tables")
            logger.warning(f"[REASONER] Found code columns in {len(self._code_columns)} tables")
            logger.warning(f"[REASONER] Found name columns in {len(self._name_columns)} tables")
            logger.warning(f"[REASONER] Indexed all columns from {len(self._all_columns)} tables")
        except Exception as e:
            logger.warning(f"[REASONER] Could not load column profiles: {e}")
    
    def _find_column_name_matches(self, term: str) -> List[ReasonedMatch]:
        """
        FIRST PASS: Check if the term matches an actual column name.
        
        This is critical for GROUP BY queries like "employees by job code" where
        "job_code" is the actual column name, not text to search for.
        
        Prioritizes:
        1. Exact column name match (highest confidence)
        2. Column name contains term (medium confidence)
        3. Reality/employee tables over config tables
        
        Args:
            term: The term to match (e.g., "job_code", "department")
            
        Returns:
            List of ReasonedMatch objects for column name matches
        """
        matches = []
        term_lower = term.lower().strip()
        
        # Normalize term variants (handle both underscore and space)
        term_variants = {
            term_lower,
            term_lower.replace('_', ''),  # jobcode
            term_lower.replace(' ', '_'),  # job_code
            term_lower.replace('_', ' '),  # job code
        }
        
        # Helper to determine table priority (reality tables > config tables)
        def get_table_priority(table_name: str) -> int:
            """Higher = better. Reality/employee tables preferred."""
            t = table_name.lower()
            
            # Config/validation tables - lowest priority
            if 'config' in t or 'validation' in t or 'lookup' in t or '_ref_' in t:
                return 1
            
            # Company tax tables - low priority for employee queries
            if 'companytax' in t or 'tax_jurisdiction' in t:
                return 2
            
            # Employee reality tables - highest priority
            if 'employee' in t or 'personal' in t or '_us_1_' in t:
                return 10
            
            # Company table (has job_code, department, etc.) - high priority
            if 'company' in t and 'tax' not in t:
                return 9
            
            # Other tables
            return 5
        
        # Search all tables for column name matches
        exact_matches = []
        partial_matches = []
        
        for table_name, columns in self._all_columns.items():
            for column_name in columns:
                col_lower = column_name.lower()
                
                # Check for exact match with any variant
                if col_lower in term_variants:
                    priority = get_table_priority(table_name)
                    exact_matches.append((table_name, column_name, priority))
                    logger.warning(f"[REASONER] COLUMN NAME EXACT MATCH: '{term}' → {table_name}.{column_name} (priority={priority})")
                
                # Check for partial match (term in column name or vice versa)
                elif term_lower in col_lower or col_lower in term_lower:
                    # Only if it's a meaningful match (not just 'a' in 'salary')
                    if len(term_lower) >= 3:
                        priority = get_table_priority(table_name)
                        partial_matches.append((table_name, column_name, priority))
                        logger.warning(f"[REASONER] COLUMN NAME PARTIAL MATCH: '{term}' → {table_name}.{column_name} (priority={priority})")
        
        # Sort by priority (highest first) and build matches
        exact_matches.sort(key=lambda x: -x[2])
        partial_matches.sort(key=lambda x: -x[2])
        
        # Add exact matches first (high confidence)
        for table_name, column_name, priority in exact_matches:
            matches.append(ReasonedMatch(
                term=term_lower,
                table_name=table_name,
                column_name=column_name,
                operator='GROUP BY',  # Column name matches are for GROUP BY/SELECT
                match_value='',  # No filter value - this is the column itself
                domain=self._get_table_domain(table_name),
                confidence=0.95 if priority >= 9 else 0.85,  # Higher confidence for reality tables
                reasoning=f"Column name exact match: {column_name} in {table_name}"
            ))
        
        # Add partial matches if no exact matches (lower confidence)
        if not exact_matches:
            for table_name, column_name, priority in partial_matches[:3]:  # Limit partial matches
                matches.append(ReasonedMatch(
                    term=term_lower,
                    table_name=table_name,
                    column_name=column_name,
                    operator='GROUP BY',
                    match_value='',
                    domain=self._get_table_domain(table_name),
                    confidence=0.75 if priority >= 9 else 0.65,
                    reasoning=f"Column name partial match: {column_name} in {table_name}"
                ))
        
        if matches:
            logger.warning(f"[REASONER] Found {len(matches)} column name matches for '{term}'")
        
        return matches
    
    def resolve_unknown_term(self, term: str, context_domain: str = None) -> List[ReasonedMatch]:
        """
        Resolve an unknown term by reasoning over metadata.
        
        RESOLUTION ORDER (most specific to least specific):
        1. COLUMN NAME MATCH - Is this term an actual column name? (e.g., "job_code")
        2. TEXT SEARCH - Search description/code/name columns for text content
        
        Args:
            term: The unknown term (e.g., "401k", "overtime", "job_code")
            context_domain: Optional domain hint from other resolved terms
            
        Returns:
            List of ReasonedMatch objects (may be empty if no reasonable match)
        """
        term_lower = term.lower().strip()
        matches = []
        
        # Skip very short terms
        if len(term_lower) < 2:
            return matches
        
        # Skip domain indicator words - these indicate WHAT to query, not filter values
        DOMAIN_INDICATOR_WORDS = {
            'employee', 'employees', 'worker', 'workers', 'staff', 'personnel',
            'person', 'people', 'individual', 'individuals',
            'show', 'list', 'find', 'get', 'display', 'count', 'total',
            'data', 'information', 'records', 'entries',
        }
        if term_lower in DOMAIN_INDICATOR_WORDS:
            logger.warning(f"[REASONER] Skipping domain indicator word: '{term_lower}'")
            return matches
        
        # ======================================================================
        # PASS 1: COLUMN NAME MATCHING (HIGHEST PRIORITY)
        # ======================================================================
        # Check if this term IS a column name before treating it as search text
        # This is critical for "employees by job code" type queries
        column_matches = self._find_column_name_matches(term_lower)
        if column_matches:
            logger.warning(f"[REASONER] Returning {len(column_matches)} COLUMN NAME matches for '{term_lower}'")
            return column_matches
        
        # ======================================================================
        # PASS 2: TEXT CONTENT SEARCH (FALLBACK)
        # ======================================================================
        # If not a column name, treat as search term for text columns
        
        # Classify the term
        term_type = self._classify_term(term_lower)
        logger.warning(f"[REASONER] Term '{term_lower}' classified as: {term_type}")
        
        # Determine which domains to search
        target_domains = self._get_target_domains(term_lower, context_domain)
        logger.warning(f"[REASONER] Target domains for '{term_lower}': {target_domains}")
        
        # Get tables for those domains
        target_tables = []
        for domain in target_domains:
            tables = self._domain_tables.get(domain, [])
            logger.warning(f"[REASONER] Domain '{domain}' has {len(tables)} tables")
            target_tables.extend(tables)
        
        # If no domain match, search all tables with relevant column types
        if not target_tables:
            logger.warning(f"[REASONER] No domain tables found, falling back to column-type search")
            if term_type == 'keyword':
                target_tables = list(self._description_columns.keys())
            elif term_type == 'code':
                target_tables = list(self._code_columns.keys())
            elif term_type == 'name':
                target_tables = list(self._name_columns.keys())
            else:
                # Default: search description columns
                target_tables = list(self._description_columns.keys())
        
        logger.warning(f"[REASONER] Searching {len(target_tables)} tables: {target_tables[:5]}...")
        
        # Build matches based on term type
        for table_name in target_tables:
            if term_type in ('keyword', 'mixed'):
                # Search description columns with ILIKE
                desc_cols = self._description_columns.get(table_name, [])
                if desc_cols:
                    logger.warning(f"[REASONER] Table '{table_name}' has desc columns: {desc_cols}")
                for col in desc_cols:
                    matches.append(ReasonedMatch(
                        term=term_lower,
                        table_name=table_name,
                        column_name=col,
                        operator='ILIKE',
                        match_value=f'%{term_lower}%',
                        domain=self._get_table_domain(table_name),
                        confidence=0.7,
                        reasoning=f"Keyword '{term_lower}' searched in description column"
                    ))
            
            if term_type in ('code', 'mixed'):
                # Search code columns with ILIKE (codes can be partial)
                for col in self._code_columns.get(table_name, []):
                    matches.append(ReasonedMatch(
                        term=term_lower,
                        table_name=table_name,
                        column_name=col,
                        operator='ILIKE',
                        match_value=f'%{term_lower}%',
                        domain=self._get_table_domain(table_name),
                        confidence=0.6,
                        reasoning=f"Code-like '{term_lower}' searched in code column"
                    ))
            
            if term_type == 'name':
                # Search name columns with ILIKE
                for col in self._name_columns.get(table_name, []):
                    matches.append(ReasonedMatch(
                        term=term_lower,
                        table_name=table_name,
                        column_name=col,
                        operator='ILIKE',
                        match_value=f'%{term_lower}%',
                        domain=self._get_table_domain(table_name),
                        confidence=0.6,
                        reasoning=f"Name '{term_lower}' searched in name column"
                    ))
        
        # Sort by confidence and limit
        matches.sort(key=lambda m: m.confidence, reverse=True)
        
        # Limit to top matches per term to avoid explosion
        matches = matches[:5]
        
        logger.warning(f"[REASONER] Returning {len(matches)} matches for '{term_lower}'")
        return matches
    
    def _classify_term(self, term: str) -> str:
        """
        Classify what type of term this is.
        
        Returns: 'keyword', 'code', 'name', 'mixed'
        """
        # Check if it looks like a code (alphanumeric, short, has numbers)
        has_numbers = bool(re.search(r'\d', term))
        has_letters = bool(re.search(r'[a-zA-Z]', term))
        is_short = len(term) <= 6
        is_upper = term.isupper()
        
        # 401k, HSA, FSA, etc. - alphanumeric codes
        if has_numbers and has_letters and is_short:
            return 'mixed'  # Search both code and description
        
        # All caps short string - likely a code
        if is_upper and is_short and not has_numbers:
            return 'code'
        
        # Looks like a name (capitalized, no numbers)
        if term[0].isupper() and not has_numbers and len(term) > 3:
            return 'name'
        
        # Common benefit/deduction keywords
        benefit_keywords = {
            'medical', 'dental', 'vision', 'health', 'insurance',
            'retirement', 'pension', 'disability', 'life',
            'overtime', 'bonus', 'commission', 'salary', 'hourly',
            'federal', 'state', 'local', 'fica', 'medicare', 'social',
            'manager', 'supervisor', 'director', 'analyst', 'engineer'
        }
        if term in benefit_keywords:
            return 'keyword'
        
        # Default to keyword (search descriptions)
        return 'keyword'
    
    def _get_target_domains(self, term: str, context_domain: str = None) -> List[str]:
        """
        Determine which domains to search based on the term.
        """
        domains = []
        
        # If context provided, use it
        if context_domain:
            domains.append(context_domain.lower())
        
        # Domain hints from term content
        term_domain_hints = {
            # Benefits/Deductions
            '401k': ['deductions', 'benefits'],
            'hsa': ['deductions', 'benefits'],
            'fsa': ['deductions', 'benefits'],
            'medical': ['deductions', 'benefits'],
            'dental': ['deductions', 'benefits'],
            'vision': ['deductions', 'benefits'],
            'insurance': ['deductions', 'benefits'],
            'retirement': ['deductions', 'benefits'],
            'pension': ['deductions', 'benefits'],
            
            # Earnings
            'overtime': ['earnings', 'payroll'],
            'bonus': ['earnings', 'payroll'],
            'commission': ['earnings', 'payroll'],
            'salary': ['earnings', 'payroll', 'demographics'],
            'hourly': ['earnings', 'payroll'],
            'regular': ['earnings', 'payroll'],
            
            # Taxes
            'federal': ['taxes', 'tax'],
            'state': ['taxes', 'tax'],
            'local': ['taxes', 'tax'],
            'fica': ['taxes', 'tax'],
            'medicare': ['taxes', 'tax'],
            'withholding': ['taxes', 'tax'],
            
            # Jobs
            'manager': ['demographics', 'jobs', 'hr'],
            'supervisor': ['demographics', 'jobs', 'hr'],
            'director': ['demographics', 'jobs', 'hr'],
            'analyst': ['demographics', 'jobs', 'hr'],
            'engineer': ['demographics', 'jobs', 'hr'],
        }
        
        if term in term_domain_hints:
            domains.extend(term_domain_hints[term])
        
        # Dedupe while preserving order
        seen = set()
        unique_domains = []
        for d in domains:
            if d not in seen:
                seen.add(d)
                unique_domains.append(d)
        
        return unique_domains if unique_domains else list(self._domain_tables.keys())
    
    def _get_table_domain(self, table_name: str) -> Optional[str]:
        """Get the domain for a table."""
        for domain, tables in self._domain_tables.items():
            if table_name in tables:
                return domain
        return None
    
    def resolve_terms(self, terms: List[str], known_matches: List[Any] = None) -> List[ReasonedMatch]:
        """
        Resolve multiple unknown terms.
        
        Args:
            terms: List of terms to resolve
            known_matches: Optional list of already-resolved TermMatch objects
                          Used to infer context domain
                          
        Returns:
            List of ReasonedMatch objects for all terms
        """
        all_matches = []
        
        # Infer context domain from known matches
        context_domain = None
        if known_matches:
            domains = [m.domain for m in known_matches if hasattr(m, 'domain') and m.domain]
            if domains:
                context_domain = domains[0]
        
        for term in terms:
            term_matches = self.resolve_unknown_term(term, context_domain)
            all_matches.extend(term_matches)
        
        return all_matches


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

def reason_about_term(
    conn: duckdb.DuckDBPyConnection,
    project: str,
    term: str,
    context_domain: str = None
) -> List[Dict]:
    """
    Convenience function to resolve an unknown term.
    
    Returns list of dicts for easy JSON serialization.
    """
    reasoner = MetadataReasoner(conn, project)
    matches = reasoner.resolve_unknown_term(term, context_domain)
    
    return [
        {
            'term': m.term,
            'table_name': m.table_name,
            'column_name': m.column_name,
            'operator': m.operator,
            'match_value': m.match_value,
            'domain': m.domain,
            'confidence': m.confidence,
            'reasoning': m.reasoning
        }
        for m in matches
    ]
