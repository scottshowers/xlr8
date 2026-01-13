# Gusto - Domain Model Extraction
**Date:** January 10, 2026  
**Vendor:** Gusto  
**Source:** Gusto website, API documentation, developer portal  
**Purpose:** Hub-and-spoke schema for XLR8 universal analysis engine

---

## Executive Summary

| Metric | Count |
|--------|-------|
| **Total Hubs** | 135 |
| **Core Hubs** | 52 |
| **Domains** | 23 |
| **Product Focus** | SMB Modern Payroll - 2-150 employees |

**Key Insight:** Gusto is the **modern SMB payroll leader** challenging ADP and Paychex in the small business space. Key differentiators include AutoPilot payroll, Embedded Payroll API for developers, Gusto Global EOR for international, and software provisioning during onboarding.

---

## Part 1: Gusto Architecture

### Platform Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    GUSTO HCM PLATFORM                            │
│            Modern Payroll + HR for SMBs                          │
└─────────────────────────────────────────────────────────────────┘
                              │
    ┌─────────────┬───────────┼───────────┬─────────────┐
    │             │           │           │             │
    ▼             ▼           ▼           ▼             ▼
┌────────┐  ┌─────────┐  ┌────────┐  ┌────────┐  ┌──────────┐
│PAYROLL │  │BENEFITS │  │HIRING  │  │TIME    │  │  HR      │
│        │  │         │  │& ONBRD │  │& PTO   │  │          │
├────────┤  ├─────────┤  ├────────┤  ├────────┤  ├──────────┤
│AutoPilt│  │Health   │  │ATS     │  │Clock   │  │Profiles  │
│Tax File│  │Dental   │  │Offer   │  │Track   │  │Directory │
│1099/W2 │  │Vision   │  │Chklist │  │PTO Bal │  │Compliance│
│Credits │  │401k/FSA │  │SoftProv│  │Holiday │  │Reports   │
└────────┘  └─────────┘  └────────┘  └────────┘  └──────────┘
                              │
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
     ┌──────────┐      ┌──────────┐      ┌──────────┐
     │EMBEDDED  │      │ GUSTO    │      │CONTRACTOR│
     │PAYROLL   │      │ GLOBAL   │      │ PAYMENTS │
     │API       │      │ (EOR)    │      │ (1099)   │
     └──────────┘      └──────────┘      └──────────┘
```

### API Structure

**Base URL:**
```
https://api.gusto.com/v1
```

**Demo Environment:**
```
https://api.gusto-demo.com/v1
```

**Authentication:** OAuth 2.0 (Authorization Code + Client Credentials)

**Key Endpoints:**
- `/companies/{company_id}` - Company info
- `/companies/{company_id}/employees` - Employees
- `/companies/{company_id}/payrolls` - Payroll runs
- `/employees/{employee_id}` - Single employee
- `/jobs/{job_id}/compensations` - Compensation

---

## Part 2: Key Differentiators

### AutoPilot Payroll

Fully automated payroll processing:
- Set it and forget it
- Automatic tax calculations
- Direct deposits on schedule
- Tax filing in all 50 states
- Minimal intervention needed

### Embedded Payroll API

Build payroll into your own platform:
- White-label payroll solution
- Pre-built UI Flows
- Full API access
- Developer portal and sandbox
- Used by vertical SaaS, POS, ecommerce

### Gusto Global (EOR)

Employer of Record for international:
- Hire in 10+ countries
- Manage US and global in one platform
- Powered by Remote
- Compliant hiring without local entity

### Software Provisioning

Unique onboarding feature:
- Auto-create accounts for new hires
- Supported: Google Workspace, Microsoft 365, Slack, Zoom, Dropbox, Asana, Box, GitHub
- Streamlined day-one experience

### R&D Tax Credit

Automatic tax credit identification:
- Up to $250K in credits for eligible businesses
- Offset payroll tax liabilities
- Built into payroll processing

---

## Part 3: Domain Structure

### Employee_Core (8 hubs)
Core employee information.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Employee | `employee_id` | ✅ |
| Person | `person_id` | ✅ |
| SSN | `ssn_id` | ✅ |
| Employee_Profile | `employee_profile_id` | |

### Employment (8 hubs)
Employment and job information.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Employment | `employment_id` | ✅ |
| Job | `job_id` | ✅ |
| Job_Title | `job_title_id` | ✅ |
| Hire_Date | `hire_date_id` | ✅ |
| Employment_Status | `employment_status_id` | ✅ |
| Worker_Type | `worker_type_id` | ✅ |

### Payroll (8 hubs)
Payroll processing with AutoPilot.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Payroll | `payroll_id` | ✅ |
| Pay_Period | `pay_period_id` | ✅ |
| Paycheck | `paycheck_id` | ✅ |
| Direct_Deposit | `direct_deposit_id` | ✅ |
| Payroll_AutoPilot | `payroll_autopilot_id` | |
| Off_Cycle_Payroll | `off_cycle_payroll_id` | |

### Contractor (4 hubs)
1099 contractor payments.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Contractor | `contractor_id` | ✅ |
| Contractor_Payment | `contractor_payment_id` | ✅ |
| Form_1099_NEC | `form_1099_nec_id` | |
| International_Contractor | `international_contractor_id` | |

### Additional Domains

**Organization (7 hubs):** Company ✅, Department ✅, Location ✅, Work_Address, Supervisor ✅, Org_Chart, Employee_Directory

**Compensation (7 hubs):** Compensation ✅, Pay_Rate ✅, Annual_Salary, Hourly_Rate, Pay_Type ✅, Pay_Schedule ✅, Compensation_Tool

**Earnings (8 hubs):** Earning ✅, Earning_Type ✅, Regular_Pay, Overtime_Pay, Bonus, Commission, Holiday_Pay, Reimbursement

**Deductions (6 hubs):** Deduction ✅, Deduction_Type ✅, Benefit_Deduction, Retirement_Deduction, Garnishment ✅, Child_Support

**Tax (10 hubs):** Tax ✅, Tax_Filing ✅, Federal_Tax ✅, State_Tax ✅, Local_Tax, W4, W2, Form_1099, State_Registration, Tax_Credit

**Time_Attendance (5 hubs):** Time_Entry ✅, Time_Card ✅, Clock_In_Out, Time_Tracking ✅, Project_Tracking

**PTO (6 hubs):** Time_Off ✅, Time_Off_Policy ✅, Time_Off_Balance ✅, Accrual, Holiday, Time_Off_Request

**Benefits (8 hubs):** Benefit ✅, Benefit_Plan ✅, Health_Insurance ✅, Dental, Vision, Dependent ✅, Open_Enrollment, Broker_Integration

**Retirement (4 hubs):** Retirement_Plan ✅, K401, Contribution, Employer_Match

**Financial_Benefits (4 hubs):** Commuter_Benefits, FSA, HSA, Financial_Wellness

**Recruiting (6 hubs):** Job_Posting ✅, Candidate ✅, Application ✅, Applicant_Tracking ✅, Job_Description, Background_Check

**Onboarding (9 hubs):** Onboarding ✅, Self_Onboarding, Offer_Letter, E_Signature, Onboarding_Checklist, Document, I9, Software_Provisioning, Welcome_Email

**Talent_Management (5 hubs):** Performance_Review ✅, Goal ✅, Feedback, Employee_Survey, Training

**Employee_Self_Service (3 hubs):** Employee_Self_Service ✅, Mobile_App, Personal_Info_Update

**Compliance (4 hubs):** Compliance, Compliance_Alert, New_Hire_Reporting, Labor_Poster

**Reporting (4 hubs):** Report, Payroll_Report, Time_Off_Report, Workforce_Costing

**Global (3 hubs):** Gusto_Global, International_Employee, Country_Compliance

**Integration (4 hubs):** Integration, Accounting_Sync, API, Embedded_Payroll

---

## Part 4: Cross-Vendor Comparison

### Gusto Overlap with Other HCM Systems

| Comparison | Shared Concepts |
|------------|-----------------|
| Gusto + Paycor | **84** |
| Gusto + Paycom | 80 |
| Gusto + Paychex | 73 |

### Gusto-Unique Concepts (42)

Concepts unique to Gusto include:

**Embedded/API:**
- Embedded_Payroll
- API (as distinct entity)
- Accounting_Sync

**Contractor Focus:**
- Contractor (dedicated entity)
- Contractor_Payment
- International_Contractor
- Form_1099_NEC

**Global:**
- Gusto_Global
- International_Employee
- Country_Compliance

**Onboarding:**
- Software_Provisioning
- Self_Onboarding
- Onboarding_Checklist
- Welcome_Email

**Payroll Automation:**
- Payroll_AutoPilot
- Off_Cycle_Payroll
- State_Registration

**Time/PTO:**
- Time_Off_Policy
- Time_Off_Request
- Time_Off_Report
- Holiday (as entity)
- Project_Tracking

**Financial:**
- Commuter_Benefits
- Financial_Wellness
- Compensation_Tool

---

## Part 5: XLR8 Integration

### Product Detection

Detect Gusto via:

| Indicator | Pattern |
|-----------|---------|
| API URL | `api.gusto.com/*`, `api.gusto-demo.com/*` |
| Key fields | `company_uuid`, `employee_uuid`, `payroll_id` |
| Pagination | `page`, `per` parameters |
| OAuth | Gusto-specific auth flow |

### Spoke Patterns

```
Company → Employee → Job → Compensation
Employee → Paycheck → Earning/Deduction
Employee → Time_Card → Time_Entry
Employee → Time_Off → Time_Off_Policy
Employee → Benefit → Benefit_Plan/Dependent
Contractor → Contractor_Payment → Form_1099_NEC
Candidate → Application → Job_Posting
Employee → Onboarding → Onboarding_Checklist
```

### Column Patterns

| Pattern | Hub |
|---------|-----|
| employee_id, employee_uuid, emp_id | employee |
| company_id, company_uuid | company |
| payroll_id | payroll |
| contractor_id | contractor |
| job_id | job |
| compensation_id | compensation |

---

## Part 6: Pricing Tiers

| Plan | Base | Per Person | Key Features |
|------|------|------------|--------------|
| **Contractor** | $35/mo | $6/contractor | 1099 payments, 4-day deposit |
| **Simple** | $49/mo | $6/person | Single-state payroll, basic HR |
| **Plus** | $80/mo | $12/person | Multi-state, time tracking, HR tools |
| **Premium** | Custom | Custom | Dedicated support, HR experts |

**Add-ons:**
- Time & Attendance Plus: $6/mo per person
- Next-Day Direct Deposit: $15/mo + $3/mo per person
- Gusto Global: Custom pricing

---

## Deliverables

| File | Description |
|------|-------------|
| `gusto_schema_v1.json` | Full hub definitions (135 hubs) |
| `gusto_comparison.json` | Cross-vendor overlap analysis |
| `GUSTO_EXTRACTION.md` | This document |

---

## Updated HCM Product Summary

| Product | Hubs | Vendor |
|---------|------|--------|
| Paycor | 174 | Paycor |
| Oracle HCM | 173 | Oracle |
| Paycom | 164 | Paycom |
| Workday HCM | 160 | Workday |
| Dayforce | 157 | Ceridian |
| Paylocity | 142 | Paylocity |
| ADP WFN | 138 | ADP |
| SuccessFactors | 137 | SAP |
| **Gusto** | **135** | **Gusto** |
| Paychex Flex | 127 | Paychex |
| UKG WFM | 113 | UKG |
| UKG Pro | 105 | UKG |
| UKG Ready | 104 | UKG |
| **TOTAL** | **1,829** | **13 products** |

---

## Summary

Gusto brings **135 hubs** across 23 HCM domains - a focused SMB-oriented extraction. Key strengths:

1. **Modern UX** - Clean, intuitive interface that SMBs love
2. **AutoPilot** - Fully automated payroll processing
3. **Embedded API** - White-label payroll for developers
4. **Contractor Support** - First-class 1099 handling
5. **Gusto Global** - EOR for international hiring
6. **Software Provisioning** - Unique onboarding automation

Gusto's largest overlap is with **Paycor (84 shared)**, reflecting similar modern approaches to payroll. However, Gusto is more SMB-focused while Paycor targets mid-market.
