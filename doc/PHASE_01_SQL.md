# Phase 1: SQL Evolutions

**Status:** 🔄 IN PROGRESS  
**Total Estimated Hours:** 30-38  
**Dependencies:** QueryResolver refactor, Duckling setup  
**Last Updated:** January 12, 2026

---

## Objective

Build deterministic SQL generation for all common query types. Every query follows the same path:

```
User Question → Parse Intent → Resolve Terms → Assemble SQL → Execute → Results
```

NO LLM in the SQL generation path. LLM is for synthesis ONLY.

---

## Prerequisites

### 1. QueryResolver Refactor (2-3 hours) ⏳ NOT STARTED

**Problem:** QueryResolver is 3,233 lines with parallel SQL building logic that duplicates SQLAssembler.

**Solution:** Make it a thin wrapper (~500 lines) that:
1. Parses intent from question
2. Extracts filter terms
3. Calls TermIndex.resolve_terms()
4. Calls SQLAssembler.assemble()
5. Returns results

**Files to modify:**
- `/backend/utils/intelligence/query_resolver.py` - Complete rewrite

**Keep from current QueryResolver:**
- `parse_intent()` function
- Intent enums (QueryIntent, EntityDomain)
- Geographic normalization (US_STATE_CODES, CA_PROVINCE_CODES)
- Domain keyword mapping

**Delete from current QueryResolver:**
- All direct SQL building code
- Duplicate state code mappings (use TermIndex)
- Scoring/fuzzy matching logic
- Table selection logic (use SQLAssembler)

### 2. Duckling Setup (1-2 hours) ⏳ NOT STARTED

**What:** Facebook's Duckling library for parsing numeric and temporal expressions.

**Why:** Deterministic extraction of:
- Numbers: "50000", "greater than 50k", "$100,000"
- Dates: "last year", "2024", "hired in January"
- Ranges: "between 50 and 100", "from 2020 to 2024"
- Comparisons: "more than", "less than", "at least"

**Setup Options:**

Option A: Docker container (recommended for production)
```bash
docker pull rasa/duckling
docker run -p 8000:8000 rasa/duckling
```

Option B: Python wrapper (pyduckling-native)
```bash
pip install pyduckling-native
```

**Integration Point:**
- New file: `/backend/utils/intelligence/value_parser.py`
- Called by TermIndex before term resolution
- Extracts structured values from raw text

**Duckling Dimensions to Use:**
- `number` - numeric values
- `time` - dates and times
- `duration` - time periods
- `quantity` - amounts with units

---

## Evolution Status

| # | Evolution | Hours | Status | Details |
|---|-----------|-------|--------|---------|
| 1 | Categorical Lookups | - | ✅ DONE | Texas→TX, Active→A |
| 2 | Multi-Table JOINs | - | ✅ DONE | employees + deductions |
| 3 | Numeric Comparisons | - | ✅ DONE | salary > 50000 |
| 4 | Date/Time Filters | 4-6 | ⏳ NEXT | hired last year |
| 5 | OR Logic | 2-3 | NOT STARTED | Texas or California |
| 6 | Negation | 2-3 | NOT STARTED | NOT terminated |
| 7 | Aggregations | 3-4 | NOT STARTED | SUM, AVG, MIN, MAX |
| 8 | Group By | 2-3 | NOT STARTED | count BY state |
| 9 | Superlatives | 3-4 | NOT STARTED | highest paid, oldest |
| 10 | Multi-Hop | 6-8 | NOT STARTED | manager's department |

---

## Evolution 1: Categorical Lookups ✅ DONE

**Capability:** Match text values to database codes.

**Examples:**
- "Texas" → `stateprovince = 'TX'`
- "active" → `employee_status = 'A'`
- "401k" → `description ILIKE '%401k%'`

**Implementation:**
- TermIndex stores value→code mappings from column profiling
- STATE_SYNONYMS maps state names to codes
- STATUS_SYNONYMS maps status words to codes
- Description columns use ILIKE for partial matches

**Key Files:**
- `term_index.py` - builds mappings at upload time
- `sql_assembler.py` - generates WHERE clauses

---

## Evolution 2: Multi-Table JOINs ✅ DONE

**Capability:** Combine data from multiple tables with automatic JOIN resolution.

**Examples:**
- "employees with 401k" → Personal JOIN Deductions
- "employees in Texas earning hourly" → Personal JOIN Earnings

**Implementation:**
- SQLAssembler._get_join_path() finds semantic type matches
- _column_mappings stores semantic_type and join_priority
- Deduplication prevents over-constraining (one filter per term)
- Primary table determined by 'personal' keyword or entity_tables

**Join Priority (from term_index.py):**
```python
JOIN_PRIORITY_MAP = {
    'employee_number': 100,  # Primary person ID
    'company_code': 80,       # Organization
    'location_code': 60,      # Secondary
    'job_code': 40,           # Tertiary
    'earning_code': 30,       # Transaction
}
```

---

## Evolution 3: Numeric Comparisons ✅ DONE

**Capability:** Handle numeric filters with comparison operators.

**Query Patterns:**
| Pattern | SQL |
|---------|-----|
| "salary above 50000" | `annual_salary > 50000` |
| "rate between 20 and 40" | `rate BETWEEN 20 AND 40` |
| "at least 100 hours" | `hours >= 100` |
| "under $50k" | `salary < 50000` |

**Implementation Completed 2026-01-12:**

Key files modified:
- `value_parser.py` - Parses numeric expressions (already existed)
- `term_index.py` - Added `resolve_numeric_expression()`, fixed case sensitivity
- `engine.py` - Extract numeric phrases, filter duplicate terms
- `intelligence.py` - Added diagnostic endpoints

Fixes applied:
1. Case-insensitive project lookup (`LOWER(project) = ?`)
2. Filter to actual numeric type columns (`inferred_type = 'numeric'`)
3. Exclude bare numbers from words when part of numeric phrases

Test endpoint: `GET /api/intelligence/{project}/diag/test-numeric?q=salary%20above%2075000`

---

### Step 3.1: Value Parser Module (Duckling Integration)

Create `/backend/utils/intelligence/value_parser.py`:

```python
"""
Value Parser - Extract structured values from natural language.

Uses Duckling for deterministic parsing of:
- Numbers: "50000", "50k", "$100,000"
- Comparisons: "more than 50", "at least 100"
- Ranges: "between 20 and 40"
"""

from dataclasses import dataclass
from typing import Optional, List, Tuple
from enum import Enum
import requests
import re

class ComparisonOp(Enum):
    EQ = "="
    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="
    BETWEEN = "BETWEEN"
    IN = "IN"

@dataclass
class ParsedValue:
    """Result of parsing a value expression."""
    operator: ComparisonOp
    value: float
    value_end: Optional[float] = None  # For BETWEEN
    original_text: str = ""
    confidence: float = 1.0

COMPARISON_PATTERNS = {
    # Greater than
    r'\b(?:more than|greater than|above|over|exceeds?|>\s*)\s*': ComparisonOp.GT,
    r'\b(?:at least|minimum|min|>=\s*)\s*': ComparisonOp.GTE,
    # Less than
    r'\b(?:less than|under|below|<\s*)\s*': ComparisonOp.LT,
    r'\b(?:at most|maximum|max|up to|<=\s*)\s*': ComparisonOp.LTE,
    # Ranges
    r'\b(?:between)\s*': ComparisonOp.BETWEEN,
}

def parse_numeric_expression(text: str) -> Optional[ParsedValue]:
    """
    Parse a numeric expression from text.
    
    Examples:
        "salary above 50000" → ParsedValue(GT, 50000)
        "between 20 and 40 hours" → ParsedValue(BETWEEN, 20, 40)
        "at least $100k" → ParsedValue(GTE, 100000)
    """
    text_lower = text.lower()
    
    # Try pattern matching first
    for pattern, op in COMPARISON_PATTERNS.items():
        match = re.search(pattern, text_lower)
        if match:
            # Extract number after pattern
            remaining = text_lower[match.end():]
            number = extract_number(remaining)
            if number is not None:
                if op == ComparisonOp.BETWEEN:
                    # Look for second number
                    second = extract_second_number(remaining)
                    return ParsedValue(op, number, second, text)
                return ParsedValue(op, number, original_text=text)
    
    # Default: exact match
    number = extract_number(text_lower)
    if number is not None:
        return ParsedValue(ComparisonOp.EQ, number, original_text=text)
    
    return None

def extract_number(text: str) -> Optional[float]:
    """Extract a number from text, handling k/m suffixes and currency."""
    # Remove currency symbols
    text = re.sub(r'[$€£¥]', '', text)
    
    # Handle k/m suffixes
    match = re.search(r'(\d+(?:\.\d+)?)\s*([km])?', text, re.IGNORECASE)
    if match:
        num = float(match.group(1))
        suffix = match.group(2)
        if suffix:
            suffix = suffix.lower()
            if suffix == 'k':
                num *= 1000
            elif suffix == 'm':
                num *= 1000000
        return num
    return None

def extract_second_number(text: str) -> Optional[float]:
    """Extract second number for BETWEEN expressions."""
    # Look for "and X" pattern
    match = re.search(r'\band\s+(\d+(?:\.\d+)?)\s*([km])?', text, re.IGNORECASE)
    if match:
        num = float(match.group(1))
        suffix = match.group(2)
        if suffix:
            if suffix.lower() == 'k':
                num *= 1000
            elif suffix.lower() == 'm':
                num *= 1000000
        return num
    return None
```

### Step 3.2: Enhance TermIndex for Numeric Columns

Add to `term_index.py`:

```python
def _identify_numeric_columns(self) -> Dict[str, List[str]]:
    """
    Identify columns suitable for numeric comparisons.
    
    Returns:
        Dict mapping table_name → list of numeric column names
    """
    numeric_cols = {}
    
    results = self.conn.execute("""
        SELECT table_name, column_name, data_type
        FROM _column_profiles
        WHERE project = ?
        AND (
            data_type IN ('INTEGER', 'BIGINT', 'DOUBLE', 'DECIMAL', 'FLOAT')
            OR column_name ILIKE '%amount%'
            OR column_name ILIKE '%rate%'
            OR column_name ILIKE '%salary%'
            OR column_name ILIKE '%hours%'
            OR column_name ILIKE '%total%'
        )
    """, [self.project]).fetchall()
    
    for table, col, dtype in results:
        if table not in numeric_cols:
            numeric_cols[table] = []
        numeric_cols[table].append(col)
    
    return numeric_cols
```

### Step 3.3: Update SQLAssembler for Numeric Operators

Enhance `_build_where_clause()` in `sql_assembler.py`:

```python
def _build_where_clause(self, term_matches: List[TermMatch], aliases: Dict[str, str]) -> Tuple[str, List[Dict]]:
    """Build WHERE clause, now with numeric operator support."""
    
    conditions = []
    filters = []
    
    for match in term_matches:
        if match.table_name not in aliases:
            continue
        
        alias = aliases[match.table_name]
        
        # Handle different operators
        if match.operator == 'ILIKE':
            condition = f'{alias}."{match.column_name}" ILIKE \'{match.match_value}\''
        elif match.operator == 'BETWEEN':
            # match_value format: "20|40" for "BETWEEN 20 AND 40"
            parts = match.match_value.split('|')
            if len(parts) == 2:
                condition = f'{alias}."{match.column_name}" BETWEEN {parts[0]} AND {parts[1]}'
            else:
                continue
        elif match.operator in ('>', '>=', '<', '<='):
            # Numeric comparison - no quotes
            condition = f'{alias}."{match.column_name}" {match.operator} {match.match_value}'
        elif match.operator == 'IN':
            condition = f'{alias}."{match.column_name}" IN ({match.match_value})'
        else:
            # Default = with quotes
            safe_value = str(match.match_value).replace("'", "''")
            condition = f'{alias}."{match.column_name}" = \'{safe_value}\''
        
        conditions.append(condition)
        filters.append({...})
    
    return 'WHERE ' + ' AND '.join(conditions) if conditions else "", filters
```

### Step 3.4: Test Cases

```python
# Test numeric comparisons
test_cases = [
    ("employees earning above 50000", "salary > 50000"),
    ("workers with rate between 20 and 40", "rate BETWEEN 20 AND 40"),
    ("staff with at least 100 hours", "hours >= 100"),
    ("people making under $50k", "salary < 50000"),
    ("employees with salary = 75000", "salary = 75000"),
]
```

---

## Evolution 4: Date/Time Filters ⏳ NEXT

**Capability:** Handle temporal queries with date comparisons.

**Query Patterns:**
| Pattern | SQL |
|---------|-----|
| "hired last year" | `hire_date >= '2025-01-01' AND hire_date < '2026-01-01'` |
| "terminated in 2024" | `term_date >= '2024-01-01' AND term_date < '2025-01-01'` |
| "started before January" | `start_date < '2026-01-01'` |
| "active in Q4" | `effective_date >= '2025-10-01' AND effective_date < '2026-01-01'` |

**Implementation Plan:**

Following Evolution 3 pattern:
1. `value_parser.py` already has `parse_date_expression()` 
2. Add `resolve_date_expression()` to `term_index.py`
3. Add `_find_date_columns()` to find columns with `inferred_type = 'date'`
4. Add date phrase patterns to `engine.py`
5. Add diagnostic endpoint `/diag/test-date?q=hired%20last%20year`

### Step 4.1: Date Column Detection

Add to `term_index.py`:
```python
def _find_date_columns(self, domain: str = None) -> List[Tuple[str, str]]:
    """Find date columns in the project."""
    DATE_PATTERNS = [
        '%date%', '%_dt', '%effective%', '%start%', '%end%',
        '%hire%', '%term%', '%birth%', '%created%', '%modified%'
    ]
    # Query _column_profiles WHERE inferred_type = 'date'
```

### Step 4.2: Date Phrase Patterns

Add to `engine.py`:
```python
date_phrase_patterns = [
    r'(?:hired|terminated|started|ended)\s+(?:in|last|this)\s+\w+',
    r'(?:last|this|next)\s+(?:year|month|quarter|week)',
    r'(?:in|during|before|after)\s+(?:Q[1-4]|January|February|...|\d{4})',
]
```

### Step 4.3: Test Cases

```python
test_cases = [
    ("employees hired last year", "hire_date >= '2025-01-01' AND hire_date < '2026-01-01'"),
    ("terminated in 2024", "term_date >= '2024-01-01' AND term_date < '2025-01-01'"),
    ("hired in Q4", "hire_date >= '2025-10-01' AND hire_date < '2026-01-01'"),
]
```

---

## Evolution 5: OR Logic

**Capability:** Handle disjunctive queries.

**Query Patterns:**
| Pattern | SQL |
|---------|-----|
| "Texas or California" | `state IN ('TX', 'CA')` |
| "active or on leave" | `status IN ('A', 'L')` |
| "earning code 100 or 200" | `code IN (100, 200)` |

**Implementation:**
- Detect "or" keyword between like terms
- Group into IN clause instead of multiple ANDs
- Update SQLAssembler to handle IN operator

---

## Evolution 6: Negation

**Capability:** Handle NOT/exclusion queries.

**Query Patterns:**
| Pattern | SQL |
|---------|-----|
| "not in Texas" | `state != 'TX'` |
| "not terminated" | `status != 'T'` |
| "excluding California" | `state != 'CA'` |

**Implementation:**
- Detect negation keywords: "not", "except", "excluding", "without"
- Add `!=` and `NOT IN` operators to SQLAssembler

---

## Evolution 7: Aggregations

**Capability:** Handle SUM, AVG, MIN, MAX queries.

**Query Patterns:**
| Pattern | SQL |
|---------|-----|
| "total earnings" | `SELECT SUM(amount)` |
| "average salary" | `SELECT AVG(salary)` |
| "highest rate" | `SELECT MAX(rate)` |
| "minimum hours" | `SELECT MIN(hours)` |

**Implementation:**
- Detect aggregation keywords in intent parsing
- New QueryIntent values: SUM, AVERAGE, MINIMUM, MAXIMUM
- SQLAssembler generates appropriate SELECT clause

---

## Evolution 8: Group By

**Capability:** Handle dimensional breakdowns.

**Query Patterns:**
| Pattern | SQL |
|---------|-----|
| "headcount by state" | `GROUP BY state` |
| "earnings by department" | `GROUP BY department` |
| "count per location" | `GROUP BY location` |

**Implementation:**
- Detect "by", "per", "for each" keywords
- Identify grouping column from term resolution
- SQLAssembler adds GROUP BY clause

---

## Evolution 9: Superlatives

**Capability:** Handle top/bottom/highest/lowest queries.

**Query Patterns:**
| Pattern | SQL |
|---------|-----|
| "highest paid employees" | `ORDER BY salary DESC LIMIT 10` |
| "oldest employees" | `ORDER BY hire_date ASC LIMIT 10` |
| "top 5 earners" | `ORDER BY earnings DESC LIMIT 5` |
| "bottom performers" | `ORDER BY rating ASC LIMIT 10` |

**Implementation:**
- Detect superlative keywords: "top", "highest", "lowest", "most", "least"
- Identify ordering column and direction
- SQLAssembler adds ORDER BY and LIMIT

---

## Evolution 10: Multi-Hop Relationships

**Capability:** Navigate relationship chains.

**Query Patterns:**
| Pattern | SQL |
|---------|-----|
| "manager's department" | JOIN through supervisor_id |
| "employees in John's team" | Self-join on manager relationship |
| "location's regional manager" | Multiple JOIN hops |

**Implementation:**
- Identify relationship chains from _column_mappings
- Build multi-step JOIN paths
- Handle self-referential relationships (manager → employee)

---

## Testing Strategy

### Unit Tests (per evolution)
- Input parsing (extract numbers, dates, operators)
- SQL generation (correct WHERE clauses)
- Edge cases (null handling, empty results)

### Integration Tests
- Full question → SQL → results path
- Multi-condition queries
- Cross-domain queries

### Intelligence Test Page
- URL: `/admin/intelligence-test`
- Live testing against real project data
- Shows term resolution, SQL, results

---

## Success Criteria

### Phase Complete When:
1. All 10 evolutions implemented and tested
2. 95% of common HCM queries resolve to valid SQL
3. No LLM in SQL generation path
4. QueryResolver reduced to ~500 lines
5. Intelligence Test Page validates all patterns

### Quality Gates:
- Zero SQL injection vulnerabilities
- Sub-100ms query generation
- Deterministic results (same input → same SQL)
- Clear error messages for unresolvable queries

---

## Version History

| Date | Change |
|------|--------|
| 2026-01-12 | Evolution 3 (Numeric Comparisons) completed. Fixed case sensitivity, type filtering, phrase deduplication. |
| 2026-01-11 | Initial detailed phase doc created |
