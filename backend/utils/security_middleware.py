"""
XLR8 Security Middleware
========================
FastAPI middleware for applying security measures across all endpoints.

SAFE MODE: Risky features (rate limiting, input validation) are OFF by default.
Enable them via Admin > Security or the config API.

Includes:
- Rate limiting middleware (OFF by default)
- Request audit logging (ON by default)
- Input validation (OFF by default)
- CORS configuration
- Security headers (ON by default)

Author: XLR8 Platform
Date: December 8, 2025
"""

import time
import uuid
from typing import Callable, Optional, List, Dict, Any
from datetime import datetime
from functools import wraps

from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# Import our security module
from utils.security import (
    get_rate_limiter,
    get_audit_logger,
    get_pii_detector,
    get_prompt_sanitizer,
    AuditAction,
    RateLimiter,
    AuditLogger,
    configure_security,
)

# Import config manager
from utils.security_config import get_security_config


# =============================================================================
# RATE LIMITING MIDDLEWARE
# =============================================================================

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware that applies rate limiting to all requests.
    
    Checks config each request - can be toggled on/off at runtime.
    
    Identifies users by:
    1. Authorization header (API key or JWT)
    2. X-User-ID header
    3. IP address (fallback)
    """
    
    # Path -> resource type mapping
    RESOURCE_MAP = {
        "/api/upload": "upload",
        "/api/chat": "api",
        "/api/vacuum": "upload",
        "/api/year-end/scan": "llm_cloud",
        "/api/export": "export",
        "/auth": "auth",
    }
    
    def __init__(self, app: ASGIApp, limiter: Optional[RateLimiter] = None):
        super().__init__(app)
        self.limiter = limiter or get_rate_limiter()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check if rate limiting is enabled
        config = get_security_config()
        if not config.get("rate_limiting_enabled", False):
            return await call_next(request)
        
        # Skip rate limiting for health checks and static files
        if request.url.path in ["/health", "/", "/docs", "/openapi.json"]:
            return await call_next(request)
        
        # Identify the client
        identifier = self._get_identifier(request)
        
        # Determine resource type
        resource = self._get_resource(request.url.path)
        
        # Check rate limit
        if not self.limiter.allow(identifier, resource):
            # Log the rate limit hit
            get_audit_logger().log(
                action=AuditAction.RATE_LIMIT_HIT,
                resource_type=resource,
                user_id=identifier,
                ip_address=self._get_client_ip(request),
                details={"path": request.url.path, "method": request.method},
                success=False,
                error_message="Rate limit exceeded"
            )
            
            # Return 429 with retry info
            remaining = self.limiter.get_remaining(identifier, resource)
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "resource": resource,
                    "retry_after": 60,  # seconds
                },
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Remaining": str(remaining),
                }
            )
        
        # Add rate limit headers to response
        response = await call_next(request)
        remaining = self.limiter.get_remaining(identifier, resource)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response
    
    def _get_identifier(self, request: Request) -> str:
        """Extract client identifier from request."""
        # Try Authorization header
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            # Hash the token to use as identifier
            import hashlib
            return hashlib.sha256(auth.encode()).hexdigest()[:16]
        
        # Try custom user header
        user_id = request.headers.get("X-User-ID")
        if user_id:
            return user_id
        
        # Fall back to IP address
        return self._get_client_ip(request)
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP, considering proxies."""
        # Check X-Forwarded-For (set by reverse proxies)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # First IP in the list is the original client
            return forwarded.split(",")[0].strip()
        
        # Check X-Real-IP (nginx)
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct connection
        return request.client.host if request.client else "unknown"
    
    def _get_resource(self, path: str) -> str:
        """Map request path to resource type."""
        for prefix, resource in self.RESOURCE_MAP.items():
            if path.startswith(prefix):
                return resource
        return "api"  # Default


# =============================================================================
# AUDIT LOGGING MIDDLEWARE
# =============================================================================

class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs all requests for audit purposes.
    
    Checks config each request - can be toggled on/off at runtime.
    
    Captures:
    - Request details (method, path, headers)
    - User identification
    - Response status
    - Timing information
    """
    
    # Paths to skip detailed logging
    SKIP_PATHS = {"/health", "/docs", "/openapi.json", "/favicon.ico"}
    
    # Sensitive paths that need extra logging
    SENSITIVE_PATHS = {
        "/api/chat": AuditAction.QUERY_SEMANTIC,
        "/api/upload": AuditAction.UPLOAD_FILE,
        "/api/vacuum": AuditAction.UPLOAD_FILE,
        "/api/status/structured": AuditAction.QUERY_STRUCTURED,
        "/api/year-end/scan": AuditAction.LLM_CALL_CLOUD,
        "/api/export": AuditAction.EXPORT_DATA,
    }
    
    def __init__(self, app: ASGIApp, logger: Optional[AuditLogger] = None):
        super().__init__(app)
        self.logger = logger or get_audit_logger()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check if audit logging is enabled
        config = get_security_config()
        if not config.get("audit_logging_enabled", True):
            return await call_next(request)
        
        # Skip logging for certain paths
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)
        
        # Generate request ID
        request_id = str(uuid.uuid4())[:8]
        
        # Extract user info
        user_id = request.headers.get("X-User-ID")
        project_id = request.query_params.get("project") or request.headers.get("X-Project-ID")
        ip_address = self._get_client_ip(request)
        session_id = request.headers.get("X-Session-ID")
        
        # Determine action type
        action = self._get_action(request.url.path, request.method)
        
        # Capture timing
        start_time = time.time()
        
        # Process request
        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000
            success = response.status_code < 400
            error_msg = None if success else f"HTTP {response.status_code}"
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            success = False
            error_msg = str(e)
            raise
        
        finally:
            # Log the request
            self.logger.log(
                action=action,
                resource_type=request.url.path,
                user_id=user_id,
                project_id=project_id,
                resource_id=request_id,
                details={
                    "method": request.method,
                    "path": request.url.path,
                    "query": dict(request.query_params),
                    "duration_ms": round(duration_ms, 2),
                    "status_code": response.status_code if 'response' in dir() else 500,
                },
                ip_address=ip_address,
                session_id=session_id,
                success=success,
                error_message=error_msg
            )
        
        # Add request ID header for tracing
        response.headers["X-Request-ID"] = request_id
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP, considering proxies."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    def _get_action(self, path: str, method: str) -> AuditAction:
        """Map request to audit action type."""
        # Check sensitive paths
        for prefix, action in self.SENSITIVE_PATHS.items():
            if path.startswith(prefix):
                return action
        
        # Generic mapping by method
        if method == "GET":
            return AuditAction.VIEW_DOCUMENT
        elif method == "POST":
            return AuditAction.UPLOAD_FILE
        elif method == "DELETE":
            return AuditAction.DELETE_FILE
        elif method == "PUT" or method == "PATCH":
            return AuditAction.UPDATE_RECORD
        
        return AuditAction.VIEW_DOCUMENT


# =============================================================================
# SECURITY HEADERS MIDDLEWARE
# =============================================================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds security headers to all responses.
    
    Checks config each request - can be toggled on/off at runtime.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Check if security headers are enabled
        config = get_security_config()
        if not config.get("security_headers_enabled", True):
            return response
        
        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://api.anthropic.com https://*.supabase.co;"
        )
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Clickjacking protection
        response.headers["X-Frame-Options"] = "DENY"
        
        # XSS protection (legacy but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # HSTS (only in production)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions policy
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), payment=(), usb=()"
        )
        
        return response


# =============================================================================
# INPUT VALIDATION MIDDLEWARE
# =============================================================================

class InputValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware that validates and sanitizes request inputs.
    
    Checks config each request - can be toggled on/off at runtime.
    
    Checks for:
    - Oversized payloads
    - Malicious file names
    - Path traversal attempts
    - SQL injection patterns
    """
    
    MAX_BODY_SIZE = 50 * 1024 * 1024  # 50MB
    
    # Dangerous patterns
    PATH_TRAVERSAL = r'\.\.[\\/]'
    SQL_INJECTION = r"('|\"|\-\-|\;|\/\*|\*\/|xp_|exec\s|union\s|select\s|insert\s|update\s|delete\s|drop\s)"
    SHELL_INJECTION = r'(\||;|`|\$\(|\${)'
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        import re
        self.path_traversal_re = re.compile(self.PATH_TRAVERSAL, re.IGNORECASE)
        self.sql_injection_re = re.compile(self.SQL_INJECTION, re.IGNORECASE)
        self.shell_injection_re = re.compile(self.SHELL_INJECTION)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check if input validation is enabled
        config = get_security_config()
        if not config.get("input_validation_enabled", False):
            return await call_next(request)
        
        # Check content length
        content_length = request.headers.get("Content-Length")
        if content_length and int(content_length) > self.MAX_BODY_SIZE:
            return JSONResponse(
                status_code=413,
                content={"error": "Payload too large", "max_size_mb": 50}
            )
        
        # Check query parameters for injection
        for key, value in request.query_params.items():
            if self._is_malicious(value):
                get_audit_logger().log(
                    action=AuditAction.PROMPT_INJECTION_BLOCKED,
                    resource_type="query_param",
                    details={"param": key, "value": value[:100]},
                    success=False,
                    error_message="Potentially malicious input detected"
                )
                return JSONResponse(
                    status_code=400,
                    content={"error": "Invalid input detected", "param": key}
                )
        
        # Check path for traversal
        if self.path_traversal_re.search(request.url.path):
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid path"}
            )
        
        return await call_next(request)
    
    def _is_malicious(self, value: str) -> bool:
        """Check if value contains malicious patterns."""
        if not value:
            return False
        
        # Check for various injection patterns
        if self.path_traversal_re.search(value):
            return True
        if self.sql_injection_re.search(value):
            return True
        if self.shell_injection_re.search(value):
            return True
        
        return False


# =============================================================================
# CORS CONFIGURATION
# =============================================================================

def configure_cors(
    app: FastAPI,
    allowed_origins: Optional[List[str]] = None,
    allow_credentials: bool = True
):
    """
    Configure CORS for the FastAPI application.
    
    Args:
        app: FastAPI application
        allowed_origins: List of allowed origins (or None for defaults)
        allow_credentials: Whether to allow credentials
    """
    # Default origins for XLR8
    default_origins = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://xlr8.vercel.app",
        "https://*.vercel.app",
    ]
    
    origins = allowed_origins or default_origins
    
    # Check for wildcard (security warning)
    if "*" in origins:
        import logging
        logging.getLogger("xlr8.security").warning(
            "CORS allows wildcard origin - this is a security risk!"
        )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=allow_credentials,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-User-ID",
            "X-Project-ID",
            "X-Session-ID",
            "X-Request-ID",
        ],
        expose_headers=[
            "X-Request-ID",
            "X-RateLimit-Remaining",
        ],
    )


# =============================================================================
# DEPENDENCY INJECTION HELPERS
# =============================================================================

async def get_current_user(request: Request) -> Optional[str]:
    """
    Dependency to get current user from request.
    
    Usage:
        @router.get("/protected")
        async def protected_route(user: str = Depends(get_current_user)):
            ...
    """
    # Try Authorization header (JWT)
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        # In real implementation, decode and validate JWT
        # For now, just extract user claim
        token = auth[7:]
        # Placeholder - would decode JWT here
        return f"user_from_jwt_{token[:8]}"
    
    # Try custom header
    user_id = request.headers.get("X-User-ID")
    if user_id:
        return user_id
    
    return None


async def require_auth(request: Request) -> str:
    """
    Dependency that requires authentication.
    
    Usage:
        @router.get("/protected")
        async def protected_route(user: str = Depends(require_auth)):
            ...
    """
    user = await get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user


def rate_limit_dependency(resource: str = "api"):
    """
    Create a rate limiting dependency for specific resource.
    
    Usage:
        @router.post("/upload")
        async def upload_file(
            _: None = Depends(rate_limit_dependency("upload"))
        ):
            ...
    """
    async def check_rate_limit(request: Request):
        limiter = get_rate_limiter()
        identifier = request.headers.get("X-User-ID") or request.client.host
        
        if not limiter.allow(identifier, resource):
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded for {resource}",
                headers={"Retry-After": "60"}
            )
    
    return check_rate_limit


# =============================================================================
# MAIN SETUP FUNCTION
# =============================================================================

def setup_security(
    app: FastAPI,
    supabase_client: Any = None,
    cors_origins: Optional[List[str]] = None,
):
    """
    Set up all security middleware for a FastAPI application.
    
    SAFE MODE: Rate limiting and input validation are OFF by default.
    Enable them via Admin > Security tab or /api/security/config.
    
    Call this in your main.py after creating the FastAPI app.
    
    Args:
        app: FastAPI application
        supabase_client: Optional Supabase client for audit logging
        cors_origins: Allowed CORS origins (overrides config if provided)
    """
    # Get config
    config = get_security_config()
    
    # Use provided CORS origins or get from config
    origins = cors_origins or config.get("cors_origins", [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://xlr8.vercel.app",
    ])
    
    # Configure global security instances
    configure_security(
        supabase_client=supabase_client,
        audit_file=config.get("audit_file_path"),
        rate_limits=config.get_rate_limits_tuple() if hasattr(config, 'get_rate_limits_tuple') else None
    )
    
    # Add CORS (must be first)
    configure_cors(app, allowed_origins=origins)
    
    # Add middleware in order (last added = first executed)
    # All middleware now check config at runtime
    app.add_middleware(InputValidationMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(AuditMiddleware)
    app.add_middleware(RateLimitMiddleware)
    
    # Add config router
    from utils.security_config import create_config_router
    app.include_router(create_config_router())
    
    # Log security setup
    import logging
    logger = logging.getLogger("xlr8.security")
    logger.info("Security middleware configured (SAFE MODE):")
    logger.info(f"  - Rate limiting: {config.get('rate_limiting_enabled', False)} (toggle via Admin)")
    logger.info(f"  - Input validation: {config.get('input_validation_enabled', False)} (toggle via Admin)")
    logger.info(f"  - Audit logging: {config.get('audit_logging_enabled', True)}")
    logger.info(f"  - Security headers: {config.get('security_headers_enabled', True)}")
    logger.info(f"  - CORS origins: {origins}")


# =============================================================================
# SECURITY STATUS ENDPOINT
# =============================================================================

def create_security_router():
    """
    Create a router with security status endpoints.
    
    Returns:
        APIRouter with security endpoints
    """
    from fastapi import APIRouter
    
    router = APIRouter(prefix="/api/security", tags=["security"])
    
    @router.get("/status")
    async def security_status(request: Request):
        """Get current security status."""
        audit_logger = get_audit_logger()
        rate_limiter = get_rate_limiter()
        
        # Get user identifier
        user_id = request.headers.get("X-User-ID") or request.client.host
        
        return {
            "status": "operational",
            "rate_limits": {
                "api": rate_limiter.get_remaining(user_id, "api"),
                "upload": rate_limiter.get_remaining(user_id, "upload"),
                "llm_cloud": rate_limiter.get_remaining(user_id, "llm_cloud"),
            },
            "audit_summary": audit_logger.get_security_summary(24),
        }
    
    @router.get("/audit")
    async def audit_log(
        request: Request,
        action: Optional[str] = None,
        limit: int = 100,
        user: str = Depends(require_auth)
    ):
        """Get audit log entries (requires auth)."""
        audit_logger = get_audit_logger()
        
        # Convert action string to enum if provided
        action_enum = None
        if action:
            try:
                action_enum = AuditAction(action)
            except ValueError:
                pass
        
        entries = audit_logger.query(
            action=action_enum,
            user_id=user,
            limit=limit
        )
        
        return {
            "entries": [e.to_dict() for e in entries],
            "count": len(entries),
        }
    
    @router.post("/scan-pii")
    async def scan_pii(
        request: Request,
        text: str,
        mask: bool = True
    ):
        """Scan text for PII."""
        detector = get_pii_detector()
        result = detector.scan_text(text, mask=mask)
        
        return {
            "has_pii": result.has_pii,
            "sensitivity_level": result.sensitivity_level.name,
            "sanitized_text": result.sanitized_text if mask else None,
            "matches": [
                {
                    "type": m.pii_type.value,
                    "masked_value": m.masked_value,
                    "sensitivity": m.sensitivity.name,
                }
                for m in result.pii_matches
            ],
            "recommendations": result.recommendations,
            "scan_duration_ms": result.scan_duration_ms,
        }
    
    @router.post("/sanitize-prompt")
    async def sanitize_prompt(
        request: Request,
        prompt: str
    ):
        """Sanitize a prompt for LLM submission."""
        sanitizer = get_prompt_sanitizer()
        safe_prompt, threats = sanitizer.sanitize(prompt)
        
        return {
            "original_length": len(prompt),
            "sanitized_length": len(safe_prompt),
            "sanitized_prompt": safe_prompt,
            "threats_detected": len(threats),
            "threat_details": threats,
            "is_safe": len(threats) == 0,
        }
    
    return router


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Example: Set up security for a FastAPI app
    from fastapi import FastAPI
    
    app = FastAPI(title="XLR8 Platform")
    
    # Configure security
    setup_security(
        app,
        cors_origins=[
            "http://localhost:3000",
            "https://xlr8.vercel.app",
        ],
        rate_limits={
            "api": (100, 60),
            "upload": (5, 60),
            "llm_cloud": (20, 60),
        },
        audit_file="/tmp/xlr8_audit.log",
        enable_rate_limiting=True,
        enable_audit_logging=True,
        enable_security_headers=True,
        enable_input_validation=True,
    )
    
    # Add security router
    app.include_router(create_security_router())
    
    # Your other routers...
    @app.get("/health")
    async def health():
        return {"status": "ok"}
    
    print("Security configured! Run with: uvicorn security_middleware:app")
