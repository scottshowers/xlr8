"""
XLR8 Entity Detector - Hub Reference Tagging for ChromaDB
==========================================================

Scans text content and identifies references to known hub types.
Used during document ingestion to tag chunks with entity metadata.

This enables:
1. "Show me everything about job_code" → finds all chunks mentioning job codes
2. Cross-reference: DuckDB hub ↔ ChromaDB documentation
3. Gap detection: "Hub exists but no documentation found"

Deploy to: backend/utils/entity_detector.py

Usage:
    detector = EntityDetector()
    detector.load_hub_vocabulary()  # Load from vendor schema
    
    # During chunk ingestion:
    hub_refs = detector.detect_entities(chunk_text)
    # Returns: {'hub_references': ['job_code', 'earnings_code'], 'hub_context': {...}}
"""

import re
import json
import logging
import os
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class HubPattern:
    """Pattern for detecting a hub type in text."""
    hub_type: str           # e.g., "job_code"
    semantic_type: str      # e.g., "job_code" 
    display_name: str       # e.g., "Job Code"
    patterns: List[str]     # Regex patterns to match
    keywords: List[str]     # Simple keyword matches
    context_hints: List[str] # Words that suggest this hub in context


# =============================================================================
# CORE HUB PATTERNS (UKG Pro focused, extensible)
# =============================================================================

CORE_HUB_PATTERNS = [
    HubPattern(
        hub_type="company_code",
        semantic_type="company_code",
        display_name="Company Code",
        patterns=[r'\bcompany\s*code', r'\bcocode\b', r'\bco\s*code', r'\bcomponent\s*company'],
        keywords=['company code', 'cocode', 'component company', 'legal entity'],
        context_hints=['company', 'organization', 'entity', 'employer']
    ),
    HubPattern(
        hub_type="job_code",
        semantic_type="job_code",
        display_name="Job Code",
        patterns=[r'\bjob\s*code', r'\bjob\s*title\s*code', r'\bposition\s*code'],
        keywords=['job code', 'job codes', 'position code', 'job title'],
        context_hints=['job', 'position', 'role', 'title', 'occupation']
    ),
    HubPattern(
        hub_type="location_code",
        semantic_type="location_code",
        display_name="Location Code",
        patterns=[r'\blocation\s*code', r'\bloc\s*code', r'\bwork\s*location'],
        keywords=['location code', 'work location', 'site code'],
        context_hints=['location', 'site', 'workplace', 'office', 'branch']
    ),
    HubPattern(
        hub_type="earnings_code",
        semantic_type="earnings_code",
        display_name="Earnings Code",
        patterns=[r'\bearning[s]?\s*code', r'\bearn\s*code', r'\bpay\s*code'],
        keywords=['earnings code', 'earning code', 'pay code', 'earnings codes'],
        context_hints=['earnings', 'pay', 'wages', 'compensation', 'salary', 'overtime', 'bonus']
    ),
    HubPattern(
        hub_type="deduction_code",
        semantic_type="deduction_code",
        display_name="Deduction Code",
        patterns=[r'\bdeduction\s*code', r'\bded\s*code', r'\bbenefit\s*code'],
        keywords=['deduction code', 'deduction codes', 'benefit code', 'benefit plan'],
        context_hints=['deduction', 'benefit', '401k', 'insurance', 'garnishment', 'withholding']
    ),
    HubPattern(
        hub_type="tax_code",
        semantic_type="tax_code",
        display_name="Tax Code",
        patterns=[r'\btax\s*code', r'\btax\s*jurisdiction', r'\btax\s*type'],
        keywords=['tax code', 'tax codes', 'tax jurisdiction', 'withholding tax'],
        context_hints=['tax', 'withholding', 'federal', 'state', 'local', 'fica', 'medicare']
    ),
    HubPattern(
        hub_type="pay_group_code",
        semantic_type="pay_group_code",
        display_name="Pay Group Code",
        patterns=[r'\bpay\s*group', r'\bpayroll\s*group', r'\bpay\s*frequency'],
        keywords=['pay group', 'pay groups', 'payroll group', 'pay frequency'],
        context_hints=['payroll', 'pay period', 'frequency', 'weekly', 'biweekly', 'monthly']
    ),
    HubPattern(
        hub_type="department_code",
        semantic_type="department_code",
        display_name="Department Code",
        patterns=[r'\bdepartment\s*code', r'\bdept\s*code', r'\borg\s*level'],
        keywords=['department code', 'dept code', 'org level', 'organization level'],
        context_hints=['department', 'division', 'org level', 'cost center']
    ),
    HubPattern(
        hub_type="employee_type_code",
        semantic_type="employee_type_code",
        display_name="Employee Type Code",
        patterns=[r'\bemployee\s*type', r'\bemp\s*type', r'\bworker\s*type'],
        keywords=['employee type', 'emp type', 'worker type', 'employment type'],
        context_hints=['full-time', 'part-time', 'contractor', 'temporary', 'exempt', 'non-exempt']
    ),
    HubPattern(
        hub_type="termination_reason_code",
        semantic_type="termination_reason_code",
        display_name="Termination Reason Code",
        patterns=[r'\btermination\s*reason', r'\bterm\s*reason', r'\bseparation\s*reason'],
        keywords=['termination reason', 'term reason', 'separation reason'],
        context_hints=['termination', 'separation', 'resignation', 'layoff', 'discharge']
    ),
    HubPattern(
        hub_type="workers_comp_code",
        semantic_type="workers_comp_code",
        display_name="Workers Comp Code",
        patterns=[r'\bworkers?\s*comp', r'\bwc\s*code', r'\bwork\s*comp'],
        keywords=['workers comp', 'workers compensation', 'wc code', 'work comp'],
        context_hints=['workers compensation', 'injury', 'claim', 'insurance', 'premium']
    ),
    HubPattern(
        hub_type="gl_account_code",
        semantic_type="gl_account_code",
        display_name="GL Account Code",
        patterns=[r'\bgl\s*account', r'\bgeneral\s*ledger', r'\baccount\s*code'],
        keywords=['gl account', 'general ledger', 'account code', 'chart of accounts'],
        context_hints=['ledger', 'accounting', 'journal', 'posting', 'debit', 'credit']
    ),
    HubPattern(
        hub_type="bank_code",
        semantic_type="bank_code",
        display_name="Bank Code",
        patterns=[r'\bbank\s*code', r'\bbank\s*id', r'\brouting\s*number'],
        keywords=['bank code', 'bank id', 'routing number', 'aba number'],
        context_hints=['bank', 'direct deposit', 'ach', 'routing', 'account']
    ),
    HubPattern(
        hub_type="pto_plan_code",
        semantic_type="pto_plan_code",
        display_name="PTO Plan Code",
        patterns=[r'\bpto\s*plan', r'\btime\s*off\s*plan', r'\baccrual\s*plan'],
        keywords=['pto plan', 'time off plan', 'accrual plan', 'leave plan'],
        context_hints=['pto', 'vacation', 'sick', 'leave', 'accrual', 'time off']
    ),
    HubPattern(
        hub_type="shift_code",
        semantic_type="shift_code",
        display_name="Shift Code",
        patterns=[r'\bshift\s*code', r'\bwork\s*shift', r'\bschedule\s*code'],
        keywords=['shift code', 'work shift', 'shift differential'],
        context_hints=['shift', 'schedule', 'night', 'weekend', 'differential']
    ),
]


class EntityDetector:
    """
    Detects hub entity references in text content.
    
    Designed to run during ChromaDB ingestion to tag chunks with
    metadata about which hubs they reference.
    """
    
    def __init__(self):
        self.hub_patterns: List[HubPattern] = []
        self.vendor_vocabulary: Dict[str, Dict] = {}
        self._compiled_patterns: Dict[str, List[re.Pattern]] = {}
        
        # Load core patterns
        self._load_core_patterns()
    
    def _load_core_patterns(self):
        """Load the core hub patterns."""
        self.hub_patterns = CORE_HUB_PATTERNS.copy()
        self._compile_patterns()
        logger.info(f"[ENTITY-DETECT] Loaded {len(self.hub_patterns)} core hub patterns")
    
    def _compile_patterns(self):
        """Pre-compile regex patterns for performance."""
        self._compiled_patterns = {}
        for hp in self.hub_patterns:
            self._compiled_patterns[hp.hub_type] = [
                re.compile(p, re.IGNORECASE) for p in hp.patterns
            ]
    
    def load_vendor_vocabulary(self, vendor: str = "ukg_pro") -> int:
        """
        Load additional patterns from vendor vocabulary files.
        
        Args:
            vendor: Vendor identifier (e.g., "ukg_pro")
            
        Returns:
            Number of patterns loaded
        """
        loaded = 0
        
        # Try multiple paths
        paths = [
            f"/app/config/ukg_vocabulary_seed.json",
            f"config/ukg_vocabulary_seed.json",
            os.path.join(os.path.dirname(__file__), '..', 'config', 'ukg_vocabulary_seed.json'),
        ]
        
        for path in paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        vocab = json.load(f)
                    
                    for entry in vocab:
                        hub_type = entry.get('hub_type', '')
                        semantic_type = entry.get('semantic_type', '')
                        display_name = entry.get('display_name', '')
                        
                        if hub_type and semantic_type:
                            self.vendor_vocabulary[hub_type] = {
                                'semantic_type': semantic_type,
                                'display_name': display_name,
                                'variations': entry.get('variations', []),
                                'column_patterns': entry.get('column_patterns', [])
                            }
                            loaded += 1
                    
                    logger.info(f"[ENTITY-DETECT] Loaded {loaded} vendor vocabulary entries from {path}")
                    break
                    
                except Exception as e:
                    logger.warning(f"[ENTITY-DETECT] Failed to load {path}: {e}")
        
        return loaded
    
    def detect_entities(self, text: str, min_confidence: float = 0.3) -> Dict:
        """
        Detect hub entity references in text.
        
        Args:
            text: Text content to analyze
            min_confidence: Minimum confidence threshold (0.0-1.0)
            
        Returns:
            Dict with:
                - hub_references: List of detected hub types
                - hub_details: Dict with confidence and context for each hub
                - primary_hub: Most prominent hub reference (if any)
        """
        if not text or len(text) < 10:
            return {'hub_references': [], 'hub_details': {}, 'primary_hub': None}
        
        text_lower = text.lower()
        detections: Dict[str, Dict] = {}
        
        # Check each hub pattern
        for hp in self.hub_patterns:
            confidence, matches = self._check_hub_pattern(text_lower, hp)
            
            if confidence >= min_confidence:
                detections[hp.hub_type] = {
                    'semantic_type': hp.semantic_type,
                    'display_name': hp.display_name,
                    'confidence': confidence,
                    'match_count': len(matches),
                    'matches': matches[:5]  # Keep top 5 matches
                }
        
        # Also check vendor vocabulary for additional matches
        for hub_type, vocab_entry in self.vendor_vocabulary.items():
            if hub_type not in detections:
                # Check variations
                for variation in vocab_entry.get('variations', []):
                    if variation.lower() in text_lower:
                        detections[hub_type] = {
                            'semantic_type': vocab_entry['semantic_type'],
                            'display_name': vocab_entry.get('display_name', hub_type),
                            'confidence': 0.5,  # Medium confidence for variation match
                            'match_count': 1,
                            'matches': [variation]
                        }
                        break
        
        # Sort by confidence and determine primary hub
        sorted_hubs = sorted(
            detections.items(),
            key=lambda x: (x[1]['confidence'], x[1]['match_count']),
            reverse=True
        )
        
        hub_references = [h[0] for h in sorted_hubs]
        primary_hub = hub_references[0] if hub_references else None
        
        return {
            'hub_references': hub_references,
            'hub_details': detections,
            'primary_hub': primary_hub
        }
    
    def _check_hub_pattern(self, text: str, hp: HubPattern) -> Tuple[float, List[str]]:
        """
        Check text against a hub pattern.
        
        Returns (confidence, list of matches)
        """
        matches = []
        score = 0.0
        
        # Check regex patterns (highest weight)
        for pattern in self._compiled_patterns.get(hp.hub_type, []):
            found = pattern.findall(text)
            if found:
                matches.extend(found)
                score += 0.4 * len(found)
        
        # Check keywords (medium weight)
        for keyword in hp.keywords:
            if keyword.lower() in text:
                matches.append(keyword)
                score += 0.3
        
        # Check context hints (lower weight, cumulative)
        context_matches = sum(1 for hint in hp.context_hints if hint.lower() in text)
        if context_matches >= 2:
            score += 0.1 * min(context_matches, 5)
        
        # Normalize to 0-1 range
        confidence = min(1.0, score)
        
        return confidence, list(set(matches))
    
    def enrich_chunk_metadata(self, chunk_text: str, existing_metadata: Dict = None) -> Dict:
        """
        Enrich chunk metadata with entity detection results.
        
        This is the main method to call during ChromaDB ingestion.
        
        Args:
            chunk_text: The text content of the chunk
            existing_metadata: Existing metadata dict to extend
            
        Returns:
            Updated metadata dict with hub_references added
        """
        metadata = existing_metadata.copy() if existing_metadata else {}
        
        # Detect entities
        detection = self.detect_entities(chunk_text)
        
        # Add to metadata
        if detection['hub_references']:
            metadata['hub_references'] = detection['hub_references']
            metadata['primary_hub'] = detection['primary_hub']
            
            # Store confidence for primary hub
            if detection['primary_hub'] and detection['primary_hub'] in detection['hub_details']:
                metadata['hub_confidence'] = detection['hub_details'][detection['primary_hub']]['confidence']
        
        return metadata
    
    def get_hub_summary(self, chunks: List[Dict]) -> Dict:
        """
        Summarize hub references across multiple chunks.
        
        Useful for document-level analysis.
        
        Args:
            chunks: List of chunk dicts with 'text' field
            
        Returns:
            Summary dict with hub counts and coverage
        """
        hub_counts: Dict[str, int] = {}
        total_chunks = len(chunks)
        
        for chunk in chunks:
            text = chunk.get('text', '') or chunk.get('content', '')
            detection = self.detect_entities(text)
            
            for hub in detection['hub_references']:
                hub_counts[hub] = hub_counts.get(hub, 0) + 1
        
        # Calculate coverage
        hub_coverage = {
            hub: count / total_chunks 
            for hub, count in hub_counts.items()
        }
        
        return {
            'total_chunks': total_chunks,
            'hub_counts': hub_counts,
            'hub_coverage': hub_coverage,
            'primary_hubs': sorted(hub_counts.keys(), key=lambda h: hub_counts[h], reverse=True)[:5]
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_detector_instance: Optional[EntityDetector] = None

def get_detector() -> EntityDetector:
    """Get or create singleton detector instance."""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = EntityDetector()
        _detector_instance.load_vendor_vocabulary()
    return _detector_instance


def detect_hub_references(text: str) -> List[str]:
    """
    Quick function to detect hub references in text.
    
    Args:
        text: Text to analyze
        
    Returns:
        List of hub type names found
    """
    detector = get_detector()
    result = detector.detect_entities(text)
    return result['hub_references']


def enrich_chunk(text: str, metadata: Dict = None) -> Dict:
    """
    Enrich chunk metadata with hub references.
    
    Args:
        text: Chunk text
        metadata: Existing metadata
        
    Returns:
        Enriched metadata dict
    """
    detector = get_detector()
    return detector.enrich_chunk_metadata(text, metadata)


# =============================================================================
# TEST / DEMO
# =============================================================================

if __name__ == "__main__":
    # Test the detector
    detector = EntityDetector()
    detector.load_vendor_vocabulary()
    
    test_texts = [
        "Review earnings codes to make sure they are assigned the correct earnings tax categories.",
        "Set up the job code and department code for each position in the organization.",
        "FLSA requires overtime pay at 1.5x for hours worked over 40 in a workweek.",
        "Configure the deduction codes for 401k contributions and health insurance benefits.",
        "The workers compensation code must match the state jurisdiction requirements.",
    ]
    
    print("=" * 70)
    print("ENTITY DETECTOR TEST")
    print("=" * 70)
    
    for text in test_texts:
        print(f"\nText: {text[:60]}...")
        result = detector.detect_entities(text)
        print(f"  Hubs found: {result['hub_references']}")
        print(f"  Primary: {result['primary_hub']}")
        for hub, details in result['hub_details'].items():
            print(f"    - {hub}: {details['confidence']:.2f} ({details['match_count']} matches)")
