# Rippling - Domain Model Extraction
**Date:** January 10, 2026  
**Vendor:** Rippling  
**Source:** Rippling website, API documentation, developer portal  
**Purpose:** Hub-and-spoke schema for XLR8 universal analysis engine

---

## Executive Summary

| Metric | Count |
|--------|-------|
| **Total Hubs** | 161 |
| **Core Hubs** | 67 |
| **Domains** | 26 |
| **Product Focus** | Unified HR + IT + Finance platform |

**Key Insight:** Rippling is **unique** in combining HR, IT, and Finance in a single platform with the Employee Graph as a unified data source. The IT management capabilities (device, app, identity) are unmatched by traditional HCM vendors. This creates 54 unique concepts not found in other payroll-focused systems.

---

## Part 1: Rippling Architecture

### Platform Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    EMPLOYEE GRAPH                                │
│            Single Source of Truth for All Data                   │
└─────────────────────────────────────────────────────────────────┘
                              │
    ┌─────────────┬───────────┼───────────┬─────────────┐
    │             │           │           │             │
    ▼             ▼           ▼           ▼             ▼
┌────────┐  ┌─────────┐  ┌────────┐  ┌────────┐  ┌──────────┐
│RIPPLING│  │RIPPLING │  │RIPPLING│  │RIPPLING│  │ PLATFORM │
│  HCM   │  │   IT    │  │ SPEND  │  │ GLOBAL │  │          │
├────────┤  ├─────────┤  ├────────┤  ├────────┤  ├──────────┤
│Payroll │  │Device   │  │Cards   │  │EOR     │  │Workflow  │
│Benefits│  │Identity │  │Expense │  │Payroll │  │Analytics │
│Talent  │  │Apps/SSO │  │AP      │  │Comply  │  │App Studio│
│Time    │  │MDM      │  │Travel  │  │        │  │Policies  │
└────────┘  └─────────┘  └────────┘  └────────┘  └──────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
       ┌──────────────┐               ┌──────────────┐
       │  ONBOARDING  │               │ OFFBOARDING  │
       │  Auto-setup  │               │ Auto-revoke  │
       │  devices,    │               │  devices,    │
       │  apps, access│               │  apps, access│
       └──────────────┘               └──────────────┘
```

### API Structure

**Base URL:**
```
https://rest.ripplingapis.com
```

**Authentication:** OAuth 2.0 or API Token

**Key Endpoints:**
- `/users` - User/employee records
- `/workers` - Worker records
- `/companies` - Company info
- `/employees` - Employee data

**Pagination:** Cursor-based with `next_link`

---

## Part 2: Key Differentiators

### Employee Graph

Single source of truth unifying:
- HR data (employee, job, compensation)
- Device data (laptops, phones)
- App data (SaaS accounts)
- Access data (permissions, SSO)
- Finance data (expenses, cards)

### Unified HR + IT

What makes Rippling unique:
- Onboard employee → Device ships automatically
- Role change → App permissions update automatically
- Offboard → All access revoked automatically
- No separate IT tickets for HR events

### Identity & Access Management

IT features built into HR:
- Single Sign-On (SSO) included
- App provisioning/deprovisioning
- Multi-factor authentication (MFA)
- SAML integration
- Permission management via Supergroups

### Device Management (MDM)

Full MDM integrated with HR:
- Device enrollment and setup
- Remote device wipe
- OS update enforcement
- Device encryption
- Endpoint security
- Device shipping logistics

### Workflow Studio

Advanced automation:
- Trigger workflows on any data
- Course completions
- Survey responses
- Role changes
- Policy violations

### App Studio

No-code app builder:
- Build custom apps
- Distribute on App Shop
- Extend platform capabilities

---

## Part 3: Domain Structure

### Employee_Core (9 hubs)
Core employee information via Employee Graph.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| User | `user_id` | ✅ |
| Worker | `worker_id` | ✅ |
| Person | `person_id` | ✅ |
| SSN | `ssn_id` | ✅ |
| Employee_Graph | `employee_graph_id` | |

### Identity_Access (9 hubs)
Identity and access management (IT).

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Identity | `identity_id` | ✅ |
| SSO | `sso_id` | ✅ |
| MFA | `mfa_id` | |
| App_Access | `app_access_id` | ✅ |
| App_Provisioning | `app_provisioning_id` | ✅ |
| App_Deprovisioning | `app_deprovisioning_id` | |
| Permission | `permission_id` | ✅ |
| Access_Control | `access_control_id` | |
| SAML | `saml_id` | |

### Device_Management (9 hubs)
Mobile device management (MDM/IT).

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Device | `device_id` | ✅ |
| Device_Enrollment | `device_enrollment_id` | ✅ |
| Device_Policy | `device_policy_id` | |
| Device_Inventory | `device_inventory_id` | |
| Device_Shipping | `device_shipping_id` | |
| Device_Wipe | `device_wipe_id` | |
| Endpoint_Security | `endpoint_security_id` | |
| OS_Update | `os_update_id` | |
| Encryption | `encryption_id` | |

### Offboarding (4 hubs)
Employee offboarding automation.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Offboarding | `offboarding_id` | ✅ |
| Exit_Interview | `exit_interview_id` | |
| Asset_Return | `asset_return_id` | |
| Access_Revocation | `access_revocation_id` | |

### Additional Domains

**Employment (9 hubs):** Employment ✅, Job ✅, Job_Title ✅, Hire_Date ✅, Termination_Date, Employment_Status ✅, Worker_Type ✅, FLSA_Status, Role ✅

**Organization (9 hubs):** Company ✅, Department ✅, Team, Location ✅, Office, Cost_Center, Supervisor ✅, Org_Chart, Supergroup

**Payroll (6 hubs):** Payroll ✅, Pay_Period ✅, Paycheck ✅, Direct_Deposit ✅, Payroll_Run, Off_Cycle_Payroll

**Tax (8 hubs):** Tax ✅, Tax_Filing ✅, Federal_Tax ✅, State_Tax ✅, Local_Tax, W4, W2, Form_1099

**Benefits (10 hubs):** Benefit ✅, Benefit_Plan ✅, Benefit_Enrollment ✅, Open_Enrollment, Dependent ✅, Carrier, COBRA, ACA, Qualifying_Life_Event, Summary_Plan_Description

**Recruiting (7 hubs):** Job_Posting ✅, Candidate ✅, Application ✅, Applicant_Tracking ✅, Interview, Offer, Background_Check

**Finance (6 hubs):** Expense ✅, Expense_Report, Corporate_Card, Accounts_Payable, Bill_Pay, Travel

**Global (4 hubs):** Global_Payroll, Employer_Of_Record, International_Employee, Country_Compliance

**Compliance (7 hubs):** Compliance, Compliance_Alert, EEO, Audit_Trail, SOC2, Policy ✅, Policy_Enforcement

**Platform (10 hubs):** Workflow_Studio, Workflow ✅, App_Studio, Analytics, Custom_Field, News_Feed, Integration, API, Webhook, App_Shop

---

## Part 4: Cross-Vendor Comparison

### Rippling Overlap with Other HCM Systems

| Comparison | Shared Concepts |
|------------|-----------------|
| Rippling + Paycor | **91** |
| Rippling + Gusto | 89 |
| Rippling + Paycom | 84 |

### Rippling-Unique Concepts (54)

Concepts unique to Rippling include:

**IT/Identity (Unmatched):**
- SSO, MFA, SAML
- Identity, Permission, Access_Control
- App_Access, App_Provisioning, App_Deprovisioning
- Supergroup (dynamic permission groups)

**Device Management (Unmatched):**
- Device, Device_Enrollment, Device_Inventory
- Device_Policy, Device_Shipping, Device_Wipe
- Endpoint_Security, Encryption, OS_Update

**Finance (Unique):**
- Corporate_Card
- Accounts_Payable
- Bill_Pay
- Travel

**Platform:**
- Employee_Graph
- Workflow_Studio, Workflow
- App_Studio, App_Shop
- Analytics
- Policy, Policy_Enforcement
- News_Feed

**Lifecycle:**
- Offboarding (dedicated domain)
- Access_Revocation
- Asset_Return
- Exit_Interview

---

## Part 5: XLR8 Integration

### Product Detection

Detect Rippling via:

| Indicator | Pattern |
|-----------|---------|
| API URL | `rest.ripplingapis.com/*` |
| Key fields | `user_id`, `worker_id`, `device_id`, `sso_id` |
| Pagination | `cursor`, `next_link` |
| IT concepts | Device, App provisioning fields |

### Spoke Patterns

```
Company → User/Worker → Employment → Job/Role
User → Device → Device_Policy
User → App_Access → App_Provisioning
User → Identity → SSO/Permission
User → Paycheck → Earning/Deduction
User → Benefit → Benefit_Plan/Dependent
User → Expense → Corporate_Card
Candidate → Application → Job_Posting
User → Onboarding → Onboarding_Workflow
User → Offboarding → Access_Revocation/Asset_Return
```

### Column Patterns

| Pattern | Hub |
|---------|-----|
| user_id, userid | user |
| worker_id, workerid | worker |
| device_id, deviceid | device |
| role_id, roleid | role |
| sso_id, ssoid | sso |
| app_id, appid | app_access |

---

## Part 6: Product Lines

### Rippling HCM
- HR Core (HRIS)
- Payroll
- Benefits Administration
- Talent Management
- Time & Attendance
- Workforce Management
- Learning Management

### Rippling IT
- Identity & Access Management
- Device Management (MDM)
- App Management
- SSO & MFA
- Endpoint Security

### Rippling Spend
- Corporate Cards
- Expense Management
- Accounts Payable
- Bill Pay
- Travel Management

### Rippling Global
- Global Payroll
- Employer of Record (EOR)
- International Compliance

---

## Deliverables

| File | Description |
|------|-------------|
| `rippling_schema_v1.json` | Full hub definitions (161 hubs) |
| `rippling_comparison.json` | Cross-vendor overlap analysis |
| `RIPPLING_EXTRACTION.md` | This document |

---

## Updated HCM Product Summary

| Product | Hubs | Vendor |
|---------|------|--------|
| Paycor | 174 | Paycor |
| Oracle HCM | 173 | Oracle |
| Paycom | 164 | Paycom |
| **Rippling** | **161** | **Rippling** |
| Workday HCM | 160 | Workday |
| Dayforce | 157 | Ceridian |
| Paylocity | 142 | Paylocity |
| ADP WFN | 138 | ADP |
| SuccessFactors | 137 | SAP |
| Gusto | 135 | Gusto |
| Paychex Flex | 127 | Paychex |
| UKG WFM | 113 | UKG |
| UKG Pro | 105 | UKG |
| UKG Ready | 104 | UKG |
| **TOTAL** | **1,990** | **14 products** |

---

## Summary

Rippling brings **161 hubs** across 26 domains - with **54 unique concepts** not found in any other extracted product. This reflects its unique positioning as a unified HR + IT + Finance platform.

Key strengths:

1. **Employee Graph** - Single source of truth across all systems
2. **IT Integration** - Device management, app provisioning, identity/access
3. **Workflow Studio** - Advanced automation on any data
4. **Unified Platform** - HR, IT, Finance in one system
5. **Lifecycle Automation** - Onboarding/offboarding with auto device/app setup

Rippling's overlap with traditional HCM vendors (84-91 shared concepts) reflects its solid HR foundation, but the IT and Finance domains set it apart. No other vendor has device management, app provisioning, or corporate cards integrated with HR.
