"""
Supabase Handler
Manages all Supabase database operations for XLR8
"""

from supabase import create_client, Client
from typing import Optional, Dict, List, Any
from datetime import datetime


class SupabaseHandler:
    """Handle all Supabase operations"""
    
    def __init__(self, url: str, key: str):
        """
        Initialize Supabase client
        
        Args:
            url: Supabase project URL
            key: Supabase anon/public key
        """
        self.client: Client = create_client(url, key)
    
    # ============================================================================
    # PROJECTS
    # ============================================================================
    
    def create_project(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new project
        
        Args:
            project_data: Project information dict
            
        Returns:
            Created project with ID
        """
        # Add timestamps
        project_data['created_at'] = datetime.utcnow().isoformat()
        project_data['updated_at'] = datetime.utcnow().isoformat()
        
        response = self.client.table('projects').insert(project_data).execute()
        
        if response.data:
            return response.data[0]
        else:
            raise Exception(f"Failed to create project: {response}")
    
    def get_project(self, project_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a project by ID
        
        Args:
            project_id: Project ID
            
        Returns:
            Project dict or None
        """
        response = self.client.table('projects').select("*").eq('id', project_id).execute()
        
        if response.data:
            return response.data[0]
        return None
    
    def get_project_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a project by name
        
        Args:
            name: Project name
            
        Returns:
            Project dict or None
        """
        response = self.client.table('projects').select("*").eq('name', name).execute()
        
        if response.data:
            return response.data[0]
        return None
    
    def get_all_projects(self) -> List[Dict[str, Any]]:
        """
        Get all projects
        
        Returns:
            List of project dicts
        """
        response = self.client.table('projects').select("*").order('created_at', desc=True).execute()
        return response.data if response.data else []
    
    def update_project(self, project_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a project
        
        Args:
            project_id: Project ID
            updates: Dict of fields to update
            
        Returns:
            Updated project
        """
        updates['updated_at'] = datetime.utcnow().isoformat()
        
        response = self.client.table('projects').update(updates).eq('id', project_id).execute()
        
        if response.data:
            return response.data[0]
        else:
            raise Exception(f"Failed to update project: {response}")
    
    def delete_project(self, project_id: int) -> bool:
        """
        Delete a project
        
        Args:
            project_id: Project ID
            
        Returns:
            True if successful
        """
        response = self.client.table('projects').delete().eq('id', project_id).execute()
        return True
    
    # ============================================================================
    # DOCUMENTS
    # ============================================================================
    
    def create_document(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a document record
        
        Args:
            document_data: Document metadata
            
        Returns:
            Created document with ID
        """
        document_data['created_at'] = datetime.utcnow().isoformat()
        document_data['updated_at'] = datetime.utcnow().isoformat()
        
        response = self.client.table('documents').insert(document_data).execute()
        
        if response.data:
            return response.data[0]
        else:
            raise Exception(f"Failed to create document: {response}")
    
    def get_documents_by_project(self, project_id: int) -> List[Dict[str, Any]]:
        """
        Get all documents for a project
        
        Args:
            project_id: Project ID
            
        Returns:
            List of document dicts
        """
        response = self.client.table('documents').select("*").eq('project_id', project_id).execute()
        return response.data if response.data else []
    
    def delete_document(self, document_id: int) -> bool:
        """
        Delete a document
        
        Args:
            document_id: Document ID
            
        Returns:
            True if successful
        """
        response = self.client.table('documents').delete().eq('id', document_id).execute()
        return True
    
    # ============================================================================
    # CHAT HISTORY
    # ============================================================================
    
    def save_chat_message(self, chat_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save a chat message
        
        Args:
            chat_data: Chat message data
            
        Returns:
            Created chat message with ID
        """
        chat_data['created_at'] = datetime.utcnow().isoformat()
        
        response = self.client.table('chats').insert(chat_data).execute()
        
        if response.data:
            return response.data[0]
        else:
            raise Exception(f"Failed to save chat: {response}")
    
    def get_chat_history(self, project_id: Optional[int] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get chat history
        
        Args:
            project_id: Optional project ID filter
            limit: Maximum number of messages
            
        Returns:
            List of chat messages
        """
        query = self.client.table('chats').select("*")
        
        if project_id:
            query = query.eq('project_id', project_id)
        
        response = query.order('created_at', desc=True).limit(limit).execute()
        
        # Reverse to get chronological order
        return list(reversed(response.data)) if response.data else []
    
    def delete_chat_history(self, project_id: Optional[int] = None) -> bool:
        """
        Delete chat history
        
        Args:
            project_id: Optional project ID (if None, deletes all)
            
        Returns:
            True if successful
        """
        query = self.client.table('chats').delete()
        
        if project_id:
            query = query.eq('project_id', project_id)
        
        response = query.execute()
        return True
    
    # ============================================================================
    # KNOWLEDGE BASE
    # ============================================================================
    
    def create_knowledge_item(self, knowledge_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a knowledge base item
        
        Args:
            knowledge_data: Knowledge item metadata
            
        Returns:
            Created item with ID
        """
        knowledge_data['created_at'] = datetime.utcnow().isoformat()
        knowledge_data['updated_at'] = datetime.utcnow().isoformat()
        
        response = self.client.table('knowledge_items').insert(knowledge_data).execute()
        
        if response.data:
            return response.data[0]
        else:
            raise Exception(f"Failed to create knowledge item: {response}")
    
    def get_all_knowledge_items(self) -> List[Dict[str, Any]]:
        """
        Get all knowledge base items
        
        Returns:
            List of knowledge items
        """
        response = self.client.table('knowledge_items').select("*").order('created_at', desc=True).execute()
        return response.data if response.data else []
    
    def delete_knowledge_item(self, item_id: int) -> bool:
        """
        Delete a knowledge item
        
        Args:
            item_id: Knowledge item ID
            
        Returns:
            True if successful
        """
        response = self.client.table('knowledge_items').delete().eq('id', item_id).execute()
        return True
    
    # ============================================================================
    # UTILITY METHODS
    # ============================================================================
    
    def test_connection(self) -> bool:
        """
        Test Supabase connection
        
        Returns:
            True if connection works
        """
        try:
            # Try to query projects table
            self.client.table('projects').select("id").limit(1).execute()
            return True
        except Exception as e:
            print(f"Supabase connection test failed: {e}")
            return False
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get database statistics
        
        Returns:
            Dict with counts of various entities
        """
        stats = {}
        
        try:
            # Count projects
            projects = self.client.table('projects').select("id", count='exact').execute()
            stats['projects'] = projects.count if hasattr(projects, 'count') else len(projects.data)
            
            # Count documents
            documents = self.client.table('documents').select("id", count='exact').execute()
            stats['documents'] = documents.count if hasattr(documents, 'count') else len(documents.data)
            
            # Count chats
            chats = self.client.table('chats').select("id", count='exact').execute()
            stats['chats'] = chats.count if hasattr(chats, 'count') else len(chats.data)
            
            # Count knowledge items
            knowledge = self.client.table('knowledge_items').select("id", count='exact').execute()
            stats['knowledge_items'] = knowledge.count if hasattr(knowledge, 'count') else len(knowledge.data)
            
        except Exception as e:
            print(f"Error getting stats: {e}")
        
        return stats
