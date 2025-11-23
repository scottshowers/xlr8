from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
import sys
import uuid
import os

sys.path.insert(0, '/app')
sys.path.insert(0, '/data')

from utils.rag_handler import RAGHandler
from utils.document_processor import DocumentProcessor

router = APIRouter()

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    project: str = Form(...),
    functional_area: Optional[str] = Form(None)
):
    try:
        job_id = str(uuid.uuid4())
        
        os.makedirs("/data/uploads", exist_ok=True)
        file_path = f"/data/uploads/{job_id}_{file.filename}"
        
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Process document to extract text
        processor = DocumentProcessor()
        text = processor.process_file(file_path)
        
        if not text:
            raise HTTPException(status_code=400, detail="Could not extract text from file")
        
        # Get file extension
        file_ext = file.filename.split('.')[-1].lower()
        
        # Add to RAG
        rag = RAGHandler()
        success = rag.add_document(
            collection_name="documents",
            text=text,
            metadata={
                "project_id": project,
                "functional_area": functional_area,
                "filename": file.filename,
                "file_type": file_ext,
                "source": file.filename
            }
        )
        
        # Clean up temp file
        os.remove(file_path)
        
        return {
            "job_id": job_id,
            "status": "completed" if success else "failed",
            "chunks": "unknown"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
