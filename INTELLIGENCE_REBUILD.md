# XLR8 Intelligence Layer Rebuild

**Date Started:** January 22, 2026  
**Goal:** Replace 25,000 lines of broken SQL generation with ~500 lines of LLM-enabled query handling  
**Principle:** Assemble context for the LLM, let it write SQL, execute, synthesize

---

## THE PROBLEM

The current `backend/utils/intelligence/` folder tried to generate SQL deterministically without LLM help. This required:
- Term indexes to map every possible keyword to columns
- Hub-spoke detection to figure out JOINs
- SQL assemblers to build queries from term matches
- Metadata reasoners as fallback

**Result:** 25,000 lines that only work for trivial queries.

**Worse:** Fallbacks everywhere meant we never knew what was actually working.

## THE SOLUTION

**New approach:**
1. Question comes in
2. Extract what tables/entities are relevant (using existing profiling data)
3. Pull schemas for those tables
4. Pull join paths
5. Send context + question to LLM → get SQL
6. Execute SQL
7. Send results + question to LLM → get synthesis

**CRITICAL RULE: NO FALLBACKS**
- If LLM fails to generate SQL → FAIL with clear error
- If SQL execution fails → FAIL with clear error
- If no tables found → FAIL with clear error
- Every step either succeeds or fails visibly

**Why this works:** The LLM is good at writing SQL when you tell it exactly what tables and columns exist. The hard part was always "which tables?" - and we already have that data in `_column_profiles` and `_schema_metadata`.

**Why no fallback:** Fallbacks hide problems. If something doesn't work, we need to know IMMEDIATELY, not have it silently degrade to garbage.

---

## PHASE 1: NEW MODULE (query_engine.py)

### Files to CREATE:
- [ ] `backend/utils/intelligence/query_engine.py` - The new single-file solution

### What it contains:
1. `ContextAssembler` - Finds relevant tables, pulls schemas
2. `SQLGenerator` - Prompts LLM to write SQL
3. `QueryExecutor` - Runs SQL, handles errors
4. `ResponseSynthesizer` - Turns results into natural language
5. `QueryEngine` - Main orchestrator class

### Dependencies (existing, reused):
- `utils/structured_data_handler.py` - DuckDB connection, profiling data
- `utils/llm_orchestrator.py` - LLM calls
- `utils/rag_handler.py` - For reference doc searches (optional)

---

## PHASE 2: WIRE INTO UNIFIED_CHAT

### Files to MODIFY:
- [ ] `backend/routers/unified_chat.py` - Replace engine.ask() call with new QueryEngine

### Changes:
- Import new QueryEngine
- Replace `IntelligenceEngineV2` instantiation with `QueryEngine`
- Keep all the session handling, clarification, etc. (that stuff works)

---

## PHASE 3: DEPRECATE OLD CODE

### Files to ARCHIVE (move to `backend/utils/intelligence/_archived/`):
- [ ] `engine.py` (3,834 lines) - Old orchestrator
- [ ] `query_resolver.py` (3,232 lines) - Old resolver
- [ ] `term_index.py` (2,538 lines) - Term matching
- [ ] `sql_generator.py` (1,997 lines) - Deprecated LLM SQL
- [ ] `sql_assembler.py` (1,566 lines) - Deterministic SQL builder
- [ ] `table_selector.py` (1,032 lines) - Table scoring
- [ ] `query_resolver_v2.py` (748 lines) - Second attempt
- [ ] `relationship_resolver.py` (657 lines) - Multi-hop
- [ ] `metadata_reasoner.py` (588 lines) - Fallback guesser
- [ ] `value_parser.py` (549 lines) - Numeric/date parsing
- [ ] `intent_parser.py` (478 lines) - Intent detection

### Files to KEEP (still useful):
- [x] `synthesis_pipeline.py` - Response formatting (may reuse parts)
- [x] `consultative_templates.py` - Response templates
- [x] `citation_tracker.py` - Source tracking
- [x] `gatherers/` - Truth gatherers for Reference/Regulatory (ChromaDB)
- [x] `types.py` - Data types
- [x] `chunk_classifier.py` - Doc classification

---

## PHASE 4: CLEANUP

### After new system is working:
- [ ] Delete `_archived/` folder entirely (or keep for reference)
- [ ] Update imports in any files that referenced old modules
- [ ] Run full test suite
- [ ] Update documentation

---

## SUCCESS CRITERIA

1. Ask "how many employees in Texas" → Get correct count
2. Ask "employees with salary over 100k by department" → Get grouped results
3. Ask "list employees hired last year with 401k deductions" → Get JOIN query working
4. All above use LLM-generated SQL, not hardcoded patterns
5. Response includes the SQL that was run (transparency)
6. Errors are clear ("I couldn't find a 'foobar' column")

---

## PROGRESS LOG

### Session 1 - January 22, 2026

**Time:** Started

- [x] Step 1: Create `query_engine.py` skeleton
- [x] Step 2: Implement `ContextAssembler`
- [x] Step 3: Implement `SQLGenerator`
- [x] Step 4: Implement `QueryExecutor`
- [x] Step 5: Implement `ResponseSynthesizer`
- [x] Step 6: Implement `QueryEngine` orchestrator
- [x] Step 7: Wire into `unified_chat.py`
- [ ] Step 8: Test with real query
- [ ] Step 9: Archive old files
- [ ] Step 10: Final cleanup

**Completed:**
- Created `backend/utils/intelligence/query_engine.py` (~650 lines)
- Added QueryEngine to `__init__.py` exports
- Modified `unified_chat.py` to use QueryEngine when `USE_QUERY_ENGINE=true`
- Added compatibility properties to SynthesizedResponse for old interface
- **REMOVED ALL FALLBACKS** - Succeed or fail clearly
- **ALL LOGGING NOW AT WARNING LEVEL** - Visible in Railway logs

**Files Created:**
- `/backend/utils/intelligence/query_engine.py` - The new simplified engine

**Files Modified:**
- `/backend/utils/intelligence/__init__.py` - Added QueryEngine exports
- `/backend/routers/unified_chat.py` - Added QueryEngine creation path

**Environment Variable:**
- `USE_QUERY_ENGINE=true` (default) - Uses new QueryEngine
- `USE_QUERY_ENGINE=false` - Falls back to IntelligenceEngineV2

**Logging Tags (look for these in Railway):**
- `[ENGINE]` - Main orchestrator steps
- `[CONTEXT]` - Table finding, schema assembly
- `[SQL_GEN]` - LLM prompt and response
- `[EXECUTOR]` - SQL execution results

---

## NOTES

- We're keeping the existing upload/profiling pipeline - it works
- We're keeping the existing LLM orchestrator - it works
- We're keeping the existing RAG handler - it works
- We're ONLY replacing the query→SQL→response flow
