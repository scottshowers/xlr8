"""
XLR8 Intent Engine - Consultative Clarification System
=======================================================

Replaces BusinessRuleInterpreter with a system that:
1. Asks business questions, not technical ones
2. Captures intent, not SQL fragments
3. Builds memory at session/project/global levels
4. Passes intent context to LLM for SQL generation

The clarification question serves FOUR purposes:
1. Better SQL (immediate) - LLM knows what user wants
2. Intent capture (session) - Current conversation context
3. Pattern learning (project) - This customer's preferences
4. Global patterns (global) - Cross-customer knowledge

Author: XLR8 Team
Date: January 23, 2026
Version: 1.0.0
"""

import re
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


# =============================================================================
# INTENT TAXONOMY
# =============================================================================

class IntentCategory(Enum):
    """High-level intent categories."""
    EXPLORE = "explore"          # "What do I have?" - Discovery
    COUNT = "count"              # "How many?" - Headcount, totals
    TREND = "trend"              # "Over time" - Change analysis
    COMPARE = "compare"          # "vs" - Side by side
    FIND = "find"                # "Show me" - List/filter
    VALIDATE = "validate"        # "Is this right?" - Verification
    DIAGNOSE = "diagnose"        # "Why?" - Root cause
    ANALYZE = "analyze"          # General analysis
    UNKNOWN = "unknown"          # Needs clarification


class FeatureCategory(Enum):
    """Maps to playbook feature categories for workflow capture."""
    INGEST = "ingest"
    TRANSFORM = "transform"
    COMPARE = "compare"
    ANALYZE = "analyze"
    COLLABORATE = "collaborate"
    OUTPUT = "output"
    GUIDE = "guide"


@dataclass
class ResolvedIntent:
    """
    Fully resolved user intent - ready for SQL generation.
    
    This is what gets passed to the LLM as context.
    """
    # What they're trying to do
    category: IntentCategory
    feature_category: FeatureCategory
    
    # Natural language description of intent
    description: str  # e.g., "Headcount trend over time"
    
    # Specific parameters resolved from clarification
    parameters: Dict[str, Any] = field(default_factory=dict)
    # e.g., {"time_dimension": "hire_date", "grouping": "month", "status_filter": "active"}
    
    # For provenance
    clarifications_used: List[str] = field(default_factory=list)
    confidence: float = 1.0
    
    # For memory storage
    original_question: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ClarificationNeeded:
    """
    Request for user clarification - consultative, not technical.
    """
    # Unique key for this clarification type
    key: str
    
    # The question to ask (business language)
    question: str
    
    # Options with business meaning
    options: List[Dict[str, str]]  # [{display, value, description}, ...]
    
    # Context for the question
    context: str = ""
    
    # What intent category this helps resolve
    resolves_category: Optional[IntentCategory] = None
    
    # Is this required or just improves confidence?
    required: bool = True
    
    # What feature category does this map to?
    feature_category: Optional[FeatureCategory] = None


# =============================================================================
# INTENT PATTERNS - Business Questions, Not Regex
# =============================================================================

# These define WHAT to ask, not HOW to query
INTENT_PATTERNS = {
    # -------------------------------------------------------------------------
    # TEMPORAL PATTERNS - "by date", "over time", "as of"
    # -------------------------------------------------------------------------
    "temporal_analysis": {
        "triggers": [
            r"\bby\s+date\b",
            r"\bover\s+time\b",
            r"\btrend\b",
            r"\bby\s+month\b",
            r"\bby\s+year\b",
            r"\bby\s+quarter\b",
        ],
        "question": "What are you trying to understand?",
        "options": [
            # NOTE: "Headcount trend" removed - requires complex hire/term/transfer calculation
            # that isn't implemented yet. Added to roadmap. - Jan 24, 2026
            {
                "display": "Hiring velocity - rate of new hires over time",
                "value": "hiring_velocity",
                "description": "Rate of new hires over time",
                "intent_params": {"analysis_type": "hires", "time_dimension": "hire_date", "time_grouping": "year"}
            },
            {
                "display": "Turnover patterns - when employees leave",
                "value": "turnover_patterns",
                "description": "When employees leave",
                "intent_params": {"analysis_type": "terminations", "time_dimension": "term_date", "time_grouping": "year"}
            },
            {
                "display": "Tenure distribution - how long employees have been here",
                "value": "tenure_distribution",
                "description": "How long employees have been here",
                "intent_params": {"analysis_type": "tenure", "time_dimension": "hire_date", "time_grouping": "year"}
            },
            {
                "display": "Something else - let me explain what I need",
                "value": "custom",
                "description": "I'll describe what I need",
                "intent_params": {"analysis_type": "custom"}
            },
        ],
        "category": IntentCategory.TREND,
        "feature_category": FeatureCategory.ANALYZE,
    },
    
    # -------------------------------------------------------------------------
    # POINT IN TIME - "as of", "on date"
    # -------------------------------------------------------------------------
    "point_in_time": {
        "triggers": [
            r"\bas\s+of\s+",
            r"\bon\s+\d{1,2}[/-]\d{1,2}",
            r"\bon\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}",
            r"\bat\s+(?:end|start)\s+of",
            r"\bpoint\s+in\s+time\b",
        ],
        "question": "What should 'as of' that date mean?",
        "options": [
            {
                "display": "Active headcount on that date - employees who were active (not terminated) as of that date",
                "value": "active_headcount",
                "description": "Employees who were active (not terminated) as of that date",
                "intent_params": {"pit_logic": "active_on_date", "include_statuses": ["A", "L"]}
            },
            {
                "display": "Everyone employed by that date - anyone hired on or before, regardless of current status",
                "value": "employed_by",
                "description": "Anyone hired on or before that date, regardless of current status",
                "intent_params": {"pit_logic": "hired_by_date", "include_statuses": "all"}
            },
            {
                "display": "Data snapshot - the exact state of records on that date",
                "value": "data_snapshot",
                "description": "The exact state of records on that date",
                "intent_params": {"pit_logic": "snapshot", "include_statuses": "all"}
            },
        ],
        "category": IntentCategory.COUNT,
        "feature_category": FeatureCategory.ANALYZE,
    },
    
    # -------------------------------------------------------------------------
    # STATUS FILTERS - "active", "terminated"
    # -------------------------------------------------------------------------
    "employee_status": {
        "triggers": [
            r"\bactive\b",
            r"\bcurrent\s+employees\b",
        ],
        "question": "How do you define 'active' for this analysis?",
        "options": [
            {
                "display": "Active employees only (status A) - just those currently working",
                "value": "active_only",
                "description": "Just those with Active status",
                "intent_params": {"status_filter": ["A"]}
            },
            {
                "display": "Active + on leave (status A or L) - typical for headcount reporting",
                "value": "active_and_leave",
                "description": "Include those on leave as part of headcount",
                "intent_params": {"status_filter": ["A", "L"]}
            },
            {
                "display": "All non-terminated - everyone except terms",
                "value": "all_non_termed",
                "description": "Everyone except terminated employees",
                "intent_params": {"status_filter": ["A", "L", "P", "S"]}
            },
        ],
        "category": IntentCategory.COUNT,
        "feature_category": FeatureCategory.ANALYZE,
    },
    
    "terminated_status": {
        "triggers": [
            r"\bterminated\b",
            r"\bterms\b",
            r"\bleft\b",
            r"\bexited\b",
        ],
        "question": "What termination data do you need?",
        "options": [
            {
                "display": "Count of terminated employees",
                "value": "term_count",
                "description": "How many have been terminated",
                "intent_params": {"analysis_type": "count", "status_filter": ["T"]}
            },
            {
                "display": "Termination reasons breakdown",
                "value": "term_reasons",
                "description": "Why employees left (voluntary, involuntary, etc.)",
                "intent_params": {"analysis_type": "breakdown", "dimension": "term_reason"}
            },
            {
                "display": "Termination timing/patterns",
                "value": "term_timing",
                "description": "When terminations happened over time",
                "intent_params": {"analysis_type": "trend", "time_dimension": "term_date"}
            },
        ],
        "category": IntentCategory.ANALYZE,
        "feature_category": FeatureCategory.ANALYZE,
    },
    
    # -------------------------------------------------------------------------
    # HEADCOUNT - "how many", "headcount", "count"
    # -------------------------------------------------------------------------
    "headcount": {
        "triggers": [
            r"\bheadcount\b",
            r"\bhow\s+many\s+employees\b",
            r"\bemployee\s+count\b",
            r"\bnumber\s+of\s+employees\b",
            r"\btotal\s+employees\b",
        ],
        "question": "What should headcount include?",
        "options": [
            {
                "display": "Active employees only",
                "value": "active_only",
                "description": "Just those currently working",
                "intent_params": {"status_filter": ["A"]}
            },
            {
                "display": "Active plus employees on leave",
                "value": "active_and_leave",
                "description": "Include leaves in headcount (typical for reporting)",
                "intent_params": {"status_filter": ["A", "L"]}
            },
            {
                "display": "All employees regardless of status",
                "value": "all",
                "description": "Everyone in the system",
                "intent_params": {"status_filter": None}
            },
        ],
        "category": IntentCategory.COUNT,
        "feature_category": FeatureCategory.ANALYZE,
    },
    
    # -------------------------------------------------------------------------
    # COMPARISON - "compare", "vs", "difference"
    # -------------------------------------------------------------------------
    "data_comparison": {
        "triggers": [
            r"\bcompare\b",
            r"\bvs\b",
            r"\bversus\b",
            r"\bdifference\b",
            r"\bdiscrepanc",
            r"\bparallel\b",
        ],
        "question": "What kind of comparison do you need?",
        "options": [
            {
                "display": "Find all differences - show me everything that doesn't match",
                "value": "all_differences",
                "description": "Show me everything that doesn't match",
                "intent_params": {"comparison_type": "full_diff", "tolerance": "exact"}
            },
            {
                "display": "Significant variances only - ignore small differences, show material issues",
                "value": "significant_only",
                "description": "Ignore small differences, show material issues",
                "intent_params": {"comparison_type": "material_diff", "tolerance": "threshold"}
            },
            {
                "display": "Categorize differences - group discrepancies by root cause type",
                "value": "categorized",
                "description": "Group discrepancies by root cause category",
                "intent_params": {"comparison_type": "categorized", "auto_categorize": True}
            },
        ],
        "category": IntentCategory.COMPARE,
        "feature_category": FeatureCategory.COMPARE,
    },
    
    # -------------------------------------------------------------------------
    # GROUPING - "by department", "by location", "by company"
    # -------------------------------------------------------------------------
    "grouping_dimension": {
        "triggers": [
            r"\bby\s+(?:department|dept)\b",
            r"\bby\s+location\b",
            r"\bby\s+company\b",
            r"\bby\s+cost\s*center\b",
            r"\bbreak\s*down\s+by\b",
        ],
        "question": "How would you like this grouped?",
        "options": [
            {
                "display": "Show hierarchy (e.g., Company > Dept > Team)",
                "value": "hierarchical",
                "description": "Nested breakdown with subtotals",
                "intent_params": {"grouping_style": "hierarchical"}
            },
            {
                "display": "Flat list with totals",
                "value": "flat",
                "description": "Simple list, one row per group",
                "intent_params": {"grouping_style": "flat"}
            },
            {
                "display": "Top 10 only",
                "value": "top_10",
                "description": "Just the largest groups",
                "intent_params": {"grouping_style": "flat", "limit": 10, "sort": "desc"}
            },
        ],
        "category": IntentCategory.COUNT,
        "feature_category": FeatureCategory.ANALYZE,
    },
}


# =============================================================================
# INTENT ENGINE
# =============================================================================

class IntentEngine:
    """
    Consultative intent resolution engine.
    
    Replaces BusinessRuleInterpreter with a system that:
    - Asks business questions, not technical ones
    - Captures intent for memory storage
    - Passes rich context to LLM for SQL generation
    """
    
    def __init__(self, conn=None, project: str = None, vendor: str = None, product: str = None):
        """
        Args:
            conn: DuckDB connection (for project memory)
            project: Project identifier
            vendor: Vendor context (e.g., "ukg", "adp")
            product: Product context (e.g., "pro", "workforce_now")
        """
        self.conn = conn
        self.project = project
        self.vendor = vendor
        self.product = product
        
        # Memory caches
        self._session_intents: List[ResolvedIntent] = []  # Current session
        self._project_memory: Dict[str, Any] = {}         # Loaded from DB
        self._confirmed_intents: Dict[str, str] = {}      # Confirmed this session
        
        # Schema cache for column clarifications
        self._schema_columns: Dict[str, List[str]] = {}   # table -> columns
        
        # Initialize project memory
        if conn and project:
            self._init_memory_tables()
            self._load_project_memory()
            self._load_schema_columns()
    
    # =========================================================================
    # MEMORY INITIALIZATION
    # =========================================================================
    
    def _init_memory_tables(self):
        """Create memory tables if they don't exist."""
        try:
            # Project intents table - use SERIAL for auto-increment in DuckDB
            self.conn.execute("""
                CREATE SEQUENCE IF NOT EXISTS seq_project_intents START 1
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS _project_intents (
                    id INTEGER DEFAULT nextval('seq_project_intents') PRIMARY KEY,
                    project VARCHAR,
                    pattern_key VARCHAR,
                    resolved_value VARCHAR,
                    resolved_description VARCHAR,
                    intent_params VARCHAR,
                    use_count INTEGER DEFAULT 1,
                    last_used TIMESTAMP DEFAULT NOW(),
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(project, pattern_key)
                )
            """)
            
            # Workflow steps table (for playbook capture)
            self.conn.execute("""
                CREATE SEQUENCE IF NOT EXISTS seq_workflow_steps START 1
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS _workflow_steps (
                    id INTEGER DEFAULT nextval('seq_workflow_steps') PRIMARY KEY,
                    project VARCHAR,
                    session_id VARCHAR,
                    step_order INTEGER,
                    feature_category VARCHAR,
                    intent_category VARCHAR,
                    intent_description VARCHAR,
                    question VARCHAR,
                    parameters VARCHAR,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            logger.info("[INTENT] Memory tables initialized")
            
        except Exception as e:
            logger.warning(f"[INTENT] Could not initialize memory tables: {e}")
    
    def _load_project_memory(self):
        """Load previously learned intents for this project."""
        try:
            results = self.conn.execute("""
                SELECT pattern_key, resolved_value, resolved_description, intent_params, use_count
                FROM _project_intents
                WHERE project = ?
                ORDER BY use_count DESC
            """, [self.project]).fetchall()
            
            for pattern_key, value, description, params_json, use_count in results:
                self._project_memory[pattern_key] = {
                    "value": value,
                    "description": description,
                    "params": json.loads(params_json) if params_json else {},
                    "use_count": use_count
                }
            
            if self._project_memory:
                logger.warning(f"[INTENT] Loaded {len(self._project_memory)} learned intents for project {self.project}")
                
        except Exception as e:
            logger.warning(f"[INTENT] Could not load project memory: {e}")
    
    def _load_schema_columns(self):
        """Load column names from schema for dynamic clarifications."""
        try:
            if not self.conn or not self.project:
                return
            
            # Get all tables for this project
            tables = self.conn.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_name LIKE ? AND table_schema = 'main'
            """, [f"{self.project}%"]).fetchall()
            
            for (table_name,) in tables:
                if table_name.startswith('_'):
                    continue
                try:
                    cols = self.conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
                    self._schema_columns[table_name] = [row[1] for row in cols]
                except Exception:
                    pass
            
            if self._schema_columns:
                total_cols = sum(len(cols) for cols in self._schema_columns.values())
                logger.info(f"[INTENT] Loaded schema: {len(self._schema_columns)} tables, {total_cols} columns")
                
        except Exception as e:
            logger.warning(f"[INTENT] Could not load schema columns: {e}")
    
    def _find_matching_columns(self, keywords: List[str]) -> List[Dict[str, str]]:
        """Find columns matching any of the keywords."""
        matches = []
        seen_lowercase = set()  # Dedupe by lowercase to avoid case variations
        
        for table_name, columns in self._schema_columns.items():
            for col in columns:
                col_lower = col.lower()
                
                # Skip if we've already seen this column name (case-insensitive)
                if col_lower in seen_lowercase:
                    continue
                
                if all(kw in col_lower for kw in keywords):
                    seen_lowercase.add(col_lower)
                    # Get short table name for display
                    short_table = table_name.split('_')[-2:] if '_' in table_name else [table_name]
                    short_table = '_'.join(short_table)
                    matches.append({
                        "table": table_name,
                        "column": col,
                        "display": f"{col} (from {short_table})",
                        "value": f"{table_name}.{col}"
                    })
        return matches
    
    def _check_column_clarification_needed(self, resolved_params: Dict) -> Optional[ClarificationNeeded]:
        """
        Check if we need to clarify which column to use based on resolved intent.
        
        This is called AFTER the main intent is resolved but BEFORE SQL generation.
        """
        time_dimension = resolved_params.get("time_dimension")
        
        if not time_dimension:
            return None
        
        # Already have a specific column resolved?
        if "hire_date_column" in self._confirmed_intents:
            return None
        if "term_date_column" in self._confirmed_intents:
            return None
        
        # Check project memory for column preference
        if "hire_date_column" in self._project_memory:
            self._confirmed_intents["hire_date_column"] = self._project_memory["hire_date_column"]["value"]
            return None
        if "term_date_column" in self._project_memory:
            self._confirmed_intents["term_date_column"] = self._project_memory["term_date_column"]["value"]
            return None
        
        # Find matching columns based on time_dimension
        if time_dimension == "hire_date":
            matches = self._find_matching_columns(["hire"])
            # Filter to date-like columns
            date_matches = [m for m in matches if any(d in m["column"].lower() for d in ["date", "dt"])]
            if not date_matches:
                date_matches = matches  # Fall back to any hire column
            
            if len(date_matches) > 1:
                # Multiple hire date columns - need clarification
                options = []
                for m in date_matches:
                    # Build business-friendly labels
                    col_lower = m["column"].lower()
                    if "last" in col_lower or "recent" in col_lower:
                        desc = "Most recent hire date (captures rehires)"
                    elif "original" in col_lower or "first" in col_lower:
                        desc = "Original hire date (first time employed)"
                    elif "adjusted" in col_lower:
                        desc = "Adjusted hire date (may reflect seniority adjustments)"
                    else:
                        desc = f"Hire date field"
                    
                    options.append({
                        "display": f"{m['column']} - {desc}",
                        "value": m["value"],
                        "description": desc,
                        "intent_params": {"hire_date_column": m["value"]}
                    })
                
                return ClarificationNeeded(
                    key="hire_date_column",
                    question="Which hire date should I use for this analysis?",
                    options=options,
                    context="Multiple hire date fields found in your data",
                    resolves_category=IntentCategory.TREND,
                    required=True
                )
            elif len(date_matches) == 1:
                # Only one option - auto-apply
                self._confirmed_intents["hire_date_column"] = date_matches[0]["value"]
        
        elif time_dimension == "term_date":
            matches = self._find_matching_columns(["term"])
            if not matches:
                matches = self._find_matching_columns(["separation"])
            
            date_matches = [m for m in matches if any(d in m["column"].lower() for d in ["date", "dt"])]
            if not date_matches:
                date_matches = matches
            
            if len(date_matches) > 1:
                options = []
                for m in date_matches:
                    col_lower = m["column"].lower()
                    if "last" in col_lower:
                        desc = "Last/most recent termination date"
                    elif "original" in col_lower:
                        desc = "Original termination date"
                    else:
                        desc = "Termination date field"
                    
                    options.append({
                        "display": f"{m['column']} - {desc}",
                        "value": m["value"],
                        "description": desc,
                        "intent_params": {"term_date_column": m["value"]}
                    })
                
                return ClarificationNeeded(
                    key="term_date_column",
                    question="Which termination date should I use for this analysis?",
                    options=options,
                    context="Multiple termination date fields found in your data",
                    resolves_category=IntentCategory.TREND,
                    required=True
                )
            elif len(date_matches) == 1:
                self._confirmed_intents["term_date_column"] = date_matches[0]["value"]
        
        return None
    
    # =========================================================================
    # MAIN INTERFACE
    # =========================================================================
    
    def analyze(self, question: str) -> Tuple[Optional[ResolvedIntent], Optional[ClarificationNeeded]]:
        """
        Analyze a question and determine if clarification is needed.
        
        Args:
            question: User's natural language question
            
        Returns:
            Tuple of (resolved_intent, clarification_needed)
            - If clarification_needed is not None, ask the user
            - If resolved_intent is not None, proceed with SQL generation
        """
        q_lower = question.lower()
        
        # Detect all matching patterns
        detected_patterns = self._detect_patterns(q_lower)
        
        if not detected_patterns:
            # No patterns detected - no clarification needed
            # Return basic intent for LLM to figure out
            return self._make_basic_intent(question), None
        
        logger.warning(f"[INTENT] Detected patterns: {[p['key'] for p in detected_patterns]}")
        
        # Check each pattern against memory
        for pattern in detected_patterns:
            pattern_key = pattern["key"]
            
            # Already confirmed this session?
            if pattern_key in self._confirmed_intents:
                logger.warning(f"[INTENT] Using session-confirmed intent for '{pattern_key}'")
                continue
            
            # In project memory?
            if pattern_key in self._project_memory:
                memory = self._project_memory[pattern_key]
                logger.warning(f"[INTENT] Using learned intent for '{pattern_key}': {memory['description']}")
                
                # Auto-apply from memory
                self._confirmed_intents[pattern_key] = memory["value"]
                continue
            
            # Need to ask
            clarification = self._build_clarification(pattern)
            logger.warning(f"[INTENT] Clarification needed for '{pattern_key}': {clarification.question}")
            return None, clarification
        
        # All patterns resolved - build full intent
        resolved = self._build_resolved_intent(question, detected_patterns)
        
        # NEW: Check if we need column-level clarification based on resolved intent
        if resolved and resolved.parameters:
            column_clarification = self._check_column_clarification_needed(resolved.parameters)
            if column_clarification:
                logger.warning(f"[INTENT] Column clarification needed: {column_clarification.question}")
                return None, column_clarification
        
        return resolved, None
    
    def apply_clarification(self, pattern_key: str, value: str, save_to_project: bool = True) -> Optional[Dict]:
        """
        Apply a user's clarification answer.
        
        Args:
            pattern_key: Which pattern this answers
            value: The selected value
            save_to_project: Whether to remember this for future use
            
        Returns:
            The intent parameters to apply, or None if invalid
        """
        # Handle dynamic column clarifications (not in static INTENT_PATTERNS)
        if pattern_key in ["hire_date_column", "term_date_column"]:
            # Store in session
            self._confirmed_intents[pattern_key] = value
            
            # Save to project memory
            if save_to_project and self.conn and self.project:
                # Extract column name for description
                col_name = value.split('.')[-1] if '.' in value else value
                self._save_to_project_memory(
                    pattern_key=pattern_key,
                    value=value,
                    description=f"Use {col_name} for {pattern_key.replace('_column', '')}",
                    params={pattern_key: value}
                )
            
            logger.warning(f"[INTENT] Applied column clarification: {pattern_key} = {value}")
            return {pattern_key: value}
        
        # Find the pattern in static patterns
        if pattern_key not in INTENT_PATTERNS:
            logger.warning(f"[INTENT] Unknown pattern key: {pattern_key}")
            return None
        
        pattern = INTENT_PATTERNS[pattern_key]
        
        # Find the selected option
        selected = None
        for option in pattern["options"]:
            if option["value"] == value:
                selected = option
                break
        
        if not selected:
            logger.warning(f"[INTENT] Invalid value '{value}' for pattern '{pattern_key}'")
            return None
        
        # Store in session
        self._confirmed_intents[pattern_key] = value
        
        # Save to project memory
        if save_to_project and self.conn and self.project:
            self._save_to_project_memory(
                pattern_key=pattern_key,
                value=value,
                description=selected["display"],
                params=selected.get("intent_params", {})
            )
        
        logger.warning(f"[INTENT] Applied clarification: {pattern_key} = {value} ({selected['display']})")
        
        return selected.get("intent_params", {})
    
    # =========================================================================
    # INTERNAL METHODS
    # =========================================================================
    
    def _detect_patterns(self, question_lower: str) -> List[Dict]:
        """Detect which intent patterns match the question."""
        detected = []
        
        for pattern_key, pattern_config in INTENT_PATTERNS.items():
            for trigger in pattern_config["triggers"]:
                if re.search(trigger, question_lower):
                    detected.append({
                        "key": pattern_key,
                        "config": pattern_config,
                        "trigger": trigger
                    })
                    break  # One match per pattern is enough
        
        return detected
    
    def _build_clarification(self, pattern: Dict) -> ClarificationNeeded:
        """Build a clarification request for an unresolved pattern."""
        config = pattern["config"]
        
        return ClarificationNeeded(
            key=pattern["key"],
            question=config["question"],
            options=config["options"],
            context=f"Pattern: {pattern['key']}",
            resolves_category=config.get("category"),
            feature_category=config.get("feature_category"),
            required=True
        )
    
    def _make_basic_intent(self, question: str) -> ResolvedIntent:
        """Make a basic intent when no patterns detected."""
        # Try to guess category from question
        q_lower = question.lower()
        
        if any(w in q_lower for w in ["how many", "count", "total"]):
            category = IntentCategory.COUNT
        elif any(w in q_lower for w in ["show", "list", "find"]):
            category = IntentCategory.FIND
        elif any(w in q_lower for w in ["compare", "vs", "difference"]):
            category = IntentCategory.COMPARE
        elif any(w in q_lower for w in ["why", "reason", "cause"]):
            category = IntentCategory.DIAGNOSE
        else:
            category = IntentCategory.UNKNOWN
        
        return ResolvedIntent(
            category=category,
            feature_category=FeatureCategory.ANALYZE,
            description="General query - no specific patterns detected",
            original_question=question,
            confidence=0.5  # Lower confidence without clarification
        )
    
    def _build_resolved_intent(self, question: str, patterns: List[Dict]) -> ResolvedIntent:
        """Build a fully resolved intent from confirmed patterns."""
        # Merge parameters from all confirmed patterns
        merged_params = {}
        descriptions = []
        
        for pattern in patterns:
            pattern_key = pattern["key"]
            config = pattern["config"]
            
            # Get confirmed value
            if pattern_key in self._confirmed_intents:
                value = self._confirmed_intents[pattern_key]
                
                # Find the option
                for option in config["options"]:
                    if option["value"] == value:
                        merged_params.update(option.get("intent_params", {}))
                        descriptions.append(option["display"])
                        break
        
        # Extract dates from question for point-in-time queries
        q_lower = question.lower()
        date_patterns = [
            r'as\s+of\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',  # as of 12/31/2025
            r'as\s+of\s+(\d{4}[/-]\d{1,2}[/-]\d{1,2})',    # as of 2025-12-31
            r'on\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',       # on 12/31/2025
            r'on\s+(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2}),?\s+(\d{4})',  # on January 1, 2024
            r'as\s+of\s+(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2}),?\s+(\d{4})',  # as of January 1, 2024
        ]
        for date_pattern in date_patterns:
            match = re.search(date_pattern, q_lower)
            if match:
                groups = match.groups()
                # Handle spelled-out month format
                if len(groups) == 3:
                    month_name, day, year = groups
                    month_map = {
                        'january': '01', 'february': '02', 'march': '03', 'april': '04',
                        'may': '05', 'june': '06', 'july': '07', 'august': '08',
                        'september': '09', 'october': '10', 'november': '11', 'december': '12'
                    }
                    month = month_map.get(month_name, '01')
                    merged_params['as_of_date'] = f"{year}-{month}-{day.zfill(2)}"
                else:
                    # Numeric date format
                    date_str = groups[0]
                    merged_params['as_of_date'] = self._normalize_date(date_str)
                logger.warning(f"[INTENT] Extracted date from question: {merged_params['as_of_date']}")
                break
        
        # Add any column selections from clarifications
        for key, value in self._confirmed_intents.items():
            if key.endswith('_column'):
                merged_params[key] = value
        
        # Use the first pattern's category as primary
        primary_pattern = patterns[0]["config"]
        
        return ResolvedIntent(
            category=primary_pattern.get("category", IntentCategory.UNKNOWN),
            feature_category=primary_pattern.get("feature_category", FeatureCategory.ANALYZE),
            description=" + ".join(descriptions) if descriptions else "Resolved from patterns",
            parameters=merged_params,
            clarifications_used=list(self._confirmed_intents.keys()),
            confidence=0.9,  # High confidence with clarification
            original_question=question
        )
    
    def _normalize_date(self, date_str: str) -> str:
        """Normalize date string to YYYY-MM-DD format."""
        import re
        
        # Try MM/DD/YYYY or MM-DD-YYYY
        match = re.match(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', date_str)
        if match:
            month, day, year = match.groups()
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        # Try YYYY-MM-DD or YYYY/MM/DD
        match = re.match(r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})', date_str)
        if match:
            year, month, day = match.groups()
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        # Try MM/DD/YY
        match = re.match(r'(\d{1,2})[/-](\d{1,2})[/-](\d{2})', date_str)
        if match:
            month, day, year = match.groups()
            # Assume 20xx for 2-digit years
            full_year = f"20{year}" if int(year) < 50 else f"19{year}"
            return f"{full_year}-{month.zfill(2)}-{day.zfill(2)}"
        
        # Return as-is if can't parse
        return date_str
    
    def _save_to_project_memory(self, pattern_key: str, value: str, description: str, params: Dict):
        """Save a resolved intent to project memory."""
        try:
            self.conn.execute("""
                INSERT INTO _project_intents (project, pattern_key, resolved_value, resolved_description, intent_params, use_count)
                VALUES (?, ?, ?, ?, ?, 1)
                ON CONFLICT (project, pattern_key) DO UPDATE SET
                    resolved_value = EXCLUDED.resolved_value,
                    resolved_description = EXCLUDED.resolved_description,
                    intent_params = EXCLUDED.intent_params,
                    use_count = _project_intents.use_count + 1,
                    last_used = NOW()
            """, [self.project, pattern_key, value, description, json.dumps(params)])
            
            # Update local cache
            self._project_memory[pattern_key] = {
                "value": value,
                "description": description,
                "params": params,
                "use_count": self._project_memory.get(pattern_key, {}).get("use_count", 0) + 1
            }
            
            logger.warning(f"[INTENT] Saved to project memory: {pattern_key} = {description}")
            
        except Exception as e:
            logger.warning(f"[INTENT] Could not save to project memory: {e}")
    
    # =========================================================================
    # CONTEXT FOR LLM
    # =========================================================================
    
    def format_for_llm(self, intent: ResolvedIntent) -> str:
        """
        Format resolved intent as context for LLM SQL generation.
        
        This is what gets injected into the SQL generation prompt.
        """
        lines = [
            "=== USER INTENT ===",
            f"Intent: {intent.description}",
            f"Category: {intent.category.value}",
        ]
        
        if intent.parameters:
            lines.append("Parameters:")
            for key, value in intent.parameters.items():
                lines.append(f"  - {key}: {value}")
        
        # Add specific column selections from clarifications
        if self._confirmed_intents:
            column_selections = []
            for key, value in self._confirmed_intents.items():
                if key.endswith("_column"):
                    # This is a specific column selection - extract table and column
                    if '.' in value:
                        table_name, col_name = value.rsplit('.', 1)
                        column_selections.append(f"  - {key}: Use column \"{col_name}\" from table \"{table_name}\"")
                    else:
                        column_selections.append(f"  - {key}: {value}")
            
            if column_selections:
                lines.append("Specific columns to use:")
                lines.extend(column_selections)
        
        if intent.clarifications_used:
            lines.append(f"Clarifications applied: {', '.join(intent.clarifications_used)}")
        
        lines.append(f"Confidence: {intent.confidence}")
        lines.append("===================")
        
        return "\n".join(lines)
    
    # =========================================================================
    # WORKFLOW CAPTURE (for playbook extraction)
    # =========================================================================
    
    def record_step(self, session_id: str, intent: ResolvedIntent, question: str):
        """Record a step for potential playbook extraction."""
        if not self.conn or not self.project:
            return
        
        try:
            # Get current step count for ordering
            result = self.conn.execute("""
                SELECT MAX(step_order) FROM _workflow_steps
                WHERE project = ? AND session_id = ?
            """, [self.project, session_id]).fetchone()
            
            next_order = (result[0] or 0) + 1
            
            self.conn.execute("""
                INSERT INTO _workflow_steps 
                (project, session_id, step_order, feature_category, intent_category, 
                 intent_description, question, parameters)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                self.project,
                session_id,
                next_order,
                intent.feature_category.value,
                intent.category.value,
                intent.description,
                question,
                json.dumps(intent.parameters)
            ])
            
            logger.info(f"[INTENT] Recorded workflow step {next_order}: {intent.description}")
            
        except Exception as e:
            logger.warning(f"[INTENT] Could not record workflow step: {e}")
    
    # =========================================================================
    # COMPATIBILITY
    # =========================================================================
    
    def interpret(self, question: str) -> Tuple[List[Any], Optional[ClarificationNeeded]]:
        """
        Compatibility wrapper matching BusinessRuleInterpreter.interpret() signature.
        
        Returns:
            Tuple of (rules_list, clarification_needed)
            - rules_list is empty (we pass intent through context, not rules)
            - clarification_needed if user input required
        """
        resolved_intent, clarification = self.analyze(question)
        
        if clarification:
            return [], clarification
        
        # Store resolved intent for later use in SQL generation
        if resolved_intent:
            self._current_intent = resolved_intent
        
        return [], None
    
    def get_current_intent(self) -> Optional[ResolvedIntent]:
        """Get the most recently resolved intent."""
        return getattr(self, '_current_intent', None)


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_intent_engine(
    conn=None, 
    project: str = None, 
    vendor: str = None, 
    product: str = None
) -> IntentEngine:
    """
    Create an IntentEngine instance.
    
    Args:
        conn: DuckDB connection
        project: Project identifier
        vendor: Vendor context
        product: Product context
        
    Returns:
        Configured IntentEngine
    """
    return IntentEngine(conn=conn, project=project, vendor=vendor, product=product)
