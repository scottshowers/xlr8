"""
Strategy Library - ADAPTIVE EXTRACTION
Truly vendor-agnostic strategies that analyze content, not structure
"""

import logging
import re
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger(__name__)

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    logger.warning("pdfplumber not available - table strategies won't work")


class ExtractionStrategy:
    """Base class for extraction strategies."""
    
    def __init__(self):
        self.name = "base_strategy"
        self.description = "Base extraction strategy"
        
        # Universal keyword sets (vendor-agnostic)
        self.EARNING_KEYWORDS = [
            'regular', 'hourly', 'salary', 'overtime', 'ot', 'double time', 'dt',
            'vacation', 'holiday', 'bonus', 'commission', 'sick', 'pto', 'personal',
            'bereavement', 'jury', 'tips', 'premium', 'shift', 'differential'
        ]
        
        self.TAX_KEYWORDS = [
            'federal', 'fed', 'fica', 'medicare', 'med', 'social security', 'ss', 'oasdi',
            'state', 'local', 'city', 'county', 'sdi', 'sui', 'fui', 'futa', 'suta',
            'withholding', 'w/h', 'tax', 'employee tax', 'er tax', 'ee tax'
        ]
        
        self.DEDUCTION_KEYWORDS = [
            'medical', 'dental', 'vision', 'health', 'insurance', 'life', 'ad&d',
            '401k', '403b', 'roth', 'retirement', 'pension', 'savings',
            'hsa', 'fsa', 'dependent', 'garnish', 'child support', 'union', 'dues',
            'parking', 'transit', 'cafeteria', 'charity', 'donation'
        ]
        
        # Blacklist: Terms that are NEVER employee names (universal)
        self.NAME_BLACKLIST = [
            'net pay', 'gross pay', 'gross', 'net', 'total', 'subtotal', 'totals',
            'dept code', 'department', 'code', 'profile', 'tax profile',
            'earnings', 'taxes', 'deductions', 'ytd', 'current', 'payroll',
            'summary', 'register', 'report', 'page', 'date', 'period',
            'employee', 'rate', 'amount', 'hours', 'description',
            # Job titles (not people)
            'director', 'manager', 'supervisor', 'coordinator', 'assistant',
            'aide', 'clerk', 'specialist', 'administrator', 'officer',
            'technician', 'analyst', 'representative', 'receptionist',
            # Departments (not people)
            'nursing', 'dietary', 'maintenance', 'housekeeping', 'laundry',
            'activities', 'administration', 'admin', 'therapy', 'rehab',
            # Common terms
            'nonresident', 'resident', 'voucher', 'allowance', 'reimbursement'
        ]
        
        # ID Blacklist: Numbers that are NEVER employee IDs
        self.ID_BLACKLIST_PATTERNS = [
            r'^20\d{2}$',  # Years: 2024, 2025, etc.
            r'^19\d{2}$',  # Years: 1990-1999
            r'^[1-9]00$',  # Round numbers: 100, 200, 300, etc.
            r'^[1-9]000$', # Round numbers: 1000, 2000, etc.
        ]
    
    def can_handle(self, pdf_path: str, vendor: str = None) -> bool:
        """Check if this strategy can handle the PDF."""
        return False
    
    def extract(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract data from PDF.
        
        Returns:
            {
                'employees': [...],
                'earnings': [...],
                'taxes': [...],
                'deductions': [...]
            }
        """
        raise NotImplementedError
    
    def _is_earning(self, text: str) -> bool:
        """Check if text describes an earning."""
        text_lower = text.lower()
        return any(kw in text_lower for kw in self.EARNING_KEYWORDS)
    
    def _is_tax(self, text: str) -> bool:
        """Check if text describes a tax."""
        text_lower = text.lower()
        return any(kw in text_lower for kw in self.TAX_KEYWORDS)
    
    def _is_deduction(self, text: str) -> bool:
        """Check if text describes a deduction."""
        text_lower = text.lower()
        return any(kw in text_lower for kw in self.DEDUCTION_KEYWORDS)
    
    def _extract_amounts(self, text: str) -> List[float]:
        """Extract all monetary amounts from text."""
        # Match $1,234.56 or 1234.56 or 1,234.56
        amounts = []
        for match in re.finditer(r'\$?\s*([\d,]+\.\d{2})', text):
            try:
                amount = float(match.group(1).replace(',', ''))
                amounts.append(amount)
            except ValueError:
                continue
        return amounts
    
    def _clean_description(self, text: str) -> str:
        """Clean up description text."""
        # Remove extra whitespace
        text = ' '.join(text.split())
        # Remove leading/trailing punctuation
        text = text.strip('.,;:- ')
        return text[:100]  # Limit length
    
    def _is_valid_employee_name(self, name: str) -> bool:
        """
        Validate if name is actually a person (not accounting term, job title, etc.)
        
        Returns True if name looks like a real person.
        """
        if not name or len(name.strip()) < 3:
            return False
        
        name_lower = name.lower().strip()
        
        # Check against blacklist
        for blacklisted_term in self.NAME_BLACKLIST:
            if blacklisted_term in name_lower:
                return False
        
        # Must have at least 2 words (FirstName LastName)
        words = name.split()
        if len(words) < 2:
            return False
        
        # Each word should start with capital letter (proper name format)
        for word in words:
            if not word[0].isupper():
                return False
        
        # Should not be all caps (likely a header/label)
        if name.isupper():
            return False
        
        # Should contain letters (not just numbers/punctuation)
        if not any(c.isalpha() for c in name):
            return False
        
        return True
    
    def _is_valid_employee_id(self, emp_id: str) -> bool:
        """
        Validate if ID is actually an employee ID (not year, dept code, etc.)
        
        Returns True if ID looks like a real employee ID.
        """
        if not emp_id or not emp_id.strip():
            return False
        
        emp_id = emp_id.strip()
        
        # Must be numeric
        if not emp_id.isdigit():
            return False
        
        # Check against blacklist patterns
        for pattern in self.ID_BLACKLIST_PATTERNS:
            if re.match(pattern, emp_id):
                return False
        
        # Employee IDs are typically 4-7 digits (not 1-3, not 8+)
        if len(emp_id) < 4 or len(emp_id) > 7:
            return False
        
        return True


class TableBasedStrategy(ExtractionStrategy):
    """
    ADAPTIVE Table-based extraction - analyzes table CONTENT, not structure.
    Works on ANY table layout by identifying columns through content analysis.
    """
    
    def __init__(self):
        super().__init__()
        self.name = "table_based"
        self.description = "Adaptive table extraction with content-based column detection"
    
    def can_handle(self, pdf_path: str, vendor: str = None) -> bool:
        """Check if PDF has extractable tables."""
        if not PDFPLUMBER_AVAILABLE:
            return False
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages[:2]:  # Check first 2 pages
                    tables = page.extract_tables()
                    if tables and len(tables) > 0:
                        # Check if table has meaningful data
                        table = tables[0]
                        if len(table) > 3 and len(table[0]) > 2:
                            return True
            return False
        except Exception as e:
            logger.error(f"Error checking table availability: {e}")
            return False
    
    def extract(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract using adaptive table analysis.
        
        Process:
        1. Extract all tables from PDF
        2. Analyze column content to identify types
        3. Find employees using pattern matching
        4. Extract and categorize line items
        """
        logger.info("TableBasedStrategy: Starting adaptive extraction")
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                all_tables = []
                
                # Extract all tables from all pages
                for page_num, page in enumerate(pdf.pages):
                    tables = page.extract_tables()
                    for table_num, table in enumerate(tables):
                        if table and len(table) > 1:
                            all_tables.append({
                                'page': page_num + 1,
                                'table_num': table_num + 1,
                                'data': table
                            })
                
                logger.info(f"Found {len(all_tables)} tables across {len(pdf.pages)} pages")
                
                if not all_tables:
                    return {'employees': [], 'earnings': [], 'taxes': [], 'deductions': []}
                
                # Try to extract from all tables
                employees = []
                earnings = []
                taxes = []
                deductions = []
                
                for table_info in all_tables:
                    table = table_info['data']
                    
                    # Analyze this table
                    result = self._extract_from_table(table)
                    
                    employees.extend(result['employees'])
                    earnings.extend(result['earnings'])
                    taxes.extend(result['taxes'])
                    deductions.extend(result['deductions'])
                
                # Deduplicate employees
                employees = self._deduplicate_employees(employees)
                
                logger.info(f"Extracted: {len(employees)} employees, {len(earnings)} earnings, "
                          f"{len(taxes)} taxes, {len(deductions)} deductions")
                
                return {
                    'employees': employees,
                    'earnings': earnings,
                    'taxes': taxes,
                    'deductions': deductions
                }
        
        except Exception as e:
            logger.error(f"TableBasedStrategy extraction failed: {e}", exc_info=True)
            return {'employees': [], 'earnings': [], 'taxes': [], 'deductions': []}
    
    def _extract_from_table(self, table: List[List]) -> Dict[str, List]:
        """Extract data from a single table using content analysis."""
        
        # Analyze columns
        column_types = self._analyze_columns(table)
        
        # Find employee ID and name columns
        id_col = column_types.get('employee_id')
        name_col = column_types.get('employee_name')
        desc_col = column_types.get('description')
        amount_cols = column_types.get('amounts', [])
        
        employees = []
        earnings = []
        taxes = []
        deductions = []
        
        current_employee = None
        
        # Process each row
        for row_idx, row in enumerate(table):
            if row_idx == 0:
                continue  # Skip header row
            
            if not row or all(cell is None or str(cell).strip() == '' for cell in row):
                continue  # Skip empty rows
            
            # Try to find employee in this row
            emp = self._find_employee_in_row(row, id_col, name_col)
            if emp:
                employees.append(emp)
                current_employee = emp
            
            # Try to find line item in this row
            if desc_col is not None and amount_cols:
                line_item = self._extract_line_item(row, desc_col, amount_cols, current_employee)
                
                if line_item:
                    # Categorize
                    if self._is_earning(line_item['description']):
                        earnings.append(line_item)
                    elif self._is_tax(line_item['description']):
                        taxes.append(line_item)
                    elif self._is_deduction(line_item['description']):
                        deductions.append(line_item)
        
        return {
            'employees': employees,
            'earnings': earnings,
            'taxes': taxes,
            'deductions': deductions
        }
    
    def _analyze_columns(self, table: List[List]) -> Dict[str, Any]:
        """
        Analyze table columns to identify what each contains.
        Returns column indices for different data types.
        """
        if len(table) < 2:
            return {}
        
        column_types = {
            'employee_id': None,
            'employee_name': None,
            'description': None,
            'amounts': []
        }
        
        header_row = table[0] if table else []
        sample_rows = table[1:min(6, len(table))]  # Look at first 5 data rows
        
        for col_idx in range(len(header_row) if header_row else 0):
            header = str(header_row[col_idx] or '').lower()
            
            # Check header for clues
            if any(kw in header for kw in ['emp', 'id', 'number', 'badge']):
                # Check if this column contains ID patterns
                if self._column_has_ids(table, col_idx):
                    column_types['employee_id'] = col_idx
                    continue
            
            if any(kw in header for kw in ['name', 'employee name', 'emp name']):
                column_types['employee_name'] = col_idx
                continue
            
            if any(kw in header for kw in ['description', 'desc', 'type', 'earning', 'deduction', 'tax']):
                column_types['description'] = col_idx
                continue
            
            if any(kw in header for kw in ['amount', 'current', 'total', 'gross', 'net', '$']):
                column_types['amounts'].append(col_idx)
                continue
            
            # If no header, analyze content
            if not header or header.strip() == '':
                # Check if column contains IDs
                if self._column_has_ids(table, col_idx):
                    column_types['employee_id'] = col_idx
                # Check if column contains names
                elif self._column_has_names(table, col_idx):
                    column_types['employee_name'] = col_idx
                # Check if column contains amounts
                elif self._column_has_amounts(table, col_idx):
                    column_types['amounts'].append(col_idx)
                # Check if column has descriptions
                elif self._column_has_descriptions(table, col_idx):
                    column_types['description'] = col_idx
        
        return column_types
    
    def _column_has_ids(self, table: List[List], col_idx: int) -> bool:
        """Check if column contains valid employee IDs."""
        valid_id_count = 0
        for row in table[1:6]:  # Check first 5 rows
            if col_idx < len(row):
                cell = str(row[col_idx] or '').strip()
                if cell and self._is_valid_employee_id(cell):
                    valid_id_count += 1
        return valid_id_count >= 2
    
    def _column_has_names(self, table: List[List], col_idx: int) -> bool:
        """Check if column contains valid employee names."""
        valid_name_count = 0
        for row in table[1:6]:
            if col_idx < len(row):
                cell = str(row[col_idx] or '').strip()
                if cell and self._is_valid_employee_name(cell):
                    valid_name_count += 1
        return valid_name_count >= 2
    
    def _column_has_amounts(self, table: List[List], col_idx: int) -> bool:
        """Check if column contains monetary amounts."""
        amount_count = 0
        for row in table[1:6]:
            if col_idx < len(row):
                cell = str(row[col_idx] or '')
                if re.search(r'\$?\s*[\d,]+\.\d{2}', cell):
                    amount_count += 1
        return amount_count >= 2
    
    def _column_has_descriptions(self, table: List[List], col_idx: int) -> bool:
        """Check if column contains text descriptions."""
        desc_count = 0
        for row in table[1:6]:
            if col_idx < len(row):
                cell = str(row[col_idx] or '').strip()
                # Description: text, not numbers, length > 5
                if len(cell) > 5 and not cell.replace('.', '').replace(',', '').isdigit():
                    desc_count += 1
        return desc_count >= 2
    
    def _find_employee_in_row(self, row: List, id_col: Optional[int], 
                             name_col: Optional[int]) -> Optional[Dict]:
        """Try to find employee info in this row with intelligent validation."""
        
        emp_id = None
        emp_name = None
        
        # Try explicit ID column
        if id_col is not None and id_col < len(row):
            cell = str(row[id_col] or '').strip()
            if re.match(r'^\d{4,7}$', cell):
                emp_id = cell
        
        # Try explicit name column
        if name_col is not None and name_col < len(row):
            cell = str(row[name_col] or '').strip()
            if re.match(r'^[A-Z][a-z]+(\s+[A-Z][a-z]+)+$', cell):
                emp_name = cell
        
        # If no explicit columns, scan entire row
        if not emp_id or not emp_name:
            for cell in row:
                cell_str = str(cell or '').strip()
                
                # Look for ID pattern
                if not emp_id and re.match(r'^\d{4,7}$', cell_str):
                    emp_id = cell_str
                
                # Look for name pattern
                if not emp_name and re.match(r'^[A-Z][a-z]+(\s+[A-Z][a-z]+)+$', cell_str):
                    emp_name = cell_str
        
        # CRITICAL VALIDATION: Only accept if BOTH pass validation
        if emp_id and emp_name:
            # Validate ID
            if not self._is_valid_employee_id(emp_id):
                logger.debug(f"Rejected ID '{emp_id}' - failed validation")
                return None
            
            # Validate name
            if not self._is_valid_employee_name(emp_name):
                logger.debug(f"Rejected name '{emp_name}' - failed validation")
                return None
            
            # Both valid - accept employee
            logger.info(f"Found valid employee: {emp_id} - {emp_name}")
            return {
                'employee_id': emp_id,
                'employee_name': emp_name,
                'department': ''
            }
        
        return None
    
    def _extract_line_item(self, row: List, desc_col: int, amount_cols: List[int],
                          current_employee: Optional[Dict]) -> Optional[Dict]:
        """Extract a line item from a row."""
        
        if desc_col >= len(row):
            return None
        
        description = str(row[desc_col] or '').strip()
        if len(description) < 3:
            return None
        
        # Get amounts from amount columns
        amounts = []
        for amt_col in amount_cols:
            if amt_col < len(row):
                cell = str(row[amt_col] or '')
                cell_amounts = self._extract_amounts(cell)
                amounts.extend(cell_amounts)
        
        if not amounts:
            return None
        
        # Build line item
        emp_id = current_employee['employee_id'] if current_employee else ''
        emp_name = current_employee['employee_name'] if current_employee else ''
        
        return {
            'employee_id': emp_id,
            'employee_name': emp_name,
            'description': self._clean_description(description),
            'amount': amounts[0],
            'hours': 0,
            'rate': 0,
            'current_ytd': amounts[1] if len(amounts) > 1 else amounts[0],
            'wages_base': 0,
            'wages_ytd': 0,
            'amount_ytd': amounts[1] if len(amounts) > 1 else amounts[0],
            'scheduled': 0
        }
    
    def _deduplicate_employees(self, employees: List[Dict]) -> List[Dict]:
        """Remove duplicate employees."""
        seen = set()
        unique = []
        for emp in employees:
            emp_id = emp['employee_id']
            if emp_id not in seen:
                seen.add(emp_id)
                unique.append(emp)
        return unique


class TextBasedStrategy(ExtractionStrategy):
    """
    ADAPTIVE Text-based extraction with multiple pattern matching.
    Works on ANY text layout by trying multiple employee/line item patterns.
    """
    
    def __init__(self):
        super().__init__()
        self.name = "text_based"
        self.description = "Adaptive text extraction with multi-pattern matching"
    
    def can_handle(self, pdf_path: str, vendor: str = None) -> bool:
        """Text extraction always available if pdfplumber exists."""
        return PDFPLUMBER_AVAILABLE
    
    def extract(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract using adaptive text analysis.
        
        Process:
        1. Extract all text from PDF
        2. Try multiple patterns to find employees
        3. Use context-aware keyword matching for line items
        4. Associate line items with nearest employee
        """
        logger.info("TextBasedStrategy: Starting adaptive extraction")
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                full_text = ""
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    full_text += page_text + "\n\n"
            
            if len(full_text) < 100:
                return {'employees': [], 'earnings': [], 'taxes': [], 'deductions': []}
            
            # Extract employees using multiple patterns
            employees = self._extract_employees_multi_pattern(full_text)
            
            if not employees:
                logger.warning("No employees found via text patterns")
                # Create a default employee
                employees = [{'employee_id': 'UNKNOWN', 'employee_name': 'Unknown Employee', 'department': ''}]
            
            # Extract line items and categorize
            earnings, taxes, deductions = self._extract_line_items(full_text, employees)
            
            logger.info(f"Extracted: {len(employees)} employees, {len(earnings)} earnings, "
                       f"{len(taxes)} taxes, {len(deductions)} deductions")
            
            return {
                'employees': employees,
                'earnings': earnings,
                'taxes': taxes,
                'deductions': deductions
            }
        
        except Exception as e:
            logger.error(f"TextBasedStrategy extraction failed: {e}", exc_info=True)
            return {'employees': [], 'earnings': [], 'taxes': [], 'deductions': []}
    
    def _extract_employees_multi_pattern(self, text: str) -> List[Dict]:
        """Try multiple patterns to find employees with intelligent validation."""
        
        employees = []
        
        # Pattern 1: "Employee: Name ID: 12345" or "Name (12345)"
        pattern1 = r'(?:Employee:|Name:)?\s*([A-Z][a-z]+\s+[A-Z][a-z]+)[\s,]*(?:ID:|#|Employee\s*#)?\s*[:\(]?\s*(\d{4,7})'
        for match in re.finditer(pattern1, text, re.MULTILINE):
            name = match.group(1)
            emp_id = match.group(2)
            
            # Validate before adding
            if self._is_valid_employee_id(emp_id) and self._is_valid_employee_name(name):
                employees.append({
                    'employee_id': emp_id,
                    'employee_name': name,
                    'department': ''
                })
                logger.info(f"Pattern 1 found: {emp_id} - {name}")
            else:
                logger.debug(f"Pattern 1 rejected: {emp_id} - {name}")
        
        # Pattern 2: "12345 - FirstName LastName"
        pattern2 = r'(\d{4,7})\s*[-–]\s*([A-Z][a-z]+\s+[A-Z][a-z]+)'
        for match in re.finditer(pattern2, text):
            emp_id = match.group(1)
            name = match.group(2)
            
            if self._is_valid_employee_id(emp_id) and self._is_valid_employee_name(name):
                employees.append({
                    'employee_id': emp_id,
                    'employee_name': name,
                    'department': ''
                })
                logger.info(f"Pattern 2 found: {emp_id} - {name}")
            else:
                logger.debug(f"Pattern 2 rejected: {emp_id} - {name}")
        
        # Pattern 3: "EmpID: 12345" followed by "Name: FirstName LastName" within 100 chars
        pattern3_id = r'(?:Emp|Employee)\s*(?:ID|#)\s*:?\s*(\d{4,7})'
        for match in re.finditer(pattern3_id, text):
            emp_id = match.group(1)
            
            if not self._is_valid_employee_id(emp_id):
                continue
            
            # Look for name nearby
            context_start = max(0, match.start() - 50)
            context_end = min(len(text), match.end() + 150)
            context = text[context_start:context_end]
            
            name_match = re.search(r'(?:Name\s*:?)?\s*([A-Z][a-z]+\s+[A-Z][a-z]+)', context)
            if name_match:
                name = name_match.group(1)
                if self._is_valid_employee_name(name):
                    employees.append({
                        'employee_id': emp_id,
                        'employee_name': name,
                        'department': ''
                    })
                    logger.info(f"Pattern 3 found: {emp_id} - {name}")
                else:
                    logger.debug(f"Pattern 3 rejected name: {name}")
        
        # Pattern 4: Line starting with "12345  FirstName LastName"
        pattern4 = r'^(\d{4,7})\s{2,}([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)'
        for match in re.finditer(pattern4, text, re.MULTILINE):
            emp_id = match.group(1)
            name = match.group(2)
            
            if self._is_valid_employee_id(emp_id) and self._is_valid_employee_name(name):
                employees.append({
                    'employee_id': emp_id,
                    'employee_name': name,
                    'department': ''
                })
                logger.info(f"Pattern 4 found: {emp_id} - {name}")
            else:
                logger.debug(f"Pattern 4 rejected: {emp_id} - {name}")
        
        # Deduplicate
        seen = {}
        unique = []
        for emp in employees:
            emp_id = emp['employee_id']
            if emp_id not in seen:
                seen[emp_id] = emp
                unique.append(emp)
        
        logger.info(f"Found {len(unique)} valid employees after validation")
        return unique
    
    def _extract_line_items(self, text: str, employees: List[Dict]) -> Tuple[List, List, List]:
        """Extract and categorize line items from text."""
        
        earnings = []
        taxes = []
        deductions = []
        
        # Split into lines
        lines = text.split('\n')
        
        # Track current employee context
        current_employee = employees[0] if employees else {
            'employee_id': 'UNKNOWN',
            'employee_name': 'Unknown',
            'department': ''
        }
        
        for line in lines:
            line = line.strip()
            if len(line) < 10:
                continue
            
            # Check if this line mentions an employee (update context)
            for emp in employees:
                if emp['employee_id'] in line or emp['employee_name'] in line:
                    current_employee = emp
                    break
            
            # Check if line has monetary amounts
            amounts = self._extract_amounts(line)
            if not amounts:
                continue
            
            # Get description (text before first amount)
            amount_match = re.search(r'\$?\s*[\d,]+\.\d{2}', line)
            if amount_match:
                description = line[:amount_match.start()].strip()
            else:
                description = line[:50]
            
            if len(description) < 3:
                continue
            
            # Categorize
            line_item = {
                'employee_id': current_employee['employee_id'],
                'employee_name': current_employee['employee_name'],
                'description': self._clean_description(description),
                'amount': amounts[0],
                'hours': 0,
                'rate': 0
            }
            
            if self._is_earning(description):
                earnings.append(line_item)
            elif self._is_tax(description):
                taxes.append({**line_item, 'wages_base': 0, 'wages_ytd': 0, 
                            'amount_ytd': amounts[1] if len(amounts) > 1 else amounts[0]})
            elif self._is_deduction(description):
                deductions.append({**line_item, 'scheduled': 0,
                                 'amount_ytd': amounts[1] if len(amounts) > 1 else amounts[0]})
        
        return earnings, taxes, deductions


class HybridStrategy(ExtractionStrategy):
    """
    ADAPTIVE Hybrid: Try table first, supplement with text if needed.
    """
    
    def __init__(self):
        super().__init__()
        self.name = "hybrid"
        self.description = "Adaptive table + text combination"
        self.table_strategy = TableBasedStrategy()
        self.text_strategy = TextBasedStrategy()
    
    def can_handle(self, pdf_path: str, vendor: str = None) -> bool:
        """Can always try if pdfplumber available."""
        return PDFPLUMBER_AVAILABLE
    
    def extract(self, pdf_path: str) -> Dict[str, Any]:
        """Try table first, supplement with text for missing data."""
        
        logger.info("HybridStrategy: Trying table extraction first")
        table_result = self.table_strategy.extract(pdf_path)
        
        # If table extraction got good data, use it
        if (len(table_result['employees']) > 0 and 
            (len(table_result['earnings']) > 0 or 
             len(table_result['taxes']) > 0 or 
             len(table_result['deductions']) > 0)):
            logger.info("HybridStrategy: Table extraction successful")
            return table_result
        
        # Otherwise, try text
        logger.info("HybridStrategy: Table extraction insufficient, trying text")
        text_result = self.text_strategy.extract(pdf_path)
        
        # Combine results (prefer table employees if available)
        if table_result['employees']:
            text_result['employees'] = table_result['employees']
        
        return text_result


class StrategyLibrary:
    """Library of all available extraction strategies."""
    
    def __init__(self):
        self.strategies = [
            TableBasedStrategy(),
            HybridStrategy(),
            TextBasedStrategy()
        ]
    
    def get_strategies_for_vendor(self, vendor: str) -> List[ExtractionStrategy]:
        """
        Get recommended strategies for a vendor, in priority order.
        
        NOTE: Vendor detection is OPTIONAL - strategies work on any vendor.
        This just optimizes the order to try strategies in.
        """
        
        # Strategy order preferences by vendor (for optimization)
        strategy_map = {
            'dayforce': ['table_based', 'hybrid', 'text_based'],
            'adp': ['text_based', 'hybrid', 'table_based'],
            'paychex': ['text_based', 'hybrid', 'table_based'],
            'paycom': ['table_based', 'hybrid', 'text_based'],
            'quickbooks': ['hybrid', 'text_based', 'table_based'],
            'gusto': ['text_based', 'hybrid', 'table_based'],
            'workday': ['table_based', 'hybrid', 'text_based'],
            'ukg': ['hybrid', 'table_based', 'text_based'],
            'unknown': ['table_based', 'hybrid', 'text_based']  # Default order
        }
        
        strategy_names = strategy_map.get(vendor, strategy_map['unknown'])
        
        # Return strategy objects in order
        ordered_strategies = []
        for name in strategy_names:
            for strategy in self.strategies:
                if strategy.name == name:
                    ordered_strategies.append(strategy)
                    break
        
        return ordered_strategies
    
    def get_all_strategies(self) -> List[ExtractionStrategy]:
        """Get all strategies."""
        return self.strategies
