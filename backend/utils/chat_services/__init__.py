"""
Chat Services - Modular components for unified chat
====================================================

Extracted from unified_chat.py monolith for maintainability.

Services:
- ReversibleRedactor: PII redaction before LLM calls
- DataModelService: Code-to-description lookups
- DataQualityService: Proactive data quality alerts
- FollowUpGenerator: Suggested follow-up questions
- CitationBuilder: Audit trail and source attribution
"""

from .pii_redactor import ReversibleRedactor
from .data_model_service import DataModelService
from .data_quality_service import DataQualityService
from .follow_up_generator import FollowUpGenerator
from .citation_builder import CitationBuilder

__all__ = [
    'ReversibleRedactor',
    'DataModelService', 
    'DataQualityService',
    'FollowUpGenerator',
    'CitationBuilder'
]
