"""
Diagnostic Analyzer - Interprets validation failures and recommends strategy mutations
The "brain" that learns from failures
"""

import logging
from typing import Dict, List, Any
import re

logger = logging.getLogger(__name__)


class DiagnosticAnalyzer:
    """
    Analyzes validation results and structured data to identify root causes.
    Returns actionable mutations for strategy adaptation.
    """
    
    def analyze(self, structured_data: Dict, validation_result: Dict, pdf_path: str = None) -> Dict:
        """
        Deep analysis of parsing failure to identify root causes.
        
        Returns:
            {
                'root_causes': ['employee_ids_missing', 'multi_row_structure', ...],
                'mutations': [
                    {'type': 'add_id_pattern', 'params': {...}},
                    {'type': 'enable_grouping', 'params': {...}},
                    ...
                ],
                'confidence': 85  # How confident we are in these mutations
            }
        """
        root_causes = []
        mutations = []
        
        employees = structured_data.get('employees', [])
        earnings = structured_data.get('earnings', [])
        taxes = structured_data.get('taxes', [])
        deductions = structured_data.get('deductions', [])
        
        # ===== DIAGNOSTIC 1: Auto-generated Employee IDs =====
        auto_gen_ids = self._detect_auto_generated_ids(employees)
        if auto_gen_ids['has_fake_ids']:
            root_causes.append('employee_ids_auto_generated')
            mutations.extend(self._get_id_extraction_mutations(auto_gen_ids, earnings, taxes))
        
        # ===== DIAGNOSTIC 2: Multi-Row Structure Not Grouped =====
        multi_row_issue = self._detect_multi_row_structure(employees, earnings, taxes)
        if multi_row_issue['detected']:
            root_causes.append('multi_row_structure_not_grouped')
            mutations.extend(self._get_grouping_mutations(multi_row_issue))
        
        # ===== DIAGNOSTIC 3: Negative Net Pay (Data Assignment Wrong) =====
        negative_net_pay = self._detect_negative_net_pay(employees, earnings, taxes)
        if negative_net_pay['detected']:
            root_causes.append('incorrect_data_assignment')
            mutations.extend(self._get_assignment_mutations(negative_net_pay))
        
        # ===== DIAGNOSTIC 4: Low Data Extraction Rate =====
        extraction_rate = self._analyze_extraction_rate(validation_result)
        if extraction_rate['low_extraction']:
            root_causes.append('insufficient_data_extraction')
            mutations.extend(self._get_extraction_mutations(extraction_rate))
        
        # ===== DIAGNOSTIC 5: Employee Names in Descriptions =====
        names_in_desc = self._detect_names_in_descriptions(earnings, taxes, employees)
        if names_in_desc['detected']:
            root_causes.append('employee_names_embedded_in_descriptions')
            mutations.extend(self._get_name_extraction_mutations(names_in_desc))
        
        # Calculate confidence based on clarity of diagnostics
        confidence = self._calculate_confidence(root_causes, mutations)
        
        return {
            'root_causes': root_causes,
            'mutations': mutations,
            'confidence': confidence,
            'diagnostics': {
                'auto_gen_ids': auto_gen_ids,
                'multi_row_issue': multi_row_issue,
                'negative_net_pay': negative_net_pay,
                'extraction_rate': extraction_rate,
                'names_in_desc': names_in_desc
            }
        }
    
    def _detect_auto_generated_ids(self, employees: List[Dict]) -> Dict:
        """Detect if employee IDs are auto-generated (100000, 100001, etc.)."""
        if not employees:
            return {'has_fake_ids': False, 'fake_count': 0, 'real_count': 0}
        
        fake_ids = []
        real_ids = []
        
        for emp in employees:
            emp_id = str(emp.get('employee_id', ''))
            # Auto-generated pattern: 100000-100999
            if re.match(r'^1000\d{2}$', emp_id):
                fake_ids.append(emp_id)
            else:
                real_ids.append(emp_id)
        
        return {
            'has_fake_ids': len(fake_ids) > 0,
            'fake_count': len(fake_ids),
            'real_count': len(real_ids),
            'fake_percentage': len(fake_ids) / len(employees) * 100,
            'fake_ids': fake_ids[:5],  # Sample
            'real_ids': real_ids[:5]   # Sample
        }
    
    def _detect_multi_row_structure(self, employees: List[Dict], earnings: List[Dict], 
                                    taxes: List[Dict]) -> Dict:
        """Detect if same employee has multiple rows (common pattern)."""
        if not employees or not earnings:
            return {'detected': False}
        
        # Count records per employee
        earnings_per_emp = {}
        for earning in earnings:
            emp_id = earning.get('employee_id', '')
            earnings_per_emp[emp_id] = earnings_per_emp.get(emp_id, 0) + 1
        
        # If ANY employee has > 5 records, likely multi-row structure
        max_records = max(earnings_per_emp.values()) if earnings_per_emp else 0
        avg_records = sum(earnings_per_emp.values()) / len(earnings_per_emp) if earnings_per_emp else 0
        
        # Multi-row detected if: high record count per employee
        detected = max_records > 8 or avg_records > 4
        
        return {
            'detected': detected,
            'max_records_per_employee': max_records,
            'avg_records_per_employee': avg_records,
            'employees_with_many_records': [emp_id for emp_id, count in earnings_per_emp.items() if count > 5]
        }
    
    def _detect_negative_net_pay(self, employees: List[Dict], earnings: List[Dict], 
                                 taxes: List[Dict]) -> Dict:
        """
        Detect if net pay calculations are wrong (data assignment incorrect).
        
        CRITICAL: Net Pay MUST equal: Earnings - Taxes - Deductions
        If this doesn't balance, data is assigned to wrong employees.
        """
        negative_count = 0
        imbalanced_count = 0
        imbalanced_employees = []
        
        for emp in employees:
            emp_id = emp['employee_id']
            emp_earnings = sum(e.get('amount', 0) for e in earnings if e.get('employee_id') == emp_id)
            emp_taxes = sum(t.get('amount', 0) for t in taxes if t.get('employee_id') == emp_id)
            calculated_net = emp_earnings - emp_taxes
            
            # Check if negative (impossible)
            if calculated_net < 0:
                negative_count += 1
                imbalanced_count += 1
                imbalanced_employees.append({
                    'id': emp_id,
                    'name': emp.get('employee_name', ''),
                    'earnings': emp_earnings,
                    'taxes': emp_taxes,
                    'calculated_net': calculated_net,
                    'issue': 'negative_net_pay'
                })
            
            # Check if taxes > 50% of earnings (highly suspicious)
            elif emp_earnings > 0 and emp_taxes > (emp_earnings * 0.5):
                imbalanced_count += 1
                imbalanced_employees.append({
                    'id': emp_id,
                    'name': emp.get('employee_name', ''),
                    'earnings': emp_earnings,
                    'taxes': emp_taxes,
                    'tax_percentage': (emp_taxes / emp_earnings * 100),
                    'issue': 'excessive_tax_rate'
                })
        
        negative_percentage = negative_count / len(employees) * 100 if employees else 0
        imbalanced_percentage = imbalanced_count / len(employees) * 100 if employees else 0
        
        # CRITICAL: If more than 20% have imbalanced net pay, data assignment is WRONG
        detected = imbalanced_percentage > 20
        
        return {
            'detected': detected,
            'negative_count': negative_count,
            'imbalanced_count': imbalanced_count,
            'total_employees': len(employees),
            'negative_percentage': negative_percentage,
            'imbalanced_percentage': imbalanced_percentage,
            'imbalanced_employees': imbalanced_employees[:5],  # Sample
            'severity': 'critical' if imbalanced_percentage > 50 else 'high' if imbalanced_percentage > 20 else 'low'
        }
    
    def _analyze_extraction_rate(self, validation_result: Dict) -> Dict:
        """Analyze if we're extracting enough data."""
        details = validation_result.get('details', {})
        comp = details.get('completeness', {})
        
        avg_earnings = comp.get('avg_earnings', 0)
        avg_taxes = comp.get('avg_taxes', 0)
        avg_deductions = comp.get('avg_deductions', 0)
        
        low_extraction = avg_earnings < 3 or avg_taxes < 5
        
        return {
            'low_extraction': low_extraction,
            'avg_earnings': avg_earnings,
            'avg_taxes': avg_taxes,
            'avg_deductions': avg_deductions,
            'expected_earnings': 5,
            'expected_taxes': 8
        }
    
    def _detect_names_in_descriptions(self, earnings: List[Dict], taxes: List[Dict], 
                                     employees: List[Dict]) -> Dict:
        """Detect if employee names appear in description fields."""
        names_found_in_desc = []
        
        # Get known employee names
        known_names = [emp.get('employee_name', '') for emp in employees]
        
        # Check earnings descriptions
        for earning in earnings[:20]:  # Sample
            desc = earning.get('description', '')
            # Look for "LASTNAME, FIRSTNAME" pattern
            if re.search(r'[A-Z]{2,},\s+[A-Z\s]+', desc):
                names_found_in_desc.append(desc)
        
        return {
            'detected': len(names_found_in_desc) > 0,
            'sample_descriptions': names_found_in_desc[:5]
        }
    
    def _get_id_extraction_mutations(self, auto_gen_info: Dict, earnings: List[Dict], 
                                     taxes: List[Dict]) -> List[Dict]:
        """Generate mutations to fix ID extraction."""
        mutations = []
        
        if auto_gen_info['fake_percentage'] > 50:
            # Critical: Most IDs are fake
            mutations.append({
                'type': 'enhance_id_extraction',
                'priority': 'critical',
                'params': {
                    'action': 'look_for_real_ids',
                    'locations': ['adjacent_to_names', 'section_headers', 'table_first_column'],
                    'patterns': [r'\b\d{4,6}\b']  # 4-6 digit numbers
                }
            })
            
            # Try to find IDs in earnings/tax descriptions
            mutations.append({
                'type': 'extract_ids_from_context',
                'priority': 'high',
                'params': {
                    'action': 'scan_descriptions',
                    'sources': ['earnings', 'taxes']
                }
            })
        
        return mutations
    
    def _get_grouping_mutations(self, multi_row_info: Dict) -> List[Dict]:
        """Generate mutations to fix multi-row grouping."""
        mutations = []
        
        if multi_row_info['avg_records_per_employee'] > 4:
            mutations.append({
                'type': 'enable_row_grouping',
                'priority': 'critical',
                'params': {
                    'action': 'group_consecutive_rows',
                    'group_by': 'employee_name_pattern',
                    'until': 'next_employee_marker'
                }
            })
        
        return mutations
    
    def _get_assignment_mutations(self, negative_pay_info: Dict) -> List[Dict]:
        """Generate mutations to fix data assignment based on net pay imbalance."""
        mutations = []
        
        severity = negative_pay_info.get('severity', 'low')
        imbalanced_percentage = negative_pay_info.get('imbalanced_percentage', 0)
        
        if imbalanced_percentage > 20:
            # CRITICAL: Data is assigned to wrong employees
            mutations.append({
                'type': 'fix_data_assignment',
                'priority': 'critical',
                'params': {
                    'action': 'reassign_based_on_net_pay_balance',
                    'method': 'context_matching',
                    'severity': severity,
                    'imbalanced_percentage': imbalanced_percentage,
                    'reason': f'{imbalanced_percentage:.0f}% of employees have imbalanced net pay (Earnings - Taxes - Deductions != Net Pay)'
                }
            })
            
            # Add mutation to re-extract with stricter employee grouping
            mutations.append({
                'type': 'enable_row_grouping',
                'priority': 'critical',
                'params': {
                    'action': 'strict_employee_section_grouping',
                    'method': 'section_based',
                    'reason': 'Net pay imbalance suggests multi-row data not grouped by employee correctly'
                }
            })
        
        return mutations
    
    def _get_extraction_mutations(self, extraction_info: Dict) -> List[Dict]:
        """Generate mutations to extract more data."""
        mutations = []
        
        if extraction_info['avg_earnings'] < 3:
            mutations.append({
                'type': 'broaden_earning_patterns',
                'priority': 'high',
                'params': {
                    'action': 'add_generic_amount_extraction',
                    'keywords': ['pay', 'wage', 'compensation']
                }
            })
        
        if extraction_info['avg_taxes'] < 5:
            mutations.append({
                'type': 'broaden_tax_patterns',
                'priority': 'high',
                'params': {
                    'action': 'add_generic_tax_extraction',
                    'keywords': ['deduct', 'withhold', 'contribution']
                }
            })
        
        return mutations
    
    def _get_name_extraction_mutations(self, names_info: Dict) -> List[Dict]:
        """Generate mutations to better extract names from descriptions."""
        mutations = []
        
        if names_info['detected']:
            mutations.append({
                'type': 'extract_names_from_descriptions',
                'priority': 'high',
                'params': {
                    'action': 'scan_for_name_patterns',
                    'patterns': [
                        r'([A-Z]{2,},\s+[A-Z\s]+)',  # LASTNAME, FIRSTNAME
                        r'([A-Z][a-z]+\s+[A-Z][a-z]+)'  # FirstName LastName
                    ]
                }
            })
        
        return mutations
    
    def _calculate_confidence(self, root_causes: List[str], mutations: List[Dict]) -> int:
        """Calculate confidence in our diagnosis (0-100)."""
        if not root_causes:
            return 0
        
        # Base confidence on number and clarity of root causes
        base_confidence = min(len(root_causes) * 20, 60)
        
        # Add confidence for actionable mutations
        mutation_confidence = min(len(mutations) * 10, 40)
        
        return min(base_confidence + mutation_confidence, 100)
