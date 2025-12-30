"""
XLR8 Intelligence Engine - Truth Gatherers
===========================================

One gatherer per Truth type. Each knows how to query its storage
and return properly formatted Truth objects with provenance.

Deploy to: backend/utils/intelligence/gatherers/__init__.py
"""

from .base import BaseGatherer, DuckDBGatherer, ChromaDBGatherer
from .reality import RealityGatherer

# TODO: Add these as refactor continues
# from .intent import IntentGatherer
# from .configuration import ConfigurationGatherer
# from .reference import ReferenceGatherer
# from .regulatory import RegulatoryGatherer

__all__ = [
    'BaseGatherer',
    'DuckDBGatherer',
    'ChromaDBGatherer',
    'RealityGatherer',
]
