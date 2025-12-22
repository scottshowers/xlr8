"""
XLR8 FastAPI Backend
Main application entry point

Updated: December 12, 2025 - Added intelligence router (Phase 3 Universal Analysis Engine)
Updated: December 14, 2025 - Added playbook_builder router (P3.6 P3)
Updated: December 15, 2025 - Added advisor router (Work Advisor)
Updated: December 17, 2025 - Added cleanup router (data deletion endpoints)
Updated: December 17, 2025 - Replaced vacuum with register_extractor (local LLM + DuckDB)
Updated: December 22, 2025 - Added Smart Router (unified upload endpoint)
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

from backend.routers import chat, status, projects, jobs

# Import Smart Router (unified upload endpoint - replaces separate upload paths)
try:
    from backend.routers import smart_router
    SMART_ROUTER_AVAILABLE = True
except ImportError as e:
    SMART_ROUTER_AVAILABLE = False
    logging.warning(f"Smart router import failed: {e}")
    # Fallback to legacy upload router
    try:
        from backend.routers import upload
        LEGACY_UPLOAD_AVAILABLE = True
    except ImportError:
        LEGACY_UPLOAD_AVAILABLE = False
        logging.error("Neither smart_router nor upload router available!")

# Import playbooks router
try:
    from backend.routers import playbooks
    PLAYBOOKS_AVAILABLE = True
except ImportError as e:
    PLAYBOOKS_AVAILABLE = False
    logging.error(f"Playbooks router import failed: {e}")

# Import playbook_builder router
try:
    from backend.routers import playbook_builder
    PLAYBOOK_BUILDER_AVAILABLE = True
except ImportError as e:
    PLAYBOOK_BUILDER_AVAILABLE = False
    logging.warning(f"Playbook builder router import failed: {e}")

# Import advisor router (Work Advisor - conversational guide)
try:
    from backend.routers import advisor_router
    ADVISOR_AVAILABLE = True
except ImportError as e:
    ADVISOR_AVAILABLE = False
    logging.warning(f"Advisor router import failed: {e}")

# Import register_extractor router (for job status endpoints - upload now handled by smart_router)
try:
    from backend.routers import register_extractor
    REGISTER_EXTRACTOR_AVAILABLE = True
except ImportError:
    REGISTER_EXTRACTOR_AVAILABLE = False
    logging.warning("Register extractor router import failed")

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

# Import admin router (learning system management)
try:
    from backend.routers import admin
    ADMIN_AVAILABLE = True
except ImportError as e:
    ADMIN_AVAILABLE = False
    logging.warning(f"Admin router import failed: {e}")

# Import api_connections router (UKG Pro/WFM/Ready integration)
try:
    from backend.routers import api_connections
    API_CONNECTIONS_AVAILABLE = True
except ImportError as e:
    API_CONNECTIONS_AVAILABLE = False
    logging.warning(f"API connections router import failed: {e}")

# Import intelligence router (Phase 3 Universal Analysis Engine)
try:
    from backend.routers import intelligence
    INTELLIGENCE_AVAILABLE = True
except ImportError as e:
    INTELLIGENCE_AVAILABLE = False
    logging.warning(f"Intelligence router import failed: {e}")

# Import unified_chat router (Phase 3.5 Intelligence Consumer)
try:
    from backend.routers import unified_chat
    UNIFIED_CHAT_AVAILABLE = True
except ImportError as e:
    UNIFIED_CHAT_AVAILABLE = False
    logging.warning(f"Unified chat router import failed: {e}")

# Import bi_router (Phase 5 BI Builder)
try:
    from backend.routers import bi_router
    BI_ROUTER_AVAILABLE = True
except ImportError as e:
    BI_ROUTER_AVAILABLE = False
    logging.warning(f"BI router import failed: {e}")

# Import cleanup router (data deletion endpoints)
try:
    from backend.routers import cleanup
    CLEANUP_AVAILABLE = True
except ImportError as e:
    CLEANUP_AVAILABLE = False
    logging.warning(f"Cleanup router import failed: {e}")

# Import deep_clean router (unified orphan cleanup across all storage systems)
try:
    from backend.routers import deep_clean
    DEEP_CLEAN_AVAILABLE = True
except ImportError as e:
    DEEP_CLEAN_AVAILABLE = False
    logging.warning(f"Deep clean router import failed: {e}")

# Import health router (comprehensive system diagnostics)
try:
    from backend.routers import health
    HEALTH_AVAILABLE = True
except ImportError as e:
    HEALTH_AVAILABLE = False
    logging.warning(f"Health router import failed: {e}")

# Standards endpoints are now in smart_router.py (no separate router needed)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="XLR8", version="2.1")

# CORS Configuration - Allow all origins for now
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # Must be False when using wildcard
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# =============================================================================
# STARTUP: Load playbooks from Supabase
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Load playbooks from Supabase on startup."""
    try:
        from utils.playbook_loader import load_playbooks_from_supabase
        results = load_playbooks_from_supabase()
        logger.info(f"Loaded {sum(results.values())}/{len(results)} playbooks from Supabase")
    except ImportError:
        try:
            from backend.utils.playbook_loader import load_playbooks_from_supabase
            results = load_playbooks_from_supabase()
            logger.info(f"Loaded {sum(results.values())}/{len(results)} playbooks from Supabase")
        except ImportError:
            logger.warning("Playbook loader not available - using code-defined playbooks only")


# =============================================================================
# CORE ROUTERS
# =============================================================================

app.include_router(chat.router, prefix="/api")
app.include_router(status.router, prefix="/api")
app.include_router(projects.router, prefix="/api/projects")
app.include_router(jobs.router, prefix="/api")

# =============================================================================
# SMART ROUTER - Unified Upload Endpoint (replaces separate upload paths)
# =============================================================================

if SMART_ROUTER_AVAILABLE:
    app.include_router(smart_router.router, prefix="/api", tags=["upload"])
    logger.info("Smart Router registered at /api/upload (unified upload endpoint)")
    logger.info("  → Routes: /upload, /standards/upload, /register/upload")
    logger.info("  → Auto-detects: register, standards, structured, semantic")
else:
    # Fallback to legacy upload router if smart_router not available
    if LEGACY_UPLOAD_AVAILABLE:
        app.include_router(upload.router, prefix="/api")
        logger.warning("Using legacy upload router (smart_router not available)")
    else:
        logger.error("No upload router available!")

# Register register_extractor for job status endpoints (upload handled by smart_router)
if REGISTER_EXTRACTOR_AVAILABLE:
    # Only register the job status and extract endpoints, not the upload endpoints
    # (those are now handled by smart_router with backward compat aliases)
    from fastapi import APIRouter
    register_jobs_router = APIRouter()
    
    # Re-export just the job/status endpoints
    @register_jobs_router.get("/register/job/{job_id}")
    async def get_register_job_status(job_id: str):
        """Get status of register extraction job."""
        return await register_extractor.get_job_status(job_id)
    
    @register_jobs_router.get("/register/extracts")
    async def get_register_extracts(project_id: str = None, limit: int = 50):
        """Get extraction history."""
        return await register_extractor.get_extracts_list(project_id, limit)
    
    @register_jobs_router.get("/register/extract/{extract_id}")
    async def get_register_extract(extract_id: str):
        """Get full extraction details."""
        return await register_extractor.get_extract(extract_id)
    
    @register_jobs_router.delete("/register/extract/{extract_id}")
    async def delete_register_extract(extract_id: str):
        """Delete an extraction."""
        return await register_extractor.delete_extract(extract_id)
    
    @register_jobs_router.get("/register/status")
    async def get_register_status():
        """Get register extractor status."""
        return await register_extractor.status()
    
    @register_jobs_router.get("/register/health")
    async def get_register_health():
        """Get register extractor health."""
        return await register_extractor.health()
    
    # Backward compatibility for /vacuum endpoints
    @register_jobs_router.get("/vacuum/status")
    async def vacuum_status_compat():
        return await register_extractor.status()
    
    @register_jobs_router.get("/vacuum/job/{job_id}")
    async def vacuum_job_compat(job_id: str):
        return await register_extractor.get_job_status(job_id)
    
    @register_jobs_router.get("/vacuum/extracts")
    async def vacuum_extracts_compat(project_id: str = None, limit: int = 50):
        return await register_extractor.get_extracts_list(project_id, limit)
    
    app.include_router(register_jobs_router, prefix="/api", tags=["register"])
    logger.info("Register extractor job endpoints registered at /api/register")
else:
    logger.warning("Register extractor not available")

# =============================================================================
# OPTIONAL ROUTERS
# =============================================================================

# Register cleanup router if available (data deletion endpoints)
if CLEANUP_AVAILABLE:
    app.include_router(cleanup.router, prefix="/api", tags=["cleanup"])
    logger.info("Cleanup router registered at /api (jobs, structured, documents deletion)")
else:
    logger.warning("Cleanup router not available")

# Register deep_clean router if available (unified orphan cleanup)
if DEEP_CLEAN_AVAILABLE:
    app.include_router(deep_clean.router, prefix="/api", tags=["deep-clean"])
    logger.info("Deep clean router registered at /api/deep-clean")
else:
    logger.warning("Deep clean router not available")

# Register playbooks router if available
if PLAYBOOKS_AVAILABLE:
    app.include_router(playbooks.router, prefix="/api", tags=["playbooks"])
    logger.info("Playbooks router registered at /api/playbooks")
else:
    logger.warning("Playbooks router not available")

# Register playbook_builder router if available
if PLAYBOOK_BUILDER_AVAILABLE:
    app.include_router(playbook_builder.router, prefix="/api", tags=["playbook-builder"])
    logger.info("Playbook builder router registered at /api/playbook-builder")
else:
    logger.warning("Playbook builder router not available")

# Register advisor router if available (Work Advisor - conversational guide)
if ADVISOR_AVAILABLE:
    app.include_router(advisor_router.router, tags=["advisor"])
    logger.info("Advisor router registered at /api/advisor")
else:
    logger.warning("Advisor router not available")

# Register progress router if available (SSE streaming)
if PROGRESS_AVAILABLE:
    app.include_router(progress.router, prefix="/api", tags=["progress"])
    logger.info("Progress router registered (SSE streaming enabled)")
else:
    logger.warning("Progress router not available")

# Register security router if available (threat monitoring)
if SECURITY_AVAILABLE:
    app.include_router(security.router, tags=["security"])
    logger.info("Security router registered at /api/security")
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
                    "ollama": {"level": 0, "label": "LOCAL AI (OLLAMA)", "component": "ollama", "category": "ai", "issues": [], "action": "", "lastScan": now},
                    "filesystem": {"level": 0, "label": "FILE SYSTEM", "component": "filesystem", "category": "data", "issues": [], "action": "", "lastScan": now},
                }

    @security_fallback.get("/summary")
    async def get_security_summary_fallback():
        """Fallback security summary."""
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
    logger.info("Security fallback endpoints registered (using threat_assessor directly)")

# Register auth router if available (user management, RBAC)
if AUTH_AVAILABLE:
    app.include_router(auth.router, tags=["auth"])
    logger.info("Auth router registered at /api/auth")
else:
    logger.warning("Auth router not available")

# Register data_model router if available (relationship detection)
if DATA_MODEL_AVAILABLE:
    app.include_router(data_model.router, prefix="/api", tags=["data-model"])
    logger.info("Data model router registered at /api/data-model")
else:
    logger.warning("Data model router not available")

# Register admin router if available (learning system management)
if ADMIN_AVAILABLE:
    app.include_router(admin.router, prefix="/api", tags=["admin"])
    logger.info("Admin router registered at /api/admin")
else:
    logger.warning("Admin router not available")

# Register api_connections router if available (UKG Pro/WFM/Ready integration)
if API_CONNECTIONS_AVAILABLE:
    app.include_router(api_connections.router, prefix="/api", tags=["connections"])
    logger.info("API connections router registered at /api/connections")
else:
    logger.warning("API connections router not available")

# Register intelligence router if available (Phase 3 Universal Analysis Engine)
if INTELLIGENCE_AVAILABLE:
    app.include_router(intelligence.router, prefix="/api", tags=["intelligence"])
    logger.info("Intelligence router registered at /api/intelligence")
else:
    logger.warning("Intelligence router not available")

# Register unified_chat router if available (Phase 3.5 Intelligence Consumer)
if UNIFIED_CHAT_AVAILABLE:
    app.include_router(unified_chat.router, prefix="/api", tags=["unified-chat"])
    logger.info("Unified chat router registered at /api/chat/unified")
else:
    logger.warning("Unified chat router not available")

# Register bi_router if available (Phase 5 BI Builder)
if BI_ROUTER_AVAILABLE:
    app.include_router(bi_router.router, prefix="/api", tags=["bi"])
    logger.info("BI router registered at /api/bi")
else:
    logger.warning("BI router not available")

# Register health router if available (comprehensive system diagnostics)
if HEALTH_AVAILABLE:
    app.include_router(health.router, prefix="/api", tags=["health"])
    logger.info("Health router registered at /api/health")
else:
    logger.warning("Health router not available - using fallback")
    
    # Fallback minimal health endpoint if router not available
    @app.get("/api/health")
    async def health_fallback():
        """Minimal health check fallback."""
        return {"status": "healthy", "note": "Full health router not loaded"}


# =============================================================================
# DEBUG ENDPOINTS
# =============================================================================

@app.get("/api/debug/imports")
async def debug_imports():
    """Debug endpoint to check import status."""
    results = {}
    
    # Check smart router
    results['smart_router'] = 'OK' if SMART_ROUTER_AVAILABLE else 'NOT AVAILABLE'
    
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
    
    # Check advisor router
    try:
        from backend.routers.advisor_router import router
        results['advisor_router'] = 'OK'
    except Exception as e:
        results['advisor_router'] = f'ERROR: {e}'
    
    # Check cleanup router
    try:
        from backend.routers.cleanup import router
        results['cleanup_router'] = 'OK'
    except Exception as e:
        results['cleanup_router'] = f'ERROR: {e}'
    
    return results


@app.get("/api/debug/routes")
async def debug_routes():
    """List all registered routes."""
    routes = []
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            routes.append({
                'path': route.path,
                'methods': list(route.methods) if route.methods else [],
                'name': route.name
            })
    return {"total": len(routes), "routes": sorted(routes, key=lambda x: x['path'])}


# =============================================================================
# STATIC FILES (Production)
# =============================================================================

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
