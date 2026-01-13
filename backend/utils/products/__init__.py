"""
XLR8 Products Module
====================
Phase 5: Multi-product support infrastructure.

Components:
- registry.py: Product registry (5B)
- vocabulary.py: Cross-product vocabulary normalization (5C)
- comparator.py: Schema comparison for M&A (5E)

Usage:
    from backend.utils.products import (
        # Registry
        get_registry,
        get_product,
        list_products_by_category,
        
        # Vocabulary
        get_vocabulary_normalizer,
        normalize_term,
        get_domain_for_term,
        
        # Comparator (M&A)
        compare_schemas,
        quick_compare,
    )
    
    # Compare two products for M&A analysis
    result = compare_schemas('ukg_pro', 'workday_hcm')
    print(result.summary())
"""

__version__ = "5.0.0"

from .registry import (
    # Main classes
    ProductRegistry,
    ProductSchema,
    ProductDomain,
    
    # Singleton access
    get_registry,
    
    # Convenience functions
    get_product,
    list_products_by_category,
    list_products_by_vendor,
)

from .vocabulary import (
    # Classes
    VocabularyNormalizer,
    DomainAligner,
    VocabularyMapping,
    ProductVocabulary,
    
    # Singleton access
    get_vocabulary_normalizer,
    get_domain_aligner,
    
    # Convenience functions
    normalize_term,
    get_domain_for_term,
    
    # Data structures
    UNIVERSAL_ENTITIES,
    DOMAIN_TO_PRIMARY_ENTITY,
)

from .comparator import (
    # Classes
    SchemaComparator,
    SchemaComparison,
    DomainComparison,
    
    # Singleton access
    get_comparator,
    
    # Convenience functions
    compare_schemas,
    quick_compare,
)

__all__ = [
    # Registry
    'ProductRegistry',
    'ProductSchema', 
    'ProductDomain',
    'get_registry',
    'get_product',
    'list_products_by_category',
    'list_products_by_vendor',
    
    # Vocabulary
    'VocabularyNormalizer',
    'DomainAligner',
    'VocabularyMapping',
    'ProductVocabulary',
    'get_vocabulary_normalizer',
    'get_domain_aligner',
    'normalize_term',
    'get_domain_for_term',
    'UNIVERSAL_ENTITIES',
    'DOMAIN_TO_PRIMARY_ENTITY',
    
    # Comparator
    'SchemaComparator',
    'SchemaComparison',
    'DomainComparison',
    'get_comparator',
    'compare_schemas',
    'quick_compare',
]
