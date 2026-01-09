"""
XLR8 CONSULTATIVE SYNTHESIS MODULE v4.7.0
==========================================

Deploy to: backend/utils/consultative_synthesis.py

v4.7 CHANGES:
- Organizational metrics now injected as GROUNDING FACTS at the top of LLM context
- These are "WHAT YOU KNOW ABOUT THIS CLIENT" - verified facts to inform every answer
- Enhanced expert prompt references grounding facts for consultative responses

APPROACH: Let the LLM reason like a consultant
- Send actual data rows (not just schema)
- Reasoning framework: UNDERSTAND → DECOMPOSE → ANALYZE → SYNTHESIZE → VALIDATE → ANSWER
- Trust the 14B model to find patterns (e.g., tax_type=SUI = SUI rate)

ROUTING:
- ALL synthesis → Qwen 14B 
- FALLBACK → Claude (only if Qwen fails)

v3.0 CHANGES:
- Reasoning framework prompt (chain of thought)
- Send ALL key_facts to LLM (removed [:5] truncation)
- Actual row data included so LLM can analyze values

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
import re
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Import response patterns - the consultant's thinking chain
try:
    from utils.response_patterns import (
        detect_question_type, 
        generate_thinking_prompt,
        generate_excel_spec,
        ResponsePattern,
        QuestionCategory
    )
    PATTERNS_AVAILABLE = True
except ImportError:
    try:
        from backend.utils.response_patterns import (
            detect_question_type,
            generate_thinking_prompt, 
            generate_excel_spec,
            ResponsePattern,
            QuestionCategory
        )
        PATTERNS_AVAILABLE = True
    except ImportError:
        logger.warning("[CONSULTATIVE] Response patterns not available")
        PATTERNS_AVAILABLE = False


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
    # v4.0: Response pattern for deliverable generation
    question_type: str = ""
    question_category: str = ""
    excel_spec: List[Dict] = field(default_factory=list)
    proactive_offers: List[str] = field(default_factory=list)
    hcmpact_hook: str = ""


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
        structured_data: Dict = None,
        context_graph: Dict = None,  # v3.0: Context Graph for relationship context
        context: Dict = None,  # v4.5: Additional context including organizational_metrics
        **kwargs  # Accept additional kwargs for forward compatibility
    ) -> ConsultativeAnswer:
        """
        Main entry point - synthesize all truths into a consultative answer.
        
        v3.0: Now accepts context_graph for relationship awareness.
        v4.5: Now accepts context with organizational_metrics for instant insights.
        
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
            context_graph: Hub/spoke relationships and coverage info
            context: Additional context including organizational_metrics
            
        Returns:
            ConsultativeAnswer with synthesized response
        """
        logger.warning(f"[SYNTHESIS] Starting synthesis for: {question[:80]}...")
        
        # v4.5: Extract organizational metrics from context
        organizational_metrics = []
        if context and isinstance(context, dict):
            organizational_metrics = context.get('organizational_metrics', [])
            if organizational_metrics:
                logger.warning(f"[SYNTHESIS] Received {len(organizational_metrics)} organizational metrics")
        
        # =====================================================================
        # v4.0: DETECT QUESTION TYPE AND GET RESPONSE PATTERN
        # =====================================================================
        pattern = None
        if PATTERNS_AVAILABLE:
            pattern = detect_question_type(question)
            logger.warning(f"[SYNTHESIS] Question type: {pattern.question_type} ({pattern.category.value})")
            logger.warning(f"[SYNTHESIS] Hidden worry: {pattern.hidden_worry}")
        
        # Step 1: Summarize each truth source
        summaries = self._summarize_truths(
            reality=reality,
            intent=intent,
            configuration=configuration,
            reference=reference,
            regulatory=regulatory,
            structured_data=structured_data
        )
        
        # v3.0: Add Context Graph context to summaries if available
        if context_graph:
            graph_summary = self._summarize_context_graph(context_graph)
            if graph_summary:
                summaries.append(graph_summary)
        
        # v4.5: Add organizational metrics to summaries if available
        if organizational_metrics:
            metrics_summary = self._summarize_organizational_metrics(organizational_metrics)
            if metrics_summary:
                summaries.append(metrics_summary)
        
        # Step 2: Triangulate - find alignments, conflicts, gaps
        triangulation = self._triangulate(summaries, conflicts or [])
        
        # Step 3: Determine complexity (for logging only now)
        complexity = self._assess_complexity(question, summaries, triangulation)
        logger.warning(f"[SYNTHESIS] Complexity: {complexity}")
        
        # Step 4: Generate the answer using pattern-guided LLM
        answer_text, method = self._synthesize_with_llm(
            question=question,
            summaries=summaries,
            triangulation=triangulation,
            conflicts=conflicts or [],
            complexity=complexity,
            pattern=pattern  # v4.0: Pass pattern for thinking guidance
        )
        
        # Step 5: Extract recommended actions
        actions = self._extract_actions(answer_text, triangulation)
        
        # v4.0: Add pattern-based proactive offers to actions
        if pattern and pattern.proactive_offers:
            actions.extend(pattern.proactive_offers)
        
        # Step 6: Calculate overall confidence
        confidence = self._calculate_confidence(summaries, triangulation)
        
        self.last_method = method
        
        # v4.0: Build excel spec and extract pattern metadata
        excel_spec = []
        question_type = ""
        question_category = ""
        hcmpact_hook = ""
        proactive_offers = []
        
        if pattern:
            excel_spec = generate_excel_spec(pattern) if PATTERNS_AVAILABLE else []
            question_type = pattern.question_type
            question_category = pattern.category.value
            hcmpact_hook = pattern.hcmpact_hook
            proactive_offers = list(pattern.proactive_offers)
        
        return ConsultativeAnswer(
            answer=answer_text,
            confidence=confidence,
            triangulation=triangulation,
            recommended_actions=actions,
            sources_used=[s.source_type for s in summaries if s.has_data],
            synthesis_method=method,
            question_type=question_type,
            question_category=question_category,
            excel_spec=excel_spec,
            proactive_offers=proactive_offers,
            hcmpact_hook=hcmpact_hook
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
    
    def _summarize_context_graph(self, context_graph: Dict) -> Optional[TruthSummary]:
        """
        Summarize Context Graph relationships for LLM context.
        
        v3.0: Provides hub/spoke relationship context so LLM understands
        how data connects and where gaps exist.
        """
        if not context_graph:
            return None
        
        hubs = context_graph.get('hubs', [])
        relationships = context_graph.get('relationships', [])
        
        if not hubs and not relationships:
            return None
        
        key_facts = []
        
        # Summarize hubs (master data)
        if hubs:
            key_facts.append(f"Data model has {len(hubs)} master data hubs:")
            for hub in hubs[:5]:
                sem_type = hub.get('semantic_type', 'unknown')
                table = hub.get('table', 'unknown')
                key_facts.append(f"  - {sem_type}: {table}")
        
        # Summarize coverage gaps
        low_coverage = [r for r in relationships if (r.get('coverage_pct') or 0) < 70]
        if low_coverage:
            key_facts.append(f"\nData coverage gaps ({len(low_coverage)} tables with <70% coverage):")
            for rel in low_coverage[:5]:
                spoke = rel.get('spoke_table', 'unknown')
                sem_type = rel.get('semantic_type', 'unknown')
                coverage = rel.get('coverage_pct', 0)
                matched = rel.get('matched_count', 0)
                total = rel.get('hub_count', 0)
                key_facts.append(f"  - {spoke}: only {matched}/{total} {sem_type}s ({coverage:.0f}%)")
        
        if not key_facts:
            return None
        
        return TruthSummary(
            source_type='data_model',
            has_data=True,
            summary=f"Context Graph: {len(hubs)} hubs, {len(relationships)} relationships",
            key_facts=key_facts,
            confidence=0.95,
            sources=['context_graph']
        )
    
    def _summarize_organizational_metrics(self, metrics: List) -> Optional[TruthSummary]:
        """
        Summarize organizational metrics for LLM context.
        
        v4.5: Provides pre-computed metrics so the LLM can give
        immediate, accurate answers about headcount, coverage, etc.
        """
        if not metrics:
            return None
        
        key_facts = []
        
        # Group metrics by category
        by_category = {}
        for m in metrics:
            cat = m.category.value if hasattr(m.category, 'value') else str(m.category)
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(m)
        
        # Workforce metrics (headcount, etc.)
        if 'workforce' in by_category:
            key_facts.append("**Workforce Metrics:**")
            for m in by_category['workforce'][:5]:
                key_facts.append(f"  - {m.metric_name}: {m.value_formatted}")
        
        # Dimensional breakdowns (by company, location)
        if 'dimensional' in by_category:
            key_facts.append("\n**Breakdowns:**")
            # Group by metric_name
            by_metric = {}
            for m in by_category['dimensional']:
                if m.metric_name not in by_metric:
                    by_metric[m.metric_name] = []
                by_metric[m.metric_name].append(m)
            
            for metric_name, items in list(by_metric.items())[:3]:  # Top 3 dimensions
                key_facts.append(f"  {metric_name}:")
                for m in items[:5]:  # Top 5 values per dimension
                    key_facts.append(f"    - {m.dimension_value}: {m.value_formatted}")
        
        # Configuration metrics (hub usage)
        if 'configuration' in by_category:
            key_facts.append("\n**Configuration Usage:**")
            for m in by_category['configuration'][:5]:
                key_facts.append(f"  - {m.metric_name}: {m.value_formatted}")
        
        # Benefits metrics
        if 'benefits' in by_category:
            key_facts.append("\n**Benefits Participation:**")
            for m in by_category['benefits'][:5]:
                key_facts.append(f"  - {m.metric_name}: {m.value_formatted}")
        
        if not key_facts:
            return None
        
        return TruthSummary(
            source_type='organizational_metrics',
            has_data=True,
            summary=f"Organizational Intelligence: {len(metrics)} pre-computed metrics",
            key_facts=key_facts,
            confidence=0.98,  # High confidence - these are computed from actual data
            sources=['project_intelligence']
        )
    
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
                for row in rows[:5]:
                    vals = list(row.values())
                    if len(vals) >= 2:
                        key_facts.append(f"  - {vals[0]}: {vals[1]}")
            elif rows:
                # =====================================================================
                # v4.0: SEND DATA FOR ANALYSIS
                # Reality tables (employees) can be huge, so cap at 100 for analysis
                # LLM will display max 30 but analyze all provided
                # =====================================================================
                key_facts.append(f"Table: {len(rows)} records, {len(cols)} columns")
                key_facts.append(f"Columns: {', '.join(cols)}")
                
                # Detect code/description columns for cleaner formatting
                code_col = None
                desc_col = None
                for col in cols:
                    col_lower = col.lower()
                    if 'code' in col_lower and 'country' not in col_lower and 'group' not in col_lower:
                        code_col = col
                    elif any(x in col_lower for x in ['desc', 'name', 'label']) and 'group' not in col_lower:
                        desc_col = col
                
                # Send up to 100 rows for analysis (reality tables can be huge)
                max_rows = min(100, len(rows))
                key_facts.append("\nData:")
                for i, row in enumerate(rows[:max_rows]):
                    if code_col and desc_col:
                        # Format as code - description
                        code = row.get(code_col, '')
                        desc = row.get(desc_col, '')
                        key_facts.append(f"  - `{code}` - {desc}")
                    else:
                        # Fallback to key=value format
                        row_str = " | ".join(f"{k}={v}" for k, v in list(row.items())[:8])
                        key_facts.append(f"  Row {i+1}: {row_str}")
                
                if len(rows) > max_rows:
                    key_facts.append(f"  ... and {len(rows) - max_rows} more rows (full data in Excel)")
            
            if sql:
                # Extract table name from SQL for clarity
                table_match = re.search(r'FROM\s+["\']?(\w+)["\']?', sql, re.IGNORECASE)
                if table_match:
                    key_facts.append(f"\nSource: {table_match.group(1)}")
        
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
                # v4.0: Special handling for config tables with rows
                # These contain actual data that needs to be shown, not truncated
                if 'rows' in content and content['rows']:
                    rows = content['rows']
                    cols = content.get('columns', list(rows[0].keys()) if rows else [])
                    table_name = content.get('display_name') or content.get('table') or source_name
                    
                    key_facts.append(f"\n[{table_name}] - {len(rows)} records:")
                    key_facts.append(f"Columns: {', '.join(cols)}")
                    
                    # v4.0: Send ALL data for analysis (LLM limits display to 30)
                    # Config tables are typically small, send everything
                    max_rows = len(rows)  # No limit - send all for analysis
                    key_facts.append("Data:")
                    for i, row in enumerate(rows[:max_rows]):
                        # Format as code - description if we can detect those columns
                        code_col = None
                        desc_col = None
                        for col in cols:
                            col_lower = col.lower()
                            if 'code' in col_lower and 'country' not in col_lower:
                                code_col = col
                            elif any(x in col_lower for x in ['desc', 'name', 'label']):
                                desc_col = col
                        
                        if code_col and desc_col:
                            code = row.get(code_col, '')
                            desc = row.get(desc_col, '')
                            key_facts.append(f"  - `{code}` - {desc}")
                        else:
                            # Fallback to key=value format
                            row_str = " | ".join(f"{k}={v}" for k, v in list(row.items())[:6])
                            key_facts.append(f"  Row {i+1}: {row_str}")
                    
                    if len(rows) > max_rows:
                        key_facts.append(f"  ... and {len(rows) - max_rows} more rows")
                else:
                    # Regular dict - safe serialization with truncation
                    try:
                        exclude_keys = {'classification', 'table_classification', 'metadata_obj'}
                        
                        def is_serializable(v):
                            """Check if value is JSON-serializable."""
                            if v is None:
                                return True
                            if isinstance(v, (str, int, float, bool)):
                                return True
                            if isinstance(v, (list, tuple)):
                                return all(is_serializable(item) for item in v)
                            if isinstance(v, dict):
                                return all(isinstance(k, str) and is_serializable(val) for k, val in v.items())
                            return False
                        
                        safe_content = {k: v for k, v in content.items() 
                                      if k not in exclude_keys and is_serializable(v)}
                        key_facts.append(f"[{source_name}]: {json.dumps(safe_content)[:200]}")
                    except (TypeError, ValueError) as e:
                        logger.debug(f"[SYNTHESIS] JSON serialization failed: {e}, using string fallback")
                        key_facts.append(f"[{source_name}]: {str(content)[:200]}")
            
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
            except Exception:
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
        conflicts: List[Any],
        complexity: str = 'complex',
        pattern: Any = None  # v4.0: ResponsePattern for guided thinking
    ) -> Tuple[str, str]:
        """
        Use LLM to synthesize a consultative answer.
        
        v4.7: Organizational metrics are now injected as GROUNDING FACTS at the
        top of the context - these are KNOWN TRUTHS about the client that should
        inform every answer.
        
        MODEL CASCADE (in order):
        1. Groq (llama-3.3-70b) - Fast, reliable, high quality
        2. Local Ollama (deepseek-r1:14b) - If Groq unavailable
        3. Claude API - Final fallback
        
        Returns: (answer_text, method_used)
        """
        # =====================================================================
        # v4.7: EXTRACT ORGANIZATIONAL METRICS AS GROUNDING FACTS
        # These go at the TOP - they're what the consultant KNOWS about this client
        # =====================================================================
        grounding_facts = []
        other_summaries = []
        
        for summary in summaries:
            if summary.source_type == 'organizational_metrics':
                # Extract the key facts as grounding
                grounding_facts.extend(summary.key_facts)
            else:
                other_summaries.append(summary)
        
        # Build context - GROUNDING FACTS FIRST
        context_parts = []
        
        if grounding_facts:
            context_parts.append("=" * 60)
            context_parts.append("WHAT YOU KNOW ABOUT THIS CLIENT (VERIFIED FACTS - USE THESE)")
            context_parts.append("=" * 60)
            context_parts.append("These metrics are computed from COMPLETE data analysis.")
            context_parts.append("They are MORE ACCURATE than raw query results below.")
            context_parts.append("")
            for fact in grounding_facts:
                context_parts.append(f"  ★ {fact}")
            context_parts.append("")
            context_parts.append("=" * 60)
            context_parts.append("")  # Blank line separator
        
        # Then add other data sources
        for summary in other_summaries:
            if summary.has_data:
                # Label Reality as potentially partial
                if summary.source_type == 'reality':
                    context_parts.append(f"=== {summary.source_type.upper()} (RAW QUERY - MAY BE PARTIAL) ===")
                else:
                    context_parts.append(f"=== {summary.source_type.upper()} ===")
                context_parts.append(summary.summary)
                for fact in summary.key_facts:
                    context_parts.append(f"  {fact}")
        
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
        
        # =====================================================================
        # v4.7: ENHANCED EXPERT PROMPT - References grounding facts
        # =====================================================================
        if pattern and PATTERNS_AVAILABLE:
            expert_prompt = generate_thinking_prompt(pattern, question)
            logger.warning(f"[CONSULTATIVE] Using pattern-guided prompt for: {pattern.question_type}")
        else:
            # Enhanced fallback prompt that references grounding facts
            if grounding_facts:
                expert_prompt = """You are a senior HCM implementation consultant who KNOWS this client well.

CRITICAL - DATA PRIORITY:
The "WHAT YOU KNOW ABOUT THIS CLIENT" section contains VERIFIED FACTS computed from complete data analysis.
These are MORE ACCURATE than raw query results shown in the REALITY section.

For questions about headcount, employee counts, or organizational metrics:
→ USE the verified facts (e.g., "active_headcount: 3,976") 
→ IGNORE conflicting numbers from raw REALITY queries (which may be from partial/wrong tables)

RESPONSE APPROACH:
1. Answer using the VERIFIED FACTS first - these are authoritative
2. If REALITY data adds useful detail (names, specifics), incorporate it
3. If numbers conflict, trust the verified facts and note any discrepancy
4. Be consultative - you're a trusted advisor who knows their business

Example: If verified facts show "active_headcount: 3,976" but a REALITY query shows 458 rows,
the correct answer is 3,976 employees (the query hit the wrong table)."""
            else:
                expert_prompt = """You are a senior HCM implementation consultant. Analyze the data and provide a professional, actionable response.

RESPONSE FORMAT:
1. Direct answer to the question (YES/NO/PARTIALLY with specifics)
2. Key findings from the data (bullet points with actual values)
3. Issues or gaps identified (if any)
4. Recommended next steps

Be specific. Quote actual values from the data. Do not be vague."""

        MIN_RESPONSE_LENGTH = 150
        
        # =====================================================================
        # USE LLM ORCHESTRATOR - Handles cascade internally
        # =====================================================================
        if not self._orchestrator:
            logger.warning("[CONSULTATIVE] LLMOrchestrator not available, using template")
            return self._template_fallback(question, summaries, triangulation), 'template'
        
        logger.warning("[CONSULTATIVE] Using LLMOrchestrator for synthesis...")
        logger.warning(f"[CONSULTATIVE] Grounding facts: {len(grounding_facts)}, Other sources: {len(other_summaries)}")
        
        result = self._orchestrator.synthesize_answer(
            question=question,
            context=context,
            expert_prompt=expert_prompt,
            use_claude_fallback=True
        )
        
        if result.get('success') and result.get('response'):
            response_len = len(result.get('response', ''))
            model_used = result.get('model_used', 'unknown')
            
            if response_len >= MIN_RESPONSE_LENGTH:
                logger.warning(f"[CONSULTATIVE] {model_used} succeeded ({response_len} chars)")
                return result['response'], model_used
            else:
                logger.warning(f"[CONSULTATIVE] {model_used} response too short ({response_len} chars)")
        else:
            logger.warning(f"[CONSULTATIVE] LLM failed: {result.get('error', 'unknown')}")
        
        # Final fallback - template-based
        logger.warning("[CONSULTATIVE] All LLMs failed, using template")
        return self._template_fallback(question, summaries, triangulation), 'template'
    
    def _call_local_model(self, model: str, question: str, context: str, expert_prompt: str) -> Dict[str, Any]:
        """
        Call a specific local Ollama model for synthesis.
        """
        try:
            import requests
            from requests.auth import HTTPBasicAuth
            import os
            
            ollama_url = os.getenv("LLM_ENDPOINT", "").rstrip('/')
            ollama_username = os.getenv("LLM_USERNAME", "")
            ollama_password = os.getenv("LLM_PASSWORD", "")
            
            if not ollama_url:
                logger.warning("[CONSULTATIVE] No LLM_ENDPOINT configured")
                return {"success": False, "error": "No Ollama URL"}
            
            prompt = f"""{expert_prompt}

QUESTION: {question}

DATA:
{context[:10000]}

Provide a direct answer based ONLY on the data above."""

            url = f"{ollama_url}/api/generate"
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,  # Slightly higher for more natural output
                    "num_predict": 1000  # Allow longer responses
                }
            }
            
            logger.warning(f"[CONSULTATIVE] Calling {model} ({len(prompt)} chars)")
            
            if ollama_username and ollama_password:
                response = requests.post(
                    url, json=payload,
                    auth=HTTPBasicAuth(ollama_username, ollama_password),
                    timeout=90
                )
            else:
                response = requests.post(url, json=payload, timeout=90)
            
            if response.status_code == 200:
                result = response.json().get("response", "").strip()
                if result and len(result) > 30:
                    logger.warning(f"[CONSULTATIVE] {model} succeeded ({len(result)} chars)")
                    return {
                        "success": True,
                        "response": result,
                        "model_used": model
                    }
                else:
                    logger.warning(f"[CONSULTATIVE] {model} returned empty/short response")
                    return {"success": False, "error": "Empty response"}
            else:
                logger.warning(f"[CONSULTATIVE] {model} HTTP error: {response.status_code}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"[CONSULTATIVE] {model} error: {e}")
            return {"success": False, "error": str(e)}
    
    def _call_claude_direct(self, question: str, context: str, expert_prompt: str) -> Dict[str, Any]:
        """
        Call Claude via LLMOrchestrator.
        
        This method is kept for backward compatibility but now delegates to orchestrator.
        """
        if not self._orchestrator:
            logger.warning("[CONSULTATIVE] LLMOrchestrator not available for Claude call")
            return {"success": False, "error": "No orchestrator"}
        
        try:
            prompt = f"""{expert_prompt}

QUESTION: {question}

DATA:
{context}

Provide a direct answer based ONLY on the data above."""

            result = self._orchestrator.synthesize_answer(
                question=prompt,
                context="",
                use_claude_fallback=True
            )
            
            if result.get('success') and result.get('response'):
                logger.warning(f"[CONSULTATIVE] Claude via orchestrator succeeded ({len(result['response'])} chars)")
                return {
                    "success": True,
                    "response": result['response'].strip(),
                    "model_used": result.get('model_used', 'claude-via-orchestrator')
                }
            
            return {"success": False, "error": result.get('error', 'Unknown error')}
            
        except Exception as e:
            logger.error(f"[CONSULTATIVE] Claude call failed: {e}")
            return {"success": False, "error": str(e)}
    
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
    
    logger.debug("=" * 60)
    logger.debug("CONSULTATIVE ANSWER:")
    logger.debug("=" * 60)
    logger.debug(f"Debug output: {result.answer}")
    logger.debug("=" * 60)
    logger.debug(f"Confidence: {result.confidence:.1%}")
    logger.debug(f"Method: {result.synthesis_method}")
    logger.debug(f"Actions: {result.recommended_actions}")
