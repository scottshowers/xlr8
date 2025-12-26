"""
Error Response Utilities
========================

Provides consistent, secure error responses across the API.

Key features:
- Logs full error details internally
- Returns sanitized errors to clients (no stack traces, internal paths)
- Consistent JSON structure
- Optional error codes for client-side handling

Usage:
    from utils.error_utils import api_error, safe_error_detail

    # In an endpoint:
    except Exception as e:
        raise api_error(500, "Database operation failed", e)

    # Or for simple cases:
    except Exception as e:
        raise HTTPException(500, detail=safe_error_detail(e, "Processing failed"))

Author: XLR8 Team
Version: 1.0.0 - Week 3 Hardening
"""

import logging
import traceback
import re
from typing import Optional, Any
from fastapi import HTTPException

logger = logging.getLogger(__name__)


# Patterns to sanitize from error messages
SANITIZE_PATTERNS = [
    (r'/home/\w+/', '/home/***/'),  # Home directories
    (r'/app/[^\s]+\.py', '***'),     # Full file paths
    (r'/data/[^\s]+', '/data/***'),  # Data paths
    (r'password[=:][^\s&]+', 'password=***'),  # Passwords in URLs
    (r'api[_-]?key[=:][^\s&]+', 'api_key=***'),  # API keys
    (r'token[=:][^\s&]+', 'token=***'),  # Tokens
    (r'Bearer [^\s]+', 'Bearer ***'),  # Bearer tokens
    (r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '***.***.***.***'),  # IP addresses
]


def sanitize_error_message(message: str) -> str:
    """
    Remove sensitive information from error messages.
    
    Sanitizes:
    - File paths
    - Home directories
    - Passwords/API keys
    - IP addresses
    """
    if not message:
        return message
    
    sanitized = str(message)
    for pattern, replacement in SANITIZE_PATTERNS:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
    
    return sanitized


def safe_error_detail(
    exception: Exception,
    default_message: str = "An error occurred",
    include_type: bool = True
) -> str:
    """
    Create a safe error message from an exception.
    
    Args:
        exception: The caught exception
        default_message: Fallback message if exception message is empty
        include_type: Whether to include the exception type name
    
    Returns:
        Sanitized error message safe for client display
    """
    error_msg = str(exception) if str(exception) else default_message
    sanitized = sanitize_error_message(error_msg)
    
    # Limit length to prevent huge error messages
    if len(sanitized) > 500:
        sanitized = sanitized[:500] + "..."
    
    if include_type and str(exception):
        error_type = type(exception).__name__
        # Don't include generic Exception type
        if error_type not in ('Exception', 'BaseException'):
            return f"{error_type}: {sanitized}"
    
    return sanitized


def api_error(
    status_code: int,
    message: str,
    exception: Optional[Exception] = None,
    error_code: Optional[str] = None,
    log_level: str = "error"
) -> HTTPException:
    """
    Create a consistent API error response.
    
    Args:
        status_code: HTTP status code
        message: User-friendly error message
        exception: Optional exception to log (full details logged internally)
        error_code: Optional error code for client-side handling (e.g., "AUTH_001")
        log_level: Logging level ("error", "warning", "info")
    
    Returns:
        HTTPException with consistent structure
    
    Example:
        try:
            result = db.execute(query)
        except Exception as e:
            raise api_error(500, "Failed to fetch data", e, "DB_QUERY_FAILED")
    """
    # Log full details internally
    if exception:
        log_func = getattr(logger, log_level, logger.error)
        log_func(f"API Error ({status_code}): {message}")
        log_func(f"Exception: {type(exception).__name__}: {exception}")
        if log_level == "error":
            logger.error(traceback.format_exc())
    
    # Build response detail
    detail: Any
    if error_code:
        detail = {
            "message": message,
            "error_code": error_code
        }
    else:
        detail = message
    
    return HTTPException(status_code=status_code, detail=detail)


# =============================================================================
# COMMON ERROR RESPONSES
# =============================================================================

def not_found(resource: str, identifier: str = None) -> HTTPException:
    """Standard 404 response."""
    if identifier:
        return HTTPException(status_code=404, detail=f"{resource} '{identifier}' not found")
    return HTTPException(status_code=404, detail=f"{resource} not found")


def bad_request(message: str) -> HTTPException:
    """Standard 400 response."""
    return HTTPException(status_code=400, detail=message)


def unauthorized(message: str = "Authentication required") -> HTTPException:
    """Standard 401 response."""
    return HTTPException(status_code=401, detail=message)


def forbidden(message: str = "Permission denied") -> HTTPException:
    """Standard 403 response."""
    return HTTPException(status_code=403, detail=message)


def service_unavailable(service: str) -> HTTPException:
    """Standard 503 response for unavailable services."""
    return HTTPException(status_code=503, detail=f"{service} is currently unavailable")


def internal_error(
    message: str = "An internal error occurred",
    exception: Optional[Exception] = None
) -> HTTPException:
    """Standard 500 response with logging."""
    return api_error(500, message, exception)


# =============================================================================
# EXCEPTION HANDLER FOR FASTAPI
# =============================================================================

async def global_exception_handler(request, exc: Exception):
    """
    Global exception handler for FastAPI.
    
    Add to main.py:
        from utils.error_utils import global_exception_handler
        app.add_exception_handler(Exception, global_exception_handler)
    """
    from fastapi.responses import JSONResponse
    
    logger.error(f"Unhandled exception: {type(exc).__name__}: {exc}")
    logger.error(traceback.format_exc())
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal error occurred. Please try again later.",
            "error_code": "INTERNAL_ERROR"
        }
    )
