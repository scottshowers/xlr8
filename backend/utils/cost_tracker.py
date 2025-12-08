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
        # RunPod GPU pricing varies - using estimate for A40/A100
        "per_second": 0.00039,      # ~$1.40/hr for mid-tier GPU
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
