"""
Secure Multi-Strategy PDF Parser for Complex Payroll Registers
100% Local Processing - NO External APIs - PII Safe
Uses multiple parsing strategies with intelligent fallbacks
"""

import io
import json
import re
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime
import logging

# PDF Processing Libraries
import pdfplumber
try:
    import camelot
    CAMELOT_AVAILABLE = True
except ImportError:
    CAMELOT_AVAILABLE = False

try:
    import tabula
    TABULA_AVAILABLE = True
except ImportError:
    TABULA_AVAILABLE = False

import fitz  # PyMuPDF

# For OCR fallback
try:
    from pdf2image import convert_from_bytes
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


class SecurePayrollParser:
    """
    Multi-strategy parser for complex payroll registers
    All processing is local - no external API calls
    """
    
    # Common payroll field patterns
    FIELD_PATTERNS = {
        'employee_id': [
            r'emp\s*id', r'employee\s*id', r'empid', r'ee\s*id', 
            r'employee\s*number', r'emp\s*#', r'ee\s*#', r'id'
        ],
        'employee_name': [
            r'name', r'employee\s*name', r'emp\s*name', 
            r'full\s*name', r'employee', r'last\s*name'
        ],
        'ssn': [
            r'ssn', r'social\s*security', r'ss\s*#', r'soc\s*sec'
        ],
        'gross_pay': [
            r'gross', r'gross\s*pay', r'gross\s*earnings', 
            r'total\s*gross', r'gross\s*amount'
        ],
        'net_pay': [
            r'net', r'net\s*pay', r'take\s*home', 
            r'net\s*amount', r'net\s*earnings'
        ],
        'hours': [
            r'hours', r'hours\s*worked', r'regular\s*hours', 
            r'total\s*hours', r'hrs', r'reg\s*hrs'
        ],
        'rate': [
            r'rate', r'pay\s*rate', r'hourly\s*rate', 
            r'hr\s*rate', r'wage\s*rate'
        ],
        'deductions': [
            r'deductions', r'total\s*deductions', r'withheld', 
            r'deduct', r'withholding'
        ],
        'taxes': [
            r'tax', r'taxes', r'federal', r'fica', 
            r'medicare', r'withholding', r'fed\s*tax'
        ],
        'ytd': [
            r'ytd', r'year\s*to\s*date', r'ytd\s*total', r'y\.t\.d\.'
        ],
        'department': [
            r'dept', r'department', r'cost\s*center', 
            r'division', r'org'
        ],
        'position': [
            r'position', r'job', r'title', r'job\s*title', r'role'
        ],
        'date': [
            r'date', r'pay\s*date', r'check\s*date', 
            r'period', r'pay\s*period'
        ],
        'check_number': [
            r'check', r'check\s*#', r'check\s*number', r'chk\s*#'
        ]
    }
    
    def __init__(self):
        """Initialize the secure parser"""
        self.parsing_results = {}
        self.strategies_tried = []
        self.logger = logging.getLogger(__name__)
        
    def parse_pdf(
        self,
        pdf_content: bytes,
        filename: str,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Parse PDF using multiple strategies with intelligent fallbacks
        
        Args:
            pdf_content: PDF file as bytes
            filename: Name of the PDF file
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary with parsed data, tables, and metadata
        """
        start_time = datetime.now()
        
        result = {
            'filename': filename,
            'parsed_at': start_time.isoformat(),
            'tables': [],
            'raw_text': '',
            'metadata': {},
            'strategies_used': [],
            'success': False,
            'error': None
        }
        
        try:
            # Strategy 1: pdfplumber (lenient settings)
            if progress_callback:
                progress_callback("Trying pdfplumber extraction...")
            
            tables, metadata = self._parse_with_pdfplumber(pdf_content)
            if tables and len(tables) > 0:
                result['tables'] = tables
                result['metadata'] = metadata
                result['strategies_used'].append('pdfplumber')
                result['success'] = True
                self.logger.info(f"pdfplumber succeeded: {len(tables)} tables found")
                
            # Strategy 2: Camelot (if pdfplumber found few/no tables)
            if (not result['success'] or len(result['tables']) < 2) and CAMELOT_AVAILABLE:
                if progress_callback:
                    progress_callback("Trying Camelot extraction...")
                    
                camelot_tables = self._parse_with_camelot(pdf_content, filename)
                if camelot_tables and len(camelot_tables) > len(result['tables']):
                    result['tables'] = camelot_tables
                    result['strategies_used'].append('camelot')
                    result['success'] = True
                    self.logger.info(f"Camelot succeeded: {len(camelot_tables)} tables found")
            
            # Strategy 3: Tabula (if still not enough data)
            if (not result['success'] or len(result['tables']) < 2) and TABULA_AVAILABLE:
                if progress_callback:
                    progress_callback("Trying Tabula extraction...")
                    
                tabula_tables = self._parse_with_tabula(pdf_content)
                if tabula_tables and len(tabula_tables) > len(result['tables']):
                    result['tables'] = tabula_tables
                    result['strategies_used'].append('tabula')
                    result['success'] = True
                    self.logger.info(f"Tabula succeeded: {len(tabula_tables)} tables found")
            
            # Strategy 4: PyMuPDF with smart pattern matching
            if not result['success']:
                if progress_callback:
                    progress_callback("Trying PyMuPDF extraction...")
                    
                pymupdf_result = self._parse_with_pymupdf(pdf_content)
                if pymupdf_result['tables']:
                    result['tables'] = pymupdf_result['tables']
                    result['raw_text'] = pymupdf_result['raw_text']
                    result['strategies_used'].append('pymupdf')
                    result['success'] = True
                    self.logger.info(f"PyMuPDF succeeded: {len(pymupdf_result['tables'])} tables found")
            
            # Strategy 5: OCR as last resort (for scanned PDFs)
            if not result['success'] and OCR_AVAILABLE:
                if progress_callback:
                    progress_callback("Trying OCR extraction (scanned PDF)...")
                    
                ocr_result = self._parse_with_ocr(pdf_content)
                if ocr_result['tables']:
                    result['tables'] = ocr_result['tables']
                    result['raw_text'] = ocr_result['raw_text']
                    result['strategies_used'].append('ocr')
                    result['success'] = True
                    self.logger.info("OCR succeeded")
            
            # Post-process: Identify payroll fields
            if result['tables']:
                if progress_callback:
                    progress_callback("Identifying payroll fields...")
                    
                result = self._identify_payroll_fields(result)
                result = self._clean_and_normalize(result)
            
            # Calculate processing time
            end_time = datetime.now()
            result['processing_time'] = (end_time - start_time).total_seconds()
            
            if not result['success']:
                result['error'] = "No tables could be extracted from PDF"
                
        except Exception as e:
            self.logger.error(f"Error parsing PDF: {str(e)}")
            result['success'] = False
            result['error'] = str(e)
        
        return result
    
    def _parse_with_pdfplumber(self, pdf_content: bytes) -> Tuple[List[Dict], Dict]:
        """
        Parse PDF with pdfplumber using very lenient settings
        
        Args:
            pdf_content: PDF file as bytes
            
        Returns:
            Tuple of (tables, metadata)
        """
        tables = []
        metadata = {
            'total_pages': 0,
            'pages_with_tables': 0
        }
        
        try:
            # Ultra-lenient table settings
            table_settings = {
                "vertical_strategy": "text",  # Most lenient
                "horizontal_strategy": "text",
                "snap_tolerance": 10,
                "snap_x_tolerance": 10,
                "snap_y_tolerance": 10,
                "join_tolerance": 10,
                "join_x_tolerance": 10,
                "join_y_tolerance": 10,
                "edge_min_length": 1,
                "min_words_vertical": 1,
                "min_words_horizontal": 1,
                "intersection_tolerance": 10,
                "intersection_x_tolerance": 10,
                "intersection_y_tolerance": 10,
                "text_tolerance": 10,
                "text_x_tolerance": 10,
                "text_y_tolerance": 10
            }
            
            with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
                metadata['total_pages'] = len(pdf.pages)
                
                for page_num, page in enumerate(pdf.pages, 1):
                    # Try to extract tables
                    page_tables = page.extract_tables(table_settings=table_settings)
                    
                    if page_tables:
                        metadata['pages_with_tables'] += 1
                        
                        for table_num, table in enumerate(page_tables, 1):
                            if table and len(table) > 0:
                                # Convert to DataFrame
                                df = self._table_to_dataframe(table)
                                
                                if not df.empty:
                                    tables.append({
                                        'page': page_num,
                                        'table_num': table_num,
                                        'data': df,
                                        'row_count': len(df),
                                        'col_count': len(df.columns)
                                    })
        
        except Exception as e:
            self.logger.error(f"pdfplumber error: {str(e)}")
        
        return tables, metadata
    
    def _parse_with_camelot(self, pdf_content: bytes, filename: str) -> List[Dict]:
        """
        Parse PDF with Camelot (better for complex tables)
        
        Args:
            pdf_content: PDF file as bytes
            filename: Filename for temporary file
            
        Returns:
            List of table dictionaries
        """
        tables = []
        
        if not CAMELOT_AVAILABLE:
            return tables
        
        try:
            # Save temporarily
            temp_path = f"/tmp/{filename}"
            with open(temp_path, 'wb') as f:
                f.write(pdf_content)
            
            # Try lattice mode (for tables with lines)
            try:
                camelot_tables = camelot.read_pdf(
                    temp_path,
                    flavor='lattice',
                    pages='all'
                )
                
                for idx, table in enumerate(camelot_tables, 1):
                    df = table.df
                    if not df.empty and len(df) > 1:
                        # Use first row as header
                        df.columns = df.iloc[0]
                        df = df[1:]
                        df.reset_index(drop=True, inplace=True)
                        
                        tables.append({
                            'page': table.page,
                            'table_num': idx,
                            'data': df,
                            'row_count': len(df),
                            'col_count': len(df.columns),
                            'accuracy': table.accuracy
                        })
            except:
                pass
            
            # Try stream mode (for tables without lines)
            try:
                camelot_tables = camelot.read_pdf(
                    temp_path,
                    flavor='stream',
                    pages='all',
                    edge_tol=500  # Very lenient
                )
                
                for idx, table in enumerate(camelot_tables, 1):
                    df = table.df
                    if not df.empty and len(df) > 1:
                        df.columns = df.iloc[0]
                        df = df[1:]
                        df.reset_index(drop=True, inplace=True)
                        
                        tables.append({
                            'page': table.page,
                            'table_num': idx,
                            'data': df,
                            'row_count': len(df),
                            'col_count': len(df.columns),
                            'accuracy': table.accuracy
                        })
            except:
                pass
                
        except Exception as e:
            self.logger.error(f"Camelot error: {str(e)}")
        
        return tables
    
    def _parse_with_tabula(self, pdf_content: bytes) -> List[Dict]:
        """
        Parse PDF with Tabula (Java-based, good for complex layouts)
        
        Args:
            pdf_content: PDF file as bytes
            
        Returns:
            List of table dictionaries
        """
        tables = []
        
        if not TABULA_AVAILABLE:
            return tables
        
        try:
            # Read all tables
            dfs = tabula.read_pdf(
                io.BytesIO(pdf_content),
                pages='all',
                multiple_tables=True,
                lattice=False,  # Try stream mode first
                guess=True
            )
            
            for idx, df in enumerate(dfs, 1):
                if not df.empty and len(df) > 1:
                    tables.append({
                        'page': 1,  # Tabula doesn't always provide page numbers
                        'table_num': idx,
                        'data': df,
                        'row_count': len(df),
                        'col_count': len(df.columns)
                    })
                    
        except Exception as e:
            self.logger.error(f"Tabula error: {str(e)}")
        
        return tables
    
    def _parse_with_pymupdf(self, pdf_content: bytes) -> Dict:
        """
        Parse PDF with PyMuPDF and smart pattern matching
        
        Args:
            pdf_content: PDF file as bytes
            
        Returns:
            Dictionary with tables and raw text
        """
        result = {
            'tables': [],
            'raw_text': ''
        }
        
        try:
            doc = fitz.open(stream=pdf_content, filetype="pdf")
            all_text = []
            
            for page_num, page in enumerate(doc, 1):
                text = page.get_text()
                all_text.append(text)
                
                # Try to extract structured data from text
                tables = self._extract_tables_from_text(text, page_num)
                result['tables'].extend(tables)
            
            result['raw_text'] = '\n\n'.join(all_text)
            doc.close()
            
        except Exception as e:
            self.logger.error(f"PyMuPDF error: {str(e)}")
        
        return result
    
    def _parse_with_ocr(self, pdf_content: bytes) -> Dict:
        """
        Parse scanned PDF with OCR (last resort)
        
        Args:
            pdf_content: PDF file as bytes
            
        Returns:
            Dictionary with tables and raw text
        """
        result = {
            'tables': [],
            'raw_text': ''
        }
        
        if not OCR_AVAILABLE:
            return result
        
        try:
            # Convert PDF to images
            images = convert_from_bytes(pdf_content)
            all_text = []
            
            for page_num, image in enumerate(images, 1):
                # OCR the image
                text = pytesseract.image_to_string(image)
                all_text.append(text)
                
                # Try to extract tables from OCR'd text
                tables = self._extract_tables_from_text(text, page_num)
                result['tables'].extend(tables)
            
            result['raw_text'] = '\n\n'.join(all_text)
            
        except Exception as e:
            self.logger.error(f"OCR error: {str(e)}")
        
        return result
    
    def _extract_tables_from_text(self, text: str, page_num: int) -> List[Dict]:
        """
        Extract tabular data from plain text using pattern matching
        
        Args:
            text: Plain text from PDF
            page_num: Page number
            
        Returns:
            List of table dictionaries
        """
        tables = []
        
        try:
            # Split into lines
            lines = text.split('\n')
            lines = [line.strip() for line in lines if line.strip()]
            
            # Look for table-like patterns (rows with similar structure)
            table_data = []
            current_table = []
            
            for line in lines:
                # Check if line looks like a data row (has multiple separated values)
                parts = re.split(r'\s{2,}|\t', line)
                if len(parts) >= 3:  # At least 3 columns
                    current_table.append(parts)
                else:
                    # End of table
                    if len(current_table) >= 3:  # At least 3 rows including header
                        table_data.append(current_table)
                    current_table = []
            
            # Don't forget the last table
            if len(current_table) >= 3:
                table_data.append(current_table)
            
            # Convert to DataFrames
            for idx, table in enumerate(table_data, 1):
                df = pd.DataFrame(table[1:], columns=table[0])
                if not df.empty:
                    tables.append({
                        'page': page_num,
                        'table_num': idx,
                        'data': df,
                        'row_count': len(df),
                        'col_count': len(df.columns)
                    })
                    
        except Exception as e:
            self.logger.error(f"Text extraction error: {str(e)}")
        
        return tables
    
    def _table_to_dataframe(self, table: List[List]) -> pd.DataFrame:
        """
        Convert table (list of lists) to pandas DataFrame
        
        Args:
            table: Table data as list of lists
            
        Returns:
            pandas DataFrame
        """
        if not table or len(table) < 2:
            return pd.DataFrame()
        
        # First row as headers
        headers = table[0]
        data = table[1:]
        
        # Clean headers
        headers = [str(h).strip() if h else f"Column_{i}" for i, h in enumerate(headers)]
        
        # Create DataFrame
        try:
            df = pd.DataFrame(data, columns=headers)
            
            # Clean data - handle None values
            df = df.map(lambda x: str(x).strip() if x is not None else '')
            
            return df
        except:
            return pd.DataFrame()
    
    def _identify_payroll_fields(self, result: Dict) -> Dict:
        """
        Identify payroll-specific fields in extracted tables
        
        Args:
            result: Parsing result dictionary
            
        Returns:
            Updated result with field mappings
        """
        result['identified_fields'] = {}
        
        for table in result['tables']:
            df = table['data']
            field_mapping = {}
            
            # Check each column header against patterns
            for col in df.columns:
                col_lower = str(col).lower()
                
                for field_name, patterns in self.FIELD_PATTERNS.items():
                    for pattern in patterns:
                        if re.search(pattern, col_lower):
                            field_mapping[col] = field_name
                            break
            
            table['field_mapping'] = field_mapping
            
            # Add to global identified fields
            for original, standardized in field_mapping.items():
                if standardized not in result['identified_fields']:
                    result['identified_fields'][standardized] = []
                result['identified_fields'][standardized].append({
                    'table': f"Page {table['page']}, Table {table['table_num']}",
                    'column': original
                })
        
        return result
    
    def _clean_and_normalize(self, result: Dict) -> Dict:
        """
        Clean and normalize extracted data
        
        Args:
            result: Parsing result dictionary
            
        Returns:
            Updated result with cleaned data
        """
        for table in result['tables']:
            df = table['data']
            
            # Remove empty rows
            df = df.replace('', np.nan)
            df = df.dropna(how='all')
            
            # Remove duplicate rows
            df = df.drop_duplicates()
            
            # Strip whitespace from all string columns
            for col in df.columns:
                try:
                    if hasattr(df[col], 'dtype') and df[col].dtype == 'object':
                        df[col] = df[col].str.strip()
                except (AttributeError, KeyError):
                    pass  # Skip if column doesn't support this operation
            
            # Try to convert numeric columns
            for col in df.columns:
                try:
                    # Check if column looks numeric (has $, commas, decimals)
                    sample = df[col].dropna().head()
                    if len(sample) > 0:
                        sample_str = str(sample.iloc[0])
                        if any(char in sample_str for char in ['$', ',', '.']):
                            # Remove $, commas
                            df[col] = df[col].str.replace('$', '', regex=False).str.replace(',', '', regex=False)
                            df[col] = pd.to_numeric(df[col], errors='ignore')
                except (AttributeError, KeyError, TypeError):
                    pass  # Skip columns that don't support these operations
            
            # Update the table
            table['data'] = df
            table['row_count'] = len(df)
        
        return result
    
    def export_to_excel(
        self,
        result: Dict,
        output_path: str
    ) -> str:
        """
        Export parsed data to Excel file
        
        Args:
            result: Parsing result dictionary
            output_path: Path to save Excel file
            
        Returns:
            Path to created Excel file
        """
        try:
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # Summary sheet
                summary_data = {
                    'Filename': [result['filename']],
                    'Parsed At': [result['parsed_at']],
                    'Total Tables': [len(result['tables'])],
                    'Processing Time (s)': [result.get('processing_time', 0)],
                    'Strategies Used': [', '.join(result['strategies_used'])]
                }
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
                
                # Identified fields sheet
                if result.get('identified_fields'):
                    fields_data = []
                    for field, locations in result['identified_fields'].items():
                        for loc in locations:
                            fields_data.append({
                                'Field': field,
                                'Table': loc['table'],
                                'Column': loc['column']
                            })
                    fields_df = pd.DataFrame(fields_data)
                    fields_df.to_excel(writer, sheet_name='Identified Fields', index=False)
                
                # Individual table sheets
                for table in result['tables']:
                    sheet_name = f"P{table['page']}_T{table['table_num']}"
                    # Excel sheet names limited to 31 characters
                    sheet_name = sheet_name[:31]
                    table['data'].to_excel(writer, sheet_name=sheet_name, index=False)
                
                # Combined data sheet (if tables have similar structure)
                if len(result['tables']) > 0:
                    try:
                        all_data = pd.concat([t['data'] for t in result['tables']], ignore_index=True)
                        all_data.to_excel(writer, sheet_name='All Data', index=False)
                    except:
                        pass  # Skip if tables can't be combined
            
            return output_path
            
        except Exception as e:
            self.logger.error(f"Excel export error: {str(e)}")
            raise
