"""
ChromaDB Repair Router - Fix customer_id metadata on existing chunks

This router provides endpoints to:
1. Diagnose chunks with missing/null customer_id
2. Repair chunks by looking up customer_id from Supabase registry
3. Verify repairs were successful

Created: January 20, 2026
Reason: Chunks were stored with null customer_id due to metadata key mismatch
        (upload.py passed 'customer_id', rag_handler.py expected 'project_id')
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/repair", tags=["repair"])

# Import dependencies
try:
    from utils.rag_handler import RAGHandler
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    logger.warning("RAGHandler not available for repair")

try:
    from backend.utils.database.models import DocumentRegistryModel
    REGISTRY_AVAILABLE = True
except ImportError:
    try:
        from utils.database.models import DocumentRegistryModel
        REGISTRY_AVAILABLE = True
    except ImportError:
        REGISTRY_AVAILABLE = False
        logger.warning("DocumentRegistryModel not available for repair")


@router.get("/chromadb/diagnose")
async def diagnose_chromadb() -> Dict[str, Any]:
    """
    Diagnose ChromaDB chunks for customer_id issues.
    
    Returns:
        Summary of chunks with/without customer_id, grouped by document
    """
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAGHandler not available")
    
    try:
        rag = RAGHandler()
        collection = rag.client.get_collection(name="documents")
        
        # Get all chunks
        all_data = collection.get(include=["metadatas"])
        
        if not all_data or not all_data.get('ids'):
            return {
                "success": True,
                "total_chunks": 0,
                "message": "No chunks in collection"
            }
        
        # Analyze chunks
        chunks_with_customer_id = 0
        chunks_without_customer_id = 0
        by_document = {}
        
        for i, metadata in enumerate(all_data.get('metadatas', [])):
            doc_name = metadata.get('filename') or metadata.get('source') or 'unknown'
            customer_id = metadata.get('customer_id')
            
            if doc_name not in by_document:
                by_document[doc_name] = {
                    'total_chunks': 0,
                    'with_customer_id': 0,
                    'without_customer_id': 0,
                    'customer_id': customer_id
                }
            
            by_document[doc_name]['total_chunks'] += 1
            
            if customer_id:
                by_document[doc_name]['with_customer_id'] += 1
                chunks_with_customer_id += 1
            else:
                by_document[doc_name]['without_customer_id'] += 1
                chunks_without_customer_id += 1
        
        return {
            "success": True,
            "total_chunks": len(all_data['ids']),
            "chunks_with_customer_id": chunks_with_customer_id,
            "chunks_without_customer_id": chunks_without_customer_id,
            "needs_repair": chunks_without_customer_id > 0,
            "by_document": by_document
        }
        
    except Exception as e:
        logger.error(f"Diagnose failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chromadb/repair")
async def repair_chromadb() -> Dict[str, Any]:
    """
    Repair ChromaDB chunks by adding customer_id from Supabase registry.
    
    Process:
    1. Get all chunks from ChromaDB
    2. Look up each document's customer_id from Supabase registry
    3. Update chunk metadata with customer_id
    
    Note: ChromaDB's update() method allows updating metadata in place.
    
    Returns:
        Summary of repairs made
    """
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAGHandler not available")
    if not REGISTRY_AVAILABLE:
        raise HTTPException(status_code=503, detail="DocumentRegistry not available")
    
    try:
        rag = RAGHandler()
        collection = rag.client.get_collection(name="documents")
        
        # Get all chunks with metadata
        all_data = collection.get(include=["metadatas", "documents", "embeddings"])
        
        if not all_data or not all_data.get('ids'):
            return {
                "success": True,
                "message": "No chunks to repair",
                "repaired": 0
            }
        
        # Build lookup from registry: filename -> customer_id
        registry_lookup = {}
        try:
            # Get all registry entries
            all_entries = DocumentRegistryModel.get_all()
            for entry in all_entries:
                filename = entry.get('filename')
                cust_id = entry.get('customer_id') or entry.get('project_id')
                if filename and cust_id:
                    registry_lookup[filename] = cust_id
                    logger.info(f"Registry: {filename} -> {cust_id}")
        except Exception as e:
            logger.warning(f"Could not load full registry: {e}")
        
        # Process chunks
        repaired_count = 0
        skipped_count = 0
        failed_count = 0
        repairs_by_doc = {}
        
        ids_to_update = []
        metadatas_to_update = []
        
        for i, (chunk_id, metadata) in enumerate(zip(all_data['ids'], all_data['metadatas'])):
            doc_name = metadata.get('filename') or metadata.get('source') or 'unknown'
            current_customer_id = metadata.get('customer_id')
            
            # Skip if already has customer_id
            if current_customer_id:
                skipped_count += 1
                continue
            
            # Look up customer_id from registry
            registry_customer_id = registry_lookup.get(doc_name)
            
            if not registry_customer_id:
                # Try to find in registry by filename
                try:
                    entry = DocumentRegistryModel.get_by_filename(doc_name)
                    if entry:
                        registry_customer_id = entry.get('customer_id') or entry.get('project_id')
                        registry_lookup[doc_name] = registry_customer_id
                except Exception:
                    pass
            
            if registry_customer_id:
                # Prepare update
                new_metadata = dict(metadata)
                new_metadata['customer_id'] = registry_customer_id
                
                ids_to_update.append(chunk_id)
                metadatas_to_update.append(new_metadata)
                
                if doc_name not in repairs_by_doc:
                    repairs_by_doc[doc_name] = {
                        'customer_id': registry_customer_id,
                        'chunks_repaired': 0
                    }
                repairs_by_doc[doc_name]['chunks_repaired'] += 1
                repaired_count += 1
            else:
                failed_count += 1
                logger.warning(f"No customer_id found for document: {doc_name}")
        
        # Batch update ChromaDB
        if ids_to_update:
            try:
                collection.update(
                    ids=ids_to_update,
                    metadatas=metadatas_to_update
                )
                logger.info(f"Updated {len(ids_to_update)} chunks in ChromaDB")
            except Exception as e:
                logger.error(f"Batch update failed: {e}")
                raise HTTPException(status_code=500, detail=f"Batch update failed: {e}")
        
        return {
            "success": True,
            "total_chunks": len(all_data['ids']),
            "repaired": repaired_count,
            "skipped_already_had_customer_id": skipped_count,
            "failed_no_registry_entry": failed_count,
            "repairs_by_document": repairs_by_doc
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Repair failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chromadb/repair-document/{document_name}")
async def repair_single_document(
    document_name: str,
    customer_id: str
) -> Dict[str, Any]:
    """
    Repair a single document's chunks with specified customer_id.
    
    Use this when you know the correct customer_id for a document.
    
    Args:
        document_name: The filename/document name to repair
        customer_id: The customer_id to assign
        
    Returns:
        Summary of repairs made
    """
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAGHandler not available")
    
    try:
        rag = RAGHandler()
        collection = rag.client.get_collection(name="documents")
        
        # Find chunks for this document
        results = None
        for field in ['filename', 'source', 'name']:
            try:
                results = collection.get(
                    where={field: document_name},
                    include=["metadatas"]
                )
                if results and results.get('ids'):
                    break
            except Exception:
                continue
        
        if not results or not results.get('ids'):
            raise HTTPException(
                status_code=404, 
                detail=f"No chunks found for document: {document_name}"
            )
        
        # Update all chunks
        ids_to_update = results['ids']
        metadatas_to_update = []
        
        for metadata in results['metadatas']:
            new_metadata = dict(metadata)
            new_metadata['customer_id'] = customer_id
            metadatas_to_update.append(new_metadata)
        
        collection.update(
            ids=ids_to_update,
            metadatas=metadatas_to_update
        )
        
        return {
            "success": True,
            "document": document_name,
            "customer_id": customer_id,
            "chunks_updated": len(ids_to_update)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Single document repair failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chromadb/verify")
async def verify_chromadb() -> Dict[str, Any]:
    """
    Verify ChromaDB chunks after repair.
    
    Returns:
        Summary showing all chunks now have customer_id
    """
    # Reuse diagnose
    return await diagnose_chromadb()
