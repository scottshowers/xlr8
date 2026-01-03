"""
Data Model Service
==================

Transform codes into human-readable values.

Auto-detects reference/lookup tables, builds code → description 
dictionaries, and enriches query results.

Example:
    Input:  "847 employees have location_code = 'LOC001'"
    Output: "847 employees in Houston, TX (LOC001)"

Usage:
    service = DataModelService("my_project")
    service.load_lookups(handler)
    enriched = service.enrich_value("location_code", "LOC001")
    # Returns: "Houston, TX (LOC001)"
"""

import re
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Try to import project intelligence for pre-computed lookups
try:
    from backend.utils.project_intelligence import get_project_intelligence
    PROJECT_INTELLIGENCE_AVAILABLE = True
except ImportError:
    try:
        from utils.project_intelligence import get_project_intelligence
        PROJECT_INTELLIGENCE_AVAILABLE = True
    except ImportError:
        PROJECT_INTELLIGENCE_AVAILABLE = False
        get_project_intelligence = None


class DataModelService:
    """
    Data Model Intelligence Service - Transform codes into human-readable values.
    
    This service:
    1. Auto-detects reference/lookup tables
    2. Builds code → description dictionaries
    3. Enriches query results with human-readable values
    """
    
    # Patterns that indicate a reference/lookup table
    REFERENCE_TABLE_PATTERNS = [
        r'.*_codes?$',           # location_codes, pay_codes
        r'.*_types?$',           # employee_types, deduction_types
        r'.*_lookup$',           # department_lookup
        r'.*_ref$',              # status_ref
        r'.*_master$',           # Only if small row count
        r'^ref_.*',              # ref_locations
        r'^lkp_.*',              # lkp_departments
        r'^code_.*',             # code_earnings
    ]
    
    # Common code → description column mappings
    CODE_DESCRIPTION_PATTERNS = [
        ('code', 'description'),
        ('code', 'name'),
        ('id', 'description'),
        ('id', 'name'),
        ('key', 'value'),
        ('abbreviation', 'full_name'),
        ('short_name', 'long_name'),
        ('location_code', 'location_name'),
        ('dept_code', 'dept_name'),
        ('company_code', 'company_name'),
    ]
    
    def __init__(self, project: str):
        self.project = project
        self.lookups: Dict[str, Dict[str, str]] = {}  # table_name -> {code: description}
        self.code_columns: Dict[str, str] = {}  # column_name -> lookup_table
        self._loaded = False
    
    def load_lookups(self, handler) -> None:
        """
        Load lookup dictionaries - tries intelligence service first, falls back to scanning.
        
        Phase 3.5: Consumes pre-computed lookups from ProjectIntelligenceService
        when available, avoiding redundant table scanning.
        
        Args:
            handler: DuckDB structured data handler
        """
        logger.warning(f"[DATA_MODEL] load_lookups called for {self.project}, _loaded={self._loaded}")
        
        if self._loaded:
            return
        
        # PHASE 3.5: Try intelligence service first (pre-computed on upload)
        if PROJECT_INTELLIGENCE_AVAILABLE and handler and get_project_intelligence:
            try:
                logger.warning(f"[DATA_MODEL] Attempting to load from intelligence service for {self.project}")
                intelligence = get_project_intelligence(self.project, handler)
                if intelligence and intelligence.lookups:
                    logger.warning(f"[DATA_MODEL] Found {len(intelligence.lookups)} lookups in intelligence")
                    # Pull from pre-computed lookups
                    for lookup in intelligence.lookups:
                        table_name = lookup.table_name
                        code_col = lookup.code_column
                        desc_col = lookup.description_column
                        mappings = lookup.lookup_data  # Note: attribute is lookup_data, not mappings
                        
                        if mappings:
                            self.lookups[table_name] = mappings
                            self.code_columns[code_col] = table_name
                    
                    self._loaded = True
                    logger.warning(f"[DATA_MODEL] Loaded {len(self.lookups)} lookup tables from intelligence service")
                    return
                else:
                    logger.warning(f"[DATA_MODEL] No lookups found in intelligence, falling back to scan")
            except Exception as e:
                logger.warning(f"[DATA_MODEL] Intelligence service unavailable, falling back: {e}")
        
        # FALLBACK: Scan tables directly (original behavior)
        if not handler or not handler.conn:
            return
        
        try:
            # Get all tables for project
            all_tables = handler.conn.execute("SHOW TABLES").fetchall()
            project_prefix = (self.project or '').lower().replace(' ', '_').replace('-', '_')
            
            for (table_name,) in all_tables:
                # Skip system tables
                if table_name.startswith('_'):
                    continue
                
                # Check if matches project
                if project_prefix and not table_name.lower().startswith(project_prefix.lower()):
                    continue
                
                # Check if looks like a reference table
                table_lower = table_name.lower()
                is_reference = any(re.match(pattern, table_lower) for pattern in self.REFERENCE_TABLE_PATTERNS)
                
                if not is_reference:
                    # Also check row count - reference tables are usually small
                    try:
                        count = handler.conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]
                        if count <= 500:  # Small table might be a lookup
                            is_reference = True
                    except Exception:
                        pass
                
                if is_reference:
                    self._load_lookup_table(handler, table_name)
            
            self._loaded = True
            logger.info(f"[DATA_MODEL] Loaded {len(self.lookups)} lookup tables for {self.project}")
            
        except Exception as e:
            logger.warning(f"[DATA_MODEL] Failed to load lookups: {e}")
    
    def _load_lookup_table(self, handler, table_name: str) -> None:
        """Load a single lookup table into memory."""
        try:
            # Get columns
            cols = handler.conn.execute(f'DESCRIBE "{table_name}"').fetchall()
            col_names = [c[0].lower() for c in cols]
            
            # Find code and description columns
            code_col = None
            desc_col = None
            
            for code_pattern, desc_pattern in self.CODE_DESCRIPTION_PATTERNS:
                for col in col_names:
                    if code_pattern in col and not code_col:
                        code_col = col
                    if desc_pattern in col and not desc_col:
                        desc_col = col
                
                if code_col and desc_col:
                    break
            
            # Fallback: first column is code, second is description
            if not code_col and len(col_names) >= 2:
                code_col = col_names[0]
                desc_col = col_names[1]
            
            if code_col and desc_col:
                # Load the lookup data
                rows = handler.conn.execute(f'''
                    SELECT "{code_col}", "{desc_col}" 
                    FROM "{table_name}" 
                    WHERE "{code_col}" IS NOT NULL
                    LIMIT 1000
                ''').fetchall()
                
                lookup = {str(row[0]): str(row[1]) for row in rows if row[0] and row[1]}
                
                if lookup:
                    self.lookups[table_name] = lookup
                    # Also map the code column to this lookup
                    self.code_columns[code_col] = table_name
                    logger.debug(f"[DATA_MODEL] Loaded {len(lookup)} values from {table_name}")
                    
        except Exception as e:
            logger.warning(f"[DATA_MODEL] Could not load {table_name}: {e}")
    
    def enrich_value(self, column: str, value: str) -> str:
        """
        Enrich a code value with its description.
        
        Args:
            column: Column name (e.g., "location_code")
            value: Code value (e.g., "LOC001")
            
        Returns:
            Enriched value (e.g., "Houston, TX (LOC001)")
        """
        if not value:
            return value
        
        col_lower = column.lower()
        
        # Check if we have a lookup for this column
        for code_col, table_name in self.code_columns.items():
            if code_col in col_lower:
                lookup = self.lookups.get(table_name, {})
                description = lookup.get(str(value))
                if description:
                    return f"{description} ({value})"
        
        return value
    
    def enrich_results(self, rows: List[Dict], columns: List[str]) -> List[Dict]:
        """
        Enrich all values in a result set.
        
        Args:
            rows: List of result dictionaries
            columns: Column names
            
        Returns:
            Rows with enriched values
        """
        if not rows or not self.lookups:
            return rows
        
        enriched = []
        for row in rows:
            enriched_row = {}
            for col, val in row.items():
                enriched_row[col] = self.enrich_value(col, str(val) if val else '')
            enriched.append(enriched_row)
        
        return enriched
    
    def get_description(self, table: str, code: str) -> Optional[str]:
        """Get description for a specific code from a specific table."""
        lookup = self.lookups.get(table, {})
        return lookup.get(str(code))
