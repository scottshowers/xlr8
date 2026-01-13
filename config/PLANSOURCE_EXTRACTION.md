# PlanSource - Domain Model Extraction
**Date:** January 10, 2026  
**Vendor:** PlanSource  
**Source:** PlanSource website, developer docs, partner info  

---

## Executive Summary

| Metric | Count |
|--------|-------|
| **Total Hubs** | 121 |
| **Core Hubs** | 36 |
| **Domains** | 24 |
| **Product Focus** | Benefits Administration Specialist - 5M+ consumers |

**Key Insight:** PlanSource is a **pure-play benefits administration** platform that white-labels to HCM vendors. **UKG Ben Admin (Prime) is powered by PlanSource.** This is critical for product detection - if you see PlanSource data structures in a UKG context, it's Ben Admin Prime.

---

## White-Label Relationships

### Critical Intel

| Brand Name | Powered By |
|------------|------------|
| **UKG Ben Admin (Prime)** | PlanSource |
| SAP SuccessFactors Benefits | PlanSource integration |
| Various HCM resellers | PlanSource white-label |

**Detection Implication:** When analyzing a UKG customer's benefits data:
- If you see PlanSource API patterns → UKG Ben Admin Prime
- If you see native UKG patterns → UKG Ready/Pro native benefits

---

## Key Differentiators

1. **Benefits-Only Specialist** - Not full HCM, partners with HCM vendors
2. **Boost Program** - 18+ carrier API integrations (Guardian, UnitedHealthcare, etc.)
3. **EOI Automation** - Real-time Evidence of Insurability with carrier APIs
4. **IQ Suite** - Decision support, dependent verification, analytics
5. **AI Assistant** - ChatGPT-powered benefits chatbot
6. **The Source** - Employee engagement hub
7. **Self-Billing** - Generate carrier invoices automatically

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        PLANSOURCE                                │
│              Benefits Administration Specialist                  │
│                    5+ Million Consumers                          │
└─────────────────────────────────────────────────────────────────┘
                              │
    ┌─────────────┬───────────┼───────────┬─────────────┐
    │             │           │           │             │
    ▼             ▼           ▼           ▼             ▼
┌────────┐  ┌─────────┐  ┌────────┐  ┌────────┐  ┌──────────┐
│SHOPPING│  │ENROLLMT │  │ BOOST  │  │BILLING │  │   ACA    │
│        │  │         │  │        │  │        │  │          │
├────────┤  ├─────────┤  ├────────┤  ├────────┤  ├──────────┤
│Compare │  │Open Enr │  │Carrier │  │Self-   │  │1095-C    │
│Decide  │  │QLE      │  │API     │  │Billing │  │Tracking  │
│Recommend│ │New Hire │  │EOI     │  │Recon   │  │ALE       │
└────────┘  └─────────┘  └────────┘  └────────┘  └──────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
       ┌──────────┐    ┌──────────┐    ┌──────────┐
       │   HCM    │    │ PAYROLL  │    │ CARRIER  │
       │  SYNC    │    │  SYNC    │    │  FEEDS   │
       │(UKG/SAP) │    │Deductions│    │EDI/API   │
       └──────────┘    └──────────┘    └──────────┘
```

---

## Domain Highlights

### Benefits Shopping (6 hubs)
Decision support, plan comparison, AI recommendations, cost calculator

### EOI - Evidence of Insurability (7 hubs)
Real-time EOI submission and decision via carrier APIs - eliminates paper process

### Billing (6 hubs)
Self-billing generation, reconciliation, premium remittance

### Payroll Deduction (6 hubs)
API sync with HCM/Payroll - deduction codes, pre/post tax, imputed income

### Consumer-Directed (7 hubs)
HSA, FSA, HRA, DCFSA, Limited FSA administration

---

## API Structure

**Base URL:** `https://developer.plansource.com`

**Key Endpoints:**
- `/employees` - Employee demographics (sync from HCM)
- `/dependents` - Dependent management
- `/beneficiaries` - Beneficiary designations
- `/coverages` - Coverage elections
- `/payroll-deductions` - Deduction sync
- `/administrators` - Admin user management

**Boost APIs (Carrier Integrations):**
- Plan Configuration API
- Enrollment API
- EOI Submission/Decision API
- Member Portal SSO

---

## UKG Ben Admin Prime Detection

When analyzing UKG customer data, detect PlanSource via:

| Indicator | Pattern |
|-----------|---------|
| API domain | `plansource.com`, `developer.plansource.com` |
| Key entities | `coverage_id`, `eoi_id`, `carrier_feed_id` |
| Features | Boost, IQ Suite, The Source |
| Field patterns | `guaranteed_issue`, `eoi_decision`, `self_billing` |

**If PlanSource patterns detected in UKG context → UKG Ben Admin Prime**

---

## Services

| Service | Description |
|---------|-------------|
| Benefits Outsourcing | Full administration |
| Employee Contact Center | Call center support |
| Billing Reconciliation | Carrier invoice matching |
| COBRA Administration | COBRA compliance |
| HSA/FSA/HRA | Account administration |
| Dependent Verification | Dependent audit |
| ACA Add-On | ACA compliance |

---

## Deliverables

| File | Description |
|------|-------------|
| `plansource_schema_v1.json` | Full hub definitions (121 hubs) |
| `PLANSOURCE_EXTRACTION.md` | This document |

---

## Updated Product Summary

| Product | Hubs | Type |
|---------|------|------|
| Paycor | 174 | HCM |
| Oracle HCM | 173 | HCM |
| Paycom | 164 | HCM |
| Rippling | 161 | HCM |
| Workday HCM | 160 | HCM |
| Dayforce | 157 | HCM |
| Paylocity | 142 | HCM |
| ADP WFN | 138 | HCM |
| BambooHR | 138 | HCM |
| SuccessFactors | 137 | HCM |
| Gusto | 135 | HCM |
| Deel | 133 | Global/EOR |
| HiBob | 131 | HCM |
| isolved | 131 | HCM |
| Paychex Flex | 127 | HCM |
| Namely | 126 | HCM |
| **PlanSource** | **121** | **Benefits Admin** |
| **Zenefits** | **120** | **HCM** |
| UKG WFM | 113 | WFM |
| UKG Pro | 105 | HCM |
| UKG Ready | 104 | HCM |
| **TOTAL** | **2,890** | **21 products** |
