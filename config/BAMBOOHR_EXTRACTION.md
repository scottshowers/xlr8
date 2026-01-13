# BambooHR - Domain Model Extraction
**Date:** January 10, 2026  
**Vendor:** BambooHR  
**Source:** BambooHR website, API documentation, developer portal  
**Purpose:** Hub-and-spoke schema for XLR8 universal analysis engine

---

## Executive Summary

| Metric | Count |
|--------|-------|
| **Total Hubs** | 138 |
| **Core Hubs** | 53 |
| **Domains** | 23 |
| **Product Focus** | SMB HRIS - 25-500 employees |

**Key Insight:** BambooHR is the **SMB HRIS leader** known for exceptional user experience and employee data management. Strong in core HR, recruiting (ATS), onboarding, and performance management. Payroll, benefits, and time tracking are add-ons.

---

## Part 1: BambooHR Architecture

### Platform Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    BAMBOOHR PLATFORM                             │
│            SMB HRIS - "Set Your People Free"                     │
└─────────────────────────────────────────────────────────────────┘
                              │
    ┌─────────────┬───────────┼───────────┬─────────────┐
    │             │           │           │             │
    ▼             ▼           ▼           ▼             ▼
┌────────┐  ┌─────────┐  ┌────────┐  ┌────────┐  ┌──────────┐
│ CORE   │  │ HIRING  │  │ TIME   │  │PERFORM │  │ EMPLOYEE │
│  HR    │  │  & ATS  │  │  OFF   │  │  MGMT  │  │   EXP    │
├────────┤  ├─────────┤  ├────────┤  ├────────┤  ├──────────┤
│Employee│  │Postings │  │Requests│  │Reviews │  │Surveys   │
│Records │  │Pipeline │  │Balance │  │Goals   │  │eNPS      │
│Docs    │  │Offers   │  │Accruals│  │Feedback│  │Wellbeing │
│Reports │  │Onboard  │  │History │  │Assess  │  │Announce  │
└────────┘  └─────────┘  └────────┘  └────────┘  └──────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
       ┌──────────┐    ┌──────────┐    ┌──────────┐
       │ PAYROLL  │    │  TIME    │    │ BENEFITS │
       │ (Add-on) │    │ TRACKING │    │ (Add-on) │
       │          │    │ (Add-on) │    │          │
       └──────────┘    └──────────┘    └──────────┘
```

### API Structure

**Base URL:**
```
https://{companyDomain}.bamboohr.com/api/gateway.php/{companyDomain}/v1
```

**Authentication:** OAuth 2.0 or API Key (Basic Auth)

**Key Endpoints:**
- `/employees` - Employee list
- `/employees/{id}` - Single employee
- `/employees/{id}/files` - Employee documents
- `/employees/{id}/time_off` - Time off data
- `/reports/{id}` - Run report
- `/applicant_tracking/applications` - ATS data

---

## Part 2: Key Differentiators

### Employee Data Management

Best-in-class HRIS:
- Centralized employee database
- Custom fields support
- Audit trail for changes
- Document management
- Employee photos

### User Experience

Known for simplicity:
- Intuitive navigation
- Clean dashboard
- Employee self-service
- Mobile app
- Minimal training needed

### Built-in ATS

Full applicant tracking:
- Job postings to Indeed, ZipRecruiter
- Candidate pipeline stages
- Offer letter generation
- E-signatures
- Auto-populate employee records

### Performance Management

Goal-oriented reviews:
- Self-assessments
- Manager assessments
- Goal tracking with status
- Review cycles
- Continuous feedback

### Employee Experience

Engagement tools:
- eNPS surveys
- Wellbeing surveys
- Company announcements
- Birthday/anniversary celebrations
- Employee satisfaction tracking

---

## Part 3: Domain Structure

### Employee_Core (9 hubs)
Core employee information.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Employee | `employee_id` | ✅ |
| Person | `person_id` | ✅ |
| SSN | `ssn_id` | ✅ |
| Preferred_Name | `preferred_name_id` | |
| Employee_Photo | `employee_photo_id` | |

### Recruiting (10 hubs)
Applicant tracking system (ATS).

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Job_Opening | `job_opening_id` | ✅ |
| Job_Posting | `job_posting_id` | ✅ |
| Candidate | `candidate_id` | ✅ |
| Application | `application_id` | ✅ |
| Application_Status | `application_status_id` | |
| Interview | `interview_id` | |
| Offer | `offer_id` | |
| Offer_Letter | `offer_letter_id` | |
| Job_Board | `job_board_id` | |
| Hiring_Lead | `hiring_lead_id` | |

### PTO (8 hubs)
Time off management.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Time_Off | `time_off_id` | ✅ |
| Time_Off_Request | `time_off_request_id` | ✅ |
| Time_Off_Policy | `time_off_policy_id` | ✅ |
| Time_Off_Balance | `time_off_balance_id` | ✅ |
| Time_Off_Type | `time_off_type_id` | |
| Time_Off_History | `time_off_history_id` | |

### Performance (7 hubs)
Performance management.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Performance_Review | `performance_review_id` | ✅ |
| Goal | `goal_id` | ✅ |
| Goal_Status | `goal_status_id` | |
| Self_Assessment | `self_assessment_id` | |
| Manager_Assessment | `manager_assessment_id` | |
| Review_Cycle | `review_cycle_id` | |

### Additional Domains

**Employment (9 hubs):** Employment ✅, Job ✅, Job_Title ✅, Job_Information, Hire_Date ✅, Termination_Date, Employment_Status ✅, Employment_Type, FLSA_Status

**Organization (7 hubs):** Company ✅, Department ✅, Division, Location ✅, Supervisor ✅, Org_Chart, Employee_Directory

**Compensation (8 hubs):** Compensation ✅, Pay_Rate ✅, Annual_Salary, Hourly_Rate, Pay_Type ✅, Pay_Schedule ✅, Pay_Change_Reason, Compensation_History

**Onboarding (8 hubs):** Onboarding ✅, Onboarding_Task ✅, Onboarding_Template, New_Hire_Packet, E_Signature, Document, Pre_Onboarding, Welcome_Email

**Employee_Experience (6 hubs):** Employee_Survey, eNPS, Wellbeing_Survey, Employee_Satisfaction, Announcement, Celebration

**Documents (4 hubs):** Employee_File ✅, File_Category, Company_File, Signature_Request

**Reporting (6 hubs):** Report, Custom_Report, Headcount_Report, Turnover_Report, Analytics, Benchmark

---

## Part 4: Cross-Vendor Comparison

### BambooHR Overlap with Other SMB Systems

| Comparison | Shared Concepts |
|------------|-----------------|
| BambooHR + Gusto | **83** |
| BambooHR + Rippling | 81 |

### BambooHR-Unique Concepts (45)

Concepts unique to BambooHR include:

**ATS/Recruiting:**
- Job_Opening, Job_Board
- Application_Status
- Hiring_Lead

**Performance:**
- Self_Assessment, Manager_Assessment
- Goal_Status
- Review_Cycle

**Employee Experience:**
- eNPS, Wellbeing_Survey
- Employee_Satisfaction
- Announcement, Celebration

**Documents:**
- Employee_File, Company_File
- File_Category
- Signature_Request

**Onboarding:**
- Onboarding_Task, Onboarding_Template
- New_Hire_Packet
- Pre_Onboarding

**Reporting:**
- Custom_Report
- Headcount_Report, Turnover_Report
- Benchmark

---

## Part 5: XLR8 Integration

### Product Detection

Detect BambooHR via:

| Indicator | Pattern |
|-----------|---------|
| API URL | `*.bamboohr.com/api/*` |
| Key fields | `employeeId`, `companyDomain` |
| Webhooks | BambooHR webhook format |
| Auth | API key in basic auth username |

### Spoke Patterns

```
Company → Employee → Job → Compensation
Employee → Time_Off_Request → Time_Off_Policy
Employee → Performance_Review → Goal
Employee → Employee_File → File_Category
Job_Opening → Job_Posting → Candidate → Application
Employee → Onboarding → Onboarding_Task
Employee → Training → Training_Completion
```

### Column Patterns

| Pattern | Hub |
|---------|-----|
| employeeId, employee_id | employee |
| jobId, job_id | job |
| timeOffId, time_off_id | time_off |
| applicantId, candidate_id | candidate |
| fileId, file_id | employee_file |

---

## Part 6: Pricing

| Plan | Base Price | Features |
|------|------------|----------|
| **Core** | $250/mo (≤25 emp) | HR data, reporting, hiring, onboarding, time off, benefits tracking |
| **Pro** | $450/mo (≤25 emp) | Core + Performance management, employee community |

**Per-Employee (>25):**
- Core: ~$10/employee
- Pro: ~$17/employee

**Add-ons:**
- Payroll
- Time Tracking
- Benefits Administration

---

## Deliverables

| File | Description |
|------|-------------|
| `bamboohr_schema_v1.json` | Full hub definitions (138 hubs) |
| `bamboohr_comparison.json` | Cross-vendor overlap analysis |
| `BAMBOOHR_EXTRACTION.md` | This document |

---

## Updated HCM Product Summary

| Product | Hubs | Vendor |
|---------|------|--------|
| Paycor | 174 | Paycor |
| Oracle HCM | 173 | Oracle |
| Paycom | 164 | Paycom |
| Rippling | 161 | Rippling |
| Workday HCM | 160 | Workday |
| Dayforce | 157 | Ceridian |
| Paylocity | 142 | Paylocity |
| ADP WFN | 138 | ADP |
| **BambooHR** | **138** | **BambooHR** |
| SuccessFactors | 137 | SAP |
| Gusto | 135 | Gusto |
| Paychex Flex | 127 | Paychex |
| UKG WFM | 113 | UKG |
| UKG Pro | 105 | UKG |
| UKG Ready | 104 | UKG |
| **TOTAL** | **2,128** | **15 products** |

---

## Summary

BambooHR brings **138 hubs** across 23 domains - matching ADP WFN in scope but focused on the SMB market. Key strengths:

1. **UX Excellence** - Best-in-class user experience
2. **Employee Data** - Centralized, clean database
3. **Built-in ATS** - Full recruiting pipeline
4. **Performance** - Goal-oriented reviews with self/manager assessments
5. **Employee Experience** - eNPS, wellbeing, celebrations
6. **Document Management** - Files, categories, e-signatures

BambooHR's 45 unique concepts reflect its focus on employee experience (eNPS, wellbeing, celebrations) and document management - areas where payroll-focused vendors are lighter.
