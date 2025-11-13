"""
Railway-Compatible PDF Parser with UKG Categorization
Works without OCR or image processing dependencies
"""

import re
from typing import Dict, List, Tuple, Optional
import pandas as pd
from io import BytesIO


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
                r'bonus(?:es)?',
                r'incentive',
                r'commission',
                r'award'
            ],
            'category': 'Earnings'
        },
        
        # Deductions
        'health_insurance': {
            'patterns': [
                r'health[\s_-]*(?:ins|insurance)',
                r'medical[\s_-]*(?:ins|insurance)',
                r'dental',
                r'vision',
                r'benefits'
            ],
            'category': 'Deductions'
        },
        'retirement': {
            'patterns': [
                r'401[\s_-]*k',
                r'retirement',
                r'pension',
                r'roth',
                r'ira'
            ],
            'category': 'Deductions'
        },
        'garnishment': {
            'patterns': [
                r'garnish(?:ment)?',
                r'wage[\s_-]*attachment',
                r'child[\s_-]*support',
                r'levy'
            ],
            'category': 'Deductions'
        },
        'other_deductions': {
            'patterns': [
                r'deduction',
                r'withholding',
                r'union[\s_-]*dues',
                r'parking',
                r'loan'
            ],
            'category': 'Deductions'
        },
        
        # Taxes
        'federal_tax': {
            'patterns': [
                r'fed(?:eral)?[\s_-]*(?:tax|wh|withhold)',
                r'fit',
                r'federal[\s_-]*income',
                r'fed[\s_-]*inc'
            ],
            'category': 'Taxes'
        },
        'state_tax': {
            'patterns': [
                r'state[\s_-]*(?:tax|wh|withhold)',
                r'sit',
                r'state[\s_-]*income',
                r'st[\s_-]*tax'
            ],
            'category': 'Taxes'
        },
        'fica': {
            'patterns': [
                r'fica',
                r'social[\s_-]*security[\s_-]*tax',
                r'ss[\s_-]*tax',
                r'oasdi'
            ],
            'category': 'Taxes'
        },
        'medicare': {
            'patterns': [
                r'medicare',
                r'med[\s_-]*tax',
                r'mc[\s_-]*tax'
            ],
            'category': 'Taxes'
        },
        'local_tax': {
            'patterns': [
                r'local[\s_-]*tax',
                r'city[\s_-]*tax',
                r'county[\s_-]*tax',
                r'municipal'
            ],
            'category': 'Taxes'
        },
        
        # Check Info
        'check_number': {
            'patterns': [
                r'check[\s_-]*(?:num|no|#)',
                r'chk[\s_-]*(?:num|no|#)',
                r'payment[\s_-]*(?:num|no|#)',
                r'(?:^|\s)check(?:$|\s)'
            ],
            'category': 'Check Info'
        },
        'check_date': {
            'patterns': [
                r'check[\s_-]*date',
                r'pay[\s_-]*date',
                r'payment[\s_-]*date',
                r'issue[\s_-]*date'
            ],
            'category': 'Check Info'
        },
        'pay_period': {
            'patterns': [
                r'pay[\s_-]*period',
                r'pp[\s_-]*(?:start|end)',
                r'period[\s_-]*(?:start|end|ending)',
                r'week[\s_-]*ending'
            ],
            'category': 'Check Info'
        },
        'net_pay': {
            'patterns': [
                r'net[\s_-]*(?:pay|amount|wages)',
                r'take[\s_-]*home',
                r'net',
                r'amount[\s_-]*paid'
            ],
            'category': 'Check Info'
        }
    }
    
    @classmethod
    def get_all_categories(cls) -> List[str]:
        """Returns list of all UKG categories"""
        return ['Employee Info', 'Earnings', 'Deductions', 'Taxes', 'Check Info']
    
    @classmethod
    def categorize_column(cls, column_name: str) -> Tuple[Optional[str], str]:
        """
        Categorize a column name into a UKG category
        
        Args:
            column_name: The column header to categorize
            
        Returns:
            Tuple of (field_type, category) or (None, 'Uncategorized')
        """
        if not column_name or not isinstance(column_name, str):
            return None, 'Uncategorized'
        
        # Clean the column name for matching
        clean_name = column_name.lower().strip()
        
        # Try to match against all field patterns
        for field_type, field_info in cls.FIELD_PATTERNS.items():
            for pattern in field_info['patterns']:
                if re.search(pattern, clean_name, re.IGNORECASE):
                    return field_type, field_info['category']
        
        return None, 'Uncategorized'


class EnhancedPayrollParser:
    """Railway-compatible parser with PDF parsing and UKG categorization"""
    
    def __init__(self):
        self.categorizer = PayrollFieldCategories()
    
    def parse_pdf(self, pdf_file=None, pdf_content=None, filename=None, pages='all', timeout=30, **kwargs):
        """
        Parse PDF using Railway-compatible strategies (no OCR)
        Accepts any parameter name for maximum compatibility
        
        Args:
            pdf_file: File-like object or path to PDF
            pdf_content: File-like object or path to PDF
            filename: File-like object or path to PDF
            pages: Pages to parse (default: 'all')
            timeout: Timeout in seconds for each strategy
            **kwargs: Accept any other parameters for compatibility
            
        Returns:
            Dictionary with 'tables' (list of DataFrames) and 'method' (str)
        """
        # Accept pdf_content, pdf_file, filename, or any other parameter
        pdf_source = pdf_content or pdf_file or filename or kwargs.get('file') or kwargs.get('uploaded_file')
        
        if pdf_source is None:
            from datetime import datetime
            return {
                'tables': [], 
                'method': 'none', 
                'error': 'No PDF provided',
                'parsed_at': datetime.now().isoformat(),
                'num_tables': 0,
                'num_rows': 0,
                'success': False
            }
        
        all_tables = []
        method_used = "none"
        
        # Strategy 1: Camelot (best for structured tables)
        try:
            import camelot
            tables = camelot.read_pdf(pdf_source, pages=pages, flavor='lattice')
            if tables and len(tables) > 0:
                all_tables = [table.df for table in tables]
                method_used = "camelot"
                from datetime import datetime
                return {
                    'tables': all_tables, 
                    'method': method_used,
                    'parsed_at': datetime.now().isoformat(),
                    'num_tables': len(all_tables),
                    'num_rows': sum(len(df) for df in all_tables),
                    'success': True
                }
        except Exception as e:
            pass
        
        # Strategy 2: Tabula (good for most PDFs)
        try:
            import tabula
            tables = tabula.read_pdf(pdf_source, pages=pages, multiple_tables=True)
            if tables and len(tables) > 0:
                all_tables = [df for df in tables if not df.empty]
                if all_tables:
                    method_used = "tabula"
                    from datetime import datetime
                    return {
                        'tables': all_tables, 
                        'method': method_used,
                        'parsed_at': datetime.now().isoformat(),
                        'num_tables': len(all_tables),
                        'num_rows': sum(len(df) for df in all_tables),
                        'success': True
                    }
        except Exception as e:
            pass
        
        # Strategy 3: pdfplumber (detailed extraction)
        try:
            import pdfplumber
            with pdfplumber.open(pdf_source) as pdf:
                for page in pdf.pages:
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            if table and len(table) > 1:
                                df = pd.DataFrame(table[1:], columns=table[0])
                                all_tables.append(df)
                if all_tables:
                    method_used = "pdfplumber"
                    from datetime import datetime
                    return {
                        'tables': all_tables, 
                        'method': method_used,
                        'parsed_at': datetime.now().isoformat(),
                        'num_tables': len(all_tables),
                        'num_rows': sum(len(df) for df in all_tables),
                        'success': True
                    }
        except Exception as e:
            pass
        
        # Strategy 4: PyMuPDF (fast text extraction)
        try:
            import fitz
            doc = fitz.open(pdf_source)
            for page in doc:
                tables = page.find_tables()
                if tables:
                    for table in tables:
                        df = pd.DataFrame(table.extract())
                        if not df.empty:
                            all_tables.append(df)
            if all_tables:
                method_used = "pymupdf"
                from datetime import datetime
                return {
                    'tables': all_tables, 
                    'method': method_used,
                    'parsed_at': datetime.now().isoformat(),
                    'num_tables': len(all_tables),
                    'num_rows': sum(len(df) for df in all_tables),
                    'success': True
                }
        except Exception as e:
            pass
        
        # Note: OCR strategy removed for Railway compatibility
        
        # If nothing worked, return empty result with all expected fields
        from datetime import datetime
        return {
            'tables': [], 
            'method': 'none',
            'parsed_at': datetime.now().isoformat(),
            'num_tables': 0,
            'num_rows': 0,
            'success': False,
            'error': 'No parsing method succeeded'
        }
    
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
            column_mapping[col] = (field_type, category)
        
        # Split DataFrame by category
        for category in categorized_data.keys():
            category_cols = [col for col, (_, cat) in column_mapping.items() if cat == category]
            if category_cols:
                categorized_data[category] = df[category_cols].copy()
        
        return categorized_data
    
    def merge_categorized_data(self, all_tables: List[pd.DataFrame], 
                               table_names: List[str] = None) -> Dict[str, pd.DataFrame]:
        """
        Process multiple tables and merge them by category
        
        Args:
            all_tables: List of DataFrames from different PDF pages/tables
            table_names: Optional list of source names for tracking
            
        Returns:
            Dictionary mapping category names to merged DataFrames
        """
        if table_names is None:
            table_names = [f"Table_{i+1}" for i in range(len(all_tables))]
        
        # Initialize merged categories
        merged_categories = {cat: [] for cat in self.categorizer.get_all_categories()}
        merged_categories['Uncategorized'] = []
        
        # Categorize each table
        for df, name in zip(all_tables, table_names):
            categorized = self.categorize_dataframe(df, name)
            
            for category, cat_df in categorized.items():
                if not cat_df.empty:
                    # Add source tracking column
                    cat_df_copy = cat_df.copy()
                    cat_df_copy['Source_Table'] = name
                    merged_categories[category].append(cat_df_copy)
        
        # Merge DataFrames within each category
        final_categories = {}
        for category, df_list in merged_categories.items():
            if df_list:
                # Try to concatenate intelligently
                final_categories[category] = self._smart_merge(df_list, category)
            else:
                # Create empty DataFrame with appropriate structure
                final_categories[category] = pd.DataFrame()
        
        # Remove empty categories except Uncategorized
        final_categories = {
            cat: df for cat, df in final_categories.items() 
            if not df.empty or cat == 'Uncategorized'
        }
        
        return final_categories
    
    def _smart_merge(self, df_list: List[pd.DataFrame], category: str) -> pd.DataFrame:
        """
        Intelligently merge DataFrames within the same category
        
        Args:
            df_list: List of DataFrames to merge
            category: Category name for context
            
        Returns:
            Merged DataFrame
        """
        if len(df_list) == 1:
            return df_list[0]
        
        # Check if DataFrames have the same structure
        first_cols = set(df_list[0].columns) - {'Source_Table'}
        same_structure = all(set(df.columns) - {'Source_Table'} == first_cols for df in df_list)
        
        if same_structure and len(df_list[0]) > 0:
            # Same structure - vertical concatenation (stacking rows)
            try:
                return pd.concat(df_list, ignore_index=True, sort=False)
            except Exception:
                pass
        
        # Different structures - horizontal concatenation or fallback
        try:
            # Try to merge on common columns (like Employee ID)
            common_cols = set.intersection(*[set(df.columns) for df in df_list])
            common_cols -= {'Source_Table'}
            
            if common_cols and category != 'Uncategorized':
                # Merge on common columns
                result = df_list[0]
                for df in df_list[1:]:
                    result = pd.merge(result, df, on=list(common_cols), how='outer', suffixes=('', '_dup'))
                return result
            else:
                # Just concatenate vertically with different columns
                return pd.concat(df_list, ignore_index=True, sort=False)
        except Exception:
            # Fallback: just concatenate
            return pd.concat(df_list, ignore_index=True, sort=False)


def create_ukg_excel_export(categorized_data: Dict[str, pd.DataFrame], 
                            filename: str = "UKG_Import_Data.xlsx") -> BytesIO:
    """
    Create an Excel file with UKG-ready tabs
    
    Args:
        categorized_data: Dictionary mapping category names to DataFrames
        filename: Name for the Excel file (for metadata)
        
    Returns:
        BytesIO object containing the Excel file
    """
    output = BytesIO()
    
    # Create Excel writer with xlsxwriter engine for formatting
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        
        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4472C4',
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        # Tab order based on UKG workflow
        tab_order = [
            'Employee Info',
            'Earnings', 
            'Deductions',
            'Taxes',
            'Check Info',
            'Uncategorized'
        ]
        
        # Write each category to its tab
        for category in tab_order:
            if category in categorized_data and not categorized_data[category].empty:
                df = categorized_data[category]
                
                # Clean up duplicate columns
                df = df.loc[:, ~df.columns.duplicated()]
                
                # Write to Excel
                df.to_excel(writer, sheet_name=category, index=False, startrow=1)
                
                # Get the worksheet
                worksheet = writer.sheets[category]
                
                # Format header row
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(1, col_num, value, header_format)
                
                # Add title row
                title_format = workbook.add_format({
                    'bold': True,
                    'font_size': 14,
                    'bg_color': '#D9E1F2',
                    'border': 1
                })
                worksheet.merge_range(0, 0, 0, len(df.columns)-1 if len(df.columns) > 0 else 0, 
                                     f"{category} - UKG Import Data", title_format)
                
                # Auto-adjust column widths
                for idx, col in enumerate(df.columns):
                    max_length = max(
                        df[col].astype(str).apply(len).max(),
                        len(str(col))
                    )
                    worksheet.set_column(idx, idx, min(max_length + 2, 50))
        
        # Add a summary sheet
        summary_data = []
        for category in tab_order:
            if category in categorized_data:
                df = categorized_data[category]
                summary_data.append({
                    'Category': category,
                    'Rows': len(df),
                    'Columns': len(df.columns) if not df.empty else 0,
                    'Fields': ', '.join(df.columns.tolist()[:5]) + ('...' if len(df.columns) > 5 else '')
                })
        
        summary_df = pd.DataFrame(summary_data)
        if not summary_df.empty:
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Format summary sheet
            summary_sheet = writer.sheets['Summary']
            for col_num, value in enumerate(summary_df.columns.values):
                summary_sheet.write(0, col_num, value, header_format)
            
            # Auto-adjust columns
            for idx, col in enumerate(summary_df.columns):
                max_length = max(
                    summary_df[col].astype(str).apply(len).max(),
                    len(str(col))
                )
                summary_sheet.set_column(idx, idx, min(max_length + 2, 50))
    
    output.seek(0)
    return output


def process_parsed_pdf_for_ukg(all_dataframes: List[pd.DataFrame], 
                               table_names: List[str] = None) -> BytesIO:
    """
    Complete pipeline to process parsed PDF data into UKG-ready Excel
    
    Args:
        all_dataframes: List of DataFrames from PDF parser
        table_names: Optional source names for tracking
        
    Returns:
        BytesIO object with UKG-ready Excel file
    """
    parser = EnhancedPayrollParser()
    
    # Categorize and merge all tables
    categorized_data = parser.merge_categorized_data(all_dataframes, table_names)
    
    # Create Excel export
    excel_file = create_ukg_excel_export(categorized_data)
    
    return excel_file


# Backwards compatibility alias
SecurePayrollParser = EnhancedPayrollParser
