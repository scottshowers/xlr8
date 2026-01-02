"""
Reversible PII Redactor
=======================

PII NEVER goes to external LLMs. We redact before sending, restore after.

Supported PII types:
- SSN (Social Security Numbers)
- Bank account/routing numbers
- Salary/compensation values
- Phone numbers
- Email addresses
- Dates of birth

Usage:
    redactor = ReversibleRedactor()
    safe_text = redactor.redact(sensitive_text)
    # ... send to LLM ...
    restored_text = redactor.restore(llm_response)
"""

import re
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class ReversibleRedactor:
    """
    Reversible PII redaction - PII NEVER goes to Claude.
    
    We redact before sending to any external LLM, then restore after.
    This allows us to work with sensitive data without compromising privacy.
    """
    
    def __init__(self):
        self.mappings: Dict[str, str] = {}  # {placeholder: original_value}
        self.counters = {
            'ssn': 0, 
            'salary': 0, 
            'phone': 0, 
            'email': 0, 
            'name': 0, 
            'account': 0,
            'dob': 0
        }
    
    def _get_placeholder(self, pii_type: str) -> str:
        """Generate unique placeholder for PII type."""
        self.counters[pii_type] += 1
        return f"[{pii_type.upper()}_{self.counters[pii_type]:03d}]"
    
    def redact(self, text: str) -> str:
        """
        Redact PII with reversible placeholders.
        
        Args:
            text: Text potentially containing PII
            
        Returns:
            Text with PII replaced by placeholders
        """
        if not text:
            return text
        
        result = text
        
        # SSN: 123-45-6789
        for match in re.finditer(r'\b(\d{3}-\d{2}-\d{4})\b', result):
            original = match.group(1)
            if original not in self.mappings.values():
                placeholder = self._get_placeholder('ssn')
                self.mappings[placeholder] = original
                result = result.replace(original, placeholder)
        
        # Bank account / routing numbers (8-17 digits)
        for match in re.finditer(r'\b(\d{8,17})\b', result):
            original = match.group(1)
            # Skip if already mapped or looks like a year/date
            if original not in self.mappings.values() and not original.startswith('20'):
                placeholder = self._get_placeholder('account')
                self.mappings[placeholder] = original
                result = result.replace(original, placeholder)
        
        # Salary: $75,000 or $75,000.00
        for match in re.finditer(r'(\$\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', result):
            original = match.group(1)
            if original not in self.mappings.values():
                placeholder = self._get_placeholder('salary')
                self.mappings[placeholder] = original
                result = result.replace(original, placeholder)
        
        # Phone: (123) 456-7890 or 123-456-7890
        for match in re.finditer(r'(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})\b', result):
            original = match.group(1)
            # Skip if it looks like SSN
            if original.count('-') == 2 and len(original.replace('-', '')) == 9:
                continue
            if original not in self.mappings.values():
                placeholder = self._get_placeholder('phone')
                self.mappings[placeholder] = original
                result = result.replace(original, placeholder)
        
        # Email
        for match in re.finditer(r'\b([\w\.-]+@[\w\.-]+\.\w{2,})\b', result):
            original = match.group(1)
            if original not in self.mappings.values():
                placeholder = self._get_placeholder('email')
                self.mappings[placeholder] = original
                result = result.replace(original, placeholder)
        
        # Date of birth patterns: MM/DD/YYYY, YYYY-MM-DD
        for match in re.finditer(r'\b(\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2})\b', result):
            original = match.group(1)
            if original not in self.mappings.values():
                placeholder = self._get_placeholder('dob')
                self.mappings[placeholder] = original
                result = result.replace(original, placeholder)
        
        return result
    
    def restore(self, text: str) -> str:
        """
        Restore original PII values from placeholders.
        
        Args:
            text: Text with placeholders
            
        Returns:
            Text with original PII restored
        """
        if not text or not self.mappings:
            return text
        
        result = text
        for placeholder, original in self.mappings.items():
            result = result.replace(placeholder, original)
        
        return result
    
    def has_pii(self) -> bool:
        """Check if any PII was redacted."""
        return len(self.mappings) > 0
    
    def get_stats(self) -> Dict[str, int]:
        """Get redaction statistics."""
        return {
            'total_redacted': len(self.mappings),
            **{k: v for k, v in self.counters.items() if v > 0}
        }
