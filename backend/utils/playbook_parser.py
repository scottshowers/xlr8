"""
Playbook Parser - Extract structured actions from Year-End Checklist

READS FROM DUCKDB - Not from original Excel files.

The Excel file has been processed into DuckDB tables. This parser:
1. Finds the Year-End Checklist tables in DuckDB (project='GLOBAL')
2. Reads the data from each sheet/table
3. Parses Action ID (Column A) and Description (Column B)
4. Returns structured playbook data

Author: XLR8 Team
"""

import os
import re
import json
import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# DuckDB path (must match structured_data_handler.py)
DUCKDB_PATH = "/data/structured_data.duckdb"


def get_duckdb_connection():
    """Get DuckDB connection"""
    try:
        import duckdb
        
        logger.info(f"[PARSER] Checking DuckDB at: {DUCKDB_PATH}")
        
        if os.path.exists(DUCKDB_PATH):
            logger.info(f"[PARSER] DuckDB file exists, size: {os.path.getsize(DUCKDB_PATH)} bytes")
            conn = duckdb.connect(DUCKDB_PATH, read_only=True)
            logger.info(f"[PARSER] DuckDB connection successful")
            return conn
        else:
            logger.warning(f"[PARSER] DuckDB not found at {DUCKDB_PATH}")
            # Check alternative paths
            alt_paths = [
                "/app/data/structured_data.duckdb",
                "./data/structured_data.duckdb",
                "/data/duckdb/structured_data.duckdb"
            ]
            for alt in alt_paths:
                if os.path.exists(alt):
                    logger.info(f"[PARSER] Found DuckDB at alternative path: {alt}")
                    return duckdb.connect(alt, read_only=True)
            
            logger.warning(f"[PARSER] DuckDB not found at any known location")
            return None
    except Exception as e:
        logger.error(f"[PARSER] Failed to connect to DuckDB: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def find_year_end_tables() -> List[Dict[str, Any]]:
    """
    Find Year-End Checklist tables in DuckDB.
    
    Searches _schema_metadata for:
    - project = 'GLOBAL' (or variations)
    - file_name contains year-end keywords
    
    Returns list of table info dicts.
    """
    conn = get_duckdb_connection()
    if not conn:
        return []
    
    try:
        # First, let's see what projects exist
        try:
            projects = conn.execute("SELECT DISTINCT project FROM _schema_metadata").fetchall()
            logger.info(f"[PARSER] Available projects in DuckDB: {[p[0] for p in projects]}")
        except Exception as e:
            logger.warning(f"[PARSER] Could not list projects: {e}")
        
        # Search for global year-end tables - be VERY flexible
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
            AND (
                -- Match Global project (case-insensitive)
                LOWER(project) = 'global' 
                OR LOWER(project) = '__global__'
                OR LOWER(project) LIKE '%global%'
                -- Also check if file looks like Year-End regardless of project
                OR (
                    LOWER(file_name) LIKE '%year%end%'
                    OR LOWER(file_name) LIKE '%year-end%'
                    OR LOWER(file_name) LIKE '%yearend%'
                    OR LOWER(file_name) LIKE '%checklist%'
                    OR LOWER(file_name) LIKE '%pro_pay%'
                    OR LOWER(file_name) LIKE '%pro-pay%'
                )
            )
            ORDER BY sheet_name
        """).fetchall()
        
        if not result:
            # Fallback: just get ALL tables and log them
            logger.warning("[PARSER] No Year-End tables found with filters, checking all tables...")
            all_tables = conn.execute("""
                SELECT project, file_name, sheet_name, table_name, row_count
                FROM _schema_metadata
                WHERE is_current = TRUE
                LIMIT 20
            """).fetchall()
            logger.info(f"[PARSER] Sample of ALL tables in DuckDB:")
            for t in all_tables:
                logger.info(f"[PARSER]   project={t[0]}, file={t[1]}, sheet={t[2]}")
        
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
        
        logger.info(f"[PARSER] Found {len(tables)} Year-End Checklist tables in DuckDB")
        for t in tables:
            logger.info(f"[PARSER]   - {t['sheet_name']}: {t['table_name']} ({t['row_count']} rows)")
        
        return tables
        
    except Exception as e:
        logger.error(f"[PARSER] Error finding Year-End tables: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []
    finally:
        conn.close()


def parse_year_end_from_duckdb() -> Dict[str, Any]:
    """
    Parse Year-End Checklist from DuckDB tables.
    
    Returns structured playbook data with FULL descriptions.
    """
    tables = find_year_end_tables()
    
    if not tables:
        logger.warning("[PARSER] No Year-End Checklist tables found in DuckDB")
        return get_default_structure()
    
    conn = get_duckdb_connection()
    if not conn:
        return get_default_structure()
    
    try:
        all_actions = []
        file_name = tables[0]['file_name'] if tables else 'unknown'
        
        # Process each sheet/table
        for table_info in tables:
            table_name = table_info['table_name']
            sheet_name = table_info['sheet_name']
            columns = table_info['columns']
            
            logger.info(f"[PARSER] Processing table: {table_name} (sheet: {sheet_name})")
            
            # Determine phase from sheet name
            sheet_lower = sheet_name.lower()
            if 'before' in sheet_lower:
                phase = 'before_final_payroll'
            elif 'after' in sheet_lower:
                phase = 'after_final_payroll'
            else:
                phase = 'general'
            
            # Get column names for the table
            col_names = []
            for col in columns:
                if isinstance(col, dict):
                    col_names.append(col.get('name', col.get('original', 'unknown')))
                else:
                    col_names.append(str(col))
            
            logger.info(f"[PARSER] Columns: {col_names[:5]}...")
            
            # Find action and description columns
            action_col = find_column_by_pattern(col_names, ['action', 'step', 'item', 'id'])
            desc_col = find_column_by_pattern(col_names, ['description', 'desc', 'detail', 'task', 'activity'])
            due_col = find_column_by_pattern(col_names, ['due', 'date', 'deadline'])
            
            # If no matches, assume first two columns
            if not action_col and len(col_names) >= 1:
                action_col = col_names[0]
            if not desc_col and len(col_names) >= 2:
                desc_col = col_names[1]
            
            if not action_col or not desc_col:
                logger.warning(f"[PARSER] Could not identify columns in {table_name}")
                continue
            
            logger.info(f"[PARSER] Using columns: action={action_col}, desc={desc_col}, due={due_col}")
            
            # Query table data
            try:
                # Build safe query (columns might have special chars)
                safe_action = f'"{action_col}"'
                safe_desc = f'"{desc_col}"'
                safe_due = f'"{due_col}"' if due_col else 'NULL'
                
                query = f'SELECT {safe_action}, {safe_desc}, {safe_due} as due_date FROM "{table_name}"'
                rows = conn.execute(query).fetchall()
                
                logger.info(f"[PARSER] Retrieved {len(rows)} rows from {table_name}")
                
                for row in rows:
                    action_id = str(row[0]).strip() if row[0] else ''
                    description = str(row[1]).strip() if row[1] else ''
                    due_date = str(row[2]).strip() if row[2] and str(row[2]).strip() not in ['None', 'nan', ''] else None
                    
                    # Skip header rows and empty rows
                    if not action_id or action_id.lower() in ['action', 'step', 'item', 'nan', 'none', '']:
                        continue
                    if not description or description.lower() in ['description', 'nan', 'none', '']:
                        continue
                    
                    # Validate action_id format (should be like 1A, 2B, 10A, etc.)
                    action_id_clean = re.sub(r'\s+', '', action_id)
                    if not re.match(r'^\d+[A-Za-z]$', action_id_clean):
                        continue
                    
                    # Parse step number from action_id
                    step_num = ''.join(c for c in action_id_clean if c.isdigit())
                    
                    # Override phase based on step number if not determined by sheet
                    if phase == 'general':
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
                    
                    all_actions.append({
                        'action_id': action_id_clean.upper(),
                        'step': step_num,
                        'description': description,  # FULL TEXT - NO TRUNCATION
                        'due_date': due_date,
                        'action_type': action_type,
                        'quarter_end': quarter_end,
                        'reports_needed': reports_needed,
                        'keywords': keywords,
                        'phase': phase,
                        'source_sheet': sheet_name
                    })
                    
            except Exception as e:
                logger.error(f"[PARSER] Error querying table {table_name}: {e}")
                continue
        
        logger.info(f"[PARSER] Extracted {len(all_actions)} total actions from DuckDB")
        
        # Deduplicate actions (same action might appear in multiple sheets)
        seen_actions = {}
        unique_actions = []
        for action in all_actions:
            aid = action['action_id']
            if aid not in seen_actions:
                seen_actions[aid] = action
                unique_actions.append(action)
            else:
                # Keep longer description
                if len(action['description']) > len(seen_actions[aid]['description']):
                    seen_actions[aid] = action
                    for i, ua in enumerate(unique_actions):
                        if ua['action_id'] == aid:
                            unique_actions[i] = action
                            break
        
        logger.info(f"[PARSER] After deduplication: {len(unique_actions)} unique actions")
        
        # Build step structure
        return build_playbook_structure(unique_actions, file_name)
        
    except Exception as e:
        logger.exception(f"[PARSER] Error parsing Year-End from DuckDB: {e}")
        return get_default_structure()
    finally:
        conn.close()


def find_column_by_pattern(columns: List[str], patterns: List[str]) -> Optional[str]:
    """Find a column that matches any of the patterns"""
    for col in columns:
        col_lower = col.lower()
        for pattern in patterns:
            if pattern in col_lower:
                return col
    return None


def build_playbook_structure(actions: List[Dict], source_file: str) -> Dict[str, Any]:
    """Build the final playbook structure from parsed actions"""
    
    # Extract step headers from actions
    step_headers = {}
    steps = []
    seen_steps = set()
    
    for action in actions:
        step_num = action['step']
        if step_num not in seen_steps:
            seen_steps.add(step_num)
            
            # Generate step name based on step number
            step_name = get_step_name(step_num)
            step_headers[step_num] = step_name
            
            steps.append({
                'step_number': step_num,
                'step_name': step_name,
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
        '2': 'Verify Company & Tax Information',
        '3': 'Verify Employee Information',
        '4': 'Process Final Payroll',
        '5': 'Year-End Adjustments',
        '6': 'Benefits & ACA',
        '7': 'Generate Tax Forms',
        '8': 'Submit & File',
        '9': 'Post Year-End',
        '10': 'New Year Setup',
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
                        'description': 'Create an internal year-end team with representation from relevant departments (Payroll, HR, Accounting, Finance, IT). Assign roles and responsibilities for year-end tasks.',
                        'due_date': None,
                        'action_type': 'recommended',
                        'quarter_end': False,
                        'reports_needed': [],
                        'keywords': ['team', 'internal'],
                        'phase': 'before_final_payroll',
                        'source_sheet': 'default'
                    }
                ]
            },
            {
                'step_number': '2',
                'step_name': 'Verify Company & Tax Information',
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
# LEGACY SUPPORT - File-based parsing (fallback if DuckDB not available)
# =============================================================================

def parse_year_end_checklist(file_path: str = None) -> Dict[str, Any]:
    """
    Parse Year-End Checklist.
    
    PRIMARY: Read from DuckDB (structured data already loaded)
    FALLBACK: Read from file if DuckDB doesn't have it
    
    This function is called by playbooks.py
    """
    # First, try DuckDB (preferred - data is already there)
    logger.info("[PARSER] Attempting to parse from DuckDB...")
    result = parse_year_end_from_duckdb()
    
    if result.get('source_type') != 'fallback' and result.get('total_actions', 0) > 2:
        logger.info(f"[PARSER] Successfully parsed {result['total_actions']} actions from DuckDB")
        return result
    
    # Fallback: try to read from file
    if file_path:
        logger.info(f"[PARSER] DuckDB parse incomplete, trying file: {file_path}")
        
        if not os.path.exists(file_path):
            logger.warning("[PARSER] File not found, using default structure")
            return get_default_structure()
        
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext in ['.xlsx', '.xls', '.xlsm']:
            return parse_excel_file(file_path)
        elif file_ext == '.docx':
            return parse_docx_file(file_path)
    
    logger.warning("[PARSER] No valid source found, using default structure")
    return get_default_structure()


def parse_excel_file(file_path: str) -> Dict[str, Any]:
    """Parse Excel file directly (fallback)"""
    try:
        import pandas as pd
        
        xl = pd.ExcelFile(file_path)
        sheet_names = xl.sheet_names
        logger.info(f"[PARSER] Reading Excel with {len(sheet_names)} sheets")
        
        all_actions = []
        
        for sheet_name in sheet_names:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            if df.empty or len(df.columns) < 2:
                continue
            
            # Assume first column is Action, second is Description
            action_col = df.columns[0]
            desc_col = df.columns[1]
            
            sheet_lower = sheet_name.lower()
            if 'before' in sheet_lower:
                phase = 'before_final_payroll'
            elif 'after' in sheet_lower:
                phase = 'after_final_payroll'
            else:
                phase = 'general'
            
            for idx, row in df.iterrows():
                action_id = str(row[action_col]).strip() if pd.notna(row[action_col]) else ''
                description = str(row[desc_col]).strip() if pd.notna(row[desc_col]) else ''
                
                if not action_id or action_id.lower() in ['action', 'nan', 'none', '']:
                    continue
                if not description or description.lower() in ['description', 'nan', 'none', '']:
                    continue
                
                action_id_clean = re.sub(r'\s+', '', action_id)
                if not re.match(r'^\d+[A-Za-z]$', action_id_clean):
                    continue
                
                step_num = ''.join(c for c in action_id_clean if c.isdigit())
                
                if phase == 'general':
                    try:
                        phase = 'before_final_payroll' if int(step_num) <= 8 else 'after_final_payroll'
                    except:
                        phase = 'before_final_payroll'
                
                all_actions.append({
                    'action_id': action_id_clean.upper(),
                    'step': step_num,
                    'description': description,
                    'due_date': None,
                    'action_type': 'required' if 'required' in description.lower()[:200] else 'recommended',
                    'quarter_end': 'quarter' in description.lower(),
                    'reports_needed': extract_report_names(description),
                    'keywords': extract_keywords(description),
                    'phase': phase,
                    'source_sheet': sheet_name
                })
        
        return build_playbook_structure(all_actions, os.path.basename(file_path))
        
    except Exception as e:
        logger.error(f"[PARSER] Excel parsing failed: {e}")
        return get_default_structure()


def parse_docx_file(file_path: str) -> Dict[str, Any]:
    """Parse DOCX file (legacy fallback)"""
    try:
        from docx import Document
        
        doc = Document(file_path)
        all_actions = []
        
        for table in doc.tables:
            if len(table.rows) < 2:
                continue
            
            header_cells = [cell.text.strip() for cell in table.rows[0].cells]
            
            if 'Action' not in header_cells or 'Description' not in header_cells:
                continue
            
            action_idx = header_cells.index('Action')
            desc_idx = header_cells.index('Description')
            
            for row in table.rows[1:]:
                cells = row.cells
                action_id = cells[action_idx].text.strip()
                description = cells[desc_idx].text.strip()
                
                if not action_id or not description:
                    continue
                
                action_id_clean = re.sub(r'\s+', '', action_id)
                if not re.match(r'^\d+[A-Za-z]$', action_id_clean):
                    continue
                
                step_num = ''.join(c for c in action_id_clean if c.isdigit())
                
                all_actions.append({
                    'action_id': action_id_clean.upper(),
                    'step': step_num,
                    'description': description,
                    'due_date': None,
                    'action_type': 'required' if 'required' in description.lower()[:200] else 'recommended',
                    'quarter_end': 'quarter' in description.lower(),
                    'reports_needed': extract_report_names(description),
                    'keywords': extract_keywords(description),
                    'phase': 'before_final_payroll' if int(step_num) <= 8 else 'after_final_payroll',
                    'source_sheet': 'docx'
                })
        
        return build_playbook_structure(all_actions, os.path.basename(file_path))
        
    except Exception as e:
        logger.error(f"[PARSER] DOCX parsing failed: {e}")
        return get_default_structure()
