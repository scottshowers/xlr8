"""
Validation Engine
==================
Cross-checks extraction results to ensure accuracy.
Based on pay register business rules.

Deploy to: backend/extraction/validation_engine.py
"""

import logging
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of validation checks"""
    passed: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    checks_run: int = 0
    checks_passed: int = 0
    confidence_adjustment: float = 1.0  # Multiplier for overall confidence


class ValidationEngine:
    """
    Validates extracted pay register data.
    
    Core validation rules (from user requirements):
    1. Earnings amounts = Gross
    2. Gross - Taxes - Deductions = Net
    3. Every employee must have: Name, Employee ID, Tax setup indicator
    4. Employees typically have department/business unit assignment
    """
    
    # Currency tolerance for comparisons
    CURRENCY_TOLERANCE = Decimal('0.02')  # 2 cents tolerance
    
    # Required fields for employee
    REQUIRED_EMPLOYEE_FIELDS = [
        'employee_name',   # Could be 'name', 'employee_name', 'full_name'
        'employee_id',     # Could be 'id', 'emp_id', 'employee_id', 'ee_id'
    ]
    
    # At least one of these tax indicators should be present
    TAX_INDICATOR_FIELDS = [
        'tax_status',      # "MD/MD/MD" style
        'fed_status',
        'state_status',
        'filing_status',
        'w4_status',
    ]
    
    def validate_document(self, sections: Dict[str, Any]) -> ValidationResult:
        """
        Run all validation checks on extracted document.
        """
        result = ValidationResult(passed=True)
        
        # Track what we're checking
        checks = [
            ('employee_required_fields', self._check_employee_required_fields),
            ('earnings_gross_match', self._check_earnings_gross_match),
            ('math_check', self._check_gross_minus_taxes_deductions),
            ('tax_indicators', self._check_tax_indicators),
            ('data_consistency', self._check_data_consistency),
            ('value_ranges', self._check_value_ranges),
        ]
        
        for check_name, check_func in checks:
            result.checks_run += 1
            try:
                passed, errors, warnings = check_func(sections)
                if passed:
                    result.checks_passed += 1
                else:
                    result.errors.extend([f"[{check_name}] {e}" for e in errors])
                result.warnings.extend([f"[{check_name}] {w}" for w in warnings])
            except Exception as e:
                logger.warning(f"Validation check {check_name} failed: {e}")
                result.warnings.append(f"[{check_name}] Check could not complete: {str(e)}")
        
        # Determine overall pass/fail
        critical_errors = [e for e in result.errors if not e.startswith('[warning]')]
        result.passed = len(critical_errors) == 0
        
        # Adjust confidence based on validation results
        if result.checks_run > 0:
            pass_rate = result.checks_passed / result.checks_run
            result.confidence_adjustment = 0.5 + (0.5 * pass_rate)  # 50%-100% based on pass rate
        
        return result
    
    def _check_employee_required_fields(self, sections: Dict) -> tuple:
        """Check that all employees have required fields"""
        errors = []
        warnings = []
        
        employee_section = sections.get('employee_info')
        if not employee_section:
            return True, [], ["No employee_info section found"]
        
        data = employee_section.data if hasattr(employee_section, 'data') else employee_section.get('data', [])
        headers = employee_section.headers if hasattr(employee_section, 'headers') else employee_section.get('headers', [])
        
        if not data:
            return True, [], ["Employee section has no data"]
        
        # Normalize headers for matching
        normalized_headers = [self._normalize_field_name(h) for h in headers]
        
        # Check for name field
        name_found = any(self._is_name_field(h) for h in normalized_headers)
        if not name_found:
            errors.append("No employee name field detected")
        
        # Check for ID field
        id_found = any(self._is_id_field(h) for h in normalized_headers)
        if not id_found:
            errors.append("No employee ID field detected")
        
        # Check for empty required values in data
        name_idx = next((i for i, h in enumerate(normalized_headers) if self._is_name_field(h)), None)
        id_idx = next((i for i, h in enumerate(normalized_headers) if self._is_id_field(h)), None)
        
        empty_names = 0
        empty_ids = 0
        
        for row in data:
            if isinstance(row, dict):
                values = list(row.values())
            else:
                values = row
            
            if name_idx is not None and name_idx < len(values):
                if not values[name_idx] or str(values[name_idx]).strip() == '':
                    empty_names += 1
            
            if id_idx is not None and id_idx < len(values):
                if not values[id_idx] or str(values[id_idx]).strip() == '':
                    empty_ids += 1
        
        if empty_names > 0:
            errors.append(f"{empty_names} employees missing name")
        if empty_ids > 0:
            errors.append(f"{empty_ids} employees missing ID")
        
        return len(errors) == 0, errors, warnings
    
    def _check_tax_indicators(self, sections: Dict) -> tuple:
        """Check that employees have tax setup indicators"""
        errors = []
        warnings = []
        
        employee_section = sections.get('employee_info')
        if not employee_section:
            return True, [], ["No employee_info section to check tax indicators"]
        
        headers = employee_section.headers if hasattr(employee_section, 'headers') else employee_section.get('headers', [])
        normalized_headers = [self._normalize_field_name(h) for h in headers]
        
        # Look for tax indicator fields
        tax_field_found = any(
            any(indicator in h for indicator in ['tax', 'status', 'filing', 'fed', 'state', 'local'])
            for h in normalized_headers
        )
        
        if not tax_field_found:
            # Also check taxes section for employee-level tax data
            taxes_section = sections.get('taxes')
            if taxes_section:
                tax_data = taxes_section.data if hasattr(taxes_section, 'data') else taxes_section.get('data', [])
                if tax_data:
                    tax_field_found = True  # Tax section exists with data
        
        if not tax_field_found:
            warnings.append("No tax status/filing indicator found (expected Fed/State/Local like 'MD/MD/MD')")
        
        return True, [], warnings  # This is a warning, not an error
    
    def _check_earnings_gross_match(self, sections: Dict) -> tuple:
        """Check that sum of earnings equals gross"""
        errors = []
        warnings = []
        
        earnings_section = sections.get('earnings')
        pay_section = sections.get('pay_totals')
        
        if not earnings_section or not pay_section:
            return True, [], ["Cannot verify earnings/gross match - missing sections"]
        
        earnings_data = earnings_section.data if hasattr(earnings_section, 'data') else earnings_section.get('data', [])
        pay_data = pay_section.data if hasattr(pay_section, 'data') else pay_section.get('data', [])
        
        # Try to find amount columns in earnings
        earnings_headers = earnings_section.headers if hasattr(earnings_section, 'headers') else earnings_section.get('headers', [])
        amount_idx = self._find_amount_column(earnings_headers)
        
        if amount_idx is None:
            warnings.append("Could not identify earnings amount column")
            return True, [], warnings
        
        # Sum earnings (excluding any "GROSS" line which is a summary)
        total_earnings = Decimal('0')
        for row in earnings_data:
            values = list(row.values()) if isinstance(row, dict) else row
            
            # Skip if this is a GROSS summary row
            if any('gross' in str(v).lower() for v in values[:2]):
                continue
            
            if amount_idx < len(values):
                amount = self._parse_currency(values[amount_idx])
                if amount:
                    total_earnings += amount
        
        # Find gross in pay section
        gross = self._find_value_in_section(pay_section, ['gross', 'gross_pay', 'total_earnings'])
        
        if gross is None:
            warnings.append("Could not find Gross Pay value")
            return True, [], warnings
        
        # Compare
        diff = abs(total_earnings - gross)
        if diff > self.CURRENCY_TOLERANCE:
            errors.append(f"Earnings sum ({total_earnings}) does not match Gross ({gross}), difference: {diff}")
        
        return len(errors) == 0, errors, warnings
    
    def _check_gross_minus_taxes_deductions(self, sections: Dict) -> tuple:
        """Check that Gross - Taxes - Deductions = Net"""
        errors = []
        warnings = []
        
        pay_section = sections.get('pay_totals')
        taxes_section = sections.get('taxes')
        deductions_section = sections.get('deductions')
        
        if not pay_section:
            return True, [], ["Cannot verify math - no pay_totals section"]
        
        # Get values
        gross = self._find_value_in_section(pay_section, ['gross', 'gross_pay', 'total_gross'])
        net = self._find_value_in_section(pay_section, ['net', 'net_pay', 'take_home'])
        
        if gross is None or net is None:
            warnings.append("Could not find Gross or Net pay values")
            return True, [], warnings
        
        # Sum taxes
        total_taxes = Decimal('0')
        if taxes_section:
            taxes_data = taxes_section.data if hasattr(taxes_section, 'data') else taxes_section.get('data', [])
            taxes_headers = taxes_section.headers if hasattr(taxes_section, 'headers') else taxes_section.get('headers', [])
            amount_idx = self._find_amount_column(taxes_headers, prefer_current=True)
            
            if amount_idx is not None:
                for row in taxes_data:
                    values = list(row.values()) if isinstance(row, dict) else row
                    if amount_idx < len(values):
                        amount = self._parse_currency(values[amount_idx])
                        if amount:
                            total_taxes += amount
        
        # Sum deductions
        total_deductions = Decimal('0')
        if deductions_section:
            ded_data = deductions_section.data if hasattr(deductions_section, 'data') else deductions_section.get('data', [])
            ded_headers = deductions_section.headers if hasattr(deductions_section, 'headers') else deductions_section.get('headers', [])
            amount_idx = self._find_amount_column(ded_headers, prefer_current=True, prefer_ee=True)
            
            if amount_idx is not None:
                for row in ded_data:
                    values = list(row.values()) if isinstance(row, dict) else row
                    if amount_idx < len(values):
                        amount = self._parse_currency(values[amount_idx])
                        if amount:
                            total_deductions += amount
        
        # Calculate expected net
        expected_net = gross - total_taxes - total_deductions
        diff = abs(expected_net - net)
        
        if diff > self.CURRENCY_TOLERANCE:
            errors.append(
                f"Math check failed: Gross ({gross}) - Taxes ({total_taxes}) - Deductions ({total_deductions}) "
                f"= {expected_net}, but Net Pay is {net} (difference: {diff})"
            )
        
        return len(errors) == 0, errors, warnings
    
    def _check_data_consistency(self, sections: Dict) -> tuple:
        """Check for data consistency issues"""
        errors = []
        warnings = []
        
        for section_name, section in sections.items():
            data = section.data if hasattr(section, 'data') else section.get('data', [])
            headers = section.headers if hasattr(section, 'headers') else section.get('headers', [])
            
            if not data:
                continue
            
            # Check for consistent column counts
            expected_cols = len(headers)
            inconsistent_rows = 0
            
            for i, row in enumerate(data):
                values = list(row.values()) if isinstance(row, dict) else row
                if len(values) != expected_cols:
                    inconsistent_rows += 1
            
            if inconsistent_rows > 0:
                warnings.append(f"{section_name}: {inconsistent_rows} rows have inconsistent column count")
            
            # Check for empty rows
            empty_rows = sum(1 for row in data if all(not str(v).strip() for v in (row.values() if isinstance(row, dict) else row)))
            if empty_rows > len(data) * 0.1:  # More than 10% empty
                warnings.append(f"{section_name}: {empty_rows} empty rows detected")
        
        return True, [], warnings  # Consistency issues are warnings
    
    def _check_value_ranges(self, sections: Dict) -> tuple:
        """Check that values are in expected ranges"""
        errors = []
        warnings = []
        
        # Check hours don't exceed reasonable limits
        earnings_section = sections.get('earnings')
        if earnings_section:
            headers = earnings_section.headers if hasattr(earnings_section, 'headers') else earnings_section.get('headers', [])
            data = earnings_section.data if hasattr(earnings_section, 'data') else earnings_section.get('data', [])
            
            hours_idx = self._find_hours_column(headers)
            if hours_idx is not None:
                for row in data:
                    values = list(row.values()) if isinstance(row, dict) else row
                    if hours_idx < len(values):
                        hours = self._parse_number(values[hours_idx])
                        if hours and hours > 744:  # Max hours in a month (31 * 24)
                            warnings.append(f"Unusually high hours value: {hours}")
        
        return True, [], warnings
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _normalize_field_name(self, name: str) -> str:
        """Normalize field name for comparison"""
        return re.sub(r'[^a-z0-9]', '', str(name).lower())
    
    def _is_name_field(self, normalized_header: str) -> bool:
        """Check if header represents a name field"""
        name_patterns = ['name', 'employeename', 'fullname', 'empname', 'employee']
        return any(p in normalized_header for p in name_patterns)
    
    def _is_id_field(self, normalized_header: str) -> bool:
        """Check if header represents an ID field"""
        id_patterns = ['id', 'employeeid', 'empid', 'eeid', 'empno', 'employeeno', 'number']
        return any(p in normalized_header for p in id_patterns)
    
    def _find_amount_column(self, headers: List[str], 
                            prefer_current: bool = True,
                            prefer_ee: bool = False) -> Optional[int]:
        """Find the column index for amounts"""
        normalized = [self._normalize_field_name(h) for h in headers]
        
        # Priority order for finding amount column
        if prefer_current:
            patterns = ['current', 'curamount', 'curamt', 'amount', 'amt']
        else:
            patterns = ['amount', 'amt', 'current', 'total']
        
        if prefer_ee:
            patterns = ['eeamount', 'eecurrent', 'employeeamount'] + patterns
        
        for pattern in patterns:
            for i, h in enumerate(normalized):
                if pattern in h:
                    return i
        
        # Fallback: look for any numeric-looking column
        return None
    
    def _find_hours_column(self, headers: List[str]) -> Optional[int]:
        """Find the column index for hours"""
        normalized = [self._normalize_field_name(h) for h in headers]
        
        for i, h in enumerate(normalized):
            if 'hour' in h or h == 'hrs':
                return i
        
        return None
    
    def _find_value_in_section(self, section: Any, 
                                labels: List[str]) -> Optional[Decimal]:
        """Find a value in a key-value section by label"""
        data = section.data if hasattr(section, 'data') else section.get('data', [])
        headers = section.headers if hasattr(section, 'headers') else section.get('headers', [])
        
        # For key-value sections, look for matching labels
        for row in data:
            values = list(row.values()) if isinstance(row, dict) else row
            
            # Check if any cell contains the label
            for i, val in enumerate(values):
                val_lower = str(val).lower()
                if any(label in val_lower for label in labels):
                    # Found label, look for value in adjacent cells
                    for j in range(i + 1, len(values)):
                        parsed = self._parse_currency(values[j])
                        if parsed is not None:
                            return parsed
        
        return None
    
    def _parse_currency(self, value: Any) -> Optional[Decimal]:
        """Parse a currency value to Decimal"""
        if value is None:
            return None
        
        try:
            # Remove currency symbols and commas
            cleaned = re.sub(r'[$,\s]', '', str(value))
            if not cleaned or cleaned == '-':
                return None
            return Decimal(cleaned)
        except (InvalidOperation, ValueError):
            return None
    
    def _parse_number(self, value: Any) -> Optional[float]:
        """Parse a numeric value"""
        if value is None:
            return None
        
        try:
            cleaned = re.sub(r'[,\s]', '', str(value))
            if not cleaned or cleaned == '-':
                return None
            return float(cleaned)
        except ValueError:
            return None
