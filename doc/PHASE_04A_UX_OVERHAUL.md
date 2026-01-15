# Phase 4A: UX Overhaul - Production Design System

**Status:** IN PROGRESS  
**Total Estimated Hours:** 29-39  
**Dependencies:** Backend pipeline (DO NOT TOUCH)  
**Last Updated:** January 15, 2026

---

## Objective

Transform XLR8 frontend from functional prototype to production-ready application with:
- **Cohesive design system** (colors, typography, spacing, components)
- **Three-interface model** (Consultant, Customer Portal, Admin)
- **Collapsible sidebar + contextual flow bar** navigation
- **Mission Control** cross-project review queue hub
- **Page-by-page implementation** to avoid compaction

**CRITICAL RULE:** UI/UX changes ONLY. Backend pipeline stays completely untouched.

---

## Design System Principles

### Color Palette

```css
/* Primary Brand */
--grass-green: #83b16d;
--grass-green-dark: #698f57;
--grass-green-light: #a8ca99;

/* Semantic Colors */
--critical: #993c44;
--critical-dark: #7d2f36;
--warning: #f59e0b;
--warning-dark: #d97706;
--info: #2766b1;
--info-dark: #1e4d8b;

/* Neutrals */
--bg-primary: #f6f5fa;
--bg-secondary: #ffffff;
--text-primary: #2a3441;
--text-secondary: #5f6c7b;
--text-muted: #a2a1a0;
--border-light: #e1e8ed;
--border-medium: #d1d5db;
--surface-light: #f9fafb;
--surface-medium: #f0f4f7;
```

### Typography

```css
/* Headings */
--font-header: 'Sora', sans-serif;
--font-body: 'Manrope', sans-serif;

/* Sizes */
--text-xs: 11px;
--text-sm: 13px;
--text-base: 14px;
--text-lg: 16px;
--text-xl: 18px;
--text-2xl: 22px;
--text-3xl: 28px;
--text-4xl: 36px;

/* Weights */
--weight-normal: 400;
--weight-medium: 500;
--weight-semibold: 600;
--weight-bold: 700;
```

### Spacing System

```css
/* 8px base unit */
--space-1: 4px;
--space-2: 8px;
--space-3: 12px;
--space-4: 16px;
--space-5: 20px;
--space-6: 24px;
--space-7: 28px;
--space-8: 32px;
--space-10: 40px;
--space-12: 48px;
```

### Component Patterns

**Cards:**
- Border radius: 16px
- Border: 1px solid var(--border-light)
- Padding: 24-32px
- Hover: translateY(-4px) + shadow

**Buttons:**
- Border radius: 10px
- Padding: 12px 28px
- Primary: Gradient (grass-green → grass-green-dark)
- Secondary: White with border

**Badges:**
- Border radius: 16px
- Padding: 6px 14px
- Font size: 11px, uppercase, 700 weight

**Inputs:**
- Border radius: 8px
- Border: 1.5px solid var(--border-light)
- Focus: border-color grass-green + shadow

---

## Three-Interface Architecture

### 1. Consultant Interface (Daily Driver)

**Purpose:** Consultant's daily work environment  
**Navigation:** Collapsible sidebar + contextual flow bar  
**Access:** All consultants

**Pages:**
- Mission Control (cross-project review queue)
- Projects (list and workspace)
- Data management (upload, vacuum, explorer)
- Playbooks (assign, review findings, track progress)
- Analytics (query builder, chat)

### 2. Customer Portal (Phase 2 - Optional)

**Purpose:** Read-only visibility for customers  
**Navigation:** Simplified sidebar  
**Access:** Customers only

**Pages:**
- Dashboard (org intelligence, health score)
- Chat (limited scope)

### 3. Admin Module (Ops/Platform)

**Purpose:** Platform management, content building  
**Navigation:** Separate from consultant interface  
**Access:** Admins only

**Pages:**
- Platform Health (costs, usage, metrics)
- Playbook Builder
- Product Schemas (view by product, compare, API connections)
- Standards Library
- Reference Data

---

## Navigation Architecture

### Collapsible Sidebar (Always Present)

**Fixed left:** 260px wide, collapsible to 0px  
**Sections:**
- Navigation (Mission Control, Projects, Analytics)
- Recent Projects (quick jump)
- System (Admin, Playbook Builder, Standards)

**Behavior:**
- Smooth cubic-bezier transition
- Toggle button floats when collapsed
- Persists across page navigation

### Flow Bar (Contextual - In-Project Only)

**Fixed top:** Below header, 52px height  
**Shows:** When inside a project workflow  
**7 Steps:**
1. Create → 2. Upload → 3. Analysis → 4. Findings → 5. Detail → 6. Playbook → 7. Progress

**States:**
- Completed (green background, checkmark)
- Active (green fill, white text)
- Pending (gray, not yet reached)

**Behavior:**
- Each step clickable (jump to any step)
- Auto-updates based on project state
- Hidden on Mission Control (cross-project view)

### Header (Always Present)

**Fixed top:** 64px height  
**Left:** XLR8 logo (proper H shape) + "HCMPACT Intelligence"  
**Center:** Search bar (future)  
**Right:** Chat icon, notifications (with badge), settings, user menu

---

## Page-by-Page Implementation Plan

### Phase 1: Foundation (4-6 hours)

**Create Design System CSS**
- File: `/frontend/src/styles/design-system.css`
- CSS custom properties for colors, typography, spacing
- Import in `/frontend/src/index.css`

**Create Reusable Components**
- `/frontend/src/components/ui/Button.jsx`
- `/frontend/src/components/ui/Card.jsx`
- `/frontend/src/components/ui/Badge.jsx`
- `/frontend/src/components/ui/PageHeader.jsx`

**Risk:** 🟢 ZERO (new files, no dependencies)

### Phase 2: Core Layout (3-4 hours)

**Update Header Component**
- File: `/frontend/src/components/Header.jsx` (or create new)
- XLR8 logo with proper H SVG
- Search bar placeholder
- Icons: chat, notifications (badge), settings
- User menu dropdown

**Update Sidebar Component**
- File: `/frontend/src/components/Sidebar.jsx` (new)
- Collapsible behavior
- Sections: Navigation, Recent Projects, System
- Active state highlighting
- Smooth transitions

**Create Flow Bar Component**
- File: `/frontend/src/components/FlowBar.jsx` (new)
- 7-step indicator
- Conditional rendering (only in-project)
- Clickable steps
- State management (completed/active/pending)

**Update Layout.jsx**
- Integrate Header, Sidebar, FlowBar
- Handle collapsed state
- Adjust main content margins

**Risk:** 🟡 LOW (visual changes only, no logic changes)

### Phase 3: Mission Control (4-5 hours)

**File:** `/frontend/src/pages/MissionControl.jsx` (new)  
**Route:** `/mission-control` (new)

**Features:**
- 4 stat cards (Awaiting Review, Critical, In Progress, Approved)
- Cross-project review queue
- Filters (All, Critical, Warning, Info)
- Batch actions (approve/reject/false positive)
- Finding rows with full metadata
- Projects with pending work cards

**Backend:** Uses existing GET /findings, GET /projects  
**Risk:** 🟡 LOW (new page, uses existing APIs)

### Phase 4: Finding Detail / Massage (4-5 hours)

**File:** `/frontend/src/pages/FindingDetail.jsx` (revamp)  
**Route:** `/findings/:id`

**Features:**
- Editable title, severity, description
- Consultant notes (internal only)
- Impact analysis (affected records, departments, effort)
- Recommended actions
- Provenance section (how we found it, data lineage)
- Approve/reject buttons
- Related findings sidebar

**Backend:** Needs new endpoints:
- PATCH /findings/:id/approve
- PATCH /findings/:id/reject
- PATCH /findings/:id (update fields)

**Risk:** 🟠 MEDIUM (new endpoints needed, WAIT FOR APPROVAL)

### Phase 5: Project Workspace (6-8 hours)

**File:** `/frontend/src/pages/ProjectWorkspace.jsx` (new)  
**Route:** `/projects/:id`

**4 Tabs:**
1. **Overview:** Client info, org intelligence (auto-generated), health metrics
2. **Data:** Upload, vacuum upload, processing status, tables, explorer, relationships, health
3. **Playbooks:** Assign button, active playbooks list, action tracker, findings review, export
4. **Analytics:** Query builder, chat

**Features:**
- Tab state persistence
- Flow bar shows based on active tab
- Quick stats in overview
- Data health visualization

**Backend:** Uses existing APIs  
**Risk:** 🟡 LOW (reorganizing existing pages into tabs)

### Phase 6: Vacuum UX Refresh (2-3 hours)

**Files:**
- `/frontend/src/pages/VacuumUploadPage.jsx` (refresh)
- `/frontend/src/pages/VacuumExplore.jsx` (refresh)

**Changes:**
- Apply design system styling
- Update to match new card/button components
- Keep ALL existing logic untouched

**Risk:** 🟢 ZERO (pure styling, no logic changes)

### Phase 7: Admin Module (6-8 hours)

**New Pages:**
- `/frontend/src/pages/admin/ProductSchemas.jsx` (NEW)
- `/frontend/src/pages/admin/SchemaCompare.jsx` (NEW)
- `/frontend/src/pages/admin/APIConnections.jsx` (NEW)
- `/frontend/src/pages/admin/PlatformHealth.jsx` (revamp)

**Features:**
- **Product Schemas:** View by product/domain, search, filter
- **Schema Compare:** Compare 2 products, gap analysis, compatibility scores
- **API Connections:** Manage SaaS API credentials, test connections
- **Platform Health:** Real-time cost tracking, processing queue, storage usage

**Backend:** Needs new endpoints:
- GET /admin/schemas
- GET /admin/schemas/:product_id
- GET /admin/schemas/compare/:source/:target
- GET /admin/api-connections
- POST /admin/api-connections

**Risk:** 🟠 MEDIUM (new functionality, requires backend work)

---

## Implementation Rules

### DO NOT TOUCH

❌ `/backend/routers/` - API endpoints  
❌ `/backend/services/` - Intelligence services  
❌ `/backend/utils/` - Detection, analysis, LLM orchestration  
❌ `/backend/models/` - Data models  
❌ `playbooks/` - Playbook definitions  
❌ Database schema

**If it processes data, analyzes intelligence, or generates findings → WE DON'T TOUCH IT**

### SAFE TO MODIFY

✅ `/frontend/src/pages/` - Page layouts  
✅ `/frontend/src/components/` - UI components  
✅ `/frontend/src/styles/` - CSS/styling  
✅ `/frontend/src/App.jsx` - Routing structure  
✅ Component prop interfaces  
✅ Data display logic (how we SHOW results)

### File Creation Strategy

**For SHORT content (<100 lines):**
- Create complete file in one tool call
- Save directly to target location

**For LONG content (>100 lines):**
- Use ITERATIVE EDITING
- Build file across multiple tool calls
- Add content section by section

**For EXISTING files:**
- Use str_replace for targeted changes
- Never replace entire file unless <200 lines

---

## Component File Structure

### Reusable UI Components

```
frontend/src/components/ui/
├── Button.jsx          # Primary, secondary, danger variants
├── Card.jsx            # White card with hover effects
├── Badge.jsx           # Critical, warning, info variants
├── PageHeader.jsx      # Title + subtitle + actions
├── StatCard.jsx        # Stats with icon, value, trend
├── FilterBar.jsx       # Filter button group
├── FindingRow.jsx      # Single finding in list
└── EmptyState.jsx      # No data placeholders
```

### Layout Components

```
frontend/src/components/
├── Header.jsx          # Top header with logo, search, user menu
├── Sidebar.jsx         # Collapsible navigation sidebar
├── FlowBar.jsx         # 7-step contextual flow indicator
└── Layout.jsx          # Main layout wrapper
```

### Page Components

```
frontend/src/pages/
├── MissionControl.jsx           # Cross-project review queue
├── ProjectWorkspace.jsx         # 4-tab project view
├── FindingDetail.jsx            # Finding massage interface
├── VacuumUploadPage.jsx         # Specialty upload
├── VacuumExplore.jsx            # Vacuum data explorer
└── admin/
    ├── ProductSchemas.jsx       # Schema viewer by product
    ├── SchemaCompare.jsx        # Product comparison
    ├── APIConnections.jsx       # API credential management
    └── PlatformHealth.jsx       # Cost tracking, metrics
```

---

## Success Criteria

### Visual Consistency
✅ All pages use design system colors, typography, spacing  
✅ Components match mockup styling (borders, shadows, hover states)  
✅ Smooth transitions and animations throughout

### Navigation
✅ Sidebar collapses smoothly, persists state  
✅ Flow bar shows only in-project, updates correctly  
✅ Clear active state indicators  
✅ Breadcrumbs where appropriate

### Functionality
✅ All existing features still work  
✅ No broken API calls  
✅ Form submissions function correctly  
✅ Data displays accurately

### Pipeline Safety
✅ Backend untouched (no changes to routers, services, utils, models)  
✅ No database migrations  
✅ Existing API contracts unchanged

---

## Testing Strategy

### Per-Page Checklist

Before marking any page "complete":

1. **Visual:** Matches mockup styling (colors, spacing, typography)
2. **Interactive:** All buttons, links, forms work
3. **Responsive:** Looks good when sidebar collapsed
4. **Data:** API calls return expected data
5. **Navigation:** Links go to correct routes
6. **Console:** No errors in browser console
7. **Network:** No failed API requests

### Integration Testing

After each phase:

1. **Cross-Page:** Navigate between pages smoothly
2. **State:** Sidebar collapse persists across navigation
3. **Data Flow:** Project selection works across components
4. **Auth:** Protected routes still protected
5. **Pipeline:** Backend still processing data correctly

---

## Open Questions (Awaiting Scott's Decisions)

### Chat Placement & Behavior
- Where does chat open? (slide-out panel, full page, modal?)
- What's the scope? (project-specific or cross-project?)
- What can users ask? (data queries, analysis, help, all of above?)

### VacuumColumnMapping.jsx
- Still used or deprecate?
- If used, include in Phase 6 refresh

### Schema Visualization
- Do we have schema data already collected?
- Building UI before data, or data exists?
- What products currently have schemas?

### API Connections Page
- What should it manage? (credentials, status, refresh triggers, all?)

### Customer Portal Priority
- Phase 1 (build now) or Phase 2 (defer)?

---

## Version History

| Date | Change |
|------|--------|
| 2026-01-15 | Complete rewrite - design system, 3-interface model, page-by-page strategy |
| 2026-01-14 | Initial Phase 4A doc - project-centric UX flow |
