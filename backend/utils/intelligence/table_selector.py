"""
XLR8 Intelligence Engine - Table Selector v3.0
===============================================

Handles table scoring and selection for SQL generation.
Given a question and available tables, selects the most relevant ones.

v3.0 CHANGES (Context Graph Integration):
- Uses Context Graph hub/spoke relationships for intelligent selection
- Boosts HUB tables when question relates to their semantic type
- Boosts SPOKE tables that connect to relevant hubs
- Uses entity_type for understanding what tables ARE
- Suggests join paths through the graph

v2.1 CHANGES:
- Added fallback domain matching when no classifications exist
- Penalizes tables matching WRONG domain (-50)
- Boosts tables matching detected domain (+80)

v2.0 CHANGES:
- Uses TableClassification metadata instead of hardcoded domain boosts
- Scoring based on table_type and domain from project_intelligence
- Removes canonical matches hack (+250) in favor of metadata-driven selection
- Removes VALUE MATCH cap - replaced by proper domain scoring

Key features:
- Context Graph hub/spoke awareness (highest priority)
- Metadata-driven domain matching
- Fallback name-based domain matching (when no metadata)
- Direct name matching
- Column value matching (finds tables with matching data)
- Lookup/checklist deprioritization

Deploy to: backend/utils/intelligence/table_selector.py
"""

import re
import json
import logging
from typing import Dict, List, Optional, Set, Any, Tuple

from .types import LOOKUP_INDICATORS

# Import table classification types
try:
    from backend.utils.project_intelligence import (
        TableClassification, TableType, TableDomain, 
        get_table_classifications
    )
except ImportError:
    try:
        from utils.project_intelligence import (
            TableClassification, TableType, TableDomain, 
            get_table_classifications
        )
    except ImportError:
        # Fallback for when running standalone
        TableClassification = None
        TableType = None
        TableDomain = None
        get_table_classifications = None

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

# Columns that indicate location data
LOCATION_COLUMNS = ['stateprovince', 'state', 'city', 'location', 'region', 
                    'site', 'work_location', 'home_state']

# Tables to heavily deprioritize (guides, not config data)
CHECKLIST_INDICATORS = ['checklist', 'step_', '_step', 'document', 
                        'before_final', 'year_end', 'yearend']

# =============================================================================
# DOMAIN KEYWORD MAPPING (for question → domain detection)
# =============================================================================

# Question keywords that indicate a domain
# This maps question words to TableDomain values for matching
DOMAIN_KEYWORDS = {
    'earnings': ['earnings', 'earning', 'pay code', 'paycode', 'compensation', 
                 'salary', 'wage', 'earings', 'earnigs'],  # Common typos
    'deductions': ['deduction', 'deductions', 'benefit plan', 'benefits', 
                   '401k', 'insurance', 'health plan'],
    'taxes': ['tax', 'taxes', 'sui', 'suta', 'futa', 'fein', 'ein', 
              'withholding', 'w2', 'w-2', '941', '940', 'fica'],
    'time': ['time', 'hours', 'attendance', 'schedule', 'pto', 'accrual'],
    'demographics': ['employee', 'employees', 'person', 'people', 'worker',
                     'associate', 'staff', 'personal'],
    'locations': ['location', 'locations', 'site', 'address', 'region'],
    'benefits': ['benefit', 'benefits', 'enrollment', 'coverage'],
    'gl': ['gl', 'general ledger', 'ledger', 'account mapping', 
           'chart of accounts', 'gl mapping'],
    'jobs': ['job', 'jobs', 'position', 'title', 'role'],
    'workers_comp': ['workers comp', 'work comp', 'wc', 'wcb', 
                     'workers compensation', 'class code'],
}


# =============================================================================
# SEMANTIC TYPE KEYWORDS (for Context Graph matching)
# =============================================================================

# Maps question keywords to semantic types in the Context Graph
# When these words appear in a question, we boost tables that are 
# hubs/spokes for these semantic types
SEMANTIC_TYPE_KEYWORDS = {
    'company_code': ['company', 'companies', 'organization', 'legal entity'],
    'employee_number': ['employee', 'employees', 'worker', 'staff', 'person'],
    'job_code': ['job', 'jobs', 'position', 'title', 'role'],
    'department_code': ['department', 'dept', 'cost center', 'org unit'],
    'location_code': ['location', 'site', 'work location', 'office'],
    'earning_code': ['earning', 'earnings', 'pay code', 'compensation'],
    'deduction_code': ['deduction', 'deductions', 'benefit code', 'benefits'],
    'employment_status_code': ['status', 'employment status', 'active', 'terminated'],
    'termination_reason_code': ['termination', 'separation', 'term reason', 'why left'],
    'benefit_change_reason_code': ['benefit change', 'life event', 'qualifying event'],
    'job_change_reason_code': ['job change', 'transfer reason', 'promotion'],
    'loa_reason_code': ['leave', 'loa', 'absence', 'time off reason'],
    'tax_code': ['tax', 'taxes', 'withholding', 'w2', 'w-2', 'fica', 'sui', 'futa'],
}

# =============================================================================
# TABLE NAME DOMAIN KEYWORDS (v4.0 - explicit table name matching)
# =============================================================================
# When user asks for "earnings", a table with "earnings" in its NAME should 
# massively outrank tables that just MENTION earnings in column values
TABLE_NAME_DOMAIN_KEYWORDS = {
    'earnings': ['earning', 'earnings'],
    'deductions': ['deduction', 'deductions', 'benefit'],
    'jobs': ['job', 'jobs', 'position'],
    'locations': ['location', 'locations', 'site'],
    'employees': ['employee', 'employees'],
    'taxes': ['tax', 'taxes'],
    'companies': ['company', 'companies'],
    'departments': ['department', 'departments', 'dept'],
    'pto': ['pto', 'accrual', 'time off'],
    'gl': ['gl', 'general ledger'],
}


# =============================================================================
# TABLE SELECTOR CLASS
# =============================================================================

class TableSelector:
    """
    Selects relevant tables for a given question.
    
    v3.0: Uses Context Graph for intelligent hub/spoke-aware selection.
    v2.0: Uses table classification metadata for domain-aware selection.
    
    Uses a scoring system that considers:
    - Context Graph hub/spoke relationships (highest priority)
    - Domain matching via classifications
    - Table type (CONFIG tables boost for setup questions)
    - Direct name matches
    - Column value matches
    - Penalties for lookup/checklist tables
    """
    
    def __init__(self, structured_handler=None, filter_candidates: Dict = None,
                 project: str = None):
        """
        Initialize the table selector.
        
        Args:
            structured_handler: DuckDB handler for value lookups
            filter_candidates: Dict of filter category → candidate columns
            project: Project name for loading classifications
        """
        self.structured_handler = structured_handler
        self.filter_candidates = filter_candidates or {}
        self.project = project
        
        # Cache for table classifications
        self._classifications: Dict[str, TableClassification] = {}
        self._classifications_loaded = False
        
        # Cache for context graph
        self._context_graph: Dict = None
        self._context_graph_loaded = False
    
    # =========================================================================
    # CONTEXT GRAPH METHODS (v3.0)
    # =========================================================================
    
    def _load_context_graph(self) -> None:
        """Load context graph from structured handler."""
        if self._context_graph_loaded:
            return
        
        logger.warning(f"[TABLE-SEL] Loading context graph: project={self.project}, has_handler={self.structured_handler is not None}")
        
        if not self.project or not self.structured_handler:
            logger.warning(f"[TABLE-SEL] Cannot load context graph: project={self.project}, handler={self.structured_handler}")
            self._context_graph_loaded = True
            return
        
        try:
            has_method = hasattr(self.structured_handler, 'get_context_graph')
            logger.warning(f"[TABLE-SEL] Handler has get_context_graph: {has_method}")
            
            if has_method:
                self._context_graph = self.structured_handler.get_context_graph(self.project)
                hub_count = len(self._context_graph.get('hubs', []))
                rel_count = len(self._context_graph.get('relationships', []))
                logger.warning(f"[TABLE-SEL] ✅ Context graph loaded: {hub_count} hubs, {rel_count} relationships")
                
                # Log first few hubs for debugging
                for hub in self._context_graph.get('hubs', [])[:3]:
                    logger.warning(f"[TABLE-SEL]   Hub: {hub.get('semantic_type')} in {hub.get('table', '')[-40:]}")
            else:
                logger.warning("[TABLE-SEL] ❌ Handler does not have get_context_graph method")
        except Exception as e:
            logger.warning(f"[TABLE-SEL] ❌ Failed to load context graph: {e}")
            import traceback
            logger.warning(f"[TABLE-SEL] Traceback: {traceback.format_exc()}")
        
        self._context_graph_loaded = True
    
    def _get_context_graph(self) -> Dict:
        """Get cached context graph."""
        self._load_context_graph()
        return self._context_graph or {'hubs': [], 'relationships': []}
    
    def _detect_semantic_types(self, q_lower: str) -> List[str]:
        """
        Detect which semantic types are relevant to a question.
        
        Returns:
            List of semantic type names (e.g., ['company_code', 'employee_number'])
        """
        relevant_types = []
        for sem_type, keywords in SEMANTIC_TYPE_KEYWORDS.items():
            if any(kw in q_lower for kw in keywords):
                relevant_types.append(sem_type)
        return relevant_types
    
    def _score_context_graph(self, table_name: str, relevant_semantic_types: List[str]) -> int:
        """
        Score table based on Context Graph hub/spoke relationships.
        
        Returns bonus if:
        - Table is a HUB for a relevant semantic type (+120)
        - Table is a SPOKE connected to a relevant hub (+80)
        - Additional bonus for high coverage spokes (+20)
        """
        if not relevant_semantic_types:
            return 0
        
        graph = self._get_context_graph()
        hubs = graph.get('hubs', [])
        relationships = graph.get('relationships', [])
        
        if not hubs and not relationships:
            logger.debug(f"[TABLE-SEL] Context graph empty for {table_name[-30:]}")
            return 0
        
        score = 0
        table_lower = table_name.lower()
        
        # Check if this table is a HUB for any relevant semantic type
        for hub in graph.get('hubs', []):
            hub_table = hub.get('table', '').lower()
            hub_semantic_type = hub.get('semantic_type', '')
            
            # Debug: Log comparison for relevant semantic types
            if hub_semantic_type in relevant_semantic_types:
                logger.warning(f"[TABLE-SEL] HUB CHECK: table='{table_lower[-50:]}' vs hub='{hub_table[-50:]}' semantic={hub_semantic_type}")
            
            # Try both exact match and suffix match (handle prefix differences)
            is_match = (hub_table == table_lower) or (table_lower.endswith(hub_table)) or (hub_table.endswith(table_lower))
            
            if is_match and hub_semantic_type in relevant_semantic_types:
                score += 120  # Strong boost for being THE hub
                logger.warning(f"[TABLE-SEL] CONTEXT GRAPH HUB: {table_name[-40:]} is hub for {hub_semantic_type} (+120)")
                
                # Extra boost if hub has Reality spokes (data is being used)
                if hub.get('has_reality_spokes'):
                    score += 20
        
        # Check if this table is a SPOKE for any relevant semantic type
        for rel in graph.get('relationships', []):
            spoke_table = rel.get('spoke_table', '').lower()
            rel_semantic_type = rel.get('semantic_type', '')
            
            # Try both exact match and suffix match (handle prefix differences)
            is_match = (spoke_table == table_lower) or (table_lower.endswith(spoke_table)) or (spoke_table.endswith(table_lower))
            
            if is_match and rel_semantic_type in relevant_semantic_types:
                score += 80  # Good boost for being a spoke
                
                # Extra boost for high coverage (>50%)
                coverage = rel.get('coverage_pct', 0) or 0
                if coverage > 50:
                    score += 20
                
                # Extra boost for Reality tables (actual data, not just config)
                if rel.get('truth_type') == 'reality':
                    score += 30
                
                logger.warning(f"[TABLE-SEL] CONTEXT GRAPH SPOKE: {table_name[-40:]} references {rel_semantic_type} "
                             f"(coverage={coverage:.0f}%, truth={rel.get('truth_type')}) (+{80 + (20 if coverage > 50 else 0) + (30 if rel.get('truth_type') == 'reality' else 0)})")
        
        return score
    
    def get_join_path(self, from_table: str, to_table: str) -> Optional[Dict]:
        """
        Find a join path between two tables using the Context Graph.
        
        Returns:
            Dict with join info if path found, None otherwise
            {
                'semantic_type': 'company_code',
                'from_column': 'company_code',
                'to_column': 'company_code',
                'via_hub': 'component_company'  # if indirect join
            }
        """
        graph = self._get_context_graph()
        from_lower = from_table.lower()
        to_lower = to_table.lower()
        
        # Build lookup of table → semantic types it participates in
        table_semantic_types = {}
        
        for hub in graph.get('hubs', []):
            hub_table = hub.get('table', '').lower()
            sem_type = hub.get('semantic_type', '')
            col = hub.get('column', '')
            if hub_table not in table_semantic_types:
                table_semantic_types[hub_table] = []
            table_semantic_types[hub_table].append({'semantic_type': sem_type, 'column': col, 'is_hub': True})
        
        for rel in graph.get('relationships', []):
            spoke_table = rel.get('spoke_table', '').lower()
            sem_type = rel.get('semantic_type', '')
            col = rel.get('spoke_column', '')
            if spoke_table not in table_semantic_types:
                table_semantic_types[spoke_table] = []
            table_semantic_types[spoke_table].append({
                'semantic_type': sem_type, 
                'column': col, 
                'is_hub': False,
                'hub_table': rel.get('hub_table'),
                'hub_column': rel.get('hub_column')
            })
        
        # Find common semantic types between the two tables
        from_types = {t['semantic_type']: t for t in table_semantic_types.get(from_lower, [])}
        to_types = {t['semantic_type']: t for t in table_semantic_types.get(to_lower, [])}
        
        common_types = set(from_types.keys()) & set(to_types.keys())
        
        if common_types:
            # Direct join possible
            sem_type = list(common_types)[0]  # Pick first common type
            return {
                'semantic_type': sem_type,
                'from_column': from_types[sem_type]['column'],
                'to_column': to_types[sem_type]['column'],
                'join_type': 'direct'
            }
        
        # Check for indirect join via hub
        for from_type_info in table_semantic_types.get(from_lower, []):
            for to_type_info in table_semantic_types.get(to_lower, []):
                # If both reference the same hub
                from_hub = from_type_info.get('hub_table')
                to_hub = to_type_info.get('hub_table')
                
                if from_hub and to_hub and from_hub == to_hub:
                    return {
                        'semantic_type': from_type_info['semantic_type'],
                        'from_column': from_type_info['column'],
                        'to_column': to_type_info['column'],
                        'via_hub': from_hub,
                        'hub_column': from_type_info.get('hub_column'),
                        'join_type': 'via_hub'
                    }
        
        return None
    
    def get_related_tables(self, table_name: str) -> List[Dict]:
        """
        Get tables related to the given table through the Context Graph.
        
        Returns:
            List of related tables with relationship info
        """
        graph = self._get_context_graph()
        table_lower = table_name.lower()
        related = []
        
        # Find semantic types this table participates in
        my_semantic_types = set()
        
        for hub in graph.get('hubs', []):
            if hub.get('table', '').lower() == table_lower:
                my_semantic_types.add(hub.get('semantic_type'))
        
        for rel in graph.get('relationships', []):
            if rel.get('spoke_table', '').lower() == table_lower:
                my_semantic_types.add(rel.get('semantic_type'))
        
        # Find other tables with same semantic types
        for sem_type in my_semantic_types:
            # Find hub for this type
            for hub in graph.get('hubs', []):
                if hub.get('semantic_type') == sem_type:
                    hub_table = hub.get('table', '').lower()
                    if hub_table != table_lower:
                        related.append({
                            'table': hub.get('table'),
                            'relationship': 'hub',
                            'semantic_type': sem_type,
                            'column': hub.get('column')
                        })
            
            # Find spokes for this type
            for rel in graph.get('relationships', []):
                if rel.get('semantic_type') == sem_type:
                    spoke_table = rel.get('spoke_table', '').lower()
                    if spoke_table != table_lower:
                        related.append({
                            'table': rel.get('spoke_table'),
                            'relationship': 'spoke',
                            'semantic_type': sem_type,
                            'column': rel.get('spoke_column'),
                            'coverage_pct': rel.get('coverage_pct')
                        })
        
        return related
    
    def _load_classifications(self) -> None:
        """Load table classifications from database."""
        if self._classifications_loaded:
            return
        
        if not self.project or not self.structured_handler:
            logger.warning(f"[TABLE-SEL] Cannot load classifications: project={self.project}, handler={bool(self.structured_handler)}")
            self._classifications_loaded = True
            return
        
        try:
            # Try to load classifications using the helper function
            if get_table_classifications:
                classifications = get_table_classifications(
                    self.project, self.structured_handler
                )
                for c in classifications:
                    self._classifications[c.table_name.lower()] = c
                logger.warning(f"[TABLE-SEL] Loaded {len(self._classifications)} classifications for project={self.project}")
            else:
                # Fallback: load directly from database
                logger.warning(f"[TABLE-SEL] Using direct classification load for project={self.project}")
                self._load_classifications_direct()
                
        except Exception as e:
            logger.warning(f"[TABLE-SEL] Failed to load classifications: {e}")
            import traceback
            logger.warning(traceback.format_exc())
        
        self._classifications_loaded = True
    
    def _load_classifications_direct(self) -> None:
        """Load classifications directly from DuckDB (fallback)."""
        if not self.structured_handler or not hasattr(self.structured_handler, 'conn'):
            return
        
        try:
            # Check if table exists
            tables = self.structured_handler.conn.execute("SHOW TABLES").fetchall()
            table_names = [t[0] for t in tables]
            
            if '_table_classifications' not in table_names:
                return
            
            results = self.structured_handler.conn.execute("""
                SELECT table_name, table_type, domain, primary_entity, confidence,
                       row_count, column_count, config_target
                FROM _table_classifications
                WHERE project_name = ?
            """, [self.project]).fetchall()
            
            for row in results:
                table_name = row[0]
                self._classifications[table_name.lower()] = {
                    'table_name': table_name,
                    'table_type': row[1],
                    'domain': row[2],
                    'primary_entity': row[3],
                    'confidence': row[4],
                    'row_count': row[5],
                    'column_count': row[6],
                    'config_target': row[7]
                }
            
            logger.warning(f"[TABLE-SEL] Loaded {len(self._classifications)} classifications (direct)")
            
        except Exception as e:
            logger.debug(f"[TABLE-SEL] Direct classification load failed: {e}")
    
    def _get_classification(self, table_name: str) -> Optional[Dict]:
        """Get classification for a table."""
        self._load_classifications()
        return self._classifications.get(table_name.lower())
    
    def _detect_question_domain(self, q_lower: str) -> Optional[str]:
        """
        Detect the domain a question is asking about.
        
        Returns:
            Domain string (e.g., 'earnings', 'taxes') or None
        """
        for domain, keywords in DOMAIN_KEYWORDS.items():
            if any(kw in q_lower for kw in keywords):
                return domain
        return None
    
    def select(self, tables: List[Dict], question: str, max_tables: int = 5) -> List[Dict]:
        """
        Select the most relevant tables for a question.
        
        v3.0: Now uses Context Graph for intelligent hub/spoke-aware selection.
        
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
        
        logger.warning(f"[TABLE-SEL] ========== SELECT START ==========")
        logger.warning(f"[TABLE-SEL] Question: {question[:80]}")
        logger.warning(f"[TABLE-SEL] Tables to score: {len(tables)}")
        
        # Detect what domain the question is about
        question_domain = self._detect_question_domain(q_lower)
        logger.warning(f"[TABLE-SEL] Question domain: {question_domain}")
        
        # v3.0: Detect relevant semantic types for Context Graph matching
        relevant_semantic_types = self._detect_semantic_types(q_lower)
        logger.warning(f"[TABLE-SEL] Semantic types: {relevant_semantic_types}")
        
        # v4.0: Force load context graph and report status
        graph = self._get_context_graph()
        logger.warning(f"[TABLE-SEL] Context graph: {len(graph.get('hubs', []))} hubs, {len(graph.get('relationships', []))} relationships")
        
        # Check if this is a config/setup question
        is_config_question = any(term in q_lower for term in [
            'configured', 'setup', 'set up', 'valid', 'correct', 
            'configuration', 'settings', 'how many', 'what', 'list'
        ])
        
        # Identify tables that contain filter_candidate columns
        filter_candidate_tables = self._get_filter_candidate_tables()
        
        # Score each table
        scored_tables = []
        for table in tables:
            score = self._score_table(
                table, q_lower, words, filter_candidate_tables,
                question_domain, is_config_question, relevant_semantic_types
            )
            scored_tables.append((score, table))
        
        # Sort by score descending
        scored_tables.sort(key=lambda x: -x[0])
        
        # Log top candidates
        for score, t in scored_tables[:5]:
            table_name = t.get('table_name', '')
            classification = self._get_classification(table_name)
            domain_info = ""
            if classification:
                if isinstance(classification, dict):
                    domain_info = f" [type={classification.get('table_type')}, domain={classification.get('domain')}]"
                else:
                    domain_info = f" [type={classification.table_type.value}, domain={classification.domain.value}]"
            logger.warning(f"[TABLE-SEL] Candidate: {table_name[-45:]} score={score}{domain_info}")
        
        # Take top N tables with positive scores
        relevant = [t for score, t in scored_tables[:max_tables] if score > 0]
        
        # If nothing found, return first table as fallback
        if not relevant and tables:
            relevant = [tables[0]]
        
        logger.warning(f"[TABLE-SEL] Selected {len(relevant)} tables from {len(tables)}")
        logger.warning(f"[TABLE-SEL] ========== SELECT END ==========")
        
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
                     filter_candidate_tables: Set[str],
                     question_domain: Optional[str],
                     is_config_question: bool,
                     relevant_semantic_types: List[str] = None) -> int:
        """
        Score a table's relevance to the question.
        
        v3.0: Adds Context Graph hub/spoke scoring (highest priority).
        v2.1: Adds fallback domain matching when no classifications exist.
        
        Returns an integer score where higher = more relevant.
        """
        table_name = table.get('table_name', '').lower()
        columns = table.get('columns', [])
        row_count = table.get('row_count', 0)
        
        score = 0
        
        # =====================================================================
        # 0a. TABLE NAME DOMAIN MATCH (v4.0 - highest priority)
        # When user asks for "earnings", table NAMED earnings_earnings should 
        # crush tables that just mention earnings in column values
        # =====================================================================
        requested_domain = None
        for domain, keywords in TABLE_NAME_DOMAIN_KEYWORDS.items():
            # Check if question contains this domain keyword
            if any(kw in q_lower for kw in keywords):
                requested_domain = domain
                # Check if table NAME contains the domain
                if domain in table_name or any(kw in table_name for kw in keywords):
                    score += 200  # Massive boost - table IS the domain
                    logger.warning(f"[TABLE-SEL] TABLE NAME DOMAIN MATCH: {table_name[-45:]} matches '{domain}' (+200)")
                break
        
        # Penalize tables that are clearly WRONG domain when user asked for something specific
        if requested_domain:
            # List of domains that are DIFFERENT from requested
            wrong_domains = [d for d in TABLE_NAME_DOMAIN_KEYWORDS.keys() if d != requested_domain]
            for wrong_domain in wrong_domains:
                wrong_keywords = TABLE_NAME_DOMAIN_KEYWORDS[wrong_domain]
                # If table name contains a DIFFERENT domain keyword, penalize
                if wrong_domain in table_name or any(kw in table_name for kw in wrong_keywords if len(kw) > 3):
                    score -= 150  # Heavy penalty for wrong domain
                    logger.warning(f"[TABLE-SEL] WRONG TABLE NAME DOMAIN: {table_name[-45:]} is '{wrong_domain}', want '{requested_domain}' (-150)")
                    break
        
        # =====================================================================
        # 0b. CONTEXT GRAPH SCORING (v3.0)
        # =====================================================================
        if relevant_semantic_types:
            context_score = self._score_context_graph(table_name, relevant_semantic_types)
            score += context_score
        
        # =====================================================================
        # 1. METADATA-BASED DOMAIN MATCHING (v2.0)
        # =====================================================================
        metadata_score = self._score_metadata_match(table_name, question_domain, is_config_question)
        score += metadata_score
        
        # =====================================================================
        # 1b. FALLBACK DOMAIN MATCHING (when no classifications)
        # If question has a clear domain but no metadata exists, use name-based matching
        # =====================================================================
        if question_domain and metadata_score == 0:
            score += self._score_fallback_domain(table_name, question_domain, q_lower)
        
        # =====================================================================
        # 2. DIRECT NAME MATCHING
        # =====================================================================
        score += self._score_name_match(table_name, words)
        
        # =====================================================================
        # 3. PENALTIES - Apply before boosts
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
        # 4. FILTER CANDIDATE BOOST
        # =====================================================================
        if table_name in filter_candidate_tables:
            score += 50
            logger.debug(f"[TABLE-SEL] Filter candidate boost: {table_name[-40:]} (+50)")
        
        # =====================================================================
        # 5. ROW COUNT SCORING
        # =====================================================================
        if row_count > 1000:
            score += 10
        elif row_count > 100:
            score += 5
        elif row_count < 50:
            score -= 5
        
        # =====================================================================
        # 6. COLUMN COUNT SCORING
        # =====================================================================
        if len(columns) > 15:
            score += 10
        elif len(columns) > 8:
            score += 5
        
        # =====================================================================
        # 7. LOCATION COLUMN BOOST
        # =====================================================================
        if any(loc in q_lower for loc in ['location', 'state', 'by state', 'by location', 'geographic']):
            col_names = [c.get('name', '').lower() if isinstance(c, dict) else str(c).lower() 
                        for c in columns]
            if any(loc_col in ' '.join(col_names) for loc_col in LOCATION_COLUMNS):
                score += 40
                logger.debug(f"[TABLE-SEL] Location columns boost: {table_name[-40:]} (+40)")
        
        # =====================================================================
        # 8. COLUMN VALUE MATCHING (kept but not capped artificially)
        # =====================================================================
        score += self._score_value_match(table, words)
        
        return score
    
    def _score_fallback_domain(self, table_name: str, question_domain: str, q_lower: str) -> int:
        """
        Fallback domain scoring when no classifications exist.
        
        Checks if table name contains domain keywords and applies boost/penalty.
        This ensures "tax" questions prefer "tax" tables over "workers_comp" tables.
        """
        score = 0
        
        # Get keywords for the detected domain
        domain_keywords = DOMAIN_KEYWORDS.get(question_domain, [])
        
        # Check if table name matches question domain
        table_matches_domain = any(kw.replace(' ', '_') in table_name or kw.replace(' ', '') in table_name 
                                   for kw in domain_keywords)
        
        if table_matches_domain:
            score += 80  # Strong boost for matching domain
            logger.warning(f"[TABLE-SEL] FALLBACK DOMAIN MATCH: {table_name[-40:]} domain={question_domain} (+80)")
        else:
            # Check if table matches a DIFFERENT domain (penalty)
            for other_domain, other_keywords in DOMAIN_KEYWORDS.items():
                if other_domain == question_domain:
                    continue
                if any(kw.replace(' ', '_') in table_name or kw.replace(' ', '') in table_name 
                       for kw in other_keywords):
                    score -= 50  # Penalty for wrong domain
                    logger.warning(f"[TABLE-SEL] WRONG DOMAIN PENALTY: {table_name[-40:]} is {other_domain}, want {question_domain} (-50)")
                    break
        
        return score
    
    def _score_metadata_match(self, table_name: str, question_domain: Optional[str],
                               is_config_question: bool) -> int:
        """
        Score based on table classification metadata.
        
        v2.0: This replaces the hardcoded domain boosts with metadata-driven scoring.
        
        Returns:
            Score adjustment based on metadata match
        """
        classification = self._get_classification(table_name)
        if not classification:
            return 0
        
        score = 0
        
        # Extract domain and type from classification (handle both dict and object)
        if isinstance(classification, dict):
            table_domain = classification.get('domain', 'general')
            table_type = classification.get('table_type', 'unknown')
            config_target = classification.get('config_target')
        else:
            table_domain = classification.domain.value if hasattr(classification.domain, 'value') else str(classification.domain)
            table_type = classification.table_type.value if hasattr(classification.table_type, 'value') else str(classification.table_type)
            config_target = classification.config_target
        
        # =====================================================================
        # DOMAIN MATCHING
        # If question is about earnings and table's domain is earnings, big boost
        # =====================================================================
        if question_domain and table_domain == question_domain:
            score += 100  # Strong boost for domain match
            logger.warning(f"[TABLE-SEL] DOMAIN MATCH: {table_name[-40:]} domain={table_domain} (+100)")
        
        # =====================================================================
        # CONFIG TABLE BOOST
        # If this is a "what's configured" question and table is CONFIG type
        # =====================================================================
        if is_config_question and table_type == 'config':
            score += 80  # Strong boost for CONFIG tables on setup questions
            logger.warning(f"[TABLE-SEL] CONFIG TYPE MATCH: {table_name[-40:]} (+80)")
            
            # Extra boost if config_target matches question domain
            if config_target and question_domain and config_target == question_domain:
                score += 50  # Very strong - this is THE config table for this domain
                logger.warning(f"[TABLE-SEL] CONFIG TARGET MATCH: {table_name[-40:]} target={config_target} (+50)")
        
        # =====================================================================
        # MASTER TABLE BOOST for "how many" questions
        # =====================================================================
        if 'how many' in table_name or any(w in ['count', 'total'] for w in table_name.split('_')):
            if table_type == 'master':
                score += 40  # Master tables are good for counting entities
        
        return score
    
    def _score_name_match(self, table_name: str, words: List[str]) -> int:
        """Score based on direct name matching."""
        score = 0
        
        # =====================================================================
        # STANDARD NAME MATCHING
        # =====================================================================
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
    
    def _score_value_match(self, table: Dict, words: List[str]) -> int:
        """
        Score based on column VALUE matching.
        
        This finds tables where query words appear in actual data values,
        not just column names. Critical for questions like "show me SUI rates"
        where "SUI" is a value in the tax_type column.
        
        v2.0: Removed artificial cap now that domain metadata provides 
        proper prioritization.
        """
        if not self.structured_handler or not hasattr(self.structured_handler, 'conn'):
            return 0
        
        score = 0
        table_name = table.get('table_name', '')
        matches_found = 0
        max_matches = 3  # Reasonable limit, but not artificially capped at 1
        
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
                if matches_found >= max_matches:
                    break
                if not distinct_values_json:
                    continue
                
                try:
                    distinct_values = json.loads(distinct_values_json)
                    
                    for val_info in distinct_values:
                        if matches_found >= max_matches:
                            break
                        
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
                            if word == val or (len(word) >= 4 and word in val):
                                score += 60  # Value match bonus
                                matches_found += 1
                                logger.warning(f"[TABLE-SEL] VALUE MATCH: '{word}' → '{val}' "
                                             f"in {table_name[-40:]}.{col_name} (+60)")
                                break
                                
                except (json.JSONDecodeError, TypeError):
                    pass
                    
        except Exception as e:
            logger.warning(f"[TABLE-SEL] Value match check failed for {table_name}: {e}")
        
        return score


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def select_tables(tables: List[Dict], question: str, 
                  structured_handler=None, project: str = None,
                  max_tables: int = 5) -> List[Dict]:
    """
    Convenience function to select tables for a question.
    
    Args:
        tables: List of table metadata
        question: User's question
        structured_handler: DuckDB handler
        project: Project name
        max_tables: Maximum tables to return
        
    Returns:
        List of selected tables
    """
    selector = TableSelector(
        structured_handler=structured_handler,
        project=project
    )
    return selector.select(tables, question, max_tables)
