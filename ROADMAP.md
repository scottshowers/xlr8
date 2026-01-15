# XLR8 Roadmap

**Last Updated:** January 13, 2026  
**Total Estimated Hours:** 180-230

---

## Phase Overview

| Phase | Name | Hours | Status | Detail Doc |
|-------|------|-------|--------|------------|
| 0 | Foundation | - | ✅ COMPLETE | - |
| 1 | SQL Evolutions | 30-38 | ✅ COMPLETE | `/doc/PHASE_01_SQL.md` |
| 2 | Vector Retrieval | 20-25 | ✅ COMPLETE | `/doc/PHASE_02_VECTOR.md` |
| 3 | Synthesis | 12-16 | ✅ COMPLETE | `/doc/PHASE_03_SYNTHESIS.md` |
| 4A | E2E Flow Polish | 8-12 | NOT STARTED | `/doc/PHASE_04A_E2E_FLOW.md` |
| 4B | Export Template Repo | 10-15 | NOT STARTED | `/doc/PHASE_04B_EXPORT.md` |
| 5 | Multi-Product Schemas | 15-20 | ✅ COMPLETE | `/doc/PHASE_05_MULTI_PRODUCT.md` |
| 6 | API Connectivity | 18-25 | NOT STARTED | `/doc/PHASE_06_API.md` |
| 7 | Feature Engine | 25-35 | FUTURE | `/doc/PHASE_07_FEATURES.md` |
| 8 | Playbook Engine | 30-40 | FUTURE | `/doc/PHASE_08_PLAYBOOKS.md` |

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

## Phase 1: SQL Evolutions ✅ COMPLETE

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
| 10 | Multi-Hop Relationships | 6-8 | ✅ DONE |

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

## Phase 3: Synthesis ✅ COMPLETE

**Turn retrieved facts into consultative responses**

| Component | Description | Hours | Status |
|-----------|-------------|-------|--------|
| 3.1 | Five Truths Assembly | 3-4 | ✅ DONE |
| 3.2 | Local LLM Prompt Engineering | 4-5 | ✅ DONE |
| 3.3 | Gap Detection Logic | 3-4 | ✅ DONE |
| 3.4 | Consultative Response Patterns | 2-3 | ✅ DONE |

**Files Created:**
- `truth_assembler.py` - TruthContext assembly with RealityContext, IntentContext, etc.
- `llm_prompter.py` - Prompt optimization for Mistral/DeepSeek with ResponseQuality validation
- `enhanced_gap_detector.py` - Gap detection for CONFIG_VS_INTENT, CONFIG_VS_REFERENCE, CONFIG_VS_REGULATORY
- `response_patterns.py` - ConsultativeResponse templates by query type
- `synthesis_pipeline.py` - Main orchestrator integrating all components

**Detail:** See `/doc/PHASE_03_SYNTHESIS.md`

---

## Phase 4A: UX Overhaul

**Complete frontend redesign with production-ready design system**

| Component | Description | Hours | Status |
|-----------|-------------|-------|--------|
| 4A.1 | Design System Foundation | 4-6 | IN PROGRESS |
| 4A.2 | Core Layout (Header/Sidebar/Flow Bar) | 3-4 | NOT STARTED |
| 4A.3 | Mission Control (Cross-Project) | 4-5 | NOT STARTED |
| 4A.4 | Finding Review & Massage | 4-5 | NOT STARTED |
| 4A.5 | Project Workspace (4 Tabs) | 6-8 | NOT STARTED |
| 4A.6 | Vacuum UX Refresh | 2-3 | NOT STARTED |
| 4A.7 | Admin Module Pages | 6-8 | NOT STARTED |

**Total:** 29-39 hours

**Approach:** Page-by-page implementation, one component at a time to avoid compaction

**Detail:** See `/doc/PHASE_04A_E2E_FLOW.md`

---

## Phase 4B: Export Template Repo

**Carbone-based export infrastructure for professional deliverables**

| Component | Description | Hours |
|-----------|-------------|-------|
| 4B.1 | Template Storage Structure | 2-3 |
| 4B.2 | Carbone Integration | 3-4 |
| 4B.3 | Variable Mapping | 2-3 |
| 4B.4 | Template Admin UI | 3-4 |
| 4B.5 | Multi-Format Output | 1-2 |

**Detail:** See `/doc/PHASE_04B_EXPORT.md`

---

## Phase 5: Multi-Product Schemas ✅ COMPLETE

**Expand beyond HCM to support FINS, ERP, CRM, and other enterprise products**

| Component | Description | Hours | Status |
|-----------|-------------|-------|--------|
| 5A | Schema Normalization | 2-3 | ✅ DONE |
| 5B | Product Registry | 2-3 | ✅ DONE |
| 5C | Domain/Vocabulary Extraction | 3-4 | ✅ DONE |
| 5D | Refactor term_index.py | 3-4 | ✅ DONE |
| 5E | Schema Comparator (M&A) | 2-3 | ✅ DONE |
| 5F | Project Setup Integration | 2-3 | ✅ DONE |

**Completed January 13, 2026**

**Files Created:**
- `backend/utils/products/__init__.py` - Module exports
- `backend/utils/products/registry.py` - ProductRegistry with 44 products, 4,257 hubs
- `backend/utils/products/vocabulary.py` - VocabularyNormalizer, DomainAligner, UNIVERSAL_ENTITIES
- `backend/utils/products/comparator.py` - SchemaComparator for M&A integration analysis

**Key Capabilities:**
- **44 Products** across 5 categories (HCM, FINS, ERP, CRM, Collaboration)
- **Universal Vocabulary** - normalize terms across products (employees/workers/staff → employee)
- **Cross-Product Domain Alignment** - map UKG Compensation to Workday Compensation
- **M&A Schema Comparison** - compatibility scores, gap analysis, integration recommendations
- **Product-Aware Engine** - IntelligenceEngineV2 now accepts product_id

**API Endpoints Added:**
- `GET /projects/products/list` - List all products by category
- `GET /projects/products/categories` - Category/vendor summary
- `GET /projects/products/{product_id}` - Product details with domains
- `GET /projects/products/compare/{source}/{target}` - M&A integration analysis

**Supported Categories:** HCM (23), FINS (5), ERP (2), CRM (6), Collaboration (8)

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

## Phase 7: Feature Engine

**Atomic building blocks for consulting workflows**

| Component | Description | Hours | Status |
|-----------|-------------|-------|--------|
| 7.1 | Feature Schema & Runtime | 4-5 | FUTURE |
| 7.2 | Core Feature Library | 10-14 | FUTURE |
| 7.3 | Feature Builder UI | 6-8 | FUTURE |
| 7.4 | Feature Registry | 3-4 | FUTURE |
| 7.5 | Feature Testing Framework | 2-3 | FUTURE |

**Core Features:** Upload, Compare/Diff, Export, Compliance Check, Crosswalk, Query, Summarize, Assign, Snapshot, Generate Report

**Prerequisites:** Phase 6 (API Connectivity)

**Detail:** See `/doc/PHASE_07_FEATURES.md`

---

## Phase 8: Playbook Engine

**Guided workflows with HCMPACT methodology baked in**

| Component | Description | Hours | Status |
|-----------|-------------|-------|--------|
| 8.1 | Playbook Schema | 3-4 | FUTURE |
| 8.2 | Playbook Runtime | 5-6 | FUTURE |
| 8.3 | Quality Gate System | 5-6 | FUTURE |
| 8.4 | Playbook Builder UI | 6-8 | FUTURE |
| 8.5 | HCMPACT Methodology Library | 6-8 | FUTURE |
| 8.6 | Guidance System | 4-5 | FUTURE |

**Ships With:** Year-End Readiness playbook (HCMPACT methodology as default)

**Key Concept:** System makes bad work harder than good work - quality gates, step guidance, deliverable standards

**Prerequisites:** Phase 7 (Feature Engine)

**Detail:** See `/doc/PHASE_08_PLAYBOOKS.md`

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

**Active:** Phase 4A - E2E Flow Polish

**Just Completed:** Phase 3 - Synthesis (all 4 components)

**Next Up:** Phase 4B (Export Template Repo)

**Unlocks After Phase 6:**
- Phase 7: Feature Engine (composable workflow building blocks)
- Phase 8: Playbook Engine (HCMPACT methodology baked in)

---

## Version History

| Date | Change |
|------|--------|
| 2026-01-15 | Phase 4A updated: Complete UX overhaul with design system (29-39 hours) |
| 2026-01-13 | Phase 3 (Synthesis) COMPLETE - truth_assembler, llm_prompter, enhanced_gap_detector, response_patterns, synthesis_pipeline |
| 2026-01-13 | Created full Phase 7 (Feature Engine) and Phase 8 (Playbook Engine) docs |
| 2026-01-13 | Split Phase 4 into 4A (E2E Flow) and 4B (Export Template Repo) |
| 2026-01-12 | Phase 1 (SQL Evolutions) COMPLETE - Evolution 10 Multi-Hop done |
| 2026-01-12 | Phase 2 (Vector Retrieval) COMPLETE - all 6 components done |
| 2026-01-12 | Added Phase 5 (Multi-Product Schemas) and Phase 6 (API Connectivity expanded) |
| 2026-01-12 | Archived old HCM-specific gap_detection_engine.py |
| 2026-01-11 | Initial roadmap created |
