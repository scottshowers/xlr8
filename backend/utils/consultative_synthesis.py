"""
XLR8 CONSULTATIVE SYNTHESIS MODULE v1.1.0
==========================================

Deploy to: backend/utils/consultative_synthesis.py

PURPOSE:
This module transforms raw data retrieval into world-class consultative answers.
It's the difference between "Here's 47 rows" and "Your SUI rates look compliant, 
but I noticed 3 companies haven't updated since 2023 - here's what to check."

ARCHITECTURE:
    gather_five_truths() → ConsultativeSynthesizer.synthesize() → Consultative Answer
                                     ↓
                          1. Triangulate sources
                          2. Detect gaps/conflicts  
                          3. Add "so-what" context
                          4. Signal confidence
                          5. Recommend next steps

LLM PRIORITY (via LLMOrchestrator):
    1. Mistral:7b (local) - Fast, private, no cost
    2. Claude API - Fallback for complex cases
    3. Template - Graceful degradation if all LLMs fail

USAGE:
    from consultative_synthesis import ConsultativeSynthesizer
    
    synthesizer = ConsultativeSynthesizer()  # Uses LLMOrchestrator internally
    answer = synthesizer.synthesize(
        question="Are my SUI rates correct?",
        reality=[...],
        intent=[...],
        # ... other truths
    )
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class TruthSummary:
    """Condensed summary of a truth source for LLM consumption."""
    source_type: str  # reality, intent, configuration, reference, regulatory
    has_data: bool
    summary: str
    key_facts: List[str] = field(default_factory=list)
    confidence: float = 0.0
    sources: List[str] = field(default_factory=list)


@dataclass
class TriangulationResult:
    """Result of comparing truths across sources."""
    alignments: List[str]  # Where sources agree
    conflicts: List[str]   # Where sources disagree
    gaps: List[str]        # Missing information
    confidence: float      # Overall confidence in the triangulation


@dataclass 
class ConsultativeAnswer:
    """The final synthesized answer."""
    answer: str
    confidence: float
    triangulation: TriangulationResult
    recommended_actions: List[str]
    sources_used: List[str]
    synthesis_method: str  # 'mistral', 'claude', 'template'


# =============================================================================
# MAIN SYNTHESIZER CLASS
# =============================================================================

class ConsultativeSynthesizer:
    """
    The consultant brain that transforms raw data into actionable insights.
    
    This is what separates XLR8 from "fancy BI tool" - the ability to
    triangulate across sources and provide the "so-what" that clients
    actually pay consultants for.
    
    Uses LLMOrchestrator for all LLM calls - Mistral first, Claude fallback.
    """
    
    def __init__(self, **kwargs):
        """
        Initialize synthesizer with LLMOrchestrator.
        
        Accepts legacy kwargs (ollama_host, claude_api_key, model_preference) 
        for backwards compatibility but ignores them - LLMOrchestrator handles config.
        """
        # Use existing LLMOrchestrator - it handles all config (LLM_ENDPOINT, auth, etc.)
        self._orchestrator = None
        self.last_method = None
        
        # Log if legacy params passed (for debugging)
        if kwargs:
            logger.debug(f"[CONSULTATIVE] Ignoring legacy kwargs: {list(kwargs.keys())}")
        
        try:
            from utils.llm_orchestrator import LLMOrchestrator
            self._orchestrator = LLMOrchestrator()
            logger.info("[CONSULTATIVE] Initialized with LLMOrchestrator")
        except ImportError:
            try:
                from backend.utils.llm_orchestrator import LLMOrchestrator
                self._orchestrator = LLMOrchestrator()
                logger.info("[CONSULTATIVE] Initialized with LLMOrchestrator (backend path)")
            except ImportError:
                logger.warning("[CONSULTATIVE] LLMOrchestrator not available - template only")
        
    def synthesize(
        self,
        question: str,
        reality: List[Any] = None,
        intent: List[Any] = None,
        configuration: List[Any] = None,
        reference: List[Any] = None,
        regulatory: List[Any] = None,
        compliance: List[Any] = None,
        conflicts: List[Any] = None,
        insights: List[Any] = None,
        structured_data: Dict = None
    ) -> ConsultativeAnswer:
        """
        Main entry point - synthesize all truths into a consultative answer.
        
        Args:
            question: The user's question
            reality: DuckDB query results (data truths)
            intent: Customer requirement documents
            configuration: System setup documents
            reference: Best practice guides
            regulatory: Legal/compliance requirements
            compliance: Audit requirements
            conflicts: Pre-detected conflicts between sources
            insights: Pre-generated insights
            structured_data: Raw query results (rows, columns, sql)
            
        Returns:
            ConsultativeAnswer with synthesized response
        """
        logger.info(f"[SYNTHESIS] Starting synthesis for: {question[:80]}...")
        
        # Step 1: Summarize each truth source
        summaries = self._summarize_truths(
            reality=reality,
            intent=intent,
            configuration=configuration,
            reference=reference,
            regulatory=regulatory,
            structured_data=structured_data
        )
        
        # Step 2: Triangulate - find alignments, conflicts, gaps
        triangulation = self._triangulate(summaries, conflicts or [])
        
        # Step 3: Determine complexity and choose synthesis method
        complexity = self._assess_complexity(question, summaries, triangulation)
        
        # Step 4: Generate the answer
        if complexity == 'simple' and structured_data:
            # Simple data query - use lightweight synthesis
            answer_text = self._synthesize_simple(question, structured_data)
            method = 'template'
        else:
            # Complex query - use LLM synthesis
            answer_text, method = self._synthesize_with_llm(
                question=question,
                summaries=summaries,
                triangulation=triangulation,
                conflicts=conflicts or []
            )
        
        # Step 5: Extract recommended actions
        actions = self._extract_actions(answer_text, triangulation)
        
        # Step 6: Calculate overall confidence
        confidence = self._calculate_confidence(summaries, triangulation)
        
        self.last_method = method
        
        return ConsultativeAnswer(
            answer=answer_text,
            confidence=confidence,
            triangulation=triangulation,
            recommended_actions=actions,
            sources_used=[s.source_type for s in summaries if s.has_data],
            synthesis_method=method
        )
    
    # =========================================================================
    # STEP 1: SUMMARIZE TRUTHS
    # =========================================================================
    
    def _summarize_truths(
        self,
        reality: List[Any] = None,
        intent: List[Any] = None,
        configuration: List[Any] = None,
        reference: List[Any] = None,
        regulatory: List[Any] = None,
        structured_data: Dict = None
    ) -> List[TruthSummary]:
        """Convert raw truth objects into concise summaries for LLM."""
        summaries = []
        
        # REALITY - What the data shows
        reality_summary = self._summarize_reality(reality, structured_data)
        summaries.append(reality_summary)
        
        # INTENT - What customer wants
        intent_summary = self._summarize_documents(intent, 'intent', 'Customer Intent')
        summaries.append(intent_summary)
        
        # CONFIGURATION - How it's set up  
        config_summary = self._summarize_documents(configuration, 'configuration', 'Configuration')
        summaries.append(config_summary)
        
        # REFERENCE - Best practices
        ref_summary = self._summarize_documents(reference, 'reference', 'Reference/Best Practice')
        summaries.append(ref_summary)
        
        # REGULATORY - Legal requirements
        reg_summary = self._summarize_documents(regulatory, 'regulatory', 'Regulatory/Legal')
        summaries.append(reg_summary)
        
        return summaries
    
    def _summarize_reality(self, reality: List[Any], structured_data: Dict = None) -> TruthSummary:
        """Summarize data/query results."""
        if not reality and not structured_data:
            return TruthSummary(
                source_type='reality',
                has_data=False,
                summary="No data found matching the query.",
                confidence=0.0
            )
        
        key_facts = []
        sources = []
        
        # Extract from structured_data if available
        if structured_data:
            rows = structured_data.get('rows', [])
            cols = structured_data.get('columns', [])
            query_type = structured_data.get('query_type', 'list')
            sql = structured_data.get('sql', '')
            
            if query_type == 'count' and rows:
                count = list(rows[0].values())[0] if rows[0] else 0
                key_facts.append(f"Count: {count:,} records")
            elif query_type == 'group' and rows:
                key_facts.append(f"Found {len(rows)} groups/categories")
                # Show top 3 groups
                for row in rows[:3]:
                    vals = list(row.values())
                    if len(vals) >= 2:
                        key_facts.append(f"  - {vals[0]}: {vals[1]}")
            elif rows:
                key_facts.append(f"Found {len(rows)} records with {len(cols)} columns")
                # Sample some key values
                if rows and cols:
                    sample_row = rows[0]
                    for col in cols[:3]:
                        val = sample_row.get(col, '')
                        if val:
                            key_facts.append(f"  - {col}: {str(val)[:50]}")
            
            if sql:
                sources.append(f"SQL: {sql[:100]}...")
        
        # Extract from Truth objects
        if reality:
            for truth in reality[:3]:
                content = getattr(truth, 'content', truth) if hasattr(truth, 'content') else truth
                source_name = getattr(truth, 'source_name', 'Data') if hasattr(truth, 'source_name') else 'Data'
                
                if isinstance(content, dict):
                    if 'rows' in content:
                        key_facts.append(f"From {source_name}: {len(content['rows'])} rows")
                elif isinstance(content, str):
                    key_facts.append(f"From {source_name}: {content[:100]}")
                
                sources.append(source_name)
        
        summary = "; ".join(key_facts[:5]) if key_facts else "Data retrieved but no specific findings."
        
        return TruthSummary(
            source_type='reality',
            has_data=True,
            summary=summary,
            key_facts=key_facts,
            confidence=0.9 if rows else 0.5,
            sources=sources
        )
    
    def _summarize_documents(
        self, 
        truths: List[Any], 
        source_type: str, 
        display_name: str
    ) -> TruthSummary:
        """Summarize document-based truths (intent, config, reference, regulatory)."""
        if not truths:
            return TruthSummary(
                source_type=source_type,
                has_data=False,
                summary=f"No {display_name.lower()} documents found.",
                confidence=0.0
            )
        
        key_facts = []
        sources = []
        total_confidence = 0.0
        
        for truth in truths[:5]:  # Limit to top 5 most relevant
            content = getattr(truth, 'content', str(truth))
            source_name = getattr(truth, 'source_name', 'Document')
            confidence = getattr(truth, 'confidence', 0.5)
            
            # Extract key content
            if isinstance(content, str):
                # Take first 200 chars as summary
                snippet = content[:200].strip()
                if len(content) > 200:
                    snippet += "..."
                key_facts.append(f"[{source_name}]: {snippet}")
            elif isinstance(content, dict):
                key_facts.append(f"[{source_name}]: {json.dumps(content)[:200]}")
            
            sources.append(source_name)
            total_confidence += confidence
        
        avg_confidence = total_confidence / len(truths) if truths else 0.0
        summary = f"Found {len(truths)} relevant {display_name.lower()} documents."
        
        return TruthSummary(
            source_type=source_type,
            has_data=True,
            summary=summary,
            key_facts=key_facts[:5],
            confidence=avg_confidence,
            sources=sources
        )
    
    # =========================================================================
    # STEP 2: TRIANGULATE
    # =========================================================================
    
    def _triangulate(
        self, 
        summaries: List[TruthSummary],
        pre_detected_conflicts: List[Any]
    ) -> TriangulationResult:
        """
        Compare truths across sources to find alignments, conflicts, and gaps.
        
        This is the core "consultant" logic - finding where sources agree,
        disagree, or where information is missing.
        """
        alignments = []
        conflicts = []
        gaps = []
        
        # Check which sources have data
        has_reality = any(s.has_data for s in summaries if s.source_type == 'reality')
        has_intent = any(s.has_data for s in summaries if s.source_type == 'intent')
        has_config = any(s.has_data for s in summaries if s.source_type == 'configuration')
        has_reference = any(s.has_data for s in summaries if s.source_type == 'reference')
        has_regulatory = any(s.has_data for s in summaries if s.source_type == 'regulatory')
        
        # Identify gaps
        if not has_intent:
            gaps.append("No customer requirement documents found - unable to verify against stated intent")
        if not has_config:
            gaps.append("No configuration documentation found - unable to verify system setup")
        if not has_reference:
            gaps.append("No best practice reference found - unable to compare against standards")
        if not has_regulatory:
            gaps.append("No regulatory documentation found - compliance verification limited")
        
        # Convert pre-detected conflicts
        for conflict in pre_detected_conflicts:
            if hasattr(conflict, 'description'):
                conflicts.append(conflict.description)
            elif isinstance(conflict, dict):
                conflicts.append(conflict.get('description', str(conflict)))
            else:
                conflicts.append(str(conflict))
        
        # If we have both reality and regulatory, that's a key alignment point
        if has_reality and has_regulatory and not conflicts:
            alignments.append("Data appears consistent with available regulatory guidance")
        
        # If we have reality and config, note alignment
        if has_reality and has_config and not conflicts:
            alignments.append("System configuration aligns with observed data patterns")
        
        # Calculate triangulation confidence
        sources_available = sum([has_reality, has_intent, has_config, has_reference, has_regulatory])
        base_confidence = sources_available / 5.0  # 5 truth types
        
        # Reduce confidence if there are conflicts
        conflict_penalty = min(len(conflicts) * 0.1, 0.3)
        gap_penalty = min(len(gaps) * 0.05, 0.2)
        
        confidence = max(0.1, base_confidence - conflict_penalty - gap_penalty)
        
        return TriangulationResult(
            alignments=alignments,
            conflicts=conflicts,
            gaps=gaps,
            confidence=confidence
        )
    
    # =========================================================================
    # STEP 3: ASSESS COMPLEXITY
    # =========================================================================
    
    def _assess_complexity(
        self,
        question: str,
        summaries: List[TruthSummary],
        triangulation: TriangulationResult
    ) -> str:
        """
        Determine if this needs full LLM synthesis or simple template.
        
        Returns: 'simple' or 'complex'
        """
        q_lower = question.lower()
        
        # Simple queries - just need data display
        simple_patterns = [
            'how many',
            'count of',
            'list all',
            'show me',
            'what are the',
        ]
        
        # Complex queries - need triangulation and analysis
        complex_patterns = [
            'correct',
            'valid',
            'compliant',
            'should',
            'recommend',
            'issue',
            'problem',
            'compare',
            'why',
            'risk',
            'audit',
        ]
        
        # Check for complexity indicators
        has_conflicts = len(triangulation.conflicts) > 0
        has_multiple_sources = sum(1 for s in summaries if s.has_data) > 1
        is_validation_question = any(p in q_lower for p in complex_patterns)
        is_simple_question = any(p in q_lower for p in simple_patterns) and not is_validation_question
        
        if is_simple_question and not has_conflicts and not has_multiple_sources:
            return 'simple'
        
        return 'complex'
    
    # =========================================================================
    # STEP 4A: SIMPLE SYNTHESIS (Template-based)
    # =========================================================================
    
    def _synthesize_simple(self, question: str, structured_data: Dict) -> str:
        """Generate a simple, direct answer for straightforward queries."""
        rows = structured_data.get('rows', [])
        cols = structured_data.get('columns', [])
        query_type = structured_data.get('query_type', 'list')
        
        if query_type == 'count' and rows:
            count = list(rows[0].values())[0] if rows[0] else 0
            try:
                count = int(count)
                return f"Based on your data, the count is **{count:,}**."
            except:
                return f"Based on your data, the result is **{count}**."
        
        elif query_type == 'group' and rows:
            parts = [f"Here's the breakdown ({len(rows)} categories):\n"]
            for row in rows[:10]:
                vals = list(row.values())
                if len(vals) >= 2:
                    parts.append(f"- **{vals[0]}**: {vals[1]}")
            if len(rows) > 10:
                parts.append(f"\n*...and {len(rows) - 10} more*")
            return "\n".join(parts)
        
        elif rows:
            parts = [f"Found **{len(rows)}** matching records.\n"]
            if cols and len(cols) <= 6:
                # Show as table
                parts.append("| " + " | ".join(cols) + " |")
                parts.append("|" + "---|" * len(cols))
                for row in rows[:10]:
                    vals = [str(row.get(c, ''))[:25] for c in cols]
                    parts.append("| " + " | ".join(vals) + " |")
            if len(rows) > 10:
                parts.append(f"\n*Showing first 10 of {len(rows)} results*")
            return "\n".join(parts)
        
        return "No data found matching your query."
    
    # =========================================================================
    # STEP 4B: LLM SYNTHESIS
    # =========================================================================
    
    def _synthesize_with_llm(
        self,
        question: str,
        summaries: List[TruthSummary],
        triangulation: TriangulationResult,
        conflicts: List[Any]
    ) -> Tuple[str, str]:
        """
        Use LLM to synthesize a consultative answer via LLMOrchestrator.
        
        Flow: Mistral (local) → Claude (fallback) → Template (final fallback)
        
        Returns: (answer_text, method_used)
        """
        if not self._orchestrator:
            logger.warning("[CONSULTATIVE] No orchestrator - using template")
            return self._template_fallback(question, summaries, triangulation), 'template'
        
        # Build context from summaries
        context_parts = []
        for summary in summaries:
            if summary.has_data:
                context_parts.append(f"=== {summary.source_type.upper()} ===")
                context_parts.append(summary.summary)
                for fact in summary.key_facts[:5]:
                    context_parts.append(f"  • {fact}")
        
        # Add conflicts
        if triangulation.conflicts:
            context_parts.append("\n=== CONFLICTS DETECTED ===")
            for c in triangulation.conflicts[:5]:
                context_parts.append(f"  ⚠ {c}")
        
        # Add gaps
        if triangulation.gaps:
            context_parts.append("\n=== INFORMATION GAPS ===")
            for g in triangulation.gaps[:3]:
                context_parts.append(f"  • {g}")
        
        context = "\n".join(context_parts)
        
        # Expert prompt for consultative synthesis
        expert_prompt = """You are a senior HCM implementation consultant reviewing configuration data.

TONE: Peer-to-peer. The user is a professional who knows their business. Never lecture or preach.

Your job is to synthesize information into a clear, actionable answer:
1. Directly answer the question - state findings first
2. Cite specific values from the data (rates, dates, codes)
3. Flag any issues or anomalies you notice
4. If sources conflict, say so clearly

AVOID: "It's important to...", "businesses should...", "essential to comply...", generic advice.
DO: State what you found, what looks correct, what needs attention.

Keep it to 2-4 paragraphs. Natural prose, no bullet points."""

        # Use orchestrator - handles Mistral first, Claude fallback
        result = self._orchestrator.synthesize_answer(
            question=question,
            context=context,
            expert_prompt=expert_prompt,
            use_claude_fallback=True
        )
        
        if result.get('success') and result.get('response'):
            model = result.get('model_used', 'unknown')
            # Normalize model name for reporting
            if 'mistral' in model.lower():
                method = 'mistral'
            elif 'claude' in model.lower():
                method = 'claude'
            else:
                method = model
            logger.info(f"[CONSULTATIVE] Synthesis succeeded: {model}")
            return result['response'], method
        
        # Final fallback - template-based
        logger.warning(f"[CONSULTATIVE] LLM synthesis failed: {result.get('error')}, using template")
        return self._template_fallback(question, summaries, triangulation), 'template'
    
    def _template_fallback(
        self,
        question: str,
        summaries: List[TruthSummary],
        triangulation: TriangulationResult
    ) -> str:
        """Generate answer using templates when LLMs are unavailable."""
        parts = []
        
        # Lead with reality
        reality = next((s for s in summaries if s.source_type == 'reality'), None)
        if reality and reality.has_data:
            parts.append(f"**What the data shows:** {reality.summary}")
            for fact in reality.key_facts[:3]:
                parts.append(f"  - {fact}")
        else:
            parts.append("**Data:** No matching records found.")
        
        # Note any conflicts
        if triangulation.conflicts:
            parts.append("\n**⚠️ Potential issues detected:**")
            for conflict in triangulation.conflicts[:3]:
                parts.append(f"  - {conflict}")
        
        # Note information gaps
        if triangulation.gaps:
            parts.append("\n**ℹ️ Note:** " + triangulation.gaps[0])
        
        # Add supporting context from other truths
        for source_type in ['regulatory', 'reference', 'configuration']:
            source = next((s for s in summaries if s.source_type == source_type and s.has_data), None)
            if source:
                label = {
                    'regulatory': '⚖️ Regulatory context',
                    'reference': '📚 Best practice',
                    'configuration': '⚙️ Configuration'
                }.get(source_type, source_type)
                parts.append(f"\n**{label}:** {source.key_facts[0] if source.key_facts else source.summary}")
        
        return "\n".join(parts)
    
    # =========================================================================
    # STEP 5: EXTRACT ACTIONS
    # =========================================================================
    
    def _extract_actions(
        self,
        answer_text: str,
        triangulation: TriangulationResult
    ) -> List[str]:
        """Extract recommended next steps from the answer."""
        actions = []
        
        # Look for action phrases in the answer
        action_phrases = [
            'recommend',
            'should',
            'next step',
            'verify',
            'check',
            'review',
            'update',
            'confirm',
        ]
        
        lines = answer_text.split('.')
        for line in lines:
            line_lower = line.lower()
            if any(phrase in line_lower for phrase in action_phrases):
                # Clean up the line
                action = line.strip()
                if len(action) > 20 and len(action) < 200:
                    actions.append(action)
        
        # Add gap-based recommendations
        if triangulation.gaps:
            for gap in triangulation.gaps[:2]:
                if 'regulatory' in gap.lower():
                    actions.append("Consider uploading relevant regulatory documentation for compliance verification")
                elif 'reference' in gap.lower():
                    actions.append("Consider uploading implementation standards for best practice comparison")
        
        return actions[:5]  # Limit to 5 actions
    
    # =========================================================================
    # STEP 6: CALCULATE CONFIDENCE
    # =========================================================================
    
    def _calculate_confidence(
        self,
        summaries: List[TruthSummary],
        triangulation: TriangulationResult
    ) -> float:
        """Calculate overall confidence in the answer."""
        
        # Start with triangulation confidence
        confidence = triangulation.confidence
        
        # Boost for having reality (data)
        reality = next((s for s in summaries if s.source_type == 'reality'), None)
        if reality and reality.has_data:
            confidence += 0.2
        
        # Boost for having regulatory backing
        regulatory = next((s for s in summaries if s.source_type == 'regulatory'), None)
        if regulatory and regulatory.has_data:
            confidence += 0.1
        
        # Penalty for conflicts
        confidence -= len(triangulation.conflicts) * 0.1
        
        return max(0.1, min(0.95, confidence))


# =============================================================================
# INTEGRATION HELPER
# =============================================================================

def integrate_with_intelligence_engine(engine_instance, synthesizer: ConsultativeSynthesizer):
    """
    Helper to integrate the synthesizer with an existing IntelligenceEngine.
    
    Call this after creating both objects to wire them together.
    
    Usage:
        engine = IntelligenceEngine(...)
        synthesizer = ConsultativeSynthesizer(...)
        integrate_with_intelligence_engine(engine, synthesizer)
    """
    # Store synthesizer reference
    engine._synthesizer = synthesizer
    
    # Store original method
    original_generate = engine._generate_consultative_response
    
    def enhanced_generate(
        question: str,
        query_type: str,
        result_value: Any,
        result_rows: List[Dict],
        result_columns: List[str],
        data_context: List[str],
        doc_context: List[str],
        reflib_context: List[str],
        filters_applied: List[str],
        insights: List,
        conflicts: List = None,
        compliance_check: Optional[Dict] = None
    ) -> str:
        """Enhanced response generation using ConsultativeSynthesizer."""
        
        # Build structured_data from params
        structured_data = {
            'rows': result_rows,
            'columns': result_columns,
            'query_type': query_type,
        }
        if result_value is not None:
            structured_data['rows'] = [{'value': result_value}]
        
        try:
            # Use new synthesizer
            answer = synthesizer.synthesize(
                question=question,
                structured_data=structured_data,
                conflicts=conflicts,
                insights=insights,
            )
            return answer.answer
        except Exception as e:
            logger.error(f"[SYNTHESIS] Enhanced synthesis failed: {e}, falling back to original")
            # Fall back to original implementation
            return original_generate(
                question=question,
                query_type=query_type,
                result_value=result_value,
                result_rows=result_rows,
                result_columns=result_columns,
                data_context=data_context,
                doc_context=doc_context,
                reflib_context=reflib_context,
                filters_applied=filters_applied,
                insights=insights,
                conflicts=conflicts,
                compliance_check=compliance_check
            )
    
    # Replace method
    engine._generate_consultative_response = enhanced_generate
    logger.info("[SYNTHESIS] Successfully integrated ConsultativeSynthesizer with IntelligenceEngine")


# =============================================================================
# STANDALONE TEST
# =============================================================================

if __name__ == "__main__":
    # Quick test
    synthesizer = ConsultativeSynthesizer()
    
    # Simulate some data
    test_structured = {
        'rows': [
            {'state': 'TX', 'rate': 0.031, 'company': 'ACME'},
            {'state': 'CA', 'rate': 0.034, 'company': 'ACME'},
            {'state': 'NY', 'rate': 0.039, 'company': 'ACME'},
        ],
        'columns': ['state', 'rate', 'company'],
        'query_type': 'list'
    }
    
    result = synthesizer.synthesize(
        question="Are my SUI rates correct?",
        structured_data=test_structured
    )
    
    print("=" * 60)
    print("CONSULTATIVE ANSWER:")
    print("=" * 60)
    print(result.answer)
    print("\n" + "=" * 60)
    print(f"Confidence: {result.confidence:.1%}")
    print(f"Method: {result.synthesis_method}")
    print(f"Actions: {result.recommended_actions}")
