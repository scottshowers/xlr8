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
Version: 1.0.0
Date: December 2025
"""

from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# CONSULTATIVE PROMPTS - Expert analysis guidance per action
# =============================================================================

YEAR_END_CONSULTATIVE_PROMPTS: Dict[str, str] = {
    "2A": """
CONSULTANT ANALYSIS - Apply your UKG/Payroll expertise:

1. FEIN VALIDATION:
   - Valid format: XX-XXXXXXX (9 digits with hyphen after 2)
   - Flag if missing or malformed
   - Cross-reference against IRS database format

2. SUI/SUTA RATES:
   - Typical range: 0.1% to 12% depending on state
   - Flag if outside normal range
   - Note: New employers often start at higher rates

3. FUTA RATE:
   - Standard rate: 6.0% (0.6% after credit)
   - Credit reduction states have higher effective rates
   - Flag if not 6.0% or doesn't match credit reduction list

4. COMPANY PROFILE:
   - Verify legal name matches exactly (case, punctuation)
   - Address should be complete with ZIP+4 if available
   - Note any multiple locations or DBAs

Return specific findings with values from the documents.
""",

    "2C": """
CONSULTANT ANALYSIS - Tax Code Verification:

1. STATE TAX REGISTRATIONS:
   - Every state with employees needs registration
   - Verify state tax IDs are in correct format per state
   - Flag missing registrations for states with payroll activity

2. TAX RATE UPDATES:
   - SUI rates change annually - verify current year rates
   - Local tax rates vary by jurisdiction
   - Flag any rates that seem outdated

3. RECIPROCITY AGREEMENTS:
   - Check for proper handling of multi-state employees
   - Verify resident vs work state tax handling

Focus on actionable issues that need resolution before year-end.
""",

    "3A": """
CONSULTANT ANALYSIS - Employee Data Validation:

1. SSN VALIDATION:
   - Format: XXX-XX-XXXX (9 digits)
   - Flag: 000-XX-XXXX, XXX-00-XXXX, XXX-XX-0000 (invalid patterns)
   - Flag: 9XX-XX-XXXX (ITINs - may need special handling)

2. NAME MATCHING:
   - Must match SSA records exactly for W-2
   - Flag special characters, extra spaces, Jr/Sr/III issues
   - Check for legal name vs preferred name confusion

3. ADDRESS VERIFICATION:
   - Complete address needed for W-2 delivery
   - Flag PO Boxes for certain states
   - Identify deceased employees (need special handling)

4. YEAR-END SPECIFIC:
   - Identify employees with multiple SSNs in system
   - Flag terminated employees still on active payroll
   - Check for rehires with different data

Report specific counts and examples where possible.
""",

    "4A": """
CONSULTANT ANALYSIS - Benefits & Deductions:

1. PRE-TAX DEDUCTIONS:
   - Section 125 (cafeteria) plans
   - HSA contributions (annual limits apply)
   - FSA elections
   - Verify proper tax treatment

2. POST-TAX DEDUCTIONS:
   - Roth contributions
   - After-tax benefits
   - Garnishments and levies

3. W-2 IMPLICATIONS:
   - Box 12 codes for various benefits
   - Box 14 for informational items
   - Verify coding matches deduction setup

Flag any deductions that may have incorrect W-2 treatment.
""",

    "5A": """
CONSULTANT ANALYSIS - Earnings Review:

1. EARNINGS CODES:
   - Regular, overtime, bonus, commission
   - Verify tax treatment per code
   - Check for supplemental wage handling

2. SPECIAL EARNINGS:
   - Fringe benefits (personal use of vehicle, etc.)
   - Third-party sick pay
   - Group term life over $50k

3. YTD RECONCILIATION:
   - Verify totals match quarterly reports
   - Check for timing differences
   - Identify any out-of-period adjustments

Focus on earnings that affect W-2 reporting.
""",

    "6A": """
CONSULTANT ANALYSIS - W-2 Preview:

1. BOX VERIFICATION:
   - Box 1 (wages) ties to 941s
   - Box 2 (federal tax) ties to deposits
   - Box 3/4 (Social Security) - check wage base
   - Box 5/6 (Medicare) - no wage limit

2. STATE BOXES:
   - Verify each state has correct totals
   - Check for reciprocity handling
   - Multiple states require multiple entries

3. BOX 12 CODES:
   - C: Group term life over $50k
   - D/E: 401k/403b contributions
   - DD: Health coverage cost (ACA)
   - W: HSA contributions

4. COMMON ERRORS:
   - Negative amounts
   - Missing state data
   - Incorrect Box 12 codes
   - W-2c needed for prior year

Flag any W-2s that will need correction before filing.
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
