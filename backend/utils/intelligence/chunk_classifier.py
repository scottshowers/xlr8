"""
Chunk Classifier for Five Truths Architecture
==============================================

Classifies documents at upload time with:
- truth_type: intent | reference | regulatory | compliance (+ reality handled by DuckDB)
- domain: demographics | earnings | deductions | taxes | time | organization | benefits | recruiting | learning
- source_authority: government | vendor | industry | customer | internal

This is DETERMINISTIC classification using pattern matching - no LLM involved.
Used by RAGHandler to enrich chunk metadata for targeted retrieval.

Phase 2B.1 Implementation - January 2026
"""

import re
import logging
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ClassificationResult:
    """Result of document classification."""
    truth_type: str
    domain: str
    source_authority: str
    confidence: float
    classification_signals: Dict[str, List[str]]  # What triggered each classification


# =============================================================================
# PATTERN DEFINITIONS
# =============================================================================

# Truth Type Patterns - What kind of document is this?
TRUTH_TYPE_PATTERNS = {
    'intent': {
        'filenames': ['sow', 'statement_of_work', 'requirements', 'scope', 'project_plan', 
                      'contract', 'proposal', 'rfp', 'rfi', 'specification', 'spec_'],
        'content': ['customer wants', 'shall implement', 'requirement:', 'deliverable',
                    'in scope', 'out of scope', 'acceptance criteria', 'milestone',
                    'the client', 'customer requires', 'must have', 'nice to have',
                    'phase 1', 'phase 2', 'go-live', 'implementation timeline']
    },
    'reference': {
        'filenames': ['best_practice', 'best-practice', 'guide', 'manual', 'documentation',
                      'reference', 'how_to', 'how-to', 'howto', 'tutorial', 'user_guide',
                      'admin_guide', 'configuration_guide', 'setup_guide', 'implementation'],
        'content': ['recommended', 'best practice', 'should configure', 'standard approach',
                    'typical setup', 'common configuration', 'suggested', 'guideline',
                    'pro tip', 'note:', 'important:', 'warning:', 'tip:',
                    'step 1', 'step 2', 'navigate to', 'click on', 'select the']
    },
    'regulatory': {
        'filenames': ['irs', 'dol', 'flsa', 'regulation', 'law', 'code', 'statute',
                      'compliance', 'legal', 'mandate', 'federal', 'state_law',
                      'pub_15', 'pub_505', 'form_w', 'form_941', 'form_940'],
        'content': ['must comply', 'required by law', 'penalty', 'federal requirement',
                    'state requirement', 'irs requires', 'department of labor',
                    'fair labor standards', 'affordable care act', 'aca',
                    'internal revenue code', 'irc section', 'cfr', 'usc',
                    'effective date', 'compliance deadline', 'filing deadline',
                    'employer must', 'employer shall', 'failure to comply']
    },
    'compliance': {
        'filenames': ['policy', 'procedure', 'internal', 'company_policy', 'handbook',
                      'soc2', 'soc_2', 'audit', 'control', 'governance'],
        'content': ['company policy', 'internal requirement', 'our standard', 'approved by',
                    'audit requirement', 'control objective', 'soc 2', 'sox',
                    'internal control', 'segregation of duties', 'access control',
                    'review and approval', 'exception process', 'escalation']
    }
}

# Domain Patterns - What HCM functional area?
DOMAIN_PATTERNS = {
    'demographics': {
        'keywords': ['employee', 'worker', 'hire', 'terminate', 'status', 'personal',
                     'address', 'phone', 'email', 'ssn', 'birth', 'gender', 'ethnicity',
                     'veteran', 'disability', 'emergency contact', 'dependent',
                     'marital', 'citizenship', 'i-9', 'e-verify', 'rehire',
                     'new hire', 'onboarding', 'offboarding', 'separation'],
        'weight': 1.0
    },
    'earnings': {
        'keywords': ['pay', 'wage', 'salary', 'compensation', 'earning code', 'earning_code',
                     'regular pay', 'overtime', 'bonus', 'commission', 'incentive',
                     'shift differential', 'on-call', 'callback', 'holiday pay',
                     'vacation pay', 'sick pay', 'pto payout', 'severance',
                     'retro pay', 'gross pay', 'pay rate', 'hourly rate'],
        'weight': 1.0
    },
    'deductions': {
        'keywords': ['deduction', 'benefit', '401k', '401(k)', 'insurance', 'hsa', 'fsa',
                     'medical', 'dental', 'vision', 'life insurance', 'ltd', 'std',
                     'garnishment', 'child support', 'levy', 'loan repayment',
                     'union dues', 'parking', 'pre-tax', 'post-tax', 'roth',
                     'contribution', 'employer match', 'vesting'],
        'weight': 1.0
    },
    'taxes': {
        'keywords': ['tax', 'withholding', 'w-2', 'w-4', 'sui', 'suta', 'futa', 'fica',
                     'federal tax', 'state tax', 'local tax', 'medicare', 'social security',
                     'taxable wages', 'tax exempt', 'tax jurisdiction', 'resident',
                     'non-resident', 'reciprocity', 'tax filing', 'quarterly',
                     'form 941', 'form 940', 'w2', 'w4', '1099'],
        'weight': 1.0
    },
    'time': {
        'keywords': ['time', 'attendance', 'pto', 'accrual', 'schedule', 'timesheet',
                     'clock', 'punch', 'time off', 'leave', 'absence', 'fmla',
                     'vacation', 'sick time', 'holiday', 'comp time',
                     'overtime rule', 'shift', 'work week', 'pay period',
                     'time tracking', 'geofence', 'attestation'],
        'weight': 1.0
    },
    'organization': {
        'keywords': ['company', 'department', 'location', 'org', 'hierarchy', 'structure',
                     'cost center', 'business unit', 'division', 'subsidiary',
                     'legal entity', 'ein', 'fein', 'work location', 'home location',
                     'reporting', 'manager', 'supervisor', 'org chart', 'job code',
                     'position', 'job title', 'grade', 'level', 'flsa status'],
        'weight': 1.0
    },
    'benefits': {
        'keywords': ['open enrollment', 'benefits administration', 'carrier', 'plan',
                     'coverage', 'eligible', 'eligibility', 'qualifying event',
                     'life event', 'cobra', 'hipaa', 'beneficiary', 'premium',
                     'employee contribution', 'employer contribution', 'wellness',
                     'eap', 'tuition reimbursement', 'stipend'],
        'weight': 1.0
    },
    'recruiting': {
        'keywords': ['requisition', 'candidate', 'applicant', 'interview', 'offer',
                     'job posting', 'talent acquisition', 'ats', 'background check',
                     'drug test', 'reference check', 'recruitment', 'sourcing',
                     'pipeline', 'requisition', 'headcount'],
        'weight': 0.8
    },
    'learning': {
        'keywords': ['training', 'course', 'certification', 'compliance training',
                     'lms', 'learning management', 'curriculum', 'competency',
                     'skill', 'development', 'performance review', 'goal'],
        'weight': 0.8
    }
}

# Source Authority Patterns - Who created this document?
SOURCE_AUTHORITY_PATTERNS = {
    'government': {
        'filenames': ['irs', 'dol', 'ssa', 'eeoc', 'osha', 'nlrb', 'pbgc',
                      'pub_', 'form_', 'circular', 'regulation', 'cfr'],
        'content': ['internal revenue service', 'department of labor', 
                    'social security administration', 'equal employment',
                    'occupational safety', 'irs.gov', 'dol.gov', 'ssa.gov',
                    'federal register', 'code of federal regulations'],
        'domains': ['irs.gov', 'dol.gov', 'ssa.gov', 'eeoc.gov', 'osha.gov']
    },
    'vendor': {
        'filenames': ['ukg', 'ultipro', 'kronos', 'workday', 'adp', 'oracle',
                      'sap', 'successfactors', 'dayforce', 'ceridian', 'paylocity',
                      'paycom', 'paychex', 'netsuite', 'bamboohr'],
        'content': ['ukg pro', 'ultipro', 'kronos', 'workforce dimensions',
                    'workday hcm', 'adp workforce', 'oracle hcm', 'peoplesoft',
                    'successfactors', 'dayforce', 'product documentation',
                    'release notes', 'known issues', 'support article'],
        'domains': ['ukg.com', 'workday.com', 'adp.com', 'oracle.com', 'sap.com']
    },
    'industry': {
        'filenames': ['shrm', 'worldatwork', 'apa', 'isaca', 'aicpa'],
        'content': ['shrm', 'society for human resource', 'worldatwork',
                    'american payroll association', 'industry standard',
                    'benchmark', 'survey results', 'market data'],
        'domains': ['shrm.org', 'worldatwork.org', 'americanpayroll.org']
    },
    'customer': {
        'filenames': ['sow', 'contract', 'requirements', 'meeting_notes',
                      'client_', 'customer_'],
        'content': ['our company', 'we require', 'our policy', 'our process',
                    'meeting notes', 'action items', 'discussed with',
                    'customer decision', 'client preference'],
        'domains': []  # Customer docs don't have standard domains
    },
    'internal': {
        'filenames': ['internal', 'draft', 'working', 'notes', 'template'],
        'content': ['internal use', 'do not distribute', 'confidential',
                    'draft version', 'working document', 'for review'],
        'domains': []
    }
}


class ChunkClassifier:
    """
    Classify documents for Five Truths metadata enrichment.
    
    Deterministic pattern-based classification - no LLM involved.
    Runs at document upload time, applies to all chunks from that document.
    """
    
    def __init__(self):
        """Initialize the classifier with compiled patterns for performance."""
        # Pre-compile regex patterns for content matching
        self._compiled_patterns = {}
        self._initialize_patterns()
        logger.info("ChunkClassifier initialized")
    
    def _initialize_patterns(self):
        """Compile regex patterns for faster matching."""
        # For now, we use simple string matching which is fast enough
        # Can optimize to compiled regex if needed for performance
        pass
    
    def classify_document(self, filename: str, content: str, 
                          existing_truth_type: str = None) -> ClassificationResult:
        """
        Classify a document for Five Truths metadata.
        
        Args:
            filename: Original filename
            content: Full document text (will sample first 5000 chars)
            existing_truth_type: If already classified (e.g., from upload UI), 
                                 use this and only classify domain/authority
        
        Returns:
            ClassificationResult with truth_type, domain, source_authority, confidence
        """
        filename_lower = filename.lower() if filename else ''
        content_sample = (content[:5000] if content else '').lower()
        
        signals = {
            'truth_type': [],
            'domain': [],
            'source_authority': []
        }
        
        # 1. Classify truth_type (unless already provided)
        if existing_truth_type and existing_truth_type in ['intent', 'reference', 'regulatory', 'compliance']:
            truth_type = existing_truth_type
            truth_confidence = 1.0  # User-specified
            signals['truth_type'].append(f'user_specified:{existing_truth_type}')
        else:
            truth_type, truth_confidence, truth_signals = self._classify_truth_type(
                filename_lower, content_sample
            )
            signals['truth_type'] = truth_signals
        
        # 2. Classify domain
        domain, domain_confidence, domain_signals = self._classify_domain(content_sample)
        signals['domain'] = domain_signals
        
        # 3. Classify source authority
        authority, authority_confidence, authority_signals = self._classify_source_authority(
            filename_lower, content_sample
        )
        signals['source_authority'] = authority_signals
        
        # Calculate overall confidence as weighted average
        overall_confidence = (
            truth_confidence * 0.4 +
            domain_confidence * 0.3 +
            authority_confidence * 0.3
        )
        
        result = ClassificationResult(
            truth_type=truth_type,
            domain=domain,
            source_authority=authority,
            confidence=round(overall_confidence, 2),
            classification_signals=signals
        )
        
        logger.info(f"[CLASSIFY] {filename}: truth={truth_type}, domain={domain}, "
                    f"authority={authority}, confidence={overall_confidence:.2f}")
        
        return result
    
    def _classify_truth_type(self, filename: str, content: str) -> Tuple[str, float, List[str]]:
        """
        Determine which truth type this document represents.
        
        Returns:
            (truth_type, confidence, signals)
        """
        scores = {}
        signals = []
        
        for truth_type, patterns in TRUTH_TYPE_PATTERNS.items():
            score = 0
            type_signals = []
            
            # Check filename patterns (weighted higher)
            for pattern in patterns['filenames']:
                if pattern in filename:
                    score += 2
                    type_signals.append(f'filename:{pattern}')
            
            # Check content patterns
            for pattern in patterns['content']:
                if pattern in content:
                    score += 1
                    type_signals.append(f'content:{pattern}')
            
            scores[truth_type] = score
            if type_signals:
                signals.extend([f'{truth_type}:{s}' for s in type_signals[:3]])  # Limit signals
        
        # Determine winner
        max_score = max(scores.values()) if scores else 0
        
        if max_score == 0:
            # No matches - default to reference
            return ('reference', 0.4, ['default:no_matches'])
        
        # Get winner and calculate confidence based on margin
        winner = max(scores, key=scores.get)
        second_score = sorted(scores.values(), reverse=True)[1] if len(scores) > 1 else 0
        
        # Confidence based on score magnitude and margin over second place
        margin = (max_score - second_score) / max(max_score, 1)
        base_confidence = min(0.5 + (max_score * 0.1), 0.95)
        confidence = base_confidence * (0.7 + 0.3 * margin)
        
        return (winner, round(confidence, 2), signals)
    
    def _classify_domain(self, content: str) -> Tuple[str, float, List[str]]:
        """
        Determine the HCM domain for this document.
        
        Returns:
            (domain, confidence, signals)
        """
        scores = {}
        signals = []
        
        for domain, config in DOMAIN_PATTERNS.items():
            score = 0
            domain_signals = []
            weight = config.get('weight', 1.0)
            
            for keyword in config['keywords']:
                # Count occurrences (capped at 5 to prevent gaming)
                count = min(content.count(keyword), 5)
                if count > 0:
                    score += count * weight
                    domain_signals.append(f'{keyword}:{count}')
            
            scores[domain] = score
            if domain_signals:
                signals.extend([f'{domain}:{s}' for s in domain_signals[:2]])
        
        # Determine winner
        max_score = max(scores.values()) if scores else 0
        
        if max_score < 2:
            # Too few signals - return general
            return ('general', 0.3, ['low_signal_count'])
        
        winner = max(scores, key=scores.get)
        total_score = sum(scores.values())
        
        # Confidence based on winner's share of total
        confidence = (scores[winner] / total_score) if total_score > 0 else 0.3
        confidence = min(max(confidence, 0.4), 0.95)
        
        return (winner, round(confidence, 2), signals)
    
    def _classify_source_authority(self, filename: str, content: str) -> Tuple[str, float, List[str]]:
        """
        Determine the source authority for this document.
        
        Returns:
            (authority, confidence, signals)
        """
        scores = {}
        signals = []
        
        for authority, patterns in SOURCE_AUTHORITY_PATTERNS.items():
            score = 0
            auth_signals = []
            
            # Check filename patterns (weighted higher)
            for pattern in patterns['filenames']:
                if pattern in filename:
                    score += 3
                    auth_signals.append(f'filename:{pattern}')
            
            # Check content patterns
            for pattern in patterns['content']:
                if pattern in content:
                    score += 1
                    auth_signals.append(f'content:{pattern}')
            
            # Check domain patterns (URLs in content)
            for domain in patterns.get('domains', []):
                if domain in content:
                    score += 2
                    auth_signals.append(f'domain:{domain}')
            
            scores[authority] = score
            if auth_signals:
                signals.extend([f'{authority}:{s}' for s in auth_signals[:2]])
        
        # Determine winner
        max_score = max(scores.values()) if scores else 0
        
        if max_score == 0:
            # No clear source - default to internal
            return ('internal', 0.4, ['default:no_matches'])
        
        winner = max(scores, key=scores.get)
        
        # Confidence based on score magnitude
        confidence = min(0.5 + (max_score * 0.1), 0.95)
        
        return (winner, round(confidence, 2), signals)
    
    def classify_chunk(self, chunk_text: str, document_classification: ClassificationResult) -> Dict:
        """
        Apply document-level classification to a chunk with optional chunk-level refinement.
        
        For most cases, we just propagate document classification.
        But we can detect if a specific chunk is about a different domain.
        
        Args:
            chunk_text: The chunk content
            document_classification: The document-level classification
        
        Returns:
            Dict of metadata to add to the chunk
        """
        # Start with document-level classification
        metadata = {
            'truth_type': document_classification.truth_type,
            'domain': document_classification.domain,
            'source_authority': document_classification.source_authority,
            'classification_confidence': document_classification.confidence
        }
        
        # Optional: Check if this chunk has a clearly different domain
        # This is useful for large documents that span multiple domains
        chunk_lower = chunk_text.lower()
        chunk_domain, chunk_domain_confidence, _ = self._classify_domain(chunk_lower)
        
        # Only override if chunk domain is clearly different AND confident
        if (chunk_domain != document_classification.domain and 
            chunk_domain_confidence > 0.7 and 
            chunk_domain != 'general'):
            metadata['chunk_domain'] = chunk_domain
            metadata['chunk_domain_confidence'] = chunk_domain_confidence
        
        return metadata


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_classifier_instance: Optional[ChunkClassifier] = None

def get_classifier() -> ChunkClassifier:
    """Get the singleton ChunkClassifier instance."""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = ChunkClassifier()
    return _classifier_instance


def classify_document(filename: str, content: str, 
                      existing_truth_type: str = None) -> ClassificationResult:
    """
    Convenience function to classify a document.
    
    Args:
        filename: Original filename
        content: Document text
        existing_truth_type: Optional pre-classified truth type
    
    Returns:
        ClassificationResult
    """
    classifier = get_classifier()
    return classifier.classify_document(filename, content, existing_truth_type)
