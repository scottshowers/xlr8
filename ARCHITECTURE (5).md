# XLR8 Architecture

**Last Updated:** January 13, 2026  
**Status:** Evolution 10 Complete - Multi-Hop Relationships Working

---

## System Overview

XLR8 is a universal SaaS implementation analysis platform. It ingests customer data and configuration files, analyzes them against best practices and regulatory requirements, and provides consultative insights through natural language queries.

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
| Structured Data | DuckDB | Railway (persistent) | Reality truth, queries, metrics |
| Vector Data | ChromaDB | Railway (persistent) | Reference, Regulatory, Compliance |
| App State | Supabase | Cloud | Users, projects, settings |
| Local LLM | Ollama | Railway | DeepSeek (SQL), Mistral (synthesis) |
| Cloud LLM | Claude API | Anthropic | Fallback only |
| File Processing | Various | Railway | PDF, Excel, CSV parsing |

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

### SQL Evolution Stack (All 10 Working ✅)

The intelligence layer converts natural language questions into SQL without LLM generation.

| Evolution | Capability | Example |
|-----------|------------|---------|
| **1** | Categorical Lookups | "employees in Texas" → `stateprovince = 'TX'` |
| **2** | Multi-table JOINs | "employees with 401k" → JOIN deductions |
| **3** | Numeric Comparisons | "salary above 75000" → `annual_salary > 75000` |
| **4** | Date Filters | "hired after 2023" → `last_hire_date > '2023-01-01'` |
| **5** | OR Logic | "Texas or California" → `state IN ('TX', 'CA')` |
| **6** | Negation | "not in Texas" → `stateprovince != 'TX'` |
| **7** | Aggregations | "total by state" → `GROUP BY` + `SUM/COUNT` |
| **8** | GROUP BY | "headcount by department" → dimensional queries |
| **9** | Superlatives | "top 5 highest paid" → `ORDER BY salary DESC LIMIT 5` |
| **10** | Multi-Hop Relationships | "manager's department" → self-join traversal |

### Query Flow

```
User Question: "manager's department"
        │
        ▼
┌───────────────────────────┐
│   detect_multi_hop_query()│  → Check for possessive pattern
└───────────────────────────┘
        │
        ▼
┌───────────────────────────┐
│  _column_relationships    │  → Find supervisor_name → name
└───────────────────────────┘
        │
        ▼
┌───────────────────────────┐
│   TARGET_ATTRIBUTES       │  → Map "department" → org_level_1
└───────────────────────────┘
        │
        ▼
┌───────────────────────────┐
│   Build Self-Join SQL     │  → SELECT t0.*, t1_mgr."org_level_1"
└───────────────────────────┘     FROM employees t0
        │                         JOIN employees t1_mgr 
        ▼                           ON t0.supervisor_name = t1_mgr.name
     Execute SQL
        │
        ▼
     Results + Synthesis
```

### Standard Query Flow (Non-Multi-Hop)

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
     Execute SQL → Results + Synthesis
```

---

## Key Components

### TermIndex (`term_index.py`)

**Purpose:** O(1) lookup from user terms to SQL filter specifications.

**Key Tables:**
- `_term_index` - Term → table/column/operator/value mappings
- `_entity_tables` - Entity → primary table mappings  
- `_column_relationships` - Self-reference and FK relationships

**Key Methods:**
- `resolve_terms_enhanced()` - Returns List[TermMatch] with numeric/date/OR/negation support
- `recalc_term_index()` - Full rebuild including relationship detection

### SQLAssembler (`sql_assembler.py`)

**Purpose:** Deterministic SQL generation from term matches.

**Key Methods:**
- `assemble()` - Standard query assembly
- `build_multi_hop_query()` - Self-join queries (Evolution 10)
- `_find_target_attribute()` - Maps user terms to column names

### RelationshipResolver (`relationship_resolver.py`)

**Purpose:** Multi-hop query detection and relationship chain building.

**Key Methods:**
- `detect_multi_hop_query()` - Pattern detection for possessive queries
- `parse_relationship_query()` - Extract source/target from "X's Y" patterns

**Pattern Support:**
- Possessive: "manager's department", "supervisor's location"
- Named: "John's team", "Sarah's reports"
- Keyword: "reports to", "managed by"

---

## DuckDB Schema

### System Metadata Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `_column_profiles` | Column statistics | distinct_count, top_values_json, inferred_type, filter_category |
| `_table_classifications` | Table categorization | domain, table_type (MASTER/TRANSACTION/CONFIG) |
| `_term_index` | Term lookups | term, table_name, column_name, operator, match_value |
| `_entity_tables` | Entity mappings | entity, primary_table |
| `_column_relationships` | Join paths | source_table, source_column, target_table, target_column, semantic_meaning |
| `_organizational_metrics` | Headcounts, structure | project, metric_type, metric_value |
| `_intelligence_lookups` | Cached patterns | project, lookup_key, result_json |
| `_intelligence_findings` | Analysis results | finding_type, severity, description |
| `_intelligence_tasks` | Recommended actions | task_type, priority, description |

### Data Tables (Customer)

Tables are named by upload: `{project}_{original_filename}` (sanitized)

Example for TEA1000 project:
- `tea1000_employee_conversion_testing_team_us_1_company`
- `tea1000_employee_conversion_testing_team_us_1_personal`
- `tea1000_team_configuration_validation_deduction_benefit_plans`

---

## ChromaDB Collections

| Collection | Purpose | Content |
|------------|---------|---------|
| `documents` | All uploaded docs | PDF text, metadata, embeddings |
| `reference` | Vendor docs | Best practices, configuration guides |
| `regulatory` | Compliance docs | IRS rules, state regulations |
| `intent` | Customer requirements | SOW, requirements, decisions |

---

## API Endpoints

### Intelligence Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/intelligence/{project}/analyze` | POST | Run full intelligence analysis |
| `/api/intelligence/{project}/relationships` | GET | View detected relationships |
| `/api/intelligence/{project}/detect-relationships` | GET | Force relationship detection |
| `/api/intelligence/{project}/run-multi-hop` | GET | Debug multi-hop query |

### Project Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/projects/{id}/recalc` | POST | Rebuild term index + relationships |
| `/api/projects/{id}/reprofile` | POST | Refresh column profiles |
| `/api/projects/{id}/resolve-terms` | POST | Test term resolution with SQL output |

---

## Current Capabilities

### Working ✅
- File upload (PDF, Excel, CSV)
- Table profiling and classification
- Term index with 11K+ terms
- All 10 SQL evolutions
- Multi-hop self-joins ("manager's department")
- Cross-domain queries ("employees with 401k")
- Numeric comparisons ("salary > 50000")
- Date filters ("hired after 2023")
- OR logic ("Texas or California")
- Negation ("not in Texas")
- Aggregations and GROUP BY
- Superlatives ("top 5 highest paid")

### Partial ⚠️
- QueryResolver (works but needs refactor)
- Synthesis (basic LLM pass-through)

### Roadmap
- Phase 3: Synthesis improvements
- Phase 4: E2E flow + Export
- Phase 7: Feature Engine
- Phase 8: Playbook Engine

---

## Deployment

### Backend (Railway)
- **URL:** `https://hcmpact-xlr8-production.up.railway.app`
- **Branch:** main
- **Auto-deploy:** Yes

### Frontend (Vercel)
- **Branch:** main
- **Auto-deploy:** Yes

---

## Version History

| Date | Change |
|------|--------|
| 2026-01-13 | Evolution 10 (Multi-Hop) complete, all 10 evolutions working |
| 2026-01-11 | Intelligence Test Page, SQLAssembler fixes |
| 2026-01-08 | GET HEALTHY Sprint complete |
