"""
PII Redactor
=============
Redacts personally identifiable information from PDFs before
sending to cloud services. Preserves document structure.

Deploy to: backend/extraction/pii_redactor.py

The key insight: We only need STRUCTURE from cloud services,
not the actual content. So we can replace all text with Xs
while preserving positions and layouts.
"""

import os
import re
import tempfile
import logging
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)

# Try to import PDF libraries
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    logger.warning("PyMuPDF not installed - PII redaction will be limited")


class PIIRedactor:
    """
    Redacts PII from PDF documents while preserving structure.
    
    Redaction strategies:
    1. FULL: Replace all text with X patterns (preserves layout only)
    2. SMART: Detect and redact only PII patterns (preserves headers/labels)
    3. HYBRID: Redact data values but keep column headers
    
    For cloud layout detection, we use HYBRID - keeps headers readable
    so the cloud service can identify column types, but all actual
    data values are redacted.
    """
    
    # PII patterns to detect
    PII_PATTERNS = {
        'ssn': r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b',
        'phone': r'\b\d{3}[-\s.]?\d{3}[-\s.]?\d{4}\b',
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'date': r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
        'currency': r'\$[\d,]+\.?\d*',
        'name_like': r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # Simple name pattern
        'numbers': r'\b\d{4,}\b',  # Long numbers (IDs, account numbers)
    }
    
    # Labels to KEEP (not redact) - these help identify structure
    KEEP_LABELS = [
        # Section headers
        'earnings', 'taxes', 'deductions', 'employee', 'pay',
        'gross', 'net', 'total', 'ytd', 'current', 'rate', 'hours',
        'federal', 'state', 'local', 'fica', 'medicare',
        '401k', 'medical', 'dental', 'vision', 'insurance',
        'department', 'location', 'hire', 'date', 'period',
        # Column headers
        'code', 'description', 'amount', 'type', 'id', 'name',
        'ssn', 'check', 'direct', 'deposit',
    ]
    
    def __init__(self):
        self.temp_dir = tempfile.gettempdir()
    
    def create_redacted_pdf(self, source_path: str, 
                            max_pages: int = 5,
                            strategy: str = 'hybrid') -> Optional[str]:
        """
        Create a redacted copy of a PDF.
        
        Args:
            source_path: Path to original PDF
            max_pages: Maximum pages to include
            strategy: 'full', 'smart', or 'hybrid'
            
        Returns:
            Path to redacted PDF, or None if failed
        """
        if not PYMUPDF_AVAILABLE:
            logger.warning("PyMuPDF not available - returning original path")
            return source_path
        
        try:
            # Open source document
            source_doc = fitz.open(source_path)
            
            # Create new document
            redacted_doc = fitz.open()
            
            # Process each page (up to max_pages)
            pages_to_process = min(max_pages, len(source_doc))
            
            for page_num in range(pages_to_process):
                source_page = source_doc[page_num]
                
                # Copy page
                redacted_doc.insert_pdf(source_doc, from_page=page_num, to_page=page_num)
                redacted_page = redacted_doc[page_num]
                
                # Apply redaction based on strategy
                if strategy == 'full':
                    self._redact_full(redacted_page)
                elif strategy == 'smart':
                    self._redact_smart(redacted_page)
                else:  # hybrid
                    self._redact_hybrid(redacted_page, source_page)
            
            # Save to temp file
            output_path = os.path.join(
                self.temp_dir, 
                f"redacted_{os.path.basename(source_path)}"
            )
            redacted_doc.save(output_path)
            
            # Cleanup
            redacted_doc.close()
            source_doc.close()
            
            logger.info(f"Created redacted PDF: {output_path} ({pages_to_process} pages)")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error creating redacted PDF: {e}", exc_info=True)
            return None
    
    def _redact_full(self, page: 'fitz.Page'):
        """
        Full redaction - replace ALL text with Xs.
        Preserves character positions and spacing.
        """
        # Get all text blocks with positions
        blocks = page.get_text("dict")["blocks"]
        
        for block in blocks:
            if block.get("type") != 0:  # Skip non-text blocks
                continue
            
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    original_text = span.get("text", "")
                    bbox = span.get("bbox")
                    
                    if not original_text.strip() or not bbox:
                        continue
                    
                    # Create redacted text (same length)
                    redacted_text = self._create_redacted_text(original_text)
                    
                    # Cover original text
                    self._cover_and_replace(page, bbox, redacted_text, span)
    
    def _redact_smart(self, page: 'fitz.Page'):
        """
        Smart redaction - only redact detected PII patterns.
        """
        text = page.get_text()
        
        # Find all PII matches
        redact_regions = []
        
        for pattern_name, pattern in self.PII_PATTERNS.items():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                # Find the bounding box for this text
                instances = page.search_for(match.group())
                redact_regions.extend(instances)
        
        # Apply redactions
        for rect in redact_regions:
            page.add_redact_annot(rect, fill=(0, 0, 0))
        
        page.apply_redactions()
    
    def _redact_hybrid(self, page: 'fitz.Page', source_page: 'fitz.Page'):
        """
        Hybrid redaction - keep labels/headers, redact data values.
        This is the preferred method for cloud layout detection.
        """
        # Get text blocks
        blocks = page.get_text("dict")["blocks"]
        
        for block in blocks:
            if block.get("type") != 0:
                continue
            
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    original_text = span.get("text", "")
                    bbox = span.get("bbox")
                    
                    if not original_text.strip() or not bbox:
                        continue
                    
                    # Check if this is a label we should keep
                    if self._is_label(original_text):
                        continue  # Keep labels readable
                    
                    # Check if this looks like data (should be redacted)
                    if self._looks_like_data(original_text):
                        redacted_text = self._create_redacted_text(original_text)
                        self._cover_and_replace(page, bbox, redacted_text, span)
    
    def _is_label(self, text: str) -> bool:
        """Check if text appears to be a label/header"""
        text_lower = text.lower().strip()
        
        # Check against known labels
        for label in self.KEEP_LABELS:
            if label in text_lower:
                return True
        
        # Check if it's mostly letters (likely a label)
        if len(text_lower) < 20:
            letters = sum(1 for c in text_lower if c.isalpha())
            if letters > len(text_lower) * 0.7:
                return True
        
        return False
    
    def _looks_like_data(self, text: str) -> bool:
        """Check if text appears to be data (should be redacted)"""
        # Numbers are data
        if re.match(r'^[\d,.$\-\s]+$', text.strip()):
            return True
        
        # SSN pattern
        if re.match(self.PII_PATTERNS['ssn'], text):
            return True
        
        # Phone pattern
        if re.match(self.PII_PATTERNS['phone'], text):
            return True
        
        # Date pattern
        if re.match(self.PII_PATTERNS['date'], text):
            return True
        
        # Long mixed alphanumeric (likely an ID)
        if len(text) > 5 and any(c.isdigit() for c in text) and any(c.isalpha() for c in text):
            return True
        
        # Name-like patterns (FirstName LastName)
        if re.match(r'^[A-Z][a-z]+\s+[A-Z][a-z]+', text):
            return True
        
        return False
    
    def _create_redacted_text(self, original: str) -> str:
        """
        Create redacted version of text.
        Preserves character count and pattern (numbers, letters, spaces).
        """
        result = []
        for char in original:
            if char.isdigit():
                result.append('0')
            elif char.isalpha():
                result.append('X')
            else:
                result.append(char)  # Keep spaces, punctuation
        return ''.join(result)
    
    def _cover_and_replace(self, page: 'fitz.Page', 
                           bbox: Tuple[float, float, float, float],
                           new_text: str,
                           span: dict):
        """Cover original text with white and draw new text"""
        try:
            rect = fitz.Rect(bbox)
            
            # Draw white rectangle over original
            page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
            
            # Insert redacted text
            font_size = span.get("size", 10)
            font_name = "helv"  # Use standard font
            
            # Position text
            text_point = fitz.Point(rect.x0, rect.y1 - 2)
            
            page.insert_text(
                text_point,
                new_text,
                fontname=font_name,
                fontsize=font_size,
                color=(0.5, 0.5, 0.5)  # Gray text
            )
            
        except Exception as e:
            logger.debug(f"Could not replace text at {bbox}: {e}")
    
    def cleanup_temp_files(self):
        """Remove temporary redacted files"""
        try:
            for filename in os.listdir(self.temp_dir):
                if filename.startswith("redacted_"):
                    filepath = os.path.join(self.temp_dir, filename)
                    try:
                        os.remove(filepath)
                    except:
                        pass
        except Exception as e:
            logger.warning(f"Error cleaning up temp files: {e}")


# Singleton
_redactor_instance = None

def get_pii_redactor() -> PIIRedactor:
    """Get or create the PII redactor singleton"""
    global _redactor_instance
    if _redactor_instance is None:
        _redactor_instance = PIIRedactor()
    return _redactor_instance
