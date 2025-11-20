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
            
            # Extract table
            with pdfplumber.open(pdf_path) as pdf:
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
                'deductions': deductions
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
                'deductions_found': len(deductions)
            }
            
        except Exception as e:
            self.logger.error(f"V2 parsing failed: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    def _parse_employee_column(self, text: str) -> Dict:
        """Parse employee info from column 0."""
        if not text:
            return None
        
        # Extract name (first line)
        lines = text.split('\n')
        name = lines[0].strip() if lines else ""
        
        # Validate name format
        if not re.match(r'^[A-Z][a-z]+\s+[A-Z][a-z]+$', name):
            return None
        
        # Extract employee ID
        emp_id_match = re.search(r'Emp\s*#:\s*(\d{4,6})', text)
        emp_id = emp_id_match.group(1) if emp_id_match else ""
        
        # Extract department
        dept_match = re.search(r'Dept:\s*(.+)', text)
        dept = dept_match.group(1).strip() if dept_match else ""
        
        return {
            'employee_id': emp_id,
            'employee_name': name,
            'department': dept
        }
    
    def _parse_earnings_column(self, text: str, employee: Dict) -> List[Dict]:
        """Parse earnings from column 1."""
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
            
            # Pattern: "Description Rate Hours Amount" or "Description Hours Amount"
            # Examples:
            # "Regular Hourly $18.1900 55.28 $1,005.60 748.73 $13,538.38"
            # "Nightshift 10.68 $198.39"
            # "Holiday Bonus $50.00"
            
            # Try full pattern first (with rate)
            match = re.search(r'^([A-Z][A-Za-z\s\-]{2,30}?)\s+\$?([\d,]+\.\d{2,4})\s+([\d,]+\.\d{2})\s+\$?([\d,]+\.\d{2})', line)
            if match:
                desc = match.group(1).strip()
                rate = self._safe_float(match.group(2))
                hours = self._safe_float(match.group(3))
                amount = self._safe_float(match.group(4))
            else:
                # Try pattern without rate
                match = re.search(r'^([A-Z][A-Za-z\s\-]{2,30}?)\s+([\d,]+\.\d{2})\s+\$?([\d,]+\.\d{2})', line)
                if match:
                    desc = match.group(1).strip()
                    hours = self._safe_float(match.group(2))
                    amount = self._safe_float(match.group(3))
                    rate = 0
                else:
                    # Try simple: "Description $Amount"
                    match = re.search(r'^([A-Z][A-Za-z\s\-]{2,30}?)\s+\$?([\d,]+\.\d{2})$', line)
                    if match:
                        desc = match.group(1).strip()
                        amount = self._safe_float(match.group(2))
                        hours = 0
                        rate = 0
                    else:
                        continue
            
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
                'current_ytd': amount
            })
        
        return earnings
    
    def _parse_taxes_column(self, text: str, employee: Dict) -> List[Dict]:
        """Parse taxes from column 7."""
        taxes = []
        
        # Exclusion keywords
        exclusions = ['memo total', 'emp total', 'er total']
        
        for line in text.split('\n'):
            line = line.strip()
            
            # Skip empty, short, dashes, or excluded
            if len(line) < 5 or line.startswith('---') or any(ex in line.lower() for ex in exclusions):
                continue
            
            # Pattern: Handle multiple amounts in different formats
            # Format 1: "Fed W/H $1,005.60 $14,559.63 $62.46" (3 amounts)
            # Format 2: "FICA EE $1,005.60 $62.35 $14,559.63 $902.70" (4 amounts)
            # Format 3: "Fed UT ER $7,000.00 $42.00" (2 amounts)
            # Format 4: "ID DRT $7,000.00" (1 amount)
            
            # Extract description (everything before first dollar sign or number)
            desc_match = re.match(r'^([A-Z][A-Za-z\s/\-]{1,20}?)\s+\$', line)
            if not desc_match:
                continue
            
            desc = desc_match.group(1).strip()
            
            # Extract all amounts from the line
            amounts = [float(a.replace(',', '')) for a in re.findall(r'\$?([\d,]+\.\d{2})', line)]
            
            if not amounts:
                continue
            
            # Logic: For tax lines, typically:
            # - 1 amount: wages (no current tax shown)
            # - 2 amounts: wages, current_tax
            # - 3 amounts: wages, ytd_wages, current_tax  
            # - 4 amounts: wages, current_tax, ytd_wages, ytd_tax
            
            if len(amounts) == 1:
                wages = amounts[0]
                amount = 0
            elif len(amounts) == 2:
                wages = amounts[0]
                amount = amounts[1]
            elif len(amounts) == 3:
                wages = amounts[0]
                amount = amounts[2]  # 3rd amount is current period tax
            else:  # 4+ amounts
                wages = amounts[0]
                amount = amounts[1]  # 2nd amount is current period tax
            
            # Validate
            if amount < 0 or amount > 10000:
                continue
            
            taxes.append({
                'employee_id': employee['employee_id'],
                'employee_name': employee['employee_name'],
                'description': desc,
                'wages_base': wages,
                'amount': amount,
                'wages_ytd': wages,
                'amount_ytd': amount
            })
        
        return taxes
    
    def _parse_deductions_column(self, text: str, employee: Dict) -> List[Dict]:
        """Parse deductions from column 13."""
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
            
            # Pattern: "Description Amount" with optional percentage
            # Examples:
            # "Uniform Purchase $4.85"
            # "Medical Pre Tax $403.81 $403.81 $6,057.15"
            # "401k-PR 5.00% $261.23 $1,636.91"
            match = re.search(r'^([A-Z][A-Za-z\s\-()]{2,35}?)(?:\s+[\d.]+%)?\s+\$?([\d,]+\.\d{2})', line)
            
            if match:
                desc = match.group(1).strip()
                amount = self._safe_float(match.group(2))
                
                # Validate
                if amount < 0.01 or amount > 5000:
                    continue
                
                deductions.append({
                    'employee_id': employee['employee_id'],
                    'employee_name': employee['employee_name'],
                    'description': desc,
                    'scheduled': 0,
                    'amount': amount,
                    'amount_ytd': amount
                })
        
        return deductions
    
    def _safe_float(self, value: str) -> float:
        """Safely convert to float."""
        try:
            return float(str(value).replace(',', '').replace('$', '').replace('%', ''))
        except:
            return 0.0
    
    def _create_excel_tabs(self, structured: Dict) -> Dict[str, pd.DataFrame]:
        """Create 4 Excel tabs."""
        summary_data = []
        for emp in structured['employees']:
            emp_id = emp['employee_id']
            emp_earnings = [e for e in structured['earnings'] if e['employee_id'] == emp_id]
            emp_taxes = [t for t in structured['taxes'] if t['employee_id'] == emp_id]
            emp_deductions = [d for d in structured['deductions'] if d['employee_id'] == emp_id]
            
            summary_data.append({
                'Employee ID': emp_id,
                'Name': emp['employee_name'],
                'Department': emp['department'],
                'Total Earnings': sum(e['amount'] for e in emp_earnings),
                'Total Taxes': sum(t['amount'] for t in emp_taxes),
                'Total Deductions': sum(d['amount'] for d in emp_deductions),
                'Net Pay': sum(e['amount'] for e in emp_earnings) - sum(t['amount'] for t in emp_taxes) - sum(d['amount'] for d in emp_deductions)
            })
        
        return {
            'Employee Summary': pd.DataFrame(summary_data),
            'Earnings': pd.DataFrame([{
                'Employee ID': e['employee_id'],
                'Name': e['employee_name'],
                'Description': e['description'],
                'Hours': e['hours'],
                'Rate': e['rate'],
                'Amount': e['amount'],
                'Current YTD': e['current_ytd']
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
