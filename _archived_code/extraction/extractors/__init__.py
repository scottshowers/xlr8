"""
Extractors Package
===================
Individual extraction implementations.
Each extractor can work independently or be combined by the orchestrator.
"""

# Import extractors if available
try:
    from .pdfplumber_extractor import PDFPlumberExtractor
except ImportError:
    PDFPlumberExtractor = None

# Future extractors
CamelotExtractor = None
PyMuPDFExtractor = None

__all__ = [
    'PDFPlumberExtractor',
    'CamelotExtractor',
    'PyMuPDFExtractor',
]
