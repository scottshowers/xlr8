"""
Intelligent Parser Orchestrator V3 - UNIVERSAL ITERATIVE PARSER
The crown jewel: Vendor detection + Multi-strategy + Validation + Iteration

Features:
- Auto-detects vendor (Dayforce, ADP, Paychex, etc.)
- Tries multiple strategies until 90%+ accuracy
- Validates and scores results
- Self-healing (retries with different approaches)
- Learning (can store what works per vendor)
"""

import logging
from typing import Dict, List, Any
from pathlib import Path
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)

try:
    from .vendor_detector import VendorDetector
    from .validation_engine import ValidationEngine
    from .strategy_library import StrategyLibrary
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False
    logger.warning("V3 dependencies not available")


class IntelligentParserOrchestratorV3:
    """
    Universal, iterative, self-healing parser.
    
    Workflow:
    1. Detect vendor (Dayforce, ADP, etc.)
    2. Get recommended strategies for that vendor
    3. Try each strategy
    4. Validate results
    5. If score >= 90%, success! Otherwise try next strategy
    6. Return best result (even if < 90%)
    """
    
    def __init__(self, custom_parsers_dir: str = None):
        self.logger = logging.getLogger(__name__)
        self.custom_parsers_dir = custom_parsers_dir
        
        if not DEPENDENCIES_AVAILABLE:
            raise Exception("V3 requires vendor_detector, validation_engine, and strategy_library")
        
        self.vendor_detector = VendorDetector()
        self.validation_engine = ValidationEngine()
        self.strategy_library = StrategyLibrary()
        
        self.min_acceptable_score = 90
        self.max_attempts = 5
    
    def parse(self, pdf_path: str, output_dir: str = '/data/parsed_registers', force_v3: bool = False) -> Dict[str, Any]:
        """
        Universal parser - tries multiple strategies until 90%+ accuracy.
        
        Returns:
            {
                'success': True,
                'excel_path': '/path/to/output.xlsx',
                'accuracy': 95,
                'method': 'V3-table_based',
                'vendor': 'dayforce',
                'vendor_confidence': 95,
                'attempts': 1,
                'validation': {...},
                'employees_found': 2,
                'earnings_found': 13,
                'taxes_found': 17,
                'deductions_found': 7
            }
        """
        try:
            self.logger.info(f"V3 Parser starting on: {pdf_path}")
            
            # Step 1: Detect vendor
            vendor_result = self.vendor_detector.detect_vendor(pdf_path)
            vendor = vendor_result['vendor']
            vendor_confidence = vendor_result['confidence']
            
            self.logger.info(f"Detected vendor: {vendor} (confidence: {vendor_confidence}%)")
            
            # Step 2: Get strategies for this vendor
            strategies = self.strategy_library.get_strategies_for_vendor(vendor)
            
            self.logger.info(f"Will try {len(strategies)} strategies: {[s.name for s in strategies]}")
            
            # Step 3: Try each strategy until we hit 90%+ accuracy
            best_result = None
            best_score = 0
            attempts = []
            
            for i, strategy in enumerate(strategies):
                if i >= self.max_attempts:
                    self.logger.info(f"Reached max attempts ({self.max_attempts}), stopping")
                    break
                
                self.logger.info(f"Attempt {i+1}: Trying strategy '{strategy.name}'")
                
                try:
                    # Extract data
                    structured_data = strategy.extract(pdf_path)
                    
                    # Validate
                    validation = self.validation_engine.validate(structured_data, pdf_path)
                    score = validation['score']
                    
                    self.logger.info(f"Strategy '{strategy.name}' scored: {score}%")
                    
                    # Store attempt
                    attempt = {
                        'strategy': strategy.name,
                        'score': score,
                        'validation': validation,
                        'data': structured_data
                    }
                    attempts.append(attempt)
                    
                    # Update best if better
                    if score > best_score:
                        best_result = attempt
                        best_score = score
                    
                    # Success! Stop trying
                    if score >= self.min_acceptable_score:
                        self.logger.info(f"✅ Success! Score {score}% >= {self.min_acceptable_score}%")
                        break
                
                except Exception as e:
                    self.logger.error(f"Strategy '{strategy.name}' failed: {e}", exc_info=True)
                    attempts.append({
                        'strategy': strategy.name,
                        'score': 0,
                        'error': str(e)
                    })
            
            # Step 4: Use best result (even if < 90%)
            if not best_result:
                return {
                    'success': False,
                    'error': 'All strategies failed',
                    'vendor': vendor,
                    'vendor_confidence': vendor_confidence,
                    'attempts': attempts
                }
            
            # Step 5: Create Excel output
            tabs = self._create_excel_tabs(best_result['data'])
            excel_path = self._write_excel(tabs, pdf_path, output_dir, best_result['strategy'])
            
            # Step 6: Return result
            return {
                'success': True,
                'excel_path': excel_path,
                'accuracy': best_score,
                'method': f"V3-{best_result['strategy']}",
                'vendor': vendor,
                'vendor_confidence': vendor_confidence,
                'attempts': len(attempts),
                'validation': best_result['validation'],
                'all_attempts': attempts,
                'employees_found': len(best_result['data'].get('employees', [])),
                'earnings_found': len(best_result['data'].get('earnings', [])),
                'taxes_found': len(best_result['data'].get('taxes', [])),
                'deductions_found': len(best_result['data'].get('deductions', []))
            }
        
        except Exception as e:
            self.logger.error(f"V3 parsing failed: {e}", exc_info=True)
            return {'success': False, 'error': str(e), 'method': 'V3'}
    
    def _create_excel_tabs(self, structured: Dict) -> Dict[str, pd.DataFrame]:
        """Create 4 Excel tabs from structured data."""
        summary_data = []
        for emp in structured.get('employees', []):
            emp_id = emp['employee_id']
            emp_earnings = [e for e in structured.get('earnings', []) if e.get('employee_id') == emp_id]
            emp_taxes = [t for t in structured.get('taxes', []) if t.get('employee_id') == emp_id]
            emp_deductions = [d for d in structured.get('deductions', []) if d.get('employee_id') == emp_id]
            
            summary_data.append({
                'Employee ID': emp_id,
                'Name': emp.get('employee_name', ''),
                'Department': emp.get('department', ''),
                'Total Earnings': sum(e.get('amount', 0) for e in emp_earnings),
                'Total Taxes': sum(t.get('amount', 0) for t in emp_taxes),
                'Total Deductions': sum(d.get('amount', 0) for d in emp_deductions),
                'Net Pay': sum(e.get('amount', 0) for e in emp_earnings) - 
                          sum(t.get('amount', 0) for t in emp_taxes) - 
                          sum(d.get('amount', 0) for d in emp_deductions)
            })
        
        return {
            'Employee Summary': pd.DataFrame(summary_data),
            'Earnings': pd.DataFrame([{
                'Employee ID': e.get('employee_id', ''),
                'Name': e.get('employee_name', ''),
                'Description': e.get('description', ''),
                'Hours': e.get('hours', 0),
                'Rate': e.get('rate', 0),
                'Amount': e.get('amount', 0),
                'Current YTD': e.get('current_ytd', e.get('amount', 0))
            } for e in structured.get('earnings', [])]),
            'Taxes': pd.DataFrame([{
                'Employee ID': t.get('employee_id', ''),
                'Name': t.get('employee_name', ''),
                'Description': t.get('description', ''),
                'Wages Base': t.get('wages_base', 0),
                'Amount': t.get('amount', 0),
                'Wages YTD': t.get('wages_ytd', 0),
                'Amount YTD': t.get('amount_ytd', t.get('amount', 0))
            } for t in structured.get('taxes', [])]),
            'Deductions': pd.DataFrame([{
                'Employee ID': d.get('employee_id', ''),
                'Name': d.get('employee_name', ''),
                'Description': d.get('description', ''),
                'Scheduled': d.get('scheduled', 0),
                'Amount': d.get('amount', 0),
                'Amount YTD': d.get('amount_ytd', d.get('amount', 0))
            } for d in structured.get('deductions', [])])
        }
    
    def _write_excel(self, tabs: Dict[str, pd.DataFrame], pdf_path: str, output_dir: str, strategy_name: str) -> str:
        """Write Excel file."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = output_dir / f"{Path(pdf_path).stem}_parsed_v3_{strategy_name}_{timestamp}.xlsx"
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            for tab_name, df in tabs.items():
                df.to_excel(writer, sheet_name=tab_name, index=False)
        
        return str(output_path)
