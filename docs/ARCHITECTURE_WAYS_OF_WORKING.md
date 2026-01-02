# XLR8 ARCHITECTURE WAYS OF WORKING

**Version:** 1.0  
**Created:** January 2, 2026  
**Purpose:** Enforce consistent development patterns across all features

---

# EXECUTIVE SUMMARY

This document exists because **we keep leaving things behind**.

Every sprint, we build new capabilities but fail to apply them consistently. We built TableSelector but didn't use it everywhere. We built LLMOrchestrator but 12+ files bypass it. We built health checks that tell us if files exist but not if PDF parsing actually works.

**This document defines the rules.** Not suggestions. Rules.

---

# PART 1: THE NON-NEGOTIABLE PATTERNS

These patterns exist. They work. Use them everywhere.

## 1.1 TableSelector - Intelligent Table Matching

**What it is:** Domain-aware table selection using scoring (domain match, name match, value match, penalties).

**Where it lives:** `backend/utils/intelligence/table_selector.py`

**Current adoption:** 7 files use it. Others still do string matching.

### THE RULE

**NEVER match tables using string operations (startswith, endswith, in, find) for user-facing queries.**

```python
# ❌ WRONG - Dumb string matching
for table in tables:
    if "tax" in table_name.lower():
        selected_tables.append(table)

# ❌ WRONG - Filename substring matching
if report_name.lower() in file_name.lower():
    matched = True

# ✅ CORRECT - Use TableSelector
from backend.utils.intelligence.table_selector import TableSelector

selector = TableSelector(
    structured_handler=handler,
    project=project_name
)
selected = selector.select(tables, question, max_tables=5)
```

### WHEN STRING MATCHING IS ACCEPTABLE

- System table identification (`table.startswith('_')`) - internal, not user-facing
- Project scoping (`table.startswith(project_prefix)`) - security boundary
- Health check diagnostics - internal tooling only

### FILES THAT NEED FIXING

The following files contain table/file matching that should use TableSelector:

| File | Issue | Priority |
|------|-------|----------|
| `backend/routers/health.py:556` | Filename to table matching with `.lower().replace()` | Low (diagnostic) |
| `backend/routers/health.py:581` | Table name fuzzy matching | Low (diagnostic) |
| `backend/routers/cleanup.py:291` | matched_tables iteration | Medium |
| `backend/routers/bi_router.py:451` | Value matching with `.lower() in .lower()` | Medium |
| `backend/utils/playbook_framework.py` | `get_matched_tables()` filename substring | Medium |

---

## 1.2 LLMOrchestrator - Centralized LLM Routing

**What it is:** Single entry point for all LLM calls. Handles local models first, Claude fallback, metrics tracking, PII sanitization.

**Where it lives:** `utils/llm_orchestrator.py`

**Current adoption:** 15 files use it. 12+ files bypass it with direct Claude/Groq calls.

### THE RULE

**ALL LLM calls MUST go through LLMOrchestrator. No exceptions.**

```python
# ❌ WRONG - Direct Anthropic client
import anthropic
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    messages=[{"role": "user", "content": prompt}]
)

# ❌ WRONG - Direct Groq call
import requests
response = requests.post("https://api.groq.com/...", json=payload)

# ✅ CORRECT - Use LLMOrchestrator
from utils.llm_orchestrator import LLMOrchestrator

orchestrator = LLMOrchestrator()
result = orchestrator.synthesize(query, context)  # Tries local first, Claude fallback
```

### AVAILABLE ORCHESTRATOR METHODS

| Method | Purpose | Local First? |
|--------|---------|--------------|
| `synthesize(query, context)` | General synthesis | Yes (Mistral → Claude) |
| `generate_sql(prompt, schema_columns)` | SQL generation | Yes (Qwen only, no Claude) |
| `generate_json(prompt)` | Structured output | Yes (phi3 → Qwen → Claude) |
| `check_status()` | Health check | N/A |

### FILES WITH DIRECT LLM CALLS - STATUS

| File | Status | Notes |
|------|--------|-------|
| `backend/utils/pdf_vision_analyzer.py` | ⚠️ Exception | Uses Vision API (images) - orchestrator doesn't support multimodal |
| `backend/utils/intelligence/intent_parser.py` | ✅ FIXED | Uses orchestrator._call_claude() |
| `backend/utils/intelligence/truth_enricher.py` | ✅ FIXED | Uses orchestrator._call_claude() |
| `backend/utils/hybrid_analyzer.py` | ✅ FIXED | Uses orchestrator._call_claude() |
| `backend/utils/llm_table_parser.py` | ✅ FIXED | Uses orchestrator._call_claude() |
| `backend/utils/consultative_synthesis.py` | ✅ FIXED | Uses orchestrator._call_claude() |
| `backend/utils/playbook_framework.py` | ✅ FIXED | Uses orchestrator._call_claude() |
| `backend/routers/advisor_router.py` | ✅ FIXED | Uses orchestrator._call_claude() |
| `backend/routers/playbooks.py` | ✅ FIXED | Uses orchestrator._call_claude() |
| `backend/routers/register_extractor.py` | ⚠️ Exception | Uses Streaming API for progress updates |

### DOCUMENTED EXCEPTIONS

**Vision API (pdf_vision_analyzer.py):** 
Uses Claude's vision capabilities for PDF image extraction. Direct access required because orchestrator doesn't support multimodal (image) inputs.

**Streaming API (register_extractor.py):**
Uses Claude's streaming API for large PDF extraction with real-time progress updates. Direct access required because orchestrator doesn't support streaming responses.

---

## 1.3 RegistrationService - File Provenance

**What it is:** Single service for registering all uploaded files. Creates registry entries, lineage tracking, file hashing.

**Where it lives:** `backend/utils/registration_service.py`

**Current adoption:** Used in upload.py, smart_router.py, register_extractor.py. Good.

### THE RULE

**ALL file uploads MUST go through RegistrationService.**

```python
# ❌ WRONG - Direct registry insert
DocumentRegistryModel.register(filename=filename, ...)

# ✅ CORRECT - Use RegistrationService
from backend.utils.registration_service import RegistrationService, RegistrationSource

result = RegistrationService.register_structured(
    filename=filename,
    project_id=project_id,
    tables_created=tables,
    row_count=total_rows,
    file_content=content_bytes,
    uploaded_by_email=user_email,
    source=RegistrationSource.UPLOAD
)
```

### REGISTRATION METHODS

| Method | Use Case |
|--------|----------|
| `register_structured()` | Excel/CSV → DuckDB |
| `register_embedded()` | PDF/DOCX → ChromaDB |
| `register_hybrid()` | PDF with tables → Both |
| `register_standards()` | Regulatory/Reference docs |
| `register_failed()` | Failed upload tracking |
| `unregister()` | File deletion |

**Current status:** This pattern is well-adopted. Maintain it.

---

## 1.4 ConsultativeSynthesizer - Response Generation

**What it is:** Transforms raw data into consultant-grade answers. Handles triangulation across Five Truths, conflict detection, "so-what" insights.

**Where it lives:** `backend/utils/consultative_synthesis.py`

### THE RULE

**ALL user-facing responses that synthesize data MUST use ConsultativeSynthesizer.**

```python
# ❌ WRONG - Raw data dump
return {"answer": f"Found {len(rows)} rows: {rows}"}

# ❌ WRONG - Direct LLM call for synthesis
response = orchestrator.synthesize(f"Summarize: {data}")
return {"answer": response}

# ✅ CORRECT - Use ConsultativeSynthesizer
from backend.utils.consultative_synthesis import ConsultativeSynthesizer

synthesizer = ConsultativeSynthesizer()
answer = synthesizer.synthesize(
    question=question,
    reality=reality_truths,
    configuration=config_truths,
    reference=reference_truths,
    regulatory=regulatory_truths,
    structured_data=duckdb_results
)
return {"answer": answer.answer, "confidence": answer.confidence}
```

---

## 1.5 ComparisonEngine - Data Comparison

**What it is:** SQL-based comparison of two DuckDB tables. Auto-detects join keys, finds gaps and mismatches.

**Where it lives:** `utils/features/comparison_engine.py`

### THE RULE

**ALL data comparison operations MUST use ComparisonEngine.**

```python
# ❌ WRONG - Manual comparison logic
for row_a in table_a:
    if row_a['id'] not in table_b_ids:
        missing.append(row_a)

# ✅ CORRECT - Use ComparisonEngine
from utils.features.comparison_engine import ComparisonEngine

engine = ComparisonEngine(structured_handler)
result = engine.compare(
    table_a="tea1000_tax_verification",
    table_b="tea1000_company_master",
    join_keys=["tax_code"],  # Optional - auto-detected if not provided
    project_id=project_id
)
# result.only_in_a, result.only_in_b, result.mismatches, result.matches
```

---

# PART 2: THE FIVE TRUTHS ARCHITECTURE

Every question should be answered by triangulating across multiple data sources.

## 2.1 The Five Truths

| # | Truth | Scope | Storage | What It Contains |
|---|-------|-------|---------|------------------|
| 1 | **Reality** | Customer | DuckDB | Employee data, payroll registers, transactions |
| 2 | **Intent** | Customer | ChromaDB | SOWs, requirements, meeting notes |
| 3 | **Configuration** | Customer | DuckDB | Code tables, mappings, system setup |
| 4 | **Reference** | Global | ChromaDB | Product docs, how-to guides |
| 5 | **Regulatory** | Global | ChromaDB | Laws, IRS rules, state mandates |

Plus **Compliance** as sub-type for audit requirements.

## 2.2 Truth Routing

```python
TRUTH_ROUTING = {
    'reality': 'duckdb',
    'intent': 'chromadb',
    'configuration': 'duckdb',  # Or 'both' for hybrid
    'reference': 'chromadb',
    'regulatory': 'chromadb',
    'compliance': 'chromadb',
}
```

## 2.3 The Magic: Triangulation

**Good Answer:**
> "Your SUI rate is 2.7%. This matches the 2024 state requirement [Regulatory]. UKG recommends configuring this as tax code OHSUI [Reference]. Your system shows OHSUI configured at 2.7% [Configuration], and 47 employees have this applied [Reality]."

**Bad Answer:**
> "Found 47 rows in tax table."

---

# PART 3: SOURCE OF TRUTH RULES

## 3.1 Data Ownership

| Data Type | Source of Truth | Location |
|-----------|-----------------|----------|
| File metadata (who uploaded, when, truth_type) | `document_registry` | Supabase |
| Table structure (columns, row_count) | `_schema_metadata` | DuckDB |
| Column statistics (top values, distinct count) | `_column_profiles` | DuckDB |
| Table data | Project tables | DuckDB |
| Document chunks | Collections | ChromaDB |
| User/Project info | `projects`, `users` | Supabase |

## 3.2 The Cardinal Rule

**Every piece of data has ONE authoritative source. Never duplicate.**

```python
# ❌ WRONG - Duplicating registry data in DuckDB
_schema_metadata.uploaded_by = ...  # This belongs in registry!
_schema_metadata.domain = ...       # This belongs in registry!

# ✅ CORRECT - Pull from both sources
registry_data = DocumentRegistryModel.find_by_filename(filename, project_id)
schema_data = handler.get_table_metadata(table_name)

# Combine in API response
response = {
    "uploaded_by": registry_data.get("uploaded_by_email"),  # From registry
    "row_count": schema_data.get("row_count"),              # From DuckDB
}
```

---

# PART 4: OPERATIONAL HEALTH REQUIREMENTS

This is the gap that let PDF parsing break silently.

## 4.1 What "Health" Actually Means

Current health checks tell us:
- ✅ DuckDB file exists
- ✅ ChromaDB is reachable
- ✅ Registry has N files
- ❌ PDF parsing actually works
- ❌ LLM cascade is functioning
- ❌ Queries return valid results
- ❌ Upload produces usable data

**We need functional health, not existence health.**

## 4.2 Required Health Metrics

| Metric | What It Measures | How to Check |
|--------|------------------|--------------|
| **LLM Cascade Health** | Can we reach Groq? Ollama? Claude? | Ping each with test prompt, measure latency |
| **PDF Parse Success Rate** | % of PDFs that produce valid tables | Track in processing_jobs, compare input/output row counts |
| **Query Success Rate** | % of chat queries that return results | Track in metrics_service |
| **Synthesis Quality** | % of responses that aren't template fallback | Track synthesis_method in responses |
| **Upload Quality** | % of uploads that pass validation | Track health_score in registration |
| **Orphan Detection** | Tables/chunks without registry entries | Run sync check every hour |

## 4.3 Dashboard Requirements

The System Monitor page MUST show:

1. **LLM Status Panel**
   - Groq: ✅ Online / ❌ Down / ⚠️ Slow
   - Ollama: ✅ Online / ❌ Down / ⚠️ Slow  
   - Claude: ✅ Online / ❌ Down / ⚠️ Rate Limited
   - Last 10 calls: Success rate, avg latency

2. **Processing Health Panel**
   - Last 10 uploads: File, status, row count, quality score
   - Any "failed" or "partial" uploads highlighted

3. **Query Health Panel**
   - Last 10 queries: Question preview, response length, synthesis method
   - Any "template fallback" highlighted as degraded

4. **Data Integrity Panel**
   - Orphan tables: Count (should be 0)
   - Orphan chunks: Count (should be 0)
   - Registry/DuckDB sync: ✅ Healthy / ❌ Mismatch

---

# PART 5: CODE QUALITY STANDARDS

## 5.1 Error Handling Pattern

**Every external call MUST have error handling.**

```python
# ❌ WRONG - Unhandled exceptions
result = orchestrator.synthesize(query, context)
return {"answer": result["response"]}

# ✅ CORRECT - Full error handling
try:
    result = orchestrator.synthesize(query, context)
    if result.get("success"):
        return {"answer": result["response"], "model": result.get("model_used")}
    else:
        logger.warning(f"Synthesis failed: {result.get('error')}")
        return {"answer": "I couldn't generate a response. Please try again.", "degraded": True}
except Exception as e:
    logger.error(f"Synthesis exception: {e}")
    return {"answer": "An error occurred. Please try again.", "error": True}
```

## 5.2 Logging Standards

**Use WARNING level for operational visibility.**

```python
# ❌ WRONG - Debug level nobody sees
logger.debug(f"Processing file {filename}")

# ❌ WRONG - Info level buried in noise
logger.info(f"TableSelector found 3 tables")

# ✅ CORRECT - Warning level for operational visibility
logger.warning(f"[TABLE-SEL] Selected 3 tables for query: {question[:50]}")
logger.warning(f"[UPLOAD] Processing {filename} ({file_size} bytes)")
logger.warning(f"[LLM] Groq succeeded ({len(response)} chars, {duration_ms}ms)")
```

**Prefix convention:**
- `[TABLE-SEL]` - TableSelector operations
- `[ENGINE-V2]` - Intelligence engine
- `[UPLOAD]` - File processing
- `[LLM]` - LLM calls
- `[SYNTHESIS]` - Response synthesis
- `[COMPARE]` - Comparison operations
- `[SCAN]` - Playbook scanning

## 5.3 Full File Replacements

**Scott is not a developer. Never give patches.**

```python
# ❌ WRONG - Patch instructions
# Add this at line 45:
#   new_code_here()
# Change line 72 from X to Y

# ✅ CORRECT - Full file replacement
# Here's the complete updated file:
# (entire file contents)
```

---

# PART 6: FEATURE DEVELOPMENT CHECKLIST

Before building ANY new feature:

## 6.1 Pre-Development

- [ ] Read this document
- [ ] `grep` the codebase for similar functionality
- [ ] Identify which existing patterns apply
- [ ] Check if TableSelector, LLMOrchestrator, ComparisonEngine can be reused
- [ ] Identify source of truth for any data involved

## 6.2 During Development

- [ ] Use TableSelector for any table/file matching
- [ ] Use LLMOrchestrator for any LLM calls
- [ ] Use RegistrationService for any file operations
- [ ] Use ConsultativeSynthesizer for user-facing responses
- [ ] Use ComparisonEngine for any data comparison
- [ ] Add WARNING-level logging with prefixes
- [ ] Add error handling for all external calls

## 6.3 Post-Development

- [ ] Verify feature works end-to-end
- [ ] Check logs for errors
- [ ] Verify no orphan data created
- [ ] Run health check
- [ ] Update ARCHITECTURE.md if new patterns introduced

---

# PART 7: KNOWN TECHNICAL DEBT

Items that violate these patterns but haven't been fixed yet:

## 7.1 LLM Bypass Violations - ✅ RESOLVED (Jan 2, 2026)

All critical LLM bypass violations have been fixed. Files now use orchestrator._call_claude():

| File | Status |
|------|--------|
| `intent_parser.py` | ✅ Fixed |
| `truth_enricher.py` | ✅ Fixed |
| `hybrid_analyzer.py` | ✅ Fixed |
| `llm_table_parser.py` | ✅ Fixed |
| `advisor_router.py` | ✅ Fixed |
| `playbook_framework.py` | ✅ Fixed |
| `playbooks.py` | ✅ Fixed |
| `consultative_synthesis.py` | ✅ Fixed |
| `pdf_vision_analyzer.py` | ⚠️ Exception - Vision API |
| `register_extractor.py` | ⚠️ Exception - Streaming API |

## 7.2 Table Matching - Not Violations

After review, these are **not** TableSelector violations. TableSelector is for query-time intelligent table selection. These files use simple string matching appropriately for:

| File | Use Case | Verdict |
|------|----------|---------|
| `health.py` | Diagnostic file matching | ✅ Appropriate |
| `cleanup.py` | File deletion matching | ✅ Appropriate |
| `bi_router.py` | Value filtering (contains) | ✅ Appropriate |

## 7.3 Operational Health - ✅ RESOLVED (Jan 2, 2026)

Added `/api/health/operational` endpoint that tracks:

| Metric | Status |
|--------|--------|
| LLM cascade health (per-provider stats) | ✅ Implemented |
| Upload success rate (24h/7d) | ✅ Implemented |
| Query success rate | ✅ Implemented |
| PDF parse quality | ✅ Implemented |
| Synthesis quality (LLM vs template) | ✅ Implemented |
| Overall health score (0-100) | ✅ Implemented |

---

# PART 8: EMERGENCY PROCEDURES

## 8.1 If PDF Parsing Breaks

1. Check Railway logs for `[PDF]` or `pdf_vision_analyzer` errors
2. Verify Groq API key is valid: `curl -H "Authorization: Bearer $GROQ_API_KEY" https://api.groq.com/openai/v1/models`
3. Check if Ollama is responding: hit `/api/health` and look for `ollama_status`
4. If all LLMs down, uploads will still work but produce raw text extraction

## 8.2 If LLM Cascade Fails

1. Check each provider in order:
   - Groq: Rate limits? API key expired?
   - Ollama: Is the server running? Auth working?
   - Claude: Rate limits? API key valid?
2. Temporary workaround: Chat will fall back to template responses
3. Fix: Restore LLM connectivity, no code change needed

## 8.3 If Data Gets Orphaned

1. Run `/api/status/registry/health` - shows orphan counts
2. For orphan DuckDB tables: `/api/cleanup/orphans` will remove them
3. For orphan ChromaDB chunks: Manual cleanup or re-upload files
4. Prevention: Always use RegistrationService for all file operations

---

# APPENDIX A: QUICK REFERENCE

## A.1 Import Patterns

```python
# Table Selection
from backend.utils.intelligence.table_selector import TableSelector

# LLM Calls
from utils.llm_orchestrator import LLMOrchestrator

# File Registration
from backend.utils.registration_service import RegistrationService, RegistrationSource

# Response Synthesis
from backend.utils.consultative_synthesis import ConsultativeSynthesizer

# Data Comparison
from utils.features.comparison_engine import ComparisonEngine

# Intelligence Engine
from backend.utils.intelligence.engine import IntelligenceEngineV2
```

## A.2 Common Operations

**Select tables for a query:**
```python
selector = TableSelector(structured_handler=handler, project=project)
tables = selector.select(all_tables, question, max_tables=5)
```

**Generate SQL:**
```python
orchestrator = LLMOrchestrator()
result = orchestrator.generate_sql(prompt, schema_columns)
sql = result.get("sql")
```

**Synthesize response:**
```python
synthesizer = ConsultativeSynthesizer()
answer = synthesizer.synthesize(question=q, reality=r, configuration=c, ...)
```

**Compare tables:**
```python
engine = ComparisonEngine(structured_handler)
result = engine.compare("table_a", "table_b", project_id=pid)
```

**Register upload:**
```python
result = RegistrationService.register_structured(
    filename=f, project_id=pid, tables_created=tables,
    row_count=rows, uploaded_by_email=email, source=RegistrationSource.UPLOAD
)
```

---

**This document is the law. Follow it.**

**When in doubt, grep the codebase and match existing patterns.**

**If you find yourself writing new infrastructure instead of using existing patterns, STOP and ask why.**
