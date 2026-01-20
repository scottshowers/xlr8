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


@router.post("/duckdb/profile-all/{customer_id}")
async def profile_all_tables(customer_id: str) -> Dict[str, Any]:
    """
    Profile all tables for a customer that are missing column profiles.
    
    This is needed when tables were created (e.g., via API sync) but never profiled.
    Profiling populates _column_profiles which enables:
    - Term index to find tables by column values
    - Hub-spoke detection to find relationships
    - Intelligence layer to answer queries
    
    Args:
        customer_id: The customer UUID
        
    Returns:
        Summary of profiling results
    """
    try:
        from utils.structured_data_handler import get_structured_handler
        handler = get_structured_handler()
        
        if not handler or not handler.conn:
            raise HTTPException(status_code=503, detail="Database not available")
        
        # Get all tables for this customer from _schema_metadata
        tables_result = handler.conn.execute("""
            SELECT table_name, row_count, display_name 
            FROM _schema_metadata 
            WHERE project = ? AND is_current = TRUE
        """, [customer_id]).fetchall()
        
        if not tables_result:
            return {
                "success": True,
                "customer_id": customer_id,
                "message": "No tables found in schema metadata",
                "profiled": 0
            }
        
        # Check which tables already have profiles
        profiled_tables = set()
        try:
            existing = handler.conn.execute("""
                SELECT DISTINCT table_name FROM _column_profiles WHERE project = ?
            """, [customer_id]).fetchall()
            profiled_tables = {r[0] for r in existing}
        except:
            pass
        
        # Profile tables that need it
        results = {
            "already_profiled": 0,
            "newly_profiled": 0,
            "failed": 0,
            "details": []
        }
        
        for row in tables_result:
            table_name = row[0]
            row_count = row[1] or 0
            display_name = row[2] or table_name
            
            if table_name in profiled_tables:
                results["already_profiled"] += 1
                continue
            
            try:
                # Profile this table
                handler.profile_columns_fast(customer_id, table_name)
                results["newly_profiled"] += 1
                results["details"].append({
                    "table": display_name,
                    "status": "profiled",
                    "rows": row_count
                })
                logger.info(f"[PROFILE] Profiled {table_name} ({row_count} rows)")
            except Exception as e:
                results["failed"] += 1
                results["details"].append({
                    "table": display_name,
                    "status": "failed",
                    "error": str(e)
                })
                logger.warning(f"[PROFILE] Failed to profile {table_name}: {e}")
        
        # Recalc term index after profiling
        recalc_message = None
        try:
            from backend.utils.intelligence.term_index import recalc_term_index
            stats = recalc_term_index(handler.conn, customer_id)
            recalc_message = f"Term index recalculated: {stats}"
            logger.info(f"[PROFILE] Term index recalculated for {customer_id}")
        except Exception as e:
            recalc_message = f"Term index recalc failed: {e}"
            logger.warning(f"[PROFILE] Term index recalc failed: {e}")
        
        return {
            "success": True,
            "customer_id": customer_id,
            "total_tables": len(tables_result),
            "already_profiled": results["already_profiled"],
            "newly_profiled": results["newly_profiled"],
            "failed": results["failed"],
            "term_index": recalc_message,
            "details": results["details"][:20]  # Limit details to first 20
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch profile failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/duckdb/register-missing/{customer_id}")
async def register_missing_tables(customer_id: str) -> Dict[str, Any]:
    """
    Register any DuckDB tables that exist but aren't in _schema_metadata.
    
    This catches tables created by API sync or other processes that
    bypassed the normal registration flow.
    
    Args:
        customer_id: The customer UUID
        
    Returns:
        Summary of registration results
    """
    try:
        from utils.structured_data_handler import get_structured_handler
        handler = get_structured_handler()
        
        if not handler or not handler.conn:
            raise HTTPException(status_code=503, detail="Database not available")
        
        # Get all actual tables in DuckDB for this customer
        all_tables = handler.conn.execute("SHOW TABLES").fetchall()
        customer_tables = [t[0] for t in all_tables if t[0].startswith(customer_id[:8]) or t[0].startswith(customer_id)]
        
        # Get tables already in _schema_metadata
        registered = handler.conn.execute("""
            SELECT table_name FROM _schema_metadata WHERE project = ?
        """, [customer_id]).fetchall()
        registered_set = {r[0] for r in registered}
        
        # Find missing tables
        missing = [t for t in customer_tables if t not in registered_set]
        
        if not missing:
            return {
                "success": True,
                "customer_id": customer_id,
                "message": "All tables already registered",
                "registered": 0
            }
        
        # Register missing tables
        registered_count = 0
        for table_name in missing:
            try:
                # Get row count
                count_result = handler.conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()
                row_count = count_result[0] if count_result else 0
                
                # Determine display name and type
                if '_api_' in table_name:
                    short_name = table_name.split('_api_')[-1]
                    display_name = f"API: {short_name.replace('_', ' ').title()}"
                    truth_type = 'configuration'
                    category = 'api'
                else:
                    display_name = table_name
                    truth_type = 'reality'
                    category = 'upload'
                
                # Insert into _schema_metadata
                handler.conn.execute("""
                    INSERT INTO _schema_metadata 
                    (project, file_name, sheet_name, table_name, row_count, is_current, display_name, truth_type, category)
                    VALUES (?, ?, 'Sheet1', ?, ?, TRUE, ?, ?, ?)
                """, [customer_id, display_name, table_name, row_count, display_name, truth_type, category])
                
                registered_count += 1
                logger.info(f"[REGISTER] Registered {table_name}")
                
            except Exception as e:
                logger.warning(f"[REGISTER] Failed to register {table_name}: {e}")
        
        return {
            "success": True,
            "customer_id": customer_id,
            "total_duckdb_tables": len(customer_tables),
            "already_registered": len(registered_set),
            "newly_registered": registered_count,
            "missing_tables_found": len(missing)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Register missing tables failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/full-repair/{customer_id}")
async def full_repair(customer_id: str) -> Dict[str, Any]:
    """
    Run a full repair for a customer:
    1. Register any missing tables in _schema_metadata
    2. Profile all unprofile tables in _column_profiles
    3. Recalc term index
    4. Recompute hub-spoke graph
    
    This is the "fix everything" endpoint.
    
    Args:
        customer_id: The customer UUID
        
    Returns:
        Combined results from all repair steps
    """
    results = {
        "customer_id": customer_id,
        "steps": {}
    }
    
    # Step 1: Register missing tables
    try:
        register_result = await register_missing_tables(customer_id)
        results["steps"]["register_tables"] = {
            "success": True,
            "newly_registered": register_result.get("newly_registered", 0)
        }
    except Exception as e:
        results["steps"]["register_tables"] = {"success": False, "error": str(e)}
    
    # Step 2: Profile all tables
    try:
        profile_result = await profile_all_tables(customer_id)
        results["steps"]["profile_columns"] = {
            "success": True,
            "newly_profiled": profile_result.get("newly_profiled", 0),
            "term_index": profile_result.get("term_index")
        }
    except Exception as e:
        results["steps"]["profile_columns"] = {"success": False, "error": str(e)}
    
    # Step 3: Recompute hub-spoke graph
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://hcmpact-xlr8-production.up.railway.app/api/data-model/context-graph/{customer_id}/compute",
                timeout=60.0
            )
            if response.status_code == 200:
                graph_result = response.json()
                results["steps"]["hub_spoke"] = {
                    "success": True,
                    "hubs": graph_result.get("result", {}).get("hubs", 0),
                    "spokes": graph_result.get("result", {}).get("spokes", 0)
                }
            else:
                results["steps"]["hub_spoke"] = {"success": False, "error": f"HTTP {response.status_code}"}
    except Exception as e:
        results["steps"]["hub_spoke"] = {"success": False, "error": str(e)}
    
    # Overall success
    results["success"] = all(
        step.get("success", False) 
        for step in results["steps"].values()
    )
    
    return results
