"""
RAG (Retrieval Augmented Generation) Handler for XLR8
Manages ChromaDB vector store for HCMPACT knowledge base

FIXED VERSION - November 17, 2025
Changed chunk_size from 500 → 2000 characters
Changed overlap from 50 → 200 characters
Reason: Larger chunks provide better context for UKG implementation documents
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
    
    def chunk_document(self, content: str, chunk_size: int = 2000, overlap: int = 200) -> List[str]:
        """
        Split document into overlapping chunks for better retrieval
        
        FIXED: Changed defaults from 500/50 to 2000/200
        - Larger chunks (2000 chars) provide better context for UKG documents
        - More overlap (200 chars) ensures continuity between chunks
        - Improves search results for implementation questions
        
        Args:
            content: Document text content
            chunk_size: Target characters per chunk (default: 2000, was 500)
            overlap: Characters to overlap between chunks (default: 200, was 50)
            
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
        
        # Chunk the document (now uses 2000/200 defaults)
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
    
    def search(self, query: str, n_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search for relevant documents using semantic similarity
        
        Args:
            query: Search query text
            n_results: Number of results to return
            
        Returns:
            List of relevant document chunks with metadata
        """
        # Generate query embedding
        query_embedding = self.generate_embedding(query)
        
        # Search ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        # Format results
        formatted_results = []
        
        if results and 'ids' in results and len(results['ids']) > 0:
            for i in range(len(results['ids'][0])):
                result = {
                    'id': results['ids'][0][i],
                    'content': results['documents'][0][i],
                    'distance': results['distances'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'document': results['metadatas'][0][i].get('doc_name', 'Unknown'),
                    'category': results['metadatas'][0][i].get('category', 'General')
                }
                formatted_results.append(result)
        
        return formatted_results
    
    def delete_document(self, name: str, category: str) -> bool:
        """
        Delete a document from the vector store
        
        Args:
            name: Document name
            category: Document category
            
        Returns:
            True if deleted successfully
        """
        try:
            doc_id = hashlib.md5(f"{name}_{category}".encode()).hexdigest()
            self.collection.delete(where={"doc_id": doc_id})
            return True
        except Exception as e:
            print(f"Error deleting document: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector store
        
        Returns:
            Dictionary with collection statistics
        """
        try:
            count = self.collection.count()
            
            # Get all metadata to calculate categories
            if count > 0:
                sample = self.collection.get(limit=count)
                categories = {}
                documents = set()
                
                for metadata in sample['metadatas']:
                    cat = metadata.get('category', 'Unknown')
                    categories[cat] = categories.get(cat, 0) + 1
                    documents.add(metadata.get('doc_id', ''))
                
                return {
                    'total_chunks': count,
                    'unique_documents': len(documents),
                    'categories': categories
                }
            
            return {
                'total_chunks': 0,
                'unique_documents': 0,
                'categories': {}
            }
            
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {
                'total_chunks': 0,
                'unique_documents': 0,
                'categories': {}
            }
    
    def clear_collection(self) -> bool:
        """
        Clear all documents from the collection
        
        Returns:
            True if successful
        """
        try:
            # Delete the collection
            self.client.delete_collection(name="hcmpact_knowledge")
            
            # Recreate empty collection
            self.collection = self.client.get_or_create_collection(
                name="hcmpact_knowledge",
                metadata={"description": "HCMPACT standards and best practices"}
            )
            
            return True
        except Exception as e:
            print(f"Error clearing collection: {e}")
            return False
