"""
XLR8 Intelligence Engine - Intent Gatherer
===========================================

Gathers INTENT truths - what the customer says they want.

Storage: ChromaDB (semantic search)
Source: Customer documents (SOWs, requirements, meeting notes)
Scope: Project-scoped (filtered by project_id)

Deploy to: backend/utils/intelligence/gatherers/intent.py
"""

import logging
from typing import Dict, List, Any

from .base import ChromaDBGatherer
from ..types import Truth, TruthType

logger = logging.getLogger(__name__)


class IntentGatherer(ChromaDBGatherer):
    """
    Gathers Intent truths from ChromaDB.
    
    Intent represents what the customer says they want:
    - Statements of Work (SOWs)
    - Requirements documents
    - Meeting notes
    - Project specifications
    
    This gatherer:
    1. Takes a question and analysis context
    2. Performs semantic search in ChromaDB
    3. Returns Truth objects with full provenance
    """
    
    truth_type = TruthType.INTENT
    
    def __init__(self, project_name: str, project_id: str = None,
                 rag_handler=None):
        """
        Initialize Intent gatherer.
        
        Args:
            project_name: Project code
            project_id: Project UUID (required for scoping)
            rag_handler: ChromaDB/RAG handler instance
        """
        super().__init__(project_name, project_id, rag_handler)
    
    def gather(self, question: str, context: Dict[str, Any]) -> List[Truth]:
        """
        Gather Intent truths for the question.
        
        Args:
            question: User's question
            context: Analysis context
            
        Returns:
            List of Truth objects from customer intent documents
        """
        self.log_gather_start(question)
        
        if not self.rag_handler:
            logger.debug("[GATHER-INTENT] No RAG handler available")
            return []
        
        if not self.project_id:
            logger.debug("[GATHER-INTENT] No project_id - intent is project-scoped")
            return []
        
        truths = []
        
        try:
            # Search for intent documents in this project
            # ChromaDB requires $and for multiple conditions
            where_filter = {"$and": [
                {"project_id": self.project_id},
                {"truth_type": "intent"}
            ]} if self.project_id else {"truth_type": "intent"}
            
            results = self.rag_handler.search(
                collection_name="documents",  # CRITICAL: Must specify collection
                query=question,
                n_results=5,
                where=where_filter
            )
            
            # Process results - rag_handler.search returns list of dicts
            # Format: [{'document': str, 'metadata': dict, 'distance': float}, ...]
            for result in results:
                doc = result.get('document', '')
                metadata = result.get('metadata', {})
                distance = result.get('distance', 1.0)
                
                if not doc:
                    continue
                
                # Convert distance to confidence (lower distance = higher confidence)
                confidence = max(0.5, 1.0 - (distance / 2.0))
                
                truth = self.create_truth(
                    source_name=metadata.get('filename', 'Customer Document'),
                    content={
                        'text': doc,
                        'metadata': metadata,
                        'chunk_index': metadata.get('chunk_index'),
                        'page': metadata.get('page'),
                        'section': metadata.get('section')
                    },
                    location=self._build_location(metadata),
                    confidence=confidence,
                    distance=distance,
                    filename=metadata.get('filename'),
                    page=metadata.get('page')
                )
                truths.append(truth)
                
        except Exception as e:
            logger.error(f"[GATHER-INTENT] Error: {e}")
        
        self.log_gather_result(truths)
        return truths
    
    def _build_location(self, metadata: Dict) -> str:
        """Build a human-readable location string."""
        parts = []
        
        if metadata.get('filename'):
            parts.append(metadata['filename'])
        if metadata.get('page'):
            parts.append(f"Page {metadata['page']}")
        if metadata.get('section'):
            parts.append(metadata['section'])
            
        return ' > '.join(parts) if parts else 'Unknown location'
