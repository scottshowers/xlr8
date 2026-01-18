"""
XLR8 Playbooks Package
======================

Contains playbook definitions and the playbook framework.

- year_end_playbook.py: Year-End playbook configuration (legacy)
- framework/: New unified playbook framework
"""

# Re-export framework for convenience
from .framework import (
    PlaybookType,
    StepStatus,
    FindingStatus,
    FindingSeverity,
    PlaybookDefinition,
    StepDefinition,
    Finding,
    get_query_service,
    get_match_service,
    get_progress_service,
    get_execution_service,
)

__all__ = [
    'PlaybookType',
    'StepStatus',
    'FindingStatus',
    'FindingSeverity',
    'PlaybookDefinition',
    'StepDefinition',
    'Finding',
    'get_query_service',
    'get_match_service',
    'get_progress_service',
    'get_execution_service',
]
