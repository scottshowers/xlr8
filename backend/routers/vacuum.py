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
                    processing_time_ms: int, extraction_method: str = "pymupdf") -> Optional[Dict]:
    """Save extraction results to Supabase"""
    supabase = get_supabase()
    if not supabase:
        logger.warning("Cannot save - Supabase not available")
        return None
    
    try:
        data = {
            'project_id': project_id,
            'source_file': source_file,
            'employee_count': len(employees),
            'employees': employees,
            'confidence': confidence,
            'validation_passed': validation_passed,
            'validation_errors': validation_errors,
            'pages_processed': pages_processed,
            'cost_usd': cost_usd,
            'processing_time_ms': processing_time_ms,
            'extraction_method': extraction_method
        }
        
        response = supabase.table('pay_extracts').insert(data).execute()
        logger.info(f"Saved extraction: {source_file} with {len(employees)} employees")
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Failed to save extraction: {e}")
        return None


def get_extractions(project_id: Optional[str] = None, limit: int = 50) -> List[Dict]:
    """Get extraction history"""
    supabase = get_supabase()
    if not supabase:
        return []
    
    try:
        query = supabase.table('pay_extracts').select('*').order('created_at', desc=True).limit(limit)
        if project_id:
            query = query.eq('project_id', project_id)
        response = query.execute()
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Failed to get extractions: {e}")
        return []


def get_extraction_by_id(extract_id: str) -> Optional[Dict]:
    """Get single extraction by ID"""
    supabase = get_supabase()
    if not supabase:
        return None
    
    try:
        response = supabase.table('pay_extracts').select('*').eq('id', extract_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Failed to get extraction: {e}")
        return None


def delete_extraction(extract_id: str) -> bool:
    """Delete an extraction"""
    supabase = get_supabase()
    if not supabase:
        return False
    
    try:
        supabase.table('pay_extracts').delete().eq('id', extract_id).execute()
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
                use_textract: bool = False, job_id: str = None) -> Dict:
        """
        Extract employee pay data from PDF.
        
        Args:
            file_path: Path to PDF file
            max_pages: Max pages to process (0 = all)
            use_textract: If True, use AWS Textract instead of PyMuPDF
            job_id: Optional job ID for progress tracking
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
                pages_text, pages_processed = self._extract_with_pymupdf(file_path, max_pages, job_id)
            
            if not pages_text:
                raise ValueError("No text extracted from PDF")
            
            # Step 2: Redact PII
            if job_id:
                update_job(job_id, message='Redacting sensitive data...')
            
            logger.info("Redacting PII before sending to Claude...")
            redacted_pages = [self.redactor.redact(page) for page in pages_text]
            redaction_stats = self.redactor.get_stats()
            logger.info(f"PII Redaction: {redaction_stats}")
            
            # Step 3: Parse with Claude (redacted text only)
            if job_id:
                update_job(job_id, message='Parsing with AI...', progress=80)
            
            logger.info("Sending REDACTED text to Claude for parsing...")
            employees = self._parse_with_claude(redacted_pages)
            
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
                "privacy_compliant": True
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
    
    def _extract_with_pymupdf(self, file_path: str, max_pages: int, job_id: str = None) -> tuple:
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
                
        finally:
            doc.close()
        
        return pages_text, len(pages_text)
    
    def _parse_with_claude(self, pages_text: List[str]) -> List[Dict]:
        """Send REDACTED text to Claude for parsing."""
        
        full_text = "\n\n--- PAGE BREAK ---\n\n".join(pages_text)
        
        # Conservative limit - can increase once chunking is implemented
        if len(full_text) > 80000:
            logger.warning(f"Text too long ({len(full_text)}), truncating to 80k chars")
            full_text = full_text[:80000]
        
        logger.info(f"Sending {len(full_text)} characters to Claude ({len(pages_text)} pages)")
        
        prompt = f"""Extract employees from this pay register as a JSON array.

DATA:
{full_text}

STRICT RULES:
1. Return ONLY a valid JSON array - no markdown, no explanation
2. Each employee object must have these EXACT keys (no duplicates):
   name, employee_id, department, tax_profile, gross_pay, net_pay, total_taxes, total_deductions, earnings, taxes, deductions, check_number, pay_method
3. earnings/taxes/deductions are arrays of objects with: type, description, amount, hours (if applicable), rate (if applicable)
4. Use 0 for missing numbers, "" for missing strings, [] for missing arrays
5. Note: Some sensitive data has been redacted with [REDACTED] placeholders - ignore those

CRITICAL - YOU MUST DO THESE:
1. tax_profile: Extract "Tax Profile:" from employee header (e.g., "Tax Profile: 2 - MD/MD/MD" → "2 - MD/MD/MD")

2. FULL DESCRIPTIONS: The "description" field must contain the COMPLETE text from the earnings/deductions/taxes column. 
   - WRONG: "Shift Diff" 
   - CORRECT: "Shift Diff 2L OT"
   - WRONG: "Federal"
   - CORRECT: "Federal Withholding"
   Do NOT truncate or abbreviate descriptions.

3. PAGE BREAKS: Employees may span across "--- PAGE BREAK ---" markers. 
   - If you see an employee's header on one page and their earnings/taxes/deductions continue on the next page, COMBINE them into ONE employee record.
   - Do NOT create duplicate employee records for the same person.
   - Match by employee name and ID to merge split data.

Example format:
[{{"name":"DOE, JOHN","employee_id":"A123","department":"Sales","tax_profile":"2 - MD/MD/MD","gross_pay":1000.00,"net_pay":800.00,"total_taxes":150.00,"total_deductions":50.00,"earnings":[{{"type":"Regular","description":"Regular Pay","rate":25.00,"hours":40,"amount":1000.00}},{{"type":"Shift Diff","description":"Shift Diff 2L OT","rate":2.50,"hours":8,"amount":20.00}}],"taxes":[{{"type":"FWT","description":"Federal Withholding Tax","amount":100.00}}],"deductions":[{{"type":"401K","description":"401K Pre-Tax Contribution","amount":50.00}}],"check_number":"","pay_method":"Direct Deposit"}}]

Return the JSON array now:"""

        try:
            response_text = ""
            with self.claude.messages.stream(
                model="claude-sonnet-4-20250514",
                max_tokens=24000,
                messages=[{"role": "user", "content": prompt}]
            ) as stream:
                for text in stream.text_stream:
                    response_text += text
            
            logger.info(f"Claude response length: {len(response_text)}")
            
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return []
        
        return self._parse_json_response(response_text)
    
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
            "pay_method": str(data.get('pay_method', ''))
        }
    
    def _validate_employee(self, emp: Dict) -> List[str]:
        """Validate employee record."""
        errors = []
        
        if not emp.get('name'):
            errors.append("Missing employee name")
        
        gross = emp.get('gross_pay', 0)
        net = emp.get('net_pay', 0)
        taxes = emp.get('total_taxes', 0)
        deductions = emp.get('total_deductions', 0)
        
        if gross > 0 and net > 0:
            calculated = gross - taxes - deductions
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
                           use_textract: bool, project_id: Optional[str]):
    """Background task for async extraction."""
    ext = get_extractor()
    
    try:
        result = ext.extract(file_path, max_pages=max_pages, 
                            use_textract=use_textract, job_id=job_id)
        
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
                extraction_method=result.get('extraction_method', 'pymupdf')
            )
            result['extract_id'] = saved.get('id') if saved else None
            result['saved_to_db'] = saved is not None
        
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
    async_mode: bool = Form(True)
):
    """
    Upload and extract pay register.
    
    Args:
        file: PDF file to process
        max_pages: Max pages (0 = all pages)
        project_id: Optional project ID
        use_textract: If True, use AWS Textract instead of PyMuPDF
        async_mode: If True, process in background and return job_id
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
            job_id, temp_path, max_pages, use_textract, project_id
        )
        
        return {
            "success": True,
            "job_id": job_id,
            "status": "processing",
            "message": f"Processing started. Poll /vacuum/job/{job_id} for status.",
            "extraction_method": "textract" if use_textract else "pymupdf"
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


@router.delete("/vacuum/extract/{extract_id}")
async def delete_extract(extract_id: str):
    """Delete an extraction"""
    success = delete_extraction(extract_id)
    return {"success": success, "id": extract_id}


@router.get("/vacuum/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}
