"""
Term Index Module - Load-Time Intelligence for Deterministic Query Resolution

This module builds searchable indexes at upload time to eliminate query-time guesswork.
Instead of scanning 73 tables and using hardcoded mappings, we lookup terms directly.

ARCHITECTURE:
- _term_index: Maps terms (like "texas") to SQL filters (state='TX')
- _entity_tables: Maps entities (like "employee") to tables
- join_priority: Enhancement to _column_mappings for deterministic JOIN key selection

VENDOR SCHEMA INTEGRATION:
- Reads vendor JSON files from /config/vendors/{vendor}/
- Uses hub definitions to enhance semantic type detection
- Uses column patterns for better column classification
- Uses spoke patterns to inform join priorities

POPULATION SOURCES:
1. Column values during profiling (e.g., "TX" in state column)
2. Synonym mappings (e.g., "texas" → "TX")
3. Lookup tables (e.g., "Medical Insurance" → deduction code "MED")
4. Vendor schemas (e.g., known UKG Pro hub types)

Author: Claude (Anthropic)
Date: 2026-01-11
"""

import json
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple, Any
import duckdb

# Evolution 3: Import value parser for numeric expressions
try:
    from .value_parser import (
        parse_numeric_expression, 
        parse_date_expression,
        detect_numeric_columns,
        detect_date_columns,
        ComparisonOp,
        ParsedValue
    )
    HAS_VALUE_PARSER = True
except ImportError:
    HAS_VALUE_PARSER = False

logger = logging.getLogger(__name__)

# =============================================================================
# DATA CLASSES
# =============================================================================

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
    term_type: str = 'value'  # 'value', 'synonym', 'pattern', 'lookup'


@dataclass
class JoinPath:
    """A join path between two tables."""
    table1: str
    column1: str
    table2: str
    column2: str
    semantic_type: str
    priority: int = 50


# =============================================================================
# SYNONYM DEFINITIONS
# =============================================================================

# US State name → code mappings (built from data, not hardcoded for query-time)
STATE_SYNONYMS: Dict[str, List[str]] = {
    'AL': ['alabama'],
    'AK': ['alaska'],
    'AZ': ['arizona'],
    'AR': ['arkansas'],
    'CA': ['california', 'cali'],
    'CO': ['colorado'],
    'CT': ['connecticut'],
    'DE': ['delaware'],
    'FL': ['florida'],
    'GA': ['georgia'],
    'HI': ['hawaii'],
    'ID': ['idaho'],
    'IL': ['illinois'],
    'IN': ['indiana'],
    'IA': ['iowa'],
    'KS': ['kansas'],
    'KY': ['kentucky'],
    'LA': ['louisiana'],
    'ME': ['maine'],
    'MD': ['maryland'],
    'MA': ['massachusetts'],
    'MI': ['michigan'],
    'MN': ['minnesota'],
    'MS': ['mississippi'],
    'MO': ['missouri'],
    'MT': ['montana'],
    'NE': ['nebraska'],
    'NV': ['nevada'],
    'NH': ['new hampshire'],
    'NJ': ['new jersey'],
    'NM': ['new mexico'],
    'NY': ['new york'],
    'NC': ['north carolina'],
    'ND': ['north dakota'],
    'OH': ['ohio'],
    'OK': ['oklahoma'],
    'OR': ['oregon'],
    'PA': ['pennsylvania'],
    'RI': ['rhode island'],
    'SC': ['south carolina'],
    'SD': ['south dakota'],
    'TN': ['tennessee'],
    'TX': ['texas', 'tex'],
    'UT': ['utah'],
    'VT': ['vermont'],
    'VA': ['virginia'],
    'WA': ['washington'],
    'WV': ['west virginia'],
    'WI': ['wisconsin'],
    'WY': ['wyoming'],
    # Canadian provinces
    'ON': ['ontario'],
    'QC': ['quebec'],
    'BC': ['british columbia'],
    'AB': ['alberta'],
    'MB': ['manitoba'],
    'SK': ['saskatchewan'],
    'NS': ['nova scotia'],
    'NB': ['new brunswick'],
    'NL': ['newfoundland'],
    'PE': ['prince edward island'],
}

# Reverse mapping for quick lookup: state name → code
STATE_NAME_TO_CODE: Dict[str, str] = {}
for code, names in STATE_SYNONYMS.items():
    for name in names:
        STATE_NAME_TO_CODE[name] = code

# Employment status synonyms
STATUS_SYNONYMS: Dict[str, List[str]] = {
    'A': ['active', 'current', 'employed', 'working'],
    'T': ['terminated', 'termed', 'former', 'inactive', 'separated'],
    'L': ['leave', 'loa', 'on leave', 'absent'],
    'P': ['pending', 'pre-hire', 'future', 'new hire'],
    'R': ['retired', 'retiree'],
    'D': ['deceased'],
    'S': ['suspended'],
    # Common spelled-out values
    'ACTIVE': ['active', 'current', 'employed'],
    'TERMINATED': ['terminated', 'termed', 'former', 'fired', 'resigned'],
    'INACTIVE': ['inactive', 'not active', 'disabled'],
}

# Join priority by semantic type
JOIN_PRIORITY_MAP: Dict[str, int] = {
    # Primary person identifiers - highest priority
    'employee_number': 100,
    'person_number': 100,
    'worker_id': 100,
    'employee_id': 100,
    'person_id': 100,
    'emp_no': 100,
    'empno': 100,
    
    # Organization identifiers
    'company_code': 80,
    'component_company_code': 80,
    'org_code': 80,
    'organization_id': 80,
    'cocode': 80,
    
    # Secondary identifiers
    'location_code': 60,
    'cost_center': 60,
    'cost_center_code': 60,
    'department_code': 60,
    'department_id': 60,
    
    # Tertiary
    'job_code': 40,
    'job_code_code': 40,
    'position_code': 40,
    'pay_group': 40,
    'pay_group_code': 40,
    
    # Payroll/transaction
    'earning_code': 30,
    'earnings_code': 30,
    'deduction_code': 30,
    'tax_code': 30,
    
    # Generic codes (lowest priority)
    'status_code': 20,
}

# Common stop words to skip during term resolution
STOP_WORDS: Set[str] = {
    'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
    'may', 'might', 'can', 'shall', 'must', 'need', 'to', 'of', 'for', 'with',
    'at', 'by', 'from', 'about', 'into', 'through', 'during', 'before', 'after',
    'above', 'below', 'between', 'under', 'again', 'further', 'then', 'once',
    'here', 'there', 'when', 'where', 'why', 'how', 'all', 'each', 'few', 'more',
    'most', 'other', 'some', 'such', 'no', 'not', 'only', 'own', 'same', 'so',
    'than', 'too', 'very', 'just', 'also', 'now', 'if', 'or', 'and', 'but',
    'show', 'me', 'give', 'get', 'find', 'list', 'what', 'which', 'who', 'whom',
    'data', 'information', 'details', 'records',
    # CRITICAL: These short words match state codes but are almost always prepositions
    'in',   # Would match Indiana (IN)
    'on',   # Would match Ontario (ON) 
    'ok',   # Would match Oklahoma (OK) - but also "ok" in conversation
    'hi',   # Would match Hawaii (HI)
    'me',   # Would match Maine (ME) - already in list above
    'or',   # Would match Oregon (OR) - already in list above
}

# Entity words - NOT filter values, but entity indicators for table selection
# These are handled specially, not filtered as WHERE clauses
ENTITY_WORDS: Set[str] = {
    'employees', 'employee', 'workers', 'worker', 'people', 'staff', 'team',
    'person', 'persons', 'personnel', 'member', 'members',
}

# =============================================================================
# ENTITY AND DOMAIN MAPPINGS
# =============================================================================

# Maps domain classifications to canonical entity names
# Domain (from classification) → entity (for table lookup)
DOMAIN_TO_ENTITY: Dict[str, str] = {
    'hr': 'employee',
    'demographics': 'employee',
    'personnel': 'employee',
    'payroll': 'employee',
    'compensation': 'employee',
    'benefits': 'benefits',
    'benefit': 'benefits',
    'deductions': 'benefits',
    'tax': 'tax',
    'taxes': 'tax',
    'time': 'time',
    'timekeeping': 'time',
    'attendance': 'time',
    'scheduling': 'time',
    'leave': 'leave',
    'pto': 'leave',
    'accruals': 'leave',
    'organization': 'organization',
    'org': 'organization',
    'company': 'organization',
    'location': 'location',
    'job': 'job',
    'position': 'job',
}

# Maps user query terms to canonical entities
# Query term → canonical entity
ENTITY_SYNONYMS: Dict[str, str] = {
    # Employee/person variants
    'employees': 'employee',
    'employee': 'employee',
    'workers': 'employee',
    'worker': 'employee',
    'people': 'employee',
    'person': 'employee',
    'persons': 'employee',
    'staff': 'employee',
    'team': 'employee',
    'personnel': 'employee',
    'members': 'employee',
    'member': 'employee',
    'headcount': 'employee',
    
    # Benefits variants
    'benefits': 'benefits',
    'benefit': 'benefits',
    'deductions': 'benefits',
    'deduction': 'benefits',
    'insurance': 'benefits',
    '401k': 'benefits',
    'retirement': 'benefits',
    'pension': 'benefits',
    'hsa': 'benefits',
    'fsa': 'benefits',
    'medical': 'benefits',
    'dental': 'benefits',
    'vision': 'benefits',
    
    # Tax variants
    'taxes': 'tax',
    'tax': 'tax',
    'withholding': 'tax',
    'withholdings': 'tax',
    'w2': 'tax',
    'w4': 'tax',
    
    # Time variants
    'time': 'time',
    'timekeeping': 'time',
    'attendance': 'time',
    'hours': 'time',
    'punches': 'time',
    'clock': 'time',
    'schedule': 'time',
    'scheduling': 'time',
    
    # Leave variants
    'leave': 'leave',
    'pto': 'leave',
    'vacation': 'leave',
    'sick': 'leave',
    'accruals': 'leave',
    'accrual': 'leave',
    'balances': 'leave',
    
    # Payroll variants
    'payroll': 'payroll',
    'pay': 'payroll',
    'earnings': 'payroll',
    'salary': 'payroll',
    'wages': 'payroll',
    'compensation': 'payroll',
    
    # Organization variants
    'organization': 'organization',
    'org': 'organization',
    'company': 'organization',
    'companies': 'organization',
    'department': 'organization',
    'departments': 'organization',
    'division': 'organization',
    
    # Location variants
    'location': 'location',
    'locations': 'location',
    'site': 'location',
    'sites': 'location',
    'office': 'location',
    'offices': 'location',
    
    # Job variants
    'job': 'job',
    'jobs': 'job',
    'position': 'job',
    'positions': 'job',
    'role': 'job',
    'roles': 'job',
    'title': 'job',
    'titles': 'job',
}


# =============================================================================
# TERM INDEX CLASS
# =============================================================================

class TermIndex:
    """
    Manages the term index for deterministic query resolution.
    
    Usage:
        index = TermIndex(conn, project)
        
        # During column profiling:
        index.build_location_terms(table_name, column_name, distinct_values)
        index.build_status_terms(table_name, column_name, distinct_values)
        
        # During lookup detection:
        index.build_lookup_terms(table_name, code_column, lookup_data, lookup_type)
        
        # At query time:
        matches = index.resolve_terms(['texas', '401k'])
        join_path = index.get_join_path('Personal', 'Deductions')
    """
    
    def __init__(self, conn: duckdb.DuckDBPyConnection, project: str):
        self.conn = conn
        original_project = project
        self.project = project.lower() if project else 'default'  # Normalize to lowercase
        if original_project != self.project:
            logger.warning(f"[TERM_INDEX] Project normalized: '{original_project}' → '{self.project}'")
        self._ensure_tables()
    
    def _ensure_tables(self):
        """Create term index tables if they don't exist."""
        
        # Term Index table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS _term_index (
                project VARCHAR NOT NULL,
                term VARCHAR NOT NULL,
                term_type VARCHAR NOT NULL,
                table_name VARCHAR NOT NULL,
                column_name VARCHAR NOT NULL,
                operator VARCHAR DEFAULT '=',
                match_value VARCHAR,
                domain VARCHAR,
                entity VARCHAR,
                confidence FLOAT DEFAULT 1.0,
                source VARCHAR,
                vendor VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                PRIMARY KEY (project, term, table_name, column_name, match_value)
            )
        """)
        
        # Create indexes for fast lookup
        try:
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_term_lookup ON _term_index(project, term)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_term_domain ON _term_index(project, domain)")
        except Exception as e:
            logger.debug(f"Index creation note: {e}")
        
        # Entity Tables table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS _entity_tables (
                project VARCHAR NOT NULL,
                entity VARCHAR NOT NULL,
                table_name VARCHAR NOT NULL,
                is_primary BOOLEAN DEFAULT FALSE,
                table_type VARCHAR,
                row_count INTEGER,
                vendor VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                PRIMARY KEY (project, entity, table_name)
            )
        """)
        
        try:
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_entity_primary ON _entity_tables(project, entity, is_primary)")
        except Exception as e:
            logger.debug(f"Index creation note: {e}")
        
        # Add join_priority to _column_mappings if it doesn't exist
        try:
            cols = self.conn.execute("PRAGMA table_info(_column_mappings)").fetchall()
            col_names = [c[1] for c in cols]
            
            if 'join_priority' not in col_names:
                logger.info("[TERM_INDEX] Adding join_priority column to _column_mappings")
                self.conn.execute("ALTER TABLE _column_mappings ADD COLUMN join_priority INTEGER DEFAULT 50")
                self.conn.commit()
        except Exception as e:
            logger.debug(f"Migration note: {e}")
    
    # =========================================================================
    # TERM POPULATION METHODS
    # =========================================================================
    
    def add_term(
        self,
        term: str,
        term_type: str,
        table_name: str,
        column_name: str,
        operator: str = '=',
        match_value: str = None,
        domain: str = None,
        entity: str = None,
        confidence: float = 1.0,
        source: str = None,
        vendor: str = None
    ) -> bool:
        """Add a single term to the index."""
        try:
            # Normalize term
            term_lower = term.lower().strip()
            if not term_lower or term_lower in STOP_WORDS:
                return False
            
            # Skip very short terms that might cause false matches
            if len(term_lower) < 2:
                return False
            
            self.conn.execute("""
                INSERT INTO _term_index 
                (project, term, term_type, table_name, column_name, operator, match_value, domain, entity, confidence, source, vendor)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (project, term, table_name, column_name, match_value) DO UPDATE SET
                    confidence = CASE WHEN EXCLUDED.confidence > _term_index.confidence THEN EXCLUDED.confidence ELSE _term_index.confidence END
            """, [
                self.project, term_lower, term_type, table_name, column_name,
                operator, match_value or term, domain, entity, confidence, source, vendor
            ])
            return True
        except Exception as e:
            logger.warning(f"[TERM_INDEX] Term add failed for '{term}': {e}")
            return False
    
    def build_location_terms(
        self,
        table_name: str,
        column_name: str,
        distinct_values: List[Any],
        domain: str = None
    ) -> int:
        """
        Build term index entries for location columns.
        
        Detects US state codes and adds synonyms (e.g., "TX" → "texas").
        Returns count of terms added.
        """
        added = 0
        
        if not distinct_values:
            return 0
        
        # Convert to strings
        values = [str(v).strip() for v in distinct_values if v is not None and str(v).strip()]
        
        for v in values:
            # Direct value (always add)
            if self.add_term(v, 'value', table_name, column_name, '=', v, domain, 'location'):
                added += 1
            
            # Check if it's a state code
            v_upper = v.upper()
            if v_upper in STATE_SYNONYMS:
                # Add synonyms for this state code
                for synonym in STATE_SYNONYMS[v_upper]:
                    if self.add_term(synonym, 'synonym', table_name, column_name, '=', v_upper, 
                                    domain, 'location', confidence=0.95, source='state_name'):
                        added += 1
        
        logger.info(f"[TERM_INDEX] Built {added} location terms for {table_name}.{column_name}")
        return added
    
    def build_status_terms(
        self,
        table_name: str,
        column_name: str,
        distinct_values: List[Any],
        domain: str = None
    ) -> int:
        """
        Build term index entries for status columns.
        
        Adds synonyms for common status values (e.g., "A" → "active").
        Returns count of terms added.
        """
        added = 0
        
        if not distinct_values:
            return 0
        
        values = [str(v).strip() for v in distinct_values if v is not None and str(v).strip()]
        
        for v in values:
            # Direct value
            if self.add_term(v, 'value', table_name, column_name, '=', v, domain, 'status'):
                added += 1
            
            # Check for synonyms
            v_upper = v.upper()
            if v_upper in STATUS_SYNONYMS:
                for synonym in STATUS_SYNONYMS[v_upper]:
                    if self.add_term(synonym, 'synonym', table_name, column_name, '=', v,
                                    domain, 'status', confidence=0.95, source='status_word'):
                        added += 1
        
        logger.info(f"[TERM_INDEX] Built {added} status terms for {table_name}.{column_name}")
        return added
    
    def build_lookup_terms(
        self,
        table_name: str,
        code_column: str,
        lookup_data: Dict[str, str],
        lookup_type: str,
        domain: str = None
    ) -> int:
        """
        Build term index from code/description lookups.
        
        For a lookup like {"MED": "Medical Insurance"}, adds:
        - "medical insurance" → MED
        - "medical" → MED (partial, lower confidence)
        
        Returns count of terms added.
        """
        added = 0
        
        if not lookup_data:
            return 0
        
        for code, description in lookup_data.items():
            if not description:
                continue
            
            # Full description → code
            desc_lower = str(description).lower().strip()
            if self.add_term(desc_lower, 'lookup', table_name, code_column, '=', code,
                            domain, lookup_type, confidence=1.0, source=f'lookup:{lookup_type}'):
                added += 1
            
            # For multi-word descriptions, add significant individual words
            words = desc_lower.split()
            if len(words) > 1:
                for word in words:
                    # Skip short/common words
                    if len(word) > 3 and word not in STOP_WORDS:
                        if self.add_term(word, 'lookup_partial', table_name, code_column, 
                                        'ILIKE', f'%{code}%', domain, lookup_type,
                                        confidence=0.7, source=f'lookup:{lookup_type}'):
                            added += 1
        
        logger.info(f"[TERM_INDEX] Built {added} lookup terms for {table_name}.{code_column} ({lookup_type})")
        return added
    
    def build_value_terms(
        self,
        table_name: str,
        column_name: str,
        distinct_values: List[Any],
        domain: str = None,
        entity: str = None
    ) -> int:
        """
        Build generic term index entries for any categorical column.
        
        Simply indexes the actual values for exact match lookup.
        Returns count of terms added.
        """
        added = 0
        
        if not distinct_values:
            return 0
        
        for v in distinct_values:
            if v is None:
                continue
            v_str = str(v).strip()
            if v_str and len(v_str) >= 2:
                if self.add_term(v_str, 'value', table_name, column_name, '=', v_str, domain, entity):
                    added += 1
        
        return added
    
    # =========================================================================
    # JOIN PRIORITY METHODS
    # =========================================================================
    
    def set_join_priority(self, table_name: str, column_name: str, semantic_type: str):
        """
        Set join priority for a column based on its semantic type.
        
        Higher priority columns are preferred for JOINs.
        """
        priority = JOIN_PRIORITY_MAP.get(semantic_type.lower(), 50)
        
        try:
            self.conn.execute("""
                UPDATE _column_mappings 
                SET join_priority = ?
                WHERE project = ? AND table_name = ? AND original_column = ?
            """, [priority, self.project, table_name, column_name])
            
            logger.debug(f"[TERM_INDEX] Set join_priority={priority} for {table_name}.{column_name} ({semantic_type})")
        except Exception as e:
            logger.debug(f"Join priority update note: {e}")
    
    def set_all_join_priorities(self):
        """
        Set join priorities for all columns based on their semantic types.
        
        Call this after column mapping is complete.
        """
        try:
            # Get all mappings for this project
            mappings = self.conn.execute("""
                SELECT table_name, original_column, semantic_type
                FROM _column_mappings
                WHERE project = ?
            """, [self.project]).fetchall()
            
            updated = 0
            for table_name, column_name, semantic_type in mappings:
                if semantic_type:
                    priority = JOIN_PRIORITY_MAP.get(semantic_type.lower(), 50)
                    self.conn.execute("""
                        UPDATE _column_mappings 
                        SET join_priority = ?
                        WHERE project = ? AND table_name = ? AND original_column = ?
                    """, [priority, self.project, table_name, column_name])
                    updated += 1
            
            self.conn.commit()
            logger.info(f"[TERM_INDEX] Updated join priorities for {updated} columns")
            return updated
        except Exception as e:
            logger.error(f"Error setting join priorities: {e}")
            return 0
    
    # =========================================================================
    # ENTITY TABLE METHODS
    # =========================================================================
    
    def add_entity_table(
        self,
        entity: str,
        table_name: str,
        is_primary: bool = False,
        table_type: str = None,
        row_count: int = None,
        vendor: str = None
    ):
        """Add a table to the entity index."""
        try:
            self.conn.execute("""
                INSERT INTO _entity_tables 
                (project, entity, table_name, is_primary, table_type, row_count, vendor)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (project, entity, table_name) DO UPDATE SET
                    is_primary = EXCLUDED.is_primary,
                    table_type = EXCLUDED.table_type,
                    row_count = EXCLUDED.row_count,
                    vendor = EXCLUDED.vendor
            """, [self.project, entity.lower(), table_name, is_primary, table_type, row_count, vendor])
        except Exception as e:
            logger.debug(f"Entity table add note: {e}")
    
    def build_entity_tables(self, classifications: List[Dict]) -> int:
        """
        Build entity tables from table classifications.
        
        Now maps domains to canonical entities using DOMAIN_TO_ENTITY.
        For example, domain "hr" creates entity mappings for both "hr" AND "employee".
        
        Args:
            classifications: List of dicts with table_name, table_type, domain, row_count
            
        Returns:
            Count of entity-table mappings added.
        """
        added = 0
        
        # Group by domain to find primaries
        domain_tables: Dict[str, List[Dict]] = {}
        for c in classifications:
            domain = c.get('domain', 'unknown')
            if domain not in domain_tables:
                domain_tables[domain] = []
            domain_tables[domain].append(c)
        
        for domain, tables in domain_tables.items():
            # Sort by row count (largest = primary)
            tables_sorted = sorted(tables, key=lambda x: x.get('row_count', 0), reverse=True)
            
            # Get canonical entity for this domain
            canonical_entity = DOMAIN_TO_ENTITY.get(domain.lower(), domain)
            
            # Build set of entity names to store (both raw domain and canonical)
            entities_to_store = {domain.lower()}
            if canonical_entity != domain.lower():
                entities_to_store.add(canonical_entity)
            
            for i, t in enumerate(tables_sorted):
                is_primary = (i == 0)  # First (largest) is primary
                
                # Store under each entity name
                for entity_name in entities_to_store:
                    self.add_entity_table(
                        entity=entity_name,
                        table_name=t['table_name'],
                        is_primary=is_primary,
                        table_type=t.get('table_type'),
                        row_count=t.get('row_count')
                    )
                    added += 1
        
        logger.info(f"[TERM_INDEX] Built {added} entity-table mappings across {len(domain_tables)} domains")
        return added
    
    def resolve_entity(self, term: str) -> Optional[str]:
        """
        Resolve a user term to a canonical entity name.
        
        Args:
            term: User's query term (e.g., "employees", "401k", "workers")
            
        Returns:
            Canonical entity name or None if not an entity term.
        """
        term_lower = term.lower().strip()
        return ENTITY_SYNONYMS.get(term_lower)
    
    def detect_entities_in_query(self, terms: List[str]) -> Set[str]:
        """
        Detect all entities mentioned in a query.
        
        Args:
            terms: List of terms from the query
            
        Returns:
            Set of canonical entity names detected.
        """
        entities = set()
        for term in terms:
            entity = self.resolve_entity(term)
            if entity:
                entities.add(entity)
        return entities
    
    # =========================================================================
    # QUERY-TIME METHODS
    # =========================================================================
    
    def resolve_terms(self, terms: List[str]) -> List[TermMatch]:
        """
        Resolve a list of terms to SQL filter information.
        
        TWO-LAYER RESOLUTION:
        1. Fast path: Look up in term_index (O(1) for known terms)
        2. Fallback: MetadataReasoner for unknown terms (queries existing metadata)
        
        Args:
            terms: List of terms from the user's question (e.g., ['texas', '401k'])
            
        Returns:
            List of TermMatch objects with table/column/filter info.
        """
        matches = []
        unresolved_terms = []
        
        # Domain indicator words - these indicate WHAT to query, not filter values
        # "employees in Texas" → "employees" is the domain, "Texas" is the filter
        DOMAIN_INDICATOR_WORDS = {
            'employee', 'employees', 'worker', 'workers', 'staff', 'personnel',
            'person', 'people', 'individual', 'individuals',
            'show', 'list', 'find', 'get', 'display', 'count', 'total',
            'data', 'information', 'records', 'entries',
        }
        
        # DIAGNOSTIC: Show project and total term count
        try:
            total_count = self.conn.execute(
                "SELECT COUNT(*) FROM _term_index WHERE project = ?", [self.project]
            ).fetchone()[0]
            all_projects = self.conn.execute(
                "SELECT DISTINCT project FROM _term_index"
            ).fetchall()
            logger.warning(f"[TERM_INDEX] resolve_terms: project='{self.project}', total_terms={total_count}, all_projects={[p[0] for p in all_projects]}")
        except Exception as diag_err:
            logger.warning(f"[TERM_INDEX] Diagnostic failed: {diag_err}")
        
        logger.warning(f"[TERM_INDEX] resolve_terms called with {len(terms)} terms: {terms[:10]}")
        
        # LAYER 1: Fast path - term_index lookup
        for term in terms:
            term_lower = term.lower().strip()
            
            # Skip stop words
            if term_lower in STOP_WORDS or len(term_lower) < 2:
                logger.warning(f"[TERM_INDEX] Skipping term '{term_lower}' (stop word or too short)")
                continue
            
            # Skip domain indicator words - they indicate the domain, not a filter value
            if term_lower in DOMAIN_INDICATOR_WORDS:
                logger.warning(f"[TERM_INDEX] Skipping domain indicator word '{term_lower}'")
                continue
            
            # Look up in term index
            results = self.conn.execute("""
                SELECT term, table_name, column_name, operator, match_value, 
                       domain, entity, confidence, term_type
                FROM _term_index
                WHERE project = ? AND term = ?
                ORDER BY confidence DESC
            """, [self.project, term_lower]).fetchall()
            
            if results:
                logger.warning(f"[TERM_INDEX] Term '{term_lower}' found {len(results)} matches (fast path)")
                for row in results:
                    matches.append(TermMatch(
                        term=row[0],
                        table_name=row[1],
                        column_name=row[2],
                        operator=row[3],
                        match_value=row[4],
                        domain=row[5],
                        entity=row[6],
                        confidence=row[7],
                        term_type=row[8]
                    ))
            else:
                # Term not found - add to unresolved list
                unresolved_terms.append(term_lower)
                logger.warning(f"[TERM_INDEX] Term '{term_lower}' NOT in index - will try reasoner")
        
        # LAYER 2: Fallback - MetadataReasoner for unresolved terms
        if unresolved_terms:
            logger.warning(f"[TERM_INDEX] {len(unresolved_terms)} unresolved terms, invoking MetadataReasoner")
            try:
                from .metadata_reasoner import MetadataReasoner
                
                # Infer context domain from matches we already have
                context_domain = None
                if matches:
                    domains = [m.domain for m in matches if m.domain]
                    if domains:
                        context_domain = domains[0]
                
                reasoner = MetadataReasoner(self.conn, self.project)
                
                for term in unresolved_terms:
                    reasoned_matches = reasoner.resolve_unknown_term(term, context_domain)
                    
                    if reasoned_matches:
                        logger.warning(f"[TERM_INDEX] Reasoner found {len(reasoned_matches)} matches for '{term}'")
                        for rm in reasoned_matches:
                            # Convert ReasonedMatch to TermMatch
                            matches.append(TermMatch(
                                term=rm.term,
                                table_name=rm.table_name,
                                column_name=rm.column_name,
                                operator=rm.operator,
                                match_value=rm.match_value,
                                domain=rm.domain,
                                entity=None,
                                confidence=rm.confidence,
                                term_type='reasoned'
                            ))
                    else:
                        logger.warning(f"[TERM_INDEX] Reasoner found no matches for '{term}'")
                        
            except ImportError as e:
                logger.warning(f"[TERM_INDEX] MetadataReasoner not available: {e}")
            except Exception as e:
                logger.error(f"[TERM_INDEX] MetadataReasoner error: {e}")
        
        logger.warning(f"[TERM_INDEX] resolve_terms returning {len(matches)} total matches")
        return matches
    
    # =========================================================================
    # EVOLUTION 3: NUMERIC EXPRESSION RESOLUTION
    # =========================================================================
    
    def resolve_numeric_expression(self, expression: str, context_domain: str = None, full_question: str = None) -> List[TermMatch]:
        """
        Resolve a numeric expression to SQL filter information.
        
        EVOLUTION 3: Handle queries like "salary above 50000", "rate between 20 and 40"
        
        Args:
            expression: Text that may contain a numeric expression (e.g., "above 75000")
            context_domain: Optional domain hint (e.g., 'earnings', 'employees')
            full_question: Optional full question for context (e.g., "annual_salary above 75000")
            
        Returns:
            List of TermMatch objects with numeric operators
        """
        if not HAS_VALUE_PARSER:
            logger.debug("[TERM_INDEX] Value parser not available for numeric resolution")
            return []
        
        # Parse the expression
        parsed = parse_numeric_expression(expression)
        if not parsed:
            return []
        
        logger.warning(f"[TERM_INDEX] Parsed numeric expression: {parsed.operator.value} {parsed.value}")
        
        # Find candidate numeric columns
        numeric_cols = self._find_numeric_columns(context_domain)
        if not numeric_cols:
            logger.warning("[TERM_INDEX] No numeric columns found for numeric expression")
            return []
        
        # Score each column based on name match with expression OR full question
        matches = []
        expression_lower = expression.lower()
        # Use full question for context matching if available
        context_text = (full_question or expression).lower()
        
        # Keywords in expression that might indicate column type
        for table_name, column_name in numeric_cols:
            col_lower = column_name.lower()
            score = 0.5  # Base score
            
            # Score based on keyword match - check BOTH expression AND full question context
            if 'salary' in context_text and 'salary' in col_lower:
                score = 1.0
            elif 'rate' in context_text and 'rate' in col_lower:
                score = 1.0
            elif 'pay' in context_text and ('pay' in col_lower or 'rate' in col_lower):
                score = 0.95
            elif 'hour' in context_text and ('hour' in col_lower or 'hrs' in col_lower):
                score = 1.0
            elif 'amount' in context_text and 'amount' in col_lower:
                score = 1.0
            elif 'earn' in context_text and ('earn' in col_lower or 'amount' in col_lower):
                score = 0.9
            elif 'wage' in context_text and ('wage' in col_lower or 'rate' in col_lower):
                score = 0.95
            elif 'annual' in context_text and 'annual' in col_lower:
                score = 0.95
            
            # If we found a strong match, add it
            if score >= 0.9:
                # Convert value_parser operator to SQL operator
                op_map = {
                    ComparisonOp.EQ: '=',
                    ComparisonOp.NE: '!=',
                    ComparisonOp.GT: '>',
                    ComparisonOp.GTE: '>=',
                    ComparisonOp.LT: '<',
                    ComparisonOp.LTE: '<=',
                    ComparisonOp.BETWEEN: 'BETWEEN',
                }
                sql_op = op_map.get(parsed.operator, '=')
                
                # Format match value
                if parsed.operator == ComparisonOp.BETWEEN and parsed.value_end:
                    match_value = f"{parsed.value}|{parsed.value_end}"
                else:
                    match_value = str(parsed.value)
                
                matches.append(TermMatch(
                    term=expression,
                    table_name=table_name,
                    column_name=column_name,
                    operator=sql_op,
                    match_value=match_value,
                    domain=context_domain,
                    entity=None,
                    confidence=score * parsed.confidence,
                    term_type='numeric'
                ))
                logger.warning(f"[TERM_INDEX] Numeric match: {table_name}.{column_name} {sql_op} {match_value}")
        
        # Sort by confidence and return top matches
        matches.sort(key=lambda m: -m.confidence)
        return matches[:3]  # Return top 3 numeric column matches
    
    def _find_numeric_columns(self, domain: str = None) -> List[Tuple[str, str]]:
        """
        Find numeric columns in the project, optionally filtered by domain.
        
        Returns:
            List of (table_name, column_name) tuples for numeric columns
        """
        # Known numeric column name patterns
        NUMERIC_PATTERNS = [
            '%amount%', '%rate%', '%salary%', '%wage%', '%pay%',
            '%hour%', '%hrs%', '%total%', '%sum%', '%count%',
            '%qty%', '%quantity%', '%price%', '%cost%', '%fee%',
            '%balance%', '%percent%', '%pct%'
        ]
        
        # Build query with LIKE conditions for column names
        like_conditions = ' OR '.join([f"LOWER(column_name) LIKE '{p}'" for p in NUMERIC_PATTERNS])
        
        query = f"""
            SELECT DISTINCT table_name, column_name
            FROM _column_profiles
            WHERE LOWER(project) = ?
              AND ({like_conditions})
              AND inferred_type = 'numeric'
        """
        params = [self.project]
        
        # If domain specified, filter by tables in that domain
        if domain:
            query += """
                AND table_name IN (
                    SELECT table_name FROM _table_classifications
                    WHERE project_name = ? AND domain = ?
                )
            """
            params.extend([self.project, domain])
        
        query += " ORDER BY table_name, column_name"
        
        try:
            results = self.conn.execute(query, params).fetchall()
            logger.debug(f"[TERM_INDEX] Found {len(results)} numeric columns" + (f" in domain '{domain}'" if domain else ""))
            return [(r[0], r[1]) for r in results]
        except Exception as e:
            logger.warning(f"[TERM_INDEX] Error finding numeric columns: {e}")
            return []
    
    def resolve_terms_enhanced(self, terms: List[str], detect_numeric: bool = True, full_question: str = None) -> List[TermMatch]:
        """
        Enhanced term resolution with numeric expression support.
        
        EVOLUTION 3: This is the new entry point that handles both
        categorical lookups (existing) and numeric expressions (new).
        
        Args:
            terms: List of terms/expressions from user's question
            detect_numeric: Whether to check for numeric expressions
            full_question: Optional full question text for context matching
            
        Returns:
            List of TermMatch objects
        """
        matches = []
        remaining_terms = []
        
        # Build full question from terms if not provided
        question_context = full_question or ' '.join(terms)
        
        # First pass: Check each term for numeric expressions
        if detect_numeric and HAS_VALUE_PARSER:
            for term in terms:
                # Try to parse as numeric expression - pass full question for context
                numeric_matches = self.resolve_numeric_expression(term, full_question=question_context)
                if numeric_matches:
                    matches.extend(numeric_matches)
                    logger.warning(f"[TERM_INDEX] Term '{term}' resolved as numeric expression")
                else:
                    remaining_terms.append(term)
        else:
            remaining_terms = terms
        
        # Second pass: Regular term resolution for remaining terms
        if remaining_terms:
            categorical_matches = self.resolve_terms(remaining_terms)
            matches.extend(categorical_matches)
        
        return matches
    
    def get_entity_tables(self, entity: str, primary_only: bool = False) -> List[str]:
        """
        Get tables for an entity.
        
        Args:
            entity: Entity name (e.g., 'employee', 'demographics')
            primary_only: If True, only return the primary table
            
        Returns:
            List of table names.
        """
        query = """
            SELECT table_name 
            FROM _entity_tables
            WHERE LOWER(project) = ? AND entity = ?
        """
        params = [self.project, entity.lower()]
        
        if primary_only:
            query += " AND is_primary = TRUE"
        
        query += " ORDER BY is_primary DESC, row_count DESC"
        
        results = self.conn.execute(query, params).fetchall()
        return [r[0] for r in results]
    
    def get_join_path(self, table1: str, table2: str) -> Optional[JoinPath]:
        """
        Get the best join path between two tables.
        
        Uses join_priority to select the best column pair.
        
        Args:
            table1: First table name
            table2: Second table name
            
        Returns:
            JoinPath object or None if no common key found.
        """
        try:
            result = self.conn.execute("""
                SELECT m1.original_column, m2.original_column, m1.semantic_type,
                       COALESCE(m1.join_priority, 50)
                FROM _column_mappings m1
                JOIN _column_mappings m2 ON m1.semantic_type = m2.semantic_type
                WHERE m1.project = ? AND m2.project = ?
                  AND m1.table_name = ? AND m2.table_name = ?
                  AND m1.table_name != m2.table_name
                ORDER BY COALESCE(m1.join_priority, 50) DESC
                LIMIT 1
            """, [self.project, self.project, table1, table2]).fetchone()
            
            if result:
                return JoinPath(
                    table1=table1,
                    column1=result[0],
                    table2=table2,
                    column2=result[1],
                    semantic_type=result[2],
                    priority=result[3]
                )
            return None
        except Exception as e:
            logger.error(f"Error getting join path: {e}")
            return None
    
    # =========================================================================
    # STATISTICS AND DEBUGGING
    # =========================================================================
    
    def get_stats(self) -> Dict:
        """Get statistics about the term index."""
        try:
            term_count = self.conn.execute(
                "SELECT COUNT(*) FROM _term_index WHERE project = ?", [self.project]
            ).fetchone()[0]
            
            entity_count = self.conn.execute(
                "SELECT COUNT(*) FROM _entity_tables WHERE project = ?", [self.project]
            ).fetchone()[0]
            
            term_types = self.conn.execute("""
                SELECT term_type, COUNT(*) 
                FROM _term_index 
                WHERE project = ?
                GROUP BY term_type
            """, [self.project]).fetchall()
            
            domains = self.conn.execute("""
                SELECT domain, COUNT(*) 
                FROM _term_index 
                WHERE project = ? AND domain IS NOT NULL
                GROUP BY domain
            """, [self.project]).fetchall()
            
            return {
                'total_terms': term_count,
                'total_entity_mappings': entity_count,
                'terms_by_type': {t[0]: t[1] for t in term_types},
                'terms_by_domain': {d[0]: d[1] for d in domains}
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}
    
    def clear(self):
        """Clear all term index data for this project."""
        self.conn.execute("DELETE FROM _term_index WHERE project = ?", [self.project])
        self.conn.execute("DELETE FROM _entity_tables WHERE project = ?", [self.project])
        self.conn.commit()
        logger.info(f"[TERM_INDEX] Cleared all data for project {self.project}")


# =============================================================================
# VENDOR SCHEMA LOADER
# =============================================================================

class VendorSchemaLoader:
    """
    Loads and provides access to vendor schema JSON files.
    
    These schemas define:
    - Hub definitions (entity types like 'employee', 'location')
    - Column patterns (how to detect columns by name)
    - Spoke patterns (relationships between entities)
    - Join keys (primary and alternate keys)
    """
    
    def __init__(self, config_path: str = None):
        """
        Initialize the vendor schema loader.
        
        Args:
            config_path: Path to config directory. Defaults to repo/config/
        """
        if config_path is None:
            # Try to find config directory relative to this file
            current_file = Path(__file__).resolve()
            # Go up from backend/utils/intelligence/ to repo root
            repo_root = current_file.parent.parent.parent.parent
            config_path = repo_root / 'config'
        
        self.config_path = Path(config_path)
        self._schemas: Dict[str, Dict] = {}
        self._unified_vocabulary: Dict = {}
    
    def load_vendor_schema(self, vendor: str) -> Optional[Dict]:
        """
        Load a specific vendor's schema.
        
        Args:
            vendor: Vendor name (e.g., 'ukg_pro', 'ukg_wfm', 'ukg_ready')
            
        Returns:
            Schema dict or None if not found.
        """
        if vendor in self._schemas:
            return self._schemas[vendor]
        
        # Map vendor names to file names
        file_map = {
            'ukg_pro': 'ukg_schema_reference.json',
            'ukg_wfm': 'ukg_wfm_dimensions_schema_v1.json',
            'ukg_wfm_dimensions': 'ukg_wfm_dimensions_schema_v1.json',
            'ukg_ready': 'ukg_ready_schema_v1.json',
        }
        
        filename = file_map.get(vendor.lower())
        if not filename:
            # Try direct file lookup
            filename = f"{vendor.lower()}_schema.json"
        
        schema_file = self.config_path / filename
        
        # Also check vendors subdirectory
        if not schema_file.exists():
            schema_file = self.config_path / 'vendors' / vendor.lower() / 'schema_reference.json'
        
        if schema_file.exists():
            try:
                with open(schema_file, 'r') as f:
                    self._schemas[vendor] = json.load(f)
                    logger.info(f"[VENDOR_SCHEMA] Loaded schema for {vendor} from {schema_file}")
                    return self._schemas[vendor]
            except Exception as e:
                logger.error(f"Error loading vendor schema {schema_file}: {e}")
        else:
            logger.debug(f"Vendor schema file not found: {schema_file}")
        
        return None
    
    def load_unified_vocabulary(self) -> Dict:
        """
        Load the unified vocabulary across all vendors.
        
        Returns:
            Unified vocabulary dict.
        """
        if self._unified_vocabulary:
            return self._unified_vocabulary
        
        vocab_file = self.config_path / 'ukg_vocabulary_seed.json'
        if not vocab_file.exists():
            vocab_file = self.config_path / 'ukg_family_unified_vocabulary.json'
        
        if vocab_file.exists():
            try:
                with open(vocab_file, 'r') as f:
                    self._unified_vocabulary = json.load(f)
                    logger.info(f"[VENDOR_SCHEMA] Loaded unified vocabulary from {vocab_file}")
                    return self._unified_vocabulary
            except Exception as e:
                logger.error(f"Error loading unified vocabulary: {e}")
        
        return {}
    
    def get_hub_definitions(self, vendor: str = None) -> Dict:
        """
        Get hub definitions from vendor schema or unified vocabulary.
        
        Args:
            vendor: Specific vendor, or None for unified
            
        Returns:
            Dict of hub_name -> hub_definition
        """
        if vendor:
            schema = self.load_vendor_schema(vendor)
            if schema and 'hubs' in schema:
                return schema['hubs']
        
        # Fall back to unified vocabulary
        vocab = self.load_unified_vocabulary()
        return vocab.get('hubs', vocab.get('concepts', {}))
    
    def get_column_patterns(self, vendor: str = None) -> Dict[str, List[str]]:
        """
        Get column patterns for semantic type detection.
        
        Args:
            vendor: Specific vendor, or None for unified
            
        Returns:
            Dict of semantic_type -> [column_patterns]
        """
        patterns = {}
        
        hubs = self.get_hub_definitions(vendor)
        for hub_name, hub_def in hubs.items():
            if isinstance(hub_def, dict):
                semantic_type = hub_def.get('semantic_type', hub_name)
                col_patterns = hub_def.get('column_patterns', [])
                if col_patterns:
                    patterns[semantic_type] = col_patterns
        
        return patterns
    
    def get_spoke_patterns(self, vendor: str = None) -> List[Dict]:
        """
        Get spoke patterns (relationships) from vendor schema.
        
        Args:
            vendor: Specific vendor, or None for unified
            
        Returns:
            List of spoke pattern dicts.
        """
        if vendor:
            schema = self.load_vendor_schema(vendor)
            if schema:
                return schema.get('spoke_patterns', schema.get('spokes', []))
        
        # Try unified vocabulary
        vocab = self.load_unified_vocabulary()
        return vocab.get('spoke_patterns', vocab.get('relationships', []))
    
    def get_join_keys(self, vendor: str = None) -> Dict:
        """
        Get join key definitions from vendor schema.
        
        Args:
            vendor: Specific vendor, or None for unified
            
        Returns:
            Dict with 'primary' and 'alternates' lists.
        """
        if vendor:
            schema = self.load_vendor_schema(vendor)
            if schema and 'join_keys' in schema:
                return schema['join_keys']
        
        # Default join keys
        return {
            'primary': ['employee_number', 'company_code', 'cocode', 'empno'],
            'alternates': ['ssn', 'national_id', 'employee_id']
        }


# =============================================================================
# RECALC FUNCTIONS
# =============================================================================

def recalc_term_index(conn: duckdb.DuckDBPyConnection, project: str) -> Dict:
    """
    Recalculate the term index for a project without re-uploading files.
    
    This reads existing column profiles and rebuilds the term index.
    
    Args:
        conn: DuckDB connection
        project: Project ID
        
    Returns:
        Dict with recalc statistics.
    """
    index = TermIndex(conn, project)
    
    # Clear existing terms
    index.clear()
    
    stats = {
        'location_terms': 0,
        'status_terms': 0,
        'lookup_terms': 0,
        'entity_mappings': 0,
        'join_priorities': 0,
        'profiles_found': 0,
        'profiles_with_values': 0,
        'location_columns': 0,
        'status_columns': 0,
        'state_columns_fallback': 0,  # NEW: Track fallback detection
        'sample_values': []
    }
    
    # Rebuild from column profiles (primary path)
    try:
        profiles = conn.execute("""
            SELECT table_name, column_name, filter_category, distinct_values
            FROM _column_profiles
            WHERE project = ? AND filter_category IS NOT NULL
        """, [project]).fetchall()
        
        stats['profiles_found'] = len(profiles)
        logger.info(f"[TERM_INDEX] Found {len(profiles)} profiles with filter_category")
        
        for table_name, column_name, category, values_json in profiles:
            if not values_json:
                continue
            
            stats['profiles_with_values'] += 1
            
            try:
                values = json.loads(values_json) if isinstance(values_json, str) else values_json
            except Exception as parse_e:
                logger.warning(f"[TERM_INDEX] Failed to parse values for {table_name}.{column_name}: {parse_e}")
                continue
            
            if category == 'location':
                stats['location_columns'] += 1
                # Sample first location column values for debugging
                if not stats['sample_values'] and values:
                    stats['sample_values'] = values[:5] if isinstance(values, list) else [str(values)[:100]]
                terms_added = index.build_location_terms(table_name, column_name, values)
                stats['location_terms'] += terms_added
                logger.info(f"[TERM_INDEX] Location {table_name}.{column_name}: {len(values) if isinstance(values, list) else 1} values → {terms_added} terms")
            elif category == 'status':
                stats['status_columns'] += 1
                terms_added = index.build_status_terms(table_name, column_name, values)
                stats['status_terms'] += terms_added
                logger.info(f"[TERM_INDEX] Status {table_name}.{column_name}: {len(values) if isinstance(values, list) else 1} values → {terms_added} terms")
    except Exception as e:
        logger.error(f"Error rebuilding terms from profiles: {e}")
        stats['error'] = str(e)
    
    # FALLBACK: Detect state columns that weren't categorized as 'location'
    # This catches columns with 'state' or 'province' in the name that have state codes
    try:
        state_columns = conn.execute("""
            SELECT table_name, column_name, distinct_values
            FROM _column_profiles
            WHERE project = ? 
              AND filter_category IS NULL
              AND (LOWER(column_name) LIKE '%state%' OR LOWER(column_name) LIKE '%province%')
              AND distinct_count > 0 AND distinct_count <= 100
              AND distinct_values IS NOT NULL
        """, [project]).fetchall()
        
        for table_name, column_name, values_json in state_columns:
            if not values_json:
                continue
            try:
                values = json.loads(values_json) if isinstance(values_json, str) else values_json
                if not values:
                    continue
                    
                # Check if values look like state codes (mostly 2-char strings)
                str_values = [str(v).strip().upper() for v in values if v]
                state_like = sum(1 for v in str_values if len(v) == 2 and v.isalpha())
                
                if state_like >= len(str_values) * 0.5:  # At least 50% look like state codes
                    terms_added = index.build_location_terms(table_name, column_name, values)
                    stats['state_columns_fallback'] += 1
                    stats['location_terms'] += terms_added
                    logger.warning(f"[TERM_INDEX] FALLBACK state column {table_name}.{column_name}: {len(values)} values → {terms_added} terms")
            except Exception as e:
                logger.debug(f"Error processing fallback state column: {e}")
                
        if stats['state_columns_fallback'] > 0:
            logger.warning(f"[TERM_INDEX] Fallback detected {stats['state_columns_fallback']} state columns")
    except Exception as e:
        logger.debug(f"State column fallback query failed: {e}")
    
    # Rebuild from lookups
    try:
        lookups = conn.execute("""
            SELECT table_name, code_column, lookup_type, lookup_data_json
            FROM _intelligence_lookups
            WHERE project_name = ?
        """, [project]).fetchall()
        
        for table_name, code_column, lookup_type, lookup_json in lookups:
            if not lookup_json:
                continue
            
            try:
                lookup_data = json.loads(lookup_json) if isinstance(lookup_json, str) else lookup_json
                stats['lookup_terms'] += index.build_lookup_terms(table_name, code_column, lookup_data, lookup_type)
            except Exception as e:
                logger.debug(f"Error processing lookup: {e}")
        
        stats['lookups_found'] = len(lookups)
        logger.info(f"[TERM_INDEX] Loaded {len(lookups)} lookups from _intelligence_lookups")
    except Exception as e:
        logger.debug(f"Lookup table may not exist: {e}")
        stats['lookups_found'] = 0
    
    # Rebuild entity tables
    try:
        classifications = conn.execute("""
            SELECT table_name, table_type, domain, row_count
            FROM _table_classifications
            WHERE project_name = ?
        """, [project]).fetchall()
        
        class_list = [
            {'table_name': c[0], 'table_type': c[1], 'domain': c[2], 'row_count': c[3]}
            for c in classifications
        ]
        stats['classifications_found'] = len(classifications)
        stats['entity_mappings'] = index.build_entity_tables(class_list)
        logger.info(f"[TERM_INDEX] Loaded {len(classifications)} classifications from _table_classifications")
    except Exception as e:
        logger.debug(f"Classification table may not exist: {e}")
        stats['classifications_found'] = 0
    
    # Set join priorities
    stats['join_priorities'] = index.set_all_join_priorities()
    
    conn.commit()
    
    logger.info(f"[TERM_INDEX] Recalc complete: {stats}")
    return stats
