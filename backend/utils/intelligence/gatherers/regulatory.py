"""
XLR8 Intelligence Engine - Regulatory Gatherer
===============================================

Gathers REGULATORY truths - laws, rules, and compliance requirements.

Storage: ChromaDB (semantic search)
Source: Laws, IRS rules, DOL guidelines, state/federal mandates
Scope: GLOBAL (no customer_id filter - regulations apply to all)

Deploy to: backend/utils/intelligence/gatherers/regulatory.py
"""

import logging
from typing import Dict, List, Any

from .base import ChromaDBGatherer
from ..types import Truth, TruthType

logger = logging.getLogger(__name__)


class RegulatoryGatherer(ChromaDBGatherer):
    """
    Gathers Regulatory truths from ChromaDB.
    
    Regulatory represents laws and compliance requirements:
    - Federal laws (FLSA, ACA, ERISA, etc.)
    - IRS rules and publications
    - DOL guidelines
    - State-specific mandates
    - Secure 2.0, COBRA, etc.
    
    IMPORTANT: Regulatory is GLOBAL - it applies to all projects.
    We do NOT filter by customer_id.
    
    This enables compliance checking:
    - Regulatory says "Secure 2.0 requires X"
    - Configuration shows "Customer has Y"
    - Reality shows "Z employees affected"
    → Gap: "Customer needs to configure X for Z employees"
    """
    
    truth_type = TruthType.REGULATORY
    
    def __init__(self, project_name: str = None, customer_id: str = None,
                 rag_handler=None):
        """
        Initialize Regulatory gatherer.
        
        Args:
            project_name: Project code (optional, for logging only)
            customer_id: Project UUID (NOT used for filtering - Regulatory is global)
            rag_handler: ChromaDB/RAG handler instance
        """
        super().__init__(project_name or "global", customer_id, rag_handler)
    
    def gather(self, question: str, context: Dict[str, Any]) -> List[Truth]:
        """
        Gather Regulatory truths for the question.
        
        Args:
            question: User's question
            context: Analysis context (may contain 'resolver' domain info)
            
        Returns:
            List of Truth objects from regulatory documents
        """
        self.log_gather_start(question)
        
        if not self.rag_handler:
            logger.warning("[GATHER-REGULATORY] No RAG handler available - cannot search ChromaDB")
            return []
        
        truths = []
        
        # v5.1: Get domain from resolver to make search more relevant
        resolver = context.get('resolver', {})
        search_query = question
        
        if resolver.get('resolved'):
            # We know what domain this is - enhance the search query
            domain_hints = {
                'demographics': 'employee workforce FMLA ACA compliance',
                'personal': 'employee workforce FMLA ACA compliance',
                'earnings': 'compensation FLSA overtime wage',
                'deductions': 'benefits ERISA 401k HSA',
                'taxes': 'tax withholding IRS W-4',
            }
            
            table_name = resolver.get('table_name', '').lower()
            for domain, hints in domain_hints.items():
                if domain in table_name:
                    search_query = f"{hints} {question}"
                    logger.warning(f"[GATHER-REGULATORY] Domain-enhanced query: {search_query[:60]}...")
                    break
        
        try:
            # Search GLOBAL regulatory documents (NO customer_id filter)
            logger.warning(f"[GATHER-REGULATORY] Searching ChromaDB for: {search_query[:50]}...")
            results = self.rag_handler.search(
                collection_name="documents",  # CRITICAL: Must specify collection
                query=search_query,  # v5.1: Use domain-enhanced query
                n_results=5,
                where={"truth_type": "regulatory"}  # Global - no customer_id!
            )
            
            logger.warning(f"[GATHER-REGULATORY] Got {len(results)} results from ChromaDB")
            
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
                    source_name=metadata.get('filename', 'Regulatory Document'),
                    content={
                        'text': doc,
                        'metadata': metadata,
                        'chunk_index': metadata.get('chunk_index'),
                        'page': metadata.get('page'),
                        'section': metadata.get('section'),
                        'law': metadata.get('law'),              # e.g., "Secure 2.0"
                        'agency': metadata.get('agency'),        # e.g., "IRS", "DOL"
                        'effective_date': metadata.get('effective_date'),
                        'jurisdiction': metadata.get('jurisdiction')  # e.g., "Federal", "CA"
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
            logger.error(f"[GATHER-REGULATORY] Error: {e}")
        
        self.log_gather_result(truths)
        return truths
    
    def _build_location(self, metadata: Dict) -> str:
        """Build a human-readable location string."""
        parts = []
        
        if metadata.get('law'):
            parts.append(metadata['law'])
        if metadata.get('agency'):
            parts.append(metadata['agency'])
        if metadata.get('filename'):
            parts.append(metadata['filename'])
        if metadata.get('page'):
            parts.append(f"Page {metadata['page']}")
        if metadata.get('section'):
            parts.append(metadata['section'])
            
        return ' > '.join(parts) if parts else 'Regulatory Library'
