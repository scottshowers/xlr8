"""
Smart PDF Analyzer - Routes PDF content to the right storage
============================================================

PROBLEM SOLVED:
PDFs with tabular data (like Workers' Comp Rates) were being chunked
into ChromaDB where they can't be queried effectively.

SOLUTION:
1. Analyze PDF structure using pdfplumber
2. Detect tables vs narrative text
3. Route tables → DuckDB (SQL queryable)
4. Route text → ChromaDB (semantic search)
5. Track BOTH in document registry

SELF-HEALING:
- If table extraction fails → falls back to text-only
- If DuckDB fails → still chunks to ChromaDB
- Always registers what was stored where

Author: XLR8 Team
"""

import logging
import os
import re
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)

# Try to import pdfplumber for table detection
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    logger.warning("pdfplumber not available - PDF table detection disabled")

# Try to import DuckDB handler
try:
    from utils.structured_data_handler import get_structured_handler
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False
    logger.warning("Structured data handler not available - PDF tables will use RAG only")


class SmartPDFAnalyzer:
    """
    Analyzes PDFs and intelligently routes content to appropriate storage.
    
    Detection heuristics:
    - Table ratio: pages with tables vs total pages
    - Column consistency: same columns across pages = likely one big table
    - Numeric density: lots of numbers = likely data, not narrative
    - Header patterns: repeated headers = multi-page table
    """
    
    def __init__(self):
        self.analysis_results = {}
    
    def analyze(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze a PDF and determine its content type.
        
        Returns:
            {
                'is_tabular': bool,          # Primary content is tables
                'is_text': bool,              # Primary content is narrative text
                'is_mixed': bool,             # Both tables and significant text
                'table_pages': [1, 2, 3],     # Pages with detected tables
                'text_pages': [4, 5],         # Pages with primarily text
                'tables': [DataFrame, ...],   # Extracted tables (if tabular)
                'text_content': str,          # Extracted text
                'confidence': float,          # 0-1 confidence in classification
                'recommendation': str,        # 'duckdb', 'chromadb', or 'both'
                'metadata': {...}             # Additional info
            }
        """
        if not PDFPLUMBER_AVAILABLE:
            logger.warning("[SMART-PDF] pdfplumber not available, defaulting to text extraction")
            return self._default_text_result(file_path)
        
        try:
            logger.info(f"[SMART-PDF] Analyzing: {file_path}")
            
            with pdfplumber.open(file_path) as pdf:
                total_pages = len(pdf.pages)
                
                if total_pages == 0:
                    return self._empty_result()
                
                # Analyze each page
                page_analyses = []
                all_tables = []
                all_text = []
                table_pages = []
                text_pages = []
                
                # Track column patterns for consistency detection
                column_signatures = []
                
                for page_num, page in enumerate(pdf.pages, start=1):
                    page_result = self._analyze_page(page, page_num)
                    page_analyses.append(page_result)
                    
                    if page_result['has_table']:
                        table_pages.append(page_num)
                        all_tables.extend(page_result['tables'])
                        
                        # Track column signature
                        for table in page_result['tables']:
                            if isinstance(table, pd.DataFrame):
                                sig = tuple(table.columns.tolist())
                                column_signatures.append(sig)
                    
                    if page_result['has_text']:
                        text_pages.append(page_num)
                        all_text.append(page_result['text'])
                
                # Calculate metrics
                table_ratio = len(table_pages) / total_pages if total_pages > 0 else 0
                
                logger.warning(f"[SMART-PDF] Pages analyzed: {total_pages}, Table pages: {len(table_pages)}, Table ratio: {table_ratio:.2f}")
                logger.warning(f"[SMART-PDF] Total tables found: {len(all_tables)}")
                
                # Check column consistency (same table structure across pages)
                column_consistent = False
                if column_signatures:
                    unique_sigs = set(column_signatures)
                    column_consistent = len(unique_sigs) == 1
                
                # Determine content type
                is_tabular = table_ratio > 0.5 or (table_ratio > 0.3 and column_consistent)
                is_text = len(text_pages) > len(table_pages) and table_ratio < 0.3
                is_mixed = 0.3 <= table_ratio <= 0.7 or (len(table_pages) > 0 and len(text_pages) > 2)
                
                # Confidence based on clarity of classification
                if is_tabular and table_ratio > 0.8:
                    confidence = 0.95
                elif is_text and table_ratio < 0.1:
                    confidence = 0.95
                elif is_mixed:
                    confidence = 0.7
                else:
                    confidence = 0.8
                
                # Recommendation
                if is_tabular:
                    recommendation = 'duckdb'
                elif is_mixed:
                    recommendation = 'both'
                else:
                    recommendation = 'chromadb'
                
                logger.warning(f"[SMART-PDF] Decision: is_tabular={is_tabular}, is_text={is_text}, is_mixed={is_mixed} -> {recommendation}")
                
                # Combine tables if they have consistent structure
                combined_df = None
                if all_tables and column_consistent:
                    try:
                        combined_df = pd.concat(all_tables, ignore_index=True)
                        logger.info(f"[SMART-PDF] Combined {len(all_tables)} tables into single DataFrame with {len(combined_df)} rows")
                    except Exception as e:
                        logger.warning(f"[SMART-PDF] Could not combine tables: {e}")
                
                result = {
                    'is_tabular': is_tabular,
                    'is_text': is_text,
                    'is_mixed': is_mixed,
                    'table_pages': table_pages,
                    'text_pages': text_pages,
                    'tables': all_tables,
                    'combined_table': combined_df,
                    'text_content': '\n\n'.join(all_text),
                    'confidence': confidence,
                    'recommendation': recommendation,
                    'metadata': {
                        'total_pages': total_pages,
                        'table_ratio': table_ratio,
                        'column_consistent': column_consistent,
                        'total_tables': len(all_tables),
                        'total_rows': len(combined_df) if combined_df is not None else sum(len(t) for t in all_tables if isinstance(t, pd.DataFrame)),
                        'analysis_date': datetime.now().isoformat()
                    }
                }
                
                logger.info(f"[SMART-PDF] Analysis complete: is_tabular={is_tabular}, table_ratio={table_ratio:.2f}, recommendation={recommendation}")
                
                return result
                
        except Exception as e:
            logger.error(f"[SMART-PDF] Analysis failed: {e}")
            return self._default_text_result(file_path)
    
    def _analyze_page(self, page, page_num: int) -> Dict[str, Any]:
        """Analyze a single page for tables and text content."""
        result = {
            'page_num': page_num,
            'has_table': False,
            'has_text': False,
            'tables': [],
            'text': '',
            'numeric_density': 0
        }
        
        try:
            # Try to extract tables using pdfplumber's built-in detection
            tables = page.extract_tables()
            
            logger.warning(f"[SMART-PDF] Page {page_num}: pdfplumber found {len(tables) if tables else 0} raw tables")
            
            if tables:
                for table in tables:
                    if table and len(table) > 1:  # Has header + at least one row
                        try:
                            # Clean up table
                            cleaned = self._clean_table(table)
                            if cleaned is not None and len(cleaned) > 0:
                                result['tables'].append(cleaned)
                                result['has_table'] = True
                        except Exception as e:
                            logger.debug(f"[SMART-PDF] Table cleanup failed on page {page_num}: {e}")
            
            # Extract text
            text = page.extract_text() or ''
            
            # FALLBACK: If no tables found, try to detect columnar structure in text
            if not result['has_table'] and text:
                logger.warning(f"[SMART-PDF] Page {page_num}: No tables found, trying columnar detection on {len(text)} chars...")
                columnar_df = self._detect_columnar_text(text, page_num)
                if columnar_df is not None and len(columnar_df) >= 3:  # At least 3 data rows
                    result['tables'].append(columnar_df)
                    result['has_table'] = True
                    logger.warning(f"[SMART-PDF] Page {page_num}: Detected columnar text -> {len(columnar_df)} rows")
            
            # Check if text is substantial (not just table leftovers)
            # Remove numbers and punctuation to check for real text
            text_only = re.sub(r'[0-9.,\-/\s]+', ' ', text)
            word_count = len([w for w in text_only.split() if len(w) > 2])
            
            if word_count > 20:  # Substantial text content
                result['has_text'] = True
                result['text'] = f"--- Page {page_num} ---\n{text}"
            
            # Calculate numeric density
            if text:
                numbers = re.findall(r'\d+\.?\d*', text)
                result['numeric_density'] = len(numbers) / max(len(text.split()), 1)
            
        except Exception as e:
            logger.debug(f"[SMART-PDF] Page {page_num} analysis error: {e}")
        
        return result
    
    def _detect_columnar_text(self, text: str, page_num: int) -> Optional[pd.DataFrame]:
        """
        Detect columnar/tabular data in plain text.
        
        Works for:
        - Space-aligned columns (fixed width)
        - Tab-separated data
        - Consistent field patterns
        """
        lines = text.strip().split('\n')
        logger.warning(f"[SMART-PDF] Page {page_num} columnar check: {len(lines)} lines in text")
        
        if len(lines) < 3:  # Need header + at least 2 data rows
            return None
        
        # Log first few lines to see structure
        for i, line in enumerate(lines[:5]):
            logger.warning(f"[SMART-PDF] Page {page_num} line {i}: '{line[:100]}...' " if len(line) > 100 else f"[SMART-PDF] Page {page_num} line {i}: '{line}'")
        
        # Strategy 1: Detect by consistent whitespace positions
        # Find lines that look like data rows (contain numbers)
        data_lines = []
        potential_header = None
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Check if line has numeric content (likely a data row)
            has_numbers = bool(re.search(r'\d+\.?\d*', line))
            
            # Check if line has multiple "columns" (separated by 2+ spaces or tabs)
            parts = re.split(r'\s{2,}|\t', line)
            parts = [p.strip() for p in parts if p.strip()]
            
            if len(parts) >= 3:  # At least 3 columns
                if has_numbers:
                    data_lines.append((i, parts))
                elif potential_header is None and i < 5:  # Likely header in first few lines
                    potential_header = (i, parts)
        
        logger.warning(f"[SMART-PDF] Page {page_num}: Found {len(data_lines)} potential data rows with 3+ columns")
        
        if len(data_lines) < 3:  # Not enough data rows
            return None
        
        # Check column count consistency
        col_counts = [len(parts) for _, parts in data_lines]
        most_common_cols = max(set(col_counts), key=col_counts.count)
        
        logger.warning(f"[SMART-PDF] Page {page_num}: Most common column count: {most_common_cols}")
        
        # Filter to rows with consistent column count
        consistent_rows = [(i, parts) for i, parts in data_lines if len(parts) == most_common_cols]
        
        if len(consistent_rows) < 3:
            return None
        
        # Build DataFrame
        try:
            data = [parts for _, parts in consistent_rows]
            
            # Determine headers
            if potential_header and len(potential_header[1]) == most_common_cols:
                headers = potential_header[1]
            else:
                # Use first consistent row as header if it looks like text
                first_row = data[0]
                if all(not re.match(r'^[\d.,\-]+$', cell) for cell in first_row):
                    headers = first_row
                    data = data[1:]
                else:
                    headers = [f'Col_{i+1}' for i in range(most_common_cols)]
            
            if len(data) < 2:
                return None
            
            df = pd.DataFrame(data, columns=headers)
            logger.warning(f"[SMART-PDF] Page {page_num}: Columnar detection SUCCESS - {len(df)} rows x {len(df.columns)} cols")
            return df
            
        except Exception as e:
            logger.warning(f"[SMART-PDF] Page {page_num}: Columnar parsing failed: {e}")
            return None
    
    def _clean_table(self, raw_table: List[List]) -> Optional[pd.DataFrame]:
        """Clean up a raw table and convert to DataFrame."""
        if not raw_table or len(raw_table) < 2:
            return None
        
        # First row is header
        headers = raw_table[0]
        data = raw_table[1:]
        
        # Clean headers
        clean_headers = []
        for i, h in enumerate(headers):
            if h:
                # Clean whitespace and normalize
                clean = str(h).strip().replace('\n', ' ')
                clean_headers.append(clean if clean else f'Column_{i+1}')
            else:
                clean_headers.append(f'Column_{i+1}')
        
        # Create DataFrame
        try:
            df = pd.DataFrame(data, columns=clean_headers)
            
            # Remove completely empty rows
            df = df.dropna(how='all')
            
            # Remove duplicate header rows (common in multi-page tables)
            if len(df) > 0:
                header_as_row = [str(h).lower().strip() for h in clean_headers]
                mask = df.apply(lambda row: [str(v).lower().strip() if v else '' for v in row] != header_as_row, axis=1)
                df = df[mask]
            
            return df if len(df) > 0 else None
            
        except Exception as e:
            logger.debug(f"[SMART-PDF] DataFrame creation failed: {e}")
            return None
    
    def _default_text_result(self, file_path: str) -> Dict[str, Any]:
        """Fallback result when smart analysis isn't available."""
        text = ""
        try:
            import PyPDF2
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() or ''
        except:
            pass
        
        return {
            'is_tabular': False,
            'is_text': True,
            'is_mixed': False,
            'table_pages': [],
            'text_pages': list(range(1, 100)),  # Unknown
            'tables': [],
            'combined_table': None,
            'text_content': text,
            'confidence': 0.5,
            'recommendation': 'chromadb',
            'metadata': {
                'fallback': True,
                'analysis_date': datetime.now().isoformat()
            }
        }
    
    def _empty_result(self) -> Dict[str, Any]:
        """Result for empty or unreadable PDFs."""
        return {
            'is_tabular': False,
            'is_text': False,
            'is_mixed': False,
            'table_pages': [],
            'text_pages': [],
            'tables': [],
            'combined_table': None,
            'text_content': '',
            'confidence': 0,
            'recommendation': 'skip',
            'metadata': {'empty': True}
        }


def store_pdf_tables_to_duckdb(
    tables: List[pd.DataFrame],
    combined_table: Optional[pd.DataFrame],
    project: str,
    filename: str,
    metadata: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Store extracted PDF tables into DuckDB.
    
    Returns:
        {
            'success': bool,
            'tables_created': List[str],
            'total_rows': int,
            'error': str (if failed)
        }
    """
    if not DUCKDB_AVAILABLE:
        return {'success': False, 'error': 'DuckDB handler not available'}
    
    try:
        handler = get_structured_handler()
        
        # Prefer combined table if available (one big table across pages)
        if combined_table is not None and len(combined_table) > 0:
            result = handler.store_dataframe(
                df=combined_table,
                project=project,
                filename=filename,
                sheet_name='pdf_table'
            )
            return {
                'success': True,
                'tables_created': result.get('tables_created', []),
                'total_rows': len(combined_table)
            }
        
        # Otherwise store each table separately
        tables_created = []
        total_rows = 0
        
        for i, table in enumerate(tables):
            if isinstance(table, pd.DataFrame) and len(table) > 0:
                sheet_name = f'table_{i+1}'
                result = handler.store_dataframe(
                    df=table,
                    project=project,
                    filename=filename,
                    sheet_name=sheet_name
                )
                tables_created.extend(result.get('tables_created', []))
                total_rows += len(table)
        
        return {
            'success': True,
            'tables_created': tables_created,
            'total_rows': total_rows
        }
        
    except Exception as e:
        logger.error(f"[SMART-PDF] DuckDB storage failed: {e}")
        return {'success': False, 'error': str(e)}


def smart_process_pdf(
    file_path: str,
    project: str,
    filename: str,
    project_id: Optional[str] = None,
    status_callback=None  # Function to update status
) -> Dict[str, Any]:
    """
    Smart PDF processing - analyzes and routes to appropriate storage.
    
    Args:
        file_path: Path to PDF file
        project: Project name
        filename: Original filename
        project_id: Optional project UUID
        status_callback: Optional function(message, progress) for status updates
    
    Returns:
        {
            'success': bool,
            'analysis': {...},
            'duckdb_result': {...},
            'chromadb_result': {...},
            'storage_used': ['duckdb', 'chromadb'],
            'error': str (if failed)
        }
    """
    result = {
        'success': False,
        'analysis': None,
        'duckdb_result': None,
        'chromadb_result': None,
        'storage_used': [],
        'error': None
    }
    
    def update_status(msg, progress=None):
        if status_callback:
            status_callback(msg, progress)
        logger.info(f"[SMART-PDF] {msg}")
    
    try:
        # Step 1: Analyze the PDF
        update_status("Analyzing PDF structure...", 10)
        analyzer = SmartPDFAnalyzer()
        analysis = analyzer.analyze(file_path)
        result['analysis'] = analysis
        
        recommendation = analysis.get('recommendation', 'chromadb')
        update_status(f"Analysis complete: {recommendation} recommended (confidence: {analysis.get('confidence', 0):.0%})", 30)
        
        # Step 2: Route based on recommendation
        if recommendation in ['duckdb', 'both'] and analysis.get('tables'):
            update_status("Storing tables in DuckDB for SQL queries...", 50)
            
            duckdb_result = store_pdf_tables_to_duckdb(
                tables=analysis.get('tables', []),
                combined_table=analysis.get('combined_table'),
                project=project,
                filename=filename,
                metadata={'project_id': project_id}
            )
            result['duckdb_result'] = duckdb_result
            
            if duckdb_result.get('success'):
                result['storage_used'].append('duckdb')
                update_status(f"✓ Stored {duckdb_result.get('total_rows', 0)} rows in DuckDB", 60)
            else:
                update_status(f"⚠ DuckDB storage failed: {duckdb_result.get('error')}", 60)
        
        # Step 3: Also/alternatively store in ChromaDB for semantic search
        if recommendation in ['chromadb', 'both'] or not result['storage_used']:
            update_status("Chunking content for semantic search...", 70)
            
            # This returns text content - the actual ChromaDB storage happens in upload.py
            text_content = analysis.get('text_content', '')
            
            if not text_content and analysis.get('tables'):
                # Convert tables to text for ChromaDB if no narrative text
                text_parts = []
                for i, table in enumerate(analysis.get('tables', [])):
                    if isinstance(table, pd.DataFrame):
                        text_parts.append(f"Table {i+1}:\n{table.to_string()}")
                text_content = '\n\n'.join(text_parts)
            
            result['chromadb_result'] = {
                'text_content': text_content,
                'text_length': len(text_content)
            }
            result['storage_used'].append('chromadb')
            update_status(f"✓ Prepared {len(text_content):,} characters for semantic search", 80)
        
        result['success'] = len(result['storage_used']) > 0
        update_status(f"Processing complete. Storage: {', '.join(result['storage_used'])}", 100)
        
    except Exception as e:
        result['error'] = str(e)
        logger.error(f"[SMART-PDF] Processing failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    return result


# =============================================================================
# SINGLETON ACCESSOR
# =============================================================================
_analyzer_instance = None

def get_smart_analyzer() -> SmartPDFAnalyzer:
    """Get singleton analyzer instance."""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = SmartPDFAnalyzer()
    return _analyzer_instance


# Alias for backward compatibility
process_pdf_intelligently = smart_process_pdf
