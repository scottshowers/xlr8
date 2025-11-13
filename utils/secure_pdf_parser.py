"""
Railway-Compatible PDF Parser with UKG Categorization
Works without OCR or image processing dependencies
"""

import re
import os
import tempfile
from typing import Dict, List, Tuple, Optional
import pandas as pd
from io import BytesIO
from datetime import datetime


class PayrollFieldCategories:
    """Defines field patterns and their UKG category mappings"""
    
    # Field patterns with their corresponding UKG categories
    FIELD_PATTERNS = {
        # Employee Info
        'employee_id': {
            'patterns': [
                r'emp(?:loyee)?[\s_-]*(?:id|num|no|#)',
                r'(?:^|\s)id(?:$|\s)',
                r'employee[\s_-]*number',
                r'emp\s*#',
                r'ee[\s_-]*(?:id|num)'
            ],
            'category': 'Employee Info'
        },
        'employee_name': {
            'patterns': [
                r'emp(?:loyee)?[\s_-]*name',
                r'(?:^|\s)name(?:$|\s)',
                r'full[\s_-]*name',
                r'employee',
                r'last[\s_-]*name',
                r'first[\s_-]*name'
            ],
            'category': 'Employee Info'
        },
        'ssn': {
            'patterns': [
                r'ssn',
                r'social[\s_-]*security',
                r'ss[\s_-]*(?:num|no|#)',
                r'tax[\s_-]*id'
            ],
            'category': 'Employee Info'
        },
        'department': {
            'patterns': [
                r'dept',
                r'department',
                r'div(?:ision)?',
                r'cost[\s_-]*center'
            ],
            'category': 'Employee Info'
        },
        'position': {
            'patterns': [
                r'position',
                r'title',
                r'job[\s_-]*(?:title|code)',
                r'role'
            ],
            'category': 'Employee Info'
        },
        
        # Earnings
        'regular_hours': {
            'patterns': [
                r'reg(?:ular)?[\s_-]*(?:hrs|hours)',
                r'straight[\s_-]*(?:time|hrs)',
                r'regular[\s_-]*time',
                r'(?:^|\s)hours(?:$|\s)'
            ],
            'category': 'Earnings'
        },
        'overtime_hours': {
            'patterns': [
                r'o\.?t\.?[\s_-]*(?:hrs|hours)',
                r'overtime[\s_-]*(?:hrs|hours)',
                r'ot[\s_-]*time',
                r'time[\s_-]*and[\s_-]*half'
            ],
            'category': 'Earnings'
        },
        'rate': {
            'patterns': [
                r'(?:^|\s)rate(?:$|\s)',
                r'pay[\s_-]*rate',
                r'hourly[\s_-]*rate',
                r'wage'
            ],
            'category': 'Earnings'
        },
        'gross_pay': {
            'patterns': [
                r'gross[\s_-]*(?:pay|wages|earnings)',
                r'total[\s_-]*(?:pay|earnings|wages)',
                r'gross'
            ],
            'category': 'Earnings'
        },
        'bonus': {
            'patterns': [
                r'bonus',
                r'incentive',
                r'commission'
            ],
            'category': 'Earnings'
        },
        
        # Deductions
        'federal_tax': {
            'patterns': [
                r'fed(?:eral)?[\s_-]*(?:tax|wit|withhold)',
                r'fit',
                r'federal[\s_-]*income'
            ],
            'category': 'Deductions'
        },
        'state_tax': {
            'patterns': [
                r'state[\s_-]*(?:tax|wit|withhold)',
                r'sit',
                r'state[\s_-]*income'
            ],
            'category': 'Deductions'
        },
        'social_security': {
            'patterns': [
                r'social[\s_-]*security',
                r'ss[\s_-]*tax',
                r'fica[\s_-]*ss',
                r'oasdi'
            ],
            'category': 'Deductions'
        },
        'medicare': {
            'patterns': [
                r'medicare',
                r'med[\s_-]*tax',
                r'fica[\s_-]*med'
            ],
            'category': 'Deductions'
        },
        'health_insurance': {
            'patterns': [
                r'health[\s_-]*ins',
                r'medical[\s_-]*ins',
                r'dental',
                r'vision'
            ],
            'category': 'Deductions'
        },
        'retirement': {
            'patterns': [
                r'401k',
                r'retirement',
                r'pension',
                r'ira'
            ],
            'category': 'Deductions'
        },
        
        # Taxes
        'local_tax': {
            'patterns': [
                r'local[\s_-]*tax',
                r'city[\s_-]*tax',
                r'county[\s_-]*tax'
            ],
            'category': 'Taxes'
        },
        'sdi': {
            'patterns': [
                r'sdi',
                r'disability[\s_-]*ins',
                r'state[\s_-]*disability'
            ],
            'category': 'Taxes'
        },
        'sui': {
            'patterns': [
                r'sui',
                r'unemployment[\s_-]*ins',
                r'state[\s_-]*unemployment'
            ],
            'category': 'Taxes'
        },
        
        # Check Info
        'net_pay': {
            'patterns': [
                r'net[\s_-]*(?:pay|amount)',
                r'take[\s_-]*home',
                r'net'
            ],
            'category': 'Check Info'
        },
        'check_number': {
            'patterns': [
                r'check[\s_-]*(?:num|no|#)',
                r'payment[\s_-]*(?:num|no|#)',
                r'(?:^|\s)check(?:$|\s)'
            ],
            'category': 'Check Info'
        },
        'pay_date': {
            'patterns': [
                r'pay[\s_-]*date',
                r'payment[\s_-]*date',
                r'check[\s_-]*date',
                r'date[\s_-]*paid'
            ],
            'category': 'Check Info'
        },
        'pay_period': {
            'patterns': [
                r'pay[\s_-]*period',
                r'period[\s_-]*(?:start|end)',
                r'pp[\s_-]*(?:start|end)'
            ],
            'category': 'Check Info'
        }
    }
    
    def categorize_column(self, column_name: str) -> Tuple[Optional[str], str]:
        """
        Determine which UKG category a column belongs to
        
        Args:
            column_name: The column name to categorize
            
        Returns:
            Tuple of (field_type, category)
        """
        if not column_name or not isinstance(column_name, str):
            return None, 'Uncategorized'
        
        # Normalize column name for matching
        normalized = column_name.lower().strip()
        normalized = re.sub(r'\s+', ' ', normalized)  # Normalize whitespace
        
        # Check each field pattern
        for field_type, field_info in self.FIELD_PATTERNS.items():
            patterns = field_info['patterns']
            category = field_info['category']
            
            for pattern in patterns:
                if re.search(pattern, normalized, re.IGNORECASE):
                    return field_type, category
        
        return None, 'Uncategorized'
    
    def get_all_categories(self) -> List[str]:
        """Get list of all possible categories"""
        categories = set()
        for field_info in self.FIELD_PATTERNS.values():
            categories.add(field_info['category'])
        return sorted(list(categories))


class EnhancedPayrollParser:
    """Railway-compatible parser with PDF parsing and UKG categorization"""
    
    def __init__(self):
        self.categorizer = PayrollFieldCategories()
    
    def parse_pdf(self, pdf_file=None, pdf_content=None, filename=None, pages='all', timeout=30, progress_callback=None, try_all_strategies=False, **kwargs):
        """
        Parse PDF using Railway-compatible strategies (no OCR)
        Accepts any parameter name for maximum compatibility
        
        Args:
            pdf_file: File-like object or path to PDF
            pdf_content: PDF bytes or file-like object
            filename: Filename for the PDF (optional, for display purposes)
            pages: Pages to parse (default: 'all')
            timeout: Timeout in seconds for each strategy
            progress_callback: Optional callback function for progress updates
            try_all_strategies: If True, tries all strategies and returns all results for comparison
            **kwargs: Accept any other parameters for compatibility
            
        Returns:
            Dictionary with 'tables' (list of table info dicts) and 'method' (str)
            If try_all_strategies=True, returns dict with 'all_results' containing results from each strategy
        """
        import time
        start_time = time.time()
        
        # Accept pdf_content, pdf_file, filename, or any other parameter
        pdf_source = pdf_content or pdf_file or kwargs.get('file') or kwargs.get('uploaded_file')
        display_filename = filename or kwargs.get('filename', 'unknown.pdf')
        
        if pdf_source is None:
            return {
                'tables': [], 
                'method': 'none', 
                'error': 'No PDF provided',
                'filename': display_filename,
                'parsed_at': datetime.now().isoformat(),
                'processing_time': 0,
                'success': False,
                'strategies_used': [],
                'metadata': {'total_pages': 0}
            }
        
        # Create temp file if pdf_source is bytes or BytesIO
        temp_file_path = None
        temp_fd = None
        
        try:
            # Check if pdf_source is bytes or BytesIO
            if isinstance(pdf_source, bytes):
                # Create temporary file from bytes
                temp_fd, temp_file_path = tempfile.mkstemp(suffix='.pdf')
                with os.fdopen(temp_fd, 'wb') as f:
                    f.write(pdf_source)
                temp_fd = None  # File is closed after context manager
                pdf_source = temp_file_path
            elif isinstance(pdf_source, BytesIO):
                # Create temporary file from BytesIO
                temp_fd, temp_file_path = tempfile.mkstemp(suffix='.pdf')
                with os.fdopen(temp_fd, 'wb') as f:
                    f.write(pdf_source.getvalue())
                temp_fd = None  # File is closed after context manager
                pdf_source = temp_file_path
            elif hasattr(pdf_source, 'read'):
                # Handle file-like objects
                temp_fd, temp_file_path = tempfile.mkstemp(suffix='.pdf')
                with os.fdopen(temp_fd, 'wb') as f:
                    f.write(pdf_source.read())
                temp_fd = None  # File is closed after context manager
                pdf_source = temp_file_path
            
            # Get PDF metadata (page count)
            total_pages = 0
            try:
                import fitz
                with fitz.open(pdf_source) as doc:
                    total_pages = len(doc)
            except:
                total_pages = 0
            
            # Now pdf_source should be a file path
            all_strategy_results = {} if try_all_strategies else None
            raw_tables = []
            method_used = "none"
            errors = []  # Track errors from each strategy
            strategies_attempted = []
            
            # Strategy 1: Camelot (best for structured tables)
            if progress_callback:
                progress_callback("Trying Camelot parser...")
            strategies_attempted.append('camelot')
            try:
                import camelot
                tables = camelot.read_pdf(pdf_source, pages=pages, flavor='lattice')
                if tables and len(tables) > 0:
                    camelot_tables = [table.df for table in tables]
                    if try_all_strategies:
                        all_strategy_results['camelot'] = {
                            'tables': camelot_tables,
                            'success': True,
                            'num_tables': len(camelot_tables),
                            'error': None
                        }
                    else:
                        raw_tables = camelot_tables
                        method_used = "camelot"
            except Exception as e:
                errors.append(f"Camelot: {str(e)}")
                if try_all_strategies:
                    all_strategy_results['camelot'] = {
                        'tables': [],
                        'success': False,
                        'num_tables': 0,
                        'error': str(e)
                    }
            
            # Strategy 2: Tabula (good for most PDFs)
            if not raw_tables or try_all_strategies:
                if progress_callback:
                    progress_callback("Trying Tabula parser...")
                strategies_attempted.append('tabula')
                try:
                    import tabula
                    tables = tabula.read_pdf(pdf_source, pages=pages, multiple_tables=True)
                    if tables and len(tables) > 0:
                        tabula_tables = [df for df in tables if not df.empty]
                        if tabula_tables:
                            if try_all_strategies:
                                all_strategy_results['tabula'] = {
                                    'tables': tabula_tables,
                                    'success': True,
                                    'num_tables': len(tabula_tables),
                                    'error': None
                                }
                            elif not raw_tables:
                                raw_tables = tabula_tables
                                method_used = "tabula"
                except Exception as e:
                    errors.append(f"Tabula: {str(e)}")
                    if try_all_strategies:
                        all_strategy_results['tabula'] = {
                            'tables': [],
                            'success': False,
                            'num_tables': 0,
                            'error': str(e)
                        }
            
            # Strategy 3: pdfplumber (detailed extraction)
            if not raw_tables or try_all_strategies:
                if progress_callback:
                    progress_callback("Trying pdfplumber parser...")
                strategies_attempted.append('pdfplumber')
                try:
                    import pdfplumber
                    pdfplumber_tables = []
                    with pdfplumber.open(pdf_source) as pdf:
                        for page in pdf.pages:
                            tables = page.extract_tables()
                            if tables:
                                for table in tables:
                                    if table and len(table) > 1:
                                        df = pd.DataFrame(table[1:], columns=table[0])
                                        pdfplumber_tables.append(df)
                        if pdfplumber_tables:
                            if try_all_strategies:
                                all_strategy_results['pdfplumber'] = {
                                    'tables': pdfplumber_tables,
                                    'success': True,
                                    'num_tables': len(pdfplumber_tables),
                                    'error': None
                                }
                            elif not raw_tables:
                                raw_tables = pdfplumber_tables
                                method_used = "pdfplumber"
                except Exception as e:
                    errors.append(f"pdfplumber: {str(e)}")
                    if try_all_strategies:
                        all_strategy_results['pdfplumber'] = {
                            'tables': [],
                            'success': False,
                            'num_tables': 0,
                            'error': str(e)
                        }
            
            # Strategy 4: PyMuPDF (fast text extraction)
            if not raw_tables or try_all_strategies:
                if progress_callback:
                    progress_callback("Trying PyMuPDF parser...")
                strategies_attempted.append('pymupdf')
                try:
                    import fitz
                    pymupdf_tables = []
                    doc = fitz.open(pdf_source)
                    for page in doc:
                        tables = page.find_tables()
                        if tables:
                            for table in tables:
                                df = pd.DataFrame(table.extract())
                                if not df.empty:
                                    pymupdf_tables.append(df)
                    if pymupdf_tables:
                        if try_all_strategies:
                            all_strategy_results['pymupdf'] = {
                                'tables': pymupdf_tables,
                                'success': True,
                                'num_tables': len(pymupdf_tables),
                                'error': None
                            }
                        elif not raw_tables:
                            raw_tables = pymupdf_tables
                            method_used = "pymupdf"
                except Exception as e:
                    errors.append(f"PyMuPDF: {str(e)}")
                    if try_all_strategies:
                        all_strategy_results['pymupdf'] = {
                            'tables': [],
                            'success': False,
                            'num_tables': 0,
                            'error': str(e)
                        }
            
            # If try_all_strategies mode, return comparison results
            if try_all_strategies:
                processing_time = time.time() - start_time
                return {
                    'success': True,
                    'mode': 'comparison',
                    'all_results': all_strategy_results,
                    'filename': display_filename,
                    'parsed_at': datetime.now().isoformat(),
                    'processing_time': processing_time,
                    'strategies_used': strategies_attempted,
                    'metadata': {'total_pages': total_pages}
                }
            
            # Format tables for app.py compatibility
            formatted_tables = []
            for idx, df in enumerate(raw_tables):
                formatted_tables.append({
                    'page': 1,  # We don't track exact page numbers in simplified version
                    'table_num': idx + 1,
                    'row_count': len(df),
                    'col_count': len(df.columns),
                    'data': df
                })
            
            # Identify payroll fields
            identified_fields = {}
            for table_idx, table_info in enumerate(formatted_tables):
                df = table_info['data']
                for col in df.columns:
                    field_type, category = self.categorizer.categorize_column(str(col))
                    if field_type:
                        if field_type not in identified_fields:
                            identified_fields[field_type] = []
                        identified_fields[field_type].append({
                            'table': f"Table_{table_idx + 1}",
                            'column': str(col)
                        })
            
            processing_time = time.time() - start_time
            
            if formatted_tables:
                return {
                    'success': True,
                    'tables': formatted_tables,
                    'filename': display_filename,
                    'method': method_used,
                    'parsed_at': datetime.now().isoformat(),
                    'processing_time': processing_time,
                    'strategies_used': strategies_attempted,
                    'metadata': {'total_pages': total_pages},
                    'identified_fields': identified_fields if identified_fields else None
                }
            else:
                # No tables found
                error_msg = "No parsing method succeeded. Errors: " + " | ".join(errors) if errors else "No tables found in PDF"
                return {
                    'success': False,
                    'tables': [],
                    'filename': display_filename,
                    'method': 'none',
                    'parsed_at': datetime.now().isoformat(),
                    'processing_time': processing_time,
                    'error': error_msg,
                    'strategies_used': strategies_attempted,
                    'metadata': {'total_pages': total_pages},
                    'errors': errors
                }
        
        finally:
            # Clean up temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except Exception as e:
                    print(f"Warning: Could not delete temp file {temp_file_path}: {e}")
            # Clean up file descriptor if it wasn't closed
            if temp_fd is not None:
                try:
                    os.close(temp_fd)
                except Exception:
                    pass
    
    def categorize_dataframe(self, df: pd.DataFrame, table_name: str = "") -> Dict[str, pd.DataFrame]:
        """
        Categorize a dataframe's columns into UKG-ready tabs
        
        Args:
            df: DataFrame to categorize
            table_name: Optional name for tracking source
            
        Returns:
            Dictionary mapping category names to DataFrames
        """
        categorized_data = {cat: pd.DataFrame() for cat in self.categorizer.get_all_categories()}
        categorized_data['Uncategorized'] = pd.DataFrame()
        
        # Track which columns go to which category
        column_mapping = {}
        
        for col in df.columns:
            field_type, category = self.categorizer.categorize_column(str(col))
            column_mapping[col] = {'field_type': field_type, 'category': category}
        
        # Create separate DataFrames for each category
        for col, mapping_info in column_mapping.items():
            category = mapping_info['category']
            if category not in categorized_data:
                categorized_data[category] = pd.DataFrame()
            
            if categorized_data[category].empty:
                categorized_data[category] = df[[col]].copy()
            else:
                categorized_data[category] = pd.concat(
                    [categorized_data[category], df[[col]]], 
                    axis=1
                )
        
        # Remove empty categories
        categorized_data = {k: v for k, v in categorized_data.items() if not v.empty}
        
        return categorized_data
    
    def get_column_categories(self, df: pd.DataFrame) -> Dict[str, Dict[str, str]]:
        """
        Get the auto-detected category for each column
        
        Args:
            df: DataFrame to analyze
            
        Returns:
            Dict mapping column names to {'field_type': str, 'category': str}
        """
        column_mapping = {}
        for col in df.columns:
            field_type, category = self.categorizer.categorize_column(str(col))
            column_mapping[str(col)] = {'field_type': field_type, 'category': category}
        return column_mapping
    
    def categorize_with_overrides(self, df: pd.DataFrame, overrides: Dict[str, str] = None, table_name: str = "") -> Dict[str, pd.DataFrame]:
        """
        Categorize with manual overrides for specific columns
        
        Args:
            df: DataFrame to categorize
            overrides: Dict mapping column names to category overrides
                      e.g. {'Column1': 'Earnings', 'Column2': 'Deductions'}
            table_name: Optional name for tracking source
            
        Returns:
            Dictionary mapping category names to DataFrames (5 tabs: Employee Info, Earnings, Deductions, Taxes, Check Info)
        """
        overrides = overrides or {}
        categorized_data = {cat: pd.DataFrame() for cat in self.categorizer.get_all_categories()}
        categorized_data['Uncategorized'] = pd.DataFrame()
        
        # Track which columns go to which category
        column_mapping = {}
        
        for col in df.columns:
            # Check if there's a manual override
            if str(col) in overrides:
                category = overrides[str(col)]
                field_type = None  # Manual override, no auto-detected type
            else:
                field_type, category = self.categorizer.categorize_column(str(col))
            
            column_mapping[col] = {'field_type': field_type, 'category': category}
        
        # Create separate DataFrames for each category
        for col, mapping_info in column_mapping.items():
            category = mapping_info['category']
            if category not in categorized_data:
                categorized_data[category] = pd.DataFrame()
            
            if categorized_data[category].empty:
                categorized_data[category] = df[[col]].copy()
            else:
                categorized_data[category] = pd.concat(
                    [categorized_data[category], df[[col]]], 
                    axis=1
                )
        
        # Remove empty categories
        categorized_data = {k: v for k, v in categorized_data.items() if not v.empty}
        
        return categorized_data
    
    def export_to_ukg_excel(self, categorized_data: Dict[str, pd.DataFrame], 
                           output_path: str, source_filename: str = ""):
        """
        Export categorized data to a UKG-ready Excel file with 5 organized tabs + Summary
        
        Tabs created (in order):
        1. Employee Info
        2. Earnings
        3. Deductions
        4. Taxes
        5. Check Info
        6. Metadata (Summary)
        
        Args:
            categorized_data: Dictionary mapping category names to DataFrames
            output_path: Path where Excel file should be saved
            source_filename: Original PDF filename for metadata
            
        Returns:
            Path to created Excel file
        """
        # Define the correct order for UKG tabs
        tab_order = ['Employee Info', 'Earnings', 'Deductions', 'Taxes', 'Check Info', 'Uncategorized']
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Write each category to its own sheet in the correct order
            for category in tab_order:
                if category in categorized_data and not categorized_data[category].empty:
                    # Clean sheet name (Excel has 31 char limit)
                    sheet_name = category[:31]
                    categorized_data[category].to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Add metadata/summary sheet at the end
            metadata = pd.DataFrame({
                'Property': ['Source File', 'Parsed At', 'Total Columns', 'Categories', 'Total Rows'],
                'Value': [
                    source_filename,
                    datetime.now().isoformat(),
                    sum(len(df.columns) for df in categorized_data.values()),
                    ', '.join([k for k in tab_order if k in categorized_data and not categorized_data[k].empty]),
                    sum(len(df) for df in categorized_data.values())
                ]
            })
            metadata.to_excel(writer, sheet_name='Metadata', index=False)
        
        return output_path


def process_parsed_pdf_for_ukg(parsed_result_or_tables, parser: EnhancedPayrollParser = None, filename: str = "parsed_payroll.pdf", column_overrides: Dict[str, str] = None):
    """
    Process a parsed PDF result and categorize for UKG, returning Excel buffer with 5 tabs
    
    Tabs created (in order):
    1. Employee Info
    2. Earnings  
    3. Deductions
    4. Taxes
    5. Check Info
    6. Metadata (Summary)
    
    Args:
        parsed_result_or_tables: Either a result dict from parse_pdf() OR a list of table dicts
        parser: EnhancedPayrollParser instance (creates new one if None)
        filename: Original filename for metadata
        column_overrides: Optional dict mapping column names to categories for manual remapping
                         e.g. {'Column1': 'Earnings', 'Column2': 'Deductions'}
        
    Returns:
        BytesIO buffer containing the UKG-formatted Excel file with 5 organized tabs
    """
    if parser is None:
        parser = EnhancedPayrollParser()
    
    column_overrides = column_overrides or {}
    
    # Handle both input formats
    if isinstance(parsed_result_or_tables, dict):
        # It's a full parsed result
        parsed_result = parsed_result_or_tables
        if not parsed_result.get('success') or not parsed_result.get('tables'):
            # Return empty Excel with error message
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                error_df = pd.DataFrame({
                    'Error': [parsed_result.get('error', 'No tables found')]
                })
                error_df.to_excel(writer, sheet_name='Error', index=False)
            output.seek(0)
            return output
        
        table_list = parsed_result['tables']
        filename = parsed_result.get('filename', filename)
    elif isinstance(parsed_result_or_tables, list):
        # It's a list of tables (either table dicts or DataFrames)
        table_list = parsed_result_or_tables
    else:
        # Unknown format
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            error_df = pd.DataFrame({
                'Error': ['Invalid input format']
            })
            error_df.to_excel(writer, sheet_name='Error', index=False)
        output.seek(0)
        return output
    
    # Extract DataFrames from table list
    all_dataframes = []
    for item in table_list:
        if isinstance(item, dict) and 'data' in item:
            # It's a table dict from parse_pdf
            all_dataframes.append(item['data'])
        elif isinstance(item, pd.DataFrame):
            # It's already a DataFrame
            all_dataframes.append(item)
    
    if not all_dataframes:
        # No valid tables found
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            error_df = pd.DataFrame({
                'Error': ['No valid tables found to process']
            })
            error_df.to_excel(writer, sheet_name='Error', index=False)
        output.seek(0)
        return output
    
    # Categorize all tables (with overrides if provided)
    all_categorized = {}
    for i, table_df in enumerate(all_dataframes):
        table_name = f"Table_{i+1}"
        
        # Use categorize_with_overrides if we have overrides, otherwise use regular categorize
        if column_overrides:
            categorized = parser.categorize_with_overrides(table_df, column_overrides, table_name)
        else:
            categorized = parser.categorize_dataframe(table_df, table_name)
        
        # Merge categorized data
        for category, df in categorized.items():
            if category not in all_categorized:
                all_categorized[category] = df.copy()
            else:
                # Concatenate rows from multiple tables
                all_categorized[category] = pd.concat(
                    [all_categorized[category], df],
                    axis=0,
                    ignore_index=True
                )
    
    # Define the correct order for UKG tabs
    tab_order = ['Employee Info', 'Earnings', 'Deductions', 'Taxes', 'Check Info', 'Uncategorized']
    
    # Create Excel file in memory with tabs in correct order
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Write each category to its own sheet in the correct order
        for category in tab_order:
            if category in all_categorized and not all_categorized[category].empty:
                # Clean sheet name (Excel has 31 char limit)
                sheet_name = category[:31]
                all_categorized[category].to_excel(writer, sheet_name=sheet_name, index=False)
        
        # Add metadata/summary sheet at the end
        metadata = pd.DataFrame({
            'Property': ['Source File', 'Processed At', 'Total Columns', 'Categories', 'Total Rows', 'Manual Overrides'],
            'Value': [
                filename,
                datetime.now().isoformat(),
                sum(len(df.columns) for df in all_categorized.values()),
                ', '.join([k for k in tab_order if k in all_categorized and not all_categorized[k].empty]),
                sum(len(df) for df in all_categorized.values()),
                'Yes' if column_overrides else 'No'
            ]
        })
        metadata.to_excel(writer, sheet_name='Metadata', index=False)
    
    output.seek(0)
    return output


# Backwards compatibility
SecurePayrollParser = EnhancedPayrollParser
create_ukg_excel_export = process_parsed_pdf_for_ukg  # Alias for backwards compatibility
