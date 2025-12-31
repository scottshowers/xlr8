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
try:
    from backend.utils.auth_middleware import (
        User, require_permission, Permissions
    )
except ImportError:
    from utils.auth_middleware import (
        User, require_permission, Permissions
    )

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# =============================================================================
# SUPABASE CLIENT
# =============================================================================

def get_supabase():
    """Get Supabase client."""
    try:
        from utils.database.supabase_client import get_supabase
        return get_supabase()
    except ImportError:
        from utils.database.supabase_client import get_supabase
        return get_supabase()


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
