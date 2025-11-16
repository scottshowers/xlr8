"""
Database Models for XLR8
CRUD operations for projects, documents, and chat history

Uses Supabase for persistent storage.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
from .supabase_client import get_supabase


class ProjectModel:
    """
    Project database operations
    
    Manages XLR8 projects in Supabase
    """
    
    @staticmethod
    def create(name: str, client_name: str = None, project_type: str = 'UKG_Pro', 
              notes: str = None) -> Optional[Dict[str, Any]]:
        """
        Create a new project
        
        Args:
            name: Project name
            client_name: Client name
            project_type: 'UKG_Pro', 'UKG_WFM', or 'Both'
            notes: Optional notes
        
        Returns:
            Created project dict or None if failed
        
        Example:
            project = ProjectModel.create(
                name="Acme Corp Implementation",
                client_name="Acme Corporation",
                project_type="Both"
            )
        """
        supabase = get_supabase()
        if not supabase:
            return None
        
        try:
            data = {
                'name': name,
                'client_name': client_name,
                'type': project_type,
                'notes': notes,
                'status': 'active'
            }
            
            response = supabase.table('projects').insert(data).execute()
            return response.data[0] if response.data else None
        
        except Exception as e:
            print(f"Error creating project: {e}")
            return None
    
    @staticmethod
    def get_all(status: str = 'active') -> List[Dict[str, Any]]:
        """
        Get all projects
        
        Args:
            status: Filter by status ('active', 'archived', 'completed', or None for all)
        
        Returns:
            List of project dicts
        
        Example:
            projects = ProjectModel.get_all()
            for project in projects:
                print(project['name'])
        """
        supabase = get_supabase()
        if not supabase:
            return []
        
        try:
            query = supabase.table('projects').select('*').order('created_at', desc=True)
            
            if status:
                query = query.eq('status', status)
            
            response = query.execute()
            return response.data if response.data else []
        
        except Exception as e:
            print(f"Error getting projects: {e}")
            return []
    
    @staticmethod
    def get_by_id(project_id: str) -> Optional[Dict[str, Any]]:
        """
        Get project by ID
        
        Args:
            project_id: Project UUID
        
        Returns:
            Project dict or None
        
        Example:
            project = ProjectModel.get_by_id("123e4567-e89b-12d3-a456-426614174000")
        """
        supabase = get_supabase()
        if not supabase:
            return None
        
        try:
            response = supabase.table('projects').select('*').eq('id', project_id).execute()
            return response.data[0] if response.data else None
        
        except Exception as e:
            print(f"Error getting project: {e}")
            return None
    
    @staticmethod
    def update(project_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Update project
        
        Args:
            project_id: Project UUID
            **kwargs: Fields to update (name, client_name, type, notes, status)
        
        Returns:
            Updated project dict or None
        
        Example:
            updated = ProjectModel.update(
                project_id="123...",
                status="completed",
                notes="Implementation finished!"
            )
        """
        supabase = get_supabase()
        if not supabase:
            return None
        
        try:
            response = supabase.table('projects').update(kwargs).eq('id', project_id).execute()
            return response.data[0] if response.data else None
        
        except Exception as e:
            print(f"Error updating project: {e}")
            return None
    
    @staticmethod
    def delete(project_id: str) -> bool:
        """
        Delete project (and all associated data via CASCADE)
        
        Args:
            project_id: Project UUID
        
        Returns:
            True if deleted, False if failed
        
        Example:
            if ProjectModel.delete("123..."):
                print("Project deleted")
        """
        supabase = get_supabase()
        if not supabase:
            return False
        
        try:
            supabase.table('projects').delete().eq('id', project_id).execute()
            return True
        
        except Exception as e:
            print(f"Error deleting project: {e}")
            return False


class DocumentModel:
    """
    Document database operations
    
    Manages documents in Supabase
    """
    
    @staticmethod
    def create(project_id: str, name: str, category: str, 
              content: str = None, file_type: str = None,
              file_size: int = None, metadata: dict = None) -> Optional[Dict[str, Any]]:
        """
        Create a new document
        
        Args:
            project_id: Associated project UUID
            name: Document name
            category: Document category
            content: Document text content
            file_type: File extension (e.g., 'pdf', 'docx')
            file_size: Size in bytes
            metadata: Additional metadata dict
        
        Returns:
            Created document dict or None
        
        Example:
            doc = DocumentModel.create(
                project_id="123...",
                name="Payroll_Config.pdf",
                category="UKG_Standards",
                content="Full text...",
                file_type="pdf",
                file_size=1024000
            )
        """
        supabase = get_supabase()
        if not supabase:
            return None
        
        try:
            data = {
                'project_id': project_id,
                'name': name,
                'category': category,
                'content': content,
                'file_type': file_type,
                'file_size': file_size,
                'metadata': metadata or {}
            }
            
            response = supabase.table('documents').insert(data).execute()
            return response.data[0] if response.data else None
        
        except Exception as e:
            print(f"Error creating document: {e}")
            return None
    
    @staticmethod
    def get_by_project(project_id: str, category: str = None) -> List[Dict[str, Any]]:
        """
        Get documents for a project
        
        Args:
            project_id: Project UUID
            category: Optional category filter
        
        Returns:
            List of document dicts
        
        Example:
            docs = DocumentModel.get_by_project("123...", category="UKG_Standards")
        """
        supabase = get_supabase()
        if not supabase:
            return []
        
        try:
            query = supabase.table('documents').select('*').eq('project_id', project_id).order('created_at', desc=True)
            
            if category:
                query = query.eq('category', category)
            
            response = query.execute()
            return response.data if response.data else []
        
        except Exception as e:
            print(f"Error getting documents: {e}")
            return []
    
    @staticmethod
    def delete(document_id: str) -> bool:
        """
        Delete document
        
        Args:
            document_id: Document UUID
        
        Returns:
            True if deleted
        """
        supabase = get_supabase()
        if not supabase:
            return False
        
        try:
            supabase.table('documents').delete().eq('id', document_id).execute()
            return True
        
        except Exception as e:
            print(f"Error deleting document: {e}")
            return False


class ChatHistoryModel:
    """
    Chat history database operations
    
    Manages chat messages in Supabase
    """
    
    @staticmethod
    def add_message(project_id: str, session_id: str, role: str,
                   content: str, sources: list = None, metadata: dict = None) -> Optional[Dict[str, Any]]:
        """
        Add a chat message
        
        Args:
            project_id: Associated project UUID (can be None)
            session_id: Chat session ID
            role: 'user' or 'assistant'
            content: Message content
            sources: List of source documents used
            metadata: Additional metadata
        
        Returns:
            Created message dict or None
        
        Example:
            msg = ChatHistoryModel.add_message(
                project_id="123...",
                session_id="session_abc",
                role="user",
                content="How do I configure earnings?"
            )
        """
        supabase = get_supabase()
        if not supabase:
            return None
        
        try:
            data = {
                'project_id': project_id,
                'session_id': session_id,
                'role': role,
                'content': content,
                'sources': sources or [],
                'metadata': metadata or {}
            }
            
            response = supabase.table('chat_history').insert(data).execute()
            return response.data[0] if response.data else None
        
        except Exception as e:
            print(f"Error adding chat message: {e}")
            return None
    
    @staticmethod
    def get_by_session(session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get chat history for a session
        
        Args:
            session_id: Chat session ID
            limit: Maximum messages to return
        
        Returns:
            List of message dicts (chronological order)
        
        Example:
            history = ChatHistoryModel.get_by_session("session_abc")
            for msg in history:
                print(f"{msg['role']}: {msg['content']}")
        """
        supabase = get_supabase()
        if not supabase:
            return []
        
        try:
            response = supabase.table('chat_history') \
                .select('*') \
                .eq('session_id', session_id) \
                .order('created_at', desc=False) \
                .limit(limit) \
                .execute()
            
            return response.data if response.data else []
        
        except Exception as e:
            print(f"Error getting chat history: {e}")
            return []
    
    @staticmethod
    def get_by_project(project_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get all chat history for a project
        
        Args:
            project_id: Project UUID
            limit: Maximum messages
        
        Returns:
            List of message dicts
        
        Example:
            history = ChatHistoryModel.get_by_project("123...")
        """
        supabase = get_supabase()
        if not supabase:
            return []
        
        try:
            response = supabase.table('chat_history') \
                .select('*') \
                .eq('project_id', project_id) \
                .order('created_at', desc=True) \
                .limit(limit) \
                .execute()
            
            return response.data if response.data else []
        
        except Exception as e:
            print(f"Error getting chat history: {e}")
            return []
    
    @staticmethod
    def delete_session(session_id: str) -> bool:
        """
        Delete all messages in a session
        
        Args:
            session_id: Session to delete
        
        Returns:
            True if deleted
        
        Example:
            ChatHistoryModel.delete_session("session_abc")
        """
        supabase = get_supabase()
        if not supabase:
            return False
        
        try:
            supabase.table('chat_history').delete().eq('session_id', session_id).execute()
            return True
        
        except Exception as e:
            print(f"Error deleting session: {e}")
            return False


# Convenience functions
def create_project(name: str, **kwargs) -> Optional[Dict]:
    """Shortcut to create project"""
    return ProjectModel.create(name, **kwargs)


def get_projects() -> List[Dict]:
    """Shortcut to get all projects"""
    return ProjectModel.get_all()


def add_chat_message(session_id: str, role: str, content: str, **kwargs) -> Optional[Dict]:
    """Shortcut to add chat message"""
    project_id = kwargs.pop('project_id', None)
    return ChatHistoryModel.add_message(project_id, session_id, role, content, **kwargs)


def get_chat_history(session_id: str) -> List[Dict]:
    """Shortcut to get chat history"""
    return ChatHistoryModel.get_by_session(session_id)
