# XLR8 Flow Map

**Last Updated:** January 18, 2026  
**Purpose:** Detailed mapping of user flows to components, routes, and backend endpoints  
**Rule:** Update this document BEFORE building anything that affects user flows

---

## MASTER FLOW (8 Steps)

The primary user journey from project creation to deliverable export.

### Step 1: Create/Modify Project

| Attribute | Value |
|-----------|-------|
| **Route** | `/projects/new` (create), `/projects/:id/edit` (modify) |
| **Component** | `CreateProjectPage.jsx`, `EditProjectPage.jsx` |
| **Flow Bar** | Yes, Step 1 |
| **Backend Endpoints** | `POST /api/projects`, `PUT /api/projects/:id` |
| **State Stored** | Supabase `projects` table |
| **Status** | ✅ Working |

**What Happens:**
- User enters customer name, project name
- Assigns playbooks to project
- Sets project metadata

**Exits To:** Step 2 (Upload)

---

### Step 2: Upload/Connect Data

| Attribute | Value |
|-----------|-------|
| **Route** | `/data` |
| **Component** | `DataPage.jsx` |
| **Flow Bar** | Yes, Step 2 |
| **Backend Endpoints** | `POST /api/upload/csv`, `POST /api/upload/excel`, `POST /api/upload/pdf` |
| **State Stored** | DuckDB tables, `_schema_metadata`, `_column_profiles`, `_term_index` |
| **Status** | ✅ Working |

**What Happens:**
- User uploads files (CSV, Excel, PDF)
- System processes and profiles data
- Creates term index entries for keyword lookup
- OR user connects via API (UKG RaaS, etc.)

**Exits To:** Step 3 (Playbooks)

---

### Step 3: Playbooks (Select + Data Source Confirmation)

| Attribute | Value |
|-----------|-------|
| **Route** | `/playbooks/select` |
| **Component** | `PlaybookSelectPage.jsx` → **NEEDS:** `DataSourcesReview.jsx` integration |
| **Flow Bar** | Yes, Step 3 |
| **Backend Endpoints** | |
| | `GET /api/playbooks/list` - Available playbooks |
| | `POST /api/playbooks/{id}/instance/{project}` - Create instance |
| | `GET /api/playbooks/{id}/definition` - Get steps with analysis configs |
| | `GET /api/playbooks/instance/{id}/step/{step}/resolve` - Get table resolutions |
| | `POST /api/playbooks/instance/{id}/step/{step}/resolve` - Set manual resolution |
| | `GET /api/playbooks/tables/{project}` - Available tables for dropdown |
| **State Stored** | `_playbook_instances`, `step_progress.resolved_tables` |
| **Status** | 🔧 BROKEN - Currently skips to Step 4 without data source review |

**What Should Happen:**
1. User sees assigned playbooks for project
2. User selects which playbook to run
3. System shows DataSourcesReview:
   - Each step's data requirements
   - Auto-resolved tables (via term_index)
   - Manual override dropdowns
   - Status badges (Ready / Needs Attention / Verify)
4. User confirms data sources
5. Proceed to Step 4

**Current Problem:**
- `PlaybookSelectPage.jsx` calls `navigate('/processing')` directly
- Never shows `DataSourcesReview`
- Table resolution never happens before execution

**Fix Required:**
- Integrate `DataSourcesReview` into `PlaybookSelectPage`
- Only allow "Run Analysis" after data sources confirmed
- Pass `instance_id` to Step 4

**Exits To:** Step 4 (Analysis) with confirmed `instance_id`

---

### Step 4: Analysis (Execute Playbook Steps)

| Attribute | Value |
|-----------|-------|
| **Route** | `/processing`, `/processing/:jobId` |
| **Component** | `ProcessingPage.jsx` → **NEEDS:** Refactor to use framework |
| **Flow Bar** | Yes, Step 4 |
| **Backend Endpoints** | |
| | `POST /api/playbooks/instance/{id}/step/{step}/execute` - Execute single step |
| | `POST /api/playbooks/instance/{id}/execute-all` - Execute all steps |
| | `GET /api/playbooks/instance/{id}/progress` - Get execution progress |
| **State Stored** | `step_progress.status`, `step_progress.findings`, `step_progress.engine_results` |
| **Status** | 🔧 BROKEN - Not connected to playbook framework |

**What Should Happen:**
1. Receive `instance_id` from Step 3
2. Show list of steps with progress
3. Execute steps (one-by-one or all)
4. Display progress bar as steps complete
5. Show finding counts per step
6. Auto-advance to Findings when complete

**Current Problem:**
- `ProcessingPage.jsx` uses old analysis pattern
- Not connected to `execution_service`
- No awareness of framework instance

**Fix Required:**
- Refactor to accept `instance_id`
- Use `POST /api/playbooks/instance/{id}/step/{step}/execute`
- Show real-time progress from framework

**Exits To:** Step 5 (Findings) when analysis complete

---

### Step 5: Findings (View All Findings)

| Attribute | Value |
|-----------|-------|
| **Route** | `/findings` |
| **Component** | `FindingsDashboard.jsx` → **NEEDS:** Connect to framework |
| **Flow Bar** | Yes, Step 5 |
| **Backend Endpoints** | |
| | `GET /api/playbooks/instance/{id}/progress` - Includes all findings |
| | `GET /api/findings?project_id={id}` - Legacy endpoint |
| **State Stored** | `step_progress.findings` (in framework) |
| **Status** | 🔧 PARTIAL - Exists but not connected to framework |

**What Should Happen:**
1. Display all findings from all executed steps
2. Group by severity (Critical, High, Medium, Low, Info)
3. Filter by step, status, category
4. Show finding count summary
5. Click finding to drill into Step 6

**Current Problem:**
- `FindingsDashboard.jsx` may use legacy findings source
- Need to pull from playbook framework instance

**Fix Required:**
- Connect to `GET /api/playbooks/instance/{id}/progress`
- Extract findings from all steps
- Pass `instance_id` and `finding_id` to Step 6

**Exits To:** Step 6 (Review) when clicking a finding

---

### Step 6: Review (Drill-In + Re-Analyze)

| Attribute | Value |
|-----------|-------|
| **Route** | `/findings/:findingId` |
| **Component** | `FindingDetailPage.jsx` → **NEEDS:** Re-analyze capability |
| **Flow Bar** | Yes, Step 6 |
| **Backend Endpoints** | |
| | `GET /api/playbooks/instance/{id}/progress` - Get finding details |
| | `PUT /api/playbooks/instance/{id}/finding/{finding_id}` - Update status |
| | `POST /api/playbooks/instance/{id}/step/{step}/execute` - Re-analyze with context |
| **State Stored** | `finding.status`, `finding.notes`, `step_progress.ai_context` |
| **Status** | 🔧 PARTIAL - Detail view exists, re-analyze missing |

**What Should Happen:**
1. Show finding detail:
   - Title, description, severity
   - Source data (which table, which rows)
   - Guidance/remediation
   - Evidence (sample data)
2. Allow consultant to:
   - Acknowledge (mark as reviewed)
   - Suppress (false positive)
   - Add notes
   - **Provide context and re-analyze** ← KEY FEATURE
3. Re-analyze sends `ai_context` to execution service
4. New findings replace old for that step

**Current Problem:**
- Re-analyze capability not implemented
- Context input not wired to backend

**Fix Required:**
- Add context input field
- Wire to `POST /api/playbooks/instance/{id}/step/{step}/execute` with `ai_context`
- Refresh findings after re-analysis

**Exits To:** Back to Step 5, or forward to Step 7/8

---

### Step 7: Progress (Track Completion)

| Attribute | Value |
|-----------|-------|
| **Route** | `/progress/:playbookId` (current), or integrated into header |
| **Component** | `ProgressTrackerPage.jsx` |
| **Flow Bar** | Yes, Step 7 |
| **Backend Endpoints** | `GET /api/playbooks/instance/{id}/progress` |
| **State Stored** | Derived from `instance.completed_steps`, `instance.total_steps` |
| **Status** | ❓ QUESTIONABLE - May be redundant |

**Discussion:**
- Progress should be visible THROUGHOUT steps 3-6
- Could be a header element showing "Step 5 of 12 complete"
- Dedicated page may be unnecessary

**Options:**
1. Keep as separate step for detailed progress view
2. Integrate into header/sidebar, remove from flow
3. Make it the "summary before export" view

**Decision Needed:** TBD with Scott

**Exits To:** Step 8 (Export)

---

### Step 8: Export (Generate Deliverables)

| Attribute | Value |
|-----------|-------|
| **Route** | `/export` |
| **Component** | `ExportPage.jsx` |
| **Flow Bar** | Yes, Step 8 |
| **Backend Endpoints** | |
| | `POST /api/export/generate` - Generate export |
| | `GET /api/export/formats` - Available formats |
| **State Stored** | Generated files |
| **Status** | ✅ Working (JSON), 🔧 Planned (PDF) |

**What Happens:**
1. Select export format (JSON, PDF, Word)
2. Select which findings/sections to include
3. Generate deliverable
4. Download or email to client

**Exits To:** Done, or back to Step 5/6 for more work

---

## FLOW STATE MANAGEMENT

### How Instance State Flows Between Steps

```
Step 3 (Playbooks)
    │
    │ Creates instance via POST /api/playbooks/{id}/instance/{project}
    │ Returns: instance_id
    │
    ▼
Step 4 (Analysis)
    │
    │ Receives: instance_id (via URL param or context)
    │ Executes steps, stores findings in instance.progress
    │
    ▼
Step 5 (Findings)
    │
    │ Receives: instance_id
    │ Reads findings from GET /api/playbooks/instance/{id}/progress
    │
    ▼
Step 6 (Review)
    │
    │ Receives: instance_id, finding_id
    │ Updates findings, re-analyzes as needed
    │
    ▼
Step 8 (Export)
    │
    │ Receives: instance_id
    │ Generates deliverable from instance data
```

### Instance ID Passing Options

1. **URL Parameter:** `/processing/{instance_id}`, `/findings/{instance_id}`
2. **React Context:** `PlaybookContext` with `activeInstanceId`
3. **URL Query:** `/processing?instance={id}`

**Recommended:** URL parameter for bookmarkability + context for convenience

---

## WHAT NEEDS TO BE BUILT

### Priority 1: Step 3 Integration
- [ ] Add `DataSourcesReview` to `PlaybookSelectPage`
- [ ] Show data source confirmation before allowing "Run Analysis"
- [ ] Create instance on playbook selection
- [ ] Pass `instance_id` to Step 4

### Priority 2: Step 4 Refactor
- [ ] Refactor `ProcessingPage` to use framework
- [ ] Accept `instance_id` from Step 3
- [ ] Execute via `/api/playbooks/instance/{id}/step/{step}/execute`
- [ ] Show real progress from framework

### Priority 3: Step 5 Connection
- [ ] Connect `FindingsDashboard` to framework
- [ ] Pull findings from instance progress
- [ ] Pass context to Step 6

### Priority 4: Step 6 Re-Analyze
- [ ] Add context input to `FindingDetailPage`
- [ ] Wire re-analyze to execution endpoint
- [ ] Refresh findings after re-analysis

### Priority 5: Progress Integration
- [ ] Decide on Step 7 approach
- [ ] Add progress indicator to header/sidebar

---

## DOCUMENT HISTORY

| Date | Change |
|------|--------|
| 2026-01-18 | Initial creation - mapped all 8 steps with current state and fixes needed |
