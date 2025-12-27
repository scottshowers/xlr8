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
    Delete a structured data file (drops DuckDB table).
    
    FIXED: Now also cleans _schema_metadata and _pdf_tables
    """
    logger.info(f"[CLEANUP] Deleting structured file: {filename} from {project_id}")
    
    conn = _get_duckdb(project_id)
    if not conn:
        return {"success": True, "message": f"Project database not found, file considered deleted"}
    
    try:
        # Convert filename to table name
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
        dropped = []
        for matched_table in matched_tables:
            try:
                conn.execute(f'DROP TABLE IF EXISTS "{matched_table}"')
                dropped.append(matched_table)
                logger.info(f"[CLEANUP] Dropped table: {matched_table}")
                
                # Clean metadata for this specific table
                _clean_metadata_tables(conn, table_name=matched_table)
                
            except Exception as drop_e:
                logger.warning(f"[CLEANUP] Failed to drop {matched_table}: {drop_e}")
        
        # Also clean by filename pattern
        _clean_metadata_tables(conn, filename=filename)
        
        return {
            "success": True, 
            "message": f"Deleted {filename}", 
            "tables_dropped": dropped,
            "metadata_cleaned": True
        }
        
    except Exception as e:
        logger.error(f"[CLEANUP] Delete structured failed: {e}")
        raise HTTPException(500, f"Failed to delete: {str(e)}")


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
async def delete_document(filename: str):
    """Delete a document's chunks from ChromaDB."""
    logger.info(f"[CLEANUP] Deleting document: {filename}")
    
    collection = _get_chromadb()
    if not collection:
        return {"success": True, "message": "Document store not available, considered deleted"}
    
    try:
        # Try different metadata field names
        for field in ['filename', 'source', 'file']:
            try:
                results = collection.get(where={field: filename})
                if results and results['ids']:
                    collection.delete(ids=results['ids'])
                    logger.info(f"[CLEANUP] Deleted {len(results['ids'])} chunks for {filename}")
                    return {"success": True, "deleted_chunks": len(results['ids']), "filename": filename}
            except Exception as e:
                logger.debug(f"[CLEANUP] Field {field} not found: {e}")
                continue
        
        # Try partial match on IDs
        try:
            all_docs = collection.get()
            matching_ids = [id for id in all_docs['ids'] if filename.lower() in id.lower()]
            if matching_ids:
                collection.delete(ids=matching_ids)
                logger.info(f"[CLEANUP] Deleted {len(matching_ids)} chunks by ID match for {filename}")
                return {"success": True, "deleted_chunks": len(matching_ids), "filename": filename}
        except Exception as e:
            logger.debug(f"Suppressed: {e}")
        
        return {"success": True, "message": "Document not found or already deleted", "filename": filename}
        
    except Exception as e:
        logger.error(f"[CLEANUP] Delete document failed: {e}")
        raise HTTPException(500, f"Failed to delete: {str(e)}")


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
