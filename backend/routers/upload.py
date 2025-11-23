from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
import sys
import uuid
import os
import PyPDF2
import docx
import pandas as pd

sys.path.insert(0, '/app')
sys.path.insert(0, '/data')

from utils.rag_handler import RAGHandler
from backend.routers.jobs import create_job, update_job, complete_job, fail_job

router = APIRouter()

def extract_text(file_path: str) -> str:
    """Extract text from file"""
    ext = file_path.split('.')[-1].lower()
    
    try:
        if ext == 'pdf':
            with open(file_path, 'rb') as f:
                pdf = PyPDF2.PdfReader(f)
                return "\n".join([p.extract_text() for p in pdf.pages])
        elif ext == 'docx':
            doc = docx.Document(file_path)
            return "\n".join([p.text for p in doc.paragraphs])
        elif ext in ['xlsx', 'xls']:
            excel = pd.ExcelFile(file_path)
            texts = []
            for sheet in excel.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet)
                texts.append(f"=== {sheet} ===\n{df.to_string()}")
            return "\n\n".join(texts)
        elif ext in ['txt', 'md']:
            with open(file_path, 'r') as f:
                return f.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Text extraction failed: {str(e)}")
    
    return ""

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    project: str = Form(...),
    functional_area: Optional[str] = Form(None)
):
    job_id = str(uuid.uuid4())
    file_path = None
    
    try:
        # Create job
        create_job(job_id, file.filename, project)
        
        # Save file
        update_job(job_id, status="processing", progress=10, current_step="Saving file...")
        os.makedirs("/data/uploads", exist_ok=True)
        file_path = f"/data/uploads/{job_id}_{file.filename}"
        
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Extract text
        update_job(job_id, progress=30, current_step="Extracting text...")
        text = extract_text(file_path)
        
        if not text:
            fail_job(job_id, "No text could be extracted from file")
            raise HTTPException(status_code=400, detail="No text extracted")
        
        # Prepare metadata
        update_job(job_id, progress=50, current_step="Preparing metadata...")
        file_ext = file.filename.split('.')[-1].lower()
        
        metadata = {
            "project": project,
            "filename": file.filename,
            "file_type": file_ext,
            "source": file.filename
        }
        
        if functional_area:
            metadata["functional_area"] = functional_area
        
        # Add to vector store
        update_job(job_id, progress=70, current_step="Creating embeddings...")
        rag = RAGHandler()
        success = rag.add_document(
            collection_name="documents",
            text=text,
            metadata=metadata
        )
        
        if not success:
            fail_job(job_id, "Failed to add document to vector store")
            raise HTTPException(status_code=500, detail="Failed to process document")
        
        # Cleanup
        update_job(job_id, progress=90, current_step="Finalizing...")
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        
        # Complete
        complete_job(job_id, f"Successfully processed {file.filename}")
        
        return {
            "job_id": job_id,
            "status": "completed",
            "message": f"File {file.filename} uploaded successfully"
        }
        
    except HTTPException:
        # Cleanup on error
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        raise
        
    except Exception as e:
        # Cleanup on error
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        fail_job(job_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))
