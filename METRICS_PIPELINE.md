# XLR8 Data Metrics Pipeline

**Last Updated:** January 13, 2026

This document shows where and what metrics are captured during data ingestion.

---

## Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           DATA INGESTION PIPELINE                                   │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                                   │
                    ▼                                   ▼
        ┌───────────────────┐               ┌───────────────────┐
        │   STRUCTURED DATA │               │ UNSTRUCTURED DATA │
        │  (Excel, CSV)     │               │    (PDF)          │
        └─────────┬─────────┘               └─────────┬─────────┘
                  │                                   │
                  ▼                                   ▼
        ┌─────────────────────────────────────────────────────────┐
        │                    STORAGE LAYER                        │
        ├─────────────────────────────────────────────────────────┤
        │                                                         │
        │   ┌─────────────┐              ┌─────────────┐          │
        │   │   DuckDB    │              │  ChromaDB   │          │
        │   │             │              │             │          │
        │   │ • Raw Data  │              │ • Embeddings│          │
        │   │ • Metrics   │              │ • Metadata  │          │
        │   │ • Index     │              │ • Chunks    │          │
        │   └─────────────┘              └─────────────┘          │
        │                                                         │
        └─────────────────────────────────────────────────────────┘
```

---

## Structured Data Metrics (DuckDB)

### On File Upload (Excel/CSV)

```
┌─────────────────────────────────────────────────────────────────┐
│                     STRUCTURED UPLOAD                           │
│                                                                 │
│   Excel/CSV ──► Parse ──► Create Table ──► Profile Columns      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              _column_profiles (per column)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   project             │ "TEA1000"                               │
│   table_name          │ "tea1000_employee_..._company"          │
│   column_name         │ "supervisor_name"                       │
│   ─────────────────────────────────────────────────────────────│
│   METRICS CAPTURED:                                             │
│   ─────────────────────────────────────────────────────────────│
│   • distinct_count    │ 847                                     │
│   • distinct_values   │ JSON array of unique values             │
│   • top_values_json   │ Most frequent values + counts           │
│   • original_dtype    │ "VARCHAR"                               │
│   • inferred_type     │ "text" | "numeric" | "date"             │
│   • filter_category   │ "status" | "location" | "company"       │
│   • is_categorical    │ true/false                              │
│   • min_value         │ For numeric columns                     │
│   • max_value         │ For numeric columns                     │
│   • min_date          │ For date columns                        │
│   • max_date          │ For date columns                        │
│   • null_count        │ Number of null values                   │
│   • sample_values     │ Representative samples                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### On Recalc/Reprofile

```
┌─────────────────────────────────────────────────────────────────┐
│              _table_classifications (per table)                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   project             │ "TEA1000"                               │
│   table_name          │ "tea1000_employee_..._company"          │
│   ─────────────────────────────────────────────────────────────│
│   METRICS CAPTURED:                                             │
│   ─────────────────────────────────────────────────────────────│
│   • domain            │ "demographics" | "earnings" | "taxes"   │
│   • table_type        │ "MASTER" | "TRANSACTION" | "CONFIG"     │
│   • row_count         │ 1,247                                   │
│   • column_count      │ 23                                      │
│   • truth_type        │ "reality" | "configuration"             │
│   • is_hub            │ true/false (primary entity table)       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│              _term_index (per unique value)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   BUILT FROM _column_profiles:                                  │
│   ─────────────────────────────────────────────────────────────│
│   • term              │ "texas", "tx", "401k", "active"         │
│   • term_type         │ "value" | "synonym" | "code"            │
│   • table_name        │ Source table                            │
│   • column_name       │ Source column                           │
│   • operator          │ "=" | "ILIKE" | ">" | "<"               │
│   • match_value       │ Actual value to filter on               │
│   • domain            │ "location" | "status" | "deduction"     │
│   • confidence        │ 0.0 - 1.0                               │
│                                                                 │
│   Example: "texas" → stateprovince = 'TX' (confidence: 1.0)     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│              _column_relationships (per relationship)           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   DETECTED PATTERNS:                                            │
│   ─────────────────────────────────────────────────────────────│
│   • source_table      │ "tea1000_employee_..._company"          │
│   • source_column     │ "supervisor_name"                       │
│   • target_table      │ "tea1000_employee_..._company"          │
│   • target_column     │ "name"                                  │
│   • relationship_type │ "self_reference" | "foreign_key"        │
│   • semantic_meaning  │ "supervisor" | "parent_org"             │
│   • confidence        │ 0.85                                    │
│                                                                 │
│   Used for Evolution 10 multi-hop queries                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│              _organizational_metrics (aggregates)               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   COMPUTED METRICS:                                             │
│   ─────────────────────────────────────────────────────────────│
│   • total_employees   │ 1,247                                   │
│   • active_count      │ 1,102                                   │
│   • terminated_count  │ 145                                     │
│   • state_breakdown   │ {"TX": 423, "CA": 287, ...}             │
│   • dept_breakdown    │ {"HR": 45, "IT": 89, ...}               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Unstructured Data Metrics (ChromaDB + DuckDB)

### On PDF Upload

```
┌─────────────────────────────────────────────────────────────────┐
│                      PDF UPLOAD PIPELINE                        │
│                                                                 │
│   PDF ──► Vision API ──► Extract Tables ──► Store + Embed       │
│           (pages 1-2)                                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────┐
│   DuckDB: _pdf_tables   │     │   ChromaDB: documents   │
├─────────────────────────┤     ├─────────────────────────┤
│                         │     │                         │
│ EXTRACTED TABLE DATA:   │     │ VECTOR STORAGE:         │
│                         │     │                         │
│ • project               │     │ • document_id           │
│ • source_file           │     │ • chunk_text            │
│ • page_number           │     │ • embedding (1536-dim)  │
│ • table_index           │     │                         │
│ • table_data (JSON)     │     │ METADATA:               │
│ • extraction_method     │     │ • source_file           │
│ • confidence            │     │ • project               │
│ • fingerprint (dedup)   │     │ • page_number           │
│                         │     │ • truth_type            │
│                         │     │ • doc_type              │
│                         │     │ • upload_date           │
│                         │     │                         │
└─────────────────────────┘     └─────────────────────────┘
```

### Document Classification

```
┌─────────────────────────────────────────────────────────────────┐
│                  DOCUMENT CLASSIFICATION                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   Based on content analysis, documents are tagged:              │
│                                                                 │
│   truth_type:                                                   │
│   • "reference"    - Vendor documentation, guides               │
│   • "regulatory"   - IRS rules, state regulations               │
│   • "intent"       - SOW, requirements, customer decisions      │
│   • "compliance"   - Audit reports, validation results          │
│                                                                 │
│   doc_type:                                                     │
│   • "configuration_guide"                                       │
│   • "best_practices"                                            │
│   • "regulatory_update"                                         │
│   • "sow" (Statement of Work)                                   │
│   • "validation_report"                                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Metrics Access Points

### Via API

```
GET  /api/intelligence/{project}/relationships    → View detected relationships
GET  /api/intelligence/{project}/metrics          → Organizational metrics
GET  /api/intelligence/{project}/findings         → Analysis findings
GET  /api/projects/{id}/term-index               → Term index stats
POST /api/projects/{id}/recalc                   → Rebuild all metrics
POST /api/projects/{id}/reprofile                → Refresh column profiles
```

### Via DuckDB Queries

```sql
-- Column statistics
SELECT * FROM _column_profiles WHERE project = 'TEA1000';

-- Table classifications
SELECT * FROM _table_classifications WHERE project = 'TEA1000';

-- Term index (searchable terms)
SELECT * FROM _term_index WHERE project = 'TEA1000';

-- Relationships (for multi-hop)
SELECT * FROM _column_relationships WHERE project = 'TEA1000';

-- Org metrics
SELECT * FROM _organizational_metrics WHERE project = 'TEA1000';
```

---

## Data Flow Summary

```
┌────────────────────────────────────────────────────────────────────────────┐
│                                                                            │
│   UPLOAD                    PROCESS                    STORE               │
│   ──────                    ───────                    ─────               │
│                                                                            │
│   Excel/CSV ─────► Parse ─────► Profile ─────► _column_profiles           │
│                       │                        _table_classifications      │
│                       │                                                    │
│                       └──────► Term Index ───► _term_index                │
│                                   │            _entity_tables              │
│                                   │                                        │
│                                   └──────────► _column_relationships       │
│                                                                            │
│   PDF ───────────► Vision API ──► Extract ───► _pdf_tables (DuckDB)       │
│                       │                        documents (ChromaDB)        │
│                       │                                                    │
│                       └──────────────────────► Embeddings + Metadata      │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Metrics for Stakeholder Discussion

1. **Data Quality Metrics**
   - Distinct value counts per column
   - Null percentage
   - Data type inference accuracy

2. **Intelligence Metrics**
   - Terms indexed (currently 11K+ for TEA1000)
   - Relationships detected (self-ref, FK)
   - Query resolution success rate

3. **Document Metrics**
   - PDFs processed with confidence scores
   - Table extraction rates
   - Vector embedding coverage

4. **Organizational Metrics**
   - Employee headcounts
   - Status breakdowns
   - Geographic distribution
