"""
Gap Detector for Five Truths Architecture
==========================================

Identifies missing truth coverage for topics.
Product-agnostic - works with any domain, not just HCM.

Gap Types:
1. Intent Gap - No SOW/requirements found for topic
2. Reference Gap - No best practice documentation found
3. Regulatory Gap - No compliance/regulatory guidance found
4. Compliance Gap - No internal policy documentation found

The detector searches each truth type for a topic and flags
when coverage is missing or insufficient.

Phase 2B.6 Implementation - January 2026
"""

import logging
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

# Minimum relevance score to consider a truth type "covered"
COVERAGE_THRESHOLD = 0.5

# Severity by truth type when gap is detected
DEFAULT_SEVERITY = {
    'regulatory': 'high',      # Missing compliance guidance is serious
    'compliance': 'high',      # Missing internal policy
    'intent': 'medium',        # Should validate with customer
    'reference': 'low',        # Nice to have best practices
}

# Recommendations by truth type
DEFAULT_RECOMMENDATIONS = {
    'regulatory': 'Upload relevant regulatory documents or compliance guidelines for this topic.',
    'compliance': 'Upload internal policies or compliance procedures for this topic.',
    'intent': 'Review SOW or requirements documents to confirm customer expectations for this topic.',
    'reference': 'Upload vendor documentation or best practice guides for this topic.',
}


@dataclass
class Gap:
    """
    A detected gap in truth coverage.
    
    Represents missing or insufficient information from one truth type
    for a given topic.
    """
    truth_type: str            # Which truth is missing (intent, reference, regulatory, compliance)
    topic: str                 # Topic that has the gap
    severity: str              # high, medium, low
    
    # Details
    description: str = ""      # Human-readable description
    recommendation: str = ""   # What to do about it
    
    # Search context
    query_used: str = ""       # Query used to search
    best_match_score: float = 0.0  # Score of best match found (if any)
    best_match_doc: str = ""   # Document name of best match
    
    # Metadata
    detected_at: str = ""
    project: str = ""
    
    def __post_init__(self):
        if not self.detected_at:
            self.detected_at = datetime.now().isoformat()
        if not self.description:
            self.description = f"No {self.truth_type} documentation found for '{self.topic}'"
        if not self.recommendation:
            self.recommendation = DEFAULT_RECOMMENDATIONS.get(self.truth_type, 
                f"Upload {self.truth_type} documentation for this topic.")
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'truth_type': self.truth_type,
            'topic': self.topic,
            'severity': self.severity,
            'description': self.description,
            'recommendation': self.recommendation,
            'query_used': self.query_used,
            'best_match_score': round(self.best_match_score, 3),
            'best_match_doc': self.best_match_doc,
            'detected_at': self.detected_at,
            'project': self.project,
        }


@dataclass
class GapAnalysis:
    """
    Complete gap analysis results for a topic.
    """
    topic: str
    project: str
    gaps: List[Gap] = field(default_factory=list)
    covered_truths: List[str] = field(default_factory=list)
    analyzed_at: str = ""
    
    def __post_init__(self):
        if not self.analyzed_at:
            self.analyzed_at = datetime.now().isoformat()
    
    @property
    def has_gaps(self) -> bool:
        return len(self.gaps) > 0
    
    @property
    def gap_count(self) -> int:
        return len(self.gaps)
    
    @property
    def coverage_score(self) -> float:
        """Calculate coverage as percentage of truths covered."""
        total_truths = 4  # intent, reference, regulatory, compliance
        covered = len(self.covered_truths)
        return covered / total_truths
    
    def summary(self) -> str:
        """Get human-readable summary."""
        if not self.gaps:
            return f"Full coverage for '{self.topic}' - all truth types have relevant documentation."
        
        gap_types = [g.truth_type for g in self.gaps]
        return f"Gaps detected for '{self.topic}': missing {', '.join(gap_types)}"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'topic': self.topic,
            'project': self.project,
            'has_gaps': self.has_gaps,
            'gap_count': self.gap_count,
            'coverage_score': round(self.coverage_score, 2),
            'covered_truths': self.covered_truths,
            'gaps': [g.to_dict() for g in self.gaps],
            'analyzed_at': self.analyzed_at,
        }


class GapDetector:
    """
    Detect gaps in Five Truths coverage for a topic.
    
    Product-agnostic - searches each truth type and flags when
    coverage is missing or below threshold.
    """
    
    def __init__(self, 
                 rag_handler=None,
                 coverage_threshold: float = COVERAGE_THRESHOLD):
        """
        Initialize the detector.
        
        Args:
            rag_handler: RAGHandler instance for searching ChromaDB
            coverage_threshold: Minimum score to consider a topic "covered"
        """
        self.rag_handler = rag_handler
        self.coverage_threshold = coverage_threshold
        logger.info(f"GapDetector initialized (threshold={coverage_threshold})")
    
    def detect_gaps(self, 
                    topic: str, 
                    project: str = None,
                    truth_types: List[str] = None) -> GapAnalysis:
        """
        Detect gaps in truth coverage for a topic.
        
        Args:
            topic: The topic to check coverage for
            project: Project ID (for scoping searches)
            truth_types: Which truth types to check (default: all 4)
            
        Returns:
            GapAnalysis with gaps and coverage info
        """
        if truth_types is None:
            truth_types = ['intent', 'reference', 'regulatory', 'compliance']
        
        gaps = []
        covered = []
        
        logger.info(f"[GAP] Analyzing coverage for '{topic}' in project '{project}'")
        
        for truth_type in truth_types:
            result = self._check_truth_coverage(topic, truth_type, project)
            
            if result['has_coverage']:
                covered.append(truth_type)
                logger.debug(f"[GAP] {truth_type}: covered (score={result['best_score']:.2f})")
            else:
                gap = Gap(
                    truth_type=truth_type,
                    topic=topic,
                    severity=DEFAULT_SEVERITY.get(truth_type, 'medium'),
                    query_used=result['query'],
                    best_match_score=result['best_score'],
                    best_match_doc=result['best_doc'],
                    project=project or '',
                )
                gaps.append(gap)
                logger.info(f"[GAP] {truth_type}: GAP DETECTED (best_score={result['best_score']:.2f})")
        
        analysis = GapAnalysis(
            topic=topic,
            project=project or '',
            gaps=gaps,
            covered_truths=covered,
        )
        
        logger.info(f"[GAP] Analysis complete: {analysis.summary()}")
        
        return analysis
    
    def detect_gaps_from_truths(self,
                                 topic: str,
                                 reference: List = None,
                                 regulatory: List = None,
                                 compliance: List = None,
                                 intent: List = None,
                                 project: str = None) -> GapAnalysis:
        """
        Detect gaps from already-gathered truth lists.
        
        Use this when truths have already been gathered by the engine,
        rather than searching again.
        
        Args:
            topic: The topic being analyzed
            reference: List of reference Truth objects
            regulatory: List of regulatory Truth objects
            compliance: List of compliance Truth objects
            intent: List of intent Truth objects
            project: Project ID
            
        Returns:
            GapAnalysis with gaps and coverage info
        """
        gaps = []
        covered = []
        
        truth_lists = {
            'reference': reference or [],
            'regulatory': regulatory or [],
            'compliance': compliance or [],
            'intent': intent or [],
        }
        
        for truth_type, truths in truth_lists.items():
            if self._has_sufficient_coverage(truths):
                covered.append(truth_type)
            else:
                best_score, best_doc = self._get_best_match_info(truths)
                gap = Gap(
                    truth_type=truth_type,
                    topic=topic,
                    severity=DEFAULT_SEVERITY.get(truth_type, 'medium'),
                    best_match_score=best_score,
                    best_match_doc=best_doc,
                    project=project or '',
                )
                gaps.append(gap)
        
        return GapAnalysis(
            topic=topic,
            project=project or '',
            gaps=gaps,
            covered_truths=covered,
        )
    
    def _check_truth_coverage(self, 
                               topic: str, 
                               truth_type: str,
                               project: str = None) -> Dict:
        """
        Check if a truth type has coverage for a topic.
        
        Returns dict with:
        - has_coverage: bool
        - best_score: float
        - best_doc: str
        - query: str
        """
        result = {
            'has_coverage': False,
            'best_score': 0.0,
            'best_doc': '',
            'query': topic,
        }
        
        if not self.rag_handler:
            logger.warning(f"[GAP] No RAG handler - cannot check {truth_type} coverage")
            return result
        
        try:
            # Search for the topic in this truth type
            # Use metadata filter for truth_type if available
            search_results = self.rag_handler.search(
                query=topic,
                n_results=3,
                where={"truth_type": truth_type} if truth_type else None
            )
            
            if search_results:
                # Get best result
                best = search_results[0]
                
                # Extract score (distance to similarity)
                distance = best.get('distance', 1.0)
                score = max(0.0, 1.0 - (distance / 2.0))
                
                # Check if score from relevance scorer is available
                if '_relevance' in best:
                    score = best['_relevance'].get('_score_final', score)
                
                result['best_score'] = score
                result['best_doc'] = best.get('metadata', {}).get('filename', 'unknown')
                result['has_coverage'] = score >= self.coverage_threshold
                
        except Exception as e:
            logger.warning(f"[GAP] Error checking {truth_type} coverage: {e}")
        
        return result
    
    def _has_sufficient_coverage(self, truths: List) -> bool:
        """Check if a list of truths provides sufficient coverage."""
        if not truths:
            return False
        
        # Check if any truth meets the threshold
        for truth in truths:
            confidence = getattr(truth, 'confidence', 0.0)
            if confidence >= self.coverage_threshold:
                return True
        
        return False
    
    def _get_best_match_info(self, truths: List) -> Tuple[float, str]:
        """Get best score and document name from truth list."""
        if not truths:
            return 0.0, ''
        
        best_score = 0.0
        best_doc = ''
        
        for truth in truths:
            confidence = getattr(truth, 'confidence', 0.0)
            if confidence > best_score:
                best_score = confidence
                metadata = getattr(truth, 'metadata', {}) or {}
                best_doc = metadata.get('filename', getattr(truth, 'source_name', ''))
        
        return best_score, best_doc


# =============================================================================
# SINGLETON AND CONVENIENCE FUNCTIONS
# =============================================================================

_detector_instance: Optional[GapDetector] = None

def get_detector(rag_handler=None, 
                 coverage_threshold: float = COVERAGE_THRESHOLD) -> GapDetector:
    """Get the singleton GapDetector instance."""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = GapDetector(rag_handler, coverage_threshold)
    elif rag_handler and not _detector_instance.rag_handler:
        _detector_instance.rag_handler = rag_handler
    return _detector_instance


def detect_gaps(topic: str, 
                project: str = None,
                rag_handler=None) -> GapAnalysis:
    """
    Convenience function to detect gaps for a topic.
    
    Args:
        topic: Topic to check coverage for
        project: Project ID
        rag_handler: RAGHandler instance
        
    Returns:
        GapAnalysis with gaps and coverage info
    """
    detector = get_detector(rag_handler)
    return detector.detect_gaps(topic, project)


def detect_gaps_from_gathered(topic: str,
                               reference: List = None,
                               regulatory: List = None,
                               compliance: List = None,
                               intent: List = None,
                               project: str = None) -> GapAnalysis:
    """
    Convenience function to detect gaps from already-gathered truths.
    """
    detector = get_detector()
    return detector.detect_gaps_from_truths(
        topic=topic,
        reference=reference,
        regulatory=regulatory,
        compliance=compliance,
        intent=intent,
        project=project
    )
