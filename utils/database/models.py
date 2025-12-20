"""
Database Models for XLR8
CRUD operations for projects, documents, chat history, suppressions, and entity config

Uses Supabase for persistent storage.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import hashlib
import re
from .supabase_client import get_supabase


class ProjectModel:
    """Project database operations"""
    
    @staticmethod
    def create(name: str, client_name: str = None, project_type: str = 'Implementation', 
              notes: str = None, product: str = None) -> Optional[Dict[str, Any]]:
        """Create a new project"""
        supabase = get_supabase()
        if not supabase:
            return None
        
        try:
            data = {
                'name': name,
                'customer': client_name or '',
                'status': 'active',
                'metadata': {
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
            count_response = supabase.table('documents').select('id', count='exact').execute()
            count = count_response.count or 0
            if count > 0:
                supabase.table('documents').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
            return count
        except Exception as e:
            print(f"Error deleting all documents: {e}")
            return 0


class DocumentRegistryModel:
    """
    Document Registry - THE SOURCE OF TRUTH for all uploaded files.
    
    Tracks ALL files in ChromaDB and/or DuckDB with unified metadata.
    All components should query this registry instead of backends directly.
    """
    
    # Storage types
    STORAGE_CHROMADB = 'chromadb'
    STORAGE_DUCKDB = 'duckdb'
    STORAGE_BOTH = 'both'
    
    # Usage types
    USAGE_RAG_KNOWLEDGE = 'rag_knowledge'      # Unstructured docs for RAG
    USAGE_STRUCTURED_DATA = 'structured_data'  # Excel/CSV/PDF tables
    USAGE_PLAYBOOK = 'playbook'                # Playbook-related data
    USAGE_PLAYBOOK_SOURCE = 'playbook_source'  # Playbook definition doc (e.g., Year-End Checklist)
    USAGE_TEMPLATE = 'template'                # Reference library templates
    
    @staticmethod
    def create_table_sql() -> str:
        """Returns SQL to create the document_registry table"""
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
        """Register a document in the registry"""
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
        """Get documents for a project"""
        supabase = get_supabase()
        if not supabase:
            return []
        
        try:
            if project_id:
                if include_global:
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
        """Find a document by filename"""
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
        """
        Remove a document from the registry.
        
        If project_id is provided, deletes only the matching entry.
        If project_id is None, first tries to find by filename alone,
        then deletes any matching entry (project-specific or global).
        """
        supabase = get_supabase()
        if not supabase:
            return False
        
        try:
            if project_id:
                # Delete specific project entry
                result = supabase.table('document_registry').delete().eq(
                    'filename', filename
                ).eq('project_id', project_id).execute()
            else:
                # No project_id - delete by filename only
                # This catches both project-specific (where we don't know the ID)
                # and global entries
                result = supabase.table('document_registry').delete().eq(
                    'filename', filename
                ).execute()
            
            # Check if anything was deleted
            deleted_count = len(result.data) if result.data else 0
            return deleted_count > 0 or True  # Return True even if nothing found (idempotent)
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
        """Delete all jobs"""
        supabase = get_supabase()
        if not supabase:
            return 0
        
        try:
            count_response = supabase.table('processing_jobs').select('id', count='exact').execute()
            count = count_response.count or 0
            if count > 0:
                supabase.table('processing_jobs').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
            return count
        except Exception as e:
            print(f"Error deleting all jobs: {e}")
            return 0
    
    @staticmethod
    def delete_older_than(days: int = 7) -> int:
        """Delete jobs older than X days"""
        supabase = get_supabase()
        if not supabase:
            return 0
        
        try:
            from datetime import timedelta
            cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
            count_response = supabase.table('processing_jobs').select('id', count='exact').lt('created_at', cutoff).execute()
            count = count_response.count or 0
            if count > 0:
                supabase.table('processing_jobs').delete().lt('created_at', cutoff).execute()
            return count
        except Exception as e:
            print(f"Error deleting old jobs: {e}")
            return 0
    
    @staticmethod
    def get_recent(days: int = 7, limit: int = 100) -> List[Dict[str, Any]]:
        """Get jobs from the last X days"""
        supabase = get_supabase()
        if not supabase:
            return []
        
        try:
            from datetime import timedelta
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


# =============================================================================
# FINDING SUPPRESSION MODEL
# =============================================================================

class FindingSuppressionModel:
    """
    Finding Suppression - Manage acknowledged/suppressed findings
    
    Playbook-agnostic: works for year_end, post_live, assessment, etc.
    """
    
    @staticmethod
    def _hash_finding(finding_text: str) -> str:
        """Create normalized hash of finding text for matching"""
        normalized = finding_text.lower().strip()
        normalized = re.sub(r'\d+\.?\d*%?', 'N', normalized)  # Replace numbers
        normalized = re.sub(r'\s+', ' ', normalized)  # Collapse whitespace
        return hashlib.sha256(normalized.encode()).hexdigest()[:32]
    
    @staticmethod
    def create(
        project_id: str,
        playbook_type: str,
        suppression_type: str,
        reason: str,
        action_id: str = None,
        finding_text: str = None,
        pattern: str = None,
        category: str = None,
        document_filter: str = None,
        state_filter: List[str] = None,
        keyword_filter: List[str] = None,
        fein_filter: List[str] = None,
        notes: str = None,
        expires_at: str = None,
        created_by: str = None
    ) -> Optional[Dict[str, Any]]:
        """Create a suppression rule"""
        supabase = get_supabase()
        if not supabase:
            return None
        
        try:
            finding_hash = None
            if finding_text and suppression_type in ('suppress', 'acknowledge'):
                finding_hash = FindingSuppressionModel._hash_finding(finding_text)
            
            data = {
                'project_id': project_id,
                'playbook_type': playbook_type,
                'action_id': action_id,
                'suppression_type': suppression_type,
                'finding_hash': finding_hash,
                'pattern': pattern,
                'category': category,
                'document_filter': document_filter,
                'state_filter': state_filter,
                'keyword_filter': keyword_filter,
                'fein_filter': fein_filter,
                'reason': reason,
                'notes': notes,
                'expires_at': expires_at,
                'created_by': created_by,
                'is_active': True
            }
            data = {k: v for k, v in data.items() if v is not None}
            
            response = supabase.table('finding_suppressions').insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error creating suppression: {e}")
            return None
    
    @staticmethod
    def get_active_rules(project_id: str, playbook_type: str, action_id: str = None) -> List[Dict[str, Any]]:
        """Get active suppression rules for a project/playbook"""
        supabase = get_supabase()
        if not supabase:
            return []
        
        try:
            query = supabase.table('finding_suppressions') \
                .select('*') \
                .eq('project_id', project_id) \
                .eq('playbook_type', playbook_type) \
                .eq('is_active', True)
            
            response = query.execute()
            rules = response.data if response.data else []
            
            # Filter by action scope
            now = datetime.utcnow().isoformat()
            filtered = []
            for rule in rules:
                # Skip expired
                if rule.get('expires_at') and rule['expires_at'] < now:
                    continue
                # Skip if action-specific and doesn't match
                if rule.get('action_id') and action_id and rule['action_id'] != action_id:
                    continue
                filtered.append(rule)
            
            return filtered
        except Exception as e:
            print(f"Error getting suppression rules: {e}")
            return []
    
    @staticmethod
    def check_finding(
        project_id: str,
        playbook_type: str,
        finding_text: str,
        action_id: str = None,
        document_name: str = None,
        state: str = None,
        fein: str = None
    ) -> Optional[Dict[str, Any]]:
        """Check if a finding matches any suppression rule. Returns matching rule or None."""
        rules = FindingSuppressionModel.get_active_rules(project_id, playbook_type, action_id)
        if not rules:
            return None
        
        finding_hash = FindingSuppressionModel._hash_finding(finding_text)
        finding_lower = finding_text.lower()
        
        for rule in rules:
            # Check FEIN filter
            if rule.get('fein_filter') and fein:
                if fein not in rule['fein_filter']:
                    continue
            
            # Check hash match
            if rule.get('finding_hash') and rule['finding_hash'] == finding_hash:
                FindingSuppressionModel._record_match(rule['id'])
                return rule
            
            # Check pattern match
            if rule.get('pattern'):
                try:
                    if re.search(rule['pattern'], finding_text, re.IGNORECASE):
                        FindingSuppressionModel._record_match(rule['id'])
                        return rule
                except re.error:
                    pass
            
            # Check document filter
            if rule.get('document_filter') and document_name:
                if rule['document_filter'].lower() in document_name.lower():
                    FindingSuppressionModel._record_match(rule['id'])
                    return rule
            
            # Check state filter
            if rule.get('state_filter') and state:
                if state.upper() in [s.upper() for s in rule['state_filter']]:
                    FindingSuppressionModel._record_match(rule['id'])
                    return rule
            
            # Check keyword filter
            if rule.get('keyword_filter'):
                if any(kw.lower() in finding_lower for kw in rule['keyword_filter']):
                    FindingSuppressionModel._record_match(rule['id'])
                    return rule
        
        return None
    
    @staticmethod
    def _record_match(rule_id: str) -> None:
        """Record that a rule matched (increment counter)"""
        supabase = get_supabase()
        if not supabase:
            return
        
        try:
            supabase.rpc('increment_suppression_match', {'rule_id': rule_id}).execute()
        except Exception:
            try:
                supabase.table('finding_suppressions') \
                    .update({
                        'match_count': supabase.table('finding_suppressions')
                            .select('match_count').eq('id', rule_id).execute().data[0].get('match_count', 0) + 1,
                        'last_matched_at': datetime.utcnow().isoformat()
                    }) \
                    .eq('id', rule_id) \
                    .execute()
            except Exception:
                pass
    
    @staticmethod
    def deactivate(rule_id: str) -> bool:
        """Soft-delete a rule"""
        supabase = get_supabase()
        if not supabase:
            return False
        
        try:
            supabase.table('finding_suppressions') \
                .update({'is_active': False, 'updated_at': datetime.utcnow().isoformat()}) \
                .eq('id', rule_id) \
                .execute()
            return True
        except Exception as e:
            print(f"Error deactivating suppression: {e}")
            return False
    
    @staticmethod
    def reactivate(rule_id: str) -> bool:
        """Reactivate a soft-deleted rule"""
        supabase = get_supabase()
        if not supabase:
            return False
        
        try:
            supabase.table('finding_suppressions') \
                .update({'is_active': True, 'updated_at': datetime.utcnow().isoformat()}) \
                .eq('id', rule_id) \
                .execute()
            return True
        except Exception as e:
            print(f"Error reactivating suppression: {e}")
            return False
    
    @staticmethod
    def get_by_project(project_id: str, playbook_type: str, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """Get all rules for a project"""
        supabase = get_supabase()
        if not supabase:
            return []
        
        try:
            query = supabase.table('finding_suppressions') \
                .select('*') \
                .eq('project_id', project_id) \
                .eq('playbook_type', playbook_type) \
                .order('created_at', desc=True)
            
            if not include_inactive:
                query = query.eq('is_active', True)
            
            response = query.execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Error getting suppressions by project: {e}")
            return []
    
    @staticmethod
    def get_stats(project_id: str, playbook_type: str) -> Dict[str, Any]:
        """Get suppression statistics"""
        supabase = get_supabase()
        if not supabase:
            return {}
        
        try:
            response = supabase.table('finding_suppressions') \
                .select('*') \
                .eq('project_id', project_id) \
                .eq('playbook_type', playbook_type) \
                .execute()
            
            rules = response.data or []
            active = [r for r in rules if r.get('is_active')]
            
            return {
                'total_rules': len(rules),
                'active_rules': len(active),
                'inactive_rules': len(rules) - len(active),
                'total_matches': sum(r.get('match_count', 0) for r in rules),
                'by_type': {
                    'acknowledge': len([r for r in active if r.get('suppression_type') == 'acknowledge']),
                    'suppress': len([r for r in active if r.get('suppression_type') == 'suppress']),
                    'pattern': len([r for r in active if r.get('suppression_type') == 'pattern'])
                }
            }
        except Exception as e:
            print(f"Error getting suppression stats: {e}")
            return {}


# =============================================================================
# ENTITY CONFIGURATION MODEL
# =============================================================================

class EntityConfigModel:
    """
    Entity Configuration - Track which FEINs/BNs are being analyzed per project
    
    Playbook-agnostic: works for year_end, post_live, assessment, etc.
    """
    
    @staticmethod
    def save(
        project_id: str,
        playbook_type: str,
        analysis_scope: str,
        selected_entities: List[str],
        primary_entity: str = None,
        country_mode: str = 'us_only',
        detected_entities: Dict = None
    ) -> Optional[Dict[str, Any]]:
        """Save entity configuration"""
        supabase = get_supabase()
        if not supabase:
            return None
        
        try:
            data = {
                'project_id': project_id,
                'playbook_type': playbook_type,
                'analysis_scope': analysis_scope,
                'selected_entities': selected_entities,
                'primary_entity': primary_entity,
                'country_mode': country_mode,
                'configured_at': datetime.utcnow().isoformat()
            }
            
            response = supabase.table('project_entity_config') \
                .upsert(data, on_conflict='project_id,playbook_type') \
                .execute()
            
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error saving entity config: {e}")
            return None
    
    @staticmethod
    def get(project_id: str, playbook_type: str) -> Optional[Dict[str, Any]]:
        """Get entity configuration"""
        supabase = get_supabase()
        if not supabase:
            return None
        
        try:
            response = supabase.table('project_entity_config') \
                .select('*') \
                .eq('project_id', project_id) \
                .eq('playbook_type', playbook_type) \
                .execute()
            
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error getting entity config: {e}")
            return None
    
    @staticmethod
    def delete(project_id: str, playbook_type: str) -> bool:
        """Delete entity configuration"""
        supabase = get_supabase()
        if not supabase:
            return False
        
        try:
            supabase.table('project_entity_config') \
                .delete() \
                .eq('project_id', project_id) \
                .eq('playbook_type', playbook_type) \
                .execute()
            return True
        except Exception as e:
            print(f"Error deleting entity config: {e}")
            return False


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_project(name: str, **kwargs) -> Optional[Dict]:
    return ProjectModel.create(name, **kwargs)

def get_projects() -> List[Dict]:
    return ProjectModel.get_all()

def add_chat_message(session_id: str, role: str, content: str, **kwargs) -> Optional[Dict]:
    project_id = kwargs.pop('project_id', None)
    return ChatHistoryModel.add_message(project_id, session_id, role, content, **kwargs)

def get_chat_history(session_id: str) -> List[Dict]:
    return ChatHistoryModel.get_by_session(session_id)

def create_job(job_type: str, **kwargs) -> Optional[Dict]:
    return ProcessingJobModel.create(job_type, **kwargs)

def update_job_progress(job_id: str, percent: int, step: str) -> bool:
    return ProcessingJobModel.update_progress(job_id, percent, step)

def complete_job(job_id: str, result_data: dict = None) -> bool:
    return ProcessingJobModel.complete(job_id, result_data)

def fail_job(job_id: str, error: str) -> bool:
    return ProcessingJobModel.fail(job_id, error)
