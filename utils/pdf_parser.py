"""
Advanced PDF Parser for XLR8
Handles complex pay register parsing with custom field mappings
"""

import pdfplumber
import pandas as pd
import io
import json
from typing import Dict, List, Any, Optional
from datetime import datetime


class AdvancedPDFParser:
    """
    Advanced PDF parser with custom field mapping support
    """
    
    def __init__(self):
        self.detected_tables = []
        self.detected_columns = []
        self.parsed_data = None
        
    def parse_pdf(self, pdf_file, custom_mapping: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Parse PDF file and extract tables
        
        Args:
            pdf_file: Uploaded PDF file object
            custom_mapping: Optional dictionary mapping PDF columns to target fields
            
        Returns:
            Dictionary containing parsed data and metadata
        """
        try:
            # Reset state
            self.detected_tables = []
            self.detected_columns = []
            
            # Open PDF with pdfplumber
            with pdfplumber.open(pdf_file) as pdf:
                # Extract tables from all pages
                for page_num, page in enumerate(pdf.pages, 1):
                    tables = page.extract_tables()
                    
                    if tables:
                        for table_num, table in enumerate(tables, 1):
                            if table and len(table) > 1:  # Has header and data
                                # Convert to DataFrame
                                df = pd.DataFrame(table[1:], columns=table[0])
                                
                                # Clean the data
                                df = self._clean_dataframe(df)
                                
                                # Apply custom mapping if provided
                                if custom_mapping and 'field_mappings' in custom_mapping:
                                    df = self._apply_custom_mapping(df, custom_mapping['field_mappings'])
                                
                                self.detected_tables.append({
                                    'page': page_num,
                                    'table_num': table_num,
                                    'data': df,
                                    'rows': len(df),
                                    'columns': list(df.columns)
                                })
                                
                                # Store unique columns
                                for col in df.columns:
                                    if col and col not in self.detected_columns:
                                        self.detected_columns.append(col)
            
            # Generate results
            if self.detected_tables:
                self.parsed_data = self._generate_results()
                return {
                    'success': True,
                    'tables_found': len(self.detected_tables),
                    'total_rows': sum(t['rows'] for t in self.detected_tables),
                    'columns': self.detected_columns,
                    'data': self.parsed_data,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'success': False,
                    'error': 'No tables detected in PDF',
                    'message': 'The PDF may not contain structured tables or might be image-based'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Error parsing PDF. Please ensure the PDF is text-based and contains tables.'
            }
    
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and normalize dataframe"""
        # Remove completely empty rows
        df = df.dropna(how='all')
        
        # Clean column names
        df.columns = [str(col).strip() if col else f'Column_{i}' 
                     for i, col in enumerate(df.columns)]
        
        # Remove None values
        df = df.fillna('')
        
        # Strip whitespace from string columns
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.strip()
        
        return df
    
    def _apply_custom_mapping(self, df: pd.DataFrame, mappings: Dict[str, str]) -> pd.DataFrame:
        """Apply custom field mappings to dataframe"""
        # Create mapping dictionary
        rename_dict = {}
        for pdf_col, target_field in mappings.items():
            if pdf_col in df.columns and target_field:
                rename_dict[pdf_col] = target_field
        
        # Rename columns
        if rename_dict:
            df = df.rename(columns=rename_dict)
        
        return df
    
    def _generate_results(self) -> Dict[str, Any]:
        """Generate comprehensive results from parsed tables"""
        results = {
            'tables': [],
            'summary': {},
            'all_data': None
        }
        
        all_dfs = []
        
        for table in self.detected_tables:
            df = table['data']
            
            table_info = {
                'page': table['page'],
                'table_num': table['table_num'],
                'rows': table['rows'],
                'columns': table['columns'],
                'data': df
            }
            
            results['tables'].append(table_info)
            all_dfs.append(df)
        
        # Combine all tables
        if all_dfs:
            results['all_data'] = pd.concat(all_dfs, ignore_index=True)
        
        # Generate summary
        results['summary'] = {
            'total_tables': len(self.detected_tables),
            'total_rows': sum(t['rows'] for t in self.detected_tables),
            'unique_columns': len(self.detected_columns),
            'column_list': self.detected_columns
        }
        
        return results
    
    def export_to_excel(self, output_path: str = None) -> io.BytesIO:
        """
        Export parsed data to Excel with multiple sheets
        
        Returns:
            BytesIO object containing Excel file
        """
        if not self.parsed_data or not self.parsed_data['tables']:
            raise ValueError("No data to export. Parse a PDF first.")
        
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Summary sheet
            summary_df = pd.DataFrame([self.parsed_data['summary']])
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Individual table sheets
            for i, table in enumerate(self.parsed_data['tables'], 1):
                sheet_name = f"Page{table['page']}_Table{table['table_num']}"
                table['data'].to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Combined data sheet
            if self.parsed_data['all_data'] is not None:
                self.parsed_data['all_data'].to_excel(writer, sheet_name='All_Data', index=False)
        
        output.seek(0)
        return output
    
    def export_to_csv(self) -> io.StringIO:
        """
        Export all parsed data to CSV
        
        Returns:
            StringIO object containing CSV data
        """
        if not self.parsed_data or self.parsed_data['all_data'] is None:
            raise ValueError("No data to export. Parse a PDF first.")
        
        output = io.StringIO()
        self.parsed_data['all_data'].to_csv(output, index=False)
        output.seek(0)
        return output
    
    def generate_mapping_template(self, pdf_file) -> Dict[str, Any]:
        """
        Generate a mapping template from detected PDF columns
        
        Args:
            pdf_file: Uploaded PDF file object
            
        Returns:
            Dictionary containing mapping template
        """
        # First, detect columns by parsing the PDF
        result = self.parse_pdf(pdf_file)
        
        if not result['success']:
            return result
        
        # Create mapping template
        template = {
            'document_info': {
                'filename': getattr(pdf_file, 'name', 'unknown.pdf'),
                'created_date': datetime.now().isoformat(),
                'tables_detected': result['tables_found'],
                'total_rows': result['total_rows']
            },
            'detected_columns': result['columns'],
            'field_mappings': {},
            'target_fields': [
                'employee_id',
                'employee_name', 
                'gross_pay',
                'net_pay',
                'hours',
                'rate',
                'deductions',
                'taxes',
                'ytd',
                'department',
                'position',
                'date',
                'custom'
            ]
        }
        
        # Initialize mappings (empty for user to fill)
        for col in result['columns']:
            template['field_mappings'][col] = ''
        
        return {
            'success': True,
            'template': template
        }


def create_mapping_editor_html(template: Dict[str, Any], color_scheme: Dict[str, str] = None) -> str:
    """
    Create an HTML mapping editor with TWO PAGES for section/field mapping
    
    Args:
        template: Mapping template dictionary
        color_scheme: Optional color scheme dictionary
        
    Returns:
        HTML string for the mapping editor
    """
    # Use provided color scheme or defaults
    colors = color_scheme or {
        'primary': '#6d8aa0',
        'secondary': '#7d96a8',
        'tertiary': '#8ca6be',
        'background': '#e8edf2',
        'card_bg': '#ffffff',
        'text': '#1a2332',
        'text_secondary': '#6c757d',
        'border': '#d1dce5',
        'success': '#6d8aa0'
    }
    
    # Generate column options for dropdowns
    detected_cols = template.get('detected_columns', [])
    target_fields = template.get('target_fields', [])
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>XLR8 PDF Mapping Editor - Two Page Mode</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', sans-serif;
            background: {colors['background']};
            padding: 20px;
            color: {colors['text']};
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: {colors['card_bg']};
            border-radius: 12px;
            box-shadow: 0 8px 24px rgba(109, 138, 160, 0.15);
            overflow: hidden;
        }}
        
        /* Header */
        .header {{
            background: linear-gradient(135deg, {colors['primary']} 0%, {colors['secondary']} 100%);
            color: white;
            padding: 2rem 3rem;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2rem;
            margin-bottom: 0.5rem;
            font-weight: 700;
        }}
        
        .header p {{
            opacity: 0.95;
            font-size: 1rem;
        }}
        
        /* Page Navigation */
        .page-nav {{
            background: {colors['card_bg']};
            border-bottom: 2px solid {colors['border']};
            padding: 1rem 3rem;
            display: flex;
            gap: 1rem;
        }}
        
        .page-btn {{
            padding: 0.75rem 2rem;
            border: none;
            background: transparent;
            color: {colors['text_secondary']};
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            border-bottom: 3px solid transparent;
            transition: all 0.3s;
        }}
        
        .page-btn:hover {{
            color: {colors['primary']};
            background: rgba(109, 138, 160, 0.05);
        }}
        
        .page-btn.active {{
            color: {colors['primary']};
            border-bottom-color: {colors['primary']};
        }}
        
        /* Pages */
        .page {{
            display: none;
            padding: 3rem;
        }}
        
        .page.active {{
            display: block;
        }}
        
        /* Info Box */
        .info-box {{
            background: rgba(109, 138, 160, 0.1);
            border-left: 4px solid {colors['primary']};
            padding: 1.5rem;
            border-radius: 8px;
            margin-bottom: 2rem;
        }}
        
        .info-box h3 {{
            color: {colors['primary']};
            margin-bottom: 0.5rem;
            font-size: 1.1rem;
        }}
        
        .info-box p {{
            color: {colors['text_secondary']};
            line-height: 1.6;
        }}
        
        /* Canvas Container */
        .canvas-container {{
            position: relative;
            background: white;
            border: 2px solid {colors['border']};
            border-radius: 8px;
            margin: 2rem 0;
            overflow: auto;
            max-height: 600px;
        }}
        
        #pdfCanvas {{
            display: block;
            cursor: crosshair;
        }}
        
        /* Section List */
        .section-list {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 1rem;
            margin-top: 2rem;
        }}
        
        .section-card {{
            background: {colors['card_bg']};
            border: 2px solid {colors['border']};
            border-radius: 8px;
            padding: 1.5rem;
            transition: all 0.3s;
        }}
        
        .section-card:hover {{
            border-color: {colors['primary']};
            box-shadow: 0 4px 12px rgba(109, 138, 160, 0.15);
        }}
        
        .section-card h4 {{
            color: {colors['primary']};
            margin-bottom: 1rem;
            font-size: 1rem;
        }}
        
        .section-card input, .section-card select {{
            width: 100%;
            padding: 0.75rem;
            border: 1px solid {colors['border']};
            border-radius: 6px;
            margin-bottom: 0.75rem;
            font-size: 0.95rem;
            transition: all 0.3s;
        }}
        
        .section-card input:focus, .section-card select:focus {{
            outline: none;
            border-color: {colors['primary']};
            box-shadow: 0 0 0 3px rgba(109, 138, 160, 0.1);
        }}
        
        .field-list {{
            margin-top: 1rem;
            padding-top: 1rem;
            border-top: 1px solid {colors['border']};
        }}
        
        .field-item {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: 0.5rem;
        }}
        
        .field-item input {{
            flex: 1;
            margin-bottom: 0;
        }}
        
        .field-item button {{
            padding: 0.5rem;
            background: #dc3545;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.85rem;
        }}
        
        /* Buttons */
        .btn {{
            padding: 0.85rem 2rem;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            margin-right: 1rem;
        }}
        
        .btn-primary {{
            background: {colors['primary']};
            color: white;
        }}
        
        .btn-primary:hover {{
            background: {colors['secondary']};
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(109, 138, 160, 0.3);
        }}
        
        .btn-secondary {{
            background: transparent;
            color: {colors['primary']};
            border: 2px solid {colors['primary']};
        }}
        
        .btn-secondary:hover {{
            background: rgba(109, 138, 160, 0.1);
        }}
        
        .btn-success {{
            background: {colors['success']};
            color: white;
        }}
        
        /* Action Bar */
        .action-bar {{
            position: sticky;
            bottom: 0;
            background: {colors['card_bg']};
            border-top: 2px solid {colors['border']};
            padding: 1.5rem 3rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 -4px 12px rgba(0,0,0,0.05);
        }}
        
        .progress-info {{
            color: {colors['text_secondary']};
            font-size: 0.95rem;
        }}
        
        /* Success Message */
        .success-message {{
            display: none;
            background: rgba(109, 138, 160, 0.1);
            border: 2px solid {colors['success']};
            padding: 1.5rem;
            border-radius: 8px;
            text-align: center;
            margin: 2rem 0;
        }}
        
        .success-message.show {{
            display: block;
        }}
        
        .success-message h3 {{
            color: {colors['success']};
            margin-bottom: 1rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>⚡ XLR8 PDF Mapping Editor</h1>
            <p>Two-Page Mode: Define Sections & Fields for Excel Export</p>
        </div>
        
        <!-- Page Navigation -->
        <div class="page-nav">
            <button class="page-btn active" onclick="switchPage('page1')">
                📄 Page 1: Define Sections
            </button>
            <button class="page-btn" onclick="switchPage('page2')">
                📋 Page 2: Define Fields
            </button>
        </div>
        
        <!-- Page 1: Define Sections -->
        <div id="page1" class="page active">
            <div class="info-box">
                <h3>📄 Page 1: Define Sections</h3>
                <p>
                    Draw boxes around SECTIONS in your PDF. Each section will become its own tab in the Excel workbook.
                    For example: "Employee Information", "Earnings", "Deductions", "YTD Totals"
                </p>
            </div>
            
            <div class="canvas-container">
                <canvas id="pdfCanvas" width="800" height="1000"></canvas>
            </div>
            
            <div class="section-list" id="sectionList">
                <!-- Sections will be added here -->
            </div>
            
            <button class="btn btn-primary" onclick="addSection()">
                ➕ Add New Section
            </button>
        </div>
        
        <!-- Page 2: Define Fields -->
        <div id="page2" class="page">
            <div class="info-box">
                <h3>📋 Page 2: Define Fields Within Sections</h3>
                <p>
                    For each section, define the FIELDS that will appear as columns in Excel (left to right).
                    Each employee will be a row. Example fields: "Employee ID", "Name", "Gross Pay", "Net Pay"
                </p>
            </div>
            
            <div id="fieldSections">
                <!-- Field definition areas will be populated based on sections -->
            </div>
        </div>
        
        <!-- Action Bar -->
        <div class="action-bar">
            <div class="progress-info">
                <span id="progressText">Sections: 0 | Total Fields: 0</span>
            </div>
            <div>
                <button class="btn btn-secondary" onclick="resetMapping()">
                    🔄 Reset All
                </button>
                <button class="btn btn-primary" onclick="previewConfig()">
                    👁️ Preview Config
                </button>
                <button class="btn btn-success" onclick="downloadConfig()">
                    💾 Download Configuration
                </button>
            </div>
        </div>
        
        <!-- Success Message -->
        <div class="success-message" id="successMessage">
            <h3>✅ Configuration Saved!</h3>
            <p>Your mapping configuration has been downloaded. Upload it to XLR8 to parse the PDF with your custom mappings.</p>
        </div>
    </div>
    
    <script>
        // State management
        let sections = [];
        let currentPage = 'page1';
        let canvas = document.getElementById('pdfCanvas');
        let ctx = canvas.getContext('2d');
        let isDrawing = false;
        let startX, startY;
        let currentBox = null;
        
        // Initialize
        function init() {{
            // Draw sample PDF representation
            drawSamplePDF();
            
            // Add first section by default
            addSection();
        }}
        
        function drawSamplePDF() {{
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            ctx.fillStyle = '#e8edf2';
            ctx.font = '16px Arial';
            ctx.fillText('Sample PDF Document', 50, 50);
            ctx.fillText('(Draw boxes around sections you want to extract)', 50, 80);
            
            // Draw sample table
            ctx.strokeStyle = '#d1dce5';
            ctx.lineWidth = 1;
            for (let i = 0; i < 10; i++) {{
                ctx.strokeRect(50, 120 + i * 40, 700, 40);
            }}
            
            ctx.fillStyle = '{colors["text_secondary"]}';
            ctx.font = '12px Arial';
            ctx.fillText('Employee Info', 60, 145);
            ctx.fillText('Earnings', 250, 145);
            ctx.fillText('Deductions', 450, 145);
            ctx.fillText('Net Pay', 650, 145);
        }}
        
        // Canvas drawing
        canvas.addEventListener('mousedown', startDrawing);
        canvas.addEventListener('mousemove', draw);
        canvas.addEventListener('mouseup', stopDrawing);
        
        function startDrawing(e) {{
            isDrawing = true;
            const rect = canvas.getBoundingClientRect();
            startX = e.clientX - rect.left;
            startY = e.clientY - rect.top;
        }}
        
        function draw(e) {{
            if (!isDrawing) return;
            
            const rect = canvas.getBoundingClientRect();
            const currentX = e.clientX - rect.left;
            const currentY = e.clientY - rect.top;
            
            // Redraw base
            drawSamplePDF();
            
            // Draw existing boxes
            sections.forEach(section => {{
                if (section.box) {{
                    ctx.strokeStyle = '{colors["primary"]}';
                    ctx.lineWidth = 3;
                    ctx.strokeRect(section.box.x, section.box.y, section.box.width, section.box.height);
                    ctx.fillStyle = 'rgba(109, 138, 160, 0.2)';
                    ctx.fillRect(section.box.x, section.box.y, section.box.width, section.box.height);
                }}
            }});
            
            // Draw current box
            ctx.strokeStyle = '{colors["secondary"]}';
            ctx.lineWidth = 2;
            ctx.setLineDash([5, 5]);
            ctx.strokeRect(startX, startY, currentX - startX, currentY - startY);
            ctx.setLineDash([]);
        }}
        
        function stopDrawing(e) {{
            if (!isDrawing) return;
            isDrawing = false;
            
            const rect = canvas.getBoundingClientRect();
            const endX = e.clientX - rect.left;
            const endY = e.clientY - rect.top;
            
            currentBox = {{
                x: Math.min(startX, endX),
                y: Math.min(startY, endY),
                width: Math.abs(endX - startX),
                height: Math.abs(endY - startY)
            }};
            
            // Save to last section if available
            if (sections.length > 0) {{
                const lastSection = sections[sections.length - 1];
                if (!lastSection.box) {{
                    lastSection.box = currentBox;
                    renderSections();
                }}
            }}
        }}
        
        // Section management
        function addSection() {{
            const sectionId = Date.now();
            sections.push({{
                id: sectionId,
                name: '',
                box: null,
                fields: []
            }});
            renderSections();
            updateProgress();
        }}
        
        function removeSection(sectionId) {{
            sections = sections.filter(s => s.id !== sectionId);
            renderSections();
            updateProgress();
        }}
        
        function renderSections() {{
            const sectionList = document.getElementById('sectionList');
            sectionList.innerHTML = '';
            
            sections.forEach((section, index) => {{
                const card = document.createElement('div');
                card.className = 'section-card';
                card.innerHTML = `
                    <h4>Section ${{index + 1}}</h4>
                    <input 
                        type="text" 
                        placeholder="Section Name (e.g., Employee Information)" 
                        value="${{section.name}}"
                        onchange="updateSectionName(${{section.id}}, this.value)"
                    >
                    <p style="color: {colors["text_secondary"]}; font-size: 0.85rem;">
                        ${{section.box ? '✓ Box drawn on canvas' : '⚠ Draw a box on the canvas above'}}
                    </p>
                    <button onclick="removeSection(${{section.id}})" style="background: #dc3545; color: white; border: none; padding: 0.5rem 1rem; border-radius: 6px; cursor: pointer; margin-top: 0.5rem;">
                        🗑️ Remove Section
                    </button>
                `;
                sectionList.appendChild(card);
            }});
            
            renderFieldSections();
        }}
        
        function updateSectionName(sectionId, name) {{
            const section = sections.find(s => s.id === sectionId);
            if (section) {{
                section.name = name;
                renderFieldSections();
            }}
        }}
        
        // Field management
        function renderFieldSections() {{
            const fieldSections = document.getElementById('fieldSections');
            fieldSections.innerHTML = '';
            
            sections.forEach(section => {{
                const sectionDiv = document.createElement('div');
                sectionDiv.className = 'section-card';
                sectionDiv.innerHTML = `
                    <h4>${{section.name || 'Unnamed Section'}}</h4>
                    <div class="field-list" id="fields_${{section.id}}">
                        <!-- Fields will be added here -->
                    </div>
                    <button class="btn btn-secondary" onclick="addField(${{section.id}})">
                        ➕ Add Field
                    </button>
                `;
                fieldSections.appendChild(sectionDiv);
                
                // Render existing fields
                section.fields.forEach((field, index) => {{
                    renderField(section.id, field, index);
                }});
            }});
            
            updateProgress();
        }}
        
        function addField(sectionId) {{
            const section = sections.find(s => s.id === sectionId);
            if (section) {{
                section.fields.push({{
                    name: '',
                    pdfColumn: ''
                }});
                renderFieldSections();
            }}
        }}
        
        function renderField(sectionId, field, index) {{
            const fieldList = document.getElementById(`fields_${{sectionId}}`);
            const fieldDiv = document.createElement('div');
            fieldDiv.className = 'field-item';
            fieldDiv.innerHTML = `
                <input 
                    type="text" 
                    placeholder="Field Name (e.g., Employee ID)" 
                    value="${{field.name}}"
                    onchange="updateField(${{sectionId}}, ${{index}}, 'name', this.value)"
                >
                <input 
                    type="text" 
                    placeholder="PDF Column" 
                    value="${{field.pdfColumn}}"
                    onchange="updateField(${{sectionId}}, ${{index}}, 'pdfColumn', this.value)"
                >
                <button onclick="removeField(${{sectionId}}, ${{index}})">🗑️</button>
            `;
            fieldList.appendChild(fieldDiv);
        }}
        
        function updateField(sectionId, fieldIndex, property, value) {{
            const section = sections.find(s => s.id === sectionId);
            if (section && section.fields[fieldIndex]) {{
                section.fields[fieldIndex][property] = value;
                updateProgress();
            }}
        }}
        
        function removeField(sectionId, fieldIndex) {{
            const section = sections.find(s => s.id === sectionId);
            if (section) {{
                section.fields.splice(fieldIndex, 1);
                renderFieldSections();
            }}
        }}
        
        // Navigation
        function switchPage(pageId) {{
            // Hide all pages
            document.querySelectorAll('.page').forEach(page => {{
                page.classList.remove('active');
            }});
            
            // Remove active from all buttons
            document.querySelectorAll('.page-btn').forEach(btn => {{
                btn.classList.remove('active');
            }});
            
            // Show selected page
            document.getElementById(pageId).classList.add('active');
            event.target.classList.add('active');
            
            currentPage = pageId;
        }}
        
        // Progress tracking
        function updateProgress() {{
            const totalFields = sections.reduce((sum, section) => sum + section.fields.length, 0);
            document.getElementById('progressText').textContent = 
                `Sections: ${{sections.length}} | Total Fields: ${{totalFields}}`;
        }}
        
        // Configuration management
        function previewConfig() {{
            const config = generateConfig();
            alert(JSON.stringify(config, null, 2));
        }}
        
        function generateConfig() {{
            return {{
                document_info: {{
                    created_date: new Date().toISOString(),
                    editor_version: '2.0',
                    mode: 'two-page-section-field'
                }},
                sections: sections.map(section => ({{
                    name: section.name,
                    box: section.box,
                    fields: section.fields,
                    excel_tab: section.name.replace(/[^a-zA-Z0-9]/g, '_')
                }}))
            }};
        }}
        
        function downloadConfig() {{
            const config = generateConfig();
            const blob = new Blob([JSON.stringify(config, null, 2)], {{ type: 'application/json' }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'xlr8_mapping_config.json';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            // Show success message
            document.getElementById('successMessage').classList.add('show');
            setTimeout(() => {{
                document.getElementById('successMessage').classList.remove('show');
            }}, 5000);
        }}
        
        function resetMapping() {{
            if (confirm('Reset all sections and fields? This cannot be undone.')) {{
                sections = [];
                addSection();
                drawSamplePDF();
                renderSections();
            }}
        }}
        
        // Initialize on load
        init();
    </script>
</body>
</html>''
