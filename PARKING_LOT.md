# XLR8 Parking Lot

**Last Updated:** January 16, 2026

Known issues and technical debt items to address later.

---

## Backend Issues

### 1. Registry Cleanup UUID Error
**Severity:** Warning (non-fatal)
**Location:** `backend/routers/cleanup.py` ~line 350-358
**Error:** `invalid input syntax for type uuid: "table"`
**Description:** When cleaning up document_registry, the code passes an invalid value to the `project_id` UUID column. The cleanup still works but logs a warning.
**Fix:** Check if `project_id` is a valid UUID before querying, or handle the case where it's not set.

### 2. SQL Assembler/Term Index Not Finding Tables
**Severity:** High - affects chat quality
**Location:** `backend/services/term_index.py`, `backend/services/sql_assembler.py`
**Description:** The intelligence pipeline sometimes can't find the correct tables for queries. May be related to project code vs name mismatch, or term index not being rebuilt after data changes.
**Investigation needed:**
- Check if term index is using correct project identifier
- Verify table names in term index match actual DuckDB tables
- Check if recalc is triggered after table delete/upload

---

## Frontend Issues

### 3. Vacuum/Register Extractor Not Wired
**Severity:** Medium - feature incomplete
**Location:** `/vacuum` route, `VacuumUploadPage.jsx`
**Description:** Register Extractor UI exists but backend processing may not be fully connected.
**Status:** Needs investigation

---

## UX Polish

### 4. AdminHub Stale Routes
**Severity:** Low
**Location:** `frontend/src/pages/AdminHub.jsx`
**Description:** Some cards still point to old routes like `/standards` and `/reference-library` which redirect. Should point directly to `/admin/global-knowledge`.

---

## Version History

| Date | Item Added |
|------|------------|
| 2026-01-16 | Initial parking lot created with items 1-4 |
