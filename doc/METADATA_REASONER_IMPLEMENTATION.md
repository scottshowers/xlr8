# IMPLEMENTATION COMPLETE: MetadataReasoner + Cross-Domain Fix
## Date: 2026-01-11

---

## WHAT WAS DONE

### 1. Created MetadataReasoner (`/backend/utils/intelligence/metadata_reasoner.py`)

**Purpose:** Fallback for unknown terms by querying EXISTING metadata (no pre-computation)

**How it works:**
```
Input: "401k" (not found in term_index)

Step 1: Load metadata on init (cached)
        - _domain_tables: Which tables belong to which domain
        - _description_columns: Which columns are descriptions
        - _code_columns: Which columns are codes
        - _name_columns: Which columns are names

Step 2: Classify term
        - "401k" → 'mixed' (alphanumeric, search both code and description)
        - "overtime" → 'keyword' (search descriptions)
        - "MED" → 'code' (search code columns)

Step 3: Determine target domains
        - "401k" → ['deductions', 'benefits'] (domain hints)

Step 4: Build ILIKE filters
        - Return: Deductions.description ILIKE '%401%'
```

### 2. Integrated MetadataReasoner into TermIndex.resolve_terms()

**Location:** `/backend/utils/intelligence/term_index.py` lines 812-920

**Flow:**
```
resolve_terms(["texas", "401k"]) →
  
  LAYER 1: Fast path (term_index lookup)
    - "texas" → FOUND: Personal.state = 'TX' ✓
    - "401k" → NOT FOUND, add to unresolved_terms
  
  LAYER 2: MetadataReasoner fallback
    - "401k" → Reasoner finds: Deductions.description ILIKE '%401%'
  
  RETURN: All matches combined
```

### 3. Fixed SQLAssembler Cross-Domain Bug

**Location:** `/backend/utils/intelligence/sql_assembler.py` line 186

**Bug:** Previous code dropped filters from non-primary tables
```python
# OLD (WRONG):
if primary_matches:
    term_matches = primary_matches  # DROPPED 401k filter!
    tables_from_matches = [primary_table]
```

**Fix:** Keep ALL term matches, build JOINs as needed
```python
# NEW (CORRECT):
# Use ALL term matches and build JOINs as needed
if len(tables_from_matches) == 1:
    logger.warning("SINGLE TABLE")
else:
    logger.warning("CROSS-DOMAIN: JOINs will be built")
```

### 4. Added Test Endpoint

**Location:** `/backend/routers/projects.py`

**Endpoint:** `POST /api/projects/{project_id}/resolve-terms?question=...`

**Returns:** Full resolution trace including:
- Parsed intent and domain
- Term matches (with source: term_index or reasoned)
- Assembled SQL
- Execution results

---

## FILES CHANGED

| File | Change |
|------|--------|
| `backend/utils/intelligence/metadata_reasoner.py` | **NEW** - MetadataReasoner class |
| `backend/utils/intelligence/term_index.py` | Updated `resolve_terms()` with reasoner fallback |
| `backend/utils/intelligence/sql_assembler.py` | Fixed cross-domain filter dropping |
| `backend/utils/intelligence/__init__.py` | Added MetadataReasoner exports |
| `backend/routers/projects.py` | Added `/resolve-terms` test endpoint |

---

## HOW TO TEST

### Step 1: Deploy to Railway

Push the changes to your repo. Railway will auto-deploy.

### Step 2: Run Required Recalcs (per RUNBOOK)

```bash
# Step 1: Analyze (populates _intelligence_lookups)
curl -X POST "https://hcmpact-xlr8-production.up.railway.app/api/intelligence/TEA1000/analyze" \
  -H "Content-Type: application/json" -d '{}'

# Step 2: Recalc (builds term index)
curl -X POST "https://hcmpact-xlr8-production.up.railway.app/api/projects/TEA1000/recalc" \
  -H "Content-Type: application/json" -d '{"what": ["terms", "entities", "joins"]}'
```

### Step 3: Test Term Resolution

```bash
# Test "employees in Texas" (term_index fast path)
curl -X POST "https://hcmpact-xlr8-production.up.railway.app/api/projects/TEA1000/resolve-terms?question=employees%20in%20Texas"

# Test "employees with 401k" (MetadataReasoner fallback)
curl -X POST "https://hcmpact-xlr8-production.up.railway.app/api/projects/TEA1000/resolve-terms?question=employees%20with%20401k"

# Test cross-domain: "employees in Texas with 401k"
curl -X POST "https://hcmpact-xlr8-production.up.railway.app/api/projects/TEA1000/resolve-terms?question=employees%20in%20Texas%20with%20401k"
```

### Expected Results

**For "employees in Texas with 401k":**
```json
{
  "term_matches": [
    {
      "term": "texas",
      "table": "Personal",
      "column": "stateprovince",
      "operator": "=",
      "match_value": "TX",
      "term_type": "synonym",
      "confidence": 1.0
    },
    {
      "term": "401k",
      "table": "Deductions",
      "column": "description",  // or similar
      "operator": "ILIKE",
      "match_value": "%401k%",
      "term_type": "reasoned",
      "confidence": 0.7
    }
  ],
  "assembly": {
    "success": true,
    "sql": "SELECT ... FROM Personal t0 JOIN Deductions t1 ON t0.employee_number = t1.employee_number WHERE t0.stateprovince = 'TX' AND t1.description ILIKE '%401k%'",
    "tables": ["Personal", "Deductions"],
    "joins": [{"table1": "Personal", "col1": "employee_number", "table2": "Deductions", "col2": "employee_number"}]
  }
}
```

---

## ARCHITECTURE SUMMARY

```
User Question
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│  TERM RESOLUTION (2-layer)                                  │
│                                                             │
│  Layer 1: term_index (fast, O(1))                          │
│    Known mappings: Texas→TX, Active→A, description→code    │
│                                                             │
│  Layer 2: MetadataReasoner (fallback)                      │
│    Queries existing metadata to find where to look         │
│    No pre-computation. No LLM. Just reasoning.             │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│  SQL ASSEMBLER (deterministic)                              │
│                                                             │
│  - Takes resolved term matches                              │
│  - Finds JOIN paths via _column_mappings + join_priority   │
│  - Builds SQL with ALL filters (cross-domain fixed)        │
│  - NO LLM                                                   │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│  EXECUTION + SYNTHESIS                                      │
│                                                             │
│  - Execute SQL against DuckDB                               │
│  - LLM ONLY for analysis/synthesis of results               │
│  - NOT for SQL generation                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## NEXT STEPS

After confirming this works:

1. **Triangulate with Vector Data** - Use the resolved filters to also query ChromaDB for relevant Reference/Regulatory/Compliance context

2. **World-Class Synthesis** - Send structured data + vector context to LLM for consultative analysis

3. **Remove Cruft** - Deprecate the old LLM SQL generation path in `sql_generator.py` and simplify `query_resolver.py`

---

## CRITICAL REMINDER

The MetadataReasoner uses metadata that is populated by:
- `/api/intelligence/{project}/analyze` → `_table_classifications`, `_intelligence_lookups`
- `/api/projects/{project}/recalc` → `_term_index`, `_entity_tables`, `join_priority`

**If these haven't run, the reasoner won't have metadata to query!**
