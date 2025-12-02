"""
Playbooks Router v2 - Interactive Year-End Checklist

Endpoints:
- GET /playbooks/year-end/structure - Get parsed playbook structure
- GET /playbooks/year-end/progress/{project_id} - Get progress for project
- POST /playbooks/year-end/progress/{project_id} - Update action status
- POST /playbooks/year-end/scan/{project_id}/{action_id} - Scan docs for action
- GET /playbooks/year-end/export/{project_id} - Export current state as XLSX
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
import json
import io
import os
import re
from datetime import datetime
from pathlib import Path

# Excel generation
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/playbooks", tags=["playbooks"])

# Persistent progress storage location
PROGRESS_FILE = "/data/playbook_progress.json"

# Cached playbook structure
PLAYBOOK_CACHE = {}

# =============================================================================
# ACTION DEPENDENCIES - Which actions inherit from which
# =============================================================================
# Key = action that inherits, Value = list of parent actions to pull from
ACTION_DEPENDENCIES = {
    # Step 2: Company Information
    "2B": ["2A"],  # Update company info - uses Company Tax Verification & Master Profile from 2A
    "2C": ["2A"],  # Update tax codes - uses same docs from 2A
    "2E": ["2A"],  # MWR review - uses company data from 2A
    "2H": ["2F", "2G"],  # Special overrides - needs earnings (2F) and deductions (2G)
    "2J": ["2G"],  # Healthcare W-2 - uses deduction data from 2G
    "2K": ["2G"],  # Healthcare new year - uses deduction data from 2G
    "2L": ["2G", "2J"],  # Healthcare ALE - uses deductions and healthcare config
    
    # Step 3: Employee Information
    "3B": ["3A"],  # SSN updates - uses Year-End Validation from 3A
    "3C": ["3A"],  # Name/address updates - uses same validation report
    "3D": ["3A"],  # Deceased employees - uses validation data
    
    # Step 5: Pre-Close
    "5B": ["5A"],  # Third party sick pay - uses earnings review from 5A
    "5E": ["5C", "5D"],  # Reconciliation - needs check recon and arrears
    
    # Step 6: Post-Close
    "6B": ["6A"],  # W-2 adjustments - uses W-2 preview from 6A
    "6C": ["6A"],  # W-2 review - uses same preview data
}

# =============================================================================
# CONSULTATIVE AI CONTEXT - Benchmarks, red flags, and expert guidance
# =============================================================================
CONSULTATIVE_PROMPTS = {
    "2A": """
CONSULTANT ANALYSIS - Apply your UKG/Payroll expertise:

1. FEIN VALIDATION:
   - Valid format: XX-XXXXXXX (9 digits with hyphen after 2)
   - Flag if missing or malformed

2. MULTI-STATE COMPLEXITY:
   - 1-5 states: Standard complexity
   - 6-15 states: Moderate complexity - ensure all state registrations current
   - 15+ states: High complexity - recommend dedicated state tax review
   
3. TAX RATE BENCHMARKS (flag if outside ranges):
   - Federal FUTA: Should be 0.6% (after credit)
   - State SUI: Typically 1-6%, new employers often 2.7-3.4%
   - SUI >8%: Flag as HIGH - may indicate claims history issues
   - SUI <1%: Flag as VERY LOW - verify this is correct
   
4. COMMON ISSUES TO FLAG:
   - Missing state registrations for states with employees
   - Tax codes without associated rates
   - Expired tax IDs or pending registrations
   - Company name mismatches between systems
   
5. YEAR-END READINESS:
   - Are all W-2 reporting fields properly configured?
   - Any states requiring special W-2 formats (PA, IN localities)?
""",

    "2B": """
CONSULTANT ANALYSIS - Company Information Updates:

INHERITED CONTEXT: Use findings from 2A (Company Tax Verification & Master Profile)

1. CRITICAL FIELDS FOR W-2:
   - Legal company name (must match IRS records exactly)
   - DBA/Trade name if applicable
   - Address (affects state reporting)
   - FEIN (cannot be changed after W-2s filed)

2. THINGS TO VERIFY:
   - Has company had any M&A activity? Name changes?
   - Is the address current for tax correspondence?
   - Any new states added mid-year that need setup?

3. DEADLINE AWARENESS:
   - Company info changes should be completed BEFORE final payroll
   - Some changes require IRS notification (Form 8822-B)
""",

    "2C": """
CONSULTANT ANALYSIS - Tax Code Updates:

INHERITED CONTEXT: Use findings from 2A (Company Tax Verification & Master Profile)

1. PRIORITY ITEMS:
   - Any tax codes flagged in 2A with unusual rates
   - New state registrations needed
   - Rate changes effective for new year

2. 2025 TAX CHANGES TO WATCH:
   - Social Security wage base: Check if updated
   - State-specific changes (many states adjust SUI rates annually)
   - Local tax jurisdiction changes

3. COMMON ERRORS:
   - Forgetting to update experience-rated SUI for new year
   - Missing local tax codes for remote workers
   - Incorrect tax categories affecting W-2 boxes
""",

    "2D": """
CONSULTANT ANALYSIS - Workers Compensation:

1. RATE BENCHMARKS BY INDUSTRY:
   - Office/Clerical (8810): 0.10% - 0.50%
   - Sales Outside (8742): 0.30% - 1.00%
   - Manufacturing: 2.00% - 8.00%
   - Construction: 5.00% - 15.00%
   - Healthcare: 1.50% - 4.00%
   
2. EXPERIENCE MODIFICATION (MOD) FACTOR:
   - 1.00 = Industry average
   - < 0.85 = Excellent safety record (discount)
   - 0.85 - 1.00 = Good
   - 1.00 - 1.25 = Below average (surcharge)
   - > 1.25 = Poor - flag for safety review
   
3. RED FLAGS:
   - Class codes that don't match actual job duties
   - Missing class codes for job types
   - Rates significantly different from prior year (>20% change)
   - Governing class code mismatch
   
4. YEAR-END TASKS:
   - Verify all class codes still accurate
   - Check for rate changes effective 1/1
   - Reconcile estimated vs actual payroll for audit
""",

    "2F": """
CONSULTANT ANALYSIS - Earnings Tax Categories:

1. W-2 BOX MAPPING (verify correct):
   - Regular wages → Box 1, 3, 5
   - Tips → Box 1, 7 (allocated tips Box 8)
   - Group Term Life >$50k → Box 1, 12 Code C
   - 401k deferrals → Box 12 Code D (reduces Box 1)
   - HSA employer contributions → Box 12 Code W
   
2. COMMON MISCONFIGURATIONS:
   - Bonus/commission not flagged as supplemental
   - Fringe benefits missing imputed income setup
   - Relocation expenses (taxable since 2018)
   - Gift cards/awards not flowing to W-2
   
3. STATE-SPECIFIC ISSUES:
   - PA: Some fringe benefits taxed differently
   - NJ: Disability insurance handling
   - CA: SDI considerations
   
4. RECONCILIATION CHECK:
   - Do QTD totals tie to 941s?
   - Any earning codes with zero YTD that seem unusual?
""",

    "2G": """
CONSULTANT ANALYSIS - Deduction Tax Categories:

1. PRE-TAX vs POST-TAX (critical for W-2):
   - 401k/403b: Pre-tax (Box 12 Code D/E)
   - Roth 401k: Post-tax but Box 12 Code AA
   - Section 125 (Cafeteria): Pre-tax (reduces Box 1)
   - HSA: Pre-tax (Box 12 Code W)
   - After-tax deductions: Do NOT reduce Box 1
   
2. COMMON ERRORS:
   - Medical premiums not set as Section 125
   - Roth contributions coded wrong
   - Garnishments affecting wrong tax boxes
   - Employer HSA contributions missing from Box 12
   
3. ACA COMPLIANCE (Box 12 Code DD):
   - Employer + employee medical cost must be reported
   - Threshold: 250+ W-2s in prior year
   - Common miss: Not including employer portion
   
4. LIMITS TO VERIFY (2025):
   - 401k: $23,500 ($31,000 catch-up if 50+)
   - HSA: $4,300 single / $8,550 family
   - FSA: $3,300
   - Dependent Care: $5,000
""",

    "3A": """
CONSULTANT ANALYSIS - SSN Validation:

1. SSN FORMAT ISSUES:
   - Must be 9 digits, XXX-XX-XXXX
   - Cannot start with 9 (except ITIN)
   - Cannot be 000-XX-XXXX or XXX-00-XXXX
   - ITINs (9XX) need special handling for W-2
   
2. IRS MATCHING:
   - SSA matches SSN + Name combination
   - Middle name/initial issues cause mismatches
   - Suffix (Jr, Sr, III) must match SSA records
   - Hyphenated names: Check SSA has same format
   
3. ACTION PRIORITIES:
   - ITIN holders: May need name control review
   - Applied for/Pending: Must resolve before W-2
   - Deceased employees: Verify final W-2 handling
   
4. PENALTIES:
   - $50/W-2 for incorrect SSN/name (up to $500k/year)
   - First-year safe harbor if good faith effort made
   
5. REMEDIATION:
   - Send Form W-9 to employee for correction
   - Document attempts to obtain correct info
""",

    "5C": """
CONSULTANT ANALYSIS - Outstanding Checks:

1. STALE-DATED CHECKS:
   - Typically >6 months old
   - Must be voided and wages added back
   - W-2 impact: Wages reportable when check issued, not cashed
   
2. ESCHEATMENT/UNCLAIMED PROPERTY:
   - State-specific holding periods (1-5 years typically)
   - Must report to state of employee's last known address
   - Deadline varies by state (usually March-November)
   
3. YEAR-END ACTIONS:
   - Identify all checks outstanding >90 days
   - Attempt employee contact for checks >6 months
   - Document escheatment status for checks meeting threshold
   
4. COMMON ISSUES:
   - Direct deposit rejects sitting as uncashed
   - Terminated employees with final checks unclaimed
   - Address issues preventing delivery
""",

    "5D": """
CONSULTANT ANALYSIS - Arrears Balances:

1. ARREARS IMPACT:
   - Unpaid deductions affect W-2 reporting
   - Pre-tax arrears: Employee owes less tax on W-2
   - Post-tax arrears: No W-2 impact but company owed money
   
2. COLLECTION PRIORITY:
   - 401k arrears: Must collect to meet ADP/ACP testing
   - Benefit arrears: Impacts coverage eligibility
   - Garnishment arrears: Legal obligation to collect
   
3. YEAR-END DECISIONS:
   - Write off uncollectible amounts?
   - Impact on benefit elections for new year?
   - Any retroactive adjustments needed?
   
4. COMMON SCENARIOS:
   - Leave of absence with unpaid benefit premiums
   - Commission-only periods with no deductions taken
   - Terminated employees with benefit arrears
""",

    "DEFAULT": """
CONSULTANT ANALYSIS:

1. Review the uploaded documents for completeness
2. Identify any data quality issues or gaps
3. Flag items requiring customer clarification
4. Note any year-end compliance concerns
5. Recommend specific actions to take
"""
}

# =============================================================================
# DEPENDENCY HELPER FUNCTIONS
# =============================================================================

def get_parent_actions(action_id: str) -> List[str]:
    """Get list of parent actions this action depends on."""
    return ACTION_DEPENDENCIES.get(action_id, [])


def get_inherited_data(project_id: str, action_id: str) -> Dict[str, Any]:
    """Get documents and findings from parent actions."""
    parents = get_parent_actions(action_id)
    if not parents:
        return {"documents": [], "findings": [], "content": []}
    
    inherited_docs = []
    inherited_findings = []
    inherited_content = []
    
    progress = PLAYBOOK_PROGRESS.get(project_id, {})
    
    for parent_id in parents:
        parent_progress = progress.get(parent_id, {})
        
        # Get documents from parent
        parent_docs = parent_progress.get("documents_found", [])
        inherited_docs.extend(parent_docs)
        
        # Get findings from parent
        parent_findings = parent_progress.get("findings")
        if parent_findings:
            inherited_findings.append({
                "action_id": parent_id,
                "findings": parent_findings
            })
            
            # Add summary as context for AI
            if parent_findings.get("summary"):
                inherited_content.append(f"[FROM ACTION {parent_id}]: {parent_findings['summary']}")
            if parent_findings.get("key_values"):
                for k, v in parent_findings["key_values"].items():
                    inherited_content.append(f"[FROM {parent_id}] {k}: {v}")
    
    return {
        "documents": list(set(inherited_docs)),  # Dedupe
        "findings": inherited_findings,
        "content": inherited_content
    }


def load_progress() -> Dict:
    """Load progress from persistent storage."""
    try:
        if os.path.exists(PROGRESS_FILE):
            with open(PROGRESS_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load progress file: {e}")
    return {}


def save_progress(progress: Dict):
    """Save progress to persistent storage."""
    try:
        os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(progress, f, indent=2, default=str)
    except Exception as e:
        logger.error(f"Could not save progress file: {e}")


# Load existing progress on startup
PLAYBOOK_PROGRESS = load_progress()


class ActionUpdate(BaseModel):
    status: str  # not_started, in_progress, complete, na, blocked
    notes: Optional[str] = None
    findings: Optional[Dict[str, Any]] = None


class ScanResult(BaseModel):
    found: bool
    documents: List[Dict[str, Any]]
    findings: Optional[Dict[str, Any]]
    suggested_status: str


# ============================================================================
# STRUCTURE ENDPOINT - Get playbook definition
# ============================================================================

@router.get("/year-end/structure")
async def get_year_end_structure():
    """
    Get the parsed Year-End Checklist structure.
    Parses from Global Data if available, otherwise uses cached/default.
    """
    global PLAYBOOK_CACHE
    
    # Check if we have it cached
    if 'year-end-2025' in PLAYBOOK_CACHE:
        return PLAYBOOK_CACHE['year-end-2025']
    
    # Try to find and parse the Year-End doc from Global Data
    try:
        from backend.utils.playbook_parser import parse_year_end_checklist
        
        # Look for Year-End doc in global data or known locations
        possible_paths = [
            '/data/global/2025_UKG_Pro_Pay_US_Year_End_Checklist_Payment_Services.docx',
            '/data/uploads/global/2025_UKG_Pro_Pay_US_Year_End_Checklist_Payment_Services.docx',
            '/app/data/global/year_end_checklist.docx',
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Parsing Year-End doc from: {path}")
                structure = parse_year_end_checklist(path)
                PLAYBOOK_CACHE['year-end-2025'] = structure
                return structure
        
        # If no file found, return default structure
        logger.warning("Year-End doc not found, using default structure")
        return get_default_year_end_structure()
        
    except Exception as e:
        logger.error(f"Error parsing Year-End doc: {e}")
        return get_default_year_end_structure()


def get_default_year_end_structure() -> Dict[str, Any]:
    """Default Year-End structure if doc not available."""
    return {
        "playbook_id": "year-end-2025",
        "title": "UKG Pro Pay U.S. Year-End Checklist: Payment Services",
        "steps": [
            {
                "step_number": "1",
                "step_name": "Get Ready",
                "phase": "before_final_payroll",
                "actions": [
                    {"action_id": "1A", "description": "Create an internal year-end team with representation from relevant departments (Payroll, HR, Accounting, Finance, IT)", "due_date": None, "action_type": "recommended", "keywords": ["team", "internal"], "reports_needed": []},
                    {"action_id": "1B", "description": "If you do not use UKG Pro Print Services, order federal Forms W-2, 1099-MISC, 1099-NEC, and 1099-R from the IRS or office supply store", "due_date": None, "action_type": "recommended", "keywords": ["forms", "print"], "reports_needed": []},
                    {"action_id": "1C", "description": "Confirm the Transmittal Control Code (TCC) for Form 1099 electronic filing or apply for an Information Returns TCC from the IRS", "due_date": "11/01/2025", "action_type": "required", "keywords": ["tcc", "1099"], "reports_needed": []},
                ]
            },
            {
                "step_number": "2",
                "step_name": "Review and Update Company Information",
                "phase": "before_final_payroll",
                "actions": [
                    {"action_id": "2A", "description": "Review company and tax code information using the Company Tax Verification and Company Master Profile reports", "due_date": None, "action_type": "required", "keywords": ["tax", "fein", "company"], "reports_needed": ["Company Tax Verification", "Company Master Profile"]},
                    {"action_id": "2B", "description": "Update company information and tax reporting details listed on the completed Company Tax Verification report", "due_date": None, "action_type": "required", "keywords": ["tax", "company"], "reports_needed": []},
                    {"action_id": "2C", "description": "Update any tax code information listed on the completed Company Tax Verification report and Company Master Profile report", "due_date": None, "action_type": "required", "keywords": ["tax code"], "reports_needed": []},
                    {"action_id": "2D", "description": "Review workers' compensation company information using the Workers' Compensation Risk Rates standard report", "due_date": None, "action_type": "recommended", "keywords": ["workers comp", "risk rates"], "reports_needed": ["Workers Compensation Risk Rates"]},
                    {"action_id": "2E", "description": "Review company or tax group multiple worksite reporting (MWR) information", "due_date": None, "action_type": "recommended", "keywords": ["mwr", "worksite"], "reports_needed": []},
                    {"action_id": "2F", "description": "Review earnings codes to make sure they are assigned the correct earnings tax categories", "due_date": None, "action_type": "recommended", "keywords": ["earnings", "tax categories"], "reports_needed": ["Earnings Tax Categories", "Earnings Codes"]},
                    {"action_id": "2G", "description": "Review deduction/benefit codes to make sure they are assigned the correct deduction tax categories", "due_date": None, "action_type": "recommended", "keywords": ["deduction", "benefit", "tax categories"], "reports_needed": ["Deduction Tax Categories", "Deduction Codes"]},
                    {"action_id": "2H", "description": "Review any special earnings or deduction tax category overrides by employee or company code", "due_date": None, "action_type": "recommended", "keywords": ["special", "override"], "reports_needed": []},
                    {"action_id": "2J", "description": "Review healthcare benefit deductions to make sure they have the correct tax categories for W-2 reporting", "due_date": None, "action_type": "recommended", "keywords": ["healthcare", "w-2"], "reports_needed": []},
                    {"action_id": "2K", "description": "Review and update healthcare benefit deductions effective for the new year", "due_date": None, "action_type": "recommended", "keywords": ["healthcare", "benefit"], "reports_needed": []},
                    {"action_id": "2L", "description": "Verify employee and employer healthcare year-to-date amounts for Applicable Large Employer (ALE) reporting", "due_date": None, "action_type": "recommended", "keywords": ["healthcare", "ale", "ytd"], "reports_needed": []},
                ]
            },
            {
                "step_number": "3",
                "step_name": "Review and Update Employee Information",
                "phase": "before_final_payroll",
                "actions": [
                    {"action_id": "3A", "description": "Review employees' Social Security Numbers (SSNs) using the Year-End Validation Report", "due_date": None, "action_type": "required", "keywords": ["ssn", "social security"], "reports_needed": ["Year-End Validation"]},
                    {"action_id": "3B", "description": "Review employees' addresses using the Year-End Validation Report", "due_date": None, "action_type": "required", "keywords": ["address"], "reports_needed": ["Year-End Validation"]},
                    {"action_id": "3C", "description": "Review employees with Form W-2 Box 13 reporting for statutory employees and retirement plan participants", "due_date": None, "action_type": "recommended", "keywords": ["w-2", "box 13", "statutory"], "reports_needed": []},
                ]
            },
            {
                "step_number": "4",
                "step_name": "Generate Employee Forms",
                "phase": "before_final_payroll",
                "actions": [
                    {"action_id": "4A", "description": "Import gross receipts and process tip allocations for tipped employees", "due_date": None, "action_type": "recommended", "keywords": ["tips", "gross receipts"], "reports_needed": []},
                    {"action_id": "4B", "description": "Generate year-end employee forms from the Employee Tax Forms page", "due_date": None, "action_type": "required", "keywords": ["w-2", "forms"], "reports_needed": []},
                ]
            },
            {
                "step_number": "5",
                "step_name": "Balance and Reconcile Pay Data",
                "phase": "before_final_payroll",
                "actions": [
                    {"action_id": "5A", "description": "Create an off-cycle payroll (adjustment payroll) to process corrections before closing the year", "due_date": None, "action_type": "recommended", "keywords": ["adjustment", "off-cycle"], "reports_needed": []},
                    {"action_id": "5B", "description": "Review negative wages using the W-2 Negative Wage Report", "due_date": None, "action_type": "required", "keywords": ["negative", "wages", "w-2"], "reports_needed": ["W-2 Negative Wage"]},
                    {"action_id": "5C", "description": "Review non-reconciled checks, including manual and voided checks, using the Outstanding Checks Report", "due_date": None, "action_type": "required", "keywords": ["outstanding", "checks", "voided"], "reports_needed": ["Outstanding Checks"]},
                    {"action_id": "5D", "description": "Review employees with outstanding arrears balances using the Arrears Report", "due_date": None, "action_type": "required", "keywords": ["arrears", "outstanding"], "reports_needed": ["Arrears"]},
                    {"action_id": "5E", "description": "Review and reconcile payroll data with general ledger", "due_date": None, "action_type": "recommended", "keywords": ["reconcile", "gl", "ledger"], "reports_needed": []},
                ]
            },
            {
                "step_number": "6",
                "step_name": "Close the Quarter and Year",
                "phase": "before_final_payroll",
                "actions": [
                    {"action_id": "6A", "description": "Pay Puerto Rico employees a Christmas Bonus per the Puerto Rico Act", "due_date": "Before last payroll", "action_type": "required", "keywords": ["puerto rico", "christmas bonus"], "reports_needed": []},
                    {"action_id": "6B", "description": "Process and close the last regular payroll of the year", "due_date": "12/29/2025 12:00 p.m.", "action_type": "required", "keywords": ["final payroll", "close"], "reports_needed": []},
                    {"action_id": "6C", "description": "Post current-quarter Q4 adjustments (such as third-party sick pay) before quarter close", "due_date": "12/29/2025 12:00 p.m.", "action_type": "required", "keywords": ["q4", "adjustment", "third party sick"], "reports_needed": []},
                ]
            },
            {
                "step_number": "7",
                "step_name": "Review Employee Forms",
                "phase": "after_final_payroll",
                "actions": [
                    {"action_id": "7A", "description": "Review Form W-2 information using standard reports and validation tools", "due_date": None, "action_type": "required", "keywords": ["w-2", "review"], "reports_needed": []},
                    {"action_id": "7B", "description": "Review Forms W-2 for U.S. territories (Puerto Rico, Virgin Islands, Guam)", "due_date": None, "action_type": "recommended", "keywords": ["w-2", "territories"], "reports_needed": []},
                    {"action_id": "7C", "description": "Review Forms 1099-MISC, 1099-NEC, and 1099-R information", "due_date": None, "action_type": "required", "keywords": ["1099"], "reports_needed": []},
                ]
            },
            {
                "step_number": "8",
                "step_name": "Prepare for Next Year",
                "phase": "after_final_payroll",
                "actions": [
                    {"action_id": "8A", "description": "Add federal bank holidays for the new year from the Holiday Calendar page", "due_date": None, "action_type": "recommended", "keywords": ["holiday", "calendar"], "reports_needed": []},
                    {"action_id": "8B", "description": "Configure next year's time off and accrual settings for UKG Pro Time solutions", "due_date": None, "action_type": "recommended", "keywords": ["time off", "accrual"], "reports_needed": []},
                    {"action_id": "8C", "description": "Extend processing calendars for each active pay group", "due_date": None, "action_type": "required", "keywords": ["calendar", "pay group"], "reports_needed": []},
                    {"action_id": "8D", "description": "Update goal amounts for earnings and deductions with annual limits", "due_date": "After last payroll, before first payroll of new year", "action_type": "required", "keywords": ["goal", "limit", "annual"], "reports_needed": []},
                ]
            },
            {
                "step_number": "9",
                "step_name": "Update Employee Form Delivery Options",
                "phase": "after_final_payroll",
                "actions": [
                    {"action_id": "9A", "description": "Encourage employees to opt in to paperless delivery of W-2 forms", "due_date": None, "action_type": "recommended", "keywords": ["paperless", "electronic"], "reports_needed": []},
                    {"action_id": "9B", "description": "Provide employees with the ability to import their W-2 data to tax preparation software", "due_date": None, "action_type": "recommended", "keywords": ["import", "tax software"], "reports_needed": []},
                ]
            },
            {
                "step_number": "10",
                "step_name": "Update Employee Tax Withholding Elections",
                "phase": "after_final_payroll",
                "actions": [
                    {"action_id": "10A", "description": "For employees who claimed exempt on their federal W-4, remind them to submit a new W-4 form", "due_date": None, "action_type": "required", "keywords": ["exempt", "w-4"], "reports_needed": []},
                    {"action_id": "10B", "description": "For employees with expiring tax withholding elections, update their records", "due_date": "02/15/2026", "action_type": "required", "keywords": ["withholding", "expiring"], "reports_needed": []},
                ]
            },
            {
                "step_number": "11",
                "step_name": "Finalize Employee Forms and Quarterly Reporting",
                "phase": "after_final_payroll",
                "actions": [
                    {"action_id": "11A", "description": "Finalize employee federal Forms W-2, 1099, and W-2c from the Employee Tax Forms page", "due_date": "01/07/2026 5:00 p.m. ET", "action_type": "required", "keywords": ["finalize", "w-2"], "reports_needed": []},
                    {"action_id": "11B", "description": "Review the Quarter-to-Date (QTD) Analysis Report before quarterly close", "due_date": "01/08/2026", "action_type": "required", "keywords": ["qtd", "quarterly"], "reports_needed": ["QTD Analysis"]},
                    {"action_id": "11C", "description": "UKG Pro Payment Services begins cash collection as scheduled", "due_date": "01/13/2026", "action_type": "required", "keywords": ["cash collection"], "reports_needed": []},
                ]
            },
            {
                "step_number": "12",
                "step_name": "Print Forms",
                "phase": "after_final_payroll",
                "actions": [
                    {"action_id": "12A", "description": "Approve W-2 forms for printing if Payment Services does not automatically approve", "due_date": "01/16/2026 11:59 p.m.", "action_type": "required", "keywords": ["approve", "print", "w-2"], "reports_needed": []},
                    {"action_id": "12B", "description": "Approve 1099 forms for filing if Payment Services does not automatically approve", "due_date": None, "action_type": "required", "keywords": ["approve", "1099"], "reports_needed": []},
                    {"action_id": "12C", "description": "Create PDF print files for Forms W-2 for U.S. territories", "due_date": "01/16/2026 11:59 p.m.", "action_type": "recommended", "keywords": ["pdf", "territories"], "reports_needed": []},
                ]
            },
            {
                "step_number": "13",
                "step_name": "Distribute Employee Forms",
                "phase": "after_final_payroll",
                "actions": [
                    {"action_id": "13A", "description": "Distribute electronic and paper federal Forms W-2 to employees", "due_date": "02/02/2026", "action_type": "required", "keywords": ["distribute", "w-2"], "reports_needed": []},
                    {"action_id": "13B", "description": "Distribute Forms W-2 for U.S. territories to employees", "due_date": "02/02/2026", "action_type": "required", "keywords": ["distribute", "territories"], "reports_needed": []},
                    {"action_id": "13C", "description": "Distribute electronic and paper Forms 1099-NEC to recipients", "due_date": "02/02/2026", "action_type": "required", "keywords": ["distribute", "1099-nec"], "reports_needed": []},
                    {"action_id": "13D", "description": "Distribute Forms 1099-MISC and 1099-R to recipients", "due_date": "02/02/2026", "action_type": "required", "keywords": ["distribute", "1099"], "reports_needed": []},
                ]
            },
            {
                "step_number": "14",
                "step_name": "File Employee and Employer Forms",
                "phase": "after_final_payroll",
                "actions": [
                    {"action_id": "14A", "description": "File Form 1099-NEC electronic files with the IRS", "due_date": "02/02/2026", "action_type": "required", "keywords": ["file", "1099-nec", "irs"], "reports_needed": []},
                    {"action_id": "14B", "description": "File Form 1099-MISC electronic files with the IRS", "due_date": "03/31/2026", "action_type": "required", "keywords": ["file", "1099-misc", "irs"], "reports_needed": []},
                    {"action_id": "14C", "description": "File Form 1099-R electronic files with the IRS", "due_date": "03/31/2026", "action_type": "required", "keywords": ["file", "1099-r", "irs"], "reports_needed": []},
                    {"action_id": "14D", "description": "File Form 945 electronically or send to the IRS", "due_date": "02/02/2026", "action_type": "required", "keywords": ["file", "945", "irs"], "reports_needed": []},
                ]
            },
        ],
        "total_actions": 55,
        "source_file": "default_structure"
    }


# ============================================================================
# PROGRESS ENDPOINTS - Track completion status
# ============================================================================

@router.get("/year-end/progress/{project_id}")
async def get_progress(project_id: str):
    """Get playbook progress for a project."""
    if project_id not in PLAYBOOK_PROGRESS:
        PLAYBOOK_PROGRESS[project_id] = {}
    
    return {
        "project_id": project_id,
        "progress": PLAYBOOK_PROGRESS[project_id],
        "updated_at": datetime.now().isoformat()
    }


@router.post("/year-end/progress/{project_id}/{action_id}")
async def update_progress(project_id: str, action_id: str, update: ActionUpdate):
    """Update status for a specific action."""
    if project_id not in PLAYBOOK_PROGRESS:
        PLAYBOOK_PROGRESS[project_id] = {}
    
    PLAYBOOK_PROGRESS[project_id][action_id] = {
        "status": update.status,
        "notes": update.notes,
        "findings": update.findings,
        "updated_at": datetime.now().isoformat()
    }
    
    # Persist to file
    save_progress(PLAYBOOK_PROGRESS)
    
    return {"success": True, "action_id": action_id, "status": update.status}


@router.delete("/year-end/progress/{project_id}")
async def reset_progress(project_id: str):
    """Reset all progress for a project's year-end checklist."""
    global PLAYBOOK_PROGRESS
    
    if project_id in PLAYBOOK_PROGRESS:
        del PLAYBOOK_PROGRESS[project_id]
        save_progress(PLAYBOOK_PROGRESS)
        logger.info(f"Reset year-end progress for project {project_id}")
        return {"success": True, "message": f"Progress reset for project {project_id}"}
    else:
        return {"success": True, "message": "No progress to reset"}


# ============================================================================
# SCAN ENDPOINT - Search docs for action-relevant content
# ============================================================================

@router.post("/year-end/scan/{project_id}/{action_id}")
async def scan_for_action(project_id: str, action_id: str):
    """
    Scan project documents for content relevant to a specific action.
    
    ENHANCED FEATURES:
    - Inherits documents/findings from parent actions (no re-upload needed)
    - Uses consultative AI with industry benchmarks
    - Provides actionable recommendations
    """
    try:
        from utils.rag_handler import RAGHandler
        
        # Get action details from structure
        structure = await get_year_end_structure()
        action = None
        for step in structure.get('steps', []):
            for a in step.get('actions', []):
                if a['action_id'] == action_id:
                    action = a
                    break
            if action:
                break
        
        if not action:
            raise HTTPException(status_code=404, detail=f"Action {action_id} not found")
        
        # Get reports needed for this action
        reports_needed = action.get('reports_needed', [])
        
        # =====================================================================
        # CHECK FOR INHERITED DATA FROM PARENT ACTIONS
        # =====================================================================
        inherited = get_inherited_data(project_id, action_id)
        inherited_docs = inherited["documents"]
        inherited_findings = inherited["findings"]
        inherited_content = inherited["content"]
        
        parent_actions = get_parent_actions(action_id)
        
        if parent_actions:
            logger.info(f"[SCAN] Action {action_id} inherits from: {parent_actions}")
            logger.info(f"[SCAN] Inherited {len(inherited_docs)} docs, {len(inherited_findings)} findings sets")
        
        # Search for documents
        rag = RAGHandler()
        found_docs = []
        all_content = []
        seen_files = set()
        
        # Add inherited docs to found docs (they're already uploaded)
        for doc_name in inherited_docs:
            if doc_name not in seen_files:
                seen_files.add(doc_name)
                found_docs.append({
                    "filename": doc_name,
                    "snippet": f"Inherited from action {', '.join(parent_actions)}",
                    "query": "inherited",
                    "match_type": "inherited"
                })
        
        # Add inherited context to all_content for AI
        all_content.extend(inherited_content)
        
        # STEP 1: Get project document filenames from ChromaDB metadata
        try:
            collection = rag.client.get_or_create_collection(name="documents")
            all_results = collection.get(include=["metadatas"], limit=1000)
            
            project_files = set()  # Just track filenames
            for metadata in all_results.get("metadatas", []):
                doc_project = metadata.get("project_id") or metadata.get("project", "")
                if doc_project == project_id or doc_project == project_id[:8]:
                    filename = metadata.get("source", metadata.get("filename", "Unknown"))
                    project_files.add(filename)
            
            logger.info(f"[SCAN] Found {len(project_files)} unique files in project {project_id}: {list(project_files)}")
            
            # STEP 2: Match by filename - check if any report name appears in filename
            for report_name in reports_needed:
                report_keywords = report_name.lower().split()
                for filename in project_files:
                    filename_lower = filename.lower()
                    # Check if report keywords appear in filename
                    matches = sum(1 for kw in report_keywords if kw in filename_lower)
                    if matches >= len(report_keywords) - 1:  # Allow 1 word missing
                        if filename not in seen_files:
                            seen_files.add(filename)
                            found_docs.append({
                                "filename": filename,
                                "snippet": f"Matched report: {report_name}",
                                "query": report_name,
                                "match_type": "filename"
                            })
                            all_content.append(f"[FILE: {filename}] - matches required report: {report_name}")
                            logger.info(f"[SCAN] Filename match: '{filename}' for report '{report_name}'")
            
        except Exception as e:
            logger.warning(f"[SCAN] Filename matching failed: {e}")
        
        # STEP 3: Semantic search - also search for inherited doc content
        # Build queries from: reports needed + action description + inherited doc names
        queries = reports_needed + [action.get('description', '')[:100]]
        if inherited_docs:
            queries.extend(inherited_docs[:3])  # Also search for content from inherited docs
        
        for query in queries[:8]:
                try:
                    results = rag.search(
                        collection_name="documents",
                        query=query,
                        n_results=15,
                        project_id=project_id
                    )
                    if results:
                        for result in results:
                            doc = result.get('document', '')
                            if doc and len(doc) > 50:
                                cleaned = re.sub(r'ENC256:[A-Za-z0-9+/=]+', '[ENCRYPTED]', doc)
                                if cleaned.count('[ENCRYPTED]') < 10:
                                    metadata = result.get('metadata', {})
                                    filename = metadata.get('source', metadata.get('filename', 'Unknown'))
                                    # Add content for AI analysis
                                    all_content.append(f"[FILE: {filename}]\n{cleaned[:3000]}")
                                    # Add to found_docs if not already there
                                    if filename not in seen_files:
                                        seen_files.add(filename)
                                        found_docs.append({
                                            "filename": filename,
                                            "snippet": cleaned[:300],
                                            "query": query,
                                            "match_type": "semantic"
                                        })
                except Exception as e:
                    logger.warning(f"Query failed: {e}")
        
        logger.info(f"[SCAN] Total unique docs found: {len(found_docs)}")
        
        # Determine findings and suggested status
        findings = None
        suggested_status = "not_started"
        
        # If we have docs OR inherited findings, we can analyze
        has_data = len(found_docs) > 0 or len(inherited_findings) > 0
        
        if has_data:
            suggested_status = "in_progress"
            
            # Use Claude with CONSULTATIVE context
            if all_content or inherited_findings:
                findings = await extract_findings_consultative(
                    action=action,
                    content=all_content[:15],
                    inherited_findings=inherited_findings,
                    action_id=action_id
                )
                if findings and findings.get('complete'):
                    suggested_status = "complete"
        
        # Update progress with scan results
        if project_id not in PLAYBOOK_PROGRESS:
            PLAYBOOK_PROGRESS[project_id] = {}
        
        PLAYBOOK_PROGRESS[project_id][action_id] = {
            "status": PLAYBOOK_PROGRESS.get(project_id, {}).get(action_id, {}).get("status", suggested_status),
            "findings": findings,
            "documents_found": [d['filename'] for d in found_docs],
            "inherited_from": parent_actions if parent_actions else None,
            "last_scan": datetime.now().isoformat(),
            "notes": PLAYBOOK_PROGRESS.get(project_id, {}).get(action_id, {}).get("notes")
        }
        
        # Persist to file
        save_progress(PLAYBOOK_PROGRESS)
        
        return {
            "found": len(found_docs) > 0,
            "documents": found_docs,
            "findings": findings,
            "suggested_status": suggested_status,
            "inherited_from": parent_actions if parent_actions else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Scan failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def extract_findings_consultative(
    action: Dict, 
    content: List[str], 
    inherited_findings: List[Dict],
    action_id: str
) -> Optional[Dict]:
    """
    Use Claude to extract findings WITH CONSULTATIVE ANALYSIS.
    
    Includes:
    - Industry benchmarks and comparisons
    - Red flag detection
    - Proactive recommendations
    - Inherited findings from parent actions
    """
    try:
        from anthropic import Anthropic
        
        client = Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))
        
        combined = "\n\n---\n\n".join(content)
        
        # Get action-specific consultative context
        consultative_context = CONSULTATIVE_PROMPTS.get(action_id, CONSULTATIVE_PROMPTS["DEFAULT"])
        
        # Build inherited findings context
        inherited_context = ""
        if inherited_findings:
            inherited_parts = []
            for inf in inherited_findings:
                parent_id = inf.get("action_id", "unknown")
                parent_findings = inf.get("findings", {})
                inherited_parts.append(f"""
--- Inherited from Action {parent_id} ---
Summary: {parent_findings.get('summary', 'N/A')}
Key Values: {json.dumps(parent_findings.get('key_values', {}), indent=2)}
Issues: {parent_findings.get('issues', [])}
""")
            inherited_context = "\n".join(inherited_parts)
        
        prompt = f"""You are a senior UKG implementation consultant performing Year-End analysis.

ACTION: {action['action_id']} - {action.get('description', '')}
REPORTS NEEDED: {', '.join(action.get('reports_needed', []))}

{f'''
INHERITED DATA FROM PREVIOUS ACTIONS:
{inherited_context}
''' if inherited_context else ''}

<documents>
{combined[:20000]}
</documents>

{consultative_context}

Based on the documents and your UKG/Payroll expertise, provide:

1. EXTRACT key data values found (FEIN, rates, states, etc.)
2. COMPARE to benchmarks where applicable (flag HIGH/LOW/UNUSUAL)
3. IDENTIFY risks, issues, or items needing attention
4. RECOMMEND specific actions the customer should take
5. ASSESS completeness - can this action be marked complete?

Return as JSON:
{{
    "complete": true/false,
    "key_values": {{"label": "value"}},
    "issues": ["list of concerns - be specific"],
    "recommendations": ["specific actions to take"],
    "risk_level": "low|medium|high",
    "summary": "2-3 sentence consultative summary with specific observations"
}}

Be specific and actionable. Reference actual values from the documents.
If rates are high/low compared to benchmarks, say so explicitly.
If data is missing, specify exactly what's needed.

Return ONLY valid JSON."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            temperature=0,
            messages=[{"role": "user", "content": prompt}]
        )
        
        text = response.content[0].text.strip()
        # Clean markdown
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()
        
        return json.loads(text)
        
    except Exception as e:
        logger.error(f"Failed to extract findings: {e}")
        return None


# Keep original function for backward compatibility
async def extract_findings_for_action(action: Dict, content: List[str]) -> Optional[Dict]:
    """Legacy function - redirects to consultative version."""
    return await extract_findings_consultative(action, content, [], action['action_id'])


# ============================================================================
# EXPORT ENDPOINT - Generate current-state workbook
# ============================================================================

@router.get("/year-end/export/{project_id}")
async def export_progress(project_id: str, customer_name: str = "Customer"):
    """Export current playbook progress as XLSX matching the XLR8 template."""
    
    structure = await get_year_end_structure()
    progress = PLAYBOOK_PROGRESS.get(project_id, {})
    
    wb = openpyxl.Workbook()
    
    # =========================================================================
    # STYLES - Matching template exactly
    # =========================================================================
    header_font = Font(bold=True, size=11, color="FFFFFF")
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    
    section_font = Font(bold=True, size=11, color="000000")
    section_fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")  # Light green for step sections
    
    best_practice_fill = PatternFill(start_color="FFCCCC", end_color="FFCCCC", fill_type="solid")  # Light pink
    
    critical_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")  # Red tint
    high_fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")  # Amber
    medium_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")  # Light green
    
    complete_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    in_progress_fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
    not_started_fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
    blocked_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
    
    normal_font = Font(size=10, color="000000")
    bold_font = Font(bold=True, size=10, color="000000")
    title_font = Font(bold=True, size=14, color="000000")
    
    thin_border = Border(
        left=Side(style='thin', color='CCCCCC'),
        right=Side(style='thin', color='CCCCCC'),
        top=Side(style='thin', color='CCCCCC'),
        bottom=Side(style='thin', color='CCCCCC')
    )
    
    wrap_align = Alignment(wrap_text=True, vertical='top')
    center_align = Alignment(horizontal='center', vertical='center')
    
    # =========================================================================
    # TAB 1: Before Final Payroll - Actions
    # =========================================================================
    ws1 = wb.active
    ws1.title = "Before Final Payroll - Actions"
    
    # Headers (15 columns matching template)
    headers = [
        "Action ID", "Step", "Type", "Description", "Due Date", "Owner", "Quarter-End",
        "Required Report(s)", "Report Uploaded?", "Report File Name(s)", "Analysis Tab",
        "Status", "Key Findings", "Issues Flagged", "Resolution/Notes"
    ]
    widths = [10, 8, 12, 60, 25, 20, 12, 45, 15, 50, 25, 18, 60, 45, 35]
    
    for col, header in enumerate(headers, 1):
        cell = ws1.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
        cell.alignment = center_align
    ws1.row_dimensions[1].height = 28.8
    
    for col, width in enumerate(widths, 1):
        ws1.column_dimensions[get_column_letter(col)].width = width
    
    ws1.freeze_panes = 'A2'
    
    # Best practice row
    row = 2
    ws1.cell(row=row, column=1, value="Best Practice: Generate W-2's in the Year-End Validation process before closing final payroll")
    ws1.merge_cells(start_row=row, start_column=1, end_row=row, end_column=15)
    ws1.cell(row=row, column=1).font = bold_font
    ws1.cell(row=row, column=1).fill = best_practice_fill
    
    row = 3
    current_step = None
    
    # Collect all issues for Critical Issues tab
    all_issues = []
    
    # Group actions by step and add section headers
    for step in structure.get('steps', []):
        if step.get('phase') != 'before_final_payroll':
            continue
            
        step_num = step['step_number']
        step_name = step['step_name']
        
        # Section header row
        section_text = f"Step {step_num}: {step_name}"
        ws1.cell(row=row, column=1, value=section_text)
        ws1.merge_cells(start_row=row, start_column=1, end_row=row, end_column=15)
        ws1.cell(row=row, column=1).font = section_font
        ws1.cell(row=row, column=1).fill = section_fill
        row += 1
        
        # Actions for this step
        for action in step.get('actions', []):
            action_id = action['action_id']
            action_progress = progress.get(action_id, {})
            
            status = action_progress.get('status', 'not_started')
            findings = action_progress.get('findings', {})
            docs_found = action_progress.get('documents_found', [])
            notes = action_progress.get('notes', '')
            
            # Determine analysis tab link
            analysis_tab = None
            if action_id.startswith('2D'):
                analysis_tab = 'Step 2D - WC Rates'
            elif action_id in ['2F', '2G', '2H']:
                analysis_tab = f'Step {action_id}'
            elif action_id == '2L':
                analysis_tab = 'Step 2L - Healthcare Audit'
            elif action_id == '5C':
                analysis_tab = 'Step 5C - Check Recon'
            elif action_id == '5D':
                analysis_tab = 'Step 5D - Arrears'
            elif action_id.startswith('2'):
                analysis_tab = 'Step 2 - Analysis & Findings'
            
            # Row data
            ws1.cell(row=row, column=1, value=action_id).font = bold_font
            ws1.cell(row=row, column=2, value=f"Step {step_num}")
            ws1.cell(row=row, column=3, value=action.get('action_type', 'Recommended').title())
            ws1.cell(row=row, column=4, value=action.get('description', '')).alignment = wrap_align
            ws1.cell(row=row, column=5, value=action.get('due_date', 'N/A') or 'N/A')
            ws1.cell(row=row, column=6, value='')  # Owner - to be filled by consultant
            ws1.cell(row=row, column=7, value='Yes' if action.get('quarter_end') else 'No')
            ws1.cell(row=row, column=8, value=', '.join(action.get('reports_needed', [])) or 'N/A').alignment = wrap_align
            ws1.cell(row=row, column=9, value='Yes' if docs_found else 'No')
            ws1.cell(row=row, column=10, value=', '.join(docs_found[:3]) if docs_found else '').alignment = wrap_align
            ws1.cell(row=row, column=11, value=analysis_tab or '')
            
            # Status with color
            status_cell = ws1.cell(row=row, column=12, value=status.replace('_', ' ').title())
            if status == 'complete':
                status_cell.fill = complete_fill
            elif status == 'in_progress':
                status_cell.fill = in_progress_fill
            elif status == 'blocked':
                status_cell.fill = blocked_fill
            else:
                status_cell.fill = not_started_fill
            
            # Findings
            key_findings = findings.get('summary', '') if findings else ''
            ws1.cell(row=row, column=13, value=key_findings).alignment = wrap_align
            
            # Issues
            issues_text = ''
            if findings and findings.get('issues'):
                issues_text = '\n'.join(findings.get('issues', []))
                # Collect for Critical Issues tab
                for issue in findings.get('issues', []):
                    all_issues.append({
                        'action_id': action_id,
                        'description': action.get('description', '')[:100],
                        'issue': issue,
                        'due_date': action.get('due_date', ''),
                        'priority': 'HIGH'  # Default, could be smarter
                    })
            ws1.cell(row=row, column=14, value=issues_text).alignment = wrap_align
            
            # Notes
            ws1.cell(row=row, column=15, value=notes or '').alignment = wrap_align
            
            # Apply borders
            for col in range(1, 16):
                ws1.cell(row=row, column=col).border = thin_border
            
            ws1.row_dimensions[row].height = 43.2
            row += 1
    
    # =========================================================================
    # TAB 2: Critical Issues Summary
    # =========================================================================
    ws2 = wb.create_sheet("Critical Issues Summary")
    
    issue_headers = ["Priority", "Issue", "Action ID", "Amount/Impact", "Action Required", "Owner", "Due Date", "Status"]
    for col, header in enumerate(issue_headers, 1):
        cell = ws2.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
    
    row = 2
    for issue in all_issues:
        priority = issue.get('priority', 'HIGH')
        priority_text = f"🔴 CRITICAL" if priority == 'CRITICAL' else f"🟠 HIGH" if priority == 'HIGH' else "🟡 MEDIUM"
        
        ws2.cell(row=row, column=1, value=priority_text)
        ws2.cell(row=row, column=2, value=issue.get('issue', '')).alignment = wrap_align
        ws2.cell(row=row, column=3, value=issue.get('action_id', ''))
        ws2.cell(row=row, column=4, value='')  # Amount/Impact - from findings
        ws2.cell(row=row, column=5, value='Review and resolve').alignment = wrap_align
        ws2.cell(row=row, column=6, value='')  # Owner
        ws2.cell(row=row, column=7, value=issue.get('due_date', ''))
        ws2.cell(row=row, column=8, value='Open')
        
        # Color row by priority
        fill = critical_fill if priority == 'CRITICAL' else high_fill if priority == 'HIGH' else medium_fill
        for col in range(1, 9):
            ws2.cell(row=row, column=col).fill = fill
            ws2.cell(row=row, column=col).border = thin_border
        
        row += 1
    
    if row == 2:
        ws2.cell(row=2, column=1, value="No critical issues identified yet - run document scans to detect issues")
        ws2.merge_cells('A2:H2')
        ws2.cell(row=2, column=1).font = Font(italic=True, color="666666")
    
    ws2.column_dimensions['A'].width = 15
    ws2.column_dimensions['B'].width = 50
    ws2.column_dimensions['C'].width = 12
    ws2.column_dimensions['D'].width = 25
    ws2.column_dimensions['E'].width = 40
    ws2.column_dimensions['F'].width = 20
    ws2.column_dimensions['G'].width = 18
    ws2.column_dimensions['H'].width = 12
    
    # =========================================================================
    # TAB 3: Uploaded Files Reference
    # =========================================================================
    ws3 = wb.create_sheet("Uploaded Files Reference")
    
    file_headers = ["File Name", "File Type", "Step/Action", "Description", "Upload Date", "Records/Pages", "Analysis Tab", "Status"]
    for col, header in enumerate(file_headers, 1):
        cell = ws3.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
    
    # Collect all docs found across all actions
    row = 2
    seen_files = set()
    for action_id, action_prog in progress.items():
        docs = action_prog.get('documents_found', [])
        for doc in docs:
            if doc not in seen_files:
                seen_files.add(doc)
                ws3.cell(row=row, column=1, value=doc)
                # Infer file type from extension
                ext = doc.split('.')[-1].upper() if '.' in doc else 'Unknown'
                ws3.cell(row=row, column=2, value=ext)
                ws3.cell(row=row, column=3, value=action_id)
                ws3.cell(row=row, column=4, value='')  # Description
                ws3.cell(row=row, column=5, value=datetime.now().strftime('%m/%d/%Y'))
                ws3.cell(row=row, column=6, value='')  # Records
                ws3.cell(row=row, column=7, value='')  # Analysis tab
                ws3.cell(row=row, column=8, value='Processed')
                
                for col in range(1, 9):
                    ws3.cell(row=row, column=col).border = thin_border
                row += 1
    
    if row == 2:
        ws3.cell(row=2, column=1, value="No files uploaded yet - use Upload Document in the playbook to add files")
        ws3.merge_cells('A2:H2')
        ws3.cell(row=2, column=1).font = Font(italic=True, color="666666")
    
    ws3.column_dimensions['A'].width = 45
    ws3.column_dimensions['B'].width = 12
    ws3.column_dimensions['C'].width = 15
    ws3.column_dimensions['D'].width = 40
    ws3.column_dimensions['E'].width = 15
    ws3.column_dimensions['F'].width = 15
    ws3.column_dimensions['G'].width = 25
    ws3.column_dimensions['H'].width = 12
    
    # =========================================================================
    # TAB 4: Key Deadlines
    # =========================================================================
    ws4 = wb.create_sheet("Key Deadlines")
    
    deadline_headers = ["Date", "Day", "Deadline", "Related Actions", "Status"]
    for col, header in enumerate(deadline_headers, 1):
        cell = ws4.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
    
    # Extract deadlines from structure
    deadlines = []
    for step in structure.get('steps', []):
        for action in step.get('actions', []):
            due = action.get('due_date')
            if due and due != 'N/A':
                deadlines.append({
                    'date': due,
                    'action_id': action['action_id'],
                    'description': action.get('description', '')[:60]
                })
    
    row = 2
    for dl in deadlines:
        ws4.cell(row=row, column=1, value=dl['date'])
        ws4.cell(row=row, column=2, value='')  # Day - would need date parsing
        ws4.cell(row=row, column=3, value=dl['description'])
        ws4.cell(row=row, column=4, value=dl['action_id'])
        
        # Check if action is complete
        action_status = progress.get(dl['action_id'], {}).get('status', 'not_started')
        status_text = 'Complete' if action_status == 'complete' else 'Upcoming'
        ws4.cell(row=row, column=5, value=status_text)
        
        for col in range(1, 6):
            ws4.cell(row=row, column=col).border = thin_border
        row += 1
    
    ws4.column_dimensions['A'].width = 15
    ws4.column_dimensions['B'].width = 8
    ws4.column_dimensions['C'].width = 60
    ws4.column_dimensions['D'].width = 20
    ws4.column_dimensions['E'].width = 15
    
    # =========================================================================
    # TAB 5: Step 2 - Analysis & Findings
    # =========================================================================
    ws5 = wb.create_sheet("Step 2 - Analysis & Findings")
    
    ws5.cell(row=1, column=1, value="STEP 2 - ANALYSIS & FINDINGS").font = title_font
    ws5.cell(row=2, column=1, value="Company Tax Verification and Profile Analysis")
    ws5.cell(row=3, column=1, value=f"Report Date: {datetime.now().strftime('%B %d, %Y')}")
    
    # Populate from Step 2 action findings
    row = 5
    ws5.cell(row=row, column=1, value="COMPANY INFORMATION").font = bold_font
    row += 1
    
    # Pull from 2A findings if available
    step2a_findings = progress.get('2A', {}).get('findings', {})
    if step2a_findings:
        key_vals = step2a_findings.get('key_values', {})
        for label, value in key_vals.items():
            ws5.cell(row=row, column=1, value=f"{label}:")
            ws5.cell(row=row, column=2, value=str(value))
            row += 1
        
        if step2a_findings.get('summary'):
            row += 1
            ws5.cell(row=row, column=1, value="SUMMARY").font = bold_font
            row += 1
            ws5.cell(row=row, column=1, value=step2a_findings.get('summary', ''))
            row += 1
        
        if step2a_findings.get('issues'):
            row += 1
            ws5.cell(row=row, column=1, value="ISSUES IDENTIFIED").font = bold_font
            row += 1
            for issue in step2a_findings.get('issues', []):
                ws5.cell(row=row, column=1, value=f"⚠️ {issue}")
                row += 1
    else:
        ws5.cell(row=row, column=1, value="Run 'Scan Documents' on Step 2A to populate this analysis")
        ws5.cell(row=row, column=1).font = Font(italic=True, color="666666")
    
    ws5.column_dimensions['A'].width = 40
    ws5.column_dimensions['B'].width = 60
    
    # =========================================================================
    # TAB 6-14: Step-specific analysis tabs (placeholders that grow)
    # =========================================================================
    analysis_tabs = [
        ("Step 2D - WC Rates", "2D", "Workers Compensation Risk Rates Analysis"),
        ("Step 2F - Earnings", "2F", "Earnings Code Analysis"),
        ("Step 2F - Exceptions", "2F", "Earnings Tax Category Exceptions"),
        ("Step 2F - Tax Categories", "2F", "Earnings Tax Categories"),
        ("Step 2G - Deductions", "2G", "Deduction Code Analysis"),
        ("Step 2G - US Ded Codes", "2G", "US Deduction Codes"),
        ("Step 2L - Healthcare Audit", "2L", "Healthcare Benefits Audit"),
        ("Step 5C - Check Recon", "5C", "Outstanding Checks Reconciliation"),
        ("Step 5D - Arrears", "5D", "Arrears Analysis"),
    ]
    
    for tab_name, action_id, title in analysis_tabs:
        ws = wb.create_sheet(tab_name)
        ws.cell(row=1, column=1, value=title.upper()).font = title_font
        ws.cell(row=2, column=1, value=f"Report Date: {datetime.now().strftime('%B %d, %Y')}")
        
        action_findings = progress.get(action_id, {}).get('findings', {})
        
        row = 4
        if action_findings:
            if action_findings.get('summary'):
                ws.cell(row=row, column=1, value="SUMMARY").font = bold_font
                row += 1
                ws.cell(row=row, column=1, value=action_findings.get('summary', ''))
                row += 2
            
            key_vals = action_findings.get('key_values', {})
            if key_vals:
                ws.cell(row=row, column=1, value="KEY FINDINGS").font = bold_font
                row += 1
                for label, value in key_vals.items():
                    ws.cell(row=row, column=1, value=f"{label}:")
                    ws.cell(row=row, column=2, value=str(value))
                    row += 1
            
            if action_findings.get('issues'):
                row += 1
                ws.cell(row=row, column=1, value="ISSUES").font = bold_font
                row += 1
                for issue in action_findings.get('issues', []):
                    ws.cell(row=row, column=1, value=f"⚠️ {issue}")
                    row += 1
        else:
            ws.cell(row=row, column=1, value=f"Run 'Scan Documents' on action {action_id} to populate this analysis")
            ws.cell(row=row, column=1).font = Font(italic=True, color="666666")
        
        ws.column_dimensions['A'].width = 50
        ws.column_dimensions['B'].width = 60
    
    # =========================================================================
    # Save and return
    # =========================================================================
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    filename = f"{customer_name.replace(' ', '_')}_Year_End_Checklist_{datetime.now().strftime('%Y%m%d')}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


# ============================================================================
# UPLOAD PLAYBOOK DOC - Parse and cache new structure
# ============================================================================

@router.post("/year-end/upload-definition")
async def upload_playbook_definition(file: UploadFile = File(...)):
    """Upload a new Year-End Checklist document to parse as playbook definition."""
    global PLAYBOOK_CACHE
    
    if not file.filename.endswith('.docx'):
        raise HTTPException(status_code=400, detail="File must be a .docx document")
    
    try:
        from backend.utils.playbook_parser import parse_year_end_checklist
        import tempfile
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        # Parse
        structure = parse_year_end_checklist(tmp_path)
        
        # Cache it
        PLAYBOOK_CACHE['year-end-2025'] = structure
        
        # Clean up
        os.unlink(tmp_path)
        
        return {
            "success": True,
            "title": structure['title'],
            "total_actions": structure['total_actions'],
            "steps": len(structure['steps'])
        }
        
    except Exception as e:
        logger.exception(f"Failed to parse playbook: {e}")
        raise HTTPException(status_code=500, detail=str(e))
