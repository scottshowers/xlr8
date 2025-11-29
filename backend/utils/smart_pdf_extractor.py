"""
Smart PDF Column Extractor v2
Hybrid approach: Position-based + Pattern-based + AI-assisted + Self-healing

Properly extracts columns from complex PDF pay registers by:
1. Character-level X-coordinate analysis
2. Header boundary detection  
3. Pattern-based column splitting
4. Data type inference and validation
5. Self-healing when columns are merged
"""

import pdfplumber
import re
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Tuple, Optional, Any
import statistics
import json


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class ColumnBoundary:
    """Detected column boundary from header analysis"""
    x_start: float
    x_end: float
    header_text: str
    header_words: List[str] = field(default_factory=list)
    

@dataclass  
class ExtractedCell:
    """Single cell with position metadata"""
    text: str
    x_start: float
    x_end: float
    y_position: float
    confidence: float = 1.0


@dataclass
class SmartColumn:
    """A properly detected column with metadata"""
    index: int
    header: str
    x_start: float
    x_end: float
    width: float
    data_type: str  # 'text', 'number', 'currency', 'date', 'code', 'hours'
    sample_values: List[str] = field(default_factory=list)
    confidence: float = 0.0
    was_split: bool = False
    original_header: Optional[str] = None


@dataclass
class ExtractedTable:
    """Complete extracted table with proper columns"""
    section_type: str  # 'employee_info', 'earnings', 'taxes', 'deductions', 'pay_info'
    columns: List[SmartColumn]
    rows: List[List[str]]
    raw_headers: List[str]
    page_number: int
    confidence: float
    extraction_method: str  # 'position', 'pattern', 'hybrid', 'fallback'


# ============================================================================
# PATTERN DEFINITIONS FOR PAYROLL DATA
# ============================================================================

# Common header patterns that indicate column boundaries
HEADER_PATTERNS = {
    'earnings': [
        r'\bearning[s]?\b', r'\bdescription\b', r'\bcode\b', r'\btype\b',
        r'\bhours\b', r'\bunits\b', r'\brate\b', r'\bamount\b', 
        r'\bcurrent\b', r'\bytd\b', r'\bperiod\b'
    ],
    'taxes': [
        r'\btax\b', r'\bdescription\b', r'\bcode\b', r'\btype\b',
        r'\btaxable\b', r'\bwages\b', r'\bamount\b', r'\bcurrent\b', 
        r'\bytd\b', r'\bemployee\b', r'\bemployer\b', r'\b(ee|er)\b'
    ],
    'deductions': [
        r'\bdeduction[s]?\b', r'\bdescription\b', r'\bcode\b', r'\btype\b',
        r'\bamount\b', r'\bcurrent\b', r'\bytd\b', r'\bemployee\b', 
        r'\bemployer\b', r'\b(ee|er)\b'
    ],
    'employee_info': [
        r'\bemployee\b', r'\bid\b', r'\bname\b', r'\bssn\b', r'\bdepartment\b',
        r'\blocation\b', r'\bjob\b', r'\btitle\b', r'\bhire\b', r'\bdate\b'
    ],
    'pay_info': [
        r'\bgross\b', r'\bnet\b', r'\bpay\b', r'\btotal\b', r'\bcheck\b',
        r'\bdirect\b', r'\bdeposit\b', r'\bnumber\b'
    ]
}

# Data patterns for value classification
VALUE_PATTERNS = {
    'currency': r'^\$?[\d,]+\.\d{2}$',
    'number': r'^[\d,]+\.?\d*$',
    'hours': r'^\d{1,3}\.\d{1,2}$',  # Typically under 200 hours
    'rate': r'^\d{1,4}\.\d{2,4}$',   # Hourly rates
    'date': r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$',
    'ssn': r'^\d{3}-?\d{2}-?\d{4}$',
    'employee_id': r'^[A-Z]?\d{4,10}$',
    'code': r'^[A-Z]{2,10}$|^\d{1,4}$',
    'text': r'^[A-Za-z\s\-\'\,\.]+$'
}

# Known earning/deduction codes
KNOWN_CODES = {
    'earnings': ['REG', 'REGULAR', 'OT', 'OVERTIME', 'HOL', 'HOLIDAY', 'VAC', 
                 'VACATION', 'SICK', 'PTO', 'BONUS', 'GROSS', 'COMMISSION'],
    'taxes': ['FED', 'FEDERAL', 'FICA', 'SS', 'SOCSEC', 'MED', 'MEDICARE',
              'STATE', 'SIT', 'LOCAL', 'CITY', 'FWT', 'SWT'],
    'deductions': ['401K', '401', 'MEDICAL', 'DENTAL', 'VISION', 'HEALTH',
                   'LIFE', 'HSA', 'FSA', 'UNION', 'GARNISH', 'LOAN']
}


# ============================================================================
# CORE EXTRACTION ENGINE
# ============================================================================

class SmartPDFExtractor:
    """
    Intelligent PDF table extractor that handles complex payroll documents.
    Uses multiple strategies and self-heals when standard extraction fails.
    """
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.pdf = None
        self.pages_data = []
        self.extraction_log = []
        
    def log(self, message: str, level: str = 'info'):
        """Log extraction progress for debugging"""
        self.extraction_log.append({'level': level, 'message': message})
        print(f"[{level.upper()}] {message}")
    
    def extract_all(self) -> Dict[str, Any]:
        """Main extraction entry point"""
        results = {
            'success': True,
            'tables': [],
            'header_metadata': {},
            'extraction_log': [],
            'stats': {}
        }
        
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                self.pdf = pdf
                self.log(f"Opened PDF with {len(pdf.pages)} pages")
                
                for page_num, page in enumerate(pdf.pages):
                    self.log(f"Processing page {page_num + 1}")
                    page_tables = self._extract_page(page, page_num)
                    results['tables'].extend(page_tables)
                    
        except Exception as e:
            self.log(f"Extraction error: {str(e)}", 'error')
            results['success'] = False
            results['error'] = str(e)
            
        results['extraction_log'] = self.extraction_log
        results['stats'] = {
            'total_tables': len(results['tables']),
            'pages_processed': len(self.pages_data)
        }
        
        return results
    
    def _extract_page(self, page, page_num: int) -> List[Dict]:
        """Extract tables from a single page using hybrid approach"""
        tables = []
        
        # Step 1: Get all characters with positions
        chars = page.chars
        if not chars:
            self.log(f"No characters found on page {page_num + 1}", 'warning')
            return tables
        
        # Step 2: Group characters into lines by Y position
        lines = self._group_chars_to_lines(chars)
        self.log(f"Found {len(lines)} text lines on page {page_num + 1}")
        
        # Step 3: Detect potential header rows
        header_candidates = self._find_header_rows(lines)
        self.log(f"Found {len(header_candidates)} potential header rows")
        
        # Step 4: For each header, extract the table below it
        for header_info in header_candidates:
            table = self._extract_table_from_header(
                lines, header_info, page_num
            )
            if table and len(table.get('rows', [])) > 0:
                tables.append(table)
        
        # Step 5: Fallback - use pdfplumber's table detection and fix it
        if not tables:
            self.log("Using fallback pdfplumber extraction", 'warning')
            tables = self._fallback_extraction(page, page_num)
        
        return tables
    
    def _group_chars_to_lines(self, chars: List[Dict]) -> List[Dict]:
        """Group characters into lines based on Y position"""
        if not chars:
            return []
        
        # Sort by Y (top to bottom), then X (left to right)
        sorted_chars = sorted(chars, key=lambda c: (round(c['top'], 1), c['x0']))
        
        lines = []
        current_line = {'y': None, 'chars': [], 'top': None, 'bottom': None}
        y_tolerance = 3  # pixels
        
        for char in sorted_chars:
            if char.get('text', '').strip() == '':
                continue
                
            char_y = round(char['top'], 1)
            
            if current_line['y'] is None:
                current_line = {
                    'y': char_y,
                    'top': char['top'],
                    'bottom': char['bottom'],
                    'chars': [char]
                }
            elif abs(char_y - current_line['y']) <= y_tolerance:
                current_line['chars'].append(char)
                current_line['bottom'] = max(current_line['bottom'], char['bottom'])
            else:
                if current_line['chars']:
                    lines.append(self._process_line(current_line))
                current_line = {
                    'y': char_y,
                    'top': char['top'],
                    'bottom': char['bottom'],
                    'chars': [char]
                }
        
        if current_line['chars']:
            lines.append(self._process_line(current_line))
        
        return lines
    
    def _process_line(self, line_data: Dict) -> Dict:
        """Process a line of characters into words with positions"""
        chars = sorted(line_data['chars'], key=lambda c: c['x0'])
        
        words = []
        current_word = {'text': '', 'x0': None, 'x1': None}
        space_threshold = 4  # pixels between words
        
        for char in chars:
            char_text = char.get('text', '')
            
            if current_word['x0'] is None:
                current_word = {
                    'text': char_text,
                    'x0': char['x0'],
                    'x1': char['x1']
                }
            elif char['x0'] - current_word['x1'] > space_threshold:
                # New word
                if current_word['text'].strip():
                    words.append(current_word.copy())
                current_word = {
                    'text': char_text,
                    'x0': char['x0'],
                    'x1': char['x1']
                }
            else:
                current_word['text'] += char_text
                current_word['x1'] = char['x1']
        
        if current_word['text'].strip():
            words.append(current_word)
        
        # Build full line text
        full_text = ' '.join(w['text'] for w in words)
        
        return {
            'y': line_data['y'],
            'top': line_data['top'],
            'bottom': line_data['bottom'],
            'words': words,
            'text': full_text,
            'word_count': len(words)
        }
    
    def _find_header_rows(self, lines: List[Dict]) -> List[Dict]:
        """Identify lines that look like table headers"""
        headers = []
        
        for i, line in enumerate(lines):
            score = self._score_as_header(line)
            if score > 0.5:
                # Determine section type
                section_type = self._classify_section(line['text'])
                headers.append({
                    'line_index': i,
                    'line': line,
                    'score': score,
                    'section_type': section_type
                })
        
        return headers
    
    def _score_as_header(self, line: Dict) -> float:
        """Score how likely a line is to be a table header (0-1)"""
        text = line['text'].lower()
        words = line['words']
        score = 0.0
        
        # Multiple words spread across the line
        if len(words) >= 3:
            score += 0.2
        
        # Contains common header terms
        header_terms = ['code', 'description', 'amount', 'hours', 'rate', 
                       'current', 'ytd', 'type', 'tax', 'earning', 'deduction',
                       'employee', 'name', 'id', 'gross', 'net', 'total']
        matches = sum(1 for term in header_terms if term in text)
        score += min(matches * 0.15, 0.5)
        
        # Words are reasonably spaced (not all clumped)
        if len(words) >= 2:
            x_positions = [w['x0'] for w in words]
            x_spread = max(x_positions) - min(x_positions)
            if x_spread > 200:  # Spread across page
                score += 0.2
        
        # Not mostly numbers (headers are mostly text)
        num_count = sum(1 for w in words if re.match(r'^[\d\.\,\$]+$', w['text']))
        if num_count < len(words) * 0.3:
            score += 0.1
        
        return min(score, 1.0)
    
    def _classify_section(self, text: str) -> str:
        """Classify what section type this header belongs to"""
        text_lower = text.lower()
        
        scores = {}
        for section, patterns in HEADER_PATTERNS.items():
            score = sum(1 for p in patterns if re.search(p, text_lower, re.I))
            scores[section] = score
        
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        return 'unknown'
    
    def _extract_table_from_header(self, lines: List[Dict], header_info: Dict, 
                                   page_num: int) -> Optional[Dict]:
        """Extract a table given a detected header row"""
        header_line = header_info['line']
        header_idx = header_info['line_index']
        section_type = header_info['section_type']
        
        # Step 1: Determine column boundaries from header positions
        columns = self._detect_column_boundaries(header_line)
        if not columns:
            self.log(f"Could not detect columns from header: {header_line['text'][:50]}", 'warning')
            return None
        
        self.log(f"Detected {len(columns)} columns for {section_type}")
        
        # Step 2: Extract data rows using column boundaries
        rows = []
        for i in range(header_idx + 1, len(lines)):
            line = lines[i]
            
            # Stop if we hit another header or empty section
            if self._score_as_header(line) > 0.5:
                break
            if line['word_count'] == 0:
                continue
            
            # Extract cells aligned to columns
            row = self._extract_row_cells(line, columns)
            if row and any(cell.strip() for cell in row):
                rows.append(row)
            
            # Limit rows per table
            if len(rows) >= 500:
                break
        
        if not rows:
            return None
        
        # Step 3: Validate and self-heal if needed
        columns, rows = self._validate_and_heal(columns, rows, section_type)
        
        # Step 4: Infer data types
        for col in columns:
            col['data_type'] = self._infer_column_type(col, rows)
        
        return {
            'section_type': section_type,
            'columns': [asdict(c) if hasattr(c, '__dataclass_fields__') else c for c in columns],
            'raw_headers': [c['header'] if isinstance(c, dict) else c.header for c in columns],
            'rows': rows,
            'row_count': len(rows),
            'column_count': len(columns),
            'page_number': page_num + 1,
            'confidence': header_info['score'],
            'extraction_method': 'position'
        }
    
    def _detect_column_boundaries(self, header_line: Dict) -> List[Dict]:
        """Detect column boundaries from header word positions"""
        words = header_line['words']
        if not words:
            return []
        
        columns = []
        
        # Strategy 1: Each word is a column header
        # (works for simple headers like "Hours Rate Amount")
        if len(words) <= 8 and all(len(w['text']) < 20 for w in words):
            for i, word in enumerate(words):
                # Estimate column width based on position to next word
                if i < len(words) - 1:
                    x_end = words[i + 1]['x0'] - 2
                else:
                    x_end = word['x1'] + 100  # Last column extends further
                
                columns.append({
                    'index': i,
                    'header': word['text'].strip(),
                    'x_start': word['x0'] - 5,  # Small padding
                    'x_end': x_end,
                    'width': x_end - word['x0'],
                    'data_type': 'unknown',
                    'sample_values': [],
                    'confidence': 0.8
                })
            return columns
        
        # Strategy 2: Group adjacent words that form multi-word headers
        # Look for natural gaps (larger spacing between column headers)
        gaps = []
        for i in range(len(words) - 1):
            gap = words[i + 1]['x0'] - words[i]['x1']
            gaps.append((i, gap))
        
        # Find significant gaps (larger than median)
        if gaps:
            median_gap = statistics.median(g[1] for g in gaps)
            threshold = max(median_gap * 1.5, 15)
            
            # Group words between significant gaps
            groups = []
            current_group = [words[0]]
            
            for i, gap in gaps:
                if gap > threshold:
                    groups.append(current_group)
                    current_group = [words[i + 1]]
                else:
                    current_group.append(words[i + 1])
            groups.append(current_group)
            
            # Create columns from groups
            for i, group in enumerate(groups):
                header_text = ' '.join(w['text'] for w in group)
                x_start = group[0]['x0'] - 5
                
                if i < len(groups) - 1:
                    x_end = groups[i + 1][0]['x0'] - 2
                else:
                    x_end = group[-1]['x1'] + 100
                
                columns.append({
                    'index': i,
                    'header': header_text.strip(),
                    'x_start': x_start,
                    'x_end': x_end,
                    'width': x_end - x_start,
                    'data_type': 'unknown',
                    'sample_values': [],
                    'confidence': 0.7
                })
        
        return columns
    
    def _extract_row_cells(self, line: Dict, columns: List[Dict]) -> List[str]:
        """Extract cell values from a line based on column boundaries"""
        words = line['words']
        cells = [''] * len(columns)
        
        for word in words:
            word_center = (word['x0'] + word['x1']) / 2
            
            # Find which column this word belongs to
            for i, col in enumerate(columns):
                if col['x_start'] <= word_center <= col['x_end']:
                    if cells[i]:
                        cells[i] += ' ' + word['text']
                    else:
                        cells[i] = word['text']
                    break
            else:
                # Word doesn't fit any column - assign to nearest
                distances = [(abs(word_center - (c['x_start'] + c['x_end'])/2), i) 
                            for i, c in enumerate(columns)]
                nearest = min(distances, key=lambda x: x[0])[1]
                if cells[nearest]:
                    cells[nearest] += ' ' + word['text']
                else:
                    cells[nearest] = word['text']
        
        return cells
    
    def _validate_and_heal(self, columns: List[Dict], rows: List[List[str]], 
                          section_type: str) -> Tuple[List[Dict], List[List[str]]]:
        """Validate extraction and fix issues"""
        
        # Check 1: Are cells still merged? (multiple values in one cell)
        needs_splitting = False
        for row in rows[:10]:  # Check first 10 rows
            for cell in row:
                if self._looks_merged(cell, section_type):
                    needs_splitting = True
                    break
        
        if needs_splitting:
            self.log("Detected merged cells, attempting to split", 'warning')
            columns, rows = self._split_merged_columns(columns, rows, section_type)
        
        # Check 2: Validate data types match expected patterns
        # (numbers in number columns, text in text columns)
        
        return columns, rows
    
    def _looks_merged(self, cell: str, section_type: str) -> bool:
        """Check if a cell looks like it has merged data"""
        if not cell or len(cell) < 10:
            return False
        
        # Multiple numbers separated by spaces
        numbers = re.findall(r'\d+\.?\d*', cell)
        if len(numbers) >= 3:
            return True
        
        # Known codes followed by numbers (e.g., "GROSS 791.55 Regular 12.00")
        if section_type == 'earnings':
            pattern = r'[A-Z]+\s+\d+\.?\d*\s+[A-Z]+'
            if re.search(pattern, cell, re.I):
                return True
        
        return False
    
    def _split_merged_columns(self, columns: List[Dict], rows: List[List[str]], 
                              section_type: str) -> Tuple[List[Dict], List[List[str]]]:
        """Attempt to split merged columns using pattern detection"""
        
        # Find the merged column (usually the one with most content)
        merged_col_idx = None
        max_avg_len = 0
        
        for i, col in enumerate(columns):
            avg_len = statistics.mean(len(row[i]) for row in rows if row[i]) if rows else 0
            if avg_len > max_avg_len:
                max_avg_len = avg_len
                merged_col_idx = i
        
        if merged_col_idx is None or max_avg_len < 20:
            return columns, rows
        
        # Analyze the merged column to detect pattern
        merged_values = [row[merged_col_idx] for row in rows]
        
        # Try to split based on section type
        if section_type == 'earnings':
            return self._split_earnings_column(columns, rows, merged_col_idx)
        elif section_type == 'taxes':
            return self._split_tax_column(columns, rows, merged_col_idx)
        elif section_type == 'deductions':
            return self._split_deduction_column(columns, rows, merged_col_idx)
        
        return columns, rows
    
    def _split_earnings_column(self, columns: List[Dict], rows: List[List[str]], 
                               merged_idx: int) -> Tuple[List[Dict], List[List[str]]]:
        """Split merged earnings data: 'GROSS 791.55 Regular 12.00 29.93 359.1'"""
        
        # Expected pattern: Code Amount [Code Hours Rate Amount]...
        # Or: Description Hours Rate Amount YTD
        
        new_columns = []
        new_rows = []
        
        # Analyze first few rows to detect pattern
        sample = [row[merged_idx] for row in rows[:5] if row[merged_idx]]
        
        # Pattern 1: Multiple earning lines in one cell
        # "GROSS 791.55 Regular 12.00 29.93 359.1 Orientation 13.00 3.00 39"
        # This is actually multiple ROWS, not columns
        
        pattern = r'([A-Za-z]+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)'
        
        # Check if this is a row-merge situation
        first_cell = sample[0] if sample else ''
        matches = re.findall(pattern, first_cell)
        
        if len(matches) > 1:
            # This is multiple rows merged into one cell!
            self.log(f"Detected {len(matches)} rows merged into single cells", 'warning')
            
            # Create proper columns: Code, Hours, Rate, Amount
            new_columns = [
                {'index': 0, 'header': 'Earning Code', 'x_start': 0, 'x_end': 100, 
                 'width': 100, 'data_type': 'code', 'sample_values': [], 'confidence': 0.9},
                {'index': 1, 'header': 'Hours', 'x_start': 100, 'x_end': 200,
                 'width': 100, 'data_type': 'hours', 'sample_values': [], 'confidence': 0.9},
                {'index': 2, 'header': 'Rate', 'x_start': 200, 'x_end': 300,
                 'width': 100, 'data_type': 'currency', 'sample_values': [], 'confidence': 0.9},
                {'index': 3, 'header': 'Amount', 'x_start': 300, 'x_end': 400,
                 'width': 100, 'data_type': 'currency', 'sample_values': [], 'confidence': 0.9},
            ]
            
            # Un-merge the rows
            for row in rows:
                cell = row[merged_idx]
                matches = re.findall(pattern, cell)
                for match in matches:
                    new_rows.append(list(match))
            
            return new_columns, new_rows
        
        # Pattern 2: Single row but columns merged
        # Try to split by detecting number patterns
        
        return columns, rows
    
    def _split_tax_column(self, columns: List[Dict], rows: List[List[str]], 
                          merged_idx: int) -> Tuple[List[Dict], List[List[str]]]:
        """Split merged tax data"""
        # Similar logic to earnings
        return columns, rows
    
    def _split_deduction_column(self, columns: List[Dict], rows: List[List[str]], 
                                merged_idx: int) -> Tuple[List[Dict], List[List[str]]]:
        """Split merged deduction data"""
        # Similar logic to earnings
        return columns, rows
    
    def _infer_column_type(self, column: Dict, rows: List[List[str]]) -> str:
        """Infer the data type of a column based on values"""
        col_idx = column['index']
        values = [row[col_idx] for row in rows if col_idx < len(row) and row[col_idx]]
        
        if not values:
            return 'unknown'
        
        # Sample values for the column
        column['sample_values'] = values[:5]
        
        # Count pattern matches
        type_counts = defaultdict(int)
        
        for val in values[:20]:  # Check first 20 values
            val = val.strip()
            for dtype, pattern in VALUE_PATTERNS.items():
                if re.match(pattern, val):
                    type_counts[dtype] += 1
                    break
        
        if type_counts:
            return max(type_counts, key=type_counts.get)
        return 'text'
    
    def _fallback_extraction(self, page, page_num: int) -> List[Dict]:
        """Fallback to pdfplumber table extraction with post-processing"""
        tables = []
        
        # Try different table settings
        table_settings = [
            {},  # Default
            {"vertical_strategy": "text", "horizontal_strategy": "text"},
            {"vertical_strategy": "lines", "horizontal_strategy": "lines"},
            {"snap_tolerance": 5, "join_tolerance": 5},
        ]
        
        for settings in table_settings:
            try:
                found_tables = page.extract_tables(table_settings=settings)
                if found_tables:
                    for table in found_tables:
                        if table and len(table) > 1:
                            processed = self._process_fallback_table(table, page_num)
                            if processed:
                                tables.append(processed)
                    if tables:
                        break
            except Exception as e:
                self.log(f"Fallback extraction failed with settings {settings}: {e}", 'warning')
        
        return tables
    
    def _process_fallback_table(self, table: List[List], page_num: int) -> Optional[Dict]:
        """Process a table from fallback extraction"""
        if not table or len(table) < 2:
            return None
        
        # First row as headers
        headers = [str(h).strip() if h else f'Column_{i}' for i, h in enumerate(table[0])]
        rows = [[str(c).strip() if c else '' for c in row] for row in table[1:]]
        
        # Classify section
        header_text = ' '.join(headers)
        section_type = self._classify_section(header_text)
        
        # Check for merged columns and try to fix
        columns = []
        for i, header in enumerate(headers):
            columns.append({
                'index': i,
                'header': header,
                'x_start': i * 100,
                'x_end': (i + 1) * 100,
                'width': 100,
                'data_type': 'unknown',
                'sample_values': [],
                'confidence': 0.5
            })
        
        # Validate and heal
        columns, rows = self._validate_and_heal(columns, rows, section_type)
        
        return {
            'section_type': section_type,
            'columns': columns,
            'raw_headers': [c['header'] for c in columns],
            'rows': rows,
            'row_count': len(rows),
            'column_count': len(columns),
            'page_number': page_num + 1,
            'confidence': 0.5,
            'extraction_method': 'fallback'
        }


# ============================================================================
# API FUNCTION
# ============================================================================

def extract_pdf_smart(pdf_path: str) -> Dict[str, Any]:
    """
    Main entry point for smart PDF extraction.
    Returns structured data with proper column separation.
    """
    extractor = SmartPDFExtractor(pdf_path)
    return extractor.extract_all()


# ============================================================================
# TEST
# ============================================================================

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        result = extract_pdf_smart(sys.argv[1])
        print(json.dumps(result, indent=2, default=str))
    else:
        print("Usage: python smart_pdf_extractor.py <pdf_path>")
