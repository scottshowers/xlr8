"""
Advanced RAG (Retrieval Augmented Generation) Handler for XLR8
Manages ChromaDB vector store with multiple chunking strategies for optimal retrieval
"""

import chromadb
from chromadb.config import Settings
import hashlib
import re
from typing import List, Dict, Any, Callable
import requests
from requests.auth import HTTPBasicAuth
import nltk
from collections import defaultdict
import os


class AdvancedRAGHandler:
    """
    Advanced RAG handler with multiple chunking strategies.
    Supports: semantic, recursive, sliding window, paragraph-based, adaptive, and all strategies.
    """
    
    def __init__(self, persist_directory: str = "/root/.xlr8_chroma", 
                 embed_endpoint: str = None, embed_username: str = None, embed_password: str = None):
        """
        Initialize ChromaDB client with advanced chunking capabilities
        
        Args:
            persist_directory: Where to store the vector database
            embed_endpoint: Ollama endpoint URL (defaults to env var or localhost)
            embed_username: Username for Ollama auth
            embed_password: Password for Ollama auth
        """
        self.persist_directory = persist_directory
        
        # Download NLTK data if needed
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt', quiet=True)
        
        # Initialize ChromaDB with persistence
        self.client = chromadb.Client(Settings(
            persist_directory=persist_directory,
            anonymized_telemetry=False
        ))
        
        # Collections for different chunking strategies
        self.collections = {}
        self.chunking_strategies = {
            'semantic': self._semantic_chunking,
            'recursive': self._recursive_chunking,
            'sliding': self._sliding_window_chunking,
            'paragraph': self._paragraph_chunking,
            'adaptive': self._adaptive_chunking
        }
        
        # Initialize collections
        for strategy in self.chunking_strategies.keys():
            collection_name = f"hcmpact_{strategy}"
            self.collections[strategy] = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"description": f"HCMPACT knowledge with {strategy} chunking"}
            )
        
        # Ollama embedding endpoint - GET FROM ENVIRONMENT OR PARAMETER
        self.embed_endpoint = embed_endpoint or os.environ.get('LLM_ENDPOINT', 'http://178.156.190.64:11435')
        self.embed_model = "nomic-embed-text"
        self.embed_username = embed_username or os.environ.get('LLM_USERNAME', 'xlr8')
        self.embed_password = embed_password or os.environ.get('LLM_PASSWORD', 'Argyle76226#')
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep punctuation
        text = re.sub(r'[^\w\s.,!?;:()\-\'"]+', '', text)
        return text.strip()
    
    def _semantic_chunking(self, content: str, chunk_size: int = 800) -> List[str]:
        """
        Semantic chunking: Split by sentences and group semantically related ones
        Uses sentence boundaries and tries to keep related sentences together
        """
        content = self._clean_text(content)
        
        # Split into sentences
        try:
            sentences = nltk.sent_tokenize(content)
        except:
            # Fallback if NLTK fails
            sentences = re.split(r'[.!?]+', content)
            sentences = [s.strip() for s in sentences if s.strip()]
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            if current_length + sentence_length > chunk_size and current_chunk:
                # Chunk is full, save it
                chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_length = sentence_length
            else:
                current_chunk.append(sentence)
                current_length += sentence_length
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def _recursive_chunking(self, content: str, chunk_size: int = 800) -> List[str]:
        """
        Recursive chunking: Split by paragraphs, then sentences, then words
        Hierarchical splitting for better coherence
        """
        content = self._clean_text(content)
        
        def split_recursive(text: str, size: int) -> List[str]:
            if len(text) <= size:
                return [text] if text else []
            
            # Try to split by double newline (paragraphs)
            paragraphs = re.split(r'\n\s*\n', text)
            if len(paragraphs) > 1:
                result = []
                for para in paragraphs:
                    result.extend(split_recursive(para, size))
                return result
            
            # Try to split by sentences
            try:
                sentences = nltk.sent_tokenize(text)
            except:
                sentences = re.split(r'[.!?]+', text)
                sentences = [s.strip() for s in sentences if s.strip()]
            
            if len(sentences) > 1:
                mid = len(sentences) // 2
                left = ' '.join(sentences[:mid])
                right = ' '.join(sentences[mid:])
                return split_recursive(left, size) + split_recursive(right, size)
            
            # Last resort: split by words
            words = text.split()
            if len(words) > 1:
                mid = len(words) // 2
                left = ' '.join(words[:mid])
                right = ' '.join(words[mid:])
                return split_recursive(left, size) + split_recursive(right, size)
            
            # Can't split further
            return [text]
        
        return split_recursive(content, chunk_size)
    
    def _sliding_window_chunking(self, content: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
        """
        Sliding window chunking: Fixed-size chunks with overlap
        Good for ensuring no context is lost at boundaries
        """
        content = self._clean_text(content)
        
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
            
            # Slide window with overlap
            start = end - overlap
            
            # Prevent infinite loop
            if start >= len(content) - overlap:
                break
        
        return chunks
    
    def _paragraph_chunking(self, content: str, max_paragraphs_per_chunk: int = 3) -> List[str]:
        """
        Paragraph-based chunking: Keep paragraph integrity
        Groups multiple paragraphs into chunks
        """
        content = self._clean_text(content)
        
        # Split by double newline or multiple spaces
        paragraphs = re.split(r'\n\s*\n|\n{2,}', content)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        if not paragraphs:
            return [content]
        
        chunks = []
        current_chunk = []
        
        for para in paragraphs:
            current_chunk.append(para)
            
            if len(current_chunk) >= max_paragraphs_per_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = []
        
        # Add remaining paragraphs
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks
    
    def _adaptive_chunking(self, content: str, chunk_size: int = 800) -> List[str]:
        """
        Adaptive chunking: Automatically choose best strategy based on content
        Analyzes content structure and selects optimal chunking method
        """
        content = self._clean_text(content)
        
        # Analyze content structure
        has_paragraphs = bool(re.search(r'\n\s*\n', content))
        avg_sentence_length = len(content) / max(len(re.findall(r'[.!?]+', content)), 1)
        has_structure = bool(re.search(r'(Chapter|Section|\d+\.)', content))
        
        # Choose strategy based on analysis
        if has_structure:
            # Structured document: use recursive
            return self._recursive_chunking(content, chunk_size)
        elif has_paragraphs and avg_sentence_length > 100:
            # Long paragraphs: use paragraph chunking
            return self._paragraph_chunking(content)
        elif avg_sentence_length < 50:
            # Short sentences: use semantic
            return self._semantic_chunking(content, chunk_size)
        else:
            # Default: use sliding window for safety
            return self._sliding_window_chunking(content, chunk_size)
    
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
            
            print(f"[EMBED DEBUG] Generating embedding for: '{text[:50]}...'")
            print(f"[EMBED DEBUG] Using endpoint: {url}")
            
            response = requests.post(url, json=payload, auth=auth, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            embedding = result.get('embedding', [])
            
            if not embedding or len(embedding) == 0:
                print(f"[EMBED ERROR] Empty embedding returned!")
                return [0.0] * 768
            
            # Check if embedding is all zeros
            if sum(embedding) == 0.0:
                print(f"[EMBED ERROR] Zero vector returned!")
            else:
                print(f"[EMBED DEBUG] Valid embedding: {len(embedding)} dims, sum={sum(embedding):.2f}")
            
            return embedding
            
        except Exception as e:
            print(f"[EMBED ERROR] Exception: {e}")
            # Return zero vector as fallback
            return [0.0] * 768  # nomic-embed-text dimension
    
    def add_document(self, name: str, content: str, category: str, 
                    chunking_strategy: str = "adaptive", metadata: Dict[str, Any] = None) -> Dict[str, int]:
        """
        Add a document to the vector store using specified or all chunking strategies
        
        Args:
            name: Document name
            content: Document text content
            category: Document category (PRO Core, WFM, etc.)
            chunking_strategy: Strategy to use ("semantic", "recursive", "sliding", 
                             "paragraph", "adaptive", or "all")
            metadata: Additional metadata
            
        Returns:
            Dictionary with strategy names and chunk counts
        """
        # Generate unique document ID
        doc_id = hashlib.md5(f"{name}_{category}".encode()).hexdigest()
        
        # Determine which strategies to use
        if chunking_strategy == "all":
            strategies_to_use = list(self.chunking_strategies.keys())
        elif chunking_strategy in self.chunking_strategies:
            strategies_to_use = [chunking_strategy]
        else:
            # Default to adaptive if invalid strategy specified
            strategies_to_use = ["adaptive"]
        
        results = {}
        
        for strategy in strategies_to_use:
            # Get collection for this strategy
            collection = self.collections[strategy]
            
            # Delete existing document if it exists
            try:
                collection.delete(where={"doc_id": doc_id})
            except:
                pass
            
            # Chunk the document using the strategy
            chunking_func = self.chunking_strategies[strategy]
            chunks = chunking_func(content)
            
            # Prepare data for ChromaDB
            ids = []
            embeddings = []
            documents = []
            metadatas = []
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"{doc_id}_{strategy}_chunk_{i}"
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
                    "chunking_strategy": strategy,
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                }
                if metadata:
                    chunk_metadata.update(metadata)
                
                metadatas.append(chunk_metadata)
            
            # Add to collection
            if ids:  # Only add if we have chunks
                collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas
                )
            
            results[strategy] = len(chunks)
        
        return results
    
    def search(self, query: str, n_results: int = 5, category_filter: str = None,
              chunking_strategy: str = "adaptive") -> List[Dict[str, Any]]:
        """
        Semantic search across knowledge base
        
        Args:
            query: Search query
            n_results: Number of results to return
            category_filter: Optional category to filter by
            chunking_strategy: Which strategy collection to search ("adaptive" default)
            
        Returns:
            List of search results with content and metadata
        """
        print(f"\n=== SEARCH METHOD CALLED ===")
        print(f"Query: '{query}'")
        print(f"Strategy: {chunking_strategy}")
        print(f"Requesting {n_results} results")
        
        # Use adaptive collection by default
        if chunking_strategy not in self.collections:
            chunking_strategy = "adaptive"
        
        collection = self.collections[chunking_strategy]
        print(f"Using collection: {chunking_strategy} (count: {collection.count()})")
        
        # Generate query embedding
        print(f"About to generate embedding for query...")
        query_embedding = self.generate_embedding(query)
        print(f"Query embedding generated: {len(query_embedding)} dims, sum={sum(query_embedding):.4f}")
        
        # Build where clause for filtering
        where_clause = None
        if category_filter:
            where_clause = {"category": category_filter}
        
        # Search
        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_clause,
                include=['embeddings', 'documents', 'metadatas', 'distances']  # Include embeddings for debug
            )
            print(f"Query executed successfully")
        except Exception as e:
            print(f"Search error: {e}")
            return []
        
        # Format results
        formatted_results = []
        
        if results and results['documents'] and len(results['documents']) > 0:
            print(f"\n=== SEARCH RESULTS ===")
            print(f"Found {len(results['documents'][0])} results")
            
            # DEBUG: Check if embeddings are included in results
            if 'embeddings' in results and results['embeddings']:
                first_emb = results['embeddings'][0][0] if results['embeddings'][0] else None
                if first_emb:
                    emb_sum = sum(first_emb)
                    print(f"First result embedding: {len(first_emb)} dims, sum={emb_sum:.4f}")
                    if emb_sum == 0.0:
                        print(f"WARNING: Stored embedding is ZERO VECTOR!")
            
            for i in range(len(results['documents'][0])):
                result = {
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if 'distances' in results else None
                }
                if i == 0:
                    print(f"Top result distance: {result['distance']:.3f}")
                    print(f"Top result content preview: {result['content'][:80]}...")
                formatted_results.append(result)
        
        return formatted_results
    
    def multi_strategy_search(self, query: str, n_results_per_strategy: int = 3,
                             category_filter: str = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search across all chunking strategies and return combined results
        
        Args:
            query: Search query
            n_results_per_strategy: Results to get from each strategy
            category_filter: Optional category filter
            
        Returns:
            Dictionary mapping strategy names to their results
        """
        all_results = {}
        
        for strategy in self.chunking_strategies.keys():
            results = self.search(
                query=query,
                n_results=n_results_per_strategy,
                category_filter=category_filter,
                chunking_strategy=strategy
            )
            all_results[strategy] = results
        
        return all_results
    
    def delete_document(self, name: str, category: str):
        """
        Delete a document from all vector stores
        
        Args:
            name: Document name
            category: Document category
        """
        doc_id = hashlib.md5(f"{name}_{category}".encode()).hexdigest()
        
        for collection in self.collections.values():
            try:
                collection.delete(where={"doc_id": doc_id})
            except Exception as e:
                print(f"Error deleting document: {e}")
    
    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics about the knowledge base for each chunking strategy
        
        Returns:
            Dictionary with stats per strategy
        """
        all_stats = {}
        
        for strategy, collection in self.collections.items():
            count = collection.count()
            
            # Get unique documents
            try:
                all_results = collection.get()
                unique_docs = set()
                categories = {}
                
                if all_results and all_results['metadatas']:
                    for metadata in all_results['metadatas']:
                        doc_id = metadata.get('doc_id')
                        if doc_id:
                            unique_docs.add(doc_id)
                        
                        category = metadata.get('category', 'Unknown')
                        categories[category] = categories.get(category, 0) + 1
                
                all_stats[strategy] = {
                    'total_chunks': count,
                    'unique_documents': len(unique_docs),
                    'categories': categories
                }
            except Exception as e:
                print(f"Error getting stats for {strategy}: {e}")
                all_stats[strategy] = {
                    'total_chunks': 0,
                    'unique_documents': 0,
                    'categories': {}
                }
        
        return all_stats
    
    def clear_all(self):
        """Clear all documents from all knowledge bases"""
        for strategy in list(self.chunking_strategies.keys()):
            try:
                collection_name = f"hcmpact_{strategy}"
                self.client.delete_collection(collection_name)
                
                # Recreate collection
                self.collections[strategy] = self.client.get_or_create_collection(
                    name=collection_name,
                    metadata={"description": f"HCMPACT knowledge with {strategy} chunking"}
                )
            except Exception as e:
                print(f"Error clearing {strategy} collection: {e}")
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about all collections"""
        info = {
            'strategies': list(self.chunking_strategies.keys()),
            'collections': {}
        }
        
        for strategy, collection in self.collections.items():
            info['collections'][strategy] = {
                'name': collection.name,
                'count': collection.count(),
                'metadata': collection.metadata
            }
        
        return info
