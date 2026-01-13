# XLR8 Roadmap

**Last Updated:** January 12, 2026  
**Total Estimated Hours:** 85-105

---

## Phase Overview

| Phase | Name | Hours | Status | Detail Doc |
|-------|------|-------|--------|------------|
| 0 | Foundation | - | ✅ COMPLETE | - |
| 1 | SQL Evolutions | 30-38 | ✅ COMPLETE | `/doc/PHASE_01_SQL.md` |
| 2 | Vector Retrieval | 20-25 | 🔄 IN PROGRESS | `/doc/PHASE_02_VECTOR.md` |
| 3 | Synthesis | 12-16 | NOT STARTED | `/doc/PHASE_03_SYNTHESIS.md` |
| 4 | Presentation | 10-12 | NOT STARTED | `/doc/PHASE_04_PRESENTATION.md` |
| 5 | API Connectivity | 8-12 | NOT STARTED | `/doc/PHASE_05_API.md` |

---

## Phase 0: Foundation ✅ COMPLETE

**GET HEALTHY Sprint - Completed December 2026**

- Data integrity fixes
- Performance optimization
- System hardening
- Column profiling
- Table classification
- Context graph

---

## Phase 1: SQL Evolutions 🔄 IN PROGRESS

**Build deterministic SQL generation for all query types**

| Evolution | Description | Hours | Status |
|-----------|-------------|-------|--------|
| 1 | Categorical Lookups | - | ✅ DONE |
| 2 | Multi-Table JOINs | - | ✅ DONE |
| 3 | Numeric Comparisons | 4-6 | NOT STARTED |
| 4 | Date/Time Filters | 4-6 | NOT STARTED |
| 5 | OR Logic | 2-3 | NOT STARTED |
| 6 | Negation | 2-3 | NOT STARTED |
| 7 | Aggregations | 3-4 | NOT STARTED |
| 8 | Group By | 2-3 | NOT STARTED |
| 9 | Superlatives | 3-4 | NOT STARTED |
| 10 | Multi-Hop Relationships | 6-8 | NOT STARTED |

**Prerequisites:**
- QueryResolver refactor (2-3 hrs)
- Duckling setup (1-2 hrs)

**Detail:** See `/doc/PHASE_01_SQL.md`

---

## Phase 2: Vector Retrieval 🔄 IN PROGRESS

**Make ChromaDB useful for Five Truths**

| Component | Description | Hours | Status |
|-----------|-------------|-------|--------|
| 2B.1 | Domain-Tagged Chunks | 3-4 | ✅ DONE |
| 2B.2 | Query-Aware Vector Search | 4-5 | ✅ DONE |
| 2B.3 | Source Typing & Prioritization | 2-3 | ✅ DONE |
| 2B.4 | Relevance Scoring & Filtering | 3-4 | ✅ DONE |
| 2B.5 | Citation Tracking | 2-3 | NOT STARTED |
| 2B.6 | Gap Detection Queries | 4-5 | NOT STARTED |

**Detail:** See `/doc/PHASE_02_VECTOR.md`

---

## Phase 3: Synthesis

**Turn retrieved facts into consultative responses**

| Component | Description | Hours |
|-----------|-------------|-------|
| 3.1 | Five Truths Assembly | 3-4 |
| 3.2 | Local LLM Prompt Engineering | 4-5 |
| 3.3 | Gap Detection Logic | 3-4 |
| 3.4 | Consultative Response Patterns | 2-3 |

**Detail:** See `/doc/PHASE_03_SYNTHESIS.md`

---

## Phase 4: Presentation

**Make it look professional**

| Component | Description | Hours |
|-----------|-------------|-------|
| 4.1 | Chat Response Styling | 3-4 |
| 4.2 | Response Structure Polish | 2-3 |
| 4.3 | Export Formatting | 3-4 |
| 4.4 | Error Handling & Edge Cases | 2-3 |

**Detail:** See `/doc/PHASE_04_PRESENTATION.md`

---

## Phase 5: API Connectivity

**Pull live data from UKG instances**

| Component | Description | Hours |
|-----------|-------------|-------|
| 0.1 | Credential Management | 2-3 |
| 0.2 | UKG Pro RaaS Connector | 3-4 |
| 0.3 | UKG WFM Connector | 2-3 |
| 0.4 | UKG Ready Connector | 1-2 |

**Detail:** See `/doc/PHASE_05_API.md`

---

## Success Criteria

**Engine Complete When:**
1. Any reasonable HCM question returns accurate data
2. System explains WHY with regulatory/best practice context
3. System flags configuration gaps
4. Response reads like a consultant wrote it
5. Can pull live from customer UKG instance

**Exit Ready When:**
- Demo handles any reasonable HCM question
- 95% of queries use deterministic SQL
- Due diligence shows clean architecture
- Metrics prove system performance

---

## Current Focus

**Active:** Phase 2 - Vector Retrieval

**Completed This Session (Jan 12):**
- ✅ Phase 2B.1: Domain-Tagged Chunks
  - Created `chunk_classifier.py` with deterministic pattern-based classification
  - Classifies: truth_type, domain, source_authority
  - Integrated into RAGHandler for automatic tagging at upload
- ✅ Phase 2B.2: Query-Aware Vector Search  
  - Created `truth_router.py` with query pattern detection
  - Routes queries to appropriate truth types (regulatory, reference, intent, compliance)
  - Domain detection from query text (earnings, taxes, time, etc.)
  - Integrated into engine's `_gather_reference_library()`
- ✅ Phase 2B.3: Source Typing & Prioritization
  - Created `source_prioritizer.py` with authority weight matrices
  - Re-ranks results by source authority per query type
  - Government wins for regulatory, vendor wins for best practice, customer wins for intent
- ✅ Phase 2B.4: Relevance Scoring & Filtering
  - Created `relevance_scorer.py` with 5-factor scoring
  - Adds recency scoring (newer docs ranked higher)
  - Adds jurisdiction matching (CA query prefers CA law over TX law)
  - Filters out low-quality results (threshold=0.5)

**Next Session Options:**
1. Phase 2B.5: Citation Tracking - Track provenance for responses
2. Phase 2B.6: Gap Detection - Find missing truth coverage
3. Skip to Phase 3 (Synthesis) - Vector retrieval is now robust

---

## Version History

| Date | Change |
|------|--------|
| 2026-01-11 | Initial roadmap created |
