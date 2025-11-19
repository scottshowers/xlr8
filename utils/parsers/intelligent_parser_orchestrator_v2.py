"""
Intelligent Parser Orchestrator V2 - Enhanced Section-Based Approach
Uses multi-method extraction per section for optimal accuracy
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)

from .section_detector import SectionDetector
from .multi_method_extractor import MultiMethodExtractor

# Fallback to v1 orchestrator if available
try:
    from .intelligent_parser_orchestrator import IntelligentParserOrchestrator as OrchestratorV1
    V1_AVAILABLE = True
except ImportError:
    V1_AVAILABLE = False
    logger.warning("V1 orchestrator not available")


class IntelligentParserOrchestratorV2:
    """
    Enhanced orchestrator that:
    1. Detects 4 sections (Employee Info, Earnings, Taxes, Deductions)
    2. Tries ALL methods on EACH section
    3. Picks best method per section
    4. Combines results into 4-tab Excel
    5. Falls back to V1 if section detection fails
    """
    
    def __init__(self, custom_parsers_dir: str = "/data/custom_parsers"):
        """Initialize enhanced orchestrator."""
        self.custom_parsers_dir = Path(custom_parsers_dir)
        self.custom_parsers_dir.mkdir(parents=True, exist_ok=True)
        
        self.section_detector = SectionDetector()
        self.extractor = MultiMethodExtractor()
        
        # Load V1 orchestrator as fallback
        self.v1_orchestrator = None
        if V1_AVAILABLE:
            try:
                self.v1_orchestrator = OrchestratorV1(custom_parsers_dir=str(self.custom_parsers_dir))
                logger.info("V1 orchestrator loaded as fallback")
            except Exception as e:
                logger.warning(f"Could not load V1 orchestrator: {str(e)}")
        
        logger.info("V2 Enhanced Orchestrator initialized")
        logger.info(f"Available methods: {list(self.extractor.available_methods.keys())}")
    
    def parse(self, pdf_path: str, output_dir: str = '/data/parsed_registers',
              force_v2: bool = False) -> Dict[str, Any]:
        """
        Parse PDF using section-based multi-method approach.
        
        Args:
            pdf_path: Path to PDF file
            output_dir: Directory for Excel output
            force_v2: Skip V1 fallback, always use V2
            
        Returns:
            Dict with status, output_path, accuracy, method_per_section, etc.
        """
        result = {
            'status': 'processing',
            'version': 'v2',
            'pdf_path': pdf_path,
            'methods_used': {},
            'sections_found': {},
            'accuracy_per_section': {},
            'overall_accuracy': 0,
            'employee_count': 0,
            'started_at': datetime.now().isoformat()
        }
        
        try:
            logger.info(f"=== V2 Enhanced Parser Starting ===")
            logger.info(f"PDF: {pdf_path}")
            
            # Step 1: Detect sections
            logger.info("Step 1: Detecting sections...")
            sections = self.section_detector.detect_sections(pdf_path)
            
            sections_found = sum(1 for s in sections.values() if s is not None)
            result['sections_found'] = {k: (v is not None) for k, v in sections.items()}
            
            logger.info(f"Found {sections_found}/4 sections")
            
            # If less than 2 sections found, fall back to V1
            if sections_found < 2 and not force_v2:
                logger.info("Too few sections detected, falling back to V1 orchestrator")
                if self.v1_orchestrator:
                    v1_result = self.v1_orchestrator.parse(pdf_path)
                    v1_result['version'] = 'v1_fallback'
                    v1_result['fallback_reason'] = 'section_detection_failed'
                    return v1_result
                else:
                    result['status'] = 'error'
                    result['message'] = 'Section detection failed and V1 fallback unavailable'
                    return result
            
            # Step 2: Extract each section with all methods
            logger.info("Step 2: Extracting sections with all methods...")
            section_data = {}
            
            for section_type, section_info in sections.items():
                if not section_info:
                    logger.info(f"  {section_type}: Not found, skipping")
                    continue
                
                logger.info(f"  {section_type}: Testing all methods...")
                
                # Try all methods on this section
                all_results = self.extractor.extract_all_methods(
                    pdf_path,
                    section_bbox=section_info.get('bbox')
                )
                
                # Pick best method for this section
                best_method, best_result = self.extractor.get_best_method(
                    all_results,
                    section_type
                )
                
                if best_method:
                    accuracy = self.extractor.score_extraction(best_result, section_type)
                    logger.info(f"    Best: {best_method} ({accuracy:.1f}%)")
                    
                    section_data[section_type] = {
                        'method': best_method,
                        'data': best_result,
                        'accuracy': accuracy
                    }
                    
                    result['methods_used'][section_type] = best_method
                    result['accuracy_per_section'][section_type] = accuracy
                else:
                    logger.warning(f"    All methods failed for {section_type}")
            
            # Step 3: Convert to structured data
            logger.info("Step 3: Building structured data...")
            structured_data = self._structure_section_data(section_data)
            
            # Step 4: Create 4-tab Excel
            logger.info("Step 4: Creating Excel output...")
            tabs = self._create_four_tabs(structured_data)
            
            # Step 5: Write Excel
            output_path = self._write_excel(tabs, pdf_path, output_dir)
            
            # Step 6: Calculate overall accuracy
            overall_accuracy = self._calculate_overall_accuracy(result['accuracy_per_section'], tabs)
            
            result['status'] = 'success'
            result['output_path'] = output_path
            result['overall_accuracy'] = overall_accuracy
            result['employee_count'] = len(tabs['Employee Summary']) if not tabs['Employee Summary'].empty else 0
            result['tabs'] = {k: len(v) for k, v in tabs.items()}
            result['completed_at'] = datetime.now().isoformat()
            
            logger.info(f"=== V2 Enhanced Parser Complete ===")
            logger.info(f"Overall Accuracy: {overall_accuracy:.1f}%")
            logger.info(f"Employees: {result['employee_count']}")
            logger.info(f"Output: {output_path}")
            
            return result
            
        except Exception as e:
            logger.error(f"V2 parser error: {str(e)}", exc_info=True)
            
            # Try V1 fallback
            if not force_v2 and self.v1_orchestrator:
                logger.info("V2 failed, attempting V1 fallback...")
                try:
                    v1_result = self.v1_orchestrator.parse(pdf_path)
                    v1_result['version'] = 'v1_fallback'
                    v1_result['fallback_reason'] = f'v2_error: {str(e)}'
                    return v1_result
                except Exception as v1_error:
                    logger.error(f"V1 fallback also failed: {str(v1_error)}")
            
            result['status'] = 'error'
            result['message'] = str(e)
            return result
    
    def _structure_section_data(self, section_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert raw extracted data into structured format.
        """
        import re
        
        structured = {
            'employees': [],
            'earnings': [],
            'taxes': [],
            'deductions': []
        }
        
        # First, extract all employees
        if 'employee_info' in section_data:
            employee_data = section_data['employee_info']['data']
            structured['employees'] = self._parse_employee_info(employee_data)
        
        # Get combined text from all sections
        all_text = ""
        for section_type in ['employee_info', 'earnings', 'taxes', 'deductions']:
            if section_type in section_data:
                data = section_data[section_type]['data']
                if data.get('text'):
                    all_text += data['text'] + "\n"
                elif data.get('lines'):
                    all_text += '\n'.join(data['lines']) + "\n"
        
        # Split text by employee for proper attribution
        if structured['employees'] and len(structured['employees']) > 1:
            # Multiple employees - split data per employee
            employee_blocks = self._split_by_employees(all_text, structured['employees'])
            
            for emp_block, emp_info in zip(employee_blocks, structured['employees']):
                # Parse earnings for this employee
                earnings_data = {'text': emp_block, 'lines': emp_block.split('\n')}
                emp_earnings = self._parse_earnings(earnings_data)
                for earning in emp_earnings:
                    earning['employee_id'] = emp_info['employee_id']
                    earning['employee_name'] = emp_info['name']
                structured['earnings'].extend(emp_earnings)
                
                # Parse taxes for this employee  
                taxes_data = {'text': emp_block, 'lines': emp_block.split('\n')}
                emp_taxes = self._parse_taxes(taxes_data)
                for tax in emp_taxes:
                    tax['employee_id'] = emp_info['employee_id']
                    tax['employee_name'] = emp_info['name']
                structured['taxes'].extend(emp_taxes)
                
                # Parse deductions for this employee
                deductions_data = {'text': emp_block, 'lines': emp_block.split('\n')}
                emp_deductions = self._parse_deductions(deductions_data)
                for deduction in emp_deductions:
                    deduction['employee_id'] = emp_info['employee_id']
                    deduction['employee_name'] = emp_info['name']
                structured['deductions'].extend(emp_deductions)
        else:
            # Single employee - parse globally
            if 'earnings' in section_data:
                earnings_data = section_data['earnings']['data']
                structured['earnings'] = self._parse_earnings(earnings_data)
            
            if 'taxes' in section_data:
                taxes_data = section_data['taxes']['data']
                structured['taxes'] = self._parse_taxes(taxes_data)
            
            if 'deductions' in section_data:
                deductions_data = section_data['deductions']['data']
                structured['deductions'] = self._parse_deductions(deductions_data)
            
            # Add employee info to each item
            if structured['employees']:
                emp_id = structured['employees'][0]['employee_id']
                emp_name = structured['employees'][0]['name']
                for earning in structured['earnings']:
                    earning['employee_id'] = emp_id
                    earning['employee_name'] = emp_name
                for tax in structured['taxes']:
                    tax['employee_id'] = emp_id
                    tax['employee_name'] = emp_name
                for deduction in structured['deductions']:
                    deduction['employee_id'] = emp_id
                    deduction['employee_name'] = emp_name
        
        return structured
    
    def _split_by_employees(self, text: str, employees: List[Dict]) -> List[str]:
        """Split text into blocks, one per employee."""
        import re
        
        if not employees or len(employees) < 2:
            return [text]
        
        blocks = []
        
        # Build pattern that splits at each employee's ID
        for i, emp in enumerate(employees):
            emp_id = emp['employee_id']
            
            if i < len(employees) - 1:
                # Not the last employee - find from this ID to next ID
                next_id = employees[i + 1]['employee_id']
                pattern = rf'Emp\s*#?\s*:?\s*{emp_id}(.*?)(?=Emp\s*#?\s*:?\s*{next_id})'
                match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
                if match:
                    blocks.append(match.group(0))
                else:
                    blocks.append("")
            else:
                # Last employee - from this ID to end
                pattern = rf'Emp\s*#?\s*:?\s*{emp_id}(.*?)$'
                match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
                if match:
                    blocks.append(match.group(0))
                else:
                    blocks.append("")
        
        return blocks
    
    def _parse_employee_info(self, data: Dict[str, Any]) -> List[Dict]:
        """Parse employee info from extracted data - handles multiple employees."""
        import re
        employees = []
        
        # Get all text content
        text_content = ""
        if data.get('lines'):
            text_content = '\n'.join(data['lines'])
        elif data.get('text'):
            text_content = data['text']
        
        # Pattern that captures name + employee ID together
        # Format: "FirstName LastName\nEmp #: 12345"
        emp_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s*[\n\r]+\s*Emp\s*#?\s*:?\s*(\d+)'
        matches = re.findall(emp_pattern, text_content, flags=re.IGNORECASE | re.MULTILINE)
        
        if matches:
            # Found employees with name+ID pattern
            for name, emp_id in matches:
                emp = {
                    'employee_id': emp_id.strip(),
                    'name': name.strip(),
                    'department': ''
                }
                
                # Try to find department for this employee
                # Look for "Dept:" after this employee ID
                dept_pattern = rf'Emp\s*#?\s*:?\s*{emp_id}.*?Dept\s*:?\s*([^\n]+)'
                dept_match = re.search(dept_pattern, text_content, flags=re.IGNORECASE | re.DOTALL)
                if dept_match:
                    emp['department'] = dept_match.group(1).strip()
                
                employees.append(emp)
        else:
            # Fallback: try to find employee IDs without names
            emp_id_matches = re.findall(r'Emp\s*#?\s*:?\s*(\d+)', text_content, flags=re.IGNORECASE)
            for emp_id in emp_id_matches:
                employees.append({
                    'employee_id': emp_id,
                    'name': '',
                    'department': ''
                })
        
        return employees if employees else [{'employee_id': 'Unknown', 'name': 'Unknown', 'department': ''}]
    
    def _parse_earnings(self, data: Dict[str, Any]) -> List[Dict]:
        """Parse earnings from extracted data using regex patterns."""
        import re
        earnings = []
        
        # Get all text content
        text_content = ""
        if data.get('lines'):
            text_content = '\n'.join(data['lines'])
        elif data.get('text'):
            text_content = data['text']
        
        if not text_content:
            return earnings
        
        # Pattern for earnings lines like: "Regular Hourly $18.1900 55.28 $1,005.60 748.73 $13,538.38"
        # Format: Description Rate Hours Amount HoursYTD AmountYTD
        lines = text_content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 10:
                continue
            
            # Skip header and total lines
            if any(word in line.lower() for word in ['description', 'rate', 'hours', 'amount', 'ytd', 'total', 'reg total', 'emp total']):
                continue
            
            # Skip employee info lines
            if re.match(r'^(Emp\s*#|Dept|Hire|Term|SSN|Status|Frequency|Type|Rate|Federal|State|Res|Transit)', line, re.IGNORECASE):
                continue
            
            # Skip lines that are just employee names (capitalized name with no numbers)
            if re.match(r'^[A-Z][a-z]+\s+[A-Z][a-z]+\s*$', line):
                continue
            
            # Look for lines with dollar amounts (likely earnings)
            if '$' in line or re.search(r'\d+\.\d{2}', line):
                # Extract all numbers from the line
                numbers = re.findall(r'[\d,]+\.?\d*', line)
                
                # Extract description (text before first number or dollar sign)
                desc_match = re.match(r'^([A-Za-z\s\-]+?)(?:\s+\$|\s+\d)', line)
                description = desc_match.group(1).strip() if desc_match else ''
                
                if description and numbers and len(numbers) >= 2:
                    # Clean numbers
                    cleaned_nums = [self._safe_float(n) for n in numbers]
                    
                    earning = {
                        'description': description,
                        'rate': cleaned_nums[0] if len(cleaned_nums) > 0 else 0,
                        'hours': cleaned_nums[1] if len(cleaned_nums) > 1 else 0,
                        'amount': cleaned_nums[2] if len(cleaned_nums) > 2 else 0,
                        'hours_ytd': cleaned_nums[3] if len(cleaned_nums) > 3 else 0,
                        'amount_ytd': cleaned_nums[4] if len(cleaned_nums) > 4 else 0
                    }
                    earnings.append(earning)
        
        return earnings
    
    def _parse_taxes(self, data: Dict[str, Any]) -> List[Dict]:
        """Parse taxes from extracted data using regex patterns."""
        import re
        taxes = []
        
        # Get all text content
        text_content = ""
        if data.get('lines'):
            text_content = '\n'.join(data['lines'])
        elif data.get('text'):
            text_content = data['text']
        
        if not text_content:
            return taxes
        
        # Pattern for tax lines like: "Fed W/H $1,005.60 $62.46 $14,559.63 $902.70"
        # Format: Description Wages Amount WagesYTD AmountYTD
        lines = text_content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 10:
                continue
            
            # Skip header and total lines
            if any(word in line.lower() for word in ['description', 'wages', 'amount', 'ytd', 'total', 'emp total', 'er total', 'memo total']):
                continue
            
            # Skip employee info lines
            if re.match(r'^(Emp\s*#|Dept|Hire|Term|SSN|Status|Frequency|Type|Rate|Federal|State|Res|Transit)', line, re.IGNORECASE):
                continue
            
            # Skip lines that are just employee names
            if re.match(r'^[A-Z][a-z]+\s+[A-Z][a-z]+\s*$', line):
                continue
            
            # Look for tax-related keywords
            if re.search(r'(?:fed|fica|state|w/h|mwt|ut|er|ee|medicare|social|comp|drt)', line, re.IGNORECASE):
                # Extract all numbers from the line
                numbers = re.findall(r'[\d,]+\.?\d*', line)
                
                # Extract description (text before first dollar sign or number)
                desc_match = re.match(r'^([A-Za-z\s/\-]+?)(?:\s+\$|\s+\d)', line)
                description = desc_match.group(1).strip() if desc_match else ''
                
                if description and numbers:
                    # Clean numbers
                    cleaned_nums = [self._safe_float(n) for n in numbers]
                    
                    tax = {
                        'description': description,
                        'wages': cleaned_nums[0] if len(cleaned_nums) > 0 else 0,
                        'amount': cleaned_nums[1] if len(cleaned_nums) > 1 else 0,
                        'wages_ytd': cleaned_nums[2] if len(cleaned_nums) > 2 else 0,
                        'amount_ytd': cleaned_nums[3] if len(cleaned_nums) > 3 else 0
                    }
                    taxes.append(tax)
        
        return taxes
    
    def _parse_deductions(self, data: Dict[str, Any]) -> List[Dict]:
        """Parse deductions from extracted data using regex patterns."""
        import re
        deductions = []
        
        # Get all text content
        text_content = ""
        if data.get('lines'):
            text_content = '\n'.join(data['lines'])
        elif data.get('text'):
            text_content = data['text']
        
        if not text_content:
            return deductions
        
        # Pattern for deduction lines like: "Medical Pre Tax $403.81 $403.81 $6,057.15"
        # Format: Description Scheduled Amount AmountYTD
        lines = text_content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 10:
                continue
            
            # Skip header and total lines
            if any(word in line.lower() for word in ['description', 'scheduled', 'amount', 'ytd', 'total', 'pre total', 'post total', 'reim total', 'memo total', 'company paid']):
                continue
            
            # Skip employee info lines
            if re.match(r'^(Emp\s*#|Dept|Hire|Term|SSN|Status|Frequency|Type|Rate|Federal|State|Res|Transit)', line, re.IGNORECASE):
                continue
            
            # Skip lines that are just employee names
            if re.match(r'^[A-Z][a-z]+\s+[A-Z][a-z]+\s*$', line):
                continue
            
            # Skip PTO/vacation balance lines
            if re.search(r'(hours|balance|accrued)\s*$', line, re.IGNORECASE):
                continue
            
            # Look for lines with dollar amounts (likely deductions)
            if '$' in line or re.search(r'\d+\.\d{2}', line):
                # Extract all numbers from the line
                numbers = re.findall(r'[\d,]+\.?\d*', line)
                
                # Extract description (text before first dollar sign or number)
                desc_match = re.match(r'^([A-Za-z\s\-()]+?)(?:\s+\$|\s+\d)', line)
                description = desc_match.group(1).strip() if desc_match else ''
                
                if description and numbers:
                    # Clean numbers
                    cleaned_nums = [self._safe_float(n) for n in numbers]
                    
                    # Handle special case for percentage-based deductions (like "401k-PR 5.00%")
                    scheduled = ''
                    if '%' in line:
                        pct_match = re.search(r'([\d.]+)%', line)
                        if pct_match:
                            scheduled = pct_match.group(1) + '%'
                            # Adjust description to include percentage
                            description = re.sub(r'\s+[\d.]+%', '', description).strip()
                    
                    deduction = {
                        'description': description,
                        'scheduled': scheduled if scheduled else (cleaned_nums[0] if len(cleaned_nums) > 0 else 0),
                        'amount': cleaned_nums[1] if len(cleaned_nums) > 1 else (cleaned_nums[0] if len(cleaned_nums) > 0 else 0),
                        'amount_ytd': cleaned_nums[2] if len(cleaned_nums) > 2 else (cleaned_nums[1] if len(cleaned_nums) > 1 else 0)
                    }
                    deductions.append(deduction)
        
        return deductions
    
    def _safe_float(self, value: Any) -> float:
        """Safely convert value to float."""
        if isinstance(value, (int, float)):
            return float(value)
        
        if not value:
            return 0.0
        
        import re
        # Remove non-numeric characters except decimal and minus
        cleaned = re.sub(r'[^\d.-]', '', str(value))
        
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return 0.0
    
    def _create_four_tabs(self, structured_data: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
        """Create 4-tab structure from structured data."""
        
        employees = structured_data.get('employees', [])
        earnings = structured_data.get('earnings', [])
        taxes = structured_data.get('taxes', [])
        deductions = structured_data.get('deductions', [])
        
        # Tab 1: Employee Summary
        summary_data = []
        for emp in employees:
            emp_id = emp.get('employee_id', '')
            
            # Calculate totals for THIS employee only
            emp_earnings = sum(e.get('amount', 0) for e in earnings if e.get('employee_id') == emp_id)
            emp_taxes = sum(t.get('amount', 0) for t in taxes if t.get('employee_id') == emp_id)
            emp_deductions = sum(d.get('amount', 0) for d in deductions if d.get('employee_id') == emp_id)
            
            summary = {
                'Employee ID': emp_id,
                'Name': emp.get('name', ''),
                'Department': emp.get('department', ''),
                'Total Earnings': emp_earnings,
                'Total Taxes': emp_taxes,
                'Total Deductions': emp_deductions,
                'Net Pay': emp_earnings - emp_taxes - emp_deductions
            }
            summary_data.append(summary)
        
        # Tab 2: Earnings (already has employee_id from parsing)
        earnings_data = []
        for earning in earnings:
            earnings_data.append({
                'Employee ID': earning.get('employee_id', ''),
                'Name': earning.get('employee_name', ''),
                'Description': earning.get('description', ''),
                'Hours': earning.get('hours', 0),
                'Rate': earning.get('rate', 0),
                'Amount': earning.get('amount', 0)
            })
        
        # Tab 3: Taxes (already has employee_id from parsing)
        taxes_data = []
        for tax in taxes:
            taxes_data.append({
                'Employee ID': tax.get('employee_id', ''),
                'Name': tax.get('employee_name', ''),
                'Description': tax.get('description', ''),
                'Amount': tax.get('amount', 0)
            })
        
        # Tab 4: Deductions (already has employee_id from parsing)
        deductions_data = []
        for deduction in deductions:
            deductions_data.append({
                'Employee ID': deduction.get('employee_id', ''),
                'Name': deduction.get('employee_name', ''),
                'Description': deduction.get('description', ''),
                'Amount': deduction.get('amount', 0)
            })
        
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
        output_path = output_dir / f"{pdf_name}_parsed_v2_{timestamp}.xlsx"
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            for tab_name, df in tabs.items():
                df.to_excel(writer, sheet_name=tab_name, index=False)
        
        logger.info(f"Excel written: {output_path}")
        return str(output_path)
    
    def _calculate_overall_accuracy(self, section_accuracies: Dict[str, float],
                                   tabs: Dict[str, pd.DataFrame]) -> float:
        """Calculate overall accuracy from section accuracies and data quality."""
        if not section_accuracies:
            return 0.0
        
        # Base score from section accuracies
        avg_accuracy = sum(section_accuracies.values()) / len(section_accuracies)
        
        # Check if we actually have meaningful data (not just empty rows)
        has_real_data = False
        
        # Check Employee Summary for actual data
        if not tabs['Employee Summary'].empty:
            emp_sum = tabs['Employee Summary']
            # Check if any numeric columns have non-zero values
            for col in ['Total Earnings', 'Total Taxes', 'Total Deductions', 'Net Pay']:
                if col in emp_sum.columns and emp_sum[col].sum() != 0:
                    has_real_data = True
                    break
        
        # If no real data found, cap accuracy at 20%
        if not has_real_data:
            return min(avg_accuracy * 0.2, 20.0)
        
        # Bonus for having data in all tabs
        tabs_with_data = sum(1 for df in tabs.values() if not df.empty and len(df) > 0)
        completeness_bonus = (tabs_with_data / 4.0) * 10
        
        # Bonus for multiple employees
        employee_count = len(tabs['Employee Summary']) if not tabs['Employee Summary'].empty else 0
        if employee_count >= 2:
            completeness_bonus += 5
        
        # Check earnings/taxes/deductions have actual line items
        detail_items = len(tabs['Earnings']) + len(tabs['Taxes']) + len(tabs['Deductions'])
        if detail_items > 0:
            completeness_bonus += 5
        
        overall = min(avg_accuracy + completeness_bonus, 100.0)
        return overall


def parse_pdf_intelligent_v2(pdf_path: str, output_dir: str = '/data/parsed_registers',
                             force_v2: bool = False) -> Dict[str, Any]:
    """
    Convenience function for V2 parsing.
    """
    orchestrator = IntelligentParserOrchestratorV2()
    return orchestrator.parse(pdf_path, output_dir, force_v2=force_v2)
