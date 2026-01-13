# Paychex Flex - Domain Model Extraction
**Date:** January 10, 2026  
**Vendor:** Paychex  
**Source:** Paychex Developer Portal, API documentation, product docs  
**Purpose:** Hub-and-spoke schema for XLR8 universal analysis engine

---

## Executive Summary

| Metric | Count |
|--------|-------|
| **Total Hubs** | 127 |
| **Core Hubs** | 53 |
| **Domains** | 18 |
| **Product Focus** | SMB-Enterprise HCM - Payroll, HR, Benefits, Time, Talent |

**Key Insight:** Paychex Flex uses a **Worker-centric architecture** with Company context. Workers can have up to 25 different pay rates. The platform emphasizes payroll accuracy with strong tax compliance and workers' compensation integration.

---

## Part 1: Paychex Flex Architecture

### Worker-Centric Data Model

```
┌─────────────────────────────────────────────────────────────────┐
│                         COMPANY                                  │
│        (Company ID - employer context)                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                          WORKER                                  │
│        (Worker ID - employee or contractor)                      │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│    PERSON     │    │  EMPLOYMENT   │    │   BENEFITS    │
│               │    │               │    │               │
├───────────────┤    ├───────────────┤    ├───────────────┤
│ Legal Name    │    │ Job Title     │    │ Health/Dental │
│ Address       │    │ Department    │    │ 401(k)        │
│ SSN           │    │ Pay Rates     │    │ FSA/HSA       │
│ Tax Status    │    │ FLSA Status   │    │ Workers Comp  │
└───────────────┘    └───────────────┘    └───────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│   PAYROLL     │    │  TIME & ATT   │    │    TALENT     │
│               │    │               │    │               │
├───────────────┤    ├───────────────┤    ├───────────────┤
│ Checks        │    │ Time Cards    │    │ Recruiting    │
│ Earnings      │    │ Schedules     │    │ Onboarding    │
│ Deductions    │    │ Attendance    │    │ Performance   │
│ Pay Components│    │ Accruals      │    │ Learning      │
└───────────────┘    └───────────────┘    └───────────────┘
```

### API Structure

**Base URL:**
```
https://api.paychex.com
```

**Key Endpoints:**
- `/companies` - Company information
- `/companies/{companyId}/workers` - Workers (employees/contractors)
- `/companies/{companyId}/workers/{workerId}/compensation` - Pay rates
- `/companies/{companyId}/payperiods` - Pay period calendar
- `/companies/{companyId}/checks` - Payroll checks

**Authentication:** OAuth 2.0 Client Credentials

**Webhooks:** Event-driven notifications for worker changes, payroll processed

---

## Part 2: Product Packages

### Paychex Flex Packages

| Package | Target | Features |
|---------|--------|----------|
| **Express** | 1-9 employees | Basic payroll |
| **Pro** | 10-49 employees | Payroll + HR basics |
| **Select** | 50-499 employees | Full HCM suite |
| **Enterprise** | 500+ employees | Large business features |

### Add-On Modules
- Time and Attendance (Stratustime)
- Benefits Administration
- Recruiting (AI-assisted)
- Performance Management
- Learning Management
- Workers' Compensation
- HR Analytics

---

## Part 3: Domain Structure

### Worker_Core (10 hubs)
Core worker information (Workers API).

| Hub | Semantic Type | Core | Description |
|-----|---------------|------|-------------|
| Worker | `worker_id` | ✅ | Employee or contractor |
| Person | `person_id` | ✅ | Personal information |
| SSN | `ssn_id` | ✅ | Social Security Number |
| Legal_Name | `legal_name_id` | | Legal name |
| Birth_Date | `birth_date_id` | | Date of birth |

### Employment (10 hubs)
Employment and job information.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Employment | `employment_id` | ✅ |
| Job | `job_id` | ✅ |
| Job_Title | `job_title_id` | ✅ |
| Worker_Type | `worker_type_id` | ✅ |
| Employment_Status | `employment_status_id` | ✅ |
| Hire_Date | `hire_date_id` | ✅ |
| FLSA_Status | `flsa_status_id` | |

### Organization (8 hubs)
Company and organizational structure.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Company | `company_id` | ✅ |
| Organization | `organization_id` | ✅ |
| Department | `department_id` | ✅ |
| Location | `location_id` | ✅ |
| Supervisor | `supervisor_id` | ✅ |

### Payroll (7 hubs)
Payroll processing.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Payroll | `payroll_id` | ✅ |
| Pay_Period | `pay_period_id` | ✅ |
| Check | `check_id` | ✅ |
| Direct_Deposit | `direct_deposit_id` | ✅ |
| Pay_Component | `pay_component_id` | ✅ |
| Check_History | `check_history_id` | |
| Unprocessed_Check | `unprocessed_check_id` | |

### Compensation (7 hubs)
Pay rates and compensation.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Compensation | `compensation_id` | ✅ |
| Pay_Rate | `pay_rate_id` | ✅ |
| Pay_Type | `pay_type_id` | ✅ |
| Pay_Frequency | `pay_frequency_id` | ✅ |
| Annual_Salary | `annual_salary_id` | |
| Hourly_Rate | `hourly_rate_id` | |

### Additional Domains

**Earnings (9 hubs):** Earning ✅, Earning_Code ✅, Regular_Pay, Overtime_Pay, Bonus, Commission, Tip, Vacation_Pay, Sick_Pay

**Deductions (8 hubs):** Deduction ✅, Deduction_Code ✅, Benefit_Deduction, Retirement_Deduction, Garnishment, Child_Support, Union_Dues, Loan

**Tax (9 hubs):** Tax ✅, Tax_Status ✅, Federal_Tax ✅, State_Tax ✅, Local_Tax, FICA, W4, W2, Filing_Status

**Time_Attendance (10 hubs):** Time_Entry ✅, Time_Card ✅, Punch, Schedule ✅, Shift, Attendance ✅, Time_Off ✅, Time_Off_Balance ✅, Accrual, Leave_Management

**Benefits (12 hubs):** Benefit ✅, Benefit_Plan ✅, Benefits_Coverage, Benefit_Enrollment ✅, Benefit_Change_Request, Dependent ✅, Health_Insurance, Dental, Vision, FSA, HSA, Retirement_Plan ✅

**Workers_Comp (4 hubs):** Workers_Comp ✅, Workers_Comp_Code ✅, Workers_Comp_Claim, Corporate_Officer_Code

**Recruiting (7 hubs):** Job_Posting ✅, Candidate ✅, Application ✅, Applicant_Tracking, Interview, Offer, Background_Check

**Onboarding (6 hubs):** Onboarding ✅, New_Hire ✅, I9, E_Verify, Onboarding_Task, Document

**Performance (4 hubs):** Performance_Review ✅, Goal ✅, Survey, Feedback

**Learning (4 hubs):** Course ✅, Learning_Assignment, Learning_Completion, Smart_Group

---

## Part 4: Cross-Vendor Comparison

### Paychex Flex Overlap with Other HCM Systems

| Comparison | Shared Concepts |
|------------|-----------------|
| Paychex + Paylocity | **84** (closest competitor) |
| Paychex + ADP WFN | 66 |
| Paychex + Dayforce | 54 |
| Paychex + Workday HCM | 34 |

### Commonly Shared Concepts

Paychex shares these core HCM concepts with competitors:
- Worker, Employment, Job_Title, Department
- Company, Location, Supervisor
- Check, Earning, Deduction, Pay_Period
- Benefit_Plan, Benefit_Enrollment, Dependent
- Time_Entry, Time_Card, Schedule, Time_Off
- Candidate, Application, Job_Posting
- Performance_Review, Goal

### Paychex-Unique Concepts (32)

Concepts unique to Paychex Flex include:
- **Check-based:** Check, Check_History, Unprocessed_Check
- **Workers Comp:** Workers_Comp, Workers_Comp_Code, Corporate_Officer_Code
- **Benefits Detail:** Health_Insurance, Dental, Vision, Benefits_Coverage
- **Tax Detail:** Filing_Status, Tax_Status
- **Other:** Smart_Group, Applicant_Tracking, Leave_Management

---

## Part 5: XLR8 Integration

### Product Detection

Detect Paychex Flex via:

| Indicator | Pattern |
|-----------|---------|
| API URL | `api.paychex.com/*` |
| Key fields | `workerId`, `companyId`, `payComponent`, `check` |
| Pay rates | Up to 25 rates per worker |
| Workers comp | `workersCompCode`, `corporateOfficerCode` |

### Spoke Patterns

```
Company → Worker (employs)
Worker → Employment (has assignment)
Employment → Job (holds job)
Employment → Department (belongs to)
Worker → Supervisor (reports to)
Worker → Pay_Rate (has compensation - up to 25)
Worker → Check (receives paycheck)
Check → Earning (includes earnings)
Check → Deduction (includes deductions)
Check → Pay_Period (for period)
Worker → Benefit (enrolled in)
Benefit → Benefit_Plan (plan type)
Worker → Time_Card (tracks time)
Worker → Workers_Comp (covered by)
Candidate → Application (submits)
```

### Column Patterns

| Pattern | Hub |
|---------|-----|
| worker_id, workerid, employee_id | worker |
| company_id, companyid | company |
| check_id, checkid, paycheck | check |
| pay_component, paycomponent | pay_component |
| earning_code, earningcode | earning_code |
| deduction_code, deductioncode | deduction_code |
| workers_comp_code, wc_code | workers_comp_code |
| pay_period, payperiod | pay_period |
| supervisor_id, manager_id | supervisor |

---

## Part 6: Paychex-Specific Concepts

### Multiple Pay Rates

Workers can have up to 25 different pay rates:
- Primary rate
- Secondary rates (shift differentials, job-specific)
- Bonus/commission rates
- Special rates (overtime, holiday)

### Check vs Pay Statement

Paychex uses "Check" terminology:
- Check = Individual pay statement
- Unprocessed_Check = Pending payroll entry
- Check_History = Historical pay records
- Pay_Component = Earning/deduction on check

### Workers Compensation

Strong WC integration:
- Workers_Comp_Code - Class code for premium calculation
- Corporate_Officer_Code (P=Partner, S=Sole Prop, X=Officer)
- Waive reasons for excluded workers

### Pay Components

Classification system:
- Earnings (regular, OT, bonus, tips)
- Deductions (benefits, retirement, garnishments)
- Taxes (federal, state, local)
- Each has start/end dates for availability

---

## Part 7: API Endpoints Summary

### Company APIs
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/companies` | GET | All companies |
| `/companies/{id}` | GET | Single company |
| `/companies/{id}/organizations` | GET | Org structure |
| `/companies/{id}/payperiods` | GET | Pay calendar |

### Worker APIs
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/companies/{id}/workers` | GET/POST | Workers list |
| `/companies/{id}/workers/{id}` | GET/PATCH | Single worker |
| `/companies/{id}/workers/{id}/compensation` | GET | Pay rates |
| `/companies/{id}/workers/{id}/communications` | GET | Contact info |

### Payroll APIs
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/companies/{id}/checks` | GET/POST | Paychecks |
| `/companies/{id}/paycomponents` | GET | Pay components |

---

## Deliverables

| File | Description |
|------|-------------|
| `paychex_schema_v1.json` | Full hub definitions (127 hubs) |
| `paychex_comparison.json` | Cross-vendor overlap analysis |
| `PAYCHEX_EXTRACTION.md` | This document |

---

## Updated HCM Product Summary

| Product | Hubs | Vendor |
|---------|------|--------|
| Oracle HCM | 173 | Oracle |
| Workday HCM | 160 | Workday |
| Dayforce | 157 | Ceridian |
| Paylocity | 142 | Paylocity |
| ADP WFN | 138 | ADP |
| SuccessFactors | 137 | SAP |
| **Paychex Flex** | **127** | **Paychex** |
| UKG WFM | 113 | UKG |
| UKG Pro | 105 | UKG |
| UKG Ready | 104 | UKG |
| **TOTAL** | **1,356** | **10 products** |

---

## Summary

Paychex Flex brings **127 hubs** across 18 HCM domains with strengths in:

1. **Payroll Accuracy** - Check-based processing with pay component classification
2. **Multiple Pay Rates** - Up to 25 rates per worker
3. **Workers Compensation** - Deep WC integration with class codes
4. **Tax Compliance** - Strong federal/state/local tax handling
5. **Scalability** - Express to Enterprise packages
6. **Integration** - ~300 third-party integrations via Marketplace

Paychex's largest overlap is with **Paylocity (84 shared)**, reflecting similar SMB/mid-market positioning and payroll-centric architecture.
