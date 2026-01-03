"""
XLR8 Security Router
====================
API endpoints for real-time security monitoring and threat assessment.

Endpoints:
- GET /api/security/threats - Get current threat data for all components
- GET /api/security/threats/summary - Get security summary
- GET /api/security/config - Get current security config
- POST /api/security/toggle/{feature} - Toggle security feature
- POST /api/security/scan - Force rescan of security posture

Author: XLR8 Platform
Date: December 8, 2025
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
from pydantic import BaseModel

router = APIRouter(tags=["security"])


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class ToggleRequest(BaseModel):
    enabled: bool


class ToggleResponse(BaseModel):
    feature: str
    enabled: bool
    message: str


# =============================================================================
# THREAT DATA ENDPOINTS
# =============================================================================

@router.get("/threats")
async def get_threats() -> Dict[str, Any]:
    """
    Get current threat assessment for all components.
    
    Returns real-time security status based on actual configuration.
    Called by SystemMonitor to populate the security dashboard.
    """
    try:
        from backend.utils.threat_assessor import get_threat_assessor, refresh_assessor
        # Refresh to get latest config
        assessor = refresh_assessor()
        return assessor.assess_all()
    except ImportError:
        try:
            from utils.threat_assessor import get_threat_assessor, refresh_assessor
            assessor = refresh_assessor()
            return assessor.assess_all()
        except ImportError:
            # Return empty threats if module not available
            return _get_fallback_threats()


@router.get("/threats/summary")
async def get_threats_summary() -> Dict[str, Any]:
    """
    Get summary of security posture.
    
    Returns:
        - status: Overall status message
        - total_issues: Count of all issues
        - open_issues: Count of open issues
        - high_severity: Count of high severity issues
        - components_at_risk: Number of components with issues
    """
    try:
        from backend.utils.threat_assessor import get_threat_assessor, refresh_assessor
        assessor = refresh_assessor()
        return assessor.get_summary()
    except ImportError:
        try:
            from utils.threat_assessor import get_threat_assessor, refresh_assessor
            assessor = refresh_assessor()
            return assessor.get_summary()
        except ImportError:
            return {
                "status": "ASSESSMENT UNAVAILABLE",
                "total_issues": 0,
                "open_issues": 0,
                "high_severity": 0,
                "components_at_risk": 0,
                "total_components": 0,
                "last_scan": None,
            }


@router.post("/scan")
async def force_scan() -> Dict[str, Any]:
    """Force a rescan of security posture."""
    try:
        from backend.utils.threat_assessor import refresh_assessor
        assessor = refresh_assessor()
        return {
            "status": "scan_complete",
            "summary": assessor.get_summary(),
        }
    except ImportError:
        try:
            from utils.threat_assessor import refresh_assessor
            assessor = refresh_assessor()
            return {
                "status": "scan_complete",
                "summary": assessor.get_summary(),
            }
        except ImportError:
            raise HTTPException(500, "Threat assessor not available")


# =============================================================================
# SECURITY CONFIG ENDPOINTS
# =============================================================================

@router.get("/config")
async def get_config() -> Dict[str, Any]:
    """Get current security configuration."""
    try:
        from backend.utils.security_config import get_security_config
        config = get_security_config()
        return config.get_all()
    except ImportError:
        try:
            from utils.security_config import get_security_config
            config = get_security_config()
            return config.get_all()
        except ImportError:
            return {"error": "Security config not available"}


class ConfigUpdate(BaseModel):
    """Model for config updates."""
    updates: Dict[str, Any] = {}


@router.patch("/config")
async def update_config(body: ConfigUpdate) -> Dict[str, Any]:
    """Update security configuration."""
    try:
        from backend.utils.security_config import get_security_config
        config = get_security_config()
    except ImportError:
        try:
            from utils.security_config import get_security_config
            config = get_security_config()
        except ImportError:
            raise HTTPException(500, "Security config not available")
    
    # Apply updates
    for key, value in body.updates.items():
        config.set(key, value, updated_by="admin")
    
    # Refresh threat assessor to pick up changes
    try:
        from backend.utils.threat_assessor import refresh_assessor
        refresh_assessor()
    except ImportError:
        try:
            from utils.threat_assessor import refresh_assessor
            refresh_assessor()
        except ImportError:
            pass
    
    return {"status": "updated", "config": config.get_all()}


@router.post("/toggle/rate-limiting")
async def toggle_rate_limiting(req: ToggleRequest) -> ToggleResponse:
    """Toggle rate limiting on/off."""
    return await _toggle_feature("rate_limiting_enabled", req.enabled, "Rate limiting")


@router.post("/toggle/input-validation")
async def toggle_input_validation(req: ToggleRequest) -> ToggleResponse:
    """Toggle input validation on/off."""
    return await _toggle_feature("input_validation_enabled", req.enabled, "Input validation")


@router.post("/toggle/audit-logging")
async def toggle_audit_logging(req: ToggleRequest) -> ToggleResponse:
    """Toggle audit logging on/off."""
    return await _toggle_feature("audit_logging_enabled", req.enabled, "Audit logging")


@router.post("/toggle/security-headers")
async def toggle_security_headers(req: ToggleRequest) -> ToggleResponse:
    """Toggle security headers on/off."""
    return await _toggle_feature("security_headers_enabled", req.enabled, "Security headers")


@router.post("/toggle/prompt-sanitization")
async def toggle_prompt_sanitization(req: ToggleRequest) -> ToggleResponse:
    """Toggle prompt sanitization on/off."""
    return await _toggle_feature("prompt_sanitization_enabled", req.enabled, "Prompt sanitization")


@router.post("/toggle/pii-scan-uploads")
async def toggle_pii_scan_uploads(req: ToggleRequest) -> ToggleResponse:
    """Toggle PII scanning on uploads."""
    return await _toggle_feature("pii_auto_scan_uploads", req.enabled, "PII scan on uploads")


@router.post("/toggle/pii-scan-llm")
async def toggle_pii_scan_llm(req: ToggleRequest) -> ToggleResponse:
    """Toggle PII scanning before LLM calls."""
    return await _toggle_feature("pii_scan_before_llm", req.enabled, "PII scan before LLM")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def _toggle_feature(key: str, enabled: bool, label: str) -> ToggleResponse:
    """Toggle a security feature and return response."""
    try:
        from backend.utils.security_config import get_security_config
        config = get_security_config()
    except ImportError:
        try:
            from utils.security_config import get_security_config
            config = get_security_config()
        except ImportError:
            raise HTTPException(500, "Security config not available")
    
    config.set(key, enabled, updated_by="admin")
    
    # Refresh threat assessor to pick up changes
    try:
        from backend.utils.threat_assessor import refresh_assessor
        refresh_assessor()
    except ImportError:
        try:
            from utils.threat_assessor import refresh_assessor
            refresh_assessor()
        except ImportError:
            pass
    
    status = "enabled" if enabled else "disabled"
    return ToggleResponse(
        feature=key,
        enabled=enabled,
        message=f"{label} {status}"
    )


def _get_fallback_threats() -> Dict[str, Any]:
    """Return fallback threat data when assessor is unavailable."""
    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return {
        "api": {
            "level": 1,
            "label": "API GATEWAY",
            "component": "api",
            "category": "infrastructure",
            "issues": [{"id": "fallback", "issue": "Threat assessor unavailable", "severity": "low", "status": "open", "detected": now}],
            "action": "Deploy threat_assessor.py",
            "lastScan": now,
        },
        "duckdb": {"level": 0, "label": "STRUCTURED DB", "component": "duckdb", "category": "data", "issues": [], "action": "", "lastScan": now},
        "chromadb": {"level": 0, "label": "VECTOR STORE", "component": "chromadb", "category": "data", "issues": [], "action": "", "lastScan": now},
        "claude": {"level": 0, "label": "CLOUD AI (CLAUDE)", "component": "claude", "category": "ai", "issues": [], "action": "", "lastScan": now},
        "supabase": {"level": 0, "label": "AUTHENTICATION", "component": "supabase", "category": "infrastructure", "issues": [], "action": "", "lastScan": now},
        "runpod": {"level": 0, "label": "LOCAL AI (RUNPOD)", "component": "runpod", "category": "ai", "issues": [], "action": "", "lastScan": now},
        "rag": {"level": 0, "label": "RAG ENGINE", "component": "rag", "category": "ai", "issues": [], "action": "", "lastScan": now},
    }


# =============================================================================
# AUDIT LOG ENDPOINTS
# =============================================================================

@router.get("/audit/summary")
async def get_audit_summary(hours: int = 24) -> Dict[str, Any]:
    """
    Get audit log summary for the specified time period.
    """
    from datetime import datetime
    
    # For now, return placeholder data
    # TODO: Connect to actual audit log storage
    return {
        "period_hours": hours,
        "total_events": 0,
        "by_category": {
            "auth": 0,
            "data_access": 0,
            "config_change": 0,
            "security": 0,
        },
        "by_severity": {
            "info": 0,
            "warning": 0,
            "error": 0,
            "critical": 0,
        },
        "generated_at": datetime.now().isoformat(),
    }


@router.get("/audit/recent")
async def get_recent_audit_logs(limit: int = 20) -> Dict[str, Any]:
    """
    Get recent audit log entries.
    """
    from datetime import datetime
    
    # For now, return placeholder data
    # TODO: Connect to actual audit log storage
    return {
        "logs": [],
        "total": 0,
        "limit": limit,
        "generated_at": datetime.now().isoformat(),
    }
