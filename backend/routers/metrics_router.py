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


# =============================================================================
# NEW ENTERPRISE METRICS ENDPOINTS
# =============================================================================

@router.delete("/reset")
async def reset_metrics(confirm: bool = False, include_costs: bool = False):
    """
    Clear all platform metrics for testing/reset purposes.
    
    Args:
        confirm: Must be True to actually delete (safety check)
        include_costs: If True, also clear cost_tracking table
    
    Returns:
        Summary of what was cleared
    """
    if not confirm:
        return {
            "warning": "This will delete all platform metrics. Pass confirm=true to proceed.",
            "will_clear": ["platform_metrics"] + (["cost_tracking"] if include_costs else [])
        }
    
    try:
        from utils.database.supabase_client import get_supabase
        supabase = get_supabase()
        if not supabase:
            return {"error": "Supabase not available"}
        
        cleared = []
        counts = {}
        
        # Clear platform_metrics
        try:
            result = supabase.table("platform_metrics").delete().neq(
                "id", "00000000-0000-0000-0000-000000000000"
            ).execute()
            counts["platform_metrics"] = len(result.data) if result.data else 0
            cleared.append("platform_metrics")
        except Exception as e:
            logger.warning(f"platform_metrics clear failed: {e}")
        
        # Optionally clear cost_tracking
        if include_costs:
            try:
                result = supabase.table("cost_tracking").delete().neq(
                    "id", "00000000-0000-0000-0000-000000000000"
                ).execute()
                counts["cost_tracking"] = len(result.data) if result.data else 0
                cleared.append("cost_tracking")
            except Exception as e:
                logger.warning(f"cost_tracking clear failed: {e}")
        
        return {
            "success": True,
            "cleared": cleared,
            "counts": counts
        }
        
    except Exception as e:
        logger.error(f"Metrics reset failed: {e}")
        return {"error": str(e)}


@router.get("/throughput")
async def get_throughput(hours: int = Query(default=24, ge=1, le=168)):
    """
    Get hourly throughput for charts.
    
    Returns counts of uploads, queries, and LLM calls per hour for the last N hours.
    Used by Dashboard throughput chart.
    
    Args:
        hours: Number of hours to look back (1-168, default 24)
    """
    try:
        from utils.database.supabase_client import get_supabase
        from datetime import datetime, timedelta
        
        supabase = get_supabase()
        if not supabase:
            return {"error": "Supabase not available", "data": []}
        
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        
        result = supabase.table("platform_metrics").select(
            "created_at, metric_type"
        ).gte("created_at", cutoff).order("created_at").execute()
        
        records = result.data or []
        
        # Bucket by hour
        hourly = {}
        for r in records:
            # Parse timestamp and truncate to hour
            ts = r.get("created_at", "")[:13]  # "2025-12-28T14"
            if not ts:
                continue
            
            if ts not in hourly:
                hourly[ts] = {"hour": ts + ":00:00", "uploads": 0, "queries": 0, "llm_calls": 0, "errors": 0}
            
            metric_type = r.get("metric_type", "")
            if metric_type == "upload":
                hourly[ts]["uploads"] += 1
            elif metric_type == "query":
                hourly[ts]["queries"] += 1
            elif metric_type == "llm_call":
                hourly[ts]["llm_calls"] += 1
            elif metric_type == "error":
                hourly[ts]["errors"] += 1
        
        # Sort by hour and return as list
        data = sorted(hourly.values(), key=lambda x: x["hour"])
        
        return {
            "period_hours": hours,
            "data": data,
            "total_records": len(records)
        }
        
    except Exception as e:
        logger.error(f"Throughput query failed: {e}")
        return {"error": str(e), "data": []}


@router.get("/upload-history")
async def get_upload_history(days: int = Query(default=90, ge=1, le=365)):
    """
    Get daily upload counts for sparkline chart.
    
    Returns daily upload counts for the last N days.
    Used by Dashboard upload sparkline.
    
    Args:
        days: Number of days to look back (1-365, default 90)
    """
    try:
        from utils.database.supabase_client import get_supabase
        from datetime import datetime, timedelta
        
        supabase = get_supabase()
        if not supabase:
            return {"error": "Supabase not available", "data": []}
        
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        result = supabase.table("platform_metrics").select(
            "created_at"
        ).eq("metric_type", "upload").gte("created_at", cutoff).order("created_at").execute()
        
        records = result.data or []
        
        # Bucket by day
        daily = {}
        for r in records:
            ts = r.get("created_at", "")[:10]  # "2025-12-28"
            if not ts:
                continue
            if ts not in daily:
                daily[ts] = {"date": ts, "uploads": 0}
            daily[ts]["uploads"] += 1
        
        # Fill in missing days with zero uploads
        today = datetime.utcnow().date()
        all_days = []
        for i in range(days):
            day = today - timedelta(days=days - 1 - i)
            day_str = day.isoformat()
            if day_str in daily:
                all_days.append(daily[day_str])
            else:
                all_days.append({"date": day_str, "uploads": 0})
        
        return {
            "period_days": days,
            "data": all_days,
            "total_uploads": sum(d["uploads"] for d in all_days)
        }
        
    except Exception as e:
        logger.error(f"Upload history query failed: {e}")
        return {"error": str(e), "data": []}


@router.get("/activity")
async def get_activity(limit: int = Query(default=50, ge=1, le=200)):
    """
    Get recent platform events for activity log.
    
    Returns the most recent platform_metrics records for real-time activity display.
    Used by SystemMonitor activity feed.
    
    Args:
        limit: Number of events to return (1-200, default 50)
    """
    try:
        from utils.database.supabase_client import get_supabase
        
        supabase = get_supabase()
        if not supabase:
            return {"error": "Supabase not available", "events": []}
        
        result = supabase.table("platform_metrics").select(
            "id, created_at, metric_type, processor, filename, success, duration_ms, error_message, llm_provider, llm_model"
        ).order("created_at", desc=True).limit(limit).execute()
        
        events = []
        for r in (result.data or []):
            # Format human-readable message
            metric_type = r.get("metric_type", "unknown")
            processor = r.get("processor", "")
            filename = r.get("filename", "")
            success = r.get("success", True)
            duration = r.get("duration_ms", 0)
            llm_provider = r.get("llm_provider", "")
            llm_model = r.get("llm_model", "")
            
            if metric_type == "upload":
                message = f"UPLOAD: {filename or 'file'} via {processor}"
            elif metric_type == "query":
                message = f"QUERY: {processor or 'chat'} query"
            elif metric_type == "llm_call":
                provider = (llm_provider or "LLM").upper()
                message = f"{provider}: {llm_model or 'inference'}"
            elif metric_type == "error":
                message = f"ERROR: {r.get('error_message', 'Unknown error')[:50]}"
            else:
                message = f"{metric_type.upper()}: {processor}"
            
            events.append({
                "id": r.get("id"),
                "time": r.get("created_at"),
                "message": message,
                "status": 0 if success else 1,  # 0=success, 1=error
                "duration_ms": duration,
                "metric_type": metric_type
            })
        
        return {
            "events": events,
            "count": len(events)
        }
        
    except Exception as e:
        logger.error(f"Activity query failed: {e}")
        return {"error": str(e), "events": []}
