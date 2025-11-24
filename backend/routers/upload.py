"""
Async Upload Router for XLR8
============================

FEATURES:
- Returns immediately after file save (no timeout!)
- Processes in background thread
- Real-time status updates via job polling
- Handles large files gracefully

Author: XLR8 Team
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from typing import Optional
import sys
import os
import threading
import traceback
import PyPDF2
import docx
import pandas as pd
import logging

sys.path.insert(0, '/app')
sys.path.insert(0, '/data')

from utils.rag_handler import RAGHandler
from utils.database.models import ProcessingJobModel, DocumentModel, ProjectModel

logger = logging.getLogger(__name__)

router = APIRouter()


def extract_text(file_path: str) -> str:
    """Extract text from file based on extension"""
    ext = file_path.split('.')[-1].lower()
    
    try:
        if ext == 'pdf':
            with open(file_path, 'rb') as f:
                pdf = PyPDF2.PdfReader(f)
                return "\n".join([p.extract_text() or '' for p in pdf.pages])
        
        elif ext == 'docx':
            doc = docx.Document(file_path)
            return "\n".join([p.text for p in doc.paragraphs])
        
        elif ext in ['xlsx', 'xls']:
            excel = pd.ExcelFile(file_path)
            texts = []
            for sheet in excel.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet)
                # Format for enhanced chunker (WORKSHEET: marker)
                texts.append(f"WORKSHEET: {sheet}\n{'=' * 40}\n{df.to_string()}")
            return "\n\n".join(texts)
        
        elif ext == 'csv':
            df = pd.read_csv(file_path)
            return f"WORKSHEET: CSV Data\n{'=' * 40}\n{df.to_string()}"
        
        elif ext in ['txt', 'md']:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        
        else:
            # Try as text
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
                
    except Exception as e:
        logger.error(f"Text extraction failed for {file_path}: {e}")
        raise


def process_file_background(
    job_id: str,
    file_path: str,
    filename: str,
    project: str,
    project_id: Optional[str],
    functional_area: Optional[str],
    file_size: int
):
    """
    Background processing function - runs in separate thread
    
    This is where all the heavy lifting happens:
    1. Extract text
    2. Chunk document
    3. Create embeddings
    4. Store in ChromaDB
    5. Update job status throughout
    """
    try:
        logger.info(f"[BACKGROUND] Starting processing for job {job_id}")
        
        # Step 1: Extract text
        ProcessingJobModel.update_progress(job_id, 5, "Extracting text from file...")
        text = extract_text(file_path)
        
        if not text or len(text.strip()) < 10:
            ProcessingJobModel.fail(job_id, "No text could be extracted from file")
            return
        
        logger.info(f"[BACKGROUND] Extracted {len(text)} characters")
        ProcessingJobModel.update_progress(job_id, 15, f"Extracted {len(text):,} characters")
        
        # Step 2: Prepare metadata
        file_ext = filename.split('.')[-1].lower()
        
        metadata = {
            "project": project,
            "filename": filename,
            "file_type": file_ext,
            "source": filename
        }
        
        if project_id:
            metadata["project_id"] = project_id
        
        if functional_area:
            metadata["functional_area"] = functional_area
        
        # Step 3: Initialize RAG and process
        ProcessingJobModel.update_progress(job_id, 20, "Initializing document processor...")
        
        def update_progress(current: int, total: int, message: str):
            """Callback for RAG handler progress updates"""
            # Map RAG progress (0-100) to our range (20-90)
            overall_percent = 20 + int(current * 0.70)
            ProcessingJobModel.update_progress(job_id, overall_percent, message)
        
        rag = RAGHandler()
        
        ProcessingJobModel.update_progress(job_id, 25, "Chunking document...")
        
        success = rag.add_document(
            collection_name="documents",
            text=text,
            metadata=metadata,
            progress_callback=update_progress
        )
        
        if not success:
            ProcessingJobModel.fail(job_id, "Failed to add document to vector store")
            return
        
        # Step 4: Save to documents table (if we have project UUID)
        ProcessingJobModel.update_progress(job_id, 92, "Saving to database...")
        
        if project_id:
            try:
                DocumentModel.create(
                    project_id=project_id,
                    name=filename,
                    category=functional_area or 'General',
                    file_type=file_ext,
                    file_size=file_size,
                    content=text[:5000],
                    metadata=metadata
                )
                logger.info(f"[BACKGROUND] Saved document to database")
            except Exception as e:
                logger.warning(f"[BACKGROUND] Could not save to documents table: {e}")
        
        # Step 5: Cleanup
        ProcessingJobModel.update_progress(job_id, 96, "Cleaning up...")
        
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"[BACKGROUND] Cleaned up temp file")
            except Exception as e:
                logger.warning(f"[BACKGROUND] Could not delete temp file: {e}")
        
        # Step 6: Complete!
        ProcessingJobModel.complete(job_id, {
            'filename': filename,
            'characters': len(text),
            'project': project,
            'functional_area': functional_area
        })
        
        logger.info(f"[BACKGROUND] Job {job_id} completed successfully!")
        
    except Exception as e:
        logger.error(f"[BACKGROUND] Job {job_id} failed: {e}")
        logger.error(traceback.format_exc())
        
        ProcessingJobModel.fail(job_id, str(e))
        
        # Cleanup on failure
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    project: str = Form(...),
    functional_area: Optional[str] = Form(None)
):
    """
    Async upload endpoint - returns immediately, processes in background
    
    Flow:
    1. Save file to disk
    2. Create job record
    3. Start background thread
    4. Return job_id immediately
    5. Client polls /api/jobs/{job_id} for progress
    """
    file_path = None
    
    try:
        # Look up project UUID from project name
        project_id = None
        if project and project not in ['global', '__GLOBAL__', '']:
            projects = ProjectModel.get_all(status='active')
            matching_project = next((p for p in projects if p.get('name') == project), None)
            
            if matching_project:
                project_id = matching_project['id']
                logger.info(f"Found project UUID: {project_id}")
        
        # Create job record FIRST (so we have job_id)
        job = ProcessingJobModel.create(
            job_type='file_upload',
            project_id=project,
            filename=file.filename,
            input_data={
                'filename': file.filename,
                'functional_area': functional_area,
                'async': True
            }
        )
        
        if not job:
            raise HTTPException(status_code=500, detail="Failed to create processing job")
        
        job_id = job['id']
        logger.info(f"[ASYNC] Created job {job_id} for {file.filename}")
        
        # Save file to disk
        ProcessingJobModel.update_progress(job_id, 2, "Saving file...")
        
        os.makedirs("/data/uploads", exist_ok=True)
        file_path = f"/data/uploads/{job_id}_{file.filename}"
        
        content = await file.read()
        file_size = len(content)
        
        with open(file_path, "wb") as f:
            f.write(content)
        
        logger.info(f"[ASYNC] Saved {file_size:,} bytes to {file_path}")
        ProcessingJobModel.update_progress(job_id, 4, f"File saved ({file_size:,} bytes)")
        
        # Start background processing thread
        thread = threading.Thread(
            target=process_file_background,
            args=(job_id, file_path, file.filename, project, project_id, functional_area, file_size),
            daemon=True
        )
        thread.start()
        
        logger.info(f"[ASYNC] Started background thread for job {job_id}")
        
        # Return immediately!
        return {
            "job_id": job_id,
            "status": "processing",
            "message": f"File '{file.filename}' queued for processing. Check status page for progress.",
            "async": True
        }
        
    except HTTPException:
        raise
        
    except Exception as e:
        logger.error(f"[ASYNC] Upload failed: {e}")
        logger.error(traceback.format_exc())
        
        # Cleanup on failure
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        
        raise HTTPException(status_code=500, detail=str(e))
