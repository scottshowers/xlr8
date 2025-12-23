"""
Text Extraction Utility
=======================

Simple utility to extract text from various file types.
Used by smart_router for content-based routing decisions.

Deploy to: utils/text_extraction.py
"""

import logging
import os

logger = logging.getLogger(__name__)

# Try pdfplumber first (better quality), fall back to PyPDF2
try:
    import pdfplumber
    PDF_LIBRARY = 'pdfplumber'
except ImportError:
    pdfplumber = None
    try:
        import PyPDF2
        PDF_LIBRARY = 'PyPDF2'
    except ImportError:
        PyPDF2 = None
        PDF_LIBRARY = None
        logger.warning("[TEXT_EXTRACTION] No PDF library available")

# Try python-docx for Word documents
try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    docx = None
    DOCX_AVAILABLE = False


def extract_text(file_path: str, max_pages: int = 10) -> str:
    """
    Extract text from a file.
    
    Args:
        file_path: Path to the file
        max_pages: Maximum pages to extract from PDFs (default 10)
        
    Returns:
        Extracted text content, or empty string on failure
    """
    if not os.path.exists(file_path):
        logger.warning(f"[TEXT_EXTRACTION] File not found: {file_path}")
        return ""
    
    extension = file_path.rsplit('.', 1)[-1].lower() if '.' in file_path else ''
    
    try:
        if extension == 'pdf':
            return _extract_pdf(file_path, max_pages)
        elif extension in ('docx', 'doc'):
            return _extract_docx(file_path)
        elif extension == 'txt':
            return _extract_txt(file_path)
        else:
            logger.debug(f"[TEXT_EXTRACTION] Unsupported extension: {extension}")
            return ""
    except Exception as e:
        logger.warning(f"[TEXT_EXTRACTION] Error extracting from {file_path}: {e}")
        return ""


def _extract_pdf(file_path: str, max_pages: int = 10) -> str:
    """Extract text from PDF using pdfplumber or PyPDF2."""
    
    if PDF_LIBRARY == 'pdfplumber':
        try:
            text_parts = []
            with pdfplumber.open(file_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    if i >= max_pages:
                        break
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            return '\n'.join(text_parts)
        except Exception as e:
            logger.warning(f"[TEXT_EXTRACTION] pdfplumber failed: {e}")
            # Fall through to PyPDF2 if available
            if PyPDF2:
                return _extract_pdf_pypdf2(file_path, max_pages)
            return ""
    
    elif PDF_LIBRARY == 'PyPDF2':
        return _extract_pdf_pypdf2(file_path, max_pages)
    
    else:
        logger.warning("[TEXT_EXTRACTION] No PDF library available")
        return ""


def _extract_pdf_pypdf2(file_path: str, max_pages: int = 10) -> str:
    """Extract text from PDF using PyPDF2."""
    try:
        text_parts = []
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for i, page in enumerate(reader.pages):
                if i >= max_pages:
                    break
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return '\n'.join(text_parts)
    except Exception as e:
        logger.warning(f"[TEXT_EXTRACTION] PyPDF2 failed: {e}")
        return ""


def _extract_docx(file_path: str) -> str:
    """Extract text from Word document."""
    if not DOCX_AVAILABLE:
        logger.warning("[TEXT_EXTRACTION] python-docx not available")
        return ""
    
    try:
        doc = docx.Document(file_path)
        text_parts = [para.text for para in doc.paragraphs if para.text]
        return '\n'.join(text_parts)
    except Exception as e:
        logger.warning(f"[TEXT_EXTRACTION] docx extraction failed: {e}")
        return ""


def _extract_txt(file_path: str) -> str:
    """Extract text from plain text file."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        logger.warning(f"[TEXT_EXTRACTION] txt extraction failed: {e}")
        return ""


# Quick availability check
def is_available() -> dict:
    """Return availability status of extraction capabilities."""
    return {
        "pdf": PDF_LIBRARY is not None,
        "pdf_library": PDF_LIBRARY,
        "docx": DOCX_AVAILABLE,
        "txt": True
    }
