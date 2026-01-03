# XLR8 ARCHITECTURE AUDIT REPORT

**Audit Date:** January 3, 2026  
**Auditor:** Claude  
**Repo Version:** xlr8-main__37_.zip

---

## EXECUTIVE SUMMARY

| Pattern | Violations | Priority |
|---------|------------|----------|
| 1. LLM Orchestrator Bypass | **11 files** | HIGH |
| 2. TableSelector Not Used | **3 files** | MEDIUM |
| 3. RegistrationService Bypass | **3 files** | MEDIUM |
| 4. ConsultativeSynthesizer | ✅ Used in engine | LOW |
| 5. ComparisonEngine | ✅ Used in playbook/engine | LOW |

**Verdict:** Patterns 4 & 5 are properly adopted. Patterns 1-3 have violations.

---

## PATTERN 1: LLM ORCHESTRATOR BYPASS (HIGH PRIORITY)

**Rule:** ALL LLM calls MUST go through `LLMOrchestrator`. No direct anthropic/groq calls.

### Files with Direct Anthropic Client

| File | Line | Notes |
|------|------|-------|
| `backend/routers/playbooks.py` | 1577 | `from anthropic import Anthropic` |
| `backend/routers/register_extractor.py` | 733 | `anthropic.Anthropic(api_key=...)` |
| `backend/routers/advisor_router.py` | 337, 608 | 2 violations |
| `backend/utils/playbook_framework.py` | 1726 | Direct client |
| `backend/utils/consultative_synthesis.py` | 826 | Fallback - intentional? |
| `backend/utils/llm_table_parser.py` | 311 | Direct client |
| `backend/utils/hybrid_analyzer.py` | 486 | Direct client |
| `backend/utils/pdf_vision_analyzer.py` | 601 | Vision API - may need special handling |
| `backend/utils/standards_processor.py` | 264 | Direct API call |

### Files with Direct Groq API Calls

| File | Line | Notes |
|------|------|-------|
| `backend/routers/register_extractor.py` | 940 | Direct requests.post |
| `backend/utils/consultative_synthesis.py` | 694 | Direct requests.post |
| `backend/utils/llm_table_parser.py` | 212 | Direct requests.post |
| `backend/utils/standards_processor.py` | 201 | Direct requests.post |
| `backend/utils/pdf_utils.py` | 308 | Direct requests.post |

### Analysis

**Total: 11 files with LLM bypass violations**

Some files (like `consultative_synthesis.py`) import LLMOrchestrator but ALSO have direct calls as fallbacks. The fallback pattern may be intentional but should be documented.

**Special case:** `pdf_vision_analyzer.py` uses Claude's vision API which LLMOrchestrator may not support. This could be a legitimate exception but should be added to orchestrator.

---

## PATTERN 2: TABLE SELECTOR NOT USED (MEDIUM PRIORITY)

**Rule:** NEVER match tables using string operations for user-facing queries. Use `TableSelector`.

### Files with String-Based Table Matching

| File | Lines | Issue |
|------|-------|-------|
| `backend/routers/cleanup.py` | 275-286, 544 | `startswith()`, `.lower() in` for table matching |
| `backend/routers/bi_router.py` | 311-312, 451, 548 | `.lower() in .lower()`, `startswith()` for value/table matching |
| `backend/routers/data_model.py` | 619, 1023 | `startswith()`, `.lower() in .lower()` |

### Current TableSelector Adoption

**7 files properly use TableSelector:**
- `backend/utils/playbook_framework.py` (2 locations)
- `backend/utils/intelligence/sql_generator.py`
- `backend/utils/intelligence/__init__.py`
- `backend/utils/intelligence/engine.py`

### Analysis

The core intelligence engine and SQL generator use TableSelector correctly. The violations are in:
- Cleanup routes (lower priority - admin function)
- BI router (medium priority - user-facing)
- Data model routes (medium priority - user-facing)

---

## PATTERN 3: REGISTRATION SERVICE BYPASS (MEDIUM PRIORITY)

**Rule:** ALL file uploads MUST go through `RegistrationService`.

### Files with Direct DocumentRegistryModel Calls

| File | Line | Notes |
|------|------|-------|
| `backend/routers/register_extractor.py` | 586 | Direct `.register()` |
| `backend/routers/upload.py` | 1074, 1413, 1745 | Legacy fallbacks |

### Analysis

`upload.py` has direct calls as **legacy fallbacks** when RegistrationService isn't available. This is actually correct defensive coding.

`register_extractor.py` at line 586 should probably use RegistrationService.

---

## PATTERN 4: CONSULTATIVE SYNTHESIZER ✅

**Status: PROPERLY ADOPTED**

ConsultativeSynthesizer is imported and used in:
- `backend/utils/playbook_framework.py` (2 locations)
- `backend/utils/intelligence/engine.py`

The intelligence engine V2 uses ConsultativeSynthesizer for response generation.

---

## PATTERN 5: COMPARISON ENGINE ✅

**Status: PROPERLY ADOPTED**

ComparisonEngine is imported and used in:
- `backend/routers/features.py` (2 locations)
- `backend/utils/playbook_framework.py` (multiple)
- `backend/utils/intelligence/engine.py`

The playbook framework and intelligence engine both use ComparisonEngine for table comparisons.

---

## PRIORITIZED FIX LIST

### BATCH 1: HIGH PRIORITY - LLM Orchestrator (Est: 8h)

| # | File | Fix |
|---|------|-----|
| 1 | `advisor_router.py` | Replace 2 direct Claude calls with orchestrator |
| 2 | `playbooks.py:1577` | Replace direct Anthropic import with orchestrator |
| 3 | `playbook_framework.py:1726` | Replace direct client with orchestrator |
| 4 | `llm_table_parser.py` | Replace both Groq and Claude calls with orchestrator |
| 5 | `hybrid_analyzer.py:486` | Replace direct Claude with orchestrator |
| 6 | `standards_processor.py` | Replace Groq and Claude calls with orchestrator |
| 7 | `pdf_utils.py:308` | Replace Groq call with orchestrator |
| 8 | `register_extractor.py:733,940` | Replace direct calls with orchestrator |

**Defer:** `pdf_vision_analyzer.py` - May need orchestrator update to support Vision API

**Review:** `consultative_synthesis.py` - Has orchestrator but also fallback. Verify intentional.

### BATCH 2: MEDIUM PRIORITY - Table Matching (Est: 4h)

| # | File | Fix |
|---|------|-----|
| 1 | `bi_router.py` | Replace string matching with TableSelector |
| 2 | `data_model.py` | Replace string matching with TableSelector |
| 3 | `cleanup.py` | Replace string matching with TableSelector (lower priority) |

### BATCH 3: LOW PRIORITY - Registration (Est: 1h)

| # | File | Fix |
|---|------|-----|
| 1 | `register_extractor.py:586` | Replace direct registry call with RegistrationService |

---

## RECOMMENDATION

**Fix order:**
1. Batch 1 first - LLM consistency is critical for cost control and reliability
2. Batch 2 second - Table matching affects query accuracy
3. Batch 3 last - Registration fallbacks are actually working

**Total estimated time:** 13 hours

---

## FILES THAT ARE CLEAN ✅

These files properly follow all patterns:
- `backend/utils/intelligence/engine.py` - Uses all patterns correctly
- `backend/utils/intelligence/sql_generator.py` - Uses TableSelector and orchestrator
- `backend/routers/unified_chat.py` - Uses LLMOrchestrator
- `backend/routers/features.py` - Uses ComparisonEngine

---

## APPENDIX: GREP COMMANDS USED

```bash
# LLM Bypass
grep -rn "anthropic.Anthropic\|api.groq.com" backend --include="*.py"

# Table matching violations
grep -rn "\.lower().*in.*\.lower()\|startswith.*table" backend --include="*.py"

# Registration bypass
grep -rn "DocumentRegistryModel.register" backend --include="*.py"

# Pattern adoption
grep -rn "TableSelector\|LLMOrchestrator\|ConsultativeSynthesizer\|ComparisonEngine" backend --include="*.py"
```
