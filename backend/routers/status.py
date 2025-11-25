from fastapi import APIRouter, HTTPException
from typing import Optional
import sys
import logging

sys.path.insert(0, '/app')
sys.path.insert(0, '/data')

from utils.rag_handler import RAGHandler
from utils.database.models import ProcessingJobModel, DocumentModel

# Import structured data handler
try:
    from utils.structured_data_handler import get_structured_handler
    STRUCTURED_AVAILABLE = True
except ImportError:
    STRUCTURED_AVAILABLE = False

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/status/chromadb")
async def get_chromadb_stats():
    """Get ChromaDB statistics"""
    try:
        rag = RAGHandler()
        collection = rag.client.get_collection(name="documents")
        count = collection.count()
        return {"total_chunks": count}
    except Exception as e:
        logger.error(f"ChromaDB stats error: {e}")
        return {"total_chunks": 0, "error": str(e)}


# ============================================================================
# STRUCTURED DATA ENDPOINTS (DuckDB)
# ============================================================================

@router.get("/status/structured")
async def get_structured_data_status(project: Optional[str] = None):
    """
    Get all structured data tables (Excel/CSV files stored in DuckDB)
    
    Returns list of files with their sheets/tables and row counts.
    """
    if not STRUCTURED_AVAILABLE:
        return {
            "available": False,
            "files": [],
            "total_files": 0,
            "total_tables": 0,
            "total_rows": 0,
            "message": "Structured data handler not available"
        }
    
    try:
        handler = get_structured_handler()
        
        # Query metadata for all files
        if project and project not in ['all', 'All Projects', '']:
            result = handler.conn.execute("""
                SELECT project, file_name, sheet_name, table_name, row_count, 
                       columns, encrypted_columns, version, created_at
                FROM _schema_metadata
                WHERE project = ? AND is_current = TRUE
                ORDER BY project, file_name, sheet_name
            """, [project]).fetchall()
        else:
            result = handler.conn.execute("""
                SELECT project, file_name, sheet_name, table_name, row_count,
                       columns, encrypted_columns, version, created_at
                FROM _schema_metadata
                WHERE is_current = TRUE
                ORDER BY project, file_name, sheet_name
            """).fetchall()
        
        # Group by file
        files = {}
        for row in result:
            project_name, file_name, sheet_name, table_name, row_count, columns, encrypted_cols, version, created_at = row
            
            file_key = f"{project_name}::{file_name}"
            if file_key not in files:
                files[file_key] = {
                    "filename": file_name,
                    "project": project_name,
                    "version": version,
                    "created_at": str(created_at) if created_at else None,
                    "sheets": [],
                    "total_rows": 0,
                    "has_encrypted": False
                }
            
            # Parse columns and encrypted columns
            import json
            try:
                cols = json.loads(columns) if columns else []
                enc_cols = json.loads(encrypted_cols) if encrypted_cols else []
            except:
                cols = []
                enc_cols = []
            
            files[file_key]["sheets"].append({
                "sheet_name": sheet_name,
                "table_name": table_name,
                "row_count": row_count or 0,
                "column_count": len(cols),
                "encrypted_columns": enc_cols
            })
            files[file_key]["total_rows"] += row_count or 0
            if enc_cols:
                files[file_key]["has_encrypted"] = True
        
        file_list = list(files.values())
        total_tables = sum(len(f["sheets"]) for f in file_list)
        total_rows = sum(f["total_rows"] for f in file_list)
        
        return {
            "available": True,
            "files": file_list,
            "total_files": len(file_list),
            "total_tables": total_tables,
            "total_rows": total_rows
        }
        
    except Exception as e:
        logger.error(f"Structured data status error: {e}")
        return {
            "available": True,
            "files": [],
            "total_files": 0,
            "total_tables": 0,
            "total_rows": 0,
            "error": str(e)
        }


@router.delete("/status/structured/{project}/{filename:path}")
async def delete_structured_file(project: str, filename: str, all_versions: bool = True):
    """
    Delete a structured data file from DuckDB.
    
    Use this to refresh data - delete then re-upload.
    """
    if not STRUCTURED_AVAILABLE:
        raise HTTPException(501, "Structured data handler not available")
    
    try:
        handler = get_structured_handler()
        result = handler.delete_file(project, filename, delete_all_versions=all_versions)
        
        logger.info(f"Deleted structured data: {project}/{filename} - {len(result['tables_deleted'])} tables")
        
        return {
            "success": True,
            "project": project,
            "filename": filename,
            "tables_deleted": result['tables_deleted'],
            "message": f"Deleted {len(result['tables_deleted'])} tables"
        }
    except Exception as e:
        logger.error(f"Failed to delete structured file: {e}")
        raise HTTPException(500, str(e))


@router.post("/status/structured/reset")
async def reset_structured_data():
    """Reset all structured data (WARNING: Deletes all DuckDB tables!)"""
    if not STRUCTURED_AVAILABLE:
        raise HTTPException(501, "Structured data handler not available")
    
    try:
        handler = get_structured_handler()
        
        # Get all tables
        tables = handler.conn.execute("""
            SELECT table_name FROM _schema_metadata
        """).fetchall()
        
        # Drop all data tables
        count = 0
        for (table_name,) in tables:
            try:
                handler.conn.execute(f"DROP TABLE IF EXISTS {table_name}")
                count += 1
            except:
                pass
        
        # Clear metadata
        handler.conn.execute("DELETE FROM _schema_metadata")
        handler.conn.execute("DELETE FROM _load_versions")
        handler.conn.commit()
        
        logger.warning(f"⚠️ Structured data RESET - {count} tables deleted!")
        
        return {
            "status": "reset_complete",
            "tables_deleted": count,
            "message": "All structured data deleted from DuckDB"
        }
    except Exception as e:
        logger.error(f"Failed to reset structured data: {e}")
        raise HTTPException(500, str(e))


# ============================================================================
# PROCESSING JOBS
# ============================================================================

@router.get("/jobs")
async def get_processing_jobs(limit: int = 50, status: Optional[str] = None):
    """Get processing jobs from database"""
    try:
        # Get jobs from database
        jobs = ProcessingJobModel.get_all(limit=limit)
        
        # Filter by status if specified
        if status:
            jobs = [j for j in jobs if j.get("status") == status]
        
        return {"jobs": jobs, "total": len(jobs)}
    except Exception as e:
        logger.error(f"Failed to get processing jobs: {e}")
        # Return empty list to prevent frontend crash
        return {"jobs": [], "total": 0, "error": str(e)}


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
        
        # Fail the job
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
    """Delete a processing job from history"""
    try:
        job = ProcessingJobModel.get_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Delete the job from Supabase
        from utils.database.supabase_client import get_supabase
        supabase = get_supabase()
        
        if not supabase:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        supabase.table('processing_jobs').delete().eq('id', job_id).execute()
        logger.info(f"Job {job_id} deleted by user")
        
        return {
            "success": True,
            "message": f"Job {job_id} deleted successfully",
            "job_id": job_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# DOCUMENTS (ChromaDB - PDFs, Word docs)
# ============================================================================

@router.get("/status/documents")
async def get_documents(project: Optional[str] = None, limit: int = 50000):
    """
    Get all documents, optionally filtered by project
    Uses ChromaDB for now - can be optimized to use DocumentModel later
    """
    try:
        rag = RAGHandler()
        collection = rag.client.get_collection(name="documents")
        
        # Get total count first
        total_chunks = collection.count()
        
        # Get documents - use total count as limit to ensure we get all
        results = collection.get(
            include=["metadatas"],
            limit=max(limit, total_chunks)  # Ensure we get ALL chunks
        )
        
        # Extract unique documents with metadata
        documents = {}
        for metadata in results["metadatas"]:
            filename = metadata.get("filename") or metadata.get("source", "unknown")
            if filename not in documents:
                documents[filename] = {
                    "filename": filename,
                    "project": metadata.get("project", "unknown"),
                    "functional_area": metadata.get("functional_area", ""),
                    "upload_date": metadata.get("upload_date", ""),
                    "chunks": 0
                }
            documents[filename]["chunks"] += 1
        
        # Filter by project if specified
        doc_list = list(documents.values())
        if project and project != "all":
            doc_list = [d for d in doc_list if d["project"] == project]
        
        return {
            "documents": doc_list, 
            "total": len(doc_list),
            "total_chunks": sum(d["chunks"] for d in doc_list)
        }
    except Exception as e:
        logger.error(f"Failed to get documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/documents/db")
async def get_documents_from_db(project_id: Optional[str] = None):
    """
    Get documents from Supabase database (faster than ChromaDB)
    Alternative endpoint for testing
    """
    try:
        if project_id:
            documents = DocumentModel.get_by_project(project_id)
        else:
            # TODO: Add DocumentModel.get_all() if needed
            documents = []
            logger.warning("DocumentModel.get_all() not implemented - use project_id filter")
        
        return {
            "documents": documents,
            "total": len(documents),
            "source": "supabase"
        }
    except Exception as e:
        logger.error(f"Failed to get documents from DB: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/status/documents/{filename}")
async def delete_document(filename: str, project: Optional[str] = None):
    """Delete all chunks for a specific document from ChromaDB"""
    try:
        rag = RAGHandler()
        
        try:
            collection = rag.client.get_collection(name="documents")
        except:
            return {"deleted": 0, "filename": filename, "message": "Collection does not exist"}
        
        # Get all chunks
        results = collection.get(include=["metadatas"])
        
        # Find IDs to delete
        ids_to_delete = []
        for i, metadata in enumerate(results["metadatas"]):
            doc_name = metadata.get("filename") or metadata.get("source")
            if doc_name == filename:
                ids_to_delete.append(results["ids"][i])
        
        # Delete the chunks
        if ids_to_delete:
            collection.delete(ids=ids_to_delete)
            logger.info(f"Deleted {len(ids_to_delete)} chunks for {filename}")
        else:
            logger.warning(f"No chunks found for {filename}")
        
        return {
            "deleted": len(ids_to_delete), 
            "filename": filename, 
            "message": f"Deleted {len(ids_to_delete)} chunks from vector store"
        }
    except Exception as e:
        logger.error(f"Failed to delete document {filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/status/documents/db/{document_id}")
async def delete_document_by_id(document_id: str):
    """Delete document from Supabase database by ID"""
    try:
        success = DocumentModel.delete(document_id)
        if success:
            return {"success": True, "message": f"Document {document_id} deleted from database"}
        else:
            raise HTTPException(status_code=404, detail="Document not found")
    except Exception as e:
        logger.error(f"Failed to delete document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/status/chromadb/reset")
async def reset_chromadb():
    """Reset ChromaDB collection (WARNING: Deletes all data!)"""
    try:
        rag = RAGHandler()
        rag.client.delete_collection(name="documents")
        logger.warning("⚠️ ChromaDB collection 'documents' was RESET - all data deleted!")
        return {"status": "reset_complete", "message": "All documents deleted from vector store"}
    except Exception as e:
        logger.error(f"Failed to reset ChromaDB: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SYSTEM STATUS
# ============================================================================

@router.get("/status/system")
async def get_system_status():
    """Get overall system health including structured data"""
    try:
        # Get ChromaDB stats
        chromadb_stats = await get_chromadb_stats()
        
        # Get structured data stats
        structured_stats = await get_structured_data_status()
        
        # Get recent jobs
        jobs_response = await get_processing_jobs(limit=10)
        recent_jobs = jobs_response.get("jobs", [])
        
        # Count job statuses
        job_counts = {
            "processing": sum(1 for j in recent_jobs if j.get("status") == "processing"),
            "completed": sum(1 for j in recent_jobs if j.get("status") == "completed"),
            "failed": sum(1 for j in recent_jobs if j.get("status") == "failed"),
            "queued": sum(1 for j in recent_jobs if j.get("status") == "queued")
        }
        
        return {
            "chromadb": chromadb_stats,
            "structured_data": {
                "available": structured_stats.get("available", False),
                "total_files": structured_stats.get("total_files", 0),
                "total_tables": structured_stats.get("total_tables", 0),
                "total_rows": structured_stats.get("total_rows", 0)
            },
            "jobs": {
                "recent": len(recent_jobs),
                "counts": job_counts
            },
            "status": "operational"
        }
    except Exception as e:
        logger.error(f"System status check failed: {e}")
        return {"status": "degraded", "error": str(e)}
