from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
import sys
import uuid
import os

sys.path.insert(0, '/app')
sys.path.insert(0, '/data')

from utils.rag_handler import RAGHandler

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
        
        rag = RAGHandler()
        result = rag.add_document(
            file_path=file_path,
            metadata={
                "project": project,
                "functional_area": functional_area,
                "filename": file.filename
            }
        )
        
        return {
            "job_id": job_id,
            "status": "completed",
            "chunks": result.get("chunks_added", 0) if isinstance(result, dict) else 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
