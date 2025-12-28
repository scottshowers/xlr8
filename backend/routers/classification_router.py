"""
Classification Router - API Endpoints for FIVE TRUTHS Transparency
===================================================================

Deploy to: backend/routers/classification_router.py

Then add to main.py:
    from routers.classification_router import router as classification_router
    app.include_router(classification_router, prefix="/api", tags=["classification"])

ENDPOINTS:
- GET /classification/table/{table_name} - Full table classification report
- GET /classification/tables - All tables with classification summary
- GET /classification/chunks/{document_name} - All chunks for a document
- GET /classification/routing - Recent routing decisions (debug)
- POST /classification/reclassify - Update classification for a table/column

Author: XLR8 Team
Version: 1.0.0
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# IMPORTS
# =============================================================================

try:
    from utils.classification_service import get_classification_service, ClassificationService
    CLASSIFICATION_AVAILABLE = True
except ImportError:
    try:
        from backend.utils.classification_service import get_classification_service, ClassificationService
        CLASSIFICATION_AVAILABLE = True
    except ImportError:
        CLASSIFICATION_AVAILABLE = False
        logger.warning("[CLASSIFICATION-API] Classification service not available")

try:
    from utils.structured_data_handler import get_structured_handler
    STRUCTURED_AVAILABLE = True
except ImportError:
    try:
        from backend.utils.structured_data_handler import get_structured_handler
        STRUCTURED_AVAILABLE = True
    except ImportError:
        STRUCTURED_AVAILABLE = False

try:
    from utils.rag_handler import RAGHandler
    RAG_AVAILABLE = True
except ImportError:
    try:
        from backend.utils.rag_handler import RAGHandler
        RAG_AVAILABLE = True
    except ImportError:
        RAG_AVAILABLE = False


def _get_service() -> ClassificationService:
    """Get initialized classification service."""
    if not CLASSIFICATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="Classification service not available")
    
    structured_handler = get_structured_handler() if STRUCTURED_AVAILABLE else None
    rag_handler = RAGHandler() if RAG_AVAILABLE else None
    
    return get_classification_service(structured_handler, rag_handler)


# =============================================================================
# TABLE CLASSIFICATION ENDPOINTS
# =============================================================================

@router.get("/classification/table/{table_name}")
async def get_table_classification(
    table_name: str,
    project_id: Optional[str] = Query(None, description="Filter by project")
):
    """
    Get complete classification report for a table.
    
    Returns:
    - Column types and captured values
    - Filter categories and WHY they were assigned
    - Detected relationships
    - Domain classification
    - Query routing keywords
    """
    service = _get_service()
    
    classification = service.get_table_classification(table_name, project_id)
    
    if not classification:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    
    return {
        "success": True,
        "classification": classification.to_dict()
    }


@router.get("/classification/tables")
async def get_all_table_classifications(
    project_id: Optional[str] = Query(None, description="Filter by project")
):
    """
    Get classification summary for all tables.
    
    Returns a list of tables with their:
    - Display name and row count
    - Domain classification
    - Number of categorical columns
    - Relationship count
    """
    service = _get_service()
    
    classifications = service.get_all_table_classifications(project_id)
    
    # Create summary view
    summaries = []
    for c in classifications:
        categorical_cols = [col for col in c.columns if col.is_categorical]
        summaries.append({
            "table_name": c.table_name,
            "display_name": c.display_name,
            "source_filename": c.source_filename,
            "row_count": c.row_count,
            "column_count": c.column_count,
            "truth_type": c.truth_type,
            "detected_domain": c.detected_domain,
            "domain_confidence": c.domain_confidence,
            "categorical_columns": len(categorical_cols),
            "relationship_count": len(c.relationships),
            "routing_keywords_sample": c.routing_keywords[:10]
        })
    
    return {
        "success": True,
        "tables": summaries,
        "total": len(summaries)
    }


@router.get("/classification/column/{table_name}/{column_name}")
async def get_column_classification(table_name: str, column_name: str):
    """
    Get detailed classification for a specific column.
    
    Returns:
    - All captured values
    - Value distribution
    - Classification reason
    - Sample values
    """
    service = _get_service()
    
    classification = service.get_table_classification(table_name)
    
    if not classification:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    
    column = next((c for c in classification.columns if c.column_name.lower() == column_name.lower()), None)
    
    if not column:
        raise HTTPException(status_code=404, detail=f"Column '{column_name}' not found in table '{table_name}'")
    
    return {
        "success": True,
        "column": {
            "column_name": column.column_name,
            "data_type": column.data_type,
            "inferred_type": column.inferred_type,
            "fill_rate": column.fill_rate,
            "distinct_count": column.distinct_count,
            "is_categorical": column.is_categorical,
            "is_likely_key": column.is_likely_key,
            "filter_category": column.filter_category,
            "classification_reason": column.classification_reason,
            "distinct_values": column.distinct_values,
            "value_distribution": column.value_distribution,
            "sample_values": column.sample_values,
            "min_value": column.min_value,
            "max_value": column.max_value,
            "mean_value": column.mean_value,
            "min_date": column.min_date,
            "max_date": column.max_date
        }
    }


# =============================================================================
# CHUNK CLASSIFICATION ENDPOINTS
# =============================================================================

@router.get("/classification/chunks/{document_name}")
async def get_document_chunks(
    document_name: str,
    project_id: Optional[str] = Query(None, description="Filter by project"),
    collection: str = Query("documents", description="ChromaDB collection name")
):
    """
    Get all chunks for a document with their metadata.
    
    Returns:
    - Total chunk count
    - Each chunk with:
      - Preview text (first 500 chars)
      - Truth type
      - Structure/strategy metadata
      - Position info
    """
    service = _get_service()
    
    if not service.rag_handler:
        raise HTTPException(status_code=503, detail="RAG handler not available")
    
    chunks = service.get_document_chunks(document_name, project_id, collection)
    
    if not chunks:
        raise HTTPException(status_code=404, detail=f"Document '{document_name}' not found")
    
    return {
        "success": True,
        "document": chunks.to_dict()
    }


@router.get("/classification/chunks")
async def list_all_documents_with_chunks(
    project_id: Optional[str] = Query(None, description="Filter by project"),
    collection: str = Query("documents", description="ChromaDB collection name")
):
    """
    List all documents with chunk counts.
    """
    service = _get_service()
    
    if not service.rag_handler:
        raise HTTPException(status_code=503, detail="RAG handler not available")
    
    try:
        coll = service.rag_handler.client.get_collection(name=collection)
        
        # Get all unique document names
        results = coll.get(include=["metadatas"])
        
        doc_counts = {}
        doc_metadata = {}
        
        for meta in results.get('metadatas', []):
            if not meta:
                continue
            source = meta.get('source') or meta.get('filename')
            if source:
                doc_counts[source] = doc_counts.get(source, 0) + 1
                if source not in doc_metadata:
                    doc_metadata[source] = {
                        'truth_type': meta.get('truth_type'),
                        'project_id': meta.get('project_id'),
                        'structure': meta.get('structure')
                    }
        
        # Filter by project if specified
        if project_id:
            doc_counts = {
                k: v for k, v in doc_counts.items()
                if doc_metadata.get(k, {}).get('project_id') == project_id
            }
        
        documents = [
            {
                "document_name": name,
                "chunk_count": count,
                "truth_type": doc_metadata.get(name, {}).get('truth_type'),
                "project_id": doc_metadata.get(name, {}).get('project_id'),
                "structure": doc_metadata.get(name, {}).get('structure')
            }
            for name, count in sorted(doc_counts.items())
        ]
        
        return {
            "success": True,
            "documents": documents,
            "total": len(documents)
        }
        
    except Exception as e:
        logger.error(f"[CLASSIFICATION-API] Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ROUTING TRANSPARENCY ENDPOINTS
# =============================================================================

@router.get("/classification/routing")
async def get_routing_decisions(
    limit: int = Query(10, description="Number of recent decisions to return", ge=1, le=50)
):
    """
    Get recent query routing decisions for debugging.
    
    Shows what tables/chunks were considered and why for recent queries.
    """
    service = _get_service()
    
    decisions = service.get_recent_routing_decisions(limit)
    
    return {
        "success": True,
        "decisions": [d.to_dict() for d in decisions],
        "count": len(decisions)
    }


# =============================================================================
# RECLASSIFICATION ENDPOINTS
# =============================================================================

@router.post("/classification/reclassify/column")
async def reclassify_column(
    table_name: str,
    column_name: str,
    new_filter_category: Optional[str] = None,
    new_filter_priority: Optional[int] = None
):
    """
    Update the classification for a column.
    
    Allows users to correct classifications that were wrong.
    """
    service = _get_service()
    
    if not service.structured_handler or not service.structured_handler.conn:
        raise HTTPException(status_code=503, detail="Structured handler not available")
    
    try:
        conn = service.structured_handler.conn
        
        # Build update query
        updates = []
        params = []
        
        if new_filter_category is not None:
            updates.append("filter_category = ?")
            params.append(new_filter_category if new_filter_category else None)
        
        if new_filter_priority is not None:
            updates.append("filter_priority = ?")
            params.append(new_filter_priority)
        
        if not updates:
            raise HTTPException(status_code=400, detail="No updates provided")
        
        params.extend([table_name, column_name])
        
        conn.execute(f"""
            UPDATE _column_profiles
            SET {', '.join(updates)}
            WHERE LOWER(table_name) = LOWER(?) AND LOWER(column_name) = LOWER(?)
        """, params)
        conn.commit()
        
        return {
            "success": True,
            "message": f"Updated classification for {table_name}.{column_name}"
        }
        
    except Exception as e:
        logger.error(f"[CLASSIFICATION-API] Error reclassifying column: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/classification/reclassify/table")
async def reclassify_table(
    table_name: str,
    new_truth_type: Optional[str] = None,
    new_display_name: Optional[str] = None
):
    """
    Update the classification for a table.
    
    Allows users to correct truth_type or set a display name.
    """
    service = _get_service()
    
    if not service.structured_handler or not service.structured_handler.conn:
        raise HTTPException(status_code=503, detail="Structured handler not available")
    
    try:
        conn = service.structured_handler.conn
        
        updates = []
        params = []
        
        if new_truth_type is not None:
            updates.append("truth_type = ?")
            params.append(new_truth_type if new_truth_type else None)
        
        # Note: display_name would need to be added to _schema_metadata schema
        # For now, just handle truth_type
        
        if not updates:
            raise HTTPException(status_code=400, detail="No updates provided")
        
        params.append(table_name)
        
        conn.execute(f"""
            UPDATE _schema_metadata
            SET {', '.join(updates)}
            WHERE LOWER(table_name) = LOWER(?)
        """, params)
        conn.commit()
        
        return {
            "success": True,
            "message": f"Updated classification for table {table_name}"
        }
        
    except Exception as e:
        logger.error(f"[CLASSIFICATION-API] Error reclassifying table: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# HEALTH CHECK
# =============================================================================

@router.get("/classification/health")
async def classification_health():
    """Check classification service availability."""
    return {
        "classification_service": CLASSIFICATION_AVAILABLE,
        "structured_handler": STRUCTURED_AVAILABLE,
        "rag_handler": RAG_AVAILABLE
    }


# =============================================================================
# CUSTOM DOMAINS
# =============================================================================

@router.get("/custom-domains")
async def get_custom_domains():
    """
    Get all custom domains for domain detection.
    These are user-created domains that extend the built-in ones.
    """
    try:
        handler = get_structured_handler()
        
        # Ensure table exists
        handler.conn.execute("""
            CREATE TABLE IF NOT EXISTS _custom_domains (
                id INTEGER PRIMARY KEY,
                name VARCHAR NOT NULL UNIQUE,
                label VARCHAR NOT NULL,
                signals TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR
            )
        """)
        handler.conn.commit()
        
        # Get all domains
        rows = handler.conn.execute("""
            SELECT name, label, signals, created_at 
            FROM _custom_domains
            ORDER BY created_at DESC
        """).fetchall()
        
        domains = []
        for row in rows:
            signals = row[2].split(',') if row[2] else []
            domains.append({
                "value": row[0],
                "label": row[1],
                "signals": signals,
                "created_at": str(row[3]) if row[3] else None
            })
        
        return {"domains": domains}
        
    except Exception as e:
        logger.error(f"[CUSTOM-DOMAINS] Error getting domains: {e}")
        return {"domains": [], "error": str(e)}


@router.post("/custom-domains")
async def create_custom_domain(
    name: str = Query(..., description="Domain identifier (lowercase, no spaces)"),
    label: str = Query(..., description="Display label"),
    signals: List[str] = Query(default=[], description="Signal words for auto-detection")
):
    """
    Create a custom domain for classification.
    
    The domain will be used for:
    1. Manual selection during upload
    2. Auto-detection when column names/values match signal words
    """
    try:
        handler = get_structured_handler()
        
        # Ensure table exists
        handler.conn.execute("""
            CREATE TABLE IF NOT EXISTS _custom_domains (
                id INTEGER PRIMARY KEY,
                name VARCHAR NOT NULL UNIQUE,
                label VARCHAR NOT NULL,
                signals TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR
            )
        """)
        
        # Clean name
        clean_name = name.lower().strip().replace(' ', '_')
        signals_str = ','.join([s.lower().strip() for s in signals if s.strip()])
        
        # Check if exists
        existing = handler.conn.execute(
            "SELECT name FROM _custom_domains WHERE name = ?", 
            [clean_name]
        ).fetchone()
        
        if existing:
            raise HTTPException(status_code=400, detail=f"Domain '{clean_name}' already exists")
        
        # Insert
        handler.conn.execute("""
            INSERT INTO _custom_domains (name, label, signals)
            VALUES (?, ?, ?)
        """, [clean_name, label.strip(), signals_str])
        handler.conn.commit()
        
        logger.info(f"[CUSTOM-DOMAINS] Created domain '{clean_name}' with signals: {signals_str}")
        
        return {
            "success": True,
            "domain": {
                "value": clean_name,
                "label": label.strip(),
                "signals": [s.lower().strip() for s in signals if s.strip()]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CUSTOM-DOMAINS] Error creating domain: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/custom-domains/{domain_name}")
async def delete_custom_domain(domain_name: str):
    """Delete a custom domain."""
    try:
        handler = get_structured_handler()
        
        result = handler.conn.execute(
            "DELETE FROM _custom_domains WHERE name = ?",
            [domain_name.lower()]
        )
        handler.conn.commit()
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Domain '{domain_name}' not found")
        
        return {"success": True, "deleted": domain_name}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CUSTOM-DOMAINS] Error deleting domain: {e}")
        raise HTTPException(status_code=500, detail=str(e))
