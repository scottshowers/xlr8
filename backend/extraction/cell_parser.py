"""
Pay Register Cell Parser
=========================
Parses concatenated cell data from Textract into structured records.

When Textract extracts pay registers, it often concatenates multiple
line items into single cells. This parser splits them back out.

Deploy to: backend/extraction/cell_parser.py
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class EmployeeRecord:
    """Parsed employee pay record"""
    name: str = ""
    employee_code: str = ""
    tax_profile: str = ""
    department: str = ""
    
    earnings: List[Dict[str, Any]] = field(default_factory=list)
    taxes: List[Dict[str, Any]] = field(default_factory=list)
    deductions: List[Dict[str, Any]] = field(default_factory=list)
    
    gross_pay: float = 0.0
    net_pay: float = 0.0
    total_taxes: float = 0.0
    total_deductions: float = 0.0
    
    check_number: str = ""
    pay_method: str = ""  # "Direct Deposit" or "Check"
    
    raw_data: Dict[str, str] = field(default_factory=dict)


class PayRegisterParser:
    """
    Parses Textract output from pay registers into structured employee records.
    
    Expected Textract format (5 columns):
    - Employee: "NAME Code: XXX Tax Profile: X - XX/XX/XX"
    - Earnings: "Regular 11.30 4.00 45.20 Overtime 16.95 2.00 33.90 GROSS 701.00"
    - Taxes: "Medicare 4.27 Social Security 18.24 Federal W/H 50.00"
    - Deductions: "401K % 8.57 Medical 25.00"
    - Net Pay: "Direct Deposit Net Check 263.08 NET PAY 263.08"
    """
    
    # Patterns for parsing
    EMPLOYEE_PATTERN = re.compile(
        r'^(?P<name>[A-Z][A-Z\s,\'-]+?)[\s]*'
        r'(?:Code:\s*(?P<code>\w+))?[\s]*'
        r'(?:Tax Profile:\s*(?P<tax_profile>[\d\s\-]+\s*[-/]\s*\w+/\w+/\w+))?',
        re.IGNORECASE
    )
    
    # Earning line: "Regular 11.30 4.00 45.20" or "Regular 36.77 8.00 294.16"
    # Format: Description Rate Hours Amount OR Description Hours Amount
    EARNING_PATTERN = re.compile(
        r'(?P<desc>[A-Za-z][A-Za-z\s\d]+?)\s+'
        r'(?P<num1>\d+\.?\d*)\s+'
        r'(?P<num2>\d+\.?\d*)\s+'
        r'(?P<num3>\d+\.?\d*)',
        re.IGNORECASE
    )
    
    # Simple earning: just description and amount (like GROSS 294.16)
    SIMPLE_AMOUNT_PATTERN = re.compile(
        r'(?P<desc>GROSS|NET PAY|TOTAL)\s+(?P<amount>\d+[,\d]*\.?\d*)',
        re.IGNORECASE
    )
    
    # Tax/Deduction line: "Medicare 4.27" or "Federal W/H (S) 50.00"
    TAX_DEDUCTION_PATTERN = re.compile(
        r'(?P<desc>[A-Za-z][A-Za-z\s\(\)/,\-]+?)\s+'
        r'(?P<amount>\d+[,\d]*\.?\d*)'
    )
    
    # Net pay patterns
    NET_PAY_PATTERN = re.compile(r'NET PAY\s+(?P<amount>\d+[,\d]*\.?\d*)', re.IGNORECASE)
    CHECK_PATTERN = re.compile(r'Check\s*#?\s*(?P<number>\d+)', re.IGNORECASE)
    
    def __init__(self):
        self.current_department = ""
    
    def parse_extraction_result(self, sections: Dict[str, Any]) -> List[EmployeeRecord]:
        """
        Parse Textract extraction result into employee records.
        
        Args:
            sections: The sections dict from extraction (has 'earnings' with data)
            
        Returns:
            List of parsed EmployeeRecord objects
        """
        employees = []
        
        # Find the main data section (usually classified as 'earnings' or 'pay_totals')
        data_section = None
        for section_name in ['earnings', 'pay_totals', 'unknown']:
            if section_name in sections:
                section = sections[section_name]
                if hasattr(section, 'data') and section.data:
                    data_section = section
                    break
                elif isinstance(section, dict) and section.get('data'):
                    data_section = section
                    break
        
        if not data_section:
            logger.warning("No data section found")
            return employees
        
        # Get the data rows
        if hasattr(data_section, 'data'):
            rows = data_section.data
        else:
            rows = data_section.get('data', [])
        
        logger.info(f"Parsing {len(rows)} rows from extraction")
        
        for row in rows:
            # Skip empty rows or subtotal rows
            if not row or not any(row):
                continue
            
            # Check if this is a department header
            first_cell = str(row[0]).strip() if row else ""
            if self._is_department_header(first_cell):
                self.current_department = first_cell
                continue
            
            # Check if this is a subtotal row
            if 'subtotal' in first_cell.lower():
                continue
            
            # Check if this looks like an employee row
            if self._is_employee_row(row):
                employee = self._parse_employee_row(row)
                if employee and employee.name:
                    employee.department = self.current_department
                    employees.append(employee)
        
        logger.info(f"Parsed {len(employees)} employee records")
        return employees
    
    def _is_department_header(self, text: str) -> bool:
        """Check if text is a department header like '2025 - RN No Benefit or Diff'"""
        if not text:
            return False
        # Department headers typically start with a number and have a dash
        if re.match(r'^\d+\s*[-–]\s*', text):
            return True
        return False
    
    def _is_employee_row(self, row: List[str]) -> bool:
        """Check if this row contains employee data"""
        if not row:
            return False
        
        first_cell = str(row[0]).strip()
        
        # Must have content
        if not first_cell:
            return False
        
        # Look for employee indicators
        if 'Code:' in first_cell or 'Tax Profile:' in first_cell:
            return True
        
        # Check if starts with a name pattern (LASTNAME, FIRSTNAME or similar)
        if re.match(r'^[A-Z][A-Z]+,?\s+[A-Z]', first_cell):
            return True
        
        return False
    
    def _parse_employee_row(self, row: List[str]) -> Optional[EmployeeRecord]:
        """Parse a single employee row into an EmployeeRecord"""
        if len(row) < 2:
            return None
        
        employee = EmployeeRecord()
        employee.raw_data = {f'col_{i}': str(cell) for i, cell in enumerate(row)}
        
        # Column 0: Employee info
        if len(row) > 0:
            self._parse_employee_info(str(row[0]), employee)
        
        # Column 1: Earnings
        if len(row) > 1:
            self._parse_earnings(str(row[1]), employee)
        
        # Column 2: Taxes
        if len(row) > 2:
            self._parse_taxes(str(row[2]), employee)
        
        # Column 3: Deductions
        if len(row) > 3:
            self._parse_deductions(str(row[3]), employee)
        
        # Column 4: Net Pay
        if len(row) > 4:
            self._parse_net_pay(str(row[4]), employee)
        
        # Calculate totals if not found
        if employee.total_taxes == 0 and employee.taxes:
            employee.total_taxes = sum(t.get('amount', 0) for t in employee.taxes)
        
        if employee.total_deductions == 0 and employee.deductions:
            employee.total_deductions = sum(d.get('amount', 0) for d in employee.deductions)
        
        return employee
    
    def _parse_employee_info(self, text: str, employee: EmployeeRecord):
        """Parse employee info cell"""
        if not text:
            return
        
        # Try structured pattern first
        match = self.EMPLOYEE_PATTERN.match(text)
        if match:
            employee.name = match.group('name').strip() if match.group('name') else ""
            employee.employee_code = match.group('code') or ""
            employee.tax_profile = match.group('tax_profile') or ""
        else:
            # Fallback: just take the first part as name
            parts = text.split('Code:')
            if parts:
                employee.name = parts[0].strip()
            if len(parts) > 1:
                code_part = parts[1].split('Tax Profile:')
                employee.employee_code = code_part[0].strip()
                if len(code_part) > 1:
                    employee.tax_profile = code_part[1].strip()
    
    def _parse_earnings(self, text: str, employee: EmployeeRecord):
        """Parse earnings cell - may contain multiple earning lines"""
        if not text:
            return
        
        # Find GROSS amount
        gross_match = re.search(r'GROSS\s+(?:[\d.]+\s+)?(\d+[,\d]*\.?\d*)', text, re.IGNORECASE)
        if gross_match:
            employee.gross_pay = self._parse_amount(gross_match.group(1))
        
        # Split on known earning types and parse
        # Common patterns: Regular, Overtime, Shift Diff, Holiday, Training, etc.
        earning_keywords = [
            'Regular', 'Overtime', 'Shift Diff', 'Holiday', 'Training', 
            'Orientation', 'Vacation', 'Sick', 'PTO', 'Bonus', 'Commission',
            'Maryland Sick', 'Retro'
        ]
        
        # Build regex to split on earning keywords
        pattern = '(' + '|'.join(re.escape(kw) for kw in earning_keywords) + r'[^A-Z]*?\d+\.?\d*\s+\d+\.?\d*\s+\d+[,\d]*\.?\d*)'
        
        matches = re.findall(pattern, text, re.IGNORECASE)
        
        for match in matches:
            earning = self._parse_single_earning(match)
            if earning:
                employee.earnings.append(earning)
        
        # If no matches with full pattern, try simpler extraction
        if not employee.earnings:
            # Try to find any "word number number number" patterns
            simple_matches = self.EARNING_PATTERN.findall(text)
            for m in simple_matches:
                if len(m) >= 4:
                    desc, num1, num2, num3 = m[0], m[1], m[2], m[3]
                    if desc.upper() not in ['GROSS', 'NET', 'TOTAL']:
                        employee.earnings.append({
                            'description': desc.strip(),
                            'rate': float(num1),
                            'hours': float(num2),
                            'amount': self._parse_amount(num3)
                        })
    
    def _parse_single_earning(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse a single earning entry like 'Regular 11.30 4.00 45.20'"""
        match = self.EARNING_PATTERN.search(text)
        if match:
            return {
                'description': match.group('desc').strip(),
                'rate': float(match.group('num1')),
                'hours': float(match.group('num2')),
                'amount': self._parse_amount(match.group('num3'))
            }
        return None
    
    def _parse_taxes(self, text: str, employee: EmployeeRecord):
        """Parse taxes cell"""
        if not text:
            return
        
        # Common tax types
        tax_keywords = [
            'Medicare', 'Social Security', 'Federal W/H', 'Fed W/H', 
            'State W/H', 'MD State', 'Local', 'County', 'FICA',
            'Res. Local', 'City'
        ]
        
        # Find all tax entries
        for keyword in tax_keywords:
            pattern = re.compile(
                re.escape(keyword) + r'[^0-9]*?(\d+[,\d]*\.?\d*)',
                re.IGNORECASE
            )
            match = pattern.search(text)
            if match:
                employee.taxes.append({
                    'description': keyword,
                    'amount': self._parse_amount(match.group(1))
                })
        
        # Also try generic pattern for anything we missed
        remaining = text
        for tax in employee.taxes:
            remaining = remaining.replace(tax['description'], '')
        
        # Look for additional patterns like "Worcester Count,MD - 5.47"
        location_pattern = re.compile(r'([A-Za-z]+\s+Count[y]?,?\s*\w*)\s*[-–]?\s*(?:Res\.?\s*Local)?\s*(\d+\.?\d*)', re.IGNORECASE)
        for match in location_pattern.finditer(text):
            desc = match.group(1).strip()
            amt = match.group(2)
            if not any(t['description'] == desc for t in employee.taxes):
                employee.taxes.append({
                    'description': desc,
                    'amount': self._parse_amount(amt)
                })
    
    def _parse_deductions(self, text: str, employee: EmployeeRecord):
        """Parse deductions cell"""
        if not text:
            return
        
        # Common deduction types
        deduction_patterns = [
            (r'401[Kk]\s*[%$]?\s*(\d+[,\d]*\.?\d*)', '401K'),
            (r'Medical\s*(\d+[,\d]*\.?\d*)', 'Medical'),
            (r'Dental\s*(\d+[,\d]*\.?\d*)', 'Dental'),
            (r'Vision\s*(\d+[,\d]*\.?\d*)', 'Vision'),
            (r'Life Insurance\s*(\d+[,\d]*\.?\d*)', 'Life Insurance'),
            (r'Health\s+\w*\s*(\d+[,\d]*\.?\d*)', 'Health'),
            (r'Physical/?New Hire\s*(\d+[,\d]*\.?\d*)', 'Physical/New Hire'),
            (r'Child Support\s*[%$]?\s*(?:Less\s*)?(\d+[,\d]*\.?\d*)', 'Child Support'),
            (r'Garnish\w*\s*(\d+[,\d]*\.?\d*)', 'Garnishment'),
            (r'Colonial\s+\w*\s*(\d+[,\d]*\.?\d*)', 'Colonial'),
        ]
        
        for pattern, desc in deduction_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                employee.deductions.append({
                    'description': desc,
                    'amount': self._parse_amount(match.group(1))
                })
    
    def _parse_net_pay(self, text: str, employee: EmployeeRecord):
        """Parse net pay cell"""
        if not text:
            return
        
        # Get net pay amount
        net_match = self.NET_PAY_PATTERN.search(text)
        if net_match:
            employee.net_pay = self._parse_amount(net_match.group('amount'))
        
        # Get check number if present
        check_match = self.CHECK_PATTERN.search(text)
        if check_match:
            employee.check_number = check_match.group('number')
        
        # Determine pay method
        if 'Direct Deposit' in text:
            employee.pay_method = 'Direct Deposit'
        elif 'Check' in text or 'Payroll Net Check' in text:
            employee.pay_method = 'Check'
    
    def _parse_amount(self, text: str) -> float:
        """Parse a currency amount, handling commas"""
        if not text:
            return 0.0
        try:
            # Remove commas and parse
            return float(text.replace(',', ''))
        except (ValueError, TypeError):
            return 0.0
    
    def to_flat_records(self, employees: List[EmployeeRecord]) -> List[Dict[str, Any]]:
        """
        Convert employee records to flat dictionaries for export/display.
        """
        records = []
        
        for emp in employees:
            record = {
                'employee_name': emp.name,
                'employee_code': emp.employee_code,
                'tax_profile': emp.tax_profile,
                'department': emp.department,
                'gross_pay': emp.gross_pay,
                'net_pay': emp.net_pay,
                'total_taxes': emp.total_taxes,
                'total_deductions': emp.total_deductions,
                'check_number': emp.check_number,
                'pay_method': emp.pay_method,
                'earnings_count': len(emp.earnings),
                'taxes_count': len(emp.taxes),
                'deductions_count': len(emp.deductions),
            }
            
            # Add individual earnings
            for i, earning in enumerate(emp.earnings[:10]):  # Limit to 10
                record[f'earning_{i+1}_desc'] = earning.get('description', '')
                record[f'earning_{i+1}_rate'] = earning.get('rate', 0)
                record[f'earning_{i+1}_hours'] = earning.get('hours', 0)
                record[f'earning_{i+1}_amount'] = earning.get('amount', 0)
            
            # Add individual taxes
            for i, tax in enumerate(emp.taxes[:10]):
                record[f'tax_{i+1}_desc'] = tax.get('description', '')
                record[f'tax_{i+1}_amount'] = tax.get('amount', 0)
            
            # Add individual deductions
            for i, ded in enumerate(emp.deductions[:10]):
                record[f'deduction_{i+1}_desc'] = ded.get('description', '')
                record[f'deduction_{i+1}_amount'] = ded.get('amount', 0)
            
            records.append(record)
        
        return records


def parse_pay_register(sections: Dict[str, Any]) -> Tuple[List[EmployeeRecord], List[Dict[str, Any]]]:
    """
    Main entry point for parsing pay register data.
    
    Args:
        sections: The sections dict from Textract extraction
        
    Returns:
        Tuple of (employee records, flat records for export)
    """
    parser = PayRegisterParser()
    employees = parser.parse_extraction_result(sections)
    flat_records = parser.to_flat_records(employees)
    
    return employees, flat_records
