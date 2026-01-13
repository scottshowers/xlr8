# Deel - Domain Model Extraction
**Date:** January 10, 2026  
**Vendor:** Deel  
**Source:** Deel website, G2 reviews, API documentation  
**Purpose:** Hub-and-spoke schema for XLR8 universal analysis engine

---

## Executive Summary

| Metric | Count |
|--------|-------|
| **Total Hubs** | 133 |
| **Core Hubs** | 53 |
| **Domains** | 25 |
| **Product Focus** | Global EOR/Contractor - 150+ countries |

**Key Insight:** Deel has **79 unique concepts** - the most differentiation we've seen. Almost entirely focused on global employment (EOR, contractor management, multi-currency payments, immigration, compliance). This is a fundamentally different architecture than traditional domestic HCM.

---

## Part 1: Deel Architecture

### Platform Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                          DEEL                                    │
│         Global Workforce Platform - "Hire Anywhere"              │
│              150+ Countries | 200+ Currencies                    │
└─────────────────────────────────────────────────────────────────┘
                              │
    ┌─────────────┬───────────┼───────────┬─────────────┐
    │             │           │           │             │
    ▼             ▼           ▼           ▼             ▼
┌────────┐  ┌─────────┐  ┌────────┐  ┌────────┐  ┌──────────┐
│  EOR   │  │CONTRACT-│  │ GLOBAL │  │IMMIGRA-│  │COMPLIANCE│
│        │  │   OR    │  │PAYROLL │  │  TION  │  │          │
├────────┤  ├─────────┤  ├────────┤  ├────────┤  ├──────────┤
│Owned   │  │Invoice  │  │120+    │  │Visa    │  │Labor Law │
│Entities│  │Milestone│  │Countries│ │Work    │  │Deel      │
│Contract│  │Shield   │  │Gross-Net│ │Permit  │  │Shield    │
│Benefits│  │Payment  │  │Currency │  │Relocate│  │Knowledge │
└────────┘  └─────────┘  └────────┘  └────────┘  └──────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
       ┌──────────┐    ┌──────────┐    ┌──────────┐
       │   PEO    │    │EQUIPMENT │    │ ENGAGE   │
       │   (US)   │    │          │    │          │
       │Co-employ │    │Laptop    │    │Perform   │
       └──────────┘    └──────────┘    └──────────┘
```

### Core Philosophy

Deel's fundamental model:
- **No entity required** - Hire globally without legal setup
- **Worker-type agnostic** - EOR, contractor, direct employee
- **Compliance-first** - Legal employer handles all liability
- **Global payments** - Any currency, any country

---

## Part 2: Key Differentiators

### EOR (Employer of Record)

**Deel becomes the legal employer:**
- Owned entities in 150+ countries
- Handles payroll, tax, benefits locally
- Compliance liability on Deel
- $599/month per employee

### Contractor Management (Origin Story)

**Original Deel product:**
- Contractor contracts and invoices
- Milestone-based payments
- Work scope management
- **Deel Shield** - Misclassification protection

### Global Payroll

**Single calculation engine:**
- 120+ countries
- 200+ currencies
- Gross-to-net in real-time
- Local payroll provider aggregation
- Off-cycle payments

### Immigration Support

**Visa and relocation:**
- Work visa applications
- Work permit management
- Employee relocation
- In-country support

### Payments

**Multi-currency flexibility:**
- Wire transfers
- Crypto payments
- Mass payments (bulk)
- 8+ payment methods
- Real-time exchange rates

---

## Part 3: Domain Structure

### EOR (5 hubs)
Employer of Record services - core differentiator.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| EOR_Employee | `eor_employee_id` | ✅ |
| EOR_Entity | `eor_entity_id` | ✅ |
| EOR_Contract | `eor_contract_id` | ✅ |
| Legal_Employer | `legal_employer_id` | |
| Country_Entity | `country_entity_id` | |

### Contractor_Management (7 hubs)
Original Deel product.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Contractor_Contract | `contractor_contract_id` | ✅ |
| Contractor_Invoice | `contractor_invoice_id` | ✅ |
| Contractor_Payment | `contractor_payment_id` | ✅ |
| Milestone | `milestone_id` | |
| Deliverable | `deliverable_id` | |
| Work_Scope | `work_scope_id` | |
| Deel_Shield | `deel_shield_id` | |

### Payroll (9 hubs)
Global payroll - 120+ countries.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Payroll | `payroll_id` | ✅ |
| Pay_Period | `pay_period_id` | ✅ |
| Paycheck | `paycheck_id` | ✅ |
| Global_Payroll | `global_payroll_id` | ✅ |
| Local_Payroll | `local_payroll_id` | |
| US_Payroll | `us_payroll_id` | |
| Off_Cycle_Payroll | `off_cycle_payroll_id` | |
| Gross_To_Net | `gross_to_net_id` | |
| Payroll_Provider | `payroll_provider_id` | |

### Payments (8 hubs)
Payment processing - 200+ currencies.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Payment | `payment_id` | ✅ |
| Payment_Method | `payment_method_id` | ✅ |
| Bank_Account | `bank_account_id` | ✅ |
| Wire_Transfer | `wire_transfer_id` | |
| Crypto_Payment | `crypto_payment_id` | |
| Mass_Payment | `mass_payment_id` | |
| Payment_Status | `payment_status_id` | |
| Exchange_Rate | `exchange_rate_id` | |

### Compliance (7 hubs)
Global compliance - core strength.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Compliance | `compliance_id` | ✅ |
| Labor_Law | `labor_law_id` | |
| Compliance_Alert | `compliance_alert_id` | |
| Misclassification | `misclassification_id` | |
| Compliance_Document | `compliance_document_id` | |
| Knowledge_Hub | `knowledge_hub_id` | |
| Country_Guide | `country_guide_id` | |

### Immigration (5 hubs)
Visa and immigration support.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Visa | `visa_id` | |
| Visa_Application | `visa_application_id` | |
| Work_Permit | `work_permit_id` | |
| Immigration_Support | `immigration_support_id` | |
| Relocation | `relocation_id` | |

---

## Part 4: Cross-Vendor Comparison

### Deel vs Traditional HCM

| Comparison | Shared Concepts |
|------------|-----------------|
| Deel + Rippling | 46 |
| Deel + Gusto | 42 |

### Deel-Unique Concepts (79) - HIGHEST COUNT

**EOR/Global Employment (Unmatched):**
- EOR_Employee, EOR_Entity, EOR_Contract
- Legal_Employer, Country_Entity
- Work_Country, Work_Permit

**Contractor (Unmatched):**
- Contractor_Contract, Contractor_Invoice
- Milestone, Deliverable, Work_Scope
- Deel_Shield (misclassification protection)

**Global Payroll:**
- Global_Payroll, Local_Payroll, US_Payroll
- Payroll_Provider, Gross_To_Net

**Payments:**
- Wire_Transfer, Crypto_Payment, Mass_Payment
- Exchange_Rate, Payment_Status, Currency

**Immigration:**
- Visa, Visa_Application, Work_Permit
- Immigration_Support, Relocation

**Compliance:**
- Labor_Law, Misclassification
- Knowledge_Hub, Country_Guide

**Tax (International):**
- W8, W9, VAT, Tax_Form, Tax_Document

---

## Part 5: XLR8 Integration

### Product Detection

Detect Deel via:

| Indicator | Pattern |
|-----------|---------|
| API URL | `api.deel.com/*` |
| Domain | `*.deel.com`, `app.deel.com` |
| Key fields | `worker_id`, `contract_id`, `eor_employee_id` |
| Features | Deel Shield, EOR, Global Payroll |

### Spoke Patterns

```
Company → Worker (Employee|Contractor|EOR)
Worker → Contract → Work_Country
EOR_Employee → EOR_Entity → Country_Entity
Contractor → Contractor_Contract → Contractor_Invoice
Worker → Payroll → Payment → Currency
Worker → Visa → Work_Permit
Worker → Equipment → Device
```

---

## Part 6: Pricing

| Service | Price |
|---------|-------|
| **Contractor** | $49/month |
| **EOR** | $599/month per employee |
| **Global Payroll** | Custom |
| **US Payroll** | Custom |
| **PEO** | Custom |

---

## Deliverables

| File | Description |
|------|-------------|
| `deel_schema_v1.json` | Full hub definitions (133 hubs) |
| `deel_comparison.json` | Cross-vendor overlap analysis |
| `DEEL_EXTRACTION.md` | This document |

---

## Updated HCM Product Summary

| Product | Hubs | Vendor | Focus |
|---------|------|--------|-------|
| Paycor | 174 | Paycor | HCM |
| Oracle HCM | 173 | Oracle | HCM |
| Paycom | 164 | Paycom | HCM |
| Rippling | 161 | Rippling | HCM |
| Workday HCM | 160 | Workday | HCM |
| Dayforce | 157 | Ceridian | HCM |
| Paylocity | 142 | Paylocity | HCM |
| ADP WFN | 138 | ADP | HCM |
| BambooHR | 138 | BambooHR | HCM |
| SuccessFactors | 137 | SAP | HCM |
| Gusto | 135 | Gusto | HCM |
| **Deel** | **133** | **Deel** | **Global/EOR** |
| HiBob | 131 | HiBob | HCM |
| isolved | 131 | isolved | HCM |
| Paychex Flex | 127 | Paychex | HCM |
| Namely | 126 | Namely | HCM |
| UKG WFM | 113 | UKG | WFM |
| UKG Pro | 105 | UKG | HCM |
| UKG Ready | 104 | UKG | HCM |
| **TOTAL** | **2,649** | **19 products** | |

---

## Summary

Deel brings **133 hubs** across 25 domains with a remarkable **79 unique concepts** - the highest differentiation of any vendor. This reflects Deel's positioning as the "anti-entity" global employment platform.

Key strengths:

1. **EOR** - Legal employment in 150+ countries without entity
2. **Contractor Management** - Original product, still best-in-class
3. **Deel Shield** - Misclassification liability protection
4. **Global Payroll** - Single calculation engine, 120+ countries
5. **Multi-Currency Payments** - 200+ currencies, crypto support
6. **Immigration** - Visa, work permits, relocation
7. **Equipment Management** - Ship laptops globally
8. **Compliance** - Labor law knowledge hub

Deel represents a fundamentally different HCM architecture: instead of managing employees within a company's legal structure, it provides the legal structure itself across 150+ countries.
