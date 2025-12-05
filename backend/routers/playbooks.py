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
import threading
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

# Track file modification time for auto-refresh
PLAYBOOK_FILE_INFO = {}


def invalidate_year_end_cache():
    """
    Invalidate the Year-End structure cache.
    Called when a new Year-End Checklist is uploaded to Global Library.
    """
    global PLAYBOOK_CACHE, PLAYBOOK_FILE_INFO
    
    if 'year-end-2025' in PLAYBOOK_CACHE:
        del PLAYBOOK_CACHE['year-end-2025']
        logger.info("[CACHE] Year-End structure cache invalidated")
    
    if 'year-end-2025' in PLAYBOOK_FILE_INFO:
        del PLAYBOOK_FILE_INFO['year-end-2025']
        logger.info("[CACHE] Year-End file info cleared")

# =============================================================================
# ACTION DEPENDENCIES - Which actions inherit from which
# =============================================================================
# DYNAMIC DEPENDENCIES - Built from structure, not hardcoded
# =============================================================================
# Dependencies are inferred at runtime based on:
# 1. Actions WITHOUT reports_needed depend on prior action in same step WITH reports_needed
# 2. Actions that reference similar keywords/reports are grouped

def build_action_dependencies(structure: dict) -> dict:
    """
    Dynamically build action dependencies from the playbook structure.
    
    Logic: Within each step, actions without reports_needed depend on 
    the first action in that step that HAS reports_needed.
    """
    dependencies = {}
    
    for step in structure.get('steps', []):
        actions = step.get('actions', [])
        
        # Find the first action with reports_needed (the "primary" action)
        primary_action = None
        for action in actions:
            if action.get('reports_needed'):
                primary_action = action['action_id']
                break
        
        if not primary_action:
            continue
            
        # All other actions in this step without reports_needed depend on primary
        for action in actions:
            action_id = action['action_id']
            if action_id != primary_action and not action.get('reports_needed'):
                dependencies[action_id] = [primary_action]
    
    return dependencies


def build_reverse_dependencies(dependencies: dict) -> dict:
    """Build reverse lookup: which actions are impacted when this action changes"""
    reverse = {}
    for dependent, parents in dependencies.items():
        for parent in parents:
            if parent not in reverse:
                reverse[parent] = []
            reverse[parent].append(dependent)
    return reverse


def build_required_documents(structure: dict) -> dict:
    """
    Dynamically build required documents list from structure.
    Groups actions by their reports_needed.
    """
    documents = {}
    
    for step in structure.get('steps', []):
        for action in step.get('actions', []):
            reports = action.get('reports_needed', [])
            action_id = action['action_id']
            
            for report in reports:
                # Normalize report name
                report_key = report.strip()
                if not report_key:
                    continue
                    
                if report_key not in documents:
                    documents[report_key] = {
                        "actions": [],
                        "keywords": [report_key.lower()],
                        "required": action.get('action_type') == 'required',
                        "description": f"Report needed for Year-End processing"
                    }
                
                if action_id not in documents[report_key]["actions"]:
                    documents[report_key]["actions"].append(action_id)
    
    return documents


# Placeholder - will be populated when structure is loaded
ACTION_DEPENDENCIES = {}
REVERSE_DEPENDENCIES = {}
REQUIRED_DOCUMENTS = {}

# =============================================================================
# ACTION-SPECIFIC GUIDANCE - For dependent actions (no scan, just guidance)
# =============================================================================
DEPENDENT_ACTION_GUIDANCE = {
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
    
    PRIMARY: Reads from DuckDB (Global structured data)
    FALLBACK: Reads from file if DuckDB doesn't have it
    
    Auto-caches for performance.
    Also builds dynamic dependencies from the structure.
    """
    global PLAYBOOK_CACHE, PLAYBOOK_FILE_INFO, ACTION_DEPENDENCIES, REVERSE_DEPENDENCIES, REQUIRED_DOCUMENTS, REPORT_TO_ACTIONS
    
    # Check cache first
    if 'year-end-2025' in PLAYBOOK_CACHE:
        cached = PLAYBOOK_CACHE['year-end-2025']
        # If it came from DuckDB, trust it (no file to check)
        if cached.get('source_type') == 'duckdb':
            return cached
        
        # If from file, check if file changed
        cached_info = PLAYBOOK_FILE_INFO.get('year-end-2025', {})
        cached_path = cached_info.get('path')
        cached_mtime = cached_info.get('mtime')
        
        if cached_path and os.path.exists(cached_path):
            current_mtime = os.path.getmtime(cached_path)
            if cached_mtime == current_mtime:
                return cached
            else:
                logger.info(f"[STRUCTURE] Source file modified, refreshing cache")
                invalidate_year_end_cache()
        else:
            return cached
    
    # Parse from DuckDB (primary) or file (fallback)
    try:
        from backend.utils.playbook_parser import parse_year_end_checklist
        
        logger.info("[STRUCTURE] Parsing Year-End Checklist...")
        structure = parse_year_end_checklist()
        
        # BUILD DYNAMIC DEPENDENCIES from the structure
        ACTION_DEPENDENCIES = build_action_dependencies(structure)
        REVERSE_DEPENDENCIES = build_reverse_dependencies(ACTION_DEPENDENCIES)
        REQUIRED_DOCUMENTS = build_required_documents(structure)
        REPORT_TO_ACTIONS = build_report_to_actions(structure)
        
        logger.info(f"[STRUCTURE] Built {len(ACTION_DEPENDENCIES)} dependencies, {len(REQUIRED_DOCUMENTS)} document types, {len(REPORT_TO_ACTIONS)} keyword mappings")
        
        # Cache the result
        PLAYBOOK_CACHE['year-end-2025'] = structure
        PLAYBOOK_FILE_INFO['year-end-2025'] = {
            'source_type': structure.get('source_type', 'unknown'),
            'parsed_at': datetime.now().isoformat()
        }
        
        logger.info(f"[STRUCTURE] Loaded {structure.get('total_actions', 0)} actions from {structure.get('source_type', 'unknown')}")
        return structure
        
    except Exception as e:
        logger.exception(f"[STRUCTURE] Error parsing Year-End doc: {e}")
        return get_default_year_end_structure()


@router.post("/year-end/refresh-structure")
async def refresh_year_end_structure():
    """
    Force re-parse of Year-End Checklist structure.
    Clears cache and re-reads from DuckDB.
    """
    global PLAYBOOK_CACHE, PLAYBOOK_FILE_INFO
    
    # Clear cache
    if 'year-end-2025' in PLAYBOOK_CACHE:
        del PLAYBOOK_CACHE['year-end-2025']
    if 'year-end-2025' in PLAYBOOK_FILE_INFO:
        del PLAYBOOK_FILE_INFO['year-end-2025']
    logger.info("[STRUCTURE] Cleared Year-End structure cache")
    
    # Re-parse
    structure = await get_year_end_structure()
    
    return {
        "success": True,
        "message": f"Structure refreshed from {structure.get('source_type', 'unknown')}",
        "total_actions": structure.get('total_actions', 0),
        "source_file": structure.get('source_file', 'default'),
        "source_type": structure.get('source_type', 'unknown')
    }


@router.get("/year-end/debug-duckdb")
async def debug_duckdb():
    """
    Debug endpoint to see what's in DuckDB _schema_metadata.
    Call: GET /playbooks/year-end/debug-duckdb
    """
    import duckdb
    
    DUCKDB_PATH = "/data/structured_data.duckdb"
    
    result = {
        "duckdb_exists": os.path.exists(DUCKDB_PATH),
        "duckdb_path": DUCKDB_PATH,
        "all_tables": [],
        "global_tables": [],
        "year_end_tables": [],
        "schema_metadata_exists": False,
        "raw_metadata": []
    }
    
    if not os.path.exists(DUCKDB_PATH):
        return result
    
    try:
        conn = duckdb.connect(DUCKDB_PATH)
        
        # Check what tables exist
        try:
            tables = conn.execute("SHOW TABLES").fetchall()
            result["all_tables"] = [t[0] for t in tables]
            result["schema_metadata_exists"] = "_schema_metadata" in result["all_tables"]
        except Exception as e:
            result["tables_error"] = str(e)
        
        # If schema_metadata exists, query it
        if result["schema_metadata_exists"]:
            try:
                # Get ALL metadata entries
                all_rows = conn.execute("""
                    SELECT project, file_name, sheet_name, table_name, row_count, is_current
                    FROM _schema_metadata
                    ORDER BY project, file_name, sheet_name
                """).fetchall()
                
                result["raw_metadata"] = [
                    {
                        "project": row[0],
                        "file_name": row[1],
                        "sheet_name": row[2],
                        "table_name": row[3],
                        "row_count": row[4],
                        "is_current": row[5]
                    }
                    for row in all_rows
                ]
                
                # Filter for global
                for row in result["raw_metadata"]:
                    proj = (row["project"] or "").lower()
                    if 'global' in proj:
                        result["global_tables"].append(row)
                
                # Filter for year-end keywords
                for row in result["raw_metadata"]:
                    fn = (row["file_name"] or "").lower()
                    if 'year' in fn or 'checklist' in fn or 'pro_pay' in fn:
                        result["year_end_tables"].append(row)
                        
            except Exception as e:
                result["query_error"] = str(e)
        
        conn.close()
        
    except Exception as e:
        result["connection_error"] = str(e)
    
    return result


@router.get("/year-end/debug-table-data")
async def debug_table_data():
    """
    Debug endpoint to see actual column names and sample data from Year-End tables.
    """
    import duckdb
    
    DUCKDB_PATH = "/data/structured_data.duckdb"
    
    result = {
        "before_final_payroll": {"columns": [], "sample_rows": [], "error": None},
        "after_final_payroll": {"columns": [], "sample_rows": [], "error": None}
    }
    
    if not os.path.exists(DUCKDB_PATH):
        return {"error": "DuckDB not found"}
    
    try:
        conn = duckdb.connect(DUCKDB_PATH)
        
        # Query Before Final Payroll table
        try:
            # Get columns
            cols = conn.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'global__pro_pay_yearend_checklist_usa_payment_services_worksheet_1__before_final_payroll'
            """).fetchall()
            result["before_final_payroll"]["columns"] = [c[0] for c in cols]
            
            # Get sample data
            rows = conn.execute("""
                SELECT * FROM global__pro_pay_yearend_checklist_usa_payment_services_worksheet_1__before_final_payroll
                LIMIT 10
            """).fetchall()
            
            # Convert to list of dicts
            col_names = result["before_final_payroll"]["columns"]
            result["before_final_payroll"]["sample_rows"] = [
                {col_names[i]: str(row[i])[:200] for i in range(len(col_names))} 
                for row in rows
            ]
        except Exception as e:
            result["before_final_payroll"]["error"] = str(e)
        
        # Query After Final Payroll table
        try:
            cols = conn.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'global__pro_pay_yearend_checklist_usa_payment_services_worksheet_1__after_final_payroll'
            """).fetchall()
            result["after_final_payroll"]["columns"] = [c[0] for c in cols]
            
            rows = conn.execute("""
                SELECT * FROM global__pro_pay_yearend_checklist_usa_payment_services_worksheet_1__after_final_payroll
                LIMIT 10
            """).fetchall()
            
            col_names = result["after_final_payroll"]["columns"]
            result["after_final_payroll"]["sample_rows"] = [
                {col_names[i]: str(row[i])[:200] for i in range(len(col_names))} 
                for row in rows
            ]
        except Exception as e:
            result["after_final_payroll"]["error"] = str(e)
        
        conn.close()
        
    except Exception as e:
        result["connection_error"] = str(e)
    
    return result


@router.get("/year-end/debug-parser")
async def debug_parser():
    """
    Debug endpoint to test the parser directly and see any errors.
    """
    import traceback
    
    result = {
        "success": False,
        "error": None,
        "traceback": None,
        "structure": None,
        "encryption_key_exists": False,
        "duckdb_exists": False
    }
    
    # Check prerequisites
    result["duckdb_exists"] = os.path.exists("/data/structured_data.duckdb")
    result["encryption_key_exists"] = os.path.exists("/data/.encryption_key_v2")
    
    try:
        from backend.utils.playbook_parser import parse_year_end_checklist
        
        structure = parse_year_end_checklist()
        result["success"] = True
        result["structure"] = {
            "total_actions": structure.get("total_actions", 0),
            "source_type": structure.get("source_type", "unknown"),
            "source_file": structure.get("source_file", "unknown"),
            "step_count": len(structure.get("steps", [])),
            "first_action": structure.get("steps", [{}])[0].get("actions", [{}])[0] if structure.get("steps") else None
        }
    except Exception as e:
        result["error"] = str(e)
        result["traceback"] = traceback.format_exc()
    
    return result
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
    
    # Get previous state for learning
    previous_status = None
    previous_findings = None
    if project_id in PLAYBOOK_PROGRESS and action_id in PLAYBOOK_PROGRESS[project_id]:
        previous = PLAYBOOK_PROGRESS[project_id][action_id]
        previous_status = previous.get('status')
        previous_findings = previous.get('findings')
    
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
    
    # ==========================================================================
    # LEARNING: Record user corrections for self-improvement
    # ==========================================================================
    try:
        from backend.utils.learning_engine import get_learning_system
        learning = get_learning_system()
        
        # Status change = user correcting AI suggestion
        if previous_status and previous_status != update.status:
            learning.record_feedback(
                action_id=action_id,
                correction_type='status',
                original_value=previous_status,
                corrected_value=update.status,
                context=f"Project {project_id}"
            )
            logger.info(f"[LEARNING] Recorded status correction: {action_id} {previous_status} → {update.status}")
        
        # Check for removed issues (false positives)
        if previous_findings and update.findings:
            prev_issues = set(previous_findings.get('issues', []) if isinstance(previous_findings.get('issues'), list) else [])
            new_issues = set(update.findings.get('issues', []) if isinstance(update.findings.get('issues'), list) else [])
            
            removed_issues = prev_issues - new_issues
            for issue in removed_issues:
                learning.record_feedback(
                    action_id=action_id,
                    correction_type='issue_removed',
                    original_value=issue,
                    corrected_value=None,
                    context=f"User removed this issue from {action_id}"
                )
                logger.info(f"[LEARNING] Recorded false positive: {issue[:50]}...")
            
            # Check for added issues (AI missed these)
            added_issues = new_issues - prev_issues
            for issue in added_issues:
                learning.record_feedback(
                    action_id=action_id,
                    correction_type='issue_added',
                    original_value=None,
                    corrected_value=issue,
                    context=f"User added this issue to {action_id}"
                )
                logger.info(f"[LEARNING] Recorded missed issue: {issue[:50]}...")
                
    except ImportError:
        pass  # Learning system not available
    except Exception as e:
        logger.warning(f"[LEARNING] Failed to record feedback: {e}")
    
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
# LEARNING STATS ENDPOINT - Monitor AI self-improvement
# ============================================================================

@router.get("/year-end/learning-stats")
async def get_learning_stats():
    """
    Get statistics about the learning system.
    
    Shows:
    - Training data collected (for fine-tuning)
    - Cache hit rate (Claude calls saved)
    - Feedback patterns learned
    - Rules auto-generated
    """
    try:
        from backend.utils.learning_engine import get_learning_system
        from backend.utils.hybrid_analyzer import get_hybrid_analyzer
        
        learning = get_learning_system()
        analyzer = get_hybrid_analyzer()
        
        return {
            "success": True,
            "learning": learning.get_stats(),
            "analyzer": analyzer.get_stats(),
            "message": "Learning system active"
        }
    except ImportError as e:
        return {
            "success": False,
            "error": f"Learning system not available: {e}",
            "message": "Deploy learning_engine.py and hybrid_analyzer.py"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================================
# SCAN ENDPOINT - Search docs for action-relevant content
# ============================================================================

@router.post("/year-end/scan/{project_id}/{action_id}")
async def scan_for_action(project_id: str, action_id: str):
    """
    Scan project documents for content relevant to a specific action.
    
    ENHANCED FEATURES:
    - Inherits documents/findings from parent actions (no re-upload needed)
    - For DEPENDENT actions: Skip redundant scan, provide guidance only
    - Uses consultative AI with industry benchmarks
    - Detects conflicts with existing data
    - Flags impacted actions when new data arrives
    - Auto-completes when all conditions met
    """
    logger.warning(f"[SCAN] === Starting scan for action {action_id} in project {project_id[:8]} ===")
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
            logger.warning(f"[SCAN] Action {action_id} NOT FOUND in structure")
            raise HTTPException(status_code=404, detail=f"Action {action_id} not found")
        
        logger.warning(f"[SCAN] Found action {action_id}: {action.get('description', 'no desc')[:50]}")
        
        # Get reports needed for this action
        reports_needed = action.get('reports_needed', [])
        
        # Get parent actions
        parent_actions = get_parent_actions(action_id)
        
        # =====================================================================
        # DEPENDENT ACTION HANDLING - Still scan but include parent context
        # =====================================================================
        if parent_actions:
            logger.warning(f"[SCAN] Action {action_id} has parent actions {parent_actions} - will include their context")
        
        logger.warning(f"[SCAN] Action {action_id} has {len(reports_needed)} reports_needed: {reports_needed[:3]}")
        
        # =====================================================================
        # STANDARD SCAN FOR ACTIONS WITH REPORTS_NEEDED
        # =====================================================================
        inherited = get_inherited_data(project_id, action_id)
        inherited_docs = inherited["documents"]
        inherited_findings = inherited["findings"]
        inherited_content = inherited["content"]
        
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
        
        # STEP 1: Get project document filenames from ChromaDB AND DuckDB
        project_files = set()
        
        # SOURCE 1: ChromaDB
        try:
            collection = rag.client.get_or_create_collection(name="documents")
            all_results = collection.get(include=["metadatas"], limit=1000)
            
            for metadata in all_results.get("metadatas", []):
                doc_project = metadata.get("project_id") or metadata.get("project", "")
                doc_project_name = metadata.get("project") or ""
                
                # Include GLOBAL or this project
                is_global = doc_project_name.lower() in ('global', '__global__', 'global/universal')
                is_this_project = doc_project == project_id or doc_project == project_id[:8]
                
                if is_global or is_this_project:
                    filename = metadata.get("source", metadata.get("filename", ""))
                    if filename:
                        project_files.add(filename)
            
            logger.warning(f"[SCAN] ChromaDB: {len(project_files)} files")
            
        except Exception as e:
            logger.warning(f"[SCAN] ChromaDB query failed: {e}")
        
        # SOURCE 2: DuckDB _pdf_tables
        try:
            from backend.utils.playbook_parser import get_duckdb_connection
            conn = get_duckdb_connection()
            if conn:
                table_check = conn.execute("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_name = '_pdf_tables'
                """).fetchone()
                
                if table_check and table_check[0] > 0:
                    result = conn.execute("""
                        SELECT DISTINCT source_file, project
                        FROM _pdf_tables
                        WHERE source_file IS NOT NULL
                    """).fetchall()
                    
                    for row in result:
                        source_file, proj = row
                        # Include GLOBAL or this project
                        is_global = proj and proj.lower() in ('global', '__global__', 'global/universal')
                        is_this_project = proj and project_id[:8].lower() in proj.lower()
                        
                        if is_global or is_this_project:
                            if source_file:
                                project_files.add(source_file)
                    
                    logger.warning(f"[SCAN] DuckDB _pdf_tables: added files, total now {len(project_files)}")
                
                conn.close()
        except Exception as e:
            logger.warning(f"[SCAN] DuckDB query failed: {e}")
        
        logger.warning(f"[SCAN] Total {len(project_files)} files in project: {list(project_files)}")
        
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
                        logger.warning(f"[SCAN] Filename match: '{filename}' for report '{report_name}'")
        
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
        
        logger.warning(f"[SCAN] Total unique docs found: {len(found_docs)}")
        logger.warning(f"[SCAN] ChromaDB content chunks: {len(all_content)}")
        
        # =====================================================================
        # STEP 4: Get structured data from DuckDB _pdf_tables
        # This has the FULL extracted table data - PRIORITIZE THIS
        # =====================================================================
        duckdb_content = []  # Separate list for DuckDB data
        try:
            from backend.utils.playbook_parser import get_duckdb_connection
            conn = get_duckdb_connection()
            if conn:
                # Check if _pdf_tables exists
                table_check = conn.execute("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_name = '_pdf_tables'
                """).fetchone()
                
                if table_check and table_check[0] > 0:
                    # Get ALL tables for this project first
                    all_tables = conn.execute("""
                        SELECT table_name, columns, source_file
                        FROM _pdf_tables
                    """).fetchall()
                    
                    logger.warning(f"[SCAN] DuckDB has {len(all_tables)} tables total, project has {len(project_files)} files")
                    
                    seen_tables = set()  # Avoid duplicate table pulls
                    
                    # Get table names for ALL project files (not just found_docs)
                    # This ensures we have complete context for analysis
                    for filename in project_files:
                        if not filename:
                            continue
                        
                        # Normalize filename for matching (remove special chars)
                        filename_norm = filename.lower().replace("'", "").replace("'", "").replace(".pdf", "")
                        
                        # Find tables that match this file (flexible matching)
                        for table_name, columns_json, source_file in all_tables:
                            if not source_file or table_name in seen_tables:
                                continue
                            source_norm = source_file.lower().replace("'", "").replace("'", "").replace(".pdf", "")
                            
                            # Match if normalized names are similar
                            if filename_norm in source_norm or source_norm in filename_norm:
                                seen_tables.add(table_name)
                                try:
                                    # Get ALL data from the table (no limit)
                                    data = conn.execute(f'SELECT * FROM "{table_name}"').fetchall()
                                    columns = json.loads(columns_json) if columns_json else []
                                    
                                    if data and columns:
                                        # Format as compact CSV-style (much smaller than dict format)
                                        content_lines = [f"[FILE: {filename}] [TABLE: {table_name}] [{len(data)} rows]"]
                                        content_lines.append("|".join(columns))  # Header row
                                        
                                        for row in data:  # ALL rows
                                            # Compact pipe-separated format
                                            row_vals = [str(row[i]) if row[i] else "" for i in range(min(len(columns), len(row)))]
                                            content_lines.append("|".join(row_vals))
                                        
                                        table_content = "\n".join(content_lines)
                                        duckdb_content.append(table_content)
                                        logger.warning(f"[SCAN] ✓ Added DuckDB table: {table_name} ({len(data)} rows) for '{filename}'")
                                        
                                        # Add to found_docs if not already there
                                        if filename not in seen_files:
                                            seen_files.add(filename)
                                            found_docs.append({
                                                "filename": filename,
                                                "snippet": f"Full table data from {table_name} ({len(data)} rows)",
                                                "query": "DuckDB",
                                                "match_type": "structured_data"
                                            })
                                except Exception as te:
                                    logger.warning(f"[SCAN] Error reading table {table_name}: {te}")
                
                conn.close()
        except Exception as e:
            logger.warning(f"[SCAN] DuckDB table content retrieval failed: {e}")
        
        # PRIORITIZE: DuckDB full data FIRST, then ChromaDB chunks
        # DuckDB has complete structured data, ChromaDB has truncated text chunks
        final_content = duckdb_content + all_content[:20]  # DuckDB first, then top 20 ChromaDB chunks
        
        # Log content sizes for debugging
        duckdb_chars = sum(len(c) for c in duckdb_content)
        chroma_chars = sum(len(c) for c in all_content[:20])
        logger.warning(f"[SCAN] Final content: {len(duckdb_content)} DuckDB ({duckdb_chars} chars) + {min(20, len(all_content))} ChromaDB ({chroma_chars} chars) = {len(final_content)} chunks")
        
        # Determine findings and suggested status
        findings = None
        suggested_status = "not_started"
        
        # If we have docs OR inherited findings, we can analyze
        has_data = len(found_docs) > 0 or len(inherited_findings) > 0 or len(final_content) > 0
        
        if has_data:
            suggested_status = "in_progress"
            logger.warning(f"[SCAN] Has data - calling AI for analysis...")
            
            # Use Claude with CONSULTATIVE context
            if final_content or inherited_findings:
                findings = await extract_findings_consultative(
                    action=action,
                    content=final_content,  # Full DuckDB + top ChromaDB chunks
                    inherited_findings=inherited_findings,
                    action_id=action_id
                )
                
                logger.warning(f"[SCAN] AI analysis complete. Findings: {bool(findings)}, keys: {list(findings.keys()) if findings else 'None'}")
                
                # NOTE: Removed auto-complete logic - users should manually mark as complete
                # Previously this would auto-mark as "complete" if AI said complete=True
        
        # =====================================================================
        # CONFLICT DETECTION - Check for inconsistencies
        # =====================================================================
        conflicts = await detect_conflicts(project_id, action_id, findings)
        if conflicts:
            findings = findings or {}
            findings['conflicts'] = conflicts
            if suggested_status == "complete":
                suggested_status = "in_progress"  # Don't auto-complete if conflicts exist
                logger.info(f"[SCAN] Conflicts detected - downgrading status to in_progress")
        
        # =====================================================================
        # IMPACT FLAGGING - Flag dependent actions if this data changes
        # =====================================================================
        await flag_impacted_actions(project_id, action_id, findings)
        
        # Update progress with scan results
        if project_id not in PLAYBOOK_PROGRESS:
            PLAYBOOK_PROGRESS[project_id] = {}
        
        # Preserve existing status if user manually set it, unless auto-completing
        existing_status = PLAYBOOK_PROGRESS.get(project_id, {}).get(action_id, {}).get("status")
        if existing_status and existing_status != "not_started":
            # Keep user's manual status unless we're auto-completing
            final_status = existing_status
        else:
            final_status = suggested_status
        
        PLAYBOOK_PROGRESS[project_id][action_id] = {
            "status": final_status,
            "findings": findings,
            "documents_found": [d['filename'] for d in found_docs],
            "inherited_from": parent_actions if parent_actions else None,
            "last_scan": datetime.now().isoformat(),
            "notes": PLAYBOOK_PROGRESS.get(project_id, {}).get(action_id, {}).get("notes"),
            "review_flag": None  # Clear review flag after scan
        }
        
        # Persist to file
        save_progress(PLAYBOOK_PROGRESS)
        
        return {
            "found": len(found_docs) > 0,
            "documents": found_docs,
            "findings": findings,
            "suggested_status": final_status,
            "inherited_from": parent_actions if parent_actions else None,
            "conflicts": conflicts
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Scan failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_dependent_action(
    project_id: str, 
    action_id: str, 
    action: Dict, 
    parent_actions: List[str]
) -> Dict:
    """
    Handle scan request for a DEPENDENT action.
    Instead of redundant scanning, provides:
    - Reference to parent action findings
    - Action-specific guidance
    - Appropriate status based on parent completion
    """
    logger.info(f"[DEPENDENT] Handling dependent action {action_id}")
    
    # Get parent progress
    progress = PLAYBOOK_PROGRESS.get(project_id, {})
    parent_findings = []
    parent_docs = []
    all_parents_complete = True
    primary_parent = parent_actions[0] if parent_actions else None
    
    for parent_id in parent_actions:
        parent_data = progress.get(parent_id, {})
        if parent_data.get("findings"):
            parent_findings.append({
                "action_id": parent_id,
                "findings": parent_data["findings"]
            })
        if parent_data.get("documents_found"):
            parent_docs.extend(parent_data["documents_found"])
        if parent_data.get("status") != "complete":
            all_parents_complete = False
    
    # Get action-specific guidance
    guidance = DEPENDENT_ACTION_GUIDANCE.get(action_id, f"Review findings from action(s) {', '.join(parent_actions)} and complete the tasks for this action.")
    
    # Build findings for this dependent action - ONLY show new/unique info
    findings = {
        "complete": all_parents_complete,  # Only complete if parents are complete
        "is_dependent": True,
        "parent_actions": parent_actions,
        "guidance": guidance,
        "key_values": {},
        "issues": [],
        "recommendations": [],
        "summary": f"Please see {primary_parent} response for document analysis. This action applies findings from {primary_parent}.",
        "risk_level": "low"
    }
    
    # DON'T copy issues/values from parent - just reference parent action
    # Only add action-specific notes if they exist
    if not all_parents_complete:
        findings["summary"] = f"Waiting on {primary_parent} to complete. Please scan {primary_parent} first."
        findings["issues"] = [f"Complete {primary_parent} before proceeding with {action_id}."]
    
    # Determine status
    if all_parents_complete:
        suggested_status = "in_progress"  # Ready to work on
    else:
        suggested_status = "blocked"  # Waiting on parents
    
    # Update progress
    if project_id not in PLAYBOOK_PROGRESS:
        PLAYBOOK_PROGRESS[project_id] = {}
    
    existing = PLAYBOOK_PROGRESS.get(project_id, {}).get(action_id, {})
    
    PLAYBOOK_PROGRESS[project_id][action_id] = {
        "status": existing.get("status") or suggested_status,
        "findings": findings,
        "documents_found": list(set(parent_docs)),  # Inherited docs
        "inherited_from": parent_actions,
        "last_scan": datetime.now().isoformat(),
        "notes": existing.get("notes"),
        "is_dependent": True
    }
    
    save_progress(PLAYBOOK_PROGRESS)
    
    return {
        "found": len(parent_docs) > 0,
        "documents": [{"filename": d, "match_type": "inherited", "snippet": f"From {primary_parent}"} for d in set(parent_docs)],
        "findings": findings,
        "suggested_status": suggested_status,
        "inherited_from": parent_actions,
        "is_dependent": True
    }


async def detect_conflicts(project_id: str, action_id: str, new_findings: Optional[Dict]) -> List[Dict]:
    """
    Detect conflicts between new findings and existing data.
    Returns list of conflict objects.
    """
    if not new_findings or not new_findings.get("key_values"):
        return []
    
    conflicts = []
    progress = PLAYBOOK_PROGRESS.get(project_id, {})
    new_values = new_findings.get("key_values", {})
    
    # Check against all other actions for conflicting values
    # Only flag conflicts for fields where a mismatch indicates real data problems
    # Company name variations are cosmetic - not worth flagging
    critical_fields = ["fein", "federal_futa_rate"]
    
    def normalize_value(field: str, value: str) -> str:
        """Normalize values for comparison to avoid false positives"""
        if not value:
            return ""
        val = str(value).strip()
        
        # Strip source citations like "(Source: filename.pdf)" or "(from filename)"
        val = re.sub(r'\s*\(Source:\s*[^)]+\)', '', val)
        val = re.sub(r'\s*\(from\s*[^)]+\)', '', val)
        val = val.strip()
        
        # FEIN: remove dashes, spaces, just keep digits
        if "fein" in field.lower() or "ein" in field.lower():
            return ''.join(c for c in val if c.isdigit())
        
        # Percentages: normalize to consistent decimal
        if "rate" in field.lower() or "%" in val:
            try:
                # Remove % sign and convert to float
                cleaned = val.replace('%', '').strip()
                num = float(cleaned)
                # Round to 4 decimal places for comparison
                return f"{num:.4f}"
            except (ValueError, TypeError):
                pass
        
        return val.lower()
    
    for other_action_id, other_progress in progress.items():
        if other_action_id == action_id:
            continue
        
        other_findings = other_progress.get("findings") if other_progress else None
        if not other_findings:
            continue
        other_values = other_findings.get("key_values", {}) if isinstance(other_findings, dict) else {}
        
        for field in critical_fields:
            # Normalize field names for comparison
            new_val = None
            other_val = None
            new_val_raw = None
            other_val_raw = None
            
            for k, v in new_values.items():
                if field.lower() in k.lower():
                    new_val_raw = str(v).strip()
                    new_val = normalize_value(field, new_val_raw)
                    break
            
            for k, v in other_values.items():
                if field.lower() in k.lower():
                    other_val_raw = str(v).strip()
                    other_val = normalize_value(field, other_val_raw)
                    break
            
            # Compare normalized values
            if new_val and other_val and new_val != other_val:
                conflicts.append({
                    "field": field,
                    "action_1": action_id,
                    "value_1": new_val_raw,
                    "action_2": other_action_id,
                    "value_2": other_val_raw,
                    "message": f"Conflicting {field}: '{new_val_raw}' (from {action_id}) vs '{other_val_raw}' (from {other_action_id})"
                })
                logger.warning(f"[CONFLICT] {conflicts[-1]['message']}")
    
    return conflicts


async def flag_impacted_actions(project_id: str, action_id: str, new_findings: Optional[Dict]):
    """
    When an action's data changes, flag dependent actions for review.
    Changes their status from 'complete' to 'in_progress' if they were marked complete.
    """
    if not new_findings:
        return
    
    # Get actions that depend on this one
    impacted = REVERSE_DEPENDENCIES.get(action_id, [])
    if not impacted:
        return
    
    progress = PLAYBOOK_PROGRESS.get(project_id, {})
    
    for dependent_id in impacted:
        dependent_progress = progress.get(dependent_id, {})
        
        # If dependent was marked complete, flag it for review
        if dependent_progress.get("status") == "complete":
            logger.info(f"[IMPACT] Flagging action {dependent_id} for review (impacted by {action_id})")
            
            PLAYBOOK_PROGRESS[project_id][dependent_id] = {
                **dependent_progress,
                "status": "in_progress",  # Downgrade from complete
                "review_flag": {
                    "reason": f"New data in {action_id} may affect this action",
                    "flagged_at": datetime.now().isoformat(),
                    "triggered_by": action_id
                }
            }
    
    save_progress(PLAYBOOK_PROGRESS)


async def extract_findings_consultative(
    action: Dict, 
    content: List[str], 
    inherited_findings: List[Dict],
    action_id: str
) -> Optional[Dict]:
    """
    HYBRID ANALYZER: Uses local LLM for extraction, Claude for complex analysis.
    
    Cost Reduction: 50-70% fewer Claude API calls
    
    Flow:
    1. Try local LLM extraction first (fast, free)
    2. If simple action + good extraction → return local result
    3. If complex action or issues found → call Claude
    """
    try:
        # Try hybrid approach first
        try:
            from backend.utils.hybrid_analyzer import get_hybrid_analyzer
            analyzer = get_hybrid_analyzer()
            
            result = await analyzer.analyze(action, content, inherited_findings)
            
            if result:
                # Log which method was used
                method = result.get('_analyzed_by', 'unknown')
                logger.info(f"[HYBRID] Action {action_id} analyzed by: {method}")
                
                # Get stats periodically
                stats = analyzer.get_stats()
                if stats['total_analyses'] > 0 and stats['total_analyses'] % 10 == 0:
                    logger.info(f"[HYBRID] Stats: {stats}")
                
                return result
                
        except ImportError as ie:
            logger.warning(f"[HYBRID] hybrid_analyzer import failed: {ie}")
            logger.warning("[HYBRID] Ensure hybrid_analyzer.py is in backend/utils/")
        except Exception as e:
            logger.warning(f"[HYBRID] Hybrid analysis failed: {e}, falling back to Claude-only")
            import traceback
            logger.warning(f"[HYBRID] Traceback: {traceback.format_exc()}")
        
        # FALLBACK: Original Claude-only approach
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

1. EXTRACT key data values found (FEIN in XX-XXXXXXX format, rates as percentages, states, etc.) - note which file each came from
2. COMPARE to benchmarks where applicable (flag HIGH/LOW/UNUSUAL)
3. IDENTIFY risks, issues, or items needing attention - cite the source document
4. RECOMMEND specific actions the customer should take
5. ASSESS completeness - can this action be marked complete?

IMPORTANT: 
- Each document chunk is labeled with [FILE: filename]. Include source citations.
- FEIN must be formatted as XX-XXXXXXX (e.g., 74-1776312)
- Rates should be percentages (e.g., 0.6%, 2.7%)

Return as JSON:
{{
    "complete": true/false,
    "key_values": {{"FEIN": "XX-XXXXXXX (from filename)", "other_field": "value (from filename)"}},
    "issues": ["Issue description (Source: filename)"],
    "recommendations": ["Specific action to take"],
    "risk_level": "low|medium|high",
    "summary": "2-3 sentence consultative summary with specific observations",
    "sources_used": ["list of filenames analyzed"]
}}

Be specific and actionable. Reference actual values from the documents.
Include "(Source: filename)" at the end of each issue when you can identify the source.
If rates are high/low compared to benchmarks, say so explicitly.
If data is missing, specify exactly what's needed.

Return ONLY valid JSON."""

        logger.info(f"[FALLBACK] Calling Claude directly for {action_id}")
        
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
        
        result = json.loads(text)
        result['_analyzed_by'] = 'claude_fallback'
        return result
        
    except Exception as e:
        logger.error(f"Failed to extract findings: {e}")
        return None


# Keep original function for backward compatibility
async def extract_findings_for_action(action: Dict, content: List[str]) -> Optional[Dict]:
    """Legacy function - redirects to consultative version."""
    return await extract_findings_consultative(action, content, [], action['action_id'])


# ============================================================================
# DOCUMENT CHECKLIST ENDPOINT - Shows all required docs and upload status
# ============================================================================

@router.get("/year-end/document-checklist/{project_id}")
async def get_document_checklist(project_id: str):
    """
    Get the document checklist with real-time upload status.
    Shows which reports are needed per step, matched vs missing.
    """
    try:
        from utils.rag_handler import RAGHandler
        from utils.database.models import ProcessingJobModel
        from backend.utils.playbook_parser import load_step_documents, match_documents_to_step, get_duckdb_connection
        
        uploaded_files_list = []
        seen_files = set()
        project_name = None
        
        # =====================================================================
        # SOURCE 1: ChromaDB (vector chunks)
        # =====================================================================
        try:
            rag = RAGHandler()
            collection = rag.client.get_or_create_collection(name="documents")
            all_results = collection.get(include=["metadatas"], limit=1000)
            
            for metadata in all_results.get("metadatas", []):
                doc_project_id = metadata.get("project_id", "")
                doc_project_name = metadata.get("project") or metadata.get("project_name", "")
                
                # Find project name for this project_id
                if not project_name and doc_project_id:
                    if doc_project_id == project_id or doc_project_id.startswith(project_id[:8]) or project_id.startswith(doc_project_id):
                        project_name = doc_project_name
                
                # Include GLOBAL files OR project-specific files
                is_global = doc_project_name and doc_project_name.lower() in ('global', '__global__', 'global/universal')
                is_this_project = (
                    (doc_project_id and (doc_project_id == project_id or doc_project_id.startswith(project_id[:8]) or project_id.startswith(doc_project_id))) or
                    (project_name and doc_project_name and doc_project_name.lower() == project_name.lower())
                )
                
                if is_global or is_this_project:
                    filename = metadata.get("source", metadata.get("filename", ""))
                    if filename and filename.lower() not in seen_files:
                        uploaded_files_list.append(filename)
                        seen_files.add(filename.lower())
            
            logger.info(f"[DOC-CHECKLIST] ChromaDB: {len(uploaded_files_list)} files for project {project_id[:8]} (includes GLOBAL)")
        except Exception as e:
            logger.warning(f"[DOC-CHECKLIST] ChromaDB query failed: {e}")
        
        # =====================================================================
        # SOURCE 2: DuckDB _schema_metadata (Excel files)
        # =====================================================================
        try:
            conn = get_duckdb_connection()
            if conn:
                # Get unique source files from _schema_metadata
                # Column is file_name, not source_file
                result = conn.execute("""
                    SELECT DISTINCT file_name, project
                    FROM _schema_metadata
                    WHERE file_name IS NOT NULL
                """).fetchall()
                
                logger.info(f"[DOC-CHECKLIST] DuckDB _schema_metadata returned {len(result)} rows")
                
                for row in result:
                    source_file, proj = row
                    # Include GLOBAL files OR project-specific files
                    is_global = proj and proj.lower() in ('global', '__global__', 'global/universal')
                    is_this_project = proj and (
                        proj.lower() in project_id.lower() or
                        project_id[:8].lower() in proj.lower() or
                        (project_name and proj.lower() == project_name.lower())
                    )
                    
                    if is_global or is_this_project:
                        if source_file and source_file.lower() not in seen_files:
                            uploaded_files_list.append(source_file)
                            seen_files.add(source_file.lower())
                            logger.info(f"[DOC-CHECKLIST] DuckDB Excel: {source_file} (project: {proj})")
                
                conn.close()
        except Exception as e:
            logger.warning(f"[DOC-CHECKLIST] DuckDB _schema_metadata query failed: {e}")
        
        # =====================================================================
        # SOURCE 3: DuckDB _pdf_tables (PDF files)
        # =====================================================================
        try:
            conn = get_duckdb_connection()
            if conn:
                # Check if _pdf_tables exists
                table_check = conn.execute("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_name = '_pdf_tables'
                """).fetchone()
                
                if table_check and table_check[0] > 0:
                    result = conn.execute("""
                        SELECT DISTINCT source_file, project, project_id
                        FROM _pdf_tables
                        WHERE source_file IS NOT NULL
                    """).fetchall()
                    
                    logger.info(f"[DOC-CHECKLIST] DuckDB _pdf_tables returned {len(result)} rows")
                    
                    for row in result:
                        source_file, proj, pid = row
                        # Include GLOBAL files OR project-specific files
                        is_global = proj and proj.lower() in ('global', '__global__', 'global/universal')
                        is_this_project = (
                            (pid and (pid == project_id or pid.startswith(project_id[:8]))) or
                            (proj and project_id[:8].lower() in proj.lower()) or
                            (proj and project_name and proj.lower() == project_name.lower())
                        )
                        
                        if is_global or is_this_project:
                            if source_file and source_file.lower() not in seen_files:
                                uploaded_files_list.append(source_file)
                                seen_files.add(source_file.lower())
                                logger.info(f"[DOC-CHECKLIST] DuckDB PDF: {source_file} (project: {proj})")
                
                conn.close()
        except Exception as e:
            logger.warning(f"[DOC-CHECKLIST] DuckDB _pdf_tables query failed: {e}")
        
        uploaded_files_list.sort()
        logger.info(f"[DOC-CHECKLIST] TOTAL: {len(uploaded_files_list)} files: {uploaded_files_list}")
        
        # Check for active processing jobs
        processing_jobs = []
        try:
            all_jobs = ProcessingJobModel.get_all(limit=20)
            for job in all_jobs:
                job_status = job.get("status", "")
                job_project = job.get("input_data", {}).get("project_id", "")
                if job_status in ["pending", "processing"] and job_project == project_id:
                    processing_jobs.append({
                        "filename": job.get("input_data", {}).get("filename", "Unknown"),
                        "progress": job.get("progress", 0),
                        "message": job.get("status_message", "Processing..."),
                        "job_id": job.get("id")
                    })
        except Exception as e:
            logger.warning(f"Could not fetch processing jobs: {e}")
        
        # =====================================================================
        # STEP-BASED DOCUMENT CHECKLIST (from Step_Documents sheet)
        # =====================================================================
        step_checklists = []
        has_step_documents = False
        total_matched = 0
        total_missing = 0
        required_missing = 0
        
        try:
            # Load Step_Documents from DuckDB
            step_documents = load_step_documents()
            
            # Get step names from structure
            step_names_map = {}
            try:
                from backend.utils.playbook_parser import parse_year_end_checklist
                structure = parse_year_end_checklist()
                for step in structure.get('steps', []):
                    step_names_map[step['step_number']] = step.get('step_name', f"Step {step['step_number']}")
            except Exception as e:
                logger.warning(f"[DOC-CHECKLIST] Could not load step names: {e}")
            
            if step_documents:
                has_step_documents = True
                logger.info(f"[DOC-CHECKLIST] Found Step_Documents for {len(step_documents)} steps")
                logger.info(f"[DOC-CHECKLIST] Files to match against: {uploaded_files_list}")
                
                # Build checklist for each step
                for step_num, docs in sorted(step_documents.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 999):
                    result = match_documents_to_step(docs, uploaded_files_list)
                    
                    # Use actual step name from structure, fallback to just the number
                    actual_step_name = step_names_map.get(step_num, "")
                    
                    step_checklists.append({
                        'step_number': step_num,
                        'step_name': actual_step_name,  # Just the name, no "Step X:" prefix
                        'matched': result['matched'],
                        'missing': result['missing'],
                        'stats': result['stats']
                    })
                    
                    total_matched += result['stats']['matched']
                    total_missing += result['stats']['missing']
                    required_missing += result['stats']['required_missing']
            else:
                logger.info("[DOC-CHECKLIST] No Step_Documents found - showing uploaded files only")
                
        except Exception as e:
            logger.warning(f"[DOC-CHECKLIST] Could not load Step_Documents: {e}")
        
        return {
            "project_id": project_id,
            "has_step_documents": has_step_documents,
            "uploaded_files": uploaded_files_list,
            "step_checklists": step_checklists,
            "stats": {
                "files_in_project": len(uploaded_files_list),
                "total_matched": total_matched,
                "total_missing": total_missing,
                "required_missing": required_missing
            },
            "processing_jobs": processing_jobs
        }
        
    except Exception as e:
        logger.exception(f"Document checklist failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class KeywordUpdateRequest(BaseModel):
    step_number: str
    old_keyword: str
    new_keyword: str


@router.put("/year-end/step-documents/keyword")
async def update_step_document_keyword(request: KeywordUpdateRequest):
    """
    Update a keyword in the Step_Documents sheet.
    This allows users to customize matching criteria.
    """
    conn = None
    try:
        from backend.utils.playbook_parser import get_duckdb_connection
        
        conn = get_duckdb_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Database connection unavailable")
        
        logger.info(f"[KEYWORD] Updating: Step {request.step_number}, '{request.old_keyword}' -> '{request.new_keyword}'")
        
        # Find the Step_Documents table
        result = conn.execute("""
            SELECT table_name
            FROM _schema_metadata
            WHERE is_current = TRUE
            AND LOWER(project) = 'global'
            AND LOWER(sheet_name) LIKE '%step_documents%'
            LIMIT 1
        """).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Step_Documents sheet not found in database")
        
        table_name = result[0]
        logger.info(f"[KEYWORD] Found table: {table_name}")
        
        # Get column info to find keyword column
        col_info = conn.execute(f"PRAGMA table_info('{table_name}')").fetchall()
        col_names = [c[1].lower() for c in col_info]
        logger.info(f"[KEYWORD] Columns: {col_names}")
        
        # Find keyword column
        keyword_col = None
        for i, name in enumerate(col_names):
            if 'keyword' in name or 'document' in name:
                keyword_col = col_info[i][1]  # Original column name
                break
        
        if not keyword_col:
            raise HTTPException(status_code=500, detail=f"Could not find keyword column in {col_names}")
        
        # Find step column
        step_col = None
        for i, name in enumerate(col_names):
            if 'step' in name:
                step_col = col_info[i][1]
                break
        
        if not step_col:
            step_col = col_info[0][1]  # Default to first column
        
        logger.info(f"[KEYWORD] Using columns: step='{step_col}', keyword='{keyword_col}'")
        
        # Update the keyword
        update_sql = f"""
            UPDATE "{table_name}"
            SET "{keyword_col}" = ?
            WHERE CAST("{step_col}" AS VARCHAR) = ?
            AND "{keyword_col}" = ?
        """
        
        logger.info(f"[KEYWORD] SQL: {update_sql}")
        conn.execute(update_sql, [request.new_keyword, request.step_number, request.old_keyword])
        conn.commit()
        
        logger.info(f"[KEYWORD] Updated successfully")
        
        return {"success": True, "message": f"Updated keyword for step {request.step_number}"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Keyword update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


# ============================================================================
# AI SUMMARY DASHBOARD - Consolidated view of all issues and recommendations
# ============================================================================

@router.get("/year-end/summary/{project_id}")
async def get_ai_summary(project_id: str):
    """
    Get consolidated AI summary across all scanned actions.
    Aggregates issues, recommendations, and key values.
    """
    progress = PLAYBOOK_PROGRESS.get(project_id, {})
    
    # Aggregate data
    all_issues = []
    all_recommendations = []
    all_key_values = {}
    all_conflicts = []
    actions_with_flags = []
    high_risk_actions = []
    
    for action_id, action_progress in progress.items():
        findings = action_progress.get("findings", {})
        if not findings:
            continue
        
        # Collect issues with action context
        for issue in findings.get("issues", []):
            all_issues.append({
                "action_id": action_id,
                "issue": issue,
                "risk_level": findings.get("risk_level", "medium")
            })
        
        # Collect recommendations
        for rec in findings.get("recommendations", []):
            all_recommendations.append({
                "action_id": action_id,
                "recommendation": rec
            })
        
        # Collect key values (dedupe by key)
        for key, value in findings.get("key_values", {}).items():
            if key not in all_key_values:
                all_key_values[key] = {"value": value, "source": action_id}
        
        # Collect conflicts (skip company_name - too many false positives)
        for conflict in findings.get("conflicts", []):
            if conflict.get("field") != "company_name":
                all_conflicts.append(conflict)
        
        # Track review flags
        if action_progress.get("review_flag"):
            actions_with_flags.append({
                "action_id": action_id,
                "flag": action_progress["review_flag"]
            })
        
        # Track high risk
        if findings.get("risk_level") == "high":
            high_risk_actions.append({
                "action_id": action_id,
                "summary": findings.get("summary", "")
            })
    
    # Sort issues by risk level
    risk_order = {"high": 0, "medium": 1, "low": 2}
    all_issues.sort(key=lambda x: risk_order.get(x["risk_level"], 3))
    
    # Calculate overall risk
    if high_risk_actions:
        overall_risk = "high"
    elif any(i["risk_level"] == "medium" for i in all_issues):
        overall_risk = "medium"
    else:
        overall_risk = "low"
    
    # Generate summary text
    summary_parts = []
    if high_risk_actions:
        summary_parts.append(f"⚠️ {len(high_risk_actions)} high-risk action(s) need attention")
    if all_conflicts:
        summary_parts.append(f"❗ {len(all_conflicts)} data conflict(s) detected")
    if actions_with_flags:
        summary_parts.append(f"🔄 {len(actions_with_flags)} action(s) flagged for review")
    
    total_complete = sum(1 for p in progress.values() if p.get("status") == "complete")
    total_in_progress = sum(1 for p in progress.values() if p.get("status") == "in_progress")
    
    return {
        "project_id": project_id,
        "overall_risk": overall_risk,
        "summary_text": " | ".join(summary_parts) if summary_parts else "No critical issues detected",
        "stats": {
            "actions_scanned": len(progress),
            "actions_complete": total_complete,
            "actions_in_progress": total_in_progress,
            "total_issues": len(all_issues),
            "total_recommendations": len(all_recommendations),
            "total_conflicts": len(all_conflicts),
            "actions_flagged": len(actions_with_flags)
        },
        "issues": all_issues[:20],  # Top 20
        "recommendations": all_recommendations[:15],  # Top 15
        "key_values": all_key_values,
        "conflicts": all_conflicts,
        "review_flags": actions_with_flags,
        "high_risk_actions": high_risk_actions
    }


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


# ============================================================================
# TOOLTIP SYSTEM - Consultant-driven tips and notes
# ============================================================================

class TooltipCreate(BaseModel):
    action_id: str
    tooltip_type: str  # 'best_practice', 'mandatory', 'hint'
    title: Optional[str] = None
    content: str
    display_order: Optional[int] = 0

class TooltipUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tooltip_type: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


def get_supabase():
    """Get Supabase client - try multiple import paths"""
    try:
        # Try the standard import
        from utils.supabase_client import get_supabase as _get_supabase
        return _get_supabase()
    except ImportError:
        try:
            # Fallback: try direct supabase client
            from utils.supabase_client import supabase
            return supabase
        except ImportError:
            try:
                # Fallback 2: try creating client directly
                import os
                from supabase import create_client
                url = os.getenv("SUPABASE_URL")
                key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")
                if url and key:
                    return create_client(url, key)
            except Exception as e:
                logger.error(f"All Supabase import methods failed: {e}")
    except Exception as e:
        logger.error(f"Failed to get Supabase client: {e}")
    return None


@router.get("/tooltips/{action_id}")
async def get_tooltips_for_action(action_id: str, playbook_id: str = "year-end-2025"):
    """Get all active tooltips for a specific action"""
    supabase = get_supabase()
    if not supabase:
        return {"tooltips": [], "error": "Database not available"}
    
    try:
        response = supabase.table('playbook_tooltips') \
            .select('*') \
            .eq('playbook_id', playbook_id) \
            .eq('action_id', action_id) \
            .eq('is_active', True) \
            .order('display_order') \
            .execute()
        
        return {"tooltips": response.data or []}
    except Exception as e:
        logger.error(f"Failed to get tooltips: {e}")
        return {"tooltips": [], "error": str(e)}


@router.get("/tooltips")
async def get_all_tooltips(playbook_id: str = "year-end-2025", include_inactive: bool = False):
    """Get all tooltips for a playbook (for admin view)"""
    supabase = get_supabase()
    if not supabase:
        return {"tooltips": [], "error": "Database not available"}
    
    try:
        query = supabase.table('playbook_tooltips') \
            .select('*') \
            .eq('playbook_id', playbook_id)
        
        if not include_inactive:
            query = query.eq('is_active', True)
        
        response = query.order('action_id').order('display_order').execute()
        
        return {"tooltips": response.data or []}
    except Exception as e:
        logger.error(f"Failed to get tooltips: {e}")
        return {"tooltips": [], "error": str(e)}


@router.post("/tooltips")
async def create_tooltip(tooltip: TooltipCreate):
    """Create a new tooltip (admin only)"""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Database not available")
    
    # Validate tooltip_type
    valid_types = ['best_practice', 'mandatory', 'hint']
    if tooltip.tooltip_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid tooltip_type. Must be one of: {valid_types}")
    
    try:
        data = {
            "playbook_id": "year-end-2025",
            "action_id": tooltip.action_id.upper(),
            "tooltip_type": tooltip.tooltip_type,
            "title": tooltip.title,
            "content": tooltip.content,
            "display_order": tooltip.display_order or 0,
            "is_active": True
        }
        
        response = supabase.table('playbook_tooltips').insert(data).execute()
        
        return {"success": True, "tooltip": response.data[0] if response.data else None}
    except Exception as e:
        logger.error(f"Failed to create tooltip: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/tooltips/{tooltip_id}")
async def update_tooltip(tooltip_id: str, tooltip: TooltipUpdate):
    """Update an existing tooltip (admin only)"""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        # Build update data (only include non-None fields)
        data = {}
        if tooltip.title is not None:
            data["title"] = tooltip.title
        if tooltip.content is not None:
            data["content"] = tooltip.content
        if tooltip.tooltip_type is not None:
            valid_types = ['best_practice', 'mandatory', 'hint']
            if tooltip.tooltip_type not in valid_types:
                raise HTTPException(status_code=400, detail=f"Invalid tooltip_type. Must be one of: {valid_types}")
            data["tooltip_type"] = tooltip.tooltip_type
        if tooltip.display_order is not None:
            data["display_order"] = tooltip.display_order
        if tooltip.is_active is not None:
            data["is_active"] = tooltip.is_active
        
        if not data:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        response = supabase.table('playbook_tooltips') \
            .update(data) \
            .eq('id', tooltip_id) \
            .execute()
        
        return {"success": True, "tooltip": response.data[0] if response.data else None}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update tooltip: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/tooltips/{tooltip_id}")
async def delete_tooltip(tooltip_id: str):
    """Delete a tooltip (admin only) - soft delete by setting is_active=False"""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        # Soft delete
        response = supabase.table('playbook_tooltips') \
            .update({"is_active": False}) \
            .eq('id', tooltip_id) \
            .execute()
        
        return {"success": True, "deleted": tooltip_id}
    except Exception as e:
        logger.error(f"Failed to delete tooltip: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tooltips/bulk/{playbook_id}")
async def get_tooltips_bulk(playbook_id: str = "year-end-2025"):
    """
    Get all tooltips grouped by action_id for efficient frontend loading.
    Returns: { "2A": [...tooltips], "3B": [...tooltips], ... }
    """
    supabase = get_supabase()
    if not supabase:
        return {"tooltips_by_action": {}, "error": "Database not available"}
    
    try:
        response = supabase.table('playbook_tooltips') \
            .select('*') \
            .eq('playbook_id', playbook_id) \
            .eq('is_active', True) \
            .order('display_order') \
            .execute()
        
        # Group by action_id
        by_action = {}
        for tip in (response.data or []):
            action_id = tip['action_id']
            if action_id not in by_action:
                by_action[action_id] = []
            by_action[action_id].append(tip)
        
        return {"tooltips_by_action": by_action}
    except Exception as e:
        logger.error(f"Failed to get tooltips bulk: {e}")
        return {"tooltips_by_action": {}, "error": str(e)}

def build_report_to_actions(structure: dict) -> dict:
    """
    Dynamically build keyword-to-action mappings from structure.
    Maps report keywords to actions that need those reports.
    """
    mapping = {}
    
    for step in structure.get('steps', []):
        for action in step.get('actions', []):
            action_id = action['action_id']
            
            # Add mappings for reports_needed
            for report in action.get('reports_needed', []):
                report_lower = report.lower().strip()
                if report_lower:
                    if report_lower not in mapping:
                        mapping[report_lower] = []
                    if action_id not in mapping[report_lower]:
                        mapping[report_lower].append(action_id)
            
            # Add mappings for keywords
            for keyword in action.get('keywords', []):
                keyword_lower = keyword.lower().strip()
                if keyword_lower:
                    if keyword_lower not in mapping:
                        mapping[keyword_lower] = []
                    if action_id not in mapping[keyword_lower]:
                        mapping[keyword_lower].append(action_id)
    
    return mapping

# Placeholder - built when structure loads
REPORT_TO_ACTIONS = {}


def match_filename_to_actions(filename: str, structure: dict = None) -> List[str]:
    """
    Match an uploaded filename to relevant playbook actions.
    Returns list of action IDs that should be scanned.
    
    Dynamically builds mapping if not cached.
    """
    global REPORT_TO_ACTIONS
    
    # Build mapping if empty and structure provided
    if not REPORT_TO_ACTIONS and structure:
        REPORT_TO_ACTIONS = build_report_to_actions(structure)
        logger.info(f"[AUTO-SCAN] Built {len(REPORT_TO_ACTIONS)} keyword mappings")
    
    filename_lower = filename.lower()
    matched_actions = set()
    
    for keyword, actions in REPORT_TO_ACTIONS.items():
        if keyword in filename_lower:
            matched_actions.update(actions)
            logger.info(f"[AUTO-SCAN] Filename '{filename}' matched keyword '{keyword}' -> actions {actions}")
    
    return list(matched_actions)


def get_dependent_actions(action_ids: List[str]) -> List[str]:
    """
    Get all actions that depend on the given actions.
    Returns the original actions plus their dependents.
    """
    all_actions = set(action_ids)
    
    # Find dependents
    for dependent_id, parent_ids in ACTION_DEPENDENCIES.items():
        if any(parent in action_ids for parent in parent_ids):
            all_actions.add(dependent_id)
            logger.info(f"[AUTO-SCAN] Adding dependent action {dependent_id} (depends on {parent_ids})")
    
    return list(all_actions)


def get_scan_order(action_ids: List[str]) -> List[str]:
    """
    Order actions so parents are scanned before dependents.
    """
    # Define a priority based on action number
    def action_priority(action_id: str) -> int:
        # Extract numeric part
        try:
            num_part = ''.join(filter(str.isdigit, action_id))
            letter_part = ''.join(filter(str.isalpha, action_id))
            return int(num_part) * 100 + ord(letter_part.upper()) - ord('A')
        except:
            return 999
    
    return sorted(action_ids, key=action_priority)


@router.post("/year-end/auto-scan/{project_id}")
async def auto_scan_for_file(project_id: str, filename: str):
    """
    Automatically scan relevant playbook actions when a file is uploaded.
    
    1. Match filename to relevant actions
    2. Add dependent actions
    3. Scan in correct order (parents before children)
    4. Return results
    """
    logger.info(f"[AUTO-SCAN] Starting auto-scan for '{filename}' in project {project_id}")
    
    # Get structure first to build dynamic mappings
    structure = await get_year_end_structure()
    
    # Step 1: Match filename to actions (pass structure for dynamic mapping)
    matched_actions = match_filename_to_actions(filename, structure)
    
    if not matched_actions:
        logger.info(f"[AUTO-SCAN] No matching actions found for '{filename}'")
        return {
            "success": True,
            "filename": filename,
            "matched_actions": [],
            "scanned_actions": [],
            "message": "No playbook actions matched this file"
        }
    
    # Step 2: Add dependent actions
    all_actions = get_dependent_actions(matched_actions)
    
    # Step 3: Order correctly
    scan_order = get_scan_order(all_actions)
    
    logger.info(f"[AUTO-SCAN] Will scan {len(scan_order)} actions in order: {scan_order}")
    
    # Step 4: Scan each action
    results = []
    for action_id in scan_order:
        try:
            logger.info(f"[AUTO-SCAN] Scanning action {action_id}...")
            result = await scan_for_action(project_id, action_id)
            results.append({
                "action_id": action_id,
                "success": True,
                "found": result.get("found", False),
                "documents": len(result.get("documents", [])),
                "status": result.get("suggested_status", "not_started")
            })
            logger.info(f"[AUTO-SCAN] Action {action_id} complete: {result.get('suggested_status', 'unknown')}")
        except Exception as e:
            logger.error(f"[AUTO-SCAN] Action {action_id} failed: {e}")
            results.append({
                "action_id": action_id,
                "success": False,
                "error": str(e)
            })
    
    return {
        "success": True,
        "filename": filename,
        "matched_actions": matched_actions,
        "scanned_actions": scan_order,
        "results": results
    }


def trigger_auto_scan_sync(project_id: str, filename: str):
    """
    Synchronous wrapper to trigger auto-scan from background threads.
    Uses asyncio to run the async function.
    """
    import asyncio
    
    try:
        # Try to get existing event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is already running, create a new task
            # This happens when called from within an async context
            asyncio.create_task(auto_scan_for_file(project_id, filename))
            logger.info(f"[AUTO-SCAN] Queued auto-scan task for '{filename}'")
        else:
            # Run in the existing loop
            loop.run_until_complete(auto_scan_for_file(project_id, filename))
    except RuntimeError:
        # No event loop, create a new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(auto_scan_for_file(project_id, filename))
        finally:
            loop.close()
    except Exception as e:
        logger.error(f"[AUTO-SCAN] Failed to trigger auto-scan: {e}")


# =============================================================================
# NON-BLOCKING SCAN-ALL WITH STATUS POLLING
# =============================================================================

# Scan job tracking
class _ScanJobStatus:
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"

class _PlaybookScanJob:
    """Tracks a scan-all job with progress updates"""
    
    def __init__(self, job_id: str, project_id: str, actions: list):
        self.job_id = job_id
        self.project_id = project_id
        self.status = _ScanJobStatus.PENDING
        self.actions = actions
        self.total = len(actions)
        self.completed = 0
        self.current_action = None
        self.progress = 0
        self.message = "Initializing..."
        self.results = []
        self.errors = []
        self.started_at = None
        self.completed_at = None
        self.created_at = datetime.now()
        self.timeout_seconds = 600  # 10 minutes
        self._lock = threading.Lock()
    
    def start(self):
        with self._lock:
            self.status = _ScanJobStatus.RUNNING
            self.started_at = datetime.now()
            self.message = "Scan started..."
    
    def update(self, action_id: str, message: str = None):
        with self._lock:
            self.current_action = action_id
            self.progress = int((self.completed / self.total) * 100) if self.total > 0 else 0
            self.message = message or f"Scanning {action_id}..."
    
    def action_done(self, action_id: str, result: dict):
        with self._lock:
            self.completed += 1
            self.results.append({"action_id": action_id, "success": True, **result})
            self.progress = int((self.completed / self.total) * 100)
            self.message = f"Completed {self.completed}/{self.total}"
    
    def action_failed(self, action_id: str, error: str):
        with self._lock:
            self.completed += 1
            self.errors.append({"action_id": action_id, "error": error})
            self.results.append({"action_id": action_id, "success": False, "error": error})
            self.progress = int((self.completed / self.total) * 100)
    
    def complete(self, message: str = None):
        with self._lock:
            self.status = _ScanJobStatus.COMPLETED
            self.completed_at = datetime.now()
            self.progress = 100
            successful = len([r for r in self.results if r.get('success')])
            self.message = message or f"Complete: {successful}/{self.total} successful"
    
    def fail(self, error: str):
        with self._lock:
            self.status = _ScanJobStatus.FAILED
            self.completed_at = datetime.now()
            self.message = error
    
    def timeout(self):
        with self._lock:
            self.status = _ScanJobStatus.TIMEOUT
            self.completed_at = datetime.now()
            self.message = f"Timeout after {self.timeout_seconds}s"
    
    def cancel(self):
        with self._lock:
            self.status = _ScanJobStatus.CANCELLED
            self.completed_at = datetime.now()
            self.message = "Cancelled by user"
    
    def is_timed_out(self) -> bool:
        with self._lock:
            if self.started_at and self.status == _ScanJobStatus.RUNNING:
                return (datetime.now() - self.started_at).total_seconds() > self.timeout_seconds
            return False
    
    def to_dict(self) -> dict:
        with self._lock:
            successful = len([r for r in self.results if r.get('success', False)])
            return {
                "job_id": self.job_id,
                "project_id": self.project_id,
                "status": self.status,
                "total_actions": self.total,
                "completed_actions": self.completed,
                "successful": successful,
                "failed": len(self.errors),
                "current_action": self.current_action,
                "progress_percent": self.progress,
                "message": self.message,
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "completed_at": self.completed_at.isoformat() if self.completed_at else None,
                "created_at": self.created_at.isoformat(),
                "results": self.results if self.status in [_ScanJobStatus.COMPLETED, _ScanJobStatus.FAILED, _ScanJobStatus.TIMEOUT] else [],
                "errors": self.errors
            }

# Global job storage
_scan_jobs: Dict[str, _PlaybookScanJob] = {}
_scan_jobs_lock = threading.Lock()

def _get_scan_job(job_id: str):
    with _scan_jobs_lock:
        return _scan_jobs.get(job_id)

def _cleanup_old_scan_jobs():
    """Remove jobs older than 1 hour"""
    from datetime import timedelta
    with _scan_jobs_lock:
        cutoff = datetime.now() - timedelta(hours=1)
        to_delete = [jid for jid, job in _scan_jobs.items() if job.completed_at and job.completed_at < cutoff]
        for jid in to_delete:
            del _scan_jobs[jid]


@router.post("/year-end/scan-all/{project_id}")
async def scan_all_actions(project_id: str, timeout: int = 600):
    """
    Start scanning ALL playbook actions for a project.
    
    Returns job_id immediately - poll /scan-all/status/{job_id} for progress.
    
    NO MORE FREEZING! Always shows status.
    
    Args:
        project_id: Project to scan
        timeout: Max seconds before timeout (default 600 = 10 min)
    
    Returns:
        job_id for status polling
    """
    import uuid as uuid_mod
    import asyncio as asyncio_mod
    
    logger.info(f"[SCAN-ALL] Starting non-blocking scan for project {project_id}")
    
    # Get structure
    structure = await get_year_end_structure()
    
    # Collect actions to scan
    actions_to_scan = []
    all_action_ids = set()
    
    for step in structure.get('steps', []):
        for action in step.get('actions', []):
            all_action_ids.add(action['action_id'])
            if action.get('reports_needed'):
                actions_to_scan.append(action['action_id'])
    
    # Add dependent actions that exist in structure
    dependencies = build_action_dependencies(structure)
    for dependent_id in dependencies.keys():
        if dependent_id in all_action_ids and dependent_id not in actions_to_scan:
            actions_to_scan.append(dependent_id)
    
    # Order by dependencies
    scan_order = get_scan_order(actions_to_scan)
    
    if not scan_order:
        return {"success": True, "message": "No actions to scan", "job_id": None}
    
    # Create job
    job_id = str(uuid_mod.uuid4())
    job = _PlaybookScanJob(job_id, project_id, scan_order)
    job.timeout_seconds = timeout
    
    with _scan_jobs_lock:
        _scan_jobs[job_id] = job
    
    # Background thread function
    def run_scan():
        try:
            job.start()
            logger.info(f"[SCAN-ALL] Starting job {job_id} with {len(job.actions)} actions: {job.actions}")
            
            # Create event loop for async calls
            loop = asyncio_mod.new_event_loop()
            asyncio_mod.set_event_loop(loop)
            
            for action_id in job.actions:
                # Check timeout
                if job.is_timed_out():
                    logger.warning(f"[SCAN-ALL] Job {job_id} timed out")
                    job.timeout()
                    return
                
                # Check cancelled
                if job.status == _ScanJobStatus.CANCELLED:
                    return
                
                try:
                    job.update(action_id, f"Scanning {action_id}...")
                    logger.info(f"[SCAN-ALL] Scanning action {action_id}...")
                    
                    # Run the scan
                    result = loop.run_until_complete(scan_for_action(project_id, action_id))
                    
                    logger.info(f"[SCAN-ALL] Action {action_id} result: found={result.get('found')}, docs={len(result.get('documents', []))}")
                    
                    job.action_done(action_id, {
                        "found": result.get("found", False),
                        "documents": len(result.get("documents", [])),
                        "status": result.get("suggested_status", "not_started")
                    })
                    
                except Exception as e:
                    logger.error(f"[SCAN-ALL] Action {action_id} failed: {e}")
                    job.action_failed(action_id, str(e))
            
            loop.close()
            job.complete()
            logger.info(f"[SCAN-ALL] Job {job_id} completed")
            
        except Exception as e:
            logger.error(f"[SCAN-ALL] Job {job_id} failed: {e}")
            job.fail(str(e))
    
    thread = threading.Thread(target=run_scan, daemon=True)
    thread.start()
    
    logger.info(f"[SCAN-ALL] Created job {job_id} with {len(scan_order)} actions")
    
    return {
        "success": True,
        "job_id": job_id,
        "project_id": project_id,
        "total_actions": len(scan_order),
        "actions": scan_order,
        "message": f"Scan started for {len(scan_order)} actions",
        "poll_url": f"/playbooks/year-end/scan-all/status/{job_id}"
    }


@router.get("/year-end/scan-all/status/{job_id}")
async def get_scan_status(job_id: str):
    """
    Get status of a scan-all job.
    
    Poll this every 1-2 seconds for live updates.
    """
    job = _get_scan_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job.to_dict()


@router.post("/year-end/scan-all/cancel/{job_id}")
async def cancel_scan(job_id: str):
    """Cancel a running scan-all job."""
    job = _get_scan_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != _ScanJobStatus.RUNNING:
        return {"success": False, "message": f"Cannot cancel job in status: {job.status}"}
    
    job.cancel()
    
    return {
        "success": True,
        "message": "Scan cancelled",
        "completed_actions": job.completed,
        "total_actions": job.total
    }


@router.get("/year-end/scan-all/jobs/{project_id}")
async def list_scan_jobs(project_id: str, limit: int = 10):
    """List recent scan jobs for a project."""
    _cleanup_old_scan_jobs()
    
    with _scan_jobs_lock:
        project_jobs = [job.to_dict() for job in _scan_jobs.values() if job.project_id == project_id]
    
    project_jobs.sort(key=lambda j: j['created_at'], reverse=True)
    
    return {"project_id": project_id, "jobs": project_jobs[:limit]}


# =============================================================================
# LEARNING & FEEDBACK ENDPOINTS
# =============================================================================

class FeedbackRequest(BaseModel):
    """Request model for recording user feedback/corrections."""
    action_id: str
    correction_type: str  # 'status', 'issue_removed', 'issue_added', 'finding_edited'
    original_value: Any
    corrected_value: Any
    context: Optional[str] = None


@router.post("/year-end/feedback/{project_id}")
async def record_feedback(project_id: str, feedback: FeedbackRequest):
    """
    Record user correction for learning.
    
    Called when user:
    - Changes status from AI suggestion
    - Removes an AI-flagged issue
    - Adds an issue AI missed
    - Edits findings
    """
    try:
        from backend.utils.learning_engine import get_learning_system
        learning = get_learning_system()
        
        learning.record_feedback(
            action_id=feedback.action_id,
            correction_type=feedback.correction_type,
            original=feedback.original_value,
            corrected=feedback.corrected_value,
            context=feedback.context
        )
        
        logger.info(f"[FEEDBACK] Recorded: {feedback.action_id} {feedback.correction_type}")
        
        return {
            "success": True,
            "message": f"Feedback recorded for {feedback.action_id}",
            "correction_type": feedback.correction_type
        }
        
    except ImportError:
        logger.warning("[FEEDBACK] Learning engine not available")
        return {"success": False, "message": "Learning engine not installed"}
    except Exception as e:
        logger.error(f"[FEEDBACK] Error: {e}")
        return {"success": False, "message": str(e)}


@router.get("/year-end/learning/stats")
async def get_learning_stats():
    """
    Get learning system statistics.
    
    Shows:
    - Training data collected
    - Cache hits
    - Feedback patterns learned
    - Claude API reduction percentage
    """
    try:
        from backend.utils.learning_engine import get_learning_system
        learning = get_learning_system()
        stats = learning.get_stats()
        
        # Add hybrid analyzer stats if available
        try:
            from backend.utils.hybrid_analyzer import get_hybrid_analyzer
            analyzer = get_hybrid_analyzer()
            stats['analyzer'] = analyzer.get_stats()
        except:
            pass
        
        return {"success": True, "stats": stats}
        
    except ImportError:
        return {"success": False, "message": "Learning engine not installed", "stats": {}}
    except Exception as e:
        logger.error(f"[LEARNING] Stats error: {e}")
        return {"success": False, "message": str(e), "stats": {}}

# =============================================================================
# PASTE THIS BEFORE THE LAST LINE OF playbooks.py
# =============================================================================

# =============================================================================
# ENTITY DETECTION & CONFIGURATION ENDPOINTS
# =============================================================================

@router.post("/{playbook_type}/detect-entities/{project_id}")
async def detect_entities(playbook_type: str, project_id: str):
    """
    Scan project documents for US FEINs and Canada BNs.
    Call this before analysis to let user select which entities to include.
    """
    try:
        from backend.utils.fein_detector import detect_entity_identifiers, identify_company_names
        
        # Get project documents
        docs = await get_project_documents_text(project_id)
        if not docs:
            return {
                "success": True,
                "entities": {"us": [], "canada": []},
                "summary": {"us_count": 0, "canada_count": 0, "total": 0},
                "warnings": []
            }
        
        combined_text = "\n\n".join(docs)
        
        # Detect entities
        entities = detect_entity_identifiers(combined_text)
        
        # Identify company names
        all_entities = entities.get('us', []) + entities.get('canada', [])
        if all_entities:
            names = identify_company_names(all_entities, combined_text)
            for country in ['us', 'canada']:
                for entity in entities.get(country, []):
                    if entity['id'] in names:
                        entity['company_name'] = names[entity['id']].get('company_name', f"Entity {entity['id']}")
        
        # Build summary
        us_count = len(entities.get('us', []))
        ca_count = len(entities.get('canada', []))
        
        # Suggested primary (most mentioned)
        primary = None
        if all_entities:
            primary = max(all_entities, key=lambda x: x.get('count', 0))
        
        warnings = []
        if ca_count > 0 and playbook_type == 'year_end':
            warnings.append("Canada entities detected - requires Canada Year-End Playbook (coming soon)")
        
        return {
            "success": True,
            "project_id": project_id,
            "playbook_type": playbook_type,
            "entities": entities,
            "summary": {
                "us_count": us_count,
                "canada_count": ca_count,
                "total": us_count + ca_count,
                "suggested_primary": primary['id'] if primary else None
            },
            "warnings": warnings
        }
        
    except ImportError:
        logger.warning("[ENTITIES] fein_detector not available")
        return {"success": False, "message": "Entity detection not available"}
    except Exception as e:
        logger.error(f"[ENTITIES] Detection error: {e}")
        return {"success": False, "message": str(e)}


class EntityConfigRequest(BaseModel):
    analysis_scope: str  # 'all', 'selected', 'primary_only'
    selected_entities: List[str]
    primary_entity: Optional[str] = None
    country_mode: str = 'us_only'


@router.post("/{playbook_type}/entity-config/{project_id}")
async def save_entity_config(playbook_type: str, project_id: str, config: EntityConfigRequest):
    """Save entity configuration for a project/playbook."""
    try:
        from utils.database.models import EntityConfigModel
        
        result = EntityConfigModel.save(
            project_id=project_id,
            playbook_type=playbook_type,
            analysis_scope=config.analysis_scope,
            selected_entities=config.selected_entities,
            primary_entity=config.primary_entity,
            country_mode=config.country_mode
        )
        
        if result:
            return {
                "success": True,
                "message": f"Entity configuration saved. Analyzing {len(config.selected_entities)} entities.",
                "config": result
            }
        return {"success": False, "message": "Failed to save configuration"}
        
    except Exception as e:
        logger.error(f"[ENTITY-CONFIG] Save error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{playbook_type}/entity-config/{project_id}")
async def get_entity_config(playbook_type: str, project_id: str):
    """Get entity configuration for a project/playbook."""
    try:
        from utils.database.models import EntityConfigModel
        
        config = EntityConfigModel.get(project_id, playbook_type)
        
        if config:
            return {"success": True, "configured": True, "config": config}
        return {"success": True, "configured": False, "config": None}
        
    except Exception as e:
        logger.error(f"[ENTITY-CONFIG] Get error: {e}")
        return {"success": False, "configured": False, "config": None, "message": str(e)}


# =============================================================================
# SUPPRESSION ENDPOINTS
# =============================================================================

class SuppressionRequest(BaseModel):
    suppression_type: str  # 'acknowledge', 'suppress', 'pattern'
    reason: str
    action_id: Optional[str] = None
    finding_text: Optional[str] = None
    pattern: Optional[str] = None
    category: Optional[str] = None
    document_filter: Optional[str] = None
    state_filter: Optional[List[str]] = None
    keyword_filter: Optional[List[str]] = None
    fein_filter: Optional[List[str]] = None
    expires_at: Optional[str] = None
    notes: Optional[str] = None


@router.post("/{playbook_type}/suppress/{project_id}")
async def create_suppression(playbook_type: str, project_id: str, request: SuppressionRequest):
    """Create a suppression rule."""
    try:
        from utils.database.models import FindingSuppressionModel
        
        result = FindingSuppressionModel.create(
            project_id=project_id,
            playbook_type=playbook_type,
            suppression_type=request.suppression_type,
            reason=request.reason,
            action_id=request.action_id,
            finding_text=request.finding_text,
            pattern=request.pattern,
            category=request.category,
            document_filter=request.document_filter,
            state_filter=request.state_filter,
            keyword_filter=request.keyword_filter,
            fein_filter=request.fein_filter,
            expires_at=request.expires_at,
            notes=request.notes
        )
        
        if result:
            return {"success": True, "rule_id": result['id'], "rule": result}
        return {"success": False, "message": "Failed to create suppression"}
        
    except Exception as e:
        logger.error(f"[SUPPRESS] Create error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{playbook_type}/suppressions/{project_id}")
async def list_suppressions(playbook_type: str, project_id: str, include_inactive: bool = False):
    """List all suppression rules for a project."""
    try:
        from utils.database.models import FindingSuppressionModel
        
        rules = FindingSuppressionModel.get_by_project(project_id, playbook_type, include_inactive)
        stats = FindingSuppressionModel.get_stats(project_id, playbook_type)
        
        return {"success": True, "rules": rules, "stats": stats}
        
    except Exception as e:
        logger.error(f"[SUPPRESS] List error: {e}")
        return {"success": False, "rules": [], "stats": {}, "message": str(e)}


@router.delete("/{playbook_type}/suppress/{rule_id}")
async def deactivate_suppression(playbook_type: str, rule_id: str):
    """Deactivate a suppression rule (soft delete)."""
    try:
        from utils.database.models import FindingSuppressionModel
        
        success = FindingSuppressionModel.deactivate(rule_id)
        return {"success": success}
        
    except Exception as e:
        logger.error(f"[SUPPRESS] Deactivate error: {e}")
        return {"success": False, "message": str(e)}


@router.put("/{playbook_type}/suppress/{rule_id}/reactivate")
async def reactivate_suppression(playbook_type: str, rule_id: str):
    """Reactivate a deactivated suppression rule."""
    try:
        from utils.database.models import FindingSuppressionModel
        
        success = FindingSuppressionModel.reactivate(rule_id)
        return {"success": success}
        
    except Exception as e:
        logger.error(f"[SUPPRESS] Reactivate error: {e}")
        return {"success": False, "message": str(e)}


class QuickSuppressRequest(BaseModel):
    finding_text: str
    reason: str
    suppress_type: str = 'acknowledge'  # 'acknowledge' or 'suppress'
    fein: Optional[str] = None


@router.post("/{playbook_type}/suppress/quick/{project_id}/{action_id}")
async def quick_suppress(playbook_type: str, project_id: str, action_id: str, request: QuickSuppressRequest):
    """Quick suppress from UI - one click acknowledge/suppress."""
    try:
        from utils.database.models import FindingSuppressionModel
        
        result = FindingSuppressionModel.create(
            project_id=project_id,
            playbook_type=playbook_type,
            action_id=action_id,
            suppression_type=request.suppress_type,
            finding_text=request.finding_text,
            reason=request.reason,
            fein_filter=[request.fein] if request.fein else None
        )
        
        if result:
            return {"success": True, "rule_id": result['id'], "type": request.suppress_type}
        return {"success": False, "message": "Failed to create suppression"}
        
    except Exception as e:
        logger.error(f"[SUPPRESS] Quick suppress error: {e}")
        return {"success": False, "message": str(e)}


@router.get("/{playbook_type}/suppressions/stats/{project_id}")
async def get_suppression_stats(playbook_type: str, project_id: str):
    """Get suppression statistics for a project."""
    try:
        from utils.database.models import FindingSuppressionModel
        
        stats = FindingSuppressionModel.get_stats(project_id, playbook_type)
        return {"success": True, "stats": stats}
        
    except Exception as e:
        logger.error(f"[SUPPRESS] Stats error: {e}")
        return {"success": False, "stats": {}, "message": str(e)}


# =============================================================================
# HELPER FUNCTION FOR ENTITY DETECTION
# =============================================================================

async def get_project_documents_text(project_id: str) -> List[str]:
    """Get all document text for a project (for entity detection).
    Checks BOTH DuckDB (structured) and ChromaDB (unstructured).
    """
    texts = []
    project_name = None
    
    logger.warning(f"[ENTITIES] Starting document retrieval for project {project_id}")
    
    # First, get the project NAME from Supabase (DuckDB uses names, not UUIDs)
    try:
        supabase = get_supabase()
        logger.warning(f"[ENTITIES] Supabase client: {supabase is not None}")
        if supabase:
            result = supabase.table('projects').select('name').eq('id', project_id).execute()
            if result.data and len(result.data) > 0:
                project_name = result.data[0].get('name')
                logger.warning(f"[ENTITIES] Project name: {project_name}")
            else:
                logger.warning(f"[ENTITIES] No project found for ID {project_id}")
    except Exception as e:
        logger.warning(f"[ENTITIES] Could not get project name: {e}")
    
    # 1. Try DuckDB (structured data - Excel files, CSVs)
    if project_name:
        try:
            from backend.utils.playbook_parser import get_duckdb_connection
            conn = get_duckdb_connection()
            logger.warning(f"[ENTITIES] DuckDB connection: {conn is not None}")
            if conn:
                try:
                    # Query using project NAME not UUID
                    tables = conn.execute("""
                        SELECT table_name, file_name 
                        FROM _schema_metadata 
                        WHERE LOWER(project) = LOWER(?) AND is_current = TRUE
                    """, [project_name]).fetchall()
                    
                    logger.warning(f"[ENTITIES] Found {len(tables)} tables for project {project_name}")
                    
                    for table_name, file_name in tables:
                        try:
                            df = conn.execute(f'SELECT * FROM "{table_name}" LIMIT 500').fetchdf()
                            if df is not None and not df.empty:
                                texts.append(f"[Source: {file_name}]\n{df.to_string()}")
                        except Exception as e:
                            logger.warning(f"[ENTITIES] Error reading table {table_name}: {e}")
                    
                    conn.close()
                except Exception as e:
                    logger.warning(f"[ENTITIES] DuckDB query error: {e}")
                    try:
                        conn.close()
                    except:
                        pass
        except ImportError as e:
            logger.warning(f"[ENTITIES] playbook_parser import failed: {e}")
        except Exception as e:
            logger.warning(f"[ENTITIES] DuckDB error: {e}")
    else:
        logger.warning("[ENTITIES] No project_name, skipping DuckDB")
    
    # 2. Try ChromaDB (unstructured data - PDFs, docs)
    try:
        from chroma_client import query_documents
        results = query_documents("company FEIN EIN employer", project_id=project_id, n_results=50)
        if results and results.get('documents'):
            for doc_list in results['documents']:
                for doc in doc_list:
                    if doc:
                        texts.append(doc)
            logger.warning(f"[ENTITIES] ChromaDB returned {len(results.get('documents', []))} results")
    except ImportError:
        try:
            from backend.chroma_client import query_documents
            results = query_documents("company FEIN EIN employer", project_id=project_id, n_results=50)
            if results and results.get('documents'):
                for doc_list in results['documents']:
                    for doc in doc_list:
                        if doc:
                            texts.append(doc)
                logger.warning(f"[ENTITIES] ChromaDB (backend) returned {len(results.get('documents', []))} results")
        except Exception as e:
            logger.warning(f"[ENTITIES] ChromaDB not available: {e}")
    except Exception as e:
        logger.warning(f"[ENTITIES] ChromaDB error: {e}")
    
    logger.warning(f"[ENTITIES] Retrieved {len(texts)} total text chunks")
    return texts
        
@router.post("/year-end/learning/export-training-data")
async def export_training_data():
    """
    Export collected training data for fine-tuning.
    
    Returns path to exported file in Alpaca format.
    """
    try:
        from backend.utils.learning_engine import get_learning_system
        learning = get_learning_system()
        
        export_path = learning.export_for_finetuning()
        
        return {
            "success": True,
            "message": "Training data exported",
            "path": export_path,
            "stats": learning.get_stats()
        }
        
    except ImportError:
        return {"success": False, "message": "Learning engine not installed"}
    except Exception as e:
        logger.error(f"[LEARNING] Export error: {e}")
        return {"success": False, "message": str(e)}
