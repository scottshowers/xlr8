"""
Supabase Client for Persistent Project Storage
===============================================

Replaces session_state.projects with Supabase database storage.
Projects will NEVER disappear again!

Author: HCMPACT
Version: 1.0
"""

from supabase import create_client, Client
import os
from typing import Dict, List, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class SupabaseProjectManager:
    """Manages projects in Supabase PostgreSQL database"""
    
    def __init__(self):
        """Initialize Supabase client"""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_KEY environment variables must be set. "
                "Add them in Railway dashboard."
            )
        
        self.client: Client = create_client(supabase_url, supabase_key)
        logger.info("Supabase Project Manager initialized")
    
    def create_project(self, name: str, customer: str = "", 
                      start_date: str = None, status: str = "active",
                      metadata: Dict = None) -> Dict:
        """
        Create a new project in Supabase.
        
        Args:
            name: Project name (must be unique)
            customer: Customer/company name
            start_date: Project start date (YYYY-MM-DD)
            status: active, on_hold, or completed
            metadata: Additional custom fields as JSON
            
        Returns:
            Created project dict
        """
        data = {
            "name": name,
            "customer": customer or "",
            "start_date": start_date,
            "status": status,
            "metadata": metadata or {}
        }
        
        try:
            result = self.client.table("projects").insert(data).execute()
            logger.info(f"✅ Created project: {name}")
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"❌ Failed to create project '{name}': {e}")
            raise
    
    def get_all_projects(self, status: str = None) -> List[Dict]:
        """
        Get all projects, optionally filtered by status.
        
        Args:
            status: Filter by status (active, on_hold, completed) or None for all
            
        Returns:
            List of project dicts
        """
        try:
            query = self.client.table("projects").select("*")
            
            if status:
                query = query.eq("status", status)
            
            result = query.order("created_at", desc=True).execute()
            return result.data
        except Exception as e:
            logger.error(f"Failed to get projects: {e}")
            return []
    
    def get_project(self, name: str) -> Optional[Dict]:
        """
        Get a specific project by name.
        
        Args:
            name: Project name
            
        Returns:
            Project dict or None
        """
        try:
            result = self.client.table("projects")\
                .select("*")\
                .eq("name", name)\
                .execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to get project '{name}': {e}")
            return None
    
    def get_active_project(self) -> Optional[Dict]:
        """
        Get the currently active project.
        
        Returns:
            Active project dict or None
        """
        try:
            result = self.client.table("projects")\
                .select("*")\
                .eq("is_active", True)\
                .execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to get active project: {e}")
            return None
    
    def set_active_project(self, name: str) -> bool:
        """
        Set a project as active (deactivates all others).
        Only ONE project can be active at a time.
        
        Args:
            name: Project name to activate
            
        Returns:
            True if successful
        """
        try:
            # First, deactivate ALL projects
            self.client.table("projects")\
                .update({"is_active": False})\
                .neq("name", "__dummy__")\
                .execute()
            
            # Then activate this project
            result = self.client.table("projects")\
                .update({"is_active": True, "updated_at": datetime.utcnow().isoformat()})\
                .eq("name", name)\
                .execute()
            
            logger.info(f"✅ Activated project: {name}")
            return len(result.data) > 0
        except Exception as e:
            logger.error(f"❌ Failed to activate project '{name}': {e}")
            return False
    
    def deactivate_all_projects(self) -> bool:
        """
        Deactivate all projects (no active project).
        
        Returns:
            True if successful
        """
        try:
            self.client.table("projects")\
                .update({"is_active": False})\
                .neq("name", "__dummy__")\
                .execute()
            logger.info("✅ Deactivated all projects")
            return True
        except Exception as e:
            logger.error(f"Failed to deactivate projects: {e}")
            return False
    
    def update_project(self, name: str, updates: Dict) -> Dict:
        """
        Update a project (can rename by including 'name' in updates).
        
        Args:
            name: Current project name
            updates: Dict of fields to update (can include new 'name')
            
        Returns:
            Updated project dict
        """
        try:
            # Always update the updated_at timestamp
            updates["updated_at"] = datetime.utcnow().isoformat()
            
            result = self.client.table("projects")\
                .update(updates)\
                .eq("name", name)\
                .execute()
            
            new_name = updates.get('name', name)
            logger.info(f"✅ Updated project: {name} → {new_name}")
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"❌ Failed to update project '{name}': {e}")
            raise
    
    def delete_project(self, name: str) -> bool:
        """
        Delete a project from Supabase.
        
        Args:
            name: Project name to delete
            
        Returns:
            True if successful
        """
        try:
            self.client.table("projects")\
                .delete()\
                .eq("name", name)\
                .execute()
            logger.info(f"✅ Deleted project: {name}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to delete project '{name}': {e}")
            return False
    
    def rename_project(self, old_name: str, new_name: str) -> bool:
        """
        Rename a project. This will propagate to all documents tagged with this project_id.
        
        NOTE: You'll need to manually update ChromaDB metadata for existing documents.
        
        Args:
            old_name: Current project name
            new_name: New project name
            
        Returns:
            True if successful
        """
        try:
            result = self.client.table("projects")\
                .update({
                    "name": new_name,
                    "updated_at": datetime.utcnow().isoformat()
                })\
                .eq("name", old_name)\
                .execute()
            
            if result.data:
                logger.info(f"✅ Renamed project: {old_name} → {new_name}")
                logger.warning(
                    f"⚠️  NOTE: Existing documents in ChromaDB still tagged with '{old_name}'. "
                    f"You may need to re-upload documents or manually update ChromaDB metadata."
                )
                return True
            return False
        except Exception as e:
            logger.error(f"❌ Failed to rename project '{old_name}': {e}")
            return False
