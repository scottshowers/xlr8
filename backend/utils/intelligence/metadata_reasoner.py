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
1. Term comes in ("401k") - not found in term_index
2. MetadataReasoner queries:
   - _table_classifications: What domains/tables exist?
   - _column_profiles: What columns are searchable text?
   - _column_mappings: What semantic types exist?
3. Apply rules:
   - Alphanumeric like "401k" → search description columns
   - Looks like a name → search name columns
   - Looks like a code → search code columns
4. Return: table, column, operator, pattern

NO LLM. NO PRE-COMPUTATION. JUST REASONING OVER EXISTING METADATA.

Author: XLR8 Team
Date: 2026-01-11
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
    operator: str  # '=', 'ILIKE', 'IN'
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
    
    def __init__(self, conn: duckdb.DuckDBPyConnection, project: str):
        self.conn = conn
        self.project = project.lower() if project else 'default'
        
        # Cache metadata on init (small, fast queries)
        self._domain_tables: Dict[str, List[str]] = {}
        self._description_columns: Dict[str, List[str]] = {}  # table -> [desc columns]
        self._code_columns: Dict[str, List[str]] = {}  # table -> [code columns]
        self._name_columns: Dict[str, List[str]] = {}  # table -> [name columns]
        
        self._load_metadata()
    
    def _load_metadata(self):
        """Load and cache metadata for fast reasoning."""
        
        # 1. Load domain → tables mapping
        try:
            results = self.conn.execute("""
                SELECT domain, table_name 
                FROM _table_classifications
                WHERE project_name = ?
            """, [self.project]).fetchall()
            
            for domain, table_name in results:
                if domain:
                    domain_lower = domain.lower()
                    if domain_lower not in self._domain_tables:
                        self._domain_tables[domain_lower] = []
                    self._domain_tables[domain_lower].append(table_name)
            
            logger.info(f"[REASONER] Loaded {len(self._domain_tables)} domains: {list(self._domain_tables.keys())}")
        except Exception as e:
            logger.warning(f"[REASONER] Could not load domain tables: {e}")
        
        # 2. Load column classifications by name patterns
        try:
            results = self.conn.execute("""
                SELECT table_name, column_name, inferred_type
                FROM _column_profiles
                WHERE project = ?
            """, [self.project]).fetchall()
            
            for table_name, column_name, inferred_type in results:
                col_lower = column_name.lower()
                
                # Description columns
                if any(pat in col_lower for pat in ['desc', 'description', 'title', 'label', 'text']):
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
            
            logger.info(f"[REASONER] Found description columns in {len(self._description_columns)} tables")
            logger.info(f"[REASONER] Found code columns in {len(self._code_columns)} tables")
            logger.info(f"[REASONER] Found name columns in {len(self._name_columns)} tables")
        except Exception as e:
            logger.warning(f"[REASONER] Could not load column profiles: {e}")
    
    def resolve_unknown_term(self, term: str, context_domain: str = None) -> List[ReasonedMatch]:
        """
        Resolve an unknown term by reasoning over metadata.
        
        Args:
            term: The unknown term (e.g., "401k", "overtime", "manager")
            context_domain: Optional domain hint from other resolved terms
            
        Returns:
            List of ReasonedMatch objects (may be empty if no reasonable match)
        """
        term_lower = term.lower().strip()
        matches = []
        
        # Skip very short terms
        if len(term_lower) < 2:
            return matches
        
        # Classify the term
        term_type = self._classify_term(term_lower)
        logger.info(f"[REASONER] Term '{term_lower}' classified as: {term_type}")
        
        # Determine which domains to search
        target_domains = self._get_target_domains(term_lower, context_domain)
        logger.info(f"[REASONER] Target domains for '{term_lower}': {target_domains}")
        
        # Get tables for those domains
        target_tables = []
        for domain in target_domains:
            target_tables.extend(self._domain_tables.get(domain, []))
        
        # If no domain match, search all tables with relevant column types
        if not target_tables:
            if term_type == 'keyword':
                target_tables = list(self._description_columns.keys())
            elif term_type == 'code':
                target_tables = list(self._code_columns.keys())
            elif term_type == 'name':
                target_tables = list(self._name_columns.keys())
            else:
                # Default: search description columns
                target_tables = list(self._description_columns.keys())
        
        logger.info(f"[REASONER] Searching {len(target_tables)} tables: {target_tables[:5]}...")
        
        # Build matches based on term type
        for table_name in target_tables:
            if term_type in ('keyword', 'mixed'):
                # Search description columns with ILIKE
                for col in self._description_columns.get(table_name, []):
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
        
        logger.info(f"[REASONER] Returning {len(matches)} matches for '{term_lower}'")
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
