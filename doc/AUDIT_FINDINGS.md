# XLR8 Full Route & Page Audit
## Generated: January 16, 2026

---

## ROUTE INVENTORY

### Public Routes (no auth):
| Route | Component | Layout |
|-------|-----------|--------|
| / | Landing | None |
| /login | LoginPage | None |
| /welcome | WelcomePage | None |
| /story | StoryPage | None |
| /journey | JourneyPage | None |
| /hype | HypeVideo | None |
| /architecture | ArchitecturePage | None |
| /architecture/metrics-pipeline | MetricsPipelinePage | None |

### Protected Routes - No Flow Bar:
| Route | Component | Layout |
|-------|-----------|--------|
| /mission-control | MissionControl | Page (MainLayout) |
| /dashboard | MissionControl | Page (MainLayout) |
| /projects | ProjectsPage | Page (MainLayout) |
| /projects/:id/hub | ProjectHub | Page (MainLayout) |
| /data | DataPage | Page (MainLayout) |
| /data/explorer | DataExplorer | Page (MainLayout) |
| /data/model | DataModelPage | Page (MainLayout) |
| /vacuum | VacuumUploadPage | Page (MainLayout) |
| /vacuum/explore/:jobId | VacuumExplore | Page (MainLayout) |
| /vacuum/mapping/:jobId | VacuumColumnMapping | Page (MainLayout) |
| /playbooks | PlaybooksPage | Page (MainLayout) |
| /build-playbook | PlaybookWireupPage | Page (MainLayout) |
| /workspace | WorkspacePage | Page (MainLayout) |
| /analytics | AnalyticsPage | Page (MainLayout) |
| /reference-library | ReferenceLibraryPage | Page (MainLayout) |
| /standards | StandardsPage | Page (MainLayout) |
| /data-health | DataHealthPage | Page (MainLayout) |
| /admin | AdminHub | Page (MainLayout) |
| /admin/settings | AdminPage | Page (MainLayout) |
| /admin/data-cleanup | DataCleanup | Page (MainLayout) |
| /admin/endpoints | AdminEndpoints | Page (MainLayout) |
| /admin/intelligence-test | IntelligenceTestPage | Page (MainLayout) |
| /admin/playbook-builder | PlaybookBuilderPage | Page (MainLayout) |
| /learning-admin | AdminDashboard | Page (MainLayout) |

### Protected Routes - With Flow Bar:
| Route | Component | Layout | Step |
|-------|-----------|--------|------|
| /projects/new | CreateProjectPage | FlowPage | 1 |
| /upload | UploadDataPage | FlowPage | 2 |
| /playbooks/select | PlaybookSelectPage | FlowPage | 3 |
| /processing | ProcessingPage | FlowPage | 4 |
| /processing/:jobId | ProcessingPage | FlowPage | 4 |
| /findings | FindingsDashboard | FlowPage | 5 |
| /findings/:findingId | FindingDetailPage | FlowPage | 6 |
| /progress/:playbookId | ProgressTrackerPage | FlowPage | 7 |
| /export | ExportPage | FlowPage | 8 |

### Redirects:
| From | To |
|------|-----|
| /data-cleanup | /admin/data-cleanup |
| /admin-endpoints | /admin/endpoints |
| /data-model | /data-health |
| /chat | /workspace |
| /status | /admin |
| /system | /admin |
| /secure20 | /playbooks |
| /packs | /playbooks |
| /playbooks/builder | /admin/playbook-builder |
| /query-builder | /analytics |
| /bi | /analytics |
| * (catch-all) | /dashboard |

---

## PAGE FILE INVENTORY

### Files in /pages/ directory (40 total):
```
AdminDashboard.jsx
AdminEndpoints.jsx
AdminHub.jsx
AdminPage.jsx
AnalyticsPage.jsx
ArchitecturePage.jsx
CreateProjectPage.jsx
DashboardPage.jsx        ← NOT IMPORTED (orphan?)
DataCleanup.jsx
DataExplorer.jsx
DataHealthPage.jsx
DataModelPage.jsx
DataPage.jsx
ExportPage.jsx
FindingDetailPage.jsx
FindingsDashboard.jsx
HypeVideo.jsx
IntelligenceTestPage.jsx
JourneyPage.jsx
Landing.jsx
LoginPage.jsx
MetricsPipelinePage.jsx
MissionControl.jsx
PlaybookBuilderPage.jsx
PlaybookSelectPage.jsx
PlaybookWireupPage.jsx
PlaybooksPage.jsx
ProcessingPage.jsx
ProgressTrackerPage.jsx
ProjectHub.jsx
ProjectsPage.jsx
ReferenceLibraryPage.jsx
StandardsPage.jsx
StoryPage.jsx
UploadDataPage.jsx
VacuumColumnMapping.jsx
VacuumExplore.jsx
VacuumUploadPage.jsx
WelcomePage.jsx
WorkspacePage.jsx
```

### Imported in App.jsx (38):
All files except `DashboardPage.jsx` are imported.

---

## NAVIGATION AUDIT

### Where does each page navigate TO?

#### MissionControl.jsx:
- Finding row click → `/findings/${finding.id}`
- Project card click → `/projects/${project.id}`

#### ProjectsPage.jsx:
- Project click → `/projects/${project.id}/hub`
- Edit menu → `/projects/${project.id}/hub`
- New Project button → `/projects/new`

#### ProjectHub.jsx:
- Back button → `/projects`
- Upload Data → `/upload`
- View Findings → `/findings`

#### CreateProjectPage.jsx:
- After create → ??? (need to check)

#### MainLayout Sidebar:
- Mission Control → `/mission-control`
- Projects → `/projects`
- Analytics → `/analytics`
- Platform Health → `/admin`
- Playbook Builder → `/admin/playbook-builder`
- Standards Library → `/standards`

#### MainLayout FlowBar:
- Step 1 → `/projects/new`
- Step 2 → `/upload`
- Step 3 → `/playbooks/select`
- Step 4 → `/processing`
- Step 5 → `/findings`
- Step 6 → `/findings`
- Step 7 → `/progress`
- Step 8 → `/export`

---

## BUGS FOUND AND FIXED

### BUG 1: Wrong context method name (CRITICAL - caused blank screens)
**Pages affected**: ProjectHub.jsx, ProjectsPage.jsx, DashboardPage.jsx
**Problem**: Used `setActiveProject` but context exports `selectProject`
**Result**: Runtime error crashed component → blank screen
**Fixed**: Changed all to use `selectProject`

### BUG 2: MissionControl wrong navigation path
**File**: MissionControl.jsx line 386
**Problem**: Navigated to `/projects/${id}` instead of `/projects/${id}/hub`
**Result**: Route didn't exist, fell through to catch-all → dashboard
**Fixed**: Changed to `/projects/${id}/hub`

---

## POTENTIAL ISSUES IDENTIFIED

### 1. DashboardPage.jsx is orphaned
- File exists but not imported in App.jsx
- /dashboard route points to MissionControl instead

### 2. MissionControl navigates to wrong route
- Clicks project card → `/projects/${project.id}`
- But that route doesn't exist!
- Should be → `/projects/${project.id}/hub`

### 3. FlowBar Step 7 has incomplete path
- Links to `/progress` without playbookId
- Route expects `/progress/:playbookId`

### 4. Multiple pages may still have old MainLayout wrappers
- Need to verify each page doesn't double-wrap

---

## NEXT: VERIFY EACH PAGE STRUCTURE
