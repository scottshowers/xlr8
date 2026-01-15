"""
YEAR-END PLAYBOOK DEFINITION
=============================

Domain-specific configuration for the UKG Year-End Checklist playbook.

This file contains:
- Consultative prompts (expert analysis guidance)
- Dependent action guidance (what to do for each action)
- Action keyword mappings (for intelligence matching)
- Custom export tabs

The framework handles everything else.

Author: XLR8 Team
Version: 1.1.0 - Schema-aware prompts
Date: December 2025
"""

from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# SCHEMA-AWARE PREAMBLE - Prepended to all consultative prompts
# =============================================================================
# This enables domain-agnostic analysis - AI learns the data structure first

SCHEMA_ANALYSIS_PREAMBLE = """
STEP 1 - UNDERSTAND THE DATA STRUCTURE:
Before analyzing, examine the column headers in each data block.
- Identify columns that contain: IDs, rates/percentages, names, codes, dates, amounts, types/categories
- Note the patterns in the data (e.g., state abbreviations, percentage values, tax codes)
- Understand how rows relate to each other (e.g., one row per tax jurisdiction, per employee, per code)

STEP 2 - APPLY DOMAIN EXPERTISE:
Use your knowledge to interpret what each column likely represents.
Then analyze against the requirements below.

STEP 3 - CITE SPECIFIC VALUES:
Always include actual values from the data in your findings.
Example: "Found SUI rate of 2.7% for Texas" not "SUI rates were reviewed"

"""


# =============================================================================
# CONSULTATIVE PROMPTS - Expert analysis guidance per action
# =============================================================================

YEAR_END_CONSULTATIVE_PROMPTS: Dict[str, str] = {
    "2A": SCHEMA_ANALYSIS_PREAMBLE + """
ANALYSIS FOCUS: Company Tax Verification & Master Profile

VALIDATE THESE ELEMENTS:

1. FEDERAL EMPLOYER ID (FEIN):
   - Format should be XX-XXXXXXX (9 digits, hyphen after first 2)
   - Look for columns containing federal IDs or tax identification numbers
   - Flag if missing, malformed, or inconsistent between documents

2. STATE UNEMPLOYMENT (SUI/SUTA) RATES:
   - Look for rate/percentage columns associated with state tax types
   - Normal range: 0.1% to 12% depending on state and employer history
   - New employers often start at higher "new employer" rates
   - Flag rates outside normal ranges or missing for states with activity

3. FEDERAL UNEMPLOYMENT (FUTA) RATE:
   - Standard rate: 6.0% gross (0.6% after state credit)
   - Credit reduction states (if any) will show higher effective rates
   - Flag if rate doesn't match expected values

4. COMPANY INFORMATION:
   - Legal company name should be consistent across documents
   - Address should be complete (street, city, state, ZIP)
   - Note any discrepancies between documents

5. CROSS-DOCUMENT VALIDATION:
   - Compare Tax Verification data against Master Profile
   - Flag any mismatches in company info, tax IDs, or rates
   - Identify any jurisdictions in one document but not the other

Report specific values found. If data for a required check is not present, note what's missing.
""",

    "2C": SCHEMA_ANALYSIS_PREAMBLE + """
ANALYSIS FOCUS: Tax Code Verification

VALIDATE THESE ELEMENTS:

1. STATE TAX REGISTRATIONS:
   - Every state with employees needs a registration
   - State tax IDs have state-specific formats
   - Flag missing registrations for states showing payroll activity

2. TAX RATE CURRENCY:
   - SUI rates change annually - rates should reflect current year
   - Local tax rates vary by jurisdiction
   - Flag any rates that appear outdated or placeholder values

3. MULTI-STATE HANDLING:
   - Check for reciprocity agreement handling
   - Verify resident vs work state tax configurations
   - Flag employees who may need corrections

Focus on actionable issues requiring resolution before year-end.
""",

    "3A": SCHEMA_ANALYSIS_PREAMBLE + """
ANALYSIS FOCUS: Employee Data Validation

VALIDATE THESE ELEMENTS:

1. SOCIAL SECURITY NUMBERS:
   - Format: XXX-XX-XXXX (9 digits with hyphens)
   - Invalid patterns: 000-XX-XXXX, XXX-00-XXXX, XXX-XX-0000
   - ITINs (9XX-XX-XXXX) may need special handling
   - Flag any invalid or missing SSNs

2. EMPLOYEE NAMES:
   - Must match SSA records exactly for W-2 filing
   - Flag: special characters, extra spaces, Jr/Sr/III formatting issues
   - Check for legal name vs preferred name confusion

3. ADDRESSES:
   - Complete address required for W-2 delivery
   - Flag incomplete addresses or PO Boxes where problematic
   - Identify any obviously invalid addresses

4. DATA QUALITY:
   - Look for duplicate employees or multiple SSNs
   - Flag terminated employees still showing as active
   - Identify rehires with inconsistent data

Report specific counts and examples where possible.
""",

    "4A": SCHEMA_ANALYSIS_PREAMBLE + """
ANALYSIS FOCUS: Benefits & Deductions Review

VALIDATE THESE ELEMENTS:

1. PRE-TAX DEDUCTIONS:
   - Section 125 (cafeteria) plan deductions
   - HSA contributions - check against annual limits
   - FSA elections
   - Verify deductions coded for correct tax treatment

2. POST-TAX DEDUCTIONS:
   - Roth 401k/403b contributions
   - After-tax benefit deductions
   - Garnishments and tax levies

3. W-2 BOX MAPPING:
   - Box 12 codes for retirement, HSA, etc.
   - Box 14 informational items
   - Verify deduction codes will produce correct W-2 reporting

Flag deductions with potentially incorrect tax treatment or W-2 coding.
""",

    "5A": SCHEMA_ANALYSIS_PREAMBLE + """
ANALYSIS FOCUS: Earnings Code Review

VALIDATE THESE ELEMENTS:

1. STANDARD EARNINGS:
   - Regular pay, overtime, bonus, commission codes
   - Verify tax treatment is correct per code
   - Check supplemental wage handling (flat rate vs aggregate)

2. SPECIAL EARNINGS:
   - Fringe benefits (personal use of company vehicle, etc.)
   - Third-party sick pay handling
   - Group term life insurance over $50k

3. YTD RECONCILIATION:
   - Earnings totals should tie to quarterly 941 reports
   - Look for timing differences or adjustments
   - Identify any out-of-period corrections

Focus on earnings codes that affect W-2 reporting accuracy.
""",

    "6A": SCHEMA_ANALYSIS_PREAMBLE + """
ANALYSIS FOCUS: W-2 Preview & Verification

VALIDATE THESE ELEMENTS:

1. FEDERAL BOXES:
   - Box 1 (wages) should reconcile to quarterly 941s
   - Box 2 (federal withholding) should tie to tax deposits
   - Box 3/4 (Social Security) - verify wage base limits applied
   - Box 5/6 (Medicare) - no wage limit applies

2. STATE BOXES:
   - Each state should show correct wage and tax totals
   - Reciprocity states handled correctly
   - Multiple state employees have proper allocations

3. BOX 12 CODES:
   - C: Group term life over $50k
   - D/E: 401k/403b elective deferrals
   - DD: Healthcare coverage cost (ACA reporting)
   - W: HSA employer contributions

4. COMMON W-2 ERRORS:
   - Negative amounts in any box
   - Missing state tax data
   - Incorrect or missing Box 12 codes
   - Prior year corrections needing W-2c

Flag any W-2s requiring correction before filing.
""",
}


# =============================================================================
# DEPENDENT ACTION GUIDANCE - Instructions for actions without reports
# =============================================================================

YEAR_END_DEPENDENT_GUIDANCE: Dict[str, str] = {
    "2B": """
**Action 2B - Update Company Information**

Based on the findings from Action 2A, review and update:

1. **Legal Company Name** - Must match IRS records exactly for W-2 filing
2. **DBA/Trade Name** - Update if changed during the year
3. **Company Address** - Verify current for tax correspondence
4. **FEIN** - Cannot be changed after W-2s are filed - verify NOW

⚠️ **Deadline**: Complete before final payroll run

**What to check in UKG:**
- Menu > Company > Company Setup
- Verify each field matches the Tax Verification report
""",

    "2C": """
**Action 2C - Update Tax Code Information**

Based on the findings from Action 2A, review and update tax codes:

1. **State Tax Registrations** - Ensure all states with employees have active registrations
2. **Tax Rates** - Update any rates that changed (especially SUI rates for new year)
3. **Tax IDs** - Verify state and local tax IDs are current

⚠️ **Common Issues:**
- Missing local tax codes for remote workers
- Outdated SUI rates (many states change annually)
- Pending registrations not completed

**What to check in UKG:**
- Menu > Company > Tax Codes
- Run Tax Code Audit report
""",

    "2E": """
**Action 2E - Multiple Worksite Reporting (MWR)**

Based on company data from Action 2A:

1. **Verify MWR Setup** - If required, ensure worksite codes are properly assigned
2. **Employee Assignments** - Check employees are assigned to correct worksites
3. **BLS Reporting** - Confirm quarterly MWR data is accurate

**When is MWR Required?**
- Companies with 10+ employees in most states
- Required for Bureau of Labor Statistics reporting
""",

    "2H": """
**Action 2H - Special Tax Category Overrides**

Based on earnings (2F) and deductions (2G) analysis:

1. **Employee-Level Overrides** - Review any employee-specific tax category changes
2. **Company-Level Overrides** - Check company code tax category exceptions
3. **Verify Necessity** - Ensure overrides are still needed for current year

⚠️ **Risk**: Incorrect overrides cause W-2 errors
""",

    "2J": """
**Action 2J - Healthcare W-2 Tax Categories**

Based on deduction analysis from Action 2G:

1. **Box 12 Code DD** - Verify employer + employee healthcare costs report correctly
2. **Section 125** - Confirm cafeteria plan deductions are pre-tax
3. **HSA Contributions** - Check Box 12 Code W setup

**ACA Requirement**: Employers with 250+ prior year W-2s must report healthcare costs
""",

    "2K": """
**Action 2K - Healthcare Benefits for New Year**

Based on deduction data from Action 2G:

1. **New Rates** - Update benefit deduction amounts for new plan year
2. **New Plans** - Add any new benefit options
3. **Effective Dates** - Ensure new rates start on correct date (usually 1/1)

**Common Issue**: Forgetting to update rates causes over/under deductions in January
""",

    "2L": """
**Action 2L - ALE Healthcare Reporting**

Based on deduction (2G) and healthcare (2J) data:

1. **ALE Status** - Verify if company qualifies as Applicable Large Employer (50+ FTE)
2. **1095-C Data** - Review employee healthcare offer/enrollment data
3. **YTD Amounts** - Verify employer contribution amounts are accurate

**Deadline**: 1095-C forms due to employees by March 2
""",

    "3B": """
**Action 3B - SSN Corrections**

Based on Year-End Validation from Action 3A:

1. **Invalid SSNs** - Contact employees with flagged SSNs
2. **Send W-9** - Request corrected information via Form W-9
3. **Update UKG** - Enter corrected SSNs before W-2 processing

⚠️ **Penalty**: $50/W-2 for incorrect SSN (up to $500k/year)
""",

    "3C": """
**Action 3C - Name/Address Updates**

Based on Year-End Validation from Action 3A:

1. **Name Mismatches** - Compare to SSA records (must match exactly)
2. **Address Updates** - Verify current addresses for W-2 delivery
3. **Deceased Employees** - Special W-2 handling required

**W-2 Delivery**: Invalid addresses = returned W-2s = penalties
""",

    "3D": """
**Action 3D - Deceased Employee Processing**

Based on validation data from Action 3A:

1. **Final W-2** - Issue to estate or surviving spouse
2. **Box Changes** - Some boxes handled differently for deceased
3. **1099 Consideration** - Payments after death may require 1099

**IRS Rule**: W-2 wages paid in year of death; 1099 for payments after
""",

    "5B": """
**Action 5B - Third-Party Sick Pay**

Based on earnings review from Action 5A:

1. **Identify TPSP** - Flag any third-party sick pay payments
2. **W-2 Reporting** - Verify Box 13 "Third-party sick pay" checkbox
3. **Tax Withholding** - Confirm taxes were handled correctly

**Common Issue**: TPSP not flagged = incorrect W-2 reporting
""",

    "5E": """
**Action 5E - Pre-Close Reconciliation**

Based on check reconciliation (5C) and arrears (5D):

1. **Resolve Outstanding Items** - Clear old checks and arrears before close
2. **Document Decisions** - Note any write-offs or waivers
3. **Final Verification** - Ensure all adjustments posted

**Goal**: Clean slate before final payroll
""",

    "6B": """
**Action 6B - W-2 Adjustments**

Based on W-2 preview from Action 6A:

1. **Correction Entries** - Process any needed adjustments
2. **Verify Changes** - Re-run preview to confirm fixes
3. **Document Reasons** - Note why adjustments were made

⚠️ **Timing**: Must complete before W-2 finalization deadline
""",

    "6C": """
**Action 6C - Final W-2 Review**

Based on W-2 preview from Action 6A:

1. **Sample Testing** - Review W-2s for sample of employees
2. **Box Totals** - Verify totals tie to quarterly reports
3. **Sign-Off** - Get manager/customer approval before filing

**Checklist**:
- [ ] Box 1 ties to 941 wages
- [ ] Box 2 ties to 941 withholding  
- [ ] State wages match state returns
""",
}


# =============================================================================
# ACTION KEYWORDS - For intelligence matching
# =============================================================================

YEAR_END_ACTION_KEYWORDS: Dict[str, Dict[str, List[str]]] = {
    '2A': {
        'keywords': ['tax', 'sui', 'suta', 'futa', 'ein', 'fein', 'rate', 'verification'],
        'categories': ['QUALITY', 'PATTERN']
    },
    '2B': {
        'keywords': ['company', 'address', 'name', 'legal'],
        'categories': ['QUALITY']
    },
    '2C': {
        'keywords': ['tax', 'code', 'rate', 'state'],
        'categories': ['QUALITY', 'PATTERN']
    },
    '2D': {
        'keywords': ['tax', 'jurisdiction', 'local', 'city', 'county'],
        'categories': ['QUALITY']
    },
    '2E': {
        'keywords': ['worksite', 'mwr', 'location', 'bls'],
        'categories': ['STRUCTURE']
    },
    '3A': {
        'keywords': ['employee', 'ssn', 'social', 'address', 'w2'],
        'categories': ['QUALITY', 'PATTERN']
    },
    '3B': {
        'keywords': ['employee', 'name', 'address', 'data'],
        'categories': ['QUALITY']
    },
    '4A': {
        'keywords': ['deduction', 'benefit', 'pretax', 'posttax', 'cafeteria', '125'],
        'categories': ['QUALITY', 'STRUCTURE']
    },
    '4B': {
        'keywords': ['401k', 'retirement', 'pension', 'match'],
        'categories': ['QUALITY']
    },
    '5A': {
        'keywords': ['earnings', 'pay', 'wage', 'salary', 'bonus'],
        'categories': ['QUALITY', 'PATTERN']
    },
    '5B': {
        'keywords': ['check', 'void', 'adjustment', 'reversal'],
        'categories': ['QUALITY']
    },
    '6A': {
        'keywords': ['w2', 'w-2', 'box', 'reporting', 'wage'],
        'categories': ['QUALITY', 'PATTERN']
    },
    '6B': {
        'keywords': ['third party', 'sick', 'disability'],
        'categories': ['QUALITY']
    },
    '6C': {
        'keywords': ['fringe', 'benefit', 'vehicle', 'life'],
        'categories': ['QUALITY', 'PATTERN']
    },
}


# =============================================================================
# EXPORT TAB DEFINITIONS - Custom tabs for Year-End export
# =============================================================================

YEAR_END_EXPORT_TABS: List[Dict[str, Any]] = [
    {
        "name": "Critical Issues Summary",
        "type": "issues",
        "description": "All identified issues requiring attention"
    },
    {
        "name": "Uploaded Files Reference",
        "type": "files",
        "description": "List of all uploaded documents"
    },
    {
        "name": "Key Deadlines",
        "type": "deadlines",
        "description": "Important dates and milestones"
    },
    {
        "name": "Step 2 - Analysis & Findings",
        "type": "step_analysis",
        "step": "2",
        "description": "Company and tax verification findings"
    },
    {
        "name": "Step 2D - WC Rates",
        "type": "action_analysis",
        "action": "2D",
        "description": "Workers Compensation rate analysis"
    },
    {
        "name": "Step 2F - Earnings",
        "type": "action_analysis",
        "action": "2F",
        "description": "Earnings code analysis"
    },
    {
        "name": "Step 2G - Deductions",
        "type": "action_analysis",
        "action": "2G",
        "description": "Deduction code analysis"
    },
    {
        "name": "Step 2L - Healthcare Audit",
        "type": "action_analysis",
        "action": "2L",
        "description": "Healthcare benefits audit"
    },
    {
        "name": "Step 5C - Check Recon",
        "type": "action_analysis",
        "action": "5C",
        "description": "Outstanding checks reconciliation"
    },
    {
        "name": "Step 5D - Arrears",
        "type": "action_analysis",
        "action": "5D",
        "description": "Arrears analysis"
    },
]


# =============================================================================
# REGISTRATION FUNCTION - Call this on startup to register the playbook
# =============================================================================

def register_year_end_playbook():
    """
    Register the Year-End playbook with the framework.
    
    Call this during app startup.
    
    Note: The actual structure (steps/actions) comes from parsing
    the uploaded Year-End Checklist document. This function registers
    the domain-specific configuration that enhances the parsed structure.
    """
    try:
        from backend.utils.playbook_framework import (
            PlaybookDefinition, 
            PlaybookRegistry,
            PLAYBOOK_REGISTRY
        )
    except ImportError:
        from utils.playbook_framework import (
            PlaybookDefinition, 
            PlaybookRegistry,
            PLAYBOOK_REGISTRY
        )
    
    # Create playbook definition with domain config
    # Note: Steps will be populated dynamically from parsed document
    year_end = PlaybookDefinition(
        playbook_id="year-end",
        name="Year-End Checklist",
        description="UKG Year-End Processing Checklist for W-2 preparation",
        version="2025.1.0",
        steps=[],  # Populated dynamically from parsed doc
        consultative_prompts=YEAR_END_CONSULTATIVE_PROMPTS,
        dependent_guidance=YEAR_END_DEPENDENT_GUIDANCE,
        action_keywords=YEAR_END_ACTION_KEYWORDS,
        export_tabs=YEAR_END_EXPORT_TABS,
    )
    
    PLAYBOOK_REGISTRY.register(year_end)
    logger.info("[YEAR-END] Playbook registered successfully")
    
    return year_end


def get_year_end_config() -> Dict[str, Any]:
    """
    Get Year-End specific configuration for use by the router.
    
    Returns all domain-specific config that the framework needs.
    """
    return {
        "consultative_prompts": YEAR_END_CONSULTATIVE_PROMPTS,
        "dependent_guidance": YEAR_END_DEPENDENT_GUIDANCE,
        "action_keywords": YEAR_END_ACTION_KEYWORDS,
        "export_tabs": YEAR_END_EXPORT_TABS,
    }
