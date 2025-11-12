"""
Advanced PDF Parser with Custom Mapping Support
Supports downloadable JSON configs and custom field mappings
"""

import io
import json
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import pdfplumber
from datetime import datetime

class AdvancedPDFParser:
    """
    Advanced PDF parser with custom mapping configuration support.
    Allows consultants to define custom field mappings per customer.
    """
    
    # Default field patterns for auto-detection
    DEFAULT_PAY_REGISTER_FIELDS = {
        'employee_id': ['emp id', 'employee id', 'empid', 'id', 'employee number', 'emp #', 'ee id'],
        'employee_name': ['name', 'employee name', 'emp name', 'full name', 'employee'],
        'gross_pay': ['gross', 'gross pay', 'gross earnings', 'total gross'],
        'net_pay': ['net', 'net pay', 'take home', 'net amount'],
        'hours': ['hours', 'hours worked', 'regular hours', 'total hours', 'hrs'],
        'rate': ['rate', 'pay rate', 'hourly rate', 'hr rate'],
        'deductions': ['deductions', 'total deductions', 'withheld'],
        'taxes': ['tax', 'taxes', 'federal', 'fica', 'medicare', 'withholding'],
        'ytd': ['ytd', 'year to date', 'ytd total'],
        'department': ['dept', 'department', 'cost center', 'division'],
        'position': ['position', 'job', 'title', 'job title'],
        'date': ['date', 'pay date', 'check date', 'period']
    }
    
    def __init__(self):
        self.custom_mapping = None
        self.parsing_results = {}
    
    def parse_pdf(
        self, 
        pdf_content: bytes, 
        filename: str,
        custom_mapping: Optional[Dict] = None,
        extract_all_tables: bool = True
    ) -> Dict[str, Any]:
        """
        Parse PDF and extract tables with optional custom mapping.
        
        Args:
            pdf_content: PDF file content as bytes
            filename: Name of the PDF file
            custom_mapping: Optional custom field mapping dictionary
            extract_all_tables: Whether to extract all tables or stop after first
            
        Returns:
            Dictionary containing parsing results
        """
        try:
            pdf_file = io.BytesIO(pdf_content)
            
            with pdfplumber.open(pdf_file) as pdf:
                total_pages = len(pdf.pages)
                all_tables = []
                all_text = []
                
                # Extract from each page
                for page_num, page in enumerate(pdf.pages, 1):
                    # Extract text
                    page_text = page.extract_text()
                    if page_text:
                        all_text.append(page_text)
                    
                    # Extract tables
                    tables = page.extract_tables()
                    if tables:
                        for table_num, table in enumerate(tables, 1):
                            if table and len(table) > 0:
                                all_tables.append({
                                    'page': page_num,
                                    'table_num': table_num,
                                    'data': table
                                })
                
                # Analyze document
                is_pay_register = self._detect_pay_register(all_text, all_tables)
                
                # Convert tables to DataFrames
                dataframes = []
                for table_info in all_tables:
                    df = self._table_to_dataframe(table_info['data'])
                    if df is not None and not df.empty:
                        df['source_page'] = table_info['page']
                        df['source_table'] = table_info['table_num']
                        dataframes.append(df)
                
                # Apply field mapping if provided or auto-detect
                mapped_data = []
                if custom_mapping:
                    for df in dataframes:
                        mapped_df = self._apply_custom_mapping(df, custom_mapping)
                        mapped_data.append(mapped_df)
                elif is_pay_register:
                    for df in dataframes:
                        mapped_df = self._auto_detect_fields(df)
                        mapped_data.append(mapped_df)
                else:
                    mapped_data = dataframes
                
                # Calculate statistics
                total_records = sum(len(df) for df in dataframes)
                
                return {
                    'success': True,
                    'filename': filename,
                    'total_pages': total_pages,
                    'tables_found': len(all_tables),
                    'is_pay_register': is_pay_register,
                    'total_records': total_records,
                    'dataframes': mapped_data,
                    'raw_dataframes': dataframes,
                    'detected_fields': self._get_detected_fields(dataframes),
                    'parsing_metadata': {
                        'parsed_at': datetime.now().isoformat(),
                        'custom_mapping_used': custom_mapping is not None,
                        'pages_processed': total_pages
                    }
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'filename': filename
            }
    
    def _table_to_dataframe(self, table: List[List]) -> Optional[pd.DataFrame]:
        """Convert extracted table to DataFrame"""
        try:
            if not table or len(table) < 2:
                return None
            
            # First row as headers
            headers = table[0]
            data = table[1:]
            
            # Clean headers
            headers = [str(h).strip() if h else f'Column_{i}' for i, h in enumerate(headers)]
            
            # Create DataFrame
            df = pd.DataFrame(data, columns=headers)
            
            # Remove empty rows
            df = df.dropna(how='all')
            
            return df
        except Exception as e:
            return None
    
    def _detect_pay_register(self, texts: List[str], tables: List[Dict]) -> bool:
        """Detect if document is a pay register"""
        keywords = [
            'payroll', 'pay register', 'earnings', 'gross pay', 'net pay',
            'deductions', 'employee', 'hours worked', 'pay period'
        ]
        
        # Check text content
        text_content = ' '.join(texts).lower()
        keyword_matches = sum(1 for kw in keywords if kw in text_content)
        
        # Check table headers
        if tables:
            for table_info in tables:
                table = table_info['data']
                if table and len(table) > 0:
                    headers = ' '.join([str(h).lower() for h in table[0] if h])
                    keyword_matches += sum(1 for kw in keywords if kw in headers)
        
        return keyword_matches >= 3
    
    def _auto_detect_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Auto-detect pay register fields in DataFrame"""
        field_mapping = {}
        
        for col in df.columns:
            col_lower = str(col).lower().strip()
            
            # Check against known patterns
            for field_name, patterns in self.DEFAULT_PAY_REGISTER_FIELDS.items():
                for pattern in patterns:
                    if pattern in col_lower:
                        field_mapping[col] = field_name
                        break
                if col in field_mapping:
                    break
        
        # Store detected mapping
        df.attrs['field_mapping'] = field_mapping
        return df
    
    def _apply_custom_mapping(self, df: pd.DataFrame, mapping: Dict[str, str]) -> pd.DataFrame:
        """Apply custom field mapping to DataFrame"""
        # Create new DataFrame with mapped column names
        renamed_df = df.copy()
        
        # Apply mapping
        for original_col, target_field in mapping.items():
            if original_col in df.columns:
                renamed_df = renamed_df.rename(columns={original_col: target_field})
        
        renamed_df.attrs['custom_mapping_applied'] = True
        return renamed_df
    
    def _get_detected_fields(self, dataframes: List[pd.DataFrame]) -> Dict[str, List[str]]:
        """Get all detected fields across all DataFrames"""
        all_fields = {}
        
        for df in dataframes:
            if hasattr(df, 'attrs') and 'field_mapping' in df.attrs:
                mapping = df.attrs['field_mapping']
                for original, detected in mapping.items():
                    if detected not in all_fields:
                        all_fields[detected] = []
                    all_fields[detected].append(original)
        
        return all_fields
    
    def generate_mapping_config(self, pdf_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Generate a mapping configuration template based on PDF structure.
        This can be downloaded, edited, and re-uploaded.
        """
        # Parse PDF to get structure
        result = self.parse_pdf(pdf_content, filename)
        
        if not result['success']:
            return result
        
        # Generate mapping template
        mapping_config = {
            'document_info': {
                'filename': filename,
                'generated_at': datetime.now().isoformat(),
                'total_pages': result['total_pages'],
                'tables_found': result['tables_found'],
                'is_pay_register': result['is_pay_register']
            },
            'field_mappings': {},
            'instructions': {
                'how_to_use': 'Edit the field_mappings section to map source columns to target fields',
                'example': {'Original Column Name': 'target_field_name'},
                'available_fields': list(self.DEFAULT_PAY_REGISTER_FIELDS.keys())
            },
            'detected_columns': []
        }
        
        # Add all detected columns
        all_columns = set()
        for df in result['raw_dataframes']:
            all_columns.update(df.columns)
        
        mapping_config['detected_columns'] = sorted(list(all_columns))
        
        # Add suggested mappings based on auto-detection
        if result['detected_fields']:
            suggestions = {}
            for target_field, source_columns in result['detected_fields'].items():
                for source_col in source_columns:
                    suggestions[source_col] = target_field
            mapping_config['field_mappings'] = suggestions
        
        return {
            'success': True,
            'config': mapping_config,
            'filename': filename
        }
    
    def export_to_excel(
        self, 
        dataframes: List[pd.DataFrame], 
        filename: str,
        include_summary: bool = True
    ) -> bytes:
        """Export parsed data to Excel with multiple sheets"""
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Write each table to separate sheet
            for i, df in enumerate(dataframes, 1):
                sheet_name = f'Table_{i}'
                if 'source_page' in df.columns:
                    page = df['source_page'].iloc[0]
                    sheet_name = f'Page{page}_T{i}'
                
                df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Add summary sheet if requested
            if include_summary and dataframes:
                summary_data = {
                    'Metric': ['Total Tables', 'Total Records', 'Total Columns'],
                    'Value': [
                        len(dataframes),
                        sum(len(df) for df in dataframes),
                        sum(len(df.columns) for df in dataframes)
                    ]
                }
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        output.seek(0)
        return output.getvalue()


def create_mapping_editor_html(mapping_config: Dict[str, Any]) -> str:
    """
    Generate an HTML file that allows offline editing of field mappings.
    """
    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>XLR8 PDF Mapping Editor</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
        }}
        
        .content {{
            padding: 30px;
        }}
        
        .info-box {{
            background: #f8f9fa;
            border-left: 4px solid #28a745;
            padding: 20px;
            margin-bottom: 30px;
            border-radius: 5px;
        }}
        
        .info-box h3 {{
            color: #28a745;
            margin-bottom: 10px;
        }}
        
        .info-row {{
            display: flex;
            justify-content: space-between;
            padding: 5px 0;
        }}
        
        .mapping-section {{
            margin-top: 30px;
        }}
        
        .mapping-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        
        .mapping-table th,
        .mapping-table td {{
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid #dee2e6;
        }}
        
        .mapping-table th {{
            background: #28a745;
            color: white;
            font-weight: 600;
        }}
        
        .mapping-table tr:hover {{
            background: #f8f9fa;
        }}
        
        input[type="text"],
        select {{
            width: 100%;
            padding: 10px;
            border: 2px solid #dee2e6;
            border-radius: 5px;
            font-size: 14px;
        }}
        
        input[type="text"]:focus,
        select:focus {{
            outline: none;
            border-color: #28a745;
        }}
        
        .button-group {{
            margin-top: 30px;
            display: flex;
            gap: 15px;
            justify-content: center;
        }}
        
        button {{
            padding: 15px 40px;
            font-size: 16px;
            font-weight: 600;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            transition: all 0.3s;
        }}
        
        .btn-primary {{
            background: #28a745;
            color: white;
        }}
        
        .btn-primary:hover {{
            background: #218838;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(40, 167, 69, 0.3);
        }}
        
        .btn-secondary {{
            background: #6c757d;
            color: white;
        }}
        
        .btn-secondary:hover {{
            background: #5a6268;
        }}
        
        .instructions {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 20px;
            margin-top: 30px;
            border-radius: 5px;
        }}
        
        .instructions h4 {{
            color: #856404;
            margin-bottom: 10px;
        }}
        
        .instructions ul {{
            margin-left: 20px;
            margin-top: 10px;
        }}
        
        .instructions li {{
            margin: 5px 0;
            color: #856404;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚡ XLR8 PDF Mapping Editor</h1>
            <p>Configure custom field mappings for pay register parsing</p>
        </div>
        
        <div class="content">
            <div class="info-box">
                <h3>📄 Document Information</h3>
                <div class="info-row">
                    <strong>Filename:</strong>
                    <span id="filename">{mapping_config['document_info']['filename']}</span>
                </div>
                <div class="info-row">
                    <strong>Pages:</strong>
                    <span>{mapping_config['document_info']['total_pages']}</span>
                </div>
                <div class="info-row">
                    <strong>Tables Found:</strong>
                    <span>{mapping_config['document_info']['tables_found']}</span>
                </div>
                <div class="info-row">
                    <strong>Pay Register:</strong>
                    <span>{"Yes" if mapping_config['document_info']['is_pay_register'] else "No"}</span>
                </div>
            </div>
            
            <div class="instructions">
                <h4>📋 Instructions</h4>
                <ul>
                    <li>Review the detected columns below</li>
                    <li>Map each source column to a target field using the dropdowns</li>
                    <li>You can also type custom field names</li>
                    <li>Click "Download Configuration" to save as JSON</li>
                    <li>Upload the JSON back to XLR8 to apply the mappings</li>
                </ul>
            </div>
            
            <div class="mapping-section">
                <h3>🎯 Field Mappings</h3>
                <table class="mapping-table">
                    <thead>
                        <tr>
                            <th>Source Column (from PDF)</th>
                            <th>Target Field (UKG/System)</th>
                            <th>Auto-Detected</th>
                        </tr>
                    </thead>
                    <tbody id="mappingTableBody">
                    </tbody>
                </table>
            </div>
            
            <div class="button-group">
                <button class="btn-primary" onclick="downloadConfig()">
                    💾 Download Configuration (JSON)
                </button>
                <button class="btn-secondary" onclick="addCustomMapping()">
                    ➕ Add Custom Mapping
                </button>
            </div>
        </div>
    </div>
    
    <script>
        const configData = {json.dumps(mapping_config, indent=2)};
        
        const availableFields = [
            'employee_id', 'employee_name', 'gross_pay', 'net_pay', 
            'hours', 'rate', 'deductions', 'taxes', 'ytd', 
            'department', 'position', 'date', 'custom'
        ];
        
        function initializeMappings() {{
            const tbody = document.getElementById('mappingTableBody');
            tbody.innerHTML = '';
            
            const detectedColumns = configData.detected_columns || [];
            const existingMappings = configData.field_mappings || {{}};
            
            detectedColumns.forEach(column => {{
                addMappingRow(column, existingMappings[column] || '');
            }});
        }}
        
        function addMappingRow(sourceColumn, targetField) {{
            const tbody = document.getElementById('mappingTableBody');
            const row = tbody.insertRow();
            
            const cell1 = row.insertCell(0);
            const cell2 = row.insertCell(1);
            const cell3 = row.insertCell(2);
            
            cell1.textContent = sourceColumn;
            
            const select = document.createElement('select');
            select.className = 'field-select';
            select.dataset.source = sourceColumn;
            
            const emptyOption = document.createElement('option');
            emptyOption.value = '';
            emptyOption.textContent = '-- Select Field --';
            select.appendChild(emptyOption);
            
            availableFields.forEach(field => {{
                const option = document.createElement('option');
                option.value = field;
                option.textContent = field.replace(/_/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase());
                if (field === targetField) {{
                    option.selected = true;
                }}
                select.appendChild(option);
            }});
            
            cell2.appendChild(select);
            cell3.textContent = targetField ? '✓' : '';
        }}
        
        function addCustomMapping() {{
            const sourceColumn = prompt('Enter source column name:');
            if (sourceColumn) {{
                addMappingRow(sourceColumn, '');
            }}
        }}
        
        function downloadConfig() {{
            const selects = document.querySelectorAll('.field-select');
            const mappings = {{}};
            
            selects.forEach(select => {{
                if (select.value) {{
                    mappings[select.dataset.source] = select.value;
                }}
            }});
            
            const updatedConfig = {{
                ...configData,
                field_mappings: mappings,
                modified_at: new Date().toISOString()
            }};
            
            const blob = new Blob([JSON.stringify(updatedConfig, null, 2)], {{type: 'application/json'}});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `mapping_${{configData.document_info.filename.replace('.pdf', '')}}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            alert('Configuration downloaded! Upload this JSON file back to XLR8 to apply the mappings.');
        }}
        
        // Initialize on load
        window.onload = initializeMappings;
    </script>
</body>
</html>"""
    
    return html_template
