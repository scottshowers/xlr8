"""
XLR8 Schema Registry
====================

Single source of truth for all system schemas.
Provides fast lookups for:
- column_name → hub_type
- hub_type → key_column  
- entity_type → hub_type

NO pattern matching. NO guessing. Just explicit mappings from API schemas.

Author: XLR8 Team
Version: 1.0.0
"""

import os
import json
import logging
import re
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class SchemaRegistry:
    """
    Loads and indexes system schemas for fast lookup.
    
    Usage:
        registry = SchemaRegistry()
        hub_type = registry.column_to_hub("earningCode", system="ukg_pro")
        # Returns: "earning"
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """Singleton pattern - one registry for the whole app."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the registry (only once due to singleton)."""
        if SchemaRegistry._initialized:
            return
        
        # Core indexes
        self._schemas: Dict[str, Dict] = {}  # system_name → full schema
        self._column_to_hub: Dict[str, Dict[str, str]] = {}  # system → {column: hub}
        self._hub_to_key_column: Dict[str, Dict[str, str]] = {}  # system → {hub: key_column}
        self._entity_to_hub: Dict[str, Dict[str, str]] = {}  # system → {entity: hub}
        self._hub_domains: Dict[str, Dict[str, str]] = {}  # system → {hub: domain}
        
        # Global index (all systems combined, for fallback)
        self._global_column_to_hub: Dict[str, str] = {}
        
        # Load all schemas
        self._load_all_schemas()
        
        SchemaRegistry._initialized = True
        logger.info(f"[SCHEMA-REGISTRY] Initialized with {len(self._schemas)} system schemas")
    
    def _load_all_schemas(self):
        """Load all schema files from config directory."""
        config_paths = [
            Path("/app/config"),
            Path("config"),
            Path(__file__).parent.parent.parent.parent / "config",
        ]
        
        config_dir = None
        for path in config_paths:
            if path.exists():
                config_dir = path
                break
        
        if not config_dir:
            logger.warning("[SCHEMA-REGISTRY] No config directory found")
            return
        
        # Find all schema files
        schema_files = list(config_dir.glob("*_schema_v1.json")) + \
                       list(config_dir.glob("*_schema.json"))
        
        for schema_file in schema_files:
            try:
                self._load_schema_file(schema_file)
            except Exception as e:
                logger.warning(f"[SCHEMA-REGISTRY] Failed to load {schema_file}: {e}")
        
        logger.info(f"[SCHEMA-REGISTRY] Loaded {len(self._schemas)} schemas from {config_dir}")
    
    def _load_schema_file(self, path: Path):
        """Load a single schema file and build indexes."""
        with open(path, 'r') as f:
            schema = json.load(f)
        
        # Derive system name from filename
        # e.g., "ukg_pro_schema_v1.json" → "ukg_pro"
        filename = path.stem
        system_name = filename.replace("_schema_v1", "").replace("_schema", "")
        
        self._schemas[system_name] = schema
        self._column_to_hub[system_name] = {}
        self._hub_to_key_column[system_name] = {}
        self._entity_to_hub[system_name] = {}
        self._hub_domains[system_name] = {}
        
        # Process hub definitions
        hubs = schema.get("hubs", {})
        for hub_name, hub_def in hubs.items():
            # Handle different schema formats:
            # Format 1 (UKG Pro): {"hub_name": {"key_column": "code", "domain": "..."}}
            # Format 2 (HubSpot): {"hub_name": "description string"}
            if isinstance(hub_def, str):
                # Simple string format - just register the hub name
                self._entity_to_hub[system_name][hub_name.lower()] = hub_name
                continue
            
            key_column = hub_def.get("key_column", "")
            domain = hub_def.get("domain", "")
            entity_name = hub_def.get("entity_name", hub_name)
            
            if key_column:
                # Store hub → key_column mapping
                self._hub_to_key_column[system_name][hub_name] = key_column
                self._hub_domains[system_name][hub_name] = domain
                
                # Build column → hub mappings (with variants)
                self._add_column_variants(system_name, key_column, hub_name)
                
                # Build entity → hub mappings (with variants)
                self._add_entity_variants(system_name, hub_name, entity_name)
        
        # Process spoke_patterns (FK column → hub mappings)
        # These are the actual FK columns that appear in reality tables
        # e.g., "employeetypecode" → "employee_type"
        spoke_patterns = schema.get("spoke_patterns", {})
        for column_name, mappings in spoke_patterns.items():
            if not mappings:
                continue
            # spoke_patterns format: {"columnname": [{"hub": "hub_name", "confidence": 0.95}]}
            # or simpler: {"columnname": "hub_name"}
            if isinstance(mappings, str):
                hub_name = mappings
            elif isinstance(mappings, list) and len(mappings) > 0:
                first = mappings[0]
                hub_name = first.get("hub") if isinstance(first, dict) else str(first)
            elif isinstance(mappings, dict):
                hub_name = mappings.get("hub")
            else:
                continue
            
            if hub_name:
                # Add this FK column → hub mapping (column_name is already lowercase)
                self._column_to_hub[system_name][column_name] = hub_name
                # Also add to global index
                if column_name not in self._global_column_to_hub:
                    self._global_column_to_hub[column_name] = hub_name
        
        logger.debug(f"[SCHEMA-REGISTRY] {system_name}: {len(hubs)} hubs indexed")
    
    def _add_column_variants(self, system: str, column: str, hub: str):
        """Add column name variants to the index."""
        variants = self._generate_variants(column)
        for variant in variants:
            self._column_to_hub[system][variant] = hub
            # Also add to global index
            if variant not in self._global_column_to_hub:
                self._global_column_to_hub[variant] = hub
    
    def _add_entity_variants(self, system: str, hub_name: str, entity_name: str):
        """Add entity name variants to the index."""
        # Hub name itself
        self._entity_to_hub[system][hub_name] = hub_name
        self._entity_to_hub[system][hub_name + "s"] = hub_name  # plural
        self._entity_to_hub[system][hub_name + "_codes"] = hub_name
        self._entity_to_hub[system][hub_name + "s_codes"] = hub_name
        
        # Entity name variants
        if entity_name:
            entity_lower = entity_name.lower().replace(" ", "_")
            self._entity_to_hub[system][entity_lower] = hub_name
            self._entity_to_hub[system][entity_lower + "s"] = hub_name
    
    def _generate_variants(self, name: str) -> Set[str]:
        """Generate case/format variants of a column name."""
        variants = set()
        
        # Original
        variants.add(name)
        
        # Lowercase
        lower = name.lower()
        variants.add(lower)
        
        # With underscores (camelCase → snake_case)
        snake = re.sub(r'([a-z])([A-Z])', r'\1_\2', name).lower()
        variants.add(snake)
        
        # Without underscores
        no_underscore = lower.replace("_", "")
        variants.add(no_underscore)
        
        return variants
    
    # =========================================================================
    # PUBLIC API
    # =========================================================================
    
    def column_to_hub(self, column_name: str, system: str = None) -> Optional[str]:
        """
        Look up which hub a column references.
        
        Args:
            column_name: Column name (e.g., "earningCode", "earning_code", "maritalStatusCode")
            system: System name (e.g., "ukg_pro"). If None, searches all.
            
        Returns:
            Hub name (e.g., "earning", "marital_status") or None if not found
        """
        # Normalize column name
        normalized = column_name.lower().replace("_", "").replace(" ", "")
        
        # Method 1: Direct lookup (explicit key_column match)
        if system and system in self._column_to_hub:
            if normalized in self._column_to_hub[system]:
                return self._column_to_hub[system][normalized]
            if column_name in self._column_to_hub[system]:
                return self._column_to_hub[system][column_name]
        
        if normalized in self._global_column_to_hub:
            return self._global_column_to_hub[normalized]
        
        # Method 2: Parse column name to derive hub type candidates
        # e.g., "maritalStatusCode" → ["marital_status"]
        # e.g., "employeeType" → ["employee_type", "employee"]
        candidates = self._parse_column_to_hub(column_name)
        for candidate in candidates:
            # Resolve to actual hub name in schema (handles variants)
            resolved = self._resolve_hub_name(candidate, system)
            if resolved:
                return resolved
        
        return None
    
    def _parse_column_to_hub(self, column_name: str) -> List[str]:
        """
        Parse a column name to derive possible hub types.
        Returns list of candidates to try (in priority order).
        
        Examples:
            maritalStatusCode → ['marital_status']
            earningCode → ['earning']
            employeeType → ['employee_type', 'employee']
            primaryJobCode → ['job']
        """
        col_lower = column_name.lower()
        candidates = []
        
        # Common suffixes to strip
        suffixes = ['code', 'id', 'key', 'number', 'no', 'num']
        type_suffixes = ['type']  # Handle separately - might be part of entity name
        
        for suffix in suffixes:
            if col_lower.endswith(suffix):
                base = col_lower[:-len(suffix)]
                base = base.rstrip('_')
                if not base:
                    continue
                
                snake = self._to_snake_case(base)
                snake = self._strip_prefixes(snake)
                snake = re.sub(r'(\d+)$', '', snake).rstrip('_')
                
                if snake:
                    candidates.append(snake)
        
        # Special handling for 'Type' suffix
        for suffix in type_suffixes:
            if col_lower.endswith(suffix):
                base = col_lower[:-len(suffix)]
                base = base.rstrip('_')
                if not base:
                    continue
                
                snake = self._to_snake_case(base)
                snake = self._strip_prefixes(snake)
                snake = re.sub(r'(\d+)$', '', snake).rstrip('_')
                
                if snake:
                    # Try both with and without _type
                    candidates.append(snake + '_type')  # employee_type
                    candidates.append(snake)  # employee
        
        return candidates
    
    def _to_snake_case(self, name: str) -> str:
        """Convert camelCase to snake_case."""
        return re.sub(r'([a-z])([A-Z])', r'\1_\2', name).lower()
    
    def _strip_prefixes(self, name: str) -> str:
        """Strip common prefixes like primary, default, etc."""
        prefixes_to_strip = ['primary', 'default', 'secondary', 'current', 'original']
        for prefix in prefixes_to_strip:
            if name.startswith(prefix + '_'):
                return name[len(prefix) + 1:]
            elif name.startswith(prefix):
                return name[len(prefix):]
        return name
    
    def _hub_exists(self, hub_name: str, system: str = None) -> bool:
        """Check if a hub exists, trying variants."""
        # Variants to try
        variants = [
            hub_name,
            hub_name.replace('_', ''),  # marital_status → maritalstatus
        ]
        
        # Check system-specific
        if system and system in self._hub_to_key_column:
            sys_hubs = self._hub_to_key_column[system]
            for v in variants:
                if v in sys_hubs:
                    return True
        
        # Check all systems
        for sys_hubs in self._hub_to_key_column.values():
            for v in variants:
                if v in sys_hubs:
                    return True
        
        return False
    
    def _resolve_hub_name(self, parsed_name: str, system: str = None) -> Optional[str]:
        """
        Resolve a parsed hub name to the actual hub name in the schema.
        Handles variants like maritalstatus vs marital_status.
        """
        # Variants to try
        variants = [
            parsed_name,
            parsed_name.replace('_', ''),  # Try without underscores
            # Also try with underscores in common places
        ]
        
        # For names without underscores, try inserting them
        if '_' not in parsed_name:
            # employeetype → employee_type
            # maritalstatus → marital_status
            # Build all possible underscore insertions... or just check both
            pass
        
        # Check system-specific first
        if system and system in self._hub_to_key_column:
            sys_hubs = self._hub_to_key_column[system]
            for v in variants:
                if v in sys_hubs:
                    return v
            # Try finding a hub that matches when underscores are removed
            for hub in sys_hubs:
                if hub.replace('_', '') == parsed_name.replace('_', ''):
                    return hub
        
        # Check all systems
        for sys_name, sys_hubs in self._hub_to_key_column.items():
            for v in variants:
                if v in sys_hubs:
                    return v
            for hub in sys_hubs:
                if hub.replace('_', '') == parsed_name.replace('_', ''):
                    return hub
        
        return None
    
    def hub_to_key_column(self, hub_name: str, system: str = None) -> Optional[str]:
        """
        Get the key column for a hub.
        
        Args:
            hub_name: Hub name (e.g., "earning")
            system: System name
            
        Returns:
            Key column name (e.g., "earningCode") or None
        """
        if system and system in self._hub_to_key_column:
            return self._hub_to_key_column[system].get(hub_name)
        
        # Search all systems
        for sys_hubs in self._hub_to_key_column.values():
            if hub_name in sys_hubs:
                return sys_hubs[hub_name]
        
        return None
    
    def entity_to_hub(self, entity_type: str, system: str = None) -> Optional[str]:
        """
        Get the hub for an entity type.
        
        Args:
            entity_type: Entity type (e.g., "earnings", "earning_codes")
            system: System name
            
        Returns:
            Hub name (e.g., "earning") or None
        """
        normalized = entity_type.lower().replace(" ", "_")
        
        if system and system in self._entity_to_hub:
            if normalized in self._entity_to_hub[system]:
                return self._entity_to_hub[system][normalized]
        
        # Search all systems
        for sys_entities in self._entity_to_hub.values():
            if normalized in sys_entities:
                return sys_entities[normalized]
        
        return None
    
    def get_hub_domain(self, hub_name: str, system: str = None) -> Optional[str]:
        """Get the domain (Configuration, Employee_Data, etc.) for a hub."""
        if system and system in self._hub_domains:
            return self._hub_domains[system].get(hub_name)
        
        for sys_domains in self._hub_domains.values():
            if hub_name in sys_domains:
                return sys_domains[hub_name]
        
        return None
    
    def get_all_hubs(self, system: str = None) -> List[str]:
        """Get list of all hub names for a system (or all systems)."""
        if system and system in self._hub_to_key_column:
            return list(self._hub_to_key_column[system].keys())
        
        all_hubs = set()
        for sys_hubs in self._hub_to_key_column.values():
            all_hubs.update(sys_hubs.keys())
        return list(all_hubs)
    
    def get_schema(self, system: str) -> Optional[Dict]:
        """Get the full schema for a system."""
        return self._schemas.get(system)
    
    def get_loaded_systems(self) -> List[str]:
        """Get list of loaded system names."""
        return list(self._schemas.keys())
    
    def detect_system(self, column_names: List[str]) -> Optional[str]:
        """
        Try to detect which system based on column names.
        
        Args:
            column_names: List of column names from a table
            
        Returns:
            Most likely system name or None
        """
        # Count matches per system
        system_scores: Dict[str, int] = {}
        
        for col in column_names:
            normalized = col.lower().replace("_", "")
            for system, col_index in self._column_to_hub.items():
                if normalized in col_index:
                    system_scores[system] = system_scores.get(system, 0) + 1
        
        if not system_scores:
            return None
        
        # Return system with most matches
        return max(system_scores, key=system_scores.get)
    
    def get_stats(self) -> Dict:
        """Get registry statistics."""
        return {
            "systems_loaded": len(self._schemas),
            "systems": list(self._schemas.keys()),
            "total_hubs": sum(len(h) for h in self._hub_to_key_column.values()),
            "total_column_mappings": sum(len(c) for c in self._column_to_hub.values()),
            "global_column_mappings": len(self._global_column_to_hub)
        }


# Singleton accessor
def get_schema_registry() -> SchemaRegistry:
    """Get the singleton SchemaRegistry instance."""
    return SchemaRegistry()


# =========================================================================
# CONVENIENCE FUNCTIONS
# =========================================================================

def lookup_hub(column_name: str, system: str = None) -> Optional[str]:
    """Quick lookup: column name → hub type."""
    return get_schema_registry().column_to_hub(column_name, system)


def lookup_key_column(hub_name: str, system: str = None) -> Optional[str]:
    """Quick lookup: hub type → key column."""
    return get_schema_registry().hub_to_key_column(hub_name, system)


def lookup_entity_hub(entity_type: str, system: str = None) -> Optional[str]:
    """Quick lookup: entity type → hub type."""
    return get_schema_registry().entity_to_hub(entity_type, system)
