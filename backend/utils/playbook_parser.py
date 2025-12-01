"""
Playbook Parser - Extract structured actions from UKG reference documents

Supports:
- Year-End Checklist (Payment Services)
- Future: Other playbook documents
"""

from docx import Document
from typing import List, Dict, Any, Optional
import logging
import re
import os

logger = logging.getLogger(__name__)


def parse_year_end_checklist(file_path: str) -> Dict[str, Any]:
    """
    Parse UKG Year-End Checklist document into structured format.
    
    Returns:
        {
            "playbook_id": "year-end-2025",
            "title": "UKG Pro Pay U.S. Year-End Checklist: Payment Services",
            "steps": [
                {
                    "step_number": "1",
                    "step_name": "Get Ready",
                    "actions": [
                        {
                            "action_id": "1A",
                            "description": "Create an internal year-end team...",
                            "full_description": "...",
                            "due_date": null,
                            "action_type": "recommended",
                            "quarter_end": false,
                            "reports_needed": ["Company Tax Verification"],
                            "keywords": ["team", "internal"]
                        }
                    ]
                }
            ],
            "total_actions": 60
        }
    """
    try:
        doc = Document(file_path)
    except Exception as e:
        logger.error(f"Failed to open document: {e}")
        raise ValueError(f"Cannot parse document: {e}")
    
    # Extract title from first paragraph
    title = "Year-End Checklist"
    for para in doc.paragraphs[:5]:
        if para.text.strip():
            title = para.text.strip()
            break
    
    # Extract step headers from paragraphs
    step_headers = {}
    for para in doc.paragraphs:
        text = para.text.strip()
        if text.startswith('Step ') and ':' in text:
            parts = text.split(':', 1)
            step_num = parts[0].replace('Step ', '').strip()
            step_name = parts[1].strip()
            step_headers[step_num] = step_name
    
    # Determine phase boundaries
    # Steps 1-8: Before Final Payroll
    # Steps 9+: After Final Payroll
    before_final = ['1', '2', '3', '4', '5', '6', '7', '8']
    
    # Extract actions from tables
    all_actions = []
    
    for table in doc.tables:
        if len(table.rows) < 2:
            continue
        
        # Check if this is an action table
        header_cells = [cell.text.strip() for cell in table.rows[0].cells]
        
        if 'Action' not in header_cells or 'Description' not in header_cells:
            continue
        
        # Find column indices
        action_idx = header_cells.index('Action')
        desc_idx = header_cells.index('Description')
        due_idx = -1
        for i, h in enumerate(header_cells):
            if 'Due Date' in h:
                due_idx = i
                break
        
        # Extract rows
        for row in table.rows[1:]:
            cells = row.cells
            action_id = cells[action_idx].text.strip()
            description = cells[desc_idx].text.strip()
            due_date = cells[due_idx].text.strip() if due_idx >= 0 else ''
            
            if not action_id or not description:
                continue
            
            # Clean action_id (remove extra spaces)
            action_id = re.sub(r'\s+', '', action_id)
            
            # Parse step number from action_id
            step_num = ''.join(c for c in action_id if c.isdigit())
            
            # Determine action type from description content
            action_type = "recommended"
            if "required" in description.lower()[:100]:
                action_type = "required"
            
            # Check if quarter-end action
            quarter_end = "quarter" in description.lower()
            
            # Extract report names mentioned
            reports_needed = extract_report_names(description)
            
            # Extract keywords for document matching
            keywords = extract_keywords(description)
            
            # Clean due date
            clean_due = None
            if due_date and due_date != '—' and due_date != '-':
                clean_due = due_date
            
            all_actions.append({
                'action_id': action_id,
                'step': step_num,
                'description': description[:300] + ('...' if len(description) > 300 else ''),
                'full_description': description,
                'due_date': clean_due,
                'action_type': action_type,
                'quarter_end': quarter_end,
                'reports_needed': reports_needed,
                'keywords': keywords,
                'phase': 'before_final_payroll' if step_num in before_final else 'after_final_payroll'
            })
    
    # Group actions by step
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
    
    # Add actions to their steps
    for action in all_actions:
        for step in steps:
            if step['step_number'] == action['step']:
                step['actions'].append(action)
                break
    
    # Sort steps by number
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
    
    # Common report patterns
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
        r'QTD Analysis',
        r'Quarter-to-Date.*Analysis',
        r'Outstanding Checks?',
        r'Arrears',
        r'Negative Wage',
        r'Multiple [Ww]orksite',
    ]
    
    for pattern in report_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        reports.extend(matches)
    
    # Deduplicate while preserving order
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
    
    # Key terms that help match customer documents
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
    ]
    
    text_lower = text.lower()
    for term in key_terms:
        if term in text_lower:
            keywords.append(term)
    
    return keywords


def get_action_search_queries(action: Dict[str, Any]) -> List[str]:
    """Generate search queries to find relevant customer documents for an action."""
    queries = []
    
    # Use reports needed
    for report in action.get('reports_needed', []):
        queries.append(report)
    
    # Use keywords
    keywords = action.get('keywords', [])
    if keywords:
        # Group related keywords
        queries.append(' '.join(keywords[:5]))
    
    # Action-specific queries based on action_id
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
    
    return queries[:5]  # Limit to 5 queries per action
