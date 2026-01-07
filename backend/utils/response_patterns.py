"""
XLR8 Response Patterns - The Consultant's Brain
================================================

This module encodes HOW a $500/hr consultant thinks, not just what they say.

PHILOSOPHY:
- Users don't know what they want, only what they don't want
- Every question hides a worry - hunt for the real problem
- Ground everything in facts (structured data = no hallucinations)
- Every response = understanding + evidence + action + support path

THE THINKING CHAIN:
1. UNDERSTAND - What did they ask? What are they worried about?
2. HUNT - Search across truths for problems they didn't ask about
3. SYNTHESIZE - Facts + problems + risk + fix
4. DELIVER - Excel with evidence and action items
5. EXTEND - Proactive offers, HCMPACT support path

QUESTION TAXONOMY:
- OPERATIONAL (current state): inventory, count, lookup
- DIAGNOSTIC (is it right): validation, comparison, compliance, troubleshoot
- ACTION (do something): howto, impact, report
- ADVISORY (think for me): strategy, analyze, alternatives

Deploy to: backend/utils/response_patterns.py
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class QuestionCategory(Enum):
    OPERATIONAL = "operational"  # Current state questions
    DIAGNOSTIC = "diagnostic"    # Is it right questions
    ACTION = "action"            # Do something questions
    ADVISORY = "advisory"        # Think for me questions


class TruthType(Enum):
    REALITY = "reality"              # DuckDB - actual employee/transaction data
    CONFIGURATION = "configuration"  # DuckDB - code tables, setup
    INTENT = "intent"                # ChromaDB - customer requirements, SOWs
    REFERENCE = "reference"          # ChromaDB - vendor docs, best practices
    REGULATORY = "regulatory"        # ChromaDB - laws, compliance requirements
    COMPLIANCE = "compliance"        # ChromaDB - audit controls


@dataclass
class ExcelSheet:
    """Definition of an Excel sheet to generate."""
    name: str
    source_truth: TruthType
    purpose: str  # evidence, impact, action_items, comparison
    columns: List[str] = field(default_factory=list)  # Optional column override
    filter_to_issues: bool = False  # If True, only include problem rows


@dataclass
class ResponsePattern:
    """
    Encodes how a consultant thinks through a question type.
    
    This isn't a template for the answer - it's a template for THINKING.
    The LLM follows this pattern to hunt for problems, not just answer questions.
    """
    
    # IDENTIFICATION
    question_type: str
    category: QuestionCategory
    trigger_patterns: List[str]  # Keywords/phrases that identify this type
    
    # PHASE 1: UNDERSTAND
    surface_question: str      # What they literally asked
    real_question: str         # What they're actually worried about
    hidden_worry: str          # The fear behind the question
    
    # PHASE 2: HUNT
    primary_truths: List[TruthType]   # Answer the surface question
    hunting_truths: List[TruthType]   # Find problems they didn't ask about
    hunt_for: List[str]               # Specific problems to look for
    
    # PHASE 3: SYNTHESIZE  
    answer_sections: List[str]        # Structure of the response
    risk_framing: str                 # How to frame the "what breaks" part
    
    # PHASE 4: DELIVER
    excel_sheets: List[ExcelSheet]    # Evidence package
    
    # PHASE 5: EXTEND
    proactive_offers: List[str]       # Next steps to offer
    hcmpact_hook: str                 # When to offer HCMPACT support


# =============================================================================
# THE 13 RESPONSE PATTERNS
# =============================================================================

PATTERNS: Dict[str, ResponsePattern] = {}

# -----------------------------------------------------------------------------
# OPERATIONAL: Current State Questions
# -----------------------------------------------------------------------------

PATTERNS["inventory"] = ResponsePattern(
    question_type="inventory",
    category=QuestionCategory.OPERATIONAL,
    trigger_patterns=[
        "list all", "show me all", "what do I have", "what are my",
        "give me all", "show all", "what's configured", "what is setup"
    ],
    
    # UNDERSTAND
    surface_question="What items exist in the system?",
    real_question="Is everything set up that should be?",
    hidden_worry="Something is missing or wrong and I don't know what.",
    
    # HUNT
    primary_truths=[TruthType.CONFIGURATION],
    hunting_truths=[TruthType.REALITY, TruthType.REFERENCE, TruthType.REGULATORY],
    hunt_for=[
        "Configured but never used (dead config)",
        "Used in reality but not in config (data integrity risk)",
        "Missing from config vs vendor standard template",
        "Missing from config vs regulatory requirements",
        "Employees with no assignments in this area"
    ],
    
    # SYNTHESIZE
    answer_sections=[
        "inventory_count",       # "You have X items across Y categories"
        "category_breakdown",    # Grouped listing with counts
        "usage_summary",         # "X employees actively using, Y with none"
        "gaps_found",            # "Missing: A, B, C based on vendor template"
        "compliance_flags",      # "Regulatory requires X - not found"
        "recommendations"        # Prioritized actions
    ],
    risk_framing="If these gaps aren't addressed: [specific consequence]",
    
    # DELIVER
    excel_sheets=[
        ExcelSheet("Configuration", TruthType.CONFIGURATION, "evidence"),
        ExcelSheet("Employee Usage", TruthType.REALITY, "impact"),
        ExcelSheet("Gaps & Issues", TruthType.CONFIGURATION, "action_items", filter_to_issues=True),
    ],
    
    # EXTEND
    proactive_offers=[
        "Compare against vendor standard template?",
        "Show employees missing assignments?",
        "Run compliance check against current regulations?"
    ],
    hcmpact_hook="Need help cleaning up configuration gaps?"
)


PATTERNS["count"] = ResponsePattern(
    question_type="count",
    category=QuestionCategory.OPERATIONAL,
    trigger_patterns=[
        "how many", "total", "count of", "number of",
        "count", "tally", "sum of"
    ],
    
    # UNDERSTAND
    surface_question="What is the quantity?",
    real_question="Is this number right? How does it break down?",
    hidden_worry="The number seems off but I can't explain it.",
    
    # HUNT
    primary_truths=[TruthType.REALITY, TruthType.CONFIGURATION],
    hunting_truths=[TruthType.REFERENCE, TruthType.INTENT],
    hunt_for=[
        "Unexpected distribution (one category dominates)",
        "Outliers (unusually high/low segments)",
        "Trend vs historical (if available)",
        "Count vs expected from requirements/SOW",
        "Duplicates inflating the count"
    ],
    
    # SYNTHESIZE
    answer_sections=[
        "headline_number",       # "You have X total"
        "breakdown",             # By category, status, location, etc.
        "distribution_insight",  # "85% are in category A - is that expected?"
        "anomalies",             # Outliers, unexpected patterns
        "comparison",            # vs benchmark, vs requirement, vs last period
        "implications"           # What this number means for the business
    ],
    risk_framing="If this count is wrong: [specific downstream impact]",
    
    # DELIVER
    excel_sheets=[
        ExcelSheet("Detail", TruthType.REALITY, "evidence"),
        ExcelSheet("Summary", TruthType.REALITY, "breakdown"),
        ExcelSheet("Anomalies", TruthType.REALITY, "action_items", filter_to_issues=True),
    ],
    
    # EXTEND
    proactive_offers=[
        "Break down by another dimension?",
        "Show the detailed list behind this count?",
        "Compare to a different time period?"
    ],
    hcmpact_hook="Need help understanding what's driving these numbers?"
)


PATTERNS["lookup"] = ResponsePattern(
    question_type="lookup",
    category=QuestionCategory.OPERATIONAL,
    trigger_patterns=[
        "what is", "find", "show me", "look up", "get me",
        "tell me about", "details on", "info on", "information about"
    ],
    
    # UNDERSTAND
    surface_question="What are the details of this specific item?",
    real_question="Is this item configured correctly? What's connected to it?",
    hidden_worry="This specific thing might be causing a problem.",
    
    # HUNT
    primary_truths=[TruthType.CONFIGURATION, TruthType.REALITY],
    hunting_truths=[TruthType.REFERENCE, TruthType.REGULATORY],
    hunt_for=[
        "Related items (what else is connected)",
        "Usage (who/what is using this)",
        "Configuration vs vendor recommendation",
        "Configuration vs regulatory requirement",
        "History of changes (if available)"
    ],
    
    # SYNTHESIZE
    answer_sections=[
        "item_details",          # Full configuration of the item
        "related_items",         # What's connected/dependent
        "usage_impact",          # Who uses this, transaction counts
        "config_assessment",     # Does this match best practice?
        "potential_issues"       # What could go wrong with this setup
    ],
    risk_framing="If this item is misconfigured: [who/what is affected]",
    
    # DELIVER
    excel_sheets=[
        ExcelSheet("Item Detail", TruthType.CONFIGURATION, "evidence"),
        ExcelSheet("Related Items", TruthType.CONFIGURATION, "context"),
        ExcelSheet("Usage", TruthType.REALITY, "impact"),
    ],
    
    # EXTEND
    proactive_offers=[
        "Show all items with similar configuration?",
        "Check this against vendor documentation?",
        "See who would be affected if this changed?"
    ],
    hcmpact_hook="Need help evaluating if this setup is optimal?"
)


# -----------------------------------------------------------------------------
# DIAGNOSTIC: Is It Right Questions
# -----------------------------------------------------------------------------

PATTERNS["validation"] = ResponsePattern(
    question_type="validation",
    category=QuestionCategory.DIAGNOSTIC,
    trigger_patterns=[
        "is this right", "is this correct", "any issues", "any problems",
        "validate", "check", "verify", "audit", "review for errors"
    ],
    
    # UNDERSTAND
    surface_question="Is this configured correctly?",
    real_question="What's broken that I haven't noticed?",
    hidden_worry="Something is wrong and it's going to blow up.",
    
    # HUNT
    primary_truths=[TruthType.CONFIGURATION, TruthType.REALITY],
    hunting_truths=[TruthType.REFERENCE, TruthType.REGULATORY, TruthType.INTENT],
    hunt_for=[
        "Config vs vendor best practice (deviations)",
        "Config vs regulatory requirement (compliance gaps)",
        "Config vs stated intent/SOW (scope gaps)",
        "Config vs reality (data not matching setup)",
        "Internal consistency (conflicting settings)",
        "Common mistakes for this config type"
    ],
    
    # SYNTHESIZE
    answer_sections=[
        "overall_assessment",    # "X issues found, Y critical"
        "critical_issues",       # Must fix now
        "warnings",              # Should fix soon
        "observations",          # Minor/informational
        "whats_correct",         # What's working (confidence builder)
        "remediation_plan"       # Prioritized fix steps
    ],
    risk_framing="If not addressed: [compliance risk, payroll error, audit finding]",
    
    # DELIVER
    excel_sheets=[
        ExcelSheet("Current Config", TruthType.CONFIGURATION, "evidence"),
        ExcelSheet("Issues Found", TruthType.CONFIGURATION, "action_items", filter_to_issues=True),
        ExcelSheet("Best Practice Comparison", TruthType.REFERENCE, "benchmark"),
    ],
    
    # EXTEND
    proactive_offers=[
        "Run a full compliance audit?",
        "Compare against industry benchmarks?",
        "Generate remediation task list?"
    ],
    hcmpact_hook="Need help remediating these issues?"
)


PATTERNS["comparison"] = ResponsePattern(
    question_type="comparison",
    category=QuestionCategory.DIAGNOSTIC,
    trigger_patterns=[
        "compare", "difference between", "vs", "versus",
        "how does X compare to Y", "what changed", "diff"
    ],
    
    # UNDERSTAND
    surface_question="How do these two things differ?",
    real_question="Which one is right? What do I need to fix?",
    hidden_worry="I merged/changed something and broke it.",
    
    # HUNT
    primary_truths=[TruthType.CONFIGURATION, TruthType.REALITY],
    hunting_truths=[TruthType.REFERENCE, TruthType.INTENT],
    hunt_for=[
        "Field-by-field differences",
        "Which version matches vendor standard",
        "Which version matches requirements",
        "Impact of each difference (who affected)",
        "Likely reason for difference (intentional vs error)"
    ],
    
    # SYNTHESIZE
    answer_sections=[
        "summary",               # "X differences found, Y are significant"
        "side_by_side",          # Key fields compared
        "significant_diffs",     # Differences that matter
        "impact_analysis",       # What each diff affects
        "recommendation",        # Which to keep, what to change
        "merge_plan"             # If applicable, how to reconcile
    ],
    risk_framing="Key differences to resolve: [list with consequences of each]",
    
    # DELIVER
    excel_sheets=[
        ExcelSheet("Side by Side", TruthType.CONFIGURATION, "comparison"),
        ExcelSheet("Differences Only", TruthType.CONFIGURATION, "action_items"),
        ExcelSheet("Impact Analysis", TruthType.REALITY, "impact"),
    ],
    
    # EXTEND
    proactive_offers=[
        "Show full detail for specific differences?",
        "Generate reconciliation script?",
        "Compare against a third source?"
    ],
    hcmpact_hook="Need help deciding which configuration to standardize on?"
)


PATTERNS["compliance"] = ResponsePattern(
    question_type="compliance",
    category=QuestionCategory.DIAGNOSTIC,
    trigger_patterns=[
        "compliant", "compliance", "legal", "required", "regulation",
        "FLSA", "ACA", "DOL", "IRS", "state law", "federal"
    ],
    
    # UNDERSTAND
    surface_question="Are we following the rules?",
    real_question="What will get us fined or sued?",
    hidden_worry="An auditor will find something bad.",
    
    # HUNT
    primary_truths=[TruthType.REGULATORY, TruthType.CONFIGURATION],
    hunting_truths=[TruthType.REALITY, TruthType.REFERENCE],
    hunt_for=[
        "Regulatory requirements not met in config",
        "Employee data violating regulations",
        "Recent regulatory changes not implemented",
        "Documentation gaps (no proof of compliance)",
        "Upcoming deadlines for new regulations"
    ],
    
    # SYNTHESIZE
    answer_sections=[
        "compliance_status",     # "Compliant/Non-compliant/Partial"
        "violations_found",      # Specific non-compliance items
        "at_risk_areas",         # Technically compliant but risky
        "recent_changes",        # New regs that may apply
        "upcoming_deadlines",    # What's coming
        "remediation_priority"   # What to fix first
    ],
    risk_framing="Non-compliance exposure: [fines, penalties, lawsuit risk]",
    
    # DELIVER
    excel_sheets=[
        ExcelSheet("Compliance Status", TruthType.REGULATORY, "evidence"),
        ExcelSheet("Violations", TruthType.CONFIGURATION, "action_items", filter_to_issues=True),
        ExcelSheet("Regulatory Reference", TruthType.REGULATORY, "documentation"),
    ],
    
    # EXTEND
    proactive_offers=[
        "Generate compliance certification documentation?",
        "Check against additional regulations?",
        "Set up monitoring for upcoming changes?"
    ],
    hcmpact_hook="Need help with compliance remediation or audit prep?"
)


PATTERNS["troubleshoot"] = ResponsePattern(
    question_type="troubleshoot",
    category=QuestionCategory.DIAGNOSTIC,
    trigger_patterns=[
        "why", "not working", "broken", "error", "wrong",
        "doesn't match", "incorrect", "failed", "issue with"
    ],
    
    # UNDERSTAND
    surface_question="Why isn't this working?",
    real_question="What broke it and how do I fix it fast?",
    hidden_worry="Payroll is tomorrow and something is wrong.",
    
    # HUNT
    primary_truths=[TruthType.CONFIGURATION, TruthType.REALITY],
    hunting_truths=[TruthType.REFERENCE, TruthType.INTENT],
    hunt_for=[
        "Configuration errors (missing/wrong settings)",
        "Data issues (nulls, bad values, duplicates)",
        "Dependency problems (missing related config)",
        "Recent changes that broke it",
        "Known issues from vendor documentation"
    ],
    
    # SYNTHESIZE
    answer_sections=[
        "diagnosis",             # "The issue is: X"
        "root_cause",            # "This is happening because: Y"
        "evidence",              # "Here's how I know: [data]"
        "fix_steps",             # "To resolve: 1, 2, 3"
        "prevention",            # "To prevent recurrence"
        "if_not_fixed"           # What happens if ignored
    ],
    risk_framing="If not fixed: [immediate impact, downstream effects]",
    
    # DELIVER
    excel_sheets=[
        ExcelSheet("Problem Data", TruthType.REALITY, "evidence"),
        ExcelSheet("Related Config", TruthType.CONFIGURATION, "context"),
        ExcelSheet("Fix Checklist", TruthType.CONFIGURATION, "action_items"),
    ],
    
    # EXTEND
    proactive_offers=[
        "Check for similar issues elsewhere?",
        "Generate fix script?",
        "Set up alert to catch this earlier?"
    ],
    hcmpact_hook="Need urgent support fixing this?"
)


# -----------------------------------------------------------------------------
# ACTION: Do Something Questions
# -----------------------------------------------------------------------------

PATTERNS["howto"] = ResponsePattern(
    question_type="howto",
    category=QuestionCategory.ACTION,
    trigger_patterns=[
        "how do I", "how to", "steps to", "configure",
        "set up", "create", "add", "enable"
    ],
    
    # UNDERSTAND
    surface_question="What are the steps to do this?",
    real_question="Will I break something if I do this wrong?",
    hidden_worry="I don't want to mess up the system.",
    
    # HUNT
    primary_truths=[TruthType.REFERENCE, TruthType.CONFIGURATION],
    hunting_truths=[TruthType.REGULATORY, TruthType.REALITY],
    hunt_for=[
        "Prerequisites not yet in place",
        "Current config that will be affected",
        "Employees/data that will be impacted",
        "Common mistakes to avoid",
        "Compliance implications of the change"
    ],
    
    # SYNTHESIZE
    answer_sections=[
        "prerequisites",         # "Before you start, ensure: X"
        "current_state",         # "Your system currently has: Y"
        "step_by_step",          # The actual instructions
        "warnings",              # "Watch out for: Z"
        "validation",            # "To verify it worked: [check]"
        "rollback"               # "If something goes wrong: [steps]"
    ],
    risk_framing="Common mistakes: [what goes wrong and how to avoid]",
    
    # DELIVER
    excel_sheets=[
        ExcelSheet("Current State", TruthType.CONFIGURATION, "baseline"),
        ExcelSheet("Checklist", TruthType.REFERENCE, "instructions"),
        ExcelSheet("Impact Preview", TruthType.REALITY, "impact"),
    ],
    
    # EXTEND
    proactive_offers=[
        "Preview what will change?",
        "Check prerequisites first?",
        "Generate change documentation?"
    ],
    hcmpact_hook="Want HCMPACT to handle this configuration change?"
)


PATTERNS["impact"] = ResponsePattern(
    question_type="impact",
    category=QuestionCategory.ACTION,
    trigger_patterns=[
        "what if", "who's affected", "impact of", "what happens if",
        "change", "modify", "delete", "remove"
    ],
    
    # UNDERSTAND
    surface_question="What will this change affect?",
    real_question="How badly can this blow up?",
    hidden_worry="I'll break something and not know until payroll.",
    
    # HUNT
    primary_truths=[TruthType.REALITY, TruthType.CONFIGURATION],
    hunting_truths=[TruthType.REFERENCE, TruthType.REGULATORY],
    hunt_for=[
        "Direct dependencies (what uses this)",
        "Employee count affected",
        "Downstream calculations affected",
        "Compliance implications",
        "Timing considerations (when is safe to change)"
    ],
    
    # SYNTHESIZE
    answer_sections=[
        "blast_radius",          # "This affects: X employees, Y processes"
        "direct_impact",         # What changes immediately
        "downstream_impact",     # What breaks later
        "timing_recommendation", # When to make the change
        "compliance_check",      # Any regulatory issues
        "mitigation"             # How to reduce risk
    ],
    risk_framing="Blast radius: [exactly who/what is affected]",
    
    # DELIVER
    excel_sheets=[
        ExcelSheet("Affected Employees", TruthType.REALITY, "impact"),
        ExcelSheet("Affected Config", TruthType.CONFIGURATION, "dependencies"),
        ExcelSheet("Timeline", TruthType.REFERENCE, "planning"),
    ],
    
    # EXTEND
    proactive_offers=[
        "Run a test simulation?",
        "Identify safe change window?",
        "Generate rollback plan?"
    ],
    hcmpact_hook="Want HCMPACT to manage this change with full impact analysis?"
)


PATTERNS["report"] = ResponsePattern(
    question_type="report",
    category=QuestionCategory.ACTION,
    trigger_patterns=[
        "report", "summary", "export", "send me", "generate",
        "create a report", "document", "pull together"
    ],
    
    # UNDERSTAND
    surface_question="Give me a formatted output.",
    real_question="I need to share this with someone / document for audit.",
    hidden_worry="I'll look bad if this isn't complete and professional.",
    
    # HUNT
    primary_truths=[TruthType.CONFIGURATION, TruthType.REALITY],
    hunting_truths=[TruthType.REFERENCE, TruthType.REGULATORY, TruthType.INTENT],
    hunt_for=[
        "What audience needs (executive vs technical)",
        "Completeness gaps (missing context)",
        "Issues worth highlighting",
        "Comparison/benchmark data to include",
        "Compliance documentation requirements"
    ],
    
    # SYNTHESIZE
    answer_sections=[
        "executive_summary",     # Top-line for leadership
        "key_findings",          # What matters
        "detailed_data",         # The evidence
        "issues_flagged",        # Problems to address
        "recommendations",       # What to do
        "appendix"               # Supporting detail
    ],
    risk_framing="Gaps in this report: [what's missing that stakeholder might ask]",
    
    # DELIVER
    excel_sheets=[
        ExcelSheet("Executive Summary", TruthType.CONFIGURATION, "summary"),
        ExcelSheet("Detail", TruthType.REALITY, "evidence"),
        ExcelSheet("Issues & Actions", TruthType.CONFIGURATION, "action_items"),
        ExcelSheet("Compliance Notes", TruthType.REGULATORY, "documentation"),
    ],
    
    # EXTEND
    proactive_offers=[
        "Format for a specific audience?",
        "Add trend analysis?",
        "Include compliance certification?"
    ],
    hcmpact_hook="Need HCMPACT to prepare executive presentation?"
)


# -----------------------------------------------------------------------------
# ADVISORY: Think For Me Questions (Highest Value)
# -----------------------------------------------------------------------------

PATTERNS["strategy"] = ResponsePattern(
    question_type="strategy",
    category=QuestionCategory.ADVISORY,
    trigger_patterns=[
        "how would I", "how would you", "best way to", "approach",
        "strategy for", "recommend", "should I", "what's the best"
    ],
    
    # UNDERSTAND
    surface_question="What's the right approach?",
    real_question="Tell me what to do so I don't screw this up.",
    hidden_worry="There's a right way and a wrong way and I don't know which is which.",
    
    # HUNT
    primary_truths=[TruthType.REFERENCE, TruthType.CONFIGURATION],
    hunting_truths=[TruthType.REGULATORY, TruthType.INTENT, TruthType.REALITY],
    hunt_for=[
        "Industry best practice approach",
        "What similar customers have done",
        "Current state that affects the decision",
        "Regulatory constraints on options",
        "Resource/timeline implications"
    ],
    
    # SYNTHESIZE
    answer_sections=[
        "recommended_approach",  # "I recommend: X because Y"
        "rationale",             # Why this is the right approach
        "alternatives",          # Other options considered
        "current_state_factors", # How your data affects the decision
        "implementation_outline",# High-level steps
        "risks_and_mitigations"  # What could go wrong
    ],
    risk_framing="Alternative approaches: [option, tradeoff for each]",
    
    # DELIVER
    excel_sheets=[
        ExcelSheet("Options Analysis", TruthType.REFERENCE, "comparison"),
        ExcelSheet("Current State", TruthType.CONFIGURATION, "baseline"),
        ExcelSheet("Implementation Plan", TruthType.REFERENCE, "action_items"),
    ],
    
    # EXTEND
    proactive_offers=[
        "Deep dive on a specific option?",
        "Build out full implementation plan?",
        "Identify quick wins to start?"
    ],
    hcmpact_hook="Want HCMPACT to lead this initiative?"
)


PATTERNS["analyze"] = ResponsePattern(
    question_type="analyze",
    category=QuestionCategory.ADVISORY,
    trigger_patterns=[
        "analyze", "assess", "evaluate", "review", "deep dive",
        "can you analyze", "take a look at", "dig into"
    ],
    
    # UNDERSTAND
    surface_question="Give me a thorough assessment.",
    real_question="Find the problems I don't know about.",
    hidden_worry="There are landmines hidden in here.",
    
    # HUNT
    primary_truths=[TruthType.CONFIGURATION, TruthType.REALITY],
    hunting_truths=[TruthType.REFERENCE, TruthType.REGULATORY, TruthType.INTENT],
    hunt_for=[
        "Everything that's wrong (comprehensive)",
        "Risk prioritization (critical vs minor)",
        "Patterns indicating systemic issues",
        "Deviations from standard/expected",
        "Gaps vs requirements/intent",
        "Compliance exposures",
        "Efficiency opportunities"
    ],
    
    # SYNTHESIZE
    answer_sections=[
        "executive_summary",     # "X critical, Y high, Z medium issues"
        "critical_findings",     # Must address immediately
        "high_priority",         # Address soon
        "medium_priority",       # Plan to address
        "observations",          # Minor/informational
        "patterns_identified",   # Systemic issues
        "prioritized_roadmap"    # What order to fix
    ],
    risk_framing="If no action taken: [consequences by priority level]",
    
    # DELIVER
    excel_sheets=[
        ExcelSheet("Executive Summary", TruthType.CONFIGURATION, "summary"),
        ExcelSheet("All Findings", TruthType.CONFIGURATION, "evidence"),
        ExcelSheet("Critical Issues", TruthType.CONFIGURATION, "action_items", filter_to_issues=True),
        ExcelSheet("Roadmap", TruthType.REFERENCE, "planning"),
    ],
    
    # EXTEND
    proactive_offers=[
        "Deep dive on critical findings?",
        "Extend analysis to related areas?",
        "Build remediation project plan?"
    ],
    hcmpact_hook="Want HCMPACT to lead the remediation effort?"
)


PATTERNS["alternatives"] = ResponsePattern(
    question_type="alternatives",
    category=QuestionCategory.ADVISORY,
    trigger_patterns=[
        "alternative", "other options", "different way", "instead of",
        "what else", "other approaches", "another way"
    ],
    
    # UNDERSTAND
    surface_question="What are my other options?",
    real_question="Is there a better way I haven't thought of?",
    hidden_worry="I'm about to do something suboptimal.",
    
    # HUNT
    primary_truths=[TruthType.REFERENCE, TruthType.CONFIGURATION],
    hunting_truths=[TruthType.REGULATORY, TruthType.REALITY, TruthType.INTENT],
    hunt_for=[
        "All viable alternatives",
        "Pros/cons of each",
        "Which fits their current setup best",
        "Regulatory constraints on options",
        "Implementation effort for each",
        "What similar customers chose"
    ],
    
    # SYNTHESIZE
    answer_sections=[
        "options_overview",      # "There are X alternatives"
        "option_details",        # Each option explained
        "comparison_matrix",     # Side-by-side pros/cons
        "fit_analysis",          # Which fits your situation
        "recommendation",        # What I'd choose and why
        "next_steps"             # How to proceed with chosen option
    ],
    risk_framing="Tradeoffs: [what you gain/lose with each option]",
    
    # DELIVER
    excel_sheets=[
        ExcelSheet("Options Comparison", TruthType.REFERENCE, "comparison"),
        ExcelSheet("Fit Analysis", TruthType.CONFIGURATION, "analysis"),
        ExcelSheet("Implementation Comparison", TruthType.REFERENCE, "planning"),
    ],
    
    # EXTEND
    proactive_offers=[
        "Model out a specific option?",
        "Talk through decision criteria?",
        "Pilot test an approach?"
    ],
    hcmpact_hook="Want HCMPACT to evaluate options with you?"
)


# =============================================================================
# PATTERN MATCHING & RETRIEVAL
# =============================================================================

def detect_question_type(question: str) -> ResponsePattern:
    """
    Detect the question type and return the appropriate response pattern.
    
    Uses trigger patterns to match, with fallback to 'analyze' for ambiguous.
    """
    q_lower = question.lower()
    
    # Score each pattern by trigger matches
    scores = {}
    for pattern_name, pattern in PATTERNS.items():
        score = 0
        for trigger in pattern.trigger_patterns:
            if trigger in q_lower:
                # Longer triggers = more specific = higher score
                score += len(trigger.split())
        scores[pattern_name] = score
    
    # Get highest scoring pattern
    best_match = max(scores, key=scores.get)
    
    # If no good match, default to 'analyze' (most comprehensive)
    if scores[best_match] == 0:
        return PATTERNS["analyze"]
    
    return PATTERNS[best_match]


def get_pattern(pattern_name: str) -> ResponsePattern:
    """Get a specific pattern by name."""
    return PATTERNS.get(pattern_name, PATTERNS["analyze"])


def get_all_patterns() -> Dict[str, ResponsePattern]:
    """Get all patterns."""
    return PATTERNS


# =============================================================================
# PROMPT GENERATION FROM PATTERN
# =============================================================================

def generate_thinking_prompt(pattern: ResponsePattern, question: str) -> str:
    """
    Generate a prompt that guides the LLM through the consultant's thinking chain.
    
    This isn't about formatting the answer - it's about HOW to think.
    """
    # Question-type specific instructions
    type_specific = ""
    
    if pattern.question_type == "inventory":
        type_specific = """
CRITICAL FOR INVENTORY QUESTIONS:
You MUST list the actual items with their codes and descriptions.
Format: `CODE` - Description
DISPLAY up to 30 items in response, but ANALYZE all data for gaps/issues.
Group by category if there are clear categories.
Note: "Full list of X items available in attached Excel"
DO NOT just describe or summarize - SHOW THE ACTUAL DATA."""

    elif pattern.question_type == "count":
        type_specific = """
CRITICAL FOR COUNT QUESTIONS:
Lead with the exact number: "You have X [items]"
Then break down by category/status/type.
Show percentages where meaningful."""

    elif pattern.question_type == "lookup":
        type_specific = """
CRITICAL FOR LOOKUP QUESTIONS:
Show the complete details of the specific item requested.
Include all fields/attributes.
Then show what's connected to it."""

    elif pattern.question_type == "validation":
        type_specific = """
CRITICAL FOR VALIDATION QUESTIONS:
Start with overall assessment: COMPLIANT / NON-COMPLIANT / PARTIAL
List specific issues found with evidence.
List what IS correct (builds confidence)."""

    elif pattern.question_type == "compliance":
        type_specific = """
CRITICAL FOR COMPLIANCE QUESTIONS:
Reference specific regulations by name.
Show current config vs requirement.
Flag gaps with severity (critical/high/medium)."""

    elif pattern.question_type in ["strategy", "analyze", "alternatives"]:
        type_specific = """
CRITICAL FOR ADVISORY QUESTIONS:
Give a clear recommendation with rationale.
Show alternatives considered and why not chosen.
Be opinionated - they're paying for expertise, not options."""

    return f"""You are a senior implementation consultant. A client asked:

"{question}"

UNDERSTAND THE QUESTION:
- Surface question: {pattern.surface_question}
- Real question: {pattern.real_question}  
- Hidden worry: {pattern.hidden_worry}
{type_specific}

=== FORMATTING RULES (CRITICAL) ===
1. USE BULLETS, NOT PARAGRAPHS - Nobody reads walls of text
2. SHOW YOUR SOURCES - Start each section with "From [table_name]:" so they know where data came from
3. DISPLAY MAX 30 ITEMS - Show up to 30 in response, note "Full list in Excel" if more exist
4. ANALYZE EVERYTHING - Use ALL the data provided to find issues, gaps, and patterns
5. BE CONCISE - Each bullet should be one line, not a paragraph

YOUR TASK - Follow this thinking chain:

1. GROUND IN FACTS (with source attribution)
   • From [table_name]: [specific data]
   • Quote actual values, codes, names
   • Show up to 30 items, note total count
   
2. HUNT FOR PROBLEMS (analyze ALL data)
   Look for: {', '.join(pattern.hunt_for)}
   • Flag each issue as a bullet with source

3. ASSESS RISK
   {pattern.risk_framing}

4. RECOMMENDATIONS (bulleted, prioritized)
   • Action 1 (highest priority)
   • Action 2
   • etc.

5. NEXT STEPS
   • {pattern.proactive_offers[0] if pattern.proactive_offers else 'Further analysis available'}
   • Full data available in attached Excel
   • If complex: "{pattern.hcmpact_hook}"

Remember: They don't know what they want, only what they don't want. 
Find the problems before they become crises.
Keep it scannable. Bullets. Sources. No fluff."""


def generate_excel_spec(pattern: ResponsePattern) -> List[Dict]:
    """Generate the Excel sheet specifications for this pattern."""
    return [
        {
            "sheet_name": sheet.name,
            "source": sheet.source_truth.value,
            "purpose": sheet.purpose,
            "filter_to_issues": sheet.filter_to_issues
        }
        for sheet in pattern.excel_sheets
    ]
