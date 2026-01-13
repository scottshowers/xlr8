"""
Source Prioritizer for Five Truths Architecture
================================================

Re-ranks search results by source authority based on query type.
Different query types should prioritize different sources:
- Regulatory queries: government > vendor > industry
- Reference queries: vendor > industry > government
- Intent queries: customer > internal > vendor

Authority Hierarchy (general):
government (IRS, DOL) > vendor (UKG docs) > industry (SHRM) > customer (SOW) > internal (notes)

Phase 2B.3 Implementation - January 2026
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# =============================================================================
# AUTHORITY WEIGHT MATRICES
# =============================================================================

# Base authority rankings (used when no specific query type)
BASE_AUTHORITY_WEIGHTS = {
    'government': 1.0,
    'vendor': 0.85,
    'industry': 0.7,
    'customer': 0.6,
    'internal': 0.5,
}

# Query-type specific weights
# Each query type prioritizes different source authorities
SOURCE_WEIGHT_MATRIX = {
    # Regulatory queries - government sources are king
    'regulatory_required': {
        'government': 1.0,
        'vendor': 0.6,
        'industry': 0.5,
        'customer': 0.2,
        'internal': 0.3,
    },
    # Best practice queries - vendor docs most relevant
    'best_practice': {
        'government': 0.6,
        'vendor': 1.0,
        'industry': 0.8,
        'customer': 0.3,
        'internal': 0.4,
    },
    # Implementation/how-to - vendor docs most relevant
    'implementation': {
        'government': 0.4,
        'vendor': 1.0,
        'industry': 0.7,
        'customer': 0.3,
        'internal': 0.5,
    },
    # Customer intent - customer sources most relevant
    'customer_intent': {
        'government': 0.3,
        'vendor': 0.5,
        'industry': 0.4,
        'customer': 1.0,
        'internal': 0.6,
    },
    # Gap analysis - need multiple perspectives
    'gap_analysis': {
        'government': 0.8,
        'vendor': 0.9,
        'industry': 0.7,
        'customer': 0.9,
        'internal': 0.5,
    },
    # Policy questions - compliance/internal sources matter
    'policy': {
        'government': 0.7,
        'vendor': 0.5,
        'industry': 0.6,
        'customer': 0.8,
        'internal': 1.0,
    },
    # Explanation queries - balanced weights
    'explanation': {
        'government': 0.8,
        'vendor': 0.9,
        'industry': 0.7,
        'customer': 0.6,
        'internal': 0.5,
    },
    # Default - balanced weights
    'default': {
        'government': 0.9,
        'vendor': 0.85,
        'industry': 0.7,
        'customer': 0.6,
        'internal': 0.5,
    },
}

# Scoring weights for combining factors
SCORING_WEIGHTS = {
    'similarity': 0.5,      # Base similarity score (from ChromaDB)
    'authority': 0.3,       # Source authority weight
    'domain_match': 0.15,   # Domain alignment bonus
    'routing': 0.05,        # TruthRouter weight bonus
}


@dataclass
class ScoredResult:
    """A search result with computed scores."""
    original: any  # The original Truth or result dict
    similarity_score: float
    authority_score: float
    domain_score: float
    routing_weight: float
    final_score: float
    source_authority: str
    domain: Optional[str]


class SourcePrioritizer:
    """
    Re-rank search results by source authority.
    
    Takes results from ChromaDB gatherers and adjusts their ranking
    based on the authority of the source and the type of query.
    """
    
    def __init__(self):
        """Initialize the prioritizer."""
        logger.info("SourcePrioritizer initialized")
    
    def prioritize_truths(self, 
                          truths: List,
                          query_category: str = 'default',
                          query_domain: str = None) -> List:
        """
        Re-rank Truth objects by source authority.
        
        Args:
            truths: List of Truth objects from gatherers
            query_category: Query category from TruthRouter (regulatory_required, best_practice, etc.)
            query_domain: Detected domain from TruthRouter (earnings, taxes, etc.)
            
        Returns:
            List of Truth objects, re-sorted by combined score
        """
        if not truths:
            return truths
        
        # Get weight matrix for this query type
        weights = SOURCE_WEIGHT_MATRIX.get(query_category, SOURCE_WEIGHT_MATRIX['default'])
        
        scored_results = []
        
        for truth in truths:
            # Extract metadata
            metadata = getattr(truth, 'metadata', {}) or {}
            
            # Get source authority (from 2B.1 classification or metadata)
            source_authority = metadata.get('source_authority', 'internal')
            
            # Get domain (from chunk classification)
            chunk_domain = metadata.get('domain') or metadata.get('chunk_domain')
            
            # Get original confidence as similarity proxy
            similarity = getattr(truth, 'confidence', 0.5)
            
            # Get routing weight if set by TruthRouter
            routing_weight = metadata.get('routing_weight', 1.0)
            
            # Calculate authority score
            authority_score = weights.get(source_authority, 0.5)
            
            # Calculate domain match score
            domain_score = 1.0 if (query_domain and chunk_domain == query_domain) else 0.7
            
            # Calculate final combined score
            final_score = (
                similarity * SCORING_WEIGHTS['similarity'] +
                authority_score * SCORING_WEIGHTS['authority'] +
                domain_score * SCORING_WEIGHTS['domain_match'] +
                routing_weight * SCORING_WEIGHTS['routing']
            )
            
            # Store scores in metadata for transparency
            truth.metadata = metadata
            truth.metadata['_authority_score'] = authority_score
            truth.metadata['_domain_score'] = domain_score
            truth.metadata['_final_score'] = final_score
            
            # Update confidence to reflect authority-adjusted score
            # Keep original in metadata for reference
            truth.metadata['_original_confidence'] = similarity
            truth.confidence = final_score
            
            scored_results.append((final_score, truth))
        
        # Sort by final score (descending)
        scored_results.sort(key=lambda x: x[0], reverse=True)
        
        # Log re-ranking summary
        if scored_results:
            top = scored_results[0][1]
            top_authority = top.metadata.get('source_authority', 'unknown')
            logger.info(f"[PRIORITIZE] Re-ranked {len(truths)} results for '{query_category}'. "
                       f"Top result: {top_authority} (score={scored_results[0][0]:.2f})")
        
        return [result[1] for result in scored_results]
    
    def prioritize_raw_results(self,
                               results: List[Dict],
                               query_category: str = 'default',
                               query_domain: str = None) -> List[Dict]:
        """
        Re-rank raw ChromaDB result dicts by source authority.
        
        Use this for results directly from RAGHandler.search() before
        they're converted to Truth objects.
        
        Args:
            results: List of dicts with 'document', 'metadata', 'distance'
            query_category: Query category from TruthRouter
            query_domain: Detected domain
            
        Returns:
            List of result dicts, re-sorted by combined score
        """
        if not results:
            return results
        
        weights = SOURCE_WEIGHT_MATRIX.get(query_category, SOURCE_WEIGHT_MATRIX['default'])
        
        scored = []
        
        for result in results:
            metadata = result.get('metadata', {})
            distance = result.get('distance', 1.0)
            
            # Convert distance to similarity (ChromaDB uses L2 distance)
            similarity = max(0.0, 1.0 - (distance / 2.0))
            
            # Get authority and domain
            source_authority = metadata.get('source_authority', 'internal')
            chunk_domain = metadata.get('domain') or metadata.get('chunk_domain')
            
            # Calculate scores
            authority_score = weights.get(source_authority, 0.5)
            domain_score = 1.0 if (query_domain and chunk_domain == query_domain) else 0.7
            
            final_score = (
                similarity * SCORING_WEIGHTS['similarity'] +
                authority_score * SCORING_WEIGHTS['authority'] +
                domain_score * SCORING_WEIGHTS['domain_match']
            )
            
            # Store computed scores in result
            result['_scores'] = {
                'similarity': similarity,
                'authority': authority_score,
                'domain': domain_score,
                'final': final_score
            }
            
            scored.append((final_score, result))
        
        # Sort by final score
        scored.sort(key=lambda x: x[0], reverse=True)
        
        return [r[1] for r in scored]
    
    def get_authority_weight(self, 
                             source_authority: str,
                             query_category: str = 'default') -> float:
        """
        Get the authority weight for a source type and query category.
        
        Args:
            source_authority: The source type (government, vendor, etc.)
            query_category: The query category from TruthRouter
            
        Returns:
            Weight value 0.0 - 1.0
        """
        weights = SOURCE_WEIGHT_MATRIX.get(query_category, SOURCE_WEIGHT_MATRIX['default'])
        return weights.get(source_authority, 0.5)
    
    def explain_ranking(self, truth) -> str:
        """
        Get a human-readable explanation of why a result was ranked where it was.
        
        Args:
            truth: A Truth object that has been through prioritize_truths()
            
        Returns:
            Explanation string
        """
        metadata = getattr(truth, 'metadata', {}) or {}
        
        authority = metadata.get('source_authority', 'unknown')
        auth_score = metadata.get('_authority_score', 0)
        domain_score = metadata.get('_domain_score', 0)
        final_score = metadata.get('_final_score', 0)
        original = metadata.get('_original_confidence', 0)
        
        return (f"Source: {authority} (authority={auth_score:.2f}), "
                f"Domain match={domain_score:.2f}, "
                f"Original={original:.2f} → Final={final_score:.2f}")


# =============================================================================
# SINGLETON AND CONVENIENCE FUNCTIONS
# =============================================================================

_prioritizer_instance: Optional[SourcePrioritizer] = None

def get_prioritizer() -> SourcePrioritizer:
    """Get the singleton SourcePrioritizer instance."""
    global _prioritizer_instance
    if _prioritizer_instance is None:
        _prioritizer_instance = SourcePrioritizer()
    return _prioritizer_instance


def prioritize_truths(truths: List,
                      query_category: str = 'default',
                      query_domain: str = None) -> List:
    """
    Convenience function to prioritize Truth objects.
    
    Args:
        truths: List of Truth objects
        query_category: Query category from TruthRouter
        query_domain: Detected domain
        
    Returns:
        Re-ranked list of Truth objects
    """
    return get_prioritizer().prioritize_truths(truths, query_category, query_domain)


def prioritize_results(results: List[Dict],
                       query_category: str = 'default',
                       query_domain: str = None) -> List[Dict]:
    """
    Convenience function to prioritize raw result dicts.
    
    Args:
        results: List of result dicts from ChromaDB
        query_category: Query category from TruthRouter
        query_domain: Detected domain
        
    Returns:
        Re-ranked list of result dicts
    """
    return get_prioritizer().prioritize_raw_results(results, query_category, query_domain)
