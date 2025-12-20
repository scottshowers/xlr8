"""
RAG Handler for XLR8
Handles all RAG operations including document processing, embedding, and retrieval.

Version: 2.0 - Universal Classification Architecture
- Added truth_type filtering for Three Truths architecture
- Added custom where clause support
- Added helper methods for truth-type specific searches

NOW USES UNIVERSAL DOCUMENT INTELLIGENCE SYSTEM:
- Automatic document structure detection (tabular, code, hierarchical, linear, mixed)
- Adaptive chunking strategy per document type
- Rich metadata preservation (structure, strategy, parent_section, etc.)
- Optimized for Excel, PDF, Word, Code, CSV, Markdown, and more

PROJECT ISOLATION:
- Preserves project_id in chunk metadata
- Filters search by project_id (optional)
- Filters search by truth_type (optional)
"""

import os
import re
import numpy as np
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
import requests
from requests.auth import HTTPBasicAuth
import logging

# Import universal document intelligence system
try:
    from utils.universal_chunker import chunk_intelligently
    from utils.document_analyzer import DocumentAnalyzer
    UNIVERSAL_CHUNKING_AVAILABLE = True
    logging.info("✅ Universal Document Intelligence System loaded")
except ImportError as e:
    UNIVERSAL_CHUNKING_AVAILABLE = False
    logging.warning(f"Universal chunker not available ({e}), falling back to basic chunking")

logger = logging.getLogger(__name__)


class RAGHandler:
    """
    Handles all RAG operations including document processing, embedding, and retrieval.
    
    NOW USES UNIVERSAL DOCUMENT INTELLIGENCE SYSTEM:
    - Automatic document structure detection (tabular, code, hierarchical, linear, mixed)
    - Adaptive chunking strategy per document type
    - Rich metadata preservation (structure, strategy, parent_section, etc.)
    - Optimized for Excel, PDF, Word, Code, CSV, Markdown, and more
    
    PROJECT ISOLATION:
    - Preserves project_id in chunk metadata
    - Filters search by project_id (optional)
    
    TRUTH TYPE FILTERING (v2.0):
    - Preserves truth_type in chunk metadata
    - Filters search by truth_type (intent, reference, etc.)
    """
    
    def __init__(
        self, 
        persist_directory: Optional[str] = None,
        embed_endpoint: Optional[str] = None,
        llm_endpoint: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        **kwargs
    ):
        """Initialize the RAG handler with ChromaDB and embedding configuration."""
        try:
            if persist_directory is None:
                if os.path.exists("/data") or os.access("/", os.W_OK):
                    try:
                        persist_directory = "/data/chromadb"
                        os.makedirs(persist_directory, exist_ok=True)
                        logger.info(f"Using persistent storage at {persist_directory}")
                    except (OSError, PermissionError) as e:
                        logger.warning(f"Cannot use /data: {e}, falling back to local storage")
                        persist_directory = None
                
                if persist_directory is None:
                    persist_directory = os.path.join(os.getcwd(), ".chromadb")
                    os.makedirs(persist_directory, exist_ok=True)
                    logger.warning(f"Using local storage at {persist_directory} (will reset on deploy)")
            else:
                os.makedirs(persist_directory, exist_ok=True)
                logger.info(f"Using provided storage at {persist_directory}")
            
            try:
                self.client = chromadb.PersistentClient(
                    path=persist_directory,
                    settings=Settings(anonymized_telemetry=False, allow_reset=True)
                )
                logger.info(f"ChromaDB client initialized successfully at {persist_directory}")
            except Exception as e:
                logger.error(f"Failed to initialize ChromaDB PersistentClient: {e}")
                logger.warning("Falling back to in-memory ChromaDB (data will not persist)")
                self.client = chromadb.Client()
            
            self.ollama_base_url = embed_endpoint or llm_endpoint or os.getenv("LLM_ENDPOINT")
            
            if not self.ollama_base_url:
                logger.error("LLM_ENDPOINT environment variable not set! Embeddings will fail.")
                self.ollama_base_url = "http://localhost:11434"
            
            self.ollama_username = username or os.getenv("LLM_USERNAME", "")
            self.ollama_password = password or os.getenv("LLM_PASSWORD", "")
            
            self.embedding_model = "nomic-embed-text"
            self.chunk_size = 800
            self.chunk_overlap = 100
            
            if UNIVERSAL_CHUNKING_AVAILABLE:
                self.analyzer = DocumentAnalyzer()
                logger.info("✅ Universal Document Intelligence System initialized")
                self.use_universal_chunking = True
            else:
                self.analyzer = None
                self.use_universal_chunking = False
                logger.warning("Using fallback basic chunking")
            
            logger.info("RAGHandler initialized successfully")
            logger.info(f"Ollama endpoint: {self.ollama_base_url}")
            
        except Exception as e:
            logger.error(f"Critical error in RAGHandler initialization: {e}")
            raise RuntimeError(f"Failed to initialize RAGHandler: {e}")

    def _normalize_embedding(self, embedding: List[float]) -> List[float]:
        """Normalize embedding to unit length (L2 norm = 1.0)."""
        embedding_array = np.array(embedding)
        norm = np.linalg.norm(embedding_array)
        
        if norm == 0:
            logger.warning("Zero norm embedding detected, returning as-is")
            return embedding
            
        normalized = embedding_array / norm
        return normalized.tolist()

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """Get normalized embedding from Ollama for the given text."""
        try:
            url = f"{self.ollama_base_url}/api/embeddings"
            payload = {"model": self.embedding_model, "prompt": text}
            
            logger.info(f"Getting embedding from {url} (text length: {len(text)})")
            
            response = requests.post(
                url, json=payload,
                auth=HTTPBasicAuth(self.ollama_username, self.ollama_password),
                timeout=120
            )
            
            if response.status_code != 200:
                logger.error(f"Ollama returned status {response.status_code}: {response.text}")
                return None
                
            response.raise_for_status()
            raw_embedding = response.json()["embedding"]
            normalized_embedding = self._normalize_embedding(raw_embedding)
            
            logger.debug(f"Successfully got embedding (dimension: {len(normalized_embedding)})")
            return normalized_embedding
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout connecting to Ollama at {self.ollama_base_url}")
            return None
        except requests.exceptions.ConnectionError:
            logger.error(f"Cannot connect to Ollama at {self.ollama_base_url}")
            return None
        except Exception as e:
            logger.error(f"Error getting embedding: {str(e)}", exc_info=True)
            return None

    def get_embeddings_batch(self, texts: List[str], batch_size: int = 10) -> List[Optional[List[float]]]:
        """Get embeddings for multiple texts using PARALLEL PROCESSING."""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import time
        
        if not texts:
            return []
        
        max_workers = min(batch_size, 10)
        logger.info(f"[PARALLEL] Getting embeddings for {len(texts)} chunks with {max_workers} workers")
        start_time = time.time()
        
        embeddings = [None] * len(texts)
        failed_count = 0
        completed = 0
        
        def get_embedding_with_index(args):
            index, text = args
            embedding = self.get_embedding(text)
            return index, embedding
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_index = {
                executor.submit(get_embedding_with_index, (i, text)): i 
                for i, text in enumerate(texts)
            }
            
            for future in as_completed(future_to_index):
                try:
                    index, embedding = future.result()
                    embeddings[index] = embedding
                    completed += 1
                    
                    if embedding is None:
                        failed_count += 1
                    
                    if completed % 50 == 0 or completed == len(texts):
                        elapsed = time.time() - start_time
                        rate = completed / elapsed if elapsed > 0 else 0
                        eta = (len(texts) - completed) / rate if rate > 0 else 0
                        logger.info(f"[PARALLEL] Progress: {completed}/{len(texts)} ({rate:.1f}/sec, ETA: {eta:.0f}s)")
                        
                except Exception as e:
                    logger.error(f"[PARALLEL] Error in embedding task: {e}")
                    failed_count += 1
        
        elapsed = time.time() - start_time
        success_count = len(texts) - failed_count
        rate = len(texts) / elapsed if elapsed > 0 else 0
        
        logger.info(f"[PARALLEL] Completed: {success_count}/{len(texts)} successful, {failed_count} failed")
        logger.info(f"[PARALLEL] Total time: {elapsed:.1f}s ({rate:.1f} embeddings/sec)")
        
        return embeddings

    def chunk_text(self, text: str, file_type: str = 'txt', filename: str = 'unknown') -> List[str]:
        """Chunk text using UNIVERSAL DOCUMENT INTELLIGENCE."""
        logger.info(f"[CHUNK] Starting, text length: {len(text)}, file_type: {file_type}")
        
        if self.use_universal_chunking:
            try:
                logger.info(f"[CHUNK] Using Universal Document Intelligence...")
                
                chunk_dicts = chunk_intelligently(text=text, filename=filename, file_type=file_type, metadata=None)
                
                if not isinstance(chunk_dicts, list):
                    raise TypeError(f"Universal chunker returned {type(chunk_dicts)}, expected list")
                
                if not chunk_dicts:
                    raise ValueError("Universal chunker returned empty list")
                
                chunks = []
                for i, c in enumerate(chunk_dicts):
                    if not isinstance(c, dict):
                        raise TypeError(f"Chunk {i} is {type(c)}, expected dict")
                    if 'text' not in c:
                        raise KeyError(f"Chunk {i} missing 'text' key")
                    chunks.append(c['text'])
                
                self._last_chunk_metadata = chunk_dicts
                
                logger.info(f"[CHUNK] Universal chunking complete: {len(chunks)} chunks created")
                
                if chunk_dicts and 'metadata' in chunk_dicts[0]:
                    first_meta = chunk_dicts[0]['metadata']
                    logger.info(f"[CHUNK] Document structure: {first_meta.get('structure', 'unknown')}")
                    logger.info(f"[CHUNK] Strategy used: {first_meta.get('strategy', 'unknown')}")
                
                avg_chunk_size = len(text) / len(chunks) if chunks else 0
                if len(text) > 5000 and len(chunks) <= 2 and avg_chunk_size > 4000:
                    logger.warning(f"[CHUNK] SANITY CHECK FAILED: forcing basic chunking fallback")
                    raise ValueError("Chunks too large - forcing basic chunking fallback")
                
                return chunks
                
            except Exception as e:
                logger.error(f"[CHUNK] Universal chunking failed: {e}", exc_info=True)
                logger.warning("[CHUNK] Falling back to basic chunking")
        else:
            logger.info("[CHUNK] Universal chunker not available")
        
        # Fallback: Basic chunking
        logger.warning("[CHUNK] Using basic chunking")
        
        if file_type in ['xlsx', 'xls', 'csv']:
            chunk_size = 2000
            chunk_overlap = 200
        else:
            chunk_size = self.chunk_size
            chunk_overlap = self.chunk_overlap
        
        text = re.sub(r'\s+', ' ', text).strip()
        
        chunks = []
        position = 0
        
        while position < len(text):
            end = min(position + chunk_size, len(text))
            chunk = text[position:end].strip()
            
            if chunk:
                chunks.append(chunk)
            
            if end < len(text):
                position = end - chunk_overlap
            else:
                position = len(text)
        
        logger.info(f"[CHUNK] COMPLETED: {len(chunks)} basic chunks created")
        return chunks

    def add_document(
        self, 
        collection_name: str, 
        text: str, 
        metadata: Dict[str, Any],
        progress_callback: Optional[callable] = None
    ) -> bool:
        """Add a document to a ChromaDB collection with optional progress reporting."""
        try:
            collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            
            project_id = metadata.get('project_id')
            truth_type = metadata.get('truth_type')  # NEW: Extract truth_type
            
            if project_id:
                logger.info(f"[PROJECT] Document tagged with project_id: {project_id}")
            if truth_type:
                logger.info(f"[TRUTH_TYPE] Document tagged with truth_type: {truth_type}")
            
            file_type = metadata.get('file_type', 'txt')
            filename = metadata.get('filename', metadata.get('source', 'unknown'))
            
            if progress_callback:
                progress_callback(0, 100, "Analyzing document structure...")
            
            chunks = self.chunk_text(text, file_type=file_type, filename=filename)
            chunk_metadata_enhanced = getattr(self, '_last_chunk_metadata', None)
            
            if progress_callback:
                progress_callback(10, 100, f"Chunked into {len(chunks)} pieces, getting embeddings...")
            
            logger.info(f"[BATCH] Getting embeddings for {len(chunks)} chunks...")
            embeddings = self.get_embeddings_batch(chunks, batch_size=10)
            
            if progress_callback:
                progress_callback(60, 100, f"Embeddings complete, adding to database...")
            
            chunks_added = 0
            batch_size = 50
            
            valid_chunks = []
            valid_embeddings = []
            valid_metadatas = []
            valid_ids = []
            
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                if embedding is None:
                    logger.warning(f"Failed to get embedding for chunk {i}, skipping")
                    continue
                
                doc_id = f"{metadata.get('source', 'unknown')}_{i}"
                base_metadata = {k: v for k, v in metadata.items() if v is not None}
                
                chunk_metadata = {**base_metadata, "chunk_index": i}
                
                # Preserve project_id and truth_type in chunk metadata
                if project_id:
                    chunk_metadata['project_id'] = project_id
                if truth_type:
                    chunk_metadata['truth_type'] = truth_type  # NEW: Preserve truth_type
                
                if chunk_metadata_enhanced and i < len(chunk_metadata_enhanced):
                    chunk_dict = chunk_metadata_enhanced[i]
                    
                    if 'metadata' in chunk_dict:
                        enhanced = chunk_dict['metadata']
                        enhanced_metadata = {
                            'structure': enhanced.get('structure', 'unknown'),
                            'strategy': enhanced.get('strategy', 'unknown'),
                            'chunk_type': enhanced.get('chunk_type', 'unknown'),
                            'parent_section': enhanced.get('parent_section', 'unknown'),
                            'has_header': enhanced.get('has_header', False),
                            'row_start': enhanced.get('row_start'),
                            'row_end': enhanced.get('row_end'),
                            'line_start': enhanced.get('line_start'),
                            'line_end': enhanced.get('line_end'),
                            'hierarchy_level': enhanced.get('hierarchy_level'),
                            'tokens_estimate': len(chunk) // 4,
                            'position': f"{i+1}/{len(chunks)}"
                        }
                        enhanced_metadata = {k: v for k, v in enhanced_metadata.items() if v is not None}
                        chunk_metadata.update(enhanced_metadata)
                    else:
                        fallback_metadata = {
                            'chunk_type': chunk_dict.get('chunk_type', 'unknown'),
                            'parent_section': chunk_dict.get('parent_section', 'unknown'),
                            'has_header': chunk_dict.get('has_header', False),
                            'tokens_estimate': len(chunk) // 4,
                            'position': f"{i+1}/{len(chunks)}"
                        }
                        fallback_metadata = {k: v for k, v in fallback_metadata.items() if v is not None}
                        chunk_metadata.update(fallback_metadata)
                
                chunk_metadata = {k: v for k, v in chunk_metadata.items() if v is not None}
                
                valid_chunks.append(chunk)
                valid_embeddings.append(embedding)
                valid_metadatas.append(chunk_metadata)
                valid_ids.append(doc_id)
            
            total_valid = len(valid_chunks)
            for batch_start in range(0, total_valid, batch_size):
                batch_end = min(batch_start + batch_size, total_valid)
                
                collection.add(
                    embeddings=valid_embeddings[batch_start:batch_end],
                    documents=valid_chunks[batch_start:batch_end],
                    metadatas=valid_metadatas[batch_start:batch_end],
                    ids=valid_ids[batch_start:batch_end]
                )
                
                chunks_added += (batch_end - batch_start)
                
                if progress_callback:
                    pct = 70 + int((batch_end / total_valid) * 25)
                    progress_callback(pct, 100, f"Adding to database... ({batch_end}/{total_valid} chunks)")
                
                logger.info(f"Added batch {batch_start}-{batch_end} ({batch_end - batch_start} chunks)")
            
            if progress_callback:
                progress_callback(100, 100, f"Complete! Added {chunks_added} chunks")
            
            logger.info(f"Added {chunks_added}/{len(chunks)} chunks to collection '{collection_name}'")
            if project_id:
                logger.info(f"[PROJECT] All chunks tagged with project_id: {project_id}")
            if truth_type:
                logger.info(f"[TRUTH_TYPE] All chunks tagged with truth_type: {truth_type}")
            
            return chunks_added > 0
            
        except Exception as e:
            logger.error(f"Error adding document to collection: {str(e)}")
            return False

    def search(
        self, 
        collection_name: str, 
        query: str, 
        n_results: int = 12,
        project_id: Optional[str] = None,
        functional_areas: Optional[List[str]] = None,
        truth_type: Optional[str] = None,  # NEW: Filter by truth_type
        where: Optional[Dict] = None  # NEW: Custom where clause
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant documents in a collection.
        
        SUPPORTS PROJECT, FUNCTIONAL AREA, AND TRUTH_TYPE FILTERING
        
        Args:
            collection_name: Name of the collection to search
            query: Search query
            n_results: Number of results to return
            project_id: Optional project ID to filter by
            functional_areas: Optional list of functional areas to filter by
            truth_type: Optional truth_type to filter by (intent, reference, etc.)
            where: Optional custom where clause (overrides other filters)
            
        Returns:
            List of search results with documents, metadata, and distances
        """
        try:
            collection = self.client.get_collection(name=collection_name)
            
            query_embedding = self.get_embedding(query)
            if query_embedding is None:
                logger.error("Failed to get query embedding")
                return []
            
            # Build where clause
            where_clause = None
            
            # NEW: If custom where clause provided, use it directly
            if where is not None:
                where_clause = where
                logger.info(f"[FILTER] Using custom where clause")
            
            # NEW: truth_type filter (takes precedence over legacy filters when no custom where)
            elif truth_type:
                conditions = [{"truth_type": truth_type}]
                
                if project_id and project_id != "Global/Universal":
                    conditions.append({"project_id": project_id})
                
                if functional_areas:
                    conditions.append({"functional_area": {"$in": functional_areas}})
                
                if len(conditions) == 1:
                    where_clause = conditions[0]
                else:
                    where_clause = {"$and": conditions}
                
                logger.info(f"[FILTER] Filtering by truth_type={truth_type}, project={project_id}")
            
            # Legacy filter logic (kept for backward compatibility)
            elif project_id and functional_areas:
                if project_id == "Global/Universal":
                    where_clause = {
                        "$and": [
                            {"project_id": "Global/Universal"},
                            {"functional_area": {"$in": functional_areas}}
                        ]
                    }
                else:
                    where_clause = {
                        "$and": [
                            {"$or": [
                                {"project_id": project_id},
                                {"project_id": "Global/Universal"}
                            ]},
                            {"functional_area": {"$in": functional_areas}}
                        ]
                    }
                logger.info(f"[PROJECT] Filtering by project_id: {project_id} + Global/Universal")
                logger.info(f"[FUNCTIONAL AREA] Filtering by areas: {', '.join(functional_areas)}")
            elif project_id:
                if project_id == "Global/Universal":
                    where_clause = {"project_id": "Global/Universal"}
                    logger.info(f"[PROJECT] Filtering search by Global/Universal only")
                else:
                    where_clause = {
                        "$or": [
                            {"project_id": project_id},
                            {"project_id": "Global/Universal"}
                        ]
                    }
                    logger.info(f"[PROJECT] Filtering search by project_id: {project_id} + Global/Universal")
            elif functional_areas:
                where_clause = {"functional_area": {"$in": functional_areas}}
                logger.info(f"[FUNCTIONAL AREA] Filtering by areas: {', '.join(functional_areas)}")
            else:
                logger.info("[FILTER] No filters - searching all documents")
            
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_clause,
                include=["documents", "metadatas", "distances"]
            )
            
            formatted_results = []
            
            if not results or not results.get('documents'):
                logger.info(f"No results found in collection '{collection_name}'")
                return []
            
            documents = results['documents']
            if not documents or (isinstance(documents, list) and len(documents) > 0 and not documents[0]):
                logger.info(f"Empty documents in search results for collection '{collection_name}'")
                return []
            
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
            if truth_type:
                logger.info(f"[TRUTH_TYPE] Results filtered by: {truth_type}")
            if project_id:
                if project_id == "Global/Universal":
                    logger.info(f"[PROJECT] Results filtered by: Global/Universal only")
                else:
                    logger.info(f"[PROJECT] Results filtered by: {project_id} + Global/Universal")
            if formatted_results and formatted_results[0].get('distance') is not None:
                logger.info(f"Best match distance: {formatted_results[0]['distance']:.4f}")
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching collection '{collection_name}': {str(e)}")
            return []

    # ==========================================================================
    # TRUTH-TYPE SPECIFIC SEARCH HELPERS
    # ==========================================================================
    
    def search_intent(
        self,
        collection_name: str,
        query: str,
        project_id: str,
        n_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for INTENT documents (customer documentation).
        
        Args:
            collection_name: Collection to search
            query: Search query
            project_id: Project to search within
            n_results: Number of results
            
        Returns:
            List of search results filtered to intent documents
        """
        return self.search(
            collection_name=collection_name,
            query=query,
            n_results=n_results,
            truth_type='intent',
            project_id=project_id
        )
    
    def search_reference(
        self,
        collection_name: str,
        query: str,
        n_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for REFERENCE documents (standards, checklists).
        Reference is always global - no project filter needed.
        
        Args:
            collection_name: Collection to search
            query: Search query
            n_results: Number of results
            
        Returns:
            List of search results filtered to reference documents
        """
        return self.search(
            collection_name=collection_name,
            query=query,
            n_results=n_results,
            truth_type='reference'
        )
    
    def search_by_truth_type(
        self,
        collection_name: str,
        query: str,
        truth_type: str,
        project_id: Optional[str] = None,
        n_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search filtered by truth_type.
        
        Args:
            collection_name: Collection to search
            query: Search query
            truth_type: 'reality', 'intent', 'reference', 'configuration', 'output'
            project_id: Optional project filter
            n_results: Number of results
            
        Returns:
            List of search results
        """
        return self.search(
            collection_name=collection_name,
            query=query,
            n_results=n_results,
            truth_type=truth_type,
            project_id=project_id
        )

    # ==========================================================================
    # COLLECTION MANAGEMENT
    # ==========================================================================

    def list_collections(self) -> List[str]:
        """List all available collections."""
        try:
            collections = self.client.list_collections()
            return [col.name for col in collections]
        except Exception as e:
            logger.error(f"Error listing collections: {str(e)}")
            return []

    def get_collection_count(self, collection_name: str) -> int:
        """Get the number of documents in a collection."""
        try:
            collection = self.client.get_collection(name=collection_name)
            return collection.count()
        except Exception as e:
            logger.error(f"Error getting collection count: {str(e)}")
            return 0

    def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection."""
        try:
            self.client.delete_collection(name=collection_name)
            logger.info(f"Deleted collection '{collection_name}'")
            return True
        except Exception as e:
            logger.error(f"Error deleting collection: {str(e)}")
            return False

    def reset_all(self) -> bool:
        """Delete all collections and reset the database."""
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
