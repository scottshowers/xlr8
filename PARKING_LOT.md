# XLR8 Parking Lot

**Last Updated:** January 24, 2026

Known issues and technical debt items to address later.

---

## Resolved

### ~~SQL Assembler/Term Index Not Finding Tables~~
**Resolved:** January 24, 2026
**Solution:** Replaced entire intelligence layer with `query_engine.py`. Old term_index.py, sql_assembler.py, query_resolver.py are deprecated.

---

## Backend Issues

### 1. Registry Cleanup UUID Error
**Severity:** Warning (non-fatal)
**Location:** `backend/routers/cleanup.py` ~line 350-358
**Error:** `invalid input syntax for type uuid: "table"`
**Description:** When cleaning up document_registry, the code passes an invalid value to the `project_id` UUID column. The cleanup still works but logs a warning.
**Fix:** Check if `project_id` is a valid UUID before querying, or handle the case where it's not set.

### 2. COUNT(*) vs COUNT(DISTINCT employeeId)
**Severity:** Medium - inflates counts
**Location:** `backend/utils/intelligence/query_engine.py`
**Description:** LLM-generated SQL uses COUNT(*) instead of COUNT(DISTINCT employeeId), which can inflate counts when tables have duplicate rows per employee.
**Fix:** Add to deterministic SQL patterns or instruction in LLM prompt.

### 3. Terminated Queries Don't Filter by Year
**Severity:** Medium - incorrect results after clarification
**Location:** `backend/utils/intelligence/query_engine.py`
**Description:** When user asks "how many terminated employees" and provides a year clarification, the year filter isn't applied to the final SQL.
**Fix:** Thread the year parameter through intent resolution to SQL generation.

---

## Frontend Issues

### 4. Vacuum/Register Extractor Not Wired
**Severity:** Medium - feature incomplete
**Location:** `/vacuum` route, `VacuumUploadPage.jsx`
**Description:** Register Extractor UI exists but backend processing may not be fully connected.
**Status:** Needs investigation

### 5. Data Page UX
**Severity:** Medium - usability
**Description:** Data page needs UX improvements for better navigation and file/table display.
**Source:** Memory parking lot item

### 6. File/Table Name Display
**Severity:** Low - cosmetic
**Description:** File and table names could be displayed more clearly in the UI.
**Source:** Memory parking lot item

### 7. Chat CSS Fixes
**Severity:** Low - cosmetic
**Estimated:** 1 hour
**Description:** Minor CSS issues in chat interface.
**Source:** P5 sprint task

---

## Architecture / Technical Debt

### 8. Unrecognized Hubs UI
**Severity:** Low - feature gap
**Description:** Need UI to name/manage discovered hubs that aren't yet recognized.
**Source:** Memory parking lot item

### 9. Vocabulary CRUD
**Severity:** Low - admin feature
**Description:** Admin interface to manage vocabulary terms.
**Source:** Memory parking lot item

### 10. Old Intelligence Files Still in Tree
**Severity:** Low - code hygiene
**Location:** `backend/utils/intelligence/`
**Files to archive:**
- `query_resolver.py` (3,232 lines)
- `term_index.py` (2,538 lines)
- `sql_assembler.py` (1,566 lines)
- `engine.py` (3,834 lines)
- `project_intelligence.py` (141K)
**Status:** Code works, just clutters the repo

---

## Infrastructure

### 11. Carbone Integration
**Severity:** Medium - export feature
**Description:** Need Carbone-based export for professional deliverables.
**Location:** Was Phase 4B in old roadmap
**Source:** Memory parking lot item

### 12. Hosting / SOC Compliance
**Severity:** Medium - exit requirement
**Description:** SOC compliance and hosting considerations for enterprise customers.
**Source:** Memory parking lot item

### 13. GitHub Cleanup
**Severity:** Low - code hygiene
**Description:** General repo cleanup, branch management, etc.
**Source:** Memory parking lot item

---

## UX Polish

### 14. AdminHub Stale Routes
**Severity:** Low
**Location:** `frontend/src/pages/AdminHub.jsx`
**Description:** Some cards still point to old routes like `/standards` and `/reference-library` which redirect. Should point directly to `/admin/global-knowledge`.

---

## Version History

| Date | Item Added |
|------|------------|
| 2026-01-24 | Added items 2-3 from PIT query session |
| 2026-01-24 | Added items 5-13 from memory parking lot |
| 2026-01-24 | Marked SQL Assembler/Term Index as RESOLVED |
| 2026-01-16 | Initial parking lot created |
