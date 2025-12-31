"""
XLR8 Intelligence Engine - Gatherers Package
=============================================

Gatherers for the Five Truths architecture.

Each gatherer knows:
1. Its truth_type (reality, intent, configuration, reference, regulatory, compliance)
2. Its storage_type (duckdb or chromadb)
3. How to query and return Truth objects with provenance

Truth Type → Storage Routing:
-----------------------------
| Truth         | Storage  | Scope    |
|---------------|----------|----------|
| Reality       | DuckDB   | Project  |
| Intent        | ChromaDB | Project  |
| Configuration | DuckDB   | Project  |
| Reference     | ChromaDB | Global   |
| Regulatory    | ChromaDB | Global   |
| Compliance    | ChromaDB | Global   |

Deploy to: backend/utils/intelligence/gatherers/__init__.py
"""

from .base import BaseGatherer, DuckDBGatherer, ChromaDBGatherer
from .reality import RealityGatherer
from .intent import IntentGatherer
from .configuration import ConfigurationGatherer
from .reference import ReferenceGatherer
from .regulatory import RegulatoryGatherer
from .compliance import ComplianceGatherer

__all__ = [
    # Base classes
    'BaseGatherer',
    'DuckDBGatherer', 
    'ChromaDBGatherer',
    
    # Customer-scoped gatherers
    'RealityGatherer',      # DuckDB - employee data, transactions
    'IntentGatherer',       # ChromaDB - SOWs, requirements
    'ConfigurationGatherer', # DuckDB - code tables, mappings
    
    # Global-scoped gatherers (Reference Library)
    'ReferenceGatherer',    # ChromaDB - product docs, best practices
    'RegulatoryGatherer',   # ChromaDB - laws, IRS rules
    'ComplianceGatherer',   # ChromaDB - audit requirements, controls
]
