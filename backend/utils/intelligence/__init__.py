"""
XLR8 Intelligence Engine Module
================================

The brain of XLR8 - orchestrates the Five Truths architecture.

Usage:
    from backend.utils.intelligence import IntelligenceEngine
    
    engine = IntelligenceEngine(project_name="ABC123")
    engine.load_context(structured_handler=handler, schema=schema)
    answer = engine.ask("How many employees are active?")

Module Structure:
    intelligence/
    ├── __init__.py          # This file - exports IntelligenceEngine
    ├── types.py             # Shared data classes (Truth, SynthesizedAnswer, etc.)
    ├── engine.py            # Main orchestrator (thin)
    ├── table_selector.py    # Table scoring and selection
    ├── sql_generator.py     # SQL generation via LLM
    ├── synthesizer.py       # Response synthesis
    ├── filters.py           # Filter detection and clarification
    ├── validators.py        # Config validation logic
    └── gatherers/           # One file per Truth type
        ├── base.py          # Abstract gatherer
        ├── reality.py       # DuckDB queries
        ├── intent.py        # Customer docs (ChromaDB)
        ├── configuration.py # Config tables (DuckDB)
        ├── reference.py     # Product docs (ChromaDB)
        └── regulatory.py    # Laws/compliance (ChromaDB)

Deploy to: backend/utils/intelligence/__init__.py
"""

# Version
__version__ = "6.0.0"

# Core types (always available)
from .types import (
    Truth,
    Conflict,
    Insight,
    ComplianceRule,
    SynthesizedAnswer,
    IntelligenceMode,
    TruthType,
    StorageType,
    TRUTH_ROUTING,
    LOOKUP_INDICATORS,
)

# Table selector
from .table_selector import TableSelector

# SQL Generator
from .sql_generator import SQLGenerator

# Synthesizer
from .synthesizer import Synthesizer

# Gatherers
from .gatherers import (
    BaseGatherer,
    DuckDBGatherer,
    ChromaDBGatherer,
    RealityGatherer,
)

# Main engine - import from legacy file for now during migration
# TODO: Replace with new modular engine once refactor is complete
try:
    from backend.utils.intelligence_engine import IntelligenceEngine
except ImportError:
    try:
        from utils.intelligence_engine import IntelligenceEngine
    except ImportError:
        # Placeholder until refactor is complete
        IntelligenceEngine = None

# New modular engine (V2)
from .engine import IntelligenceEngineV2

__all__ = [
    # Core types
    'Truth',
    'Conflict', 
    'Insight',
    'ComplianceRule',
    'SynthesizedAnswer',
    'IntelligenceMode',
    'TruthType',
    'StorageType',
    'TRUTH_ROUTING',
    'LOOKUP_INDICATORS',
    
    # Components
    'TableSelector',
    'SQLGenerator',
    'Synthesizer',
    
    # Gatherers
    'BaseGatherer',
    'DuckDBGatherer',
    'ChromaDBGatherer',
    'RealityGatherer',
    
    # Main engine
    'IntelligenceEngine',
    'IntelligenceEngineV2',
]
