"""
Adaptive Parser Orchestrator - TRUE ITERATIVE LEARNING
Self-healing parser that adapts strategies until 90%+ accuracy or max iterations

This is the crown jewel: learns from failures and evolves strategies.
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
    from .diagnostic_analyzer import DiagnosticAnalyzer
    from .strategy_mutator import StrategyMutator
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    # Try absolute imports for standalone testing
    try:
        import sys
        sys.path.append('/home/claude')
        from diagnostic_analyzer import DiagnosticAnalyzer
        from strategy_mutator import StrategyMutator
        from validation_engine import ValidationEngine
        DEPENDENCIES_AVAILABLE = True
    except ImportError:
        DEPENDENCIES_AVAILABLE = False
        logger.warning("Adaptive orchestrator dependencies not available")


class AdaptiveParserOrchestrator:
    """
    Truly adaptive parser that LEARNS and EVOLVES strategies.
    
    Workflow:
    1. Try initial strategy → Validate → 40% accuracy
    2. Diagnose: "Missing IDs for 38 employees"
    3. Mutate: "Add ID extraction from context"
    4. Try adapted strategy → Validate → 70% accuracy
    5. Diagnose: "Multi-row structure not grouped"
    6. Mutate: "Enable row grouping"
    7. Try adapted strategy → Validate → 92% accuracy → SUCCESS!
    
    Key Innovation: Doesn't give up after trying 3 pre-made strategies.
    Adapts and evolves until it figures it out.
    """
    
    def __init__(self, custom_parsers_dir: str = None):
        self.logger = logging.getLogger(__name__)
        self.custom_parsers_dir = custom_parsers_dir
        
        if not DEPENDENCIES_AVAILABLE:
            raise Exception("Adaptive orchestrator requires all dependencies")
        
        self.validator = ValidationEngine()
        self.diagnostic_analyzer = DiagnosticAnalyzer()
        self.strategy_mutator = StrategyMutator()
        
        # Try to load other components (vendor detector, strategy library)
        try:
            from .vendor_detector import VendorDetector
            from .strategy_library import StrategyLibrary
            self.vendor_detector = VendorDetector()
            self.strategy_library = StrategyLibrary()
        except:
            self.vendor_detector = None
            self.strategy_library = None
            logger.warning("Vendor detector and strategy library not available")
        
        # Configuration
        self.target_accuracy = 90
        self.max_iterations = 10
        self.min_improvement = 5  # Must improve by 5% to continue
    
    def parse(self, pdf_path: str, output_dir: str = '/data/parsed_registers', 
              force_adaptive: bool = True) -> Dict[str, Any]:
        """
        Adaptive parsing with iterative learning.
        
        Returns:
            {
                'success': True,
                'excel_path': '/path/to/output.xlsx',
                'accuracy': 92,
                'method': 'adaptive_iter3',
                'iterations': 3,
                'learning_path': [
                    {'iteration': 1, 'score': 40, 'diagnosis': [...], 'mutations': [...]},
                    {'iteration': 2, 'score': 70, 'diagnosis': [...], 'mutations': [...]},
                    {'iteration': 3, 'score': 92, 'diagnosis': [], 'mutations': []}
                ],
                ...
            }
        """
        try:
            self.logger.info(f"🧠 ADAPTIVE PARSER starting on: {pdf_path}")
            self.logger.info(f"Target: {self.target_accuracy}% accuracy in max {self.max_iterations} iterations")
            
            # Step 1: Get initial strategy
            initial_strategy = self._get_initial_strategy(pdf_path)
            
            # Step 2: Iterative learning loop
            learning_path = []
            current_strategy = initial_strategy
            best_result = None
            best_score = 0
            
            for iteration in range(1, self.max_iterations + 1):
                self.logger.info(f"\n{'='*80}")
                self.logger.info(f"🔄 ITERATION {iteration}/{self.max_iterations}")
                self.logger.info(f"{'='*80}")
                
                # Try current strategy
                try:
                    structured_data = current_strategy.extract(pdf_path)
                    
                    # Validate results
                    validation = self.validator.validate(structured_data, pdf_path)
                    score = validation['score']
                    
                    self.logger.info(f"📊 Score: {score}%")
                    
                    # Record iteration
                    iteration_record = {
                        'iteration': iteration,
                        'strategy_name': current_strategy.name,
                        'score': score,
                        'validation': validation,
                        'structured_data': structured_data
                    }
                    
                    # Update best if better
                    if score > best_score:
                        best_result = iteration_record
                        best_score = score
                        self.logger.info(f"✅ New best score: {score}%")
                    
                    # Check if we hit target
                    if score >= self.target_accuracy:
                        self.logger.info(f"🎉 SUCCESS! Achieved {score}% >= {self.target_accuracy}%")
                        iteration_record['success_reason'] = 'target_achieved'
                        learning_path.append(iteration_record)
                        break
                    
                    # Check if improvement is too small
                    if iteration > 1 and (score - learning_path[-1]['score']) < self.min_improvement:
                        self.logger.info(f"⚠️ Improvement < {self.min_improvement}%, diminishing returns")
                        if iteration >= 5:  # Give up after 5 attempts with small gains
                            iteration_record['success_reason'] = 'diminishing_returns'
                            learning_path.append(iteration_record)
                            break
                    
                    # Diagnose what went wrong
                    self.logger.info(f"🔍 Diagnosing failures...")
                    diagnosis = self.diagnostic_analyzer.analyze(structured_data, validation, pdf_path)
                    
                    iteration_record['diagnosis'] = diagnosis
                    learning_path.append(iteration_record)
                    
                    self.logger.info(f"🧬 Root causes: {diagnosis['root_causes']}")
                    self.logger.info(f"💡 Mutations: {len(diagnosis['mutations'])} recommended")
                    
                    # If no mutations recommended, we can't improve
                    if not diagnosis['mutations']:
                        self.logger.info("⚠️ No mutations available, stopping")
                        break
                    
                    # Mutate strategy for next iteration
                    self.logger.info(f"🧪 Mutating strategy for iteration {iteration + 1}...")
                    current_strategy = self.strategy_mutator.mutate(
                        initial_strategy,
                        diagnosis['mutations'],
                        iteration + 1
                    )
                
                except Exception as e:
                    self.logger.error(f"❌ Iteration {iteration} failed: {e}", exc_info=True)
                    learning_path.append({
                        'iteration': iteration,
                        'error': str(e),
                        'score': 0
                    })
                    # Continue to next iteration with different approach
                    continue
            
            # Step 3: Use best result
            if not best_result:
                return {
                    'success': False,
                    'error': 'All iterations failed',
                    'learning_path': learning_path
                }
            
            # Step 4: Create Excel output
            tabs = self._create_excel_tabs(best_result['structured_data'])
            excel_path = self._write_excel(
                tabs, 
                pdf_path, 
                output_dir, 
                f"adaptive_iter{best_result['iteration']}"
            )
            
            # Step 5: Return comprehensive result
            return {
                'success': True,
                'excel_path': excel_path,
                'accuracy': best_score,
                'method': f"adaptive_iter{best_result['iteration']}",
                'iterations': len(learning_path),
                'target_achieved': best_score >= self.target_accuracy,
                'learning_path': learning_path,
                'best_iteration': best_result['iteration'],
                'validation': best_result['validation'],
                'employees_found': len(best_result['structured_data'].get('employees', [])),
                'earnings_found': len(best_result['structured_data'].get('earnings', [])),
                'taxes_found': len(best_result['structured_data'].get('taxes', [])),
                'deductions_found': len(best_result['structured_data'].get('deductions', []))
            }
        
        except Exception as e:
            self.logger.error(f"❌ Adaptive parsing failed: {e}", exc_info=True)
            return {'success': False, 'error': str(e), 'method': 'adaptive'}
    
    def _get_initial_strategy(self, pdf_path: str):
        """Get the initial strategy to start with."""
        # If we have strategy library, use it
        if self.strategy_library:
            # Get vendor-specific strategies if possible
            if self.vendor_detector:
                vendor_result = self.vendor_detector.detect_vendor(pdf_path)
                strategies = self.strategy_library.get_strategies_for_vendor(vendor_result['vendor'])
                if strategies:
                    return strategies[0]  # Start with first recommended strategy
            
            # Otherwise get default strategy
            all_strategies = self.strategy_library.get_strategies_for_vendor('universal')
            if all_strategies:
                return all_strategies[0]
        
        # Fallback: Create basic hybrid strategy
        from .strategy_library import HybridStrategy
        return HybridStrategy()
    
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
    
    def _write_excel(self, tabs: Dict[str, pd.DataFrame], pdf_path: str, 
                     output_dir: str, method_name: str) -> str:
        """Write Excel file."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = output_dir / f"{Path(pdf_path).stem}_parsed_{method_name}_{timestamp}.xlsx"
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            for tab_name, df in tabs.items():
                df.to_excel(writer, sheet_name=tab_name, index=False)
        
        return str(output_path)
    
    def get_learning_summary(self, result: Dict) -> str:
        """Generate human-readable learning summary."""
        if not result.get('success'):
            return "❌ Parsing failed"
        
        summary = [
            f"🎯 Final Accuracy: {result['accuracy']}%",
            f"🔄 Iterations: {result['iterations']}",
            f"✅ Target Achieved: {result['target_achieved']}",
            "\n📚 Learning Path:"
        ]
        
        for step in result.get('learning_path', []):
            iter_num = step['iteration']
            score = step['score']
            diagnosis = step.get('diagnosis', {})
            root_causes = diagnosis.get('root_causes', [])
            
            summary.append(f"\n  Iteration {iter_num}: {score}%")
            if root_causes:
                summary.append(f"    Issues: {', '.join(root_causes)}")
        
        return '\n'.join(summary)
