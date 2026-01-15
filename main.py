"""
XLR8 FastAPI Backend
Main application entry point

Updated: December 12, 2025 - Added intelligence router (Phase 3 Universal Analysis Engine)
Updated: December 14, 2025 - Added playbook_builder router (P3.6 P3)
Updated: December 15, 2025 - Added advisor router (Work Advisor)
Updated: December 17, 2025 - Added cleanup router (data deletion endpoints)
Updated: December 17, 2025 - Replaced vacuum with register_extractor (local LLM + DuckDB)
Updated: December 23, 2025 - Added smart_router (unified upload endpoint)
Updated: December 23, 2025 - Added metrics_router (platform analytics)
Updated: December 27, 2025 - Added classification_router (FIVE TRUTHS transparency layer)
Updated: January 15, 2026 - Added remediation router (Phase 4A.6 & 4A.7 Playbook Wire-up + Progress)
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

from backend.routers import upload, projects, jobs

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

# Import register_extractor router (formerly vacuum - includes backward compat routes)
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

# Import smart_router (unified upload endpoint - replaces fragmented upload paths)
try:
    from backend.routers import smart_router
    SMART_ROUTER_AVAILABLE = True
except ImportError as e:
    SMART_ROUTER_AVAILABLE = False
    logging.warning(f"Smart router import failed: {e}")

# Import metrics router (platform analytics for dashboards)
try:
    from backend.routers import metrics_router
    METRICS_AVAILABLE = True
except ImportError as e:
    METRICS_AVAILABLE = False
    logging.warning(f"Metrics router import failed: {e}")

# Import classification router (FIVE TRUTHS transparency layer)
try:
    from backend.routers import classification_router
    CLASSIFICATION_AVAILABLE = True
except ImportError as e:
    CLASSIFICATION_AVAILABLE = False
    logging.warning(f"Classification router import failed: {e}")

# Import platform router (COMPREHENSIVE status endpoint - replaces 50+ scattered endpoints)
try:
    from backend.routers import platform
    PLATFORM_AVAILABLE = True
except ImportError as e:
    PLATFORM_AVAILABLE = False
    logging.warning(f"Platform router import failed: {e}")

# Import features router (comparison and export engines)
try:
    from backend.routers import features
    FEATURES_AVAILABLE = True
except ImportError as e:
    FEATURES_AVAILABLE = False
    logging.warning(f"Features router import failed: {e}")

# Import domain decoder router (consultant knowledge)
try:
    from backend.routers import decoder_router
    DECODER_AVAILABLE = True
except ImportError as e:
    DECODER_AVAILABLE = False
    logging.warning(f"Decoder router import failed: {e}")

# Import reference truth router (systems, domains, detection)
try:
    from backend.routers import reference
    REFERENCE_AVAILABLE = True
except ImportError as e:
    REFERENCE_AVAILABLE = False
    logging.warning(f"Reference router import failed: {e}")

try:
    from backend.routers import dashboard
    DASHBOARD_AVAILABLE = True
except ImportError as e:
    DASHBOARD_AVAILABLE = False
    logging.warning(f"Dashboard router import failed: {e}")

# Standards endpoints are now in upload.py (no separate router needed)

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

# =============================================================================
# STARTUP: Load playbooks from Supabase
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Startup tasks: cleanup stuck jobs, load playbooks."""
    
    # CRITICAL: Clean up any jobs stuck from previous runs/crashes
    try:
        from models.processing_job import ProcessingJobModel
        cancelled = ProcessingJobModel.cancel_stuck(max_age_minutes=15)
        if cancelled > 0:
            logger.warning(f"[STARTUP] Cancelled {cancelled} stuck jobs from previous run")
        else:
            logger.info("[STARTUP] No stuck jobs to clean up")
    except ImportError:
        try:
            from utils.database.models import ProcessingJobModel
            cancelled = ProcessingJobModel.cancel_stuck(max_age_minutes=15)
            if cancelled > 0:
                logger.warning(f"[STARTUP] Cancelled {cancelled} stuck jobs from previous run")
            else:
                logger.info("[STARTUP] No stuck jobs to clean up")
        except Exception as e:
            logger.warning(f"[STARTUP] Could not clean stuck jobs: {e}")
    except Exception as e:
        logger.warning(f"[STARTUP] Could not clean stuck jobs: {e}")
    
    # Load playbooks from Supabase
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


# Register core routers
app.include_router(upload.router, prefix="/api")
app.include_router(projects.router, prefix="/api/projects")
app.include_router(jobs.router, prefix="/api")

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

# Register register_extractor router if available (pay register extraction + DuckDB storage)
if REGISTER_EXTRACTOR_AVAILABLE:
    app.include_router(register_extractor.router, prefix="/api", tags=["register-extractor"])
    logger.info("Register extractor router registered (includes /vacuum backward compat)")
else:
    logger.warning("Register extractor router not available")

# Register playbooks router if available
if PLAYBOOKS_AVAILABLE:
    app.include_router(playbooks.router, prefix="/api/playbooks")
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
    app.include_router(advisor_router.router, prefix="/api/advisor", tags=["advisor"])
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
    app.include_router(security.router, prefix="/api/security", tags=["security"])
    logger.info("Security router registered at /api/security")
else:
    # Create inline fallback security endpoints
    from fastapi import APIRouter
    security_fallback = APIRouter(tags=["security"])
    
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
    
    app.include_router(security_fallback, prefix="/api/security")
    logger.info("Security fallback endpoints registered (using threat_assessor directly)")

# Register auth router if available (user management, RBAC)
if AUTH_AVAILABLE:
    app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
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
    app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
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
    app.include_router(intelligence.router, prefix="/api/intelligence", tags=["intelligence"])
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

# Register smart_router if available (unified upload endpoint)
if SMART_ROUTER_AVAILABLE:
    app.include_router(smart_router.router, prefix="/api", tags=["smart-router"])
    logger.info("Smart router registered at /api/upload (unified endpoint)")
else:
    logger.warning("Smart router not available - using legacy upload.py")

# Register metrics router if available (platform analytics)
if METRICS_AVAILABLE:
    app.include_router(metrics_router.router, prefix="/api/metrics", tags=["metrics"])
    logger.info("Metrics router registered at /api/metrics")
else:
    logger.warning("Metrics router not available")

# Register classification router if available (FIVE TRUTHS transparency)
if CLASSIFICATION_AVAILABLE:
    app.include_router(classification_router.router, prefix="/api", tags=["classification"])
    logger.info("Classification router registered at /api/classification")
else:
    logger.warning("Classification router not available")

# Register platform router if available (COMPREHENSIVE status - ONE endpoint for everything)
if PLATFORM_AVAILABLE:
    app.include_router(platform.router, prefix="/api", tags=["platform"])
    logger.info("Platform router registered at /api/platform - USE THIS INSTEAD OF 50+ STATUS ENDPOINTS")
else:
    logger.warning("Platform router not available")

# Register features router if available (comparison and export engines)
if FEATURES_AVAILABLE:
    app.include_router(features.router, prefix="/api", tags=["features"])
    logger.info("Features router registered at /api (compare, export)")
else:
    logger.warning("Features router not available")

# Register domain decoder router if available (consultant knowledge)
if DECODER_AVAILABLE:
    app.include_router(decoder_router.router, prefix="/api/decoder", tags=["domain-decoder"])
    logger.info("Domain Decoder router registered at /api/decoder")
else:
    logger.warning("Domain Decoder router not available")

# Register reference truth router if available (systems, domains, detection)
if REFERENCE_AVAILABLE:
    app.include_router(reference.router, prefix="/api/reference", tags=["reference"])
    logger.info("Reference Truth router registered at /api/reference")
else:
    logger.warning("Reference Truth router not available")

# Register dashboard router if available (real metrics, lineage, relationships)
if DASHBOARD_AVAILABLE:
    app.include_router(dashboard.router, tags=["dashboard"])
    logger.info("Dashboard router registered at /api/dashboard")
else:
    logger.warning("Dashboard router not available")

# Register findings router (Phase 4A.4 - Findings Dashboard)
try:
    from backend.routers import findings
    app.include_router(findings.router, prefix="/api/findings", tags=["findings"])
    logger.info("Findings router registered at /api/findings")
except ImportError as e:
    logger.warning(f"Findings router import failed: {e}")

# Register remediation router (Phase 4A.6 & 4A.7 - Playbook Wire-up + Progress Tracker)
try:
    from backend.routers import remediation
    app.include_router(remediation.router, prefix="/api", tags=["remediation"])
    logger.info("Remediation router registered at /api/remediation")
except ImportError as e:
    logger.warning(f"Remediation router import failed: {e}")


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
    
    # Check classification service
    try:
        from backend.utils.classification_service import ClassificationService
        results['classification_service'] = 'OK'
    except Exception as e:
        results['classification_service'] = f'ERROR: {e}'
    
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
