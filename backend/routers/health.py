"""
Health Monitoring Router - XLR8 System Diagnostics
===================================================

Provides comprehensive health checks for all subsystems:
- Storage: DuckDB, ChromaDB, Supabase
- Processing: LLM, Background Jobs
- Data Integrity: Cross-system validation

Endpoint: GET /api/health
Optional: ?verbose=true for detailed breakdown

Deploy to: backend/routers/health.py
Register in main.py: app.include_router(health.router, prefix="/api")

Author: XLR8 Team
"""

import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# HEALTH CHECK FUNCTIONS
# =============================================================================

def check_duckdb_health() -> Dict[str, Any]:
    """Check DuckDB storage health."""
    result = {
        "status": "unknown",
        "latency_ms": None,
        "details": {}
    }
    
    start = time.time()
    
    try:
        from utils.structured_data_handler import get_structured_handler
        handler = get_structured_handler()
        
        # Basic connectivity
        conn_start = time.time()
        test = handler.conn.execute("SELECT 1").fetchone()
        result["latency_ms"] = int((time.time() - conn_start) * 1000)
        
        # Database file info
        db_path = handler.db_path
        if os.path.exists(db_path):
            result["details"]["db_file_exists"] = True
            result["details"]["db_file_size_mb"] = round(os.path.getsize(db_path) / (1024 * 1024), 2)
        else:
            result["details"]["db_file_exists"] = False
            result["status"] = "critical"
            return result
        
        # Table counts
        tables = handler.conn.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'main' AND table_type = 'BASE TABLE'
        """).fetchall()
        all_tables = [t[0] for t in tables]
        
        # Separate system tables from data tables
        system_tables = [t for t in all_tables if t.startswith('_')]
        data_tables = [t for t in all_tables if not t.startswith('_')]
        
        result["details"]["total_tables"] = len(all_tables)
        result["details"]["system_tables"] = len(system_tables)
        result["details"]["data_tables"] = len(data_tables)
        
        # Row counts
        total_rows = 0
        empty_tables = []
        table_sizes = []
        
        for table in data_tables:
            try:
                count = handler.conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
                total_rows += count
                table_sizes.append({"table": table, "rows": count})
                if count == 0:
                    empty_tables.append(table)
            except:
                pass
        
        result["details"]["total_rows"] = total_rows
        result["details"]["empty_tables"] = len(empty_tables)
        result["details"]["empty_table_names"] = empty_tables[:5]
        result["details"]["table_sizes"] = sorted(table_sizes, key=lambda x: -x["rows"])[:10]
        
        # Schema metadata check
        try:
            meta_count = handler.conn.execute(
                "SELECT COUNT(*) FROM _schema_metadata WHERE is_current = TRUE"
            ).fetchone()[0]
            result["details"]["schema_metadata_count"] = meta_count
            result["details"]["metadata_table_mismatch"] = meta_count != len(data_tables)
        except:
            result["details"]["schema_metadata_count"] = 0
        
        # Determine status
        if result["details"]["db_file_exists"] and result["latency_ms"] < 1000:
            result["status"] = "healthy"
        elif result["latency_ms"] < 5000:
            result["status"] = "degraded"
        else:
            result["status"] = "critical"
            
    except Exception as e:
        result["status"] = "critical"
        result["error"] = str(e)
        logger.error(f"[HEALTH] DuckDB check failed: {e}")
    
    result["check_time_ms"] = int((time.time() - start) * 1000)
    return result


def check_chromadb_health() -> Dict[str, Any]:
    """Check ChromaDB vector storage health."""
    result = {
        "status": "unknown",
        "latency_ms": None,
        "details": {}
    }
    
    start = time.time()
    
    try:
        from utils.rag_handler import RAGHandler
        rag = RAGHandler()
        
        # Basic connectivity
        conn_start = time.time()
        collection = rag.client.get_or_create_collection(name="documents")
        result["latency_ms"] = int((time.time() - conn_start) * 1000)
        
        # Collection stats
        count = collection.count()
        result["details"]["total_chunks"] = count
        
        # Get unique sources and breakdown
        try:
            all_docs = collection.get(include=["metadatas"], limit=10000)
            sources = set()
            projects = set()
            truth_types = {"reality": 0, "intent": 0, "reference": 0, "unknown": 0}
            
            for meta in all_docs.get("metadatas", []):
                if meta:
                    source = meta.get("source") or meta.get("filename")
                    if source:
                        sources.add(source)
                    project = meta.get("project")
                    if project:
                        projects.add(project)
                    tt = meta.get("truth_type", "unknown")
                    if tt in truth_types:
                        truth_types[tt] += 1
                    else:
                        truth_types["unknown"] += 1
            
            result["details"]["unique_documents"] = len(sources)
            result["details"]["unique_projects"] = len(projects)
            result["details"]["by_truth_type"] = truth_types
            
        except Exception as meta_e:
            logger.warning(f"[HEALTH] ChromaDB metadata scan failed: {meta_e}")
        
        # Determine status
        if result["latency_ms"] < 1000:
            result["status"] = "healthy"
        elif result["latency_ms"] < 5000:
            result["status"] = "degraded"
        else:
            result["status"] = "critical"
            
    except Exception as e:
        result["status"] = "critical"
        result["error"] = str(e)
        logger.error(f"[HEALTH] ChromaDB check failed: {e}")
    
    result["check_time_ms"] = int((time.time() - start) * 1000)
    return result


def check_supabase_health() -> Dict[str, Any]:
    """Check Supabase connection health."""
    result = {
        "status": "unknown",
        "latency_ms": None,
        "details": {}
    }
    
    start = time.time()
    
    try:
        from utils.database.supabase_client import get_supabase
        supabase = get_supabase()
        
        if not supabase:
            result["status"] = "critical"
            result["error"] = "Supabase client not initialized"
            return result
        
        # Test read
        conn_start = time.time()
        response = supabase.table('projects').select('id').limit(1).execute()
        result["latency_ms"] = int((time.time() - conn_start) * 1000)
        
        # Get counts
        try:
            projects = supabase.table('projects').select('id', count='exact').execute()
            result["details"]["projects_count"] = projects.count if hasattr(projects, 'count') else len(projects.data)
        except:
            result["details"]["projects_count"] = "unknown"
        
        try:
            docs = supabase.table('documents').select('id', count='exact').execute()
            result["details"]["documents_count"] = docs.count if hasattr(docs, 'count') else len(docs.data)
        except:
            result["details"]["documents_count"] = "unknown"
        
        try:
            registry = supabase.table('document_registry').select('id', count='exact').execute()
            result["details"]["registry_count"] = registry.count if hasattr(registry, 'count') else len(registry.data)
        except:
            result["details"]["registry_count"] = "unknown"
        
        # Check for stuck jobs
        try:
            from datetime import datetime, timedelta
            cutoff = (datetime.utcnow() - timedelta(minutes=15)).isoformat()
            stuck = supabase.table('processing_jobs').select('id').eq('status', 'processing').lt('created_at', cutoff).execute()
            result["details"]["stuck_jobs"] = len(stuck.data) if stuck.data else 0
        except:
            result["details"]["stuck_jobs"] = "unknown"
        
        # Determine status
        if result["latency_ms"] < 2000:
            result["status"] = "healthy"
        elif result["latency_ms"] < 10000:
            result["status"] = "degraded"
        else:
            result["status"] = "critical"
            
    except Exception as e:
        result["status"] = "critical"
        result["error"] = str(e)
        logger.error(f"[HEALTH] Supabase check failed: {e}")
    
    result["check_time_ms"] = int((time.time() - start) * 1000)
    return result


def check_llm_health() -> Dict[str, Any]:
    """Check LLM (Ollama/RunPod) health."""
    result = {
        "status": "unknown",
        "latency_ms": None,
        "details": {}
    }
    
    start = time.time()
    
    try:
        import requests
        from requests.auth import HTTPBasicAuth
        
        # Get LLM config
        url = os.getenv('LLM_INFERENCE_URL') or os.getenv('OLLAMA_URL') or os.getenv('RUNPOD_URL')
        username = os.getenv('LLM_USERNAME', '')
        password = os.getenv('LLM_PASSWORD', '')
        
        if not url:
            result["status"] = "critical"
            result["error"] = "No LLM endpoint configured"
            return result
        
        result["details"]["endpoint"] = url
        
        # Check if endpoint is reachable
        auth = HTTPBasicAuth(username, password) if username and password else None
        
        # Try to list models
        conn_start = time.time()
        try:
            tags_response = requests.get(f"{url.rstrip('/')}/api/tags", auth=auth, timeout=10)
            result["latency_ms"] = int((time.time() - conn_start) * 1000)
            
            if tags_response.ok:
                models = tags_response.json().get('models', [])
                result["details"]["models_available"] = [m.get('name') for m in models]
                result["details"]["model_count"] = len(models)
            else:
                result["details"]["models_available"] = []
        except:
            # Fallback - just check if generate endpoint responds
            try:
                test_response = requests.post(
                    f"{url.rstrip('/')}/api/generate",
                    json={"model": "mistral:7b", "prompt": "Hi", "stream": False, "options": {"num_predict": 1}},
                    auth=auth,
                    timeout=30
                )
                result["latency_ms"] = int((time.time() - conn_start) * 1000)
                result["details"]["generate_test"] = "success" if test_response.ok else "failed"
            except Exception as gen_e:
                result["latency_ms"] = int((time.time() - conn_start) * 1000)
                result["details"]["generate_test"] = f"failed: {gen_e}"
        
        # Determine status
        if result["latency_ms"] and result["latency_ms"] < 5000:
            result["status"] = "healthy"
        elif result["latency_ms"] and result["latency_ms"] < 30000:
            result["status"] = "degraded"
        else:
            result["status"] = "critical"
            
    except Exception as e:
        result["status"] = "critical"
        result["error"] = str(e)
        logger.error(f"[HEALTH] LLM check failed: {e}")
    
    result["check_time_ms"] = int((time.time() - start) * 1000)
    return result


def check_jobs_health() -> Dict[str, Any]:
    """Check background job processing health."""
    result = {
        "status": "unknown",
        "details": {}
    }
    
    start = time.time()
    
    try:
        from utils.database.supabase_client import get_supabase
        supabase = get_supabase()
        
        if not supabase:
            result["status"] = "degraded"
            result["error"] = "Supabase not available for job tracking"
            return result
        
        # Get job stats
        now = datetime.utcnow()
        hour_ago = (now - timedelta(hours=1)).isoformat()
        day_ago = (now - timedelta(days=1)).isoformat()
        
        # Current state
        try:
            pending = supabase.table('processing_jobs').select('id').eq('status', 'pending').execute()
            result["details"]["pending"] = len(pending.data) if pending.data else 0
        except:
            result["details"]["pending"] = "unknown"
        
        try:
            processing = supabase.table('processing_jobs').select('id', 'created_at').eq('status', 'processing').execute()
            result["details"]["processing"] = len(processing.data) if processing.data else 0
            
            # Check for stuck (processing > 15 min)
            stuck = 0
            if processing.data:
                cutoff = now - timedelta(minutes=15)
                for job in processing.data:
                    created = job.get('created_at', '')
                    if created:
                        try:
                            job_time = datetime.fromisoformat(created.replace('Z', '+00:00').replace('+00:00', ''))
                            if job_time < cutoff:
                                stuck += 1
                        except:
                            pass
            result["details"]["stuck"] = stuck
        except:
            result["details"]["processing"] = "unknown"
            result["details"]["stuck"] = "unknown"
        
        # Last hour stats
        try:
            completed_hour = supabase.table('processing_jobs').select('id').eq('status', 'completed').gte('updated_at', hour_ago).execute()
            result["details"]["completed_last_hour"] = len(completed_hour.data) if completed_hour.data else 0
        except:
            result["details"]["completed_last_hour"] = "unknown"
        
        try:
            failed_hour = supabase.table('processing_jobs').select('id').eq('status', 'failed').gte('updated_at', hour_ago).execute()
            result["details"]["failed_last_hour"] = len(failed_hour.data) if failed_hour.data else 0
        except:
            result["details"]["failed_last_hour"] = "unknown"
        
        # Last 24h stats
        try:
            completed_day = supabase.table('processing_jobs').select('id').eq('status', 'completed').gte('updated_at', day_ago).execute()
            result["details"]["completed_last_24h"] = len(completed_day.data) if completed_day.data else 0
        except:
            result["details"]["completed_last_24h"] = "unknown"
        
        try:
            failed_day = supabase.table('processing_jobs').select('id').eq('status', 'failed').gte('updated_at', day_ago).execute()
            result["details"]["failed_last_24h"] = len(failed_day.data) if failed_day.data else 0
        except:
            result["details"]["failed_last_24h"] = "unknown"
        
        # Determine status
        stuck = result["details"].get("stuck", 0)
        if stuck == "unknown":
            result["status"] = "degraded"
        elif stuck > 0:
            result["status"] = "critical"
        elif result["details"].get("failed_last_hour", 0) > 5:
            result["status"] = "degraded"
        else:
            result["status"] = "healthy"
            
    except Exception as e:
        result["status"] = "critical"
        result["error"] = str(e)
        logger.error(f"[HEALTH] Jobs check failed: {e}")
    
    result["check_time_ms"] = int((time.time() - start) * 1000)
    return result


def check_data_integrity() -> Dict[str, Any]:
    """Cross-system data integrity check."""
    result = {
        "status": "unknown",
        "details": {
            "orphaned_duckdb_tables": [],
            "orphaned_chromadb_docs": [],
            "orphaned_registry_entries": [],
            "mismatched_counts": []
        },
        "issues": []
    }
    
    start = time.time()
    
    try:
        # Get DuckDB tables
        duckdb_tables = set()
        duckdb_table_rows = {}
        try:
            from utils.structured_data_handler import get_structured_handler
            handler = get_structured_handler()
            
            tables = handler.conn.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'main' AND table_type = 'BASE TABLE'
                AND table_name NOT LIKE '\\_%' ESCAPE '\\'
            """).fetchall()
            
            for (table,) in tables:
                duckdb_tables.add(table)
                try:
                    count = handler.conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
                    duckdb_table_rows[table] = count
                except:
                    pass
        except Exception as duck_e:
            result["issues"].append(f"DuckDB scan failed: {duck_e}")
        
        # Get ChromaDB documents
        chromadb_sources = set()
        chromadb_chunk_counts = {}
        try:
            from utils.rag_handler import RAGHandler
            rag = RAGHandler()
            collection = rag.client.get_or_create_collection(name="documents")
            
            all_docs = collection.get(include=["metadatas"], limit=10000)
            for meta in all_docs.get("metadatas", []):
                if meta:
                    source = meta.get("source") or meta.get("filename")
                    if source:
                        chromadb_sources.add(source)
                        chromadb_chunk_counts[source] = chromadb_chunk_counts.get(source, 0) + 1
        except Exception as chroma_e:
            result["issues"].append(f"ChromaDB scan failed: {chroma_e}")
        
        # Get registry entries
        registry_entries = {}
        try:
            from utils.database.supabase_client import get_supabase
            supabase = get_supabase()
            
            if supabase:
                registry = supabase.table('document_registry').select('*').execute()
                for entry in registry.data or []:
                    filename = entry.get('filename')
                    if filename:
                        registry_entries[filename] = {
                            'storage_type': entry.get('storage_type'),
                            'row_count': entry.get('row_count'),
                            'chunk_count': entry.get('chunk_count'),
                            'duckdb_tables': entry.get('duckdb_tables', [])
                        }
        except Exception as reg_e:
            result["issues"].append(f"Registry scan failed: {reg_e}")
        
        # Cross-reference checks
        
        # 1. DuckDB tables not in registry
        for table in duckdb_tables:
            found = False
            for filename, entry in registry_entries.items():
                if table in (entry.get('duckdb_tables') or []):
                    found = True
                    break
                # Also check if table name matches filename pattern
                if table.lower().replace('_', ' ').replace('.', ' ') in filename.lower().replace('_', ' ').replace('.', ' '):
                    found = True
                    break
            if not found:
                result["details"]["orphaned_duckdb_tables"].append(table)
        
        # 2. ChromaDB sources not in registry
        for source in chromadb_sources:
            if source not in registry_entries:
                # Fuzzy match
                found = False
                for reg_file in registry_entries.keys():
                    if source.lower() == reg_file.lower():
                        found = True
                        break
                if not found:
                    result["details"]["orphaned_chromadb_docs"].append(source)
        
        # 3. Registry entries with missing storage
        for filename, entry in registry_entries.items():
            storage = entry.get('storage_type', '')
            
            if storage in ['duckdb', 'both']:
                # Should have DuckDB table
                has_table = any(
                    t.lower().replace('_', '') in filename.lower().replace('_', '').replace('.', '').replace(' ', '')
                    for t in duckdb_tables
                )
                if not has_table and entry.get('duckdb_tables'):
                    # Check explicit table list
                    has_table = any(t in duckdb_tables for t in entry.get('duckdb_tables', []))
                
                if not has_table:
                    result["details"]["orphaned_registry_entries"].append({
                        "filename": filename,
                        "issue": "missing_duckdb_table",
                        "expected_storage": storage
                    })
            
            if storage in ['chromadb', 'both']:
                # Should have ChromaDB chunks
                if filename not in chromadb_sources:
                    # Fuzzy match
                    found = any(filename.lower() == s.lower() for s in chromadb_sources)
                    if not found:
                        result["details"]["orphaned_registry_entries"].append({
                            "filename": filename,
                            "issue": "missing_chromadb_chunks",
                            "expected_storage": storage
                        })
        
        # Summary counts
        result["details"]["duckdb_table_count"] = len(duckdb_tables)
        result["details"]["chromadb_source_count"] = len(chromadb_sources)
        result["details"]["registry_entry_count"] = len(registry_entries)
        
        # Determine status
        total_orphans = (
            len(result["details"]["orphaned_duckdb_tables"]) +
            len(result["details"]["orphaned_chromadb_docs"]) +
            len(result["details"]["orphaned_registry_entries"])
        )
        
        if total_orphans == 0 and not result["issues"]:
            result["status"] = "healthy"
        elif total_orphans <= 5:
            result["status"] = "degraded"
        else:
            result["status"] = "critical"
        
        result["details"]["total_orphans"] = total_orphans
        
    except Exception as e:
        result["status"] = "critical"
        result["error"] = str(e)
        logger.error(f"[HEALTH] Integrity check failed: {e}")
    
    result["check_time_ms"] = int((time.time() - start) * 1000)
    return result


# =============================================================================
# MAIN ENDPOINT
# =============================================================================

@router.get("/health")
async def get_system_health(verbose: bool = Query(False, description="Include detailed breakdown")):
    """
    Comprehensive system health check.
    
    Returns overall status and per-subsystem health.
    Use ?verbose=true for detailed metrics.
    """
    start = time.time()
    
    # Run all checks
    duckdb = check_duckdb_health()
    chromadb = check_chromadb_health()
    supabase = check_supabase_health()
    llm = check_llm_health()
    jobs = check_jobs_health()
    integrity = check_data_integrity()
    
    # Calculate overall status
    statuses = [
        duckdb["status"],
        chromadb["status"],
        supabase["status"],
        llm["status"],
        jobs["status"],
        integrity["status"]
    ]
    
    if "critical" in statuses:
        overall = "critical"
    elif "degraded" in statuses:
        overall = "degraded"
    elif "unknown" in statuses:
        overall = "degraded"
    else:
        overall = "healthy"
    
    # Build response
    response = {
        "status": overall,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "subsystems": {
            "duckdb": {"status": duckdb["status"], "latency_ms": duckdb.get("latency_ms")},
            "chromadb": {"status": chromadb["status"], "latency_ms": chromadb.get("latency_ms")},
            "supabase": {"status": supabase["status"], "latency_ms": supabase.get("latency_ms")},
            "llm": {"status": llm["status"], "latency_ms": llm.get("latency_ms")},
            "jobs": {"status": jobs["status"]},
            "integrity": {"status": integrity["status"]}
        },
        "summary": {
            "duckdb_tables": duckdb.get("details", {}).get("data_tables", 0),
            "duckdb_rows": duckdb.get("details", {}).get("total_rows", 0),
            "chromadb_chunks": chromadb.get("details", {}).get("total_chunks", 0),
            "chromadb_docs": chromadb.get("details", {}).get("unique_documents", 0),
            "stuck_jobs": jobs.get("details", {}).get("stuck", 0),
            "orphaned_data": integrity.get("details", {}).get("total_orphans", 0)
        },
        "check_time_ms": int((time.time() - start) * 1000)
    }
    
    # Add alerts
    alerts = []
    if duckdb["status"] == "critical":
        alerts.append({"severity": "critical", "subsystem": "duckdb", "message": duckdb.get("error", "DuckDB unavailable")})
    if chromadb["status"] == "critical":
        alerts.append({"severity": "critical", "subsystem": "chromadb", "message": chromadb.get("error", "ChromaDB unavailable")})
    if supabase["status"] == "critical":
        alerts.append({"severity": "critical", "subsystem": "supabase", "message": supabase.get("error", "Supabase unavailable")})
    if llm["status"] == "critical":
        alerts.append({"severity": "critical", "subsystem": "llm", "message": llm.get("error", "LLM unavailable")})
    if jobs.get("details", {}).get("stuck", 0) > 0:
        alerts.append({"severity": "critical", "subsystem": "jobs", "message": f"{jobs['details']['stuck']} jobs stuck > 15 min"})
    if integrity.get("details", {}).get("total_orphans", 0) > 0:
        alerts.append({"severity": "warning", "subsystem": "integrity", "message": f"{integrity['details']['total_orphans']} orphaned data items"})
    
    response["alerts"] = alerts
    
    # Add verbose details if requested
    if verbose:
        response["details"] = {
            "duckdb": duckdb,
            "chromadb": chromadb,
            "supabase": supabase,
            "llm": llm,
            "jobs": jobs,
            "integrity": integrity
        }
    
    return response


@router.get("/health/duckdb")
async def get_duckdb_health():
    """DuckDB-specific health check."""
    return check_duckdb_health()


@router.get("/health/chromadb")
async def get_chromadb_health():
    """ChromaDB-specific health check."""
    return check_chromadb_health()


@router.get("/health/supabase")
async def get_supabase_health():
    """Supabase-specific health check."""
    return check_supabase_health()


@router.get("/health/llm")
async def get_llm_health():
    """LLM-specific health check."""
    return check_llm_health()


@router.get("/health/jobs")
async def get_jobs_health():
    """Background jobs health check."""
    return check_jobs_health()


@router.get("/health/integrity")
async def get_integrity_health():
    """Data integrity check."""
    return check_data_integrity()


# =============================================================================
# PROJECT & FILE LEVEL METRICS
# =============================================================================

@router.get("/health/projects")
async def get_projects_health():
    """
    Per-project health metrics.
    
    Returns storage breakdown and health status for each project.
    """
    result = {
        "projects": [],
        "total_projects": 0,
        "check_time_ms": 0
    }
    
    start = time.time()
    
    try:
        # Collect project data from all sources
        project_data = {}  # project_name -> metrics
        
        # 1. DuckDB - tables and rows per project
        try:
            from utils.structured_data_handler import get_structured_handler
            handler = get_structured_handler()
            
            # Get from schema_metadata
            meta = handler.conn.execute("""
                SELECT project, COUNT(*) as table_count, SUM(row_count) as total_rows
                FROM _schema_metadata 
                WHERE is_current = TRUE
                GROUP BY project
            """).fetchall()
            
            for project, table_count, total_rows in meta:
                if project:
                    if project not in project_data:
                        project_data[project] = {
                            "project": project,
                            "duckdb_tables": 0,
                            "duckdb_rows": 0,
                            "chromadb_chunks": 0,
                            "chromadb_docs": 0,
                            "registry_entries": 0,
                            "files": []
                        }
                    project_data[project]["duckdb_tables"] = table_count
                    project_data[project]["duckdb_rows"] = total_rows or 0
        except Exception as e:
            logger.warning(f"[HEALTH] DuckDB project scan failed: {e}")
        
        # 2. ChromaDB - chunks per project
        try:
            from utils.rag_handler import RAGHandler
            rag = RAGHandler()
            collection = rag.client.get_or_create_collection(name="documents")
            
            all_docs = collection.get(include=["metadatas"], limit=10000)
            project_chunks = {}
            project_sources = {}
            
            for meta in all_docs.get("metadatas", []):
                if meta:
                    project = meta.get("project", "unknown")
                    source = meta.get("source") or meta.get("filename")
                    
                    if project not in project_chunks:
                        project_chunks[project] = 0
                        project_sources[project] = set()
                    
                    project_chunks[project] += 1
                    if source:
                        project_sources[project].add(source)
            
            for project, chunks in project_chunks.items():
                if project not in project_data:
                    project_data[project] = {
                        "project": project,
                        "duckdb_tables": 0,
                        "duckdb_rows": 0,
                        "chromadb_chunks": 0,
                        "chromadb_docs": 0,
                        "registry_entries": 0,
                        "files": []
                    }
                project_data[project]["chromadb_chunks"] = chunks
                project_data[project]["chromadb_docs"] = len(project_sources.get(project, set()))
        except Exception as e:
            logger.warning(f"[HEALTH] ChromaDB project scan failed: {e}")
        
        # 3. Supabase registry - entries per project
        try:
            from utils.database.supabase_client import get_supabase
            supabase = get_supabase()
            
            if supabase:
                # Get projects table for project_id mapping
                projects_resp = supabase.table('projects').select('id, name').execute()
                project_id_map = {p['id']: p['name'] for p in (projects_resp.data or [])}
                
                # Get registry counts
                registry = supabase.table('document_registry').select('project_id').execute()
                project_registry_counts = {}
                
                for entry in registry.data or []:
                    pid = entry.get('project_id')
                    if pid:
                        project_name = project_id_map.get(pid, pid)
                        project_registry_counts[project_name] = project_registry_counts.get(project_name, 0) + 1
                
                for project, count in project_registry_counts.items():
                    if project not in project_data:
                        project_data[project] = {
                            "project": project,
                            "duckdb_tables": 0,
                            "duckdb_rows": 0,
                            "chromadb_chunks": 0,
                            "chromadb_docs": 0,
                            "registry_entries": 0,
                            "files": []
                        }
                    project_data[project]["registry_entries"] = count
        except Exception as e:
            logger.warning(f"[HEALTH] Supabase project scan failed: {e}")
        
        # Calculate health status per project
        for project, data in project_data.items():
            # Simple health calc: has data in expected places
            has_duckdb = data["duckdb_rows"] > 0
            has_chromadb = data["chromadb_chunks"] > 0
            has_registry = data["registry_entries"] > 0
            
            if has_registry and (has_duckdb or has_chromadb):
                data["status"] = "healthy"
            elif has_duckdb or has_chromadb:
                data["status"] = "degraded"  # Data but no registry
            else:
                data["status"] = "empty"
            
            data["total_data_points"] = data["duckdb_rows"] + data["chromadb_chunks"]
        
        result["projects"] = sorted(project_data.values(), key=lambda x: -x["total_data_points"])
        result["total_projects"] = len(project_data)
        
    except Exception as e:
        logger.error(f"[HEALTH] Projects check failed: {e}")
        result["error"] = str(e)
    
    result["check_time_ms"] = int((time.time() - start) * 1000)
    return result


@router.get("/health/files")
async def get_files_health(project: str = Query(None, description="Filter by project name")):
    """
    Per-file health metrics.
    
    Shows storage status for each file across DuckDB, ChromaDB, and Registry.
    Use ?project=XXX to filter by project.
    """
    result = {
        "files": [],
        "total_files": 0,
        "summary": {
            "healthy": 0,
            "degraded": 0,
            "orphaned": 0
        },
        "check_time_ms": 0
    }
    
    start = time.time()
    
    try:
        file_data = {}  # filename -> metrics
        
        # 1. DuckDB files
        try:
            from utils.structured_data_handler import get_structured_handler
            handler = get_structured_handler()
            
            query = """
                SELECT project, file_name, table_name, row_count
                FROM _schema_metadata 
                WHERE is_current = TRUE
            """
            if project:
                query += f" AND LOWER(project) = LOWER('{project}')"
            
            meta = handler.conn.execute(query).fetchall()
            
            for proj, file_name, table_name, row_count in meta:
                key = f"{proj}::{file_name}"
                if key not in file_data:
                    file_data[key] = {
                        "project": proj,
                        "filename": file_name,
                        "duckdb_table": None,
                        "duckdb_rows": 0,
                        "chromadb_chunks": 0,
                        "registry_status": None,
                        "registry_storage_type": None
                    }
                file_data[key]["duckdb_table"] = table_name
                file_data[key]["duckdb_rows"] = row_count or 0
        except Exception as e:
            logger.warning(f"[HEALTH] DuckDB file scan failed: {e}")
        
        # 2. ChromaDB files
        try:
            from utils.rag_handler import RAGHandler
            rag = RAGHandler()
            collection = rag.client.get_or_create_collection(name="documents")
            
            all_docs = collection.get(include=["metadatas"], limit=10000)
            
            for meta in all_docs.get("metadatas", []):
                if meta:
                    proj = meta.get("project", "unknown")
                    source = meta.get("source") or meta.get("filename")
                    
                    if project and proj.lower() != project.lower():
                        continue
                    
                    if source:
                        key = f"{proj}::{source}"
                        if key not in file_data:
                            file_data[key] = {
                                "project": proj,
                                "filename": source,
                                "duckdb_table": None,
                                "duckdb_rows": 0,
                                "chromadb_chunks": 0,
                                "registry_status": None,
                                "registry_storage_type": None
                            }
                        file_data[key]["chromadb_chunks"] += 1
        except Exception as e:
            logger.warning(f"[HEALTH] ChromaDB file scan failed: {e}")
        
        # 3. Registry entries
        try:
            from utils.database.supabase_client import get_supabase
            supabase = get_supabase()
            
            if supabase:
                # Get projects for name lookup
                projects_resp = supabase.table('projects').select('id, name').execute()
                project_id_map = {p['id']: p['name'] for p in (projects_resp.data or [])}
                project_name_to_id = {p['name'].lower(): p['id'] for p in (projects_resp.data or [])}
                
                query = supabase.table('document_registry').select('*')
                
                if project:
                    # Find project_id for filter
                    pid = project_name_to_id.get(project.lower())
                    if pid:
                        query = query.eq('project_id', pid)
                
                registry = query.execute()
                
                for entry in registry.data or []:
                    filename = entry.get('filename')
                    pid = entry.get('project_id')
                    proj_name = project_id_map.get(pid, "unknown")
                    
                    if filename:
                        key = f"{proj_name}::{filename}"
                        if key not in file_data:
                            file_data[key] = {
                                "project": proj_name,
                                "filename": filename,
                                "duckdb_table": None,
                                "duckdb_rows": 0,
                                "chromadb_chunks": 0,
                                "registry_status": None,
                                "registry_storage_type": None
                            }
                        file_data[key]["registry_status"] = entry.get('parse_status', 'unknown')
                        file_data[key]["registry_storage_type"] = entry.get('storage_type')
                        file_data[key]["registry_row_count"] = entry.get('row_count')
                        file_data[key]["registry_chunk_count"] = entry.get('chunk_count')
                        file_data[key]["truth_type"] = entry.get('truth_type')
                        file_data[key]["uploaded_at"] = entry.get('created_at')
                        # New enhanced metadata fields
                        file_data[key]["file_hash"] = entry.get('file_hash')
                        file_data[key]["file_size_bytes"] = entry.get('file_size_bytes')
                        file_data[key]["uploaded_by_email"] = entry.get('uploaded_by_email')
                        file_data[key]["uploaded_by_id"] = entry.get('uploaded_by_id')
                        file_data[key]["last_accessed_at"] = entry.get('last_accessed_at')
                        file_data[key]["access_count"] = entry.get('access_count', 0)
                        file_data[key]["data_quality_score"] = entry.get('data_quality_score')
                        file_data[key]["quality_issues"] = entry.get('quality_issues')
        except Exception as e:
            logger.warning(f"[HEALTH] Registry file scan failed: {e}")
        
        # Calculate health status per file
        for key, data in file_data.items():
            storage_type = data.get("registry_storage_type")
            has_registry = data["registry_status"] is not None
            has_duckdb = data["duckdb_rows"] > 0
            has_chromadb = data["chromadb_chunks"] > 0
            
            # Determine expected vs actual
            if storage_type == "duckdb":
                expected_duckdb = True
                expected_chromadb = False
            elif storage_type == "chromadb":
                expected_duckdb = False
                expected_chromadb = True
            elif storage_type == "both":
                expected_duckdb = True
                expected_chromadb = True
            else:
                expected_duckdb = None
                expected_chromadb = None
            
            # Health status
            issues = []
            
            if not has_registry:
                issues.append("not_in_registry")
            
            if expected_duckdb and not has_duckdb:
                issues.append("missing_duckdb_data")
            
            if expected_chromadb and not has_chromadb:
                issues.append("missing_chromadb_data")
            
            if has_duckdb and not has_registry:
                issues.append("orphaned_duckdb")
            
            if has_chromadb and not has_registry:
                issues.append("orphaned_chromadb")
            
            # Row count mismatch
            if has_registry and has_duckdb:
                registry_rows = data.get("registry_row_count", 0) or 0
                if registry_rows > 0 and abs(registry_rows - data["duckdb_rows"]) > 0:
                    issues.append(f"row_count_mismatch:registry={registry_rows},actual={data['duckdb_rows']}")
            
            if not issues:
                data["status"] = "healthy"
                result["summary"]["healthy"] += 1
            elif "orphaned" in str(issues):
                data["status"] = "orphaned"
                result["summary"]["orphaned"] += 1
            else:
                data["status"] = "degraded"
                result["summary"]["degraded"] += 1
            
            data["issues"] = issues
        
        result["files"] = sorted(file_data.values(), key=lambda x: (x["status"] != "healthy", -x.get("duckdb_rows", 0)))
        result["total_files"] = len(file_data)
        
    except Exception as e:
        logger.error(f"[HEALTH] Files check failed: {e}")
        result["error"] = str(e)
    
    result["check_time_ms"] = int((time.time() - start) * 1000)
    return result


@router.get("/health/project/{project_name}")
async def get_project_detail(project_name: str):
    """
    Detailed health for a specific project.
    
    Combines project summary + file-level details.
    """
    result = {
        "project": project_name,
        "summary": {},
        "files": [],
        "issues": [],
        "check_time_ms": 0
    }
    
    start = time.time()
    
    try:
        # Get project summary
        projects_health = await get_projects_health()
        for proj in projects_health.get("projects", []):
            if proj.get("project", "").lower() == project_name.lower():
                result["summary"] = proj
                break
        
        if not result["summary"]:
            result["summary"] = {
                "project": project_name,
                "status": "not_found",
                "duckdb_tables": 0,
                "duckdb_rows": 0,
                "chromadb_chunks": 0,
                "chromadb_docs": 0
            }
        
        # Get file details
        files_health = await get_files_health(project=project_name)
        result["files"] = files_health.get("files", [])
        result["file_summary"] = files_health.get("summary", {})
        
        # Collect issues
        for f in result["files"]:
            if f.get("issues"):
                result["issues"].append({
                    "filename": f.get("filename"),
                    "issues": f.get("issues")
                })
        
    except Exception as e:
        logger.error(f"[HEALTH] Project detail failed: {e}")
        result["error"] = str(e)
    
    result["check_time_ms"] = int((time.time() - start) * 1000)
    return result


@router.get("/health/stale-files")
async def get_stale_files(days: int = Query(30, description="Files not accessed in this many days")):
    """
    Find files that haven't been accessed recently.
    
    Helps identify data that may be obsolete or orphaned.
    """
    result = {
        "threshold_days": days,
        "stale_files": [],
        "never_accessed": [],
        "total_stale": 0,
        "check_time_ms": 0
    }
    
    start = time.time()
    
    try:
        from utils.database.supabase_client import get_supabase
        from datetime import timedelta
        
        supabase = get_supabase()
        if not supabase:
            result["error"] = "Supabase not available"
            return result
        
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        # Get all files from registry
        registry = supabase.table('document_registry').select(
            'filename, project_id, last_accessed_at, access_count, created_at, file_size_bytes, storage_type'
        ).execute()
        
        # Get project names
        projects_resp = supabase.table('projects').select('id, name').execute()
        project_id_map = {p['id']: p['name'] for p in (projects_resp.data or [])}
        
        for entry in registry.data or []:
            last_accessed = entry.get('last_accessed_at')
            
            file_info = {
                "filename": entry.get('filename'),
                "project": project_id_map.get(entry.get('project_id'), 'unknown'),
                "created_at": entry.get('created_at'),
                "last_accessed_at": last_accessed,
                "access_count": entry.get('access_count', 0),
                "file_size_bytes": entry.get('file_size_bytes'),
                "storage_type": entry.get('storage_type')
            }
            
            if last_accessed is None:
                result["never_accessed"].append(file_info)
            elif last_accessed < cutoff:
                result["stale_files"].append(file_info)
        
        result["total_stale"] = len(result["stale_files"]) + len(result["never_accessed"])
        
        # Sort by oldest first
        result["stale_files"] = sorted(result["stale_files"], key=lambda x: x.get("last_accessed_at") or "")
        result["never_accessed"] = sorted(result["never_accessed"], key=lambda x: x.get("created_at") or "")
        
    except Exception as e:
        logger.error(f"[HEALTH] Stale files check failed: {e}")
        result["error"] = str(e)
    
    result["check_time_ms"] = int((time.time() - start) * 1000)
    return result


@router.get("/health/uploaders")
async def get_uploader_stats():
    """
    Get upload statistics by user.
    
    Shows who uploaded what and when.
    """
    result = {
        "uploaders": [],
        "total_uploaders": 0,
        "anonymous_uploads": 0,
        "check_time_ms": 0
    }
    
    start = time.time()
    
    try:
        from utils.database.supabase_client import get_supabase
        
        supabase = get_supabase()
        if not supabase:
            result["error"] = "Supabase not available"
            return result
        
        # Get all files grouped by uploader
        registry = supabase.table('document_registry').select(
            'uploaded_by_id, uploaded_by_email, filename, file_size_bytes, created_at, parse_status'
        ).execute()
        
        uploader_stats = {}
        
        for entry in registry.data or []:
            uploader_id = entry.get('uploaded_by_id')
            uploader_email = entry.get('uploaded_by_email') or 'anonymous'
            
            if not uploader_id:
                result["anonymous_uploads"] += 1
                continue
            
            if uploader_email not in uploader_stats:
                uploader_stats[uploader_email] = {
                    "email": uploader_email,
                    "user_id": uploader_id,
                    "file_count": 0,
                    "total_size_bytes": 0,
                    "successful_uploads": 0,
                    "failed_uploads": 0,
                    "first_upload": None,
                    "last_upload": None
                }
            
            stats = uploader_stats[uploader_email]
            stats["file_count"] += 1
            stats["total_size_bytes"] += entry.get('file_size_bytes') or 0
            
            if entry.get('parse_status') == 'success':
                stats["successful_uploads"] += 1
            else:
                stats["failed_uploads"] += 1
            
            created = entry.get('created_at')
            if created:
                if stats["first_upload"] is None or created < stats["first_upload"]:
                    stats["first_upload"] = created
                if stats["last_upload"] is None or created > stats["last_upload"]:
                    stats["last_upload"] = created
        
        result["uploaders"] = sorted(uploader_stats.values(), key=lambda x: -x["file_count"])
        result["total_uploaders"] = len(uploader_stats)
        
    except Exception as e:
        logger.error(f"[HEALTH] Uploader stats failed: {e}")
        result["error"] = str(e)
    
    result["check_time_ms"] = int((time.time() - start) * 1000)
    return result


@router.get("/health/duplicates")
async def find_duplicate_files():
    """
    Find duplicate files based on file hash.
    
    Identifies files that have been uploaded multiple times.
    """
    result = {
        "duplicate_groups": [],
        "total_duplicates": 0,
        "wasted_bytes": 0,
        "check_time_ms": 0
    }
    
    start = time.time()
    
    try:
        from utils.database.supabase_client import get_supabase
        
        supabase = get_supabase()
        if not supabase:
            result["error"] = "Supabase not available"
            return result
        
        # Get all files with hashes
        registry = supabase.table('document_registry').select(
            'filename, file_hash, file_size_bytes, project_id, created_at, uploaded_by_email'
        ).not_.is_('file_hash', 'null').execute()
        
        # Get project names
        projects_resp = supabase.table('projects').select('id, name').execute()
        project_id_map = {p['id']: p['name'] for p in (projects_resp.data or [])}
        
        # Group by hash
        hash_groups = {}
        for entry in registry.data or []:
            file_hash = entry.get('file_hash')
            if file_hash:
                if file_hash not in hash_groups:
                    hash_groups[file_hash] = []
                hash_groups[file_hash].append({
                    "filename": entry.get('filename'),
                    "project": project_id_map.get(entry.get('project_id'), 'unknown'),
                    "file_size_bytes": entry.get('file_size_bytes'),
                    "created_at": entry.get('created_at'),
                    "uploaded_by": entry.get('uploaded_by_email')
                })
        
        # Find duplicates (more than one file with same hash)
        for file_hash, files in hash_groups.items():
            if len(files) > 1:
                # Sort by created_at to identify original vs duplicates
                files_sorted = sorted(files, key=lambda x: x.get("created_at") or "")
                
                result["duplicate_groups"].append({
                    "file_hash": file_hash[:16] + "...",  # Truncate for display
                    "count": len(files),
                    "original": files_sorted[0],
                    "duplicates": files_sorted[1:]
                })
                
                result["total_duplicates"] += len(files) - 1
                
                # Calculate wasted space (size of duplicates)
                for dup in files_sorted[1:]:
                    result["wasted_bytes"] += dup.get("file_size_bytes") or 0
        
        # Sort by most duplicates first
        result["duplicate_groups"] = sorted(result["duplicate_groups"], key=lambda x: -x["count"])
        
    except Exception as e:
        logger.error(f"[HEALTH] Duplicate check failed: {e}")
        result["error"] = str(e)
    
    result["check_time_ms"] = int((time.time() - start) * 1000)
    return result


# =============================================================================
# LINEAGE ENDPOINTS
# =============================================================================
# NOTE: Route order matters! Specific routes must come before generic {node_type}/{node_id}

@router.get("/health/lineage")
async def get_lineage_summary():
    """
    Get overall lineage statistics.
    
    Shows edge counts by type across all projects.
    """
    result = {
        "total_edges": 0,
        "by_relationship": {},
        "by_project": {},
        "check_time_ms": 0
    }
    
    start = time.time()
    
    try:
        from utils.database.supabase_client import get_supabase
        
        supabase = get_supabase()
        if not supabase:
            result["error"] = "Supabase not available"
            return result
        
        # Get all edges
        response = supabase.table('lineage_edges').select('source_type, target_type, relationship, project_id').execute()
        
        edges = response.data or []
        result["total_edges"] = len(edges)
        
        # Get project names
        projects_resp = supabase.table('projects').select('id, name').execute()
        project_id_map = {p['id']: p['name'] for p in (projects_resp.data or [])}
        
        for edge in edges:
            rel = edge.get('relationship', 'unknown')
            result["by_relationship"][rel] = result["by_relationship"].get(rel, 0) + 1
            
            pid = edge.get('project_id')
            if pid:
                proj_name = project_id_map.get(pid, pid)
                if proj_name not in result["by_project"]:
                    result["by_project"][proj_name] = {"total": 0, "by_relationship": {}}
                result["by_project"][proj_name]["total"] += 1
                result["by_project"][proj_name]["by_relationship"][rel] = \
                    result["by_project"][proj_name]["by_relationship"].get(rel, 0) + 1
        
    except Exception as e:
        logger.error(f"[HEALTH] Lineage summary failed: {e}")
        result["error"] = str(e)
    
    result["check_time_ms"] = int((time.time() - start) * 1000)
    return result


@router.get("/health/lineage/project/{project_name}")
async def get_project_lineage(project_name: str):
    """
    Get lineage statistics for a specific project.
    
    Shows edge breakdown and helps identify lineage gaps.
    """
    result = {
        "project": project_name,
        "summary": {},
        "files_with_lineage": [],
        "files_without_lineage": [],
        "check_time_ms": 0
    }
    
    start = time.time()
    
    try:
        from utils.database.models import LineageModel
        from utils.database.supabase_client import get_supabase
        
        supabase = get_supabase()
        if not supabase:
            result["error"] = "Supabase not available"
            return result
        
        # Get project ID
        proj_resp = supabase.table('projects').select('id').eq('name', project_name).execute()
        if not proj_resp.data:
            result["error"] = f"Project '{project_name}' not found"
            return result
        
        project_id = proj_resp.data[0]['id']
        
        # Get lineage summary
        result["summary"] = LineageModel.get_project_summary(project_id)
        
        # Get all files in project from registry
        registry = supabase.table('document_registry').select('filename').eq('project_id', project_id).execute()
        all_files = set(f['filename'] for f in (registry.data or []))
        
        # Get files that have lineage edges
        edges = supabase.table('lineage_edges').select('source_id').eq('project_id', project_id).eq('source_type', 'file').execute()
        files_with_edges = set(e['source_id'] for e in (edges.data or []))
        
        result["files_with_lineage"] = list(files_with_edges)
        result["files_without_lineage"] = list(all_files - files_with_edges)
        result["lineage_coverage"] = f"{len(files_with_edges)}/{len(all_files)}" if all_files else "0/0"
        
    except Exception as e:
        logger.error(f"[HEALTH] Project lineage failed: {e}")
        result["error"] = str(e)
    
    result["check_time_ms"] = int((time.time() - start) * 1000)
    return result


@router.get("/health/lineage/trace/{target_type}/{target_id:path}")
async def trace_to_source(target_type: str, target_id: str, project: str = Query(None)):
    """
    Trace a target back to its original source file(s).
    
    Answers the question: "Where did this come from?"
    
    Useful for:
    - Finding the source document for a finding
    - Tracing a table back to its upload
    - Audit trails
    """
    result = {
        "target": {"type": target_type, "id": target_id},
        "source_files": [],
        "trace_path": [],
        "check_time_ms": 0
    }
    
    start = time.time()
    
    try:
        from utils.database.models import LineageModel
        from utils.database.supabase_client import get_supabase
        
        # Get project_id if project name provided
        project_id = None
        if project:
            supabase = get_supabase()
            if supabase:
                proj_resp = supabase.table('projects').select('id').eq('name', project).execute()
                if proj_resp.data:
                    project_id = proj_resp.data[0]['id']
        
        # Get ancestors
        ancestors = LineageModel.get_ancestors(target_type, target_id, project_id)
        
        # Build trace path
        for ancestor in ancestors:
            result["trace_path"].append({
                "source": f"{ancestor.get('source_type')}:{ancestor.get('source_id')}",
                "target": f"{ancestor.get('target_type')}:{ancestor.get('target_id')}",
                "relationship": ancestor.get('relationship'),
                "depth": ancestor.get('depth', 1)
            })
        
        # Get root files
        result["source_files"] = LineageModel.get_root_files(target_type, target_id, project_id)
        
    except Exception as e:
        logger.error(f"[HEALTH] Trace to source failed: {e}")
        result["error"] = str(e)
    
    result["check_time_ms"] = int((time.time() - start) * 1000)
    return result


@router.get("/health/lineage/{node_type}/{node_id:path}")
async def get_node_lineage(node_type: str, node_id: str, project: str = Query(None)):
    """
    Get full lineage for a specific node.
    
    Returns ancestors (what it came from) and descendants (what was derived from it).
    
    Args:
        node_type: Type of node (file, table, chunk, analysis, finding, etc.)
        node_id: Identifier of the node
        project: Optional project name filter
    """
    result = {
        "node": {"type": node_type, "id": node_id},
        "ancestors": [],
        "descendants": [],
        "root_files": [],
        "check_time_ms": 0
    }
    
    start = time.time()
    
    try:
        from utils.database.models import LineageModel
        from utils.database.supabase_client import get_supabase
        
        # Get project_id if project name provided
        project_id = None
        if project:
            supabase = get_supabase()
            if supabase:
                proj_resp = supabase.table('projects').select('id').eq('name', project).execute()
                if proj_resp.data:
                    project_id = proj_resp.data[0]['id']
        
        # Get ancestors and descendants
        result["ancestors"] = LineageModel.get_ancestors(node_type, node_id, project_id)
        result["descendants"] = LineageModel.get_descendants(node_type, node_id, project_id)
        result["root_files"] = LineageModel.get_root_files(node_type, node_id, project_id)
        
    except Exception as e:
        logger.error(f"[HEALTH] Node lineage failed: {e}")
        result["error"] = str(e)
    
    result["check_time_ms"] = int((time.time() - start) * 1000)
    return result
