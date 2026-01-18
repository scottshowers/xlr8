"""
PLAYBOOK FRAMEWORK - Match Service
===================================

Handles matching uploaded files to playbook step requirements.

This replaces the scattered fuzzy matching logic from YearEndPlaybook.jsx
and playbook_parser.py with a centralized, testable service.

Author: XLR8 Team
Created: January 18, 2026
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    """Result of matching files to requirements."""
    requirement: str
    matched_file: Optional[str] = None
    confidence: float = 0.0
    match_method: Optional[str] = None  # 'exact', 'substring', 'words', 'fuzzy'


class MatchService:
    """
    Service for matching uploaded files to playbook step requirements.
    
    Uses multiple matching strategies:
    1. Exact match (normalized)
    2. Substring match
    3. Word overlap match
    4. Fuzzy prefix match
    """
    
    # Words to ignore when matching
    STOP_WORDS = {
        'the', 'a', 'an', 'and', 'or', 'for', 'to', 'of', 'in', 'on',
        'report', 'reports', 'file', 'files', 'data', 'export'
    }
    
    def __init__(self):
        pass
    
    def normalize(self, text: str) -> str:
        """Normalize text for matching - lowercase, remove punctuation."""
        if not text:
            return ""
        # Remove apostrophes, underscores, hyphens, periods
        normalized = re.sub(r'[\'_\-\.]', ' ', text.lower())
        # Remove other punctuation
        normalized = re.sub(r'[^\w\s]', '', normalized)
        # Collapse whitespace
        normalized = ' '.join(normalized.split())
        return normalized.strip()
    
    def get_words(self, text: str, min_length: int = 3) -> Set[str]:
        """Extract significant words from text."""
        normalized = self.normalize(text)
        words = set(w for w in normalized.split() if len(w) >= min_length)
        return words - self.STOP_WORDS
    
    def match_file_to_requirement(
        self, 
        requirement: str, 
        filename: str
    ) -> Tuple[bool, float, str]:
        """
        Try to match a single file to a requirement.
        
        Returns: (matched, confidence, method)
        """
        req_norm = self.normalize(requirement)
        file_norm = self.normalize(filename)
        
        if not req_norm or not file_norm:
            return False, 0.0, None
        
        # Method 1: Exact match (after normalization)
        if req_norm == file_norm:
            return True, 1.0, 'exact'
        
        # Method 2: Substring match (requirement in filename)
        if req_norm in file_norm:
            return True, 0.95, 'substring'
        
        # Method 3: All requirement words appear in filename
        req_words = self.get_words(requirement)
        file_words = self.get_words(filename)
        
        if req_words and req_words.issubset(file_words):
            return True, 0.9, 'words'
        
        # Method 4: Fuzzy word matching (prefixes)
        if len(req_words) >= 2:
            matches = 0
            for rw in req_words:
                for fw in file_words:
                    # Exact word match
                    if rw == fw:
                        matches += 1
                        break
                    # Prefix match (at least 4 chars)
                    if len(rw) >= 4 and len(fw) >= 4:
                        if rw.startswith(fw) or fw.startswith(rw):
                            matches += 1
                            break
            
            # Require most words to match
            match_ratio = matches / len(req_words)
            if match_ratio >= 0.7 and matches >= 2:
                return True, 0.8 * match_ratio, 'fuzzy'
        
        return False, 0.0, None
    
    def match_files_to_requirements(
        self,
        requirements: List[str],
        uploaded_files: List[str]
    ) -> Dict[str, MatchResult]:
        """
        Match a list of requirements against uploaded files.
        
        Returns dict: requirement -> MatchResult
        """
        results = {}
        used_files = set()  # Don't double-match files
        
        for req in requirements:
            if not req:
                continue
            
            best_match = None
            best_confidence = 0.0
            best_method = None
            
            for filename in uploaded_files:
                if filename in used_files:
                    continue
                
                matched, confidence, method = self.match_file_to_requirement(req, filename)
                
                if matched and confidence > best_confidence:
                    best_match = filename
                    best_confidence = confidence
                    best_method = method
            
            results[req] = MatchResult(
                requirement=req,
                matched_file=best_match,
                confidence=best_confidence,
                match_method=best_method
            )
            
            if best_match:
                used_files.add(best_match)
                logger.debug(f"[MATCH] '{req}' -> '{best_match}' ({best_method}, {best_confidence:.2f})")
            else:
                logger.debug(f"[MATCH] '{req}' -> NO MATCH")
        
        return results
    
    def match_step_requirements(
        self,
        step_requirements: Dict[str, List[str]],  # step_id -> [requirements]
        uploaded_files: List[str]
    ) -> Dict[str, Dict[str, MatchResult]]:
        """
        Match requirements for multiple steps.
        
        Returns: step_id -> {requirement -> MatchResult}
        """
        all_results = {}
        used_files = set()
        
        for step_id, requirements in step_requirements.items():
            step_results = {}
            
            for req in requirements:
                if not req:
                    continue
                
                best_match = None
                best_confidence = 0.0
                best_method = None
                
                for filename in uploaded_files:
                    if filename in used_files:
                        continue
                    
                    matched, confidence, method = self.match_file_to_requirement(req, filename)
                    
                    if matched and confidence > best_confidence:
                        best_match = filename
                        best_confidence = confidence
                        best_method = method
                
                step_results[req] = MatchResult(
                    requirement=req,
                    matched_file=best_match,
                    confidence=best_confidence,
                    match_method=best_method
                )
                
                if best_match:
                    used_files.add(best_match)
            
            all_results[step_id] = step_results
        
        return all_results
    
    def get_match_summary(
        self, 
        results: Dict[str, MatchResult]
    ) -> Dict[str, any]:
        """Get summary statistics for match results."""
        total = len(results)
        matched = sum(1 for r in results.values() if r.matched_file)
        missing = total - matched
        
        avg_confidence = 0.0
        if matched > 0:
            avg_confidence = sum(
                r.confidence for r in results.values() if r.matched_file
            ) / matched
        
        return {
            'total_requirements': total,
            'matched': matched,
            'missing': missing,
            'match_rate': matched / total if total > 0 else 0,
            'avg_confidence': avg_confidence,
            'missing_requirements': [
                r.requirement for r in results.values() if not r.matched_file
            ]
        }


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_match_service = None

def get_match_service() -> MatchService:
    """Get the singleton match service instance."""
    global _match_service
    if _match_service is None:
        _match_service = MatchService()
    return _match_service
