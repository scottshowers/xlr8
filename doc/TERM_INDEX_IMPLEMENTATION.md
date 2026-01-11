# Term Index Implementation Complete
## Session: 2026-01-11

---

## What Was Built

### 1. New Module: `backend/utils/intelligence/term_index.py`

The core term index module with:

**Classes:**
- `TermIndex` - Manages term index for deterministic query resolution
- `TermMatch` - Data class for matched term results
- `JoinPath` - Data class for join path results
- `VendorSchemaLoader` - Loads and provides access to vendor JSON schemas

**Key Methods:**
```python
# During column profiling (load-time):
index.build_location_terms(table, column, values)  # "TX" → "texas" synonyms
index.build_status_terms(table, column, values)    # "A" → "active" synonyms
index.build_lookup_terms(table, column, lookups, type)  # "Medical Insurance" → "MED"
index.build_value_terms(table, column, values)     # Generic categorical indexing

# At query time:
matches = index.resolve_terms(['texas', '401k'])   # O(1) lookup
join_path = index.get_join_path('Personal', 'Deductions')  # Priority-based

# Management:
index.set_all_join_priorities()  # Apply priorities from semantic types
stats = index.get_stats()        # Get index statistics
index.clear()                    # Clear all data for project
```

**Tables Created:**
```sql
-- Term index for query resolution
CREATE TABLE _term_index (
    project, term, term_type, table_name, column_name,
    operator, match_value, domain, entity, confidence, source, vendor
);

-- Entity to table mapping
CREATE TABLE _entity_tables (
    project, entity, table_name, is_primary, table_type, row_count, vendor
);

-- Enhancement to _column_mappings
ALTER TABLE _column_mappings ADD COLUMN join_priority INTEGER;
```

---

### 2. Integration: `utils/structured_data_handler.py`

Modified `_store_column_profile()` to automatically populate term index:

```python
# When a column profile is stored with a filter_category:
if filter_category == 'location':
    term_index.build_location_terms(...)  # Adds state synonyms
elif filter_category == 'status':
    term_index.build_status_terms(...)    # Adds status synonyms
else:
    term_index.build_value_terms(...)     # Indexes raw values
```

Added helper method:
```python
def get_term_index(self, project: str) -> TermIndex
```

---

### 3. New Endpoint: `POST /api/projects/{project_id}/recalc`

Recalculates indexes without re-uploading files:

```bash
curl -X POST https://your-api/api/projects/TEA1000/recalc \
  -H "Content-Type: application/json" \
  -d '{"what": ["terms", "entities", "joins"]}'
```

Response:
```json
{
  "success": true,
  "project_id": "TEA1000",
  "recalculated": ["terms", "entities", "joins"],
  "stats": {
    "location_terms": 156,
    "status_terms": 42,
    "lookup_terms": 89,
    "entity_mappings": 73,
    "join_priorities": 245
  }
}
```

---

### 4. Vendor Schema Files (Copied to `/config/`)

```
/config/
├── ukg_pro_schema_v3.json           # 105 hubs, 1950 lines
├── ukg_wfm_dimensions_schema_v1.json # 113 hubs
├── ukg_ready_schema_v1.json         # 104 hubs
├── ukg_family_unified_vocabulary.json # 303 unified concepts
├── ukg_schema_reference.json        # (existing)
├── ukg_spoke_patterns.json          # (existing)
└── ukg_vocabulary_seed.json         # (existing)
```

---

## How It Works

### Before (Query Time - SLOW)
```
User: "employees in Texas with 401k"
↓
Scan 73 tables looking for "texas"
↓
Hardcoded US_STATE_CODES dict
↓
LLM tries to build JOIN SQL
↓
Wrong tables, wrong joins
↓
"No data found"
```

### After (Load Time + Query Time - FAST)
```
LOAD TIME (during profiling):
- Detect filter_category='location' on state column
- Build terms: "tx" → value, "texas" → synonym
- Set join_priority=100 for employee_number

QUERY TIME:
User: "employees in Texas with 401k"
↓
Tokenize → ['texas', '401k']
↓
Lookup _term_index → texas → Personal.stateprovince='TX'
↓
Lookup _term_index → 401k → Deductions.deduction_code ILIKE '%401%'
↓
Lookup join_path → employee_number (priority 100)
↓
Assemble SQL (deterministic, no LLM)
↓
Execute → Results
```

---

## Files Changed

| File | Change |
|------|--------|
| `backend/utils/intelligence/term_index.py` | NEW - Core module |
| `backend/utils/intelligence/__init__.py` | Added exports |
| `utils/structured_data_handler.py` | Added term population during profiling |
| `backend/routers/projects.py` | Added `/recalc` endpoint |
| `config/*.json` | Added vendor schema files |

---

## Next Steps

1. **Deploy and Test**
   - Deploy updated backend to Railway
   - Run recalc on TEA1000: `POST /api/projects/TEA1000/recalc`
   - Verify term index populated: Check `_term_index` table

2. **Wire into Query Engine**
   - Modify `engine.py` to use `TermIndex.resolve_terms()` 
   - Modify `sql_generator.py` to use term matches instead of hardcoded states
   - Remove hardcoded `US_STATE_CODES` from sql_generator.py and engine.py

3. **Test Query Resolution**
   - "employees in Texas" → Should resolve via term index
   - "active employees with 401k" → Should find both terms
   - Cross-domain queries should work

---

## Glossary

| Term | Definition |
|------|------------|
| Term Index | DuckDB table mapping search terms to SQL filters |
| Join Priority | Numeric score (0-100) determining which column to prefer for JOINs |
| Entity Table | Mapping of entity types (employee, company) to actual tables |
| Vendor Schema | JSON file defining hub types, column patterns, spoke relationships |

---

## Why The Last Session Compacted

The previous session was **generating vendor JSON files** instead of **reading your provided files**. Each JSON file with 100+ hubs is thousands of tokens. Generating 7 of them = context blowout.

This session: **read-only** for JSON files. The module just loads them via `VendorSchemaLoader`.

---

## Version

- term_index.py: v1.0
- structured_data_handler.py: v5.15 (added term index integration)
- projects.py: Added recalc endpoint
