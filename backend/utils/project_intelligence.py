"""
PROJECT INTELLIGENCE SERVICE
=============================
The Universal Analysis Engine - The Brain of XLR8

v4.7: Organizational metrics now use Context Graph for dimensional breakdowns.
      Merges dimensions across all employee tables (company, country, org_levels, location).

This is NOT a UKG tool. This is NOT an HCM tool.
This is a UNIVERSAL ANALYSIS ENGINE that works on ANY data.

Upload data → Complete intelligence in seconds.
Upload standards → Automatic compliance checking.
Get tasks → Not reports. TASKS with shortcuts.

ARCHITECTURE:
─────────────
┌─────────────────────────────────────────────────────────────────┐
│                   UNIVERSAL ANALYSIS ENGINE                      │
│                                                                  │
│  TIER 1 (instant)     TIER 2 (fast)       TIER 3 (background)   │
│  ─────────────────    ─────────────────   ─────────────────────  │
│  • Structure          • Relationships     • Deep patterns        │
│  • Row counts         • Duplicates        • Correlations         │
│  • Distinct values    • Code detection    • Anomaly detection    │
│  • Basic quality      • Cross-table       • Predictive           │
│  ~5 seconds           ~30 seconds         ~2-3 minutes           │
│                                                                  │
└────────────────────────────────────────────────────────────────┘
                             │
                             ▼
                    RAW INTELLIGENCE
                    (domain-agnostic)
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      STANDARDS LAYER                             │
│                                                                  │
│   Upload your rules. LLM reads them. Compliance checked.         │
│   (NOT learned over time - seeded from YOUR documents)           │
│                                                                  │
└────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                         OUTPUTS                                  │
│                                                                  │
│  ┌─────────┐  ┌─────────────┐  ┌──────────┐  ┌───────────────┐ │
│  │  TASKS  │  │DEFENSIBILITY│  │WORK TRAIL│  │COLLISION WARN │ │
│  │         │  │             │  │          │  │               │ │
│  │"Do this"│  │"Prove it"   │  │"What was │  │"This will     │ │
│  │[SHORTCUT]│ │[EVIDENCE]   │  │ done"    │  │ break that"   │ │
│  └─────────┘  └─────────────┘  └──────────┘  └───────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

CONSUMED BY:
────────────
• Chat - answers questions using intelligence
• Playbooks - runs checks against standards
• Vacuum - extracts with quality awareness
• Reports - surfaces findings
• Future features - get intelligence for free

TABLE METADATA (v2.0):
─────────────────────
Classifications are stored in `_table_classifications` table:
- table_type: MASTER, TRANSACTION, REFERENCE, CONFIG, STAGING, UNKNOWN
- domain: earnings, deductions, taxes, time, demographics, locations, benefits, gl, general
- Queryable and usable by intelligence engine and table selector

Author: XLR8 Team
Version: 2.0.0 - Table Metadata Foundation
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from datetime import datetime
import logging
import json
import hashlib
import time
import re

logger = logging.getLogger(__name__)

# Try to import gap detection engine
try:
    from backend.utils.gap_detection_engine import GapDetectionEngine
    GAP_DETECTION_AVAILABLE = True
except ImportError:
    try:
        from utils.gap_detection_engine import GapDetectionEngine
        GAP_DETECTION_AVAILABLE = True
    except ImportError:
        GAP_DETECTION_AVAILABLE = False
        GapDetectionEngine = None
        logger.info("[INTELLIGENCE] Gap Detection Engine not available")

# Try to import domain decoder for enriching findings with consultant knowledge
try:
    from backend.utils.domain_decoder import get_decoder, decode
    DOMAIN_DECODER_AVAILABLE = True
except ImportError:
    try:
        from utils.domain_decoder import get_decoder, decode
        DOMAIN_DECODER_AVAILABLE = True
    except ImportError:
        DOMAIN_DECODER_AVAILABLE = False
        get_decoder = None
        decode = None
        logger.info("[INTELLIGENCE] Domain Decoder not available")

# Try to import relationship detector for table relationship analysis
try:
    from backend.utils.relationship_detector import analyze_project_relationships
    RELATIONSHIP_DETECTOR_AVAILABLE = True
except ImportError:
    try:
        from utils.relationship_detector import analyze_project_relationships
        RELATIONSHIP_DETECTOR_AVAILABLE = True
    except ImportError:
        RELATIONSHIP_DETECTOR_AVAILABLE = False
        analyze_project_relationships = None
        logger.info("[INTELLIGENCE] Relationship Detector not available")


# =============================================================================
# ENUMS AND CONSTANTS
# =============================================================================

class AnalysisTier(Enum):
    """Analysis tiers - determines when analysis runs."""
    TIER_1 = "instant"      # ~5 seconds - runs on upload
    TIER_2 = "fast"         # ~30 seconds - runs on upload  
    TIER_3 = "background"   # ~2-3 minutes - runs async


class TableType(Enum):
    """
    Classification of table types.
    
    v2.0: Added CONFIG for configuration/validation files (earnings codes, 
    deduction plans, tax setup, etc.) - tables that define how the system 
    should be configured vs actual transactional data.
    """
    MASTER = "master"           # One row per entity (employees, locations)
    TRANSACTION = "transaction" # Many rows per entity (earnings, time)
    REFERENCE = "reference"     # Lookup/code tables (small, few columns)
    CONFIG = "config"           # Configuration validation files (earnings codes, deduction plans)
    STAGING = "staging"         # Temporary/intermediate
    UNKNOWN = "unknown"


class TableDomain(Enum):
    """
    Domain classification for tables.
    
    This replaces hardcoded domain boosts in table_selector.
    Tables are classified into domains on upload, then the selector
    uses this metadata instead of pattern matching.
    """
    EARNINGS = "earnings"           # Earnings codes, pay rates, compensation
    DEDUCTIONS = "deductions"       # Deduction plans, benefits, 401k
    TAXES = "taxes"                 # Tax tables, SUI/SUTA/FUTA, withholding
    TIME = "time"                   # Time and attendance, hours, schedules
    DEMOGRAPHICS = "demographics"   # Employee master data, personal info
    LOCATIONS = "locations"         # Location/site/address data
    BENEFITS = "benefits"           # Benefit plans, enrollments
    GL = "gl"                       # General ledger, account mappings
    JOBS = "jobs"                   # Job codes, positions, titles
    WORKERS_COMP = "workers_comp"   # Workers compensation
    GENERAL = "general"             # Uncategorized


class ColumnSemantic(Enum):
    """Semantic meaning of columns."""
    IDENTIFIER = "identifier"       # Primary key, employee_id, SSN
    FOREIGN_KEY = "foreign_key"     # References another table
    NAME = "name"                   # Person/entity name
    DATE = "date"                   # Any date field
    MONEY = "money"                 # Currency values
    CODE = "code"                   # Coded value (status, type)
    DESCRIPTION = "description"     # Human-readable text
    MEASURE = "measure"             # Numeric measure
    FLAG = "flag"                   # Boolean/yes-no
    UNKNOWN = "unknown"


class FindingSeverity(Enum):
    """Severity of findings."""
    CRITICAL = "critical"   # Must fix - will cause failure
    WARNING = "warning"     # Should fix - may cause issues
    INFO = "info"           # Nice to know
    

class TaskStatus(Enum):
    """Status of tasks."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETE = "complete"
    SKIPPED = "skipped"


# =============================================================================
# DOMAIN DETECTION PATTERNS
# =============================================================================

# Table name patterns → domain classification
DOMAIN_PATTERNS = {
    TableDomain.EARNINGS: [
        r'.*earning.*', r'.*pay_code.*', r'.*paycode.*', r'.*compensation.*',
        r'.*salary.*', r'.*wage.*', r'.*pay_rate.*'
    ],
    TableDomain.DEDUCTIONS: [
        r'.*deduction.*', r'.*benefit_plan.*', r'.*401k.*', r'.*ded_.*',
        r'.*insurance.*', r'.*health.*'
    ],
    TableDomain.TAXES: [
        r'.*tax.*', r'.*sui.*', r'.*suta.*', r'.*futa.*', r'.*withhold.*',
        r'.*fica.*', r'.*w2.*', r'.*jurisdiction.*'
    ],
    TableDomain.TIME: [
        r'.*time.*', r'.*hours.*', r'.*attendance.*', r'.*schedule.*',
        r'.*accrual.*', r'.*pto.*'
    ],
    TableDomain.DEMOGRAPHICS: [
        r'.*employee.*', r'.*personal.*', r'.*person.*', r'.*worker.*',
        r'.*associate.*', r'.*staff.*'
    ],
    TableDomain.LOCATIONS: [
        r'.*location.*', r'.*site.*', r'.*address.*', r'.*region.*',
        r'.*geography.*'
    ],
    TableDomain.BENEFITS: [
        r'.*benefit.*', r'.*enrollment.*', r'.*coverage.*', r'.*plan.*'
    ],
    TableDomain.GL: [
        r'.*general_ledger.*', r'.*gl_.*', r'.*ledger.*', r'.*account.*',
        r'.*chart_of_accounts.*'
    ],
    TableDomain.JOBS: [
        r'.*job.*', r'.*position.*', r'.*title.*', r'.*role.*'
    ],
    TableDomain.WORKERS_COMP: [
        r'.*workers_comp.*', r'.*work_comp.*', r'.*wc_.*', r'.*wcb.*'
    ],
}

# Column patterns that suggest a CONFIG table (vs TRANSACTION)
CONFIG_COLUMN_PATTERNS = [
    'code', 'description', 'name', 'type', 'category', 'status',
    'effective_date', 'end_date', 'active', 'enabled', 'setup'
]

# Column patterns that suggest a TRANSACTION table
TRANSACTION_COLUMN_PATTERNS = [
    'amount', 'hours', 'quantity', 'units', 'period', 'date',
    'check_date', 'pay_date', 'transaction_date'
]


# =============================================================================
# DATA CLASSES - Findings, Tasks, Evidence
# =============================================================================

@dataclass
class Finding:
    """
    A single finding from analysis.
    
    Not domain-specific. Just "here's what's TRUE about this data."
    """
    id: str
    category: str               # STRUCTURE, QUALITY, RELATIONSHIP, PATTERN
    finding_type: str           # duplicate_values, missing_data, orphan_records, etc.
    severity: FindingSeverity
    
    # Location
    table_name: str
    column_name: Optional[str] = None
    
    # The finding
    title: str = ""
    description: str = ""
    affected_count: int = 0
    affected_percentage: float = 0.0
    
    # Evidence (for defensibility)
    evidence_sql: str = ""
    evidence_sample: List[Dict] = field(default_factory=list)
    evidence_hash: str = ""     # Hash of source data for proof
    
    # For validators who need to drill down
    details: Dict = field(default_factory=dict)
    
    # Timestamps
    detected_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'category': self.category,
            'finding_type': self.finding_type,
            'severity': self.severity.value,
            'table_name': self.table_name,
            'column_name': self.column_name,
            'title': self.title,
            'description': self.description,
            'affected_count': self.affected_count,
            'affected_percentage': self.affected_percentage,
            'evidence_sql': self.evidence_sql,
            'evidence_sample': self.evidence_sample[:10],
            'evidence_hash': self.evidence_hash,
            'details': self.details,
            'detected_at': self.detected_at.isoformat()
        }


@dataclass
class Task:
    """
    A task to complete.
    
    Not "here's a report." It's "here's what you need to DO."
    """
    id: str
    title: str
    description: str
    
    # Link to finding(s) that created this task
    finding_ids: List[str] = field(default_factory=list)
    
    # Priority/severity
    severity: FindingSeverity = FindingSeverity.INFO
    
    # Status
    status: TaskStatus = TaskStatus.PENDING
    
    # The shortcut - how to do it fast
    shortcut_type: str = ""     # sql_fix, export, review, approve, etc.
    shortcut_data: Dict = field(default_factory=dict)  # SQL to run, records to export, etc.
    
    # Ownership
    assigned_to: Optional[str] = None
    blocked_by: Optional[str] = None  # Who/what is blocking
    
    # Time tracking
    estimated_minutes: int = 0
    actual_minutes: int = 0
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'finding_ids': self.finding_ids,
            'severity': self.severity.value,
            'status': self.status.value,
            'shortcut_type': self.shortcut_type,
            'shortcut_data': self.shortcut_data,
            'assigned_to': self.assigned_to,
            'blocked_by': self.blocked_by,
            'estimated_minutes': self.estimated_minutes,
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


@dataclass
class Evidence:
    """
    One-click defensibility - proof package for a finding.
    """
    finding_id: str
    
    # The query that proves it
    sql_query: str
    
    # The actual records
    records: List[Dict] = field(default_factory=list)
    record_count: int = 0
    
    # The standard/rule that says this is wrong (if applicable)
    standard_reference: Optional[str] = None
    standard_text: Optional[str] = None
    
    # Proof of data integrity
    source_data_hash: str = ""
    generated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            'finding_id': self.finding_id,
            'sql_query': self.sql_query,
            'records': self.records[:100],  # Limit for export
            'record_count': self.record_count,
            'standard_reference': self.standard_reference,
            'standard_text': self.standard_text,
            'source_data_hash': self.source_data_hash,
            'generated_at': self.generated_at.isoformat()
        }


@dataclass
class WorkTrailEntry:
    """
    Auto-documentation of what was done.
    """
    id: str
    timestamp: datetime
    
    # What happened
    action_type: str        # upload, analyze, resolve, approve, export, etc.
    action_description: str
    
    # Who did it
    actor: str              # User or "system"
    
    # Context
    project: str
    table_name: Optional[str] = None
    finding_id: Optional[str] = None
    task_id: Optional[str] = None
    
    # Details
    details: Dict = field(default_factory=dict)
    
    # Attachments (email, file, screenshot)
    attachments: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'action_type': self.action_type,
            'action_description': self.action_description,
            'actor': self.actor,
            'project': self.project,
            'table_name': self.table_name,
            'finding_id': self.finding_id,
            'task_id': self.task_id,
            'details': self.details,
            'attachments': self.attachments
        }


@dataclass 
class CollisionWarning:
    """
    Proactive warning about impacts of an action.
    """
    id: str
    
    # What they're trying to do
    proposed_action: str
    affected_table: str
    affected_records: int
    
    # What will break
    impacts: List[Dict] = field(default_factory=list)
    # Each impact: {table, description, record_count, severity}
    
    # Severity
    severity: FindingSeverity = FindingSeverity.WARNING
    
    # Recommendations
    recommendation: str = ""
    safe_alternative: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'proposed_action': self.proposed_action,
            'affected_table': self.affected_table,
            'affected_records': self.affected_records,
            'impacts': self.impacts,
            'severity': self.severity.value,
            'recommendation': self.recommendation,
            'safe_alternative': self.safe_alternative
        }


class MetricCategory(Enum):
    """Categories for organizational metrics."""
    WORKFORCE = "workforce"           # Headcount, FT/PT, employee types
    COMPENSATION = "compensation"     # Payroll totals, averages
    BENEFITS = "benefits"             # Participation rates, coverage
    DEMOGRAPHICS = "demographics"     # Age, tenure, gender, ethnicity
    CONFIGURATION = "configuration"   # Hub usage, coverage gaps
    DIMENSIONAL = "dimensional"       # Breakdowns by company/location/etc


@dataclass
class OrganizationalMetric:
    """
    A computed organizational metric.
    
    These are the metrics every HR/Payroll/Benefits leader wants:
    headcount, turnover, participation rates, coverage gaps, etc.
    
    Computed dynamically from Context Graph relationships and lookups.
    """
    id: str
    category: MetricCategory
    metric_name: str              # e.g., "active_headcount", "401k_participation"
    
    # The value
    value: float
    value_formatted: str          # e.g., "1,234" or "78.5%"
    
    # Context
    dimension: Optional[str] = None      # e.g., "home_company_code" for breakdowns
    dimension_value: Optional[str] = None  # e.g., "ACME Corp"
    
    # For coverage/gap metrics
    numerator: Optional[int] = None      # e.g., in_use count
    denominator: Optional[int] = None    # e.g., configured count
    
    # Source tables for transparency
    source_table: Optional[str] = None
    source_query: Optional[str] = None
    
    # Metadata
    computed_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'category': self.category.value,
            'metric_name': self.metric_name,
            'value': self.value,
            'value_formatted': self.value_formatted,
            'dimension': self.dimension,
            'dimension_value': self.dimension_value,
            'numerator': self.numerator,
            'denominator': self.denominator,
            'source_table': self.source_table,
            'source_query': self.source_query,
            'computed_at': self.computed_at.isoformat()
        }


@dataclass
class TableClassification:
    """
    Classification of a single table.
    
    v2.0: Added domain field for domain-specific scoring in table selector.
    This replaces hardcoded domain boosts with metadata-driven selection.
    """
    table_name: str
    table_type: TableType
    domain: TableDomain              # NEW: earnings, deductions, taxes, etc.
    primary_entity: str              # employee, earning, location, etc.
    confidence: float
    
    row_count: int = 0
    column_count: int = 0
    
    likely_key_columns: List[str] = field(default_factory=list)
    parent_tables: List[str] = field(default_factory=list)
    child_tables: List[str] = field(default_factory=list)
    
    # For CONFIG tables: what they configure
    config_target: Optional[str] = None  # e.g., "earnings", "deductions"
    
    def to_dict(self) -> Dict:
        return {
            'table_name': self.table_name,
            'table_type': self.table_type.value,
            'domain': self.domain.value,
            'primary_entity': self.primary_entity,
            'confidence': self.confidence,
            'row_count': self.row_count,
            'column_count': self.column_count,
            'likely_key_columns': self.likely_key_columns,
            'parent_tables': self.parent_tables,
            'child_tables': self.child_tables,
            'config_target': self.config_target
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TableClassification':
        """Create TableClassification from a dictionary."""
        return cls(
            table_name=data['table_name'],
            table_type=TableType(data.get('table_type', 'unknown')),
            domain=TableDomain(data.get('domain', 'general')),
            primary_entity=data.get('primary_entity', 'unknown'),
            confidence=data.get('confidence', 0.5),
            row_count=data.get('row_count', 0),
            column_count=data.get('column_count', 0),
            likely_key_columns=data.get('likely_key_columns', []),
            parent_tables=data.get('parent_tables', []),
            child_tables=data.get('child_tables', []),
            config_target=data.get('config_target')
        )


@dataclass
class ReferenceLookup:
    """A detected reference/lookup table with decoded values."""
    table_name: str
    code_column: str
    description_column: str
    lookup_type: str            # location, department, status, etc.
    confidence: float
    
    # The actual lookup data
    lookup_data: Dict[str, str] = field(default_factory=dict)  # code -> description
    entry_count: int = 0
    
    def to_dict(self) -> Dict:
        return {
            'table_name': self.table_name,
            'code_column': self.code_column,
            'description_column': self.description_column,
            'lookup_type': self.lookup_type,
            'confidence': self.confidence,
            'lookup_data': self.lookup_data,
            'entry_count': self.entry_count
        }
    
    def decode(self, code: str) -> str:
        """Decode a code to its description."""
        desc = self.lookup_data.get(str(code))
        if desc:
            return f"{desc} ({code})"
        return code


@dataclass
class Relationship:
    """A detected relationship between tables."""
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    
    relationship_type: str      # one-to-one, one-to-many, many-to-many
    confidence: float
    
    # Validation
    orphan_count: int = 0       # Records in from_table with no match
    orphan_percentage: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            'from_table': self.from_table,
            'from_column': self.from_column,
            'to_table': self.to_table,
            'to_column': self.to_column,
            'relationship_type': self.relationship_type,
            'confidence': self.confidence,
            'orphan_count': self.orphan_count,
            'orphan_percentage': self.orphan_percentage
        }


# =============================================================================
# MAIN SERVICE CLASS
# =============================================================================

class ProjectIntelligenceService:
    """
    THE Universal Analysis Engine.
    
    This is the shared intelligence layer that powers everything in XLR8.
    Domain-agnostic. Standards-driven. Task-focused.
    
    Usage:
        # On upload (runs analysis)
        intelligence = ProjectIntelligenceService(project, handler)
        summary = intelligence.analyze()  # Returns full analysis
        
        # In chat/playbooks/anywhere (retrieves pre-computed)
        intelligence = ProjectIntelligenceService(project, handler)
        findings = intelligence.get_findings(severity='critical')
        tasks = intelligence.get_tasks(status='pending')
        evidence = intelligence.get_evidence(finding_id)
        
        # NEW: Get table classifications for table selection
        classifications = intelligence.get_table_classifications()
        earnings_tables = intelligence.get_tables_by_domain(TableDomain.EARNINGS)
    """
    
    def __init__(self, project: str, handler=None):
        """
        Initialize the intelligence service.
        
        Args:
            project: Project identifier
            handler: DuckDB structured data handler (optional for retrieval-only)
        """
        self.project = project
        self.handler = handler
        
        # Analysis results (populated by analyze())
        self.findings: List[Finding] = []
        self.tasks: List[Task] = []
        self.tables: List[TableClassification] = []
        self.lookups: List[ReferenceLookup] = []
        self.relationships: List[Relationship] = []
        self.work_trail: List[WorkTrailEntry] = []
        self.metrics: List[OrganizationalMetric] = []  # NEW: Organizational metrics
        
        # Summary stats
        self.total_tables = 0
        self.total_rows = 0
        self.total_columns = 0
        self.analysis_time_seconds = 0
        self.analyzed_at: Optional[datetime] = None
        
        # Tier tracking
        self.tier1_complete = False
        self.tier2_complete = False
        self.tier3_complete = False
    
    # =========================================================================
    # TABLE CLASSIFICATION API (NEW in v2.0)
    # =========================================================================
    
    def get_table_classifications(self) -> List[TableClassification]:
        """
        Get all table classifications for this project.
        
        If classifications aren't loaded, attempts to load from database.
        
        Returns:
            List of TableClassification objects
        """
        if not self.tables:
            self._load_classifications()
        return self.tables
    
    def get_tables_by_domain(self, domain: TableDomain) -> List[TableClassification]:
        """
        Get tables matching a specific domain.
        
        Args:
            domain: TableDomain enum value
            
        Returns:
            List of TableClassification objects matching the domain
        """
        classifications = self.get_table_classifications()
        return [t for t in classifications if t.domain == domain]
    
    def get_tables_by_type(self, table_type: TableType) -> List[TableClassification]:
        """
        Get tables matching a specific type.
        
        Args:
            table_type: TableType enum value
            
        Returns:
            List of TableClassification objects matching the type
        """
        classifications = self.get_table_classifications()
        return [t for t in classifications if t.table_type == table_type]
    
    def get_config_tables(self) -> List[TableClassification]:
        """
        Get all CONFIG type tables (configuration validation files).
        
        Returns:
            List of CONFIG type TableClassification objects
        """
        return self.get_tables_by_type(TableType.CONFIG)
    
    def get_classification_for_table(self, table_name: str) -> Optional[TableClassification]:
        """
        Get classification for a specific table.
        
        Args:
            table_name: The table name (case-insensitive)
            
        Returns:
            TableClassification or None if not found
        """
        classifications = self.get_table_classifications()
        table_lower = table_name.lower()
        for c in classifications:
            if c.table_name.lower() == table_lower:
                return c
        return None
    
    def _load_classifications(self) -> bool:
        """
        Load table classifications from database.
        
        Returns:
            True if classifications were loaded, False otherwise
        """
        if not self.handler or not self.handler.conn:
            return False
        
        try:
            # Check if table exists
            tables = self.handler.conn.execute("SHOW TABLES").fetchall()
            table_names = [t[0] for t in tables]
            
            if '_table_classifications' not in table_names:
                logger.debug("[INTELLIGENCE] _table_classifications table doesn't exist yet")
                return False
            
            results = self.handler.conn.execute("""
                SELECT table_name, table_type, domain, primary_entity, confidence,
                       row_count, column_count, likely_key_columns_json, 
                       parent_tables_json, child_tables_json, config_target
                FROM _table_classifications
                WHERE project_name = ?
            """, [self.project]).fetchall()
            
            self.tables = []
            for row in results:
                self.tables.append(TableClassification(
                    table_name=row[0],
                    table_type=TableType(row[1]) if row[1] else TableType.UNKNOWN,
                    domain=TableDomain(row[2]) if row[2] else TableDomain.GENERAL,
                    primary_entity=row[3] or 'unknown',
                    confidence=row[4] or 0.5,
                    row_count=row[5] or 0,
                    column_count=row[6] or 0,
                    likely_key_columns=json.loads(row[7]) if row[7] else [],
                    parent_tables=json.loads(row[8]) if row[8] else [],
                    child_tables=json.loads(row[9]) if row[9] else [],
                    config_target=row[10]
                ))
            
            logger.warning(f"[INTELLIGENCE] Loaded {len(self.tables)} table classifications from DB")
            return len(self.tables) > 0
            
        except Exception as e:
            logger.warning(f"[INTELLIGENCE] Failed to load classifications: {e}")
            return False
    
    # =========================================================================
    # MAIN ANALYSIS ENTRY POINT
    # =========================================================================
    
    def analyze(self, tiers: List[AnalysisTier] = None) -> Dict:
        """
        Run analysis on the project data.
        
        Args:
            tiers: Which tiers to run. Default is TIER_1 and TIER_2.
                   TIER_3 should typically run in background.
        
        Returns:
            Complete analysis summary
        """
        if not self.handler or not self.handler.conn:
            logger.error("[INTELLIGENCE] No database handler")
            return {'error': 'No database handler'}
        
        start_time = time.time()
        self.analyzed_at = datetime.now()
        
        # Default to Tier 1 and 2
        if tiers is None:
            tiers = [AnalysisTier.TIER_1, AnalysisTier.TIER_2]
        
        logger.warning(f"[INTELLIGENCE] Starting analysis for {self.project}")
        logger.warning(f"[INTELLIGENCE] Tiers: {[t.value for t in tiers]}")
        
        try:
            # Get all tables for project
            project_tables = self._get_project_tables()
            self.total_tables = len(project_tables)
            
            if not project_tables:
                logger.warning(f"[INTELLIGENCE] No tables found for {self.project}")
                return self._build_summary()
            
            # TIER 1: Instant (~5 seconds)
            if AnalysisTier.TIER_1 in tiers:
                self._run_tier1_analysis(project_tables)
                self.tier1_complete = True
            
            # TIER 2: Fast (~30 seconds)
            if AnalysisTier.TIER_2 in tiers:
                self._run_tier2_analysis(project_tables)
                self.tier2_complete = True
            
            # TIER 3: Background (~2-3 minutes)
            if AnalysisTier.TIER_3 in tiers:
                self._run_tier3_analysis(project_tables)
                self.tier3_complete = True
            
            # Generate tasks from findings
            self._generate_tasks()
            
            # Store results
            self._persist_results()
            
            self.analysis_time_seconds = time.time() - start_time
            logger.warning(f"[INTELLIGENCE] Analysis complete in {self.analysis_time_seconds:.1f}s")
            logger.warning(f"[INTELLIGENCE] Found {len(self.findings)} findings, generated {len(self.tasks)} tasks")
            
            # Log work trail entry
            self._log_work_trail(
                action_type='analyze',
                action_description=f"Analyzed {self.total_tables} tables, found {len(self.findings)} findings",
                details={
                    'tables': self.total_tables,
                    'findings': len(self.findings),
                    'tasks': len(self.tasks),
                    'time_seconds': self.analysis_time_seconds
                }
            )
            
            return self._build_summary()
            
        except Exception as e:
            logger.error(f"[INTELLIGENCE] Analysis failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {'error': str(e)}
    
    # =========================================================================
    # TIER 1: INSTANT ANALYSIS (~5 seconds)
    # =========================================================================
    
    def _run_tier1_analysis(self, tables: List[Dict]) -> None:
        """
        Tier 1: Instant analysis - structure and basic quality.
        
        This runs synchronously on upload. Must be FAST.
        """
        logger.info("[INTELLIGENCE] Running Tier 1 analysis...")
        
        for table_info in tables:
            table_name = table_info['table_name']
            columns = table_info.get('columns', [])
            row_count = table_info.get('row_count', 0)
            
            self.total_rows += row_count
            self.total_columns += len(columns)
            
            # Classify table (enhanced with domain detection)
            classification = self._classify_table(table_name, columns, row_count)
            self.tables.append(classification)
            
            # Basic quality checks (fast)
            self._check_empty_table(table_name, row_count)
            self._check_null_columns(table_name, columns)
            self._check_basic_duplicates(table_name, columns)
    
    def _classify_table(self, table_name: str, columns: List[str], row_count: int) -> TableClassification:
        """
        Classify a table by its structure and naming.
        
        v2.0: Enhanced with domain detection and CONFIG type.
        """
        table_lower = table_name.lower()
        columns_lower = [c.lower() for c in columns]
        
        # Detect table type
        table_type = TableType.UNKNOWN
        primary_entity = "unknown"
        confidence = 0.5
        config_target = None
        
        # =====================================================================
        # DOMAIN DETECTION (NEW in v2.0)
        # =====================================================================
        domain = self._detect_domain(table_lower)
        
        # =====================================================================
        # TABLE TYPE DETECTION
        # =====================================================================
        
        # CONFIG table detection (NEW in v2.0)
        # Config tables typically have: code, description, name columns
        # and moderate row counts (not huge transaction tables)
        config_indicators = sum(1 for c in columns_lower if any(
            p in c for p in CONFIG_COLUMN_PATTERNS
        ))
        transaction_indicators = sum(1 for c in columns_lower if any(
            p in c for p in TRANSACTION_COLUMN_PATTERNS
        ))
        
        # If it looks like a config file AND has a domain AND reasonable size
        if (config_indicators >= 2 and 
            transaction_indicators < config_indicators and
            domain != TableDomain.GENERAL and
            row_count <= 5000):
            table_type = TableType.CONFIG
            config_target = domain.value
            primary_entity = domain.value
            confidence = 0.85
            logger.info(f"[INTELLIGENCE] Classified {table_name} as CONFIG ({domain.value})")
        
        # Reference table detection
        reference_patterns = [
            r'.*_codes?$', r'.*_types?$', r'.*_lookup$', r'.*_ref$',
            r'^ref_.*', r'^lkp_.*', r'^code_.*'
        ]
        if table_type == TableType.UNKNOWN:
            if any(re.match(p, table_lower) for p in reference_patterns) or row_count <= 100:
                table_type = TableType.REFERENCE
                confidence = 0.8
        
        # Master table detection
        master_patterns = ['employee', 'customer', 'vendor', 'location', 'department', 'company']
        if table_type == TableType.UNKNOWN:
            for pattern in master_patterns:
                if pattern in table_lower:
                    table_type = TableType.MASTER
                    primary_entity = pattern
                    confidence = 0.85
                    break
        
        # Transaction table detection
        transaction_patterns = ['earning', 'deduction', 'time', 'transaction', 'history', 'log', 'detail']
        if table_type == TableType.UNKNOWN:
            for pattern in transaction_patterns:
                if pattern in table_lower:
                    table_type = TableType.TRANSACTION
                    primary_entity = pattern
                    confidence = 0.8
                    break
        
        # Find likely key columns
        key_patterns = ['_id', '_key', '_code', '_number', '_no', 'ssn', 'employee_id', 'emp_id']
        likely_keys = []
        for col in columns:
            col_lower = col.lower()
            if any(p in col_lower for p in key_patterns):
                likely_keys.append(col)
        
        return TableClassification(
            table_name=table_name,
            table_type=table_type,
            domain=domain,
            primary_entity=primary_entity,
            confidence=confidence,
            row_count=row_count,
            column_count=len(columns),
            likely_key_columns=likely_keys[:5],
            config_target=config_target
        )
    
    def _detect_domain(self, table_name_lower: str) -> TableDomain:
        """
        Detect the domain of a table based on name patterns.
        
        Args:
            table_name_lower: Lowercase table name
            
        Returns:
            TableDomain enum value
        """
        for domain, patterns in DOMAIN_PATTERNS.items():
            for pattern in patterns:
                if re.match(pattern, table_name_lower):
                    return domain
        return TableDomain.GENERAL
    
    def _check_empty_table(self, table_name: str, row_count: int) -> None:
        """Check for empty tables."""
        if row_count == 0:
            self.findings.append(Finding(
                id=f"empty_{table_name}_{int(time.time())}",
                category="STRUCTURE",
                finding_type="empty_table",
                severity=FindingSeverity.WARNING,
                table_name=table_name,
                title="Empty Table",
                description=f"Table '{table_name}' contains no data",
                affected_count=0
            ))
    
    def _check_null_columns(self, table_name: str, columns: List[str]) -> None:
        """Check for columns with high null rates."""
        try:
            for col in columns[:20]:  # Limit for speed
                result = self.handler.conn.execute(f'''
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN "{col}" IS NULL OR TRIM(CAST("{col}" AS VARCHAR)) = '' THEN 1 ELSE 0 END) as nulls
                    FROM "{table_name}"
                ''').fetchone()
                
                if result and result[0] > 0:
                    total, nulls = result
                    null_pct = (nulls / total) * 100
                    
                    # Flag if >50% null
                    if null_pct > 50:
                        self.findings.append(Finding(
                            id=f"sparse_{table_name}_{col}_{int(time.time())}",
                            category="QUALITY",
                            finding_type="sparse_column",
                            severity=FindingSeverity.INFO,
                            table_name=table_name,
                            column_name=col,
                            title="Sparse Data Column",
                            description=f"Column '{col}' is {null_pct:.1f}% empty",
                            affected_count=nulls,
                            affected_percentage=null_pct,
                            evidence_sql=f'SELECT * FROM "{table_name}" WHERE "{col}" IS NULL OR TRIM(CAST("{col}" AS VARCHAR)) = \'\''
                        ))
                    
                    # Flag if 100% null
                    if null_pct == 100:
                        self.findings[-1].severity = FindingSeverity.WARNING
                        self.findings[-1].title = "Completely Empty Column"
                        
        except Exception as e:
            logger.debug(f"[INTELLIGENCE] Null check failed for {table_name}: {e}")
    
    def _check_basic_duplicates(self, table_name: str, columns: List[str]) -> None:
        """Check for duplicates in likely key columns."""
        # Find likely unique columns
        key_patterns = ['_id', 'ssn', 'employee_id', 'emp_id', 'emplid', '_key', '_number']
        
        for col in columns:
            col_lower = col.lower()
            if any(p in col_lower for p in key_patterns):
                try:
                    result = self.handler.conn.execute(f'''
                        SELECT "{col}", COUNT(*) as cnt
                        FROM "{table_name}"
                        WHERE "{col}" IS NOT NULL AND TRIM(CAST("{col}" AS VARCHAR)) != ''
                        GROUP BY "{col}"
                        HAVING COUNT(*) > 1
                        LIMIT 100
                    ''').fetchall()
                    
                    if result:
                        dup_count = len(result)
                        total_affected = sum(r[1] for r in result)
                        
                        severity = FindingSeverity.WARNING
                        if 'ssn' in col_lower or 'employee_id' in col_lower:
                            severity = FindingSeverity.CRITICAL
                        
                        self.findings.append(Finding(
                            id=f"dup_{table_name}_{col}_{int(time.time())}",
                            category="QUALITY",
                            finding_type="duplicate_values",
                            severity=severity,
                            table_name=table_name,
                            column_name=col,
                            title=f"Duplicate {col} Values",
                            description=f"{dup_count} duplicate values found in '{col}' affecting {total_affected} records",
                            affected_count=total_affected,
                            evidence_sql=f'''
                                SELECT "{col}", COUNT(*) as duplicate_count
                                FROM "{table_name}"
                                WHERE "{col}" IS NOT NULL
                                GROUP BY "{col}"
                                HAVING COUNT(*) > 1
                                ORDER BY COUNT(*) DESC
                            ''',
                            evidence_sample=[{'value': r[0], 'count': r[1]} for r in result[:10]]
                        ))
                        
                except Exception as e:
                    logger.debug(f"[INTELLIGENCE] Duplicate check failed for {table_name}.{col}: {e}")
    
    # =========================================================================
    # TIER 2: FAST ANALYSIS (~30 seconds)
    # =========================================================================
    
    def _run_tier2_analysis(self, tables: List[Dict]) -> None:
        """
        Tier 2: Fast analysis - relationships, lookups, cross-table.
        """
        logger.info("[INTELLIGENCE] Running Tier 2 analysis...")
        
        # Detect reference tables and build lookups
        self._detect_reference_tables(tables)
        
        # Also extract lookups from categorical columns in column profiles
        self._detect_profile_based_lookups(tables)
        
        # Detect relationships between tables
        self._detect_relationships(tables)
        
        # Persist relationships to Supabase
        self._persist_relationships()
        
        # Check for orphan records
        self._check_orphan_records()
        
        # Check for cross-table consistency
        self._check_cross_table_consistency(tables)
        
        # Check for date logic errors
        self._check_date_logic(tables)
        
        # Run gap detection (Configuration vs Reality)
        self._run_gap_detection(tables)
        
        # NEW: Compute organizational metrics using Context Graph
        self._compute_organizational_metrics(tables)
    
    def _detect_reference_tables(self, tables: List[Dict]) -> None:
        """
        Detect reference/lookup tables and build code→description mappings.
        
        Uses smart pattern detection:
        1. "{Entity} Code" → "{Entity}" (e.g., "Job Code" → "Job")
        2. "{Entity} Code" → "{Entity} Name" (e.g., "Company Code" → "Company Name")
        3. "* Code" → "Description" or "Name" column
        4. Traditional code/description patterns as fallback
        """
        
        for table_info in tables:
            table_name = table_info['table_name']
            columns = table_info.get('columns', [])
            columns_lower = [c.lower() for c in columns]
            row_count = table_info.get('row_count', 0)
            
            # Find best code→description pair
            code_col, desc_col = self._find_code_desc_pair(columns, columns_lower)
            
            if not code_col or not desc_col:
                logger.debug(f"[INTELLIGENCE] Skipping {table_name} - no code/desc pair found")
                continue
            
            logger.debug(f"[INTELLIGENCE] Checking {table_name} for lookup (rows={row_count}, code={code_col}, desc={desc_col})")
            
            try:
                # Load the lookup data - use DISTINCT to handle large tables efficiently
                rows = self.handler.conn.execute(f'''
                    SELECT DISTINCT "{code_col}", "{desc_col}"
                    FROM "{table_name}"
                    WHERE "{code_col}" IS NOT NULL 
                    AND TRIM(CAST("{code_col}" AS VARCHAR)) != ''
                    LIMIT 50000
                ''').fetchall()
                
                if rows:
                    lookup_data = {str(r[0]): str(r[1]) for r in rows if r[0] and r[1]}
                    
                    if lookup_data:
                        # Determine lookup type from table/column name
                        lookup_type = self._infer_lookup_type(table_name, code_col)
                        
                        self.lookups.append(ReferenceLookup(
                            table_name=table_name,
                            code_column=code_col,
                            description_column=desc_col,
                            lookup_type=lookup_type,
                            confidence=0.8,
                            lookup_data=lookup_data,
                            entry_count=len(lookup_data)
                        ))
                        logger.warning(f"[INTELLIGENCE] Found lookup: {table_name} ({len(lookup_data)} entries, type={lookup_type}, code={code_col}→{desc_col})")
                        
            except Exception as e:
                logger.debug(f"[INTELLIGENCE] Lookup detection failed for {table_name}: {e}")
        
        # Summary log
        logger.warning(f"[INTELLIGENCE] Lookup detection complete: scanned {len(tables)} tables, found {len(self.lookups)} lookups")
    
    def _find_code_desc_pair(self, columns: List[str], columns_lower: List[str]) -> tuple:
        """
        Find the best code→description column pair using smart pattern matching.
        
        Patterns detected:
        1. "{Entity} Code" → "{Entity}" (Job Code → Job)
        2. "{Entity} Code" → "{Entity} Name" (Company Code → Company Name)  
        3. "{Entity} Code" → "Description" (Any Code → Description)
        4. Traditional patterns (code/description, id/name)
        
        Returns:
            (code_column, description_column) in original case, or (None, None)
        """
        if not columns:
            return None, None
        
        # Pattern 1 & 2: Look for "{Entity} Code" → "{Entity}" or "{Entity} Name"
        for i, col in enumerate(columns):
            col_lower = columns_lower[i]
            
            # Check if column ends with " code" or "_code"
            if col_lower.endswith(' code') or col_lower.endswith('_code'):
                # Extract the entity name (e.g., "Job" from "Job Code")
                if col_lower.endswith(' code'):
                    entity = col_lower[:-5].strip()  # Remove " code"
                else:
                    entity = col_lower[:-5].strip()  # Remove "_code"
                
                if entity:
                    # Look for matching description column
                    for j, other_col in enumerate(columns):
                        if i == j:
                            continue
                        other_lower = columns_lower[j]
                        
                        # Check for exact match: "{Entity}" 
                        if other_lower == entity:
                            return col, other_col
                        
                        # Check for "{Entity} Name" or "{Entity} Description"
                        if other_lower == f"{entity} name" or other_lower == f"{entity}_name":
                            return col, other_col
                        if other_lower == f"{entity} description" or other_lower == f"{entity}_description":
                            return col, other_col
        
        # Pattern 3: Any "* Code" column → "Description" or "Name" column
        code_cols = [(i, col) for i, col in enumerate(columns) 
                     if columns_lower[i].endswith(' code') or columns_lower[i].endswith('_code') or columns_lower[i] == 'code']
        desc_cols = [(i, col) for i, col in enumerate(columns) 
                     if columns_lower[i] in ('description', 'name', 'desc', 'label', 'title')]
        
        if code_cols and desc_cols:
            # Return first code col and first description col
            return code_cols[0][1], desc_cols[0][1]
        
        # Pattern 4: Traditional patterns (less strict)
        traditional_patterns = [
            ('code', 'description'), ('code', 'name'), ('code', 'desc'),
            ('id', 'description'), ('id', 'name'), ('id', 'label'),
            ('key', 'value'), ('key', 'description'),
            ('type', 'description'), ('type', 'name'),
        ]
        
        for code_pattern, desc_pattern in traditional_patterns:
            code_match = None
            desc_match = None
            
            for i, col_lower in enumerate(columns_lower):
                if code_pattern in col_lower and not code_match:
                    code_match = columns[i]
                if desc_pattern in col_lower and not desc_match:
                    desc_match = columns[i]
            
            if code_match and desc_match and code_match != desc_match:
                return code_match, desc_match
        
        return None, None
    
    def _infer_lookup_type(self, table_name: str, code_column: str) -> str:
        """Infer the lookup type from table and column names."""
        combined = f"{table_name} {code_column}".lower()
        
        type_hints = {
            'location': 'location', 'loc_': 'location', 'site': 'location',
            'department': 'department', 'dept': 'department', 'division': 'department',
            'company': 'company', 'comp_': 'company', 'organization': 'company',
            'status': 'status', 'employment_status': 'status',
            'pay_group': 'pay_group', 'paygroup': 'pay_group', 'pay group': 'pay_group',
            'job': 'job', 'position': 'job', 'job_code': 'job', 'job code': 'job',
            'earning': 'earning', 'earnings': 'earning',
            'deduction': 'deduction', 'benefit': 'benefit',
            'tax': 'tax', 'tax_group': 'tax',
            'bank': 'bank',
            'project': 'project',
            'union': 'union',
            'worker': 'workers_comp', 'compensation': 'workers_comp',
            'salary': 'salary', 'grade': 'salary',
        }
        
        for hint, ltype in type_hints.items():
            if hint in combined:
                return ltype
        
        return "general"
    
    def _detect_profile_based_lookups(self, tables: List[Dict]) -> None:
        """
        Extract lookup-like data from categorical columns in column profiles.
        
        This catches cases where code→description mappings are embedded in
        large transactional tables rather than separate reference tables.
        """
        if not self.handler or not self.handler.conn:
            return
        
        try:
            # Check if column profiles exist
            profile_exists = self.handler.conn.execute("""
                SELECT COUNT(*) FROM _column_profiles WHERE project = ?
            """, [self.project]).fetchone()
            
            if not profile_exists or profile_exists[0] == 0:
                logger.debug("[INTELLIGENCE] No column profiles found for profile-based lookup detection")
                return
            
            # Get categorical columns with few unique values (potential lookups)
            profiles = self.handler.conn.execute("""
                SELECT table_name, column_name, distinct_count, distinct_values
                FROM _column_profiles 
                WHERE project = ?
                AND inferred_type = 'categorical'
                AND distinct_count <= 50
                AND distinct_count > 1
                AND distinct_values IS NOT NULL
            """, [self.project]).fetchall()
            
            for row in profiles:
                table_name, col_name, distinct_count, distinct_values_json = row
                
                # Check if we already have a lookup for this column type
                col_lower = col_name.lower()
                already_have = any(
                    l.code_column.lower() == col_lower or 
                    l.lookup_type.lower() in col_lower
                    for l in self.lookups
                )
                
                if already_have:
                    continue
                
                # Check if this is a code-like column
                code_indicators = ['code', 'type', 'status', 'category', 'class', 'group']
                if not any(ind in col_lower for ind in code_indicators):
                    continue
                
                try:
                    values = json.loads(distinct_values_json)
                    if not values:
                        continue
                    
                    # Build a simple lookup (code → code for now)
                    lookup_data = {}
                    for val in values[:50]:
                        if isinstance(val, dict):
                            v = str(val.get('value', ''))
                        else:
                            v = str(val)
                        if v:
                            lookup_data[v] = v  # Self-reference for now
                    
                    if lookup_data:
                        lookup_type = self._infer_lookup_type(table_name, col_name)
                        
                        self.lookups.append(ReferenceLookup(
                            table_name=table_name,
                            code_column=col_name,
                            description_column=col_name,  # Same column
                            lookup_type=lookup_type,
                            confidence=0.6,  # Lower confidence for profile-based
                            lookup_data=lookup_data,
                            entry_count=len(lookup_data)
                        ))
                        logger.info(f"[INTELLIGENCE] Profile-based lookup: {table_name}.{col_name} ({len(lookup_data)} values)")
                        
                except (json.JSONDecodeError, TypeError):
                    pass
                    
        except Exception as e:
            logger.debug(f"[INTELLIGENCE] Profile-based lookup detection failed: {e}")
    
    def _detect_relationships(self, tables: List[Dict]) -> None:
        """
        Detect relationships between tables using semantic analysis.
        
        NOTE: SKIPPED - relationship detection now handled by upload_enrichment.py
        to avoid duplicate work. The enrichment step runs after intelligence
        analysis and persists relationships to Supabase.
        
        Uses relationship_detector.py which:
        1. Detects semantic type of each key column (employee_id, company_code, etc.)
        2. Only compares columns of the SAME type
        3. Strips prefixes before comparing (home_company_code ↔ company_code)
        4. Uses global mappings for known equivalents
        """
        # SKIP - handled by upload_enrichment.py to avoid duplicate detection
        logger.info("[INTELLIGENCE] Skipping relationship detection (handled by enrichment)")
        return
    
    def _persist_relationships(self) -> None:
        """Persist detected relationships to Supabase."""
        if not self.relationships:
            return
        
        try:
            from utils.database.supabase_client import get_supabase
        except ImportError:
            try:
                from backend.utils.database.supabase_client import get_supabase
            except ImportError:
                logger.debug("[INTELLIGENCE] Supabase not available for relationship persistence")
                return
        
        try:
            supabase = get_supabase()
            
            for rel in self.relationships:
                try:
                    supabase.table('project_relationships').upsert({
                        'project_name': self.project,
                        'source_table': rel.from_table,
                        'source_column': rel.from_column,
                        'target_table': rel.to_table,
                        'target_column': rel.to_column,
                        'confidence': rel.confidence,
                        'relationship_type': rel.relationship_type,
                        'needs_review': rel.confidence < 0.8,
                        'confirmed': False,
                        'orphan_count': rel.orphan_count,
                        'orphan_percentage': rel.orphan_percentage
                    }, on_conflict='project_name,source_table,source_column,target_table,target_column').execute()
                except Exception as e:
                    logger.debug(f"[INTELLIGENCE] Failed to persist relationship: {e}")
            
            logger.info(f"[INTELLIGENCE] Persisted {len(self.relationships)} relationships to Supabase")
            
        except Exception as e:
            logger.warning(f"[INTELLIGENCE] Relationship persistence failed: {e}")
    
    def _check_orphan_records(self) -> None:
        """Check for orphan records based on detected relationships."""
        for rel in self.relationships:
            try:
                result = self.handler.conn.execute(f'''
                    SELECT COUNT(*) 
                    FROM "{rel.from_table}" f
                    LEFT JOIN "{rel.to_table}" t ON f."{rel.from_column}" = t."{rel.to_column}"
                    WHERE t."{rel.to_column}" IS NULL
                    AND f."{rel.from_column}" IS NOT NULL
                ''').fetchone()
                
                if result and result[0] > 0:
                    rel.orphan_count = result[0]
                    
                    # Get total for percentage
                    total = self.handler.conn.execute(f'''
                        SELECT COUNT(*) FROM "{rel.from_table}"
                        WHERE "{rel.from_column}" IS NOT NULL
                    ''').fetchone()
                    
                    if total and total[0] > 0:
                        rel.orphan_percentage = (rel.orphan_count / total[0]) * 100
                        
                        if rel.orphan_percentage > 5:  # More than 5% orphans
                            self.findings.append(Finding(
                                id=f"orphan_{rel.from_table}_{rel.from_column}_{int(time.time())}",
                                category="RELATIONSHIP",
                                finding_type="orphan_records",
                                severity=FindingSeverity.WARNING if rel.orphan_percentage > 10 else FindingSeverity.INFO,
                                table_name=rel.from_table,
                                column_name=rel.from_column,
                                title="Orphan Records",
                                description=f"{rel.orphan_count} records ({rel.orphan_percentage:.1f}%) have no matching record in {rel.to_table}",
                                affected_count=rel.orphan_count,
                                affected_percentage=rel.orphan_percentage
                            ))
                            
            except Exception as e:
                logger.debug(f"[INTELLIGENCE] Orphan check failed for {rel.from_table}: {e}")
    
    def _check_cross_table_consistency(self, tables: List[Dict]) -> None:
        """Check for cross-table data consistency issues."""
        # Placeholder for cross-table checks
        pass
    
    def _check_date_logic(self, tables: List[Dict]) -> None:
        """Check for date logic errors (end before start, future dates, etc.)."""
        for table_info in tables:
            table_name = table_info['table_name']
            columns = table_info.get('columns', [])
            columns_lower = [c.lower() for c in columns]
            
            # Look for date pairs
            date_patterns = [
                ('start_date', 'end_date'),
                ('hire_date', 'term_date'),
                ('effective_date', 'expiration_date'),
                ('begin_date', 'end_date'),
            ]
            
            for start_pat, end_pat in date_patterns:
                start_col = None
                end_col = None
                
                for i, col_lower in enumerate(columns_lower):
                    if start_pat in col_lower and not start_col:
                        start_col = columns[i]
                    if end_pat in col_lower and not end_col:
                        end_col = columns[i]
                
                if start_col and end_col:
                    try:
                        result = self.handler.conn.execute(f'''
                            SELECT COUNT(*)
                            FROM "{table_name}"
                            WHERE "{end_col}" IS NOT NULL
                            AND "{start_col}" IS NOT NULL
                            AND TRY_CAST("{end_col}" AS DATE) < TRY_CAST("{start_col}" AS DATE)
                        ''').fetchone()
                        
                        if result and result[0] > 0:
                            self.findings.append(Finding(
                                id=f"datelogic_{table_name}_{start_col}_{end_col}_{int(time.time())}",
                                category="QUALITY",
                                finding_type="date_logic_error",
                                severity=FindingSeverity.WARNING,
                                table_name=table_name,
                                title="Date Logic Error",
                                description=f"{result[0]} records have {end_col} before {start_col}",
                                affected_count=result[0],
                                evidence_sql=f'''
                                    SELECT * FROM "{table_name}"
                                    WHERE TRY_CAST("{end_col}" AS DATE) < TRY_CAST("{start_col}" AS DATE)
                                '''
                            ))
                    except Exception as e:
                        logger.debug(f"[INTELLIGENCE] Date logic check failed for {table_name}: {e}")
    
    def _run_gap_detection(self, tables: List[Dict]) -> None:
        """
        Run gap detection between Configuration and Reality tables.
        
        This is the "Configuration Validation vs Employee Conversion Testing" logic:
        - Config tables define what SHOULD exist (codes, plans, setup)
        - Reality tables show what IS being used (actual employee data)
        - The GAP between them = implementation issues
        
        Gap types:
        1. Configured but unused: Code in Config but not in Reality → over-configured
        2. In use but unconfigured: Code in Reality but not in Config → ERROR!
        """
        if not GAP_DETECTION_AVAILABLE:
            logger.debug("[INTELLIGENCE] Gap detection not available")
            return
        
        logger.info("[INTELLIGENCE] Running gap detection...")
        
        try:
            # Initialize gap detection engine with handler
            gap_engine = GapDetectionEngine(structured_handler=self.handler)
            
            # Get table classifications to find Config vs Reality pairs
            config_tables = []
            reality_tables = []
            
            for table_info in tables:
                table_name = table_info.get('table_name', '')
                table_lower = table_name.lower()
                
                # Detect Configuration tables
                if any(pattern in table_lower for pattern in 
                       ['configuration_validation', 'config_valid', '_codes', '_setup', 
                        'code_table', 'earning_code', 'deduction_code', 'tax_code']):
                    config_tables.append(table_info)
                    logger.debug(f"[GAP] Config table: {table_name}")
                
                # Detect Reality/Transaction tables
                elif any(pattern in table_lower for pattern in 
                         ['employee_conversion', 'conversion_test', 'employee_', 
                          'transaction', 'history', 'register', 'payroll']):
                    reality_tables.append(table_info)
                    logger.debug(f"[GAP] Reality table: {table_name}")
            
            if not config_tables or not reality_tables:
                logger.info("[INTELLIGENCE] Gap detection skipped - need both Config and Reality tables")
                return
            
            logger.info(f"[INTELLIGENCE] Gap detection: {len(config_tables)} config tables, {len(reality_tables)} reality tables")
            
            # Run gap detection for each domain
            gaps_found = 0
            
            for config_table in config_tables:
                config_name = config_table.get('table_name', '')
                config_cols = [c.lower() for c in config_table.get('columns', [])]
                
                # Detect domain from config table
                domain = self._detect_domain_from_table(config_name, config_cols)
                
                if not domain:
                    continue
                
                # Find matching reality tables for this domain
                for reality_table in reality_tables:
                    reality_name = reality_table.get('table_name', '')
                    reality_cols = [c.lower() for c in reality_table.get('columns', [])]
                    
                    # Look for common key columns (e.g., earning_code, deduction_code)
                    common_keys = self._find_common_key_columns(config_cols, reality_cols)
                    
                    if common_keys:
                        # Run comparison for each common key
                        for key_col in common_keys:
                            gaps = self._compare_config_vs_reality(
                                config_name, reality_name, key_col, domain
                            )
                            gaps_found += len(gaps)
            
            logger.info(f"[INTELLIGENCE] Gap detection complete: {gaps_found} gaps found")
            
        except Exception as e:
            logger.warning(f"[INTELLIGENCE] Gap detection failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())
    
    def _detect_domain_from_table(self, table_name: str, columns: List[str]) -> Optional[str]:
        """Detect domain from table name and columns."""
        name_lower = table_name.lower()
        cols_str = ' '.join(columns)
        
        if any(x in name_lower or x in cols_str for x in ['earning', 'pay_code', 'compensation']):
            return 'earnings'
        if any(x in name_lower or x in cols_str for x in ['deduction', 'benefit', '401k', 'ded_code']):
            return 'deductions'
        if any(x in name_lower or x in cols_str for x in ['tax', 'sui', 'futa', 'withhold']):
            return 'taxes'
        if any(x in name_lower or x in cols_str for x in ['time', 'hours', 'attendance', 'schedule']):
            return 'time'
        
        return None
    
    def _find_common_key_columns(self, config_cols: List[str], reality_cols: List[str]) -> List[str]:
        """Find columns that could be join keys between config and reality."""
        common = []
        key_patterns = ['_code', '_id', '_num', '_key', '_type']
        
        for config_col in config_cols:
            if any(pattern in config_col for pattern in key_patterns):
                # Look for matching or similar column in reality
                for reality_col in reality_cols:
                    if config_col == reality_col:
                        common.append(config_col)
                        break
                    # Try without common prefixes/suffixes
                    config_base = config_col.replace('_code', '').replace('_id', '').replace('_num', '')
                    reality_base = reality_col.replace('_code', '').replace('_id', '').replace('_num', '')
                    if config_base and config_base == reality_base:
                        common.append((config_col, reality_col))
                        break
        
        return common
    
    def _compare_config_vs_reality(
        self, 
        config_table: str, 
        reality_table: str, 
        key_col: str, 
        domain: str
    ) -> List[Dict]:
        """
        Compare values between Config and Reality tables.
        
        Returns list of gaps:
        - 'configured_unused': In config but not in reality
        - 'in_use_unconfigured': In reality but not in config (ERROR!)
        """
        gaps = []
        
        try:
            # Handle tuple (different column names) or string (same name)
            if isinstance(key_col, tuple):
                config_col, reality_col = key_col
            else:
                config_col = reality_col = key_col
            
            # Get distinct values from each table
            config_values = set()
            reality_values = set()
            
            try:
                result = self.handler.conn.execute(f'''
                    SELECT DISTINCT "{config_col}" FROM "{config_table}"
                    WHERE "{config_col}" IS NOT NULL AND "{config_col}" != ''
                ''').fetchall()
                config_values = {str(r[0]).strip() for r in result if r[0]}
            except Exception as e:
                logger.debug(f"[GAP] Config query failed: {e}")
                return gaps
            
            try:
                result = self.handler.conn.execute(f'''
                    SELECT DISTINCT "{reality_col}" FROM "{reality_table}"
                    WHERE "{reality_col}" IS NOT NULL AND "{reality_col}" != ''
                ''').fetchall()
                reality_values = {str(r[0]).strip() for r in result if r[0]}
            except Exception as e:
                logger.debug(f"[GAP] Reality query failed: {e}")
                return gaps
            
            # Find gaps
            configured_unused = config_values - reality_values
            in_use_unconfigured = reality_values - config_values
            
            # Report configured but unused
            if configured_unused and len(configured_unused) <= 20:  # Don't report huge lists
                self.findings.append(Finding(
                    id=f"gap_unused_{config_table}_{config_col}_{int(time.time())}",
                    category="GAP_DETECTION",
                    finding_type="configured_unused",
                    severity=FindingSeverity.INFO,
                    table_name=config_table,
                    column_name=config_col,
                    title=f"Configured but Unused: {domain.title()} codes",
                    description=f"{len(configured_unused)} {domain} codes are configured in {config_table} but not used in {reality_table}: {', '.join(list(configured_unused)[:10])}{'...' if len(configured_unused) > 10 else ''}",
                    affected_count=len(configured_unused),
                    evidence_sql=f'''
                        SELECT * FROM "{config_table}" WHERE "{config_col}" IN ({','.join([f"'{v}'" for v in list(configured_unused)[:20]])})
                    '''
                ))
                gaps.append({'type': 'configured_unused', 'count': len(configured_unused)})
            
            # Report in use but unconfigured - THIS IS AN ERROR
            if in_use_unconfigured:
                self.findings.append(Finding(
                    id=f"gap_unconfigured_{reality_table}_{reality_col}_{int(time.time())}",
                    category="GAP_DETECTION",
                    finding_type="in_use_unconfigured",
                    severity=FindingSeverity.CRITICAL if len(in_use_unconfigured) > 5 else FindingSeverity.WARNING,
                    table_name=reality_table,
                    column_name=reality_col,
                    title=f"⚠️ IN USE BUT UNCONFIGURED: {domain.title()} codes",
                    description=f"{len(in_use_unconfigured)} {domain} codes are being USED in {reality_table} but NOT CONFIGURED in {config_table}: {', '.join(list(in_use_unconfigured)[:10])}{'...' if len(in_use_unconfigured) > 10 else ''}. This is a data integrity issue!",
                    affected_count=len(in_use_unconfigured),
                    evidence_sql=f'''
                        SELECT * FROM "{reality_table}" WHERE "{reality_col}" IN ({','.join([f"'{v}'" for v in list(in_use_unconfigured)[:20]])})
                    '''
                ))
                gaps.append({'type': 'in_use_unconfigured', 'count': len(in_use_unconfigured)})
            
            if gaps:
                logger.warning(f"[GAP] {config_table} vs {reality_table}.{reality_col}: "
                              f"{len(configured_unused)} unused, {len(in_use_unconfigured)} unconfigured")
            
        except Exception as e:
            logger.warning(f"[GAP] Comparison failed: {e}")
        
        return gaps
    
    # =========================================================================
    # TIER 3: BACKGROUND ANALYSIS (~2-3 minutes)
    # =========================================================================
    
    def _run_tier3_analysis(self, tables: List[Dict]) -> None:
        """Tier 3: Deep analysis - patterns, correlations, anomalies."""
        logger.info("[INTELLIGENCE] Running Tier 3 analysis...")
        # Placeholder for deep analysis
        pass
    
    # =========================================================================
    # ORGANIZATIONAL METRICS COMPUTATION
    # =========================================================================
    
    def _compute_organizational_metrics(self, tables: List[Dict]) -> None:
        """
        Compute organizational metrics using Context Graph and Lookups.
        
        This is the AI consultant intelligence layer:
        - Headcount (total, by company, by location, by status)
        - Hub usage (configured vs in use)
        - Coverage gaps (config items with no reality usage)
        - Benefits participation
        - Demographics breakdowns
        
        All computed DYNAMICALLY from the data - not hardcoded.
        """
        logger.info("[INTELLIGENCE] Computing organizational metrics...")
        
        if not self.handler:
            logger.warning("[INTELLIGENCE] No handler for metrics computation")
            return
        
        try:
            # Step 1: Get Context Graph
            context_graph = None
            if hasattr(self.handler, 'get_context_graph'):
                context_graph = self.handler.get_context_graph(self.project)
            
            if not context_graph:
                logger.warning("[INTELLIGENCE] No context graph available for metrics")
                return
            
            hubs = context_graph.get('hubs', [])
            relationships = context_graph.get('relationships', [])
            
            if not hubs and not relationships:
                logger.info("[INTELLIGENCE] No hubs or relationships in context graph")
                return
            
            # Step 2: Discover status columns and active values from lookups
            status_info = self._discover_status_columns()
            
            # Step 3: Find employee identifier column and reality tables  
            employee_tables = self._find_employee_tables(tables, context_graph)
            
            if not employee_tables:
                logger.info("[INTELLIGENCE] No employee/reality tables found")
                return
            
            # Step 4: Compute workforce metrics (headcount, demographics)
            self._compute_workforce_metrics(employee_tables, status_info)
            
            # Step 5: Compute hub usage metrics (configured vs in use)
            self._compute_hub_usage_metrics(context_graph, status_info, employee_tables)
            
            # Step 6: Compute coverage/gap metrics
            self._compute_coverage_metrics(context_graph, status_info, employee_tables)
            
            # Log summary with breakdown by category
            by_category = {}
            for m in self.metrics:
                cat = m.category.value if hasattr(m.category, 'value') else str(m.category)
                by_category[cat] = by_category.get(cat, 0) + 1
            logger.info(f"[INTELLIGENCE] Computed {len(self.metrics)} organizational metrics: {by_category}")
            
        except Exception as e:
            logger.warning(f"[INTELLIGENCE] Metrics computation failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())
    
    def _discover_status_columns(self) -> Dict:
        """
        Discover status columns and their active values from lookups.
        
        Returns dict with:
        - status_columns: {column_name: {'active_value': 'A', 'table': '...'}}
        - active_patterns: ['A', 'Y', 'Active', etc.]
        """
        status_info = {
            'status_columns': {},
            'active_patterns': ['A', 'Y', 'Active', 'ACTIVE', '1', 'true', 'True']
        }
        
        # Scan lookups for status patterns
        for lookup in self.lookups:
            code_col = lookup.code_column.lower()
            lookup_data = lookup.lookup_data or {}
            
            # Check if this looks like a status column
            if any(pattern in code_col for pattern in ['status', 'active', 'is_']):
                # Find which value means "active"
                active_value = None
                for code, desc in lookup_data.items():
                    desc_lower = str(desc).lower()
                    if desc_lower == 'active' or desc_lower.startswith('active'):
                        active_value = code
                        break
                    elif code.upper() == 'A' and 'active' in desc_lower:
                        active_value = code
                        break
                    elif code.upper() == 'Y':
                        active_value = code
                        break
                
                if active_value:
                    status_info['status_columns'][lookup.code_column] = {
                        'active_value': active_value,
                        'table': lookup.table_name,
                        'lookup_type': lookup.lookup_type
                    }
                    logger.debug(f"[METRICS] Found status column: {lookup.code_column} = '{active_value}' means active")
        
        return status_info
    
    def _find_employee_tables(self, tables: List[Dict], context_graph: Dict) -> List[Dict]:
        """
        Find employee/reality tables that contain headcount data.
        
        v4.7: Now uses Context Graph to identify dimensional columns.
        The graph tells us which columns are spokes to dimensional hubs
        (company, country, location, org_level).
        
        Looks for:
        - Tables with employee_number, emp_id, etc.
        - Tables marked as truth_type = 'reality'
        - Tables with status columns
        - Dimensional columns from Context Graph relationships
        """
        employee_tables = []
        
        # Employee identifier patterns
        employee_id_patterns = ['employee_number', 'employee_id', 'emp_id', 'emp_no', 
                               'worker_id', 'person_id', 'ssn']
        
        # Build dimensional lookup from Context Graph
        # Maps table.column -> semantic_type for dimensional hubs
        dimensional_spokes = self._get_dimensional_spokes_from_graph(context_graph)
        
        for table_info in tables:
            table_name = table_info.get('table_name', '')
            columns = [c.lower() for c in table_info.get('columns', [])]
            
            # Check for employee identifier
            has_employee_id = any(
                any(pattern in col for pattern in employee_id_patterns)
                for col in columns
            )
            
            if has_employee_id:
                # Find the actual employee ID column name
                emp_col = None
                for col in table_info.get('columns', []):
                    if any(pattern in col.lower() for pattern in employee_id_patterns):
                        emp_col = col
                        break
                
                # Check for status column
                status_col = None
                for col in table_info.get('columns', []):
                    col_lower = col.lower()
                    if 'employment_status' in col_lower or col_lower == 'status_code':
                        status_col = col
                        break
                
                # Get dimensional columns FROM CONTEXT GRAPH
                dimensional_cols = {}
                for col in table_info.get('columns', []):
                    key = f"{table_name}.{col}".lower()
                    if key in dimensional_spokes:
                        dim_info = dimensional_spokes[key]
                        dim_name = dim_info['dimension_name']
                        dimensional_cols[dim_name] = {
                            'column': col,
                            'hub_table': dim_info['hub_table'],
                            'hub_column': dim_info['hub_column'],
                            'semantic_type': dim_info['semantic_type']
                        }
                
                # Fallback: also check by name patterns for any missed
                for col in table_info.get('columns', []):
                    col_lower = col.lower()
                    if 'country' in col_lower and 'code' in col_lower and 'country' not in dimensional_cols:
                        dimensional_cols['country'] = {'column': col, 'hub_table': None, 'hub_column': None, 'semantic_type': 'country_code'}
                    elif 'company' in col_lower and 'code' in col_lower and 'company' not in dimensional_cols:
                        dimensional_cols['company'] = {'column': col, 'hub_table': None, 'hub_column': None, 'semantic_type': 'company_code'}
                    elif 'location' in col_lower and 'code' in col_lower and 'location' not in dimensional_cols:
                        dimensional_cols['location'] = {'column': col, 'hub_table': None, 'hub_column': None, 'semantic_type': 'location_code'}
                    elif 'org_level' in col_lower and col_lower not in [d.get('column', '').lower() for d in dimensional_cols.values()]:
                        dim_name = col_lower.replace('_code', '')
                        dimensional_cols[dim_name] = {'column': col, 'hub_table': None, 'hub_column': None, 'semantic_type': col_lower}
                
                employee_tables.append({
                    'table_name': table_name,
                    'employee_column': emp_col,
                    'status_column': status_col,
                    'dimensional_columns': dimensional_cols,
                    'columns': table_info.get('columns', []),
                    'row_count': table_info.get('row_count', 0)
                })
        
        # Sort by row count descending - primary employee table usually has most rows
        employee_tables.sort(key=lambda x: x.get('row_count', 0), reverse=True)
        
        logger.debug(f"[METRICS] Found {len(employee_tables)} employee tables")
        for et in employee_tables[:3]:
            logger.debug(f"[METRICS]   {et['table_name']}: {list(et['dimensional_columns'].keys())}")
        
        return employee_tables
    
    def _get_dimensional_spokes_from_graph(self, context_graph: Dict) -> Dict:
        """
        Extract dimensional spoke columns from Context Graph.
        
        Returns dict mapping "table.column" (lowercase) to dimension info:
        {
            "table.column": {
                "dimension_name": "company",  # simplified name for grouping
                "semantic_type": "company_code",
                "hub_table": "...",
                "hub_column": "..."
            }
        }
        """
        dimensional_spokes = {}
        
        # Dimensional hub types we care about for organizational breakdowns
        dimensional_hub_types = {
            'company_code': 'company',
            'home_company_code': 'company', 
            'country_code': 'country',
            'location_code': 'location',
            'org_level_1_code': 'org_level_1',
            'org_level_2_code': 'org_level_2',
            'org_level_3_code': 'org_level_3',
            'org_level_4_code': 'org_level_4',
            'department_code': 'department',
            'pay_group_code': 'pay_group',
        }
        
        relationships = context_graph.get('relationships', [])
        
        for rel in relationships:
            spoke_table = rel.get('spoke_table', '')
            spoke_column = rel.get('spoke_column', '')
            hub_semantic_type = rel.get('hub_semantic_type', '')
            
            # Check if this spoke connects to a dimensional hub
            for hub_type, dim_name in dimensional_hub_types.items():
                if hub_type in hub_semantic_type.lower() or hub_type in spoke_column.lower():
                    key = f"{spoke_table}.{spoke_column}".lower()
                    dimensional_spokes[key] = {
                        'dimension_name': dim_name,
                        'semantic_type': hub_semantic_type or spoke_column,
                        'hub_table': rel.get('hub_table'),
                        'hub_column': rel.get('hub_column')
                    }
                    break
        
        logger.debug(f"[METRICS] Found {len(dimensional_spokes)} dimensional spokes from Context Graph")
        return dimensional_spokes
    
    def _compute_workforce_metrics(self, employee_tables: List[Dict], status_info: Dict) -> None:
        """
        Compute workforce metrics: headcount, by dimension, demographics.
        
        v4.7: Now uses Context Graph dimensional structure.
        Merges dimensions across all employee tables and uses hub tables for descriptions.
        """
        if not employee_tables:
            return
        
        # Use the primary employee table for headcount (usually personal/master)
        primary_table = None
        for et in employee_tables:
            tn = et.get('table_name', '').lower()
            # Prefer personal or employee master table
            if 'personal' in tn or ('employee' in tn and 'master' in tn):
                primary_table = et
                break
        
        if not primary_table:
            primary_table = employee_tables[0]
        
        table_name = primary_table['table_name']
        emp_col = primary_table['employee_column']
        status_col = primary_table.get('status_column')
        
        # Determine active filter
        active_filter = ""
        active_value = None
        
        if status_col:
            # Check if we know the active value from lookups
            for col_name, info in status_info.get('status_columns', {}).items():
                if col_name.lower() == status_col.lower():
                    active_value = info.get('active_value')
                    break
            
            # Default to 'A' if we have a status column but didn't find in lookups
            if not active_value:
                active_value = 'A'
            
            active_filter = f'WHERE "{status_col}" = \'{active_value}\''
        
        # 1. Total headcount
        try:
            sql = f'SELECT COUNT(DISTINCT "{emp_col}") as cnt FROM "{table_name}" {active_filter}'
            result = self.handler.conn.execute(sql).fetchone()
            total_count = result[0] if result else 0
            
            self.metrics.append(OrganizationalMetric(
                id=f"{self.project}_headcount_total",
                category=MetricCategory.WORKFORCE,
                metric_name="active_headcount",
                value=float(total_count),
                value_formatted=f"{total_count:,}",
                source_table=table_name,
                source_query=sql
            ))
            logger.info(f"[METRICS] Total headcount: {total_count}")
        except Exception as e:
            logger.warning(f"[METRICS] Failed to compute total headcount: {e}")
        
        # 2. MERGE dimensions from ALL employee tables
        # Personal might have company, Company sheet has org_levels
        all_dimensions = {}
        for et in employee_tables:
            for dim_name, dim_info in et.get('dimensional_columns', {}).items():
                if dim_name not in all_dimensions:
                    all_dimensions[dim_name] = {
                        'table_name': et['table_name'],
                        'employee_column': et['employee_column'],
                        'status_column': et.get('status_column'),
                        'dim_info': dim_info
                    }
        
        logger.info(f"[METRICS] Computing breakdowns for {len(all_dimensions)} dimensions: {list(all_dimensions.keys())}")
        
        # =====================================================================
        # DATA-DRIVEN DIMENSION SCORING
        # Score each dimension by: cardinality (prefer 3-50), coverage, hub status
        # Only compute breakdowns for TOP dimensions
        # =====================================================================
        MAX_DIMENSIONS = 6  # Only compute breakdowns for top N dimensions
        MAX_VALUES_PER_DIMENSION = 10  # Only store top M values per dimension
        
        scored_dimensions = []
        
        for dim_name, dim_data in all_dimensions.items():
            try:
                source_table = dim_data['table_name']
                dim_info = dim_data['dim_info']
                
                # Handle new structure
                if isinstance(dim_info, dict):
                    dim_col = dim_info.get('column')
                    is_hub = dim_info.get('hub_table') is not None
                else:
                    dim_col = dim_info
                    is_hub = False
                
                if not dim_col:
                    continue
                
                # Get cardinality and coverage
                cardinality_sql = f'SELECT COUNT(DISTINCT "{dim_col}") FROM "{source_table}" WHERE "{dim_col}" IS NOT NULL'
                cardinality = self.handler.conn.execute(cardinality_sql).fetchone()[0] or 0
                
                coverage_sql = f'SELECT COUNT(*) FROM "{source_table}" WHERE "{dim_col}" IS NOT NULL'
                total_sql = f'SELECT COUNT(*) FROM "{source_table}"'
                non_null = self.handler.conn.execute(coverage_sql).fetchone()[0] or 0
                total = self.handler.conn.execute(total_sql).fetchone()[0] or 1
                coverage_pct = (non_null / total) * 100 if total > 0 else 0
                
                # SCORE THE DIMENSION (data-driven, no hardcoding)
                score = 0
                
                # Cardinality score: prefer 3-50 values
                if 3 <= cardinality <= 50:
                    score += 3  # Sweet spot
                elif cardinality == 1:
                    score -= 5  # Useless - only one value
                elif cardinality == 2:
                    score += 1  # Binary - somewhat useful
                elif 50 < cardinality <= 100:
                    score += 1  # Getting granular
                elif cardinality > 100:
                    score -= 2  # Too granular for summary metrics
                
                # Coverage score: prefer high coverage
                if coverage_pct >= 90:
                    score += 2
                elif coverage_pct >= 50:
                    score += 1
                elif coverage_pct < 10:
                    score -= 2  # Mostly empty
                
                # Hub score: Context Graph hubs are more meaningful
                if is_hub:
                    score += 2
                
                scored_dimensions.append({
                    'dim_name': dim_name,
                    'dim_data': dim_data,
                    'score': score,
                    'cardinality': cardinality,
                    'coverage_pct': coverage_pct,
                    'is_hub': is_hub
                })
                
                logger.debug(f"[METRICS] Scored {dim_name}: score={score}, cardinality={cardinality}, coverage={coverage_pct:.1f}%, hub={is_hub}")
                
            except Exception as e:
                logger.debug(f"[METRICS] Could not score dimension {dim_name}: {e}")
        
        # Sort by score descending, take top N
        scored_dimensions.sort(key=lambda x: x['score'], reverse=True)
        top_dimensions = scored_dimensions[:MAX_DIMENSIONS]
        
        logger.info(f"[METRICS] Selected top {len(top_dimensions)} dimensions: {[d['dim_name'] for d in top_dimensions]}")
        
        # 3. Headcount by each TOP dimension (limited values)
        for dim_entry in top_dimensions:
            dim_name = dim_entry['dim_name']
            dim_data = dim_entry['dim_data']
            
            try:
                source_table = dim_data['table_name']
                source_emp_col = dim_data['employee_column']
                source_status_col = dim_data.get('status_column')
                dim_info = dim_data['dim_info']
                
                # Handle new structure: dim_info is now a dict with 'column', 'hub_table', etc.
                if isinstance(dim_info, dict):
                    dim_col = dim_info.get('column')
                    hub_table = dim_info.get('hub_table')
                    hub_column = dim_info.get('hub_column')
                else:
                    # Legacy: dim_info is just the column name
                    dim_col = dim_info
                    hub_table = None
                    hub_column = None
                
                if not dim_col:
                    continue
                
                # Build status filter for this table
                source_filter = ""
                if source_status_col:
                    for col_name, info in status_info.get('status_columns', {}).items():
                        if col_name.lower() == source_status_col.lower():
                            source_filter = f'WHERE "{source_status_col}" = \'{info.get("active_value", "A")}\''
                            break
                    if not source_filter and source_status_col:
                        source_filter = f'WHERE "{source_status_col}" = \'A\''
                
                # Try to get description from hub table via JOIN
                # LIMIT to top values only
                limit_clause = f"LIMIT {MAX_VALUES_PER_DIMENSION}"
                
                if hub_table and hub_column:
                    # Find description column in hub table (usually ends with _name or description)
                    desc_col = self._find_description_column_in_hub(hub_table, hub_column)
                    
                    if desc_col:
                        sql = f'''
                            SELECT e."{dim_col}", h."{desc_col}", COUNT(DISTINCT e."{source_emp_col}") as cnt 
                            FROM "{source_table}" e
                            LEFT JOIN "{hub_table}" h ON e."{dim_col}" = h."{hub_column}"
                            {source_filter}
                            GROUP BY e."{dim_col}", h."{desc_col}"
                            ORDER BY cnt DESC
                            {limit_clause}
                        '''
                    else:
                        sql = f'''
                            SELECT "{dim_col}", COUNT(DISTINCT "{source_emp_col}") as cnt 
                            FROM "{source_table}" 
                            {source_filter}
                            GROUP BY "{dim_col}"
                            ORDER BY cnt DESC
                            {limit_clause}
                        '''
                else:
                    # No hub - look for description column in same table
                    desc_col = None
                    columns = [c for c in dim_data.get('columns', []) if isinstance(c, str)]
                    base_name = dim_col.lower().replace('_code', '')
                    for col in columns:
                        col_lower = col.lower()
                        if col_lower == f"{base_name}_name" or col_lower == base_name or col_lower == f"{base_name}_description":
                            desc_col = col
                            break
                    
                    if desc_col:
                        sql = f'''
                            SELECT "{dim_col}", "{desc_col}", COUNT(DISTINCT "{source_emp_col}") as cnt 
                            FROM "{source_table}" 
                            {source_filter}
                            GROUP BY "{dim_col}", "{desc_col}"
                            ORDER BY cnt DESC
                            {limit_clause}
                        '''
                    else:
                        sql = f'''
                            SELECT "{dim_col}", COUNT(DISTINCT "{source_emp_col}") as cnt 
                            FROM "{source_table}" 
                            {source_filter}
                            GROUP BY "{dim_col}"
                            ORDER BY cnt DESC
                            {limit_clause}
                        '''
                
                results = self.handler.conn.execute(sql).fetchall()
                
                for row in results:
                    if len(row) == 3:
                        dim_value, dim_desc, count = row[0], row[1], row[2]
                        display_value = f"{dim_desc} ({dim_value})" if dim_desc else str(dim_value)
                    else:
                        dim_value, count = row[0], row[1]
                        display_value = str(dim_value)
                    
                    if dim_value:  # Skip nulls
                        self.metrics.append(OrganizationalMetric(
                            id=f"{self.project}_headcount_{dim_name}_{dim_value}",
                            category=MetricCategory.DIMENSIONAL,
                            metric_name=f"headcount_by_{dim_name}",
                            value=float(count),
                            value_formatted=f"{count:,}",
                            dimension=dim_name,
                            dimension_value=display_value,
                            source_table=source_table,
                            source_query=sql
                        ))
                
                logger.info(f"[METRICS] Headcount by {dim_name}: {len(results)} values")
            except Exception as e:
                logger.warning(f"[METRICS] Failed to compute headcount by {dim_name}: {e}")
    
    def _find_description_column_in_hub(self, hub_table: str, hub_column: str) -> Optional[str]:
        """Find the description column in a hub table for a given code column."""
        try:
            # Query the hub table schema
            sql = f"SELECT * FROM \"{hub_table}\" LIMIT 1"
            result = self.handler.conn.execute(sql)
            columns = [desc[0] for desc in result.description]
            
            # Look for description column
            base_name = hub_column.lower().replace('_code', '')
            for col in columns:
                col_lower = col.lower()
                if col_lower in [f"{base_name}_name", f"{base_name}", 'description', 'name', f"{base_name}_description"]:
                    return col
            
            return None
        except Exception as e:
            logger.debug(f"[METRICS] Could not find description column in {hub_table}: {e}")
            return None
    
    def _compute_hub_usage_metrics(self, context_graph: Dict, status_info: Dict, 
                                   employee_tables: List[Dict]) -> None:
        """
        Compute hub usage metrics: how many config items are actually in use.
        
        For each hub (earnings, deductions, etc.) with reality spokes:
        - Count distinct values in config (hub)
        - Count distinct values in reality (spoke) for active employees
        - Calculate coverage percentage
        """
        hubs = context_graph.get('hubs', [])
        relationships = context_graph.get('relationships', [])
        
        # Limit to avoid metric explosion
        MAX_HUB_USAGE_METRICS = 15
        hub_usage_count = 0
        
        # Find hubs that have reality spokes
        for hub in hubs:
            # Stop if we've hit the limit
            if hub_usage_count >= MAX_HUB_USAGE_METRICS:
                logger.debug(f"[METRICS] Stopping hub usage metrics at {MAX_HUB_USAGE_METRICS}")
                break
                
            hub_type = hub.get('semantic_type', '')
            hub_table = hub.get('table', '')
            hub_column = hub.get('column', '')
            hub_cardinality = hub.get('cardinality', 0)
            truth_type = hub.get('truth_type', '')
            
            # Only process configuration hubs
            if truth_type != 'configuration':
                continue
            
            # Find reality spokes for this hub
            reality_spokes = [
                r for r in relationships
                if r.get('semantic_type') == hub_type and r.get('truth_type') == 'reality'
            ]
            
            if not reality_spokes:
                continue
            
            # Use the first reality spoke to compute usage
            spoke = reality_spokes[0]
            spoke_table = spoke.get('spoke_table', '')
            spoke_column = spoke.get('spoke_column', '')
            
            try:
                # Find active filter for this spoke table
                active_filter = ""
                for et in employee_tables:
                    if et['table_name'] == spoke_table:
                        status_col = et.get('status_column')
                        if status_col:
                            # Check for active column in this table
                            cols_lower = [c.lower() for c in et.get('columns', [])]
                            if 'active' in cols_lower:
                                active_filter = "WHERE active = 'Y'"
                            elif 'benefit_status_code' in cols_lower:
                                active_filter = "WHERE benefit_status_code = 'A'"
                        break
                
                # Count distinct in-use values
                sql = f'''
                    SELECT COUNT(DISTINCT "{spoke_column}") 
                    FROM "{spoke_table}"
                    {active_filter}
                '''
                result = self.handler.conn.execute(sql).fetchone()
                in_use_count = result[0] if result else 0
                
                # Coverage percentage
                coverage = (in_use_count / hub_cardinality * 100) if hub_cardinality > 0 else 0
                
                self.metrics.append(OrganizationalMetric(
                    id=f"{self.project}_hub_usage_{hub_type}",
                    category=MetricCategory.CONFIGURATION,
                    metric_name=f"{hub_type}_usage",
                    value=coverage,
                    value_formatted=f"{in_use_count:,} of {hub_cardinality:,} ({coverage:.1f}%)",
                    numerator=in_use_count,
                    denominator=hub_cardinality,
                    source_table=spoke_table,
                    source_query=sql
                ))
                
                hub_usage_count += 1
                logger.debug(f"[METRICS] Hub usage {hub_type}: {in_use_count}/{hub_cardinality} ({coverage:.1f}%)")
                
            except Exception as e:
                logger.warning(f"[METRICS] Failed to compute hub usage for {hub_type}: {e}")
    
    def _compute_coverage_metrics(self, context_graph: Dict, status_info: Dict,
                                  employee_tables: List[Dict]) -> None:
        """
        Compute coverage gap metrics: employees with/without certain assignments.
        
        For each hub type with reality spokes:
        - Count employees WITH at least one assignment
        - Count employees WITHOUT any assignment
        - Calculate participation rate
        """
        hubs = context_graph.get('hubs', [])
        relationships = context_graph.get('relationships', [])
        
        # Get primary employee table for total headcount
        primary_table = None
        total_employees = 0
        emp_col = None
        
        for et in employee_tables:
            tn = et.get('table_name', '').lower()
            if 'personal' in tn:
                primary_table = et
                break
        
        if not primary_table and employee_tables:
            primary_table = employee_tables[0]
        
        if primary_table:
            emp_col = primary_table['employee_column']
            status_col = primary_table.get('status_column')
            table_name = primary_table['table_name']
            
            try:
                active_filter = f"WHERE \"{status_col}\" = 'A'" if status_col else ""
                sql = f'SELECT COUNT(DISTINCT "{emp_col}") FROM "{table_name}" {active_filter}'
                result = self.handler.conn.execute(sql).fetchone()
                total_employees = result[0] if result else 0
            except Exception as e:
                logger.warning(f"[METRICS] Could not get total employees: {e}")
                return
        
        if total_employees == 0:
            return
        
        # For each hub type, compute participation
        # Limit to avoid metric explosion
        MAX_HUB_COVERAGE_METRICS = 15
        hub_types_processed = set()
        
        for rel in relationships:
            hub_type = rel.get('semantic_type', '')
            spoke_table = rel.get('spoke_table', '')
            spoke_column = rel.get('spoke_column', '')
            truth_type = rel.get('truth_type', '')
            
            if truth_type != 'reality' or hub_type in hub_types_processed:
                continue
            
            # Stop if we've hit the limit
            if len(hub_types_processed) >= MAX_HUB_COVERAGE_METRICS:
                logger.debug(f"[METRICS] Stopping coverage metrics at {MAX_HUB_COVERAGE_METRICS} hub types")
                break
            
            hub_types_processed.add(hub_type)
            
            try:
                # Find employee column in this spoke table
                spoke_emp_col = None
                for et in employee_tables:
                    if et['table_name'] == spoke_table:
                        spoke_emp_col = et.get('employee_column')
                        break
                
                if not spoke_emp_col:
                    continue
                
                # Count distinct employees with this assignment type
                # Apply active filter if available
                active_filter = ""
                for et in employee_tables:
                    if et['table_name'] == spoke_table:
                        cols = [c.lower() for c in et.get('columns', [])]
                        if 'active' in cols:
                            active_filter = "WHERE active = 'Y'"
                        elif 'benefit_status_code' in cols:
                            active_filter = "WHERE benefit_status_code = 'A'"
                        break
                
                sql = f'''
                    SELECT COUNT(DISTINCT "{spoke_emp_col}")
                    FROM "{spoke_table}"
                    {active_filter}
                '''
                result = self.handler.conn.execute(sql).fetchone()
                employees_with = result[0] if result else 0
                
                participation_rate = (employees_with / total_employees * 100) if total_employees > 0 else 0
                
                self.metrics.append(OrganizationalMetric(
                    id=f"{self.project}_participation_{hub_type}",
                    category=MetricCategory.BENEFITS if 'deduction' in hub_type.lower() or 'benefit' in hub_type.lower() else MetricCategory.WORKFORCE,
                    metric_name=f"{hub_type}_participation",
                    value=participation_rate,
                    value_formatted=f"{employees_with:,} of {total_employees:,} ({participation_rate:.1f}%)",
                    numerator=employees_with,
                    denominator=total_employees,
                    source_table=spoke_table,
                    source_query=sql
                ))
                
                logger.debug(f"[METRICS] {hub_type} participation: {employees_with}/{total_employees} ({participation_rate:.1f}%)")
                
            except Exception as e:
                logger.warning(f"[METRICS] Failed to compute participation for {hub_type}: {e}")
    
    # =========================================================================
    # TASK GENERATION
    # =========================================================================
    
    def _generate_tasks(self) -> None:
        """Generate actionable tasks from findings."""
        for finding in self.findings:
            if finding.severity in [FindingSeverity.CRITICAL, FindingSeverity.WARNING]:
                task = Task(
                    id=f"task_{finding.id}",
                    title=f"Fix: {finding.title}",
                    description=finding.description,
                    finding_ids=[finding.id],
                    severity=finding.severity,
                    shortcut_type="review",
                    shortcut_data={'evidence_sql': finding.evidence_sql},
                    estimated_minutes=15 if finding.severity == FindingSeverity.CRITICAL else 5
                )
                self.tasks.append(task)
    
    # =========================================================================
    # RETRIEVAL METHODS
    # =========================================================================
    
    def get_findings(self, severity: str = None, category: str = None) -> List[Finding]:
        """Get findings, optionally filtered."""
        results = self.findings
        
        if severity:
            results = [f for f in results if f.severity.value == severity]
        if category:
            results = [f for f in results if f.category == category]
        
        return results
    
    def get_tasks(self, status: str = None) -> List[Task]:
        """Get tasks, optionally filtered by status."""
        if status:
            return [t for t in self.tasks if t.status.value == status]
        return self.tasks
    
    def get_evidence(self, finding_id: str) -> Optional[Evidence]:
        """Get evidence package for a finding."""
        finding = next((f for f in self.findings if f.id == finding_id), None)
        if not finding:
            return None
        
        # Build evidence package
        records = []
        if finding.evidence_sql and self.handler:
            try:
                result = self.handler.conn.execute(finding.evidence_sql).fetchall()
                # Get column names
                col_info = self.handler.conn.execute(f"DESCRIBE ({finding.evidence_sql})").fetchall()
                columns = [c[0] for c in col_info]
                records = [dict(zip(columns, row)) for row in result[:100]]
            except Exception:
                pass
        
        return Evidence(
            finding_id=finding_id,
            sql_query=finding.evidence_sql,
            records=records,
            record_count=len(records),
            generated_at=datetime.now()
        )
    
    def get_lookups(self, lookup_type: str = None) -> List[ReferenceLookup]:
        """Get detected lookups, optionally filtered by type."""
        if lookup_type:
            return [l for l in self.lookups if l.lookup_type == lookup_type]
        return self.lookups
    
    def get_organizational_metrics(self, category: str = None) -> List[OrganizationalMetric]:
        """
        Get organizational metrics, optionally filtered by category.
        
        Categories: workforce, compensation, benefits, demographics, configuration, dimensional
        """
        if category:
            try:
                cat_enum = MetricCategory(category)
                return [m for m in self.metrics if m.category == cat_enum]
            except ValueError:
                return [m for m in self.metrics if m.category.value == category]
        return self.metrics
    
    def decode_value(self, table_name: str, column_name: str, code: str) -> str:
        """Decode a code value using detected lookups."""
        for lookup in self.lookups:
            if lookup.table_name == table_name and lookup.code_column == column_name:
                return lookup.decode(code)
        return code
    
    # =========================================================================
    # WORK TRAIL
    # =========================================================================
    
    def _log_work_trail(self, action_type: str, action_description: str, 
                        table_name: str = None, finding_id: str = None,
                        task_id: str = None, actor: str = "system", **kwargs) -> None:
        """Log an entry to the work trail."""
        entry = WorkTrailEntry(
            id=f"wt_{int(time.time())}_{len(self.work_trail)}",
            timestamp=datetime.now(),
            action_type=action_type,
            action_description=action_description,
            actor=actor,
            project=self.project,
            table_name=table_name,
            finding_id=finding_id,
            task_id=task_id,
            **kwargs
        )
        self.work_trail.append(entry)
        self._persist_work_trail_entry(entry)
    
    def get_work_trail(self, limit: int = 50) -> List[WorkTrailEntry]:
        """Get recent work trail entries."""
        return self.work_trail[-limit:]
    
    # =========================================================================
    # PERSISTENCE
    # =========================================================================
    
    def _get_project_tables(self) -> List[Dict]:
        """Get all tables for this project."""
        tables = []
        
        try:
            all_tables = self.handler.conn.execute("SHOW TABLES").fetchall()
            project_prefix = (self.project or '').lower().replace(' ', '_').replace('-', '_')
            
            for (table_name,) in all_tables:
                if table_name.startswith('_'):
                    continue
                
                if project_prefix and not table_name.lower().startswith(project_prefix.lower()):
                    continue
                
                # Get columns
                try:
                    col_result = self.handler.conn.execute(f'DESCRIBE "{table_name}"').fetchall()
                    columns = [row[0] for row in col_result]
                except Exception:
                    columns = []
                
                # Get row count
                try:
                    count_result = self.handler.conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()
                    row_count = count_result[0] if count_result else 0
                except Exception:
                    row_count = 0
                
                tables.append({
                    'table_name': table_name,
                    'columns': columns,
                    'row_count': row_count
                })
                
        except Exception as e:
            logger.error(f"[INTELLIGENCE] Failed to get tables: {e}")
        
        return tables
    
    def _persist_results(self) -> None:
        """Persist analysis results to database."""
        if not self.handler or not self.handler.conn:
            return
        
        try:
            # Create intelligence tables if they don't exist
            self._ensure_tables_exist()
            
            # Store project intelligence summary
            summary_json = json.dumps(self._build_summary())
            
            self.handler.conn.execute("""
                INSERT OR REPLACE INTO _project_intelligence 
                (project_name, analyzed_at, total_tables, total_rows, total_columns,
                 critical_count, warning_count, info_count, summary_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                self.project,
                self.analyzed_at.isoformat(),
                self.total_tables,
                self.total_rows,
                self.total_columns,
                len([f for f in self.findings if f.severity == FindingSeverity.CRITICAL]),
                len([f for f in self.findings if f.severity == FindingSeverity.WARNING]),
                len([f for f in self.findings if f.severity == FindingSeverity.INFO]),
                summary_json
            ])
            
            # Store findings
            for finding in self.findings:
                self.handler.conn.execute("""
                    INSERT OR REPLACE INTO _intelligence_findings
                    (id, project_name, category, finding_type, severity,
                     table_name, column_name, title, description,
                     affected_count, affected_percentage, evidence_sql, details_json, detected_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    finding.id, self.project, finding.category, finding.finding_type,
                    finding.severity.value, finding.table_name, finding.column_name,
                    finding.title, finding.description, finding.affected_count,
                    finding.affected_percentage, finding.evidence_sql,
                    json.dumps(finding.details), finding.detected_at.isoformat()
                ])
            
            # Store tasks
            for task in self.tasks:
                self.handler.conn.execute("""
                    INSERT OR REPLACE INTO _intelligence_tasks
                    (id, project_name, title, description, severity, status,
                     shortcut_type, shortcut_data_json, finding_ids_json,
                     estimated_minutes, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    task.id, self.project, task.title, task.description,
                    task.severity.value, task.status.value, task.shortcut_type,
                    json.dumps(task.shortcut_data), json.dumps(task.finding_ids),
                    task.estimated_minutes, task.created_at.isoformat()
                ])
            
            # Store lookups
            for lookup in self.lookups:
                self.handler.conn.execute("""
                    INSERT OR REPLACE INTO _intelligence_lookups
                    (id, project_name, table_name, code_column, description_column,
                     lookup_type, confidence, lookup_data_json, entry_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    f"{self.project}_{lookup.table_name}_{lookup.code_column}",
                    self.project, lookup.table_name, lookup.code_column,
                    lookup.description_column, lookup.lookup_type, lookup.confidence,
                    json.dumps(lookup.lookup_data), lookup.entry_count
                ])
            
            # Store relationships
            for rel in self.relationships:
                self.handler.conn.execute("""
                    INSERT OR REPLACE INTO _intelligence_relationships
                    (id, project_name, from_table, from_column, to_table, to_column,
                     relationship_type, confidence, orphan_count, orphan_percentage)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    f"{self.project}_{rel.from_table}_{rel.from_column}_{rel.to_table}",
                    self.project, rel.from_table, rel.from_column,
                    rel.to_table, rel.to_column, rel.relationship_type,
                    rel.confidence, rel.orphan_count, rel.orphan_percentage
                ])
            
            # NEW: Store organizational metrics
            for metric in self.metrics:
                self.handler.conn.execute("""
                    INSERT OR REPLACE INTO _organizational_metrics
                    (id, project_name, category, metric_name, value, value_formatted,
                     dimension, dimension_value, numerator, denominator,
                     source_table, source_query, computed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    metric.id, self.project, metric.category.value, metric.metric_name,
                    metric.value, metric.value_formatted, metric.dimension,
                    metric.dimension_value, metric.numerator, metric.denominator,
                    metric.source_table, metric.source_query, metric.computed_at.isoformat()
                ])
            
            # NEW: Store table classifications
            self._persist_classifications()
            
            logger.info(f"[INTELLIGENCE] Persisted results for {self.project}")
            
        except Exception as e:
            logger.error(f"[INTELLIGENCE] Failed to persist results: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _persist_classifications(self) -> None:
        """
        Persist table classifications to dedicated table.
        
        NEW in v2.0: Classifications are stored in _table_classifications
        for direct querying by intelligence engine and table selector.
        """
        if not self.handler or not self.handler.conn:
            return
        
        try:
            # Clear existing classifications for this project
            self.handler.conn.execute("""
                DELETE FROM _table_classifications WHERE project_name = ?
            """, [self.project])
            
            # Insert new classifications
            for classification in self.tables:
                self.handler.conn.execute("""
                    INSERT INTO _table_classifications
                    (id, project_name, table_name, table_type, domain, primary_entity,
                     confidence, row_count, column_count, likely_key_columns_json,
                     parent_tables_json, child_tables_json, config_target, classified_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    f"{self.project}_{classification.table_name}",
                    self.project,
                    classification.table_name,
                    classification.table_type.value,
                    classification.domain.value,
                    classification.primary_entity,
                    classification.confidence,
                    classification.row_count,
                    classification.column_count,
                    json.dumps(classification.likely_key_columns),
                    json.dumps(classification.parent_tables),
                    json.dumps(classification.child_tables),
                    classification.config_target,
                    datetime.now().isoformat()
                ])
            
            logger.info(f"[INTELLIGENCE] Persisted {len(self.tables)} table classifications")
            
        except Exception as e:
            logger.error(f"[INTELLIGENCE] Failed to persist classifications: {e}")
    
    def _ensure_tables_exist(self) -> None:
        """Create intelligence tables if they don't exist."""
        
        self.handler.conn.execute("""
            CREATE TABLE IF NOT EXISTS _project_intelligence (
                project_name VARCHAR PRIMARY KEY,
                analyzed_at VARCHAR,
                total_tables INTEGER,
                total_rows INTEGER,
                total_columns INTEGER,
                critical_count INTEGER,
                warning_count INTEGER,
                info_count INTEGER,
                summary_json TEXT
            )
        """)
        
        self.handler.conn.execute("""
            CREATE TABLE IF NOT EXISTS _intelligence_findings (
                id VARCHAR PRIMARY KEY,
                project_name VARCHAR,
                category VARCHAR,
                finding_type VARCHAR,
                severity VARCHAR,
                table_name VARCHAR,
                column_name VARCHAR,
                title VARCHAR,
                description TEXT,
                affected_count INTEGER,
                affected_percentage DOUBLE,
                evidence_sql TEXT,
                details_json TEXT,
                detected_at VARCHAR
            )
        """)
        
        self.handler.conn.execute("""
            CREATE TABLE IF NOT EXISTS _intelligence_tasks (
                id VARCHAR PRIMARY KEY,
                project_name VARCHAR,
                title VARCHAR,
                description TEXT,
                severity VARCHAR,
                status VARCHAR,
                shortcut_type VARCHAR,
                shortcut_data_json TEXT,
                finding_ids_json TEXT,
                estimated_minutes INTEGER,
                created_at VARCHAR,
                completed_at VARCHAR
            )
        """)
        
        self.handler.conn.execute("""
            CREATE TABLE IF NOT EXISTS _intelligence_lookups (
                id VARCHAR PRIMARY KEY,
                project_name VARCHAR,
                table_name VARCHAR,
                code_column VARCHAR,
                description_column VARCHAR,
                lookup_type VARCHAR,
                confidence DOUBLE,
                lookup_data_json TEXT,
                entry_count INTEGER
            )
        """)
        
        self.handler.conn.execute("""
            CREATE TABLE IF NOT EXISTS _intelligence_relationships (
                id VARCHAR PRIMARY KEY,
                project_name VARCHAR,
                from_table VARCHAR,
                from_column VARCHAR,
                to_table VARCHAR,
                to_column VARCHAR,
                relationship_type VARCHAR,
                confidence DOUBLE,
                orphan_count INTEGER,
                orphan_percentage DOUBLE
            )
        """)
        
        self.handler.conn.execute("""
            CREATE TABLE IF NOT EXISTS _intelligence_work_trail (
                id VARCHAR PRIMARY KEY,
                project_name VARCHAR,
                timestamp VARCHAR,
                action_type VARCHAR,
                action_description TEXT,
                actor VARCHAR,
                table_name VARCHAR,
                finding_id VARCHAR,
                task_id VARCHAR,
                details_json TEXT,
                attachments_json TEXT
            )
        """)
        
        # NEW in v2.0: Table classifications table
        self.handler.conn.execute("""
            CREATE TABLE IF NOT EXISTS _table_classifications (
                id VARCHAR PRIMARY KEY,
                project_name VARCHAR NOT NULL,
                table_name VARCHAR NOT NULL,
                table_type VARCHAR NOT NULL,
                domain VARCHAR NOT NULL,
                primary_entity VARCHAR,
                confidence DOUBLE,
                row_count INTEGER,
                column_count INTEGER,
                likely_key_columns_json TEXT,
                parent_tables_json TEXT,
                child_tables_json TEXT,
                config_target VARCHAR,
                classified_at VARCHAR
            )
        """)
        
        # NEW: Organizational metrics table
        self.handler.conn.execute("""
            CREATE TABLE IF NOT EXISTS _organizational_metrics (
                id VARCHAR PRIMARY KEY,
                project_name VARCHAR NOT NULL,
                category VARCHAR NOT NULL,
                metric_name VARCHAR NOT NULL,
                value DOUBLE,
                value_formatted VARCHAR,
                dimension VARCHAR,
                dimension_value VARCHAR,
                numerator INTEGER,
                denominator INTEGER,
                source_table VARCHAR,
                source_query TEXT,
                computed_at VARCHAR
            )
        """)
    
    def _persist_work_trail_entry(self, entry: WorkTrailEntry) -> None:
        """Persist a single work trail entry."""
        if not self.handler or not self.handler.conn:
            return
        
        try:
            self.handler.conn.execute("""
                INSERT INTO _intelligence_work_trail
                (id, project_name, timestamp, action_type, action_description,
                 actor, table_name, finding_id, task_id, details_json, attachments_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                entry.id, self.project, entry.timestamp.isoformat(),
                entry.action_type, entry.action_description, entry.actor,
                entry.table_name, entry.finding_id, entry.task_id,
                json.dumps(entry.details), json.dumps(entry.attachments)
            ])
        except Exception as e:
            logger.warning(f"[INTELLIGENCE] Failed to persist work trail entry: {e}")
    
    def load_from_database(self) -> bool:
        """Load previously computed analysis from database."""
        if not self.handler or not self.handler.conn:
            return False
        
        try:
            # Load summary
            result = self.handler.conn.execute("""
                SELECT * FROM _project_intelligence WHERE project_name = ?
            """, [self.project]).fetchone()
            
            if not result:
                return False
            
            self.analyzed_at = datetime.fromisoformat(result[1]) if result[1] else None
            self.total_tables = result[2] or 0
            self.total_rows = result[3] or 0
            self.total_columns = result[4] or 0
            
            # Load findings
            findings_result = self.handler.conn.execute("""
                SELECT * FROM _intelligence_findings WHERE project_name = ?
            """, [self.project]).fetchall()
            
            for row in findings_result:
                self.findings.append(Finding(
                    id=row[0],
                    category=row[2],
                    finding_type=row[3],
                    severity=FindingSeverity(row[4]),
                    table_name=row[5],
                    column_name=row[6],
                    title=row[7],
                    description=row[8],
                    affected_count=row[9] or 0,
                    affected_percentage=row[10] or 0,
                    evidence_sql=row[11] or "",
                    details=json.loads(row[12]) if row[12] else {},
                    detected_at=datetime.fromisoformat(row[13]) if row[13] else datetime.now()
                ))
            
            # Load tasks
            tasks_result = self.handler.conn.execute("""
                SELECT * FROM _intelligence_tasks WHERE project_name = ?
            """, [self.project]).fetchall()
            
            for row in tasks_result:
                self.tasks.append(Task(
                    id=row[0],
                    title=row[2],
                    description=row[3],
                    severity=FindingSeverity(row[4]),
                    status=TaskStatus(row[5]),
                    shortcut_type=row[6] or "",
                    shortcut_data=json.loads(row[7]) if row[7] else {},
                    finding_ids=json.loads(row[8]) if row[8] else [],
                    estimated_minutes=row[9] or 0,
                    created_at=datetime.fromisoformat(row[10]) if row[10] else datetime.now()
                ))
            
            # Load lookups
            lookups_result = self.handler.conn.execute("""
                SELECT * FROM _intelligence_lookups WHERE project_name = ?
            """, [self.project]).fetchall()
            
            for row in lookups_result:
                self.lookups.append(ReferenceLookup(
                    table_name=row[2],
                    code_column=row[3],
                    description_column=row[4],
                    lookup_type=row[5],
                    confidence=row[6] or 0,
                    lookup_data=json.loads(row[7]) if row[7] else {},
                    entry_count=row[8] or 0
                ))
            
            # Load relationships
            rels_result = self.handler.conn.execute("""
                SELECT * FROM _intelligence_relationships WHERE project_name = ?
            """, [self.project]).fetchall()
            
            for row in rels_result:
                self.relationships.append(Relationship(
                    from_table=row[2],
                    from_column=row[3],
                    to_table=row[4],
                    to_column=row[5],
                    relationship_type=row[6],
                    confidence=row[7] or 0,
                    orphan_count=row[8] or 0,
                    orphan_percentage=row[9] or 0
                ))
            
            # NEW: Load organizational metrics
            try:
                metrics_result = self.handler.conn.execute("""
                    SELECT * FROM _organizational_metrics WHERE project_name = ?
                """, [self.project]).fetchall()
                
                for row in metrics_result:
                    self.metrics.append(OrganizationalMetric(
                        id=row[0],
                        category=MetricCategory(row[2]),
                        metric_name=row[3],
                        value=row[4] or 0,
                        value_formatted=row[5] or "",
                        dimension=row[6],
                        dimension_value=row[7],
                        numerator=row[8],
                        denominator=row[9],
                        source_table=row[10],
                        source_query=row[11],
                        computed_at=datetime.fromisoformat(row[12]) if row[12] else datetime.now()
                    ))
            except Exception as e:
                logger.debug(f"[INTELLIGENCE] No organizational metrics to load: {e}")
            
            # NEW: Load table classifications
            self._load_classifications()
            
            self.tier1_complete = True
            self.tier2_complete = True
            
            logger.info(f"[INTELLIGENCE] Loaded from database: {len(self.findings)} findings, {len(self.tasks)} tasks, {len(self.tables)} classifications, {len(self.metrics)} metrics")
            return True
            
        except Exception as e:
            logger.warning(f"[INTELLIGENCE] Failed to load from database: {e}")
            return False
    
    # =========================================================================
    # SUMMARY BUILDER
    # =========================================================================
    
    def _build_summary(self) -> Dict:
        """Build complete analysis summary."""
        
        critical = [f for f in self.findings if f.severity == FindingSeverity.CRITICAL]
        warnings = [f for f in self.findings if f.severity == FindingSeverity.WARNING]
        info = [f for f in self.findings if f.severity == FindingSeverity.INFO]
        
        # Get relevant domain knowledge
        domain_knowledge = self._get_relevant_domain_knowledge()
        
        return {
            'project': self.project,
            'analyzed_at': self.analyzed_at.isoformat() if self.analyzed_at else None,
            'analysis_time_seconds': self.analysis_time_seconds,
            
            # Structure
            'structure': {
                'total_tables': self.total_tables,
                'total_rows': self.total_rows,
                'total_columns': self.total_columns,
                'table_classifications': [t.to_dict() for t in self.tables],
                'relationships': [r.to_dict() for r in self.relationships],
                'lookups_detected': len(self.lookups)
            },
            
            # Findings summary
            'findings_summary': {
                'total': len(self.findings),
                'critical': len(critical),
                'warning': len(warnings),
                'info': len(info),
                'by_category': self._group_findings_by_category()
            },
            
            # Actual findings
            'findings': [f.to_dict() for f in self.findings],
            
            # Tasks
            'tasks': {
                'total': len(self.tasks),
                'pending': len([t for t in self.tasks if t.status == TaskStatus.PENDING]),
                'items': [t.to_dict() for t in self.tasks]
            },
            
            # Lookups
            'lookups': [l.to_dict() for l in self.lookups],
            
            # NEW: Organizational Metrics
            'organizational_metrics': {
                'total': len(self.metrics),
                'by_category': {
                    cat.value: len([m for m in self.metrics if m.category == cat])
                    for cat in MetricCategory
                },
                'items': [m.to_dict() for m in self.metrics]
            },
            
            # Domain Knowledge (from Domain Decoder)
            'domain_knowledge': domain_knowledge,
            
            # Tier completion
            'tiers_complete': {
                'tier1': self.tier1_complete,
                'tier2': self.tier2_complete,
                'tier3': self.tier3_complete
            }
        }
    
    def _get_relevant_domain_knowledge(self) -> Dict:
        """Get domain knowledge relevant to this project's data."""
        if not DOMAIN_DECODER_AVAILABLE or not decode:
            return {'available': False, 'entries': []}
        
        try:
            decoder = get_decoder()
            relevant_entries = []
            
            # Build text to match against from table names and findings
            search_text_parts = []
            
            # Add table names
            for table in self.tables:
                search_text_parts.append(table.table_name)
            
            # Add finding descriptions
            for finding in self.findings[:20]:  # Limit to avoid too many
                search_text_parts.append(finding.description)
            
            combined_text = ' '.join(search_text_parts)
            
            # Get matches from decoder
            matches = decoder.decode(combined_text)
            
            # Also get knowledge for detected domains
            detected_domains = set(t.domain.value for t in self.tables if t.domain)
            for domain in detected_domains:
                domain_entries = decoder.get_by_domain(domain)
                for entry in domain_entries:
                    if entry not in matches:
                        matches.append(entry)
            
            # Deduplicate and limit
            seen_ids = set()
            for entry in matches[:20]:  # Limit to 20
                if entry.id not in seen_ids:
                    relevant_entries.append(entry.to_dict())
                    seen_ids.add(entry.id)
            
            return {
                'available': True,
                'count': len(relevant_entries),
                'entries': relevant_entries
            }
            
        except Exception as e:
            logger.warning(f"[INTELLIGENCE] Domain knowledge enrichment failed: {e}")
            return {'available': False, 'error': str(e), 'entries': []}
    
    def _group_findings_by_category(self) -> Dict[str, int]:
        """Group findings by category."""
        groups = {}
        for f in self.findings:
            groups[f.category] = groups.get(f.category, 0) + 1
        return groups


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

def get_project_intelligence(project: str, handler=None) -> ProjectIntelligenceService:
    """
    Get intelligence service for a project.
    
    If analysis exists in database, loads it.
    If not, returns empty service (call .analyze() to populate).
    """
    service = ProjectIntelligenceService(project, handler)
    service.load_from_database()
    return service


def get_table_classifications(project: str, handler=None) -> List[TableClassification]:
    """
    Quick access to table classifications for a project.
    
    Usage:
        classifications = get_table_classifications("my_project", handler)
        earnings_tables = [c for c in classifications if c.domain == TableDomain.EARNINGS]
    """
    service = ProjectIntelligenceService(project, handler)
    return service.get_table_classifications()
