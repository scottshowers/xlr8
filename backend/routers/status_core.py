"""
Status Core Router - Basic Status Endpoints
============================================

Provides core status endpoints that were missing:
- GET /api/status - Basic platform status
- GET /api/status/dashboard - Dashboard summary stats
- GET /api/project-intelligence/genome - Customer genome data

Deploy to: backend/routers/status_core.py

Add to main.py:
    from routers import status_core
    app.include_router(status_core.router, prefix="/api", tags=["status"])
"""

from fastapi import APIRouter, Query
from typing import Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/status")
async def get_platform_status():
    """
    Basic platform status endpoint.
    Returns overall system health and key metrics.
    """
    try:
        # Get health from existing components
        from utils.structured_data_handler import get_structured_handler
        from utils.rag_handler import RAGHandler
        from utils.database.client import get_supabase
        
        status = {
            "status": "operational",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "2.0.0",
            "components": {}
        }
        
        # Check DuckDB
        try:
            handler = get_structured_handler()
            tables = handler.conn.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'main'").fetchone()[0]
            status["components"]["duckdb"] = {"status": "ok", "tables": tables}
        except Exception as e:
            status["components"]["duckdb"] = {"status": "error", "error": str(e)}
        
        # Check ChromaDB
        try:
            rag = RAGHandler()
            collection = rag.client.get_or_create_collection(name="documents")
            count = collection.count()
            status["components"]["chromadb"] = {"status": "ok", "chunks": count}
        except Exception as e:
            status["components"]["chromadb"] = {"status": "error", "error": str(e)}
        
        # Check Supabase
        try:
            supabase = get_supabase()
            if supabase:
                result = supabase.table("document_registry").select("id", count="exact").limit(1).execute()
                status["components"]["supabase"] = {"status": "ok", "registry_entries": result.count if hasattr(result, 'count') else 0}
            else:
                status["components"]["supabase"] = {"status": "unavailable"}
        except Exception as e:
            status["components"]["supabase"] = {"status": "error", "error": str(e)}
        
        # Set overall status
        errors = [c for c in status["components"].values() if c.get("status") == "error"]
        if errors:
            status["status"] = "degraded"
        
        return status
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


@router.get("/status/dashboard")
async def get_dashboard_status(project_id: Optional[str] = None):
    """
    Dashboard summary statistics.
    Used by Mission Control and Dashboard page.
    """
    try:
        from utils.structured_data_handler import get_structured_handler
        from utils.rag_handler import RAGHandler
        from utils.database.client import get_supabase
        
        stats = {
            "timestamp": datetime.utcnow().isoformat(),
            "ingested": 0,
            "tables": 0,
            "rows": 0,
            "insights": 0,
            "documents": 0,
            "chunks": 0,
            "health_score": 100,
        }
        
        # DuckDB stats
        try:
            handler = get_structured_handler()
            
            # Get table count from metadata
            try:
                meta = handler.conn.execute("""
                    SELECT COUNT(DISTINCT table_name), COALESCE(SUM(row_count), 0)
                    FROM _schema_metadata WHERE is_current = TRUE
                """).fetchone()
                stats["tables"] = meta[0] or 0
                stats["rows"] = int(meta[1] or 0)
            except:
                pass
                
        except Exception as e:
            logger.warning(f"DuckDB stats failed: {e}")
        
        # ChromaDB stats
        try:
            rag = RAGHandler()
            collection = rag.client.get_or_create_collection(name="documents")
            stats["chunks"] = collection.count()
        except Exception as e:
            logger.warning(f"ChromaDB stats failed: {e}")
        
        # Supabase stats
        try:
            supabase = get_supabase()
            if supabase:
                # Count document registry entries
                result = supabase.table("document_registry").select("id", count="exact").execute()
                stats["documents"] = result.count if hasattr(result, 'count') else len(result.data or [])
                stats["ingested"] = stats["documents"]
                
                # Count insights from intelligence findings if exists
                try:
                    findings = supabase.table("intelligence_findings").select("id", count="exact").execute()
                    stats["insights"] = findings.count if hasattr(findings, 'count') else len(findings.data or [])
                except:
                    stats["insights"] = 0
                    
        except Exception as e:
            logger.warning(f"Supabase stats failed: {e}")
        
        # Calculate health score based on data presence
        if stats["tables"] == 0 and stats["documents"] == 0:
            stats["health_score"] = 100  # Clean state is healthy
        else:
            stats["health_score"] = min(100, 70 + (stats["tables"] * 2) + (stats["insights"]))
        
        return stats
        
    except Exception as e:
        logger.error(f"Dashboard status failed: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "ingested": 0,
            "tables": 0,
            "rows": 0,
            "insights": 0,
        }


@router.get("/project-intelligence/genome")
async def get_project_genome(project_id: Optional[str] = Query(None)):
    """
    Customer genome data for a project.
    Returns intelligence fingerprint metrics.
    """
    try:
        from utils.structured_data_handler import get_structured_handler
        from utils.rag_handler import RAGHandler
        from utils.database.client import get_supabase
        
        genome = {
            "project_id": project_id,
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": {
                "data_complexity": 0,
                "relationship_density": 0,
                "query_sophistication": 0,
                "standards_coverage": 0,
            },
            "stats": {
                "files": 0,
                "tables": 0,
                "rows": 0,
                "documents": 0,
                "queries": 0,
                "patterns": 0,
            },
            "health_score": 0,
        }
        
        # Get DuckDB stats
        try:
            handler = get_structured_handler()
            
            if project_id:
                meta = handler.conn.execute("""
                    SELECT COUNT(DISTINCT table_name), COALESCE(SUM(row_count), 0), COUNT(DISTINCT file_name)
                    FROM _schema_metadata 
                    WHERE is_current = TRUE AND LOWER(project) LIKE ?
                """, [f"%{project_id.lower()}%"]).fetchone()
            else:
                meta = handler.conn.execute("""
                    SELECT COUNT(DISTINCT table_name), COALESCE(SUM(row_count), 0), COUNT(DISTINCT file_name)
                    FROM _schema_metadata WHERE is_current = TRUE
                """).fetchone()
            
            genome["stats"]["tables"] = meta[0] or 0
            genome["stats"]["rows"] = int(meta[1] or 0)
            genome["stats"]["files"] = meta[2] or 0
            
        except Exception as e:
            logger.warning(f"Genome DuckDB stats failed: {e}")
        
        # Get ChromaDB stats
        try:
            rag = RAGHandler()
            collection = rag.client.get_or_create_collection(name="documents")
            
            if project_id:
                # Filter by project
                results = collection.get(
                    where={"project_id": project_id},
                    include=[]
                )
                genome["stats"]["documents"] = len(results.get("ids", []))
            else:
                genome["stats"]["documents"] = collection.count()
                
        except Exception as e:
            logger.warning(f"Genome ChromaDB stats failed: {e}")
        
        # Calculate metrics based on actual data
        has_data = genome["stats"]["files"] > 0 or genome["stats"]["documents"] > 0
        
        if has_data:
            files = genome["stats"]["files"]
            rows = genome["stats"]["rows"]
            docs = genome["stats"]["documents"]
            
            genome["metrics"]["data_complexity"] = min(95, 20 + (files * 8) + (rows // 10000))
            genome["metrics"]["standards_coverage"] = min(95, 30 + (docs * 5))
            genome["health_score"] = (genome["metrics"]["data_complexity"] + genome["metrics"]["standards_coverage"]) // 2
        
        return genome
        
    except Exception as e:
        logger.error(f"Genome fetch failed: {e}")
        return {
            "project_id": project_id,
            "error": str(e),
            "metrics": {"data_complexity": 0, "relationship_density": 0, "query_sophistication": 0, "standards_coverage": 0},
            "stats": {"files": 0, "tables": 0, "rows": 0, "documents": 0, "queries": 0, "patterns": 0},
            "health_score": 0,
        }
