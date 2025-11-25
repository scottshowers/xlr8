"""
Document Analyzer - Universal Document Intelligence System
===========================================================

Phase 1: Analyze ANY document to understand its structure

Author: XLR8 Team
"""

from typing import List, Dict, Any, Optional
from enum import Enum
import re
import logging

logger = logging.getLogger(__name__)


class DocumentStructure(Enum):
    """Primary document structures"""
    TABULAR = "tabular"              # Tables, spreadsheets, data rows
    HIERARCHICAL = "hierarchical"    # Sections, chapters, nested structure
    CODE_BASED = "code"              # Source code with functions/classes
    LINEAR = "linear"                # Articles, blog posts, plain text
    MIXED = "mixed"                  # Multiple structures (common in PDFs)


class DocumentAnalysis:
    """Results of document analysis"""
    
    def __init__(
        self,
        file_type: str,
        filename: str,
        structure: DocumentStructure,
        patterns: List[str],
        density: Dict[str, Any],
        recommended_strategy: Dict[str, Any]
    ):
        self.file_type = file_type
        self.filename = filename
        self.structure = structure
        self.patterns = patterns
        self.density = density
        self.recommended_strategy = recommended_strategy
    
    def __repr__(self):
        return f"DocumentAnalysis(type={self.file_type}, structure={self.structure.value}, strategy={self.recommended_strategy['name']})"


class DocumentAnalyzer:
    """
    Analyzes documents to determine optimal processing strategy
    
    This is the "brain" of the system - it understands document structure
    BEFORE any chunking happens.
    """
    
    def __init__(self):
        # Pattern detection regex
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile all detection patterns"""
        
        # Table patterns
        self.table_patterns = [
            re.compile(r'\|.+\|'),                                    # Markdown tables
            re.compile(r'^\s*[A-Za-z\s]+\t[A-Za-z\s]+\t', re.M),     # Tab-separated
            re.compile(r'Country Code:|Earnings Code:|Deduction'),   # UKG specific
            re.compile(r'Columns:\s*[A-Za-z]'),                      # Column headers
            re.compile(r'\[SHEET:\s*.+\]', re.I),                    # Sheet markers
        ]
        
        # Code patterns
        self.code_patterns = [
            re.compile(r'^(def|class|function|const|let|var)\s+\w+', re.M),  # Python/JS
            re.compile(r'^(public|private|protected)\s+(class|void|int)', re.M),  # Java/C++
            re.compile(r'^import\s+|^from\s+.+import', re.M),       # Imports
            re.compile(r'\{|\}|;$', re.M),                           # Braces/semicolons
            re.compile(r'^#include|^using\s+namespace', re.M),       # C/C++
            re.compile(r'^package\s+|^import\s+static', re.M),       # Java
        ]
        
        # Hierarchical section patterns
        self.section_patterns = [
            re.compile(r'^#{1,6}\s+.+$', re.M),                      # Markdown headers
            re.compile(r'^[A-Z][A-Z\s]{4,}:?\s*$', re.M),           # ALL CAPS HEADERS
            re.compile(r'^\d+\.\s+[A-Z].+$', re.M),                  # Numbered sections
            re.compile(r'^(Chapter|Section|Part|Article)\s+\d+', re.M | re.I),
            re.compile(r'^[IVX]+\.\s+[A-Z]', re.M),                  # Roman numerals
        ]
        
        # PDF-specific patterns
        self.pdf_patterns = [
            re.compile(r'Page\s+\d+', re.I),                         # Page numbers
            re.compile(r'^\s{20,}.+', re.M),                         # Multi-column (spacing)
            re.compile(r'\f'),                                        # Form feed (page break)
        ]
        
        # List patterns
        self.list_patterns = [
            re.compile(r'^\s*[-*•]\s+', re.M),                       # Bullet lists
            re.compile(r'^\s*\d+[\.)]\s+', re.M),                    # Numbered lists
            re.compile(r'^\s*[a-z][\.)]\s+', re.M),                  # Lettered lists
        ]
    
    def analyze(self, text: str, filename: str, file_type: str) -> DocumentAnalysis:
        """
        Main analysis method - determines document structure and optimal strategy
        
        Args:
            text: Full document text
            filename: Original filename
            file_type: Extension (xlsx, pdf, docx, py, etc)
        
        Returns:
            DocumentAnalysis object with complete analysis
        """
        logger.info("="*80)
        logger.info(f"ANALYZING DOCUMENT: {filename} ({file_type})")
        
        # Basic metrics
        lines = text.split('\n')
        length = len(text)
        line_count = len(lines)
        
        # 1. Detect primary structure
        structure = self._detect_structure(text, lines, file_type)
        logger.info(f"  Structure: {structure.value}")
        
        # 2. Detect specific patterns
        patterns = self._detect_patterns(text, structure)
        logger.info(f"  Patterns: {', '.join(patterns) if patterns else 'none'}")
        
        # 3. Calculate density metrics
        density = self._calculate_density(text, lines, structure, file_type)
        logger.info(f"  Density: {self._format_density(density)}")
        
        # 4. Recommend chunking strategy
        strategy = self._recommend_strategy(file_type, structure, density, patterns)
        logger.info(f"  Strategy: {strategy['name']} ({strategy['method']})")
        logger.info("="*80)
        
        return DocumentAnalysis(
            file_type=file_type,
            filename=filename,
            structure=structure,
            patterns=patterns,
            density=density,
            recommended_strategy=strategy
        )
    
    def _detect_structure(self, text: str, lines: List[str], file_type: str) -> DocumentStructure:
        """Detect primary document structure"""
        
        total_lines = len(lines)
        if total_lines == 0:
            return DocumentStructure.LINEAR
        
        # Count pattern matches
        table_lines = sum(1 for line in lines if any(p.search(line) for p in self.table_patterns))
        code_lines = sum(1 for line in lines if any(p.search(line) for p in self.code_patterns))
        section_lines = sum(1 for line in lines if any(p.search(line) for p in self.section_patterns))
        
        # Calculate ratios
        table_ratio = table_lines / total_lines
        code_ratio = code_lines / total_lines
        section_ratio = section_lines / total_lines
        
        # File type hints
        code_extensions = ['py', 'js', 'java', 'cpp', 'c', 'h', 'cs', 'rb', 'go', 'rs', 'php', 'ts']
        table_extensions = ['xlsx', 'xls', 'csv', 'tsv']
        
        # Decision tree
        if file_type in code_extensions or code_ratio > 0.15:
            return DocumentStructure.CODE_BASED
        
        if file_type in table_extensions or table_ratio > 0.25:
            return DocumentStructure.TABULAR
        
        if section_ratio > 0.05 and table_ratio > 0.1:
            return DocumentStructure.MIXED  # Sections + tables (common in PDFs, Word)
        
        if section_ratio > 0.05:
            return DocumentStructure.HIERARCHICAL
        
        return DocumentStructure.LINEAR
    
    def _detect_patterns(self, text: str, structure: DocumentStructure) -> List[str]:
        """Detect specific patterns that affect chunking"""
        patterns = []
        
        # Multi-sheet indicators
        if '[SHEET:' in text or 'WORKSHEET:' in text:
            sheet_count = text.count('[SHEET:') + text.count('WORKSHEET:')
            patterns.append(f'multi-sheet-{sheet_count}')
        
        # Repeated headers (common in tables)
        columns_count = text.count('Columns:')
        if columns_count > 1:
            patterns.append(f'repeated-headers-{columns_count}')
        
        # Code blocks in markdown/docs
        if '```' in text:
            patterns.append('code-blocks')
        
        # Lists
        if any(p.search(text) for p in self.list_patterns):
            patterns.append('lists')
        
        # PDF indicators
        if any(p.search(text) for p in self.pdf_patterns):
            patterns.append('pdf-layout')
        
        # Two-column layout (lots of spacing)
        spacing_lines = len(re.findall(r'^\s{20,}', text, re.M))
        if spacing_lines > 10:
            patterns.append('multi-column')
        
        return patterns
    
    def _calculate_density(
        self, 
        text: str, 
        lines: List[str], 
        structure: DocumentStructure,
        file_type: str
    ) -> Dict[str, Any]:
        """Calculate density metrics for chunking decisions"""
        
        non_empty_lines = [l for l in lines if l.strip()]
        
        density = {
            'total_chars': len(text),
            'total_lines': len(lines),
            'non_empty_lines': len(non_empty_lines),
            'avg_line_length': sum(len(l) for l in non_empty_lines) / max(len(non_empty_lines), 1),
            'short_lines': sum(1 for l in non_empty_lines if len(l) < 40),
            'long_lines': sum(1 for l in non_empty_lines if len(l) > 150),
        }
        
        # Structure-specific metrics
        if structure == DocumentStructure.TABULAR:
            # Count data rows (lines with typical data separators)
            data_rows = [l for l in non_empty_lines if '|' in l or ': ' in l]
            density['data_rows'] = len(data_rows)
            density['data_density'] = len(data_rows) / max(len(non_empty_lines), 1)
            
            # Count sheets if multi-sheet
            density['sheet_count'] = text.count('[SHEET:') + text.count('WORKSHEET:')
        
        elif structure == DocumentStructure.CODE_BASED:
            # Count functions/classes
            functions = len(re.findall(r'^(def|function|class)\s+\w+', text, re.M))
            density['functions'] = functions
            density['avg_function_size'] = len(non_empty_lines) / max(functions, 1)
        
        elif structure == DocumentStructure.HIERARCHICAL:
            # Count sections
            sections = sum(1 for p in self.section_patterns for _ in p.finditer(text))
            density['sections'] = sections
            density['avg_section_size'] = len(non_empty_lines) / max(sections, 1)
        
        return density
    
    def _recommend_strategy(
        self,
        file_type: str,
        structure: DocumentStructure,
        density: Dict[str, Any],
        patterns: List[str]
    ) -> Dict[str, Any]:
        """Recommend optimal chunking strategy based on analysis"""
        
        # TABULAR DOCUMENTS
        if structure == DocumentStructure.TABULAR:
            data_rows = density.get('data_rows', density.get('non_empty_lines', 100))
            
            # Adaptive row-based chunking
            if data_rows <= 5:
                rows_per_chunk = data_rows  # Keep small datasets intact
            elif data_rows <= 20:
                rows_per_chunk = 5
            elif data_rows <= 50:
                rows_per_chunk = 4
            else:
                rows_per_chunk = 3  # High density
            
            return {
                'name': 'adaptive-table',
                'method': 'row-based-adaptive',
                'rows_per_chunk': rows_per_chunk,
                'preserve_headers': True,
                'include_sheet_name': True,
                'multi_sheet': 'multi-sheet' in str(patterns)
            }
        
        # CODE DOCUMENTS
        elif structure == DocumentStructure.CODE_BASED:
            return {
                'name': 'code-aware',
                'method': 'function-boundary',
                'chunk_on': ['def', 'class', 'function'],
                'max_lines': 100,
                'preserve_imports': True,
                'include_signatures': True
            }
        
        # HIERARCHICAL DOCUMENTS
        elif structure == DocumentStructure.HIERARCHICAL:
            return {
                'name': 'hierarchical',
                'method': 'section-based',
                'chunk_size': 1000,
                'overlap': 100,
                'preserve_hierarchy': True,
                'include_parent_sections': True
            }
        
        # MIXED (PDFs, complex Word docs)
        elif structure == DocumentStructure.MIXED:
            return {
                'name': 'hybrid',
                'method': 'pattern-adaptive',
                'chunk_size': 800,
                'overlap': 100,
                'respect_tables': True,
                'respect_sections': True,
                'pdf_aware': 'pdf-layout' in patterns
            }
        
        # LINEAR (articles, plain text)
        else:
            return {
                'name': 'semantic',
                'method': 'paragraph-sentence',
                'chunk_size': 800,
                'overlap': 100,
                'boundary_aware': True
            }
    
    def _format_density(self, density: Dict) -> str:
        """Format density dict for logging"""
        key_metrics = []
        if 'data_rows' in density:
            key_metrics.append(f"{density['data_rows']} data rows")
        if 'sheet_count' in density and density['sheet_count'] > 0:
            key_metrics.append(f"{density['sheet_count']} sheets")
        if 'functions' in density:
            key_metrics.append(f"{density['functions']} functions")
        if 'sections' in density:
            key_metrics.append(f"{density['sections']} sections")
        
        if key_metrics:
            return ', '.join(key_metrics)
        return f"{density['non_empty_lines']} lines"
