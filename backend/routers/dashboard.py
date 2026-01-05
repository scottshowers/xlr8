"""
Dashboard Router - Real Platform Intelligence
==============================================

Single endpoint for dashboard data with REAL metrics:
- Pipeline health (actual tests, not just pings)
- Data by Truth Type
- Lineage tracking (file → tables provenance)
- Relationship coverage
- Attention items (failures, stuck jobs)
- Historical activity graphs

Deploy to: backend/routers/dashboard.py
"""

import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

# Cache for expensive operations
_dashboard_cache = {
    'data': None,
    'timestamp': 0,
    'lock': __import__('threading').Lock()
}
_CACHE_TTL_SECONDS = 15  # Short TTL - dashboard should be fresh


def _get_supabase():
    """Get Supabase client."""
    try:
        from utils.database.supabase_client import get_supabase
        return get_supabase()
    except Exception:
        return None


def _get_duckdb():
    """Get DuckDB handler for dashboard operations."""
    try:
        try:
            from utils.structured_data_handler import get_structured_handler
        except ImportError:
            from backend.utils.structured_data_handler import get_structured_handler
        return get_structured_handler()
    except Exception:
        return None


def _get_chromadb():
    """Get ChromaDB client."""
    try:
        from utils.rag_handler import RAGHandler
        return RAGHandler()
    except Exception:
        return None


# =============================================================================
# PIPELINE HEALTH - Real Tests
# =============================================================================

def test_pipeline_upload() -> Dict:
    """Test upload pipeline with a real operation."""
    start = time.time()
    try:
        handler = _get_duckdb()
        if not handler:
            return {"healthy": False, "error": "DuckDB unavailable", "latency_ms": 0}
        
        # Test: Can we create and query a table?
        test_table = "_dashboard_test_upload"
        handler.conn.execute(f"CREATE OR REPLACE TABLE {test_table} AS SELECT 1 as test_col")
        result = handler.conn.execute(f"SELECT * FROM {test_table}").fetchone()
        handler.conn.execute(f"DROP TABLE IF EXISTS {test_table}")
        
        latency = int((time.time() - start) * 1000)
        return {"healthy": result is not None, "latency_ms": latency}
    except Exception as e:
        return {"healthy": False, "error": str(e), "latency_ms": int((time.time() - start) * 1000)}


def test_pipeline_process() -> Dict:
    """Test processing pipeline - schema metadata operations."""
    start = time.time()
    try:
        handler = _get_duckdb()
        if not handler:
            return {"healthy": False, "error": "DuckDB unavailable", "latency_ms": 0}
        
        # Test: Can we read schema metadata?
        try:
            result = handler.conn.execute("""
                SELECT COUNT(*) FROM _schema_metadata WHERE is_current = TRUE
            """).fetchone()
            tables_tracked = result[0] if result else 0
        except Exception:
            # Table might not exist yet - that's OK
            tables_tracked = 0
        
        latency = int((time.time() - start) * 1000)
        return {"healthy": True, "latency_ms": latency, "tables_tracked": tables_tracked}
    except Exception as e:
        return {"healthy": False, "error": str(e), "latency_ms": int((time.time() - start) * 1000)}


def test_pipeline_query() -> Dict:
    """Test query pipeline - intelligence engine readiness."""
    start = time.time()
    try:
        handler = _get_duckdb()
        if not handler:
            return {"healthy": False, "error": "DuckDB unavailable", "latency_ms": 0}
        
        # Test: Can we run a real aggregation on column profiles?
        try:
            result = handler.conn.execute("""
                SELECT COUNT(*), COUNT(DISTINCT table_name)
                FROM _column_profiles
            """).fetchone()
            columns = result[0] if result else 0
            tables = result[1] if result else 0
        except Exception:
            columns, tables = 0, 0
        
        latency = int((time.time() - start) * 1000)
        return {"healthy": True, "latency_ms": latency, "columns_profiled": columns, "tables_profiled": tables}
    except Exception as e:
        return {"healthy": False, "error": str(e), "latency_ms": int((time.time() - start) * 1000)}


def test_pipeline_semantic() -> Dict:
    """Test semantic pipeline - ChromaDB readiness."""
    start = time.time()
    try:
        rag = _get_chromadb()
        if not rag:
            return {"healthy": False, "error": "ChromaDB unavailable", "latency_ms": 0}
        
        # Test: Can we list collections and count?
        collections = rag.client.list_collections()
        total_chunks = 0
        for coll in collections:
            try:
                total_chunks += coll.count()
            except Exception:
                pass
        
        latency = int((time.time() - start) * 1000)
        return {"healthy": True, "latency_ms": latency, "collections": len(collections), "chunks": total_chunks}
    except Exception as e:
        return {"healthy": False, "error": str(e), "latency_ms": int((time.time() - start) * 1000)}


# =============================================================================
# DATA SUMMARY BY TRUTH TYPE
# =============================================================================

def get_data_by_truth_type() -> Dict:
    """Get data breakdown by Five Truths classification."""
    result = {
        "reality": {"files": 0, "tables": 0, "rows": 0},
        "configuration": {"files": 0, "tables": 0, "rows": 0},
        "reference": {"files": 0, "chunks": 0},
        "regulatory": {"files": 0, "chunks": 0},
        "intent": {"files": 0, "chunks": 0},
        "compliance": {"files": 0, "chunks": 0},
        "unclassified": {"files": 0}
    }
    
    try:
        supabase = _get_supabase()
        if supabase:
            # Get from document_registry
            docs = supabase.table("document_registry").select(
                "truth_type, storage_type, row_count, chunk_count"
            ).execute()
            
            for doc in (docs.data or []):
                truth = (doc.get("truth_type") or "unclassified").lower()
                storage = doc.get("storage_type") or ""
                
                if truth not in result:
                    truth = "unclassified"
                
                result[truth]["files"] = result[truth].get("files", 0) + 1
                
                # DuckDB storage = structured (reality, configuration)
                if "duckdb" in storage.lower():
                    result[truth]["tables"] = result[truth].get("tables", 0) + 1
                    result[truth]["rows"] = result[truth].get("rows", 0) + (doc.get("row_count") or 0)
                
                # ChromaDB storage = semantic (reference, regulatory, intent)
                if "chroma" in storage.lower():
                    result[truth]["chunks"] = result[truth].get("chunks", 0) + (doc.get("chunk_count") or 0)
    
    except Exception as e:
        logger.warning(f"[DASHBOARD] Truth type query failed: {e}")
    
    return result


# =============================================================================
# LINEAGE TRACKING
# =============================================================================

def get_lineage_summary() -> Dict:
    """Get lineage tracking summary and recent activity."""
    result = {
        "total_edges": 0,
        "files_tracked": 0,
        "tables_created": 0,
        "recent": []
    }
    
    try:
        supabase = _get_supabase()
        if supabase:
            # Count total edges
            edges = supabase.table("lineage_edges").select("id", count="exact").execute()
            result["total_edges"] = edges.count if hasattr(edges, 'count') else len(edges.data or [])
            
            # Get unique source files
            file_edges = supabase.table("lineage_edges").select(
                "source_id, target_id, target_type, relationship, created_at, metadata"
            ).eq("source_type", "file").order("created_at", desc=True).limit(50).execute()
            
            files_seen = set()
            tables_seen = set()
            recent = []
            
            for edge in (file_edges.data or []):
                source = edge.get("source_id")
                target = edge.get("target_id")
                target_type = edge.get("target_type")
                
                files_seen.add(source)
                if target_type == "table":
                    tables_seen.add(target)
                
                # Build recent activity (group by file)
                if len(recent) < 10:
                    existing = next((r for r in recent if r["file"] == source), None)
                    if existing:
                        if target_type == "table" and target not in existing["tables"]:
                            existing["tables"].append(target)
                            existing["rows"] += (edge.get("metadata") or {}).get("row_count", 0)
                    else:
                        recent.append({
                            "file": source,
                            "tables": [target] if target_type == "table" else [],
                            "rows": (edge.get("metadata") or {}).get("row_count", 0),
                            "timestamp": edge.get("created_at")
                        })
            
            result["files_tracked"] = len(files_seen)
            result["tables_created"] = len(tables_seen)
            result["recent"] = recent[:5]
    
    except Exception as e:
        logger.warning(f"[DASHBOARD] Lineage query failed: {e}")
    
    return result


# =============================================================================
# RELATIONSHIP COVERAGE
# =============================================================================

def get_relationship_summary() -> Dict:
    """Get table relationship coverage."""
    result = {
        "total_relationships": 0,
        "tables_with_relationships": 0,
        "tables_total": 0,
        "tables_orphaned": 0,
        "coverage_percent": 0,
        "by_type": {}
    }
    
    try:
        handler = _get_duckdb()
        supabase = _get_supabase()
        
        # Get total tables from DuckDB
        if handler:
            try:
                tables = handler.conn.execute("""
                    SELECT COUNT(DISTINCT table_name) FROM _schema_metadata WHERE is_current = TRUE
                """).fetchone()
                result["tables_total"] = tables[0] if tables else 0
            except Exception:
                # Fallback: count all user tables
                try:
                    tables = handler.conn.execute("""
                        SELECT COUNT(*) FROM information_schema.tables 
                        WHERE table_schema = 'main' AND table_name NOT LIKE '\\_%' ESCAPE '\\'
                    """).fetchone()
                    result["tables_total"] = tables[0] if tables else 0
                except Exception:
                    pass
        
        # Get relationships from Supabase
        if supabase:
            rels = supabase.table("project_relationships").select(
                "source_table, target_table, relationship_type"
            ).execute()
            
            tables_in_rels = set()
            type_counts = {}
            
            for rel in (rels.data or []):
                tables_in_rels.add(rel.get("source_table"))
                tables_in_rels.add(rel.get("target_table"))
                
                rel_type = rel.get("relationship_type") or "unknown"
                type_counts[rel_type] = type_counts.get(rel_type, 0) + 1
            
            result["total_relationships"] = len(rels.data or [])
            result["tables_with_relationships"] = len(tables_in_rels)
            result["by_type"] = type_counts
        
        # Calculate coverage
        result["tables_orphaned"] = max(0, result["tables_total"] - result["tables_with_relationships"])
        if result["tables_total"] > 0:
            result["coverage_percent"] = round(
                (result["tables_with_relationships"] / result["tables_total"]) * 100, 1
            )
    
    except Exception as e:
        logger.warning(f"[DASHBOARD] Relationship query failed: {e}")
    
    return result


# =============================================================================
# ATTENTION ITEMS
# =============================================================================

def get_attention_items() -> List[Dict]:
    """Get items that need attention."""
    items = []
    
    try:
        supabase = _get_supabase()
        handler = _get_duckdb()
        
        if supabase:
            # Failed jobs in last 24 hours
            yesterday = (datetime.utcnow() - timedelta(hours=24)).isoformat()
            failed = supabase.table("processing_jobs").select(
                "id, job_type, error_message, created_at"
            ).eq("status", "failed").gte("created_at", yesterday).limit(5).execute()
            
            for job in (failed.data or []):
                items.append({
                    "type": "failed_upload",
                    "severity": "error",
                    "message": f"Failed: {job.get('job_type', 'upload')}",
                    "detail": job.get("error_message", "")[:100],
                    "time": job.get("created_at"),
                    "job_id": job.get("id")
                })
            
            # Stuck jobs (processing for > 15 min)
            stuck_cutoff = (datetime.utcnow() - timedelta(minutes=15)).isoformat()
            stuck = supabase.table("processing_jobs").select(
                "id, job_type, created_at"
            ).in_("status", ["queued", "processing"]).lt("created_at", stuck_cutoff).limit(3).execute()
            
            for job in (stuck.data or []):
                items.append({
                    "type": "stuck_job",
                    "severity": "warning",
                    "message": f"Job stuck > 15 min",
                    "detail": job.get("job_type", "unknown"),
                    "time": job.get("created_at"),
                    "job_id": job.get("id")
                })
        
        if handler:
            # Tables missing profiles
            try:
                missing = handler.conn.execute("""
                    SELECT COUNT(DISTINCT m.table_name)
                    FROM _schema_metadata m
                    LEFT JOIN _column_profiles p ON m.table_name = p.table_name
                    WHERE m.is_current = TRUE AND p.table_name IS NULL
                """).fetchone()
                
                if missing and missing[0] > 0:
                    items.append({
                        "type": "missing_profiles",
                        "severity": "warning",
                        "message": f"{missing[0]} tables missing column profiles",
                        "detail": "Run profiling to enable intelligent queries",
                        "count": missing[0]
                    })
            except Exception:
                pass
            
            # Unclassified tables
            try:
                unclassified = handler.conn.execute("""
                    SELECT COUNT(*) FROM _schema_metadata 
                    WHERE is_current = TRUE AND (truth_type IS NULL OR truth_type = '')
                """).fetchone()
                
                if unclassified and unclassified[0] > 0:
                    items.append({
                        "type": "unclassified",
                        "severity": "info",
                        "message": f"{unclassified[0]} tables need classification",
                        "count": unclassified[0]
                    })
            except Exception:
                pass
    
    except Exception as e:
        logger.warning(f"[DASHBOARD] Attention items query failed: {e}")
    
    return items


# =============================================================================
# HISTORICAL ACTIVITY
# =============================================================================

def get_activity_history(days: int = 30) -> Dict:
    """Get historical activity for graphs."""
    result = {
        "uploads_by_day": [],
        "queries_by_day": [],
        "period_days": days
    }
    
    try:
        supabase = _get_supabase()
        if not supabase:
            return result
        
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        # Uploads from processing_jobs
        jobs = supabase.table("processing_jobs").select(
            "created_at, status"
        ).gte("created_at", cutoff).execute()
        
        # Group by day
        upload_days = {}
        for job in (jobs.data or []):
            day = job.get("created_at", "")[:10]  # YYYY-MM-DD
            if day not in upload_days:
                upload_days[day] = {"total": 0, "success": 0, "failed": 0}
            upload_days[day]["total"] += 1
            if job.get("status") == "completed":
                upload_days[day]["success"] += 1
            elif job.get("status") == "failed":
                upload_days[day]["failed"] += 1
        
        result["uploads_by_day"] = [
            {"date": day, **counts}
            for day, counts in sorted(upload_days.items())
        ]
        
        # Queries from chat_history
        chats = supabase.table("chat_history").select(
            "created_at"
        ).eq("role", "user").gte("created_at", cutoff).execute()
        
        query_days = {}
        for chat in (chats.data or []):
            day = chat.get("created_at", "")[:10]
            query_days[day] = query_days.get(day, 0) + 1
        
        result["queries_by_day"] = [
            {"date": day, "count": count}
            for day, count in sorted(query_days.items())
        ]
    
    except Exception as e:
        logger.warning(f"[DASHBOARD] Activity history query failed: {e}")
    
    return result


# =============================================================================
# MAIN ENDPOINT
# =============================================================================

@router.get("")
async def get_dashboard(
    force: bool = Query(False, description="Force cache refresh"),
    days: int = Query(30, ge=1, le=90, description="Days of history")
) -> Dict[str, Any]:
    """
    Get complete dashboard data.
    
    Returns:
        - pipeline_status: Real health tests for each pipeline stage
        - data_summary: Files/tables/rows by Truth Type
        - lineage: Document → Table provenance tracking
        - relationships: Table relationship coverage
        - attention: Items that need action
        - activity: Historical graphs (uploads, queries)
    """
    now = time.time()
    
    # Check cache
    if not force:
        with _dashboard_cache['lock']:
            if (_dashboard_cache['data'] is not None 
                and (now - _dashboard_cache['timestamp']) < _CACHE_TTL_SECONDS):
                cached = _dashboard_cache['data'].copy()
                cached['_cached'] = True
                cached['_cache_age_ms'] = int((now - _dashboard_cache['timestamp']) * 1000)
                return cached
    
    start_time = time.time()
    
    # Run pipeline tests SEQUENTIALLY (DuckDB is NOT thread-safe)
    # Each test is fast (ms), so sequential is fine
    pipeline = {
        'upload': test_pipeline_upload(),
        'process': test_pipeline_process(),
        'query': test_pipeline_query(),
        'semantic': test_pipeline_semantic(),  # ChromaDB - could be parallel but keep simple
    }
    
    # Run data queries SEQUENTIALLY (all touch DuckDB)
    data_summary = {}
    lineage = {}
    relationships = {}
    attention = []
    activity = {}
    
    try:
        data_summary = get_data_by_truth_type()
    except Exception as e:
        logger.warning(f"[DASHBOARD] data_summary failed: {e}")
    
    try:
        lineage = get_lineage_summary()
    except Exception as e:
        logger.warning(f"[DASHBOARD] lineage failed: {e}")
    
    try:
        relationships = get_relationship_summary()
    except Exception as e:
        logger.warning(f"[DASHBOARD] relationships failed: {e}")
    
    try:
        attention = get_attention_items()
    except Exception as e:
        logger.warning(f"[DASHBOARD] attention failed: {e}")
    
    try:
        activity = get_activity_history(days)
    except Exception as e:
        logger.warning(f"[DASHBOARD] activity failed: {e}")
    
    # Calculate overall health
    all_healthy = all(p.get("healthy", False) for p in pipeline.values())
    total_latency = sum(p.get("latency_ms", 0) for p in pipeline.values())
    
    response = {
        "timestamp": datetime.utcnow().isoformat(),
        
        "pipeline_status": {
            "healthy": all_healthy,
            "total_latency_ms": total_latency,
            "last_test": datetime.utcnow().isoformat(),
            "stages": pipeline
        },
        
        "data_summary": {
            "by_truth_type": data_summary,
            "total_files": sum(d.get("files", 0) for d in data_summary.values()),
            "total_tables": sum(d.get("tables", 0) for d in data_summary.values()),
            "total_rows": sum(d.get("rows", 0) for d in data_summary.values()),
            "total_chunks": sum(d.get("chunks", 0) for d in data_summary.values())
        },
        
        "lineage": lineage,
        "relationships": relationships,
        "attention": attention,
        "activity": activity,
        
        "_meta": {
            "response_time_ms": int((time.time() - start_time) * 1000),
            "cached": False
        }
    }
    
    # Cache the response
    with _dashboard_cache['lock']:
        _dashboard_cache['data'] = response.copy()
        _dashboard_cache['timestamp'] = now
    
    return response


@router.get("/pipeline-test")
async def run_pipeline_test() -> Dict[str, Any]:
    """
    Run a quick pipeline health test.
    
    Returns just pipeline status for fast refresh.
    """
    start_time = time.time()
    
    # Run sequentially (DuckDB is NOT thread-safe)
    pipeline = {
        'upload': test_pipeline_upload(),
        'process': test_pipeline_process(),
        'query': test_pipeline_query(),
        'semantic': test_pipeline_semantic(),
    }
    
    all_healthy = all(p.get("healthy", False) for p in pipeline.values())
    
    return {
        "healthy": all_healthy,
        "timestamp": datetime.utcnow().isoformat(),
        "stages": pipeline,
        "response_time_ms": int((time.time() - start_time) * 1000)
    }
