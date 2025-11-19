"""
Parser Code Generator
Generates custom Python parser code based on PDF structure analysis
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ParserCodeGenerator:
    """
    Generates custom Python parser code based on document structure.
    """
    
    def __init__(self):
        """Initialize code generator."""
        pass
    
    def generate(self, structure: Dict[str, Any]) -> Optional[str]:
        """
        Generate parser code based on structure analysis.
        
        Args:
            structure: Structure dict from PDFStructureAnalyzer
            
        Returns:
            Python code as string, or None if generation fails
        """
        try:
            format_type = structure.get('format_type', 'unknown')
            strategy = structure.get('recommended_strategy', 'basic_text')
            
            logger.info(f"Generating parser for {format_type} using {strategy} strategy")
            
            # Generate appropriate parser based on strategy
            if strategy == 'iterative_employee_extraction':
                return self._generate_iterative_parser(structure)
            elif strategy == 'section_based_extraction':
                return self._generate_section_parser(structure)
            elif strategy == 'basic_table_extraction':
                return self._generate_table_parser(structure)
            else:
                return self._generate_basic_parser(structure)
                
        except Exception as e:
            logger.error(f"Code generation error: {str(e)}", exc_info=True)
            return None
    
    def _generate_iterative_parser(self, structure: Dict[str, Any]) -> str:
        """
        Generate parser for complex multi-employee documents.
        """
        sections = structure.get('sections', [])
        
        code = '''"""
Generated Parser - Iterative Employee Extraction
Auto-generated based on PDF structure analysis
"""

import fitz  # PyMuPDF
import re
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


def parse(pdf_path: str, output_dir: str) -> Dict[str, Any]:
    """
    Parse PDF with iterative employee extraction.
    
    Args:
        pdf_path: Path to PDF file
        output_dir: Directory for output files
        
    Returns:
        Dict with status, output_path, accuracy, employee_count
    """
    try:
        # Open PDF
        doc = fitz.open(pdf_path)
        
        # Extract all text
        full_text = ""
        for page in doc:
            full_text += page.get_text()
        
        doc.close()
        
        # Parse employee blocks
        employees = parse_employee_blocks(full_text)
        
        if not employees:
            return {
                'status': 'error',
                'message': 'No employee data found',
                'accuracy': 0,
                'employee_count': 0
            }
        
        # Create 4-tab structure
        tabs = create_four_tabs(employees)
        
        # Write Excel
        output_path = write_excel(tabs, pdf_path, output_dir)
        
        # Calculate accuracy
        accuracy = calculate_accuracy(tabs, employees)
        
        return {
            'status': 'success',
            'output_path': output_path,
            'accuracy': accuracy,
            'employee_count': len(employees)
        }
        
    except Exception as e:
        logger.error(f"Parse error: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'message': str(e),
            'accuracy': 0,
            'employee_count': 0
        }


def parse_employee_blocks(text: str) -> List[Dict[str, Any]]:
    """Parse individual employee blocks."""
    employees = []
    
    # Find employee boundaries (by ID pattern)
    id_pattern = r'(?:Employee ID|EMP#|ID)[\s:]+(\d+)'
    matches = list(re.finditer(id_pattern, text, re.IGNORECASE))
    
    if not matches:
        return employees
    
    # Extract each employee block
    for i in range(len(matches)):
        start = matches[i].start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start:end]
        
        employee = parse_single_employee(block)
        if employee:
            employees.append(employee)
    
    return employees


def parse_single_employee(block: str) -> Optional[Dict[str, Any]]:
    """Parse a single employee block."""
    employee = {
        'info': {},
        'earnings': [],
        'taxes': [],
        'deductions': []
    }
    
    # Extract employee info
    id_match = re.search(r'(?:Employee ID|EMP#|ID)[\s:]+(\d+)', block, re.IGNORECASE)
    if id_match:
        employee['info']['employee_id'] = id_match.group(1)
    
    name_match = re.search(r'(?:Name|Employee)[\s:]+([A-Za-z\s,]+)', block, re.IGNORECASE)
    if name_match:
        employee['info']['name'] = name_match.group(1).strip()
    
    # Extract sections (simplified - would be more sophisticated in practice)
    lines = block.split('\\n')
    
    current_section = None
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Detect section headers
        if re.search(r'earnings', line, re.IGNORECASE):
            current_section = 'earnings'
        elif re.search(r'taxes', line, re.IGNORECASE):
            current_section = 'taxes'
        elif re.search(r'deductions', line, re.IGNORECASE):
            current_section = 'deductions'
        elif current_section and re.search(r'\d+\.\d{2}', line):
            # Line contains amount, add to current section
            parts = re.split(r'\s{2,}', line)
            if len(parts) >= 2:
                employee[current_section].append({
                    'description': parts[0],
                    'amount': parts[-1]
                })
    
    return employee if employee['info'].get('employee_id') else None


def create_four_tabs(employees: List[Dict[str, Any]]) -> Dict[str, pd.DataFrame]:
    """Create 4 DataFrames from employee data."""
    tabs = {
        'Employee Summary': [],
        'Earnings': [],
        'Taxes': [],
        'Deductions': []
    }
    
    for emp in employees:
        # Employee Summary
        summary = emp['info'].copy()
        summary['Total_Earnings'] = sum(float(e.get('amount', 0)) for e in emp['earnings'] if e.get('amount', '').replace('.', '').isdigit())
        summary['Total_Taxes'] = sum(float(t.get('amount', 0)) for t in emp['taxes'] if t.get('amount', '').replace('.', '').isdigit())
        summary['Total_Deductions'] = sum(float(d.get('amount', 0)) for d in emp['deductions'] if d.get('amount', '').replace('.', '').isdigit())
        tabs['Employee Summary'].append(summary)
        
        # Detail tabs
        for earning in emp['earnings']:
            row = emp['info'].copy()
            row.update(earning)
            tabs['Earnings'].append(row)
        
        for tax in emp['taxes']:
            row = emp['info'].copy()
            row.update(tax)
            tabs['Taxes'].append(row)
        
        for deduction in emp['deductions']:
            row = emp['info'].copy()
            row.update(deduction)
            tabs['Deductions'].append(row)
    
    return {name: pd.DataFrame(rows) if rows else pd.DataFrame() for name, rows in tabs.items()}


def write_excel(tabs: Dict[str, pd.DataFrame], pdf_path: str, output_dir: str) -> str:
    """Write 4 tabs to Excel."""
    from pathlib import Path
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    pdf_name = Path(pdf_path).stem
    output_path = output_dir / f"{pdf_name}_parsed.xlsx"
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        for tab_name, df in tabs.items():
            df.to_excel(writer, sheet_name=tab_name, index=False)
    
    return str(output_path)


def calculate_accuracy(tabs: Dict[str, pd.DataFrame], employees: List[Dict]) -> int:
    """Calculate accuracy score (0-100)."""
    score = 30  # Base success points
    
    # Table quality (40 pts)
    total_rows = sum(len(df) for df in tabs.values())
    if total_rows > 0:
        score += min(40, int(total_rows / len(employees) * 8))
    
    # Data extraction (20 pts)
    info_fields = sum(len(emp['info']) for emp in employees) / max(len(employees), 1)
    score += min(20, int(info_fields * 4))
    
    # Data quality (10 pts)
    has_ids = all('employee_id' in emp['info'] for emp in employees)
    if has_ids:
        score += 10
    
    return min(100, score)
'''
        
        return code
    
    def _generate_section_parser(self, structure: Dict[str, Any]) -> str:
        """
        Generate parser for section-based documents.
        """
        code = '''"""
Generated Parser - Section-Based Extraction
Auto-generated based on PDF structure analysis
"""

import fitz
import re
import pandas as pd
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def parse(pdf_path: str, output_dir: str) -> Dict[str, Any]:
    """Parse PDF with section-based extraction."""
    try:
        doc = fitz.open(pdf_path)
        full_text = "".join(page.get_text() for page in doc)
        doc.close()
        
        # Extract sections
        sections = extract_sections(full_text)
        
        # Create output
        df = pd.DataFrame([sections])
        
        # Write Excel
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{Path(pdf_path).stem}_parsed.xlsx"
        df.to_excel(output_path, index=False)
        
        return {
            'status': 'success',
            'output_path': str(output_path),
            'accuracy': 60,
            'employee_count': 1
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e),
            'accuracy': 0,
            'employee_count': 0
        }


def extract_sections(text: str) -> Dict[str, str]:
    """Extract text by sections."""
    sections = {}
    lines = text.split('\\n')
    current_section = 'general'
    current_text = []
    
    for line in lines:
        if re.search(r'^[A-Z][a-z]+:', line):
            if current_text:
                sections[current_section] = ' '.join(current_text)
            current_section = line.split(':')[0].lower()
            current_text = [line]
        else:
            current_text.append(line)
    
    if current_text:
        sections[current_section] = ' '.join(current_text)
    
    return sections
'''
        return code
    
    def _generate_table_parser(self, structure: Dict[str, Any]) -> str:
        """
        Generate parser for simple table documents.
        """
        code = '''"""
Generated Parser - Basic Table Extraction
Auto-generated based on PDF structure analysis
"""

import fitz
import pandas as pd
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def parse(pdf_path: str, output_dir: str) -> Dict[str, Any]:
    """Parse PDF with basic table extraction."""
    try:
        import pdfplumber
        
        with pdfplumber.open(pdf_path) as pdf:
            all_tables = []
            for page in pdf.pages:
                tables = page.extract_tables()
                all_tables.extend(tables)
        
        if not all_tables:
            return {
                'status': 'error',
                'message': 'No tables found',
                'accuracy': 0,
                'employee_count': 0
            }
        
        # Convert first table to DataFrame
        df = pd.DataFrame(all_tables[0][1:], columns=all_tables[0][0])
        
        # Write Excel
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{Path(pdf_path).stem}_parsed.xlsx"
        df.to_excel(output_path, index=False)
        
        return {
            'status': 'success',
            'output_path': str(output_path),
            'accuracy': 70,
            'employee_count': len(df)
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e),
            'accuracy': 0,
            'employee_count': 0
        }
'''
        return code
    
    def _generate_basic_parser(self, structure: Dict[str, Any]) -> str:
        """
        Generate basic text extraction parser.
        """
        code = '''"""
Generated Parser - Basic Text Extraction
Auto-generated based on PDF structure analysis
"""

import fitz
import pandas as pd
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def parse(pdf_path: str, output_dir: str) -> Dict[str, Any]:
    """Parse PDF with basic text extraction."""
    try:
        doc = fitz.open(pdf_path)
        text = "".join(page.get_text() for page in doc)
        doc.close()
        
        # Create simple DataFrame
        df = pd.DataFrame([{'content': text}])
        
        # Write Excel
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{Path(pdf_path).stem}_parsed.xlsx"
        df.to_excel(output_path, index=False)
        
        return {
            'status': 'success',
            'output_path': str(output_path),
            'accuracy': 50,
            'employee_count': 1
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e),
            'accuracy': 0,
            'employee_count': 0
        }
'''
        return code
