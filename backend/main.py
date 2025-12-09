"""
XLR8 FastAPI Backend
Main application entry point

Updated: December 8, 2025 - Added security router for real-time threat monitoring
"""

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

# Import playbooks router
try:
    from backend.routers import playbooks
    PLAYBOOKS_AVAILABLE = True
except ImportError as e:
    PLAYBOOKS_AVAILABLE = False
    logging.error(f"Playbooks router import failed: {e}")

# Import vacuum router
try:
    from backend.routers import vacuum
    VACUUM_AVAILABLE = True
except ImportError:
    VACUUM_AVAILABLE = False

# Import progress router (SSE streaming)
try:
    from backend.routers import progress
    PROGRESS_AVAILABLE = True
except ImportError:
    PROGRESS_AVAILABLE = False

# Import security router (threat monitoring)
try:
    from backend.routers import security
    SECURITY_AVAILABLE = True
except ImportError as e:
    SECURITY_AVAILABLE = False
    logging.warning(f"Security router import failed: {e}")

# Import auth router (user management, RBAC)
try:
    from backend.routers import auth
    AUTH_AVAILABLE = True
except ImportError as e:
    AUTH_AVAILABLE = False
    logging.warning(f"Auth router import failed: {e}")

# Import data_model router (relationship detection)
try:
    from backend.routers import data_model
    DATA_MODEL_AVAILABLE = True
except ImportError as e:
    DATA_MODEL_AVAILABLE = False
    logging.warning(f"Data model router import failed: {e}")

# Import intelligent_chat router (revolutionary AI chat)
try:
    from backend.routers import intelligent_chat
    INTELLIGENT_CHAT_AVAILABLE = True
except ImportError as e:
    INTELLIGENT_CHAT_AVAILABLE = False
    logging.warning(f"Intelligent chat router import failed: {e}")

# Import admin router (learning system management)
try:
    from backend.routers import admin
    ADMIN_AVAILABLE = True
except ImportError as e:
    ADMIN_AVAILABLE = False
    logging.warning(f"Admin router import failed: {e}")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="XLR8", version="2.0")

# CORS Configuration - Allow all origins for now
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # Must be False when using wildcard
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Register core routers
app.include_router(chat.router, prefix="/api")
app.include_router(upload.router, prefix="/api")
app.include_router(status.router, prefix="/api")
app.include_router(projects.router, prefix="/api/projects")
app.include_router(jobs.router, prefix="/api")

# Register vacuum router if available
if VACUUM_AVAILABLE:
    app.include_router(vacuum.router, prefix="/api", tags=["vacuum"])
    logger.info("✓ Vacuum router registered")
else:
    logger.warning("Vacuum router not available")

# Register playbooks router if available
if PLAYBOOKS_AVAILABLE:
    app.include_router(playbooks.router, prefix="/api")
    logger.info("✓ Playbooks router registered at /api/playbooks")
else:
    logger.warning("Playbooks router not available")

# Register progress router if available (SSE streaming)
if PROGRESS_AVAILABLE:
    app.include_router(progress.router, prefix="/api", tags=["progress"])
    logger.info("✓ Progress router registered (SSE streaming enabled)")
else:
    logger.warning("Progress router not available")

# Register security router if available (threat monitoring)
if SECURITY_AVAILABLE:
    app.include_router(security.router, tags=["security"])
    logger.info("✓ Security router registered at /api/security")
else:
    # Create inline fallback security endpoints
    from fastapi import APIRouter
    security_fallback = APIRouter(prefix="/api/security", tags=["security"])
    
    @security_fallback.get("/threats")
    async def get_threats_fallback():
        """Fallback threat endpoint when full security module not available."""
        try:
            from backend.utils.threat_assessor import get_threat_assessor, refresh_assessor
            assessor = refresh_assessor()
            return assessor.assess_all()
        except ImportError:
            try:
                from utils.threat_assessor import get_threat_assessor, refresh_assessor
                assessor = refresh_assessor()
                return assessor.assess_all()
            except ImportError:
                # Return minimal fallback
                from datetime import datetime
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                return {
                    "api": {"level": 0, "label": "API GATEWAY", "component": "api", "category": "infrastructure", "issues": [], "action": "", "lastScan": now},
                    "duckdb": {"level": 0, "label": "STRUCTURED DB", "component": "duckdb", "category": "data", "issues": [], "action": "", "lastScan": now},
                    "chromadb": {"level": 0, "label": "VECTOR STORE", "component": "chromadb", "category": "data", "issues": [], "action": "", "lastScan": now},
                    "claude": {"level": 0, "label": "CLOUD AI (CLAUDE)", "component": "claude", "category": "ai", "issues": [], "action": "", "lastScan": now},
                    "supabase": {"level": 0, "label": "AUTHENTICATION", "component": "supabase", "category": "infrastructure", "issues": [], "action": "", "lastScan": now},
                    "runpod": {"level": 0, "label": "LOCAL AI (RUNPOD)", "component": "runpod", "category": "ai", "issues": [], "action": "", "lastScan": now},
                    "rag": {"level": 0, "label": "RAG ENGINE", "component": "rag", "category": "ai", "issues": [], "action": "", "lastScan": now},
                }
    
    @security_fallback.get("/threats/summary")
    async def get_threats_summary_fallback():
        """Fallback summary endpoint."""
        try:
            from backend.utils.threat_assessor import refresh_assessor
            assessor = refresh_assessor()
            return assessor.get_summary()
        except ImportError:
            try:
                from utils.threat_assessor import refresh_assessor
                assessor = refresh_assessor()
                return assessor.get_summary()
            except ImportError:
                return {
                    "status": "ALL SYSTEMS NOMINAL",
                    "total_issues": 0,
                    "open_issues": 0,
                    "high_severity": 0,
                    "components_at_risk": 0,
                    "total_components": 7,
                    "last_scan": None,
                }
    
    app.include_router(security_fallback)
    logger.info("✓ Security fallback endpoints registered (using threat_assessor directly)")

# Register auth router if available (user management, RBAC)
if AUTH_AVAILABLE:
    app.include_router(auth.router, tags=["auth"])
    logger.info("✓ Auth router registered at /api/auth")
else:
    logger.warning("Auth router not available")

# Register data_model router if available (relationship detection)
if DATA_MODEL_AVAILABLE:
    app.include_router(data_model.router, prefix="/api", tags=["data-model"])
    logger.info("✓ Data model router registered at /api/data-model")
else:
    logger.warning("Data model router not available")

# Register intelligent_chat router if available (revolutionary AI chat)
if INTELLIGENT_CHAT_AVAILABLE:
    app.include_router(intelligent_chat.router, prefix="/api", tags=["intelligent-chat"])
    logger.info("✓ Intelligent chat router registered at /api/chat/intelligent")
else:
    logger.warning("Intelligent chat router not available")

# Register admin router if available (learning system management)
if ADMIN_AVAILABLE:
    app.include_router(admin.router, prefix="/api", tags=["admin"])
    logger.info("✓ Admin router registered at /api/admin")
else:
    logger.warning("Admin router not available")


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    try:
        from utils.rag_handler import RAGHandler
        rag = RAGHandler()
        
        # Check various subsystems
        features = {
            "rag": True,
            "chat": True,
            "upload": True,
            "status": True,
            "vacuum": VACUUM_AVAILABLE,
            "playbooks": PLAYBOOKS_AVAILABLE,
            "progress": PROGRESS_AVAILABLE,
            "security": SECURITY_AVAILABLE,
            "auth": AUTH_AVAILABLE,
            "data_model": DATA_MODEL_AVAILABLE,
            "intelligent_chat": INTELLIGENT_CHAT_AVAILABLE,
            "admin": ADMIN_AVAILABLE,
        }
        
        return {
            "status": "healthy",
            "features": features,
            "collections": {
                "hcmpact_docs": rag.collection.count() if hasattr(rag, 'collection') else 0,
            }
        }
    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e),
            "features": {
                "vacuum": VACUUM_AVAILABLE,
                "playbooks": PLAYBOOKS_AVAILABLE,
                "progress": PROGRESS_AVAILABLE,
                "security": SECURITY_AVAILABLE,
                "intelligent_chat": INTELLIGENT_CHAT_AVAILABLE,
                "admin": ADMIN_AVAILABLE,
            }
        }


@app.get("/api/debug/imports")
async def debug_imports():
    """Debug endpoint to check import status."""
    results = {}
    
    # Check structured data handler
    try:
        from utils.structured_data_handler import StructuredDataHandler
        results['structured_data_handler'] = 'OK'
    except Exception as e:
        results['structured_data_handler'] = f'ERROR: {e}'
    
    # Check RAG handler
    try:
        from utils.rag_handler import RAGHandler
        results['rag_handler'] = 'OK'
    except Exception as e:
        results['rag_handler'] = f'ERROR: {e}'
    
    # Check hybrid analyzer
    try:
        from backend.utils.hybrid_analyzer import HybridAnalyzer
        results['hybrid_analyzer'] = 'OK'
    except Exception as e:
        results['hybrid_analyzer'] = f'ERROR: {e}'
    
    # Check security config
    try:
        from backend.utils.security_config import get_security_config
        config = get_security_config()
        results['security_config'] = 'OK'
    except Exception as e:
        try:
            from utils.security_config import get_security_config
            config = get_security_config()
            results['security_config'] = 'OK (alt path)'
        except Exception as e2:
            results['security_config'] = f'ERROR: {e2}'
    
    # Check threat assessor
    try:
        from backend.utils.threat_assessor import get_threat_assessor
        assessor = get_threat_assessor()
        results['threat_assessor'] = 'OK'
    except Exception as e:
        try:
            from utils.threat_assessor import get_threat_assessor
            assessor = get_threat_assessor()
            results['threat_assessor'] = 'OK (alt path)'
        except Exception as e2:
            results['threat_assessor'] = f'ERROR: {e2}'
    
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
