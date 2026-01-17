"""
XLR8 ENGINE FRAMEWORK
=====================

Five core engines that power all analysis:

1. AGGREGATE - Summarize data by dimensions (COUNT, SUM, AVG, MIN, MAX)
2. COMPARE   - Find differences between two data sets
3. VALIDATE  - Check data against rules (format, range, referential, custom)
4. DETECT    - Find patterns (duplicates, orphans, outliers, anomalies)
5. MAP       - Build translation tables between value sets

ARCHITECTURE
============

Each engine:
- Takes a config dict
- Returns a standard EngineResult
- Has full provenance (audit trail)
- Is stateless (no side effects)

Engines WRAP existing implementations:
- AggregateEngine wraps SQLAssembler
- CompareEngine wraps ComparisonEngine
- ValidateEngine wraps ComplianceEngine (coming soon)
- DetectEngine wraps ProjectIntelligence detection (coming soon)
- MapEngine wraps TermIndex mapping (coming soon)

This gives us:
- Single interface for all consumers (Chat, BI, Playbooks, API)
- No breaking changes to existing code
- Incremental migration path
- Easy testing

USAGE
=====

    from backend.engines import AggregateEngine, CompareEngine, EngineResult
    
    # Aggregate - question mode
    engine = AggregateEngine(conn, project)
    result = engine.execute({"question": "count employees by state"})
    
    # Aggregate - config mode
    result = engine.execute({
        "source_table": "employees",
        "measures": [{"function": "COUNT"}],
        "dimensions": ["state"]
    })
    
    # Compare
    engine = CompareEngine(conn, project)
    result = engine.execute({
        "source_a": "source_data",
        "source_b": "target_data"
    })
    
    # All engines return EngineResult
    print(result.status)      # SUCCESS, PARTIAL, FAILURE, NO_DATA
    print(result.data)        # List of dicts
    print(result.row_count)   # Number of rows
    print(result.sql)         # SQL that was executed
    print(result.provenance)  # Full audit trail
    print(result.findings)    # For Validate/Detect engines

Author: XLR8 Team
Version: 1.0.0
Date: January 2026
"""

import logging

logger = logging.getLogger(__name__)

# =============================================================================
# BASE CLASSES
# =============================================================================

from .base import (
    # Enums
    EngineType,
    Severity,
    ResultStatus,
    
    # Data classes
    Finding,
    Provenance,
    EngineResult,
    
    # Base class
    BaseEngine,
    
    # Helpers
    generate_finding_id
)

# =============================================================================
# ENGINES
# =============================================================================

# Compare Engine - wraps ComparisonEngine
from .compare import CompareEngine, compare

# Aggregate Engine - wraps SQLAssembler
from .aggregate import AggregateEngine, AggregateFunction, aggregate

# Validate Engine - wraps ComplianceEngine
from .validate import ValidateEngine, ValidationType, validate

# Detect Engine - wraps ProjectIntelligence detection
from .detect import DetectEngine, DetectionType, detect

# Map Engine - wraps TermIndex mapping
from .map import MapEngine, MapMode, map_values, transform, crosswalk


# =============================================================================
# ENGINE REGISTRY
# =============================================================================

ENGINE_REGISTRY = {
    EngineType.COMPARE: CompareEngine,
    EngineType.AGGREGATE: AggregateEngine,
    EngineType.VALIDATE: ValidateEngine,
    EngineType.DETECT: DetectEngine,
    EngineType.MAP: MapEngine,
}


def get_engine(engine_type: EngineType, conn, project: str) -> BaseEngine:
    """
    Factory function to get an engine instance.
    
    Args:
        engine_type: The type of engine to create
        conn: DuckDB connection
        project: Project ID
        
    Returns:
        Engine instance
        
    Raises:
        ValueError: If engine type not implemented
    """
    engine_class = ENGINE_REGISTRY.get(engine_type)
    if not engine_class:
        raise ValueError(f"Engine type '{engine_type.value}' not implemented")
    
    return engine_class(conn, project)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Enums
    'EngineType',
    'Severity',
    'ResultStatus',
    'AggregateFunction',
    'ValidationType',
    'DetectionType',
    'MapMode',
    
    # Data classes
    'Finding',
    'Provenance',
    'EngineResult',
    
    # Base
    'BaseEngine',
    
    # Engines
    'CompareEngine',
    'AggregateEngine',
    'ValidateEngine',
    'DetectEngine',
    'MapEngine',
    
    # Convenience functions
    'compare',
    'aggregate',
    'validate',
    'detect',
    'map_values',
    'transform',
    'crosswalk',
    
    # Factory
    'get_engine',
    'ENGINE_REGISTRY',
    
    # Helpers
    'generate_finding_id',
]

logger.info(f"[ENGINES] Loaded {len(ENGINE_REGISTRY)} engines: {[e.value for e in ENGINE_REGISTRY.keys()]}")
