"""
PDF Parser Interface Contract
All PDF parser implementations MUST follow this interface

This ensures team members can work on parsers independently
without breaking existing functionality.
"""

from typing import Protocol, List, Dict, Any, Optional
from pandas import DataFrame
from io import BytesIO


class PDFParserInterface(Protocol):
    """
    Interface contract for PDF parsers.
    
    Any class/module that parses PDFs must implement these methods
    with the exact signatures and return types specified.
    
    Team members can create new parsers (e.g., OCR-based, AI-enhanced)
    as long as they follow this contract.
    """
    
    def parse(self, file: BytesIO, filename: str) -> Dict[str, Any]:
        """
        Parse a PDF file and extract structured data.
        
        Args:
            file: PDF file as BytesIO object
            filename: Original filename (for metadata)
        
        Returns:
            Dictionary with REQUIRED keys:
            {
                'text': str,                    # Full extracted text
                'tables': List[DataFrame],       # Extracted tables as DataFrames
                'metadata': {                    # Document metadata
                    'filename': str,
                    'pages': int,
                    'parser_version': str,
                    'extraction_method': str     # e.g., 'pdfplumber', 'OCR', 'AI'
                },
                'success': bool,                 # True if parsing succeeded
                'errors': List[str]              # List of error messages (empty if success)
            }
        
        Example:
            result = parser.parse(file_obj, "payroll.pdf")
            if result['success']:
                text = result['text']
                tables = result['tables']
        """
        ...
    
    def extract_tables(self, file: BytesIO) -> List[DataFrame]:
        """
        Extract only tables from PDF (fast operation).
        
        Args:
            file: PDF file as BytesIO object
        
        Returns:
            List of pandas DataFrames, one per detected table
            Empty list if no tables found
        
        Example:
            tables = parser.extract_tables(file_obj)
            for i, table in enumerate(tables):
                print(f"Table {i}: {table.shape}")
        """
        ...
    
    def extract_text(self, file: BytesIO) -> str:
        """
        Extract only text from PDF (fast operation).
        
        Args:
            file: PDF file as BytesIO object
        
        Returns:
            Full text content as string
            Empty string if extraction fails
        
        Example:
            text = parser.extract_text(file_obj)
        """
        ...
    
    def validate_structure(self, file: BytesIO) -> Dict[str, Any]:
        """
        Validate PDF structure without full parsing.
        
        Args:
            file: PDF file as BytesIO object
        
        Returns:
            {
                'is_valid': bool,           # Can this PDF be parsed?
                'page_count': int,          # Number of pages
                'has_tables': bool,         # Contains tables?
                'has_text': bool,           # Contains text?
                'is_scanned': bool,         # Is this a scanned image?
                'warnings': List[str]       # Potential issues
            }
        
        Example:
            validation = parser.validate_structure(file_obj)
            if validation['is_scanned']:
                print("OCR required")
        """
        ...
    
    def get_parser_info(self) -> Dict[str, str]:
        """
        Get information about this parser implementation.
        
        Returns:
            {
                'name': str,                # e.g., "EnhancedPDFParser"
                'version': str,             # e.g., "2.0.0"
                'engine': str,              # e.g., "pdfplumber", "OCR", "AI"
                'capabilities': List[str]   # e.g., ["tables", "text", "images"]
            }
        
        Example:
            info = parser.get_parser_info()
            print(f"Using {info['name']} v{info['version']}")
        """
        ...


class PayrollParserInterface(Protocol):
    """
    Specialized interface for payroll-specific parsing.
    
    Extends PDFParserInterface with payroll-specific methods.
    """
    
    def parse_payroll(self, file: BytesIO, filename: str, 
                     mapping: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Parse payroll-specific data with optional field mapping.
        
        Args:
            file: PDF file
            filename: Original filename
            mapping: Optional field mapping dict
                     e.g., {'EMP ID': 'employee_id', 'Gross': 'gross_pay'}
        
        Returns:
            {
                'employees': DataFrame,          # Employee data
                'totals': Dict[str, float],     # Totals by category
                'pay_period': {                 # Pay period info
                    'start_date': str,
                    'end_date': str,
                    'pay_date': str
                },
                'company_info': Dict[str, str], # Company details
                'detected_fields': List[str],   # Auto-detected field names
                'success': bool,
                'errors': List[str]
            }
        """
        ...
    
    def detect_payroll_fields(self, file: BytesIO) -> List[str]:
        """
        Auto-detect payroll field names in the document.
        
        Args:
            file: PDF file
        
        Returns:
            List of detected field names
            e.g., ['Employee ID', 'Name', 'Regular Hours', 'Gross Pay']
        """
        ...
    
    def apply_mapping(self, data: DataFrame, 
                     mapping: Dict[str, str]) -> DataFrame:
        """
        Apply field name mapping to DataFrame.
        
        Args:
            data: Original DataFrame with source field names
            mapping: Dict mapping source → target field names
        
        Returns:
            DataFrame with renamed columns
        
        Example:
            mapping = {'EMP ID': 'employee_id', 'Name': 'employee_name'}
            mapped_data = parser.apply_mapping(data, mapping)
        """
        ...


# Example implementation signature (for reference)
class ExamplePDFParser:
    """
    Example showing how to implement PDFParserInterface.
    
    Team members can copy this template.
    """
    
    def __init__(self):
        self.version = "1.0.0"
        self.name = "ExampleParser"
    
    def parse(self, file: BytesIO, filename: str) -> Dict[str, Any]:
        """Implementation of parse method"""
        try:
            # Your parsing logic here
            text = self.extract_text(file)
            tables = self.extract_tables(file)
            
            return {
                'text': text,
                'tables': tables,
                'metadata': {
                    'filename': filename,
                    'pages': 1,  # calculate actual
                    'parser_version': self.version,
                    'extraction_method': 'example'
                },
                'success': True,
                'errors': []
            }
        except Exception as e:
            return {
                'text': '',
                'tables': [],
                'metadata': {'filename': filename},
                'success': False,
                'errors': [str(e)]
            }
    
    def extract_tables(self, file: BytesIO) -> List[DataFrame]:
        """Implementation of extract_tables"""
        # Your logic here
        return []
    
    def extract_text(self, file: BytesIO) -> str:
        """Implementation of extract_text"""
        # Your logic here
        return ""
    
    def validate_structure(self, file: BytesIO) -> Dict[str, Any]:
        """Implementation of validate_structure"""
        return {
            'is_valid': True,
            'page_count': 1,
            'has_tables': True,
            'has_text': True,
            'is_scanned': False,
            'warnings': []
        }
    
    def get_parser_info(self) -> Dict[str, str]:
        """Implementation of get_parser_info"""
        return {
            'name': self.name,
            'version': self.version,
            'engine': 'example',
            'capabilities': ['tables', 'text']
        }
