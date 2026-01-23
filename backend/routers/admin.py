"""
ADMIN ROUTER - Learning System Management
==========================================

Endpoints for viewing and managing:
- Learned query patterns
- User preferences
- Clarification patterns
- Feedback history
- Global column mappings

Deploy to: backend/routers/admin.py

Add to main.py:
    from routers import admin
    app.include_router(admin.router, prefix="/api", tags=["admin"])

Security: All endpoints require OPS_CENTER permission (admin role).
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
import logging
import json

# Auth imports - all admin endpoints require authentication
from backend.utils.auth_middleware import (
    User, require_permission, Permissions
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin"])


# =============================================================================
# SUPABASE CLIENT
# =============================================================================

from utils.database.supabase_client import get_supabase


# =============================================================================
# LEARNED QUERIES
# =============================================================================

@router.get("/learning/queries")
async def get_learned_queries(limit: int = 100, offset: int = 0, user: User = Depends(require_permission(Permissions.OPS_CENTER))):
    """Get all learned query patterns."""
    try:
        supabase = get_supabase()
        result = supabase.table('learned_queries') \
            .select('*') \
            .order('created_at', desc=True) \
            .range(offset, offset + limit - 1) \
            .execute()
        return result.data or []
    except Exception as e:
        logger.error(f"[ADMIN] Error fetching queries: {e}")
        return []


@router.delete("/learning/queries/{query_id}")
async def delete_learned_query(query_id: str, user: User = Depends(require_permission(Permissions.OPS_CENTER))):
    """Delete a learned query pattern."""
    try:
        supabase = get_supabase()
        supabase.table('learned_queries').delete().eq('id', query_id).execute()
        return {"success": True}
    except Exception as e:
        logger.error(f"[ADMIN] Error deleting query: {e}")
        raise HTTPException(500, str(e))


# =============================================================================
# FEEDBACK
# =============================================================================

@router.get("/learning/feedback")
async def get_feedback(limit: int = 100, offset: int = 0, feedback_type: str = None, user: User = Depends(require_permission(Permissions.OPS_CENTER))):
    """Get feedback records."""
    try:
        supabase = get_supabase()
        query = supabase.table('query_feedback') \
            .select('*') \
            .order('created_at', desc=True)
        
        if feedback_type:
            query = query.eq('feedback', feedback_type)
        
        result = query.range(offset, offset + limit - 1).execute()
        return result.data or []
    except Exception as e:
        logger.error(f"[ADMIN] Error fetching feedback: {e}")
        return []


@router.delete("/learning/feedback/{feedback_id}")
async def delete_feedback(feedback_id: str, user: User = Depends(require_permission(Permissions.OPS_CENTER))):
    """Delete a feedback record."""
    try:
        supabase = get_supabase()
        supabase.table('query_feedback').delete().eq('id', feedback_id).execute()
        return {"success": True}
    except Exception as e:
        logger.error(f"[ADMIN] Error deleting feedback: {e}")
        raise HTTPException(500, str(e))


# =============================================================================
# USER PREFERENCES
# =============================================================================

@router.get("/learning/preferences")
async def get_preferences(user_id: str = None, limit: int = 100, user: User = Depends(require_permission(Permissions.OPS_CENTER))):
    """Get user preferences."""
    try:
        supabase = get_supabase()
        query = supabase.table('user_preferences') \
            .select('*') \
            .order('updated_at', desc=True)
        
        if user_id:
            query = query.eq('user_id', user_id)
        
        result = query.limit(limit).execute()
        return result.data or []
    except Exception as e:
        logger.error(f"[ADMIN] Error fetching preferences: {e}")
        return []


@router.delete("/learning/preferences/{pref_id}")
async def delete_preference(pref_id: str, user: User = Depends(require_permission(Permissions.OPS_CENTER))):
    """Delete a user preference."""
    try:
        supabase = get_supabase()
        supabase.table('user_preferences').delete().eq('id', pref_id).execute()
        return {"success": True}
    except Exception as e:
        logger.error(f"[ADMIN] Error deleting preference: {e}")
        raise HTTPException(500, str(e))


# =============================================================================
# CLARIFICATION PATTERNS
# =============================================================================

@router.get("/learning/clarifications")
async def get_clarification_patterns(limit: int = 100, user: User = Depends(require_permission(Permissions.OPS_CENTER))):
    """Get clarification patterns."""
    try:
        supabase = get_supabase()
        result = supabase.table('clarification_patterns') \
            .select('*') \
            .order('choice_count', desc=True) \
            .limit(limit) \
            .execute()
        return result.data or []
    except Exception as e:
        logger.error(f"[ADMIN] Error fetching clarifications: {e}")
        return []


@router.delete("/learning/clarifications/{pattern_id}")
async def delete_clarification(pattern_id: str, user: User = Depends(require_permission(Permissions.OPS_CENTER))):
    """Delete a clarification pattern."""
    try:
        supabase = get_supabase()
        supabase.table('clarification_patterns').delete().eq('id', pattern_id).execute()
        return {"success": True}
    except Exception as e:
        logger.error(f"[ADMIN] Error deleting clarification: {e}")
        raise HTTPException(500, str(e))


# =============================================================================
# GLOBAL COLUMN MAPPINGS
# =============================================================================

@router.get("/learning/mappings")
async def get_global_mappings(limit: int = 200, user: User = Depends(require_permission(Permissions.OPS_CENTER))):
    """Get global column mappings."""
    try:
        supabase = get_supabase()
        result = supabase.table('global_column_mappings') \
            .select('*') \
            .order('confirmed_count', desc=True) \
            .limit(limit) \
            .execute()
        return result.data or []
    except Exception as e:
        logger.error(f"[ADMIN] Error fetching mappings: {e}")
        return []


@router.delete("/learning/mappings/{mapping_id}")
async def delete_mapping(mapping_id: str, user: User = Depends(require_permission(Permissions.OPS_CENTER))):
    """Delete a global column mapping."""
    try:
        supabase = get_supabase()
        supabase.table('global_column_mappings').delete().eq('id', mapping_id).execute()
        return {"success": True}
    except Exception as e:
        logger.error(f"[ADMIN] Error deleting mapping: {e}")
        raise HTTPException(500, str(e))


@router.post("/learning/mappings")
async def add_mapping(
    column_pattern_1: str,
    column_pattern_2: str,
    semantic_type: str = None,
    canonical_name: str = None
, user: User = Depends(require_permission(Permissions.OPS_CENTER))):
    """Add a new global column mapping."""
    try:
        supabase = get_supabase()
        
        # Normalize patterns
        p1 = column_pattern_1.lower().strip()
        p2 = column_pattern_2.lower().strip()
        
        # Ensure consistent ordering
        if p1 > p2:
            p1, p2 = p2, p1
        
        result = supabase.table('global_column_mappings').upsert({
            'column_pattern_1': p1,
            'column_pattern_2': p2,
            'semantic_type': semantic_type,
            'canonical_name': canonical_name,
            'confidence': 1.0,
            'confirmed_count': 1
        }).execute()
        
        return {"success": True, "data": result.data}
    except Exception as e:
        logger.error(f"[ADMIN] Error adding mapping: {e}")
        raise HTTPException(500, str(e))


# =============================================================================
# EXPORT
# =============================================================================

@router.get("/learning/export/{data_type}")
async def export_learning_data(data_type: str, user: User = Depends(require_permission(Permissions.OPS_CENTER))):
    """Export learning data as JSON."""
    try:
        supabase = get_supabase()
        
        if data_type == 'all':
            data = {
                'learned_queries': (supabase.table('learned_queries').select('*').execute()).data,
                'feedback': (supabase.table('query_feedback').select('*').execute()).data,
                'preferences': (supabase.table('user_preferences').select('*').execute()).data,
                'clarifications': (supabase.table('clarification_patterns').select('*').execute()).data,
                'mappings': (supabase.table('global_column_mappings').select('*').execute()).data,
            }
        elif data_type == 'queries':
            data = (supabase.table('learned_queries').select('*').execute()).data
        elif data_type == 'feedback':
            data = (supabase.table('query_feedback').select('*').execute()).data
        elif data_type == 'preferences':
            data = (supabase.table('user_preferences').select('*').execute()).data
        elif data_type == 'clarifications':
            data = (supabase.table('clarification_patterns').select('*').execute()).data
        elif data_type == 'mappings':
            data = (supabase.table('global_column_mappings').select('*').execute()).data
        else:
            raise HTTPException(400, f"Unknown data type: {data_type}")
        
        return data
        
    except Exception as e:
        logger.error(f"[ADMIN] Error exporting data: {e}")
        raise HTTPException(500, str(e))


# =============================================================================
# STATS
# =============================================================================

@router.get("/learning/stats/detailed")
async def get_detailed_stats(user: User = Depends(require_permission(Permissions.OPS_CENTER))):
    """Get detailed learning statistics."""
    try:
        supabase = get_supabase()
        
        # Get counts
        queries = supabase.table('learned_queries').select('id', count='exact').execute()
        feedback = supabase.table('query_feedback').select('id, feedback', count='exact').execute()
        prefs = supabase.table('user_preferences').select('id', count='exact').execute()
        clarifs = supabase.table('clarification_patterns').select('id', count='exact').execute()
        mappings = supabase.table('global_column_mappings').select('id', count='exact').execute()
        
        # Get feedback breakdown
        positive = len([f for f in (feedback.data or []) if f.get('feedback') == 'positive'])
        negative = len([f for f in (feedback.data or []) if f.get('feedback') == 'negative'])
        
        # Get high-confidence patterns
        high_conf_queries = supabase.table('learned_queries') \
            .select('id') \
            .gte('avg_feedback', 0.5) \
            .execute()
        
        high_conf_prefs = supabase.table('user_preferences') \
            .select('id') \
            .gte('confidence', 0.8) \
            .execute()
        
        return {
            'totals': {
                'learned_queries': queries.count or 0,
                'feedback_records': feedback.count or 0,
                'user_preferences': prefs.count or 0,
                'clarification_patterns': clarifs.count or 0,
                'global_mappings': mappings.count or 0,
            },
            'feedback': {
                'positive': positive,
                'negative': negative,
                'rate': positive / max(positive + negative, 1)
            },
            'confidence': {
                'high_confidence_queries': len(high_conf_queries.data or []),
                'high_confidence_preferences': len(high_conf_prefs.data or []),
            }
        }
    except Exception as e:
        logger.error(f"[ADMIN] Error getting detailed stats: {e}")
        return {'error': str(e)}


# =============================================================================
# BULK OPERATIONS
# =============================================================================

@router.delete("/learning/clear/{data_type}")
async def clear_learning_data(data_type: str, confirm: bool = False, user: User = Depends(require_permission(Permissions.OPS_CENTER))):
    """Clear all data of a specific type. Requires confirm=true."""
    if not confirm:
        raise HTTPException(400, "Must set confirm=true to clear data")
    
    try:
        supabase = get_supabase()
        
        if data_type == 'queries':
            supabase.table('learned_queries').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
        elif data_type == 'feedback':
            supabase.table('query_feedback').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
        elif data_type == 'preferences':
            supabase.table('user_preferences').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
        elif data_type == 'clarifications':
            supabase.table('clarification_patterns').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
        elif data_type == 'all':
            supabase.table('learned_queries').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
            supabase.table('query_feedback').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
            supabase.table('user_preferences').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
            supabase.table('clarification_patterns').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
        else:
            raise HTTPException(400, f"Unknown data type: {data_type}")
        
        return {"success": True, "cleared": data_type}
        
    except Exception as e:
        logger.error(f"[ADMIN] Error clearing data: {e}")
        raise HTTPException(500, str(e))


# =============================================================================
# REFERENCE / STANDARDS MANAGEMENT
# =============================================================================

@router.get("/references")
async def list_references(user: User = Depends(require_permission(Permissions.OPS_CENTER))):
    """
    List all reference/standards files.
    
    These are global documents with truth_type='reference'.
    """
    try:
        supabase = get_supabase()
        
        # Get from document_registry
        result = supabase.table('document_registry') \
            .select('*') \
            .eq('truth_type', 'reference') \
            .execute()
        
        files = result.data or []
        
        # Also check for is_global files
        global_result = supabase.table('document_registry') \
            .select('*') \
            .eq('is_global', True) \
            .execute()
        
        global_files = global_result.data or []
        
        # Merge unique
        seen = set(f['filename'] for f in files)
        for gf in global_files:
            if gf['filename'] not in seen:
                files.append(gf)
                seen.add(gf['filename'])
        
        return {
            'count': len(files),
            'files': files
        }
        
    except Exception as e:
        logger.error(f"[ADMIN] Error listing references: {e}")
        raise HTTPException(500, str(e))


@router.delete("/references/{filename:path}")
async def delete_reference(filename: str, confirm: bool = False, user: User = Depends(require_permission(Permissions.OPS_CENTER))):
    """
    Delete a specific reference/standards file.
    
    Removes from:
    - Document registry (Supabase)
    - ChromaDB (vector store)
    - Lineage edges
    - Rule registry (if applicable)
    """
    if not confirm:
        raise HTTPException(400, "Must set confirm=true to delete")
    
    try:
        deleted = {
            'registry': False,
            'chromadb': 0,
            'lineage': 0,
            'rules': False
        }
        
        supabase = get_supabase()
        
        # 1. Delete from document_registry
        try:
            result = supabase.table('document_registry') \
                .delete() \
                .eq('filename', filename) \
                .eq('truth_type', 'reference') \
                .execute()
            deleted['registry'] = len(result.data or []) > 0
            
            # Also try is_global
            if not deleted['registry']:
                result = supabase.table('document_registry') \
                    .delete() \
                    .eq('filename', filename) \
                    .eq('is_global', True) \
                    .execute()
                deleted['registry'] = len(result.data or []) > 0
        except Exception as e:
            logger.warning(f"[ADMIN] Registry delete failed: {e}")
        
        # 2. Delete from ChromaDB
        try:
            from utils.rag_handler import RAGHandler
            rag = RAGHandler()
            collection = rag.client.get_or_create_collection(name="documents")
            
            # Find chunks for this file
            results = collection.get(
                where={"$or": [
                    {"source": filename},
                    {"filename": filename}
                ]},
                include=["metadatas"]
            )
            
            if results and results.get('ids'):
                collection.delete(ids=results['ids'])
                deleted['chromadb'] = len(results['ids'])
                logger.info(f"[ADMIN] Deleted {len(results['ids'])} chunks from ChromaDB")
        except Exception as e:
            logger.warning(f"[ADMIN] ChromaDB delete failed: {e}")
        
        # 3. Delete lineage edges
        try:
            result = supabase.table('lineage_edges') \
                .delete() \
                .eq('source_id', filename) \
                .eq('source_type', 'file') \
                .execute()
            deleted['lineage'] = len(result.data or [])
        except Exception as e:
            logger.warning(f"[ADMIN] Lineage delete failed: {e}")
        
        # 4. Delete from standards_rules Supabase table
        try:
            result = supabase.table('standards_rules') \
                .delete() \
                .eq('source_document', filename) \
                .execute()
            deleted['rules'] = len(result.data or [])
            if deleted['rules']:
                logger.info(f"[ADMIN] Deleted {deleted['rules']} rules from standards_rules")
        except Exception as e:
            logger.warning(f"[ADMIN] standards_rules delete failed: {e}")
        
        return {
            'success': True,
            'filename': filename,
            'deleted': deleted
        }
        
    except Exception as e:
        logger.error(f"[ADMIN] Error deleting reference: {e}")
        raise HTTPException(500, str(e))


@router.delete("/references/clear/all")
async def clear_all_references(confirm: bool = False, user: User = Depends(require_permission(Permissions.OPS_CENTER))):
    """
    Clear ALL reference/standards files.
    
    WARNING: This is destructive. Requires confirm=true.
    """
    if not confirm:
        raise HTTPException(400, "Must set confirm=true to clear all references")
    
    try:
        deleted = {
            'registry': 0,
            'chromadb': 0,
            'lineage': 0,
            'rules': False
        }
        
        supabase = get_supabase()
        
        # 1. Get all reference files first
        refs = supabase.table('document_registry') \
            .select('filename') \
            .or_('truth_type.eq.reference,is_global.eq.true') \
            .execute()
        
        filenames = [r['filename'] for r in (refs.data or [])]
        
        # 2. Delete from registry
        try:
            result = supabase.table('document_registry') \
                .delete() \
                .or_('truth_type.eq.reference,is_global.eq.true') \
                .execute()
            deleted['registry'] = len(result.data or [])
        except Exception as e:
            logger.warning(f"[ADMIN] Registry clear failed: {e}")
        
        # 3. Delete from ChromaDB
        try:
            from utils.rag_handler import RAGHandler
            rag = RAGHandler()
            collection = rag.client.get_or_create_collection(name="documents")
            
            for filename in filenames:
                try:
                    results = collection.get(
                        where={"$or": [
                            {"source": filename},
                            {"filename": filename}
                        ]},
                        include=["metadatas"]
                    )
                    if results and results.get('ids'):
                        collection.delete(ids=results['ids'])
                        deleted['chromadb'] += len(results['ids'])
                except Exception as e:
                    logger.debug(f"Suppressed: {e}")
        except Exception as e:
            logger.warning(f"[ADMIN] ChromaDB clear failed: {e}")
        
        # 4. Delete lineage for these files
        try:
            for filename in filenames:
                result = supabase.table('lineage_edges') \
                    .delete() \
                    .eq('source_id', filename) \
                    .eq('source_type', 'file') \
                    .execute()
                deleted['lineage'] += len(result.data or [])
        except Exception as e:
            logger.warning(f"[ADMIN] Lineage clear failed: {e}")
        
        # 5. Clear standards_rules table
        try:
            result = supabase.table('standards_rules').delete().neq('rule_id', '').execute()
            deleted['rules'] = len(result.data or [])
            if deleted['rules']:
                logger.info(f"[ADMIN] Deleted {deleted['rules']} rules from standards_rules")
        except Exception as e:
            logger.warning(f"[ADMIN] standards_rules clear failed: {e}")
        
        return {
            'success': True,
            'files_processed': len(filenames),
            'deleted': deleted
        }
        
    except Exception as e:
        logger.error(f"[ADMIN] Error clearing references: {e}")
        raise HTTPException(500, str(e))


@router.get("/rules")
async def list_rules(user: User = Depends(require_permission(Permissions.OPS_CENTER))):
    """
    List all rules in the standards rule registry.
    """
    try:
        from utils.standards_processor import get_rule_registry
        registry = get_rule_registry()
        
        documents = []
        total_rules = 0
        
        if hasattr(registry, 'documents'):
            for doc in registry.documents:
                doc_info = {
                    'document_id': getattr(doc, 'document_id', 'unknown'),
                    'filename': getattr(doc, 'filename', 'unknown'),
                    'title': getattr(doc, 'title', ''),
                    'domain': getattr(doc, 'domain', 'general'),
                    'rules_count': len(getattr(doc, 'rules', []))
                }
                documents.append(doc_info)
                total_rules += doc_info['rules_count']
        
        return {
            'documents': len(documents),
            'total_rules': total_rules,
            'registry': documents
        }
        
    except ImportError:
        return {
            'documents': 0,
            'total_rules': 0,
            'registry': [],
            'note': 'Standards processor not available'
        }
    except Exception as e:
        logger.error(f"[ADMIN] Error listing rules: {e}")
        raise HTTPException(500, str(e))


@router.delete("/rules/clear")
async def clear_rules(confirm: bool = False, user: User = Depends(require_permission(Permissions.OPS_CENTER))):
    """
    Clear all rules from the standards rule registry.
    
    Note: This only clears the in-memory registry.
    Use /references/clear/all to also remove from ChromaDB/Supabase.
    """
    if not confirm:
        raise HTTPException(400, "Must set confirm=true to clear rules")
    
    try:
        from utils.standards_processor import get_rule_registry
        registry = get_rule_registry()
        
        cleared = 0
        if hasattr(registry, 'documents'):
            cleared = len(registry.documents)
            registry.documents = []
        
        if hasattr(registry, 'clear'):
            registry.clear()
        
        return {
            'success': True,
            'cleared': cleared
        }
        
    except ImportError:
        return {
            'success': False,
            'error': 'Standards processor not available'
        }
    except Exception as e:
        logger.error(f"[ADMIN] Error clearing rules: {e}")
        raise HTTPException(500, str(e))


# =============================================================================
# FORCE DELETE PROJECT
# =============================================================================

@router.delete("/force-delete-project/{customer_id}")
async def force_delete_project(customer_id: str):
    """
    Force delete a project from Supabase regardless of is_active status.
    Use this when normal delete fails due to is_active filtering.
    """
    try:
        supabase = get_supabase()
        if not supabase:
            raise HTTPException(500, "Database unavailable")
        
        # Check if project exists
        check = supabase.table('customers').select('id, name').eq('id', customer_id).execute()
        if not check.data:
            raise HTTPException(404, f"Project {customer_id} not found")
        
        customer_id = check.data[0].get('name', customer_id)
        
        # Hard delete from customers table
        result = supabase.table('customers').delete().eq('id', customer_id).execute()
        
        logger.info(f"[ADMIN] Force deleted project: {customer_id} ({customer_id})")
        
        return {
            'success': True,
            'message': f'Project {customer_id} permanently deleted',
            'customer_id': customer_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ADMIN] Force delete failed: {e}")
        raise HTTPException(500, str(e))


@router.delete("/force-delete-project-by-name/{customer_id}")
async def force_delete_project_by_name(customer_id: str):
    """
    Force delete a project by name from Supabase.
    """
    try:
        supabase = get_supabase()
        if not supabase:
            raise HTTPException(500, "Database unavailable")
        
        # Find project
        check = supabase.table('customers').select('id, name').eq('name', customer_id).execute()
        if not check.data:
            raise HTTPException(404, f"Project '{customer_id}' not found")
        
        customer_id = check.data[0]['id']
        
        # Hard delete
        supabase.table('customers').delete().eq('id', customer_id).execute()
        
        logger.info(f"[ADMIN] Force deleted project: {customer_id} ({customer_id})")
        
        return {
            'success': True,
            'message': f'Project {customer_id} permanently deleted',
            'customer_id': customer_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ADMIN] Force delete failed: {e}")
        raise HTTPException(500, str(e))


# =============================================================================
# REGISTRY REPAIR - Sync existing data with document_registry
# =============================================================================

@router.get("/registry/status")
async def get_registry_status():
    """
    Check registry status - what's in DuckDB/ChromaDB vs document_registry.
    """
    try:
        supabase = get_supabase()
        
        # Import from correct locations
        # structured_data_handler is in /utils/
        # classification_service is in /backend/utils/
        # rag_handler is in /utils/
        try:
            from utils.structured_data_handler import get_structured_handler
        except ImportError:
            from backend.utils.structured_data_handler import get_structured_handler
        
        try:
            from utils.rag_handler import RAGHandler
        except ImportError:
            from backend.utils.rag_handler import RAGHandler
        
        try:
            from utils.classification_service import get_classification_service
        except ImportError:
            from backend.utils.classification_service import get_classification_service
        
        handler = get_structured_handler()
        rag = RAGHandler()
        service = get_classification_service(handler, rag)
        
        # 1. Get DuckDB tables via classification service
        duckdb_tables = []
        try:
            classifications = service.get_all_table_classifications()
            for c in classifications:
                duckdb_tables.append({
                    'table_name': c.table_name,
                    'source_filename': c.source_filename,
                    'row_count': c.row_count,
                    'column_count': c.column_count
                })
        except Exception as e:
            logger.error(f"[ADMIN] DuckDB scan error: {e}")
        
        # 2. Get ChromaDB documents (same pattern as classification/chunks)
        chromadb_docs = []
        try:
            collection = rag.client.get_collection(name="documents")
            if collection:
                results = collection.get(include=['metadatas'])
                sources = {}
                for meta in results.get('metadatas', []):
                    if not meta:
                        continue
                    source = meta.get('source') or meta.get('filename')
                    if source:
                        project = meta.get('customer_id', meta.get('project'))
                        if source not in sources:
                            sources[source] = {'count': 0, 'customer_id': project}
                        sources[source]['count'] += 1
                
                for source, info in sources.items():
                    chromadb_docs.append({
                        'document_name': source,
                        'chunk_count': info['count'],
                        'customer_id': info['customer_id']
                    })
        except Exception as e:
            logger.error(f"[ADMIN] ChromaDB scan error: {e}")
        
        # 3. Get registry entries
        registry_entries = []
        if supabase:
            try:
                result = supabase.table('document_registry').select('*').execute()
                registry_entries = result.data or []
            except Exception as e:
                logger.error(f"[ADMIN] Registry query error: {e}")
        
        # 4. Find orphans (in DuckDB/ChromaDB but not registry)
        registered_files = {r.get('filename') for r in registry_entries}
        
        orphan_tables = []
        for t in duckdb_tables:
            source = t.get('source_filename')
            if source and source not in registered_files:
                orphan_tables.append(t)
        
        orphan_docs = []
        for d in chromadb_docs:
            doc_name = d.get('document_name')
            if doc_name and doc_name not in registered_files:
                orphan_docs.append(d)
        
        return {
            'success': True,
            'summary': {
                'duckdb_tables': len(duckdb_tables),
                'chromadb_docs': len(chromadb_docs),
                'registry_entries': len(registry_entries),
                'orphan_tables': len(orphan_tables),
                'orphan_docs': len(orphan_docs)
            },
            'duckdb_tables': duckdb_tables,
            'chromadb_docs': chromadb_docs,
            'registry_entries': [{'filename': r.get('filename'), 'id': r.get('id'), 'storage_type': r.get('storage_type')} for r in registry_entries],
            'orphans': {
                'tables': orphan_tables,
                'documents': orphan_docs
            }
        }
        
    except Exception as e:
        logger.error(f"[ADMIN] Registry status failed: {e}")
        raise HTTPException(500, str(e))


@router.post("/registry/repair")
async def repair_registry(dry_run: bool = True):
    """
    Repair registry by registering orphaned DuckDB tables and ChromaDB documents.
    
    Args:
        dry_run: If True, only preview what would be registered. If False, actually register.
    """
    try:
        # Get current status
        status = await get_registry_status()
        
        if not status.get('success'):
            raise HTTPException(500, "Could not get registry status")
        
        orphan_tables = status.get('orphans', {}).get('tables', [])
        orphan_docs = status.get('orphans', {}).get('documents', [])
        
        if dry_run:
            return {
                'success': True,
                'dry_run': True,
                'would_register': {
                    'tables': len(orphan_tables),
                    'documents': len(orphan_docs),
                    'details': {
                        'tables': orphan_tables,
                        'documents': orphan_docs
                    }
                },
                'message': 'Set dry_run=false to actually register these items'
            }
        
        # Actually register orphans
        try:
            from backend.utils.registration_service import RegistrationService, RegistrationSource
        except ImportError:
            from utils.registration_service import RegistrationService, RegistrationSource
        
        supabase = get_supabase()
        registered = []
        errors = []
        
        # Group tables by source file to register as hybrid if needed
        tables_by_file = {}
        for t in orphan_tables:
            source = t.get('source_filename')
            if source:
                if source not in tables_by_file:
                    tables_by_file[source] = {
                        'tables': [],
                        'total_rows': 0
                    }
                tables_by_file[source]['tables'].append(t.get('table_name'))
                tables_by_file[source]['total_rows'] += t.get('row_count', 0)
        
        # Check if any orphan docs match table source files (hybrid)
        doc_names = {d.get('document_name') for d in orphan_docs}
        
        # Get customer_id from first orphan doc or table
        customer_id = None
        if orphan_docs:
            customer_id = orphan_docs[0].get('customer_id')
        
        # Register each file
        for source_file, info in tables_by_file.items():
            try:
                # Check if this file also has chunks (hybrid)
                chunk_count = 0
                for d in orphan_docs:
                    if d.get('document_name') == source_file:
                        chunk_count = d.get('chunk_count', 0)
                        break
                
                if chunk_count > 0:
                    # Hybrid registration
                    result = RegistrationService.register_hybrid(
                        filename=source_file,
                        customer_id=customer_id,
                        tables_created=info['tables'],
                        row_count=info['total_rows'],
                        chunk_count=chunk_count,
                        truth_type='reality',
                        source=RegistrationSource.MIGRATION
                    )
                else:
                    # Structured only
                    result = RegistrationService.register_structured(
                        filename=source_file,
                        customer_id=customer_id,
                        tables_created=info['tables'],
                        row_count=info['total_rows'],
                        source=RegistrationSource.MIGRATION
                    )
                
                if result.success:
                    registered.append({
                        'filename': source_file,
                        'type': 'hybrid' if chunk_count > 0 else 'structured',
                        'tables': len(info['tables']),
                        'rows': info['total_rows'],
                        'chunks': chunk_count,
                        'registry_id': result.registry_id
                    })
                else:
                    errors.append({
                        'filename': source_file,
                        'error': result.error
                    })
                    
            except Exception as e:
                errors.append({
                    'filename': source_file,
                    'error': str(e)
                })
        
        # Register any remaining docs that weren't part of hybrid
        registered_file_names = {r['filename'] for r in registered}
        for d in orphan_docs:
            doc_name = d.get('document_name')
            if doc_name and doc_name not in registered_file_names:
                try:
                    result = RegistrationService.register_embedded(
                        filename=doc_name,
                        customer_id=d.get('customer_id') or customer_id,
                        chunk_count=d.get('chunk_count', 0),
                        truth_type='intent',
                        source=RegistrationSource.MIGRATION
                    )
                    
                    if result.success:
                        registered.append({
                            'filename': doc_name,
                            'type': 'embedded',
                            'chunks': d.get('chunk_count', 0),
                            'registry_id': result.registry_id
                        })
                    else:
                        errors.append({
                            'filename': doc_name,
                            'error': result.error
                        })
                        
                except Exception as e:
                    errors.append({
                        'filename': doc_name,
                        'error': str(e)
                    })
        
        logger.info(f"[ADMIN] Registry repair: {len(registered)} registered, {len(errors)} errors")
        
        return {
            'success': len(errors) == 0,
            'dry_run': False,
            'registered': registered,
            'errors': errors,
            'summary': {
                'total_registered': len(registered),
                'total_errors': len(errors)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ADMIN] Registry repair failed: {e}")
        raise HTTPException(500, str(e))


@router.post("/registry/sync")
async def sync_registry_tables():
    """
    Sync duckdb_tables field in existing registry entries.
    
    This fixes entries that were registered before duckdb_tables was being saved.
    Matches registry entries to DuckDB tables via source_filename.
    """
    try:
        supabase = get_supabase()
        if not supabase:
            raise HTTPException(500, "Database unavailable")
        
        # Import handlers
        try:
            from utils.structured_data_handler import get_structured_handler
        except ImportError:
            from backend.utils.structured_data_handler import get_structured_handler
        
        try:
            from utils.classification_service import get_classification_service
        except ImportError:
            from backend.utils.classification_service import get_classification_service
        
        handler = get_structured_handler()
        service = get_classification_service(handler, None)
        
        # Get all DuckDB tables with their source files
        tables_by_source = {}
        rows_by_source = {}
        try:
            classifications = service.get_all_table_classifications()
            for c in classifications:
                source = c.source_filename
                if source:
                    if source not in tables_by_source:
                        tables_by_source[source] = []
                        rows_by_source[source] = 0
                    tables_by_source[source].append(c.table_name)
                    rows_by_source[source] += c.row_count or 0
        except Exception as e:
            logger.error(f"[ADMIN] Error getting table classifications: {e}")
            raise HTTPException(500, f"Could not get table info: {e}")
        
        # Get registry entries
        registry = supabase.table('document_registry').select('id, filename, duckdb_tables, row_count').execute()
        
        updated = []
        skipped = []
        errors = []
        
        for entry in registry.data or []:
            filename = entry.get('filename')
            entry_id = entry.get('id')
            current_tables = entry.get('duckdb_tables') or []
            
            if filename in tables_by_source:
                expected_tables = tables_by_source[filename]
                expected_rows = rows_by_source[filename]
                
                # Check if update needed
                if set(current_tables) != set(expected_tables):
                    try:
                        supabase.table('document_registry').update({
                            'duckdb_tables': expected_tables,
                            'row_count': expected_rows
                        }).eq('id', entry_id).execute()
                        
                        updated.append({
                            'filename': filename,
                            'tables_added': expected_tables,
                            'row_count': expected_rows
                        })
                        logger.info(f"[ADMIN] Synced registry: {filename} -> {expected_tables}")
                    except Exception as e:
                        errors.append({
                            'filename': filename,
                            'error': str(e)
                        })
                else:
                    skipped.append({
                        'filename': filename,
                        'reason': 'already_synced'
                    })
            else:
                skipped.append({
                    'filename': filename,
                    'reason': 'no_matching_tables'
                })
        
        return {
            'success': len(errors) == 0,
            'updated': updated,
            'skipped': skipped,
            'errors': errors,
            'summary': {
                'total_updated': len(updated),
                'total_skipped': len(skipped),
                'total_errors': len(errors)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ADMIN] Registry sync failed: {e}")
        raise HTTPException(500, str(e))


# =============================================================================
# TERM MAPPINGS (Natural Language Query Configuration)
# =============================================================================

@router.get("/learning/term-mappings/pending")
async def get_pending_term_mappings(project_id: str = None, user: User = Depends(require_permission(Permissions.OPS_CENTER))):
    """Get pending term mappings awaiting review."""
    try:
        from utils.learning_engine import get_learning_system
    except ImportError:
        from backend.utils.learning_engine import get_learning_system
    
    learning = get_learning_system()
    pending = learning.get_pending_term_mappings(project_id)
    
    if project_id:
        return pending
    else:
        # Return all projects' pending mappings
        return pending


@router.get("/learning/term-mappings/approved")
async def get_approved_term_mappings(project_id: str, user: User = Depends(require_permission(Permissions.OPS_CENTER))):
    """Get approved term mappings for a project."""
    try:
        from utils.learning_engine import get_learning_system
    except ImportError:
        from backend.utils.learning_engine import get_learning_system
    
    learning = get_learning_system()
    return learning.get_approved_term_mappings(project_id)


@router.post("/learning/term-mappings/approve/{project_id}/{mapping_index}")
async def approve_term_mapping(project_id: str, mapping_index: int, user: User = Depends(require_permission(Permissions.OPS_CENTER))):
    """Approve a specific pending term mapping."""
    try:
        from utils.learning_engine import get_learning_system
    except ImportError:
        from backend.utils.learning_engine import get_learning_system
    
    learning = get_learning_system()
    success = learning.approve_term_mapping(project_id, mapping_index, approved_by=user.email if hasattr(user, 'email') else 'admin')
    
    if success:
        # Sync to DuckDB
        try:
            from utils.structured_data_handler import get_structured_handler
        except ImportError:
            from backend.utils.structured_data_handler import get_structured_handler
        
        handler = get_structured_handler()
        learning.sync_term_mappings_to_duckdb(handler.conn, project_id)
        
        return {"success": True, "message": "Mapping approved and synced"}
    else:
        raise HTTPException(400, "Failed to approve mapping")


@router.post("/learning/term-mappings/approve-all/{project_id}")
async def approve_all_term_mappings(project_id: str, min_confidence: float = 0.7, user: User = Depends(require_permission(Permissions.OPS_CENTER))):
    """Approve all pending term mappings above confidence threshold."""
    try:
        from utils.learning_engine import get_learning_system
    except ImportError:
        from backend.utils.learning_engine import get_learning_system
    
    learning = get_learning_system()
    count = learning.approve_all_term_mappings(project_id, min_confidence, approved_by=user.email if hasattr(user, 'email') else 'admin')
    
    if count > 0:
        # Sync to DuckDB
        try:
            from utils.structured_data_handler import get_structured_handler
        except ImportError:
            from backend.utils.structured_data_handler import get_structured_handler
        
        handler = get_structured_handler()
        learning.sync_term_mappings_to_duckdb(handler.conn, project_id)
    
    return {"success": True, "approved_count": count}


@router.post("/learning/term-mappings/reject/{project_id}/{mapping_index}")
async def reject_term_mapping(project_id: str, mapping_index: int, user: User = Depends(require_permission(Permissions.OPS_CENTER))):
    """Reject a pending term mapping."""
    try:
        from utils.learning_engine import get_learning_system
    except ImportError:
        from backend.utils.learning_engine import get_learning_system
    
    learning = get_learning_system()
    success = learning.reject_term_mapping(project_id, mapping_index, rejected_by=user.email if hasattr(user, 'email') else 'admin')
    
    if success:
        return {"success": True, "message": "Mapping rejected"}
    else:
        raise HTTPException(400, "Failed to reject mapping")


@router.post("/learning/term-mappings/discover/{project_id}")
async def discover_term_mappings(project_id: str, vendor: str = "UKG", product: str = "Pro", user: User = Depends(require_permission(Permissions.OPS_CENTER))):
    """Manually trigger term mapping discovery for a project."""
    try:
        from utils.learning_engine import get_learning_system
    except ImportError:
        from backend.utils.learning_engine import get_learning_system
    
    try:
        from utils.structured_data_handler import get_structured_handler
    except ImportError:
        from backend.utils.structured_data_handler import get_structured_handler
    
    learning = get_learning_system()
    handler = get_structured_handler()
    
    discovered = learning.discover_term_mappings(handler.conn, project_id, vendor, product)
    
    return {
        "success": True,
        "discovered_count": len(discovered),
        "mappings": discovered
    }


@router.get("/learning/term-mappings/stats")
async def get_term_mapping_stats(user: User = Depends(require_permission(Permissions.OPS_CENTER))):
    """Get term mapping statistics."""
    try:
        from utils.learning_engine import get_learning_system
    except ImportError:
        from backend.utils.learning_engine import get_learning_system
    
    learning = get_learning_system()
    stats = learning.get_stats()
    
    return stats.get('term_mappings', {})
