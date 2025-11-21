"""
Strategy Mutator - Applies diagnostic mutations to create adapted strategies
The "evolution" engine that creates new strategy variants
"""

import logging
import re
from typing import Dict, List, Any
from copy import deepcopy

logger = logging.getLogger(__name__)


class StrategyMutator:
    """
    Takes a strategy and mutation recommendations,
    creates a NEW adapted strategy variant.
    """
    
    def mutate(self, base_strategy, mutations: List[Dict], iteration: int) -> Any:
        """
        Create a new strategy variant by applying mutations.
        
        Args:
            base_strategy: The strategy to mutate
            mutations: List of mutation instructions from DiagnosticAnalyzer
            iteration: Current iteration number (affects mutation aggressiveness)
        
        Returns:
            New strategy instance with mutations applied
        """
        logger.info(f"Mutating strategy (iteration {iteration}) with {len(mutations)} mutations")
        
        # Sort mutations by priority
        sorted_mutations = sorted(mutations, key=lambda m: self._priority_score(m), reverse=True)
        
        # Create adapted strategy
        adapted_strategy = AdaptedStrategy(base_strategy, iteration)
        
        # Apply mutations in priority order
        for mutation in sorted_mutations:
            mutation_type = mutation['type']
            params = mutation.get('params', {})
            
            if mutation_type == 'enhance_id_extraction':
                adapted_strategy.enhance_id_extraction(params)
            
            elif mutation_type == 'extract_ids_from_context':
                adapted_strategy.extract_ids_from_context(params)
            
            elif mutation_type == 'switch_to_text_extraction':
                adapted_strategy.switch_to_text_extraction(params)
            
            elif mutation_type == 'enable_row_grouping':
                adapted_strategy.enable_row_grouping(params)
            
            elif mutation_type == 'fix_data_assignment':
                adapted_strategy.fix_data_assignment(params)
            
            elif mutation_type == 'broaden_earning_patterns':
                adapted_strategy.broaden_earning_patterns(params)
            
            elif mutation_type == 'broaden_tax_patterns':
                adapted_strategy.broaden_tax_patterns(params)
            
            elif mutation_type == 'extract_names_from_descriptions':
                adapted_strategy.extract_names_from_descriptions(params)
            
            else:
                logger.warning(f"Unknown mutation type: {mutation_type}")
        
        return adapted_strategy
    
    def _priority_score(self, mutation: Dict) -> int:
        """Convert priority to numeric score."""
        priority_map = {
            'critical': 100,
            'high': 75,
            'medium': 50,
            'low': 25
        }
        return priority_map.get(mutation.get('priority', 'medium'), 50)


class AdaptedStrategy:
    """
    A dynamically adapted extraction strategy that wraps a base strategy
    and applies behavioral mutations.
    """
    
    def __init__(self, base_strategy, iteration: int):
        self.base_strategy = base_strategy
        self.iteration = iteration
        self.name = f"adapted_{base_strategy.name}_iter{iteration}"
        
        # Mutation flags
        self.enhanced_id_extraction = False
        self.extract_ids_from_context_enabled = False
        self.use_text_based_strategy = False
        self.row_grouping_enabled = False
        self.data_assignment_fixed = False
        self.broader_patterns = False
        self.name_from_descriptions = False
        
        # Configuration for mutations
        self.id_extraction_config = {}
        self.context_extraction_config = {}
        self.text_strategy_config = {}
        self.grouping_config = {}
        self.assignment_config = {}
        self.pattern_config = {}
        self.name_extraction_config = {}
    
    def enhance_id_extraction(self, params: Dict):
        """Enable enhanced employee ID extraction."""
        logger.info("Mutation: Enhancing ID extraction")
        self.enhanced_id_extraction = True
        self.id_extraction_config = params
    
    def extract_ids_from_context(self, params: Dict):
        """Enable extracting IDs from earnings/tax context."""
        logger.info("Mutation: Extracting IDs from context")
        self.extract_ids_from_context_enabled = True
        self.context_extraction_config = params
    
    def switch_to_text_extraction(self, params: Dict):
        """Switch from table-based to text-based extraction."""
        logger.info("Mutation: Switching to text-based extraction")
        self.use_text_based_strategy = True
        self.text_strategy_config = params
    
    def enable_row_grouping(self, params: Dict):
        """Enable grouping of multi-row data per employee."""
        logger.info("Mutation: Enabling row grouping")
        self.row_grouping_enabled = True
        self.grouping_config = params
    
    def fix_data_assignment(self, params: Dict):
        """Fix how data is assigned to employees."""
        logger.info("Mutation: Fixing data assignment")
        self.data_assignment_fixed = True
        self.assignment_config = params
    
    def broaden_earning_patterns(self, params: Dict):
        """Broaden earning extraction patterns."""
        logger.info("Mutation: Broadening earning patterns")
        self.broader_patterns = True
        self.pattern_config['earnings'] = params
    
    def broaden_tax_patterns(self, params: Dict):
        """Broaden tax extraction patterns."""
        logger.info("Mutation: Broadening tax patterns")
        self.broader_patterns = True
        self.pattern_config['taxes'] = params
    
    def extract_names_from_descriptions(self, params: Dict):
        """Extract employee names from description fields."""
        logger.info("Mutation: Extracting names from descriptions")
        self.name_from_descriptions = True
        self.name_extraction_config = params
    
    def can_handle(self, pdf_path: str, vendor: str = None) -> bool:
        """Delegate to base strategy."""
        return self.base_strategy.can_handle(pdf_path, vendor)
    
    def extract(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract data using base strategy + applied mutations.
        """
        logger.info(f"Extracting with adapted strategy (iteration {self.iteration})")
        
        # Step 1: Check if we should switch strategies entirely
        if self.use_text_based_strategy:
            logger.info("⚡ SWITCHING TO TEXT-BASED STRATEGY")
            # Import and use TextBasedStrategy instead of TableBased
            try:
                # Try to get TextBasedStrategy from strategy_library
                from . import strategy_library
                text_strategy = strategy_library.TextBasedStrategy()
                base_result = text_strategy.extract(pdf_path)
                logger.info(f"Text-based extraction: {len(base_result.get('employees', []))} employees, {len(base_result.get('earnings', []))} earnings")
            except Exception as e:
                logger.error(f"Failed to switch to text strategy: {e}")
                # Fallback to base strategy
                base_result = self.base_strategy.extract(pdf_path)
        else:
            # Step 1: Get base extraction
            base_result = self.base_strategy.extract(pdf_path)
        
        # Step 2: Apply post-processing mutations
        adapted_result = self._apply_mutations(base_result, pdf_path)
        
        return adapted_result
    
    def _apply_mutations(self, base_result: Dict, pdf_path: str) -> Dict:
        """Apply all enabled mutations to base extraction result."""
        result = deepcopy(base_result)
        
        employees = result.get('employees', [])
        earnings = result.get('earnings', [])
        taxes = result.get('taxes', [])
        deductions = result.get('deductions', [])
        
        # MUTATION 1: Extract names from descriptions
        if self.name_from_descriptions:
            employees, earnings, taxes = self._extract_names_from_descriptions_logic(
                employees, earnings, taxes
            )
        
        # MUTATION 2: Enhanced ID extraction
        if self.enhanced_id_extraction:
            employees = self._enhance_id_extraction_logic(employees, earnings, taxes)
        
        # MUTATION 3: Extract IDs from context
        if self.extract_ids_from_context_enabled:
            employees, earnings, taxes = self._extract_ids_from_context_logic(
                employees, earnings, taxes, pdf_path
            )
        
        # MUTATION 4: Row grouping
        if self.row_grouping_enabled:
            earnings, taxes, deductions = self._apply_row_grouping_logic(
                employees, earnings, taxes, deductions
            )
        
        # MUTATION 5: Fix data assignment
        if self.data_assignment_fixed:
            earnings, taxes, deductions = self._fix_assignment_logic(
                employees, earnings, taxes, deductions
            )
        
        # MUTATION 6: Broader patterns
        if self.broader_patterns:
            earnings, taxes = self._apply_broader_patterns_logic(
                earnings, taxes, pdf_path
            )
        
        result['employees'] = employees
        result['earnings'] = earnings
        result['taxes'] = taxes
        result['deductions'] = deductions
        
        return result
    
    def _extract_names_from_descriptions_logic(self, employees: List[Dict], 
                                               earnings: List[Dict], 
                                               taxes: List[Dict]) -> tuple:
        """
        Extract employee names from earnings/tax descriptions.
        
        Pattern: "LASTNAME, FIRSTNAME Regular" or similar
        This is KEY for Paycom-style registers where employee names appear in descriptions.
        """
        logger.info("Applying mutation: Extract names from descriptions")
        
        # Build comprehensive map: name -> real_id (if we can find it)
        employee_map = {}  # {name: {'id': xxx, 'records': []}}
        
        # PASS 1: Scan ALL records to find employee markers and their associated data
        current_employee = None
        
        for i, earning in enumerate(earnings):
            desc = earning.get('description', '')
            
            # Pattern 1: "LASTNAME, FIRSTNAME Regular" - Primary employee marker
            name_match = re.search(r'([A-Z]{2,},\s+[A-Z][A-Z\s]+)\s+(Regular|Hourly|Salary)', desc, re.IGNORECASE)
            
            if name_match:
                # This is an employee header row!
                raw_name = name_match.group(1).strip()
                
                # Clean up name
                name = raw_name.strip()
                
                # Look for a real ID nearby (in same or adjacent rows)
                real_id = self._find_real_id_near_name(earnings, i)
                
                if name not in employee_map:
                    employee_map[name] = {
                        'id': real_id if real_id else None,
                        'records': [],
                        'first_seen': i
                    }
                
                current_employee = name
                employee_map[name]['records'].append(i)
            
            # Pattern 2: Continuation row (belongs to current employee)
            elif current_employee:
                # This row belongs to the current employee
                employee_map[current_employee]['records'].append(i)
                
                # Check if this is a new employee marker (next employee starts)
                if any(keyword in desc for keyword in ['Subtotals', 'Total for', 'Tax Profile: ']):
                    # Marker that might indicate transition - but keep current employee
                    pass
        
        # PASS 2: Assign IDs (real or generated) to each employee
        next_generated_id = 1  # Start from 1, not 100000
        final_employees = []
        
        for name, info in employee_map.items():
            if info['id']:
                # Use real ID found
                emp_id = info['id']
            else:
                # Generate sequential ID
                emp_id = next_generated_id
                next_generated_id += 1
            
            final_employees.append({
                'employee_id': emp_id,
                'employee_name': name,
                'department': ''
            })
            
            # Update all earnings records for this employee
            for record_idx in info['records']:
                if record_idx < len(earnings):
                    earnings[record_idx]['employee_id'] = emp_id
                    earnings[record_idx]['employee_name'] = name
        
        # PASS 3: Handle any earnings not assigned (assign to UNKNOWN)
        for earning in earnings:
            if not earning.get('employee_id'):
                earning['employee_id'] = 9999
                earning['employee_name'] = 'UNKNOWN'
        
        # Add UNKNOWN employee if needed
        if any(e.get('employee_id') == 9999 for e in earnings):
            final_employees.append({
                'employee_id': 9999,
                'employee_name': 'UNKNOWN',
                'department': ''
            })
        
        logger.info(f"Found {len(final_employees)} employees from descriptions")
        logger.info(f"Sample: {[e['employee_name'] for e in final_employees[:5]]}")
        
        return final_employees, earnings, taxes
    
    def _find_real_id_near_name(self, earnings: List[Dict], name_index: int, window: int = 5) -> Any:
        """
        Look for a real employee ID near where we found the name.
        Scans nearby records for numeric IDs that aren't years/round numbers.
        """
        # Check records around this position
        start = max(0, name_index - window)
        end = min(len(earnings), name_index + window)
        
        for i in range(start, end):
            desc = earnings[i].get('description', '')
            # Look for 4-6 digit numbers
            numbers = re.findall(r'\b(\d{4,6})\b', desc)
            
            for num in numbers:
                # Filter out years (2024, 2025, etc.)
                if num.startswith('20') or num.startswith('19'):
                    continue
                # Filter out round numbers (1000, 2000, etc.)
                if num.endswith('000') or num.endswith('00'):
                    continue
                
                # This looks like a real employee ID!
                return int(num)
        
        return None
    
    def _enhance_id_extraction_logic(self, employees: List[Dict], 
                                     earnings: List[Dict], 
                                     taxes: List[Dict]) -> List[Dict]:
        """Look for real employee IDs in multiple locations."""
        logger.info("Applying mutation: Enhanced ID extraction")
        
        # Scan earnings/taxes for numeric IDs that aren't auto-generated
        found_ids = set()
        
        for earning in earnings:
            desc = earning.get('description', '')
            # Look for 4-7 digit numbers
            numbers = re.findall(r'\b(\d{4,7})\b', desc)
            for num in numbers:
                # Filter out years and other non-ID numbers
                if not num.startswith('20') and not num.endswith('00'):
                    found_ids.add(num)
        
        # If we found real IDs, try to match them with employees
        if found_ids:
            logger.info(f"Found {len(found_ids)} potential real IDs: {list(found_ids)[:5]}")
        
        return employees
    
    def _extract_ids_from_context_logic(self, employees: List[Dict], 
                                        earnings: List[Dict], 
                                        taxes: List[Dict], 
                                        pdf_path: str) -> tuple:
        """Extract employee IDs from surrounding context."""
        logger.info("Applying mutation: Extract IDs from context")
        
        # This would require re-parsing PDF with focus on ID locations
        # For now, scan existing data for ID patterns
        
        return employees, earnings, taxes
    
    def _apply_row_grouping_logic(self, employees: List[Dict], 
                                  earnings: List[Dict], 
                                  taxes: List[Dict], 
                                  deductions: List[Dict]) -> tuple:
        """Group multiple rows belonging to same employee."""
        logger.info("Applying mutation: Row grouping")
        
        # Group earnings by employee (already should be grouped if IDs are correct)
        # This mutation helps when we have correct names but data is fragmented
        
        return earnings, taxes, deductions
    
    def _fix_assignment_logic(self, employees: List[Dict], 
                              earnings: List[Dict], 
                              taxes: List[Dict], 
                              deductions: List[Dict]) -> tuple:
        """Fix incorrect data assignment using proximity/context."""
        logger.info("Applying mutation: Fix data assignment")
        
        # Strategy: If employee has negative net pay, reassign data
        # based on name matching in descriptions
        
        return earnings, taxes, deductions
    
    def _apply_broader_patterns_logic(self, earnings: List[Dict], 
                                      taxes: List[Dict], 
                                      pdf_path: str) -> tuple:
        """Apply broader extraction patterns to get more data."""
        logger.info("Applying mutation: Broader patterns")
        
        # This would require re-parsing with relaxed keyword matching
        # For now, return as-is
        
        return earnings, taxes
