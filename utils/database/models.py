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
    def get_by_name(name: str) -> Optional[Dict[str, Any]]:
        """Get project by name"""
        supabase = get_supabase()
        if not supabase:
            return None
        
        try:
            response = supabase.table('projects').select('*').eq('name', name).execute()
            return response.data[0] if response.data else None
        
        except Exception as e:
            print(f"Error getting project by name: {e}")
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
    def get_all(limit: int = 500) -> List[Dict[str, Any]]:
        """Get all documents"""
        supabase = get_supabase()
        if not supabase:
            return []
        
        try:
            response = supabase.table('documents') \
                .select('*') \
                .order('created_at', desc=True) \
                .limit(limit) \
                .execute()
            
            return response.data if response.data else []
        
        except Exception as e:
            print(f"Error getting all documents: {e}")
            return []
    
    @staticmethod
    def get_by_id(document_id: str) -> Optional[Dict[str, Any]]:
        """Get document by ID"""
        supabase = get_supabase()
        if not supabase:
            return None
        
        try:
            response = supabase.table('documents').select('*').eq('id', document_id).execute()
            return response.data[0] if response.data else None
        
        except Exception as e:
            print(f"Error getting document: {e}")
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
    
    @staticmethod
    def delete_all() -> int:
        """Delete all documents - returns count deleted"""
        supabase = get_supabase()
        if not supabase:
            return 0
        
        try:
            # Get count first
            count_response = supabase.table('documents').select('id', count='exact').execute()
            count = count_response.count or 0
            
            # Delete all
            if count > 0:
                supabase.table('documents').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
            
            return count
        
        except Exception as e:
            print(f"Error deleting all documents: {e}")
            return 0


class DocumentRegistryModel:
    """
    Document Registry - tracks ALL uploaded files in ChromaDB/DuckDB
    
    This is the source of truth for what documents SHOULD exist.
    Used by audit to detect orphans (docs in ChromaDB not in registry).
    
    IMPORTANT: Requires 'document_registry' table in Supabase.
    See create_table_sql() for schema.
    """
    
    # Storage type constants
    STORAGE_CHROMADB = 'chromadb'
    STORAGE_DUCKDB = 'duckdb'
    STORAGE_BOTH = 'both'
    
    # Usage type constants
    USAGE_RAG_KNOWLEDGE = 'rag_knowledge'      # PDFs, docs for RAG search
    USAGE_STRUCTURED_DATA = 'structured_data'  # Excel/CSV in DuckDB
    USAGE_PLAYBOOK = 'playbook'                # Year-end checklist etc.
    
    @staticmethod
    def create_table_sql() -> str:
        """Returns SQL to create the document_registry table in Supabase"""
        return """
        CREATE TABLE IF NOT EXISTS document_registry (
            id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            filename TEXT NOT NULL,
            file_type TEXT,
            storage_type TEXT DEFAULT 'chromadb',
            usage_type TEXT DEFAULT 'rag_knowledge',
            project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
            is_global BOOLEAN DEFAULT FALSE,
            chunk_count INTEGER DEFAULT 0,
            file_size INTEGER,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_doc_registry_project ON document_registry(project_id);
        CREATE INDEX IF NOT EXISTS idx_doc_registry_filename ON document_registry(filename);
        CREATE INDEX IF NOT EXISTS idx_doc_registry_global ON document_registry(is_global);
        """
    
    @staticmethod
    def register(filename: str, file_type: str = None, storage_type: str = 'chromadb',
                usage_type: str = 'rag_knowledge', project_id: str = None,
                is_global: bool = False, chunk_count: int = 0, 
                file_size: int = None, metadata: dict = None) -> Optional[Dict[str, Any]]:
        """
        Register a document in the registry.
        Call this after successfully adding to ChromaDB/DuckDB.
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
                'chunk_count': chunk_count,
                'file_size': file_size,
                'metadata': metadata or {}
            }
            
            # Remove None values to let DB use defaults
            data = {k: v for k, v in data.items() if v is not None}
            
            response = supabase.table('document_registry').insert(data).execute()
            return response.data[0] if response.data else None
        
        except Exception as e:
            print(f"Error registering document: {e}")
            return None
    
    @staticmethod
    def get_all(limit: int = 1000) -> List[Dict[str, Any]]:
        """Get all registered documents"""
        supabase = get_supabase()
        if not supabase:
            return []
        
        try:
            response = supabase.table('document_registry') \
                .select('*') \
                .order('created_at', desc=True) \
                .limit(limit) \
                .execute()
            
            return response.data if response.data else []
        
        except Exception as e:
            print(f"Error getting document registry: {e}")
            return []
    
    @staticmethod
    def get_by_project(project_id: str = None, include_global: bool = True) -> List[Dict[str, Any]]:
        """Get documents for a project (optionally including global)"""
        supabase = get_supabase()
        if not supabase:
            return []
        
        try:
            if project_id:
                if include_global:
                    # Get project docs + global docs
                    response = supabase.table('document_registry') \
                        .select('*') \
                        .or_(f'project_id.eq.{project_id},is_global.eq.true') \
                        .order('created_at', desc=True) \
                        .execute()
                else:
                    response = supabase.table('document_registry') \
                        .select('*') \
                        .eq('project_id', project_id) \
                        .order('created_at', desc=True) \
                        .execute()
            else:
                # Just global docs
                response = supabase.table('document_registry') \
                    .select('*') \
                    .eq('is_global', True) \
                    .order('created_at', desc=True) \
                    .execute()
            
            return response.data if response.data else []
        
        except Exception as e:
            print(f"Error getting documents by project: {e}")
            return []
    
    @staticmethod
    def find_by_filename(filename: str, project_id: str = None) -> Optional[Dict[str, Any]]:
        """Find a document by filename (and optionally project)"""
        supabase = get_supabase()
        if not supabase:
            return None
        
        try:
            query = supabase.table('document_registry').select('*').eq('filename', filename)
            
            if project_id:
                query = query.eq('project_id', project_id)
            
            response = query.limit(1).execute()
            return response.data[0] if response.data else None
        
        except Exception as e:
            print(f"Error finding document: {e}")
            return None
    
    @staticmethod
    def unregister(filename: str, project_id: str = None) -> bool:
        """Remove a document from the registry (call when deleting from ChromaDB)"""
        supabase = get_supabase()
        if not supabase:
            return False
        
        try:
            query = supabase.table('document_registry').delete().eq('filename', filename)
            
            if project_id:
                query = query.eq('project_id', project_id)
            else:
                query = query.is_('project_id', 'null')
            
            query.execute()
            return True
        
        except Exception as e:
            print(f"Error unregistering document: {e}")
            return False
    
    @staticmethod
    def update_chunk_count(filename: str, chunk_count: int, project_id: str = None) -> bool:
        """Update the chunk count for a document"""
        supabase = get_supabase()
        if not supabase:
            return False
        
        try:
            query = supabase.table('document_registry') \
                .update({'chunk_count': chunk_count, 'updated_at': datetime.utcnow().isoformat()}) \
                .eq('filename', filename)
            
            if project_id:
                query = query.eq('project_id', project_id)
            
            query.execute()
            return True
        
        except Exception as e:
            print(f"Error updating chunk count: {e}")
            return False
    
    @staticmethod
    def table_exists() -> bool:
        """Check if the document_registry table exists"""
        supabase = get_supabase()
        if not supabase:
            return False
        
        try:
            # Try a simple query - if table doesn't exist, this will fail
            supabase.table('document_registry').select('id').limit(1).execute()
            return True
        except Exception:
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
    
    @staticmethod
    def delete(job_id: str) -> bool:
        """Delete a job"""
        supabase = get_supabase()
        if not supabase:
            return False
        
        try:
            supabase.table('processing_jobs').delete().eq('id', job_id).execute()
            return True
        
        except Exception as e:
            print(f"Error deleting job: {e}")
            return False
    
    @staticmethod
    def delete_all() -> int:
        """Delete all jobs - returns count deleted"""
        supabase = get_supabase()
        if not supabase:
            return 0
        
        try:
            # Get count first
            count_response = supabase.table('processing_jobs').select('id', count='exact').execute()
            count = count_response.count or 0
            
            # Delete all
            if count > 0:
                supabase.table('processing_jobs').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
            
            return count
        
        except Exception as e:
            print(f"Error deleting all jobs: {e}")
            return 0
    
    @staticmethod
    def delete_older_than(days: int = 7) -> int:
        """Delete jobs older than X days - returns count deleted"""
        supabase = get_supabase()
        if not supabase:
            return 0
        
        try:
            from datetime import datetime, timedelta
            cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
            
            # Get count first
            count_response = supabase.table('processing_jobs') \
                .select('id', count='exact') \
                .lt('created_at', cutoff) \
                .execute()
            count = count_response.count or 0
            
            # Delete old jobs
            if count > 0:
                supabase.table('processing_jobs').delete().lt('created_at', cutoff).execute()
            
            return count
        
        except Exception as e:
            print(f"Error deleting old jobs: {e}")
            return 0
    
    @staticmethod
    def delete_by_date_range(start_date: str, end_date: str) -> int:
        """Delete jobs within a date range - returns count deleted"""
        supabase = get_supabase()
        if not supabase:
            return 0
        
        try:
            # Get count first
            count_response = supabase.table('processing_jobs') \
                .select('id', count='exact') \
                .gte('created_at', start_date) \
                .lte('created_at', end_date) \
                .execute()
            count = count_response.count or 0
            
            # Delete jobs in range
            if count > 0:
                supabase.table('processing_jobs') \
                    .delete() \
                    .gte('created_at', start_date) \
                    .lte('created_at', end_date) \
                    .execute()
            
            return count
        
        except Exception as e:
            print(f"Error deleting jobs by date range: {e}")
            return 0
    
    @staticmethod
    def get_recent(days: int = 7, limit: int = 100) -> List[Dict[str, Any]]:
        """Get jobs from the last X days"""
        supabase = get_supabase()
        if not supabase:
            return []
        
        try:
            from datetime import datetime, timedelta
            cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
            
            response = supabase.table('processing_jobs') \
                .select('*') \
                .gte('created_at', cutoff) \
                .order('created_at', desc=True) \
                .limit(limit) \
                .execute()
            
            return response.data if response.data else []
        
        except Exception as e:
            print(f"Error getting recent jobs: {e}")
            return []


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
