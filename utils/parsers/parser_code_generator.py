"""
Parser Code Generator for XLR8 Intelligent Parser
Generates custom Python parser code based on PDF analysis
"""

import logging
from typing import Dict, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class ParserCodeGenerator:
    """Generates custom parser code based on PDF structure analysis"""
    
    def __init__(self):
        self.template_version = "1.0"
        
    def generate_parser(self, analysis: Dict, hints: Dict, parser_name: Optional[str] = None) -> Dict:
        """
        Generate custom parser code based on analysis
        
        Args:
            analysis: PDF structure analysis result
            hints: Parsing hints from analyzer
            parser_name: Optional custom name for parser
            
        Returns:
            Dict with parser code and metadata
        """
        try:
            if not parser_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                doc_type = analysis.get('document_type', 'unknown')
                parser_name = f"{doc_type}_parser_{timestamp}"
            
            # Generate parser code based on document type and structure
            doc_type = analysis.get('document_type', 'unknown')
            
            if doc_type in ['payroll_register', 'register']:
                code = self._generate_register_parser(analysis, hints, parser_name)
            elif analysis.get('has_tables'):
                code = self._generate_table_parser(analysis, hints, parser_name)
            elif analysis.get('has_text'):
                code = self._generate_text_parser(analysis, hints, parser_name)
            else:
                code = self._generate_generic_parser(analysis, hints, parser_name)
            
            return {
                'success': True,
                'parser_name': parser_name,
                'code': code,
                'document_type': doc_type,
                'complexity': analysis.get('layout_complexity', 'unknown'),
                'confidence': analysis.get('confidence', 50)
            }
            
        except Exception as e:
            logger.error(f"Parser generation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_register_parser(self, analysis: Dict, hints: Dict, parser_name: str) -> str:
        """Generate parser for register documents"""
        
        code = f'''"""
Custom Register Parser: {parser_name}
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Document Type: {analysis.get('document_type', 'register')}
Complexity: {analysis.get('layout_complexity', 'moderate')}
"""

import pdfplumber
import pandas as pd
from typing import Dict, List, Optional
import logging
import re

logger = logging.getLogger(__name__)


def parse_register(pdf_path: str, output_path: str) -> Dict:
    """
    Parse register document to Excel
    
    Args:
        pdf_path: Path to input PDF
        output_path: Path to output Excel file
        
    Returns:
        Dict with parsing results and metadata
    """
    try:
        all_data = []
        metadata = {{
            'total_pages': 0,
            'total_rows': 0,
            'tables_found': 0
        }}
        
        with pdfplumber.open(pdf_path) as pdf:
            metadata['total_pages'] = len(pdf.pages)
            
            for page_num, page in enumerate(pdf.pages):
                # Extract tables from page
                tables = page.extract_tables()
                
                if not tables:
                    continue
                
                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    
                    metadata['tables_found'] += 1
                    
                    # Process table
                    processed_data = process_table(table, page_num)
                    if processed_data:
                        all_data.extend(processed_data)
        
        # Create DataFrame
        if all_data:
            df = pd.DataFrame(all_data)
            
            # Clean and standardize column names
            df.columns = [clean_column_name(col) for col in df.columns]
            
            # Remove empty rows
            df = df.dropna(how='all')
            
            # Save to Excel
            df.to_excel(output_path, index=False, engine='openpyxl')
            
            metadata['total_rows'] = len(df)
            
            return {{
                'success': True,
                'output_file': output_path,
                'rows_extracted': len(df),
                'columns': list(df.columns),
                'metadata': metadata
            }}
        else:
            return {{
                'success': False,
                'error': 'No data extracted from PDF'
            }}
            
    except Exception as e:
        logger.error(f"Parsing failed: {{str(e)}}")
        return {{
            'success': False,
            'error': str(e)
        }}


def process_table(table: List[List], page_num: int) -> List[Dict]:
    """Process a table and convert to list of dicts"""
    if not table or len(table) < 2:
        return []
    
    # Identify header row
    header_row = None
    data_start = 0
    
    # Check first few rows for header
    for i in range(min(3, len(table))):
        if is_header_row(table[i], table[i+1] if i+1 < len(table) else None):
            header_row = table[i]
            data_start = i + 1
            break
    
    if header_row is None:
        # No header found, use first row as header
        header_row = table[0]
        data_start = 1
    
    # Clean headers
    headers = [clean_header(h) for h in header_row]
    
    # Process data rows
    result = []
    for row in table[data_start:]:
        if not row or all(cell is None or str(cell).strip() == '' for cell in row):
            continue
        
        # Create row dict
        row_dict = {{}}
        for i, value in enumerate(row):
            if i < len(headers):
                header = headers[i]
                row_dict[header] = clean_value(value)
        
        result.append(row_dict)
    
    return result


def is_header_row(row: List, next_row: Optional[List]) -> bool:
    """Determine if row is a header"""
    if not row:
        return False
    
    # Headers usually have text in most cells
    non_empty = sum(1 for cell in row if cell and str(cell).strip())
    if non_empty < len(row) * 0.5:
        return False
    
    # Headers usually don't have many numbers
    numeric_count = sum(1 for cell in row if is_numeric(cell))
    if numeric_count > len(row) * 0.5:
        return False
    
    # Compare with next row if available
    if next_row:
        next_numeric = sum(1 for cell in next_row if is_numeric(cell))
        # If next row is more numeric, this is likely a header
        if next_numeric > numeric_count:
            return True
    
    return True


def is_numeric(value) -> bool:
    """Check if value is numeric"""
    if value is None:
        return False
    s = str(value).strip().replace(',', '').replace('$', '')
    try:
        float(s)
        return True
    except:
        return False


def clean_header(header) -> str:
    """Clean and standardize header name"""
    if header is None:
        return 'Unknown'
    
    s = str(header).strip()
    
    # Remove special characters
    s = re.sub(r'[^a-zA-Z0-9\\s_-]', '', s)
    
    # Replace spaces with underscores
    s = re.sub(r'\\s+', '_', s)
    
    # Remove multiple underscores
    s = re.sub(r'_+', '_', s)
    
    return s if s else 'Unknown'


def clean_column_name(name) -> str:
    """Clean column name for Excel"""
    if not name:
        return 'Column'
    
    s = str(name).strip()
    
    # Standardize common column names
    name_map = {{
        'emp_id': 'Employee_ID',
        'employee_id': 'Employee_ID',
        'empid': 'Employee_ID',
        'name': 'Employee_Name',
        'employee_name': 'Employee_Name',
        'dept': 'Department',
        'department': 'Department',
        'pos': 'Position',
        'position': 'Position',
        'salary': 'Salary',
        'pay': 'Pay',
        'date': 'Date',
        'hours': 'Hours',
        'rate': 'Rate'
    }}
    
    lower_s = s.lower()
    if lower_s in name_map:
        return name_map[lower_s]
    
    # Capitalize first letter of each word
    s = '_'.join(word.capitalize() for word in s.split('_'))
    
    return s


def clean_value(value):
    """Clean cell value"""
    if value is None:
        return ''
    
    s = str(value).strip()
    
    # Remove excessive whitespace
    s = re.sub(r'\\s+', ' ', s)
    
    return s


# Entry point for orchestrator
def parse(pdf_path: str, output_path: str) -> Dict:
    """Main entry point for parser"""
    return parse_register(pdf_path, output_path)
'''
        
        return code
    
    def _generate_table_parser(self, analysis: Dict, hints: Dict, parser_name: str) -> str:
        """Generate parser for table-based documents"""
        
        code = f'''"""
Custom Table Parser: {parser_name}
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Document Type: Table-based document
Complexity: {analysis.get('layout_complexity', 'moderate')}
"""

import pdfplumber
import pandas as pd
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


def parse(pdf_path: str, output_path: str) -> Dict:
    """
    Parse table-based document to Excel
    
    Args:
        pdf_path: Path to input PDF
        output_path: Path to output Excel file
        
    Returns:
        Dict with parsing results
    """
    try:
        all_tables = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                
                for table in tables:
                    if table and len(table) > 1:
                        # Convert to DataFrame
                        df = pd.DataFrame(table[1:], columns=table[0])
                        all_tables.append(df)
        
        if all_tables:
            # Combine all tables
            final_df = pd.concat(all_tables, ignore_index=True)
            
            # Clean data
            final_df = final_df.dropna(how='all')
            
            # Save to Excel
            final_df.to_excel(output_path, index=False, engine='openpyxl')
            
            return {{
                'success': True,
                'output_file': output_path,
                'rows_extracted': len(final_df),
                'columns': list(final_df.columns)
            }}
        else:
            return {{
                'success': False,
                'error': 'No tables found in PDF'
            }}
            
    except Exception as e:
        logger.error(f"Parsing failed: {{str(e)}}")
        return {{
            'success': False,
            'error': str(e)
        }}
'''
        
        return code
    
    def _generate_text_parser(self, analysis: Dict, hints: Dict, parser_name: str) -> str:
        """Generate parser for text-based documents"""
        
        code = f'''"""
Custom Text Parser: {parser_name}
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Document Type: Text-based document
Complexity: {analysis.get('layout_complexity', 'simple')}
"""

import pdfplumber
import pandas as pd
from typing import Dict
import logging
import re

logger = logging.getLogger(__name__)


def parse(pdf_path: str, output_path: str) -> Dict:
    """
    Parse text-based document to Excel
    
    Args:
        pdf_path: Path to input PDF
        output_path: Path to output Excel file
        
    Returns:
        Dict with parsing results
    """
    try:
        all_text = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    all_text.append(text)
        
        if all_text:
            # Parse text into structured data
            data = parse_text_content('\\n'.join(all_text))
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Save to Excel
            df.to_excel(output_path, index=False, engine='openpyxl')
            
            return {{
                'success': True,
                'output_file': output_path,
                'rows_extracted': len(df),
                'columns': list(df.columns)
            }}
        else:
            return {{
                'success': False,
                'error': 'No text extracted from PDF'
            }}
            
    except Exception as e:
        logger.error(f"Parsing failed: {{str(e)}}")
        return {{
            'success': False,
            'error': str(e)
        }}


def parse_text_content(text: str) -> List[Dict]:
    """Parse text content into structured data"""
    # Basic text parsing - extract lines as rows
    lines = text.split('\\n')
    
    data = []
    for line in lines:
        line = line.strip()
        if line:
            data.append({{'Content': line}})
    
    return data
'''
        
        return code
    
    def _generate_generic_parser(self, analysis: Dict, hints: Dict, parser_name: str) -> str:
        """Generate generic fallback parser"""
        
        code = f'''"""
Generic Parser: {parser_name}
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Document Type: {analysis.get('document_type', 'unknown')}
Complexity: {analysis.get('layout_complexity', 'unknown')}
"""

import pdfplumber
import pandas as pd
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


def parse(pdf_path: str, output_path: str) -> Dict:
    """
    Generic PDF parser
    
    Args:
        pdf_path: Path to input PDF
        output_path: Path to output Excel file
        
    Returns:
        Dict with parsing results
    """
    try:
        all_data = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                # Try tables first
                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        if table and len(table) > 1:
                            df = pd.DataFrame(table[1:], columns=table[0])
                            all_data.append(df)
                else:
                    # Fall back to text extraction
                    text = page.extract_text()
                    if text:
                        lines = text.split('\\n')
                        for line in lines:
                            if line.strip():
                                all_data.append(pd.DataFrame([{{'Content': line.strip()}}]))
        
        if all_data:
            final_df = pd.concat(all_data, ignore_index=True)
            final_df = final_df.dropna(how='all')
            
            final_df.to_excel(output_path, index=False, engine='openpyxl')
            
            return {{
                'success': True,
                'output_file': output_path,
                'rows_extracted': len(final_df),
                'columns': list(final_df.columns)
            }}
        else:
            return {{
                'success': False,
                'error': 'No data extracted from PDF'
            }}
            
    except Exception as e:
        logger.error(f"Parsing failed: {{str(e)}}")
        return {{
            'success': False,
            'error': str(e)
        }}
'''
        
        return code
    
    def save_parser(self, code: str, parser_name: str, output_dir: str = "/data/custom_parsers") -> Dict:
        """
        Save generated parser code to file
        
        Args:
            code: Parser code
            parser_name: Name for parser file
            output_dir: Directory to save parser
            
        Returns:
            Dict with save result
        """
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            parser_file = output_path / f"{parser_name}.py"
            
            with open(parser_file, 'w') as f:
                f.write(code)
            
            logger.info(f"Parser saved to {parser_file}")
            
            return {
                'success': True,
                'parser_path': str(parser_file),
                'parser_name': parser_name
            }
            
        except Exception as e:
            logger.error(f"Failed to save parser: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
