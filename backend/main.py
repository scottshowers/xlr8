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

# Import progress router (SSE streaming)
try:
    from backend.routers import progress
    PROGRESS_AVAILABLE = True
except ImportError:
    PROGRESS_AVAILABLE = False

# Import security config router
try:
    from backend.utils.security_config import create_config_router
    SECURITY_AVAILABLE = True
except ImportError as e:
    SECURITY_AVAILABLE = False
    print(f"Security config not available: {e}")

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

# Register progress router if available (SSE streaming)
if PROGRESS_AVAILABLE:
    app.include_router(progress.router, prefix="/api", tags=["progress"])
    logger.info("Progress router registered (SSE streaming enabled)")
else:
    logger.warning("Progress router not available")

# Register security config router if available
if SECURITY_AVAILABLE:
    app.include_router(create_config_router(), tags=["security"])
    logger.info("Security config router registered at /api/security/config")
else:
    logger.warning("Security config router not available")

@app.get("/api/health")
async def health():
    try:
        from utils.rag_handler import RAGHandler
        rag = RAGHandler()
        
        return {
            "status": "healthy",
            "chromadb": "connected",
            "collection_count": len(rag.chroma_client.list_collections()),
            "version": "2.0-optimized",
            "features": {
                "vacuum": VACUUM_AVAILABLE,
                "playbooks": PLAYBOOKS_AVAILABLE,
                "progress_streaming": PROGRESS_AVAILABLE,
                "security": SECURITY_AVAILABLE,
            }
        }
    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e)
        }

# Debug route to check imports
@app.get("/api/debug/imports")
async def debug_imports():
    results = {}
    
    # Check smart_pdf_analyzer
    try:
        from backend.utils.smart_pdf_analyzer import process_pdf_intelligently
        results['smart_pdf_analyzer'] = 'OK'
    except Exception as e:
        results['smart_pdf_analyzer'] = f'ERROR: {e}'
    
    # Check progress router
    try:
        from backend.routers.progress import update_chunk_progress
        results['progress_streaming'] = 'OK'
    except Exception as e:
        results['progress_streaming'] = f'ERROR: {e}'
    
    # Check parallel processing
    try:
        from concurrent.futures import ThreadPoolExecutor
        results['parallel_processing'] = 'OK'
    except Exception as e:
        results['parallel_processing'] = f'ERROR: {e}'
    
    # Check security config
    try:
        from backend.utils.security_config import get_security_config
        config = get_security_config()
        results['security_config'] = 'OK'
    except Exception as e:
        results['security_config'] = f'ERROR: {e}'
    
    return results

# Serve static files in production
static_path = Path("/app/static")
if static_path.exists():
    app.mount("/assets", StaticFiles(directory=static_path / "assets"), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # API routes should not reach here
        if full_path.startswith("api/"):
            return {"error": "Not found"}
        
        # Serve index.html for SPA routing
        index_path = static_path / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        return {"error": "Frontend not built"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
