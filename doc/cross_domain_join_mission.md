# MISSION: Cross-Domain JOIN Queries via Context Graph

## OBJECTIVE
Make SqlGenerator detect when queries span multiple tables and use Context Graph hub/spoke relationships to generate JOINs automatically. This is THE differentiator for XLR8 - without this, it's just a fancy SQL builder.

## THE PROBLEM (TRACED)

Query: "employees in Texas with 401k"

**What SHOULD happen:**
```
1. Detect: "Texas" → location filter, "401k" → deduction filter  
2. Context Graph lookup: Personal has stateprovince, Deductions has deductionbenefit_code
3. Context Graph: Both share employee_number hub
4. Generate: SELECT ... FROM Personal p 
             JOIN Deductions d ON p.employee_number = d.employee_number
             WHERE p.stateprovince = 'TX' AND d.deductionbenefit_code LIKE '%401%'
```

**What ACTUALLY happens:**
```
1. SqlGenerator._needs_join() checks for explicit patterns: "join with", "cross-reference", etc.
2. "employees in Texas with 401k" matches NONE of these patterns
3. _needs_join() returns False
4. _build_relationship_hints() is NEVER called (line 692-693)
5. LLM prompt has NO join information
6. LLM generates single-table SQL against whichever table matched best
```

## ROOT CAUSE

`sql_generator.py` line 118-147: `_needs_join()` uses hardcoded regex patterns:
```python
join_patterns = [
    r'\bwith\s+(their|the)\s+\w+\s+name',     # "employees with their department name"
    r'\bincluding\s+\w+\s+(name|description)', # "including location name"
    r'\bfull\s+(details|information)',         # "full details"
    ...
]
```

This NEVER detects "employees in Texas with 401k" as needing a JOIN.

## THE FIX

Replace pattern-based detection with **semantic detection**:

```python
def _needs_join(self, question: str, tables: List[Dict]) -> bool:
    """
    Detect if query concepts span multiple tables.
    
    NEW APPROACH: Check if question references columns/domains from 
    different tables that share a hub connection.
    """
    # 1. Get selected tables
    # 2. For each table, get its columns and domains
    # 3. Parse question for filter terms (Texas, 401k, active, etc.)
    # 4. Map filter terms to tables that contain matching columns
    # 5. If terms map to 2+ tables that share a hub → needs JOIN
```

The infrastructure EXISTS:
- `table_selector.get_join_path(t1, t2)` - finds join column via Context Graph ✅
- `_build_relationship_hints()` - builds LLM prompt hints ✅
- Context Graph has hub/spoke relationships ✅

We just need `_needs_join()` to return True when appropriate.

## KEY FILES

| File | Purpose | Key Methods |
|------|---------|-------------|
| `backend/utils/intelligence/sql_generator.py` | SQL generation | `_needs_join()` (line 118), `_generate_complex()` (line 644) |
| `backend/utils/intelligence/table_selector.py` | Table selection + Context Graph | `get_join_path()` (line 321), `_get_context_graph()` |
| `backend/utils/intelligence/query_resolver.py` | Intent parsing | `parse_intent()`, filter detection |

## CONTEXT GRAPH STRUCTURE

```python
{
    'hubs': [
        {'table': 'personal', 'column': 'employee_number', 'semantic_type': 'employee_id'},
        {'table': 'companies', 'column': 'company_code', 'semantic_type': 'company'}
    ],
    'relationships': [
        {'spoke_table': 'deductions', 'spoke_column': 'employee_number', 
         'hub_table': 'personal', 'semantic_type': 'employee_id'},
        {'spoke_table': 'earnings', 'spoke_column': 'employee_number',
         'hub_table': 'personal', 'semantic_type': 'employee_id'}
    ]
}
```

## TEST QUERIES

Run against TEA1000 project:

| Query | Expected Tables | Expected JOIN |
|-------|-----------------|---------------|
| "employees in Texas with 401k" | Personal + Deductions | ON employee_number |
| "employees missing direct deposit" | Personal + Direct Deposit | ON employee_number |
| "earnings by department" | Earnings + Personal (for dept) | ON employee_number |
| "deductions by location" | Deductions + Personal | ON employee_number |

```bash
# Test command
curl -s --max-time 120 -X POST "https://hcmpact-xlr8-production.up.railway.app/api/chat/unified" \
  -H "Content-Type: application/json" \
  -d '{"message": "employees in Texas with 401k", "project": "TEA1000", "clarifications": {"scope": "all", "status": "active"}}'
```

## SUCCESS CRITERIA

1. Query "employees in Texas with 401k" returns employees filtered by BOTH location AND deduction
2. Generated SQL contains JOIN clause
3. No hardcoded table names - all discovered via Context Graph
4. Works for any multi-domain query, not just this example

## IMPLEMENTATION APPROACH

1. **Analyze question for filter concepts** - Extract terms like "Texas", "401k", "active"
2. **Map concepts to tables** - Which table has stateprovince? Which has deduction codes?
3. **Check if tables share hub** - Use `get_join_path()`
4. **If shared hub exists → build JOIN** - Use `_build_relationship_hints()` which already works

## DO NOT

- Hardcode table names or column names
- Add special cases for specific query patterns
- Break existing single-table queries
- Add new clarification prompts

## PRODUCTION ENDPOINT

```
https://hcmpact-xlr8-production.up.railway.app/
```

## STARTING POINT

Open `sql_generator.py` line 118: `_needs_join()` method. This is the gatekeeper that's blocking JOINs.
