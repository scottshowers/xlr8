# DuckDB Connection Management Fix - January 5, 2026

## The Problem
Upload jobs were crashing with segfaults because:
1. `relationship_detector.py` created new DuckDB connections during upload
2. These collided with the upload handler's connection
3. Multiple threads hitting DuckDB = memory corruption

## The Fix
**Handler Passing** - Upload creates ONE handler and passes it through the entire pipeline.

## Files to Deploy

| File | Destination | What Changed |
|------|-------------|--------------|
| `relationship_detector.py` | `backend/utils/` | All functions accept `handler` param |
| `upload_enrichment.py` | `backend/utils/` | Passes `handler` to relationship detector |
| `project_intelligence.py` | `backend/utils/` | Passes `self.handler` to relationship detector |
| `structured_data_handler.py` | `utils/` | Background inference disabled, thread locks |
| `dashboard.py` | `backend/routers/` | Reverted to singleton handler |
| `unified_chat.py` | `backend/routers/` | Reverted to singleton handler |
| `intelligence.py` | `backend/routers/` | Reverted to singleton handler |
| `features.py` | `backend/routers/` | Reverted to singleton handler |
| `health.py` | `backend/routers/` | Reverted to singleton handler |
| `playbook_framework.py` | `backend/utils/` | Reverted to singleton handler |
| `Architecture_Ways_of_Working.md` | `doc/` | Added Part 13: DuckDB Connection Management |

## Deployment Order
1. Deploy all backend files
2. Clear any stuck jobs
3. Clear project data
4. Test upload with Excel file

## Expected Result
- Upload completes without segfault
- Relationships detected (was 0, should be 300+)
- `[QUEUE] ====== Job completed ======` in logs

## Architecture (Part 13 in Ways of Working)

```
smart_router.py → upload.py:process_file_background
                      │
                      ├── handler = get_structured_handler()  ← ONE handler
                      │
                      ├── run_intelligence_analysis(handler)  ← PASSED
                      │       └── ProjectIntelligenceService(handler)
                      │               └── analyze_project_relationships(handler)
                      │
                      └── enrich_structured_upload(handler)   ← PASSED
                              └── _run_relationship_detection(handler)
                                      └── analyze_project_relationships(handler)
```

## The Rule
Functions in the upload pipeline MUST:
1. Accept `handler` as a parameter
2. Use the passed handler, not call `get_structured_handler()`
3. Pass handler to any functions they call

API endpoints outside the upload path can use `get_structured_handler()` directly.
