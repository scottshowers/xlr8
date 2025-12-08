"""
Vacuum Router - All In One v11
==============================
Privacy-First Architecture:
- PyMuPDF for local text extraction (default)
- PII redaction BEFORE sending to Claude
- Textract as optional fallback for scanned PDFs
- Async background job support

Deploy to: backend/routers/vacuum.py
Requirements: pip install pymupdf anthropic boto3
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

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# PII REDACTION
# =============================================================================

class PIIRedactor:
    """Redact PII before sending to Claude."""
    
    # Patterns to redact
    PATTERNS = {
        'ssn': [
            r'\b\d{3}-\d{2}-\d{4}\b',           # 123-45-6789
            r'\b\d{3}\s\d{2}\s\d{4}\b',         # 123 45 6789
            r'\b\d{9}\b(?=.*(?:ssn|social))',   # 123456789 near SSN context
        ],
        'bank_account': [
            r'\b\d{8,17}\b(?=.*(?:account|acct|routing|aba))',  # Account numbers
            r'\b\d{9}\b(?=.*(?:routing|aba))',                   # Routing numbers
        ],
        'credit_card': [
            r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',  # 1234-5678-9012-3456
        ],
    }
    
    # Placeholders
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
# SUPABASE STORAGE
# =============================================================================

def get_supabase():
    """Get Supabase client"""
    try:
        from utils.supabase_client import get_supabase as _get_supabase
        return _get_supabase()
    except ImportError:
        try:
            from backend.utils.supabase_client import get_supabase as _get_supabase
            return _get_supabase()
        except ImportError:
            logger.warning("Supabase client not available")
            return None


def save_extraction(project_id: Optional[str], source_file: str, 
                    employees: List[Dict], confidence: float,
                    validation_passed: bool, validation_errors: List[str],
                    pages_processed: int, cost_usd: float, 
                    processing_time_ms: int, extraction_method: str = "pymupdf",
                    customer_id: Optional[str] = None,
                    raw_text: Optional[str] = None) -> Optional[Dict]:
    """Save extraction results to normalized Supabase tables.
    
    Writes to:
    - extraction_jobs (header)
    - extraction_employees (each employee)
    - extraction_earnings/taxes/deductions (line items)
    
    Returns the same format as before for API compatibility.
    """
    supabase = get_supabase()
    if not supabase:
        logger.warning("Cannot save - Supabase not available")
        return None
    
    # Use default customer if none specified
    if not customer_id:
        customer_id = '00000000-0000-0000-0000-000000000001'
    
    try:
        # Extract header info from first employee if available
        first_emp = employees[0] if employees else {}
        
        # 1. Insert extraction job (header)
        job_data = {
            'customer_id': customer_id,
            'project_id': project_id,
            'source_file': source_file,
            'company_name': first_emp.get('company_name', ''),
            'client_code': first_emp.get('client_code', ''),
            'check_date': _parse_date(first_emp.get('check_date')),
            'pay_period_end': _parse_date(first_emp.get('period_ending')),
            'employee_count': len(employees),
            'confidence': confidence,
            'validation_passed': validation_passed,
            'validation_errors': validation_errors,
            'pages_processed': pages_processed,
            'cost_usd': cost_usd,
            'processing_time_ms': processing_time_ms,
            'extraction_method': extraction_method,
            'status': 'completed',
            'completed_at': datetime.now().isoformat(),
            'raw_text': raw_text[:500000] if raw_text else None  # Limit to 500KB
        }
        
        job_response = supabase.table('extraction_jobs').insert(job_data).execute()
        if not job_response.data:
            logger.error("Failed to insert extraction job")
            return None
        
        extraction_id = job_response.data[0]['id']
        
        # 2. Insert each employee and their line items
        for sort_order, emp in enumerate(employees):
            emp_data = {
                'extraction_id': extraction_id,
                'customer_id': customer_id,
                'name': emp.get('name', ''),
                'employee_id': emp.get('employee_id', ''),
                'department': emp.get('department', ''),
                'tax_profile': emp.get('tax_profile', ''),
                'company_name': emp.get('company_name', ''),
                'client_code': emp.get('client_code', ''),
                'period_ending': emp.get('period_ending', ''),
                'check_date': emp.get('check_date', ''),
                'gross_pay': _safe_decimal(emp.get('gross_pay')),
                'net_pay': _safe_decimal(emp.get('net_pay')),
                'total_taxes': _safe_decimal(emp.get('total_taxes')),
                'total_deductions': _safe_decimal(emp.get('total_deductions')),
                'gross_pay_ytd': _safe_decimal(emp.get('gross_pay_ytd')),
                'net_pay_ytd': _safe_decimal(emp.get('net_pay_ytd')),
                'check_number': emp.get('check_number', ''),
                'pay_method': emp.get('pay_method', ''),
                'is_valid': emp.get('is_valid', True),
                'validation_errors': emp.get('validation_errors', []),
                'sort_order': sort_order,
                # New demographic fields
                'hire_date': emp.get('hire_date', ''),
                'term_date': emp.get('term_date', ''),
                'status': emp.get('status', ''),
                'pay_frequency': emp.get('pay_frequency', ''),
                'employee_type': emp.get('employee_type', ''),
                'hourly_rate': _safe_decimal(emp.get('hourly_rate')),
                'salary': _safe_decimal(emp.get('salary')),
                'resident_state': emp.get('resident_state', ''),
                'work_state': emp.get('work_state', ''),
                'federal_filing_status': emp.get('federal_filing_status', ''),
                'state_filing_status': emp.get('state_filing_status', ''),
                'pay_period_start': emp.get('pay_period_start', ''),
                'pay_period_end': emp.get('pay_period_end', ''),
            }
            
            emp_response = supabase.table('extraction_employees').insert(emp_data).execute()
            if not emp_response.data:
                logger.warning(f"Failed to insert employee: {emp.get('name')}")
                continue
            
            employee_id = emp_response.data[0]['id']
            
            # 3. Insert earnings
            for earn_order, earning in enumerate(emp.get('earnings', [])):
                earn_data = {
                    'employee_id': employee_id,
                    'extraction_id': extraction_id,
                    'customer_id': customer_id,
                    'type': earning.get('type', ''),
                    'description': earning.get('description', ''),
                    'amount': _safe_decimal(earning.get('amount')),
                    'hours': _safe_decimal(earning.get('hours')),
                    'rate': _safe_decimal(earning.get('rate')),
                    'amount_ytd': _safe_decimal(earning.get('amount_ytd')),
                    'hours_ytd': _safe_decimal(earning.get('hours_ytd')),
                    'sort_order': earn_order
                }
                supabase.table('extraction_earnings').insert(earn_data).execute()
            
            # 4. Insert taxes
            for tax_order, tax in enumerate(emp.get('taxes', [])):
                tax_data = {
                    'employee_id': employee_id,
                    'extraction_id': extraction_id,
                    'customer_id': customer_id,
                    'type': tax.get('type', ''),
                    'description': tax.get('description', ''),
                    'amount': _safe_decimal(tax.get('amount')),
                    'taxable_wages': _safe_decimal(tax.get('taxable_wages')),
                    'amount_ytd': _safe_decimal(tax.get('amount_ytd')),
                    'taxable_wages_ytd': _safe_decimal(tax.get('taxable_wages_ytd')),
                    'is_employer': tax.get('is_employer', False),
                    'sort_order': tax_order
                }
                supabase.table('extraction_taxes').insert(tax_data).execute()
            
            # 5. Insert deductions
            for ded_order, ded in enumerate(emp.get('deductions', [])):
                ded_data = {
                    'employee_id': employee_id,
                    'extraction_id': extraction_id,
                    'customer_id': customer_id,
                    'type': ded.get('type', ''),
                    'description': ded.get('description', ''),
                    'amount': _safe_decimal(ded.get('amount')),
                    'amount_ytd': _safe_decimal(ded.get('amount_ytd')),
                    'category': ded.get('category', ''),
                    'sort_order': ded_order
                }
                supabase.table('extraction_deductions').insert(ded_data).execute()
        
        logger.info(f"Saved extraction: {source_file} with {len(employees)} employees to normalized tables")
        
        # Return format compatible with old API
        return {
            'id': extraction_id,
            'project_id': project_id,
            'source_file': source_file,
            'employee_count': len(employees),
            'created_at': job_response.data[0].get('created_at')
        }
        
    except Exception as e:
        logger.error(f"Failed to save extraction: {e}")
        return None


def _parse_date(date_str: Optional[str]) -> Optional[str]:
    """Parse date string to ISO format for Supabase."""
    if not date_str:
        return None
    try:
        # Try common formats
        for fmt in ['%m/%d/%Y', '%Y-%m-%d', '%m-%d-%Y']:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        return None
    except Exception:
        return None


def _safe_decimal(value) -> Optional[float]:
    """Safely convert value to decimal/float for Supabase."""
    if value is None:
        return None
    try:
        if isinstance(value, str):
            value = value.replace(',', '').replace('$', '')
        return float(value)
    except (ValueError, TypeError):
        return None


def get_extractions(project_id: Optional[str] = None, limit: int = 50, 
                   customer_id: Optional[str] = None) -> List[Dict]:
    """Get extraction history from normalized tables.
    
    Returns data in the same format as before for API compatibility.
    """
    supabase = get_supabase()
    if not supabase:
        return []
    
    try:
        query = supabase.table('extraction_jobs').select('*').order('created_at', desc=True).limit(limit)
        if project_id:
            query = query.eq('project_id', project_id)
        if customer_id:
            query = query.eq('customer_id', customer_id)
        response = query.execute()
        
        if not response.data:
            return []
        
        # Convert to old format for compatibility
        results = []
        for job in response.data:
            results.append({
                'id': job['id'],
                'project_id': job.get('project_id'),
                'source_file': job.get('source_file'),
                'employee_count': job.get('employee_count', 0),
                'confidence': job.get('confidence', 0),
                'validation_passed': job.get('validation_passed', False),
                'validation_errors': job.get('validation_errors', []),
                'pages_processed': job.get('pages_processed', 0),
                'cost_usd': job.get('cost_usd', 0),
                'processing_time_ms': job.get('processing_time_ms', 0),
                'extraction_method': job.get('extraction_method'),
                'created_at': job.get('created_at')
            })
        
        return results
    except Exception as e:
        logger.error(f"Failed to get extractions: {e}")
        return []


def get_extraction_by_id(extract_id: str) -> Optional[Dict]:
    """Get single extraction by ID with all employees and line items.
    
    Reassembles the nested JSON structure from normalized tables.
    """
    supabase = get_supabase()
    if not supabase:
        return None
    
    try:
        # Get the job
        job_response = supabase.table('extraction_jobs').select('*').eq('id', extract_id).execute()
        if not job_response.data:
            return None
        
        job = job_response.data[0]
        
        # Get employees
        emp_response = supabase.table('extraction_employees').select('*').eq('extraction_id', extract_id).order('sort_order').execute()
        employees = []
        
        for emp in (emp_response.data or []):
            employee_id = emp['id']
            
            # Get earnings
            earn_response = supabase.table('extraction_earnings').select('*').eq('employee_id', employee_id).order('sort_order').execute()
            earnings = [{
                'type': e.get('type', ''),
                'description': e.get('description', ''),
                'amount': float(e.get('amount') or 0),
                'hours': float(e.get('hours') or 0) if e.get('hours') else None,
                'rate': float(e.get('rate') or 0) if e.get('rate') else None,
                'amount_ytd': float(e.get('amount_ytd') or 0) if e.get('amount_ytd') else None,
            } for e in (earn_response.data or [])]
            
            # Get taxes
            tax_response = supabase.table('extraction_taxes').select('*').eq('employee_id', employee_id).order('sort_order').execute()
            taxes = [{
                'type': t.get('type', ''),
                'description': t.get('description', ''),
                'amount': float(t.get('amount') or 0),
                'taxable_wages': float(t.get('taxable_wages') or 0) if t.get('taxable_wages') else None,
                'amount_ytd': float(t.get('amount_ytd') or 0) if t.get('amount_ytd') else None,
                'is_employer': t.get('is_employer', False),
            } for t in (tax_response.data or [])]
            
            # Get deductions
            ded_response = supabase.table('extraction_deductions').select('*').eq('employee_id', employee_id).order('sort_order').execute()
            deductions = [{
                'type': d.get('type', ''),
                'description': d.get('description', ''),
                'amount': float(d.get('amount') or 0),
                'amount_ytd': float(d.get('amount_ytd') or 0) if d.get('amount_ytd') else None,
                'category': d.get('category', ''),
            } for d in (ded_response.data or [])]
            
            employees.append({
                'id': emp.get('employee_id', ''),
                'name': emp.get('name', ''),
                'employee_id': emp.get('employee_id', ''),
                'department': emp.get('department', ''),
                'tax_profile': emp.get('tax_profile', ''),
                'company_name': emp.get('company_name', ''),
                'client_code': emp.get('client_code', ''),
                'period_ending': emp.get('period_ending', ''),
                'check_date': emp.get('check_date', ''),
                'gross_pay': float(emp.get('gross_pay') or 0),
                'net_pay': float(emp.get('net_pay') or 0),
                'total_taxes': float(emp.get('total_taxes') or 0),
                'total_deductions': float(emp.get('total_deductions') or 0),
                'check_number': emp.get('check_number', ''),
                'pay_method': emp.get('pay_method', ''),
                'is_valid': emp.get('is_valid', True),
                'validation_errors': emp.get('validation_errors', []),
                # Demographic fields
                'hire_date': emp.get('hire_date', ''),
                'term_date': emp.get('term_date', ''),
                'status': emp.get('status', ''),
                'pay_frequency': emp.get('pay_frequency', ''),
                'employee_type': emp.get('employee_type', ''),
                'hourly_rate': float(emp.get('hourly_rate') or 0) if emp.get('hourly_rate') else None,
                'salary': float(emp.get('salary') or 0) if emp.get('salary') else None,
                'resident_state': emp.get('resident_state', ''),
                'work_state': emp.get('work_state', ''),
                'federal_filing_status': emp.get('federal_filing_status', ''),
                'state_filing_status': emp.get('state_filing_status', ''),
                'pay_period_start': emp.get('pay_period_start', ''),
                'pay_period_end': emp.get('pay_period_end', ''),
                'earnings': earnings,
                'taxes': taxes,
                'deductions': deductions
            })
        
        # Return in old format for compatibility
        return {
            'id': job['id'],
            'project_id': job.get('project_id'),
            'source_file': job.get('source_file'),
            'employee_count': job.get('employee_count', 0),
            'employees': employees,
            'confidence': job.get('confidence', 0),
            'validation_passed': job.get('validation_passed', False),
            'validation_errors': job.get('validation_errors', []),
            'pages_processed': job.get('pages_processed', 0),
            'cost_usd': float(job.get('cost_usd') or 0),
            'processing_time_ms': job.get('processing_time_ms', 0),
            'extraction_method': job.get('extraction_method'),
            'created_at': job.get('created_at')
        }
        
    except Exception as e:
        logger.error(f"Failed to get extraction: {e}")
        return None


def delete_extraction(extract_id: str) -> bool:
    """Delete an extraction and all related data.
    
    CASCADE delete handles employees and line items automatically.
    """
    supabase = get_supabase()
    if not supabase:
        return False
    
    try:
        supabase.table('extraction_jobs').delete().eq('id', extract_id).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to delete extraction: {e}")
        return False


# =============================================================================
# JOB TRACKING (for async processing)
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

class VacuumExtractor:
    """
    Privacy-first extractor:
    - PyMuPDF for local text extraction (default)
    - PII redaction before Claude
    - Textract as fallback for scanned PDFs
    """
    
    def __init__(self):
        self.claude_api_key = os.environ.get('CLAUDE_API_KEY')
        self.aws_region = os.environ.get('AWS_REGION', 'us-east-1')
        self._textract = None
        self._claude = None
        self.redactor = PIIRedactor()
    
    @property
    def is_available(self) -> bool:
        return bool(self.claude_api_key)
    
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
    
    def extract(self, file_path: str, max_pages: int = 0, 
                use_textract: bool = False, job_id: str = None,
                vendor_type: str = "unknown") -> Dict:
        """
        Extract employee pay data from PDF.
        
        Args:
            file_path: Path to PDF file
            max_pages: Max pages to process (0 = all)
            use_textract: If True, use AWS Textract instead of PyMuPDF
            job_id: Optional job ID for progress tracking
            vendor_type: Vendor type for prompt selection (paycom, dayforce, adp, etc.)
        """
        start = datetime.now()
        filename = os.path.basename(file_path)
        method = "textract" if use_textract else "pymupdf"
        
        try:
            # Step 1: Extract text
            if job_id:
                update_job(job_id, status='processing', message='Extracting text from PDF...')
            
            if use_textract:
                logger.info(f"Using Textract for OCR extraction...")
                pages_text, pages_processed = self._extract_with_textract(file_path, max_pages, job_id)
            else:
                logger.info(f"Using PyMuPDF for local extraction (privacy-compliant)...")
                # For auto-detect, do a quick first page scan
                if vendor_type == "unknown":
                    quick_text = self._quick_vendor_detect(file_path)
                    vendor_type = self._detect_vendor([quick_text]) if quick_text else "unknown"
                    logger.info(f"Quick vendor detection: {vendor_type}")
                
                pages_text, pages_processed = self._extract_with_pymupdf(file_path, max_pages, job_id, vendor_type)
            
            if not pages_text:
                raise ValueError("No text extracted from PDF")
            
            # Confirm/update vendor detection if still unknown
            if vendor_type == "unknown":
                vendor_type = self._detect_vendor(pages_text)
                logger.info(f"Auto-detected vendor: {vendor_type}")
            
            # Step 2: Redact PII
            if job_id:
                update_job(job_id, message='Redacting sensitive data...')
            
            logger.info("Redacting PII before sending to Claude...")
            redacted_pages = [self.redactor.redact(page) for page in pages_text]
            redaction_stats = self.redactor.get_stats()
            logger.info(f"PII Redaction: {redaction_stats}")
            
            # Step 3: Parse with Claude (redacted text only)
            if job_id:
                update_job(job_id, message=f'Parsing with AI ({vendor_type})...', progress=80)
            
            logger.info("Sending REDACTED text to Claude for parsing...")
            employees = self._parse_with_claude(redacted_pages, vendor_type)
            
            # Step 3.5: Fix truncated descriptions using ORIGINAL text
            # Skip for Dayforce - the post-processing grabs YTD amounts incorrectly
            if vendor_type != 'dayforce':
                original_text = "\n\n--- PAGE BREAK ---\n\n".join(pages_text)
                employees = self._fix_descriptions(employees, original_text)
            else:
                logger.info("Skipping description fix for Dayforce (causes YTD confusion)")
            
            # Step 4: Validate employees
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
            
            # Cost calculation
            if use_textract:
                cost = (pages_processed * 0.015) + 0.05  # Textract + Claude
            else:
                cost = 0.05  # Claude only (PyMuPDF is free)
            
            processing_time = int((datetime.now() - start).total_seconds() * 1000)
            
            # Join pages for raw_text storage
            raw_text = "\n\n--- PAGE BREAK ---\n\n".join(pages_text)
            
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
                "pii_redacted": redaction_stats['total_redacted'],
                "privacy_compliant": True,
                "raw_text": raw_text
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
                "privacy_compliant": True
            }
            
            if job_id:
                update_job(job_id, status='failed', message=str(e), result=error_result)
            
            return error_result
    
    def _extract_with_pymupdf(self, file_path: str, max_pages: int, job_id: str = None, vendor_type: str = "unknown") -> tuple:
        """Extract text using PyMuPDF (local, free, private)."""
        import fitz
        
        pages_text = []
        doc = fitz.open(file_path)
        
        try:
            total = len(doc)
            to_process = total if max_pages == 0 else min(max_pages, total)
            
            if job_id:
                update_job(job_id, total_pages=to_process)
            
            for page_num in range(to_process):
                page = doc[page_num]
                
                # For Dayforce, use column-aware extraction
                if vendor_type == 'dayforce':
                    text = self._extract_dayforce_page(page)
                else:
                    text = page.get_text()
                
                if text.strip():
                    pages_text.append(text)
                else:
                    # Page has no selectable text - might be scanned
                    logger.warning(f"Page {page_num + 1} has no text - may need Textract")
                    pages_text.append(f"[Page {page_num + 1}: No extractable text - consider Textract]")
                
                if job_id:
                    progress = int((page_num + 1) / to_process * 70)
                    update_job(job_id, current_page=page_num + 1, progress=progress,
                              message=f'Extracting page {page_num + 1} of {to_process}...')
                
                logger.info(f"PyMuPDF: Extracted page {page_num + 1}/{to_process}")
                
        finally:
            doc.close()
        
        return pages_text, len(pages_text)
    
    def _extract_dayforce_page(self, page) -> str:
        """Extract Dayforce page with column awareness using x-coordinates.
        
        Dayforce has these approximate column regions (x-coordinates):
        - Employee Info: 0-100
        - Earnings: 100-400 (Description, Rate, Hours, Amount, HoursYTD, AmountYTD)
        - Taxes: 400-600 (Description, Wages, Amount, WagesYTD, AmountYTD)
        - Deductions: 600-800 (Description, Scheduled, Amount, AmountYTD)
        - Net Pay: 800+
        
        For earnings, we need to distinguish current vs YTD based on x-position.
        """
        # Get text with position info
        blocks = page.get_text("dict")["blocks"]
        
        # Collect all text spans with positions
        spans = []
        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if text:
                            bbox = span.get("bbox", [0, 0, 0, 0])
                            spans.append({
                                "text": text,
                                "x": bbox[0],
                                "y": bbox[1],
                                "x2": bbox[2]
                            })
        
        # Sort by y (top to bottom), then x (left to right)
        spans.sort(key=lambda s: (round(s["y"] / 5) * 5, s["x"]))  # Group by ~5px rows
        
        # Build structured output with column markers
        # Detect column boundaries from header row
        earnings_cols = self._detect_earnings_columns(spans)
        
        lines = []
        current_y = -1
        current_line = []
        
        for span in spans:
            y_group = round(span["y"] / 5) * 5
            
            if y_group != current_y:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = []
                current_y = y_group
            
            # Add column marker for earnings section based on x position
            text = span["text"]
            x = span["x"]
            
            # Mark YTD values in earnings section (approximate x-ranges)
            # These will vary by document but the pattern is consistent
            if earnings_cols:
                if earnings_cols.get("hours_ytd_x") and abs(x - earnings_cols["hours_ytd_x"]) < 20:
                    text = f"[HYTD]{text}"
                elif earnings_cols.get("amount_ytd_x") and abs(x - earnings_cols["amount_ytd_x"]) < 20:
                    text = f"[AYTD]{text}"
                elif earnings_cols.get("amount_x") and abs(x - earnings_cols["amount_x"]) < 20:
                    text = f"[AMT]{text}"
                elif earnings_cols.get("hours_x") and abs(x - earnings_cols["hours_x"]) < 20:
                    text = f"[HRS]{text}"
            
            current_line.append(text)
        
        if current_line:
            lines.append(" ".join(current_line))
        
        return "\n".join(lines)
    
    def _detect_earnings_columns(self, spans) -> dict:
        """Detect column x-positions from header row."""
        cols = {}
        
        for span in spans:
            text = span["text"].lower()
            x = span["x"]
            
            if text == "hoursytd":
                cols["hours_ytd_x"] = x
            elif text == "amountytd" and "hours_ytd_x" in cols:
                cols["amount_ytd_x"] = x
            elif text == "amount" and "amount_ytd_x" not in cols:
                cols["amount_x"] = x
            elif text == "hours" and "hours_ytd_x" not in cols:
                cols["hours_x"] = x
        
        return cols
    
    def _extract_with_textract(self, file_path: str, max_pages: int, job_id: str = None) -> tuple:
        """Extract text using AWS Textract (for scanned PDFs)."""
        import fitz
        
        pages_text = []
        doc = fitz.open(file_path)
        
        try:
            total = len(doc)
            to_process = total if max_pages == 0 else min(max_pages, total)
            
            if job_id:
                update_job(job_id, total_pages=to_process)
            
            for page_num in range(to_process):
                page = doc[page_num]
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img_bytes = pix.tobytes("png")
                
                response = self.textract.analyze_document(
                    Document={'Bytes': img_bytes},
                    FeatureTypes=['TABLES']
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
                
                logger.info(f"Textract: Extracted page {page_num + 1}/{to_process}")
            
            # Log Textract cost
            try:
                from backend.utils.cost_tracker import log_cost, CostService
                log_cost(
                    service=CostService.TEXTRACT,
                    operation="vacuum",
                    pages=len(pages_text),
                    textract_type="analyze",  # AnalyzeDocument with TABLES
                    metadata={"file": file_path.split('/')[-1]}
                )
            except Exception as cost_err:
                logger.debug(f"Cost tracking failed: {cost_err}")
                
        finally:
            doc.close()
        
        return pages_text, len(pages_text)
    
    def _parse_with_claude(self, pages_text: List[str], vendor_type: str = "unknown") -> List[Dict]:
        """Send REDACTED text to Claude for parsing using vendor-specific prompt."""
        
        full_text = "\n\n--- PAGE BREAK ---\n\n".join(pages_text)
        
        # Conservative limit - can increase once chunking is implemented
        if len(full_text) > 80000:
            logger.warning(f"Text too long ({len(full_text)}), truncating to 80k chars")
            full_text = full_text[:80000]
        
        logger.info(f"Sending {len(full_text)} characters to Claude ({len(pages_text)} pages), vendor: {vendor_type}")
        
        # Get vendor-specific prompt from database, fall back to default
        prompt_template = self._get_vendor_prompt(vendor_type)
        
        # Build the full prompt with data
        prompt = self._build_prompt(prompt_template, full_text, vendor_type)

        try:
            response_text = ""
            with self.claude.messages.stream(
                model="claude-sonnet-4-20250514",
                max_tokens=64000,
                temperature=0,  # Deterministic output - same input = same output
                messages=[{"role": "user", "content": prompt}]
            ) as stream:
                for text in stream.text_stream:
                    response_text += text
                
                # Get final message for usage stats
                try:
                    final_message = stream.get_final_message()
                    if final_message and hasattr(final_message, 'usage'):
                        from backend.utils.cost_tracker import log_cost, CostService
                        log_cost(
                            service=CostService.CLAUDE,
                            operation="vacuum",
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
    
    def _get_vendor_prompt(self, vendor_type: str) -> str:
        """Load vendor-specific prompt from database, with fallback to default."""
        supabase = get_supabase()
        
        if supabase:
            try:
                response = supabase.table('vendor_prompts').select('prompt_template').eq('vendor_type', vendor_type).eq('is_active', True).execute()
                if response.data:
                    logger.info(f"Loaded prompt for vendor: {vendor_type}")
                    return response.data[0]['prompt_template']
            except Exception as e:
                logger.warning(f"Failed to load vendor prompt: {e}")
        
        # Fallback to default prompt
        logger.info(f"Using default prompt for vendor: {vendor_type}")
        return self._get_default_prompt()
    
    def _get_default_prompt(self) -> str:
        """Default prompt template - works for most register formats."""
        return """IMPORTANT - READ FIRST:
When extracting earnings, taxes, and deductions, the "description" field must be the EXACT TEXT from the document.
Copy each description EXACTLY as written, character for character.

STRICT RULES:
1. Return ONLY a valid JSON array - no markdown, no explanation
2. Each employee object must have these EXACT keys:
   company_name, client_code, period_ending, check_date, name, employee_id, department, tax_profile, gross_pay, net_pay, total_taxes, total_deductions, earnings, taxes, deductions, check_number, pay_method
3. earnings array: objects with type, description, amount, hours, rate, amount_ytd, hours_ytd
4. taxes array: objects with type, description, amount, taxable_wages, amount_ytd, is_employer (true if employer-paid)
5. deductions array: objects with type, description, amount, amount_ytd, category (pre_tax, post_tax, or memo)
6. Use 0 for missing numbers, "" for missing strings, [] for missing arrays
7. Ignore [REDACTED] placeholders

Extract all employees and return as JSON array."""
    
    def _build_prompt(self, template: str, full_text: str, vendor_type: str) -> str:
        """Build the complete prompt with data and vendor-specific instructions."""
        
        # Base structure
        prompt = f"""{template}

DATA TO EXTRACT:
{full_text}

Return the JSON array now:"""
        
        return prompt
    
    def _quick_vendor_detect(self, file_path: str) -> str:
        """Quick first-page scan for vendor detection before full extraction."""
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
        
        # Combine first few pages for detection
        sample_text = "\n".join(pages_text[:3]).lower()
        
        # Vendor signatures
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
                    logger.info(f"Detected vendor '{vendor}' from signature '{sig}'")
                    return vendor
        
        # Fallback: check for common patterns
        if 'emp #:' in sample_text and 'dept:' in sample_text:
            return 'dayforce'  # Dayforce-style employee info block
        
        if 'code:' in sample_text and 'tax profile:' in sample_text:
            return 'paycom'  # Paycom-style
        
        return 'unknown'

    def _fix_descriptions(self, employees: List[Dict], raw_text: str) -> List[Dict]:
        """Post-process to replace truncated descriptions with full text from PDF."""
        
        # Build a list of all lines
        lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
        print(f"[VACUUM] Raw text has {len(lines)} lines for description matching", flush=True)
        logger.info(f"Raw text has {len(lines)} lines for description matching")
        
        fixes_made = 0
        
        for emp in employees:
            # Fix earnings descriptions
            for earning in emp.get('earnings', []):
                old_desc = earning.get('description', '')
                full_desc = self._find_full_description(
                    earning.get('type', ''),
                    old_desc,
                    earning.get('amount', 0),
                    lines
                )
                if full_desc:
                    # Only fix if new description is LONGER (don't make things worse)
                    if len(full_desc) > len(old_desc):
                        print(f"[FIX] Earning: '{old_desc}' -> '{full_desc}'", flush=True)
                        earning['description'] = full_desc
                        fixes_made += 1
            
            # Fix taxes descriptions
            for tax in emp.get('taxes', []):
                old_desc = tax.get('description', '')
                full_desc = self._find_full_description(
                    tax.get('type', ''),
                    old_desc,
                    tax.get('amount', 0),
                    lines
                )
                if full_desc:
                    # Only fix if new description is LONGER
                    if len(full_desc) > len(old_desc):
                        print(f"[FIX] Tax: '{old_desc}' -> '{full_desc}'", flush=True)
                        tax['description'] = full_desc
                        fixes_made += 1
            
            # Fix deductions descriptions
            for deduction in emp.get('deductions', []):
                old_desc = deduction.get('description', '')
                full_desc = self._find_full_description(
                    deduction.get('type', ''),
                    old_desc,
                    deduction.get('amount', 0),
                    lines
                )
                if full_desc:
                    # Only fix if new description is LONGER
                    if len(full_desc) > len(old_desc):
                        print(f"[FIX] Deduction: '{old_desc}' -> '{full_desc}'", flush=True)
                        deduction['description'] = full_desc
                        fixes_made += 1
        
        print(f"[VACUUM] Description fixes made: {fixes_made}", flush=True)
        logger.info(f"Description fixes made: {fixes_made}")
        return employees
    
    def _find_full_description(self, type_code: str, short_desc: str, amount: float, lines: List[str]) -> Optional[str]:
        """Find the full description from raw text by matching amount and partial text."""
        
        if not amount or amount == 0:
            return None
        
        # Format amount for matching
        amount_str = f"{amount:.2f}"
        amount_with_comma = f"{amount:,.2f}"
        
        # Get search terms from both type and description
        search_term = short_desc.lower().strip() if short_desc else ""
        type_term = type_code.lower().strip() if type_code else ""
        
        if not search_term and not type_term:
            return None
        
        # First, find all lines that contain the amount
        amount_line_indices = []
        for i, line in enumerate(lines):
            if amount_str in line or amount_with_comma in line:
                amount_line_indices.append(i)
        
        print(f"[DEBUG] Looking for '{short_desc}'/'{type_code}' amount={amount_str}, found {len(amount_line_indices)} amount matches", flush=True)
        
        # For each amount match, look backwards for the description line
        for amt_idx in amount_line_indices:
            # Look at the 5 lines BEFORE the amount line
            for j in range(max(0, amt_idx - 5), amt_idx + 1):
                line = lines[j]
                line_lower = line.lower()
                
                # Skip lines that are just numbers
                if line.replace(',', '').replace('.', '').replace('-', '').isdigit():
                    continue
                    
                # Check if this line contains our search term or type
                if search_term and search_term in line_lower:
                    print(f"[DEBUG] MATCH: '{search_term}' found in '{line}'", flush=True)
                    return self._build_full_description(lines, j)
                if type_term and type_term in line_lower:
                    print(f"[DEBUG] MATCH: '{type_term}' found in '{line}'", flush=True)
                    return self._build_full_description(lines, j)
                    
                # Also try if line STARTS with what we're looking for
                if search_term and line_lower.startswith(search_term[:min(len(search_term), 4)]):
                    print(f"[DEBUG] MATCH (prefix): '{search_term[:4]}' starts '{line}'", flush=True)
                    return self._build_full_description(lines, j)
        
        print(f"[DEBUG] NO MATCH for '{short_desc}'/'{type_code}' amount={amount_str}", flush=True)
        return None
    
    def _build_full_description(self, lines: List[str], idx: int) -> str:
        """Build full description, handling multi-line cases."""
        full_desc = lines[idx]
        
        # Check if next line is a continuation (starts with "- " or is part of the description)
        if idx + 1 < len(lines):
            next_line = lines[idx + 1]
            # Skip if next line is a number
            if not next_line.replace(',', '').replace('.', '').replace('-', '').isdigit():
                if next_line.startswith('- '):
                    full_desc = full_desc + " " + next_line
        
        return full_desc
    
    def _parse_json_response(self, response_text: str) -> List[Dict]:
        """Parse JSON from Claude response with multiple fallback strategies."""
        
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
                logger.error("Could not find end of JSON array")
                return []
        
        json_str = text[start_idx:end_idx + 1]
        
        # Fix common issues
        json_str = re.sub(r',\s*]', ']', json_str)
        json_str = re.sub(r',\s*}', '}', json_str)
        
        # Strategy 1: Direct parse
        try:
            data = json.loads(json_str)
            if isinstance(data, list):
                logger.info(f"Strategy 1 (direct): Parsed {len(data)} employees")
                return [self._normalize_employee(e) for e in data if isinstance(e, dict)]
        except json.JSONDecodeError as e:
            logger.warning(f"Strategy 1 failed: {e}")
        
        # Strategy 2: Extract objects one by one
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
        
        logger.info(f"Strategy 2 (object extraction): Parsed {len(employees)} employees")
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
        
        # Fallback: regex extraction
        try:
            name_match = re.search(r'"name"\s*:\s*"([^"]*)"', obj_str)
            emp_id_match = re.search(r'"employee_id"\s*:\s*"([^"]*)"', obj_str)
            dept_match = re.search(r'"department"\s*:\s*"([^"]*)"', obj_str)
            gross_match = re.search(r'"gross_pay"\s*:\s*([\d.]+)', obj_str)
            net_match = re.search(r'"net_pay"\s*:\s*([\d.]+)', obj_str)
            taxes_match = re.search(r'"total_taxes"\s*:\s*([\d.]+)', obj_str)
            deductions_match = re.search(r'"total_deductions"\s*:\s*([\d.]+)', obj_str)
            pay_method_match = re.search(r'"pay_method"\s*:\s*"([^"]*)"', obj_str)
            check_match = re.search(r'"check_number"\s*:\s*"([^"]*)"', obj_str)
            
            if name_match or gross_match:
                return {
                    "name": name_match.group(1) if name_match else "",
                    "employee_id": emp_id_match.group(1) if emp_id_match else "",
                    "department": dept_match.group(1) if dept_match else "",
                    "gross_pay": float(gross_match.group(1)) if gross_match else 0.0,
                    "net_pay": float(net_match.group(1)) if net_match else 0.0,
                    "total_taxes": float(taxes_match.group(1)) if taxes_match else 0.0,
                    "total_deductions": float(deductions_match.group(1)) if deductions_match else 0.0,
                    "earnings": [],
                    "taxes": [],
                    "deductions": [],
                    "check_number": check_match.group(1) if check_match else "",
                    "pay_method": pay_method_match.group(1) if pay_method_match else ""
                }
        except Exception as e:
            logger.debug(f"Object parse failed: {e}")
        
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
            # Demographic fields
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
        
        gross = emp.get('gross_pay', 0)
        net = emp.get('net_pay', 0)
        total_taxes = emp.get('total_taxes', 0)
        total_deductions = emp.get('total_deductions', 0)
        
        if gross > 0 and net > 0:
            # Sum only EMPLOYEE taxes/deductions (exclude ER/memo items)
            # These are what actually affect net pay
            
            ee_taxes = sum(
                t.get('amount', 0) or 0 
                for t in emp.get('taxes', []) 
                if not t.get('is_employer', False)
            )
            
            ee_deductions = sum(
                d.get('amount', 0) or 0 
                for d in emp.get('deductions', []) 
                if not d.get('is_employer', False) and d.get('category') != 'memo'
            )
            
            # Use provided totals if they exist and seem reasonable, otherwise use calculated
            # This handles cases where Claude correctly identified Emp Total / Post Total
            use_taxes = total_taxes if total_taxes > 0 else ee_taxes
            use_deductions = total_deductions if total_deductions >= 0 else ee_deductions
            
            # If totals are provided and different from sums, trust the totals (Emp Total, Post Total)
            if total_taxes > 0 or total_deductions >= 0:
                calculated = gross - total_taxes - total_deductions
            else:
                calculated = gross - ee_taxes - ee_deductions
            
            if abs(calculated - net) > 1.00:
                errors.append(
                    f"{emp.get('name', 'Unknown')}: Net mismatch (calc {calculated:.2f}, actual {net:.2f})"
                )
        
        return errors
    
    def _validate_against_report_totals(self, employees: List[Dict], report_totals: Optional[Dict]) -> Dict:
        """Cross-validate calculated totals against report totals section."""
        
        validation = {
            "has_report_totals": report_totals is not None,
            "all_matched": False,
            "discrepancies": [],
            "calculated": {
                "earnings": {},
                "taxes": {},
                "deductions": {},
                "grand_totals": {}
            },
            "reported": {
                "earnings": {},
                "taxes": {},
                "deductions": {},
                "grand_totals": {}
            }
        }
        
        if not report_totals:
            return validation
        
        # Calculate totals from employee data
        earnings_calc = {}
        taxes_calc = {}
        deductions_calc = {}
        grand_gross = 0
        grand_taxes = 0
        grand_deductions = 0
        grand_net = 0
        
        for emp in employees:
            grand_gross += emp.get('gross_pay', 0) or 0
            grand_taxes += emp.get('total_taxes', 0) or 0
            grand_deductions += emp.get('total_deductions', 0) or 0
            grand_net += emp.get('net_pay', 0) or 0
            
            for e in emp.get('earnings', []):
                key = e.get('type') or e.get('code') or e.get('description') or 'Unknown'
                earnings_calc[key] = earnings_calc.get(key, 0) + (e.get('amount', 0) or 0)
            
            for t in emp.get('taxes', []):
                key = t.get('type') or t.get('code') or t.get('description') or 'Unknown'
                taxes_calc[key] = taxes_calc.get(key, 0) + (t.get('amount', 0) or 0)
            
            for d in emp.get('deductions', []):
                key = d.get('type') or d.get('code') or d.get('description') or 'Unknown'
                deductions_calc[key] = deductions_calc.get(key, 0) + (d.get('amount', 0) or 0)
        
        validation["calculated"]["earnings"] = earnings_calc
        validation["calculated"]["taxes"] = taxes_calc
        validation["calculated"]["deductions"] = deductions_calc
        validation["calculated"]["grand_totals"] = {
            "gross_pay": round(grand_gross, 2),
            "total_taxes": round(grand_taxes, 2),
            "total_deductions": round(grand_deductions, 2),
            "net_pay": round(grand_net, 2)
        }
        
        # Extract reported totals
        reported_earnings = {}
        for e in report_totals.get('earnings', []):
            key = e.get('code') or e.get('description') or 'Unknown'
            reported_earnings[key] = e.get('total', 0)
        
        reported_taxes = {}
        for t in report_totals.get('taxes', []):
            key = t.get('code') or t.get('description') or 'Unknown'
            reported_taxes[key] = t.get('total', 0)
        
        reported_deductions = {}
        for d in report_totals.get('deductions', []):
            key = d.get('code') or d.get('description') or 'Unknown'
            reported_deductions[key] = d.get('total', 0)
        
        reported_grand = report_totals.get('grand_totals', {})
        
        validation["reported"]["earnings"] = reported_earnings
        validation["reported"]["taxes"] = reported_taxes
        validation["reported"]["deductions"] = reported_deductions
        validation["reported"]["grand_totals"] = reported_grand
        
        # Compare and find discrepancies
        discrepancies = []
        
        # Compare grand totals
        for key in ['gross_pay', 'total_taxes', 'total_deductions', 'net_pay']:
            calc_val = validation["calculated"]["grand_totals"].get(key, 0)
            rep_val = reported_grand.get(key, 0) or 0
            diff = round(calc_val - rep_val, 2)
            if abs(diff) > 0.01:
                discrepancies.append({
                    "category": "Grand Total",
                    "code": key.replace('_', ' ').title(),
                    "calculated": calc_val,
                    "reported": rep_val,
                    "difference": diff
                })
        
        # Compare earnings by code
        all_earning_codes = set(earnings_calc.keys()) | set(reported_earnings.keys())
        for code in all_earning_codes:
            calc_val = round(earnings_calc.get(code, 0), 2)
            rep_val = round(reported_earnings.get(code, 0), 2)
            diff = round(calc_val - rep_val, 2)
            if abs(diff) > 0.01:
                discrepancies.append({
                    "category": "Earnings",
                    "code": code,
                    "calculated": calc_val,
                    "reported": rep_val,
                    "difference": diff
                })
        
        # Compare taxes by code
        all_tax_codes = set(taxes_calc.keys()) | set(reported_taxes.keys())
        for code in all_tax_codes:
            calc_val = round(taxes_calc.get(code, 0), 2)
            rep_val = round(reported_taxes.get(code, 0), 2)
            diff = round(calc_val - rep_val, 2)
            if abs(diff) > 0.01:
                discrepancies.append({
                    "category": "Taxes",
                    "code": code,
                    "calculated": calc_val,
                    "reported": rep_val,
                    "difference": diff
                })
        
        # Compare deductions by code
        all_ded_codes = set(deductions_calc.keys()) | set(reported_deductions.keys())
        for code in all_ded_codes:
            calc_val = round(deductions_calc.get(code, 0), 2)
            rep_val = round(reported_deductions.get(code, 0), 2)
            diff = round(calc_val - rep_val, 2)
            if abs(diff) > 0.01:
                discrepancies.append({
                    "category": "Deductions",
                    "code": code,
                    "calculated": calc_val,
                    "reported": rep_val,
                    "difference": diff
                })
        
        validation["discrepancies"] = discrepancies
        validation["all_matched"] = len(discrepancies) == 0
        
        logger.info(f"Totals validation: {len(discrepancies)} discrepancies found")
        
        return validation


# =============================================================================
# SINGLETON
# =============================================================================

_extractor = None

def get_extractor() -> VacuumExtractor:
    global _extractor
    if _extractor is None:
        _extractor = VacuumExtractor()
    return _extractor


# =============================================================================
# BACKGROUND TASK
# =============================================================================

def process_extraction_job(job_id: str, file_path: str, max_pages: int, 
                           use_textract: bool, project_id: Optional[str],
                           vendor_type: str = "unknown", customer_id: Optional[str] = None):
    """Background task for async extraction."""
    ext = get_extractor()
    
    try:
        result = ext.extract(file_path, max_pages=max_pages, 
                            use_textract=use_textract, job_id=job_id,
                            vendor_type=vendor_type)
        
        # Add id field to employees for frontend
        for emp in result.get('employees', []):
            emp['id'] = emp.get('employee_id', '')
        
        # Save to database
        if result.get('success'):
            saved = save_extraction(
                project_id=project_id,
                source_file=result['source_file'],
                employees=result['employees'],
                confidence=result['confidence'],
                validation_passed=result['validation_passed'],
                validation_errors=result['validation_errors'],
                pages_processed=result['pages_processed'],
                cost_usd=result['cost_usd'],
                processing_time_ms=result['processing_time_ms'],
                extraction_method=result.get('extraction_method', 'pymupdf'),
                customer_id=customer_id,
                raw_text=result.get('raw_text')
            )
            result['extract_id'] = saved.get('id') if saved else None
            result['saved_to_db'] = saved is not None
            result['vendor_type'] = vendor_type
        
        update_job(job_id, result=result)
        
    except Exception as e:
        logger.error(f"Background job failed: {e}", exc_info=True)
        update_job(job_id, status='failed', message=str(e))
    
    finally:
        # Cleanup temp file
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                parent = os.path.dirname(file_path)
                if os.path.isdir(parent):
                    shutil.rmtree(parent, ignore_errors=True)
        except:
            pass


# =============================================================================
# ROUTES
# =============================================================================

@router.get("/vacuum/status")
async def status():
    ext = get_extractor()
    return {
        "available": ext.is_available,
        "version": "11.0-privacy",
        "default_method": "PyMuPDF (local, private)",
        "fallback_method": "Textract (AWS OCR)",
        "pii_redaction": True,
        "claude_key_set": bool(ext.claude_api_key),
        "aws_region": ext.aws_region
    }


@router.post("/vacuum/upload")
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
    
    Args:
        file: PDF file to process
        max_pages: Max pages (0 = all pages)
        project_id: Optional project ID
        use_textract: If True, use AWS Textract instead of PyMuPDF
        async_mode: If True, process in background and return job_id
        vendor_type: Vendor type (paycom, dayforce, adp, etc.) - 'unknown' for auto-detect
        customer_id: Optional customer ID for data isolation
    """
    ext = get_extractor()
    
    if not ext.is_available:
        return {"success": False, "error": "CLAUDE_API_KEY not set", "employees": [], "employee_count": 0}
    
    if not file.filename.lower().endswith('.pdf'):
        return {"success": False, "error": "Only PDF files supported", "employees": [], "employee_count": 0}
    
    # Save file
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, file.filename)
    
    with open(temp_path, 'wb') as f:
        shutil.copyfileobj(file.file, f)
    
    if async_mode:
        # Create job and process in background
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
            "message": f"Processing started. Poll /vacuum/job/{job_id} for status.",
            "extraction_method": "textract" if use_textract else "pymupdf",
            "vendor_type": vendor_type
        }
    else:
        # Synchronous processing
        try:
            result = ext.extract(temp_path, max_pages=max_pages, use_textract=use_textract)
            
            for emp in result.get('employees', []):
                emp['id'] = emp.get('employee_id', '')
            
            if result.get('success'):
                saved = save_extraction(
                    project_id=project_id,
                    source_file=result['source_file'],
                    employees=result['employees'],
                    confidence=result['confidence'],
                    validation_passed=result['validation_passed'],
                    validation_errors=result['validation_errors'],
                    pages_processed=result['pages_processed'],
                    cost_usd=result['cost_usd'],
                    processing_time_ms=result['processing_time_ms'],
                    extraction_method=result.get('extraction_method', 'pymupdf')
                )
                result['extract_id'] = saved.get('id') if saved else None
                result['saved_to_db'] = saved is not None
            
            return result
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


@router.get("/vacuum/job/{job_id}")
async def get_job_status(job_id: str):
    """Get status of an async extraction job."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/vacuum/extract")
async def extract(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    max_pages: int = Form(0),
    project_id: Optional[str] = Form(None),
    use_textract: bool = Form(False),
    async_mode: bool = Form(True)
):
    """Alias for /vacuum/upload"""
    return await upload(background_tasks, file, max_pages, project_id, use_textract, async_mode)


@router.get("/vacuum/extracts")
async def get_extracts(project_id: Optional[str] = None, limit: int = 50):
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
                "created_at": e.get('created_at')
            }
            for e in extracts
        ],
        "total": len(extracts)
    }


@router.get("/vacuum/extract/{extract_id}")
async def get_extract(extract_id: str):
    """Get full extraction details"""
    extraction = get_extraction_by_id(extract_id)
    if not extraction:
        return {"error": "Extraction not found"}
    return extraction


@router.get("/vacuum/extract/{extract_id}/raw")
async def get_extract_raw_text(extract_id: str):
    """Get raw extracted text for Consultant Assist review."""
    supabase = get_supabase()
    if not supabase:
        return {"error": "Database not available", "raw_text": ""}
    
    try:
        # Get the extraction job with raw_text
        response = supabase.table('extraction_jobs').select('source_file, raw_text').eq('id', extract_id).execute()
        if not response.data:
            return {"error": "Extraction not found", "raw_text": ""}
        
        raw_text = response.data[0].get('raw_text', '')
        if not raw_text:
            return {
                "raw_text": "Raw text not available for this extraction.\n\nRe-run the extraction to capture raw text.",
                "source_file": response.data[0].get('source_file', '')
            }
        
        return {
            "raw_text": raw_text,
            "source_file": response.data[0].get('source_file', '')
        }
    except Exception as e:
        logger.error(f"Failed to get raw text: {e}")
        return {"error": str(e), "raw_text": ""}


@router.get("/vacuum/extract-by-file/{source_file}/raw")
async def get_extract_raw_text_by_file(source_file: str):
    """Get raw extracted text by source file name (most recent)."""
    supabase = get_supabase()
    if not supabase:
        return {"error": "Database not available", "raw_text": "", "extract_id": ""}
    
    try:
        # Get the most recent extraction for this file
        response = supabase.table('extraction_jobs')\
            .select('id, source_file, raw_text')\
            .eq('source_file', source_file)\
            .order('created_at', desc=True)\
            .limit(1)\
            .execute()
        
        if not response.data:
            return {"error": "Extraction not found", "raw_text": "", "extract_id": ""}
        
        raw_text = response.data[0].get('raw_text', '')
        extract_id = response.data[0].get('id', '')
        
        if not raw_text:
            return {
                "raw_text": "Raw text not available for this extraction.\n\nRe-run the extraction to capture raw text.",
                "source_file": response.data[0].get('source_file', ''),
                "extract_id": extract_id
            }
        
        return {
            "raw_text": raw_text,
            "source_file": response.data[0].get('source_file', ''),
            "extract_id": extract_id
        }
    except Exception as e:
        logger.error(f"Failed to get raw text by file: {e}")
        return {"error": str(e), "raw_text": "", "extract_id": ""}


@router.get("/vacuum/field-definitions")
async def get_field_definitions(
    customer_id: Optional[str] = None,
    vendor_type: Optional[str] = None
):
    """Get custom field definitions for a customer or vendor."""
    supabase = get_supabase()
    if not supabase:
        return {"fields": []}
    
    try:
        query = supabase.table('field_definitions').select('*')
        if customer_id:
            query = query.eq('customer_id', customer_id)
        if vendor_type:
            query = query.eq('vendor_type', vendor_type)
        
        response = query.order('sort_order').execute()
        return {"fields": response.data or []}
    except Exception as e:
        logger.error(f"Failed to get field definitions: {e}")
        return {"fields": []}


@router.post("/vacuum/field-definitions")
async def create_field_definition(request: dict):
    """Create a new custom field definition."""
    supabase = get_supabase()
    if not supabase:
        return {"success": False, "error": "Database not available"}
    
    try:
        data = {
            "customer_id": request.get('customer_id'),
            "vendor_type": request.get('vendor_type'),
            "table_name": request.get('table_name'),
            "field_name": request.get('field_name'),
            "field_label": request.get('field_label'),
            "field_type": request.get('field_type', 'text'),
            "is_required": request.get('is_required', False),
            "default_value": request.get('default_value'),
            "sort_order": request.get('sort_order', 0)
        }
        
        response = supabase.table('field_definitions').insert(data).execute()
        return {"success": True, "field": response.data[0] if response.data else None}
    except Exception as e:
        logger.error(f"Failed to create field definition: {e}")
        return {"success": False, "error": str(e)}


@router.post("/vacuum/assist/save-template")
async def save_assist_template(request: dict):
    """Save Consultant Assist template (sections, fields, hints)."""
    supabase = get_supabase()
    if not supabase:
        return {"success": False, "error": "Database not available"}
    
    try:
        vendor_type = request.get('vendor_type', 'unknown')
        customer_id = request.get('customer_id')
        sections = request.get('sections', [])
        fields = request.get('fields', [])
        hints = request.get('hints', {})
        
        # Save field definitions
        for field in fields:
            if field.get('id', '').startswith('temp-'):
                # New field - insert
                field_data = {
                    "customer_id": customer_id,
                    "vendor_type": vendor_type,
                    "table_name": field.get('table_name'),
                    "field_name": field.get('field_name'),
                    "field_label": field.get('field_label'),
                    "field_type": field.get('field_type', 'text'),
                }
                supabase.table('field_definitions').insert(field_data).execute()
        
        # Update or create vendor prompt with hints
        if hints.get('specialInstructions') or hints.get('employeeMarker'):
            # Get existing prompt
            existing = supabase.table('vendor_prompts').select('*').eq('vendor_type', vendor_type).execute()
            
            # Build enhanced prompt with hints
            hint_additions = []
            if hints.get('layout') == 'horizontal':
                hint_additions.append("LAYOUT: This register has a HORIZONTAL layout with columns side-by-side.")
            if hints.get('employeeMarker'):
                hint_additions.append(f"EMPLOYEE MARKER: Each employee section starts with '{hints['employeeMarker']}'")
            if hints.get('specialInstructions'):
                hint_additions.append(f"SPECIAL INSTRUCTIONS: {hints['specialInstructions']}")
            
            if hint_additions and existing.data:
                # Append hints to existing prompt
                existing_prompt = existing.data[0].get('prompt_template', '')
                enhanced_prompt = existing_prompt + "\n\n" + "\n".join(hint_additions)
                
                supabase.table('vendor_prompts').update({
                    'prompt_template': enhanced_prompt
                }).eq('vendor_type', vendor_type).execute()
            elif hint_additions:
                # Create new prompt with hints
                base_prompt = VacuumExtractor()._get_default_prompt()
                enhanced_prompt = base_prompt + "\n\n" + "\n".join(hint_additions)
                
                supabase.table('vendor_prompts').insert({
                    'vendor_type': vendor_type,
                    'description': f'Auto-generated from Consultant Assist',
                    'prompt_template': enhanced_prompt
                }).execute()
        
        return {"success": True, "message": "Template saved successfully"}
    except Exception as e:
        logger.error(f"Failed to save assist template: {e}")
        return {"success": False, "error": str(e)}


@router.delete("/vacuum/extract/{extract_id}")
async def delete_extract(extract_id: str):
    """Delete an extraction"""
    success = delete_extraction(extract_id)
    return {"success": success, "id": extract_id}


@router.post("/vacuum/debug-extract")
async def debug_extract(
    file: UploadFile = File(...),
    page_num: int = Form(0)
):
    """Debug endpoint - extract one page with position data."""
    import fitz
    
    # Save file temporarily
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, file.filename)
    
    with open(temp_path, 'wb') as f:
        shutil.copyfileobj(file.file, f)
    
    try:
        doc = fitz.open(temp_path)
        
        if page_num >= len(doc):
            return {"error": f"Page {page_num} doesn't exist. Doc has {len(doc)} pages."}
        
        page = doc[page_num]
        
        # Get text with positions
        blocks = page.get_text("dict")["blocks"]
        
        lines_with_positions = []
        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    spans = line.get("spans", [])
                    line_text = " ".join(s.get("text", "") for s in spans)
                    bbox = line.get("bbox", [0,0,0,0])
                    lines_with_positions.append({
                        "text": line_text,
                        "x0": round(bbox[0], 1),
                        "y0": round(bbox[1], 1),
                        "x1": round(bbox[2], 1),
                        "y1": round(bbox[3], 1)
                    })
        
        # Also get plain text for comparison
        plain_text = page.get_text()
        
        doc.close()
        
        return {
            "page": page_num,
            "total_pages": len(doc),
            "plain_text": plain_text[:5000],  # First 5000 chars
            "lines_with_positions": lines_with_positions[:100]  # First 100 lines
        }
        
    finally:
        try:
            os.remove(temp_path)
            os.rmdir(temp_dir)
        except:
            pass


@router.get("/vacuum/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}
