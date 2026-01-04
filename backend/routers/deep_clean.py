"""
Deep Clean Router - Registry-First Orphan Cleanup
==================================================

FIXED: Registry is now the SOURCE OF TRUTH.
- Files in Registry are VALID
- Files in DuckDB/ChromaDB but NOT in Registry are ORPHANS

Deploy to: backend/routers/deep_clean.py

Endpoint: POST /api/deep-clean
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, Set
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_registry_files(project_id: Optional[str] = None) -> Set[str]:
    """
    Get all valid filenames from DocumentRegistry (the source of truth).
    Returns lowercase filenames for case-insensitive matching.
    """
    valid_files = set()
    
    try:
        from utils.database.models import DocumentRegistryModel, ProjectModel
        
        if project_id:
            # Try to get project UUID from name if needed
            if len(project_id) < 32:  # Likely a name, not UUID
                proj = ProjectModel.get_by_name(project_id)
                if proj:
                    project_id = proj.get('id')
            
            entries = DocumentRegistryModel.get_by_project(project_id, include_global=True)
        else:
            entries = DocumentRegistryModel.get_all()
        
        for entry in entries:
            filename = entry.get('filename', '')
            if filename:
                valid_files.add(filename.lower())
        
        logger.info(f"[DEEP-CLEAN] Registry contains {len(valid_files)} valid files")
        
    except Exception as e:
        logger.error(f"[DEEP-CLEAN] Failed to get registry files: {e}")
    
    return valid_files


@router.post("/deep-clean")
async def deep_clean(project_id: Optional[str] = None, confirm: bool = False, force: bool = False):
    """
    Deep clean all orphaned data across all storage systems.
    
    REGISTRY IS SOURCE OF TRUTH:
    - Files in Registry are VALID
    - Files in DuckDB/ChromaDB but NOT in Registry are ORPHANS and get deleted
    
    This cleans:
    - DuckDB orphan tables (tables for files not in registry)
    - DuckDB orphan metadata (_schema_metadata, _pdf_tables for non-existent files)
    - DuckDB orphan support data (file_metadata, column_profiles)
    - ChromaDB orphan chunks (chunks for files not in registry)
    - Playbook progress cache for deleted files
    
    Args:
        project_id: Optional - clean only this project. If None, cleans everything.
        confirm: Must be True to actually delete (safety check)
        force: If True, proceed even if Registry is empty (for intentional full wipe)
    
    Returns:
        Summary of what was cleaned
    """
    
    if not confirm:
        return {
            "warning": "This will delete orphaned data. Pass confirm=true to proceed.",
            "preview": await _preview_orphans(project_id)
        }
    
    results = {
        "duckdb_tables": {"cleaned": 0, "errors": []},
        "duckdb_metadata": {"cleaned": 0, "errors": []},
        "chromadb": {"cleaned": 0, "errors": []},
        "playbook_cache": {"cleaned": 0, "errors": []},
    }
    
    # =========================================================================
    # STEP 1: Determine what to clean
    # =========================================================================
    
    if force:
        # FORCE MODE: Wipe EVERYTHING regardless of registry
        logger.warning("[DEEP-CLEAN] FORCE MODE - wiping ALL data, ignoring registry")
        valid_files = set()  # Empty set = everything is orphan
        wipe_all = True
    else:
        # NORMAL MODE: Only clean orphans (files not in registry)
        valid_files = _get_registry_files(project_id)
        wipe_all = False
        
        if not valid_files:
            logger.warning("[DEEP-CLEAN] Registry returned no files - skipping cleanup to prevent data loss")
            return {
                "success": False,
                "error": "Registry returned no files. This could indicate a connection issue. Aborting to prevent data loss. Use force=true to wipe everything.",
                "details": results
            }
    
    # =========================================================================
    # STEP 2: CLEAN DUCKDB
    # =========================================================================
    try:
        from utils.structured_data_handler import get_structured_handler
        handler = get_structured_handler()
        conn = handler.conn
        
        if wipe_all:
            # FORCE: Delete ALL user tables and metadata
            logger.warning("[DEEP-CLEAN] Wiping ALL DuckDB tables...")
            
            # Get all tables except system tables
            all_tables = conn.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'main'
                AND table_name NOT LIKE 'information_schema%'
            """).fetchall()
            
            system_tables = {'_schema_metadata', '_column_profiles', '_load_versions', 
                           '_intelligence_lookups', '_intelligence_relationships',
                           '_pdf_tables', '_playbook_results', 'information_schema'}
            
            for (table_name,) in all_tables:
                if table_name.startswith('_'):
                    # System table - clear data but keep structure
                    if table_name in ('_schema_metadata', '_column_profiles', '_pdf_tables'):
                        try:
                            conn.execute(f'DELETE FROM "{table_name}"')
                            results["duckdb_metadata"]["cleaned"] += 1
                            logger.info(f"[DEEP-CLEAN] Cleared metadata table: {table_name}")
                        except Exception as e:
                            logger.warning(f"[DEEP-CLEAN] Could not clear {table_name}: {e}")
                else:
                    # User table - drop it
                    try:
                        conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
                        results["duckdb_tables"]["cleaned"] += 1
                        logger.info(f"[DEEP-CLEAN] Dropped table: {table_name}")
                    except Exception as e:
                        results["duckdb_tables"]["errors"].append(f"{table_name}: {str(e)}")
            
            conn.commit()
            
        else:
            # NORMAL: Only clean orphans based on registry
            orphan_tables = []
            try:
                if project_id:
                    meta_result = conn.execute("""
                        SELECT table_name, file_name FROM _schema_metadata 
                        WHERE LOWER(project) LIKE ?
                    """, [f"%{project_id.lower()}%"]).fetchall()
                else:
                    meta_result = conn.execute(
                        "SELECT table_name, file_name FROM _schema_metadata"
                    ).fetchall()
                
                for table_name, file_name in meta_result:
                    if file_name and file_name.lower() not in valid_files:
                        orphan_tables.append((table_name, file_name, '_schema_metadata'))
                        
            except Exception as e:
                results["duckdb_metadata"]["errors"].append(f"_schema_metadata query: {str(e)}")
            
            # Get all files referenced in _pdf_tables
            try:
                table_check = conn.execute("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_name = '_pdf_tables'
                """).fetchone()
                
                if table_check[0] > 0:
                    if project_id:
                        pdf_result = conn.execute("""
                            SELECT table_name, source_file FROM _pdf_tables 
                            WHERE LOWER(project) LIKE ? OR LOWER(project_id) LIKE ?
                        """, [f"%{project_id.lower()}%", f"%{project_id.lower()}%"]).fetchall()
                    else:
                        pdf_result = conn.execute(
                            "SELECT table_name, source_file FROM _pdf_tables"
                        ).fetchall()
                    
                    for table_name, source_file in pdf_result:
                        if source_file and source_file.lower() not in valid_files:
                            # Avoid duplicates
                            if not any(t[0] == table_name for t in orphan_tables):
                                orphan_tables.append((table_name, source_file, '_pdf_tables'))
                                
            except Exception as e:
                results["duckdb_metadata"]["errors"].append(f"_pdf_tables query: {str(e)}")
            
            # Drop orphan tables and clean metadata
            for table_name, file_name, source_table in orphan_tables:
                try:
                    # Try to drop the actual table
                    try:
                        conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
                        results["duckdb_tables"]["cleaned"] += 1
                        logger.info(f"[DEEP-CLEAN] Dropped orphan table: {table_name}")
                    except Exception as drop_e:
                        logger.warning(f"[DEEP-CLEAN] Could not drop {table_name}: {drop_e}")
                    
                    # Clean metadata regardless
                    conn.execute(f"DELETE FROM _schema_metadata WHERE table_name = ?", [table_name])
                    
                    try:
                        conn.execute(f"DELETE FROM _pdf_tables WHERE table_name = ?", [table_name])
                    except Exception as e:
                        logger.debug(f"Suppressed: {e}")
                    
                    results["duckdb_metadata"]["cleaned"] += 1
                    logger.info(f"[DEEP-CLEAN] Cleaned metadata for: {table_name} (file: {file_name})")
                    
                except Exception as e:
                    results["duckdb_metadata"]["errors"].append(f"{table_name}: {str(e)}")
        
        # Clean file_metadata orphans
        try:
            table_check = conn.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name = 'file_metadata'
            """).fetchone()
            
            if table_check[0] > 0:
                if project_id:
                    fm_result = conn.execute(
                        "SELECT filename FROM file_metadata WHERE LOWER(project) LIKE ?",
                        [f"%{project_id.lower()}%"]
                    ).fetchall()
                else:
                    fm_result = conn.execute("SELECT filename FROM file_metadata").fetchall()
                
                for (filename,) in fm_result:
                    if filename and filename.lower() not in valid_files:
                        conn.execute("DELETE FROM file_metadata WHERE filename = ?", [filename])
                        results["duckdb_metadata"]["cleaned"] += 1
                        logger.info(f"[DEEP-CLEAN] Cleaned file_metadata: {filename}")
        except Exception as e:
            results["duckdb_metadata"]["errors"].append(f"file_metadata: {str(e)}")
        
        # Clean column_profiles orphans (based on tables that no longer exist)
        try:
            table_check = conn.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name = '_column_profiles'
            """).fetchone()
            
            if table_check[0] > 0:
                # Get actual tables
                actual_tables = set(t[0] for t in conn.execute("SHOW TABLES").fetchall())
                
                profile_tables = conn.execute(
                    "SELECT DISTINCT table_name FROM _column_profiles"
                ).fetchall()
                
                for (table_name,) in profile_tables:
                    if table_name not in actual_tables:
                        conn.execute("DELETE FROM _column_profiles WHERE table_name = ?", [table_name])
                        results["duckdb_metadata"]["cleaned"] += 1
                        logger.info(f"[DEEP-CLEAN] Cleaned _column_profiles for: {table_name}")
        except Exception as e:
            results["duckdb_metadata"]["errors"].append(f"_column_profiles: {str(e)}")
        
        # Checkpoint
        try:
            conn.execute("CHECKPOINT")
        except Exception as e:
            logger.debug(f"Suppressed: {e}")
            
    except Exception as e:
        logger.error(f"[DEEP-CLEAN] DuckDB cleanup failed: {e}")
        results["duckdb_tables"]["errors"].append(str(e))
    
    # =========================================================================
    # STEP 3: CLEAN CHROMADB
    # =========================================================================
    try:
        from utils.rag_handler import RAGHandler
        
        rag = RAGHandler()
        collection = rag.client.get_or_create_collection(name="documents")
        
        # Get all ChromaDB documents
        all_chroma = collection.get(include=["metadatas"], limit=10000)
        
        ids_to_delete = []
        
        if wipe_all:
            # FORCE: Delete ALL chunks
            logger.warning("[DEEP-CLEAN] Wiping ALL ChromaDB chunks...")
            ids_to_delete = all_chroma.get("ids", [])
        else:
            # NORMAL: Only delete orphans (chunks for files not in registry)
            for i, metadata in enumerate(all_chroma.get("metadatas", [])):
                filename = metadata.get("source", metadata.get("filename", ""))
                doc_project = metadata.get("project_id", metadata.get("project", ""))
                
                # Filter by project if specified
                if project_id:
                    if not (doc_project == project_id or 
                            str(doc_project).lower().startswith(project_id[:8].lower()) or
                            project_id.lower() in str(doc_project).lower()):
                        continue
                
                # Check if file is orphaned (not in registry)
                if filename and filename.lower() not in valid_files:
                    ids_to_delete.append(all_chroma["ids"][i])
        
        # Delete in batches
        if ids_to_delete:
            for i in range(0, len(ids_to_delete), 100):
                batch = ids_to_delete[i:i+100]
                collection.delete(ids=batch)
            results["chromadb"]["cleaned"] = len(ids_to_delete)
            logger.info(f"[DEEP-CLEAN] Removed {len(ids_to_delete)} ChromaDB chunks")
            
    except Exception as e:
        logger.error(f"[DEEP-CLEAN] ChromaDB cleanup failed: {e}")
        results["chromadb"]["errors"].append(str(e))
    
    # =========================================================================
    # STEP 4: CLEAN SUPABASE (only in force mode)
    # =========================================================================
    results["supabase"] = {"cleaned": 0, "errors": []}
    
    if wipe_all:
        try:
            from supabase import create_client
            
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
            
            supabase = None
            if url and key:
                supabase = create_client(url, key)
            
            if supabase:
                logger.warning("[DEEP-CLEAN] Wiping ALL Supabase data...")
                
                # Tables to wipe (in order - handle foreign key constraints)
                tables_to_wipe = [
                    "processing_jobs",         # Processing jobs
                    "document_registry",       # File registry (source of truth)
                    "learned_queries",         # Learned query patterns
                    "query_feedback",          # User feedback
                    "customer_mappings",       # Column mappings
                    "user_preferences",        # User preferences  
                    "playbook_runs",           # Playbook scan results
                    "finding_suppressions",    # Suppressed findings
                    # NOTE: lineage_edges, project_relationships, standards_rules, standards_documents 
                    # handled separately below (different key columns / no id)
                ]
                
                for table in tables_to_wipe:
                    try:
                        if project_id:
                            result = supabase.table(table).delete().eq("project_id", project_id).execute()
                        else:
                            # Delete all - need a condition that matches everything
                            result = supabase.table(table).delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
                        count = len(result.data) if result.data else 0
                        if count > 0:
                            results["supabase"]["cleaned"] += count
                            logger.info(f"[DEEP-CLEAN] Wiped {count} {table} entries")
                    except Exception as e:
                        # Table might not exist - that's fine
                        if "does not exist" not in str(e).lower():
                            results["supabase"]["errors"].append(f"{table}: {str(e)}")
                            logger.warning(f"[DEEP-CLEAN] {table} wipe: {e}")
                
                # Handle tables with non-standard keys
                special_tables = [
                    ("project_relationships", "project_name"),  # Uses project_name not project_id
                    ("standards_rules", "rule_id"),             # Uses rule_id
                    ("standards_documents", "id"),              # Standard id
                    ("lineage_edges", "source_type"),           # Composite key, no id column
                ]
                for table, key_col in special_tables:
                    try:
                        # Always delete all for these tables (they're global or use different keys)
                        result = supabase.table(table).delete().neq(key_col, "").execute()
                        count = len(result.data) if result.data else 0
                        if count > 0:
                            results["supabase"]["cleaned"] += count
                            logger.info(f"[DEEP-CLEAN] Wiped {count} {table} entries")
                    except Exception as e:
                        if "does not exist" not in str(e).lower():
                            logger.debug(f"[DEEP-CLEAN] {table}: {e}")
                
                # Clear platform_metrics (event log table - DELETE not UPDATE)
                try:
                    result = supabase.table("platform_metrics").delete().neq(
                        "id", "00000000-0000-0000-0000-000000000000"
                    ).execute()
                    count = len(result.data) if result.data else 0
                    if count > 0:
                        results["supabase"]["cleaned"] += count
                        logger.info(f"[DEEP-CLEAN] Cleared {count} platform_metrics records")
                except Exception as e:
                    logger.debug(f"[DEEP-CLEAN] platform_metrics clear: {e}")
                
                # Clear cost_tracking if full wipe
                try:
                    result = supabase.table("cost_tracking").delete().neq(
                        "id", "00000000-0000-0000-0000-000000000000"
                    ).execute()
                    count = len(result.data) if result.data else 0
                    if count > 0:
                        results["supabase"]["cleaned"] += count
                        logger.info(f"[DEEP-CLEAN] Cleared {count} cost_tracking records")
                except Exception as e:
                    logger.debug(f"[DEEP-CLEAN] cost_tracking clear: {e}")
                
                logger.warning(f"[DEEP-CLEAN] Supabase wipe complete: {results['supabase']['cleaned']} items")
            else:
                results["supabase"]["errors"].append("Supabase connection not available")
                
        except Exception as e:
            logger.error(f"[DEEP-CLEAN] Supabase cleanup failed: {e}")
            results["supabase"]["errors"].append(str(e))
    
    # =========================================================================
    # STEP 5: INVALIDATE PLAYBOOK CACHE
    # =========================================================================
    try:
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
        "registry_file_count": len(valid_files),
        "details": results,
        "project_filter": project_id
    }


async def _preview_orphans(project_id: Optional[str] = None) -> dict:
    """Preview what would be cleaned without actually deleting."""
    
    preview = {
        "registry_file_count": 0,
        "duckdb_orphan_tables": 0,
        "duckdb_orphan_metadata": 0,
        "chromadb_orphan_chunks": 0,
        "orphan_files": []
    }
    
    # Get valid files from registry
    valid_files = _get_registry_files(project_id)
    preview["registry_file_count"] = len(valid_files)
    
    if not valid_files:
        preview["warning"] = "Registry returned no files - cannot determine orphans"
        return preview
    
    orphan_file_set = set()
    
    # Check DuckDB
    try:
        from utils.structured_data_handler import get_structured_handler
        handler = get_structured_handler()
        conn = handler.conn
        
        # Check _schema_metadata
        try:
            meta_result = conn.execute("SELECT table_name, file_name FROM _schema_metadata").fetchall()
            for table_name, file_name in meta_result:
                if file_name and file_name.lower() not in valid_files:
                    preview["duckdb_orphan_tables"] += 1
                    orphan_file_set.add(file_name)
        except Exception as e:
            logger.debug(f"Suppressed: {e}")
        
        # Check _pdf_tables
        try:
            pdf_result = conn.execute("SELECT table_name, source_file FROM _pdf_tables").fetchall()
            for table_name, source_file in pdf_result:
                if source_file and source_file.lower() not in valid_files:
                    preview["duckdb_orphan_tables"] += 1
                    orphan_file_set.add(source_file)
        except Exception as e:
            logger.debug(f"Suppressed: {e}")
            
    except Exception as e:
        logger.debug(f"Suppressed: {e}")
    
    # Check ChromaDB
    try:
        from utils.rag_handler import RAGHandler
        rag = RAGHandler()
        collection = rag.client.get_or_create_collection(name="documents")
        all_chroma = collection.get(include=["metadatas"], limit=10000)
        
        for metadata in all_chroma.get("metadatas", []):
            filename = metadata.get("source", metadata.get("filename", ""))
            if filename and filename.lower() not in valid_files:
                preview["chromadb_orphan_chunks"] += 1
                orphan_file_set.add(filename)
    except Exception as e:
        logger.debug(f"Suppressed: {e}")
    
    preview["orphan_files"] = list(orphan_file_set)[:20]  # First 20
    
    return preview


@router.get("/deep-clean/preview")
async def preview_deep_clean(project_id: Optional[str] = None):
    """Preview what would be cleaned without deleting anything."""
    return await _preview_orphans(project_id)
