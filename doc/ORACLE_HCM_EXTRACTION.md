# Oracle Fusion Cloud HCM - Domain Model Extraction
**Date:** January 10, 2026  
**Vendor:** Oracle Corporation  
**Source:** Oracle docs, REST API, HCM Data Loader (HDL)  
**Purpose:** Hub-and-spoke schema for XLR8 universal analysis engine

---

## Executive Summary

| Metric | Count |
|--------|-------|
| **Total Hubs** | 173 |
| **Core Hubs** | 62 |
| **Domains** | 20 |
| **Product Focus** | Enterprise HCM - Global HR, Talent, Payroll, WFM, Benefits |

**Key Insight:** Oracle HCM uses a **3-tier employment model**: Work Relationship → Employment Terms → Assignment. This is more complex than Workday's unified object model.

---

## Part 1: Oracle HCM Architecture

### 3-Tier Employment Model

Oracle's unique employment structure:

```
                    ┌─────────────────┐
                    │     PERSON      │  ← Identity (can have multiple workers)
                    │   (person_id)   │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │     WORKER      │  ← Employment instance
                    │   (worker_id)   │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
       ┌────────────┐ ┌────────────┐ ┌────────────┐
       │    Work    │ │    Work    │ │    Work    │
       │ Relationship│ │ Relationship│ │ Relationship│
       │ (Employee) │ │   (CW)     │ │ (Applicant)│
       └─────┬──────┘ └─────┬──────┘ └────────────┘
             │              │
      ┌──────▼──────┐ ┌─────▼──────┐
      │ Employment  │ │ Employment │
      │   Terms     │ │   Terms    │
      └──────┬──────┘ └─────┬──────┘
             │              │
      ┌──────▼──────┐ ┌─────▼──────┐
      │ Assignment  │ │ Assignment │  ← Job, Dept, Location, Grade
      │ (Primary)   │ │ (Secondary)│
      └─────────────┘ └────────────┘
```

### Key Tables

| Table | Purpose |
|-------|---------|
| PER_ALL_PEOPLE_F | Person master data |
| PER_ALL_ASSIGNMENTS_M | Assignment records (all types) |
| HR_ALL_ORGANIZATION_UNITS_F | Organizations, departments, BUs |
| PER_JOBS_F | Job catalog |
| PER_POSITIONS_F | Position definitions |
| PER_GRADES_F | Grade structure |
| PER_LOCATIONS | Work locations |

### REST API Structure

**Base URL:**
```
https://{server}.oraclecloud.com/hcmRestApi/resources/{version}/{resource}
```

**Key Endpoints:**
- `/workers` - Worker records with nested child objects
- `/emps` - Employee-specific views
- `/jobs` - Job definitions
- `/positions` - Position data
- `/locations` - Location records
- `/departments` - Department hierarchy

---

## Part 2: Domain Structure

### Worker_Core (17 hubs)
Central worker/person data - foundation of Oracle HCM.

| Hub | Semantic Type | Core | Description |
|-----|---------------|------|-------------|
| Worker | `worker_id` | ✅ | **Central** worker record |
| Person | `person_id` | ✅ | Person identity |
| Person Name | `person_name_id` | | Name components |
| Person Address | `person_address_id` | | Address records |
| Person Email | `person_email_id` | | Email addresses |
| Person Phone | `person_phone_id` | | Phone numbers |
| National Identifier | `national_id` | | SSN, NI, etc. |
| Legislative Data | `legislative_data_id` | | Country-specific |
| Visa | `visa_id` | | Visa/permit records |
| Citizenship | `citizenship_id` | | Citizenship |
| Passport | `passport_id` | | Passport records |
| Ethnicity | `ethnicity_id` | | Ethnicity data |
| Religion | `religion_id` | | Religion data |
| Person Image | `person_image_id` | | Profile photo |
| Emergency Contact | `emergency_contact_id` | | Emergency contacts |
| Dependent | `dependent_id` | | Dependents |
| Contact Relationship | `contact_relationship_id` | | Relations |

### Employment_Model (9 hubs)
3-tier employment model unique to Oracle.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Work Relationship | `work_relationship_id` | ✅ |
| Employment Terms | `employment_terms_id` | ✅ |
| Assignment | `assignment_id` | ✅ |
| Assignment Supervisor | `assignment_supervisor_id` | |
| Assignment Extra Info | `assignment_extra_info_id` | |
| Assignment Work Measure | `assignment_work_measure_id` | |
| Assignment Grade Steps | `assignment_grade_steps_id` | |
| Period of Service | `period_of_service_id` | ✅ |
| Contract | `contract_id` | |

### Organization (11 hubs)
Organizational hierarchy and structure.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Legal Employer | `legal_employer_id` | ✅ |
| Business Unit | `business_unit_id` | ✅ |
| Department | `department_id` | ✅ |
| Division | `division_id` | |
| Organization | `organization_id` | ✅ |
| Organization Hierarchy | `org_hierarchy_id` | |
| Reporting Establishment | `reporting_establishment_id` | |
| Tax Reporting Unit | `tax_reporting_unit_id` | ✅ |
| Legislative Data Group | `legislative_data_group_id` | ✅ |
| Enterprise | `enterprise_id` | |
| Cost Center | `cost_center_id` | ✅ |

### Job_Position (6 hubs)
Job catalog and position management.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Job | `job_id` | ✅ |
| Job Family | `job_family_id` | ✅ |
| Position | `position_id` | ✅ |
| Position Hierarchy | `position_hierarchy_id` | |
| Headcount | `headcount_id` | |
| Incumbent | `incumbent_id` | |

### Payroll (13 hubs)
Global payroll processing.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Payroll | `payroll_id` | ✅ |
| Pay Period | `pay_period_id` | ✅ |
| Payroll Run | `payroll_run_id` | ✅ |
| Payroll Relationship | `payroll_relationship_id` | ✅ |
| Earning | `earning_id` | ✅ |
| Deduction | `deduction_id` | ✅ |
| Tax Card | `tax_card_id` | |
| Costing | `costing_id` | |
| Payment Method | `payment_method_id` | |
| Bank Account | `bank_account_id` | |
| Payslip | `payslip_id` | |
| Balance | `balance_id` | |
| Retroactive Pay | `retro_pay_id` | |

### Additional Domains

**Compensation (10 hubs):** Compensation Plan ✅, Salary ✅, Salary Basis ✅, Pay Component ✅, Element ✅, Element Entry, Worksheet, Stock Grant, Bonus, Total Comp Statement

**Time_Labor (9 hubs):** Time Card ✅, Time Entry ✅, Time Record, Shift ✅, Work Schedule ✅, Schedule Assignment, Working Hours, Overtime, Time Attribute

**Absence (8 hubs):** Absence ✅, Absence Type ✅, Absence Plan ✅, Absence Entry, Accrual ✅, Entitlement, Leave Balance, Certification

**Benefits (10 hubs):** Benefit Plan ✅, Benefit Program ✅, Benefit Option, Benefit Enrollment ✅, Benefit Election, Coverage, Beneficiary, Life Event, Participation, Rate

**Recruiting (14 hubs):** Requisition ✅, Job Posting ✅, Candidate ✅, Candidate Pool, Application ✅, Interview, Interview Request, Assessment, Offer ✅, Offer Letter, Source, Referral, Background Check, Screening

**Onboarding (6 hubs):** Onboarding ✅, Journey ✅, Journey Task, Checklist, Checklist Task, Preboarding

**Performance (11 hubs):** Performance Document ✅, Goal ✅, Goal Plan, Rating, Rating Model, Competency ✅, Competency Profile, Feedback, Check-In, Check-In Document, Development Goal

**Learning (8 hubs):** Learning Item ✅, Offering, Learning Enrollment ✅, Completion, Learning Assignment, Certification ✅, License, Qualification

**Talent (7 hubs):** Talent Profile ✅, Talent Review, Succession Plan, Career Development, Career Path, Career Interest, Mentor

**Actions (8 hubs):** Action ✅, Action Reason ✅, Hire ✅, Termination ✅, Promotion, Transfer, Global Transfer, Seniority Date

---

## Part 3: Cross-Vendor Comparison

### Oracle vs Competition

| Comparison | Shared Concepts | Notes |
|------------|-----------------|-------|
| **Oracle + Dayforce** | **58** | Strongest overlap |
| **Oracle + Workday** | **52** | Both enterprise-grade |
| Oracle + UKG Ready | 21 | Different markets |
| Oracle + UKG Pro | 8 | Different architectures |
| Oracle + UKG WFM | 7 | WFM is specialized |

### Enterprise Vendors Shared (38 concepts)
Oracle, Workday, and Dayforce share these core HCM concepts:
- **Core HR:** Person, Dependent, Emergency Contact
- **Organization:** Business Unit, Cost Center, Location, Department
- **Compensation:** Earning, Deduction, Salary
- **Benefits:** Benefit Plan, Benefit Election
- **Time:** Shift, Schedule, Time Entry
- **Talent:** Candidate, Certification, Competency, Goal
- **Recruiting:** Job Posting, Requisition, Offer, Background Check

### Oracle-Unique Concepts (97)
Concepts in Oracle HCM not found in other vendors:
- **Employment Model:** Assignment, Work Relationship, Employment Terms, Period of Service
- **Payroll:** Element, Element Entry, Payroll Relationship, Balance, Costing
- **Oracle Journeys:** Journey, Journey Task, Check-In Document
- **Talent:** Talent Profile, Career Development, Talent Review
- **Security:** Data Role, Security Profile, Person Security Profile
- **Global:** Legislative Data Group, Tax Reporting Unit

---

## Part 4: XLR8 Integration

### Product Detection

Detect Oracle HCM via:

| Indicator | Pattern |
|-----------|---------|
| API URL | `*.oraclecloud.com/hcmRestApi` |
| Table names | `PER_*`, `HR_*` prefix |
| Assignment structure | `work_relationship` → `employment_terms` → `assignment` |
| Legal Employer concept | `legal_employer_id` field |
| Legislative Data Group | `legislative_data_group_id` |

### Spoke Patterns

```
Person → Worker (has worker instances)
Worker → Work Relationship (has relationships)
Work Relationship → Employment Terms (has terms)
Employment Terms → Assignment (has assignments)
Assignment → Job (assigned to)
Assignment → Position (fills)
Assignment → Department (belongs to)
Assignment → Location (works at)
Assignment → Grade (at grade)
Assignment → Payroll (paid via)
Payroll Relationship → Worker (links to)
Benefit Enrollment → Benefit Plan (enrolled in)
Candidate → Application (submitted)
Application → Requisition (applies to)
```

### Column Patterns

| Pattern | Hub |
|---------|-----|
| person_id, per_* | person |
| worker_id | worker |
| assignment_id, asg_* | assignment |
| work_relationship_id | work_relationship |
| legal_employer_id, legal_entity* | legal_employer |
| business_unit_id, bu_* | business_unit |
| department_id, dept_* | department |
| job_id, job_code | job |
| position_id, pos_* | position |
| grade_id | grade |
| location_id, loc_* | location |
| payroll_id | payroll |

---

## Part 5: All-Vendor Summary

### Complete Extraction Status

| Vendor | Product | Hubs | Status |
|--------|---------|------|--------|
| **Oracle** | Fusion Cloud HCM | **173** | ✅ Complete |
| **Workday** | HCM | **160** | ✅ Complete |
| **Dayforce** | HCM | **157** | ✅ Complete |
| UKG | WFM Dimensions | 113 | ✅ Complete |
| UKG | Pro | 105 | ✅ Complete |
| UKG | Ready | 104 | ✅ Complete |
| **TOTAL** | | **812** | |

### Unique Concepts (Deduplicated)
**601 unique HCM concepts** across all vendors

### Universal Concept (All 6 Products)
Only **1 concept** exists in ALL products: **Shift**

### Enterprise Shared (Oracle + Workday + Dayforce)
**38 concepts** shared across all enterprise vendors

---

## Deliverables

| File | Description |
|------|-------------|
| `oracle_hcm_schema_v1.json` | Full hub definitions (173 hubs) |
| `complete_vendor_comparison.json` | 6-vendor comparison |
| `ORACLE_HCM_EXTRACTION.md` | This document |

---

## Oracle HCM Key Differentiators

1. **3-Tier Employment Model** - Work Relationship → Employment Terms → Assignment
2. **Global Payroll** - Native support for 160+ countries
3. **Element-Based Payroll** - Flexible element/entry model
4. **Legislative Data Groups** - Country-specific compliance
5. **Oracle Journeys** - Guided employee experiences
6. **Workforce Modeling** - AI-powered predictions
7. **Dynamic Skills** - AI skills matching and recommendations
