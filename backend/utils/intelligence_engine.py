"""
XLR8 INTELLIGENCE ENGINE v5.1
==============================

Deploy to: backend/utils/intelligence_engine.py

UPDATES:
- v5.1: Filter override logic (detects new values even if category already confirmed)
        Location column validation (rejects routing_number, bank fields)
        Stricter state detection (word boundaries, prevents false positives like "many" → NY)
- v5.0: Fixed state detection - no longer requires state code to be in sample values
        Added LLM location filter stripping (data-driven, uses column from filter_candidates)
- v4.9: ARE bug fix (common English word blocklist)

SIMPLIFIED:
- Only asks ONE clarification: active/terminated/all employees
- Only when the question is about employees
- Everything else: just query the data
- LLM used for SQL generation only (where it adds value)
"""

import os
import re
import json
import logging
import requests
from requests.auth import HTTPBasicAuth
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)

# LOAD VERIFICATION - this line proves the new file is loaded
logger.warning("[INTELLIGENCE_ENGINE] ====== v5.1 OVERRIDE + COLUMN VALIDATION ======")


# =============================================================================
# COMMON ENGLISH WORDS BLOCKLIST (ARE BUG FIX)
# Language-level filtering - these words should NEVER be treated as data codes
# even if they match values in the data (e.g., "ARE" is UAE but also "are")
# =============================================================================
COMMON_ENGLISH_BLOCKLIST = {
    # Common verbs
    'are', 'was', 'were', 'been', 'being', 'have', 'has', 'had', 'having',
    'can', 'could', 'may', 'might', 'must', 'shall', 'should', 'will', 'would',
    'get', 'got', 'let', 'put', 'say', 'see', 'use', 'try', 'ask', 'run',
    'set', 'add', 'end', 'own', 'pay', 'cut', 'win', 'hit', 'buy', 'sit',
    'do', 'did', 'does', 'done', 'go', 'goes', 'went', 'gone', 'come', 'came',
    
    # Common nouns/adjectives
    'the', 'and', 'for', 'not', 'all', 'one', 'two', 'new', 'now', 'old',
    'any', 'day', 'way', 'man', 'men', 'our', 'out', 'her', 'him', 'his',
    'who', 'how', 'its', 'job', 'few', 'top', 'low', 'big', 'lot', 'per',
    'each', 'every', 'both', 'many', 'much', 'more', 'most', 'some',
    
    # Question words
    'what', 'when', 'where', 'why', 'which',
    
    # Pronouns  
    'you', 'your', 'they', 'them', 'their', 'she', 'hers', 'we', 'us',
    
    # Prepositions
    'from', 'with', 'into', 'over', 'under', 'after', 'before', 'by', 'at', 'in', 'on', 'to',
    
    # Articles and conjunctions
    'but', 'yet', 'nor', 'so', 'or',
    
    # Common query words
    'total', 'count', 'list', 'show', 'find', 'give', 'tell', 'need',
    'only', 'just', 'also', 'even', 'still', 'again', 'then', 'than',
    'first', 'last', 'next', 'this', 'that', 'these', 'those',
}


def _is_word_boundary_match(text: str, word: str) -> bool:
    """
    Check if word appears in text with word boundaries (not as substring).
    Prevents "are" matching in "compare", etc.
    """
    pattern = r'\b' + re.escape(word) + r'\b'
    return bool(re.search(pattern, text, re.IGNORECASE))


def _is_blocklisted(word: str) -> bool:
    """Check if word is in the common English blocklist."""
    return word.lower() in COMMON_ENGLISH_BLOCKLIST


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Truth:
    """A piece of information from one source of truth."""
    source_type: str
    source_name: str
    content: Any
    confidence: float
    location: str


@dataclass  
class Conflict:
    """A detected conflict between sources of truth."""
    description: str
    reality: Optional[Truth] = None
    intent: Optional[Truth] = None
    best_practice: Optional[Truth] = None
    severity: str = "medium"
    recommendation: str = ""


@dataclass
class Insight:
    """A proactive insight discovered while processing."""
    type: str
    title: str
    description: str
    data: Any
    severity: str
    action_required: bool = False


@dataclass
class SynthesizedAnswer:
    """A complete answer synthesized from all sources."""
    question: str
    answer: str
    confidence: float
    from_reality: List[Truth] = field(default_factory=list)
    from_intent: List[Truth] = field(default_factory=list)
    from_best_practice: List[Truth] = field(default_factory=list)
    conflicts: List[Conflict] = field(default_factory=list)
    insights: List[Insight] = field(default_factory=list)
    structured_output: Optional[Dict] = None
    reasoning: List[str] = field(default_factory=list)
    executed_sql: Optional[str] = None


class IntelligenceMode(Enum):
    SEARCH = "search"
    ANALYZE = "analyze"
    COMPARE = "compare"
    VALIDATE = "validate"
    CONFIGURE = "configure"
    INTERVIEW = "interview"
    WORKFLOW = "workflow"
    POPULATE = "populate"
    REPORT = "report"


# =============================================================================
# SEMANTIC PATTERNS (for column matching only)
# =============================================================================

SEMANTIC_TYPES = {
    'employee_id': [
        r'^emp.*id', r'^ee.*num', r'^employee.*number', r'^worker.*id',
        r'^person.*id', r'^emp.*num', r'^emp.*no$', r'^ee.*id',
        r'^employee.*id', r'^staff.*id', r'^associate.*id', r'^emp.*key',
    ],
    'company_code': [
        r'^comp.*code', r'^co.*code', r'^company.*id', r'^org.*code',
        r'^entity.*code', r'^legal.*entity', r'^business.*unit',
        r'^company$', r'^comp$',
    ],
}


# =============================================================================
# INTELLIGENCE ENGINE
# =============================================================================

class IntelligenceEngine:
    """The brain of XLR8."""
    
    def __init__(self, project_name: str):
        self.project = project_name
        self.structured_handler = None
        self.rag_handler = None
        self.schema = {}
        self.relationships = []
        self.conversation_history = []
        self.confirmed_facts = {}
        self.pending_questions = []
        self.conversation_context = {}
        self.last_executed_sql = None
        self.filter_candidates = {}  # Detected filter dimensions
    
    def load_context(
        self, 
        structured_handler=None, 
        rag_handler=None,
        schema: Dict = None,
        relationships: List[Dict] = None
    ):
        """Load data context for this project."""
        self.structured_handler = structured_handler
        self.rag_handler = rag_handler
        self.schema = schema or {}
        self.relationships = relationships or []
        
        # Extract filter candidates for intelligent clarification
        self.filter_candidates = self.schema.get('filter_candidates', {})
        if self.filter_candidates:
            logger.warning(f"[INTELLIGENCE] Filter candidates loaded: {list(self.filter_candidates.keys())}")
    
    def ask(
        self, 
        question: str,
        mode: IntelligenceMode = None,
        context: Dict = None
    ) -> SynthesizedAnswer:
        """Main entry point - ask the engine a question."""
        logger.warning(f"[INTELLIGENCE] Question: {question[:100]}...")
        logger.warning(f"[INTELLIGENCE] Current confirmed_facts: {self.confirmed_facts}")
        logger.warning(f"[INTELLIGENCE] Available filter categories: {list(self.filter_candidates.keys())}")
        
        q_lower = question.lower()
        
        # Simple analysis
        mode = mode or self._detect_mode(q_lower)
        is_employee_question = self._is_employee_question(q_lower)
        logger.warning(f"[INTELLIGENCE] is_employee_question: {is_employee_question}")
        
        # INTELLIGENT CLARIFICATION
        # For employee questions, determine which filters need clarification
        if is_employee_question:
            needed_clarifications = self._get_needed_clarifications(q_lower)
            logger.warning(f"[INTELLIGENCE] Needed clarifications: {needed_clarifications}")
            
            if needed_clarifications:
                # Build clarification question for first needed filter
                first_filter = needed_clarifications[0]
                return self._request_filter_clarification(question, first_filter)
        
        logger.warning(f"[INTELLIGENCE] Proceeding with facts: {self.confirmed_facts}")
        
        # Gather the three truths
        analysis = {'domains': self._detect_domains(q_lower), 'mode': mode}
        
        reality = self._gather_reality(question, analysis)
        logger.info(f"[INTELLIGENCE] Reality gathered: {len(reality)} truths")
        
        intent = self._gather_intent(question, analysis)
        best_practice = self._gather_best_practice(question, analysis)
        
        conflicts = self._detect_conflicts(reality, intent, best_practice)
        insights = self._run_proactive_checks(analysis)
        
        answer = self._synthesize_answer(
            question=question,
            mode=mode,
            reality=reality,
            intent=intent,
            best_practice=best_practice,
            conflicts=conflicts,
            insights=insights,
            context=context
        )
        
        self.conversation_history.append({
            'question': question,
            'answer_preview': answer.answer[:200] if answer.answer else '',
            'mode': mode.value if mode else 'search',
            'timestamp': datetime.now().isoformat()
        })
        
        return answer
    
    def _is_employee_question(self, q_lower: str) -> bool:
        """Check if question is about employees/people."""
        employee_words = [
            'employee', 'employees', 'worker', 'workers', 'staff', 
            'people', 'person', 'who ', 'how many', 'count',
            'headcount', 'roster', 'census'
        ]
        return any(w in q_lower for w in employee_words)
    
    def _detect_status_in_question(self, q_lower: str) -> Optional[str]:
        """
        Check if user specified employee status in their question.
        Returns the detected status ('active', 'termed', 'all') or None.
        """
        # Active patterns
        if any(p in q_lower for p in ['active only', 'active employees', 'only active', 'current employees']):
            return 'active'
        
        # Terminated patterns
        if any(p in q_lower for p in ['terminated', 'termed', 'inactive', 'former employees']):
            return 'termed'
        
        # All patterns
        if any(p in q_lower for p in ['all employees', 'everyone', 'all staff', 'all workers', 'total employees']):
            return 'all'
        
        return None
    
    def _get_needed_clarifications(self, q_lower: str) -> List[str]:
        """
        Determine which filter categories need clarification for this question.
        
        Returns list of filter category names that need clarification.
        """
        needed = []
        
        logger.warning(f"[CLARIFICATION] Checking needed. confirmed_facts={self.confirmed_facts}, filter_candidates={list(self.filter_candidates.keys())}")
        
        # Check each available filter category
        for category in self.filter_candidates.keys():
            # ALWAYS detect first - user may be overriding a previous value
            detected = self._detect_filter_in_question(category, q_lower)
            
            if detected:
                # User specified in THIS question - set/override it
                if category in self.confirmed_facts and self.confirmed_facts[category] != detected:
                    logger.warning(f"[INTELLIGENCE] Overriding {category}: {self.confirmed_facts[category]} → {detected}")
                else:
                    logger.warning(f"[INTELLIGENCE] Detected {category} in question: {detected}")
                self.confirmed_facts[category] = detected
                continue
            
            # Not detected in question - check if already confirmed
            if category in self.confirmed_facts:
                logger.warning(f"[CLARIFICATION] Skipping {category} - already confirmed as {self.confirmed_facts[category]}")
                continue
            
            # Check if this filter is relevant to the question
            if self._is_filter_relevant(category, q_lower):
                needed.append(category)
        
        # Sort by priority (status first, then company, etc.)
        priority_order = ['status', 'company', 'organization', 'location', 'employee_type', 'pay_type', 'job']
        needed.sort(key=lambda x: priority_order.index(x) if x in priority_order else 99)
        
        logger.warning(f"[CLARIFICATION] Needed clarifications: {needed}")
        return needed
    
    def _detect_filter_in_question(self, category: str, q_lower: str) -> Optional[str]:
        """
        Check if user specified a filter value in their question.
        Returns the detected value or None.
        
        This is the SMART DETECTION that auto-applies filters without asking.
        """
        if category == 'status':
            return self._detect_status_in_question(q_lower)
        
        # Get filter candidates for this category
        candidates = self.filter_candidates.get(category, [])
        if not candidates:
            return None
        
        # LOCATION DETECTION - States, cities, common patterns
        if category == 'location':
            # US States - universal mapping (not data-specific)
            states = {
                'texas': 'TX', 'tx': 'TX',
                'california': 'CA', 'ca': 'CA', 
                'new york': 'NY', 'ny': 'NY',
                'florida': 'FL', 'fl': 'FL',
                'illinois': 'IL', 'il': 'IL',
                'pennsylvania': 'PA', 'pa': 'PA',
                'ohio': 'OH', 'oh': 'OH',
                'georgia': 'GA', 'ga': 'GA',
                'michigan': 'MI', 'mi': 'MI',
                'north carolina': 'NC', 'nc': 'NC',
                'new jersey': 'NJ', 'nj': 'NJ',
                'virginia': 'VA', 'va': 'VA',
                'washington': 'WA', 'wa': 'WA',
                'arizona': 'AZ', 'az': 'AZ',
                'massachusetts': 'MA', 'ma': 'MA',
                'tennessee': 'TN', 'tn': 'TN',
                'indiana': 'IN', 'missouri': 'MO',
                'maryland': 'MD', 'wisconsin': 'WI',
                'colorado': 'CO', 'minnesota': 'MN',
                'south carolina': 'SC', 'alabama': 'AL',
                'louisiana': 'LA', 'kentucky': 'KY',
                'oregon': 'OR', 'oklahoma': 'OK',
                'connecticut': 'CT', 'utah': 'UT',
                'iowa': 'IA', 'nevada': 'NV',
                'arkansas': 'AR', 'mississippi': 'MS',
                'kansas': 'KS', 'new mexico': 'NM',
                'nebraska': 'NE', 'hawaii': 'HI',
                'idaho': 'ID', 'maine': 'ME',
                'new hampshire': 'NH', 'rhode island': 'RI',
                'montana': 'MT', 'delaware': 'DE',
                'south dakota': 'SD', 'north dakota': 'ND',
                'alaska': 'AK', 'vermont': 'VT',
                'wyoming': 'WY', 'west virginia': 'WV'
            }
            
            # Check for state mentions
            for state_name, state_code in states.items():
                # Skip 2-letter codes as standalone patterns (too many false positives)
                # Only match them with explicit context like "in TX" or "TX employees"
                if len(state_name) == 2:
                    # Stricter patterns for 2-letter codes
                    patterns = [
                        f' in {state_name}$',  # "in TX" at end
                        f' in {state_name} ',  # "in TX " with space after
                        f' in {state_name},',  # "in TX,"
                        f'{state_name} employees',
                        f'{state_name} workers',
                        f'from {state_name}',
                    ]
                    for pattern in patterns:
                        # Use regex for end-of-string patterns
                        if pattern.endswith('$'):
                            if q_lower.endswith(pattern[:-1]):
                                logger.warning(f"[FILTER-DETECT] Found state '{state_name}' → '{state_code}' in question")
                                return state_code
                        elif pattern in q_lower:
                            logger.warning(f"[FILTER-DETECT] Found state '{state_name}' → '{state_code}' in question")
                            return state_code
                else:
                    # Full state names - use word boundary matching
                    if _is_word_boundary_match(q_lower, state_name):
                        logger.warning(f"[FILTER-DETECT] Found state '{state_name}' → '{state_code}' in question")
                        return state_code
            
            # Check actual location values in data (with ARE bug fix)
            for candidate in candidates:
                values = candidate.get('values', [])
                for value in values:
                    value_str = str(value).lower()
                    # Skip short values, blocklisted words, and require word boundary match
                    if len(value_str) > 2 and not _is_blocklisted(value_str):
                        if _is_word_boundary_match(q_lower, value_str):
                            logger.warning(f"[FILTER-DETECT] Found location value {value} in question (word boundary)")
                            return value
        
        # COMPANY DETECTION - Check company codes directly (with ARE bug fix)
        if category == 'company':
            for candidate in candidates:
                values = candidate.get('values', [])
                for value in values:
                    value_str = str(value).lower()
                    # Skip blocklisted words
                    if len(value_str) >= 3 and not _is_blocklisted(value_str):
                        # Use word boundary matching
                        if _is_word_boundary_match(q_lower, value_str):
                            logger.warning(f"[FILTER-DETECT] Found company {value} in question (word boundary)")
                            return value
        
        # PAY TYPE DETECTION
        if category == 'pay_type':
            pay_patterns = {
                'hourly': ['hourly', 'hourly employees', 'hourly workers', 'hourly staff'],
                'salary': ['salary', 'salaried', 'salaried employees'],
                'full_time': ['full time', 'full-time', 'fulltime', ' ft '],
                'part_time': ['part time', 'part-time', 'parttime', ' pt ']
            }
            for detected_value, patterns in pay_patterns.items():
                if any(p in q_lower for p in patterns):
                    # Map to actual code in data
                    for candidate in candidates:
                        values = candidate.get('values', [])
                        for value in values:
                            v = str(value).upper()
                            if detected_value == 'hourly' and v in ['H', 'HOURLY', 'HR']:
                                return value
                            if detected_value == 'salary' and v in ['S', 'SALARY', 'SAL', 'SALARIED']:
                                return value
                            if detected_value == 'full_time' and v in ['F', 'FT', 'FULL', 'FULL-TIME']:
                                return value
                            if detected_value == 'part_time' and v in ['P', 'PT', 'PART', 'PART-TIME']:
                                return value
                    # Return the detected value if no mapping found
                    logger.warning(f"[FILTER-DETECT] Found pay_type {detected_value} in question")
                    return detected_value
        
        # EMPLOYEE TYPE DETECTION
        if category == 'employee_type':
            emp_patterns = {
                'regular': ['regular employee', 'regular workers', 'regular staff', 'permanent'],
                'temp': ['temp ', 'temporary', 'temps ', 'temp employees'],
                'contractor': ['contractor', 'contractors', 'contract workers', '1099']
            }
            for detected_value, patterns in emp_patterns.items():
                if any(p in q_lower for p in patterns):
                    # Map to actual code in data
                    for candidate in candidates:
                        values = candidate.get('values', [])
                        for value in values:
                            v = str(value).upper()
                            if detected_value == 'regular' and v in ['REG', 'REGULAR', 'R', 'PERM']:
                                return value
                            if detected_value == 'temp' and v in ['TMP', 'TEMP', 'T', 'TEMPORARY']:
                                return value
                            if detected_value == 'contractor' and v in ['CON', 'CTR', 'CONTRACTOR', 'C']:
                                return value
                    logger.warning(f"[FILTER-DETECT] Found employee_type {detected_value} in question")
                    return detected_value
        
        # GENERIC: Check if any specific value from data is mentioned (with ARE bug fix)
        for candidate in candidates:
            values = candidate.get('values', [])
            for value in values:
                value_str = str(value).lower()
                if len(value_str) > 2 and not _is_blocklisted(value_str):
                    if _is_word_boundary_match(q_lower, value_str):
                        logger.warning(f"[FILTER-DETECT] Found {category} value {value} in question (word boundary)")
                        return value
        
        return None
    
    def _is_filter_relevant(self, category: str, q_lower: str) -> bool:
        """
        Determine if a filter category is relevant to this question.
        Returns True if we should ASK about this filter (not auto-detected).
        
        Smart logic:
        - Status: Always relevant for employee questions (unless "all")
        - Company: Ask if "by company" or multiple companies exist and asking totals
        - Location: Ask if "by location/state" mentioned
        - Others: Only if explicitly requested with "by X"
        """
        # Status is almost always relevant for employee questions
        if category == 'status':
            # Skip if user said "all employees" or similar
            if any(p in q_lower for p in ['all employees', 'all staff', 'everyone', 'all workers']):
                self.confirmed_facts['status'] = 'all'
                return False
            return True
        
        # Check for "by X" patterns that trigger clarification
        by_patterns = {
            'company': ['by company', 'per company', 'each company', 'by entity', 'by legal entity'],
            'location': ['by location', 'by state', 'per state', 'by site', 'each location', 'by region'],
            'organization': ['by department', 'by org', 'by cost center', 'per department', 'by division'],
            'pay_type': ['by pay type', 'hourly vs salary', 'hourly and salary'],
            'employee_type': ['by employee type', 'by worker type', 'regular vs temp']
        }
        
        patterns = by_patterns.get(category, [])
        if any(p in q_lower for p in patterns):
            # Check if we have multiple values to ask about
            candidates = self.filter_candidates.get(category, [])
            if candidates:
                distinct_count = candidates[0].get('distinct_count', 0)
                if distinct_count > 1:
                    logger.warning(f"[FILTER-RELEVANT] {category} relevant due to 'by X' pattern, {distinct_count} values")
                    return True
        
        return False
    
    def _request_filter_clarification(self, question: str, category: str) -> SynthesizedAnswer:
        """
        Build a clarification question for a specific filter category.
        Uses actual values from profile data.
        """
        # Get candidates for this category
        candidates = self.filter_candidates.get(category, [])
        
        if category == 'status':
            return self._request_employee_status_clarification(question)
        
        # Build options from profile data
        options = self._build_filter_options(category, candidates)
        
        if not options:
            # Skip this category if we can't build options
            return self._continue_without_filter(question, category)
        
        # Category-specific question text
        question_text = {
            'company': "Which company should I include?",
            'organization': "Which department/organization?",
            'location': "Which location(s)?",
            'pay_type': "Which pay type?",
            'employee_type': "Which employee type?",
            'job': "Which job family/code?"
        }.get(category, f"Which {category}?")
        
        return SynthesizedAnswer(
            question=question,
            answer="",
            confidence=0.0,
            structured_output={
                'type': 'clarification_needed',
                'filter_category': category,
                'questions': [{
                    'id': category,
                    'text': question_text,
                    'type': 'single_select',
                    'options': options
                }],
                'detected_domains': ['employees']
            },
            reasoning=f"Need to clarify {category} filter"
        )
    
    def _build_filter_options(self, category: str, candidates: List[Dict]) -> List[Dict]:
        """Build filter options from profile data."""
        if not candidates:
            return []
        
        # Use first candidate (highest priority)
        candidate = candidates[0]
        values = candidate.get('values', [])
        distribution = candidate.get('distribution', {})
        total_count = candidate.get('total_count', 0)
        
        if not values:
            return []
        
        options = []
        for value in values[:10]:  # Limit to 10 options
            count = distribution.get(str(value), 0)
            label = f"{value} ({count:,})" if count else str(value)
            options.append({
                'id': str(value).lower().replace(' ', '_'),
                'label': label,
                'value': value
            })
        
        # Add "All" option
        options.append({
            'id': 'all',
            'label': f'All ({total_count:,} total)'
        })
        
        return options
    
    def _continue_without_filter(self, question: str, category: str) -> SynthesizedAnswer:
        """Continue processing without this filter (skip clarification)."""
        self.confirmed_facts[category] = 'all'
        return self.ask(question)  # Recursive call to continue
    
    def _request_employee_status_clarification(self, question: str) -> SynthesizedAnswer:
        """Ask for employee status clarification using ACTUAL values from filter_candidates."""
        
        # Get status options from filter_candidates (smarter selection)
        status_options = self._get_status_options_from_filter_candidates()
        
        if not status_options:
            # Fallback to generic options if no profile data
            status_options = [
                {'id': 'active', 'label': 'Active only', 'default': True},
                {'id': 'termed', 'label': 'Terminated only'},
                {'id': 'all', 'label': 'All employees'}
            ]
        
        return SynthesizedAnswer(
            question=question,
            answer="",
            confidence=0.0,
            structured_output={
                'type': 'clarification_needed',
                'questions': [{
                    'id': 'status',  # Use 'status' consistently (was 'employee_status')
                    'question': 'Which employees should I include?',
                    'type': 'radio',
                    'options': status_options
                }],
                'original_question': question,
                'detected_mode': 'search',
                'detected_domains': ['employees']
            },
            reasoning=['Need to know which employees to include']
        )
    
    def _get_status_options_from_filter_candidates(self) -> List[Dict]:
        """
        Get employee status options from filter_candidates.
        Prioritizes columns from employee-level tables (lower row counts).
        """
        status_candidates = self.filter_candidates.get('status', [])
        
        if not status_candidates:
            return []
        
        # Find the BEST status column:
        # 1. Prefer employment_status_code/employment_status over others
        # 2. Prefer tables with ~14k rows (employee-level) over 60k+ (transaction-level)
        best_candidate = None
        
        for candidate in status_candidates:
            col_name = candidate.get('column', '').lower()
            total_count = candidate.get('total_count', 0)
            col_type = candidate.get('type', '')
            
            # Skip transaction tables (too many rows per employee)
            if total_count > 20000:
                continue
            
            # Prefer employment_status columns
            if 'employment_status' in col_name:
                best_candidate = candidate
                break
            
            # termination_date is good but harder to show counts
            if col_type == 'date' and 'termination' in col_name:
                if not best_candidate:
                    best_candidate = candidate
                continue
            
            # Any categorical status column from employee-level table
            if not best_candidate and col_type == 'categorical':
                best_candidate = candidate
        
        if not best_candidate:
            # Fallback to first candidate
            best_candidate = status_candidates[0] if status_candidates else None
        
        if not best_candidate:
            return []
        
        logger.warning(f"[CLARIFICATION] Using status column: {best_candidate.get('column')} from {best_candidate.get('table', '').split('__')[-1]}")
        
        col_type = best_candidate.get('type', '')
        
        # Handle termination_date (date type)
        if col_type == 'date':
            total = best_candidate.get('total_count', 0)
            null_count = best_candidate.get('null_count', 0)
            active_count = null_count  # null termination_date = active
            termed_count = total - null_count
            
            return [
                {'id': 'active', 'label': f'Active only ({active_count:,} employees)', 'default': True},
                {'id': 'termed', 'label': f'Terminated only ({termed_count:,} employees)'},
                {'id': 'all', 'label': f'All employees ({total:,} total)'}
            ]
        
        # Handle categorical status column (A/T codes)
        values = best_candidate.get('values', [])
        distribution = best_candidate.get('distribution', {})
        total = best_candidate.get('total_count', 0)
        
        # Map codes to active/termed
        active_codes = ['A', 'ACTIVE', 'ACT']
        termed_codes = ['T', 'TERMINATED', 'TERM', 'I', 'INACTIVE']
        leave_codes = ['L', 'LEAVE', 'LOA']
        
        active_count = sum(distribution.get(v, 0) for v in values if str(v).upper() in active_codes)
        termed_count = sum(distribution.get(v, 0) for v in values if str(v).upper() in termed_codes)
        leave_count = sum(distribution.get(v, 0) for v in values if str(v).upper() in leave_codes)
        
        options = []
        if active_count > 0:
            options.append({'id': 'active', 'label': f'Active only ({active_count:,} employees)', 'default': True})
        if termed_count > 0:
            options.append({'id': 'termed', 'label': f'Terminated only ({termed_count:,} employees)'})
        if leave_count > 0:
            options.append({'id': 'leave', 'label': f'On Leave ({leave_count:,} employees)'})
        options.append({'id': 'all', 'label': f'All employees ({total:,} total)'})
        
        return options
    
    def _get_status_options_from_profiles(self) -> List[Dict]:
        """
        Get employee status options from actual profile data.
        This is the key Phase 2 feature - data-driven clarification.
        """
        if not self.schema:
            return []
        
        tables = self.schema.get('tables', [])
        
        # Look for status-related columns in the profiles
        status_patterns = ['status', 'employment_status', 'emp_status', 'employee_status', 
                          'employment_status_code', 'termination_date', 'term_date']
        
        for table in tables:
            categorical_cols = table.get('categorical_columns', [])
            column_profiles = table.get('column_profiles', {})
            
            # Check categorical columns for status-like values
            for cat_col in categorical_cols:
                col_name = cat_col.get('column', '').lower()
                
                # Is this a status column?
                if any(pattern in col_name for pattern in status_patterns):
                    values = cat_col.get('values', [])
                    distribution = cat_col.get('distribution', {})
                    
                    if values:
                        return self._build_status_options(values, distribution, col_name)
            
            # Also check column_profiles directly
            for col_name, profile in column_profiles.items():
                col_lower = col_name.lower()
                if any(pattern in col_lower for pattern in status_patterns):
                    if profile.get('is_categorical') and profile.get('distinct_values'):
                        values = profile['distinct_values']
                        distribution = profile.get('value_distribution', {})
                        return self._build_status_options(values, distribution, col_name)
        
        return []
    
    def _build_status_options(self, values: List[str], distribution: Dict, col_name: str) -> List[Dict]:
        """Build clarification options from actual data values."""
        options = []
        
        # Common status code mappings
        status_labels = {
            'A': 'Active', 'T': 'Terminated', 'L': 'Leave', 'I': 'Inactive',
            'ACTIVE': 'Active', 'TERMED': 'Terminated', 'TERM': 'Terminated',
            'LOA': 'Leave of Absence', 'LEAVE': 'Leave', 'INACTIVE': 'Inactive',
            'REG': 'Regular', 'TEMP': 'Temporary', 'PART': 'Part-time',
            'FT': 'Full-time', 'PT': 'Part-time'
        }
        
        # Build options with counts
        active_values = []
        termed_values = []
        other_values = []
        
        for val in values:
            val_upper = str(val).upper().strip()
            count = distribution.get(val, distribution.get(str(val), 0))
            
            # Categorize
            if val_upper in ['A', 'ACTIVE', 'ACT']:
                active_values.append((val, count))
            elif val_upper in ['T', 'TERMINATED', 'TERM', 'TERMED', 'I', 'INACTIVE']:
                termed_values.append((val, count))
            else:
                other_values.append((val, count))
        
        # Build options with actual counts
        if active_values:
            active_count = sum(c for _, c in active_values)
            active_codes = ', '.join(v for v, _ in active_values)
            options.append({
                'id': 'active',
                'label': f'Active only ({active_count:,} employees)',
                'codes': active_codes,
                'default': True
            })
        
        if termed_values:
            termed_count = sum(c for _, c in termed_values)
            termed_codes = ', '.join(v for v, _ in termed_values)
            options.append({
                'id': 'termed',
                'label': f'Terminated only ({termed_count:,} employees)',
                'codes': termed_codes
            })
        
        # Add "All" option with total
        total_count = sum(distribution.values()) if distribution else 0
        options.append({
            'id': 'all',
            'label': f'All employees ({total_count:,} total)'
        })
        
        # If we couldn't categorize well, show raw values
        if not active_values and not termed_values and other_values:
            options = []
            for val, count in sorted(other_values, key=lambda x: -x[1])[:5]:
                label = status_labels.get(str(val).upper(), str(val))
                options.append({
                    'id': str(val).lower(),
                    'label': f'{label} ({count:,})',
                    'code': val
                })
            options.append({'id': 'all', 'label': f'All ({total_count:,} total)'})
        
        logger.info(f"[CLARIFICATION] Built {len(options)} options from {col_name}: {[o['id'] for o in options]}")
        return options
    
    def _get_status_column_and_codes(self, status_filter: str) -> Tuple[Optional[str], List[str]]:
        """
        Get the actual column name and codes to use for filtering.
        Returns (column_name, [list of codes])
        """
        if not self.schema:
            return None, []
        
        tables = self.schema.get('tables', [])
        status_patterns = ['status', 'employment_status', 'emp_status', 'employee_status', 'employment_status_code']
        
        for table in tables:
            categorical_cols = table.get('categorical_columns', [])
            column_profiles = table.get('column_profiles', {})
            
            for cat_col in categorical_cols:
                col_name = cat_col.get('column', '')
                col_lower = col_name.lower()
                
                if any(pattern in col_lower for pattern in status_patterns):
                    values = cat_col.get('values', [])
                    
                    # Find matching codes based on status_filter
                    if status_filter == 'active':
                        codes = [v for v in values if str(v).upper() in ['A', 'ACTIVE', 'ACT']]
                    elif status_filter == 'termed':
                        codes = [v for v in values if str(v).upper() in ['T', 'TERMINATED', 'TERM', 'TERMED', 'I', 'INACTIVE']]
                    else:
                        # Check if filter matches a specific code
                        codes = [v for v in values if str(v).lower() == status_filter.lower()]
                    
                    if codes:
                        return col_name, codes
            
            # Also check column_profiles
            for col_name, profile in column_profiles.items():
                col_lower = col_name.lower()
                if any(pattern in col_lower for pattern in status_patterns):
                    values = profile.get('distinct_values', [])
                    
                    if status_filter == 'active':
                        codes = [v for v in values if str(v).upper() in ['A', 'ACTIVE', 'ACT']]
                    elif status_filter == 'termed':
                        codes = [v for v in values if str(v).upper() in ['T', 'TERMINATED', 'TERM', 'TERMED', 'I', 'INACTIVE']]
                    else:
                        codes = [v for v in values if str(v).lower() == status_filter.lower()]
                    
                    if codes:
                        return col_name, codes
        
        return None, []
    
    def _build_filter_instructions(self, relevant_tables: List[Dict]) -> str:
        """
        Build SQL filter instructions from confirmed_facts and filter_candidates.
        Uses profile data to generate accurate WHERE clauses.
        """
        filters = []
        
        # STATUS FILTER
        status_filter = self.confirmed_facts.get('status')
        logger.warning(f"[SQL-GEN] Building filters. status={status_filter}, all_facts={self.confirmed_facts}")
        
        if status_filter and status_filter != 'all':
            # Use SAME logic as _get_status_options_from_filter_candidates to pick column
            status_candidates = self.filter_candidates.get('status', [])
            best_candidate = None
            
            for candidate in status_candidates:
                col_name = candidate.get('column', '').lower()
                total_count = candidate.get('total_count', 0)
                col_type = candidate.get('type', '')
                
                # Skip transaction tables (too many rows per employee)
                if total_count > 20000:
                    continue
                
                # Prefer employment_status columns (categorical with A/T codes)
                if 'employment_status' in col_name:
                    best_candidate = candidate
                    break
                
                # termination_date is fallback
                if col_type == 'date' and 'termination' in col_name:
                    if not best_candidate:
                        best_candidate = candidate
                    continue
                
                # Any categorical status column from employee-level table
                if not best_candidate and col_type == 'categorical':
                    best_candidate = candidate
            
            if not best_candidate and status_candidates:
                best_candidate = status_candidates[0]
            
            if best_candidate:
                col_name = best_candidate.get('column')
                col_type = best_candidate.get('type')
                values = best_candidate.get('values', [])
                
                logger.warning(f"[SQL-GEN] Status candidate: col={col_name}, type={col_type}")
                
                if col_type == 'date':  # termination_date
                    if status_filter == 'active':
                        filters.append(f"({col_name} IS NULL OR {col_name} = '' OR CAST({col_name} AS VARCHAR) = '')")
                    elif status_filter == 'termed':
                        filters.append(f"({col_name} IS NOT NULL AND {col_name} != '' AND CAST({col_name} AS VARCHAR) != '')")
                else:  # categorical status code
                    # Find matching codes
                    if status_filter == 'active':
                        codes = [v for v in values if str(v).upper() in ['A', 'ACTIVE', 'ACT']]
                    elif status_filter == 'termed':
                        codes = [v for v in values if str(v).upper() in ['T', 'TERMINATED', 'TERM', 'TERMED', 'I', 'INACTIVE']]
                    elif status_filter == 'leave':
                        codes = [v for v in values if str(v).upper() in ['L', 'LEAVE', 'LOA']]
                    else:
                        codes = [v for v in values if str(v).lower() == status_filter.lower()]
                    
                    if codes:
                        codes_str = ', '.join(f"'{c}'" for c in codes)
                        filters.append(f"{col_name} IN ({codes_str})")
                    else:
                        logger.warning(f"[SQL-GEN] No matching codes for status={status_filter} in values={values}")
            else:
                # Last resort fallback: look for termination_date in tables
                for table in relevant_tables:
                    columns = table.get('columns', [])
                    for col in columns:
                        col_name = col.get('name', str(col)) if isinstance(col, dict) else str(col)
                        if 'termination_date' in col_name.lower():
                            if status_filter == 'active':
                                filters.append(f"({col_name} IS NULL OR {col_name} = '')")
                            elif status_filter == 'termed':
                                filters.append(f"({col_name} IS NOT NULL AND {col_name} != '')")
                            break
        
        # COMPANY FILTER
        company_filter = self.confirmed_facts.get('company')
        if company_filter and company_filter != 'all':
            company_candidates = self.filter_candidates.get('company', [])
            if company_candidates:
                col_name = company_candidates[0].get('column')
                filters.append(f"{col_name} = '{company_filter}'")
        
        # LOCATION FILTER
        location_filter = self.confirmed_facts.get('location')
        if location_filter and location_filter != 'all':
            location_candidates = self.filter_candidates.get('location', [])
            if location_candidates:
                # Find a valid location column (not routing numbers, banks, etc.)
                location_column_patterns = ['state', 'province', 'location', 'region', 'city', 'address', 'county']
                invalid_patterns = ['routing', 'bank', 'account', 'number', 'branch', 'aba']
                
                valid_col = None
                for candidate in location_candidates:
                    col_name = candidate.get('column', '').lower()
                    # Check if column name looks like a location field
                    is_location = any(p in col_name for p in location_column_patterns)
                    is_invalid = any(p in col_name for p in invalid_patterns)
                    
                    if is_location and not is_invalid:
                        valid_col = candidate.get('column')
                        break
                    elif not is_invalid and not valid_col:
                        # Fallback: accept if not obviously invalid
                        valid_col = candidate.get('column')
                
                if valid_col:
                    filters.append(f"{valid_col} = '{location_filter}'")
                    logger.warning(f"[FILTER] Using location column: {valid_col}")
                else:
                    logger.warning(f"[FILTER] No valid location column found, skipping location filter")
        
        # PAY TYPE FILTER
        pay_type_filter = self.confirmed_facts.get('pay_type')
        if pay_type_filter and pay_type_filter != 'all':
            pay_candidates = self.filter_candidates.get('pay_type', [])
            if pay_candidates:
                col_name = pay_candidates[0].get('column')
                values = pay_candidates[0].get('values', [])
                # Map common terms to actual codes
                if pay_type_filter in ['hourly', 'h']:
                    codes = [v for v in values if str(v).upper() in ['H', 'HOURLY']]
                elif pay_type_filter in ['salary', 'salaried', 's']:
                    codes = [v for v in values if str(v).upper() in ['S', 'SALARY', 'SALARIED']]
                else:
                    codes = [pay_type_filter]
                if codes:
                    codes_str = ', '.join(f"'{c}'" for c in codes)
                    filters.append(f"{col_name} IN ({codes_str})")
        
        # EMPLOYEE TYPE FILTER
        emp_type_filter = self.confirmed_facts.get('employee_type')
        if emp_type_filter and emp_type_filter != 'all':
            emp_candidates = self.filter_candidates.get('employee_type', [])
            if emp_candidates:
                col_name = emp_candidates[0].get('column')
                values = emp_candidates[0].get('values', [])
                # Map common terms
                if emp_type_filter in ['regular', 'reg']:
                    codes = [v for v in values if str(v).upper() in ['REG', 'REGULAR']]
                elif emp_type_filter in ['temp', 'temporary']:
                    codes = [v for v in values if str(v).upper() in ['TMP', 'TEMP', 'TEMPORARY']]
                elif emp_type_filter in ['contractor', 'contract']:
                    codes = [v for v in values if str(v).upper() in ['CON', 'CTR', 'CONTRACTOR']]
                else:
                    codes = [emp_type_filter]
                if codes:
                    codes_str = ', '.join(f"'{c}'" for c in codes)
                    filters.append(f"{col_name} IN ({codes_str})")
        
        # Build final filter string
        if filters:
            return "WHERE " + " AND ".join(filters)
        
        return ""
    
    def _fix_state_names_in_sql(self, sql: str) -> str:
        """
        Strip location/state filters from LLM-generated SQL.
        
        We handle location filters via data-driven injection from confirmed_facts.
        The LLM sometimes adds its own (wrong) location filters like ILIKE '%Texas%'.
        We strip these and let our filter injection handle it properly.
        """
        # Only strip if we have a confirmed location filter (we'll inject the right one)
        location_filter = self.confirmed_facts.get('location')
        if not location_filter or location_filter == 'all':
            return sql
        
        # Get location column name from filter_candidates
        location_candidates = self.filter_candidates.get('location', [])
        if not location_candidates:
            return sql
        
        col_name = location_candidates[0].get('column', '')
        if not col_name:
            return sql
        
        modified = sql
        
        # Strip patterns like: column ILIKE '%anything%'
        # This removes the LLM's location filter so our injection can add the correct one
        
        # Pattern 0: WHERE col ILIKE '...' AND ... → WHERE ...
        pattern0 = rf"WHERE\s+{re.escape(col_name)}\s+ILIKE\s+'%[^']+%'\s*AND\s*"
        modified = re.sub(pattern0, 'WHERE ', modified, flags=re.IGNORECASE)
        
        # Pattern 1: ... AND col ILIKE '...' AND ... → ... AND ...
        pattern1 = rf"{re.escape(col_name)}\s+ILIKE\s+'%[^']+%'\s*AND\s*"
        modified = re.sub(pattern1, '', modified, flags=re.IGNORECASE)
        
        # Pattern 2: ... AND col ILIKE '...' (at end) → ...
        pattern2 = rf"\s*AND\s+{re.escape(col_name)}\s+ILIKE\s+'%[^']+%'"
        modified = re.sub(pattern2, '', modified, flags=re.IGNORECASE)
        
        # Pattern 3: WHERE col = 'StateName' AND ... → WHERE ...
        pattern3 = rf"WHERE\s+{re.escape(col_name)}\s*=\s*'[A-Za-z\s]+'\s*AND\s*"
        modified = re.sub(pattern3, 'WHERE ', modified, flags=re.IGNORECASE)
        
        # Pattern 4: ... AND col = 'StateName' (at end) → ...  
        pattern4 = rf"\s*AND\s+{re.escape(col_name)}\s*=\s*'[A-Za-z\s]+'"
        modified = re.sub(pattern4, '', modified, flags=re.IGNORECASE)
        
        if modified != sql:
            logger.warning(f"[SQL-FIX] Stripped LLM location filter, will use confirmed_facts['location']={location_filter}")
            logger.warning(f"[SQL-FIX] Before: {sql[:150]}")
            logger.warning(f"[SQL-FIX] After: {modified[:150]}")
        
        return modified
    
    def _inject_where_clause(self, sql: str, filter_clause: str) -> str:
        """
        Inject a WHERE clause into SQL that may or may not already have one.
        
        This is the data-driven approach: LLM generates structure, we inject filters.
        """
        # Clean up filter_clause - remove leading WHERE if present
        conditions = filter_clause.strip()
        if conditions.upper().startswith('WHERE '):
            conditions = conditions[6:].strip()
        
        if not conditions:
            logger.warning(f"[FILTER-INJECT] No conditions to inject")
            return sql
        
        logger.warning(f"[FILTER-INJECT] Injecting: {conditions}")
        logger.warning(f"[FILTER-INJECT] SQL length before: {len(sql)}")
        
        sql_upper = sql.upper()
        
        # Check if SQL already has WHERE
        where_match = re.search(r'\bWHERE\b', sql, re.IGNORECASE)
        
        if where_match:
            # Has WHERE - add with AND after existing conditions
            logger.warning(f"[FILTER-INJECT] Found existing WHERE at position {where_match.start()}")
            where_pos = where_match.end()
            
            # Find the end of existing WHERE conditions
            end_keywords = ['GROUP BY', 'ORDER BY', 'LIMIT', 'HAVING', ';']
            end_pos = len(sql)
            
            for keyword in end_keywords:
                kw_match = re.search(rf'\b{keyword}\b', sql[where_pos:], re.IGNORECASE)
                if kw_match:
                    candidate_pos = where_pos + kw_match.start()
                    if candidate_pos < end_pos:
                        end_pos = candidate_pos
            
            # Insert AND + conditions before end_pos
            sql = sql[:end_pos].rstrip() + f" AND {conditions} " + sql[end_pos:]
        
        else:
            # No WHERE - find where to insert
            logger.warning(f"[FILTER-INJECT] No existing WHERE found")
            
            # Insert before GROUP BY, ORDER BY, LIMIT, or at end
            insert_keywords = ['GROUP BY', 'ORDER BY', 'LIMIT', 'HAVING']
            insert_pos = len(sql.rstrip().rstrip(';'))
            
            for keyword in insert_keywords:
                kw_match = re.search(rf'\b{keyword}\b', sql, re.IGNORECASE)
                if kw_match and kw_match.start() < insert_pos:
                    insert_pos = kw_match.start()
                    logger.warning(f"[FILTER-INJECT] Found {keyword} at {insert_pos}")
            
            logger.warning(f"[FILTER-INJECT] Insert position: {insert_pos}")
            
            # Insert WHERE clause
            before = sql[:insert_pos].rstrip()
            after = sql[insert_pos:].lstrip()
            
            logger.warning(f"[FILTER-INJECT] Before part ends with: ...{before[-50:] if len(before) > 50 else before}")
            logger.warning(f"[FILTER-INJECT] After part: {after[:50] if after else 'EMPTY'}")
            
            if after:
                sql = f"{before} WHERE {conditions} {after}"
            else:
                sql = f"{before} WHERE {conditions}"
        
        logger.warning(f"[FILTER-INJECT] SQL length after: {len(sql)}")
        return sql.strip()
    
    def _detect_mode(self, q_lower: str) -> IntelligenceMode:
        """Detect the appropriate intelligence mode."""
        if any(w in q_lower for w in ['validate', 'check', 'verify', 'issues', 'problems']):
            return IntelligenceMode.VALIDATE
        if any(w in q_lower for w in ['configure', 'set up', 'setup']):
            return IntelligenceMode.CONFIGURE
        if any(w in q_lower for w in ['compare', 'versus', 'vs', 'difference']):
            return IntelligenceMode.COMPARE
        if any(w in q_lower for w in ['report', 'summary', 'overview']):
            return IntelligenceMode.REPORT
        if any(w in q_lower for w in ['analyze', 'trend', 'pattern']):
            return IntelligenceMode.ANALYZE
        return IntelligenceMode.SEARCH
    
    def _detect_domains(self, q_lower: str) -> List[str]:
        """Detect which data domains are relevant."""
        domains = []
        
        if any(w in q_lower for w in ['employee', 'worker', 'staff', 'people', 'who', 'how many', 'count']):
            domains.append('employees')
        if any(w in q_lower for w in ['earn', 'pay', 'salary', 'wage', 'rate', 'hour', '$', 'compensation']):
            domains.append('earnings')
        if any(w in q_lower for w in ['deduction', 'benefit', '401k', 'insurance', 'health']):
            domains.append('deductions')
        if any(w in q_lower for w in ['tax', 'withhold', 'federal', 'state']):
            domains.append('taxes')
        if any(w in q_lower for w in ['job', 'position', 'title', 'department']):
            domains.append('jobs')
        
        return domains if domains else ['general']
    
    def _select_relevant_tables(self, tables: List[Dict], q_lower: str) -> List[Dict]:
        """
        Select only tables relevant to the question.
        This keeps the SQL prompt small and focused.
        """
        if not tables:
            return []
        
        # Priority keywords for table selection
        table_keywords = {
            'personal': ['employee', 'employees', 'person', 'people', 'who', 'name', 'ssn', 'birth', 'hire'],
            'company': ['company', 'organization', 'org', 'entity'],
            'job': ['job', 'position', 'title', 'department', 'dept'],
            'earnings': ['earn', 'earning', 'pay', 'salary', 'wage', 'compensation', 'rate'],
            'deductions': ['deduction', 'benefit', '401k', 'insurance', 'health'],
            'taxes': ['tax', 'withhold', 'federal', 'state'],
            'time': ['time', 'hours', 'attendance', 'schedule'],
            'address': ['address', 'location', 'city', 'state', 'zip'],
        }
        
        # Score each table
        scored_tables = []
        for table in tables:
            table_name = table.get('table_name', '').lower()
            short_name = table_name.split('__')[-1] if '__' in table_name else table_name
            
            score = 0
            
            # Check if table name matches any keyword patterns
            for pattern, keywords in table_keywords.items():
                if pattern in short_name:
                    # Check if any keyword is in the question
                    if any(kw in q_lower for kw in keywords):
                        score += 10
                    else:
                        score += 1  # Table exists but question doesn't directly ask about it
            
            # Boost "personal" table for general employee questions
            if 'personal' in short_name and any(kw in q_lower for kw in ['employee', 'how many', 'count', 'who']):
                score += 20
            
            # Boost tables with high row counts (they're likely the main tables)
            row_count = table.get('row_count', 0)
            if row_count > 1000:
                score += 5
            elif row_count > 100:
                score += 2
            
            scored_tables.append((score, table))
        
        # Sort by score descending
        scored_tables.sort(key=lambda x: -x[0])
        
        # Take top 3 tables max (keeps prompt small)
        relevant = [t for score, t in scored_tables[:3] if score > 0]
        
        # If no relevant tables found, just use first table
        if not relevant:
            relevant = [tables[0]]
        
        logger.info(f"[SQL-GEN] Selected {len(relevant)} relevant tables: {[t.get('table_name', '').split('__')[-1] for t in relevant]}")
        
        return relevant
    
    def _generate_sql_for_question(self, question: str, analysis: Dict) -> Optional[Dict]:
        """Generate SQL query using LLMOrchestrator with SMART table selection."""
        logger.warning(f"[SQL-GEN] v4.8 - Starting SQL generation")
        logger.warning(f"[SQL-GEN] confirmed_facts: {self.confirmed_facts}")
        
        if not self.structured_handler or not self.schema:
            return None
        
        tables = self.schema.get('tables', [])
        if not tables:
            return None
        
        # Get LLMOrchestrator
        try:
            try:
                from utils.llm_orchestrator import LLMOrchestrator
            except ImportError:
                from backend.utils.llm_orchestrator import LLMOrchestrator
            
            orchestrator = LLMOrchestrator()
        except Exception as e:
            logger.error(f"[SQL-GEN] Could not load LLMOrchestrator: {e}")
            return None
        
        # SMART TABLE SELECTION - only include relevant tables
        q_lower = question.lower()
        relevant_tables = self._select_relevant_tables(tables, q_lower)
        
        # Build COMPACT schema with SHORT ALIASES
        tables_info = []
        all_columns = set()
        primary_table = None
        table_aliases = {}  # Map short alias to full name
        
        for i, table in enumerate(relevant_tables):
            table_name = table.get('table_name', '')
            columns = table.get('columns', [])
            if columns and isinstance(columns[0], dict):
                col_names = [c.get('name', str(c)) for c in columns]
            else:
                col_names = [str(c) for c in columns] if columns else []
            row_count = table.get('row_count', 0)
            
            all_columns.update(col_names)
            
            # Create SHORT alias from table name
            short_name = table_name.split('__')[-1] if '__' in table_name else table_name
            table_aliases[short_name] = table_name
            
            # First relevant table is "primary"
            if i == 0:
                primary_table = short_name
            
            # Only include sample for primary table
            sample_str = ""
            if i == 0:
                try:
                    rows, cols = self.structured_handler.execute_query(f'SELECT * FROM "{table_name}" LIMIT 2')
                    if rows and cols:
                        samples = []
                        for col in cols[:4]:  # Limit to 4 columns
                            vals = set(str(row.get(col, ''))[:15] for row in rows if row.get(col))
                            if vals:
                                samples.append(f"    {col}: {', '.join(list(vals)[:2])}")
                        sample_str = "\n  Sample:\n" + "\n".join(samples[:4]) if samples else ""
                except:
                    pass
            
            # Compact column list
            col_str = ', '.join(col_names[:15])
            if len(col_names) > 15:
                col_str += f" (+{len(col_names) - 15} more)"
            
            # Use SHORT name in schema
            tables_info.append(f"Table: {short_name}\n  Columns: {col_str}\n  Rows: {row_count}{sample_str}")
        
        # Store aliases for SQL post-processing
        self._table_aliases = table_aliases
        
        schema_text = '\n\n'.join(tables_info)
        
        # SIMPLIFIED relationships - only between relevant tables
        relationships_text = ""
        if self.relationships and len(relevant_tables) > 1:
            relevant_table_names = {t.get('table_name', '') for t in relevant_tables}
            rel_lines = []
            for rel in self.relationships[:10]:
                src_table = rel.get('source_table', '')
                tgt_table = rel.get('target_table', '')
                if src_table in relevant_table_names and tgt_table in relevant_table_names:
                    src = f"{src_table.split('__')[-1]}.{rel.get('source_column')}"
                    tgt = f"{tgt_table.split('__')[-1]}.{rel.get('target_column')}"
                    rel_lines.append(f"  {src} → {tgt}")
            if rel_lines:
                relationships_text = "\n\nJOIN ON:\n" + "\n".join(rel_lines[:5])
        
        # BUILD FILTER INSTRUCTIONS FROM CONFIRMED FACTS (for post-injection)
        filter_instructions = self._build_filter_instructions(relevant_tables)
        logger.warning(f"[SQL-GEN] filter_instructions: {filter_instructions if filter_instructions else 'NONE'}")
        
        # Simple hint for COUNT queries (no filter - we inject it after)
        query_hint = ""
        if 'how many' in q_lower or 'count' in q_lower:
            query_hint = f"\n\nHINT: For COUNT, use: SELECT COUNT(*) FROM \"{primary_table}\""
        
        prompt = f"""SCHEMA:
{schema_text}{relationships_text}
{query_hint}

QUESTION: {question}

RULES:
1. Use ONLY columns from schema above
2. ILIKE for text matching
3. Quote table names with special chars

SQL:"""
        
        logger.warning(f"[SQL-GEN] Calling orchestrator ({len(prompt)} chars, {len(relevant_tables)} tables)")
        
        result = orchestrator.generate_sql(prompt, all_columns)
        
        if result.get('success') and result.get('sql'):
            sql = result['sql'].strip()
            
            # Clean markdown
            if '```' in sql:
                sql = re.sub(r'```sql\s*', '', sql, flags=re.IGNORECASE)
                sql = re.sub(r'```\s*$', '', sql)
                sql = sql.replace('```', '').strip()
            
            # EXPAND short aliases to full table names WITH alias preservation
            if hasattr(self, '_table_aliases') and self._table_aliases:
                for short_name, full_name in self._table_aliases.items():
                    # Replace FROM short_name → FROM "full_name" AS short_name
                    sql = re.sub(
                        rf'\bFROM\s+{re.escape(short_name)}\b(?!\s+AS)',
                        f'FROM "{full_name}" AS {short_name}',
                        sql,
                        flags=re.IGNORECASE
                    )
                    sql = re.sub(
                        rf'\bFROM\s+"{re.escape(short_name)}"(?!\s+AS)',
                        f'FROM "{full_name}" AS {short_name}',
                        sql,
                        flags=re.IGNORECASE
                    )
                    # Replace JOIN short_name → JOIN "full_name" AS short_name
                    sql = re.sub(
                        rf'\bJOIN\s+{re.escape(short_name)}\b(?!\s+AS)',
                        f'JOIN "{full_name}" AS {short_name}',
                        sql,
                        flags=re.IGNORECASE
                    )
                    sql = re.sub(
                        rf'\bJOIN\s+"{re.escape(short_name)}"(?!\s+AS)',
                        f'JOIN "{full_name}" AS {short_name}',
                        sql,
                        flags=re.IGNORECASE
                    )
                logger.warning(f"[SQL-GEN] After alias expansion: {sql[:200]}")
            
            # INJECT FILTER CLAUSE (data-driven, not LLM-generated)
            logger.warning(f"[SQL-GEN] About to inject, filter_instructions={filter_instructions}")
            if filter_instructions:
                sql = self._inject_where_clause(sql, filter_instructions)
                logger.warning(f"[SQL-GEN] After filter injection: {sql[:200]}")
            
            # FIX STATE NAME PATTERNS - convert "Texas" to "TX" etc in ILIKE clauses
            sql = self._fix_state_names_in_sql(sql)
            
            logger.warning(f"[SQL-GEN] Generated: {sql[:150]}")
            
            # Detect query type
            sql_upper = sql.upper()
            if 'COUNT(' in sql_upper:
                query_type = 'count'
            elif 'SUM(' in sql_upper:
                query_type = 'sum'
            elif 'AVG(' in sql_upper:
                query_type = 'average'
            else:
                query_type = 'list'
            
            table_match = re.search(r'FROM\s+"?([^"\s]+)"?', sql, re.IGNORECASE)
            table_name = table_match.group(1) if table_match else 'unknown'
            
            return {
                'sql': sql,
                'table': table_name,
                'query_type': query_type,
                'all_columns': all_columns
            }
        
        return None
    
    def _try_fix_sql_from_error(self, sql: str, error_msg: str, all_columns: set) -> Optional[str]:
        """Try to fix SQL based on error message."""
        from difflib import SequenceMatcher
        
        patterns = [
            r'does not have a column named "([^"]+)"',
            r'Referenced column "([^"]+)" not found',
            r'column "([^"]+)" not found',
        ]
        
        bad_col = None
        for pattern in patterns:
            match = re.search(pattern, error_msg, re.IGNORECASE)
            if match:
                bad_col = match.group(1)
                break
        
        if not bad_col:
            return None
        
        valid_cols_lower = {c.lower() for c in all_columns}
        
        known_fixes = {
            'rate': 'hourly_pay_rate',
            'hourly_rate': 'hourly_pay_rate',
            'pay_rate': 'hourly_pay_rate',
            'employee_id': 'employee_number',
            'emp_id': 'employee_number',
        }
        
        fix = known_fixes.get(bad_col.lower())
        if fix and fix.lower() in valid_cols_lower:
            logger.info(f"[SQL-FIX] {bad_col} → {fix}")
            return re.sub(r'\b' + re.escape(bad_col) + r'\b', f'"{fix}"', sql, flags=re.IGNORECASE)
        
        # Fuzzy match
        if '_' in bad_col:
            best_score = 0.6
            for col in all_columns:
                score = SequenceMatcher(None, bad_col.lower(), col.lower()).ratio()
                if score > best_score:
                    best_score = score
                    fix = col
            if fix:
                logger.info(f"[SQL-FIX] Fuzzy: {bad_col} → {fix}")
                return re.sub(r'\b' + re.escape(bad_col) + r'\b', f'"{fix}"', sql, flags=re.IGNORECASE)
        
        return None
    
    def _gather_reality(self, question: str, analysis: Dict) -> List[Truth]:
        """Gather REALITY - what the customer's DATA shows."""
        if not self.structured_handler or not self.schema:
            return []
        
        truths = []
        domains = analysis.get('domains', ['general'])
        
        # Pattern cache
        pattern_cache = None
        try:
            from utils.sql_pattern_cache import initialize_patterns
            if self.project:
                pattern_cache = initialize_patterns(self.project, self.schema)
        except:
            try:
                from backend.utils.sql_pattern_cache import initialize_patterns
                if self.project:
                    pattern_cache = initialize_patterns(self.project, self.schema)
            except:
                pass
        
        try:
            sql = None
            sql_source = None
            sql_info = None
            
            # Check cache
            if pattern_cache:
                cached = pattern_cache.find_matching_pattern(question)
                if cached and cached.get('sql'):
                    sql = cached['sql']
                    sql_source = 'cache'
                    logger.warning("[SQL] Cache hit!")
            
            # Generate if no cache
            if not sql:
                sql_info = self._generate_sql_for_question(question, analysis)
                if sql_info:
                    sql = sql_info['sql']
                    sql_source = 'llm'
            
            # Execute
            if sql:
                for attempt in range(3):
                    try:
                        rows, cols = self.structured_handler.execute_query(sql)
                        self.last_executed_sql = sql
                        
                        if rows:
                            table_name = sql_info.get('table', 'query') if sql_info else 'query'
                            
                            truths.append(Truth(
                                source_type='reality',
                                source_name=f"SQL: {table_name}",
                                content={
                                    'sql': sql,
                                    'columns': cols,
                                    'rows': rows,
                                    'total': len(rows),
                                    'query_type': sql_info.get('query_type', 'list') if sql_info else 'list',
                                    'table': table_name,
                                    'is_targeted_query': True
                                },
                                confidence=0.98,
                                location=f"Query: {sql}"
                            ))
                            
                            if pattern_cache and sql_source == 'llm':
                                pattern_cache.learn_pattern(question, sql, success=True)
                            
                            return truths
                        break
                        
                    except Exception as e:
                        error_msg = str(e)
                        logger.warning(f"[SQL] Failed attempt {attempt + 1}: {error_msg}")
                        
                        if sql_info and attempt < 2:
                            fixed = self._try_fix_sql_from_error(sql, error_msg, sql_info.get('all_columns', set()))
                            if fixed and fixed != sql:
                                sql = fixed
                                continue
                        break
        
        except Exception as e:
            logger.error(f"Error gathering reality: {e}")
        
        return truths
    
    def _gather_intent(self, question: str, analysis: Dict) -> List[Truth]:
        """Gather INTENT - what customer's DOCUMENTS say."""
        if not self.rag_handler:
            return []
        
        truths = []
        
        try:
            collection_name = self._get_document_collection_name()
            if not collection_name:
                return []
            
            results = self.rag_handler.search(
                collection_name=collection_name,
                query=question,
                n_results=10,
                project_id=self.project if self.project else None
            )
            
            for result in results:
                metadata = result.get('metadata', {})
                distance = result.get('distance', 1.0)
                doc = result.get('document', '')
                
                project_id = metadata.get('project_id', '').lower()
                if project_id in ['global', '__global__', 'global/universal']:
                    continue
                
                truths.append(Truth(
                    source_type='intent',
                    source_name=metadata.get('filename', 'Document'),
                    content=doc,
                    confidence=max(0.3, 1.0 - distance) if distance else 0.7,
                    location=f"Page {metadata.get('page', '?')}"
                ))
        
        except Exception as e:
            logger.error(f"Error gathering intent: {e}")
        
        return truths
    
    def _get_document_collection_name(self) -> Optional[str]:
        """Find the document collection name."""
        if not self.rag_handler:
            return None
        
        if hasattr(self, '_doc_collection_name'):
            return self._doc_collection_name
        
        try:
            collections = self.rag_handler.list_collections()
            for name in ['hcmpact_docs', 'documents', 'hcm_docs', 'xlr8_docs']:
                if name in collections:
                    self._doc_collection_name = name
                    return name
            
            for name in collections:
                if 'doc' in name.lower():
                    self._doc_collection_name = name
                    return name
            
            if collections:
                self._doc_collection_name = collections[0]
                return collections[0]
        except:
            pass
        
        return None
    
    def _gather_best_practice(self, question: str, analysis: Dict) -> List[Truth]:
        """Gather BEST PRACTICE - what UKG docs say."""
        if not self.rag_handler:
            return []
        
        truths = []
        
        try:
            collection_name = self._get_document_collection_name()
            if not collection_name:
                return []
            
            results = self.rag_handler.search(
                collection_name=collection_name,
                query=question,
                n_results=10,
                project_id="Global/Universal"
            )
            
            for result in results:
                metadata = result.get('metadata', {})
                distance = result.get('distance', 1.0)
                doc = result.get('document', '')
                
                truths.append(Truth(
                    source_type='best_practice',
                    source_name=metadata.get('filename', 'UKG Documentation'),
                    content=doc,
                    confidence=max(0.3, 1.0 - distance) if distance else 0.7,
                    location=f"Page {metadata.get('page', '?')}"
                ))
        
        except Exception as e:
            logger.error(f"Error gathering best practice: {e}")
        
        return truths
    
    def _detect_conflicts(self, reality, intent, best_practice) -> List[Conflict]:
        return []
    
    def _run_proactive_checks(self, analysis: Dict) -> List[Insight]:
        insights = []
        
        if not self.structured_handler:
            return insights
        
        try:
            tables = self.schema.get('tables', [])
            domains = analysis.get('domains', ['general'])
            
            if 'employees' in domains or domains == ['general']:
                for table in tables:
                    table_name = table.get('table_name', '')
                    if any(c in table_name.lower() for c in ['personal', 'employee']):
                        try:
                            sql = f'SELECT COUNT(*) as cnt FROM "{table_name}" WHERE ssn IS NULL OR ssn = \'\''
                            result = self.structured_handler.conn.execute(sql).fetchone()
                            if result and result[0] > 0:
                                insights.append(Insight(
                                    type='anomaly',
                                    title='Missing SSN',
                                    description=f'{result[0]} employees missing SSN',
                                    data={'count': result[0]},
                                    severity='high',
                                    action_required=True
                                ))
                        except:
                            pass
                        break
        except:
            pass
        
        return insights
    
    def _synthesize_answer(
        self,
        question: str,
        mode: IntelligenceMode,
        reality: List[Truth],
        intent: List[Truth],
        best_practice: List[Truth],
        conflicts: List[Conflict],
        insights: List[Insight],
        context: Dict = None
    ) -> SynthesizedAnswer:
        """Synthesize answer from all sources."""
        reasoning = []
        context_parts = []
        
        if reality:
            context_parts.append("=== DATA RESULTS ===")
            for truth in reality[:3]:
                if isinstance(truth.content, dict) and 'rows' in truth.content:
                    rows = truth.content['rows']
                    cols = truth.content['columns']
                    query_type = truth.content.get('query_type', 'list')
                    
                    if query_type == 'count' and rows:
                        count_val = list(rows[0].values())[0] if rows[0] else 0
                        context_parts.append(f"\n**ANSWER: {count_val}**")
                        context_parts.append(f"SQL: {truth.content.get('sql', '')[:200]}")
                    elif query_type in ['sum', 'average'] and rows:
                        result_val = list(rows[0].values())[0] if rows[0] else 0
                        context_parts.append(f"\n**RESULT: {result_val}**")
                        context_parts.append(f"SQL: {truth.content.get('sql', '')[:200]}")
                    else:
                        context_parts.append(f"\nResults ({len(rows)} rows):")
                        for row in rows[:10]:
                            row_str = " | ".join(f"{k}: {v}" for k, v in list(row.items())[:6])
                            context_parts.append(f"  {row_str}")
            reasoning.append(f"Found {len(reality)} data results")
        
        if intent:
            context_parts.append("\n=== CUSTOMER DOCS ===")
            for truth in intent[:3]:
                context_parts.append(f"\n{truth.source_name}: {str(truth.content)[:300]}")
            reasoning.append(f"Found {len(intent)} customer documents")
        
        if best_practice:
            context_parts.append("\n=== BEST PRACTICE ===")
            for truth in best_practice[:3]:
                context_parts.append(f"\n{truth.source_name}: {str(truth.content)[:300]}")
            reasoning.append(f"Found {len(best_practice)} best practice docs")
        
        if insights:
            context_parts.append("\n=== INSIGHTS ===")
            for insight in insights:
                icon = '🔴' if insight.severity == 'high' else '🟡'
                context_parts.append(f"{icon} {insight.title}: {insight.description}")
        
        combined = '\n'.join(context_parts)
        
        confidence = 0.5
        if reality:
            confidence += 0.3
        if intent:
            confidence += 0.1
        if best_practice:
            confidence += 0.05
        
        return SynthesizedAnswer(
            question=question,
            answer=combined,
            confidence=min(confidence, 0.95),
            from_reality=reality,
            from_intent=intent,
            from_best_practice=best_practice,
            conflicts=conflicts,
            insights=insights,
            structured_output=None,
            reasoning=reasoning,
            executed_sql=self.last_executed_sql
        )
    
    def clear_clarifications(self):
        """Clear confirmed facts."""
        self.confirmed_facts = {}
