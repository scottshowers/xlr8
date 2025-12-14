"""
Intelligent Parser Orchestrator V2 - TABLE-BASED (CORRECT APPROACH)

Dayforce PDFs use a TABLE layout:
- Row per employee
- Columns: Employee Info | Earnings | Taxes | Deductions
"""

import logging
import re
from typing import Dict, List, Any
from pathlib import Path
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False


class IntelligentParserOrchestratorV2:
    """V2 parser using TABLE extraction."""
    
    def __init__(self, custom_parsers_dir: str = None):
        self.logger = logging.getLogger(__name__)
        self.custom_parsers_dir = custom_parsers_dir
    
    def parse(self, pdf_path: str, output_dir: str = '/data/parsed_registers', force_v2: bool = False) -> Dict[str, Any]:
        """Parse PDF using table extraction."""
        try:
            if not PDFPLUMBER_AVAILABLE:
                raise Exception("pdfplumber not available")
            
            # Extract table AND metadata
            with pdfplumber.open(pdf_path) as pdf:
                # Get full text for metadata
                full_text = pdf.pages[0].extract_text() or ""
                
                # Extract metadata
                metadata = self._extract_metadata(full_text)
                
                # Get table
                tables = pdf.pages[0].extract_tables()
                
                if not tables:
                    raise Exception("No tables found in PDF")
                
                table = tables[0]
            
            # Parse table rows (skip headers)
            employees = []
            earnings = []
            taxes = []
            deductions = []
            
            for row in table[3:]:  # Skip header rows (0, 1, 2)
                if not row or not row[0]:
                    continue
                
                # Parse employee info (column 0)
                emp = self._parse_employee_column(row[0])
                if not emp:
                    continue
                
                employees.append(emp)
                
                # Parse earnings (column 1)
                if row[1]:
                    emp_earnings = self._parse_earnings_column(row[1], emp)
                    earnings.extend(emp_earnings)
                
                # Parse taxes (column 7)
                if len(row) > 7 and row[7]:
                    emp_taxes = self._parse_taxes_column(row[7], emp)
                    taxes.extend(emp_taxes)
                
                # Parse deductions (column 12)
                if len(row) > 12 and row[12]:
                    emp_deductions = self._parse_deductions_column(row[12], emp)
                    deductions.extend(emp_deductions)
            
            structured_data = {
                'employees': employees,
                'earnings': earnings,
                'taxes': taxes,
                'deductions': deductions,
                'metadata': metadata  # Add metadata
            }
            
            tabs = self._create_excel_tabs(structured_data)
            excel_path = self._write_excel(tabs, pdf_path, output_dir)
            accuracy = self._calculate_accuracy(structured_data, tabs)
            
            return {
                'success': True,
                'excel_path': excel_path,
                'accuracy': accuracy,
                'method': 'V2-Table-Based',
                'employees_found': len(employees),
                'earnings_found': len(earnings),
                'taxes_found': len(taxes),
                'deductions_found': len(deductions),
                'metadata': metadata  # Include metadata in result
            }
            
        except Exception as e:
            self.logger.error(f"V2 parsing failed: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    def _extract_metadata(self, full_text: str) -> Dict[str, str]:
        """
        Extract metadata from PDF: company, pay date, pay period.
        
        Dayforce PDFs typically have:
        - "Multiple Legal Entities" or company name at top
        - "Pay Date: 8/8/2025" at bottom
        - "Pay Period: 7/21/2025 - 8/3/2025" at bottom
        """
        metadata = {
            'company': '',
            'pay_date': '',
            'pay_period_start': '',
            'pay_period_end': ''
        }
        
        # Extract company/legal entity (usually first few lines)
        lines = full_text.split('\n')
        for i, line in enumerate(lines[:10]):  # Check first 10 lines
            line = line.strip()
            if 'legal entit' in line.lower():
                # Next line might be company name, or it might say "Multiple Legal Entities"
                if 'multiple' in line.lower():
                    metadata['company'] = 'Multiple Legal Entities'
                elif i + 1 < len(lines):
                    # Try next line
                    next_line = lines[i + 1].strip()
                    if next_line and len(next_line) > 3 and not next_line.startswith('Employee'):
                        metadata['company'] = next_line
                break
            # Sometimes company name is just at the very top
            elif i == 0 and len(line) > 3 and not line.startswith('Employee'):
                metadata['company'] = line
        
        # If no company found, use default
        if not metadata['company']:
            metadata['company'] = 'Unknown'
        
        # Extract pay date - look for "Pay Date: MM/DD/YYYY"
        pay_date_match = re.search(r'Pay\s+Date:\s*(\d{1,2}/\d{1,2}/\d{4})', full_text, re.IGNORECASE)
        if pay_date_match:
            metadata['pay_date'] = pay_date_match.group(1)
        
        # Extract pay period - look for "Pay Period: MM/DD/YYYY - MM/DD/YYYY"
        pay_period_match = re.search(
            r'Pay\s+Period:\s*(\d{1,2}/\d{1,2}/\d{4})\s*-\s*(\d{1,2}/\d{1,2}/\d{4})',
            full_text,
            re.IGNORECASE
        )
        if pay_period_match:
            metadata['pay_period_start'] = pay_period_match.group(1)
            metadata['pay_period_end'] = pay_period_match.group(2)
        
        self.logger.info(f"Extracted metadata: {metadata}")
        return metadata
    
    def _parse_employee_column(self, text: str) -> Dict:
        """Parse employee info from column 0 - capture ALL fields."""
        if not text:
            return None
        
        # Extract name (first line)
        lines = text.split('\n')
        name = lines[0].strip() if lines else ""
        
        # Validate name format
        if not re.match(r'^[A-Z][a-z]+\s+[A-Z][a-z]+$', name):
            return None
        
        # Extract all fields from Employee Info column
        emp_data = {
            'employee_id': '',
            'employee_name': name,
            'department': '',
            'position': '',
            'status': '',
            'pay_group': '',
            'location': '',
            'hire_date': ''
        }
        
        # Parse each line for field:value patterns
        for line in lines[1:]:  # Skip first line (name)
            line = line.strip()
            if not line:
                continue
            
            # Employee ID
            if 'emp #' in line.lower() or 'emp#' in line.lower():
                match = re.search(r'Emp\s*#?\s*:?\s*(\d{4,6})', line, re.IGNORECASE)
                if match:
                    emp_data['employee_id'] = match.group(1)
            
            # Department
            elif 'dept' in line.lower():
                match = re.search(r'Dept\s*:?\s*(.+)', line, re.IGNORECASE)
                if match:
                    emp_data['department'] = match.group(1).strip()
            
            # Position/Job Title
            elif 'position' in line.lower() or 'job' in line.lower() or 'title' in line.lower():
                match = re.search(r'(?:Position|Job|Title)\s*:?\s*(.+)', line, re.IGNORECASE)
                if match:
                    emp_data['position'] = match.group(1).strip()
            
            # Status (FT/PT/Temp)
            elif 'status' in line.lower():
                match = re.search(r'Status\s*:?\s*(.+)', line, re.IGNORECASE)
                if match:
                    emp_data['status'] = match.group(1).strip()
            
            # Pay Group
            elif 'pay group' in line.lower() or 'paygroup' in line.lower():
                match = re.search(r'Pay\s*Group\s*:?\s*(.+)', line, re.IGNORECASE)
                if match:
                    emp_data['pay_group'] = match.group(1).strip()
            
            # Location
            elif 'location' in line.lower() or 'site' in line.lower():
                match = re.search(r'(?:Location|Site)\s*:?\s*(.+)', line, re.IGNORECASE)
                if match:
                    emp_data['location'] = match.group(1).strip()
            
            # Hire Date
            elif 'hire' in line.lower() or 'start' in line.lower():
                match = re.search(r'(?:Hire|Start)\s*(?:Date)?\s*:?\s*(\d{1,2}/\d{1,2}/\d{2,4})', line, re.IGNORECASE)
                if match:
                    emp_data['hire_date'] = match.group(1)
        
        return emp_data
    
    def _parse_earnings_column(self, text: str, employee: Dict) -> List[Dict]:
        """Parse earnings from column 1 - including YTD Hours."""
        earnings = []
        
        # Exclusion keywords (not earnings)
        exclusions = ['phone', 'reimbursement', 'manager fuel', 'company paid', 
                      'memo total', 'hours', 'balance', 'accrued']
        
        for line in text.split('\n'):
            line = line.strip()
            
            # Skip empty, short, or excluded lines
            if len(line) < 5 or any(ex in line.lower() for ex in exclusions):
                continue
            
            # Skip lines with just dashes or totals
            if line.startswith('---') or 'total' in line.lower():
                continue
            
            # Pattern: Extract description and all numbers
            # Examples:
            # "Regular Hourly $18.1900 55.28 $1,005.60 748.73 $13,538.38"
            # Format: Description Rate Hours Amount HoursYTD AmountYTD
            # "Nightshift 10.68 $198.39"
            # Format: Description Hours Amount
            # "Holiday Bonus $50.00"
            # Format: Description Amount
            
            # Extract description (everything before first number/dollar)
            desc_match = re.match(r'^([A-Z][A-Za-z\s\-]{2,30}?)\s+(?:\$|[\d])', line)
            if not desc_match:
                continue
            
            desc = desc_match.group(1).strip()
            
            # Extract all amounts/numbers from the line
            numbers = re.findall(r'[\d,]+\.\d{2,4}', line)
            
            if not numbers:
                continue
            
            # Convert to floats
            values = [self._safe_float(n) for n in numbers]
            
            # Determine what each value represents based on count and magnitude
            rate = 0
            hours = 0
            amount = 0
            hours_ytd = 0
            amount_ytd = 0
            
            # Logic based on number of values and their magnitudes
            if len(values) == 1:
                # "Holiday Bonus $50.00" - just amount
                amount = values[0]
                amount_ytd = values[0]
            elif len(values) == 2:
                # "Nightshift 10.68 $198.39" - hours, amount
                hours = values[0]
                amount = values[1]
                hours_ytd = hours
                amount_ytd = amount
            elif len(values) == 3:
                # "Regular Hourly $18.19 55.28 $1,005.60" - rate, hours, amount
                # OR could be: hours, amount, amount_ytd
                if values[0] > 100:  # Likely rate (e.g., $18.1900)
                    rate = values[0]
                    hours = values[1]
                    amount = values[2]
                    hours_ytd = hours
                    amount_ytd = amount
                else:
                    # hours, amount, amount_ytd
                    hours = values[0]
                    amount = values[1]
                    amount_ytd = values[2]
                    hours_ytd = hours
            elif len(values) == 4:
                # Could be: rate, hours, amount, amount_ytd
                # OR: hours, amount, hours_ytd, amount_ytd
                if values[0] > 100:  # Likely rate
                    rate = values[0]
                    hours = values[1]
                    amount = values[2]
                    amount_ytd = values[3]
                    hours_ytd = hours
                else:
                    hours = values[0]
                    amount = values[1]
                    hours_ytd = values[2]
                    amount_ytd = values[3]
            elif len(values) >= 5:
                # "Regular Hourly $18.1900 55.28 $1,005.60 748.73 $13,538.38"
                # Format: Rate Hours Amount HoursYTD AmountYTD
                rate = values[0]
                hours = values[1]
                amount = values[2]
                hours_ytd = values[3]
                amount_ytd = values[4]
            
            # Validate
            if amount < 1 or amount > 50000:
                continue
            
            earnings.append({
                'employee_id': employee['employee_id'],
                'employee_name': employee['employee_name'],
                'description': desc,
                'hours': hours,
                'rate': rate,
                'amount': amount,
                'hours_ytd': hours_ytd,
                'amount_ytd': amount_ytd
            })
        
        return earnings
        
        return earnings
    
    def _parse_taxes_column(self, text: str, employee: Dict) -> List[Dict]:
        """Parse taxes from column 7 - correctly extract current and YTD values."""
        taxes = []
        
        # Exclusion keywords
        exclusions = ['memo total', 'emp total', 'er total']
        
        for line in text.split('\n'):
            line = line.strip()
            
            # Skip empty, short, dashes, or excluded
            if len(line) < 5 or line.startswith('---') or any(ex in line.lower() for ex in exclusions):
                continue
            
            # Pattern: Handle multiple amounts in different formats
            # Format 1: "Fed W/H $1,005.60 $14,559.63 $62.46" (3 amounts: wages, wages_ytd, amount)
            # Format 2: "FICA EE $1,005.60 $62.35 $14,559.63 $902.70" (4 amounts: wages, amount, wages_ytd, amount_ytd)
            # Format 3: "Fed UT ER $7,000.00 $42.00" (2 amounts: wages, amount)
            # Format 4: "ID DRT $7,000.00" (1 amount: wages only)
            
            # Extract description (everything before first dollar sign or number)
            desc_match = re.match(r'^([A-Z][A-Za-z\s/\-]{1,20}?)\s+\$', line)
            if not desc_match:
                continue
            
            desc = desc_match.group(1).strip()
            
            # Extract all amounts from the line
            amounts = [float(a.replace(',', '')) for a in re.findall(r'\$?([\d,]+\.\d{2})', line)]
            
            if not amounts:
                continue
            
            # Logic: Determine current vs YTD based on count and values
            wages_base = 0
            amount = 0
            wages_ytd = 0
            amount_ytd = 0
            
            if len(amounts) == 1:
                # Only wages shown, no tax
                wages_base = amounts[0]
                wages_ytd = amounts[0]
                amount = 0
                amount_ytd = 0
            elif len(amounts) == 2:
                # wages, amount (current period)
                wages_base = amounts[0]
                amount = amounts[1]
                wages_ytd = amounts[0]  # Assume same as current if only 2 values
                amount_ytd = amounts[1]
            elif len(amounts) == 3:
                # Three patterns possible:
                # A) wages, wages_ytd, amount (most common)
                # B) wages, amount, amount_ytd
                # Heuristic: if 2nd value >> 1st value, it's wages_ytd
                if amounts[1] > amounts[0] * 3:
                    # Pattern A: wages, wages_ytd, amount
                    wages_base = amounts[0]
                    wages_ytd = amounts[1]
                    amount = amounts[2]
                    amount_ytd = amounts[2]  # Assume same if only 3 values
                else:
                    # Pattern B: wages, amount, amount_ytd
                    wages_base = amounts[0]
                    amount = amounts[1]
                    amount_ytd = amounts[2]
                    wages_ytd = amounts[0]
            elif len(amounts) >= 4:
                # Full format: wages, amount, wages_ytd, amount_ytd
                wages_base = amounts[0]
                amount = amounts[1]
                wages_ytd = amounts[2]
                amount_ytd = amounts[3]
            
            # Validate
            if amount < 0 or amount > 10000:
                continue
            
            taxes.append({
                'employee_id': employee['employee_id'],
                'employee_name': employee['employee_name'],
                'description': desc,
                'wages_base': wages_base,
                'amount': amount,
                'wages_ytd': wages_ytd,
                'amount_ytd': amount_ytd
            })
        
        return taxes
    
    def _parse_deductions_column(self, text: str, employee: Dict) -> List[Dict]:
        """Parse deductions from column 13 - correctly extract scheduled, current, and YTD."""
        deductions = []
        
        # Exclusion keywords
        exclusions = ['memo total', 'pre total', 'post total', 'workers comp', 
                      'italicized amounts', 'balance', 'accrued']
        
        for line in text.split('\n'):
            line = line.strip()
            
            # Skip empty, short, dashes, or excluded
            if len(line) < 5 or line.startswith('---') or any(ex in line.lower() for ex in exclusions):
                continue
            
            # Skip year markers like "(2023)"
            if re.match(r'^\(\d{4}\)$', line):
                continue
            
            # Pattern: "Description [Percentage] Amount1 [Amount2] [Amount3]"
            # Examples:
            # "Uniform Purchase $4.85" - 1 amount (current = YTD)
            # "401k-PR 5.00% $261.23 $1,636.91" - 2 amounts (current, YTD)
            # "Medical Pre Tax $403.81 $403.81 $6,057.15" - 3 amounts (scheduled, current, YTD)
            
            # Extract description (everything before first dollar sign or percentage)
            desc_match = re.match(r'^([A-Z][A-Za-z\s\-()]{2,35}?)(?:\s+[\d.]+%)?\s+\$', line)
            if not desc_match:
                continue
            
            desc = desc_match.group(1).strip()
            
            # Extract all amounts from the line
            amounts = [float(a.replace(',', '')) for a in re.findall(r'\$?([\d,]+\.\d{2})', line)]
            
            if not amounts:
                continue
            
            # Determine scheduled, current, and YTD based on count
            scheduled = 0
            amount = 0
            amount_ytd = 0
            
            if len(amounts) == 1:
                # "Uniform Purchase $4.85" - single amount (current = YTD)
                amount = amounts[0]
                amount_ytd = amounts[0]
                scheduled = 0
            elif len(amounts) == 2:
                # "401k-PR 5.00% $261.23 $1,636.91" - current, YTD
                amount = amounts[0]
                amount_ytd = amounts[1]
                scheduled = 0
            elif len(amounts) >= 3:
                # "Medical Pre Tax $403.81 $403.81 $6,057.15" - scheduled, current, YTD
                scheduled = amounts[0]
                amount = amounts[1]
                amount_ytd = amounts[2]
            
            # Validate
            if amount < 0.01 or amount > 5000:
                continue
            
            deductions.append({
                'employee_id': employee['employee_id'],
                'employee_name': employee['employee_name'],
                'description': desc,
                'scheduled': scheduled,
                'amount': amount,
                'amount_ytd': amount_ytd
            })
        
        return deductions
    
    def _safe_float(self, value: str) -> float:
        """Safely convert to float."""
        try:
            return float(str(value).replace(',', '').replace('$', '').replace('%', ''))
        except:
            return 0.0
    
    def _create_excel_tabs(self, structured: Dict) -> Dict[str, pd.DataFrame]:
        """Create 5 Excel tabs (including metadata and all employee fields)."""
        metadata = structured.get('metadata', {})
        
        summary_data = []
        for emp in structured['employees']:
            emp_id = emp['employee_id']
            emp_earnings = [e for e in structured['earnings'] if e['employee_id'] == emp_id]
            emp_taxes = [t for t in structured['taxes'] if t['employee_id'] == emp_id]
            emp_deductions = [d for d in structured['deductions'] if d['employee_id'] == emp_id]
            
            summary_data.append({
                'Company': metadata.get('company', ''),
                'Pay Date': metadata.get('pay_date', ''),
                'Pay Period Start': metadata.get('pay_period_start', ''),
                'Pay Period End': metadata.get('pay_period_end', ''),
                'Employee ID': emp_id,
                'Name': emp['employee_name'],
                'Department': emp.get('department', ''),
                'Position': emp.get('position', ''),
                'Status': emp.get('status', ''),
                'Pay Group': emp.get('pay_group', ''),
                'Location': emp.get('location', ''),
                'Hire Date': emp.get('hire_date', ''),
                'Total Earnings': sum(e['amount'] for e in emp_earnings),
                'Total Taxes': sum(t['amount'] for t in emp_taxes),
                'Total Deductions': sum(d['amount'] for d in emp_deductions),
                'Net Pay': sum(e['amount'] for e in emp_earnings) - sum(t['amount'] for t in emp_taxes) - sum(d['amount'] for d in emp_deductions)
            })
        
        # Create Metadata tab
        metadata_df = pd.DataFrame([{
            'Field': 'Company / Legal Entity',
            'Value': metadata.get('company', '')
        }, {
            'Field': 'Pay Date',
            'Value': metadata.get('pay_date', '')
        }, {
            'Field': 'Pay Period Start',
            'Value': metadata.get('pay_period_start', '')
        }, {
            'Field': 'Pay Period End',
            'Value': metadata.get('pay_period_end', '')
        }])
        
        return {
            'Metadata': metadata_df,
            'Employee Summary': pd.DataFrame(summary_data),
            'Earnings': pd.DataFrame([{
                'Employee ID': e['employee_id'],
                'Name': e['employee_name'],
                'Description': e['description'],
                'Hours': e['hours'],
                'Rate': e['rate'],
                'Amount': e['amount'],
                'Hours YTD': e['hours_ytd'],
                'Amount YTD': e['amount_ytd']
            } for e in structured['earnings']]),
            'Taxes': pd.DataFrame([{
                'Employee ID': t['employee_id'],
                'Name': t['employee_name'],
                'Description': t['description'],
                'Wages Base': t['wages_base'],
                'Amount': t['amount'],
                'Wages YTD': t['wages_ytd'],
                'Amount YTD': t['amount_ytd']
            } for t in structured['taxes']]),
            'Deductions': pd.DataFrame([{
                'Employee ID': d['employee_id'],
                'Name': d['employee_name'],
                'Description': d['description'],
                'Scheduled': d['scheduled'],
                'Amount': d['amount'],
                'Amount YTD': d['amount_ytd']
            } for d in structured['deductions']])
        }
    
    def _write_excel(self, tabs: Dict[str, pd.DataFrame], pdf_path: str, output_dir: str) -> str:
        """Write Excel file."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = output_dir / f"{Path(pdf_path).stem}_parsed_v2_{timestamp}.xlsx"
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            for tab_name, df in tabs.items():
                df.to_excel(writer, sheet_name=tab_name, index=False)
        
        return str(output_path)
    
    def _calculate_accuracy(self, structured: Dict, tabs: Dict[str, pd.DataFrame]) -> float:
        """Calculate accuracy based on data completeness."""
        score = 0
        
        # Employees with valid names (30 points)
        employees = structured['employees']
        if employees:
            valid_names = sum(1 for e in employees if len(e['employee_name'].split()) == 2)
            if valid_names == len(employees):
                score += 30
        
        # Earnings quantity (25 points)
        if employees:
            avg_earnings = len(structured['earnings']) / len(employees)
            if avg_earnings >= 5:
                score += 25
            elif avg_earnings >= 3:
                score += 15
        
        # Taxes quantity (25 points)
        if employees:
            avg_taxes = len(structured['taxes']) / len(employees)
            if avg_taxes >= 8:
                score += 25
            elif avg_taxes >= 5:
                score += 15
        
        # Deductions quantity (20 points)
        if employees:
            avg_deductions = len(structured['deductions']) / len(employees)
            if avg_deductions >= 2:
                score += 20
            elif avg_deductions >= 1:
                score += 10
        
        return min(score, 100.0)
