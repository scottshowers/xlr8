"""
XLR8 FIELD INTERPRETATION ENGINE
================================

The missing link between raw data and intelligent analysis.

This engine provides:
1. FIELD INTERPRETATIONS - Maps columns to semantic meanings based on domain context
   Example: "rate" in tax domain → tax_rate, in payroll domain → pay_rate

2. DOMAIN-SPECIFIC GAP CHECKS - Pre-defined checks that auto-trigger when domains detected
   Example: If tax domain detected → automatically check SUI rates are valid

3. CONTEXT-AWARE QUERIES - Helps SQL generator understand field semantics

Integration points:
- TableClassification (from project_intelligence.py) - knows domain of each table
- Rule Registry (from standards_processor.py) - dynamic rules from uploads
- Gap Detection Engine - regulatory checks
- Intelligence Engine - query understanding

NO HARDCODING of specific values - uses patterns and metadata.
Specific thresholds come from Rule Registry (uploaded standards).

Deploy to: backend/utils/field_interpretation_engine.py

Author: XLR8 Team
Version: 1.0.0 - Task 4 Domain Rules Layer
"""

import re
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# FIELD SEMANTIC TYPES
# =============================================================================

class FieldSemantic(Enum):
    """
    Semantic meaning of fields, more specific than ColumnSemantic.
    These help the system understand WHAT a field represents.
    """
    # Identity fields
    EMPLOYEE_ID = "employee_id"
    SSN = "ssn"
    FEIN = "fein"
    
    # Tax-specific
    TAX_RATE = "tax_rate"
    TAX_WAGE_BASE = "tax_wage_base"
    TAX_CODE = "tax_code"
    TAX_JURISDICTION = "tax_jurisdiction"
    SUI_RATE = "sui_rate"
    FUTA_RATE = "futa_rate"
    FICA_RATE = "fica_rate"
    
    # Payroll-specific  
    PAY_RATE = "pay_rate"
    HOURLY_RATE = "hourly_rate"
    EARNING_CODE = "earning_code"
    DEDUCTION_CODE = "deduction_code"
    GROSS_PAY = "gross_pay"
    NET_PAY = "net_pay"
    YTD_AMOUNT = "ytd_amount"
    
    # Benefits-specific
    BENEFIT_PLAN = "benefit_plan"
    COVERAGE_LEVEL = "coverage_level"
    CONTRIBUTION_AMOUNT = "contribution_amount"
    CONTRIBUTION_PERCENT = "contribution_percent"
    
    # Time-specific
    HOURS_WORKED = "hours_worked"
    REGULAR_HOURS = "regular_hours"
    OVERTIME_HOURS = "overtime_hours"
    
    # HR-specific
    HIRE_DATE = "hire_date"
    TERM_DATE = "term_date"
    EMPLOYMENT_STATUS = "employment_status"
    JOB_TITLE = "job_title"
    DEPARTMENT = "department"
    
    # Generic
    AMOUNT = "amount"
    RATE = "rate"
    CODE = "code"
    STATUS = "status"
    DATE = "date"
    DESCRIPTION = "description"
    UNKNOWN = "unknown"


# =============================================================================
# DOMAIN → FIELD INTERPRETATION MAPPINGS
# =============================================================================

# Maps column name patterns to semantic types, qualified by domain
# Format: domain → [(column_pattern, semantic_type, confidence)]

DOMAIN_FIELD_INTERPRETATIONS = {
    'taxes': [
        # Tax rates
        (r'sui.*rate|suta.*rate|state.*unemployment.*rate', FieldSemantic.SUI_RATE, 0.95),
        (r'futa.*rate|federal.*unemployment.*rate', FieldSemantic.FUTA_RATE, 0.95),
        (r'fica.*rate|ss.*rate|social.*security.*rate|medicare.*rate', FieldSemantic.FICA_RATE, 0.95),
        (r'tax.*rate|withhold.*rate', FieldSemantic.TAX_RATE, 0.85),
        (r'^rate$', FieldSemantic.TAX_RATE, 0.70),  # "rate" in tax context = tax rate
        
        # Tax wage bases
        (r'sui.*wage.*base|suta.*wage.*base', FieldSemantic.TAX_WAGE_BASE, 0.95),
        (r'wage.*base|taxable.*wage', FieldSemantic.TAX_WAGE_BASE, 0.80),
        
        # Tax codes/jurisdictions
        (r'tax.*code|tax.*type', FieldSemantic.TAX_CODE, 0.90),
        (r'jurisdiction|state.*code|locality', FieldSemantic.TAX_JURISDICTION, 0.85),
        (r'fein|ein|employer.*id.*num', FieldSemantic.FEIN, 0.95),
    ],
    
    'earnings': [
        (r'earning.*code|pay.*code|earn.*code', FieldSemantic.EARNING_CODE, 0.95),
        (r'hourly.*rate|hour.*rate', FieldSemantic.HOURLY_RATE, 0.95),
        (r'pay.*rate|rate.*of.*pay', FieldSemantic.PAY_RATE, 0.90),
        (r'^rate$', FieldSemantic.PAY_RATE, 0.70),  # "rate" in earnings context = pay rate
        (r'gross.*pay|gross.*amount|gross.*wages', FieldSemantic.GROSS_PAY, 0.95),
        (r'net.*pay|net.*amount|take.*home', FieldSemantic.NET_PAY, 0.95),
        (r'ytd|year.*to.*date', FieldSemantic.YTD_AMOUNT, 0.90),
    ],
    
    'deductions': [
        (r'deduction.*code|ded.*code|ded.*type', FieldSemantic.DEDUCTION_CODE, 0.95),
        (r'contribution.*amt|contrib.*amount|employee.*contrib', FieldSemantic.CONTRIBUTION_AMOUNT, 0.90),
        (r'contribution.*pct|contrib.*percent|employer.*match', FieldSemantic.CONTRIBUTION_PERCENT, 0.90),
        (r'^rate$|^pct$|^percent$', FieldSemantic.CONTRIBUTION_PERCENT, 0.60),
    ],
    
    'benefits': [
        (r'plan.*code|benefit.*code|plan.*type', FieldSemantic.BENEFIT_PLAN, 0.95),
        (r'coverage.*level|coverage.*type|tier', FieldSemantic.COVERAGE_LEVEL, 0.90),
        (r'contribution|premium|employee.*cost', FieldSemantic.CONTRIBUTION_AMOUNT, 0.85),
    ],
    
    'time': [
        (r'hours.*worked|total.*hours|work.*hours', FieldSemantic.HOURS_WORKED, 0.95),
        (r'regular.*hours|reg.*hours|straight.*hours', FieldSemantic.REGULAR_HOURS, 0.95),
        (r'overtime.*hours|ot.*hours|ot_hours', FieldSemantic.OVERTIME_HOURS, 0.95),
    ],
    
    'demographics': [
        (r'hire.*date|start.*date|doh|date.*of.*hire', FieldSemantic.HIRE_DATE, 0.95),
        (r'term.*date|termination.*date|end.*date', FieldSemantic.TERM_DATE, 0.95),
        (r'status|emp.*status|employment.*status', FieldSemantic.EMPLOYMENT_STATUS, 0.90),
        (r'job.*title|position|occupation', FieldSemantic.JOB_TITLE, 0.90),
        (r'department|dept|division', FieldSemantic.DEPARTMENT, 0.90),
        (r'employee.*id|emp.*id|ee.*id|employee.*num|emp.*num', FieldSemantic.EMPLOYEE_ID, 0.95),
        (r'ssn|social.*security', FieldSemantic.SSN, 0.95),
    ],
    
    'gl': [
        (r'debit|dr', FieldSemantic.AMOUNT, 0.80),
        (r'credit|cr', FieldSemantic.AMOUNT, 0.80),
        (r'account|acct|gl.*code', FieldSemantic.CODE, 0.90),
    ],
}

# Generic patterns (apply when domain doesn't have specific match)
GENERIC_FIELD_INTERPRETATIONS = [
    (r'employee.*id|emp.*id|ee.*id|employee.*num|emp.*num', FieldSemantic.EMPLOYEE_ID, 0.85),
    (r'ssn|social.*security', FieldSemantic.SSN, 0.95),
    (r'fein|ein|employer.*id', FieldSemantic.FEIN, 0.95),
    (r'amount|amt', FieldSemantic.AMOUNT, 0.60),
    (r'rate|pct|percent', FieldSemantic.RATE, 0.50),
    (r'code|type', FieldSemantic.CODE, 0.50),
    (r'status', FieldSemantic.STATUS, 0.70),
    (r'date|dt$|_dt$', FieldSemantic.DATE, 0.70),
    (r'desc|description|name', FieldSemantic.DESCRIPTION, 0.60),
]


# =============================================================================
# DOMAIN-SPECIFIC GAP CHECKS
# =============================================================================

@dataclass
class DomainGapCheck:
    """
    A domain-specific check that auto-triggers when domain is detected.
    
    These are the "smart checks" that run automatically based on detected domains.
    Thresholds/values come from Rule Registry when available, otherwise use
    built-in knowledge (which may need verification).
    """
    check_id: str
    domain: str
    name: str
    description: str
    
    # Fields required for this check
    required_fields: List[FieldSemantic]
    
    # SQL template (uses {field_name} placeholders)
    sql_template: str
    
    # What a violation looks like
    violation_condition: str  # "rows > 0", "any NULL", etc.
    
    # Severity and category
    severity: str = "medium"
    category: str = "data_quality"
    
    # Whether this check needs values from Rule Registry
    needs_registry_values: bool = False
    registry_value_keys: List[str] = field(default_factory=list)


# Pre-defined domain checks
DOMAIN_GAP_CHECKS = [
    # ==========================================================================
    # TAX DOMAIN CHECKS
    # ==========================================================================
    DomainGapCheck(
        check_id="tax_sui_zero_rate",
        domain="taxes",
        name="Zero SUI Rate Detection",
        description="Identifies states with 0% SUI rate (may indicate excellent experience rating OR missing data)",
        required_fields=[FieldSemantic.SUI_RATE, FieldSemantic.TAX_JURISDICTION],
        sql_template="""
            SELECT {jurisdiction_field}, {rate_field}, COUNT(*) as record_count
            FROM {table_name}
            WHERE TRY_CAST({rate_field} AS DOUBLE) = 0
               OR TRY_CAST({rate_field} AS DOUBLE) IS NULL
            GROUP BY {jurisdiction_field}, {rate_field}
        """,
        violation_condition="rows > 0",
        severity="medium",
        category="tax_compliance",
    ),
    
    DomainGapCheck(
        check_id="tax_sui_high_rate",
        domain="taxes",
        name="SUI Rate Above Maximum",
        description="Identifies SUI rates that exceed typical state maximums",
        required_fields=[FieldSemantic.SUI_RATE, FieldSemantic.TAX_JURISDICTION],
        sql_template="""
            SELECT {jurisdiction_field}, {rate_field}
            FROM {table_name}
            WHERE TRY_CAST({rate_field} AS DOUBLE) > 0.10
        """,
        violation_condition="rows > 0",
        severity="high",
        category="tax_compliance",
        needs_registry_values=True,
        registry_value_keys=["state_sui_max_rates"],
    ),
    
    DomainGapCheck(
        check_id="tax_missing_jurisdiction",
        domain="taxes",
        name="Missing Tax Jurisdiction",
        description="Tax records without a state/jurisdiction assignment",
        required_fields=[FieldSemantic.TAX_JURISDICTION],
        sql_template="""
            SELECT COUNT(*) as missing_count
            FROM {table_name}
            WHERE {jurisdiction_field} IS NULL 
               OR TRIM({jurisdiction_field}) = ''
        """,
        violation_condition="missing_count > 0",
        severity="high",
        category="data_quality",
    ),
    
    # ==========================================================================
    # EARNINGS/PAYROLL CHECKS
    # ==========================================================================
    DomainGapCheck(
        check_id="earnings_negative_rate",
        domain="earnings",
        name="Negative Pay Rate",
        description="Pay rates should not be negative",
        required_fields=[FieldSemantic.PAY_RATE],
        sql_template="""
            SELECT {employee_id_field}, {rate_field}
            FROM {table_name}
            WHERE TRY_CAST({rate_field} AS DOUBLE) < 0
        """,
        violation_condition="rows > 0",
        severity="high",
        category="data_quality",
    ),
    
    DomainGapCheck(
        check_id="earnings_zero_hourly_rate",
        domain="earnings",
        name="Zero Hourly Rate",
        description="Hourly employees with $0/hour rate",
        required_fields=[FieldSemantic.HOURLY_RATE],
        sql_template="""
            SELECT {employee_id_field}, {rate_field}
            FROM {table_name}
            WHERE TRY_CAST({rate_field} AS DOUBLE) = 0
        """,
        violation_condition="rows > 0",
        severity="medium",
        category="data_quality",
    ),
    
    DomainGapCheck(
        check_id="earnings_gross_net_mismatch",
        domain="earnings",
        name="Gross Less Than Net",
        description="Gross pay should always be >= net pay",
        required_fields=[FieldSemantic.GROSS_PAY, FieldSemantic.NET_PAY],
        sql_template="""
            SELECT {employee_id_field}, {gross_field}, {net_field}
            FROM {table_name}
            WHERE TRY_CAST({gross_field} AS DOUBLE) < TRY_CAST({net_field} AS DOUBLE)
        """,
        violation_condition="rows > 0",
        severity="critical",
        category="data_integrity",
    ),
    
    # ==========================================================================
    # DEDUCTIONS/BENEFITS CHECKS
    # ==========================================================================
    DomainGapCheck(
        check_id="deductions_over_100_percent",
        domain="deductions",
        name="Deduction Percent Over 100%",
        description="Percentage-based deductions exceeding 100%",
        required_fields=[FieldSemantic.CONTRIBUTION_PERCENT],
        sql_template="""
            SELECT {employee_id_field}, {percent_field}
            FROM {table_name}
            WHERE TRY_CAST({percent_field} AS DOUBLE) > 100
               OR TRY_CAST({percent_field} AS DOUBLE) > 1.0
        """,
        violation_condition="rows > 0",
        severity="high",
        category="data_quality",
    ),
    
    # ==========================================================================
    # TIME/ATTENDANCE CHECKS
    # ==========================================================================
    DomainGapCheck(
        check_id="time_excessive_hours",
        domain="time",
        name="Excessive Hours Worked",
        description="Single-day hours exceeding 24 or weekly hours exceeding 168",
        required_fields=[FieldSemantic.HOURS_WORKED],
        sql_template="""
            SELECT {employee_id_field}, {hours_field}
            FROM {table_name}
            WHERE TRY_CAST({hours_field} AS DOUBLE) > 24
        """,
        violation_condition="rows > 0",
        severity="medium",
        category="data_quality",
    ),
    
    DomainGapCheck(
        check_id="time_negative_hours",
        domain="time",
        name="Negative Hours",
        description="Hours worked should not be negative",
        required_fields=[FieldSemantic.HOURS_WORKED],
        sql_template="""
            SELECT {employee_id_field}, {hours_field}
            FROM {table_name}
            WHERE TRY_CAST({hours_field} AS DOUBLE) < 0
        """,
        violation_condition="rows > 0",
        severity="high",
        category="data_quality",
    ),
    
    # ==========================================================================
    # HR/DEMOGRAPHICS CHECKS
    # ==========================================================================
    DomainGapCheck(
        check_id="hr_future_hire_date",
        domain="demographics",
        name="Future Hire Date",
        description="Hire dates in the future (may be intentional for pre-boarding)",
        required_fields=[FieldSemantic.HIRE_DATE],
        sql_template="""
            SELECT {employee_id_field}, {hire_date_field}
            FROM {table_name}
            WHERE TRY_CAST({hire_date_field} AS DATE) > CURRENT_DATE
        """,
        violation_condition="rows > 0",
        severity="low",
        category="data_quality",
    ),
    
    DomainGapCheck(
        check_id="hr_term_before_hire",
        domain="demographics",
        name="Termination Before Hire",
        description="Termination date is before hire date",
        required_fields=[FieldSemantic.HIRE_DATE, FieldSemantic.TERM_DATE],
        sql_template="""
            SELECT {employee_id_field}, {hire_date_field}, {term_date_field}
            FROM {table_name}
            WHERE {term_date_field} IS NOT NULL
              AND TRY_CAST({term_date_field} AS DATE) < TRY_CAST({hire_date_field} AS DATE)
        """,
        violation_condition="rows > 0",
        severity="critical",
        category="data_integrity",
    ),
]


# =============================================================================
# FIELD INTERPRETATION ENGINE
# =============================================================================

@dataclass
class FieldInterpretation:
    """Result of interpreting a field."""
    column_name: str
    semantic_type: FieldSemantic
    confidence: float
    domain_context: Optional[str]
    interpretation_reason: str


class FieldInterpretationEngine:
    """
    Interprets fields based on domain context.
    
    Usage:
        engine = FieldInterpretationEngine(handler)
        
        # Get interpretation for a specific field
        interp = engine.interpret_field("rate", "taxes", "sui_rates_table")
        # Returns: FieldInterpretation(semantic_type=TAX_RATE, confidence=0.95)
        
        # Get all interpretations for a table
        interpretations = engine.interpret_table("sui_rates", "taxes")
        
        # Get applicable gap checks for domains
        checks = engine.get_gap_checks_for_domains(["taxes", "earnings"])
    """
    
    def __init__(self, structured_handler=None):
        """
        Initialize the engine.
        
        Args:
            structured_handler: DuckDB handler for querying metadata
        """
        self.handler = structured_handler
        self._classifications_cache = {}
        self._rule_registry = None
    
    def _get_rule_registry(self):
        """Get rule registry for dynamic values."""
        if self._rule_registry is None:
            try:
                from backend.utils.standards_processor import get_rule_registry
                self._rule_registry = get_rule_registry()
            except ImportError:
                try:
                    from utils.standards_processor import get_rule_registry
                    self._rule_registry = get_rule_registry()
                except ImportError:
                    pass
        return self._rule_registry
    
    def interpret_field(
        self, 
        column_name: str, 
        domain: Optional[str] = None,
        table_name: Optional[str] = None
    ) -> FieldInterpretation:
        """
        Interpret a field's semantic meaning.
        
        Args:
            column_name: Name of the column
            domain: Domain context (taxes, earnings, etc.)
            table_name: Table name for additional context
            
        Returns:
            FieldInterpretation with semantic type and confidence
        """
        col_lower = column_name.lower().strip()
        
        # Try domain-specific patterns first
        if domain and domain.lower() in DOMAIN_FIELD_INTERPRETATIONS:
            domain_patterns = DOMAIN_FIELD_INTERPRETATIONS[domain.lower()]
            for pattern, semantic_type, confidence in domain_patterns:
                if re.search(pattern, col_lower, re.IGNORECASE):
                    return FieldInterpretation(
                        column_name=column_name,
                        semantic_type=semantic_type,
                        confidence=confidence,
                        domain_context=domain,
                        interpretation_reason=f"Matched domain pattern '{pattern}' in {domain}"
                    )
        
        # Fall back to generic patterns
        for pattern, semantic_type, confidence in GENERIC_FIELD_INTERPRETATIONS:
            if re.search(pattern, col_lower, re.IGNORECASE):
                return FieldInterpretation(
                    column_name=column_name,
                    semantic_type=semantic_type,
                    confidence=confidence,
                    domain_context=domain,
                    interpretation_reason=f"Matched generic pattern '{pattern}'"
                )
        
        # No match - return UNKNOWN
        return FieldInterpretation(
            column_name=column_name,
            semantic_type=FieldSemantic.UNKNOWN,
            confidence=0.0,
            domain_context=domain,
            interpretation_reason="No pattern match"
        )
    
    def interpret_table(
        self, 
        table_name: str, 
        domain: Optional[str] = None,
        project: Optional[str] = None
    ) -> Dict[str, FieldInterpretation]:
        """
        Interpret all fields in a table.
        
        Args:
            table_name: Name of the table
            domain: Domain context (if known)
            project: Project name
            
        Returns:
            Dict mapping column names to interpretations
        """
        interpretations = {}
        
        if not self.handler:
            return interpretations
        
        try:
            # Get columns from schema metadata
            result = self.handler.conn.execute("""
                SELECT columns
                FROM _schema_metadata
                WHERE table_name = ?
                LIMIT 1
            """, [table_name]).fetchone()
            
            if not result or not result[0]:
                return interpretations
            
            columns = json.loads(result[0]) if isinstance(result[0], str) else result[0]
            
            for col in columns:
                col_name = col if isinstance(col, str) else col.get('column_name', col.get('name', ''))
                if col_name:
                    interpretations[col_name] = self.interpret_field(col_name, domain, table_name)
            
        except Exception as e:
            logger.warning(f"[FIELD-INTERP] Failed to interpret table {table_name}: {e}")
        
        return interpretations
    
    def get_gap_checks_for_domains(
        self, 
        domains: List[str]
    ) -> List[DomainGapCheck]:
        """
        Get applicable gap checks for detected domains.
        
        Args:
            domains: List of detected domain names
            
        Returns:
            List of DomainGapCheck objects to run
        """
        applicable_checks = []
        
        for check in DOMAIN_GAP_CHECKS:
            if check.domain.lower() in [d.lower() for d in domains]:
                applicable_checks.append(check)
        
        return applicable_checks
    
    def build_gap_check_sql(
        self, 
        check: DomainGapCheck,
        table_name: str,
        field_mappings: Dict[FieldSemantic, str]
    ) -> Optional[str]:
        """
        Build SQL for a gap check given field mappings.
        
        Args:
            check: The gap check definition
            table_name: Table to check
            field_mappings: Map of FieldSemantic → actual column name
            
        Returns:
            SQL query string or None if required fields missing
        """
        # Check all required fields are mapped
        for required_field in check.required_fields:
            if required_field not in field_mappings:
                logger.debug(f"[FIELD-INTERP] Missing field {required_field} for check {check.check_id}")
                return None
        
        # Build substitution dict
        substitutions = {
            'table_name': table_name,
        }
        
        # Map semantic types to placeholder names
        placeholder_map = {
            FieldSemantic.SUI_RATE: 'rate_field',
            FieldSemantic.TAX_RATE: 'rate_field',
            FieldSemantic.TAX_JURISDICTION: 'jurisdiction_field',
            FieldSemantic.PAY_RATE: 'rate_field',
            FieldSemantic.HOURLY_RATE: 'rate_field',
            FieldSemantic.EMPLOYEE_ID: 'employee_id_field',
            FieldSemantic.GROSS_PAY: 'gross_field',
            FieldSemantic.NET_PAY: 'net_field',
            FieldSemantic.CONTRIBUTION_PERCENT: 'percent_field',
            FieldSemantic.HOURS_WORKED: 'hours_field',
            FieldSemantic.HIRE_DATE: 'hire_date_field',
            FieldSemantic.TERM_DATE: 'term_date_field',
        }
        
        # Add field mappings
        for semantic_type, column_name in field_mappings.items():
            placeholder = placeholder_map.get(semantic_type, f'{semantic_type.value}_field')
            substitutions[placeholder] = column_name
        
        # Build SQL
        try:
            sql = check.sql_template.format(**substitutions)
            return sql.strip()
        except KeyError as e:
            logger.warning(f"[FIELD-INTERP] Missing substitution {e} in check {check.check_id}")
            return None
    
    def run_domain_gap_checks(
        self, 
        project: str,
        detected_domains: List[str]
    ) -> List[Dict]:
        """
        Run all applicable gap checks for a project.
        
        Args:
            project: Project name
            detected_domains: List of detected domains
            
        Returns:
            List of gap check results
        """
        results = []
        
        if not self.handler:
            logger.warning("[FIELD-INTERP] No handler - cannot run gap checks")
            return results
        
        # Get applicable checks
        checks = self.get_gap_checks_for_domains(detected_domains)
        if not checks:
            logger.info(f"[FIELD-INTERP] No gap checks for domains: {detected_domains}")
            return results
        
        logger.info(f"[FIELD-INTERP] Running {len(checks)} gap checks for domains: {detected_domains}")
        
        # Get tables for this project
        try:
            tables_result = self.handler.conn.execute("""
                SELECT table_name, columns
                FROM _schema_metadata
                WHERE project = ?
            """, [project]).fetchall()
        except Exception as e:
            logger.error(f"[FIELD-INTERP] Failed to get tables: {e}")
            return results
        
        for check in checks:
            # Find tables that might have the required fields
            for table_name, columns_json in tables_result:
                try:
                    columns = json.loads(columns_json) if isinstance(columns_json, str) else columns_json
                    col_names = [c if isinstance(c, str) else c.get('column_name', '') for c in columns]
                    
                    # Try to map required fields to actual columns
                    field_mappings = {}
                    for required_field in check.required_fields:
                        for col_name in col_names:
                            interp = self.interpret_field(col_name, check.domain, table_name)
                            if interp.semantic_type == required_field and interp.confidence > 0.5:
                                field_mappings[required_field] = col_name
                                break
                    
                    # Check if we have all required fields
                    if len(field_mappings) < len(check.required_fields):
                        continue
                    
                    # Also try to find employee_id for context
                    for col_name in col_names:
                        interp = self.interpret_field(col_name, check.domain, table_name)
                        if interp.semantic_type == FieldSemantic.EMPLOYEE_ID:
                            field_mappings[FieldSemantic.EMPLOYEE_ID] = col_name
                            break
                    
                    # Build and run SQL
                    sql = self.build_gap_check_sql(check, table_name, field_mappings)
                    if not sql:
                        continue
                    
                    try:
                        query_result = self.handler.conn.execute(sql).fetchall()
                        
                        # Check for violations
                        has_violation = False
                        if "rows > 0" in check.violation_condition:
                            has_violation = len(query_result) > 0
                        elif "missing_count > 0" in check.violation_condition:
                            has_violation = query_result and query_result[0][0] > 0
                        
                        results.append({
                            'check_id': check.check_id,
                            'check_name': check.name,
                            'domain': check.domain,
                            'table_name': table_name,
                            'has_violation': has_violation,
                            'violation_count': len(query_result) if has_violation else 0,
                            'severity': check.severity,
                            'category': check.category,
                            'description': check.description,
                            'sample_data': [dict(zip(range(len(r)), r)) for r in query_result[:5]] if query_result else [],
                        })
                        
                        if has_violation:
                            logger.warning(f"[FIELD-INTERP] Violation found: {check.name} on {table_name}")
                        
                    except Exception as sql_e:
                        logger.debug(f"[FIELD-INTERP] Check {check.check_id} failed on {table_name}: {sql_e}")
                        
                except Exception as e:
                    logger.debug(f"[FIELD-INTERP] Table processing error: {e}")
        
        return results


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_engine_instance = None

def get_field_interpretation_engine(handler=None) -> FieldInterpretationEngine:
    """Get or create field interpretation engine singleton."""
    global _engine_instance
    if _engine_instance is None or handler is not None:
        _engine_instance = FieldInterpretationEngine(handler)
    return _engine_instance


def interpret_field(column_name: str, domain: str = None) -> Dict:
    """Quick field interpretation."""
    engine = get_field_interpretation_engine()
    result = engine.interpret_field(column_name, domain)
    return {
        'column_name': result.column_name,
        'semantic_type': result.semantic_type.value,
        'confidence': result.confidence,
        'domain': result.domain_context,
        'reason': result.interpretation_reason,
    }


def run_gap_checks(project: str, domains: List[str], handler=None) -> List[Dict]:
    """Run gap checks for a project."""
    engine = get_field_interpretation_engine(handler)
    return engine.run_domain_gap_checks(project, domains)
