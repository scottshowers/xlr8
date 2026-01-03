"""
XLR8 Auth Router
================
User management, role assignment, and permissions API.

Endpoints:
- GET  /api/auth/me              - Get current user
- GET  /api/auth/permissions     - Get current user's permissions
- GET  /api/auth/users           - List all users (admin only)
- POST /api/auth/users           - Create user (admin only)
- PATCH /api/auth/users/{id}     - Update user (admin only)
- DELETE /api/auth/users/{id}    - Delete user (admin only)
- GET  /api/auth/roles           - List all roles
- GET  /api/auth/role-permissions - Get permission grid
- PATCH /api/auth/role-permissions - Update permission grid (admin only)

Author: XLR8 Platform
Date: December 8, 2025
"""

import os
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import httpx

# Import auth middleware
from backend.utils.auth_middleware import (
    User, require_auth, require_permission, require_role,
    get_current_user, Permissions
)

router = APIRouter(tags=["auth"])

# Supabase config
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")  # For admin operations


# =============================================================================
# MODELS
# =============================================================================

class UserCreate(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: str = "customer"
    project_id: Optional[str] = None
    mfa_method: str = "totp"  # 'totp' or 'sms'


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    project_id: Optional[str] = None
    mfa_method: Optional[str] = None


class PermissionUpdate(BaseModel):
    role: str
    permission: str
    allowed: bool


class BulkPermissionUpdate(BaseModel):
    updates: List[PermissionUpdate]


# =============================================================================
# CURRENT USER ENDPOINTS
# =============================================================================

@router.get("/me")
async def get_me(user: User = Depends(require_auth)) -> Dict[str, Any]:
    """Get current authenticated user."""
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "project_id": user.project_id,
        "mfa_enabled": user.mfa_enabled,
    }


@router.get("/permissions")
async def get_my_permissions(user: User = Depends(require_auth)) -> Dict[str, Any]:
    """Get current user's permissions."""
    return {
        "role": user.role,
        "permissions": user.permissions,
    }


# =============================================================================
# USER MANAGEMENT (Admin Only)
# =============================================================================

@router.get("/users")
async def list_users(
    user: User = Depends(require_permission(Permissions.USER_MANAGEMENT))
) -> List[Dict[str, Any]]:
    """List all users (admin only)."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        # Dev mode - return mock users
        return [
            {"id": "1", "email": "admin@xlr8.com", "full_name": "Admin User", "role": "admin", "project_id": None},
            {"id": "2", "email": "consultant@xlr8.com", "full_name": "Consultant User", "role": "consultant", "project_id": None},
            {"id": "3", "email": "customer@acme.com", "full_name": "Customer User", "role": "customer", "project_id": "proj-123"},
        ]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/profiles?select=*&order=created_at.desc",
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            }
        )
        
        if response.status_code == 200:
            return response.json()
        
        raise HTTPException(500, "Failed to fetch users")


@router.post("/users")
async def create_user(
    data: UserCreate,
    user: User = Depends(require_permission(Permissions.USER_MANAGEMENT))
) -> Dict[str, Any]:
    """Create a new user (admin only)."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise HTTPException(500, "Supabase not configured for user creation")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Create auth user via Supabase Admin API
        response = await client.post(
            f"{SUPABASE_URL}/auth/v1/admin/users",
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "email": data.email,
                "password": data.password,
                "email_confirm": True,  # Auto-confirm email
                "user_metadata": {
                    "full_name": data.full_name,
                    "role": data.role,
                },
            }
        )
        
        if response.status_code not in [200, 201]:
            error = response.json()
            raise HTTPException(400, f"Failed to create user: {error.get('message', 'Unknown error')}")
        
        new_user = response.json()
        user_id = new_user.get("id")
        
        # Update profile with role, phone, mfa_method and project_id
        await client.patch(
            f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{user_id}",
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "role": data.role,
                "project_id": data.project_id,
                "full_name": data.full_name,
                "phone": data.phone,
                "mfa_method": data.mfa_method,
            }
        )
        
        return {
            "status": "created",
            "user_id": user_id,
            "email": data.email,
            "role": data.role,
            "mfa_method": data.mfa_method,
        }


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    data: UserUpdate,
    user: User = Depends(require_permission(Permissions.USER_MANAGEMENT))
) -> Dict[str, Any]:
    """Update a user's profile (admin only)."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return {"status": "updated", "user_id": user_id}
    
    update_data = {}
    if data.full_name is not None:
        update_data["full_name"] = data.full_name
    if data.phone is not None:
        update_data["phone"] = data.phone
    if data.role is not None:
        if data.role not in ["admin", "consultant", "customer"]:
            raise HTTPException(400, "Invalid role")
        update_data["role"] = data.role
    if data.project_id is not None:
        update_data["project_id"] = data.project_id
    if data.mfa_method is not None:
        if data.mfa_method not in ["totp", "sms"]:
            raise HTTPException(400, "Invalid MFA method")
        update_data["mfa_method"] = data.mfa_method
    
    if not update_data:
        raise HTTPException(400, "No fields to update")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.patch(
            f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{user_id}",
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
            json=update_data
        )
        
        if response.status_code == 200:
            updated = response.json()
            return {"status": "updated", "user": updated[0] if updated else None}
        
        raise HTTPException(500, "Failed to update user")


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    user: User = Depends(require_permission(Permissions.USER_MANAGEMENT))
) -> Dict[str, Any]:
    """Delete a user (admin only)."""
    # Prevent self-deletion
    if user_id == user.id:
        raise HTTPException(400, "Cannot delete yourself")
    
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return {"status": "deleted", "user_id": user_id}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Delete from Supabase Auth
        response = await client.delete(
            f"{SUPABASE_URL}/auth/v1/admin/users/{user_id}",
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            }
        )
        
        if response.status_code in [200, 204]:
            return {"status": "deleted", "user_id": user_id}
        
        raise HTTPException(500, "Failed to delete user")


# =============================================================================
# ROLES & PERMISSIONS
# =============================================================================

@router.get("/roles")
async def list_roles() -> List[Dict[str, Any]]:
    """List all available roles."""
    return [
        {
            "id": "admin",
            "label": "Administrator",
            "description": "Full system access including user management and security settings",
        },
        {
            "id": "consultant",
            "label": "Consultant",
            "description": "Access to all work features across all projects",
        },
        {
            "id": "customer",
            "label": "Customer",
            "description": "Limited access to their assigned project only",
        },
    ]


@router.get("/role-permissions")
async def get_role_permissions(
    user: Optional[User] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get the full permission grid."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        # Dev mode - return default grid
        return {
            "permissions": [
                "chat", "upload", "playbooks", "vacuum", "export", "data_model",
                "projects_all", "projects_own", "delete_data",
                "ops_center", "security_settings", "user_management", "role_permissions"
            ],
            "roles": ["admin", "consultant", "customer"],
            "grid": {
                "admin": {
                    "chat": True, "upload": True, "playbooks": True, "vacuum": True,
                    "export": True, "data_model": True, "projects_all": True,
                    "projects_own": True, "delete_data": True, "ops_center": True,
                    "security_settings": True, "user_management": True, "role_permissions": True,
                },
                "consultant": {
                    "chat": True, "upload": True, "playbooks": True, "vacuum": True,
                    "export": True, "data_model": True, "projects_all": True,
                    "projects_own": True, "delete_data": False, "ops_center": False,
                    "security_settings": False, "user_management": False, "role_permissions": False,
                },
                "customer": {
                    "chat": True, "upload": False, "playbooks": False, "vacuum": False,
                    "export": True, "data_model": False, "projects_all": False,
                    "projects_own": True, "delete_data": False, "ops_center": False,
                    "security_settings": False, "user_management": False, "role_permissions": False,
                },
            },
            "labels": {
                "chat": "Chat",
                "upload": "Upload Documents",
                "playbooks": "Playbooks",
                "vacuum": "Vacuum Extractor",
                "export": "Export Data",
                "data_model": "Data Model",
                "projects_all": "All Projects",
                "projects_own": "Own Project",
                "delete_data": "Delete Data",
                "ops_center": "Ops Center",
                "security_settings": "Security Settings",
                "user_management": "User Management",
                "role_permissions": "Role Permissions",
            },
            "categories": {
                "Features": ["chat", "upload", "playbooks", "vacuum", "export", "data_model"],
                "Data Access": ["projects_all", "projects_own", "delete_data"],
                "Admin": ["ops_center", "security_settings", "user_management", "role_permissions"],
            },
        }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/role_permissions?select=*",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
            }
        )
        
        if response.status_code != 200:
            raise HTTPException(500, "Failed to fetch permissions")
        
        rows = response.json()
        
        # Build grid from rows
        grid = {"admin": {}, "consultant": {}, "customer": {}}
        permissions = set()
        
        for row in rows:
            role = row["role"]
            perm = row["permission"]
            allowed = row["allowed"]
            permissions.add(perm)
            if role in grid:
                grid[role][perm] = allowed
        
        return {
            "permissions": sorted(list(permissions)),
            "roles": ["admin", "consultant", "customer"],
            "grid": grid,
            "labels": {
                "chat": "Chat",
                "upload": "Upload Documents",
                "playbooks": "Playbooks",
                "vacuum": "Vacuum Extractor",
                "export": "Export Data",
                "data_model": "Data Model",
                "projects_all": "All Projects",
                "projects_own": "Own Project",
                "delete_data": "Delete Data",
                "ops_center": "Ops Center",
                "security_settings": "Security Settings",
                "user_management": "User Management",
                "role_permissions": "Role Permissions",
            },
            "categories": {
                "Features": ["chat", "upload", "playbooks", "vacuum", "export", "data_model"],
                "Data Access": ["projects_all", "projects_own", "delete_data"],
                "Admin": ["ops_center", "security_settings", "user_management", "role_permissions"],
            },
        }


@router.patch("/role-permissions")
async def update_role_permissions(
    data: BulkPermissionUpdate,
    user: User = Depends(require_permission(Permissions.ROLE_PERMISSIONS))
) -> Dict[str, Any]:
    """Update role permissions (admin only)."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return {"status": "updated", "count": len(data.updates)}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        updated_count = 0
        
        for update in data.updates:
            # Upsert permission
            response = await client.post(
                f"{SUPABASE_URL}/rest/v1/role_permissions",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "resolution=merge-duplicates",
                },
                json={
                    "role": update.role,
                    "permission": update.permission,
                    "allowed": update.allowed,
                }
            )
            
            if response.status_code in [200, 201]:
                updated_count += 1
        
        return {"status": "updated", "count": updated_count}
