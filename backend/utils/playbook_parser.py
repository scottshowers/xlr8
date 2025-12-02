"""
Playbook Parser - Extract structured actions from Year-End Checklist

READS FROM DUCKDB - Not from original Excel files.

The Excel file has been processed into DuckDB tables. This parser:
1. Finds the Year-End Checklist tables in DuckDB (project='GLOBAL')
2. Reads the data from each sheet/table
3. Decrypts encrypted description column
4. Parses Action ID and Description
5. Returns structured playbook data

Author: XLR8 Team
"""

import os
import re
import json
import logging
import base64
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# DuckDB path (must match structured_data_handler.py)
DUCKDB_PATH = "/data/structured_data.duckdb"
ENCRYPTION_KEY_PATH = "/data/.encryption_key_v2"


def get_encryption_key() -> Optional[bytes]:
    """Load the encryption key for decrypting PII fields."""
    try:
        if os.path.exists(ENCRYPTION_KEY_PATH):
            with open(ENCRYPTION_KEY_PATH, 'rb') as f:
                return f.read()
        else:
            logger.warning(f"[PARSER] Encryption key not found at {ENCRYPTION_KEY_PATH}")
            return None
    except Exception as e:
        logger.error(f"[PARSER] Failed to load encryption key: {e}")
        return None


def decrypt_value(encrypted_value: str, key: bytes) -> str:
    """
    Decrypt an ENC256: prefixed value.
    Format: ENC256: + base64(nonce + ciphertext + tag)
    Uses AES-256-GCM
    """
    if not encrypted_value or not encrypted_value.startswith('ENC256:'):
        return encrypted_value
    
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        
        # Remove prefix and decode
        encoded = encrypted_value[7:]  # Remove "ENC256:"
        data = base64.b64decode(encoded)
        
        # Extract components (nonce=12 bytes, tag=16 bytes at end)
        nonce = data[:12]
        ciphertext_with_tag = data[12:]
        
        # Decrypt
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext_with_tag, None)
        
        return plaintext.decode('utf-8')
    except Exception as e:
        logger.warning(f"[PARSER] Decryption failed: {e}")
        return encrypted_value  # Return as-is if decryption fails


def get_duckdb_connection():
    """Get DuckDB connection"""
    try:
        import duckdb
        
        if os.path.exists(DUCKDB_PATH):
            conn = duckdb.connect(DUCKDB_PATH, read_only=True)
            return conn
        else:
            logger.warning(f"[PARSER] DuckDB not found at {DUCKDB_PATH}")
            return None
    except Exception as e:
        logger.error(f"[PARSER] Failed to connect to DuckDB: {e}")
        return None


def find_year_end_tables() -> List[Dict[str, Any]]:
    """
    Find Year-End Checklist tables in DuckDB.
    Returns list of table info for Before/After Final Payroll sheets.
    """
    conn = get_duckdb_connection()
    if not conn:
        return []
    
    try:
        # Get the specific year-end tables we know exist
        result = conn.execute("""
            SELECT 
                project,
                file_name,
                sheet_name,
                table_name,
                columns,
                row_count
            FROM _schema_metadata
            WHERE is_current = TRUE
            AND LOWER(project) = 'global'
            AND (
                LOWER(sheet_name) LIKE '%before%payroll%'
                OR LOWER(sheet_name) LIKE '%after%payroll%'
            )
            ORDER BY sheet_name
        """).fetchall()
        
        tables = []
        for row in result:
            project, file_name, sheet_name, table_name, columns_json, row_count = row
            tables.append({
                'project': project,
                'file_name': file_name,
                'sheet_name': sheet_name,
                'table_name': table_name,
                'columns': json.loads(columns_json) if columns_json else [],
                'row_count': row_count
            })
        
        logger.info(f"[PARSER] Found {len(tables)} Year-End tables")
        for t in tables:
            logger.info(f"[PARSER]   - {t['sheet_name']}: {t['row_count']} rows")
        
        return tables
        
    except Exception as e:
        logger.error(f"[PARSER] Error finding Year-End tables: {e}")
        return []
    finally:
        conn.close()


def parse_year_end_from_duckdb() -> Dict[str, Any]:
    """
    Parse Year-End Checklist from DuckDB tables.
    
    Column mapping (based on actual data):
    - Column 0 (due_date): Actually the Action ID (1A, 1B, etc.)
    - Column 1 (long name): Description (ENCRYPTED)
    - Column 2 (unnamed_2): Due Date
    - Column 3 (unnamed_3): Action Type (Required/Recommended)
    - Column 4 (unnamed_4): Quarter-End flag
    - Column 5 (unnamed_5): Completed flag
    """
    tables = find_year_end_tables()
    
    if not tables:
        logger.warning("[PARSER] No Year-End tables found")
        return get_default_structure()
    
    conn = get_duckdb_connection()
    if not conn:
        return get_default_structure()
    
    # Load encryption key for decrypting descriptions
    encryption_key = get_encryption_key()
    if not encryption_key:
        logger.warning("[PARSER] No encryption key - descriptions may be encrypted")
    
    try:
        all_actions = []
        file_name = tables[0]['file_name'] if tables else 'unknown'
        
        for table_info in tables:
            table_name = table_info['table_name']
            sheet_name = table_info['sheet_name']
            
            logger.info(f"[PARSER] Processing: {sheet_name}")
            
            # Determine phase from sheet name
            sheet_lower = sheet_name.lower()
            if 'before' in sheet_lower:
                phase = 'before_final_payroll'
            elif 'after' in sheet_lower:
                phase = 'after_final_payroll'
            else:
                phase = 'general'
            
            # Query all rows - we'll filter in Python
            try:
                rows = conn.execute(f'SELECT * FROM "{table_name}"').fetchall()
                
                # Get column names
                col_info = conn.execute(f"PRAGMA table_info('{table_name}')").fetchall()
                col_names = [c[1] for c in col_info]
                
                logger.info(f"[PARSER] {len(rows)} rows, columns: {col_names[:3]}...")
                
                # Find the description column (it's the one with the super long name)
                desc_col_idx = None
                for i, name in enumerate(col_names):
                    if len(name) > 50 or 'due_date_is_listed' in name.lower():
                        desc_col_idx = i
                        break
                
                if desc_col_idx is None and len(col_names) > 1:
                    desc_col_idx = 1  # Default to second column
                
                logger.info(f"[PARSER] Description column index: {desc_col_idx}")
                
                for row in rows:
                    # Column 0 is Action ID
                    action_id_raw = str(row[0]).strip() if row[0] else ''
                    
                    # Skip header rows and empty rows
                    if not action_id_raw:
                        continue
                    if action_id_raw.lower() in ['action', 'action type', 'quarter-end', 'completed', 'due date', 'type']:
                        continue
                    if action_id_raw.lower().startswith('step '):
                        continue
                    if action_id_raw.lower().startswith('if a due date'):
                        continue
                    
                    # Validate action_id format (1A, 2B, 10A, etc.)
                    action_id_clean = re.sub(r'\s+', '', action_id_raw)
                    if not re.match(r'^\d+[A-Za-z]$', action_id_clean):
                        continue
                    
                    # Get description (may be encrypted)
                    description_raw = str(row[desc_col_idx]).strip() if desc_col_idx and row[desc_col_idx] else ''
                    
                    # Decrypt if needed
                    if description_raw.startswith('ENC256:') and encryption_key:
                        description = decrypt_value(description_raw, encryption_key)
                    else:
                        description = description_raw
                    
                    if not description or description.startswith('ENC256:'):
                        logger.warning(f"[PARSER] No description for {action_id_clean}")
                        continue
                    
                    # Get other fields
                    due_date = None
                    action_type = 'recommended'
                    quarter_end = False
                    
                    # unnamed_2 = Due Date
                    if len(row) > 2 and row[2]:
                        due_str = str(row[2]).strip()
                        if due_str and due_str != '—' and due_str != '-':
                            due_date = due_str
                    
                    # unnamed_3 = Action Type
                    if len(row) > 3 and row[3]:
                        type_str = str(row[3]).strip().lower()
                        if 'required' in type_str:
                            action_type = 'required'
                    
                    # unnamed_4 = Quarter-End
                    if len(row) > 4 and row[4]:
                        qe_str = str(row[4]).strip().lower()
                        if 'quarter' in qe_str:
                            quarter_end = True
                    
                    # Parse step number
                    step_num = ''.join(c for c in action_id_clean if c.isdigit())
                    
                    # Extract report names and keywords
                    reports_needed = extract_report_names(description)
                    keywords = extract_keywords(description)
                    
                    all_actions.append({
                        'action_id': action_id_clean.upper(),
                        'step': step_num,
                        'description': description,
                        'due_date': due_date,
                        'action_type': action_type,
                        'quarter_end': quarter_end,
                        'reports_needed': reports_needed,
                        'keywords': keywords,
                        'phase': phase,
                        'source_sheet': sheet_name
                    })
                    
            except Exception as e:
                logger.error(f"[PARSER] Error processing {table_name}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                continue
        
        logger.info(f"[PARSER] Extracted {len(all_actions)} actions from DuckDB")
        
        if not all_actions:
            logger.warning("[PARSER] No actions extracted, using default")
            return get_default_structure()
        
        # Build step structure
        return build_playbook_structure(all_actions, file_name)
        
    except Exception as e:
        logger.exception(f"[PARSER] Error parsing Year-End from DuckDB: {e}")
        return get_default_structure()
    finally:
        conn.close()


def build_playbook_structure(actions: List[Dict], source_file: str) -> Dict[str, Any]:
    """Build the final playbook structure from parsed actions"""
    
    steps = []
    seen_steps = set()
    
    for action in actions:
        step_num = action['step']
        if step_num not in seen_steps:
            seen_steps.add(step_num)
            steps.append({
                'step_number': step_num,
                'step_name': get_step_name(step_num),
                'phase': action['phase'],
                'actions': []
            })
    
    # Add actions to their steps
    for action in actions:
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
        'title': 'UKG Pro Pay U.S. Year-End Checklist: Payment Services',
        'steps': steps,
        'total_actions': len(actions),
        'source_file': source_file,
        'source_type': 'duckdb'
    }


def get_step_name(step_num: str) -> str:
    """Get descriptive step name based on step number"""
    step_names = {
        '1': 'Get Ready',
        '2': 'Review and Update Company Information',
        '3': 'Review and Update Employee Information',
        '4': 'Process Final Payroll',
        '5': 'Year-End Adjustments',
        '6': 'Benefits & ACA Reporting',
        '7': 'Generate Tax Forms',
        '8': 'Submit & File',
        '9': 'Update Employee Form Delivery Options',
        '10': 'Update Employee Tax Withholding Elections',
        '11': 'Update Year-End Tax Codes',
        '12': 'Post Year-End Cleanup',
    }
    return step_names.get(step_num, f'Step {step_num}')


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
    
    # Deduplicate
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


def get_default_structure() -> Dict[str, Any]:
    """Return default structure if parsing fails"""
    return {
        'playbook_id': 'year-end-2025',
        'title': 'UKG Pro Pay U.S. Year-End Checklist: Payment Services',
        'steps': [
            {
                'step_number': '1',
                'step_name': 'Get Ready',
                'phase': 'before_final_payroll',
                'actions': [
                    {
                        'action_id': '1A',
                        'step': '1',
                        'description': 'Create an internal year-end team with representation from relevant departments (Payroll, HR, Accounting, Finance, IT). Assign roles and responsibilities.',
                        'due_date': None,
                        'action_type': 'recommended',
                        'quarter_end': True,
                        'reports_needed': [],
                        'keywords': ['team', 'internal'],
                        'phase': 'before_final_payroll',
                        'source_sheet': 'default'
                    }
                ]
            },
            {
                'step_number': '2',
                'step_name': 'Review and Update Company Information',
                'phase': 'before_final_payroll',
                'actions': [
                    {
                        'action_id': '2A',
                        'step': '2',
                        'description': 'Run the Company Tax Verification report and Company Master Profile report. Review all company information for accuracy including FEIN, company name, address, and state tax IDs.',
                        'due_date': None,
                        'action_type': 'required',
                        'quarter_end': False,
                        'reports_needed': ['Company Tax Verification', 'Company Master Profile'],
                        'keywords': ['tax', 'fein', 'company'],
                        'phase': 'before_final_payroll',
                        'source_sheet': 'default'
                    }
                ]
            }
        ],
        'total_actions': 2,
        'source_file': 'default_structure',
        'source_type': 'fallback'
    }


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def parse_year_end_checklist(file_path: str = None) -> Dict[str, Any]:
    """
    Parse Year-End Checklist.
    
    PRIMARY: Read from DuckDB (structured data already loaded)
    FALLBACK: Default structure if DuckDB doesn't have it
    
    This function is called by playbooks.py
    """
    logger.info("[PARSER] Parsing Year-End Checklist from DuckDB...")
    result = parse_year_end_from_duckdb()
    
    if result.get('source_type') != 'fallback' and result.get('total_actions', 0) > 2:
        logger.info(f"[PARSER] SUCCESS: {result['total_actions']} actions from DuckDB")
        return result
    
    logger.warning("[PARSER] DuckDB parse failed, using default structure")
    return get_default_structure()
