"""XLR8 FastAPI Backend"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import sys
import logging

sys.path.insert(0, '/app')
sys.path.insert(0, '/data')

from backend.routers import chat, upload, status, projects
from backend.websocket_manager import ws_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="XLR8", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api")
app.include_router(upload.router, prefix="/api")
app.include_router(status.router, prefix="/api")
app.include_router(projects.router, prefix="/api")

@app.websocket("/ws/jobs")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

@app.get("/api/health")
async def health():
    from utils.rag_handler import RAGHandler
    from utils.database.supabase_client import get_supabase_client
    
    try:
        rag = RAGHandler()
        stats = rag.get_stats()
        supabase = get_supabase_client()
        
        return {
            "status": "healthy",
            "chromadb": stats,
            "supabase": "connected"
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

# Serve React static files
frontend_path = Path("/app/frontend/dist")
if frontend_path.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_path / "assets")), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("ws/"):
            return {"error": "Not found"}
        file_path = frontend_path / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_path / "index.html")
