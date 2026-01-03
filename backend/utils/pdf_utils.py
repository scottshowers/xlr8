"""
PDF Utilities - Shared functions for PDF processing
====================================================

Extracted from Register Extractor to provide consistency across:
- smart_pdf_analyzer.py (tabular PDF detection and parsing)
- register_extractor.py (pay register extraction)

UTILITIES:
- PIIRedactor: Redact sensitive data before LLM processing
- parse_json_array: Robust JSON array parsing with fallbacks
- repair_json: Fix common LLM JSON errors
- call_groq: Groq API wrapper with retry logic

Author: XLR8 Team
Version: 1.0.0
"""

import re
import json
import time
import logging
import requests
import os
from typing import List, Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)

# Import LLM orchestrator for consistent LLM handling
_pdf_orchestrator = None
try:
    from utils.llm_orchestrator import LLMOrchestrator
    _pdf_orchestrator = LLMOrchestrator()
except ImportError:
    try:
        from backend.utils.llm_orchestrator import LLMOrchestrator
        _pdf_orchestrator = LLMOrchestrator()
    except ImportError:
        logger.warning("[PDF-UTILS] LLMOrchestrator not available")


# =============================================================================
# PII REDACTION (from register_extractor)
# =============================================================================

class PIIRedactor:
    """
    Redact PII before sending to any LLM.
    
    Handles: SSN, bank accounts, credit cards, addresses, emails, phone numbers.
    """
    
    PATTERNS = {
        'ssn': [
            r'\b\d{3}-\d{2}-\d{4}\b',           # 123-45-6789
            r'\b\d{3}\s\d{2}\s\d{4}\b',         # 123 45 6789
            r'\b\d{9}\b(?=.*(?:ssn|social))',   # 123456789 near SSN keyword
        ],
        'bank_account': [
            r'\b\d{8,17}\b(?=.*(?:account|acct|routing|aba))',
            r'\b\d{9}\b(?=.*(?:routing|aba))',
        ],
        'credit_card': [
            r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
        ],
        'email': [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        ],
        'phone': [
            r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # 123-456-7890
            r'\(\d{3}\)\s*\d{3}[-.\s]?\d{4}\b',    # (123) 456-7890
        ],
        'address': [
            r'\b\d{1,5}\s+[\w\s]+(?:street|st|avenue|ave|road|rd|drive|dr|lane|ln|way|court|ct|boulevard|blvd)\.?\s*(?:#?\s*\d+[a-z]?)?\b',
        ],
    }
    
    PLACEHOLDERS = {
        'ssn': '[SSN-REDACTED]',
        'bank_account': '[ACCOUNT-REDACTED]',
        'credit_card': '[CC-REDACTED]',
        'email': '[EMAIL-REDACTED]',
        'phone': '[PHONE-REDACTED]',
        'address': '[ADDRESS-REDACTED]',
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
        """Get redaction statistics."""
        return {
            'total_redacted': self.redaction_count,
            'details': self.redaction_log
        }


# Singleton instance for simple use
_redactor = PIIRedactor()

def redact_pii(text: str) -> str:
    """Simple function to redact PII from text."""
    return _redactor.redact(text)

def get_redaction_stats() -> Dict:
    """Get stats from last redaction."""
    return _redactor.get_stats()


# =============================================================================
# JSON REPAIR AND PARSING
# =============================================================================

def repair_json(text: str) -> str:
    """
    Attempt to repair common JSON errors from LLM output.
    
    Fixes:
    - Markdown code blocks
    - Trailing commas
    - Single quotes (in some cases)
    - Missing array bounds
    """
    if not text:
        return text
    
    # Remove markdown code blocks
    text = re.sub(r'^```json\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^```\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'\s*```\s*$', '', text)
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    # Fix trailing commas before ] or }
    text = re.sub(r',\s*]', ']', text)
    text = re.sub(r',\s*}', '}', text)
    
    # Ensure array brackets
    if not text.startswith('['):
        array_start = text.find('[')
        if array_start != -1:
            text = text[array_start:]
    
    # Try to fix unclosed array
    if text.startswith('[') and not text.endswith(']'):
        # Find last complete object
        last_brace = text.rfind('}')
        if last_brace > 0:
            text = text[:last_brace + 1] + ']'
    
    return text


def parse_json_array(
    response_text: str, 
    normalizer: Callable[[Dict], Dict] = None
) -> List[Dict]:
    """
    Parse JSON array from LLM response with multiple fallback strategies.
    
    Extracted from register_extractor._parse_json_response
    
    Args:
        response_text: Raw LLM response
        normalizer: Optional function to normalize each parsed object
        
    Returns:
        List of parsed dictionaries
    """
    text = repair_json(response_text)
    
    # Find array bounds
    start_idx = text.find('[')
    end_idx = text.rfind(']')
    
    if start_idx < 0:
        logger.warning("[JSON] No JSON array found in response")
        return []
    
    if end_idx < start_idx:
        # Try to recover by adding closing bracket after last object
        last_brace = text.rfind('}')
        if last_brace > start_idx:
            text = text[:last_brace + 1] + ']'
            end_idx = len(text) - 1
        else:
            return []
    
    json_str = text[start_idx:end_idx + 1]
    
    # Try direct parse first
    try:
        data = json.loads(json_str)
        if isinstance(data, list):
            results = [d for d in data if isinstance(d, dict)]
            if normalizer:
                results = [normalizer(r) for r in results]
            logger.info(f"[JSON] Direct parse successful: {len(results)} objects")
            return results
    except json.JSONDecodeError as e:
        logger.warning(f"[JSON] Direct parse failed: {e}")
    
    # Fallback: Extract objects one by one using depth tracking
    logger.info("[JSON] Attempting object-by-object extraction...")
    objects = extract_json_objects(json_str)
    
    if normalizer:
        objects = [normalizer(o) for o in objects if o]
    
    logger.info(f"[JSON] Object extraction found: {len(objects)} objects")
    return objects


def extract_json_objects(json_str: str) -> List[Dict]:
    """
    Extract individual JSON objects from a potentially malformed array.
    
    Uses depth tracking to find complete {...} objects even when
    the overall array structure is broken.
    """
    objects = []
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
                obj = try_parse_object(obj_str)
                if obj:
                    objects.append(obj)
                obj_start = None
    
    return objects


def try_parse_object(obj_str: str) -> Optional[Dict]:
    """
    Try to parse a single JSON object string.
    
    Attempts repairs before giving up.
    """
    # Apply basic repairs
    obj_str = re.sub(r',\s*}', '}', obj_str)
    obj_str = re.sub(r',\s*]', ']', obj_str)
    
    try:
        obj = json.loads(obj_str)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    
    return None


# =============================================================================
# GROQ API WRAPPER - Via LLMOrchestrator
# =============================================================================

def call_groq(
    prompt: str,
    model: str = "llama-3.3-70b-versatile",
    max_tokens: int = 8192,
    temperature: float = 0.1,
    max_retries: int = 3,
    retry_delay: int = 5,
    timeout: int = 60
) -> Optional[str]:
    """
    Call Groq API via LLMOrchestrator.
    
    Args:
        prompt: The prompt to send
        model: Groq model name (ignored - orchestrator handles model selection)
        max_tokens: Maximum tokens in response
        temperature: Sampling temperature
        max_retries: Number of retry attempts (handled by orchestrator)
        retry_delay: Base delay between retries
        timeout: Request timeout in seconds
        
    Returns:
        Response text or None if failed
    """
    global _pdf_orchestrator
    
    if not _pdf_orchestrator:
        logger.warning("[GROQ] LLMOrchestrator not available")
        return None
    
    try:
        # Use orchestrator's synthesize which tries local first, then Claude
        result = _pdf_orchestrator.synthesize_answer(
            question=prompt,
            context="",
            use_claude_fallback=False  # Don't fall back to Claude for Groq replacement
        )
        
        if result.get('success') and result.get('response'):
            return result['response']
        
        logger.warning(f"[GROQ] LLM via orchestrator failed: {result.get('error')}")
        return None
        
    except Exception as e:
        logger.error(f"[GROQ] Request failed: {e}")
        return None


# =============================================================================
# OLLAMA API WRAPPER  
# =============================================================================

def call_ollama(
    prompt: str,
    model: str = "mistral:7b-instruct-v0.3-q8_0",
    max_tokens: int = 4000,
    timeout: int = 180
) -> Optional[str]:
    """
    Call Ollama API for local LLM inference.
    
    Args:
        prompt: The prompt to send
        model: Ollama model name
        max_tokens: Maximum tokens in response
        timeout: Request timeout in seconds
        
    Returns:
        Response text or None if failed
    """
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_user = os.getenv("OLLAMA_USER", "")
    ollama_pass = os.getenv("OLLAMA_PASS", "")
    
    url = f"{ollama_url}/api/generate"
    
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": 0.1
        }
    }
    
    auth = None
    if ollama_user and ollama_pass:
        auth = requests.auth.HTTPBasicAuth(ollama_user, ollama_pass)
    
    try:
        response = requests.post(url, json=payload, auth=auth, timeout=timeout)
        response.raise_for_status()
        result = response.json()
        return result.get('response', '')
        
    except requests.exceptions.RequestException as e:
        logger.warning(f"[OLLAMA] Request failed: {e}")
        return None


def call_llm(
    prompt: str,
    max_tokens: int = 4000,
    prefer_groq: bool = False,
    model_ollama: str = "mistral:7b-instruct-v0.3-q8_0",
    model_groq: str = "llama-3.3-70b-versatile"
) -> Optional[str]:
    """
    Call LLM with automatic fallback.
    
    Default order: Ollama -> Groq
    If prefer_groq=True: Groq -> Ollama
    
    Returns:
        Response text or None if all failed
    """
    if prefer_groq:
        # Try Groq first
        result = call_groq(prompt, model=model_groq, max_tokens=max_tokens)
        if result:
            return result
        
        # Fallback to Ollama
        logger.info("[LLM] Groq failed, trying Ollama...")
        return call_ollama(prompt, model=model_ollama, max_tokens=max_tokens)
    else:
        # Try Ollama first
        result = call_ollama(prompt, model=model_ollama, max_tokens=max_tokens)
        if result:
            return result
        
        # Fallback to Groq
        logger.info("[LLM] Ollama failed, trying Groq...")
        return call_groq(prompt, model=model_groq, max_tokens=max_tokens)
