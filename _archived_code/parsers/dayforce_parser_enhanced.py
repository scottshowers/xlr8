"""
Dayforce Register Parser - pdfplumber Implementation
Handles complex multi-section horizontal layout with side-by-side employees
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    logger.warning("pdfplumber not available - install with: pip install pdfplumber")


class DayforceParserEnhanced:
    """
    pdfplumber-based parser for Dayforce payroll registers.
    Uses table detection and position-based extraction.
    """
    
    def __init__(self):
        """Initialize parser with section headers."""
        self.section_headers = {
            'employee_info': ['Employee', 'Emp #', 'Department', 'Dept', 'SSN', 'Status'],
            'earnings': ['Earnings', 'Hours', 'Rate', 'Amount', 'Regular', 'Overtime'],
            'taxes': ['Taxes', 'Federal', 'FICA', 'State', 'Local', 'Medicare'],
            'deductions': ['Deductions', '401k', 'Insurance', 'Uniform', 'Pre-Tax']
        }
    
    def parse(self, pdf_path: str, output_dir: str = '/data/parsed_registers') -> Dict[str, Any]:
        """
        Parse Dayforce register using pdfplumber.
        
        Args:
            pdf_path: Path to PDF file
            output_dir: Directory for Excel output
            
        Returns:
            Dict with status, output_path, accuracy, and employee_count
        """
        if not PDFPLUMBER_AVAILABLE:
            return {
                'status': 'error',
                'message': 'pdfplumber not installed',
                'accuracy': 0,
                'employee_count': 0
            }
        
        try:
            logger.info(f"Opening Dayforce PDF with pdfplumber: {pdf_path}")
            
            # Open PDF
            with pdfplumber.open(pdf_path) as pdf:
                all_employees = []
                
                # Process each page
                for page_num, page in enumerate(pdf.pages):
                    logger.info(f"Processing page {page_num + 1}")
                    
                    # Extract employees from this page
                    page_employees = self._extract_page_employees(page)
                    all_employees.extend(page_employees)
                
                logger.info(f"Found {len(all_employees)} employees")
            
            if not all_employees:
                logger.warning("No employee data extracted")
                return {
                    'status': 'error',
                    'message': 'No employee data found in PDF',
                    'accuracy': 0,
                    'employee_count': 0
                }
            
            # Create 4-tab structure
            tabs = self._create_four_tabs(all_employees)
            
            # Write to Excel
            output_path = self._write_excel(tabs, pdf_path, output_dir)
            
            # Calculate accuracy
            accuracy = self._calculate_accuracy(tabs, all_employees)
            
            return {
                'status': 'success',
                'output_path': output_path,
                'accuracy': accuracy,
                'employee_count': len(all_employees),
                'tabs': {k: len(v) for k, v in tabs.items()}
            }
            
        except Exception as e:
            logger.error(f"Parse error: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': str(e),
                'accuracy': 0,
                'employee_count': 0
            }
    
    def _extract_page_employees(self, page) -> List[Dict[str, Any]]:
        """
        Extract all employees from a page using pdfplumber's table detection.
        """
        employees = []
        
        # Get all text with position info
        words = page.extract_words(x_tolerance=3, y_tolerance=3)
        
        # Get tables (pdfplumber's auto-detection)
        tables = page.extract_tables()
        
        # If tables found, parse them
        if tables:
            logger.info(f"Found {len(tables)} tables on page")
            employees = self._parse_tables_for_employees(tables, words)
        else:
            # Fall back to text-based extraction
            logger.info("No tables found, using text-based extraction")
            text = page.extract_text()
            employees = self._parse_text_for_employees(text, words)
        
        return employees
    
    def _parse_tables_for_employees(self, tables: List[List[List[str]]], words: List[Dict]) -> List[Dict[str, Any]]:
        """
        Parse employee data from detected tables.
        """
        employees = []
        
        # Look for employee identifiers in tables
        for table_idx, table in enumerate(tables):
            if not table:
                continue
            
            logger.info(f"Parsing table {table_idx + 1} with {len(table)} rows")
            
            # Check if this table contains employee data
            # Look for employee ID pattern in any cell
            for row_idx, row in enumerate(table):
                if not row:
                    continue
                
                # Join row cells to search for employee ID
                row_text = ' '.join([str(cell) if cell else '' for cell in row])
                
                # Check if this row starts a new employee
                if self._is_employee_header(row_text):
                    # Extract this employee's data
                    employee = self._extract_employee_from_table(table, row_idx)
                    if employee:
                        employees.append(employee)
        
        return employees
    
    def _parse_text_for_employees(self, text: str, words: List[Dict]) -> List[Dict[str, Any]]:
        """
        Fall back to text-based extraction if tables not detected.
        """
        employees = []
        
        # Split text into lines
        lines = text.split('\n')
        
        # Find employee boundaries by looking for ID pattern
        employee_starts = []
        for i, line in enumerate(lines):
            if self._is_employee_header(line):
                employee_starts.append(i)
        
        # If we found employee headers, parse each section
        if employee_starts:
            for i, start_idx in enumerate(employee_starts):
                # Determine end of this employee's section
                end_idx = employee_starts[i + 1] if i + 1 < len(employee_starts) else len(lines)
                
                # Extract this employee's data
                employee_lines = lines[start_idx:end_idx]
                employee = self._extract_employee_from_lines(employee_lines)
                
                if employee:
                    employees.append(employee)
        
        return employees
    
    def _is_employee_header(self, text: str) -> bool:
        """Check if text contains employee header indicators."""
        # Look for employee ID pattern
        patterns = [
            r'Emp\s*#?\s*:?\s*\d+',
            r'Employee\s+ID\s*:?\s*\d+',
            r'EmpID\s*:?\s*\d+'
        ]
        
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def _extract_employee_from_table(self, table: List[List[str]], start_row: int) -> Dict[str, Any]:
        """Extract employee data starting from a specific table row."""
        employee = {
            'info': {},
            'earnings': [],
            'taxes': [],
            'deductions': []
        }
        
        # Parse employee info section (usually first few rows)
        info_rows = table[start_row:min(start_row + 10, len(table))]
        
        for row in info_rows:
            if not row:
                continue
            
            row_text = ' '.join([str(cell) if cell else '' for cell in row])
            
            # Extract employee ID
            emp_id_match = re.search(r'(?:Emp\s*#?|Employee\s+ID)[\s:]+(\d+)', row_text, re.IGNORECASE)
            if emp_id_match:
                employee['info']['employee_id'] = emp_id_match.group(1)
            
            # Extract name
            name_match = re.search(r'(?:Name|Employee)[\s:]+([A-Za-z\s,]+?)(?:\s{2,}|\||$)', row_text, re.IGNORECASE)
            if name_match:
                employee['info']['name'] = name_match.group(1).strip()
            
            # Extract department
            dept_match = re.search(r'(?:Dept|Department)[\s:]+([^\n\|]+)', row_text, re.IGNORECASE)
            if dept_match:
                employee['info']['department'] = dept_match.group(1).strip()
        
        # Parse earnings, taxes, deductions sections
        # Look for section headers in the table
        for row_idx in range(start_row, len(table)):
            row = table[row_idx]
            if not row:
                continue
            
            row_text = ' '.join([str(cell) if cell else '' for cell in row])
            
            # Identify section type
            section_type = self._identify_section(row_text)
            
            if section_type == 'earnings':
                earning = self._parse_earning_row(row)
                if earning:
                    employee['earnings'].append(earning)
            
            elif section_type == 'taxes':
                tax = self._parse_tax_row(row)
                if tax:
                    employee['taxes'].append(tax)
            
            elif section_type == 'deductions':
                deduction = self._parse_deduction_row(row)
                if deduction:
                    employee['deductions'].append(deduction)
        
        # Only return if we have at least employee ID
        if employee['info'].get('employee_id'):
            return employee
        
        return None
    
    def _extract_employee_from_lines(self, lines: List[str]) -> Dict[str, Any]:
        """Extract employee data from text lines."""
        employee = {
            'info': {},
            'earnings': [],
            'taxes': [],
            'deductions': []
        }
        
        # Parse employee info
        for line in lines[:10]:  # Check first 10 lines for info
            # Extract employee ID
            emp_id_match = re.search(r'(?:Emp\s*#?|Employee\s+ID)[\s:]+(\d+)', line, re.IGNORECASE)
            if emp_id_match:
                employee['info']['employee_id'] = emp_id_match.group(1)
            
            # Extract name
            name_match = re.search(r'(?:Name|Employee)[\s:]+([A-Za-z\s,]+?)(?:\s{2,}|$)', line, re.IGNORECASE)
            if name_match:
                employee['info']['name'] = name_match.group(1).strip()
            
            # Extract department
            dept_match = re.search(r'(?:Dept|Department)[\s:]+([^\n]+)', line, re.IGNORECASE)
            if dept_match:
                employee['info']['department'] = dept_match.group(1).strip()
        
        # Parse sections
        current_section = None
        
        for line in lines:
            # Identify section
            section = self._identify_section(line)
            if section:
                current_section = section
                continue
            
            # Parse line based on current section
            if current_section == 'earnings':
                earning = self._parse_earning_line(line)
                if earning:
                    employee['earnings'].append(earning)
            
            elif current_section == 'taxes':
                tax = self._parse_tax_line(line)
                if tax:
                    employee['taxes'].append(tax)
            
            elif current_section == 'deductions':
                deduction = self._parse_deduction_line(line)
                if deduction:
                    employee['deductions'].append(deduction)
        
        # Only return if we have at least employee ID
        if employee['info'].get('employee_id'):
            return employee
        
        return None
    
    def _identify_section(self, text: str) -> str:
        """Identify which section this text belongs to."""
        text_lower = text.lower()
        
        # Check for section keywords
        if any(keyword.lower() in text_lower for keyword in self.section_headers['earnings']):
            if 'hours' in text_lower or 'rate' in text_lower or 'regular' in text_lower:
                return 'earnings'
        
        if any(keyword.lower() in text_lower for keyword in self.section_headers['taxes']):
            if 'federal' in text_lower or 'fica' in text_lower or 'state' in text_lower:
                return 'taxes'
        
        if any(keyword.lower() in text_lower for keyword in self.section_headers['deductions']):
            if '401k' in text_lower or 'insurance' in text_lower or 'deduction' in text_lower:
                return 'deductions'
        
        return None
    
    def _parse_earning_row(self, row: List[str]) -> Dict[str, Any]:
        """Parse earning from table row."""
        if not row or len(row) < 2:
            return None
        
        # Typical structure: [Description, Rate, Hours, Amount, Hours YTD, Amount YTD]
        earning = {
            'description': row[0] if len(row) > 0 else '',
            'rate': self._clean_number(row[1]) if len(row) > 1 else 0,
            'hours': self._clean_number(row[2]) if len(row) > 2 else 0,
            'amount': self._clean_number(row[3]) if len(row) > 3 else 0,
            'hours_ytd': self._clean_number(row[4]) if len(row) > 4 else 0,
            'amount_ytd': self._clean_number(row[5]) if len(row) > 5 else 0
        }
        
        # Only return if has description and amount
        if earning['description'] and (earning['amount'] or earning['hours']):
            return earning
        
        return None
    
    def _parse_earning_line(self, line: str) -> Dict[str, Any]:
        """Parse earning from text line."""
        # Try to extract numbers from line
        numbers = re.findall(r'[\d,]+\.?\d*', line)
        
        # Extract description (text before first number)
        desc_match = re.match(r'^([A-Za-z\s]+)', line)
        description = desc_match.group(1).strip() if desc_match else ''
        
        if not description or not numbers:
            return None
        
        # Convert numbers
        nums = [self._clean_number(n) for n in numbers]
        
        earning = {
            'description': description,
            'rate': nums[0] if len(nums) > 0 else 0,
            'hours': nums[1] if len(nums) > 1 else 0,
            'amount': nums[2] if len(nums) > 2 else 0,
            'hours_ytd': nums[3] if len(nums) > 3 else 0,
            'amount_ytd': nums[4] if len(nums) > 4 else 0
        }
        
        return earning
    
    def _parse_tax_row(self, row: List[str]) -> Dict[str, Any]:
        """Parse tax from table row."""
        if not row or len(row) < 2:
            return None
        
        # Typical structure: [Description, Wages, Amount, Wages YTD, Amount YTD]
        tax = {
            'description': row[0] if len(row) > 0 else '',
            'wages': self._clean_number(row[1]) if len(row) > 1 else 0,
            'amount': self._clean_number(row[2]) if len(row) > 2 else 0,
            'wages_ytd': self._clean_number(row[3]) if len(row) > 3 else 0,
            'amount_ytd': self._clean_number(row[4]) if len(row) > 4 else 0
        }
        
        if tax['description'] and tax['amount']:
            return tax
        
        return None
    
    def _parse_tax_line(self, line: str) -> Dict[str, Any]:
        """Parse tax from text line."""
        numbers = re.findall(r'[\d,]+\.?\d*', line)
        desc_match = re.match(r'^([A-Za-z\s]+)', line)
        description = desc_match.group(1).strip() if desc_match else ''
        
        if not description or not numbers:
            return None
        
        nums = [self._clean_number(n) for n in numbers]
        
        tax = {
            'description': description,
            'wages': nums[0] if len(nums) > 0 else 0,
            'amount': nums[1] if len(nums) > 1 else 0,
            'wages_ytd': nums[2] if len(nums) > 2 else 0,
            'amount_ytd': nums[3] if len(nums) > 3 else 0
        }
        
        return tax
    
    def _parse_deduction_row(self, row: List[str]) -> Dict[str, Any]:
        """Parse deduction from table row."""
        if not row or len(row) < 2:
            return None
        
        # Typical structure: [Description, Scheduled, Amount, Amount YTD]
        deduction = {
            'description': row[0] if len(row) > 0 else '',
            'scheduled': self._clean_number(row[1]) if len(row) > 1 else 0,
            'amount': self._clean_number(row[2]) if len(row) > 2 else 0,
            'amount_ytd': self._clean_number(row[3]) if len(row) > 3 else 0
        }
        
        if deduction['description'] and deduction['amount']:
            return deduction
        
        return None
    
    def _parse_deduction_line(self, line: str) -> Dict[str, Any]:
        """Parse deduction from text line."""
        numbers = re.findall(r'[\d,]+\.?\d*', line)
        desc_match = re.match(r'^([A-Za-z\s]+)', line)
        description = desc_match.group(1).strip() if desc_match else ''
        
        if not description or not numbers:
            return None
        
        nums = [self._clean_number(n) for n in numbers]
        
        deduction = {
            'description': description,
            'scheduled': nums[0] if len(nums) > 0 else 0,
            'amount': nums[1] if len(nums) > 1 else 0,
            'amount_ytd': nums[2] if len(nums) > 2 else 0
        }
        
        return deduction
    
    def _clean_number(self, value: Any) -> float:
        """Convert string to number, handling various formats."""
        if isinstance(value, (int, float)):
            return float(value)
        
        if not value:
            return 0.0
        
        # Remove commas, dollar signs, spaces
        cleaned = str(value).replace(',', '').replace('$', '').replace(' ', '').strip()
        
        # Handle negative numbers in parentheses
        if cleaned.startswith('(') and cleaned.endswith(')'):
            cleaned = '-' + cleaned[1:-1]
        
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return 0.0
    
    def _create_four_tabs(self, employees: List[Dict[str, Any]]) -> Dict[str, pd.DataFrame]:
        """Create 4-tab structure from employee data."""
        
        # Tab 1: Employee Summary
        summary_data = []
        for emp in employees:
            summary = {
                'Employee ID': emp['info'].get('employee_id', ''),
                'Name': emp['info'].get('name', ''),
                'Department': emp['info'].get('department', ''),
                'Total Earnings': sum(e.get('amount', 0) for e in emp['earnings']),
                'Total Taxes': sum(t.get('amount', 0) for t in emp['taxes']),
                'Total Deductions': sum(d.get('amount', 0) for d in emp['deductions'])
            }
            summary['Net Pay'] = summary['Total Earnings'] - summary['Total Taxes'] - summary['Total Deductions']
            summary_data.append(summary)
        
        # Tab 2: Earnings
        earnings_data = []
        for emp in employees:
            emp_id = emp['info'].get('employee_id', '')
            name = emp['info'].get('name', '')
            for earning in emp['earnings']:
                earnings_data.append({
                    'Employee ID': emp_id,
                    'Name': name,
                    'Description': earning.get('description', ''),
                    'Rate': earning.get('rate', 0),
                    'Hours': earning.get('hours', 0),
                    'Amount': earning.get('amount', 0),
                    'Hours YTD': earning.get('hours_ytd', 0),
                    'Amount YTD': earning.get('amount_ytd', 0)
                })
        
        # Tab 3: Taxes
        taxes_data = []
        for emp in employees:
            emp_id = emp['info'].get('employee_id', '')
            name = emp['info'].get('name', '')
            for tax in emp['taxes']:
                taxes_data.append({
                    'Employee ID': emp_id,
                    'Name': name,
                    'Description': tax.get('description', ''),
                    'Wages': tax.get('wages', 0),
                    'Amount': tax.get('amount', 0),
                    'Wages YTD': tax.get('wages_ytd', 0),
                    'Amount YTD': tax.get('amount_ytd', 0)
                })
        
        # Tab 4: Deductions
        deductions_data = []
        for emp in employees:
            emp_id = emp['info'].get('employee_id', '')
            name = emp['info'].get('name', '')
            for deduction in emp['deductions']:
                deductions_data.append({
                    'Employee ID': emp_id,
                    'Name': name,
                    'Description': deduction.get('description', ''),
                    'Scheduled': deduction.get('scheduled', 0),
                    'Amount': deduction.get('amount', 0),
                    'Amount YTD': deduction.get('amount_ytd', 0)
                })
        
        return {
            'Employee Summary': pd.DataFrame(summary_data),
            'Earnings': pd.DataFrame(earnings_data),
            'Taxes': pd.DataFrame(taxes_data),
            'Deductions': pd.DataFrame(deductions_data)
        }
    
    def _write_excel(self, tabs: Dict[str, pd.DataFrame], pdf_path: str, output_dir: str) -> str:
        """Write tabs to Excel file."""
        # Create output directory if needed
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate output filename
        pdf_name = Path(pdf_path).stem
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = output_dir / f"{pdf_name}_parsed_{timestamp}.xlsx"
        
        # Write to Excel
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            for tab_name, df in tabs.items():
                df.to_excel(writer, sheet_name=tab_name, index=False)
        
        logger.info(f"Excel written to: {output_path}")
        return str(output_path)
    
    def _calculate_accuracy(self, tabs: Dict[str, pd.DataFrame], employees: List[Dict[str, Any]]) -> float:
        """Calculate parsing accuracy."""
        score = 0
        max_score = 100
        
        # Basic success (30 points)
        score += 30
        
        # Employee count (20 points)
        if len(employees) >= 2:
            score += 20
        elif len(employees) == 1:
            score += 10
        
        # Data in tabs (30 points total)
        if not tabs['Employee Summary'].empty:
            score += 10
        if not tabs['Earnings'].empty:
            score += 10
        if not tabs['Taxes'].empty:
            score += 5
        if not tabs['Deductions'].empty:
            score += 5
        
        # Data completeness (20 points)
        total_rows = sum(len(df) for df in tabs.values())
        if total_rows >= 20:
            score += 20
        elif total_rows >= 10:
            score += 10
        elif total_rows >= 5:
            score += 5
        
        return min(score, max_score)


def parse_dayforce_register(pdf_path: str, output_dir: str = '/data/parsed_registers') -> Dict[str, Any]:
    """
    Parse Dayforce register using pdfplumber-based parser.
    """
    parser = DayforceParserEnhanced()
    return parser.parse(pdf_path, output_dir)
