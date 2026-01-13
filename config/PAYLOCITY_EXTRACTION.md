# Paylocity - Domain Model Extraction
**Date:** January 10, 2026  
**Vendor:** Paylocity  
**Source:** Paylocity Developer Portal, API documentation, product docs  
**Purpose:** Hub-and-spoke schema for XLR8 universal analysis engine

---

## Executive Summary

| Metric | Count |
|--------|-------|
| **Total Hubs** | 142 |
| **Core Hubs** | 51 |
| **Domains** | 19 |
| **Product Focus** | SMB HCM - Payroll, HR, Time, Benefits, Talent |

**Key Insight:** Paylocity uses an **Employee-centric architecture** with Company-level configuration. The platform emphasizes SMB usability with three product suites: Web Pay (Payroll), Guide (Onboarding), and Perform (Performance).

---

## Part 1: Paylocity Architecture

### Employee-Centric Data Model

```
┌─────────────────────────────────────────────────────────────────┐
│                         COMPANY                                  │
│        (Company ID - employer context)                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         EMPLOYEE                                 │
│        (Employee ID - unique per company)                        │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  DEMOGRAPHICS │    │  EMPLOYMENT   │    │   BENEFITS    │
│               │    │               │    │               │
├───────────────┤    ├───────────────┤    ├───────────────┤
│ Legal Name    │    │ Position      │    │ Enrollments   │
│ Address       │    │ Department    │    │ Dependents    │
│ SSN (masked)  │    │ Job Code      │    │ Elections     │
│ Contacts      │    │ Pay Rate      │    │ ACA Status    │
└───────────────┘    └───────────────┘    └───────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│   PAYROLL     │    │  TIME & ATT   │    │    TALENT     │
│               │    │               │    │               │
├───────────────┤    ├───────────────┤    ├───────────────┤
│ Earnings      │    │ Time Cards    │    │ Recruiting    │
│ Deductions    │    │ Schedules     │    │ Onboarding    │
│ Tax           │    │ Time Off      │    │ Performance   │
│ Pay Statements│    │ Accruals      │    │ Learning      │
└───────────────┘    └───────────────┘    └───────────────┘
```

### API Structure

**Base URL:**
```
https://api.paylocity.com/api/v2/companies/{companyId}
```

**Key Endpoints:**
- `/employees` - Employee demographics
- `/employees/{employeeId}/earnings` - Earnings setup
- `/employees/{employeeId}/deductions` - Deductions setup
- `/payroll/v1/pay-statements` - Pay stubs
- `/time-entry` - Time tracking

**Authentication:** OAuth 2.0 Client Credentials (60-minute token expiry)

**Rate Limits:** 40,000 calls/hour

---

## Part 2: Product Suites

### Paylocity Web Pay (Core HR & Payroll)
- Payroll processing with tax filing
- Employee demographics
- Benefits administration
- Direct deposit management
- Reporting and analytics

### Paylocity Guide (Onboarding & Training)
- Digital onboarding workflows
- I-9 and E-Verify integration
- Document management
- Learning Management System (LMS)
- Compliance training

### Paylocity Perform (Performance Management)
- Goal setting and tracking
- Performance reviews
- 360-degree feedback
- Competency management
- Career development

---

## Part 3: Domain Structure

### Employee_Core (10 hubs)
Core employee information (Employee API).

| Hub | Semantic Type | Core | Description |
|-----|---------------|------|-------------|
| Employee | `employee_id` | ✅ | Core employee record |
| Employee_Demographic | `employee_demographic_id` | ✅ | Demographic data |
| SSN | `ssn_id` | ✅ | Social Security Number (masked) |
| Legal_Name | `legal_name_id` | | Legal name |
| Preferred_Name | `preferred_name_id` | | Preferred name |
| Birth_Date | `birth_date_id` | | Date of birth |

### Employment (11 hubs)
Employment and position information.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Employment | `employment_id` | ✅ |
| Position | `position_id` | ✅ |
| Job_Title | `job_title_id` | ✅ |
| Job_Code | `job_code_id` | ✅ |
| Employee_Status | `employee_status_id` | ✅ |
| Employment_Type | `employment_type_id` | ✅ |
| Hire_Date | `hire_date_id` | ✅ |

### Organization (10 hubs)
Company and organizational structure.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Company | `company_id` | ✅ |
| Department | `department_id` | ✅ |
| Location | `location_id` | ✅ |
| Cost_Center | `cost_center_id` | ✅ |
| Cost_Center_1 | `cost_center_1_id` | |
| Cost_Center_2 | `cost_center_2_id` | |
| Cost_Center_3 | `cost_center_3_id` | |

### Payroll (9 hubs)
Payroll processing.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Payroll | `payroll_id` | ✅ |
| Pay_Group | `pay_group_id` | ✅ |
| Pay_Frequency | `pay_frequency_id` | ✅ |
| Pay_Period | `pay_period_id` | ✅ |
| Pay_Statement | `pay_statement_id` | ✅ |
| Direct_Deposit | `direct_deposit_id` | ✅ |

### Earnings (9 hubs)
Earnings and pay codes.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Earning | `earning_id` | ✅ |
| Earning_Code | `earning_code_id` | ✅ |
| Earning_Type | `earning_type_id` | ✅ |
| Regular_Earning | `regular_earning_id` | |
| Overtime_Earning | `overtime_earning_id` | |
| Bonus | `bonus_id` | |

### Deductions (8 hubs)
Payroll deductions.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Deduction | `deduction_id` | ✅ |
| Deduction_Code | `deduction_code_id` | ✅ |
| Deduction_Type | `deduction_type_id` | ✅ |
| Garnishment | `garnishment_id` | |
| Retirement_Deduction | `retirement_deduction_id` | |
| Loan | `loan_id` | |

### Additional Domains

**Tax (8 hubs):** Tax ✅, Tax_Code ✅, Federal_Tax ✅, State_Tax ✅, Local_Tax, FICA, SUI, W4

**Time_Attendance (10 hubs):** Time_Entry ✅, Time_Card ✅, Punch, Schedule ✅, Shift, Overtime, Time_Off ✅, Time_Off_Balance ✅, Accrual, Geofence

**Benefits (10 hubs):** Benefit ✅, Benefit_Plan ✅, Benefit_Election, Dependent ✅, Beneficiary, Open_Enrollment, Life_Event, ACA_Status, FSA, HSA

**Recruiting (9 hubs):** Requisition ✅, Job_Posting ✅, Candidate ✅, Application ✅, Interview, Offer, Background_Check, Screening_Package, Assessment

**Onboarding (7 hubs):** Onboarding ✅, Onboarding_Task, New_Hire ✅, I9, E_Verify, Document, Acknowledgment

**Performance (6 hubs):** Performance_Review ✅, Goal ✅, Competency, Rating, Feedback, Review_Cycle

**Learning (6 hubs):** Course ✅, Learning_Assignment, Learning_Completion, Certification, Training_Content, Compliance_Training

**Employee_Engagement (6 hubs):** Survey, Survey_Response, Recognition, Community_Post, Announcement, Pulse_Check

**Custom_Fields (3 hubs):** Custom_Field ✅, Custom_Field_Value, Custom_Category

---

## Part 4: Cross-Vendor Comparison

### Paylocity Overlap with Other HCM Systems

| Comparison | Shared Concepts |
|------------|-----------------|
| Paylocity + ADP WFN | **74** (closest competitor) |
| Paylocity + Dayforce | 61 |
| Paylocity + Workday HCM | 40 |
| Paylocity + Oracle HCM | 40 |
| Paylocity + SuccessFactors | 38 |

### Commonly Shared Concepts

Paylocity shares these core HCM concepts with competitors:
- Employee, Position, Job_Code, Department
- Company, Location, Cost_Center
- Pay_Statement, Earning, Deduction
- Benefit_Plan, Benefit_Election, Dependent
- Time_Entry, Schedule, Time_Off
- Candidate, Application, Job_Posting
- Performance_Review, Goal

### Paylocity-Unique Concepts (51)

Concepts unique to Paylocity include:
- **Cost Centers:** Cost_Center_1, Cost_Center_2, Cost_Center_3 (hierarchical)
- **Employee Engagement:** Community_Post, Pulse_Check, Announcement, Recognition
- **Compliance:** Compliance_Training, ACA_Status, Acknowledgment
- **Payroll Details:** Check_Date, Pay_Entry, Calculation_Code
- **Custom:** Custom_Field, Custom_Field_Value, Custom_Category
- **Screening:** Screening_Package, Assessment, Billing_Code

---

## Part 5: XLR8 Integration

### Product Detection

Detect Paylocity via:

| Indicator | Pattern |
|-----------|---------|
| API URL | `api.paylocity.com/*` |
| Key fields | `companyId`, `employeeId`, `earningCode`, `deductionCode` |
| DET codes | `D` (Deduction), `E` (Earning), `T` (Tax) |
| Custom fields | Company-specific configurations |

### Spoke Patterns

```
Company → Employee (employs)
Employee → Employment (has assignment)
Employment → Position (holds position)
Employment → Department (belongs to)
Employment → Job_Code (classified as)
Employee → Earning (has earnings)
Earning → Earning_Code (of type)
Employee → Deduction (has deductions)
Deduction → Deduction_Code (of type)
Employee → Pay_Statement (receives pay)
Employee → Time_Entry (records time)
Employee → Benefit (enrolled in)
Benefit → Benefit_Plan (plan type)
Benefit → Dependent (covers)
Candidate → Application (submits)
Application → Requisition (applies to)
```

### Column Patterns

| Pattern | Hub |
|---------|-----|
| company_id, companyid | company |
| employee_id, employeeid, emp_id | employee |
| earning_code, earn_code, det_e | earning_code |
| deduction_code, ded_code, det_d | deduction_code |
| tax_code, det_t | tax_code |
| department_id, dept_id, dept | department |
| cost_center, cost_center_1/2/3 | cost_center |
| job_code, job_cd | job_code |
| pay_group, paygroup | pay_group |

---

## Part 6: Paylocity-Specific Concepts

### DET Codes (Deduction/Earning/Tax)

Paylocity categorizes pay components as:
- **D** - Deductions (benefits, garnishments, retirement)
- **E** - Earnings (regular, OT, bonus)
- **T** - Taxes (federal, state, local)

Each code has a `detType` determining taxability and W-2 treatment.

### Calculation Codes

Determine deduction calculation method:
- **Flat Amount** - Fixed dollar
- **Percentage of Gross** - % of gross pay
- **Percentage of Net** - % of net pay
- **Garnishment** - 15% of gross (if > 45x min wage)
- **Configurable Garnishment** - State-specific

### Cost Center Hierarchy

Supports multi-level cost allocation:
- Cost_Center_1 (primary)
- Cost_Center_2 (secondary)
- Cost_Center_3 (tertiary)

### Webhooks

Real-time event notifications:
- `employee.hired` - New hire
- `employee.terminated` - Termination
- `employee.transferred` - Transfer
- `payroll.processed` - Payroll complete

---

## Part 7: API Endpoints Summary

### Employee APIs
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/employees` | GET | All employees |
| `/employees/{id}` | GET | Single employee |
| `/employees/{id}/demographics` | GET | Demographics |
| `/employees/{id}/earnings` | GET/POST | Earnings setup |
| `/employees/{id}/deductions` | GET/POST | Deductions setup |

### Payroll APIs
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/payroll/pay-statements` | GET | Pay stubs |
| `/payroll/pay-entry` | POST | One-time pay data |
| `/payroll/summary` | GET | Payroll totals |

### Company APIs
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/companies/{id}/codes/earnings` | GET | Earning codes |
| `/companies/{id}/codes/deductions` | GET | Deduction codes |
| `/companies/{id}/custom-fields` | GET | Custom fields |

---

## Deliverables

| File | Description |
|------|-------------|
| `paylocity_schema_v1.json` | Full hub definitions (142 hubs) |
| `paylocity_comparison.json` | Cross-vendor overlap analysis |
| `PAYLOCITY_EXTRACTION.md` | This document |

---

## Updated HCM Product Summary

| Product | Hubs | Vendor |
|---------|------|--------|
| Oracle HCM | 173 | Oracle |
| Workday HCM | 160 | Workday |
| Dayforce | 157 | Ceridian |
| **Paylocity** | **142** | **Paylocity** |
| ADP WFN | 138 | ADP |
| SuccessFactors | 137 | SAP |
| UKG WFM | 113 | UKG |
| UKG Pro | 105 | UKG |
| UKG Ready | 104 | UKG |
| **TOTAL** | **1,229** | **9 products** |

---

## Summary

Paylocity brings **142 hubs** across 19 HCM domains with strengths in:

1. **SMB Focus** - Designed for 20-1,000 employee companies
2. **Unified Platform** - HR, Payroll, Benefits, Time, Talent in one system
3. **Employee Engagement** - Community features, surveys, recognition
4. **Modern LMS** - Built-in learning management
5. **Flexible Configuration** - Company-specific earning/deduction codes

Paylocity's largest overlap is with **ADP WFN (74 shared)**, reflecting similar mid-market positioning and payroll-centric architecture.
