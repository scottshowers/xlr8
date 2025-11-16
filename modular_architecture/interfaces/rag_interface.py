"""
RAG System Interface Contract
All RAG implementations MUST follow this interface

Ensures RAG systems can be swapped without breaking Chat or Analysis modules.
"""

from typing import Protocol, List, Dict, Any, Optional
from enum import Enum


class SearchMethod(Enum):
    """Supported search methods"""
    SEMANTIC = "semantic"      # Cosine similarity search
    HYBRID = "hybrid"          # Semantic + keyword
    MMR = "mmr"               # Maximum Marginal Relevance
    KEYWORD = "keyword"        # Traditional keyword search


class RAGInterface(Protocol):
    """
    Interface contract for RAG (Retrieval Augmented Generation) systems.
    
    Any RAG implementation must follow this interface to be compatible
    with Chat and Analysis modules.
    
    Team members can create new RAG systems (different vector DBs, algorithms)
    as long as they follow this contract.
    """
    
    def add_document(self, 
                    content: str,
                    doc_name: str,
                    category: str,
                    metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Add a document to the RAG system.
        
        Args:
            content: Full text content of the document
            doc_name: Document name/identifier
            category: Document category (e.g., "UKG_Standards", "Client_Docs")
            metadata: Optional additional metadata
        
        Returns:
            {
                'success': bool,
                'doc_id': str,              # Unique document ID
                'chunks_created': int,       # Number of chunks created
                'embeddings_generated': int, # Number of embeddings
                'processing_time': float,    # Seconds taken
                'errors': List[str]
            }
        
        Example:
            result = rag.add_document(
                content="UKG configuration guide...",
                doc_name="UKG_Config_v2.pdf",
                category="UKG_Standards"
            )
        """
        ...
    
    def search(self,
              query: str,
              method: SearchMethod = SearchMethod.HYBRID,
              n_results: int = 5,
              category_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for relevant document chunks.
        
        Args:
            query: Search query
            method: Search method to use
            n_results: Number of results to return
            category_filter: Optional category to filter by
        
        Returns:
            List of result dictionaries:
            [
                {
                    'text': str,           # Chunk text
                    'doc_name': str,       # Source document
                    'category': str,       # Document category
                    'score': float,        # Relevance score (0-1)
                    'metadata': dict,      # Additional metadata
                    'chunk_id': str        # Unique chunk identifier
                },
                ...
            ]
        
        Example:
            results = rag.search(
                query="How to configure earnings?",
                method=SearchMethod.HYBRID,
                n_results=5,
                category_filter="UKG_Standards"
            )
        """
        ...
    
    def delete_document(self, doc_name: str, category: str) -> Dict[str, Any]:
        """
        Delete a document from the RAG system.
        
        Args:
            doc_name: Document name
            category: Document category
        
        Returns:
            {
                'success': bool,
                'chunks_deleted': int,
                'errors': List[str]
            }
        
        Example:
            result = rag.delete_document("old_config.pdf", "UKG_Standards")
        """
        ...
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get RAG system statistics.
        
        Returns:
            {
                'total_documents': int,
                'total_chunks': int,
                'total_embeddings': int,
                'categories': Dict[str, int],  # Count per category
                'storage_size_mb': float,
                'last_indexed': str            # ISO datetime
            }
        
        Example:
            stats = rag.get_stats()
            print(f"Indexed {stats['total_documents']} documents")
        """
        ...
    
    def list_documents(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all documents in the RAG system.
        
        Args:
            category: Optional category filter
        
        Returns:
            List of document info:
            [
                {
                    'doc_name': str,
                    'category': str,
                    'chunks': int,
                    'added_date': str,
                    'size_kb': float
                },
                ...
            ]
        
        Example:
            docs = rag.list_documents(category="UKG_Standards")
        """
        ...
    
    def clear_category(self, category: str) -> Dict[str, Any]:
        """
        Clear all documents in a category.
        
        Args:
            category: Category to clear
        
        Returns:
            {
                'success': bool,
                'documents_deleted': int,
                'chunks_deleted': int,
                'errors': List[str]
            }
        
        Example:
            result = rag.clear_category("Test_Documents")
        """
        ...
    
    def get_system_info(self) -> Dict[str, str]:
        """
        Get RAG system implementation info.
        
        Returns:
            {
                'name': str,              # e.g., "ChromaDB_RAG"
                'version': str,           # e.g., "1.0.0"
                'vector_db': str,         # e.g., "ChromaDB", "Pinecone"
                'embedding_model': str,   # e.g., "nomic-embed-text"
                'chunk_size': int,        # Characters per chunk
                'chunk_overlap': int      # Overlap between chunks
            }
        
        Example:
            info = rag.get_system_info()
            print(f"Using {info['name']} with {info['vector_db']}")
        """
        ...


class EmbeddingInterface(Protocol):
    """
    Interface for embedding generation systems.
    
    Can be swapped independently from vector storage.
    """
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text.
        
        Args:
            text: Input text
        
        Returns:
            List of floats (embedding vector)
            Length matches model's embedding dimension
        
        Example:
            embedding = embedder.generate_embedding("Sample text")
            # Returns: [0.123, -0.456, 0.789, ...]
        """
        ...
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts (batch processing).
        
        Args:
            texts: List of input texts
        
        Returns:
            List of embedding vectors
        
        Example:
            texts = ["Text 1", "Text 2", "Text 3"]
            embeddings = embedder.generate_embeddings_batch(texts)
        """
        ...
    
    def get_embedding_dimension(self) -> int:
        """
        Get embedding vector dimension.
        
        Returns:
            Dimension of embedding vectors (e.g., 768, 1536)
        
        Example:
            dim = embedder.get_embedding_dimension()
            # Returns: 768
        """
        ...


# Example implementation
class ExampleRAGSystem:
    """
    Example RAG implementation showing interface compliance.
    
    Team members can use this as a template.
    """
    
    def __init__(self):
        self.name = "ExampleRAG"
        self.version = "1.0.0"
        self.documents = {}
    
    def add_document(self, content: str, doc_name: str, 
                    category: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Example implementation"""
        try:
            # Your chunking and embedding logic here
            chunks = self._chunk_text(content)
            embeddings = self._generate_embeddings(chunks)
            
            # Store
            self.documents[f"{category}/{doc_name}"] = {
                'content': content,
                'chunks': chunks,
                'embeddings': embeddings,
                'metadata': metadata or {}
            }
            
            return {
                'success': True,
                'doc_id': f"{category}/{doc_name}",
                'chunks_created': len(chunks),
                'embeddings_generated': len(embeddings),
                'processing_time': 0.5,
                'errors': []
            }
        except Exception as e:
            return {
                'success': False,
                'doc_id': '',
                'chunks_created': 0,
                'embeddings_generated': 0,
                'processing_time': 0.0,
                'errors': [str(e)]
            }
    
    def search(self, query: str, method: SearchMethod = SearchMethod.HYBRID,
              n_results: int = 5, category_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Example implementation"""
        # Your search logic here
        return []
    
    def delete_document(self, doc_name: str, category: str) -> Dict[str, Any]:
        """Example implementation"""
        key = f"{category}/{doc_name}"
        if key in self.documents:
            del self.documents[key]
            return {'success': True, 'chunks_deleted': 0, 'errors': []}
        return {'success': False, 'chunks_deleted': 0, 'errors': ['Not found']}
    
    def get_stats(self) -> Dict[str, Any]:
        """Example implementation"""
        return {
            'total_documents': len(self.documents),
            'total_chunks': 0,
            'total_embeddings': 0,
            'categories': {},
            'storage_size_mb': 0.0,
            'last_indexed': '2025-11-16T00:00:00Z'
        }
    
    def list_documents(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Example implementation"""
        return []
    
    def clear_category(self, category: str) -> Dict[str, Any]:
        """Example implementation"""
        return {'success': True, 'documents_deleted': 0, 'chunks_deleted': 0, 'errors': []}
    
    def get_system_info(self) -> Dict[str, str]:
        """Example implementation"""
        return {
            'name': self.name,
            'version': self.version,
            'vector_db': 'in-memory',
            'embedding_model': 'example',
            'chunk_size': 500,
            'chunk_overlap': 50
        }
    
    # Private helper methods
    def _chunk_text(self, text: str) -> List[str]:
        """Helper: chunk text"""
        return [text]
    
    def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Helper: generate embeddings"""
        return [[0.0] * 768 for _ in texts]
