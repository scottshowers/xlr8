"""
XLR8 COMPARE ENGINE
===================

Find differences between two data sets.

This is a WRAPPER around the existing ComparisonEngine.
We don't rewrite working code - we standardize the interface.

Capabilities:
- Row-level comparison (what's in A not in B, what's in B not in A)
- Field-level comparison (same key, different values)
- Auto-detection of join keys
- Full provenance on all results

Author: XLR8 Team
Version: 1.0.0
Date: January 2026
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from .base import (
    BaseEngine, 
    EngineType, 
    EngineResult, 
    ResultStatus,
    Finding,
    Severity,
    generate_finding_id
)

logger = logging.getLogger(__name__)

# Import existing ComparisonEngine
COMPARISON_ENGINE_AVAILABLE = False
ComparisonEngine = None
ComparisonResult = None

try:
    from utils.features.comparison_engine import (
        ComparisonEngine as _ComparisonEngine,
        ComparisonResult as _ComparisonResult,
        get_comparison_engine
    )
    ComparisonEngine = _ComparisonEngine
    ComparisonResult = _ComparisonResult
    COMPARISON_ENGINE_AVAILABLE = True
    logger.info("[COMPARE] ComparisonEngine loaded from utils.features")
except ImportError:
    try:
        from backend.utils.features.comparison_engine import (
            ComparisonEngine as _ComparisonEngine,
            ComparisonResult as _ComparisonResult,
            get_comparison_engine
        )
        ComparisonEngine = _ComparisonEngine
        ComparisonResult = _ComparisonResult
        COMPARISON_ENGINE_AVAILABLE = True
        logger.info("[COMPARE] ComparisonEngine loaded from backend.utils.features")
    except ImportError as e:
        logger.warning(f"[COMPARE] ComparisonEngine not available: {e}")


class CompareEngine(BaseEngine):
    """
    Engine for comparing two data sets.
    
    Wraps the existing ComparisonEngine with a standard interface.
    
    Config Schema:
    {
        "source_a": "table_name_a",           # Required
        "source_b": "table_name_b",           # Required
        "match_keys": ["col1", "col2"],       # Optional - auto-detected if not provided
        "compare_columns": ["col3", "col4"],  # Optional - all common cols if not provided
        "limit": 100                          # Optional - max rows per category
    }
    
    Future enhancements (not yet implemented):
    - Numeric tolerance: {"column": "salary", "tolerance": 0.01}
    - Value mapping: {"source_a_value": "A", "source_b_value": "Active"}
    - Case sensitivity options
    """
    
    VERSION = "1.0.0"
    
    @property
    def engine_type(self) -> EngineType:
        return EngineType.COMPARE
    
    @property
    def engine_version(self) -> str:
        return self.VERSION
    
    def _validate_config(self, config: Dict) -> List[str]:
        """Validate compare configuration."""
        errors = []
        
        if not COMPARISON_ENGINE_AVAILABLE:
            errors.append("ComparisonEngine is not available")
            return errors
        
        if not config.get("source_a"):
            errors.append("'source_a' is required")
        
        if not config.get("source_b"):
            errors.append("'source_b' is required")
        
        # Validate tables exist
        if config.get("source_a"):
            if not self._table_exists(config["source_a"]):
                errors.append(f"Table '{config['source_a']}' does not exist")
        
        if config.get("source_b"):
            if not self._table_exists(config["source_b"]):
                errors.append(f"Table '{config['source_b']}' does not exist")
        
        return errors
    
    def _table_exists(self, table_name: str) -> bool:
        """Check if a table exists."""
        try:
            self.conn.execute(f"SELECT 1 FROM \"{table_name}\" LIMIT 1")
            return True
        except:
            return False
    
    def _execute(self, config: Dict) -> EngineResult:
        """Execute the comparison using existing ComparisonEngine."""
        
        source_a = config["source_a"]
        source_b = config["source_b"]
        match_keys = config.get("match_keys")
        compare_columns = config.get("compare_columns")
        limit = config.get("limit", 100)
        
        logger.info(f"[COMPARE] Comparing {source_a} vs {source_b}")
        
        # Get or create the underlying engine
        # Pass None for handler - it will lazy-load
        comparison_engine = ComparisonEngine(structured_handler=None)
        
        # We need to give it our connection
        # The existing engine expects a handler with .query() method
        # Create a minimal adapter
        class ConnectionAdapter:
            def __init__(self, conn):
                self._conn = conn
            
            def query(self, sql: str) -> List[Dict]:
                result = self._conn.execute(sql).fetchdf()
                return result.to_dict('records')
        
        comparison_engine.handler = ConnectionAdapter(self.conn)
        
        # Execute comparison
        comparison_result = comparison_engine.compare(
            table_a=source_a,
            table_b=source_b,
            join_keys=match_keys,
            compare_columns=compare_columns,
            project_id=self.project,
            limit=limit
        )
        
        # Convert to standard EngineResult
        return self._convert_result(comparison_result, config)
    
    def _convert_result(self, 
                       comparison_result: 'ComparisonResult',
                       config: Dict) -> EngineResult:
        """Convert ComparisonResult to standard EngineResult."""
        
        # Build findings from comparison results
        findings = []
        
        # Only in A
        if comparison_result.only_in_a:
            findings.append(Finding(
                finding_id=generate_finding_id("only_in_source_a", config["source_a"]),
                finding_type="only_in_source_a",
                severity=Severity.WARNING,
                message=f"{len(comparison_result.only_in_a)} records exist only in {config['source_a']}",
                affected_records=len(comparison_result.only_in_a),
                evidence=comparison_result.only_in_a[:5],  # Sample
                details={
                    "source": config["source_a"],
                    "count": len(comparison_result.only_in_a)
                }
            ))
        
        # Only in B
        if comparison_result.only_in_b:
            findings.append(Finding(
                finding_id=generate_finding_id("only_in_source_b", config["source_b"]),
                finding_type="only_in_source_b",
                severity=Severity.WARNING,
                message=f"{len(comparison_result.only_in_b)} records exist only in {config['source_b']}",
                affected_records=len(comparison_result.only_in_b),
                evidence=comparison_result.only_in_b[:5],
                details={
                    "source": config["source_b"],
                    "count": len(comparison_result.only_in_b)
                }
            ))
        
        # Mismatches
        if comparison_result.mismatches:
            findings.append(Finding(
                finding_id=generate_finding_id("value_mismatch", f"{config['source_a']}:{config['source_b']}"),
                finding_type="value_mismatch",
                severity=Severity.ERROR,
                message=f"{len(comparison_result.mismatches)} records have value differences",
                affected_records=len(comparison_result.mismatches),
                evidence=comparison_result.mismatches[:5],
                details={
                    "count": len(comparison_result.mismatches)
                }
            ))
        
        # Build combined data output
        # Structure: list of all differences with type tag
        data = []
        
        for row in comparison_result.only_in_a:
            data.append({
                "_difference_type": "only_in_a",
                "_source": config["source_a"],
                **row
            })
        
        for row in comparison_result.only_in_b:
            data.append({
                "_difference_type": "only_in_b", 
                "_source": config["source_b"],
                **row
            })
        
        for mismatch in comparison_result.mismatches:
            data.append({
                "_difference_type": "mismatch",
                "_keys": mismatch.get("keys", {}),
                "_differences": mismatch.get("differences", [])
            })
        
        # Determine columns from data
        columns = []
        if data:
            columns = list(data[0].keys())
        
        # Determine status
        if comparison_result.has_differences:
            status = ResultStatus.SUCCESS  # Completed successfully, found differences
        else:
            status = ResultStatus.SUCCESS  # Completed successfully, no differences
        
        # Build summary
        summary_parts = []
        if comparison_result.matches:
            summary_parts.append(f"{comparison_result.matches} matched")
        if comparison_result.only_in_a:
            summary_parts.append(f"{len(comparison_result.only_in_a)} only in A")
        if comparison_result.only_in_b:
            summary_parts.append(f"{len(comparison_result.only_in_b)} only in B")
        if comparison_result.mismatches:
            summary_parts.append(f"{len(comparison_result.mismatches)} mismatches")
        
        summary = ", ".join(summary_parts) if summary_parts else "No differences found"
        
        return EngineResult(
            status=status,
            data=data,
            row_count=len(data),
            columns=columns,
            provenance=self._create_provenance(
                execution_id="",  # Will be filled by base class
                config_hash="",   # Will be filled by base class
                source_tables=[config["source_a"], config["source_b"]],
                sql_executed=[],  # ComparisonEngine doesn't expose SQL
                warnings=[]
            ),
            findings=findings,
            summary=summary,
            metadata={
                "match_rate": comparison_result.match_rate,
                "source_a_rows": comparison_result.source_a_rows,
                "source_b_rows": comparison_result.source_b_rows,
                "join_keys": comparison_result.join_keys,
                "compared_columns": comparison_result.compared_columns,
                "comparison_id": comparison_result.comparison_id,
                "matches": comparison_result.matches,
                "only_in_a_count": len(comparison_result.only_in_a),
                "only_in_b_count": len(comparison_result.only_in_b),
                "mismatch_count": len(comparison_result.mismatches)
            }
        )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def compare(conn, 
           project: str,
           source_a: str, 
           source_b: str,
           match_keys: List[str] = None,
           compare_columns: List[str] = None,
           limit: int = 100) -> EngineResult:
    """
    Convenience function to run a comparison.
    
    Args:
        conn: DuckDB connection
        project: Project ID
        source_a: First table name
        source_b: Second table name
        match_keys: Columns to join on (auto-detected if not provided)
        compare_columns: Columns to compare (all common if not provided)
        limit: Max rows per category
        
    Returns:
        EngineResult with comparison findings
    """
    engine = CompareEngine(conn, project)
    return engine.execute({
        "source_a": source_a,
        "source_b": source_b,
        "match_keys": match_keys,
        "compare_columns": compare_columns,
        "limit": limit
    })
