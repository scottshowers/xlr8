# UKG Ready - Domain Model Extraction
**Date:** January 10, 2026  
**Source:** UKG Developer Hub, Knit API docs, CloudApper integration guides  
**Purpose:** Hub-and-spoke schema for XLR8 universal analysis engine

---

## Executive Summary

| Metric | Count |
|--------|-------|
| **Total Hubs** | 104 |
| **Core Hubs** | 33 |
| **Domains** | 18 |
| **Product Focus** | Mid-market unified HR/Payroll/Time |

**Key Insight:** UKG Ready is a unified platform combining HCM, Payroll, and Time & Labor - making it overlap with BOTH UKG Pro (HCM/Payroll) AND UKG WFM (Time/Scheduling), but with its own distinct architecture.

---

## Part 1: Domain Structure

### Company_Organization (8 hubs)
Company structure and organizational hierarchy.

| Hub | Semantic Type | Core | Notes |
|-----|---------------|------|-------|
| Company | `company_code` | ✅ | Tenant identifier |
| Cost Center | `cost_center_code` | ✅ | **Jobs in Ready = Cost Centers** |
| Cost Center Tree | `cost_center_tree_code` | | Hierarchy structure |
| Cost Center List | `cost_center_list_code` | | Groupings |
| EIN | `ein_code` | ✅ | Employer ID |
| Account Group | `account_group_code` | | Permission groupings |
| Position | `position_code` | ✅ | Job positions |
| Department | `department_code` | | Departments |

### Employee_Core (9 hubs)
Employee master data and demographics.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Employee Account | `employee_account_code` | ✅ |
| System Account | `system_account_code` | |
| Service Account | `service_account_code` | |
| Demographics | `demographics_code` | |
| Contact Information | `contact_info_code` | |
| Emergency Contact | `emergency_contact_code` | |
| Dependent | `dependent_code` | |
| Education | `education_code` | |
| Work History | `work_history_code` | |

### Employment (8 hubs)
Employment status and job assignments.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Employment Status | `employment_status_code` | ✅ |
| Worker Type | `worker_type_code` | ✅ |
| Job Assignment | `job_assignment_code` | ✅ |
| Position Assignment | `position_assignment_code` | |
| Hire Source | `hire_source_code` | |
| Referral | `referral_code` | |
| Termination Reason | `termination_reason_code` | ✅ |
| Rehire Eligibility | `rehire_eligibility_code` | |

### Compensation (10 hubs)
Pay rates and compensation management.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Pay Information | `pay_information_code` | ✅ |
| Pay Type | `pay_type_code` | ✅ |
| Pay Grade | `pay_grade_code` | |
| Pay Rate | `pay_rate_code` | ✅ |
| Base Compensation | `base_compensation_code` | ✅ |
| Total Compensation | `total_compensation_code` | |
| Additional Compensation | `additional_compensation_code` | |
| Rate Table | `rate_table_code` | |
| Rate Schedule | `rate_schedule_code` | |
| Currency | `currency_code` | |

### Payroll (9 hubs)
Payroll processing and pay statements.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Payroll | `payroll_code` | ✅ |
| Pay Period | `pay_period_code` | ✅ |
| Pay Period Profile | `pay_period_profile_code` | ✅ |
| Pay Statement | `pay_statement_code` | ✅ |
| Pay Statement Type | `pay_statement_type_code` | |
| Payroll Type | `payroll_type_code` | |
| Payroll Batch Type | `payroll_batch_type_code` | |
| Payroll Export | `payroll_export_code` | |
| Snapshot | `snapshot_code` | |

### Earnings_Deductions (7 hubs)
Earnings and deduction configuration.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Earning | `earning_code` | ✅ |
| Scheduled Earning | `scheduled_earning_code` | |
| Deduction | `deduction_code` | ✅ |
| Scheduled Deduction | `scheduled_deduction_code` | |
| Pay Category | `pay_category_code` | |
| Garnishment | `garnishment_code` | |
| Child Support | `child_support_code` | |

### Taxes (4 hubs)
Tax configuration and withholding.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Tax Code | `tax_code` | ✅ |
| Tax Information | `tax_information_code` | ✅ |
| Workers Comp Code | `workers_comp_code` | ✅ |
| Tax Withholding | `tax_withholding_code` | |

### Time_Labor (9 hubs)
Time tracking and timesheets.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Timesheet | `timesheet_code` | ✅ |
| Timesheet Profile | `timesheet_profile_code` | |
| Time Entry | `time_entry_code` | ✅ |
| Punch | `punch_code` | ✅ |
| Attendance | `attendance_code` | |
| Reason Code | `reason_code` | |
| Pay Calculation Profile | `pay_calculation_profile_code` | |
| Workday Breakdown Profile | `workday_breakdown_profile_code` | |
| Working Time Regulation | `working_time_regulation_code` | |

### Scheduling (6 hubs)
Advanced scheduling (requires SCHEDULE subsystem).

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Schedule | `schedule_code` | ✅ |
| Schedule Setting | `schedule_setting_code` | |
| Shift | `shift_code` | ✅ |
| Shift Premium | `shift_premium_code` | |
| Scheduler Profile | `scheduler_profile_code` | |
| Work Schedule Profile | `work_schedule_profile_code` | |

### Time_Off (6 hubs)
PTO, leave, and accruals.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| PTO Request | `pto_request_code` | ✅ |
| Accrual | `accrual_code` | ✅ |
| Accrual Profile | `accrual_profile_code` | |
| Time Off Type | `time_off_type_code` | ✅ |
| Time Off Planning Profile | `time_off_planning_profile_code` | |
| Holiday | `holiday_code` | |

### Remaining Domains

**Benefits (4 hubs):** Benefit Plan, Benefit Enrollment, Retirement Plan Profile, Insurance

**Profiles_Security (4 hubs):** Security Profile ✅, Access Policy Profile, Role Profile, Function Access Profile

**Skills_Training (4 hubs):** Skill ✅, Training, Certification, Training Profile

**Performance (3 hubs):** Performance Review, Succession Profile, Points Profile

**Projects (2 hubs):** Project, Project Metrics

**Assets (3 hubs):** Vehicle, Vehicle Assignment, Vendor

**Recruiting (4 hubs):** Job Requisition, Candidate, Questionnaire, Onboarding

**Reference_Data (4 hubs):** Timezone ✅, Country, State, Union

---

## Part 2: API Structure

### Base URL Pattern
```
https://secure3.saashr.com/ta/rest/v2/companies/{cid}/...
```

### Key Endpoints

| Resource | Endpoint | Description |
|----------|----------|-------------|
| Employees | `/employees` | Employee records |
| Timesheets | `/timesheets` | Timesheet data |
| Time Entries | `/time-entries` | Individual entries |
| Punches | `/time-punches` | Clock punches |
| Schedules | `/schedules` | Work schedules |
| Cost Centers | `/config/cost-centers` | Cost center config |
| Pay Periods | `/payroll/pay-periods` | Pay period data |
| Payrolls | `/payroll/payrolls` | Payroll runs |
| Accruals | `/accruals` | Accrual balances |

### Ready-Specific Concepts

**Jobs = Cost Centers:** In UKG Ready, what Pro calls "Jobs" are called "Cost Centers". The cost center tree provides the organizational hierarchy.

**Unified Timesheet:** Ready combines time entry, punches, and scheduling in a single timesheet interface rather than separate modules.

---

## Part 3: Cross-Product Comparison

### UKG Product Family Overview

| Product | Hubs | Target Market | Focus |
|---------|------|---------------|-------|
| UKG Pro | 105 | Enterprise | HCM + Payroll |
| UKG WFM Dimensions | 113 | Enterprise | Workforce Management |
| UKG Ready | 104 | Mid-Market | Unified HR/Payroll/Time |

### Shared Concepts

**All Three Products (1):**
- Shift

**Pro + Ready (HCM/Payroll - 5):**
- Country, Deduction, Earning, Skill, Tax

**WFM + Ready (Time/Scheduling - 8):**
- Accrual, Cost Center, Function Access Profile, Holiday, Payroll Export, Punch, Role Profile, Timezone

**Pro + WFM (2):**
- Job, Location

### Product Positioning

```
                    ┌─────────────────┐
                    │    UKG Pro      │
                    │  (Enterprise)   │
                    │   HCM/Payroll   │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        │     ┌──────────────┴──────────────┐     │
        │     │         SHARED: Shift       │     │
        │     └──────────────┬──────────────┘     │
        │                    │                    │
┌───────┴───────┐     ┌──────┴──────┐     ┌──────┴───────┐
│   UKG WFM     │     │  UKG Ready  │     │   UKG Pro    │
│  Dimensions   │     │ (Mid-Market)│     │   (cont.)    │
│  Workforce    │     │  Unified    │     │              │
└───────────────┘     └─────────────┘     └──────────────┘
```

---

## Part 4: XLR8 Integration

### Product Detection

When data is uploaded, detect which UKG product:

| Indicator | Product |
|-----------|---------|
| BRIT templates, NCU files | UKG Pro |
| Cost Center trees, /ta/rest/ endpoints | UKG Ready |
| Labor Categories, Activities, /api/v1/ endpoints | UKG WFM |
| Attendance Policies, Forecasting | UKG WFM |
| Pay Calculation Profiles, Timesheet Profiles | UKG Ready |

### Spoke Patterns

```
Employee → Cost Center (primary assignment)
Employee → Position (position assignment)
Timesheet → Employee (timesheet owner)
Time Entry → Cost Center (cost allocation)
Punch → Cost Center (punch transfer)
Schedule → Shift (shift assignment)
Pay Statement → Payroll (payroll run)
Accrual → Time Off Type (balance type)
```

---

## Deliverables

| File | Description |
|------|-------------|
| `ukg_ready_schema_v1.json` | Full hub definitions |
| `ukg_family_unified_vocabulary.json` | All 3 UKG products combined |
| `UKG_READY_EXTRACTION.md` | This document |

---

## Session Summary - Complete UKG Family

| Product | Status | Hubs | File |
|---------|--------|------|------|
| UKG Pro | ✅ Complete | 105 | `ukg_pro_schema_v3_normalized.json` |
| UKG WFM Dimensions | ✅ Complete | 113 | `ukg_wfm_dimensions_schema_v1.json` |
| UKG Ready | ✅ Complete | 104 | `ukg_ready_schema_v1.json` |
| **TOTAL** | | **322** hubs | |
| **Unified** | | **303** unique concepts | `ukg_family_unified_vocabulary.json` |

### Key Finding

The three UKG products are remarkably distinct:
- Only **1 concept** (Shift) is shared across all three
- Only **16 concepts** are shared between any two products
- **287 concepts** are unique to a single product

This means XLR8 needs **separate domain models** for each UKG product, with a thin mapping layer for the few shared concepts.
