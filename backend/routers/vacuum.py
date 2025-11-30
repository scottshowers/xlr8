"""
Vacuum Router - All In One v7
==============================
Robust JSON parsing with fallback extraction.

Deploy to: backend/routers/vacuum.py
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from datetime import datetime
from dataclasses import dataclass, field, asdict
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
    
    def extract(self, file_path: str, max_pages: int = 10) -> Dict:
        """Extract employee pay data from PDF. Returns dict for JSON response."""
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
                emp['validation_errors'] = errors
                emp['is_valid'] = len(errors) == 0
                validation_errors.extend(errors)
            
            valid_count = sum(1 for e in employees if e.get('is_valid', False))
            confidence = valid_count / len(employees) if employees else 0.0
            
            # Cost: $0.015/page for Textract + ~$0.05 for Claude
            cost = (pages_processed * 0.015) + 0.05
            processing_time = int((datetime.now() - start).total_seconds() * 1000)
            
            return {
                "success": len(employees) > 0,
                "source_file": filename,
                "employees": employees,
                "employee_count": len(employees),
                "confidence": confidence,
                "validation_passed": len(validation_errors) == 0,
                "validation_errors": validation_errors[:20],
                "pages_processed": pages_processed,
                "processing_time_ms": processing_time,
                "cost_usd": round(cost, 4)
            }
            
        except Exception as e:
            logger.error(f"Extraction failed: {e}", exc_info=True)
            processing_time = int((datetime.now() - start).total_seconds() * 1000)
            return {
                "success": False,
                "source_file": filename,
                "employees": [],
                "employee_count": 0,
                "confidence": 0.0,
                "validation_passed": False,
                "validation_errors": [str(e)],
                "pages_processed": 0,
                "processing_time_ms": processing_time,
                "cost_usd": 0.0
            }
    
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
    
    def _parse_with_claude(self, pages_text: List[str]) -> List[Dict]:
        """Send text to Claude for parsing."""
        
        full_text = "\n\n--- PAGE BREAK ---\n\n".join(pages_text)
        
        # Limit text
        if len(full_text) > 35000:
            logger.warning(f"Text too long ({len(full_text)}), truncating")
            full_text = full_text[:35000]
        
        prompt = f"""Extract employees from this pay register as a JSON array.

DATA:
{full_text}

STRICT RULES:
1. Return ONLY a valid JSON array - no markdown, no explanation
2. Each employee object must have these EXACT keys (no duplicates):
   name, employee_id, department, gross_pay, net_pay, total_taxes, total_deductions, earnings, taxes, deductions, check_number, pay_method
3. earnings/taxes/deductions are arrays of objects
4. Use 0 for missing numbers, "" for missing strings, [] for missing arrays

Example format:
[{{"name":"DOE, JOHN","employee_id":"A123","department":"Sales","gross_pay":1000.00,"net_pay":800.00,"total_taxes":150.00,"total_deductions":50.00,"earnings":[{{"description":"Regular","rate":25.00,"hours":40,"amount":1000.00}}],"taxes":[{{"description":"Federal","amount":100.00}}],"deductions":[{{"description":"401K","amount":50.00}}],"check_number":"","pay_method":"Direct Deposit"}}]

Return the JSON array now:"""

        try:
            response_text = ""
            with self.claude.messages.stream(
                model="claude-sonnet-4-20250514",
                max_tokens=16000,
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
        
        # Clean up response
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
            # Array not closed - find last complete object
            last_brace = text.rfind('}')
            if last_brace > start_idx:
                text = text[:last_brace + 1] + ']'
                end_idx = len(text) - 1
            else:
                logger.error("Could not find end of JSON array")
                return []
        
        json_str = text[start_idx:end_idx + 1]
        
        # Fix common issues
        json_str = re.sub(r',\s*]', ']', json_str)  # trailing comma before ]
        json_str = re.sub(r',\s*}', '}', json_str)  # trailing comma before }
        
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
        """Try to parse a single JSON object, fixing issues."""
        
        # Fix trailing commas
        obj_str = re.sub(r',\s*}', '}', obj_str)
        obj_str = re.sub(r',\s*]', ']', obj_str)
        
        # Try direct parse
        try:
            obj = json.loads(obj_str)
            return self._normalize_employee(obj)
        except:
            pass
        
        # Try removing duplicate keys by keeping only first occurrence
        # This is a hack but handles Claude's duplicate key bug
        try:
            seen_keys = set()
            fixed_parts = []
            in_string = False
            escape_next = False
            key_start = None
            brace_depth = 0
            bracket_depth = 0
            
            i = 0
            while i < len(obj_str):
                char = obj_str[i]
                
                if escape_next:
                    escape_next = False
                    i += 1
                    continue
                
                if char == '\\':
                    escape_next = True
                    i += 1
                    continue
                
                if char == '"':
                    in_string = not in_string
                
                if not in_string:
                    if char == '{':
                        brace_depth += 1
                    elif char == '}':
                        brace_depth -= 1
                    elif char == '[':
                        bracket_depth += 1
                    elif char == ']':
                        bracket_depth -= 1
                
                i += 1
            
            # If parsing still fails, extract what we can manually
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
        "version": "7.0-robust",
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
    """Upload and extract pay register."""
    ext = get_extractor()
    
    if not ext.is_available:
        return {"success": False, "error": "CLAUDE_API_KEY not set", "employees": [], "employee_count": 0}
    
    if not file.filename.lower().endswith('.pdf'):
        return {"success": False, "error": "Only PDF files supported", "employees": [], "employee_count": 0}
    
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, file.filename)
    
    try:
        with open(temp_path, 'wb') as f:
            shutil.copyfileobj(file.file, f)
        
        result = ext.extract(temp_path, max_pages=max_pages)
        
        # Add id field to employees for frontend
        for emp in result.get('employees', []):
            emp['id'] = emp.get('employee_id', '')
        
        # Save to database
        saved = None
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
                processing_time_ms=result['processing_time_ms']
            )
        
        result['extract_id'] = saved.get('id') if saved else None
        result['saved_to_db'] = saved is not None
        
        return result
        
    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "employees": [],
            "employee_count": 0,
            "source_file": file.filename,
            "validation_errors": [str(e)]
        }
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
