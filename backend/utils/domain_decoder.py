"""
DOMAIN DECODER - Consultant Knowledge That Makes XLR8 Smarter
============================================================

This is the "tribal knowledge" layer - the stuff consultants learn after
10 years of implementations that makes them worth $500/hr.

Examples:
- "TXC in an earning code means Taxable Company Car"
- "Configuration Validation = what's configured, Employee Conversion Testing = what's in use"
- "Codes 50-59 typically indicate Payroll Tax module is active"
- "An effective date in the future means staged, not active"

This knowledge is:
1. Added by consultants through the UI
2. Stored in Supabase (persistent across sessions)
3. Queried by the Intelligence Engine to enrich analysis
4. Searchable by pattern, domain, or category

NOT HARDCODED. NOT IN CODE. CONSULTANT-EDITABLE.

Table: domain_decoder
- pattern: What to look for (regex or keyword)
- meaning: What it means in plain English
- domain: earnings, deductions, taxes, benefits, hr, general
- category: code_interpretation, file_relationship, business_rule, signal_pattern
- example: A concrete example showing the pattern
- confidence: How confident we are (1.0 = always true, 0.7 = usually true)
- added_by: Who added it (consultant email)
- source: Where this knowledge came from

Author: XLR8 Team
Version: 1.0.0 - Tribal Knowledge Made Queryable
"""

import re
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import Supabase
try:
    from utils.database.supabase_client import get_supabase
    SUPABASE_AVAILABLE = True
except ImportError:
    try:
        from backend.utils.database.supabase_client import get_supabase
        SUPABASE_AVAILABLE = True
    except ImportError:
        SUPABASE_AVAILABLE = False
        logger.warning("[DECODER] Supabase not available")


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class DecoderEntry:
    """A piece of domain knowledge."""
    id: str
    pattern: str
    meaning: str
    domain: str
    category: str
    example: Optional[str] = None
    confidence: float = 1.0
    added_by: Optional[str] = None
    source: Optional[str] = None
    is_active: bool = True
    created_at: Optional[str] = None
    
    def matches(self, text: str) -> bool:
        """Check if this entry's pattern matches the given text."""
        if not text:
            return False
        
        text_lower = text.lower()
        pattern_lower = self.pattern.lower()
        
        # Try exact substring match first
        if pattern_lower in text_lower:
            return True
        
        # Try regex if pattern looks like one
        if any(c in self.pattern for c in ['*', '+', '?', '[', ']', '^', '$', '|']):
            try:
                if re.search(self.pattern, text, re.IGNORECASE):
                    return True
            except re.error:
                pass
        
        return False
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'pattern': self.pattern,
            'meaning': self.meaning,
            'domain': self.domain,
            'category': self.category,
            'example': self.example,
            'confidence': self.confidence,
            'added_by': self.added_by,
            'source': self.source,
            'is_active': self.is_active,
            'created_at': self.created_at
        }


# =============================================================================
# CATEGORIES AND DOMAINS
# =============================================================================

DECODER_CATEGORIES = {
    'code_interpretation': 'What codes/abbreviations mean (TXC = Taxable Company Car)',
    'file_relationship': 'How files relate to each other (Config Validation vs Employee Conversion)',
    'business_rule': 'Domain-specific rules (effective date in future = staged)',
    'signal_pattern': 'Patterns that indicate something (codes 50-59 = Payroll Tax module)',
    'vendor_specific': 'Vendor-specific knowledge (UKG, ADP, etc.)',
    'compliance_flag': 'Things that indicate compliance issues',
}

DECODER_DOMAINS = {
    'earnings': 'Earning codes, pay rates, compensation',
    'deductions': 'Deduction codes, benefits, 401k',
    'taxes': 'Tax codes, SUI/SUTA/FUTA, withholding',
    'benefits': 'Benefit plans, enrollments, coverage',
    'hr': 'Employee data, demographics, org structure',
    'time': 'Time and attendance, schedules',
    'gl': 'General ledger, account mappings',
    'general': 'Cross-domain or general knowledge',
}


# =============================================================================
# DOMAIN DECODER SERVICE
# =============================================================================

class DomainDecoder:
    """
    Service for managing and querying domain knowledge.
    
    Usage:
        decoder = DomainDecoder()
        
        # Add knowledge
        decoder.add(
            pattern="TXC",
            meaning="Taxable Company Car - a fringe benefit earning code",
            domain="earnings",
            category="code_interpretation",
            example="Earning code TXC-01 = Company car taxable benefit"
        )
        
        # Query knowledge
        matches = decoder.decode("What does TXC mean?")
        # Returns: [DecoderEntry(pattern='TXC', meaning='Taxable Company Car...')]
        
        # Get all for a domain
        earnings_knowledge = decoder.get_by_domain('earnings')
    """
    
    TABLE_NAME = 'domain_decoder'
    
    def __init__(self):
        self._cache: List[DecoderEntry] = []
        self._cache_loaded = False
    
    def _get_client(self):
        """Get Supabase client."""
        if not SUPABASE_AVAILABLE:
            return None
        try:
            return get_supabase()
        except Exception as e:
            logger.warning(f"[DECODER] Could not get Supabase client: {e}")
            return None
    
    def _ensure_table_exists(self) -> bool:
        """Ensure the domain_decoder table exists in Supabase."""
        client = self._get_client()
        if not client:
            return False
        
        # Table creation is handled by Supabase migrations
        # This method just verifies the table is accessible
        try:
            client.table(self.TABLE_NAME).select('id').limit(1).execute()
            return True
        except Exception as e:
            logger.warning(f"[DECODER] Table check failed: {e}")
            return False
    
    def _load_cache(self) -> None:
        """Load all active entries into cache."""
        if self._cache_loaded:
            return
        
        client = self._get_client()
        if not client:
            self._cache_loaded = True
            return
        
        try:
            result = client.table(self.TABLE_NAME).select('*').eq('is_active', True).execute()
            
            self._cache = []
            for row in (result.data or []):
                self._cache.append(DecoderEntry(
                    id=row.get('id', ''),
                    pattern=row.get('pattern', ''),
                    meaning=row.get('meaning', ''),
                    domain=row.get('domain', 'general'),
                    category=row.get('category', 'general'),
                    example=row.get('example'),
                    confidence=row.get('confidence', 1.0),
                    added_by=row.get('added_by'),
                    source=row.get('source'),
                    is_active=row.get('is_active', True),
                    created_at=row.get('created_at')
                ))
            
            self._cache_loaded = True
            logger.info(f"[DECODER] Loaded {len(self._cache)} knowledge entries")
            
        except Exception as e:
            logger.warning(f"[DECODER] Cache load failed: {e}")
            self._cache_loaded = True
    
    def refresh_cache(self) -> None:
        """Force reload of cache."""
        self._cache_loaded = False
        self._load_cache()
    
    # =========================================================================
    # QUERY METHODS
    # =========================================================================
    
    def decode(self, text: str, domain: str = None) -> List[DecoderEntry]:
        """
        Find all knowledge entries that match the given text.
        
        Args:
            text: Text to decode (question, column name, code, etc.)
            domain: Optional domain filter
            
        Returns:
            List of matching DecoderEntry objects, sorted by confidence
        """
        self._load_cache()
        
        matches = []
        for entry in self._cache:
            if domain and entry.domain != domain:
                continue
            if entry.matches(text):
                matches.append(entry)
        
        # Sort by confidence (highest first)
        matches.sort(key=lambda e: e.confidence, reverse=True)
        
        return matches
    
    def get_by_domain(self, domain: str) -> List[DecoderEntry]:
        """Get all knowledge entries for a domain."""
        self._load_cache()
        return [e for e in self._cache if e.domain == domain]
    
    def get_by_category(self, category: str) -> List[DecoderEntry]:
        """Get all knowledge entries for a category."""
        self._load_cache()
        return [e for e in self._cache if e.category == category]
    
    def get_all(self) -> List[DecoderEntry]:
        """Get all active knowledge entries."""
        self._load_cache()
        return self._cache.copy()
    
    def search(self, query: str) -> List[DecoderEntry]:
        """
        Search knowledge entries by pattern, meaning, or example.
        """
        self._load_cache()
        
        query_lower = query.lower()
        matches = []
        
        for entry in self._cache:
            if (query_lower in entry.pattern.lower() or
                query_lower in entry.meaning.lower() or
                (entry.example and query_lower in entry.example.lower())):
                matches.append(entry)
        
        return matches
    
    # =========================================================================
    # WRITE METHODS
    # =========================================================================
    
    def add(
        self,
        pattern: str,
        meaning: str,
        domain: str = 'general',
        category: str = 'general',
        example: str = None,
        confidence: float = 1.0,
        added_by: str = None,
        source: str = None
    ) -> Optional[DecoderEntry]:
        """
        Add a new knowledge entry.
        
        Returns the created entry, or None if failed.
        """
        client = self._get_client()
        if not client:
            logger.warning("[DECODER] Cannot add entry - no database connection")
            return None
        
        try:
            import uuid
            entry_id = str(uuid.uuid4())
            
            data = {
                'id': entry_id,
                'pattern': pattern,
                'meaning': meaning,
                'domain': domain,
                'category': category,
                'example': example,
                'confidence': confidence,
                'added_by': added_by,
                'source': source,
                'is_active': True
            }
            
            result = client.table(self.TABLE_NAME).insert(data).execute()
            
            if result.data:
                # Invalidate cache
                self._cache_loaded = False
                
                entry = DecoderEntry(**data)
                logger.info(f"[DECODER] Added: {pattern} → {meaning[:50]}...")
                return entry
            
        except Exception as e:
            logger.error(f"[DECODER] Add failed: {e}")
        
        return None
    
    def update(self, entry_id: str, updates: Dict) -> bool:
        """Update an existing entry."""
        client = self._get_client()
        if not client:
            return False
        
        try:
            # Only allow updating certain fields
            allowed = {'pattern', 'meaning', 'domain', 'category', 
                       'example', 'confidence', 'is_active'}
            safe_updates = {k: v for k, v in updates.items() if k in allowed}
            
            if safe_updates:
                client.table(self.TABLE_NAME).update(safe_updates).eq('id', entry_id).execute()
                self._cache_loaded = False
                return True
                
        except Exception as e:
            logger.error(f"[DECODER] Update failed: {e}")
        
        return False
    
    def delete(self, entry_id: str) -> bool:
        """Soft-delete an entry (set is_active = False)."""
        return self.update(entry_id, {'is_active': False})
    
    def hard_delete(self, entry_id: str) -> bool:
        """Permanently delete an entry."""
        client = self._get_client()
        if not client:
            return False
        
        try:
            client.table(self.TABLE_NAME).delete().eq('id', entry_id).execute()
            self._cache_loaded = False
            return True
        except Exception as e:
            logger.error(f"[DECODER] Hard delete failed: {e}")
        
        return False


# =============================================================================
# MODULE-LEVEL CONVENIENCE
# =============================================================================

_decoder_instance: Optional[DomainDecoder] = None

def get_decoder() -> DomainDecoder:
    """Get or create the global DomainDecoder instance."""
    global _decoder_instance
    if _decoder_instance is None:
        _decoder_instance = DomainDecoder()
    return _decoder_instance


def decode(text: str, domain: str = None) -> List[DecoderEntry]:
    """Convenience function to decode text."""
    return get_decoder().decode(text, domain)


def add_knowledge(
    pattern: str,
    meaning: str,
    domain: str = 'general',
    category: str = 'general',
    **kwargs
) -> Optional[DecoderEntry]:
    """Convenience function to add knowledge."""
    return get_decoder().add(pattern, meaning, domain, category, **kwargs)


# =============================================================================
# SEED DATA - Initial Knowledge
# =============================================================================

SEED_KNOWLEDGE = [
    # File Relationships (the UKG-specific insight you mentioned)
    {
        'pattern': 'Configuration Validation',
        'meaning': 'Shows what is CONFIGURED in the system - earning codes, deduction plans, tax setup. This is the "should be" view.',
        'domain': 'general',
        'category': 'file_relationship',
        'example': 'Configuration Validation Report shows 47 earning codes are configured in the system',
        'source': 'UKG Pro implementation knowledge'
    },
    {
        'pattern': 'Employee Conversion Testing',
        'meaning': 'Shows what is actually IN USE by employees - actual earnings, deductions, pay data. This is the "is" view. Compare to Configuration Validation to find gaps.',
        'domain': 'general',
        'category': 'file_relationship',
        'example': 'Employee Conversion Testing shows only 31 earning codes are actually being used',
        'source': 'UKG Pro implementation knowledge'
    },
    
    # Code Interpretations
    {
        'pattern': 'TXC',
        'meaning': 'Taxable Company Car - a fringe benefit where the personal use of a company vehicle is reported as taxable income',
        'domain': 'earnings',
        'category': 'code_interpretation',
        'example': 'Earning code TXC-01 = Company car taxable benefit',
        'source': 'Common payroll terminology'
    },
    {
        'pattern': 'GTL',
        'meaning': 'Group Term Life - employer-provided life insurance. Amounts over $50,000 are taxable as imputed income.',
        'domain': 'benefits',
        'category': 'code_interpretation',
        'example': 'GTL imputed income appears when coverage exceeds $50,000',
        'source': 'IRS regulations'
    },
    
    # Business Rules
    {
        'pattern': 'effective date in future',
        'meaning': 'A record with an effective date in the future is STAGED - it exists but is not yet active. Will become active on that date.',
        'domain': 'general',
        'category': 'business_rule',
        'example': 'Pay rate change effective 2025-01-01 means the new rate activates on that date',
        'source': 'Standard HCM practice'
    },
    {
        'pattern': 'status A T L',
        'meaning': 'Common employment status codes: A=Active, T=Terminated, L=Leave of Absence',
        'domain': 'hr',
        'category': 'code_interpretation',
        'example': 'emp_status = A means the employee is currently active',
        'source': 'Common HR terminology'
    },
    
    # Signal Patterns
    {
        'pattern': 'codes 50-59',
        'meaning': 'In UKG Pro, earning codes in the 50-59 range often indicate the Payroll Tax module is configured',
        'domain': 'taxes',
        'category': 'signal_pattern',
        'example': 'Seeing earning code 51 suggests Payroll Tax module is active',
        'confidence': 0.7,
        'source': 'UKG Pro implementation patterns'
    },
]


def seed_initial_knowledge() -> int:
    """
    Seed the database with initial knowledge entries.
    Returns count of entries added.
    """
    decoder = get_decoder()
    added = 0
    
    for entry in SEED_KNOWLEDGE:
        result = decoder.add(**entry)
        if result:
            added += 1
    
    logger.info(f"[DECODER] Seeded {added} initial knowledge entries")
    return added
