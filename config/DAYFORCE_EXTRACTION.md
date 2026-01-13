# Dayforce HCM - Domain Model Extraction
**Date:** January 10, 2026  
**Vendor:** Ceridian (now Dayforce, Inc.)  
**Source:** Dayforce API documentation, integration guides  
**Purpose:** Hub-and-spoke schema for XLR8 universal analysis engine

---

## Executive Summary

| Metric | Count |
|--------|-------|
| **Total Hubs** | 157 |
| **Core Hubs** | 57 |
| **Domains** | 17 |
| **Product Focus** | Unified HCM - HR, Payroll, Time, Scheduling, Benefits, Talent |

**Key Insight:** Dayforce uses a **single-database architecture** with **real-time continuous calculations** - not batch processing. Everything connects through the Employee record.

---

## Part 1: Domain Structure

### Employee_Core (11 hubs)
Central employee data - single employee record across platform.

| Hub | Semantic Type | Core | Description |
|-----|---------------|------|-------------|
| Employee | `employee_id` | ✅ | **Central** employee record |
| Person | `person_id` | ✅ | Person identity information |
| Employee Number | `employee_number` | ✅ | Unique employee identifier |
| Personal Information | `personal_info_id` | | Name, DOB, demographics |
| Contact | `contact_id` | | Phone, email, address |
| Address | `address_id` | | Home/work addresses |
| Emergency Contact | `emergency_contact_id` | | Emergency contacts |
| Dependent | `dependent_id` | | Employee dependents |
| National ID | `national_id` | | SSN, SIN, etc. |
| Work Eligibility | `work_eligibility_id` | | Right to work status |
| Employee Document | `employee_document_id` | | HR documents |

### Organization (10 hubs)
Organizational hierarchy and structure.

| Hub | Semantic Type | Core | Description |
|-----|---------------|------|-------------|
| Company | `company_id` | ✅ | Legal entity/company |
| Department | `department_id` | ✅ | Organizational department |
| Location | `location_id` | ✅ | Work location/site |
| Business Unit | `business_unit_id` | | Business unit |
| Cost Center | `cost_center_id` | ✅ | Cost allocation unit |
| Division | `division_id` | | Company division |
| Region | `region_id` | | Geographic region |
| Site | `site_id` | ✅ | Physical work site |
| Org Unit | `org_unit_id` | | Generic org unit |
| Reporting Hierarchy | `reporting_hierarchy_id` | | Reporting structure |

### Position_Job (8 hubs)
Position and job management.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Position | `position_id` | ✅ |
| Job | `job_id` | ✅ |
| Job Family | `job_family_id` | |
| Job Code | `job_code` | ✅ |
| Employment Status | `employment_status_id` | ✅ |
| Employment Type | `employment_type_id` | ✅ |
| Worker Type | `worker_type_id` | ✅ |
| Position Assignment | `position_assignment_id` | |

### Payroll (15 hubs)
Payroll processing and administration - **continuous real-time calculation**.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Payroll | `payroll_id` | ✅ |
| Pay Period | `pay_period_id` | ✅ |
| Pay Group | `pay_group_id` | ✅ |
| Pay Run | `pay_run_id` | ✅ |
| Earning | `earning_id` | ✅ |
| Earning Code | `earning_code` | ✅ |
| Deduction | `deduction_id` | ✅ |
| Deduction Code | `deduction_code` | ✅ |
| Tax | `tax_id` | ✅ |
| Tax Code | `tax_code` | ✅ |
| Pay Statement | `pay_statement_id` | |
| Direct Deposit | `direct_deposit_id` | |
| Garnishment | `garnishment_id` | |
| Pay Adjustment | `pay_adjustment_id` | |
| GL Export | `gl_export_id` | |

### Time_Attendance (13 hubs)
Time tracking and attendance management.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Time Entry | `time_entry_id` | ✅ |
| Punch | `punch_id` | ✅ |
| Timesheet | `timesheet_id` | ✅ |
| Time Clock | `time_clock_id` | |
| Attendance | `attendance_id` | ✅ |
| Absence | `absence_id` | ✅ |
| Absence Code | `absence_code` | ✅ |
| Time Off Balance | `time_off_balance_id` | ✅ |
| Time Off Request | `time_off_request_id` | |
| Overtime | `overtime_id` | |
| Exception | `exception_id` | |
| Attestation | `attestation_id` | |
| Labor Metric | `labor_metric_id` | |

### Scheduling (10 hubs)
Employee scheduling and shift management.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Schedule | `schedule_id` | ✅ |
| Shift | `shift_id` | ✅ |
| Shift Pattern | `shift_pattern_id` | |
| Schedule Template | `schedule_template_id` | |
| Shift Bid | `shift_bid_id` | |
| Shift Swap | `shift_swap_id` | |
| Coverage | `coverage_id` | |
| Labor Budget | `labor_budget_id` | |
| Labor Forecast | `labor_forecast_id` | |
| Schedule Zone | `schedule_zone_id` | |

### Benefits (16 hubs)
Benefits administration and enrollment.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Benefit Plan | `benefit_plan_id` | ✅ |
| Benefit Group | `benefit_group_id` | ✅ |
| Benefit Enrollment | `benefit_enrollment_id` | ✅ |
| Benefit Election | `benefit_election_id` | |
| Coverage Level | `coverage_level_id` | |
| Carrier | `carrier_id` | |
| Medical Plan | `medical_plan_id` | ✅ |
| Dental Plan | `dental_plan_id` | |
| Vision Plan | `vision_plan_id` | |
| Life Insurance | `life_insurance_id` | |
| Retirement Plan | `retirement_plan_id` | ✅ |
| HSA | `hsa_id` | |
| FSA | `fsa_id` | |
| Open Enrollment | `open_enrollment_id` | |
| Life Event | `life_event_id` | |
| ACA Compliance | `aca_compliance_id` | |

### Recruiting (12 hubs)
Talent acquisition and recruiting.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Requisition | `requisition_id` | ✅ |
| Job Posting | `job_posting_id` | ✅ |
| Candidate | `candidate_id` | ✅ |
| Application | `application_id` | ✅ |
| Applicant | `applicant_id` | ✅ |
| Interview | `interview_id` | |
| Offer | `offer_id` | ✅ |
| Recruiting Source | `recruiting_source_id` | |
| Background Check | `background_check_id` | |
| Screening | `screening_id` | |
| Referral | `referral_id` | |
| Talent Pool | `talent_pool_id` | |

### Additional Domains

**Compensation (10 hubs):** Pay Class ✅, Pay Grade ✅, Pay Rate ✅, Pay Type ✅, Compensation Package, Salary ✅, Bonus, Allowance, Currency, Pay Frequency ✅

**Onboarding (6 hubs):** Onboarding ✅, Onboarding Task, I-9, E-Verify, New Hire Packet, Preboarding

**Performance (8 hubs):** Performance Review ✅, Goal ✅, Competency ✅, Rating, Feedback, Development Plan, Review Cycle, Check-In

**Learning (7 hubs):** Course ✅, Training ✅, Certification ✅, Learning Assignment, Learning Completion, Credential, License

**Succession (4 hubs):** Succession Plan, Career Path, Talent Profile, Potential Rating

**Compliance (7 hubs):** Compliance Rule, Work Rule ✅, Overtime Rule, Break Rule, Minimum Wage, Labor Standard, Policy

**Analytics (5 hubs):** Report, Dashboard, KPI, Metric, Data Export

**Staffing_Events (9 hubs):** Hire ✅, Termination ✅, Termination Reason ✅, Transfer, Promotion, Rehire, Job Change, Leave of Absence ✅, Return from Leave

**Security_Integration (6 hubs):** User, Role, Permission, Integration, Webhook, API Client

---

## Part 2: Dayforce Architecture

### Single Database Model
Unlike multi-module systems, Dayforce uses **one database** for all functions. This enables:

- **Real-time calculations** - Net pay updates instantly as time is entered
- **Continuous payroll** - No batch processing, always current
- **Single employee record** - One source of truth across all modules

```
                    ┌─────────────────┐
                    │    EMPLOYEE     │  ← Single Record
                    │  (employee_id)  │
                    └────────┬────────┘
                             │
     ┌───────────┬───────────┼───────────┬───────────┐
     │           │           │           │           │
     ▼           ▼           ▼           ▼           ▼
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│  Time   │ │ Payroll │ │Benefits │ │Schedule │ │ Talent  │
│ Entry   │ │   Run   │ │Election │ │  Shift  │ │  Goal   │
└─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘
     │           │           │           │           │
     └───────────┴───────────┼───────────┴───────────┘
                             │
                    ┌────────▼────────┐
                    │  REAL-TIME      │
                    │  NET PAY CALC   │
                    └─────────────────┘
```

### API Structure

**REST API Base:**
```
https://{client}.dayforcehcm.com/api/v1/{tenant}/{resource}
```

**Key Endpoints:**
- `/Employees` - Employee records
- `/Employees/{xrefcode}/Addresses` - Employee addresses
- `/Employees/{xrefcode}/Contacts` - Contacts
- `/Employees/{xrefcode}/CompensationSummary` - Pay info
- `/Employees/{xrefcode}/EmployeePunches` - Time punches
- `/Employees/{xrefcode}/TimeOffBalances` - PTO balances
- `/Departments` - Department data
- `/Locations` - Location data

---

## Part 3: Cross-Vendor Comparison

### Dayforce vs Competition

| Comparison | Shared Concepts | Notes |
|------------|-----------------|-------|
| **Dayforce + Workday** | **63** | Strong overlap - both unified HCM |
| Dayforce + UKG Ready | 35 | Similar mid-market focus |
| Dayforce + UKG Pro | 9 | Different architectures |
| Dayforce + UKG WFM | 7 | WFM is specialized |

### Key Overlap with Workday (63 shared)
Both platforms share concepts in:
- **Core HR:** Employee, Person, Company, Department, Location, Cost Center
- **Compensation:** Pay Grade, Salary, Bonus, Compensation Package
- **Benefits:** Benefit Plan, Enrollment, Medical Plan, Retirement Plan
- **Time:** Time Entry, Timesheet, Schedule, Shift
- **Talent:** Performance Review, Goal, Competency, Certification
- **Recruiting:** Candidate, Job Posting, Offer, Background Check

### Dayforce-Unique Concepts (69)
Concepts in Dayforce not found in other vendors:
- **Compliance:** ACA Compliance, Break Rule, Work Rule, Labor Standard
- **Scheduling:** Shift Bid, Shift Swap, Coverage, Labor Forecast
- **Benefits:** Carrier, Coverage Level, HSA, FSA
- **Onboarding:** E-Verify, New Hire Packet, Preboarding
- **Analytics:** KPI, Metric, Data Export

---

## Part 4: XLR8 Integration

### Product Detection

Detect Dayforce via:

| Indicator | Pattern |
|-----------|---------|
| API URL | `*.dayforcehcm.com` |
| XRefCode usage | `xrefcode` field in records |
| Employee Number format | Dayforce-specific patterns |
| Pay Run structure | Continuous payroll indicators |

### Spoke Patterns

```
Employee → Department (belongs to)
Employee → Location (works at)
Employee → Position (holds)
Employee → Pay Group (paid via)
Punch → Employee (logged by)
Time Entry → Employee (worked by)
Schedule → Shift (contains)
Schedule → Employee (assigned to)
Benefit Enrollment → Benefit Plan (enrolled in)
Requisition → Job Posting (published as)
Candidate → Application (submitted)
```

### Column Patterns

| Pattern | Hub |
|---------|-----|
| employee_id, employee_number, xrefcode | employee |
| department_id, department_code | department |
| location_id, location_code | location |
| position_id, position_code | position |
| pay_group_*, payroll_group | pay_group |
| punch_id, time_punch* | punch |
| shift_id, shift_code | shift |
| schedule_id | schedule |

---

## Part 5: All-Vendor Summary

### Complete Extraction Status

| Vendor | Product | Hubs | Status |
|--------|---------|------|--------|
| **Dayforce** | HCM | **157** | ✅ Complete |
| **Workday** | HCM | **160** | ✅ Complete |
| UKG | Pro | 105 | ✅ Complete |
| UKG | WFM Dimensions | 113 | ✅ Complete |
| UKG | Ready | 104 | ✅ Complete |
| **TOTAL** | | **639** | |

### Unique Concepts (Deduplicated)
**504 unique HCM concepts** across all vendors

### Universal Concept (All 5 Products)
Only **1 concept** exists in ALL products: **Shift**

---

## Deliverables

| File | Description |
|------|-------------|
| `dayforce_schema_v1.json` | Full hub definitions (157 hubs) |
| `all_vendors_comparison.json` | Multi-vendor comparison |
| `DAYFORCE_EXTRACTION.md` | This document |

---

## Dayforce Key Differentiators

1. **Continuous Payroll** - Real-time net pay calculations (not batch)
2. **Single Database** - One source of truth, no integrations between modules
3. **Strong WFM** - Scheduling, forecasting, labor optimization
4. **Compliance Focus** - ACA, labor law rules built-in
5. **Time + Pay Together** - Unified time and payroll on same platform
