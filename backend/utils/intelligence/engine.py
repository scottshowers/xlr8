"""
XLR8 Intelligence Engine - Main Orchestrator
=============================================

The brain of XLR8. This is the thin orchestrator that coordinates:
- Table selection
- SQL generation
- Truth gathering (Reality, Intent, Configuration, Reference, Regulatory)
- Response synthesis

This is the NEW modular engine. It uses the refactored components:
- TableSelector for smart table selection
- SQLGenerator for LLM-based SQL generation
- Gatherers for each Truth type
- Synthesizer for response generation

Deploy to: backend/utils/intelligence/engine.py
"""

import logging
from typing import Dict, List, Optional, Any

from .types import (
    Truth, Conflict, Insight, SynthesizedAnswer, IntelligenceMode,
    TruthType, TRUTH_ROUTING
)
from .table_selector import TableSelector
from .sql_generator import SQLGenerator
from .synthesizer import Synthesizer
from .gatherers import RealityGatherer

logger = logging.getLogger(__name__)

# Version
__version__ = "6.0.0"


class IntelligenceEngineV2:
    """
    The brain of XLR8 - modular edition.
    
    This is a thin orchestrator that coordinates the Five Truths:
    1. REALITY - What the data actually shows (DuckDB)
    2. INTENT - What the customer says they want (ChromaDB)
    3. CONFIGURATION - How they've configured the system (DuckDB)
    4. REFERENCE - Product docs, implementation standards (ChromaDB)
    5. REGULATORY - Laws, compliance requirements (ChromaDB)
    
    Each Truth has its own gatherer. The engine:
    1. Analyzes the question
    2. Selects relevant tables
    3. Gathers from each Truth type
    4. Synthesizes a consultative response
    
    Usage:
        engine = IntelligenceEngineV2("PROJECT123")
        engine.load_context(structured_handler=handler, schema=schema)
        answer = engine.ask("How many active employees?")
    """
    
    def __init__(self, project_name: str, project_id: str = None):
        """
        Initialize the engine.
        
        Args:
            project_name: Project code (e.g., "TEA1000")
            project_id: Project UUID for RAG filtering
        """
        self.project = project_name
        self.project_id = project_id
        
        # Data handlers (set via load_context)
        self.structured_handler = None
        self.rag_handler = None
        self.schema: Dict = {}
        self.relationships: List = []
        
        # Filter state
        self.filter_candidates: Dict = {}
        self.confirmed_facts: Dict = {}
        
        # Components (initialized in load_context)
        self.table_selector: Optional[TableSelector] = None
        self.sql_generator: Optional[SQLGenerator] = None
        self.synthesizer: Optional[Synthesizer] = None
        
        # Gatherers
        self.reality_gatherer: Optional[RealityGatherer] = None
        
        # State tracking
        self.last_executed_sql: Optional[str] = None
        
        logger.info(f"[ENGINE-V2] Initialized for project={project_name}")
    
    def load_context(
        self,
        structured_handler=None,
        rag_handler=None,
        schema: Dict = None,
        relationships: List = None,
        filter_candidates: Dict = None
    ):
        """
        Load context for the engine.
        
        Args:
            structured_handler: DuckDB handler
            rag_handler: ChromaDB/RAG handler
            schema: Schema metadata (tables, columns)
            relationships: Detected table relationships
            filter_candidates: Filter candidate columns
        """
        self.structured_handler = structured_handler
        self.rag_handler = rag_handler
        self.schema = schema or {}
        self.relationships = relationships or []
        self.filter_candidates = filter_candidates or {}
        
        # Initialize components
        self.table_selector = TableSelector(
            structured_handler=structured_handler,
            filter_candidates=self.filter_candidates
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
            confirmed_facts=self.confirmed_facts,
            filter_candidates=self.filter_candidates,
            schema=self.schema
        )
        
        # Initialize gatherers
        self.reality_gatherer = RealityGatherer(
            project_name=self.project,
            project_id=self.project_id,
            structured_handler=structured_handler,
            schema=self.schema,
            sql_generator=self.sql_generator
        )
        
        logger.info(f"[ENGINE-V2] Context loaded: {len(self.schema.get('tables', []))} tables")
    
    def ask(self, question: str, context: Dict = None) -> SynthesizedAnswer:
        """
        Answer a question using all Five Truths.
        
        This is the main entry point. It:
        1. Analyzes the question to detect mode and domains
        2. Gathers from each relevant Truth type
        3. Detects conflicts between truths
        4. Synthesizes a consultative response
        
        Args:
            question: The user's question
            context: Optional additional context (clarification answers, etc.)
            
        Returns:
            SynthesizedAnswer with full provenance
        """
        context = context or {}
        q_lower = question.lower()
        
        logger.warning(f"[ENGINE-V2] Processing: {question[:60]}...")
        
        # Merge any clarification answers into confirmed_facts
        if context.get('clarification_answers'):
            self.confirmed_facts.update(context['clarification_answers'])
            self.sql_generator.confirmed_facts = self.confirmed_facts
        
        # Analyze question
        mode = self._detect_mode(q_lower)
        domains = self._detect_domains(q_lower)
        
        analysis = {
            'mode': mode,
            'domains': domains,
            'question': question,
            'q_lower': q_lower
        }
        
        # Gather from each Truth type
        reality = self._gather_reality(question, analysis)
        intent = self._gather_intent(question, analysis)
        configuration = self._gather_configuration(question, analysis)
        reference, regulatory, compliance = self._gather_reference_library(question, analysis)
        
        # Detect conflicts
        conflicts = self._detect_conflicts(
            reality, intent, configuration, reference, regulatory, compliance
        )
        
        # Run proactive checks
        insights = self._run_proactive_checks(analysis)
        
        # Check compliance
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
        
        logger.info(f"[ENGINE-V2] Answer generated: {len(answer.answer)} chars, "
                   f"confidence={answer.confidence:.0%}")
        
        return answer
    
    # =========================================================================
    # ANALYSIS METHODS
    # =========================================================================
    
    def _detect_mode(self, q_lower: str) -> IntelligenceMode:
        """Detect the intelligence mode from the question."""
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
        """Detect relevant domains from the question."""
        domains = []
        
        domain_keywords = {
            'payroll': ['payroll', 'pay', 'wage', 'salary', 'compensation'],
            'tax': ['tax', 'sui', 'suta', 'futa', 'withholding', 'w2', 'fica'],
            'benefits': ['benefit', 'deduction', '401k', 'insurance', 'health'],
            'time': ['time', 'hours', 'attendance', 'schedule', 'pto'],
            'hr': ['employee', 'hire', 'termination', 'job', 'position'],
            'gl': ['gl', 'general ledger', 'account', 'mapping'],
        }
        
        for domain, keywords in domain_keywords.items():
            if any(kw in q_lower for kw in keywords):
                domains.append(domain)
        
        return domains or ['general']
    
    # =========================================================================
    # GATHERER METHODS
    # =========================================================================
    
    def _gather_reality(self, question: str, analysis: Dict) -> List[Truth]:
        """Gather Reality truths from DuckDB."""
        if not self.reality_gatherer:
            return []
        return self.reality_gatherer.gather(question, analysis)
    
    def _gather_intent(self, question: str, analysis: Dict) -> List[Truth]:
        """Gather Intent truths from customer documents."""
        # TODO: Implement with IntentGatherer
        return []
    
    def _gather_configuration(self, question: str, analysis: Dict) -> List[Truth]:
        """Gather Configuration truths from config tables."""
        # TODO: Implement with ConfigurationGatherer
        return []
    
    def _gather_reference_library(self, question: str, analysis: Dict) -> tuple:
        """Gather Reference Library truths (Reference, Regulatory, Compliance)."""
        # TODO: Implement with respective gatherers
        return [], [], []
    
    # =========================================================================
    # ANALYSIS METHODS
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
    # UTILITY METHODS
    # =========================================================================
    
    def confirm_filter(self, category: str, value: str):
        """Confirm a filter selection (from clarification)."""
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
