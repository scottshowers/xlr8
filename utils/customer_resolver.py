"""
CustomerResolver - The One Ring for Customer Identification
============================================================

This is the SINGLE SOURCE OF TRUTH for customer identification in XLR8.
Everything else delegates to it. No exceptions. No shortcuts.

RULES:
1. Customer.id (UUID) is the ONLY identifier used for:
   - DuckDB table prefixes
   - API calls
   - All internal references

2. Given ANY identifier (UUID, name, or legacy code), returns canonical customer context

3. EVERY file that needs customer identification imports this

Usage:
    from backend.utils.customer_resolver import CustomerResolver
    
    # Resolve any identifier to canonical form
    customer = CustomerResolver.resolve("Team Inc")
    customer = CustomerResolver.resolve("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    
    # Get DuckDB table prefix
    prefix = CustomerResolver.get_table_prefix(customer_id)  # Returns "a1b2c3d4"
    
    # Get all tables for a customer
    tables = CustomerResolver.get_tables(customer_id)

Author: XLR8 Team
Version: 1.0
Date: January 2026
"""

import re
import logging
from typing import Optional, Dict, Any, List, Tuple
from functools import lru_cache

logger = logging.getLogger(__name__)


class CustomerResolver:
    """Single source of truth for customer identification.
    
    Resolves any identifier (UUID, name, legacy code) to canonical customer data.
    Caches lookups for performance.
    """
    
    # UUID regex pattern
    UUID_PATTERN = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    
    # Short UUID pattern (first 8 chars, used in table names)
    SHORT_UUID_PATTERN = re.compile(r'^[0-9a-f]{8}$', re.IGNORECASE)
    
    @classmethod
    def resolve(cls, identifier: str) -> Optional[Dict[str, Any]]:
        """Resolve ANY identifier to canonical customer data.
        
        Args:
            identifier: Can be:
                - Full UUID: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
                - Customer name: "Team Inc"
                - Legacy project code: "TEA1000" (deprecated but supported)
        
        Returns:
            Customer dict with keys: id, name, status, metadata
            Or None if not found
        """
        if not identifier:
            return None
            
        identifier = str(identifier).strip()
        
        # Try cache first
        cached = cls._get_from_cache(identifier)
        if cached:
            return cached
        
        # Get Supabase client
        try:
            from utils.database.supabase_client import get_supabase
        except ImportError:
            from backend.utils.supabase_client import get_supabase
        
        supabase = get_supabase()
        if not supabase:
            logger.error("[CustomerResolver] Supabase not available")
            return None
        
        customer = None
        
        try:
            # Strategy 1: If it looks like a UUID, query by ID
            if cls.UUID_PATTERN.match(identifier):
                result = supabase.table('customers').select('*').eq('id', identifier).execute()
                if result.data:
                    customer = result.data[0]
            
            # Strategy 2: Query by name (case-insensitive)
            if not customer:
                result = supabase.table('customers').select('*').ilike('name', identifier).execute()
                if result.data:
                    customer = result.data[0]
            
            # Strategy 3: Query by legacy 'code' field (if exists in metadata)
            if not customer:
                result = supabase.table('customers').select('*').execute()
                for c in (result.data or []):
                    metadata = c.get('metadata', {}) or {}
                    if metadata.get('code', '').upper() == identifier.upper():
                        customer = c
                        break
            
            # Strategy 4: Query by legacy 'customer' field (backward compat)
            if not customer:
                result = supabase.table('customers').select('*').ilike('customer', identifier).execute()
                if result.data:
                    customer = result.data[0]
            
            # Cache the result
            if customer:
                cls._add_to_cache(identifier, customer)
                # Also cache by ID for faster subsequent lookups
                if customer.get('id') != identifier:
                    cls._add_to_cache(customer['id'], customer)
            
            return customer
            
        except Exception as e:
            logger.error(f"[CustomerResolver] Error resolving '{identifier}': {e}")
            return None
    
    @classmethod
    def get_table_prefix(cls, customer_id: str) -> str:
        """Get the DuckDB table prefix for a customer.
        
        Args:
            customer_id: Customer UUID
            
        Returns:
            First 8 characters of UUID, lowercase, no hyphens
            Example: "a1b2c3d4-e5f6-7890-abcd-ef1234567890" → "a1b2c3d4"
        """
        if not customer_id:
            return "unknown"
        return customer_id.replace('-', '')[:8].lower()
    
    @classmethod
    def get_tables(cls, customer_id: str) -> List[Dict[str, Any]]:
        """Get ALL tables for a customer from DuckDB.
        
        This is THE function to get tables. No other function should query
        DuckDB directly for table lists.
        
        Args:
            customer_id: Customer UUID
            
        Returns:
            List of table dicts with keys:
            - table_name: Internal DuckDB name
            - display_name: Human-readable name
            - columns: List of column names
            - row_count: Number of rows
            - source: 'upload' | 'api' | 'pdf'
            - filename: Original file name
            - sheet_name: Sheet name (for Excel)
        """
        try:
            from utils.structured_data_handler import get_structured_handler
        except ImportError:
            from backend.utils.structured_data_handler import get_structured_handler
        
        handler = get_structured_handler()
        if not handler:
            return []
        
        prefix = cls.get_table_prefix(customer_id)
        tables = []
        
        try:
            # Get all tables from DuckDB
            all_tables = handler.conn.execute("SHOW TABLES").fetchall()
            
            for (table_name,) in all_tables:
                # Skip system tables
                if table_name.startswith('_'):
                    continue
                
                # Must match customer prefix
                if not table_name.lower().startswith(prefix):
                    continue
                
                # Get columns
                columns = []
                try:
                    result = handler.conn.execute(f'SELECT * FROM "{table_name}" LIMIT 0')
                    columns = [desc[0] for desc in result.description]
                except Exception:
                    try:
                        col_result = handler.conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
                        columns = [row[1] for row in col_result]
                    except Exception as e:
                        logger.debug(f"Could not get columns for {table_name}: {e}")
                
                # Get row count
                row_count = 0
                try:
                    count_result = handler.conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()
                    row_count = count_result[0] if count_result else 0
                except Exception:
                    pass
                
                # Determine source type
                source = 'upload'
                if '_api_' in table_name.lower():
                    source = 'api'
                elif '_pdf_' in table_name.lower():
                    source = 'pdf'
                
                # Generate display name
                display_name = cls._generate_display_name(table_name, prefix)
                
                # Try to get additional metadata from _schema_metadata
                filename = None
                sheet_name = None
                try:
                    meta_result = handler.conn.execute("""
                        SELECT file_name, sheet_name 
                        FROM _schema_metadata 
                        WHERE table_name = ? AND is_current = TRUE
                        LIMIT 1
                    """, [table_name]).fetchone()
                    if meta_result:
                        filename, sheet_name = meta_result
                except Exception:
                    pass
                
                tables.append({
                    'table_name': table_name,
                    'display_name': display_name,
                    'columns': columns,
                    'row_count': row_count,
                    'source': source,
                    'filename': filename or display_name,
                    'sheet_name': sheet_name or 'Sheet1'
                })
            
            return sorted(tables, key=lambda t: t['display_name'].lower())
            
        except Exception as e:
            logger.error(f"[CustomerResolver] Error getting tables for {customer_id}: {e}")
            return []
    
    @classmethod
    def get_table_by_name(cls, customer_id: str, table_ref: str) -> Optional[Dict[str, Any]]:
        """Get a specific table by name or display name.
        
        Args:
            customer_id: Customer UUID
            table_ref: Table name (internal or display)
            
        Returns:
            Table dict or None
        """
        tables = cls.get_tables(customer_id)
        
        # Try exact match on table_name
        for t in tables:
            if t['table_name'].lower() == table_ref.lower():
                return t
        
        # Try exact match on display_name
        for t in tables:
            if t['display_name'].lower() == table_ref.lower():
                return t
        
        # Try partial match
        for t in tables:
            if table_ref.lower() in t['table_name'].lower():
                return t
            if table_ref.lower() in t['display_name'].lower():
                return t
        
        return None
    
    @classmethod
    def validate_access(cls, customer_id: str, table_name: str) -> bool:
        """Validate that a table belongs to a customer.
        
        Security check to prevent cross-customer data access.
        
        Args:
            customer_id: Customer UUID
            table_name: Table name to check
            
        Returns:
            True if table belongs to customer
        """
        if not customer_id or not table_name:
            return False
        
        prefix = cls.get_table_prefix(customer_id)
        return table_name.lower().startswith(prefix)
    
    @classmethod
    def _generate_display_name(cls, table_name: str, prefix: str) -> str:
        """Generate human-readable display name from table name.
        
        Args:
            table_name: Internal table name. Can be:
                - Short prefix: "a1b2c3d4_employees_personal"
                - Full UUID: "a1b2c3d4-e5f6-7890-abcd-ef1234567890_api_1099m"
            prefix: Customer prefix (e.g., "a1b2c3d4")
            
        Returns:
            Display name (e.g., "Employees Personal" or "API: 1099M")
        """
        name = table_name.lower()
        
        # Strategy 1: Remove full UUID prefix if present (with hyphens)
        # Pattern: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx_
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}_'
        match = re.match(uuid_pattern, name)
        if match:
            name = name[match.end():]
        # Strategy 2: Remove short prefix if present
        elif name.startswith(prefix.lower()):
            name = name[len(prefix):]
            name = name.lstrip('_')
        
        # Handle API tables
        if name.startswith('api_'):
            name = name[4:]
            # Title case the API endpoint name
            display = name.replace('_', ' ')
            words = display.split()
            titled = []
            for word in words:
                # Keep short uppercase words as-is (acronyms)
                if len(word) <= 4:
                    titled.append(word.upper())
                else:
                    titled.append(word.title())
            return f"API: {' '.join(titled)}"
        
        # Handle PDF tables
        if name.startswith('pdf_'):
            name = name[4:]
            display = name.replace('_', ' ')
            return f"PDF: {display.title()}"
        
        # Regular tables - replace underscores with spaces and title case
        name = name.replace('_', ' ')
        
        # Title case but preserve acronyms
        words = name.split()
        titled = []
        for word in words:
            if word.isupper() and len(word) <= 4:
                titled.append(word)  # Keep acronyms
            else:
                titled.append(word.title())
        
        return ' '.join(titled)
    
    # ==========================================================================
    # CACHING
    # ==========================================================================
    
    _cache: Dict[str, Dict[str, Any]] = {}
    _cache_max_size = 100
    
    @classmethod
    def _get_from_cache(cls, identifier: str) -> Optional[Dict[str, Any]]:
        """Get customer from cache."""
        return cls._cache.get(identifier.lower())
    
    @classmethod
    def _add_to_cache(cls, identifier: str, customer: Dict[str, Any]):
        """Add customer to cache."""
        # Simple LRU: if full, clear half
        if len(cls._cache) >= cls._cache_max_size:
            keys = list(cls._cache.keys())[:cls._cache_max_size // 2]
            for k in keys:
                cls._cache.pop(k, None)
        cls._cache[identifier.lower()] = customer
    
    @classmethod
    def clear_cache(cls):
        """Clear the customer cache."""
        cls._cache.clear()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def resolve_customer(identifier: str) -> Optional[Dict[str, Any]]:
    """Resolve any identifier to canonical customer data."""
    return CustomerResolver.resolve(identifier)

def get_customer_prefix(customer_id: str) -> str:
    """Get DuckDB table prefix for a customer."""
    return CustomerResolver.get_table_prefix(customer_id)

def get_customer_tables(customer_id: str) -> List[Dict[str, Any]]:
    """Get all tables for a customer."""
    return CustomerResolver.get_tables(customer_id)

def validate_customer_table_access(customer_id: str, table_name: str) -> bool:
    """Validate that a table belongs to a customer."""
    return CustomerResolver.validate_access(customer_id, table_name)
