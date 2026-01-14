"""
XLR8 Resolution Response - Honest Failure Handling
===================================================

This module provides structured responses for when the deterministic path
cannot resolve a query. Instead of returning None (which triggers garbage
LLM fallback), we return honest, helpful failure messages.

PRINCIPLE: Honest Failure > Silent Garbage

Three response types:
1. CANNOT_RESOLVE - We don't understand the query
2. NEEDS_CLARIFICATION - We need more information  
3. NO_DATA - We understood but found nothing

Author: XLR8 Team
Version: 1.0.0
Date: 2026-01-14
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from .types import SynthesizedAnswer, Truth

logger = logging.getLogger(__name__)


class ResolutionStatus(Enum):
    """Why we couldn't resolve the query."""
    SUCCESS = "success"
    CANNOT_RESOLVE = "cannot_resolve"      # Don't understand the terms
    NEEDS_CLARIFICATION = "needs_clarification"  # Ambiguous, need user input
    NO_DATA = "no_data"                    # Understood but found nothing
    COMPLEX_QUERY = "complex_query"        # Needs full pipeline (ChromaDB, etc.)
    SYSTEM_ERROR = "system_error"          # Technical failure


@dataclass  
class ResolutionFailure:
    """
    Structured failure information.
    
    Contains everything needed to:
    1. Tell the user what went wrong
    2. Suggest how to fix it
    3. Provide debugging context
    """
    status: ResolutionStatus
    reason: str
    suggestions: List[str]
    unresolved_terms: List[str] = None
    available_tables: List[str] = None
    available_columns: List[str] = None
    context: Dict[str, Any] = None


def build_cannot_resolve_response(
    question: str,
    reason: str,
    unresolved_terms: List[str] = None,
    suggestions: List[str] = None,
    available_columns: List[str] = None,
    context: Dict = None
) -> SynthesizedAnswer:
    """
    Build a response when we cannot resolve terms in the query.
    
    Args:
        question: The original question
        reason: Why we couldn't resolve
        unresolved_terms: Terms we couldn't map to columns
        suggestions: Suggested alternatives
        available_columns: List of valid columns for context
        context: Additional debugging context
        
    Returns:
        SynthesizedAnswer with helpful failure information
    """
    suggestions = suggestions or []
    unresolved_terms = unresolved_terms or []
    
    # Build a helpful answer message
    if unresolved_terms:
        terms_str = ", ".join(f"'{t}'" for t in unresolved_terms[:5])
        answer = f"I couldn't resolve these terms to database columns: {terms_str}.\n\n"
    else:
        answer = f"I couldn't understand what you're asking for.\n\n"
    
    answer += f"**Reason**: {reason}\n\n"
    
    if suggestions:
        answer += "**Did you mean one of these?**\n"
        for s in suggestions[:5]:
            answer += f"- {s}\n"
        answer += "\n"
    
    if available_columns:
        sample_cols = available_columns[:10]
        answer += f"**Available columns include**: {', '.join(sample_cols)}"
        if len(available_columns) > 10:
            answer += f" (and {len(available_columns) - 10} more)"
        answer += "\n\n"
    
    answer += "Try rephrasing your question or use more specific terms."
    
    return SynthesizedAnswer(
        question=question,
        answer=answer,
        confidence=0.0,  # Zero confidence = honest failure
        reasoning=[
            "DETERMINISTIC PATH: Cannot resolve",
            f"Unresolved terms: {unresolved_terms}",
            f"Reason: {reason}",
            "OLD PATH DISABLED - no LLM fallback"
        ],
        structured_output={
            'type': 'resolution_failure',
            'status': ResolutionStatus.CANNOT_RESOLVE.value,
            'reason': reason,
            'unresolved_terms': unresolved_terms,
            'suggestions': suggestions,
            'context': context or {}
        }
    )


def build_needs_clarification_response(
    question: str,
    reason: str,
    options: List[Dict[str, Any]],
    clarification_type: str = "term",
    context: Dict = None
) -> SynthesizedAnswer:
    """
    Build a response when we need clarification from the user.
    
    Args:
        question: The original question
        reason: Why we need clarification
        options: List of options to present (each with 'value', 'label', optional 'count')
        clarification_type: Type of clarification needed (term, table, filter)
        context: Additional context
        
    Returns:
        SynthesizedAnswer with clarification request
    """
    answer = f"I need some clarification to answer your question.\n\n"
    answer += f"**{reason}**\n\n"
    
    if options:
        answer += "Please choose one of the following:\n"
        for i, opt in enumerate(options[:10], 1):
            label = opt.get('label', opt.get('value', f'Option {i}'))
            count = opt.get('count')
            if count:
                answer += f"- {label} ({count:,} records)\n"
            else:
                answer += f"- {label}\n"
    
    return SynthesizedAnswer(
        question=question,
        answer=answer,
        confidence=0.0,
        reasoning=[
            "DETERMINISTIC PATH: Needs clarification",
            f"Clarification type: {clarification_type}",
            f"Reason: {reason}",
            f"Options presented: {len(options)}"
        ],
        structured_output={
            'type': 'needs_clarification',
            'status': ResolutionStatus.NEEDS_CLARIFICATION.value,
            'clarification_type': clarification_type,
            'reason': reason,
            'options': options,
            'context': context or {}
        }
    )


def build_no_data_response(
    question: str,
    sql: str,
    filters_applied: List[Dict],
    table_name: str,
    context: Dict = None
) -> SynthesizedAnswer:
    """
    Build a response when query was valid but returned no data.
    
    Args:
        question: The original question
        sql: The SQL that was executed
        filters_applied: List of filters that were applied
        table_name: The table that was queried
        context: Additional context
        
    Returns:
        SynthesizedAnswer explaining no data was found
    """
    answer = f"I understood your question and ran the query, but **no matching data was found**.\n\n"
    
    if filters_applied:
        answer += "**Filters applied**:\n"
        for f in filters_applied[:5]:
            if isinstance(f, dict):
                col = f.get('column', f.get('column_name', 'unknown'))
                op = f.get('operator', '=')
                val = f.get('value', f.get('match_value', ''))
                answer += f"- {col} {op} '{val}'\n"
            else:
                answer += f"- {f}\n"
        answer += "\n"
    
    answer += "**Suggestions**:\n"
    answer += "- Check if the filter values are correct\n"
    answer += "- Try broader criteria\n"
    answer += f"- Verify data exists in {table_name}\n"
    
    return SynthesizedAnswer(
        question=question,
        answer=answer,
        confidence=0.5,  # Medium confidence - we understood, just no data
        executed_sql=sql,
        reasoning=[
            "DETERMINISTIC PATH: No data found",
            f"Table: {table_name}",
            f"Filters: {len(filters_applied)} applied",
            "Query executed successfully but returned 0 rows"
        ],
        structured_output={
            'type': 'no_data',
            'status': ResolutionStatus.NO_DATA.value,
            'sql': sql,
            'table': table_name,
            'filters': filters_applied,
            'context': context or {}
        }
    )


def build_complex_query_response(
    question: str,
    reason: str,
    required_sources: List[str] = None,
    context: Dict = None
) -> SynthesizedAnswer:
    """
    Build a response for complex queries that need full pipeline.
    
    This is used for queries that genuinely need:
    - Reference documentation (ChromaDB)
    - Regulatory information
    - Compliance checking
    - Multi-truth analysis
    
    Args:
        question: The original question
        reason: Why this needs full pipeline
        required_sources: List of truth types needed
        context: Additional context
        
    Returns:
        SynthesizedAnswer indicating complex query handling needed
    """
    required_sources = required_sources or ['reference', 'regulatory']
    
    answer = f"This question requires analysis beyond simple data lookup.\n\n"
    answer += f"**Reason**: {reason}\n\n"
    answer += f"**Sources needed**: {', '.join(required_sources)}\n\n"
    answer += "Processing with full analysis pipeline...\n"
    
    return SynthesizedAnswer(
        question=question,
        answer=answer,
        confidence=0.0,  # Signal to continue with full pipeline
        reasoning=[
            "DETERMINISTIC PATH: Complex query detected",
            f"Reason: {reason}",
            f"Required sources: {required_sources}",
            "Deferring to full pipeline"
        ],
        structured_output={
            'type': 'complex_query',
            'status': ResolutionStatus.COMPLEX_QUERY.value,
            'reason': reason,
            'required_sources': required_sources,
            'context': context or {}
        }
    )


def build_system_error_response(
    question: str,
    error: str,
    component: str = "unknown",
    context: Dict = None
) -> SynthesizedAnswer:
    """
    Build a response for system/technical errors.
    
    Args:
        question: The original question
        error: Error message
        component: Which component failed
        context: Additional context
        
    Returns:
        SynthesizedAnswer with error information
    """
    answer = f"I encountered a technical error while processing your question.\n\n"
    answer += f"**Error**: {error}\n\n"
    answer += f"**Component**: {component}\n\n"
    answer += "Please try again or rephrase your question.\n"
    
    return SynthesizedAnswer(
        question=question,
        answer=answer,
        confidence=0.0,
        reasoning=[
            "DETERMINISTIC PATH: System error",
            f"Component: {component}",
            f"Error: {error}",
            "OLD PATH DISABLED - no fallback"
        ],
        structured_output={
            'type': 'system_error',
            'status': ResolutionStatus.SYSTEM_ERROR.value,
            'error': error,
            'component': component,
            'context': context or {}
        }
    )


def get_fuzzy_suggestions(term: str, available_terms: List[str], max_suggestions: int = 5) -> List[str]:
    """
    Get fuzzy match suggestions for an unresolved term.
    
    Uses simple string matching - no external dependencies.
    
    Args:
        term: The term that couldn't be resolved
        available_terms: List of valid terms to match against
        max_suggestions: Maximum number of suggestions to return
        
    Returns:
        List of similar terms
    """
    if not term or not available_terms:
        return []
    
    term_lower = term.lower().replace('_', ' ').replace('-', ' ')
    term_words = set(term_lower.split())
    
    scored = []
    for available in available_terms:
        avail_lower = available.lower().replace('_', ' ').replace('-', ' ')
        avail_words = set(avail_lower.split())
        
        # Score based on:
        # 1. Substring match
        # 2. Word overlap
        # 3. Starting characters match
        score = 0
        
        if term_lower in avail_lower or avail_lower in term_lower:
            score += 10
        
        common_words = term_words & avail_words
        score += len(common_words) * 5
        
        if avail_lower.startswith(term_lower[:3]) or term_lower.startswith(avail_lower[:3]):
            score += 3
        
        if score > 0:
            scored.append((available, score))
    
    # Sort by score descending
    scored.sort(key=lambda x: -x[1])
    
    return [s[0] for s in scored[:max_suggestions]]
