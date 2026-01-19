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

logger = logging.getLogger(__name__)

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

# Phase 5: Multi-product vocabulary support
try:
    from backend.utils.products import (
        get_vocabulary_normalizer,
        normalize_term as vocab_normalize_term,
        get_domain_for_term,
        DOMAIN_TO_PRIMARY_ENTITY,
    )
    HAS_VOCABULARY = True
    logger.info("[TERM_INDEX] ✅ Multi-product vocabulary available")
except ImportError:
    HAS_VOCABULARY = False

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
    term_type: str = 'value'  # 'value', 'synonym', 'pattern', 'lookup', 'concept'
    source: Optional[str] = None  # 'vocabulary', 'filter_category', 'inferred', etc.


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
    # Question modifiers - NEVER filter on these
    'many', 'much', 'any', 'every',
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
            # Phase 5: Try vocabulary system first
            canonical_entity = None
            if HAS_VOCABULARY:
                try:
                    canonical_entity = DOMAIN_TO_PRIMARY_ENTITY.get(domain)
                except Exception:
                    pass
            
            # Fallback to hardcoded mapping
            if not canonical_entity:
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
        
        Now uses multi-product vocabulary system (Phase 5) with fallback
        to hardcoded ENTITY_SYNONYMS for backward compatibility.
        
        Args:
            term: User's query term (e.g., "employees", "401k", "workers")
            
        Returns:
            Canonical entity name or None if not an entity term.
        """
        term_lower = term.lower().strip()
        
        # Phase 5: Try vocabulary normalizer first (multi-product support)
        if HAS_VOCABULARY:
            try:
                canonical = vocab_normalize_term(term_lower)
                if canonical:
                    return canonical
            except Exception:
                pass  # Fall through to hardcoded
        
        # Fallback to hardcoded synonyms
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
            
            # Domain indicator words - resolve to find target table but mark as domain context
            is_domain_indicator = term_lower in DOMAIN_INDICATOR_WORDS
            
            # Look up in term index
            results = self.conn.execute("""
                SELECT term, table_name, column_name, operator, match_value, 
                       domain, entity, confidence, term_type, source
                FROM _term_index
                WHERE project = ? AND term = ?
                ORDER BY confidence DESC
            """, [self.project, term_lower]).fetchall()
            
            if results:
                logger.warning(f"[TERM_INDEX] Term '{term_lower}' found {len(results)} matches (fast path), is_domain_indicator={is_domain_indicator}")
                for row in results:
                    term_type = row[8]
                    # For domain indicators, only use 'concept' type entries (table identification)
                    # Skip 'lookup' and 'lookup_partial' (filter values)
                    if is_domain_indicator and term_type not in ('concept', 'synonym'):
                        logger.warning(f"[TERM_INDEX] Skipping non-concept match for domain indicator '{term_lower}': type={term_type}")
                        continue
                    matches.append(TermMatch(
                        term=row[0],
                        table_name=row[1],
                        column_name=row[2],
                        operator=row[3],
                        match_value=row[4],
                        domain=row[5],
                        entity=row[6],
                        confidence=row[7],
                        term_type=term_type,
                        source=row[9] if len(row) > 9 else None
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
            '%balance%', '%percent%', '%pct%', '%annual%'
        ]
        
        # Build query with LIKE conditions for column names
        like_conditions = ' OR '.join([f"LOWER(column_name) LIKE '{p}'" for p in NUMERIC_PATTERNS])
        
        # Accept multiple numeric types
        query = f"""
            SELECT DISTINCT table_name, column_name
            FROM _column_profiles
            WHERE LOWER(project) = ?
              AND ({like_conditions})
              AND inferred_type IN ('numeric', 'integer', 'float', 'decimal')
        """
        params = [self.project]
        
        # If domain specified, filter by tables in that domain
        if domain:
            query += """
                AND table_name IN (
                    SELECT table_name FROM _table_classifications
                    WHERE LOWER(project_name) = LOWER(?) AND domain = ?
                )
            """
            params.extend([self.project, domain])
        
        query += " ORDER BY table_name, column_name"
        
        try:
            results = self.conn.execute(query, params).fetchall()
            logger.warning(f"[TERM_INDEX] Found {len(results)} numeric columns" + (f" in domain '{domain}'" if domain else " (all domains)"))
            return [(r[0], r[1]) for r in results]
        except Exception as e:
            logger.warning(f"[TERM_INDEX] Error finding numeric columns: {e}")
            return []
    
    def resolve_aggregation_target(self, term: str, domain: str = None) -> List[TermMatch]:
        """
        Resolve a term to a numeric column for aggregation.
        
        EVOLUTION 7: Find numeric columns that match the aggregation target.
        Example: "salary" → annual_salary column
        
        Args:
            term: The aggregation target term (e.g., "salary", "rate", "hours")
            domain: Optional domain to filter by (will fallback to all if no matches found)
            
        Returns:
            List of TermMatch objects for matching numeric columns
        """
        term_lower = term.lower().strip()
        
        def find_matches(columns):
            """Find columns that match the term."""
            matches = []
            for table_name, column_name in columns:
                col_lower = column_name.lower()
                
                # Score based on how well the term matches the column name
                score = 0.0
                
                # Exact match
                if term_lower == col_lower:
                    score = 1.0
                # Term is part of column name (e.g., "salary" in "annual_salary")
                elif term_lower in col_lower:
                    score = 0.9
                # Column name ends/starts with term
                elif col_lower.endswith(term_lower) or col_lower.startswith(term_lower):
                    score = 0.85
                
                if score > 0.5:
                    matches.append(TermMatch(
                        term=term,
                        table_name=table_name,
                        column_name=column_name,
                        operator='AGG',  # Special operator for aggregation
                        match_value=column_name,
                        domain=domain,
                        entity=None,
                        confidence=score,
                        term_type='aggregation_target'
                    ))
                    logger.warning(f"[TERM_INDEX] Aggregation target: '{term}' → {table_name}.{column_name} (score={score:.2f})")
            return matches
        
        # Try domain-filtered first
        if domain:
            numeric_columns = self._find_numeric_columns(domain)
            logger.warning(f"[TERM_INDEX] Found {len(numeric_columns)} numeric columns in domain '{domain}'")
            matches = find_matches(numeric_columns)
            
            if matches:
                matches.sort(key=lambda m: -m.confidence)
                return matches[:5]
            else:
                logger.warning(f"[TERM_INDEX] No matches for '{term}' in domain '{domain}', trying all domains")
        
        # Fallback: try all domains
        numeric_columns = self._find_numeric_columns(None)
        logger.warning(f"[TERM_INDEX] Found {len(numeric_columns)} numeric columns (all domains)")
        matches = find_matches(numeric_columns)
        
        if not matches:
            logger.warning(f"[TERM_INDEX] No aggregation target found for '{term}'")
            return []
        
        # Sort by score and return top matches
        matches.sort(key=lambda m: -m.confidence)
        return matches[:5]
    
    # =========================================================================
    # EVOLUTION 4: DATE/TIME FILTERS
    # =========================================================================
    
    def _find_date_columns(self, domain: str = None) -> List[Tuple[str, str]]:
        """
        Find date columns in the project, optionally filtered by domain.
        
        EVOLUTION 4: Finds columns that are either:
        - Profiled as 'date' type
        - Have date-like names (hire, term, birth, effective, etc.)
        
        Returns:
            List of (table_name, column_name) tuples for date columns
        """
        query = """
            SELECT DISTINCT table_name, column_name
            FROM _column_profiles
            WHERE LOWER(project) = ?
              AND inferred_type = 'date'
        """
        params = [self.project]
        
        # If domain specified, filter by tables in that domain
        if domain:
            query += """
                AND table_name IN (
                    SELECT table_name FROM _table_classifications
                    WHERE LOWER(project_name) = ? AND domain = ?
                )
            """
            params.extend([self.project, domain])
        
        query += " ORDER BY table_name, column_name"
        
        try:
            results = self.conn.execute(query, params).fetchall()
            logger.debug(f"[TERM_INDEX] Found {len(results)} date columns" + (f" in domain '{domain}'" if domain else ""))
            return [(r[0], r[1]) for r in results]
        except Exception as e:
            logger.warning(f"[TERM_INDEX] Error finding date columns: {e}")
            return []
    
    def resolve_date_expression(self, expression: str, context_domain: str = None, full_question: str = None) -> List[TermMatch]:
        """
        Resolve a date expression to SQL filter information.
        
        EVOLUTION 4: Handle queries like "hired last year", "terminated in 2024"
        
        Args:
            expression: Text that may contain a date expression (e.g., "last year", "in 2024")
            context_domain: Optional domain hint
            full_question: Optional full question for context (e.g., "employees hired last year")
            
        Returns:
            List of TermMatch objects with date operators
        """
        if not HAS_VALUE_PARSER:
            logger.debug("[TERM_INDEX] Value parser not available for date resolution")
            return []
        
        # Parse the expression
        parsed = parse_date_expression(expression)
        if not parsed:
            return []
        
        logger.warning(f"[TERM_INDEX] Parsed date expression: {parsed.start_date} to {parsed.end_date} ({parsed.grain})")
        
        # Find candidate date columns
        date_cols = self._find_date_columns(context_domain)
        if not date_cols:
            logger.warning("[TERM_INDEX] No date columns found for date expression")
            return []
        
        # Score each column based on name match with full question context
        matches = []
        context_text = (full_question or expression).lower()
        
        # Keywords that indicate specific date column types
        for table_name, column_name in date_cols:
            col_lower = column_name.lower()
            score = 0.5  # Base score
            
            # Score based on keyword match in the full question
            if 'hire' in context_text and 'hire' in col_lower:
                score = 1.0
            elif 'hired' in context_text and 'hire' in col_lower:
                score = 1.0
            elif 'term' in context_text and 'term' in col_lower:
                score = 1.0
            elif 'terminated' in context_text and 'term' in col_lower:
                score = 1.0
            elif 'birth' in context_text and 'birth' in col_lower:
                score = 1.0
            elif 'born' in context_text and 'birth' in col_lower:
                score = 0.95
            elif 'start' in context_text and 'start' in col_lower:
                score = 1.0
            elif 'started' in context_text and 'start' in col_lower:
                score = 1.0
            elif 'end' in context_text and 'end' in col_lower:
                score = 1.0
            elif 'ended' in context_text and 'end' in col_lower:
                score = 1.0
            elif 'effective' in context_text and 'effective' in col_lower:
                score = 1.0
            elif 'review' in context_text and 'review' in col_lower:
                score = 0.95
            # Generic date column - lower score
            elif 'date' in col_lower:
                score = 0.6
            
            # If we found a decent match, add it
            if score >= 0.6:
                # Format as BETWEEN for date ranges
                match_value = f"{parsed.start_date}|{parsed.end_date}"
                
                matches.append(TermMatch(
                    term=expression,
                    table_name=table_name,
                    column_name=column_name,
                    operator='BETWEEN',
                    match_value=match_value,
                    domain=context_domain,
                    entity=None,
                    confidence=score * 0.95,  # Slightly lower than numeric since dates can be ambiguous
                    term_type='date'
                ))
                logger.warning(f"[TERM_INDEX] Date match: {table_name}.{column_name} BETWEEN {parsed.start_date} AND {parsed.end_date}")
        
        # Sort by confidence and return top matches
        matches.sort(key=lambda m: -m.confidence)
        return matches[:3]  # Return top 3 date column matches
    
    # =========================================================================
    # EVOLUTION 5: OR LOGIC
    # =========================================================================
    
    def resolve_or_expression(self, terms: List[str], full_question: str = None) -> List[TermMatch]:
        """
        Resolve an OR expression to a single IN clause.
        
        EVOLUTION 5: Handle queries like "Texas or California" → state IN ('TX', 'CA')
        
        Args:
            terms: List of terms in the OR group (e.g., ['texas', 'california'])
            full_question: Optional full question for context
            
        Returns:
            List of TermMatch objects with IN operator, grouped by column
        """
        if len(terms) < 2:
            return []
        
        # Resolve each term individually
        all_matches = []
        for term in terms:
            term_matches = self.resolve_terms([term])
            all_matches.extend(term_matches)
        
        if not all_matches:
            logger.warning(f"[TERM_INDEX] OR expression: no matches for terms {terms}")
            return []
        
        # Group by (table, column) to find common columns
        from collections import defaultdict
        groups = defaultdict(list)
        for match in all_matches:
            key = (match.table_name, match.column_name)
            groups[key].append(match)
        
        # Find groups that have matches for ALL terms (or at least 2)
        result_matches = []
        for (table_name, column_name), matches in groups.items():
            # Get unique values for this column
            values = list(set(m.match_value for m in matches))
            
            # Only create IN clause if we have multiple values
            if len(values) >= 2:
                # Combine into IN clause
                in_values = ', '.join(f"'{v}'" for v in values)
                avg_confidence = sum(m.confidence for m in matches) / len(matches)
                
                result_matches.append(TermMatch(
                    term=' or '.join(terms),
                    table_name=table_name,
                    column_name=column_name,
                    operator='IN',
                    match_value=in_values,
                    domain=matches[0].domain,
                    entity=matches[0].entity,
                    confidence=avg_confidence,
                    term_type='or_group'
                ))
                logger.warning(f"[TERM_INDEX] OR match: {table_name}.{column_name} IN ({in_values})")
        
        # Sort by confidence
        result_matches.sort(key=lambda m: -m.confidence)
        return result_matches
    
    # =========================================================================
    # EVOLUTION 6: NEGATION
    # =========================================================================
    
    def resolve_negation_expression(self, term: str, negation_type: str = 'not', full_question: str = None) -> List[TermMatch]:
        """
        Resolve a negation expression to a != or NOT IN clause.
        
        EVOLUTION 6: Handle queries like "not Texas" → state != 'TX'
        
        Args:
            term: The term being negated (e.g., 'texas', 'terminated')
            negation_type: Type of negation ('not', 'excluding', 'except', 'without')
            full_question: Optional full question for context
            
        Returns:
            List of TermMatch objects with != or NOT IN operator
        """
        # Resolve the term normally first
        term_matches = self.resolve_terms([term])
        
        if not term_matches:
            logger.warning(f"[TERM_INDEX] Negation: no matches for term '{term}'")
            return []
        
        # Convert each match to negated version
        negated_matches = []
        for match in term_matches:
            negated_matches.append(TermMatch(
                term=f"not {term}",
                table_name=match.table_name,
                column_name=match.column_name,
                operator='!=',
                match_value=match.match_value,
                domain=match.domain,
                entity=match.entity,
                confidence=match.confidence * 0.95,  # Slightly lower for negation
                term_type='negation'
            ))
            logger.warning(f"[TERM_INDEX] Negation match: {match.table_name}.{match.column_name} != '{match.match_value}'")
        
        return negated_matches
    
    def resolve_terms_enhanced(self, terms: List[str], detect_numeric: bool = True, detect_dates: bool = True, detect_or: bool = True, detect_negation: bool = True, full_question: str = None) -> List[TermMatch]:
        """
        Enhanced term resolution with numeric, date, OR, and negation expression support.
        
        EVOLUTION 3, 4, 5 & 6: This is the entry point that handles:
        - Categorical lookups (existing)
        - Numeric expressions (Evolution 3)
        - Date expressions (Evolution 4)
        - OR expressions (Evolution 5)
        - Negation expressions (Evolution 6)
        
        Args:
            terms: List of terms/expressions from user's question
            detect_numeric: Whether to check for numeric expressions
            detect_dates: Whether to check for date expressions
            detect_or: Whether to check for OR expressions
            detect_negation: Whether to check for negation expressions
            full_question: Optional full question text for context matching
            
        Returns:
            List of TermMatch objects
        """
        matches = []
        remaining_terms = []
        
        # Build full question from terms if not provided
        question_context = full_question or ' '.join(terms)
        
        # First pass: Check for negation expressions (Evolution 6)
        # Must be before OR to handle "not X or Y" correctly
        if detect_negation:
            for term in terms:
                term_lower = term.lower()
                if term_lower.startswith('not '):
                    # Extract the negated term
                    negated_term = term_lower[4:].strip()
                    # Remove "in " if present ("not in Texas" -> "Texas")
                    if negated_term.startswith('in '):
                        negated_term = negated_term[3:].strip()
                    neg_matches = self.resolve_negation_expression(negated_term, full_question=question_context)
                    if neg_matches:
                        matches.extend(neg_matches)
                        logger.warning(f"[TERM_INDEX] Term '{term}' resolved as negation expression")
                    else:
                        remaining_terms.append(term)
                else:
                    remaining_terms.append(term)
        else:
            remaining_terms = list(terms)
        
        # Second pass: Check for OR expressions (Evolution 5)
        or_remaining = []
        if detect_or:
            for term in remaining_terms:
                if ' or ' in term.lower():
                    # Split "X or Y" into individual terms
                    or_parts = [p.strip() for p in term.lower().split(' or ')]
                    or_matches = self.resolve_or_expression(or_parts, full_question=question_context)
                    if or_matches:
                        matches.extend(or_matches)
                        logger.warning(f"[TERM_INDEX] Term '{term}' resolved as OR expression")
                    else:
                        or_remaining.append(term)
                else:
                    or_remaining.append(term)
            remaining_terms = or_remaining
        
        # Third pass: Check for numeric expressions
        numeric_remaining = []
        if detect_numeric and HAS_VALUE_PARSER:
            for term in remaining_terms:
                # Try to parse as numeric expression - pass full question for context
                numeric_matches = self.resolve_numeric_expression(term, full_question=question_context)
                if numeric_matches:
                    matches.extend(numeric_matches)
                    logger.warning(f"[TERM_INDEX] Term '{term}' resolved as numeric expression")
                else:
                    numeric_remaining.append(term)
            remaining_terms = numeric_remaining
        
        # Fourth pass: Check remaining terms for date expressions
        date_remaining = []
        if detect_dates and HAS_VALUE_PARSER:
            for term in remaining_terms:
                # Try to parse as date expression
                date_matches = self.resolve_date_expression(term, full_question=question_context)
                if date_matches:
                    matches.extend(date_matches)
                    logger.warning(f"[TERM_INDEX] Term '{term}' resolved as date expression")
                else:
                    date_remaining.append(term)
            remaining_terms = date_remaining
        
        # Fifth pass: Regular term resolution for remaining terms
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
            'ukg_pro': 'ukg_pro_schema.json',
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
            Unified vocabulary dict (or list for seed format).
        """
        if self._unified_vocabulary:
            return self._unified_vocabulary
        
        # Prefer unified vocabulary (has more concepts), fall back to seed
        vocab_file = self.config_path / 'ukg_family_unified_vocabulary.json'
        if not vocab_file.exists():
            vocab_file = self.config_path / 'ukg_vocabulary_seed.json'
        
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
    Now also builds CONCEPT terms from vocabulary + inference.
    
    Args:
        conn: DuckDB connection
        project: Project ID
        
    Returns:
        Dict with recalc statistics.
    """
    # ==========================================================================
    # CASE SENSITIVITY FIX: Normalize project to match however it's stored
    # Try exact match first, then case-insensitive lookup
    # ==========================================================================
    original_project = project
    try:
        # Check if project exists as-is
        exact = conn.execute(
            "SELECT DISTINCT project FROM _column_profiles WHERE project = ? LIMIT 1", 
            [project]
        ).fetchone()
        
        if not exact:
            # Try case-insensitive match
            fuzzy = conn.execute(
                "SELECT DISTINCT project FROM _column_profiles WHERE LOWER(project) = LOWER(?) LIMIT 1",
                [project]
            ).fetchone()
            if fuzzy:
                project = fuzzy[0]
                logger.warning(f"[TERM_INDEX] Project case normalized: '{original_project}' → '{project}'")
    except Exception as e:
        logger.debug(f"[TERM_INDEX] Project normalization check failed: {e}")
    
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
        'state_columns_fallback': 0,
        'sample_values': [],
        'concept_terms_vocabulary': 0,
        'concept_terms_inferred': 0,
    }
    
    # ==========================================================================
    # STEP 1: Rebuild VALUE terms from column profiles (existing logic)
    # ==========================================================================
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
                str_values = [str(v).strip().upper() for v in values if v]
                state_like = sum(1 for v in str_values if len(v) == 2 and v.isalpha())
                
                if state_like >= len(str_values) * 0.5:
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
    
    # ==========================================================================
    # STEP 2: Rebuild from lookups
    # ==========================================================================
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
    
    # ==========================================================================
    # STEP 3: Rebuild entity tables
    # ==========================================================================
    entity_domain_map = {}  # table_name -> domain (for concept building)
    try:
        classifications = conn.execute("""
            SELECT table_name, table_type, domain, row_count
            FROM _table_classifications
            WHERE project_name = ?
        """, [project]).fetchall()
        
        class_list = []
        for c in classifications:
            class_list.append({
                'table_name': c[0], 'table_type': c[1], 'domain': c[2], 'row_count': c[3]
            })
            entity_domain_map[c[0].lower()] = c[2]  # Store for concept building
        
        stats['classifications_found'] = len(classifications)
        stats['entity_mappings'] = index.build_entity_tables(class_list)
        logger.info(f"[TERM_INDEX] Loaded {len(classifications)} classifications from _table_classifications")
    except Exception as e:
        logger.debug(f"Classification table may not exist: {e}")
        stats['classifications_found'] = 0
    
    # Set join priorities
    stats['join_priorities'] = index.set_all_join_priorities()
    
    # ==========================================================================
    # STEP 4: BUILD CONCEPT TERMS (NEW)
    # Sources: vocabulary file (primary) + inference from semantic_type (secondary)
    # ==========================================================================
    try:
        concept_stats = _build_concept_terms(conn, index, project, entity_domain_map)
        stats['concept_terms_vocabulary'] = concept_stats.get('vocabulary', 0)
        stats['concept_terms_inferred'] = concept_stats.get('inferred', 0)
    except Exception as e:
        logger.error(f"[TERM_INDEX] Error building concept terms: {e}")
        stats['concept_error'] = str(e)
    
    # ==========================================================================
    # STEP 5: DETECT RELATIONSHIPS (Evolution 10: Multi-Hop)
    # Finds self-referential columns and foreign key relationships
    # ==========================================================================
    try:
        relationship_stats = _detect_relationships(conn, project)
        stats['relationships_detected'] = relationship_stats.get('total', 0)
        stats['self_references'] = relationship_stats.get('self_references', 0)
        stats['foreign_keys'] = relationship_stats.get('foreign_keys', 0)
    except Exception as e:
        logger.warning(f"[TERM_INDEX] Relationship detection failed: {e}")
        stats['relationship_error'] = str(e)
    
    conn.commit()
    
    logger.info(f"[TERM_INDEX] Recalc complete: {stats}")
    return stats


def _build_concept_terms(
    conn: duckdb.DuckDBPyConnection, 
    index: 'TermIndex', 
    project: str,
    entity_domain_map: Dict[str, str]
) -> Dict[str, int]:
    """
    Build CONCEPT terms that map user concepts (like "state", "salary") to columns.
    
    Three-pass approach:
    1. VOCABULARY: Load concepts from vocabulary JSON, match to hubs by semantic_type
    2. FILTER_CATEGORY: Use column profiles to map concepts (state, status) to actual columns
    3. INFERRED: For remaining hubs, derive concept by stripping _code/_id suffix
    
    Args:
        conn: DuckDB connection
        index: TermIndex instance to add terms to
        project: Project ID
        entity_domain_map: table_name -> domain mapping for entity detection
        
    Returns:
        Dict with counts: {'vocabulary': N, 'inferred': M, 'filter_category': P}
    """
    stats = {'vocabulary': 0, 'inferred': 0, 'filter_category': 0}
    covered_semantic_types = set()
    covered_columns = set()  # Track (table, column) to avoid duplicates
    
    # --------------------------------------------------------------------------
    # Load context graph hubs (semantic_type -> table/column)
    # --------------------------------------------------------------------------
    hubs = []
    try:
        hub_rows = conn.execute("""
            SELECT table_name, original_column, semantic_type, is_hub
            FROM _column_mappings
            WHERE project = ? AND is_hub = TRUE
        """, [project]).fetchall()
        
        for table_name, column_name, semantic_type, is_hub in hub_rows:
            if semantic_type:
                hubs.append({
                    'table': table_name,
                    'column': column_name,
                    'semantic_type': semantic_type.lower(),
                    'domain': entity_domain_map.get(table_name.lower(), 'unknown')
                })
        
        logger.info(f"[TERM_INDEX] Found {len(hubs)} hubs for concept mapping")
    except Exception as e:
        logger.warning(f"[TERM_INDEX] Could not load hubs from _column_mappings: {e}")
    
    # Build lookup: semantic_type -> list of hubs
    semantic_to_hubs: Dict[str, List[Dict]] = {}
    for hub in hubs:
        st = hub['semantic_type']
        if st not in semantic_to_hubs:
            semantic_to_hubs[st] = []
        semantic_to_hubs[st].append(hub)
    
    # ==========================================================================
    # PASS 1: Filter-category based concepts (MOST RELIABLE for user queries)
    # Maps common concepts to columns based on filter_category + column name hints
    # ==========================================================================
    
    # Concept -> (filter_category, column_name_patterns)
    # Only match if BOTH filter_category matches AND column name contains pattern
    CONCEPT_MAPPINGS = {
        # Location concepts - must match column name patterns
        'state': ('location', ['state', 'province', 'stateprovince']),
        'location': ('location', ['location', 'site', 'facility', 'office']),
        'region': ('location', ['region', 'area', 'territory']),
        'country': ('location', ['country', 'nation']),
        'city': ('location', ['city', 'town']),
        'county': ('location', ['county']),
        
        # Status concepts
        'status': ('status', ['status', 'active', 'inactive', 'terminated']),
        'employment status': ('status', ['status', 'emp_status', 'employment']),
        
        # Company concepts
        'company': ('company', ['company', 'employer', 'entity', 'cocode']),
        
        # Org concepts
        'department': ('organization', ['department', 'dept']),
        'division': ('organization', ['division', 'div']),
        'cost center': ('organization', ['cost_center', 'costcenter', 'cc']),
        'organization': ('organization', ['org', 'organization']),
        
        # Pay type concepts
        'pay type': ('pay_type', ['pay_type', 'paytype', 'hourly', 'salary', 'flsa']),
        
        # Employee type concepts
        'employee type': ('employee_type', ['employee_type', 'emp_type', 'worker_type']),
        
        # Job concepts
        'job': ('job', ['job', 'position', 'title', 'role']),
        'job code': ('job', ['job_code', 'jobcode', 'position_code']),
    }
    
    try:
        # Get columns with filter_category from profiles
        filter_cols = conn.execute("""
            SELECT DISTINCT table_name, column_name, filter_category
            FROM _column_profiles
            WHERE project = ? AND filter_category IS NOT NULL
        """, [project]).fetchall()
        
        logger.info(f"[TERM_INDEX] Found {len(filter_cols)} columns with filter_category")
        
        for table_name, column_name, filter_category in filter_cols:
            col_lower = column_name.lower()
            domain = entity_domain_map.get(table_name.lower(), 'unknown')
            entity = _domain_to_entity(domain)
            
            # Check each concept to see if this column matches
            for concept, (required_category, col_patterns) in CONCEPT_MAPPINGS.items():
                # Must match filter_category
                if filter_category != required_category:
                    continue
                
                # Must match at least one column name pattern
                if not any(pat in col_lower for pat in col_patterns):
                    continue
                
                col_key = (table_name.lower(), column_name.lower(), concept)
                if col_key in covered_columns:
                    continue
                    
                if index.add_term(
                    term=concept,
                    term_type='concept',
                    table_name=table_name,
                    column_name=column_name,
                    operator='GROUP BY',
                    match_value=None,
                    domain=domain,
                    entity=entity,
                    confidence=0.90,
                    source='filter_category'
                ):
                    stats['filter_category'] += 1
                    logger.debug(f"[TERM_INDEX] Concept '{concept}' → {table_name}.{column_name}")
            
                covered_columns.add(col_key)
                
    except Exception as e:
        logger.warning(f"[TERM_INDEX] Filter category concept building failed: {e}")
    
    # ==========================================================================
    # PASS 2: Vocabulary-based concepts
    # ==========================================================================
    try:
        vocab_loader = VendorSchemaLoader()
        vocabulary = vocab_loader.load_unified_vocabulary()
        
        # Handle both formats:
        # - ukg_vocabulary_seed.json: LIST of {semantic_type, display_name, hub_type, ...}
        # - ukg_family_unified_vocabulary.json: DICT with vocabulary: {concept: {...}}
        
        vocab_entries = []
        if isinstance(vocabulary, list):
            vocab_entries = vocabulary
            logger.info(f"[TERM_INDEX] Loaded vocabulary (list format) with {len(vocab_entries)} entries")
        elif isinstance(vocabulary, dict):
            vocab_dict = vocabulary.get('vocabulary', {})
            for concept_name, concept_def in vocab_dict.items():
                entry = {
                    'concept': concept_name,
                    'semantic_type': None,
                    'display_name': concept_def.get('entity_name', concept_name),
                }
                sem_types = concept_def.get('semantic_types', {})
                if sem_types:
                    entry['semantic_type'] = list(sem_types.values())[0]
                vocab_entries.append(entry)
            logger.info(f"[TERM_INDEX] Loaded vocabulary (dict format) with {len(vocab_entries)} entries")
        
        for entry in vocab_entries:
            sem_type = entry.get('semantic_type', '')
            if not sem_type:
                continue
            
            sem_type_lower = sem_type.lower()
            
            concept_name = entry.get('hub_type') or entry.get('concept')
            if not concept_name:
                display = entry.get('display_name', '')
                concept_name = display.lower().replace(' ', '_') if display else None
            if not concept_name:
                concept_name = _derive_concept_from_semantic_type(sem_type_lower)
            
            if not concept_name or len(concept_name) < 2:
                continue
            
            concept_name = concept_name.lower().replace('_', ' ').strip()
            
            if sem_type_lower in semantic_to_hubs:
                for hub in semantic_to_hubs[sem_type_lower]:
                    col_key = (hub['table'].lower(), hub['column'].lower())
                    if col_key in covered_columns:
                        continue
                        
                    entity = _domain_to_entity(hub['domain'])
                    
                    if index.add_term(
                        term=concept_name,
                        term_type='concept',
                        table_name=hub['table'],
                        column_name=hub['column'],
                        operator='GROUP BY',
                        match_value=None,
                        domain=hub['domain'],
                        entity=entity,
                        confidence=0.95,
                        source='vocabulary'
                    ):
                        stats['vocabulary'] += 1
                    
                    covered_columns.add(col_key)
                
                covered_semantic_types.add(sem_type_lower)
                logger.debug(f"[TERM_INDEX] Vocabulary concept '{concept_name}' → {sem_type_lower}")
                
    except Exception as e:
        logger.warning(f"[TERM_INDEX] Vocabulary loading failed: {e}")
        import traceback
        logger.warning(f"[TERM_INDEX] Traceback: {traceback.format_exc()}")
    
    # --------------------------------------------------------------------------
    # PASS 2: Inferred concepts from remaining semantic_types
    # --------------------------------------------------------------------------
    for semantic_type, hub_list in semantic_to_hubs.items():
        if semantic_type in covered_semantic_types:
            continue  # Already covered by vocabulary
        
        # Derive concept name by stripping common suffixes
        concept = _derive_concept_from_semantic_type(semantic_type)
        if not concept or len(concept) < 2:
            continue
        
        for hub in hub_list:
            entity = _domain_to_entity(hub['domain'])
            
            if index.add_term(
                term=concept,
                term_type='concept',
                table_name=hub['table'],
                column_name=hub['column'],
                operator='GROUP BY',
                match_value=None,
                domain=hub['domain'],
                entity=entity,
                confidence=0.75,  # Lower confidence for inferred
                source='inferred'
            ):
                stats['inferred'] += 1
        
        logger.debug(f"[TERM_INDEX] Inferred concept '{concept}' from semantic_type '{semantic_type}'")
    
    logger.info(f"[TERM_INDEX] Concept terms built: {stats['vocabulary']} from vocabulary, {stats['inferred']} inferred")
    return stats


def _derive_concept_from_semantic_type(semantic_type: str) -> Optional[str]:
    """
    Derive a user-friendly concept name from a semantic_type.
    
    Examples:
        'location_code' -> 'location'
        'employee_number' -> 'employee'
        'pay_group_code' -> 'pay_group' -> 'pay group'
        'state_code' -> 'state'
    """
    if not semantic_type:
        return None
    
    st = semantic_type.lower().strip()
    
    # Strip common suffixes
    for suffix in ['_code', '_id', '_number', '_num', '_key']:
        if st.endswith(suffix):
            st = st[:-len(suffix)]
            break
    
    # Replace underscores with spaces for multi-word concepts
    # But also keep underscore version as that might match
    return st.replace('_', ' ').strip()


def _domain_to_entity(domain: str) -> Optional[str]:
    """
    Map a domain/truth_type to a canonical entity name.
    
    This helps filter concept terms by what type of question is being asked.
    """
    if not domain:
        return None
    
    domain_lower = domain.lower()
    
    # Reality domains -> employee entity
    if domain_lower in ('hr', 'payroll', 'demographics', 'personal', 'employee', 'reality'):
        return 'employee'
    
    # Configuration domains
    if domain_lower in ('configuration', 'config', 'setup'):
        return 'configuration'
    
    # Benefits/deductions
    if domain_lower in ('benefits', 'deductions', 'benefit'):
        return 'benefits'
    
    # Tax
    if domain_lower in ('tax', 'taxes'):
        return 'tax'
    
    # Time
    if domain_lower in ('time', 'timekeeping', 'attendance'):
        return 'time'
    
    # Organization
    if domain_lower in ('organization', 'org', 'company'):
        return 'organization'
    
    return domain_lower  # Return as-is if no mapping


# =============================================================================
# EVOLUTION 10: RELATIONSHIP DETECTION
# =============================================================================

def _detect_relationships(conn: duckdb.DuckDBPyConnection, project: str) -> Dict[str, int]:
    """
    Detect self-referential and foreign key relationships in project tables.
    
    Called during recalc to find:
    - supervisor_id → employee_number (self-references)
    - department_code → department table (foreign keys)
    
    Args:
        conn: DuckDB connection
        project: Project ID
        
    Returns:
        Dict with detection counts
    """
    import re
    stats = {'total': 0, 'self_references': 0, 'foreign_keys': 0}
    
    # Self-reference patterns: column names that reference employee identifiers
    SELF_REF_PATTERNS = [
        # ID-based patterns
        (r'supervisor.*(?:id|number|no)$', r'employee.*(?:id|number|no)$', 'supervisor'),
        (r'manager.*(?:id|number|no)$', r'employee.*(?:id|number|no)$', 'supervisor'),
        (r'reports.*to.*(?:id|number|no)$', r'employee.*(?:id|number|no)$', 'supervisor'),
        (r'alternate.*super.*(?:id|number|no)$', r'employee.*(?:id|number|no)$', 'alternate_supervisor'),
        (r'primary.*super.*(?:id|number|no)$', r'employee.*(?:id|number|no)$', 'primary_supervisor'),
        (r'hiring.*manager.*(?:id|number|no)$', r'employee.*(?:id|number|no)$', 'hiring_manager'),
        (r'parent.*(?:id|code)$', r'(?:^id$|^code$)', 'parent_org'),
        # Name-based patterns (supervisor_name → employee_name)
        (r'supervisor.*name$', r'(?:employee.*name|^name$|full.*name)', 'supervisor'),
        (r'manager.*name$', r'(?:employee.*name|^name$|full.*name)', 'supervisor'),
        (r'reports.*to.*name$', r'(?:employee.*name|^name$|full.*name)', 'supervisor'),
        (r'alternate.*super.*name$', r'(?:employee.*name|^name$|full.*name)', 'alternate_supervisor'),
        (r'hiring.*manager.*name$', r'(?:employee.*name|^name$|full.*name)', 'hiring_manager'),
    ]
    
    # Ensure the relationships table exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _column_relationships (
            project VARCHAR NOT NULL,
            source_table VARCHAR NOT NULL,
            source_column VARCHAR NOT NULL,
            target_table VARCHAR NOT NULL,
            target_column VARCHAR NOT NULL,
            relationship_type VARCHAR NOT NULL,
            semantic_meaning VARCHAR,
            confidence FLOAT DEFAULT 0.9,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            PRIMARY KEY (project, source_table, source_column, target_table, target_column)
        )
    """)
    
    try:
        # Get all tables for this project
        tables = conn.execute("""
            SELECT DISTINCT table_name 
            FROM _column_profiles 
            WHERE LOWER(project) = LOWER(?)
        """, [project]).fetchall()
        
        for (table_name,) in tables:
            # Get all columns for this table
            columns = conn.execute("""
                SELECT column_name, original_dtype
                FROM _column_profiles
                WHERE LOWER(project) = LOWER(?) AND table_name = ?
            """, [project, table_name]).fetchall()
            
            column_info = {row[0].lower(): {'name': row[0], 'dtype': row[1]} 
                          for row in columns}
            
            # Check for self-reference patterns
            for source_col_lower, info in column_info.items():
                source_col = info['name']
                
                for source_pattern, target_pattern, semantic in SELF_REF_PATTERNS:
                    if not re.search(source_pattern, source_col_lower, re.IGNORECASE):
                        continue
                    
                    # Find matching target column in same table
                    for target_col_lower, target_info in column_info.items():
                        target_col = target_info['name']
                        if source_col_lower == target_col_lower:
                            continue
                            
                        if re.search(target_pattern, target_col_lower, re.IGNORECASE):
                            # Found a self-reference!
                            try:
                                conn.execute("""
                                    INSERT INTO _column_relationships 
                                    (project, source_table, source_column, target_table, target_column,
                                     relationship_type, semantic_meaning, confidence)
                                    VALUES (?, ?, ?, ?, ?, 'self_reference', ?, 0.85)
                                    ON CONFLICT (project, source_table, source_column, target_table, target_column)
                                    DO UPDATE SET
                                        relationship_type = EXCLUDED.relationship_type,
                                        semantic_meaning = EXCLUDED.semantic_meaning,
                                        confidence = EXCLUDED.confidence
                                """, [
                                    project.lower(),
                                    table_name,
                                    source_col,
                                    table_name,
                                    target_col,
                                    semantic
                                ])
                                stats['self_references'] += 1
                                stats['total'] += 1
                                logger.info(f"[RELATIONSHIP] Self-ref: {table_name}.{source_col} → {target_col} ({semantic})")
                            except Exception as e:
                                logger.debug(f"[RELATIONSHIP] Insert note: {e}")
                            break  # Found match, move to next source column
        
        conn.commit()
        
    except Exception as e:
        logger.warning(f"[RELATIONSHIP] Detection error: {e}")
        stats['error'] = str(e)
    
    logger.info(f"[TERM_INDEX] Relationship detection: {stats}")
    return stats
