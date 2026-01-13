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
    ├── relationship_resolver.py  # Evolution 10: Multi-hop relationship queries
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
__version__ = "8.0.0"  # v8.0: Phase 3 - Synthesis Pipeline

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

# Synthesizer - NOW FROM synthesis_pipeline.py (Phase 3 clean implementation)
from .synthesis_pipeline import SynthesisPipeline, Synthesizer  # Synthesizer is alias for backward compat

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

# Metadata Reasoner (Fallback for unknown terms - queries existing metadata)
from .metadata_reasoner import (
    MetadataReasoner,
    ReasonedMatch,
    reason_about_term,
)

# Chunk Classifier (Five Truths domain tagging at upload time)
from .chunk_classifier import (
    ChunkClassifier,
    ClassificationResult,
    get_classifier,
    classify_document,
)

# Truth Router (Query-aware vector search routing)
from .truth_router import (
    TruthRouter,
    TruthQuery,
    RoutingResult,
    get_router,
    route_query,
)

# Source Prioritizer (Authority-based result re-ranking)
from .source_prioritizer import (
    SourcePrioritizer,
    get_prioritizer,
    prioritize_truths,
    prioritize_results,
)

# Relevance Scorer (Multi-factor scoring and filtering)
from .relevance_scorer import (
    RelevanceScorer,
    RelevanceScore,
    get_scorer,
    score_and_filter,
    score_and_filter_raw,
)

# Citation Tracker (Source provenance tracking)
from .citation_tracker import (
    Citation,
    CitationCollector,
    create_collector,
    collect_citations_from_truths,
)

# Gap Detector (Missing truth coverage detection)
from .gap_detector import (
    Gap,
    GapAnalysis,
    GapDetector,
    get_detector as get_gap_detector,
    detect_gaps,
    detect_gaps_from_gathered,
)

# Relationship Resolver (Evolution 10: Multi-hop relationship queries)
from .relationship_resolver import (
    RelationshipResolver,
    Relationship,
    RelationshipChain,
    RelationshipType,
    MultiHopJoin,
    detect_multi_hop_query,
    get_resolver as get_relationship_resolver,
)

# =========================================================================
# PHASE 3: SYNTHESIS COMPONENTS
# =========================================================================

# Truth Assembler (Phase 3.1: Five Truths Assembly)
from .truth_assembler import (
    TruthAssembler,
    TruthContext,
    RealityContext,
    IntentContext,
    ConfigurationContext,
    ReferenceContext,
    RegulatoryContext,
    get_assembler,
    assemble_truths,
)

# LLM Prompter (Phase 3.2: Local LLM Prompt Engineering)
from .llm_prompter import (
    LocalLLMPrompter,
    ResponseQuality,
    get_prompter,
    build_synthesis_prompt,
    build_sql_explanation_prompt,
    build_gap_explanation_prompt,
)

# Enhanced Gap Detector (Phase 3.3: Gap Detection Logic)
from .enhanced_gap_detector import (
    EnhancedGapDetector,
    GapExplainer,
    GapType,
    GapRule,
    get_detector as get_enhanced_gap_detector,
    get_explainer as get_gap_explainer,
    detect_gaps as detect_enhanced_gaps,
    explain_gap,
)

# Response Patterns (Phase 3.4: Consultative Response Patterns)
from .response_patterns import (
    ResponseFormatter,
    ConsultativeResponse,
    ResponseSection,
    get_formatter,
    format_response,
    render_response,
)

# Synthesis Pipeline (Phase 3: Main Orchestrator)
# Note: SynthesisPipeline and Synthesizer already imported above
from .synthesis_pipeline import get_pipeline, create_synthesizer

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
    'Synthesizer',           # Alias for SynthesisPipeline (backward compat)
    'SynthesisPipeline',     # Phase 3: New clean implementation
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
    
    # Metadata Reasoner
    'MetadataReasoner',
    'ReasonedMatch',
    'reason_about_term',
    
    # Chunk Classifier
    'ChunkClassifier',
    'ClassificationResult',
    'get_classifier',
    'classify_document',
    
    # Truth Router
    'TruthRouter',
    'TruthQuery',
    'RoutingResult',
    'get_router',
    'route_query',
    
    # Source Prioritizer
    'SourcePrioritizer',
    'get_prioritizer',
    'prioritize_truths',
    'prioritize_results',
    
    # Relevance Scorer
    'RelevanceScorer',
    'RelevanceScore',
    'get_scorer',
    'score_and_filter',
    'score_and_filter_raw',
    
    # Citation Tracker
    'Citation',
    'CitationCollector',
    'create_collector',
    'collect_citations_from_truths',
    
    # Gap Detector
    'Gap',
    'GapAnalysis',
    'GapDetector',
    'get_gap_detector',
    'detect_gaps',
    'detect_gaps_from_gathered',
    
    # Relationship Resolver (Evolution 10)
    'RelationshipResolver',
    'Relationship',
    'RelationshipChain',
    'RelationshipType',
    'MultiHopJoin',
    'detect_multi_hop_query',
    'get_relationship_resolver',
    
    # Phase 3: Truth Assembler
    'TruthAssembler',
    'TruthContext',
    'RealityContext',
    'IntentContext',
    'ConfigurationContext',
    'ReferenceContext',
    'RegulatoryContext',
    'get_assembler',
    'assemble_truths',
    
    # Phase 3: LLM Prompter
    'LocalLLMPrompter',
    'ResponseQuality',
    'get_prompter',
    'build_synthesis_prompt',
    'build_sql_explanation_prompt',
    'build_gap_explanation_prompt',
    
    # Phase 3: Enhanced Gap Detector
    'EnhancedGapDetector',
    'GapExplainer',
    'GapType',
    'GapRule',
    'get_enhanced_gap_detector',
    'get_gap_explainer',
    'detect_enhanced_gaps',
    'explain_gap',
    
    # Phase 3: Response Patterns
    'ResponseFormatter',
    'ConsultativeResponse',
    'ResponseSection',
    'get_formatter',
    'format_response',
    'render_response',
    
    # Phase 3: Synthesis Pipeline
    'SynthesisPipeline',
    'get_pipeline',
    'create_synthesizer',
    
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
