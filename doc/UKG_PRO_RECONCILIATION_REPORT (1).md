# UKG Pro Schema Reconciliation Report
**Date:** January 10, 2026  
**Purpose:** Reconcile JSON ground truth with XLR8 production detection

---

## Executive Summary

| Metric | Count |
|--------|-------|
| **JSON Hub Definitions** | 105 |
| **Production Hubs Detected** | 59 |
| **Properly Matched** | 12 (11%) |
| **REQUIRED Hubs Missing** | 26 |
| **XLR8 Self-Discovered** | 47 |

**Key Finding:** Only 11% alignment between the schema and production. This isn't because XLR8 is broken—it's because:
1. **Naming convention mismatch** (e.g., `job_code_code` in JSON vs `job_code` in production)
2. **XLR8 discovers hubs data-driven** that aren't in the BRIT schema (good thing)
3. **Spoke patterns incomplete** in JSON (only 62 mappings vs ~200+ needed)

---

## Part 1: What's Working ✅

### Matched Hubs (12)
These are properly aligned between JSON schema and production:

| JSON Semantic Type | Production Semantic Type |
|-------------------|-------------------------|
| component_company_code | component_company_code |
| country_code | country_code |
| earning_group_code | earning_group_code |
| employee_type_code | employee_type_code |
| job_change_reason_code | job_change_reason_code |
| location_code | location_code |
| org_level_1_code | org_level_1_code |
| org_level_2_code | org_level_2_code |
| org_level_3_code | org_level_3_code |
| org_level_4_code | org_level_4_code |
| pay_group_code | pay_group_code |

### XLR8 Self-Discovered (47)
These hubs were **discovered by XLR8's data-driven algorithm** from uploaded data—not from the schema. This is good! Examples:

- `earnings_code` (from employee earnings data)
- `accrual_code` (from PTO/accrual tables)
- `workers_compensation_code` (from WC data)
- `union_code` (from employee data)
- `bank_code` (from direct deposit data)
- `supervisor_code` (from employee hierarchy)
- `deductionbenefit_group_code` (from benefits data)

---

## Part 2: Critical Gaps 🔴

### REQUIRED BRIT Hubs Not Detected (26)

These are marked `is_required: true` in BRIT but XLR8 isn't detecting them:

| Hub | Entity Name | Why Missing |
|-----|-------------|-------------|
| `master_company_code` | Master Company | No data uploaded? |
| `tax_info_code` | Tax Info | No data uploaded? |
| `establishments_code` | Establishments | No data uploaded? |
| `organization_levels_code` | Organization Levels | Naming conflict with org_level_N |
| `banks_code` | Banks | XLR8 detects as `bank_code` (singular) |
| `holidays_code` | Holidays | No data uploaded? |
| `pay_groups_code` | Pay Groups | XLR8 detects as `pay_group_code` |
| `tax_groups_code` | Tax Groups | No data uploaded? |
| `distributioncenter_code` | Distribution Center | No data uploaded? |
| `earn_group_code` | Earn Group | XLR8 detects as `earning_group_code` |
| `earn_group_earns_code` | Earn Group Earns | Junction table - may not upload |
| `ded_code` | Ded Codes | XLR8 uses `deduction_code` |
| `ded_groups_code` | Ded Groups | Detected as `deduction_group_code`? |
| `ded_group_deds_code` | Ded Group Deds | Junction table |
| `optionratecodes_code` | Option Rate Codes | Benefits config |
| `option_rates_code` | Option Rates | Benefits config |
| `agegradedrates_code` | Age Graded Rates | Benefits config |
| `salary_grades_code` | Salary Grades | No data uploaded? |
| `jobfamilies_code` | Job Families | Detected as `job_family_code` |
| `eduleveldegs_code` | Education Levels | Detected as `education_level_code`? |
| `edu_majors_code` | Education Majors | Detected as `major_code`? |
| `licensetype_code` | License Type | No data uploaded? |
| `liccerts_code` | Licenses & Certs | No data uploaded? |
| `provadminvendpayee_code` | Providers | No data uploaded? |
| `ppaca_code` | PPACA/ACA | No data uploaded? |
| `timeclockimport_code` | Time Clock Import | Time interface config |

### Root Cause Analysis

**Issue 1: Semantic Type Naming Inconsistency**
```
JSON Schema uses:        XLR8 Discovers:
─────────────────        ───────────────
banks_code        →      bank_code
pay_groups_code   →      pay_group_code  
ded_code          →      deduction_code
jobfamilies_code  →      job_family_code
```

**Issue 2: Data Not Uploaded**
Many BRIT config tables (Tax Info, Establishments, PPACA, etc.) haven't been uploaded to TEA1000, so XLR8 can't detect them.

**Issue 3: Spoke Patterns Incomplete**
The JSON only has 62 column→hub mappings across 7 pattern groups. Need ~200+ to cover all conversion template columns.

---

## Part 3: Recommended Actions

### Immediate (Fix Alignment)

1. **Normalize Semantic Types in JSON**
   Update JSON to use XLR8's discovered naming conventions:
   ```json
   "banks_code" → "bank_code"
   "pay_groups_code" → "pay_group_code"
   "ded_code" → "deduction_code"
   "jobfamilies_code" → "job_family_code"
   ```

2. **Add Missing Spoke Patterns**
   The JSON has only 7 spoke pattern groups. Need to add all patterns from conversion templates:
   - Employee Data columns
   - Deduction Data columns
   - Earnings Data columns
   - All OB (Opening Balance) columns
   - Job History columns
   - etc.

3. **Upload Missing Config Data to TEA1000**
   - Tax Info export
   - Establishments export
   - PPACA config (if applicable)
   - Banks
   - Holidays
   - Time Clock mappings

### Near-Term (Platform Enhancement)

4. **Create Predefined Hub Registry**
   Load BRIT hub definitions into XLR8's Reference Library so the system KNOWS these hubs should exist, even before data is uploaded:
   ```
   When TEA1000 uploads Location Codes → match to "location" hub
   When TEA1000 uploads Earnings → match to "earning" hub (not "earning_code_code")
   ```

5. **Implement Schema-Aware Detection**
   When a file is uploaded tagged as "UKG Pro":
   - Apply UKG Pro spoke patterns
   - Map columns to known hub types
   - Flag missing required hubs

---

## Part 4: File Deliverables

### What You Have Now
- `ukg_schema_reference_v2.json` - 105 hub definitions, partial spoke patterns

### What You Need
1. **Normalized Hub Registry** - Semantic types aligned with XLR8 conventions
2. **Complete Spoke Patterns** - All conversion template column→hub mappings
3. **Detection Rules** - How to identify each hub from uploaded data

---

## Next Steps

1. **Do you want me to create a normalized version of the JSON?** (Fix naming to match XLR8)

2. **Do you want me to expand the spoke patterns?** (Add all conversion template mappings)

3. **Do you want a Platform Integration Guide?** (How to load this into XLR8's Reference Library)

---

## Appendix: Full Hub List by Category

### A. BRIT Config Tables (53 hubs)
| Tab | Hub | Entity Name | Required |
|-----|-----|-------------|----------|
| 1 | master_company | Master Company | ✅ |
| 2 | component_company | Component Company | ✅ |
| 3 | tax_info | Tax Info | ✅ |
| 4 | location | Location Codes | ✅ |
| 5 | establishments | Establishments | ✅ |
| 6 | organization_levels | Organization Levels | ✅ |
| 7 | suborg_levels | Sub-Org Levels | |
| 8 | projects | Projects | |
| 9 | ppaca | PPACA | ✅ |
| 10 | banks | Banks | ✅ |
| 11 | holidays | Holidays | ✅ |
| 12 | timeclockimport | Time Clock Import | ✅ |
| 13 | pay_groups | Pay Groups | ✅ |
| 14 | tax_groups | Tax Groups | ✅ |
| 15 | work_pattern | Work Pattern | |
| 16 | distributioncenter | Distribution Center | ✅ |
| 17 | earning | Earning Codes | ✅ |
| 18 | earn_group | Earn Group | ✅ |
| 19 | earn_group_earns | Earn Group Earns | ✅ |
| 20 | shifts | Shifts | |
| 21 | shifts_groups | Shift Groups | |
| 22 | ded | Ded Codes | ✅ |
| 23 | optionratecodes | Option Rate Codes | ✅ |
| 24 | option_rates | Option Rates | ✅ |
| 25 | agegradedrates | Age Graded Rates | ✅ |
| 26 | ded_groups | Ded Groups | ✅ |
| 27 | ded_group_deds | Ded Group Deds | ✅ |
| 28 | gl_base_accts | GL Base Accounts | |
| 29 | gl_rules | GL Rules | |
| 30 | salary_grades | Salary Grades | ✅ |
| 31 | slrydifferentialgroups | Salary Differential Groups | |
| 32 | wc | WC Codes | |
| 33 | wc_risk_rates | WC Risk Rates | |
| 34 | jobfamilies | Job Families | ✅ |
| 35 | job | Job Code | ✅ |
| 36 | job_groups | Job Groups | |
| 37 | job_group_jobs | Job Group Jobs | |
| 38 | pto_benefits | PTO Benefits | |
| 39 | labor_union | Labor Union | |
| 40 | eduleveldegs | Education Levels | ✅ |
| 41 | edu_majors | Education Majors | ✅ |
| 42 | licensetype | License Type | ✅ |
| 43 | liccerts | Licenses & Certs | ✅ |
| 44 | provadminvendpayee | Providers | ✅ |

### B. NCU Codes (24 hubs)
Non-Configuration Update codes - lookup tables that don't require BRIT configuration.

### C. Inferred Hubs (28 hubs)
Derived from conversion template column analysis - represent data relationships.
