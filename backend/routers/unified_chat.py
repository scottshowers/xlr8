"""
UNIFIED CHAT ROUTER - THE REVOLUTIONARY HEART OF XLR8
======================================================

This is it. The single, unified chat system that transforms XLR8 from 
"a tool that queries data" into "a world-class consultant in a box."

REVOLUTIONARY FEATURES:
-----------------------
1. DATA MODEL INTELLIGENCE
   - Auto-detect reference tables (location codes, dept codes, pay groups)
   - Build lookup dictionaries on upload
   - Transform "LOC001" → "Houston, TX (LOC001)" automatically
   
2. PROACTIVE DATA QUALITY ALERTS
   - Don't just answer - NOTICE things
   - Terminated employees with active status? Flag it.
   - Missing hire dates? Surface it.
   - Duplicate SSNs? Alert immediately.
   
3. SUGGESTED FOLLOW-UPS
   - Guide the conversation like a real consultant
   - "Break this down by department"
   - "Show me the trend over time"
   - "Compare to benchmarks"
   
4. CITATION & AUDIT TRAIL
   - Every claim backed by data
   - Full SQL transparency
   - Source table attribution
   - Defensible findings

ARCHITECTURE:
-------------
┌─────────────────────────────────────────────────────────────┐
│                    POST /api/chat/unified                    │
└─────────────────────────────┬───────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ DataModel    │    │ Intelligence │    │ DataQuality  │
│ Service      │    │ Engine       │    │ Service      │
│ (Lookups)    │    │ (Core Logic) │    │ (Alerts)     │
└──────────────┘    └──────────────┘    └──────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
                    ┌──────────────────┐
                    │ Citation Builder │
                    │ + Follow-up Gen  │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ PII Redaction    │
                    │ (if Claude call) │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ RESPONSE         │
                    │ Revolutionary.   │
                    └──────────────────┘

DEPLOYMENT:
-----------
1. Copy to backend/routers/unified_chat.py
2. Add to main.py:
   from routers import unified_chat
   app.include_router(unified_chat.router, prefix="/api")
3. Update frontend to call /api/chat/unified

Author: XLR8 Team
Version: 1.1.0 - Phase 3.5 Intelligence Consumer
Date: December 2025
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, List, Optional, Any, Tuple
import logging
import uuid
import json
import re
import time
import io
import traceback

logger = logging.getLogger(__name__)

router = APIRouter(tags=["unified-chat"])


# =============================================================================
# IMPORTS - Graceful degradation for all dependencies
# =============================================================================

# Intelligence Engine
try:
    from utils.intelligence_engine import IntelligenceEngine, IntelligenceMode
    INTELLIGENCE_AVAILABLE = True
except ImportError:
    try:
        from backend.utils.intelligence_engine import IntelligenceEngine, IntelligenceMode
        INTELLIGENCE_AVAILABLE = True
    except ImportError:
        INTELLIGENCE_AVAILABLE = False
        logger.warning("[UNIFIED] Intelligence engine not available")

# Learning Module
try:
    from utils.learning import get_learning_module
    LEARNING_AVAILABLE = True
except ImportError:
    try:
        from backend.utils.learning import get_learning_module
        LEARNING_AVAILABLE = True
    except ImportError:
        LEARNING_AVAILABLE = False
        logger.warning("[UNIFIED] Learning module not available")

# Structured Data Handler
try:
    from utils.structured_data_handler import get_structured_handler
    STRUCTURED_AVAILABLE = True
except ImportError:
    try:
        from backend.utils.structured_data_handler import get_structured_handler
        STRUCTURED_AVAILABLE = True
    except ImportError:
        STRUCTURED_AVAILABLE = False
        logger.warning("[UNIFIED] Structured data handler not available")

# RAG Handler
try:
    from utils.rag_handler import RAGHandler
    RAG_AVAILABLE = True
except ImportError:
    try:
        from backend.utils.rag_handler import RAGHandler
        RAG_AVAILABLE = True
    except ImportError:
        RAG_AVAILABLE = False
        logger.warning("[UNIFIED] RAG handler not available")

# LLM Orchestrator
try:
    from utils.llm_orchestrator import LLMOrchestrator
    LLM_AVAILABLE = True
except ImportError:
    try:
        from backend.utils.llm_orchestrator import LLMOrchestrator
        LLM_AVAILABLE = True
    except ImportError:
        LLM_AVAILABLE = False
        logger.warning("[UNIFIED] LLM orchestrator not available")

# Persona Manager
try:
    from utils.persona_manager import get_persona_manager
    PERSONAS_AVAILABLE = True
except ImportError:
    try:
        from backend.utils.persona_manager import get_persona_manager
        PERSONAS_AVAILABLE = True
    except ImportError:
        PERSONAS_AVAILABLE = False
        logger.warning("[UNIFIED] Persona manager not available")

# Supabase
try:
    from utils.database.supabase_client import get_supabase
    SUPABASE_AVAILABLE = True
except ImportError:
    try:
        from backend.utils.database.supabase_client import get_supabase
        SUPABASE_AVAILABLE = True
    except ImportError:
        SUPABASE_AVAILABLE = False
        logger.warning("[UNIFIED] Supabase not available")

# Project Intelligence Service (Phase 3)
try:
    from backend.utils.project_intelligence import ProjectIntelligenceService, get_project_intelligence
    PROJECT_INTELLIGENCE_AVAILABLE = True
    logger.warning("[UNIFIED] Project intelligence imported successfully")
except ImportError:
    try:
        from utils.project_intelligence import ProjectIntelligenceService, get_project_intelligence
        PROJECT_INTELLIGENCE_AVAILABLE = True
        logger.warning("[UNIFIED] Project intelligence imported successfully (alt path)")
    except ImportError:
        PROJECT_INTELLIGENCE_AVAILABLE = False
        logger.warning("[UNIFIED] Project intelligence not available - using fallback services")


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class UnifiedChatRequest(BaseModel):
    """
    Unified chat request - supports all chat modes.
    
    Attributes:
        message: The user's question or command
        project: Project identifier (e.g., "TEA1000")
        persona: Persona to use for response style (default: "bessie")
        scope: Data scope - "project", "global", or "all"
        mode: Force specific intelligence mode (optional)
        clarifications: Answers to clarification questions
        session_id: Session ID for conversation continuity
        include_quality_alerts: Whether to run data quality checks
        include_follow_ups: Whether to suggest follow-up questions
        include_citations: Whether to include full audit trail
    """
    message: str
    project: Optional[str] = None
    persona: Optional[str] = 'bessie'
    scope: Optional[str] = 'project'
    mode: Optional[str] = None
    clarifications: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    
    # Revolutionary feature flags
    include_quality_alerts: Optional[bool] = True
    include_follow_ups: Optional[bool] = True
    include_citations: Optional[bool] = True


class ClarificationAnswer(BaseModel):
    """User's answers to clarification questions."""
    session_id: str
    original_question: str
    answers: Dict[str, Any]


class FeedbackRequest(BaseModel):
    """Feedback on chat response."""
    job_id: Optional[str] = None
    session_id: Optional[str] = None
    feedback: str  # 'up' or 'down'
    message: Optional[str] = None
    response: Optional[str] = None
    correction: Optional[str] = None


class ResetPreferencesRequest(BaseModel):
    """Request to reset user preferences."""
    session_id: Optional[str] = None
    project: Optional[str] = None
    reset_type: str = "session"  # "session" or "learned"


class ExportRequest(BaseModel):
    """Request to export data to Excel."""
    query: str
    project: Optional[str] = None
    tables: Optional[List[str]] = None
    include_summary: Optional[bool] = True
    include_quality_report: Optional[bool] = True


# =============================================================================
# CORE SERVICE: REVERSIBLE PII REDACTION
# =============================================================================

class ReversibleRedactor:
    """
    Reversible PII redaction - PII NEVER goes to Claude.
    
    We redact before sending to any external LLM, then restore after.
    This allows us to work with sensitive data without compromising privacy.
    
    Supported PII types:
    - SSN (Social Security Numbers)
    - Bank account/routing numbers
    - Salary/compensation values
    - Phone numbers
    - Email addresses
    """
    
    def __init__(self):
        self.mappings: Dict[str, str] = {}  # {placeholder: original_value}
        self.counters = {
            'ssn': 0, 
            'salary': 0, 
            'phone': 0, 
            'email': 0, 
            'name': 0, 
            'account': 0,
            'dob': 0
        }
    
    def _get_placeholder(self, pii_type: str) -> str:
        """Generate unique placeholder for PII type."""
        self.counters[pii_type] += 1
        return f"[{pii_type.upper()}_{self.counters[pii_type]:03d}]"
    
    def redact(self, text: str) -> str:
        """
        Redact PII with reversible placeholders.
        
        Args:
            text: Text potentially containing PII
            
        Returns:
            Text with PII replaced by placeholders
        """
        if not text:
            return text
        
        result = text
        
        # SSN: 123-45-6789
        for match in re.finditer(r'\b(\d{3}-\d{2}-\d{4})\b', result):
            original = match.group(1)
            if original not in self.mappings.values():
                placeholder = self._get_placeholder('ssn')
                self.mappings[placeholder] = original
                result = result.replace(original, placeholder)
        
        # Bank account / routing numbers (8-17 digits)
        for match in re.finditer(r'\b(\d{8,17})\b', result):
            original = match.group(1)
            # Skip if already mapped or looks like a year/date
            if original not in self.mappings.values() and not original.startswith('20'):
                placeholder = self._get_placeholder('account')
                self.mappings[placeholder] = original
                result = result.replace(original, placeholder)
        
        # Salary: $75,000 or $75,000.00
        for match in re.finditer(r'(\$\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', result):
            original = match.group(1)
            if original not in self.mappings.values():
                placeholder = self._get_placeholder('salary')
                self.mappings[placeholder] = original
                result = result.replace(original, placeholder)
        
        # Phone: (123) 456-7890 or 123-456-7890
        for match in re.finditer(r'(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})\b', result):
            original = match.group(1)
            # Skip if it looks like SSN
            if original.count('-') == 2 and len(original.replace('-', '')) == 9:
                continue
            if original not in self.mappings.values():
                placeholder = self._get_placeholder('phone')
                self.mappings[placeholder] = original
                result = result.replace(original, placeholder)
        
        # Email
        for match in re.finditer(r'\b([\w\.-]+@[\w\.-]+\.\w{2,})\b', result):
            original = match.group(1)
            if original not in self.mappings.values():
                placeholder = self._get_placeholder('email')
                self.mappings[placeholder] = original
                result = result.replace(original, placeholder)
        
        # Date of birth patterns: MM/DD/YYYY, YYYY-MM-DD
        for match in re.finditer(r'\b(\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2})\b', result):
            original = match.group(1)
            if original not in self.mappings.values():
                placeholder = self._get_placeholder('dob')
                self.mappings[placeholder] = original
                result = result.replace(original, placeholder)
        
        return result
    
    def restore(self, text: str) -> str:
        """
        Restore original PII values from placeholders.
        
        Args:
            text: Text with placeholders
            
        Returns:
            Text with original PII restored
        """
        if not text or not self.mappings:
            return text
        
        result = text
        for placeholder, original in self.mappings.items():
            result = result.replace(placeholder, original)
        
        return result
    
    def has_pii(self) -> bool:
        """Check if any PII was redacted."""
        return len(self.mappings) > 0
    
    def get_stats(self) -> Dict[str, int]:
        """Get redaction statistics."""
        return {
            'total_redacted': len(self.mappings),
            **{k: v for k, v in self.counters.items() if v > 0}
        }


# =============================================================================
# CORE SERVICE: DATA MODEL INTELLIGENCE
# =============================================================================

class DataModelService:
    """
    Data Model Intelligence Service - Transform codes into human-readable values.
    
    This service:
    1. Auto-detects reference/lookup tables
    2. Builds code → description dictionaries
    3. Enriches query results with human-readable values
    
    Example:
        Input:  "847 employees have location_code = 'LOC001'"
        Output: "847 employees in Houston, TX (LOC001)"
    """
    
    # Patterns that indicate a reference/lookup table
    REFERENCE_TABLE_PATTERNS = [
        r'.*_codes?$',           # location_codes, pay_codes
        r'.*_types?$',           # employee_types, deduction_types
        r'.*_lookup$',           # department_lookup
        r'.*_ref$',              # status_ref
        r'.*_master$',           # Only if small row count
        r'^ref_.*',              # ref_locations
        r'^lkp_.*',              # lkp_departments
        r'^code_.*',             # code_earnings
    ]
    
    # Common code → description column mappings
    CODE_DESCRIPTION_PATTERNS = [
        ('code', 'description'),
        ('code', 'name'),
        ('id', 'description'),
        ('id', 'name'),
        ('key', 'value'),
        ('abbreviation', 'full_name'),
        ('short_name', 'long_name'),
        ('location_code', 'location_name'),
        ('dept_code', 'dept_name'),
        ('company_code', 'company_name'),
    ]
    
    def __init__(self, project: str):
        self.project = project
        self.lookups: Dict[str, Dict[str, str]] = {}  # table_name -> {code: description}
        self.code_columns: Dict[str, str] = {}  # column_name -> lookup_table
        self._loaded = False
    
    def load_lookups(self, handler) -> None:
        """
        Load lookup dictionaries - tries intelligence service first, falls back to scanning.
        
        Phase 3.5: Consumes pre-computed lookups from ProjectIntelligenceService
        when available, avoiding redundant table scanning.
        
        Args:
            handler: DuckDB structured data handler
        """
        logger.warning(f"[DATA_MODEL] load_lookups called for {self.project}, _loaded={self._loaded}")
        
        if self._loaded:
            return
        
        # PHASE 3.5: Try intelligence service first (pre-computed on upload)
        if PROJECT_INTELLIGENCE_AVAILABLE and handler:
            try:
                logger.warning(f"[DATA_MODEL] Attempting to load from intelligence service for {self.project}")
                intelligence = get_project_intelligence(self.project, handler)
                if intelligence and intelligence.lookups:
                    logger.warning(f"[DATA_MODEL] Found {len(intelligence.lookups)} lookups in intelligence")
                    # Pull from pre-computed lookups
                    for lookup in intelligence.lookups:
                        table_name = lookup.table_name
                        code_col = lookup.code_column
                        desc_col = lookup.description_column
                        mappings = lookup.lookup_data  # Note: attribute is lookup_data, not mappings
                        
                        if mappings:
                            self.lookups[table_name] = mappings
                            self.code_columns[code_col] = table_name
                    
                    self._loaded = True
                    logger.warning(f"[DATA_MODEL] Loaded {len(self.lookups)} lookup tables from intelligence service")
                    return
                else:
                    logger.warning(f"[DATA_MODEL] No lookups found in intelligence, falling back to scan")
            except Exception as e:
                logger.warning(f"[DATA_MODEL] Intelligence service unavailable, falling back: {e}")
        
        # FALLBACK: Scan tables directly (original behavior)
        if not handler or not handler.conn:
            return
        
        try:
            # Get all tables for project
            all_tables = handler.conn.execute("SHOW TABLES").fetchall()
            project_prefix = (self.project or '').lower().replace(' ', '_').replace('-', '_')
            
            for (table_name,) in all_tables:
                # Skip system tables
                if table_name.startswith('_'):
                    continue
                
                # Check if matches project
                if project_prefix and not table_name.lower().startswith(project_prefix.lower()):
                    continue
                
                # Check if looks like a reference table
                table_lower = table_name.lower()
                is_reference = any(re.match(pattern, table_lower) for pattern in self.REFERENCE_TABLE_PATTERNS)
                
                if not is_reference:
                    # Also check row count - reference tables are usually small
                    try:
                        count = handler.conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]
                        if count <= 500:  # Small table might be a lookup
                            is_reference = True
                    except:
                        pass
                
                if is_reference:
                    self._load_lookup_table(handler, table_name)
            
            self._loaded = True
            logger.info(f"[DATA_MODEL] Loaded {len(self.lookups)} lookup tables for {self.project}")
            
        except Exception as e:
            logger.warning(f"[DATA_MODEL] Failed to load lookups: {e}")
    
    def _load_lookup_table(self, handler, table_name: str) -> None:
        """Load a single lookup table into memory."""
        try:
            # Get columns
            cols = handler.conn.execute(f'DESCRIBE "{table_name}"').fetchall()
            col_names = [c[0].lower() for c in cols]
            
            # Find code and description columns
            code_col = None
            desc_col = None
            
            for code_pattern, desc_pattern in self.CODE_DESCRIPTION_PATTERNS:
                for col in col_names:
                    if code_pattern in col and not code_col:
                        code_col = col
                    if desc_pattern in col and not desc_col:
                        desc_col = col
                
                if code_col and desc_col:
                    break
            
            # Fallback: first column is code, second is description
            if not code_col and len(col_names) >= 2:
                code_col = col_names[0]
                desc_col = col_names[1]
            
            if code_col and desc_col:
                # Load the lookup data
                rows = handler.conn.execute(f'''
                    SELECT "{code_col}", "{desc_col}" 
                    FROM "{table_name}" 
                    WHERE "{code_col}" IS NOT NULL
                    LIMIT 1000
                ''').fetchall()
                
                lookup = {str(row[0]): str(row[1]) for row in rows if row[0] and row[1]}
                
                if lookup:
                    self.lookups[table_name] = lookup
                    # Also map the code column to this lookup
                    self.code_columns[code_col] = table_name
                    logger.debug(f"[DATA_MODEL] Loaded {len(lookup)} values from {table_name}")
                    
        except Exception as e:
            logger.warning(f"[DATA_MODEL] Could not load {table_name}: {e}")
    
    def enrich_value(self, column: str, value: str) -> str:
        """
        Enrich a code value with its description.
        
        Args:
            column: Column name (e.g., "location_code")
            value: Code value (e.g., "LOC001")
            
        Returns:
            Enriched value (e.g., "Houston, TX (LOC001)")
        """
        if not value:
            return value
        
        col_lower = column.lower()
        
        # Check if we have a lookup for this column
        for code_col, table_name in self.code_columns.items():
            if code_col in col_lower:
                lookup = self.lookups.get(table_name, {})
                description = lookup.get(str(value))
                if description:
                    return f"{description} ({value})"
        
        return value
    
    def enrich_results(self, rows: List[Dict], columns: List[str]) -> List[Dict]:
        """
        Enrich all values in a result set.
        
        Args:
            rows: List of result dictionaries
            columns: Column names
            
        Returns:
            Rows with enriched values
        """
        if not rows or not self.lookups:
            return rows
        
        enriched = []
        for row in rows:
            enriched_row = {}
            for col, val in row.items():
                enriched_row[col] = self.enrich_value(col, str(val) if val else '')
            enriched.append(enriched_row)
        
        return enriched
    
    def get_description(self, table: str, code: str) -> Optional[str]:
        """Get description for a specific code from a specific table."""
        lookup = self.lookups.get(table, {})
        return lookup.get(str(code))


# =============================================================================
# CORE SERVICE: DATA QUALITY ALERTS
# =============================================================================

class DataQualityService:
    """
    Proactive Data Quality Alerts - Don't just answer, NOTICE things.
    
    A world-class consultant doesn't just answer the question asked.
    They notice data quality issues and surface them proactively.
    
    Alert Categories:
    - INTEGRITY: Data consistency issues (status mismatches, orphan records)
    - COMPLETENESS: Missing data (null hire dates, empty required fields)
    - DUPLICATES: Duplicate key values (SSN, employee ID)
    - ANOMALIES: Statistical outliers (negative salaries, future dates)
    """
    
    # Quality checks to run
    QUALITY_CHECKS = [
        {
            'id': 'status_mismatch',
            'name': 'Status/Date Mismatch',
            'description': 'Employees with termination date but active status',
            'category': 'INTEGRITY',
            'severity': 'warning',
            'sql_template': '''
                SELECT COUNT(*) as count
                FROM "{table}"
                WHERE {status_col} = 'A' 
                AND {term_date_col} IS NOT NULL 
                AND {term_date_col} != ''
            ''',
            'required_columns': ['status', 'termination_date']
        },
        {
            'id': 'missing_hire_date',
            'name': 'Missing Hire Dates',
            'description': 'Records missing hire date',
            'category': 'COMPLETENESS',
            'severity': 'info',
            'sql_template': '''
                SELECT COUNT(*) as count,
                       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM "{table}"), 1) as pct
                FROM "{table}"
                WHERE {hire_date_col} IS NULL OR {hire_date_col} = ''
            ''',
            'required_columns': ['hire_date']
        },
        {
            'id': 'duplicate_ssn',
            'name': 'Duplicate SSN',
            'description': 'Multiple records with same SSN',
            'category': 'DUPLICATES',
            'severity': 'critical',
            'sql_template': '''
                SELECT COUNT(*) as count
                FROM (
                    SELECT {ssn_col}, COUNT(*) as cnt
                    FROM "{table}"
                    WHERE {ssn_col} IS NOT NULL AND {ssn_col} != ''
                    GROUP BY {ssn_col}
                    HAVING COUNT(*) > 1
                )
            ''',
            'required_columns': ['ssn']
        },
        {
            'id': 'duplicate_employee_id',
            'name': 'Duplicate Employee ID',
            'description': 'Multiple records with same Employee ID',
            'category': 'DUPLICATES',
            'severity': 'critical',
            'sql_template': '''
                SELECT COUNT(*) as count
                FROM (
                    SELECT {emp_id_col}, COUNT(*) as cnt
                    FROM "{table}"
                    WHERE {emp_id_col} IS NOT NULL AND {emp_id_col} != ''
                    GROUP BY {emp_id_col}
                    HAVING COUNT(*) > 1
                )
            ''',
            'required_columns': ['employee_id']
        },
        {
            'id': 'future_hire_date',
            'name': 'Future Hire Dates',
            'description': 'Hire dates in the future',
            'category': 'ANOMALIES',
            'severity': 'warning',
            'sql_template': '''
                SELECT COUNT(*) as count
                FROM "{table}"
                WHERE TRY_CAST({hire_date_col} AS DATE) > CURRENT_DATE
            ''',
            'required_columns': ['hire_date']
        },
        {
            'id': 'negative_pay',
            'name': 'Negative Pay Rates',
            'description': 'Negative hourly or salary values',
            'category': 'ANOMALIES',
            'severity': 'critical',
            'sql_template': '''
                SELECT COUNT(*) as count
                FROM "{table}"
                WHERE TRY_CAST({pay_col} AS DOUBLE) < 0
            ''',
            'required_columns': ['pay_rate']
        }
    ]
    
    # Column name mappings (what we look for → what it might be called)
    COLUMN_MAPPINGS = {
        'status': ['employment_status', 'emp_status', 'status', 'employee_status', 'active_flag'],
        'termination_date': ['termination_date', 'term_date', 'termdate', 'end_date', 'separation_date'],
        'hire_date': ['hire_date', 'hiredate', 'start_date', 'original_hire_date', 'employment_date'],
        'ssn': ['ssn', 'social_security', 'social_security_number', 'ss_number'],
        'employee_id': ['employee_id', 'emp_id', 'empid', 'employee_number', 'ee_id', 'emplid'],
        'pay_rate': ['hourly_rate', 'pay_rate', 'salary', 'annual_salary', 'hourly_pay_rate', 'compensation']
    }
    
    def __init__(self, project: str):
        self.project = project
        self.alerts: List[Dict] = []
    
    def _find_column(self, columns: List[str], column_type: str) -> Optional[str]:
        """Find matching column name for a column type."""
        patterns = self.COLUMN_MAPPINGS.get(column_type, [])
        columns_lower = [c.lower() for c in columns]
        
        for pattern in patterns:
            for i, col_lower in enumerate(columns_lower):
                if pattern in col_lower:
                    return columns[i]  # Return original case
        
        return None
    
    def run_checks(self, handler, tables: List[Dict]) -> List[Dict]:
        """
        Get quality alerts - tries intelligence service first, falls back to SQL checks.
        
        Phase 3.5: Consumes pre-computed findings from ProjectIntelligenceService
        when available, avoiding redundant SQL execution.
        
        Args:
            handler: DuckDB handler
            tables: List of table info dicts with 'table_name' and 'columns'
            
        Returns:
            List of alert dicts
        """
        self.alerts = []
        
        # PHASE 3.5: Try intelligence service first (pre-computed on upload)
        if PROJECT_INTELLIGENCE_AVAILABLE and handler:
            try:
                logger.warning(f"[DATA_QUALITY] Attempting to load from intelligence service for {self.project}")
                intelligence = get_project_intelligence(self.project, handler)
                if intelligence and intelligence.findings:
                    logger.warning(f"[DATA_QUALITY] Found {len(intelligence.findings)} findings in intelligence")
                    # Convert intelligence findings to alert format
                    for finding in intelligence.findings:
                        alert = {
                            'id': finding.finding_type,
                            'name': finding.title,
                            'category': finding.category,
                            'severity': finding.severity,
                            'table': finding.table_name.split('__')[-1] if finding.table_name else '',
                            'count': finding.affected_count,
                            'percentage': finding.affected_percentage,
                            'description': finding.description,
                            'details': f"{finding.affected_count:,} records affected" if finding.affected_count else finding.description,
                            'evidence_sql': finding.evidence_sql
                        }
                        self.alerts.append(alert)
                    
                    # Sort by severity
                    severity_order = {'critical': 0, 'warning': 1, 'info': 2}
                    self.alerts.sort(key=lambda x: severity_order.get(x.get('severity', 'info'), 3))
                    
                    logger.warning(f"[DATA_QUALITY] Loaded {len(self.alerts)} alerts from intelligence service")
                    return self.alerts
                else:
                    logger.warning(f"[DATA_QUALITY] No findings in intelligence, falling back to SQL checks")
            except Exception as e:
                logger.warning(f"[DATA_QUALITY] Intelligence service unavailable, falling back: {e}")
        
        # FALLBACK: Run SQL checks directly (original behavior)
        if not handler or not handler.conn:
            return self.alerts
        
        for table_info in tables:
            table_name = table_info.get('table_name', '')
            columns = table_info.get('columns', [])
            
            if not columns:
                continue
            
            for check in self.QUALITY_CHECKS:
                self._run_check(handler, table_name, columns, check)
        
        # Sort by severity
        severity_order = {'critical': 0, 'warning': 1, 'info': 2}
        self.alerts.sort(key=lambda x: severity_order.get(x.get('severity', 'info'), 3))
        
        return self.alerts
    
    def _run_check(self, handler, table_name: str, columns: List[str], check: Dict) -> None:
        """Run a single quality check."""
        try:
            # Find required columns
            col_mappings = {}
            for required_col in check['required_columns']:
                found_col = self._find_column(columns, required_col)
                if not found_col:
                    return  # Skip if required column not found
                col_mappings[f'{required_col}_col'] = found_col
            
            # Build SQL
            sql = check['sql_template'].format(
                table=table_name,
                **col_mappings
            )
            
            # Execute
            result = handler.conn.execute(sql).fetchone()
            
            if result and result[0]:
                count = result[0]
                pct = result[1] if len(result) > 1 else None
                
                if count > 0:
                    alert = {
                        'id': check['id'],
                        'name': check['name'],
                        'category': check['category'],
                        'severity': check['severity'],
                        'table': table_name.split('__')[-1],  # Remove project prefix
                        'count': count,
                        'percentage': pct,
                        'description': check['description'],
                        'details': f"{count:,} records affected" + (f" ({pct}%)" if pct else "")
                    }
                    self.alerts.append(alert)
                    
        except Exception as e:
            logger.debug(f"[DATA_QUALITY] Check {check['id']} failed on {table_name}: {e}")
    
    def get_summary(self) -> Dict:
        """Get summary of all alerts."""
        if not self.alerts:
            return {'status': 'clean', 'message': '✅ No data quality issues detected'}
        
        critical = len([a for a in self.alerts if a['severity'] == 'critical'])
        warning = len([a for a in self.alerts if a['severity'] == 'warning'])
        info = len([a for a in self.alerts if a['severity'] == 'info'])
        
        if critical > 0:
            status = 'critical'
            emoji = '🚨'
        elif warning > 0:
            status = 'warning'
            emoji = '⚠️'
        else:
            status = 'info'
            emoji = 'ℹ️'
        
        return {
            'status': status,
            'message': f"{emoji} {len(self.alerts)} data quality issue(s) detected",
            'critical': critical,
            'warning': warning,
            'info': info,
            'alerts': self.alerts
        }


# =============================================================================
# CORE SERVICE: SUGGESTED FOLLOW-UPS
# =============================================================================

class FollowUpGenerator:
    """
    Suggested Follow-Up Generator - Guide the conversation like a consultant.
    
    After answering a question, suggest relevant follow-up questions
    to help the user dig deeper into their data.
    """
    
    # Follow-up templates based on query type
    FOLLOW_UP_TEMPLATES = {
        'count': [
            "Break this down by {dimension}",
            "How has this changed over the last {time_period}?",
            "Which {entity} has the most?",
            "Compare this to {benchmark}",
        ],
        'list': [
            "Filter this to show only {filter_value}",
            "Sort by {sort_column}",
            "Show me more details about {entity}",
            "Export this to Excel",
        ],
        'sum': [
            "What's the average instead?",
            "Break this down by {dimension}",
            "Show the top 10 contributors",
            "How does this compare to budget?",
        ],
        'analysis': [
            "What's driving this trend?",
            "Are there any outliers?",
            "How does this compare to industry benchmarks?",
            "What actions should we take based on this?",
        ],
        'general': [
            "Tell me more about {entity}",
            "What else should I know about this?",
            "Are there any related issues?",
            "Show me the underlying data",
        ]
    }
    
    # Common dimensions for breakdowns
    COMMON_DIMENSIONS = [
        'department', 'location', 'company', 'pay_group', 
        'job_title', 'employment_type', 'hire_year'
    ]
    
    def __init__(self, schema: Dict = None):
        self.schema = schema or {}
        self.available_columns = self._extract_columns()
    
    def _extract_columns(self) -> List[str]:
        """Extract all available column names from schema."""
        columns = []
        for table in self.schema.get('tables', []):
            columns.extend(table.get('columns', []))
        return list(set(columns))
    
    def generate(
        self, 
        query_type: str, 
        question: str, 
        result: Dict,
        context: Dict = None
    ) -> List[str]:
        """
        Generate suggested follow-up questions.
        
        Args:
            query_type: Type of query (count, list, sum, analysis, general)
            question: Original question asked
            result: Query result
            context: Additional context
            
        Returns:
            List of suggested follow-up questions
        """
        suggestions = []
        context = context or {}
        
        # Get templates for this query type
        templates = self.FOLLOW_UP_TEMPLATES.get(query_type, self.FOLLOW_UP_TEMPLATES['general'])
        
        # Find relevant dimensions from schema
        available_dimensions = []
        for dim in self.COMMON_DIMENSIONS:
            if any(dim in col.lower() for col in self.available_columns):
                available_dimensions.append(dim.replace('_', ' ').title())
        
        # Generate suggestions
        for template in templates[:4]:  # Max 4 suggestions
            suggestion = template
            
            # Fill in placeholders
            if '{dimension}' in suggestion and available_dimensions:
                suggestion = suggestion.replace('{dimension}', available_dimensions[0])
            elif '{dimension}' in suggestion:
                suggestion = suggestion.replace('{dimension}', 'department')
            
            if '{time_period}' in suggestion:
                suggestion = suggestion.replace('{time_period}', '12 months')
            
            if '{entity}' in suggestion:
                # Try to extract entity from question
                entity = self._extract_entity(question)
                suggestion = suggestion.replace('{entity}', entity)
            
            if '{filter_value}' in suggestion:
                suggestion = suggestion.replace('{filter_value}', 'active employees')
            
            if '{sort_column}' in suggestion:
                suggestion = suggestion.replace('{sort_column}', 'hire date')
            
            if '{benchmark}' in suggestion:
                suggestion = suggestion.replace('{benchmark}', 'last year')
            
            suggestions.append(suggestion)
        
        # Add context-specific suggestions
        if query_type == 'count' and result.get('count', 0) > 100:
            suggestions.append("Show me the top 10 by count")
        
        if 'employee' in question.lower():
            if 'terminated' not in question.lower():
                suggestions.append("Include terminated employees")
            if 'active' not in question.lower():
                suggestions.append("Filter to active employees only")
        
        return suggestions[:5]  # Return max 5 suggestions
    
    def _extract_entity(self, question: str) -> str:
        """Extract the main entity from a question."""
        # Simple extraction - look for common nouns
        entities = ['employees', 'departments', 'locations', 'companies', 'earnings', 'deductions']
        
        question_lower = question.lower()
        for entity in entities:
            if entity in question_lower:
                return entity
        
        return 'this'


# =============================================================================
# CORE SERVICE: CITATION BUILDER
# =============================================================================

class CitationBuilder:
    """
    Citation & Audit Trail Builder - Every claim backed by data.
    
    Consultants need to defend their findings. This makes every
    answer bulletproof with full source attribution and SQL transparency.
    """
    
    def __init__(self):
        self.citations: List[Dict] = []
        self.sql_executed: List[str] = []
    
    def add_citation(
        self,
        claim: str,
        source_table: str,
        source_column: Optional[str] = None,
        sql: Optional[str] = None,
        row_count: Optional[int] = None,
        confidence: float = 1.0
    ) -> None:
        """
        Add a citation for a claim.
        
        Args:
            claim: The claim being made
            source_table: Source table name
            source_column: Relevant column(s)
            sql: SQL query executed
            row_count: Number of rows supporting claim
            confidence: Confidence level (0-1)
        """
        citation = {
            'claim': claim,
            'source_table': source_table.split('__')[-1] if '__' in source_table else source_table,
            'full_table': source_table,
            'source_column': source_column,
            'sql': sql,
            'row_count': row_count,
            'confidence': confidence,
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self.citations.append(citation)
        
        if sql and sql not in self.sql_executed:
            self.sql_executed.append(sql)
    
    def build_audit_trail(self) -> Dict:
        """Build complete audit trail."""
        return {
            'citations': self.citations,
            'sql_queries': self.sql_executed,
            'total_sources': len(set(c['full_table'] for c in self.citations)),
            'generated_at': time.strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def format_for_display(self) -> str:
        """Format citations for display in response."""
        if not self.citations:
            return ""
        
        lines = ["\n---", "📍 **Sources & Audit Trail**"]
        
        for i, citation in enumerate(self.citations, 1):
            source_info = f"• {citation['source_table']}"
            if citation['source_column']:
                source_info += f" → {citation['source_column']}"
            if citation['row_count']:
                source_info += f" ({citation['row_count']:,} rows)"
            lines.append(source_info)
        
        if self.sql_executed:
            lines.append("\n*SQL Executed:*")
            for sql in self.sql_executed[:3]:  # Show max 3
                # Truncate long SQL
                sql_display = sql[:200] + '...' if len(sql) > 200 else sql
                lines.append(f"```sql\n{sql_display}\n```")
        
        return "\n".join(lines)


# =============================================================================
# SESSION MANAGEMENT
# =============================================================================

# In-memory session storage (in production, use Redis)
unified_sessions: Dict[str, Dict] = {}


def get_or_create_session(session_id: str, project: str) -> Tuple[str, Dict]:
    """Get existing session or create new one."""
    if not session_id:
        session_id = f"session_{uuid.uuid4().hex[:8]}"
    
    if session_id not in unified_sessions:
        unified_sessions[session_id] = {
            'engine': None,
            'project': project,
            'created_at': time.time(),
            'last_sql': None,
            'last_result': None,
            'last_question': None,
            'skip_learning': False,
            'data_model': None,
            'conversation_history': []
        }
    
    return session_id, unified_sessions[session_id]


def cleanup_old_sessions(max_sessions: int = 100) -> None:
    """Remove oldest sessions if over limit."""
    if len(unified_sessions) > max_sessions:
        # Sort by created_at and remove oldest
        sorted_sessions = sorted(
            unified_sessions.items(),
            key=lambda x: x[1].get('created_at', 0)
        )
        for session_id, _ in sorted_sessions[:len(sorted_sessions) - max_sessions]:
            del unified_sessions[session_id]


# =============================================================================
# SCHEMA RETRIEVAL
# =============================================================================

async def get_project_schema(project: str, scope: str, handler) -> Dict:
    """
    Get comprehensive schema for project including column profiles.
    
    This is the foundation for intelligent clarification - we need to know
    what's in the data before we can ask smart questions.
    """
    tables = []
    filter_candidates = {}
    
    if not handler or not handler.conn:
        logger.error("[SCHEMA] No handler connection")
        return {'tables': [], 'filter_candidates': {}}
    
    try:
        # Get all tables directly from DuckDB
        all_tables = handler.conn.execute("SHOW TABLES").fetchall()
        logger.info(f"[SCHEMA] DuckDB has {len(all_tables)} total tables")
        
        # Build project prefix for filtering
        project_clean = (project or '').strip()
        project_prefixes = [
            project_clean.lower(),
            project_clean.lower().replace(' ', '_'),
            project_clean.lower().replace(' ', '_').replace('-', '_'),
            project_clean.upper(),
            project_clean,
        ]
        
        matched_tables = []
        all_valid_tables = []
        
        for (table_name,) in all_tables:
            if table_name.startswith('_'):
                continue
            
            all_valid_tables.append(table_name)
            
            table_lower = table_name.lower()
            matches_project = any(
                table_lower.startswith(prefix.lower()) 
                for prefix in project_prefixes if prefix
            )
            
            if matches_project:
                matched_tables.append(table_name)
        
        tables_to_process = matched_tables if matched_tables else all_valid_tables
        
        if not matched_tables and all_valid_tables:
            logger.warning(f"[SCHEMA] No tables match project '{project}', using all tables")
        
        for table_name in tables_to_process:
            try:
                # Get columns
                columns = []
                try:
                    col_result = handler.conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
                    columns = [row[1] for row in col_result]
                except:
                    try:
                        col_result = handler.conn.execute(f'DESCRIBE "{table_name}"').fetchall()
                        columns = [row[0] for row in col_result]
                    except:
                        result = handler.conn.execute(f'SELECT * FROM "{table_name}" LIMIT 0')
                        columns = [desc[0] for desc in result.description]
                
                if not columns:
                    continue
                
                # Get row count
                try:
                    count_result = handler.conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()
                    row_count = count_result[0] if count_result else 0
                except:
                    row_count = 0
                
                # Get column profiles (Phase 2: Data-driven clarification)
                categorical_columns = []
                column_profiles = {}
                
                try:
                    profile_result = handler.conn.execute("""
                        SELECT column_name, inferred_type, distinct_count, 
                               distinct_values, value_distribution, is_categorical,
                               min_value, max_value, filter_category
                        FROM _column_profiles 
                        WHERE table_name = ?
                    """, [table_name]).fetchall()
                    
                    for prow in profile_result:
                        col_name = prow[0]
                        profile = {
                            'inferred_type': prow[1],
                            'distinct_count': prow[2],
                            'is_categorical': prow[5],
                            'filter_category': prow[8]
                        }
                        
                        if prow[3]:  # distinct_values
                            try:
                                profile['distinct_values'] = json.loads(prow[3])
                            except:
                                pass
                        
                        if prow[4]:  # value_distribution
                            try:
                                profile['value_distribution'] = json.loads(prow[4])
                            except:
                                pass
                        
                        if prow[1] == 'numeric':
                            profile['min_value'] = prow[6]
                            profile['max_value'] = prow[7]
                        
                        column_profiles[col_name] = profile
                        
                        if prow[5] and prow[2] and prow[2] <= 20:  # is_categorical and small distinct count
                            categorical_columns.append({
                                'column': col_name,
                                'values': profile.get('distinct_values', []),
                                'distribution': profile.get('value_distribution', {}),
                                'filter_category': prow[8]
                            })
                            
                except Exception as profile_e:
                    logger.debug(f"[SCHEMA] No profiles for {table_name}: {profile_e}")
                
                tables.append({
                    'table_name': table_name,
                    'project': project or 'unknown',
                    'columns': columns,
                    'row_count': row_count,
                    'column_profiles': column_profiles,
                    'categorical_columns': categorical_columns
                })
                
            except Exception as col_e:
                logger.warning(f"[SCHEMA] Error processing {table_name}: {col_e}")
        
        # Get filter candidates
        try:
            filter_candidates = handler.get_filter_candidates(project)
        except:
            pass
        
        logger.info(f"[SCHEMA] Returning {len(tables)} tables for project '{project}'")
        
    except Exception as e:
        logger.error(f"[SCHEMA] Failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    return {'tables': tables, 'filter_candidates': filter_candidates}


# =============================================================================
# ANSWER GENERATION
# =============================================================================

async def generate_synthesized_answer(
    question: str,
    context: str,
    persona: str,
    insights: List,
    conflicts: List,
    citations: CitationBuilder,
    quality_alerts: DataQualityService,
    follow_ups: List[str],
    redactor: ReversibleRedactor
) -> str:
    """
    Generate the final synthesized answer using Claude.
    
    This is where all the pieces come together - data, quality alerts,
    citations, and follow-ups into one cohesive response.
    """
    try:
        if not LLM_AVAILABLE:
            logger.warning("[UNIFIED] LLM not available, returning raw context")
            return context[:3000]
        
        orchestrator = LLMOrchestrator()
        
        if not orchestrator.claude_api_key:
            logger.warning("[UNIFIED] No Claude API key")
            return context[:3000]
        
        import anthropic
        client = anthropic.Anthropic(api_key=orchestrator.claude_api_key)
        
        # Redact PII before sending to Claude
        redacted_context = redactor.redact(context)
        
        # Build system prompt
        system_prompt = """You are an expert UKG implementation consultant helping another consultant analyze customer data and configuration.

Your responses should be:
- Direct and actionable
- Backed by the data provided
- Clear about confidence levels
- Professional but conversational

When presenting findings:
- Lead with the key number/insight
- Provide context for what it means
- Note any caveats or limitations
- Be specific about data sources"""

        # Build user prompt with all context
        user_prompt = f"""Question: {question}

Data Context:
{redacted_context[:8000]}

Please provide a clear, direct answer to the question based on the data above.
Focus on the key insight first, then provide supporting details."""

        # Call Claude
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        
        answer = response.content[0].text
        
        # Restore any PII in the response
        answer = redactor.restore(answer)
        
        return answer
        
    except Exception as e:
        logger.error(f"[UNIFIED] Claude synthesis failed: {e}")
        return context[:2000]


# =============================================================================
# MAIN ENDPOINT
# =============================================================================

@router.post("/chat/unified")
async def unified_chat(request: UnifiedChatRequest):
    """
    UNIFIED CHAT ENDPOINT - The Revolutionary Heart of XLR8
    
    This endpoint combines:
    - Intelligent clarification (from Phase 2)
    - Data model intelligence (reference lookups)
    - Proactive data quality alerts
    - Suggested follow-ups
    - Full citation/audit trail
    - PII protection
    
    Returns a comprehensive response suitable for rich frontend display.
    """
    project = request.project
    message = request.message
    session_id, session = get_or_create_session(request.session_id, project)
    
    logger.warning(f"[UNIFIED] ===== NEW REQUEST =====")
    logger.warning(f"[UNIFIED] Message: {message[:100]}...")
    logger.warning(f"[UNIFIED] Project: {project}, Session: {session_id}")
    
    # Initialize services
    redactor = ReversibleRedactor()
    citation_builder = CitationBuilder()
    
    try:
        # Get or create intelligence engine
        if session['engine']:
            engine = session['engine']
        elif INTELLIGENCE_AVAILABLE:
            engine = IntelligenceEngine(project or 'default')
            session['engine'] = engine
        else:
            return {
                "session_id": session_id,
                "answer": "Intelligence engine not available. Please check deployment.",
                "needs_clarification": False,
                "confidence": 0.0,
                "success": False
            }
        
        # Load structured data handler and schema
        handler = None
        schema = {'tables': [], 'filter_candidates': {}}
        data_model = None
        quality_service = None
        
        if STRUCTURED_AVAILABLE:
            try:
                handler = get_structured_handler()
                if handler and handler.conn:
                    schema = await get_project_schema(project, request.scope, handler)
                    
                    if schema['tables']:
                        engine.load_context(structured_handler=handler, schema=schema)
                        logger.info(f"[UNIFIED] Loaded {len(schema['tables'])} tables")
                        
                        # Initialize Data Model Service
                        data_model = DataModelService(project)
                        data_model.load_lookups(handler)
                        session['data_model'] = data_model
                        
                        # Initialize Quality Service
                        quality_service = DataQualityService(project)
                        
            except Exception as e:
                logger.error(f"[UNIFIED] Structured handler error: {e}")
        
        # Load RAG handler
        if RAG_AVAILABLE:
            try:
                rag = RAGHandler()
                engine.rag_handler = rag
            except Exception as e:
                logger.warning(f"[UNIFIED] RAG handler error: {e}")
        
        # Load relationships
        if SUPABASE_AVAILABLE:
            try:
                supabase = get_supabase()
                result = supabase.table('project_relationships').select('*').eq(
                    'project_name', project
                ).in_('status', ['confirmed', 'auto_confirmed']).execute()
                
                if result.data:
                    engine.relationships = result.data
            except Exception as e:
                logger.warning(f"[UNIFIED] Relationships error: {e}")
        
        # Apply clarifications if provided
        if request.clarifications:
            logger.info(f"[UNIFIED] Applying clarifications: {request.clarifications}")
            engine.confirmed_facts.update(request.clarifications)
            session['skip_learning'] = False
            
            # Record to learning module
            if LEARNING_AVAILABLE:
                try:
                    learning = get_learning_module()
                    for q_id, choice in request.clarifications.items():
                        if not q_id.startswith('_'):
                            learning.record_clarification_choice(
                                question_id=q_id,
                                chosen_option=str(choice),
                                project=project
                            )
                except Exception as e:
                    logger.warning(f"[UNIFIED] Learning record error: {e}")
        
        # Pass conversation context to engine
        if session.get('last_sql') or session.get('last_result'):
            engine.conversation_context = {
                'last_sql': session.get('last_sql'),
                'last_result': session.get('last_result'),
                'last_question': session.get('last_question')
            }
        
        # Determine mode
        mode = None
        if request.mode:
            try:
                mode = IntelligenceMode(request.mode)
            except:
                pass
        
        # Check learning for similar queries
        learned_sql = None
        auto_applied_facts = {}
        
        if LEARNING_AVAILABLE and not request.clarifications and not session.get('skip_learning'):
            try:
                learning = get_learning_module()
                
                # Check for learned SQL patterns
                similar = learning.find_similar_query(
                    question=message,
                    intent=mode.value if mode else None,
                    project=project
                )
                if similar and similar.get('successful_sql'):
                    learned_sql = similar['successful_sql']
                    logger.info(f"[UNIFIED] Found learned SQL pattern")
                    
            except Exception as e:
                logger.warning(f"[UNIFIED] Learning check error: {e}")
        
        # ASK THE INTELLIGENCE ENGINE
        answer = engine.ask(message, mode=mode, context={'learned_sql': learned_sql} if learned_sql else None)
        
        # Check if we can skip clarification using learning
        if answer.structured_output and answer.structured_output.get('type') == 'clarification_needed':
            if LEARNING_AVAILABLE and not session.get('skip_learning'):
                try:
                    learning = get_learning_module()
                    questions = answer.structured_output.get('questions', [])
                    detected_domain = answer.structured_output.get('detected_domains', ['general'])[0]
                    
                    can_skip, learned_answers = learning.should_skip_clarification(
                        questions=questions,
                        domain=detected_domain,
                        project=project
                    )
                    
                    if can_skip and learned_answers:
                        logger.info(f"[UNIFIED] Auto-applying learned answers: {learned_answers}")
                        engine.confirmed_facts.update(learned_answers)
                        auto_applied_facts = learned_answers.copy()
                        answer = engine.ask(message, mode=mode)
                        
                except Exception as e:
                    logger.warning(f"[UNIFIED] Skip clarification error: {e}")
        
        # Build auto-applied note
        auto_applied_note = ""
        if auto_applied_facts:
            notes = []
            for key, value in auto_applied_facts.items():
                if key in ['employee_status', 'status']:
                    if value == 'active':
                        notes.append("Active employees only")
                    elif value == 'termed':
                        notes.append("Terminated employees only")
                    else:
                        notes.append(f"Status: {value}")
                else:
                    notes.append(f"{key}: {value}")
            if notes:
                auto_applied_note = "📌 *Remembered: " + ", ".join(notes) + "*"
        
        # Build response
        response = {
            "session_id": session_id,
            "question": answer.question,
            "confidence": answer.confidence,
            "reasoning": answer.reasoning,
            
            # Auto-applied preferences
            "auto_applied_note": auto_applied_note,
            "auto_applied_facts": auto_applied_facts,
            "can_reset_preferences": bool(auto_applied_facts),
            
            # Clarification
            "needs_clarification": (
                answer.structured_output and 
                answer.structured_output.get('type') == 'clarification_needed'
            ),
            "clarification_questions": (
                answer.structured_output.get('questions', []) 
                if answer.structured_output else []
            ),
            
            # Three Truths
            "from_reality": [],
            "from_intent": [],
            "from_best_practice": [],
            
            # Core results
            "conflicts": [],
            "insights": [],
            "structured_output": answer.structured_output,
            
            # Revolutionary features
            "quality_alerts": None,
            "follow_up_suggestions": [],
            "citations": None,
            
            # Learning
            "used_learning": learned_sql is not None,
            
            # The answer
            "answer": None,
            "success": True
        }
        
        # Serialize truths
        for truth in answer.from_reality:
            response["from_reality"].append(_serialize_truth(truth, data_model))
        for truth in answer.from_intent:
            response["from_intent"].append(_serialize_truth(truth, data_model))
        for truth in answer.from_best_practice:
            response["from_best_practice"].append(_serialize_truth(truth, data_model))
        
        # Serialize conflicts
        for conflict in answer.conflicts:
            response["conflicts"].append({
                "description": conflict.description,
                "severity": conflict.severity,
                "recommendation": conflict.recommendation
            })
        
        # Serialize insights
        for insight in answer.insights:
            response["insights"].append({
                "type": insight.type,
                "title": insight.title,
                "description": insight.description,
                "severity": insight.severity,
                "action_required": insight.action_required
            })
        
        # Generate answer if not clarification
        if not response["needs_clarification"] and answer.answer:
            
            # Check for simple answer (count, sum, etc.)
            simple_answer = _try_simple_answer(answer, data_model)
            
            if simple_answer:
                if auto_applied_note:
                    simple_answer = auto_applied_note + "\n\n" + simple_answer
                response["answer"] = simple_answer
            else:
                # Complex query - use Claude
                synthesized = await generate_synthesized_answer(
                    question=message,
                    context=answer.answer,
                    persona=request.persona,
                    insights=answer.insights,
                    conflicts=answer.conflicts,
                    citations=citation_builder,
                    quality_alerts=quality_service,
                    follow_ups=[],
                    redactor=redactor
                )
                
                if auto_applied_note and synthesized:
                    response["answer"] = auto_applied_note + "\n\n" + synthesized
                else:
                    response["answer"] = synthesized
            
            # Add citations
            if request.include_citations and answer.from_reality:
                for truth in answer.from_reality:
                    if isinstance(truth.content, dict):
                        citation_builder.add_citation(
                            claim=str(truth.content.get('rows', [])[:1]),
                            source_table=truth.source_name,
                            sql=truth.content.get('sql'),
                            row_count=len(truth.content.get('rows', []))
                        )
                response["citations"] = citation_builder.build_audit_trail()
            
            # Run quality checks
            if request.include_quality_alerts and quality_service and schema['tables']:
                quality_service.run_checks(handler, schema['tables'][:5])
                response["quality_alerts"] = quality_service.get_summary()
            
            # Generate follow-ups
            if request.include_follow_ups:
                follow_up_gen = FollowUpGenerator(schema)
                query_type = _detect_query_type(message, answer)
                response["follow_up_suggestions"] = follow_up_gen.generate(
                    query_type=query_type,
                    question=message,
                    result={'answer': response["answer"]}
                )
        
        # Handle no answer case
        if response["answer"] is None and not response["needs_clarification"]:
            if answer.from_reality or answer.from_intent or answer.from_best_practice:
                response["answer"] = "I found some related information but couldn't generate a complete answer. Please try rephrasing your question."
            else:
                response["answer"] = "I couldn't find any data matching your query. Please check that data has been uploaded for this project."
            response["confidence"] = 0.3
        
        # Clarification message
        if response["needs_clarification"]:
            questions = response.get("clarification_questions", [])
            if questions:
                q_text = questions[0].get('question', 'I need more information')
                response["answer"] = f"Before I can answer, {q_text.lower()}"
        
        # Update session
        actual_sql = getattr(answer, 'executed_sql', None) or learned_sql
        session['last_sql'] = actual_sql
        session['last_result'] = response["answer"][:1000] if response.get("answer") else None
        session['last_question'] = message
        
        # Cleanup old sessions
        cleanup_old_sessions()
        
        return response
        
    except Exception as e:
        logger.error(f"[UNIFIED] Error: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(500, f"Chat error: {str(e)}")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _serialize_truth(truth, data_model: Optional[DataModelService] = None) -> Dict:
    """Serialize a Truth object for JSON response."""
    content = truth.content
    
    # Handle data content (rows from DuckDB)
    if isinstance(content, dict) and 'rows' in content:
        rows = content.get('rows', [])
        
        # Enrich with data model if available
        if data_model and rows:
            columns = content.get('columns', [])
            rows = data_model.enrich_results(rows, columns)
        
        content = {
            'columns': content.get('columns', []),
            'rows': rows[:20],  # Limit to 20 rows
            'total': content.get('total', len(rows)),
            'sql': content.get('sql'),
            'query_type': content.get('query_type')
        }
    elif not isinstance(content, (dict, list, str, int, float, bool, type(None))):
        content = str(content)[:2000]
    
    return {
        "source_type": truth.source_type,
        "source_name": truth.source_name,
        "content": content,
        "confidence": truth.confidence,
        "location": truth.location
    }


def _try_simple_answer(answer, data_model: Optional[DataModelService] = None) -> Optional[str]:
    """Try to generate a simple direct answer without Claude."""
    if not answer.from_reality:
        return None
    
    for truth in answer.from_reality:
        if not isinstance(truth.content, dict):
            continue
        
        query_type = truth.content.get('query_type', '')
        rows = truth.content.get('rows', [])
        sql = truth.content.get('sql', '')
        cols = truth.content.get('columns', [])
        
        if query_type == 'count' and rows:
            count_val = list(rows[0].values())[0] if rows[0] else 0
            simple_answer = f"**{count_val:,}** employees match your criteria."
            if sql:
                simple_answer += f"\n\n*Query executed:* `{sql[:300]}`"
            return simple_answer
        
        elif query_type in ['sum', 'average'] and rows:
            result_val = list(rows[0].values())[0] if rows[0] else 0
            label = "Total" if query_type == 'sum' else "Average"
            simple_answer = f"**{label}: {result_val:,.2f}**"
            if sql:
                simple_answer += f"\n\n*Query executed:* `{sql[:300]}`"
            return simple_answer
        
        elif query_type == 'list' and rows and cols:
            # Enrich rows if data model available
            if data_model:
                rows = data_model.enrich_results(rows, cols)
            
            # Format as markdown table
            table_lines = []
            display_cols = cols[:6]
            table_lines.append("| " + " | ".join(display_cols) + " |")
            table_lines.append("|" + "|".join(["---"] * len(display_cols)) + "|")
            
            for row in rows[:20]:
                vals = [str(row.get(c, ''))[:30] for c in display_cols]
                table_lines.append("| " + " | ".join(vals) + " |")
            
            simple_answer = f"**Found {len(rows)} results:**\n\n" + "\n".join(table_lines)
            
            if len(rows) > 20:
                simple_answer += f"\n\n*Showing first 20 of {len(rows)} results*"
            if sql:
                simple_answer += f"\n\n*Query:* `{sql[:200]}`"
            
            return simple_answer
    
    return None


def _detect_query_type(question: str, answer) -> str:
    """Detect the type of query for follow-up generation."""
    question_lower = question.lower()
    
    if any(word in question_lower for word in ['how many', 'count', 'total number']):
        return 'count'
    elif any(word in question_lower for word in ['list', 'show me', 'who are', 'which']):
        return 'list'
    elif any(word in question_lower for word in ['sum', 'total', 'add up']):
        return 'sum'
    elif any(word in question_lower for word in ['analyze', 'compare', 'trend', 'pattern']):
        return 'analysis'
    else:
        return 'general'


def _decrypt_results(rows: List[Dict], handler) -> List[Dict]:
    """Decrypt encrypted fields in query results."""
    if not rows:
        return rows
    
    try:
        encryptor = getattr(handler, 'encryptor', None)
        if not encryptor:
            return rows
        
        decrypted_rows = []
        for row in rows:
            decrypted_row = {}
            for key, value in row.items():
                if isinstance(value, str) and (value.startswith('ENC:') or value.startswith('ENC256:')):
                    try:
                        decrypted_row[key] = encryptor.decrypt(value)
                    except:
                        decrypted_row[key] = '[encrypted]'
                else:
                    decrypted_row[key] = value
            decrypted_rows.append(decrypted_row)
        
        return decrypted_rows
        
    except Exception as e:
        logger.warning(f"[DECRYPT] Error: {e}")
        return rows


# =============================================================================
# SESSION ENDPOINTS
# =============================================================================

@router.get("/chat/unified/session/{session_id}")
async def get_session(session_id: str):
    """Get current state of a unified chat session."""
    if session_id not in unified_sessions:
        raise HTTPException(404, "Session not found")
    
    session = unified_sessions[session_id]
    engine = session.get('engine')
    
    return {
        "session_id": session_id,
        "project": session.get('project'),
        "confirmed_facts": dict(engine.confirmed_facts) if engine else {},
        "conversation_length": len(session.get('conversation_history', [])),
        "last_question": session.get('last_question'),
        "created_at": session.get('created_at')
    }


@router.delete("/chat/unified/session/{session_id}")
async def end_session(session_id: str):
    """End a unified chat session."""
    if session_id in unified_sessions:
        del unified_sessions[session_id]
    return {"success": True}


@router.post("/chat/unified/clarify")
async def submit_clarification(request: ClarificationAnswer):
    """Submit answers to clarification questions."""
    if request.session_id not in unified_sessions:
        raise HTTPException(404, "Session not found")
    
    session = unified_sessions[request.session_id]
    engine = session.get('engine')
    
    if not engine:
        raise HTTPException(400, "Session has no active engine")
    
    # Store confirmed facts
    engine.confirmed_facts.update(request.answers)
    
    # Re-ask the original question
    answer = engine.ask(request.original_question)
    
    return {
        "session_id": request.session_id,
        "question": answer.question,
        "confidence": answer.confidence,
        "answer": answer.answer,
        "needs_clarification": False
    }


# =============================================================================
# PREFERENCES ENDPOINTS
# =============================================================================

@router.post("/chat/unified/reset-preferences")
async def reset_preferences(request: ResetPreferencesRequest):
    """Reset user preferences/filters."""
    result = {
        "success": False,
        "reset_type": request.reset_type,
        "message": ""
    }
    
    try:
        if request.reset_type == "session":
            if request.session_id and request.session_id in unified_sessions:
                session = unified_sessions[request.session_id]
                engine = session.get('engine')
                if engine:
                    old_facts = dict(engine.confirmed_facts)
                    engine.confirmed_facts.clear()
                    session['skip_learning'] = True
                    result["success"] = True
                    result["message"] = f"Cleared session facts: {old_facts}"
                    result["cleared_facts"] = old_facts
                else:
                    result["message"] = "Session found but no engine"
            else:
                result["message"] = "Session not found"
        
        elif request.reset_type == "learned":
            if LEARNING_AVAILABLE and SUPABASE_AVAILABLE:
                try:
                    supabase = get_supabase()
                    supabase.table('clarification_choices').delete().eq(
                        'project', request.project
                    ).execute()
                    result["success"] = True
                    result["message"] = "Cleared learned preferences"
                except Exception as e:
                    result["message"] = f"Database error: {e}"
            else:
                result["message"] = "Learning/Supabase not available"
        
        else:
            result["message"] = f"Unknown reset_type: {request.reset_type}"
            
    except Exception as e:
        result["message"] = f"Error: {e}"
        logger.error(f"[RESET] Error: {e}")
    
    return result


@router.get("/chat/unified/preferences")
async def get_preferences(session_id: str = None, project: str = None):
    """Get current preferences for debugging."""
    result = {
        "session_facts": {},
        "learned_preferences": {},
        "session_exists": False
    }
    
    if session_id and session_id in unified_sessions:
        session = unified_sessions[session_id]
        engine = session.get('engine')
        if engine:
            result["session_facts"] = dict(engine.confirmed_facts)
            result["session_exists"] = True
    
    if LEARNING_AVAILABLE and SUPABASE_AVAILABLE and project:
        try:
            supabase = get_supabase()
            choices = supabase.table('clarification_choices').select('*').eq(
                'project', project
            ).order('created_at', desc=True).limit(20).execute()
            
            if choices.data:
                result["learned_preferences"] = {
                    c['question_id']: c['chosen_option']
                    for c in choices.data
                }
        except Exception as e:
            result["learning_error"] = str(e)
    
    return result


# =============================================================================
# FEEDBACK ENDPOINT
# =============================================================================

@router.post("/chat/unified/feedback")
async def submit_feedback(request: FeedbackRequest):
    """Submit feedback for learning."""
    try:
        if not LEARNING_AVAILABLE:
            return {"success": False, "error": "Learning not available"}
        
        learning = get_learning_module()
        
        # Record feedback
        if hasattr(learning, 'record_feedback'):
            learning.record_feedback(
                question=request.message,
                response=request.response,
                feedback=request.feedback,
                correction=request.correction
            )
        
        return {"success": True, "feedback": request.feedback}
        
    except Exception as e:
        logger.error(f"[FEEDBACK] Error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# PERSONA ENDPOINTS
# =============================================================================

@router.get("/chat/unified/personas")
async def list_personas():
    """List all available personas."""
    if not PERSONAS_AVAILABLE:
        return {"personas": [], "default": "bessie"}
    
    try:
        pm = get_persona_manager()
        return {"personas": pm.list_personas(), "default": "bessie"}
    except Exception as e:
        logger.error(f"[PERSONAS] List error: {e}")
        return {"personas": [], "default": "bessie", "error": str(e)}


@router.get("/chat/unified/personas/{name}")
async def get_persona(name: str):
    """Get specific persona."""
    if not PERSONAS_AVAILABLE:
        raise HTTPException(503, "Personas not available")
    
    try:
        pm = get_persona_manager()
        persona = pm.get_persona(name)
        if persona:
            return persona.to_dict()
        raise HTTPException(404, f"Persona '{name}' not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/chat/unified/personas")
async def create_persona(request: Request):
    """Create a new persona."""
    if not PERSONAS_AVAILABLE:
        raise HTTPException(503, "Personas not available")
    
    try:
        data = await request.json()
        pm = get_persona_manager()
        persona = pm.create_persona(
            name=data['name'],
            icon=data.get('icon', '🤖'),
            description=data.get('description', ''),
            system_prompt=data.get('system_prompt', ''),
            expertise=data.get('expertise', []),
            tone=data.get('tone', 'Professional')
        )
        return {"success": True, "persona": persona.to_dict()}
    except Exception as e:
        logger.error(f"[PERSONAS] Create error: {e}")
        raise HTTPException(500, str(e))


@router.put("/chat/unified/personas/{name}")
async def update_persona(name: str, request: Request):
    """Update an existing persona."""
    if not PERSONAS_AVAILABLE:
        raise HTTPException(503, "Personas not available")
    
    try:
        data = await request.json()
        pm = get_persona_manager()
        persona = pm.update_persona(name, **data)
        if persona:
            return {"success": True, "persona": persona.to_dict()}
        raise HTTPException(404, f"Persona '{name}' not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.delete("/chat/unified/personas/{name}")
async def delete_persona(name: str):
    """Delete a persona."""
    if not PERSONAS_AVAILABLE:
        raise HTTPException(503, "Personas not available")
    
    try:
        pm = get_persona_manager()
        success = pm.delete_persona(name)
        if success:
            return {"success": True}
        raise HTTPException(404, f"Persona '{name}' not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


# =============================================================================
# EXCEL EXPORT ENDPOINT
# =============================================================================

@router.post("/chat/unified/export-excel")
async def export_to_excel(request: ExportRequest):
    """Export query results to Excel with quality report."""
    if not STRUCTURED_AVAILABLE:
        raise HTTPException(503, "Structured queries not available")
    
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
        
        handler = get_structured_handler()
        project = request.project
        
        # Get tables for project
        tables_list = handler.get_tables(project) if project else []
        
        if not tables_list:
            raise HTTPException(404, "No tables found for this project")
        
        # Select tables to export
        tables_to_query = []
        if request.tables:
            for t in tables_list:
                if t.get('table_name') in request.tables:
                    tables_to_query.append(t)
        else:
            # Use first 3 tables
            tables_to_query = tables_list[:3]
        
        # Create workbook
        wb = Workbook()
        
        # Styling
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # Summary tab (if requested)
        if request.include_summary:
            ws_summary = wb.active
            ws_summary.title = "Summary"
            
            ws_summary.cell(row=1, column=1, value="XLR8 Data Export").font = Font(bold=True, size=14)
            ws_summary.cell(row=2, column=1, value=f"Project: {project or 'All'}")
            ws_summary.cell(row=3, column=1, value=f"Query: {request.query}")
            ws_summary.cell(row=4, column=1, value=f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            ws_summary.cell(row=6, column=1, value="Tables Included:").font = Font(bold=True)
            
            for i, t in enumerate(tables_to_query, 1):
                ws_summary.cell(row=6+i, column=1, value=f"• {t.get('table_name', '')}")
        else:
            wb.remove(wb.active)
        
        # Data tabs
        sources_info = []
        for table_info in tables_to_query[:5]:
            table_name = table_info.get('table_name', '')
            sheet_name = table_info.get('sheet', table_name)[:31]  # Excel limit
            
            try:
                sql = f'SELECT * FROM "{table_name}"'
                rows = handler.query(sql)
                cols = list(rows[0].keys()) if rows else []
                
                if not rows:
                    continue
                
                decrypted = _decrypt_results(rows, handler)
                
                ws = wb.create_sheet(title=sheet_name)
                
                # Headers
                for col_idx, col_name in enumerate(cols, 1):
                    cell = ws.cell(row=1, column=col_idx, value=col_name)
                    cell.font = header_font
                    cell.fill = header_fill
                    cell.border = thin_border
                
                # Data
                for row_idx, row_data in enumerate(decrypted[:5000], 2):
                    for col_idx, col_name in enumerate(cols, 1):
                        cell = ws.cell(row=row_idx, column=col_idx, value=row_data.get(col_name, ''))
                        cell.border = thin_border
                
                # Auto-width
                for col_idx in range(1, min(len(cols) + 1, 20)):
                    ws.column_dimensions[get_column_letter(col_idx)].width = 15
                
                sources_info.append({
                    'table': table_name,
                    'rows': len(decrypted),
                    'columns': len(cols)
                })
                
            except Exception as e:
                logger.error(f"[EXPORT] Error on {table_name}: {e}")
        
        # Quality report tab (if requested)
        if request.include_quality_report and project:
            try:
                quality_service = DataQualityService(project)
                quality_service.run_checks(handler, tables_to_query)
                alerts = quality_service.alerts
                
                if alerts:
                    ws_quality = wb.create_sheet(title="Quality Report")
                    
                    headers = ["Severity", "Issue", "Table", "Count", "Description"]
                    for col_idx, header in enumerate(headers, 1):
                        cell = ws_quality.cell(row=1, column=col_idx, value=header)
                        cell.font = header_font
                        cell.fill = header_fill
                    
                    for row_idx, alert in enumerate(alerts, 2):
                        ws_quality.cell(row=row_idx, column=1, value=alert['severity'].upper())
                        ws_quality.cell(row=row_idx, column=2, value=alert['name'])
                        ws_quality.cell(row=row_idx, column=3, value=alert['table'])
                        ws_quality.cell(row=row_idx, column=4, value=alert['count'])
                        ws_quality.cell(row=row_idx, column=5, value=alert['description'])
                        
            except Exception as qe:
                logger.warning(f"[EXPORT] Quality report error: {qe}")
        
        # Save to buffer
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        # Generate filename
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        safe_query = re.sub(r'[^\w\s]', '', request.query[:20]).strip().replace(' ', '_')
        filename = f"xlr8_export_{safe_query}_{timestamp}.xlsx"
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[EXPORT] Error: {e}")
        raise HTTPException(500, f"Export failed: {str(e)}")


# =============================================================================
# DATA INSPECTION ENDPOINTS
# =============================================================================

@router.get("/chat/unified/data/{project}")
async def get_project_data_summary(project: str):
    """Get summary of available data for a project."""
    if not STRUCTURED_AVAILABLE:
        raise HTTPException(503, "Structured queries not available")
    
    try:
        handler = get_structured_handler()
        tables = handler.get_tables(project)
        
        return {
            "project": project,
            "tables": len(tables),
            "summary": [
                {
                    "file": t.get('file'),
                    "sheet": t.get('sheet_name'),
                    "rows": t.get('row_count'),
                    "columns": len(t.get('columns', []))
                }
                for t in tables
            ]
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/chat/unified/data/{project}/{file_name}/versions")
async def get_file_versions(project: str, file_name: str):
    """Get version history for a file."""
    if not STRUCTURED_AVAILABLE:
        raise HTTPException(503, "Not available")
    
    try:
        handler = get_structured_handler()
        return {"versions": handler.get_file_versions(project, file_name)}
    except Exception as e:
        raise HTTPException(500, str(e))


class CompareRequest(BaseModel):
    sheet_name: str
    key_column: str
    version1: Optional[int] = None
    version2: Optional[int] = None


@router.post("/chat/unified/data/{project}/{file_name}/compare")
async def compare_versions(project: str, file_name: str, request: CompareRequest):
    """Compare two versions of a file."""
    if not STRUCTURED_AVAILABLE:
        raise HTTPException(503, "Not available")
    
    try:
        handler = get_structured_handler()
        result = handler.compare_versions(
            project=project,
            file_name=file_name,
            sheet_name=request.sheet_name,
            key_column=request.key_column,
            version1=request.version1,
            version2=request.version2
        )
        if 'error' in result:
            raise HTTPException(400, result['error'])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


# =============================================================================
# DIAGNOSTICS ENDPOINTS
# =============================================================================

@router.get("/chat/unified/diagnostics")
async def get_diagnostics(project: str = None):
    """Get diagnostic information about the chat system."""
    result = {
        "intelligence_available": INTELLIGENCE_AVAILABLE,
        "learning_available": LEARNING_AVAILABLE,
        "structured_available": STRUCTURED_AVAILABLE,
        "rag_available": RAG_AVAILABLE,
        "llm_available": LLM_AVAILABLE,
        "personas_available": PERSONAS_AVAILABLE,
        "active_sessions": len(unified_sessions),
        "profile_status": None,
        "sample_profiles": []
    }
    
    if STRUCTURED_AVAILABLE:
        try:
            handler = get_structured_handler()
            
            # Check for _column_profiles table
            try:
                count = handler.conn.execute("SELECT COUNT(*) FROM _column_profiles").fetchone()[0]
                result["profile_status"] = f"✅ {count} column profiles"
            except:
                result["profile_status"] = "❌ No column profiles - run backfill"
            
            # Sample profiles
            if project:
                try:
                    samples = handler.conn.execute("""
                        SELECT table_name, column_name, inferred_type, distinct_count, is_categorical, filter_category
                        FROM _column_profiles 
                        WHERE table_name LIKE ?
                        LIMIT 15
                    """, [f"{project}%"]).fetchall()
                    
                    result["sample_profiles"] = [
                        {
                            "table": s[0].split('__')[-1],
                            "column": s[1],
                            "type": s[2],
                            "distinct_count": s[3],
                            "is_categorical": s[4],
                            "filter_category": s[5]
                        }
                        for s in samples
                    ]
                except:
                    pass
                    
        except Exception as e:
            result["diagnostics_error"] = str(e)
    
    return result


@router.post("/chat/unified/diagnostics/backfill")
async def run_backfill(project: str = None):
    """Run profile backfill for existing tables."""
    if not STRUCTURED_AVAILABLE:
        raise HTTPException(503, "Structured queries not available")
    
    try:
        handler = get_structured_handler()
        
        if not hasattr(handler, 'backfill_profiles'):
            return {"error": "backfill_profiles method not found - deploy latest structured_data_handler.py"}
        
        result = handler.backfill_profiles(project)
        return result
        
    except Exception as e:
        raise HTTPException(500, str(e))


# =============================================================================
# HEALTH & STATS
# =============================================================================

@router.get("/chat/unified/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.1.0",  # Phase 3.5
        "intelligence": INTELLIGENCE_AVAILABLE,
        "project_intelligence": PROJECT_INTELLIGENCE_AVAILABLE,
        "learning": LEARNING_AVAILABLE,
        "structured": STRUCTURED_AVAILABLE,
        "rag": RAG_AVAILABLE,
        "sessions": len(unified_sessions)
    }


@router.get("/chat/unified/stats")
async def get_stats():
    """Get chat system statistics."""
    stats = {
        "active_sessions": len(unified_sessions),
        "intelligence_available": INTELLIGENCE_AVAILABLE,
        "project_intelligence_available": PROJECT_INTELLIGENCE_AVAILABLE,
        "learning_available": LEARNING_AVAILABLE,
        "structured_available": STRUCTURED_AVAILABLE,
        "rag_available": RAG_AVAILABLE
    }
    
    if LEARNING_AVAILABLE:
        try:
            learning = get_learning_module()
            if hasattr(learning, 'get_stats'):
                stats["learning_stats"] = learning.get_stats()
        except:
            pass
    
    return stats


@router.get("/chat/intelligent/learning/stats")
async def get_learning_stats():
    """
    Get learning system statistics.
    
    This endpoint is called by the Admin UI Learning page.
    Provides counts for learned queries, feedback, preferences, and patterns.
    """
    if not LEARNING_AVAILABLE:
        return {
            'available': False,
            'learned_queries': 0,
            'feedback_records': 0,
            'user_preferences': 0,
            'clarification_patterns': 0
        }
    
    try:
        learning = get_learning_module()
        return learning.get_learning_stats()
    except Exception as e:
        logger.error(f"[LEARNING] Stats error: {e}")
        return {
            'available': False,
            'error': str(e)
        }


# =============================================================================
# BACKWARD COMPATIBILITY REDIRECTS
# =============================================================================

@router.post("/chat/intelligent")
async def intelligent_chat_redirect(request: UnifiedChatRequest):
    """Redirect old /chat/intelligent to unified endpoint."""
    logger.info("[REDIRECT] /chat/intelligent → /chat/unified")
    return await unified_chat(request)


# =============================================================================
# END OF UNIFIED CHAT ROUTER
# =============================================================================
