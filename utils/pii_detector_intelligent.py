"""
Intelligent PII Detector - Self-Healing & Learning
===================================================

Philosophy: Understand intent, not just patterns.

Uses:
1. Semantic similarity (fuzzy matching)
2. Context analysis (column name + sample data)
3. Learning from user corrections
4. Conservative defaults (encrypt if uncertain)

Author: XLR8 Team
"""

import re
import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from difflib import SequenceMatcher
from datetime import datetime

logger = logging.getLogger(__name__)

# PII CONCEPTS - what we're looking for semantically
PII_CONCEPTS = {
    'ssn': {
        'description': 'Social Security Number',
        'variations': [
            'ssn', 'ss', 'social security', 'social sec', 'soc sec',
            'ss num', 'ss#', 'ssn#', 'social', 'ss number'
        ],
        'data_patterns': [r'\d{3}-\d{2}-\d{4}', r'\d{9}'],
        'sensitivity': 'critical'
    },
    'tax_id': {
        'description': 'Tax Identification Number',
        'variations': [
            'tax id', 'tin', 'fein', 'ein', 'fed id', 'federal id',
            'tax num', 'itin', 'employer id'
        ],
        'data_patterns': [r'\d{2}-\d{7}', r'\d{9}'],
        'sensitivity': 'critical'
    },
    'bank_account': {
        'description': 'Bank Account Information',
        'variations': [
            'bank', 'account', 'acct', 'routing', 'aba', 'ach',
            'direct deposit', 'dd', 'checking', 'savings',
            'bank num', 'acct num', 'account num', 'bank acct'
        ],
        'data_patterns': [r'\d{8,17}'],
        'sensitivity': 'critical'
    },
    'compensation': {
        'description': 'Salary/Compensation Information',
        'variations': [
            'salary', 'pay', 'wage', 'compensation', 'comp',
            'rate', 'hourly', 'annual', 'base pay', 'gross',
            'net pay', 'earnings', 'income', 'ytd', 'pay rate',
            'hour rate', 'annual sal', 'base sal', 'pay amt'
        ],
        'data_patterns': [r'\$[\d,]+\.?\d*', r'\d+\.\d{2}'],
        'sensitivity': 'high'
    },
    'birth_date': {
        'description': 'Date of Birth',
        'variations': [
            'birth', 'dob', 'bday', 'birthday', 'born', 'date of birth',
            'birth date', 'birthdate', 'age', 'birth dt'
        ],
        'data_patterns': [r'\d{1,2}/\d{1,2}/\d{2,4}', r'\d{4}-\d{2}-\d{2}'],
        'sensitivity': 'high'
    },
    'identity_doc': {
        'description': 'Identity Documents',
        'variations': [
            'passport', 'license', 'driver', 'dl', 'id num', 'id card',
            'visa', 'green card', 'work permit', 'i9', 'i-9',
            'national id', 'govt id', 'state id'
        ],
        'data_patterns': [r'[A-Z]{1,2}\d{6,8}'],
        'sensitivity': 'critical'
    },
    'contact': {
        'description': 'Personal Contact Information',
        'variations': [
            'phone', 'cell', 'mobile', 'home phone', 'personal phone',
            'email', 'personal email', 'home email', 'address',
            'home addr', 'street', 'residence'
        ],
        'data_patterns': [r'\(\d{3}\)\s*\d{3}-\d{4}', r'\d{3}-\d{3}-\d{4}'],
        'sensitivity': 'medium'
    },
    'medical': {
        'description': 'Medical/Health Information',
        'variations': [
            'medical', 'health', 'diagnosis', 'condition', 'disability',
            'prescription', 'treatment', 'doctor', 'hospital',
            'insurance claim', 'hipaa', 'phi'
        ],
        'data_patterns': [],
        'sensitivity': 'critical'
    },
    'demographic': {
        'description': 'Protected Demographics',
        'variations': [
            'race', 'ethnicity', 'religion', 'gender', 'sex',
            'orientation', 'national origin', 'citizenship',
            'veteran', 'disability status', 'marital'
        ],
        'data_patterns': [],
        'sensitivity': 'high'
    }
}

# Learning storage path
LEARNING_DB_PATH = "/data/pii_learning.json"


class IntelligentPIIDetector:
    """
    Self-healing PII detector that:
    1. Uses fuzzy matching for column names
    2. Analyzes sample data for patterns
    3. Learns from user corrections
    4. Errs on the side of caution (encrypt if uncertain)
    """
    
    def __init__(self, learning_path: str = LEARNING_DB_PATH):
        self.learning_path = learning_path
        self.learned = self._load_learning()
        self.detection_cache: Dict[str, bool] = {}
    
    def _load_learning(self) -> Dict:
        """Load learned patterns"""
        if os.path.exists(self.learning_path):
            try:
                with open(self.learning_path, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            'confirmed_pii': [],      # User confirmed these ARE PII
            'confirmed_safe': [],     # User confirmed these are NOT PII
            'auto_detected': {},      # Auto-detected with confidence scores
            'corrections': []         # History of corrections for analysis
        }
    
    def _save_learning(self):
        """Persist learned patterns"""
        os.makedirs(os.path.dirname(self.learning_path), exist_ok=True)
        with open(self.learning_path, 'w') as f:
            json.dump(self.learned, f, indent=2)
    
    def fuzzy_similarity(self, text1: str, text2: str) -> float:
        """Calculate fuzzy similarity between two strings"""
        # Normalize
        t1 = re.sub(r'[^a-z0-9]', '', text1.lower())
        t2 = re.sub(r'[^a-z0-9]', '', text2.lower())
        
        if not t1 or not t2:
            return 0.0
        
        # Direct containment
        if t1 in t2 or t2 in t1:
            return 0.9
        
        # Sequence matching
        return SequenceMatcher(None, t1, t2).ratio()
    
    def detect_pii_type(self, column_name: str, sample_data: List[Any] = None) -> Dict[str, Any]:
        """
        Detect if column contains PII and what type.
        
        Returns:
            {
                'is_pii': bool,
                'pii_type': str or None,
                'confidence': float (0-1),
                'reasoning': str,
                'sensitivity': str
            }
        """
        column_lower = column_name.lower()
        column_normalized = re.sub(r'[^a-z0-9]', '', column_lower)
        
        # EXCLUSION PATTERNS - these are metadata/classification fields, NOT PII
        # Even if they contain words like "earning", they're just category names
        safe_suffixes = ['_code', '_group', '_type', '_category', '_status', '_flag', 
                         '_id', '_key', '_name', '_desc', '_description', '_label']
        safe_words = ['code', 'group', 'type', 'category', 'status', 'flag', 'level',
                      'step', 'grade', 'class', 'tier', 'plan', 'model', 'template',
                      'frequency', 'period', 'schedule', 'rule', 'method', 'option']
        
        # Check if column is clearly a metadata/classification field
        for suffix in safe_suffixes:
            if column_lower.endswith(suffix):
                return {
                    'is_pii': False,
                    'pii_type': None,
                    'confidence': 0.95,
                    'reasoning': f'Metadata field (ends with {suffix})',
                    'sensitivity': 'none'
                }
        
        # Check if column contains safe classification words
        for word in safe_words:
            if word in column_lower and not any(pii in column_lower for pii in ['ssn', 'salary', 'wage', 'bank', 'account', 'birth', 'dob']):
                return {
                    'is_pii': False,
                    'pii_type': None,
                    'confidence': 0.9,
                    'reasoning': f'Classification field (contains "{word}")',
                    'sensitivity': 'none'
                }
        
        # Check learned patterns
        if column_lower in self.learned['confirmed_pii']:
            return {
                'is_pii': True,
                'pii_type': 'user_confirmed',
                'confidence': 1.0,
                'reasoning': 'User confirmed as PII',
                'sensitivity': 'high'
            }
        
        if column_lower in self.learned['confirmed_safe']:
            return {
                'is_pii': False,
                'pii_type': None,
                'confidence': 1.0,
                'reasoning': 'User confirmed as safe',
                'sensitivity': 'none'
            }
        
        # Check against PII concepts using fuzzy matching
        best_match = None
        best_score = 0.0
        
        for pii_type, concept in PII_CONCEPTS.items():
            for variation in concept['variations']:
                # Check containment first (fast path)
                var_normalized = re.sub(r'[^a-z0-9]', '', variation.lower())
                
                if var_normalized in column_normalized or column_normalized in var_normalized:
                    score = 0.95
                else:
                    score = self.fuzzy_similarity(column_name, variation)
                
                if score > best_score:
                    best_score = score
                    best_match = {
                        'type': pii_type,
                        'matched_variation': variation,
                        'sensitivity': concept['sensitivity']
                    }
        
        # Check sample data for patterns if we have it
        data_score = 0.0
        if sample_data and best_match:
            concept = PII_CONCEPTS.get(best_match['type'], {})
            patterns = concept.get('data_patterns', [])
            
            if patterns:
                matches = 0
                non_empty = 0
                for value in sample_data[:20]:  # Check first 20 values
                    if value and str(value).strip():
                        non_empty += 1
                        for pattern in patterns:
                            if re.search(pattern, str(value)):
                                matches += 1
                                break
                
                if non_empty > 0:
                    data_score = matches / non_empty * 0.3  # Data patterns add up to 0.3
        
        # Calculate final confidence
        final_score = best_score + data_score
        
        # Decision threshold
        if final_score >= 0.7:
            return {
                'is_pii': True,
                'pii_type': best_match['type'] if best_match else 'unknown',
                'confidence': min(1.0, final_score),
                'reasoning': f"Matched '{best_match['matched_variation']}' (score: {best_score:.2f})",
                'sensitivity': best_match['sensitivity'] if best_match else 'medium'
            }
        elif final_score >= 0.5:
            # Uncertain - err on side of caution for critical types
            if best_match and best_match['sensitivity'] == 'critical':
                return {
                    'is_pii': True,
                    'pii_type': best_match['type'],
                    'confidence': final_score,
                    'reasoning': f"Possible PII (score: {final_score:.2f}) - encrypting due to critical sensitivity",
                    'sensitivity': best_match['sensitivity']
                }
            else:
                return {
                    'is_pii': False,
                    'pii_type': None,
                    'confidence': 1.0 - final_score,
                    'reasoning': f"Low confidence match (score: {final_score:.2f})",
                    'sensitivity': 'none'
                }
        else:
            return {
                'is_pii': False,
                'pii_type': None,
                'confidence': 1.0 - final_score,
                'reasoning': 'No PII patterns detected',
                'sensitivity': 'none'
            }
    
    def analyze_columns(self, columns: List[str], sample_data: Dict[str, List] = None) -> Dict[str, Dict]:
        """
        Analyze multiple columns for PII.
        
        Returns dict of column_name -> detection_result
        """
        sample_data = sample_data or {}
        results = {}
        
        for col in columns:
            col_samples = sample_data.get(col, [])
            results[col] = self.detect_pii_type(col, col_samples)
        
        return results
    
    def get_columns_to_encrypt(self, columns: List[str], sample_data: Dict[str, List] = None) -> List[str]:
        """Get list of columns that should be encrypted"""
        analysis = self.analyze_columns(columns, sample_data)
        return [col for col, result in analysis.items() if result['is_pii']]
    
    def learn_pii(self, column_name: str, is_pii: bool, pii_type: str = None):
        """Learn from user correction"""
        column_lower = column_name.lower()
        
        # Record correction
        self.learned['corrections'].append({
            'column': column_name,
            'is_pii': is_pii,
            'pii_type': pii_type,
            'timestamp': datetime.now().isoformat()
        })
        
        if is_pii:
            if column_lower not in self.learned['confirmed_pii']:
                self.learned['confirmed_pii'].append(column_lower)
            if column_lower in self.learned['confirmed_safe']:
                self.learned['confirmed_safe'].remove(column_lower)
        else:
            if column_lower not in self.learned['confirmed_safe']:
                self.learned['confirmed_safe'].append(column_lower)
            if column_lower in self.learned['confirmed_pii']:
                self.learned['confirmed_pii'].remove(column_lower)
        
        self._save_learning()
        logger.info(f"[PII LEARNING] '{column_name}' marked as {'PII' if is_pii else 'SAFE'}")
    
    def get_pii_summary(self) -> Dict:
        """Get summary of PII detection learning"""
        return {
            'confirmed_pii_count': len(self.learned['confirmed_pii']),
            'confirmed_safe_count': len(self.learned['confirmed_safe']),
            'total_corrections': len(self.learned['corrections']),
            'concepts_tracked': len(PII_CONCEPTS)
        }


# Singleton
_detector: Optional[IntelligentPIIDetector] = None

def get_pii_detector() -> IntelligentPIIDetector:
    """Get or create singleton detector"""
    global _detector
    if _detector is None:
        _detector = IntelligentPIIDetector()
    return _detector


def detect_pii_columns(columns: List[str], sample_data: Dict[str, List] = None) -> List[str]:
    """Convenience function to get PII columns"""
    detector = get_pii_detector()
    return detector.get_columns_to_encrypt(columns, sample_data)


def is_pii_column(column_name: str, sample_data: List = None) -> bool:
    """Convenience function to check single column"""
    detector = get_pii_detector()
    result = detector.detect_pii_type(column_name, sample_data)
    return result['is_pii']
