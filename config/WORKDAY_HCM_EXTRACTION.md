# Workday HCM - Domain Model Extraction
**Date:** January 10, 2026  
**Source:** Workday docs, community resources, integration guides  
**Purpose:** Hub-and-spoke schema for XLR8 universal analysis engine

---

## Executive Summary

| Metric | Count |
|--------|-------|
| **Total Hubs** | 160 |
| **Core Hubs** | 55 |
| **Domains** | 18 |
| **Product Focus** | Enterprise HCM (HR, Payroll, Talent, Benefits, Time) |

**Key Insight:** Workday uses an object-oriented data model with the **Worker** object at the center. Everything revolves around the worker-position-organization relationship.

---

## Part 1: Domain Structure

### Worker_Core (10 hubs)
Central worker/employee data - the core of Workday HCM.

| Hub | Semantic Type | Core | Description |
|-----|---------------|------|-------------|
| Worker | `worker_id` | ✅ | **Central** employee/contingent worker record |
| Person | `person_id` | ✅ | Person identity (can have multiple workers) |
| Employee | `employee_id` | ✅ | Employee worker subtype |
| Contingent Worker | `contingent_worker_id` | ✅ | Contract/temp worker subtype |
| Worker Document | `worker_document_id` | | Employee documents |
| Personal Information | `personal_info_id` | | Name, contact, demographics |
| Emergency Contact | `emergency_contact_id` | | Emergency contacts |
| Dependent | `dependent_id` | | Dependents and beneficiaries |
| National ID | `national_id` | | SSN, passport, etc. |
| Visa | `visa_id` | | Immigration/visa records |

### Organization (11 hubs)
Organizational hierarchy and structure.

| Hub | Semantic Type | Core | Description |
|-----|---------------|------|-------------|
| Supervisory Organization | `supervisory_org_id` | ✅ | **Reporting hierarchy - foundation of HCM** |
| Company | `company_id` | ✅ | Legal entity/company |
| Cost Center | `cost_center_id` | ✅ | Financial tracking unit |
| Region | `region_id` | | Geographic region |
| Location | `location_id` | ✅ | Work location/site |
| Business Site | `business_site_id` | | Physical business site |
| Business Unit | `business_unit_id` | | Business unit organization |
| Matrix Organization | `matrix_org_id` | | Matrix management structure |
| Pay Group | `pay_group_id` | ✅ | Payroll grouping |
| Organization Hierarchy | `org_hierarchy_id` | | Org hierarchy definitions |
| Custom Organization | `custom_org_id` | | User-defined org types |

### Position_Staffing (6 hubs)
Position management and staffing model.

| Hub | Semantic Type | Core | Description |
|-----|---------------|------|-------------|
| Position | `position_id` | ✅ | Position definition (seat) |
| Job Requisition | `job_requisition_id` | ✅ | Open position request |
| Staffing Model | `staffing_model_id` | | Position/Job/Headcount management |
| Headcount Group | `headcount_group_id` | | Headcount planning group |
| Position Restriction | `position_restriction_id` | | Position hiring rules |
| Worker Position | `worker_position_id` | | Worker-to-position assignment |

### Job_Profile (8 hubs)
Job catalog and profile hierarchy.

| Hub | Semantic Type | Core | Description |
|-----|---------------|------|-------------|
| Job Profile | `job_profile_id` | ✅ | Job template with requirements |
| Job Family | `job_family_id` | ✅ | Group of related job profiles |
| Job Family Group | `job_family_group_id` | | Top-level job grouping |
| Job Category | `job_category_id` | | Job categorization |
| Management Level | `management_level_id` | ✅ | Supervisor/Manager/IC level |
| Worker Type | `worker_type_id` | ✅ | Employee vs Contingent |
| Worker Sub-Type | `worker_sub_type_id` | | Further worker classification |
| Time Type | `time_type_id` | ✅ | Full-time vs Part-time |

### Compensation (14 hubs)
Compensation plans and administration.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Compensation Plan | `compensation_plan_id` | ✅ |
| Compensation Grade | `compensation_grade_id` | ✅ |
| Compensation Grade Profile | `grade_profile_id` | |
| Compensation Package | `compensation_package_id` | ✅ |
| Salary Plan | `salary_plan_id` | ✅ |
| Hourly Plan | `hourly_plan_id` | |
| Bonus Plan | `bonus_plan_id` | |
| Stock Plan | `stock_plan_id` | |
| Commission Plan | `commission_plan_id` | |
| Allowance Plan | `allowance_plan_id` | |
| Pay Range | `pay_range_id` | |
| Compensation Element | `comp_element_id` | |
| Merit Plan | `merit_plan_id` | |
| Currency | `currency_id` | |

### Benefits (11 hubs)
Benefits plans and enrollment.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Benefit Plan | `benefit_plan_id` | ✅ |
| Benefit Group | `benefit_group_id` | ✅ |
| Health Care Coverage | `health_care_id` | ✅ |
| Insurance Coverage | `insurance_id` | |
| Retirement Plan | `retirement_plan_id` | ✅ |
| HSA Plan | `hsa_plan_id` | |
| FSA Plan | `fsa_plan_id` | |
| Benefit Election | `benefit_election_id` | |
| Benefit Event | `benefit_event_id` | |
| Open Enrollment | `open_enrollment_id` | |
| Dependent Coverage | `dependent_coverage_id` | |

### Payroll (13 hubs)
Payroll processing and administration.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Payroll | `payroll_id` | ✅ |
| Pay Period | `pay_period_id` | ✅ |
| Pay Component | `pay_component_id` | ✅ |
| Earning | `earning_id` | ✅ |
| Deduction | `deduction_id` | ✅ |
| Tax Code | `tax_code_id` | ✅ |
| Pay Slip | `pay_slip_id` | |
| Payment Election | `payment_election_id` | |
| Payroll Input | `payroll_input_id` | |
| Tax Authority | `tax_authority_id` | |
| Garnishment | `garnishment_id` | |
| W-4 | `w4_id` | |
| PECI | `peci_id` | |

### Time_Tracking (11 hubs)
Time and attendance management.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Time Entry | `time_entry_id` | ✅ |
| Time Block | `time_block_id` | |
| Time Clock | `time_clock_id` | |
| Time Sheet | `time_sheet_id` | ✅ |
| Time Calculation | `time_calc_id` | |
| Work Schedule | `work_schedule_id` | ✅ |
| Shift | `shift_id` | ✅ |
| Schedule Pattern | `schedule_pattern_id` | |
| Time Off | `time_off_id` | ✅ |
| Overtime | `overtime_id` | |
| Geolocation | `geolocation_id` | |

### Absence (9 hubs)
Leave and absence management.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Absence Type | `absence_type_id` | ✅ |
| Absence Plan | `absence_plan_id` | ✅ |
| Leave of Absence | `leave_of_absence_id` | ✅ |
| Absence Request | `absence_request_id` | |
| Absence Balance | `absence_balance_id` | |
| Absence Accrual | `absence_accrual_id` | |
| Leave Type | `leave_type_id` | |
| Leave Family | `leave_family_id` | |
| Holiday Calendar | `holiday_calendar_id` | |

### Recruiting (12 hubs)
Talent acquisition and recruiting.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Candidate | `candidate_id` | ✅ |
| Job Posting | `job_posting_id` | ✅ |
| Job Application | `job_application_id` | ✅ |
| Interview | `interview_id` | |
| Assessment | `assessment_id` | |
| Offer | `offer_id` | ✅ |
| Recruiting Source | `recruiting_source_id` | |
| Recruiting Stage | `recruiting_stage_id` | |
| Background Check | `background_check_id` | |
| Evergreen Requisition | `evergreen_req_id` | |
| Referral | `referral_id` | |
| Talent Pool | `talent_pool_id` | |

### Talent_Performance (10 hubs)
Performance and talent management.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Performance Review | `performance_review_id` | ✅ |
| Goal | `goal_id` | ✅ |
| Feedback | `feedback_id` | |
| Competency | `competency_id` | ✅ |
| Rating | `rating_id` | |
| Development Plan | `development_plan_id` | |
| Career Interest | `career_interest_id` | |
| Succession Plan | `succession_plan_id` | |
| Talent Review | `talent_review_id` | |
| Calibration | `calibration_id` | |

### Additional Domains

**Onboarding (4 hubs):** Onboarding Event, Onboarding Task, I-9, Provisioning

**Skills_Certifications (8 hubs):** Skill ✅, Skill Level, Certification ✅, License, Education, Degree, Language, Work Experience

**Learning (6 hubs):** Learning Course ✅, Learning Program, Learning Enrollment, Learning Content, Learning Completion, Learning Assignment

**Workforce_Planning (4 hubs):** Workforce Plan, Forecast, Scenario, Headcount Plan

**Business_Process (7 hubs):** Business Process ✅, Business Process Step, Approval Chain, Delegation, Security Group ✅, Domain, Integration System User

**Reporting (5 hubs):** Report, Dashboard, Calculated Field, Worktag ✅, Data Source

**Staffing_Events (11 hubs):** Hire ✅, Termination ✅, Termination Reason ✅, Transfer, Promotion, Demotion, Job Change ✅, Location Change, Compensation Change, Contract Extension, Rehire

---

## Part 2: Workday Architecture

### Object Model
Workday uses a **unified object model** - not separate modules with separate databases. Everything relates back to the Worker object.

```
                    ┌─────────────────┐
                    │     WORKER      │  ← Central Object
                    │   (Person ID)   │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
   ┌─────────┐        ┌───────────┐        ┌──────────┐
   │Position │        │Supervisory│        │   Job    │
   │         │◄──────►│   Org     │◄──────►│ Profile  │
   └─────────┘        └───────────┘        └──────────┘
        │                    │                    │
        ▼                    ▼                    ▼
   ┌─────────┐        ┌───────────┐        ┌──────────┐
   │Comp Plan│        │Cost Center│        │Job Family│
   └─────────┘        └───────────┘        └──────────┘
```

### API Structure

**SOAP API (Primary):**
```
https://{host}.workday.com/ccx/service/{tenant}/{service}/v{version}
```

Services:
- Human_Resources
- Staffing
- Compensation
- Benefits_Administration
- Payroll
- Time_Tracking
- Absence_Management
- Recruiting
- Talent
- Learning

**REST API (Modern):**
```
https://{host}.workday.com/ccx/api/v1/{tenant}/{resource}
```

---

## Part 3: Cross-Vendor Comparison

### Workday vs UKG Family

| Product | Hubs | Shared w/ Workday |
|---------|------|-------------------|
| Workday HCM | 160 | - |
| UKG Pro | 105 | 7 concepts |
| UKG WFM | 113 | 5 concepts |
| UKG Ready | 104 | **25 concepts** |

### Key Overlap Areas

**Workday + UKG Ready (25 shared):**
- Core HCM: company, cost_center, location, position
- Compensation: earning, deduction, currency
- Benefits: benefit_plan, retirement_plan
- Time: time_entry, timesheet, shift, schedule
- Recruiting: candidate, job_requisition, referral
- Skills: skill, certification, training

**Workday + UKG Pro (7 shared):**
- earning, location, pay_group, rating, shift, skill, license

**Workday + UKG WFM (5 shared):**
- cost_center, location, person, schedule_pattern, shift

### Workday-Unique Concepts (129)

Workday has many concepts not found in UKG:
- **Business Process automation** (workflows, approvals)
- **Absence management** (accruals, balances, absence types)
- **Advanced Benefits** (benefit groups, HSA/FSA, elections)
- **Talent Management** (calibration, succession, career interests)
- **Learning Management** (courses, programs, content)
- **Workforce Planning** (scenarios, forecasts)

---

## Part 4: XLR8 Integration

### Product Detection

When data is uploaded, detect Workday via:

| Indicator | Description |
|-----------|-------------|
| Worker_ID patterns | Workday uses specific ID formats |
| Supervisory Organization | Core Workday concept |
| Job Profile hierarchy | Job Profile → Job Family → Job Family Group |
| Business Process references | Workflow/approval data |
| Worktag usage | Workday tagging system |

### Spoke Patterns

```
Worker → Supervisory Organization (reports to)
Worker → Position (fills position)
Worker → Job Profile (assigned job)
Position → Job Profile (based on)
Position → Supervisory Organization (belongs to)
Worker → Cost Center (costed to)
Worker → Compensation Plan (paid via)
Worker → Benefit Election (enrolled in)
Time Entry → Worker (logged by)
Absence Request → Worker (requested by)
Job Requisition → Position (fills)
Candidate → Job Application (applied via)
```

### Column Patterns

| Pattern | Hub |
|---------|-----|
| worker_id, employee_id, wid | worker |
| supervisory_org*, sup_org* | supervisory_org |
| position_id, position_number | position |
| job_profile*, job_code | job_profile |
| cost_center*, cc_* | cost_center |
| location_id, work_location | location |
| company_*, legal_entity* | company |

---

## Deliverables

| File | Description |
|------|-------------|
| `workday_hcm_schema_v1.json` | Full hub definitions (160 hubs) |
| `vendor_comparison.json` | Workday vs UKG comparison |
| `WORKDAY_HCM_EXTRACTION.md` | This document |

---

## Multi-Vendor Summary

| Vendor | Product | Hubs | Focus |
|--------|---------|------|-------|
| **Workday** | HCM | **160** | Enterprise HCM (most comprehensive) |
| UKG | Pro | 105 | Enterprise HCM + Payroll |
| UKG | WFM Dimensions | 113 | Workforce Management |
| UKG | Ready | 104 | Mid-Market Unified |

**Grand Total Across All Vendors: 482 hubs**

Workday is the most comprehensive single-product schema, but UKG's three products combined (322 hubs) cover different market segments.
