"""
Extraction Package
===================
Multi-layer document extraction system with 98% confidence target.

Components:
- orchestrator: Main coordinator for all extraction methods
- layout_detector: Analyzes document structure
- template_manager: Saves and matches vendor templates
- cloud_analyzer: AWS Textract integration
- pii_redactor: Protects PII before cloud calls
- validation_engine: Cross-checks extraction results
- extractors/: Individual extraction implementations
"""

from .orchestrator import (
    ExtractionOrchestrator,
    get_extraction_orchestrator,
    ExtractionStatus,
    SectionType,
    LayoutType,
    DocumentResult,
    SectionResult,
    CONFIDENCE_THRESHOLD
)

from .validation_engine import (
    ValidationEngine,
    ValidationResult
)

__all__ = [
    'ExtractionOrchestrator',
    'get_extraction_orchestrator',
    'ExtractionStatus',
    'SectionType', 
    'LayoutType',
    'DocumentResult',
    'SectionResult',
    'CONFIDENCE_THRESHOLD',
    'ValidationEngine',
    'ValidationResult',
]
