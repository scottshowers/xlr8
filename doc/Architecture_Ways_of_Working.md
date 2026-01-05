# XLR8 ARCHITECTURE WAYS OF WORKING

**Version:** 1.4  
**Created:** January 2, 2026  
**Updated:** January 5, 2026 (Part 13 added - DuckDB Connection Management)  
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

### THE RULE: utils/ vs backend/utils/

App starts as `uvicorn backend.main:app` from repo root. Two utils directories exist:

| Location | Purpose | Import Style |
|----------|---------|--------------|
| `utils/` (repo root) | Core data handlers | `from utils.X` |
| `backend/utils/` | Backend services | `from backend.utils.X` |

**Core Data Handlers (`utils/`):**
- `structured_data_handler.py` - DuckDB operations
- `rag_handler.py` - ChromaDB operations  
- `llm_orchestrator.py` - LLM routing
- `query_router.py`, `query_decomposition.py` - Query handling
- `text_extraction.py`, `universal_chunker.py` - Document processing

**Backend Services (`backend/utils/`):**
- `classification_service.py` - Table/column classification
- `registration_service.py` - File registration & lineage
- `metrics_service.py` - Usage metrics
- `pdf_vision_analyzer.py`, `smart_pdf_analyzer.py` - PDF processing
- `consultative_synthesis.py` - Response generation
- `intelligence/*.py` - Intelligence engine components

**NEVER use try/except for imports:**
```python
# ❌ WRONG - Import guessing
try:
    from utils.structured_data_handler import get_structured_handler
except ImportError:
    from backend.utils.structured_data_handler import get_structured_handler

# ✅ CORRECT - Know where it lives
from utils.structured_data_handler import get_structured_handler  # Core handler
from backend.utils.classification_service import ClassificationService  # Backend service
```

### Standard Imports

```python
# Core Data Handlers (from utils/)
from utils.structured_data_handler import get_structured_handler
from utils.rag_handler import RAGHandler
from utils.llm_orchestrator import LLMOrchestrator

# Backend Services (from backend/utils/)
from backend.utils.intelligence.table_selector import TableSelector
from backend.utils.registration_service import RegistrationService, RegistrationSource
from backend.utils.consultative_synthesis import ConsultativeSynthesizer
from backend.utils.classification_service import ClassificationService
from backend.utils.metrics_service import MetricsService

# Database (from utils/database/)
from utils.database.supabase_client import get_supabase
from utils.database.models import DocumentRegistryModel, LineageModel

# Features (from utils/features/)
from utils.features.comparison_engine import ComparisonEngine
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

---

# PART 9: IMPORT STANDARDS

**Added:** January 3, 2026 after finding 27 routers with try/except import blocks.

## 9.1 The Problem

The codebase has two `utils` directories:
- `/utils/` - At repo root
- `/backend/utils/` - Inside backend

App starts as `uvicorn backend.main:app` from repo root, so both are valid import paths. This led to inconsistent imports and try/except guessing blocks throughout the codebase.

## 9.2 The Rule

**Know where each module lives. Use the correct import. No try/except.**

| Location | Contents | Import Style |
|----------|----------|--------------|
| `utils/` | Core data handlers (DuckDB, ChromaDB, LLM) | `from utils.X` |
| `backend/utils/` | Backend services (classification, registration, etc.) | `from backend.utils.X` |
| `utils/database/` | Database clients and models | `from utils.database.X` |
| `utils/features/` | Feature modules (comparison, etc.) | `from utils.features.X` |

## 9.3 Core Handlers (utils/)

These handle direct data storage operations:

```python
from utils.structured_data_handler import get_structured_handler, StructuredDataHandler
from utils.rag_handler import RAGHandler
from utils.llm_orchestrator import LLMOrchestrator
from utils.query_router import QueryRouter
from utils.text_extraction import extract_text
from utils.universal_chunker import UniversalChunker
```

## 9.4 Backend Services (backend/utils/)

These provide higher-level business logic:

```python
from backend.utils.classification_service import ClassificationService, get_classification_service
from backend.utils.registration_service import RegistrationService, RegistrationSource
from backend.utils.metrics_service import MetricsService
from backend.utils.consultative_synthesis import ConsultativeSynthesizer
from backend.utils.pdf_vision_analyzer import PDFVisionAnalyzer
from backend.utils.smart_pdf_analyzer import SmartPDFAnalyzer
from backend.utils.intelligence.table_selector import TableSelector
from backend.utils.intelligence.engine import IntelligenceEngineV2
```

## 9.5 Anti-Pattern: Import Guessing

```python
# ❌ NEVER DO THIS
try:
    from utils.classification_service import ClassificationService
except ImportError:
    from backend.utils.classification_service import ClassificationService

try:
    from backend.utils.structured_data_handler import get_structured_handler
except ImportError:
    from utils.structured_data_handler import get_structured_handler

# ✅ INSTEAD: Know where it lives
from utils.structured_data_handler import get_structured_handler  # It's in utils/
from backend.utils.classification_service import ClassificationService  # It's in backend/utils/
```

## 9.6 When Adding New Modules

**Question:** Is this a core data handler or a business service?

- **Core handler** (direct DuckDB/ChromaDB/LLM operations) → `utils/`
- **Business service** (uses handlers to provide features) → `backend/utils/`

---

# PART 10: API ENDPOINT CONVENTIONS

**Added:** January 3, 2026 after discovering routers had inconsistent prefix patterns.

## 10.1 The Problem

Some routers defined their own prefix (`/api/advisor`), some had no prefix (main.py adds `/api`), some had partial prefixes. You couldn't look at a router and know its actual path.

## 10.2 The Rule

**All endpoint prefixes are defined in main.py. Routers define NO prefix.**

```python
# ❌ WRONG - Router defines its own prefix
router = APIRouter(prefix="/api/advisor", tags=["advisor"])

# ✅ CORRECT - Router has no prefix
router = APIRouter(tags=["advisor"])

# main.py adds the prefix
app.include_router(advisor_router.router, prefix="/api/advisor")
```

## 10.3 Endpoint Types

### Resource Endpoints (REST)
Standard CRUD on data entities. Noun-based, plural.

```
GET    /api/projects           → List all projects
POST   /api/projects           → Create a project
GET    /api/projects/{id}      → Get one project
PUT    /api/projects/{id}      → Update a project
DELETE /api/projects/{id}      → Delete a project
```

### Action Endpoints (RPC-style)
Operations that DO something. Verb in path is OK.

```
POST   /api/upload             → Process an upload
POST   /api/chat/unified       → Send a chat query
POST   /api/playbooks/scan     → Run a scan
```

### Nested Resources
Resources that belong to a parent.

```
GET    /api/projects/{id}/files      → Files in a project
GET    /api/intelligence/{id}/tasks  → Tasks for a project
```

### System/Admin Endpoints
Health, metrics, admin operations.

```
GET    /api/health             → System health
GET    /api/metrics            → System metrics
POST   /api/admin/cleanup      → Run cleanup
DELETE /api/admin/cache        → Clear cache
```

## 10.4 Standard Structure

```
/api
├── /projects                 # Resource: Projects
├── /projects/{id}/files      # Nested: Files in project
│
├── /upload                   # Action: Upload files
├── /chat                     # Action: Chat/query
├── /bi                       # Action: BI queries
│
├── /playbooks                # Resource: Playbook definitions
├── /playbook-builder         # Resource: Playbook configs
│
├── /classification           # Resource: Classifications
├── /data-model               # Resource: Data models
├── /intelligence             # Action: Intelligence analysis
│
├── /reference                # Resource: Reference library
├── /standards                # Resource: Standards/rules
├── /decoder                  # Action: Domain decoding
│
├── /health                   # System: Health check
├── /metrics                  # System: Metrics
├── /status                   # System: Status info
│
├── /admin                    # Admin operations
│   ├── /registry
│   ├── /learning
│   └── /rules
│
├── /auth                     # Auth operations
└── /security                 # Security operations
```

## 10.5 Router Template

```python
# myrouter.py
from fastapi import APIRouter

# NO prefix here - main.py handles it
router = APIRouter(tags=["myrouter"])

@router.get("/")
async def list_items():
    """GET /api/myrouter"""
    pass

@router.get("/{id}")
async def get_item(id: str):
    """GET /api/myrouter/{id}"""
    pass

@router.post("/{id}/process")
async def process_item(id: str):
    """POST /api/myrouter/{id}/process"""
    pass
```

```python
# main.py
from backend.routers import myrouter

app.include_router(myrouter.router, prefix="/api/myrouter")
```

## 10.6 Current Status

As of January 3, 2026, all router prefixes have been removed and consolidated to main.py. The pattern is now consistent across all 27 routers.

**This document is the law. Follow it.**

**When in doubt, grep the codebase and match existing patterns.**

**If you find yourself writing new infrastructure instead of using existing patterns, STOP and ask why.**

---

# PART 11: FRONTEND COMPONENT STANDARDS

**Added:** January 4, 2026 after finding 5 pages with duplicate local Tooltip components that didn't respect global settings.

## 11.1 The Problem

Pages were copy-pasting component implementations locally instead of using shared components. This led to:
- Inconsistent behavior (local tooltips ignored global toggle)
- Duplicated code across 5+ files
- Style drift between implementations
- Features not working (tooltip toggle only worked on nav, not page content)

## 11.2 The Rule

**NEVER define UI components locally in page files. Use shared components from `components/ui/`.**

```jsx
// ❌ WRONG - Local component definition in page file
function Tooltip({ children, title, detail }) {
  const [show, setShow] = useState(false);
  return (
    <div onMouseEnter={() => setShow(true)}>
      {children}
      {show && <div>{title}</div>}
    </div>
  );
}

// ✅ CORRECT - Import shared component
import { Tooltip } from '../components/ui';
```

## 11.3 Shared UI Components

All reusable UI components live in `frontend/src/components/ui/`:

| Component | File | Purpose |
|-----------|------|---------|
| `Tooltip` | `Tooltip.jsx` | Fancy tooltips with title/detail/action, respects global toggle |
| `SimpleTooltip` | `Tooltip.jsx` | Basic single-line tooltips for nav/buttons |
| `Card` | `Card.jsx` | Consistent card styling |
| `Button` | `Button.jsx` | Standard button variants |

### Tooltip Usage

```jsx
import { Tooltip, SimpleTooltip } from '../components/ui';

// Fancy tooltip (3-part: title, detail, action)
<Tooltip 
  title="Pipeline Status" 
  detail="Real-time health checks for each pipeline stage."
  action="Click to refresh"
>
  <div>Hover me</div>
</Tooltip>

// Simple tooltip (single line, for nav/buttons)
<SimpleTooltip text="Sign out of XLR8">
  <button>Logout</button>
</SimpleTooltip>
```

### Tooltip Global Toggle

Tooltips respect `TooltipContext`:
- Toggle button in nav bar controls all tooltips app-wide
- Setting persists to localStorage
- Individual tooltips can be disabled with `disabled` prop

```jsx
// In components/ui/Tooltip.jsx
const { tooltipsEnabled } = useTooltips();
if (!tooltipsEnabled) return children; // No tooltip shown
```

## 11.4 When Creating New Shared Components

1. **Check if it exists first** - grep `frontend/src/components/`
2. **If creating new** - put in `components/ui/` and export from `components/ui/index.js`
3. **Add to this document** - update the table above

## 11.5 Anti-Pattern: Component Duplication

Files that HAD local Tooltip components (now fixed):
- `DashboardPage.jsx` ❌ → ✅ Uses shared
- `DataPage.jsx` ❌ → ✅ Uses shared
- `DataExplorer.jsx` ❌ → ✅ Uses shared
- `DataModelPage.jsx` ❌ → ✅ Uses shared
- `MissionControl.jsx` ❌ → Deleted (orphaned file)

**If you find yourself copy-pasting a component into a page file, STOP.**

---

# PART 12: DEAD CODE REMOVAL

**Added:** January 4, 2026

## 12.1 The Rule

**Delete orphaned files. Don't leave them around "just in case."**

Orphaned files cause:
- Confusion about what's actually used
- Wasted effort updating dead code
- False positives in grep/search
- Technical debt accumulation

## 12.2 How to Identify Orphaned Files

```bash
# Check if a component is imported anywhere
grep -rn "import.*MyComponent" frontend/src/

# Check if a page is routed
grep -n "MyPage" frontend/src/App.jsx

# Check if a backend module is used
grep -rn "from.*mymodule\|import.*mymodule" backend/
```

## 12.3 Known Orphaned Files (Deleted)

| File | Reason | Date Removed |
|------|--------|--------------|
| `MissionControl.jsx` | Replaced by DashboardPage, not routed | Jan 4, 2026 |

**When you find orphaned code, delete it. Don't comment it out. Git has history.**

---

# PART 13: DUCKDB CONNECTION MANAGEMENT

**Added:** January 5, 2026 after segfaults from thread collisions during upload.

## 13.1 The Problem

DuckDB connections are NOT thread-safe for concurrent operations. When upload is writing to DuckDB and other code creates new connections or accesses the same connection from different threads, we get:
- `malloc(): unaligned tcache chunk detected`
- `Segmentation fault`
- `Connection Error: Can't open a connection to same database file with a different configuration`

## 13.2 The Architecture

**Single Singleton Handler** - One DuckDB connection for the entire application:

```python
# utils/structured_data_handler.py
def get_structured_handler() -> StructuredDataHandler:
    """Returns the singleton handler with one DuckDB connection."""
```

**Handler Passing** - Functions in the upload pipeline receive the handler, they don't create new ones:

```python
# ❌ WRONG - Creates new connection, causes collision
def detect_relationships(project: str):
    handler = get_structured_handler()  # Might conflict with upload
    result = handler.conn.execute("SELECT ...")

# ✅ CORRECT - Uses passed handler
def detect_relationships(project: str, handler):
    result = handler.conn.execute("SELECT ...")  # Same connection as upload
```

## 13.3 The Upload Pipeline

The upload flow maintains ONE handler throughout:

```
smart_router.py → upload.py:process_file_background
                      │
                      ├── handler = get_structured_handler()  ← Created ONCE
                      │
                      ├── handler.store_excel()              ← Uses same handler
                      ├── handler.profile_columns_fast()     ← Uses same handler
                      │
                      ├── run_intelligence_analysis(handler) ← Passed down
                      │       └── ProjectIntelligenceService(handler)
                      │               └── analyze_project_relationships(handler)
                      │
                      └── enrich_structured_upload(handler)  ← Passed down
                              └── _run_relationship_detection(handler)
                                      └── analyze_project_relationships(handler)
```

## 13.4 The Rules

### RULE 1: Upload Pipeline Functions MUST Accept Handler

Any function called during upload processing MUST accept a `handler` parameter:

```python
# ✅ CORRECT
def analyze_project_relationships(project: str, tables: List, handler=None) -> Dict:
    if handler is None:
        handler = get_structured_handler()  # Fallback for non-upload calls
    ...

# ✅ CORRECT  
class ProjectIntelligenceService:
    def __init__(self, project: str, handler=None):
        self.handler = handler
```

### RULE 2: Upload Callers MUST Pass Handler

```python
# ✅ CORRECT - In upload.py
handler = get_structured_handler()
intelligence = ProjectIntelligenceService(project, handler)  # Pass it
enrichment = enrich_structured_upload(project, handler=handler)  # Pass it
```

### RULE 3: API Endpoints Use Singleton Directly

Endpoints NOT in the upload path can call `get_structured_handler()` directly:

```python
# ✅ CORRECT - API endpoint, not upload path
@router.get("/tables")
async def get_tables():
    handler = get_structured_handler()
    return handler.conn.execute("SHOW TABLES").fetchall()
```

This is safe because:
- If upload is running, the singleton IS the upload's handler
- The `_db_lock` in StructuredDataHandler serializes operations

### RULE 4: No Background Threads During Upload

Background inference was disabled because it created a separate thread hitting DuckDB while upload was writing:

```python
# In structured_data_handler.py store_excel_file():
# DISABLED: queue_inference_job() - caused thread collision
```

If you need background processing, it must happen AFTER upload completes.

## 13.5 Files Following This Pattern

| File | Role | Handler Source |
|------|------|----------------|
| `upload.py` | Creates handler | `get_structured_handler()` |
| `upload_enrichment.py` | Receives handler | Parameter from upload.py |
| `project_intelligence.py` | Receives handler | Parameter from upload.py |
| `relationship_detector.py` | Receives handler | Parameter from caller |
| All API routers | Use singleton | `get_structured_handler()` |

## 13.6 Debugging Connection Issues

If you see these errors:

**`malloc(): unaligned tcache chunk detected` / `Segmentation fault`**
- Multiple threads hitting DuckDB simultaneously
- Check for background threads or API calls during upload

**`Connection Error: Can't open a connection to same database file with a different configuration`**
- Mixed read_only and read-write connections
- Don't use `duckdb.connect(path, read_only=True)` while write connection exists

**Symptoms of thread collision:**
- Upload hangs at random points
- 0 relationships detected despite data existing
- Logs show queries failing with "NoneType" errors

## 13.7 Testing Upload Isolation

To verify upload isn't being interrupted:

1. Start an upload
2. DON'T navigate to other pages
3. Watch logs for `[QUEUE] ====== Job completed ======`

If it completes, the connection management is working. If it fails when you navigate elsewhere, there's still a thread collision somewhere.

**This is the law for DuckDB operations. Follow it.**
