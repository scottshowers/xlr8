"""
RAG (Retrieval Augmented Generation) Handler for XLR8
Manages ChromaDB vector store for HCMPACT knowledge base
"""

import chromadb
from chromadb.config import Settings
import hashlib
import re
from typing import List, Dict, Any
import requests
from requests.auth import HTTPBasicAuth


class RAGHandler:
    """Handles vector storage and semantic search for HCMPACT documents"""
    
    def __init__(self, persist_directory: str = "/root/.xlr8_chroma"):
        """
        Initialize ChromaDB client
        
        Args:
            persist_directory: Where to store the vector database
        """
        self.persist_directory = persist_directory
        
        # Initialize ChromaDB with persistence
        self.client = chromadb.Client(Settings(
            persist_directory=persist_directory,
            anonymized_telemetry=False
        ))
        
        # Get or create collection for HCMPACT knowledge
        self.collection = self.client.get_or_create_collection(
            name="hcmpact_knowledge",
            metadata={"description": "HCMPACT standards and best practices"}
        )
        
        # Ollama embedding endpoint
        self.embed_endpoint = "http://localhost:11435"
        self.embed_model = "nomic-embed-text"
        self.embed_username = "xlr8"
        self.embed_password = "Argyle76226#"
    
    def chunk_document(self, content: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """
        Split document into overlapping chunks for better retrieval
        
        Args:
            content: Document text content
            chunk_size: Target characters per chunk
            overlap: Characters to overlap between chunks
            
        Returns:
            List of text chunks
        """
        # Clean up content
        content = re.sub(r'\s+', ' ', content).strip()
        
        if len(content) <= chunk_size:
            return [content]
        
        chunks = []
        start = 0
        
        while start < len(content):
            end = start + chunk_size
            
            # Try to break at sentence boundary
            if end < len(content):
                # Look for sentence endings near the target
                for i in range(end, max(start + chunk_size - 100, start), -1):
                    if content[i] in '.!?\n':
                        end = i + 1
                        break
            
            chunk = content[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start with overlap
            start = end - overlap
        
        return chunks
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text using Ollama
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        try:
            url = f"{self.embed_endpoint}/api/embeddings"
            
            payload = {
                "model": self.embed_model,
                "prompt": text
            }
            
            auth = HTTPBasicAuth(self.embed_username, self.embed_password)
            
            response = requests.post(url, json=payload, auth=auth, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            return result.get('embedding', [])
            
        except Exception as e:
            print(f"Error generating embedding: {e}")
            # Return zero vector as fallback
            return [0.0] * 768  # nomic-embed-text dimension
    
    def add_document(self, name: str, content: str, category: str, metadata: Dict[str, Any] = None) -> int:
        """
        Add a document to the vector store
        
        Args:
            name: Document name
            content: Document text content
            category: Document category (PRO Core, WFM, etc.)
            metadata: Additional metadata
            
        Returns:
            Number of chunks added
        """
        # Generate unique document ID
        doc_id = hashlib.md5(f"{name}_{category}".encode()).hexdigest()
        
        # Delete existing document if it exists (update scenario)
        try:
            self.collection.delete(where={"doc_id": doc_id})
        except:
            pass
        
        # Chunk the document
        chunks = self.chunk_document(content)
        
        # Prepare data for ChromaDB
        ids = []
        embeddings = []
        documents = []
        metadatas = []
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}_chunk_{i}"
            ids.append(chunk_id)
            
            # Generate embedding
            embedding = self.generate_embedding(chunk)
            embeddings.append(embedding)
            
            documents.append(chunk)
            
            # Metadata
            chunk_metadata = {
                "doc_id": doc_id,
                "doc_name": name,
                "category": category,
                "chunk_index": i,
                "total_chunks": len(chunks)
            }
            if metadata:
                chunk_metadata.update(metadata)
            
            metadatas.append(chunk_metadata)
        
        # Add to collection
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        
        return len(chunks)
    
    def search(self, query: str, n_results: int = 5, category_filter: str = None) -> List[Dict[str, Any]]:
        """
        Semantic search across knowledge base
        
        Args:
            query: Search query
            n_results: Number of results to return
            category_filter: Optional category to filter by
            
        Returns:
            List of search results with content and metadata
        """
        # Generate query embedding
        query_embedding = self.generate_embedding(query)
        
        # Build where clause for filtering
        where_clause = None
        if category_filter:
            where_clause = {"category": category_filter}
        
        # Search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_clause
        )
        
        # Format results
        formatted_results = []
        
        if results and results['documents'] and len(results['documents']) > 0:
            for i in range(len(results['documents'][0])):
                result = {
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if 'distances' in results else None
                }
                formatted_results.append(result)
        
        return formatted_results
    
    def delete_document(self, name: str, category: str):
        """
        Delete a document from the vector store
        
        Args:
            name: Document name
            category: Document category
        """
        doc_id = hashlib.md5(f"{name}_{category}".encode()).hexdigest()
        
        try:
            self.collection.delete(where={"doc_id": doc_id})
        except Exception as e:
            print(f"Error deleting document: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the knowledge base
        
        Returns:
            Dictionary with stats
        """
        count = self.collection.count()
        
        # Get unique documents
        all_results = self.collection.get()
        unique_docs = set()
        categories = {}
        
        if all_results and all_results['metadatas']:
            for metadata in all_results['metadatas']:
                doc_id = metadata.get('doc_id')
                if doc_id:
                    unique_docs.add(doc_id)
                
                category = metadata.get('category', 'Unknown')
                categories[category] = categories.get(category, 0) + 1
        
        return {
            'total_chunks': count,
            'unique_documents': len(unique_docs),
            'categories': categories
        }
    
    def clear_all(self):
        """Clear all documents from the knowledge base"""
        try:
            self.client.delete_collection("hcmpact_knowledge")
            self.collection = self.client.get_or_create_collection(
                name="hcmpact_knowledge",
                metadata={"description": "HCMPACT standards and best practices"}
            )
        except Exception as e:
            print(f"Error clearing collection: {e}")
