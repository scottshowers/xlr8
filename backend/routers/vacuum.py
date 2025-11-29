"""
Vacuum Smart Extraction API
Endpoints for intelligent PDF column extraction with self-healing
"""

from flask import Blueprint, request, jsonify
import os
import json
import traceback
from smart_pdf_extractor import extract_pdf_smart, SmartPDFExtractor

vacuum_smart_bp = Blueprint('vacuum_smart', __name__)

UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', '/tmp/uploads')


@vacuum_smart_bp.route('/api/vacuum/smart-extract', methods=['POST'])
def smart_extract():
    """
    Perform smart extraction on an uploaded PDF.
    Uses position-based column detection with self-healing.
    """
    try:
        data = request.get_json() or {}
        filename = data.get('filename')
        
        if not filename:
            return jsonify({'error': 'No filename provided'}), 400
        
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        if not os.path.exists(filepath):
            return jsonify({'error': f'File not found: {filename}'}), 404
        
        # Run smart extraction
        result = extract_pdf_smart(filepath)
        
        return jsonify(result)
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@vacuum_smart_bp.route('/api/vacuum/split-column', methods=['POST'])
def split_column():
    """
    Manually split a merged column based on user-defined pattern.
    
    Request body:
    {
        "extract_id": "...",
        "column_index": 0,
        "split_method": "pattern" | "positions" | "delimiter",
        "pattern": "([A-Z]+)\\s+([\\d.]+)\\s+([\\d.]+)\\s+([\\d.]+)",
        "new_headers": ["Code", "Hours", "Rate", "Amount"],
        "positions": [10, 20, 30],  // For position-based split
        "delimiter": "|"  // For delimiter-based split
    }
    """
    try:
        data = request.get_json() or {}
        
        extract_id = data.get('extract_id')
        column_index = data.get('column_index', 0)
        split_method = data.get('split_method', 'pattern')
        pattern = data.get('pattern')
        new_headers = data.get('new_headers', [])
        positions = data.get('positions', [])
        delimiter = data.get('delimiter')
        
        # Load the extract from database
        from supabase_client import get_supabase
        supabase = get_supabase()
        
        result = supabase.table('vacuum_extracts').select('*').eq('id', extract_id).single().execute()
        if not result.data:
            return jsonify({'error': 'Extract not found'}), 404
        
        extract = result.data
        raw_data = extract.get('raw_data', [])
        raw_headers = extract.get('raw_headers', [])
        
        if not raw_data:
            return jsonify({'error': 'No data to split'}), 400
        
        # Perform the split
        if split_method == 'pattern' and pattern:
            new_data, new_cols = split_by_pattern(raw_data, column_index, pattern, new_headers)
        elif split_method == 'positions' and positions:
            new_data, new_cols = split_by_positions(raw_data, column_index, positions, new_headers)
        elif split_method == 'delimiter' and delimiter:
            new_data, new_cols = split_by_delimiter(raw_data, column_index, delimiter, new_headers)
        else:
            return jsonify({'error': 'Invalid split method or missing parameters'}), 400
        
        # Build new headers list
        new_raw_headers = raw_headers[:column_index] + new_cols + raw_headers[column_index + 1:]
        
        # Update the extract
        update_result = supabase.table('vacuum_extracts').update({
            'raw_data': new_data,
            'raw_headers': new_raw_headers,
            'column_count': len(new_raw_headers),
            'was_manually_split': True,
            'split_details': {
                'method': split_method,
                'original_column': column_index,
                'pattern': pattern,
                'new_columns': new_cols
            }
        }).eq('id', extract_id).execute()
        
        return jsonify({
            'success': True,
            'new_headers': new_raw_headers,
            'new_column_count': len(new_raw_headers),
            'rows_processed': len(new_data),
            'preview': new_data[:5]
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def split_by_pattern(data: list, col_idx: int, pattern: str, new_headers: list) -> tuple:
    """Split column using regex pattern with capture groups"""
    import re
    
    new_data = []
    compiled = re.compile(pattern)
    num_groups = compiled.groups
    
    # Generate default headers if not provided
    if not new_headers or len(new_headers) != num_groups:
        new_headers = [f'Split_{i+1}' for i in range(num_groups)]
    
    for row in data:
        if col_idx >= len(row):
            new_data.append(row)
            continue
        
        cell = str(row[col_idx])
        match = compiled.search(cell)
        
        if match:
            # Replace original column with matched groups
            new_row = list(row[:col_idx]) + list(match.groups()) + list(row[col_idx + 1:])
        else:
            # Keep original with empty placeholders
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
    
    # First pass: determine max splits
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
        
        # Pad with empty strings if needed
        while len(parts) < max_splits:
            parts.append('')
        
        new_row = list(row[:col_idx]) + [p.strip() for p in parts] + list(row[col_idx + 1:])
        new_data.append(new_row)
    
    return new_data, new_headers


@vacuum_smart_bp.route('/api/vacuum/detect-pattern', methods=['POST'])
def detect_pattern():
    """
    Auto-detect split pattern from sample data.
    Returns suggested patterns and how they would split the data.
    """
    try:
        data = request.get_json() or {}
        sample_values = data.get('sample_values', [])
        section_type = data.get('section_type', 'unknown')
        
        if not sample_values:
            return jsonify({'error': 'No sample values provided'}), 400
        
        suggestions = []
        
        # Pattern 1: Code + Numbers (earnings/deductions)
        pattern1 = r'([A-Za-z]+)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)'
        headers1 = ['Code', 'Value1', 'Value2', 'Value3']
        if test_pattern(sample_values, pattern1):
            suggestions.append({
                'pattern': pattern1,
                'headers': headers1,
                'description': 'Code followed by 3 numbers',
                'preview': apply_pattern_preview(sample_values[0], pattern1)
            })
        
        # Pattern 2: Multiple Code+Amount pairs
        pattern2 = r'([A-Za-z]+)\s+([\d,]+\.?\d*)'
        if count_pattern_matches(sample_values[0], pattern2) > 1:
            suggestions.append({
                'pattern': pattern2,
                'headers': ['Code', 'Amount'],
                'description': 'Multiple Code+Amount pairs (suggests row merge)',
                'is_row_merge': True,
                'preview': apply_pattern_preview(sample_values[0], pattern2, multiple=True)
            })
        
        # Pattern 3: Space-separated numbers
        pattern3 = r'([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)'
        if test_pattern(sample_values, pattern3):
            # Guess column types based on values
            suggestions.append({
                'pattern': pattern3,
                'headers': ['Hours', 'Rate', 'Current', 'YTD'],
                'description': '4 numeric columns',
                'preview': apply_pattern_preview(sample_values[0], pattern3)
            })
        
        # Pattern 4: Text + Numbers
        pattern4 = r'([A-Za-z\s\-]+?)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)'
        if test_pattern(sample_values, pattern4):
            suggestions.append({
                'pattern': pattern4,
                'headers': ['Description', 'Current', 'YTD'],
                'description': 'Description followed by 2 numbers',
                'preview': apply_pattern_preview(sample_values[0], pattern4)
            })
        
        return jsonify({
            'suggestions': suggestions,
            'sample_analyzed': sample_values[0][:100] if sample_values else ''
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def test_pattern(values: list, pattern: str) -> bool:
    """Test if pattern matches most values"""
    import re
    matches = sum(1 for v in values if re.search(pattern, str(v)))
    return matches >= len(values) * 0.5


def count_pattern_matches(value: str, pattern: str) -> int:
    """Count how many times pattern matches in value"""
    import re
    return len(re.findall(pattern, str(value)))


def apply_pattern_preview(value: str, pattern: str, multiple: bool = False) -> list:
    """Show what the split would look like"""
    import re
    if multiple:
        matches = re.findall(pattern, str(value))
        return [list(m) for m in matches]
    else:
        match = re.search(pattern, str(value))
        if match:
            return list(match.groups())
        return []


@vacuum_smart_bp.route('/api/vacuum/reprocess-with-settings', methods=['POST'])
def reprocess_with_settings():
    """
    Re-extract a PDF with custom column detection settings.
    Allows user to provide hints about column structure.
    """
    try:
        data = request.get_json() or {}
        filename = data.get('filename')
        settings = data.get('settings', {})
        
        # Settings can include:
        # - column_count: Expected number of columns
        # - header_row: Which row contains headers (0-indexed)
        # - column_boundaries: Manual X positions for columns
        # - section_hints: Which sections to expect
        
        if not filename:
            return jsonify({'error': 'No filename provided'}), 400
        
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404
        
        # Custom extraction with settings
        extractor = SmartPDFExtractor(filepath)
        extractor.custom_settings = settings
        result = extractor.extract_all()
        
        return jsonify(result)
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
