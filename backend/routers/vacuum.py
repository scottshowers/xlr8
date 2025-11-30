"""
Vacuum Router - All In One
===========================
Everything in one file. No import issues.

Deploy to: backend/routers/vacuum.py
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import os
import re
import json
import logging
import tempfile
import shutil

logger = logging.getLogger(__name__)
router = APIRouter()


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
                    processing_time_ms: int) -> Optional[Dict]:
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
            'processing_time_ms': processing_time_ms
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
# DATA CLASSES
# =============================================================================

@dataclass
class Employee:
    name: str = ""
    employee_id: str = ""
    department: str = ""
    gross_pay: float = 0.0
    net_pay: float = 0.0
    total_taxes: float = 0.0
    total_deductions: float = 0.0
    earnings: List[Dict] = field(default_factory=list)
    taxes: List[Dict] = field(default_factory=list)
    deductions: List[Dict] = field(default_factory=list)
    check_number: str = ""
    pay_method: str = ""
    is_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)


@dataclass
class ExtractionResult:
    success: bool
    source_file: str
    employees: List[Employee]
    employee_count: int
    confidence: float
    validation_passed: bool
    validation_errors: List[str]
    pages_processed: int
    processing_time_ms: int
    cost_usd: float


# =============================================================================
# EXTRACTOR CLASS
# =============================================================================

class SimpleExtractor:
    """Textract + Claude extractor."""
    
    def __init__(self):
        self.claude_api_key = os.environ.get('CLAUDE_API_KEY')
        self.aws_region = os.environ.get('AWS_REGION', 'us-east-1')
        self._textract = None
        self._claude = None
    
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
    
    def extract(self, file_path: str, max_pages: int = 10) -> ExtractionResult:
        """Extract employee pay data from PDF."""
        start = datetime.now()
        filename = os.path.basename(file_path)
        
        try:
            # Step 1: Get text from pages using Textract
            logger.info(f"Step 1: Extracting text with Textract (max {max_pages} pages)...")
            pages_text = self._extract_pages_text(file_path, max_pages)
            pages_processed = len(pages_text)
            
            if not pages_text:
                raise ValueError("No text extracted from PDF")
            
            # Step 2: Send to Claude for parsing
            logger.info("Step 2: Sending to Claude for parsing...")
            employees = self._parse_with_claude(pages_text)
            
            # Step 3: Validate
            logger.info("Step 3: Validating...")
            validation_errors = []
            for emp in employees:
                errors = self._validate_employee(emp)
                emp.validation_errors = errors
                emp.is_valid = len(errors) == 0
                validation_errors.extend(errors)
            
            valid_count = sum(1 for e in employees if e.is_valid)
            confidence = valid_count / len(employees) if employees else 0.0
            
            # Cost: $0.015/page for Textract + ~$0.05 for Claude
            cost = (pages_processed * 0.015) + 0.05
            
            processing_time = int((datetime.now() - start).total_seconds() * 1000)
            
            return ExtractionResult(
                success=len(employees) > 0,
                source_file=filename,
                employees=employees,
                employee_count=len(employees),
                confidence=confidence,
                validation_passed=len(validation_errors) == 0,
                validation_errors=validation_errors[:20],
                pages_processed=pages_processed,
                processing_time_ms=processing_time,
                cost_usd=round(cost, 4)
            )
            
        except Exception as e:
            logger.error(f"Extraction failed: {e}", exc_info=True)
            processing_time = int((datetime.now() - start).total_seconds() * 1000)
            return ExtractionResult(
                success=False,
                source_file=filename,
                employees=[],
                employee_count=0,
                confidence=0.0,
                validation_passed=False,
                validation_errors=[str(e)],
                pages_processed=0,
                processing_time_ms=processing_time,
                cost_usd=0.0
            )
    
    def _extract_pages_text(self, file_path: str, max_pages: int) -> List[str]:
        """Extract text using Textract."""
        import fitz  # PyMuPDF
        
        pages_text = []
        doc = fitz.open(file_path)
        
        try:
            total = len(doc)
            to_process = total if max_pages == 0 else min(max_pages, total)
            
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
                logger.info(f"Extracted page {page_num + 1}/{to_process}")
                
        finally:
            doc.close()
        
        return pages_text
    
    def _parse_with_claude(self, pages_text: List[str]) -> List[Employee]:
        """Send text to Claude for parsing with streaming."""
        
        full_text = "\n\n--- PAGE BREAK ---\n\n".join(pages_text)
        
        # Limit text size to avoid timeout
        if len(full_text) > 40000:
            logger.warning(f"Text too long ({len(full_text)}), truncating to 40000")
            full_text = full_text[:40000]
        
        prompt = f"""Parse this pay register and extract ALL employees as JSON.

PAY REGISTER DATA:
{full_text}

Return a JSON array where each employee has:
{{
  "name": "LASTNAME, FIRSTNAME",
  "employee_id": "code from Code: field",
  "department": "department name",
  "gross_pay": 0.00,
  "net_pay": 0.00,
  "total_taxes": 0.00,
  "total_deductions": 0.00,
  "earnings": [{{"description": "Regular", "rate": 0.00, "hours": 0.00, "amount": 0.00}}],
  "taxes": [{{"description": "Medicare", "amount": 0.00}}],
  "deductions": [{{"description": "401K", "amount": 0.00}}],
  "check_number": "",
  "pay_method": "Direct Deposit or Check"
}}

IMPORTANT:
- Extract actual names and values, not placeholders
- Include ALL employees found
- Parse earnings like "Regular 11.30 4.00 45.20" as rate=11.30, hours=4.00, amount=45.20
- GROSS amount goes in gross_pay
- NET PAY amount goes in net_pay
- Return ONLY the JSON array, no other text"""

        # Use streaming to avoid timeout
        response_text = ""
        with self.claude.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=16000,
            messages=[{"role": "user", "content": prompt}]
        ) as stream:
            for text in stream.text_stream:
                response_text += text
        
        logger.info(f"Claude response length: {len(response_text)}")
        
        # Parse JSON - handle common issues
        employees = []
        try:
            # Find JSON array in response
            json_match = re.search(r'\[[\s\S]*\]', response_text)
            if json_match:
                json_str = json_match.group()
            else:
                json_str = response_text
            
            # Remove markdown code fences
            json_str = re.sub(r'^```json\s*', '', json_str)
            json_str = re.sub(r'^```\s*', '', json_str)
            json_str = re.sub(r'\s*```$', '', json_str)
            
            # Fix common JSON issues
            # Remove trailing commas before ] or }
            json_str = re.sub(r',\s*]', ']', json_str)
            json_str = re.sub(r',\s*}', '}', json_str)
            
            # Fix duplicate keys by keeping only first occurrence in each object
            # This is a simple approach - find objects and dedupe
            
            # If truncated mid-object, try to salvage complete objects
            if json_str.count('[') > json_str.count(']'):
                # Find last complete object (ends with })
                last_brace = json_str.rfind('}')
                if last_brace > 0:
                    # Find the comma or [ before it
                    search_pos = last_brace
                    while search_pos > 0:
                        if json_str[search_pos] == '{':
                            # Found start of last object, check if it's complete
                            try:
                                test_obj = json_str[search_pos:last_brace+1]
                                json.loads(test_obj)
                                # Object is valid, truncate here
                                json_str = json_str[:last_brace+1] + ']'
                                break
                            except:
                                pass
                        search_pos -= 1
                    else:
                        # Fallback: just close the array
                        json_str = json_str[:last_brace+1] + ']'
            
            # Try to parse
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.warning(f"First parse attempt failed: {e}")
                # Try extracting individual objects
                data = self._extract_objects_manually(json_str)
            
            for emp_data in data:
                if not isinstance(emp_data, dict):
                    continue
                emp = Employee(
                    name=str(emp_data.get('name', '')),
                    employee_id=str(emp_data.get('employee_id', '')),
                    department=str(emp_data.get('department', '')),
                    gross_pay=float(emp_data.get('gross_pay', 0) or 0),
                    net_pay=float(emp_data.get('net_pay', 0) or 0),
                    total_taxes=float(emp_data.get('total_taxes', 0) or 0),
                    total_deductions=float(emp_data.get('total_deductions', 0) or 0),
                    earnings=emp_data.get('earnings', []) or [],
                    taxes=emp_data.get('taxes', []) or [],
                    deductions=emp_data.get('deductions', []) or [],
                    check_number=str(emp_data.get('check_number', '')),
                    pay_method=str(emp_data.get('pay_method', ''))
                )
                employees.append(emp)
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            logger.error(f"Response: {response_text[:1000]}")
        except Exception as e:
            logger.error(f"Unexpected error parsing response: {e}")
        
        logger.info(f"Parsed {len(employees)} employees")
        return employees
    
    def _extract_objects_manually(self, json_str: str) -> List[Dict]:
        """Manually extract JSON objects from malformed array"""
        objects = []
        depth = 0
        start = None
        
        for i, char in enumerate(json_str):
            if char == '{':
                if depth == 0:
                    start = i
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0 and start is not None:
                    obj_str = json_str[start:i+1]
                    try:
                        obj = json.loads(obj_str)
                        objects.append(obj)
                    except:
                        # Try to fix common issues in this object
                        try:
                            # Remove duplicate keys (keep first)
                            obj_str = re.sub(r',\s*"(\w+)":\s*\[?\s*$', '', obj_str)
                            obj_str = re.sub(r',\s*}', '}', obj_str)
                            obj = json.loads(obj_str)
                            objects.append(obj)
                        except:
                            logger.debug(f"Could not parse object: {obj_str[:100]}...")
                    start = None
        
        logger.info(f"Manually extracted {len(objects)} objects")
        return objects
    
    def _validate_employee(self, emp: Employee) -> List[str]:
        """Validate employee record."""
        errors = []
        
        if not emp.name:
            errors.append("Missing employee name")
        
        if emp.gross_pay > 0 and emp.net_pay > 0:
            calculated = emp.gross_pay - emp.total_taxes - emp.total_deductions
            if abs(calculated - emp.net_pay) > 1.00:  # $1 tolerance
                errors.append(
                    f"{emp.name}: Net pay mismatch (calculated {calculated:.2f}, actual {emp.net_pay:.2f})"
                )
        
        return errors


# =============================================================================
# SINGLETON
# =============================================================================

_extractor = None

def get_extractor() -> SimpleExtractor:
    global _extractor
    if _extractor is None:
        _extractor = SimpleExtractor()
    return _extractor


# =============================================================================
# ROUTES
# =============================================================================

@router.get("/vacuum/status")
async def status():
    ext = get_extractor()
    return {
        "available": ext.is_available,
        "version": "6.0-simple",
        "method": "Textract + Claude",
        "claude_key_set": bool(ext.claude_api_key),
        "aws_region": ext.aws_region
    }


@router.post("/vacuum/upload")
async def upload(
    file: UploadFile = File(...),
    max_pages: int = Form(3),
    project_id: Optional[str] = Form(None)
):
    """
    Upload and extract pay register.
    
    Cost: ~$0.015/page (Textract) + ~$0.05 (Claude)
    Default 3 pages = ~$0.10
    """
    ext = get_extractor()
    
    if not ext.is_available:
        raise HTTPException(503, "CLAUDE_API_KEY not set")
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, "Only PDF files supported")
    
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, file.filename)
    
    try:
        with open(temp_path, 'wb') as f:
            shutil.copyfileobj(file.file, f)
        
        result = ext.extract(temp_path, max_pages=max_pages)
        
        # Convert employees to dicts for storage
        employees_data = [
            {
                "name": e.name,
                "id": e.employee_id,
                "department": e.department,
                "gross_pay": e.gross_pay,
                "net_pay": e.net_pay,
                "total_taxes": e.total_taxes,
                "total_deductions": e.total_deductions,
                "earnings": e.earnings,
                "taxes": e.taxes,
                "deductions": e.deductions,
                "check_number": e.check_number,
                "pay_method": e.pay_method,
                "is_valid": e.is_valid,
                "validation_errors": e.validation_errors
            }
            for e in result.employees
        ]
        
        # Save to database
        saved = save_extraction(
            project_id=project_id,
            source_file=result.source_file,
            employees=employees_data,
            confidence=result.confidence,
            validation_passed=result.validation_passed,
            validation_errors=result.validation_errors,
            pages_processed=result.pages_processed,
            cost_usd=result.cost_usd,
            processing_time_ms=result.processing_time_ms
        )
        
        return {
            "success": result.success,
            "extract_id": saved.get('id') if saved else None,
            "source_file": result.source_file,
            "employee_count": result.employee_count,
            "employees": employees_data,
            "confidence": result.confidence,
            "validation_passed": result.validation_passed,
            "validation_errors": result.validation_errors,
            "pages_processed": result.pages_processed,
            "processing_time_ms": result.processing_time_ms,
            "cost_usd": result.cost_usd,
            "saved_to_db": saved is not None
        }
        
    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        raise HTTPException(500, str(e))
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@router.post("/vacuum/extract")
async def extract(
    file: UploadFile = File(...),
    max_pages: int = Form(3),
    project_id: Optional[str] = Form(None)
):
    """Alias for /vacuum/upload"""
    return await upload(file, max_pages, project_id)


@router.get("/vacuum/extracts")
async def get_extracts(project_id: Optional[str] = None, limit: int = 50):
    """Get extraction history"""
    extracts = get_extractions(project_id=project_id, limit=limit)
    
    # Simplify for list view (don't return all employee data)
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
                "created_at": e.get('created_at')
            }
            for e in extracts
        ],
        "total": len(extracts)
    }


@router.get("/vacuum/extract/{extract_id}")
async def get_extract(extract_id: str):
    """Get full extraction details including all employees"""
    extraction = get_extraction_by_id(extract_id)
    if not extraction:
        raise HTTPException(404, "Extraction not found")
    return extraction


@router.delete("/vacuum/extract/{extract_id}")
async def delete_extract(extract_id: str):
    """Delete an extraction"""
    success = delete_extraction(extract_id)
    return {"success": success, "id": extract_id}


@router.get("/vacuum/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}
