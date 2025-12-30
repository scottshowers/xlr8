"""
XLR8 Intelligence Engine - Synthesizer
=======================================

Synthesizes responses from all Five Truths into consultative answers.

This is where the magic happens - combining Reality, Intent, Configuration,
Reference, and Regulatory data into actionable insights like a senior consultant.

Deploy to: backend/utils/intelligence/synthesizer.py
"""

import logging
from typing import Dict, List, Optional, Any

from .types import (
    Truth, Conflict, Insight, SynthesizedAnswer, IntelligenceMode
)

logger = logging.getLogger(__name__)


class Synthesizer:
    """
    Synthesizes responses from Five Truths.
    
    Supports two modes:
    1. LLM Synthesis - Uses ConsultativeSynthesizer for intelligent responses
    2. Template Fallback - Formatted response when LLM unavailable
    
    The Five Truths provide full provenance:
    - REALITY: What the data actually shows
    - INTENT: What the customer says they want
    - CONFIGURATION: How they've configured the system
    - REFERENCE: Product docs, implementation standards
    - REGULATORY: Laws, compliance requirements
    """
    
    def __init__(self, llm_synthesizer=None, confirmed_facts: Dict = None,
                 filter_candidates: Dict = None, schema: Dict = None):
        """
        Initialize the synthesizer.
        
        Args:
            llm_synthesizer: ConsultativeSynthesizer instance for LLM synthesis
            confirmed_facts: Dict of confirmed filter facts (status=active, etc.)
            filter_candidates: Dict of filter category → candidates
            schema: Schema metadata for suggestions
        """
        self.llm_synthesizer = llm_synthesizer
        self.confirmed_facts = confirmed_facts or {}
        self.filter_candidates = filter_candidates or {}
        self.schema = schema or {}
        
        # Store last gathered truths for LLM synthesis
        self._last_reality: List[Truth] = []
        self._last_intent: List[Truth] = []
        self._last_configuration: List[Truth] = []
        self._last_reference: List[Truth] = []
        self._last_regulatory: List[Truth] = []
        
        # Track last executed SQL for provenance
        self.last_executed_sql: Optional[str] = None
    
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
        context: Dict = None
    ) -> SynthesizedAnswer:
        """
        Synthesize a consultative answer from all Five Truths.
        
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
            context: Additional context
            
        Returns:
            SynthesizedAnswer with full provenance
        """
        # Store for LLM synthesis
        self._last_reality = reality
        self._last_intent = intent
        self._last_configuration = configuration
        self._last_reference = reference
        self._last_regulatory = regulatory
        
        reasoning = []
        
        # Extract data from reality truths
        data_info = self._extract_data_info(reality)
        reasoning.append(f"Found {len(reality)} data results (Reality)")
        
        # Extract document context
        doc_context = self._build_doc_context(intent, configuration)
        if intent:
            reasoning.append(f"Found {len(intent)} customer intent documents")
        if configuration:
            reasoning.append(f"Found {len(configuration)} configuration documents")
        
        # Extract reference library context
        reflib_context = self._build_reflib_context(reference, regulatory, compliance)
        if reference:
            reasoning.append(f"Found {len(reference)} reference documents")
        if regulatory:
            reasoning.append(f"Found {len(regulatory)} regulatory documents")
        if compliance:
            reasoning.append(f"Found {len(compliance)} compliance documents")
        
        # Generate the response
        answer_text = self._generate_response(
            question=question,
            data_info=data_info,
            doc_context=doc_context,
            reflib_context=reflib_context,
            insights=insights,
            conflicts=conflicts,
            compliance_check=compliance_check
        )
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            reality, intent, configuration, reference, regulatory, compliance
        )
        
        return SynthesizedAnswer(
            question=question,
            answer=answer_text,
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
            structured_output=data_info.get('structured_output'),
            reasoning=reasoning,
            executed_sql=self.last_executed_sql
        )
    
    def _extract_data_info(self, reality: List[Truth]) -> Dict:
        """Extract query results and metadata from reality truths."""
        info = {
            'query_type': 'list',
            'result_value': None,
            'result_rows': [],
            'result_columns': [],
            'data_context': [],
            'structured_output': None
        }
        
        if not reality:
            return info
        
        for truth in reality[:3]:
            if isinstance(truth.content, dict) and 'rows' in truth.content:
                rows = truth.content['rows']
                cols = truth.content['columns']
                query_type = truth.content.get('query_type', 'list')
                
                info['query_type'] = query_type
                info['result_columns'] = cols
                
                if query_type == 'count' and rows:
                    info['result_value'] = list(rows[0].values())[0] if rows[0] else 0
                    info['data_context'].append(f"COUNT RESULT: {info['result_value']}")
                elif query_type in ['sum', 'average'] and rows:
                    info['result_value'] = list(rows[0].values())[0] if rows[0] else 0
                    info['data_context'].append(f"{query_type.upper()} RESULT: {info['result_value']}")
                elif query_type == 'group' and rows:
                    info['result_rows'] = rows[:20]
                    info['data_context'].append(f"Grouped results: {len(rows)} groups")
                else:
                    info['result_rows'] = rows[:20]
                    info['data_context'].append(f"Found {len(rows)} rows with columns: {', '.join(cols[:8])}")
                
                # Build structured output
                info['structured_output'] = {
                    'type': 'data',
                    'sql': truth.content.get('sql'),
                    'rows': info['result_rows'],
                    'columns': info['result_columns'],
                    'total': len(rows)
                }
                break
        
        return info
    
    def _build_doc_context(self, intent: List[Truth], 
                          configuration: List[Truth]) -> List[str]:
        """Build document context from Intent and Configuration truths."""
        context = []
        
        for truth in intent[:2]:
            context.append(f"Customer Intent ({truth.source_name}): {str(truth.content)[:200]}")
        
        for truth in configuration[:2]:
            context.append(f"Configuration ({truth.source_name}): {str(truth.content)[:200]}")
        
        return context
    
    def _build_reflib_context(self, reference: List[Truth], regulatory: List[Truth],
                             compliance: List[Truth]) -> List[str]:
        """Build reference library context."""
        context = []
        
        for truth in reference[:2]:
            context.append(f"Reference ({truth.source_name}): {str(truth.content)[:200]}")
        
        for truth in regulatory[:2]:
            context.append(f"Regulatory ({truth.source_name}): {str(truth.content)[:200]}")
        
        for truth in compliance[:2]:
            context.append(f"Compliance ({truth.source_name}): {str(truth.content)[:200]}")
        
        return context
    
    def _generate_response(
        self,
        question: str,
        data_info: Dict,
        doc_context: List[str],
        reflib_context: List[str],
        insights: List[Insight],
        conflicts: List[Conflict],
        compliance_check: Optional[Dict]
    ) -> str:
        """
        Generate the response text.
        
        Tries LLM synthesis first, falls back to template formatting.
        """
        # Try LLM synthesis first
        if self.llm_synthesizer:
            try:
                structured_data = {
                    'rows': data_info.get('result_rows', []),
                    'columns': data_info.get('result_columns', []),
                    'query_type': data_info.get('query_type', 'list'),
                    'sql': self.last_executed_sql or ''
                }
                
                # Handle count/sum/avg values
                if data_info.get('query_type') in ['count', 'sum', 'average']:
                    if data_info.get('result_value') is not None:
                        structured_data['rows'] = [{'result': data_info['result_value']}]
                        structured_data['columns'] = ['result']
                
                answer = self.llm_synthesizer.synthesize(
                    question=question,
                    reality=self._last_reality,
                    intent=self._last_intent,
                    configuration=self._last_configuration,
                    reference=self._last_reference,
                    regulatory=self._last_regulatory,
                    conflicts=conflicts,
                    insights=insights,
                    structured_data=structured_data
                )
                
                logger.info(f"[SYNTHESIZE] LLM synthesis: method={answer.synthesis_method}")
                return answer.answer
                
            except Exception as e:
                logger.error(f"[SYNTHESIZE] LLM synthesis failed: {e}")
        
        # Fallback to template
        return self._generate_template_response(
            question, data_info, doc_context, reflib_context,
            insights, conflicts, compliance_check
        )
    
    def _generate_template_response(
        self,
        question: str,
        data_info: Dict,
        doc_context: List[str],
        reflib_context: List[str],
        insights: List[Insight],
        conflicts: List[Conflict],
        compliance_check: Optional[Dict]
    ) -> str:
        """Generate template-based response as fallback."""
        parts = []
        
        query_type = data_info.get('query_type', 'list')
        result_value = data_info.get('result_value')
        result_rows = data_info.get('result_rows', [])
        result_columns = data_info.get('result_columns', [])
        
        status_filter = self.confirmed_facts.get('status', '')
        
        # REALITY section
        if query_type == 'count' and result_value is not None:
            try:
                count = int(result_value)
                if status_filter == 'active':
                    parts.append(f"📊 **Reality:** You have **{count:,} active employees**.")
                elif status_filter == 'termed':
                    parts.append(f"📊 **Reality:** Your data shows **{count:,} terminated employees**.")
                else:
                    parts.append(f"📊 **Reality:** Found **{count:,}** matching records.")
            except (ValueError, TypeError):
                parts.append(f"📊 **Reality:** Count = **{result_value}**")
        
        elif query_type in ['sum', 'average'] and result_value is not None:
            try:
                val = float(result_value)
                parts.append(f"📊 **Reality:** {query_type.title()} = **{val:,.2f}**")
            except (ValueError, TypeError):
                parts.append(f"📊 **Reality:** {query_type.title()} = **{result_value}**")
        
        elif query_type == 'group' and result_rows:
            parts.append(f"📊 **Reality:** Breakdown by {result_columns[0] if result_columns else 'category'}:\n")
            parts.extend(self._format_table(result_rows[:15], result_columns[:4]))
            if len(result_rows) > 15:
                parts.append(f"\n*Showing top 15 of {len(result_rows):,} groups*")
        
        elif result_rows:
            parts.append(f"📊 **Reality:** Found **{len(result_rows):,}** matching records\n")
            parts.extend(self._format_table(result_rows[:12], result_columns[:6]))
            if len(result_rows) > 12:
                parts.append(f"\n*Showing first 12 of {len(result_rows):,} results*")
        else:
            parts.append("📊 **Reality:** No data found matching your criteria.")
        
        # Document context sections
        self._add_truth_sections(parts, doc_context, reflib_context)
        
        # Compliance findings
        if compliance_check:
            if compliance_check.get('findings'):
                parts.append("\n\n🚨 **Compliance Findings:**")
                for finding in compliance_check['findings'][:5]:
                    parts.append(f"- {finding}")
            if compliance_check.get('gaps'):
                parts.append("\n\n⚠️ **Compliance Gaps:**")
                for gap in compliance_check['gaps'][:5]:
                    parts.append(f"- {gap}")
        
        # Insights
        if insights:
            parts.append("\n\n---\n💡 **Insights:**")
            for insight in insights[:3]:
                icon = '🔴' if insight.severity == 'high' else '🟡' if insight.severity == 'medium' else '💡'
                parts.append(f"\n{icon} **{insight.title}**: {insight.description}")
        
        # Conflicts
        if conflicts:
            parts.append("\n\n---\n⚖️ **Cross-Truth Analysis:**")
            for conflict in conflicts[:5]:
                icon = '🔴' if conflict.severity in ['critical', 'high'] else '🟡' if conflict.severity == 'medium' else '💡'
                parts.append(f"\n{icon} {conflict.description}")
                if conflict.recommendation:
                    parts.append(f"   → *{conflict.recommendation}*")
        
        return "\n".join(parts)
    
    def _format_table(self, rows: List[Dict], columns: List[str]) -> List[str]:
        """Format rows as a markdown table."""
        if not rows or not columns:
            return []
        
        parts = []
        header = " | ".join(columns)
        parts.append(f"| {header} |")
        parts.append("|" + "---|" * len(columns))
        
        for row in rows:
            vals = []
            for col in columns:
                v = row.get(col, '')
                if isinstance(v, (int, float)) and col.lower() in ['count', 'count(*)', 'total']:
                    vals.append(f"{int(v):,}")
                else:
                    vals.append(str(v)[:30])
            parts.append(f"| {' | '.join(vals)} |")
        
        return parts
    
    def _add_truth_sections(self, parts: List[str], doc_context: List[str],
                          reflib_context: List[str]):
        """Add sections for each truth type."""
        intent_docs = [d for d in doc_context if 'Customer Intent' in d]
        if intent_docs:
            parts.append("\n\n📋 **Customer Intent:**")
            for doc in intent_docs[:2]:
                content = doc.split('): ', 1)[-1] if '): ' in doc else doc
                parts.append(f"- {content[:300]}")
        
        config_docs = [d for d in doc_context if 'Configuration' in d]
        if config_docs:
            parts.append("\n\n⚙️ **Configuration:**")
            for doc in config_docs[:2]:
                content = doc.split('): ', 1)[-1] if '): ' in doc else doc
                parts.append(f"- {content[:300]}")
        
        ref_docs = [d for d in reflib_context if 'Reference' in d]
        if ref_docs:
            parts.append("\n\n📚 **Reference:**")
            for doc in ref_docs[:2]:
                content = doc.split('): ', 1)[-1] if '): ' in doc else doc
                parts.append(f"- {content[:300]}")
        
        reg_docs = [d for d in reflib_context if 'Regulatory' in d]
        if reg_docs:
            parts.append("\n\n⚖️ **Regulatory:**")
            for doc in reg_docs[:2]:
                content = doc.split('): ', 1)[-1] if '): ' in doc else doc
                parts.append(f"- {content[:300]}")
    
    def _calculate_confidence(self, reality, intent, configuration,
                            reference, regulatory, compliance) -> float:
        """Calculate confidence score based on available truths."""
        confidence = 0.5
        if reality:
            confidence += 0.2
        if intent:
            confidence += 0.1
        if configuration:
            confidence += 0.05
        if reference:
            confidence += 0.05
        if regulatory:
            confidence += 0.05
        if compliance:
            confidence += 0.05
        return min(confidence, 0.95)
