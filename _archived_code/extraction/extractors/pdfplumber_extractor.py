"""
PDFPlumber Extractor
=====================
Character-level PDF extraction using pdfplumber.
Best for: Precise position analysis, detecting merged columns.

Deploy to: backend/extraction/extractors/pdfplumber_extractor.py
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from statistics import median

logger = logging.getLogger(__name__)

try:
    import pdfplumber
    AVAILABLE = True
except ImportError:
    AVAILABLE = False
    logger.warning("pdfplumber not installed")


@dataclass 
class ExtractionResult:
    """Result from extraction"""
    extractor_name: str
    data: List[Dict[str, Any]]
    headers: List[str]
    confidence: float
    bbox: Optional[Dict] = None
    issues: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class PDFPlumberExtractor:
    """
    Extracts tables using pdfplumber with character-level position analysis.
    
    Key features:
    - Character position tracking
    - Intelligent column boundary detection
    - Merged column detection
    - Section type inference from content
    """
    
    # Keywords for section detection
    SECTION_KEYWORDS = {
        'employee_info': ['employee', 'name', 'id', 'ssn', 'department', 'hire', 'location'],
        'earnings': ['earnings', 'hours', 'rate', 'regular', 'overtime', 'gross', 'pay code'],
        'taxes': ['tax', 'federal', 'state', 'fica', 'medicare', 'withhold'],
        'deductions': ['deduction', '401k', 'medical', 'dental', 'insurance', 'garnish'],
        'pay_totals': ['gross pay', 'net pay', 'total', 'check', 'direct deposit'],
    }
    
    # Patterns for value types
    VALUE_PATTERNS = {
        'currency': r'^\$?[\d,]+\.?\d{0,2}$',
        'hours': r'^\d{1,3}\.\d{1,2}$',
        'date': r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$',
        'ssn': r'^\d{3}-?\d{2}-?\d{4}$',
        'percentage': r'^\d{1,3}\.?\d*%$',
    }
    
    def __init__(self):
        if not AVAILABLE:
            raise RuntimeError("pdfplumber not installed")
    
    def extract(self, file_path: str, 
                layout: Optional[Dict] = None) -> Dict[str, ExtractionResult]:
        """
        Extract all sections from a PDF.
        
        Args:
            file_path: Path to PDF file
            layout: Optional pre-detected layout structure
            
        Returns:
            Dict mapping section names to ExtractionResult
        """
        results = {}
        
        try:
            with pdfplumber.open(file_path) as pdf:
                all_tables = []
                
                for page_num, page in enumerate(pdf.pages):
                    # Extract tables from this page
                    page_tables = self._extract_page_tables(page, page_num)
                    all_tables.extend(page_tables)
                
                # Classify and group tables by section
                for table_data in all_tables:
                    section_type = self._detect_section_type(
                        table_data['headers'],
                        table_data['data']
                    )
                    
                    if section_type not in results:
                        results[section_type] = ExtractionResult(
                            extractor_name='pdfplumber',
                            data=[],
                            headers=table_data['headers'],
                            confidence=table_data.get('confidence', 0.7),
                            issues=[]
                        )
                    
                    # Append data to section
                    results[section_type].data.extend(table_data['data'])
                    
                    # Check for merged columns
                    merged = self._detect_merged_columns(
                        table_data['headers'],
                        table_data['data']
                    )
                    if merged:
                        results[section_type].issues.append(
                            f"Possible merged columns detected: {merged}"
                        )
                        results[section_type].confidence *= 0.8
        
        except Exception as e:
            logger.error(f"pdfplumber extraction failed: {e}", exc_info=True)
            raise
        
        return results
    
    def _extract_page_tables(self, page, page_num: int) -> List[Dict]:
        """Extract tables from a single page using multiple strategies"""
        tables = []
        
        # Strategy 1: Use pdfplumber's built-in table detection
        detected_tables = page.extract_tables()
        
        for idx, table in enumerate(detected_tables):
            if not table or len(table) < 2:
                continue
            
            # First row as headers
            headers = [str(h).strip() if h else f'Col_{i}' 
                      for i, h in enumerate(table[0])]
            
            # Rest as data
            data = []
            for row in table[1:]:
                cleaned_row = [str(cell).strip() if cell else '' for cell in row]
                if any(cleaned_row):  # Skip empty rows
                    data.append(cleaned_row)
            
            if data:
                tables.append({
                    'headers': headers,
                    'data': data,
                    'page': page_num,
                    'table_index': idx,
                    'confidence': 0.75
                })
        
        # Strategy 2: Character-level extraction for complex layouts
        if not tables or self._should_try_char_extraction(page):
            char_tables = self._extract_using_characters(page)
            
            for char_table in char_tables:
                # Check if this is better than what we already have
                if self._is_better_extraction(char_table, tables):
                    tables.append(char_table)
        
        return tables
    
    def _extract_using_characters(self, page) -> List[Dict]:
        """
        Extract tables using character-level position analysis.
        Better for complex layouts with merged columns.
        """
        tables = []
        
        try:
            # Get all characters with positions
            chars = page.chars
            
            if not chars:
                return tables
            
            # Group characters into lines by Y position
            lines = self._group_chars_to_lines(chars)
            
            if len(lines) < 2:
                return tables
            
            # Find potential header rows
            header_candidates = self._find_header_rows(lines)
            
            for header_idx in header_candidates:
                # Detect column boundaries from header
                col_boundaries = self._detect_column_boundaries(lines[header_idx])
                
                if len(col_boundaries) < 2:
                    continue
                
                # Extract header cells
                header_line = lines[header_idx]
                headers = self._extract_cells_by_boundaries(header_line, col_boundaries)
                
                # Extract data rows
                data = []
                for i in range(header_idx + 1, len(lines)):
                    row_cells = self._extract_cells_by_boundaries(lines[i], col_boundaries)
                    if any(c.strip() for c in row_cells):
                        data.append(row_cells)
                
                if data:
                    tables.append({
                        'headers': headers,
                        'data': data,
                        'confidence': 0.85,
                        'extraction_method': 'character_level'
                    })
            
        except Exception as e:
            logger.warning(f"Character extraction failed: {e}")
        
        return tables
    
    def _group_chars_to_lines(self, chars: List[Dict], 
                              y_tolerance: float = 3) -> List[List[Dict]]:
        """Group characters into lines based on Y position"""
        if not chars:
            return []
        
        # Sort by Y position
        sorted_chars = sorted(chars, key=lambda c: (c['top'], c['x0']))
        
        lines = []
        current_line = [sorted_chars[0]]
        current_y = sorted_chars[0]['top']
        
        for char in sorted_chars[1:]:
            if abs(char['top'] - current_y) <= y_tolerance:
                current_line.append(char)
            else:
                if current_line:
                    lines.append(sorted(current_line, key=lambda c: c['x0']))
                current_line = [char]
                current_y = char['top']
        
        if current_line:
            lines.append(sorted(current_line, key=lambda c: c['x0']))
        
        return lines
    
    def _find_header_rows(self, lines: List[List[Dict]]) -> List[int]:
        """Find potential header rows based on content analysis"""
        candidates = []
        
        for i, line in enumerate(lines[:20]):  # Check first 20 lines
            line_text = ''.join(c.get('text', '') for c in line).lower()
            
            # Score based on header keywords
            score = 0
            for section, keywords in self.SECTION_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in line_text:
                        score += 1
            
            # Check for formatting patterns (all caps, etc.)
            all_text = ''.join(c.get('text', '') for c in line)
            if all_text.isupper() and len(all_text) > 10:
                score += 0.5
            
            if score >= 1:
                candidates.append(i)
        
        return candidates if candidates else [0]  # Default to first line
    
    def _detect_column_boundaries(self, line: List[Dict]) -> List[float]:
        """Detect column boundaries from character positions"""
        if len(line) < 2:
            return []
        
        # Calculate gaps between characters
        gaps = []
        for i in range(1, len(line)):
            gap = line[i]['x0'] - line[i-1]['x1']
            gaps.append((gap, line[i]['x0']))
        
        if not gaps:
            return []
        
        # Find significant gaps (larger than median * 1.5)
        gap_values = [g[0] for g in gaps]
        median_gap = median(gap_values) if gap_values else 0
        threshold = max(median_gap * 1.5, 10)  # At least 10 pixels
        
        # Column boundaries are at positions after large gaps
        boundaries = [line[0]['x0']]  # Start of first column
        
        for gap, pos in gaps:
            if gap > threshold:
                boundaries.append(pos)
        
        # Add end boundary
        boundaries.append(line[-1]['x1'] + 50)
        
        return boundaries
    
    def _extract_cells_by_boundaries(self, line: List[Dict], 
                                      boundaries: List[float]) -> List[str]:
        """Extract cell values based on column boundaries"""
        cells = [''] * (len(boundaries) - 1)
        
        for char in line:
            char_mid = (char['x0'] + char['x1']) / 2
            
            # Find which column this character belongs to
            for i in range(len(boundaries) - 1):
                if boundaries[i] <= char_mid < boundaries[i + 1]:
                    cells[i] += char.get('text', '')
                    break
        
        return [c.strip() for c in cells]
    
    def _detect_section_type(self, headers: List[str], 
                             data: List[List[str]]) -> str:
        """Detect section type based on headers and data"""
        header_text = ' '.join(headers).lower()
        
        # Check for section keywords in headers
        scores = {}
        for section, keywords in self.SECTION_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in header_text)
            if score > 0:
                scores[section] = score
        
        if scores:
            return max(scores, key=scores.get)
        
        # Fallback: analyze data patterns
        if data:
            sample = data[0] if data else []
            sample_text = ' '.join(str(s) for s in sample).lower()
            
            for section, keywords in self.SECTION_KEYWORDS.items():
                if any(kw in sample_text for kw in keywords):
                    return section
        
        return 'unknown'
    
    def _detect_merged_columns(self, headers: List[str], 
                               data: List[List[str]]) -> List[int]:
        """Detect columns that appear to contain merged data"""
        merged_indices = []
        
        for col_idx in range(len(headers)):
            # Check sample values
            samples = [row[col_idx] for row in data[:10] if col_idx < len(row)]
            
            for sample in samples:
                if self._looks_like_merged(sample):
                    if col_idx not in merged_indices:
                        merged_indices.append(col_idx)
                    break
        
        return merged_indices
    
    def _looks_like_merged(self, value: str) -> bool:
        """Check if a value looks like it contains multiple columns"""
        if not value or len(value) < 15:
            return False
        
        # Count numeric values
        numbers = re.findall(r'[\d,]+\.?\d*', value)
        if len(numbers) >= 3:
            return True
        
        # Check for code + numbers pattern
        if re.search(r'[A-Z]{2,}\s+[\d.]+\s+[\d.]+', value):
            return True
        
        # Multiple distinct value patterns
        parts = value.split()
        if len(parts) >= 4 and sum(1 for p in parts if re.match(r'[\d,.]+', p)) >= 2:
            return True
        
        return False
    
    def _should_try_char_extraction(self, page) -> bool:
        """Determine if character-level extraction should be attempted"""
        # Try character extraction if we detect potential issues
        tables = page.extract_tables()
        
        if not tables:
            return True
        
        # Check for wide columns that might be merged
        for table in tables:
            if table and len(table) > 1:
                for row in table[1:5]:  # Check first few data rows
                    for cell in row:
                        if cell and len(str(cell)) > 40:
                            return True
        
        return False
    
    def _is_better_extraction(self, new_table: Dict, 
                              existing_tables: List[Dict]) -> bool:
        """Check if new extraction is better than existing"""
        if not existing_tables:
            return True
        
        # More columns is usually better (less merging)
        new_cols = len(new_table.get('headers', []))
        max_existing_cols = max(len(t.get('headers', [])) for t in existing_tables)
        
        if new_cols > max_existing_cols * 1.2:  # 20% more columns
            return True
        
        return False


# Export for easy importing
__all__ = ['PDFPlumberExtractor', 'AVAILABLE']
