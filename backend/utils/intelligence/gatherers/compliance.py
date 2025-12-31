"""
XLR8 Intelligence Engine - Compliance Gatherer
==============================================

Gathers COMPLIANCE truths - audit requirements and controls.

Storage: ChromaDB (semantic search)
Source: SOC 2 requirements, audit controls, compliance frameworks
Scope: GLOBAL (no project_id filter - compliance standards apply to all)

This is a sub-type of Regulatory, focused on:
- Audit requirements
- SOC 2 controls
- Internal compliance policies
- Industry standards

Deploy to: backend/utils/intelligence/gatherers/compliance.py
"""

import logging
from typing import Dict, List, Any

from .base import ChromaDBGatherer
from ..types import Truth, TruthType

logger = logging.getLogger(__name__)


class ComplianceGatherer(ChromaDBGatherer):
    """
    Gathers Compliance truths from ChromaDB.
    
    Compliance represents audit and control requirements:
    - SOC 2 Type I/II controls
    - Internal audit requirements
    - Compliance frameworks (GDPR, HIPAA, etc.)
    - Data retention policies
    - Access control requirements
    
    IMPORTANT: Compliance is GLOBAL - it applies to all projects.
    We do NOT filter by project_id.
    
    Usage in analysis:
    - Compliance says "Require annual review of X"
    - Reality shows "Last review was Y date"
    - → Finding: "X review is overdue by Z months"
    """
    
    truth_type = TruthType.COMPLIANCE
    
    def __init__(self, project_name: str = None, project_id: str = None,
                 rag_handler=None):
        """
        Initialize Compliance gatherer.
        
        Args:
            project_name: Project code (optional, for logging only)
            project_id: Project UUID (NOT used for filtering - Compliance is global)
            rag_handler: ChromaDB/RAG handler instance
        """
        super().__init__(project_name or "global", project_id, rag_handler)
    
    def gather(self, question: str, context: Dict[str, Any]) -> List[Truth]:
        """
        Gather Compliance truths for the question.
        
        Args:
            question: User's question
            context: Analysis context
            
        Returns:
            List of Truth objects from compliance documents
        """
        self.log_gather_start(question)
        
        if not self.rag_handler:
            logger.debug("[GATHER-COMPLIANCE] No RAG handler available")
            return []
        
        truths = []
        
        try:
            # Search GLOBAL compliance documents (NO project_id filter)
            results = self.rag_handler.search(
                collection_name="documents",  # CRITICAL: Must specify collection
                query=question,
                n_results=5,
                where={"truth_type": "compliance"}  # Global - no project_id!
            )
            
            # Process results - rag_handler.search returns list of dicts
            # Format: [{'document': str, 'metadata': dict, 'distance': float}, ...]
            for result in results:
                doc = result.get('document', '')
                metadata = result.get('metadata', {})
                distance = result.get('distance', 1.0)
                
                if not doc:
                    continue
                
                # Convert distance to confidence
                confidence = max(0.5, 1.0 - (distance / 2.0))
                
                truth = self.create_truth(
                    source_name=metadata.get('filename', 'Compliance Document'),
                    content={
                        'text': doc,
                        'metadata': metadata,
                        'chunk_index': metadata.get('chunk_index'),
                        'page': metadata.get('page'),
                        'section': metadata.get('section'),
                        'framework': metadata.get('framework'),    # e.g., "SOC 2", "GDPR"
                        'control_id': metadata.get('control_id'),  # e.g., "CC6.1"
                        'control_type': metadata.get('control_type'),  # e.g., "preventive", "detective"
                        'audit_period': metadata.get('audit_period')
                    },
                    location=self._build_location(metadata),
                    confidence=confidence,
                    distance=distance,
                    filename=metadata.get('filename'),
                    page=metadata.get('page'),
                    is_global=True
                )
                truths.append(truth)
                
        except Exception as e:
            logger.error(f"[GATHER-COMPLIANCE] Error: {e}")
        
        self.log_gather_result(truths)
        return truths
    
    def _build_location(self, metadata: Dict) -> str:
        """Build a human-readable location string."""
        parts = []
        
        if metadata.get('framework'):
            parts.append(metadata['framework'])
        if metadata.get('control_id'):
            parts.append(f"Control {metadata['control_id']}")
        if metadata.get('filename'):
            parts.append(metadata['filename'])
        if metadata.get('page'):
            parts.append(f"Page {metadata['page']}")
        if metadata.get('section'):
            parts.append(metadata['section'])
            
        return ' > '.join(parts) if parts else 'Compliance Library'
