# XLR8 ARCHITECTURE & EXECUTION GUIDE

**Version:** 4.0  
**Created:** January 2, 2026  
**Updated:** January 6, 2026  
**Purpose:** Single source of truth for what we're building and how

---

# SECTION A: CURRENT STATUS & ROADMAP

This section answers: "Where are we? What's next?"

---

## A.1 Executive Summary

**XLR8 is a SaaS implementation analysis platform** that delivers consultant-grade insights from customer data. The core value proposition: "Upload your HCM data, ask questions, get answers a $500/hr consultant would give."

**The breakthrough (January 5-6, 2026):** We discovered the platform was missing its intelligence layer. We had 2,451 pairwise relationships when we needed a Context Graph with ~50 hub/spoke connections. We also discovered that generic columns (like "code") can't be semantically typed without knowing what the table IS (`entity_type`).

**The pivot (January 6, 2026 - Phase 4 testing):** Hub detection was vocabulary-gated - only columns matching known semantic types could become hubs. This is backwards. **Data patterns should identify hubs, vocabulary should label them.** New approach: detect lookup table patterns from data, find relationships by value matching, then apply vocabulary labels.

**Current state:**
- Context Graph schema: ✅ Done
- Hub/spoke computation: 🔄 Needs rewrite (data-driven)
- Entity type foundation: ✅ Phase 1-3 Done
- Component integration: 🔄 Phase 4 In Progress (blocked on hub rewrite)
- Holistic extension: ⬜ Phase 8+

**Total foundation work: ~50 hours (revised). Then we build value.**

---

## A.2 The Roadmap At A Glance

```
┌─────────────────────────────────────────────────────────────────────┐
│                     FOUNDATION (~50 hours)                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  PHASE 1-7: DuckDB Foundation (~26 hours)                          │
│  ├── Phase 1: entity_type schema (2h)              ✅ DONE          │
│  ├── Phase 2: Semantic inference update (1h)       ✅ DONE          │
│  ├── Phase 3: API updates (1h)                     ✅ DONE          │
│  ├── Phase 4: Component integration (8h)           ✅ DONE          │
│  │   ├── Phase 4A: Data-driven hub detection (5h)  ✅ DONE          │
│  │   └── Phase 4B: Intelligence integration (3h)   ✅ DONE          │
│  ├── Phase 5: UI updates (3h)                      ⬜ TODO          │
│  ├── Phase 6: Query scoping (3h)                   ⬜ TODO          │
│  └── Phase 7: Migration + testing (5h)             ⬜ TODO          │
│                                                                     │
│  PHASE 8: Holistic Extension (~24 hours)                           │
│  ├── Phase 8A: Entity Registry (4h)                ✅ DONE          │
│  ├── Phase 8B: Entity Detection - ChromaDB (6h)    ✅ DONE          │
│  ├── Phase 8C: ChromaDB Integration (4h)           ✅ DONE          │
│  ├── Phase 8D: Unified Graph API (3h)              ⬜ TODO          │
│  ├── Phase 8E: Intelligence Integration (4h)       ✅ DONE          │
│  └── Phase 8F: UI Updates (3h)                     ⬜ TODO          │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                     VALUE ADD (After Foundation)                    │
├─────────────────────────────────────────────────────────────────────┤
│  Phase 9+: External Integrations (Smartsheet, Email, etc.)         │
│  Playbook Builder polish                                            │
│  Compliance automation                                              │
│  UX improvements                                                    │
│  Export engine                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## A.3 Phase 1-7: DuckDB Foundation (Detailed)

### Phase 1: Foundation (2 hours) ✅ COMPLETE

| Task | File | Status |
|------|------|--------|
| Add `entity_type`, `category` to schema | `structured_data_handler.py` | ✅ Done |
| Add migration for existing DBs | `structured_data_handler.py` | ✅ Done |
| Create `_derive_entity_metadata()` | `structured_data_handler.py` | ✅ Done |
| Update `_store_single_table()` | `structured_data_handler.py` | ✅ Done |
| Parse "Sheet - SubTable" format | `_derive_entity_metadata()` | ✅ Done |

**Deliverable:** All new uploads have entity_type populated. ✅

### Phase 2: Semantic Inference (1 hour) ✅ COMPLETE

| Task | File | Status |
|------|------|--------|
| Update inference prompt with entity_type | `structured_data_handler.py` | ✅ Done |
| Dynamic vocabulary search (not hardcoded) | `_fallback_column_inference()` | ✅ Done |
| Test with "code" column in Change Reasons | Manual test | ✅ Done |

**Deliverable:** `code` in `termination_reasons` → `termination_reason_code` ✅

### Phase 3: API Updates (1 hour) ✅ COMPLETE

| Task | File | Status |
|------|------|--------|
| Include entity_type in BI schema | `bi_router.py` | ✅ Done |
| Include entity_type in classification | `classification_router.py` | ✅ Done |
| Include entity_type in context graph | `data_model.py` | ✅ Done |
| Include entity_type in dashboard | `dashboard.py` | ✅ Done |

**Deliverable:** All APIs return entity_type for tables. ✅

### Phase 4: Component Integration (8 hours) ✅ COMPLETE

#### Phase 4A: Data-Driven Hub Detection (5 hours) ✅ COMPLETE (Jan 7, 2026)

**Problem:** Current `compute_context_graph()` was vocabulary-gated. Only columns with known semantic types could become hubs.

**Solution:** Detect hubs from DATA PATTERNS, find relationships by VALUE MATCHING, then apply vocabulary labels.

| Task | File | Est | Status |
|------|------|-----|--------|
| Rewrite `compute_context_graph()` | `structured_data_handler.py` | 4h | ✅ Done |
| Add `is_discovered` flag to mappings | `structured_data_handler.py` | 30m | ✅ Done |
| Add `auto_add_type()` to vocabulary | `semantic_vocabulary.py` | 30m | ⬜ Deferred (UI Phase) |

**Implementation Notes:**
- Data-driven scoring: code columns (+2), description columns (+2), uniqueness (+2), size (+1), entity_type patterns (+1), truth_type=configuration (+1)
- Threshold: Score >= 4 = hub candidate
- Value matching: MIN_COVERAGE_PCT = 20% or is_subset = TRUE
- Deduplication: Same semantic_type → prefer configuration, then score, then cardinality
- `is_discovered` flag tracks auto-discovered types for UI naming

**Algorithm:** See lines 2185-2687 in `structured_data_handler.py`

#### Phase 4B: Remaining Integration (3 hours)

| Task | File | Est | Status |
|------|------|-----|--------|
| Intelligence Engine scopes to active values | `intelligence/engine.py` | 1h | ✅ Done |
| SQL Generator uses graph for auto-filtering | `sql_generator.py` | 1h | ✅ Done |
| Gap Detection from graph coverage | `playbook_framework.py` | 30m | ✅ Done |
| Consultative synthesis uses graph | `consultative_synthesis.py` | 30m | ✅ Done |

**Deliverable:** Query "Show me W2 issues" returns scoped, intelligent answer.

### Phase 5: UI Updates (3 hours) ⬜ TODO

| Task | File | Est | Status |
|------|------|-----|--------|
| Data Model UI shows hub/spoke hierarchy | `data_model.py` + frontend | 2h | ⬜ TODO |
| DataExplorer shows entity_type | `DataExplorer.jsx` | 30m | ⬜ TODO |
| AnalyticsPage shows entity_type | `AnalyticsPage.jsx` | 30m | ⬜ TODO |
| Unrecognized Hubs UI (name discovered hubs) | Frontend | Parked | ⬜ TODO |

**Deliverable:** UI shows data hierarchy, not flat list.

### Phase 6: Query Scoping (3 hours) ⬜ TODO

| Task | File | Est | Status |
|------|------|-----|--------|
| Chain context through graph | Multiple | 3h | ⬜ TODO |
| "W2 → US → 2 companies" works | End-to-end | Included | ⬜ TODO |

**Deliverable:** Complex scoped queries work automatically.

### Phase 7: Migration + Testing (5 hours) ⬜ TODO

| Task | File | Est | Status |
|------|------|-----|--------|
| Backfill entity_type for existing TEA1000 | Script | 1h | ⬜ TODO |
| Recompute context graph for TEA1000 | Script | 30m | ⬜ TODO |
| Verify all lookup tables become hubs | Manual test | 30m | ⬜ TODO |
| Test full query flow | Manual test | 2h | ⬜ TODO |
| Edge cases and bug fixes | Various | 1h | ⬜ TODO |

**Deliverable:** TEA1000 has complete, working Context Graph.

---

## A.4 Phase 8: Holistic Extension (Detailed)

### Phase 8A: Entity Registry (4 hours) ✅ COMPLETE (Jan 7, 2026)

| Task | File | Status |
|------|------|--------|
| Create entity_registry table in Supabase | Migration | ✅ Done |
| Create entity_references table in Supabase | Migration | ✅ Done |
| Create `EntityRegistry` class | `backend/utils/entity_registry.py` | ✅ Done |
| Register DuckDB hubs in entity registry | `structured_data_handler.py` | ✅ Done |
| Register DuckDB spokes in entity registry | `structured_data_handler.py` | ✅ Done |
| Register ChromaDB mentions in entity registry | `utils/rag_handler.py` | ✅ Done |

**Implementation Notes:**
- Supabase tables: `entity_registry` (master list), `entity_references` (where entities appear)
- Views: `entity_summary`, `entity_gaps`
- EntityRegistry class: singleton pattern, graceful degradation if Supabase unavailable
- Auto-registration during upload: DuckDB (context graph) and ChromaDB (chunk metadata)

**Deliverable:** All entities tracked in Supabase registry. ✅

### Phase 8B: Entity Detection - ChromaDB (6 hours) ✅ COMPLETE (Jan 7, 2026)

| Task | File | Status |
|------|------|--------|
| Create `EntityDetector` class | `backend/utils/entity_detector.py` | ✅ Done |
| Value matching detection | `entity_detector.py` | ✅ Done |
| LLM-based semantic detection | `entity_detector.py` | ⬜ Deferred (not needed) |
| Pattern matching for known formats | `entity_detector.py` | ✅ Done (15 hub patterns) |
| Unit tests for detection | `tests/test_entity_detector.py` | ⬜ Deferred |

**Implementation Notes:**
- Regex patterns + keywords + context hints for 15 hub types
- Confidence scoring (0.0-1.0) based on match strength
- Loads vendor vocabulary from `config/ukg_vocabulary_seed.json`
- Returns `hub_references`, `primary_hub`, `hub_confidence`

**Deliverable:** Detector identifies entity references in unstructured text. ✅

### Phase 8C: ChromaDB Integration (4 hours) ✅ COMPLETE (Jan 7, 2026)

| Task | File | Status |
|------|------|--------|
| Add entity detection to `add_document()` | `utils/rag_handler.py` | ✅ Done |
| Store entity refs in registry during ingestion | `utils/rag_handler.py` | ✅ Done (in chunk metadata) |
| Update chunk metadata schema | `utils/rag_handler.py` | ✅ Done |
| Backfill existing chunks (optional) | Script | ⬜ Skipped (re-upload easier) |

**Implementation Notes:**
- Entity detection runs automatically during `add_document()`
- Chunk metadata includes: `hub_references`, `primary_hub`, `hub_confidence`
- `hub_references` stored as comma-separated string (ChromaDB metadata limitation)

**Deliverable:** New ChromaDB documents have entity references. ✅

### Phase 8D: Unified Graph API (3 hours)

| Task | File | Status |
|------|------|--------|
| Create `get_unified_context_graph()` | `structured_data_handler.py` | ⬜ TODO |
| Create `query_entity()` | `backend/utils/entity_query.py` | ⬜ TODO |
| API endpoint for entity query | `backend/routers/data_model.py` | ⬜ TODO |
| Cross-storage gap detection | `entity_query.py` | ⬜ TODO |

**Deliverable:** API returns unified view of entity across all storage.

### Phase 8E: Intelligence Integration (4 hours) ✅ COMPLETE (Jan 7, 2026)

| Task | File | Status |
|------|------|--------|
| Update Intelligence Engine to use unified graph | `intelligence/engine.py` | ✅ Done |
| Update gatherers to include semantic context | `intelligence/gatherers/*.py` | ✅ Done |
| Update consultative synthesis | `consultative_synthesis.py` | ✅ Done |
| Works without DuckDB (ChromaDB-only mode) | `unified_chat.py` | ✅ Done |

**Implementation Notes:**
- Fixed: `load_context()` now called even without DuckDB tables
- Five Truths triangulation working: Reality + Configuration + Reference + Regulatory
- All 6 gatherers operational
- System tagging for vendor docs (UKG Pro, Workday, etc.)

**Deliverable:** "What do we know about X?" returns holistic answer. ✅

### Phase 8F: UI Updates (3 hours)

| Task | File | Status |
|------|------|--------|
| Show semantic references in Context Graph UI | Frontend | ⬜ TODO |
| Entity detail view (hub + spokes + docs) | Frontend | ⬜ TODO |
| Cross-reference links (click entity → see all) | Frontend | ⬜ TODO |

**Deliverable:** UI shows unified entity view.

---

## A.4.1 Infrastructure Improvements (Jan 7, 2026)

Work completed that wasn't in the original plan but was necessary:

### OCR Support for Image-Based PDFs
| Task | File | Status |
|------|------|--------|
| Add Tesseract OCR fallback | `utils/text_extraction.py` | ✅ Done |
| Add OCR to standards processor | `backend/utils/standards_processor.py` | ✅ Done |
| Add OCR to upload router | `backend/routers/upload.py` | ✅ Done |
| Add OCR to smart PDF analyzer | `backend/utils/smart_pdf_analyzer.py` | ✅ Done |
| Docker config for tesseract | `Dockerfile` | ✅ Done |

**Why:** "Print to PDF" documents are image-based, not text-based. pdfplumber/PyMuPDF return 0 chars.

### Smart Router Truth Type Fix
| Task | File | Status |
|------|------|--------|
| Route `reference` → SEMANTIC (RAG only) | `backend/routers/smart_router.py` | ✅ Done |
| Route `regulatory/compliance` → STANDARDS (rules) | `backend/routers/smart_router.py` | ✅ Done |
| Reference docs skip table extraction | `backend/utils/smart_pdf_analyzer.py` | ✅ Done |
| Tabular check gates Vision AI | `backend/utils/smart_pdf_analyzer.py` | ✅ Done |

**Why:** Vendor guides (Locations Guide, etc.) shouldn't go through rule extraction OR table extraction. Only config data needs DuckDB, only DOL/FLSA/regulatory docs need rules.

### System Tagging for Vendor Docs
| Task | File | Status |
|------|------|--------|
| System parameter in upload flow | `backend/routers/upload.py` | ✅ Done |
| Auto-detect system from filename | `utils/rag_handler.py` | ✅ Done |
| System dropdown UI (from Supabase) | `frontend/src/pages/DataPage.jsx` | ✅ Done |
| Filter by system in ReferenceGatherer | `backend/utils/intelligence/gatherers/reference.py` | ✅ Done |

**Why:** UKG project shouldn't see Workday docs. System tagging enables filtering.

### Cleanup Infrastructure
| Task | File | Status |
|------|------|--------|
| Nuclear ChromaDB clear endpoint | `backend/routers/cleanup.py` | ✅ Done |
| Nuclear rules/documents clear endpoint | `backend/routers/cleanup.py` | ✅ Done |
| Combined semantic clear endpoint | `backend/routers/cleanup.py` | ✅ Done |
| Fix ChromaDB path mismatch | `backend/routers/cleanup.py` | ✅ Done |
| ChromaDB singleton pattern | `utils/rag_handler.py` | ✅ Done |

**Endpoints:**
- `DELETE /api/status/chromadb/all` - Clear all ChromaDB chunks
- `DELETE /api/status/rules/all` - Clear all rules + documents
- `DELETE /api/status/semantic/all` - Clear everything (combined)

---

## A.5 QUERY ENGINE - CRITICAL PATH (Jan 10, 2026) ✅ COMPLETE

**Status:** ✅ ALL CRITERIA MET - Query engine fully operational.

Everything flows through the same pipe: Chat, Playbooks, BI Builder, Exports. Query engine now handles geographic filtering, SUM/LIST patterns, cross-table JOINs, and synthesis that uses actual results.

### A.5.1 Current State Assessment

| Component | Status | What Works | What's Broken |
|-----------|--------|------------|---------------|
| Dimension Resolution | 70% | Exact matches (TNC, Pasadena, manufacturing) | Fuzzy matching ("Texas" → TX codes) |
| JOIN Strategy | 0% | Basic LEFT JOINs | Should be INNER for filters, LEFT for lookups |
| Query Patterns | 20% | COUNT only | SUM, LIST, date filtering missing |
| Consultant Synthesis | 0% | Template fallback | LLM returns garbage (data dumps, not insights) |

### A.5.2 The Problem

**Dimension Resolution:**
- "How many employees in TNC" → ✅ Works (exact code match)
- "How many employees in Pasadena" → ✅ Works (description contains "Pasadena")
- "How many employees in Texas" → ❌ Returns ALL employees (no "Texas" in data, only "TX -")

**Query Patterns:**
- "How many employees" → ✅ COUNT works
- "Total earnings by pay group" → ❌ SUM not implemented
- "List employees in TNC" → ❌ LIST not implemented
- "Employees hired last year" → ❌ Date filtering not implemented

**Synthesis:**
```
WARNING:utils.llm_orchestrator:[SYNTHESIS] Garbage: low alpha ratio (0.38)
WARNING:utils.llm_orchestrator:[SYNTHESIS] qwen2.5-coder:14b returned garbage
```
LLM regurgitates breakdown data instead of generating insights.

### A.5.3 Solution Architecture

**No Hardcoding.** All solutions must be data-driven and domain-agnostic.

#### 1. Fuzzy Dimension Resolution (4h)

**Current flow:**
```
"Texas" → search hub descriptions for "texas" → no match → no filter
```

**New flow:**
```
"Texas" → search hub descriptions for "texas" → no match
       → extract state codes from descriptions ("TX - Houston" → "TX")
       → map "Texas" → "TX" using state lookup
       → filter by codes starting with "TX"
```

**Implementation:**
- Add state/province/country normalization (built-in, not hardcoded per customer)
- Add partial matching (contains, starts-with)
- Add phonetic matching for typos
- Score and rank matches

**Files:** `backend/utils/intelligence/query_resolver.py`

#### 2. Query Pattern Expansion (4h)

**Current:** Only `QueryIntent.COUNT`

**New intents:**
```python
class QueryIntent(Enum):
    COUNT = "count"      # How many...
    SUM = "sum"          # Total, sum of...
    AVG = "average"      # Average...
    LIST = "list"        # List, show me, who are...
    BREAKDOWN = "breakdown"  # ...by department
    TREND = "trend"      # ...over time
```

**SQL generation per intent:**
- COUNT: `SELECT COUNT(DISTINCT employee_number)` ✅ exists
- SUM: `SELECT SUM(column)` where column detected from question
- LIST: `SELECT employee_number, name, ... LIMIT 100`
- BREAKDOWN: `GROUP BY dimension` ✅ exists (in breakdowns)
- TREND: `GROUP BY date_column ORDER BY date_column`

**Files:** `backend/utils/intelligence/query_resolver.py`

#### 3. JOIN Strategy (1h)

**Current:** All LEFT JOINs

**New:**
- Filter JOINs (WHERE clause uses joined table) → INNER JOIN
- Lookup JOINs (description enrichment only) → LEFT JOIN

**Example:**
```sql
-- "employees in TNC" - INNER because filtering on pay_group
SELECT COUNT(DISTINCT p.employee_number)
FROM personal p
INNER JOIN company c ON p.employee_number = c.employee_number
WHERE c.pay_group_code = 'TNC'

-- "employees by pay group" - LEFT because enriching output
SELECT c.pay_group_code, pg.pay_group, COUNT(*)
FROM personal p
JOIN company c ON p.employee_number = c.employee_number
LEFT JOIN pay_groups pg ON c.pay_group_code = pg.pay_group_code
GROUP BY c.pay_group_code, pg.pay_group
```

**Files:** `backend/utils/intelligence/query_resolver.py`

#### 4. Consultant Synthesis (4h)

**Problem:** LLM is formatting data, not analyzing it.

**Root cause:** Prompt tells LLM to "format the response" with the data we pass.

**Solution:** Two-phase synthesis:
1. **Data Summary** (deterministic) - Format numbers, percentages, breakdowns
2. **Insight Generation** (LLM) - "Given this data, what would a consultant highlight?"

**New prompt structure:**
```
You are a senior HCM consultant. The client asked: "{question}"

DATA SUMMARY (do not repeat this):
- Total: 3,254 active employees in TNC pay group
- This is 82% of all active employees (3,976)
- Top org levels: 1174 (654), 1110 (310), 1119 (261)

GENERATE INSIGHTS:
- What patterns are notable?
- What risks or opportunities exist?
- What questions should the client ask next?

Do NOT repeat the data summary. Provide consultant-level analysis only.
```

**Files:** `backend/utils/intelligence/synthesizer.py`, `utils/llm_orchestrator.py`

### A.5.4 Implementation Plan

| Task | Est | Priority | Status |
|------|-----|----------|--------|
| Fuzzy dimension resolution | 4h | P0 | ✅ DONE (Jan 10) |
| Query pattern expansion (SUM, LIST) | 4h | P0 | ✅ DONE (Jan 10) |
| JOIN strategy (INNER vs LEFT) | 1h | P1 | ✅ DONE (Jan 10) |
| Consultant synthesis fix | 4h | P0 | ✅ DONE (Jan 10) |
| **Total** | **13h** | | **COMPLETE** |

**Jan 10 Implementation Notes:**
- Geographic fallback: `normalize_geographic_term()` + `_try_direct_geographic_filter()` for state/province columns not in context graph
- SUM: Domain priority fix (earnings > employees), `_find_sum_column()` skips _code/_id columns, cross-table JOIN support
- LIST: Added status filter, geographic fallback, key column selection (not SELECT *)
- All JOINs use INNER for filters (already correct, made explicit)
- Synthesis: Fixed to use actual SQL result (`data_info['result_value']`) instead of pre-computed total (`reality_context['answer']`)

### A.5.5 Success Criteria

All of these must work before moving on:

```
✅ "How many employees in Texas" → 1,636 (filters to TX via stateprovince)
✅ "How many employees in TNC" → 3,254 
✅ "Total earnings for TNC employees" → $15,360.44 (JOIN earnings→company)
✅ "List employees in Pasadena" → Returns 20 employees
✅ "Employees hired in 2024" → 428 (date filter works)
✅ Response includes insights, not just data formatting
```

**ALL CRITERIA MET - Jan 10, 2026**

### A.5.6 Cleanup Tasks (After Query Engine Works)

| Task | Description | Status |
|------|-------------|--------|
| Remove relationship detector | `backend/utils/relationship_detector.py` - no longer needed | ⬜ TODO |
| Remove relationship API | `backend/routers/relationships.py` - if exists | ⬜ TODO |
| Remove relationship UI | Frontend relationship components | ⬜ TODO |
| Clean up dead relationship code | Any pairwise relationship logic | ⬜ TODO |

**Why:** We moved to Context Graph (hub/spoke). The old pairwise relationship system is dead code.

---

## A.6 Phase 9+: Future (Not Detailed Yet)

| Phase | Description | Estimate |
|-------|-------------|----------|
| Phase 9 | Smartsheet Integration | 8 hours |
| Phase 10 | Email Integration | 12 hours |
| Phase 11 | Meeting Notes Processing | 6 hours |
| Phase 12 | Decision/Action Tracking | 8 hours |
| Phase 13 | Timeline/History View | 6 hours |

---

## A.6 Success Criteria (Phase 1-7)

After Phase 7, these must all be true:

- [ ] All lookup tables detected as hubs (not just vocabulary-matched ones)
- [ ] Hubs discovered by data patterns, labeled by vocabulary
- [ ] Unknown hubs auto-added to vocabulary with is_discovered flag
- [ ] Context Graph shows 20+ hubs (was 14 with vocabulary-gating)
- [ ] Query "Show me termination reason gaps" returns hub/spoke/gap breakdown
- [ ] UI shows hierarchical view, not flat tables
- [ ] "W2 issues" scopes to US companies automatically

---

## A.7 Conversation Continuity

When starting a new conversation:

```
Continue XLR8 FIVE TRUTHS implementation.
Reference: Architecture_Ways_of_Working.md Section A

Current status: Foundation phases nearly complete
Last completed: 
  - Phase 1-4 (DuckDB Foundation) ✅
  - Phase 8A (Entity Registry) ✅
  - Phase 8B (Entity Detection) ✅
  - Phase 8C (ChromaDB Integration) ✅
  - Phase 8E (Intelligence Integration) ✅
  - Infrastructure: OCR, routing fix, cleanup endpoints, system tagging
  
Remaining Foundation:
  - Phase 5: UI updates (3h)
  - Phase 6: Query scoping (3h)  
  - Phase 7: Migration + testing (5h)
  - Phase 8D: Unified Graph API (3h)
  - Phase 8F: UI Updates (3h)
  
EXIT BLOCKER: Playbook Builder UI (12h)

Start by viewing Section A.2 for the roadmap.
```

Update checkboxes (⬜ → ✅) as tasks complete.

---

# SECTION B: THE ARCHITECTURE

This section answers: "How does it work?"

---

## B.1 The Context Graph

**The Context Graph is not a feature. It IS the platform.**

XLR8's entire value proposition is context-aware analysis. The Context Graph is how we deliver that. Without it, we're just a fancy ETL tool with a chatbot.

### Hub/Spoke Model (Data-Driven)

**OLD MODEL (Vocabulary-Gated):**
```
Vocabulary → Semantic Type → Hub Candidate → Check Data
```

**NEW MODEL (Data-Driven):**
```
Data Patterns → Hub Candidate → Value Matching → Vocabulary Labels
```

For each discovered hub:

```
HUB = Table matching lookup pattern (code+description, high uniqueness)
SPOKES = Tables with columns whose values overlap hub values
```

**Example:**
```
union_code (discovered, not in original vocabulary):
├── HUB: Unions (45 values)                    ← Detected by pattern
├── SPOKE: Employee (12 values, 27% coverage)  ← Found by value match
└── SPOKE: Deductions (8 values, 18% coverage) ← Found by value match
```

### Storage

```sql
_column_mappings:
├── semantic_type          -- 'company_code', 'job_code', 'union_code'
├── is_hub                 -- TRUE if this is THE hub for its semantic_type
├── is_discovered          -- NEW: TRUE if auto-detected (not in original vocab)
├── hub_table              -- If spoke, which table is the hub?
├── hub_column             -- If spoke, which column in hub?
├── hub_cardinality        -- How many values in the hub? (13)
├── spoke_cardinality      -- How many values in this spoke? (6)
├── coverage_pct           -- spoke_cardinality / hub_cardinality (46%)
└── is_subset              -- Are ALL spoke values in hub? (FK integrity)
```

### Query

```python
graph = handler.get_context_graph(project)
# Returns:
{
    'hubs': [
        {'semantic_type': 'company_code', 'table': 'component_company', 
         'column': 'company_code', 'cardinality': 13, 'entity_type': 'companies',
         'is_discovered': False},
        {'semantic_type': 'union_code', 'table': 'unions',
         'column': 'union_code', 'cardinality': 45, 'entity_type': 'unions',
         'is_discovered': True},  # Auto-detected
    ],
    'relationships': [
        {'semantic_type': 'company_code', 'spoke_table': 'employee', 
         'hub_table': 'component_company', 'coverage_pct': 46.0, 'is_valid_fk': True},
    ]
}
```

---

## B.2 The Entity Type Model

**Problem:** Generic column names can't be semantically typed without table context.

```
Table: tea1000_...change_reasons_termination_reasons
Column: "code"
Without entity_type: ??? (can't determine)
With entity_type: termination_reason_code ✓
```

### Schema Extension

```sql
_schema_metadata:
├── table_name             -- DuckDB identifier (ugly)
├── display_name           -- Human-readable
├── entity_type            -- What this table IS ('termination_reasons')
├── category               -- Logical grouping ('change_reasons')
├── file_name              -- Source file
├── sheet_name             -- Source tab
└── ...
```

### Derivation Logic

```python
def _derive_entity_metadata(file_name, sheet_name, sub_table_title=None):
    # Handle "Sheet - SubTable" format from split detection
    if sheet_name and ' - ' in sheet_name and not sub_table_title:
        parts = sheet_name.split(' - ', 1)
        sheet_name = parts[0]      # "Change Reasons" → category
        sub_table_title = parts[1] # "Termination Reasons" → entity_type
    
    # Priority:
    # 1. Sub-table title → entity_type (e.g., "Termination Reasons")
    # 2. Sheet name → entity_type if no sub-table, or category if sub-table
    # 3. File name → entity_type for simple files
```

---

## B.3 The Unified Entity Model (Phase 8+)

After Phase 8, entities span ALL storage types:

```
"termination_reasons" (entity_type)
├── HUB: Config table (DuckDB) - 245 codes
├── SPOKE: Employee terminations (DuckDB) - 47 used
├── SPOKE: HR Policy v2.1.docx (ChromaDB) - discusses process
├── SPOKE: Meeting note Dec 15 (ChromaDB) - mentions new codes
└── SPOKE: RAID Log (Future) - risk about missing codes
```

### Supabase Tables

```sql
-- entity_registry: Master list of entities
CREATE TABLE entity_registry (
    id UUID PRIMARY KEY,
    project_id UUID,
    entity_type VARCHAR NOT NULL,
    canonical_display VARCHAR,
    hub_storage VARCHAR,
    hub_table VARCHAR,
    hub_column VARCHAR,
    hub_cardinality INTEGER,
    is_discovered BOOLEAN DEFAULT FALSE,
    UNIQUE(project_id, entity_type)
);

-- entity_references: All references to entities
CREATE TABLE entity_references (
    id UUID PRIMARY KEY,
    entity_id UUID REFERENCES entity_registry(id),
    storage_type VARCHAR NOT NULL,  -- 'duckdb', 'chromadb', 'external'
    reference_id VARCHAR NOT NULL,
    reference_type VARCHAR NOT NULL, -- 'hub', 'spoke', 'mention'
    cardinality INTEGER,            -- For structured
    coverage_pct DECIMAL(5,2),      -- For structured
    mention_count INTEGER,          -- For semantic
    context_snippet TEXT,           -- For semantic
    UNIQUE(entity_id, storage_type, reference_id)
);
```

---

## B.4 The Five Truths Architecture

All data in XLR8 belongs to one of five "truths":

| Truth | Storage | Description | Example |
|-------|---------|-------------|---------|
| **Reality** | DuckDB | Actual customer data | Employee records, payroll |
| **Configuration** | DuckDB | System setup | Company codes, job codes, deductions |
| **Intent** | ChromaDB | Human decisions | Policies, meeting notes |
| **Reference** | ChromaDB | Domain knowledge | Tax tables, compliance guides |
| **Regulatory** | ChromaDB | Legal requirements | Federal/state regulations |

**The magic:** Triangulation across truths.

```
Question: "Are we compliant with overtime rules?"

→ Reality: Who worked overtime? (DuckDB)
→ Configuration: What's our OT policy setup? (DuckDB)
→ Regulatory: What does FLSA require? (ChromaDB)
→ Answer: "3 employees exceeded 40 hours but aren't flagged for OT pay"
```

---

## B.5 Data Flow Diagrams

### Upload Flow (Updated)

```
┌────────────────────────────────────────────────────────────────────┐
│                         UPLOAD FLOW                                 │
├────────────────────────────────────────────────────────────────────┤
│  File → Split Detection → Store Tables → Derive entity_type        │
│                                              ↓                      │
│                                    _schema_metadata                 │
│                                    (entity_type, category)          │
│                                              ↓                      │
│                           Semantic Inference (uses entity_type)     │
│                                              ↓                      │
│                                    _column_mappings                 │
│                                    (semantic_type - if known)       │
│                                              ↓                      │
│                         compute_context_graph() [DATA-DRIVEN]       │
│                           1. Detect hub patterns from data          │
│                           2. Find spokes by value matching          │
│                           3. Apply vocabulary labels                │
│                           4. Auto-add discovered types              │
│                                              ↓                      │
│                                    CONTEXT GRAPH                    │
│                            (all hubs, including discovered)         │
└────────────────────────────────────────────────────────────────────┘
```

### Query Flow

```
┌────────────────────────────────────────────────────────────────────┐
│                         QUERY FLOW                                  │
├────────────────────────────────────────────────────────────────────┤
│  User Question → get_context_graph() → Scope to Active Universe    │
│                          ↓                                          │
│                  TableSelector (uses graph)                         │
│                          ↓                                          │
│                  SQL Generator (uses graph for joins)               │
│                          ↓                                          │
│                  Intelligence Engine (active data only)             │
│                          ↓                                          │
│                  Consultative Response                              │
└────────────────────────────────────────────────────────────────────┘
```

### Holistic Flow (Post Phase 8)

```
┌────────────────────────────────────────────────────────────────────┐
│                      HOLISTIC DATA FLOW                             │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Excel/CSV ───┐                                                     │
│  PDF Tables ──┼──→ Structured Pipeline ──→ DuckDB ──┐              │
│  Smartsheet ──┘                                      │              │
│                                                      │              │
│                                          Entity Registry            │
│                                            (Supabase)               │
│                                                      │              │
│  Meeting Notes ─┐                                    │              │
│  Policy Docs ───┼──→ Semantic Pipeline ──→ ChromaDB ─┘              │
│  Email ─────────┘                                                   │
│                                                                     │
│                              ↓                                      │
│                                                                     │
│           get_unified_context_graph() spans ALL storage             │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

---

# SECTION C: WAYS OF WORKING

This section answers: "How do we work together?"

---

## C.1 The Prime Directives

1. **Architecture.md is the source of truth** - Update it, don't contradict it
2. **No hardcoding** - Vocabulary labels, thresholds are configurable
3. **Data-driven** - Patterns in data determine structure, not predefined lists
4. **Full file replacements** - No patches, no "add at line X"
5. **Test before claiming done** - Deployed and verified

---

## C.2 File Handling

**ALWAYS provide complete file replacements.** Never:
- "Add this at line 47"
- "Replace the function with..."
- Partial snippets

**ALWAYS verify:**
- `python -m py_compile filename.py`
- Deploy and test endpoint
- Check actual data, not assumptions

---

## C.3 Conversation Continuity

When context is lost, reference:
1. This Architecture document (Section A for status)
2. Transcript files in `/mnt/transcripts/`
3. Memory (Claude's stored context)

Start new conversations with status block from A.7.

---

## C.4 Parking Lot

Items identified but not currently in scope:

- Data Page UX improvements
- Carbone document generation
- Unified SQL Generation refactor
- Chat improvements
- Compliance automation
- Hosting/SOC considerations
- Github integration
- File/Table name display improvements
- Vocabulary CRUD UI (add/update/delete semantic types)
- Unrecognized Hubs UI (name discovered hubs)

---

# SECTION C.5: RESPONSE PATTERNS - THE CONSULTANT'S BRAIN

**Added:** January 7, 2026  
**Status:** Implementation In Progress  
**File:** `backend/utils/response_patterns.py`

---

## C.5.1 Philosophy

**XLR8 is NOT a query engine.** The structured data exists to:
1. Minimize hallucinations - ground everything in FACT
2. Answer analysis questions customers never have accurate answers for
3. Hunt for problems they don't know they have

**Core insight:** Users don't know what they want, only what they don't want.

When someone asks "list my deduction codes" they're really saying: "Something is probably wrong with my deductions and I don't know what. Help me."

---

## C.5.2 The Thinking Chain

Every question, regardless of type, follows this consultant thinking pattern:

```
1. UNDERSTAND
   - What did they literally ask? (surface question)
   - What are they actually worried about? (real question)
   - What fear is driving this? (hidden worry)

2. HUNT
   - Answer the surface question with FACTS (no hallucinations)
   - Search across ALL truths for problems they didn't ask about
   - Look for gaps, risks, compliance issues, orphaned data

3. SYNTHESIZE
   - Ground in facts (here's what you have)
   - Problems found (here's what's wrong)
   - Risk assessment (here's what breaks if ignored)
   - Recommendations (here's what to do)

4. DELIVER
   - Excel workbook with evidence
   - Sheet 1: Configuration (what's set up)
   - Sheet 2: Reality (how it's being used)
   - Sheet 3: Issues & Actions (what to fix)

5. EXTEND
   - Proactive offers (anticipate next 2-3 questions)
   - HCMPACT hook (support path for complex issues)
```

---

## C.5.3 Question Taxonomy (13 Types)

### OPERATIONAL (Current State)
| Type | Triggers | Real Question |
|------|----------|---------------|
| **INVENTORY** | "list", "show all", "what do I have" | Is everything set up that should be? |
| **COUNT** | "how many", "total" | Is this number right? How does it break down? |
| **LOOKUP** | "what is", "find", "show me [specific]" | Is this item configured correctly? |

### DIAGNOSTIC (Is It Right)
| Type | Triggers | Real Question |
|------|----------|---------------|
| **VALIDATION** | "is this right", "any issues", "check" | What's broken that I haven't noticed? |
| **COMPARISON** | "compare", "difference", "vs" | Which one is right? What do I need to fix? |
| **COMPLIANCE** | "compliant", "legal", "required" | What will get us fined or sued? |
| **TROUBLESHOOT** | "why", "not working", "error" | What broke it and how do I fix it fast? |

### ACTION (Do Something)
| Type | Triggers | Real Question |
|------|----------|---------------|
| **HOW-TO** | "how do I", "configure", "set up" | Will I break something if I do this wrong? |
| **IMPACT** | "what if", "who's affected", "change" | How badly can this blow up? |
| **REPORT** | "report", "summary", "export" | I need to share this / document for audit |

### ADVISORY (Think For Me) - Highest Value
| Type | Triggers | Real Question |
|------|----------|---------------|
| **STRATEGY** | "how would I", "best way to", "recommend" | Tell me what to do so I don't screw this up |
| **ANALYZE** | "analyze", "assess", "evaluate" | Find the problems I don't know about |
| **ALTERNATIVES** | "other options", "different way", "instead of" | Is there a better way I haven't thought of? |

---

## C.5.4 Response Pattern Structure

Each pattern defines:

```python
ResponsePattern(
    # IDENTIFICATION
    question_type="inventory",
    trigger_patterns=["list", "show all", "what do I have"],
    
    # UNDERSTAND
    surface_question="What items exist?",
    real_question="Is everything set up that should be?",
    hidden_worry="Something is missing and I don't know what.",
    
    # HUNT
    primary_truths=[CONFIGURATION],      # Answer surface question
    hunting_truths=[REALITY, REFERENCE, REGULATORY],  # Find problems
    hunt_for=[
        "Configured but never used",
        "Used but not configured", 
        "Missing vs vendor template",
        "Missing vs regulatory requirements"
    ],
    
    # DELIVER
    excel_sheets=[
        Sheet("Configuration", CONFIGURATION, "evidence"),
        Sheet("Employee Usage", REALITY, "impact"),
        Sheet("Gaps & Issues", CONFIGURATION, "action_items"),
    ],
    
    # EXTEND
    proactive_offers=[
        "Compare against vendor standard?",
        "Show employees missing assignments?",
        "Run compliance check?"
    ],
    hcmpact_hook="Need help cleaning up configuration gaps?"
)
```

---

## C.5.5 The $500/hr Difference

**Data Monkey Response:**
```
You have 127 deduction codes.
```

**Consultant Response:**
```
You have **127 deduction codes** configured across 4 categories:

**Garnishments (23):** DEF, GARN, LEVY, CHSUP...
**Benefits (45):** GTL, DEN, VIS, MED...
**Retirement (12):** 401K, ROTH...
**Other (47):** UNION, PARK...

**Reality Check:** Of 1,847 active employees:
- 1,823 (98.7%) have at least one deduction
- 12 employees have ZERO deductions assigned ⚠️

**Gap Detected:** Your reference docs mention "HSA" and "FSA" 
but I don't see them configured.

**Compliance Alert:** DOL issued guidance on garnishment limits 
effective 3/1/2026. Review your GARN/LEVY codes.

📎 **Attached: deductions_analysis.xlsx**
- Sheet 1: All Deduction Codes (config)
- Sheet 2: Employee Assignments (reality)
- Sheet 3: Employees with No Deductions (action items)

**Need help?** [Schedule HCMPACT Review]
```

---

## C.5.6 Five Truths Integration

Each response synthesizes across ALL available truths:

| Truth | Role in Response |
|-------|------------------|
| **Configuration** | What's set up (ground facts) |
| **Reality** | How it's being used (impact analysis) |
| **Reference** | Vendor best practices (gap detection) |
| **Regulatory** | Legal requirements (compliance alerts) |
| **Intent** | Customer requirements (scope validation) |

The magic is **triangulation** - finding where truths disagree:
- Config says X, Reality shows Y → Data integrity issue
- Config says X, Regulatory requires Z → Compliance gap
- Config says X, Reference recommends W → Optimization opportunity

---

## C.5.7 Key Files

| File | Purpose |
|------|---------|
| `backend/utils/response_patterns.py` | 13 response patterns with thinking chains |
| `backend/utils/consultative_synthesis.py` | LLM synthesis using patterns |
| `backend/utils/intelligence/synthesizer.py` | Template fallback synthesis |

---

## C.5.8 Implementation Status

| Component | Status |
|-----------|--------|
| Response patterns defined | ✅ Complete |
| Pattern detection (question → type) | ✅ Complete |
| Thinking prompt generation | ✅ Complete |
| Excel spec generation | ✅ Complete |
| Wire into consultative_synthesis | 🔄 In Progress |
| Excel deliverable generation | ⬜ TODO |
| HCMPACT hook integration | ⬜ TODO |

---

# SECTION D: REFERENCE

## D.1 Key Files

| File | Purpose |
|------|---------|
| `utils/structured_data_handler.py` | DuckDB operations, context graph |
| `backend/utils/semantic_vocabulary.py` | Semantic type definitions |
| `backend/utils/relationship_detector.py` | Relationship scoring |
| `backend/routers/data_model.py` | Context graph API |
| `backend/routers/bi_router.py` | BI queries, schema |
| `intelligence/engine.py` | Query orchestration |

## D.2 Key Tables

| Table | Purpose |
|-------|---------|
| `_schema_metadata` | Table metadata (entity_type, category) |
| `_column_mappings` | Semantic types, hub/spoke relationships |
| `_column_profiles` | Column statistics, distinct values |

## D.3 API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /api/data-model/context-graph/{project}` | Get hub/spoke graph |
| `GET /api/bi/schema/{project}` | Get tables with entity_type |
| `GET /api/classification/{project}` | Get table classifications |
| `GET /api/dashboard` | Dashboard metrics with entity breakdown |
