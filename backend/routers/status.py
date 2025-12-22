"""
Status Router - Registry-Aware Version
======================================

UPDATED December 20, 2025:
- Thread-safe DuckDB operations (safe_execute, safe_fetchall, safe_fetchone)
- Data integrity now classifies INSIGHTS vs ISSUES
- Optional fields (orgudfield*, udf*, report_category) are insights, not issues
- Health score only affected by actual issues

UPDATED December 19, 2025:
- Delete endpoints now call DocumentRegistryModel.unregister()
- Registry is the SOURCE OF TRUTH for all file existence checks
- Added /status/registry/sync endpoint for one-time cleanup

FIXED December 19, 2025:
- Delete now ALWAYS cleans _schema_metadata and _pdf_tables
- Case-insensitive matching for project/filename
- Explicit checkpoint after deletes
- Metadata cleanup happens even if table drop fails
- Added /status/structured/clean-orphans endpoint

Deploy to: backend/routers/status.py
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
from datetime import datetime
import sys
import logging
import json
import traceback
import re

sys.path.insert(0, '/app')
sys.path.insert(0, '/data')

from utils.rag_handler import RAGHandler
from utils.database.models import ProcessingJobModel, DocumentModel, DocumentRegistryModel

# Import structured data handler
try:
    from utils.structured_data_handler import get_structured_handler
    STRUCTURED_AVAILABLE = True
except ImportError:
    STRUCTURED_AVAILABLE = False

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== STRUCTURED DATA STATUS ====================

@router.get("/status/structured")
async def get_structured_data_status(project: Optional[str] = None):
    """
    Get structured data (DuckDB) statistics.
    
    Uses document_registry as source of truth, enriched with DuckDB table details.
    """
    import time
    start_time = time.time()
    logger.info(f"[STATUS/STRUCTURED] Starting request, project={project}")
    
    if not STRUCTURED_AVAILABLE:
        logger.warning("[STATUS/STRUCTURED] Handler not available")
        return {
            "available": False,
            "error": "Structured data handler not available",
            "files": [],
            "total_files": 0,
            "total_tables": 0,
            "total_rows": 0
        }
    
    try:
        handler = get_structured_handler()
        logger.info(f"[STATUS/STRUCTURED] Got handler in {time.time() - start_time:.2f}s")
        
        # =================================================================
        # STEP 1: Get valid files from REGISTRY (source of truth)
        # =================================================================
        valid_files = set()
        try:
            # Get registry entries for DuckDB files
            if project:
                # Try to get project_id from project name
                from utils.database.models import ProjectModel
                proj_record = ProjectModel.get_by_name(project)
                project_id = proj_record.get('id') if proj_record else None
                
                registry_entries = DocumentRegistryModel.get_by_project(project_id, include_global=True)
            else:
                registry_entries = DocumentRegistryModel.get_all()
            
            # Filter to only DuckDB files
            for entry in registry_entries:
                storage = entry.get('storage_type', '')
                if storage in ('duckdb', 'both'):
                    valid_files.add(entry.get('filename', '').lower())
            
            logger.info(f"[STATUS/STRUCTURED] Registry has {len(valid_files)} valid DuckDB files")
            
            # If registry is empty, return empty - no fallback to stale metadata
            if not valid_files:
                logger.info("[STATUS/STRUCTURED] Registry is empty, returning empty result")
                return {
                    "available": True,
                    "files": [],
                    "total_files": 0,
                    "total_tables": 0,
                    "total_rows": 0
                }
                
        except Exception as reg_e:
            logger.warning(f"[STATUS/STRUCTURED] Registry query failed: {reg_e}")
            # Don't fall back - return empty if registry fails
            return {
                "available": True,
                "files": [],
                "total_files": 0,
                "total_tables": 0,
                "total_rows": 0,
                "registry_error": str(reg_e)
            }
        
        # =================================================================
        # STEP 2: Get table details from DuckDB metadata
        # =================================================================
        tables = []
        try:
            logger.info("[STATUS/STRUCTURED] Querying _schema_metadata...")
            metadata_result = handler.safe_fetchall("""
                SELECT table_name, project, file_name, sheet_name, columns, row_count, created_at
                FROM _schema_metadata 
                WHERE is_current = TRUE
            """)
            logger.info(f"[STATUS/STRUCTURED] _schema_metadata returned {len(metadata_result)} rows")
            
            for row in metadata_result:
                table_name, proj, filename, sheet, columns_json, row_count, created_at = row
                
                # Filter by project if specified
                if project and proj and proj.lower() != project.lower():
                    continue
                
                # Filter by registry (if available)
                if valid_files is not None and filename and filename.lower() not in valid_files:
                    logger.debug(f"[STATUS/STRUCTURED] Skipping {filename} - not in registry")
                    continue
                
                # Verify table actually exists
                try:
                    handler.safe_execute(f'SELECT 1 FROM "{table_name}" LIMIT 1')
                except:
                    logger.warning(f"[STATUS] Skipping stale metadata for non-existent table: {table_name}")
                    continue
                
                try:
                    columns_data = json.loads(columns_json) if columns_json else []
                    columns = [c.get('name', c) if isinstance(c, dict) else c for c in columns_data]
                except:
                    columns = []
                
                tables.append({
                    'table_name': table_name,
                    'project': proj,
                    'file': filename,
                    'sheet': sheet,
                    'columns': columns,
                    'row_count': row_count or 0,
                    'loaded_at': str(created_at) if created_at else None,
                    'source_type': 'excel'
                })
            
            logger.info(f"[STATUS] Got {len(tables)} tables from _schema_metadata (Excel)")
            
        except Exception as meta_e:
            logger.warning(f"Metadata query failed: {meta_e}")
        
        # =================================================================
        # STEP 3: Also query _pdf_tables for PDF-derived tables
        # =================================================================
        try:
            # First check if table exists
            table_check = handler.safe_fetchone("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name = '_pdf_tables'
            """)
            logger.info(f"[STATUS] _pdf_tables exists: {table_check[0] > 0}")
            
            if table_check[0] > 0:
                pdf_result = handler.safe_fetchall("""
                    SELECT table_name, source_file, project, project_id, row_count, columns, created_at
                    FROM _pdf_tables
                """)
                logger.info(f"[STATUS] _pdf_tables has {len(pdf_result)} rows")
            else:
                pdf_result = []
            
            pdf_count = 0
            for row in pdf_result:
                table_name, source_file, proj, project_id, row_count, columns_json, created_at = row
                
                # Filter by project if specified
                if project and proj and proj.lower() != project.lower():
                    continue
                
                # Filter by registry (if available)
                if valid_files is not None and source_file and source_file.lower() not in valid_files:
                    logger.debug(f"[STATUS/STRUCTURED] Skipping PDF {source_file} - not in registry")
                    continue
                
                # Verify table actually exists
                try:
                    handler.safe_execute(f'SELECT 1 FROM "{table_name}" LIMIT 1')
                except:
                    logger.warning(f"[STATUS] Skipping stale metadata for non-existent PDF table: {table_name}")
                    continue
                
                try:
                    columns = json.loads(columns_json) if columns_json else []
                except:
                    columns = []
                
                tables.append({
                    'table_name': table_name,
                    'project': proj or 'Unknown',
                    'file': source_file,
                    'sheet': 'PDF Data',
                    'columns': columns,
                    'row_count': row_count or 0,
                    'loaded_at': str(created_at) if created_at else None,
                    'source_type': 'pdf'
                })
                pdf_count += 1
            
            logger.info(f"[STATUS] Got {pdf_count} tables from _pdf_tables (PDF)")
            
        except Exception as pdf_e:
            logger.debug(f"PDF tables query: {pdf_e}")
        
        # =================================================================
        # STEP 4: Fallback to information_schema if no metadata
        # =================================================================
        if not tables:
            logger.warning("No metadata found, falling back to information_schema")
            
            try:
                table_result = handler.safe_fetchall("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'main'
                    AND table_name NOT LIKE '_%'
                """)
                
                for (table_name,) in table_result:
                    try:
                        count_result = handler.safe_fetchone(f'SELECT COUNT(*) FROM "{table_name}"')
                        row_count = count_result[0] if count_result else 0
                        
                        col_result = handler.safe_fetchall(f'PRAGMA table_info("{table_name}")')
                        columns = [col[1] for col in col_result] if col_result else []
                        
                        parts = table_name.split('__')
                        if len(parts) >= 2:
                            proj = parts[0]
                            filename = '__'.join(parts[1:])
                            sheet = ''
                        else:
                            proj = 'default'
                            filename = table_name
                            sheet = ''
                        
                        if project and proj.lower() != project.lower():
                            continue
                        
                        # Filter by registry (if available)
                        if valid_files is not None and filename and filename.lower() not in valid_files:
                            continue
                        
                        tables.append({
                            'table_name': table_name,
                            'project': proj,
                            'file': filename,
                            'sheet': sheet,
                            'columns': columns,
                            'row_count': row_count,
                            'loaded_at': None,
                            'source_type': 'unknown'
                        })
                    except Exception as te:
                        logger.warning(f"Error getting info for table {table_name}: {te}")
            except Exception as qe:
                logger.error(f"Error querying tables: {qe}")
                schema = handler.get_schema_for_project(project)
                tables = schema.get('tables', [])
        
        # Group by file
        files_dict = {}
        total_rows = 0
        
        for table in tables:
            file_name = table.get('file', 'Unknown')
            project_name = table.get('project', 'Unknown')
            source_type = table.get('source_type', 'unknown')
            
            key = f"{project_name}:{file_name}"
            if key not in files_dict:
                files_dict[key] = {
                    'filename': file_name,
                    'project': project_name,
                    'sheets': [],
                    'total_rows': 0,
                    'loaded_at': None,
                    'source_type': source_type
                }
            
            row_count = table.get('row_count', 0)
            columns_list = table.get('columns', [])
            loaded_at = table.get('loaded_at')
            
            files_dict[key]['sheets'].append({
                'table_name': table.get('table_name'),
                'sheet_name': table.get('sheet', ''),
                'columns': columns_list,
                'column_count': len(columns_list),
                'row_count': row_count,
                'encrypted_columns': []
            })
            files_dict[key]['total_rows'] += row_count
            total_rows += row_count
            
            if loaded_at and (files_dict[key]['loaded_at'] is None or loaded_at > files_dict[key]['loaded_at']):
                files_dict[key]['loaded_at'] = loaded_at
        
        files_list = list(files_dict.values())
        
        logger.info(f"[STATUS] Found {len(files_list)} files, {len(tables)} tables, {total_rows} rows")
        
        return {
            "available": True,
            "files": files_list,
            "total_files": len(files_list),
            "total_tables": len(tables),
            "total_rows": total_rows
        }
        
    except Exception as e:
        logger.error(f"Structured data status error: {e}", exc_info=True)
        return {
            "available": False,
            "error": str(e),
            "files": [],
            "total_files": 0,
            "total_tables": 0,
            "total_rows": 0
        }


# =============================================================================
# FIXED DELETE ENDPOINT
# =============================================================================

@router.delete("/status/structured/{project}/{filename}")
async def delete_structured_file(project: str, filename: str):
    """
    Delete a structured data file from DuckDB.
    
    FIXED: Now properly cleans _schema_metadata and _pdf_tables even if
    table lookup or drop fails.
    """
    logger.warning(f"[DELETE] Request to delete project={project}, filename={filename}")
    
    if not STRUCTURED_AVAILABLE:
        raise HTTPException(status_code=503, detail="Structured data not available")
    
    try:
        handler = get_structured_handler()
        conn = handler.conn
        deleted_tables = []
        metadata_cleaned = {"_schema_metadata": 0, "_pdf_tables": 0}
        
        # Normalize for case-insensitive matching
        project_lower = project.lower()
        filename_lower = filename.lower()
        
        # =================================================================
        # STEP 1: Find and drop tables from _schema_metadata (Excel files)
        # =================================================================
        tables_from_metadata = []
        try:
            # Case-insensitive lookup
            tables_result = conn.execute("""
                SELECT table_name FROM _schema_metadata 
                WHERE LOWER(project) = ? AND LOWER(file_name) = ?
            """, [project_lower, filename_lower]).fetchall()
            
            tables_from_metadata = [t[0] for t in tables_result]
            logger.info(f"[DELETE] Found {len(tables_from_metadata)} tables in _schema_metadata")
            
        except Exception as meta_e:
            logger.warning(f"[DELETE] Metadata lookup failed: {meta_e}")
        
        # Drop the tables
        for table_name in tables_from_metadata:
            try:
                conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
                deleted_tables.append(table_name)
                logger.info(f"[DELETE] Dropped table: {table_name}")
            except Exception as te:
                logger.warning(f"[DELETE] Could not drop {table_name}: {te}")
        
        # =================================================================
        # STEP 2: ALWAYS clean _schema_metadata (even if table drop failed)
        # =================================================================
        try:
            conn.execute("""
                DELETE FROM _schema_metadata 
                WHERE LOWER(project) = ? AND LOWER(file_name) = ?
            """, [project_lower, filename_lower])
            metadata_cleaned["_schema_metadata"] = len(tables_from_metadata) or 1
            logger.info(f"[DELETE] Cleaned _schema_metadata")
        except Exception as meta_del_e:
            logger.warning(f"[DELETE] Failed to clean _schema_metadata: {meta_del_e}")
        
        # =================================================================
        # STEP 3: Find and drop tables from _pdf_tables (PDF files)
        # =================================================================
        try:
            # Check if _pdf_tables exists
            table_check = conn.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name = '_pdf_tables'
            """).fetchone()
            
            if table_check[0] > 0:
                # Case-insensitive lookup
                pdf_result = conn.execute("""
                    SELECT table_name FROM _pdf_tables 
                    WHERE LOWER(source_file) = ? 
                       OR (LOWER(project) = ? AND LOWER(source_file) LIKE ?)
                       OR LOWER(source_file) LIKE ?
                """, [filename_lower, project_lower, f"%{filename_lower}%", f"%{filename_lower}%"]).fetchall()
                
                pdf_tables = [t[0] for t in pdf_result]
                logger.info(f"[DELETE] Found {len(pdf_tables)} tables in _pdf_tables")
                
                for table_name in pdf_tables:
                    try:
                        conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
                        if table_name not in deleted_tables:
                            deleted_tables.append(table_name)
                        logger.info(f"[DELETE] Dropped PDF table: {table_name}")
                    except Exception as te:
                        logger.warning(f"[DELETE] Could not drop PDF table {table_name}: {te}")
                
                # ALWAYS clean _pdf_tables
                conn.execute("""
                    DELETE FROM _pdf_tables 
                    WHERE LOWER(source_file) = ? 
                       OR (LOWER(project) = ? AND LOWER(source_file) LIKE ?)
                       OR LOWER(source_file) LIKE ?
                """, [filename_lower, project_lower, f"%{filename_lower}%", f"%{filename_lower}%"])
                metadata_cleaned["_pdf_tables"] = len(pdf_tables) or 1
                logger.info(f"[DELETE] Cleaned _pdf_tables")
                
        except Exception as pdf_e:
            logger.warning(f"[DELETE] PDF tables check failed: {pdf_e}")
        
        # =================================================================
        # STEP 4: Fallback - pattern matching on actual tables
        # =================================================================
        if not deleted_tables:
            try:
                # Generate expected table name pattern
                safe_project = project_lower.replace(' ', '_').replace('-', '_')
                safe_file = filename.rsplit('.', 1)[0].lower().replace(' ', '_').replace('-', '_')
                
                all_tables = conn.execute("SHOW TABLES").fetchall()
                for (tbl,) in all_tables:
                    tbl_lower = tbl.lower()
                    # Match: project__filename or project__filename__sheet
                    if tbl_lower.startswith(f"{safe_project}__{safe_file}"):
                        try:
                            conn.execute(f'DROP TABLE IF EXISTS "{tbl}"')
                            deleted_tables.append(tbl)
                            logger.info(f"[DELETE] Dropped by pattern match: {tbl}")
                            
                            # Also clean metadata for this table
                            try:
                                conn.execute("DELETE FROM _schema_metadata WHERE table_name = ?", [tbl])
                            except:
                                pass
                            try:
                                conn.execute("DELETE FROM _pdf_tables WHERE table_name = ?", [tbl])
                            except:
                                pass
                                
                        except Exception as drop_e:
                            logger.warning(f"[DELETE] Could not drop {tbl}: {drop_e}")
                            
            except Exception as fb_e:
                logger.warning(f"[DELETE] Fallback pattern match failed: {fb_e}")
        
        # =================================================================
        # STEP 5: COMMIT and Checkpoint to persist changes
        # =================================================================
        try:
            conn.commit()
            logger.warning("[DELETE] Committed delete operations")
        except Exception as commit_e:
            logger.warning(f"[DELETE] Commit failed: {commit_e}")
        
        try:
            conn.execute("CHECKPOINT")
            logger.info("[DELETE] Checkpoint complete")
        except Exception as cp_e:
            logger.debug(f"[DELETE] Checkpoint failed (may not be needed): {cp_e}")
        
        # =================================================================
        # STEP 6: Unregister from document registry (SOURCE OF TRUTH)
        # =================================================================
        registry_cleaned = False
        try:
            # Try to find the project_id for this project name
            from utils.database.models import ProjectModel
            project_record = ProjectModel.get_by_name(project)
            project_id = project_record.get('id') if project_record else None
            
            # Unregister from registry
            registry_cleaned = DocumentRegistryModel.unregister(filename, project_id)
            if registry_cleaned:
                logger.info(f"[DELETE] Unregistered {filename} from document registry")
            else:
                # Try without project_id (might be global)
                registry_cleaned = DocumentRegistryModel.unregister(filename, None)
                if registry_cleaned:
                    logger.info(f"[DELETE] Unregistered {filename} from document registry (global)")
        except Exception as reg_e:
            logger.warning(f"[DELETE] Registry unregister failed: {reg_e}")
        
        result = {
            "deleted_tables": deleted_tables,
            "count": len(deleted_tables),
            "metadata_cleaned": metadata_cleaned,
            "registry_cleaned": registry_cleaned
        }
        
        logger.warning(f"[DELETE] Result: {result}")
        return {"success": True, "message": f"Deleted {filename}", "details": result}
        
    except Exception as e:
        logger.error(f"Failed to delete structured file: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ORPHAN CLEANUP ENDPOINT
# =============================================================================

@router.post("/status/structured/clean-orphans")
async def clean_orphaned_metadata(project: Optional[str] = None):
    """
    Remove metadata entries that reference non-existent tables.
    
    Call this to fix stale metrics after deletes.
    """
    if not STRUCTURED_AVAILABLE:
        raise HTTPException(503, "Structured data not available")
    
    try:
        handler = get_structured_handler()
        conn = handler.conn
        
        # Get all actual tables
        tables = conn.execute("SHOW TABLES").fetchall()
        actual_tables = set(t[0] for t in tables)
        
        orphaned = {"_schema_metadata": 0, "_pdf_tables": 0}
        
        # Clean orphaned _schema_metadata entries
        try:
            if project:
                meta_result = conn.execute(
                    "SELECT table_name FROM _schema_metadata WHERE LOWER(project) = ?",
                    [project.lower()]
                ).fetchall()
            else:
                meta_result = conn.execute("SELECT table_name FROM _schema_metadata").fetchall()
            
            for (table_name,) in meta_result:
                if table_name not in actual_tables:
                    conn.execute("DELETE FROM _schema_metadata WHERE table_name = ?", [table_name])
                    orphaned["_schema_metadata"] += 1
                    logger.info(f"[CLEANUP] Removed orphaned _schema_metadata: {table_name}")
                    
        except Exception as e:
            logger.warning(f"[CLEANUP] _schema_metadata cleanup error: {e}")
        
        # Clean orphaned _pdf_tables entries
        try:
            table_check = conn.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name = '_pdf_tables'
            """).fetchone()
            
            if table_check[0] > 0:
                if project:
                    pdf_result = conn.execute(
                        "SELECT table_name FROM _pdf_tables WHERE LOWER(project) = ? OR LOWER(project_id) = ?",
                        [project.lower(), project.lower()]
                    ).fetchall()
                else:
                    pdf_result = conn.execute("SELECT table_name FROM _pdf_tables").fetchall()
                
                for (table_name,) in pdf_result:
                    if table_name not in actual_tables:
                        conn.execute("DELETE FROM _pdf_tables WHERE table_name = ?", [table_name])
                        orphaned["_pdf_tables"] += 1
                        logger.info(f"[CLEANUP] Removed orphaned _pdf_tables: {table_name}")
                        
        except Exception as e:
            logger.warning(f"[CLEANUP] _pdf_tables cleanup error: {e}")
        
        # Checkpoint
        try:
            conn.execute("CHECKPOINT")
        except:
            pass
        
        logger.info(f"[CLEANUP] Orphan cleanup complete: {orphaned}")
        return {
            "success": True, 
            "orphaned_removed": orphaned, 
            "actual_tables": len(actual_tables)
        }
        
    except Exception as e:
        logger.error(f"[CLEANUP] Failed: {e}")
        raise HTTPException(500, str(e))


@router.post("/status/structured/reset")
async def reset_structured_data():
    """Reset all structured data (DuckDB)"""
    if not STRUCTURED_AVAILABLE:
        raise HTTPException(status_code=503, detail="Structured data not available")
    
    try:
        handler = get_structured_handler()
        result = handler.reset_database()
        logger.warning("⚠️ Structured data (DuckDB) was RESET - all data deleted!")
        return {"success": True, "message": "All structured data deleted", "details": result}
    except Exception as e:
        logger.error(f"Failed to reset structured data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/chromadb")
async def get_chromadb_stats():
    """Get ChromaDB statistics"""
    import time
    start_time = time.time()
    logger.info("[STATUS/CHROMADB] Starting request...")
    try:
        rag = RAGHandler()
        logger.info(f"[STATUS/CHROMADB] RAGHandler initialized in {time.time() - start_time:.2f}s")
        collection = rag.client.get_or_create_collection(name="documents")
        count = collection.count()
        logger.info(f"[STATUS/CHROMADB] Got count={count} in {time.time() - start_time:.2f}s total")
        return {"total_chunks": count}
    except Exception as e:
        logger.error(f"ChromaDB stats error: {e}")
        return {"total_chunks": 0, "error": str(e)}


@router.get("/jobs")
async def get_processing_jobs(limit: int = 50, status: Optional[str] = None, days: Optional[int] = 7):
    """Get processing jobs from database. Default shows last 7 days."""
    try:
        if days:
            jobs = ProcessingJobModel.get_recent(days=days, limit=limit)
        else:
            jobs = ProcessingJobModel.get_all(limit=limit)
        
        if status:
            jobs = [j for j in jobs if j.get("status") == status]
        
        return {"jobs": jobs, "total": len(jobs), "days_filter": days}
    except Exception as e:
        logger.error(f"Failed to get processing jobs: {e}")
        return {"jobs": [], "total": 0, "error": str(e)}


@router.delete("/jobs/old")
async def delete_old_jobs(days: int = 7, start_date: Optional[str] = None, end_date: Optional[str] = None):
    """Delete processing jobs by date range or older than X days"""
    try:
        if start_date and end_date:
            # Use date range
            count = ProcessingJobModel.delete_by_date_range(start_date, end_date)
            return {"success": True, "message": f"Deleted {count} jobs from {start_date} to {end_date}", "deleted_count": count}
        else:
            # Use days threshold
            count = ProcessingJobModel.delete_older_than(days=days)
            return {"success": True, "message": f"Deleted {count} jobs older than {days} days", "deleted_count": count}
    except Exception as e:
        logger.error(f"Failed to delete old jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get status of a specific processing job"""
    try:
        job = ProcessingJobModel.get_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/{job_id}/fail")
async def fail_job_manually(job_id: str, error_message: str = "Manually terminated by user"):
    """Manually fail a stuck processing job"""
    try:
        job = ProcessingJobModel.get_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        success = ProcessingJobModel.fail(job_id, error_message)
        
        if success:
            logger.info(f"Job {job_id} manually failed by user")
            return {
                "success": True,
                "message": f"Job {job_id} marked as failed",
                "job_id": job_id
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update job status")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fail job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a processing job record"""
    try:
        success = ProcessingJobModel.delete(job_id)
        if success:
            return {"success": True, "message": f"Job {job_id} deleted"}
        else:
            raise HTTPException(status_code=404, detail="Job not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/jobs")
async def delete_all_jobs():
    """Delete all processing job records"""
    try:
        count = ProcessingJobModel.delete_all()
        return {"success": True, "message": f"Deleted {count} jobs"}
    except Exception as e:
        logger.error(f"Failed to delete all jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== DOCUMENT STATUS ====================

@router.get("/status/documents")
async def get_documents(project: Optional[str] = None, limit: int = 1000):
    """
    Get all documents.
    
    Uses document_registry as source of truth.
    """
    import time
    start_time = time.time()
    logger.info("[STATUS/DOCUMENTS] Starting request...")
    
    try:
        # =================================================================
        # Get documents from REGISTRY (source of truth)
        # =================================================================
        documents = []
        
        try:
            if project:
                # Check if project is a UUID or name
                is_uuid = len(project) == 36 and '-' in project
                
                if is_uuid:
                    project_id = project
                else:
                    # Try to get project_id from project name
                    from utils.database.models import ProjectModel
                    proj_record = ProjectModel.get_by_name(project)
                    project_id = proj_record.get('id') if proj_record else None
                
                # Handle global projects
                if project.upper() in ('__GLOBAL__', 'GLOBAL', 'GLOBAL/UNIVERSAL'):
                    registry_entries = DocumentRegistryModel.get_by_project(None, include_global=False)
                    # Filter to only global
                    registry_entries = [e for e in registry_entries if e.get('is_global')]
                else:
                    registry_entries = DocumentRegistryModel.get_by_project(project_id, include_global=True)
            else:
                registry_entries = DocumentRegistryModel.get_all(limit=limit)
            
            logger.info(f"[STATUS/DOCUMENTS] Registry returned {len(registry_entries)} entries")
            
            for entry in registry_entries:
                doc_entry = {
                    "id": entry.get("id"),
                    "filename": entry.get("filename", "unknown"),
                    "file_type": entry.get("file_type", ""),
                    "file_size": entry.get("file_size"),
                    "project": entry.get("metadata", {}).get("project_name") or ("GLOBAL" if entry.get("is_global") else "unknown"),
                    "project_id": entry.get("project_id"),
                    "functional_area": entry.get("metadata", {}).get("functional_area", ""),
                    "upload_date": entry.get("created_at", ""),
                    "chunks": entry.get("chunk_count", 0),
                    "storage_type": entry.get("storage_type", ""),
                    "usage_type": entry.get("usage_type", ""),
                    "is_global": entry.get("is_global", False),
                }
                documents.append(doc_entry)
                
        except Exception as reg_e:
            logger.warning(f"[STATUS/DOCUMENTS] Registry query failed: {reg_e}")
            # Don't fall back - if registry fails, return empty
            return {"documents": [], "total": 0, "total_chunks": 0, "error": f"Registry unavailable: {reg_e}"}
        
        # Sort by upload date (newest first)
        documents.sort(key=lambda x: x.get("upload_date", "") or "", reverse=True)
        
        total_chunks = sum(d.get("chunks", 0) for d in documents)
        
        logger.info(f"[STATUS/DOCUMENTS] Returning {len(documents)} documents in {time.time() - start_time:.2f}s")
        
        return {
            "documents": documents,
            "total": len(documents),
            "total_chunks": total_chunks
        }
        
    except Exception as e:
        logger.error(f"Document status error: {e}", exc_info=True)
        return {"documents": [], "total": 0, "total_chunks": 0, "error": str(e)}


@router.delete("/status/documents/{doc_id}")
async def delete_document(doc_id: str, filename: str = None, project: str = None):
    """Delete a document and its chunks from ChromaDB"""
    try:
        # Check if doc_id is a UUID or a filename
        is_uuid = len(doc_id) == 36 and '-' in doc_id
        
        doc = None
        if is_uuid:
            doc = DocumentModel.get_by_id(doc_id)
        
        # Use filename from param, doc_id (if it's a filename), or from doc record
        actual_filename = filename or (doc_id if not is_uuid else None)
        if doc:
            actual_filename = doc.get("name", actual_filename)
        
        # Delete from ChromaDB
        if actual_filename:
            try:
                rag = RAGHandler()
                collection = rag.client.get_or_create_collection(name="documents")
                
                # Try multiple metadata fields
                for field in ["filename", "source", "name"]:
                    results = collection.get(where={field: actual_filename})
                    if results and results['ids']:
                        collection.delete(ids=results['ids'])
                        logger.info(f"Deleted {len(results['ids'])} chunks from ChromaDB (field: {field})")
                        break
            except Exception as ce:
                logger.warning(f"ChromaDB deletion issue: {ce}")
        
        # Delete from Supabase if we have a doc record
        if doc:
            DocumentModel.delete(doc.get("id"))
            logger.info(f"Deleted document {doc.get('id')} from Supabase")
        elif not is_uuid and actual_filename:
            # Try to find and delete by filename
            try:
                from utils.database.supabase_client import get_supabase
                supabase = get_supabase()
                if supabase:
                    supabase.table('documents').delete().eq('name', actual_filename).execute()
                    logger.info(f"Deleted document by filename: {actual_filename}")
            except Exception as db_e:
                logger.warning(f"Could not delete from Supabase by filename: {db_e}")
        
        # =================================================================
        # Unregister from document registry (SOURCE OF TRUTH)
        # =================================================================
        registry_cleaned = False
        try:
            # Get project_id from doc or param
            project_id = doc.get("project_id") if doc else None
            
            if actual_filename:
                registry_cleaned = DocumentRegistryModel.unregister(actual_filename, project_id)
                if registry_cleaned:
                    logger.info(f"Unregistered {actual_filename} from document registry")
                elif not project_id:
                    # File might be global or project_id not found
                    logger.info(f"Registry entry not found for {actual_filename} (may not exist)")
        except Exception as reg_e:
            logger.warning(f"Registry unregister failed: {reg_e}")
        
        return {"success": True, "message": f"Document deleted", "registry_cleaned": registry_cleaned}
            
    except Exception as e:
        logger.error(f"Failed to delete document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/status/documents/reset")
async def reset_all_documents():
    """Reset all documents (ChromaDB, database, and registry)"""
    try:
        # Reset ChromaDB
        chroma_count = 0
        try:
            rag = RAGHandler()
            collection = rag.client.get_or_create_collection(name="documents")
            all_ids = collection.get()['ids']
            if all_ids:
                collection.delete(ids=all_ids)
                chroma_count = len(all_ids)
            logger.warning(f"⚠️ Deleted {chroma_count} chunks from ChromaDB")
        except Exception as ce:
            logger.error(f"ChromaDB reset error: {ce}")
        
        # Reset database documents
        doc_count = DocumentModel.delete_all()
        logger.warning(f"⚠️ Deleted {doc_count} documents from database")
        
        # Reset document registry
        registry_count = 0
        try:
            from utils.database.supabase_client import get_supabase
            supabase = get_supabase()
            if supabase:
                # Count first
                count_result = supabase.table('document_registry').select('id', count='exact').execute()
                registry_count = count_result.count or 0
                # Delete all
                if registry_count > 0:
                    supabase.table('document_registry').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
                logger.warning(f"⚠️ Deleted {registry_count} entries from document registry")
        except Exception as reg_e:
            logger.error(f"Registry reset error: {reg_e}")
        
        return {
            "success": True, 
            "message": f"Reset complete",
            "details": {
                "chromadb_chunks": chroma_count,
                "supabase_documents": doc_count,
                "registry_entries": registry_count
            }
        }
    except Exception as e:
        logger.error(f"Failed to reset documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# REFERENCE / STANDARDS MANAGEMENT
# =============================================================================

@router.get("/status/references")
async def list_references():
    """
    List all reference/standards files (global documents).
    
    These are documents with truth_type='reference' or is_global=true.
    """
    try:
        from utils.database.supabase_client import get_supabase
        supabase = get_supabase()
        
        if not supabase:
            raise HTTPException(500, "Supabase not available")
        
        # Get from document_registry - reference or global
        result = supabase.table('document_registry') \
            .select('*') \
            .or_('truth_type.eq.reference,is_global.eq.true') \
            .order('created_at', desc=True) \
            .execute()
        
        files = result.data or []
        
        # Also get rules from standards processor
        rules_info = {'available': False, 'documents': 0, 'total_rules': 0}
        try:
            from utils.standards_processor import get_rule_registry
            registry = get_rule_registry()
            if hasattr(registry, 'documents'):
                rules_info['available'] = True
                rules_info['documents'] = len(registry.documents)
                rules_info['total_rules'] = sum(len(getattr(d, 'rules', [])) for d in registry.documents)
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Could not get rules info: {e}")
        
        return {
            'count': len(files),
            'files': files,
            'rules': rules_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing references: {e}")
        raise HTTPException(500, str(e))


@router.delete("/status/references/{filename:path}")
async def delete_reference(filename: str, confirm: bool = False):
    """
    Delete a specific reference/standards file.
    
    Removes from:
    - Document registry (Supabase)
    - ChromaDB (vector store)
    - Lineage edges
    - Rule registry (if applicable)
    
    Requires confirm=true query parameter.
    """
    if not confirm:
        raise HTTPException(400, "Must set confirm=true to delete")
    
    try:
        from utils.database.supabase_client import get_supabase
        supabase = get_supabase()
        
        deleted = {
            'registry': False,
            'chromadb': 0,
            'lineage': 0,
            'rules': False
        }
        
        # 1. Delete from document_registry
        try:
            result = supabase.table('document_registry') \
                .delete() \
                .eq('filename', filename) \
                .or_('truth_type.eq.reference,is_global.eq.true') \
                .execute()
            deleted['registry'] = len(result.data or []) > 0
        except Exception as e:
            logger.warning(f"Registry delete failed: {e}")
        
        # 2. Delete from ChromaDB
        try:
            rag = RAGHandler()
            collection = rag.client.get_or_create_collection(name="documents")
            
            # Find chunks for this file
            all_docs = collection.get(include=["metadatas"])
            ids_to_delete = []
            for i, meta in enumerate(all_docs.get('metadatas', [])):
                if meta and (meta.get('source') == filename or meta.get('filename') == filename):
                    ids_to_delete.append(all_docs['ids'][i])
            
            if ids_to_delete:
                collection.delete(ids=ids_to_delete)
                deleted['chromadb'] = len(ids_to_delete)
                logger.info(f"Deleted {len(ids_to_delete)} chunks from ChromaDB")
        except Exception as e:
            logger.warning(f"ChromaDB delete failed: {e}")
        
        # 3. Delete lineage edges
        try:
            result = supabase.table('lineage_edges') \
                .delete() \
                .eq('source_id', filename) \
                .eq('source_type', 'file') \
                .execute()
            deleted['lineage'] = len(result.data or [])
        except Exception as e:
            logger.warning(f"Lineage delete failed: {e}")
        
        # 4. Clear from rule registry
        try:
            from utils.standards_processor import get_rule_registry
            registry = get_rule_registry()
            if hasattr(registry, 'documents'):
                before = len(registry.documents)
                registry.documents = [d for d in registry.documents if getattr(d, 'filename', '') != filename]
                deleted['rules'] = len(registry.documents) < before
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Rule registry delete failed: {e}")
        
        return {
            'success': True,
            'filename': filename,
            'deleted': deleted
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting reference: {e}")
        raise HTTPException(500, str(e))


@router.delete("/status/references")
async def clear_all_references(confirm: bool = False):
    """
    Clear ALL reference/standards files.
    
    WARNING: This is destructive. Requires confirm=true.
    
    Removes from:
    - Document registry (all reference/global entries)
    - ChromaDB (all chunks for those files)
    - Lineage edges
    - Rule registry
    """
    if not confirm:
        raise HTTPException(400, "Must set confirm=true to clear all references")
    
    try:
        from utils.database.supabase_client import get_supabase
        supabase = get_supabase()
        
        deleted = {
            'registry': 0,
            'chromadb': 0,
            'lineage': 0,
            'rules': 0
        }
        
        # 1. Get all reference files first
        refs = supabase.table('document_registry') \
            .select('filename') \
            .or_('truth_type.eq.reference,is_global.eq.true') \
            .execute()
        
        filenames = [r['filename'] for r in (refs.data or [])]
        
        # 2. Delete from registry
        try:
            result = supabase.table('document_registry') \
                .delete() \
                .or_('truth_type.eq.reference,is_global.eq.true') \
                .execute()
            deleted['registry'] = len(result.data or [])
        except Exception as e:
            logger.warning(f"Registry clear failed: {e}")
        
        # 3. Delete from ChromaDB
        try:
            rag = RAGHandler()
            collection = rag.client.get_or_create_collection(name="documents")
            
            all_docs = collection.get(include=["metadatas"])
            ids_to_delete = []
            for i, meta in enumerate(all_docs.get('metadatas', [])):
                if meta:
                    source = meta.get('source') or meta.get('filename')
                    if source in filenames:
                        ids_to_delete.append(all_docs['ids'][i])
            
            if ids_to_delete:
                collection.delete(ids=ids_to_delete)
                deleted['chromadb'] = len(ids_to_delete)
        except Exception as e:
            logger.warning(f"ChromaDB clear failed: {e}")
        
        # 4. Delete lineage for these files
        try:
            for filename in filenames:
                result = supabase.table('lineage_edges') \
                    .delete() \
                    .eq('source_id', filename) \
                    .eq('source_type', 'file') \
                    .execute()
                deleted['lineage'] += len(result.data or [])
        except Exception as e:
            logger.warning(f"Lineage clear failed: {e}")
        
        # 5. Clear rule registry
        try:
            from utils.standards_processor import get_rule_registry
            registry = get_rule_registry()
            if hasattr(registry, 'documents'):
                deleted['rules'] = len(registry.documents)
                registry.documents = []
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Rule registry clear failed: {e}")
        
        return {
            'success': True,
            'files_processed': len(filenames),
            'deleted': deleted
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing references: {e}")
        raise HTTPException(500, str(e))


@router.get("/status/rules")
async def list_rules():
    """
    List all rules in the standards rule registry.
    """
    try:
        from utils.standards_processor import get_rule_registry
        registry = get_rule_registry()
        
        documents = []
        total_rules = 0
        
        if hasattr(registry, 'documents'):
            for doc in registry.documents:
                doc_info = {
                    'document_id': getattr(doc, 'document_id', 'unknown'),
                    'filename': getattr(doc, 'filename', 'unknown'),
                    'title': getattr(doc, 'title', ''),
                    'domain': getattr(doc, 'domain', 'general'),
                    'rules_count': len(getattr(doc, 'rules', []))
                }
                documents.append(doc_info)
                total_rules += doc_info['rules_count']
        
        return {
            'documents': len(documents),
            'total_rules': total_rules,
            'registry': documents
        }
        
    except ImportError:
        return {
            'documents': 0,
            'total_rules': 0,
            'registry': [],
            'note': 'Standards processor not available'
        }
    except Exception as e:
        logger.error(f"Error listing rules: {e}")
        raise HTTPException(500, str(e))


@router.get("/status/registry")
async def get_registry_status():
    """
    Get current registry status - shows what's in the registry.
    Use this to verify registry is working.
    """
    try:
        registry_entries = DocumentRegistryModel.get_all(limit=100)
        
        # Group by storage type
        by_storage = {}
        for entry in registry_entries:
            st = entry.get('storage_type', 'unknown')
            if st not in by_storage:
                by_storage[st] = []
            by_storage[st].append(entry.get('filename'))
        
        return {
            "total_entries": len(registry_entries),
            "by_storage_type": {k: len(v) for k, v in by_storage.items()},
            "sample_files": [e.get('filename') for e in registry_entries[:10]],
            "registry_working": True
        }
    except Exception as e:
        return {
            "total_entries": 0,
            "error": str(e),
            "registry_working": False
        }


@router.post("/status/registry/sync")
async def sync_document_registry():
    """
    Sync document registry with actual data in backends.
    
    This is a one-time cleanup to fix orphaned registry entries
    and add missing entries for existing files.
    
    Run this ONCE after deploying the registry-aware delete.
    """
    """
    Sync document registry with actual data in backends.
    
    This is a one-time cleanup to fix orphaned registry entries
    and add missing entries for existing files.
    
    Run this ONCE after deploying the registry-aware delete.
    """
    try:
        from utils.database.supabase_client import get_supabase
        supabase = get_supabase()
        
        results = {
            "orphans_removed": 0,
            "missing_added": 0,
            "errors": []
        }
        
        # =================================================================
        # STEP 1: Get all files that actually exist in backends
        # =================================================================
        actual_files = {}  # filename -> {storage_type, project_id, ...}
        
        # 1a. Get files from DuckDB _schema_metadata (Excel)
        if STRUCTURED_AVAILABLE:
            try:
                handler = get_structured_handler()
                meta_result = handler.safe_fetchall("""
                    SELECT DISTINCT file_name, project
                    FROM _schema_metadata 
                    WHERE is_current = TRUE AND file_name IS NOT NULL
                """)
                
                for filename, project in meta_result:
                    if filename:
                        actual_files[filename] = {
                            'storage_type': 'duckdb',
                            'project_name': project,
                            'source': '_schema_metadata'
                        }
                logger.info(f"[SYNC] Found {len(meta_result)} Excel files in _schema_metadata")
            except Exception as e:
                results["errors"].append(f"_schema_metadata query: {e}")
        
        # 1b. Get files from DuckDB _pdf_tables (PDF)
        if STRUCTURED_AVAILABLE:
            try:
                handler = get_structured_handler()
                table_check = handler.safe_fetchone("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_name = '_pdf_tables'
                """)
                
                if table_check[0] > 0:
                    pdf_result = handler.safe_fetchall("""
                        SELECT DISTINCT source_file, project, project_id
                        FROM _pdf_tables 
                        WHERE source_file IS NOT NULL
                    """)
                    
                    for filename, project, project_id in pdf_result:
                        if filename:
                            actual_files[filename] = {
                                'storage_type': 'duckdb',
                                'project_name': project,
                                'project_id': project_id,
                                'source': '_pdf_tables'
                            }
                    logger.info(f"[SYNC] Found {len(pdf_result)} PDF files in _pdf_tables")
            except Exception as e:
                results["errors"].append(f"_pdf_tables query: {e}")
        
        # 1c. Get files from ChromaDB
        try:
            rag = RAGHandler()
            collection = rag.client.get_or_create_collection(name="documents")
            chroma_results = collection.get(include=["metadatas"], limit=5000)
            
            seen_chroma = set()
            for metadata in chroma_results.get("metadatas", []):
                filename = metadata.get("source") or metadata.get("filename")
                if filename and filename not in seen_chroma:
                    seen_chroma.add(filename)
                    if filename not in actual_files:
                        actual_files[filename] = {
                            'storage_type': 'chromadb',
                            'project_name': metadata.get("project"),
                            'project_id': metadata.get("project_id"),
                            'source': 'chromadb'
                        }
                    elif actual_files[filename]['storage_type'] == 'duckdb':
                        # File is in both
                        actual_files[filename]['storage_type'] = 'both'
            
            logger.info(f"[SYNC] Found {len(seen_chroma)} unique files in ChromaDB")
        except Exception as e:
            results["errors"].append(f"ChromaDB query: {e}")
        
        # =================================================================
        # STEP 2: Get all entries currently in registry
        # =================================================================
        registry_entries = {}
        try:
            registry_data = DocumentRegistryModel.get_all(limit=5000)
            for entry in registry_data:
                registry_entries[entry['filename']] = entry
            logger.info(f"[SYNC] Found {len(registry_entries)} entries in registry")
        except Exception as e:
            results["errors"].append(f"Registry query: {e}")
        
        # =================================================================
        # STEP 3: Remove orphaned registry entries (file doesn't exist)
        # =================================================================
        for filename, entry in registry_entries.items():
            if filename not in actual_files:
                try:
                    DocumentRegistryModel.unregister(filename, entry.get('project_id'))
                    results["orphans_removed"] += 1
                    logger.info(f"[SYNC] Removed orphan: {filename}")
                except Exception as e:
                    results["errors"].append(f"Remove orphan {filename}: {e}")
        
        # =================================================================
        # STEP 4: Add missing registry entries (file exists but not registered)
        # =================================================================
        for filename, file_info in actual_files.items():
            if filename not in registry_entries:
                try:
                    # Determine usage type
                    is_global = file_info.get('project_name', '').lower() in (
                        'global', '__global__', 'reference library', 'reference_library'
                    )
                    
                    # Try to get project_id from project name
                    project_id = file_info.get('project_id')
                    if not project_id and file_info.get('project_name') and not is_global:
                        try:
                            from utils.database.models import ProjectModel
                            proj = ProjectModel.get_by_name(file_info['project_name'])
                            if proj:
                                project_id = proj.get('id')
                        except:
                            pass
                    
                    DocumentRegistryModel.register(
                        filename=filename,
                        file_type=filename.rsplit('.', 1)[-1] if '.' in filename else None,
                        storage_type=file_info['storage_type'],
                        usage_type='structured_data' if file_info['storage_type'] in ('duckdb', 'both') else 'rag_knowledge',
                        project_id=project_id if not is_global else None,
                        is_global=is_global,
                        metadata={
                            'project_name': file_info.get('project_name'),
                            'synced_from': file_info.get('source'),
                            'synced_at': datetime.utcnow().isoformat()
                        }
                    )
                    results["missing_added"] += 1
                    logger.info(f"[SYNC] Added missing: {filename}")
                except Exception as e:
                    results["errors"].append(f"Add missing {filename}: {e}")
        
        logger.info(f"[SYNC] Complete: {results}")
        
        return {
            "success": True,
            "message": f"Registry sync complete",
            "actual_files_found": len(actual_files),
            "registry_entries_before": len(registry_entries),
            "orphans_removed": results["orphans_removed"],
            "missing_added": results["missing_added"],
            "errors": results["errors"][:10] if results["errors"] else []
        }
        
    except Exception as e:
        logger.error(f"Registry sync failed: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


# ==================== COLUMN MAPPING ENDPOINTS ====================

@router.get("/status/mappings/{project}")
async def get_project_mappings(project: str, file_name: str = None):
    """Get all column mappings for a project"""
    if not STRUCTURED_AVAILABLE:
        raise HTTPException(503, "Structured data not available")
    
    try:
        handler = get_structured_handler()
        mappings = handler.get_column_mappings(project, file_name=file_name)
        needs_review = handler.get_mappings_needing_review(project)
        
        return {
            "project": project,
            "mappings": mappings,
            "total_mappings": len(mappings),
            "needs_review_count": len(needs_review),
            "needs_review": needs_review
        }
    except Exception as e:
        logger.error(f"Failed to get mappings: {e}")
        raise HTTPException(500, str(e))


@router.get("/status/mappings/{project}/{file_name}/summary")
async def get_file_mapping_summary(project: str, file_name: str):
    """Get mapping summary for a specific file (for badge display)"""
    if not STRUCTURED_AVAILABLE:
        raise HTTPException(503, "Structured data not available")
    
    try:
        handler = get_structured_handler()
        summary = handler.get_file_mapping_summary(project, file_name)
        return summary
    except Exception as e:
        logger.error(f"Failed to get mapping summary: {e}")
        raise HTTPException(500, str(e))


@router.get("/status/mapping-job/{job_id}")
async def get_mapping_job_status(job_id: str):
    """Get status of a column inference job"""
    if not STRUCTURED_AVAILABLE:
        raise HTTPException(503, "Structured data not available")
    
    try:
        handler = get_structured_handler()
        status = handler.get_mapping_job_status(job_id=job_id)
        if not status:
            raise HTTPException(404, "Job not found")
        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status: {e}")
        raise HTTPException(500, str(e))


@router.get("/status/mapping-jobs/{project}")
async def get_project_mapping_jobs(project: str):
    """Get all mapping jobs for a project"""
    if not STRUCTURED_AVAILABLE:
        raise HTTPException(503, "Structured data not available")
    
    try:
        handler = get_structured_handler()
        status = handler.get_mapping_job_status(project=project)
        return {"project": project, "jobs": status if isinstance(status, list) else [status] if status else []}
    except Exception as e:
        logger.error(f"Failed to get project jobs: {e}")
        raise HTTPException(500, str(e))


from pydantic import BaseModel

class MappingUpdate(BaseModel):
    semantic_type: str

@router.put("/status/mappings/{project}/{table_name}/{column_name}")
async def update_column_mapping(project: str, table_name: str, column_name: str, update: MappingUpdate):
    """Update a column mapping (human override)"""
    if not STRUCTURED_AVAILABLE:
        raise HTTPException(503, "Structured data not available")
    
    try:
        handler = get_structured_handler()
        success = handler.update_column_mapping(
            project=project,
            table_name=table_name,
            original_column=column_name,
            semantic_type=update.semantic_type
        )
        
        if success:
            return {"status": "updated", "column": column_name, "semantic_type": update.semantic_type}
        else:
            raise HTTPException(500, "Failed to update mapping")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update mapping: {e}")
        raise HTTPException(500, str(e))


@router.get("/status/semantic-types")
async def get_semantic_types():
    """Get list of available semantic types for mapping"""
    return {
        "types": [
            {"id": "employee_number", "label": "Employee Number", "category": "keys"},
            {"id": "company_code", "label": "Company Code", "category": "keys"},
            {"id": "employment_status_code", "label": "Employment Status", "category": "status"},
            {"id": "earning_code", "label": "Earning Code", "category": "codes"},
            {"id": "deduction_code", "label": "Deduction Code", "category": "codes"},
            {"id": "job_code", "label": "Job Code", "category": "codes"},
            {"id": "department_code", "label": "Department Code", "category": "codes"},
            {"id": "amount", "label": "Amount", "category": "values"},
            {"id": "rate", "label": "Rate", "category": "values"},
            {"id": "effective_date", "label": "Effective Date", "category": "dates"},
            {"id": "start_date", "label": "Start Date", "category": "dates"},
            {"id": "end_date", "label": "End Date", "category": "dates"},
            {"id": "employee_name", "label": "Employee Name", "category": "other"},
            {"id": "NONE", "label": "Not Mapped", "category": "none"}
        ]
    }


# ==================== RELATIONSHIPS ENDPOINTS ====================

@router.get("/status/relationships/{project}")
async def get_project_relationships(project: str):
    """Get all table relationships for a project"""
    if not STRUCTURED_AVAILABLE:
        raise HTTPException(503, "Structured data not available")
    
    try:
        handler = get_structured_handler()
        relationships = handler.get_relationships(project)
        return {
            "project": project,
            "relationships": relationships
        }
    except Exception as e:
        logger.error(f"Failed to get relationships: {e}")
        raise HTTPException(500, str(e))


@router.post("/status/relationships/{project}/analyze")
async def analyze_relationships(project: str):
    """
    Auto-detect table relationships for a project.
    
    This scans all tables looking for:
    - Common column names (employee_id, company_code, etc.)
    - Foreign key patterns (_id, _code, _num suffixes)
    - Key columns identified during upload
    
    Returns the detected relationships.
    """
    if not STRUCTURED_AVAILABLE:
        raise HTTPException(503, "Structured data not available")
    
    try:
        handler = get_structured_handler()
        
        # Run relationship detection
        relationships = handler.detect_relationships(project)
        
        logger.info(f"[RELATIONSHIPS] Analyzed project {project}, found {len(relationships)} relationships")
        
        return {
            "project": project,
            "relationships_found": len(relationships),
            "relationships": relationships,
            "message": f"Detected {len(relationships)} relationships across tables"
        }
    except Exception as e:
        logger.error(f"Failed to analyze relationships: {e}")
        raise HTTPException(500, str(e))


class RelationshipCreate(BaseModel):
    source_table: str
    source_columns: list
    target_table: str
    target_columns: list

@router.post("/status/relationships/{project}")
async def create_relationship(project: str, rel: RelationshipCreate):
    """Create a new table relationship"""
    if not STRUCTURED_AVAILABLE:
        raise HTTPException(503, "Structured data not available")
    
    try:
        handler = get_structured_handler()
        handler.safe_execute("""
            INSERT INTO _table_relationships 
            (id, project, source_table, source_columns, target_table, target_columns, relationship_type, confidence)
            VALUES (?, ?, ?, ?, ?, ?, 'manual', 1.0)
        """, [
            hash(f"{project}_{rel.source_table}_{rel.target_table}") % 2147483647,
            project,
            rel.source_table,
            json.dumps(rel.source_columns),
            rel.target_table,
            json.dumps(rel.target_columns)
        ])
        handler.conn.commit()
        
        return {"status": "created", "source": rel.source_table, "target": rel.target_table}
    except Exception as e:
        logger.error(f"Failed to create relationship: {e}")
        raise HTTPException(500, str(e))


class RelationshipDelete(BaseModel):
    source_table: str
    target_table: str

@router.delete("/status/relationships/{project}")
async def delete_relationship(project: str, rel: RelationshipDelete):
    """Delete a table relationship"""
    if not STRUCTURED_AVAILABLE:
        raise HTTPException(503, "Structured data not available")
    
    try:
        handler = get_structured_handler()
        handler.safe_execute("""
            DELETE FROM _table_relationships 
            WHERE project = ? AND source_table = ? AND target_table = ?
        """, [project, rel.source_table, rel.target_table])
        handler.conn.commit()
        
        return {"status": "deleted"}
    except Exception as e:
        logger.error(f"Failed to delete relationship: {e}")
        raise HTTPException(500, str(e))


# =============================================================================
# DOCUMENT REGISTRY SETUP
# =============================================================================

@router.get("/status/document-registry/setup-sql")
async def get_registry_setup_sql():
    """
    Get SQL to create the document_registry table in Supabase.
    Run this in Supabase SQL Editor to enable document tracking.
    """
    try:
        from utils.database.models import DocumentRegistryModel
        return {
            "sql": DocumentRegistryModel.create_table_sql(),
            "instructions": [
                "1. Go to Supabase Dashboard → SQL Editor",
                "2. Paste the SQL below and run it",
                "3. This creates the document_registry table",
                "4. New uploads will be registered automatically",
                "5. Use the Audit button to verify"
            ]
        }
    except Exception as e:
        # Fallback SQL if import fails
        return {
            "sql": """
CREATE TABLE IF NOT EXISTS document_registry (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    filename TEXT NOT NULL,
    file_type TEXT,
    storage_type TEXT DEFAULT 'chromadb',
    usage_type TEXT DEFAULT 'rag_knowledge',
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    is_global BOOLEAN DEFAULT FALSE,
    chunk_count INTEGER DEFAULT 0,
    file_size INTEGER,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_doc_registry_project ON document_registry(project_id);
CREATE INDEX IF NOT EXISTS idx_doc_registry_filename ON document_registry(filename);
CREATE INDEX IF NOT EXISTS idx_doc_registry_global ON document_registry(is_global);
            """,
            "instructions": [
                "1. Go to Supabase Dashboard → SQL Editor",
                "2. Paste the SQL below and run it",
                "3. This creates the document_registry table",
                "4. New uploads will be registered automatically",
                "5. Use the Audit button to verify"
            ],
            "error": str(e)
        }


# =============================================================================
# CHROMADB CLEANUP ENDPOINTS
# =============================================================================

@router.get("/status/chromadb/audit")
async def audit_chromadb():
    """
    Audit ChromaDB contents vs Supabase registry.
    Shows orphaned documents that exist in ChromaDB but not in registry.
    """
    try:
        from utils.rag_handler import RAGHandler
        
        rag = RAGHandler()
        collection = rag.client.get_or_create_collection(name="documents")
        
        # Get all ChromaDB documents
        all_chroma = collection.get(include=["metadatas"], limit=10000)
        chroma_docs = {}
        
        for i, metadata in enumerate(all_chroma.get("metadatas", [])):
            doc_id = all_chroma["ids"][i] if all_chroma.get("ids") else f"unknown_{i}"
            filename = metadata.get("source", metadata.get("filename", "Unknown"))
            project = metadata.get("project_id", metadata.get("project", "unknown"))
            
            # Use just filename as key (project matching is fuzzy)
            if filename not in chroma_docs:
                chroma_docs[filename] = {
                    "filename": filename,
                    "project": project,
                    "chunk_ids": [],
                    "chunk_count": 0
                }
            chroma_docs[filename]["chunk_ids"].append(doc_id)
            chroma_docs[filename]["chunk_count"] += 1
        
        # Get document registry from Supabase
        registry_files = set()
        registry_available = False
        registry_error = None
        
        try:
            from utils.database.models import DocumentRegistryModel
            
            # Check if table exists
            if DocumentRegistryModel.table_exists():
                registry_available = True
                docs = DocumentRegistryModel.get_all(limit=1000)
                for doc in docs:
                    filename = doc.get("filename", "")
                    if filename:
                        registry_files.add(filename)
                logger.info(f"[AUDIT] Found {len(registry_files)} files in registry")
            else:
                registry_error = "document_registry table not found - run SQL to create it"
                logger.warning(f"[AUDIT] {registry_error}")
        except Exception as e:
            registry_error = str(e)
            logger.warning(f"[AUDIT] Could not fetch document registry: {e}")
        
        # Find orphans (in ChromaDB but not in registry)
        orphans = []
        registered = []
        
        for filename, info in chroma_docs.items():
            if filename in registry_files:
                registered.append(info)
            else:
                orphans.append(info)
        
        result = {
            "total_chroma_files": len(chroma_docs),
            "total_chroma_chunks": sum(d["chunk_count"] for d in chroma_docs.values()),
            "registered_files": len(registered),
            "orphaned_files": len(orphans),
            "registry_available": registry_available,
            "orphans": orphans[:50],
            "registered": [{"filename": r["filename"], "project": r["project"], "chunks": r["chunk_count"]} for r in registered[:50]]
        }
        
        if registry_error:
            result["registry_error"] = registry_error
            result["note"] = "Without registry, all files appear as orphans. Create the document_registry table in Supabase."
        
        return result
        
    except Exception as e:
        logger.exception(f"ChromaDB audit failed: {e}")
        raise HTTPException(500, str(e))


@router.delete("/status/chromadb/purge-orphans")
async def purge_chromadb_orphans():
    """
    Delete orphaned documents from ChromaDB.
    Only deletes docs that are NOT in Supabase registry.
    """
    try:
        from utils.rag_handler import RAGHandler
        
        # First run audit
        audit = await audit_chromadb()
        orphans = audit.get("orphans", [])
        
        if not orphans:
            return {"status": "success", "message": "No orphans to delete", "deleted": 0}
        
        rag = RAGHandler()
        collection = rag.client.get_or_create_collection(name="documents")
        
        deleted_count = 0
        deleted_files = []
        
        for orphan in orphans:
            chunk_ids = orphan.get("chunk_ids", [])
            if chunk_ids:
                try:
                    # Delete in batches
                    for i in range(0, len(chunk_ids), 100):
                        batch = chunk_ids[i:i+100]
                        collection.delete(ids=batch)
                    deleted_count += len(chunk_ids)
                    deleted_files.append(orphan.get("filename"))
                    logger.warning(f"[CHROMADB] Deleted {len(chunk_ids)} chunks for orphan: {orphan.get('filename')}")
                except Exception as e:
                    logger.warning(f"[CHROMADB] Failed to delete orphan {orphan.get('filename')}: {e}")
        
        return {
            "status": "success",
            "deleted_chunks": deleted_count,
            "deleted_files": deleted_files,
            "message": f"Purged {len(deleted_files)} orphaned files ({deleted_count} chunks)"
        }
        
    except Exception as e:
        logger.exception(f"ChromaDB purge failed: {e}")
        raise HTTPException(500, str(e))


@router.delete("/status/chromadb/purge-project/{project_id}")
async def purge_chromadb_project(project_id: str):
    """
    Delete ALL ChromaDB documents for a specific project.
    Use with caution!
    """
    try:
        from utils.rag_handler import RAGHandler
        
        rag = RAGHandler()
        collection = rag.client.get_or_create_collection(name="documents")
        
        # Get project name for flexible matching
        project_name = None
        try:
            from utils.supabase_client import get_supabase
            supabase = get_supabase()
            proj_result = supabase.table("projects").select("name").eq("id", project_id).execute()
            if proj_result.data:
                project_name = proj_result.data[0].get("name", "").upper()
        except Exception as e:
            logger.warning(f"[CHROMADB] Could not get project name: {e}")
        
        # Get all docs for this project
        all_chroma = collection.get(include=["metadatas"], limit=10000)
        
        ids_to_delete = []
        for i, metadata in enumerate(all_chroma.get("metadatas", [])):
            doc_project = metadata.get("project_id", metadata.get("project", ""))
            doc_project_str = str(doc_project)
            doc_project_upper = doc_project_str.upper()
            
            # Match by multiple methods
            is_match = (
                doc_project_str == project_id or 
                doc_project_str == project_id[:8] or
                (project_name and doc_project_upper == project_name) or
                (project_name and len(project_name) >= 3 and doc_project_upper.startswith(project_name[:3])) or
                (project_name and len(project_name) >= 3 and project_name.startswith(doc_project_upper[:3]))
            )
            
            if is_match:
                ids_to_delete.append(all_chroma["ids"][i])
        
        if not ids_to_delete:
            return {"status": "success", "message": f"No documents found for project {project_id}", "deleted": 0}
        
        # Delete in batches
        for i in range(0, len(ids_to_delete), 100):
            batch = ids_to_delete[i:i+100]
            collection.delete(ids=batch)
        
        logger.warning(f"[CHROMADB] Purged {len(ids_to_delete)} chunks for project {project_id}")
        
        return {
            "status": "success",
            "deleted_chunks": len(ids_to_delete),
            "project_id": project_id,
            "message": f"Purged all {len(ids_to_delete)} chunks for project"
        }
        
    except Exception as e:
        logger.exception(f"ChromaDB project purge failed: {e}")
        raise HTTPException(500, str(e))


@router.delete("/status/chromadb/purge-all")
async def purge_chromadb_all(confirm: str = None):
    """
    Delete ALL documents from ChromaDB.
    Requires confirm=YES parameter.
    """
    if confirm != "YES":
        raise HTTPException(400, "Must pass confirm=YES to purge all ChromaDB data")
    
    try:
        from utils.rag_handler import RAGHandler
        
        rag = RAGHandler()
        collection = rag.client.get_or_create_collection(name="documents")
        
        # Get count before
        all_chroma = collection.get(limit=10000)
        total_before = len(all_chroma.get("ids", []))
        
        if total_before == 0:
            return {"status": "success", "message": "ChromaDB already empty", "deleted": 0}
        
        # Delete in batches
        ids = all_chroma.get("ids", [])
        for i in range(0, len(ids), 100):
            batch = ids[i:i+100]
            collection.delete(ids=batch)
        
        logger.warning(f"[CHROMADB] PURGED ALL - {total_before} chunks deleted")
        
        return {
            "status": "success",
            "deleted_chunks": total_before,
            "message": f"Purged ALL {total_before} chunks from ChromaDB"
        }
        
    except Exception as e:
        logger.exception(f"ChromaDB full purge failed: {e}")
        raise HTTPException(500, str(e))


# ==================== COST TRACKING ====================

@router.get("/status/costs")
async def get_cost_summary(days: int = 30, project_id: Optional[str] = None):
    """Get cost summary for System Monitor dashboard"""
    try:
        from backend.utils.cost_tracker import get_cost_summary
        return get_cost_summary(days=days, project_id=project_id)
    except ImportError:
        return {"error": "Cost tracker not available", "total_cost": 0}
    except Exception as e:
        logger.error(f"Cost summary failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/status/costs/by-project")
async def get_costs_by_project():
    """Get costs grouped by project"""
    try:
        from backend.utils.cost_tracker import get_cost_by_project
        return get_cost_by_project()
    except ImportError:
        return []
    except Exception as e:
        logger.error(f"Cost by project failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/status/costs/recent")
async def get_recent_costs(limit: int = 100):
    """Get recent cost entries for detailed view"""
    try:
        from utils.database.supabase_client import get_supabase
        client = get_supabase()
        if not client:
            return {"error": "Supabase not available", "records": []}
        
        result = client.table("cost_tracking").select("*").order(
            "created_at", desc=True
        ).limit(limit).execute()
        
        return {"records": result.data or [], "count": len(result.data or [])}
    except Exception as e:
        logger.error(f"Recent costs query failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/status/costs/daily")
async def get_daily_costs(days: int = 7):
    """Get daily cost breakdown"""
    try:
        from backend.utils.cost_tracker import get_daily_costs
        return get_daily_costs(days=days)
    except ImportError:
        return []
    except Exception as e:
        logger.error(f"Daily costs failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/status/costs/month")
async def get_month_costs(year: int = None, month: int = None):
    """Get costs for a specific calendar month (includes fixed costs)"""
    try:
        from backend.utils.cost_tracker import get_month_costs
        return get_month_costs(year=year, month=month)
    except ImportError:
        return {"error": "Cost tracker not available"}
    except Exception as e:
        logger.error(f"Month costs failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/status/costs/fixed")
async def get_fixed_costs():
    """Get fixed/subscription costs"""
    try:
        from backend.utils.cost_tracker import get_fixed_costs
        return get_fixed_costs()
    except ImportError:
        return {"error": "Cost tracker not available", "items": [], "total": 0}
    except Exception as e:
        logger.error(f"Fixed costs failed: {e}")
        raise HTTPException(500, str(e))


@router.put("/status/costs/fixed/{name}")
async def update_fixed_cost(name: str, cost_per_unit: float = None, quantity: int = None):
    """Update a fixed cost entry"""
    try:
        from backend.utils.cost_tracker import update_fixed_cost
        return update_fixed_cost(name=name, cost_per_unit=cost_per_unit, quantity=quantity)
    except ImportError:
        return {"error": "Cost tracker not available"}
    except Exception as e:
        logger.error(f"Update fixed cost failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/status/table-profile/{table_name}")
async def get_table_profile(table_name: str):
    """Get column statistics for a specific table"""
    if not STRUCTURED_AVAILABLE:
        return {"error": "Structured data not available", "columns": []}
    
    try:
        handler = get_structured_handler()
        
        # Get row count
        row_count_result = handler.safe_fetchone(f'SELECT COUNT(*) FROM "{table_name}"')
        total_rows = row_count_result[0] if row_count_result else 0
        
        # Get column names
        columns_result = handler.safe_fetchall(f"""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = '{table_name}'
        """)
        
        column_stats = []
        for (col_name,) in columns_result:
            try:
                # Get distinct count and null count for each column
                stats = handler.safe_fetchone(f'''
                    SELECT 
                        COUNT(DISTINCT "{col_name}") as distinct_count,
                        SUM(CASE WHEN "{col_name}" IS NULL OR TRIM(CAST("{col_name}" AS VARCHAR)) = '' THEN 1 ELSE 0 END) as null_count
                    FROM "{table_name}"
                ''')
                
                distinct_count = stats[0] if stats else 0
                null_count = stats[1] if stats else 0
                fill_rate = round((total_rows - null_count) / total_rows * 100, 1) if total_rows > 0 else 0
                
                column_stats.append({
                    "name": col_name,
                    "distinct_values": distinct_count,
                    "null_count": null_count,
                    "fill_rate": fill_rate
                })
            except Exception as col_e:
                logger.warning(f"Failed to profile column {col_name}: {col_e}")
                column_stats.append({
                    "name": col_name,
                    "distinct_values": None,
                    "null_count": None,
                    "fill_rate": None,
                    "error": str(col_e)
                })
        
        return {
            "table_name": table_name,
            "total_rows": total_rows,
            "columns": column_stats
        }
        
    except Exception as e:
        logger.error(f"Table profile failed for {table_name}: {e}")
        return {"error": str(e), "columns": []}


@router.get("/status/data-integrity")
async def check_data_integrity(project: Optional[str] = None):
    """
    Check data quality across all tables for a project.
    Returns table list with health metrics for frontend display.
    
    Uses document_registry as source of truth.
    """
    if not STRUCTURED_AVAILABLE:
        return {"error": "Structured data not available", "tables": [], "total_rows": 0, "health_score": 0, "issues_count": 0}
    
    try:
        handler = get_structured_handler()
        
        all_tables = []
        total_rows = 0
        total_issues = 0
        
        # =================================================================
        # STEP 1: Get valid files from REGISTRY (source of truth)
        # =================================================================
        valid_files = set()
        try:
            if project:
                # Try to get project_id from project name
                from utils.database.models import ProjectModel
                proj_record = ProjectModel.get_by_name(project)
                project_id = proj_record.get('id') if proj_record else None
                
                registry_entries = DocumentRegistryModel.get_by_project(project_id, include_global=False)
            else:
                registry_entries = DocumentRegistryModel.get_all()
            
            # Filter to only DuckDB files
            for entry in registry_entries:
                storage = entry.get('storage_type', '')
                if storage in ('duckdb', 'both'):
                    valid_files.add(entry.get('filename', '').lower())
            
            logger.info(f"[INTEGRITY] Registry has {len(valid_files)} valid DuckDB files")
            
            # If registry is empty, return empty result
            if not valid_files:
                return {
                    "status": "healthy",
                    "tables": [],
                    "total_rows": 0,
                    "health_score": 100,
                    "issues_count": 0
                }
                
        except Exception as reg_e:
            logger.warning(f"[INTEGRITY] Registry query failed: {reg_e}")
            return {"error": f"Registry unavailable: {reg_e}", "tables": [], "total_rows": 0, "health_score": 0, "issues_count": 0}
        
        # =================================================================
        # STEP 2: Get tables that belong to registered files
        # =================================================================
        tables_to_check = []
        
        try:
            # Get from _schema_metadata
            meta_result = handler.safe_fetchall("""
                SELECT DISTINCT table_name, file_name, project
                FROM _schema_metadata 
                WHERE is_current = TRUE
            """)
            
            for table_name, file_name, proj in meta_result:
                # Only include if file is in registry
                if file_name and file_name.lower() in valid_files:
                    # Apply project filter if specified
                    if project:
                        if proj and project.lower() in proj.lower():
                            tables_to_check.append(table_name)
                    else:
                        tables_to_check.append(table_name)
            
            # Also check _pdf_tables
            try:
                table_check = handler.safe_fetchone("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_name = '_pdf_tables'
                """)
                
                if table_check and table_check[0] > 0:
                    pdf_result = handler.safe_fetchall("""
                        SELECT DISTINCT table_name, source_file, project
                        FROM _pdf_tables
                    """)
                    
                    for table_name, source_file, proj in pdf_result:
                        if source_file and source_file.lower() in valid_files:
                            if project:
                                if proj and project.lower() in proj.lower():
                                    if table_name not in tables_to_check:
                                        tables_to_check.append(table_name)
                            else:
                                if table_name not in tables_to_check:
                                    tables_to_check.append(table_name)
            except:
                pass
                
            logger.info(f"[INTEGRITY] Found {len(tables_to_check)} tables for registered files")
            
        except Exception as meta_e:
            logger.warning(f"[INTEGRITY] Metadata query failed: {meta_e}")
            return {"error": str(meta_e), "tables": [], "total_rows": 0, "health_score": 0, "issues_count": 0}
        
        # =================================================================
        # STEP 3: Analyze each table with INSIGHT vs ISSUE classification
        # =================================================================
        
        # Patterns that are ACTUALLY bad (parsing failures)
        parsing_failure_patterns = [
            'nan', 'none', 'null', 'unnamed',
            'column0', 'column1', 'column2', 'column_0', 'column_1',
            'field0', 'field1', 'field_0', 'field_1',
            'var0', 'var1', 'var_0', 'var_1',
        ]
        
        # Patterns that are INSIGHTS (optional fields - not issues)
        optional_field_patterns = [
            r'orgud?field\d+',      # orgudfield1-10, orgufield1-10
            r'udf\d+',              # udf1, udf2, etc.
            r'custom_?\d+',         # custom1, custom_field_2
            r'report_category',     # report_category_code, report_category
            r'user_defined',        # user_defined_*
            r'flex_?\d*',           # flex1, flex_field
            r'attribute_?\d*',      # attribute1, attribute_field
        ]
        
        total_insights = 0
        all_insights = []
        
        for table_name in tables_to_check:
            table_issues = []
            table_insights = []
            
            # Get columns for this table
            try:
                cols_result = handler.safe_fetchall(f"""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = '{table_name}'
                """)
            except Exception as col_e:
                logger.warning(f"Failed to get columns for {table_name}: {col_e}")
                continue
            
            column_names = [c[0] for c in cols_result]
            
            # Skip if table doesn't actually exist (stale metadata)
            if not column_names:
                logger.warning(f"Skipping {table_name} - no columns found (stale metadata?)")
                continue
            
            # Get row count
            try:
                row_count = handler.safe_fetchone(f'SELECT COUNT(*) FROM "{table_name}"')[0]
            except Exception as count_e:
                logger.warning(f"Skipping {table_name} - table doesn't exist: {count_e}")
                continue
            
            total_rows += row_count
            
            # Analyze each column
            for col in column_names:
                col_lower = col.lower().strip()
                
                # Check if it's an optional field pattern (INSIGHT, not issue)
                is_optional = any(re.search(pattern, col_lower) for pattern in optional_field_patterns)
                
                if is_optional:
                    # It's an insight - track it but don't penalize
                    # We could get fill rate here for richer insights, but skip for now
                    table_insights.append({
                        "column": col,
                        "type": "optional_field",
                        "message": f"Optional field: {col}"
                    })
                    continue
                
                # Check for actual parsing failures
                is_parsing_failure = any(pattern in col_lower for pattern in parsing_failure_patterns)
                is_purely_numeric = col_lower.replace('.', '').replace('_', '').replace('-', '').isdigit()
                is_single_char_junk = len(col_lower) == 1 and (col_lower.isdigit() or col_lower in 'abcdefghij')
                is_numeric_with_underscore = col_lower.replace('_', '').isdigit() and '_' in col_lower
                
                # col_X patterns - check if they're junk vs intentional
                is_col_pattern = re.match(r'^col_\d+$', col_lower)
                
                if is_parsing_failure or is_purely_numeric or is_single_char_junk or is_numeric_with_underscore:
                    table_issues.append({
                        "column": col,
                        "type": "bad_column_name",
                        "severity": "high",
                        "message": f"Suspicious column: {col}"
                    })
                elif is_col_pattern:
                    # col_X could be junk OR intentional - flag as warning not error
                    table_issues.append({
                        "column": col,
                        "type": "possible_junk",
                        "severity": "medium",
                        "message": f"Possible parsing artifact: {col}"
                    })
            
            # Check first few column names for header detection issues
            if len(column_names) >= 3:
                first_three = column_names[:3]
                numeric_count = sum(1 for c in first_three if c.lower().replace('_', '').replace('.', '').replace('-', '').isdigit())
                if numeric_count >= 2:
                    table_issues.append({
                        "type": "header_detection",
                        "severity": "high",
                        "message": "Possible header row issue - first columns look numeric"
                    })
            
            # Calculate fill rate
            fill_rate = 100
            if row_count > 0 and column_names:
                try:
                    first_col = column_names[0]
                    null_count = handler.safe_fetchone(f'''
                        SELECT COUNT(*) FROM "{table_name}" WHERE "{first_col}" IS NULL
                    ''')[0]
                    fill_rate = round(((row_count - null_count) / row_count) * 100)
                except:
                    pass
            
            total_issues += len(table_issues)
            total_insights += len(table_insights)
            
            if table_insights:
                all_insights.append({
                    "table_name": table_name,
                    "insights": table_insights
                })
            
            all_tables.append({
                "table_name": table_name,
                "column_count": len(column_names),
                "row_count": row_count,
                "fill_rate": fill_rate,
                "issues": table_issues,
                "insights": table_insights,
                "status": "unhealthy" if table_issues else "healthy"
            })
        
        # Calculate health score
        if all_tables:
            healthy_tables = sum(1 for t in all_tables if t["status"] == "healthy")
            health_score = round((healthy_tables / len(all_tables)) * 100)
        else:
            health_score = 100
        
        overall_status = "healthy" if health_score >= 80 else ("degraded" if health_score >= 50 else "unhealthy")
        
        logger.info(f"[INTEGRITY] Checked {len(all_tables)} tables, health_score={health_score}%, total_rows={total_rows}, issues={total_issues}, insights={total_insights}")
        
        return {
            "status": overall_status,
            "tables": all_tables,
            "total_rows": total_rows,
            "health_score": health_score,
            "issues_count": total_issues,
            "insights_count": total_insights,
            "insights": all_insights
        }
        
    except Exception as e:
        logger.error(f"Data integrity check failed: {e}")
        return {"error": str(e), "tables": [], "total_rows": 0, "health_score": 0, "issues_count": 0, "insights_count": 0}
