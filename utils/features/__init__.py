"""
XLR8 Features Module
====================

Reusable feature services available across the platform.

Features:
- comparison_engine: Compare any two data sources
- export_engine: Template-based export to various formats

Usage:
    from utils.features import comparison_engine, export_engine
    
    result = comparison_engine.compare("table_a", "table_b")
    export = export_engine.export_comparison(result, format="xlsx")
"""

from utils.features.comparison_engine import (
    ComparisonEngine,
    ComparisonResult,
    compare,
    get_comparison_engine
)

from utils.features.export_engine import (
    ExportEngine,
    export_comparison,
    export_data,
    get_export_engine
)

__all__ = [
    # Comparison
    'ComparisonEngine',
    'ComparisonResult', 
    'compare',
    'get_comparison_engine',
    # Export
    'ExportEngine',
    'export_comparison',
    'export_data',
    'get_export_engine',
]
