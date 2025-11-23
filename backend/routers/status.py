from fastapi import APIRouter, HTTPException
from typing import Optional
import sys

sys.path.insert(0, '/app')
sys.path.insert(0, '/data')

from utils.rag_handler import RAGHandler

router = APIRouter()

@router.get("/status/chromadb")
async def get_chromadb_stats():
    try:
        rag = RAGHandler()
        collection = rag.client.get_collection(name="documents")
        count = collection.count()
        return {"total_chunks": count}
    except Exception as e:
        return {"total_chunks": 0, "error": str(e)}

@router.get("/status/documents")
async def get_documents(project: Optional[str] = None):
    """Get all documents, optionally filtered by project"""
    try:
        rag = RAGHandler()
        collection = rag.client.get_collection(name="documents")
        
        # Get all documents
        results = collection.get(include=["metadatas"])
        
        # Extract unique documents with metadata
        documents = {}
        for metadata in results["metadatas"]:
            filename = metadata.get("filename", "unknown")
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
        
        return {"documents": doc_list, "total": len(doc_list)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/status/chromadb/reset")
async def reset_chromadb():
    try:
        rag = RAGHandler()
        rag.client.delete_collection(name="documents")
        return {"status": "reset_complete"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
