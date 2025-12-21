"""
Smart PDF Analyzer - LLM-Based with PII Redaction

Simple approach:
1. Extract text from PDF
2. Redact PII before sending to LLM
3. Ask LLM: "Is this tabular? If yes, parse it"
4. Route to DuckDB (tabular) or ChromaDB (text)
"""

import os
import re
import json
import logging
import requests
from typing import Dict, Any, List, Optional
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)

# Try to import pdfplumber for text extraction
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    logger.warning("pdfplumber not available")

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


# =============================================================================
# PII REDACTION PATTERNS
# =============================================================================

PII_PATTERNS = {
    # === IDENTITY ===
    'ssn': (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN-REDACTED]'),
    'ssn_no_dash': (r'\b(?<!\d)\d{9}(?!\d)\b', '[SSN-REDACTED]'),  # 9 digits not part of larger number
    
    # === CONTACT ===
    'phone': (r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b', '[PHONE-REDACTED]'),
    'email': (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL-REDACTED]'),
    
    # === FINANCIAL ===
    'credit_card': (r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CC-REDACTED]'),
    'bank_account': (r'\b\d{8,17}\b', '[ACCT-REDACTED]'),  # Bank accounts typically 8-17 digits
    'routing': (r'\b\d{9}\b', '[ROUTING-REDACTED]'),  # ABA routing numbers are 9 digits
    'salary_amount': (r'\$\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?\b', '[AMOUNT-REDACTED]'),  # $50,000.00
    'salary_plain': (r'\b\d{2,3},\d{3}(?:\.\d{2})?\b', '[AMOUNT-REDACTED]'),  # 50,000.00 without $
    
    # === DATES ===
    'dob_slash': (r'\b\d{1,2}/\d{1,2}/\d{2,4}\b', '[DATE-REDACTED]'),  # MM/DD/YYYY or MM/DD/YY
    'dob_dash': (r'\b\d{1,2}-\d{1,2}-\d{2,4}\b', '[DATE-REDACTED]'),  # MM-DD-YYYY
    'iso_date': (r'\b\d{4}-\d{2}-\d{2}\b', '[DATE-REDACTED]'),  # YYYY-MM-DD
    
    # === ADDRESSES ===
    'street_address': (r'\b\d{1,5}\s+(?:[A-Za-z]+\s+){1,3}(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct|Circle|Cir|Place|Pl)\.?\b', '[ADDRESS-REDACTED]'),
    'zip_code': (r'\b\d{5}(?:-\d{4})?\b', '[ZIP-REDACTED]'),
    'po_box': (r'\b[Pp]\.?[Oo]\.?\s*[Bb]ox\s+\d+\b', '[POBOX-REDACTED]'),
    
    # === EMPLOYEE IDENTIFIERS ===
    'employee_id': (r'\b[Ee]mp(?:loyee)?[-\s]?(?:[Ii][Dd]|[Nn]o|[Nn]um(?:ber)?)?[-:\s]*\d{3,10}\b', '[EMPID-REDACTED]'),
    'badge_id': (r'\b[Bb]adge[-\s]?(?:[Ii][Dd]|[Nn]o)?[-:\s]*\d{3,10}\b', '[BADGEID-REDACTED]'),
    
    # === NAMES (context-based - looks for labeled names) ===
    # These catch "Name: John Smith" or "Employee Name: Jane Doe" patterns
    'labeled_name': (r'(?:[Nn]ame|[Ee]mployee|[Aa]ssociate)[-:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})', '[NAME-REDACTED]'),
    'name_first_last': (r'\b([A-Z][a-z]+)\s+([A-Z][a-z]+)\s+(?=\d{3}-\d{2}-\d{4})', '[NAME-REDACTED]'),  # Name before SSN
}

# NOTE: EIN/FEIN removed - these are public business identifiers, not personal PII
# 'ein': (r'\b\d{2}-\d{7}\b', '[EIN-REDACTED]'),

def redact_pii(text: str) -> str:
    """Redact PII from text before sending to LLM."""
    redacted = text
    
    for name, (pattern, replacement) in PII_PATTERNS.items():
        if replacement:
            redacted = re.sub(pattern, replacement, redacted)
    
    return redacted


# =============================================================================
# LLM CLIENT - Smart Model Routing
# =============================================================================

# Model routing by task - uses available RunPod models
TASK_MODEL_MAP = {
    # PDF analysis - needs good instruction following
    'pdf_parse': 'mistral:7b',
    'pdf_analyze': 'mistral:7b',
    
    # SQL generation - code model excels here
    'sql_generate': 'deepseek-coder:6.7b',
    'sql': 'deepseek-coder:6.7b',
    
    # General code tasks - use larger code model for complex work
    'code': 'qwen2.5-coder:14b',
    'code_complex': 'qwen2.5-coder:14b',
    'code_simple': 'deepseek-coder:6.7b',
    
    # Chat/synthesis - general purpose
    'chat': 'mistral:7b',
    'synthesis': 'mistral:7b',
    'summarize': 'mistral:7b',
    
    # Embeddings - dedicated model
    'embed': 'nomic-embed-text:latest',
    'embedding': 'nomic-embed-text:latest',
    
    # Default fallback
    'default': 'mistral:7b',
}

def get_model_for_task(task: str) -> str:
    """
    Get the appropriate model for a given task.
    
    Falls back to env var if set, then to mistral:7b as default.
    """
    # Check for env var override first (allows forcing specific model)
    env_override = os.getenv('LLM_MODEL_OVERRIDE')
    if env_override:
        return env_override
    
    # Look up task in map
    model = TASK_MODEL_MAP.get(task.lower(), TASK_MODEL_MAP['default'])
    
    logger.info(f"[LLM] Task '{task}' -> Model '{model}'")
    return model


def get_llm_config() -> Dict[str, str]:
    """Get LLM configuration from environment."""
    return {
        'url': os.getenv('LLM_INFERENCE_URL') or os.getenv('OLLAMA_URL') or os.getenv('RUNPOD_URL') or os.getenv('LLM_ENDPOINT'),
        'username': os.getenv('LLM_USERNAME', ''),
        'password': os.getenv('LLM_PASSWORD', ''),
        # Note: model is now determined per-call by get_model_for_task()
        'default_model': os.getenv('LLM_MODEL') or os.getenv('LLM_DEFAULT_MODEL', 'mistral:7b')
    }


def call_llm(prompt: str, max_tokens: int = 4000, operation: str = "pdf_parse", project_id: str = None) -> Optional[str]:
    """
    Call LLM for text generation with smart model routing.
    
    The 'operation' parameter determines which model to use:
    - pdf_parse, pdf_analyze -> mistral:7b
    - sql_generate, sql -> deepseek-coder:6.7b  
    - code, code_complex -> qwen2.5-coder:14b
    - chat, synthesis -> mistral:7b
    """
    config = get_llm_config()
    model = get_model_for_task(operation)
    
    # Try Ollama-compatible endpoint first
    if config['url']:
        url = f"{config['url'].rstrip('/')}/api/generate"
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": 0.1
            }
        }
        
        import time
        start_time = time.time()
        
        try:
            auth = None
            if config['username'] and config['password']:
                auth = HTTPBasicAuth(config['username'], config['password'])
            
            logger.warning(f"[LLM] Calling {url} with model {model}")
            response = requests.post(url, json=payload, auth=auth, timeout=180)
            response.raise_for_status()
            
            result = response.json()
            llm_response = result.get('response', '')
            
            # Track cost
            duration_ms = int((time.time() - start_time) * 1000)
            try:
                from backend.utils.cost_tracker import log_cost, CostService
                log_cost(CostService.LOCAL_LLM, operation, duration_ms=duration_ms, project_id=project_id)
            except:
                pass
            
            return llm_response
            
        except Exception as e:
            logger.warning(f"[LLM] Ollama request failed: {e}, falling back to rule-based detection")
    
    # Groq fallback DISABLED for PII protection
    # External LLM services should not receive customer data
    # When Ollama is unavailable, we rely on rule-based detection
    # 
    # groq_key = os.getenv('GROQ_API_KEY', '')
    # if groq_key:
    #     ... Groq code removed for security ...
    
    logger.warning("[LLM] Ollama unavailable - using rule-based detection (Groq disabled for PII protection)")
    return None


# =============================================================================
# PDF TEXT EXTRACTION
# =============================================================================

def extract_pdf_text(file_path: str) -> str:
    """Extract all text from a PDF."""
    if not PDFPLUMBER_AVAILABLE:
        logger.error("[PDF] pdfplumber not available")
        return ""
    
    text_parts = []
    try:
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text() or ''
                if page_text.strip():
                    text_parts.append(f"--- PAGE {i+1} ---\n{page_text}")
        
        full_text = '\n\n'.join(text_parts)
        logger.warning(f"[PDF] Extracted {len(full_text):,} chars from {len(text_parts)} pages")
        return full_text
    except Exception as e:
        logger.error(f"[PDF] Extraction failed: {e}")
        return ""


# =============================================================================
# RULE-BASED DETECTION (Fallback when LLM unavailable)
# =============================================================================

def detect_tabular_by_rules(text_sample: str) -> Dict[str, Any]:
    """
    Detect tabular structure using rules when LLM is unavailable.
    
    Looks for:
    - Consistent delimiters (|, tabs, commas)
    - Repeated line patterns
    - Column-like spacing
    - Numeric data patterns
    - Config/setup document patterns
    """
    lines = [l for l in text_sample.split('\n') if l.strip()]
    
    if len(lines) < 5:
        return {"is_tabular": False, "method": "rules", "reason": "too few lines"}
    
    # Check for pipe delimiters (very common in PDF tables)
    pipe_lines = sum(1 for l in lines if '|' in l and l.count('|') >= 2)
    pipe_ratio = pipe_lines / len(lines)
    
    # Check for tab delimiters
    tab_lines = sum(1 for l in lines if '\t' in l)
    tab_ratio = tab_lines / len(lines)
    
    # Check for consistent spacing patterns (column alignment)
    # Lines with multiple spaces followed by content = columnar data
    spacing_pattern = sum(1 for l in lines if len(re.findall(r'\s{2,}\S+', l)) >= 2)
    spacing_ratio = spacing_pattern / len(lines)
    
    # Check for repeated numeric patterns (data rows)
    numeric_lines = sum(1 for l in lines if len(re.findall(r'\b\d+\.?\d*\b', l)) >= 2)
    numeric_ratio = numeric_lines / len(lines)
    
    # Check for code-like patterns (5-digit codes, alphanumeric codes at line start)
    code_lines = sum(1 for l in lines if re.match(r'^\s*\d{4,6}\s+', l.strip()) or re.match(r'^\s*[A-Z]{2,5}\d*\s+', l.strip()))
    code_ratio = code_lines / len(lines) if lines else 0
    
    # Check for UKG-specific patterns
    ukg_patterns = ['Earnings Code', 'Deduction Code', 'Company Code', 'Tax Category', 
                    'Employee Number', 'Pay Group', 'Rate Table', 'Filing Status',
                    'Calculation', 'Rate Factor', 'Accumulators', 'General Ledger']
    has_ukg = any(p.lower() in text_sample.lower() for p in ukg_patterns)
    ukg_matches = sum(1 for p in ukg_patterns if p.lower() in text_sample.lower())
    
    # Check for config/setup document patterns
    config_patterns = ['Page 1', 'Page 2', 'Select: All', 'Last Page', 
                       'Reg Pay', 'Flat amount', 'Pay rate', 'hours *']
    has_config = any(p.lower() in text_sample.lower() for p in config_patterns)
    config_matches = sum(1 for p in config_patterns if p.lower() in text_sample.lower())
    
    # Check for repeated header lines (common in multi-page PDF tables)
    first_line = lines[0].strip() if lines else ""
    header_repeats = sum(1 for l in lines if l.strip() == first_line)
    has_repeated_headers = header_repeats >= 3
    
    # Decision logic
    is_tabular = False
    confidence = 0.0
    reasons = []
    
    if pipe_ratio > 0.3:
        is_tabular = True
        confidence = max(confidence, pipe_ratio)
        reasons.append(f"pipe_delimited ({pipe_ratio:.0%})")
    
    if tab_ratio > 0.3:
        is_tabular = True
        confidence = max(confidence, tab_ratio)
        reasons.append(f"tab_delimited ({tab_ratio:.0%})")
    
    if spacing_ratio > 0.4 and numeric_ratio > 0.2:
        is_tabular = True
        confidence = max(confidence, spacing_ratio)
        reasons.append(f"column_spacing ({spacing_ratio:.0%}) + numeric ({numeric_ratio:.0%})")
    
    # Code patterns strongly indicate tabular data (e.g., earnings codes, deduction codes)
    if code_ratio > 0.15:
        is_tabular = True
        confidence = max(confidence, 0.85)
        reasons.append(f"code_patterns ({code_ratio:.0%})")
    
    # UKG patterns - lower threshold since these are strong indicators
    if has_ukg and ukg_matches >= 2:
        is_tabular = True
        confidence = max(confidence, 0.8)
        reasons.append(f"ukg_patterns ({ukg_matches} matches)")
    elif has_ukg and (spacing_ratio > 0.15 or numeric_ratio > 0.2 or code_ratio > 0.1):
        is_tabular = True
        confidence = max(confidence, 0.75)
        reasons.append("ukg_patterns_with_structure")
    
    # Config document patterns
    if has_config and config_matches >= 3:
        is_tabular = True
        confidence = max(confidence, 0.75)
        reasons.append(f"config_document ({config_matches} matches)")
    
    # Repeated headers (multi-page table)
    if has_repeated_headers and (numeric_ratio > 0.15 or code_ratio > 0.1):
        is_tabular = True
        confidence = max(confidence, 0.7)
        reasons.append("repeated_headers")
    
    # Large documents with moderate signals should lean tabular
    if len(text_sample) > 100000 and (spacing_ratio > 0.25 or numeric_ratio > 0.25):
        is_tabular = True
        confidence = max(confidence, 0.7)
        reasons.append(f"large_doc_with_patterns")
    
    # Medium docs with good signals
    if len(text_sample) > 10000 and (numeric_ratio > 0.3 or code_ratio > 0.2):
        is_tabular = True
        confidence = max(confidence, 0.7)
        reasons.append(f"medium_doc_numeric ({numeric_ratio:.0%})")
    
    result = {
        "is_tabular": is_tabular,
        "method": "rules",
        "confidence": confidence,
        "reasons": reasons,
        "metrics": {
            "pipe_ratio": pipe_ratio,
            "tab_ratio": tab_ratio,
            "spacing_ratio": spacing_ratio,
            "numeric_ratio": numeric_ratio,
            "code_ratio": code_ratio,
            "has_ukg_patterns": has_ukg,
            "ukg_matches": ukg_matches,
            "has_config_patterns": has_config,
            "config_matches": config_matches
        }
    }
    
    logger.warning(f"[RULES] Detection result: is_tabular={is_tabular}, reasons={reasons}")
    if not is_tabular:
        logger.warning(f"[RULES] Metrics: numeric={numeric_ratio:.0%}, code={code_ratio:.0%}, spacing={spacing_ratio:.0%}, ukg={ukg_matches}, config={config_matches}")
    return result


def infer_columns_from_text(text_sample: str) -> List[str]:
    """
    Infer column names from tabular text when LLM is unavailable.
    
    Looks for:
    - Common header patterns (Code, Description, Amount, etc.)
    - Repeated header lines across pages
    - UKG-specific column names
    """
    lines = [l.strip() for l in text_sample.split('\n') if l.strip()]
    
    if len(lines) < 3:
        return []
    
    # UKG Earnings/Deductions specific columns
    ukg_earnings_cols = ['Code', 'Description', 'Tax Category', 'Calculation Rule', 
                         'Rate Factor', 'Reg Pay', 'Special 1', 'Special 2', 'Special 3',
                         'Accumulators', 'Retro Accruals', 'Deferred Pay', 'Shift Calc',
                         'Loc Alloc', 'General Ledger', 'Expense Account']
    
    ukg_deduction_cols = ['Code', 'Description', 'Category', 'Calculation', 
                          'Rate', 'Limit', 'Start Date', 'End Date', 'GL Account']
    
    ukg_employee_cols = ['Employee ID', 'Name', 'Department', 'Location', 
                         'Job Title', 'Pay Group', 'Status', 'Hire Date']
    
    # Generic payroll columns
    generic_cols = ['Code', 'Description', 'Type', 'Category', 'Amount', 
                    'Rate', 'Hours', 'Units', 'Total', 'YTD']
    
    text_lower = text_sample.lower()
    
    # Check which column set matches best
    if 'tax category' in text_lower and 'calculation' in text_lower:
        # Earnings codes document
        logger.warning("[RULES] Detected UKG earnings code structure")
        return ukg_earnings_cols
    
    if 'deduction' in text_lower and ('category' in text_lower or 'limit' in text_lower):
        # Deductions document
        logger.warning("[RULES] Detected UKG deduction code structure")
        return ukg_deduction_cols
    
    if 'employee' in text_lower and ('department' in text_lower or 'location' in text_lower):
        # Employee list
        logger.warning("[RULES] Detected employee list structure")
        return ukg_employee_cols
    
    # Try to extract columns from first few lines
    # Look for lines that have multiple capitalized words (potential headers)
    for line in lines[:10]:
        words = line.split()
        # Header lines typically have multiple capitalized words
        cap_words = [w for w in words if w and w[0].isupper() and len(w) > 1]
        
        if len(cap_words) >= 4:
            # This might be a header line
            # Clean up and return as columns
            cols = []
            current_col = []
            
            for word in words:
                if word and word[0].isupper():
                    if current_col:
                        cols.append(' '.join(current_col))
                    current_col = [word]
                else:
                    current_col.append(word)
            
            if current_col:
                cols.append(' '.join(current_col))
            
            if len(cols) >= 4:
                logger.warning(f"[RULES] Extracted columns from header line: {cols[:5]}...")
                return cols
    
    # Fallback to generic columns if we detected tabular but couldn't identify specific type
    logger.warning("[RULES] Using generic column set")
    return generic_cols


# =============================================================================
# LLM-BASED ANALYSIS
# =============================================================================

def analyze_pdf_with_llm(text_sample: str) -> Dict[str, Any]:
    """
    Ask LLM to analyze PDF content and determine if it's tabular.
    Returns structure info if tabular.
    """
    
    # Redact PII before sending to LLM
    redacted_sample = redact_pii(text_sample[:8000])
    
    prompt = f"""Analyze this text extracted from a PDF document.

TEXT SAMPLE:
{redacted_sample}

TASK: Determine if this is TABULAR DATA (like a report, spreadsheet, rate table, or data listing) or NARRATIVE TEXT (paragraphs, articles, documents).

Signs of TABULAR DATA:
- Repeated patterns of similar data across lines
- Column-like structure (numbers, codes, descriptions aligned)
- Headers followed by rows of data
- Lists of items with multiple attributes per item

Signs of NARRATIVE TEXT:
- Full sentences and paragraphs
- Articles, letters, or documents
- No repeating row structure

If TABULAR, identify the column headers that would represent this data.

Respond with ONLY valid JSON:

For TABULAR data:
{{"is_tabular": true, "columns": ["Column1", "Column2", "Column3"], "description": "Brief description of the data"}}

For NARRATIVE text:
{{"is_tabular": false, "description": "Brief description of the content"}}

JSON RESPONSE:"""

    response = call_llm(prompt)
    
    if not response:
        logger.warning("[LLM] No response from LLM, using rule-based detection...")
        rule_result = detect_tabular_by_rules(text_sample)
        
        # If rules detect tabular, try to infer columns from text
        if rule_result.get('is_tabular'):
            inferred_columns = infer_columns_from_text(text_sample)
            if inferred_columns:
                rule_result['columns'] = inferred_columns
                logger.warning(f"[RULES] Inferred {len(inferred_columns)} columns: {inferred_columns[:5]}...")
        
        return rule_result
    
    # Parse JSON from response
    try:
        # Find JSON object in response
        json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            logger.warning(f"[LLM] Analysis result: is_tabular={result.get('is_tabular')}, columns={result.get('columns', [])}")
            return result
        else:
            logger.warning(f"[LLM] No JSON found in response: {response[:300]}")
            return {"is_tabular": False, "error": "No JSON in response"}
    except json.JSONDecodeError as e:
        logger.warning(f"[LLM] JSON parse error: {e}")
        return {"is_tabular": False, "error": str(e)}


def parse_tabular_pdf_with_llm(text: str, columns: List[str], file_path: str = None) -> List[Dict[str, str]]:
    """
    Ask LLM to parse tabular PDF text into structured rows.
    Falls back to pdfplumber if LLM unavailable.
    """
    
    # Redact PII
    redacted_text = redact_pii(text)
    
    # Process in chunks if text is large
    max_chunk = 5000
    chunks = []
    
    # Split by page markers to keep pages together
    pages = redacted_text.split('--- PAGE ')
    current_chunk = ""
    
    for page in pages:
        if len(current_chunk) + len(page) < max_chunk:
            current_chunk += '--- PAGE ' + page if page else ''
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = '--- PAGE ' + page if page else ''
    
    if current_chunk:
        chunks.append(current_chunk)
    
    if not chunks:
        chunks = [redacted_text[:max_chunk]]
    
    all_rows = []
    col_json = json.dumps(columns)
    
    for chunk_num, chunk in enumerate(chunks):
        logger.warning(f"[LLM] Parsing chunk {chunk_num+1}/{len(chunks)} ({len(chunk)} chars)")
        
        prompt = f"""Parse this tabular data into JSON rows.

EXPECTED COLUMNS: {col_json}

DATA TO PARSE:
{chunk}

TASK: 
1. Extract each data row as a JSON object
2. Use the column names provided as keys
3. Skip headers, page numbers, totals, and non-data lines
4. Include ALL data rows you can find

Return ONLY a valid JSON array of objects. Example:
[
  {{{", ".join([f'"{col}": "value"' for col in columns[:3]])}}},
  {{{", ".join([f'"{col}": "value"' for col in columns[:3]])}}}
]

JSON ARRAY:"""

        response = call_llm(prompt, max_tokens=8000)
        
        if response:
            try:
                # Find JSON array in response
                array_match = re.search(r'\[[\s\S]*\]', response)
                if array_match:
                    rows = json.loads(array_match.group())
                    if isinstance(rows, list):
                        all_rows.extend(rows)
                        logger.warning(f"[LLM] Chunk {chunk_num+1}: parsed {len(rows)} rows")
            except json.JSONDecodeError as e:
                logger.warning(f"[LLM] Parse error on chunk {chunk_num+1}: {e}")
    
    logger.warning(f"[LLM] Total rows parsed: {len(all_rows)}")
    
    # If LLM failed and we have file path, try pdfplumber extraction
    if len(all_rows) == 0 and file_path and PDFPLUMBER_AVAILABLE:
        logger.warning("[LLM] LLM parsing failed, trying pdfplumber table extraction...")
        all_rows = parse_tabular_pdf_with_pdfplumber(file_path, columns)
    
    return all_rows


def parse_tabular_pdf_with_pdfplumber(file_path: str, columns: List[str]) -> List[Dict[str, str]]:
    """
    Extract tables from PDF using pdfplumber when LLM is unavailable.
    
    This is a fallback that uses pdfplumber's built-in table detection.
    """
    if not PDFPLUMBER_AVAILABLE:
        logger.warning("[PDFPLUMBER] pdfplumber not available")
        return []
    
    all_rows = []
    
    try:
        with pdfplumber.open(file_path) as pdf:
            logger.warning(f"[PDFPLUMBER] Processing {len(pdf.pages)} pages...")
            
            for page_num, page in enumerate(pdf.pages):
                try:
                    # Extract tables from page
                    tables = page.extract_tables()
                    
                    if not tables:
                        continue
                    
                    for table in tables:
                        if not table or len(table) < 2:
                            continue
                        
                        # First row might be header
                        header_row = table[0] if table else []
                        data_rows = table[1:] if len(table) > 1 else []
                        
                        # Check if first row looks like data (starts with code pattern)
                        if header_row and header_row[0]:
                            first_cell = str(header_row[0]).strip()
                            if re.match(r'^\d{4,6}$', first_cell) or re.match(r'^[A-Z]{2,5}\d*$', first_cell):
                                # First row is data, not header
                                data_rows = table
                        
                        for row in data_rows:
                            if not row or not any(row):
                                continue
                            
                            # Skip page headers/footers
                            row_text = ' '.join(str(c) for c in row if c)
                            if 'Page' in row_text and 'of' in row_text:
                                continue
                            if 'Select: All' in row_text or 'Last Page' in row_text:
                                continue
                            
                            # Create row dict using provided columns
                            row_dict = {}
                            for i, col in enumerate(columns):
                                if i < len(row) and row[i]:
                                    row_dict[col] = str(row[i]).strip()
                                else:
                                    row_dict[col] = ''
                            
                            # Only add if we have some data
                            if any(v for v in row_dict.values()):
                                all_rows.append(row_dict)
                
                except Exception as page_e:
                    logger.warning(f"[PDFPLUMBER] Page {page_num+1} error: {page_e}")
                    continue
        
        logger.warning(f"[PDFPLUMBER] Extracted {len(all_rows)} rows from PDF")
    
    except Exception as e:
        logger.error(f"[PDFPLUMBER] Table extraction failed: {e}")
    
    # If pdfplumber didn't find tables, try text-based parsing
    if len(all_rows) == 0:
        logger.warning("[PDFPLUMBER] No table structures found, trying text-based parsing...")
        all_rows = parse_tabular_text_by_patterns(file_path, columns)
    
    return all_rows


def parse_tabular_text_by_patterns(file_path: str, columns: List[str]) -> List[Dict[str, str]]:
    """
    Parse tabular PDF using text patterns when pdfplumber table extraction fails.
    
    Patterns are loaded from /app/config/pdf_patterns.json if available,
    otherwise uses sensible defaults.
    """
    # Load patterns from config or use defaults
    patterns = load_pdf_parsing_patterns()
    
    all_rows = []
    
    try:
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                try:
                    text = page.extract_text() or ""
                    lines = text.split('\n')
                    
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        
                        # Skip headers, footers, page markers
                        if any(skip in line for skip in patterns.get('skip_patterns', [])):
                            continue
                        
                        # Try each code pattern
                        row = None
                        for pattern_def in patterns.get('code_patterns', []):
                            match = re.match(pattern_def['regex'], line)
                            if match:
                                row = parse_line_with_pattern(match, line, pattern_def, patterns, columns)
                                break
                        
                        if row:
                            all_rows.append(row)
                
                except Exception as page_e:
                    logger.warning(f"[TEXT-PARSE] Page {page_num+1} error: {page_e}")
                    continue
        
        logger.warning(f"[TEXT-PARSE] Extracted {len(all_rows)} rows via text patterns")
        
    except Exception as e:
        logger.error(f"[TEXT-PARSE] Text parsing failed: {e}")
    
    return all_rows


def load_pdf_parsing_patterns() -> Dict[str, Any]:
    """
    Load PDF parsing patterns from config file or return defaults.
    
    Config file: /app/config/pdf_patterns.json
    """
    config_paths = [
        '/app/config/pdf_patterns.json',
        'config/pdf_patterns.json',
        os.path.join(os.path.dirname(__file__), 'pdf_patterns.json')
    ]
    
    for path in config_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    patterns = json.load(f)
                    logger.info(f"[TEXT-PARSE] Loaded patterns from {path}")
                    return patterns
            except Exception as e:
                logger.warning(f"[TEXT-PARSE] Failed to load {path}: {e}")
    
    # Default patterns
    return {
        'skip_patterns': [
            'Page ', 'Select: All', 'Last Page',
            'Code Tax Category', 'Description Rule'
        ],
        'code_patterns': [
            {
                'name': 'numeric_code',
                'regex': r'^(\d{5})\s+([A-Z]{3,6})\s+(.+)$',
                'groups': {'Code': 1, 'Tax Category': 2, 'rest': 3}
            },
            {
                'name': 'alpha_code', 
                'regex': r'^([A-Z][A-Z0-9]{1,5})\s+([A-Z]{3,6})\s+(.+)$',
                'groups': {'Code': 1, 'Tax Category': 2, 'rest': 3}
            }
        ],
        'calculation_rules': [
            'Pay rate * hours * rate factor',
            'Flat amount',
            'Expression',
            'Hours * flat amount',
            'Coefficient OT'
        ],
        'flags': {
            'reg_pay_markers': ['ü', '✓'],
            'accumulator_markers': [' Z ', ' Z$']
        }
    }


def parse_line_with_pattern(match, line: str, pattern_def: Dict, patterns: Dict, columns: List[str]) -> Dict[str, str]:
    """
    Parse a matched line using pattern definition.
    """
    groups = pattern_def.get('groups', {})
    row = {}
    
    # Extract named groups
    for field, group_num in groups.items():
        if field != 'rest' and group_num <= len(match.groups()):
            row[field] = match.group(group_num)
    
    # Get the "rest" portion for further parsing
    rest_group = groups.get('rest')
    rest = match.group(rest_group) if rest_group and rest_group <= len(match.groups()) else ''
    
    # Extract calculation rule
    for calc in patterns.get('calculation_rules', []):
        if calc.lower() in rest.lower():
            row['Calculation Rule'] = calc
            rest = rest.replace(calc, '').strip()
            break
    
    # Extract rate factor
    rate_match = re.search(r'\b(\d+\.?\d*)\b', rest)
    if rate_match:
        row['Rate Factor'] = rate_match.group(1)
    
    # Check flags
    flags = patterns.get('flags', {})
    if any(m in line for m in flags.get('reg_pay_markers', [])):
        row['Reg Pay'] = 'Yes'
    
    for marker in flags.get('accumulator_markers', []):
        if marker.rstrip('$') in line or (marker.endswith('$') and line.endswith(marker[:-1])):
            row['Accumulators'] = 'Z'
            break
    
    # Fill remaining columns
    for col in columns:
        if col not in row:
            row[col] = ''
    
    return row


# =============================================================================
# DUCKDB STORAGE
# =============================================================================

def store_to_duckdb(rows: List[Dict], project: str, filename: str, project_id: str = None) -> Dict[str, Any]:
    """Store parsed rows to DuckDB."""
    if not PANDAS_AVAILABLE:
        return {"success": False, "error": "pandas not available"}
    
    if not rows:
        return {"success": False, "error": "No rows to store"}
    
    try:
        import duckdb
        
        # Create DataFrame
        df = pd.DataFrame(rows)
        
        if df.empty:
            return {"success": False, "error": "DataFrame is empty"}
        
        # Clean table name
        clean_project = re.sub(r'[^a-zA-Z0-9_]', '_', project)
        clean_filename = re.sub(r'[^a-zA-Z0-9_]', '_', filename.rsplit('.', 1)[0])
        table_name = f"{clean_project}__{clean_filename}"
        
        # Connect to DuckDB
        db_path = os.getenv('DUCKDB_PATH', '/data/xlr8.duckdb')
        conn = duckdb.connect(db_path)
        
        # Create/replace table
        conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
        conn.execute(f'CREATE TABLE "{table_name}" AS SELECT * FROM df')
        
        row_count = conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]
        
        # Store metadata
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS _pdf_tables (
                    table_name VARCHAR PRIMARY KEY,
                    source_file VARCHAR,
                    project VARCHAR,
                    project_id VARCHAR,
                    row_count INTEGER,
                    columns VARCHAR,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                INSERT OR REPLACE INTO _pdf_tables (table_name, source_file, project, project_id, row_count, columns)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [table_name, filename, project, project_id, row_count, json.dumps(list(df.columns))])
        except Exception as e:
            logger.warning(f"[DUCKDB] Could not store metadata: {e}")
        
        conn.close()
        
        logger.warning(f"[DUCKDB] Stored {row_count} rows to table '{table_name}'")
        
        return {
            "success": True,
            "table_name": table_name,
            "row_count": row_count,
            "columns": list(df.columns)
        }
        
    except Exception as e:
        logger.error(f"[DUCKDB] Storage failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def process_pdf_intelligently(
    file_path: str,
    project: str,
    filename: str,
    project_id: str = None,
    status_callback=None
) -> Dict[str, Any]:
    """
    Smart PDF processing using LLM for analysis and parsing.
    
    Flow:
    1. Extract text from PDF
    2. Redact PII
    3. Ask LLM: Is this tabular?
    4. If yes: LLM parses to rows → DuckDB
    5. Return text for ChromaDB either way
    """
    
    result = {
        'success': False,
        'storage_used': [],
        'duckdb_result': None,
        'chromadb_result': None,
        'analysis': None,
        'error': None
    }
    
    def update_status(msg, progress=None):
        if status_callback:
            status_callback(msg, progress)
        logger.warning(f"[SMART-PDF] {msg}")
    
    try:
        # Step 1: Extract text
        update_status("Extracting text from PDF...", 10)
        text = extract_pdf_text(file_path)
        
        if not text or len(text.strip()) < 50:
            result['error'] = "Could not extract text from PDF"
            result['success'] = True  # Still allow ChromaDB with whatever we got
            result['chromadb_result'] = {'text_content': text or '', 'text_length': len(text or '')}
            result['storage_used'].append('chromadb')
            return result
        
        update_status(f"Extracted {len(text):,} characters", 20)
        result['chromadb_result'] = {'text_content': text, 'text_length': len(text)}
        
        # Step 2: Analyze with LLM (PII is redacted inside the function)
        update_status("Analyzing PDF structure with AI...", 30)
        analysis = analyze_pdf_with_llm(text)
        result['analysis'] = analysis
        
        # Step 3: If tabular, parse and store to DuckDB
        if analysis.get('is_tabular') and analysis.get('columns'):
            columns = analysis['columns']
            update_status(f"Detected tabular data with {len(columns)} columns, parsing...", 50)
            
            # Parse with LLM (falls back to pdfplumber if LLM unavailable)
            rows = parse_tabular_pdf_with_llm(text, columns, file_path=file_path)
            
            if rows:
                update_status(f"Parsed {len(rows)} rows, storing to DuckDB...", 70)
                
                # Store to DuckDB
                duckdb_result = store_to_duckdb(rows, project, filename, project_id)
                result['duckdb_result'] = duckdb_result
                
                if duckdb_result.get('success'):
                    result['storage_used'].append('duckdb')
                    update_status(f"✓ Stored {duckdb_result['row_count']} rows to DuckDB", 85)
                else:
                    update_status(f"⚠ DuckDB storage failed: {duckdb_result.get('error')}", 85)
            else:
                update_status("No rows could be parsed from tabular data", 85)
        else:
            update_status("PDF classified as narrative text (not tabular)", 50)
        
        # ChromaDB decision: Skip for large tabular PDFs that went to DuckDB
        text_length = len(text) if text else 0
        duckdb_success = 'duckdb' in result['storage_used']
        is_tabular = analysis.get('is_tabular', False)
        
        if is_tabular and duckdb_success and text_length > 500000:
            # Large tabular PDF successfully in DuckDB - skip ChromaDB
            logger.warning(f"[SMART-PDF] Skipping ChromaDB for large tabular PDF ({text_length:,} chars)")
            update_status("✓ Large tabular PDF stored to DuckDB only (too large for semantic search)", 95)
        else:
            # Include ChromaDB for semantic search
            result['storage_used'].append('chromadb')
        
        result['success'] = True
        
        update_status("PDF processing complete", 100)
        return result
        
    except Exception as e:
        logger.error(f"[SMART-PDF] Processing failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        result['error'] = str(e)
        # Still try to return text for ChromaDB if not too large
        text_content = result.get('chromadb_result', {}).get('text_content', '')
        if len(text_content) > 500000:
            logger.warning(f"[SMART-PDF] Skipping ChromaDB fallback - text too large ({len(text_content):,} chars)")
        else:
            if 'chromadb_result' not in result or not result['chromadb_result']:
                result['chromadb_result'] = {'text_content': '', 'text_length': 0}
            result['storage_used'].append('chromadb')
        return result


# Alias for backward compatibility
smart_process_pdf = process_pdf_intelligently
