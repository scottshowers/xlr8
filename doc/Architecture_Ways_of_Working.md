# XLR8 Architecture & Ways of Working

**Last Updated:** 2026-01-11  
**Purpose:** Single source of truth for how XLR8 works. Read this FIRST.

---

## SECTION A: CURRENT STATE & ROADMAP

### A.1 Where We Are

| Milestone | Status | Notes |
|-----------|--------|-------|
| Data Pipeline | ✅ DONE | Upload → DuckDB + metadata tables |
| Context Graph | ✅ DONE | Hub-spoke relationships detected |
| Project Intelligence | ✅ DONE | 66 organizational metrics computed |
| QueryResolver | ✅ DONE | Handles ~5 deterministic patterns |
| SqlGenerator | ⚠️ 80% | Has intelligence, needs testing |
| Clarification System | ✅ FIXED (v9.1) | Auto-detects filters, syncs to SqlGenerator |
| Synthesizer | ⚠️ 70% | Template works, LLM overlay needs tuning |
| Consultative Responses | ⚠️ UNBLOCKED | Can now test with working clarification |

### A.2 What's Blocking Us

**#1 BLOCKER: ~~Clarification Loop~~ FIXED**
- ~~User says "active employees with salary over 50000"~~
- ~~System asks for status clarification anyway~~
- v9.0 now auto-detects "active" → status='A'
- Uses domain-agnostic vocabulary built from filter_candidates

**#2 BLOCKER: ~~Config vs Employee Table Selection~~ FIXED**
- ~~"list employees with 401k" selected CONFIG deductions table~~
- ~~Config table has no employee_number, so JOINs fail~~
- v4.1 fix in TableSelector: `is_config_question` no longer triggers on data domain questions
- v4.2 fix: WRONG TABLE NAME DOMAIN penalty skips tables matching question_domain
  - Before: Deductions table got -150 for having "deductions" in name when question had "employees"
  - After: Skip penalty because question_domain is "deductions" (from 401k)
  - Deductions table now scores higher than Personal table

**#3 BLOCKER: ~~QueryResolver Blocking Cross-Domain~~ FIXED**
- ~~QueryResolver handled "employees with 401k" as single-domain employee query~~
- ~~Never reached SqlGenerator which has JOIN logic~~
- v5.0 fix: QueryResolver now detects multiple domains and returns success=False
- Cross-domain queries fall through to SqlGenerator for JOIN handling

**#4: Synthesizer Quality**
- Template responses work (lists data)
- LLM overlay produces generic consultant-speak
- Hub usage analysis exists but needs tuning

### A.3 Immediate Roadmap

| Priority | Task | Hours | Why |
|----------|------|-------|-----|
| ~~P0~~ | ~~Fix clarification loop~~ | ~~2h~~ | ✅ DONE - v9.0 |
| P1 | Test SqlGenerator intelligence | 2h | Validate schema hints work |
| P2 | Tune synthesizer LLM overlay | 4h | Real consultative responses |
| P3 | Hub usage in synthesis | 2h | "5 of 20 codes unused" insights |

---

## SECTION B: QUERY FLOW (How Chat Actually Works)

### B.1 The Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    POST /api/chat/unified                        │
│                    (unified_chat.py:1634)                        │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   IntelligenceEngineV2                           │
│                   (engine.py v8.0)                               │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 1. Load context (vocabulary, dimensions, scope, metrics) │    │
│  │ 2. Check if clarification needed                         │    │
│  │ 3. Route to QueryResolver or SqlGenerator               │    │
│  │ 4. Gather Five Truths                                   │    │
│  │ 5. Synthesize response                                  │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐      ┌───────────────┐      ┌───────────────┐
│ QueryResolver │      │ SqlGenerator  │      │ Clarification │
│ (139K, 5      │      │ (61K, LLM     │      │ (in engine)   │
│  patterns)    │      │  generates)   │      │               │
└───────────────┘      └───────────────┘      └───────────────┘
        │                       │
        └───────────┬───────────┘
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                      GATHERERS                                   │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────────┐  │
│  │ Reality │ │ Intent  │ │ Config  │ │Reference│ │Regulatory │  │
│  │(DuckDB) │ │(parsed) │ │(hubs)   │ │(Chroma) │ │(Chroma)   │  │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └───────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      SYNTHESIZER                                 │
│                      (92K)                                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Decision: Template only? Or LLM overlay?                 │    │
│  │ • Inventory questions → Template + hub usage            │    │
│  │ • Analysis questions → Template + LLM synthesis         │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
                         JSON Response
```

### B.2 Query Routing Decision

```
User Question
     │
     ▼
┌─────────────────────┐
│ Is employee-related │
│ AND status unknown? │
└─────────────────────┘
     │
     ├─ YES → Return clarification_needed
     │        (BROKEN: loops even when status known)
     │
     └─ NO ──┬─────────────────────────────────┐
             │                                 │
             ▼                                 ▼
    ┌─────────────────┐              ┌─────────────────┐
    │ QueryResolver   │              │ SqlGenerator    │
    │ Can handle?     │              │ (LLM-based)     │
    │ • COUNT(*)      │              │ Complex queries │
    │ • LIST entities │              │ Numeric filters │
    │ • GROUP BY dim  │              │ Multi-table     │
    │ • Simple filter │              │ Cross-domain    │
    └─────────────────┘              └─────────────────┘
```

### B.3 The Five Truths

| Truth | Source | Gatherer File | What It Provides |
|-------|--------|---------------|------------------|
| **Reality** | DuckDB | `gatherers/reality.py` | Actual data, counts, distributions |
| **Intent** | Question parse | `gatherers/intent.py` | What user wants (entities, filters) |
| **Configuration** | Hub tables | `gatherers/configuration.py` | How it's set up (codes, rules) |
| **Reference** | ChromaDB | `gatherers/reference.py` | Vendor docs (how it should work) |
| **Regulatory** | ChromaDB | `gatherers/regulatory.py` | Compliance requirements |
| **Compliance** | Computed | `gatherers/compliance.py` | Config vs Regulatory gaps |

---

## SECTION C: KEY COMPONENTS

### C.1 Intelligence Engine (engine.py - 75K)

**Version:** 8.0.0  
**Role:** Orchestrator - thin layer that coordinates everything

**Key Methods:**
- `ask(question, mode)` - Main entry point
- `_check_clarification_needed()` - Status/scope clarification
- `_gather_truths()` - Calls all gatherers
- `load_context()` - Loads vocabulary, dimensions, metrics

**Loads on Init:**
- Project Intelligence (66 metrics)
- Vocabulary (customer terminology)
- Filter candidates (status, location, company columns)
- Context graph (hub-spoke relationships)

### C.2 QueryResolver (query_resolver.py - 139K)

**Role:** Deterministic query handler for simple patterns

**Handles:**
- `COUNT(*)` questions ("how many employees")
- `LIST` questions ("show me earnings codes")
- `GROUP BY` questions ("breakdown by location")
- Simple filters ("in Texas", "active only")

**Does NOT Handle:**
- Numeric filters ("salary > 50000")
- Complex joins
- Cross-domain queries
- Date range queries

### C.3 SqlGenerator (sql_generator.py - 61K)

**Role:** LLM-based SQL generation for complex queries

**Intelligence Available:**
- Schema with comments (column types + filter hints)
- Translation hints ("Texas" → "TX")
- Join paths from context graph
- Lookups for code→description

**Current State:** Has intelligence wired in, but clarification bug prevents testing.

### C.4 Synthesizer (synthesizer.py - 92K)

**Role:** Converts gathered truths into human response

**Modes:**
1. **Template Only** - For inventory/listing questions
2. **LLM Overlay** - For analysis questions needing interpretation

**Hub Usage Analysis:**
- Finds hub table for query domain
- Looks up Reality spokes (employee tables)
- Counts actual usage vs configured
- "5 of 20 earnings codes in use"

### C.5 Project Intelligence (project_intelligence.py - 3.4K lines)

**Role:** Pre-compute customer facts on upload

**Computes:**
- Active headcount (with dimensional breakdowns)
- Hub usage percentages
- Coverage metrics (config vs reality)
- Dimensional structure (country, company, org levels)

**Stores In:** `_organizational_metrics` table

**API:** `GET /api/intelligence/{project}/metrics`

---

## SECTION D: KNOWN ISSUES & FIXES

### D.1 Clarification Loop - FIXED in v9.0

**Location:** `engine.py` in `_check_clarification_needed()`

**Was:**
```
User: "active employees with salary over 50000"
System: "Which employees? Active, Terminated, or All?"  ← WRONG
```

**Now (v9.0):**
```
User: "active employees with salary over 50000"
System: [auto-detects 'active' → status='A'] → proceeds to SqlGenerator
```

**How It Works:**
1. `_build_filter_vocabulary()` creates term→value mappings from filter_candidates
2. `_detect_filters_from_question()` scans question for known terms
3. Auto-populates `confirmed_facts` before asking for clarification
4. Uses word boundaries to avoid false matches ("proactive" ≠ "active")

**Domain-Agnostic Design:**
- Status mappings: 'active'→'A', 'terminated'→'T' (common HCM patterns)
- Location mappings: State names → codes from actual data
- Lookups: Uses project_intelligence.lookups for data-driven mappings
- Direct matching: Any value in filter_candidates can be matched

### D.2 Synthesizer LLM Quality

**Location:** `synthesizer.py` in `_synthesize_with_llm()`

**Symptom:** Generic consultant-speak instead of data-driven insights

**Root Cause:** LLM prompt has grounding facts but doesn't enforce using them

**Fix Approach:** Stronger prompt structure:
```
YOU KNOW THESE FACTS (use them):
- Active headcount: 3,976
- 5 of 20 earnings codes unused

DO NOT make generic observations.
DO cite specific numbers from the data.
```

---

## SECTION E: REFERENCE

### E.1 File Locations

| Component | Path | Size |
|-----------|------|------|
| Engine | `backend/utils/intelligence/engine.py` | 75K |
| QueryResolver | `backend/utils/intelligence/query_resolver.py` | 139K |
| SqlGenerator | `backend/utils/intelligence/sql_generator.py` | 61K |
| Synthesizer | `backend/utils/intelligence/synthesizer.py` | 92K |
| TableSelector | `backend/utils/intelligence/table_selector.py` | 45K |
| Project Intelligence | `backend/utils/project_intelligence.py` | 3.4K lines |
| Consultative Synthesis | `backend/utils/consultative_synthesis.py` | 1.3K lines |
| Unified Chat Router | `backend/routers/unified_chat.py` | 148K |

### E.2 DuckDB Metadata Tables

| Table | Purpose |
|-------|---------|
| `_schema_metadata` | Table entity_type, category |
| `_column_mappings` | Semantic types, hub/spoke links |
| `_column_profiles` | Stats, distinct values, filter_category |
| `_table_registry` | Table classifications |
| `_intelligence_lookups` | Code → description mappings |
| `_organizational_metrics` | Pre-computed customer metrics |
| `_project_intelligence` | Analysis summary |

### E.3 API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /api/chat/unified` | Main chat entry |
| `GET /api/intelligence/{project}/metrics` | Get 66 metrics |
| `POST /api/intelligence/{project}/analyze` | Trigger analysis |
| `GET /api/data-model/context-graph/{project}` | Hub/spoke graph |
| `GET /api/bi/schema/{project}` | Table schemas |

### E.4 Production URLs

- **Backend:** `https://hcmpact-xlr8-production.up.railway.app/`
- **Frontend:** Vercel deployment

---

## SECTION F: WAYS OF WORKING

### F.1 Non-Negotiables

1. **Full file replacements only** - No patches, no "add at line X"
2. **Test before deploy** - Syntax check at minimum
3. **Follow the Five Truths** - Every question gathers all truths
4. **Domain-agnostic** - No hardcoded UKG logic in core
5. **Local LLMs first** - DeepSeek for SQL, Mistral for synthesis, Claude API as fallback

### F.2 Before Starting Work

1. Read this document (Section A for status)
2. Check blockers - don't build on broken foundation
3. Identify which component you're touching
4. Understand the query flow (Section B)

### F.3 After Completing Work

1. Update Section A status
2. Document any new issues in Section D
3. Test end-to-end, not just the component

---

## SECTION G: PARKING LOT (Future)

- Data Page UX improvements
- Carbone for document generation
- Compliance gap reporting
- SOC 2 / hosting considerations
- GitHub integration
- Unrecognized hubs UI
- PDF export for reports
- Multi-tenant project isolation
- Playbook Builder UI (exit blocker - 12h estimate)
