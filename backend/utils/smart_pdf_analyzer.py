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
    'ssn': (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN-REDACTED]'),
    'ssn_no_dash': (r'\b(?<!\d)\d{9}(?!\d)\b', '[SSN-REDACTED]'),  # 9 digits not part of larger number
    # NOTE: EIN/FEIN removed - these are public business identifiers, not personal PII
    # 'ein': (r'\b\d{2}-\d{7}\b', '[EIN-REDACTED]'),
    'phone': (r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b', '[PHONE-REDACTED]'),
    'email': (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL-REDACTED]'),
    'credit_card': (r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CC-REDACTED]'),
    'dob_slash': (r'\b\d{1,2}/\d{1,2}/\d{2,4}\b', '[DATE-REDACTED]'),  # MM/DD/YYYY or MM/DD/YY
    'dob_dash': (r'\b\d{1,2}-\d{1,2}-\d{2,4}\b', '[DATE-REDACTED]'),  # MM-DD-YYYY
}

def redact_pii(text: str) -> str:
    """Redact PII from text before sending to LLM."""
    redacted = text
    
    for name, (pattern, replacement) in PII_PATTERNS.items():
        if replacement:
            redacted = re.sub(pattern, replacement, redacted)
    
    return redacted


# =============================================================================
# LLM CLIENT
# =============================================================================

def get_llm_config() -> Dict[str, str]:
    """Get LLM configuration from environment."""
    return {
        'url': os.getenv('LLM_INFERENCE_URL') or os.getenv('OLLAMA_URL') or os.getenv('RUNPOD_URL') or os.getenv('LLM_ENDPOINT'),
        'username': os.getenv('LLM_USERNAME', ''),
        'password': os.getenv('LLM_PASSWORD', ''),
        'model': os.getenv('LLM_MODEL') or os.getenv('LLM_DEFAULT_MODEL', 'llama3.1:8b-instruct-q8_0')
    }


def call_llm(prompt: str, max_tokens: int = 4000) -> Optional[str]:
    """Call LLM for text generation."""
    config = get_llm_config()
    
    if not config['url']:
        logger.error("[LLM] No LLM URL configured (set LLM_ENDPOINT, LLM_INFERENCE_URL, OLLAMA_URL, or RUNPOD_URL)")
        return None
    
    url = f"{config['url'].rstrip('/')}/api/generate"
    
    payload = {
        "model": config['model'],
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": 0.1  # Low temp for structured output
        }
    }
    
    try:
        auth = None
        if config['username'] and config['password']:
            auth = HTTPBasicAuth(config['username'], config['password'])
        
        logger.warning(f"[LLM] Calling {url} with model {config['model']}")
        response = requests.post(
            url,
            json=payload,
            auth=auth,
            timeout=180  # 3 minutes for large parses
        )
        response.raise_for_status()
        
        result = response.json()
        return result.get('response', '')
        
    except requests.Timeout:
        logger.error(f"[LLM] Timeout calling {url}")
        return None
    except requests.RequestException as e:
        logger.error(f"[LLM] Request failed: {e}")
        return None
    except Exception as e:
        logger.error(f"[LLM] Unexpected error: {e}")
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
    
    # Check for UKG-specific patterns
    ukg_patterns = ['Earnings Code', 'Deduction Code', 'Company Code', 'Tax Category', 
                    'Employee Number', 'Pay Group', 'Rate Table', 'Filing Status']
    has_ukg = any(p.lower() in text_sample.lower() for p in ukg_patterns)
    
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
    
    if has_ukg and (spacing_ratio > 0.2 or numeric_ratio > 0.3):
        is_tabular = True
        confidence = max(confidence, 0.8)
        reasons.append("ukg_patterns_detected")
    
    # Large documents with moderate signals should lean tabular
    if len(text_sample) > 100000 and (spacing_ratio > 0.25 or numeric_ratio > 0.25):
        is_tabular = True
        confidence = max(confidence, 0.7)
        reasons.append(f"large_doc_with_patterns")
    
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
            "has_ukg_patterns": has_ukg
        }
    }
    
    logger.warning(f"[RULES] Detection result: is_tabular={is_tabular}, reasons={reasons}")
    return result


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
        return detect_tabular_by_rules(text_sample)
    
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


def parse_tabular_pdf_with_llm(text: str, columns: List[str]) -> List[Dict[str, str]]:
    """
    Ask LLM to parse tabular PDF text into structured rows.
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
    return all_rows


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
            
            # Parse with LLM
            rows = parse_tabular_pdf_with_llm(text, columns)
            
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
