"""
Vendor Detector - Identifies payroll register vendor
"""

import re
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False


class VendorDetector:
    """Detects which payroll vendor created the PDF."""
    
    # Vendor signatures (keywords/patterns that identify each vendor)
    VENDOR_SIGNATURES = {
        'dayforce': {
            'keywords': ['dayforce', 'ceridian', 'payroll register report'],
            'patterns': [r'© \d{4} Dayforce', r'Ceridian'],
            'confidence_threshold': 70
        },
        'adp': {
            'keywords': ['adp', 'automatic data processing', 'adp payroll'],
            'patterns': [r'ADP\s+Payroll', r'Automatic Data Processing'],
            'confidence_threshold': 70
        },
        'paychex': {
            'keywords': ['paychex', 'paychex, inc'],
            'patterns': [r'Paychex\s+Payroll', r'© Paychex'],
            'confidence_threshold': 70
        },
        'quickbooks': {
            'keywords': ['quickbooks', 'intuit', 'qb payroll'],
            'patterns': [r'QuickBooks', r'Intuit Payroll'],
            'confidence_threshold': 70
        },
        'gusto': {
            'keywords': ['gusto', 'zenpayroll'],
            'patterns': [r'Gusto\s+Payroll', r'ZenPayroll'],
            'confidence_threshold': 70
        },
        'workday': {
            'keywords': ['workday', 'workday hcm'],
            'patterns': [r'Workday\s+Payroll', r'Workday HCM'],
            'confidence_threshold': 70
        },
        'ukg': {
            'keywords': ['ukg', 'ultipro', 'kronos', 'ultimate software'],
            'patterns': [r'UKG\s+Pro', r'UltiPro', r'Kronos'],
            'confidence_threshold': 70
        }
    }
    
    def detect_vendor(self, pdf_path: str) -> Dict[str, any]:
        """
        Detect vendor from PDF.
        
        Returns:
            {
                'vendor': 'dayforce',
                'confidence': 95,
                'method': 'keyword_match',
                'details': {...}
            }
        """
        if not PDFPLUMBER_AVAILABLE:
            return {'vendor': 'unknown', 'confidence': 0, 'method': 'no_pdfplumber'}
        
        try:
            # Extract text from first 2 pages (vendors usually ID themselves early)
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                for i, page in enumerate(pdf.pages[:2]):
                    text += page.extract_text() or ""
                    if i >= 1:  # Only need first 2 pages
                        break
                
                text_lower = text.lower()
            
            # Score each vendor
            vendor_scores = {}
            
            for vendor_name, signatures in self.VENDOR_SIGNATURES.items():
                score = 0
                matches = []
                
                # Check keywords
                for keyword in signatures['keywords']:
                    if keyword in text_lower:
                        score += 30
                        matches.append(f"keyword:{keyword}")
                
                # Check regex patterns
                for pattern in signatures['patterns']:
                    if re.search(pattern, text, re.IGNORECASE):
                        score += 40
                        matches.append(f"pattern:{pattern}")
                
                # Cap at 100
                score = min(score, 100)
                
                if score > 0:
                    vendor_scores[vendor_name] = {
                        'score': score,
                        'matches': matches
                    }
            
            # Find highest scoring vendor
            if vendor_scores:
                best_vendor = max(vendor_scores.keys(), key=lambda v: vendor_scores[v]['score'])
                best_score = vendor_scores[best_vendor]['score']
                
                if best_score >= self.VENDOR_SIGNATURES[best_vendor]['confidence_threshold']:
                    return {
                        'vendor': best_vendor,
                        'confidence': best_score,
                        'method': 'signature_match',
                        'details': vendor_scores[best_vendor],
                        'all_scores': vendor_scores
                    }
            
            # No confident match - try layout analysis
            layout_vendor = self._detect_by_layout(pdf_path)
            if layout_vendor:
                return layout_vendor
            
            # Unknown vendor
            return {
                'vendor': 'unknown',
                'confidence': 0,
                'method': 'no_match',
                'all_scores': vendor_scores
            }
        
        except Exception as e:
            logger.error(f"Vendor detection failed: {e}", exc_info=True)
            return {'vendor': 'unknown', 'confidence': 0, 'method': 'error', 'error': str(e)}
    
    def _detect_by_layout(self, pdf_path: str) -> Optional[Dict]:
        """Detect vendor by PDF layout characteristics."""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                page = pdf.pages[0]
                
                # Try table extraction
                tables = page.extract_tables()
                
                if tables:
                    # Has table structure
                    table = tables[0]
                    
                    # Dayforce typically has multi-column layout with headers:
                    # "Employee Info | Earnings | Taxes | Deductions"
                    if len(table) > 0 and len(table[0]) >= 4:
                        header_text = ' '.join([str(cell) for row in table[:2] for cell in row if cell])
                        if 'earnings' in header_text.lower() and 'taxes' in header_text.lower():
                            return {
                                'vendor': 'dayforce',
                                'confidence': 60,
                                'method': 'layout_analysis',
                                'details': 'Multi-column table layout typical of Dayforce'
                            }
            
            return None
        
        except Exception as e:
            logger.error(f"Layout detection failed: {e}")
            return None
    
    def get_vendor_strategy(self, vendor: str) -> str:
        """
        Get recommended extraction strategy for vendor.
        
        Returns strategy name: 'table_based', 'text_based', 'hybrid', etc.
        """
        strategy_map = {
            'dayforce': 'table_based',
            'adp': 'text_based',
            'paychex': 'text_based',
            'quickbooks': 'hybrid',
            'gusto': 'text_based',
            'workday': 'table_based',
            'ukg': 'hybrid',
            'unknown': 'auto'  # Try all strategies
        }
        
        return strategy_map.get(vendor, 'auto')
