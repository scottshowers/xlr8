"""
Multi-Method PDF Extraction Engine
Tests ALL available libraries and returns scored results
"""

import logging
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)

# Import all available libraries (gracefully handle missing ones)
AVAILABLE_METHODS = {}

try:
    import fitz  # PyMuPDF
    AVAILABLE_METHODS['pymupdf'] = True
except ImportError:
    AVAILABLE_METHODS['pymupdf'] = False
    logger.warning("PyMuPDF not available")

try:
    import pdfplumber
    AVAILABLE_METHODS['pdfplumber'] = True
except ImportError:
    AVAILABLE_METHODS['pdfplumber'] = False
    logger.warning("pdfplumber not available")

try:
    import camelot
    AVAILABLE_METHODS['camelot'] = True
except ImportError:
    AVAILABLE_METHODS['camelot'] = False
    logger.warning("Camelot not available")

try:
    import tabula
    AVAILABLE_METHODS['tabula'] = True
except ImportError:
    AVAILABLE_METHODS['tabula'] = False
    logger.warning("Tabula not available")

try:
    from pdf2image import convert_from_path
    import pytesseract
    AVAILABLE_METHODS['ocr'] = True
except ImportError:
    AVAILABLE_METHODS['ocr'] = False
    logger.warning("OCR tools not available")

try:
    import PyPDF2
    AVAILABLE_METHODS['pypdf2'] = True
except ImportError:
    AVAILABLE_METHODS['pypdf2'] = False
    logger.warning("PyPDF2 not available")


class MultiMethodExtractor:
    """
    Extraction engine that tries ALL available methods and returns scored results.
    Each method is tried on each section independently.
    """
    
    def __init__(self):
        self.available_methods = {k: v for k, v in AVAILABLE_METHODS.items() if v}
        logger.info(f"Available extraction methods: {list(self.available_methods.keys())}")
    
    def extract_all_methods(self, pdf_path: str, section_bbox: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Try ALL available extraction methods on a section.
        
        Args:
            pdf_path: Path to PDF
            section_bbox: Optional bounding box {x0, y0, x1, y1, page} for section
            
        Returns:
            Dict with results from each method and scores
        """
        results = {}
        
        if self.available_methods.get('pymupdf'):
            results['pymupdf'] = self._extract_pymupdf(pdf_path, section_bbox)
        
        if self.available_methods.get('pdfplumber'):
            results['pdfplumber'] = self._extract_pdfplumber(pdf_path, section_bbox)
        
        if self.available_methods.get('camelot'):
            results['camelot'] = self._extract_camelot(pdf_path, section_bbox)
        
        if self.available_methods.get('tabula'):
            results['tabula'] = self._extract_tabula(pdf_path, section_bbox)
        
        if self.available_methods.get('ocr'):
            results['ocr'] = self._extract_ocr(pdf_path, section_bbox)
        
        if self.available_methods.get('pypdf2'):
            results['pypdf2'] = self._extract_pypdf2(pdf_path, section_bbox)
        
        return results
    
    def _extract_pymupdf(self, pdf_path: str, bbox: Optional[Dict] = None) -> Dict[str, Any]:
        """Extract using PyMuPDF with coordinate-based extraction."""
        try:
            doc = fitz.open(pdf_path)
            
            if bbox:
                # Extract specific region
                page = doc[bbox.get('page', 0)]
                rect = fitz.Rect(bbox['x0'], bbox['y0'], bbox['x1'], bbox['y1'])
                text = page.get_text("text", clip=rect)
                words = page.get_text("words", clip=rect)
            else:
                # Extract full document
                text = ""
                words = []
                for page in doc:
                    text += page.get_text("text")
                    words.extend(page.get_text("words"))
            
            doc.close()
            
            # Parse text into structured data
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            # Try to detect table structure
            table_data = self._parse_text_to_table(lines, words)
            
            return {
                'success': True,
                'text': text,
                'lines': lines,
                'words': words,
                'table_data': table_data,
                'method': 'pymupdf'
            }
            
        except Exception as e:
            logger.error(f"PyMuPDF extraction error: {str(e)}")
            return {'success': False, 'error': str(e), 'method': 'pymupdf'}
    
    def _extract_pdfplumber(self, pdf_path: str, bbox: Optional[Dict] = None) -> Dict[str, Any]:
        """Extract using pdfplumber with table detection."""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if bbox:
                    # Extract specific region
                    page = pdf.pages[bbox.get('page', 0)]
                    cropped = page.crop((bbox['x0'], bbox['y0'], bbox['x1'], bbox['y1']))
                    text = cropped.extract_text()
                    tables = cropped.extract_tables()
                    words = cropped.extract_words()
                else:
                    # Extract full document
                    text = ""
                    tables = []
                    words = []
                    for page in pdf.pages:
                        text += page.extract_text() or ""
                        tables.extend(page.extract_tables() or [])
                        words.extend(page.extract_words() or [])
            
            # Convert tables to DataFrames
            table_dfs = []
            for table in tables:
                if table:
                    df = pd.DataFrame(table[1:], columns=table[0] if table else None)
                    table_dfs.append(df)
            
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            return {
                'success': True,
                'text': text,
                'lines': lines,
                'tables': tables,
                'table_dfs': table_dfs,
                'words': words,
                'method': 'pdfplumber'
            }
            
        except Exception as e:
            logger.error(f"pdfplumber extraction error: {str(e)}")
            return {'success': False, 'error': str(e), 'method': 'pdfplumber'}
    
    def _extract_camelot(self, pdf_path: str, bbox: Optional[Dict] = None) -> Dict[str, Any]:
        """Extract using Camelot for advanced table detection."""
        try:
            if bbox:
                # Camelot uses different coordinate system
                table_areas = [f"{bbox['x0']},{bbox['y0']},{bbox['x1']},{bbox['y1']}"]
                tables = camelot.read_pdf(
                    pdf_path,
                    pages=str(bbox.get('page', 0) + 1),
                    flavor='lattice',
                    table_areas=table_areas
                )
            else:
                tables = camelot.read_pdf(pdf_path, pages='all', flavor='lattice')
            
            # Convert to DataFrames
            table_dfs = [table.df for table in tables]
            
            return {
                'success': True,
                'tables': tables,
                'table_dfs': table_dfs,
                'n_tables': len(tables),
                'method': 'camelot'
            }
            
        except Exception as e:
            logger.error(f"Camelot extraction error: {str(e)}")
            return {'success': False, 'error': str(e), 'method': 'camelot'}
    
    def _extract_tabula(self, pdf_path: str, bbox: Optional[Dict] = None) -> Dict[str, Any]:
        """Extract using Tabula for table detection."""
        try:
            if bbox:
                # Tabula area format: [top, left, bottom, right]
                area = [bbox['y0'], bbox['x0'], bbox['y1'], bbox['x1']]
                tables = tabula.read_pdf(
                    pdf_path,
                    pages=bbox.get('page', 0) + 1,
                    area=area,
                    multiple_tables=True
                )
            else:
                tables = tabula.read_pdf(pdf_path, pages='all', multiple_tables=True)
            
            return {
                'success': True,
                'table_dfs': tables,
                'n_tables': len(tables),
                'method': 'tabula'
            }
            
        except Exception as e:
            logger.error(f"Tabula extraction error: {str(e)}")
            return {'success': False, 'error': str(e), 'method': 'tabula'}
    
    def _extract_ocr(self, pdf_path: str, bbox: Optional[Dict] = None) -> Dict[str, Any]:
        """Extract using OCR for scanned/image PDFs."""
        try:
            # Convert PDF to images
            images = convert_from_path(pdf_path, dpi=300)
            
            all_text = ""
            for i, image in enumerate(images):
                if bbox and i != bbox.get('page', 0):
                    continue
                
                if bbox:
                    # Crop to bbox
                    cropped = image.crop((bbox['x0'], bbox['y0'], bbox['x1'], bbox['y1']))
                    text = pytesseract.image_to_string(cropped)
                else:
                    text = pytesseract.image_to_string(image)
                
                all_text += text + "\n"
            
            lines = [line.strip() for line in all_text.split('\n') if line.strip()]
            
            return {
                'success': True,
                'text': all_text,
                'lines': lines,
                'method': 'ocr'
            }
            
        except Exception as e:
            logger.error(f"OCR extraction error: {str(e)}")
            return {'success': False, 'error': str(e), 'method': 'ocr'}
    
    def _extract_pypdf2(self, pdf_path: str, bbox: Optional[Dict] = None) -> Dict[str, Any]:
        """Extract using PyPDF2 for basic text extraction."""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                
                if bbox:
                    page = reader.pages[bbox.get('page', 0)]
                    text = page.extract_text()
                else:
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text()
            
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            return {
                'success': True,
                'text': text,
                'lines': lines,
                'method': 'pypdf2'
            }
            
        except Exception as e:
            logger.error(f"PyPDF2 extraction error: {str(e)}")
            return {'success': False, 'error': str(e), 'method': 'pypdf2'}
    
    def _parse_text_to_table(self, lines: List[str], words: List) -> Optional[pd.DataFrame]:
        """
        Try to parse text lines into table structure.
        Used for methods that don't detect tables automatically.
        """
        if not lines:
            return None
        
        try:
            # Simple heuristic: look for lines with multiple numbers
            table_rows = []
            for line in lines:
                # Count numbers in line
                import re
                numbers = re.findall(r'[\d,]+\.?\d*', line)
                if len(numbers) >= 2:  # Likely a data row
                    table_rows.append(line)
            
            if not table_rows:
                return None
            
            # Try to split into columns (very basic)
            data = []
            for row in table_rows:
                # Split by multiple spaces
                parts = [p.strip() for p in re.split(r'\s{2,}', row) if p.strip()]
                data.append(parts)
            
            if data:
                return pd.DataFrame(data)
            
        except Exception as e:
            logger.error(f"Text to table parsing error: {str(e)}")
        
        return None
    
    def score_extraction(self, result: Dict[str, Any], section_type: str) -> float:
        """
        Score extraction result based on section type and data quality.
        
        Returns score 0-100
        """
        if not result.get('success'):
            return 0.0
        
        score = 0.0
        
        # Base score for success
        score += 20
        
        # Check for structured data (tables)
        if result.get('table_dfs'):
            tables = result['table_dfs']
            if tables:
                score += 30
                # Bonus for multiple tables
                score += min(len(tables) * 5, 20)
        elif result.get('tables'):
            score += 25
        
        # Check text quality
        text = result.get('text', '')
        if text:
            score += 10
            # Bonus for substantial text
            if len(text) > 100:
                score += 10
        
        # Check for lines/structure
        lines = result.get('lines', [])
        if len(lines) > 5:
            score += 10
        
        # Section-specific scoring
        if section_type == 'employee_info':
            # Look for employee indicators
            if any(keyword in text.lower() for keyword in ['emp #', 'employee', 'name', 'id']):
                score += 10
        
        elif section_type == 'earnings':
            # Look for earnings indicators
            if any(keyword in text.lower() for keyword in ['hours', 'rate', 'regular', 'overtime', 'earnings']):
                score += 10
        
        elif section_type == 'taxes':
            # Look for tax indicators
            if any(keyword in text.lower() for keyword in ['federal', 'fica', 'state', 'medicare', 'tax']):
                score += 10
        
        elif section_type == 'deductions':
            # Look for deduction indicators
            if any(keyword in text.lower() for keyword in ['401k', 'insurance', 'deduction', 'benefit']):
                score += 10
        
        return min(score, 100.0)
    
    def get_best_method(self, results: Dict[str, Any], section_type: str) -> Tuple[str, Dict[str, Any]]:
        """
        Get the best extraction method for a section based on scores.
        
        Returns:
            Tuple of (method_name, result_dict)
        """
        scored_results = []
        
        for method_name, result in results.items():
            score = self.score_extraction(result, section_type)
            scored_results.append((method_name, result, score))
        
        # Sort by score descending
        scored_results.sort(key=lambda x: x[2], reverse=True)
        
        if scored_results:
            best_method, best_result, best_score = scored_results[0]
            logger.info(f"Best method for {section_type}: {best_method} ({best_score:.1f}%)")
            return best_method, best_result
        
        return None, None
