# XLR8 Technical Backlog

Items extracted from codebase TODOs during audit cleanup. These are documented limitations, not bugs.

---

## Intelligence Engine Enhancements
**File:** `backend/utils/intelligence/engine.py`

### Conflict Detection (Line 858)
- **Current:** Stub function
- **Need:** Implement detection when multiple truth sources conflict
- **Priority:** P2 (post-exit)

### Proactive Checks (Line 864)
- **Current:** Stub function
- **Need:** Implement proactive data quality checks
- **Priority:** P2 (post-exit)

### Compliance Checking (Line 870)
- **Current:** Stub function
- **Need:** Implement automated compliance validation
- **Priority:** P2 (post-exit)

---

## PDF Processing

### ChromaDB Storage (Line 1226)
**File:** `backend/utils/pdf_vision_analyzer.py`
- **Current:** Placeholder
- **Need:** Implement ChromaDB storage for extracted PDF content
- **Priority:** P3

---

## Security & Audit

### User Context from Auth (Line 478)
**File:** `backend/routers/intelligence.py`
- **Current:** Hardcoded `actor='user'`
- **Need:** Pull actual user from auth context
- **Priority:** P2

### Audit Log Storage (Lines 291, 319)
**File:** `backend/routers/security.py`
- **Current:** Stub functions
- **Need:** Connect to actual audit log storage (Supabase table or external service)
- **Priority:** P2 (needed for SOC2)

---

## API Integrations

### WFM and Ready Testing (Line 305)
**File:** `backend/routers/api_connections.py`
- **Current:** Only UKG Pro tested
- **Need:** Add integration tests for WFM and Ready endpoints
- **Priority:** P3

---

## Database Schema

### Display Name Column (Line 507)
**File:** `utils/database/models.py`
- **Current:** Commented out
- **Need:** Add `display_name` column to Supabase `document_registry` table
- **Priority:** P3 (nice to have)

---

## Summary

| Priority | Count | Description |
|----------|-------|-------------|
| P2 | 5 | Post-exit, pre-SOC2 |
| P3 | 3 | Nice to have |

These items are tracked for post-acquisition roadmap discussions.

---

*Last updated: January 3, 2026*
