# XLR8 Architecture

**Last Updated:** January 11, 2026  
**Status:** Post-GET HEALTHY Sprint, Intelligence Layer Active

---

## System Overview

XLR8 is a universal SaaS implementation analysis platform. It ingests customer data and configuration files, analyzes them against best practices and regulatory requirements, and provides consultative insights.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              XLR8 PLATFORM                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                    │
│   │   Frontend  │    │   Backend   │    │  Databases  │                    │
│   │   (Vercel)  │◄──►│  (Railway)  │◄──►│             │                    │
│   │   React     │    │  FastAPI    │    │  DuckDB     │                    │
│   └─────────────┘    └─────────────┘    │  ChromaDB   │                    │
│                             │           │  Supabase   │                    │
│                             ▼           └─────────────┘                    │
│                      ┌─────────────┐                                       │
│                      │  Ollama     │                                       │
│                      │  (Local LLM)│                                       │
│                      └─────────────┘                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Component | Technology | Location | Purpose |
|-----------|------------|----------|---------|
| Frontend | React 18 | Vercel | User interface |
| Backend | FastAPI | Railway | API, processing |
| Structured Data | DuckDB | Railway (in-memory) | Reality truth, queries |
| Vector Data | ChromaDB | Railway (persistent) | Reference, Regulatory, Compliance |
| App State | Supabase | Cloud | Users, projects, settings |
| Local LLM | Ollama | Railway | DeepSeek (SQL), Mistral (synthesis) |
| Cloud LLM | Claude API | Anthropic | Fallback only |
| File Processing | Various | Railway | PDF, Excel, CSV parsing |

---

## Directory Structure

```
/xlr8-main
├── ARCHITECTURE.md              # This file
├── WAYS_OF_WORKING.md           # Principles and practices
├── ROADMAP.md                   # Phase overview (TODO)
│
├── /backend
│   ├── main.py                  # FastAPI app entry
│   ├── /routers
│   │   ├── projects.py          # Project CRUD, recalc, analyze
│   │   ├── chat.py              # Chat endpoint
│   │   ├── upload.py            # File upload handling
│   │   └── ...
│   │
│   └── /utils
│       ├── structured_data_handler.py   # DuckDB management
│       ├── project_intelligence.py      # Post-upload analysis
│       │
│       └── /intelligence                # ★ CORE INTELLIGENCE LAYER
│           ├── term_index.py            # Term → table/column lookup
│           ├── sql_assembler.py         # Term matches → SQL
│           ├── metadata_reasoner.py     # Fallback for unknown terms
│           ├── query_resolver.py        # Chat query handling (needs refactor)
│           └── intent_parser.py         # SOW/document parsing
│
├── /frontend
│   ├── /src
│   │   ├── App.jsx              # Routes
│   │   ├── /pages
│   │   │   ├── AdminPage.jsx    # Admin tools
│   │   │   ├── IntelligenceTestPage.jsx  # ★ NEW: Test TermIndex + SQLAssembler
│   │   │   ├── DataPage.jsx     # Data exploration
│   │   │   └── ChatPage.jsx     # Main chat interface
│   │   └── /components
│
└── /doc
    └── METADATA_REASONER_IMPLEMENTATION.md
```

---

## Five Truths Data Model

All analysis maps to five truths:

| Truth | Storage | Source | Example |
|-------|---------|--------|---------|
| **Reality** | DuckDB | Uploaded data files | Employee records, earnings, deductions |
| **Intent** | ChromaDB | SOW, requirements docs | "Customer wants 401k match at 4%" |
| **Configuration** | DuckDB | Config validation files | UKG system settings |
| **Reference** | ChromaDB | Vendor documentation | UKG best practices |
| **Regulatory** | ChromaDB | Compliance documents | IRS rules, state laws |

---

## Core Intelligence Layer

### Overview

The intelligence layer converts natural language questions into SQL without LLM generation.

```
User Question: "employees in Texas with 401k"
        │
        ▼
┌───────────────────┐
│   parse_intent()  │  → QueryIntent.LIST, domain hints
└───────────────────┘
        │
        ▼
┌───────────────────┐
│    TermIndex      │  → "texas" → stateprovince = 'TX'
│  .resolve_terms() │  → "401k" → description ILIKE '%401k%'
└───────────────────┘
        │
        ▼
┌───────────────────┐
│   SQLAssembler    │  → SELECT t0.* FROM Personal t0
│    .assemble()    │     JOIN Deductions t1 ON ...
└───────────────────┘     WHERE t0.stateprovince = 'TX'
        │                   AND t1.description ILIKE '%401k%'
        ▼
     Execute SQL
        │
        ▼
     Results + Synthesis
```

### TermIndex (`term_index.py`)

**Purpose:** O(1) lookup from user terms to SQL filter specifications.

**Key Tables:**
- `_term_index` - Term → table/column/operator/value mappings
- `_entity_tables` - Entity → primary table mappings
- `_column_mappings` - Column semantic types for joins

**Key Methods:**
- `resolve_terms(terms)` - Returns List[TermMatch] for given terms
- `build_from_profiles()` - Populates index from column profiles
- `recalc_term_index()` - Full rebuild from current data

**Current State:** ✅ Working - 11,273 terms indexed for TEA1000

### SQLAssembler (`sql_assembler.py`)

**Purpose:** Deterministic SQL generation from term matches.

**Key Methods:**
- `assemble(intent, term_matches, domain)` - Returns AssembledQuery
- `_deduplicate_term_matches()` - One match per term, prefers primary table
- `_get_primary_table()` - Determines FROM table
- `_resolve_tables_and_joins()` - Builds JOINs with valid paths only
- `_build_where_clause()` - Safe WHERE generation

**Key Features (as of 2026-01-11):**
- ✅ Domain indicator word filtering ("employees" not treated as filter)
- ✅ Term deduplication (prevents over-joining)
- ✅ Deterministic alias assignment (primary = t0)
- ✅ Safe WHERE clause (only references tables in FROM)
- ✅ Fallback table lookup when entity_primary empty

**Current State:** ✅ Working - categorical lookups + multi-table JOINs

### MetadataReasoner (`metadata_reasoner.py`)

**Purpose:** Fallback for terms not in TermIndex. Queries existing metadata to find likely matches.

**Key Methods:**
- `resolve_unknown_term(term, context_domain)` - Returns List[ReasonedMatch]
- `_classify_term()` - keyword | code | name | mixed
- `_get_target_domains()` - Domain hints from term content

**Current State:** ✅ Working - finds description columns for unknown terms like "401k"

### QueryResolver (`query_resolver.py`)

**Purpose:** Chat query handling.

**Current State:** ⚠️ NEEDS REFACTOR
- Has parallel SQL building logic
- Should be thin wrapper around TermIndex + SQLAssembler
- Currently ~3200 lines, should be ~500

---

## DuckDB Schema

### Metadata Tables (System)

| Table | Purpose |
|-------|---------|
| `_table_classifications` | Domain, type, relationships for each table |
| `_column_profiles` | Stats, types, top values for each column |
| `_column_mappings` | Semantic types, join priorities |
| `_term_index` | Term → filter lookups |
| `_entity_tables` | Entity → table mappings |
| `_organizational_metrics` | Headcounts, structure analysis |
| `_intelligence_lookups` | Cached pattern matches |

### Data Tables (Customer)

Tables are named by upload: `{project}_{original_filename}` (sanitized)

Example for TEA1000 project:
- `tea1000_employee_conversion_testing_team_us_1_personal`
- `tea1000_team_configuration_validation_deduction_benefit_plans`
- `tea1000_companytax_company_tax_listing`

---

## API Endpoints

### Intelligence Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/intelligence/{project}/analyze` | POST | Run full intelligence analysis |
| `/api/projects/{project}/recalc` | POST | Rebuild term index |
| `/api/intelligence/{project}/resolve-terms` | POST | Test term resolution |

### Project Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/projects` | GET | List projects |
| `/api/projects/{id}` | GET | Get project details |
| `/api/projects/{id}/tables` | GET | List tables in project |
| `/api/projects/{id}/reprofile` | POST | Refresh column profiles |

### Chat Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/chat` | POST | Main chat interface |
| `/api/chat/history` | GET | Chat history |

---

## Frontend Routes

| Route | Component | Purpose |
|-------|-----------|---------|
| `/` | HomePage | Landing |
| `/chat` | ChatPage | Main chat interface |
| `/data` | DataPage | Data exploration |
| `/admin` | AdminPage | Admin tools |
| `/admin/intelligence-test` | IntelligenceTestPage | ★ Test term resolution |

---

## Current Capabilities

### Working ✅
- File upload (PDF, Excel, CSV)
- Table profiling and classification
- Term index population
- Categorical lookups ("Texas" → TX)
- Multi-table JOINs via semantic types
- Cross-domain queries ("employees with 401k")
- Intelligence test page for validation

### Partial ⚠️
- QueryResolver (works but needs refactor)
- Vector search (basic similarity, not domain-aware)
- Synthesis (basic LLM pass-through)

### Not Working ❌
- Numeric comparisons ("salary > 50000")
- Date filters ("hired last year")
- OR logic ("Texas or California")
- Negation ("NOT in Texas")
- Aggregations ("total earnings")
- Group by ("headcount by state")
- Superlatives ("highest paid")
- Multi-hop ("manager in California")
- API connectivity (UKG direct pull)

---

## Deployment

### Backend (Railway)
- **URL:** `https://hcmpact-xlr8-production.up.railway.app`
- **Branch:** main
- **Auto-deploy:** Yes

### Frontend (Vercel)
- **URL:** Production URL on Vercel
- **Branch:** main
- **Auto-deploy:** Yes

### Environment Variables
- `ANTHROPIC_API_KEY` - Claude fallback
- `SUPABASE_URL` - Database
- `SUPABASE_KEY` - Auth
- `OPENAI_API_KEY` - Vision API for PDFs

---

## Known Issues

1. **QueryResolver duplication** - Has own SQL logic parallel to SQLAssembler
2. **Project case sensitivity** - Some queries need LOWER() normalization
3. **Join path gaps** - Not all table combinations have semantic mappings

---

## Next Steps

See ROADMAP.md for phase details.

**Immediate:**
1. Refactor QueryResolver to use TermIndex + SQLAssembler
2. Add Duckling for numeric/date parsing
3. Complete SQL evolutions 3-10

---

## Version History

| Date | Change |
|------|--------|
| 2026-01-11 | Complete rewrite - reflects current state post-Intelligence Test Page work |
