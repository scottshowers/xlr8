# XLR8 Roadmap

**Last Updated:** January 24, 2026  
**Architecture:** Chat-First (see `/doc/CHAT_ARCHITECTURE_VISION.md`)  
**Principle:** Chat IS the product. Every interaction answers, captures, learns, and crystallizes.

---

## Strategic Direction

The chat interface is not a feature of XLR8. It IS XLR8.

Every interaction simultaneously:
1. **Answers** the question
2. **Captures** the work (workflow steps)
3. **Builds** memory layers (session → project → global)
4. **Recognizes** patterns for playbook extraction

Consultants don't "build" playbooks. They work. The system watches, learns, and crystallizes what it observed into reusable playbooks.

---

## Phase Overview

| Phase | Name | Status | Hours Est |
|-------|------|--------|-----------|
| 1 | Consultative Clarification | ✅ COMPLETE | - |
| 2 | Memory Layers | 🟡 FOUNDATION | 12-16 |
| 3 | Workflow Capture | 🔲 NOT STARTED | 15-20 |
| 4 | Enhanced Synthesis | 🔲 NOT STARTED | 10-14 |
| 5 | Emergent Playbooks | 🔲 NOT STARTED | 20-25 |
| 6 | Value Crosswalks | 🔲 NOT STARTED | 12-16 |
| 7 | GUIDE Mode | 🔲 NOT STARTED | 15-20 |

**Total Remaining:** ~85-110 hours

---

## Phase 1: Consultative Clarification ✅ COMPLETE

**Deployed:** January 23, 2026

Replaced `BusinessRuleInterpreter` with `IntentEngine` - asks business questions, not technical ones.

| Component | Status |
|-----------|--------|
| IntentEngine | ✅ Deployed |
| Pattern Detection (7 patterns) | ✅ Working |
| Radio Button UI | ✅ Working |
| Session Memory | ✅ Working |
| Project Memory (`_project_intents`) | ✅ Working |
| Intent Context → SQL Generation | ✅ Working |

**Files:**
- `backend/utils/intelligence/intent_engine.py`
- `backend/utils/intelligence/query_engine.py` (v2024.01.24.7)
- `backend/routers/unified_chat.py`

**Verified Behavior:**
1. Ask "how many active employees" → System asks "How do you define 'active'?"
2. Select option → Clarification applied, answer generated
3. Ask same question again → System remembers preference
4. New session → Project memory loads preference

---

## Phase 2: Memory Layers 🟡 FOUNDATION

**Goal:** Three-layer memory system that compounds knowledge

| Layer | Scope | Storage | Status |
|-------|-------|---------|--------|
| Session | Current conversation | Context window | ✅ Working |
| Project | This customer | DuckDB `_project_intents` | ✅ Foundation |
| Global | All customers | Cross-project store | 🔲 NOT STARTED |

### 2.1 Session Memory Enhancement (3-4h)
- [ ] Maintain conversation context across clarifications
- [ ] Track which tables/columns were used in session
- [ ] Remember corrections made during session

### 2.2 Project Memory Expansion (4-5h)
- [ ] Promote useful session patterns to project memory
- [ ] Store table/column preferences per customer
- [ ] Track query patterns and their resolutions

### 2.3 Global Memory Infrastructure (5-7h)
- [ ] Cross-project pattern storage
- [ ] Threshold for promotion (frequency, consistency)
- [ ] Domain-specific global knowledge (HCM patterns vs FINS patterns)

---

## Phase 3: Workflow Capture 🔲 NOT STARTED

**Goal:** Automatically record what consultants do for playbook extraction

| Component | Description | Hours |
|-----------|-------------|-------|
| 3.1 | Step Recording | 4-5 |
| 3.2 | Feature Category Classification | 3-4 |
| 3.3 | Variable Detection | 4-5 |
| 3.4 | Session Boundary Detection | 2-3 |
| 3.5 | Workflow Review UI | 2-3 |

**Infrastructure exists:**
- `_workflow_steps` table created
- `IntentEngine.record_step()` method exists
- Not actively calling it yet

**Feature Categories (from vision):**
- INGEST - Data ingestion
- TRANSFORM - Value crosswalks, normalization  
- COMPARE - Side-by-side analysis
- ANALYZE - Queries, aggregations
- COLLABORATE - Assignments, comments
- OUTPUT - Exports, reports
- GUIDE - Recommendations

---

## Phase 4: Enhanced Synthesis 🔲 NOT STARTED

**Goal:** Every response delivers Answer + SOLVE + Headline

| Component | Description | Hours |
|-----------|-------------|-------|
| 4.1 | Answer Generation | 2-3 |
| 4.2 | SOLVE Detection | 3-4 |
| 4.3 | Headline Generation | 2-3 |
| 4.4 | Confidence Scoring | 2-3 |
| 4.5 | Gap Identification | 1-2 |

**Output Structure:**
```
ANSWER: 23 CA employees undertaxed in UKG

SOLVE: Tax table version mismatch - ADP using 2026 rates, 
       UKG using 2025 rates. Fix: Update UKG tax tables.

HEADLINE: 23 CA employees at tax compliance risk - config fix needed

CONFIDENCE: 85% (missing: actual tax config files)
GAPS: Would need UKG tax table export to confirm version
```

---

## Phase 5: Emergent Playbooks 🔲 NOT STARTED

**Goal:** Playbooks emerge from work, not built upfront

| Component | Description | Hours |
|-----------|-------------|-------|
| 5.1 | Workflow Pattern Recognition | 5-6 |
| 5.2 | Playbook Extraction | 4-5 |
| 5.3 | Variable Parameterization | 4-5 |
| 5.4 | Playbook Storage | 2-3 |
| 5.5 | Playbook Execution | 4-5 |

**Key Insight:**
First time through = DISCOVERY (consultant works, system captures)
Every time after = PLAYBOOK (consultant clicks, system runs)

**At end of discovery:**
> "You just ran a 6-step analysis. Want to save this as a playbook?"

**Playbook Definition:**
- Recorded sequence of feature categories
- Variable parts tagged as inputs (the clarifying questions)
- Defined outputs at the end

---

## Phase 6: Value Crosswalks 🔲 NOT STARTED

**Goal:** Map values across systems for meaningful comparison

| Component | Description | Hours |
|-----------|-------------|-------|
| 6.1 | Crosswalk Storage | 2-3 |
| 6.2 | Client-Provided Import | 2-3 |
| 6.3 | System Inference | 4-5 |
| 6.4 | Clarification-Built | 2-3 |
| 6.5 | Confidence Scoring | 2-3 |

**Problem:** Legacy "100" vs New "ACCT-100" creates false discrepancies

**Three ways to build:**
1. Client provides mapping table
2. System infers from pattern matching
3. Built one answer at a time through clarification

---

## Phase 7: GUIDE Mode 🔲 NOT STARTED

**Goal:** Proactive data solicitation and workflow recommendation

| Component | Description | Hours |
|-----------|-------------|-------|
| 7.1 | Data Gap Analysis | 3-4 |
| 7.2 | Proactive Prompting | 3-4 |
| 7.3 | Workflow Suggestion | 4-5 |
| 7.4 | Flexible Playbook Paths | 3-4 |
| 7.5 | Pattern Learning | 2-3 |

**GUIDE Behavior:**
> "You mentioned payroll parallel. For a complete analysis, I'd need:
> - Legacy pay registers (required)
> - New system pay registers (required)  
> - Tax configuration exports (helpful)
> 
> Can you get me the legacy pay registers? That's highest value."

---

## Completed Infrastructure

### Intelligence Layer (January 2026)
- `query_engine.py` - New simplified SQL generation
- `intent_engine.py` - Consultative clarification
- Deterministic SQL for PIT queries
- TRY_STRPTIME date parsing
- Status column detection (excludes date columns)

### Data Foundation (December 2025)
- GET HEALTHY Sprint complete
- `_schema_metadata` + `_column_profiles` = NEW system
- Column profiling with `top_values_json`
- Table classification
- Context graph (hub-spoke relationships)

### Multi-Product Support (January 2026)
- 44 products across 5 categories
- Universal vocabulary normalization
- Cross-product domain alignment
- M&A schema comparison

---

## Deprecated / Superseded

The following are superseded by Chat Architecture Vision:

| Old Concept | Replaced By |
|-------------|-------------|
| Manual Playbook Builder | Emergent Playbooks (Phase 5) |
| Feature Engine (Phase 7 old) | Workflow Capture (Phase 3) |
| Playbook Engine (Phase 8 old) | Emergent Playbooks (Phase 5) |

**Old files to archive:**
- `query_resolver.py` (3,232 lines) - replaced by `query_engine.py`
- `term_index.py` (2,538 lines) - replaced by `query_engine.py`
- `sql_assembler.py` (1,566 lines) - replaced by `query_engine.py`
- `engine.py` (3,834 lines) - replaced by `query_engine.py`
- `project_intelligence.py` (141K) - OLD system

---

## Exit Criteria

**Exit Ready When:**
1. Chat handles any reasonable enterprise question
2. System delivers Answer + SOLVE + Headline
3. Workflow capture records consultant work
4. At least one emergent playbook demo works
5. Memory persists across sessions
6. Due diligence shows clean architecture

**Demo Script:**
1. Consultant asks questions, system answers with provenance
2. System shows "You just ran a 5-step analysis"
3. Consultant saves as playbook
4. Different project, same playbook runs with different data
5. Knowledge survives consultant turnover

---

## Version History

| Date | Change |
|------|--------|
| 2026-01-24 | **MAJOR REVISION** - Aligned with Chat Architecture Vision |
| 2026-01-24 | Deprecated manual Playbook Builder approach |
| 2026-01-24 | New phases: Memory Layers, Workflow Capture, Enhanced Synthesis, Emergent Playbooks |
| 2026-01-24 | Phase 1 (Consultative Clarification) marked COMPLETE |
| 2026-01-13 | Previous roadmap (Feature Engine → Playbook Engine approach) |
