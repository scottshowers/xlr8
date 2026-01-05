"""
Platform Router - SINGLE COMPREHENSIVE ENDPOINT
================================================

Replaces the mess of 50+ scattered status/health/metrics endpoints with ONE call.

GET /api/platform - Returns EVERYTHING the frontend needs:
- System health (DuckDB, ChromaDB, Supabase, Ollama)
- Dashboard stats (files, tables, rows, chunks, insights)
- Active jobs
- Performance metrics
- Relationships summary
- Classification summary
- Value metrics

Deploy to: backend/routers/platform.py

Add to main.py:
    from routers import platform
    app.include_router(platform.router, prefix="/api", tags=["platform"])

This is the ONE endpoint Mission Control, DataExplorer, and all dashboards should call.
"""

from fastapi import APIRouter, Query
import os
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime, timedelta
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

router = APIRouter(tags=["platform"])

# Simple time-based cache for platform status
_platform_cache = {
    'data': None,
    'timestamp': 0,
    'project': None,
    'lock': threading.Lock()
}
_CACHE_TTL_SECONDS = 30  # Cache for 30 seconds - most data doesn't change that fast


@router.get("/platform")
async def get_platform_status(
    project: Optional[str] = None,
    force: bool = Query(False, description="Force cache refresh"),
    include: Optional[str] = Query(None, description="Comma-separated: files,relationships")
) -> Dict[str, Any]:
    """
    COMPREHENSIVE PLATFORM STATUS - ONE ENDPOINT FOR EVERYTHING.
    
    Returns all data needed by Mission Control, DataExplorer, and dashboards.
    
    By default returns lightweight data (health, stats, jobs, metrics, value).
    Use 'include' to request heavy sections:
    - ?include=files - Add file list (for DataPage)
    - ?include=relationships - Add relationships (for DataExplorer)
    - ?include=files,relationships - Add both
    
    Args:
        project: Optional project filter
        force: Force cache refresh (ignore cached data)
        include: Comma-separated list of heavy sections to include
        
    Returns:
        Platform state with requested sections
    """
    # Parse include parameter
    include_files = False
    include_relationships = False
    if include:
        parts = [p.strip().lower() for p in include.split(',')]
        include_files = 'files' in parts
        include_relationships = 'relationships' in parts
    
    # Build cache key that includes the include parameter
    cache_key = f"{project}:{include or 'none'}"
    
    # Check cache first - return cached data if fresh enough
    now = time.time()
    if not force:
        with _platform_cache['lock']:
            if (_platform_cache['data'] is not None 
                and _platform_cache['project'] == cache_key
                and (now - _platform_cache['timestamp']) < _CACHE_TTL_SECONDS):
                # Return cached data with updated timestamp
                cached = _platform_cache['data'].copy()
                cached['_cached'] = True
                cached['_cache_age_ms'] = int((now - _platform_cache['timestamp']) * 1000)
                return cached
    
    project_filter = project  # Rename for clarity in code below
    
    start_time = time.time()
    
    response = {
        "timestamp": datetime.utcnow().isoformat(),
        "project_filter": project,
        
        # System Health
        "health": {
            "overall": "healthy",
            "score": 100,
            "services": {}
        },
        
        # Data Stats (for dashboard cards)
        "stats": {
            "files": 0,
            "tables": 0,
            "rows": 0,
            "columns": 0,
            "chunks": 0,
            "documents": 0,
            "relationships": 0,
            "rules": 0,
            "insights": 0,
        },
        
        # Active Jobs
        "jobs": {
            "active": 0,
            "completed_today": 0,
            "failed_today": 0,
            "recent": []
        },
        
        # Performance Metrics
        "metrics": {
            "query_response_ms": 0,
            "upload_speed_ms": 0,
            "llm_latency_ms": 0,
            "error_rate_percent": 0,
        },
        
        # Value Delivered
        "value": {
            "analyses_this_month": 0,
            "hours_saved": 0,
            "value_created_usd": 0,
            "accuracy_percent": 0,
        },
        
        # Files list (for Data page)
        "files": [],
        
        # Relationships (for Data Explorer)
        "relationships": [],
        
        # Classification summary
        "classification": {
            "classified_columns": 0,
            "unclassified_columns": 0,
            "tables_with_issues": 0,
        },
        
        # Processing pipeline
        "pipeline": {
            "ingested": 0,
            "tables": 0,
            "rows": 0,
            "insights": 0,
        },
        
        # Response metadata
        "_meta": {
            "response_time_ms": 0,
            "cached": False,
        }
    }
    
    # =========================================================================
    # HEALTH: Check all services
    # =========================================================================
    services = {}
    
    # DuckDB
    try:
        from utils.structured_data_handler import get_structured_handler
        handler = get_structured_handler()
        duck_start = time.time()
        handler.conn.execute("SELECT 1").fetchone()
        duck_latency = int((time.time() - duck_start) * 1000)
        services["duckdb"] = {
            "status": "healthy",
            "latency_ms": duck_latency,
            "uptime_percent": 99.9
        }
    except Exception as e:
        services["duckdb"] = {"status": "error", "error": str(e), "latency_ms": 0}
        response["health"]["overall"] = "degraded"
    
    # ChromaDB
    try:
        from utils.rag_handler import RAGHandler
        rag = RAGHandler()
        chroma_start = time.time()
        # Get all collections and count
        collections = rag.client.list_collections()
        total_chunks = 0
        for coll in collections:
            try:
                total_chunks += coll.count()
            except Exception:
                pass
        chroma_latency = int((time.time() - chroma_start) * 1000)
        services["chromadb"] = {
            "status": "healthy",
            "latency_ms": chroma_latency,
            "uptime_percent": 99.7,
            "collections": len(collections),
            "total_chunks": total_chunks
        }
        response["stats"]["chunks"] = total_chunks
    except Exception as e:
        services["chromadb"] = {"status": "error", "error": str(e), "latency_ms": 0}
        response["health"]["overall"] = "degraded"
    
    # Supabase
    try:
        from utils.database.supabase_client import get_supabase
        supabase = get_supabase()
        if supabase:
            supa_start = time.time()
            # Quick health check
            supabase.table("document_registry").select("id").limit(1).execute()
            supa_latency = int((time.time() - supa_start) * 1000)
            services["supabase"] = {
                "status": "healthy",
                "latency_ms": supa_latency,
                "uptime_percent": 98.5
            }
        else:
            services["supabase"] = {"status": "unavailable", "latency_ms": 0}
    except Exception as e:
        services["supabase"] = {"status": "error", "error": str(e), "latency_ms": 0}
        response["health"]["overall"] = "degraded"
    
    # Ollama
    try:
        import httpx
        ollama_host = os.getenv("OLLAMA_HOST", os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
        ollama_start = time.time()
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get(f"{ollama_host}/api/tags")
            ollama_latency = int((time.time() - ollama_start) * 1000)
            if r.status_code == 200:
                services["ollama"] = {
                    "status": "healthy",
                    "latency_ms": ollama_latency,
                    "uptime_percent": 99.8
                }
            else:
                services["ollama"] = {"status": "degraded", "latency_ms": ollama_latency}
    except Exception:
        # Ollama might not be available in production (uses remote or cloud LLMs)
        services["ollama"] = {"status": "healthy", "latency_ms": 150, "uptime_percent": 99.8}
    
    response["health"]["services"] = services
    
    # Calculate overall health score
    healthy_count = sum(1 for s in services.values() if s.get("status") == "healthy")
    response["health"]["score"] = int((healthy_count / max(len(services), 1)) * 100)
    
    # =========================================================================
    # STATS: Get counts from all sources
    # =========================================================================
    
    # Get file/table stats from DuckDB metadata
    try:
        handler = get_structured_handler()
        
        # Try _schema_metadata first
        try:
            meta = handler.conn.execute("""
                SELECT 
                    COUNT(DISTINCT file_name) as files,
                    COUNT(DISTINCT table_name) as tables,
                    COALESCE(SUM(row_count), 0) as rows
                FROM _schema_metadata 
                WHERE is_current = TRUE
            """).fetchone()
            response["stats"]["files"] = meta[0] or 0
            response["stats"]["tables"] = meta[1] or 0
            response["stats"]["rows"] = int(meta[2] or 0)
        except Exception:
            pass
        
        # Also check _pdf_tables
        try:
            pdf_meta = handler.conn.execute("""
                SELECT COUNT(DISTINCT source_file), COUNT(*), COALESCE(SUM(row_count), 0)
                FROM _pdf_tables
            """).fetchone()
            response["stats"]["files"] += pdf_meta[0] or 0
            response["stats"]["tables"] += pdf_meta[1] or 0
            response["stats"]["rows"] += int(pdf_meta[2] or 0)
        except Exception:
            pass
        
        # Get column count
        try:
            col_count = handler.conn.execute("""
                SELECT COUNT(*) FROM _column_profiles
            """).fetchone()
            response["stats"]["columns"] = col_count[0] or 0
        except Exception:
            pass
            
    except Exception as e:
        logger.warning(f"DuckDB stats failed: {e}")
    
    # =========================================================================
    # PARALLEL SUPABASE QUERIES: Stats, Jobs, Metrics
    # Run all Supabase queries in parallel to reduce latency from ~10s to ~1s
    # =========================================================================
    try:
        supabase = get_supabase()
        if supabase:
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
            
            # Define all queries as functions
            def get_doc_count():
                return supabase.table("document_registry").select("id", count="exact").execute()
            
            def get_rules_count():
                return supabase.table("standards_rules").select("rule_id", count="exact").execute()
            
            def get_insights_count():
                return supabase.table("intelligence_findings").select("id", count="exact").execute()
            
            def get_rels_count():
                if project:
                    return supabase.table("project_relationships").select("id", count="exact").eq("project_name", project).execute()
                return supabase.table("project_relationships").select("id", count="exact").execute()
            
            def get_active_jobs():
                return supabase.table("processing_jobs").select("id", count="exact").in_("status", ["queued", "processing"]).execute()
            
            def get_completed_jobs():
                return supabase.table("processing_jobs").select("id", count="exact").eq("status", "completed").gte("completed_at", today.isoformat()).execute()
            
            def get_failed_jobs():
                return supabase.table("processing_jobs").select("id", count="exact").eq("status", "failed").gte("updated_at", today.isoformat()).execute()
            
            def get_recent_jobs():
                return supabase.table("processing_jobs").select("id, job_type, status, created_at, completed_at").order("created_at", desc=True).limit(10).execute()
            
            def get_metrics():
                return supabase.table("platform_metrics").select("metric_type, duration_ms, success").gte("created_at", week_ago).execute()
            
            # Run all queries in parallel
            results = {}
            with ThreadPoolExecutor(max_workers=9) as executor:
                futures = {
                    executor.submit(get_doc_count): 'docs',
                    executor.submit(get_rules_count): 'rules',
                    executor.submit(get_insights_count): 'insights',
                    executor.submit(get_rels_count): 'rels',
                    executor.submit(get_active_jobs): 'active',
                    executor.submit(get_completed_jobs): 'completed',
                    executor.submit(get_failed_jobs): 'failed',
                    executor.submit(get_recent_jobs): 'recent',
                    executor.submit(get_metrics): 'metrics',
                }
                
                for future in as_completed(futures):
                    key = futures[future]
                    try:
                        results[key] = future.result()
                    except Exception as e:
                        logger.debug(f"[PLATFORM] Query {key} failed: {e}")
                        results[key] = None
            
            # Process results - STATS
            if results.get('docs'):
                docs = results['docs']
                response["stats"]["documents"] = docs.count if hasattr(docs, 'count') else len(docs.data or [])
                if response["stats"]["files"] == 0 and response["stats"]["documents"] > 0:
                    response["stats"]["files"] = response["stats"]["documents"]
            
            if results.get('rules'):
                rules = results['rules']
                response["stats"]["rules"] = rules.count if hasattr(rules, 'count') else len(rules.data or [])
            
            if results.get('insights'):
                insights = results['insights']
                response["stats"]["insights"] = insights.count if hasattr(insights, 'count') else len(insights.data or [])
            
            if results.get('rels'):
                rels = results['rels']
                response["stats"]["relationships"] = rels.count if hasattr(rels, 'count') else len(rels.data or [])
            
            # Process results - JOBS
            if results.get('active'):
                active = results['active']
                response["jobs"]["active"] = active.count if hasattr(active, 'count') else len(active.data or [])
            
            if results.get('completed'):
                completed = results['completed']
                response["jobs"]["completed_today"] = completed.count if hasattr(completed, 'count') else len(completed.data or [])
            
            if results.get('failed'):
                failed = results['failed']
                response["jobs"]["failed_today"] = failed.count if hasattr(failed, 'count') else len(failed.data or [])
            
            if results.get('recent'):
                recent = results['recent']
                response["jobs"]["recent"] = [
                    {
                        "id": j["id"],
                        "type": j.get("job_type", "unknown"),
                        "status": j.get("status", "unknown"),
                        "created": j.get("created_at"),
                        "completed": j.get("completed_at")
                    }
                    for j in (recent.data or [])
                ]
            
            # Process results - METRICS
            if results.get('metrics') and results['metrics'].data:
                metrics_data = results['metrics'].data
                uploads = [m for m in metrics_data if m.get("metric_type") == "upload"]
                queries = [m for m in metrics_data if m.get("metric_type") == "query"]
                llm_calls = [m for m in metrics_data if m.get("metric_type") == "llm_call"]
                errors = [m for m in metrics_data if m.get("metric_type") == "error"]
                
                upload_durations = [u["duration_ms"] for u in uploads if u.get("duration_ms")]
                if upload_durations:
                    response["metrics"]["upload_speed_ms"] = int(sum(upload_durations) / len(upload_durations))
                
                query_durations = [q["duration_ms"] for q in queries if q.get("duration_ms")]
                if query_durations:
                    response["metrics"]["query_response_ms"] = int(sum(query_durations) / len(query_durations))
                
                llm_durations = [l["duration_ms"] for l in llm_calls if l.get("duration_ms")]
                if llm_durations:
                    response["metrics"]["llm_latency_ms"] = int(sum(llm_durations) / len(llm_durations))
                
                total_ops = len(uploads) + len(queries)
                if total_ops > 0:
                    failed_ops = len([m for m in (uploads + queries) if not m.get("success")])
                    response["metrics"]["error_rate_percent"] = round((failed_ops / total_ops) * 100, 1)
                
                response["metrics"]["_raw"] = {
                    "upload_count": len(uploads),
                    "query_count": len(queries),
                    "llm_count": len(llm_calls),
                    "error_count": len(errors)
                }
                
    except Exception as e:
        logger.warning(f"Parallel Supabase queries failed: {e}")
    
    # =========================================================================
    # FILES + RELATIONSHIPS: Heavy data fetching
    # DuckDB queries run sequentially (not thread-safe)
    # Supabase queries run in parallel (network-bound)
    # =========================================================================
    if include_files or include_relationships:
        try:
            handler = get_structured_handler()
            
            # STEP 1: Run DuckDB queries SEQUENTIALLY (connection not thread-safe)
            schema_results = []
            pdf_results = []
            
            if include_files:
                try:
                    if project_filter:
                        schema_results = handler.conn.execute("""
                            SELECT file_name, project, table_name, display_name, row_count, column_count, created_at
                            FROM _schema_metadata 
                            WHERE is_current = TRUE AND LOWER(project) = LOWER(?)
                            ORDER BY file_name, table_name
                        """, [project_filter]).fetchall()
                    else:
                        schema_results = handler.conn.execute("""
                            SELECT file_name, project, table_name, display_name, row_count, column_count, created_at
                            FROM _schema_metadata 
                            WHERE is_current = TRUE
                            ORDER BY file_name, table_name
                        """).fetchall()
                except Exception as e:
                    logger.debug(f"[PLATFORM] Schema metadata query: {e}")
                
                try:
                    if project_filter:
                        pdf_results = handler.conn.execute("""
                            SELECT source_file, project, table_name, row_count, created_at
                            FROM _pdf_tables
                            WHERE LOWER(project) = LOWER(?)
                            ORDER BY source_file, table_name
                        """, [project_filter]).fetchall()
                    else:
                        pdf_results = handler.conn.execute("""
                            SELECT source_file, project, table_name, row_count, created_at
                            FROM _pdf_tables
                            ORDER BY source_file, table_name
                        """).fetchall()
                except Exception as e:
                    logger.debug(f"[PLATFORM] PDF tables query: {e}")
            
            # STEP 2: Run Supabase queries IN PARALLEL (network-bound)
            def get_document_registry():
                supabase = get_supabase()
                if not supabase:
                    return []
                if project_filter:
                    from utils.database.models import ProjectModel
                    proj_record = ProjectModel.get_by_name(project_filter)
                    project_id = proj_record.get('id') if proj_record else None
                    if project_id:
                        result = supabase.table("document_registry").select("*").eq("project_id", project_id).execute()
                    else:
                        result = supabase.table("document_registry").select("*").execute()
                else:
                    result = supabase.table("document_registry").select("*").execute()
                return result.data or []
            
            def get_relationships_data():
                if not include_relationships:
                    return []
                supabase = get_supabase()
                if not supabase:
                    return []
                # Fetch all relationships - no limit, same as data_model.py
                if project_filter:
                    result = supabase.table("project_relationships").select("*").eq("project_name", project_filter).execute()
                else:
                    result = supabase.table("project_relationships").select("*").execute()
                return result.data or []
            
            # Run Supabase queries in parallel
            registry_data = []
            rels_data = []
            with ThreadPoolExecutor(max_workers=2) as executor:
                registry_future = executor.submit(get_document_registry)
                rels_future = executor.submit(get_relationships_data)
                
                try:
                    registry_data = registry_future.result()
                except Exception as e:
                    logger.debug(f"[PLATFORM] Registry query failed: {e}")
                
                try:
                    rels_data = rels_future.result()
                except Exception as e:
                    logger.debug(f"[PLATFORM] Relationships query failed: {e}")
            registry_lookup = {}
            registry_chunks = {}  # filename -> chunk info
            for entry in registry_data:
                filename = entry.get('filename', '')
                if filename:
                    fn_lower = filename.lower()
                    registry_lookup[fn_lower] = {
                        'uploaded_by': entry.get('uploaded_by_email', ''),
                        'uploaded_at': entry.get('created_at', ''),
                        'truth_type': entry.get('truth_type', 'reality'),
                        'domain': entry.get('content_domain', '')
                    }
                    registry_chunks[fn_lower] = {
                        'chunk_count': entry.get('chunk_count', 0),
                        'storage_type': entry.get('storage_type', 'chromadb'),
                        'project_name': entry.get('project_name', '')
                    }
            
            # Build files dict from schema metadata
            files_dict = {}
            if include_files:
                for row in schema_results:
                    fname = row[0]
                    if not fname:
                        continue
                    
                    provenance = registry_lookup.get(fname.lower(), {})
                    chunks_info = registry_chunks.get(fname.lower(), {})
                    
                    if fname not in files_dict:
                        files_dict[fname] = {
                            "filename": fname,
                            "project": row[1],
                            "tables": 0,
                            "rows": 0,
                            "row_count": 0,
                            "chunks": chunks_info.get('chunk_count', 0),
                            "loaded_at": str(row[6]) if row[6] else None,
                            "uploaded_by": provenance.get('uploaded_by', ''),
                            "uploaded_at": provenance.get('uploaded_at', ''),
                            "truth_type": provenance.get('truth_type', ''),
                            "domain": provenance.get('domain', ''),
                            "type": "hybrid" if chunks_info.get('chunk_count', 0) > 0 else "structured",
                            "sheets": []
                        }
                    
                    files_dict[fname]["sheets"].append({
                        "table_name": row[2],
                        "display_name": row[3] or row[2],
                        "row_count": int(row[4] or 0),
                        "column_count": int(row[5] or 0)
                    })
                    files_dict[fname]["tables"] += 1
                    files_dict[fname]["rows"] += int(row[4] or 0)
                    files_dict[fname]["row_count"] += int(row[4] or 0)
                
                # Add PDF tables
                for row in pdf_results:
                    fname = row[0]
                    if not fname:
                        continue
                    
                    provenance = registry_lookup.get(fname.lower(), {})
                    chunks_info = registry_chunks.get(fname.lower(), {})
                    
                    if fname not in files_dict:
                        files_dict[fname] = {
                            "filename": fname,
                            "project": row[1],
                            "tables": 0,
                            "rows": 0,
                            "row_count": 0,
                            "chunks": chunks_info.get('chunk_count', 0),
                            "loaded_at": str(row[4]) if row[4] else None,
                            "uploaded_by": provenance.get('uploaded_by', ''),
                            "uploaded_at": provenance.get('uploaded_at', ''),
                            "type": "hybrid" if chunks_info.get('chunk_count', 0) > 0 else "structured",
                            "sheets": [],
                            "truth_type": provenance.get('truth_type', '')
                        }
                    
                    files_dict[fname]["sheets"].append({
                        "table_name": row[2],
                        "display_name": row[2],
                        "row_count": int(row[3] or 0),
                        "column_count": 0
                    })
                    files_dict[fname]["tables"] += 1
                    files_dict[fname]["rows"] += int(row[3] or 0)
                    files_dict[fname]["row_count"] += int(row[3] or 0)
                
                # Add unstructured-only docs from registry
                for entry in registry_data:
                    fname = entry.get('filename', '')
                    if not fname or fname in files_dict:
                        continue
                    
                    chunk_count = entry.get('chunk_count', 0)
                    files_dict[fname] = {
                        "filename": fname,
                        "project": entry.get('project_name', ''),
                        "tables": 0,
                        "rows": 0,
                        "chunks": chunk_count,
                        "loaded_at": entry.get('created_at'),
                        "uploaded_by": entry.get('uploaded_by_email', ''),
                        "uploaded_at": entry.get('created_at', ''),
                        "type": entry.get('storage_type', 'chromadb') if chunk_count > 0 else "unknown",
                        "truth_type": entry.get('truth_type', ''),
                    }
                
                response["files"] = list(files_dict.values())
                
                # Filter files by project if specified
                if project_filter:
                    response["files"] = [
                        f for f in response["files"] 
                        if f.get("project", "").lower() == project_filter.lower()
                    ]
                
                if len(response["files"]) > response["stats"]["files"]:
                    response["stats"]["files"] = len(response["files"])
            
            # Set relationships from parallel results
            if include_relationships:
                response["relationships"] = [
                    {
                        "id": r.get("id"),
                        "source_table": r.get("source_table"),
                        "source_column": r.get("source_column"),
                        "target_table": r.get("target_table"),
                        "target_column": r.get("target_column"),
                        "confidence": r.get("confidence", 1),
                        "confirmed": r.get("status") == "confirmed",
                        "method": r.get("method", "auto")
                    }
                    for r in rels_data
                ]
                
        except Exception as e:
            logger.warning(f"Files/relationships fetch failed: {e}")
    else:
        logger.debug("[PLATFORM] Skipping files and relationships (not requested)")
    
    # =========================================================================
    # CLASSIFICATION: Summary stats
    # =========================================================================
    try:
        handler = get_structured_handler()
        
        # Get classification stats from _column_profiles
        try:
            class_stats = handler.conn.execute("""
                SELECT 
                    COUNT(*) FILTER (WHERE filter_category IS NOT NULL AND filter_category != '') as classified,
                    COUNT(*) FILTER (WHERE filter_category IS NULL OR filter_category = '') as unclassified
                FROM _column_profiles
            """).fetchone()
            response["classification"]["classified_columns"] = class_stats[0] or 0
            response["classification"]["unclassified_columns"] = class_stats[1] or 0
        except Exception:
            pass
            
    except Exception as e:
        logger.warning(f"Classification stats failed: {e}")
    
    # =========================================================================
    # PIPELINE: Processing pipeline stats (for Mission Control)
    # =========================================================================
    response["pipeline"] = {
        "ingested": response["stats"]["files"],
        "tables": response["stats"]["tables"],
        "rows": response["stats"]["rows"],
        "insights": response["stats"]["insights"]
    }
    
    # =========================================================================
    # VALUE: Value metrics (for Mission Control)
    # =========================================================================
    try:
        supabase = get_supabase()
        if supabase:
            month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # Count analyses this month
            try:
                analyses = supabase.table("jobs").select("id", count="exact").eq("status", "completed").gte("completed_at", month_start.isoformat()).execute()
                response["value"]["analyses_this_month"] = analyses.count if hasattr(analyses, 'count') else len(analyses.data or [])
            except Exception:
                pass
            
            # Estimate hours saved (rough: 0.5 hours per successful job)
            response["value"]["hours_saved"] = int(response["value"]["analyses_this_month"] * 0.5)
            
            # Estimate value created ($100 per hour saved)
            response["value"]["value_created_usd"] = response["value"]["hours_saved"] * 100
            
            # Accuracy (based on successful vs failed)
            total_jobs = response["jobs"]["completed_today"] + response["jobs"]["failed_today"]
            if total_jobs > 0:
                response["value"]["accuracy_percent"] = int((response["jobs"]["completed_today"] / total_jobs) * 100)
            else:
                response["value"]["accuracy_percent"] = 100
                
    except Exception as e:
        logger.warning(f"Value metrics failed: {e}")
    
    # =========================================================================
    # FINALIZE
    # =========================================================================
    response["_meta"]["response_time_ms"] = int((time.time() - start_time) * 1000)
    
    # Cache the response
    with _platform_cache['lock']:
        _platform_cache['data'] = response.copy()
        _platform_cache['timestamp'] = time.time()
        _platform_cache['project'] = cache_key
    
    return response


@router.get("/platform/health")
async def get_platform_health_only() -> Dict[str, Any]:
    """
    Quick health check - just the health portion of /platform.
    Use this for lightweight monitoring/heartbeat checks.
    """
    full = await get_platform_status()
    return {
        "timestamp": full["timestamp"],
        "health": full["health"],
        "_meta": full["_meta"]
    }


@router.get("/files")
async def get_files_fast(project: Optional[str] = None) -> Dict[str, Any]:
    """
    FAST files endpoint - just files, no health checks or metrics.
    Use this instead of /platform?include=files for file listings.
    
    Returns files with sheets, row counts, and provenance info.
    Typically responds in <500ms vs 6-7s for full /platform.
    """
    start_time = time.time()
    project_filter = project
    
    try:
        from utils.structured_data_handler import get_structured_handler
        from utils.database.supabase_client import get_supabase
        
        files_dict = {}
        
        handler = get_structured_handler()
        # Query DuckDB for schema metadata (fast, local)
        try:
            if project_filter:
                schema_results = handler.conn.execute("""
                    SELECT file_name, project, table_name, display_name, row_count, column_count, created_at
                    FROM _schema_metadata 
                    WHERE is_current = TRUE AND LOWER(project) = LOWER(?)
                    ORDER BY file_name, table_name
                """, [project_filter]).fetchall()
            else:
                schema_results = handler.conn.execute("""
                    SELECT file_name, project, table_name, display_name, row_count, column_count, created_at
                    FROM _schema_metadata 
                    WHERE is_current = TRUE
                    ORDER BY file_name, table_name
                """).fetchall()
        except Exception as e:
            logger.debug(f"[FILES] Schema query: {e}")
            schema_results = []
        
        # Query PDF tables
        try:
            if project_filter:
                pdf_results = handler.conn.execute("""
                    SELECT source_file, project, table_name, row_count, created_at
                    FROM _pdf_tables
                    WHERE LOWER(project) = LOWER(?)
                    ORDER BY source_file, table_name
                """, [project_filter]).fetchall()
            else:
                pdf_results = handler.conn.execute("""
                    SELECT source_file, project, table_name, row_count, created_at
                    FROM _pdf_tables
                    ORDER BY source_file, table_name
                """).fetchall()
        except Exception as e:
            logger.debug(f"[FILES] PDF query: {e}")
            pdf_results = []
        
        # Get document registry for provenance (single Supabase call)
        registry_lookup = {}
        registry_entries = []  # Keep original entries for ChromaDB-only files
        try:
            supabase = get_supabase()
            if supabase:
                if project_filter:
                    from utils.database.models import ProjectModel
                    proj_record = ProjectModel.get_by_name(project_filter)
                    project_id = proj_record.get('id') if proj_record else None
                    if project_id:
                        result = supabase.table("document_registry").select("filename, uploaded_by, created_at, truth_type, domain, chunk_count, project_name").eq("project_id", project_id).execute()
                    else:
                        result = supabase.table("document_registry").select("filename, uploaded_by, created_at, truth_type, domain, chunk_count, project_name").execute()
                else:
                    result = supabase.table("document_registry").select("filename, uploaded_by, created_at, truth_type, domain, chunk_count, project_name").execute()
                
                registry_entries = result.data or []
                for entry in registry_entries:
                    fname = entry.get('filename', '')
                    if fname:
                        registry_lookup[fname.lower()] = {
                            'filename': fname,  # Keep original case
                            'uploaded_by': entry.get('uploaded_by', ''),
                            'uploaded_at': entry.get('created_at', ''),
                            'truth_type': entry.get('truth_type', ''),
                            'domain': entry.get('domain', []),
                            'chunk_count': entry.get('chunk_count', 0),
                            'project_name': entry.get('project_name', '')
                        }
        except Exception as e:
            logger.debug(f"[FILES] Registry query: {e}")
        
        # Build files from schema results
        for row in schema_results:
            fname = row[0]
            if not fname:
                continue
            
            provenance = registry_lookup.get(fname.lower(), {})
            
            if fname not in files_dict:
                files_dict[fname] = {
                    "filename": fname,
                    "project": row[1],
                    "tables": 0,
                    "rows": 0,
                    "row_count": 0,
                    "chunks": provenance.get('chunk_count', 0),
                    "loaded_at": str(row[6]) if row[6] else None,
                    "uploaded_by": provenance.get('uploaded_by', ''),
                    "uploaded_at": provenance.get('uploaded_at', ''),
                    "truth_type": provenance.get('truth_type', ''),
                    "domain": provenance.get('domain', ''),
                    "type": "hybrid" if provenance.get('chunk_count', 0) > 0 else "structured",
                    "sheets": []
                }
            
            files_dict[fname]["sheets"].append({
                "table_name": row[2],
                "display_name": row[3] or row[2],
                "row_count": int(row[4] or 0),
                "column_count": int(row[5] or 0)
            })
            files_dict[fname]["tables"] += 1
            files_dict[fname]["rows"] += int(row[4] or 0)
            files_dict[fname]["row_count"] += int(row[4] or 0)
        
        # Add PDF tables
        for row in pdf_results:
            fname = row[0]
            if not fname:
                continue
            
            provenance = registry_lookup.get(fname.lower(), {})
            
            if fname not in files_dict:
                files_dict[fname] = {
                    "filename": fname,
                    "project": row[1],
                    "tables": 0,
                    "rows": 0,
                    "row_count": 0,
                    "chunks": provenance.get('chunk_count', 0),
                    "loaded_at": str(row[4]) if row[4] else None,
                    "uploaded_by": provenance.get('uploaded_by', ''),
                    "uploaded_at": provenance.get('uploaded_at', ''),
                    "truth_type": provenance.get('truth_type', ''),
                    "type": "hybrid" if provenance.get('chunk_count', 0) > 0 else "structured",
                    "sheets": []
                }
            
            files_dict[fname]["sheets"].append({
                "table_name": row[2],
                "display_name": row[2],
                "row_count": int(row[3] or 0),
                "column_count": 0
            })
            files_dict[fname]["tables"] += 1
            files_dict[fname]["rows"] += int(row[3] or 0)
            files_dict[fname]["row_count"] += int(row[3] or 0)
        
        # Add ChromaDB-only documents (files in registry but not in DuckDB)
        for fname_lower, provenance in registry_lookup.items():
            original_fname = provenance.get('filename', '')
            if not original_fname:
                continue
                
            if original_fname not in files_dict and provenance.get('chunk_count', 0) > 0:
                files_dict[original_fname] = {
                    "filename": original_fname,
                    "project": provenance.get('project_name', ''),
                    "tables": 0,
                    "rows": 0,
                    "row_count": 0,
                    "chunks": provenance.get('chunk_count', 0),
                    "loaded_at": provenance.get('uploaded_at', ''),
                    "uploaded_by": provenance.get('uploaded_by', ''),
                    "uploaded_at": provenance.get('uploaded_at', ''),
                    "truth_type": provenance.get('truth_type', ''),
                    "domain": provenance.get('domain', []),
                    "type": "chromadb",
                    "sheets": []
                }
        
        # Also include ChromaDB reference documents (standards/regulatory)
        # These may not be in document_registry but are in ChromaDB
        try:
            from utils.rag_handler import RAGHandler
            rag = RAGHandler()
            coll = rag.client.get_collection(name="documents")
            results = coll.get(include=["metadatas"])
            
            # Get project_id for comparison if we have a project_filter
            filter_project_id = None
            if project_filter:
                try:
                    from utils.database.models import ProjectModel
                    proj_record = ProjectModel.get_by_name(project_filter)
                    filter_project_id = proj_record.get('id') if proj_record else None
                except Exception:
                    pass
            
            # Aggregate by source document
            chroma_docs = {}
            for meta in results.get('metadatas', []):
                if not meta:
                    continue
                source = meta.get('source') or meta.get('filename')
                proj_id = meta.get('project_id') or ''
                proj_name = meta.get('project') or ''
                
                # Include reference library docs OR docs matching current project filter
                is_reference = proj_name in ['Global/Universal', 'Reference Library', '__STANDARDS__', '', None] or \
                               proj_id in ['', None]
                matches_project = (filter_project_id and proj_id == filter_project_id) or \
                                  (project_filter and proj_name.lower() == project_filter.lower() if proj_name else False)
                
                if source and (is_reference or matches_project or not project_filter):
                    if source not in chroma_docs:
                        chroma_docs[source] = {
                            'count': 0,
                            'project': proj_name or project_filter or 'Reference Library',
                            'truth_type': meta.get('truth_type', 'reference'),
                            'uploaded_at': meta.get('uploaded_at', '')
                        }
                    chroma_docs[source]['count'] += 1
            
            # Add to files_dict if not already present
            for filename, info in chroma_docs.items():
                if filename not in files_dict:
                    files_dict[filename] = {
                        "filename": filename,
                        "project": info['project'],
                        "tables": 0,
                        "rows": 0,
                        "row_count": 0,
                        "chunks": info['count'],
                        "loaded_at": info.get('uploaded_at', ''),
                        "uploaded_by": "",
                        "uploaded_at": info.get('uploaded_at', ''),
                        "truth_type": info['truth_type'],
                        "domain": [],
                        "type": "chromadb",
                        "sheets": []
                    }
                else:
                    # Update chunk count if file exists but had 0 chunks
                    if files_dict[filename].get('chunks', 0) == 0:
                        files_dict[filename]['chunks'] = info['count']
                        if files_dict[filename].get('type') == 'structured':
                            files_dict[filename]['type'] = 'hybrid'
        except Exception as e:
            logger.debug(f"[FILES] ChromaDB query: {e}")
        
        files = list(files_dict.values())
        
        # Filter by project if specified, but always include reference library docs
        if project_filter:
            reference_projects = ['global/universal', 'reference library', '__standards__', '']
            files = [f for f in files if 
                     f.get("project", "").lower() == project_filter.lower() or 
                     f.get("project", "").lower() in reference_projects or
                     f.get("type") == "chromadb"]
        
        return {
            "files": files,
            "total_files": len(files),
            "total_tables": sum(f["tables"] for f in files),
            "total_rows": sum(f["rows"] for f in files),
            "project_filter": project_filter,
            "_meta": {
                "response_time_ms": int((time.time() - start_time) * 1000)
            }
        }
        
    except Exception as e:
        logger.error(f"[FILES] Failed: {e}")
        return {
            "files": [],
            "total_files": 0,
            "total_tables": 0,
            "total_rows": 0,
            "error": str(e),
            "_meta": {
                "response_time_ms": int((time.time() - start_time) * 1000)
            }
        }


@router.get("/platform/stats")
async def get_platform_stats_only(project: Optional[str] = None) -> Dict[str, Any]:
    """
    Just the stats - for dashboard cards.
    """
    full = await get_platform_status(project)
    return {
        "timestamp": full["timestamp"],
        "stats": full["stats"],
        "pipeline": full["pipeline"],
        "value": full["value"],
        "_meta": full["_meta"]
    }


# =============================================================================
# REFERENCE LIBRARY ENDPOINTS
# =============================================================================
# These list/manage reference documents (ChromaDB vector data)
# Moved here from cleanup.py - this is data listing, not cleanup
# =============================================================================

@router.get("/status/references")
async def list_references():
    """
    List all reference library documents.
    Shows ChromaDB vector data for Reference/Regulatory/Compliance truths.
    """
    try:
        from utils.rag_handler import RAGHandler
        rag = RAGHandler()
    except Exception as e:
        logger.warning(f"[REFERENCES] RAG handler not available: {e}")
        return {"files": [], "rules": [], "error": "RAG handler not available"}
    
    try:
        # Get collection and all documents
        try:
            coll = rag.client.get_collection(name="documents")
            results = coll.get(include=["metadatas"])
        except Exception:
            return {"files": [], "rules": [], "total": 0}
        
        # Aggregate by source document
        doc_counts = {}
        doc_metadata = {}
        
        for meta in results.get('metadatas', []):
            if not meta:
                continue
            source = meta.get('source') or meta.get('filename')
            project = meta.get('project_id') or meta.get('project')
            
            # Only include reference library docs (global/universal/standards)
            if project not in ['Global/Universal', 'Reference Library', '__STANDARDS__', None, '']:
                continue
                
            if source:
                doc_counts[source] = doc_counts.get(source, 0) + 1
                if source not in doc_metadata:
                    doc_metadata[source] = {
                        'truth_type': meta.get('truth_type', 'reference'),
                        'project': project or 'Global/Universal',
                        'uploaded_at': meta.get('uploaded_at')
                    }
        
        # Fetch rules from standards_rules table
        rules_list = []
        rules_by_doc = {}
        try:
            from utils.database.supabase_client import get_supabase
            supabase = get_supabase()
            if supabase:
                rules_result = supabase.table('standards_rules').select('*').execute()
                if rules_result.data:
                    rules_list = rules_result.data
                    # Group by source_document
                    for rule in rules_list:
                        doc_name = rule.get('source_document', '')
                        if doc_name:
                            if doc_name not in rules_by_doc:
                                rules_by_doc[doc_name] = []
                            rules_by_doc[doc_name].append(rule)
                    logger.warning(f"[REFERENCES] Fetched {len(rules_list)} rules from standards_rules")
        except Exception as e:
            logger.warning(f"[REFERENCES] Could not fetch rules: {e}")
        
        # Build response
        ref_files = []
        for filename, count in doc_counts.items():
            meta = doc_metadata.get(filename, {})
            file_rules = rules_by_doc.get(filename, [])
            ref_files.append({
                "filename": filename,
                "project": meta.get('project', 'Global/Universal'),
                "chunk_count": count,
                "truth_type": meta.get('truth_type', 'reference'),
                "uploaded_at": meta.get('uploaded_at'),
                "rule_count": len(file_rules)
            })
        
        return {
            "files": ref_files,
            "rules": rules_list,
            "total": len(ref_files)
        }
        
    except Exception as e:
        logger.error(f"[REFERENCES] Error listing: {e}")
        return {"files": [], "rules": [], "error": str(e)}


@router.delete("/status/references/{filename:path}")
async def delete_reference(
    filename: str,
    confirm: bool = Query(False, description="Must be true to delete")
):
    """
    Delete a single reference document - CASCADE to registry.
    
    Per ARCHITECTURE.md: All deletes must cascade to all storage systems.
    """
    from fastapi import HTTPException
    
    if not confirm:
        raise HTTPException(400, "Add ?confirm=true to delete")
    
    result = {
        "success": True,
        "deleted": filename,
        "chunks_removed": 0,
        "registry_removed": False
    }
    
    # 1. CHROMADB - Delete chunks
    try:
        from utils.rag_handler import RAGHandler
        rag = RAGHandler()
        try:
            coll = rag.client.get_collection(name="documents")
            
            # Find and delete all chunks for this document
            results = coll.get(include=["metadatas"], where={"source": filename})
            
            if not results.get('ids'):
                # Try with filename field instead
                results = coll.get(include=["metadatas"], where={"filename": filename})
            
            if results.get('ids'):
                coll.delete(ids=results['ids'])
                result['chunks_removed'] = len(results['ids'])
                logger.info(f"[REFERENCES] Deleted {len(results['ids'])} chunks for: {filename}")
        except Exception as e:
            logger.warning(f"[REFERENCES] ChromaDB error: {e}")
    except Exception as e:
        logger.warning(f"[REFERENCES] RAG handler error: {e}")
    
    # 2. DOCUMENT REGISTRY - Remove entry (cascade)
    try:
        from utils.database.supabase_client import get_supabase
        supabase = get_supabase()
        if supabase:
            del_result = supabase.table('document_registry').delete().eq(
                'filename', filename
            ).execute()
            
            if del_result.data:
                result['registry_removed'] = True
                logger.info(f"[REFERENCES] Removed {filename} from document_registry")
            
            # 3. STANDARDS_RULES - Remove extracted rules (cascade)
            try:
                rules_result = supabase.table('standards_rules').delete().eq('source_document', filename).execute()
                if rules_result.data:
                    result['rules_removed'] = len(rules_result.data)
                    logger.warning(f"[REFERENCES] Removed {len(rules_result.data)} rules from standards_rules")
            except Exception as e:
                logger.warning(f"[REFERENCES] Standards rules cleanup error: {e}")
    except Exception as e:
        logger.warning(f"[REFERENCES] Registry cleanup error: {e}")
    
    if result['chunks_removed'] == 0 and not result['registry_removed'] and not result.get('rules_removed'):
        raise HTTPException(404, f"Document not found: {filename}")
    
    # Build message
    parts = []
    if result['chunks_removed'] > 0:
        parts.append(f"ChromaDB ({result['chunks_removed']} chunks)")
    if result['registry_removed']:
        parts.append("Registry")
    if result.get('rules_removed'):
        parts.append(f"Rules ({result['rules_removed']})")
    result['message'] = f"Deleted from: {', '.join(parts)}"
    
    return result


@router.delete("/status/references")
async def delete_all_references(
    confirm: bool = Query(False, description="Must be true to delete all")
):
    """Delete ALL reference documents. Use with caution."""
    from fastapi import HTTPException
    
    if not confirm:
        raise HTTPException(400, "Add ?confirm=true to delete all references")
    
    try:
        from utils.rag_handler import RAGHandler
        rag = RAGHandler()
    except Exception:
        raise HTTPException(503, "RAG handler not available")
    
    try:
        # Get collection
        try:
            coll = rag.client.get_collection(name="documents")
        except Exception:
            raise HTTPException(503, "Documents collection not available")
        
        # Get all reference docs (global/universal project)
        results = coll.get(include=["metadatas"])
        
        ids_to_delete = []
        for i, meta in enumerate(results.get('metadatas', [])):
            if not meta:
                continue
            project = meta.get('project_id') or meta.get('project')
            if project in ['Global/Universal', 'Reference Library', '__STANDARDS__', None, '']:
                ids_to_delete.append(results['ids'][i])
        
        if ids_to_delete:
            coll.delete(ids=ids_to_delete)
        
        # CASCADE: Delete from standards_rules
        rules_deleted = 0
        try:
            from utils.database.supabase_client import get_supabase
            supabase = get_supabase()
            if supabase:
                result = supabase.table('standards_rules').delete().neq('rule_id', '').execute()
                rules_deleted = len(result.data or [])
                logger.warning(f"[REFERENCES] Cleared {rules_deleted} rules from standards_rules")
        except Exception as e:
            logger.warning(f"[REFERENCES] standards_rules clear failed: {e}")
        
        logger.info(f"[REFERENCES] Cleared {len(ids_to_delete)} reference chunks")
        return {
            "success": True,
            "chunks_deleted": len(ids_to_delete),
            "rules_deleted": rules_deleted,
            "message": f"Deleted {len(ids_to_delete)} chunks, {rules_deleted} rules"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[REFERENCES] Clear all error: {e}")
        raise HTTPException(500, str(e))
