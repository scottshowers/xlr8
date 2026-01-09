"""
XLR8 Intelligence Engine - Reference Gatherer
==============================================

Gathers REFERENCE truths - vendor documentation and best practices.

Storage: ChromaDB (semantic search)
Source: Product docs, how-to guides, implementation standards
Scope: GLOBAL (no project_id filter - these apply to all projects)

Deploy to: backend/utils/intelligence/gatherers/reference.py
"""

import logging
from typing import Dict, List, Any

from .base import ChromaDBGatherer
from ..types import Truth, TruthType

logger = logging.getLogger(__name__)


class ReferenceGatherer(ChromaDBGatherer):
    """
    Gathers Reference truths from ChromaDB.
    
    Reference represents vendor documentation and best practices:
    - Product documentation
    - How-to guides
    - Implementation standards
    - Configuration guides
    - Best practices
    
    IMPORTANT: Reference is GLOBAL - it applies to all projects.
    We do NOT filter by project_id, BUT we DO filter by system (UKG, Workday, etc.)
    
    This enables the "Regulatory ↔ Reference dovetail" described in ARCHITECTURE.md:
    - Regulatory says "Secure 2.0 requires X"
    - Reference says "Here's how UKG implements X"
    """
    
    truth_type = TruthType.REFERENCE
    
    def __init__(self, project_name: str = None, project_id: str = None,
                 rag_handler=None, system: str = None):
        """
        Initialize Reference gatherer.
        
        Args:
            project_name: Project code (optional, for logging only)
            project_id: Project UUID (NOT used for filtering - Reference is global)
            rag_handler: ChromaDB/RAG handler instance
            system: System filter (ukg, workday, etc.) - filters vendor docs
        """
        # Pass project_id to parent but we won't use it for filtering
        super().__init__(project_name or "global", project_id, rag_handler)
        self.system = system.lower() if system else None
    
    def gather(self, question: str, context: Dict[str, Any]) -> List[Truth]:
        """
        Gather Reference truths for the question.
        
        Args:
            question: User's question
            context: Analysis context (may contain 'system' override and 'resolver' domain info)
            
        Returns:
            List of Truth objects from reference documentation
        """
        self.log_gather_start(question)
        
        if not self.rag_handler:
            logger.warning("[GATHER-REFERENCE] No RAG handler available - cannot search ChromaDB")
            return []
        
        truths = []
        
        # Get system from context if not set at init
        system = context.get('system', self.system)
        
        # v5.1: Get domain from resolver to make search more relevant
        # Without this, "what's the headcount?" might return GL Rules docs
        resolver = context.get('resolver', {})
        search_query = question
        
        if resolver.get('resolved'):
            # We know what domain this is - enhance the search query
            domain_hints = {
                'demographics': 'employee headcount workforce',
                'personal': 'employee headcount workforce',  # personal tables are demographics
                'earnings': 'compensation pay earnings',
                'deductions': 'benefits deductions',
                'taxes': 'tax withholding',
                'locations': 'work locations sites',
                'jobs': 'job positions titles',
            }
            
            # Get table name to infer domain
            table_name = resolver.get('table_name', '').lower()
            for domain, hints in domain_hints.items():
                if domain in table_name:
                    search_query = f"{hints} {question}"
                    logger.warning(f"[GATHER-REFERENCE] Domain-enhanced query: {search_query[:60]}...")
                    break
        
        try:
            # Build where clause - Reference is GLOBAL (no project_id)
            # But we DO filter by system for vendor docs
            if system:
                where_clause = {
                    "$and": [
                        {"truth_type": "reference"},
                        {"$or": [
                            {"system": system.lower()},
                            {"system": "universal"},
                            {"system": None}  # Legacy untagged docs
                        ]}
                    ]
                }
                logger.warning(f"[GATHER-REFERENCE] Searching ChromaDB for system={system}: {question[:50]}...")
            else:
                where_clause = {"truth_type": "reference"}
                logger.warning(f"[GATHER-REFERENCE] Searching ChromaDB (all systems): {question[:50]}...")
            
            results = self.rag_handler.search(
                collection_name="documents",
                query=search_query,  # v5.1: Use domain-enhanced query
                n_results=5,
                where=where_clause
            )
            
            logger.warning(f"[GATHER-REFERENCE] Got {len(results)} results from ChromaDB")
            
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
                    source_name=metadata.get('filename', 'Reference Document'),
                    content={
                        'text': doc,
                        'metadata': metadata,
                        'chunk_index': metadata.get('chunk_index'),
                        'page': metadata.get('page'),
                        'section': metadata.get('section'),
                        'product': metadata.get('product'),  # e.g., "UKG Pro"
                        'topic': metadata.get('topic')       # e.g., "Deductions Setup"
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
            logger.error(f"[GATHER-REFERENCE] Error: {e}")
        
        self.log_gather_result(truths)
        return truths
    
    def _build_location(self, metadata: Dict) -> str:
        """Build a human-readable location string."""
        parts = []
        
        if metadata.get('product'):
            parts.append(metadata['product'])
        if metadata.get('filename'):
            parts.append(metadata['filename'])
        if metadata.get('page'):
            parts.append(f"Page {metadata['page']}")
        if metadata.get('section'):
            parts.append(metadata['section'])
            
        return ' > '.join(parts) if parts else 'Reference Library'
