# ADP Workforce Now - Domain Model Extraction
**Date:** January 10, 2026  
**Vendor:** ADP  
**Source:** ADP Developer Resources, API documentation, product docs  
**Purpose:** Hub-and-spoke schema for XLR8 universal analysis engine

---

## Executive Summary

| Metric | Count |
|--------|-------|
| **Total Hubs** | 138 |
| **Core Hubs** | 50 |
| **Domains** | 17 |
| **Product Focus** | Mid-market HCM - HR, Payroll, Benefits, Time, Talent |

**Key Insight:** ADP Workforce Now uses an **event-driven, Worker-centric architecture** with Work Assignment as the primary employment record. The API follows a RESTful pattern with OAuth 2.0 authentication.

---

## Part 1: ADP Workforce Now Architecture

### Worker-Centric Data Model

```
┌─────────────────────────────────────────────────────────────────┐
│                         WORKER                                   │
│        (Associate OID - unique identifier)                       │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│    PERSON     │    │WORK ASSIGNMENT│    │   BENEFITS    │
│               │    │               │    │               │
├───────────────┤    ├───────────────┤    ├───────────────┤
│ Legal Name    │    │ Position      │    │ Enrollments   │
│ Demographics  │    │ Job Code      │    │ Dependents    │
│ Addresses     │    │ Department    │    │ Elections     │
│ Contacts      │    │ Compensation  │    │ Carriers      │
└───────────────┘    └───────────────┘    └───────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│   PAYROLL     │    │  TIME & ATT   │    │    TALENT     │
│               │    │               │    │               │
├───────────────┤    ├───────────────┤    ├───────────────┤
│ Pay Data      │    │ Time Cards    │    │ Recruiting    │
│ Earnings      │    │ Schedules     │    │ Performance   │
│ Deductions    │    │ Absences      │    │ Learning      │
│ Tax           │    │ Accruals      │    │ Onboarding    │
└───────────────┘    └───────────────┘    └───────────────┘
```

### API Structure

**Base URL:**
```
https://api.adp.com/hr/v2/workers
```

**Key APIs:**
- `/hr/v2/workers` - Worker demographics and employment
- `/payroll/v1/pay-data-input` - Payroll batch data
- `/time/v1/time-cards` - Time and attendance
- `/events/hr/v1/worker.*` - Workforce events

**Authentication:** OAuth 2.0 with mTLS certificate option

---

## Part 2: Domain Structure

### Worker_Core (9 hubs)
Core worker/employee information (Workers API).

| Hub | Semantic Type | Core | Description |
|-----|---------------|------|-------------|
| Worker | `worker_id` | ✅ | Core employee/contractor record |
| Person | `person_id` | ✅ | Personal information |
| Associate_ID | `associate_oid` | ✅ | ADP associate OID |
| Legal_Name | `legal_name_id` | | Legal name record |
| Preferred_Name | `preferred_name_id` | | Preferred/display name |
| National_ID | `national_id` | ✅ | SSN/national identifier |

### Work_Assignment (11 hubs)
Employment/work assignment information.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Work_Assignment | `work_assignment_id` | ✅ |
| Position | `position_id` | ✅ |
| Job | `job_id` | ✅ |
| Job_Code | `job_code_id` | ✅ |
| Job_Family | `job_family_id` | |
| Job_Level | `job_level_id` | |
| Worker_Type | `worker_type_id` | ✅ |
| Assignment_Status | `assignment_status_id` | ✅ |
| Hire_Date | `hire_date_id` | |
| Termination_Date | `termination_date_id` | |
| Seniority_Date | `seniority_date_id` | |

### Organization (11 hubs)
Organizational structure.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Company | `company_id` | ✅ |
| Company_Code | `company_code_id` | ✅ |
| Department | `department_id` | ✅ |
| Department_Code | `department_code_id` | |
| Cost_Center | `cost_center_id` | ✅ |
| Location | `location_id` | ✅ |
| Business_Unit | `business_unit_id` | |
| Division | `division_id` | |
| Region | `region_id` | |
| Home_Organization | `home_organization_id` | |
| Reports_To | `reports_to_id` | |

### Payroll (9 hubs)
Payroll processing.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Payroll_Profile | `payroll_profile_id` | ✅ |
| Payroll_Group_Code | `payroll_group_code_id` | ✅ |
| Payroll_File_Number | `payroll_file_number_id` | ✅ |
| Pay_Cycle | `pay_cycle_id` | ✅ |
| Pay_Period | `pay_period_id` | ✅ |
| Pay_Statement | `pay_statement_id` | ✅ |
| Payroll_Run | `payroll_run_id` | |
| Direct_Deposit | `direct_deposit_id` | |
| Payroll_Region_Code | `payroll_region_code_id` | |

### Earnings (9 hubs)
Earnings and pay data.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Earning | `earning_id` | ✅ |
| Earning_Code | `earning_code_id` | ✅ |
| Pay_Data_Input | `pay_data_input_id` | ✅ |
| Regular_Earning | `regular_earning_id` | |
| Overtime_Earning | `overtime_earning_id` | |
| Bonus | `bonus_id` | |
| Commission | `commission_id` | |
| Tip_Amount | `tip_amount_id` | |
| Reportable_Earning | `reportable_earning_id` | |

### Additional Domains

**Deductions (6 hubs):** Deduction ✅, Deduction_Code ✅, Deduction_Instruction, Garnishment, Loan_Repayment, Reimbursement

**Tax (8 hubs):** Tax_Withholding ✅, Federal_Tax ✅, State_Tax ✅, Local_Tax, Tax_Profile, W4, W2, Form_1099

**Time_Attendance (10 hubs):** Time_Card ✅, Time_Entry ✅, Punch, Schedule ✅, Shift, Absence ✅, Time_Off_Request, Time_Off_Balance ✅, Accrual_Policy, Attendance_Policy

**Benefits (10 hubs):** Benefit_Plan ✅, Benefit_Enrollment ✅, Benefit_Election, Coverage_Level, Dependent ✅, Beneficiary, Open_Enrollment, Life_Event, Carrier, ACA_Compliance

**Recruiting (8 hubs):** Job_Requisition ✅, Job_Posting ✅, Candidate ✅, Application ✅, Interview, Offer, Background_Check, Applicant_Source

**Onboarding (6 hubs):** Onboarding ✅, Onboarding_Task, I9, E_Verify, New_Hire_Packet, Applicant_Onboard

**Performance (6 hubs):** Performance_Review ✅, Goal ✅, Competency, Rating, Feedback, Development_Plan

**Learning (5 hubs):** Course ✅, Learning_Assignment, Learning_Completion, Certification, License

**Events (8 hubs):** Worker_Hire ✅, Worker_Termination ✅, Worker_Rehire, Job_Change, Transfer, Promotion, Leave_of_Absence, Return_from_Leave

**Compensation (8 hubs):** Base_Remuneration ✅, Pay_Rate ✅, Pay_Grade, Pay_Range, Compensation_Plan, Annual_Benefit_Base, FLSA_Status, Pay_Frequency ✅

---

## Part 3: Cross-Vendor Comparison

### ADP WFN Overlap with Other HCM Systems

| Comparison | Shared Concepts |
|------------|-----------------|
| ADP + Dayforce | 70 |
| ADP + Oracle HCM | 50 |
| ADP + Workday HCM | 49 |
| ADP + SuccessFactors | 44 |
| ADP + UKG Ready | 26 |
| ADP + UKG Pro | 10 |

### Commonly Shared Concepts

ADP shares these core HCM concepts with most competitors:
- Worker/Employee, Position, Job, Department
- Company, Location, Cost_Center
- Pay_Statement, Earning, Deduction
- Benefit_Plan, Benefit_Enrollment, Dependent
- Time_Entry, Schedule, Absence
- Candidate, Application, Job_Requisition
- Performance_Review, Goal, Competency

### ADP-Unique Concepts (51)

Concepts unique to ADP Workforce Now include:
- **Payroll-specific:** Associate_OID, Payroll_File_Number, Payroll_Group_Code, Company_Code, Department_Code
- **Tax:** Federal_Tax, State_Tax, Local_Tax (granular tax entities)
- **Compliance:** I9, E_Verify, ACA_Compliance, EEO_Report, VETS_Report
- **Pay Data:** Pay_Data_Input, Base_Remuneration, Tip_Amount, Commission
- **Benefits:** Annual_Benefit_Base, Life_Event, Carrier
- **Time:** Accrual_Policy, Attendance_Policy

---

## Part 4: XLR8 Integration

### Product Detection

Detect ADP Workforce Now via:

| Indicator | Pattern |
|-----------|---------|
| API URL | `api.adp.com/*` |
| Key fields | `associateOID`, `workAssignment`, `payrollFileNumber` |
| Company code | Numeric company codes (e.g., "ABC") |
| File number | `payrollFileNumber` format |

### Spoke Patterns

```
Worker → Work_Assignment (has employment)
Work_Assignment → Position (fills position)
Work_Assignment → Department (belongs to)
Work_Assignment → Job_Code (classified as)
Work_Assignment → Company (employed by)
Worker → Benefit_Enrollment (enrolled in)
Benefit_Enrollment → Benefit_Plan (plan type)
Benefit_Enrollment → Dependent (covers)
Worker → Pay_Statement (receives pay)
Pay_Statement → Earning (includes earnings)
Pay_Statement → Deduction (includes deductions)
Worker → Time_Card (tracks time)
Time_Card → Time_Entry (has punches)
Candidate → Application (submits)
Application → Job_Requisition (applies to)
```

### Column Patterns

| Pattern | Hub |
|---------|-----|
| associate_oid, aoid, worker_id | worker |
| work_assignment_*, was_* | work_assignment |
| company_code, co_code | company_code |
| department_code, dept_code | department_code |
| payroll_file_*, file_number | payroll_file_number |
| earning_code, earn_code | earning_code |
| deduction_code, ded_code | deduction_code |
| job_code, job_cd | job_code |
| pay_group, payroll_group | payroll_group_code |

---

## Part 5: ADP-Specific Concepts

### Associate OID

ADP uses Associate OID (AOID) as the unique worker identifier:
- Format: Alphanumeric string
- Persists across rehires
- Used in all API calls

### Payroll File Number

Unique identifier for payroll processing:
- Company-specific
- Links to tax and pay records
- Used for pay data input

### Event-Driven Architecture

ADP uses events for workforce changes:
```
worker.hire → New employee added
worker.termination → Employee terminated
worker.rehire → Employee rehired
worker.legal-name.change → Name changed
worker.work-assignment.change → Job changed
```

### Pay Data Input API

Batch payroll data entry:
- Earnings (regular, OT, bonus)
- Deductions (pre-tax, post-tax)
- Memos (non-monetary)
- Reimbursements

---

## Part 6: Product Tiers

### ADP Workforce Now Packages

| Package | Features |
|---------|----------|
| **Select** | Payroll + HR basics |
| **Plus** | + Benefits Administration |
| **Premium** | + Time & Attendance |

### Add-On Modules

- Talent Acquisition/Recruitment
- Performance Management
- Compensation Management
- Learning Management
- Enhanced Analytics
- Voice of the Employee

---

## Deliverables

| File | Description |
|------|-------------|
| `adp_wfn_schema_v1.json` | Full hub definitions (138 hubs) |
| `adp_comparison.json` | Cross-vendor overlap analysis |
| `ADP_WFN_EXTRACTION.md` | This document |

---

## Updated HCM Product Summary

| Product | Hubs | Vendor |
|---------|------|--------|
| Oracle HCM | 173 | Oracle |
| Workday HCM | 160 | Workday |
| Dayforce | 157 | Ceridian |
| **ADP WFN** | **138** | **ADP** |
| SuccessFactors | 137 | SAP |
| UKG WFM | 113 | UKG |
| UKG Pro | 105 | UKG |
| UKG Ready | 104 | UKG |
| **TOTAL** | **1,087** | **8 products** |

---

## Summary

ADP Workforce Now brings **138 hubs** across 17 HCM domains with strengths in:

1. **Payroll Processing** - Deep payroll with file numbers, pay groups, tax withholding
2. **Compliance** - Built-in I-9, E-Verify, ACA, EEO reporting
3. **Mid-Market Focus** - Scalable from 50 to 1,000+ employees
4. **Event-Driven API** - Real-time workforce change notifications
5. **Tax Expertise** - Multi-state tax calculations and filing

ADP's largest overlaps are with **Dayforce (70 shared)** and **Oracle HCM (50 shared)**, reflecting similar mid-market to enterprise positioning.
