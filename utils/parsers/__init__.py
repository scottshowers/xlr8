"""
Parsers package for XLR8
Intelligent PDF parsing with multi-stage fallback
"""

# Make modules available at package level
from .dayforce_parser_enhanced import DayforceParserEnhanced, parse_dayforce_register
from .intelligent_parser_orchestrator import IntelligentParserOrchestrator, parse_pdf_intelligent
from .intelligent_parser_ui import IntelligentParserUI, render_intelligent_parser_ui
from .pdf_structure_analyzer import PDFStructureAnalyzer
from .parser_code_generator import ParserCodeGenerator

__all__ = [
    'DayforceParserEnhanced',
    'parse_dayforce_register',
    'IntelligentParserOrchestrator',
    'parse_pdf_intelligent',
    'IntelligentParserUI',
    'render_intelligent_parser_ui',
    'PDFStructureAnalyzer',
    'ParserCodeGenerator'
]
