"""
XLR8 Product Registry
=====================
Phase 5B: Central registry of all supported products.

Loads schemas from config/, normalizes them, and provides lookup methods.
This is the foundation for multi-product support.

Usage:
    from backend.utils.products import get_registry
    
    registry = get_registry()
    
    # Get a specific product
    product = registry.get_product('workday_hcm')
    
    # List by category
    hcm_products = registry.list_by_category('HCM')
    
    # List by vendor
    ukg_products = registry.list_by_vendor('UKG')
    
    # Get all domains for a product
    domains = registry.get_domains('ukg_pro')

Deploy to: backend/utils/products/registry.py
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


# =============================================================================
# CATEGORY CLASSIFICATION
# =============================================================================

# Keywords to auto-detect category from product info
CATEGORY_KEYWORDS = {
    'HCM': [
        'hcm', 'hr', 'human capital', 'payroll', 'workforce', 'employee',
        'talent', 'recruiting', 'benefits', 'time tracking', 'attendance',
        'compensation', 'performance', 'learning', 'onboarding'
    ],
    'FINS': [
        'financials', 'finance', 'accounting', 'general ledger', 'ap', 'ar',
        'accounts payable', 'accounts receivable', 'billing', 'invoicing',
        'expense', 'budgeting', 'treasury', 'tax'
    ],
    'ERP': [
        'erp', 'enterprise resource', 'manufacturing', 'inventory', 
        'supply chain', 'procurement', 'warehouse', 'logistics',
        'production', 'planning', 'mrp', 'distribution'
    ],
    'CRM': [
        'crm', 'customer', 'sales', 'marketing', 'service', 'support',
        'leads', 'opportunities', 'pipeline', 'campaigns', 'contacts'
    ],
    'Collaboration': [
        'project', 'task', 'collaboration', 'communication', 'messaging',
        'teams', 'workspace', 'productivity', 'documents', 'wiki'
    ],
    'Benefits_Admin': [
        'benefits administration', 'enrollment', 'cobra', 'aca', 'ppaca',
        'open enrollment', 'carrier', 'plan administration'
    ],
}

# Explicit vendor → category mappings for known products
VENDOR_CATEGORY_MAP = {
    # HCM vendors
    'UKG': 'HCM',
    'Workday': 'HCM',  # Default, but Workday FINS exists
    'ADP': 'HCM',
    'Ceridian': 'HCM',
    'Paylocity': 'HCM',
    'Paycom': 'HCM',
    'Paychex': 'HCM',
    'Paycor': 'HCM',
    'BambooHR': 'HCM',
    'Namely': 'HCM',
    'Gusto': 'HCM',
    'Rippling': 'HCM',
    'Deel': 'HCM',
    'HiBob': 'HCM',
    'isolved': 'HCM',
    'TriNet': 'HCM',
    'Zenefits': 'HCM',
    
    # FINS/ERP vendors
    'SAP': 'ERP',
    'Oracle': 'FINS',  # NetSuite is FINS, Fusion HCM is HCM
    'Intuit': 'FINS',
    'Sage': 'FINS',
    'Xero': 'FINS',
    'Microsoft': 'ERP',  # D365 could be ERP or CRM
    
    # CRM vendors
    'Salesforce': 'CRM',  # Except Slack
    'HubSpot': 'CRM',
    'Pipedrive': 'CRM',
    'Freshworks': 'CRM',
    'Zoho': 'CRM',
    
    # Collaboration vendors
    'Atlassian': 'Collaboration',
    'Asana': 'Collaboration',
    'Monday.com': 'Collaboration',
    'ClickUp': 'Collaboration',
    'Notion': 'Collaboration',
    'Smartsheet': 'Collaboration',
    
    # Benefits-specific
    'PlanSource': 'Benefits_Admin',
}

# Product-specific overrides (when vendor default isn't right)
PRODUCT_CATEGORY_OVERRIDES = {
    # FINS products
    'workday_fins': 'FINS',
    'netsuite': 'FINS',
    'quickbooks': 'FINS',
    'xero': 'FINS',
    'sage_intacct': 'FINS',
    
    # HCM products (override vendor defaults)
    'oracle_hcm': 'HCM',
    'successfactors': 'HCM',
    
    # ERP products
    'dynamics365': 'ERP',
    's4hana': 'ERP',
    
    # CRM products
    'dynamics_crm': 'CRM',
    'salesforce': 'CRM',
    'hubspot': 'CRM',
    'pipedrive': 'CRM',
    'freshsales': 'CRM',
    'zoho_crm': 'CRM',
    
    # Collaboration products
    'slack': 'Collaboration',
    'smartsheet': 'Collaboration',
    'notion': 'Collaboration',
    'asana': 'Collaboration',
    'jira': 'Collaboration',
    'clickup': 'Collaboration',
    'monday': 'Collaboration',
    'teams': 'Collaboration',
}


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ProductDomain:
    """A domain within a product (e.g., Compensation, Benefits)."""
    name: str
    description: str
    hub_count: int
    hubs: List[str]


@dataclass 
class ProductSchema:
    """Complete schema for a product."""
    product_id: str          # e.g., 'ukg_pro', 'workday_hcm'
    vendor: str              # e.g., 'UKG', 'Workday'
    product: str             # e.g., 'UKG Pro', 'HCM'
    category: str            # e.g., 'HCM', 'FINS', 'CRM'
    version: str
    source: str
    extracted: str
    
    # API info
    api_types: List[str] = field(default_factory=list)
    product_focus: str = ''
    
    # Structure
    domains: Dict[str, ProductDomain] = field(default_factory=dict)
    hubs: Dict[str, Dict] = field(default_factory=dict)
    
    # Total counts
    domain_count: int = 0
    hub_count: int = 0
    
    # Extra metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def all_hub_names(self) -> List[str]:
        """Get flat list of all hub names."""
        return list(self.hubs.keys())
    
    def get_hubs_for_domain(self, domain: str) -> List[str]:
        """Get hub names for a specific domain."""
        if domain in self.domains:
            return self.domains[domain].hubs
        return []
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'product_id': self.product_id,
            'vendor': self.vendor,
            'product': self.product,
            'category': self.category,
            'version': self.version,
            'domain_count': self.domain_count,
            'hub_count': self.hub_count,
            'domains': {
                name: {
                    'description': d.description,
                    'hub_count': d.hub_count,
                    'hubs': d.hubs
                }
                for name, d in self.domains.items()
            },
            'api_types': self.api_types,
            'product_focus': self.product_focus,
        }


# =============================================================================
# REGISTRY
# =============================================================================

class ProductRegistry:
    """
    Central registry of all supported products.
    
    Loads schemas from config directory, normalizes them,
    and provides lookup methods.
    """
    
    def __init__(self, config_dir: str = None):
        """
        Initialize the registry.
        
        Args:
            config_dir: Path to config directory with schema files.
                       Defaults to project config/ directory.
        """
        if config_dir is None:
            # Find config dir relative to this file
            this_dir = Path(__file__).parent
            config_dir = this_dir.parent.parent.parent / 'config'
        
        self.config_dir = Path(config_dir)
        self.products: Dict[str, ProductSchema] = {}
        self._loaded = False
        
        logger.info(f"[REGISTRY] Initialized with config_dir={self.config_dir}")
    
    def load(self, force: bool = False) -> int:
        """
        Load all schemas from config directory.
        
        Args:
            force: Force reload even if already loaded
            
        Returns:
            Number of products loaded
        """
        if self._loaded and not force:
            return len(self.products)
        
        self.products = {}
        
        if not self.config_dir.exists():
            logger.warning(f"[REGISTRY] Config dir not found: {self.config_dir}")
            return 0
        
        # Find all schema files
        schema_files = list(self.config_dir.glob('*_schema_*.json'))
        
        for schema_file in schema_files:
            try:
                product = self._load_schema_file(schema_file)
                if product:
                    self.products[product.product_id] = product
                    logger.debug(f"[REGISTRY] Loaded: {product.product_id}")
            except Exception as e:
                logger.warning(f"[REGISTRY] Failed to load {schema_file.name}: {e}")
        
        self._loaded = True
        logger.info(f"[REGISTRY] Loaded {len(self.products)} products")
        
        return len(self.products)
    
    def _load_schema_file(self, path: Path) -> Optional[ProductSchema]:
        """Load and normalize a single schema file."""
        with open(path) as f:
            data = json.load(f)
        
        # Derive product_id from filename
        product_id = path.stem.replace('_schema_v1', '').replace('_schema_v2', '') \
                              .replace('_schema_v3', '').replace('_schema_v4', '') \
                              .replace('_schema', '')
        
        # Skip files that aren't product schemas
        if product_id in ('pdf_patterns', 'ukg_vocabulary_seed', 'ukg_family_unified_vocabulary'):
            return None
        
        # Get vendor and product
        vendor = data.get('vendor', '')
        product = data.get('product', '')
        
        # Handle missing vendor/product (old format)
        if not vendor or vendor == 'NO_VENDOR':
            vendor = self._infer_vendor(product_id)
        if not product or product == 'NO_PRODUCT':
            product = self._infer_product(product_id)
        
        # Determine category
        category = self._determine_category(product_id, vendor, product, data)
        
        # Build domains
        domains = {}
        raw_domains = data.get('domains', {})
        
        for domain_name, domain_data in raw_domains.items():
            if isinstance(domain_data, dict):
                domains[domain_name] = ProductDomain(
                    name=domain_name,
                    description=domain_data.get('description', ''),
                    hub_count=domain_data.get('hub_count', len(domain_data.get('hubs', []))),
                    hubs=domain_data.get('hubs', [])
                )
        
        # Get hubs
        hubs = data.get('hubs', {})
        
        # If no domains but has hubs, create a single domain
        if not domains and hubs:
            domains['All'] = ProductDomain(
                name='All',
                description='All hubs (uncategorized)',
                hub_count=len(hubs),
                hubs=list(hubs.keys())
            )
        
        return ProductSchema(
            product_id=product_id,
            vendor=vendor,
            product=product,
            category=category,
            version=data.get('version', '1.0'),
            source=data.get('source', ''),
            extracted=data.get('extracted', ''),
            api_types=data.get('api_types', [data.get('api_type', '')]) if data.get('api_type') else data.get('api_types', []),
            product_focus=data.get('product_focus', ''),
            domains=domains,
            hubs=hubs,
            domain_count=len(domains),
            hub_count=len(hubs),
            metadata={
                'source_file': path.name,
                'xlr8_compatible': data.get('xlr8_compatible', False),
            }
        )
    
    def _infer_vendor(self, product_id: str) -> str:
        """Infer vendor from product_id."""
        product_lower = product_id.lower()
        
        if 'ukg' in product_lower:
            return 'UKG'
        if 'workday' in product_lower:
            return 'Workday'
        if 'adp' in product_lower:
            return 'ADP'
        if 'oracle' in product_lower or 'netsuite' in product_lower:
            return 'Oracle'
        if 'sap' in product_lower or 's4hana' in product_lower or 'successfactors' in product_lower:
            return 'SAP'
        if 'dynamics' in product_lower:
            return 'Microsoft'
        if 'salesforce' in product_lower:
            return 'Salesforce'
        
        # Default: capitalize product_id
        return product_id.split('_')[0].title()
    
    def _infer_product(self, product_id: str) -> str:
        """Infer product name from product_id."""
        # Convert underscores to spaces and title case
        return product_id.replace('_', ' ').title()
    
    def _determine_category(self, product_id: str, vendor: str, 
                           product: str, data: Dict) -> str:
        """Determine product category (HCM, FINS, CRM, etc.)."""
        # Check explicit overrides first
        if product_id in PRODUCT_CATEGORY_OVERRIDES:
            return PRODUCT_CATEGORY_OVERRIDES[product_id]
        
        # Check if category is in the data
        if 'category' in data:
            return data['category']
        
        # Check product focus for keywords
        focus = (data.get('product_focus', '') + ' ' + product).lower()
        
        for category, keywords in CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in focus:
                    return category
        
        # Fall back to vendor default
        if vendor in VENDOR_CATEGORY_MAP:
            return VENDOR_CATEGORY_MAP[vendor]
        
        return 'Other'
    
    # =========================================================================
    # LOOKUP METHODS
    # =========================================================================
    
    def get_product(self, product_id: str) -> Optional[ProductSchema]:
        """Get a product by ID."""
        self.load()
        return self.products.get(product_id)
    
    def list_all(self) -> List[ProductSchema]:
        """List all products."""
        self.load()
        return list(self.products.values())
    
    def list_by_category(self, category: str) -> List[ProductSchema]:
        """List products by category (HCM, FINS, CRM, etc.)."""
        self.load()
        return [p for p in self.products.values() if p.category == category]
    
    def list_by_vendor(self, vendor: str) -> List[ProductSchema]:
        """List products by vendor."""
        self.load()
        return [p for p in self.products.values() 
                if p.vendor.lower() == vendor.lower()]
    
    def get_categories(self) -> List[str]:
        """Get list of all categories."""
        self.load()
        return sorted(set(p.category for p in self.products.values()))
    
    def get_vendors(self) -> List[str]:
        """Get list of all vendors."""
        self.load()
        return sorted(set(p.vendor for p in self.products.values()))
    
    def get_domains(self, product_id: str) -> Dict[str, ProductDomain]:
        """Get domains for a product."""
        product = self.get_product(product_id)
        return product.domains if product else {}
    
    def get_hubs(self, product_id: str) -> Dict[str, Dict]:
        """Get hubs for a product."""
        product = self.get_product(product_id)
        return product.hubs if product else {}
    
    def search_products(self, query: str) -> List[ProductSchema]:
        """Search products by name, vendor, or category."""
        self.load()
        query_lower = query.lower()
        results = []
        
        for product in self.products.values():
            if (query_lower in product.product_id.lower() or
                query_lower in product.vendor.lower() or
                query_lower in product.product.lower() or
                query_lower in product.category.lower()):
                results.append(product)
        
        return results
    
    def summary(self) -> Dict:
        """Get summary statistics."""
        self.load()
        
        by_category = {}
        for p in self.products.values():
            by_category[p.category] = by_category.get(p.category, 0) + 1
        
        by_vendor = {}
        for p in self.products.values():
            by_vendor[p.vendor] = by_vendor.get(p.vendor, 0) + 1
        
        return {
            'total_products': len(self.products),
            'by_category': by_category,
            'by_vendor': by_vendor,
            'total_hubs': sum(p.hub_count for p in self.products.values()),
        }


# =============================================================================
# SINGLETON & CONVENIENCE FUNCTIONS
# =============================================================================

_registry_instance: Optional[ProductRegistry] = None


def get_registry(config_dir: str = None) -> ProductRegistry:
    """Get the singleton registry instance."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ProductRegistry(config_dir)
    return _registry_instance


def get_product(product_id: str) -> Optional[ProductSchema]:
    """Get a product by ID."""
    return get_registry().get_product(product_id)


def list_products_by_category(category: str) -> List[ProductSchema]:
    """List products by category."""
    return get_registry().list_by_category(category)


def list_products_by_vendor(vendor: str) -> List[ProductSchema]:
    """List products by vendor."""
    return get_registry().list_by_vendor(vendor)
