"""
Validation Engine - Scores parsing quality and identifies issues
"""

import re
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class ValidationEngine:
    """Validates parsed data quality and identifies issues."""
    
    def validate(self, structured_data: Dict, pdf_path: str = None) -> Dict:
        """
        Validate parsed data and return quality score + issues.
        
        Returns:
            {
                'score': 85,  # 0-100
                'passed': True,  # score >= 90
                'issues': ['Missing employee names', ...],
                'details': {...}
            }
        """
        score = 0
        max_score = 100
        issues = []
        details = {}
        
        employees = structured_data.get('employees', [])
        earnings = structured_data.get('earnings', [])
        taxes = structured_data.get('taxes', [])
        deductions = structured_data.get('deductions', [])
        
        # ===== EMPLOYEE VALIDATION (30 points) =====
        employee_score = self._validate_employees(employees)
        score += employee_score['score']
        issues.extend(employee_score['issues'])
        details['employees'] = employee_score
        
        # ===== DATA COMPLETENESS (30 points) =====
        completeness_score = self._validate_completeness(employees, earnings, taxes, deductions)
        score += completeness_score['score']
        issues.extend(completeness_score['issues'])
        details['completeness'] = completeness_score
        
        # ===== DATA QUALITY (20 points) =====
        quality_score = self._validate_data_quality(earnings, taxes, deductions)
        score += quality_score['score']
        issues.extend(quality_score['issues'])
        details['quality'] = quality_score
        
        # ===== DATA SEPARATION (20 points) =====
        separation_score = self._validate_separation(earnings, taxes, deductions)
        score += separation_score['score']
        issues.extend(separation_score['issues'])
        details['separation'] = separation_score
        
        return {
            'score': min(score, max_score),
            'passed': score >= 90,
            'issues': issues,
            'details': details,
            'employees_found': len(employees),
            'earnings_found': len(earnings),
            'taxes_found': len(taxes),
            'deductions_found': len(deductions)
        }
    
    def _validate_employees(self, employees: List[Dict]) -> Dict:
        """Validate employee data (30 points max)."""
        issues = []
        score = 0
        
        if not employees:
            issues.append("No employees found")
            return {'score': 0, 'issues': issues}
        
        # Check for at least 1 employee (10 points)
        if len(employees) >= 1:
            score += 10
        
        # Check employee names quality (10 points)
        valid_names = 0
        for emp in employees:
            name = emp.get('employee_name', '')
            # Valid name: FirstName LastName (both capitalized, no weird chars)
            if re.match(r'^[A-Z][a-z]+\s+[A-Z][a-z]+$', name):
                valid_names += 1
            else:
                issues.append(f"Invalid employee name: '{name}'")
        
        if valid_names == len(employees):
            score += 10
        elif valid_names > 0:
            score += 5
        
        # Check employee IDs (10 points)
        valid_ids = 0
        for emp in employees:
            emp_id = str(emp.get('employee_id', ''))
            if emp_id and emp_id.isdigit() and len(emp_id) >= 4:
                valid_ids += 1
            else:
                issues.append(f"Invalid employee ID: '{emp_id}'")
        
        if valid_ids == len(employees):
            score += 10
        elif valid_ids > 0:
            score += 5
        
        return {'score': score, 'issues': issues, 'valid_names': valid_names, 'valid_ids': valid_ids}
    
    def _validate_completeness(self, employees: List[Dict], earnings: List[Dict], 
                               taxes: List[Dict], deductions: List[Dict]) -> Dict:
        """Validate data completeness (30 points max)."""
        issues = []
        score = 0
        
        if not employees:
            issues.append("No employees to validate completeness")
            return {'score': 0, 'issues': issues}
        
        emp_count = len(employees)
        
        # Earnings per employee (10 points)
        avg_earnings = len(earnings) / emp_count if emp_count > 0 else 0
        if avg_earnings >= 5:
            score += 10
        elif avg_earnings >= 3:
            score += 7
        elif avg_earnings >= 1:
            score += 3
        else:
            issues.append(f"Low earnings count: {avg_earnings:.1f} per employee (expect 5+)")
        
        # Taxes per employee (10 points)
        avg_taxes = len(taxes) / emp_count if emp_count > 0 else 0
        if avg_taxes >= 8:
            score += 10
        elif avg_taxes >= 5:
            score += 7
        elif avg_taxes >= 2:
            score += 3
        else:
            issues.append(f"Low tax count: {avg_taxes:.1f} per employee (expect 8+)")
        
        # Deductions per employee (10 points)
        avg_deductions = len(deductions) / emp_count if emp_count > 0 else 0
        if avg_deductions >= 2:
            score += 10
        elif avg_deductions >= 1:
            score += 5
        else:
            issues.append(f"Low deduction count: {avg_deductions:.1f} per employee (expect 2+)")
        
        return {
            'score': score,
            'issues': issues,
            'avg_earnings': avg_earnings,
            'avg_taxes': avg_taxes,
            'avg_deductions': avg_deductions
        }
    
    def _validate_data_quality(self, earnings: List[Dict], taxes: List[Dict], 
                               deductions: List[Dict]) -> Dict:
        """Validate data quality - realistic amounts, no zeros (20 points max)."""
        issues = []
        score = 20  # Start at full, subtract for issues
        
        # Check earnings amounts
        if earnings:
            zero_earnings = sum(1 for e in earnings if e.get('amount', 0) == 0)
            unrealistic_earnings = sum(1 for e in earnings if e.get('amount', 0) > 50000)
            
            if zero_earnings > len(earnings) * 0.3:
                issues.append(f"{zero_earnings}/{len(earnings)} earnings have $0 amount")
                score -= 5
            
            if unrealistic_earnings > 0:
                issues.append(f"{unrealistic_earnings} earnings have unrealistic amounts (>$50k)")
                score -= 3
        
        # Check tax amounts
        if taxes:
            zero_taxes = sum(1 for t in taxes if t.get('amount', 0) == 0)
            unrealistic_taxes = sum(1 for t in taxes if t.get('amount', 0) > 10000)
            
            if zero_taxes > len(taxes) * 0.2:
                issues.append(f"{zero_taxes}/{len(taxes)} taxes have $0 amount")
                score -= 5
            
            if unrealistic_taxes > 0:
                issues.append(f"{unrealistic_taxes} taxes have unrealistic amounts (>$10k)")
                score -= 3
        
        # Check deduction amounts
        if deductions:
            zero_deductions = sum(1 for d in deductions if d.get('amount', 0) == 0)
            unrealistic_deductions = sum(1 for d in deductions if d.get('amount', 0) > 5000)
            
            if zero_deductions > len(deductions) * 0.1:
                issues.append(f"{zero_deductions}/{len(deductions)} deductions have $0 amount")
                score -= 4
            
            if unrealistic_deductions > 0:
                issues.append(f"{unrealistic_deductions} deductions have unrealistic amounts (>$5k)")
                score -= 3
        
        return {'score': max(score, 0), 'issues': issues}
    
    def _validate_separation(self, earnings: List[Dict], taxes: List[Dict], 
                            deductions: List[Dict]) -> Dict:
        """Validate data separation - no contamination between categories (20 points max)."""
        issues = []
        score = 20
        
        # Earning keywords that shouldn't appear in other categories
        earning_keywords = ['regular', 'hourly', 'salary', 'overtime', 'vacation', 'bonus', 'holiday']
        
        # Tax keywords
        tax_keywords = ['fed', 'fica', 'medicare', 'w/h', 'tax', 'ss', 'state']
        
        # Deduction keywords
        deduction_keywords = ['medical', 'dental', '401k', 'insurance', 'vision', 'life']
        
        # Check taxes for earning contamination
        for tax in taxes:
            desc = tax.get('description', '').lower()
            for kw in earning_keywords:
                if kw in desc:
                    issues.append(f"Earning keyword '{kw}' found in tax: {desc}")
                    score -= 3
                    break
        
        # Check deductions for earning/tax contamination
        for ded in deductions:
            desc = ded.get('description', '').lower()
            for kw in earning_keywords:
                if kw in desc:
                    issues.append(f"Earning keyword '{kw}' found in deduction: {desc}")
                    score -= 3
                    break
            for kw in tax_keywords:
                if kw in desc:
                    issues.append(f"Tax keyword '{kw}' found in deduction: {desc}")
                    score -= 3
                    break
        
        # Check earnings for tax/deduction contamination
        for earn in earnings:
            desc = earn.get('description', '').lower()
            for kw in tax_keywords:
                if kw in desc:
                    issues.append(f"Tax keyword '{kw}' found in earning: {desc}")
                    score -= 3
                    break
        
        return {'score': max(score, 0), 'issues': issues}
    
    def get_recommendations(self, validation_result: Dict) -> List[str]:
        """Get recommendations for improving parsing based on validation results."""
        recommendations = []
        
        if validation_result['score'] >= 90:
            recommendations.append("✅ Data quality is excellent - no changes needed")
            return recommendations
        
        details = validation_result.get('details', {})
        
        # Employee issues
        emp_details = details.get('employees', {})
        if emp_details.get('valid_names', 0) < emp_details.get('score', 0) / 10:
            recommendations.append("🔧 Try different name extraction pattern")
        
        # Completeness issues
        comp_details = details.get('completeness', {})
        if comp_details.get('avg_earnings', 0) < 3:
            recommendations.append("🔧 Earnings extraction too strict - try broader patterns")
        if comp_details.get('avg_taxes', 0) < 5:
            recommendations.append("🔧 Tax extraction missing data - try different column/method")
        if comp_details.get('avg_deductions', 0) < 1:
            recommendations.append("🔧 Deduction extraction failing - check column location")
        
        # Separation issues
        sep_score = details.get('separation', {}).get('score', 20)
        if sep_score < 15:
            recommendations.append("🔧 Category contamination detected - improve keyword filtering")
        
        # General recommendations
        if validation_result['score'] < 70:
            recommendations.append("🔄 Try different extraction strategy (table vs text vs OCR)")
        
        return recommendations
