"""
PDF Structure Analyzer for Intelligent Parsing
Detects PDF patterns to determine optimal parsing strategy

Author: HCMPACT
Version: 1.0
"""

import pymupdf
from typing import Dict, Any, List, Tuple
import logging
from collections import Counter
import re

logger = logging.getLogger(__name__)


class PDFStructureAnalyzer:
    """
    Analyzes PDF structure to determine optimal parsing strategy.
    
    Detects:
    - Text-based vs scanned
    - Table-heavy vs text-heavy
    - Column layouts
    - Consistent patterns
    - Data types (payroll, financial, narrative)
    """
    
    def __init__(self):
        self.analysis_result = None
    
    def analyze(self, pdf_path: str) -> Dict[str, Any]:
        """
        Comprehensive PDF structure analysis.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            {
                'document_type': str,          # 'payroll_register', 'report', 'form', etc.
                'is_scanned': bool,            # Image-based or text-based
                'table_density': float,        # 0-1, percentage of content in tables
                'text_density': float,         # 0-1, percentage as flowing text
                'layout_type': str,            # 'single_column', 'multi_column', 'mixed'
                'has_headers': bool,           # Consistent headers/footers
                'patterns': List[str],         # Detected patterns
                'complexity': str,             # 'simple', 'moderate', 'complex'
                'recommended_strategy': str,   # 'pdfplumber', 'camelot', 'pymupdf4llm', 'custom'
                'confidence': float,           # 0-1
                'page_analysis': List[Dict],   # Per-page analysis
                'metadata': Dict[str, Any]
            }
        """
        
        logger.info(f"Analyzing PDF structure: {pdf_path}")
        
        try:
            doc = pymupdf.open(pdf_path)
            
            # Initialize analysis
            analysis = {
                'document_type': 'unknown',
                'is_scanned': False,
                'table_density': 0.0,
                'text_density': 0.0,
                'layout_type': 'single_column',
                'has_headers': False,
                'patterns': [],
                'complexity': 'simple',
                'recommended_strategy': 'pdfplumber',
                'confidence': 0.5,
                'page_analysis': [],
                'metadata': {
                    'total_pages': len(doc),
                    'file_size': 0,
                    'has_images': False
                }
            }
            
            # Analyze each page
            page_analyses = []
            for page_num in range(len(doc)):
                page_analysis = self._analyze_page(doc[page_num], page_num)
                page_analyses.append(page_analysis)
            
            analysis['page_analysis'] = page_analyses
            
            # Aggregate analysis
            analysis = self._aggregate_analysis(analysis, page_analyses)
            
            # Detect document type
            analysis['document_type'] = self._detect_document_type(analysis, page_analyses)
            
            # Recommend strategy
            analysis['recommended_strategy'] = self._recommend_strategy(analysis)
            
            # Calculate confidence
            analysis['confidence'] = self._calculate_confidence(analysis)
            
            doc.close()
            
            self.analysis_result = analysis
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing PDF: {e}")
            return {
                'document_type': 'unknown',
                'is_scanned': False,
                'table_density': 0.0,
                'text_density': 0.0,
                'layout_type': 'unknown',
                'has_headers': False,
                'patterns': [],
                'complexity': 'unknown',
                'recommended_strategy': 'pdfplumber',
                'confidence': 0.0,
                'page_analysis': [],
                'metadata': {'error': str(e)}
            }
    
    def _analyze_page(self, page, page_num: int) -> Dict[str, Any]:
        """Analyze a single page."""
        
        # Get page text
        text = page.get_text()
        text_blocks = page.get_text("blocks")
        
        # Detect if scanned (no text or very little)
        is_scanned = len(text.strip()) < 50
        
        # Count text blocks
        num_blocks = len(text_blocks)
        
        # Detect tables (simple heuristic - lines of similar length)
        lines = text.split('\n')
        line_lengths = [len(line.strip()) for line in lines if line.strip()]
        
        # Calculate variance in line lengths
        if line_lengths:
            avg_length = sum(line_lengths) / len(line_lengths)
            variance = sum((l - avg_length) ** 2 for l in line_lengths) / len(line_lengths)
            is_tabular = variance < (avg_length * 0.3)  # Low variance = tabular
        else:
            is_tabular = False
        
        # Detect columns (check text block positioning)
        x_positions = [block[0] for block in text_blocks]
        unique_x = len(set([round(x, -1) for x in x_positions]))  # Round to nearest 10
        num_columns = min(unique_x, 3)  # Cap at 3 columns
        
        return {
            'page_num': page_num,
            'is_scanned': is_scanned,
            'text_length': len(text),
            'num_blocks': num_blocks,
            'is_tabular': is_tabular,
            'num_columns': num_columns,
            'has_images': len(page.get_images()) > 0
        }
    
    def _aggregate_analysis(self, analysis: Dict[str, Any], page_analyses: List[Dict]) -> Dict[str, Any]:
        """Aggregate page-level analysis to document level."""
        
        total_pages = len(page_analyses)
        if total_pages == 0:
            return analysis
        
        # Is document scanned?
        scanned_pages = sum(1 for p in page_analyses if p['is_scanned'])
        analysis['is_scanned'] = scanned_pages > (total_pages * 0.5)
        
        # Table density
        tabular_pages = sum(1 for p in page_analyses if p['is_tabular'])
        analysis['table_density'] = tabular_pages / total_pages
        
        # Text density
        avg_text_length = sum(p['text_length'] for p in page_analyses) / total_pages
        analysis['text_density'] = min(avg_text_length / 3000, 1.0)  # Normalize
        
        # Layout type
        column_counts = [p['num_columns'] for p in page_analyses]
        most_common_cols = Counter(column_counts).most_common(1)[0][0]
        
        if most_common_cols == 1:
            analysis['layout_type'] = 'single_column'
        elif most_common_cols >= 2:
            analysis['layout_type'] = 'multi_column'
        else:
            analysis['layout_type'] = 'mixed'
        
        # Has images
        analysis['metadata']['has_images'] = any(p['has_images'] for p in page_analyses)
        
        # Complexity
        if analysis['is_scanned']:
            analysis['complexity'] = 'complex'
        elif analysis['layout_type'] == 'multi_column' or analysis['table_density'] > 0.7:
            analysis['complexity'] = 'moderate'
        else:
            analysis['complexity'] = 'simple'
        
        return analysis
    
    def _detect_document_type(self, analysis: Dict[str, Any], page_analyses: List[Dict]) -> str:
        """Detect document type based on patterns."""
        
        # Sample first page text
        if page_analyses:
            first_page_text = ""
            # Get first page text (we'd need to store this in page analysis)
            # For now, use heuristics based on structure
            
            table_density = analysis['table_density']
            text_density = analysis['text_density']
            
            # High table density = likely register/report
            if table_density > 0.7:
                return 'payroll_register'
            elif table_density > 0.4:
                return 'financial_report'
            elif text_density > 0.7:
                return 'narrative_document'
            else:
                return 'mixed_content'
        
        return 'unknown'
    
    def _recommend_strategy(self, analysis: Dict[str, Any]) -> str:
        """Recommend parsing strategy based on analysis."""
        
        if analysis['is_scanned']:
            return 'ocr_required'
        
        table_density = analysis['table_density']
        complexity = analysis['complexity']
        layout = analysis['layout_type']
        
        # Table-heavy documents
        if table_density > 0.7:
            if complexity == 'simple':
                return 'pdfplumber'
            else:
                return 'camelot'
        
        # Text-heavy documents
        elif table_density < 0.3:
            return 'pymupdf4llm'
        
        # Mixed content
        else:
            if layout == 'multi_column':
                return 'pymupdf4llm'
            else:
                return 'pdfplumber'
    
    def _calculate_confidence(self, analysis: Dict[str, Any]) -> float:
        """Calculate confidence in the analysis."""
        
        confidence = 0.5  # Base confidence
        
        # High table density = high confidence
        if analysis['table_density'] > 0.8 or analysis['table_density'] < 0.2:
            confidence += 0.2
        
        # Simple complexity = high confidence
        if analysis['complexity'] == 'simple':
            confidence += 0.2
        
        # Known document type = high confidence
        if analysis['document_type'] != 'unknown':
            confidence += 0.1
        
        # Scanned = low confidence
        if analysis['is_scanned']:
            confidence -= 0.3
        
        return max(0.0, min(1.0, confidence))
    
    def get_parsing_hints(self) -> Dict[str, Any]:
        """
        Get hints for parser based on analysis.
        
        Returns:
            {
                'use_tables': bool,
                'use_text': bool,
                'column_count': int,
                'table_strategy': str,
                'post_processing': List[str]
            }
        """
        
        if not self.analysis_result:
            return {}
        
        analysis = self.analysis_result
        
        return {
            'use_tables': analysis['table_density'] > 0.3,
            'use_text': analysis['text_density'] > 0.3,
            'column_count': analysis.get('num_columns', 1),
            'table_strategy': analysis['recommended_strategy'],
            'post_processing': self._suggest_post_processing(analysis)
        }
    
    def _suggest_post_processing(self, analysis: Dict[str, Any]) -> List[str]:
        """Suggest post-processing steps."""
        
        steps = []
        
        if analysis['document_type'] == 'payroll_register':
            steps.append('normalize_column_names')
            steps.append('detect_currency_columns')
            steps.append('detect_date_columns')
        
        if analysis['layout_type'] == 'multi_column':
            steps.append('merge_columns')
        
        if analysis['complexity'] == 'complex':
            steps.append('manual_review_recommended')
        
        return steps


# Convenience function
def analyze_pdf_structure(pdf_path: str) -> Dict[str, Any]:
    """
    Quick analysis of PDF structure.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Analysis result dictionary
    """
    analyzer = PDFStructureAnalyzer()
    return analyzer.analyze(pdf_path)
