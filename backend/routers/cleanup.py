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
            except Exception:
                try:
                    from backend.utils.structured_data_handler import get_structured_handler
                    handler = get_structured_handler()
                    return handler.conn
                except Exception:
                    return None


def _get_chromadb():
    try:
        from services.chromadb_service import get_collection
        return get_collection()
    except ImportError:
        try:
            from backend.services.chromadb_service import get_collection
            return get_collection()
        except Exception:
            try:
                import chromadb
                from chromadb.config import Settings
                # Use same path logic as RAGHandler
                if os.path.exists("/data"):
                    persist_dir = "/data/chromadb"
                else:
                    persist_dir = os.getenv("CHROMADB_PATH", "./chroma_db")
                # Use same settings as rag_handler to avoid "different settings" error
                client = chromadb.PersistentClient(
                    path=persist_dir,
                    settings=Settings(anonymized_telemetry=False, allow_reset=True)
                )
                return client.get_or_create_collection("documents")
            except Exception:
                return None


def _clean_metadata_tables(conn, table_name: str = None, filename: str = None, project: str = None):
    """
    Clean up ALL metadata tables after a delete.
    
    CONTEXT GRAPH: Must clean _column_mappings and _column_profiles
    to ensure hub/spoke relationships are recalculated on re-upload.
    
    Note: PDF tables are now in _schema_metadata (via store_dataframe).
    The _pdf_tables table is deprecated and no longer used.
    
    The 'project' param can be either:
    - Project code (e.g., "TEA1000")  
    - Project UUID (e.g., "0a2a186d-daa2-4a33-891c-b508803fdd83")
    We check both project and project_id columns for matches.
    """
    cleaned = {
        "_schema_metadata": 0, 
        "_column_mappings": 0,
        "_column_profiles": 0,
        "_term_index": 0,
        "_entity_tables": 0,
        "_intelligence_findings": 0,
        "_intelligence_tasks": 0,
        "_intelligence_lookups": 0,
        "_intelligence_relationships": 0,
    }
    
    try:
        # Check if project_id column exists (for hybrid matching)
        has_project_id = False
        try:
            cols = [row[1] for row in conn.execute("PRAGMA table_info(_schema_metadata)").fetchall()]
            has_project_id = 'project_id' in cols
        except Exception:
            pass
        
        # 1. Clean _schema_metadata (ALL file types: Excel, CSV, PDF)
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
                # Match by project CODE or project_id UUID
                if has_project_id:
                    result = conn.execute(f"DELETE FROM _schema_metadata WHERE LOWER(project) = LOWER(?) OR project_id = ?", [project, project])
                else:
                    result = conn.execute(f"DELETE FROM _schema_metadata WHERE LOWER(project) = LOWER(?)", [project])
                cleaned["_schema_metadata"] = result.rowcount if hasattr(result, 'rowcount') else 1
                logger.info(f"[CLEANUP] Deleted from _schema_metadata by project: {project}")
        except Exception as e:
            logger.debug(f"[CLEANUP] _schema_metadata cleanup: {e}")
        
        # 2. Clean CONTEXT GRAPH tables (_column_mappings, _column_profiles)
        # These MUST be cleaned to ensure hub/spoke is recalculated on re-upload
        for ctx_table in ['_column_mappings', '_column_profiles']:
            try:
                if table_name:
                    conn.execute(f"DELETE FROM {ctx_table} WHERE table_name = ?", [table_name])
                elif filename:
                    conn.execute(f"DELETE FROM {ctx_table} WHERE file_name = ?", [filename])
                elif project:
                    # Check if this table has project_id column
                    ctx_has_project_id = False
                    try:
                        ctx_cols = [row[1] for row in conn.execute(f"PRAGMA table_info({ctx_table})").fetchall()]
                        ctx_has_project_id = 'project_id' in ctx_cols
                    except Exception:
                        pass
                    
                    if ctx_has_project_id:
                        conn.execute(f"DELETE FROM {ctx_table} WHERE LOWER(project) = LOWER(?) OR project_id = ?", [project, project])
                    else:
                        conn.execute(f"DELETE FROM {ctx_table} WHERE LOWER(project) = LOWER(?)", [project])
                cleaned[ctx_table] = 1
                logger.info(f"[CLEANUP] Cleaned {ctx_table}")
            except Exception as e:
                logger.debug(f"[CLEANUP] {ctx_table} cleanup: {e}")
        
        # 3. Clean term_index and entity_tables
        for term_table in ['_term_index', '_entity_tables']:
            try:
                if project:
                    conn.execute(f"DELETE FROM {term_table} WHERE LOWER(project) = LOWER(?)", [project])
                    cleaned[term_table] = 1
                    logger.info(f"[CLEANUP] Cleaned {term_table}")
            except Exception as e:
                logger.debug(f"[CLEANUP] {term_table} cleanup: {e}")
        
        # 4. Clean intelligence tables
        for intel_table in ['_intelligence_findings', '_intelligence_tasks', '_intelligence_lookups', '_intelligence_relationships']:
            try:
                if project:
                    conn.execute(f"DELETE FROM {intel_table} WHERE LOWER(project_name) = LOWER(?)", [project])
                    cleaned[intel_table] = 1
                    logger.info(f"[CLEANUP] Cleaned {intel_table}")
            except Exception as e:
                logger.debug(f"[CLEANUP] {intel_table} cleanup: {e}")
        
        conn.execute("CHECKPOINT")
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
    logger.warning(f"[CLEANUP] Deleting document (cascade): {filename}")
    
    result = {
        "success": True,
        "filename": filename,
        "deleted_chunks": 0,
        "registry_removed": False
    }
    
    filename_lower = filename.lower()
    
    # 1. CHROMADB - Delete chunks (case-insensitive)
    collection = _get_chromadb()
    if not collection:
        logger.warning(f"[CLEANUP] ChromaDB collection not available!")
    if collection:
        try:
            # Fetch all and do case-insensitive match on metadata
            all_docs = collection.get(include=["metadatas"])
            ids_to_delete = []
            
            # Debug: log first few docs to see metadata structure
            sample_docs = all_docs.get("metadatas", [])[:3]
            logger.warning(f"[CLEANUP] Sample metadata: {sample_docs}")
            logger.warning(f"[CLEANUP] Looking for filename: {filename_lower}")
            
            for i, metadata in enumerate(all_docs.get("metadatas", [])):
                if not metadata:
                    continue
                # Check source, filename, file fields - case insensitive
                doc_name = metadata.get("source") or metadata.get("filename") or metadata.get("file") or ""
                if doc_name.lower() == filename_lower:
                    ids_to_delete.append(all_docs["ids"][i])
            
            logger.warning(f"[CLEANUP] Found {len(ids_to_delete)} chunks to delete")
            
            if ids_to_delete:
                collection.delete(ids=ids_to_delete)
                result['deleted_chunks'] = len(ids_to_delete)
                logger.warning(f"[CLEANUP] Deleted {len(ids_to_delete)} chunks for {filename}")
                    
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
        
        # 3. STANDARDS_RULES - Remove extracted rules (cascade)
        try:
            # Delete rules where source_document matches filename
            rules_result = supabase.table('standards_rules').delete().eq('source_document', filename).execute()
            if rules_result.data:
                result['rules_removed'] = len(rules_result.data)
                logger.warning(f"[CLEANUP] Removed {len(rules_result.data)} rules from standards_rules for {filename}")
            else:
                # Try ilike for case-insensitive
                rules_result = supabase.table('standards_rules').delete().ilike('source_document', filename).execute()
                if rules_result.data:
                    result['rules_removed'] = len(rules_result.data)
                    logger.warning(f"[CLEANUP] Removed {len(rules_result.data)} rules from standards_rules (case-insensitive)")
        except Exception as e:
            logger.warning(f"[CLEANUP] Standards rules cleanup error: {e}")
    
    if result['deleted_chunks'] == 0 and not result['registry_removed'] and not result.get('rules_removed'):
        result['message'] = "Document not found or already deleted"
    else:
        parts = []
        if result['deleted_chunks'] > 0:
            parts.append(f"ChromaDB ({result['deleted_chunks']} chunks)")
        if result['registry_removed']:
            parts.append("Registry")
        if result.get('rules_removed'):
            parts.append(f"Rules ({result['rules_removed']})")
        result['message'] = f"Deleted from: {', '.join(parts)}"
    
    return result


# =============================================================================
# BULK PROJECT CLEANUP
# =============================================================================

@router.delete("/status/system-tables/all")
async def clear_all_system_tables():
    """
    Clear ALL system/metadata tables. NUCLEAR OPTION.
    
    Clears:
    - _column_mappings (semantic types, context graph)
    - _column_profiles (cardinality data)
    - _schema_metadata (table registry)
    - _intelligence_* tables
    """
    logger.warning("[CLEANUP] NUCLEAR: Clearing ALL system tables")
    
    conn = _get_duckdb(None)
    if not conn:
        return {"success": False, "error": "DuckDB not available"}
    
    cleared = {}
    tables_to_clear = [
        '_column_mappings',
        '_column_profiles', 
        '_schema_metadata',
        '_intelligence_findings',
        '_intelligence_tasks',
        '_intelligence_lookups',
        '_intelligence_relationships',
        '_intelligence_work_trail'
    ]
    
    for table in tables_to_clear:
        try:
            result = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
            count_before = result[0] if result else 0
            conn.execute(f"DELETE FROM {table}")
            cleared[table] = count_before
            logger.info(f"[CLEANUP] Cleared {count_before} rows from {table}")
        except Exception as e:
            cleared[table] = f"error: {str(e)}"
            logger.debug(f"[CLEANUP] {table}: {e}")
    
    try:
        conn.execute("CHECKPOINT")
    except Exception:
        pass
    
    logger.warning(f"[CLEANUP] NUCLEAR complete: {cleared}")
    return {"success": True, "cleared": cleared}


@router.delete("/status/project/{project_id}/all")
async def delete_all_project_data(project_id: str):
    """
    Delete ALL data for a project - complete cascade cleanup.
    
    Cleans:
    - DuckDB tables (all tables prefixed with project)
    - DuckDB metadata (_column_profiles, _column_mappings, _schema_metadata, etc.)
    - ChromaDB chunks (documents)
    - Supabase: document_registry, jobs, project_relationships, files
    """
    logger.info(f"[CLEANUP] Deleting ALL data for project: {project_id}")
    
    deleted = {
        "tables": 0, 
        "documents": 0, 
        "jobs": 0, 
        "registry": 0,
        "files": 0,
        "relationships": 0,
        "metadata": {}
    }
    
    # Build project prefixes for matching (handle variations)
    project_lower = project_id.lower()
    project_prefixes = [
        project_lower + '__',
        project_lower + '_',
        project_lower.replace('-', '') + '__',
        project_lower.replace('-', '')[:8] + '_',  # UUID first 8 chars
    ]
    
    # 1. DuckDB tables
    conn = _get_duckdb(project_id)
    if conn:
        try:
            # FIRST: Find tables registered in _schema_metadata for this project
            # This catches tables regardless of naming convention
            tables_from_metadata = set()
            try:
                meta_results = conn.execute("""
                    SELECT DISTINCT table_name FROM _schema_metadata 
                    WHERE LOWER(project) = LOWER(?) 
                       OR project_id = ?
                       OR LOWER(project) LIKE LOWER(?)
                """, [project_id, project_id, f"%{project_id}%"]).fetchall()
                tables_from_metadata = {r[0] for r in meta_results}
                logger.info(f"[CLEANUP] Found {len(tables_from_metadata)} tables in metadata for {project_id}")
            except Exception as meta_e:
                logger.debug(f"[CLEANUP] Metadata lookup: {meta_e}")
            
            tables = conn.execute("SHOW TABLES").fetchall()
            system_tables = {'_schema_metadata', '_pdf_tables', 'file_metadata', '_column_profiles', 
                           '_column_mappings', '_table_classifications', '_term_index', 
                           '_column_relationships', 'schema_info', '_join_priorities'}
            
            for (table_name,) in tables:
                # Skip system/metadata tables
                if table_name in system_tables or table_name.startswith('_'):
                    continue
                
                # Check if table belongs to this project (by prefix OR by metadata registration)
                table_lower = table_name.lower()
                matches_prefix = any(table_lower.startswith(prefix) for prefix in project_prefixes)
                in_metadata = table_name in tables_from_metadata
                
                if matches_prefix or in_metadata:
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
            # Build list of project identifiers to match (code, UUID, name variations)
            project_matches = {project_lower}
            
            # Try to look up project in Supabase to get all identifiers
            supabase = _get_supabase()
            if supabase:
                try:
                    # Try by ID (UUID)
                    result = supabase.table("projects").select("id,code,name,customer").eq("id", project_id).execute()
                    if result.data:
                        proj = result.data[0]
                        project_matches.add(proj.get('id', '').lower())
                        project_matches.add(proj.get('code', '').lower())
                        project_matches.add(proj.get('name', '').lower())
                    else:
                        # Try by code
                        result = supabase.table("projects").select("id,code,name,customer").ilike("code", project_id).execute()
                        if result.data:
                            proj = result.data[0]
                            project_matches.add(proj.get('id', '').lower())
                            project_matches.add(proj.get('code', '').lower())
                            project_matches.add(proj.get('name', '').lower())
                except Exception as lookup_e:
                    logger.debug(f"[CLEANUP] Project lookup: {lookup_e}")
            
            project_matches.discard('')  # Remove empty strings
            logger.info(f"[CLEANUP] ChromaDB cleanup - matching identifiers: {project_matches}")
            
            # Get all docs and filter by any matching project identifier
            all_docs = collection.get(include=["metadatas"])
            ids_to_delete = []
            
            for i, metadata in enumerate(all_docs.get("metadatas", [])):
                if not metadata:
                    continue
                doc_project = (metadata.get("project_id") or metadata.get("project") or "").lower()
                if doc_project in project_matches:
                    ids_to_delete.append(all_docs["ids"][i])
            
            if ids_to_delete:
                collection.delete(ids=ids_to_delete)
                deleted["documents"] = len(ids_to_delete)
                logger.info(f"[CLEANUP] Deleted {len(ids_to_delete)} ChromaDB chunks")
        except Exception as e:
            logger.warning(f"[CLEANUP] ChromaDB cleanup error: {e}")
    
    # 3. Supabase cleanup
    supabase = _get_supabase()
    if supabase:
        # Jobs
        try:
            result = supabase.table("jobs").delete().eq("project_id", project_id).execute()
            deleted["jobs"] = len(result.data) if result.data else 0
        except Exception as e:
            logger.debug(f"[CLEANUP] Jobs cleanup: {e}")
        
        # Document Registry - try multiple matching strategies
        try:
            # Strategy 1: Match by project_id column (UUID)
            result1 = supabase.table("document_registry").delete().eq("project_id", project_id).execute()
            count1 = len(result1.data) if result1.data else 0
            
            # Strategy 2: Match by project_name column (code like "TEA1000")
            result2 = supabase.table("document_registry").delete().ilike("project_name", project_id).execute()
            count2 = len(result2.data) if result2.data else 0
            
            # Strategy 3: Match by filename prefix (legacy)
            result3 = supabase.table("document_registry").delete().ilike("filename", f"{project_id}%").execute()
            count3 = len(result3.data) if result3.data else 0
            
            deleted["registry"] = count1 + count2 + count3
            logger.info(f"[CLEANUP] Deleted {deleted['registry']} from document_registry (by_project_id={count1}, by_name={count2}, by_filename={count3})")
        except Exception as e:
            logger.debug(f"[CLEANUP] Registry cleanup: {e}")
        
        # Files table
        try:
            result = supabase.table("files").delete().eq("project", project_id).execute()
            deleted["files"] = len(result.data) if result.data else 0
            logger.info(f"[CLEANUP] Deleted {deleted['files']} from files table")
        except Exception as e:
            logger.debug(f"[CLEANUP] Files cleanup: {e}")
        
        # Also try files by project_id
        if deleted["files"] == 0:
            try:
                result = supabase.table("files").delete().eq("project_id", project_id).execute()
                deleted["files"] = len(result.data) if result.data else 0
            except Exception as e:
                logger.debug(f"[CLEANUP] Files cleanup (project_id): {e}")
        
        # Project Relationships (context graph)
        try:
            result = supabase.table("project_relationships").delete().eq("project_name", project_id).execute()
            deleted["relationships"] = len(result.data) if result.data else 0
        except Exception as e:
            logger.debug(f"[CLEANUP] Relationships cleanup: {e}")
    
    logger.info(f"[CLEANUP] Complete cascade delete for {project_id}: {deleted}")
    return {"success": True, "deleted": deleted, "project_id": project_id}


# =============================================================================
# METADATA REFRESH (Force recalculation)
# =============================================================================

@router.post("/status/refresh-metrics")
async def refresh_metrics(project: str = Query(None)):
    """
    Force refresh of metrics by cleaning orphaned metadata entries.
    
    This cleans up _schema_metadata entries that reference
    tables that no longer exist in DuckDB.
    
    Note: _pdf_tables is deprecated - PDFs now use _schema_metadata.
    """
    logger.info(f"[CLEANUP] Refreshing metrics for project: {project or 'all'}")
    
    conn = _get_duckdb(project)
    if not conn:
        return {"success": False, "message": "Database not available"}
    
    try:
        # Get all actual tables
        tables = conn.execute("SHOW TABLES").fetchall()
        actual_tables = set(t[0] for t in tables)
        
        orphaned = {"_schema_metadata": 0}
        
        # Clean orphaned _schema_metadata entries (ALL file types: Excel, CSV, PDF)
        try:
            meta_result = conn.execute("SELECT table_name FROM _schema_metadata").fetchall()
            for (table_name,) in meta_result:
                if table_name not in actual_tables:
                    conn.execute("DELETE FROM _schema_metadata WHERE table_name = ?", [table_name])
                    orphaned["_schema_metadata"] += 1
                    logger.info(f"[CLEANUP] Removed orphaned _schema_metadata: {table_name}")
        except Exception as e:
            logger.debug(f"[CLEANUP] _schema_metadata refresh: {e}")
        
        # Note: _pdf_tables is deprecated - PDFs now use _schema_metadata
        
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
# =============================================================================
# REFERENCES - MOVED TO platform.py
# =============================================================================
# The /status/references endpoints have been moved to platform.py
# because they're data listing endpoints, not cleanup functions.
#
# See: backend/routers/platform.py for:
#   GET /status/references
#   DELETE /status/references/{filename}
#   DELETE /status/references
# =============================================================================


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
        
        # Note: PDF tables are now in _schema_metadata (queried above)
        
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
        except Exception:
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
        except Exception:
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
        except Exception:
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
                except Exception:
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
            except Exception:
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


@router.delete("/status/chromadb/all")
async def delete_all_chromadb_chunks():
    """
    NUCLEAR OPTION: Delete ALL chunks from ChromaDB.
    Use when normal cleanup fails.
    """
    logger.warning("[CLEANUP] NUCLEAR: Deleting ALL ChromaDB chunks!")
    
    collection = _get_chromadb()
    if not collection:
        return {"success": False, "error": "ChromaDB not available"}
    
    try:
        # Get all document IDs
        all_docs = collection.get()
        if not all_docs or not all_docs.get('ids'):
            return {"success": True, "deleted": 0, "message": "No chunks found"}
        
        chunk_ids = all_docs['ids']
        total = len(chunk_ids)
        
        # Delete in batches of 1000 to avoid timeouts
        batch_size = 1000
        deleted = 0
        for i in range(0, total, batch_size):
            batch = chunk_ids[i:i+batch_size]
            collection.delete(ids=batch)
            deleted += len(batch)
            logger.warning(f"[CLEANUP] Deleted batch {i//batch_size + 1}: {len(batch)} chunks")
        
        logger.warning(f"[CLEANUP] NUCLEAR complete: {deleted} total chunks deleted")
        return {"success": True, "deleted": deleted}
        
    except Exception as e:
        logger.error(f"[CLEANUP] NUCLEAR failed: {e}")
        return {"success": False, "error": str(e)}


@router.delete("/status/rules/all")
async def delete_all_rules():
    """
    NUCLEAR OPTION: Delete ALL rules and documents from Supabase standards tables.
    Use when re-uploading reference library from scratch.
    """
    logger.warning("[CLEANUP] NUCLEAR: Deleting ALL standards rules and documents!")
    
    supabase = _get_supabase()
    if not supabase:
        return {"success": False, "error": "Supabase not available"}
    
    result = {"success": True, "rules_deleted": 0, "documents_deleted": 0}
    
    try:
        # Delete all rules
        rules_result = supabase.table('standards_rules').delete().neq('rule_id', '').execute()
        result['rules_deleted'] = len(rules_result.data) if rules_result.data else 0
        logger.warning(f"[CLEANUP] Deleted {result['rules_deleted']} rules")
    except Exception as e:
        logger.warning(f"[CLEANUP] Rules delete error: {e}")
    
    try:
        # Delete all documents from standards_documents
        docs_result = supabase.table('standards_documents').delete().neq('document_id', '').execute()
        result['documents_deleted'] = len(docs_result.data) if docs_result.data else 0
        logger.warning(f"[CLEANUP] Deleted {result['documents_deleted']} standards documents")
    except Exception as e:
        logger.warning(f"[CLEANUP] Documents delete error: {e}")
    
    logger.warning(f"[CLEANUP] NUCLEAR complete: {result['rules_deleted']} rules, {result['documents_deleted']} documents deleted")
    return result


@router.delete("/status/semantic/all")
async def delete_all_semantic_data():
    """
    NUCLEAR OPTION: Delete ALL semantic data (ChromaDB + rules + documents).
    Use when starting fresh with reference library.
    """
    logger.warning("[CLEANUP] NUCLEAR: Deleting ALL semantic data!")
    
    result = {
        "success": True,
        "chromadb_chunks": 0,
        "rules": 0,
        "documents": 0
    }
    
    # 1. Clear ChromaDB
    collection = _get_chromadb()
    if collection:
        try:
            all_docs = collection.get()
            if all_docs and all_docs.get('ids'):
                chunk_ids = all_docs['ids']
                batch_size = 1000
                for i in range(0, len(chunk_ids), batch_size):
                    batch = chunk_ids[i:i+batch_size]
                    collection.delete(ids=batch)
                    result['chromadb_chunks'] += len(batch)
        except Exception as e:
            logger.warning(f"[CLEANUP] ChromaDB error: {e}")
    
    # 2. Clear rules and documents
    supabase = _get_supabase()
    if supabase:
        try:
            rules_result = supabase.table('standards_rules').delete().neq('rule_id', '').execute()
            result['rules'] = len(rules_result.data) if rules_result.data else 0
        except Exception as e:
            logger.warning(f"[CLEANUP] Rules error: {e}")
        
        try:
            docs_result = supabase.table('standards_documents').delete().neq('document_id', '').execute()
            result['documents'] = len(docs_result.data) if docs_result.data else 0
        except Exception as e:
            logger.warning(f"[CLEANUP] Documents error: {e}")
    
    logger.warning(f"[CLEANUP] NUCLEAR SEMANTIC complete: {result}")
    return result


@router.delete("/status/nuclear/all")
async def nuclear_delete_all_data(force: bool = Query(default=True, description="If true, delete EVERYTHING including reference library")):
    """
    NUCLEAR OPTION: Delete ALL user data from DuckDB and ChromaDB.
    
    With force=True (default): Deletes EVERYTHING. No exceptions.
    With force=False: Preserves reference library data.
    """
    logger.warning(f"[CLEANUP] ⚠️ NUCLEAR DELETE ALL - force={force}")
    
    result = {
        "tables_dropped": [],
        "metadata_cleared": {},
        "chromadb_cleared": 0,
        "supabase_cleared": {},
        "errors": []
    }
    
    # 1. DuckDB - Drop ALL non-system tables
    conn = _get_duckdb()
    if conn:
        try:
            tables = conn.execute("SHOW TABLES").fetchall()
            system_tables = {'_schema_metadata', '_pdf_tables', 'file_metadata', '_column_profiles', 
                           '_column_mappings', '_table_classifications', '_term_index', 
                           '_column_relationships', 'schema_info', '_join_priorities',
                           '_entity_config', '_suppression_rules'}
            
            for (table_name,) in tables:
                # Skip system/metadata tables (these are structural, not data)
                if table_name in system_tables or table_name.startswith('__'):
                    continue
                
                # If not force mode, skip reference/global tables
                if not force:
                    if 'reference' in table_name.lower() or 'standards' in table_name.lower():
                        continue
                    
                try:
                    conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
                    result["tables_dropped"].append(table_name)
                    logger.info(f"[CLEANUP] Dropped table: {table_name}")
                except Exception as drop_e:
                    result["errors"].append(f"Drop {table_name}: {drop_e}")
            
            # Clear ALL rows from metadata tables (but keep table structure)
            metadata_tables = ['_column_profiles', '_column_mappings', '_schema_metadata', 
                             '_table_classifications', '_term_index', '_column_relationships',
                             '_join_priorities']
            
            for meta_table in metadata_tables:
                try:
                    # Check if table exists
                    exists = conn.execute(f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '{meta_table}'").fetchone()
                    if exists and exists[0] > 0:
                        count_before = conn.execute(f"SELECT COUNT(*) FROM {meta_table}").fetchone()[0]
                        conn.execute(f"DELETE FROM {meta_table}")
                        result["metadata_cleared"][meta_table] = count_before
                except Exception as e:
                    logger.debug(f"[CLEANUP] Metadata table {meta_table}: {e}")
                    
        except Exception as e:
            result["errors"].append(f"DuckDB: {e}")
            logger.error(f"[CLEANUP] DuckDB error: {e}")
    
    # 2. ChromaDB - Clear ALL chunks
    collection = _get_chromadb()
    if collection:
        try:
            all_docs = collection.get()
            if all_docs and all_docs.get('ids'):
                if force:
                    # Delete EVERYTHING
                    ids_to_delete = all_docs['ids']
                else:
                    # Filter out reference library
                    ids_to_delete = []
                    for i, doc_id in enumerate(all_docs['ids']):
                        metadata = all_docs.get('metadatas', [{}])[i] or {}
                        project = metadata.get('project', '')
                        if project in ('Reference Library', '__STANDARDS__', 'Global/Universal'):
                            continue
                        ids_to_delete.append(doc_id)
                
                if ids_to_delete:
                    batch_size = 1000
                    for i in range(0, len(ids_to_delete), batch_size):
                        batch = ids_to_delete[i:i+batch_size]
                        collection.delete(ids=batch)
                    result["chromadb_cleared"] = len(ids_to_delete)
        except Exception as e:
            result["errors"].append(f"ChromaDB: {e}")
            logger.error(f"[CLEANUP] ChromaDB error: {e}")
    
    # 3. Supabase - Clear jobs, document registry, and documents
    supabase = _get_supabase()
    if supabase:
        # Clear jobs
        try:
            jobs = supabase.table('jobs').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
            result["supabase_cleared"]["jobs"] = len(jobs.data) if jobs.data else 0
        except Exception as e:
            logger.debug(f"[CLEANUP] Jobs: {e}")
        
        # Clear document_registry - ALL of it
        try:
            docs = supabase.table('document_registry').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
            result["supabase_cleared"]["document_registry"] = len(docs.data) if docs.data else 0
        except Exception as e:
            logger.debug(f"[CLEANUP] document_registry: {e}")
        
        # Clear documents table
        try:
            if force:
                docs = supabase.table('documents').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
            else:
                docs = supabase.table('documents').delete().neq('project_id', '__STANDARDS__').execute()
            result["supabase_cleared"]["documents"] = len(docs.data) if docs.data else 0
        except Exception as e:
            logger.debug(f"[CLEANUP] documents: {e}")
        
        # Clear standards_rules and standards_documents if force
        if force:
            try:
                rules = supabase.table('standards_rules').delete().neq('rule_id', '').execute()
                result["supabase_cleared"]["standards_rules"] = len(rules.data) if rules.data else 0
            except Exception as e:
                logger.debug(f"[CLEANUP] standards_rules: {e}")
            
            try:
                std_docs = supabase.table('standards_documents').delete().neq('document_id', '').execute()
                result["supabase_cleared"]["standards_documents"] = len(std_docs.data) if std_docs.data else 0
            except Exception as e:
                logger.debug(f"[CLEANUP] standards_documents: {e}")
    
    logger.warning(f"[CLEANUP] ⚠️ NUCLEAR DELETE ALL complete: {len(result['tables_dropped'])} tables, {result['chromadb_cleared']} chunks")
    
    return {
        "success": True,
        "message": f"Deleted {len(result['tables_dropped'])} tables, {result['chromadb_cleared']} document chunks",
        "details": result
    }
