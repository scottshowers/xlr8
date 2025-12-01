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
async def get_progress(project_id: int):
    """Get playbook progress for a project."""
    if project_id not in PLAYBOOK_PROGRESS:
        PLAYBOOK_PROGRESS[project_id] = {}
    
    return {
        "project_id": project_id,
        "progress": PLAYBOOK_PROGRESS[project_id],
        "updated_at": datetime.now().isoformat()
    }


@router.post("/year-end/progress/{project_id}/{action_id}")
async def update_progress(project_id: int, action_id: str, update: ActionUpdate):
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
async def scan_for_action(project_id: int, action_id: str):
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
                results = rag.query(
                    query=query,
                    project_id=project_id,
                    n_results=3
                )
                if results and results.get('documents'):
                    for i, doc in enumerate(results['documents'][0]):
                        if doc and len(doc) > 50:
                            # Clean encrypted content
                            cleaned = re.sub(r'ENC256:[A-Za-z0-9+/=]+', '[ENCRYPTED]', doc)
                            if cleaned.count('[ENCRYPTED]') < 10:
                                metadata = results.get('metadatas', [[]])[0][i] if results.get('metadatas') else {}
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
async def export_progress(project_id: int, customer_name: str = "Customer"):
    """Export current playbook progress as XLSX."""
    
    structure = await get_year_end_structure()
    progress = PLAYBOOK_PROGRESS.get(project_id, {})
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Year-End Checklist"
    
    # Styles
    header_font = Font(bold=True, size=11, color="FFFFFF")
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    complete_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    progress_fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
    not_started_fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )
    wrap = Alignment(wrap_text=True, vertical='top')
    
    # Title
    ws.cell(row=1, column=1, value=f"Year-End Checklist - {customer_name}").font = Font(bold=True, size=14)
    ws.cell(row=2, column=1, value=f"Generated: {datetime.now().strftime('%B %d, %Y %H:%M')}")
    ws.cell(row=3, column=1, value=f"Progress: {sum(1 for p in progress.values() if p.get('status') == 'complete')}/{structure['total_actions']} Complete")
    
    # Headers
    headers = ["Action", "Step", "Description", "Due Date", "Status", "Findings", "Documents", "Notes"]
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=5, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
    
    # Data rows
    row = 6
    for step in structure.get('steps', []):
        for action in step.get('actions', []):
            action_id = action['action_id']
            action_progress = progress.get(action_id, {})
            
            status = action_progress.get('status', 'not_started')
            findings = action_progress.get('findings', {})
            docs = action_progress.get('documents_found', [])
            notes = action_progress.get('notes', '')
            
            ws.cell(row=row, column=1, value=action_id).border = thin_border
            ws.cell(row=row, column=2, value=f"Step {step['step_number']}").border = thin_border
            ws.cell(row=row, column=3, value=action['description'][:200]).border = thin_border
            ws.cell(row=row, column=3).alignment = wrap
            ws.cell(row=row, column=4, value=action.get('due_date', '')).border = thin_border
            
            status_cell = ws.cell(row=row, column=5, value=status.replace('_', ' ').title())
            status_cell.border = thin_border
            if status == 'complete':
                status_cell.fill = complete_fill
            elif status == 'in_progress':
                status_cell.fill = progress_fill
            else:
                status_cell.fill = not_started_fill
            
            # Findings summary
            findings_text = findings.get('summary', '') if findings else ''
            ws.cell(row=row, column=6, value=findings_text).border = thin_border
            ws.cell(row=row, column=6).alignment = wrap
            
            ws.cell(row=row, column=7, value=', '.join(docs[:3])).border = thin_border
            ws.cell(row=row, column=8, value=notes or '').border = thin_border
            ws.cell(row=row, column=8).alignment = wrap
            
            row += 1
    
    # Column widths
    widths = [8, 10, 50, 15, 12, 40, 30, 30]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    
    ws.freeze_panes = 'A6'
    
    # Save to bytes
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    filename = f"{customer_name.replace(' ', '_')}_Year_End_Progress_{datetime.now().strftime('%Y%m%d')}.xlsx"
    
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
