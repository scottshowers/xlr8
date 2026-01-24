# XLR8 Chat Architecture Vision

**Date:** January 23, 2026  
**Last Updated:** January 24, 2026  
**Status:** Phase 1 COMPLETE - IntentEngine Deployed & Tested  
**Authors:** Scott + Claude (Solution Architecture Session)

---

## Implementation Status

### ✅ Phase 1: Consultative Clarification (COMPLETE)

**Deployed:** January 23, 2026

**What was built:**

| Component | Status | Description |
|-----------|--------|-------------|
| `IntentEngine` | ✅ Deployed | Replaces BusinessRuleInterpreter with consultative questions |
| Pattern Detection | ✅ Working | 7 business intent patterns (temporal, status, comparison, etc.) |
| Radio Button UI | ✅ Working | Frontend displays options with full descriptive labels |
| Session Memory | ✅ Working | Clarifications persist within conversation |
| Project Memory | ✅ Working | Choices saved to DuckDB `_project_intents` table |
| Intent Context | ✅ Working | Parameters passed to SQL generation |

**Files modified:**
- `backend/utils/intelligence/intent_engine.py` - New consultative engine
- `backend/utils/intelligence/query_engine.py` - IntentEngine integration + persistence fix
- `backend/routers/unified_chat.py` - Clarification application + logging

**Verified behavior:**
1. Ask "how many active employees" → System asks "How do you define 'active'?" with radio options
2. Select option → Clarification applied, answer generated with intent context in footer
3. Ask same question again → System remembers preference, no re-ask
4. New session → Project memory loads, preference still applied

### 🔲 Phase 2: Memory Layers (NOT STARTED)

- Session memory (context window) - partially in place
- Project memory (DuckDB) - foundation in place via `_project_intents`
- Global memory (cross-project) - not implemented

### 🔲 Phase 3: Workflow Capture (NOT STARTED)

- `_workflow_steps` table exists but not actively recording
- Playbook extraction from workflows - not implemented
- GUIDE mode - not implemented

### 🔲 Enhanced Synthesis (NOT STARTED)

- Answer + SOLVE + Headline format - not implemented
- Confidence scoring - not implemented
- Gap identification - not implemented

### Known Issues / Feedback (from testing)

1. **Chat quality** - Scott has feedback on response formatting (captured for P5 sprint)
2. **Option labels** - Enhanced to be more descriptive, may need further tuning
3. **Intent context display** - Currently shows in italics footer, may want different presentation

### Recommended Next Steps

1. **Test remaining patterns** - temporal_analysis, data_comparison need production validation
2. **Chat quality sprint** - Address feedback on response formatting (P5 task, 6h estimated)
3. **Phase 2 memory** - Build session/global memory layers when ready
4. **Workflow capture** - Start recording steps for playbook extraction

---

## Executive Summary

The chat interface is not a feature of XLR8. It IS XLR8.

Every interaction flows through chat. Chat simultaneously:
1. Answers the question
2. Captures the work
3. Builds memory layers
4. Recognizes workflow patterns

The consultant never "builds" anything. They work. The system watches, learns, and crystallizes what it observed into reusable playbooks.

---

## The Problem We Solved

### Previous State (Fixed in Phase 1)

When a user asked "employees by date", the system asked:

> "Which date field do you want to use?"

This is DBA talk, not consultant talk. A real consultant would ask:

> "What are you trying to understand - headcount trend over time, turnover patterns, or something else?"

The current implementation:
- Detects patterns (by_date, active, as_of)
- Maps them to technical questions about columns
- Stores "business rules" that are really just column preferences

**Why this is wrong:**
1. It asks technical questions instead of business questions
2. It hardcodes assumptions about what patterns mean
3. It doesn't help the user think through their actual intent
4. The same user intent might need different columns depending on available data

### The Consultant's Real Job

A consultant doesn't just answer questions. They deliver THREE things:

| Deliverable | Description | Example |
|-------------|-------------|---------|
| **Answer** | Immediate response to what was asked | "47 employees" |
| **SOLVE** | Systemic why + how to prevent recurrence | "Concentrated in no-income-tax states. Config gap - system not requiring acknowledgment. Fix the election rule." |
| **Headline** | 130-character executive summary | "47 at risk for tax compliance - config fix needed" |

Most consultants stop at Answer, stumble into SOLVE, rarely package Headline.

**XLR8's job:** Make delivering all three AUTOMATIC, so even a mediocre consultant looks like they connected the dots.

---

## Core Architecture Principles

### 1. Chat is Everything

The chat engine isn't: Question → SQL → Answer

It's: Question → **Answer + SOLVE + Headline + Confidence + Gaps**

Every response includes:
- The answer to what was asked
- The systemic explanation
- The executive summary
- How confident the system is
- What's missing that would increase confidence

### 2. Clarification is Load-Bearing

Clarification questions serve FOUR purposes simultaneously:

| Purpose | What it does | Example |
|---------|--------------|---------|
| **Better SQL** | Immediate query improvement | Knows to GROUP BY month on hireDate |
| **Intent Capture** | Records what user is trying to accomplish | "headcount trend analysis" |
| **Step Classification** | Identifies which feature category this is | ANALYZE step |
| **Pattern Learning** | Recognizes reusable patterns | "by date" + "headcount" = trend analysis |

One question, four purposes.

### 3. Playbooks Emerge, Not Built

**The problem with playbook builders:**
- Feels like overhead ("I know what I need to do, stop making me click")
- Requires consultants to think abstractly about steps
- Creates technical-feeling UX
- Most consultants can't articulate the 5 steps to solve a problem

**The solution:**

First time through = DISCOVERY
- Consultant asks questions
- System connects dots
- System captures: what was asked → what data was touched → what categories were used → what output was produced

At the end:
> "You just ran a 6-step analysis. Want to save this as a playbook?"

Every time after:
- Sidebar shows "Payroll Parallel Comparison"
- Consultant clicks it
- Chat asks 3-4 input questions
- System runs entire chain
- Deliverable lands in their lap

**The playbook is:**
- A recorded sequence of feature categories
- Variable parts tagged as inputs (the clarifying questions)
- Defined outputs at the end

### 4. Three Layers of Memory

| Layer | Scope | Persistence | What it stores |
|-------|-------|-------------|----------------|
| **Session** | Current conversation | Context window | Immediate back-and-forth, working state |
| **Project** | This customer | DuckDB per project | Learned terms, preferences, table mappings, domain-specific rules |
| **Global** | All customers | Cross-project store | Patterns that generalize, common playbooks, domain knowledge |

**How they feed each other:**
- Session context captures what's happening NOW
- Good session interactions get promoted to Project memory
- Patterns that repeat across projects get promoted to Global memory

Clarification answers flow into all three.

### 5. Provenance is Mandatory

The system must show its work. Always.

> "Here's what I found. Here's how I found it. Here's what I'm not sure about."

**Why this matters:**
- Consultants can validate the 80%
- Consultants know where to focus on the 20%
- No black box magic that can't be defended to a client
- Architecture FORCES honesty - LLM can only narrate what actually happened

**Synthesis output structure:**
```
ANSWER: 23 CA employees undertaxed in UKG

SOLVE: Backed into rate differential - ADP applying 9.0% (2026 CA rate), 
       UKG applying 7.84% (2025 CA rate). Tax table version mismatch.
       Fix: Update UKG to 2026 tables, rerun test payroll.

HEADLINE: "23 CA employees undertaxed - UKG has outdated tax tables"

CONFIDENCE: High - rate differential is mathematically provable from data

GAPS: Don't have actual tax table configs from either system. 
      Recommend pulling to confirm before presenting to client.

PROVENANCE:
- Source: TEA1000_adp_pay_register, TEA1000_ukg_test_payroll
- SQL: [actual query]
- Rows examined: 312 employees, 23 with CA state tax variance
```

### 6. LLM is Last Mile, Not Engine

**The engine is:**
- INGEST (get clean data in)
- COMPARE (find differences in actual data)  
- ANALYZE (pattern detection on real results)

**The LLM just:**
- Turns results into natural language
- Suggests what patterns might mean
- Admits what it doesn't have

If the data isn't there, the system says "I don't have this." It doesn't make it up. It CAN'T - because the architecture won't let it. There's nothing to hallucinate from if you never asked it to generate from thin air.

### 7. 80/20 Honesty

> "I got you 80% of the way. Here's the 20% I need help with."

This is not a limitation. This is the VALUE PROP.

**The consultant's job:**
- Validate the 80%
- Solve the 20%
- Apply judgment
- Advise the client

If the system claims 100% confidence, the consultant becomes a button-pusher. That's not a product for consultants - that's a replacement for them. And it won't actually work.

---

## Feature Categories (The Building Blocks)

From Phase 7 spec, refined:

| Category | Purpose | Examples |
|----------|---------|----------|
| **INGEST** | Bring data in | Upload, Snapshot, API Pull |
| **TRANSFORM** | Modify/clean/map data | Crosswalk, Normalize, Value Mapping |
| **COMPARE** | Diff two things | Schema compare, Data compare, Config compare |
| **ANALYZE** | Run rules, find patterns | Compliance check, Root cause, Trend analysis |
| **COLLABORATE** | Human workflow | Assign, Review, Approve |
| **OUTPUT** | Produce deliverables | Export, Report, Workbook |

**Plus one MODE (not a category):**

| Mode | Purpose | When Used |
|------|---------|-----------|
| **GUIDE** | Help consultant figure out what to do | "I have data but don't know where to start" |

**Playbooks are chains of categories with defined inputs/outputs. GUIDE helps you find the right playbook.**

---

## Use Case Validation

### Use Case 1: Payroll Parallel Comparison

**Scenario:** Compare ADP pay register (FACT) vs UKG test payroll (Testing)

**Workflow:**
1. COMPARE → auto-categorize discrepancies
2. ANALYZE → drill into category (e.g., tax withholding)
3. ANALYZE → back into calculations, prove root cause
4. OUTPUT → document findings per category
5. Repeat 2-4 for each category
6. OUTPUT → consolidated workbook (tab per issue)

**Clarifying questions (become playbook inputs):**
- Which file is source of truth?
- What's the match key? (Employee ID, SSN, etc.)
- What's the tolerance? (Exact, pennies, percentage?)
- Line-level or totals comparison?

**Output:** Workbook with summary tab + tab per root cause, each containing affected employees, variance amounts, backed-into calculations, root cause, recommended fix.

**Playbook capture:** After first run, consultant can click "Payroll Parallel" in sidebar, answer inputs, get complete workbook.

### Use Case 2: M&A Integration Readiness

**Scenario:** Acquirer buying target company. Need integration analysis across all business functions.

**Key insight:** This is the same pattern as payroll parallel, just at scale.

| Payroll Parallel | M&A Integration |
|------------------|-----------------|
| 2 files | 2 companies × N domains |
| COMPARE → ANALYZE → OUTPUT | COMPARE → ANALYZE → OUTPUT |
| Single domain (payroll) | All domains (HCM, FINS, ERP, CRM) |
| Hours | Days |

**The platform doesn't care about org charts or workstreams.** If both companies' data is in the system, it's just COMPARE at scale.

**Clarifying questions:**
- Who's the acquirer? (source of truth)
- Target state? (keep acquirer systems, best of breed, greenfield)
- Which domains are in scope?

**Value prop:** What takes an army of consultants 6 weeks becomes one consultant and XLR8 in 2 days.

---

## Implementation Plan

### Phase 1: Consultative Clarification (Foundation)

**Goal:** Replace technical questions with business intent questions

**Current:**
```
Pattern: by_date
Question: "Which date field do you want to use?"
Options: [hireDate, termDate, birthDate]
Storage: {pattern: "by_date", column: "hireDate"}
```

**Target:**
```
Pattern: by_date
Question: "What are you trying to understand?"
Options: [
  "Headcount trend over time",
  "Turnover patterns", 
  "Tenure distribution",
  "Something else - let me explain"
]
Storage: {
  intent: "headcount_trend",
  clarification: "Headcount trend over time",
  timestamp: "...",
  project: "TEA1000"
}
```

**Key changes:**
- Questions ask about business INTENT, not technical implementation
- Answers stored as intent, not SQL fragments
- Intent passed to LLM which determines appropriate SQL given available tables
- Same intent, different data = LLM figures out the right columns

**Files to modify:**
- `backend/utils/intelligence/query_engine.py` - BusinessRuleInterpreter class
- New: `backend/utils/intelligence/intent_patterns.py` - Business intent taxonomy

**Estimated hours:** 4-6

### Phase 2: Memory Architecture

**Goal:** Build three-layer memory system

#### Layer 1: Session (exists, needs structure)
- Current conversation in context window
- Working memory for multi-step tasks
- Cleared when conversation ends

#### Layer 2: Project Memory (new)
- Stored in DuckDB per project
- Tables:
  - `_project_intents` - Captured user intents and clarifications
  - `_project_terms` - Learned term mappings for this customer
  - `_project_preferences` - How this consultant likes things done
  - `_workflow_steps` - Captured steps for playbook extraction

**Schema:**
```sql
CREATE TABLE _project_intents (
    id INTEGER PRIMARY KEY,
    project VARCHAR,
    session_id VARCHAR,
    question VARCHAR,
    detected_pattern VARCHAR,
    clarification_question VARCHAR,
    user_response VARCHAR,
    resolved_intent VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE _workflow_steps (
    id INTEGER PRIMARY KEY,
    project VARCHAR,
    session_id VARCHAR,
    step_order INTEGER,
    feature_category VARCHAR,  -- INGEST, COMPARE, ANALYZE, OUTPUT, etc.
    intent VARCHAR,
    inputs JSON,
    outputs JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Layer 3: Global Memory (new)
- Cross-project pattern storage
- Tables:
  - `_global_patterns` - Intent patterns that generalize
  - `_global_playbooks` - Saved playbook templates
  - `_domain_knowledge` - Learned domain rules (tax tables = state-specific, etc.)

**Files to create:**
- `backend/utils/memory/session_memory.py`
- `backend/utils/memory/project_memory.py`
- `backend/utils/memory/global_memory.py`
- `backend/utils/memory/__init__.py`

**Estimated hours:** 8-12

### Phase 3: Workflow Capture

**Goal:** Watch work happening, capture steps, enable playbook extraction

**Mechanism:**
1. Every chat interaction tagged with feature category
2. Clarification answers captured with intent
3. Outputs recorded with structure
4. Session forms a "workflow trace"

**At session end (or on demand):**
- System analyzes trace
- Filters noise (dead ends, corrections)
- Identifies coherent workflow
- Offers to save as playbook

**Playbook structure:**
```json
{
  "id": "payroll_parallel_v1",
  "name": "Payroll Parallel Comparison",
  "description": "Compare two pay registers, identify and categorize discrepancies, prove root causes",
  "inputs": [
    {"name": "source_of_truth", "question": "Which file is your source of truth?", "type": "file_select"},
    {"name": "test_file", "question": "Which file is the test/comparison?", "type": "file_select"},
    {"name": "match_key", "question": "How should I match employees?", "type": "select", "options": ["Employee ID", "SSN", "Name + Pay Period"]},
    {"name": "tolerance", "question": "What variance threshold should I flag?", "type": "select", "options": ["Any difference", "Over $1", "Over 1%"]}
  ],
  "steps": [
    {"category": "COMPARE", "intent": "line_level_comparison", "input_refs": ["source_of_truth", "test_file", "match_key", "tolerance"]},
    {"category": "ANALYZE", "intent": "auto_categorize_discrepancies"},
    {"category": "ANALYZE", "intent": "drill_and_prove_root_cause", "repeat": "per_category"},
    {"category": "OUTPUT", "intent": "document_per_category", "repeat": "per_category"},
    {"category": "OUTPUT", "intent": "consolidated_workbook"}
  ],
  "outputs": [
    {"name": "comparison_workbook", "type": "xlsx", "structure": "tab_per_root_cause"}
  ],
  "created_from_session": "sess_abc123",
  "created_at": "2026-01-23T...",
  "created_by": "consultant@hcmpact.com"
}
```

**Files to create:**
- `backend/utils/playbooks/workflow_capture.py`
- `backend/utils/playbooks/playbook_extractor.py`
- `backend/utils/playbooks/playbook_runner.py`

**Estimated hours:** 10-15

### Phase 4: Synthesis Enhancement

**Goal:** Every response includes Answer + SOLVE + Headline + Confidence + Gaps

**Current synthesis:** Basic LLM pass-through

**Target synthesis prompt structure:**
```
You are synthesizing analysis results for a consultant.

DATA CONTEXT:
{tables_used}
{sql_executed}
{row_counts}

RESULTS:
{actual_data}

RESPOND WITH:
1. ANSWER: Direct response to the question (1-2 sentences)
2. SOLVE: What's causing this? How to fix/prevent? (2-4 sentences)  
3. HEADLINE: Executive summary, <130 characters
4. CONFIDENCE: High/Medium/Low with brief justification
5. GAPS: What data would increase confidence? What couldn't be verified?

Be honest about uncertainty. If you can't prove something from the data, say so.
```

**Files to modify:**
- `backend/utils/intelligence/query_engine.py` - ResponseSynthesizer class

**Estimated hours:** 4-6

### Phase 5: Pre-seed Playbooks

**Goal:** Day 1 has 6-7 working playbooks so AHA moment lands immediately

**Candidate playbooks:**
1. **Payroll Parallel Comparison** - Compare pay registers, prove root causes
2. **M&A Integration Readiness** - Cross-domain system comparison
3. **Year-End Readiness** - Compliance checks across tax, benefits, time
4. **Employee Data Quality Audit** - Find gaps, duplicates, inconsistencies
5. **Benefits Reconciliation** - Compare enrollment vs deductions vs carrier
6. **Compliance Gap Analysis** - Config vs regulatory requirements
7. **Org Structure Validation** - Reporting relationships, cost center alignment

**For each:**
- Define inputs (clarifying questions)
- Define step chain (feature categories)
- Define outputs (deliverable structure)
- Test with real data

**Estimated hours:** 12-18 (2-3 hours per playbook)

### Phase 6: UI Integration

**Goal:** Chat interface with playbook sidebar

**Components:**
- Chat panel (primary interface)
- Playbook sidebar (saved playbooks, click to run)
- Memory indicator (what system knows about this project)
- Provenance panel (show your work, collapsible)

**Note:** UX design deferred - functionality first, pretty later

**Estimated hours:** 8-12

---

## Total Estimate

| Phase | Hours | Dependency |
|-------|-------|------------|
| 1. Consultative Clarification | 4-6 | None |
| 2. Memory Architecture | 8-12 | None |
| 3. Workflow Capture | 10-15 | Phase 1, 2 |
| 4. Synthesis Enhancement | 4-6 | Phase 1 |
| 5. Pre-seed Playbooks | 12-18 | Phase 1, 2, 3 |
| 6. UI Integration | 8-12 | Phase 3 |

**Total:** 46-69 hours

**Critical path:** Phase 1 + 2 are foundational. Everything else builds on them.

**Recommended sequence:**
1. Phase 1 + 2 in parallel (foundation)
2. Phase 4 (synthesis) - quick win, visible improvement
3. Phase 3 (workflow capture) - enables playbooks
4. Phase 5 (pre-seed) - creates AHA moment
5. Phase 6 (UI) - makes it real for users

---

## Proactive Data Solicitation

The system isn't passive. It tells you what it needs and helps you get it.

### Before Work Starts

When a playbook or analysis requires data that's missing:

> "To run a payroll parallel comparison, I need a source file and a test file. I see you've uploaded the ADP register but I don't see a UKG test payroll. Do you have that?"

### During Work

When the system hits a gap mid-analysis:

> "I found 58 tax withholding discrepancies. To prove root cause, I need to back into the rates - but I'm missing the tax table configs from both systems. Want me to continue with inference, or wait for that data?"

### After Work (Path Forward)

When results are delivered with confidence gaps:

> "I categorized 147 discrepancies but I'm only 60% confident on the tax root causes. If you can get me the tax table configs from both systems, I can prove it instead of infer it. Want me to draft a request email to send to the client?"

The system doesn't just report gaps - it helps close them.

---

## Flexible Playbooks

Playbooks aren't rigid scripts. They're templates that adapt to available data.

### Required vs Optional Inputs

Some inputs are blockers, some improve confidence:

```
PAYROLL PARALLEL COMPARISON

Required:
- Source of truth file (blocks entire playbook)
- Test file (blocks entire playbook)
- Match key (blocks comparison)

Optional (improves confidence):
- Tax table configs (proves vs infers root cause)
- Deduction rules (explains 401k variances)
- Pay rate sources (explains gross pay variances)
```

### Steps Can Be Skipped

If data isn't there, run what you CAN run:

> "Payroll Parallel Comparison: 
> - Step 1-3: COMPLETE (discrepancies found, categorized)
> - Step 4: PARTIAL (root cause inferred, not proven - need tax configs)
> - Step 5-6: BLOCKED (need tax configs to generate final workbook)
> 
> Current confidence: 60%. Upload tax configs to continue, or export partial findings now?"

### Confidence Scales with Completeness

More data = higher confidence. Not pass/fail.

| Data Available | Confidence | Output |
|----------------|------------|--------|
| Both pay registers | 40% | Discrepancies listed, no root cause |
| + Backed-into calculations | 70% | Root cause inferred from patterns |
| + Tax table configs | 90% | Root cause proven with evidence |
| + System config exports | 95% | Root cause + exact fix identified |

The consultant decides: good enough, or go get more data.

---

## The Abstraction Layer

Playbooks can't speak in filenames or column names. They speak in CONCEPTS.

### Three-Layer Translation

| Layer | Speaks in | Example |
|-------|-----------|---------|
| **Playbook** | Business concepts | "Compare gross pay from source vs test pay register" |
| **Project** | Customer mappings | "Source = ADP, gross pay = 'Gross' column; Test = UKG, gross pay = 'GrossEarnings' column" |
| **File** | Actual tables/columns | `SELECT t1.Gross, t2.GrossEarnings FROM tea1000_adp_payroll t1 JOIN tea1000_ukg_test t2...` |

### Ingestion Builds the Map

When a file comes in, ingestion:

1. **Classifies it**: What TYPE is this? (pay register, employee master, GL extract, benefits enrollment)
2. **Detects domain**: What DOMAIN? (HCM, FINS, ERP, CRM)
3. **Maps fields**: What CONCEPTS do these columns represent?

This is where clarification at ingest matters:

> "I see you uploaded 'Q1_Payroll_Final.xlsx'. This looks like a pay register - is that right? And should I treat this as the source of truth or the test data?"

That answer goes into project memory. Playbook can now find it by concept, not filename.

### Playbook Execution Flow

1. Playbook says: "I need pay register from source system"
2. System queries project memory: "What files are classified as `pay_register` and tagged `source_of_truth`?"
3. Finds: `tea1000_adp_payroll_export`
4. Playbook says: "Compare `gross_pay`"
5. System checks field mapping: "`gross_pay` = column 'Gross' in this table"
6. SQL uses actual column name

**The consultant never sees this translation.** They just see:

> "I found your ADP pay register and UKG test payroll. Comparing gross pay, net pay, and deductions across 312 employees..."

### What This Means for Memory

Project memory must store:

| Memory Type | Example |
|-------------|---------|
| **File classifications** | `Q1_Payroll_Final.xlsx` → type: `pay_register` |
| **System tags** | `Q1_Payroll_Final.xlsx` → role: `source_of_truth` |
| **Field mappings** | table `tea1000_adp_payroll`, column `Gross` → concept: `gross_pay` |
| **Vendor context** | This project uses ADP as source, UKG as target |

Built during INGEST - auto-detected where possible, clarified with user where needed.

---

## Temporal Context

Time is a dimension that touches everything. The system must track three temporal layers.

### File-Level Dates

What period does this data represent?

System tries to infer:
> "This file has pay dates ranging from Jan 1-15, 2026. Should I treat this as the Jan 1-15 pay period?"

Or asks directly:
> "You uploaded 'ADP_Payroll_Export.xlsx'. What pay period does this cover?"

**Why it matters:** Comparing Jan ADP to Feb UKG is garbage. System needs to know.

### Analysis-Level Dates

What point in time are we analyzing?

> "How many active employees?"

Active as of WHEN?
- Today?
- End of last month?
- Specific point-in-time for a report?

> "Compare these registers"

Same period? Which one defines the analysis window?

### Intelligence-Level Dates

What version of rules/rates/configs apply to THIS data?

> "I'm applying 2026 CA tax rates because your pay period is Jan 2026. If this is actually 2025 data, tell me and I'll recalculate."

Tax tables, benefit plan rules, compliance thresholds - all change over time. System must apply the RIGHT version.

### Temporal Context Capture

Clarification captures all three:

| Level | Question | Example Storage |
|-------|----------|-----------------|
| **File** | What period does this data represent? | `pay_period: "2026-PP1", date_range: "2026-01-01 to 2026-01-15"` |
| **Analysis** | What point in time are we analyzing? | `as_of_date: "2025-12-31"` |
| **Intelligence** | What rules/rates apply? | `tax_year: 2025, config_effective: "2025-01-01"` |

### Mismatch Detection

System flags temporal inconsistencies:

> "Warning: Your ADP file covers Jan 1-15 but your UKG file covers Jan 1-31. Want me to compare only the overlapping period, or are these actually supposed to match?"

> "You asked for active employees as of Dec 31, but this employee file was extracted Jan 15 and includes January hires. Should I filter to only those with hire date on or before Dec 31?"

> "Your pay register is from Jan 2026 but the tax tables I have are from 2025. Do you want me to use 2025 rates (may not match current withholding) or should you upload 2026 tax tables?"

### Temporal Flexibility in Playbooks

Playbooks adapt to date mismatches rather than breaking:

- Auto-filter to overlapping periods when possible
- Flag when periods don't align
- Ask when ambiguous
- Track what assumptions were made (provenance)

---

## GUIDE Mode (The Entry Point)

Half of users won't arrive knowing what playbook they need. They arrive with:

> "Client hired me to help with their Workday implementation. They just went live and there are issues. They sent me a bunch of exports but I don't even know what I'm looking at. Where do I start?"

This is NOT "run payroll parallel" or "compare these files." This is: **"Help me figure out what to do."**

### What GUIDE Mode Does

1. **Understand the engagement** - What were you hired to do? What's the problem?
2. **Inventory what exists** - What did they upload? What data is there?
3. **Connect the dots** - Given the problem + available data, what's the approach?
4. **Suggest a path** - "Based on what you've told me and what I see, I'd recommend starting with X"
5. **Guide through it** - Run the playbook, but explain WHY each step matters

### GUIDE is a Mode, Not a Category

Categories are actions: INGEST, COMPARE, ANALYZE, TRANSFORM, OUTPUT.

GUIDE is the meta-layer that sits ABOVE playbooks:

> "Let's figure out what playbook you need."

### Example GUIDE Flow

**Consultant:** "I've been asked to validate a UKG implementation before go-live. Client sent me a bunch of files but I don't know where to start."

**System:** "Got it - pre-go-live validation. Let me look at what you have."

*System scans uploads*

**System:** "I see you have:
- Employee master export (2,847 employees)
- Pay register from parallel test (2 pay periods)  
- Benefits enrollment file
- Tax configuration export
- Nothing from the legacy system

For go-live validation, I'd typically recommend:
1. Compare parallel payroll to legacy (but I don't have legacy data yet)
2. Audit employee data for gaps and issues
3. Validate benefits enrollments vs eligibility
4. Check tax configs against state requirements

**Can you get me the legacy pay registers for the same periods? That's the highest-value comparison.**

In the meantime, want me to start with the employee data audit? I can do that now with what I have."

### GUIDE Learns from Work

When GUIDE suggests a path and the consultant follows it, that becomes a pattern:

- "Pre-go-live validation" + these file types → this sequence of playbooks
- Stored in global memory
- Next consultant with similar situation gets smarter suggestions faster

The system acts like a senior consultant onboarding a junior. "Here's what I'd do, here's what I need, here's what I can do now."

---

## Value Crosswalks

Schema mapping (column A = column B) is one layer. VALUE mapping is another.

### The Problem

| Legacy System | New System |
|---------------|------------|
| `Department = "100"` | `Department = "ACCT-100"` |
| `Status = "A"` | `Status = "Active"` |
| `Location = "NYC01"` | `Location = "US-NY-001"` |

If you compare raw values, EVERYTHING looks like a discrepancy. The comparison is useless.

### The Solution: Crosswalk Tables

Before comparing, system needs value mappings:

| Field | Legacy Value | New Value |
|-------|--------------|-----------|
| Department | 100 | ACCT-100 |
| Department | 200 | FIN-200 |
| Status | A | Active |
| Status | T | Terminated |
| Location | NYC01 | US-NY-001 |

### Three Ways to Build Crosswalks

**1. Client Provides It**

> "Here's our mapping table from the implementation"

System ingests it, stores in project memory, applies automatically.

**2. System Infers It**

Pattern matching across datasets. If every "100" employee in legacy shows as "ACCT-100" in new, that's probably a match.

System proposes:
> "I noticed all employees with Department '100' in legacy have Department 'ACCT-100' in new. Should I treat these as the same?"

Consultant confirms or corrects.

**3. Clarification Builds It**

When discrepancies appear:
> "I see 47 employees with Department '100' in legacy but no matching value in new. The new system has 'ACCT-100' for these same employees. Are these equivalent?"

Built one answer at a time, stored for future use.

### Crosswalks in the Workflow

TRANSFORM step happens before COMPARE:

```
INGEST (legacy file)
INGEST (new file)
TRANSFORM (build/apply value crosswalk) ← maps values
COMPARE (now apples to apples)
ANALYZE (find REAL discrepancies, not mapping noise)
OUTPUT (report)
```

### Crosswalk Memory

**Project memory:**
Once built, crosswalk persists for this customer. Upload another legacy file next week, system already knows how to translate.

**Global memory:**
Some mappings are universal:
- Status codes (A/T/L → Active/Terminated/Leave) are often standard
- Common vendor migrations have known patterns (ADP → UKG, etc.)

New project with same migration path? System suggests: "This looks like an ADP to UKG migration. Want me to apply standard value mappings as a starting point?"

### Crosswalk Confidence

Not all mappings are certain:

| Confidence | Meaning | Action |
|------------|---------|--------|
| **High** | 100% of legacy values map consistently | Apply automatically |
| **Medium** | 90%+ map consistently, some exceptions | Apply with exceptions flagged |
| **Low** | Pattern unclear or conflicts exist | Ask consultant to confirm |

System shows its work:
> "Applied department crosswalk with 98% confidence. 12 employees have legacy department '999' which doesn't appear in new system - flagged for review."

---

## Open Questions (Parked)

1. **Schema/extraction docs per domain** - Needed to make COMPARE/ANALYZE smart per domain (HCM vs FINS vs ERP). Not foundation, but important for depth.

2. **UX AHA moment** - We're designing for consultants now. How does this translate when we go to end customers? Investor lens? (Scott has more here)

3. **Multi-user workflows** - When does one consultant's work need to connect to another's? Edge case or core requirement?

4. **Playbook versioning** - When a playbook gets refined, what happens to old versions? 

5. **Global memory promotion** - What's the threshold for promoting a project pattern to global? Human review or automatic?

---

## Success Criteria

**We know this works when:**

1. Consultant asks "compare these two pay registers" and gets categorized discrepancies with proven root causes in under 5 minutes

2. Same consultant clicks "Payroll Parallel" next month, answers 3 questions, gets complete workbook in under 30 seconds

3. System says "I found 23 CA employees with tax variance. High confidence it's tax table version. Gap: I don't have actual configs to prove it" - and the consultant trusts that assessment

4. M&A integration that would take 6 weeks with a team takes 2 days with one consultant and XLR8

5. Knowledge captured in playbooks survives consultant turnover - new hire runs senior's playbook on day 1

---

## Appendix: Context Engineering Alignment

This architecture maps to the six pillars of context engineering (per Weaviate):

| Pillar | XLR8 Implementation |
|--------|---------------------|
| **Agents** | Chat orchestrates decisions across feature categories |
| **Query Augmentation** | Consultative clarification refines user input |
| **Retrieval** | Five Truths data model (Reality, Intent, Config, Reference, Regulatory) |
| **Prompting** | Synthesis with Answer + SOLVE + Headline + Confidence + Gaps |
| **Memory** | Session, Project, Global layers |
| **Tools** | Feature categories (INGEST, COMPARE, ANALYZE, OUTPUT, etc.) |

The clarification system is query augmentation AND memory capture simultaneously.

---

## Version History

| Date | Change |
|------|--------|
| 2026-01-24 | **Phase 1 COMPLETE** - IntentEngine deployed and tested in production |
| 2026-01-24 | Fixed: Radio button options format mismatch (backend `{display,value}` → frontend `{id,label}`) |
| 2026-01-24 | Fixed: IntentEngine session persistence (was recreating on every request) |
| 2026-01-24 | Fixed: Syntax error in unified_chat.py (`elif` after `else`) |
| 2026-01-24 | Enhanced: Option labels now consultative, not technical |
| 2026-01-23 | Added GUIDE mode, Value Crosswalks sections |
| 2026-01-23 | Added Proactive Data Solicitation, Flexible Playbooks, Abstraction Layer, Temporal Context |
| 2026-01-23 | Initial vision document from strategic architecture session |

---

## Technical Notes (for next session)

### IntentEngine Architecture

```
User Question
    ↓
IntentEngine.analyze()
    ↓
Pattern Detection (regex triggers)
    ↓
Check Memory (session → project → ask)
    ↓
ClarificationNeeded OR ResolvedIntent
    ↓
SQL Generation (with intent context)
    ↓
Response (with parameters in footer)
```

### Key Files

| File | Purpose |
|------|---------|
| `intent_engine.py` | Core clarification logic, pattern definitions, memory |
| `query_engine.py` | Orchestrator, uses IntentEngine, manages session |
| `unified_chat.py` | API endpoint, applies clarifications to engine |

### Current Intent Patterns

| Pattern | Trigger | Question |
|---------|---------|----------|
| `employee_status` | "active", "current employees" | "How do you define 'active'?" |
| `temporal_analysis` | "by date", "over time", "trend" | "What are you trying to understand?" |
| `point_in_time` | "as of", "on date" | "What should 'as of' mean?" |
| `data_comparison` | "compare", "vs", "difference" | "What kind of comparison?" |
| `headcount` | "headcount", "how many employees" | "What should headcount include?" |
| `terminated_status` | "terminated", "left", "exited" | "What termination data?" |
| `grouping_dimension` | "by department", "by location" | "How would you like this grouped?" |

### Debugging Checklist

If clarifications not working:
1. Check logs for `[UNIFIED] *** CLARIFICATIONS RECEIVED`
2. Check logs for `[ENGINE] REUSING IntentEngine` (not "Created NEW")
3. Verify frontend sends `clarifications: {pattern_key: value}`
4. Verify options format: `{id, label}` not `{display, value}`
