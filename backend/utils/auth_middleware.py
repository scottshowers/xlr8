"""
XLR8 Auth Middleware
====================
JWT validation, role extraction, and permission checking.

Usage:
    from backend.utils.auth_middleware import require_permission, get_current_user

    @router.get("/admin-only")
    async def admin_endpoint(user: User = Depends(require_permission("ops_center"))):
        return {"message": f"Hello {user.email}"}

Author: XLR8 Platform
Date: December 8, 2025
"""

import os
import jwt
from typing import Optional, List
from functools import wraps
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime
import httpx

# Supabase config
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "")

security = HTTPBearer(auto_error=False)


# =============================================================================
# MODELS
# =============================================================================

class User(BaseModel):
    """Authenticated user with role and permissions."""
    id: str
    email: str
    full_name: Optional[str] = None
    role: str = "customer"
    project_id: Optional[str] = None
    permissions: List[str] = []
    mfa_enabled: bool = False


class AuthError(HTTPException):
    """Authentication error."""
    def __init__(self, detail: str):
        super().__init__(status_code=401, detail=detail)


class ForbiddenError(HTTPException):
    """Authorization error - user lacks permission."""
    def __init__(self, detail: str = "You don't have permission to access this resource"):
        super().__init__(status_code=403, detail=detail)


# =============================================================================
# TOKEN VALIDATION
# =============================================================================

async def decode_jwt(token: str) -> dict:
    """Decode and validate Supabase JWT."""
    try:
        # Supabase uses HS256 with JWT secret
        if SUPABASE_JWT_SECRET:
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated"
            )
        else:
            # Fallback: decode without verification (DEV ONLY)
            payload = jwt.decode(token, options={"verify_signature": False})
        
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise AuthError(f"Invalid token: {str(e)}")


async def get_user_profile(user_id: str) -> dict:
    """Fetch user profile from Supabase."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        # Return mock profile for dev
        return {
            "id": user_id,
            "email": "dev@xlr8.com",
            "full_name": "Dev User",
            "role": "admin",
            "project_id": None,
            "mfa_enabled": False,
        }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{user_id}&select=*",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
            }
        )
        
        if response.status_code == 200:
            profiles = response.json()
            if profiles:
                return profiles[0]
        
        # Return default if not found
        return {
            "id": user_id,
            "email": "unknown",
            "role": "customer",
            "project_id": None,
            "mfa_enabled": False,
        }


async def get_role_permissions(role: str) -> List[str]:
    """Fetch permissions for a role from Supabase."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        # Return all permissions for dev
        if role == "admin":
            return [
                "chat", "upload", "playbooks", "vacuum", "export",
                "projects_all", "projects_own", "delete_data",
                "ops_center", "security_settings", "user_management",
                "role_permissions", "data_model"
            ]
        elif role == "consultant":
            return [
                "chat", "upload", "playbooks", "vacuum", "export",
                "projects_all", "projects_own", "data_model"
            ]
        else:
            return ["chat", "export", "projects_own"]
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/role_permissions?role=eq.{role}&allowed=eq.true&select=permission",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
            }
        )
        
        if response.status_code == 200:
            rows = response.json()
            return [row["permission"] for row in rows]
        
        return []


# =============================================================================
# DEPENDENCIES
# =============================================================================

async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[User]:
    """
    Get current authenticated user from JWT.
    Returns None if not authenticated (for optional auth).
    """
    # Check for token in header
    token = None
    if credentials:
        token = credentials.credentials
    
    # Also check cookie (for SSR/browser requests)
    if not token:
        token = request.cookies.get("sb-access-token")
    
    if not token:
        return None
    
    try:
        # Decode JWT
        payload = await decode_jwt(token)
        user_id = payload.get("sub")
        
        if not user_id:
            return None
        
        # Get profile and permissions
        profile = await get_user_profile(user_id)
        permissions = await get_role_permissions(profile.get("role", "customer"))
        
        return User(
            id=user_id,
            email=profile.get("email", ""),
            full_name=profile.get("full_name"),
            role=profile.get("role", "customer"),
            project_id=profile.get("project_id"),
            permissions=permissions,
            mfa_enabled=profile.get("mfa_enabled", False),
        )
    except AuthError:
        return None


async def require_auth(
    user: Optional[User] = Depends(get_current_user)
) -> User:
    """Require authenticated user."""
    if not user:
        raise AuthError("Authentication required")
    return user


def require_permission(permission: str):
    """
    Dependency factory for permission checking.
    
    Usage:
        @router.get("/admin")
        async def admin_only(user: User = Depends(require_permission("ops_center"))):
            ...
    """
    async def check_permission(user: User = Depends(require_auth)) -> User:
        if permission not in user.permissions:
            raise ForbiddenError(f"Permission '{permission}' required")
        return user
    return check_permission


def require_role(role: str):
    """
    Dependency factory for role checking.
    
    Usage:
        @router.get("/admin")
        async def admin_only(user: User = Depends(require_role("admin"))):
            ...
    """
    async def check_role(user: User = Depends(require_auth)) -> User:
        if user.role != role:
            raise ForbiddenError(f"Role '{role}' required")
        return user
    return check_role


def require_any_role(*roles: str):
    """
    Dependency factory for multiple acceptable roles.
    
    Usage:
        @router.get("/staff")
        async def staff_only(user: User = Depends(require_any_role("admin", "consultant"))):
            ...
    """
    async def check_roles(user: User = Depends(require_auth)) -> User:
        if user.role not in roles:
            raise ForbiddenError(f"One of roles {roles} required")
        return user
    return check_roles


# =============================================================================
# PROJECT ACCESS HELPERS
# =============================================================================

async def check_project_access(user: User, project_id: str) -> bool:
    """Check if user can access a specific project."""
    # Admins and consultants can access all projects
    if "projects_all" in user.permissions:
        return True
    
    # Customers can only access their assigned project
    if "projects_own" in user.permissions:
        return user.project_id == project_id
    
    return False


def require_project_access(project_id_param: str = "project_id"):
    """
    Dependency factory for project-level access control.
    
    Usage:
        @router.get("/projects/{project_id}/data")
        async def get_project_data(
            project_id: str,
            user: User = Depends(require_project_access("project_id"))
        ):
            ...
    """
    async def check_access(request: Request, user: User = Depends(require_auth)) -> User:
        project_id = request.path_params.get(project_id_param)
        if project_id and not await check_project_access(user, project_id):
            raise ForbiddenError("You don't have access to this project")
        return user
    return check_access


# =============================================================================
# PERMISSION CONSTANTS (for reference)
# =============================================================================

class Permissions:
    """Permission constants."""
    # Features
    CHAT = "chat"
    UPLOAD = "upload"
    PLAYBOOKS = "playbooks"
    VACUUM = "vacuum"
    EXPORT = "export"
    DATA_MODEL = "data_model"
    
    # Data access
    PROJECTS_ALL = "projects_all"
    PROJECTS_OWN = "projects_own"
    DELETE_DATA = "delete_data"
    
    # Admin
    OPS_CENTER = "ops_center"
    SECURITY_SETTINGS = "security_settings"
    USER_MANAGEMENT = "user_management"
    ROLE_PERMISSIONS = "role_permissions"
