"""
PLAYBOOK FRAMEWORK
==================

A flexible framework for building and executing analysis playbooks.

Supports multiple playbook types:
- Vendor-prescribed (Year-End, etc.)
- XLR8-defined (best practices)
- Generated (from consultant intent)
- Discovery (data-driven)
- Comparison (side-by-side)

Services:
- QueryService: Load playbook definitions
- MatchService: Match files to requirements
- ProgressService: Track instance state
- ExecutionService: Run analysis engines

Author: XLR8 Team
Created: January 18, 2026
"""

from .definitions import (
    # Enums
    PlaybookType,
    StepStatus,
    FindingStatus,
    FindingSeverity,
    
    # Data classes
    EngineConfig,
    StepDefinition,
    PlaybookDefinition,
    Finding,
    StepProgress,
    PlaybookInstance,
    
    # Helper functions
    create_step_progress,
    create_playbook_instance,
)

from .query_service import QueryService, get_query_service
from .match_service import MatchService, get_match_service
from .progress_service import ProgressService, get_progress_service
from .execution_service import ExecutionService, get_execution_service


__all__ = [
    # Enums
    'PlaybookType',
    'StepStatus', 
    'FindingStatus',
    'FindingSeverity',
    
    # Data classes
    'EngineConfig',
    'StepDefinition',
    'PlaybookDefinition',
    'Finding',
    'StepProgress',
    'PlaybookInstance',
    
    # Helper functions
    'create_step_progress',
    'create_playbook_instance',
    
    # Services
    'QueryService',
    'MatchService', 
    'ProgressService',
    'ExecutionService',
    
    # Service getters
    'get_query_service',
    'get_match_service',
    'get_progress_service',
    'get_execution_service',
]
