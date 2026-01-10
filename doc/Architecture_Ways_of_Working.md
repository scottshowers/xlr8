# XLR8 Architecture

## Ways of Working

### PRIORITY 1: SqlGenerator Intelligence Integration
**Status:** IN PROGRESS  
**Date:** 2025-01-10  
**Goal:** Make SqlGenerator use existing intelligence (context graph, lookups, column profiles) so LLM generates correct SQL without hallucinating.

---

#### Problem Statement
SqlGenerator receives raw schema (column names + types) but no intelligence about:
- What values mean ('A' = Active)
- How to translate user terms ('Texas' → 'TX')
- Which tables relate to each other
- What columns are filterable and how

QueryResolver has all this intelligence but only handles ~5 query patterns. Everything else falls to blind SqlGenerator.

---

#### What We Have (Already Built)
| Component | Location | What It Provides |
|-----------|----------|------------------|
| `_column_profiles` | DuckDB | filter_category, distinct_values, value_distribution |
| `_intelligence_lookups` | DuckDB | code → description mappings from config tables |
| `context_graph` | handler.get_context_graph() | hub-spoke relationships, join paths |
| `_table_registry` | DuckDB | table classifications (master/config/transaction) |
| `vocabulary` | engine.vocabulary | customer terminology mappings |
| `filter_candidates` | engine.filter_candidates | columns by category (status, location, company) |

---

#### Implementation Plan

##### Step 1: Enrich Schema in SqlGenerator (2 hours)
**File:** `backend/utils/intelligence/sql_generator.py`  
**Function:** `_build_create_table_schema()`

Change from:
```sql
CREATE TABLE emp (
    employment_status_code TEXT,
    state_province_code TEXT
);
```

To:
```sql
CREATE TABLE emp (
    employment_status_code TEXT,  -- Filter:status | Values:['A','L','T'] | A=Active,L=LOA,T=Terminated
    state_province_code TEXT,     -- Filter:location | Values:['TX','CA','NY',...] | US state codes
);
```

**How:**
1. Query `_column_profiles` for each column
2. If `filter_category` exists, add it as comment
3. If `distinct_values` exists and count < 20, add to comment
4. Query `_intelligence_lookups` for value descriptions

##### Step 2: Add Filter Translation Block (1 hour)
**File:** `backend/utils/intelligence/sql_generator.py`  
**Function:** `_generate_simple()` and `_generate_complex()`

Add to prompt:
```
FILTER TRANSLATIONS (use these for WHERE clauses):
- "active" → employment_status_code = 'A'
- "terminated" → employment_status_code = 'T'
- "texas" → state_province_code = 'TX'
- "california" → state_province_code = 'CA'
```

**How:**
1. Get `filter_candidates` from engine
2. For each category (status, location, company), get the column
3. Query `_intelligence_lookups` or `_column_profiles` for value mappings
4. Build translation hints

##### Step 3: Add Join Intelligence (1 hour)
**File:** `backend/utils/intelligence/sql_generator.py`  
**Function:** `_build_relationship_hints()`

Already exists but may not use context graph. Verify it uses:
```python
graph = self.handler.get_context_graph(project)
# Get join paths between selected tables
```

##### Step 4: Retry Loop with Feedback (2 hours)
**File:** `backend/utils/intelligence/sql_generator.py`  
**New function:** `_generate_with_retry()`

```python
def _generate_with_retry(self, question, table, max_attempts=3):
    for attempt in range(max_attempts):
        result = self._generate_simple(question, table, orchestrator)
        if result and self._validate_sql(result['sql']):
            return result
        
        # Parse error, add feedback
        error = self._get_sql_error(result)
        feedback = self._build_correction_hint(error)
        # Retry with feedback in prompt
```

##### Step 5: Test Suite (1 hour)
Create `tests/test_sql_intelligence.py`:
```python
def test_active_employees():
    # "show active employees" → WHERE employment_status_code = 'A'
    
def test_texas_filter():
    # "employees in texas" → WHERE state_province_code = 'TX'
    
def test_company_filter():
    # "employees at ACME" → WHERE company_code = '001' (from lookup)
    
def test_combined_filters():
    # "active employees in texas" → both filters correct
```

---

#### Verification Criteria
- [ ] "show active employees" generates correct SQL without hallucination
- [ ] "employees in texas" uses 'TX' not 'Texas'
- [ ] "employees at [company name]" looks up code from intelligence
- [ ] Joins use context graph paths
- [ ] Provenance shows which intelligence was used
- [ ] Failed queries retry with feedback

---

#### Timeline
| Task | Hours | Owner |
|------|-------|-------|
| Step 1: Enrich schema | 2 | Claude |
| Step 2: Filter translations | 1 | Claude |
| Step 3: Join intelligence | 1 | Claude |
| Step 4: Retry loop | 2 | Claude |
| Step 5: Tests | 1 | Claude |
| **Total** | **7** | |

---

### PRIORITY 2: Analysis Orchestration Layer
**Status:** BLOCKED (waiting on Priority 1)  
**Dependency:** SqlGenerator must be reliable before analysis can chain queries

Once SqlGenerator works reliably:
1. Define metric formulas (turnover rate, tenure, etc.)
2. Build multi-step query orchestration
3. Add interpretation layer using reference docs + LLM
4. Proactive insights based on data patterns

---

## Core Architecture

### Five Truths
| Truth | Source | Purpose |
|-------|--------|---------|
| Reality | DuckDB (customer data) | What exists |
| Intent | User question parsing | What they want |
| Configuration | Config tables via hubs | How it's set up |
| Reference | ChromaDB (vendor docs) | How it should work |
| Regulatory | ChromaDB (compliance) | Legal requirements |

### Data Flow
```
Upload → structured_data_handler → DuckDB + metadata tables
                                        ↓
Query → Engine → QueryResolver (deterministic) or SqlGenerator (LLM)
                                        ↓
                           Gatherers (Five Truths)
                                        ↓
                              Synthesizer → Response
```

### Intelligence Layer
```
_column_profiles     → Per-column stats, filter categories, values
_table_registry      → Table classifications, domains
_intelligence_lookups → Code-to-description from config hubs
context_graph        → Hub-spoke relationships
vocabulary           → Customer terminology
```
