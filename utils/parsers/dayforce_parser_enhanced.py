"""
Improved Dayforce Register Parser
Handles horizontal multi-column layout with side-by-side sections per employee
"""

import re
import fitz  # PyMuPDF
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class DayforceParserEnhanced:
    """
    Enhanced parser for Dayforce payroll registers with complex layouts.
    Handles horizontal employee blocks with side-by-side sections.
    """
    
    def __init__(self):
        """Initialize parser."""
        pass
    
    def parse(self, pdf_path: str, output_dir: str = '/data/parsed_registers') -> Dict[str, Any]:
        """
        Parse Dayforce register and return 4-tab Excel.
        
        Args:
            pdf_path: Path to PDF file
            output_dir: Directory for Excel output
            
        Returns:
            Dict with status, output_path, accuracy, and employee_count
        """
        try:
            logger.info(f"Opening Dayforce PDF: {pdf_path}")
            
            # Extract text with layout preservation
            doc = fitz.open(pdf_path)
            
            # Get text blocks with position information
            employees = []
            
            for page_num, page in enumerate(doc):
                logger.info(f"Processing page {page_num + 1}")
                
                # Get text with layout (preserves positioning)
                text = page.get_text("text")
                
                # Parse employees from this page
                page_employees = self._parse_page_employees(text)
                employees.extend(page_employees)
            
            doc.close()
            
            if not employees:
                logger.warning("No employee data extracted")
                return {
                    'status': 'error',
                    'message': 'No employee data found in PDF',
                    'accuracy': 0,
                    'employee_count': 0
                }
            
            logger.info(f"Parsed {len(employees)} employees")
            
            # Create 4-tab DataFrame structure
            tabs = self._create_four_tabs(employees)
            
            # Write to Excel
            output_path = self._write_excel(tabs, pdf_path, output_dir)
            
            # Calculate accuracy
            accuracy = self._calculate_accuracy(tabs, employees)
            
            return {
                'status': 'success',
                'output_path': output_path,
                'accuracy': accuracy,
                'employee_count': len(employees),
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
    
    def _parse_page_employees(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse employees from a page of text.
        Handles horizontal layout with side-by-side sections.
        """
        employees = []
        
        # Split by employee - look for "Emp #:" pattern
        emp_pattern = r'Emp #:\s*(\d+)'
        matches = list(re.finditer(emp_pattern, text))
        
        if not matches:
            logger.warning("No employee ID patterns found")
            return employees
        
        # Extract each employee block
        for i, match in enumerate(matches):
            start_pos = match.start()
            
            # Find end of this employee block
            if i + 1 < len(matches):
                end_pos = matches[i + 1].start()
            else:
                # Last employee - look for page footer or end
                footer_match = re.search(r'(?:Confidential|Page \d+ of|\* italicized amounts)', text[start_pos:])
                if footer_match:
                    end_pos = start_pos + footer_match.start()
                else:
                    end_pos = len(text)
            
            # Extract employee block
            emp_block = text[start_pos:end_pos]
            
            # Parse this employee
            employee = self._parse_single_employee(emp_block, match.group(1))
            if employee:
                employees.append(employee)
        
        return employees
    
    def _parse_single_employee(self, block: str, emp_id: str) -> Optional[Dict[str, Any]]:
        """
        Parse a single employee block with horizontal sections.
        """
        try:
            employee = {
                'info': {'employee_id': emp_id},
                'earnings': [],
                'taxes': [],
                'deductions': []
            }
            
            # Extract employee info fields (appears at start of block)
            info_patterns = {
                'name': r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',  # First line is name
                'dept': r'Dept:\s*([^\n]+)',
                'hire_date': r'Hire Date:\s*([^\n]+)',
                'term_date': r'Term Date:\s*([^\n]+)',
                'ssn': r'SSN:\s*(X+\d+)',
                'status': r'Status:\s*([^\n]+)',
                'frequency': r'Frequency:\s*([^\n]+)',
                'type': r'Type:\s*([^\n]+)',
                'rate': r'Rate:\s*\$?([\d,.]+)',
                'salary': r'Sal:\s*\$?([\d,.]+)',
                'federal': r'Federal:\s*([^\n]+)',
                'state': r'State:\s*([^\n]+)'
            }
            
            for field, pattern in info_patterns.items():
                match = re.search(pattern, block, re.MULTILINE)
                if match:
                    employee['info'][field] = match.group(1).strip()
            
            # Parse earnings section
            # Earnings appear after employee info, before taxes
            earnings_section = self._extract_section_by_header(block, 'Earnings', 'Taxes')
            if earnings_section:
                employee['earnings'] = self._parse_earnings(earnings_section)
            
            # Parse taxes section
            taxes_section = self._extract_section_by_header(block, 'Taxes', 'Deductions')
            if taxes_section:
                employee['taxes'] = self._parse_taxes(taxes_section)
            
            # Parse deductions section
            deductions_section = self._extract_section_after_header(block, 'Deductions')
            if deductions_section:
                employee['deductions'] = self._parse_deductions(deductions_section)
            
            return employee
            
        except Exception as e:
            logger.error(f"Error parsing employee {emp_id}: {str(e)}")
            return None
    
    def _extract_section_by_header(self, text: str, start_header: str, end_header: str) -> Optional[str]:
        """
        Extract section between two headers.
        """
        # Find start position
        start_match = re.search(rf'\b{start_header}\b', text, re.IGNORECASE)
        if not start_match:
            return None
        
        # Find end position
        end_match = re.search(rf'\b{end_header}\b', text[start_match.end():], re.IGNORECASE)
        if not end_match:
            return text[start_match.end():]
        
        return text[start_match.end():start_match.end() + end_match.start()]
    
    def _extract_section_after_header(self, text: str, header: str) -> Optional[str]:
        """
        Extract section after a header to end of text.
        """
        match = re.search(rf'\b{header}\b', text, re.IGNORECASE)
        if not match:
            return None
        
        return text[match.end():]
    
    def _parse_earnings(self, section: str) -> List[Dict[str, Any]]:
        """
        Parse earnings section.
        Expected columns: Description, Rate, Hours, Amount, HoursYTD, AmountYTD
        """
        earnings = []
        
        # Split into lines
        lines = section.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 10:
                continue
            
            # Skip header lines
            if any(word in line for word in ['Description', 'Rate', 'Hours', 'Amount', 'YTD']):
                continue
            
            # Skip total lines
            if 'Total' in line:
                continue
            
            # Look for lines with amounts (contains $)
            if '$' in line or re.search(r'\d+\.\d{2}', line):
                # Try to parse structured data
                # Pattern: Description Rate Hours Amount ...
                parts = re.split(r'\s{2,}', line)
                
                if len(parts) >= 2:
                    earning = {
                        'description': parts[0].strip(),
                        'amount': self._extract_amount(line)
                    }
                    
                    # Try to extract rate and hours
                    rate_match = re.search(r'\$?([\d,]+\.\d+)', line)
                    if rate_match:
                        earning['rate'] = rate_match.group(1)
                    
                    hours_match = re.search(r'(\d+\.\d+)\s+\$', line)
                    if hours_match:
                        earning['hours'] = hours_match.group(1)
                    
                    earnings.append(earning)
        
        return earnings
    
    def _parse_taxes(self, section: str) -> List[Dict[str, Any]]:
        """
        Parse taxes section.
        Expected columns: Description, Wages, Amount, WagesYTD, AmountYTD
        """
        taxes = []
        
        lines = section.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 10:
                continue
            
            # Skip headers and totals
            if any(word in line for word in ['Description', 'Wages', 'Amount', 'YTD', 'Total']):
                continue
            
            # Look for tax lines (usually have Fed, FICA, State abbreviations)
            if re.search(r'(?:Fed|FICA|State|W/H|MWT|UT|ER|EE)', line, re.IGNORECASE):
                parts = re.split(r'\s{2,}', line)
                
                if len(parts) >= 2:
                    tax = {
                        'description': parts[0].strip(),
                        'amount': self._extract_amount(line)
                    }
                    taxes.append(tax)
        
        return taxes
    
    def _parse_deductions(self, section: str) -> List[Dict[str, Any]]:
        """
        Parse deductions section.
        Expected columns: Description, Scheduled, Amount, AmountYTD
        """
        deductions = []
        
        lines = section.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 10:
                continue
            
            # Skip headers and totals
            if any(word in line for word in ['Description', 'Scheduled', 'Amount', 'YTD', 'Total', 'Current']):
                continue
            
            # Look for deduction lines with amounts
            if '$' in line or re.search(r'\d+\.\d{2}', line):
                parts = re.split(r'\s{2,}', line)
                
                if len(parts) >= 1:
                    deduction = {
                        'description': parts[0].strip(),
                        'amount': self._extract_amount(line)
                    }
                    deductions.append(deduction)
        
        return deductions
    
    def _extract_amount(self, text: str) -> str:
        """
        Extract dollar amount from text.
        """
        # Look for patterns like $1,234.56 or 1234.56
        match = re.search(r'\$?([\d,]+\.\d{2})', text)
        if match:
            return match.group(1).replace(',', '')
        return '0.00'
    
    def _create_four_tabs(self, employees: List[Dict[str, Any]]) -> Dict[str, pd.DataFrame]:
        """
        Create 4 DataFrames from employee data.
        """
        tabs = {
            'Employee Summary': [],
            'Earnings': [],
            'Taxes': [],
            'Deductions': []
        }
        
        for emp in employees:
            # Employee Summary tab
            summary = emp['info'].copy()
            
            # Calculate totals
            summary['Total_Earnings'] = sum(
                float(e.get('amount', 0)) for e in emp['earnings']
                if str(e.get('amount', '')).replace('.', '').replace('-', '').isdigit()
            )
            
            summary['Total_Taxes'] = sum(
                float(t.get('amount', 0)) for t in emp['taxes']
                if str(t.get('amount', '')).replace('.', '').replace('-', '').isdigit()
            )
            
            summary['Total_Deductions'] = sum(
                float(d.get('amount', 0)) for d in emp['deductions']
                if str(d.get('amount', '')).replace('.', '').replace('-', '').isdigit()
            )
            
            summary['Net_Pay'] = summary['Total_Earnings'] - summary['Total_Taxes'] - summary['Total_Deductions']
            
            tabs['Employee Summary'].append(summary)
            
            # Earnings tab - one row per earning type
            for earning in emp['earnings']:
                earning_row = emp['info'].copy()
                earning_row.update(earning)
                tabs['Earnings'].append(earning_row)
            
            # Taxes tab - one row per tax type
            for tax in emp['taxes']:
                tax_row = emp['info'].copy()
                tax_row.update(tax)
                tabs['Taxes'].append(tax_row)
            
            # Deductions tab - one row per deduction type
            for deduction in emp['deductions']:
                deduction_row = emp['info'].copy()
                deduction_row.update(deduction)
                tabs['Deductions'].append(deduction_row)
        
        # Convert to DataFrames
        return {
            name: pd.DataFrame(rows) if rows else pd.DataFrame()
            for name, rows in tabs.items()
        }
    
    def _write_excel(self, tabs: Dict[str, pd.DataFrame], pdf_path: str, output_dir: str) -> str:
        """
        Write 4 tabs to Excel file.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        pdf_name = Path(pdf_path).stem
        output_path = output_dir / f"{pdf_name}_parsed.xlsx"
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            for tab_name, df in tabs.items():
                df.to_excel(writer, sheet_name=tab_name, index=False)
        
        logger.info(f"Excel written to: {output_path}")
        return str(output_path)
    
    def _calculate_accuracy(self, tabs: Dict[str, pd.DataFrame], employees: List[Dict]) -> int:
        """
        Calculate accuracy score (0-100).
        """
        score = 0
        
        # Basic success (30 pts)
        if tabs and all(isinstance(df, pd.DataFrame) for df in tabs.values()):
            score += 30
        
        # Table quality (40 pts) - based on row count
        total_rows = sum(len(df) for df in tabs.values() if len(df) > 0)
        expected_rows = len(employees) * 10  # Rough estimate
        
        if total_rows > 0:
            quality_score = min(40, int((total_rows / max(expected_rows, 1)) * 40))
            score += quality_score
        
        # Data extraction (20 pts) - based on fields extracted
        total_fields = sum(len(emp['info']) for emp in employees)
        avg_fields = total_fields / max(len(employees), 1)
        
        if avg_fields >= 8:
            score += 20
        elif avg_fields >= 5:
            score += 15
        elif avg_fields >= 3:
            score += 10
        
        # Data quality (10 pts) - all employees have required fields
        has_required = all('employee_id' in emp['info'] for emp in employees)
        if has_required:
            score += 10
        
        return min(100, score)


def parse_dayforce_register(pdf_path: str, output_dir: str = '/data/parsed_registers') -> Dict[str, Any]:
    """
    Convenience function for parsing Dayforce registers.
    """
    parser = DayforceParserEnhanced()
    return parser.parse(pdf_path, output_dir)
