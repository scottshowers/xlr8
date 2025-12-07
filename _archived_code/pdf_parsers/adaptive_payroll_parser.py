"""
Adaptive Payroll Register Parser
Fixed tabs: Employee Summary, Earnings, Taxes, Deductions
Dynamic columns: Discovers what columns exist in each register
"""

import fitz  # PyMuPDF
import pandas as pd
import logging
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class AdaptivePayrollParser:
    """
    Parses payroll registers with vendor-agnostic approach.
    Always creates 4 tabs, but discovers columns dynamically.
    """
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.doc = None
        self.lines = []
        
    def extract(self) -> Tuple[bool, Dict[str, pd.DataFrame], Dict[str, Any]]:
        """
        Extract payroll register data.
        
        Returns:
            (success, {sheet_name: dataframe}, metadata)
            
        metadata includes:
            - accuracy: float (0-100)
            - columns_found: dict of {tab: [columns]}
            - employee_count: int
            - parsing_strategy: str
        """
        try:
            # Try pymupdf first (your working code)
            success, sheets, metadata = self._try_pymupdf_fitz()
            
            if success:
                return True, sheets, metadata
            
            # Fallback to other strategies
            logger.info("pymupdf failed, trying alternative strategies")
            return False, {}, {'accuracy': 0.0, 'error': 'All strategies failed'}
            
        except Exception as e:
            logger.error(f"Payroll parsing error: {e}")
            return False, {}, {'accuracy': 0.0, 'error': str(e)}
    
    def _try_pymupdf_fitz(self) -> Tuple[bool, Dict[str, pd.DataFrame], Dict[str, Any]]:
        """Extract using pymupdf (your working approach)."""
        try:
            # Extract text
            self.doc = fitz.open(self.pdf_path)
            text = ""
            for page in self.doc:
                text += page.get_text("text") + "\n"
            self.doc.close()
            
            self.lines = [l.strip() for l in text.split('\n') if l.strip()]
            
            if not self.lines:
                return False, {}, {}
            
            # Detect structure
            structure = self._detect_structure()
            
            if not structure['employees']:
                logger.info("No employees detected")
                return False, {}, {}
            
            # Parse all employees
            all_data = {
                'Employee Summary': [],
                'Earnings': [],
                'Taxes': [],
                'Deductions': []
            }
            
            columns_found = {
                'Employee Summary': set(),
                'Earnings': set(),
                'Taxes': set(),
                'Deductions': set()
            }
            
            for emp_name, start, end in structure['employees']:
                emp_data = self._parse_employee_section(start, end, emp_name)
                
                # Employee Summary
                all_data['Employee Summary'].append(emp_data['summary'])
                columns_found['Employee Summary'].update(emp_data['summary'].keys())
                
                # Earnings
                for row in emp_data['earnings']:
                    row['Employee Name'] = emp_name
                    all_data['Earnings'].append(row)
                    columns_found['Earnings'].update(row.keys())
                
                # Taxes
                for row in emp_data['taxes']:
                    row['Employee Name'] = emp_name
                    all_data['Taxes'].append(row)
                    columns_found['Taxes'].update(row.keys())
                
                # Deductions
                for row in emp_data['deductions']:
                    row['Employee Name'] = emp_name
                    all_data['Deductions'].append(row)
                    columns_found['Deductions'].update(row.keys())
            
            # Create DataFrames with discovered columns
            sheets = {}
            
            for tab, data in all_data.items():
                if data:
                    df = pd.DataFrame(data)
                    
                    # Reorder columns: Employee Name first (if exists), then alphabetical
                    cols = list(df.columns)
                    if 'Employee Name' in cols:
                        cols.remove('Employee Name')
                        cols = ['Employee Name'] + sorted(cols)
                    else:
                        cols = sorted(cols)
                    
                    df = df[cols]
                    sheets[tab] = df
            
            # Calculate accuracy
            accuracy = self._calculate_accuracy(sheets, len(structure['employees']))
            
            # Convert sets to lists for metadata
            columns_dict = {k: sorted(list(v)) for k, v in columns_found.items()}
            
            metadata = {
                'accuracy': accuracy,
                'employee_count': len(structure['employees']),
                'columns_found': columns_dict,
                'parsing_strategy': 'pymupdf_fitz',
                'total_rows': {k: len(v) for k, v in sheets.items()}
            }
            
            logger.info(f"pymupdf extraction: {len(sheets)} sheets, {accuracy:.1f}% accuracy")
            return True, sheets, metadata
            
        except Exception as e:
            logger.error(f"pymupdf fitz extraction failed: {e}")
            return False, {}, {}
    
    def _detect_structure(self) -> Dict[str, Any]:
        """Detect document structure (employees, sections)."""
        structure = {
            'employees': [],
            'report_totals_idx': None
        }
        
        # Find employee names (heuristic: look for Last, First pattern)
        employee_candidates = []
        for i, line in enumerate(self.lines):
            if ',' in line and not any(kw in line.lower() for kw in ['code', 'amount', 'total']):
                # Check if followed by "Emp Id" or similar employee fields
                if i + 1 < len(self.lines) and 'emp' in self.lines[i+1].lower():
                    employee_candidates.append((line, i))
        
        # Find Report Totals
        for i, line in enumerate(self.lines):
            if 'report totals' in line.lower() or 'grand total' in line.lower():
                structure['report_totals_idx'] = i
                break
        
        # Create employee sections with boundaries
        for idx, (name, start) in enumerate(employee_candidates):
            if idx < len(employee_candidates) - 1:
                end = employee_candidates[idx + 1][1]
            elif structure['report_totals_idx']:
                end = structure['report_totals_idx']
            else:
                end = len(self.lines)
            
            structure['employees'].append((name, start, end))
        
        return structure
    
    def _parse_employee_section(self, start_idx: int, end_idx: int, emp_name: str) -> Dict[str, Any]:
        """Parse all sections for one employee."""
        result = {
            'summary': {'Employee Name': emp_name},
            'earnings': [],
            'taxes': [],
            'deductions': []
        }
        
        i = start_idx + 1
        current_section = None
        section_headers = []
        
        while i < end_idx:
            line = self.lines[i]
            
            # Detect section by "Code" header
            if line == 'Code':
                # Look ahead for section headers
                section_headers = []
                j = i + 1
                while j < end_idx and j < i + 10:
                    if self._is_numeric(self.lines[j]) or self.lines[j] in ['Code']:
                        break
                    section_headers.append(self.lines[j])
                    j += 1
                
                # Determine section type
                if 'Hours' in section_headers and 'Amount' in section_headers:
                    current_section = 'earnings'
                    i = j
                elif 'Taxable' in section_headers:
                    current_section = 'taxes'
                    i = j
                elif 'Amount' in section_headers and 'YTD Amt' in section_headers:
                    current_section = 'deductions'
                    i = j
                else:
                    current_section = None
                    i += 1
                continue
            
            # Parse based on current section
            if current_section == 'earnings':
                row, next_i = self._parse_earnings_row(i, end_idx, section_headers)
                if row:
                    result['earnings'].append(row)
                    i = next_i
                else:
                    i += 1
            
            elif current_section == 'taxes':
                row, next_i = self._parse_taxes_row(i, end_idx, section_headers)
                if row:
                    result['taxes'].append(row)
                    i = next_i
                else:
                    i += 1
            
            elif current_section == 'deductions':
                row, next_i = self._parse_deductions_row(i, end_idx, section_headers)
                if row:
                    result['deductions'].append(row)
                    i = next_i
                else:
                    i += 1
            
            else:
                # Parse employee summary fields
                field_value = self._parse_field(i, end_idx)
                if field_value:
                    field, value = field_value
                    result['summary'][field] = value
                    i += 2
                else:
                    i += 1
        
        return result
    
    def _parse_earnings_row(self, start_idx: int, end_idx: int, headers: List[str]) -> Tuple[Optional[Dict], int]:
        """Parse earnings row dynamically based on headers."""
        if start_idx >= end_idx:
            return None, start_idx + 1
        
        code = self.lines[start_idx]
        
        # Stop if we hit another section
        if code in ['Vchr', 'Type', 'Totals'] or 'totals' in code.lower():
            return None, start_idx + 1
        
        row = {'Code': code}
        i = start_idx + 1
        
        # Parse values matching header count
        values = []
        for j in range(len(headers)):
            if i + j < end_idx and (self._is_numeric(self.lines[i + j]) or self.lines[i + j] == ''):
                values.append(self.lines[i + j])
            else:
                break
        
        if len(values) >= len(headers) - 1:  # Allow for some missing values
            for idx, header in enumerate(headers):
                if idx < len(values):
                    row[header] = values[idx]
                else:
                    row[header] = ''
            
            return row, i + len(values)
        
        return None, start_idx + 1
    
    def _parse_taxes_row(self, start_idx: int, end_idx: int, headers: List[str]) -> Tuple[Optional[Dict], int]:
        """Parse tax row dynamically."""
        if start_idx >= end_idx:
            return None, start_idx + 1
        
        code = self.lines[start_idx]
        
        if code in ['Code', 'Vchr', 'Type', 'Totals'] or 'totals' in code.lower():
            return None, start_idx + 1
        
        row = {'Code': code}
        i = start_idx + 1
        
        # Check for status code
        has_status = False
        if i < end_idx and '-' in self.lines[i] and len(self.lines[i]) <= 4:
            row['Status'] = self.lines[i]
            has_status = True
            i += 1
        
        # Parse remaining values
        values = []
        expected = len(headers) - (2 if has_status else 1)  # Subtract Code and Status if present
        
        for j in range(expected):
            if i + j < end_idx and self._is_numeric(self.lines[i + j]):
                values.append(self.lines[i + j])
            else:
                break
        
        if len(values) >= expected - 1:
            value_idx = 0
            for header in headers:
                if header != 'Code' and header != 'Status':
                    if value_idx < len(values):
                        row[header] = values[value_idx]
                        value_idx += 1
                    else:
                        row[header] = ''
            
            return row, i + len(values)
        
        return None, start_idx + 1
    
    def _parse_deductions_row(self, start_idx: int, end_idx: int, headers: List[str]) -> Tuple[Optional[Dict], int]:
        """Parse deduction row dynamically."""
        if start_idx >= end_idx:
            return None, start_idx + 1
        
        code = self.lines[start_idx]
        
        if code in ['Code', 'Vchr', 'Type', 'Totals'] or 'totals' in code.lower():
            return None, start_idx + 1
        
        row = {'Code': code}
        i = start_idx + 1
        
        # Parse values (typically 2: Amount, YTD Amt)
        expected = len(headers) - 1  # Subtract Code
        values = []
        
        for j in range(expected):
            if i + j < end_idx and self._is_numeric(self.lines[i + j]):
                values.append(self.lines[i + j])
            else:
                break
        
        if len(values) >= expected - 1:
            value_idx = 0
            for header in headers:
                if header != 'Code':
                    if value_idx < len(values):
                        row[header] = values[value_idx]
                        value_idx += 1
                    else:
                        row[header] = ''
            
            return row, i + len(values)
        
        return None, start_idx + 1
    
    def _parse_field(self, idx: int, end_idx: int) -> Optional[Tuple[str, str]]:
        """Parse field/value pair."""
        if idx + 1 >= end_idx:
            return None
        
        field = self.lines[idx]
        value = self.lines[idx + 1]
        
        # Check if this looks like a field/value pair
        field_keywords = ['emp id', 'salary', 'rate', 'freq', 'vchr', 'type', 'chk date', 'net', 'dir dep']
        
        if field.lower() in field_keywords:
            return (field, value)
        
        return None
    
    def _is_numeric(self, s: str) -> bool:
        """Check if string is numeric."""
        return s.replace(',', '').replace('.', '').replace('-', '').replace('$', '').isdigit()
    
    def _calculate_accuracy(self, sheets: Dict[str, pd.DataFrame], employee_count: int) -> float:
        """Calculate extraction accuracy score."""
        score = 0.0
        max_score = 100.0
        
        # Required sheets (25 points each)
        required_sheets = ['Employee Summary', 'Earnings', 'Taxes', 'Deductions']
        for sheet in required_sheets:
            if sheet in sheets and not sheets[sheet].empty:
                score += 25.0
        
        # Employee count match (bonus if > 0)
        if employee_count > 0:
            score = min(score * 1.1, max_score)  # 10% bonus
        
        # Data completeness (check for non-empty cells)
        if sheets:
            total_cells = sum(df.size for df in sheets.values())
            non_empty = sum((df != '').sum().sum() for df in sheets.values())
            if total_cells > 0:
                completeness = (non_empty / total_cells)
                score = score * completeness
        
        return min(score, max_score)
    
    def save_to_excel(self, sheets: Dict[str, pd.DataFrame], output_path: str) -> str:
        """Save sheets to Excel file."""
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            for sheet_name, df in sheets.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        return output_path


def extract_payroll_register(pdf_path: str, output_dir: str) -> Dict[str, Any]:
    """
    Extract payroll register with adaptive parsing.
    
    Returns:
        Dict with success, excel_path, metadata
    """
    try:
        parser = AdaptivePayrollParser(pdf_path)
        success, sheets, metadata = parser.extract()
        
        if not success or not sheets:
            return {
                'success': False,
                'error': 'No data extracted',
                'metadata': metadata
            }
        
        # Save to Excel
        pdf_name = Path(pdf_path).stem
        output_path = Path(output_dir) / f"{pdf_name}_parsed.xlsx"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        parser.save_to_excel(sheets, str(output_path))
        
        # Build table info
        table_info = []
        for sheet_name, df in sheets.items():
            table_info.append({
                'sheet_name': sheet_name,
                'rows': len(df),
                'columns': len(df.columns),
                'headers': list(df.columns)
            })
        
        return {
            'success': True,
            'excel_path': str(output_path),
            'table_count': len(sheets),
            'table_info': table_info,
            'metadata': metadata
        }
        
    except Exception as e:
        logger.error(f"Payroll extraction failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }
