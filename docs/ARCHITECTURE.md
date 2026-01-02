# XLR8 Platform Architecture
## Technical Stack & System Design

**Version:** 5.0.0  
**Architecture:** Five Truths Intelligence Model  
**Deployment:** Railway (Backend) + Vercel (Frontend)  
**Last Updated:** January 2, 2026

---

## 🏗️ SYSTEM OVERVIEW

XLR8 is a domain-agnostic SaaS implementation analysis platform. It ingests customer configuration data, compares it against reference standards, and provides consultative insights—automating what traditionally required senior consultants.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER BROWSER                              │
│                    React SPA (Vercel)                           │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                    RAILWAY PLATFORM                              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  FastAPI Backend (Python 3.11)                           │   │
│  │  - 25 API Routers / 247 Endpoints                        │   │
│  │  - Smart Router (unified file processing)                │   │
│  │  - Intelligence Engine (Five Truths)                     │   │
│  └─────────┬──────────────────────────────────────┬─────────┘   │
└────────────┼──────────────────────────────────────┼─────────────┘
             │                                       │
      ┌──────┴──────┐                         ┌──────┴──────┐
      │   STORAGE   │                         │    LLMs     │
      └──────┬──────┘                         └──────┬──────┘
             │                                       │
    ┌────────┼────────┐                    ┌─────────┼─────────┐
    ▼        ▼        ▼                    ▼                   ▼
┌────────┐┌────────┐┌────────┐      ┌──────────────┐   ┌──────────────┐
│DuckDB  ││ChromaDB││Supabase│      │ Ollama       │   │ Cloud APIs   │
│Reality ││Semantic││Metadata│      │ (Local LLMs) │   │ (Fallback)   │
│        ││ Search │├────────┤      │ - DeepSeek   │   │ - Claude     │
│SQL Data││Vectors ││PostgreSQL     │ - Mistral    │   │ - Groq       │
└────────┘└────────┘└────────┘      └──────────────┘   └──────────────┘
```

---

## 💻 TECHNOLOGY STACK

### Frontend Layer

**Framework:** React 18 + Vite
- **Hosting:** Vercel (auto-deploy from GitHub)
- **Styling:** Tailwind CSS
- **Charts:** Recharts
- **State:** React Context + hooks

**Key Pages:**
| Page | Purpose |
|------|---------|
| DataPage | File upload, project management |
| AnalyticsPage | SQL builder, natural language queries |
| PlaybooksPage | Guided analysis workflows |
| WorkAdvisor | Chat-based consulting |
| ArchitecturePage | Live system documentation |

### Backend Layer

**Framework:** FastAPI (Python 3.11)
- **Hosting:** Railway (PaaS)
- **ASGI:** Uvicorn
- **Background Jobs:** Threading + asyncio

**Key Files:**
| File | Lines | Purpose |
|------|-------|---------|
| `intelligence_engine.py` | 5,937 | Core AI orchestrator - Five Truths |
| `structured_data_handler.py` | 4,800+ | DuckDB storage and queries |
| `unified_chat.py` | 3,449 | Chat routing and synthesis |
| `project_intelligence.py` | 2,245 | Auto-discovery on upload |
| `smart_router.py` | 1,044 | Universal file routing |
| `consultative_synthesis.py` | 839 | LLM answer generation |

### Storage Layer

**Three Specialized Databases:**

| Database | Purpose | Data Stored |
|----------|---------|-------------|
| **DuckDB** | Reality (SQL queries) | Customer Excel/CSV data, column profiles |
| **ChromaDB** | Semantic search | Document chunks, embeddings (768-dim) |
| **Supabase** | Metadata + Auth | Projects, file registry, relationships |

**DuckDB System Tables:**
- `_schema_metadata` — Table definitions, display names
- `_column_profiles` — **★ CRITICAL** Column values for query matching
- `_intelligence_lookups` — Code-to-description mappings
- `_intelligence_relationships` — Table relationships
- `{project}_{filename}` — Actual customer data

### AI/LLM Layer

**Local First = Privacy + Speed + Cost**

| Model | Purpose | Location |
|-------|---------|----------|
| DeepSeek | SQL generation | Ollama (local) |
| Mistral | Synthesis/analysis | Ollama (local) |
| nomic-embed-text | Embeddings | Ollama (local) |
| Claude API | Complex fallback | Cloud |
| Groq (llama-3.3-70b) | Pay register extraction | Cloud |

**LLM Selection Logic:**
```python
if task == "sql_generation":
    use_model("deepseek")  # Best at SQL
elif task == "synthesis":
    use_model("mistral")   # Fast, good reasoning
elif task == "complex_analysis" and local_failed:
    use_model("claude")    # Fallback only
```

---

## 🧠 FIVE TRUTHS ARCHITECTURE

The core IP of XLR8. Every question is answered by triangulating five sources of truth:

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER QUESTION                             │
│              "Is our SUI rate configured correctly?"             │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    INTELLIGENCE ENGINE                           │
│                  (intelligence_engine.py)                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   REALITY   │     │   INTENT    │     │   CONFIG    │
│   DuckDB    │     │  ChromaDB   │     │   DuckDB    │
│             │     │             │     │             │
│ "Current    │     │ "Customer   │     │ "Tax code   │
│  rate: 2.7%"│     │  wanted all │     │  SUI maps   │
│             │     │  state taxes"│    │  to cat 4"  │
└─────────────┘     └─────────────┘     └─────────────┘
         │                   │                   │
         └───────────────────┼───────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  REFERENCE  │     │ REGULATORY  │     │ SYNTHESIZER │
│  ChromaDB   │     │  ChromaDB   │     │   Mistral   │
│             │     │             │     │             │
│ "Valid SUI  │     │ "Texas SUI  │     │ Triangulate │
│  range:     │     │  due        │     │ + Conflicts │
│  0.1%-12%"  │     │  quarterly" │     │ + Recommend │
└─────────────┘     └─────────────┘     └─────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CONSULTATIVE ANSWER                           │
│  "Your SUI rate of 2.7% is within valid range. However, your    │
│   config shows quarterly filing but Texas requires monthly for   │
│   employers with 10+ employees. Recommend: Update filing freq."  │
└─────────────────────────────────────────────────────────────────┘
```

### Truth Sources

| Truth | Source | Storage | Function |
|-------|--------|---------|----------|
| **Reality** | Customer data (Excel/CSV) | DuckDB | `_gather_reality()` |
| **Intent** | SOWs, requirements docs | ChromaDB | `_gather_intent()` |
| **Configuration** | System config exports | DuckDB | `_gather_configuration()` |
| **Reference** | Product docs, best practices | ChromaDB | `_gather_reflib()` |
| **Regulatory** | Laws, compliance rules | ChromaDB | `_gather_regulatory()` |

---

## 📊 FIVE-TIER PROCESSING MODEL

### Tier 1: API Entry
**Files:** `backend/main.py`, `backend/routers/*`

All requests enter through FastAPI routers:
- `POST /api/upload` → Smart Router
- `POST /api/chat` → Unified Chat
- `POST /api/bi/execute` → BI Builder
- `POST /api/playbooks/*` → Playbook Engine

### Tier 2: Smart Router + Security
**Files:** `smart_router.py`, PII redaction in `unified_chat.py`

```
File Upload → Determine Type → Route to Processor
                  │
    ┌─────────────┼─────────────┐
    ▼             ▼             ▼
.xlsx/.csv    *register*     .pdf/.docx
    │             │             │
    ▼             ▼             ▼
Structured    Register      Standards
 Handler      Extractor     Processor
```

**Security Features:**
- PII Redaction: SSN, DOB, salary stripped before LLM calls
- Reversible tokens for response restoration
- AES-GCM field encryption in DuckDB

### Tier 3: Processors
**Specialized handlers for each file type:**

| Processor | File | Purpose |
|-----------|------|---------|
| Structured Handler | `structured_data_handler.py` | Excel/CSV → DuckDB |
| Register Extractor | `register_extractor.py` | Pay stubs → AI extraction |
| Standards Processor | `standards_processor.py` | Policy docs → rules |
| PDF Vision Analyzer | `pdf_vision_analyzer.py` | PDF tables → columns |

**★ Critical Function: `_profile_columns()`**
Stores actual VALUES from each column in `_column_profiles.top_values_json`. This enables matching queries like "show SUI rates" to the correct table even when "SUI" isn't a column name—it's a value in a column.

### Tier 4: Intelligence
**Files:** `intelligence_engine.py`, `consultative_synthesis.py`

The brain of XLR8:
1. Parse user question
2. Gather from all Five Truths
3. Score and select relevant tables
4. Execute queries
5. Synthesize consultative answer

**Table Scoring Algorithm:**
```
+120  Three-word name match
+100  Two-word match
+80   ★ VALUE MATCH (from _column_profiles)
+50   Filter candidate match
+40   Location columns present
+30   Single word match
-30   Lookup table penalty
```

### Tier 5: Storage
See Storage Layer section above.

---

## 🔄 CRITICAL DATA FLOWS

### Flow 1: Config Validation → Query Routing (★ MOST CRITICAL)
```
Config upload → store_dataframe() → _profile_columns() → top_values_json
                                                              │
User query: "Show SUI rates" ─────────────────────────────────┘
                                                              │
_select_tables() ← VALUE MATCH +80 ← "SUI" found in top_values_json
```

### Flow 2: PDF Vision Learning (Cost Optimization)
```
PDF upload → get_fingerprint() → Cache check
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                                 ▼
              Cache miss                         Cache hit
                    │                                 │
                    ▼                                 ▼
        Claude Vision ($0.04)                   Reuse columns ($0)
                    │
                    ▼
           store_learned_columns()
```

### Flow 3: Learning Loop (Self-Improvement)
```
User query → find_similar_query() → Cache hit? → Return cached SQL
                                        │
                                        ▼ (miss)
                              Generate SQL → Execute
                                        │
                                        ▼
                              learn_query() → Next time faster
```

### Flow 4: Five Truths Query Resolution
```
Question → Reality → Intent → Config → Reference → Regulatory
                              │
                              ▼
                      Synthesizer triangulates
                              │
                              ▼
                      Consultative answer
```

### Flow 5: Consultative Synthesis
```
Five Truths data → Summarize → Triangulate → Find conflicts
                                                    │
                                                    ▼
                              LLM Synthesis (Mistral → Claude fallback)
                                                    │
                                                    ▼
                              Answer + Confidence + Next Steps
```

---

## 📁 PROJECT STRUCTURE

```
xlr8-main/
├── backend/
│   ├── main.py                 # FastAPI app entry
│   ├── routers/                # 25 API routers
│   │   ├── upload.py           # File upload
│   │   ├── unified_chat.py     # Chat interface
│   │   ├── bi_router.py        # BI Builder
│   │   ├── playbooks.py        # Playbook execution
│   │   ├── smart_router.py     # Universal routing
│   │   └── ...
│   ├── utils/
│   │   ├── intelligence_engine.py   # Five Truths core
│   │   ├── consultative_synthesis.py
│   │   ├── project_intelligence.py
│   │   ├── gap_detection_engine.py
│   │   └── ...
│   └── playbooks/              # Playbook definitions
│
├── frontend/
│   ├── src/
│   │   ├── pages/              # React pages
│   │   ├── components/         # Shared components
│   │   ├── context/            # React context
│   │   └── services/           # API client
│   └── ...
│
├── utils/                      # Shared utilities
│   ├── structured_data_handler.py  # DuckDB operations
│   ├── rag_handler.py              # ChromaDB operations
│   └── database/
│       ├── models.py               # Supabase models
│       └── supabase_client.py
│
├── docs/
│   ├── ARCHITECTURE.md         # This file
│   ├── DEPLOYMENT_GUIDE.md
│   └── SECURITY.md
│
└── data/                       # Runtime data
    └── questions_database.json
```

---

## 🔐 SECURITY ARCHITECTURE

### Data Protection
- **PII Redaction:** 30+ patterns stripped before LLM calls
- **Encryption:** AES-GCM for sensitive DuckDB fields
- **Local LLMs:** Customer data never leaves your infrastructure

### Authentication
- **Supabase Auth:** JWT-based authentication
- **Project Isolation:** Data scoped by project prefix

### Network
- **HTTPS:** All traffic encrypted (Railway/Vercel managed)
- **CORS:** Configured for frontend domain only

---

## 📈 PERFORMANCE CHARACTERISTICS

### Response Times (Typical)
| Operation | Time |
|-----------|------|
| Page load | <2s |
| File upload (10MB) | 3-8s |
| SQL query | <1s |
| Natural language query | 2-5s |
| Playbook execution | 10-30s |
| Register extraction | 10-60s |

### Scaling
- **Railway:** Auto-scaling containers
- **Vercel:** Edge deployment
- **DuckDB:** Per-project isolation
- **Concurrent users:** 50-100 (current tier)

---

## 🚧 WORK IN PROGRESS

| Feature | Status | Priority |
|---------|--------|----------|
| Playbook Builder UI | In Progress | Exit Blocker |
| Customer Landing Page | Planned | High |
| Export Engine (PDF/Excel) | Planned | High |
| Comparison Engine | Planned | High |
| Unified Chat Refactor | Planned | Medium |

---

## 🆕 RECENT ADDITIONS (January 2026)

### Domain Decoder
**File:** `backend/utils/domain_decoder.py`

Consultant knowledge that makes XLR8 smarter. Stores pattern → meaning mappings.

| Pattern | Meaning | Example |
|---------|---------|---------|
| Configuration Validation | What's CONFIGURED in UKG | Earning codes, deduction plans |
| Employee Conversion Testing | What's IN USE by employees | Actual data being used |
| TXC | Taxable Company Car | Fringe benefit earning code |

**Endpoints:** `/api/decoder/*` - list, search, add, update, delete

### Gap Detection Engine
**File:** `backend/utils/gap_detection_engine.py`

Compares Configuration vs Reality to find implementation gaps:
- **Configured but unused:** Code in Config but not in Reality
- **In use but unconfigured:** Code in Reality but not in Config (ERROR!)

Automatically runs during Tier 2 analysis via `project_intelligence.py`.

### Sequential Job Queue
**File:** `backend/routers/upload.py` (JobQueue class)

Prevents Ollama overload by processing ONE upload at a time. Multiple file uploads are queued and processed sequentially.

**Endpoint:** `GET /api/upload/queue-status`

### Relationship Detector
**File:** `backend/utils/relationship_detector.py`

Intelligent table relationship detection:
1. Detects semantic type of each key column
2. Only compares columns of the SAME type
3. Strips prefixes before comparing (home_company_code ↔ company_code)
4. Stores relationships to Supabase for review/confirmation

Called from `project_intelligence.py` during Tier 2 analysis.

---

## 📚 REFERENCES

### Internal Documentation
- `ArchitecturePage.jsx` — Live architecture in the platform
- `DEPLOYMENT_GUIDE.md` — Deployment procedures
- `SECURITY.md` — Security policies

### External
- FastAPI: https://fastapi.tiangolo.com
- DuckDB: https://duckdb.org/docs
- ChromaDB: https://docs.trychroma.com
- Supabase: https://supabase.com/docs

---

**Document Version:** 5.0  
**Last Updated:** January 2, 2026  
**Maintainer:** HCMPACT Engineering
