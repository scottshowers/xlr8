"""
Advanced RAG Handler with Multiple Chunking Strategies
Supports semantic chunking, recursive splitting, sliding window, and hybrid retrieval
"""

import chromadb
from chromadb.config import Settings
import hashlib
import re
from typing import List, Dict, Any, Optional, Tuple
import requests
from requests.auth import HTTPBasicAuth
import numpy as np
from collections import Counter


class AdvancedRAGHandler:
    """Advanced RAG with multiple chunking strategies and hybrid retrieval"""
    
    def __init__(self, persist_directory: str = "/root/.xlr8_chroma"):
        self.persist_directory = persist_directory
        
        # Initialize ChromaDB
        self.client = chromadb.Client(Settings(
            persist_directory=persist_directory,
            anonymized_telemetry=False
        ))
        
        # Collections for different strategies
        self.collections = {
            'semantic': self.client.get_or_create_collection(
                name="hcmpact_semantic",
                metadata={"description": "Semantic chunking strategy"}
            ),
            'recursive': self.client.get_or_create_collection(
                name="hcmpact_recursive",
                metadata={"description": "Recursive character splitting"}
            ),
            'sliding': self.client.get_or_create_collection(
                name="hcmpact_sliding",
                metadata={"description": "Sliding window chunks"}
            ),
            'paragraph': self.client.get_or_create_collection(
                name="hcmpact_paragraph",
                metadata={"description": "Paragraph-based chunks"}
            )
        }
        
        # Ollama config
        self.embed_endpoint = "http://localhost:11435"
        self.embed_model = "nomic-embed-text"
        self.embed_username = "xlr8"
        self.embed_password = "Argyle76226#"
        
        # Cache for embeddings
        self.embedding_cache = {}
    
    # ========================================================================
    # ADVANCED CHUNKING STRATEGIES
    # ========================================================================
    
    def semantic_chunking(self, content: str, similarity_threshold: float = 0.5) -> List[str]:
        """
        Semantic chunking - groups sentences by semantic similarity
        Creates chunks where sentences are topically related
        """
        # Split into sentences
        sentences = self._split_into_sentences(content)
        
        if len(sentences) <= 1:
            return sentences
        
        # Generate embeddings for all sentences
        embeddings = [self._get_cached_embedding(sent) for sent in sentences]
        
        # Group sentences by semantic similarity
        chunks = []
        current_chunk = [sentences[0]]
        
        for i in range(1, len(sentences)):
            # Calculate similarity between current sentence and chunk centroid
            chunk_embedding = np.mean([embeddings[j] for j in range(len(current_chunk))], axis=0)
            similarity = self._cosine_similarity(embeddings[i], chunk_embedding)
            
            if similarity >= similarity_threshold:
                current_chunk.append(sentences[i])
            else:
                # Start new chunk
                chunks.append(' '.join(current_chunk))
                current_chunk = [sentences[i]]
        
        # Add last chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def recursive_character_splitting(self, content: str, 
                                     chunk_size: int = 1000, 
                                     chunk_overlap: int = 200) -> List[str]:
        """
        Recursive character splitting with multiple separators
        Tries to split on paragraph, then sentence, then word boundaries
        """
        separators = ["\n\n", "\n", ". ", " ", ""]
        
        return self._recursive_split(content, chunk_size, chunk_overlap, separators)
    
    def _recursive_split(self, text: str, chunk_size: int, overlap: int, 
                        separators: List[str]) -> List[str]:
        """Helper for recursive splitting"""
        if len(text) <= chunk_size:
            return [text.strip()]
        
        # Try each separator
        for separator in separators:
            if separator and separator in text:
                splits = text.split(separator)
                
                chunks = []
                current_chunk = ""
                
                for split in splits:
                    # Add separator back
                    piece = split + separator if separator else split
                    
                    if len(current_chunk) + len(piece) <= chunk_size:
                        current_chunk += piece
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = piece
                
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                return chunks
        
        # Fallback: hard split at chunk_size
        return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size-overlap)]
    
    def sliding_window_chunking(self, content: str, 
                               window_size: int = 500, 
                               step_size: int = 250) -> List[str]:
        """
        Sliding window approach - overlapping chunks for better context
        Good for ensuring no information is lost at boundaries
        """
        sentences = self._split_into_sentences(content)
        
        if not sentences:
            return []
        
        chunks = []
        current_window = []
        current_length = 0
        
        i = 0
        while i < len(sentences):
            sentence = sentences[i]
            sentence_len = len(sentence)
            
            if current_length + sentence_len > window_size and current_window:
                # Create chunk
                chunks.append(' '.join(current_window))
                
                # Slide window by removing sentences from start
                chars_to_remove = 0
                sentences_removed = 0
                
                while chars_to_remove < step_size and current_window:
                    chars_to_remove += len(current_window[0])
                    current_window.pop(0)
                    sentences_removed += 1
                
                current_length = sum(len(s) for s in current_window)
            else:
                current_window.append(sentence)
                current_length += sentence_len
                i += 1
        
        # Add final window
        if current_window:
            chunks.append(' '.join(current_window))
        
        return chunks
    
    def paragraph_chunking(self, content: str, 
                          min_length: int = 100, 
                          max_length: int = 1500) -> List[str]:
        """
        Paragraph-based chunking with length constraints
        Preserves natural document structure
        """
        # Split on double newlines (paragraphs)
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for para in paragraphs:
            para_len = len(para)
            
            # If single paragraph is too long, split it
            if para_len > max_length:
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_length = 0
                
                # Recursively split long paragraph
                sub_chunks = self.recursive_character_splitting(para, max_length, 200)
                chunks.extend(sub_chunks)
            
            # If adding paragraph exceeds max, start new chunk
            elif current_length + para_len > max_length:
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_length = para_len
            
            # Add to current chunk
            else:
                current_chunk.append(para)
                current_length += para_len
        
        # Add final chunk
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        # Filter out too-short chunks
        chunks = [c for c in chunks if len(c) >= min_length]
        
        return chunks
    
    def adaptive_chunking(self, content: str, target_size: int = 800) -> List[str]:
        """
        Adaptive chunking - combines multiple strategies based on content
        Uses document structure analysis to pick best strategy
        """
        # Analyze document structure
        has_paragraphs = '\n\n' in content
        has_sections = any(h in content for h in ['#', '##', '###'])
        avg_sentence_length = len(content) / max(content.count('.'), 1)
        
        # Choose strategy based on structure
        if has_sections:
            # Document with headers - use paragraph chunking
            return self.paragraph_chunking(content, target_size//2, target_size*2)
        elif has_paragraphs and avg_sentence_length < 200:
            # Well-structured prose - use semantic chunking
            return self.semantic_chunking(content, similarity_threshold=0.6)
        elif avg_sentence_length > 300:
            # Dense technical content - use sliding window
            return self.sliding_window_chunking(content, target_size, target_size//2)
        else:
            # Generic content - use recursive splitting
            return self.recursive_character_splitting(content, target_size, target_size//4)
    
    # ========================================================================
    # ADVANCED RETRIEVAL METHODS
    # ========================================================================
    
    def hybrid_search(self, query: str, 
                     n_results: int = 5, 
                     alpha: float = 0.5,
                     strategy: str = 'semantic') -> List[Dict[str, Any]]:
        """
        Hybrid search combining dense (semantic) and sparse (keyword) retrieval
        alpha: weight for semantic search (1-alpha for keyword search)
        """
        collection = self.collections.get(strategy, self.collections['semantic'])
        
        # Semantic search
        query_embedding = self.generate_embedding(query)
        semantic_results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results * 2  # Get more for reranking
        )
        
        # Keyword search (BM25-like scoring)
        query_terms = self._tokenize(query.lower())
        keyword_scores = self._bm25_score(query_terms, semantic_results)
        
        # Combine scores
        combined_results = []
        if semantic_results['documents'] and len(semantic_results['documents']) > 0:
            for i in range(len(semantic_results['documents'][0])):
                semantic_score = 1 - semantic_results['distances'][0][i]  # Convert distance to similarity
                keyword_score = keyword_scores.get(i, 0)
                
                combined_score = (alpha * semantic_score) + ((1 - alpha) * keyword_score)
                
                combined_results.append({
                    'content': semantic_results['documents'][0][i],
                    'metadata': semantic_results['metadatas'][0][i],
                    'score': combined_score,
                    'semantic_score': semantic_score,
                    'keyword_score': keyword_score
                })
        
        # Sort by combined score and return top n
        combined_results.sort(key=lambda x: x['score'], reverse=True)
        return combined_results[:n_results]
    
    def mmr_search(self, query: str, 
                   n_results: int = 5, 
                   lambda_param: float = 0.5,
                   strategy: str = 'semantic') -> List[Dict[str, Any]]:
        """
        Maximal Marginal Relevance - balances relevance and diversity
        Reduces redundancy in retrieved documents
        """
        collection = self.collections.get(strategy, self.collections['semantic'])
        
        query_embedding = self.generate_embedding(query)
        
        # Get initial candidates (more than needed)
        candidates = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results * 3
        )
        
        if not candidates['documents'] or len(candidates['documents'][0]) == 0:
            return []
        
        # MMR selection
        selected_indices = []
        selected_embeddings = []
        
        # Get embeddings for all candidates
        candidate_embeddings = [
            self._get_cached_embedding(doc) 
            for doc in candidates['documents'][0]
        ]
        
        # Select first document (most relevant)
        selected_indices.append(0)
        selected_embeddings.append(candidate_embeddings[0])
        
        # Iteratively select remaining documents
        for _ in range(n_results - 1):
            best_score = -float('inf')
            best_idx = None
            
            for idx in range(len(candidate_embeddings)):
                if idx in selected_indices:
                    continue
                
                # Relevance to query
                relevance = self._cosine_similarity(query_embedding, candidate_embeddings[idx])
                
                # Diversity (max similarity to already selected)
                max_similarity = max([
                    self._cosine_similarity(candidate_embeddings[idx], sel_emb)
                    for sel_emb in selected_embeddings
                ])
                
                # MMR score
                mmr_score = lambda_param * relevance - (1 - lambda_param) * max_similarity
                
                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx
            
            if best_idx is not None:
                selected_indices.append(best_idx)
                selected_embeddings.append(candidate_embeddings[best_idx])
        
        # Format results
        results = []
        for idx in selected_indices:
            results.append({
                'content': candidates['documents'][0][idx],
                'metadata': candidates['metadatas'][0][idx],
                'distance': candidates['distances'][0][idx] if 'distances' in candidates else None
            })
        
        return results
    
    def rerank_with_cross_encoder(self, query: str, 
                                  candidates: List[Dict[str, Any]],
                                  top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Rerank candidates using cross-encoder for better relevance
        (Simulated - in production would use actual cross-encoder model)
        """
        # Simulate cross-encoder scores based on query-document interaction
        reranked = []
        
        query_terms = set(self._tokenize(query.lower()))
        
        for candidate in candidates:
            doc_text = candidate['content'].lower()
            doc_terms = set(self._tokenize(doc_text))
            
            # Calculate various relevance signals
            term_overlap = len(query_terms & doc_terms) / len(query_terms) if query_terms else 0
            position_bonus = 1.0 if any(term in doc_text[:200] for term in query_terms) else 0.5
            length_penalty = 1.0 / (1.0 + abs(len(doc_text) - 500) / 1000)
            
            # Combined score
            rerank_score = (term_overlap * 0.5) + (position_bonus * 0.3) + (length_penalty * 0.2)
            
            candidate['rerank_score'] = rerank_score
            reranked.append(candidate)
        
        # Sort by rerank score
        reranked.sort(key=lambda x: x['rerank_score'], reverse=True)
        return reranked[:top_k]
    
    def contextual_compression(self, query: str, 
                              retrieved_docs: List[Dict[str, Any]],
                              compression_ratio: float = 0.5) -> List[Dict[str, Any]]:
        """
        Extract only the most relevant parts of each document
        Reduces token usage while maintaining relevance
        """
        compressed_docs = []
        query_terms = set(self._tokenize(query.lower()))
        
        for doc in retrieved_docs:
            content = doc['content']
            sentences = self._split_into_sentences(content)
            
            # Score each sentence
            sentence_scores = []
            for sent in sentences:
                sent_terms = set(self._tokenize(sent.lower()))
                overlap = len(query_terms & sent_terms) / len(query_terms) if query_terms else 0
                sentence_scores.append((sent, overlap))
            
            # Sort by score and take top sentences
            sentence_scores.sort(key=lambda x: x[1], reverse=True)
            num_keep = max(1, int(len(sentences) * compression_ratio))
            kept_sentences = [s[0] for s in sentence_scores[:num_keep]]
            
            # Maintain original order
            compressed_content = ' '.join([s for s in sentences if s in kept_sentences])
            
            compressed_docs.append({
                'content': compressed_content,
                'metadata': doc['metadata'],
                'original_length': len(content),
                'compressed_length': len(compressed_content)
            })
        
        return compressed_docs
    
    def search(self, query: str, n_results: int = 5, category_filter: str = None) -> List[Dict[str, Any]]:
        """
        Basic search method for backwards compatibility
        Uses hybrid search by default
        
        Args:
            query: Search query
            n_results: Number of results
            category_filter: Optional category filter
        
        Returns:
            List of search results
        """
        # Use hybrid search as default
        results = self.hybrid_search(
            query=query,
            n_results=n_results,
            alpha=0.5,
            strategy='semantic'
        )
        
        # Apply category filter if provided
        if category_filter:
            results = [r for r in results if r.get('metadata', {}).get('category') == category_filter]
        
        return results
    
    # ========================================================================
    # DOCUMENT MANAGEMENT
    # ========================================================================
    
    def add_document(self, name: str, content: str, category: str, 
                    metadata: Dict[str, Any] = None,
                    chunking_strategy: str = 'adaptive') -> Dict[str, int]:
        """
        Add document using specified chunking strategy
        Returns counts for each strategy used
        """
        doc_id = hashlib.md5(f"{name}_{category}".encode()).hexdigest()
        
        # Delete existing if updating
        for collection in self.collections.values():
            try:
                collection.delete(where={"doc_id": doc_id})
            except:
                pass
        
        # Apply chunking strategy
        if chunking_strategy == 'semantic':
            chunks = self.semantic_chunking(content)
            target_collections = ['semantic']
        elif chunking_strategy == 'recursive':
            chunks = self.recursive_character_splitting(content)
            target_collections = ['recursive']
        elif chunking_strategy == 'sliding':
            chunks = self.sliding_window_chunking(content)
            target_collections = ['sliding']
        elif chunking_strategy == 'paragraph':
            chunks = self.paragraph_chunking(content)
            target_collections = ['paragraph']
        elif chunking_strategy == 'adaptive':
            chunks = self.adaptive_chunking(content)
            # Store in multiple collections for hybrid retrieval
            target_collections = ['semantic', 'recursive']
        else:  # all
            # Apply all strategies
            chunks_by_strategy = {
                'semantic': self.semantic_chunking(content),
                'recursive': self.recursive_character_splitting(content),
                'sliding': self.sliding_window_chunking(content),
                'paragraph': self.paragraph_chunking(content)
            }
            
            counts = {}
            for strategy, strategy_chunks in chunks_by_strategy.items():
                count = self._add_chunks_to_collection(
                    strategy, doc_id, name, category, strategy_chunks, metadata
                )
                counts[strategy] = count
            
            return counts
        
        # Add to target collections
        counts = {}
        for collection_name in target_collections:
            count = self._add_chunks_to_collection(
                collection_name, doc_id, name, category, chunks, metadata
            )
            counts[collection_name] = count
        
        return counts
    
    def _add_chunks_to_collection(self, collection_name: str, doc_id: str, 
                                  doc_name: str, category: str, 
                                  chunks: List[str], 
                                  metadata: Dict[str, Any] = None) -> int:
        """Helper to add chunks to specific collection"""
        collection = self.collections[collection_name]
        
        ids = []
        embeddings = []
        documents = []
        metadatas = []
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}_{collection_name}_{i}"
            ids.append(chunk_id)
            
            # Generate embedding
            embedding = self.generate_embedding(chunk)
            embeddings.append(embedding)
            documents.append(chunk)
            
            # Metadata
            chunk_metadata = {
                "doc_id": doc_id,
                "doc_name": doc_name,
                "category": category,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "chunking_strategy": collection_name
            }
            if metadata:
                chunk_metadata.update(metadata)
            
            metadatas.append(chunk_metadata)
        
        # Add to collection
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        
        return len(chunks)
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding with caching"""
        # Check cache
        text_hash = hashlib.md5(text.encode()).hexdigest()
        if text_hash in self.embedding_cache:
            return self.embedding_cache[text_hash]
        
        try:
            url = f"{self.embed_endpoint}/api/embeddings"
            payload = {"model": self.embed_model, "prompt": text}
            auth = HTTPBasicAuth(self.embed_username, self.embed_password)
            
            response = requests.post(url, json=payload, auth=auth, timeout=30)
            response.raise_for_status()
            
            embedding = response.json().get('embedding', [])
            
            # Cache it
            self.embedding_cache[text_hash] = embedding
            
            return embedding
        except Exception as e:
            print(f"Embedding error: {e}")
            return [0.0] * 768
    
    def _get_cached_embedding(self, text: str) -> np.ndarray:
        """Get embedding as numpy array"""
        return np.array(self.generate_embedding(text))
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitter
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization"""
        return re.findall(r'\w+', text.lower())
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity"""
        if len(vec1) == 0 or len(vec2) == 0:
            return 0.0
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _bm25_score(self, query_terms: List[str], 
                   search_results: Dict) -> Dict[int, float]:
        """Calculate BM25 scores for search results"""
        if not search_results['documents'] or len(search_results['documents']) == 0:
            return {}
        
        docs = search_results['documents'][0]
        scores = {}
        
        # Parameters
        k1 = 1.5
        b = 0.75
        avgdl = np.mean([len(self._tokenize(doc)) for doc in docs])
        
        # Term frequencies
        for idx, doc in enumerate(docs):
            doc_terms = self._tokenize(doc.lower())
            doc_len = len(doc_terms)
            term_freqs = Counter(doc_terms)
            
            score = 0.0
            for term in query_terms:
                if term in term_freqs:
                    tf = term_freqs[term]
                    idf = 1.0  # Simplified IDF
                    
                    numerator = tf * (k1 + 1)
                    denominator = tf + k1 * (1 - b + b * (doc_len / avgdl))
                    
                    score += idf * (numerator / denominator)
            
            scores[idx] = score
        
        # Normalize
        if scores:
            max_score = max(scores.values())
            if max_score > 0:
                scores = {k: v/max_score for k, v in scores.items()}
        
        return scores
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for all collections"""
        stats = {}
        
        for name, collection in self.collections.items():
            count = collection.count()
            
            # Get unique documents
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
            
            stats[name] = {
                'total_chunks': count,
                'unique_documents': len(unique_docs),
                'categories': categories
            }
        
        return stats
