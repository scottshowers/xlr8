"""
Cost Tracker - Centralized cost logging for all paid services
=============================================================

Tracks:
- Claude API (per token)
- RunPod/Ollama Local LLM (per second)
- AWS Textract (per page)

Usage:
    from backend.utils.cost_tracker import log_cost, CostService

    # Claude API call
    log_cost(
        service=CostService.CLAUDE,
        operation="chat",
        tokens_in=1500,
        tokens_out=800,
        project_id="xxx"
    )

    # Local LLM call
    log_cost(
        service=CostService.RUNPOD,
        operation="pdf_parse",
        duration_ms=3500,
        project_id="xxx"
    )

    # Textract call
    log_cost(
        service=CostService.TEXTRACT,
        operation="vacuum",
        pages=15,
        project_id="xxx"
    )
"""

import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)

# =============================================================================
# PRICING CONFIGURATION (as of Dec 2025)
# =============================================================================

class CostService(str, Enum):
    CLAUDE = "claude"
    RUNPOD = "runpod"
    TEXTRACT = "textract"
    OPENAI = "openai"  # Future
    VOYAGE = "voyage"  # Embeddings


# Pricing per unit (USD)
PRICING = {
    CostService.CLAUDE: {
        # Claude 3.5 Sonnet pricing
        "input_per_1k": 0.003,      # $3 per 1M input tokens
        "output_per_1k": 0.015,     # $15 per 1M output tokens
    },
    CostService.RUNPOD: {
        # RunPod GPU pricing - user's actual rate
        "per_hour": 0.06,           # $0.06/hr
        "per_second": 0.06 / 3600,  # ~$0.0000167/sec
    },
    CostService.TEXTRACT: {
        # AWS Textract pricing
        "per_page_detect": 0.0015,  # DetectDocumentText
        "per_page_analyze": 0.015,  # AnalyzeDocument (tables/forms)
    },
    CostService.VOYAGE: {
        "per_1k_tokens": 0.0001,    # Voyage embeddings
    }
}


# =============================================================================
# COST CALCULATION
# =============================================================================

def calculate_cost(
    service: CostService,
    tokens_in: int = 0,
    tokens_out: int = 0,
    duration_ms: int = 0,
    pages: int = 0,
    textract_type: str = "detect"
) -> float:
    """Calculate estimated cost based on service and usage."""
    
    if service == CostService.CLAUDE:
        input_cost = (tokens_in / 1000) * PRICING[service]["input_per_1k"]
        output_cost = (tokens_out / 1000) * PRICING[service]["output_per_1k"]
        return input_cost + output_cost
    
    elif service == CostService.RUNPOD:
        seconds = duration_ms / 1000
        return seconds * PRICING[service]["per_second"]
    
    elif service == CostService.TEXTRACT:
        if textract_type == "analyze":
            return pages * PRICING[service]["per_page_analyze"]
        return pages * PRICING[service]["per_page_detect"]
    
    elif service == CostService.VOYAGE:
        total_tokens = tokens_in + tokens_out
        return (total_tokens / 1000) * PRICING[service]["per_1k_tokens"]
    
    return 0.0


# =============================================================================
# FIXED COSTS MANAGEMENT
# =============================================================================

def get_fixed_costs() -> Dict[str, Any]:
    """Get all fixed/subscription costs from platform_costs table."""
    client = _get_supabase()
    if not client:
        return {"error": "Supabase not available", "items": [], "total": 0}
    
    try:
        result = client.table("platform_costs").select("*").eq(
            "category", "subscription"
        ).eq("is_active", True).execute()
        
        items = result.data or []
        total = sum(
            (item.get("cost_per_unit", 0) * item.get("quantity", 1))
            for item in items
        )
        
        return {
            "items": items,
            "total": round(total, 2),
            "count": len(items)
        }
    except Exception as e:
        logger.error(f"[COST] Fixed costs query failed: {e}")
        return {"error": str(e), "items": [], "total": 0}


def update_fixed_cost(name: str, cost_per_unit: float = None, quantity: int = None) -> Dict:
    """Update a fixed cost entry."""
    client = _get_supabase()
    if not client:
        return {"error": "Supabase not available"}
    
    try:
        updates = {"updated_at": datetime.utcnow().isoformat()}
        if cost_per_unit is not None:
            updates["cost_per_unit"] = cost_per_unit
        if quantity is not None:
            updates["quantity"] = quantity
        
        result = client.table("platform_costs").update(updates).eq(
            "name", name
        ).execute()
        
        return {"success": True, "updated": result.data}
    except Exception as e:
        logger.error(f"[COST] Update fixed cost failed: {e}")
        return {"error": str(e)}


def get_daily_costs(days: int = 7) -> list:
    """Get daily cost breakdown for the last N days."""
    client = _get_supabase()
    if not client:
        return []
    
    try:
        from datetime import timedelta
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        result = client.table("cost_tracking").select(
            "created_at, estimated_cost, service"
        ).gte("created_at", cutoff).execute()
        
        records = result.data or []
        
        # Aggregate by day
        by_day = {}
        for r in records:
            day = r.get("created_at", "")[:10]  # YYYY-MM-DD
            cost = r.get("estimated_cost", 0) or 0
            
            if day not in by_day:
                by_day[day] = {"date": day, "total": 0, "by_service": {}}
            
            by_day[day]["total"] += cost
            svc = r.get("service", "unknown")
            by_day[day]["by_service"][svc] = by_day[day]["by_service"].get(svc, 0) + cost
        
        # Sort and round
        daily_list = sorted(by_day.values(), key=lambda x: x["date"], reverse=True)
        for day in daily_list:
            day["total"] = round(day["total"], 4)
            day["by_service"] = {k: round(v, 4) for k, v in day["by_service"].items()}
        
        return daily_list
        
    except Exception as e:
        logger.error(f"[COST] Daily costs query failed: {e}")
        return []


def get_month_costs(year: int = None, month: int = None) -> Dict[str, Any]:
    """Get costs for a specific calendar month."""
    client = _get_supabase()
    if not client:
        return {"error": "Supabase not available"}
    
    try:
        from datetime import timedelta
        
        # Default to current month
        now = datetime.utcnow()
        if year is None:
            year = now.year
        if month is None:
            month = now.month
        
        # Calculate month boundaries
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        result = client.table("cost_tracking").select(
            "service, operation, estimated_cost"
        ).gte("created_at", start_date.isoformat()).lt(
            "created_at", end_date.isoformat()
        ).execute()
        
        records = result.data or []
        
        # Aggregate
        total = sum(r.get("estimated_cost", 0) or 0 for r in records)
        by_service = {}
        by_operation = {}
        
        for r in records:
            svc = r.get("service", "unknown")
            op = r.get("operation", "unknown")
            cost = r.get("estimated_cost", 0) or 0
            
            by_service[svc] = by_service.get(svc, 0) + cost
            by_operation[op] = by_operation.get(op, 0) + cost
        
        # Get fixed costs
        fixed = get_fixed_costs()
        
        return {
            "year": year,
            "month": month,
            "month_name": start_date.strftime("%B"),
            "api_usage": round(total, 4),
            "fixed_costs": fixed.get("total", 0),
            "total": round(total + fixed.get("total", 0), 2),
            "by_service": {k: round(v, 4) for k, v in by_service.items()},
            "by_operation": {k: round(v, 4) for k, v in by_operation.items()},
            "call_count": len(records),
            "fixed_items": fixed.get("items", [])
        }
        
    except Exception as e:
        logger.error(f"[COST] Month costs query failed: {e}")
        return {"error": str(e)}


# =============================================================================
# SUPABASE LOGGING
# =============================================================================

_supabase_client = None

def _get_supabase():
    """Lazy load Supabase client."""
    global _supabase_client
    if _supabase_client is None:
        try:
            from utils.database.supabase_client import get_supabase
            _supabase_client = get_supabase()
        except Exception as e:
            logger.warning(f"[COST] Could not load Supabase: {e}")
            _supabase_client = False  # Mark as unavailable
    return _supabase_client if _supabase_client else None


def log_cost(
    service: CostService,
    operation: str,
    tokens_in: int = 0,
    tokens_out: int = 0,
    duration_ms: int = 0,
    pages: int = 0,
    project_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    textract_type: str = "detect"
) -> Optional[Dict]:
    """
    Log a cost entry to Supabase.
    
    Args:
        service: CostService enum (CLAUDE, RUNPOD, TEXTRACT)
        operation: What triggered this (chat, scan, pdf_parse, vacuum)
        tokens_in: Input tokens (for LLMs)
        tokens_out: Output tokens (for LLMs)
        duration_ms: Processing time in milliseconds (for RunPod)
        pages: Number of pages (for Textract)
        project_id: Optional project UUID
        metadata: Optional extra data (model name, file info, etc.)
        textract_type: "detect" or "analyze" for Textract pricing
    
    Returns:
        The created record or None if logging failed
    """
    
    # Calculate cost
    estimated_cost = calculate_cost(
        service=service,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        duration_ms=duration_ms,
        pages=pages,
        textract_type=textract_type
    )
    
    # Build record
    record = {
        "service": service.value,
        "operation": operation,
        "tokens_in": tokens_in if tokens_in else None,
        "tokens_out": tokens_out if tokens_out else None,
        "pages": pages if pages else None,
        "duration_ms": duration_ms if duration_ms else None,
        "estimated_cost": estimated_cost,
        "project_id": project_id,
        "metadata": metadata or {}
    }
    
    # Log locally regardless of Supabase
    logger.warning(f"[COST] {service.value}/{operation}: ${estimated_cost:.6f} "
                   f"(in={tokens_in}, out={tokens_out}, ms={duration_ms}, pages={pages})")
    
    # Try to save to Supabase
    client = _get_supabase()
    if client:
        try:
            result = client.table("cost_tracking").insert(record).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.warning(f"[COST] Failed to save to Supabase: {e}")
            # Still return the record for local tracking
            return record
    
    return record


# =============================================================================
# AGGREGATION QUERIES
# =============================================================================

def get_cost_summary(
    days: int = 30,
    project_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get cost summary for dashboard.
    
    Returns:
        {
            "total_cost": 12.34,
            "by_service": {"claude": 10.00, "runpod": 2.00, "textract": 0.34},
            "by_operation": {"chat": 5.00, "scan": 4.00, ...},
            "by_day": [{"date": "2025-12-07", "cost": 1.50}, ...]
        }
    """
    client = _get_supabase()
    if not client:
        return {"error": "Supabase not available", "total_cost": 0}
    
    try:
        # Get recent records
        query = client.table("cost_tracking").select("*")
        
        if project_id:
            query = query.eq("project_id", project_id)
        
        # Filter by date (last N days)
        from datetime import timedelta
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        query = query.gte("created_at", cutoff)
        
        result = query.order("created_at", desc=True).execute()
        records = result.data or []
        
        # Aggregate
        total_cost = sum(r.get("estimated_cost", 0) or 0 for r in records)
        
        by_service = {}
        by_operation = {}
        by_day = {}
        
        for r in records:
            svc = r.get("service", "unknown")
            op = r.get("operation", "unknown")
            cost = r.get("estimated_cost", 0) or 0
            day = r.get("created_at", "")[:10]  # YYYY-MM-DD
            
            by_service[svc] = by_service.get(svc, 0) + cost
            by_operation[op] = by_operation.get(op, 0) + cost
            by_day[day] = by_day.get(day, 0) + cost
        
        # Sort by_day into list
        daily_list = [{"date": k, "cost": v} for k, v in sorted(by_day.items())]
        
        return {
            "total_cost": round(total_cost, 4),
            "by_service": {k: round(v, 4) for k, v in by_service.items()},
            "by_operation": {k: round(v, 4) for k, v in by_operation.items()},
            "by_day": daily_list,
            "record_count": len(records),
            "days": days
        }
        
    except Exception as e:
        logger.error(f"[COST] Summary query failed: {e}")
        return {"error": str(e), "total_cost": 0}


def get_cost_by_project() -> list:
    """Get total costs grouped by project."""
    client = _get_supabase()
    if not client:
        return []
    
    try:
        result = client.table("cost_tracking").select(
            "project_id, estimated_cost"
        ).execute()
        
        records = result.data or []
        
        # Aggregate by project
        by_project = {}
        for r in records:
            pid = r.get("project_id") or "global"
            cost = r.get("estimated_cost", 0) or 0
            by_project[pid] = by_project.get(pid, 0) + cost
        
        return [
            {"project_id": k, "total_cost": round(v, 4)}
            for k, v in sorted(by_project.items(), key=lambda x: -x[1])
        ]
        
    except Exception as e:
        logger.error(f"[COST] Project query failed: {e}")
        return []
