"""
Functional Area Mapping for Configuration Validation
Maps worksheet names to functional area categories for filtering
"""

FUNCTIONAL_AREA_MAPPING = {
    # Company Setup
    "Master Company Settings": "Company Setup",
    "Company Information": "Company Setup",
    "Establishments": "Company Setup",
    
    # Organization
    "Locations": "Organization",
    "Organization": "Organization",
    "Projects": "Organization",
    
    # Payroll
    "Pay Groups": "Payroll",
    "Payroll Models": "Payroll",
    "Earnings": "Payroll",
    "Earnings Groups": "Payroll",
    "Earnings Info (CAN)": "Payroll",
    "Banks": "Payroll",
    "Banks (CAN)": "Payroll",
    "Distribution Centers": "Payroll",
    
    # Deductions & Benefits
    "Deduction_Benefit Plans": "Deductions & Benefits",
    "Deduction Groups": "Deductions & Benefits",
    "Option Rates": "Deductions & Benefits",
    "Age Graded Rates": "Deductions & Benefits",
    "Benefit Age Reductions": "Deductions & Benefits",
    "PTO": "Deductions & Benefits",
    "ACA Setup": "Deductions & Benefits",
    
    # Compensation
    "Payscale": "Compensation",
    "Salary Grades": "Compensation",
    
    # Tax & Compliance
    "Tax Information": "Tax & Compliance",
    "Tax Groups": "Tax & Compliance",
    "Local Min Wage Jurisdictions": "Tax & Compliance",
    "Workers Compensation": "Tax & Compliance",
    "OSHA": "Tax & Compliance",
    "Unions": "Tax & Compliance",
    
    # Jobs & Workforce
    "Job Family": "Jobs & Workforce",
    "Job Codes": "Jobs & Workforce",
    "Job Groups": "Jobs & Workforce",
    "Employee Types": "Jobs & Workforce",
    
    # Finance/GL
    "General Ledger": "Finance/GL",
    "GL Rules": "Finance/GL",
    
    # System Configuration
    "Expressions": "System Configuration",
    "User Defined Fields": "System Configuration",
    "Relationships": "System Configuration",
    "Change Reasons": "System Configuration",
    "Platform Config Fields": "System Configuration",
}

FUNCTIONAL_AREAS = [
    "All Areas",
    "Company Setup",
    "Organization",
    "Payroll",
    "Deductions & Benefits",
    "Compensation",
    "Tax & Compliance",
    "Jobs & Workforce",
    "Finance/GL",
    "System Configuration"
]


def get_functional_area(sheet_name: str) -> str:
    """
    Get functional area for a given sheet name.
    
    Args:
        sheet_name: Name of the worksheet
        
    Returns:
        Functional area category or 'Uncategorized'
    """
    return FUNCTIONAL_AREA_MAPPING.get(sheet_name, "Uncategorized")


def get_all_functional_areas() -> list:
    """Get list of all functional area categories"""
    return FUNCTIONAL_AREAS.copy()
