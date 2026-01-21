"""
XLR8 Relationship Detector (Schema-Driven)
==========================================

Detects relationships between tables using SCHEMA KNOWLEDGE, not value guessing.

Algorithm:
1. Load schema for the system (UKG, Workday, etc.)
2. For each column, check if it's a known hub reference
3. Find the hub table in the project
4. VALIDATE with value overlap (90%+ threshold)
5. Only declare relationship if validated

NO more flsaTypeCode → maritalStatusCode garbage.

Author: XLR8 Team
Version: 1.0.0
"""

import logging
import re
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class HubInfo:
    """Information about a detected hub (config table)."""
    table_name: str
    key_column: str
    hub_type: str  # e.g., "earning", "job", "location"
    entity_type: str  # From _schema_metadata
    domain: str  # "Configuration" or "Employee_Data"
    cardinality: int
    values: Set[str] = field(default_factory=set)


@dataclass
class RelationshipInfo:
    """Information about a detected relationship."""
    spoke_table: str
    spoke_column: str
    hub_table: str
    hub_column: str
    hub_type: str
    coverage_pct: float
    is_valid: bool  # True if spoke values ⊆ hub values
    match_method: str  # "schema" or "heuristic"


class RelationshipDetector:
    """
    Schema-driven relationship detection.
    
    Usage:
        detector = RelationshipDetector(duckdb_conn, project_id)
        detector.set_system("ukg_pro")  # Optional - auto-detects if not set
        results = detector.detect_all()
    """
    
    # Minimum overlap for validation
    MIN_VALIDATION_COVERAGE = 90.0
    
    # Known suffixes that indicate a reference column
    REFERENCE_SUFFIXES = ['code', 'id', 'key', 'type', 'number', 'no', 'num']
    
    # Generic columns that need context (can't be resolved without entity_type)
    GENERIC_COLUMNS = {'code', 'id', 'type', 'status', 'name', 'description'}
    
    def __init__(self, conn, project: str):
        """
        Initialize detector.
        
        Args:
            conn: DuckDB connection
            project: Project/customer ID
        """
        self.conn = conn
        self.project = project
        self.system: Optional[str] = None
        
        # Lazy load schema registry
        self._registry = None
        
        # Cache
        self._tables: List[Dict] = []
        self._hubs: Dict[str, HubInfo] = {}  # hub_type → HubInfo
        self._column_values: Dict[Tuple[str, str], Set[str]] = {}  # (table, col) → values
    
    @property
    def registry(self):
        """Lazy load schema registry."""
        if self._registry is None:
            from backend.utils.intelligence.schema_registry import get_schema_registry
            self._registry = get_schema_registry()
        return self._registry
    
    def set_system(self, system: str):
        """Set the HCM system for schema lookups."""
        self.system = system
        logger.info(f"[REL-DETECT] System set to: {system}")
    
    def detect_all(self) -> Dict[str, Any]:
        """
        Detect all relationships in the project.
        
        Returns:
            Dict with 'hubs', 'relationships', 'stats'
        """
        logger.info(f"[REL-DETECT] Starting relationship detection for {self.project}")
        
        # Step 1: Load all tables
        self._load_tables()
        if not self._tables:
            logger.warning(f"[REL-DETECT] No tables found for {self.project}")
            return {'hubs': [], 'relationships': [], 'stats': {'tables': 0}}
        
        # Step 2: Auto-detect system if not set
        if not self.system:
            self._auto_detect_system()
        
        # Step 3: Find all hubs (config tables)
        self._find_hubs()
        
        # Step 4: Find relationships (spoke columns → hubs)
        relationships = self._find_relationships()
        
        # Build result
        hub_list = [
            {
                'table': h.table_name,
                'column': h.key_column,
                'hub_type': h.hub_type,
                'entity_type': h.entity_type,
                'domain': h.domain,
                'cardinality': h.cardinality
            }
            for h in self._hubs.values()
        ]
        
        rel_list = [
            {
                'spoke_table': r.spoke_table,
                'spoke_column': r.spoke_column,
                'hub_table': r.hub_table,
                'hub_column': r.hub_column,
                'hub_type': r.hub_type,
                'coverage_pct': r.coverage_pct,
                'is_valid': r.is_valid,
                'match_method': r.match_method
            }
            for r in relationships
        ]
        
        logger.info(f"[REL-DETECT] Complete: {len(hub_list)} hubs, {len(rel_list)} relationships")
        
        return {
            'hubs': hub_list,
            'relationships': rel_list,
            'stats': {
                'tables': len(self._tables),
                'hubs_found': len(hub_list),
                'relationships_found': len(rel_list),
                'system': self.system
            }
        }
    
    def _load_tables(self):
        """Load all tables for this project from _schema_metadata."""
        try:
            # Get tables with metadata
            rows = self.conn.execute("""
                SELECT 
                    table_name,
                    file_name,
                    entity_type,
                    category,
                    truth_type,
                    row_count
                FROM _schema_metadata
                WHERE project = ?
                  AND is_current = TRUE
                  AND table_name NOT LIKE '\\_%' ESCAPE '\\'
            """, [self.project]).fetchall()
            
            self._tables = [
                {
                    'table_name': r[0],
                    'file_name': r[1],
                    'entity_type': r[2],
                    'category': r[3],
                    'truth_type': r[4],
                    'row_count': r[5] or 0
                }
                for r in rows
            ]
            
            logger.info(f"[REL-DETECT] Loaded {len(self._tables)} tables")
            
        except Exception as e:
            logger.error(f"[REL-DETECT] Failed to load tables: {e}")
            self._tables = []
    
    def _auto_detect_system(self):
        """Try to detect the HCM system from table data."""
        # Collect all column names
        all_columns = []
        for table in self._tables[:10]:  # Sample first 10 tables
            try:
                cols = self.conn.execute(f"PRAGMA table_info('{table['table_name']}')").fetchall()
                all_columns.extend([c[1] for c in cols])
            except:
                pass
        
        if all_columns:
            detected = self.registry.detect_system(all_columns)
            if detected:
                self.system = detected
                logger.info(f"[REL-DETECT] Auto-detected system: {detected}")
            else:
                logger.info("[REL-DETECT] Could not auto-detect system, using global schema")
    
    def _find_hubs(self):
        """Find all hub tables (config tables with code columns)."""
        self._hubs = {}
        
        for table in self._tables:
            table_name = table['table_name']
            entity_type = table['entity_type']
            truth_type = table['truth_type']
            
            # Skip reality tables (they have spokes, not hubs)
            # But check all tables for potential hubs
            
            # Get columns
            try:
                cols = self.conn.execute(f"PRAGMA table_info('{table_name}')").fetchall()
                col_names = [c[1] for c in cols if c[1] and not c[1].startswith('_')]
            except:
                continue
            
            # Find key column for this table
            key_column = None
            hub_type = None
            
            # Method 1: Use entity_type to find hub type
            if entity_type:
                hub_type = self.registry.entity_to_hub(entity_type, self.system)
                if hub_type:
                    expected_key = self.registry.hub_to_key_column(hub_type, self.system)
                    if expected_key:
                        # Check if this key column exists in the table
                        for col in col_names:
                            if col.lower() == expected_key.lower() or \
                               col.lower().replace('_', '') == expected_key.lower().replace('_', ''):
                                key_column = col
                                break
            
            # Method 2: Look for *Code or *Id columns
            if not key_column:
                for col in col_names:
                    # Skip generic columns
                    if col.lower() in self.GENERIC_COLUMNS:
                        continue
                    
                    # Check if column maps to a hub
                    col_hub = self.registry.column_to_hub(col, self.system)
                    if col_hub:
                        key_column = col
                        hub_type = col_hub
                        break
            
            # Method 3: Heuristic for *Code columns on config tables
            if not key_column and truth_type == 'configuration':
                for col in col_names:
                    if col.lower().endswith('code') and col.lower() not in self.GENERIC_COLUMNS:
                        key_column = col
                        # Derive hub type from column name
                        hub_type = self._derive_hub_type_from_column(col)
                        break
            
            if key_column and hub_type:
                # Get values and cardinality
                try:
                    values_result = self.conn.execute(f"""
                        SELECT DISTINCT LOWER(TRIM(CAST("{key_column}" AS VARCHAR)))
                        FROM "{table_name}"
                        WHERE "{key_column}" IS NOT NULL
                          AND TRIM(CAST("{key_column}" AS VARCHAR)) != ''
                        LIMIT 10000
                    """).fetchall()
                    values = {r[0] for r in values_result if r[0]}
                except:
                    values = set()
                
                # Only consider as hub if it has values
                if values:
                    domain = self.registry.get_hub_domain(hub_type, self.system) or \
                             ('Configuration' if truth_type == 'configuration' else 'Employee_Data')
                    
                    self._hubs[hub_type] = HubInfo(
                        table_name=table_name,
                        key_column=key_column,
                        hub_type=hub_type,
                        entity_type=entity_type or hub_type,
                        domain=domain,
                        cardinality=len(values),
                        values=values
                    )
                    
                    logger.debug(f"[REL-DETECT] Hub: {hub_type} → {table_name}.{key_column} ({len(values)} values)")
        
        logger.info(f"[REL-DETECT] Found {len(self._hubs)} hubs")
    
    def _derive_hub_type_from_column(self, column: str) -> str:
        """Derive hub type from column name (fallback heuristic)."""
        # earningCode → earning
        # jobCode → job
        col_lower = column.lower()
        
        for suffix in self.REFERENCE_SUFFIXES:
            if col_lower.endswith(suffix):
                base = col_lower[:-len(suffix)]
                # Handle underscore: earning_code → earning
                base = base.rstrip('_')
                if base:
                    return base
        
        return column.lower()
    
    def _find_relationships(self) -> List[RelationshipInfo]:
        """Find all spoke→hub relationships."""
        relationships = []
        seen = set()  # Avoid duplicates
        
        for table in self._tables:
            table_name = table['table_name']
            
            # Get columns
            try:
                cols = self.conn.execute(f"PRAGMA table_info('{table_name}')").fetchall()
                col_names = [c[1] for c in cols if c[1] and not c[1].startswith('_')]
            except:
                continue
            
            for col in col_names:
                # Skip generic columns (need entity_type context to resolve)
                if col.lower() in self.GENERIC_COLUMNS:
                    continue
                
                # Method 1: Schema lookup
                hub_type = self.registry.column_to_hub(col, self.system)
                match_method = "schema"
                
                # Method 2: Heuristic (if schema doesn't know)
                if not hub_type:
                    hub_type = self._derive_hub_type_from_column(col)
                    match_method = "heuristic"
                
                if not hub_type:
                    continue
                
                # Check if we have a hub for this type
                if hub_type not in self._hubs:
                    continue
                
                hub = self._hubs[hub_type]
                
                # Skip self-reference (hub table to itself)
                if table_name == hub.table_name:
                    continue
                
                # Skip if already seen
                key = (table_name, col, hub.table_name, hub.key_column)
                if key in seen:
                    continue
                seen.add(key)
                
                # Get spoke values
                try:
                    spoke_values = self._get_column_values(table_name, col)
                except:
                    continue
                
                if not spoke_values:
                    continue
                
                # Validate: Check overlap with hub
                overlap = spoke_values & hub.values
                coverage_pct = (len(overlap) / len(spoke_values)) * 100 if spoke_values else 0
                is_valid = spoke_values <= hub.values  # All spoke values in hub
                
                # Only accept if coverage is high enough
                if coverage_pct >= self.MIN_VALIDATION_COVERAGE:
                    relationships.append(RelationshipInfo(
                        spoke_table=table_name,
                        spoke_column=col,
                        hub_table=hub.table_name,
                        hub_column=hub.key_column,
                        hub_type=hub_type,
                        coverage_pct=round(coverage_pct, 1),
                        is_valid=is_valid,
                        match_method=match_method
                    ))
                    
                    logger.debug(f"[REL-DETECT] Relationship: {table_name}.{col} → {hub.table_name}.{hub.key_column} ({coverage_pct:.0f}%)")
                elif coverage_pct > 0:
                    # Log potential relationship that didn't meet threshold
                    logger.debug(f"[REL-DETECT] Low coverage: {table_name}.{col} → {hub_type} ({coverage_pct:.0f}%) - skipped")
        
        logger.info(f"[REL-DETECT] Found {len(relationships)} validated relationships")
        return relationships
    
    def _get_column_values(self, table: str, column: str) -> Set[str]:
        """Get distinct values for a column (cached)."""
        cache_key = (table, column)
        
        if cache_key not in self._column_values:
            try:
                result = self.conn.execute(f"""
                    SELECT DISTINCT LOWER(TRIM(CAST("{column}" AS VARCHAR)))
                    FROM "{table}"
                    WHERE "{column}" IS NOT NULL
                      AND TRIM(CAST("{column}" AS VARCHAR)) != ''
                    LIMIT 10000
                """).fetchall()
                self._column_values[cache_key] = {r[0] for r in result if r[0]}
            except:
                self._column_values[cache_key] = set()
        
        return self._column_values[cache_key]


# =========================================================================
# CONVENIENCE FUNCTION
# =========================================================================

def detect_relationships(conn, project: str, system: str = None) -> Dict[str, Any]:
    """
    Quick function to detect all relationships for a project.
    
    Args:
        conn: DuckDB connection
        project: Project/customer ID
        system: Optional system name (auto-detects if not provided)
        
    Returns:
        Dict with 'hubs', 'relationships', 'stats'
    """
    detector = RelationshipDetector(conn, project)
    if system:
        detector.set_system(system)
    return detector.detect_all()
