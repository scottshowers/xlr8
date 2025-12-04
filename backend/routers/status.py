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
        
        tables = []
        try:
            # First try to get data from metadata table (has timestamps) - EXCEL FILES
            try:
                metadata_result = handler.conn.execute("""
                    SELECT table_name, project, file_name, sheet_name, columns, row_count, created_at
                    FROM _schema_metadata 
                    WHERE is_current = TRUE
                """).fetchall()
                
                for row in metadata_result:
                    table_name, proj, filename, sheet, columns_json, row_count, created_at = row
                    
                    if project and proj.lower() != project.lower():
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
            
            # ALSO query _pdf_tables for PDF-derived tables
            try:
                # First check if table exists
                table_check = handler.conn.execute("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_name = '_pdf_tables'
                """).fetchone()
                logger.warning(f"[STATUS] _pdf_tables exists: {table_check[0] > 0}")
                
                if table_check[0] > 0:
                    pdf_result = handler.conn.execute("""
                        SELECT table_name, source_file, project, project_id, row_count, columns, created_at
                        FROM _pdf_tables
                    """).fetchall()
                    logger.warning(f"[STATUS] _pdf_tables has {len(pdf_result)} rows")
                else:
                    pdf_result = []
                    logger.warning("[STATUS] _pdf_tables does not exist yet")
                
                pdf_count = 0
                for row in pdf_result:
                    table_name, source_file, proj, project_id, row_count, columns_json, created_at = row
                    
                    if project and proj and proj.lower() != project.lower():
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
            
            # Fallback to information_schema if no metadata
            if not tables:
                logger.warning("No metadata found, falling back to information_schema")
                
                table_result = handler.conn.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'main'
                    AND table_name NOT LIKE '_%'
                """).fetchall()
                
                for (table_name,) in table_result:
                    try:
                        count_result = handler.conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()
                        row_count = count_result[0] if count_result else 0
                        
                        col_result = handler.conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
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


@router.delete("/status/structured/{project}/{filename}")
async def delete_structured_file(project: str, filename: str):
    """Delete a structured data file from DuckDB"""
    logger.warning(f"[DELETE] Request to delete project={project}, filename={filename}")
    
    if not STRUCTURED_AVAILABLE:
        raise HTTPException(status_code=503, detail="Structured data not available")
    
    try:
        handler = get_structured_handler()
        result = handler.delete_file(project, filename)
        logger.warning(f"[DELETE] Result: {result}")
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
        jobs = ProcessingJobModel.get_all(limit=limit)
        
        if status:
            jobs = [j for j in jobs if j.get("status") == status]
        
        return {"jobs": jobs, "total": len(jobs)}
    except Exception as e:
        logger.error(f"Failed to get processing jobs: {e}")
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
    Get all documents with chunk counts.
    Combines Supabase document metadata with ChromaDB chunk counts.
    """
    try:
        # Step 1: Get documents from Supabase
        supabase_docs = DocumentModel.get_all(limit=limit)
        
        # Step 2: Get chunk counts from ChromaDB
        chunk_counts = {}
        try:
            rag = RAGHandler()
            collection = rag.client.get_or_create_collection(name="documents")
            
            if collection.count() > 0:
                results = collection.get(include=["metadatas"], limit=10000)
                
                for metadata in results.get("metadatas", []):
                    # Try multiple fields for filename
                    filename = (
                        metadata.get("filename") or 
                        metadata.get("source") or 
                        metadata.get("name") or 
                        "unknown"
                    )
                    if filename not in chunk_counts:
                        chunk_counts[filename] = {
                            "chunks": 0,
                            "project": metadata.get("project", "unknown"),
                            "functional_area": metadata.get("functional_area", ""),
                            "upload_date": metadata.get("upload_date", "")
                        }
                    chunk_counts[filename]["chunks"] += 1
        except Exception as chroma_e:
            logger.warning(f"ChromaDB query failed: {chroma_e}")
        
        # Step 3: Build merged document list
        documents = []
        seen_filenames = set()
        
        # First, add documents from Supabase (authoritative source)
        for doc in supabase_docs:
            filename = doc.get("name", "unknown")
            metadata = doc.get("metadata", {})
            
            # Get chunk count from ChromaDB if available
            chroma_data = chunk_counts.get(filename, {})
            
            doc_entry = {
                "id": doc.get("id"),
                "filename": filename,
                "file_type": doc.get("file_type", ""),
                "file_size": doc.get("file_size"),
                "project": metadata.get("project") or doc.get("project_id", "unknown"),
                "project_id": doc.get("project_id"),
                "functional_area": metadata.get("functional_area", ""),
                "upload_date": metadata.get("upload_date") or doc.get("created_at", ""),
                "chunks": chroma_data.get("chunks", 0),
                "category": doc.get("category", ""),
            }
            
            documents.append(doc_entry)
            seen_filenames.add(filename)
        
        # Then add any ChromaDB-only documents (not in Supabase)
        for filename, data in chunk_counts.items():
            if filename not in seen_filenames and filename != "unknown":
                documents.append({
                    "id": None,
                    "filename": filename,
                    "file_type": filename.split(".")[-1] if "." in filename else "",
                    "file_size": None,
                    "project": data.get("project", "unknown"),
                    "project_id": None,
                    "functional_area": data.get("functional_area", ""),
                    "upload_date": data.get("upload_date", ""),
                    "chunks": data.get("chunks", 0),
                    "category": "",
                })
        
        # Filter by project if specified
        if project:
            if project == "__GLOBAL__" or project == "GLOBAL":
                documents = [d for d in documents if d["project"] in ("__GLOBAL__", "GLOBAL", "Global/Universal")]
            else:
                documents = [d for d in documents if d["project"] == project or d["project_id"] == project]
        
        # Sort by upload date (newest first)
        documents.sort(key=lambda x: x.get("upload_date", "") or "", reverse=True)
        
        total_chunks = sum(d.get("chunks", 0) for d in documents)
        
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
        
        return {"success": True, "message": f"Document deleted"}
            
    except Exception as e:
        logger.error(f"Failed to delete document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/status/documents/reset")
async def reset_all_documents():
    """Reset all documents (ChromaDB and database)"""
    try:
        # Reset ChromaDB
        try:
            rag = RAGHandler()
            collection = rag.client.get_or_create_collection(name="documents")
            all_ids = collection.get()['ids']
            if all_ids:
                collection.delete(ids=all_ids)
            logger.warning(f"⚠️ Deleted {len(all_ids)} chunks from ChromaDB")
        except Exception as ce:
            logger.error(f"ChromaDB reset error: {ce}")
        
        # Reset database documents
        count = DocumentModel.delete_all()
        logger.warning(f"⚠️ Deleted {count} documents from database")
        
        return {"success": True, "message": f"Reset complete: {count} documents deleted"}
    except Exception as e:
        logger.error(f"Failed to reset documents: {e}")
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
