# Paycor - Domain Model Extraction
**Date:** January 10, 2026  
**Vendor:** Paycor  
**Source:** Paycor website, API documentation, developer portal  
**Purpose:** Hub-and-spoke schema for XLR8 universal analysis engine

---

## Executive Summary

| Metric | Count |
|--------|-------|
| **Total Hubs** | 174 |
| **Core Hubs** | 62 |
| **Domains** | 25 |
| **Product Focus** | Mid-market HCM - 10-1000 employees, AI-powered |

**Key Insight:** Paycor has the **largest hub count** of all extracted products. Their "Intelligent HCM" AI platform, 140+ APIs, and industry-specific solutions (Healthcare, Manufacturing, Restaurant) differentiate them in the mid-market. Note: Paycor merged with Paychex in 2024-2025.

---

## Part 1: Paycor Architecture

### Platform Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    INTELLIGENT HCM                               │
│            AI-Powered People Management                          │
└─────────────────────────────────────────────────────────────────┘
                              │
    ┌─────────────┬───────────┼───────────┬─────────────┐
    │             │           │           │             │
    ▼             ▼           ▼           ▼             ▼
┌────────┐  ┌─────────┐  ┌────────┐  ┌────────┐  ┌──────────┐
│HR &    │  │WORKFORCE│  │TALENT  │  │TALENT  │  │BENEFITS  │
│PAYROLL │  │MGMT     │  │ACQUIRE │  │MGMT    │  │ADMIN     │
├────────┤  ├─────────┤  ├────────┤  ├────────┤  ├──────────┤
│Payroll │  │Time     │  │ATS     │  │Perform │  │Enrollment│
│Tax     │  │Schedule │  │AI Src  │  │Goals   │  │Carriers  │
│Expense │  │Labor    │  │Onboard │  │LMS     │  │ACA/COBRA │
│EWA     │  │Attend   │  │Docs    │  │Career  │  │FSA/HSA   │
└────────┘  └─────────┘  └────────┘  └────────┘  └──────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │      ANALYTICS & AI            │
              │  Predictive insights           │
              │  Turnover analysis             │
              │  Workforce benchmarking        │
              └───────────────────────────────┘
```

### API Structure

**Base URL:**
```
https://api.paycor.com/v1
```

**Authentication:** OAuth 2.0 (Client Credentials)

**Key Endpoints:**
- `/employees` - Employee records
- `/employees/{id}` - Single employee
- `/legal-entities` - Company/legal entity info
- `/payrolls` - Payroll data
- `/time-cards` - Time entries

**Pagination:** Continuation token-based

---

## Part 2: Key Differentiators

### Intelligent HCM (AI Platform)

Paycor's AI-powered features:
- Predictive analytics for turnover risk
- AI-powered candidate sourcing
- Automated workflow recommendations
- Mobile-first AI assistant
- Data-driven workforce insights

### 140+ APIs

Extensive API coverage:
- Employee lifecycle APIs
- Payroll processing APIs
- Time and attendance APIs
- Benefits administration APIs
- Recruiting and onboarding APIs
- Custom reporting APIs

### Earned Wage Access (EWA)

Employees can access earned wages before payday:
- Real-time earned wage calculation
- Mobile-first access
- Reduces employee financial stress
- No employer cost

### Industry-Specific Solutions

Tailored for:
- **Healthcare:** PBJ reporting, credential tracking, shift management
- **Manufacturing:** Labor distribution, overtime management
- **Restaurant:** Tip management, scheduling, labor cost control
- **Professional Services:** Project tracking, utilization

---

## Part 3: Domain Structure

### Employee_Core (10 hubs)
Core employee information.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Employee | `employee_id` | ✅ |
| Person | `person_id` | ✅ |
| Legal_Entity | `legal_entity_id` | ✅ |
| SSN | `ssn_id` | ✅ |

### Employment (12 hubs)
Employment and job information.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Employment | `employment_id` | ✅ |
| Job | `job_id` | ✅ |
| Job_Title | `job_title_id` | ✅ |
| Position | `position_id` | ✅ |
| Employment_Status | `employment_status_id` | ✅ |
| Hire_Date | `hire_date_id` | ✅ |
| Status | `status_id` | ✅ |

### Time_Attendance (13 hubs)
Time tracking with Paycor Time.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Time_Entry | `time_entry_id` | ✅ |
| Time_Card | `time_card_id` | ✅ |
| Mobile_Punch | `mobile_punch_id` | |
| Geo_Validation | `geo_validation_id` | |
| Schedule | `schedule_id` | ✅ |
| Shift_Swap | `shift_swap_id` | |
| Attendance | `attendance_id` | ✅ |
| Time_Off | `time_off_id` | ✅ |
| Time_Off_Balance | `time_off_balance_id` | ✅ |

### Payroll (8 hubs)
Payroll processing.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Payroll | `payroll_id` | ✅ |
| Pay_Period | `pay_period_id` | ✅ |
| Paycheck | `paycheck_id` | ✅ |
| Direct_Deposit | `direct_deposit_id` | ✅ |
| Payroll_Journal | `payroll_journal_id` | |
| Earned_Wage_Access | `earned_wage_access_id` | |

### Additional Domains

**Organization (8 hubs):** Company ✅, Department ✅, Division, Location ✅, Cost_Center, Supervisor ✅, Group, Org_Level

**Compensation (9 hubs):** Compensation ✅, Pay_Rate ✅, Annual_Salary, Hourly_Rate, Pay_Type ✅, Pay_Frequency ✅, Pay_Grade, Bonus, Commission

**Earnings (7 hubs):** Earning ✅, Earning_Code ✅, Regular_Pay, Overtime_Pay, Shift_Differential, Holiday_Pay, PTO_Pay

**Deductions (7 hubs):** Deduction ✅, Deduction_Code ✅, Benefit_Deduction, Retirement_Deduction, Garnishment ✅, Child_Support, Loan

**Tax (9 hubs):** Tax ✅, Tax_Filing ✅, Federal_Tax ✅, State_Tax ✅, Local_Tax, W4, W2, Tax_Credit, ACA_Compliance

**Expense_Management (5 hubs):** Expense ✅, Expense_Report, Expense_Category, Mileage, Reimbursement

**Scheduling (5 hubs):** Scheduling ✅, Schedule_Template, Open_Shift, Schedule_Notification, Budget_Planning

**Labor_Management (4 hubs):** Labor_Distribution ✅, Labor_Code, Labor_Cost, Overtime_Management

**Benefits (12 hubs):** Benefit ✅, Benefit_Plan ✅, Benefit_Enrollment ✅, Open_Enrollment, Life_Event, Dependent ✅, Beneficiary, Carrier_Connection, ACA, COBRA, FSA, HSA

**Retirement (4 hubs):** Retirement_Plan ✅, K401_Plan, Contribution, Employer_Match

**Recruiting (10 hubs):** Job_Requisition ✅, Job_Posting ✅, Candidate ✅, Application ✅, Applicant_Tracking ✅, Interview, Offer, Background_Check, AI_Sourcing, Hiring_Tax_Credit

**Onboarding (7 hubs):** Onboarding ✅, New_Hire ✅, I9, E_Verify, Onboarding_Task, Document, Offer_Letter

**Performance (6 hubs):** Performance_Review ✅, Goal ✅, Goal_Setting, Feedback, Competency, Rating

**Learning (6 hubs):** Course ✅, Learning_Assignment ✅, Learning_Completion, Certification ✅, Compliance_Training, Training_Program

**Talent_Development (4 hubs):** Career_Path, Succession_Plan, Skill, Development_Plan

**HR_Management (5 hubs):** Personnel_Action ✅, HR_Workflow, Document_Management, Compliance, EEO

**Employee_Self_Service (4 hubs):** Employee_Self_Service ✅, Manager_Self_Service, Mobile_App, Pay_Stub_Access

**Analytics (6 hubs):** Report, Custom_Report, Dashboard, Turnover_Analysis, Benchmarking, Workforce_Insights

**Intelligent_HCM (4 hubs):** Intelligent_HCM, AI_Assistant, Predictive_Analytics, Automated_Workflow

**Integration (4 hubs):** Integration, API, Webhook, Marketplace

---

## Part 4: Cross-Vendor Comparison

### Paycor Overlap with Other HCM Systems

| Comparison | Shared Concepts |
|------------|-----------------|
| Paycor + Paycom | **114** (closest competitor) |
| Paycor + Paychex | 95 |

### Paycor-Unique Concepts (57)

Concepts unique to Paycor include:

**AI & Analytics:**
- Intelligent_HCM
- AI_Assistant
- AI_Sourcing
- Predictive_Analytics
- Workforce_Insights
- Turnover_Analysis
- Benchmarking

**Payroll Features:**
- Earned_Wage_Access (EWA)
- Gross_To_Net
- Payroll_Journal
- Legal_Entity (vs Company)

**Time & Scheduling:**
- Geo_Validation
- Mobile_Punch
- Shift_Swap
- Schedule_Notification
- Open_Shift
- Budget_Planning
- Attendance_Policy

**Talent:**
- Hiring_Tax_Credit
- Competency
- Career_Path
- Succession_Plan
- Development_Plan

---

## Part 5: XLR8 Integration

### Product Detection

Detect Paycor via:

| Indicator | Pattern |
|-----------|---------|
| API URL | `api.paycor.com/*` |
| Key fields | `legalEntityId`, `employeeId`, `continuationToken` |
| Pagination | Continuation token style |
| Industry fields | `pbj_reporting`, `tip_allocation` |

### Spoke Patterns

```
Legal_Entity → Employee → Employment → Job/Position
Employee → Paycheck → Earning/Deduction
Employee → Time_Card → Time_Entry → Punch
Employee → Schedule → Shift
Employee → Benefit → Benefit_Plan/Dependent
Candidate → Application → Job_Requisition
Employee → Performance_Review → Goal
Employee → Learning_Assignment → Course
```

### Column Patterns

| Pattern | Hub |
|---------|-----|
| employee_id, emp_id, employeeid | employee |
| legal_entity_id, legalentityid | legal_entity |
| time_card_id, timecard | time_card |
| paycheck_id, check_id | paycheck |
| earning_code, earn_cd | earning_code |
| deduction_code, ded_cd | deduction_code |

---

## Part 6: Product Modules

### Core Platform
- HR & Payroll
- Employee Self-Service
- Mobile App
- Reporting & Analytics

### Talent Acquisition
- Recruiting (ATS)
- AI Sourcing
- Onboarding
- Background Checks
- Tax Credits (WOTC)

### Talent Management
- Performance Management
- Goal Setting
- Learning Management (LMS)
- Career Development
- Succession Planning

### Workforce Management
- Time & Attendance
- Scheduling
- Labor Distribution
- Attendance Management

### Benefits Administration
- Enrollment
- Carrier Connections
- ACA Compliance
- COBRA
- FSA/HSA

---

## Deliverables

| File | Description |
|------|-------------|
| `paycor_schema_v1.json` | Full hub definitions (174 hubs) |
| `paycor_comparison.json` | Cross-vendor overlap analysis |
| `PAYCOR_EXTRACTION.md` | This document |

---

## Updated HCM Product Summary

| Product | Hubs | Vendor |
|---------|------|--------|
| **Paycor** | **174** | **Paycor** |
| Oracle HCM | 173 | Oracle |
| Paycom | 164 | Paycom |
| Workday HCM | 160 | Workday |
| Dayforce | 157 | Ceridian |
| Paylocity | 142 | Paylocity |
| ADP WFN | 138 | ADP |
| SuccessFactors | 137 | SAP |
| Paychex Flex | 127 | Paychex |
| UKG WFM | 113 | UKG |
| UKG Pro | 105 | UKG |
| UKG Ready | 104 | UKG |
| **TOTAL** | **1,694** | **12 products** |

---

## Summary

Paycor brings **174 hubs** across 25 HCM domains - the **largest extraction** so far. Key strengths:

1. **Intelligent HCM** - AI-powered insights and automation
2. **140+ APIs** - Extensive developer platform
3. **Earned Wage Access** - Early pay access for employees
4. **Industry Solutions** - Healthcare, Manufacturing, Restaurant verticals
5. **Mid-Market Focus** - Purpose-built for 10-1000 employees

Paycor's largest overlap is with **Paycom (114 shared)**, reflecting similar mid-market positioning and comprehensive HCM suites. The 2024-2025 merger with Paychex creates interesting competitive dynamics.
