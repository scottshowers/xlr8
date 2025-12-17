"""
Register Extractor - Intelligent Pay Register Extraction
=========================================================
Formerly "Vacuum" - Rebranded for production use.

ARCHITECTURE:
- PyMuPDF for local text extraction (default)
- PII redaction BEFORE any LLM processing
- LOCAL LLM FIRST (DeepSeek) for extraction - privacy + cost savings
- Claude as fallback for complex/edge cases
- DuckDB storage for chat/intelligence integration
- Profiling for data quality insights

Deploy to: backend/routers/register_extractor.py
Requirements: pip install pymupdf anthropic boto3

Author: XLR8 Team
Version: 1.0.0 - Rebrand from Vacuum + Local LLM + DuckDB
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import os
import re
import json
import logging
import tempfile
import shutil
import uuid
import time
import pandas as pd
import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# IMPORTS - Graceful degradation
# =============================================================================

# LLM Orchestrator (local LLM support)
try:
    from utils.llm_orchestrator import LLMOrchestrator
    LLM_ORCHESTRATOR_AVAILABLE = True
except ImportError:
    try:
        from backend.utils.llm_orchestrator import LLMOrchestrator
        LLM_ORCHESTRATOR_AVAILABLE = True
    except ImportError:
        LLM_ORCHESTRATOR_AVAILABLE = False
        logger.warning("[REGISTER] LLM Orchestrator not available - Claude only mode")

# Structured Data Handler (DuckDB storage)
try:
    from utils.structured_data_handler import get_structured_handler
    DUCKDB_AVAILABLE = True
except ImportError:
    try:
        from backend.utils.structured_data_handler import get_structured_handler
        DUCKDB_AVAILABLE = True
    except ImportError:
        DUCKDB_AVAILABLE = False
        logger.warning("[REGISTER] Structured data handler not available - no DuckDB storage")


# =============================================================================
# PII REDACTION
# =============================================================================

class PIIRedactor:
    """Redact PII before sending to any LLM."""
    
    PATTERNS = {
        'ssn': [
            r'\b\d{3}-\d{2}-\d{4}\b',
            r'\b\d{3}\s\d{2}\s\d{4}\b',
            r'\b\d{9}\b(?=.*(?:ssn|social))',
        ],
        'bank_account': [
            r'\b\d{8,17}\b(?=.*(?:account|acct|routing|aba))',
            r'\b\d{9}\b(?=.*(?:routing|aba))',
        ],
        'credit_card': [
            r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
        ],
    }
    
    PLACEHOLDERS = {
        'ssn': '[SSN-REDACTED]',
        'bank_account': '[ACCOUNT-REDACTED]',
        'credit_card': '[CC-REDACTED]',
    }
    
    def __init__(self):
        self.redaction_count = 0
        self.redaction_log = []
    
    def redact(self, text: str) -> str:
        """Redact all PII patterns from text."""
        self.redaction_count = 0
        self.redaction_log = []
        
        redacted = text
        
        for pii_type, patterns in self.PATTERNS.items():
            placeholder = self.PLACEHOLDERS.get(pii_type, '[REDACTED]')
            
            for pattern in patterns:
                matches = re.findall(pattern, redacted, re.IGNORECASE)
                if matches:
                    self.redaction_count += len(matches)
                    self.redaction_log.append(f"{pii_type}: {len(matches)} redacted")
                    redacted = re.sub(pattern, placeholder, redacted, flags=re.IGNORECASE)
        
        return redacted
    
    def get_stats(self) -> Dict:
        return {
            'total_redacted': self.redaction_count,
            'details': self.redaction_log
        }


# =============================================================================
# SUPABASE STORAGE (Job metadata only - data goes to DuckDB)
# =============================================================================

def get_supabase():
    """Get Supabase client"""
    try:
        from utils.database.supabase_client import get_supabase as _get_supabase
        return _get_supabase()
    except ImportError:
        try:
            from backend.utils.database.supabase_client import get_supabase as _get_supabase
            return _get_supabase()
        except ImportError:
            logger.warning("Supabase client not available")
            return None


def _parse_date(date_str: Optional[str]) -> Optional[str]:
    """Parse date string to ISO format."""
    if not date_str:
        return None
    try:
        for fmt in ['%m/%d/%Y', '%Y-%m-%d', '%m-%d-%Y', '%d/%m/%Y']:
            try:
                return datetime.strptime(str(date_str), fmt).date().isoformat()
            except:
                continue
        return None
    except:
        return None


def _safe_decimal(value) -> Optional[float]:
    """Safely convert to decimal."""
    if value is None:
        return None
    try:
        if isinstance(value, str):
            value = value.replace(',', '').replace('$', '').strip()
            if not value or value == '-':
                return None
        return float(value)
    except:
        return None


def save_extraction_job(
    project_id: Optional[str], 
    source_file: str,
    employee_count: int,
    confidence: float,
    validation_passed: bool, 
    validation_errors: List[str],
    pages_processed: int, 
    cost_usd: float,
    processing_time_ms: int, 
    extraction_method: str = "local_llm",
    customer_id: Optional[str] = None,
    duckdb_table: Optional[str] = None
) -> Optional[Dict]:
    """
    Save extraction job metadata to Supabase.
    
    NOTE: Employee data now goes to DuckDB, not Supabase.
    This just logs the job for history/tracking.
    """
    supabase = get_supabase()
    if not supabase:
        logger.warning("Cannot save job - Supabase not available")
        return None
    
    if not customer_id:
        customer_id = '00000000-0000-0000-0000-000000000001'
    
    try:
        job_data = {
            'customer_id': customer_id,
            'project_id': project_id,
            'source_file': source_file,
            'employee_count': employee_count,
            'confidence': confidence,
            'validation_passed': validation_passed,
            'validation_errors': validation_errors[:20] if validation_errors else [],
            'pages_processed': pages_processed,
            'cost_usd': cost_usd,
            'processing_time_ms': processing_time_ms,
            'extraction_method': extraction_method,
            'status': 'completed',
            'completed_at': datetime.now().isoformat(),
            'duckdb_table': duckdb_table  # Reference to DuckDB table
        }
        
        job_response = supabase.table('extraction_jobs').insert(job_data).execute()
        if not job_response.data:
            logger.error("Failed to insert extraction job")
            return None
        
        return job_response.data[0]
        
    except Exception as e:
        logger.error(f"Failed to save extraction job: {e}")
        return None


def get_extractions(project_id: Optional[str] = None, limit: int = 50) -> List[Dict]:
    """Get extraction history from Supabase."""
    supabase = get_supabase()
    if not supabase:
        return []
    
    try:
        query = supabase.table('extraction_jobs').select('*').order('created_at', desc=True).limit(limit)
        if project_id:
            query = query.eq('project_id', project_id)
        response = query.execute()
        return response.data or []
    except Exception as e:
        logger.error(f"Failed to get extractions: {e}")
        return []


def get_extraction_by_id(extract_id: str) -> Optional[Dict]:
    """Get extraction by ID - now also fetches from DuckDB if available."""
    supabase = get_supabase()
    if not supabase:
        return None
    
    try:
        response = supabase.table('extraction_jobs').select('*').eq('id', extract_id).execute()
        if not response.data:
            return None
        
        job = response.data[0]
        
        # If we have a DuckDB table reference, fetch employees from there
        duckdb_table = job.get('duckdb_table')
        if duckdb_table and DUCKDB_AVAILABLE:
            try:
                handler = get_structured_handler()
                employees_df = handler.conn.execute(f"SELECT * FROM {duckdb_table}").fetchdf()
                job['employees'] = employees_df.to_dict('records')
            except Exception as e:
                logger.warning(f"Could not fetch from DuckDB: {e}")
                job['employees'] = []
        else:
            # Fallback to old Supabase employee storage
            try:
                emp_response = supabase.table('extraction_employees').select('*').eq('extraction_id', extract_id).order('sort_order').execute()
                job['employees'] = emp_response.data or []
            except:
                job['employees'] = []
        
        return job
        
    except Exception as e:
        logger.error(f"Failed to get extraction: {e}")
        return None


def delete_extraction(extract_id: str) -> bool:
    """Delete an extraction and related data."""
    supabase = get_supabase()
    if not supabase:
        return False
    
    try:
        # Get the job first to find DuckDB table
        response = supabase.table('extraction_jobs').select('duckdb_table').eq('id', extract_id).execute()
        if response.data:
            duckdb_table = response.data[0].get('duckdb_table')
            if duckdb_table and DUCKDB_AVAILABLE:
                try:
                    handler = get_structured_handler()
                    handler.conn.execute(f"DROP TABLE IF EXISTS {duckdb_table}")
                    logger.info(f"Dropped DuckDB table: {duckdb_table}")
                except Exception as e:
                    logger.warning(f"Could not drop DuckDB table: {e}")
        
        # Delete from Supabase (CASCADE handles employees/earnings/etc)
        supabase.table('extraction_jobs').delete().eq('id', extract_id).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to delete extraction: {e}")
        return False


# =============================================================================
# DUCKDB STORAGE - NEW!
# =============================================================================

def store_to_duckdb(
    project_id: str,
    source_file: str,
    employees: List[Dict],
    vendor_type: str = "unknown",
    job_id: str = None
) -> Optional[str]:
    """
    Store extracted payroll data to DuckDB for chat/intelligence queries.
    
    Creates a flat table with all employee data.
    Earnings/taxes/deductions are stored as JSON columns for flexibility.
    
    Returns: table_name if successful, None otherwise
    """
    if not DUCKDB_AVAILABLE:
        logger.warning("[REGISTER] DuckDB not available - skipping storage")
        return None
    
    if not employees:
        logger.warning("[REGISTER] No employees to store")
        return None
    
    try:
        if job_id:
            update_job(job_id, message='Storing to database...', progress=96)
        
        handler = get_structured_handler()
        
        # Look up project name from UUID
        project_name = project_id  # Default to ID if lookup fails
        supabase = get_supabase()
        if supabase and project_id:
            try:
                result = supabase.table('projects').select('name').eq('id', project_id).execute()
                if result.data and len(result.data) > 0:
                    project_name = result.data[0].get('name', project_id)
                    logger.info(f"[REGISTER] Resolved project: {project_id} -> {project_name}")
            except Exception as e:
                logger.warning(f"[REGISTER] Could not look up project name: {e}")
        
        # Generate table name using project NAME (not UUID)
        safe_project = re.sub(r'[^a-zA-Z0-9]', '_', project_name.lower())
        safe_file = re.sub(r'[^a-zA-Z0-9]', '_', source_file.lower().replace('.pdf', ''))
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        table_name = f"{safe_project}__payroll__{safe_file}_{timestamp}"
        
        # Limit table name length
        if len(table_name) > 60:
            table_name = table_name[:60]
        
        # Build flat records - convert nested arrays to JSON strings
        if job_id:
            update_job(job_id, message=f'Processing {len(employees)} employees...', progress=97)
        
        flat_records = []
        for emp in employees:
            record = {
                'employee_name': emp.get('name', ''),
                'employee_id': emp.get('employee_id', ''),
                'department': emp.get('department', ''),
                'company_name': emp.get('company_name', ''),
                'check_date': emp.get('check_date', ''),
                'period_ending': emp.get('period_ending', ''),
                'gross_pay': emp.get('gross_pay', 0),
                'net_pay': emp.get('net_pay', 0),
                'total_taxes': emp.get('total_taxes', 0),
                'total_deductions': emp.get('total_deductions', 0),
                'check_number': emp.get('check_number', ''),
                'pay_method': emp.get('pay_method', ''),
                # Demographics
                'hire_date': emp.get('hire_date', ''),
                'term_date': emp.get('term_date', ''),
                'status': emp.get('status', ''),
                'pay_frequency': emp.get('pay_frequency', ''),
                'employee_type': emp.get('employee_type', ''),
                'hourly_rate': emp.get('hourly_rate'),
                'salary': emp.get('salary'),
                'resident_state': emp.get('resident_state', ''),
                'work_state': emp.get('work_state', ''),
                # Nested data as JSON
                'earnings_json': json.dumps(emp.get('earnings', [])),
                'taxes_json': json.dumps(emp.get('taxes', [])),
                'deductions_json': json.dumps(emp.get('deductions', [])),
                # Metadata
                'vendor_type': vendor_type,
                'source_file': source_file,
                'extracted_at': datetime.now().isoformat()
            }
            flat_records.append(record)
        
        # Create DataFrame
        df = pd.DataFrame(flat_records)
        
        # Store in DuckDB
        if job_id:
            update_job(job_id, message='Writing to DuckDB...', progress=98)
        
        handler.conn.execute(f"DROP TABLE IF EXISTS {table_name}")
        handler.conn.register('temp_payroll', df)
        handler.conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM temp_payroll")
        handler.conn.unregister('temp_payroll')
        
        # Store metadata
        try:
            columns_info = [{'name': col, 'type': 'VARCHAR'} for col in df.columns]
            handler.conn.execute("""
                INSERT INTO _schema_metadata 
                (id, project, file_name, sheet_name, table_name, columns, row_count, version, is_current)
                VALUES (nextval('schema_metadata_seq'), ?, ?, 'payroll', ?, ?, ?, 1, TRUE)
            """, [
                project_name,
                source_file,
                table_name,
                json.dumps(columns_info),
                len(df)
            ])
        except Exception as meta_err:
            logger.warning(f"Could not store metadata: {meta_err}")
        
        logger.info(f"[REGISTER] Stored {len(employees)} employees to DuckDB: {table_name}")
        
        # Queue profiling in background (don't block on it)
        if job_id:
            update_job(job_id, message='Profiling queued...', progress=100)
        
        try:
            # Import the queue function from structured_data_handler
            from utils.structured_data_handler import queue_inference_job
            
            # Build tables_info for the queue
            tables_info = [{
                'table_name': table_name,
                'columns': list(df.columns),
                'row_count': len(df)
            }]
            
            # Queue it - don't wait
            queue_inference_job(handler, f"reg_{table_name[:20]}", project_name, source_file, tables_info)
            logger.info(f"[REGISTER] Queued profiling for: {table_name}")
        except Exception as prof_err:
            # Fallback to sync profiling if queue not available
            logger.warning(f"[REGISTER] Queue not available, running sync profiling: {prof_err}")
            try:
                handler.profile_columns_fast(project_name, table_name)
                logger.info(f"[REGISTER] Profiled table: {table_name}")
            except Exception as e:
                logger.warning(f"[REGISTER] Profiling failed: {e}")
        
        return table_name
        
    except Exception as e:
        logger.error(f"[REGISTER] DuckDB storage failed: {e}")
        return None


# =============================================================================
# JOB TRACKING
# =============================================================================

_jobs: Dict[str, Dict] = {}

def create_job(filename: str) -> str:
    """Create a new job and return its ID."""
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        'id': job_id,
        'status': 'pending',
        'filename': filename,
        'progress': 0,
        'current_page': 0,
        'total_pages': 0,
        'message': 'Starting...',
        'result': None,
        'created_at': datetime.now().isoformat()
    }
    return job_id

def update_job(job_id: str, **kwargs):
    """Update job status."""
    if job_id in _jobs:
        _jobs[job_id].update(kwargs)

def get_job(job_id: str) -> Optional[Dict]:
    """Get job status."""
    return _jobs.get(job_id)


# =============================================================================
# EXTRACTOR CLASS
# =============================================================================

class RegisterExtractor:
    """
    Privacy-first payroll register extractor.
    
    NEW in v1.0:
    - Local LLM (DeepSeek) first for extraction
    - Claude only as fallback for complex formats
    - DuckDB storage for chat/intelligence integration
    """
    
    def __init__(self):
        self.claude_api_key = os.environ.get('CLAUDE_API_KEY')
        self.aws_region = os.environ.get('AWS_REGION', 'us-east-1')
        self._textract = None
        self._claude = None
        self._orchestrator = None
        self.redactor = PIIRedactor()
    
    @property
    def is_available(self) -> bool:
        """Check if extraction is available (either local LLM or Claude)."""
        return LLM_ORCHESTRATOR_AVAILABLE or bool(self.claude_api_key)
    
    @property
    def orchestrator(self):
        """Get LLM orchestrator instance."""
        if self._orchestrator is None and LLM_ORCHESTRATOR_AVAILABLE:
            self._orchestrator = LLMOrchestrator()
        return self._orchestrator
    
    @property
    def textract(self):
        if self._textract is None:
            import boto3
            self._textract = boto3.client('textract', region_name=self.aws_region)
        return self._textract
    
    @property
    def claude(self):
        if self._claude is None:
            import anthropic
            self._claude = anthropic.Anthropic(api_key=self.claude_api_key)
        return self._claude
    
    def extract(
        self, 
        file_path: str, 
        max_pages: int = 0,
        use_textract: bool = False, 
        job_id: str = None,
        vendor_type: str = "unknown",
        project_id: str = None
    ) -> Dict:
        """
        Extract employee pay data from PDF.
        
        NEW: Uses local LLM first, falls back to Claude if needed.
        """
        start = datetime.now()
        filename = os.path.basename(file_path)
        method = "textract" if use_textract else "pymupdf"
        llm_used = "local"  # Track which LLM was used
        
        try:
            # Step 1: Extract text
            if job_id:
                update_job(job_id, status='processing', message='Extracting text from PDF...')
            
            if use_textract:
                logger.info(f"Using Textract for OCR extraction...")
                pages_text, pages_processed = self._extract_with_textract(file_path, max_pages, job_id)
            else:
                logger.info(f"Using PyMuPDF for local extraction (privacy-compliant)...")
                if vendor_type == "unknown":
                    quick_text = self._quick_vendor_detect(file_path)
                    vendor_type = self._detect_vendor([quick_text]) if quick_text else "unknown"
                    logger.info(f"Quick vendor detection: {vendor_type}")
                
                pages_text, pages_processed = self._extract_with_pymupdf(file_path, max_pages, job_id, vendor_type)
            
            if not pages_text:
                raise ValueError("No text extracted from PDF")
            
            if vendor_type == "unknown":
                vendor_type = self._detect_vendor(pages_text)
                logger.info(f"Auto-detected vendor: {vendor_type}")
            
            # Step 2: Redact PII
            if job_id:
                update_job(job_id, message='Redacting sensitive data...')
            
            logger.info("Redacting PII before LLM processing...")
            redacted_pages = [self.redactor.redact(page) for page in pages_text]
            redaction_stats = self.redactor.get_stats()
            logger.info(f"PII Redaction: {redaction_stats}")
            
            # Step 3: Parse with LLM - LOCAL FIRST, Claude fallback
            if job_id:
                update_job(job_id, message=f'Parsing with AI ({vendor_type})...', progress=80)
            
            employees, llm_used, cost = self._parse_with_llm(redacted_pages, vendor_type, job_id)
            
            # Step 3.5: Fix truncated descriptions using ORIGINAL text
            if vendor_type != 'dayforce' and employees:
                original_text = "\n\n--- PAGE BREAK ---\n\n".join(pages_text)
                employees = self._fix_descriptions(employees, original_text)
            
            # Step 4: Validate
            if job_id:
                update_job(job_id, message='Validating results...', progress=95)
            
            validation_errors = []
            for emp in employees:
                errors = self._validate_employee(emp)
                emp['validation_errors'] = errors
                emp['is_valid'] = len(errors) == 0
                validation_errors.extend(errors)
            
            valid_count = sum(1 for e in employees if e.get('is_valid', False))
            confidence = valid_count / len(employees) if employees else 0.0
            
            processing_time = int((datetime.now() - start).total_seconds() * 1000)
            raw_text = "\n\n--- PAGE BREAK ---\n\n".join(pages_text)
            
            # Step 5: Store to DuckDB
            duckdb_table = None
            if employees and project_id:
                duckdb_table = store_to_duckdb(project_id, filename, employees, vendor_type, job_id)
            
            result = {
                "success": len(employees) > 0,
                "source_file": filename,
                "employees": employees,
                "employee_count": len(employees),
                "confidence": confidence,
                "validation_passed": len(validation_errors) == 0,
                "validation_errors": validation_errors[:20],
                "pages_processed": pages_processed,
                "processing_time_ms": processing_time,
                "cost_usd": round(cost, 4),
                "extraction_method": method,
                "llm_used": llm_used,
                "pii_redacted": redaction_stats['total_redacted'],
                "privacy_compliant": True,
                "raw_text": raw_text,
                "duckdb_table": duckdb_table
            }
            
            if job_id:
                update_job(job_id, status='completed', progress=100, 
                          message='Extraction complete', result=result)
            
            return result
            
        except Exception as e:
            logger.error(f"Extraction failed: {e}", exc_info=True)
            processing_time = int((datetime.now() - start).total_seconds() * 1000)
            
            error_result = {
                "success": False,
                "source_file": filename,
                "employees": [],
                "employee_count": 0,
                "confidence": 0.0,
                "validation_passed": False,
                "validation_errors": [str(e)],
                "pages_processed": 0,
                "processing_time_ms": processing_time,
                "cost_usd": 0.0,
                "extraction_method": method,
                "llm_used": "none",
                "privacy_compliant": True
            }
            
            if job_id:
                update_job(job_id, status='failed', message=str(e), result=error_result)
            
            return error_result
    
    def _parse_with_llm(self, pages_text: List[str], vendor_type: str, job_id: str = None) -> tuple:
        """
        Parse employees using Groq (page-by-page) + code merge.
        
        Strategy:
        1. Extract each page individually via Groq (fast, accurate)
        2. Merge employees by employee_id in code (deterministic)
        
        Returns: (employees, llm_used, cost_usd)
        """
        groq_api_key = os.getenv("GROQ_API_KEY", "")
        
        if not groq_api_key:
            # Fallback to Claude if no Groq
            if self.claude_api_key:
                logger.info("[REGISTER] No Groq API key, falling back to Claude...")
                employees = self._parse_with_claude_direct(pages_text, vendor_type, job_id)
                return employees, "claude", 0.05
            return [], "none", 0.0
        
        logger.info(f"[REGISTER] Groq page-by-page extraction ({len(pages_text)} pages)...")
        
        prompt_template = self._get_vendor_prompt(vendor_type)
        all_employees = []
        
        # Overlap settings for page-spanning records
        OVERLAP_CHARS = 600  # Include last 600 chars from previous page
        
        for page_idx, page_text in enumerate(pages_text):
            page_num = page_idx + 1
            
            if job_id:
                progress = 80 + int((page_idx / len(pages_text)) * 15)
                update_job(job_id, message=f'Extracting page {page_num}/{len(pages_text)}...', progress=progress)
            
            # Build context with overlap from previous page
            if page_idx > 0 and len(pages_text[page_idx - 1]) > 0:
                prev_page = pages_text[page_idx - 1]
                overlap_text = prev_page[-OVERLAP_CHARS:] if len(prev_page) > OVERLAP_CHARS else prev_page
                context_text = f"[END OF PREVIOUS PAGE - for context only, may contain partial employee data:]\n{overlap_text}\n\n[CURRENT PAGE {page_num} - extract employees from here:]\n{page_text}"
                has_overlap = True
            else:
                context_text = page_text
                has_overlap = False
            
            logger.warning(f"[REGISTER] Processing page {page_num}/{len(pages_text)} ({len(page_text)} chars, overlap={has_overlap})...")
            
            page_prompt = f"""{prompt_template}

{context_text}

INSTRUCTIONS:
- Extract ALL employees visible on the CURRENT PAGE (page {page_num})
- If an employee's data started on the previous page (shown in context), include their FULL record with all data you can see
- If an employee's data appears partial at the end of this page, still extract what you see
- We will merge duplicate records later, so it's OK to extract the same employee twice

Return ONLY a valid JSON array. No markdown, no explanation."""

            try:
                # Retry logic - paid tier has high limits but keep as safety net
                max_retries = 3
                retry_delay = 5  # seconds - quick retry on paid tier
                
                for attempt in range(max_retries):
                    response = requests.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {groq_api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "llama-3.3-70b-versatile",
                            "messages": [{"role": "user", "content": page_prompt}],
                            "temperature": 0.1,
                            "max_tokens": 8192
                        },
                        timeout=60
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                        logger.warning(f"[REGISTER] Page {page_num} raw response length: {len(content)}")
                        
                        page_employees = self._parse_json_response(content)
                        
                        if page_employees:
                            logger.warning(f"[REGISTER] Page {page_num}: {len(page_employees)} employees extracted")
                            for emp in page_employees:
                                logger.warning(f"[REGISTER]   - {emp.get('name', 'NO NAME')} (ID: {emp.get('employee_id', 'NO ID')})")
                            all_employees.extend(page_employees)
                        else:
                            logger.warning(f"[REGISTER] Page {page_num}: NO employees parsed from response")
                            logger.warning(f"[REGISTER] Page {page_num} response preview: {content[:500]}...")
                        
                        # Paid tier - minimal delay just to be safe
                        if page_idx < len(pages_text) - 1:  # Don't delay after last page
                            time.sleep(1)  # 1 second courtesy delay
                        break  # Success, exit retry loop
                        
                    elif response.status_code == 429:
                        # Rate limited - wait and retry
                        wait_time = retry_delay * (attempt + 1)  # Exponential backoff
                        logger.warning(f"[REGISTER] Page {page_num} rate limited, waiting {wait_time}s (attempt {attempt + 1}/{max_retries})...")
                        
                        if job_id:
                            update_job(job_id, message=f'Rate limited, waiting {wait_time}s... (page {page_num})')
                        
                        time.sleep(wait_time)
                        
                        if attempt == max_retries - 1:
                            logger.warning(f"[REGISTER] Page {page_num} failed after {max_retries} retries due to rate limiting")
                    else:
                        logger.warning(f"[REGISTER] Page {page_num} Groq error: {response.status_code} - {response.text[:200]}")
                        break  # Non-rate-limit error, don't retry
                    
            except Exception as e:
                logger.warning(f"[REGISTER] Page {page_num} error: {e}")
        
        # Merge employees by employee_id
        if all_employees:
            merged = self._merge_employees(all_employees)
            logger.info(f"[REGISTER] Groq extraction complete: {len(all_employees)} raw -> {len(merged)} merged")
            return merged, "groq_llama70b", 0.001
        
        # Fallback to Claude
        if self.claude_api_key:
            logger.info("[REGISTER] Groq returned no employees, falling back to Claude...")
            employees = self._parse_with_claude_direct(pages_text, vendor_type, job_id)
            return employees, "claude", 0.05
        
        return [], "none", 0.0
    
    def _merge_employees(self, employees: List[Dict]) -> List[Dict]:
        """
        Merge employee records by employee_id or name.
        Handles employees split across pages.
        Uses two-pass approach: first by employee_id, then by normalized name.
        """
        logger.warning(f"[REGISTER] Starting merge of {len(employees)} raw employee records...")
        
        def normalize_name(name: str) -> str:
            """Aggressively normalize name for deduplication."""
            if not name:
                return ""
            # Uppercase
            name = name.upper()
            # Remove ALL punctuation
            name = ''.join(c if c.isalnum() or c == ' ' else '' for c in name)
            # Normalize whitespace
            name = ' '.join(name.split())
            return name
        
        # First pass: collect all records, build name->id mapping
        name_to_ids = {}  # normalized_name -> set of employee_ids
        id_to_name = {}   # employee_id -> normalized_name
        
        for emp in employees:
            raw_name = emp.get('name', '') or ''
            raw_name = raw_name.strip() if isinstance(raw_name, str) else ''
            emp_id = emp.get('employee_id', '') or ''
            emp_id = emp_id.strip().upper() if isinstance(emp_id, str) else ''
            
            normalized = normalize_name(raw_name)
            if normalized:
                if normalized not in name_to_ids:
                    name_to_ids[normalized] = set()
                if emp_id:
                    name_to_ids[normalized].add(emp_id)
                    id_to_name[emp_id] = normalized
        
        # Second pass: merge using normalized name as primary key
        merged = {}
        
        for emp in employees:
            raw_name = emp.get('name', '') or ''
            raw_name = raw_name.strip() if isinstance(raw_name, str) else ''
            emp_id = emp.get('employee_id', '') or ''
            emp_id = emp_id.strip().upper() if isinstance(emp_id, str) else ''
            
            # Skip completely empty records
            if not raw_name and not emp_id:
                logger.warning(f"[REGISTER] Skipping blank employee record")
                continue
            
            # Normalize name
            normalized_name = normalize_name(raw_name)
            
            # ALWAYS use normalized name as merge key if available
            # This ensures "COOK, BETTY L" with ID and without ID merge together
            if normalized_name:
                merge_key = normalized_name
            elif emp_id and emp_id in id_to_name:
                # If we only have ID, look up the name we found elsewhere
                merge_key = id_to_name[emp_id]
            elif emp_id:
                merge_key = f"ID_{emp_id}"
            else:
                merge_key = f"_unknown_{len(merged)}"
            
            # Display name for logging
            display_name = raw_name if raw_name else f"(ID only: {emp_id})"
            
            if merge_key not in merged:
                merged[merge_key] = emp.copy()
                logger.warning(f"[REGISTER] New employee: {display_name}")
            else:
                # Merge: combine arrays, prefer non-zero values
                logger.warning(f"[REGISTER] Merging duplicate: {display_name}")
                existing = merged[merge_key]
                
                # If existing has no name but new one does, use the name
                if not existing.get('name') and raw_name:
                    existing['name'] = raw_name
                
                # If existing has no employee_id but new one does, use it
                if not existing.get('employee_id') and emp_id:
                    existing['employee_id'] = emp_id
                
                # Merge earnings, taxes, deductions arrays - dedupe by TYPE only
                # Each earning code (Regular, Shift Diff C2, etc) should appear only ONCE per employee
                for field in ['earnings', 'taxes', 'deductions']:
                    existing_items = existing.get(field, [])
                    new_items = emp.get(field, [])
                    
                    # Normalize function for consistent matching
                    def norm(s):
                        return ' '.join(str(s or '').lower().split())
                    
                    # Build seen set from existing items - BY TYPE ONLY
                    seen_types = {norm(item.get('type', '')) for item in existing_items if item.get('type')}
                    seen_descs = {norm(item.get('description', '')) for item in existing_items if item.get('description')}
                    
                    for item in new_items:
                        item_type = norm(item.get('type', ''))
                        item_desc = norm(item.get('description', ''))
                        
                        # Skip if we've seen this type OR this description
                        if item_type and item_type in seen_types:
                            continue
                        if item_desc and item_desc in seen_descs:
                            continue
                        
                        existing_items.append(item)
                        if item_type:
                            seen_types.add(item_type)
                        if item_desc:
                            seen_descs.add(item_desc)
                    
                    existing[field] = existing_items
                
                # Prefer non-zero/non-empty values for scalars
                for field in ['gross_pay', 'net_pay', 'total_taxes', 'total_deductions']:
                    if not existing.get(field) and emp.get(field):
                        existing[field] = emp[field]
                
                for field in ['name', 'department', 'company_name', 'check_number', 'check_date', 'employee_id']:
                    if not existing.get(field) and emp.get(field):
                        existing[field] = emp[field]
        
        # Post-merge: ALWAYS calculate totals from line items - they are the source of truth
        result = []
        for key, emp in merged.items():
            if not emp.get('name') and emp.get('employee_id'):
                logger.warning(f"[REGISTER] WARNING: Employee {emp.get('employee_id')} has no name!")
            
            # ALWAYS calculate totals from line items - NO EXCEPTIONS
            calc_taxes = sum(float(t.get('amount', 0) or 0) for t in emp.get('taxes', []))
            
            # Filter out payment methods from deductions - they are NOT deductions
            payment_methods = ['direct deposit', 'net check', 'check', 'payment']
            real_deductions = [
                d for d in emp.get('deductions', [])
                if not any(pm in str(d.get('description', '')).lower() for pm in payment_methods)
                and not any(pm in str(d.get('type', '')).lower() for pm in payment_methods)
            ]
            calc_deductions = sum(float(d.get('amount', 0) or 0) for d in real_deductions)
            
            calc_earnings = sum(float(e.get('amount', 0) or 0) for e in emp.get('earnings', []))
            
            # Overwrite totals with calculated values
            emp['total_taxes'] = calc_taxes
            emp['total_deductions'] = calc_deductions
            
            # Also clean up the deductions array itself
            emp['deductions'] = real_deductions
            
            # If gross is 0 but we have earnings, use earnings sum
            if not emp.get('gross_pay') and calc_earnings > 0:
                emp['gross_pay'] = calc_earnings
            
            result.append(emp)
        
        logger.warning(f"[REGISTER] Merge complete: {len(employees)} raw -> {len(result)} unique employees")
        return result
    
    def _parse_with_claude_direct(self, pages_text: List[str], vendor_type: str = "unknown", job_id: str = None) -> List[Dict]:
        """Send REDACTED text to Claude for parsing - with progress updates"""
        
        full_text = "\n\n--- PAGE BREAK ---\n\n".join(pages_text)
        
        if len(full_text) > 80000:
            logger.warning(f"Text too long ({len(full_text)}), truncating to 80k chars")
            full_text = full_text[:80000]
        
        logger.info(f"Sending {len(full_text)} characters to Claude ({len(pages_text)} pages), vendor: {vendor_type}")
        
        if job_id:
            update_job(job_id, message=f'AI processing {len(pages_text)} pages...', progress=80)
        
        prompt_template = self._get_vendor_prompt(vendor_type)
        prompt = self._build_prompt(prompt_template, full_text, vendor_type)

        try:
            response_text = ""
            chunk_count = 0
            with self.claude.messages.stream(
                model="claude-sonnet-4-20250514",
                max_tokens=64000,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            ) as stream:
                for text in stream.text_stream:
                    response_text += text
                    chunk_count += 1
                    
                    # Update progress every 100 chunks
                    if job_id and chunk_count % 100 == 0:
                        # Progress from 80 to 95 during streaming
                        chars_received = len(response_text)
                        progress = min(95, 80 + int(chars_received / 5000))  # ~1% per 5KB
                        update_job(job_id, message=f'Extracting employees ({chars_received:,} chars received)...', progress=progress)
                
                try:
                    final_message = stream.get_final_message()
                    if final_message and hasattr(final_message, 'usage'):
                        from backend.utils.cost_tracker import log_cost, CostService
                        log_cost(
                            service=CostService.CLAUDE,
                            operation="register_extract",
                            tokens_in=final_message.usage.input_tokens,
                            tokens_out=final_message.usage.output_tokens,
                            metadata={"model": "claude-sonnet-4-20250514", "vendor": vendor_type}
                        )
                except Exception as cost_err:
                    logger.debug(f"Cost tracking failed: {cost_err}")
            
            logger.info(f"Claude response length: {len(response_text)}")
            
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return []
        
        employees = self._parse_json_response(response_text)
        return employees
    
    def _extract_with_pymupdf(self, file_path: str, max_pages: int, job_id: str = None, vendor_type: str = "unknown") -> tuple:
        """Extract text using PyMuPDF (local, free, private)."""
        import fitz
        
        pages_text = []
        doc = fitz.open(file_path)
        
        try:
            total = len(doc)
            to_process = min(max_pages, total) if max_pages > 0 else total
            
            if job_id:
                update_job(job_id, total_pages=to_process)
            
            for page_num in range(to_process):
                page = doc[page_num]
                text = page.get_text()
                pages_text.append(text)
                
                if job_id:
                    progress = int((page_num + 1) / to_process * 70)
                    update_job(job_id, current_page=page_num + 1, progress=progress,
                              message=f'Extracting page {page_num + 1} of {to_process}...')
            
        finally:
            doc.close()
        
        return pages_text, len(pages_text)
    
    def _extract_with_textract(self, file_path: str, max_pages: int, job_id: str = None) -> tuple:
        """Extract text using AWS Textract (for scanned PDFs)."""
        import fitz
        
        pages_text = []
        doc = fitz.open(file_path)
        
        try:
            total = len(doc)
            to_process = min(max_pages, total) if max_pages > 0 else total
            
            for page_num in range(to_process):
                page = doc[page_num]
                pix = page.get_pixmap(dpi=200)
                img_bytes = pix.tobytes("png")
                
                response = self.textract.analyze_document(
                    Document={'Bytes': img_bytes},
                    FeatureTypes=['TABLES', 'FORMS']
                )
                
                lines = []
                for block in response.get('Blocks', []):
                    if block['BlockType'] == 'LINE':
                        lines.append(block.get('Text', ''))
                
                pages_text.append('\n'.join(lines))
                
                if job_id:
                    progress = int((page_num + 1) / to_process * 70)
                    update_job(job_id, current_page=page_num + 1, progress=progress,
                              message=f'OCR processing page {page_num + 1} of {to_process}...')
                
        finally:
            doc.close()
        
        return pages_text, len(pages_text)
    
    def _get_vendor_prompt(self, vendor_type: str) -> str:
        """Load vendor-specific prompt from database, with fallback to default."""
        base_prompt = None
        supabase = get_supabase()
        
        if supabase:
            try:
                response = supabase.table('vendor_prompts').select('prompt_template').eq('vendor_type', vendor_type).eq('is_active', True).execute()
                if response.data:
                    logger.warning(f"[REGISTER] Loaded Supabase prompt for vendor: {vendor_type} ({len(response.data[0]['prompt_template'])} chars)")
                    base_prompt = response.data[0]['prompt_template']
                else:
                    logger.warning(f"[REGISTER] No Supabase prompt found for vendor: {vendor_type}")
            except Exception as e:
                logger.warning(f"[REGISTER] Failed to load vendor prompt: {e}")
        else:
            logger.warning(f"[REGISTER] Supabase not available, using default prompt")
        
        if not base_prompt:
            logger.warning(f"[REGISTER] Using DEFAULT prompt for vendor: {vendor_type}")
            base_prompt = self._get_default_prompt()
        
        # ALWAYS append critical extraction hints - these work across all vendors
        critical_hints = self._get_critical_extraction_hints()
        return f"{base_prompt}\n\n{critical_hints}"
    
    def _get_critical_extraction_hints(self) -> str:
        """Critical extraction hints that should ALWAYS be included."""
        return """
=== CRITICAL FIELD EXTRACTION RULES ===

EMPLOYEE ID - MUST EXTRACT:
- Look for "Code: XXXX" pattern (e.g., "Code: A30H") - this IS the employee_id
- Also look for: "ID:", "Emp #:", "Employee #:", "Badge:", "EE ID:", "Emp ID:"
- The ID is usually a short alphanumeric code like "A30H", "A3JC", "12345", "EE001"
- Extract the CODE VALUE, not the label

DEPARTMENT - MUST EXTRACT:
- Departments appear as SECTION HEADERS above groups of employees
- Format examples: "2025 - RN No Benefit or Diff", "2099 - MED TECH", "DEPT 100 - ACCOUNTING"
- The number prefix (2025, 2099, 100) is often the department code
- Apply the department header to ALL employees listed below it until the next department header appears

TAX PROFILE:
- Look for "Tax Profile: X - XX/XX/XX" pattern (e.g., "Tax Profile: 1 - MD/MD/MD")
- Extract the full string including the number and state codes

=== CRITICAL: WHAT IS NOT A DEDUCTION ===
DO NOT include these in the deductions array - they are PAYMENT METHODS, not deductions:
- "Direct Deposit" - this is HOW the net pay is delivered, NOT a deduction
- "Net Check" - payment method
- "Payment:" lines - these describe payment method
- Any line showing how money is PAID OUT is not a deduction

DEDUCTIONS are things SUBTRACTED from gross pay like:
- 401K contributions
- Health/Dental/Vision insurance premiums
- Life insurance
- Garnishments
- Union dues

EXAMPLE EXTRACTION:
If you see:
  2025 - RN No Benefit or Diff
  METZ, TILLIE
  Code: A30H
  Tax Profile: 1 - MD/MD/MD

Then extract:
  name: "METZ, TILLIE"
  employee_id: "A30H"
  department: "2025 - RN No Benefit or Diff"
  tax_profile: "1 - MD/MD/MD"
"""
    
    def _get_default_prompt(self) -> str:
        """Default prompt template - works for most register formats."""
        return """IMPORTANT - READ FIRST:
When extracting earnings, taxes, and deductions, the "description" field must be the EXACT TEXT from the document.
Copy each description EXACTLY as written, character for character.

STRICT RULES:
1. Return ONLY a valid JSON array - no markdown, no explanation
2. Each employee object must have these EXACT keys:
   company_name, client_code, period_ending, check_date, name, employee_id, department, tax_profile, gross_pay, net_pay, total_taxes, total_deductions, earnings, taxes, deductions, check_number, pay_method

EMPLOYEE ID EXTRACTION - CRITICAL:
- Look for "Code: XXXX" below the employee name - this IS the employee_id
- Also look for "ID:", "Emp #:", "Employee #:", "Badge:", "EE ID:" patterns
- The employee_id is usually a short alphanumeric code like "A30H", "A3JC", "12345"

DEPARTMENT EXTRACTION - CRITICAL:
- Departments often appear as HEADER ROWS above groups of employees
- Format like "2025 - RN No Benefit or Diff" or "2099 - MED TECH"
- The number prefix (2025, 2099) is the department code
- Apply this department to ALL employees listed below that header until the next department header

TAX PROFILE:
- Look for "Tax Profile: X - XX/XX/XX" pattern (e.g., "1 - MD/MD/MD")

3. earnings array: objects with type, description, amount, hours, rate, amount_ytd, hours_ytd
4. taxes array: objects with type, description, amount, taxable_wages, amount_ytd, is_employer (true if employer-paid)
5. deductions array: objects with type, description, amount, amount_ytd, category (pre_tax, post_tax, or memo)
6. Use 0 for missing numbers, "" for missing strings, [] for missing arrays
7. Ignore [REDACTED] placeholders

Extract all employees and return as JSON array."""
    
    def _build_prompt(self, template: str, full_text: str, vendor_type: str) -> str:
        """Build the complete prompt with data."""
        return f"""{template}

DATA TO EXTRACT:
{full_text}

Return the JSON array now:"""
    
    def _quick_vendor_detect(self, file_path: str) -> str:
        """Quick first-page scan for vendor detection."""
        import fitz
        try:
            doc = fitz.open(file_path)
            if len(doc) > 0:
                text = doc[0].get_text()
                doc.close()
                return text
            doc.close()
        except Exception as e:
            logger.warning(f"Quick vendor detect failed: {e}")
        return ""

    def _detect_vendor(self, pages_text: List[str]) -> str:
        """Auto-detect vendor from register content."""
        sample_text = "\n".join(pages_text[:3]).lower()
        
        vendor_signatures = {
            'dayforce': ['dayforce', 'ceridian', 'payroll register report (pr001)'],
            'paycom': ['paycom', 'client:', 'tax profile:'],
            'adp': ['adp', 'automatic data processing', 'run payroll'],
            'paychex': ['paychex', 'paychex flex'],
            'ultipro': ['ultipro', 'ukg pro', 'ultimate software'],
            'workday': ['workday', 'wd payroll'],
            'gusto': ['gusto', 'zenpayroll'],
            'quickbooks': ['quickbooks', 'intuit payroll'],
        }
        
        for vendor, signatures in vendor_signatures.items():
            for sig in signatures:
                if sig in sample_text:
                    return vendor
        
        return 'unknown'
    
    def _parse_json_response(self, response_text: str) -> List[Dict]:
        """Parse JSON from LLM response with multiple fallback strategies."""
        text = response_text.strip()
        
        # Remove markdown code fences
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'^```\s*', '', text)
        text = re.sub(r'\s*```\s*$', '', text)
        
        # Find array bounds
        start_idx = text.find('[')
        end_idx = text.rfind(']')
        
        if start_idx < 0:
            logger.error("No JSON array found in response")
            return []
        
        if end_idx < start_idx:
            last_brace = text.rfind('}')
            if last_brace > start_idx:
                text = text[:last_brace + 1] + ']'
                end_idx = len(text) - 1
            else:
                return []
        
        json_str = text[start_idx:end_idx + 1]
        
        # Fix common issues
        json_str = re.sub(r',\s*]', ']', json_str)
        json_str = re.sub(r',\s*}', '}', json_str)
        
        # Try direct parse
        try:
            data = json.loads(json_str)
            if isinstance(data, list):
                return [self._normalize_employee(e) for e in data if isinstance(e, dict)]
        except json.JSONDecodeError:
            pass
        
        # Extract objects one by one
        employees = []
        depth = 0
        obj_start = None
        
        for i, char in enumerate(json_str):
            if char == '{':
                if depth == 0:
                    obj_start = i
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0 and obj_start is not None:
                    obj_str = json_str[obj_start:i + 1]
                    emp = self._try_parse_object(obj_str)
                    if emp:
                        employees.append(emp)
                    obj_start = None
        
        return employees
    
    def _try_parse_object(self, obj_str: str) -> Optional[Dict]:
        """Try to parse a single JSON object."""
        obj_str = re.sub(r',\s*}', '}', obj_str)
        obj_str = re.sub(r',\s*]', ']', obj_str)
        
        try:
            obj = json.loads(obj_str)
            return self._normalize_employee(obj)
        except:
            pass
        
        # Regex fallback for corrupt JSON
        try:
            name_match = re.search(r'"name"\s*:\s*"([^"]*)"', obj_str)
            gross_match = re.search(r'"gross_pay"\s*:\s*([\d.]+)', obj_str)
            
            if name_match or gross_match:
                return {
                    "name": name_match.group(1) if name_match else "",
                    "employee_id": "",
                    "gross_pay": float(gross_match.group(1)) if gross_match else 0.0,
                    "net_pay": 0.0,
                    "earnings": [],
                    "taxes": [],
                    "deductions": []
                }
        except:
            pass
        
        return None
    
    def _normalize_employee(self, data: Dict) -> Dict:
        """Ensure employee dict has all required fields."""
        return {
            "company_name": str(data.get('company_name', '')),
            "client_code": str(data.get('client_code', '')),
            "period_ending": str(data.get('period_ending', '')),
            "check_date": str(data.get('check_date', '')),
            "name": str(data.get('name', '')),
            "employee_id": str(data.get('employee_id', '')),
            "department": str(data.get('department', '')),
            "tax_profile": str(data.get('tax_profile', '')),
            "gross_pay": float(data.get('gross_pay', 0) or 0),
            "net_pay": float(data.get('net_pay', 0) or 0),
            "total_taxes": float(data.get('total_taxes', 0) or 0),
            "total_deductions": float(data.get('total_deductions', 0) or 0),
            "earnings": data.get('earnings') if isinstance(data.get('earnings'), list) else [],
            "taxes": data.get('taxes') if isinstance(data.get('taxes'), list) else [],
            "deductions": data.get('deductions') if isinstance(data.get('deductions'), list) else [],
            "check_number": str(data.get('check_number', '')),
            "pay_method": str(data.get('pay_method', '')),
            "hire_date": str(data.get('hire_date', '')),
            "term_date": str(data.get('term_date', '')),
            "status": str(data.get('status', '')),
            "pay_frequency": str(data.get('pay_frequency', '')),
            "employee_type": str(data.get('employee_type', '')),
            "hourly_rate": float(data.get('hourly_rate', 0) or 0) if data.get('hourly_rate') else None,
            "salary": float(data.get('salary', 0) or 0) if data.get('salary') else None,
            "resident_state": str(data.get('resident_state', '')),
            "work_state": str(data.get('work_state', '')),
            "federal_filing_status": str(data.get('federal_filing_status', '')),
            "state_filing_status": str(data.get('state_filing_status', '')),
            "pay_period_start": str(data.get('pay_period_start', '')),
            "pay_period_end": str(data.get('pay_period_end', '')),
        }
    
    def _validate_employee(self, emp: Dict) -> List[str]:
        """Validate employee record."""
        errors = []
        
        if not emp.get('name'):
            errors.append("Missing employee name")
        
        gross = float(emp.get('gross_pay', 0) or 0)
        net = float(emp.get('net_pay', 0) or 0)
        total_taxes = float(emp.get('total_taxes', 0) or 0)
        total_deductions = float(emp.get('total_deductions', 0) or 0)
        
        # Calculate from line items, excluding payment methods
        calc_taxes = sum(float(t.get('amount', 0) or 0) for t in emp.get('taxes', []) if not t.get('is_employer', False))
        
        payment_methods = ['direct deposit', 'net check', 'check', 'payment']
        real_deductions = [
            d for d in emp.get('deductions', [])
            if not any(pm in str(d.get('description', '')).lower() for pm in payment_methods)
            and not any(pm in str(d.get('type', '')).lower() for pm in payment_methods)
            and not d.get('is_employer', False)
            and d.get('category') != 'memo'
        ]
        calc_deductions = sum(float(d.get('amount', 0) or 0) for d in real_deductions)
        
        # Use totals if provided, otherwise use calculated
        use_taxes = total_taxes if total_taxes > 0 else calc_taxes
        use_deductions = total_deductions if total_deductions > 0 else calc_deductions
        
        if gross > 0 and net > 0:
            calculated_net = gross - use_taxes - use_deductions
            diff = abs(calculated_net - net)
            
            # Allow $1 tolerance OR 1% tolerance for rounding
            tolerance = max(1.00, gross * 0.01)
            
            if diff > tolerance:
                errors.append(f"Net mismatch: gross({gross:.2f}) - taxes({use_taxes:.2f}) - ded({use_deductions:.2f}) = {calculated_net:.2f}, expected {net:.2f}")
        
        return errors
    
    def _fix_descriptions(self, employees: List[Dict], raw_text: str) -> List[Dict]:
        """Post-process to replace truncated descriptions with full text from PDF."""
        lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
        fixes_made = 0
        
        for emp in employees:
            for earning in emp.get('earnings', []):
                old_desc = earning.get('description', '')
                full_desc = self._find_full_description(earning.get('type', ''), old_desc, earning.get('amount', 0), lines)
                if full_desc and len(full_desc) > len(old_desc):
                    earning['description'] = full_desc
                    fixes_made += 1
            
            for tax in emp.get('taxes', []):
                old_desc = tax.get('description', '')
                full_desc = self._find_full_description(tax.get('type', ''), old_desc, tax.get('amount', 0), lines)
                if full_desc and len(full_desc) > len(old_desc):
                    tax['description'] = full_desc
                    fixes_made += 1
            
            for deduction in emp.get('deductions', []):
                old_desc = deduction.get('description', '')
                full_desc = self._find_full_description(deduction.get('type', ''), old_desc, deduction.get('amount', 0), lines)
                if full_desc and len(full_desc) > len(old_desc):
                    deduction['description'] = full_desc
                    fixes_made += 1
        
        logger.info(f"Description fixes made: {fixes_made}")
        return employees
    
    def _find_full_description(self, type_code: str, short_desc: str, amount, lines: List[str]) -> Optional[str]:
        """Find the full description from raw text."""
        # Convert amount to float if it's a string
        try:
            amount = float(amount) if amount else 0
        except (ValueError, TypeError):
            amount = 0
            
        if not amount or amount == 0:
            return None
        
        amount_str = f"{amount:.2f}"
        search_term = short_desc.lower().strip() if short_desc else ""
        type_term = type_code.lower().strip() if type_code else ""
        
        if not search_term and not type_term:
            return None
        
        for i, line in enumerate(lines):
            if amount_str in line:
                line_lower = line.lower()
                if (search_term and search_term in line_lower) or (type_term and type_term in line_lower):
                    return line.strip()
        
        return None


# =============================================================================
# SINGLETON
# =============================================================================

_extractor = None

def get_extractor() -> RegisterExtractor:
    global _extractor
    if _extractor is None:
        _extractor = RegisterExtractor()
    return _extractor


# =============================================================================
# BACKGROUND TASK
# =============================================================================

def process_extraction_job(
    job_id: str, 
    file_path: str, 
    max_pages: int,
    use_textract: bool, 
    project_id: Optional[str],
    vendor_type: str = "unknown", 
    customer_id: Optional[str] = None
):
    """Background task for async extraction."""
    ext = get_extractor()
    
    try:
        result = ext.extract(
            file_path, 
            max_pages=max_pages,
            use_textract=use_textract, 
            job_id=job_id,
            vendor_type=vendor_type,
            project_id=project_id
        )
        
        for emp in result.get('employees', []):
            emp['id'] = emp.get('employee_id', '')
        
        # Save job metadata to Supabase
        if result.get('success'):
            saved = save_extraction_job(
                project_id=project_id,
                source_file=result['source_file'],
                employee_count=result['employee_count'],
                confidence=result['confidence'],
                validation_passed=result['validation_passed'],
                validation_errors=result['validation_errors'],
                pages_processed=result['pages_processed'],
                cost_usd=result['cost_usd'],
                processing_time_ms=result['processing_time_ms'],
                extraction_method=result.get('llm_used', 'unknown'),
                customer_id=customer_id,
                duckdb_table=result.get('duckdb_table')
            )
            result['extract_id'] = saved.get('id') if saved else None
            result['saved_to_db'] = saved is not None
            result['vendor_type'] = vendor_type
        
        update_job(job_id, result=result)
        
    except Exception as e:
        logger.error(f"Background job failed: {e}", exc_info=True)
        update_job(job_id, status='failed', message=str(e))
    
    finally:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                parent = os.path.dirname(file_path)
                if os.path.isdir(parent):
                    shutil.rmtree(parent, ignore_errors=True)
        except:
            pass


# =============================================================================
# ROUTES - Renamed from /vacuum to /register
# =============================================================================

@router.get("/register/status")
async def status():
    ext = get_extractor()
    return {
        "available": ext.is_available,
        "version": "1.0.0",
        "default_method": "PyMuPDF (local, private)",
        "llm_primary": "Local (DeepSeek)" if LLM_ORCHESTRATOR_AVAILABLE else "Claude",
        "llm_fallback": "Claude",
        "duckdb_enabled": DUCKDB_AVAILABLE,
        "pii_redaction": True
    }


@router.post("/register/upload")
async def upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    max_pages: int = Form(0),
    project_id: Optional[str] = Form(None),
    use_textract: bool = Form(False),
    async_mode: bool = Form(True),
    vendor_type: str = Form("unknown"),
    customer_id: Optional[str] = Form(None)
):
    """
    Upload and extract pay register.
    
    NEW: Uses local LLM first, stores to DuckDB for chat integration.
    """
    ext = get_extractor()
    
    if not ext.is_available:
        return {"success": False, "error": "No LLM configured", "employees": [], "employee_count": 0}
    
    if not file.filename.lower().endswith('.pdf'):
        return {"success": False, "error": "Only PDF files supported", "employees": [], "employee_count": 0}
    
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, file.filename)
    
    with open(temp_path, 'wb') as f:
        shutil.copyfileobj(file.file, f)
    
    if async_mode:
        job_id = create_job(file.filename)
        background_tasks.add_task(
            process_extraction_job,
            job_id, temp_path, max_pages, use_textract, project_id,
            vendor_type, customer_id
        )
        
        return {
            "success": True,
            "job_id": job_id,
            "status": "processing",
            "message": f"Processing started. Poll /register/job/{job_id} for status.",
            "extraction_method": "textract" if use_textract else "pymupdf",
            "vendor_type": vendor_type
        }
    else:
        try:
            result = ext.extract(temp_path, max_pages=max_pages, use_textract=use_textract, project_id=project_id)
            
            for emp in result.get('employees', []):
                emp['id'] = emp.get('employee_id', '')
            
            if result.get('success'):
                saved = save_extraction_job(
                    project_id=project_id,
                    source_file=result['source_file'],
                    employee_count=result['employee_count'],
                    confidence=result['confidence'],
                    validation_passed=result['validation_passed'],
                    validation_errors=result['validation_errors'],
                    pages_processed=result['pages_processed'],
                    cost_usd=result['cost_usd'],
                    processing_time_ms=result['processing_time_ms'],
                    extraction_method=result.get('llm_used', 'unknown'),
                    duckdb_table=result.get('duckdb_table')
                )
                result['extract_id'] = saved.get('id') if saved else None
                result['saved_to_db'] = saved is not None
            
            return result
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


@router.get("/register/job/{job_id}")
async def get_job_status(job_id: str):
    """Get status of an async extraction job."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/register/extract")
async def extract(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    max_pages: int = Form(0),
    project_id: Optional[str] = Form(None),
    use_textract: bool = Form(False),
    async_mode: bool = Form(True)
):
    """Alias for /register/upload"""
    return await upload(background_tasks, file, max_pages, project_id, use_textract, async_mode)


@router.get("/register/extracts")
async def get_extracts_list(project_id: Optional[str] = None, limit: int = 50):
    """Get extraction history"""
    extracts = get_extractions(project_id=project_id, limit=limit)
    
    return {
        "extracts": [
            {
                "id": e.get('id'),
                "source_file": e.get('source_file'),
                "employee_count": e.get('employee_count'),
                "confidence": e.get('confidence'),
                "validation_passed": e.get('validation_passed'),
                "pages_processed": e.get('pages_processed'),
                "cost_usd": e.get('cost_usd'),
                "extraction_method": e.get('extraction_method', 'unknown'),
                "duckdb_table": e.get('duckdb_table'),
                "created_at": e.get('created_at')
            }
            for e in extracts
        ],
        "total": len(extracts)
    }


@router.get("/register/extract/{extract_id}")
async def get_extract(extract_id: str):
    """Get full extraction details"""
    extraction = get_extraction_by_id(extract_id)
    if not extraction:
        return {"error": "Extraction not found"}
    return extraction


@router.get("/register/extract/{extract_id}/raw")
async def get_extract_raw_text(extract_id: str):
    """Get raw extracted text for review."""
    supabase = get_supabase()
    if not supabase:
        return {"error": "Database not available", "raw_text": ""}
    
    try:
        response = supabase.table('extraction_jobs').select('source_file, raw_text').eq('id', extract_id).execute()
        if not response.data:
            return {"error": "Extraction not found", "raw_text": ""}
        
        raw_text = response.data[0].get('raw_text', '')
        if not raw_text:
            return {
                "raw_text": "Raw text not available.",
                "source_file": response.data[0].get('source_file', '')
            }
        
        return {
            "raw_text": raw_text,
            "source_file": response.data[0].get('source_file', '')
        }
    except Exception as e:
        logger.error(f"Failed to get raw text: {e}")
        return {"error": str(e), "raw_text": ""}


@router.delete("/register/extract/{extract_id}")
async def delete_extract(extract_id: str):
    """Delete an extraction"""
    success = delete_extraction(extract_id)
    return {"success": success, "id": extract_id}


@router.get("/register/health")
async def health():
    return {
        "status": "ok", 
        "timestamp": datetime.now().isoformat(),
        "duckdb": DUCKDB_AVAILABLE,
        "local_llm": LLM_ORCHESTRATOR_AVAILABLE
    }


# =============================================================================
# BACKWARD COMPATIBILITY - Keep /vacuum routes working
# =============================================================================

@router.get("/vacuum/status")
async def vacuum_status():
    """Backward compatibility for /vacuum/status"""
    return await status()

@router.post("/vacuum/upload")
async def vacuum_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    max_pages: int = Form(0),
    project_id: Optional[str] = Form(None),
    use_textract: bool = Form(False),
    async_mode: bool = Form(True),
    vendor_type: str = Form("unknown"),
    customer_id: Optional[str] = Form(None)
):
    """Backward compatibility for /vacuum/upload"""
    return await upload(background_tasks, file, max_pages, project_id, use_textract, async_mode, vendor_type, customer_id)

@router.get("/vacuum/job/{job_id}")
async def vacuum_job_status(job_id: str):
    """Backward compatibility for /vacuum/job"""
    return await get_job_status(job_id)

@router.get("/vacuum/extracts")
async def vacuum_extracts(project_id: Optional[str] = None, limit: int = 50):
    """Backward compatibility for /vacuum/extracts"""
    return await get_extracts_list(project_id, limit)

@router.get("/vacuum/extract/{extract_id}")
async def vacuum_extract(extract_id: str):
    """Backward compatibility for /vacuum/extract"""
    return await get_extract(extract_id)

@router.delete("/vacuum/extract/{extract_id}")
async def vacuum_delete(extract_id: str):
    """Backward compatibility for /vacuum/extract delete"""
    return await delete_extract(extract_id)

@router.get("/vacuum/health")
async def vacuum_health():
    """Backward compatibility for /vacuum/health"""
    return await health()
