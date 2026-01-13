# Finance & ERP Domain Model Extraction
**Date:** January 10, 2026  
**Session Focus:** Core enterprise finance and ERP systems  

---

## Executive Summary

| Product | Vendor | Hubs | Market Tier | Focus |
|---------|--------|------|-------------|-------|
| **Workday Financials** | Workday | 136 | Enterprise | Cloud financials + planning |
| **Oracle NetSuite** | Oracle | 141 | Mid-Market | Unified ERP leader |
| **SAP S/4HANA** | SAP | 138 | Enterprise | On-prem/cloud ERP |
| **Dynamics 365 F&SCM** | Microsoft | 128 | Enterprise | Azure-native ERP |
| **Sage Intacct** | Sage | 85 | Mid-Market | Cloud financials (AICPA) |
| **Xero** | Xero | 50 | SMB | Global accounting |
| **QuickBooks Online** | Intuit | 49 | SMB | US accounting leader |
| **TOTAL** | | **727** | | |

---

## Market Segmentation

### Enterprise ERP (128-141 hubs)
| Product | Hubs | Key Differentiator |
|---------|------|-------------------|
| Workday Financials | 136 | Cloud-native, unified HCM+FIN |
| SAP S/4HANA | 138 | HANA in-memory, industry depth |
| Dynamics 365 | 128 | Azure/Power Platform ecosystem |

### Mid-Market ERP (85-141 hubs)
| Product | Hubs | Key Differentiator |
|---------|------|-------------------|
| NetSuite | 141 | First cloud ERP, OneWorld multi-entity |
| Sage Intacct | 85 | AICPA preferred, dimension-based |

### SMB Accounting (49-50 hubs)
| Product | Hubs | Key Differentiator |
|---------|------|-------------------|
| Xero | 50 | Global, beautiful UX, UK/AU payroll |
| QuickBooks Online | 49 | US market leader, 7M+ customers |

---

## Cross-Platform Coverage Analysis

### Core Finance Domains (Present in ALL platforms)
- General Ledger / Chart of Accounts
- Accounts Payable
- Accounts Receivable
- Banking / Cash Management
- Tax Management

### Mid-Market+ Domains (NetSuite, Intacct, Enterprise)
- Fixed Assets / Depreciation
- Multi-entity Consolidation
- Budgeting & Planning
- Revenue Recognition (ASC 606)
- Project Accounting

### Enterprise-Only Domains (S/4HANA, D365, Workday)
- Manufacturing / Production Planning
- Warehouse Management (WMS)
- Transportation Management
- Quality Management
- Cost Accounting / Controlling

---

## API Architecture Comparison

| Product | API Type | Authentication |
|---------|----------|---------------|
| Workday | REST/SOAP | OAuth 2.0 |
| NetSuite | REST/SOAP (SuiteTalk) | Token-based |
| SAP S/4HANA | OData REST | OAuth 2.0 |
| Dynamics 365 | OData REST | Azure AD |
| Sage Intacct | XML/REST | Sender credentials |
| Xero | REST | OAuth 2.0 |
| QuickBooks | REST | OAuth 2.0 |

---

## Key Detection Patterns

### SAP S/4HANA
- Look for: Company Code, Cost Center, Profit Center, Material Document
- FICO terminology: FI-GL, FI-AP, FI-AR, CO-PA

### NetSuite
- Look for: Subsidiary, Saved Search, SuiteScript, Custom Record
- OneWorld for multi-entity

### Dynamics 365
- Look for: Legal Entity, Financial Dimension, Data Entity
- Power Platform extensions

### Sage Intacct
- Look for: Dimension (Location, Department, Class), Entity
- XML API patterns

### QuickBooks/Xero
- Look for: Class (QBO), Tracking Category (Xero)
- Simpler entity structure

---

## Deliverables

| File | Description |
|------|-------------|
| `workday_fins_schema_v1.json` | Workday Financials (155 hubs) |
| `netsuite_schema_v1.json` | Oracle NetSuite (141 hubs) |
| `s4hana_schema_v1.json` | SAP S/4HANA (138 hubs) |
| `dynamics365_schema_v1.json` | Microsoft Dynamics 365 (128 hubs) |
| `sage_intacct_schema_v1.json` | Sage Intacct (85 hubs) |
| `xero_schema_v1.json` | Xero (50 hubs) |
| `quickbooks_schema_v1.json` | QuickBooks Online (49 hubs) |
| `FINS_ERP_EXTRACTION.md` | This summary document |

---

## Running Totals

### HCM Products: 23 products | 3,020 hubs
### Finance/ERP Products: 7 products | 727 hubs
### **GRAND TOTAL: 30 products | 3,747 hubs**

