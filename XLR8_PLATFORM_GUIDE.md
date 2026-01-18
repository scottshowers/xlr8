# XLR8 Platform Guide

**Last Updated:** January 18, 2026  
**Purpose:** Comprehensive reference for development continuity across sessions  
**Rule:** Read this document at the start of EVERY development conversation

---

## Related Documents (Reading Order)

1. **This document** - Always read first
2. **FLOW_MAP.md** - Current state of user flows and what needs building
3. **PARKING_LOT.md** - Backlog and pending items
4. **ARCHITECTURE.md** - Deep technical reference (only when needed)

---

## THE VISION

### What XLR8 Actually Is

**Not this:**
- A chatbot for HCM data
- A BI tool for UKG implementations  
- A niche consulting accelerator

**This:**
> **A decision acceleration platform for ANY enterprise software engagement.**

### The Insight

Every enterprise software engagement - whether it's Workday, SAP, Salesforce, or anything else - involves the same five activities:

1. **Comparing** data between systems
2. **Validating** configurations against rules
3. **Aggregating** data for analysis
4. **Mapping** between source and target
5. **Detecting** problems and anomalies

XLR8 does all 5. Universally. The engines don't care if the data is from UKG, Workday, SAP, Salesforce, NetSuite, or anything else.

### The Transformation

| Today (Consulting) | Tomorrow (Platform) |
|-------------------|---------------------|
| Customer brings problem | Customer brings problem |
| Consultant figures it out | Consultant assembles playbook from features |
| Delivers solution | Delivers solution |
| Knowledge walks out the door | **Playbook saved as IP** |
| Next customer = start over | Next customer = run playbook, handle exceptions |

**The result:** What used to take 40 hours of manual work takes 4 minutes. And every playbook becomes IP that makes the next engagement faster.

## THE BUSINESS MODEL

### Today (Consulting):
- Customer brings problem
- Consultant figures it out
- Delivers solution
- Knowledge walks out the door
- Next customer = start over

### Tomorrow (Platform):
- Customer brings problem
- Consultant assembles playbook from features
- Delivers solution
- **Playbook saved as IP**
- Next customer = run playbook, handle exceptions
- Platform gets smarter

### The Flywheel:
1. New problem → build playbook
2. Playbook runs → captures edge cases
3. Edge cases → refine playbook
4. Refined playbook → faster delivery
5. Eventually → customers self-serve common playbooks

### Revenue Evolution:
- **Now:** Consulting revenue (~$150K/month avg, lumpy)
- **Bridge:** Consulting + early platform clients
- **Scale:** Platform subscriptions + consulting for complex work
- **Exit:** Recurring platform revenue + playbook IP library

---

## CURRENT STATE

### What Exists:
- Working product (chat, BI, file upload, analysis)
- DuckDB + ChromaDB + Supabase architecture
- Intelligence layer (term index, SQL generation)
- Basic playbook structure
- 110 employees demo data ready

### What's Close:
- 5 engine abstraction (code exists, needs formalization)
- Feature configuration UI
- Playbook assembly UI
- Output → input flow wiring

### Estimated Build Time:
- Engine abstraction: 2-3 weeks
- Config/Assembly UI: 2 weeks
- Polish + demo-ready: 1-2 weeks
- **Total: 4-6 weeks to fundable demo**

---

## FINANCIAL REALITY

### Current Burn:
- ~$350K/month total
- ~$200K team salaries
- ~$150K cash flow timing gap (consulting AR)

### Revenue:
- ~$1.5M consulting revenue over next 10 months
- ~$150K/month average (but lumpy)
- Gap of ~$200K/month

### Runway:
- Line of credit buying ~60 days
- Need bridge funding to extend runway
- Can't wait for perfect - must move now

---

## THE FUNDING PLAN

### Phase 1: Bridge Round (Now → 60 days)

**Target:** $1-1.5M

**Structure:** 
- Convertible note or SAFE
- Valuation cap: $8-10M
- Dilution: 10-15%

**Sources:**
- Angels (HCM/HR Tech exits, ex-Big 4 partners)
- Your network (people who know you)
- Your buddy (FINS/ERP guy - brings credibility + connections)
- Small checks, fast decisions

**Use of Funds:**
- 12 months runway
- Finish product (4-6 weeks)
- Get 3-5 clients on platform
- Prove the model

### Phase 2: Prove It (6-12 months post-bridge)

**Milestones:**
- 3-5 paying platform clients
- $20-50K MRR (product revenue, not consulting)
- 2-3 engagement types working (HCM + ERP or M&A)
- Case studies: "40 hours → 4 hours"
- Playbook library growing

### Phase 3: Series A or Exit (12-18 months)

**Option A - Series A:**
- Raise $10-20M
- Valuation $40-80M
- Scale sales team
- Expand to 5+ verticals
- Target $2-5M ARR

**Option B - Strategic Exit:**
- Big 4 (Deloitte, Accenture, EY, KPMG)
- PE roll-up (Vista, Thoma Bravo)
- HCM adjacent (Ceridian, Paylocity, Paycor)
- Exit range: $30-50M+

---

## THE 60-DAY SPRINT

### Weeks 1-4: Finish Product
- [ ] Test pending fixes (term index, Pure Chat fallback)
- [ ] Lock 5 engine abstraction
- [ ] Playbook Builder UI complete
- [ ] Feature configuration working
- [ ] Output → input flow wired
- [ ] Demo data loaded and tested
- [ ] One end-to-end playbook running

### Weeks 5-6: Build Funding Assets
- [ ] Pitch deck (10-12 slides)
- [ ] Demo video (5 min, authentic, product does the talking)
- [ ] One-pager / executive summary
- [ ] Target angel list (50+ names)
- [ ] Outreach templates
- [ ] Intro asks to your buddy and UK friend

### Weeks 7-10: Fundraise
- [ ] Blast outreach (email, LinkedIn)
- [ ] Video does initial selling
- [ ] Take meetings with warm leads only
- [ ] Your buddy helps with energy/intros
- [ ] Close $1-1.5M in commitments
- [ ] Wire funds, extend runway

---

## THE PITCH (Draft)

### 60-Second Version:

> "Every enterprise software implementation - whether it's Workday, SAP, Salesforce, or anything else - involves the same five activities: comparing data, validating configurations, aggregating for analysis, mapping between systems, and detecting problems.
>
> We built XLR8 - a platform with 5 engines that do all of this universally. Consultants configure these engines into reusable 'playbooks' for any engagement type: implementations, M&A, migrations, vendor evaluations.
>
> What used to take 40 hours of manual work now takes 4 minutes. And every playbook we build becomes IP that makes the next engagement faster.
>
> We've proven it in HCM. The architecture is system-agnostic. We're raising $1.5M to expand into ERP and CRM and prove this scales across any enterprise software.
>
> We're not selling consulting hours. We're selling solved problems at scale. That's how 25 people compete with Deloitte."

### The Demo Flow (5 min video):

1. **Problem Setup** (30 sec)
   - "Client is implementing Workday. They uploaded 3 files. Let's validate their data."

2. **Load Playbook** (30 sec)
   - Show playbook selection
   - "Data Conversion Validation - 8 features, runs in sequence"

3. **Run Features** (2 min)
   - Compare: Source vs target census
   - Validate: Required fields, format checks
   - Detect: Duplicates, orphans
   - Aggregate: Summary stats
   - Show findings flowing to next feature

4. **Results** (1 min)
   - "142 issues found across 4 categories"
   - "Would have taken consultant 2 days. Took 3 minutes."
   - "Playbook saved. Next client with same need? One click."

5. **The Vision** (1 min)
   - "This same architecture works for M&A, vendor eval, any system"
   - "We're building the playbook library for enterprise software consulting"
   - Show engagement template view

---

## YOUR BUDDY - THE MULTIPLIER

### Why He Matters:
- Brings energy (you're tapped out on that)
- Knows FINS/ERP (validates "not just HCM" story)
- Has network (warm intros > cold outreach)
- Can be in the room with you (you answer product, he drives meeting)

### The Ask to Him:
- Not full-time, not co-founder (yet)
- Help with bridge round (intros, maybe joins meetings)
- Advisory role / small equity stake
- If it works, bigger conversation later

### What You Offer:
- Ground floor of something real
- Equity upside
- Platform that helps HIS world too (FINS/ERP)
- Partnership with someone who builds (you)



---

## THE PRODUCT HIERARCHY

This is the core mental model. Everything in XLR8 fits this hierarchy:

```
Engagement Template (Implementation, Support, M&A, Due Diligence, Vendor Eval)
  └── Playbooks (curated for specific outcomes)
        └── Features (configured engines with specific inputs/rules/outputs)
              └── Engines (Compare, Validate, Aggregate, Map, Detect)
```

### Level 1: Engines (The Foundation)

Five universal engines that work on ANY data:

| Engine | What It Does | Example |
|--------|--------------|---------|
| **Compare** | Thing A ↔ Thing B → Delta | File compare, parallel testing, migration validation |
| **Validate** | Data → Rules → Pass/Fail | Config validation, compliance checks, data quality |
| **Aggregate** | Data → Group By → Measure | Headcount by location, costs by department |
| **Map** | Source ↔ Target → Translation | Code crosswalks, field mapping, gap analysis |
| **Detect** | Data → Pattern → Matches | Duplicates, orphans, anomalies, outliers |

**Key point:** These engines are system-agnostic. The IP is in how they're configured and assembled.

### Level 2: Features (Configured Engines)

A Feature = Engine + specific inputs + rules + output format

Examples:
- "Duplicate Employee Detection" = Detect engine + employee data + SSN matching rule
- "Earnings Code Crosswalk" = Map engine + source codes + target codes
- "Headcount by Location" = Aggregate engine + census + location dimension

### Level 3: Playbooks (Assembled Features)

A Playbook = sequence of Features for a specific outcome

Examples:
- Year-End Readiness (12 features)
- Parallel Testing (8 features)
- Data Conversion Validation (10 features)
- M&A Harmonization (15 features)

**Critical concept: Output → Input Flow**
- Findings from one feature feed into the next
- Discovery findings → feed Data Conversion playbook
- Conversion findings → feed Parallel Testing playbook
- Creates workflow chains, not just checklists

### Level 4: Engagement Templates (Bundled Playbooks)

An Engagement Template = bundle of playbooks for a type of work

| Template | Playbooks Included |
|----------|-------------------|
| Implementation | ~15 playbooks (discovery, conversion, validation, parallel, go-live) |
| Support/Managed Services | ~5 playbooks (health checks, audits, optimization) |
| M&A | ~6 playbooks (discovery, harmonization, cost modeling) |
| Vendor Evaluation | ~4 playbooks (requirements, scoring, comparison) |

---

## MARKET OPPORTUNITY

### Proven (HCM):
- New implementations (UKG, Workday, ADP)
- Parallel payroll testing
- Year-end readiness
- Data conversion validation
- Config audits

### Unlocked (Any SaaS):
- **M&A:** Two companies becoming one - field mapping, cost modeling, harmonization
- **Vendor Evaluation:** Compare 3 PM tools, score against requirements
- **Migration Assessment:** Effort to move from System A to System B
- **Due Diligence:** What are we buying? What's the risk?
- **ERP Implementations:** SAP, Oracle, NetSuite
- **CRM Implementations:** Salesforce, HubSpot, Dynamics
- **ITSM:** ServiceNow, Jira

---

## OWNER & WORKING STYLE

**Scott** - HCMPACT CEO, XLR8 architect
- Technical architect and product owner, not a developer
- Works with Claude as primary development partner
- Requires **full file replacements**, not patches
- Values systematic, methodical approaches
- Strong exit timeline pressure - no gold-plating

**Development approach:**
- Document before building
- Update FLOW_MAP.md before touching code
- Clean as we go (docstrings, remove dead code, consolidate duplicates)

---

## CORE ARCHITECTURE

### The Five Truths

XLR8's intelligence is built on five layers of truth that get assembled for any analysis:

| Truth | What It Contains | Source |
|-------|------------------|--------|
| **Reality** | Actual client data (employees, deductions, tax setup) | Uploaded files |
| **Intent** | What the client wants to achieve | Project context, chat |
| **Configuration** | How their system is set up | Config exports, PDFs |
| **Reference** | Best practices, vendor standards | Reference Library |
| **Regulatory** | Compliance requirements (IRS, state, federal) | Standards uploads |

The **Compliance Truth** is derived by comparing the above five.

### Hub and Spoke Data Model

- **Hubs:** Core entity types (~70+ defined in BRIT). Examples: Employee, Earnings Code, Deduction Code, Tax Group
- **Spokes:** Relationships and attributes hanging off hubs
- Every config table IS a hub by definition
- Hubs exist even with 0 spokes ("100% configured, 0% in use")

### Intelligence Layer

How XLR8 understands queries and resolves them to data:

| Component | Purpose | Location |
|-----------|---------|----------|
| **term_index** | Maps keywords to tables/columns (semantic lookup) | `term_index.py` |
| **sql_assembler** | Generates SQL from resolved terms | `sql_assembler.py` |
| **metadata_reasoner** | Fallback when term_index fails | `metadata_reasoner.py` |
| **query_resolver** | Orchestrates resolution flow (NEEDS REFACTOR) | `query_resolver.py` |

### LLM Strategy

- **Local First:** DeepSeek for SQL generation, Mistral for synthesis
- **Claude API:** Fallback only for complex edge cases
- **Vision API:** PDF table extraction (pages 1-2, ~$0.04, cached by fingerprint)

### Data Storage

| Store | Purpose |
|-------|---------|
| **DuckDB** | Structured data, uploaded files, analysis results |
| **ChromaDB** | Vector embeddings for semantic search |
| **Supabase** | User auth, project metadata, persistent state |

---

## THE MASTER FLOW (8 Steps)

This is the primary user journey through XLR8. A consultant takes a client from project creation to deliverable export.

| Step | Name | What Happens |
|------|------|--------------|
| 1 | **Create/Modify** | Create project, set customer, assign playbooks |
| 2 | **Upload/Connect** | Upload files OR connect via API (UKG RaaS, etc.) |
| 3 | **Playbooks** | Select playbook + confirm data source mappings (table resolution) |
| 4 | **Analysis** | Run engines against data, execute playbook steps |
| 5 | **Findings** | View all findings from analysis |
| 6 | **Review** | Drill into findings, provide context, re-analyze |
| 7 | **Progress** | Track completion across steps (may be integrated into UI) |
| 8 | **Export** | Generate client deliverables |

**See FLOW_MAP.md for detailed component/endpoint mapping and current status.**

### Current State of Master Flow

| Step | Status | Notes |
|------|--------|-------|
| 1 | ✅ Working | Project creation functional |
| 2 | ✅ Working | File upload, PDF processing, column profiling |
| 3 | 🔧 **BROKEN** | Skips data source review, jumps to step 4 |
| 4 | 🔧 **BROKEN** | Not connected to playbook framework |
| 5 | 🔧 Partial | Exists but not pulling from framework |
| 6 | 🔧 Partial | Detail view exists, re-analyze missing |
| 7 | ❓ TBD | May be redundant - integrate into header? |
| 8 | ✅ Working | JSON export works, PDF planned |

---

## FEATURE INVENTORY

### Engines (Level 1 of Product Hierarchy)

| Engine | Location | Status | Notes |
|--------|----------|--------|-------|
| Aggregate | `backend/engines/aggregate.py` | ✅ Working | Count, sum, group by |
| Compare | `backend/engines/compare.py` | ✅ Working | Diff between datasets |
| Validate | `backend/engines/validate.py` | ✅ Working | Rule-based validation |
| Detect | `backend/engines/detect.py` | ✅ Working | Pattern matching, anomalies |
| Map | `backend/engines/map.py` | ✅ Working | Value translation |
| Export | `backend/engines/export.py` | ✅ Working | Format output |

### Playbook Framework (Level 3 of Product Hierarchy)

| Component | Location | Status | Notes |
|-----------|----------|--------|-------|
| Definitions | `playbooks/framework/definitions.py` | ✅ Working | Data classes for playbooks, steps, findings |
| Query Service | `playbooks/framework/query_service.py` | ✅ Working | Load playbook definitions |
| Progress Service | `playbooks/framework/progress_service.py` | ✅ Working | Track execution state |
| Execution Service | `playbooks/framework/execution_service.py` | ✅ Working | Run engines, collect findings |
| Match Service | `playbooks/framework/match_service.py` | ✅ Working | File → requirement matching |
| Analysis Inference | `playbooks/framework/analysis_inference.py` | ✅ Working | Step description → engine config |
| Router | `playbooks/framework/router.py` | ✅ Working | API endpoints |

### Data Management

| Feature | Location | Status | Notes |
|---------|----------|--------|-------|
| File Upload | `routers/upload.py` | ✅ Working | CSV, Excel, PDF |
| PDF Processing | `utils/pdf_vision_analyzer.py` | ✅ Working | Vision API table extraction |
| Column Profiling | `utils/upload_enrichment.py` | ✅ Working | Auto-detect types, domains |
| Schema Metadata | `_schema_metadata` table | ✅ Working | Tracks all uploaded tables |
| Term Index | `utils/intelligence/term_index.py` | ✅ Working | Keyword → table/column |
| API Connections | `routers/api_connections.py` | 🔧 Partial | UKG RaaS started |

### Chat & Intelligence

| Feature | Location | Status | Notes |
|---------|----------|--------|-------|
| Chat/Workspace | `pages/WorkspacePage.jsx` | ✅ Working | Natural language queries |
| Query Resolution | `utils/intelligence/query_resolver.py` | 🔧 Needs Refactor | Should use term_index + sql_assembler |
| Consultative Responses | `utils/consultative_synthesis.py` | ✅ Working | Senior consultant tone |
| Citation Tracking | `utils/intelligence/citation_tracker.py` | ✅ Working | Source attribution |

### Admin & Reference

| Feature | Location | Status | Notes |
|---------|----------|--------|-------|
| Reference Library | `pages/GlobalKnowledgePage.jsx` | ✅ Working | Upload standards |
| System Library | `integrations/system_library.py` | ✅ Working | Product schemas |
| Data Cleanup | `pages/DataCleanup.jsx` | ✅ Working | Remove orphaned data |
| Playbook Builder | `pages/EnginePlaybookBuilder.jsx` | 🔧 In Progress | Visual playbook creation |

### Frontend - Playbook UI Components

| Component | Location | Status | Notes |
|-----------|----------|--------|-------|
| PlaybookRunner | `components/PlaybookRunner.jsx` | ⚠️ Built, not integrated | 3-phase inline runner |
| DataSourcesReview | `components/DataSourcesReview.jsx` | ⚠️ Built, not integrated | Table resolution UI |
| PlaybookSteps | `components/PlaybookSteps.jsx` | ⚠️ Built, not integrated | Step execution UI |
| PlaybookFindings | `components/PlaybookFindings.jsx` | ⚠️ Built, not integrated | Findings review UI |
| PlaybooksPage | `pages/PlaybooksPage.jsx` | ✅ Working | Standalone playbook list |
| PlaybookSelectPage | `pages/PlaybookSelectPage.jsx` | 🔧 Needs integration | Master flow step 3 |

---

## KEY DATA TABLES

### DuckDB (`/data/structured_data.duckdb`)

| Table | Purpose |
|-------|---------|
| `_schema_metadata` | Tracks all uploaded tables (file, project, columns, row count) |
| `_column_profiles` | Column-level metadata (type, domain, top values) |
| `_term_index` | Keyword → table/column mappings |
| `_playbook_instances` | Playbook execution state per project |
| `_playbook_progress` | Step-level progress and findings |
| `[project]_[filename]_v[n]` | Actual uploaded data tables |

### Supabase

| Table | Purpose |
|-------|---------|
| `projects` | Project metadata (customer, name, assigned playbooks) |
| `users` | Authentication |
| `findings` | Persisted findings (may move to DuckDB) |



---

## CURRENT STATE & PRIORITIES

### What's Complete (GET HEALTHY Sprint)
- ✅ Data integrity issues resolved
- ✅ Performance hardening
- ✅ Five Truths pipeline architecture
- ✅ Universal engine implementation (all 5 engines working)
- ✅ Playbook framework backend (definitions, execution, progress, findings)
- ✅ Term index and column profiling
- ✅ PDF Vision processing

### Current Blocker: Master Flow Steps 3-6

**The Problem:**
- Built PlaybookRunner as inline component
- Master Flow expects separate routes per step
- Step 3 skips directly to Step 4 without data source review
- Steps 4-6 aren't connected to the playbook framework

**The Fix:**
1. Integrate DataSourcesReview into Step 3
2. Refactor ProcessingPage to use framework execution
3. Connect FindingsDashboard to framework findings
4. Add re-analyze capability to FindingDetailPage

**See FLOW_MAP.md for detailed breakdown.**

### The 60-Day Sprint Context

From SUMMARY_AND_PLAN.md - we're in a funding sprint:

| Weeks | Focus |
|-------|-------|
| 1-4 | Finish product (Master Flow working end-to-end) |
| 5-6 | Build funding assets (deck, demo video) |
| 7-10 | Fundraise (bridge round, $1-1.5M target) |

**Priority order:**
1. Master Flow Steps 3-6 integration (current blocker)
2. Build end-to-end playbook working (Year-End)
3. Demo-ready polish
4. Playbook Builder UI completion
5. API connectivity for UKG Pro
6. Schema compare (cross domain, cross multi vendor, friction detection during M&A/Vendor Eval/etc.)
7. Export Library templates with upload and recognition capabilities for use in Chat, Analytics, Playbooks
8. Review Chat Vocabulary and expand Natural Language comprehension.  Consider split screen chat.
9 Make sure learning engine is attached and being utilized correctly
10. Rewire existing functionality to Engines where needed
11. Consistent same level tool tips throughout product
12. Revisit Marketing/Sales pages and develop thoughtful materials


---

## KEY PATTERNS & DECISIONS

### Connection Pattern (Critical)
All services MUST use:
```python
from utils.structured_data_handler import get_structured_handler
handler = get_structured_handler()
conn = handler.conn
```
Do NOT create direct `duckdb.connect()` calls - causes conflicts.

### File Handling
- User uploads go to DuckDB with versioned table names: `[project]_[filename]_v[n]`
- `_schema_metadata` tracks current version (`is_current = TRUE`)
- Column profiles stored in `_column_profiles.top_values_json`

### Domain Agnostic Design
XLR8 is NOT just for HCM. The engines are domain-agnostic. Domain knowledge comes from:
- Uploaded standards (Reference Library)
- System schemas (`/config/*.json`)
- Learning layer (adapts to user preferences)

**Never hardcode domain-specific logic into engines.**

### Full File Replacements
Scott requires complete file replacements, not patches. Always provide the entire file content when making changes.

### Clean As We Go
When touching any file:
- Add/update docstrings
- Remove dead code
- Consolidate duplicates
- Don't leave TODOs without tickets

---

## KEY DATA TABLES

### DuckDB (`/data/structured_data.duckdb`)

| Table | Purpose |
|-------|---------|
| `_schema_metadata` | Tracks all uploaded tables (file, project, columns, row count) |
| `_column_profiles` | Column-level metadata (type, domain, top values) |
| `_term_index` | Keyword → table/column mappings |
| `_playbook_instances` | Playbook execution state per project |
| `_playbook_progress` | Step-level progress and findings |
| `[project]_[filename]_v[n]` | Actual uploaded data tables |

### Supabase

| Table | Purpose |
|-------|---------|
| `projects` | Project metadata (customer, name, assigned playbooks) |
| `users` | Authentication |
| `findings` | Persisted findings (may consolidate to DuckDB) |

---

## PROJECT STRUCTURE

### Frontend (`/frontend/src/`)
```
├── components/          # Reusable components
│   ├── ui/              # Design system (Button, Card, Badge)
│   ├── PlaybookRunner.jsx      # 3-phase runner (needs integration)
│   ├── DataSourcesReview.jsx   # Table resolution UI
│   ├── PlaybookSteps.jsx       # Step execution UI
│   └── PlaybookFindings.jsx    # Findings review UI
├── pages/               # Route-level components
├── context/             # React context (Project, Auth, Theme)
├── services/api.js      # Axios instance
└── App.jsx              # Route definitions
```

### Backend (`/backend/`)
```
├── main.py              # FastAPI entry point
├── engines/             # Universal analysis engines
│   ├── aggregate.py
│   ├── compare.py
│   ├── validate.py
│   ├── detect.py
│   ├── map.py
│   └── export.py
├── playbooks/framework/ # Playbook execution framework
├── routers/             # API route modules
├── utils/
│   ├── intelligence/    # Query resolution, term index
│   └── structured_data_handler.py  # DuckDB singleton
└── integrations/        # External system connectors
```

---

## HOW TO USE THIS DOCUMENT

### Starting a New Conversation
1. **Read this document first** - understand the vision and current state
2. **Read FLOW_MAP.md** - see what's broken and what needs building
3. **Ask Scott** what we're working on today
4. **Don't assume** - if something seems off, ask before building

### Before Building Anything
1. Identify which Master Flow step(s) it affects
2. Update FLOW_MAP.md with the plan
3. Confirm alignment with Scott
4. Then build

### After Completing Work
1. Update this document if features/status changed
2. Update FLOW_MAP.md with new state
3. Note any architectural decisions made

### Key Questions to Ask
- "Does this affect the Master Flow?"
- "Does this align with the product hierarchy (Engines → Features → Playbooks)?"
- "Is this demo-critical or can it wait?"
- "Am I building something new or fixing something broken?"

---

## DOCUMENT HISTORY

| Date | Change |
|------|--------|
| 2026-01-18 | Rewrote with strategic vision from SUMMARY_AND_PLAN.md |
| 2026-01-18 | Initial creation |
