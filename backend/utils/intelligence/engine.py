"""
XLR8 Intelligence Engine v2 - Main Orchestrator
================================================

The brain of XLR8. Thin orchestrator that coordinates:
- Question analysis and mode detection
- Clarification handling (employee status, filters)
- Truth gathering (Reality, Intent, Configuration, Reference, Regulatory)
- Conflict detection
- Response synthesis

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

__version__ = "6.2.0"  # FIXED: Gather ALL Five Truths for ALL questions (no more validation skip)

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
        'how many', 'count of', 'list of', 'show me', 'who',
        'terminated', 'active', 'hired', 'tenure'
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
        
        logger.info(f"[ENGINE-V2] Context loaded: {len(self.schema.get('tables', []))} tables, "
                   f"{len(self.filter_candidates)} filter categories")
    
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
        if is_validation and is_config:
            is_employee_question = False
            logger.warning("[ENGINE-V2] Config validation - skipping employee clarification")
        
        # Handle filter clarification for employee questions
        if is_employee_question:
            clarification = self._check_clarification_needed(question, q_lower)
            if clarification:
                return clarification
        
        logger.warning(f"[ENGINE-V2] Proceeding with mode={mode.value}, validation={is_validation}, config={is_config}")
        
        # Build analysis context
        analysis = {
            'mode': mode,
            'domains': self._detect_domains(q_lower),
            'is_employee_question': is_employee_question,
            'is_validation': is_validation,
            'is_config': is_config,
            'question': question,
            'q_lower': q_lower
        }
        
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
            context=context
        )
        
        # Track SQL
        if self.reality_gatherer:
            self.last_executed_sql = self.reality_gatherer.last_executed_sql
            answer.executed_sql = self.last_executed_sql
        
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
        """Detect conflicts between truths."""
        conflicts = []
        # TODO: Implement conflict detection
        return conflicts
    
    def _run_proactive_checks(self, analysis: Dict) -> List[Insight]:
        """Run proactive analysis checks."""
        insights = []
        # TODO: Implement proactive checks
        return insights
    
    def _check_compliance(self, reality, configuration,
                         regulatory) -> Optional[Dict]:
        """Check compliance against regulatory rules."""
        # TODO: Implement compliance checking
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
