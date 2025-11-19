"""
Intelligent Parser Orchestrator V2 - SIMPLIFIED APPROACH
Bypasses section detection, uses keyword-based filtering instead
"""

import logging
import re
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)

# Import only what we need
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    logger.warning("pdfplumber not available - V2 parser won't work")


class IntelligentParserOrchestratorV2:
    """
    Simplified V2 parser that:
    1. Extracts FULL PDF text once (pdfplumber)
    2. Parses ALL sections from same text using keyword filters
    3. No bbox detection needed
    """
    
    def __init__(self, custom_parsers_dir: str = None):
        self.logger = logging.getLogger(__name__)
        self.custom_parsers_dir = custom_parsers_dir  # Accept but don't use for now
        
        # Keywords for filtering sections
        self.earning_keywords = [
            'regular', 'overtime', 'ot', 'holiday', 'vacation', 'sick', 'pto',
            'bonus', 'commission', 'hourly', 'salary', 'wages', 'hours'
        ]
        
        self.tax_keywords = [
            'federal', 'fica', 'medicare', 'social security', 'ss', 'med',
            'fit', 'sit', 'futa', 'suta', 'state tax', 'local tax', 'city tax',
            'withholding', 'w/h', 'tax'
        ]
        
        self.deduction_keywords = [
            '401k', '401(k)', 'insurance', 'health', 'dental', 'vision', 'life',
            'retirement', 'benefit', 'medical', 'hsa', 'fsa', 'garnishment',
            'child support', 'union', 'dues', 'deduction'
        ]
    
    def parse(self, pdf_path: str, output_dir: str = '/data/parsed_registers', force_v2: bool = False) -> Dict[str, Any]:
        """
        Parse PDF using simplified keyword-based approach.
        
        Args:
            pdf_path: Path to PDF file
            output_dir: Where to save Excel output
            force_v2: Compatibility parameter (ignored, always uses V2)
            
        Returns:
            Dict with result info
        """
        try:
            self.logger.info(f"V2 Simplified Parser: {pdf_path}")
            
            # Step 1: Extract ALL text from PDF
            full_text = self._extract_full_text(pdf_path)
            if not full_text:
                raise Exception("Could not extract text from PDF")
            
            self.logger.info(f"Extracted {len(full_text)} characters of text")
            
            # Step 2: Parse employee info
            employees = self._parse_employee_info(full_text)
            self.logger.info(f"Found {len(employees)} employees")
            
            # Step 3: Parse all sections using keyword filtering
            earnings = self._parse_earnings(full_text, employees)
            taxes = self._parse_taxes(full_text, employees)
            deductions = self._parse_deductions(full_text, employees)
            
            self.logger.info(f"Extracted: {len(earnings)} earnings, {len(taxes)} taxes, {len(deductions)} deductions")
            
            # Step 4: Build structured data
            structured_data = {
                'employees': employees,
                'earnings': earnings,
                'taxes': taxes,
                'deductions': deductions
            }
            
            # Step 5: Create Excel tabs
            tabs = self._create_excel_tabs(structured_data)
            
            # Step 6: Write Excel file
            excel_path = self._write_excel(tabs, pdf_path, output_dir)
            
            # Step 7: Calculate accuracy
            accuracy = self._calculate_accuracy(structured_data, tabs)
            
            return {
                'success': True,
                'excel_path': excel_path,
                'accuracy': accuracy,
                'method': 'V2-Simplified-Keywords',
                'employees_found': len(employees),
                'earnings_found': len(earnings),
                'taxes_found': len(taxes),
                'deductions_found': len(deductions)
            }
            
        except Exception as e:
            self.logger.error(f"V2 parsing failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'method': 'V2-Simplified-Failed'
            }
    
    def _extract_full_text(self, pdf_path: str) -> str:
        """Extract complete text from PDF using pdfplumber."""
        if not PDFPLUMBER_AVAILABLE:
            raise Exception("pdfplumber not available")
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                full_text = ""
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"
                return full_text
        except Exception as e:
            self.logger.error(f"pdfplumber extraction failed: {e}")
            return ""
    
    def _parse_employee_info(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse employee information from text.
        Looks for: Employee ID, Name, Department
        """
        employees = []
        lines = text.split('\n')
        
        # Pattern for employee ID (common formats: 10807, EMP-10807, E10807)
        emp_id_pattern = r'(?:emp[-\s]?#?|employee[-\s]?id[-:\s]?|emp[-:\s]?)?(\d{4,6})'
        
        # Find lines with employee IDs
        for i, line in enumerate(lines):
            match = re.search(emp_id_pattern, line, re.IGNORECASE)
            if match:
                emp_id = match.group(1)
                
                # Look for name nearby (next few lines)
                name = None
                for j in range(i, min(i+5, len(lines))):
                    # Name pattern: "LastName, FirstName" or "FirstName LastName"
                    name_pattern = r'([A-Z][a-z]+(?:,\s+|\s+)[A-Z][a-z]+)'
                    name_match = re.search(name_pattern, lines[j])
                    if name_match:
                        name = name_match.group(1)
                        break
                
                if name:
                    employees.append({
                        'employee_id': emp_id,
                        'employee_name': name,
                        'department': ''  # Can add department parsing if needed
                    })
        
        # Remove duplicates
        seen = set()
        unique_employees = []
        for emp in employees:
            key = emp['employee_id']
            if key not in seen:
                seen.add(key)
                unique_employees.append(emp)
        
        return unique_employees
    
    def _parse_earnings(self, text: str, employees: List[Dict]) -> List[Dict[str, Any]]:
        """
        Parse earnings from text using keyword filtering.
        Looks for lines containing earning keywords + dollar amounts.
        """
        earnings = []
        lines = text.split('\n')
        
        # Pattern for dollar amounts and hours
        amount_pattern = r'\$?([\d,]+\.?\d*)'
        
        for line in lines:
            line_lower = line.lower()
            
            # Check if line contains earning keywords
            has_earning_keyword = any(keyword in line_lower for keyword in self.earning_keywords)
            
            if has_earning_keyword:
                # Extract description (first substantial word group)
                desc_match = re.search(r'([A-Za-z][\w\s]{2,30})', line)
                description = desc_match.group(1).strip() if desc_match else ""
                
                # Extract numbers (hours, rate, amount)
                numbers = re.findall(amount_pattern, line)
                numbers = [float(n.replace(',', '')) for n in numbers if n and n.strip()]
                
                if description and numbers:
                    # Try to map to employee (look for ID in line or nearby context)
                    employee_id = ""
                    employee_name = ""
                    for emp in employees:
                        if emp['employee_id'] in line or emp['employee_name'] in line:
                            employee_id = emp['employee_id']
                            employee_name = emp['employee_name']
                            break
                    
                    # If we have at least 2 numbers, try to parse as hours + amount
                    hours = numbers[0] if len(numbers) >= 1 else 0
                    rate = numbers[1] if len(numbers) >= 2 else 0
                    amount = numbers[-1]  # Last number is usually the amount
                    
                    earnings.append({
                        'employee_id': employee_id,
                        'employee_name': employee_name,
                        'description': description,
                        'hours': hours,
                        'rate': rate,
                        'amount': amount,
                        'current_ytd': amount  # Can improve with YTD parsing
                    })
        
        return earnings
    
    def _parse_taxes(self, text: str, employees: List[Dict]) -> List[Dict[str, Any]]:
        """
        Parse taxes from text using keyword filtering.
        Looks for lines containing tax keywords + dollar amounts.
        """
        taxes = []
        lines = text.split('\n')
        
        amount_pattern = r'\$?([\d,]+\.?\d*)'
        
        for line in lines:
            line_lower = line.lower()
            
            # Check if line contains tax keywords
            has_tax_keyword = any(keyword in line_lower for keyword in self.tax_keywords)
            
            # CRITICAL: Exclude earning keywords to avoid false positives
            has_earning_keyword = any(keyword in line_lower for keyword in self.earning_keywords)
            
            if has_tax_keyword and not has_earning_keyword:
                # Extract description
                desc_match = re.search(r'([A-Za-z][\w\s]{2,30})', line)
                description = desc_match.group(1).strip() if desc_match else ""
                
                # Extract numbers
                numbers = re.findall(amount_pattern, line)
                numbers = [float(n.replace(',', '')) for n in numbers if n and n.strip()]
                
                if description and numbers:
                    # Map to employee
                    employee_id = ""
                    employee_name = ""
                    for emp in employees:
                        if emp['employee_id'] in line or emp['employee_name'] in line:
                            employee_id = emp['employee_id']
                            employee_name = emp['employee_name']
                            break
                    
                    # Wages base is often first number, amount is last
                    wages_base = numbers[0] if len(numbers) >= 2 else 0
                    amount = numbers[-1]
                    
                    taxes.append({
                        'employee_id': employee_id,
                        'employee_name': employee_name,
                        'description': description,
                        'wages_base': wages_base,
                        'amount': amount,
                        'wages_ytd': wages_base,
                        'amount_ytd': amount
                    })
        
        return taxes
    
    def _parse_deductions(self, text: str, employees: List[Dict]) -> List[Dict[str, Any]]:
        """
        Parse deductions from text using keyword filtering.
        Looks for lines containing deduction keywords + dollar amounts.
        """
        deductions = []
        lines = text.split('\n')
        
        amount_pattern = r'\$?([\d,]+\.?\d*)'
        
        for line in lines:
            line_lower = line.lower()
            
            # Check if line contains deduction keywords
            has_deduction_keyword = any(keyword in line_lower for keyword in self.deduction_keywords)
            
            # CRITICAL: Exclude earning and tax keywords
            has_earning_keyword = any(keyword in line_lower for keyword in self.earning_keywords)
            has_tax_keyword = any(keyword in line_lower for keyword in self.tax_keywords)
            
            if has_deduction_keyword and not has_earning_keyword and not has_tax_keyword:
                # Extract description
                desc_match = re.search(r'([A-Za-z][\w\s]{2,30})', line)
                description = desc_match.group(1).strip() if desc_match else ""
                
                # Extract numbers
                numbers = re.findall(amount_pattern, line)
                numbers = [float(n.replace(',', '')) for n in numbers if n and n.strip()]
                
                if description and numbers:
                    # Map to employee
                    employee_id = ""
                    employee_name = ""
                    for emp in employees:
                        if emp['employee_id'] in line or emp['employee_name'] in line:
                            employee_id = emp['employee_id']
                            employee_name = emp['employee_name']
                            break
                    
                    # Scheduled and amount
                    scheduled = numbers[0] if len(numbers) >= 2 else 0
                    amount = numbers[-1]
                    
                    deductions.append({
                        'employee_id': employee_id,
                        'employee_name': employee_name,
                        'description': description,
                        'scheduled': scheduled,
                        'amount': amount,
                        'amount_ytd': amount
                    })
        
        return deductions
    
    def _create_excel_tabs(self, structured: Dict) -> Dict[str, pd.DataFrame]:
        """Create 4 Excel tabs from structured data."""
        
        # Employee Summary
        summary_data = []
        for emp in structured['employees']:
            emp_id = emp['employee_id']
            emp_name = emp['employee_name']
            
            # Sum earnings for this employee
            emp_earnings = [e for e in structured['earnings'] if e['employee_id'] == emp_id]
            total_earnings = sum(e['amount'] for e in emp_earnings)
            
            # Sum taxes for this employee
            emp_taxes = [t for t in structured['taxes'] if t['employee_id'] == emp_id]
            total_taxes = sum(t['amount'] for t in emp_taxes)
            
            # Sum deductions for this employee
            emp_deductions = [d for d in structured['deductions'] if d['employee_id'] == emp_id]
            total_deductions = sum(d['amount'] for d in emp_deductions)
            
            summary_data.append({
                'Employee ID': emp_id,
                'Name': emp_name,
                'Total Earnings': total_earnings,
                'Total Taxes': total_taxes,
                'Total Deductions': total_deductions,
                'Net Pay': total_earnings - total_taxes - total_deductions
            })
        
        # Earnings
        earnings_data = [{
            'Employee ID': e['employee_id'],
            'Name': e['employee_name'],
            'Description': e['description'],
            'Hours': e['hours'],
            'Rate': e['rate'],
            'Amount': e['amount'],
            'Current YTD': e['current_ytd']
        } for e in structured['earnings']]
        
        # Taxes
        taxes_data = [{
            'Employee ID': t['employee_id'],
            'Name': t['employee_name'],
            'Description': t['description'],
            'Wages Base': t['wages_base'],
            'Amount': t['amount'],
            'Wages YTD': t['wages_ytd'],
            'Amount YTD': t['amount_ytd']
        } for t in structured['taxes']]
        
        # Deductions
        deductions_data = [{
            'Employee ID': d['employee_id'],
            'Name': d['employee_name'],
            'Description': d['description'],
            'Scheduled': d['scheduled'],
            'Amount': d['amount'],
            'Amount YTD': d['amount_ytd']
        } for d in structured['deductions']]
        
        return {
            'Employee Summary': pd.DataFrame(summary_data),
            'Earnings': pd.DataFrame(earnings_data),
            'Taxes': pd.DataFrame(taxes_data),
            'Deductions': pd.DataFrame(deductions_data)
        }
    
    def _write_excel(self, tabs: Dict[str, pd.DataFrame], pdf_path: str, output_dir: str) -> str:
        """Write tabs to Excel file."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        pdf_name = Path(pdf_path).stem
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = output_dir / f"{pdf_name}_parsed_v2_simplified_{timestamp}.xlsx"
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            for tab_name, df in tabs.items():
                df.to_excel(writer, sheet_name=tab_name, index=False)
        
        return str(output_path)
    
    def _calculate_accuracy(self, structured: Dict, tabs: Dict[str, pd.DataFrame]) -> float:
        """
        Calculate accuracy score based on data extracted.
        """
        score = 0
        
        # Employees found (30 points)
        if structured['employees']:
            score += 20
        if len(structured['employees']) >= 2:
            score += 10
        
        # Data extracted (40 points total)
        if structured['earnings']:
            score += 15
        if structured['taxes']:
            score += 15
        if structured['deductions']:
            score += 10
        
        # Real data validation (30 points)
        emp_summary = tabs['Employee Summary']
        if not emp_summary.empty:
            # Check if amounts are non-zero
            if emp_summary['Total Earnings'].sum() > 0:
                score += 15
            if emp_summary['Total Taxes'].sum() > 0:
                score += 10
            if emp_summary['Total Deductions'].sum() > 0:
                score += 5
        
        return min(score, 100.0)


# Convenience function
def parse_pdf_intelligent_v2(pdf_path: str, output_dir: str = '/data/parsed_registers') -> Dict[str, Any]:
    """Parse PDF using V2 simplified approach."""
    orchestrator = IntelligentParserOrchestratorV2()
    return orchestrator.parse(pdf_path, output_dir)
