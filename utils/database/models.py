"""
Database Models for XLR8
CRUD operations for projects, documents, and chat history

Uses Supabase for persistent storage.
FIXED: Column names now match actual Supabase schema
- 'customer' not 'client_name'
- 'type' stored in metadata JSON
- 'notes' stored in metadata JSON
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
    def create(name: str, client_name: str = None, project_type: str = 'Implementation', 
              notes: str = None, product: str = None) -> Optional[Dict[str, Any]]:
        """
        Create a new project
        
        Args:
            name: Project name (Customer AR#)
            client_name: Client name (Company Name, maps to 'customer' column)
            project_type: 'Implementation', 'Post Launch Support', or 'Assessment/Analysis' (stored in metadata)
            notes: Optional notes (stored in metadata)
            product: 'UKG Pro', 'WFM Dimensions', or 'UKG Ready' (stored in metadata)
        
        Returns:
            Created project dict or None if failed
        """
        supabase = get_supabase()
        if not supabase:
            return None
        
        try:
            # ✅ FIXED: Match actual Supabase schema columns
            data = {
                'name': name,
                'customer': client_name or '',  # ✅ Column is 'customer' not 'client_name'
                'status': 'active',
                'metadata': {                    # ✅ type, notes & product go in metadata JSON
                    'type': project_type,
                    'notes': notes,
                    'product': product
                }
            }
            
            response = supabase.table('projects').insert(data).execute()
            return response.data[0] if response.data else None
        
        except Exception as e:
            print(f"Error creating project: {e}")
            return None
    
    @staticmethod
    def get_all(status: str = 'active') -> List[Dict[str, Any]]:
        """Get all projects"""
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
        """Get project by ID"""
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
        """Update project"""
        supabase = get_supabase()
        if not supabase:
            return None
        
        try:
            kwargs['updated_at'] = datetime.utcnow().isoformat()
            response = supabase.table('projects').update(kwargs).eq('id', project_id).execute()
            return response.data[0] if response.data else None
        
        except Exception as e:
            print(f"Error updating project: {e}")
            return None
    
    @staticmethod
    def delete(project_id: str) -> bool:
        """Delete project"""
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
    """Document database operations"""
    
    @staticmethod
    def create(project_id: str, name: str, category: str, 
              content: str = None, file_type: str = None,
              file_size: int = None, metadata: dict = None) -> Optional[Dict[str, Any]]:
        """Create a new document"""
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
        """Get documents for a project"""
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
        """Delete document"""
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
    """Chat history database operations"""
    
    @staticmethod
    def add_message(project_id: str, session_id: str, role: str,
                   content: str, sources: list = None, metadata: dict = None) -> Optional[Dict[str, Any]]:
        """Add a chat message"""
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
        """Get chat history for a session"""
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
        """Get all chat history for a project"""
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
        """Delete all messages in a session"""
        supabase = get_supabase()
        if not supabase:
            return False
        
        try:
            supabase.table('chat_history').delete().eq('session_id', session_id).execute()
            return True
        
        except Exception as e:
            print(f"Error deleting session: {e}")
            return False


class ProcessingJobModel:
    """Processing job database operations"""
    
    @staticmethod
    def create(job_type: str, project_id: str = None, filename: str = None,
              input_data: dict = None) -> Optional[Dict[str, Any]]:
        """Create a new processing job"""
        supabase = get_supabase()
        if not supabase:
            return None
        
        try:
            data = {
                'job_type': job_type,
                'project_id': project_id,
                'status': 'queued',
                'progress': {'percent': 0, 'step': 'Queued...'},
                'input_data': input_data or {'filename': filename}
            }
            
            response = supabase.table('processing_jobs').insert(data).execute()
            return response.data[0] if response.data else None
        
        except Exception as e:
            print(f"Error creating job: {e}")
            return None
    
    @staticmethod
    def update_progress(job_id: str, percent: int, step: str) -> bool:
        """Update job progress"""
        supabase = get_supabase()
        if not supabase:
            return False
        
        try:
            data = {
                'status': 'processing',
                'progress': {'percent': percent, 'step': step},
                'updated_at': datetime.utcnow().isoformat()
            }
            
            if percent == 0:
                data['started_at'] = datetime.utcnow().isoformat()
            
            supabase.table('processing_jobs').update(data).eq('id', job_id).execute()
            return True
        
        except Exception as e:
            print(f"Error updating job progress: {e}")
            return False
    
    @staticmethod
    def complete(job_id: str, result_data: dict = None) -> bool:
        """Mark job as completed"""
        supabase = get_supabase()
        if not supabase:
            return False
        
        try:
            data = {
                'status': 'completed',
                'progress': {'percent': 100, 'step': 'Complete'},
                'result_data': result_data or {},
                'completed_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            supabase.table('processing_jobs').update(data).eq('id', job_id).execute()
            return True
        
        except Exception as e:
            print(f"Error completing job: {e}")
            return False
    
    @staticmethod
    def fail(job_id: str, error_message: str) -> bool:
        """Mark job as failed"""
        supabase = get_supabase()
        if not supabase:
            return False
        
        try:
            data = {
                'status': 'failed',
                'error_message': error_message,
                'completed_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            supabase.table('processing_jobs').update(data).eq('id', job_id).execute()
            return True
        
        except Exception as e:
            print(f"Error failing job: {e}")
            return False
    
    @staticmethod
    def get_all(limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent jobs"""
        supabase = get_supabase()
        if not supabase:
            return []
        
        try:
            response = supabase.table('processing_jobs') \
                .select('*') \
                .order('created_at', desc=True) \
                .limit(limit) \
                .execute()
            
            return response.data if response.data else []
        
        except Exception as e:
            print(f"Error getting jobs: {e}")
            return []
    
    @staticmethod
    def get_by_id(job_id: str) -> Optional[Dict[str, Any]]:
        """Get job by ID"""
        supabase = get_supabase()
        if not supabase:
            return None
        
        try:
            response = supabase.table('processing_jobs').select('*').eq('id', job_id).execute()
            return response.data[0] if response.data else None
        
        except Exception as e:
            print(f"Error getting job: {e}")
            return None


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


def create_job(job_type: str, **kwargs) -> Optional[Dict]:
    """Shortcut to create job"""
    return ProcessingJobModel.create(job_type, **kwargs)


def update_job_progress(job_id: str, percent: int, step: str) -> bool:
    """Shortcut to update job progress"""
    return ProcessingJobModel.update_progress(job_id, percent, step)


def complete_job(job_id: str, result_data: dict = None) -> bool:
    """Shortcut to complete job"""
    return ProcessingJobModel.complete(job_id, result_data)


def fail_job(job_id: str, error: str) -> bool:
    """Shortcut to fail job"""
    return ProcessingJobModel.fail(job_id, error)


class DocumentRegistryModel:
    """
    Document Registry - Central source of truth for all uploaded files.
    
    Tracks:
    - Where files are stored (DuckDB, ChromaDB, filesystem)
    - What type of file it is (structured data, RAG knowledge, playbook source, etc.)
    - Project association (or Global)
    - Original file preservation status
    
    This enables features to find the right data without guessing.
    """
    
    # Storage type constants
    STORAGE_DUCKDB = 'duckdb'
    STORAGE_CHROMADB = 'chromadb'
    STORAGE_FILESYSTEM = 'filesystem'
    
    # Usage type constants
    USAGE_STRUCTURED_DATA = 'structured_data'      # Excel/CSV data tables
    USAGE_RAG_KNOWLEDGE = 'rag_knowledge'          # PDF/DOCX for semantic search
    USAGE_PLAYBOOK_SOURCE = 'playbook_source'      # Year-End Checklist, etc.
    USAGE_TEMPLATE = 'template'                    # Config templates
    USAGE_CUSTOMER_DATA = 'customer_data'          # Employee loads, etc.
    
    @staticmethod
    def register(
        filename: str,
        file_type: str,
        storage_type: str,
        usage_type: str,
        project_id: str = None,
        is_global: bool = False,
        original_file_path: str = None,
        duckdb_tables: List[str] = None,
        chromadb_collection: str = None,
        chunk_count: int = None,
        row_count: int = None,
        sheet_count: int = None,
        metadata: dict = None
    ) -> Optional[Dict[str, Any]]:
        """
        Register a document in the central registry.
        
        Args:
            filename: Original filename
            file_type: Extension (xlsx, pdf, docx, csv, etc.)
            storage_type: Where data is stored (duckdb, chromadb, filesystem)
            usage_type: How the file is used (structured_data, rag_knowledge, playbook_source, etc.)
            project_id: Associated project UUID (None for global)
            is_global: True if this is a global/universal document
            original_file_path: Path to preserved original file (if kept)
            duckdb_tables: List of DuckDB table names (if structured)
            chromadb_collection: ChromaDB collection name (if RAG)
            chunk_count: Number of chunks (if RAG)
            row_count: Total rows (if structured)
            sheet_count: Number of sheets (if Excel)
            metadata: Additional metadata JSON
        
        Returns:
            Created registry entry or None if failed
        """
        supabase = get_supabase()
        if not supabase:
            return None
        
        try:
            data = {
                'filename': filename,
                'file_type': file_type,
                'storage_type': storage_type,
                'usage_type': usage_type,
                'project_id': project_id,
                'is_global': is_global,
                'original_file_path': original_file_path,
                'duckdb_tables': duckdb_tables or [],
                'chromadb_collection': chromadb_collection,
                'chunk_count': chunk_count,
                'row_count': row_count,
                'sheet_count': sheet_count,
                'metadata': metadata or {}
            }
            
            response = supabase.table('document_registry').insert(data).execute()
            return response.data[0] if response.data else None
        
        except Exception as e:
            print(f"Error registering document: {e}")
            return None
    
    @staticmethod
    def find(
        usage_type: str = None,
        storage_type: str = None,
        project_id: str = None,
        is_global: bool = None,
        filename_contains: str = None,
        file_type: str = None
    ) -> List[Dict[str, Any]]:
        """
        Find documents in the registry.
        
        Args:
            usage_type: Filter by usage type
            storage_type: Filter by storage type
            project_id: Filter by project
            is_global: Filter by global flag
            filename_contains: Filter by filename substring (case-insensitive)
            file_type: Filter by file extension
        
        Returns:
            List of matching registry entries
        """
        supabase = get_supabase()
        if not supabase:
            return []
        
        try:
            query = supabase.table('document_registry').select('*')
            
            if usage_type:
                query = query.eq('usage_type', usage_type)
            if storage_type:
                query = query.eq('storage_type', storage_type)
            if project_id:
                query = query.eq('project_id', project_id)
            if is_global is not None:
                query = query.eq('is_global', is_global)
            if file_type:
                query = query.eq('file_type', file_type)
            if filename_contains:
                query = query.ilike('filename', f'%{filename_contains}%')
            
            response = query.order('created_at', desc=True).execute()
            return response.data if response.data else []
        
        except Exception as e:
            print(f"Error finding documents: {e}")
            return []
    
    @staticmethod
    def find_playbook_source(playbook_type: str = 'year-end') -> Optional[Dict[str, Any]]:
        """
        Find the source file for a specific playbook.
        
        Args:
            playbook_type: Type of playbook ('year-end', etc.)
        
        Returns:
            Registry entry for the playbook source file, or None
        """
        supabase = get_supabase()
        if not supabase:
            return None
        
        try:
            # Look for playbook source files
            results = DocumentRegistryModel.find(
                usage_type=DocumentRegistryModel.USAGE_PLAYBOOK_SOURCE,
                is_global=True
            )
            
            if not results:
                # Fallback: search by filename pattern in global structured data
                results = DocumentRegistryModel.find(
                    storage_type=DocumentRegistryModel.STORAGE_DUCKDB,
                    is_global=True
                )
            
            # Filter by playbook type keywords
            keywords = {
                'year-end': ['year-end', 'yearend', 'year_end', 'checklist'],
            }.get(playbook_type, [playbook_type])
            
            for entry in results:
                filename_lower = entry.get('filename', '').lower()
                if any(kw in filename_lower for kw in keywords):
                    return entry
            
            return None
        
        except Exception as e:
            print(f"Error finding playbook source: {e}")
            return None
    
    @staticmethod
    def get_by_filename(filename: str, project_id: str = None) -> Optional[Dict[str, Any]]:
        """Get registry entry by exact filename"""
        supabase = get_supabase()
        if not supabase:
            return None
        
        try:
            query = supabase.table('document_registry').select('*').eq('filename', filename)
            
            if project_id:
                query = query.eq('project_id', project_id)
            
            response = query.execute()
            return response.data[0] if response.data else None
        
        except Exception as e:
            print(f"Error getting document: {e}")
            return None
    
    @staticmethod
    def update(registry_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Update a registry entry"""
        supabase = get_supabase()
        if not supabase:
            return None
        
        try:
            kwargs['updated_at'] = datetime.utcnow().isoformat()
            response = supabase.table('document_registry').update(kwargs).eq('id', registry_id).execute()
            return response.data[0] if response.data else None
        
        except Exception as e:
            print(f"Error updating document registry: {e}")
            return None
    
    @staticmethod
    def delete(registry_id: str) -> bool:
        """Delete a registry entry"""
        supabase = get_supabase()
        if not supabase:
            return False
        
        try:
            supabase.table('document_registry').delete().eq('id', registry_id).execute()
            return True
        
        except Exception as e:
            print(f"Error deleting document registry: {e}")
            return False
    
    @staticmethod
    def get_all_global() -> List[Dict[str, Any]]:
        """Get all global documents"""
        return DocumentRegistryModel.find(is_global=True)
    
    @staticmethod
    def get_by_project(project_id: str) -> List[Dict[str, Any]]:
        """Get all documents for a project"""
        return DocumentRegistryModel.find(project_id=project_id)
