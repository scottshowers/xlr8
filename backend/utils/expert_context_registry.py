"""
EXPERT CONTEXT REGISTRY & AUTO-SELECTION
==========================================

Manages expert context prompts and automatically selects the best one
based on:
1. Project's detected domains
2. Question keywords
3. Historical feedback (learning)

NO HARDCODING - expert contexts are stored in database and refined by feedback.

Tables:
- expert_contexts: Stores expert prompt templates
- expert_context_usage: Tracks usage and feedback for learning

Author: XLR8 Team
Version: 1.0.0
"""

import logging
import re
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ExpertContext:
    """An expert context template."""
    id: str
    name: str
    domains: List[str]  # Domains this context applies to
    keywords: List[str]  # Keywords that trigger this context
    prompt_template: str  # The actual expert prompt
    
    # Metadata
    description: str = ""
    created_by: str = "system"
    is_active: bool = True
    
    # Learning stats
    usage_count: int = 0
    positive_feedback: int = 0
    negative_feedback: int = 0
    
    @property
    def effectiveness_score(self) -> float:
        """Calculate effectiveness based on feedback."""
        total = self.positive_feedback + self.negative_feedback
        if total == 0:
            return 0.5  # Neutral for new contexts
        return self.positive_feedback / total
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'name': self.name,
            'domains': self.domains,
            'keywords': self.keywords,
            'prompt_template': self.prompt_template,
            'description': self.description,
            'created_by': self.created_by,
            'is_active': self.is_active,
            'usage_count': self.usage_count,
            'positive_feedback': self.positive_feedback,
            'negative_feedback': self.negative_feedback,
            'effectiveness_score': self.effectiveness_score,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ExpertContext':
        return cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            domains=data.get('domains', []),
            keywords=data.get('keywords', []),
            prompt_template=data.get('prompt_template', ''),
            description=data.get('description', ''),
            created_by=data.get('created_by', 'system'),
            is_active=data.get('is_active', True),
            usage_count=data.get('usage_count', 0),
            positive_feedback=data.get('positive_feedback', 0),
            negative_feedback=data.get('negative_feedback', 0),
        )


@dataclass
class ContextMatch:
    """A matched expert context with relevance score."""
    context: ExpertContext
    match_score: float  # 0-1, how well it matches
    domain_match: float  # Score from domain matching
    keyword_match: float  # Score from keyword matching
    learning_boost: float  # Boost from positive feedback history
    
    def to_dict(self) -> Dict:
        return {
            'context_id': self.context.id,
            'context_name': self.context.name,
            'match_score': round(self.match_score, 3),
            'domain_match': round(self.domain_match, 3),
            'keyword_match': round(self.keyword_match, 3),
            'learning_boost': round(self.learning_boost, 3),
        }


# =============================================================================
# DEFAULT EXPERT CONTEXTS - Seeded from Year-End Playbook knowledge
# These are the STARTING point - system will learn and add more
# =============================================================================

DEFAULT_EXPERT_CONTEXTS = [
    {
        'id': 'tax_compliance',
        'name': 'Tax & Compliance Expert',
        'domains': ['tax', 'payroll'],
        'keywords': ['tax', 'sui', 'suta', 'futa', 'fein', 'ein', 'w2', 'w4', '941', '940', 
                    'withholding', 'exempt', 'taxable', 'jurisdiction', 'reciprocity', 'rate', 'rates', 'correct'],
        'description': 'Expert in payroll tax compliance, tax IDs, rates, and filing requirements',
        'prompt_template': """You are a TAX & COMPLIANCE EXPERT analyzing customer data.

WHEN ASKED IF RATES ARE "CORRECT" - ACTUALLY EVALUATE THEM:

SUI/SUTA RATE VALIDATION (State Unemployment):
- Valid range: 0.1% to 12.0% (rates outside this = RED FLAG)
- New employer rates: typically 2.0% to 5.0% for most states
- Rates change annually - check effective dates
- Each state has different min/max/new employer rates
- If rate is 0% or blank = PROBLEM (SUI is mandatory)
- If rate > 12% = LIKELY ERROR (no state goes above ~12%)

FUTA RATE VALIDATION:
- Standard rate: 6.0% (appears as 0.060 or 6.0)
- After FUTA credit: 0.6% (appears as 0.006 or 0.6)
- Credit reduction states add 0.3%+ to effective rate

FEIN/EIN VALIDATION:
- Format: XX-XXXXXXX (9 digits with hyphen after first 2)
- Cannot start with 07, 08, 09, 17, 18, 19, 28, 29, 49, 69, 70, 78, 79, 89

YOUR RESPONSE MUST:
1. State clearly if rates LOOK CORRECT or if there are ISSUES
2. List any specific values that are out of range
3. Flag missing or blank rates
4. Note any rates that need verification (edge cases)

Be direct. If the SUI rate is 2.5%, say "This SUI rate of 2.5% is within the valid range for most states."
If the rate is 0% or 99%, say "ISSUE: This rate appears incorrect."

Focus on specific, actionable findings with data evidence."""
    },
    {
        'id': 'employee_data',
        'name': 'Employee Data Expert',
        'domains': ['hr', 'payroll'],
        'keywords': ['employee', 'ssn', 'address', 'name', 'hire', 'term', 'status',
                    'demographic', 'personal', 'data quality', 'validation'],
        'description': 'Expert in employee master data quality and validation',
        'prompt_template': """CONSULTANT ANALYSIS - Apply your Employee Data expertise:

1. IDENTIFIER VALIDATION:
   - SSN format: XXX-XX-XXXX
   - Flag invalid: 000-XX-XXXX, XXX-00-XXXX, XXX-XX-0000
   - Flag ITINs (9XX): may need special handling
   - Check for duplicates or multiple SSNs per person

2. NAME VALIDATION:
   - Must match SSA records exactly for W-2
   - Flag special characters, extra spaces
   - Check Jr/Sr/III suffix handling
   - Legal name vs preferred name confusion

3. ADDRESS QUALITY:
   - Complete address required for mailings
   - Flag PO Boxes (restrictions in some states)
   - Verify state codes are valid
   - ZIP code format: XXXXX or XXXXX-XXXX

4. STATUS CONSISTENCY:
   - Terminated employees on active payroll
   - Active employees with term dates
   - Rehires with different data
   - Status code validity

Report specific counts and examples where possible."""
    },
    {
        'id': 'earnings_deductions',
        'name': 'Earnings & Deductions Expert',
        'domains': ['payroll', 'benefits'],
        'keywords': ['earnings', 'deduction', 'pay', 'wage', 'salary', 'bonus', 'benefit',
                    'pretax', 'posttax', 'cafeteria', '125', '401k', 'hsa', 'fsa'],
        'description': 'Expert in earnings codes, deduction setup, and benefit plans',
        'prompt_template': """CONSULTANT ANALYSIS - Apply your Earnings & Deductions expertise:

1. EARNINGS CODES:
   - Regular, overtime, bonus, commission
   - Verify tax treatment per code
   - Check supplemental wage handling
   - Fringe benefits (vehicle, GTL over $50k)

2. PRE-TAX DEDUCTIONS:
   - Section 125 (cafeteria) plans
   - HSA contributions - annual limits apply
   - FSA elections
   - 401(k)/403(b) contributions - annual limits

3. POST-TAX DEDUCTIONS:
   - Roth contributions
   - After-tax benefits
   - Garnishments and levies
   - Verify proper sequencing

4. W-2 IMPLICATIONS:
   - Box 12 codes for various benefits
   - Box 14 for informational items
   - Verify coding matches deduction setup

Flag any codes with incorrect tax treatment or missing W-2 mapping."""
    },
    {
        'id': 'general_data_analyst',
        'name': 'Data Analysis Expert',
        'domains': ['hr', 'payroll', 'benefits', 'time', 'gl'],
        'keywords': ['count', 'total', 'average', 'sum', 'compare', 'trend', 'analysis',
                    'report', 'breakdown', 'distribution', 'summary'],
        'description': 'General data analysis and reporting expertise',
        'prompt_template': """ANALYST APPROACH - Data-driven analysis:

1. UNDERSTAND THE QUESTION:
   - What specific metric or insight is needed?
   - What time period or scope?
   - Any filters or segments to apply?

2. ANALYZE THE DATA:
   - Start with the aggregate/summary
   - Break down by relevant dimensions
   - Look for patterns or anomalies
   - Compare to benchmarks if available

3. PRESENT FINDINGS:
   - Lead with the key number/insight
   - Provide context for interpretation
   - Note any data quality caveats
   - Suggest follow-up questions

Be specific about data sources and calculations used."""
    },
    {
        'id': 'gl_mapping',
        'name': 'GL & Financial Expert',
        'domains': ['gl', 'payroll'],
        'keywords': ['gl', 'general ledger', 'account', 'debit', 'credit', 'journal',
                    'posting', 'mapping', 'chart of accounts', 'cost center'],
        'description': 'Expert in GL mapping, journal entries, and financial posting',
        'prompt_template': """CONSULTANT ANALYSIS - Apply your GL & Financial expertise:

1. ACCOUNT MAPPING:
   - Verify account numbers are valid
   - Check segment structure matches target system
   - Identify unmapped earnings/deductions
   - Review cost center/department allocation

2. JOURNAL ENTRIES:
   - Debits must equal credits
   - Verify posting dates are correct period
   - Check for duplicate entries
   - Review reversal handling

3. RECONCILIATION:
   - Compare to source system totals
   - Identify timing differences
   - Flag out-of-balance conditions
   - Verify control totals

4. CONVERSION CONCERNS:
   - Historical data mapping
   - Opening balance setup
   - Multi-company consolidation

Provide specific account examples and variance details."""
    },
    {
        'id': 'time_attendance',
        'name': 'Time & Attendance Expert',
        'domains': ['time'],
        'keywords': ['time', 'hours', 'attendance', 'punch', 'schedule', 'shift',
                    'overtime', 'accrual', 'pto', 'leave', 'absence'],
        'description': 'Expert in time tracking, scheduling, and attendance management',
        'prompt_template': """CONSULTANT ANALYSIS - Apply your Time & Attendance expertise:

1. TIME DATA QUALITY:
   - Missing punches or incomplete records
   - Overlapping time entries
   - Excessive hours (compliance risk)
   - Gaps between shifts

2. OVERTIME ANALYSIS:
   - Weekly vs daily OT rules
   - State-specific requirements (CA, etc.)
   - Exempt vs non-exempt classification
   - Holiday/premium calculations

3. ACCRUAL TRACKING:
   - Balance accuracy
   - Carryover limits
   - Usage patterns
   - Negative balance situations

4. SCHEDULING CONCERNS:
   - Predictive scheduling compliance
   - Rest period requirements
   - Minor work restrictions

Focus on compliance risks and operational issues."""
    },
]


# =============================================================================
# EXPERT CONTEXT REGISTRY
# =============================================================================

class ExpertContextRegistry:
    """
    Manages expert contexts - storage, retrieval, and selection.
    
    Uses Supabase for persistent storage. Falls back to defaults if
    database not available.
    """
    
    def __init__(self):
        self.supabase = None
        self._cache: Dict[str, ExpertContext] = {}
        self._cache_loaded = False
        self._init_supabase()
    
    def _init_supabase(self):
        """Initialize Supabase connection."""
        try:
            from utils.database.supabase_client import get_supabase
            self.supabase = get_supabase()
        except ImportError:
            try:
                from backend.utils.database.supabase_client import get_supabase
                self.supabase = get_supabase()
            except ImportError:
                logger.warning("[EXPERT] Supabase not available, using defaults only")
    
    def _ensure_table(self):
        """Ensure expert_contexts table exists and is seeded."""
        if not self.supabase:
            return
        
        try:
            # Check if any contexts exist
            result = self.supabase.table('expert_contexts').select('id').limit(1).execute()
            
            # If empty, seed with defaults
            if not result.data:
                logger.info("[EXPERT] Seeding default expert contexts")
                for ctx_data in DEFAULT_EXPERT_CONTEXTS:
                    self.supabase.table('expert_contexts').insert({
                        'id': ctx_data['id'],
                        'name': ctx_data['name'],
                        'domains': ctx_data['domains'],
                        'keywords': ctx_data['keywords'],
                        'prompt_template': ctx_data['prompt_template'],
                        'description': ctx_data.get('description', ''),
                        'created_by': 'system',
                        'is_active': True,
                        'usage_count': 0,
                        'positive_feedback': 0,
                        'negative_feedback': 0,
                    }).execute()
                logger.info(f"[EXPERT] Seeded {len(DEFAULT_EXPERT_CONTEXTS)} default contexts")
                
        except Exception as e:
            logger.warning(f"[EXPERT] Table check/seed failed: {e}")
    
    def _load_cache(self):
        """Load all active contexts into cache."""
        if self._cache_loaded:
            return
        
        # First try database
        if self.supabase:
            try:
                self._ensure_table()
                result = self.supabase.table('expert_contexts').select('*').eq('is_active', True).execute()
                
                if result.data:
                    for row in result.data:
                        ctx = ExpertContext.from_dict(row)
                        self._cache[ctx.id] = ctx
                    logger.info(f"[EXPERT] Loaded {len(self._cache)} contexts from database")
                    self._cache_loaded = True
                    return
            except Exception as e:
                logger.warning(f"[EXPERT] Database load failed: {e}")
        
        # Fall back to defaults
        for ctx_data in DEFAULT_EXPERT_CONTEXTS:
            ctx = ExpertContext(
                id=ctx_data['id'],
                name=ctx_data['name'],
                domains=ctx_data['domains'],
                keywords=ctx_data['keywords'],
                prompt_template=ctx_data['prompt_template'],
                description=ctx_data.get('description', ''),
            )
            self._cache[ctx.id] = ctx
        
        logger.info(f"[EXPERT] Loaded {len(self._cache)} default contexts")
        self._cache_loaded = True
    
    def get_all(self) -> List[ExpertContext]:
        """Get all active expert contexts."""
        self._load_cache()
        return list(self._cache.values())
    
    def get_by_id(self, context_id: str) -> Optional[ExpertContext]:
        """Get a specific expert context by ID."""
        self._load_cache()
        return self._cache.get(context_id)
    
    def get_by_domain(self, domain: str) -> List[ExpertContext]:
        """Get all contexts that apply to a domain."""
        self._load_cache()
        return [ctx for ctx in self._cache.values() if domain in ctx.domains]
    
    def create(self, context: ExpertContext) -> bool:
        """Create a new expert context."""
        if self.supabase:
            try:
                self.supabase.table('expert_contexts').insert(context.to_dict()).execute()
                self._cache[context.id] = context
                return True
            except Exception as e:
                logger.error(f"[EXPERT] Create failed: {e}")
                return False
        
        # Fall back to cache only
        self._cache[context.id] = context
        return True
    
    def update(self, context_id: str, **updates) -> bool:
        """Update an expert context."""
        if self.supabase:
            try:
                self.supabase.table('expert_contexts').update(updates).eq('id', context_id).execute()
            except Exception as e:
                logger.error(f"[EXPERT] Update failed: {e}")
                return False
        
        # Update cache
        if context_id in self._cache:
            for key, value in updates.items():
                if hasattr(self._cache[context_id], key):
                    setattr(self._cache[context_id], key, value)
        
        return True
    
    def record_usage(self, context_id: str, feedback: str = None):
        """
        Record usage of a context and optional feedback.
        
        Args:
            context_id: The context that was used
            feedback: 'positive', 'negative', or None
        """
        updates = {'usage_count': self._cache.get(context_id, ExpertContext(id='', name='', domains=[], keywords=[], prompt_template='')).usage_count + 1}
        
        if feedback == 'positive':
            updates['positive_feedback'] = self._cache.get(context_id, ExpertContext(id='', name='', domains=[], keywords=[], prompt_template='')).positive_feedback + 1
        elif feedback == 'negative':
            updates['negative_feedback'] = self._cache.get(context_id, ExpertContext(id='', name='', domains=[], keywords=[], prompt_template='')).negative_feedback + 1
        
        self.update(context_id, **updates)


# =============================================================================
# AUTO-SELECTION ENGINE
# =============================================================================

class ExpertContextSelector:
    """
    Automatically selects the best expert context based on:
    1. Project's detected domains
    2. Question keywords
    3. Historical effectiveness (learning)
    """
    
    def __init__(self, registry: ExpertContextRegistry = None):
        self.registry = registry or ExpertContextRegistry()
    
    def select(
        self,
        question: str,
        project_domains: List[Dict] = None,
        top_k: int = 1
    ) -> List[ContextMatch]:
        """
        Select the best expert context(s) for a question.
        
        Args:
            question: The user's question
            project_domains: Detected domains for the project (from DomainInferenceEngine)
            top_k: Number of contexts to return
            
        Returns:
            List of ContextMatch objects, sorted by match_score
        """
        contexts = self.registry.get_all()
        if not contexts:
            return []
        
        # Extract keywords from question
        question_keywords = self._extract_keywords(question)
        
        # Build domain scores from project_domains
        domain_scores = {}
        if project_domains:
            for d in project_domains:
                domain_scores[d.get('domain', '')] = d.get('confidence', 0.5)
        
        # Score each context
        matches = []
        for ctx in contexts:
            # Domain match score
            domain_match = self._calculate_domain_match(ctx.domains, domain_scores)
            
            # Keyword match score
            keyword_match = self._calculate_keyword_match(ctx.keywords, question_keywords, question)
            
            # Learning boost from historical effectiveness
            learning_boost = (ctx.effectiveness_score - 0.5) * 0.2  # -0.1 to +0.1
            
            # Combined score
            # Keyword match is most important (60%), domain (30%), learning (10%)
            match_score = (keyword_match * 0.6) + (domain_match * 0.3) + (learning_boost + 0.1)
            
            matches.append(ContextMatch(
                context=ctx,
                match_score=match_score,
                domain_match=domain_match,
                keyword_match=keyword_match,
                learning_boost=learning_boost,
            ))
        
        # Sort by score, return top_k
        matches.sort(key=lambda m: m.match_score, reverse=True)
        return matches[:top_k]
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text."""
        if not text:
            return []
        
        # Lowercase and clean
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Split and filter
        words = text.split()
        
        stop_words = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'shall',
            'i', 'me', 'my', 'we', 'our', 'you', 'your', 'he', 'she', 'it',
            'they', 'them', 'their', 'this', 'that', 'these', 'those',
            'what', 'which', 'who', 'whom', 'where', 'when', 'why', 'how',
            'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other',
            'some', 'such', 'no', 'not', 'only', 'same', 'so', 'than', 'too',
            'very', 'just', 'can', 'also', 'any', 'and', 'or', 'but', 'if',
            'for', 'from', 'to', 'of', 'in', 'on', 'at', 'by', 'with',
            'show', 'give', 'get', 'find', 'list', 'display', 'tell', 'help',
            'please', 'want', 'need', 'like', 'know', 'many', 'much',
        }
        
        return [w for w in words if w not in stop_words and len(w) > 2]
    
    def _calculate_domain_match(
        self, 
        context_domains: List[str], 
        project_domain_scores: Dict[str, float]
    ) -> float:
        """Calculate how well context domains match project domains."""
        if not context_domains or not project_domain_scores:
            return 0.3  # Neutral baseline
        
        # Sum of matching domain confidences
        total_match = 0.0
        for domain in context_domains:
            if domain in project_domain_scores:
                total_match += project_domain_scores[domain]
        
        # Normalize by number of context domains
        return min(total_match / len(context_domains), 1.0)
    
    def _calculate_keyword_match(
        self,
        context_keywords: List[str],
        question_keywords: List[str],
        full_question: str
    ) -> float:
        """Calculate keyword match score."""
        if not context_keywords:
            return 0.3
        
        question_lower = full_question.lower()
        matches = 0
        
        for keyword in context_keywords:
            # Direct match in keywords
            if keyword.lower() in question_keywords:
                matches += 1
            # Substring match in full question (for phrases)
            elif keyword.lower() in question_lower:
                matches += 0.7
            # Partial match (keyword is part of a question word)
            elif any(keyword.lower() in qw for qw in question_keywords):
                matches += 0.5
        
        # Normalize
        return min(matches / len(context_keywords), 1.0)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_registry_instance = None
_selector_instance = None


def get_expert_registry() -> ExpertContextRegistry:
    """Get or create expert context registry singleton."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ExpertContextRegistry()
    return _registry_instance


def get_expert_selector() -> ExpertContextSelector:
    """Get or create expert context selector singleton."""
    global _selector_instance
    if _selector_instance is None:
        _selector_instance = ExpertContextSelector(get_expert_registry())
    return _selector_instance


def select_expert_context(
    question: str,
    project_id: str = None,
    project_domains: List[Dict] = None
) -> Optional[str]:
    """
    Select the best expert context prompt for a question.
    
    Args:
        question: The user's question
        project_id: Optional project ID to get detected domains
        project_domains: Optional pre-loaded domains
        
    Returns:
        Expert prompt template string, or None if no good match
    """
    # Get project domains if not provided
    if project_domains is None and project_id:
        try:
            from domain_inference_engine import get_domain_engine
            engine = get_domain_engine()
            domains_data = engine.get_project_domains(project_id)
            if domains_data:
                project_domains = domains_data.get('domains', [])
        except ImportError:
            pass
    
    selector = get_expert_selector()
    matches = selector.select(question, project_domains, top_k=1)
    
    if matches and matches[0].match_score > 0.3:
        # Record usage
        registry = get_expert_registry()
        registry.record_usage(matches[0].context.id)
        
        logger.info(f"[EXPERT] Selected '{matches[0].context.name}' "
                   f"(score={matches[0].match_score:.2f})")
        
        return matches[0].context.prompt_template
    
    return None


def record_expert_feedback(context_id: str, feedback: str):
    """
    Record feedback on expert context selection.
    
    Args:
        context_id: The context that was used
        feedback: 'positive' or 'negative'
    """
    registry = get_expert_registry()
    registry.record_usage(context_id, feedback)
