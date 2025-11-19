"""
Intelligent Parser Orchestrator V2 - BBOX-BASED (Fixed)
Uses section detection + multi-method extraction with proper bbox passing
"""

import logging
import re
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)

# Import dependencies
try:
    from .section_detector import SectionDetector
    from .multi_method_extractor import MultiMethodExtractor
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    try:
        from section_detector import SectionDetector
        from multi_method_extractor import MultiMethodExtractor
        DEPENDENCIES_AVAILABLE = True
    except ImportError:
        DEPENDENCIES_AVAILABLE = False
        logger.error("section_detector or multi_method_extractor not available")


class IntelligentParserOrchestratorV2:
    """
    V2 parser that uses section detection + multi-method extraction.
    Properly passes bbox to extraction methods.
    """
    
    def __init__(self, custom_parsers_dir: str = None):
        self.logger = logging.getLogger(__name__)
        self.custom_parsers_dir = custom_parsers_dir
        
        if not DEPENDENCIES_AVAILABLE:
            raise Exception("Required dependencies not available")
        
        self.section_detector = SectionDetector()
        self.multi_method_extractor = MultiMethodExtractor()
    
    def parse(self, pdf_path: str, output_dir: str = '/data/parsed_registers', force_v2: bool = False) -> Dict[str, Any]:
        """
        Parse PDF using section-based multi-method approach.
        
        Args:
            pdf_path: Path to PDF file
            output_dir: Where to save Excel output
            force_v2: Compatibility parameter (always uses V2)
            
        Returns:
            Dict with result info
        """
        try:
            self.logger.info(f"=== V2 Parser Starting (bbox-based) ===")
            self.logger.info(f"PDF: {pdf_path}")
            
            # Step 1: Detect sections
            self.logger.info("Step 1: Detecting sections...")
            sections = self.section_detector.detect_sections(pdf_path)
            
            if not sections:
                raise Exception("No sections detected")
            
            self.logger.info(f"Found {len(sections)}/4 sections")
            for section_type, section_info in sections.items():
                bbox = section_info.get('bbox') or section_info
                self.logger.info(f"  {section_type}: bbox={bbox}")
            
            # Step 2: Extract each section with multi-method
            self.logger.info("Step 2: Extracting sections with best methods...")
            section_data = {}
            
            for section_type, section_info in sections.items():
                bbox = section_info.get('bbox') or section_info
                
                # CRITICAL: Pass bbox to multi_method_extractor
                self.logger.info(f"  Extracting {section_type} with bbox={bbox}")
                all_results = self.multi_method_extractor.extract_all_methods(pdf_path, section_bbox=bbox)
                
                # Get best method
                best_method, best_result = self.multi_method_extractor.get_best_method(all_results, section_type)
                
                if best_result and best_result.get('success'):
                    text = best_result.get('text', '')
                    self.logger.info(f"    Best: {best_method}, text length: {len(text)} chars")
                    self.logger.info(f"    Preview: {text[:100]}...")
                    section_data[section_type] = {
                        'method': best_method,
                        'data': best_result
                    }
                else:
                    self.logger.warning(f"    No successful extraction for {section_type}")
                    section_data[section_type] = {'method': 'none', 'data': {}}
            
            # Step 3: Parse structured data from extracted sections
            self.logger.info("Step 3: Parsing structured data...")
            structured_data = self._parse_sections(section_data)
            
            self.logger.info(f"Found {len(structured_data['employees'])} employees, "
                           f"{len(structured_data['earnings'])} earnings, "
                           f"{len(structured_data['taxes'])} taxes, "
                           f"{len(structured_data['deductions'])} deductions")
            
            # Step 4: Create Excel tabs
            tabs = self._create_excel_tabs(structured_data)
            
            # Step 5: Write Excel file
            excel_path = self._write_excel(tabs, pdf_path, output_dir)
            
            # Step 6: Calculate accuracy
            accuracy = self._calculate_accuracy(structured_data, tabs)
            
            # Report methods used per section
            methods_used = {k: v.get('method') for k, v in section_data.items()}
            
            return {
                'success': True,
                'excel_path': excel_path,
                'accuracy': accuracy,
                'method': 'V2-Bbox-Multi-Method',
                'methods_per_section': methods_used,
                'employees_found': len(structured_data['employees']),
                'earnings_found': len(structured_data['earnings']),
                'taxes_found': len(structured_data['taxes']),
                'deductions_found': len(structured_data['deductions'])
            }
            
        except Exception as e:
            self.logger.error(f"V2 bbox parsing failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'method': 'V2-Bbox-Failed'
            }
    
    def _parse_sections(self, section_data: Dict) -> Dict:
        """Parse structured data from extracted sections."""
        structured = {
            'employees': [],
            'earnings': [],
            'taxes': [],
            'deductions': []
        }
        
        # Parse employee info
        if 'employee_info' in section_data:
            emp_data = section_data['employee_info']['data']
            structured['employees'] = self._parse_employee_info(emp_data)
        
        # Parse earnings
        if 'earnings' in section_data:
            earnings_data = section_data['earnings']['data']
            structured['earnings'] = self._parse_earnings(earnings_data, structured['employees'])
        
        # Parse taxes
        if 'taxes' in section_data:
            taxes_data = section_data['taxes']['data']
            structured['taxes'] = self._parse_taxes(taxes_data, structured['employees'])
        
        # Parse deductions
        if 'deductions' in section_data:
            deductions_data = section_data['deductions']['data']
            structured['deductions'] = self._parse_deductions(deductions_data, structured['employees'])
        
        return structured
    
    def _parse_employee_info(self, data: Dict) -> List[Dict]:
        """Parse employee info from extracted data."""
        employees = []
        text = data.get('text', '')
        lines = data.get('lines', [])
        
        # Pattern for employee ID
        emp_id_pattern = r'(?:emp\s*#?|employee\s*id)[\s:]*(\d{4,6})'
        
        # Pattern for names
        name_pattern = r'([A-Z][a-z]+(?:,?\s+[A-Z][a-z]+)+)'
        
        # Find all employees in text
        for match in re.finditer(emp_id_pattern, text, re.IGNORECASE):
            emp_id = match.group(1)
            
            # Look for name near this ID (within 200 chars)
            context_start = max(0, match.start() - 100)
            context_end = min(len(text), match.end() + 100)
            context = text[context_start:context_end]
            
            name_match = re.search(name_pattern, context)
            name = name_match.group(1) if name_match else f"Employee {emp_id}"
            
            employees.append({
                'employee_id': emp_id,
                'employee_name': name,
                'department': ''
            })
        
        # Remove duplicates
        seen = set()
        unique = []
        for emp in employees:
            key = emp['employee_id']
            if key not in seen:
                seen.add(key)
                unique.append(emp)
        
        return unique if unique else [{'employee_id': 'Unknown', 'employee_name': 'Unknown', 'department': ''}]
    
    def _parse_earnings(self, data: Dict, employees: List[Dict]) -> List[Dict]:
        """Parse earnings from extracted data."""
        earnings = []
        lines = data.get('lines', [])
        
        # Pattern for earning lines: "Description $rate hours $amount"
        # Example: "Regular Hourly $18.1900 55.28 $1,005.60"
        earning_pattern = r'([A-Za-z][\w\s]{2,30})\s+\$?([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+\$?([\d,]+\.?\d*)'
        
        for line in lines:
            match = re.search(earning_pattern, line)
            if match:
                desc = match.group(1).strip()
                rate = self._safe_float(match.group(2))
                hours = self._safe_float(match.group(3))
                amount = self._safe_float(match.group(4))
                
                # Map to employee
                emp_id = ""
                emp_name = ""
                for emp in employees:
                    if emp['employee_id'] in line or emp['employee_name'] in line:
                        emp_id = emp['employee_id']
                        emp_name = emp['employee_name']
                        break
                
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
    
    def _parse_taxes(self, data: Dict, employees: List[Dict]) -> List[Dict]:
        """Parse taxes from extracted data."""
        taxes = []
        lines = data.get('lines', [])
        
        # Pattern for tax lines: "Description $wages $amount"
        # Example: "Fed W/H $1,005.60 $62.35"
        tax_pattern = r'([A-Za-z][\w\s/]{2,20})\s+\$?([\d,]+\.?\d*)\s+\$?([\d,]+\.?\d*)'
        
        for line in lines:
            match = re.search(tax_pattern, line)
            if match:
                desc = match.group(1).strip()
                wages = self._safe_float(match.group(2))
                amount = self._safe_float(match.group(3))
                
                # Map to employee
                emp_id = ""
                emp_name = ""
                for emp in employees:
                    if emp['employee_id'] in line or emp['employee_name'] in line:
                        emp_id = emp['employee_id']
                        emp_name = emp['employee_name']
                        break
                
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
    
    def _parse_deductions(self, data: Dict, employees: List[Dict]) -> List[Dict]:
        """Parse deductions from extracted data."""
        deductions = []
        lines = data.get('lines', [])
        
        # Pattern for deduction lines: "Description $amount"
        # Example: "401k-PR 5.00% $261.23"
        deduction_pattern = r'([A-Za-z][\w\s\-()]{2,30})\s+(?:[\d.]+%)?\s*\$?([\d,]+\.?\d*)'
        
        for line in lines:
            match = re.search(deduction_pattern, line)
            if match:
                desc = match.group(1).strip()
                amount = self._safe_float(match.group(2))
                
                # Map to employee
                emp_id = ""
                emp_name = ""
                for emp in employees:
                    if emp['employee_id'] in line or emp['employee_name'] in line:
                        emp_id = emp['employee_id']
                        emp_name = emp['employee_name']
                        break
                
                deductions.append({
                    'employee_id': emp_id,
                    'employee_name': emp_name,
                    'description': desc,
                    'scheduled': 0,
                    'amount': amount,
                    'amount_ytd': amount
                })
        
        return deductions
    
    def _safe_float(self, value: str) -> float:
        """Safely convert string to float."""
        try:
            return float(str(value).replace(',', '').replace('$', ''))
        except (ValueError, AttributeError):
            return 0.0
    
    def _create_excel_tabs(self, structured: Dict) -> Dict[str, pd.DataFrame]:
        """Create 4 Excel tabs from structured data."""
        
        # Employee Summary
        summary_data = []
        for emp in structured['employees']:
            emp_id = emp['employee_id']
            emp_name = emp['employee_name']
            
            emp_earnings = [e for e in structured['earnings'] if e['employee_id'] == emp_id]
            total_earnings = sum(e['amount'] for e in emp_earnings)
            
            emp_taxes = [t for t in structured['taxes'] if t['employee_id'] == emp_id]
            total_taxes = sum(t['amount'] for t in emp_taxes)
            
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
        output_path = output_dir / f"{pdf_name}_parsed_v2_bbox_{timestamp}.xlsx"
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            for tab_name, df in tabs.items():
                df.to_excel(writer, sheet_name=tab_name, index=False)
        
        return str(output_path)
    
    def _calculate_accuracy(self, structured: Dict, tabs: Dict[str, pd.DataFrame]) -> float:
        """Calculate accuracy score."""
        score = 0
        
        # Employees found (30 points)
        if structured['employees']:
            score += 20
        if len(structured['employees']) >= 2:
            score += 10
        
        # Data extracted (40 points)
        if structured['earnings']:
            score += 15
        if structured['taxes']:
            score += 15
        if structured['deductions']:
            score += 10
        
        # Real data (30 points)
        emp_summary = tabs['Employee Summary']
        if not emp_summary.empty:
            if emp_summary['Total Earnings'].sum() > 0:
                score += 15
            if emp_summary['Total Taxes'].sum() > 0:
                score += 10
            if emp_summary['Total Deductions'].sum() > 0:
                score += 5
        
        return min(score, 100.0)


# Convenience function
def parse_pdf_intelligent_v2(pdf_path: str, output_dir: str = '/data/parsed_registers') -> Dict[str, Any]:
    """Parse PDF using V2 bbox-based approach."""
    orchestrator = IntelligentParserOrchestratorV2()
    return orchestrator.parse(pdf_path, output_dir)
