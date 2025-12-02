"""
Playbook Parser - Extract structured actions from UKG Year-End Checklist

Parses Excel workbook with multiple tabs:
- Before Final Payroll tabs
- After Final Payroll tabs
- Payment Services tabs
- etc.

Column A = Action ID (1A, 2B, etc.)
Column B = Full Description (THE COMPLETE TEXT - NO TRUNCATION)
"""

import pandas as pd
from typing import List, Dict, Any, Optional
import logging
import re
import os

logger = logging.getLogger(__name__)


def parse_year_end_checklist(file_path: str) -> Dict[str, Any]:
    """
    Parse UKG Year-End Checklist Excel workbook into structured format.
    
    Reads ALL tabs and extracts FULL descriptions from Column B.
    
    Returns:
        {
            "playbook_id": "year-end-2025",
            "title": "UKG Pro Pay U.S. Year-End Checklist",
            "steps": [
                {
                    "step_number": "1",
                    "step_name": "Get Ready",
                    "phase": "before_final_payroll",
                    "actions": [
                        {
                            "action_id": "1A",
                            "description": "FULL TEXT - NO TRUNCATION",
                            "due_date": null,
                            "action_type": "recommended",
                            "reports_needed": [...],
                            "keywords": [...]
                        }
                    ]
                }
            ],
            "total_actions": 60
        }
    """
    file_ext = os.path.splitext(file_path)[1].lower()
    
    if file_ext in ['.xlsx', '.xls', '.xlsm']:
        return parse_excel_workbook(file_path)
    elif file_ext == '.docx':
        return parse_docx_document(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_ext}")


def parse_excel_workbook(file_path: str) -> Dict[str, Any]:
    """
    Parse Excel workbook with multiple tabs.
    
    Tab naming conventions typically indicate phase:
    - "Before" in name → before_final_payroll
    - "After" in name → after_final_payroll
    - Step numbers 1-8 → before_final_payroll
    - Step numbers 9+ → after_final_payroll
    """
    try:
        # Read all sheets
        xl = pd.ExcelFile(file_path)
        sheet_names = xl.sheet_names
        logger.info(f"[PARSER] Found {len(sheet_names)} sheets: {sheet_names}")
    except Exception as e:
        logger.error(f"[PARSER] Failed to open Excel file: {e}")
        raise ValueError(f"Cannot parse Excel file: {e}")
    
    all_actions = []
    step_headers = {}
    title = "UKG Pro Pay U.S. Year-End Checklist"
    
    # Process each sheet
    for sheet_name in sheet_names:
        logger.info(f"[PARSER] Processing sheet: {sheet_name}")
        
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
        except Exception as e:
            logger.warning(f"[PARSER] Could not read sheet {sheet_name}: {e}")
            continue
        
        if df.empty:
            continue
        
        # Try to find the action column (usually A) and description column (usually B)
        # Column names might vary, so we look for patterns
        
        # First, try to identify columns by header content
        action_col = None
        desc_col = None
        due_col = None
        
        # Check first row for headers
        headers = df.columns.tolist()
        
        for i, header in enumerate(headers):
            header_str = str(header).lower().strip()
            if 'action' in header_str or header_str == 'a':
                action_col = i
            elif 'description' in header_str or header_str == 'b':
                desc_col = i
            elif 'due' in header_str or 'date' in header_str:
                due_col = i
        
        # If no headers found, assume Column A (0) = Action, Column B (1) = Description
        if action_col is None and len(headers) >= 1:
            action_col = 0
        if desc_col is None and len(headers) >= 2:
            desc_col = 1
        
        if action_col is None or desc_col is None:
            logger.warning(f"[PARSER] Could not identify columns in sheet {sheet_name}")
            continue
        
        # Determine phase from sheet name
        sheet_lower = sheet_name.lower()
        if 'before' in sheet_lower:
            default_phase = 'before_final_payroll'
        elif 'after' in sheet_lower:
            default_phase = 'after_final_payroll'
        else:
            default_phase = None  # Will determine from step number
        
        # Process each row
        for idx, row in df.iterrows():
            action_id = str(row.iloc[action_col]).strip() if pd.notna(row.iloc[action_col]) else ''
            description = str(row.iloc[desc_col]).strip() if pd.notna(row.iloc[desc_col]) else ''
            due_date = str(row.iloc[due_col]).strip() if due_col and due_col < len(row) and pd.notna(row.iloc[due_col]) else ''
            
            # Skip header rows and empty rows
            if not action_id or action_id.lower() in ['action', 'nan', 'none', '']:
                continue
            if not description or description.lower() in ['description', 'nan', 'none', '']:
                continue
            
            # Validate action_id format (should be like 1A, 2B, 10A, etc.)
            action_id_clean = re.sub(r'\s+', '', action_id)
            if not re.match(r'^\d+[A-Za-z]$', action_id_clean):
                # Check if this might be a step header
                if action_id_clean.lower().startswith('step'):
                    # Extract step info
                    match = re.match(r'step\s*(\d+)\s*[:\-]?\s*(.*)', action_id_clean, re.IGNORECASE)
                    if match:
                        step_num = match.group(1)
                        step_name = match.group(2).strip() or description[:50]
                        step_headers[step_num] = step_name
                continue
            
            # Parse step number from action_id
            step_num = ''.join(c for c in action_id_clean if c.isdigit())
            
            # Determine phase
            if default_phase:
                phase = default_phase
            else:
                # Steps 1-8 are before final payroll, 9+ are after
                try:
                    phase = 'before_final_payroll' if int(step_num) <= 8 else 'after_final_payroll'
                except:
                    phase = 'before_final_payroll'
            
            # Determine action type from description
            action_type = "recommended"
            if "required" in description.lower()[:200]:
                action_type = "required"
            
            # Check if quarter-end action
            quarter_end = "quarter" in description.lower()
            
            # Extract report names mentioned
            reports_needed = extract_report_names(description)
            
            # Extract keywords for document matching
            keywords = extract_keywords(description)
            
            # Clean due date
            clean_due = None
            if due_date and due_date not in ['—', '-', 'nan', 'None', '']:
                clean_due = due_date
            
            all_actions.append({
                'action_id': action_id_clean.upper(),
                'step': step_num,
                'description': description,  # FULL TEXT - NO TRUNCATION
                'due_date': clean_due,
                'action_type': action_type,
                'quarter_end': quarter_end,
                'reports_needed': reports_needed,
                'keywords': keywords,
                'phase': phase,
                'source_sheet': sheet_name
            })
            
            logger.debug(f"[PARSER] Extracted action {action_id_clean}: {len(description)} chars")
    
    logger.info(f"[PARSER] Extracted {len(all_actions)} total actions")
    
    # Deduplicate actions (same action might appear in multiple sheets)
    seen_actions = {}
    unique_actions = []
    for action in all_actions:
        aid = action['action_id']
        if aid not in seen_actions:
            seen_actions[aid] = action
            unique_actions.append(action)
        else:
            # Merge - keep longer description
            if len(action['description']) > len(seen_actions[aid]['description']):
                seen_actions[aid] = action
                # Update in unique_actions list
                for i, ua in enumerate(unique_actions):
                    if ua['action_id'] == aid:
                        unique_actions[i] = action
                        break
    
    logger.info(f"[PARSER] After deduplication: {len(unique_actions)} unique actions")
    
    # Group actions by step
    steps = []
    seen_steps = set()
    
    for action in unique_actions:
        step_num = action['step']
        if step_num not in seen_steps:
            seen_steps.add(step_num)
            steps.append({
                'step_number': step_num,
                'step_name': step_headers.get(step_num, f'Step {step_num}'),
                'phase': action['phase'],
                'actions': []
            })
    
    # Add actions to their steps
    for action in unique_actions:
        for step in steps:
            if step['step_number'] == action['step']:
                step['actions'].append(action)
                break
    
    # Sort steps by number
    steps.sort(key=lambda s: int(s['step_number']) if s['step_number'].isdigit() else 999)
    
    # Sort actions within each step
    for step in steps:
        step['actions'].sort(key=lambda a: a['action_id'])
    
    return {
        'playbook_id': 'year-end-2025',
        'title': title,
        'steps': steps,
        'total_actions': len(unique_actions),
        'source_file': os.path.basename(file_path)
    }


def parse_docx_document(file_path: str) -> Dict[str, Any]:
    """
    Legacy parser for DOCX files.
    Falls back to this if Excel parsing fails.
    """
    from docx import Document
    
    try:
        doc = Document(file_path)
    except Exception as e:
        logger.error(f"[PARSER] Failed to open DOCX: {e}")
        raise ValueError(f"Cannot parse DOCX: {e}")
    
    title = "Year-End Checklist"
    for para in doc.paragraphs[:5]:
        if para.text.strip():
            title = para.text.strip()
            break
    
    step_headers = {}
    for para in doc.paragraphs:
        text = para.text.strip()
        if text.startswith('Step ') and ':' in text:
            parts = text.split(':', 1)
            step_num = parts[0].replace('Step ', '').strip()
            step_name = parts[1].strip()
            step_headers[step_num] = step_name
    
    before_final = ['1', '2', '3', '4', '5', '6', '7', '8']
    all_actions = []
    
    for table in doc.tables:
        if len(table.rows) < 2:
            continue
        
        header_cells = [cell.text.strip() for cell in table.rows[0].cells]
        
        if 'Action' not in header_cells or 'Description' not in header_cells:
            continue
        
        action_idx = header_cells.index('Action')
        desc_idx = header_cells.index('Description')
        due_idx = -1
        for i, h in enumerate(header_cells):
            if 'Due Date' in h:
                due_idx = i
                break
        
        for row in table.rows[1:]:
            cells = row.cells
            action_id = cells[action_idx].text.strip()
            description = cells[desc_idx].text.strip()
            due_date = cells[due_idx].text.strip() if due_idx >= 0 else ''
            
            if not action_id or not description:
                continue
            
            action_id = re.sub(r'\s+', '', action_id)
            step_num = ''.join(c for c in action_id if c.isdigit())
            
            action_type = "recommended"
            if "required" in description.lower()[:200]:
                action_type = "required"
            
            quarter_end = "quarter" in description.lower()
            reports_needed = extract_report_names(description)
            keywords = extract_keywords(description)
            
            clean_due = None
            if due_date and due_date not in ['—', '-']:
                clean_due = due_date
            
            all_actions.append({
                'action_id': action_id,
                'step': step_num,
                'description': description,  # FULL TEXT - NO TRUNCATION
                'due_date': clean_due,
                'action_type': action_type,
                'quarter_end': quarter_end,
                'reports_needed': reports_needed,
                'keywords': keywords,
                'phase': 'before_final_payroll' if step_num in before_final else 'after_final_payroll'
            })
    
    steps = []
    seen_steps = set()
    
    for action in all_actions:
        step_num = action['step']
        if step_num not in seen_steps:
            seen_steps.add(step_num)
            steps.append({
                'step_number': step_num,
                'step_name': step_headers.get(step_num, f'Step {step_num}'),
                'phase': action['phase'],
                'actions': []
            })
    
    for action in all_actions:
        for step in steps:
            if step['step_number'] == action['step']:
                step['actions'].append(action)
                break
    
    steps.sort(key=lambda s: int(s['step_number']) if s['step_number'].isdigit() else 999)
    
    return {
        'playbook_id': 'year-end-2025',
        'title': title,
        'steps': steps,
        'total_actions': len(all_actions),
        'source_file': os.path.basename(file_path)
    }


def extract_report_names(text: str) -> List[str]:
    """Extract UKG report names mentioned in description."""
    reports = []
    
    report_patterns = [
        r'Company Tax Verification',
        r'Company Master Profile',
        r'Workers[\' ]* Compensation Risk Rates',
        r'Earnings Tax Categor(?:y|ies)',
        r'Earnings Tax Category Exceptions',
        r'Deduction Tax Categor(?:y|ies)',
        r'Earnings Codes?',
        r'Deduction Codes?',
        r'W-2 [\w\s]+ Report',
        r'Year-End Validation',
        r'YE Validation',
        r'QTD Analysis',
        r'Quarter-to-Date.*Analysis',
        r'Outstanding Checks?',
        r'Arrears',
        r'Negative Wage',
        r'Multiple [Ww]orksite',
        r'MWR',
        r'1099[\-\s]?[A-Z]+',
        r'ACA\s+[\w\s]+Report',
        r'1095-[A-C]',
    ]
    
    for pattern in report_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        reports.extend(matches)
    
    seen = set()
    unique_reports = []
    for r in reports:
        r_lower = r.lower()
        if r_lower not in seen:
            seen.add(r_lower)
            unique_reports.append(r)
    
    return unique_reports


def extract_keywords(text: str) -> List[str]:
    """Extract keywords for document matching."""
    keywords = []
    
    key_terms = [
        'tax', 'fein', 'ein', 'sui', 'suta', 'sdi',
        'earnings', 'deduction', 'benefit',
        'w-2', 'w2', '1099', '1099-misc', '1099-nec', '1099-r',
        'workers comp', 'work comp',
        'healthcare', 'medical', 'dental', 'vision', 'hsa', 'fsa',
        'ssn', 'social security',
        'address', 'employee',
        'arrears', 'outstanding', 'check',
        'adjustment', 'reconcile',
        '401k', '401(k)', 'retirement', 'pension',
        'tip', 'tips', 'gross receipts',
        'puerto rico', 'virgin islands', 'guam',
        'third party sick', 'tps',
        'withholding', 'exempt',
        'ale', 'affordable care', 'aca',
        '1095', 'healthcare reporting',
    ]
    
    text_lower = text.lower()
    for term in key_terms:
        if term in text_lower:
            keywords.append(term)
    
    return keywords


def get_action_search_queries(action: Dict[str, Any]) -> List[str]:
    """Generate search queries to find relevant customer documents for an action."""
    queries = []
    
    for report in action.get('reports_needed', []):
        queries.append(report)
    
    keywords = action.get('keywords', [])
    if keywords:
        queries.append(' '.join(keywords[:5]))
    
    action_id = action.get('action_id', '')
    
    specific_queries = {
        '2A': ['company tax verification', 'FEIN tax code', 'company master profile'],
        '2B': ['company information tax reporting'],
        '2C': ['tax code information'],
        '2D': ['workers compensation rates'],
        '2E': ['multiple worksite MWR'],
        '2F': ['earnings codes tax categories'],
        '2G': ['deduction codes tax categories'],
        '2H': ['special tax categories'],
        '2J': ['healthcare benefit deductions'],
        '3A': ['social security SSN validation'],
        '3B': ['employee address validation'],
        '5B': ['negative wages W-2'],
        '5C': ['outstanding checks non-reconciled'],
        '5D': ['arrears outstanding balance'],
    }
    
    if action_id in specific_queries:
        queries.extend(specific_queries[action_id])
    
    return queries[:5]
