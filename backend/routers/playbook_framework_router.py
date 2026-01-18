"""
PLAYBOOK FRAMEWORK ROUTER - Shim
=================================

This module re-exports the router from the playbook framework package.
The actual implementation is in /backend/playbooks/framework/router.py

This shim exists so main.py can import from the standard routers location.

ENDPOINTS (via framework):
- GET  /api/playbooks/list                              - List available playbooks
- GET  /api/playbooks/{id}/definition                   - Get playbook structure
- POST /api/playbooks/{id}/instance/{project}           - Get/create instance
- GET  /api/playbooks/instance/{id}/progress            - Progress summary
- POST /api/playbooks/instance/{id}/match               - Match files to requirements
- POST /api/playbooks/instance/{id}/step/{step}/execute - Execute a step
- POST /api/playbooks/instance/{id}/execute-all         - Execute all steps
- PUT  /api/playbooks/instance/{id}/step/{step}/status  - Update status
- PUT  /api/playbooks/instance/{id}/finding/{finding}   - Acknowledge/suppress

Old router backed up to: playbook_framework_router_OLD.py

Author: XLR8 Team
Updated: January 18, 2026
"""

import logging

logger = logging.getLogger(__name__)

# Import and re-export the router from the framework
try:
    from backend.playbooks.framework.router import router
    logger.info("[PLAYBOOK-FW] Successfully imported framework router")
except ImportError as e1:
    logger.warning(f"[PLAYBOOK-FW] Primary import failed: {e1}")
    try:
        from playbooks.framework.router import router
        logger.info("[PLAYBOOK-FW] Successfully imported framework router (alt path)")
    except ImportError as e2:
        logger.error(f"[PLAYBOOK-FW] All imports failed: {e2}")
        # Create a dummy router if framework not available
        from fastapi import APIRouter
        router = APIRouter(prefix="/api/playbooks", tags=["playbook-framework"])
        
        @router.get("/health")
        async def framework_health():
            return {
                'status': 'unavailable',
                'error': 'Playbook framework not found - check /backend/playbooks/framework/'
            }
