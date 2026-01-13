"""
Citation Tracker for Five Truths Architecture
==============================================

Tracks provenance so responses can cite their sources.
Collects, deduplicates, and formats citations from retrieved truths.

Citation Structure:
- Source document (filename)
- Location (page, section, chunk)
- Truth type (reference, regulatory, intent, compliance)
- Source authority (government, vendor, customer, etc.)
- Relevance score
- Text excerpt

Phase 2B.5 Implementation - January 2026
"""

import logging
from typing import List, Dict, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Citation:
    """
    A citation to source material.
    
    Tracks exactly where information came from so responses can
    reference their sources with confidence.
    """
    # Source identification
    source_document: str        # Original filename
    source_type: str           # truth_type: reference, regulatory, intent, compliance
    source_authority: str      # government, vendor, customer, internal
    
    # Location within document
    page_number: Optional[int] = None
    section: Optional[str] = None
    chunk_index: Optional[int] = None
    
    # Content
    excerpt: str = ""          # Relevant text excerpt (truncated)
    full_text: str = ""        # Full chunk text (for internal use)
    
    # Scoring
    relevance_score: float = 0.0
    
    # Additional metadata
    domain: Optional[str] = None
    effective_date: Optional[str] = None
    jurisdiction: Optional[str] = None
    
    # Unique identifier for deduplication
    _chunk_id: str = field(default="", repr=False)
    
    def __post_init__(self):
        """Generate chunk ID if not provided."""
        if not self._chunk_id:
            self._chunk_id = f"{self.source_document}:{self.chunk_index or 0}"
    
    def to_display(self, style: str = "brief") -> str:
        """
        Format citation for display.
        
        Styles:
        - brief: [Document, p.X]
        - full: [Document, p.X, Section Y] (authority)
        - academic: Author (Year). Document. Page X.
        """
        if style == "brief":
            if self.page_number:
                return f"[{self.source_document}, p.{self.page_number}]"
            else:
                return f"[{self.source_document}]"
        
        elif style == "full":
            parts = [self.source_document]
            if self.page_number:
                parts.append(f"p.{self.page_number}")
            if self.section:
                parts.append(self.section)
            location = ", ".join(parts)
            return f"[{location}] ({self.source_authority})"
        
        elif style == "academic":
            # For formal reports
            date_part = f" ({self.effective_date[:4]})" if self.effective_date else ""
            page_part = f" Page {self.page_number}." if self.page_number else ""
            return f"{self.source_authority.title()}{date_part}. {self.source_document}.{page_part}"
        
        return f"[{self.source_document}]"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'source_document': self.source_document,
            'source_type': self.source_type,
            'source_authority': self.source_authority,
            'page_number': self.page_number,
            'section': self.section,
            'chunk_index': self.chunk_index,
            'excerpt': self.excerpt,
            'relevance_score': round(self.relevance_score, 3),
            'domain': self.domain,
            'effective_date': self.effective_date,
            'jurisdiction': self.jurisdiction,
        }


class CitationCollector:
    """
    Collect and deduplicate citations during retrieval.
    
    Used by the engine to track all sources consulted while
    answering a question, then format them for the response.
    """
    
    def __init__(self, max_excerpt_length: int = 200):
        """
        Initialize the collector.
        
        Args:
            max_excerpt_length: Maximum characters for excerpt preview
        """
        self.citations: List[Citation] = []
        self.seen_chunks: Set[str] = set()
        self.max_excerpt_length = max_excerpt_length
        self._question: str = ""
        self._timestamp: datetime = datetime.now()
    
    def set_question(self, question: str):
        """Set the question being answered (for context)."""
        self._question = question
        self._timestamp = datetime.now()
    
    def add_from_truth(self, truth) -> Optional[Citation]:
        """
        Add citation from a Truth object.
        
        Args:
            truth: A Truth object from gatherers
            
        Returns:
            Citation if added, None if duplicate
        """
        metadata = getattr(truth, 'metadata', {}) or {}
        
        # Build chunk ID for deduplication
        filename = metadata.get('filename', getattr(truth, 'source_name', 'unknown'))
        chunk_index = metadata.get('chunk_index', 0)
        chunk_id = f"{filename}:{chunk_index}"
        
        if chunk_id in self.seen_chunks:
            return None
        
        self.seen_chunks.add(chunk_id)
        
        # Extract text content
        content = getattr(truth, 'content', {})
        if isinstance(content, dict):
            full_text = content.get('text', str(content))
        else:
            full_text = str(content)
        
        excerpt = full_text[:self.max_excerpt_length]
        if len(full_text) > self.max_excerpt_length:
            excerpt += "..."
        
        citation = Citation(
            source_document=filename,
            source_type=metadata.get('truth_type', getattr(truth, 'source_type', 'unknown')),
            source_authority=metadata.get('source_authority', 'unknown'),
            page_number=metadata.get('page'),
            section=metadata.get('section') or metadata.get('parent_section'),
            chunk_index=chunk_index,
            excerpt=excerpt,
            full_text=full_text,
            relevance_score=getattr(truth, 'confidence', metadata.get('_score_final', 0.5)),
            domain=metadata.get('domain'),
            effective_date=metadata.get('effective_date'),
            jurisdiction=metadata.get('jurisdiction'),
            _chunk_id=chunk_id
        )
        
        self.citations.append(citation)
        return citation
    
    def add_from_result(self, result: Dict) -> Optional[Citation]:
        """
        Add citation from a raw ChromaDB result dict.
        
        Args:
            result: Dict with 'document', 'metadata', 'distance'
            
        Returns:
            Citation if added, None if duplicate
        """
        metadata = result.get('metadata', {})
        
        filename = metadata.get('filename', metadata.get('source', 'unknown'))
        chunk_index = metadata.get('chunk_index', 0)
        chunk_id = f"{filename}:{chunk_index}"
        
        if chunk_id in self.seen_chunks:
            return None
        
        self.seen_chunks.add(chunk_id)
        
        full_text = result.get('document', '')
        excerpt = full_text[:self.max_excerpt_length]
        if len(full_text) > self.max_excerpt_length:
            excerpt += "..."
        
        # Get relevance score (from 2B.4 or compute from distance)
        relevance = result.get('_relevance', {})
        if relevance:
            score = relevance.get('_score_final', 0.5)
        else:
            distance = result.get('distance', 1.0)
            score = max(0.0, 1.0 - (distance / 2.0))
        
        citation = Citation(
            source_document=filename,
            source_type=metadata.get('truth_type', 'unknown'),
            source_authority=metadata.get('source_authority', 'unknown'),
            page_number=metadata.get('page'),
            section=metadata.get('section'),
            chunk_index=chunk_index,
            excerpt=excerpt,
            full_text=full_text,
            relevance_score=score,
            domain=metadata.get('domain'),
            effective_date=metadata.get('effective_date'),
            jurisdiction=metadata.get('jurisdiction'),
            _chunk_id=chunk_id
        )
        
        self.citations.append(citation)
        return citation
    
    def get_all_citations(self) -> List[Citation]:
        """Get all collected citations."""
        return self.citations
    
    def get_top_citations(self, n: int = 5) -> List[Citation]:
        """
        Get top N citations by relevance score.
        
        Args:
            n: Number of citations to return
            
        Returns:
            List of top citations, sorted by relevance
        """
        sorted_citations = sorted(
            self.citations,
            key=lambda c: c.relevance_score,
            reverse=True
        )
        return sorted_citations[:n]
    
    def get_citations_by_type(self, source_type: str) -> List[Citation]:
        """Get all citations of a specific truth type."""
        return [c for c in self.citations if c.source_type == source_type]
    
    def get_citations_by_authority(self, authority: str) -> List[Citation]:
        """Get all citations from a specific authority."""
        return [c for c in self.citations if c.source_authority == authority]
    
    def format_bibliography(self, style: str = "brief", max_citations: int = 10) -> str:
        """
        Format all citations as a bibliography.
        
        Args:
            style: Citation style (brief, full, academic)
            max_citations: Maximum number to include
            
        Returns:
            Formatted bibliography string
        """
        top = self.get_top_citations(max_citations)
        
        if not top:
            return ""
        
        lines = ["**Sources:**"]
        for i, citation in enumerate(top, 1):
            lines.append(f"{i}. {citation.to_display(style)}")
        
        return "\n".join(lines)
    
    def format_inline_citations(self, max_citations: int = 3) -> str:
        """
        Format citations for inline display in response.
        
        Args:
            max_citations: Maximum to show inline
            
        Returns:
            Inline citation string like "(IRS Pub 15; UKG Best Practices)"
        """
        top = self.get_top_citations(max_citations)
        
        if not top:
            return ""
        
        # Use short document names
        names = []
        for c in top:
            name = c.source_document
            # Truncate long filenames
            if len(name) > 30:
                name = name[:27] + "..."
            names.append(name)
        
        return f"({'; '.join(names)})"
    
    def to_dict(self) -> Dict:
        """Convert collector state to dictionary."""
        return {
            'question': self._question,
            'timestamp': self._timestamp.isoformat(),
            'total_citations': len(self.citations),
            'citations': [c.to_dict() for c in self.citations]
        }
    
    def clear(self):
        """Clear all collected citations."""
        self.citations = []
        self.seen_chunks = set()
        self._question = ""
    
    def summary(self) -> str:
        """Get a summary of collected citations."""
        if not self.citations:
            return "No citations collected"
        
        by_type = {}
        by_authority = {}
        
        for c in self.citations:
            by_type[c.source_type] = by_type.get(c.source_type, 0) + 1
            by_authority[c.source_authority] = by_authority.get(c.source_authority, 0) + 1
        
        type_str = ", ".join(f"{k}:{v}" for k, v in sorted(by_type.items()))
        auth_str = ", ".join(f"{k}:{v}" for k, v in sorted(by_authority.items()))
        
        return f"{len(self.citations)} citations | By type: {type_str} | By authority: {auth_str}"


# =============================================================================
# SINGLETON AND CONVENIENCE FUNCTIONS
# =============================================================================

def create_collector(max_excerpt_length: int = 200) -> CitationCollector:
    """Create a new CitationCollector instance."""
    return CitationCollector(max_excerpt_length)


def collect_citations_from_truths(truths: List, question: str = "") -> CitationCollector:
    """
    Convenience function to collect citations from a list of truths.
    
    Args:
        truths: List of Truth objects
        question: The question being answered
        
    Returns:
        CitationCollector with all citations
    """
    collector = CitationCollector()
    collector.set_question(question)
    
    for truth in truths:
        collector.add_from_truth(truth)
    
    return collector
