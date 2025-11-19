"""
PDF Structure Analyzer for XLR8 Intelligent Parser
Analyzes PDF structure and recommends parsing strategies
"""

import pdfplumber
import pandas as pd
import re
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class PDFStructureAnalyzer:
    """Analyzes PDF structure to determine optimal parsing strategy"""
    
    def __init__(self):
        self.analysis_result = {}
        
    def analyze_pdf(self, pdf_path: str) -> Dict:
        """
        Comprehensive PDF structure analysis
        
        Returns:
            Dict with structure analysis and recommended strategy
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                analysis = {
                    'success': True,
                    'total_pages': len(pdf.pages),
                    'document_type': None,
                    'has_tables': False,
                    'table_count': 0,
                    'has_text': False,
                    'text_density': 0,
                    'layout_complexity': 'simple',
                    'recommended_strategy': None,
                    'page_samples': [],
                    'table_structures': [],
                    'text_patterns': [],
                    'confidence': 0
                }
                
                # Analyze first 3 pages for structure
                sample_pages = min(3, len(pdf.pages))
                for i in range(sample_pages):
                    page = pdf.pages[i]
                    page_analysis = self._analyze_page(page, i)
                    analysis['page_samples'].append(page_analysis)
                    
                    if page_analysis['tables']:
                        analysis['has_tables'] = True
                        analysis['table_count'] += len(page_analysis['tables'])
                        analysis['table_structures'].extend(page_analysis['table_structures'])
                    
                    if page_analysis['text']:
                        analysis['has_text'] = True
                        analysis['text_density'] += page_analysis['text_density']
                
                # Calculate average text density
                if sample_pages > 0:
                    analysis['text_density'] = analysis['text_density'] / sample_pages
                
                # Detect document type
                analysis['document_type'] = self._detect_document_type(analysis)
                
                # Determine layout complexity
                analysis['layout_complexity'] = self._determine_complexity(analysis)
                
                # Recommend strategy
                strategy = self._recommend_strategy(analysis)
                analysis['recommended_strategy'] = strategy['strategy']
                analysis['confidence'] = strategy['confidence']
                analysis['reasoning'] = strategy['reasoning']
                
                self.analysis_result = analysis
                return analysis
                
        except Exception as e:
            logger.error(f"PDF analysis failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'recommended_strategy': 'adaptive'
            }
    
    def _analyze_page(self, page, page_num: int) -> Dict:
        """Analyze individual page structure"""
        analysis = {
            'page_num': page_num,
            'tables': [],
            'table_structures': [],
            'text': None,
            'text_density': 0,
            'has_header': False,
            'has_footer': False
        }
        
        # Extract tables
        tables = page.extract_tables()
        if tables:
            analysis['tables'] = tables
            for table in tables:
                structure = self._analyze_table_structure(table)
                analysis['table_structures'].append(structure)
        
        # Extract text
        text = page.extract_text()
        if text:
            analysis['text'] = text
            # Calculate text density (chars per area)
            area = page.width * page.height
            analysis['text_density'] = len(text) / area if area > 0 else 0
            
            # Detect header/footer
            lines = text.split('\n')
            if len(lines) > 2:
                analysis['has_header'] = self._is_header_line(lines[0])
                analysis['has_footer'] = self._is_footer_line(lines[-1])
        
        return analysis
    
    def _analyze_table_structure(self, table: List[List]) -> Dict:
        """Analyze table structure"""
        if not table:
            return {'rows': 0, 'cols': 0, 'has_header': False}
        
        structure = {
            'rows': len(table),
            'cols': len(table[0]) if table else 0,
            'has_header': False,
            'header_row': None,
            'data_types': []
        }
        
        # Check if first row is header
        if len(table) > 1:
            first_row = table[0]
            second_row = table[1]
            structure['has_header'] = self._is_header_row(first_row, second_row)
            if structure['has_header']:
                structure['header_row'] = first_row
        
        # Detect data types in columns
        if len(table) > 1:
            data_rows = table[1:] if structure['has_header'] else table
            for col_idx in range(structure['cols']):
                col_values = [row[col_idx] for row in data_rows if col_idx < len(row)]
                data_type = self._detect_column_type(col_values)
                structure['data_types'].append(data_type)
        
        return structure
    
    def _is_header_row(self, first_row: List, second_row: List) -> bool:
        """Determine if first row is a header"""
        if not first_row or not second_row:
            return False
        
        # Check if first row has text and second row has different pattern
        first_has_text = any(isinstance(cell, str) and cell.strip() for cell in first_row)
        
        # Headers usually don't have numbers in every cell
        first_numeric_count = sum(1 for cell in first_row if self._is_numeric(cell))
        second_numeric_count = sum(1 for cell in second_row if self._is_numeric(cell))
        
        return first_has_text and (first_numeric_count < second_numeric_count)
    
    def _detect_column_type(self, values: List) -> str:
        """Detect data type of column"""
        if not values:
            return 'empty'
        
        non_empty = [v for v in values if v is not None and str(v).strip()]
        if not non_empty:
            return 'empty'
        
        numeric_count = sum(1 for v in non_empty if self._is_numeric(v))
        date_count = sum(1 for v in non_empty if self._is_date(v))
        
        total = len(non_empty)
        if numeric_count / total > 0.8:
            return 'numeric'
        elif date_count / total > 0.8:
            return 'date'
        else:
            return 'text'
    
    def _is_numeric(self, value) -> bool:
        """Check if value is numeric"""
        if value is None:
            return False
        s = str(value).strip().replace(',', '').replace('$', '')
        try:
            float(s)
            return True
        except:
            return False
    
    def _is_date(self, value) -> bool:
        """Check if value looks like a date"""
        if value is None:
            return False
        s = str(value).strip()
        # Simple date pattern matching
        date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{2,4}',
            r'\d{1,2}-\d{1,2}-\d{2,4}',
            r'\d{4}-\d{1,2}-\d{1,2}'
        ]
        return any(re.match(pattern, s) for pattern in date_patterns)
    
    def _is_header_line(self, line: str) -> bool:
        """Check if line looks like a header"""
        if not line:
            return False
        line = line.strip()
        # Headers often have dates, report names, company names
        header_keywords = ['report', 'register', 'date', 'company', 'period', 'page']
        return any(keyword in line.lower() for keyword in header_keywords)
    
    def _is_footer_line(self, line: str) -> bool:
        """Check if line looks like a footer"""
        if not line:
            return False
        line = line.strip()
        # Footers often have page numbers
        return bool(re.search(r'page\s+\d+', line.lower()))
    
    def _detect_document_type(self, analysis: Dict) -> str:
        """Detect type of document"""
        text_samples = []
        for page in analysis['page_samples']:
            if page['text']:
                text_samples.append(page['text'].lower())
        
        full_text = ' '.join(text_samples)
        
        # Check for register indicators
        if 'register' in full_text:
            if 'payroll' in full_text:
                return 'payroll_register'
            else:
                return 'register'
        
        # Check for other document types
        if any(keyword in full_text for keyword in ['invoice', 'bill']):
            return 'invoice'
        if any(keyword in full_text for keyword in ['receipt', 'payment']):
            return 'receipt'
        if 'report' in full_text:
            return 'report'
        
        # Default based on structure
        if analysis['has_tables']:
            return 'tabular_document'
        else:
            return 'text_document'
    
    def _determine_complexity(self, analysis: Dict) -> str:
        """Determine layout complexity"""
        score = 0
        
        # More tables = more complex
        if analysis['table_count'] > 3:
            score += 2
        elif analysis['table_count'] > 0:
            score += 1
        
        # Multiple table structures = more complex
        if len(set(str(s) for s in analysis['table_structures'])) > 1:
            score += 1
        
        # High text density with tables = more complex
        if analysis['has_tables'] and analysis['text_density'] > 0.1:
            score += 1
        
        if score >= 3:
            return 'complex'
        elif score >= 1:
            return 'moderate'
        else:
            return 'simple'
    
    def _recommend_strategy(self, analysis: Dict) -> Dict:
        """Recommend parsing strategy based on analysis"""
        strategy = {
            'strategy': 'adaptive',
            'confidence': 50,
            'reasoning': []
        }
        
        doc_type = analysis['document_type']
        
        # Strong recommendations for known document types
        if doc_type in ['payroll_register', 'register']:
            strategy['strategy'] = 'adaptive'
            strategy['confidence'] = 90
            strategy['reasoning'].append(f"Document identified as {doc_type}")
            strategy['reasoning'].append("Adaptive parsers optimized for register documents")
            return strategy
        
        # Table-based documents
        if analysis['has_tables'] and analysis['table_count'] > 0:
            if analysis['layout_complexity'] == 'simple':
                strategy['strategy'] = 'table_extraction'
                strategy['confidence'] = 75
                strategy['reasoning'].append("Simple table structure detected")
            else:
                strategy['strategy'] = 'adaptive'
                strategy['confidence'] = 70
                strategy['reasoning'].append("Complex table structure - adaptive parsing recommended")
            return strategy
        
        # Text-heavy documents
        if analysis['has_text'] and not analysis['has_tables']:
            strategy['strategy'] = 'text_extraction'
            strategy['confidence'] = 60
            strategy['reasoning'].append("Text-based document without tables")
            return strategy
        
        # Default to adaptive for unknown cases
        strategy['reasoning'].append("Document type unclear - using adaptive approach")
        return strategy
    
    def generate_parsing_hints(self) -> Dict:
        """Generate hints for parser code generation"""
        if not self.analysis_result:
            return {}
        
        hints = {
            'document_type': self.analysis_result.get('document_type'),
            'table_positions': [],
            'header_rows': [],
            'expected_columns': [],
            'data_types': {}
        }
        
        # Extract table hints
        for i, page in enumerate(self.analysis_result.get('page_samples', [])):
            for j, table_struct in enumerate(page.get('table_structures', [])):
                hints['table_positions'].append({
                    'page': i,
                    'table_index': j,
                    'rows': table_struct['rows'],
                    'cols': table_struct['cols']
                })
                
                if table_struct['has_header'] and table_struct['header_row']:
                    hints['header_rows'].append({
                        'page': i,
                        'table_index': j,
                        'headers': table_struct['header_row']
                    })
                    hints['expected_columns'].extend(table_struct['header_row'])
                
                # Add data types
                for col_idx, dtype in enumerate(table_struct.get('data_types', [])):
                    if table_struct['has_header'] and col_idx < len(table_struct['header_row']):
                        col_name = table_struct['header_row'][col_idx]
                        hints['data_types'][col_name] = dtype
        
        return hints
