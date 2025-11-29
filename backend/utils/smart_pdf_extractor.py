"""
Smart PDF Column Extractor
==========================
Deploy to: backend/utils/smart_pdf_extractor.py

Hybrid approach for intelligent PDF table extraction:
1. Character-level X-coordinate analysis
2. Header boundary detection  
3. Pattern-based column splitting
4. Data type inference and validation
5. Self-healing when columns are merged
"""

import pdfplumber
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any
import statistics
import json
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# PATTERN DEFINITIONS FOR PAYROLL DATA
# ============================================================================

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

VALUE_PATTERNS = {
    'currency': r'^\$?[\d,]+\.\d{2}$',
    'number': r'^[\d,]+\.?\d*$',
    'hours': r'^\d{1,3}\.\d{1,2}$',
    'rate': r'^\d{1,4}\.\d{2,4}$',
    'date': r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$',
    'ssn': r'^\d{3}-?\d{2}-?\d{4}$',
    'employee_id': r'^[A-Z]?\d{4,10}$',
    'code': r'^[A-Z]{2,10}$|^\d{1,4}$',
    'text': r'^[A-Za-z\s\-\'\,\.]+$'
}

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
        self.extraction_log = []
        
    def log(self, message: str, level: str = 'info'):
        self.extraction_log.append({'level': level, 'message': message})
        if level == 'error':
            logger.error(message)
        elif level == 'warning':
            logger.warning(message)
        else:
            logger.info(message)
    
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
        }
        
        return results
    
    def _extract_page(self, page, page_num: int) -> List[Dict]:
        """Extract tables from a single page using hybrid approach"""
        tables = []
        
        chars = page.chars
        if not chars:
            self.log(f"No characters found on page {page_num + 1}", 'warning')
            return tables
        
        lines = self._group_chars_to_lines(chars)
        self.log(f"Found {len(lines)} text lines on page {page_num + 1}")
        
        header_candidates = self._find_header_rows(lines)
        self.log(f"Found {len(header_candidates)} potential header rows")
        
        for header_info in header_candidates:
            table = self._extract_table_from_header(lines, header_info, page_num)
            if table and len(table.get('rows', [])) > 0:
                tables.append(table)
        
        if not tables:
            self.log("Using fallback pdfplumber extraction", 'warning')
            tables = self._fallback_extraction(page, page_num)
        
        return tables
    
    def _group_chars_to_lines(self, chars: List[Dict]) -> List[Dict]:
        """Group characters into lines based on Y position"""
        if not chars:
            return []
        
        sorted_chars = sorted(chars, key=lambda c: (round(c['top'], 1), c['x0']))
        
        lines = []
        current_line = {'y': None, 'chars': [], 'top': None, 'bottom': None}
        y_tolerance = 3
        
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
        space_threshold = 4
        
        for char in chars:
            char_text = char.get('text', '')
            
            if current_word['x0'] is None:
                current_word = {
                    'text': char_text,
                    'x0': char['x0'],
                    'x1': char['x1']
                }
            elif char['x0'] - current_word['x1'] > space_threshold:
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
        
        if len(words) >= 3:
            score += 0.2
        
        header_terms = ['code', 'description', 'amount', 'hours', 'rate', 
                       'current', 'ytd', 'type', 'tax', 'earning', 'deduction',
                       'employee', 'name', 'id', 'gross', 'net', 'total']
        matches = sum(1 for term in header_terms if term in text)
        score += min(matches * 0.15, 0.5)
        
        if len(words) >= 2:
            x_positions = [w['x0'] for w in words]
            x_spread = max(x_positions) - min(x_positions)
            if x_spread > 200:
                score += 0.2
        
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
        
        columns = self._detect_column_boundaries(header_line)
        if not columns:
            self.log(f"Could not detect columns from header: {header_line['text'][:50]}", 'warning')
            return None
        
        self.log(f"Detected {len(columns)} columns for {section_type}")
        
        rows = []
        for i in range(header_idx + 1, len(lines)):
            line = lines[i]
            
            if self._score_as_header(line) > 0.5:
                break
            if line['word_count'] == 0:
                continue
            
            row = self._extract_row_cells(line, columns)
            if row and any(cell.strip() for cell in row):
                rows.append(row)
            
            if len(rows) >= 500:
                break
        
        if not rows:
            return None
        
        columns, rows = self._validate_and_heal(columns, rows, section_type)
        
        for col in columns:
            col['data_type'] = self._infer_column_type(col, rows)
        
        return {
            'section_type': section_type,
            'columns': columns,
            'raw_headers': [c['header'] for c in columns],
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
        
        if len(words) <= 8 and all(len(w['text']) < 20 for w in words):
            for i, word in enumerate(words):
                if i < len(words) - 1:
                    x_end = words[i + 1]['x0'] - 2
                else:
                    x_end = word['x1'] + 100
                
                columns.append({
                    'index': i,
                    'header': word['text'].strip(),
                    'x_start': word['x0'] - 5,
                    'x_end': x_end,
                    'width': x_end - word['x0'],
                    'data_type': 'unknown',
                    'sample_values': [],
                    'confidence': 0.8
                })
            return columns
        
        gaps = []
        for i in range(len(words) - 1):
            gap = words[i + 1]['x0'] - words[i]['x1']
            gaps.append((i, gap))
        
        if gaps:
            median_gap = statistics.median(g[1] for g in gaps)
            threshold = max(median_gap * 1.5, 15)
            
            groups = []
            current_group = [words[0]]
            
            for i, gap in gaps:
                if gap > threshold:
                    groups.append(current_group)
                    current_group = [words[i + 1]]
                else:
                    current_group.append(words[i + 1])
            groups.append(current_group)
            
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
            
            for i, col in enumerate(columns):
                if col['x_start'] <= word_center <= col['x_end']:
                    if cells[i]:
                        cells[i] += ' ' + word['text']
                    else:
                        cells[i] = word['text']
                    break
            else:
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
        needs_splitting = False
        for row in rows[:10]:
            for cell in row:
                if self._looks_merged(cell, section_type):
                    needs_splitting = True
                    break
        
        if needs_splitting:
            self.log("Detected merged cells, attempting to split", 'warning')
            columns, rows = self._split_merged_columns(columns, rows, section_type)
        
        return columns, rows
    
    def _looks_merged(self, cell: str, section_type: str) -> bool:
        """Check if a cell looks like it has merged data"""
        if not cell or len(cell) < 10:
            return False
        
        numbers = re.findall(r'\d+\.?\d*', cell)
        if len(numbers) >= 3:
            return True
        
        if section_type == 'earnings':
            pattern = r'[A-Z]+\s+\d+\.?\d*\s+[A-Z]+'
            if re.search(pattern, cell, re.I):
                return True
        
        return False
    
    def _split_merged_columns(self, columns: List[Dict], rows: List[List[str]], 
                              section_type: str) -> Tuple[List[Dict], List[List[str]]]:
        """Attempt to split merged columns using pattern detection"""
        merged_col_idx = None
        max_avg_len = 0
        
        for i, col in enumerate(columns):
            vals = [row[i] for row in rows if i < len(row) and row[i]]
            avg_len = statistics.mean(len(v) for v in vals) if vals else 0
            if avg_len > max_avg_len:
                max_avg_len = avg_len
                merged_col_idx = i
        
        if merged_col_idx is None or max_avg_len < 20:
            return columns, rows
        
        if section_type == 'earnings':
            return self._split_earnings_column(columns, rows, merged_col_idx)
        
        return columns, rows
    
    def _split_earnings_column(self, columns: List[Dict], rows: List[List[str]], 
                               merged_idx: int) -> Tuple[List[Dict], List[List[str]]]:
        """Split merged earnings data"""
        sample = [row[merged_idx] for row in rows[:5] if merged_idx < len(row) and row[merged_idx]]
        
        pattern = r'([A-Za-z]+)\s+([\d\.]+)\s+([\d\.]+)\s+([\d\.]+)'
        
        first_cell = sample[0] if sample else ''
        matches = re.findall(pattern, first_cell)
        
        if len(matches) > 1:
            self.log(f"Detected {len(matches)} rows merged into single cells", 'warning')
            
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
            
            new_rows = []
            for row in rows:
                if merged_idx < len(row):
                    cell = row[merged_idx]
                    matches = re.findall(pattern, cell)
                    for match in matches:
                        new_rows.append(list(match))
            
            return new_columns, new_rows
        
        return columns, rows
    
    def _infer_column_type(self, column: Dict, rows: List[List[str]]) -> str:
        """Infer the data type of a column based on values"""
        col_idx = column['index']
        values = [row[col_idx] for row in rows if col_idx < len(row) and row[col_idx]]
        
        if not values:
            return 'unknown'
        
        column['sample_values'] = values[:5]
        
        type_counts = defaultdict(int)
        
        for val in values[:20]:
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
        
        table_settings = [
            {},
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
                self.log(f"Fallback extraction failed: {e}", 'warning')
        
        return tables
    
    def _process_fallback_table(self, table: List[List], page_num: int) -> Optional[Dict]:
        """Process a table from fallback extraction"""
        if not table or len(table) < 2:
            return None
        
        headers = [str(h).strip() if h else f'Column_{i}' for i, h in enumerate(table[0])]
        rows = [[str(c).strip() if c else '' for c in row] for row in table[1:]]
        
        header_text = ' '.join(headers)
        section_type = self._classify_section(header_text)
        
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
# COLUMN SPLITTING UTILITIES
# ============================================================================

def split_by_pattern(data: list, col_idx: int, pattern: str, new_headers: list) -> tuple:
    """Split column using regex pattern with capture groups"""
    new_data = []
    compiled = re.compile(pattern)
    num_groups = compiled.groups
    
    if not new_headers or len(new_headers) != num_groups:
        new_headers = [f'Split_{i+1}' for i in range(num_groups)]
    
    for row in data:
        if col_idx >= len(row):
            new_data.append(row)
            continue
        
        cell = str(row[col_idx])
        match = compiled.search(cell)
        
        if match:
            new_row = list(row[:col_idx]) + list(match.groups()) + list(row[col_idx + 1:])
        else:
            new_row = list(row[:col_idx]) + [''] * num_groups + list(row[col_idx + 1:])
        
        new_data.append(new_row)
    
    return new_data, new_headers


def split_by_positions(data: list, col_idx: int, positions: list, new_headers: list) -> tuple:
    """Split column at specific character positions"""
    num_cols = len(positions) + 1
    if not new_headers or len(new_headers) != num_cols:
        new_headers = [f'Split_{i+1}' for i in range(num_cols)]
    
    new_data = []
    
    for row in data:
        if col_idx >= len(row):
            new_data.append(row)
            continue
        
        cell = str(row[col_idx])
        splits = []
        prev_pos = 0
        
        for pos in positions:
            splits.append(cell[prev_pos:pos].strip())
            prev_pos = pos
        splits.append(cell[prev_pos:].strip())
        
        new_row = list(row[:col_idx]) + splits + list(row[col_idx + 1:])
        new_data.append(new_row)
    
    return new_data, new_headers


def split_by_delimiter(data: list, col_idx: int, delimiter: str, new_headers: list) -> tuple:
    """Split column by delimiter"""
    max_splits = 1
    for row in data:
        if col_idx < len(row):
            parts = str(row[col_idx]).split(delimiter)
            max_splits = max(max_splits, len(parts))
    
    if not new_headers or len(new_headers) != max_splits:
        new_headers = [f'Split_{i+1}' for i in range(max_splits)]
    
    new_data = []
    
    for row in data:
        if col_idx >= len(row):
            new_data.append(row)
            continue
        
        cell = str(row[col_idx])
        parts = cell.split(delimiter)
        
        while len(parts) < max_splits:
            parts.append('')
        
        new_row = list(row[:col_idx]) + [p.strip() for p in parts] + list(row[col_idx + 1:])
        new_data.append(new_row)
    
    return new_data, new_headers


def detect_split_patterns(sample_values: list, section_type: str = 'unknown') -> list:
    """Auto-detect split patterns from sample data"""
    suggestions = []
    
    if not sample_values:
        return suggestions
    
    # Pattern 1: Code + Numbers
    pattern1 = r'([A-Za-z]+)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)'
    if _test_pattern(sample_values, pattern1):
        suggestions.append({
            'pattern': pattern1,
            'headers': ['Code', 'Value1', 'Value2', 'Value3'],
            'description': 'Code followed by 3 numbers',
            'preview': _apply_pattern_preview(sample_values[0], pattern1)
        })
    
    # Pattern 2: Multiple Code+Amount pairs (row merge)
    pattern2 = r'([A-Za-z]+)\s+([\d,]+\.?\d*)'
    if _count_pattern_matches(sample_values[0], pattern2) > 1:
        suggestions.append({
            'pattern': pattern2,
            'headers': ['Code', 'Amount'],
            'description': 'Multiple Code+Amount pairs (suggests row merge)',
            'is_row_merge': True,
            'preview': _apply_pattern_preview(sample_values[0], pattern2, multiple=True)
        })
    
    # Pattern 3: Space-separated numbers
    pattern3 = r'([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)'
    if _test_pattern(sample_values, pattern3):
        suggestions.append({
            'pattern': pattern3,
            'headers': ['Hours', 'Rate', 'Current', 'YTD'],
            'description': '4 numeric columns',
            'preview': _apply_pattern_preview(sample_values[0], pattern3)
        })
    
    # Pattern 4: Text + Numbers
    pattern4 = r'([A-Za-z\s\-]+?)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)'
    if _test_pattern(sample_values, pattern4):
        suggestions.append({
            'pattern': pattern4,
            'headers': ['Description', 'Current', 'YTD'],
            'description': 'Description followed by 2 numbers',
            'preview': _apply_pattern_preview(sample_values[0], pattern4)
        })
    
    return suggestions


def _test_pattern(values: list, pattern: str) -> bool:
    """Test if pattern matches most values"""
    matches = sum(1 for v in values if re.search(pattern, str(v)))
    return matches >= len(values) * 0.5


def _count_pattern_matches(value: str, pattern: str) -> int:
    """Count how many times pattern matches in value"""
    return len(re.findall(pattern, str(value)))


def _apply_pattern_preview(value: str, pattern: str, multiple: bool = False) -> list:
    """Show what the split would look like"""
    if multiple:
        matches = re.findall(pattern, str(value))
        return [list(m) for m in matches]
    else:
        match = re.search(pattern, str(value))
        if match:
            return list(match.groups())
        return []


# ============================================================================
# API FUNCTION
# ============================================================================

def extract_pdf_smart(pdf_path: str) -> Dict[str, Any]:
    """Main entry point for smart PDF extraction"""
    extractor = SmartPDFExtractor(pdf_path)
    return extractor.extract_all()
