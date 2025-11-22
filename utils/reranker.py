"""
Lightweight Reranker for RAG Results
Scores query-document relevance using keyword matching and metadata signals
No ML models, no API calls - pure Python for speed

Author: HCMPACT
Version: 1.0
"""

import logging
import re
from typing import List, Dict, Any
from collections import Counter

logger = logging.getLogger(__name__)


class LightweightReranker:
    """
    Fast reranker using keyword matching and metadata signals.
    
    Scoring factors:
    1. Keyword overlap (TF-IDF style)
    2. Query term frequency in document
    3. Functional area relevance
    4. Sheet name relevance
    5. Distance score from ChromaDB
    """
    
    def __init__(self):
        """Initialize reranker"""
        # Common stopwords to ignore
        self.stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
            'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these',
            'those', 'what', 'which', 'who', 'when', 'where', 'why', 'how'
        }
        
        logger.info("Lightweight Reranker initialized")
    
    def rerank(
        self, 
        query: str, 
        candidates: List[Dict[str, Any]], 
        top_k: int = 15
    ) -> List[Dict[str, Any]]:
        """
        Rerank candidates by relevance to query.
        
        Args:
            query: User's search query
            candidates: List of ChromaDB search results
            top_k: Number of top results to return
            
        Returns:
            Reranked list of top_k candidates
        """
        if not candidates:
            return []
        
        if len(candidates) <= top_k:
            # Already have fewer than top_k - no need to rerank
            logger.info(f"Only {len(candidates)} candidates - no reranking needed")
            return candidates
        
        logger.info(f"Reranking {len(candidates)} candidates to top {top_k}")
        
        # Extract query keywords
        query_keywords = self._extract_keywords(query)
        
        # Score each candidate
        scored_candidates = []
        for candidate in candidates:
            score = self._score_candidate(query, query_keywords, candidate)
            scored_candidates.append({
                'candidate': candidate,
                'score': score
            })
        
        # Sort by score (descending)
        scored_candidates.sort(key=lambda x: x['score'], reverse=True)
        
        # Return top K
        top_candidates = [item['candidate'] for item in scored_candidates[:top_k]]
        
        # Log score distribution
        top_score = scored_candidates[0]['score'] if scored_candidates else 0
        cutoff_score = scored_candidates[top_k-1]['score'] if len(scored_candidates) >= top_k else 0
        logger.info(f"Reranking complete - Top score: {top_score:.2f}, Cutoff: {cutoff_score:.2f}")
        
        return top_candidates
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract meaningful keywords from text.
        
        Args:
            text: Input text
            
        Returns:
            List of lowercase keywords (no stopwords)
        """
        # Lowercase and split
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Remove stopwords and short words
        keywords = [
            word for word in words 
            if word not in self.stopwords and len(word) > 2
        ]
        
        return keywords
    
    def _score_candidate(
        self, 
        query: str, 
        query_keywords: List[str], 
        candidate: Dict[str, Any]
    ) -> float:
        """
        Score a candidate's relevance to the query.
        
        Args:
            query: Original query string
            query_keywords: Extracted query keywords
            candidate: ChromaDB result dict
            
        Returns:
            Relevance score (higher = more relevant)
        """
        score = 0.0
        
        # Get document text
        doc_text = candidate.get('document', '').lower()
        doc_keywords = self._extract_keywords(doc_text)
        
        # Get metadata
        metadata = candidate.get('metadata', {})
        source = metadata.get('source', '').lower()
        sheet_name = metadata.get('sheet_name', '').lower()
        functional_area = metadata.get('functional_area', '').lower()
        
        # FACTOR 1: Keyword overlap (30 points max)
        # Count how many query keywords appear in document
        doc_keyword_set = set(doc_keywords)
        matching_keywords = [kw for kw in query_keywords if kw in doc_keyword_set]
        keyword_overlap_ratio = len(matching_keywords) / len(query_keywords) if query_keywords else 0
        score += keyword_overlap_ratio * 30
        
        # FACTOR 2: Keyword frequency (20 points max)
        # How often do query keywords appear in document?
        doc_keyword_counts = Counter(doc_keywords)
        total_frequency = sum(doc_keyword_counts.get(kw, 0) for kw in query_keywords)
        # Normalize by document length (avoid bias toward long docs)
        normalized_frequency = total_frequency / len(doc_keywords) if doc_keywords else 0
        score += min(normalized_frequency * 100, 20)  # Cap at 20 points
        
        # FACTOR 3: Exact phrase match (25 points)
        # Does the query appear as a phrase in the document?
        if query.lower() in doc_text:
            score += 25
        
        # FACTOR 4: Sheet name relevance (15 points)
        # Do query keywords appear in sheet name?
        if sheet_name:
            sheet_keywords = self._extract_keywords(sheet_name)
            sheet_matches = [kw for kw in query_keywords if kw in sheet_keywords]
            if sheet_matches:
                score += 15
        
        # FACTOR 5: Functional area relevance (10 points)
        # Do query keywords relate to functional area?
        if functional_area:
            fa_keywords = self._extract_keywords(functional_area)
            fa_matches = [kw for kw in query_keywords if kw in fa_keywords]
            if fa_matches:
                score += 10
        
        # FACTOR 6: ChromaDB distance (bonus)
        # Use existing distance score from vector search
        distance = candidate.get('distance', 1.0)
        # Lower distance = more similar = better
        # Convert to bonus (0-10 points, inverted)
        similarity_bonus = max(0, 10 - (distance * 10))
        score += similarity_bonus
        
        return score
    
    def explain_scores(
        self, 
        query: str, 
        scored_candidates: List[Dict[str, Any]], 
        top_n: int = 5
    ) -> str:
        """
        Generate explanation of top scoring candidates.
        
        Args:
            query: Query string
            scored_candidates: List of scored candidates
            top_n: Number of top candidates to explain
            
        Returns:
            Human-readable explanation
        """
        explanation_parts = [f"Top {top_n} Results for: '{query}'\n"]
        
        for i, item in enumerate(scored_candidates[:top_n], 1):
            candidate = item['candidate']
            score = item['score']
            metadata = candidate.get('metadata', {})
            
            explanation_parts.append(
                f"{i}. Score: {score:.1f} | "
                f"Source: {metadata.get('source', 'Unknown')} | "
                f"Sheet: {metadata.get('sheet_name', 'N/A')}"
            )
        
        return "\n".join(explanation_parts)


def rerank_results(
    query: str, 
    results: List[Dict[str, Any]], 
    top_k: int = 15
) -> List[Dict[str, Any]]:
    """
    Convenience function to rerank search results.
    
    Args:
        query: Search query
        results: List of search results
        top_k: Number of top results to keep
        
    Returns:
        Reranked results
    """
    reranker = LightweightReranker()
    return reranker.rerank(query, results, top_k)
