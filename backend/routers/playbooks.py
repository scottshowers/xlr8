"""
Playbooks Router - Backend for Analysis Playbooks

Currently supports:
- Year-End Checklist Playbook
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
import json
import io
from datetime import datetime

# Excel generation
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/playbooks", tags=["playbooks"])


class GenerateRequest(BaseModel):
    project_id: int
    project_name: str
    customer_name: str


# ============================================================================
# YEAR-END CHECKLIST PLAYBOOK
# ============================================================================

@router.post("/year-end/generate")
async def generate_year_end_workbook(request: GenerateRequest):
    """
    Generate Year-End Checklist workbook for a project.
    
    Flow:
    1. Query project documents from ChromaDB
    2. Use Claude to analyze documents against Year-End checklist
    3. Generate multi-tab XLSX with findings
    4. Return as downloadable file
    """
    try:
        from utils.rag_handler import RAGHandler
        from anthropic import Anthropic
        import os
        
        logger.info(f"Generating Year-End workbook for project {request.project_id}")
        
        # Initialize handlers
        rag = RAGHandler()
        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        
        # Step 1: Query relevant documents
        doc_queries = [
            "company tax verification FEIN tax code",
            "earnings codes tax categories W-2 box",
            "deduction codes benefit tax categories",
            "workers compensation rates risk classification",
            "outstanding checks payment services",
            "arrears outstanding balance employee",
            "company profile master",
        ]
        
        all_context = []
        docs_analyzed = 0
        
        def clean_encrypted_content(text: str) -> str:
            """Remove encrypted values from text - they're not useful for config analysis."""
            import re
            # Remove ENC256: encrypted values (they look like ENC256:base64string==)
            cleaned = re.sub(r'ENC256:[A-Za-z0-9+/=]+', '[ENCRYPTED]', text)
            # If more than 30% of content is [ENCRYPTED], skip this chunk
            encrypted_count = cleaned.count('[ENCRYPTED]')
            if encrypted_count > 10:  # Too much encrypted content
                return None
            return cleaned
        
        for query in doc_queries:
            try:
                results = rag.query(
                    query=query,
                    project_id=request.project_id,
                    n_results=5
                )
                if results and results.get('documents'):
                    for doc in results['documents'][0]:
                        if doc and len(doc) > 100:  # Only meaningful content
                            # Clean out encrypted values
                            cleaned_doc = clean_encrypted_content(doc)
                            if cleaned_doc and len(cleaned_doc) > 100:
                                all_context.append(cleaned_doc[:3000])  # Limit per doc
                                docs_analyzed += 1
            except Exception as e:
                logger.warning(f"Query failed for '{query}': {e}")
        
        if not all_context:
            raise HTTPException(
                status_code=400,
                detail="No relevant documents found for analysis. Please upload required documents."
            )
        
        # Step 2: Analyze with Claude
        combined_context = "\n\n---\n\n".join(all_context[:20])  # Limit total context
        
        analysis_prompt = f"""You are analyzing customer documents for UKG Pro Year-End Processing.

Customer: {request.customer_name}
Project: {request.project_name}

Based on the following document excerpts, extract key findings for the Year-End Checklist:

<documents>
{combined_context}
</documents>

Please analyze and provide a JSON response with the following structure:
{{
    "company_info": {{
        "name": "company name if found",
        "fein": "FEIN if found",
        "ar_code": "AR code if found",
        "platform": "UKG product if mentioned",
        "states": ["list of states with tax setup"]
    }},
    "tax_findings": {{
        "sui_rates_noted": ["any SUI rates mentioned"],
        "tax_codes_count": "number of tax codes if mentioned",
        "issues": ["any tax-related issues or concerns"]
    }},
    "earnings_findings": {{
        "total_codes": "count if available",
        "w2_box_mappings": ["notable W-2 box mappings like HSA, GTL"],
        "imputed_income_codes": "count of imputed income codes",
        "issues": ["any earnings-related concerns"]
    }},
    "deduction_findings": {{
        "total_codes": "count if available",
        "retirement_codes": ["401k, pension, etc."],
        "healthcare_codes": ["medical, dental, vision"],
        "issues": ["any deduction concerns"]
    }},
    "workers_comp_findings": {{
        "rates_found": true/false,
        "rate_details": ["rate info if found"],
        "issues": ["any WC concerns - uniform rates are suspicious"]
    }},
    "outstanding_items": {{
        "checks_found": true/false,
        "arrears_found": true/false,
        "check_details": "summary if found",
        "arrears_details": "summary if found"
    }},
    "critical_issues": ["list of CRITICAL items requiring immediate attention"],
    "high_priority_issues": ["list of HIGH priority items"],
    "medium_priority_issues": ["list of MEDIUM priority items"]
}}

Return ONLY valid JSON, no markdown formatting."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            temperature=0,
            messages=[{"role": "user", "content": analysis_prompt}]
        )
        
        # Parse Claude's response
        analysis_text = response.content[0].text.strip()
        
        # Clean up potential markdown
        if analysis_text.startswith("```"):
            analysis_text = analysis_text.split("```")[1]
            if analysis_text.startswith("json"):
                analysis_text = analysis_text[4:]
        analysis_text = analysis_text.strip()
        
        try:
            analysis = json.loads(analysis_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response: {e}")
            logger.error(f"Response was: {analysis_text[:500]}")
            # Use default structure
            analysis = {
                "company_info": {"name": request.customer_name},
                "critical_issues": ["Analysis parsing failed - manual review required"],
                "high_priority_issues": [],
                "medium_priority_issues": []
            }
        
        # Step 3: Generate workbook
        wb = create_year_end_workbook(analysis, request.customer_name, request.project_name)
        
        # Save to bytes
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        # Create filename
        safe_name = "".join(c if c.isalnum() else "_" for c in request.customer_name)
        filename = f"{safe_name}_Year_End_Checklist_2025.xlsx"
        
        # Build findings summary for header
        findings_summary = {
            "documents_analyzed": docs_analyzed,
            "critical_items": len(analysis.get("critical_issues", [])),
            "high_items": len(analysis.get("high_priority_issues", [])),
            "total_actions": len(analysis.get("critical_issues", [])) + len(analysis.get("high_priority_issues", [])) + len(analysis.get("medium_priority_issues", []))
        }
        
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Findings-Summary": json.dumps(findings_summary)
        }
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error generating Year-End workbook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def create_year_end_workbook(analysis: Dict[str, Any], customer_name: str, project_name: str) -> openpyxl.Workbook:
    """Create the Year-End Checklist workbook from analysis results."""
    
    wb = openpyxl.Workbook()
    default_sheet = wb.active
    wb.remove(default_sheet)
    
    # Styles
    header_font = Font(bold=True, size=11, color="FFFFFF")
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    section_fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
    critical_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
    warning_fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
    complete_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    wrap_alignment = Alignment(wrap_text=True, vertical='top')
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )
    
    company_info = analysis.get("company_info", {})
    
    # =========================================================================
    # SHEET 1: Executive Summary
    # =========================================================================
    ws1 = wb.create_sheet("Executive Summary")
    
    ws1.cell(row=1, column=1, value="YEAR-END CHECKLIST - EXECUTIVE SUMMARY").font = Font(bold=True, size=16)
    ws1.cell(row=2, column=1, value=f"Customer: {customer_name}")
    ws1.cell(row=3, column=1, value=f"Generated: {datetime.now().strftime('%B %d, %Y %H:%M')}")
    ws1.cell(row=4, column=1, value=f"Generated by: XLR8 Analysis Platform")
    
    ws1.cell(row=6, column=1, value="COMPANY INFORMATION").font = Font(bold=True, size=12)
    row = 7
    for key, val in company_info.items():
        if val and key != "states":
            ws1.cell(row=row, column=1, value=key.replace("_", " ").title())
            ws1.cell(row=row, column=2, value=str(val))
            row += 1
    if company_info.get("states"):
        ws1.cell(row=row, column=1, value="States")
        ws1.cell(row=row, column=2, value=", ".join(company_info["states"][:10]) + ("..." if len(company_info.get("states", [])) > 10 else ""))
        row += 1
    
    row += 1
    ws1.cell(row=row, column=1, value="CRITICAL ISSUES").font = Font(bold=True, size=12, color="FF0000")
    row += 1
    for issue in analysis.get("critical_issues", []):
        cell = ws1.cell(row=row, column=1, value=f"🔴 {issue}")
        cell.fill = critical_fill
        row += 1
    
    if not analysis.get("critical_issues"):
        ws1.cell(row=row, column=1, value="No critical issues identified")
        row += 1
    
    row += 1
    ws1.cell(row=row, column=1, value="HIGH PRIORITY ISSUES").font = Font(bold=True, size=12, color="FF6600")
    row += 1
    for issue in analysis.get("high_priority_issues", []):
        cell = ws1.cell(row=row, column=1, value=f"🟠 {issue}")
        cell.fill = warning_fill
        row += 1
    
    if not analysis.get("high_priority_issues"):
        ws1.cell(row=row, column=1, value="No high priority issues identified")
        row += 1
    
    row += 1
    ws1.cell(row=row, column=1, value="MEDIUM PRIORITY ISSUES").font = Font(bold=True, size=12)
    row += 1
    for issue in analysis.get("medium_priority_issues", []):
        ws1.cell(row=row, column=1, value=f"🟡 {issue}")
        row += 1
    
    ws1.column_dimensions['A'].width = 80
    ws1.column_dimensions['B'].width = 40
    
    # =========================================================================
    # SHEET 2: Before Final Payroll - Actions
    # =========================================================================
    ws2 = wb.create_sheet("Before Final Payroll")
    
    headers = ["Action ID", "Step", "Type", "Description", "Due Date", "Owner", "Status", "Findings", "Issues"]
    for col, header in enumerate(headers, 1):
        cell = ws2.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = wrap_alignment
        cell.border = thin_border
    
    # Standard Year-End Actions
    actions = [
        ("1A", "Step 1", "Recommended", "Create internal year-end team", "N/A", "Payroll Manager", "Not Started", "", ""),
        ("2A", "Step 2", "Required", "Review company and tax code information", "12/12/2025", "Payroll Team", 
         "Analysis Complete" if company_info.get("fein") else "Pending",
         f"FEIN: {company_info.get('fein', 'Not found')}, AR: {company_info.get('ar_code', 'Not found')}", 
         "; ".join(analysis.get("tax_findings", {}).get("issues", []))),
        ("2F", "Step 2", "Recommended", "Review earnings codes tax categories", "N/A", "Payroll Team",
         "Analysis Complete" if analysis.get("earnings_findings") else "Pending",
         f"Codes: {analysis.get('earnings_findings', {}).get('total_codes', 'N/A')}, W-2 mappings: {', '.join(analysis.get('earnings_findings', {}).get('w2_box_mappings', [])[:3])}",
         "; ".join(analysis.get("earnings_findings", {}).get("issues", []))),
        ("2G", "Step 2", "Recommended", "Review deduction codes tax categories", "N/A", "Payroll Team",
         "Analysis Complete" if analysis.get("deduction_findings") else "Pending",
         f"Codes: {analysis.get('deduction_findings', {}).get('total_codes', 'N/A')}",
         "; ".join(analysis.get("deduction_findings", {}).get("issues", []))),
        ("2D", "Step 2", "Recommended", "Review workers compensation rates", "N/A", "Risk Management",
         "Analysis Complete" if analysis.get("workers_comp_findings", {}).get("rates_found") else "Pending",
         "; ".join(analysis.get("workers_comp_findings", {}).get("rate_details", [])),
         "; ".join(analysis.get("workers_comp_findings", {}).get("issues", []))),
    ]
    
    for row_idx, action in enumerate(actions, 2):
        for col_idx, val in enumerate(action, 1):
            cell = ws2.cell(row=row_idx, column=col_idx, value=val)
            cell.alignment = wrap_alignment
            cell.border = thin_border
            # Color coding
            if col_idx == 7:  # Status
                if "Complete" in val:
                    cell.fill = complete_fill
                elif "Pending" in val:
                    cell.fill = warning_fill
            if col_idx == 9 and val:  # Issues
                cell.fill = critical_fill
    
    for i, width in enumerate([10, 10, 12, 50, 12, 15, 15, 40, 40], 1):
        ws2.column_dimensions[get_column_letter(i)].width = width
    
    ws2.freeze_panes = 'A2'
    
    # =========================================================================
    # SHEET 3: Tax Verification Analysis
    # =========================================================================
    ws3 = wb.create_sheet("Tax Verification")
    
    ws3.cell(row=1, column=1, value="TAX VERIFICATION ANALYSIS").font = Font(bold=True, size=14)
    ws3.cell(row=3, column=1, value="Company Information").font = Font(bold=True)
    
    row = 4
    tax_info = [
        ("Company Name", company_info.get("name", "Not extracted")),
        ("FEIN", company_info.get("fein", "Not extracted")),
        ("AR Code", company_info.get("ar_code", "Not extracted")),
        ("Platform", company_info.get("platform", "Not extracted")),
    ]
    for label, val in tax_info:
        ws3.cell(row=row, column=1, value=label)
        ws3.cell(row=row, column=2, value=val)
        row += 1
    
    row += 1
    ws3.cell(row=row, column=1, value="State Tax Setup").font = Font(bold=True)
    row += 1
    states = company_info.get("states", [])
    if states:
        ws3.cell(row=row, column=1, value=f"States configured: {len(states)}")
        row += 1
        ws3.cell(row=row, column=1, value=", ".join(states))
    else:
        ws3.cell(row=row, column=1, value="State information not extracted from documents")
    
    row += 2
    ws3.cell(row=row, column=1, value="SUI Rates Noted").font = Font(bold=True)
    row += 1
    sui_rates = analysis.get("tax_findings", {}).get("sui_rates_noted", [])
    if sui_rates:
        for rate in sui_rates:
            ws3.cell(row=row, column=1, value=rate)
            row += 1
    else:
        ws3.cell(row=row, column=1, value="No SUI rates extracted")
    
    row += 2
    ws3.cell(row=row, column=1, value="Tax Issues Identified").font = Font(bold=True, color="FF0000")
    row += 1
    tax_issues = analysis.get("tax_findings", {}).get("issues", [])
    if tax_issues:
        for issue in tax_issues:
            cell = ws3.cell(row=row, column=1, value=f"⚠️ {issue}")
            cell.fill = warning_fill
            row += 1
    else:
        cell = ws3.cell(row=row, column=1, value="✓ No tax issues identified")
        cell.fill = complete_fill
    
    ws3.column_dimensions['A'].width = 60
    ws3.column_dimensions['B'].width = 40
    
    # =========================================================================
    # SHEET 4: Earnings Analysis
    # =========================================================================
    ws4 = wb.create_sheet("Earnings Analysis")
    
    ws4.cell(row=1, column=1, value="EARNINGS CODES ANALYSIS").font = Font(bold=True, size=14)
    
    earnings = analysis.get("earnings_findings", {})
    row = 3
    ws4.cell(row=row, column=1, value="Summary").font = Font(bold=True)
    row += 1
    ws4.cell(row=row, column=1, value="Total Earnings Codes")
    ws4.cell(row=row, column=2, value=earnings.get("total_codes", "Not extracted"))
    row += 1
    ws4.cell(row=row, column=1, value="Imputed Income Codes")
    ws4.cell(row=row, column=2, value=earnings.get("imputed_income_codes", "Not extracted"))
    
    row += 2
    ws4.cell(row=row, column=1, value="W-2 Box Mappings Verified").font = Font(bold=True)
    row += 1
    w2_mappings = earnings.get("w2_box_mappings", [])
    if w2_mappings:
        for mapping in w2_mappings:
            ws4.cell(row=row, column=1, value=f"✓ {mapping}")
            row += 1
    else:
        ws4.cell(row=row, column=1, value="No specific W-2 mappings extracted")
    
    row += 2
    ws4.cell(row=row, column=1, value="Earnings Issues").font = Font(bold=True, color="FF0000")
    row += 1
    earnings_issues = earnings.get("issues", [])
    if earnings_issues:
        for issue in earnings_issues:
            cell = ws4.cell(row=row, column=1, value=f"⚠️ {issue}")
            cell.fill = warning_fill
            row += 1
    else:
        cell = ws4.cell(row=row, column=1, value="✓ No earnings issues identified")
        cell.fill = complete_fill
    
    ws4.column_dimensions['A'].width = 60
    ws4.column_dimensions['B'].width = 30
    
    # =========================================================================
    # SHEET 5: Deductions Analysis
    # =========================================================================
    ws5 = wb.create_sheet("Deductions Analysis")
    
    ws5.cell(row=1, column=1, value="DEDUCTION CODES ANALYSIS").font = Font(bold=True, size=14)
    
    deductions = analysis.get("deduction_findings", {})
    row = 3
    ws5.cell(row=row, column=1, value="Summary").font = Font(bold=True)
    row += 1
    ws5.cell(row=row, column=1, value="Total Deduction Codes")
    ws5.cell(row=row, column=2, value=deductions.get("total_codes", "Not extracted"))
    
    row += 2
    ws5.cell(row=row, column=1, value="Retirement Plan Codes").font = Font(bold=True)
    row += 1
    retirement = deductions.get("retirement_codes", [])
    if retirement:
        for code in retirement:
            ws5.cell(row=row, column=1, value=f"• {code}")
            row += 1
    else:
        ws5.cell(row=row, column=1, value="Not extracted")
    
    row += 2
    ws5.cell(row=row, column=1, value="Healthcare Codes").font = Font(bold=True)
    row += 1
    healthcare = deductions.get("healthcare_codes", [])
    if healthcare:
        for code in healthcare:
            ws5.cell(row=row, column=1, value=f"• {code}")
            row += 1
    else:
        ws5.cell(row=row, column=1, value="Not extracted")
    
    row += 2
    ws5.cell(row=row, column=1, value="Deduction Issues").font = Font(bold=True, color="FF0000")
    row += 1
    ded_issues = deductions.get("issues", [])
    if ded_issues:
        for issue in ded_issues:
            cell = ws5.cell(row=row, column=1, value=f"⚠️ {issue}")
            cell.fill = warning_fill
            row += 1
    else:
        cell = ws5.cell(row=row, column=1, value="✓ No deduction issues identified")
        cell.fill = complete_fill
    
    ws5.column_dimensions['A'].width = 60
    ws5.column_dimensions['B'].width = 30
    
    # =========================================================================
    # SHEET 6: Workers Comp Analysis
    # =========================================================================
    ws6 = wb.create_sheet("Workers Comp")
    
    ws6.cell(row=1, column=1, value="WORKERS COMPENSATION ANALYSIS").font = Font(bold=True, size=14)
    
    wc = analysis.get("workers_comp_findings", {})
    row = 3
    ws6.cell(row=row, column=1, value="Rates Found")
    ws6.cell(row=row, column=2, value="Yes" if wc.get("rates_found") else "No")
    
    row += 2
    ws6.cell(row=row, column=1, value="Rate Details").font = Font(bold=True)
    row += 1
    rate_details = wc.get("rate_details", [])
    if rate_details:
        for detail in rate_details:
            ws6.cell(row=row, column=1, value=detail)
            row += 1
    else:
        ws6.cell(row=row, column=1, value="No rate details extracted")
    
    row += 2
    ws6.cell(row=row, column=1, value="Workers Comp Issues").font = Font(bold=True, color="FF0000")
    row += 1
    wc_issues = wc.get("issues", [])
    if wc_issues:
        for issue in wc_issues:
            cell = ws6.cell(row=row, column=1, value=f"⚠️ {issue}")
            cell.fill = critical_fill
            row += 1
    else:
        cell = ws6.cell(row=row, column=1, value="✓ No workers comp issues identified")
        cell.fill = complete_fill
    
    ws6.column_dimensions['A'].width = 60
    ws6.column_dimensions['B'].width = 30
    
    # =========================================================================
    # SHEET 7: Outstanding Items
    # =========================================================================
    ws7 = wb.create_sheet("Outstanding Items")
    
    ws7.cell(row=1, column=1, value="OUTSTANDING ITEMS REVIEW").font = Font(bold=True, size=14)
    
    outstanding = analysis.get("outstanding_items", {})
    row = 3
    
    ws7.cell(row=row, column=1, value="Outstanding Checks").font = Font(bold=True)
    row += 1
    if outstanding.get("checks_found"):
        ws7.cell(row=row, column=1, value=outstanding.get("check_details", "Details in source documents"))
    else:
        ws7.cell(row=row, column=1, value="No outstanding check data found in uploaded documents")
    
    row += 3
    ws7.cell(row=row, column=1, value="Arrears").font = Font(bold=True)
    row += 1
    if outstanding.get("arrears_found"):
        ws7.cell(row=row, column=1, value=outstanding.get("arrears_details", "Details in source documents"))
    else:
        ws7.cell(row=row, column=1, value="No arrears data found in uploaded documents")
    
    row += 3
    ws7.cell(row=row, column=1, value="Required Actions").font = Font(bold=True, color="FF0000")
    row += 1
    ws7.cell(row=row, column=1, value="1. Review and reconcile all outstanding checks before year-end close")
    row += 1
    ws7.cell(row=row, column=1, value="2. Contact employees with outstanding arrears")
    row += 1
    ws7.cell(row=row, column=1, value="3. Determine write-off vs collection strategy for terminated employee arrears")
    
    ws7.column_dimensions['A'].width = 80
    
    # =========================================================================
    # SHEET 8: Required Actions Summary
    # =========================================================================
    ws8 = wb.create_sheet("Required Actions")
    
    ws8.cell(row=1, column=1, value="REQUIRED ACTIONS SUMMARY").font = Font(bold=True, size=14)
    ws8.cell(row=2, column=1, value=f"Generated: {datetime.now().strftime('%B %d, %Y')}")
    
    headers = ["Priority", "Action", "Owner", "Due Date", "Status"]
    for col, header in enumerate(headers, 1):
        cell = ws8.cell(row=4, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
    
    row = 5
    
    # Critical
    for issue in analysis.get("critical_issues", []):
        ws8.cell(row=row, column=1, value="🔴 CRITICAL").fill = critical_fill
        ws8.cell(row=row, column=2, value=issue)
        ws8.cell(row=row, column=3, value="TBD")
        ws8.cell(row=row, column=4, value="ASAP")
        ws8.cell(row=row, column=5, value="Open")
        for col in range(1, 6):
            ws8.cell(row=row, column=col).border = thin_border
        row += 1
    
    # High
    for issue in analysis.get("high_priority_issues", []):
        ws8.cell(row=row, column=1, value="🟠 HIGH").fill = warning_fill
        ws8.cell(row=row, column=2, value=issue)
        ws8.cell(row=row, column=3, value="TBD")
        ws8.cell(row=row, column=4, value="Before Final Payroll")
        ws8.cell(row=row, column=5, value="Open")
        for col in range(1, 6):
            ws8.cell(row=row, column=col).border = thin_border
        row += 1
    
    # Medium
    for issue in analysis.get("medium_priority_issues", []):
        ws8.cell(row=row, column=1, value="🟡 MEDIUM")
        ws8.cell(row=row, column=2, value=issue)
        ws8.cell(row=row, column=3, value="TBD")
        ws8.cell(row=row, column=4, value="Year-End")
        ws8.cell(row=row, column=5, value="Open")
        for col in range(1, 6):
            ws8.cell(row=row, column=col).border = thin_border
        row += 1
    
    if row == 5:  # No actions
        ws8.cell(row=row, column=1, value="✓ No outstanding actions identified")
        ws8.merge_cells(start_row=row, start_column=1, end_row=row, end_column=5)
        ws8.cell(row=row, column=1).fill = complete_fill
    
    for i, width in enumerate([15, 60, 15, 20, 12], 1):
        ws8.column_dimensions[get_column_letter(i)].width = width
    
    ws8.freeze_panes = 'A5'
    
    return wb
