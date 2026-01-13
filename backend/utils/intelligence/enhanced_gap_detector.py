"""
XLR8 Intelligence Engine - Enhanced Gap Detector
=================================================
Phase 3.3: Gap Detection Logic

Enhanced gap detection that compares truths to identify:
- CONFIG_VS_INTENT: Configuration doesn't match customer requirements
- CONFIG_VS_REFERENCE: Configuration doesn't follow best practices
- CONFIG_VS_REGULATORY: Configuration may not be compliant
- MISSING_DATA: Expected data not found
- INCOMPLETE_SETUP: Partial configuration detected

This is where the consulting intelligence happens - triangulating
across the Five Truths to find meaningful gaps.

Deploy to: backend/utils/intelligence/enhanced_gap_detector.py
"""

import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from .truth_assembler import (
    TruthContext, Gap, RealityContext, IntentContext, 
    ReferenceContext, RegulatoryContext
)

logger = logging.getLogger(__name__)


# =============================================================================
# GAP TYPES AND RULES
# =============================================================================

class GapType(Enum):
    """Types of gaps between truths."""
    CONFIG_VS_INTENT = "configured_vs_intended"      # Setup doesn't match SOW
    CONFIG_VS_REFERENCE = "configured_vs_best"       # Setup doesn't follow best practice
    CONFIG_VS_REGULATORY = "configured_vs_required"  # Setup may not be compliant
    MISSING_DATA = "missing_data"                    # Expected data not found
    INCOMPLETE_SETUP = "incomplete_setup"            # Partial configuration
    COVERAGE_GAP = "coverage_gap"                    # No documentation for topic


@dataclass
class GapRule:
    """
    A rule for detecting a specific type of gap.
    """
    name: str
    gap_type: GapType
    description: str
    severity: str  # high, medium, low
    check_fn: callable = None  # Function to check condition
    recommendation_template: str = ""
    
    def check(self, context: TruthContext) -> Optional[Gap]:
        """Run the check and return Gap if detected."""
        if self.check_fn:
            return self.check_fn(context, self)
        return None


# =============================================================================
# GAP DETECTION FUNCTIONS
# =============================================================================

def _check_intent_not_configured(context: TruthContext, rule: GapRule) -> Optional[Gap]:
    """
    Check if customer requirements (intent) are not reflected in data (reality).
    
    Example: SOW mentions "weekly payroll" but no weekly pay runs found.
    """
    if context.intent.is_empty() or context.reality.is_empty():
        return None
    
    # Look for specific mismatches
    intent_text = " ".join(context.intent.relevant_requirements).lower()
    
    # Check for common requirement patterns not in data
    requirement_patterns = {
        'weekly payroll': ['weekly', 'pay frequency', 'w'],
        'bi-weekly payroll': ['biweekly', 'bi-weekly', 'b'],
        'multi-state': ['state', 'states', 'jurisdiction'],
        'multi-company': ['company', 'companies', 'entity'],
        '401k': ['401k', '401(k)', 'retirement'],
    }
    
    for requirement, keywords in requirement_patterns.items():
        if any(kw in intent_text for kw in keywords):
            # Check if related data exists
            has_data = any(
                any(kw in str(row).lower() for kw in keywords)
                for row in context.reality.sample_data[:5]
            )
            if not has_data:
                return Gap(
                    gap_type='config_vs_intent',
                    severity='high',
                    topic=requirement,
                    description=f"Customer requirement '{requirement}' mentioned in SOW but no matching data found.",
                    recommendation=f"Verify {requirement} configuration is complete.",
                    expected_value=requirement,
                    source_truth='intent',
                )
    
    return None


def _check_not_best_practice(context: TruthContext, rule: GapRule) -> Optional[Gap]:
    """
    Check if configuration deviates from best practices (reference).
    
    Example: Reference says "use standardized earning codes" but codes are custom.
    """
    if context.reference.is_empty() or context.reality.is_empty():
        return None
    
    reference_text = " ".join(context.reference.relevant_guidance).lower()
    
    # Check for common best practice violations
    best_practice_checks = [
        {
            'pattern': r'standard(?:ized)?',
            'topic': 'Standardization',
            'check_data': lambda data: any(
                any(len(str(v)) > 20 and '_' in str(v) for v in row.values())
                for row in data[:10]
            ),
            'message': 'Custom codes detected where standardized codes recommended.',
        },
        {
            'pattern': r'description.+required',
            'topic': 'Documentation',
            'check_data': lambda data: any(
                any(k.lower() in ['description', 'desc', 'name'] and (not v or v == 'NULL')
                    for k, v in row.items())
                for row in data[:10]
            ),
            'message': 'Missing descriptions where documentation is recommended.',
        },
    ]
    
    for check in best_practice_checks:
        if re.search(check['pattern'], reference_text):
            if check['check_data'](context.reality.sample_data):
                return Gap(
                    gap_type='config_vs_reference',
                    severity='medium',
                    topic=check['topic'],
                    description=check['message'],
                    recommendation='Review configuration against best practice guidelines.',
                    source_truth='reference',
                )
    
    return None


def _check_compliance_risk(context: TruthContext, rule: GapRule) -> Optional[Gap]:
    """
    Check if configuration may violate regulatory requirements.
    
    Example: Regulation requires tax withholding but no tax configuration found.
    """
    if context.regulatory.is_empty():
        return None
    
    regulatory_text = " ".join(context.regulatory.relevant_requirements).lower()
    
    # Common compliance checks
    compliance_checks = [
        {
            'patterns': ['federal tax', 'fit', 'federal income'],
            'topic': 'Federal Tax Compliance',
            'severity': 'high',
        },
        {
            'patterns': ['state tax', 'sit', 'state income'],
            'topic': 'State Tax Compliance',
            'severity': 'high',
        },
        {
            'patterns': ['futa', 'federal unemployment'],
            'topic': 'FUTA Compliance',
            'severity': 'high',
        },
        {
            'patterns': ['workers comp', 'wc', 'work comp'],
            'topic': 'Workers Compensation',
            'severity': 'high',
        },
    ]
    
    for check in compliance_checks:
        if any(p in regulatory_text for p in check['patterns']):
            # Check if configuration addresses this
            has_config = False
            if not context.reality.is_empty():
                reality_text = str(context.reality.sample_data).lower()
                has_config = any(p in reality_text for p in check['patterns'])
            
            if not has_config:
                jurisdictions = ", ".join(context.regulatory.jurisdictions) or "applicable jurisdictions"
                return Gap(
                    gap_type='config_vs_regulatory',
                    severity=check['severity'],
                    topic=check['topic'],
                    description=f"⚠️ {check['topic']} requirements mentioned but no matching configuration found.",
                    recommendation=f"Verify {check['topic']} setup meets {jurisdictions} requirements.",
                    source_truth='regulatory',
                )
    
    return None


def _check_missing_data(context: TruthContext, rule: GapRule) -> Optional[Gap]:
    """
    Check if expected data is missing from the dataset.
    """
    if not context.reality.is_empty():
        return None
    
    # If we have intent or reference but no reality, that's a gap
    has_context = not context.intent.is_empty() or not context.reference.is_empty()
    
    if has_context:
        return Gap(
            gap_type='missing_data',
            severity='medium',
            topic=context.domain,
            description=f"No data found for {context.domain} despite having documentation.",
            recommendation=f"Upload {context.domain} data or verify data extraction.",
            source_truth='reality',
        )
    
    return None


def _check_incomplete_setup(context: TruthContext, rule: GapRule) -> Optional[Gap]:
    """
    Check for incomplete configuration patterns.
    """
    if context.reality.is_empty():
        return None
    
    # Check for common incomplete setup patterns
    sample_data = context.reality.sample_data[:20]
    columns = context.reality.column_names
    
    # Check for high null rates in important columns
    important_patterns = ['code', 'name', 'description', 'amount', 'rate']
    
    for col in columns:
        if any(p in col.lower() for p in important_patterns):
            null_count = sum(
                1 for row in sample_data 
                if row.get(col) is None or row.get(col) == '' or row.get(col) == 'NULL'
            )
            null_rate = null_count / len(sample_data) if sample_data else 0
            
            if null_rate > 0.5:
                return Gap(
                    gap_type='incomplete_setup',
                    severity='low',
                    topic=f'{col} completeness',
                    description=f"Column '{col}' has {null_rate:.0%} missing values.",
                    recommendation=f"Review data quality for {col} field.",
                    actual_value=f'{null_rate:.0%} null',
                    source_truth='reality',
                )
    
    return None


def _check_coverage_gap(context: TruthContext, rule: GapRule) -> Optional[Gap]:
    """
    Check for missing documentation coverage.
    """
    # Check each truth type for coverage
    gaps_detected = []
    
    if context.intent.is_empty():
        gaps_detected.append('intent')
    if context.reference.is_empty():
        gaps_detected.append('reference')
    if context.regulatory.is_empty() and context.domain in ['taxes', 'compliance', 'payroll']:
        gaps_detected.append('regulatory')
    
    if len(gaps_detected) >= 2:
        return Gap(
            gap_type='coverage_gap',
            severity='low',
            topic=context.domain,
            description=f"Limited documentation coverage: missing {', '.join(gaps_detected)}.",
            recommendation=f"Upload {', '.join(gaps_detected)} documentation for better analysis.",
            source_truth='coverage',
        )
    
    return None


# =============================================================================
# GAP RULES REGISTRY
# =============================================================================

GAP_RULES: List[GapRule] = [
    GapRule(
        name='intent_not_configured',
        gap_type=GapType.CONFIG_VS_INTENT,
        description='Customer requirement not reflected in data',
        severity='high',
        check_fn=_check_intent_not_configured,
        recommendation_template='Verify {topic} configuration matches customer requirements.',
    ),
    GapRule(
        name='not_best_practice',
        gap_type=GapType.CONFIG_VS_REFERENCE,
        description='Configuration deviates from best practices',
        severity='medium',
        check_fn=_check_not_best_practice,
        recommendation_template='Review {topic} configuration against vendor recommendations.',
    ),
    GapRule(
        name='compliance_risk',
        gap_type=GapType.CONFIG_VS_REGULATORY,
        description='Configuration may not meet compliance requirements',
        severity='high',
        check_fn=_check_compliance_risk,
        recommendation_template='Verify {topic} meets regulatory requirements.',
    ),
    GapRule(
        name='missing_data',
        gap_type=GapType.MISSING_DATA,
        description='Expected data not found in dataset',
        severity='medium',
        check_fn=_check_missing_data,
        recommendation_template='Upload {topic} data for analysis.',
    ),
    GapRule(
        name='incomplete_setup',
        gap_type=GapType.INCOMPLETE_SETUP,
        description='Partial or incomplete configuration detected',
        severity='low',
        check_fn=_check_incomplete_setup,
        recommendation_template='Complete {topic} setup for all required fields.',
    ),
    GapRule(
        name='coverage_gap',
        gap_type=GapType.COVERAGE_GAP,
        description='Missing documentation for topic',
        severity='low',
        check_fn=_check_coverage_gap,
        recommendation_template='Upload documentation for {topic}.',
    ),
]


# =============================================================================
# ENHANCED GAP DETECTOR
# =============================================================================

class EnhancedGapDetector:
    """
    Enhanced gap detector that triangulates across Five Truths.
    
    Runs all gap rules against the assembled context and returns
    detected gaps with severity and recommendations.
    """
    
    def __init__(self, rules: List[GapRule] = None):
        self.rules = rules or GAP_RULES
        logger.info(f"[GAP-DETECT] Initialized with {len(self.rules)} rules")
    
    def detect_gaps(self, context: TruthContext) -> List[Gap]:
        """
        Run all gap rules and return detected gaps.
        
        Args:
            context: Assembled TruthContext
            
        Returns:
            List of detected gaps, sorted by severity
        """
        detected = []
        
        for rule in self.rules:
            try:
                gap = rule.check(context)
                if gap:
                    detected.append(gap)
                    logger.info(f"[GAP-DETECT] Found: {rule.name} - {gap.topic}")
            except Exception as e:
                logger.warning(f"[GAP-DETECT] Rule {rule.name} error: {e}")
        
        # Sort by severity
        severity_order = {'high': 0, 'medium': 1, 'low': 2}
        detected.sort(key=lambda g: severity_order.get(g.severity, 3))
        
        logger.info(f"[GAP-DETECT] Total gaps detected: {len(detected)}")
        
        return detected
    
    def detect_specific_gap(self, context: TruthContext, 
                            gap_type: GapType) -> Optional[Gap]:
        """
        Check for a specific type of gap.
        
        Args:
            context: Assembled TruthContext
            gap_type: Which gap type to check
            
        Returns:
            Gap if detected, None otherwise
        """
        for rule in self.rules:
            if rule.gap_type == gap_type:
                return rule.check(context)
        return None
    
    def get_gap_summary(self, gaps: List[Gap]) -> str:
        """
        Generate human-readable summary of gaps.
        """
        if not gaps:
            return "No gaps detected - configuration appears complete."
        
        # Group by severity
        high = [g for g in gaps if g.severity == 'high']
        medium = [g for g in gaps if g.severity == 'medium']
        low = [g for g in gaps if g.severity == 'low']
        
        parts = []
        
        if high:
            parts.append(f"⚠️ **{len(high)} High Priority Issues:**")
            for g in high:
                parts.append(f"  - {g.description}")
        
        if medium:
            parts.append(f"⚡ **{len(medium)} Medium Priority Items:**")
            for g in medium:
                parts.append(f"  - {g.description}")
        
        if low:
            parts.append(f"ℹ️ **{len(low)} Low Priority Notes:**")
            for g in low[:3]:
                parts.append(f"  - {g.description}")
            if len(low) > 3:
                parts.append(f"  - ... and {len(low) - 3} more")
        
        return "\n".join(parts)


# =============================================================================
# GAP EXPLAINER
# =============================================================================

class GapExplainer:
    """
    Generate human-readable gap explanations.
    
    Produces consultative explanations that explain:
    1. What the gap is
    2. Why it matters
    3. What to do about it
    """
    
    EXPLANATION_TEMPLATES = {
        'config_vs_intent': (
            "The {topic} is configured as {actual}, but the SOW specifies {expected}. "
            "This should be verified with the customer before go-live."
        ),
        'config_vs_reference': (
            "The {topic} configuration ({actual}) differs from the recommended "
            "best practice ({expected}). Consider reviewing this setup."
        ),
        'config_vs_regulatory': (
            "⚠️ The {topic} configuration may not meet {jurisdiction} requirements. "
            "{description}"
        ),
        'missing_data': (
            "No {topic} data was found in the uploaded files. "
            "This may indicate missing data exports or incomplete upload."
        ),
        'incomplete_setup': (
            "The {topic} configuration appears incomplete: {description}. "
            "Review and complete all required fields."
        ),
        'coverage_gap': (
            "Limited documentation available for {topic}. "
            "Upload additional documents for more comprehensive analysis."
        ),
    }
    
    def explain(self, gap: Gap, context: TruthContext = None) -> str:
        """
        Generate consultative explanation for a gap.
        
        Args:
            gap: The gap to explain
            context: Optional TruthContext for additional context
            
        Returns:
            Human-readable explanation
        """
        template = self.EXPLANATION_TEMPLATES.get(gap.gap_type, "{description}")
        
        # Build template variables
        vars = {
            'topic': gap.topic,
            'actual': gap.actual_value or 'current configuration',
            'expected': gap.expected_value or 'documented requirement',
            'description': gap.description,
            'jurisdiction': 'applicable',
        }
        
        # Add jurisdiction if available
        if context and context.regulatory and context.regulatory.jurisdictions:
            vars['jurisdiction'] = ", ".join(context.regulatory.jurisdictions)
        
        try:
            return template.format(**vars)
        except KeyError:
            return gap.description


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_detector_instance: Optional[EnhancedGapDetector] = None
_explainer_instance: Optional[GapExplainer] = None

def get_detector() -> EnhancedGapDetector:
    """Get the singleton detector instance."""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = EnhancedGapDetector()
    return _detector_instance


def get_explainer() -> GapExplainer:
    """Get the singleton explainer instance."""
    global _explainer_instance
    if _explainer_instance is None:
        _explainer_instance = GapExplainer()
    return _explainer_instance


def detect_gaps(context: TruthContext) -> List[Gap]:
    """Convenience function to detect gaps."""
    detector = get_detector()
    return detector.detect_gaps(context)


def explain_gap(gap: Gap, context: TruthContext = None) -> str:
    """Convenience function to explain a gap."""
    explainer = get_explainer()
    return explainer.explain(gap, context)
