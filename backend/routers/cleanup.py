"""
CLEANUP ROUTER
==============

All data deletion endpoints in one place.

Handles:
- Jobs (processing history)
- Structured files (DuckDB tables)
- Documents (ChromaDB chunks)
- Bulk project cleanup

Deploy to: backend/routers/cleanup.py

Add to main.py:
    from routers import cleanup
    app.include_router(cleanup.router, prefix="/api", tags=["cleanup"])

FIXED: December 19, 2025 - Now cleans _schema_metadata and _pdf_tables on delete
"""

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta
import logging
import os

logger = logging.getLogger(__name__)
router = APIRouter()

# =============================================================================
# HELPERS
# =============================================================================

def _get_supabase():
    try:
        from supabase import create_client
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
        if url and key:
            return create_client(url, key)
    except Exception as e:
        logger.warning(f"[CLEANUP] Supabase not available: {e}")
    return None


def _get_duckdb(project_id: str = None):
    """Get DuckDB connection - tries multiple import paths."""
    try:
        from services.duckdb_service import get_duckdb_connection
        return get_duckdb_connection(project_id)
    except ImportError:
        try:
            from backend.services.duckdb_service import get_duckdb_connection
            return get_duckdb_connection(project_id)
        except ImportError:
            # Try structured data handler as fallback
            try:
                from utils.structured_data_handler import get_structured_handler
                handler = get_structured_handler()
                return handler.conn
            except:
                try:
                    from backend.utils.structured_data_handler import get_structured_handler
                    handler = get_structured_handler()
                    return handler.conn
                except:
                    return None


def _get_chromadb():
    try:
        from services.chromadb_service import get_collection
        return get_collection()
    except ImportError:
        try:
            from backend.services.chromadb_service import get_collection
            return get_collection()
        except:
            try:
                import chromadb
                client = chromadb.PersistentClient(path=os.getenv("CHROMADB_PATH", "./chroma_db"))
                return client.get_or_create_collection("documents")
            except:
                return None


def _clean_metadata_tables(conn, table_name: str = None, filename: str = None, project: str = None):
    """
    Clean up ALL metadata tables after a delete.
    
    This is the KEY fix - we need to clean _schema_metadata and _pdf_tables
    which are what the status/metrics endpoints query.
    """
    cleaned = {"_schema_metadata": 0, "_pdf_tables": 0, "file_metadata": 0, "column_profiles": 0}
    
    try:
        # 1. Clean _schema_metadata (Excel files)
        try:
            if table_name:
                result = conn.execute(f"DELETE FROM _schema_metadata WHERE table_name = ?", [table_name])
                cleaned["_schema_metadata"] = result.rowcount if hasattr(result, 'rowcount') else 1
                logger.info(f"[CLEANUP] Deleted from _schema_metadata by table_name: {table_name}")
            elif filename:
                result = conn.execute(f"DELETE FROM _schema_metadata WHERE file_name = ?", [filename])
                cleaned["_schema_metadata"] = result.rowcount if hasattr(result, 'rowcount') else 1
                logger.info(f"[CLEANUP] Deleted from _schema_metadata by file_name: {filename}")
            elif project:
                result = conn.execute(f"DELETE FROM _schema_metadata WHERE project = ?", [project])
                cleaned["_schema_metadata"] = result.rowcount if hasattr(result, 'rowcount') else 1
                logger.info(f"[CLEANUP] Deleted from _schema_metadata by project: {project}")
        except Exception as e:
            logger.debug(f"[CLEANUP] _schema_metadata cleanup: {e}")
        
        # 2. Clean _pdf_tables (PDF files)
        try:
            # Check if table exists first
            table_check = conn.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name = '_pdf_tables'
            """).fetchone()
            
            if table_check[0] > 0:
                if table_name:
                    result = conn.execute(f"DELETE FROM _pdf_tables WHERE table_name = ?", [table_name])
                    cleaned["_pdf_tables"] = result.rowcount if hasattr(result, 'rowcount') else 1
                    logger.info(f"[CLEANUP] Deleted from _pdf_tables by table_name: {table_name}")
                elif filename:
                    result = conn.execute(f"DELETE FROM _pdf_tables WHERE source_file = ?", [filename])
                    cleaned["_pdf_tables"] = result.rowcount if hasattr(result, 'rowcount') else 1
                    logger.info(f"[CLEANUP] Deleted from _pdf_tables by source_file: {filename}")
                elif project:
                    result = conn.execute(f"DELETE FROM _pdf_tables WHERE project = ? OR project_id = ?", [project, project])
                    cleaned["_pdf_tables"] = result.rowcount if hasattr(result, 'rowcount') else 1
                    logger.info(f"[CLEANUP] Deleted from _pdf_tables by project: {project}")
        except Exception as e:
            logger.debug(f"[CLEANUP] _pdf_tables cleanup: {e}")
        
        # 3. Also clean legacy metadata tables (file_metadata, column_profiles)
        for meta_table in ['file_metadata', 'column_profiles']:
            try:
                if filename:
                    conn.execute(f"DELETE FROM {meta_table} WHERE filename = ?", [filename])
                elif table_name:
                    conn.execute(f"DELETE FROM {meta_table} WHERE table_name = ?", [table_name])
                cleaned[meta_table] = 1
            except Exception as e:
                logger.debug(f"[CLEANUP] {meta_table} cleanup: {e}")
        
        logger.info(f"[CLEANUP] Metadata cleanup complete: {cleaned}")
        return cleaned
        
    except Exception as e:
        logger.error(f"[CLEANUP] Metadata cleanup failed: {e}")
        return cleaned


# =============================================================================
# JOB DELETION
# =============================================================================

# IMPORTANT: Static routes MUST come before parameterized routes
# /jobs/all must be before /jobs/{job_id} or "all" gets treated as a job_id

@router.delete("/jobs/all")
async def delete_all_jobs(project_id: str = Query(None)):
    """Delete all jobs, optionally filtered by project."""
    supabase = _get_supabase()
    if not supabase:
        raise HTTPException(503, "Database not available")
    
    try:
        query = supabase.table("jobs").delete()
        
        if project_id:
            query = query.eq("project_id", project_id)
        else:
            # Delete all - need a condition that matches everything
            query = query.neq("id", "IMPOSSIBLE_ID_THAT_WILL_NEVER_EXIST")
        
        result = query.execute()
        count = len(result.data) if result.data else 0
        
        logger.info(f"[CLEANUP] Deleted {count} jobs")
        return {"success": True, "deleted": count}
        
    except Exception as e:
        logger.error(f"[CLEANUP] Delete all jobs failed: {e}")
        raise HTTPException(500, f"Failed to delete jobs: {str(e)}")


@router.delete("/jobs/range")
async def delete_jobs_in_range(
    start_date: str = Query(...),
    end_date: str = Query(...),
    project_id: str = Query(None)
):
    """Delete jobs within a date range."""
    supabase = _get_supabase()
    if not supabase:
        raise HTTPException(503, "Database not available")
    
    try:
        # Parse dates
        from datetime import datetime
        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        query = supabase.table("jobs").delete()\
            .gte("created_at", start.isoformat())\
            .lte("created_at", end.isoformat())
        
        if project_id:
            query = query.eq("project_id", project_id)
        
        result = query.execute()
        count = len(result.data) if result.data else 0
        
        logger.info(f"[CLEANUP] Deleted {count} jobs in range {start_date} to {end_date}")
        return {"success": True, "deleted": count, "range": {"start": start_date, "end": end_date}}
        
    except ValueError as e:
        raise HTTPException(400, f"Invalid date format: {str(e)}")
    except Exception as e:
        logger.error(f"[CLEANUP] Delete jobs in range failed: {e}")
        raise HTTPException(500, f"Failed to delete jobs: {str(e)}")




# =============================================================================
# STRUCTURED FILE DELETION (DuckDB)
# =============================================================================

@router.delete("/status/structured/{project_id}/{filename:path}")
async def delete_structured_file(project_id: str, filename: str):
    """
    Delete a structured data file - CASCADE to all storage systems.
    
    Per ARCHITECTURE.md: "Not cascading deletes to all storage systems" is a mistake.
    This endpoint now cleans:
    1. DuckDB tables
    2. DuckDB metadata (_schema_metadata, _pdf_tables)
    3. ChromaDB chunks (if any exist for this file)
    4. document_registry entry
    """
    logger.info(f"[CLEANUP] Deleting file (cascade): {filename} from {project_id}")
    
    result = {
        "success": True,
        "filename": filename,
        "project": project_id,
        "tables_dropped": [],
        "chunks_removed": 0,
        "registry_removed": False,
        "metadata_cleaned": True
    }
    
    # 1. DUCKDB - Drop tables and clean metadata
    conn = _get_duckdb(project_id)
    if conn:
        try:
            # Convert filename to table name pattern
            table_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
            table_name = table_name.lower().replace(' ', '_').replace('-', '_')
            table_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in table_name)
            
            # Get existing tables
            tables = conn.execute("SHOW TABLES").fetchall()
            table_names = [t[0] for t in tables]
            
            # Find matching table(s) - might have multiple sheets from same file
            matched_tables = []
            
            # Exact match
            if table_name in table_names:
                matched_tables.append(table_name)
            
            # Partial match (for sheets: filename__sheet1, filename__sheet2, etc.)
            for t in table_names:
                t_lower = t.lower()
                # Match by prefix (handles multi-sheet files)
                if t_lower.startswith(table_name + '__') or t_lower.startswith(table_name[:30]):
                    if t not in matched_tables:
                        matched_tables.append(t)
                # Match by filename component
                if filename.lower().replace('.', '_').replace(' ', '_') in t_lower:
                    if t not in matched_tables:
                        matched_tables.append(t)
            
            # Drop all matched tables
            for matched_table in matched_tables:
                try:
                    conn.execute(f'DROP TABLE IF EXISTS "{matched_table}"')
                    result['tables_dropped'].append(matched_table)
                    logger.info(f"[CLEANUP] Dropped table: {matched_table}")
                    
                    # Clean metadata for this specific table
                    _clean_metadata_tables(conn, table_name=matched_table)
                    
                except Exception as drop_e:
                    logger.warning(f"[CLEANUP] Failed to drop {matched_table}: {drop_e}")
            
            # Also clean by filename pattern
            _clean_metadata_tables(conn, filename=filename)
            
        except Exception as e:
            logger.warning(f"[CLEANUP] DuckDB cleanup error: {e}")
    
    # 2. CHROMADB - Delete any chunks for this file (cascade, case-insensitive)
    collection = _get_chromadb()
    if collection:
        try:
            filename_lower = filename.lower()
            
            # Fetch all and do case-insensitive match
            all_docs = collection.get(include=["metadatas"])
            ids_to_delete = []
            
            for i, metadata in enumerate(all_docs.get("metadatas", [])):
                if not metadata:
                    continue
                doc_name = metadata.get("source") or metadata.get("filename") or ""
                if doc_name.lower() == filename_lower:
                    ids_to_delete.append(all_docs["ids"][i])
            
            if ids_to_delete:
                collection.delete(ids=ids_to_delete)
                result['chunks_removed'] = len(ids_to_delete)
                logger.info(f"[CLEANUP] Deleted {len(ids_to_delete)} ChromaDB chunks for {filename}")
                
        except Exception as e:
            logger.warning(f"[CLEANUP] ChromaDB cleanup error: {e}")
    
    # 3. DOCUMENT REGISTRY - Remove entry (cascade)
    supabase = _get_supabase()
    if supabase:
        try:
            del_result = supabase.table('document_registry').delete().eq(
                'filename', filename
            ).eq('project_id', project_id).execute()
            
            if del_result.data:
                result['registry_removed'] = True
                logger.info(f"[CLEANUP] Removed {filename} from document_registry")
        except Exception as e:
            logger.warning(f"[CLEANUP] Registry cleanup error: {e}")
    
    # Build message
    parts = []
    if result['tables_dropped']:
        parts.append(f"DuckDB ({len(result['tables_dropped'])} tables)")
    if result['chunks_removed'] > 0:
        parts.append(f"ChromaDB ({result['chunks_removed']} chunks)")
    if result['registry_removed']:
        parts.append("Registry")
    
    result['message'] = f"Deleted from: {', '.join(parts)}" if parts else f"Deleted {filename}"
    
    logger.info(f"[CLEANUP] Cascade delete complete: {result}")
    return result


@router.delete("/status/structured/table/{table_name}")
async def delete_structured_table(table_name: str, project: str = Query(None)):
    """
    Delete a specific DuckDB table by name.
    
    Use this when you know the exact table name.
    """
    logger.info(f"[CLEANUP] Deleting table: {table_name}")
    
    conn = _get_duckdb(project)
    if not conn:
        return {"success": True, "message": "Database not found, considered deleted"}
    
    try:
        # Drop the table
        conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
        logger.info(f"[CLEANUP] Dropped table: {table_name}")
        
        # Clean ALL metadata tables
        _clean_metadata_tables(conn, table_name=table_name)
        
        return {
            "success": True,
            "message": f"Deleted table {table_name}",
            "metadata_cleaned": True
        }
        
    except Exception as e:
        logger.error(f"[CLEANUP] Delete table failed: {e}")
        raise HTTPException(500, f"Failed to delete: {str(e)}")


# =============================================================================
# DOCUMENT DELETION (ChromaDB)
# =============================================================================

@router.delete("/status/documents/{filename:path}")
async def delete_document(filename: str, project_id: str = Query(None)):
    """
    Delete a document's chunks from ChromaDB - CASCADE to registry.
    
    Per ARCHITECTURE.md: All deletes must cascade to all storage systems.
    Uses case-insensitive matching.
    """
    logger.info(f"[CLEANUP] Deleting document (cascade): {filename}")
    
    result = {
        "success": True,
        "filename": filename,
        "deleted_chunks": 0,
        "registry_removed": False
    }
    
    filename_lower = filename.lower()
    
    # 1. CHROMADB - Delete chunks (case-insensitive)
    collection = _get_chromadb()
    if collection:
        try:
            # Fetch all and do case-insensitive match on metadata
            all_docs = collection.get(include=["metadatas"])
            ids_to_delete = []
            
            for i, metadata in enumerate(all_docs.get("metadatas", [])):
                if not metadata:
                    continue
                # Check source, filename, file fields - case insensitive
                doc_name = metadata.get("source") or metadata.get("filename") or metadata.get("file") or ""
                if doc_name.lower() == filename_lower:
                    ids_to_delete.append(all_docs["ids"][i])
            
            if ids_to_delete:
                collection.delete(ids=ids_to_delete)
                result['deleted_chunks'] = len(ids_to_delete)
                logger.info(f"[CLEANUP] Deleted {len(ids_to_delete)} chunks for {filename}")
                    
        except Exception as e:
            logger.warning(f"[CLEANUP] ChromaDB delete error: {e}")
    
    # 2. DOCUMENT REGISTRY - Remove entry (cascade, case-insensitive)
    supabase = _get_supabase()
    if supabase:
        try:
            # Try exact match first
            query = supabase.table('document_registry').delete().eq('filename', filename)
            if project_id:
                query = query.eq('project_id', project_id)
            del_result = query.execute()
            
            if del_result.data:
                result['registry_removed'] = True
                logger.info(f"[CLEANUP] Removed {filename} from document_registry")
            else:
                # Try case-insensitive via ilike
                query = supabase.table('document_registry').delete().ilike('filename', filename)
                if project_id:
                    query = query.eq('project_id', project_id)
                del_result = query.execute()
                if del_result.data:
                    result['registry_removed'] = True
                    logger.info(f"[CLEANUP] Removed {filename} from document_registry (case-insensitive)")
        except Exception as e:
            logger.warning(f"[CLEANUP] Registry cleanup error: {e}")
    
    if result['deleted_chunks'] == 0 and not result['registry_removed']:
        result['message'] = "Document not found or already deleted"
    else:
        parts = []
        if result['deleted_chunks'] > 0:
            parts.append(f"ChromaDB ({result['deleted_chunks']} chunks)")
        if result['registry_removed']:
            parts.append("Registry")
        result['message'] = f"Deleted from: {', '.join(parts)}"
    
    return result


# =============================================================================
# BULK PROJECT CLEANUP
# =============================================================================

@router.delete("/status/project/{project_id}/all")
async def delete_all_project_data(project_id: str):
    """
    Delete ALL data for a project. Use with caution!
    
    FIXED: Now cleans _schema_metadata and _pdf_tables
    """
    logger.info(f"[CLEANUP] Deleting ALL data for project: {project_id}")
    
    deleted = {"tables": 0, "documents": 0, "jobs": 0, "metadata": {}}
    
    # 1. DuckDB tables
    conn = _get_duckdb(project_id)
    if conn:
        try:
            tables = conn.execute("SHOW TABLES").fetchall()
            system_tables = {'_schema_metadata', '_pdf_tables', 'file_metadata', 'column_profiles', 'schema_info'}
            
            # Build project prefixes for matching
            project_lower = project_id.lower()
            project_prefixes = [
                project_lower + '__',
                project_lower.replace('-', '') + '__',
                project_lower.replace('_', '') + '__',
            ]
            
            for (table_name,) in tables:
                # Skip system/metadata tables
                if table_name in system_tables or table_name.startswith('_'):
                    continue
                
                # Check if table belongs to this project
                table_lower = table_name.lower()
                if any(table_lower.startswith(prefix) for prefix in project_prefixes):
                    try:
                        conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
                        deleted["tables"] += 1
                        logger.info(f"[CLEANUP] Dropped table: {table_name}")
                    except Exception as drop_e:
                        logger.warning(f"[CLEANUP] Failed to drop {table_name}: {drop_e}")
            
            # Clean metadata tables for this project
            deleted["metadata"] = _clean_metadata_tables(conn, project=project_id)
            
        except Exception as e:
            logger.warning(f"[CLEANUP] DuckDB cleanup error: {e}")
    
    # 2. ChromaDB documents
    collection = _get_chromadb()
    if collection:
        try:
            results = collection.get(where={"project_id": project_id})
            if results and results['ids']:
                collection.delete(ids=results['ids'])
                deleted["documents"] = len(results['ids'])
        except:
            # Try alternate field name
            try:
                results = collection.get(where={"project": project_id})
                if results and results['ids']:
                    collection.delete(ids=results['ids'])
                    deleted["documents"] = len(results['ids'])
            except Exception as e:
                logger.debug(f"Suppressed: {e}")
    
    # 3. Jobs
    supabase = _get_supabase()
    if supabase:
        try:
            result = supabase.table("jobs").delete().eq("project_id", project_id).execute()
            deleted["jobs"] = len(result.data) if result.data else 0
        except Exception as e:
            logger.debug(f"Suppressed: {e}")
    
    logger.info(f"[CLEANUP] Deleted for {project_id}: {deleted}")
    return {"success": True, "deleted": deleted, "project_id": project_id}


# =============================================================================
# METADATA REFRESH (Force recalculation)
# =============================================================================

@router.post("/status/refresh-metrics")
async def refresh_metrics(project: str = Query(None)):
    """
    Force refresh of metrics by cleaning orphaned metadata entries.
    
    This cleans up _schema_metadata and _pdf_tables entries that reference
    tables that no longer exist in DuckDB.
    """
    logger.info(f"[CLEANUP] Refreshing metrics for project: {project or 'all'}")
    
    conn = _get_duckdb(project)
    if not conn:
        return {"success": False, "message": "Database not available"}
    
    try:
        # Get all actual tables
        tables = conn.execute("SHOW TABLES").fetchall()
        actual_tables = set(t[0] for t in tables)
        
        orphaned = {"_schema_metadata": 0, "_pdf_tables": 0}
        
        # Clean orphaned _schema_metadata entries
        try:
            meta_result = conn.execute("SELECT table_name FROM _schema_metadata").fetchall()
            for (table_name,) in meta_result:
                if table_name not in actual_tables:
                    conn.execute("DELETE FROM _schema_metadata WHERE table_name = ?", [table_name])
                    orphaned["_schema_metadata"] += 1
                    logger.info(f"[CLEANUP] Removed orphaned _schema_metadata: {table_name}")
        except Exception as e:
            logger.debug(f"[CLEANUP] _schema_metadata refresh: {e}")
        
        # Clean orphaned _pdf_tables entries
        try:
            table_check = conn.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name = '_pdf_tables'
            """).fetchone()
            
            if table_check[0] > 0:
                pdf_result = conn.execute("SELECT table_name FROM _pdf_tables").fetchall()
                for (table_name,) in pdf_result:
                    if table_name not in actual_tables:
                        conn.execute("DELETE FROM _pdf_tables WHERE table_name = ?", [table_name])
                        orphaned["_pdf_tables"] += 1
                        logger.info(f"[CLEANUP] Removed orphaned _pdf_tables: {table_name}")
        except Exception as e:
            logger.debug(f"[CLEANUP] _pdf_tables refresh: {e}")
        
        logger.info(f"[CLEANUP] Metrics refresh complete - removed orphans: {orphaned}")
        return {
            "success": True,
            "orphaned_removed": orphaned,
            "actual_tables": len(actual_tables)
        }
        
    except Exception as e:
        logger.error(f"[CLEANUP] Metrics refresh failed: {e}")
        raise HTTPException(500, f"Refresh failed: {str(e)}")


# =============================================================================
# REFERENCES (Backward Compatibility)
# =============================================================================

def _get_rag_handler():
    """Get RAG handler for reference document operations."""
    try:
        from utils.rag_handler import RAGHandler
        return RAGHandler()
    except ImportError:
        try:
            from backend.utils.rag_handler import RAGHandler
            return RAGHandler()
        except ImportError:
            return None


@router.get("/status/references")
async def list_references():
    """
    List all reference library documents.
    Backward compatible endpoint for ReferenceLibraryPage.
    """
    try:
        rag = _get_rag_handler()
        if not rag:
            return {"files": [], "rules": [], "error": "RAG handler not available"}
        
        # Get collection and all documents
        try:
            coll = rag.client.get_collection(name="documents")
            results = coll.get(include=["metadatas"])
        except:
            return {"files": [], "rules": [], "total": 0}
        
        # Aggregate by source document
        doc_counts = {}
        doc_metadata = {}
        
        for meta in results.get('metadatas', []):
            if not meta:
                continue
            source = meta.get('source') or meta.get('filename')
            project = meta.get('project_id') or meta.get('project')
            
            # Only include reference library docs (global/universal)
            if project not in ['Global/Universal', 'Reference Library', '__STANDARDS__', None, '']:
                continue
                
            if source:
                doc_counts[source] = doc_counts.get(source, 0) + 1
                if source not in doc_metadata:
                    doc_metadata[source] = {
                        'truth_type': meta.get('truth_type', 'reference'),
                        'project': project or 'Global/Universal',
                        'uploaded_at': meta.get('uploaded_at')
                    }
        
        # Build response
        ref_files = []
        for filename, count in doc_counts.items():
            meta = doc_metadata.get(filename, {})
            ref_files.append({
                "filename": filename,
                "project": meta.get('project', 'Global/Universal'),
                "chunk_count": count,
                "truth_type": meta.get('truth_type', 'reference'),
                "uploaded_at": meta.get('uploaded_at')
            })
        
        return {
            "files": ref_files,
            "rules": [],  # Rules extracted from these docs (future)
            "total": len(ref_files)
        }
        
    except Exception as e:
        logger.error(f"[REFERENCES] Error listing: {e}")
        return {"files": [], "rules": [], "error": str(e)}


@router.delete("/status/references/{filename:path}")
async def delete_reference(
    filename: str,
    confirm: bool = Query(False, description="Must be true to delete")
):
    """
    Delete a single reference document - CASCADE to registry.
    
    Per ARCHITECTURE.md: All deletes must cascade to all storage systems.
    """
    if not confirm:
        raise HTTPException(400, "Add ?confirm=true to delete")
    
    result = {
        "success": True,
        "deleted": filename,
        "chunks_removed": 0,
        "registry_removed": False
    }
    
    # 1. CHROMADB - Delete chunks
    try:
        rag = _get_rag_handler()
        if rag:
            try:
                coll = rag.client.get_collection(name="documents")
                
                # Find and delete all chunks for this document
                results = coll.get(include=["metadatas"], where={"source": filename})
                
                if not results.get('ids'):
                    # Try with filename field instead
                    results = coll.get(include=["metadatas"], where={"filename": filename})
                
                if results.get('ids'):
                    coll.delete(ids=results['ids'])
                    result['chunks_removed'] = len(results['ids'])
                    logger.info(f"[REFERENCES] Deleted {len(results['ids'])} chunks for: {filename}")
            except Exception as e:
                logger.warning(f"[REFERENCES] ChromaDB error: {e}")
    except Exception as e:
        logger.warning(f"[REFERENCES] RAG handler error: {e}")
    
    # 2. DOCUMENT REGISTRY - Remove entry (cascade)
    # Reference docs typically have project_id = 'Global/Universal' or similar
    supabase = _get_supabase()
    if supabase:
        try:
            del_result = supabase.table('document_registry').delete().eq(
                'filename', filename
            ).execute()
            
            if del_result.data:
                result['registry_removed'] = True
                logger.info(f"[REFERENCES] Removed {filename} from document_registry")
        except Exception as e:
            logger.warning(f"[REFERENCES] Registry cleanup error: {e}")
    
    if result['chunks_removed'] == 0 and not result['registry_removed']:
        raise HTTPException(404, f"Document not found: {filename}")
    
    # Build message
    parts = []
    if result['chunks_removed'] > 0:
        parts.append(f"ChromaDB ({result['chunks_removed']} chunks)")
    if result['registry_removed']:
        parts.append("Registry")
    result['message'] = f"Deleted from: {', '.join(parts)}"
    
    return result


@router.delete("/status/references")
async def delete_all_references(
    confirm: bool = Query(False, description="Must be true to delete all")
):
    """Delete ALL reference documents. Use with caution."""
    if not confirm:
        raise HTTPException(400, "Add ?confirm=true to delete all references")
    
    try:
        rag = _get_rag_handler()
        if not rag:
            raise HTTPException(503, "RAG handler not available")
        
        # Get collection
        try:
            coll = rag.client.get_collection(name="documents")
        except:
            raise HTTPException(503, "Documents collection not available")
        
        # Get all reference docs (global/universal project)
        results = coll.get(include=["metadatas"])
        
        ids_to_delete = []
        for i, meta in enumerate(results.get('metadatas', [])):
            if not meta:
                continue
            project = meta.get('project_id') or meta.get('project')
            if project in ['Global/Universal', 'Reference Library', None, '']:
                ids_to_delete.append(results['ids'][i])
        
        if ids_to_delete:
            coll.delete(ids=ids_to_delete)
        
        logger.info(f"[REFERENCES] Cleared {len(ids_to_delete)} reference chunks")
        return {
            "success": True,
            "files_processed": len(ids_to_delete),
            "message": f"Deleted {len(ids_to_delete)} reference chunks"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[REFERENCES] Clear all error: {e}")
        raise HTTPException(500, str(e))


# =============================================================================
# MORE BACKWARD COMPAT ENDPOINTS
# =============================================================================

@router.get("/status/structured")
async def list_structured_files():
    """
    List all structured files/tables in DuckDB.
    Backward compatible endpoint.
    """
    try:
        conn = _get_duckdb()
        if not conn:
            return {"files": [], "total": 0}
        
        # Get from _schema_metadata
        files_dict = {}
        try:
            rows = conn.execute("""
                SELECT file_name, project, table_name, display_name, row_count, column_count, created_at
                FROM _schema_metadata 
                WHERE is_current = TRUE
                ORDER BY file_name
            """).fetchall()
            
            for row in rows:
                fname = row[0]
                if not fname:
                    continue
                if fname not in files_dict:
                    files_dict[fname] = {
                        "filename": fname,
                        "project": row[1],
                        "tables": 0,
                        "row_count": 0,
                        "sheets": []
                    }
                files_dict[fname]["sheets"].append({
                    "table_name": row[2],
                    "display_name": row[3] or row[2],
                    "row_count": int(row[4] or 0),
                    "column_count": int(row[5] or 0)
                })
                files_dict[fname]["tables"] += 1
                files_dict[fname]["row_count"] += int(row[4] or 0)
        except Exception as e:
            logger.debug(f"[STATUS] Schema query: {e}")
        
        # Also check _pdf_tables
        try:
            pdf_rows = conn.execute("""
                SELECT source_file, project, table_name, row_count, created_at
                FROM _pdf_tables
                ORDER BY source_file
            """).fetchall()
            
            for row in pdf_rows:
                fname = row[0]
                if not fname:
                    continue
                if fname not in files_dict:
                    files_dict[fname] = {
                        "filename": fname,
                        "project": row[1],
                        "tables": 0,
                        "row_count": 0,
                        "sheets": []
                    }
                files_dict[fname]["sheets"].append({
                    "table_name": row[2],
                    "display_name": row[2],
                    "row_count": int(row[3] or 0)
                })
                files_dict[fname]["tables"] += 1
                files_dict[fname]["row_count"] += int(row[3] or 0)
        except Exception as e:
            logger.debug(f"[STATUS] PDF tables query: {e}")
        
        return {
            "files": list(files_dict.values()),
            "total": len(files_dict),
            "total_rows": sum(f["row_count"] for f in files_dict.values())
        }
    except Exception as e:
        logger.error(f"[STATUS] List structured failed: {e}")
        return {"files": [], "total": 0, "error": str(e)}


@router.get("/status/documents")
async def list_documents():
    """List all documents in ChromaDB."""
    try:
        rag = _get_rag_handler()
        if not rag:
            return {"documents": [], "total": 0}
        
        try:
            coll = rag.client.get_collection(name="documents")
            results = coll.get(include=["metadatas"])
        except:
            return {"documents": [], "total": 0}
        
        # Aggregate by source document
        doc_counts = {}
        doc_metadata = {}
        
        for meta in results.get('metadatas', []):
            if not meta:
                continue
            source = meta.get('source') or meta.get('filename')
            if source:
                doc_counts[source] = doc_counts.get(source, 0) + 1
                if source not in doc_metadata:
                    doc_metadata[source] = {
                        'truth_type': meta.get('truth_type'),
                        'project': meta.get('project_id') or meta.get('project'),
                    }
        
        documents = []
        for filename, count in doc_counts.items():
            meta = doc_metadata.get(filename, {})
            documents.append({
                "filename": filename,
                "chunk_count": count,
                "truth_type": meta.get('truth_type'),
                "project": meta.get('project')
            })
        
        return {
            "documents": documents,
            "total": len(documents),
            "total_chunks": sum(doc_counts.values())
        }
    except Exception as e:
        logger.error(f"[STATUS] List documents failed: {e}")
        return {"documents": [], "total": 0, "error": str(e)}


@router.get("/status/chromadb")
async def get_chromadb_status():
    """Get ChromaDB status and chunk counts."""
    try:
        rag = _get_rag_handler()
        if not rag:
            return {"available": False, "total_chunks": 0}
        
        try:
            coll = rag.client.get_collection(name="documents")
            count = coll.count()
            return {"available": True, "total_chunks": count}
        except:
            return {"available": True, "total_chunks": 0}
    except Exception as e:
        return {"available": False, "total_chunks": 0, "error": str(e)}


@router.get("/status/table-profile/{table_name}")
async def get_table_profile(table_name: str):
    """Get column statistics for a specific table."""
    try:
        conn = _get_duckdb()
        if not conn:
            return {"error": "DuckDB not available", "columns": []}
        
        # Get row count
        try:
            row_count = conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]
        except:
            return {"error": f"Table {table_name} not found", "columns": []}
        
        # Get column info
        columns = []
        try:
            col_info = conn.execute(f"PRAGMA table_info('{table_name}')").fetchall()
            for col in col_info:
                col_name = col[1]
                col_type = col[2]
                
                # Get distinct count and sample values
                try:
                    distinct = conn.execute(f'SELECT COUNT(DISTINCT "{col_name}") FROM "{table_name}"').fetchone()[0]
                    samples = conn.execute(f'SELECT DISTINCT "{col_name}" FROM "{table_name}" LIMIT 10').fetchall()
                    sample_values = [str(s[0]) for s in samples if s[0] is not None]
                except:
                    distinct = 0
                    sample_values = []
                
                columns.append({
                    "name": col_name,
                    "type": col_type,
                    "distinct_count": distinct,
                    "sample_values": sample_values[:5]
                })
        except Exception as e:
            logger.debug(f"Column info error: {e}")
        
        return {
            "table_name": table_name,
            "row_count": row_count,
            "columns": columns,
            "column_count": len(columns)
        }
    except Exception as e:
        logger.error(f"[STATUS] Table profile failed: {e}")
        return {"error": str(e), "columns": []}


@router.get("/status/data-integrity")
async def get_data_integrity():
    """Get data integrity status."""
    try:
        conn = _get_duckdb()
        if not conn:
            return {"healthy": False, "issues": []}
        
        issues = []
        
        # Check for orphaned metadata
        try:
            # Get actual tables
            actual = set()
            for row in conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'").fetchall():
                if not row[0].startswith('_'):
                    actual.add(row[0])
            
            # Get metadata tables
            metadata = set()
            try:
                for row in conn.execute("SELECT DISTINCT table_name FROM _schema_metadata").fetchall():
                    metadata.add(row[0])
            except:
                pass
            
            # Find orphans
            orphaned_metadata = metadata - actual
            if orphaned_metadata:
                issues.append({
                    "type": "orphaned_metadata",
                    "count": len(orphaned_metadata),
                    "items": list(orphaned_metadata)[:5]
                })
        except Exception as e:
            logger.debug(f"Integrity check error: {e}")
        
        return {
            "healthy": len(issues) == 0,
            "issues": issues,
            "checked_at": str(datetime.now())
        }
    except Exception as e:
        return {"healthy": False, "issues": [], "error": str(e)}
