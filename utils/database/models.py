"""
Database Models for XLR8
CRUD operations for projects, documents, chat history, suppressions, and entity config

Uses Supabase for persistent storage.

Version: 2.0 - Universal Classification Architecture
Updated: December 2024
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import uuid
import hashlib
import re
import logging

from .supabase_client import get_supabase

logger = logging.getLogger(__name__)


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


# =============================================================================
# DOCUMENT REGISTRY MODEL - Universal Classification Architecture
# =============================================================================

class DocumentRegistryModel:
    """
    Document Registry - THE SOURCE OF TRUTH for all uploaded files.
    
    Tracks ALL files in ChromaDB and/or DuckDB with unified metadata.
    All components should query this registry instead of backends directly.
    
    Classification Architecture (Three Truths):
    - REALITY: Customer's actual data (queryable in DuckDB)
    - INTENT: Customer's documentation (searchable in ChromaDB)
    - REFERENCE: Standards, best practices (global, searchable)
    - CONFIGURATION: Mapping/lookup files (queryable AND searchable)
    - OUTPUT: Generated deliverables (archive only)
    
    truth_type determines WHAT the file is
    storage_type determines WHERE it's stored
    Routing is determined by truth_type, NOT file extension
    """
    
    # ==========================================================================
    # TRUTH TYPES - The core classification
    # ==========================================================================
    TRUTH_REALITY = 'reality'
    TRUTH_INTENT = 'intent'
    TRUTH_REFERENCE = 'reference'
    TRUTH_CONFIGURATION = 'configuration'
    TRUTH_OUTPUT = 'output'
    
    VALID_TRUTH_TYPES = [TRUTH_REALITY, TRUTH_INTENT, TRUTH_REFERENCE, TRUTH_CONFIGURATION, TRUTH_OUTPUT]
    
    # ==========================================================================
    # STORAGE TYPES
    # ==========================================================================
    STORAGE_CHROMADB = 'chromadb'
    STORAGE_DUCKDB = 'duckdb'
    STORAGE_BOTH = 'both'
    
    VALID_STORAGE_TYPES = [STORAGE_CHROMADB, STORAGE_DUCKDB, STORAGE_BOTH]
    
    # ==========================================================================
    # CLASSIFICATION METHODS
    # ==========================================================================
    CLASS_USER_SELECTED = 'user_selected'
    CLASS_AUTO_DETECTED = 'auto_detected'
    CLASS_FILENAME_INFERRED = 'filename_inferred'
    
    VALID_CLASSIFICATION_METHODS = [CLASS_USER_SELECTED, CLASS_AUTO_DETECTED, CLASS_FILENAME_INFERRED]
    
    # ==========================================================================
    # PARSE STATUS
    # ==========================================================================
    PARSE_PENDING = 'pending'
    PARSE_SUCCESS = 'success'
    PARSE_PARTIAL = 'partial'
    PARSE_FAILED = 'failed'
    
    # ==========================================================================
    # LEGACY USAGE TYPES - Backward compatibility
    # ==========================================================================
    USAGE_RAG_KNOWLEDGE = 'rag_knowledge'
    USAGE_STRUCTURED_DATA = 'structured_data'
    USAGE_PLAYBOOK = 'playbook'
    USAGE_PLAYBOOK_SOURCE = 'playbook_source'
    USAGE_TEMPLATE = 'template'
    
    # ==========================================================================
    # ROUTING RULES
    # ==========================================================================
    
    @classmethod
    def get_storage_for_truth_type(cls, truth_type: str) -> str:
        """Determine storage type based on truth_type."""
        routing = {
            cls.TRUTH_REALITY: cls.STORAGE_DUCKDB,
            cls.TRUTH_INTENT: cls.STORAGE_CHROMADB,
            cls.TRUTH_REFERENCE: cls.STORAGE_CHROMADB,
            cls.TRUTH_CONFIGURATION: cls.STORAGE_BOTH,
            cls.TRUTH_OUTPUT: cls.STORAGE_CHROMADB,
        }
        return routing.get(truth_type, cls.STORAGE_CHROMADB)
    
    @classmethod
    def get_legacy_usage_type(cls, truth_type: str, is_global: bool) -> str:
        """Map truth_type to legacy usage_type for backward compatibility."""
        if truth_type == cls.TRUTH_REALITY:
            return cls.USAGE_STRUCTURED_DATA
        elif truth_type == cls.TRUTH_REFERENCE:
            return cls.USAGE_PLAYBOOK_SOURCE if is_global else cls.USAGE_TEMPLATE
        elif truth_type == cls.TRUTH_CONFIGURATION:
            return cls.USAGE_STRUCTURED_DATA
        else:
            return cls.USAGE_RAG_KNOWLEDGE
    
    # ==========================================================================
    # REGISTRATION
    # ==========================================================================
    
    @staticmethod
    def register(
        filename: str,
        truth_type: str = None,
        classification_method: str = None,
        file_type: str = None,
        storage_type: str = None,
        usage_type: str = None,
        project_id: str = None,
        is_global: bool = False,
        classification_confidence: float = 0.5,
        content_domain: List[str] = None,
        chunk_count: int = 0,
        file_size: int = None,
        duckdb_tables: List[str] = None,
        chromadb_collection: str = None,
        row_count: int = None,
        sheet_count: int = None,
        page_count: int = None,
        parse_status: str = 'success',
        parse_errors: List[str] = None,
        schema_confidence: float = None,
        processing_time_ms: int = None,
        classification_time_ms: int = None,
        parse_time_ms: int = None,
        embedding_time_ms: int = None,
        storage_time_ms: int = None,
        metadata: dict = None
    ) -> Optional[Dict[str, Any]]:
        """Register a document in the registry."""
        supabase = get_supabase()
        if not supabase:
            logger.error("[REGISTRY] No Supabase connection")
            return None
        
        # Handle backward compatibility
        if truth_type is None and usage_type is not None:
            if usage_type == DocumentRegistryModel.USAGE_STRUCTURED_DATA:
                truth_type = DocumentRegistryModel.TRUTH_REALITY
            elif usage_type in [DocumentRegistryModel.USAGE_PLAYBOOK_SOURCE, DocumentRegistryModel.USAGE_TEMPLATE]:
                truth_type = DocumentRegistryModel.TRUTH_REFERENCE
            else:
                truth_type = DocumentRegistryModel.TRUTH_INTENT if not is_global else DocumentRegistryModel.TRUTH_REFERENCE
            classification_method = classification_method or DocumentRegistryModel.CLASS_FILENAME_INFERRED
        
        if truth_type is None:
            truth_type = DocumentRegistryModel.TRUTH_INTENT if not is_global else DocumentRegistryModel.TRUTH_REFERENCE
            classification_method = classification_method or DocumentRegistryModel.CLASS_FILENAME_INFERRED
        
        if classification_method is None:
            classification_method = DocumentRegistryModel.CLASS_FILENAME_INFERRED
        
        if storage_type is None:
            storage_type = DocumentRegistryModel.get_storage_for_truth_type(truth_type)
        
        if usage_type is None:
            usage_type = DocumentRegistryModel.get_legacy_usage_type(truth_type, is_global)
        
        intelligence_ready = True
        readiness_blockers = []
        
        if parse_status == 'failed':
            intelligence_ready = False
            readiness_blockers.append('parse_failed')
        elif parse_status == 'partial':
            readiness_blockers.append('parse_partial')
        
        if classification_confidence < 0.4:
            readiness_blockers.append('low_classification_confidence')
        
        try:
            data = {
                'filename': filename,
                'file_type': file_type,
                'truth_type': truth_type,
                'classification_method': classification_method,
                'classification_confidence': classification_confidence,
                'content_domain': content_domain or [],
                'storage_type': storage_type,
                'usage_type': usage_type,
                'project_id': project_id,
                'is_global': is_global,
                'chunk_count': chunk_count,
                'file_size': file_size,
                'row_count': row_count,
                'sheet_count': sheet_count,
                'page_count': page_count,
                'parse_status': parse_status,
                'parse_errors': parse_errors or [],
                'schema_confidence': schema_confidence,
                'intelligence_ready': intelligence_ready,
                'readiness_blockers': readiness_blockers,
                'citation_count': 0,
                'positive_feedback': 0,
                'negative_feedback': 0,
                'processing_time_ms': processing_time_ms,
                'classification_time_ms': classification_time_ms,
                'parse_time_ms': parse_time_ms,
                'embedding_time_ms': embedding_time_ms,
                'storage_time_ms': storage_time_ms,
                'metadata': metadata or {}
            }
            
            data = {k: v for k, v in data.items() if v is not None}
            
            response = supabase.table('document_registry').insert(data).execute()
            
            if response.data:
                logger.info(f"[REGISTRY] Registered: {filename} as {truth_type} -> {storage_type}")
                return response.data[0]
            return None
            
        except Exception as e:
            logger.error(f"[REGISTRY] Error registering {filename}: {e}")
            return None
    
    # ==========================================================================
    # BASIC QUERIES
    # ==========================================================================
    
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
            logger.error(f"[REGISTRY] Error getting all: {e}")
            return []
    
    @staticmethod
    def get_by_project(
        project_id: str = None, 
        include_global: bool = True,
        truth_type: str = None,
        storage_type: str = None,
        intelligence_ready_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Get documents for a project with optional filters."""
        supabase = get_supabase()
        if not supabase:
            return []
        
        try:
            query = supabase.table('document_registry').select('*')
            
            if project_id:
                if include_global:
                    query = query.or_(f'project_id.eq.{project_id},is_global.eq.true')
                else:
                    query = query.eq('project_id', project_id)
            else:
                query = query.eq('is_global', True)
            
            if truth_type:
                if isinstance(truth_type, list):
                    query = query.in_('truth_type', truth_type)
                else:
                    query = query.eq('truth_type', truth_type)
            
            if storage_type:
                if isinstance(storage_type, list):
                    query = query.in_('storage_type', storage_type)
                else:
                    query = query.eq('storage_type', storage_type)
            
            if intelligence_ready_only:
                query = query.eq('intelligence_ready', True)
            
            response = query.order('created_at', desc=True).execute()
            return response.data if response.data else []
            
        except Exception as e:
            logger.error(f"[REGISTRY] Error getting by project: {e}")
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
            logger.error(f"[REGISTRY] Error finding {filename}: {e}")
            return None
    
    @staticmethod
    def find_by_id(registry_id: str) -> Optional[Dict[str, Any]]:
        """Find a document by registry ID"""
        supabase = get_supabase()
        if not supabase:
            return None
        
        try:
            response = supabase.table('document_registry').select('*').eq('id', registry_id).limit(1).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"[REGISTRY] Error finding by ID {registry_id}: {e}")
            return None
    
    # ==========================================================================
    # TRUTH-TYPE SPECIFIC QUERIES
    # ==========================================================================
    
    @staticmethod
    def get_reality_files(project_id: str, include_global: bool = False) -> List[Dict[str, Any]]:
        """Get REALITY files (customer data) for a project."""
        return DocumentRegistryModel.get_by_project(
            project_id=project_id,
            include_global=include_global,
            truth_type=DocumentRegistryModel.TRUTH_REALITY,
            intelligence_ready_only=True
        )
    
    @staticmethod
    def get_intent_files(project_id: str) -> List[Dict[str, Any]]:
        """Get INTENT files (customer documentation) for a project."""
        return DocumentRegistryModel.get_by_project(
            project_id=project_id,
            include_global=False,
            truth_type=DocumentRegistryModel.TRUTH_INTENT,
            intelligence_ready_only=True
        )
    
    @staticmethod
    def get_reference_files() -> List[Dict[str, Any]]:
        """Get REFERENCE files (standards, checklists)."""
        return DocumentRegistryModel.get_by_project(
            project_id=None,
            include_global=True,
            truth_type=DocumentRegistryModel.TRUTH_REFERENCE,
            intelligence_ready_only=True
        )
    
    @staticmethod
    def get_configuration_files(project_id: str = None, include_global: bool = True) -> List[Dict[str, Any]]:
        """Get CONFIGURATION files (mappings, lookups)."""
        return DocumentRegistryModel.get_by_project(
            project_id=project_id,
            include_global=include_global,
            truth_type=DocumentRegistryModel.TRUTH_CONFIGURATION,
            intelligence_ready_only=True
        )
    
    @staticmethod
    def get_queryable_tables(project_id: str, include_global: bool = False) -> List[str]:
        """Get list of DuckDB table names that are queryable for a project."""
        files = DocumentRegistryModel.get_by_project(
            project_id=project_id,
            include_global=include_global,
            truth_type=[DocumentRegistryModel.TRUTH_REALITY, DocumentRegistryModel.TRUTH_CONFIGURATION],
            storage_type=[DocumentRegistryModel.STORAGE_DUCKDB, DocumentRegistryModel.STORAGE_BOTH],
            intelligence_ready_only=True
        )
        
        tables = []
        for f in files:
            metadata = f.get('metadata', {})
            if isinstance(metadata, dict) and 'tables' in metadata:
                tables.extend(metadata['tables'])
            if f.get('duckdb_tables'):
                tables.extend(f['duckdb_tables'])
        
        return list(set(tables))
    
    @staticmethod
    def get_for_intelligence(project_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """Get all files organized by truth type for the Intelligence Engine."""
        return {
            'reality': DocumentRegistryModel.get_reality_files(project_id),
            'intent': DocumentRegistryModel.get_intent_files(project_id),
            'reference': DocumentRegistryModel.get_reference_files(),
            'configuration': DocumentRegistryModel.get_configuration_files(project_id)
        }
    
    # ==========================================================================
    # UNREGISTER / DELETE
    # ==========================================================================
    
    @staticmethod
    def unregister(filename: str, project_id: str = None) -> bool:
        """Remove a document from the registry."""
        supabase = get_supabase()
        if not supabase:
            return False
        
        try:
            if project_id:
                result = supabase.table('document_registry').delete().eq('filename', filename).eq('project_id', project_id).execute()
            else:
                result = supabase.table('document_registry').delete().eq('filename', filename).execute()
            
            deleted_count = len(result.data) if result.data else 0
            if deleted_count > 0:
                logger.info(f"[REGISTRY] Unregistered: {filename}")
            return deleted_count > 0 or True
            
        except Exception as e:
            logger.error(f"[REGISTRY] Error unregistering {filename}: {e}")
            return False
    
    # ==========================================================================
    # UPDATES
    # ==========================================================================
    
    @staticmethod
    def update(filename: str, project_id: str = None, **updates) -> bool:
        """Update fields for a document."""
        supabase = get_supabase()
        if not supabase:
            return False
        
        try:
            updates['updated_at'] = datetime.utcnow().isoformat()
            query = supabase.table('document_registry').update(updates).eq('filename', filename)
            if project_id:
                query = query.eq('project_id', project_id)
            query.execute()
            return True
        except Exception as e:
            logger.error(f"[REGISTRY] Error updating {filename}: {e}")
            return False
    
    @staticmethod
    def update_chunk_count(filename: str, chunk_count: int, project_id: str = None) -> bool:
        """Update the chunk count for a document"""
        return DocumentRegistryModel.update(filename, project_id, chunk_count=chunk_count)
    
    @staticmethod
    def reclassify(filename: str, truth_type: str, classification_method: str = 'user_selected',
                   classification_confidence: float = 1.0, project_id: str = None) -> bool:
        """Reclassify a document with a new truth_type."""
        if truth_type not in DocumentRegistryModel.VALID_TRUTH_TYPES:
            return False
        new_storage = DocumentRegistryModel.get_storage_for_truth_type(truth_type)
        return DocumentRegistryModel.update(filename, project_id, truth_type=truth_type,
                                            storage_type=new_storage, classification_method=classification_method,
                                            classification_confidence=classification_confidence)
    
    # ==========================================================================
    # LEARNING METRICS
    # ==========================================================================
    
    @staticmethod
    def increment_citation(filename: str, project_id: str = None) -> bool:
        """Increment citation count when a file is used in an answer."""
        supabase = get_supabase()
        if not supabase:
            return False
        
        try:
            doc = DocumentRegistryModel.find_by_filename(filename, project_id)
            if not doc:
                return False
            
            current_count = doc.get('citation_count', 0) or 0
            updates = {
                'citation_count': current_count + 1,
                'last_cited_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            query = supabase.table('document_registry').update(updates).eq('filename', filename)
            if project_id:
                query = query.eq('project_id', project_id)
            query.execute()
            return True
        except Exception as e:
            logger.error(f"[REGISTRY] Error incrementing citation for {filename}: {e}")
            return False
    
    @staticmethod
    def record_feedback(filename: str, positive: bool, project_id: str = None) -> bool:
        """Record feedback for a file (thumbs up/down)."""
        supabase = get_supabase()
        if not supabase:
            return False
        
        try:
            doc = DocumentRegistryModel.find_by_filename(filename, project_id)
            if not doc:
                return False
            
            if positive:
                current = doc.get('positive_feedback', 0) or 0
                updates = {'positive_feedback': current + 1}
            else:
                current = doc.get('negative_feedback', 0) or 0
                updates = {'negative_feedback': current + 1}
            
            updates['updated_at'] = datetime.utcnow().isoformat()
            
            query = supabase.table('document_registry').update(updates).eq('filename', filename)
            if project_id:
                query = query.eq('project_id', project_id)
            query.execute()
            return True
        except Exception as e:
            logger.error(f"[REGISTRY] Error recording feedback for {filename}: {e}")
            return False
    
    # ==========================================================================
    # DIAGNOSTICS
    # ==========================================================================
    
    @staticmethod
    def get_classification_stats(project_id: str = None) -> Dict[str, Any]:
        """Get classification statistics for diagnostics dashboard."""
        supabase = get_supabase()
        if not supabase:
            return {}
        
        try:
            files = DocumentRegistryModel.get_by_project(project_id, include_global=True) if project_id else DocumentRegistryModel.get_all()
            
            stats = {
                'total_files': len(files),
                'by_truth_type': {},
                'by_classification_method': {},
                'by_parse_status': {},
                'intelligence_ready': 0,
                'not_ready': 0,
                'low_confidence': 0,
                'never_cited': 0,
                'avg_feedback_score': 0.0
            }
            
            total_feedback = 0
            positive_total = 0
            
            for f in files:
                tt = f.get('truth_type', 'unknown')
                stats['by_truth_type'][tt] = stats['by_truth_type'].get(tt, 0) + 1
                
                cm = f.get('classification_method', 'unknown')
                stats['by_classification_method'][cm] = stats['by_classification_method'].get(cm, 0) + 1
                
                ps = f.get('parse_status', 'unknown')
                stats['by_parse_status'][ps] = stats['by_parse_status'].get(ps, 0) + 1
                
                if f.get('intelligence_ready', True):
                    stats['intelligence_ready'] += 1
                else:
                    stats['not_ready'] += 1
                
                conf = f.get('classification_confidence')
                if conf is not None and conf < 0.5:
                    stats['low_confidence'] += 1
                
                if (f.get('citation_count') or 0) == 0:
                    stats['never_cited'] += 1
                
                pos = f.get('positive_feedback') or 0
                neg = f.get('negative_feedback') or 0
                if pos + neg > 0:
                    total_feedback += pos + neg
                    positive_total += pos
            
            if total_feedback > 0:
                stats['avg_feedback_score'] = round(positive_total / total_feedback, 2)
            
            return stats
        except Exception as e:
            logger.error(f"[REGISTRY] Error getting stats: {e}")
            return {}
    
    @staticmethod
    def get_files_needing_review(project_id: str = None) -> List[Dict[str, Any]]:
        """Get files that need manual review."""
        try:
            files = DocumentRegistryModel.get_by_project(project_id, include_global=True) if project_id else DocumentRegistryModel.get_all()
            
            needs_review = []
            for f in files:
                reasons = []
                if not f.get('intelligence_ready', True):
                    reasons.append('not_intelligence_ready')
                conf = f.get('classification_confidence')
                if conf is not None and conf < 0.5:
                    reasons.append('low_confidence')
                ps = f.get('parse_status', 'success')
                if ps in ['partial', 'failed']:
                    reasons.append(f'parse_{ps}')
                blockers = f.get('readiness_blockers', [])
                if blockers:
                    reasons.extend(blockers)
                if reasons:
                    f['review_reasons'] = reasons
                    needs_review.append(f)
            
            return needs_review
        except Exception as e:
            logger.error(f"[REGISTRY] Error getting files needing review: {e}")
            return []
    
    @staticmethod
    def get_processing_stats(project_id: str = None) -> Dict[str, Any]:
        """Get processing time statistics for performance monitoring."""
        supabase = get_supabase()
        if not supabase:
            return {}
        
        try:
            files = DocumentRegistryModel.get_by_project(project_id, include_global=True) if project_id else DocumentRegistryModel.get_all()
            
            stats = {
                'total_files': len(files),
                'files_with_timing': 0,
                'avg_processing_time_ms': 0,
                'avg_classification_time_ms': 0,
                'avg_parse_time_ms': 0,
                'avg_embedding_time_ms': 0,
                'avg_storage_time_ms': 0,
                'max_processing_time_ms': 0,
                'min_processing_time_ms': None,
                'by_file_type': {},
                'by_truth_type': {},
                'slowest_files': []
            }
            
            processing_times = []
            classification_times = []
            parse_times = []
            embedding_times = []
            storage_times = []
            
            files_with_timing = []
            
            for f in files:
                pt = f.get('processing_time_ms')
                if pt is not None:
                    stats['files_with_timing'] += 1
                    processing_times.append(pt)
                    files_with_timing.append((pt, f))
                    
                    # Track by file type
                    ft = f.get('file_type', 'unknown')
                    if ft not in stats['by_file_type']:
                        stats['by_file_type'][ft] = {'count': 0, 'total_ms': 0, 'avg_ms': 0}
                    stats['by_file_type'][ft]['count'] += 1
                    stats['by_file_type'][ft]['total_ms'] += pt
                    
                    # Track by truth type
                    tt = f.get('truth_type', 'unknown')
                    if tt not in stats['by_truth_type']:
                        stats['by_truth_type'][tt] = {'count': 0, 'total_ms': 0, 'avg_ms': 0}
                    stats['by_truth_type'][tt]['count'] += 1
                    stats['by_truth_type'][tt]['total_ms'] += pt
                
                if f.get('classification_time_ms'):
                    classification_times.append(f['classification_time_ms'])
                if f.get('parse_time_ms'):
                    parse_times.append(f['parse_time_ms'])
                if f.get('embedding_time_ms'):
                    embedding_times.append(f['embedding_time_ms'])
                if f.get('storage_time_ms'):
                    storage_times.append(f['storage_time_ms'])
            
            # Calculate averages
            if processing_times:
                stats['avg_processing_time_ms'] = int(sum(processing_times) / len(processing_times))
                stats['max_processing_time_ms'] = max(processing_times)
                stats['min_processing_time_ms'] = min(processing_times)
            if classification_times:
                stats['avg_classification_time_ms'] = int(sum(classification_times) / len(classification_times))
            if parse_times:
                stats['avg_parse_time_ms'] = int(sum(parse_times) / len(parse_times))
            if embedding_times:
                stats['avg_embedding_time_ms'] = int(sum(embedding_times) / len(embedding_times))
            if storage_times:
                stats['avg_storage_time_ms'] = int(sum(storage_times) / len(storage_times))
            
            # Calculate per-type averages
            for ft in stats['by_file_type']:
                info = stats['by_file_type'][ft]
                if info['count'] > 0:
                    info['avg_ms'] = int(info['total_ms'] / info['count'])
            for tt in stats['by_truth_type']:
                info = stats['by_truth_type'][tt]
                if info['count'] > 0:
                    info['avg_ms'] = int(info['total_ms'] / info['count'])
            
            # Get top 5 slowest files
            files_with_timing.sort(reverse=True, key=lambda x: x[0])
            stats['slowest_files'] = [
                {
                    'filename': f['filename'],
                    'processing_time_ms': pt,
                    'file_type': f.get('file_type'),
                    'truth_type': f.get('truth_type'),
                    'file_size': f.get('file_size')
                }
                for pt, f in files_with_timing[:5]
            ]
            
            return stats
        except Exception as e:
            logger.error(f"[REGISTRY] Error getting processing stats: {e}")
            return {}
    
    # ==========================================================================
    # UTILITY
    # ==========================================================================
    
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
    
    @staticmethod
    def validate_truth_type(truth_type: str) -> bool:
        return truth_type in DocumentRegistryModel.VALID_TRUTH_TYPES
    
    @staticmethod
    def validate_classification_method(method: str) -> bool:
        return method in DocumentRegistryModel.VALID_CLASSIFICATION_METHODS


# =============================================================================
# AUTO-CLASSIFICATION HELPER
# =============================================================================

def auto_classify_file(filename: str, file_extension: str, project_name: str, 
                       file_content_sample: str = None) -> Tuple[str, str, float]:
    """
    Auto-classify a file based on filename, extension, and optionally content.
    
    Truth Types:
    - REALITY: Customer data (employee records, payroll exports, registers)
    - INTENT: Customer documents (their setup, requirements, SOWs)
    - REFERENCE: Standards/best practices (global, checklists, guides)
    - CONFIGURATION: Mapping/lookup tables (ONLY for structured files xlsx/csv)
    
    Key insight: A PDF about "Earnings Codes" is documenting the customer's setup (INTENT),
    not a config file itself. Configuration only applies to actual data files.
    """
    filename_lower = filename.lower()
    is_global = project_name.lower() in ['global', '__global__', 'global/universal', 'reference library']
    is_structured = file_extension in ['xlsx', 'xls', 'csv']
    is_document = file_extension in ['pdf', 'docx', 'doc', 'txt']
    
    # Keywords for classification
    reality_keywords = ['register', 'export', 'report', 'data', 'payroll', 'employee', 'hr_', 'audit']
    intent_keywords = ['sow', 'requirement', 'statement of work', 'notes', 'meeting', 'spec', 'scope']
    reference_keywords = ['checklist', 'standard', 'guide', 'reference', 'compliance', 'template', 
                          'best_practice', 'best-practice', 'year-end', 'yearend', 'year_end']
    # Config keywords only apply to structured files - PDFs with these words are documentation
    config_keywords = ['mapping', 'lookup', 'config', 'crosswalk', 'translation', 'xref']
    # "codes" is special - structured file with codes = config, PDF with codes = intent (documenting codes)
    codes_keywords = ['codes', 'code_list', 'earnings_codes', 'deduction_codes']
    
    # 1. Reference materials (any file type - checklists, guides, standards)
    if any(kw in filename_lower for kw in reference_keywords):
        return (DocumentRegistryModel.TRUTH_REFERENCE, DocumentRegistryModel.CLASS_FILENAME_INFERRED, 0.8)
    
    # 2. Configuration - ONLY for structured files (xlsx/csv) with mapping/lookup data
    if is_structured and any(kw in filename_lower for kw in config_keywords):
        return (DocumentRegistryModel.TRUTH_CONFIGURATION, DocumentRegistryModel.CLASS_FILENAME_INFERRED, 0.8)
    
    # 3. "Codes" in filename - structured = config data, document = documentation about codes
    if any(kw in filename_lower for kw in codes_keywords):
        if is_structured:
            return (DocumentRegistryModel.TRUTH_CONFIGURATION, DocumentRegistryModel.CLASS_FILENAME_INFERRED, 0.8)
        else:
            # PDF/doc about codes = customer documentation of their setup
            return (DocumentRegistryModel.TRUTH_INTENT, DocumentRegistryModel.CLASS_FILENAME_INFERRED, 0.8)
    
    # 4. Intent keywords (requirements, SOWs, specs)
    if any(kw in filename_lower for kw in intent_keywords):
        return (DocumentRegistryModel.TRUTH_INTENT, DocumentRegistryModel.CLASS_FILENAME_INFERRED, 0.8)
    
    # 5. Reality keywords (data exports, registers) - only for non-global
    if any(kw in filename_lower for kw in reality_keywords) and not is_global:
        return (DocumentRegistryModel.TRUTH_REALITY, DocumentRegistryModel.CLASS_FILENAME_INFERRED, 0.8)
    
    # 6. Default by file extension
    if is_structured:
        if is_global:
            return (DocumentRegistryModel.TRUTH_REFERENCE, DocumentRegistryModel.CLASS_FILENAME_INFERRED, 0.5)
        else:
            return (DocumentRegistryModel.TRUTH_REALITY, DocumentRegistryModel.CLASS_FILENAME_INFERRED, 0.6)
    
    if is_document:
        if is_global:
            return (DocumentRegistryModel.TRUTH_REFERENCE, DocumentRegistryModel.CLASS_FILENAME_INFERRED, 0.6)
        else:
            return (DocumentRegistryModel.TRUTH_INTENT, DocumentRegistryModel.CLASS_FILENAME_INFERRED, 0.6)
    
    # 7. Ultimate fallback
    if is_global:
        return (DocumentRegistryModel.TRUTH_REFERENCE, DocumentRegistryModel.CLASS_FILENAME_INFERRED, 0.4)
    else:
        return (DocumentRegistryModel.TRUTH_INTENT, DocumentRegistryModel.CLASS_FILENAME_INFERRED, 0.4)


# =============================================================================
# CHAT HISTORY MODEL
# =============================================================================

class ChatHistoryModel:
    """Chat history database operations"""
    
    @staticmethod
    def add_message(project_id: str, session_id: str, role: str,
                   content: str, sources: list = None, metadata: dict = None) -> Optional[Dict[str, Any]]:
        supabase = get_supabase()
        if not supabase:
            return None
        try:
            data = {
                'project_id': project_id, 'session_id': session_id, 'role': role,
                'content': content, 'sources': sources or [], 'metadata': metadata or {}
            }
            response = supabase.table('chat_history').insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error adding chat message: {e}")
            return None
    
    @staticmethod
    def get_by_session(session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        supabase = get_supabase()
        if not supabase:
            return []
        try:
            response = supabase.table('chat_history').select('*').eq('session_id', session_id).order('created_at', desc=False).limit(limit).execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Error getting chat history: {e}")
            return []
    
    @staticmethod
    def get_by_project(project_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        supabase = get_supabase()
        if not supabase:
            return []
        try:
            response = supabase.table('chat_history').select('*').eq('project_id', project_id).order('created_at', desc=True).limit(limit).execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Error getting chat history: {e}")
            return []
    
    @staticmethod
    def delete_session(session_id: str) -> bool:
        supabase = get_supabase()
        if not supabase:
            return False
        try:
            supabase.table('chat_history').delete().eq('session_id', session_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting session: {e}")
            return False


# =============================================================================
# PROCESSING JOB MODEL
# =============================================================================

class ProcessingJobModel:
    """Processing job database operations"""
    
    @staticmethod
    def create(job_type: str, project_id: str = None, filename: str = None, input_data: dict = None) -> Optional[Dict[str, Any]]:
        supabase = get_supabase()
        if not supabase:
            return None
        try:
            data = {'job_type': job_type, 'project_id': project_id, 'status': 'queued',
                    'progress': {'percent': 0, 'step': 'Queued...'}, 'input_data': input_data or {'filename': filename}}
            response = supabase.table('processing_jobs').insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error creating job: {e}")
            return None
    
    @staticmethod
    def update_progress(job_id: str, percent: int, step: str) -> bool:
        supabase = get_supabase()
        if not supabase:
            return False
        try:
            data = {'status': 'processing', 'progress': {'percent': percent, 'step': step}, 'updated_at': datetime.utcnow().isoformat()}
            if percent == 0:
                data['started_at'] = datetime.utcnow().isoformat()
            supabase.table('processing_jobs').update(data).eq('id', job_id).execute()
            return True
        except Exception as e:
            print(f"Error updating job progress: {e}")
            return False
    
    @staticmethod
    def complete(job_id: str, result_data: dict = None) -> bool:
        supabase = get_supabase()
        if not supabase:
            return False
        try:
            data = {'status': 'completed', 'progress': {'percent': 100, 'step': 'Complete'},
                    'result_data': result_data or {}, 'completed_at': datetime.utcnow().isoformat(), 'updated_at': datetime.utcnow().isoformat()}
            supabase.table('processing_jobs').update(data).eq('id', job_id).execute()
            return True
        except Exception as e:
            print(f"Error completing job: {e}")
            return False
    
    @staticmethod
    def fail(job_id: str, error_message: str) -> bool:
        supabase = get_supabase()
        if not supabase:
            return False
        try:
            data = {'status': 'failed', 'error_message': error_message, 'completed_at': datetime.utcnow().isoformat(), 'updated_at': datetime.utcnow().isoformat()}
            supabase.table('processing_jobs').update(data).eq('id', job_id).execute()
            return True
        except Exception as e:
            print(f"Error failing job: {e}")
            return False
    
    @staticmethod
    def get_all(limit: int = 50) -> List[Dict[str, Any]]:
        supabase = get_supabase()
        if not supabase:
            return []
        try:
            response = supabase.table('processing_jobs').select('*').order('created_at', desc=True).limit(limit).execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Error getting jobs: {e}")
            return []
    
    @staticmethod
    def get_by_id(job_id: str) -> Optional[Dict[str, Any]]:
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
        supabase = get_supabase()
        if not supabase:
            return []
        try:
            from datetime import timedelta
            cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
            response = supabase.table('processing_jobs').select('*').gte('created_at', cutoff).order('created_at', desc=True).limit(limit).execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Error getting recent jobs: {e}")
            return []


# =============================================================================
# FINDING SUPPRESSION MODEL
# =============================================================================

class FindingSuppressionModel:
    """Finding Suppression - Manage acknowledged/suppressed findings"""
    
    @staticmethod
    def _hash_finding(finding_text: str) -> str:
        normalized = finding_text.lower().strip()
        normalized = re.sub(r'\d+\.?\d*%?', 'N', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        return hashlib.sha256(normalized.encode()).hexdigest()[:32]
    
    @staticmethod
    def create(project_id: str, playbook_type: str, suppression_type: str, reason: str,
               action_id: str = None, finding_text: str = None, pattern: str = None,
               category: str = None, document_filter: str = None, state_filter: List[str] = None,
               keyword_filter: List[str] = None, fein_filter: List[str] = None,
               notes: str = None, expires_at: str = None, created_by: str = None) -> Optional[Dict[str, Any]]:
        supabase = get_supabase()
        if not supabase:
            return None
        try:
            finding_hash = None
            if finding_text and suppression_type in ('suppress', 'acknowledge'):
                finding_hash = FindingSuppressionModel._hash_finding(finding_text)
            data = {
                'project_id': project_id, 'playbook_type': playbook_type, 'action_id': action_id,
                'suppression_type': suppression_type, 'finding_hash': finding_hash, 'pattern': pattern,
                'category': category, 'document_filter': document_filter, 'state_filter': state_filter,
                'keyword_filter': keyword_filter, 'fein_filter': fein_filter, 'reason': reason,
                'notes': notes, 'expires_at': expires_at, 'created_by': created_by, 'is_active': True
            }
            data = {k: v for k, v in data.items() if v is not None}
            response = supabase.table('finding_suppressions').insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error creating suppression: {e}")
            return None
    
    @staticmethod
    def get_active_rules(project_id: str, playbook_type: str, action_id: str = None) -> List[Dict[str, Any]]:
        supabase = get_supabase()
        if not supabase:
            return []
        try:
            query = supabase.table('finding_suppressions').select('*').eq('project_id', project_id).eq('playbook_type', playbook_type).eq('is_active', True)
            response = query.execute()
            rules = response.data if response.data else []
            now = datetime.utcnow().isoformat()
            filtered = []
            for rule in rules:
                if rule.get('expires_at') and rule['expires_at'] < now:
                    continue
                if rule.get('action_id') and action_id and rule['action_id'] != action_id:
                    continue
                filtered.append(rule)
            return filtered
        except Exception as e:
            print(f"Error getting suppression rules: {e}")
            return []
    
    @staticmethod
    def check_finding(project_id: str, playbook_type: str, finding_text: str, action_id: str = None,
                      document_name: str = None, state: str = None, fein: str = None) -> Optional[Dict[str, Any]]:
        rules = FindingSuppressionModel.get_active_rules(project_id, playbook_type, action_id)
        if not rules:
            return None
        finding_hash = FindingSuppressionModel._hash_finding(finding_text)
        finding_lower = finding_text.lower()
        for rule in rules:
            if rule.get('fein_filter') and fein and fein not in rule['fein_filter']:
                continue
            if rule.get('finding_hash') and rule['finding_hash'] == finding_hash:
                FindingSuppressionModel._record_match(rule['id'])
                return rule
            if rule.get('pattern'):
                try:
                    if re.search(rule['pattern'], finding_text, re.IGNORECASE):
                        FindingSuppressionModel._record_match(rule['id'])
                        return rule
                except re.error:
                    pass
            if rule.get('document_filter') and document_name and rule['document_filter'].lower() in document_name.lower():
                FindingSuppressionModel._record_match(rule['id'])
                return rule
            if rule.get('state_filter') and state and state.upper() in [s.upper() for s in rule['state_filter']]:
                FindingSuppressionModel._record_match(rule['id'])
                return rule
            if rule.get('keyword_filter') and any(kw.lower() in finding_lower for kw in rule['keyword_filter']):
                FindingSuppressionModel._record_match(rule['id'])
                return rule
        return None
    
    @staticmethod
    def _record_match(rule_id: str) -> None:
        supabase = get_supabase()
        if not supabase:
            return
        try:
            supabase.rpc('increment_suppression_match', {'rule_id': rule_id}).execute()
        except Exception:
            try:
                supabase.table('finding_suppressions').update({
                    'match_count': supabase.table('finding_suppressions').select('match_count').eq('id', rule_id).execute().data[0].get('match_count', 0) + 1,
                    'last_matched_at': datetime.utcnow().isoformat()
                }).eq('id', rule_id).execute()
            except Exception:
                pass
    
    @staticmethod
    def deactivate(rule_id: str) -> bool:
        supabase = get_supabase()
        if not supabase:
            return False
        try:
            supabase.table('finding_suppressions').update({'is_active': False, 'updated_at': datetime.utcnow().isoformat()}).eq('id', rule_id).execute()
            return True
        except Exception as e:
            print(f"Error deactivating suppression: {e}")
            return False
    
    @staticmethod
    def reactivate(rule_id: str) -> bool:
        supabase = get_supabase()
        if not supabase:
            return False
        try:
            supabase.table('finding_suppressions').update({'is_active': True, 'updated_at': datetime.utcnow().isoformat()}).eq('id', rule_id).execute()
            return True
        except Exception as e:
            print(f"Error reactivating suppression: {e}")
            return False
    
    @staticmethod
    def get_by_project(project_id: str, playbook_type: str, include_inactive: bool = False) -> List[Dict[str, Any]]:
        supabase = get_supabase()
        if not supabase:
            return []
        try:
            query = supabase.table('finding_suppressions').select('*').eq('project_id', project_id).eq('playbook_type', playbook_type).order('created_at', desc=True)
            if not include_inactive:
                query = query.eq('is_active', True)
            response = query.execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Error getting suppressions by project: {e}")
            return []
    
    @staticmethod
    def get_stats(project_id: str, playbook_type: str) -> Dict[str, Any]:
        supabase = get_supabase()
        if not supabase:
            return {}
        try:
            response = supabase.table('finding_suppressions').select('*').eq('project_id', project_id).eq('playbook_type', playbook_type).execute()
            rules = response.data or []
            active = [r for r in rules if r.get('is_active')]
            return {
                'total_rules': len(rules), 'active_rules': len(active), 'inactive_rules': len(rules) - len(active),
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
    """Entity Configuration - Track which FEINs/BNs are being analyzed per project"""
    
    @staticmethod
    def save(project_id: str, playbook_type: str, analysis_scope: str, selected_entities: List[str],
             primary_entity: str = None, country_mode: str = 'us_only', detected_entities: Dict = None) -> Optional[Dict[str, Any]]:
        supabase = get_supabase()
        if not supabase:
            return None
        try:
            data = {
                'project_id': project_id, 'playbook_type': playbook_type, 'analysis_scope': analysis_scope,
                'selected_entities': selected_entities, 'primary_entity': primary_entity,
                'country_mode': country_mode, 'configured_at': datetime.utcnow().isoformat()
            }
            response = supabase.table('project_entity_config').upsert(data, on_conflict='project_id,playbook_type').execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error saving entity config: {e}")
            return None
    
    @staticmethod
    def get(project_id: str, playbook_type: str) -> Optional[Dict[str, Any]]:
        supabase = get_supabase()
        if not supabase:
            return None
        try:
            response = supabase.table('project_entity_config').select('*').eq('project_id', project_id).eq('playbook_type', playbook_type).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error getting entity config: {e}")
            return None
    
    @staticmethod
    def delete(project_id: str, playbook_type: str) -> bool:
        supabase = get_supabase()
        if not supabase:
            return False
        try:
            supabase.table('project_entity_config').delete().eq('project_id', project_id).eq('playbook_type', playbook_type).execute()
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
