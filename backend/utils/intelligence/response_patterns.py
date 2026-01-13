"""
XLR8 Intelligence Engine - Consultative Response Patterns
==========================================================
Phase 3.4: Response Templates and Patterns

Templates and patterns for generating consultative responses.
These ensure responses read like a senior consultant wrote them.

Response Structure:
1. Direct Answer (1-2 sentences) - Answer the question with data
2. Supporting Detail (2-4 sentences) - Context from truths
3. Gaps/Recommendations (if any) - What's missing or concerning
4. Citations (brief) - Source documents referenced

Deploy to: backend/utils/intelligence/response_patterns.py
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .truth_assembler import TruthContext, Gap

logger = logging.getLogger(__name__)


# =============================================================================
# RESPONSE STRUCTURE
# =============================================================================

@dataclass
class ResponseSection:
    """A section of the response."""
    name: str
    content: str
    priority: int = 1  # Lower = more important
    
    def is_empty(self) -> bool:
        return not self.content or len(self.content.strip()) == 0


@dataclass
class ConsultativeResponse:
    """
    Structured consultative response.
    
    Contains all sections needed for a professional response.
    """
    direct_answer: str
    supporting_detail: str = ""
    gaps_section: str = ""
    recommendations: List[str] = None
    citations: List[str] = None
    proactive_offers: List[str] = None
    
    def to_markdown(self) -> str:
        """Render as markdown."""
        parts = []
        
        # Direct answer (always first)
        parts.append(self.direct_answer)
        
        # Supporting detail
        if self.supporting_detail:
            parts.append("")
            parts.append(self.supporting_detail)
        
        # Gaps section
        if self.gaps_section:
            parts.append("")
            parts.append("**Findings:**")
            parts.append(self.gaps_section)
        
        # Recommendations
        if self.recommendations:
            parts.append("")
            parts.append("**Recommendations:**")
            for rec in self.recommendations[:3]:
                parts.append(f"- {rec}")
        
        # Citations
        if self.citations:
            parts.append("")
            parts.append("---")
            parts.append(f"*Sources: {', '.join(self.citations[:3])}*")
        
        # Proactive offers
        if self.proactive_offers:
            parts.append("")
            parts.append("**Next Steps:**")
            for offer in self.proactive_offers[:3]:
                parts.append(f"- {offer}")
        
        return "\n".join(parts)


# =============================================================================
# RESPONSE TEMPLATES BY QUERY TYPE
# =============================================================================

RESPONSE_TEMPLATES = {
    'count': """**{count:,} {entity}** match your criteria.

{breakdown}

{gap_section}""",

    'list': """Found **{count:,} {entity}** matching your query.

{sample_table}

{context_section}

{gap_section}""",

    'compare': """**Comparison: {dimension}**

{comparison_table}

**Key Findings:**
{findings}

{gap_section}""",

    'validate': """**Validation Result: {status}**

{details}

**Issues Found:**
{issues}

**Recommendations:**
{recommendations}""",

    'gap_analysis': """**Gap Analysis: {topic}**

| Truth | Status | Details |
|-------|--------|---------|
{truth_status_table}

**Recommended Actions:**
{recommendations}""",

    'workforce': """**Workforce Analysis**

**Current Active Headcount:** {active_count:,}

{breakdown}

{gap_section}

**Next Steps:**
{next_steps}""",

    'configuration': """**{entity_type} Configuration**

Found **{count:,}** configured {entity_type}.

{details}

{breakdown}

{gap_section}""",

    'default': """Based on the uploaded data, {answer}

{context}

{gap_section}

{next_steps}""",
}


# =============================================================================
# TONE GUIDELINES
# =============================================================================

TONE_RULES = {
    # DO
    'be_specific': "Use exact numbers: '127 employees' not 'many employees'",
    'be_direct': "Answer first, explain second",
    'be_helpful': "Suggest next steps when appropriate",
    'acknowledge_limits': "Say 'Based on the uploaded data...' when appropriate",
    
    # DON'T
    'no_hedging': "Avoid 'It appears that...' when data is clear",
    'no_jargon': "Avoid unexplained technical terms",
    'no_assumptions': "Don't assume context not in the data",
    'no_repetition': "Don't repeat the question back",
}


# Phrases to avoid
AVOID_PHRASES = [
    "Based on my analysis",  # Use "Based on the data"
    "It appears that",       # Be direct
    "It seems like",         # Be direct
    "I think",               # Be factual
    "In my opinion",         # Be factual
    "As you can see",        # Not conversational
    "Obviously",             # Condescending
    "Simply put",            # Condescending
    "Basically",             # Filler
]


# =============================================================================
# RESPONSE FORMATTER
# =============================================================================

class ResponseFormatter:
    """
    Format responses using templates and tone guidelines.
    
    Ensures all responses follow consultative patterns.
    """
    
    def __init__(self):
        self.templates = RESPONSE_TEMPLATES
        logger.info("[FORMATTER] ResponseFormatter initialized")
    
    def format(self, 
               context: TruthContext,
               llm_response: str = None,
               template_type: str = None) -> ConsultativeResponse:
        """
        Format a consultative response.
        
        Can use either:
        - LLM response as the base (with cleanup)
        - Template-based generation from context
        
        Args:
            context: Assembled TruthContext
            llm_response: Optional raw LLM response to format
            template_type: Override template selection
            
        Returns:
            ConsultativeResponse ready for rendering
        """
        # Determine template type
        if template_type:
            t_type = template_type
        else:
            t_type = self._select_template_type(context)
        
        # Build response sections
        if llm_response:
            # Clean up LLM response
            direct_answer = self._clean_llm_response(llm_response, context)
            supporting_detail = ""  # LLM already included detail
        else:
            # Generate from template
            direct_answer, supporting_detail = self._generate_from_template(
                context, t_type
            )
        
        # Build gaps section
        gaps_section = self._format_gaps(context.gaps)
        
        # Build recommendations
        recommendations = self._build_recommendations(context)
        
        # Build citations
        citations = self._build_citations(context)
        
        # Build proactive offers
        proactive_offers = self._build_proactive_offers(context)
        
        return ConsultativeResponse(
            direct_answer=direct_answer,
            supporting_detail=supporting_detail,
            gaps_section=gaps_section,
            recommendations=recommendations,
            citations=citations,
            proactive_offers=proactive_offers,
        )
    
    def _select_template_type(self, context: TruthContext) -> str:
        """Select template based on context."""
        intent_type = context.intent_type
        
        type_mapping = {
            'count': 'count',
            'sum': 'count',
            'average': 'count',
            'list': 'list',
            'compare': 'compare',
            'validate': 'validate',
            'group': 'list',
            'superlative': 'list',
        }
        
        # Check for special cases
        if context.domain in ['employees', 'workforce']:
            return 'workforce'
        
        if context.domain in ['earnings', 'deductions', 'taxes', 'locations', 'jobs']:
            return 'configuration'
        
        return type_mapping.get(intent_type, 'default')
    
    def _clean_llm_response(self, response: str, context: TruthContext) -> str:
        """Clean up LLM response."""
        cleaned = response
        
        # Remove phrases to avoid
        for phrase in AVOID_PHRASES:
            cleaned = cleaned.replace(phrase, "")
        
        # Clean up extra whitespace
        cleaned = " ".join(cleaned.split())
        
        # Ensure starts with capital
        if cleaned:
            cleaned = cleaned[0].upper() + cleaned[1:]
        
        return cleaned
    
    def _generate_from_template(self, context: TruthContext, 
                                t_type: str) -> tuple:
        """Generate response from template."""
        template = self.templates.get(t_type, self.templates['default'])
        
        # Build template variables
        vars = {}
        
        # Count/entity info
        vars['count'] = context.reality.row_count
        vars['entity'] = context.domain or 'records'
        vars['entity_type'] = context.domain.title() if context.domain else 'Configuration'
        
        # Answer for default template
        if context.reality.row_count > 0:
            vars['answer'] = f"found {context.reality.row_count:,} {context.domain} records"
        else:
            vars['answer'] = f"no {context.domain} data was found"
        
        # Breakdown if we have aggregates
        if context.reality.aggregates:
            breakdown_parts = []
            for k, v in context.reality.aggregates.items():
                if isinstance(v, (int, float)):
                    breakdown_parts.append(f"- {k}: {v:,}")
            vars['breakdown'] = "\n".join(breakdown_parts) if breakdown_parts else ""
        else:
            vars['breakdown'] = ""
        
        # Sample table
        if context.reality.sample_data:
            vars['sample_table'] = self._format_sample_table(
                context.reality.sample_data[:5],
                context.reality.column_names
            )
        else:
            vars['sample_table'] = "No sample data available."
        
        # Details
        vars['details'] = context.reality.to_prompt_section(max_rows=5)
        
        # Context section
        context_parts = []
        if not context.reference.is_empty():
            context_parts.append("Best practices suggest: " + 
                               context.reference.relevant_guidance[0][:200])
        if not context.regulatory.is_empty():
            context_parts.append("Regulatory note: " +
                               context.regulatory.relevant_requirements[0][:200])
        vars['context_section'] = "\n\n".join(context_parts) if context_parts else ""
        vars['context'] = vars['context_section']
        
        # Gap section (placeholder, filled separately)
        vars['gap_section'] = ""
        
        # Next steps
        vars['next_steps'] = ""
        
        # Other placeholders
        vars['dimension'] = context.domain
        vars['comparison_table'] = ""
        vars['findings'] = ""
        vars['topic'] = context.domain
        vars['status'] = "Review Required" if context.gaps else "Complete"
        vars['issues'] = ""
        vars['recommendations'] = ""
        vars['truth_status_table'] = ""
        vars['active_count'] = context.reality.row_count
        
        try:
            direct_answer = template.format(**vars)
        except KeyError as e:
            logger.warning(f"[FORMATTER] Template variable missing: {e}")
            direct_answer = f"Found {context.reality.row_count:,} {context.domain} records."
        
        return direct_answer, ""
    
    def _format_sample_table(self, rows: List[Dict], columns: List[str]) -> str:
        """Format rows as markdown table."""
        if not rows:
            return ""
        
        # Use first 5 columns max
        cols = columns[:5] if columns else list(rows[0].keys())[:5]
        
        # Build table
        parts = []
        header = " | ".join(cols)
        parts.append(f"| {header} |")
        parts.append("|" + "---|" * len(cols))
        
        for row in rows[:5]:
            vals = []
            for col in cols:
                v = row.get(col, '')
                if isinstance(v, (int, float)):
                    vals.append(f"{v:,}" if isinstance(v, int) else f"{v:.2f}")
                else:
                    vals.append(str(v)[:30])
            parts.append(f"| {' | '.join(vals)} |")
        
        return "\n".join(parts)
    
    def _format_gaps(self, gaps: List[Gap]) -> str:
        """Format gaps for response."""
        if not gaps:
            return ""
        
        parts = []
        for gap in gaps[:3]:
            severity_icon = {
                'high': '⚠️',
                'medium': '⚡',
                'low': 'ℹ️'
            }.get(gap.severity, '•')
            parts.append(f"{severity_icon} {gap.description}")
        
        if len(gaps) > 3:
            parts.append(f"... and {len(gaps) - 3} more findings")
        
        return "\n".join(parts)
    
    def _build_recommendations(self, context: TruthContext) -> List[str]:
        """Build list of recommendations."""
        recs = []
        
        # From gaps
        for gap in context.gaps[:3]:
            if gap.recommendation:
                recs.append(gap.recommendation)
        
        # Generic recommendations based on context
        if context.reality.is_empty():
            recs.append(f"Upload {context.domain} data for analysis")
        
        if context.reference.is_empty() and context.domain:
            recs.append(f"Upload {context.domain} best practice documentation")
        
        return recs
    
    def _build_citations(self, context: TruthContext) -> List[str]:
        """Build list of source citations."""
        sources = []
        
        # From intent
        for doc in context.intent.source_documents[:2]:
            if doc not in sources:
                sources.append(doc)
        
        # From reference
        for doc in context.reference.source_documents[:2]:
            if doc not in sources:
                sources.append(doc)
        
        # From regulatory
        for doc in context.regulatory.source_documents[:2]:
            if doc not in sources:
                sources.append(doc)
        
        return sources
    
    def _build_proactive_offers(self, context: TruthContext) -> List[str]:
        """Build list of proactive next steps."""
        offers = []
        
        domain = context.domain or 'data'
        
        # Based on query type
        if context.intent_type == 'count':
            offers.append(f"\"Show me {domain} breakdown by category\" to see distribution")
            offers.append(f"\"List all {domain}\" to see details")
        
        elif context.intent_type == 'list':
            offers.append(f"\"How many {domain}?\" for a summary count")
            offers.append(f"\"Compare {domain} by category\" for analysis")
        
        elif context.intent_type == 'validate':
            offers.append("\"What's missing?\" for gap analysis")
            offers.append("\"Show compliance issues\" for detailed review")
        
        else:
            offers.append(f"\"Tell me more about {domain}\" to drill down")
            offers.append("\"What should I check next?\" for guided review")
        
        return offers


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_formatter_instance: Optional[ResponseFormatter] = None

def get_formatter() -> ResponseFormatter:
    """Get the singleton formatter instance."""
    global _formatter_instance
    if _formatter_instance is None:
        _formatter_instance = ResponseFormatter()
    return _formatter_instance


def format_response(context: TruthContext, 
                    llm_response: str = None,
                    template_type: str = None) -> ConsultativeResponse:
    """Convenience function to format a response."""
    formatter = get_formatter()
    return formatter.format(context, llm_response, template_type)


def render_response(context: TruthContext,
                    llm_response: str = None) -> str:
    """Format and render to markdown."""
    response = format_response(context, llm_response)
    return response.to_markdown()
