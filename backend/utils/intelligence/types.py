"""
XLR8 Intelligence Engine - Shared Types
========================================

Data classes and enums used across the intelligence module.

Deploy to: backend/utils/intelligence/types.py
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any


# =============================================================================
# CORE DATA CLASSES
# =============================================================================

@dataclass
class Truth:
    """
    A piece of information from one source of truth.
    
    The Five Truths:
    - reality: What actually exists in the data (DuckDB)
    - intent: What the customer says they want (ChromaDB - SOWs, requirements)
    - configuration: How the system is configured (DuckDB - code tables)
    - reference: Vendor documentation and best practices (ChromaDB)
    - regulatory: Laws, IRS rules, compliance requirements (ChromaDB)
    """
    source_type: str  # One of: reality, intent, configuration, reference, regulatory, compliance
    source_name: str  # Table name, document name, etc.
    content: Any      # The actual data (rows, text, etc.)
    confidence: float # 0.0 - 1.0
    location: str     # Where this came from (table, page, section)
    metadata: Dict = field(default_factory=dict)  # Additional context (query, row_count, etc.)


@dataclass  
class Conflict:
    """
    A detected conflict between sources of truth.
    
    Example: Customer intent says "weekly payroll" but configuration shows bi-weekly.
    """
    description: str
    reality: Optional[Truth] = None
    intent: Optional[Truth] = None
    configuration: Optional[Truth] = None
    reference: Optional[Truth] = None
    regulatory: Optional[Truth] = None
    compliance: Optional[Truth] = None
    severity: str = "medium"  # high, medium, low
    recommendation: str = ""


@dataclass
class Insight:
    """
    A proactive insight discovered while processing.
    
    These are findings that emerge from analysis, not directly asked for.
    """
    type: str           # pattern, anomaly, warning, opportunity
    title: str          # Short description
    description: str    # Detailed explanation
    data: Any          # Supporting data
    severity: str       # critical, high, medium, low, info
    action_required: bool = False


@dataclass
class ComplianceRule:
    """
    A structured rule extracted from regulatory/compliance documents.
    
    Used for automated compliance checking against Reality and Configuration.
    """
    rule_id: str
    source_doc: str
    source_page: str
    condition: str              # Human readable condition
    condition_sql: Optional[str] # SQL-translatable condition if possible
    requirement: str            # What must be true
    effective_date: Optional[str]
    severity: str = "high"      # high, medium, low
    category: str = "regulatory"  # regulatory, compliance, reference


@dataclass
class SynthesizedAnswer:
    """
    A complete answer synthesized from all sources of truth.
    
    This is what the Intelligence Engine returns to callers.
    Every field supports provenance - you can trace back where info came from.
    """
    question: str
    answer: str
    confidence: float
    
    # Customer truths (project-scoped)
    from_reality: List[Truth] = field(default_factory=list)
    from_intent: List[Truth] = field(default_factory=list)
    from_configuration: List[Truth] = field(default_factory=list)
    
    # Global truths (Reference Library)
    from_reference: List[Truth] = field(default_factory=list)
    from_regulatory: List[Truth] = field(default_factory=list)
    from_compliance: List[Truth] = field(default_factory=list)
    
    # Analysis results
    conflicts: List[Conflict] = field(default_factory=list)
    insights: List[Insight] = field(default_factory=list)
    compliance_check: Optional[Dict] = None  # Results of auto-compliance checking
    
    # For structured responses (tables, charts, etc.)
    structured_output: Optional[Dict] = None
    
    # Reasoning chain (for debugging/transparency)
    reasoning: List[str] = field(default_factory=list)
    
    # The SQL that was executed (if any)
    executed_sql: Optional[str] = None


# =============================================================================
# ENUMS
# =============================================================================

class IntelligenceMode(Enum):
    """
    Operating modes for the Intelligence Engine.
    
    Detected from the question to optimize processing.
    """
    SEARCH = "search"       # Simple data lookup
    ANALYZE = "analyze"     # Deep analysis with multiple truths
    COMPARE = "compare"     # Compare across sources or time
    VALIDATE = "validate"   # Configuration validation
    CONFIGURE = "configure" # How-to questions
    INTERVIEW = "interview" # Guided discovery
    WORKFLOW = "workflow"   # Multi-step process
    POPULATE = "populate"   # Fill in forms/templates
    REPORT = "report"       # Generate formatted output


class TruthType(Enum):
    """The Five Truths + Compliance."""
    REALITY = "reality"
    INTENT = "intent"
    CONFIGURATION = "configuration"
    REFERENCE = "reference"
    REGULATORY = "regulatory"
    COMPLIANCE = "compliance"


class StorageType(Enum):
    """Where each truth type is stored."""
    DUCKDB = "duckdb"
    CHROMADB = "chromadb"


# =============================================================================
# TRUTH TYPE ROUTING
# =============================================================================

TRUTH_ROUTING: Dict[str, StorageType] = {
    # Customer-scoped (project data)
    TruthType.REALITY.value: StorageType.DUCKDB,
    TruthType.INTENT.value: StorageType.CHROMADB,
    TruthType.CONFIGURATION.value: StorageType.DUCKDB,
    
    # Global-scoped (reference library)
    TruthType.REFERENCE.value: StorageType.CHROMADB,
    TruthType.REGULATORY.value: StorageType.CHROMADB,
    TruthType.COMPLIANCE.value: StorageType.CHROMADB,
}


# =============================================================================
# SEMANTIC PATTERNS (for column matching)
# =============================================================================

SEMANTIC_TYPES = {
    'employee_id': [
        r'^emp.*id', r'^ee.*num', r'^employee.*number', r'^worker.*id',
        r'^person.*id', r'^emp.*num', r'^emp.*no$', r'^ee.*id',
        r'^employee.*id', r'^staff.*id', r'^associate.*id', r'^emp.*key',
    ],
    'company_code': [
        r'^comp.*code', r'^co.*code', r'^company.*id', r'^org.*code',
        r'^entity.*code', r'^legal.*entity', r'^business.*unit',
        r'^company$', r'^comp$',
    ],
}


# =============================================================================
# LOOKUP INDICATORS (tables to deprioritize)
# =============================================================================

LOOKUP_INDICATORS = [
    '_lookup', '_ref', '_xref', '_map', '_mapping',
    'lookup_', 'ref_', 'xref_', 'map_',
    '_code_', '_codes', 'code_table',
]
