# Workday Financial Management (FINS) - Domain Model Extraction
**Date:** January 10, 2026  
**Vendor:** Workday  
**Source:** Workday docs, WWS API, datasheets, implementation guides  
**Purpose:** Hub-and-spoke schema for XLR8 universal analysis engine

---

## Executive Summary

| Metric | Count |
|--------|-------|
| **Total Hubs** | 136 |
| **Core Hubs** | 43 |
| **Domains** | 16 |
| **Product Focus** | Enterprise Financial Management - GL, AP, AR, Procurement, Projects, Grants |

**Key Insight:** Workday FINS uses a **Worktag-based Foundation Data Model (FDM)** where transactions are classified by dimensions (worktags) rather than traditional account strings.

---

## Part 1: Workday FINS Architecture

### Foundation Data Model (FDM)

Workday's unique approach uses **Worktags** as multi-dimensional attributes:

```
┌─────────────────────────────────────────────────────────────────┐
│                    FOUNDATION WORKTAGS                           │
│  Company, Cost Center, Fund, Program, Location, Business Unit   │
│              Spend Category, Revenue Category, Project          │
└─────────────────────────────────────────────────────────────────┘
                              │
           ┌──────────────────┴──────────────────┐
           │                                     │
           ▼                                     ▼
┌─────────────────────────┐       ┌─────────────────────────┐
│    GENERAL LEDGER       │       │   SUBLEDGERS            │
│                         │       │                         │
├─────────────────────────┤       ├─────────────────────────┤
│ Ledger Account          │◄──────│ Accounts Payable        │
│ Journal Entry           │       │ Accounts Receivable     │
│ Fiscal Period           │       │ Fixed Assets            │
│ Trial Balance           │       │ Projects                │
│                         │       │ Grants                  │
└─────────────────────────┘       └─────────────────────────┘
```

### Account Posting Rules

Unlike traditional ERPs, Workday derives ledger accounts from worktags:

```
Transaction + Worktags → Account Posting Rule → Ledger Account + Journal
```

Example:
- Spend Category: "Office Supplies" 
- → Account Posting Rule maps to → Ledger Account: 6100 (Supplies Expense)

### API Structure

**WWS SOAP API:**
```
https://{tenant}.workday.com/ccx/service/{tenant}/Financial_Management/v45
```

**REST API:**
```
https://{tenant}.workday.com/ccx/api/v1/{tenant}/financials
```

---

## Part 2: Domain Structure

### General_Ledger (10 hubs)
Core accounting and general ledger.

| Hub | Semantic Type | Core | Description |
|-----|---------------|------|-------------|
| Ledger_Account | `ledger_account_id` | ✅ | Chart of accounts entry |
| Journal_Entry | `journal_entry_id` | ✅ | Accounting journal |
| Journal_Line | `journal_line_id` | | Journal line item |
| Fiscal_Year | `fiscal_year_id` | ✅ | Fiscal year definition |
| Fiscal_Period | `fiscal_period_id` | ✅ | Accounting period |
| Ledger | `ledger_id` | ✅ | Book type (primary, secondary) |
| Account_Posting_Rule | `account_posting_rule_id` | | Worktag to account mapping |
| Intercompany_Profile | `intercompany_profile_id` | | Intercompany accounting |

### Foundation_Worktags (11 hubs)
Foundation Data Model - Worktags/dimensions.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Company | `company_id` | ✅ |
| Cost_Center | `cost_center_id` | ✅ |
| Fund | `fund_id` | ✅ |
| Program | `program_id` | |
| Business_Unit | `business_unit_id` | ✅ |
| Location | `location_id` | ✅ |
| Region | `region_id` | |
| Spend_Category | `spend_category_id` | ✅ |
| Revenue_Category | `revenue_category_id` | ✅ |
| Object_Class | `object_class_id` | |
| Custom_Worktag | `custom_worktag_id` | |

### Accounts_Payable (11 hubs)
Supplier management and payables.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Supplier | `supplier_id` | ✅ |
| Supplier_Invoice | `supplier_invoice_id` | ✅ |
| Supplier_Invoice_Line | `supplier_invoice_line_id` | |
| Supplier_Contract | `supplier_contract_id` | ✅ |
| Supplier_Payment | `supplier_payment_id` | ✅ |
| Payment_Election | `payment_election_id` | |
| Payment_Run | `payment_run_id` | |
| Settlement_Run | `settlement_run_id` | |
| Recurring_Supplier_Invoice | `recurring_supplier_invoice_id` | |

### Accounts_Receivable (11 hubs)
Customer management and receivables.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Customer | `customer_id` | ✅ |
| Customer_Invoice | `customer_invoice_id` | ✅ |
| Customer_Contract | `customer_contract_id` | ✅ |
| Customer_Payment | `customer_payment_id` | ✅ |
| Customer_Deposit | `customer_deposit_id` | |
| Credit_Memo | `credit_memo_id` | |
| Debit_Memo | `debit_memo_id` | |
| Dunning_Letter | `dunning_letter_id` | |
| Collections_Case | `collections_case_id` | |

### Procurement (11 hubs)
Purchasing and spend management.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Requisition | `requisition_id` | ✅ |
| Purchase_Order | `purchase_order_id` | ✅ |
| Purchase_Order_Line | `purchase_order_line_id` | |
| Purchase_Item | `purchase_item_id` | ✅ |
| Receipt | `receipt_id` | ✅ |
| Supplier_Catalog | `supplier_catalog_id` | |
| Catalog_Item | `catalog_item_id` | |
| Punchout_Supplier | `punchout_supplier_id` | |

### Additional Domains

**Cash_Management (10 hubs):** Bank ✅, Bank_Account ✅, Bank_Statement ✅, Bank_Statement_Line, Bank_Transaction, Cash_Position, Payment_Type, Bank_Reconciliation, Ad_Hoc_Payment, Wire_Transfer

**Business_Assets (10 hubs):** Business_Asset ✅, Asset_Book ✅, Depreciation_Schedule, Depreciation_Profile, Asset_Category, Asset_Disposal, Asset_Transfer, Inventory_Item, Inventory_Location, Stock_Request

**Revenue_Management (8 hubs):** Revenue_Schedule ✅, Revenue_Recognition ✅, Billing_Schedule ✅, Billing_Event, Sales_Item ✅, Price_List, Contract_Line, Revenue_Arrangement

**Projects (9 hubs):** Project ✅, Project_Task, Project_Phase, Project_Plan, Resource_Assignment, Project_Billing, Time_Entry ✅, Project_Cost, Capital_Project

**Grants_Management (8 hubs):** Grant ✅, Award ✅, Sponsor ✅, Grant_Budget, Grant_Billing, Letter_of_Credit, Facilities_Admin_Rate, Gift

**Budgeting (7 hubs):** Budget ✅, Budget_Structure, Budget_Amendment, Position_Budget, Budget_Check_Override, Commitment, Obligation

**Expenses (7 hubs):** Expense_Report ✅, Expense_Item, Expense_Category ✅, Spend_Authorization, Per_Diem, Mileage_Rate, Corporate_Card_Transaction

**Tax_Management (6 hubs):** Tax_Code ✅, Tax_Category, Tax_Authority, Withholding_Tax, Tax_Applicability, Form_1099

---

## Part 3: Workday Platform Integration (HCM + FINS)

### Shared Foundation Worktags

| Worktag | HCM Use | FINS Use |
|---------|---------|----------|
| **Company** | Legal employer | Legal entity for accounting |
| **Cost_Center** | Worker org assignment | Expense allocation |
| **Location** | Work location | Business location |
| **Business_Unit** | Org hierarchy | P&L responsibility |
| **Region** | Geographic grouping | Regional reporting |

### Integration Points

```
┌────────────────────┐                    ┌────────────────────┐
│   WORKDAY HCM      │                    │   WORKDAY FINS     │
│   (160 hubs)       │                    │   (136 hubs)       │
├────────────────────┤                    ├────────────────────┤
│ Worker             │────────────────────│ Expense Report     │
│ Position           │────────────────────│ Position Budget    │
│ Compensation       │────────────────────│ Payroll Costing    │
│ Time Entry         │════════════════════│ Time Entry         │
│ Pay Group          │────────────────────│ Settlement Run     │
└────────────────────┘                    └────────────────────┘
        │                                         │
        └──────────────┬──────────────────────────┘
                       ▼
        ┌──────────────────────────────────────────┐
        │         SHARED WORKTAGS                   │
        │  Company, Cost Center, Location, Region  │
        │  Business Unit, Security Group           │
        └──────────────────────────────────────────┘
```

### Combined Platform Metrics

| Metric | Value |
|--------|-------|
| Workday HCM Hubs | 160 |
| Workday FINS Hubs | 136 |
| Combined Total | 296 |
| Shared Concepts | 12 |
| Unique Concepts | 284 |

---

## Part 4: XLR8 Integration

### Product Detection

Detect Workday FINS via:

| Indicator | Pattern |
|-----------|---------|
| API URL | `*/Financial_Management/*` or `*/financials/*` |
| Worktag entities | `Spend_Category`, `Revenue_Category`, `Fund` |
| Financial entities | `Supplier_Invoice`, `Customer_Invoice`, `Journal_Entry` |
| Composite keys | `{company}_{fiscal_year}_{fiscal_period}` |

### Spoke Patterns

```
Journal_Entry → Journal_Line (has lines)
Supplier_Invoice → Supplier (from vendor)
Supplier_Invoice → Supplier_Invoice_Line (has lines)
Supplier_Invoice_Line → Spend_Category (classified as)
Supplier_Invoice_Line → Cost_Center (charged to)
Purchase_Order → Requisition (fulfills)
Receipt → Purchase_Order (receives)
Customer_Invoice → Customer (billed to)
Project → Time_Entry (tracks time)
Grant → Award (funded by)
Business_Asset → Asset_Book (depreciated in)
```

### Column Patterns

| Pattern | Hub |
|---------|-----|
| company_*, company_id | company |
| cost_center_*, cc_* | cost_center |
| supplier_*, vendor_* | supplier |
| customer_*, cust_* | customer |
| spend_category_*, expense_type | spend_category |
| revenue_category_*, rev_cat | revenue_category |
| ledger_account_*, gl_account | ledger_account |
| project_*, proj_* | project |
| grant_*, award_* | grant |
| fund_*, fund_code | fund |

---

## Part 5: Key Workday FINS Concepts

### Worktag-Driven Accounting

**Traditional ERP:**
```
User selects: Account 6100-100-5000
              (Expense-Dept-Project)
```

**Workday:**
```
User selects: Spend Category = Office Supplies
              Cost Center = Marketing
              Project = Website Redesign
              
System derives: Account 6100 (from posting rules)
```

### Continuous Accounting

Workday provides real-time accounting:
- Transactions post immediately upon approval
- No batch processing required
- Intercompany entries generated automatically
- Multi-book support (GAAP, IFRS, statutory)

### Key Differentiators

1. **Worktag-based FDM** - Dimensions instead of account strings
2. **Account Posting Rules** - System-derived GL accounts
3. **Continuous Accounting** - Real-time posting
4. **Unified Platform** - Shared data with HCM
5. **Multi-book Support** - GAAP, IFRS, local GAAP
6. **In-Memory Architecture** - Fast reporting

---

## Deliverables

| File | Description |
|------|-------------|
| `workday_fins_schema_v1.json` | Full hub definitions (136 hubs) |
| `workday_platform_comparison.json` | HCM vs FINS integration points |
| `WORKDAY_FINS_EXTRACTION.md` | This document |

---

## Financial System Comparison

| System | Hubs | Focus | Architecture |
|--------|------|-------|--------------|
| **Workday FINS** | **136** | Cloud ERP | Worktag-based FDM |
| Oracle Fusion FINS | ~150* | Cloud ERP | Flexfield-based |
| SAP S/4HANA FINS | ~180* | Cloud/On-prem | Account-based |
| NetSuite | ~100* | Cloud ERP | Subsidiary-based |

*Estimated - not yet extracted

---

## Summary

Workday Financial Management brings **136 hubs** across 16 financial domains, with a unique worktag-based architecture that:

1. **Simplifies user experience** - Users select categories, not accounts
2. **Enables rich analytics** - Multi-dimensional reporting built-in
3. **Integrates with HCM** - Shared foundation data model
4. **Supports global operations** - Multi-book, multi-currency native

Combined with Workday HCM (160 hubs), the complete Workday platform provides **284 unique concepts** for enterprise HR and Finance management.
