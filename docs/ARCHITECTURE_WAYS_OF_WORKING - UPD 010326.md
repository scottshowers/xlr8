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

### FILES WITH DIRECT LLM CALLS (VIOLATIONS)

| File | Line | Violation | Fix Priority |
|------|------|-----------|--------------|
| `backend/utils/pdf_vision_analyzer.py` | 601 | Direct `anthropic.Anthropic()` | Medium - Vision API may need special handling |
| `backend/utils/intelligence/intent_parser.py` | 299 | Direct Claude call | High |
| `backend/utils/intelligence/truth_enricher.py` | 326 | Direct Claude call | High |
| `backend/utils/hybrid_analyzer.py` | 395 | Direct Claude call | High |
| `backend/utils/llm_table_parser.py` | 281 | Direct Claude call | High |
| `backend/utils/consultative_synthesis.py` | 796 | Direct Claude call (fallback) | Medium - is intentional fallback |
| `backend/utils/playbook_framework.py` | 1642 | Direct Claude call | High |
| `backend/routers/advisor_router.py` | 308, 563 | Direct Claude call | High |
| `backend/routers/playbooks.py` | 1550 | Direct Claude call | High |
| `backend/routers/register_extractor.py` | 724 | Direct Claude client | Medium |

### SPECIAL CASES

**Vision API:** `pdf_vision_analyzer.py` uses Claude's vision capabilities for PDF extraction. This may legitimately need direct access. If so, document it and add to orchestrator.

**Intentional Fallback:** `consultative_synthesis.py` has Claude as last resort. This is correct but should use orchestrator's fallback mechanism.

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

## 7.1 LLM Bypass Violations

| File | Priority | Notes |
|------|----------|-------|
| `intent_parser.py` | High | Should use orchestrator |
| `truth_enricher.py` | High | Should use orchestrator |
| `hybrid_analyzer.py` | High | Should use orchestrator |
| `llm_table_parser.py` | High | Should use orchestrator |
| `advisor_router.py` | High | 2 violations |
| `playbook_framework.py` | High | Should use orchestrator |
| `playbooks.py` | High | Should use orchestrator |
| `pdf_vision_analyzer.py` | Medium | May need vision-specific handling |

## 7.2 Table Matching Violations

| File | Priority | Notes |
|------|----------|-------|
| `health.py` | Low | Diagnostic only |
| `cleanup.py` | Medium | User-facing cleanup |
| `bi_router.py` | Medium | BI queries |

## 7.3 Missing Operational Health

| Gap | Priority | Effort |
|-----|----------|--------|
| LLM health monitoring | High | 4h |
| PDF parse success tracking | High | 2h |
| Query success rate dashboard | High | 4h |
| Upload quality visibility | Medium | 2h |

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



ART 9: API ENDPOINT CONVENTIONS
XLR8's API structure was inconsistent - some routers defined prefixes, some didn't, main.py added prefixes inconsistently. This section defines the rules.
9.1 The Golden Rule
ALL route prefixes are defined in main.py. Routers define NONE.
python# ❌ WRONG - Router defines its own prefix
# In advisor_router.py
router = APIRouter(prefix="/api/advisor", tags=["advisor"])

@router.post("/chat")  # Actual path unclear without checking main.py

# ✅ CORRECT - Router has no prefix
# In advisor_router.py
router = APIRouter(tags=["advisor"])

@router.post("/chat")  # Path is /{whatever main.py says}/chat

# In main.py - ALL prefixes defined here
app.include_router(advisor_router.router, prefix="/api/advisor")
Why this matters:

One place to see all routes: main.py
No double-prefix bugs (/api/api/...)
Easy to refactor endpoint structure
Self-documenting API surface


9.2 Endpoint Types
Type 1: Resource Endpoints (REST)
Standard CRUD on data entities. Use plural nouns.
MethodPathPurposeGET/api/projectsList all projectsPOST/api/projectsCreate a projectGET/api/projects/{id}Get one projectPUT/api/projects/{id}Update a projectDELETE/api/projects/{id}Delete a project
Router pattern:
python# projects.py
router = APIRouter(tags=["projects"])

@router.get("/")
async def list_projects(): ...

@router.post("/")
async def create_project(): ...

@router.get("/{project_id}")
async def get_project(project_id: str): ...

# main.py
app.include_router(projects.router, prefix="/api/projects")
Type 2: Action Endpoints (RPC-style)
Operations that DO something. Verbs are OK here.
MethodPathPurposePOST/api/upload/processProcess an uploadPOST/api/chat/querySend a chat queryPOST/api/playbooks/{id}/executeRun a playbookPOST/api/register/extractExtract from PDF
Router pattern:
python# upload.py
router = APIRouter(tags=["upload"])

@router.post("/process")
async def process_upload(): ...

@router.post("/validate")
async def validate_file(): ...

# main.py
app.include_router(upload.router, prefix="/api/upload")
Type 3: Nested Resources
Resources that belong to a parent. Parent ID in path.
MethodPathPurposeGET/api/projects/{id}/filesFiles in a projectGET/api/projects/{id}/tablesTables in a projectPOST/api/projects/{id}/uploadUpload to a projectGET/api/playbooks/{id}/progressPlaybook run progress
Router pattern:
python# projects.py - nested routes in same router
router = APIRouter(tags=["projects"])

@router.get("/{project_id}/files")
async def list_project_files(project_id: str): ...

@router.get("/{project_id}/tables")
async def list_project_tables(project_id: str): ...

@router.post("/{project_id}/upload")
async def upload_to_project(project_id: str): ...
Type 4: System Endpoints
Health, metrics, diagnostics. Grouped under /api/system or specific names.
MethodPathPurposeGET/api/healthSystem healthGET/api/health/operationalOperational metricsGET/api/metricsSystem metricsGET/api/metrics/llmLLM-specific metrics
Router pattern:
python# health.py
router = APIRouter(tags=["health"])

@router.get("/")
async def health_check(): ...

@router.get("/operational")
async def operational_health(): ...

# main.py
app.include_router(health.router, prefix="/api/health")
Type 5: Admin Endpoints
Administrative operations. Grouped under /api/admin.
MethodPathPurposeDELETE/api/admin/cacheClear cachePOST/api/admin/cleanupRun cleanupDELETE/api/admin/project/{id}Force delete projectGET/api/admin/learning/statsLearning system stats
Router pattern:
python# admin.py
router = APIRouter(tags=["admin"])

@router.delete("/cache")
async def clear_cache(): ...

@router.post("/cleanup")
async def run_cleanup(): ...

# main.py
app.include_router(admin.router, prefix="/api/admin")

9.3 Naming Conventions
Path Segments
ConventionExampleNotesPlural nouns for resources/projects, /files, /tablesNot /projectLowercase, hyphenated/api/bi-builder, /api/data-modelNot biBuilder or data_modelIDs use descriptive names/{project_id}, /{playbook_id}Not just /{id}Verbs for actions only/execute, /process, /extractOnly when it's an action
Query Parameters
ConventionExampleNotesFiltering?status=active&type=pdfFilter resourcesPagination?page=2&limit=50Standard paginationSorting?sort=created_at&order=descSort controlSearch?q=search+termFull-text search
Response Codes
CodeMeaningWhen to Use200OKSuccessful GET, PUT201CreatedSuccessful POST that creates204No ContentSuccessful DELETE400Bad RequestInvalid input401UnauthorizedNo/invalid auth token403ForbiddenValid auth, no permission404Not FoundResource doesn't exist500Server ErrorUnexpected failure

9.4 XLR8 API Structure
Proposed Clean Structure
/api
│
├── /projects                     # Project management
│   ├── GET /                     # List projects
│   ├── POST /                    # Create project
│   ├── GET /{id}                 # Get project
│   ├── DELETE /{id}              # Delete project
│   ├── GET /{id}/files           # List files in project
│   ├── GET /{id}/tables          # List tables in project
│   └── POST /{id}/upload         # Upload to project
│
├── /upload                       # File upload/processing
│   ├── POST /                    # Upload file
│   ├── POST /process             # Process uploaded file
│   └── GET /status/{job_id}      # Upload job status
│
├── /chat                         # Chat/query interface
│   ├── POST /query               # Send query
│   ├── POST /clarify             # Clarification response
│   └── GET /history/{project}    # Chat history
│
├── /playbooks                    # Playbook management
│   ├── GET /                     # List playbooks
│   ├── POST /                    # Create playbook
│   ├── GET /{id}                 # Get playbook
│   ├── POST /{id}/execute        # Run playbook
│   └── GET /{id}/progress        # Execution progress
│
├── /bi                           # BI/reporting
│   ├── POST /query               # Run BI query
│   ├── GET /schema/{project}     # Get schema for project
│   └── GET /suggestions/{project} # Query suggestions
│
├── /reference                    # Reference library
│   ├── GET /                     # List reference docs
│   ├── POST /upload              # Upload reference doc
│   └── DELETE /{id}              # Remove reference doc
│
├── /health                       # System health
│   ├── GET /                     # Basic health
│   └── GET /operational          # Detailed metrics
│
├── /metrics                      # System metrics
│   ├── GET /                     # All metrics
│   └── GET /llm                  # LLM-specific
│
├── /admin                        # Admin operations
│   ├── DELETE /cache             # Clear cache
│   ├── POST /cleanup             # Run cleanup
│   ├── GET /learning/stats       # Learning stats
│   └── DELETE /project/{id}      # Force delete
│
└── /auth                         # Authentication
    ├── GET /me                   # Current user
    └── GET /permissions          # User permissions

9.5 Migration Checklist
When fixing endpoint structure:
Step 1: Update Router File
python# BEFORE
router = APIRouter(prefix="/api/some-thing", tags=["thing"])

# AFTER
router = APIRouter(tags=["thing"])  # Remove prefix
Step 2: Update main.py
python# Ensure prefix is defined here
app.include_router(thing.router, prefix="/api/some-thing", tags=["thing"])
Step 3: Update Frontend
typescript// Update any hardcoded paths
const API_BASE = '/api/some-thing';
Step 4: Test
bash# Verify endpoint works
curl https://your-domain.com/api/some-thing/endpoint

9.6 Import Consistency (Related Issue)
XLR8 has two utils directories:

/utils/ - Core infrastructure (rag_handler, llm_orchestrator, structured_data_handler)
/backend/utils/ - Business logic (playbook_framework, consultative_synthesis)

THE RULE
Pick ONE import style per file and use it consistently.
python# ❌ WRONG - Mixed imports
from utils.llm_orchestrator import LLMOrchestrator
from backend.utils.consultative_synthesis import ConsultativeSynthesizer

# ✅ CORRECT - Consistent with try/except fallback
try:
    from utils.llm_orchestrator import LLMOrchestrator
    from utils.consultative_synthesis import ConsultativeSynthesizer
except ImportError:
    from backend.utils.llm_orchestrator import LLMOrchestrator
    from backend.utils.consultative_synthesis import ConsultativeSynthesizer
Long-term Resolution
Eventually consolidate to single /backend/utils/ with proper __init__.py exports. Until then, use the try/except pattern consistently.

9.7 Quick Reference
Router Template
python"""
Router for [RESOURCE NAME]
"""
from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["resource-name"])  # NO PREFIX

@router.get("/")
async def list_resources():
    """List all resources."""
    pass

@router.post("/")
async def create_resource():
    """Create a resource."""
    pass

@router.get("/{resource_id}")
async def get_resource(resource_id: str):
    """Get a specific resource."""
    pass

@router.delete("/{resource_id}")
async def delete_resource(resource_id: str):
    """Delete a resource."""
    pass
main.py Template
python# All routers with explicit prefixes
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(upload.router, prefix="/api/upload", tags=["upload"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(playbooks.router, prefix="/api/playbooks", tags=["playbooks"])
app.include_router(bi.router, prefix="/api/bi", tags=["bi"])
app.include_router(health.router, prefix="/api/health", tags=["health"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])

This is the law. When creating new endpoints, follow these patterns.

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
