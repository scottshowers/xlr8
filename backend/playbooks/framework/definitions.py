"""
PLAYBOOK FRAMEWORK - Core Definitions
======================================

Defines the core data structures for the playbook framework.

Playbook Types:
- vendor: Steps defined by vendor (uploaded doc)
- xlr8: Steps defined by us (stored definition)  
- generated: Steps generated from consultant intent
- discovery: No steps - data-driven analysis
- comparison: No steps - side-by-side comparison

Author: XLR8 Team
Created: January 18, 2026
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime


# =============================================================================
# ENUMS
# =============================================================================

class PlaybookType(Enum):
    """Types of playbooks supported by the framework."""
    VENDOR = "vendor"           # Vendor-prescribed steps (Year-End)
    XLR8 = "xlr8"               # XLR8-defined best practices
    GENERATED = "generated"     # AI-generated from consultant intent
    DISCOVERY = "discovery"     # No steps - find what's wrong
    COMPARISON = "comparison"   # No steps - compare A vs B


class StepStatus(Enum):
    """Status of a playbook step."""
    NOT_STARTED = "not_started"
    BLOCKED = "blocked"         # Missing required data
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    SKIPPED = "skipped"         # N/A or expert path skip
    

class FindingStatus(Enum):
    """Status of a finding."""
    ACTIVE = "active"           # Needs attention
    ACKNOWLEDGED = "acknowledged"  # Reviewed, accepted
    SUPPRESSED = "suppressed"   # Hidden (not relevant)
    RESOLVED = "resolved"       # Fixed


class FindingSeverity(Enum):
    """Severity level of a finding."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


# =============================================================================
# CORE DATA CLASSES
# =============================================================================

@dataclass
class EngineConfig:
    """Configuration for an engine operation."""
    engine: str  # aggregate, compare, validate, detect, map
    config: Dict[str, Any]
    description: Optional[str] = None


@dataclass
class StepDefinition:
    """Definition of a playbook step."""
    id: str
    name: str
    description: Optional[str] = None
    required_data: List[str] = field(default_factory=list)  # File patterns or API endpoints
    analysis: List[EngineConfig] = field(default_factory=list)  # Engine configs to run
    guidance: Optional[str] = None  # Consultant guidance text
    expert_path_skip: bool = False  # Can be skipped in expert path
    sequence: int = 0  # Order in playbook
    phase: Optional[str] = None  # e.g., "before_final_payroll"


@dataclass
class PlaybookDefinition:
    """Definition of a playbook (template)."""
    id: str
    name: str
    type: PlaybookType
    description: Optional[str] = None
    version: str = "1.0.0"
    
    # Source info
    source_table: Optional[str] = None  # For vendor type - DuckDB table
    source_file: Optional[str] = None   # Original file name
    
    # Steps (empty for discovery/comparison types)
    steps: List[StepDefinition] = field(default_factory=list)
    
    # Expert path (alternate sequence)
    expert_path: Optional[List[str]] = None  # List of step IDs in expert order
    
    # Export configuration
    export_config: Optional[Dict[str, Any]] = None
    
    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass  
class Finding:
    """A finding from analysis."""
    id: str
    step_id: str
    engine: str
    severity: FindingSeverity
    message: str
    details: Optional[Dict[str, Any]] = None
    
    # Provenance - MANDATORY
    source_table: Optional[str] = None
    source_columns: Optional[List[str]] = None
    source_rows: Optional[List[int]] = None
    sql_query: Optional[str] = None
    
    # Status
    status: FindingStatus = FindingStatus.ACTIVE
    review_note: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None


@dataclass
class StepProgress:
    """Progress state for a single step."""
    step_id: str
    status: StepStatus = StepStatus.NOT_STARTED
    
    # Data matching
    matched_files: List[str] = field(default_factory=list)
    missing_data: List[str] = field(default_factory=list)
    
    # Analysis results
    findings: List[Finding] = field(default_factory=list)
    finding_counts: Dict[str, int] = field(default_factory=dict)  # By severity
    
    # Consultant input
    notes: Optional[str] = None
    ai_context: Optional[str] = None  # Extra context for re-analysis
    
    # Timestamps
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class PlaybookInstance:
    """A running instance of a playbook against a project."""
    id: str
    playbook_id: str
    project_id: str
    
    # Progress per step
    progress: Dict[str, StepProgress] = field(default_factory=dict)
    
    # Overall status
    total_steps: int = 0
    completed_steps: int = 0
    blocked_steps: int = 0
    
    # Path tracking
    using_expert_path: bool = False
    vendor_path_mapping: Optional[Dict[str, str]] = None  # Maps expert steps to vendor steps
    
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_step_progress(step: StepDefinition) -> StepProgress:
    """Create initial progress state for a step."""
    return StepProgress(
        step_id=step.id,
        status=StepStatus.NOT_STARTED,
        missing_data=step.required_data.copy()  # All data starts as missing
    )


def create_playbook_instance(
    playbook: PlaybookDefinition, 
    project_id: str,
    instance_id: Optional[str] = None
) -> PlaybookInstance:
    """Create a new playbook instance for a project."""
    import uuid
    
    instance = PlaybookInstance(
        id=instance_id or str(uuid.uuid4()),
        playbook_id=playbook.id,
        project_id=project_id,
        total_steps=len(playbook.steps),
        created_at=datetime.now()
    )
    
    # Initialize progress for each step
    for step in playbook.steps:
        instance.progress[step.id] = create_step_progress(step)
    
    return instance
