"""
XLR8 INTELLIGENCE ENGINE v5.4
==============================

Deploy to: backend/utils/intelligence_engine.py

UPDATES:
- v5.4: Location column validation (rejects routing/bank columns)
        Schema fallback for state/province columns
        SQL fix uses common location column patterns (not just filter_candidates)
- v5.3: Added US state name→code fallback (universal knowledge)
        Data-driven approach first, state mapping as fallback
- v5.2: FULLY DATA-DRIVEN filters
        - Removed all hardcoded state/value mappings
        - Location detection uses lookups from _intelligence_lookups
        - Falls back to actual values in filter_candidates
        - Profiler now handles column classification via lookup matching
- v5.1: Filter override logic, location column validation
- v5.0: Fixed state detection, LLM location filter stripping
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
logger.warning("[INTELLIGENCE_ENGINE] ====== v5.4 LOCATION COLUMN VALIDATION ======")


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
        
        # LOCATION DETECTION - Fully data-driven from lookups and profile values
        if category == 'location':
            # STEP 1: Try to find location from lookups (DATA-DRIVEN)
            lookup_match = self._find_value_in_lookups(q_lower, 'location')
            if lookup_match:
                logger.warning(f"[FILTER-DETECT] Found location '{lookup_match}' from lookup")
                return lookup_match
            
            # STEP 2: Check actual values in data from filter_candidates
            for candidate in candidates:
                values = candidate.get('values', [])
                for value in values:
                    value_str = str(value).strip()
                    value_lower = value_str.lower()
                    
                    # Skip very short values and blocklisted common words
                    if len(value_str) < 2 or _is_blocklisted(value_lower):
                        continue
                    
                    # Check if value appears in question with word boundary
                    if _is_word_boundary_match(q_lower, value_lower):
                        logger.warning(f"[FILTER-DETECT] Found location value '{value_str}' in question")
                        return value_str
                    
                    # Also check for the code's description from lookups
                    description = self._get_lookup_description('location', value_str)
                    if description and _is_word_boundary_match(q_lower, description.lower()):
                        logger.warning(f"[FILTER-DETECT] Found location '{description}' → code '{value_str}'")
                        return value_str
            
            # STEP 3: US State name→code mapping (universal knowledge fallback)
            # This is acceptable because US state abbreviations are standardized
            state_code = self._detect_us_state_in_question(q_lower)
            if state_code:
                logger.warning(f"[FILTER-DETECT] Found US state → '{state_code}' via standard mapping")
                return state_code
            
            return None
        
        # COMPANY DETECTION - Data-driven from lookups and profile values
        if category == 'company':
            # Try lookups first
            lookup_match = self._find_value_in_lookups(q_lower, 'company')
            if lookup_match:
                logger.warning(f"[FILTER-DETECT] Found company '{lookup_match}' from lookup")
                return lookup_match
            
            # Fall back to actual values in data
            for candidate in candidates:
                values = candidate.get('values', [])
                for value in values:
                    value_str = str(value).strip()
                    value_lower = value_str.lower()
                    if len(value_str) >= 3 and not _is_blocklisted(value_lower):
                        if _is_word_boundary_match(q_lower, value_lower):
                            logger.warning(f"[FILTER-DETECT] Found company '{value_str}' in question")
                            return value_str
                        # Check description from lookups
                        description = self._get_lookup_description('company', value_str)
                        if description and _is_word_boundary_match(q_lower, description.lower()):
                            logger.warning(f"[FILTER-DETECT] Found company '{description}' → code '{value_str}'")
                            return value_str
        
        # PAY TYPE DETECTION - Data-driven from lookups and profile values
        if category == 'pay_type':
            # Try lookups first
            lookup_match = self._find_value_in_lookups(q_lower, 'pay_type')
            if lookup_match:
                logger.warning(f"[FILTER-DETECT] Found pay_type '{lookup_match}' from lookup")
                return lookup_match
            
            # Fall back to actual values in data
            for candidate in candidates:
                values = candidate.get('values', [])
                for value in values:
                    value_str = str(value).strip()
                    value_lower = value_str.lower()
                    if len(value_str) >= 1 and not _is_blocklisted(value_lower):
                        if _is_word_boundary_match(q_lower, value_lower):
                            logger.warning(f"[FILTER-DETECT] Found pay_type '{value_str}' in question")
                            return value_str
                        # Check description from lookups
                        description = self._get_lookup_description('pay_type', value_str)
                        if description and _is_word_boundary_match(q_lower, description.lower()):
                            logger.warning(f"[FILTER-DETECT] Found pay_type '{description}' → code '{value_str}'")
                            return value_str
        
        # EMPLOYEE TYPE DETECTION - Data-driven from lookups and profile values
        if category == 'employee_type':
            # Try lookups first
            lookup_match = self._find_value_in_lookups(q_lower, 'employee_type')
            if lookup_match:
                logger.warning(f"[FILTER-DETECT] Found employee_type '{lookup_match}' from lookup")
                return lookup_match
            
            # Fall back to actual values in data
            for candidate in candidates:
                values = candidate.get('values', [])
                for value in values:
                    value_str = str(value).strip()
                    value_lower = value_str.lower()
                    if len(value_str) >= 1 and not _is_blocklisted(value_lower):
                        if _is_word_boundary_match(q_lower, value_lower):
                            logger.warning(f"[FILTER-DETECT] Found employee_type '{value_str}' in question")
                            return value_str
                        # Check description from lookups
                        description = self._get_lookup_description('employee_type', value_str)
                        if description and _is_word_boundary_match(q_lower, description.lower()):
                            logger.warning(f"[FILTER-DETECT] Found employee_type '{description}' → code '{value_str}'")
                            return value_str
        
        # GENERIC: Check any category against lookups and actual values
        # Try lookups first
        lookup_match = self._find_value_in_lookups(q_lower, category)
        if lookup_match:
            logger.warning(f"[FILTER-DETECT] Found {category} '{lookup_match}' from lookup")
            return lookup_match
        
        # Fall back to actual values in data
        for candidate in candidates:
            values = candidate.get('values', [])
            for value in values:
                value_str = str(value).strip()
                value_lower = value_str.lower()
                if len(value_str) > 2 and not _is_blocklisted(value_lower):
                    if _is_word_boundary_match(q_lower, value_lower):
                        logger.warning(f"[FILTER-DETECT] Found {category} value '{value_str}' in question")
                        return value_str
        
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
    
    def _find_value_in_lookups(self, q_lower: str, lookup_type: str) -> Optional[str]:
        """
        Search lookups for a value mentioned in the question.
        Returns the code if found, None otherwise.
        
        DATA-DRIVEN: Uses lookups from _intelligence_lookups table.
        """
        if not self.structured_handler or not hasattr(self.structured_handler, 'conn'):
            return None
        
        try:
            # Load lookups for this type
            lookups = self.structured_handler.conn.execute("""
                SELECT code_column, lookup_data_json
                FROM _intelligence_lookups
                WHERE project_name = ? AND lookup_type = ?
            """, [self.project, lookup_type]).fetchall()
            
            for code_col, lookup_json in lookups:
                if not lookup_json:
                    continue
                    
                lookup_data = json.loads(lookup_json)
                
                # Check each code→description pair
                for code, description in lookup_data.items():
                    code_lower = str(code).lower()
                    desc_lower = str(description).lower() if description else ''
                    
                    # Check if description appears in question
                    if desc_lower and len(desc_lower) > 2:
                        if _is_word_boundary_match(q_lower, desc_lower):
                            return code
                    
                    # Check if code appears in question (for longer codes)
                    if len(code_lower) > 2 and not _is_blocklisted(code_lower):
                        if _is_word_boundary_match(q_lower, code_lower):
                            return code
            
            return None
            
        except Exception as e:
            logger.debug(f"[LOOKUP] Failed to search lookups: {e}")
            return None
    
    def _get_lookup_description(self, lookup_type: str, code: str) -> Optional[str]:
        """
        Get the description for a code from lookups.
        
        DATA-DRIVEN: Uses lookups from _intelligence_lookups table.
        """
        if not self.structured_handler or not hasattr(self.structured_handler, 'conn') or not code:
            return None
        
        try:
            lookups = self.structured_handler.conn.execute("""
                SELECT lookup_data_json
                FROM _intelligence_lookups
                WHERE project_name = ? AND lookup_type = ?
            """, [self.project, lookup_type]).fetchall()
            
            code_upper = str(code).upper().strip()
            
            for (lookup_json,) in lookups:
                if not lookup_json:
                    continue
                    
                lookup_data = json.loads(lookup_json)
                
                # Try exact match first
                if code_upper in lookup_data:
                    return lookup_data[code_upper]
                
                # Try case-insensitive
                for k, v in lookup_data.items():
                    if str(k).upper().strip() == code_upper:
                        return v
            
            return None
            
        except Exception as e:
            logger.debug(f"[LOOKUP] Failed to get description: {e}")
            return None
    
    def _detect_us_state_in_question(self, q_lower: str) -> Optional[str]:
        """
        Detect US state names in question and return state code.
        
        This is UNIVERSAL KNOWLEDGE fallback - US state abbreviations are standardized.
        Used only when data-driven lookups don't find a match.
        """
        # US States - full name to code mapping
        us_states = {
            'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR',
            'california': 'CA', 'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE',
            'florida': 'FL', 'georgia': 'GA', 'hawaii': 'HI', 'idaho': 'ID',
            'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA', 'kansas': 'KS',
            'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
            'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS',
            'missouri': 'MO', 'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV',
            'new hampshire': 'NH', 'new jersey': 'NJ', 'new mexico': 'NM', 'new york': 'NY',
            'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH', 'oklahoma': 'OK',
            'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
            'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT',
            'vermont': 'VT', 'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV',
            'wisconsin': 'WI', 'wyoming': 'WY'
        }
        
        for state_name, state_code in us_states.items():
            if _is_word_boundary_match(q_lower, state_name):
                return state_code
        
        return None

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
            col_name = candidate.get('column_name', candidate.get('column', '')).lower()
            total_count = candidate.get('distinct_count', candidate.get('total_count', 0))
            col_type = candidate.get('inferred_type', candidate.get('type', ''))
            
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
        
        col_name = best_candidate.get('column_name', best_candidate.get('column'))
        table_name = best_candidate.get('table_name', best_candidate.get('table', ''))
        logger.warning(f"[CLARIFICATION] Using status column: {col_name} from {table_name.split('__')[-1]}")
        
        col_type = best_candidate.get('inferred_type', best_candidate.get('type', ''))
        
        # Handle termination_date (date type)
        if col_type == 'date':
            total = best_candidate.get('distinct_count', best_candidate.get('total_count', 0))
            null_count = best_candidate.get('null_count', 0)
            active_count = null_count  # null termination_date = active
            termed_count = total - null_count
            
            return [
                {'id': 'active', 'label': f'Active only ({active_count:,} employees)', 'default': True},
                {'id': 'termed', 'label': f'Terminated only ({termed_count:,} employees)'},
                {'id': 'all', 'label': f'All employees ({total:,} total)'}
            ]
        
        # Handle categorical status column (A/T codes)
        values = best_candidate.get('distinct_values', best_candidate.get('values', []))
        distribution = best_candidate.get('value_distribution', best_candidate.get('distribution', {}))
        total = best_candidate.get('distinct_count', best_candidate.get('total_count', 0))
        
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
                col_name = candidate.get('column_name', candidate.get('column', '')).lower()
                total_count = candidate.get('distinct_count', candidate.get('total_count', 0))
                col_type = candidate.get('inferred_type', candidate.get('type', ''))
                
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
                col_name = best_candidate.get('column_name', best_candidate.get('column'))
                col_type = best_candidate.get('inferred_type', best_candidate.get('type'))
                values = best_candidate.get('distinct_values', best_candidate.get('values', []))
                
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
                col_name = company_candidates[0].get('column_name', company_candidates[0].get('column'))
                filters.append(f"{col_name} = '{company_filter}'")
        
        # LOCATION FILTER
        location_filter = self.confirmed_facts.get('location')
        if location_filter and location_filter != 'all':
            location_candidates = self.filter_candidates.get('location', [])
            
            # Find a VALID location column (reject routing numbers, bank fields, etc.)
            # This is a safety net for cached profiles from before the profiler fix
            location_positive = ['state', 'province', 'stateprovince', 'location', 'region', 'city', 'county', 'country', 'site', 'geo']
            location_negative = ['routing', 'bank', 'account', 'aba', 'swift', 'transit', 'branch_number', 'bsb']
            
            valid_col = None
            valid_table = None
            
            # First try filter_candidates
            for candidate in location_candidates:
                col_name = candidate.get('column_name', candidate.get('column', ''))
                col_lower = col_name.lower()
                
                # Skip if column name contains invalid patterns
                if any(neg in col_lower for neg in location_negative):
                    logger.warning(f"[SQL-GEN] Skipping invalid location column: {col_name}")
                    continue
                
                # Prefer columns with location-related names
                if any(pos in col_lower for pos in location_positive):
                    valid_col = col_name
                    valid_table = candidate.get('table_name', candidate.get('table'))
                    break
                
                # Accept as fallback if no obvious red flags
                if not valid_col:
                    valid_col = col_name
                    valid_table = candidate.get('table_name', candidate.get('table'))
            
            # Fallback: search schema for state/province columns if no valid candidate
            if not valid_col and self.schema:
                for table_name, table_info in self.schema.items():
                    columns = table_info.get('columns', [])
                    for col in columns:
                        col_lower = col.lower() if isinstance(col, str) else str(col).lower()
                        if any(pos in col_lower for pos in ['state', 'province', 'stateprovince']):
                            valid_col = col
                            valid_table = table_name
                            logger.warning(f"[SQL-GEN] Found location column from schema: {table_name}.{col}")
                            break
                    if valid_col:
                        break
            
            if valid_col:
                filters.append(f"{valid_col} = '{location_filter}'")
                logger.warning(f"[SQL-GEN] Location filter: {valid_col} = '{location_filter}'")
            else:
                logger.warning(f"[SQL-GEN] No valid location column found, skipping location filter")
        
        # PAY TYPE FILTER
        pay_type_filter = self.confirmed_facts.get('pay_type')
        if pay_type_filter and pay_type_filter != 'all':
            pay_candidates = self.filter_candidates.get('pay_type', [])
            if pay_candidates:
                col_name = pay_candidates[0].get('column_name', pay_candidates[0].get('column'))
                values = pay_candidates[0].get('distinct_values', pay_candidates[0].get('values', []))
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
                col_name = emp_candidates[0].get('column_name', emp_candidates[0].get('column'))
                values = emp_candidates[0].get('distinct_values', emp_candidates[0].get('values', []))
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
        
        # Common location column patterns to strip (LLM might use any of these)
        location_col_patterns = [
            'stateprovince', 'state_province', 'state', 'province', 
            'work_state', 'home_state', 'location', 'work_location'
        ]
        
        modified = sql
        
        for col_name in location_col_patterns:
            # Strip patterns like: column ILIKE '%anything%'
            # This removes the LLM's location filter so our injection can add the correct one
            
            # Pattern 0: WHERE col ILIKE '...' AND ... → WHERE ...
            pattern0 = rf"WHERE\s+{re.escape(col_name)}\s+ILIKE\s+'%?[^']+%?'\s*AND\s*"
            modified = re.sub(pattern0, 'WHERE ', modified, flags=re.IGNORECASE)
            
            # Pattern 1: ... AND col ILIKE '...' AND ... → ... AND ...
            pattern1 = rf"{re.escape(col_name)}\s+ILIKE\s+'%?[^']+%?'\s*AND\s*"
            modified = re.sub(pattern1, '', modified, flags=re.IGNORECASE)
            
            # Pattern 2: ... AND col ILIKE '...' (at end) → ...
            pattern2 = rf"\s*AND\s+{re.escape(col_name)}\s+ILIKE\s+'%?[^']+%?'"
            modified = re.sub(pattern2, '', modified, flags=re.IGNORECASE)
            
            # Pattern 3: WHERE col = 'StateName' AND ... → WHERE ...
            pattern3 = rf"WHERE\s+{re.escape(col_name)}\s*=\s*'[A-Za-z\s]+'\s*AND\s*"
            modified = re.sub(pattern3, 'WHERE ', modified, flags=re.IGNORECASE)
            
            # Pattern 4: ... AND col = 'StateName' (at end) → ...  
            pattern4 = rf"\s*AND\s+{re.escape(col_name)}\s*=\s*'[A-Za-z\s]+'"
            modified = re.sub(pattern4, '', modified, flags=re.IGNORECASE)
            
            # Pattern 5: WHERE col ILIKE '...' (standalone, no AND) → WHERE 1=1
            pattern5 = rf"WHERE\s+{re.escape(col_name)}\s+ILIKE\s+'%?[^']+%?'\s*$"
            modified = re.sub(pattern5, 'WHERE 1=1 ', modified, flags=re.IGNORECASE)
        
        if modified != sql:
            logger.warning(f"[SQL-FIX] Stripped LLM location filter, will use confirmed_facts['location']={location_filter}")
        
        if modified != sql:
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
        
        IMPORTANT: Always includes tables containing filter_candidate columns
        so the LLM can build proper JOINs for compound queries.
        """
        if not tables:
            return []
        
        # First, identify tables that contain filter_candidate columns
        # These MUST be included for compound queries to work
        filter_candidate_tables = set()
        if self.filter_candidates:
            for category, candidates in self.filter_candidates.items():
                for cand in candidates:
                    table_name = cand.get('table_name', cand.get('table', ''))
                    if table_name:
                        filter_candidate_tables.add(table_name.lower())
        
        logger.info(f"[SQL-GEN] Filter candidate tables: {filter_candidate_tables}")
        
        # Priority keywords for table selection
        table_keywords = {
            'personal': ['employee', 'employees', 'person', 'people', 'who', 'name', 'ssn', 'birth', 'hire', 'termination', 'termed', 'terminated', 'active'],
            'company': ['company', 'organization', 'org', 'entity', 'status'],
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
            
            # CRITICAL: Boost tables that have filter_candidate columns
            if table_name in filter_candidate_tables:
                score += 50  # Very high score to ensure inclusion
                logger.info(f"[SQL-GEN] Boosting table {short_name} (has filter candidates)")
            
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
        
        # Take top 5 tables (increased from 3 to handle compound queries)
        relevant = [t for score, t in scored_tables[:5] if score > 0]
        
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
                    rows = self.structured_handler.query(f'SELECT * FROM "{table_name}" LIMIT 2')
                    cols = list(rows[0].keys()) if rows else []
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
        
        # BUILD SEMANTIC HINTS from filter_candidates
        # This tells the LLM which columns to use for specific purposes
        # For simple queries, only include columns from the primary table
        semantic_hints = []
        
        # Get primary table name for filtering
        primary_table_full = relevant_tables[0].get('table_name', '') if relevant_tables else ''
        primary_table_short = primary_table_full.split('__')[-1] if '__' in primary_table_full else primary_table_full
        
        # Check if this is a simple "by X" query (should avoid JOINs)
        is_simple_query = bool(re.search(r'\bshow\s+\w+.*\bby\s+\w+', q_lower)) or bool(re.search(r'\bhow many\b', q_lower))
        
        if self.filter_candidates:
            for category, candidates in self.filter_candidates.items():
                if not candidates:
                    continue
                    
                if category == 'status':
                    # Status can have multiple useful columns - list them all
                    date_cols = []
                    code_cols = []
                    for cand in candidates:
                        col_name = cand.get('column_name', cand.get('column', ''))
                        col_type = cand.get('inferred_type', cand.get('type', ''))
                        table_name = cand.get('table_name', cand.get('table', ''))
                        short_table = table_name.split('__')[-1] if '__' in table_name else table_name
                        col_lower = col_name.lower()
                        logger.warning(f"[SQL-GEN] Status candidate column: {col_name} in {short_table} (type={col_type})")
                        # Check if this is a termination date column
                        is_term_date = (
                            col_type == 'date' or
                            'termination' in col_lower or 
                            'term_date' in col_lower or
                            'term_dt' in col_lower or
                            'termdate' in col_lower or
                            col_lower == 'term_date' or
                            col_lower.endswith('_term_date')
                        )
                        if is_term_date:
                            date_cols.append((f"{short_table}.{col_name}", col_lower))
                        else:
                            # Prioritize employment_status columns
                            priority = 0
                            if 'employment_status' in col_lower:
                                priority = 100
                            elif 'emp_status' in col_lower:
                                priority = 90
                            elif col_lower == 'status' or col_lower.endswith('_status'):
                                priority = 50
                            code_cols.append((f"{short_table}.{col_name}", priority))
                    
                    if date_cols:
                        semantic_hints.append(f"- For termination dates/timing: use {date_cols[0][0]}")
                    if code_cols:
                        # Sort by priority descending, pick best
                        code_cols.sort(key=lambda x: -x[1])
                        semantic_hints.append(f"- For employee status (active/termed): use {code_cols[0][0]}")
                else:
                    # Other categories - find column in primary table if possible
                    best = candidates[0]
                    col_name = best.get('column_name', best.get('column', ''))
                    table_name = best.get('table_name', best.get('table', ''))
                    short_table = table_name.split('__')[-1] if '__' in table_name else table_name
                    
                    # For simple queries, prefer columns in the primary table
                    if is_simple_query and short_table and short_table != primary_table_short:
                        # Try to find same column in primary table
                        found_in_primary = False
                        for cand in candidates:
                            cand_table = cand.get('table_name', cand.get('table', ''))
                            cand_short = cand_table.split('__')[-1] if '__' in cand_table else cand_table
                            if cand_short == primary_table_short:
                                col_name = cand.get('column_name', cand.get('column', ''))
                                short_table = cand_short
                                found_in_primary = True
                                break
                        
                        if not found_in_primary:
                            logger.warning(f"[SQL-GEN] Skipping hint for {category} - column not in primary table {primary_table_short}")
                            continue
                    
                    full_col = f"{short_table}.{col_name}" if short_table else col_name
                    
                    if category == 'location':
                        semantic_hints.append(f"- For location/state: use {full_col}")
                    elif category == 'company':
                        semantic_hints.append(f"- For company: use {full_col}")
                    elif category == 'organization':
                        semantic_hints.append(f"- For org/department: use {full_col}")
                    elif category == 'pay_type':
                        semantic_hints.append(f"- For pay type (hourly/salary): use {full_col}")
                    elif category == 'employee_type':
                        semantic_hints.append(f"- For employee type (regular/temp): use {full_col}")
                    elif category == 'job':
                        semantic_hints.append(f"- For job/position: use {full_col}")
        
        semantic_text = ""
        if semantic_hints:
            # Add note about automatic status filtering
            semantic_hints.insert(0, "NOTE: Status filtering (active/termed) is applied automatically - do not add WHERE clauses for it")
            semantic_text = "\n\nCOLUMN USAGE:\n" + "\n".join(semantic_hints)
            logger.warning(f"[SQL-GEN] Semantic hints: {len(semantic_hints)} column mappings added")
            for hint in semantic_hints:
                logger.warning(f"[SQL-GEN] Hint: {hint}")
        
        # Build query hints based on question patterns
        query_hints = []
        
        # "Show X by Y" pattern - simple aggregation, no JOINs needed
        if re.search(r'\bshow\s+\w+\s+\w*\s*by\s+\w+', q_lower) or re.search(r'\bby\s+(job|state|location|company|month|year)\b', q_lower):
            query_hints.append(f"Use simple aggregation: SELECT column, COUNT(*) FROM {primary_table} GROUP BY column")
            query_hints.append("Do NOT use JOINs for simple counts")
        
        # COUNT hint
        if 'how many' in q_lower or 'count' in q_lower:
            query_hints.append(f"For COUNT, use: SELECT COUNT(*) FROM \"{primary_table}\"")
        
        # GROUP BY hint - detect "by X" patterns
        group_by_patterns = [
            (r'\bby\s+month\b', 'GROUP BY month - use strftime(\'%Y-%m\', TRY_CAST(date_column AS DATE)) to get YYYY-MM format'),
            (r'\bby\s+year\b', 'GROUP BY year - use EXTRACT(YEAR FROM date_column)'),
            (r'\bby\s+(state|location)\b', 'GROUP BY location/state column'),
            (r'\bby\s+(company|org)\b', 'GROUP BY company/organization column'),
            (r'\bby\s+(department|dept)\b', 'GROUP BY department/org column'),
        ]
        
        for pattern, hint in group_by_patterns:
            if re.search(pattern, q_lower):
                query_hints.append(hint)
                logger.warning(f"[SQL-GEN] Detected GROUP BY pattern: {pattern}")
        
        # Format all hints
        query_hint = ""
        if query_hints:
            query_hint = "\n\nHINTS:\n" + "\n".join(f"- {h}" for h in query_hints)
        
        prompt = f"""SCHEMA:
{schema_text}{relationships_text}{semantic_text}
{query_hint}

QUESTION: {question}

RULES:
1. Use ONLY columns from SCHEMA - never invent columns
2. DO NOT add WHERE for status/active/termed - filters injected automatically
3. For "show X by Y" queries: SELECT Y, COUNT(*) FROM table GROUP BY Y
4. Keep queries SIMPLE - avoid JOINs unless absolutely needed
5. ILIKE for text matching

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
            
            logger.warning(f"[SQL-GEN] LLM raw output: {sql[:200]}")
            
            # EXPAND short aliases to full table names WITH alias preservation
            # (?!\.) prevents matching table.column references like personal.termination_date
            if hasattr(self, '_table_aliases') and self._table_aliases:
                for short_name, full_name in self._table_aliases.items():
                    # Replace FROM short_name → FROM "full_name" AS short_name
                    sql = re.sub(
                        rf'\bFROM\s+{re.escape(short_name)}\b(?!\.)(?!\s+AS)',
                        f'FROM "{full_name}" AS {short_name}',
                        sql,
                        flags=re.IGNORECASE
                    )
                    sql = re.sub(
                        rf'\bFROM\s+"{re.escape(short_name)}"(?!\.)(?!\s+AS)',
                        f'FROM "{full_name}" AS {short_name}',
                        sql,
                        flags=re.IGNORECASE
                    )
                    # Replace JOIN short_name → JOIN "full_name" AS short_name
                    sql = re.sub(
                        rf'\bJOIN\s+{re.escape(short_name)}\b(?!\.)(?!\s+AS)',
                        f'JOIN "{full_name}" AS {short_name}',
                        sql,
                        flags=re.IGNORECASE
                    )
                    sql = re.sub(
                        rf'\bJOIN\s+"{re.escape(short_name)}"(?!\.)(?!\s+AS)',
                        f'JOIN "{full_name}" AS {short_name}',
                        sql,
                        flags=re.IGNORECASE
                    )
                logger.warning(f"[SQL-GEN] After alias expansion: {sql[:200]}")
            
            # STRIP LLM-generated status filters (we inject the correct one ourselves)
            # The LLM often ignores our "don't add status WHERE" instruction
            status_filter_patterns = [
                r"\bWHERE\s+\w*\.?employment_status_code\s*=\s*'[^']*'\s*",  # WHERE x.employment_status_code = 'TERM'
                r"\bAND\s+\w*\.?employment_status_code\s*=\s*'[^']*'\s*",    # AND x.employment_status_code = 'TERM'
                r"\bWHERE\s+\w*\.?employment_status\s*=\s*'[^']*'\s*",       # WHERE employment_status = 'X'
                r"\bAND\s+\w*\.?employment_status\s*=\s*'[^']*'\s*",
            ]
            for pattern in status_filter_patterns:
                if re.search(pattern, sql, re.IGNORECASE):
                    logger.warning(f"[SQL-GEN] Stripping LLM-generated status filter")
                    # If it was the only WHERE clause, remove it entirely
                    sql = re.sub(pattern, 'WHERE ', sql, count=1, flags=re.IGNORECASE)
                    # Clean up "WHERE AND" or "WHERE WHERE" that might result
                    sql = re.sub(r'\bWHERE\s+WHERE\b', 'WHERE', sql, flags=re.IGNORECASE)
                    sql = re.sub(r'\bWHERE\s+AND\b', 'WHERE', sql, flags=re.IGNORECASE)
                    sql = re.sub(r'\bWHERE\s+GROUP\b', 'GROUP', sql, flags=re.IGNORECASE)
                    sql = re.sub(r'\bWHERE\s+ORDER\b', 'ORDER', sql, flags=re.IGNORECASE)
                    sql = re.sub(r'\bWHERE\s*$', '', sql, flags=re.IGNORECASE)
            
            # INJECT FILTER CLAUSE (data-driven, not LLM-generated)
            logger.warning(f"[SQL-GEN] About to inject, filter_instructions={filter_instructions}")
            if filter_instructions:
                sql = self._inject_where_clause(sql, filter_instructions)
                logger.warning(f"[SQL-GEN] After filter injection: {sql[:200]}")
            
            # FIX STATE NAME PATTERNS - convert "Texas" to "TX" etc in ILIKE clauses
            sql = self._fix_state_names_in_sql(sql)
            
            # FIX DuckDB syntax: MONTH(x) → EXTRACT(MONTH FROM x)
            sql = re.sub(r'\bMONTH\s*\(\s*([^)]+)\s*\)', r'EXTRACT(MONTH FROM \1)', sql, flags=re.IGNORECASE)
            sql = re.sub(r'\bYEAR\s*\(\s*([^)]+)\s*\)', r'EXTRACT(YEAR FROM \1)', sql, flags=re.IGNORECASE)
            sql = re.sub(r'\bDAY\s*\(\s*([^)]+)\s*\)', r'EXTRACT(DAY FROM \1)', sql, flags=re.IGNORECASE)
            
            # FIX: Wrap columns with "date" in name in TRY_CAST for DATE_TRUNC and EXTRACT
            # This handles VARCHAR date columns that DuckDB can't process directly
            # Match any column name containing 'date' (case insensitive)
            # DATE_TRUNC('month', xxx_date) → DATE_TRUNC('month', TRY_CAST(xxx_date AS DATE))
            sql = re.sub(
                r"DATE_TRUNC\s*\(\s*'(\w+)'\s*,\s*(\w*date\w*)\s*\)",
                r"DATE_TRUNC('\1', TRY_CAST(\2 AS DATE))",
                sql, flags=re.IGNORECASE
            )
            # Also handle table.column format: DATE_TRUNC('month', personal.termination_date)
            sql = re.sub(
                r"DATE_TRUNC\s*\(\s*'(\w+)'\s*,\s*(\w+\.\w*date\w*)\s*\)",
                r"DATE_TRUNC('\1', TRY_CAST(\2 AS DATE))",
                sql, flags=re.IGNORECASE
            )
            
            # Wrap strftime on date columns in TRY_CAST (in case LLM used strftime directly)
            # strftime('%Y-%m', termination_date) → strftime('%Y-%m', TRY_CAST(termination_date AS DATE))
            sql = re.sub(
                r"strftime\s*\(\s*'([^']+)'\s*,\s*(\w*date\w*)\s*\)",
                r"strftime('\1', TRY_CAST(\2 AS DATE))",
                sql, flags=re.IGNORECASE
            )
            sql = re.sub(
                r"strftime\s*\(\s*'([^']+)'\s*,\s*(\w+\.\w*date\w*)\s*\)",
                r"strftime('\1', TRY_CAST(\2 AS DATE))",
                sql, flags=re.IGNORECASE
            )
            
            # EXTRACT(MONTH FROM xxx_date) → EXTRACT(MONTH FROM TRY_CAST(xxx_date AS DATE))
            sql = re.sub(
                r"EXTRACT\s*\(\s*(\w+)\s+FROM\s+(\w*date\w*)\s*\)",
                r"EXTRACT(\1 FROM TRY_CAST(\2 AS DATE))",
                sql, flags=re.IGNORECASE
            )
            # Also handle table.column format
            sql = re.sub(
                r"EXTRACT\s*\(\s*(\w+)\s+FROM\s+(\w+\.\w*date\w*)\s*\)",
                r"EXTRACT(\1 FROM TRY_CAST(\2 AS DATE))",
                sql, flags=re.IGNORECASE
            )
            
            # UPGRADE: Convert EXTRACT(MONTH FROM x) to strftime('%Y-%m', x) for year-month grouping
            # This gives us "2024-01" instead of just "1" which is much more useful
            if 'by month' in q_lower or 'per month' in q_lower:
                # Replace EXTRACT(MONTH FROM TRY_CAST(x AS DATE)) with strftime('%Y-%m', TRY_CAST(x AS DATE))
                sql = re.sub(
                    r"EXTRACT\s*\(\s*MONTH\s+FROM\s+TRY_CAST\s*\(\s*([^)]+)\s+AS\s+DATE\s*\)\s*\)",
                    r"strftime('%Y-%m', TRY_CAST(\1 AS DATE))",
                    sql, flags=re.IGNORECASE
                )
                # Also convert DATE_TRUNC('month', x) to strftime('%Y-%m', x)
                sql = re.sub(
                    r"DATE_TRUNC\s*\(\s*'month'\s*,\s*TRY_CAST\s*\(\s*([^)]+)\s+AS\s+DATE\s*\)\s*\)",
                    r"strftime('%Y-%m', TRY_CAST(\1 AS DATE))",
                    sql, flags=re.IGNORECASE
                )
                logger.warning("[SQL-GEN] Upgraded to strftime('%Y-%m') for year-month grouping")
            
            logger.warning(f"[SQL-GEN] Generated: {sql[:150]}")
            
            # AUTO-FIX: If question asks "by X" but SQL has no GROUP BY, add it
            sql_upper = sql.upper()
            if 'GROUP BY' not in sql_upper:
                # Check if question expects grouping
                group_match = re.search(r'\bby\s+(month|year|state|location|company|department)\b', q_lower)
                if group_match:
                    group_type = group_match.group(1)
                    logger.warning(f"[SQL-GEN] Question expects GROUP BY {group_type} but SQL has none - checking for aggregation")
                    
                    # Find if there's an alias we can GROUP BY
                    # Look for "AS month" or "AS termination_month" etc.
                    alias_match = re.search(rf'\bAS\s+(\w*{group_type}\w*)', sql, re.IGNORECASE)
                    if alias_match:
                        alias = alias_match.group(1)
                        # Add GROUP BY before ORDER BY or at end
                        if 'ORDER BY' in sql_upper:
                            sql = re.sub(r'\bORDER BY\b', f'GROUP BY {alias} ORDER BY', sql, flags=re.IGNORECASE)
                        else:
                            sql = sql.rstrip(';') + f' GROUP BY {alias}'
                        logger.warning(f"[SQL-GEN] Auto-added: GROUP BY {alias}")
            
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
        
        # Fix 1: VARCHAR column used with date functions - add TRY_CAST
        if 'date_part' in error_msg.lower() and 'VARCHAR' in error_msg:
            # Find EXTRACT(... FROM column_name) patterns and wrap in TRY_CAST
            pattern = r"EXTRACT\s*\(\s*(\w+)\s+FROM\s+(\w+)\s*\)"
            match = re.search(pattern, sql, re.IGNORECASE)
            if match:
                part = match.group(1)  # MONTH, YEAR, etc.
                col = match.group(2)   # column name
                fixed_sql = re.sub(
                    pattern,
                    f"EXTRACT({part} FROM TRY_CAST({col} AS DATE))",
                    sql,
                    flags=re.IGNORECASE
                )
                logger.info(f"[SQL-FIX] Added TRY_CAST for date extraction on {col}")
                return fixed_sql
        
        # Fix 2: Column not found errors
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
                        rows = self.structured_handler.query(sql)
                        cols = list(rows[0].keys()) if rows else []
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
