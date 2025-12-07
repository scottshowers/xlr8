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

# In-memory progress storage (will move to DuckDB later)
# Structure: {project_id: {action_id: {status, findings, notes, updated_at}}}
PLAYBOOK_PROGRESS = {}

# Cached playbook structure
PLAYBOOK_CACHE = {}


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
        from utils.playbook_parser import parse_year_end_checklist
        
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
    
    return {"success": True, "action_id": action_id, "status": update.status}


# ============================================================================
# SCAN ENDPOINT - Search docs for action-relevant content
# ============================================================================

@router.post("/year-end/scan/{project_id}/{action_id}")
async def scan_for_action(project_id: str, action_id: str):
    """
    Scan project documents for content relevant to a specific action.
    Returns findings and suggested status.
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
        
        # Build search queries
        queries = []
        
        # Use reports needed
        queries.extend(action.get('reports_needed', []))
        
        # Use keywords
        keywords = action.get('keywords', [])
        if keywords:
            queries.append(' '.join(keywords[:4]))
        
        # Add action-specific queries
        queries.append(action.get('description', '')[:100])
        
        # Search for documents
        rag = RAGHandler()
        found_docs = []
        all_content = []
        
        for query in queries[:5]:
            try:
                results = rag.search(
                    collection_name="documents",
                    query=query,
                    n_results=3,
                    project_id=project_id
                )
                if results:
                    for result in results:
                        doc = result.get('document', '')
                        if doc and len(doc) > 50:
                            # Clean encrypted content
                            cleaned = re.sub(r'ENC256:[A-Za-z0-9+/=]+', '[ENCRYPTED]', doc)
                            if cleaned.count('[ENCRYPTED]') < 10:
                                metadata = result.get('metadata', {})
                                found_docs.append({
                                    "filename": metadata.get('source', metadata.get('filename', 'Unknown')),
                                    "snippet": cleaned[:300],
                                    "query": query
                                })
                                all_content.append(cleaned[:1000])
            except Exception as e:
                logger.warning(f"Query failed: {e}")
        
        # Deduplicate by filename
        seen_files = set()
        unique_docs = []
        for doc in found_docs:
            if doc['filename'] not in seen_files:
                seen_files.add(doc['filename'])
                unique_docs.append(doc)
        
        # Determine findings and suggested status
        findings = None
        suggested_status = "not_started"
        
        if unique_docs:
            suggested_status = "in_progress"
            
            # Use Claude to extract specific findings if we have content
            if all_content:
                findings = await extract_findings_for_action(action, all_content[:5])
                if findings and findings.get('complete'):
                    suggested_status = "complete"
        
        # Update progress with scan results
        if project_id not in PLAYBOOK_PROGRESS:
            PLAYBOOK_PROGRESS[project_id] = {}
        
        PLAYBOOK_PROGRESS[project_id][action_id] = {
            "status": PLAYBOOK_PROGRESS.get(project_id, {}).get(action_id, {}).get("status", suggested_status),
            "findings": findings,
            "documents_found": [d['filename'] for d in unique_docs],
            "last_scan": datetime.now().isoformat(),
            "notes": PLAYBOOK_PROGRESS.get(project_id, {}).get(action_id, {}).get("notes")
        }
        
        return {
            "found": len(unique_docs) > 0,
            "documents": unique_docs,
            "findings": findings,
            "suggested_status": suggested_status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Scan failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def extract_findings_for_action(action: Dict, content: List[str]) -> Optional[Dict]:
    """Use Claude to extract specific findings from document content."""
    try:
        from anthropic import Anthropic
        
        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        
        combined = "\n---\n".join(content)
        
        prompt = f"""Analyze these document excerpts for Year-End Checklist action:

Action: {action['action_id']} - {action.get('description', '')}
Reports Needed: {', '.join(action.get('reports_needed', []))}

<documents>
{combined[:4000]}
</documents>

Extract relevant findings as JSON:
{{
    "complete": true/false (is there enough info to mark this action complete?),
    "key_values": {{"label": "value"}} (specific values found, e.g., FEIN, state count, rate),
    "issues": ["list of concerns or missing items"],
    "summary": "1-2 sentence summary of what was found"
}}

Return ONLY valid JSON."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
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
        from utils.playbook_parser import parse_year_end_checklist
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
