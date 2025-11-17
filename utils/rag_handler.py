import os
import re
import numpy as np
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
import requests
from requests.auth import HTTPBasicAuth
import logging

logger = logging.getLogger(__name__)


class RAGHandler:
    """Handles all RAG operations including document processing, embedding, and retrieval."""
    
    def __init__(
        self, 
        persist_directory: Optional[str] = None,
        embed_endpoint: Optional[str] = None,
        llm_endpoint: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        **kwargs  # Catch any other parameters
    ):
        """Initialize the RAG handler with ChromaDB and embedding configuration.
        
        Args:
            persist_directory: Optional custom directory for ChromaDB storage.
                             If None, uses /data/chromadb or falls back to .chromadb
            embed_endpoint: Optional Ollama endpoint for embeddings (overrides env var)
            llm_endpoint: Optional Ollama endpoint for LLM (overrides env var)
            username: Optional username for Ollama auth
            password: Optional password for Ollama auth
            **kwargs: Additional parameters (ignored for compatibility)
        """
        try:
            # Use provided directory or determine automatically
            if persist_directory is None:
                # Try /data first (Railway volume)
                if os.path.exists("/data") or os.access("/", os.W_OK):
                    try:
                        persist_directory = "/data/chromadb"
                        os.makedirs(persist_directory, exist_ok=True)
                        logger.info(f"Using persistent storage at {persist_directory}")
                    except (OSError, PermissionError) as e:
                        logger.warning(f"Cannot use /data: {e}, falling back to local storage")
                        persist_directory = None
                
                # Fall back to local directory if /data not available
                if persist_directory is None:
                    persist_directory = os.path.join(os.getcwd(), ".chromadb")
                    os.makedirs(persist_directory, exist_ok=True)
                    logger.warning(f"Using local storage at {persist_directory} (will reset on deploy)")
            else:
                # Use provided directory
                os.makedirs(persist_directory, exist_ok=True)
                logger.info(f"Using provided storage at {persist_directory}")
            
            # Initialize ChromaDB with PERSISTENT storage
            try:
                self.client = chromadb.PersistentClient(
                    path=persist_directory,
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True
                    )
                )
                logger.info(f"ChromaDB client initialized successfully at {persist_directory}")
            except Exception as e:
                logger.error(f"Failed to initialize ChromaDB PersistentClient: {e}")
                # Last resort: use in-memory client
                logger.warning("Falling back to in-memory ChromaDB (data will not persist)")
                self.client = chromadb.Client()
            
            # Ollama configuration - use provided values or fall back to env vars
            self.ollama_base_url = (
                embed_endpoint or 
                llm_endpoint or 
                os.getenv("LLM_ENDPOINT", "http://178.156.190.64:11435")
            )
            self.ollama_username = username or os.getenv("LLM_USERNAME", "xlr8")
            self.ollama_password = password or os.getenv("LLM_PASSWORD", "Argyle76226#")
            
            # Embedding settings
            self.embedding_model = "nomic-embed-text"
            self.chunk_size = 800
            self.chunk_overlap = 100
            
            logger.info("RAGHandler initialized successfully")
            logger.info(f"Ollama endpoint: {self.ollama_base_url}")
            
        except Exception as e:
            logger.error(f"Critical error in RAGHandler initialization: {e}")
            raise RuntimeError(f"Failed to initialize RAGHandler: {e}")

    def _normalize_embedding(self, embedding: List[float]) -> List[float]:
        """
        Normalize embedding to unit length (L2 norm = 1.0).
        
        Args:
            embedding: Raw embedding vector
            
        Returns:
            Normalized embedding vector
        """
        embedding_array = np.array(embedding)
        norm = np.linalg.norm(embedding_array)
        
        if norm == 0:
            logger.warning("Zero norm embedding detected, returning as-is")
            return embedding
            
        normalized = embedding_array / norm
        logger.debug(f"Embedding normalized: L2 norm = {np.linalg.norm(normalized):.6f}")
        return normalized.tolist()

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Get normalized embedding from Ollama for the given text.
        
        Args:
            text: Text to embed
            
        Returns:
            Normalized embedding vector or None if failed
        """
        try:
            url = f"{self.ollama_base_url}/api/embeddings"
            payload = {
                "model": self.embedding_model,
                "prompt": text
            }
            
            response = requests.post(
                url,
                json=payload,
                auth=HTTPBasicAuth(self.ollama_username, self.ollama_password),
                timeout=30
            )
            response.raise_for_status()
            
            raw_embedding = response.json()["embedding"]
            
            # Normalize the embedding
            normalized_embedding = self._normalize_embedding(raw_embedding)
            
            return normalized_embedding
            
        except Exception as e:
            logger.error(f"Error getting embedding: {str(e)}")
            return None

    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks with overlap.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of text chunks
        """
        # Clean the text
        text = re.sub(r'\s+', ' ', text).strip()
        
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = start + self.chunk_size
            
            # Try to break at sentence boundary
            if end < text_length:
                # Look for sentence endings
                sentence_end = max(
                    text.rfind('. ', start, end),
                    text.rfind('! ', start, end),
                    text.rfind('? ', start, end)
                )
                if sentence_end > start:
                    end = sentence_end + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - self.chunk_overlap if end < text_length else text_length
        
        logger.info(f"Created {len(chunks)} chunks from text (size={self.chunk_size}, overlap={self.chunk_overlap})")
        return chunks

    def add_document(self, collection_name: str, text: str, metadata: Dict[str, Any]) -> bool:
        """
        Add a document to a ChromaDB collection.
        
        Args:
            collection_name: Name of the collection
            text: Document text
            metadata: Document metadata
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get or create collection
            collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            
            # Chunk the text
            chunks = self.chunk_text(text)
            
            # Process each chunk
            for i, chunk in enumerate(chunks):
                # Get normalized embedding
                embedding = self.get_embedding(chunk)
                if embedding is None:
                    logger.warning(f"Failed to get embedding for chunk {i}, skipping")
                    continue
                
                # Create unique ID
                doc_id = f"{metadata.get('source', 'unknown')}_{i}"
                
                # Add to collection
                collection.add(
                    embeddings=[embedding],
                    documents=[chunk],
                    metadatas=[{**metadata, "chunk_index": i}],
                    ids=[doc_id]
                )
            
            logger.info(f"Added {len(chunks)} chunks to collection '{collection_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Error adding document to collection: {str(e)}")
            return False

    def search(self, collection_name: str, query: str, n_results: int = 12) -> List[Dict[str, Any]]:
        """
        Search for relevant documents in a collection.
        
        Args:
            collection_name: Name of the collection to search
            query: Search query
            n_results: Number of results to return
            
        Returns:
            List of search results with documents, metadata, and distances
        """
        try:
            # Get collection
            collection = self.client.get_collection(name=collection_name)
            
            # Get normalized query embedding
            query_embedding = self.get_embedding(query)
            if query_embedding is None:
                logger.error("Failed to get query embedding")
                return []
            
            # Perform search
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            formatted_results = []
            
            # Check if we have results
            if not results or not results.get('documents'):
                logger.info(f"No results found in collection '{collection_name}'")
                return []
            
            # Check if documents list is empty or contains empty lists
            documents = results['documents']
            if not documents or (isinstance(documents, list) and len(documents) > 0 and not documents[0]):
                logger.info(f"Empty documents in search results for collection '{collection_name}'")
                return []
            
            # Process results
            docs = results['documents'][0] if results['documents'] else []
            metadatas = results['metadatas'][0] if results.get('metadatas') else []
            distances = results['distances'][0] if results.get('distances') else []
            
            for i, doc in enumerate(docs):
                result = {
                    'document': doc,
                    'metadata': metadatas[i] if i < len(metadatas) else {},
                    'distance': distances[i] if i < len(distances) else None
                }
                formatted_results.append(result)
            
            logger.info(f"Search returned {len(formatted_results)} results from '{collection_name}'")
            if formatted_results and formatted_results[0].get('distance') is not None:
                logger.info(f"Best match distance: {formatted_results[0]['distance']:.4f}")
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching collection '{collection_name}': {str(e)}")
            return []

    def list_collections(self) -> List[str]:
        """
        List all available collections.
        
        Returns:
            List of collection names
        """
        try:
            collections = self.client.list_collections()
            return [col.name for col in collections]
        except Exception as e:
            logger.error(f"Error listing collections: {str(e)}")
            return []

    def get_collection_count(self, collection_name: str) -> int:
        """
        Get the number of documents in a collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Number of documents in the collection
        """
        try:
            collection = self.client.get_collection(name=collection_name)
            return collection.count()
        except Exception as e:
            logger.error(f"Error getting collection count: {str(e)}")
            return 0

    def delete_collection(self, collection_name: str) -> bool:
        """
        Delete a collection.
        
        Args:
            collection_name: Name of the collection to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.delete_collection(name=collection_name)
            logger.info(f"Deleted collection '{collection_name}'")
            return True
        except Exception as e:
            logger.error(f"Error deleting collection: {str(e)}")
            return False

    def reset_all(self) -> bool:
        """
        Delete all collections and reset the database.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            collections = self.list_collections()
            for collection_name in collections:
                self.delete_collection(collection_name)
            logger.info("Reset all collections")
            return True
        except Exception as e:
            logger.error(f"Error resetting database: {str(e)}")
            return False


# Backward compatibility alias
AdvancedRAGHandler = RAGHandler
