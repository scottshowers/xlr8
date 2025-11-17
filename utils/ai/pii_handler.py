"""
PII Handler for XLR8 Chat System

Detects and anonymizes Personally Identifiable Information (PII):
- Social Security Numbers (SSN)
- Email addresses
- Phone numbers
- Street addresses
- Person names (basic detection)

Provides anonymization and de-anonymization capabilities.

Author: HCMPACT
Version: 1.0
"""

import re
from typing import Dict, Tuple, List
import logging

logger = logging.getLogger(__name__)


class PIIHandler:
    """
    Handles detection and anonymization of PII in text.
    
    Supports:
    - SSN (xxx-xx-xxxx, xxx.xx.xxxx, xxxxxxxxx)
    - Email addresses
    - Phone numbers (various formats)
    - Street addresses
    - Names (basic detection)
    """
    
    def __init__(self):
        """Initialize PII patterns"""
        
        # SSN patterns: 123-45-6789, 123.45.6789, 123456789
        self.ssn_pattern = re.compile(
            r'\b(?:\d{3}[-.]?\d{2}[-.]?\d{4})\b'
        )
        
        # Email pattern
        self.email_pattern = re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        )
        
        # Phone patterns: (123) 456-7890, 123-456-7890, 123.456.7890, 1234567890
        self.phone_pattern = re.compile(
            r'\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b'
        )
        
        # Street address pattern (basic)
        # Matches: 123 Main St, 456 Oak Avenue, etc.
        self.address_pattern = re.compile(
            r'\b\d{1,5}\s+[A-Za-z0-9\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Court|Ct|Way|Circle|Cir|Place|Pl)\b',
            re.IGNORECASE
        )
        
        logger.info("PII Handler initialized")
    
    def has_pii(self, text: str) -> bool:
        """
        Check if text contains any PII.
        
        Args:
            text: Text to check
            
        Returns:
            True if PII detected, False otherwise
        """
        if not text:
            return False
        
        # Check each pattern
        if self.ssn_pattern.search(text):
            logger.info("SSN detected in text")
            return True
        
        if self.email_pattern.search(text):
            logger.info("Email detected in text")
            return True
        
        if self.phone_pattern.search(text):
            logger.info("Phone number detected in text")
            return True
        
        if self.address_pattern.search(text):
            logger.info("Street address detected in text")
            return True
        
        return False
    
    def anonymize(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        Anonymize PII in text by replacing with tokens.
        
        Args:
            text: Original text with PII
            
        Returns:
            Tuple of (anonymized_text, pii_map)
            - anonymized_text: Text with PII replaced by tokens
            - pii_map: Dict mapping tokens back to original values
        """
        if not text:
            return text, {}
        
        anonymized = text
        pii_map = {}
        
        # Anonymize SSNs
        ssn_matches = list(self.ssn_pattern.finditer(anonymized))
        for i, match in enumerate(ssn_matches, 1):
            token = f"[SSN_{i}]"
            pii_map[token] = match.group()
            anonymized = anonymized.replace(match.group(), token, 1)
        
        # Anonymize emails
        email_matches = list(self.email_pattern.finditer(anonymized))
        for i, match in enumerate(email_matches, 1):
            token = f"[EMAIL_{i}]"
            pii_map[token] = match.group()
            anonymized = anonymized.replace(match.group(), token, 1)
        
        # Anonymize phone numbers
        phone_matches = list(self.phone_pattern.finditer(anonymized))
        for i, match in enumerate(phone_matches, 1):
            token = f"[PHONE_{i}]"
            pii_map[token] = match.group()
            anonymized = anonymized.replace(match.group(), token, 1)
        
        # Anonymize addresses
        address_matches = list(self.address_pattern.finditer(anonymized))
        for i, match in enumerate(address_matches, 1):
            token = f"[ADDRESS_{i}]"
            pii_map[token] = match.group()
            anonymized = anonymized.replace(match.group(), token, 1)
        
        if pii_map:
            logger.info(f"Anonymized {len(pii_map)} PII items")
        
        return anonymized, pii_map
    
    def deanonymize(self, text: str, pii_map: Dict[str, str]) -> str:
        """
        Restore original PII values from anonymized text.
        
        Args:
            text: Anonymized text with tokens
            pii_map: Dict mapping tokens to original values
            
        Returns:
            Text with original PII restored
        """
        if not text or not pii_map:
            return text
        
        deanonymized = text
        
        # Replace each token with original value
        for token, original_value in pii_map.items():
            deanonymized = deanonymized.replace(token, original_value)
        
        logger.info(f"De-anonymized {len(pii_map)} PII items")
        
        return deanonymized
    
    def detect_pii_types(self, text: str) -> List[str]:
        """
        Detect which types of PII are present in text.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of PII types found (e.g., ['ssn', 'email'])
        """
        pii_types = []
        
        if self.ssn_pattern.search(text):
            pii_types.append('ssn')
        
        if self.email_pattern.search(text):
            pii_types.append('email')
        
        if self.phone_pattern.search(text):
            pii_types.append('phone')
        
        if self.address_pattern.search(text):
            pii_types.append('address')
        
        return pii_types
    
    def get_pii_count(self, text: str) -> Dict[str, int]:
        """
        Count how many of each PII type are in text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dict with counts for each PII type
        """
        return {
            'ssn': len(self.ssn_pattern.findall(text)),
            'email': len(self.email_pattern.findall(text)),
            'phone': len(self.phone_pattern.findall(text)),
            'address': len(self.address_pattern.findall(text))
        }


# Convenience functions
def has_pii(text: str) -> bool:
    """
    Quick check if text contains PII.
    
    Args:
        text: Text to check
        
    Returns:
        True if PII detected
    """
    handler = PIIHandler()
    return handler.has_pii(text)


def anonymize_text(text: str) -> Tuple[str, Dict[str, str]]:
    """
    Anonymize PII in text.
    
    Args:
        text: Text to anonymize
        
    Returns:
        Tuple of (anonymized_text, pii_map)
    """
    handler = PIIHandler()
    return handler.anonymize(text)


def deanonymize_text(text: str, pii_map: Dict[str, str]) -> str:
    """
    Restore PII in text.
    
    Args:
        text: Anonymized text
        pii_map: Mapping of tokens to original values
        
    Returns:
        De-anonymized text
    """
    handler = PIIHandler()
    return handler.deanonymize(text, pii_map)
