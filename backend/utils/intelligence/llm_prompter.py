"""
XLR8 Intelligence Engine - Local LLM Prompter
==============================================
Phase 3.2: Local LLM Prompt Engineering

Optimizes prompts for local LLMs (Mistral, DeepSeek) with:
- Context window management (4096 tokens)
- Priority-based truncation
- Structured Five Truths format
- Response quality validation

Model Selection:
- DeepSeek: SQL explanation, technical queries
- Mistral: Synthesis, consultative responses
- Claude API: Complex reasoning (fallback)

Deploy to: backend/utils/intelligence/llm_prompter.py
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .truth_assembler import TruthContext, Gap

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

# Approximate token limits for local LLMs
MAX_CONTEXT_TOKENS = {
    'mistral': 4096,
    'deepseek': 4096,
    'claude': 100000,
}

# Approximate chars per token (rough estimate)
CHARS_PER_TOKEN = 4

# Priority order for truncation (1 = never truncate, higher = truncate first)
SECTION_PRIORITY = {
    'question': 1,      # Never truncate
    'reality': 2,       # Essential data
    'regulatory': 3,    # Compliance context
    'gaps': 3,          # Important findings
    'reference': 4,     # Best practices
    'intent': 5,        # Customer context
    'configuration': 5, # System settings
}


# =============================================================================
# PROMPT TEMPLATES
# =============================================================================

SYNTHESIS_PROMPT_TEMPLATE = """You are a senior implementation consultant analyzing enterprise data.

## QUESTION
{question}

## WHAT THE DATA SHOWS (Reality)
{reality_section}

## CUSTOMER REQUIREMENTS (Intent)
{intent_section}

## BEST PRACTICES (Reference)
{reference_section}

## COMPLIANCE REQUIREMENTS (Regulatory)
{regulatory_section}

## GAPS DETECTED
{gaps_section}

## YOUR TASK
Provide a consultative response that:
1. Directly answers the question using the data
2. Highlights any gaps between configuration and best practices
3. Notes compliance considerations if relevant
4. Suggests next steps if appropriate

RESPONSE RULES:
- Be factual - cite specific numbers from the data
- Be consultative - like a trusted advisor, not a data dump
- Be actionable - if there are issues, suggest fixes
- Be concise - answer the question directly first
- Never invent data - only use what's provided
- Say "Based on the uploaded data" when appropriate

Response:"""


COUNT_PROMPT_TEMPLATE = """You are analyzing enterprise data for a client.

QUESTION: {question}

DATA RESULT:
{reality_section}

CONTEXT:
{context_section}

Provide a brief, professional response that:
1. States the count clearly
2. Notes any relevant breakdowns
3. Offers to drill down if useful

Response:"""


VALIDATION_PROMPT_TEMPLATE = """You are a compliance consultant validating configuration.

QUESTION: {question}

CURRENT CONFIGURATION:
{reality_section}

REGULATORY REQUIREMENTS:
{regulatory_section}

BEST PRACTICES:
{reference_section}

GAPS DETECTED:
{gaps_section}

Analyze the configuration against requirements and provide:
1. Compliance status (compliant/needs review/non-compliant)
2. Specific issues found
3. Recommended actions

Response:"""


GAP_ANALYSIS_PROMPT_TEMPLATE = """You are conducting a gap analysis.

TOPIC: {question}

CURRENT STATE (Reality):
{reality_section}

INTENDED STATE (Intent):
{intent_section}

BEST PRACTICES (Reference):
{reference_section}

REGULATORY REQUIREMENTS:
{regulatory_section}

GAPS IDENTIFIED:
{gaps_section}

Provide a structured gap analysis:
1. Summary of current vs intended state
2. Risk assessment for each gap
3. Priority recommendations

Response:"""


# =============================================================================
# RESPONSE QUALITY CHECKLIST
# =============================================================================

@dataclass
class ResponseQuality:
    """Quality assessment of a synthesized response."""
    direct_answer: bool = False      # Actually answers the question
    data_citation: bool = False      # References specific numbers
    context_usage: bool = False      # Uses truth context
    actionable_insight: bool = False # Suggests next steps
    appropriate_length: bool = False # Not too short or long
    no_hallucination: bool = False   # Only uses provided data
    
    @property
    def score(self) -> float:
        """Calculate quality score 0-1."""
        checks = [
            self.direct_answer,
            self.data_citation,
            self.context_usage,
            self.actionable_insight,
            self.appropriate_length,
            self.no_hallucination,
        ]
        return sum(checks) / len(checks)
    
    @property
    def is_acceptable(self) -> bool:
        """Check if response meets minimum quality."""
        # Must have direct answer and no hallucination at minimum
        return self.direct_answer and self.no_hallucination


# =============================================================================
# LOCAL LLM PROMPTER
# =============================================================================

class LocalLLMPrompter:
    """
    Optimize prompts for local LLM constraints.
    
    Handles context window limits, priority-based truncation,
    and template selection based on query type.
    """
    
    def __init__(self, model: str = 'mistral'):
        self.model = model
        self.max_tokens = MAX_CONTEXT_TOKENS.get(model, 4096)
        self.max_chars = self.max_tokens * CHARS_PER_TOKEN
        logger.info(f"[PROMPTER] Initialized for {model} (max {self.max_tokens} tokens)")
    
    def build_prompt(self, context: TruthContext) -> str:
        """
        Build optimized prompt from TruthContext.
        
        Selects appropriate template and fits content to context window.
        """
        # Select template based on intent type
        template = self._select_template(context.intent_type)
        
        # Build sections with priority-based truncation
        sections = self._build_sections(context)
        
        # Optimize to fit context window
        optimized_sections = self._optimize_for_context(sections)
        
        # Fill template
        prompt = self._fill_template(template, context.question, optimized_sections)
        
        logger.info(f"[PROMPTER] Built prompt: {len(prompt)} chars for {context.intent_type}")
        
        return prompt
    
    def _select_template(self, intent_type: str) -> str:
        """Select prompt template based on intent type."""
        templates = {
            'count': COUNT_PROMPT_TEMPLATE,
            'sum': COUNT_PROMPT_TEMPLATE,
            'average': COUNT_PROMPT_TEMPLATE,
            'validate': VALIDATION_PROMPT_TEMPLATE,
            'compare': GAP_ANALYSIS_PROMPT_TEMPLATE,
            'gap_analysis': GAP_ANALYSIS_PROMPT_TEMPLATE,
        }
        return templates.get(intent_type, SYNTHESIS_PROMPT_TEMPLATE)
    
    def _build_sections(self, context: TruthContext) -> Dict[str, str]:
        """Build all prompt sections from context."""
        sections = {}
        
        # Reality section
        if context.reality and not context.reality.is_empty():
            sections['reality'] = context.reality.to_prompt_section(max_rows=15)
        else:
            sections['reality'] = "No data available."
        
        # Intent section
        if context.intent and not context.intent.is_empty():
            sections['intent'] = context.intent.to_prompt_section()
        else:
            sections['intent'] = "No customer requirements found."
        
        # Reference section
        if context.reference and not context.reference.is_empty():
            sections['reference'] = context.reference.to_prompt_section()
        else:
            sections['reference'] = "No best practices found."
        
        # Regulatory section
        if context.regulatory and not context.regulatory.is_empty():
            sections['regulatory'] = context.regulatory.to_prompt_section()
        else:
            sections['regulatory'] = "No regulatory requirements found."
        
        # Gaps section
        if context.gaps:
            sections['gaps'] = self._format_gaps(context.gaps)
        else:
            sections['gaps'] = "No gaps detected."
        
        # Context section (combined for simple templates)
        context_parts = []
        if context.intent and not context.intent.is_empty():
            context_parts.append(f"Customer Intent: {context.intent.to_prompt_section()}")
        if context.reference and not context.reference.is_empty():
            context_parts.append(f"Best Practices: {context.reference.to_prompt_section()}")
        sections['context'] = "\n\n".join(context_parts) if context_parts else "No additional context."
        
        return sections
    
    def _format_gaps(self, gaps: List[Gap]) -> str:
        """Format gaps for prompt."""
        if not gaps:
            return "No gaps detected."
        
        parts = []
        for i, gap in enumerate(gaps[:5], 1):  # Limit to 5 gaps
            severity_icon = {'high': '⚠️', 'medium': '⚡', 'low': 'ℹ️'}.get(gap.severity, '•')
            parts.append(f"{severity_icon} {gap.description}")
            if gap.recommendation:
                parts.append(f"   → {gap.recommendation}")
        
        if len(gaps) > 5:
            parts.append(f"\n... and {len(gaps) - 5} more gaps")
        
        return "\n".join(parts)
    
    def _optimize_for_context(self, sections: Dict[str, str]) -> Dict[str, str]:
        """
        Optimize sections to fit within context window.
        
        Truncates lower-priority sections first.
        """
        total_chars = sum(len(s) for s in sections.values())
        
        # If within limits, return as-is
        if total_chars <= self.max_chars * 0.8:  # Leave 20% headroom for template
            return sections
        
        logger.warning(f"[PROMPTER] Content too long ({total_chars} chars), truncating")
        
        # Sort sections by priority (higher number = truncate first)
        sorted_sections = sorted(
            sections.items(),
            key=lambda x: SECTION_PRIORITY.get(x[0], 5),
            reverse=True
        )
        
        # Truncate until we fit
        target_chars = int(self.max_chars * 0.7)
        for section_name, content in sorted_sections:
            total_chars = sum(len(s) for s in sections.values())
            if total_chars <= target_chars:
                break
            
            # Skip essential sections
            if SECTION_PRIORITY.get(section_name, 5) <= 2:
                continue
            
            # Truncate this section
            current_len = len(content)
            if current_len > 500:
                # Truncate to 30% with ellipsis
                truncate_to = int(current_len * 0.3)
                sections[section_name] = content[:truncate_to] + "\n... (truncated)"
                logger.debug(f"[PROMPTER] Truncated {section_name}: {current_len} → {truncate_to}")
        
        return sections
    
    def _fill_template(self, template: str, question: str, 
                       sections: Dict[str, str]) -> str:
        """Fill template with sections."""
        return template.format(
            question=question,
            reality_section=sections.get('reality', 'No data.'),
            intent_section=sections.get('intent', 'No requirements.'),
            reference_section=sections.get('reference', 'No guidance.'),
            regulatory_section=sections.get('regulatory', 'No requirements.'),
            gaps_section=sections.get('gaps', 'No gaps.'),
            context_section=sections.get('context', 'No context.'),
        )
    
    def count_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        return len(text) // CHARS_PER_TOKEN
    
    def validate_response(self, response: str, context: TruthContext) -> ResponseQuality:
        """
        Validate response quality.
        
        Checks that the response meets quality standards.
        """
        quality = ResponseQuality()
        
        response_lower = response.lower()
        
        # Check direct answer
        # For count queries, should have a number
        if context.intent_type == 'count':
            quality.direct_answer = any(c.isdigit() for c in response)
        else:
            # For other queries, should be substantive
            quality.direct_answer = len(response) > 50
        
        # Check data citation
        if context.reality and context.reality.row_count > 0:
            # Should mention row count or specific values
            quality.data_citation = (
                str(context.reality.row_count) in response or
                any(str(v) in response for row in context.reality.sample_data[:3]
                    for v in row.values() if isinstance(v, (int, float)))
            )
        else:
            quality.data_citation = True  # N/A if no data
        
        # Check context usage
        quality.context_usage = (
            'best practice' in response_lower or
            'requirement' in response_lower or
            'recommend' in response_lower or
            'compliance' in response_lower or
            context.has_context  # At least have context available
        )
        
        # Check for actionable insight
        quality.actionable_insight = (
            'suggest' in response_lower or
            'recommend' in response_lower or
            'next step' in response_lower or
            'consider' in response_lower or
            'should' in response_lower
        )
        
        # Check length
        quality.appropriate_length = 50 <= len(response) <= 3000
        
        # Check no hallucination (rough check)
        # Should reference "based on" or "data shows" for data claims
        quality.no_hallucination = (
            'based on' in response_lower or
            'data shows' in response_lower or
            'found' in response_lower or
            'no data' in response_lower or
            len(response) < 200  # Short responses less likely to hallucinate
        )
        
        return quality


# =============================================================================
# SPECIALIZED PROMPT BUILDERS
# =============================================================================

def build_sql_explanation_prompt(sql: str, question: str, 
                                  columns: List[str] = None) -> str:
    """
    Build prompt for SQL explanation (DeepSeek optimized).
    
    Used to explain generated SQL in human terms.
    """
    col_info = f"\nAvailable columns: {', '.join(columns[:10])}" if columns else ""
    
    return f"""Explain this SQL query in plain English.

QUESTION: {question}

SQL:
```sql
{sql}
```
{col_info}

Explain briefly (2-3 sentences) what this query does and what results it will return.
Focus on the business meaning, not technical details.

Explanation:"""


def build_gap_explanation_prompt(gap: Gap, context: TruthContext) -> str:
    """
    Build prompt for gap explanation (Mistral optimized).
    
    Used to generate consultative explanations of detected gaps.
    """
    return f"""You are a senior consultant explaining a configuration gap to a client.

GAP DETECTED:
Type: {gap.gap_type}
Severity: {gap.severity}
Topic: {gap.topic}
Description: {gap.description}

CONTEXT:
{context.reference.to_prompt_section() if context.reference else 'No best practices available.'}

Write a brief (2-3 sentences) consultative explanation of this gap that:
1. Explains why this matters
2. Suggests what to do about it

Explanation:"""


def build_followup_prompt(question: str, previous_response: str,
                          followup: str) -> str:
    """
    Build prompt for follow-up questions.
    
    Maintains context from previous interaction.
    """
    return f"""PREVIOUS QUESTION: {question}

PREVIOUS RESPONSE:
{previous_response[:1000]}

FOLLOW-UP QUESTION: {followup}

Provide a brief response to the follow-up question, building on the previous context.

Response:"""


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_prompter_instance: Optional[LocalLLMPrompter] = None

def get_prompter(model: str = 'mistral') -> LocalLLMPrompter:
    """Get a prompter instance."""
    global _prompter_instance
    if _prompter_instance is None or _prompter_instance.model != model:
        _prompter_instance = LocalLLMPrompter(model)
    return _prompter_instance


def build_synthesis_prompt(context: TruthContext, model: str = 'mistral') -> str:
    """Convenience function to build synthesis prompt."""
    prompter = get_prompter(model)
    return prompter.build_prompt(context)
