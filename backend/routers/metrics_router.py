"""
Metrics Router - Platform Analytics API
=======================================

Exposes metrics data for dashboards and reporting.

Deploy to: backend/routers/metrics.py

Endpoints:
    GET /metrics/summary      - Summary stats for last N days
    GET /metrics/trends       - Time-series data for charts
    GET /metrics/processors   - Per-processor breakdown
    GET /metrics/llm          - LLM usage and costs
"""

from fastapi import APIRouter, Query
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics", tags=["metrics"])

# Import MetricsService
try:
    from utils.metrics_service import MetricsService
    METRICS_AVAILABLE = True
except ImportError:
    try:
        from backend.utils.metrics_service import MetricsService
        METRICS_AVAILABLE = True
    except ImportError:
        METRICS_AVAILABLE = False
        logger.warning("[METRICS-API] MetricsService not available")


@router.get("/summary")
async def get_metrics_summary(days: int = Query(default=7, ge=1, le=90)):
    """
    Get summary metrics for dashboard.
    
    Returns upload counts, success rates, avg processing times, LLM usage.
    """
    if not METRICS_AVAILABLE:
        return {"error": "Metrics service not available", "available": False}
    
    try:
        summary = MetricsService.get_summary(days=days)
        return {"available": True, **summary}
    except Exception as e:
        logger.error(f"[METRICS-API] Summary error: {e}")
        return {"error": str(e), "available": False}


@router.get("/trends")
async def get_metrics_trends(
    days: int = Query(default=30, ge=1, le=365),
    bucket: str = Query(default="day", pattern="^(hour|day|week)$")
):
    """
    Get time-series metrics for trend analysis.
    
    Args:
        days: Number of days to look back (1-365)
        bucket: Time bucket - 'hour', 'day', or 'week'
    
    Returns time-bucketed upload counts, success rates, and avg processing times.
    """
    if not METRICS_AVAILABLE:
        return {"error": "Metrics service not available", "available": False}
    
    try:
        trends = MetricsService.get_trends(days=days, bucket=bucket)
        return {"available": True, **trends}
    except Exception as e:
        logger.error(f"[METRICS-API] Trends error: {e}")
        return {"error": str(e), "available": False}


@router.get("/processors")
async def get_processor_metrics(days: int = Query(default=7, ge=1, le=90)):
    """
    Get per-processor breakdown.
    
    Returns metrics grouped by processor type (register, standards, structured, semantic).
    """
    if not METRICS_AVAILABLE:
        return {"error": "Metrics service not available", "available": False}
    
    try:
        summary = MetricsService.get_summary(days=days)
        return {
            "available": True,
            "period_days": days,
            "processors": summary.get('upload_stats', {})
        }
    except Exception as e:
        logger.error(f"[METRICS-API] Processors error: {e}")
        return {"error": str(e), "available": False}


@router.get("/llm")
async def get_llm_metrics(days: int = Query(default=7, ge=1, le=90)):
    """
    Get LLM usage and costs.
    
    Returns metrics grouped by LLM provider (groq, claude, deepseek, ollama).
    """
    if not METRICS_AVAILABLE:
        return {"error": "Metrics service not available", "available": False}
    
    try:
        summary = MetricsService.get_summary(days=days)
        return {
            "available": True,
            "period_days": days,
            "providers": summary.get('llm_stats', {}),
            "total_calls": summary.get('total_llm_calls', 0)
        }
    except Exception as e:
        logger.error(f"[METRICS-API] LLM error: {e}")
        return {"error": str(e), "available": False}


@router.get("/health")
async def get_metrics_health():
    """
    Check if metrics system is operational.
    """
    if not METRICS_AVAILABLE:
        return {"healthy": False, "reason": "MetricsService not available"}
    
    try:
        # Try to get recent data
        summary = MetricsService.get_summary(days=1)
        if 'error' in summary:
            return {"healthy": False, "reason": summary['error']}
        return {"healthy": True, "recent_uploads": summary.get('total_uploads', 0)}
    except Exception as e:
        return {"healthy": False, "reason": str(e)}


# =============================================================================
# COST TRACKING ENDPOINTS
# =============================================================================

@router.get("/costs")
async def get_cost_summary(days: int = 30, project_id: Optional[str] = None):
    """Get cost summary for System Monitor dashboard."""
    try:
        from backend.utils.cost_tracker import get_cost_summary
        return get_cost_summary(days=days, project_id=project_id)
    except ImportError:
        try:
            from utils.cost_tracker import get_cost_summary
            return get_cost_summary(days=days, project_id=project_id)
        except ImportError:
            return {"error": "Cost tracker not available", "total_cost": 0}
    except Exception as e:
        logger.error(f"Cost summary failed: {e}")
        return {"error": str(e), "total_cost": 0}


@router.get("/costs/by-project")
async def get_costs_by_project():
    """Get costs grouped by project."""
    try:
        from backend.utils.cost_tracker import get_cost_by_project
        return get_cost_by_project()
    except ImportError:
        try:
            from utils.cost_tracker import get_cost_by_project
            return get_cost_by_project()
        except ImportError:
            return []
    except Exception as e:
        logger.error(f"Cost by project failed: {e}")
        return []


@router.get("/costs/recent")
async def get_recent_costs(limit: int = 100):
    """Get recent cost entries for detailed view."""
    try:
        from utils.database.supabase_client import get_supabase
        client = get_supabase()
        if not client:
            return {"error": "Supabase not available", "records": []}
        
        result = client.table("cost_tracking").select("*").order(
            "created_at", desc=True
        ).limit(limit).execute()
        
        return {"records": result.data or [], "count": len(result.data or [])}
    except Exception as e:
        logger.error(f"Recent costs query failed: {e}")
        return {"records": [], "count": 0, "error": str(e)}


@router.get("/costs/daily")
async def get_daily_costs(days: int = 7):
    """Get daily cost breakdown."""
    try:
        from backend.utils.cost_tracker import get_daily_costs
        return get_daily_costs(days=days)
    except ImportError:
        try:
            from utils.cost_tracker import get_daily_costs
            return get_daily_costs(days=days)
        except ImportError:
            return []
    except Exception as e:
        logger.error(f"Daily costs failed: {e}")
        return []


@router.get("/costs/month")
async def get_month_costs(year: int = None, month: int = None):
    """Get costs for a specific calendar month (includes fixed costs)."""
    try:
        from backend.utils.cost_tracker import get_month_costs
        return get_month_costs(year=year, month=month)
    except ImportError:
        try:
            from utils.cost_tracker import get_month_costs
            return get_month_costs(year=year, month=month)
        except ImportError:
            return {"error": "Cost tracker not available"}
    except Exception as e:
        logger.error(f"Month costs failed: {e}")
        return {"error": str(e)}


@router.get("/costs/fixed")
async def get_fixed_costs():
    """Get fixed/subscription costs."""
    try:
        from backend.utils.cost_tracker import get_fixed_costs
        return get_fixed_costs()
    except ImportError:
        try:
            from utils.cost_tracker import get_fixed_costs
            return get_fixed_costs()
        except ImportError:
            return {"error": "Cost tracker not available", "items": [], "total": 0}
    except Exception as e:
        logger.error(f"Fixed costs failed: {e}")
        return {"error": str(e), "items": [], "total": 0}


@router.put("/costs/fixed/{name}")
async def update_fixed_cost(name: str, cost_per_unit: float = None, quantity: int = None):
    """Update a fixed cost entry."""
    try:
        from backend.utils.cost_tracker import update_fixed_cost
        return update_fixed_cost(name=name, cost_per_unit=cost_per_unit, quantity=quantity)
    except ImportError:
        try:
            from utils.cost_tracker import update_fixed_cost
            return update_fixed_cost(name=name, cost_per_unit=cost_per_unit, quantity=quantity)
        except ImportError:
            return {"error": "Cost tracker not available"}
    except Exception as e:
        logger.error(f"Update fixed cost failed: {e}")
        return {"error": str(e)}
