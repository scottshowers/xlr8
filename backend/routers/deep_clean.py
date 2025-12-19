"""
Deep Clean Router - Unified Orphan Cleanup
==========================================

One endpoint to clean ALL orphaned data across ALL storage systems.

Add to backend:
1. Save as backend/routers/deep_clean.py
2. In main.py add: from routers.deep_clean import router as deep_clean_router
3. Add: app.include_router(deep_clean_router, prefix="/api")

Endpoint: POST /api/deep-clean
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/deep-clean")
async def deep_clean(project_id: Optional[str] = None, confirm: bool = False):
    """
    Deep clean all orphaned data across all storage systems.
    
    This cleans:
    - ChromaDB orphan chunks (files not in registry)
    - DuckDB orphan metadata (_schema_metadata, _pdf_tables pointing to non-existent tables)
    - DuckDB orphan support tables (file_metadata, column_profiles for deleted files)
    - Supabase orphan documents (if applicable)
    - Playbook progress cache for deleted files
    
    Args:
        project_id: Optional - clean only this project. If None, cleans everything.
        confirm: Must be True to actually delete (safety check)
    
    Returns:
        Summary of what was cleaned
    """
    
    if not confirm:
        return {
            "warning": "This will delete orphaned data. Pass confirm=true to proceed.",
            "preview": await _preview_orphans(project_id)
        }
    
    results = {
        "chromadb": {"cleaned": 0, "errors": []},
        "duckdb_metadata": {"cleaned": 0, "errors": []},
        "duckdb_tables": {"cleaned": 0, "errors": []},
        "supabase": {"cleaned": 0, "errors": []},
        "playbook_cache": {"cleaned": 0, "errors": []},
    }
    
    # =========================================================================
    # 1. CLEAN DUCKDB ORPHANS
    # =========================================================================
    try:
        from utils.structured_data_handler import get_structured_handler
        handler = get_structured_handler()
        conn = handler.conn
        
        # Get all actual tables
        tables = conn.execute("SHOW TABLES").fetchall()
        actual_tables = set(t[0] for t in tables)
        
        # Clean _schema_metadata orphans
        try:
            if project_id:
                meta_result = conn.execute(
                    "SELECT table_name FROM _schema_metadata WHERE LOWER(project) LIKE ?",
                    [f"%{project_id.lower()}%"]
                ).fetchall()
            else:
                meta_result = conn.execute("SELECT table_name FROM _schema_metadata").fetchall()
            
            for (table_name,) in meta_result:
                if table_name not in actual_tables:
                    conn.execute("DELETE FROM _schema_metadata WHERE table_name = ?", [table_name])
                    results["duckdb_metadata"]["cleaned"] += 1
                    logger.info(f"[DEEP-CLEAN] Removed orphan _schema_metadata: {table_name}")
        except Exception as e:
            results["duckdb_metadata"]["errors"].append(f"_schema_metadata: {str(e)}")
        
        # Clean _pdf_tables orphans
        try:
            table_check = conn.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name = '_pdf_tables'
            """).fetchone()
            
            if table_check[0] > 0:
                if project_id:
                    pdf_result = conn.execute(
                        "SELECT table_name FROM _pdf_tables WHERE LOWER(project) LIKE ? OR LOWER(project_id) LIKE ?",
                        [f"%{project_id.lower()}%", f"%{project_id.lower()}%"]
                    ).fetchall()
                else:
                    pdf_result = conn.execute("SELECT table_name FROM _pdf_tables").fetchall()
                
                for (table_name,) in pdf_result:
                    if table_name not in actual_tables:
                        conn.execute("DELETE FROM _pdf_tables WHERE table_name = ?", [table_name])
                        results["duckdb_metadata"]["cleaned"] += 1
                        logger.info(f"[DEEP-CLEAN] Removed orphan _pdf_tables: {table_name}")
        except Exception as e:
            results["duckdb_metadata"]["errors"].append(f"_pdf_tables: {str(e)}")
        
        # Clean file_metadata orphans (files that no longer have tables)
        try:
            table_check = conn.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name = 'file_metadata'
            """).fetchone()
            
            if table_check[0] > 0:
                # Get all file names that have actual tables
                files_with_tables = set()
                
                try:
                    schema_files = conn.execute("SELECT DISTINCT file_name FROM _schema_metadata").fetchall()
                    for (f,) in schema_files:
                        if f:
                            files_with_tables.add(f.lower())
                except:
                    pass
                
                try:
                    pdf_files = conn.execute("SELECT DISTINCT source_file FROM _pdf_tables").fetchall()
                    for (f,) in pdf_files:
                        if f:
                            files_with_tables.add(f.lower())
                except:
                    pass
                
                # Delete file_metadata entries for files that don't exist
                if project_id:
                    fm_result = conn.execute(
                        "SELECT filename FROM file_metadata WHERE LOWER(project) LIKE ?",
                        [f"%{project_id.lower()}%"]
                    ).fetchall()
                else:
                    fm_result = conn.execute("SELECT filename FROM file_metadata").fetchall()
                
                for (filename,) in fm_result:
                    if filename and filename.lower() not in files_with_tables:
                        conn.execute("DELETE FROM file_metadata WHERE filename = ?", [filename])
                        results["duckdb_metadata"]["cleaned"] += 1
                        logger.info(f"[DEEP-CLEAN] Removed orphan file_metadata: {filename}")
        except Exception as e:
            results["duckdb_metadata"]["errors"].append(f"file_metadata: {str(e)}")
        
        # Clean column_profiles orphans
        try:
            table_check = conn.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name = 'column_profiles'
            """).fetchone()
            
            if table_check[0] > 0:
                if project_id:
                    cp_result = conn.execute(
                        "SELECT DISTINCT table_name FROM column_profiles WHERE LOWER(project) LIKE ?",
                        [f"%{project_id.lower()}%"]
                    ).fetchall()
                else:
                    cp_result = conn.execute("SELECT DISTINCT table_name FROM column_profiles").fetchall()
                
                for (table_name,) in cp_result:
                    if table_name not in actual_tables:
                        conn.execute("DELETE FROM column_profiles WHERE table_name = ?", [table_name])
                        results["duckdb_metadata"]["cleaned"] += 1
                        logger.info(f"[DEEP-CLEAN] Removed orphan column_profiles for: {table_name}")
        except Exception as e:
            results["duckdb_metadata"]["errors"].append(f"column_profiles: {str(e)}")
        
        # Checkpoint to persist
        try:
            conn.execute("CHECKPOINT")
        except:
            pass
            
    except Exception as e:
        logger.error(f"[DEEP-CLEAN] DuckDB cleanup failed: {e}")
        results["duckdb_metadata"]["errors"].append(str(e))
    
    # =========================================================================
    # 2. CLEAN CHROMADB ORPHANS
    # =========================================================================
    try:
        from utils.rag_handler import RAGHandler
        
        rag = RAGHandler()
        collection = rag.client.get_or_create_collection(name="documents")
        
        # Get all ChromaDB documents
        all_chroma = collection.get(include=["metadatas"], limit=10000)
        
        # Build set of valid files (from DuckDB metadata)
        valid_files = set()
        try:
            handler = get_structured_handler()
            conn = handler.conn
            
            try:
                schema_files = conn.execute("SELECT DISTINCT file_name FROM _schema_metadata").fetchall()
                for (f,) in schema_files:
                    if f:
                        valid_files.add(f.lower())
            except:
                pass
            
            try:
                pdf_files = conn.execute("SELECT DISTINCT source_file FROM _pdf_tables").fetchall()
                for (f,) in pdf_files:
                    if f:
                        valid_files.add(f.lower())
            except:
                pass
        except:
            pass
        
        # Also check Supabase document registry
        try:
            from utils.database.supabase_client import get_supabase
            supabase = get_supabase()
            if supabase:
                docs = supabase.table("documents").select("name").execute()
                for doc in docs.data or []:
                    if doc.get("name"):
                        valid_files.add(doc["name"].lower())
        except:
            pass
        
        # Find and delete orphans
        ids_to_delete = []
        for i, metadata in enumerate(all_chroma.get("metadatas", [])):
            filename = metadata.get("source", metadata.get("filename", ""))
            doc_project = metadata.get("project_id", metadata.get("project", ""))
            
            # Filter by project if specified
            if project_id:
                if not (doc_project == project_id or 
                        str(doc_project).lower().startswith(project_id[:8].lower())):
                    continue
            
            # Check if file is orphaned
            if filename and filename.lower() not in valid_files:
                ids_to_delete.append(all_chroma["ids"][i])
        
        # Delete in batches
        if ids_to_delete:
            for i in range(0, len(ids_to_delete), 100):
                batch = ids_to_delete[i:i+100]
                collection.delete(ids=batch)
            results["chromadb"]["cleaned"] = len(ids_to_delete)
            logger.info(f"[DEEP-CLEAN] Removed {len(ids_to_delete)} ChromaDB orphan chunks")
            
    except Exception as e:
        logger.error(f"[DEEP-CLEAN] ChromaDB cleanup failed: {e}")
        results["chromadb"]["errors"].append(str(e))
    
    # =========================================================================
    # 3. CLEAN SUPABASE ORPHANS
    # =========================================================================
    try:
        from utils.database.supabase_client import get_supabase
        supabase = get_supabase()
        
        if supabase:
            # Get valid files from DuckDB
            valid_files = set()
            try:
                handler = get_structured_handler()
                conn = handler.conn
                
                try:
                    schema_files = conn.execute("SELECT DISTINCT file_name FROM _schema_metadata").fetchall()
                    for (f,) in schema_files:
                        if f:
                            valid_files.add(f.lower())
                except:
                    pass
                
                try:
                    pdf_files = conn.execute("SELECT DISTINCT source_file FROM _pdf_tables").fetchall()
                    for (f,) in pdf_files:
                        if f:
                            valid_files.add(f.lower())
                except:
                    pass
            except:
                pass
            
            # Clean documents table
            try:
                if project_id:
                    docs = supabase.table("documents").select("id, name").eq("project_id", project_id).execute()
                else:
                    docs = supabase.table("documents").select("id, name").execute()
                
                for doc in docs.data or []:
                    if doc.get("name") and doc["name"].lower() not in valid_files:
                        supabase.table("documents").delete().eq("id", doc["id"]).execute()
                        results["supabase"]["cleaned"] += 1
                        logger.info(f"[DEEP-CLEAN] Removed Supabase document: {doc['name']}")
            except Exception as e:
                results["supabase"]["errors"].append(f"documents: {str(e)}")
            
            # Clean document_registry table
            try:
                if project_id:
                    registry = supabase.table("document_registry").select("id, filename").eq("project_id", project_id).execute()
                else:
                    registry = supabase.table("document_registry").select("id, filename").execute()
                
                for doc in registry.data or []:
                    if doc.get("filename") and doc["filename"].lower() not in valid_files:
                        supabase.table("document_registry").delete().eq("id", doc["id"]).execute()
                        results["supabase"]["cleaned"] += 1
                        logger.info(f"[DEEP-CLEAN] Removed Supabase registry: {doc['filename']}")
            except Exception as e:
                results["supabase"]["errors"].append(f"document_registry: {str(e)}")
                
    except Exception as e:
        logger.error(f"[DEEP-CLEAN] Supabase cleanup failed: {e}")
        results["supabase"]["errors"].append(str(e))
    
    # =========================================================================
    # 4. INVALIDATE PLAYBOOK CACHE
    # =========================================================================
    try:
        # Clear in-memory playbook progress cache
        from routers.playbooks import PLAYBOOK_PROGRESS, PLAYBOOK_CACHE
        
        if project_id:
            if project_id in PLAYBOOK_PROGRESS:
                del PLAYBOOK_PROGRESS[project_id]
                results["playbook_cache"]["cleaned"] += 1
        else:
            count = len(PLAYBOOK_PROGRESS)
            PLAYBOOK_PROGRESS.clear()
            PLAYBOOK_CACHE.clear()
            results["playbook_cache"]["cleaned"] = count
            
        logger.info(f"[DEEP-CLEAN] Cleared playbook cache")
    except Exception as e:
        # Cache might not exist, that's fine
        logger.debug(f"[DEEP-CLEAN] Playbook cache clear: {e}")
    
    # =========================================================================
    # SUMMARY
    # =========================================================================
    total_cleaned = sum(r["cleaned"] for r in results.values())
    total_errors = sum(len(r["errors"]) for r in results.values())
    
    logger.warning(f"[DEEP-CLEAN] Complete: {total_cleaned} items cleaned, {total_errors} errors")
    
    return {
        "success": True,
        "total_cleaned": total_cleaned,
        "total_errors": total_errors,
        "details": results,
        "project_filter": project_id
    }


async def _preview_orphans(project_id: Optional[str] = None) -> dict:
    """Preview what would be cleaned without actually deleting."""
    
    preview = {
        "duckdb_metadata_orphans": 0,
        "chromadb_orphans": 0,
        "supabase_orphans": 0,
    }
    
    try:
        from utils.structured_data_handler import get_structured_handler
        handler = get_structured_handler()
        conn = handler.conn
        
        tables = conn.execute("SHOW TABLES").fetchall()
        actual_tables = set(t[0] for t in tables)
        
        # Count _schema_metadata orphans
        try:
            meta_result = conn.execute("SELECT table_name FROM _schema_metadata").fetchall()
            for (table_name,) in meta_result:
                if table_name not in actual_tables:
                    preview["duckdb_metadata_orphans"] += 1
        except:
            pass
        
        # Count _pdf_tables orphans
        try:
            pdf_result = conn.execute("SELECT table_name FROM _pdf_tables").fetchall()
            for (table_name,) in pdf_result:
                if table_name not in actual_tables:
                    preview["duckdb_metadata_orphans"] += 1
        except:
            pass
            
    except:
        pass
    
    return preview


@router.get("/deep-clean/preview")
async def preview_deep_clean(project_id: Optional[str] = None):
    """Preview what would be cleaned without deleting anything."""
    return await _preview_orphans(project_id)
