"""
XLR8 Vocabulary Normalizer
==========================
Phase 5C: Cross-product vocabulary normalization.

Extracts domain → entity mappings from schemas to replace
hardcoded DOMAIN_TO_ENTITY and ENTITY_SYNONYMS in term_index.py.

This enables queries like "show me employees" to work across:
- UKG Pro (personal table, employee_number semantic type)
- Workday (worker table)
- SAP (person table)

Usage:
    from backend.utils.products import get_vocabulary_normalizer
    
    normalizer = get_vocabulary_normalizer()
    
    # Normalize a term to canonical form
    canonical = normalizer.normalize('workers')  # → 'employee'
    
    # Get product-specific term
    ukg_term = normalizer.denormalize('employee', 'ukg_pro')  # → 'personal'
    
    # Find domain for a query term
    domain = normalizer.get_domain_for_term('payroll')  # → 'Compensation'

Deploy to: backend/utils/products/vocabulary.py
"""

import logging
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

from .registry import get_registry, ProductSchema

logger = logging.getLogger(__name__)


# =============================================================================
# UNIVERSAL VOCABULARY
# =============================================================================

# Universal entity types that exist across products
UNIVERSAL_ENTITIES = {
    # People entities
    'employee': {
        'description': 'Worker/employee in the organization',
        'synonyms': [
            'employees', 'worker', 'workers', 'person', 'persons', 'people',
            'staff', 'personnel', 'team', 'member', 'members', 'headcount',
            'associate', 'associates', 'contingent', 'contractor'
        ],
        'domains': ['Worker_Core', 'Worker_Demographics', 'Demographics', 'Core_HR'],
    },
    
    # Organization entities
    'organization': {
        'description': 'Organizational structure (company, department, location)',
        'synonyms': [
            'org', 'company', 'companies', 'department', 'departments',
            'division', 'divisions', 'unit', 'units', 'location', 'locations',
            'site', 'sites', 'branch', 'branches', 'subsidiary', 'entity'
        ],
        'domains': ['Organization', 'Org_Structure', 'Company'],
    },
    
    # Job entities
    'job': {
        'description': 'Job/position information',
        'synonyms': [
            'jobs', 'position', 'positions', 'role', 'roles', 'title', 'titles',
            'job code', 'job codes', 'occupation', 'function'
        ],
        'domains': ['Job_Position', 'Position', 'Job_Profile', 'Position_Staffing'],
    },
    
    # Compensation entities
    'compensation': {
        'description': 'Pay, earnings, salary information',
        'synonyms': [
            'pay', 'earnings', 'earning', 'salary', 'salaries', 'wage', 'wages',
            'payroll', 'compensation', 'income', 'stipend', 'bonus', 'bonuses'
        ],
        'domains': ['Compensation', 'Payroll', 'Earnings', 'Pay'],
    },
    
    # Deductions entities
    'deduction': {
        'description': 'Payroll deductions',
        'synonyms': [
            'deductions', 'withholding', 'withholdings', 'garnishment',
            'garnishments', 'contribution', 'contributions'
        ],
        'domains': ['Deductions', 'Deduction'],
    },
    
    # Benefits entities
    'benefits': {
        'description': 'Employee benefits (insurance, retirement, etc.)',
        'synonyms': [
            'benefit', 'insurance', 'medical', 'dental', 'vision', 'health',
            '401k', 'retirement', 'pension', 'hsa', 'fsa', 'cobra', 'aca',
            'enrollment', 'coverage', 'plan', 'plans'
        ],
        'domains': ['Benefits', 'Benefit', 'Benefits_Admin'],
    },
    
    # Tax entities
    'tax': {
        'description': 'Tax-related information',
        'synonyms': [
            'taxes', 'taxation', 'withholding', 'w2', 'w4', 'tax code',
            'tax codes', 'futa', 'suta', 'fica', 'federal', 'state tax'
        ],
        'domains': ['Taxes', 'Tax', 'Tax_Management'],
    },
    
    # Time entities
    'time': {
        'description': 'Time tracking, attendance, scheduling',
        'synonyms': [
            'time', 'timekeeping', 'attendance', 'scheduling', 'schedule',
            'schedules', 'shift', 'shifts', 'clock', 'punch', 'hours'
        ],
        'domains': ['Time_Attendance', 'Time_Leave', 'Time', 'Workforce_Management'],
    },
    
    # Leave entities
    'leave': {
        'description': 'Leave/PTO management',
        'synonyms': [
            'leave', 'pto', 'vacation', 'sick', 'absence', 'absences',
            'time off', 'accrual', 'accruals', 'holiday', 'holidays'
        ],
        'domains': ['Time_Leave', 'Leave', 'Absence'],
    },
    
    # --- FINS/ERP Entities ---
    
    # General Ledger entities
    'account': {
        'description': 'GL accounts and chart of accounts',
        'synonyms': [
            'accounts', 'gl', 'general ledger', 'chart of accounts', 'coa',
            'ledger', 'ledger account', 'gl account'
        ],
        'domains': ['General_Ledger', 'GL', 'Accounting'],
    },
    
    # AP entities
    'vendor': {
        'description': 'Vendors/suppliers (AP)',
        'synonyms': [
            'vendors', 'supplier', 'suppliers', 'payee', 'payees',
            'accounts payable', 'ap'
        ],
        'domains': ['Accounts_Payable', 'AP', 'Procurement', 'Vendor'],
    },
    
    # AR entities
    'customer': {
        'description': 'Customers (AR/CRM)',
        'synonyms': [
            'customers', 'client', 'clients', 'account', 'accounts',
            'accounts receivable', 'ar', 'buyer', 'buyers'
        ],
        'domains': ['Accounts_Receivable', 'AR', 'Customer', 'CRM'],
    },
    
    # Transaction entities
    'invoice': {
        'description': 'Invoices and billing',
        'synonyms': [
            'invoices', 'bill', 'bills', 'billing', 'receipt', 'receipts'
        ],
        'domains': ['Accounts_Receivable', 'Accounts_Payable', 'Billing'],
    },
    
    # --- CRM Entities ---
    
    'opportunity': {
        'description': 'Sales opportunities',
        'synonyms': [
            'opportunities', 'deal', 'deals', 'pipeline', 'prospect', 'prospects'
        ],
        'domains': ['Sales', 'CRM', 'Opportunity'],
    },
    
    'lead': {
        'description': 'Sales leads',
        'synonyms': [
            'leads', 'prospect', 'prospects', 'inquiry', 'inquiries'
        ],
        'domains': ['Sales', 'CRM', 'Lead', 'Marketing'],
    },
    
    'contact': {
        'description': 'Contacts (CRM)',
        'synonyms': [
            'contacts', 'person', 'people', 'stakeholder', 'stakeholders'
        ],
        'domains': ['CRM', 'Contact', 'Customer'],
    },
}

# Domain → primary entity mapping
DOMAIN_TO_PRIMARY_ENTITY = {
    # HCM domains
    'Worker_Core': 'employee',
    'Worker_Demographics': 'employee',
    'Demographics': 'employee',
    'Core_HR': 'employee',
    'Personal': 'employee',
    
    'Organization': 'organization',
    'Org_Structure': 'organization',
    'Company': 'organization',
    
    'Job_Position': 'job',
    'Position': 'job',
    'Job_Profile': 'job',
    'Position_Staffing': 'job',
    
    'Compensation': 'compensation',
    'Payroll': 'compensation',
    'Earnings': 'compensation',
    'Pay': 'compensation',
    
    'Deductions': 'deduction',
    'Deduction': 'deduction',
    
    'Benefits': 'benefits',
    'Benefit': 'benefits',
    'Benefits_Admin': 'benefits',
    
    'Taxes': 'tax',
    'Tax': 'tax',
    'Tax_Management': 'tax',
    
    'Time_Attendance': 'time',
    'Time_Leave': 'leave',
    'Time': 'time',
    'Workforce_Management': 'time',
    'Leave': 'leave',
    'Absence': 'leave',
    
    # FINS domains
    'General_Ledger': 'account',
    'GL': 'account',
    'Accounting': 'account',
    
    'Accounts_Payable': 'vendor',
    'AP': 'vendor',
    'Procurement': 'vendor',
    'Vendor': 'vendor',
    
    'Accounts_Receivable': 'customer',
    'AR': 'customer',
    
    'Billing': 'invoice',
    
    # CRM domains
    'Sales': 'opportunity',
    'CRM': 'contact',
    'Marketing': 'lead',
    'Lead': 'lead',
    'Opportunity': 'opportunity',
    'Contact': 'contact',
    'Customer': 'customer',
}


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class VocabularyMapping:
    """Mapping from term to canonical entity."""
    term: str
    canonical_entity: str
    domains: List[str]
    confidence: float = 1.0
    source: str = 'universal'  # 'universal', 'schema', 'inferred'


@dataclass
class ProductVocabulary:
    """Product-specific vocabulary."""
    product_id: str
    
    # Domain → hub mappings for this product
    domain_hubs: Dict[str, List[str]] = field(default_factory=dict)
    
    # Entity → preferred hub for this product
    entity_hub: Dict[str, str] = field(default_factory=dict)
    
    # Term → semantic type for this product
    term_semantic_types: Dict[str, str] = field(default_factory=dict)


# =============================================================================
# VOCABULARY NORMALIZER
# =============================================================================

class VocabularyNormalizer:
    """
    Normalizes vocabulary across products.
    
    Replaces hardcoded DOMAIN_TO_ENTITY and ENTITY_SYNONYMS
    with schema-driven lookups.
    """
    
    def __init__(self):
        """Initialize the normalizer."""
        self.registry = get_registry()
        
        # Build reverse lookup: synonym → canonical entity
        self._term_to_entity: Dict[str, str] = {}
        self._term_to_domains: Dict[str, List[str]] = {}
        
        # Build from universal vocabulary
        for entity, info in UNIVERSAL_ENTITIES.items():
            # Map entity itself
            self._term_to_entity[entity] = entity
            self._term_to_domains[entity] = info['domains']
            
            # Map all synonyms
            for synonym in info['synonyms']:
                self._term_to_entity[synonym.lower()] = entity
                self._term_to_domains[synonym.lower()] = info['domains']
        
        # Product-specific vocabularies (loaded on demand)
        self._product_vocab: Dict[str, ProductVocabulary] = {}
        
        logger.info(f"[VOCABULARY] Initialized with {len(self._term_to_entity)} terms")
    
    def normalize(self, term: str) -> Optional[str]:
        """
        Normalize a term to its canonical entity.
        
        Args:
            term: User term (e.g., 'workers', 'payroll', 'staff')
            
        Returns:
            Canonical entity (e.g., 'employee', 'compensation') or None
        """
        return self._term_to_entity.get(term.lower())
    
    def get_domain_for_term(self, term: str) -> Optional[str]:
        """
        Get the primary domain for a term.
        
        Args:
            term: User term
            
        Returns:
            Primary domain name or None
        """
        domains = self._term_to_domains.get(term.lower(), [])
        return domains[0] if domains else None
    
    def get_domains_for_term(self, term: str) -> List[str]:
        """Get all domains associated with a term."""
        return self._term_to_domains.get(term.lower(), [])
    
    def get_entity_for_domain(self, domain: str) -> Optional[str]:
        """
        Get the primary entity for a domain.
        
        Args:
            domain: Domain name (e.g., 'Compensation', 'Worker_Core')
            
        Returns:
            Primary entity (e.g., 'compensation', 'employee')
        """
        return DOMAIN_TO_PRIMARY_ENTITY.get(domain)
    
    def denormalize(self, entity: str, product_id: str) -> Optional[str]:
        """
        Convert canonical entity to product-specific term.
        
        Args:
            entity: Canonical entity (e.g., 'employee')
            product_id: Product ID (e.g., 'ukg_pro', 'workday_hcm')
            
        Returns:
            Product-specific hub/table name or None
        """
        vocab = self._get_product_vocab(product_id)
        if vocab and entity in vocab.entity_hub:
            return vocab.entity_hub[entity]
        return None
    
    def get_hubs_for_entity(self, entity: str, product_id: str) -> List[str]:
        """
        Get all hubs related to an entity for a product.
        
        Args:
            entity: Canonical entity
            product_id: Product ID
            
        Returns:
            List of hub names
        """
        vocab = self._get_product_vocab(product_id)
        if not vocab:
            return []
        
        # Get domains for this entity
        entity_info = UNIVERSAL_ENTITIES.get(entity, {})
        domains = entity_info.get('domains', [])
        
        # Collect hubs from all matching domains
        hubs = []
        for domain in domains:
            if domain in vocab.domain_hubs:
                hubs.extend(vocab.domain_hubs[domain])
        
        return list(set(hubs))
    
    def find_synonyms(self, term: str) -> List[str]:
        """
        Find all synonyms for a term.
        
        Args:
            term: Any term
            
        Returns:
            List of synonyms including the canonical form
        """
        canonical = self.normalize(term)
        if not canonical:
            return [term]
        
        entity_info = UNIVERSAL_ENTITIES.get(canonical, {})
        synonyms = [canonical] + entity_info.get('synonyms', [])
        return list(set(synonyms))
    
    def _get_product_vocab(self, product_id: str) -> Optional[ProductVocabulary]:
        """Get or build product-specific vocabulary."""
        if product_id in self._product_vocab:
            return self._product_vocab[product_id]
        
        # Load from registry
        product = self.registry.get_product(product_id)
        if not product:
            return None
        
        vocab = ProductVocabulary(product_id=product_id)
        
        # Build domain → hubs mapping
        for domain_name, domain in product.domains.items():
            vocab.domain_hubs[domain_name] = domain.hubs
        
        # Build entity → preferred hub mapping
        # This maps canonical entities to the best hub for that product
        self._build_entity_hub_mapping(vocab, product)
        
        self._product_vocab[product_id] = vocab
        return vocab
    
    def _build_entity_hub_mapping(self, vocab: ProductVocabulary, 
                                  product: ProductSchema):
        """Build entity → hub mapping for a product."""
        # For each universal entity, find the best hub
        for entity, info in UNIVERSAL_ENTITIES.items():
            best_hub = None
            best_score = 0
            
            for domain_name in info['domains']:
                if domain_name in vocab.domain_hubs:
                    for hub in vocab.domain_hubs[domain_name]:
                        # Score based on name match
                        hub_lower = hub.lower()
                        score = 0
                        
                        # Direct entity match
                        if entity in hub_lower:
                            score = 100
                        
                        # Synonym match
                        for syn in info['synonyms']:
                            if syn.replace(' ', '_') in hub_lower:
                                score = max(score, 50)
                        
                        # Domain keyword match
                        if domain_name.lower().replace('_', '') in hub_lower:
                            score = max(score, 30)
                        
                        if score > best_score:
                            best_score = score
                            best_hub = hub
            
            if best_hub:
                vocab.entity_hub[entity] = best_hub
    
    # =========================================================================
    # COMPATIBILITY METHODS (for replacing term_index.py hardcoded dicts)
    # =========================================================================
    
    def get_domain_to_entity_map(self) -> Dict[str, str]:
        """
        Get DOMAIN_TO_ENTITY-compatible mapping.
        
        This replaces the hardcoded dict in term_index.py.
        """
        return DOMAIN_TO_PRIMARY_ENTITY.copy()
    
    def get_entity_synonyms_map(self) -> Dict[str, str]:
        """
        Get ENTITY_SYNONYMS-compatible mapping.
        
        This replaces the hardcoded dict in term_index.py.
        """
        return self._term_to_entity.copy()
    
    def is_entity_term(self, term: str) -> bool:
        """Check if a term maps to a known entity."""
        return term.lower() in self._term_to_entity
    
    def get_all_entity_terms(self) -> Set[str]:
        """Get all terms that map to entities."""
        return set(self._term_to_entity.keys())


# =============================================================================
# DOMAIN ALIGNER
# =============================================================================

class DomainAligner:
    """
    Aligns domains across products for cross-product queries.
    
    Example: Map UKG Pro "Compensation" to Workday "Compensation" 
    even though the hub names differ.
    """
    
    def __init__(self):
        """Initialize the aligner."""
        self.registry = get_registry()
        self.normalizer = VocabularyNormalizer()
    
    def align_domains(self, source_product: str, 
                     target_product: str) -> Dict[str, str]:
        """
        Find domain mappings between two products.
        
        Args:
            source_product: Source product ID
            target_product: Target product ID
            
        Returns:
            Dict mapping source domain → target domain
        """
        source = self.registry.get_product(source_product)
        target = self.registry.get_product(target_product)
        
        if not source or not target:
            return {}
        
        mappings = {}
        
        for src_domain in source.domains.keys():
            # Get entity for source domain
            entity = self.normalizer.get_entity_for_domain(src_domain)
            if not entity:
                continue
            
            # Find target domain for same entity
            entity_info = UNIVERSAL_ENTITIES.get(entity, {})
            target_domains = entity_info.get('domains', [])
            
            for tgt_domain in target_domains:
                if tgt_domain in target.domains:
                    mappings[src_domain] = tgt_domain
                    break
        
        return mappings
    
    def find_equivalent_hubs(self, hub: str, source_product: str,
                            target_product: str) -> List[str]:
        """
        Find equivalent hubs in target product.
        
        Args:
            hub: Hub name in source product
            source_product: Source product ID
            target_product: Target product ID
            
        Returns:
            List of equivalent hub names in target product
        """
        source = self.registry.get_product(source_product)
        target = self.registry.get_product(target_product)
        
        if not source or not target:
            return []
        
        # Find which domain the hub belongs to
        source_domain = None
        for domain_name, domain in source.domains.items():
            if hub in domain.hubs:
                source_domain = domain_name
                break
        
        if not source_domain:
            return []
        
        # Get entity for domain
        entity = self.normalizer.get_entity_for_domain(source_domain)
        if not entity:
            return []
        
        # Find hubs in target for same entity
        return self.normalizer.get_hubs_for_entity(entity, target_product)


# =============================================================================
# SINGLETON & CONVENIENCE FUNCTIONS
# =============================================================================

_normalizer_instance: Optional[VocabularyNormalizer] = None
_aligner_instance: Optional[DomainAligner] = None


def get_vocabulary_normalizer() -> VocabularyNormalizer:
    """Get the singleton normalizer instance."""
    global _normalizer_instance
    if _normalizer_instance is None:
        _normalizer_instance = VocabularyNormalizer()
    return _normalizer_instance


def get_domain_aligner() -> DomainAligner:
    """Get the singleton aligner instance."""
    global _aligner_instance
    if _aligner_instance is None:
        _aligner_instance = DomainAligner()
    return _aligner_instance


def normalize_term(term: str) -> Optional[str]:
    """Normalize a term to canonical entity."""
    return get_vocabulary_normalizer().normalize(term)


def get_domain_for_term(term: str) -> Optional[str]:
    """Get domain for a term."""
    return get_vocabulary_normalizer().get_domain_for_term(term)
