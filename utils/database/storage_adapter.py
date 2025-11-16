"""
Storage Adapter for XLR8
Unified interface for session state and Supabase

This adapter automatically uses Supabase if enabled, otherwise falls back to session state.
Makes it easy to switch between storage backends!
"""

import streamlit as st
from typing import List, Dict, Any, Optional
from config import AppConfig
import uuid


class ProjectStorage:
    """
    Project storage adapter
    
    Automatically uses Supabase or session state based on config
    """
    
    @staticmethod
    def create(name: str, **kwargs) -> Dict[str, Any]:
        """
        Create a project
        
        Args:
            name: Project name
            **kwargs: Other project fields
        
        Returns:
            Project dict
        
        Example:
            project = ProjectStorage.create(
                name="Acme Corp",
                client_name="Acme",
                project_type="Both"
            )
        """
        if AppConfig.use_supabase():
            # Use Supabase
            from utils.database.models import ProjectModel
            project = ProjectModel.create(name, **kwargs)
            if project:
                return project
            # Fall back to session if Supabase fails
        
        # Use session state
        if 'projects' not in st.session_state:
            st.session_state.projects = {}
        
        project_id = str(uuid.uuid4())
        project = {
            'id': project_id,
            'name': name,
            'client_name': kwargs.get('client_name'),
            'type': kwargs.get('project_type', 'UKG_Pro'),
            'notes': kwargs.get('notes'),
            'status': 'active'
        }
        
        st.session_state.projects[name] = project
        return project
    
    @staticmethod
    def get_all() -> List[Dict[str, Any]]:
        """
        Get all projects
        
        Returns:
            List of project dicts
        
        Example:
            projects = ProjectStorage.get_all()
        """
        if AppConfig.use_supabase():
            # Use Supabase
            from utils.database.models import ProjectModel
            projects = ProjectModel.get_all()
            if projects:
                return projects
            # Fall back if empty
        
        # Use session state
        if 'projects' not in st.session_state:
            st.session_state.projects = {}
        
        return list(st.session_state.projects.values())
    
    @staticmethod
    def get_by_name(name: str) -> Optional[Dict[str, Any]]:
        """
        Get project by name
        
        Args:
            name: Project name
        
        Returns:
            Project dict or None
        """
        if AppConfig.use_supabase():
            # With Supabase, search by name
            from utils.database.models import ProjectModel
            projects = ProjectModel.get_all()
            for project in projects:
                if project['name'] == name:
                    return project
        
        # Session state
        projects = st.session_state.get('projects', {})
        return projects.get(name)
    
    @staticmethod
    def update(project_id: str = None, name: str = None, **kwargs) -> bool:
        """
        Update project
        
        Args:
            project_id: Project ID (for Supabase)
            name: Project name (for session state)
            **kwargs: Fields to update
        
        Returns:
            True if updated
        """
        if AppConfig.use_supabase() and project_id:
            from utils.database.models import ProjectModel
            result = ProjectModel.update(project_id, **kwargs)
            return result is not None
        
        # Session state
        if name and 'projects' in st.session_state and name in st.session_state.projects:
            st.session_state.projects[name].update(kwargs)
            return True
        
        return False
    
    @staticmethod
    def delete(project_id: str = None, name: str = None) -> bool:
        """
        Delete project
        
        Args:
            project_id: Project ID (for Supabase)
            name: Project name (for session state)
        
        Returns:
            True if deleted
        """
        if AppConfig.use_supabase() and project_id:
            from utils.database.models import ProjectModel
            return ProjectModel.delete(project_id)
        
        # Session state
        if name and 'projects' in st.session_state and name in st.session_state.projects:
            del st.session_state.projects[name]
            return True
        
        return False


class ChatStorage:
    """
    Chat history storage adapter
    
    Automatically uses Supabase or session state
    """
    
    @staticmethod
    def add_message(role: str, content: str, sources: list = None, 
                   session_id: str = None, project_id: str = None) -> Dict[str, Any]:
        """
        Add a chat message
        
        Args:
            role: 'user' or 'assistant'
            content: Message content
            sources: Source documents
            session_id: Chat session ID
            project_id: Associated project
        
        Returns:
            Message dict
        
        Example:
            ChatStorage.add_message(
                role="user",
                content="How do I configure earnings?",
                session_id="abc123"
            )
        """
        message = {
            'role': role,
            'content': content,
            'sources': sources or []
        }
        
        if AppConfig.use_supabase():
            # Save to Supabase
            from utils.database.models import ChatHistoryModel
            if not session_id:
                # Generate session ID if not provided
                if 'chat_session_id' not in st.session_state:
                    st.session_state.chat_session_id = str(uuid.uuid4())
                session_id = st.session_state.chat_session_id
            
            db_message = ChatHistoryModel.add_message(
                project_id=project_id,
                session_id=session_id,
                role=role,
                content=content,
                sources=sources
            )
            if db_message:
                message['id'] = db_message['id']
        
        # Also keep in session state for current session
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        
        st.session_state.chat_history.append(message)
        return message
    
    @staticmethod
    def get_history(session_id: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get chat history
        
        Args:
            session_id: Session to load (for Supabase)
            limit: Maximum messages
        
        Returns:
            List of message dicts
        
        Example:
            history = ChatStorage.get_history()
        """
        if AppConfig.use_supabase() and session_id:
            # Load from Supabase
            from utils.database.models import ChatHistoryModel
            history = ChatHistoryModel.get_by_session(session_id, limit)
            if history:
                return history
        
        # Session state
        return st.session_state.get('chat_history', [])
    
    @staticmethod
    def clear_history(session_id: str = None):
        """
        Clear chat history
        
        Args:
            session_id: Session to clear (for Supabase)
        
        Example:
            ChatStorage.clear_history()
        """
        if AppConfig.use_supabase() and session_id:
            from utils.database.models import ChatHistoryModel
            ChatHistoryModel.delete_session(session_id)
        
        # Clear session state
        if 'chat_history' in st.session_state:
            st.session_state.chat_history = []


class DocumentStorage:
    """
    Document storage adapter
    
    Automatically uses Supabase or session state
    """
    
    @staticmethod
    def save(project_id: str, name: str, category: str, content: str = None, **kwargs) -> Dict[str, Any]:
        """
        Save a document
        
        Args:
            project_id: Associated project
            name: Document name
            category: Document category
            content: Document content
            **kwargs: Additional fields
        
        Returns:
            Document dict
        """
        if AppConfig.use_supabase():
            from utils.database.models import DocumentModel
            doc = DocumentModel.create(
                project_id=project_id,
                name=name,
                category=category,
                content=content,
                **kwargs
            )
            if doc:
                return doc
        
        # Session state fallback
        if 'doc_library' not in st.session_state:
            st.session_state.doc_library = []
        
        doc = {
            'id': str(uuid.uuid4()),
            'name': name,
            'category': category,
            'content': content,
            **kwargs
        }
        
        st.session_state.doc_library.append(doc)
        return doc
    
    @staticmethod
    def get_by_project(project_id: str, category: str = None) -> List[Dict[str, Any]]:
        """
        Get documents for a project
        
        Args:
            project_id: Project ID
            category: Optional category filter
        
        Returns:
            List of document dicts
        """
        if AppConfig.use_supabase():
            from utils.database.models import DocumentModel
            docs = DocumentModel.get_by_project(project_id, category)
            if docs:
                return docs
        
        # Session state
        all_docs = st.session_state.get('doc_library', [])
        if category:
            return [d for d in all_docs if d.get('category') == category]
        return all_docs


# Convenience exports
__all__ = ['ProjectStorage', 'ChatStorage', 'DocumentStorage']
