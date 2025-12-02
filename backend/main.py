from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import sys
import logging

sys.path.insert(0, '/app')
sys.path.insert(0, '/data')

from backend.routers import chat, upload, status, projects, jobs

# Import vacuum router
try:
    from backend.routers import vacuum
    VACUUM_AVAILABLE = True
except ImportError:
    VACUUM_AVAILABLE = False

# Import playbooks router
try:
    from backend.routers import playbooks
    PLAYBOOKS_AVAILABLE = True
except Exception as e:
    PLAYBOOKS_AVAILABLE = False
    import traceback
    print(f"ERROR: Playbooks router import failed: {e}")
    print(traceback.format_exc())

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="XLR8", version="2.0")

# CORS Configuration - Fixed for Vercel
# NOTE: allow_credentials=True requires explicit origins (no "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://xlr8-six.vercel.app",                           # Production Vercel
        "https://xlr8-git-main-scott-showers-projects.vercel.app", # Vercel preview
        "http://localhost:5173",                                  # Vite dev server
        "http://localhost:3000",                                  # Alternative dev server
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Register routers
app.include_router(chat.router, prefix="/api")
app.include_router(upload.router, prefix="/api")
app.include_router(status.router, prefix="/api")
app.include_router(projects.router, prefix="/api/projects")
app.include_router(jobs.router, prefix="/api")

# Register vacuum router if available
if VACUUM_AVAILABLE:
    app.include_router(vacuum.router, prefix="/api", tags=["vacuum"])
    logger.info("Vacuum router registered")
else:
    logger.warning("Vacuum router not available")

# Register playbooks router if available
if PLAYBOOKS_AVAILABLE:
    app.include_router(playbooks.router, prefix="/api")  # Frontend expects /api/playbooks/...
    logger.info("Playbooks router registered at /api/playbooks")
else:
    logger.warning("Playbooks router not available")

@app.get("/api/health")
async def health():
    try:
        from utils.rag_handler import RAGHandler
        rag = RAGHandler()
        
        return {
            "status": "healthy",
            "chromadb": "connected",
            "vacuum_available": VACUUM_AVAILABLE,
            "playbooks_available": PLAYBOOKS_AVAILABLE
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

# Serve frontend
frontend_path = Path("/app/frontend/dist")
if frontend_path.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_path / "assets")), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        if full_path.startswith("api/"):
            return {"error": "Not found"}
        file_path = frontend_path / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_path / "index.html")
