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


def _get_duckdb(project_id: str):
    try:
        from services.duckdb_service import get_duckdb_connection
        return get_duckdb_connection(project_id)
    except ImportError:
        try:
            from backend.services.duckdb_service import get_duckdb_connection
            return get_duckdb_connection(project_id)
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


# =============================================================================
# JOB DELETION
# =============================================================================

@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a single job by ID."""
    supabase = _get_supabase()
    if not supabase:
        raise HTTPException(503, "Database not available")
    
    try:
        result = supabase.table("jobs").delete().eq("id", job_id).execute()
        
        if not result.data:
            # Job might not exist, but that's okay
            logger.warning(f"[CLEANUP] Job not found or already deleted: {job_id}")
        
        logger.info(f"[CLEANUP] Deleted job: {job_id}")
        return {"success": True, "message": f"Job {job_id} deleted"}
        
    except Exception as e:
        logger.error(f"[CLEANUP] Delete job failed: {e}")
        raise HTTPException(500, f"Failed to delete job: {str(e)}")


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
            # Must have some filter - use a always-true condition
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
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        
        query = supabase.table("jobs").delete()\
            .gte("created_at", start.isoformat())\
            .lt("created_at", end.isoformat())
        
        if project_id:
            query = query.eq("project_id", project_id)
        
        result = query.execute()
        count = len(result.data) if result.data else 0
        
        logger.info(f"[CLEANUP] Deleted {count} jobs in range {start_date} to {end_date}")
        return {"success": True, "deleted": count}
        
    except ValueError as e:
        raise HTTPException(400, f"Invalid date format: {e}")
    except Exception as e:
        logger.error(f"[CLEANUP] Delete range failed: {e}")
        raise HTTPException(500, f"Failed to delete jobs: {str(e)}")


# =============================================================================
# STRUCTURED FILE DELETION (DuckDB)
# =============================================================================

@router.delete("/status/structured/{project_id}/{filename:path}")
async def delete_structured_file(project_id: str, filename: str):
    """Delete a structured data file (drops DuckDB table)."""
    logger.info(f"[CLEANUP] Deleting structured file: {filename} from {project_id}")
    
    conn = _get_duckdb(project_id)
    if not conn:
        # No database = nothing to delete
        return {"success": True, "message": f"Project database not found, file considered deleted"}
    
    try:
        # Convert filename to table name
        table_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
        table_name = table_name.lower().replace(' ', '_').replace('-', '_')
        table_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in table_name)
        
        # Get existing tables
        tables = conn.execute("SHOW TABLES").fetchall()
        table_names = [t[0] for t in tables]
        
        # Find matching table
        matched_table = None
        if table_name in table_names:
            matched_table = table_name
        else:
            # Try partial match
            for t in table_names:
                if t.startswith(table_name[:20]) or table_name.startswith(t[:20]):
                    matched_table = t
                    break
        
        if matched_table:
            conn.execute(f'DROP TABLE IF EXISTS "{matched_table}"')
            logger.info(f"[CLEANUP] Dropped table: {matched_table}")
        
        # Clean up metadata tables
        for meta_table in ['file_metadata', 'column_profiles']:
            try:
                if 'file_metadata' in meta_table:
                    conn.execute(f"DELETE FROM {meta_table} WHERE filename = ?", [filename])
                else:
                    conn.execute(f"DELETE FROM {meta_table} WHERE table_name = ?", [matched_table or table_name])
            except:
                pass
        
        return {"success": True, "message": f"Deleted {filename}", "table": matched_table}
        
    except Exception as e:
        logger.error(f"[CLEANUP] Delete structured failed: {e}")
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
        
        # Try partial match on IDs (some systems use filename in ID)
        try:
            all_docs = collection.get()
            matching_ids = [id for id in all_docs['ids'] if filename.lower() in id.lower()]
            if matching_ids:
                collection.delete(ids=matching_ids)
                logger.info(f"[CLEANUP] Deleted {len(matching_ids)} chunks by ID match for {filename}")
                return {"success": True, "deleted_chunks": len(matching_ids), "filename": filename}
        except:
            pass
        
        return {"success": True, "message": "Document not found or already deleted", "filename": filename}
        
    except Exception as e:
        logger.error(f"[CLEANUP] Delete document failed: {e}")
        raise HTTPException(500, f"Failed to delete: {str(e)}")


# =============================================================================
# BULK PROJECT CLEANUP
# =============================================================================

@router.delete("/status/project/{project_id}/all")
async def delete_all_project_data(project_id: str):
    """Delete ALL data for a project. Use with caution!"""
    logger.info(f"[CLEANUP] Deleting ALL data for project: {project_id}")
    
    deleted = {"tables": 0, "documents": 0, "jobs": 0}
    
    # 1. DuckDB tables
    conn = _get_duckdb(project_id)
    if conn:
        try:
            tables = conn.execute("SHOW TABLES").fetchall()
            system_tables = {'file_metadata', 'column_profiles', 'schema_info'}
            
            for (table_name,) in tables:
                if table_name not in system_tables:
                    try:
                        conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
                        deleted["tables"] += 1
                    except:
                        pass
            
            # Clear metadata
            for t in ['file_metadata', 'column_profiles']:
                try:
                    conn.execute(f"DELETE FROM {t}")
                except:
                    pass
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
            except:
                pass
    
    # 3. Jobs
    supabase = _get_supabase()
    if supabase:
        try:
            result = supabase.table("jobs").delete().eq("project_id", project_id).execute()
            deleted["jobs"] = len(result.data) if result.data else 0
        except:
            pass
    
    logger.info(f"[CLEANUP] Deleted for {project_id}: {deleted}")
    return {"success": True, "deleted": deleted, "project_id": project_id}
