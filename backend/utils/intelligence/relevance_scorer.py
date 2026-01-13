"""
Relevance Scorer for Five Truths Architecture
==============================================

Multi-factor relevance scoring that goes beyond embedding similarity.

Scoring Factors:
1. Similarity Score - Base embedding distance from ChromaDB
2. Domain Match - Chunk domain matches query domain
3. Source Authority - Query-type specific authority weights
4. Recency - More recent documents preferred
5. Jurisdiction Match - State/federal alignment

Filtering:
- Minimum relevance threshold (configurable, default 0.5)
- Top-N filtering

Phase 2B.4 Implementation - January 2026
"""

import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

# Minimum relevance threshold - results below this are filtered out
MINIMUM_RELEVANCE_THRESHOLD = 0.5

# Maximum results to return after filtering
MAX_RESULTS_DEFAULT = 10

# Scoring weights for combining factors
RELEVANCE_WEIGHTS = {
    'similarity': 0.45,     # Base similarity score (from ChromaDB)
    'authority': 0.25,      # Source authority weight (from 2B.3)
    'domain_match': 0.15,   # Domain alignment bonus
    'recency': 0.10,        # Document recency
    'jurisdiction': 0.05,   # Jurisdiction match
}

# Authority weight matrix (from 2B.3)
SOURCE_WEIGHT_MATRIX = {
    'regulatory_required': {
        'government': 1.0, 'vendor': 0.6, 'industry': 0.5, 'customer': 0.2, 'internal': 0.3,
    },
    'best_practice': {
        'government': 0.6, 'vendor': 1.0, 'industry': 0.8, 'customer': 0.3, 'internal': 0.4,
    },
    'implementation': {
        'government': 0.4, 'vendor': 1.0, 'industry': 0.7, 'customer': 0.3, 'internal': 0.5,
    },
    'customer_intent': {
        'government': 0.3, 'vendor': 0.5, 'industry': 0.4, 'customer': 1.0, 'internal': 0.6,
    },
    'gap_analysis': {
        'government': 0.8, 'vendor': 0.9, 'industry': 0.7, 'customer': 0.9, 'internal': 0.5,
    },
    'policy': {
        'government': 0.7, 'vendor': 0.5, 'industry': 0.6, 'customer': 0.8, 'internal': 1.0,
    },
    'explanation': {
        'government': 0.8, 'vendor': 0.9, 'industry': 0.7, 'customer': 0.6, 'internal': 0.5,
    },
    'default': {
        'government': 0.9, 'vendor': 0.85, 'industry': 0.7, 'customer': 0.6, 'internal': 0.5,
    },
}

# US States for jurisdiction matching
US_STATES = {
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
    'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
    'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
    'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
    'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC'
}


@dataclass
class RelevanceScore:
    """Detailed breakdown of relevance scoring."""
    similarity: float = 0.0
    authority: float = 0.0
    domain_match: float = 0.0
    recency: float = 0.0
    jurisdiction: float = 0.0
    final_score: float = 0.0
    
    # Metadata for debugging
    source_authority: str = ""
    chunk_domain: str = ""
    query_domain: str = ""
    effective_date: str = ""
    chunk_jurisdiction: str = ""
    query_jurisdiction: str = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for metadata storage."""
        return {
            '_score_similarity': round(self.similarity, 3),
            '_score_authority': round(self.authority, 3),
            '_score_domain': round(self.domain_match, 3),
            '_score_recency': round(self.recency, 3),
            '_score_jurisdiction': round(self.jurisdiction, 3),
            '_score_final': round(self.final_score, 3),
        }


class RelevanceScorer:
    """
    Multi-factor relevance scoring for ChromaDB results.
    
    Combines multiple signals beyond raw similarity to rank results
    by actual relevance to the user's query.
    """
    
    def __init__(self, 
                 min_threshold: float = MINIMUM_RELEVANCE_THRESHOLD,
                 max_results: int = MAX_RESULTS_DEFAULT):
        """
        Initialize the scorer.
        
        Args:
            min_threshold: Minimum score to include in results (0.0 - 1.0)
            max_results: Maximum number of results to return
        """
        self.min_threshold = min_threshold
        self.max_results = max_results
        logger.info(f"RelevanceScorer initialized (threshold={min_threshold}, max={max_results})")
    
    def score_and_filter_truths(self,
                                truths: List,
                                query_category: str = 'default',
                                query_domain: str = None,
                                query_jurisdiction: str = None) -> List:
        """
        Score and filter Truth objects.
        
        Args:
            truths: List of Truth objects from gatherers
            query_category: Query category from TruthRouter
            query_domain: Detected domain (earnings, taxes, etc.)
            query_jurisdiction: Detected jurisdiction (federal, CA, TX, etc.)
            
        Returns:
            Filtered and re-ranked list of Truth objects
        """
        if not truths:
            return truths
        
        scored = []
        
        for truth in truths:
            metadata = getattr(truth, 'metadata', {}) or {}
            
            # Calculate all scoring factors
            score = self._calculate_score(
                similarity=getattr(truth, 'confidence', 0.5),
                source_authority=metadata.get('source_authority', 'internal'),
                chunk_domain=metadata.get('domain') or metadata.get('chunk_domain'),
                effective_date=metadata.get('effective_date'),
                chunk_jurisdiction=metadata.get('jurisdiction'),
                query_category=query_category,
                query_domain=query_domain,
                query_jurisdiction=query_jurisdiction
            )
            
            # Store scores in metadata
            truth.metadata = metadata
            truth.metadata.update(score.to_dict())
            truth.metadata['_original_confidence'] = getattr(truth, 'confidence', 0.5)
            
            # Update confidence with final score
            truth.confidence = score.final_score
            
            scored.append((score.final_score, truth))
        
        # Sort by final score
        scored.sort(key=lambda x: x[0], reverse=True)
        
        # Filter by threshold
        filtered = [(s, t) for s, t in scored if s >= self.min_threshold]
        
        # Limit results
        limited = filtered[:self.max_results]
        
        # Log summary
        logger.info(f"[RELEVANCE] Scored {len(truths)} → filtered to {len(filtered)} → "
                   f"limited to {len(limited)} (threshold={self.min_threshold})")
        
        if limited:
            top_score = limited[0][0]
            bottom_score = limited[-1][0] if limited else 0
            logger.info(f"[RELEVANCE] Score range: {bottom_score:.2f} - {top_score:.2f}")
        
        return [t for _, t in limited]
    
    def score_and_filter_raw(self,
                             results: List[Dict],
                             query_category: str = 'default',
                             query_domain: str = None,
                             query_jurisdiction: str = None) -> List[Dict]:
        """
        Score and filter raw ChromaDB result dicts.
        
        Args:
            results: List of dicts with 'document', 'metadata', 'distance'
            query_category: Query category from TruthRouter
            query_domain: Detected domain
            query_jurisdiction: Detected jurisdiction
            
        Returns:
            Filtered and re-ranked list of result dicts
        """
        if not results:
            return results
        
        scored = []
        
        for result in results:
            metadata = result.get('metadata', {})
            distance = result.get('distance', 1.0)
            
            # Convert distance to similarity
            similarity = max(0.0, 1.0 - (distance / 2.0))
            
            score = self._calculate_score(
                similarity=similarity,
                source_authority=metadata.get('source_authority', 'internal'),
                chunk_domain=metadata.get('domain') or metadata.get('chunk_domain'),
                effective_date=metadata.get('effective_date'),
                chunk_jurisdiction=metadata.get('jurisdiction'),
                query_category=query_category,
                query_domain=query_domain,
                query_jurisdiction=query_jurisdiction
            )
            
            # Store scores in result
            result['_relevance'] = score.to_dict()
            result['_relevance']['_original_distance'] = distance
            
            scored.append((score.final_score, result))
        
        # Sort, filter, limit
        scored.sort(key=lambda x: x[0], reverse=True)
        filtered = [(s, r) for s, r in scored if s >= self.min_threshold]
        limited = filtered[:self.max_results]
        
        return [r for _, r in limited]
    
    def _calculate_score(self,
                         similarity: float,
                         source_authority: str,
                         chunk_domain: str,
                         effective_date: str,
                         chunk_jurisdiction: str,
                         query_category: str,
                         query_domain: str,
                         query_jurisdiction: str) -> RelevanceScore:
        """
        Calculate multi-factor relevance score.
        
        Returns:
            RelevanceScore with all factor scores and final combined score
        """
        score = RelevanceScore()
        
        # Factor 1: Similarity (from ChromaDB)
        score.similarity = max(0.0, min(1.0, similarity))
        
        # Factor 2: Authority (query-type specific)
        weights = SOURCE_WEIGHT_MATRIX.get(query_category, SOURCE_WEIGHT_MATRIX['default'])
        score.authority = weights.get(source_authority, 0.5)
        score.source_authority = source_authority
        
        # Factor 3: Domain match
        score.chunk_domain = chunk_domain or ""
        score.query_domain = query_domain or ""
        if query_domain and chunk_domain:
            if chunk_domain == query_domain:
                score.domain_match = 1.0
            elif self._domains_related(chunk_domain, query_domain):
                score.domain_match = 0.7
            else:
                score.domain_match = 0.4
        else:
            score.domain_match = 0.6  # Unknown = neutral
        
        # Factor 4: Recency
        score.effective_date = effective_date or ""
        score.recency = self._calculate_recency_score(effective_date)
        
        # Factor 5: Jurisdiction match
        score.chunk_jurisdiction = chunk_jurisdiction or ""
        score.query_jurisdiction = query_jurisdiction or ""
        score.jurisdiction = self._calculate_jurisdiction_score(
            chunk_jurisdiction, query_jurisdiction
        )
        
        # Calculate weighted final score
        score.final_score = (
            score.similarity * RELEVANCE_WEIGHTS['similarity'] +
            score.authority * RELEVANCE_WEIGHTS['authority'] +
            score.domain_match * RELEVANCE_WEIGHTS['domain_match'] +
            score.recency * RELEVANCE_WEIGHTS['recency'] +
            score.jurisdiction * RELEVANCE_WEIGHTS['jurisdiction']
        )
        
        return score
    
    def _domains_related(self, domain1: str, domain2: str) -> bool:
        """Check if two domains are related (adjacent in HCM workflow)."""
        related_domains = {
            ('earnings', 'taxes'),
            ('earnings', 'deductions'),
            ('deductions', 'benefits'),
            ('demographics', 'organization'),
            ('time', 'earnings'),
        }
        
        pair = tuple(sorted([domain1.lower(), domain2.lower()]))
        return pair in related_domains
    
    def _calculate_recency_score(self, effective_date: str) -> float:
        """
        Calculate recency score based on effective date.
        
        More recent = higher score. Documents without dates get neutral score.
        
        Scoring:
        - Last 6 months: 1.0
        - Last 1 year: 0.9
        - Last 2 years: 0.8
        - Last 3 years: 0.7
        - Older: 0.6
        - No date: 0.7 (neutral)
        """
        if not effective_date:
            return 0.7  # Neutral for unknown dates
        
        try:
            # Try to parse the date
            parsed = None
            for fmt in ['%Y-%m-%d', '%Y-%m', '%Y', '%m/%d/%Y', '%m-%d-%Y']:
                try:
                    parsed = datetime.strptime(str(effective_date)[:10], fmt)
                    break
                except ValueError:
                    continue
            
            if not parsed:
                # Try to extract year
                year_match = re.search(r'20\d{2}', str(effective_date))
                if year_match:
                    parsed = datetime(int(year_match.group()), 1, 1)
            
            if not parsed:
                return 0.7  # Can't parse = neutral
            
            # Calculate age
            now = datetime.now()
            age_days = (now - parsed).days
            
            if age_days < 0:
                return 1.0  # Future effective date = very relevant
            elif age_days <= 180:
                return 1.0  # Last 6 months
            elif age_days <= 365:
                return 0.9  # Last year
            elif age_days <= 730:
                return 0.8  # Last 2 years
            elif age_days <= 1095:
                return 0.7  # Last 3 years
            else:
                return 0.6  # Older
                
        except Exception as e:
            logger.debug(f"Could not parse date '{effective_date}': {e}")
            return 0.7
    
    def _calculate_jurisdiction_score(self, 
                                       chunk_jurisdiction: str,
                                       query_jurisdiction: str) -> float:
        """
        Calculate jurisdiction match score.
        
        Scoring:
        - Exact match: 1.0
        - Federal matches everything: 0.9
        - State matches federal: 0.8
        - Different states: 0.5
        - Unknown: 0.7 (neutral)
        """
        if not chunk_jurisdiction or not query_jurisdiction:
            return 0.7  # Unknown = neutral
        
        chunk_j = chunk_jurisdiction.upper().strip()
        query_j = query_jurisdiction.upper().strip()
        
        # Exact match
        if chunk_j == query_j:
            return 1.0
        
        # Federal content matches any jurisdiction
        if chunk_j in ['FEDERAL', 'US', 'USA', 'NATIONAL']:
            return 0.9
        
        # Query is federal - state content partially matches
        if query_j in ['FEDERAL', 'US', 'USA', 'NATIONAL']:
            return 0.8
        
        # Both are states but different
        if chunk_j in US_STATES and query_j in US_STATES:
            return 0.5
        
        # One is state, one is unknown
        return 0.6
    
    def explain_score(self, truth_or_result) -> str:
        """
        Get human-readable explanation of a result's score.
        
        Args:
            truth_or_result: A Truth object or result dict that has been scored
            
        Returns:
            Explanation string
        """
        if hasattr(truth_or_result, 'metadata'):
            m = truth_or_result.metadata
        elif isinstance(truth_or_result, dict):
            m = truth_or_result.get('_relevance', truth_or_result)
        else:
            return "No scoring information available"
        
        parts = []
        
        if '_score_similarity' in m:
            parts.append(f"similarity={m['_score_similarity']:.2f}")
        if '_score_authority' in m:
            parts.append(f"authority={m['_score_authority']:.2f}")
        if '_score_domain' in m:
            parts.append(f"domain={m['_score_domain']:.2f}")
        if '_score_recency' in m:
            parts.append(f"recency={m['_score_recency']:.2f}")
        if '_score_jurisdiction' in m:
            parts.append(f"jurisdiction={m['_score_jurisdiction']:.2f}")
        if '_score_final' in m:
            parts.append(f"→ FINAL={m['_score_final']:.2f}")
        
        return " | ".join(parts) if parts else "No scores found"


# =============================================================================
# SINGLETON AND CONVENIENCE FUNCTIONS
# =============================================================================

_scorer_instance: Optional[RelevanceScorer] = None

def get_scorer(min_threshold: float = MINIMUM_RELEVANCE_THRESHOLD,
               max_results: int = MAX_RESULTS_DEFAULT) -> RelevanceScorer:
    """Get the singleton RelevanceScorer instance."""
    global _scorer_instance
    if _scorer_instance is None:
        _scorer_instance = RelevanceScorer(min_threshold, max_results)
    return _scorer_instance


def score_and_filter(truths: List,
                     query_category: str = 'default',
                     query_domain: str = None,
                     query_jurisdiction: str = None,
                     min_threshold: float = None) -> List:
    """
    Convenience function to score and filter Truth objects.
    
    Args:
        truths: List of Truth objects
        query_category: Query category from TruthRouter
        query_domain: Detected domain
        query_jurisdiction: Detected jurisdiction
        min_threshold: Optional override for minimum threshold
        
    Returns:
        Filtered and re-ranked list of Truth objects
    """
    scorer = get_scorer()
    if min_threshold is not None:
        scorer.min_threshold = min_threshold
    return scorer.score_and_filter_truths(
        truths, query_category, query_domain, query_jurisdiction
    )


def score_and_filter_raw(results: List[Dict],
                         query_category: str = 'default',
                         query_domain: str = None,
                         query_jurisdiction: str = None) -> List[Dict]:
    """
    Convenience function to score and filter raw result dicts.
    """
    return get_scorer().score_and_filter_raw(
        results, query_category, query_domain, query_jurisdiction
    )
