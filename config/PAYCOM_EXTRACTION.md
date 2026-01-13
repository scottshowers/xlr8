# Paycom - Domain Model Extraction
**Date:** January 10, 2026  
**Vendor:** Paycom  
**Source:** Paycom website, API documentation, product guides  
**Purpose:** Hub-and-spoke schema for XLR8 universal analysis engine

---

## Executive Summary

| Metric | Count |
|--------|-------|
| **Total Hubs** | 164 |
| **Core Hubs** | 60 |
| **Domains** | 23 |
| **Product Focus** | Mid-market HCM - Single database, employee self-service |

**Key Insight:** Paycom has the **second largest hub count** after Oracle HCM. Its **single-database architecture** and **Beti employee-guided payroll** are unique differentiators. The platform emphasizes employee self-service with data flowing seamlessly across all modules.

---

## Part 1: Paycom Architecture

### Single Database Philosophy

```
┌─────────────────────────────────────────────────────────────────┐
│                    SINGLE DATABASE                               │
│     (One login, one password, no data reentry)                   │
└─────────────────────────────────────────────────────────────────┘
                              │
    ┌─────────────┬───────────┼───────────┬─────────────┐
    │             │           │           │             │
    ▼             ▼           ▼           ▼             ▼
┌────────┐  ┌─────────┐  ┌────────┐  ┌────────┐  ┌──────────┐
│POSITION│  │EMPLOYEE │  │PAYROLL │  │  TIME  │  │  TALENT  │
│MGMT    │  │         │  │ (Beti) │  │& LABOR │  │          │
├────────┤  ├─────────┤  ├────────┤  ├────────┤  ├──────────┤
│Job Desc│  │Self-Svc │  │Earnings│  │Schedule│  │Recruiting│
│Salary  │  │Benefits │  │Deduct  │  │Punches │  │Onboarding│
│Skills  │  │Tax Info │  │Taxes   │  │Accruals│  │LMS       │
│Org Chrt│  │Expenses │  │DDX/ROI │  │Labor $ │  │Perform   │
└────────┘  └─────────┘  └────────┘  └────────┘  └──────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │          BETI                  │
              │  Employee-Guided Payroll       │
              │  Employees fix errors BEFORE   │
              │  payroll submission            │
              └───────────────────────────────┘
```

### API Structure

**Base URL:**
```
https://api.paycom.com
```

**Key Endpoints:**
- `/v1/cl/establishments` - Company/establishment info
- `/v1/cl/locations` - Work locations
- `/v1/cl/category/{code}/detail` - Group information
- `/employees` - Employee records
- `/payrolls` - Payroll data
- `/timeandattendance` - Time entries

**Authentication:** OAuth 2.0 or API SID + Token

---

## Part 2: Key Differentiators

### Beti - Employee-Guided Payroll

Beti revolutionizes payroll by empowering employees to:
- Review their paycheck before submission
- Find and fix errors (hours, expenses, deductions)
- Approve their own payroll
- Reduce post-payroll corrections by 90%

### IWant - AI Command Engine

Industry's first command-driven AI in a single database:
- Natural language queries for employee data
- Searches profiles and dashboards instantly
- Returns accurate, real-time answers
- No hunting through menus

### Position Management

Automated org structure management:
- Auto-generates job descriptions
- Ties pay classes and salary ranges to positions
- Benefits eligibility flows from position
- Accruals and labor rules position-based
- Changes cascade automatically systemwide

### Direct Data Exchange (DDX)

ROI measurement built into the platform:
- Tracks employee self-service usage
- Assigns dollar value to automated tasks
- Shows savings from employee adoption
- Based on Ernst & Young research

---

## Part 3: Domain Structure

### Employee_Core (10 hubs)
Core employee information in single database.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Employee | `employee_id` | ✅ |
| Person | `person_id` | ✅ |
| SSN | `ssn_id` | ✅ |
| Employee_Directory | `employee_directory_id` | |

### Employment (11 hubs)
Employment and job information.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Employment | `employment_id` | ✅ |
| Job | `job_id` | ✅ |
| Job_Title | `job_title_id` | ✅ |
| Position | `position_id` | ✅ |
| Job_Description | `job_description_id` | |
| Employment_Status | `employment_status_id` | ✅ |
| Hire_Date | `hire_date_id` | ✅ |

### Position_Management (5 hubs)
Paycom's unique position management automation.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Position_Management | `position_management_id` | ✅ |
| Salary_Grade | `salary_grade_id` | |
| Salary_Range | `salary_range_id` | |
| Required_Skills | `required_skills_id` | |
| Org_Chart | `org_chart_id` | |

### Payroll (8 hubs)
Payroll processing with Beti.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Payroll | `payroll_id` | ✅ |
| Pay_Period | `pay_period_id` | ✅ |
| Paycheck | `paycheck_id` | ✅ |
| Direct_Deposit | `direct_deposit_id` | ✅ |
| Vault_Pay_Card | `vault_pay_card_id` | |
| Paycom_Pay | `paycom_pay_id` | |
| GL_Concierge | `gl_concierge_id` | |
| Beti | `beti_id` | |

### Additional Domains

**Compensation (10 hubs):** Compensation ✅, Pay_Rate ✅, Annual_Salary, Hourly_Rate, Pay_Type ✅, Pay_Frequency ✅, Compensation_Budget, Merit_Increase, Commission, Bonus

**Earnings (7 hubs):** Earning ✅, Earning_Code ✅, Regular_Pay, Overtime_Pay, Shift_Differential, Tips, Reimbursement

**Deductions (7 hubs):** Deduction ✅, Deduction_Code ✅, Benefit_Deduction, Retirement_Deduction, Garnishment ✅, Child_Support, Loan

**Tax (9 hubs):** Tax ✅, Tax_Status ✅, Federal_Tax ✅, State_Tax ✅, Local_Tax, W4, W2, Form_1099, Tax_Credit

**Expense_Management (5 hubs):** Expense ✅, Expense_Report, Expense_Category, Mileage, Receipt

**Time_Attendance (11 hubs):** Time_Entry ✅, Time_Card ✅, Punch, Schedule ✅, Shift, Attendance ✅, Time_Off ✅, Time_Off_Balance ✅, Accrual, Time_Clock, Geofence

**Labor_Management (4 hubs):** Labor_Allocation ✅, Labor_Code, Labor_Analytics, Overtime_Rule

**Benefits (12 hubs):** Benefit ✅, Benefit_Plan ✅, Benefit_Enrollment ✅, Open_Enrollment, Qualifying_Event, Dependent ✅, Beneficiary, Benefits_To_Carrier, ACA, COBRA, FSA, HSA

**Retirement (4 hubs):** Retirement_Plan ✅, K401_Reporting, Contribution, Employer_Match

**Recruiting (9 hubs):** Job_Requisition ✅, Job_Posting ✅, Candidate ✅, Application ✅, Applicant_Tracking ✅, Interview, Offer, Background_Check, Tax_Credit_Screening

**Onboarding (7 hubs):** Onboarding ✅, New_Hire ✅, I9, E_Verify, Onboarding_Task, Document, E_Signature

**Performance (7 hubs):** Performance_Review ✅, Goal ✅, Self_Review, Manager_Review, Review_360, Merit_Rating, Feedback

**Learning (8 hubs):** Course ✅, Learning_Assignment ✅, Learning_Completion, Quiz, Performance_Evidence, Compliance_Training, Certification ✅, License

**HR_Management (5 hubs):** Personnel_Action_Form ✅, Documents_Checklists, Government_Compliance, EEOC, OFCCP

**Employee_Engagement (4 hubs):** Survey, Ask_Here, MyCom, Announcement

**Self_Service (4 hubs):** Employee_Self_Service ✅, Manager_On_The_Go, Client_Action_Center, IWant

**Reporting (5 hubs):** Report, Custom_Report, Direct_Data_Exchange, Dashboard, Labor_Analytics

---

## Part 4: Cross-Vendor Comparison

### Paycom Overlap with Other HCM Systems

| Comparison | Shared Concepts |
|------------|-----------------|
| Paycom + Paychex | **94** (closest competitor) |
| Paycom + Paylocity | 88 |
| Paycom + ADP WFN | 70 |
| Paycom + Dayforce | 59 |

### Paycom-Unique Concepts (54)

Concepts unique to Paycom include:

**Self-Service & AI:**
- Beti (employee-guided payroll)
- IWant (AI command engine)
- Employee_Self_Service (ESS)
- Manager_On_The_Go
- Client_Action_Center
- Ask_Here (Q&A portal)

**Payroll Features:**
- GL_Concierge (ledger export)
- Vault_Pay_Card
- Paycom_Pay (paper checks)
- Direct_Data_Exchange (ROI)

**Position Management:**
- Position_Management
- Salary_Grade
- Salary_Range
- Required_Skills
- Org_Chart

**Compliance:**
- EEOC
- OFCCP
- Personnel_Action_Form (PAF)
- Tax_Credit_Screening (WOTC)

**Learning:**
- Performance_Evidence (video proof)
- Quiz

---

## Part 5: XLR8 Integration

### Product Detection

Detect Paycom via:

| Indicator | Pattern |
|-----------|---------|
| API URL | `api.paycom.com/*` |
| Key fields | `employeeId`, `establishmentId`, `beti`, `paf` |
| Single database | No data reentry across modules |
| Position-centric | Pay/benefits/accruals tied to position |

### Spoke Patterns

```
Company → Establishment → Employee
Employee → Position → Job_Title/Salary_Grade/Required_Skills
Position → Benefits_Eligibility → Benefit_Plan
Position → Accrual_Rules → Time_Off_Balance
Employee → Paycheck (via Beti approval)
Paycheck → Earning/Deduction
Employee → Time_Card → Time_Entry
Employee → Expense → Expense_Category
Candidate → Application → Job_Requisition
Employee → Learning_Assignment → Course
Employee → Performance_Review → Goal
```

### Column Patterns

| Pattern | Hub |
|---------|-----|
| employee_id, emp_id, employeeid | employee |
| establishment_id, est_id | establishment |
| position_id, pos_id | position |
| paycheck_id, check_id | paycheck |
| paf_id, personnel_action | paf |
| earning_code, earn_cd | earning_code |
| deduction_code, ded_cd | deduction_code |
| time_card_id, timecard | time_card |

---

## Part 6: Product Modules

### Core Modules (Included)
- Payroll (Beti)
- HR Management
- Employee Self-Service
- Tax Management

### Additional Modules
- Time and Labor Management
- Talent Acquisition (ATS)
- Talent Management
- Learning Management (Paycom Learning)
- Benefits Administration
- Position Management
- Expense Management
- Garnishment Administration
- 401(k) Reporting
- Enhanced ACA
- COBRA Administration

---

## Part 7: API Endpoints Summary

### Company/Org APIs
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/cl/establishments` | GET | Company info |
| `/v1/cl/locations` | GET | Work locations |
| `/v1/cl/category/{code}/detail` | GET | Groups |

### Employee APIs
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/employees` | GET/POST | Employee list |
| `/employees/{id}` | GET/PUT/DELETE | Single employee |

### Payroll APIs
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/payrolls` | GET/POST | Payroll runs |
| `/payrolls/{id}` | GET | Specific payroll |

### Time APIs
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/timeandattendance` | GET/POST | Time entries |

---

## Deliverables

| File | Description |
|------|-------------|
| `paycom_schema_v1.json` | Full hub definitions (164 hubs) |
| `paycom_comparison.json` | Cross-vendor overlap analysis |
| `PAYCOM_EXTRACTION.md` | This document |

---

## Updated HCM Product Summary

| Product | Hubs | Vendor |
|---------|------|--------|
| Oracle HCM | 173 | Oracle |
| **Paycom** | **164** | **Paycom** |
| Workday HCM | 160 | Workday |
| Dayforce | 157 | Ceridian |
| Paylocity | 142 | Paylocity |
| ADP WFN | 138 | ADP |
| SuccessFactors | 137 | SAP |
| Paychex Flex | 127 | Paychex |
| UKG WFM | 113 | UKG |
| UKG Pro | 105 | UKG |
| UKG Ready | 104 | UKG |
| **TOTAL** | **1,520** | **11 products** |

---

## Summary

Paycom brings **164 hubs** across 23 HCM domains - the **second largest extraction** after Oracle HCM. Key strengths:

1. **Single Database** - No data silos, no reentry, seamless flow
2. **Beti** - Revolutionary employee-guided payroll reduces errors 90%
3. **Position Management** - Org structure automation unique to Paycom
4. **IWant AI** - Command-driven data retrieval
5. **Direct Data Exchange** - Built-in ROI measurement
6. **Self-Service Focus** - Employee empowerment at core

Paycom's largest overlap is with **Paychex (94 shared)**, reflecting similar mid-market positioning and comprehensive HCM suites.
