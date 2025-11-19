"""
Section Detector - Identifies Employee Info, Earnings, Taxes, Deductions sections
Works with multiple PDF layouts and vendors
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import fitz
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False
    logger.warning("PyMuPDF not available")

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    logger.warning("pdfplumber not available")


class SectionDetector:
    """
    Detects the 4 required sections in payroll PDFs using keyword matching.
    Returns bounding boxes for each section.
    """
    
    def __init__(self):
        self.section_keywords = {
            'employee_info': [
                'employee', 'emp #', 'emp#', 'empid', 'employee id', 'emp id',
                'name', 'department', 'dept', 'ssn', 'social security',
                'hire date', 'pay period', 'status', 'position', 'location'
            ],
            'earnings': [
                'earnings', 'hours', 'rate', 'amount', 'regular', 'overtime',
                'holiday', 'vacation', 'sick', 'pto', 'wages', 'gross',
                'regular pay', 'ot pay', 'bonus', 'commission'
            ],
            'taxes': [
                'taxes', 'federal', 'fica', 'state', 'medicare', 'social security',
                'withholding', 'fit', 'sit', 'ss tax', 'med tax', 'futa', 'suta',
                'local tax', 'city tax'
            ],
            'deductions': [
                'deductions', '401k', 'insurance', 'health', 'dental', 'vision',
                'life', 'retirement', 'benefit', 'pre-tax', 'post-tax',
                'garnishment', 'child support', 'union dues'
            ]
        }
    
    def detect_sections(self, pdf_path: str) -> Dict[str, Any]:
        """
        Detect all 4 sections in the PDF.
        
        Returns:
            Dict with section info: {
                'employee_info': {'bbox': ..., 'confidence': ..., 'page': ...},
                'earnings': {...},
                'taxes': {...},
                'deductions': {...}
            }
        """
        sections = {
            'employee_info': None,
            'earnings': None,
            'taxes': None,
            'deductions': None
        }
        
        # Try both detection methods
        pdfplumber_result = None
        pymupdf_result = None
        
        if PDFPLUMBER_AVAILABLE:
            pdfplumber_result = self._detect_with_pdfplumber(pdf_path)
        
        if FITZ_AVAILABLE:
            pymupdf_result = self._detect_with_pymupdf(pdf_path)
        
        # Merge results (prefer higher confidence)
        for section_type in sections.keys():
            candidates = []
            
            if pdfplumber_result and pdfplumber_result.get(section_type):
                candidates.append(pdfplumber_result[section_type])
            
            if pymupdf_result and pymupdf_result.get(section_type):
                candidates.append(pymupdf_result[section_type])
            
            if candidates:
                # Pick highest confidence
                best = max(candidates, key=lambda x: x.get('confidence', 0))
                sections[section_type] = best
        
        logger.info(f"Section detection complete: {sum(1 for s in sections.values() if s)} sections found")
        
        return sections
    
    def _detect_with_pdfplumber(self, pdf_path: str) -> Dict[str, Any]:
        """Detect sections using pdfplumber."""
        try:
            sections = {}
            
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_height = page.height
                    page_width = page.width
                    
                    # Extract words with positions
                    words = page.extract_words(x_tolerance=3, y_tolerance=3)
                    
                    # Find section headers
                    for word in words:
                        text = word['text'].lower()
                        
                        # Check each section type
                        for section_type, keywords in self.section_keywords.items():
                            if section_type in sections:
                                continue  # Already found
                            
                            # Check if this word matches section keywords
                            for keyword in keywords:
                                if keyword in text or text in keyword:
                                    # Found potential section header
                                    confidence = self._calculate_confidence(text, section_type)
                                    
                                    if confidence > 0.5:  # Threshold
                                        # Estimate section bbox
                                        # Header is at y0, section extends down
                                        y0 = word['top']
                                        y1 = y0 + (page_height - y0) * 0.3  # Assume 30% of remaining page
                                        
                                        sections[section_type] = {
                                            'bbox': {
                                                'x0': 0,
                                                'y0': y0,
                                                'x1': page_width,
                                                'y1': min(y1, page_height),
                                                'page': page_num
                                            },
                                            'confidence': confidence,
                                            'header_text': word['text'],
                                            'method': 'pdfplumber'
                                        }
                                        break
            
            return sections
            
        except Exception as e:
            logger.error(f"pdfplumber detection error: {str(e)}")
            return {}
    
    def _detect_with_pymupdf(self, pdf_path: str) -> Dict[str, Any]:
        """Detect sections using PyMuPDF."""
        try:
            sections = {}
            doc = fitz.open(pdf_path)
            
            for page_num, page in enumerate(doc):
                page_height = page.rect.height
                page_width = page.rect.width
                
                # Get text blocks with positions
                blocks = page.get_text("dict")["blocks"]
                
                for block in blocks:
                    if "lines" not in block:
                        continue
                    
                    # Extract text from block
                    block_text = ""
                    for line in block["lines"]:
                        for span in line["spans"]:
                            block_text += span["text"] + " "
                    
                    block_text = block_text.lower().strip()
                    
                    # Check for section keywords
                    for section_type, keywords in self.section_keywords.items():
                        if section_type in sections:
                            continue
                        
                        for keyword in keywords:
                            if keyword in block_text:
                                confidence = self._calculate_confidence(block_text, section_type)
                                
                                if confidence > 0.5:
                                    bbox = block["bbox"]
                                    
                                    # Extend bbox to cover section
                                    y0 = bbox[1]
                                    y1 = y0 + (page_height - y0) * 0.3
                                    
                                    sections[section_type] = {
                                        'bbox': {
                                            'x0': 0,
                                            'y0': y0,
                                            'x1': page_width,
                                            'y1': min(y1, page_height),
                                            'page': page_num
                                        },
                                        'confidence': confidence,
                                        'header_text': block_text[:50],
                                        'method': 'pymupdf'
                                    }
                                    break
            
            doc.close()
            return sections
            
        except Exception as e:
            logger.error(f"PyMuPDF detection error: {str(e)}")
            return {}
    
    def _calculate_confidence(self, text: str, section_type: str) -> float:
        """Calculate confidence score for section detection."""
        text_lower = text.lower()
        keywords = self.section_keywords[section_type]
        
        matches = sum(1 for keyword in keywords if keyword in text_lower)
        confidence = min(matches / 3.0, 1.0)  # Max 3 keywords needed for 100%
        
        # Boost if exact section name appears
        if section_type.replace('_', ' ') in text_lower:
            confidence = min(confidence + 0.3, 1.0)
        
        return confidence
    
    def expand_section_boundaries(self, sections: Dict[str, Any], pdf_path: str) -> Dict[str, Any]:
        """
        Refine section boundaries to capture full content.
        Looks for next section header or end of page.
        """
        # Sort sections by y-position
        sorted_sections = []
        for section_type, info in sections.items():
            if info:
                sorted_sections.append((section_type, info))
        
        sorted_sections.sort(key=lambda x: (x[1]['bbox']['page'], x[1]['bbox']['y0']))
        
        # Adjust boundaries
        for i, (section_type, info) in enumerate(sorted_sections):
            if i < len(sorted_sections) - 1:
                # Set y1 to start of next section
                next_info = sorted_sections[i + 1][1]
                if info['bbox']['page'] == next_info['bbox']['page']:
                    info['bbox']['y1'] = next_info['bbox']['y0']
        
        return sections
