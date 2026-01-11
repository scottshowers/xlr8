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
    ├── truth_enricher.py    # LLM Lookups - extracts structured data from truths
    └── gatherers/           # One file per Truth type
        ├── base.py          # Abstract gatherer
        ├── reality.py       # DuckDB queries
        ├── intent.py        # Customer docs (ChromaDB)
        ├── configuration.py # Config tables (DuckDB)
        ├── reference.py     # Product docs (ChromaDB)
        ├── regulatory.py    # Laws/compliance (ChromaDB)
        └── compliance.py    # Audit/controls (ChromaDB)

Deploy to: backend/utils/intelligence/__init__.py
"""

# Version
__version__ = "7.0.0"  # v7.0: SQLAssembler - Deterministic SQL generation

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

# Truth Enricher (LLM Lookups)
from .truth_enricher import TruthEnricher

# Intent Parser (SOW/Requirements parsing)
from .intent_parser import IntentParser, ParsedRequirement, parse_sow

# Term Index (Load-time intelligence for deterministic query resolution)
from .term_index import (
    TermIndex,
    TermMatch,
    JoinPath,
    VendorSchemaLoader,
    recalc_term_index,
)

# SQL Assembler (Deterministic SQL generation from term matches)
from .sql_assembler import (
    SQLAssembler,
    AssembledQuery,
    assemble_query,
)

# Gatherers
from .gatherers import (
    BaseGatherer,
    DuckDBGatherer,
    ChromaDBGatherer,
    RealityGatherer,
    IntentGatherer,
    ConfigurationGatherer,
    ReferenceGatherer,
    RegulatoryGatherer,
    ComplianceGatherer,
)

# Modular engine (V2) - THE engine going forward
from .engine import IntelligenceEngineV2

# Legacy alias - IntelligenceEngine now points to IntelligenceEngineV2
IntelligenceEngine = IntelligenceEngineV2

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
    'TruthEnricher',
    'IntentParser',
    'ParsedRequirement',
    'parse_sow',
    
    # Term Index
    'TermIndex',
    'TermMatch',
    'JoinPath',
    'VendorSchemaLoader',
    'recalc_term_index',
    
    # SQL Assembler
    'SQLAssembler',
    'AssembledQuery',
    'assemble_query',
    
    # Gatherers
    'BaseGatherer',
    'DuckDBGatherer',
    'ChromaDBGatherer',
    'RealityGatherer',
    'IntentGatherer',
    'ConfigurationGatherer',
    'ReferenceGatherer',
    'RegulatoryGatherer',
    'ComplianceGatherer',
    
    # Main engine
    'IntelligenceEngine',
    'IntelligenceEngineV2',
]
