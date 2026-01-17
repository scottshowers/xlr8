"""
XLR8 ENGINE BASE CLASSES
========================

Foundation for all 5 engines: Aggregate, Compare, Validate, Detect, Map.

Every engine:
- Takes a config dict
- Returns an EngineResult
- Has full provenance
- Is stateless (no side effects)

Author: XLR8 Team
Version: 1.0.0
Date: January 2026
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timezone
from enum import Enum
import logging
import hashlib
import json

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class EngineType(str, Enum):
    """The five core engine types."""
    AGGREGATE = "aggregate"
    COMPARE = "compare"
    VALIDATE = "validate"
    DETECT = "detect"
    MAP = "map"


class Severity(str, Enum):
    """Severity levels for findings."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ResultStatus(str, Enum):
    """Execution result status."""
    SUCCESS = "success"
    PARTIAL = "partial"  # Some results, but with issues
    FAILURE = "failure"
    NO_DATA = "no_data"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Finding:
    """
    A single finding from an engine execution.
    Used by Validate, Detect engines primarily.
    """
    finding_id: str
    finding_type: str           # duplicate, orphan, validation_failure, etc.
    severity: Severity
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    affected_records: int = 0
    evidence: List[Dict] = field(default_factory=list)  # Sample records
    
    def to_dict(self) -> Dict:
        return {
            "finding_id": self.finding_id,
            "finding_type": self.finding_type,
            "severity": self.severity.value,
            "message": self.message,
            "details": self.details,
            "affected_records": self.affected_records,
            "evidence": self.evidence[:10]  # Limit evidence in output
        }


@dataclass
class Provenance:
    """
    Full audit trail for any engine execution.
    Every result carries this - no exceptions.
    """
    engine_type: EngineType
    engine_version: str
    execution_id: str
    executed_at: str
    project: str
    config_hash: str            # Hash of input config for reproducibility
    duration_ms: int = 0
    source_tables: List[str] = field(default_factory=list)
    sql_executed: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "engine_type": self.engine_type.value,
            "engine_version": self.engine_version,
            "execution_id": self.execution_id,
            "executed_at": self.executed_at,
            "project": self.project,
            "config_hash": self.config_hash,
            "duration_ms": self.duration_ms,
            "source_tables": self.source_tables,
            "sql_executed": self.sql_executed,
            "warnings": self.warnings
        }


@dataclass
class EngineResult:
    """
    Standard result from any engine execution.
    
    All engines return this same structure.
    Consumers don't need to know which engine produced it.
    """
    status: ResultStatus
    data: List[Dict[str, Any]]      # The actual results (rows)
    row_count: int
    columns: List[str]
    provenance: Provenance
    
    # Optional based on engine type
    sql: Optional[str] = None       # Primary SQL that was executed
    findings: List[Finding] = field(default_factory=list)  # For Validate/Detect
    summary: Optional[str] = None   # Human-readable summary
    metadata: Dict[str, Any] = field(default_factory=dict)  # Engine-specific extras
    
    def to_dict(self) -> Dict:
        return {
            "status": self.status.value,
            "data": self.data,
            "row_count": self.row_count,
            "columns": self.columns,
            "provenance": self.provenance.to_dict(),
            "sql": self.sql,
            "findings": [f.to_dict() for f in self.findings],
            "summary": self.summary,
            "metadata": self.metadata
        }
    
    @property
    def success(self) -> bool:
        return self.status == ResultStatus.SUCCESS
    
    @property
    def has_findings(self) -> bool:
        return len(self.findings) > 0


# =============================================================================
# BASE ENGINE CLASS
# =============================================================================

class BaseEngine(ABC):
    """
    Abstract base class for all XLR8 engines.
    
    Subclasses implement:
    - engine_type property
    - engine_version property  
    - _validate_config()
    - _execute()
    
    Base class handles:
    - Config hashing
    - Execution ID generation
    - Timing
    - Error wrapping
    - Provenance assembly
    """
    
    def __init__(self, conn, project: str):
        """
        Initialize engine with DuckDB connection and project.
        
        Args:
            conn: DuckDB connection
            project: Project ID
        """
        self.conn = conn
        self.project = project
        self._start_time: Optional[datetime] = None
    
    @property
    @abstractmethod
    def engine_type(self) -> EngineType:
        """Return the engine type."""
        pass
    
    @property
    @abstractmethod
    def engine_version(self) -> str:
        """Return the engine version string."""
        pass
    
    @abstractmethod
    def _validate_config(self, config: Dict) -> List[str]:
        """
        Validate configuration before execution.
        
        Args:
            config: The configuration dict
            
        Returns:
            List of error messages (empty if valid)
        """
        pass
    
    @abstractmethod
    def _execute(self, config: Dict) -> EngineResult:
        """
        Execute the engine logic.
        
        Args:
            config: Validated configuration
            
        Returns:
            EngineResult with data and provenance
        """
        pass
    
    def execute(self, config: Dict) -> EngineResult:
        """
        Main entry point. Validates config, executes, handles errors.
        
        Args:
            config: Engine configuration
            
        Returns:
            EngineResult (always - even on error)
        """
        self._start_time = datetime.now(timezone.utc)
        execution_id = self._generate_execution_id(config)
        config_hash = self._hash_config(config)
        
        logger.info(f"[{self.engine_type.value.upper()}] Starting execution {execution_id}")
        
        # Validate config
        errors = self._validate_config(config)
        if errors:
            logger.error(f"[{self.engine_type.value.upper()}] Config validation failed: {errors}")
            return self._error_result(
                execution_id=execution_id,
                config_hash=config_hash,
                error=f"Configuration errors: {'; '.join(errors)}"
            )
        
        # Execute
        try:
            result = self._execute(config)
            
            # Ensure provenance is complete
            if result.provenance:
                result.provenance.duration_ms = self._get_duration_ms()
                result.provenance.execution_id = execution_id
                result.provenance.config_hash = config_hash
            
            logger.info(f"[{self.engine_type.value.upper()}] Completed {execution_id}: "
                       f"{result.row_count} rows, status={result.status.value}")
            
            return result
            
        except Exception as e:
            logger.error(f"[{self.engine_type.value.upper()}] Execution failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            return self._error_result(
                execution_id=execution_id,
                config_hash=config_hash,
                error=str(e)
            )
    
    def _generate_execution_id(self, config: Dict) -> str:
        """Generate unique execution ID."""
        timestamp = datetime.now(timezone.utc).isoformat()
        content = f"{self.engine_type.value}:{self.project}:{timestamp}:{json.dumps(config, sort_keys=True)}"
        return hashlib.sha256(content.encode()).hexdigest()[:12]
    
    def _hash_config(self, config: Dict) -> str:
        """Hash config for reproducibility tracking."""
        return hashlib.sha256(
            json.dumps(config, sort_keys=True).encode()
        ).hexdigest()[:16]
    
    def _get_duration_ms(self) -> int:
        """Get execution duration in milliseconds."""
        if self._start_time:
            delta = datetime.now(timezone.utc) - self._start_time
            return int(delta.total_seconds() * 1000)
        return 0
    
    def _create_provenance(self, 
                          execution_id: str,
                          config_hash: str,
                          source_tables: List[str] = None,
                          sql_executed: List[str] = None,
                          warnings: List[str] = None) -> Provenance:
        """Create a Provenance object with current state."""
        return Provenance(
            engine_type=self.engine_type,
            engine_version=self.engine_version,
            execution_id=execution_id,
            executed_at=datetime.now(timezone.utc).isoformat(),
            project=self.project,
            config_hash=config_hash,
            duration_ms=self._get_duration_ms(),
            source_tables=source_tables or [],
            sql_executed=sql_executed or [],
            warnings=warnings or []
        )
    
    def _error_result(self, 
                     execution_id: str,
                     config_hash: str,
                     error: str) -> EngineResult:
        """Create an error result."""
        return EngineResult(
            status=ResultStatus.FAILURE,
            data=[],
            row_count=0,
            columns=[],
            provenance=self._create_provenance(
                execution_id=execution_id,
                config_hash=config_hash,
                warnings=[f"Error: {error}"]
            ),
            summary=f"Execution failed: {error}"
        )
    
    def _query(self, sql: str) -> List[Dict]:
        """Execute SQL and return results as list of dicts."""
        try:
            result = self.conn.execute(sql).fetchdf()
            return result.to_dict('records')
        except Exception as e:
            logger.error(f"[{self.engine_type.value.upper()}] SQL error: {e}")
            logger.error(f"SQL: {sql[:500]}")
            raise


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def generate_finding_id(finding_type: str, context: str) -> str:
    """Generate a unique finding ID."""
    content = f"{finding_type}:{context}:{datetime.now(timezone.utc).isoformat()}"
    return hashlib.sha256(content.encode()).hexdigest()[:10]
