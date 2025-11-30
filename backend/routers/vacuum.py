"""
Vacuum Router v10 - Background Job Processing
Deploy to: backend/routers/vacuum.py
"""

from fastapi import APIRouter, UploadFile, File, Form
from datetime import datetime
from typing import List, Dict, Optional
import os, re, json, logging, tempfile, shutil, threading

logger = logging.getLogger(__name__)
router = APIRouter()

def get_supabase():
    try:
        from utils.supabase_client import get_supabase as _get_supabase
        return _get_supabase()
    except ImportError:
        try:
            from backend.utils.supabase_client import get_supabase as _get_supabase
            return _get_supabase()
        except ImportError:
            return None

def create_job(job_type: str, project_id: str, input_data: dict) -> Optional[str]:
    supabase = get_supabase()
    if not supabase: return None
    try:
        data = {'job_type': job_type, 'project_id': project_id, 'status': 'queued', 'progress': {'total': 0, 'current': 0, 'step': 'Queued'}, 'input_data': input_data}
        response = supabase.table('processing_jobs').insert(data).execute()
        return response.data[0]['id'] if response.data else None
    except Exception as e:
        logger.error(f"Failed to create job: {e}")
        return None

def update_job(job_id: str, status: str = None, progress: dict = None, result_data: dict = None, error_message: str = None):
    supabase = get_supabase()
    if not supabase: return
    try:
        data = {'updated_at': datetime.now().isoformat()}
        if status:
            data['status'] = status
            if status == 'processing': data['started_at'] = datetime.now().isoformat()
            if status in ['completed', 'failed']: data['completed_at'] = datetime.now().isoformat()
        if progress: data['progress'] = progress
        if result_data: data['result_data'] = result_data
        if error_message: data['error_message'] = error_message
        supabase.table('processing_jobs').update(data).eq('id', job_id).execute()
    except Exception as e:
        logger.error(f"Failed to update job: {e}")

def get_job(job_id: str) -> Optional[dict]:
    supabase = get_supabase()
    if not supabase: return None
    try:
        response = supabase.table('processing_jobs').select('*').eq('id', job_id).execute()
        return response.data[0] if response.data else None
    except: return None

def save_extraction(project_id, source_file, employees, confidence, validation_passed, validation_errors, pages_processed, cost_usd, processing_time_ms):
    supabase = get_supabase()
    if not supabase: return None
    try:
        data = {'project_id': project_id, 'source_file': source_file, 'employee_count': len(employees), 'employees': employees, 'confidence': confidence, 'validation_passed': validation_passed, 'validation_errors': validation_errors, 'pages_processed': pages_processed, 'cost_usd': cost_usd, 'processing_time_ms': processing_time_ms}
        response = supabase.table('pay_extracts').insert(data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Failed to save: {e}")
        return None

def get_extractions(project_id=None, limit=50):
    supabase = get_supabase()
    if not supabase: return []
    try:
        query = supabase.table('pay_extracts').select('*').order('created_at', desc=True).limit(limit)
        if project_id: query = query.eq('project_id', project_id)
        return query.execute().data or []
    except: return []

def get_extraction_by_id(extract_id):
    supabase = get_supabase()
    if not supabase: return None
    try:
        response = supabase.table('pay_extracts').select('*').eq('id', extract_id).execute()
        return response.data[0] if response.data else None
    except: return None

def delete_extraction(extract_id):
    supabase = get_supabase()
    if not supabase: return False
    try:
        supabase.table('pay_extracts').delete().eq('id', extract_id).execute()
        return True
    except: return False

class SimpleExtractor:
    def __init__(self):
        self.claude_api_key = os.environ.get('CLAUDE_API_KEY')
        self.aws_region = os.environ.get('AWS_REGION', 'us-east-1')
        self._textract = None
        self._claude = None
    
    @property
    def is_available(self): return bool(self.claude_api_key)
    
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
    
    def extract_with_progress(self, file_path: str, max_pages: int, use_local_llm: bool, job_id: str, project_id: str) -> Dict:
        start = datetime.now()
        filename = os.path.basename(file_path)
        try:
            update_job(job_id, status='processing', progress={'total': max_pages, 'current': 0, 'step': 'Starting extraction'})
            pages_text = self._extract_pages_with_progress(file_path, max_pages, job_id)
            pages_processed = len(pages_text)
            if not pages_text: raise ValueError("No text extracted from PDF")
            
            update_job(job_id, progress={'total': pages_processed, 'current': pages_processed, 'step': 'Parsing with AI...'})
            employees = self._parse_with_claude(pages_text) if not use_local_llm else self._parse_with_local_llm(pages_text)
            
            update_job(job_id, progress={'total': pages_processed, 'current': pages_processed, 'step': 'Validating...'})
            validation_errors = []
            for emp in employees:
                errors = self._validate_employee(emp)
                emp['validation_errors'] = errors
                emp['is_valid'] = len(errors) == 0
                emp['id'] = emp.get('employee_id', '')
                validation_errors.extend(errors)
            
            valid_count = sum(1 for e in employees if e.get('is_valid', False))
            confidence = valid_count / len(employees) if employees else 0.0
            cost = (pages_processed * 0.015) + (0.0 if use_local_llm else 0.05)
            processing_time = int((datetime.now() - start).total_seconds() * 1000)
            
            result = {"success": len(employees) > 0, "source_file": filename, "employees": employees, "employee_count": len(employees), "confidence": confidence, "validation_passed": len(validation_errors) == 0, "validation_errors": validation_errors[:20], "pages_processed": pages_processed, "processing_time_ms": processing_time, "cost_usd": round(cost, 4)}
            
            saved = save_extraction(project_id, filename, employees, confidence, len(validation_errors) == 0, validation_errors[:20], pages_processed, round(cost, 4), processing_time)
            result['extract_id'] = saved.get('id') if saved else None
            result['saved_to_db'] = saved is not None
            
            update_job(job_id, status='completed', progress={'total': pages_processed, 'current': pages_processed, 'step': 'Complete'}, result_data=result)
            return result
        except Exception as e:
            logger.error(f"Extraction failed: {e}", exc_info=True)
            update_job(job_id, status='failed', error_message=str(e))
            return {"success": False, "error": str(e)}
    
    def _extract_pages_with_progress(self, file_path: str, max_pages: int, job_id: str) -> List[str]:
        import fitz
        pages_text = []
        doc = fitz.open(file_path)
        try:
            total = len(doc)
            to_process = total if max_pages == 0 else min(max_pages, total)
            for page_num in range(to_process):
                page = doc[page_num]
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img_bytes = pix.tobytes("png")
                response = self.textract.analyze_document(Document={'Bytes': img_bytes}, FeatureTypes=['TABLES'])
                lines = [block.get('Text', '') for block in response.get('Blocks', []) if block['BlockType'] == 'LINE']
                pages_text.append('\n'.join(lines))
                update_job(job_id, progress={'total': to_process, 'current': page_num + 1, 'step': f'Extracting page {page_num + 1}/{to_process}'})
        finally:
            doc.close()
        return pages_text
    
    def _parse_with_claude(self, pages_text: List[str]) -> List[Dict]:
        full_text = "\n\n--- PAGE BREAK ---\n\n".join(pages_text)[:35000]
        prompt = f"""Extract employees from this pay register as a JSON array.
DATA:
{full_text}

Return ONLY valid JSON array. Each employee: name, employee_id, department, gross_pay, net_pay, total_taxes, total_deductions, earnings, taxes, deductions, check_number, pay_method"""
        try:
            response_text = ""
            with self.claude.messages.stream(model="claude-sonnet-4-20250514", max_tokens=16000, messages=[{"role": "user", "content": prompt}]) as stream:
                for text in stream.text_stream: response_text += text
        except Exception as e:
            logger.error(f"Claude error: {e}")
            return []
        return self._parse_json_response(response_text)
    
    def _parse_with_local_llm(self, pages_text: List[str]) -> List[Dict]:
        import requests
        full_text = "\n\n--- PAGE BREAK ---\n\n".join(pages_text)[:30000]
        prompt = f"""Extract employees as JSON array: name, employee_id, department, gross_pay, net_pay, total_taxes, total_deductions, earnings, taxes, deductions, check_number, pay_method
DATA:
{full_text}"""
        try:
            response = requests.post(f"{os.environ.get('LOCAL_LLM_URL', 'http://localhost:11434')}/api/generate", json={"model": os.environ.get('LOCAL_LLM_MODEL', 'mistral'), "prompt": prompt, "stream": False, "options": {"num_predict": 8000}}, timeout=120)
            if response.status_code == 200: return self._parse_json_response(response.json().get('response', ''))
        except Exception as e:
            logger.error(f"Local LLM error: {e}")
        return []
    
    def _parse_json_response(self, response_text: str) -> List[Dict]:
        text = re.sub(r'^```json\s*|^```\s*|\s*```\s*$', '', response_text.strip())
        start_idx, end_idx = text.find('['), text.rfind(']')
        if start_idx < 0: return []
        if end_idx < start_idx:
            last_brace = text.rfind('}')
            if last_brace > start_idx: text = text[:last_brace + 1] + ']'; end_idx = len(text) - 1
            else: return []
        json_str = re.sub(r',\s*]', ']', re.sub(r',\s*}', '}', text[start_idx:end_idx + 1]))
        try:
            data = json.loads(json_str)
            if isinstance(data, list): return [self._normalize_employee(e) for e in data if isinstance(e, dict)]
        except: pass
        employees = []
        depth, obj_start = 0, None
        for i, char in enumerate(json_str):
            if char == '{':
                if depth == 0: obj_start = i
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0 and obj_start is not None:
                    emp = self._try_parse_object(json_str[obj_start:i + 1])
                    if emp: employees.append(emp)
                    obj_start = None
        return employees
    
    def _try_parse_object(self, obj_str: str) -> Optional[Dict]:
        obj_str = re.sub(r',\s*}', '}', re.sub(r',\s*]', ']', obj_str))
        try: return self._normalize_employee(json.loads(obj_str))
        except: pass
        def get(p): m = re.search(p, obj_str); return m.group(1) if m else ''
        def num(p): m = re.search(p, obj_str); return float(m.group(1)) if m else 0.0
        if get(r'"name"\s*:\s*"([^"]*)"') or num(r'"gross_pay"\s*:\s*([\d.]+)'):
            return {"name": get(r'"name"\s*:\s*"([^"]*)"'), "employee_id": get(r'"employee_id"\s*:\s*"([^"]*)"'), "department": get(r'"department"\s*:\s*"([^"]*)"'), "gross_pay": num(r'"gross_pay"\s*:\s*([\d.]+)'), "net_pay": num(r'"net_pay"\s*:\s*([\d.]+)'), "total_taxes": num(r'"total_taxes"\s*:\s*([\d.]+)'), "total_deductions": num(r'"total_deductions"\s*:\s*([\d.]+)'), "earnings": [], "taxes": [], "deductions": [], "check_number": get(r'"check_number"\s*:\s*"([^"]*)"'), "pay_method": get(r'"pay_method"\s*:\s*"([^"]*)"')}
        return None
    
    def _normalize_employee(self, data: Dict) -> Dict:
        return {"name": str(data.get('name', '')), "employee_id": str(data.get('employee_id', '')), "department": str(data.get('department', '')), "gross_pay": float(data.get('gross_pay', 0) or 0), "net_pay": float(data.get('net_pay', 0) or 0), "total_taxes": float(data.get('total_taxes', 0) or 0), "total_deductions": float(data.get('total_deductions', 0) or 0), "earnings": data.get('earnings') if isinstance(data.get('earnings'), list) else [], "taxes": data.get('taxes') if isinstance(data.get('taxes'), list) else [], "deductions": data.get('deductions') if isinstance(data.get('deductions'), list) else [], "check_number": str(data.get('check_number', '')), "pay_method": str(data.get('pay_method', ''))}
    
    def _validate_employee(self, emp: Dict) -> List[str]:
        errors = []
        if not emp.get('name'): errors.append("Missing name")
        gross, net, taxes, ded = emp.get('gross_pay', 0), emp.get('net_pay', 0), emp.get('total_taxes', 0), emp.get('total_deductions', 0)
        if gross > 0 and net > 0 and abs((gross - taxes - ded) - net) > 1.00: errors.append(f"{emp.get('name', '?')}: Net mismatch")
        return errors

_extractor = None
def get_extractor():
    global _extractor
    if _extractor is None: _extractor = SimpleExtractor()
    return _extractor

def process_vacuum_job(job_id: str, file_path: str, max_pages: int, use_local_llm: bool, project_id: str):
    try:
        get_extractor().extract_with_progress(file_path, max_pages, use_local_llm, job_id, project_id)
    except Exception as e:
        logger.error(f"Background job failed: {e}")
        update_job(job_id, status='failed', error_message=str(e))
    finally:
        try:
            if os.path.exists(file_path): os.remove(file_path)
            shutil.rmtree(os.path.dirname(file_path), ignore_errors=True)
        except: pass

@router.get("/vacuum/status")
async def status():
    ext = get_extractor()
    return {"available": ext.is_available, "version": "10.0-async", "claude_key_set": bool(ext.claude_api_key)}

@router.post("/vacuum/upload")
async def upload(file: UploadFile = File(...), max_pages: int = Form(3), project_id: Optional[str] = Form(None), use_local_llm: str = Form("false")):
    ext = get_extractor()
    use_local = use_local_llm.lower() == 'true'
    if not ext.is_available and not use_local: return {"success": False, "error": "CLAUDE_API_KEY not set", "job_id": None}
    if not file.filename.lower().endswith('.pdf'): return {"success": False, "error": "Only PDF supported", "job_id": None}
    
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, file.filename)
    with open(temp_path, 'wb') as f: shutil.copyfileobj(file.file, f)
    
    job_id = create_job('vacuum_extract', project_id, {'filename': file.filename, 'max_pages': max_pages, 'use_local_llm': use_local})
    if not job_id:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return {"success": False, "error": "Failed to create job", "job_id": None}
    
    thread = threading.Thread(target=process_vacuum_job, args=(job_id, temp_path, max_pages, use_local, project_id), daemon=True)
    thread.start()
    return {"success": True, "job_id": job_id, "message": "Processing started"}

@router.get("/vacuum/job/{job_id}")
async def get_job_status(job_id: str):
    job = get_job(job_id)
    if not job: return {"error": "Job not found"}
    return {"id": job.get('id'), "status": job.get('status'), "progress": job.get('progress'), "result": job.get('result_data'), "error": job.get('error_message'), "created_at": job.get('created_at'), "completed_at": job.get('completed_at')}

@router.post("/vacuum/extract")
async def extract(file: UploadFile = File(...), max_pages: int = Form(3), project_id: Optional[str] = Form(None), use_local_llm: str = Form("false")):
    return await upload(file, max_pages, project_id, use_local_llm)

@router.get("/vacuum/extracts")
async def get_extracts(project_id: Optional[str] = None, limit: int = 50):
    extracts = get_extractions(project_id=project_id, limit=limit)
    return {"extracts": [{"id": e.get('id'), "source_file": e.get('source_file'), "employee_count": e.get('employee_count'), "confidence": e.get('confidence'), "validation_passed": e.get('validation_passed'), "pages_processed": e.get('pages_processed'), "cost_usd": e.get('cost_usd'), "created_at": e.get('created_at')} for e in extracts], "total": len(extracts)}

@router.get("/vacuum/extract/{extract_id}")
async def get_extract(extract_id: str):
    extraction = get_extraction_by_id(extract_id)
    return extraction if extraction else {"error": "Not found"}

@router.delete("/vacuum/extract/{extract_id}")
async def delete_extract(extract_id: str):
    return {"success": delete_extraction(extract_id), "id": extract_id}

@router.get("/vacuum/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}
