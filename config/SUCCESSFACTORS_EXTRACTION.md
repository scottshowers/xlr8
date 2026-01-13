# SAP SuccessFactors HXM Suite - Domain Model Extraction
**Date:** January 10, 2026  
**Vendor:** SAP  
**Source:** SAP docs, OData API V2/V4, Employee Central entities  
**Purpose:** Hub-and-spoke schema for XLR8 universal analysis engine

---

## Executive Summary

| Metric | Count |
|--------|-------|
| **Total Hubs** | 137 |
| **Core Hubs** | 51 |
| **Domains** | 16 |
| **Product Focus** | Cloud HCM - Employee Central, Talent Management, Payroll, LMS |

**Key Insight:** SuccessFactors uses a **modular architecture** with standardized entity naming: `FO*` (Foundation Objects), `Per*` (Personal), `Emp*` (Employment).

---

## Part 1: SuccessFactors Architecture

### Entity Naming Convention

SuccessFactors organizes data into three main entity categories:

```
┌─────────────────────────────────────────────────────────────────┐
│                    FOUNDATION OBJECTS (FO*)                      │
│  FOCompany, FOBusinessUnit, FODepartment, FOJobCode, FOPayGrade │
│              Organization, Job, and Pay structures               │
└─────────────────────────────────────────────────────────────────┘
                              │
           ┌──────────────────┴──────────────────┐
           │                                     │
           ▼                                     ▼
┌─────────────────────────┐       ┌─────────────────────────┐
│   PERSONAL OBJECTS      │       │  EMPLOYMENT OBJECTS     │
│       (Per*)            │       │       (Emp*)            │
├─────────────────────────┤       ├─────────────────────────┤
│ PerPerson               │       │ EmpEmployment           │
│ PerPersonal             │       │ EmpJob                  │
│ PerAddress              │       │ EmpCompensation         │
│ PerEmail                │       │ EmpPayCompRecurring     │
│ PerPhone                │       │ EmpWorkPermit           │
│ PerNationalId           │       │ EmpEmploymentTermination│
│ PerEmergencyContacts    │       │ EmpGlobalAssignment     │
└─────────────────────────┘       └─────────────────────────┘
```

### API Structure

**OData V2 Base URL:**
```
https://{api-server}/odata/v2/{entity}
```

**OData V4 Base URL:**
```
https://{api-server}/odata/v4/{entity}
```

**Key API Entities:**
- `/PerPerson` - Core person record
- `/EmpEmployment` - Employment information
- `/EmpJob` - Job assignment details
- `/EmpCompensation` - Pay information
- `/FOCompany`, `/FODepartment` - Organization structure
- `/FOJobCode`, `/FOPayGrade` - Job and pay structure

---

## Part 2: Domain Structure

### Person_Core (10 hubs)
Personal data objects (Per* entities).

| Hub | Semantic Type | Core | Description |
|-----|---------------|------|-------------|
| PerPerson | `per_person_id` | ✅ | **Core** person record |
| PerPersonal | `per_personal_id` | ✅ | Biographical data |
| PerGlobalInfo | `per_global_info_id` | | Country-specific info |
| PerNationalId | `per_national_id` | ✅ | SSN, national IDs |
| PerAddress | `per_address_id` | | Address records |
| PerEmail | `per_email_id` | | Email addresses |
| PerPhone | `per_phone_id` | | Phone numbers |
| PerEmergencyContacts | `per_emergency_contacts_id` | | Emergency contacts |
| PerSocialAccount | `per_social_account_id` | | Social media |
| User | `user_id` | ✅ | System user/login |

### Employment_Objects (10 hubs)
Employment data objects (Emp* entities).

| Hub | Semantic Type | Core |
|-----|---------------|------|
| EmpEmployment | `emp_employment_id` | ✅ |
| EmpJob | `emp_job_id` | ✅ |
| EmpCompensation | `emp_compensation_id` | ✅ |
| EmpCostDistribution | `emp_cost_distribution_id` | |
| EmpPayCompRecurring | `emp_pay_comp_recurring_id` | |
| EmpPayCompNonRecurring | `emp_pay_comp_non_recurring_id` | |
| EmpWorkPermit | `emp_work_permit_id` | |
| EmpJobRelationships | `emp_job_relationships_id` | |
| EmpEmploymentTermination | `emp_employment_termination_id` | ✅ |
| EmpGlobalAssignment | `emp_global_assignment_id` | |

### Foundation_Organization (9 hubs)
Foundation Objects - Organization structure.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| FOCompany | `fo_company_id` | ✅ |
| FOBusinessUnit | `fo_business_unit_id` | ✅ |
| FODivision | `fo_division_id` | |
| FODepartment | `fo_department_id` | ✅ |
| FOCostCenter | `fo_cost_center_id` | ✅ |
| FOLocation | `fo_location_id` | ✅ |
| FOLocationGroup | `fo_location_group_id` | |
| FOGeozone | `fo_geozone_id` | |
| LegalEntity | `legal_entity_id` | ✅ |

### Foundation_Job (5 hubs)
Foundation Objects - Job structure.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| FOJobCode | `fo_job_code_id` | ✅ |
| FOJobFunction | `fo_job_function_id` | |
| FOJobFamily | `fo_job_family_id` | |
| Position | `position_id` | ✅ |
| PositionMatrixRelationship | `position_matrix_relationship_id` | |

### Foundation_Pay (8 hubs)
Foundation Objects - Pay structure.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| FOPayGrade | `fo_pay_grade_id` | ✅ |
| FOPayRange | `fo_pay_range_id` | |
| FOPayGroup | `fo_pay_group_id` | ✅ |
| FOPayComponent | `fo_pay_component_id` | ✅ |
| FOPayComponentGroup | `fo_pay_component_group_id` | |
| FOPayCalendar | `fo_pay_calendar_id` | |
| FOFrequency | `fo_frequency_id` | |
| FOEventReason | `fo_event_reason_id` | ✅ |

### Additional Domains

**Payroll (10 hubs):** PayrollRun ✅, PayrollArea ✅, PayrollResult, Earning ✅, Deduction ✅, TaxCode, PayStatement, DirectDeposit, WageType ✅, PayrollControlCenter

**Time_Management (9 hubs):** TimeSheet ✅, TimeEntry ✅, TimeAccount ✅, TimeType ✅, TimeOff ✅, WorkSchedule ✅, ShiftClassification, TimeCollector, TimeValuation

**Benefits (8 hubs):** BenefitsPlan ✅, BenefitsOption, BenefitsEnrollment ✅, BenefitsElection, BenefitsClaim, Dependent ✅, BenefitsEligibility, OpenEnrollment

**Recruiting (13 hubs):** JobRequisition ✅, JobPosting ✅, Candidate ✅, CandidateProfile, JobApplication ✅, Interview, InterviewAssessment, JobOffer ✅, OfferLetter, RecruitingSource, TalentPool, Referral, BackgroundCheck

**Onboarding (6 hubs):** Onboarding ✅, OnboardingTask, NewHireDataCollection, OnboardingEquipment, OnboardingBuddy, Offboarding

**Performance_Goals (12 hubs):** PerformanceReview ✅, PerformanceForm ✅, Goal ✅, GoalPlan, GoalLibrary, Rating ✅, RatingScale, Competency ✅, CompetencyRating, Feedback, Calibration, ContinuousFeedback

**Learning (9 hubs):** LearningItem ✅, LearningCourse ✅, LearningProgram, LearningEnrollment ✅, LearningCompletion, LearningAssignment, Certification ✅, CertificationRequirement, Curriculum

**Compensation (8 hubs):** CompensationPlan ✅, CompensationTemplate, SalaryPlan ✅, BonusPlan, StockPlan, VariablePay, CompensationStatement, MeritIncrease

**Succession_Development (7 hubs):** SuccessionPlan, NomineeRelationship, TalentPool, CareerPath, DevelopmentPlan, DevelopmentGoal, Mentoring

---

## Part 3: Cross-Vendor Comparison

### SuccessFactors vs Competition

| Comparison | Shared Concepts | Notes |
|------------|-----------------|-------|
| **SuccessFactors + Workday** | **52** | Strongest overlap |
| **SuccessFactors + Dayforce** | **46** | Strong overlap |
| **SuccessFactors + Oracle** | **41** | Both enterprise-grade |
| SuccessFactors + UKG Ready | 17 | Different markets |
| SuccessFactors + UKG Pro | 6 | Different architectures |

### Enterprise Vendors Shared (24 concepts)
All 4 enterprise vendors (SAP, Oracle, Workday, Ceridian) share:
- **Core HR:** BusinessUnit, CostCenter, Dependent
- **Recruiting:** Candidate, Interview, JobPosting, Referral, BackgroundCheck
- **Talent:** Certification, Competency, Goal, Feedback, SuccessionPlan
- **Learning:** LearningAssignment, LearningCompletion
- **Compensation:** Earning, Deduction
- **Recruiting:** JobFamily, TalentPool

### SuccessFactors-Unique Concepts (67)
Concepts in SuccessFactors not found in other vendors:
- **Entity Naming:** Per*, Emp*, FO* prefixed entities
- **Performance:** ContinuousFeedback, GoalLibrary, RatingScale
- **Benefits:** BenefitsClaim, BenefitsEligibility
- **Payroll:** WageType, PayrollControlCenter
- **Platform:** BusinessRule, MassChange, IntegrationCenter

---

## Part 4: XLR8 Integration

### Product Detection

Detect SuccessFactors via:

| Indicator | Pattern |
|-----------|---------|
| API URL | `*/odata/v2/*` or `*/odata/v4/*` |
| Entity prefixes | `FO*`, `Per*`, `Emp*` |
| Person ID | `personIdExternal` field |
| Employment ID | `userId` + employment structure |
| Foundation Objects | `FOCompany`, `FODepartment` patterns |

### Spoke Patterns

```
PerPerson → EmpEmployment (has employment)
EmpEmployment → EmpJob (has job info)
EmpJob → FOJobCode (assigned job)
EmpJob → FODepartment (belongs to)
EmpJob → FOLocation (works at)
EmpJob → FOPayGrade (at grade)
EmpCompensation → FOPayComponent (has components)
Candidate → JobApplication (submitted)
JobApplication → JobRequisition (applies to)
LearningEnrollment → LearningItem (enrolled in)
```

### Column Patterns

| Pattern | Hub |
|---------|-----|
| personIdExternal, per_person* | per_person |
| userId, user_id | user |
| company_*, fo_company* | fo_company |
| department_*, fo_department* | fo_department |
| cost_center*, fo_cost_center* | fo_cost_center |
| job_code*, fo_job_code* | fo_job_code |
| position_*, position_id | position |
| pay_grade*, fo_pay_grade* | fo_pay_grade |
| location_*, fo_location* | fo_location |

---

## Part 5: All-Vendor Final Summary

### Complete Extraction Status

| Rank | Vendor | Product | Hubs | Status |
|------|--------|---------|------|--------|
| 1 | Oracle | Fusion Cloud HCM | **173** | ✅ Complete |
| 2 | Workday | HCM | **160** | ✅ Complete |
| 3 | Ceridian | Dayforce | **157** | ✅ Complete |
| 4 | **SAP** | **SuccessFactors** | **137** | ✅ Complete |
| 5 | UKG | WFM Dimensions | 113 | ✅ Complete |
| 6 | UKG | Pro | 105 | ✅ Complete |
| 7 | UKG | Ready | 104 | ✅ Complete |
| | **TOTAL** | | **949** | |

### Unique Concepts (Deduplicated)
**668 unique HCM concepts** across all vendors

### Universal Concept (All 7 Products)
**0 concepts** exist in ALL 7 products (Shift was universal in 6, but SuccessFactors uses ShiftClassification)

### Enterprise Shared (4 Major Vendors)
**24 concepts** shared across SAP, Oracle, Workday, Ceridian

---

## Deliverables

| File | Description |
|------|-------------|
| `successfactors_schema_v1.json` | Full hub definitions (137 hubs) |
| `final_vendor_comparison.json` | Complete 7-vendor comparison |
| `SUCCESSFACTORS_EXTRACTION.md` | This document |

---

## SuccessFactors Key Differentiators

1. **Standardized Entity Naming** - FO*, Per*, Emp* prefixes
2. **Employee Central as Core** - Central HRIS with modular talent additions
3. **Strong Learning (LMS)** - Originally a talent/learning company
4. **Performance & Goals** - Deep performance management
5. **Integration Center** - Built-in integration tooling
6. **OData API** - Standard OData V2/V4 protocol
7. **SAP Ecosystem** - Integrates with SAP ERP, S/4HANA
