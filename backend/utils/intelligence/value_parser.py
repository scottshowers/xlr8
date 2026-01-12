"""
XLR8 Value Parser - Deterministic Parsing for Numeric and Temporal Expressions
===============================================================================

Uses pattern matching for deterministic extraction of:
- Numbers: "50000", "50k", "$100,000"
- Comparisons: "more than 50", "at least 100"
- Ranges: "between 20 and 40"
- Dates: "last year", "2024", "Q4" (future: Duckling)

NOTE: For production, consider integrating Facebook's Duckling for
more robust temporal parsing. This module provides a solid baseline.

Author: XLR8 Team
Version: 1.0.0
Date: 2026-01-11
"""

import re
import logging
from dataclasses import dataclass
from typing import Optional, List, Tuple, Any
from enum import Enum
from datetime import datetime, date, timedelta

logger = logging.getLogger(__name__)


# =============================================================================
# COMPARISON OPERATORS
# =============================================================================

class ComparisonOp(Enum):
    """SQL comparison operators."""
    EQ = "="
    NE = "!="
    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="
    BETWEEN = "BETWEEN"
    IN = "IN"
    NOT_IN = "NOT IN"
    ILIKE = "ILIKE"


# =============================================================================
# PARSED VALUE RESULT
# =============================================================================

@dataclass
class ParsedValue:
    """Result of parsing a value expression."""
    value_type: str  # 'numeric', 'date', 'text'
    operator: ComparisonOp
    value: Any  # The primary value
    value_end: Optional[Any] = None  # For BETWEEN
    original_text: str = ""
    confidence: float = 1.0
    
    def to_sql_condition(self, column: str, alias: str = None) -> str:
        """Generate SQL condition string."""
        col_ref = f'{alias}."{column}"' if alias else f'"{column}"'
        
        if self.operator == ComparisonOp.BETWEEN:
            return f"{col_ref} BETWEEN {self.value} AND {self.value_end}"
        elif self.operator == ComparisonOp.IN:
            values = ', '.join(str(v) for v in self.value) if isinstance(self.value, list) else self.value
            return f"{col_ref} IN ({values})"
        elif self.operator == ComparisonOp.ILIKE:
            return f"{col_ref} ILIKE '{self.value}'"
        elif self.value_type == 'numeric':
            return f"{col_ref} {self.operator.value} {self.value}"
        else:
            # Text/date - needs quotes
            safe_value = str(self.value).replace("'", "''")
            return f"{col_ref} {self.operator.value} '{safe_value}'"


@dataclass
class ParsedDateRange:
    """Result of parsing a date expression."""
    start_date: date
    end_date: date
    grain: str  # 'year', 'quarter', 'month', 'week', 'day'
    original_text: str = ""
    
    def to_sql_condition(self, column: str, alias: str = None) -> str:
        """Generate SQL condition for date range."""
        col_ref = f'{alias}."{column}"' if alias else f'"{column}"'
        return f"{col_ref} >= '{self.start_date}' AND {col_ref} < '{self.end_date}'"


# =============================================================================
# COMPARISON PATTERNS
# =============================================================================

# Pattern → Operator mapping (order matters - more specific first)
COMPARISON_PATTERNS: List[Tuple[str, ComparisonOp]] = [
    # Greater than or equal
    (r'\b(?:at\s+least|minimum|min|no\s+less\s+than|>=)\s*', ComparisonOp.GTE),
    # Less than or equal
    (r'\b(?:at\s+most|maximum|max|up\s+to|no\s+more\s+than|<=)\s*', ComparisonOp.LTE),
    # Greater than
    (r'\b(?:more\s+than|greater\s+than|above|over|exceeds?|higher\s+than|>)\s*', ComparisonOp.GT),
    # Less than
    (r'\b(?:less\s+than|under|below|lower\s+than|<)\s*', ComparisonOp.LT),
    # Not equal
    (r'\b(?:not|except|excluding|other\s+than|!=)\s*', ComparisonOp.NE),
    # Between (handled specially)
    (r'\b(?:between)\s*', ComparisonOp.BETWEEN),
]

# Number extraction patterns
# Note: Order matters - comma-formatted first, then plain numbers
NUMBER_PATTERN = r'[\$€£¥]?\s*(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?\s*([kmKM])?'


# =============================================================================
# NUMERIC PARSING
# =============================================================================

def extract_number(text: str) -> Optional[float]:
    """
    Extract a number from text, handling currency and suffixes.
    
    Examples:
        "50000" → 50000.0
        "$50,000" → 50000.0
        "50k" → 50000.0
        "1.5M" → 1500000.0
    """
    # Remove currency symbols
    text = re.sub(r'[\$€£¥]', '', text)
    # Remove commas in numbers
    text = text.replace(',', '')
    
    match = re.search(r'(\d+(?:\.\d+)?)\s*([kmKM])?', text)
    if match:
        num = float(match.group(1))
        suffix = match.group(2)
        if suffix:
            suffix_lower = suffix.lower()
            if suffix_lower == 'k':
                num *= 1000
            elif suffix_lower == 'm':
                num *= 1000000
        return num
    return None


def extract_number_from_position(text: str, start_pos: int = 0) -> Tuple[Optional[float], int]:
    """
    Extract number starting from a position in text.
    
    Returns:
        Tuple of (number, end_position)
    """
    remaining = text[start_pos:]
    match = re.search(NUMBER_PATTERN, remaining)
    if match:
        # Group 1: integer part (with or without commas)
        # Group 2: decimal part (if any)
        # Group 3: suffix (k/m)
        num_str = match.group(1).replace(',', '')
        decimal_part = match.group(2)
        suffix = match.group(3)
        
        if decimal_part:
            num = float(f"{num_str}.{decimal_part}")
        else:
            num = float(num_str)
        
        if suffix:
            if suffix.lower() == 'k':
                num *= 1000
            elif suffix.lower() == 'm':
                num *= 1000000
        return num, start_pos + match.end()
    return None, start_pos


def parse_numeric_expression(text: str) -> Optional[ParsedValue]:
    """
    Parse a numeric expression from text.
    
    Examples:
        "salary above 50000" → ParsedValue(GT, 50000)
        "between 20 and 40 hours" → ParsedValue(BETWEEN, 20, 40)
        "at least $100k" → ParsedValue(GTE, 100000)
        "rate = 25" → ParsedValue(EQ, 25)
        
    Returns:
        ParsedValue or None if no numeric expression found
    """
    text_lower = text.lower().strip()
    
    # Try each comparison pattern
    for pattern, op in COMPARISON_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            # Extract number after the pattern
            remaining = text_lower[match.end():]
            number, end_pos = extract_number_from_position(text_lower, match.end())
            
            if number is not None:
                if op == ComparisonOp.BETWEEN:
                    # Look for second number after "and"
                    and_match = re.search(r'\band\s+', remaining)
                    if and_match:
                        second_num, _ = extract_number_from_position(remaining, and_match.end())
                        if second_num is not None:
                            return ParsedValue(
                                value_type='numeric',
                                operator=ComparisonOp.BETWEEN,
                                value=number,
                                value_end=second_num,
                                original_text=text,
                                confidence=0.95
                            )
                else:
                    return ParsedValue(
                        value_type='numeric',
                        operator=op,
                        value=number,
                        original_text=text,
                        confidence=0.95
                    )
    
    # No comparison pattern found - try for bare number (exact match)
    number = extract_number(text_lower)
    if number is not None:
        return ParsedValue(
            value_type='numeric',
            operator=ComparisonOp.EQ,
            value=number,
            original_text=text,
            confidence=0.8
        )
    
    return None


# =============================================================================
# DATE PARSING (Basic - consider Duckling for production)
# =============================================================================

def parse_date_expression(text: str, reference_date: date = None) -> Optional[ParsedDateRange]:
    """
    Parse a date/time expression from text.
    
    Examples:
        "last year" → 2025-01-01 to 2025-12-31
        "2024" → 2024-01-01 to 2024-12-31
        "Q4" → 2025-10-01 to 2025-12-31
        "January" → 2026-01-01 to 2026-01-31
        
    NOTE: For production use, integrate Facebook's Duckling for
    more robust and comprehensive date parsing.
    
    Returns:
        ParsedDateRange or None
    """
    if reference_date is None:
        reference_date = date.today()
    
    text_lower = text.lower().strip()
    
    # Pattern: "last year", "previous year"
    if re.search(r'\b(?:last|previous)\s+year\b', text_lower):
        year = reference_date.year - 1
        return ParsedDateRange(
            start_date=date(year, 1, 1),
            end_date=date(year + 1, 1, 1),
            grain='year',
            original_text=text
        )
    
    # Pattern: "this year", "current year"
    if re.search(r'\b(?:this|current)\s+year\b', text_lower):
        year = reference_date.year
        return ParsedDateRange(
            start_date=date(year, 1, 1),
            end_date=date(year + 1, 1, 1),
            grain='year',
            original_text=text
        )
    
    # Pattern: "last month", "previous month"
    if re.search(r'\b(?:last|previous)\s+month\b', text_lower):
        first_of_this = reference_date.replace(day=1)
        last_month_end = first_of_this - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        return ParsedDateRange(
            start_date=last_month_start,
            end_date=first_of_this,
            grain='month',
            original_text=text
        )
    
    # IMPORTANT: Check compound patterns (quarter+year, month+year) BEFORE simple patterns
    
    # Pattern: Quarter WITH year "Q2 2024", "Q1 2025"
    quarter_year_match = re.search(r'\bq([1-4])\s*(?:of\s+)?(\d{4})\b', text_lower)
    if not quarter_year_match:
        quarter_year_match = re.search(r'\b(\d{4})\s*q([1-4])\b', text_lower)
        if quarter_year_match:
            # Swap groups - year is group 1, quarter is group 2
            year = int(quarter_year_match.group(1))
            q = int(quarter_year_match.group(2))
            quarter_starts = {1: 1, 2: 4, 3: 7, 4: 10}
            start_month = quarter_starts[q]
            end_month = start_month + 3 if q < 4 else 1
            end_year = year if q < 4 else year + 1
            return ParsedDateRange(
                start_date=date(year, start_month, 1),
                end_date=date(end_year, end_month, 1),
                grain='quarter',
                original_text=text
            )
    
    if quarter_year_match:
        q = int(quarter_year_match.group(1))
        year = int(quarter_year_match.group(2))
        quarter_starts = {1: 1, 2: 4, 3: 7, 4: 10}
        start_month = quarter_starts[q]
        end_month = start_month + 3 if q < 4 else 1
        end_year = year if q < 4 else year + 1
        return ParsedDateRange(
            start_date=date(year, start_month, 1),
            end_date=date(end_year, end_month, 1),
            grain='quarter',
            original_text=text
        )
    
    # Pattern: Month names (check for compound with year first)
    months = {
        'january': 1, 'jan': 1, 'february': 2, 'feb': 2,
        'march': 3, 'mar': 3, 'april': 4, 'apr': 4,
        'may': 5, 'june': 6, 'jun': 6, 'july': 7, 'jul': 7,
        'august': 8, 'aug': 8, 'september': 9, 'sep': 9, 'sept': 9,
        'october': 10, 'oct': 10, 'november': 11, 'nov': 11,
        'december': 12, 'dec': 12
    }
    
    # Check for month with year
    for month_name, month_num in months.items():
        # Pattern: "January 2025" or "2025 January" or "Jan 2025"
        month_year_pattern = rf'\b{month_name}\s+(\d{{4}})\b|\b(\d{{4}})\s+{month_name}\b'
        month_year_match = re.search(month_year_pattern, text_lower)
        if month_year_match:
            year = int(month_year_match.group(1) or month_year_match.group(2))
            # Calculate end date (first day of next month)
            if month_num == 12:
                end_date_val = date(year + 1, 1, 1)
            else:
                end_date_val = date(year, month_num + 1, 1)
            return ParsedDateRange(
                start_date=date(year, month_num, 1),
                end_date=end_date_val,
                grain='month',
                original_text=text
            )
    
    # Pattern: Quarters alone "Q1", "Q2", "Q3", "Q4" (no year specified)
    quarter_match = re.search(r'\bq([1-4])\b', text_lower)
    if quarter_match:
        # Check there's no year in the text (we would have matched above)
        year_check = re.search(r'\b(20\d{2})\b', text_lower)
        if not year_check:
            q = int(quarter_match.group(1))
            year = reference_date.year
            quarter_starts = {1: 1, 2: 4, 3: 7, 4: 10}
            start_month = quarter_starts[q]
            end_month = start_month + 3 if q < 4 else 1
            end_year = year if q < 4 else year + 1
            return ParsedDateRange(
                start_date=date(year, start_month, 1),
                end_date=date(end_year, end_month, 1),
                grain='quarter',
                original_text=text
            )
    
    # Check for month alone (without year)
    for month_name, month_num in months.items():
        if re.search(rf'\b{month_name}\b', text_lower):
            # Check there's no year in the text
            year_check = re.search(r'\b(20\d{2})\b', text_lower)
            if not year_check:
                year = reference_date.year
                if month_num == 12:
                    end_date_val = date(year + 1, 1, 1)
                else:
                    end_date_val = date(year, month_num + 1, 1)
                return ParsedDateRange(
                    start_date=date(year, month_num, 1),
                    end_date=end_date_val,
                    grain='month',
                    original_text=text
                )
    
    # Pattern: Just a year "2024", "in 2024" (only if no month or quarter specified)
    year_match = re.search(r'\b(20\d{2})\b', text_lower)
    if year_match:
        year = int(year_match.group(1))
        return ParsedDateRange(
            start_date=date(year, 1, 1),
            end_date=date(year + 1, 1, 1),
            grain='year',
            original_text=text
        )
    
    return None


# =============================================================================
# COMBINED PARSER
# =============================================================================

def parse_value_expression(text: str, context_type: str = None) -> Optional[ParsedValue]:
    """
    Parse any value expression from text.
    
    Tries numeric parsing first, then date if context suggests temporal.
    
    Args:
        text: The text to parse
        context_type: Hint about expected type ('numeric', 'date', 'text')
        
    Returns:
        ParsedValue or None
    """
    # Try numeric first (most common in HCM queries)
    numeric = parse_numeric_expression(text)
    if numeric:
        return numeric
    
    # Try date if context suggests it or numeric failed
    if context_type in (None, 'date', 'temporal'):
        date_range = parse_date_expression(text)
        if date_range:
            # Convert date range to ParsedValue
            return ParsedValue(
                value_type='date',
                operator=ComparisonOp.BETWEEN,
                value=date_range.start_date.isoformat(),
                value_end=date_range.end_date.isoformat(),
                original_text=text,
                confidence=0.9
            )
    
    return None


# =============================================================================
# COLUMN TYPE DETECTION
# =============================================================================

def detect_numeric_columns(column_names: List[str]) -> List[str]:
    """
    Detect columns likely to be numeric based on name patterns.
    
    Returns list of column names that are probably numeric.
    """
    numeric_patterns = [
        r'amount', r'rate', r'salary', r'wage', r'pay',
        r'hours', r'total', r'count', r'qty', r'quantity',
        r'price', r'cost', r'fee', r'balance', r'sum',
        r'percent', r'pct', r'ratio', r'factor',
        r'_amt$', r'_rate$', r'_hrs$', r'_qty$'
    ]
    
    numeric_cols = []
    for col in column_names:
        col_lower = col.lower()
        for pattern in numeric_patterns:
            if re.search(pattern, col_lower):
                numeric_cols.append(col)
                break
    
    return numeric_cols


def detect_date_columns(column_names: List[str]) -> List[str]:
    """
    Detect columns likely to be dates based on name patterns.
    
    Returns list of column names that are probably dates.
    """
    date_patterns = [
        r'date', r'_dt$', r'_date$', r'effective',
        r'start', r'end', r'begin', r'hire',
        r'term', r'birth', r'created', r'modified',
        r'timestamp', r'time$'
    ]
    
    date_cols = []
    for col in column_names:
        col_lower = col.lower()
        for pattern in date_patterns:
            if re.search(pattern, col_lower):
                date_cols.append(col)
                break
    
    return date_cols


# =============================================================================
# TESTING / EXAMPLES
# =============================================================================

if __name__ == "__main__":
    # Test numeric parsing
    test_numeric = [
        "salary above 50000",
        "rate between 20 and 40",
        "at least $100k",
        "less than 1.5M",
        "more than 75 hours",
        "50000",
        "under $30,000",
    ]
    
    print("=== Numeric Parsing ===")
    for text in test_numeric:
        result = parse_numeric_expression(text)
        if result:
            print(f"'{text}' → {result.operator.value} {result.value}" + 
                  (f" AND {result.value_end}" if result.value_end else ""))
        else:
            print(f"'{text}' → NOT PARSED")
    
    # Test date parsing
    test_dates = [
        "last year",
        "2024",
        "Q4",
        "January 2025",
        "hired in March",
        "Q2 2024",
    ]
    
    print("\n=== Date Parsing ===")
    for text in test_dates:
        result = parse_date_expression(text)
        if result:
            print(f"'{text}' → {result.start_date} to {result.end_date} ({result.grain})")
        else:
            print(f"'{text}' → NOT PARSED")
