# XLR8 Roadmap

**Last Updated:** January 12, 2026  
**Total Estimated Hours:** 115-145

---

## Phase Overview

| Phase | Name | Hours | Status | Detail Doc |
|-------|------|-------|--------|------------|
| 0 | Foundation | - | ✅ COMPLETE | - |
| 1 | SQL Evolutions | 30-38 | ✅ COMPLETE | `/doc/PHASE_01_SQL.md` |
| 2 | Vector Retrieval | 20-25 | ✅ COMPLETE | `/doc/PHASE_02_VECTOR.md` |
| 3 | Synthesis | 12-16 | NOT STARTED | `/doc/PHASE_03_SYNTHESIS.md` |
| 4 | Presentation | 10-12 | NOT STARTED | `/doc/PHASE_04_PRESENTATION.md` |
| 5 | Multi-Product Schemas | 15-20 | NOT STARTED | `/doc/PHASE_05_MULTI_PRODUCT.md` |
| 6 | API Connectivity | 18-25 | NOT STARTED | `/doc/PHASE_06_API.md` |

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
| 3 | Numeric Comparisons | - | ✅ DONE |
| 4 | Date/Time Filters | - | ✅ DONE |
| 5 | OR Logic | - | ✅ DONE |
| 6 | Negation | - | ✅ DONE |
| 7 | Aggregations | - | ✅ DONE |
| 8 | Group By | - | ✅ DONE |
| 9 | Superlatives | - | ✅ DONE |
| 10 | Multi-Hop Relationships | 6-8 | NOT STARTED |

**Prerequisites:**
- QueryResolver refactor (2-3 hrs)
- Duckling setup (1-2 hrs)

**Detail:** See `/doc/PHASE_01_SQL.md`

---

## Phase 2: Vector Retrieval ✅ COMPLETE

**Make ChromaDB useful for Five Truths**

| Component | Description | Hours | Status |
|-----------|-------------|-------|--------|
| 2B.1 | Domain-Tagged Chunks | 3-4 | ✅ DONE |
| 2B.2 | Query-Aware Vector Search | 4-5 | ✅ DONE |
| 2B.3 | Source Typing & Prioritization | 2-3 | ✅ DONE |
| 2B.4 | Relevance Scoring & Filtering | 3-4 | ✅ DONE |
| 2B.5 | Citation Tracking | 2-3 | ✅ DONE |
| 2B.6 | Gap Detection Queries | 4-5 | ✅ DONE |

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

## Phase 5: Multi-Product Schemas

**Expand beyond HCM to support FINS, ERP, CRM, and other enterprise products**

| Component | Description | Hours | Status |
|-----------|-------------|-------|--------|
| 5.1 | Schema Loader | 3-4 | NOT STARTED |
| 5.2 | Product Registry | 2-3 | NOT STARTED |
| 5.3 | Domain Alignment | 4-5 | NOT STARTED |
| 5.4 | Vocabulary Normalization | 3-4 | NOT STARTED |
| 5.5 | Hub Type Expansion | 2-3 | NOT STARTED |

**Supported Categories:** HCM, FINS, ERP, CRM, SCM

**Detail:** See `/doc/PHASE_05_MULTI_PRODUCT.md`

---

## Phase 6: API Connectivity

**Pull live data from customer instances across multiple products**

| Component | Description | Hours | Status |
|-----------|-------------|-------|--------|
| 6.1 | Credential Management | 2-3 | NOT STARTED |
| 6.2 | Connector Framework | 3-4 | NOT STARTED |
| 6.3 | UKG Connectors | 3-4 | NOT STARTED |
| 6.4 | Workday Connector | 3-4 | NOT STARTED |
| 6.5 | SAP Connectors | 3-4 | NOT STARTED |
| 6.6 | Salesforce Connector | 2-3 | NOT STARTED |
| 6.7 | Oracle Connectors | 2-3 | NOT STARTED |

**Prerequisites:** Phase 5 (Multi-Product Schemas)

**Detail:** See `/doc/PHASE_06_API.md`

---

## Success Criteria

**Engine Complete When:**
1. Any reasonable enterprise question returns accurate data
2. System explains WHY with regulatory/best practice context
3. System flags configuration gaps
4. Response reads like a consultant wrote it
5. Can pull live from customer instances (multiple products)

**Exit Ready When:**
- Demo handles any reasonable enterprise question (HCM, FINS, ERP, CRM)
- 95% of queries use deterministic SQL
- Due diligence shows clean architecture
- Metrics prove system performance
- Multi-product schema support demonstrated

---

## Current Focus

**Active:** Phase 2 - Vector Retrieval ✅ COMPLETE

**Completed This Session (Jan 12):**
- ✅ Phase 2B.1: Domain-Tagged Chunks
  - Created `chunk_classifier.py` with deterministic pattern-based classification
  - Classifies: truth_type, domain, source_authority
  - Integrated into RAGHandler for automatic tagging at upload
- ✅ Phase 2B.2: Query-Aware Vector Search  
  - Created `truth_router.py` with query pattern detection
  - Routes queries to appropriate truth types (regulatory, reference, intent, compliance)
  - Domain detection from query text
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
- ✅ Phase 2B.5: Citation Tracking
  - Created `citation_tracker.py` for source provenance
  - Collects, deduplicates, and formats citations
  - Multiple display formats (brief, full, academic)
  - Added citations field to SynthesizedAnswer
- ✅ Phase 2B.6: Gap Detection
  - Created `gap_detector.py` (product-agnostic, fresh implementation)
  - Archived old HCM-specific `gap_detection_engine.py`
  - Detects missing truth coverage per topic
  - Coverage scoring and gap recommendations

**Next Up:** Phase 3 (Synthesis) - Turn retrieved facts into consultative responses

---

## Version History

| Date | Change |
|------|--------|
| 2026-01-12 | Phase 2 (Vector Retrieval) COMPLETE - all 6 components done |
| 2026-01-12 | Added Phase 5 (Multi-Product Schemas) and Phase 6 (API Connectivity expanded) |
| 2026-01-12 | Archived old HCM-specific gap_detection_engine.py |
| 2026-01-11 | Initial roadmap created |
