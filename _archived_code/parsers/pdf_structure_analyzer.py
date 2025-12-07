"""
PDF Structure Analyzer
Analyzes PDF structure to detect document type and extraction strategy
"""

import fitz  # PyMuPDF
import re
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class PDFStructureAnalyzer:
    """
    Analyzes PDF structure to identify document type and recommend parsing strategy.
    """
    
    def __init__(self, pdf_path: str):
        """
        Initialize analyzer with PDF path.
        
        Args:
            pdf_path: Path to PDF file
        """
        self.pdf_path = pdf_path
        self.text = ""
        self.pages = []
        
    def analyze(self) -> Dict[str, Any]:
        """
        Analyze PDF structure and detect document type.
        
        Returns:
            Dict with structure info:
            - format_type: 'payroll_register', 'benefits', 'timecard', etc.
            - sections: List of detected sections
            - has_tables: Boolean
            - employee_count: Estimated number of employees
            - complexity: 'simple', 'medium', 'complex'
            - recommended_strategy: Parsing approach to use
        """
        try:
            # Open PDF and extract text
            doc = fitz.open(self.pdf_path)
            
            for page_num, page in enumerate(doc):
                page_text = page.get_text()
                self.pages.append({
                    'page_num': page_num,
                    'text': page_text
                })
                self.text += page_text + "\n\n"
            
            doc.close()
            
            # Analyze structure
            structure = {
                'format_type': self._detect_format_type(),
                'sections': self._detect_sections(),
                'has_tables': self._detect_tables(),
                'employee_count': self._estimate_employee_count(),
                'complexity': self._assess_complexity(),
                'column_patterns': self._detect_column_patterns(),
                'recommended_strategy': None
            }
            
            # Determine recommended strategy
            structure['recommended_strategy'] = self._recommend_strategy(structure)
            
            logger.info(f"Analyzed PDF: {structure['format_type']} with {structure['employee_count']} employees")
            return structure
            
        except Exception as e:
            logger.error(f"Analysis error: {str(e)}", exc_info=True)
            return {
                'format_type': 'unknown',
                'sections': [],
                'has_tables': False,
                'employee_count': 0,
                'complexity': 'unknown',
                'recommended_strategy': 'basic_text'
            }
    
    def _detect_format_type(self) -> str:
        """
        Detect the type of document.
        """
        text_lower = self.text.lower()
        
        # Payroll register indicators
        payroll_keywords = [
            'payroll', 'pay register', 'earnings', 'deductions', 
            'gross pay', 'net pay', 'ytd', 'taxes'
        ]
        
        # Benefits indicators
        benefits_keywords = [
            'benefits', 'enrollment', 'coverage', 'premium',
            'health insurance', 'dental', 'vision'
        ]
        
        # Timecard indicators
        timecard_keywords = [
            'timecard', 'time sheet', 'hours worked', 'clock in',
            'clock out', 'overtime'
        ]
        
        # Count matches
        payroll_matches = sum(1 for kw in payroll_keywords if kw in text_lower)
        benefits_matches = sum(1 for kw in benefits_keywords if kw in text_lower)
        timecard_matches = sum(1 for kw in timecard_keywords if kw in text_lower)
        
        # Determine type
        if payroll_matches >= 3:
            return 'payroll_register'
        elif benefits_matches >= 3:
            return 'benefits'
        elif timecard_matches >= 3:
            return 'timecard'
        else:
            return 'general'
    
    def _detect_sections(self) -> List[str]:
        """
        Detect major sections in the document.
        """
        sections = []
        
        # Common section headers
        section_patterns = {
            'employee_info': r'(?:Employee\s+(?:Information|Info|Details)|EMP\s+INFO)',
            'earnings': r'(?:Earnings|Pay\s+Items|Income|Wages)',
            'taxes': r'(?:Taxes|Tax\s+Deductions|Statutory\s+Deductions)',
            'deductions': r'(?:Deductions|Pre-Tax|Post-Tax|Benefits\s+Deductions)',
            'summary': r'(?:Summary|Totals|Pay\s+Summary)',
            'ytd': r'(?:YTD|Year[\s-]to[\s-]Date)'
        }
        
        for section_name, pattern in section_patterns.items():
            if re.search(pattern, self.text, re.IGNORECASE):
                sections.append(section_name)
        
        return sections
    
    def _detect_tables(self) -> bool:
        """
        Detect if document contains table structures.
        """
        # Look for table indicators
        indicators = [
            r'\|\s+\w+\s+\|',  # Pipe-separated
            r'\t\w+\t',  # Tab-separated
            r'\s{4,}\w+\s{4,}',  # Multiple spaces (column alignment)
            r'[-=]{5,}',  # Horizontal lines
        ]
        
        for pattern in indicators:
            if re.search(pattern, self.text):
                return True
        
        return False
    
    def _estimate_employee_count(self) -> int:
        """
        Estimate number of employees in the document.
        """
        # Look for employee ID patterns
        id_patterns = [
            r'(?:Employee\s+ID|EMP#|ID)[\s:]+(\d+)',
            r'(?:SSN)[\s:]+(\d{3}-\d{2}-\d{4})',
        ]
        
        unique_ids = set()
        
        for pattern in id_patterns:
            matches = re.findall(pattern, self.text, re.IGNORECASE)
            unique_ids.update(matches)
        
        # If no IDs found, estimate by page count
        if not unique_ids:
            # Rough estimate: 1-3 employees per page for registers
            return max(1, len(self.pages))
        
        return len(unique_ids)
    
    def _detect_column_patterns(self) -> Dict[str, List[str]]:
        """
        Detect common column patterns in the document.
        """
        patterns = {
            'date_columns': [],
            'amount_columns': [],
            'code_columns': [],
            'text_columns': []
        }
        
        # Find lines that look like headers
        header_lines = []
        for line in self.text.split('\n')[:50]:  # Check first 50 lines
            if len(line) > 20 and re.search(r'[A-Z][a-z]+', line):
                header_lines.append(line)
        
        # Analyze header lines for column types
        for line in header_lines:
            words = line.split()
            
            for word in words:
                word_lower = word.lower()
                
                if any(kw in word_lower for kw in ['date', 'period', 'from', 'to']):
                    patterns['date_columns'].append(word)
                elif any(kw in word_lower for kw in ['amount', 'rate', 'hours', 'qty', 'total']):
                    patterns['amount_columns'].append(word)
                elif any(kw in word_lower for kw in ['code', 'id', 'type', 'class']):
                    patterns['code_columns'].append(word)
                elif len(word) > 3:
                    patterns['text_columns'].append(word)
        
        return patterns
    
    def _assess_complexity(self) -> str:
        """
        Assess document complexity.
        """
        complexity_score = 0
        
        # Factors that increase complexity
        if len(self.pages) > 5:
            complexity_score += 1
        
        if len(self._detect_sections()) > 3:
            complexity_score += 1
        
        if self._estimate_employee_count() > 10:
            complexity_score += 1
        
        if self._detect_tables():
            complexity_score += 1
        
        # Check for multi-column layout
        if re.search(r'\s{10,}', self.text):
            complexity_score += 1
        
        # Classify
        if complexity_score <= 1:
            return 'simple'
        elif complexity_score <= 3:
            return 'medium'
        else:
            return 'complex'
    
    def _recommend_strategy(self, structure: Dict[str, Any]) -> str:
        """
        Recommend parsing strategy based on structure analysis.
        """
        format_type = structure['format_type']
        complexity = structure['complexity']
        
        # Strategy recommendations
        if format_type == 'payroll_register':
            if complexity == 'simple':
                return 'basic_table_extraction'
            elif complexity == 'medium':
                return 'section_based_extraction'
            else:
                return 'iterative_employee_extraction'
        
        elif format_type == 'benefits':
            return 'section_based_extraction'
        
        elif format_type == 'timecard':
            return 'basic_table_extraction'
        
        else:
            return 'basic_text_extraction'
