from fastapi import APIRouter, HTTPException
from typing import Optional
import sys
import logging

sys.path.insert(0, '/app')
sys.path.insert(0, '/data')

from utils.rag_handler import RAGHandler
from utils.database.models import ProcessingJobModel, DocumentModel

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


@router.get("/status/documents")
async def get_documents(project: Optional[str] = None, limit: int = 1000):
    """
    Get all documents, optionally filtered by project
    Uses ChromaDB for now - can be optimized to use DocumentModel later
    """
    try:
        rag = RAGHandler()
        collection = rag.client.get_collection(name="documents")
        
        # Get documents with limit to prevent slowness
        results = collection.get(
            include=["metadatas"],
            limit=limit
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
        if project and project != "__GLOBAL__":
            doc_list = [d for d in doc_list if d["project"] == project]
        elif project == "__GLOBAL__":
            doc_list = [d for d in doc_list if d["project"] == "__GLOBAL__"]
        
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


@router.get("/status/system")
async def get_system_status():
    """Get overall system health"""
    try:
        # Get ChromaDB stats
        chromadb_stats = await get_chromadb_stats()
        
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
            "jobs": {
                "recent": len(recent_jobs),
                "counts": job_counts
            },
            "status": "operational"
        }
    except Exception as e:
        logger.error(f"System status check failed: {e}")
        return {"status": "degraded", "error": str(e)}
