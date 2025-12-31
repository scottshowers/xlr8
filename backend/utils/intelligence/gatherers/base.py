"""
XLR8 Intelligence Engine - Base Gatherer
=========================================

Abstract base class for all Truth gatherers.

Each Truth type (Reality, Intent, Configuration, Reference, Regulatory)
has a gatherer that knows how to query its storage system and return
properly formatted Truth objects with provenance.

Deploy to: backend/utils/intelligence/gatherers/base.py
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import logging

from ..types import Truth, TruthType, StorageType, TRUTH_ROUTING

logger = logging.getLogger(__name__)


class BaseGatherer(ABC):
    """
    Abstract base class for Truth gatherers.
    
    Each gatherer:
    1. Knows its truth_type (reality, intent, etc.)
    2. Knows its storage_type (duckdb, chromadb)
    3. Implements gather() to query and return Truth objects
    4. Ensures provenance (every Truth traces back to source)
    """
    
    # Subclasses must override these
    truth_type: TruthType = None
    storage_type: StorageType = None
    
    def __init__(self, project_name: str, project_id: str = None):
        """
        Initialize the gatherer.
        
        Args:
            project_name: The project code (e.g., "TEA1000")
            project_id: The project UUID for filtering
        """
        self.project_name = project_name
        self.project_id = project_id
        
        if self.truth_type is None:
            raise NotImplementedError("Subclass must define truth_type")
        if self.storage_type is None:
            raise NotImplementedError("Subclass must define storage_type")
    
    @abstractmethod
    def gather(self, question: str, context: Dict[str, Any]) -> List[Truth]:
        """
        Gather truths relevant to the question.
        
        Args:
            question: The user's question
            context: Additional context (tables, analysis, filters, etc.)
            
        Returns:
            List of Truth objects with proper provenance
        """
        pass
    
    def create_truth(
        self,
        source_name: str,
        content: Any,
        location: str,
        confidence: float = 0.8,
        **metadata
    ) -> Truth:
        """
        Create a Truth object with proper provenance.
        
        This helper ensures all Truths have consistent structure.
        
        Args:
            source_name: Name of source (table, document, etc.)
            content: The actual data
            location: Where this came from (table name, page, section)
            confidence: Confidence score 0.0-1.0
            **metadata: Additional metadata (query, row_count, etc.)
            
        Returns:
            Truth object
        """
        return Truth(
            source_type=self.truth_type.value,
            source_name=source_name,
            content=content,
            confidence=confidence,
            location=location,
            metadata={
                'project': self.project_name,
                'storage': self.storage_type.value,
                **metadata
            }
        )
    
    def log_gather_start(self, question: str):
        """Log the start of a gather operation."""
        logger.info(f"[GATHER-{self.truth_type.value.upper()}] "
                   f"Starting for project={self.project_name}")
    
    def log_gather_result(self, truths: List[Truth]):
        """Log the result of a gather operation."""
        logger.info(f"[GATHER-{self.truth_type.value.upper()}] "
                   f"Returning {len(truths)} truths")


class DuckDBGatherer(BaseGatherer):
    """Base class for gatherers that query DuckDB."""
    
    storage_type = StorageType.DUCKDB
    
    def __init__(self, project_name: str, project_id: str = None, 
                 structured_handler=None):
        """
        Initialize DuckDB gatherer.
        
        Args:
            project_name: The project code
            project_id: The project UUID
            structured_handler: DuckDB handler instance
        """
        super().__init__(project_name, project_id)
        self.handler = structured_handler
    
    def execute_sql(self, sql: str) -> List[Dict]:
        """
        Execute SQL and return results as list of dicts.
        
        Args:
            sql: SQL query to execute
            
        Returns:
            List of row dicts
        """
        if not self.handler:
            logger.warning(f"[GATHER-{self.truth_type.value.upper()}] No handler available")
            return []
        
        try:
            return self.handler.query(sql)
        except Exception as e:
            logger.error(f"[GATHER-{self.truth_type.value.upper()}] SQL error: {e}")
            return []


class ChromaDBGatherer(BaseGatherer):
    """Base class for gatherers that query ChromaDB."""
    
    storage_type = StorageType.CHROMADB
    
    def __init__(self, project_name: str, project_id: str = None,
                 rag_handler=None, collection_name: str = None):
        """
        Initialize ChromaDB gatherer.
        
        Args:
            project_name: The project code
            project_id: The project UUID
            rag_handler: RAG/ChromaDB handler instance
            collection_name: Name of the ChromaDB collection
        """
        super().__init__(project_name, project_id)
        self.rag_handler = rag_handler
        self.collection_name = collection_name
    
    def semantic_search(self, query: str, n_results: int = 5, 
                       filters: Dict = None) -> List[Dict]:
        """
        Perform semantic search in ChromaDB.
        
        Args:
            query: Search query
            n_results: Number of results to return
            filters: Optional metadata filters
            
        Returns:
            List of search results with documents and metadata
        """
        if not self.rag_handler:
            logger.warning(f"[GATHER-{self.truth_type.value.upper()}] No RAG handler available")
            return []
        
        try:
            # Build filter for project scoping
            # ChromaDB requires $and for multiple conditions
            conditions = []
            
            if filters:
                for key, value in filters.items():
                    conditions.append({key: value})
            
            if self.project_id:
                conditions.append({"project_id": self.project_id})
            
            # Build where clause
            if len(conditions) == 0:
                where_filter = None
            elif len(conditions) == 1:
                where_filter = conditions[0]
            else:
                where_filter = {"$and": conditions}
            
            results = self.rag_handler.search(
                query=query,
                collection_name=self.collection_name,
                n_results=n_results,
                where=where_filter
            )
            return results
            
        except Exception as e:
            logger.error(f"[GATHER-{self.truth_type.value.upper()}] Search error: {e}")
            return []
