from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
import sys
import os
import PyPDF2
import docx
import pandas as pd

sys.path.insert(0, '/app')
sys.path.insert(0, '/data')

from utils.rag_handler import RAGHandler
from utils.database.models import ProcessingJobModel, DocumentModel

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
    file_path = None
    
    try:
        # Create processing job in database
        job = ProcessingJobModel.create(
            job_type='file_upload',
            project_id=project,
            filename=file.filename,
            input_data={'filename': file.filename, 'functional_area': functional_area}
        )
        
        if not job:
            raise HTTPException(status_code=500, detail="Failed to create processing job")
        
        job_id = job['id']
        
        # Save file
        ProcessingJobModel.update_progress(job_id, 10, "Saving file...")
        os.makedirs("/data/uploads", exist_ok=True)
        file_path = f"/data/uploads/{job_id}_{file.filename}"
        
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Extract text
        ProcessingJobModel.update_progress(job_id, 30, "Extracting text...")
        text = extract_text(file_path)
        
        if not text:
            ProcessingJobModel.fail(job_id, "No text could be extracted from file")
            raise HTTPException(status_code=400, detail="No text extracted")
        
        # Prepare metadata
        ProcessingJobModel.update_progress(job_id, 50, "Preparing metadata...")
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
        ProcessingJobModel.update_progress(job_id, 70, "Creating embeddings...")
        rag = RAGHandler()
        success = rag.add_document(
            collection_name="documents",
            text=text,
            metadata=metadata
        )
        
        if not success:
            ProcessingJobModel.fail(job_id, "Failed to add document to vector store")
            raise HTTPException(status_code=500, detail="Failed to process document")
        
        # Save to documents table
        ProcessingJobModel.update_progress(job_id, 90, "Saving to database...")
        DocumentModel.create(
            project_id=project,
            name=file.filename,
            category=functional_area or 'General',
            file_type=file_ext,
            file_size=len(content),
            content=text[:5000],  # Store first 5000 chars
            metadata=metadata
        )
        
        # Cleanup
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        
        # Complete job
        ProcessingJobModel.complete(job_id, {
            'filename': file.filename,
            'chunks_created': 'processed',
            'project': project
        })
        
        return {
            "job_id": job_id,
            "status": "completed",
            "message": f"File {file.filename} uploaded successfully"
        }
        
    except HTTPException:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        raise
        
    except Exception as e:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        if 'job_id' in locals():
            ProcessingJobModel.fail(job_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))
