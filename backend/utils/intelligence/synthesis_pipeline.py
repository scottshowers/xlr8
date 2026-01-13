"""
XLR8 Intelligence Engine - Synthesis Pipeline
==============================================
Phase 3: Main Synthesis Integration

This is the orchestrator for Phase 3 synthesis, bringing together:
- 3.1 Truth Assembly (truth_assembler.py)
- 3.2 LLM Prompt Engineering (llm_prompter.py)
- 3.3 Gap Detection (enhanced_gap_detector.py)
- 3.4 Response Patterns (response_patterns.py)

The pipeline flow:
1. Assemble all Five Truths into TruthContext
2. Detect gaps between truths
3. Build optimized prompt for local LLM
4. Call LLM for synthesis (or use template)
5. Format response with consultative patterns
6. Validate response quality

REPLACES: synthesizer.py (the old 2000-line monolith)
CALLED BY: engine.py in ask() method

Deploy to: backend/utils/intelligence/synthesis_pipeline.py
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

from .types import Truth, SynthesizedAnswer, Conflict, Insight, IntelligenceMode
from .truth_assembler import (
    TruthAssembler, TruthContext, Gap, Citation,
    get_assembler, assemble_truths
)
from .llm_prompter import (
    LocalLLMPrompter, ResponseQuality,
    get_prompter, build_synthesis_prompt
)
from .enhanced_gap_detector import (
    EnhancedGapDetector, GapExplainer, GapType,
    get_detector as get_gap_detector,
    detect_gaps
)
from .response_patterns import (
    ResponseFormatter, ConsultativeResponse,
    get_formatter, format_response, render_response
)

logger = logging.getLogger(__name__)

# Log version on import
logger.warning("[SYNTHESIS-PIPELINE] Module loaded - VERSION 1.0.0 (Phase 3 Clean Implementation)")


# =============================================================================
# SYNTHESIS PIPELINE (Replaces old Synthesizer class)
# =============================================================================

class SynthesisPipeline:
    """
    Main synthesis pipeline for Phase 3.
    
    REPLACES: The old Synthesizer class from synthesizer.py
    
    Orchestrates all synthesis components to produce
    consultative responses from assembled truths.
    
    Maintains same interface as old Synthesizer.synthesize() for compatibility.
    """
    
    def __init__(self, 
                 llm_synthesizer=None,
                 confirmed_facts: Dict = None,
                 filter_candidates: Dict = None,
                 schema: Dict = None,
                 structured_handler=None,
                 vocabulary: Dict = None,
                 dimensions: List = None,
                 scope: Dict = None,
                 coverage: Dict = None,
                 preferred_model: str = 'mistral'):
        """
        Initialize the synthesis pipeline.
        
        Args match old Synthesizer for drop-in replacement:
            llm_synthesizer: LLM client (ConsultativeSynthesizer or similar)
            confirmed_facts: Dict of confirmed filter facts
            filter_candidates: Dict of filter category → candidates
            schema: Schema metadata for suggestions
            structured_handler: DuckDB handler for running queries
            vocabulary: Column name → label/values mapping
            dimensions: Natural breakdown hierarchy
            scope: Who's in the data - countries, companies, active/termed
            coverage: Config vs used per entity type
            preferred_model: Preferred local LLM (mistral, deepseek)
        """
        # Store context (same as old Synthesizer)
        self.llm_synthesizer = llm_synthesizer
        self.confirmed_facts = confirmed_facts or {}
        self.filter_candidates = filter_candidates or {}
        self.schema = schema or {}
        self.structured_handler = structured_handler
        self.vocabulary = vocabulary or {}
        self.dimensions = dimensions or []
        self.scope = scope or {}
        self.coverage = coverage or {}
        
        # Initialize Phase 3 components
        self.assembler = get_assembler()
        self.prompter = get_prompter(preferred_model)
        self.gap_detector = get_gap_detector()
        self.gap_explainer = GapExplainer()
        self.formatter = get_formatter()
        
        # Track state (for compatibility)
        self.last_executed_sql: Optional[str] = None
        self._last_consultative_answer = None
        self._context_graph: Dict = None
        self._project: str = None
        
        logger.info(f"[SYNTHESIS] Pipeline initialized (llm={'available' if llm_synthesizer else 'template-only'})")
    
    def synthesize(
        self,
        question: str,
        mode: IntelligenceMode,
        reality: List[Truth],
        intent: List[Truth],
        configuration: List[Truth],
        reference: List[Truth],
        regulatory: List[Truth],
        compliance: List[Truth],
        conflicts: List[Conflict],
        insights: List[Insight],
        compliance_check: Optional[Dict] = None,
        context: Dict = None,
        context_graph: Dict = None
    ) -> SynthesizedAnswer:
        """
        Synthesize a consultative answer from all Five Truths.
        
        SAME SIGNATURE as old Synthesizer.synthesize() for drop-in replacement.
        
        Args:
            question: The user's question
            mode: Intelligence mode (search, analyze, validate, etc.)
            reality: Truths from Reality (DuckDB data)
            intent: Truths from Intent (customer docs)
            configuration: Truths from Configuration (config tables)
            reference: Truths from Reference (product docs)
            regulatory: Truths from Regulatory (laws/compliance)
            compliance: Truths from Compliance checks
            conflicts: Detected conflicts between truths
            insights: Proactive insights discovered
            compliance_check: Results of compliance checking
            context: Additional context (is_config, is_validation, project, etc.)
            context_graph: Hub/spoke relationships and coverage info
            
        Returns:
            SynthesizedAnswer with full provenance
        """
        import time
        start_time = time.time()
        
        # Store context for later use
        self._context_graph = context_graph
        ctx = context or {}
        self._project = ctx.get('project')
        
        reasoning = []
        
        # =====================================================================
        # STEP 1: Extract SQL results from Reality truths
        # =====================================================================
        sql_results = self._extract_sql_results(reality)
        if sql_results.get('row_count', 0) > 0:
            reasoning.append(f"Found {sql_results['row_count']} data rows")
        
        # =====================================================================
        # STEP 2: Assemble all Five Truths into structured context
        # =====================================================================
        logger.info(f"[SYNTHESIS] Assembling truths for: {question[:50]}...")
        
        truth_context = self.assembler.assemble(
            question=question,
            sql_results=sql_results,
            reality_truths=reality,
            intent_truths=intent,
            configuration_truths=configuration,
            reference_truths=reference,
            regulatory_truths=regulatory,
            project=self._project,
        )
        
        reasoning.append(f"Truths assembled: {truth_context.truths_used}")
        
        # =====================================================================
        # STEP 3: Detect gaps between truths
        # =====================================================================
        gaps = self.gap_detector.detect_gaps(truth_context)
        truth_context.gaps = gaps
        
        if gaps:
            reasoning.append(f"Detected {len(gaps)} gaps")
            # Convert gaps to Insight objects for backward compatibility
            for gap in gaps[:5]:
                insights.append(Insight(
                    type='gap_detection',
                    title=f'{gap.gap_type}: {gap.topic}',
                    description=gap.description,
                    data={'recommendation': gap.recommendation},
                    severity=gap.severity,
                    action_required=(gap.severity == 'high')
                ))
        
        # =====================================================================
        # STEP 4: Build prompt and call LLM (or use template)
        # =====================================================================
        llm_response = ""
        synthesis_method = "template"
        
        if self.llm_synthesizer and truth_context.has_data:
            try:
                prompt = self.prompter.build_prompt(truth_context)
                llm_response = self._call_llm_sync(prompt)
                synthesis_method = "llm"
                reasoning.append(f"LLM synthesis: {len(llm_response)} chars")
            except Exception as e:
                logger.warning(f"[SYNTHESIS] LLM call failed, using template: {e}")
        
        # =====================================================================
        # STEP 5: Format response with consultative patterns
        # =====================================================================
        if llm_response:
            formatted = self.formatter.format(truth_context, llm_response=llm_response)
        else:
            formatted = self.formatter.format(truth_context)
        
        response_text = formatted.to_markdown()
        
        # =====================================================================
        # STEP 6: Validate response quality
        # =====================================================================
        quality = self.prompter.validate_response(response_text, truth_context)
        
        if not quality.is_acceptable:
            logger.warning(f"[SYNTHESIS] Response quality low: {quality.score:.2f}")
            reasoning.append(f"Quality check: {quality.score:.2f}")
        
        # =====================================================================
        # STEP 7: Calculate confidence and build answer
        # =====================================================================
        confidence = self._calculate_confidence(
            reality, intent, configuration, reference, regulatory, compliance
        )
        
        # Store for get_consultative_metadata()
        self._last_consultative_answer = {
            'question_type': truth_context.intent_type,
            'question_category': truth_context.domain,
            'synthesis_method': synthesis_method,
            'proactive_offers': formatted.proactive_offers or [],
            'excel_spec': [],  # Could be populated from formatter
            'hcmpact_hook': '',
            'recommended_actions': formatted.recommendations or [],
        }
        
        synthesis_time_ms = int((time.time() - start_time) * 1000)
        reasoning.append(f"Synthesis complete in {synthesis_time_ms}ms")
        
        logger.info(f"[SYNTHESIS] Complete: {len(response_text)} chars, "
                   f"confidence={confidence:.0%}, method={synthesis_method}")
        
        return SynthesizedAnswer(
            question=question,
            answer=response_text,
            confidence=confidence,
            from_reality=reality,
            from_intent=intent,
            from_configuration=configuration,
            from_reference=reference,
            from_regulatory=regulatory,
            from_compliance=compliance,
            conflicts=conflicts,
            insights=insights,
            compliance_check=compliance_check,
            structured_output=sql_results.get('structured_output'),
            reasoning=reasoning,
            executed_sql=sql_results.get('sql', ''),
            citations=[c.to_dict() for c in truth_context.citations] if truth_context.citations else None,
        )
    
    def get_consultative_metadata(self) -> Optional[Dict]:
        """
        Get rich metadata from last consultative synthesis.
        
        SAME INTERFACE as old Synthesizer for compatibility.
        
        Returns:
            Dict with: question_type, question_category, excel_spec, 
                      proactive_offers, hcmpact_hook, synthesis_method
        """
        return self._last_consultative_answer
    
    def _extract_sql_results(self, reality: List[Truth]) -> Dict:
        """Extract SQL results from reality truths."""
        results = {
            'sql': '',
            'data': [],
            'row_count': 0,
            'columns': [],
            'query_type': 'list',
            'table': '',
            'structured_output': None,
        }
        
        if not reality:
            return results
        
        for truth in reality[:3]:
            if isinstance(truth.content, dict) and 'rows' in truth.content:
                results['sql'] = truth.metadata.get('sql', '')
                results['data'] = truth.content.get('rows', [])
                results['row_count'] = len(results['data'])
                results['columns'] = truth.content.get('columns', [])
                results['query_type'] = truth.content.get('query_type', 'list')
                results['table'] = truth.content.get('table', '')
                results['structured_output'] = truth.content.get('structured_output')
                
                # Use real total if available
                if 'total' in truth.content:
                    results['row_count'] = truth.content['total']
                
                break
        
        return results
    
    def _call_llm_sync(self, prompt: str) -> str:
        """Call LLM synchronously."""
        if not self.llm_synthesizer:
            return ""
        
        try:
            # Try the synthesize method if available
            if hasattr(self.llm_synthesizer, 'synthesize'):
                result = self.llm_synthesizer.synthesize(
                    question=prompt,
                    data_context=[],
                    doc_context=[],
                    reflib_context=[]
                )
                if hasattr(result, 'answer'):
                    return result.answer
                return str(result)
            
            # Try generate method (Ollama style)
            if hasattr(self.llm_synthesizer, 'generate'):
                import asyncio
                loop = asyncio.get_event_loop()
                result = loop.run_until_complete(
                    self.llm_synthesizer.generate(prompt=prompt)
                )
                return result.get('response', '')
            
            return ""
            
        except Exception as e:
            logger.warning(f"[SYNTHESIS] LLM call error: {e}")
            return ""
    
    def _calculate_confidence(self, reality, intent, configuration,
                              reference, regulatory, compliance) -> float:
        """Calculate confidence score based on available truths."""
        confidence = 0.5
        
        # Reality is most important
        if reality:
            has_data = any(
                isinstance(t.content, dict) and t.content.get('rows')
                for t in reality
            )
            confidence += 0.25 if has_data else 0.1
        
        # Supporting truths
        if intent:
            confidence += 0.05
        if configuration:
            confidence += 0.05
        if reference:
            confidence += 0.05
        if regulatory:
            confidence += 0.05
        if compliance:
            confidence += 0.05
        
        return min(confidence, 0.95)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_pipeline_instance: Optional[SynthesisPipeline] = None

def get_pipeline(**kwargs) -> SynthesisPipeline:
    """Get a pipeline instance (not singleton - creates new each time for flexibility)."""
    return SynthesisPipeline(**kwargs)


def create_synthesizer(**kwargs) -> SynthesisPipeline:
    """
    Factory function to create a SynthesisPipeline.
    
    This is the replacement for creating old Synthesizer instances.
    Use this in engine.py instead of Synthesizer().
    """
    return SynthesisPipeline(**kwargs)


# Alias for backward compatibility - SynthesisPipeline IS the new Synthesizer
Synthesizer = SynthesisPipeline
