"""
Truth Router for Five Truths Architecture
==========================================

Routes queries to appropriate truth types based on what's being asked.
Deterministic pattern matching - no LLM involved.

Query Type → Truth Mapping:
- "What's required?" → Regulatory + Compliance
- "Best practice for X" → Reference + Regulatory
- "Customer wants X" → Intent
- "Why is X set up this way?" → All truths
- Default → All truths with equal weight

Phase 2B.2 Implementation - January 2026
"""

import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TruthQuery:
    """A query to a specific truth type with weight."""
    truth_type: str  # intent | reference | regulatory | compliance | configuration | reality
    weight: float    # 0.0 - 1.0, higher = more relevant
    domain: Optional[str] = None  # Optional domain filter (earnings, taxes, etc.)


@dataclass 
class RoutingResult:
    """Result of query routing."""
    queries: List[TruthQuery]
    query_category: str  # Which pattern matched
    domain_detected: Optional[str] = None
    confidence: float = 1.0
    reasoning: str = ""


# =============================================================================
# QUERY PATTERNS
# =============================================================================

# Pattern definitions: patterns that indicate a specific truth type should be prioritized
QUERY_PATTERNS = {
    'regulatory_required': {
        'patterns': [
            r'\brequired\b', r'\bmust\b', r'\bmandatory\b', r'\bcompliance\b', 
            r'\blaw\b', r'\blegal\b', r'\birs\b', r'\bdol\b', r'\bflsa\b',
            r'\bregulation\b', r'\bstatute\b', r'\bpenalty\b', r'\bfine\b',
            r'\bfederal\b', r'\bstate law\b', r'\bviolation\b', r'\baudit\b',
            r'\baca\b', r'\bcobra\b', r'\berisa\b', r'\bfmla\b', r'\bhipaa\b'
        ],
        'truths': ['regulatory', 'compliance'],
        'weights': [1.0, 0.8],
        'description': 'Regulatory/compliance requirements'
    },
    'best_practice': {
        'patterns': [
            r'\bbest practice\b', r'\brecommend\b', r'\bshould\b', r'\bstandard\b',
            r'\btypical\b', r'\bnormal\b', r'\bcommon\b', r'\bhow should\b',
            r'\bbetter way\b', r'\boptimal\b', r'\bsuggested\b', r'\bguideline\b',
            r'\bhow to\b', r'\bsetup\b', r'\bconfigure\b'
        ],
        'truths': ['reference', 'regulatory'],
        'weights': [1.0, 0.6],
        'description': 'Best practices and setup guidance'
    },
    'customer_intent': {
        'patterns': [
            r'\bcustomer wants\b', r'\bsow\b', r'\brequirement\b', r'\bscope\b',
            r'\bdeliverable\b', r'\bin scope\b', r'\bout of scope\b',
            r'\bwhat they want\b', r'\bwhat we agreed\b', r'\bcontract\b',
            r'\bspecification\b', r'\bclient\b'
        ],
        'truths': ['intent'],
        'weights': [1.0],
        'description': 'Customer requirements and scope'
    },
    'gap_analysis': {
        'patterns': [
            r'\bgap\b', r'\bmissing\b', r'\bnot configured\b', r'\bdifference\b',
            r'\bcompare\b', r'\bvs\b', r'\bversus\b', r'\bshould have\b',
            r'\bdon\'t have\b', r'\bdoesn\'t have\b', r'\bwhy not\b',
            r'\bwhy isn\'t\b', r'\bwhat\'s missing\b'
        ],
        'truths': ['reference', 'intent', 'regulatory'],
        'weights': [1.0, 0.9, 0.8],
        'description': 'Gap and difference analysis'
    },
    'explanation': {
        'patterns': [
            r'\bwhy\b', r'\bexplain\b', r'\bhow does\b', r'\bwhat does\b',
            r'\bwhat is\b', r'\bwhat are\b', r'\bmeaning\b', r'\bdefine\b',
            r'\bunderstand\b', r'\bpurpose\b', r'\breason\b'
        ],
        'truths': ['reference', 'regulatory', 'intent', 'compliance'],
        'weights': [0.9, 0.8, 0.7, 0.6],
        'description': 'Explanations and definitions'
    },
    'implementation': {
        'patterns': [
            r'\bhow to\b', r'\bsteps\b', r'\bprocess\b', r'\bprocedure\b',
            r'\bimplement\b', r'\bset up\b', r'\bconfigure\b', r'\bcreate\b',
            r'\badd\b', r'\bchange\b', r'\bmodify\b', r'\bupdate\b'
        ],
        'truths': ['reference'],
        'weights': [1.0],
        'description': 'Implementation and how-to guidance'
    },
    'policy': {
        'patterns': [
            r'\bpolicy\b', r'\bprocedure\b', r'\binternal\b', r'\bcompany\b',
            r'\bapproval\b', r'\bsign.off\b', r'\bcontrol\b', r'\bsoc\b',
            r'\bsox\b', r'\bsegregation\b'
        ],
        'truths': ['compliance', 'intent'],
        'weights': [1.0, 0.7],
        'description': 'Internal policies and controls'
    }
}

# Domain detection patterns
DOMAIN_PATTERNS = {
    'demographics': [
        r'\bemployees?\b', r'\bworkers?\b', r'\bhire[ds]?\b', r'\bterminate[ds]?\b', 
        r'\bheadcount\b', r'\bstatus\b', r'\bactive\b', r'\binactive\b'
    ],
    'earnings': [
        r'\bpay\b', r'\bwages?\b', r'\bsalar(?:y|ies)\b', r'\bcompensation\b',
        r'\bearnings?\b', r'\bovertime\b', r'\bbonus(?:es)?\b', r'\brates?\b'
    ],
    'deductions': [
        r'\bdeductions?\b', r'\bbenefits?\b', r'\b401k\b', r'\binsurance\b',
        r'\bhsa\b', r'\bfsa\b', r'\bmedical\b', r'\bdental\b'
    ],
    'taxes': [
        r'\btaxe?s?\b', r'\bwithholding\b', r'\bw-?2\b', r'\bw-?4\b',
        r'\bsui\b', r'\bfuta\b', r'\bfica\b', r'\bfederal\b', r'\bstate\b'
    ],
    'time': [
        r'\btime\b', r'\battendance\b', r'\bpto\b', r'\baccruals?\b',
        r'\bschedules?\b', r'\bleave\b', r'\bfmla\b', r'\babsence\b'
    ],
    'organization': [
        r'\bdepartments?\b', r'\blocations?\b', r'\borg\b', r'\bcompany\b',
        r'\bcost center\b', r'\bjobs?\b', r'\bpositions?\b', r'\bmanagers?\b'
    ]
}


class TruthRouter:
    """
    Route queries to appropriate truth sources.
    
    Analyzes user questions and determines which truth types (intent, reference,
    regulatory, compliance) should be searched and with what priority.
    
    This is DETERMINISTIC pattern matching - no LLM involved.
    """
    
    def __init__(self):
        """Initialize the router with compiled patterns for performance."""
        self._compiled_patterns = {}
        self._compile_patterns()
        logger.info("TruthRouter initialized")
    
    def _compile_patterns(self):
        """Pre-compile regex patterns for faster matching."""
        for category, config in QUERY_PATTERNS.items():
            self._compiled_patterns[category] = [
                re.compile(p, re.IGNORECASE) for p in config['patterns']
            ]
        
        self._domain_patterns = {}
        for domain, patterns in DOMAIN_PATTERNS.items():
            self._domain_patterns[domain] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]
    
    def route_query(self, query: str, context: Dict = None) -> RoutingResult:
        """
        Determine which truths to query and with what priority.
        
        Args:
            query: User's question
            context: Optional context (may contain pre-detected domain, etc.)
            
        Returns:
            RoutingResult with list of TruthQuery objects
        """
        context = context or {}
        query_lower = query.lower()
        
        # Detect domain
        domain = context.get('domain') or self._detect_domain(query_lower)
        
        # Find matching category
        best_category = None
        best_score = 0
        
        for category, compiled in self._compiled_patterns.items():
            score = sum(1 for p in compiled if p.search(query_lower))
            if score > best_score:
                best_score = score
                best_category = category
        
        # Build result
        if best_category and best_score > 0:
            config = QUERY_PATTERNS[best_category]
            queries = [
                TruthQuery(
                    truth_type=t,
                    weight=w,
                    domain=domain
                )
                for t, w in zip(config['truths'], config['weights'])
            ]
            
            result = RoutingResult(
                queries=queries,
                query_category=best_category,
                domain_detected=domain,
                confidence=min(0.5 + (best_score * 0.15), 0.95),
                reasoning=config['description']
            )
        else:
            # Default: search all truths with equal weight
            queries = [
                TruthQuery(truth_type='reference', weight=1.0, domain=domain),
                TruthQuery(truth_type='regulatory', weight=1.0, domain=domain),
                TruthQuery(truth_type='intent', weight=0.8, domain=domain),
                TruthQuery(truth_type='compliance', weight=0.8, domain=domain),
            ]
            
            result = RoutingResult(
                queries=queries,
                query_category='default',
                domain_detected=domain,
                confidence=0.5,
                reasoning='No specific pattern matched - searching all truths'
            )
        
        logger.info(f"[ROUTE] Query: '{query[:50]}...' → {result.query_category} "
                   f"(domain={domain}, confidence={result.confidence:.2f})")
        
        return result
    
    def _detect_domain(self, query: str) -> Optional[str]:
        """Detect HCM domain from query text."""
        scores = {}
        
        for domain, patterns in self._domain_patterns.items():
            score = sum(1 for p in patterns if p.search(query))
            if score > 0:
                scores[domain] = score
        
        if not scores:
            return None
        
        return max(scores, key=scores.get)
    
    def should_gather(self, truth_type: str, routing: RoutingResult, 
                      min_weight: float = 0.0) -> Tuple[bool, float]:
        """
        Check if a specific truth type should be gathered based on routing.
        
        Args:
            truth_type: The truth type to check (reference, regulatory, etc.)
            routing: The routing result from route_query()
            min_weight: Minimum weight threshold (0.0 = always gather if in list)
            
        Returns:
            (should_gather, weight)
        """
        for tq in routing.queries:
            if tq.truth_type == truth_type:
                if tq.weight >= min_weight:
                    return (True, tq.weight)
                else:
                    return (False, tq.weight)
        
        return (False, 0.0)
    
    def get_truth_types(self, routing: RoutingResult, 
                        min_weight: float = 0.0) -> List[str]:
        """
        Get list of truth types that should be gathered.
        
        Args:
            routing: The routing result
            min_weight: Minimum weight threshold
            
        Returns:
            List of truth type strings
        """
        return [
            tq.truth_type 
            for tq in routing.queries 
            if tq.weight >= min_weight
        ]
    
    def get_weight(self, truth_type: str, routing: RoutingResult) -> float:
        """Get the weight for a specific truth type from routing result."""
        for tq in routing.queries:
            if tq.truth_type == truth_type:
                return tq.weight
        return 0.0


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_router_instance: Optional[TruthRouter] = None

def get_router() -> TruthRouter:
    """Get the singleton TruthRouter instance."""
    global _router_instance
    if _router_instance is None:
        _router_instance = TruthRouter()
    return _router_instance


def route_query(query: str, context: Dict = None) -> RoutingResult:
    """
    Convenience function to route a query.
    
    Args:
        query: User's question
        context: Optional context dict
        
    Returns:
        RoutingResult
    """
    return get_router().route_query(query, context)


def should_gather_truth(truth_type: str, query: str, 
                        context: Dict = None, min_weight: float = 0.0) -> Tuple[bool, float]:
    """
    Convenience function to check if a truth type should be gathered.
    
    Args:
        truth_type: Truth type to check
        query: User's question
        context: Optional context
        min_weight: Minimum weight threshold
        
    Returns:
        (should_gather, weight)
    """
    router = get_router()
    routing = router.route_query(query, context)
    return router.should_gather(truth_type, routing, min_weight)
