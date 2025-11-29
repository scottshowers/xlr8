"""
Layout Detector
================
Analyzes document structure locally before extraction.
Identifies sections, tables, and key-value regions.

Deploy to: backend/extraction/layout_detector.py
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
import re

logger = logging.getLogger(__name__)

# Try PDF libraries
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False


@dataclass
class LayoutRegion:
    """A detected region in the document"""
    region_type: str  # 'header', 'table', 'key_value', 'text', 'footer'
    bbox: Dict[str, float]  # {left, top, right, bottom} as percentages
    page: int
    confidence: float
    section_hint: Optional[str] = None  # employee_info, earnings, etc.
    column_count: int = 0
    row_count: int = 0
    has_border: bool = False


@dataclass
class PageLayout:
    """Layout information for a single page"""
    page_num: int
    width: float
    height: float
    regions: List[LayoutRegion]
    text_blocks: List[Dict]


@dataclass
class DocumentLayout:
    """Complete document layout"""
    page_count: int
    pages: List[PageLayout]
    detected_vendor: Optional[str] = None
    document_type: Optional[str] = None
    is_pay_register: bool = False
    confidence: float = 0.0
    employee_blocks: List[Dict] = field(default_factory=list)


class LayoutDetector:
    """
    Detects document layout and structure.
    
    Key features:
    - Identifies document type (pay register, invoice, etc.)
    - Detects repeating employee blocks
    - Finds table regions and key-value sections
    - Provides bounding boxes for guided extraction
    """
    
    # Keywords that suggest document type
    PAY_REGISTER_KEYWORDS = [
        'earnings', 'deductions', 'taxes', 'gross pay', 'net pay',
        'pay period', 'check date', 'ytd', 'federal', 'fica',
        'employee', 'hours', 'rate', 'withholding'
    ]
    
    # Vendor signatures (text patterns that identify vendor)
    VENDOR_SIGNATURES = {
        'ADP': [r'ADP', r'Automatic Data Processing'],
        'Paychex': [r'Paychex', r'PEO Services'],
        'Paylocity': [r'Paylocity'],
        'Paycom': [r'Paycom'],
        'UKG': [r'UKG', r'Ultimate Software', r'Kronos'],
        'Workday': [r'Workday'],
        'Ceridian': [r'Ceridian', r'Dayforce'],
        'Gusto': [r'Gusto'],
        'Quickbooks': [r'QuickBooks', r'Intuit'],
    }
    
    # Section header patterns
    SECTION_PATTERNS = {
        'employee_info': [
            r'employee\s*info', r'employee\s*data', r'personal\s*info',
            r'emp\s*id', r'employee\s*name'
        ],
        'earnings': [
            r'earnings', r'pay\s*code', r'hours\s*&\s*earnings',
            r'current\s*earnings', r'gross\s*earnings'
        ],
        'taxes': [
            r'tax', r'withhold', r'federal', r'state\s*tax',
            r'fica', r'medicare'
        ],
        'deductions': [
            r'deduction', r'benefit', r'401k', r'medical',
            r'pre-?tax', r'post-?tax'
        ],
        'pay_totals': [
            r'pay\s*summary', r'net\s*pay', r'gross\s*pay',
            r'total', r'check\s*amount'
        ]
    }
    
    def __init__(self):
        if not PYMUPDF_AVAILABLE and not PDFPLUMBER_AVAILABLE:
            logger.warning("No PDF library available for layout detection")
    
    def detect_layout(self, file_path: str) -> DocumentLayout:
        """
        Detect the layout structure of a document.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            DocumentLayout with detected structure
        """
        layout = DocumentLayout(
            page_count=0,
            pages=[],
            confidence=0.0
        )
        
        try:
            if PYMUPDF_AVAILABLE:
                layout = self._detect_with_pymupdf(file_path)
            elif PDFPLUMBER_AVAILABLE:
                layout = self._detect_with_pdfplumber(file_path)
            
            # Analyze for pay register characteristics
            self._analyze_document_type(layout)
            
            # Detect repeating employee blocks
            self._detect_employee_blocks(layout)
            
        except Exception as e:
            logger.error(f"Layout detection failed: {e}", exc_info=True)
        
        return layout
    
    def _detect_with_pymupdf(self, file_path: str) -> DocumentLayout:
        """Detect layout using PyMuPDF"""
        doc = fitz.open(file_path)
        
        pages = []
        all_text = ""
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_width = page.rect.width
            page_height = page.rect.height
            
            regions = []
            text_blocks = []
            
            # Get text blocks
            blocks = page.get_text("dict")["blocks"]
            
            for block in blocks:
                if block.get("type") == 0:  # Text block
                    bbox = block.get("bbox", [0, 0, 0, 0])
                    text = ""
                    
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text += span.get("text", "") + " "
                    
                    text = text.strip()
                    all_text += text + "\n"
                    
                    if text:
                        # Normalize bbox to percentages
                        norm_bbox = {
                            'left': bbox[0] / page_width,
                            'top': bbox[1] / page_height,
                            'right': bbox[2] / page_width,
                            'bottom': bbox[3] / page_height
                        }
                        
                        text_blocks.append({
                            'text': text,
                            'bbox': norm_bbox,
                            'font_size': self._get_avg_font_size(block)
                        })
                        
                        # Check if this looks like a section header
                        section_hint = self._identify_section(text)
                        
                        regions.append(LayoutRegion(
                            region_type='text',
                            bbox=norm_bbox,
                            page=page_num + 1,
                            confidence=0.8,
                            section_hint=section_hint
                        ))
            
            # Detect tables
            tables = page.find_tables()
            for table in tables:
                bbox = table.bbox
                norm_bbox = {
                    'left': bbox[0] / page_width,
                    'top': bbox[1] / page_height,
                    'right': bbox[2] / page_width,
                    'bottom': bbox[3] / page_height
                }
                
                regions.append(LayoutRegion(
                    region_type='table',
                    bbox=norm_bbox,
                    page=page_num + 1,
                    confidence=0.85,
                    column_count=table.col_count,
                    row_count=table.row_count
                ))
            
            pages.append(PageLayout(
                page_num=page_num + 1,
                width=page_width,
                height=page_height,
                regions=regions,
                text_blocks=text_blocks
            ))
        
        doc.close()
        
        # Detect vendor from text
        detected_vendor = self._detect_vendor(all_text)
        
        return DocumentLayout(
            page_count=len(pages),
            pages=pages,
            detected_vendor=detected_vendor,
            confidence=0.75
        )
    
    def _detect_with_pdfplumber(self, file_path: str) -> DocumentLayout:
        """Detect layout using pdfplumber"""
        pages = []
        all_text = ""
        
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                page_width = page.width
                page_height = page.height
                
                regions = []
                text_blocks = []
                
                # Get text
                text = page.extract_text() or ""
                all_text += text + "\n"
                
                # Detect tables
                tables = page.find_tables()
                for table in tables:
                    bbox = table.bbox
                    norm_bbox = {
                        'left': bbox[0] / page_width,
                        'top': bbox[1] / page_height,
                        'right': bbox[2] / page_width,
                        'bottom': bbox[3] / page_height
                    }
                    
                    # Try to identify section from nearby text
                    section_hint = None
                    for line in text.split('\n'):
                        section_hint = self._identify_section(line)
                        if section_hint:
                            break
                    
                    regions.append(LayoutRegion(
                        region_type='table',
                        bbox=norm_bbox,
                        page=page_num + 1,
                        confidence=0.8,
                        section_hint=section_hint,
                        column_count=len(table.cells[0]) if table.cells else 0,
                        row_count=len(table.cells) if table.cells else 0
                    ))
                
                pages.append(PageLayout(
                    page_num=page_num + 1,
                    width=page_width,
                    height=page_height,
                    regions=regions,
                    text_blocks=text_blocks
                ))
        
        detected_vendor = self._detect_vendor(all_text)
        
        return DocumentLayout(
            page_count=len(pages),
            pages=pages,
            detected_vendor=detected_vendor,
            confidence=0.7
        )
    
    def _get_avg_font_size(self, block: Dict) -> float:
        """Get average font size in a text block"""
        sizes = []
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                sizes.append(span.get("size", 10))
        return sum(sizes) / len(sizes) if sizes else 10
    
    def _detect_vendor(self, text: str) -> Optional[str]:
        """Detect vendor from document text"""
        text_upper = text.upper()
        
        for vendor, patterns in self.VENDOR_SIGNATURES.items():
            for pattern in patterns:
                if re.search(pattern, text_upper, re.IGNORECASE):
                    return vendor
        
        return None
    
    def _identify_section(self, text: str) -> Optional[str]:
        """Identify which section a text block belongs to"""
        text_lower = text.lower()
        
        for section, patterns in self.SECTION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return section
        
        return None
    
    def _analyze_document_type(self, layout: DocumentLayout):
        """Analyze document to determine if it's a pay register"""
        # Collect all text from layout
        all_text = ""
        for page in layout.pages:
            for block in page.text_blocks:
                all_text += block.get('text', '') + " "
        
        all_text_lower = all_text.lower()
        
        # Count pay register keywords
        keyword_count = sum(
            1 for keyword in self.PAY_REGISTER_KEYWORDS 
            if keyword in all_text_lower
        )
        
        # Calculate confidence
        if keyword_count >= 5:
            layout.is_pay_register = True
            layout.document_type = 'pay_register'
            layout.confidence = min(0.5 + (keyword_count * 0.1), 0.98)
        elif keyword_count >= 3:
            layout.is_pay_register = True
            layout.document_type = 'pay_register'
            layout.confidence = 0.3 + (keyword_count * 0.1)
    
    def _detect_employee_blocks(self, layout: DocumentLayout):
        """
        Detect repeating employee blocks in the document.
        This is key for pay registers where each employee has
        their own section that repeats.
        """
        # Look for repeating vertical patterns
        employee_blocks = []
        
        for page in layout.pages:
            tables = [r for r in page.regions if r.region_type == 'table']
            
            if len(tables) >= 2:
                # Check if tables have similar structure (repeating pattern)
                first_cols = tables[0].column_count
                
                similar_tables = [
                    t for t in tables 
                    if abs(t.column_count - first_cols) <= 1
                ]
                
                if len(similar_tables) >= 2:
                    # Likely repeating employee blocks
                    for table in similar_tables:
                        employee_blocks.append({
                            'page': page.page_num,
                            'bbox': table.bbox,
                            'type': 'table_block'
                        })
        
        layout.employee_blocks = employee_blocks


# Singleton
_layout_detector_instance = None

def get_layout_detector() -> LayoutDetector:
    """Get or create layout detector singleton"""
    global _layout_detector_instance
    if _layout_detector_instance is None:
        _layout_detector_instance = LayoutDetector()
    return _layout_detector_instance
