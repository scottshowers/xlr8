"""
XLR8 SEMANTIC VOCABULARY
========================

ONE source of truth for ALL semantic types across the platform.

Used by:
- structured_data_handler.py: Tag columns at upload
- standards_processor.py: Tag rule fields during extraction
- compliance_engine.py: Match rule fields to columns
- relationship_detector.py: Match columns across tables

NO MORE HARDCODED MAPPINGS scattered across files.

Deploy to: backend/utils/semantic_vocabulary.py
"""

from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field
import re
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# SEMANTIC TYPE DEFINITIONS
# =============================================================================

@dataclass
class SemanticType:
    """Definition of a semantic type with aliases and derived fields."""
    name: str                           # Primary name (e.g., "birth_date")
    category: str                       # Category (employee, org, pay, date, status)
    aliases: List[str] = field(default_factory=list)  # Alternative names
    patterns: List[str] = field(default_factory=list) # Regex patterns to match
    derives: List[str] = field(default_factory=list)  # Fields that can be derived (e.g., age from birth_date)
    derivation_sql: Dict[str, str] = field(default_factory=dict)  # SQL to derive fields
    description: str = ""
    
    def matches(self, text: str) -> Tuple[bool, float]:
        """
        Check if text matches this semantic type.
        Returns (matches, confidence).
        """
        text_norm = self._normalize(text)
        
        # Exact match on name
        if text_norm == self.name:
            return True, 0.95
        
        # Exact match on alias
        if text_norm in [self._normalize(a) for a in self.aliases]:
            return True, 0.90
        
        # Pattern match
        for pattern in self.patterns:
            if re.search(pattern, text_norm, re.IGNORECASE):
                return True, 0.85
        
        # Partial match on name or alias
        if self.name in text_norm or text_norm in self.name:
            return True, 0.70
        
        for alias in self.aliases:
            alias_norm = self._normalize(alias)
            if alias_norm in text_norm or text_norm in alias_norm:
                return True, 0.65
        
        return False, 0.0
    
    def _normalize(self, text: str) -> str:
        """Normalize text for comparison."""
        if not text:
            return ""
        text = text.lower().strip()
        text = re.sub(r'[\s\-\.]+', '_', text)
        return text


# =============================================================================
# THE VOCABULARY - All semantic types defined here
# =============================================================================

SEMANTIC_TYPES: Dict[str, SemanticType] = {}

def _register(st: SemanticType):
    """Register a semantic type."""
    SEMANTIC_TYPES[st.name] = st
    return st


# -----------------------------------------------------------------------------
# EMPLOYEE IDENTIFIERS
# -----------------------------------------------------------------------------

_register(SemanticType(
    name="employee_number",
    category="employee",
    aliases=["employee_id", "emp_id", "emp_no", "ee_id", "worker_id", "badge_number", "personnel_number"],
    patterns=[r"^emp.*(?:id|num|no)$", r"^ee.*(?:id|num)$", r"employee.*number"],
    description="Unique identifier for an employee"
))

_register(SemanticType(
    name="employee_name",
    category="employee",
    aliases=["emp_name", "worker_name", "full_name", "name"],
    patterns=[r"^(?:emp|employee).*name$", r"^(?:first|last|full).*name$"],
    description="Employee name field"
))

_register(SemanticType(
    name="employee_type_code",
    category="employee",
    aliases=["emp_type", "ee_type", "worker_type", "employment_type", "employee_classification"],
    patterns=[r"^emp.*type", r"^ee.*type", r"employee.*class"],
    description="Employee classification (FT, PT, Temp, etc.)"
))

_register(SemanticType(
    name="ssn",
    category="employee",
    aliases=["social_security_number", "ss_number", "tax_id", "tin"],
    patterns=[r"^ssn$", r"social.*security", r"^tax.*id$"],
    description="Social Security Number or Tax ID"
))


# -----------------------------------------------------------------------------
# ORGANIZATIONAL CODES
# -----------------------------------------------------------------------------

_register(SemanticType(
    name="company_code",
    category="org",
    aliases=["company_id", "comp_code", "organization_code", "org_code", "legal_entity"],
    patterns=[r"^comp.*code$", r"^org.*code$", r"company.*(?:id|code)"],
    description="Company or legal entity code"
))

_register(SemanticType(
    name="department_code",
    category="org",
    aliases=["dept_code", "dept_id", "department_id", "cost_center", "org_unit"],
    patterns=[r"^dept.*(?:code|id)$", r"department", r"cost.*center"],
    description="Department or cost center code"
))

_register(SemanticType(
    name="job_code",
    category="org",
    aliases=["job_id", "position_code", "position_id", "job_title_code"],
    patterns=[r"^job.*(?:code|id)$", r"position.*(?:code|id)"],
    description="Job or position code"
))

_register(SemanticType(
    name="location_code",
    category="org",
    aliases=["loc_code", "work_location", "site_code", "facility_code"],
    patterns=[r"^loc.*(?:code|id)$", r"location", r"work.*site"],
    description="Work location code"
))

_register(SemanticType(
    name="pay_group_code",
    category="org",
    aliases=["pay_group", "paygroup", "pay_group_id"],
    patterns=[r"pay.*group", r"^pg.*code$"],
    description="Pay group identifier"
))

_register(SemanticType(
    name="org_level_code",
    category="org",
    aliases=["org_level", "organization_level", "hierarchy_level"],
    patterns=[r"org.*level", r"hierarchy"],
    description="Organization hierarchy level code"
))


# -----------------------------------------------------------------------------
# PAY & COMPENSATION
# -----------------------------------------------------------------------------

_register(SemanticType(
    name="earning_code",
    category="pay",
    aliases=["earnings_code", "earn_code", "pay_code", "earning_type"],
    patterns=[r"^earn.*(?:code|type)$", r"pay.*code"],
    description="Earning type code (REG, OT, BON, etc.)"
))

_register(SemanticType(
    name="deduction_code",
    category="pay",
    aliases=["deductionbenefit_code", "ded_code", "benefit_code", "deduction_type"],
    patterns=[r"^ded.*(?:code|type)$", r"benefit.*code", r"deduction"],
    description="Deduction or benefit code"
))

_register(SemanticType(
    name="amount",
    category="pay",
    aliases=["pay_amount", "dollar_amount", "value", "total"],
    patterns=[r".*amount$", r".*total$", r"^pay$"],
    description="Monetary amount"
))

_register(SemanticType(
    name="rate",
    category="pay",
    aliases=["pay_rate", "hourly_rate", "salary_rate", "wage_rate"],
    patterns=[r".*rate$", r"hourly", r"salary"],
    description="Pay rate (hourly, salary, etc.)"
))

_register(SemanticType(
    name="fica_wages",
    category="pay",
    aliases=["ss_wages", "social_security_wages", "oasdi_wages", "taxable_wages_ss"],
    patterns=[r"fica", r"social.*security.*wage", r"ss.*wage", r"oasdi"],
    derives=["ytd_fica_wages"],
    description="FICA/Social Security taxable wages"
))

_register(SemanticType(
    name="gross_wages",
    category="pay",
    aliases=["gross_pay", "gross_earnings", "total_wages", "total_pay"],
    patterns=[r"gross.*(?:wage|pay|earn)", r"total.*(?:wage|pay)"],
    description="Gross wages/pay"
))

_register(SemanticType(
    name="hours",
    category="pay",
    aliases=["hours_worked", "work_hours", "total_hours"],
    patterns=[r".*hours$", r"hrs"],
    description="Hours worked"
))


# -----------------------------------------------------------------------------
# DATES - These can derive calculated fields
# -----------------------------------------------------------------------------

_register(SemanticType(
    name="birth_date",
    category="date",
    aliases=["dob", "date_of_birth", "birthdate", "birth_dt"],
    patterns=[r"birth", r"^dob$", r"date.*birth"],
    derives=["age"],
    derivation_sql={
        "age": "DATE_DIFF('year', {column}, CURRENT_DATE)"
    },
    description="Employee date of birth"
))

_register(SemanticType(
    name="hire_date",
    category="date",
    aliases=["start_date", "employment_date", "date_hired", "original_hire_date"],
    patterns=[r"hire.*date", r"start.*date", r"employment.*date"],
    derives=["tenure", "years_of_service"],
    derivation_sql={
        "tenure": "DATE_DIFF('year', {column}, CURRENT_DATE)",
        "years_of_service": "DATE_DIFF('year', {column}, CURRENT_DATE)"
    },
    description="Employment start date"
))

_register(SemanticType(
    name="termination_date",
    category="date",
    aliases=["term_date", "end_date", "separation_date", "last_day"],
    patterns=[r"term.*date", r"separation", r"end.*date"],
    description="Employment end date"
))

_register(SemanticType(
    name="effective_date",
    category="date",
    aliases=["eff_date", "effective_dt", "as_of_date"],
    patterns=[r"effective", r"eff.*date", r"as.*of"],
    description="Effective date for a change or record"
))


# -----------------------------------------------------------------------------
# STATUS FIELDS
# -----------------------------------------------------------------------------

_register(SemanticType(
    name="employment_status_code",
    category="status",
    aliases=["emp_status", "status_code", "employee_status", "active_status"],
    patterns=[r"emp.*status", r"status.*code", r"active"],
    description="Employment status (Active, Terminated, Leave, etc.)"
))

_register(SemanticType(
    name="tax_code",
    category="status",
    aliases=["tax_jurisdiction", "tax_type", "withholding_code"],
    patterns=[r"tax.*(?:code|type|jurisdiction)", r"withholding"],
    description="Tax jurisdiction or type code"
))


# -----------------------------------------------------------------------------
# CHANGE REASON CODES - For configuration/reference tables
# -----------------------------------------------------------------------------

_register(SemanticType(
    name="termination_reason_code",
    category="change_reasons",
    aliases=["term_reason_code", "separation_reason", "term_code", "termination_code"],
    patterns=[r"term.*reason", r"separation.*reason", r"termination.*code"],
    description="Termination/separation reason code"
))

_register(SemanticType(
    name="benefit_change_reason_code",
    category="change_reasons",
    aliases=["benefit_reason_code", "ben_change_reason", "benefit_event_code"],
    patterns=[r"benefit.*reason", r"ben.*change.*reason"],
    description="Benefit change reason code (life events, etc.)"
))

_register(SemanticType(
    name="job_change_reason_code",
    category="change_reasons",
    aliases=["position_change_reason", "job_reason_code", "transfer_reason"],
    patterns=[r"job.*change.*reason", r"position.*change", r"transfer.*reason"],
    description="Job/position change reason code"
))

_register(SemanticType(
    name="loa_reason_code",
    category="change_reasons",
    aliases=["leave_reason_code", "absence_reason", "loa_code", "leave_type"],
    patterns=[r"loa.*reason", r"leave.*reason", r"absence.*reason"],
    description="Leave of absence reason code"
))


# -----------------------------------------------------------------------------
# DERIVED/CALCULATED FIELDS (not stored, calculated from source)
# -----------------------------------------------------------------------------

_register(SemanticType(
    name="age",
    category="derived",
    aliases=["employee_age", "participant_age", "current_age"],
    patterns=[r"^age$", r".*age$"],
    description="Age in years (derived from birth_date)"
))

_register(SemanticType(
    name="tenure",
    category="derived",
    aliases=["years_of_service", "service_years", "employment_length", "yos"],
    patterns=[r"tenure", r"years.*service", r"^yos$"],
    description="Years of service (derived from hire_date)"
))


# =============================================================================
# VOCABULARY ACCESS FUNCTIONS
# =============================================================================

def get_all_types() -> List[SemanticType]:
    """Get all semantic types."""
    return list(SEMANTIC_TYPES.values())


def get_type(name: str) -> Optional[SemanticType]:
    """Get a semantic type by name."""
    return SEMANTIC_TYPES.get(name)


def get_types_by_category(category: str) -> List[SemanticType]:
    """Get all semantic types in a category."""
    return [st for st in SEMANTIC_TYPES.values() if st.category == category]


def find_semantic_type(text: str) -> Optional[Tuple[SemanticType, float]]:
    """
    Find the best matching semantic type for text.
    Returns (SemanticType, confidence) or None.
    """
    best_match = None
    best_confidence = 0.0
    
    for st in SEMANTIC_TYPES.values():
        matches, confidence = st.matches(text)
        if matches and confidence > best_confidence:
            best_match = st
            best_confidence = confidence
    
    if best_match:
        return best_match, best_confidence
    return None


def get_derivation_source(derived_field: str) -> Optional[Tuple[SemanticType, str]]:
    """
    Find which semantic type can derive a given field.
    Returns (source_type, sql_expression) or None.
    
    Example: get_derivation_source("age") -> (birth_date_type, "DATE_DIFF('year', {column}, CURRENT_DATE)")
    """
    for st in SEMANTIC_TYPES.values():
        if derived_field in st.derives:
            sql = st.derivation_sql.get(derived_field, "")
            return st, sql
    return None


def get_type_names_for_prompt() -> str:
    """
    Generate a formatted list of semantic types for LLM prompts.
    Used by structured_data_handler.py and standards_processor.py.
    """
    lines = []
    
    # Group by category
    categories = {}
    for st in SEMANTIC_TYPES.values():
        if st.category not in categories:
            categories[st.category] = []
        categories[st.category].append(st)
    
    category_names = {
        "employee": "EMPLOYEE IDENTIFIERS",
        "org": "ORGANIZATIONAL CODES", 
        "pay": "PAY & COMPENSATION",
        "date": "DATES",
        "status": "STATUS FIELDS",
        "change_reasons": "CHANGE REASON CODES",
        "derived": "DERIVED/CALCULATED FIELDS"
    }
    
    for cat_key in ["employee", "org", "pay", "date", "status", "change_reasons", "derived"]:
        if cat_key in categories:
            lines.append(f"\n{category_names.get(cat_key, cat_key.upper())}:")
            for st in categories[cat_key]:
                aliases_str = f" (aliases: {', '.join(st.aliases[:3])})" if st.aliases else ""
                lines.append(f"- {st.name}: {st.description}{aliases_str}")
    
    lines.append("\n- NONE: Does not match any semantic type")
    
    return "\n".join(lines)


def get_all_type_names() -> Set[str]:
    """Get all semantic type names including aliases."""
    names = set()
    for st in SEMANTIC_TYPES.values():
        names.add(st.name)
        names.update(st.aliases)
    return names


def normalize_to_canonical(field_name: str) -> Optional[str]:
    """
    Normalize a field name to its canonical semantic type.
    
    Example: "dob" -> "birth_date", "emp_id" -> "employee_number"
    """
    result = find_semantic_type(field_name)
    if result:
        return result[0].name
    return None


# =============================================================================
# FIELD MATCHING FOR COMPLIANCE
# =============================================================================

def match_rule_field_to_column(rule_field: str, column_semantic_type: str) -> Tuple[bool, float, Optional[str]]:
    """
    Check if a rule field matches a column's semantic type.
    
    Returns (matches, confidence, derivation_sql_or_None)
    
    Example:
        match_rule_field_to_column("age", "birth_date") 
        -> (True, 0.9, "DATE_DIFF('year', {column}, CURRENT_DATE)")
    """
    # Normalize rule field to canonical type
    rule_result = find_semantic_type(rule_field)
    if not rule_result:
        return False, 0.0, None
    
    rule_type, rule_conf = rule_result
    
    # Direct match
    if rule_type.name == column_semantic_type:
        return True, 0.95, None
    
    # Check if column can derive the rule field
    col_type = get_type(column_semantic_type)
    if col_type and rule_type.name in col_type.derives:
        sql = col_type.derivation_sql.get(rule_type.name, "")
        return True, 0.90, sql
    
    # Check if rule field is derived and column is its source
    derivation = get_derivation_source(rule_type.name)
    if derivation:
        source_type, sql = derivation
        if source_type.name == column_semantic_type:
            return True, 0.90, sql
    
    return False, 0.0, None
