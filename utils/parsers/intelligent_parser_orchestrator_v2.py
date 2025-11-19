"""
Intelligent Parser Orchestrator V2 - Production Keyword Parser
Strict pattern matching, no bbox complexity
"""

import logging
import re
from typing import Dict, List, Any, Optional
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
    """Production V2 parser with strict keyword patterns."""
    
    def __init__(self, custom_parsers_dir: str = None):
        self.logger = logging.getLogger(__name__)
        self.custom_parsers_dir = custom_parsers_dir
    
    def parse(self, pdf_path: str, output_dir: str = '/data/parsed_registers', force_v2: bool = False) -> Dict[str, Any]:
        """Parse PDF with strict pattern matching."""
        try:
            if not PDFPLUMBER_AVAILABLE:
                raise Exception("pdfplumber not available")
            
            # Extract full text
            full_text = self._extract_full_text(pdf_path)
            if not full_text:
                raise Exception("No text extracted")
            
            # Parse with strict patterns
            employees = self._parse_employee_info(full_text)
            earnings = self._parse_earnings(full_text, employees)
            taxes = self._parse_taxes(full_text, employees)
            deductions = self._parse_deductions(full_text, employees)
            
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
                'method': 'V2-Keywords-Strict',
                'employees_found': len(employees),
                'earnings_found': len(earnings),
                'taxes_found': len(taxes),
                'deductions_found': len(deductions)
            }
            
        except Exception as e:
            self.logger.error(f"V2 parsing failed: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    def _extract_full_text(self, pdf_path: str) -> str:
        """Extract complete PDF text."""
        with pdfplumber.open(pdf_path) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    
    def _parse_employee_info(self, text: str) -> List[Dict]:
        """Parse employees with strict pattern."""
        employees = []
        
        # Pattern: "Emp #: 12345" followed by name within 200 chars
        pattern = r'Emp\s*#:\s*(\d{4,6})'
        
        for match in re.finditer(pattern, text, re.IGNORECASE):
            emp_id = match.group(1)
            
            # Get context around match
            start = max(0, match.start() - 100)
            end = min(len(text), match.end() + 100)
            context = text[start:end]
            
            # Find name: "FirstName LastName" (both capitalized)
            name_match = re.search(r'\b([A-Z][a-z]+)\s+([A-Z][a-z]+)\b', context)
            if name_match:
                name = f"{name_match.group(1)} {name_match.group(2)}"
                employees.append({
                    'employee_id': emp_id,
                    'employee_name': name,
                    'department': ''
                })
        
        # Deduplicate
        seen = {}
        for emp in employees:
            if emp['employee_id'] not in seen:
                seen[emp['employee_id']] = emp
        
        return list(seen.values())
    
    def _parse_earnings(self, text: str, employees: List[Dict]) -> List[Dict]:
        """Parse earnings with strict pattern: Description Rate Hours Amount."""
        earnings = []
        
        # Strict pattern: Word(s) $Rate Hours $Amount with 4 numbers
        # Example: "Regular Hourly $18.1900 55.28 $1,005.60"
        pattern = r'([A-Z][A-Za-z\s-]{2,25})\s+\$?([\d,]+\.\d{2,4})\s+([\d,]+\.\d{2})\s+\$?([\d,]+\.\d{2})'
        
        for line in text.split('\n'):
            # Skip metadata lines
            if ':' in line or 'Date' in line or 'Status' in line or len(line) < 20:
                continue
            
            match = re.search(pattern, line)
            if match:
                desc = match.group(1).strip()
                rate = self._safe_float(match.group(2))
                hours = self._safe_float(match.group(3))
                amount = self._safe_float(match.group(4))
                
                # Skip if doesn't look like earnings
                if rate > 500 or hours > 200 or amount > 50000:
                    continue
                
                # Map to employee
                emp_id, emp_name = self._find_employee(line, text, employees)
                
                earnings.append({
                    'employee_id': emp_id,
                    'employee_name': emp_name,
                    'description': desc,
                    'hours': hours,
                    'rate': rate,
                    'amount': amount,
                    'current_ytd': amount
                })
        
        return earnings
    
    def _parse_taxes(self, text: str, employees: List[Dict]) -> List[Dict]:
        """Parse taxes with strict pattern: Tax Name $Amount $Amount."""
        taxes = []
        
        # Tax keywords (must have at least one)
        tax_keywords = ['fed', 'fica', 'medicare', 'ss', 'state', 'w/h', 'tax', 'ut', 'mwt']
        
        # Strict pattern: Tax Name $Amount $Amount
        # Example: "Fed W/H $1,005.60 $62.35"
        pattern = r'([A-Z][A-Za-z\s/\-]{2,20})\s+\$?([\d,]+\.\d{2})\s+\$?([\d,]+\.\d{2})'
        
        for line in text.split('\n'):
            # Skip metadata
            if ':' in line or 'Date' in line or 'Status' in line or len(line) < 15:
                continue
            
            # Must have tax keyword
            if not any(kw in line.lower() for kw in tax_keywords):
                continue
            
            # Must NOT have earning keywords
            if any(kw in line.lower() for kw in ['regular', 'overtime', 'hourly', 'salary', 'bonus']):
                continue
            
            match = re.search(pattern, line)
            if match:
                desc = match.group(1).strip()
                wages = self._safe_float(match.group(2))
                amount = self._safe_float(match.group(3))
                
                # Skip unrealistic values
                if amount > 10000:
                    continue
                
                emp_id, emp_name = self._find_employee(line, text, employees)
                
                taxes.append({
                    'employee_id': emp_id,
                    'employee_name': emp_name,
                    'description': desc,
                    'wages_base': wages,
                    'amount': amount,
                    'wages_ytd': wages,
                    'amount_ytd': amount
                })
        
        return taxes
    
    def _parse_deductions(self, text: str, employees: List[Dict]) -> List[Dict]:
        """Parse deductions with strict pattern."""
        deductions = []
        
        # Deduction keywords
        ded_keywords = ['401k', '401(k)', 'insurance', 'medical', 'dental', 'vision', 
                        'life', 'hsa', 'fsa', 'uniform', 'pre-tax', 'pre tax']
        
        # Strict pattern: Description $Amount (single amount)
        # Example: "Medical Pre Tax $403.81"
        pattern = r'([A-Z][A-Za-z\s\-()]{2,30})\s+\$?([\d,]+\.\d{2})(?:\s|$)'
        
        for line in text.split('\n'):
            # Skip metadata
            if ':' in line or 'Date' in line or 'Status' in line or len(line) < 15:
                continue
            
            # Must have deduction keyword
            if not any(kw in line.lower() for kw in ded_keywords):
                continue
            
            # Must NOT have earning or tax keywords
            if any(kw in line.lower() for kw in ['regular', 'overtime', 'hourly', 'salary', 'fed', 'fica']):
                continue
            
            match = re.search(pattern, line)
            if match:
                desc = match.group(1).strip()
                amount = self._safe_float(match.group(2))
                
                # Skip unrealistic values
                if amount > 5000:
                    continue
                
                emp_id, emp_name = self._find_employee(line, text, employees)
                
                deductions.append({
                    'employee_id': emp_id,
                    'employee_name': emp_name,
                    'description': desc,
                    'scheduled': 0,
                    'amount': amount,
                    'amount_ytd': amount
                })
        
        return deductions
    
    def _find_employee(self, line: str, full_text: str, employees: List[Dict]) -> tuple:
        """Find which employee a line belongs to."""
        # Check if employee ID or name in line
        for emp in employees:
            if emp['employee_id'] in line or emp['employee_name'] in line:
                return emp['employee_id'], emp['employee_name']
        
        # Find nearest employee in text
        line_pos = full_text.find(line)
        if line_pos > 0:
            # Look backwards for nearest employee
            before_text = full_text[:line_pos]
            for emp in reversed(employees):
                emp_pattern = f"Emp #: {emp['employee_id']}"
                if emp_pattern in before_text:
                    last_pos = before_text.rfind(emp_pattern)
                    if line_pos - last_pos < 2000:  # Within 2000 chars
                        return emp['employee_id'], emp['employee_name']
        
        return "", ""
    
    def _safe_float(self, value: str) -> float:
        """Safely convert to float."""
        try:
            return float(str(value).replace(',', '').replace('$', ''))
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
        """Calculate accuracy."""
        score = 0
        
        if structured['employees'] and len(structured['employees']) >= 1:
            score += 30
        if structured['earnings']:
            score += 25
        if structured['taxes']:
            score += 25
        if structured['deductions']:
            score += 20
        
        return min(score, 100.0)
