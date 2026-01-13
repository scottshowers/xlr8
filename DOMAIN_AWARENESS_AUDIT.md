# XLR8 Domain Awareness Audit
## What's Generic vs HCM-Hardcoded

**Date:** January 2026  
**Purpose:** Document domain-specific vs domain-agnostic components before expanding to FINS/ERP

---

## Executive Summary

XLR8 has a **mostly domain-agnostic architecture** with HCM-specific logic concentrated in a few places. The core infrastructure (Context Graph, Truth gathering, Synthesis) is product-neutral. The hardcoding is primarily in:

1. **QueryResolver** - Workforce snapshot logic (active/termed/LOA)
2. **Project Intelligence** - Employee table detection patterns
3. **Domain Patterns** - Table classification regex (already includes GL/FINS patterns)

---

## Architecture Layers

### ✅ DOMAIN-AGNOSTIC (Ready for Any Domain)

#### 1. Context Graph (`structured_data_handler.py`)
- Hub/spoke relationship detection
- Works on ANY table structure
- Discovers relationships via column name matching + FK analysis
- **No domain assumptions**

#### 2. Five Truths Model (`types.py`, `gatherers/`)
- Reality, Intent, Configuration, Reference, Regulatory, Compliance
- Each gatherer is schema-agnostic
- Truth types work for HCM, FINS, ERP, CRM, etc.
- **No domain assumptions**

#### 3. Product Registry (`backend/utils/products/registry.py`)
- Loads product schemas from JSON config files
- Already has FINS schemas:
  - `workday_fins_schema_v1.json` (GL, AP, AR, Projects)
  - `netsuite_schema_v1.json`
  - `sage_intacct_schema_v1.json`
  - `dynamics365_schema_v1.json`
- ProductDomain class handles any domain structure
- **Ready for FINS/ERP**

#### 4. Domain Patterns (`project_intelligence.py:199-237`)
```python
DOMAIN_PATTERNS = {
    TableDomain.EARNINGS: [...],
    TableDomain.DEDUCTIONS: [...],
    TableDomain.TAXES: [...],
    TableDomain.TIME: [...],
    TableDomain.DEMOGRAPHICS: [...],  # HCM
    TableDomain.LOCATIONS: [...],
    TableDomain.BENEFITS: [...],
    TableDomain.GL: [                 # FINS - already exists!
        r'.*general_ledger.*', r'.*gl_.*', r'.*ledger.*', 
        r'.*account.*', r'.*chart_of_accounts.*'
    ],
    TableDomain.JOBS: [...],
    TableDomain.WORKERS_COMP: [...],
}
```
**GL domain already defined** - just needs expansion for AP/AR/Inventory

#### 5. Table Classification (`project_intelligence.py:935-1030`)
- `_classify_table()` - Uses domain patterns, row counts, column patterns
- CONFIG vs TRANSACTION detection
- **Domain-agnostic logic**

#### 6. Synthesis Pipeline (`synthesis_pipeline.py`)
- Assembles truths → calls LLM → returns consultative answer
- Prompts are generic ("senior implementation consultant")
- **No domain assumptions in core flow**

#### 7. LLM Orchestrator (`llm_orchestrator.py`)
- Local LLM (Mistral/DeepSeek) → Claude fallback
- Generic prompts that work for any domain
- **Domain-agnostic**

---

### ⚠️ HCM-HARDCODED (Needs Extension for FINS/ERP)

#### 1. QueryResolver Workforce Snapshot (`query_resolver.py:2573-2760`)

**What it does:**
- Detects employee count queries
- Computes active/termed/LOA breakdown by year
- Returns structured output for consultative synthesis

**HCM-specific logic:**
```python
# Line 2626-2656 - Hardcoded column names
for hint in ['termination_date', 'term_date', 'end_date', 'separation_date']:
    ...
for hint in ['hire_date', 'last_hire_date', 'original_hire_date', 'start_date']:
    ...
```

**FINS equivalent needed:**
- GL: Period status, account counts, trial balance totals
- AP: Open invoice count, aging buckets, vendor concentration
- AR: Open receivable count, DSO, customer concentration
- Inventory: Item counts, valuation, turnover metrics

#### 2. Entity Detection Patterns (`query_resolver.py:104-107`)

**HCM patterns:**
```python
EMPLOYEE_SYNONYMS = [
    'employee', 'employees', 'worker', 'workers', 'staff',
    'headcount', 'head count', 'personnel', 'workforce', 'person',
    'people', 'team member', 'associate', 'associates'
]
```

**FINS equivalents needed:**
```python
GL_SYNONYMS = ['account', 'accounts', 'ledger', 'gl', 'coa', 'chart']
AP_SYNONYMS = ['vendor', 'supplier', 'invoice', 'payable', 'bill']
AR_SYNONYMS = ['customer', 'receivable', 'invoice', 'billing']
INVENTORY_SYNONYMS = ['item', 'product', 'sku', 'inventory', 'stock']
```

#### 3. Status Column Discovery (`project_intelligence.py:1838-1879`)

**HCM assumptions:**
```python
# Looks for 'A' = Active, 'T' = Terminated, 'L' = LOA
if desc_lower == 'active' or desc_lower.startswith('active'):
    active_value = code
```

**FINS equivalents:**
- GL: Period status (Open/Closed/Locked)
- AP: Invoice status (Draft/Pending/Approved/Paid)
- AR: Invoice status (Open/Partial/Closed/Written Off)

#### 4. Dimensional Hub Types (`project_intelligence.py:1994-2005`)

**HCM dimensions:**
```python
dimensional_hub_types = {
    'company_code': 'company',
    'home_company_code': 'company', 
    'country_code': 'country',
    'location_code': 'location',
    'org_level_1_code': 'org_level_1',
    'department_code': 'department',
    'pay_group_code': 'pay_group',
}
```

**FINS dimensions needed:**
```python
fins_dimensional_hub_types = {
    'account_code': 'account',
    'cost_center_code': 'cost_center',
    'fund_code': 'fund',
    'program_code': 'program',
    'business_unit_code': 'business_unit',
    'project_code': 'project',
    'vendor_code': 'vendor',
    'customer_code': 'customer',
    'period_code': 'period',
}
```

#### 5. Consultative Templates (`consultative_templates.py`)

**Currently HCM-focused:**
- `format_count_response()` - "X employees found"
- Entity humanization maps to employee terminology

**FINS templates needed:**
- `format_balance_response()` - Trial balance, account balances
- `format_aging_response()` - AP/AR aging buckets
- `format_period_response()` - Period close status
- Entity maps for accounts, vendors, customers

---

## Product Schema Structure (Already Exists)

### HCM Schema Example (`ukg_pro_schema_v4.json`)
```json
{
  "category": "HCM",
  "domains": {
    "Organization": { "hubs": ["company", "location", ...] },
    "Compensation": { "hubs": ["earning", "pay_group", ...] },
    "Benefits": { "hubs": ["benefit_option", "pto_benefits", ...] },
    "Deductions": { "hubs": ["deduction_code", ...] }
  }
}
```

### FINS Schema Example (`workday_fins_schema_v1.json`)
```json
{
  "category": "FINS",
  "domains": {
    "General_Ledger": { "hubs": ["ledger_account", "journal_entry", "fiscal_period", ...] },
    "Foundation_Worktags": { "hubs": ["company", "cost_center", "fund", "program", ...] },
    "Accounts_Payable": { "hubs": ["supplier", "supplier_invoice", ...] },
    "Accounts_Receivable": { "hubs": ["customer", "customer_invoice", ...] }
  }
}
```

**The infrastructure already supports domain detection via schema** - QueryResolver just doesn't use it yet.

---

## Recommended Fixes

### Phase 1: Make QueryResolver Domain-Aware

1. **Add domain detection at query parse time**
```python
def _detect_query_domain(self, question: str) -> str:
    """Detect if question is about HCM, FINS, CRM, etc."""
    if any(term in question.lower() for term in EMPLOYEE_SYNONYMS):
        return 'HCM'
    if any(term in question.lower() for term in GL_SYNONYMS):
        return 'FINS_GL'
    if any(term in question.lower() for term in AP_SYNONYMS):
        return 'FINS_AP'
    # etc.
```

2. **Route to domain-specific snapshot generators**
```python
if domain == 'HCM':
    return self._generate_workforce_snapshot(...)
elif domain == 'FINS_GL':
    return self._generate_gl_snapshot(...)
elif domain == 'FINS_AP':
    return self._generate_ap_snapshot(...)
```

### Phase 2: Add FINS Snapshot Generators

```python
def _generate_gl_snapshot(self, project: str, table_name: str) -> Dict:
    """Generate GL snapshot: account counts, period status, balances."""
    return {
        'type': 'gl_snapshot',
        'yearly_snapshot': {
            2026: {
                'total_accounts': 1234,
                'active_accounts': 987,
                'periods_open': 2,
                'periods_closed': 10,
                'trial_balance': 0.00  # Should be zero if balanced
            }
        }
    }

def _generate_ap_snapshot(self, project: str, table_name: str) -> Dict:
    """Generate AP snapshot: open invoices, aging, vendor metrics."""
    return {
        'type': 'ap_snapshot',
        'current': {
            'open_invoices': 456,
            'total_outstanding': 1234567.89,
            'aging': {
                'current': 500000,
                '30_days': 300000,
                '60_days': 200000,
                '90_plus': 234567.89
            },
            'vendor_count': 234
        }
    }
```

### Phase 3: Update Consultative Templates

Add FINS-specific response templates that speak the language of accountants:
- "Your trial balance is **in balance** with 1,234 active accounts"
- "**$1.2M in open payables** - 19% is over 90 days (flagged for review)"
- "Period 12 is **still open** - 3 unposted journals pending approval"

---

## Files to Modify

| File | Change | Effort |
|------|--------|--------|
| `query_resolver.py` | Add domain detection, FINS snapshot generators | Medium |
| `project_intelligence.py` | Add FINS dimensional patterns, status mappings | Low |
| `consultative_templates.py` | Add FINS response formatters | Low |
| `DOMAIN_PATTERNS` | Add AP, AR, Inventory patterns | Low |

---

## What's Already Working for FINS

1. ✅ Product schemas exist (`workday_fins_schema_v1.json`, etc.)
2. ✅ GL domain pattern exists in `DOMAIN_PATTERNS`
3. ✅ Context Graph will discover FINS relationships automatically
4. ✅ Five Truths model works for any domain
5. ✅ Synthesis pipeline is domain-agnostic
6. ✅ LLM prompts are generic "consultant" prompts

---

## Hidden/Buried Features (May Not Be Visible in Frontend)

1. **Organizational Metrics** (`project_intelligence.py:1762`)
   - Pre-computes headcount, hub usage, coverage gaps
   - Runs on upload but results may not surface in UI

2. **Product Domain Mappings** (`products/registry.py`)
   - Full domain structure loaded from JSON
   - `get_domains(product_id)` available but may not be used in chat

3. **Table Classifications** (`project_intelligence.py`)
   - CONFIG vs TRANSACTION detection
   - Domain assignment per table
   - Stored in Supabase but may not surface in Data Model UI

4. **Entity Gaps** (`engine.py:1139`)
   - Detects configured-but-unused codes
   - Passed to synthesis but may not be prominently displayed

---

## Summary

| Component | Status | Notes |
|-----------|--------|-------|
| Context Graph | ✅ Generic | Works for any domain |
| Five Truths | ✅ Generic | Works for any domain |
| Product Registry | ✅ Generic | FINS schemas exist |
| Domain Patterns | ⚠️ Partial | GL exists, needs AP/AR/Inventory |
| QueryResolver | ❌ HCM-specific | Needs FINS snapshot generators |
| Consultative Templates | ❌ HCM-specific | Needs FINS formatters |
| Synthesis Pipeline | ✅ Generic | Works for any domain |

**Bottom line:** 80% of the infrastructure is domain-agnostic. The HCM-specific parts are concentrated in QueryResolver and consultative templates - both fixable with ~2-3 days of work to add FINS equivalents.
