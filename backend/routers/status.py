from fastapi import APIRouter, HTTPException
from typing import Optional
import sys
import logging
import json

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


# ==================== STRUCTURED DATA STATUS ====================

@router.get("/status/structured")
async def get_structured_data_status(project: Optional[str] = None):
    """Get structured data (DuckDB) statistics"""
    if not STRUCTURED_AVAILABLE:
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
        
        # Query DuckDB directly for ALL tables - more reliable than get_schema_for_project
        tables = []
        try:
            # First try to get data from metadata table (has timestamps)
            try:
                metadata_result = handler.conn.execute("""
                    SELECT table_name, project, file_name, sheet_name, columns, row_count, created_at
                    FROM _schema_metadata 
                    WHERE is_current = TRUE
                """).fetchall()
                
                for row in metadata_result:
                    table_name, proj, filename, sheet, columns_json, row_count, created_at = row
                    
                    # Apply project filter if specified
                    if project and proj.lower() != project.lower():
                        continue
                    
                    # Parse columns JSON
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
                        'loaded_at': str(created_at) if created_at else None
                    })
                
                logger.info(f"[STATUS] Got {len(tables)} tables from metadata")
                
            except Exception as meta_e:
                logger.warning(f"Metadata query failed, falling back to information_schema: {meta_e}")
                
                # Fallback: Get all table names from DuckDB information_schema
                table_result = handler.conn.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'main'
                """).fetchall()
                
                for (table_name,) in table_result:
                    try:
                        # Get row count
                        count_result = handler.conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()
                        row_count = count_result[0] if count_result else 0
                        
                        # Get column info
                        col_result = handler.conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
                        columns = [col[1] for col in col_result] if col_result else []
                        
                        # Parse table name to extract metadata
                        parts = table_name.split('__')
                        if len(parts) >= 3:
                            proj = parts[0]
                            filename = parts[1]
                            sheet = parts[2] if len(parts) > 2 else ''
                        else:
                            proj = 'default'
                            filename = table_name
                            sheet = ''
                        
                        # Apply project filter if specified
                        if project and proj.lower() != project.lower():
                            continue
                        
                        tables.append({
                            'table_name': table_name,
                            'project': proj,
                            'file': filename,
                            'sheet': sheet,
                            'columns': columns,
                            'row_count': row_count,
                            'loaded_at': None
                        })
                    except Exception as te:
                        logger.warning(f"Error getting info for table {table_name}: {te}")
                    
        except Exception as qe:
            logger.error(f"Error querying tables: {qe}")
            # Fallback to get_schema_for_project
            schema = handler.get_schema_for_project(project)
            tables = schema.get('tables', [])
        
        # Group by file
        files_dict = {}
        total_rows = 0
        
        for table in tables:
            file_name = table.get('file', 'Unknown')
            project_name = table.get('project', 'Unknown')
            
            key = f"{project_name}:{file_name}"
            if key not in files_dict:
                files_dict[key] = {
                    'filename': file_name,
                    'project': project_name,
                    'sheets': [],  # Frontend expects 'sheets' not 'tables'
                    'total_rows': 0,
                    'loaded_at': None
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
            
            # Track most recent loaded_at for the file
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


@router.delete("/status/structured/{project}/{filename}")
async def delete_structured_file(project: str, filename: str):
    """Delete a structured data file from DuckDB"""
    if not STRUCTURED_AVAILABLE:
        raise HTTPException(status_code=503, detail="Structured data not available")
    
    try:
        handler = get_structured_handler()
        result = handler.delete_file(project, filename)
        return {"success": True, "message": f"Deleted {filename}", "details": result}
    except Exception as e:
        logger.error(f"Failed to delete structured file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
    try:
        rag = RAGHandler()
        collection = rag.client.get_or_create_collection(name="documents")
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


@router.get("/status/documents")
async def get_documents(project: Optional[str] = None, limit: int = 1000):
    """
    Get all documents, optionally filtered by project
    Uses ChromaDB for now - can be optimized to use DocumentModel later
    """
    try:
        rag = RAGHandler()
        collection = rag.client.get_or_create_collection(name="documents")
        
        # Check if collection is empty
        if collection.count() == 0:
            return {
                "documents": [], 
                "total": 0,
                "total_chunks": 0
            }
        
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
        # Return empty instead of 500 error
        return {
            "documents": [], 
            "total": 0,
            "total_chunks": 0,
            "error": str(e)
        }


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
        # Add relationship to database
        handler.conn.execute("""
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
        handler.conn.execute("""
            DELETE FROM _table_relationships 
            WHERE project = ? AND source_table = ? AND target_table = ?
        """, [project, rel.source_table, rel.target_table])
        handler.conn.commit()
        
        return {"status": "deleted"}
    except Exception as e:
        logger.error(f"Failed to delete relationship: {e}")
        raise HTTPException(500, str(e))
