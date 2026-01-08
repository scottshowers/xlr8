"""
XLR8 Intelligence Engine v3 - Main Orchestrator
================================================

The brain of XLR8. Thin orchestrator that coordinates:
- Question analysis and mode detection
- Clarification handling (employee status, filters)
- Truth gathering (Reality, Intent, Configuration, Reference, Regulatory)
- Conflict detection
- Response synthesis

v3.0 CHANGES:
- Context Graph integration for intelligent table selection
- Semantic type detection in queries
- Graph-aware JOIN suggestions via TableSelector
- Passes Context Graph to components for scoped queries

CRITICAL: ALL questions gather ALL Five Truths.
Validation questions especially need all truths to triangulate:
- "Is this tax rate correct?" needs Regulatory + Configuration + Reality
- "Are we compliant?" needs Regulatory + Reference + Reality + Configuration

This is the NEW modular engine replacing the 6000-line monolith.

Deploy to: backend/utils/intelligence/engine.py
"""

import re
import os
import logging
from typing import Dict, List, Optional, Any, Tuple

from .types import (
    Truth, Conflict, Insight, SynthesizedAnswer, IntelligenceMode,
    TruthType
)
from .table_selector import TableSelector
from .sql_generator import SQLGenerator
from .synthesizer import Synthesizer
from .truth_enricher import TruthEnricher
from .gatherers import (
    RealityGatherer,
    IntentGatherer,
    ConfigurationGatherer,
    ReferenceGatherer,
    RegulatoryGatherer,
    ComplianceGatherer
)

logger = logging.getLogger(__name__)

__version__ = "7.0.0"  # v3.0: Context Graph integration

# Try to load IntelligentScoping
SCOPING_AVAILABLE = False
analyze_question_scope = None
try:
    from backend.utils.intelligent_scoping import analyze_question_scope
    SCOPING_AVAILABLE = True
    logger.info("[ENGINE-V2] IntelligentScoping loaded")
except ImportError:
    try:
        from utils.intelligent_scoping import analyze_question_scope
        SCOPING_AVAILABLE = True
        logger.info("[ENGINE-V2] IntelligentScoping loaded (alt path)")
    except ImportError:
        logger.warning("[ENGINE-V2] IntelligentScoping not available")

# Try to load ConsultativeSynthesizer
SYNTHESIS_AVAILABLE = False
ConsultativeSynthesizer = None
try:
    from backend.utils.consultative_synthesis import ConsultativeSynthesizer
    SYNTHESIS_AVAILABLE = True
    logger.info("[ENGINE-V2] ConsultativeSynthesizer loaded")
except ImportError:
    try:
        from utils.consultative_synthesis import ConsultativeSynthesizer
        SYNTHESIS_AVAILABLE = True
        logger.info("[ENGINE-V2] ConsultativeSynthesizer loaded (alt path)")
    except ImportError:
        logger.warning("[ENGINE-V2] ConsultativeSynthesizer not available")

# Try to load ComparisonEngine
COMPARISON_AVAILABLE = False
ComparisonEngine = None
try:
    from utils.features.comparison_engine import ComparisonEngine
    COMPARISON_AVAILABLE = True
    logger.info("[ENGINE-V2] ComparisonEngine loaded")
except ImportError:
    try:
        from backend.utils.features.comparison_engine import ComparisonEngine
        COMPARISON_AVAILABLE = True
        logger.info("[ENGINE-V2] ComparisonEngine loaded (alt path)")
    except ImportError:
        logger.warning("[ENGINE-V2] ComparisonEngine not available")

# Try to load ComplianceEngine
COMPLIANCE_ENGINE_AVAILABLE = False
run_compliance_check = None
try:
    from backend.utils.compliance_engine import run_compliance_check
    COMPLIANCE_ENGINE_AVAILABLE = True
    logger.info("[ENGINE-V2] ComplianceEngine loaded")
except ImportError:
    try:
        from utils.compliance_engine import run_compliance_check
        COMPLIANCE_ENGINE_AVAILABLE = True
        logger.info("[ENGINE-V2] ComplianceEngine loaded (alt path)")
    except ImportError:
        logger.warning("[ENGINE-V2] ComplianceEngine not available")


class IntelligenceEngineV2:
    """
    The brain of XLR8 - modular edition.
    
    Orchestrates the Five Truths:
    1. REALITY - What the data actually shows (DuckDB)
    2. INTENT - What the customer says they want (ChromaDB)
    3. CONFIGURATION - How they've configured the system (DuckDB)
    4. REFERENCE - Product docs, implementation standards (ChromaDB)
    5. REGULATORY - Laws, compliance requirements (ChromaDB)
    
    CRITICAL: ALL questions gather ALL truths. The synthesizer decides relevance.
    Validation questions ESPECIALLY need all truths to triangulate.
    
    Usage:
        engine = IntelligenceEngineV2("PROJECT123")
        engine.load_context(structured_handler=handler, schema=schema)
        answer = engine.ask("How many active employees?")
    """
    
    # Question patterns that indicate config/validation (not employee data)
    CONFIG_DOMAINS = [
        'workers comp', 'work comp', 'sui ', 'suta', 'futa', 'tax rate',
        'withholding', 'wc rate', 'workers compensation', 'local tax',
        'earnings', 'earning code', 'pay code', 'earning setup',
        'deduction', 'benefit plan', 'deduction setup', 'deductions',
        'gl', 'general ledger', 'gl mapping', 'account mapping',
        'tax jurisdiction', 'jurisdiction setup', 'state setup',
    ]
    
    VALIDATION_KEYWORDS = [
        'correct', 'valid', 'right', 'properly', 'configured',
        'issue', 'problem', 'check', 'verify', 'audit', 'review',
        'accurate', 'wrong', 'error', 'mistake', 'setup', 'setting'
    ]
    
    EMPLOYEE_INDICATORS = [
        'employee', 'worker', 'staff', 'personnel', 'headcount',
        'how many people', 'count of people', 'list of employees', 
        'terminated', 'active employee', 'hired', 'tenure'
    ]
    
    def __init__(self, project_name: str, project_id: str = None):
        """
        Initialize the engine.
        
        Args:
            project_name: Project code (e.g., "TEA1000")
            project_id: Project UUID for RAG filtering
        """
        self.project = project_name
        self.project_id = project_id
        
        # Data handlers
        self.structured_handler = None
        self.rag_handler = None
        self.schema: Dict = {}
        self.relationships: List = []
        
        # Filter state
        self.filter_candidates: Dict = {}
        self.confirmed_facts: Dict = {}
        
        # Components
        self.table_selector: Optional[TableSelector] = None
        self.sql_generator: Optional[SQLGenerator] = None
        self.synthesizer: Optional[Synthesizer] = None
        
        # Truth Gatherers
        self.reality_gatherer: Optional[RealityGatherer] = None
        self.intent_gatherer: Optional[IntentGatherer] = None
        self.configuration_gatherer: Optional[ConfigurationGatherer] = None
        self.reference_gatherer: Optional[ReferenceGatherer] = None
        self.regulatory_gatherer: Optional[RegulatoryGatherer] = None
        self.compliance_gatherer: Optional[ComplianceGatherer] = None
        
        # Truth Enricher (LLM Lookups)
        self.truth_enricher: Optional[TruthEnricher] = None
        
        # Pattern cache for learning
        self.pattern_cache = None
        
        # State tracking
        self.last_executed_sql: Optional[str] = None
        self.conversation_history: List[Dict] = []
        self._pending_clarification = None
        self._last_validation_export = None
        
        # Initialize LLM synthesizer
        self._llm_synthesizer = None
        if SYNTHESIS_AVAILABLE and ConsultativeSynthesizer:
            try:
                self._llm_synthesizer = ConsultativeSynthesizer(
                    ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
                    claude_api_key=os.getenv("CLAUDE_API_KEY"),
                    model_preference="auto"
                )
                logger.info("[ENGINE-V2] ConsultativeSynthesizer initialized")
            except Exception as e:
                logger.warning(f"[ENGINE-V2] ConsultativeSynthesizer init failed: {e}")
        
        logger.info(f"[ENGINE-V2] Initialized v{__version__} for project={project_name}")
    
    def load_context(
        self,
        structured_handler=None,
        rag_handler=None,
        schema: Dict = None,
        relationships: List = None,
        filter_candidates: Dict = None
    ):
        """
        Load context and initialize components.
        
        Args:
            structured_handler: DuckDB handler
            rag_handler: ChromaDB/RAG handler
            schema: Schema metadata (tables, columns)
            relationships: Detected table relationships
            filter_candidates: Filter candidate columns by category (optional, extracted from schema if not provided)
        """
        self.structured_handler = structured_handler
        self.rag_handler = rag_handler
        self.schema = schema or {}
        self.relationships = relationships or []
        
        # Extract filter candidates from schema if not provided explicitly
        self.filter_candidates = filter_candidates or self.schema.get('filter_candidates', {})
        if self.filter_candidates:
            logger.warning(f"[ENGINE-V2] Filter candidates loaded: {list(self.filter_candidates.keys())}")
        
        # Initialize pattern cache
        self._init_pattern_cache()
        
        # Initialize components
        self.table_selector = TableSelector(
            structured_handler=structured_handler,
            filter_candidates=self.filter_candidates,
            project=self.project  # Enable classification metadata loading
        )
        
        self.sql_generator = SQLGenerator(
            structured_handler=structured_handler,
            schema=self.schema,
            table_selector=self.table_selector,
            filter_candidates=self.filter_candidates,
            confirmed_facts=self.confirmed_facts,
            relationships=self.relationships
        )
        
        self.synthesizer = Synthesizer(
            llm_synthesizer=self._llm_synthesizer,
            confirmed_facts=self.confirmed_facts,
            filter_candidates=self.filter_candidates,
            schema=self.schema
        )
        
        self.reality_gatherer = RealityGatherer(
            project_name=self.project,
            project_id=self.project_id,
            structured_handler=structured_handler,
            schema=self.schema,
            sql_generator=self.sql_generator,
            pattern_cache=self.pattern_cache
        )
        
        # Intent gatherer (ChromaDB - customer documents)
        self.intent_gatherer = IntentGatherer(
            project_name=self.project,
            project_id=self.project_id,
            rag_handler=rag_handler
        )
        
        # Configuration gatherer (DuckDB - code tables)
        # Pass table_selector so it can use the same scoring logic
        self.configuration_gatherer = ConfigurationGatherer(
            project_name=self.project,
            project_id=self.project_id,
            structured_handler=structured_handler,
            schema=self.schema,
            table_selector=self.table_selector  # Use same selector for consistent scoring
        )
        
        # Global gatherers (Reference Library - no project filter)
        self.reference_gatherer = ReferenceGatherer(
            project_name=self.project,
            project_id=self.project_id,
            rag_handler=rag_handler
        )
        
        self.regulatory_gatherer = RegulatoryGatherer(
            project_name=self.project,
            project_id=self.project_id,
            rag_handler=rag_handler
        )
        
        self.compliance_gatherer = ComplianceGatherer(
            project_name=self.project,
            project_id=self.project_id,
            rag_handler=rag_handler
        )
        
        # Truth Enricher (LLM Lookups) - extracts structured data from raw truths
        self.truth_enricher = TruthEnricher(project_id=self.project_id)
        
        # v3.0: Log Context Graph availability
        context_graph_available = False
        if structured_handler and hasattr(structured_handler, 'get_context_graph'):
            try:
                graph = structured_handler.get_context_graph(self.project)
                hub_count = len(graph.get('hubs', []))
                rel_count = len(graph.get('relationships', []))
                if hub_count > 0 or rel_count > 0:
                    context_graph_available = True
                    logger.warning(f"[ENGINE-V2] Context Graph: {hub_count} hubs, {rel_count} relationships")
            except Exception as e:
                logger.debug(f"[ENGINE-V2] Context Graph not available: {e}")
        
        logger.info(f"[ENGINE-V2] Context loaded: {len(self.schema.get('tables', []))} tables, "
                   f"{len(self.filter_candidates)} filter categories, "
                   f"context_graph={'yes' if context_graph_available else 'no'}")
    
    def _init_pattern_cache(self):
        """Initialize SQL pattern cache for learning.
        
        NOTE: Pattern cache module was archived. This is a no-op stub.
        The pattern_cache remains None, which is handled gracefully by
        RealityGatherer (it checks `if self.pattern_cache` before use).
        """
        # Pattern cache feature removed - RealityGatherer handles None gracefully
        pass
    
    # =========================================================================
    # MAIN ENTRY POINT
    # =========================================================================
    
    def ask(self, question: str, mode: IntelligenceMode = None,
            context: Dict = None) -> SynthesizedAnswer:
        """
        Answer a question using ALL Five Truths.
        
        CRITICAL: Every question gathers from ALL truth types.
        The synthesizer decides what's relevant, not this method.
        
        This is the main entry point. It:
        1. Analyzes the question to detect mode and domains
        2. Handles clarification requests if needed
        3. Gathers from ALL Truth types (no skipping)
        4. Detects conflicts between truths
        5. Synthesizes a consultative response
        
        Args:
            question: The user's question
            mode: Optional explicit mode
            context: Optional additional context
            
        Returns:
            SynthesizedAnswer with full provenance
        """
        context = context or {}
        q_lower = question.lower()
        
        logger.warning(f"[ENGINE-V2] Question: {question[:80]}...")
        logger.warning(f"[ENGINE-V2] confirmed_facts: {self.confirmed_facts}")
        
        # Check for export request
        export_result = self._handle_export_request(question, q_lower)
        if export_result:
            return export_result
        
        # Analyze question
        mode = mode or self._detect_mode(q_lower)
        is_employee_question = self._is_employee_question(q_lower)
        is_validation = self._is_validation_question(q_lower)
        is_config = self._is_config_domain(q_lower)
        
        # Override employee detection for config/validation questions
        # Config questions (tax codes, earnings, deductions, GL) are NOT about employees
        if is_config:
            is_employee_question = False
            logger.warning("[ENGINE-V2] Config domain detected - skipping employee clarification")
        
        # Handle filter clarification for employee questions
        if is_employee_question:
            clarification = self._check_clarification_needed(question, q_lower)
            if clarification:
                return clarification
        
        logger.warning(f"[ENGINE-V2] Proceeding with mode={mode.value}, validation={is_validation}, config={is_config}")
        
        # =====================================================================
        # v4.0: INTELLIGENT SCOPING - The Consultant's First Move
        # Before answering, understand the data landscape
        # =====================================================================
        scope_filter = None
        
        # Check if scope was already provided via clarification
        if self.confirmed_facts.get('scope'):
            scope_value = self.confirmed_facts['scope']
            logger.warning(f"[ENGINE-V2] Scope already confirmed: {scope_value}")
            
            if scope_value != 'all':
                # Parse "dimension:value" format
                if ':' in scope_value:
                    dim, val = scope_value.split(':', 1)
                    scope_filter = {'dimension': dim, 'value': val}
                    logger.warning(f"[ENGINE-V2] Applying scope filter: {scope_filter}")
        
        # Only ask for scoping if not already answered
        elif SCOPING_AVAILABLE and self.structured_handler:
            # Check if this is a scope-sensitive question
            scope_sensitive = any([
                'list' in q_lower, 'show' in q_lower, 'all' in q_lower,
                'how many' in q_lower, 'count' in q_lower,
                is_config, is_validation
            ])
            
            if scope_sensitive:
                scope_analysis = analyze_question_scope(
                    self.project, 
                    question, 
                    self.structured_handler
                )
                
                if scope_analysis and scope_analysis.needs_clarification:
                    logger.warning(f"[ENGINE-V2] Scoping clarification needed: {len(scope_analysis.segments)} segments")
                    
                    # Build scope options from segments
                    scope_options = []
                    for seg in scope_analysis.segments:
                        scope_options.append({
                            'id': f"{seg.dimension}:{seg.value}",
                            'label': f"{seg.display_name} ({seg.employee_count:,} employees)"
                        })
                    scope_options.append({
                        'id': 'all',
                        'label': f"All ({scope_analysis.total_employees:,} employees) - export to Excel"
                    })
                    
                    # Return the intelligent scoping question as the response
                    return SynthesizedAnswer(
                        question=question,
                        answer=scope_analysis.suggested_question,
                        confidence=0.95,
                        structured_output={
                            'type': 'clarification_needed',  # Use same type as status clarification
                            'questions': [{
                                'id': 'scope',
                                'question': f"Which {scope_analysis.segments[0].dimension.replace('_code', '').replace('_', ' ')} should I focus on?",
                                'type': 'radio',
                                'options': scope_options
                            }],
                            'domain': scope_analysis.question_domain,
                            'total_employees': scope_analysis.total_employees,
                            'original_question': question
                        },
                        reasoning=[
                            f"Detected {scope_analysis.question_domain} domain",
                            f"Found {len(scope_analysis.segments)} meaningful segments",
                            f"Total {scope_analysis.total_employees:,} employees across segments",
                            "Asking for scope clarification before querying"
                        ]
                    )
                elif scope_analysis:
                    # Add scope info to analysis context
                    logger.warning(f"[ENGINE-V2] Scope analysis: {scope_analysis.question_domain}, "
                                  f"{scope_analysis.total_employees} employees")
        
        # =====================================================================
        # COMPARISON MODE - Use ComparisonEngine for table comparisons
        # =====================================================================
        if mode == IntelligenceMode.COMPARE and COMPARISON_AVAILABLE and self.structured_handler:
            comparison_result = self._handle_comparison(question, q_lower)
            if comparison_result:
                return comparison_result
        
        # Build analysis context
        analysis = {
            'mode': mode,
            'domains': self._detect_domains(q_lower),
            'is_employee_question': is_employee_question,
            'is_validation': is_validation,
            'is_config': is_config,
            'question': question,
            'q_lower': q_lower,
            'scope_filter': scope_filter  # v4.0: Pass scope filter for SQL generation
        }
        
        # v3.0: Detect entity scoping from Context Graph
        # If question mentions specific values (e.g., "company ABC"), scope queries
        entity_scope = self._detect_entity_scope(question, q_lower)
        if entity_scope:
            analysis['entity_scope'] = entity_scope
            logger.warning(f"[ENGINE-V2] Entity scope detected: {entity_scope}")
        
        # v4.0: Also use scope_filter as entity_scope if provided
        if scope_filter and not entity_scope:
            # Format for SQL generator: needs semantic_type, value, hub_column
            analysis['entity_scope'] = {
                'semantic_type': scope_filter['dimension'],  # e.g., 'company'
                'value': scope_filter['value'],              # e.g., 'TISI'
                'hub_column': scope_filter['dimension'],     # try direct column match too
                'scope_column': scope_filter['dimension']    # original column name
            }
            logger.warning(f"[ENGINE-V2] Using scope as entity filter: {analysis['entity_scope']}")
        
        # =====================================================================
        # GATHER ALL FIVE TRUTHS - NO SKIPPING
        # =====================================================================
        # CRITICAL: Every question needs all truths for proper triangulation.
        # Validation questions ESPECIALLY need Regulatory + Reference to verify
        # whether Reality matches what SHOULD be configured.
        # =====================================================================
        
        # Truth 1: REALITY - What the data shows
        reality = self._gather_reality(question, analysis)
        logger.warning(f"[ENGINE-V2] REALITY gathered: {len(reality)} truths")
        
        # Check for pending clarification from reality gathering
        if context.get('pending_clarification') or self._pending_clarification:
            clarification = context.get('pending_clarification') or self._pending_clarification
            self._pending_clarification = None
            return clarification
        
        # Truth 2: INTENT - What customer wants (SOWs, requirements)
        intent = self._gather_intent(question, analysis)
        logger.warning(f"[ENGINE-V2] INTENT gathered: {len(intent)} truths")
        
        # Truth 3: CONFIGURATION - How system is configured (code tables)
        configuration = self._gather_configuration(question, analysis)
        logger.warning(f"[ENGINE-V2] CONFIGURATION gathered: {len(configuration)} truths")
        
        # Truths 4, 5, 6: REFERENCE, REGULATORY, COMPLIANCE (global library)
        reference, regulatory, compliance = self._gather_reference_library(question, analysis)
        logger.warning(f"[ENGINE-V2] REFERENCE gathered: {len(reference)} truths")
        logger.warning(f"[ENGINE-V2] REGULATORY gathered: {len(regulatory)} truths")
        logger.warning(f"[ENGINE-V2] COMPLIANCE gathered: {len(compliance)} truths")
        
        # Log total truths gathered
        total_truths = len(reality) + len(intent) + len(configuration) + len(reference) + len(regulatory) + len(compliance)
        logger.warning(f"[ENGINE-V2] TOTAL TRUTHS GATHERED: {total_truths}")
        
        # Enrich semantic truths with LLM extraction (LLM Lookups)
        if self.truth_enricher:
            intent = self.truth_enricher.enrich_batch(intent)
            reference = self.truth_enricher.enrich_batch(reference)
            regulatory = self.truth_enricher.enrich_batch(regulatory)
            compliance = self.truth_enricher.enrich_batch(compliance)
            # Configuration is DuckDB (structured), light enrichment
            configuration = self.truth_enricher.enrich_batch(configuration)
        
        # Detect conflicts between truths
        conflicts = self._detect_conflicts(
            reality, intent, configuration, reference, regulatory, compliance
        )
        
        # Run proactive checks
        insights = self._run_proactive_checks(analysis)
        
        # Compliance check
        compliance_check = None
        if regulatory:
            compliance_check = self._check_compliance(reality, configuration, regulatory)
        
        # v3.0: Get Context Graph for synthesis
        context_graph = None
        if self.table_selector and hasattr(self.table_selector, '_get_context_graph'):
            try:
                context_graph = self.table_selector._get_context_graph()
            except Exception as e:
                logger.debug(f"[ENGINE-V2] Could not get context graph: {e}")
        
        # v3.2: Get entity gaps from Entity Registry (configured but not in docs, or vice versa)
        entity_gaps = []
        try:
            from backend.utils.entity_registry import get_entity_registry
            registry = get_entity_registry()
            if registry:
                entity_gaps = registry.get_gaps() or []
                if entity_gaps:
                    logger.warning(f"[ENGINE-V2] Found {len(entity_gaps)} entity gaps for gap detection")
        except Exception as e:
            logger.debug(f"[ENGINE-V2] Could not get entity gaps: {e}")
        
        # Merge analysis flags into context for synthesizer
        synth_context = context.copy() if context else {}
        synth_context['is_config'] = analysis.get('is_config', False)
        synth_context['is_validation'] = analysis.get('is_validation', False)
        synth_context['is_employee_question'] = analysis.get('is_employee_question', False)
        synth_context['entity_gaps'] = entity_gaps  # v3.2: Pass gaps for synthesis
        
        # Synthesize answer
        answer = self.synthesizer.synthesize(
            question=question,
            mode=mode,
            reality=reality,
            intent=intent,
            configuration=configuration,
            reference=reference,
            regulatory=regulatory,
            compliance=compliance,
            conflicts=conflicts,
            insights=insights,
            compliance_check=compliance_check,
            context=synth_context,
            context_graph=context_graph  # v3.0
        )
        
        # Track SQL
        if self.reality_gatherer:
            self.last_executed_sql = self.reality_gatherer.last_executed_sql
            answer.executed_sql = self.last_executed_sql
        
        # v3.2: Attach consultative metadata (excel_spec, proactive_offers, etc.)
        if self.synthesizer and hasattr(self.synthesizer, 'get_consultative_metadata'):
            consultative_meta = self.synthesizer.get_consultative_metadata()
            if consultative_meta:
                answer.consultative_metadata = consultative_meta
                logger.warning(f"[ENGINE-V2] Consultative metadata: type={consultative_meta.get('question_type')}, "
                             f"offers={len(consultative_meta.get('proactive_offers', []))}")
        
        # Update history
        self.conversation_history.append({
            'question': question,
            'mode': mode.value if mode else 'search',
            'answer_length': len(answer.answer),
            'confidence': answer.confidence,
            'truths_gathered': {
                'reality': len(reality),
                'intent': len(intent),
                'configuration': len(configuration),
                'reference': len(reference),
                'regulatory': len(regulatory),
                'compliance': len(compliance)
            }
        })
        
        total_truths = len(reality) + len(intent) + len(configuration) + len(reference) + len(regulatory) + len(compliance)
        logger.info(f"[ENGINE-V2] Answer: {len(answer.answer)} chars, "
                   f"confidence={answer.confidence:.0%}, truths={total_truths}")
        
        return answer
    
    # =========================================================================
    # QUESTION ANALYSIS
    # =========================================================================
    
    def _detect_mode(self, q_lower: str) -> IntelligenceMode:
        """Detect intelligence mode from question."""
        if any(w in q_lower for w in ['correct', 'valid', 'check', 'verify', 'audit']):
            return IntelligenceMode.VALIDATE
        if any(w in q_lower for w in ['compare', 'versus', 'vs', 'difference']):
            return IntelligenceMode.COMPARE
        if any(w in q_lower for w in ['how to', 'configure', 'setup', 'set up']):
            return IntelligenceMode.CONFIGURE
        if any(w in q_lower for w in ['report', 'summary', 'overview']):
            return IntelligenceMode.REPORT
        if any(w in q_lower for w in ['count', 'how many', 'total', 'sum']):
            return IntelligenceMode.ANALYZE
        return IntelligenceMode.SEARCH
    
    def _detect_domains(self, q_lower: str) -> List[str]:
        """Detect relevant domains from question."""
        domains = []
        
        domain_keywords = {
            'payroll': ['payroll', 'pay', 'wage', 'salary', 'compensation'],
            'tax': ['tax', 'sui', 'suta', 'futa', 'withholding', 'w2', 'fica'],
            'benefits': ['benefit', 'deduction', '401k', 'insurance', 'health'],
            'time': ['time', 'hours', 'attendance', 'schedule', 'pto'],
            'hr': ['employee', 'hire', 'termination', 'job', 'position'],
            'gl': ['gl', 'general ledger', 'account', 'mapping'],
            'earnings': ['earnings', 'earning', 'pay code'],
        }
        
        for domain, keywords in domain_keywords.items():
            if any(kw in q_lower for kw in keywords):
                domains.append(domain)
        
        return domains or ['general']
    
    def _is_employee_question(self, q_lower: str) -> bool:
        """Check if question is about employee data."""
        return any(ind in q_lower for ind in self.EMPLOYEE_INDICATORS)
    
    def _is_validation_question(self, q_lower: str) -> bool:
        """Check if question is a validation/audit question."""
        return any(kw in q_lower for kw in self.VALIDATION_KEYWORDS)
    
    def _is_config_domain(self, q_lower: str) -> bool:
        """Check if question is about config (not employee data)."""
        return any(cd in q_lower for cd in self.CONFIG_DOMAINS)
    
    def _detect_entity_scope(self, question: str, q_lower: str) -> Optional[Dict]:
        """
        Detect if question references specific entity values for scoping.
        
        Uses Context Graph to find hub values mentioned in the question.
        Returns scoping info that gatherers can use to filter queries.
        
        Example: "Show employees in company ABC" → scope to company_code='ABC'
        
        Returns:
            Dict with {semantic_type, value, hub_table, hub_column} or None
        """
        if not self.structured_handler or not self.table_selector:
            return None
        
        try:
            # Get Context Graph
            graph = self.table_selector._get_context_graph()
            if not graph or not graph.get('hubs'):
                return None
            
            # For each hub, check if any of its values appear in the question
            for hub in graph.get('hubs', []):
                hub_table = hub.get('table', '')
                hub_column = hub.get('column', '')
                semantic_type = hub.get('semantic_type', '')
                
                if not hub_table or not hub_column:
                    continue
                
                # Get distinct values from this hub
                try:
                    values = self.structured_handler.conn.execute(f"""
                        SELECT DISTINCT "{hub_column}" 
                        FROM "{hub_table}" 
                        WHERE "{hub_column}" IS NOT NULL
                        LIMIT 100
                    """).fetchall()
                    
                    for (val,) in values:
                        if not val:
                            continue
                        val_str = str(val).lower()
                        val_upper = str(val).upper()
                        
                        # Check if value appears in question (case-insensitive)
                        # Must be a "word" - not substring of another word
                        import re
                        if len(val_str) >= 2:  # Skip single chars
                            # Match as word boundary
                            pattern = rf'\b{re.escape(val_str)}\b'
                            if re.search(pattern, q_lower):
                                logger.warning(f"[ENGINE-V2] Found entity scope: {semantic_type}={val}")
                                return {
                                    'semantic_type': semantic_type,
                                    'value': str(val),  # Original case
                                    'hub_table': hub_table,
                                    'hub_column': hub_column
                                }
                except Exception as e:
                    logger.debug(f"[ENGINE-V2] Could not check hub {hub_table}: {e}")
                    continue
                    
        except Exception as e:
            logger.debug(f"[ENGINE-V2] Entity scope detection failed: {e}")
        
        return None
    
    # =========================================================================
    # CLARIFICATION HANDLING
    # =========================================================================
    
    def _check_clarification_needed(self, question: str, 
                                    q_lower: str) -> Optional[SynthesizedAnswer]:
        """Check if clarification is needed for employee questions."""
        # Status is the most important filter
        if 'status' not in self.confirmed_facts:
            if 'status' in self.filter_candidates:
                return self._build_status_clarification(question)
        
        return None
    
    def _build_status_clarification(self, question: str) -> SynthesizedAnswer:
        """Build status clarification request."""
        options = [
            {'id': 'active', 'label': 'Active employees only'},
            {'id': 'termed', 'label': 'Terminated employees only'},
            {'id': 'all', 'label': 'All employees (active + terminated)'}
        ]
        
        return SynthesizedAnswer(
            question=question,
            answer="",
            confidence=0.0,
            structured_output={
                'type': 'clarification_needed',
                'questions': [{
                    'id': 'status',
                    'question': 'Which employees would you like to include?',
                    'type': 'radio',
                    'options': options
                }],
                'original_question': question
            },
            reasoning=['Need to clarify employee status filter']
        )
    
    def _handle_comparison(self, question: str, q_lower: str) -> Optional[SynthesizedAnswer]:
        """
        Handle comparison queries using the ComparisonEngine.
        
        Uses TableSelector to find the best matching tables for each reference,
        leveraging all the classification/domain intelligence we built.
        """
        logger.warning(f"[ENGINE-V2] Handling comparison query: {question[:60]}...")
        
        if not self.schema or not self.schema.get('tables'):
            logger.warning("[ENGINE-V2] No schema available for comparison")
            return None
        
        # Parse question to extract the two table references
        ref_a, ref_b = self._extract_comparison_references(q_lower)
        
        if not ref_a or not ref_b:
            logger.warning(f"[ENGINE-V2] Could not extract two table references from query")
            return None
        
        logger.warning(f"[ENGINE-V2] Extracted references: A='{ref_a}', B='{ref_b}'")
        
        # Use TableSelector to find best match for EACH reference
        # This uses all our classification intelligence (domain, truth_type, etc.)
        tables = self.schema.get('tables', [])
        
        # Find best table for reference A
        table_a = self._find_table_for_reference(ref_a, tables, exclude=None)
        if not table_a:
            logger.warning(f"[ENGINE-V2] No table found for reference A: {ref_a}")
            return None
        
        # Find best table for reference B (excluding table A)
        table_b = self._find_table_for_reference(ref_b, tables, exclude=table_a)
        if not table_b:
            logger.warning(f"[ENGINE-V2] No table found for reference B: {ref_b}")
            return None
        
        if table_a == table_b:
            logger.warning(f"[ENGINE-V2] Both references matched same table: {table_a}")
            return None
        
        logger.warning(f"[ENGINE-V2] Comparing: {table_a} vs {table_b}")
        
        try:
            # Run comparison
            engine = ComparisonEngine(structured_handler=self.structured_handler)
            result = engine.compare(
                table_a=table_a,
                table_b=table_b,
                project_id=self.project_id
            )
            
            # Format consultative response
            answer = self._format_comparison_result(result, question)
            
            return SynthesizedAnswer(
                question=question,
                answer=answer,
                confidence=0.92,
                structured_output={
                    'type': 'comparison',
                    'result': result.to_dict()
                },
                reasoning=[
                    f"Compared {result.source_a_rows} rows from {table_a}",
                    f"Compared {result.source_b_rows} rows from {table_b}",
                    f"Found {result.matches} matches, {len(result.only_in_a)} only in A, {len(result.only_in_b)} only in B"
                ]
            )
            
        except Exception as e:
            logger.error(f"[ENGINE-V2] Comparison failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _extract_comparison_references(self, q_lower: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract the two table references from a comparison question.
        
        Returns the raw reference strings, NOT table names.
        e.g., "Company Tax Verification" and "Company Master Profile"
        """
        # Patterns to extract the two things being compared
        patterns = [
            # "compare X to Y and tell me..."
            r'compare\s+(?:the\s+)?(?:tax\s+codes\s+in\s+)?(.+?)\s+to\s+(.+?)(?:\s+and\s+tell|\s+and\s+show|\s*$)',
            # "compare X with Y"
            r'compare\s+(.+?)\s+(?:with|vs|versus)\s+(.+?)(?:\s+and|\s*$)',
            # "X compared to Y"
            r'(.+?)\s+compared\s+to\s+(.+?)(?:\s+and|\s*$)',
            # "difference between X and Y"
            r'difference\s+between\s+(.+?)\s+and\s+(.+?)(?:\s*$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, q_lower)
            if match:
                ref_a = match.group(1).strip()
                ref_b = match.group(2).strip()
                
                # Clean up common prefixes
                for prefix in ['the ', 'my ', 'our ']:
                    if ref_a.startswith(prefix):
                        ref_a = ref_a[len(prefix):]
                    if ref_b.startswith(prefix):
                        ref_b = ref_b[len(prefix):]
                
                if ref_a and ref_b:
                    return ref_a, ref_b
        
        return None, None
    
    def _find_table_for_reference(self, reference: str, tables: List[Dict], 
                                   exclude: str = None) -> Optional[str]:
        """
        Find the best matching table for a reference string.
        
        Uses TableSelector with the reference as the "question" to leverage
        all our classification intelligence.
        """
        # Filter out excluded table
        if exclude:
            tables = [t for t in tables if t.get('table_name') != exclude]
        
        if not tables:
            return None
        
        # Use TableSelector to score tables against this reference
        selector = TableSelector(
            structured_handler=self.structured_handler,
            filter_candidates=self.filter_candidates,
            project=self.project_id
        )
        
        # Select best matches for this reference
        matches = selector.select(tables, reference, max_tables=3)
        
        if matches:
            best_match = matches[0].get('table_name')
            logger.warning(f"[ENGINE-V2] Reference '{reference[:30]}' -> {best_match}")
            return best_match
        
        return None
    
    def _format_comparison_result(self, result, question: str) -> str:
        """Format comparison result as consultative answer."""
        parts = []
        
        # Summary
        parts.append(f"## Comparison: {result.source_a} vs {result.source_b}\n")
        
        # Key metrics
        parts.append(f"**Match Rate:** {result.match_rate:.1%}")
        parts.append(f"- **Matched:** {result.matches} records")
        parts.append(f"- **Only in {result.source_a}:** {len(result.only_in_a)} records")
        parts.append(f"- **Only in {result.source_b}:** {len(result.only_in_b)} records")
        
        if result.mismatches:
            parts.append(f"- **Value Mismatches:** {len(result.mismatches)} records")
        
        # Show what's missing
        if result.only_in_a:
            parts.append(f"\n### Missing from {result.source_b}:")
            # Get key column values
            key_col = result.join_keys[0] if result.join_keys else None
            if key_col:
                missing_values = [str(r.get(key_col, ''))[:30] for r in result.only_in_a[:10]]
                for val in missing_values:
                    parts.append(f"- `{val}`")
                if len(result.only_in_a) > 10:
                    parts.append(f"- *...and {len(result.only_in_a) - 10} more*")
        
        if result.only_in_b:
            parts.append(f"\n### Missing from {result.source_a}:")
            key_col = result.join_keys[0] if result.join_keys else None
            if key_col:
                missing_values = [str(r.get(key_col, ''))[:30] for r in result.only_in_b[:10]]
                for val in missing_values:
                    parts.append(f"- `{val}`")
                if len(result.only_in_b) > 10:
                    parts.append(f"- *...and {len(result.only_in_b) - 10} more*")
        
        # Mismatches
        if result.mismatches:
            parts.append(f"\n### Value Differences:")
            for mismatch in result.mismatches[:5]:
                keys = mismatch.get('keys', {})
                key_str = ", ".join([f"{k}={v}" for k, v in keys.items()])
                parts.append(f"- **{key_str}**:")
                for diff in mismatch.get('differences', [])[:3]:
                    parts.append(f"  - {diff['column']}: `{diff['value_a']}` → `{diff['value_b']}`")
        
        # Recommendation
        parts.append("\n### Recommendation:")
        if result.match_rate >= 0.95:
            parts.append("✅ **High alignment** - Only minor discrepancies to review.")
        elif result.match_rate >= 0.7:
            parts.append("⚠️ **Moderate alignment** - Review the gaps above to ensure data consistency.")
        else:
            parts.append("🔴 **Low alignment** - Significant discrepancies require immediate attention.")
        
        return "\n".join(parts)
    
    def _handle_export_request(self, question: str, 
                               q_lower: str) -> Optional[SynthesizedAnswer]:
        """Handle export/download requests."""
        export_keywords = ['export', 'download', 'excel', 'csv', 'spreadsheet']
        is_export = any(kw in q_lower for kw in export_keywords)
        
        if is_export and self._last_validation_export:
            export_data = self._last_validation_export
            return SynthesizedAnswer(
                question=question,
                answer=f"📥 **Export Ready**\n\n{export_data['total_records']} records prepared.",
                confidence=0.95,
                structured_output={
                    'type': 'export_ready',
                    'export_data': export_data
                },
                reasoning=['Export requested']
            )
        
        return None
    
    # =========================================================================
    # TRUTH GATHERING
    # =========================================================================
    
    def _gather_reality(self, question: str, analysis: Dict) -> List[Truth]:
        """Gather Reality truths from DuckDB."""
        if not self.reality_gatherer:
            return []
        
        truths = self.reality_gatherer.gather(question, analysis)
        
        # Check for pending clarification
        if analysis.get('pending_clarification'):
            self._pending_clarification = analysis['pending_clarification']
        
        return truths
    
    def _gather_intent(self, question: str, analysis: Dict) -> List[Truth]:
        """Gather Intent truths from customer documents."""
        if self.intent_gatherer:
            return self.intent_gatherer.gather(question, analysis)
        return []
    
    def _gather_configuration(self, question: str, analysis: Dict) -> List[Truth]:
        """
        Gather Configuration truths from config tables.
        
        NOTE: Configuration uses DuckDB (code tables, mappings), NOT ChromaDB.
        This was a bug in the previous implementation that searched ChromaDB.
        """
        if self.configuration_gatherer:
            return self.configuration_gatherer.gather(question, analysis)
        return []
    
    def _gather_reference_library(self, question: str, 
                                  analysis: Dict) -> Tuple[List[Truth], List[Truth], List[Truth]]:
        """
        Gather Reference Library truths (global scope).
        
        Returns:
            Tuple of (reference, regulatory, compliance) Truth lists
            
        These are GLOBAL - they apply to all projects and are not filtered by project_id.
        """
        reference = []
        regulatory = []
        compliance = []
        
        # Gather from each global truth type
        if self.reference_gatherer:
            reference = self.reference_gatherer.gather(question, analysis)
            
        if self.regulatory_gatherer:
            regulatory = self.regulatory_gatherer.gather(question, analysis)
            
        if self.compliance_gatherer:
            compliance = self.compliance_gatherer.gather(question, analysis)
        
        return reference, regulatory, compliance
    
    # =========================================================================
    # ANALYSIS
    # =========================================================================
    
    def _detect_conflicts(self, reality, intent, configuration,
                         reference, regulatory, compliance) -> List[Conflict]:
        """
        Detect conflicts between truths.
        
        Looks for discrepancies where different truth sources disagree:
        - Reality vs Configuration (data doesn't match setup)
        - Reality vs Regulatory (data violates rules)
        - Configuration vs Reference (setup doesn't match best practice)
        - Intent vs Reality (what they want vs what they have)
        """
        conflicts = []
        
        try:
            # Reality vs Regulatory conflicts
            for reg_truth in regulatory:
                for real_truth in reality:
                    # Check if regulatory requirement mentions something reality contradicts
                    reg_content = reg_truth.content.lower() if reg_truth.content else ""
                    real_content = real_truth.content.lower() if real_truth.content else ""
                    
                    # Look for value mismatches (e.g., "rate must be X" vs "rate is Y")
                    if any(kw in reg_content for kw in ['must be', 'required', 'shall not exceed', 'minimum']):
                        if any(kw in real_content for kw in ['currently', 'actual', 'found', 'shows']):
                            conflicts.append(Conflict(
                                truth_a=reg_truth,
                                truth_b=real_truth,
                                conflict_type="regulatory_violation",
                                description=f"Potential compliance gap: {reg_truth.summary[:100]} vs {real_truth.summary[:100]}",
                                severity="medium"
                            ))
            
            # Configuration vs Reference conflicts  
            for ref_truth in reference:
                for config_truth in configuration:
                    ref_content = ref_truth.content.lower() if ref_truth.content else ""
                    config_content = config_truth.content.lower() if config_truth.content else ""
                    
                    # Look for setup that doesn't match best practice
                    if any(kw in ref_content for kw in ['best practice', 'recommended', 'should be configured']):
                        if config_content and 'configured' in config_content:
                            conflicts.append(Conflict(
                                truth_a=ref_truth,
                                truth_b=config_truth,
                                conflict_type="best_practice_deviation",
                                description=f"Configuration may deviate from best practice",
                                severity="low"
                            ))
            
            # Intent vs Reality conflicts
            for intent_truth in intent:
                for real_truth in reality:
                    intent_content = intent_truth.content.lower() if intent_truth.content else ""
                    real_content = real_truth.content.lower() if real_truth.content else ""
                    
                    # Look for gaps between what they want and what they have
                    if any(kw in intent_content for kw in ['want', 'need', 'require', 'goal']):
                        if any(kw in real_content for kw in ['currently', 'actual', 'no ', 'not ']):
                            conflicts.append(Conflict(
                                truth_a=intent_truth,
                                truth_b=real_truth,
                                conflict_type="intent_gap",
                                description=f"Gap between intent and reality",
                                severity="medium"
                            ))
            
            if conflicts:
                logger.info(f"[ENGINE-V2] Detected {len(conflicts)} conflicts")
                
        except Exception as e:
            logger.warning(f"[ENGINE-V2] Conflict detection error: {e}")
        
        return conflicts
    
    def _run_proactive_checks(self, analysis: Dict) -> List[Insight]:
        """
        Run proactive analysis checks.
        
        Automatically flags potential issues without user asking:
        - Missing required configurations
        - Unusual data patterns
        - Approaching compliance deadlines
        """
        insights = []
        
        try:
            # If we have compliance results, surface them as insights
            if COMPLIANCE_ENGINE_AVAILABLE and self.project_id:
                compliance_result = self._check_compliance([], [], [])
                if compliance_result and compliance_result.get('findings'):
                    for finding in compliance_result['findings'][:3]:  # Top 3
                        insights.append(Insight(
                            insight_type="compliance_finding",
                            description=finding.get('description', 'Compliance issue detected'),
                            severity=finding.get('severity', 'medium'),
                            source="compliance_engine",
                            recommendation=finding.get('recommendation', 'Review and remediate')
                        ))
            
            if insights:
                logger.info(f"[ENGINE-V2] Generated {len(insights)} proactive insights")
                
        except Exception as e:
            logger.warning(f"[ENGINE-V2] Proactive check error: {e}")
        
        return insights
    
    def _check_compliance(self, reality, configuration,
                         regulatory) -> Optional[Dict]:
        """
        Check compliance against regulatory rules.
        
        Calls the ComplianceEngine to run rule-based checks against
        the project's data and configuration.
        """
        if not COMPLIANCE_ENGINE_AVAILABLE:
            logger.debug("[ENGINE-V2] ComplianceEngine not available")
            return None
        
        if not self.project_id:
            logger.debug("[ENGINE-V2] No project_id for compliance check")
            return None
        
        try:
            result = run_compliance_check(
                project_id=self.project_id,
                db_handler=self.structured_handler
            )
            
            if result:
                finding_count = len(result.get('findings', []))
                logger.info(f"[ENGINE-V2] Compliance check complete: {finding_count} findings")
                
            return result
            
        except Exception as e:
            logger.warning(f"[ENGINE-V2] Compliance check error: {e}")
            return None
    
    # =========================================================================
    # FILTER MANAGEMENT
    # =========================================================================
    
    def confirm_filter(self, category: str, value: str):
        """Confirm a filter selection."""
        self.confirmed_facts[category] = value
        if self.sql_generator:
            self.sql_generator.confirmed_facts = self.confirmed_facts
        logger.info(f"[ENGINE-V2] Confirmed: {category}={value}")
    
    def clear_filters(self):
        """Clear all confirmed filters."""
        self.confirmed_facts = {}
        if self.sql_generator:
            self.sql_generator.confirmed_facts = {}
        logger.info("[ENGINE-V2] Filters cleared")
    
    def get_filter_options(self, category: str) -> List[Dict]:
        """Get available options for a filter category."""
        if category not in self.filter_candidates:
            return []
        
        candidates = self.filter_candidates[category]
        if not candidates:
            return []
        
        # Return unique values from first candidate
        best = candidates[0]
        values = best.get('value_distribution', {})
        return [{'id': v, 'label': v, 'count': c} for v, c in values.items()]
