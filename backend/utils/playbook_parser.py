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
            # Try without read_only first (matches structured_data_handler)
            try:
                conn = duckdb.connect(DUCKDB_PATH)
                return conn
            except Exception as e1:
                # If that fails, try read_only
                try:
                    conn = duckdb.connect(DUCKDB_PATH, read_only=True)
                    return conn
                except Exception as e2:
                    logger.error(f"[PARSER] Both connection modes failed: {e1}, {e2}")
                    return None
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


def load_step_documents() -> Dict[str, List[Dict[str, Any]]]:
    """
    Load Step_Documents sheet from DuckDB.
    Returns dict: step_number -> list of {keyword, description, required}
    
    This sheet defines which documents are needed per step.
    """
    conn = get_duckdb_connection()
    if not conn:
        logger.warning("[PARSER] No DuckDB connection for Step_Documents")
        return {}
    
    try:
        # Find the Step_Documents table
        result = conn.execute("""
            SELECT table_name, columns
            FROM _schema_metadata
            WHERE is_current = TRUE
            AND LOWER(project) = 'global'
            AND LOWER(sheet_name) LIKE '%step_documents%'
            LIMIT 1
        """).fetchone()
        
        if not result:
            logger.info("[PARSER] No Step_Documents sheet found - using legacy report extraction")
            return {}
        
        table_name, columns_json = result
        logger.info(f"[PARSER] Found Step_Documents table: {table_name}")
        
        # Read all rows
        rows = conn.execute(f'SELECT * FROM "{table_name}"').fetchall()
        
        # Get column names
        col_info = conn.execute(f"PRAGMA table_info('{table_name}')").fetchall()
        col_names = [c[1].lower() for c in col_info]
        
        logger.info(f"[PARSER] Step_Documents columns: {col_names}")
        
        # Find column indices
        step_idx = next((i for i, c in enumerate(col_names) if 'step' in c), 0)
        keyword_idx = next((i for i, c in enumerate(col_names) if 'keyword' in c or 'document' in c), 1)
        desc_idx = next((i for i, c in enumerate(col_names) if 'desc' in c), 2) if len(col_names) > 2 else None
        req_idx = next((i for i, c in enumerate(col_names) if 'req' in c), 3) if len(col_names) > 3 else None
        
        # Build step -> documents mapping
        step_docs = {}
        
        for row in rows:
            try:
                step = str(row[step_idx]).strip()
                keyword = str(row[keyword_idx]).strip() if row[keyword_idx] else ''
                
                # Skip header rows or empty
                if not step or not keyword:
                    continue
                if step.lower() in ['step', 'action']:
                    continue
                
                # Normalize step number (remove any letters, take first number)
                step_num = ''.join(c for c in step if c.isdigit())[:2]
                if not step_num:
                    continue
                
                description = str(row[desc_idx]).strip() if desc_idx and row[desc_idx] else ''
                required = str(row[req_idx]).strip().lower() in ['yes', 'true', '1', 'y'] if req_idx and row[req_idx] else False
                
                if step_num not in step_docs:
                    step_docs[step_num] = []
                
                step_docs[step_num].append({
                    'keyword': keyword,
                    'description': description,
                    'required': required
                })
                
            except Exception as e:
                logger.warning(f"[PARSER] Error parsing Step_Documents row: {e}")
                continue
        
        logger.info(f"[PARSER] Loaded Step_Documents: {len(step_docs)} steps with documents")
        for step, docs in step_docs.items():
            logger.info(f"[PARSER]   Step {step}: {len(docs)} document types")
        
        return step_docs
        
    except Exception as e:
        logger.error(f"[PARSER] Error loading Step_Documents: {e}")
        return {}
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
        all_fast_track = []
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
                
                logger.warning(f"[PARSER] {len(rows)} rows, ALL columns: {col_names}")
                
                # Find Fast Track column indices - try by name first, then by position
                ft_col_indices = {}
                for i, name in enumerate(col_names):
                    name_lower = name.lower().replace(' ', '_').replace('-', '_')
                    if 'ft_action_id' in name_lower or name_lower == 'ft_action_id':
                        ft_col_indices['ft_id'] = i
                    elif 'ft_description' in name_lower:
                        ft_col_indices['description'] = i
                    elif 'ft_sequence' in name_lower:
                        ft_col_indices['sequence'] = i
                    elif 'ft_ukg_actionref' in name_lower or 'ft_ukg_action_ref' in name_lower:
                        ft_col_indices['ukg_action_ref'] = i
                    elif 'ft_sql_script' in name_lower:
                        ft_col_indices['sql_script'] = i
                    elif 'ft_notes' in name_lower:
                        ft_col_indices['notes'] = i
                
                # POSITIONAL FALLBACK: If no FT columns found by name but we have 12+ columns,
                # use known positions: G=6, H=7, I=8, J=9, K=10, L=11
                if not ft_col_indices and len(col_names) >= 12:
                    logger.warning(f"[PARSER] Using positional fallback for Fast Track columns")
                    ft_col_indices = {
                        'ft_id': 6,        # Column G = FT_Action_ID
                        'description': 7,  # Column H = FT_Description
                        'sequence': 8,     # Column I = FT_Sequence
                        'ukg_action_ref': 9,  # Column J = FT_UKG_ActionRef
                        'sql_script': 10,  # Column K = FT_SQL_Script
                        'notes': 11        # Column L = FT_Notes
                    }
                
                logger.warning(f"[PARSER] Fast Track columns: {ft_col_indices}")
                
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
                    
                    # Extract Fast Track data if columns exist and FT_Action_ID is populated
                    if ft_col_indices.get('ft_id') is not None:
                        ft_id_idx = ft_col_indices['ft_id']
                        ft_id_raw = str(row[ft_id_idx]).strip() if len(row) > ft_id_idx and row[ft_id_idx] else ''
                        
                        # Debug: log first few FT values we see
                        if action_id_clean in ['1A', '2A', '3A']:
                            logger.warning(f"[PARSER] Row {action_id_clean}: ft_id_idx={ft_id_idx}, ft_id_raw='{ft_id_raw}'")
                        
                        if ft_id_raw and ft_id_raw.lower() not in ['', 'none', 'nan', 'ft_action_id']:
                            ft_item = {
                                'ft_id': ft_id_raw,
                                'description': '',
                                'sequence': 0,
                                'ukg_action_ref': [],
                                'sql_script': None,
                                'notes': '',
                                'reports_needed': reports_needed  # Inherit from parent action
                            }
                            
                            # Get FT description
                            if 'description' in ft_col_indices:
                                idx = ft_col_indices['description']
                                if len(row) > idx and row[idx]:
                                    ft_item['description'] = str(row[idx]).strip()
                            
                            # Get FT sequence
                            if 'sequence' in ft_col_indices:
                                idx = ft_col_indices['sequence']
                                if len(row) > idx and row[idx]:
                                    try:
                                        ft_item['sequence'] = int(float(str(row[idx]).strip()))
                                    except:
                                        pass
                            
                            # Get UKG action refs (comma-separated)
                            if 'ukg_action_ref' in ft_col_indices:
                                idx = ft_col_indices['ukg_action_ref']
                                if len(row) > idx and row[idx]:
                                    refs = str(row[idx]).strip()
                                    if refs and refs.lower() not in ['none', 'nan']:
                                        ft_item['ukg_action_ref'] = [r.strip() for r in refs.split(',') if r.strip()]
                            
                            # Get SQL script
                            if 'sql_script' in ft_col_indices:
                                idx = ft_col_indices['sql_script']
                                if len(row) > idx and row[idx]:
                                    script = str(row[idx]).strip()
                                    if script and script.lower() not in ['none', 'nan']:
                                        ft_item['sql_script'] = script
                            
                            # Get notes
                            if 'notes' in ft_col_indices:
                                idx = ft_col_indices['notes']
                                if len(row) > idx and row[idx]:
                                    notes_val = str(row[idx]).strip()
                                    if notes_val and notes_val.lower() not in ['none', 'nan']:
                                        ft_item['notes'] = notes_val
                            
                            # Only add if we have a description or can use the action description
                            if not ft_item['description']:
                                ft_item['description'] = description[:100]  # Use action description as fallback
                            
                            all_fast_track.append(ft_item)
                            logger.warning(f"[PARSER] ⚡ Added Fast Track item: {ft_id_raw} seq={ft_item['sequence']} refs={ft_item['ukg_action_ref']}")
                    
            except Exception as e:
                logger.error(f"[PARSER] Error processing {table_name}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                continue
        
        logger.info(f"[PARSER] Extracted {len(all_actions)} actions from DuckDB")
        logger.warning(f"[PARSER] Extracted {len(all_fast_track)} Fast Track items (before dedup)")
        
        if not all_actions:
            logger.warning("[PARSER] No actions extracted, using default")
            return get_default_structure()
        
        # Deduplicate Fast Track by ft_id (keep first occurrence)
        seen_ft_ids = set()
        unique_fast_track = []
        for ft in all_fast_track:
            if ft['ft_id'] not in seen_ft_ids:
                seen_ft_ids.add(ft['ft_id'])
                unique_fast_track.append(ft)
        
        logger.warning(f"[PARSER] Fast Track after dedup: {len(unique_fast_track)} items")
        
        # Sort Fast Track by sequence
        unique_fast_track.sort(key=lambda x: x.get('sequence', 999))
        
        # Load Step_Documents mapping
        step_documents = load_step_documents()
        
        # Build step structure with document mappings
        return build_playbook_structure(all_actions, file_name, step_documents, unique_fast_track)
        
    except Exception as e:
        logger.exception(f"[PARSER] Error parsing Year-End from DuckDB: {e}")
        return get_default_structure()
    finally:
        conn.close()


def build_playbook_structure(actions: List[Dict], source_file: str, step_documents: Dict[str, List[Dict]] = None, fast_track: List[Dict] = None) -> Dict[str, Any]:
    """Build the final playbook structure from parsed actions"""
    
    step_documents = step_documents or {}
    fast_track = fast_track or []
    
    steps = []
    seen_steps = set()
    
    for action in actions:
        step_num = action['step']
        if step_num not in seen_steps:
            seen_steps.add(step_num)
            
            # Get documents for this step from Step_Documents sheet
            step_docs = step_documents.get(step_num, [])
            
            steps.append({
                'step_number': step_num,
                'step_name': get_step_name(step_num),
                'phase': action['phase'],
                'actions': [],
                'required_documents': step_docs  # NEW: documents needed for this step
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
        'fast_track': fast_track,
        'total_actions': len(actions),
        'source_file': source_file,
        'source_type': 'duckdb',
        'has_step_documents': len(step_documents) > 0,
        'has_fast_track': len(fast_track) > 0
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
        'fast_track': [],
        'total_actions': 2,
        'source_file': 'default_structure',
        'source_type': 'fallback',
        'has_fast_track': False
    }


# =============================================================================
# DOCUMENT MATCHING UTILITIES
# =============================================================================

def match_documents_to_step(step_documents: List[Dict], uploaded_files: List[str]) -> Dict[str, Any]:
    """
    Match uploaded files against step document requirements.
    
    Args:
        step_documents: List of {keyword, description, required} from Step_Documents sheet
        uploaded_files: List of actual uploaded filenames
    
    Returns:
        {
            'matched': [{keyword, description, required, matched_file}, ...],
            'missing': [{keyword, description, required}, ...],
            'stats': {total, matched, missing, required_matched, required_missing}
        }
    """
    matched = []
    missing = []
    
    for doc in step_documents:
        keyword = doc.get('keyword', '').lower()
        if not keyword:
            continue
        
        # Check if any uploaded file matches this keyword
        matched_file = None
        for filename in uploaded_files:
            filename_lower = filename.lower()
            # Simple keyword matching
            if keyword in filename_lower:
                matched_file = filename
                break
            # Also check individual words for multi-word keywords
            keyword_words = keyword.split()
            if len(keyword_words) > 1:
                matches = sum(1 for w in keyword_words if w in filename_lower)
                if matches >= len(keyword_words) - 1:  # Allow 1 word missing
                    matched_file = filename
                    break
        
        doc_info = {
            'keyword': doc.get('keyword'),
            'description': doc.get('description', ''),
            'required': doc.get('required', False)
        }
        
        if matched_file:
            doc_info['matched_file'] = matched_file
            matched.append(doc_info)
        else:
            missing.append(doc_info)
    
    # Calculate stats
    total = len(step_documents)
    required_docs = [d for d in step_documents if d.get('required')]
    required_matched = sum(1 for m in matched if m.get('required'))
    required_missing = sum(1 for m in missing if m.get('required'))
    
    return {
        'matched': matched,
        'missing': missing,
        'stats': {
            'total': total,
            'matched': len(matched),
            'missing': len(missing),
            'required_total': len(required_docs),
            'required_matched': required_matched,
            'required_missing': required_missing
        }
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
