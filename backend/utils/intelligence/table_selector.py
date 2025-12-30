"""
XLR8 Intelligence Engine - Table Selector
==========================================

Handles table scoring and selection for SQL generation.
Given a question and available tables, selects the most relevant ones.

Key features:
- Direct name matching (highest priority)
- Column value matching (finds tables with matching data)
- Domain-specific boosts (tax, earnings, deductions, etc.)
- Lookup/checklist deprioritization

Deploy to: backend/utils/intelligence/table_selector.py
"""

import re
import json
import logging
from typing import Dict, List, Optional, Set, Any

from .types import LOOKUP_INDICATORS

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

# Words to skip when matching question to table names
SKIP_WORDS = {
    'the', 'and', 'for', 'are', 'have', 'been', 'what', 'which', 'show', 
    'list', 'all', 'get', 'setup', 'set', 'how', 'many', 'config', 'table',
    'tell', 'give', 'find', 'display', 'view', 'see', 'configured', 'exist',
    'exists', 'there', 'any', 'our', 'the', 'this', 'that', 'with', 'has',
    'currently', 'please', 'can', 'you', 'me', 'about'
}

# Table name patterns → question keywords that should boost them
TABLE_KEYWORDS = {
    'personal': ['employee', 'employees', 'person', 'people', 'who', 'name', 'ssn', 
                 'birth', 'hire', 'termination', 'termed', 'terminated', 'active', 
                 'location', 'state', 'city', 'address'],
    'company': ['company', 'organization', 'org', 'entity', 'legal'],
    'job': ['job', 'position', 'title', 'department', 'dept'],
    'earnings': ['earn', 'earning', 'pay code', 'salary', 'wage', 'compensation', 
                 'earning code', 'earnings setup', 'earnings configured', 'earnigs', 'earings'],
    'deductions': ['deduction', 'benefit', '401k', 'insurance', 'health', 
                   'benefit plan', 'deduction code', 'deduction setup'],
    'tax': ['tax', 'sui', 'suta', 'futa', 'fein', 'ein', 'withhold', 'federal', 
            'state tax', 'fica', 'w2', 'w-2', '941', '940'],
    'workers_comp': ['workers comp', 'work comp', 'wc', 'workers compensation', 
                     'wcb', 'class code', 'experience mod'],
    'general_ledger': ['gl', 'general ledger', 'ledger', 'account mapping', 
                       'gl mapping', 'chart of accounts', 'gl rules'],
    'gl_': ['gl', 'general ledger', 'account', 'ledger mapping'],
    'time': ['time', 'hours', 'attendance', 'schedule'],
    'address': ['address', 'zip', 'postal'],
    'rate': ['rate', 'rates', 'percentage', 'percent'],
    'config': ['config', 'configuration', 'setup', 'setting', 'correct', 'valid', 'validation'],
    'master': ['master', 'setup', 'configuration'],
    'jurisdiction': ['jurisdiction', 'tax jurisdiction', 'state setup', 'registration'],
}

# Columns that indicate location data
LOCATION_COLUMNS = ['stateprovince', 'state', 'city', 'location', 'region', 
                    'site', 'work_location', 'home_state']

# Tables to heavily deprioritize (guides, not config data)
CHECKLIST_INDICATORS = ['checklist', 'step_', '_step', 'document', 
                        'before_final', 'year_end', 'yearend']


# =============================================================================
# TABLE SELECTOR CLASS
# =============================================================================

class TableSelector:
    """
    Selects relevant tables for a given question.
    
    Uses a scoring system that considers:
    - Direct name matches (e.g., "earnings" in question matches "earnings" table)
    - Column value matches (e.g., "SUI" matches value in tax_type column)
    - Domain-specific boosts (tax questions boost tax tables)
    - Penalties for lookup/checklist tables
    """
    
    def __init__(self, structured_handler=None, filter_candidates: Dict = None):
        """
        Initialize the table selector.
        
        Args:
            structured_handler: DuckDB handler for value lookups
            filter_candidates: Dict of filter category → candidate columns
        """
        self.structured_handler = structured_handler
        self.filter_candidates = filter_candidates or {}
    
    def select(self, tables: List[Dict], question: str, max_tables: int = 5) -> List[Dict]:
        """
        Select the most relevant tables for a question.
        
        Args:
            tables: List of table metadata dicts with table_name, columns, row_count
            question: The user's question
            max_tables: Maximum number of tables to return
            
        Returns:
            List of selected tables, sorted by relevance
        """
        if not tables:
            return []
        
        q_lower = question.lower()
        words = re.findall(r'\b[a-z]+\b', q_lower)
        
        # Identify tables that contain filter_candidate columns
        filter_candidate_tables = self._get_filter_candidate_tables()
        
        # Score each table
        scored_tables = []
        for table in tables:
            score = self._score_table(table, q_lower, words, filter_candidate_tables)
            scored_tables.append((score, table))
        
        # Sort by score descending
        scored_tables.sort(key=lambda x: -x[0])
        
        # Log top candidates
        for score, t in scored_tables[:5]:
            logger.warning(f"[TABLE-SEL] Candidate: {t.get('table_name', '')[-45:]} score={score}")
        
        # Take top N tables with positive scores
        relevant = [t for score, t in scored_tables[:max_tables] if score > 0]
        
        # If nothing found, return first table as fallback
        if not relevant and tables:
            relevant = [tables[0]]
        
        logger.info(f"[TABLE-SEL] Selected {len(relevant)} tables from {len(tables)}")
        
        return relevant
    
    def _get_filter_candidate_tables(self) -> Set[str]:
        """Get set of table names that contain filter candidate columns."""
        tables = set()
        for category, candidates in self.filter_candidates.items():
            for cand in candidates:
                table_name = cand.get('table_name', cand.get('table', ''))
                if table_name:
                    tables.add(table_name.lower())
        return tables
    
    def _score_table(self, table: Dict, q_lower: str, words: List[str], 
                     filter_candidate_tables: Set[str]) -> int:
        """
        Score a table's relevance to the question.
        
        Returns an integer score where higher = more relevant.
        """
        table_name = table.get('table_name', '').lower()
        columns = table.get('columns', [])
        row_count = table.get('row_count', 0)
        
        score = 0
        
        # =====================================================================
        # 1. DIRECT NAME MATCHING (highest priority)
        # =====================================================================
        score += self._score_name_match(table_name, words)
        
        # =====================================================================
        # 2. PENALTIES - Apply before boosts
        # =====================================================================
        
        # Lookup table penalty
        is_lookup = any(ind in table_name for ind in LOOKUP_INDICATORS)
        if is_lookup:
            score -= 30
            logger.debug(f"[TABLE-SEL] Lookup penalty: {table_name[-40:]} (-30)")
        
        # Checklist/document table penalty (heavy)
        is_checklist = any(ind in table_name for ind in CHECKLIST_INDICATORS)
        if is_checklist:
            score -= 100
            logger.warning(f"[TABLE-SEL] Checklist penalty: {table_name[-40:]} (-100)")
        
        # Few columns penalty (likely lookup)
        if len(columns) <= 3:
            score -= 20
        
        # =====================================================================
        # 3. FILTER CANDIDATE BOOST
        # =====================================================================
        if table_name in filter_candidate_tables:
            score += 50
            logger.debug(f"[TABLE-SEL] Filter candidate boost: {table_name[-40:]} (+50)")
        
        # =====================================================================
        # 4. KEYWORD PATTERN MATCHING
        # =====================================================================
        for pattern, keywords in TABLE_KEYWORDS.items():
            if pattern in table_name:
                if any(kw in q_lower for kw in keywords):
                    score += 10
                else:
                    score += 1
        
        # =====================================================================
        # 5. DOMAIN-SPECIFIC BOOSTS
        # =====================================================================
        score += self._score_domain_boosts(table_name, q_lower)
        
        # =====================================================================
        # 6. ROW COUNT SCORING
        # =====================================================================
        if row_count > 1000:
            score += 10
        elif row_count > 100:
            score += 5
        elif row_count < 50:
            score -= 5
        
        # =====================================================================
        # 7. COLUMN COUNT SCORING
        # =====================================================================
        if len(columns) > 15:
            score += 10
        elif len(columns) > 8:
            score += 5
        
        # =====================================================================
        # 8. LOCATION COLUMN BOOST
        # =====================================================================
        if any(loc in q_lower for loc in ['location', 'state', 'by state', 'by location', 'geographic']):
            col_names = [c.get('name', '').lower() if isinstance(c, dict) else str(c).lower() 
                        for c in columns]
            if any(loc_col in ' '.join(col_names) for loc_col in LOCATION_COLUMNS):
                score += 40
                logger.debug(f"[TABLE-SEL] Location columns boost: {table_name[-40:]} (+40)")
        
        # =====================================================================
        # 9. COLUMN VALUE MATCHING
        # =====================================================================
        score += self._score_value_match(table, words)
        
        return score
    
    def _score_name_match(self, table_name: str, words: List[str]) -> int:
        """Score based on direct name matching."""
        score = 0
        
        for i, word in enumerate(words):
            if len(word) < 3 or word in SKIP_WORDS:
                continue
            
            # Single word match
            word_singular = word.rstrip('s') if len(word) > 3 and word.endswith('s') else word
            if word in table_name or word_singular in table_name:
                score += 30
            
            # Two-word combination
            if i < len(words) - 1:
                word2 = words[i + 1]
                two_word = f"{word}_{word2}"
                two_word_alt = f"{word}{word2}"
                word2_singular = word2.rstrip('s') if len(word2) > 3 and word2.endswith('s') else word2
                two_word_singular = f"{word}_{word2_singular}"
                
                if any(tw in table_name for tw in [two_word, two_word_alt, two_word_singular]):
                    score += 100
                    logger.warning(f"[TABLE-SEL] DIRECT NAME MATCH: '{two_word}' in {table_name[-45:]} (+100)")
            
            # Three-word combination
            if i < len(words) - 2:
                word2 = words[i + 1]
                word3 = words[i + 2]
                three_word = f"{word}_{word2}_{word3}"
                word3_singular = word3.rstrip('s') if len(word3) > 3 and word3.endswith('s') else word3
                three_word_singular = f"{word}_{word2}_{word3_singular}"
                
                if three_word in table_name or three_word_singular in table_name:
                    score += 120
                    logger.warning(f"[TABLE-SEL] DIRECT NAME MATCH: '{three_word}' in {table_name[-45:]} (+120)")
        
        return score
    
    def _score_domain_boosts(self, table_name: str, q_lower: str) -> int:
        """Apply domain-specific scoring boosts."""
        score = 0
        
        # Tax questions
        tax_terms = ['sui', 'suta', 'futa', 'fein', 'ein', 'tax rate', 'withholding', 
                     'w2', 'w-2', '941', '940']
        if any(term in q_lower for term in tax_terms):
            if 'tax' in table_name:
                score += 60
                logger.warning(f"[TABLE-SEL] Tax boost: {table_name[-40:]} (+60)")
        
        # Workers Comp questions
        wc_terms = ['workers comp', 'work comp', 'wc rate', 'workers compensation', 'wcb']
        if any(term in q_lower for term in wc_terms):
            if any(wc in table_name for wc in ['workers_comp', 'work_comp', 'wc_']):
                score += 70
                logger.warning(f"[TABLE-SEL] Workers Comp boost: {table_name[-40:]} (+70)")
        
        # Earnings questions
        earnings_terms = ['earnings', 'earning code', 'pay code', 'earning setup', 
                          'earnings configured', 'earnigs', 'earings', 'earning']
        if any(term in q_lower for term in earnings_terms):
            if any(e in table_name for e in ['earnings', 'earning', 'pay_code']):
                score += 70
                logger.warning(f"[TABLE-SEL] Earnings boost: {table_name[-40:]} (+70)")
        
        # Deduction questions
        deduction_terms = ['deduction', 'benefit plan', 'deduction setup', 'deductions configured']
        if any(term in q_lower for term in deduction_terms):
            if any(d in table_name for d in ['deduction', 'benefit', 'ded_']):
                score += 70
                logger.warning(f"[TABLE-SEL] Deduction boost: {table_name[-40:]} (+70)")
        
        # GL questions
        gl_terms = ['gl', 'general ledger', 'gl mapping', 'account mapping', 'chart of accounts']
        if any(term in q_lower for term in gl_terms):
            if any(g in table_name for g in ['general_ledger', 'gl_', 'account_map', 'ledger']):
                score += 70
                logger.warning(f"[TABLE-SEL] GL boost: {table_name[-40:]} (+70)")
        
        # Config/validation questions
        config_terms = ['correct', 'configured', 'valid', 'setup', 'setting', 'configuration']
        if any(term in q_lower for term in config_terms):
            if any(cfg in table_name for cfg in ['config', 'validation', 'master', 'setting']):
                score += 50
                logger.warning(f"[TABLE-SEL] Config boost: {table_name[-40:]} (+50)")
        
        return score
    
    def _score_value_match(self, table: Dict, words: List[str]) -> int:
        """
        Score based on column VALUE matching.
        
        This finds tables where query words appear in actual data values,
        not just column names. Critical for questions like "show me SUI rates"
        where "SUI" is a value in the tax_type column.
        """
        if not self.structured_handler or not hasattr(self.structured_handler, 'conn'):
            return 0
        
        score = 0
        table_name = table.get('table_name', '')
        
        try:
            # Get distinct values from column profiles
            value_profiles = self.structured_handler.conn.execute("""
                SELECT column_name, distinct_values
                FROM _column_profiles 
                WHERE LOWER(table_name) = LOWER(?)
                AND distinct_values IS NOT NULL
                AND distinct_values != '[]'
            """, [table_name]).fetchall()
            
            for col_name, distinct_values_json in value_profiles:
                if not distinct_values_json:
                    continue
                
                try:
                    distinct_values = json.loads(distinct_values_json)
                    
                    for val_info in distinct_values:
                        val = str(val_info.get('value', '')).lower().strip() \
                              if isinstance(val_info, dict) else str(val_info).lower().strip()
                        
                        # Skip short values (state codes cause false matches)
                        if not val or len(val) < 3:
                            continue
                        
                        for word in words:
                            if len(word) < 3 or word in SKIP_WORDS:
                                continue
                            
                            # Match if:
                            # 1. Exact match
                            # 2. Word is significant substring of value (4+ chars)
                            # FIXED: Removed reverse match (val in word) which caused "ar" to match "earnings"
                            if word == val or (len(word) >= 4 and word in val):
                                score += 80
                                logger.warning(f"[TABLE-SEL] VALUE MATCH: '{word}' → '{val}' "
                                             f"in {table_name[-40:]}.{col_name} (+80)")
                                break
                                
                except (json.JSONDecodeError, TypeError):
                    pass
                    
        except Exception as e:
            logger.debug(f"[TABLE-SEL] Value match check failed for {table_name}: {e}")
        
        return score
