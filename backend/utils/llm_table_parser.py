"""
LLM Table Parser - Shared utility for LLM-based text parsing.

Extracted from the WORKING RegisterExtractor patterns.
Used by both register_extractor.py (payroll) and pdf_vision_analyzer.py (general).

Architecture:
- One implementation of LLM cascade (Groq → Ollama → Claude)
- One implementation of PII redaction
- One implementation of JSON response parsing
- Domain-specific callers provide their own prompts

This follows ARCHITECTURE.md Tenet #8: "No duplicate systems - One way to do each thing"

Author: XLR8 Team
"""

import os
import re
import json
import time
import logging
import requests
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# Try to import LLM orchestrator for consistent Claude calls
_orchestrator = None
try:
    from utils.llm_orchestrator import LLMOrchestrator
    _orchestrator = LLMOrchestrator()
except ImportError:
    try:
        from backend.utils.llm_orchestrator import LLMOrchestrator
        _orchestrator = LLMOrchestrator()
    except ImportError:
        logger.warning("[LLM-PARSER] LLMOrchestrator not available")


# =============================================================================
# PII REDACTOR - Same patterns that work in RegisterExtractor
# =============================================================================

class PIIRedactor:
    """
    Redact PII before sending to any LLM.
    
    Extracted from register_extractor.py - PROVEN TO WORK.
    """
    
    PATTERNS = {
        'ssn': [
            r'\b\d{3}-\d{2}-\d{4}\b',
            r'\b\d{3}\s\d{2}\s\d{4}\b',
        ],
        'ein': [
            r'\b\d{2}-\d{7}\b',
        ],
        'bank_account': [
            r'\b\d{10,17}\b',
        ],
        'credit_card': [
            r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
        ],
        'phone': [
            r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',
            r'\(\d{3}\)\s*\d{3}[-.\s]?\d{4}\b',
        ],
        'email': [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        ],
    }
    
    PLACEHOLDERS = {
        'ssn': '[SSN]',
        'ein': '[EIN]',
        'bank_account': '[ACCOUNT]',
        'credit_card': '[CC]',
        'phone': '[PHONE]',
        'email': '[EMAIL]',
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
                    self.redaction_log.append(f"{pii_type}: {len(matches)}")
                    redacted = re.sub(pattern, placeholder, redacted, flags=re.IGNORECASE)
        
        return redacted
    
    def get_stats(self) -> Dict:
        return {
            'total_redacted': self.redaction_count,
            'details': self.redaction_log
        }


# =============================================================================
# JSON RESPONSE PARSER - Same robust parsing from RegisterExtractor
# =============================================================================

def parse_json_response(response_text: str) -> List[Dict]:
    """
    Parse JSON array from LLM response with multiple fallback strategies.
    
    Handles:
    - Markdown code blocks
    - Truncated responses
    - Trailing commas
    - Malformed JSON
    
    Extracted from RegisterExtractor._parse_json_response - PROVEN TO WORK.
    """
    if not response_text:
        return []
    
    text = response_text.strip()
    
    # Remove markdown code fences
    text = re.sub(r'^```json\s*', '', text)
    text = re.sub(r'^```\s*', '', text)
    text = re.sub(r'\s*```\s*$', '', text)
    
    # Find array bounds
    start_idx = text.find('[')
    end_idx = text.rfind(']')
    
    if start_idx < 0:
        logger.warning("[LLM-PARSER] No JSON array found in response")
        return []
    
    if end_idx < start_idx:
        # Try to fix truncated array
        last_brace = text.rfind('}')
        if last_brace > start_idx:
            text = text[:last_brace + 1] + ']'
            end_idx = len(text) - 1
        else:
            return []
    
    json_str = text[start_idx:end_idx + 1]
    
    # Fix common LLM JSON issues
    json_str = re.sub(r',\s*]', ']', json_str)  # Trailing comma in array
    json_str = re.sub(r',\s*}', '}', json_str)  # Trailing comma in object
    
    # Try direct parse
    try:
        data = json.loads(json_str)
        if isinstance(data, list):
            return [row for row in data if isinstance(row, dict)]
        return []
    except json.JSONDecodeError:
        pass
    
    # Fallback: Extract objects one by one
    rows = []
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
                try:
                    obj = json.loads(obj_str)
                    if isinstance(obj, dict):
                        rows.append(obj)
                except json.JSONDecodeError:
                    pass
                obj_start = None
    
    return rows


# =============================================================================
# LLM CASCADE - Uses LLMOrchestrator for consistent handling
# =============================================================================

def call_groq(prompt: str, max_tokens: int = 8192, temperature: float = 0.1) -> Optional[str]:
    """
    Call Groq via LLMOrchestrator.
    Falls back to direct call only if orchestrator unavailable.
    """
    global _orchestrator
    
    if _orchestrator:
        # Use orchestrator's synthesize which tries local first then Claude
        # But we want Groq specifically - check if orchestrator supports it
        try:
            result = _orchestrator.synthesize_answer(
                question=prompt,
                context="",
                use_claude_fallback=False  # Don't fall back to Claude here
            )
            if result.get('success') and result.get('response'):
                return result['response']
        except Exception as e:
            logger.debug(f"[LLM-PARSER] Orchestrator synthesize failed: {e}")
    
    # If orchestrator doesn't have Groq, this function returns None
    # and the cascade will try Ollama next
    return None


def call_ollama(prompt: str, model: str = "deepseek-r1:14b", max_tokens: int = 8192) -> Optional[str]:
    """
    Call Ollama API.
    Tries configured endpoint with auth if available.
    """
    ollama_url = os.getenv("LLM_ENDPOINT", "").rstrip('/')
    
    if not ollama_url:
        return None
    
    ollama_username = os.getenv("LLM_USERNAME", "")
    ollama_password = os.getenv("LLM_PASSWORD", "")
    
    try:
        auth = None
        if ollama_username and ollama_password:
            from requests.auth import HTTPBasicAuth
            auth = HTTPBasicAuth(ollama_username, ollama_password)
        
        response = requests.post(
            f"{ollama_url}/api/generate",
            auth=auth,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": max_tokens}
            },
            timeout=180
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('response', '')
        else:
            logger.warning(f"[LLM-PARSER] Ollama {model} returned {response.status_code}")
            return None
            
    except Exception as e:
        logger.warning(f"[LLM-PARSER] Ollama {model} failed: {e}")
        return None


def call_claude(prompt: str, max_tokens: int = 8192) -> Optional[str]:
    """
    Call Claude API via LLMOrchestrator.
    Only used when local LLMs fail.
    """
    global _orchestrator
    
    if not _orchestrator:
        logger.warning("[LLM-PARSER] LLMOrchestrator not available for Claude call")
        return None
    
    try:
        system_prompt = "You are a precise data extraction assistant. Extract table data and return valid JSON."
        
        # Use synthesize_answer with Claude fallback enabled
        result = _orchestrator.synthesize_answer(
            question=prompt,
            context="",
            expert_prompt=system_prompt,
            use_claude_fallback=True
        )
        
        if result.get('success') and result.get('response'):
            logger.info(f"[LLM-PARSER] Got response from {result.get('model_used', 'claude')}")
            return result['response']
        
        return None
        
    except Exception as e:
        logger.error(f"[LLM-PARSER] Claude via orchestrator failed: {e}")
        return None


def call_llm_cascade(prompt: str, max_tokens: int = 8192) -> Tuple[Optional[str], str]:
    """
    Call LLM for TABLE/JSON extraction.
    
    Uses qwen2.5-coder:14b - best model for structured JSON output.
    
    NOTE: Groq skipped for table parsing - returns incomplete results
    NOTE: Does NOT use deepseek-r1 (reasoning model, outputs <think> tags)
    NOTE: Does NOT use mistral:7b (poor JSON output quality)
    NOTE: Does NOT fall back to Claude API (too expensive for bulk)
    
    Returns:
        Tuple of (response_text, llm_used)
    """
    # Use qwen2.5-coder:14b directly - best for structured JSON output
    # Groq skipped: returns incomplete table extractions
    logger.info("[LLM-PARSER] Using qwen2.5-coder:14b for table extraction...")
    response = call_ollama(prompt, 'qwen2.5-coder:14b', max_tokens)
    if response:
        return response, "ollama-qwen2.5-coder:14b"
    
    # No fallback - if qwen fails, other local models won't do better
    logger.warning("[LLM-PARSER] qwen2.5-coder:14b unavailable - text parsing skipped")
    return None, "none"


# =============================================================================
# MAIN ENTRY POINT - Parse table text with LLM
# =============================================================================

def parse_table_with_llm(
    text: str,
    columns: List[str],
    table_description: str = "",
    redact_pii: bool = True
) -> Dict[str, Any]:
    """
    Parse tabular data from text using LLM.
    
    This is the DOMAIN-AGNOSTIC entry point.
    Uses the same LLM cascade as RegisterExtractor but with generic prompts.
    
    Args:
        text: Raw text from PDF/document
        columns: Column names (from Vision or known structure)
        table_description: What this table contains (helps LLM understand context)
        redact_pii: Whether to redact PII before sending (default True, NON-NEGOTIABLE for EE data)
        
    Returns:
        Dict with:
        - rows: List[Dict] - parsed data rows
        - llm_used: str - which LLM was used
        - pii_redacted: int - count of PII items redacted
        - success: bool
    """
    result = {
        'rows': [],
        'llm_used': 'none',
        'pii_redacted': 0,
        'success': False
    }
    
    if not text or not columns:
        return result
    
    # Step 1: Redact PII (NON-NEGOTIABLE)
    if redact_pii:
        redactor = PIIRedactor()
        text = redactor.redact(text)
        result['pii_redacted'] = redactor.redaction_count
        if redactor.redaction_count > 0:
            logger.info(f"[LLM-PARSER] Redacted {redactor.redaction_count} PII items")
    
    # Step 2: Build prompt (generic, domain-agnostic)
    columns_str = ", ".join(columns)
    
    prompt = f"""Extract ALL tabular data rows from this text into a JSON array.

TABLE STRUCTURE:
Columns: {columns_str}
Description: {table_description or "Tabular data"}

TEXT TO PARSE:
{text}

INSTRUCTIONS:
1. Extract EVERY data row - do not skip or summarize
2. Skip only: headers, footers, letterhead, company info, page numbers
3. Each row = one JSON object with the exact column names above
4. Use "" for empty cells
5. Preserve exact values - don't modify
6. IMPORTANT: Extract ALL rows, not just the first few

Return ONLY a valid JSON array. No markdown, no explanation.
Format: [{{"column1": "value1", "column2": "value2"}}]"""

    # Step 3: Call LLM cascade
    response, llm_used = call_llm_cascade(prompt)
    result['llm_used'] = llm_used
    
    if not response:
        logger.error("[LLM-PARSER] All LLMs failed")
        return result
    
    # Log response size to detect truncation
    logger.warning(f"[LLM-PARSER] {llm_used} response: {len(response)} chars")
    
    # Step 4: Parse JSON response
    rows = parse_json_response(response)
    
    if rows:
        result['rows'] = rows
        result['success'] = True
        logger.warning(f"[LLM-PARSER] Extracted {len(rows)} rows via {llm_used}")
    else:
        logger.warning(f"[LLM-PARSER] {llm_used} returned no parseable rows")
    
    return result


def parse_pages_with_llm(
    pages_text: List[str],
    columns: List[str],
    table_description: str = "",
    redact_pii: bool = True
) -> Dict[str, Any]:
    """
    Parse multiple pages of table data.
    
    For small documents: combines all pages and sends once.
    For large documents (>50 pages): processes in parallel chunks.
    
    Args:
        pages_text: List of text strings, one per page
        columns: Column names
        table_description: What this table contains
        redact_pii: Whether to redact PII (NON-NEGOTIABLE for EE data)
        
    Returns:
        Same as parse_table_with_llm
    """
    if not pages_text:
        return {'rows': [], 'llm_used': 'none', 'pii_redacted': 0, 'success': False}
    
    CHUNK_SIZE = 10  # Pages per chunk - larger = faster, smaller = more accurate
    
    # For small documents (5 pages or less), combine and send once
    if len(pages_text) <= CHUNK_SIZE:
        combined_text = "\n\n--- PAGE BREAK ---\n\n".join(pages_text)
        return parse_table_with_llm(
            text=combined_text,
            columns=columns,
            table_description=table_description,
            redact_pii=redact_pii
        )
    
    # For larger documents, process in chunks to avoid overwhelming LLM
    logger.warning(f"[LLM-PARSER] Document ({len(pages_text)} pages) - processing in {CHUNK_SIZE}-page chunks")
    all_rows = []
    pii_total = 0
    llm_used = 'none'
    
    chunks = [pages_text[i:i + CHUNK_SIZE] for i in range(0, len(pages_text), CHUNK_SIZE)]
    
    for chunk_idx, chunk in enumerate(chunks):
        start_page = chunk_idx * CHUNK_SIZE + 1
        end_page = min((chunk_idx + 1) * CHUNK_SIZE, len(pages_text))
        
        combined_text = "\n\n--- PAGE BREAK ---\n\n".join(chunk)
        
        chunk_result = parse_table_with_llm(
            text=combined_text,
            columns=columns,
            table_description=table_description,
            redact_pii=redact_pii
        )
        
        if chunk_result.get('rows'):
            all_rows.extend(chunk_result['rows'])
            pii_total += chunk_result.get('pii_redacted', 0)
            llm_used = chunk_result.get('llm_used', llm_used)
        
        logger.warning(f"[LLM-PARSER] Chunk {chunk_idx + 1}/{len(chunks)} (pages {start_page}-{end_page}): {len(chunk_result.get('rows', []))} rows")
    
    return {
        'rows': all_rows,
        'llm_used': llm_used,
        'pii_redacted': pii_total,
        'success': len(all_rows) > 0
    }
