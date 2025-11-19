"""
Enhanced Dayforce Register Parser
Handles complex multi-section layouts iteratively
"""

import re
from typing import Dict, List, Any, Optional
import pandas as pd
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class DayforceParserEnhanced:
    """
    Iteratively parses Dayforce payroll registers with multiple sections per employee.
    
    Sections: Employee Info | Earnings | Taxes | Deductions
    """
    
    def __init__(self):
        self.section_patterns = {
            'employee_info': r'(?:Employee\s+Info|Employee\s+Information|EMP\s+INFO)',
            'earnings': r'(?:Earnings|PAY\s+ITEMS|Income)',
            'taxes': r'(?:Taxes|Tax\s+Deductions|Statutory)',
            'deductions': r'(?:Deductions|Pre-Tax|Post-Tax|Benefits)'
        }
        
        # Common field patterns
        self.field_patterns = {
            'employee_id': r'(?:ID|EMP#|Employee\s+ID)[\s:]+(\d+)',
            'name': r'(?:Name|Employee)[\s:]+([A-Za-z\s,]+)',
            'ssn': r'(?:SSN)[\s:]+(\d{3}-\d{2}-\d{4})',
            'department': r'(?:Dept|Department)[\s:]+([^\n]+)',
            'pay_period': r'(?:Pay\s+Period|Period)[\s:]+([^\n]+)',
            'check_date': r'(?:Check\s+Date|Date)[\s:]+([^\n]+)'
        }
    
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
            import fitz  # PyMuPDF
            
            logger.info(f"Opening PDF: {pdf_path}")
            doc = fitz.open(pdf_path)
            
            # Extract all text
            full_text = ""
            for page in doc:
                full_text += page.get_text()
            
            logger.info(f"Extracted {len(full_text)} characters from PDF")
            
            # Parse employee blocks
            employees = self._parse_employee_blocks(full_text)
            
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
    
    def _parse_employee_blocks(self, text: str) -> List[Dict[str, Any]]:
        """
        Iteratively parse employee blocks from text.
        Each employee has 4 sections.
        """
        employees = []
        
        # Split by employee boundaries (look for ID pattern)
        # Pattern: new employee starts with ID line
        employee_pattern = r'(?:Employee\s+ID|EMP#|ID)[\s:]+(\d+)'
        
        employee_starts = [m.start() for m in re.finditer(employee_pattern, text)]
        
        if not employee_starts:
            logger.warning("No employee ID patterns found")
            return employees
        
        # Add end position
        employee_starts.append(len(text))
        
        # Extract each employee block
        for i in range(len(employee_starts) - 1):
            start = employee_starts[i]
            end = employee_starts[i + 1]
            block = text[start:end]
            
            employee_data = self._parse_single_employee(block)
            if employee_data:
                employees.append(employee_data)
        
        return employees
    
    def _parse_single_employee(self, block: str) -> Optional[Dict[str, Any]]:
        """
        Parse a single employee block with 4 sections.
        """
        try:
            employee = {
                'info': {},
                'earnings': [],
                'taxes': [],
                'deductions': []
            }
            
            # Extract employee info fields
            for field_name, pattern in self.field_patterns.items():
                match = re.search(pattern, block, re.IGNORECASE)
                if match:
                    employee['info'][field_name] = match.group(1).strip()
            
            # Find section boundaries
            sections = self._find_section_boundaries(block)
            
            # Extract each section
            if 'earnings' in sections:
                employee['earnings'] = self._extract_table_section(
                    block[sections['earnings']['start']:sections['earnings']['end']]
                )
            
            if 'taxes' in sections:
                employee['taxes'] = self._extract_table_section(
                    block[sections['taxes']['start']:sections['taxes']['end']]
                )
            
            if 'deductions' in sections:
                employee['deductions'] = self._extract_table_section(
                    block[sections['deductions']['start']:sections['deductions']['end']]
                )
            
            # Only return if we have at least employee ID
            if employee['info'].get('employee_id'):
                return employee
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing employee block: {str(e)}")
            return None
    
    def _find_section_boundaries(self, block: str) -> Dict[str, Dict[str, int]]:
        """
        Find where each section starts and ends in the employee block.
        """
        sections = {}
        
        for section_name, pattern in self.section_patterns.items():
            match = re.search(pattern, block, re.IGNORECASE)
            if match:
                sections[section_name] = {
                    'start': match.end(),
                    'end': len(block)  # Will be updated
                }
        
        # Update end positions (each section ends where next begins)
        section_list = sorted(sections.items(), key=lambda x: x[1]['start'])
        
        for i in range(len(section_list) - 1):
            section_name = section_list[i][0]
            next_start = section_list[i + 1][1]['start']
            sections[section_name]['end'] = next_start
        
        return sections
    
    def _extract_table_section(self, section_text: str) -> List[Dict[str, Any]]:
        """
        Extract table data from a section (earnings/taxes/deductions).
        Uses line-by-line parsing with column detection.
        """
        rows = []
        
        # Split into lines
        lines = [line.strip() for line in section_text.split('\n') if line.strip()]
        
        if not lines:
            return rows
        
        # First non-empty line is likely the header
        header_line = lines[0]
        headers = self._extract_columns_from_line(header_line)
        
        # Parse data rows
        for line in lines[1:]:
            # Skip total lines and separators
            if any(word in line.lower() for word in ['total', '---', '===', 'subtotal']):
                continue
            
            values = self._extract_columns_from_line(line)
            
            if values and len(values) > 0:
                # Create row dict
                row = {}
                for i, value in enumerate(values):
                    col_name = headers[i] if i < len(headers) else f'Column_{i+1}'
                    row[col_name] = value
                
                rows.append(row)
        
        return rows
    
    def _extract_columns_from_line(self, line: str) -> List[str]:
        """
        Extract columns from a line using whitespace detection.
        Handles varying column widths.
        """
        # Split by 2+ spaces (common column separator)
        columns = re.split(r'\s{2,}', line)
        return [col.strip() for col in columns if col.strip()]
    
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
            summary['Total_Earnings'] = sum(
                float(e.get('Amount', 0)) for e in emp['earnings'] 
                if isinstance(e.get('Amount'), (int, float, str)) and str(e.get('Amount', '')).replace('.', '').replace('-', '').isdigit()
            ) if emp['earnings'] else 0
            summary['Total_Taxes'] = sum(
                float(t.get('Amount', 0)) for t in emp['taxes']
                if isinstance(t.get('Amount'), (int, float, str)) and str(t.get('Amount', '')).replace('.', '').replace('-', '').isdigit()
            ) if emp['taxes'] else 0
            summary['Total_Deductions'] = sum(
                float(d.get('Amount', 0)) for d in emp['deductions']
                if isinstance(d.get('Amount'), (int, float, str)) and str(d.get('Amount', '')).replace('.', '').replace('-', '').isdigit()
            ) if emp['deductions'] else 0
            summary['Net_Pay'] = summary['Total_Earnings'] - summary['Total_Taxes'] - summary['Total_Deductions']
            
            tabs['Employee Summary'].append(summary)
            
            # Earnings tab
            for earning in emp['earnings']:
                earning_row = emp['info'].copy()
                earning_row.update(earning)
                tabs['Earnings'].append(earning_row)
            
            # Taxes tab
            for tax in emp['taxes']:
                tax_row = emp['info'].copy()
                tax_row.update(tax)
                tabs['Taxes'].append(tax_row)
            
            # Deductions tab
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
        
        # Table quality (40 pts)
        total_rows = sum(len(df) for df in tabs.values())
        if total_rows > 0:
            score += min(40, int(total_rows / len(employees) * 10)) if employees else 0
        
        # Data extraction (20 pts)
        info_fields = sum(
            len(emp['info']) for emp in employees
        ) / max(len(employees), 1)
        score += min(20, int(info_fields * 3))
        
        # Data quality (10 pts)
        has_required = all(
            'employee_id' in emp['info'] for emp in employees
        )
        if has_required:
            score += 10
        
        return min(100, score)


def parse_dayforce_register(pdf_path: str, output_dir: str = '/data/parsed_registers') -> Dict[str, Any]:
    """
    Convenience function for parsing Dayforce registers.
    """
    parser = DayforceParserEnhanced()
    return parser.parse(pdf_path, output_dir)
