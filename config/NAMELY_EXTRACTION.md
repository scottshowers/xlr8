# Namely - Domain Model Extraction
**Date:** January 10, 2026  
**Vendor:** Namely  
**Source:** Namely website, API documentation, Gartner reviews  
**Purpose:** Hub-and-spoke schema for XLR8 universal analysis engine

---

## Executive Summary

| Metric | Count |
|--------|-------|
| **Total Hubs** | 126 |
| **Core Hubs** | 53 |
| **Domains** | 24 |
| **Product Focus** | Mid-market all-in-one HCM - 50-1000 employees |

**Key Insight:** Namely differentiates through **managed services** (Managed Payroll, Managed Benefits) and **compliance tools** (HR advisor access, state comparison, handbook wizard). The company newsfeed/culture features reflect its focus on employee engagement.

---

## Part 1: Namely Architecture

### Platform Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    NAMELY HCM PLATFORM                           │
│            Mid-Market All-in-One with Managed Services           │
└─────────────────────────────────────────────────────────────────┘
                              │
    ┌─────────────┬───────────┼───────────┬─────────────┐
    │             │           │           │             │
    ▼             ▼           ▼           ▼             ▼
┌────────┐  ┌─────────┐  ┌────────┐  ┌────────┐  ┌──────────┐
│  HR    │  │ PAYROLL │  │BENEFITS│  │ TALENT │  │COMPLIANCE│
│ CORE   │  │         │  │        │  │        │  │          │
├────────┤  ├─────────┤  ├────────┤  ├────────┤  ├──────────┤
│Employee│  │Process  │  │Enroll  │  │Recruit │  │Library   │
│Records │  │Tax      │  │Open Enr│  │Perform │  │States    │
│Newsfeed│  │Service  │  │Broker  │  │Goals   │  │Handbook  │
│Workflow│  │Managed  │  │Managed │  │360     │  │OSHA      │
└────────┘  └─────────┘  └────────┘  └────────┘  └──────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
       ┌──────────┐    ┌──────────┐    ┌──────────┐
       │   TIME   │    │SCHEDULING│    │REPORTING │
       │          │    │          │    │          │
       │Track Hrs │    │ Shifts   │    │Analytics │
       └──────────┘    └──────────┘    └──────────┘
```

### API Structure

**Base URL:**
```
https://api.namely.com/v1
```

**Developer Portal:** https://developers.namely.com

**Authentication:** OAuth 2.0

**Key Endpoints:**
- `/profiles` - Employee profiles
- `/jobs` - Job records
- `/time_off` - PTO requests
- `/reports` - Custom reports

---

## Part 2: Key Differentiators

### Managed Services

What sets Namely apart:

**Managed Payroll:**
- Dedicated team handles payroll processing
- Accuracy guarantee
- Full tax filing
- Expert support

**Managed Benefits:**
- Benefits brokerage services
- Employee benefits consulting
- Carrier management
- Open enrollment support

### Compliance Tools

Strong compliance differentiator:

**Compliance Library:**
- Constantly updated regulation database
- Federal, state, local laws

**State Comparison Tool:**
- Compare laws across states
- Multi-state compliance made easy

**Handbook Wizard:**
- Build compliant employee handbooks
- Auto-update with law changes

**HR Advisor Access:**
- Unlimited access to HR experts
- On-demand compliance guidance

**Additional Compliance:**
- OSHA logs
- Anonymous reporting (whistleblower)
- E-Verify integration
- Learning management (compliance training)

### Company Culture

Employee engagement focus:

**Newsfeed:**
- Company-wide communication
- Social media-style interface

**Recognition:**
- Peer recognition
- Kudos and shout-outs

---

## Part 3: Domain Structure

### Employee_Core (9 hubs)
Core employee information.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Employee | `employee_id` | ✅ |
| Person | `person_id` | ✅ |
| SSN | `ssn_id` | ✅ |
| Profile | `profile_id` | |

### Compliance (8 hubs)
HR compliance (strong differentiator).

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Compliance | `compliance_id` | ✅ |
| Compliance_Library | `compliance_library_id` | |
| State_Comparison | `state_comparison_id` | |
| Handbook_Wizard | `handbook_wizard_id` | |
| OSHA_Log | `osha_log_id` | |
| Anonymous_Reporting | `anonymous_reporting_id` | |
| HR_Advisor | `hr_advisor_id` | |
| Learning_Management | `lms_id` | |

### Benefits (9 hubs)
Benefits administration with managed option.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Benefit | `benefit_id` | ✅ |
| Benefit_Plan | `benefit_plan_id` | ✅ |
| Benefit_Enrollment | `benefit_enrollment_id` | ✅ |
| Dependent | `dependent_id` | ✅ |
| Managed_Benefits | `managed_benefits_id` | |
| Benefits_Consulting | `benefits_consulting_id` | |
| Carrier | `carrier_id` | |
| E_Verify | `e_verify_id` | |

### Additional Domains

**Employment (8 hubs):** Employment ✅, Job ✅, Job_Title ✅, Hire_Date ✅, Termination_Date, Employment_Status ✅, Employment_Type, FLSA_Status

**Organization (7 hubs):** Company ✅, Department ✅, Division, Location ✅, Supervisor ✅, Org_Chart, Team

**Payroll (7 hubs):** Payroll ✅, Pay_Period ✅, Paycheck ✅, Pay_Stub, Direct_Deposit ✅, Managed_Payroll, Payroll_Tax

**PTO (6 hubs):** Time_Off ✅, Time_Off_Request ✅, Time_Off_Policy ✅, Time_Off_Balance ✅, Accrual, Time_Off_Type

**Recruiting (6 hubs):** Job_Posting ✅, Candidate ✅, Application ✅, Interview, Offer, Recruiting ✅

**Performance (4 hubs):** Performance_Review ✅, Goal ✅, Feedback, Review_360

**Employee_Engagement (4 hubs):** Newsfeed, Announcement, Employee_Recognition, Company_Culture

---

## Part 4: Cross-Vendor Comparison

### Namely Overlap with Other Mid-Market Systems

| Comparison | Shared Concepts |
|------------|-----------------|
| Namely + BambooHR | **91** |
| Namely + Gusto | 77 |

### Namely-Unique Concepts (34)

Concepts unique to Namely include:

**Managed Services:**
- Managed_Payroll
- Managed_Benefits
- Benefits_Consulting
- HR_Advisor

**Compliance:**
- Compliance_Library
- State_Comparison
- Handbook_Wizard
- OSHA_Log
- Anonymous_Reporting
- Learning_Management (LMS)

**Culture/Engagement:**
- Newsfeed
- Employee_Recognition
- Company_Culture
- Engagement_Report

**Other:**
- E_Verify
- Review_360
- Carrier
- Partner_Network

---

## Part 5: XLR8 Integration

### Product Detection

Detect Namely via:

| Indicator | Pattern |
|-----------|---------|
| API URL | `api.namely.com/*` |
| Key fields | `profile_id`, `employee_id` |
| Domain | `*.namely.com` |
| Features | Newsfeed, state comparison |

### Spoke Patterns

```
Company → Employee/Profile → Job → Compensation
Employee → Time_Off_Request → Time_Off_Policy
Employee → Benefit_Enrollment → Benefit_Plan
Employee → Performance_Review → Goal
Employee → Onboarding → Onboarding_Task
Candidate → Application → Job_Posting
Company → Compliance → Compliance_Library
```

### Column Patterns

| Pattern | Hub |
|---------|-----|
| profile_id, profileid | profile |
| employee_id, employeeid | employee |
| time_off_id | time_off |
| benefit_id | benefit |

---

## Part 6: Service Options

### Self-Service (Technology Only)
- HR platform
- Payroll processing
- Benefits enrollment
- Time tracking
- All modules available

### Managed Payroll
- Dedicated payroll team
- Day-to-day administration
- Accuracy guarantee
- Tax filing and compliance

### Managed Benefits
- Benefits brokerage
- Employee consulting
- Carrier management
- Open enrollment support
- Compliance guidance

---

## Deliverables

| File | Description |
|------|-------------|
| `namely_schema_v1.json` | Full hub definitions (126 hubs) |
| `namely_comparison.json` | Cross-vendor overlap analysis |
| `NAMELY_EXTRACTION.md` | This document |

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
| BambooHR | 138 | BambooHR |
| SuccessFactors | 137 | SAP |
| Gusto | 135 | Gusto |
| Paychex Flex | 127 | Paychex |
| **Namely** | **126** | **Namely** |
| UKG WFM | 113 | UKG |
| UKG Pro | 105 | UKG |
| UKG Ready | 104 | UKG |
| **TOTAL** | **2,254** | **16 products** |

---

## Summary

Namely brings **126 hubs** across 24 domains - a focused mid-market extraction with unique strengths in managed services and compliance.

Key strengths:

1. **Managed Payroll** - Let experts handle payroll processing
2. **Managed Benefits** - Brokerage and consulting services
3. **Compliance Tools** - Library, state comparison, handbook wizard
4. **HR Advisor** - Unlimited expert access
5. **Company Culture** - Newsfeed, recognition, engagement
6. **E-Verify Integration** - Built-in I-9 verification

Namely's 34 unique concepts heavily skew toward compliance and managed services - reflecting its positioning as "HCM + HR expertise" rather than just software.
