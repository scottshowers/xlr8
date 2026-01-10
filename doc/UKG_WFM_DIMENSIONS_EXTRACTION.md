# UKG WFM Dimensions - Domain Model Extraction
**Date:** January 10, 2026  
**Source:** developer.ukg.com/wfm/reference API Documentation  
**Purpose:** Hub-and-spoke schema for XLR8 universal analysis engine

---

## Executive Summary

| Metric | Count |
|--------|-------|
| **Total Hubs** | 113 |
| **Core Hubs** | 25 |
| **Domains** | 11 |
| **Shared with UKG Pro** | 3 |

**Key Finding:** UKG WFM Dimensions and UKG Pro are almost entirely separate products with only 3 overlapping concepts (Job, Location, Shift). This means XLR8 needs distinct domain models for each.

---

## Part 1: Domain Structure

### Activities (18 hubs)
Task and activity tracking for workforce operations.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Activity | `activity_code` | ✅ |
| Activity Action | `activity_action_code` | |
| Activity Customer | `activity_customer_code` | |
| Activity Form | `activity_form_code` | |
| Activity Form Profile | `activity_form_profile_code` | |
| Activity Profile | `activity_profile_code` | |
| Activity Query | `activity_query_code` | |
| Activity Query Profile | `activity_query_profile_code` | |
| Activity Resource | `activity_resource_code` | |
| Activity Results Template | `activity_results_template_code` | |
| Activity Setting | `activity_setting_code` | |
| Activity Shift | `activity_shift_code` | |
| Activity Team | `activity_team_code` | |
| Activity Team Segment | `activity_team_segment_code` | |
| Field Definition | `field_definition_code` | |
| Result Code | `result_code` | |
| Result Code Profile | `result_code_profile_code` | |
| Unit of Measure | `unit_of_measure_code` | |

### Attendance (16 hubs)
Attendance tracking, policies, and point systems.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Attendance Action | `attendance_action_code` | ✅ |
| Attendance Event | `attendance_event_code` | ✅ |
| Attendance Pattern | `attendance_pattern_code` | |
| Attendance Policy | `attendance_policy_code` | ✅ |
| Attendance Profile | `attendance_profile_code` | ✅ |
| Balance Type | `attendance_balance_type_code` | |
| Combined Event | `combined_event_code` | |
| Discipline Level | `discipline_level_code` | |
| Discipline Policy | `discipline_policy_code` | |
| Formula Policy | `formula_policy_code` | |
| Lost Time Event | `lost_time_event_code` | |
| Perfect Attendance Definition | `perfect_attendance_def_code` | |
| Perfect Attendance Policy | `perfect_attendance_policy_code` | |
| Previous Action Policy | `previous_action_policy_code` | |
| Total Balance Policy | `total_balance_policy_code` | |
| Tracking Period | `tracking_period_code` | |

### Organization (10 hubs)
Organizational structure and hierarchy.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Location | `location_code` | ✅ |
| Location Type | `location_type_code` | ✅ |
| Location Set | `location_set_code` | |
| Location Attribute | `location_attribute_code` | |
| Job | `job_code` | ✅ |
| Labor Category | `labor_category_code` | ✅ |
| Labor Category Entry | `labor_category_entry_code` | ✅ |
| Labor Category List | `labor_category_list_code` | |
| Labor Category Profile | `labor_category_profile_code` | |
| Generic Location | `generic_location_code` | |

### Timekeeping (10 hubs)
Time capture and totals.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Pay Code | `pay_code` | ✅ |
| Pay Code Edit | `pay_code_edit_code` | |
| Punch | `punch_code` | |
| Timecard | `timecard_code` | |
| Work Rule | `work_rule_code` | ✅ |
| Exception Type | `exception_type_code` | |
| Accrual Code | `accrual_code` | ✅ |
| Accrual Policy | `accrual_policy_code` | ✅ |
| Holiday | `holiday_code` | ✅ |
| Holiday Profile | `holiday_profile_code` | |

### Scheduling (8 hubs)
Schedule management and patterns.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Schedule Pattern | `schedule_pattern_code` | ✅ |
| Schedule Group | `schedule_group_code` | |
| Shift | `shift_code` | ✅ |
| Shift Template | `shift_template_code` | |
| Schedule Tag | `schedule_tag_code` | |
| Open Shift | `open_shift_code` | |
| Schedule Zone | `schedule_zone_code` | |
| Availability Pattern | `availability_pattern_code` | |

### Common Resources - Core (15 hubs)
Core organizational and access configuration.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Cost Center | `cost_center_code` | ✅ |
| Employee Group | `employee_group_code` | ✅ |
| Function Access Profile | `function_access_profile_code` | ✅ |
| Role Profile | `role_profile_code` | ✅ |
| Access Control Point | `access_control_point_code` | |
| Access Method Profile | `access_method_profile_code` | |
| Control Center Profile | `control_center_profile_code` | |
| Delegate Profile | `delegate_profile_code` | |
| Device Group | `device_group_code` | |
| Display Profile | `display_profile_code` | |
| Generic Data Access Profile | `data_access_profile_code` | |
| Hyperfind Profile | `hyperfind_profile_code` | |
| Notification Profile | `notification_profile_code` | |
| Process Profile | `process_profile_code` | |
| Transfer Display Profile | `transfer_display_profile_code` | |

### Common Resources - Time (10 hubs)
Time and scheduling configuration.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Hours of Operation | `hours_of_operation_code` | ✅ |
| Timezone | `timezone_code` | ✅ |
| Pay Period Timespan | `pay_period_timespan_code` | ✅ |
| Hours of Operation Override | `hours_of_operation_override_code` | |
| Known IP Address | `known_ip_address_code` | |
| WiFi Access Point | `wifi_access_point_code` | |
| WiFi Network | `wifi_network_code` | |
| GPS Known Place | `gps_known_place_code` | |
| Symbolic Period | `symbolic_period_code` | |
| Fiscal Calendar | `fiscal_calendar_code` | |

### Person (5 hubs)
Employee/person core data.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Person | `person_code` | ✅ |
| Employment Term | `employment_term_code` | |
| Badge | `badge_code` | |
| User Account | `user_account_code` | |
| Employee Photo | `employee_photo_code` | |

### Forecasting (9 hubs)
Labor forecasting and planning.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Adjustment Driver Setting | `adjustment_driver_setting_code` | |
| Budget Distribution Type | `budget_distribution_type_code` | |
| Category Property Set | `category_property_set_code` | |
| Combined Labor Distribution | `combined_labor_distribution_code` | |
| Custom Driver | `custom_driver_code` | |
| Forecast Planner Profile | `forecast_planner_profile_code` | |
| Forecast Planner Setting | `forecast_planner_setting_code` | |
| Volume Driver | `volume_driver_code` | |
| Labor Standard | `labor_standard_code` | |

### Requests (7 hubs)
Employee self-service requests.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Time Off Request | `time_off_request_code` | |
| Availability Request | `availability_request_code` | |
| Cover Request | `cover_request_code` | |
| Swap Request | `swap_request_code` | |
| Open Shift Request | `open_shift_request_code` | |
| Self-Schedule Request | `self_schedule_request_code` | |
| Request Subtype | `request_subtype_code` | |

### Payroll Integration (5 hubs)
Payroll export and integration.

| Hub | Semantic Type | Core |
|-----|---------------|------|
| Payroll Table | `payroll_table_code` | |
| Payroll Export | `payroll_export_code` | |
| Currency Definition | `currency_definition_code` | |
| Currency Policy | `currency_policy_code` | |
| Exchange Rate | `exchange_rate_code` | |

---

## Part 2: Cross-Product Comparison

### UKG Pro vs WFM Dimensions

| Aspect | UKG Pro | WFM Dimensions |
|--------|---------|----------------|
| **Focus** | HCM + Payroll | Workforce Management |
| **Hub Count** | 105 | 113 |
| **Core Function** | Employee master, earnings, deductions, taxes, benefits | Scheduling, timekeeping, attendance, activities |

### Shared Concepts (Only 3!)

| Concept | Pro Semantic Type | WFM Semantic Type |
|---------|-------------------|-------------------|
| Job | `job_code_code` | `job_code` |
| Location | `location_code` | `location_code` |
| Shift | `shift_code` | `shift_code` |

### Product-Specific Concepts

**UKG Pro Only (HCM/Payroll):**
- Earnings, Deductions, Taxes
- Benefits, PPACA/ACA
- Component Company, Master Company
- Salary Grades, Workers Comp
- GL Rules, Payroll Models

**WFM Dimensions Only (Workforce):**
- Activities, Activity Teams
- Attendance Policies, Events
- Scheduling, Open Shifts
- Labor Categories
- Work Rules, Pay Codes
- Forecasting, Labor Standards

---

## Part 3: Spoke Patterns (Data Relationships)

### Key WFM Spoke Patterns

```
Employee → Location (primary work location)
Employee → Job (primary job assignment)
Employee → Labor Category Entry (labor assignments)
Punch → Location (punch location)
Punch → Job (punch job transfer)
Punch → Pay Code (hours type)
Schedule → Shift (shift assignment)
Schedule → Employee (schedule owner)
Timecard → Pay Code (hours allocation)
Timecard → Work Rule (calculation rule)
Attendance Event → Attendance Policy (triggering policy)
Activity → Activity Team (team assignment)
Activity → Cost Center (cost allocation)
```

### Column Pattern Examples

| Column Pattern | Hub | Entity |
|----------------|-----|--------|
| `personNumber`, `person_number`, `empId` | person | All employee tables |
| `locationId`, `location_id`, `locId` | location | Schedule, Punch, Timecard |
| `jobId`, `job_id`, `jobName` | job | Employee, Schedule, Punch |
| `payCodeId`, `pay_code`, `paycode` | pay | Timecard, Punch |
| `laborCategoryId`, `labor_category` | labor_category | Employee, Schedule |
| `costCenterId`, `cost_center` | cost_center | Punch, Activity |
| `shiftId`, `shift_id`, `shift` | shift | Schedule, Open Shift |
| `workRuleId`, `work_rule` | work_rule | Employee, Schedule |

---

## Part 4: API Structure

### Base URL Pattern
```
https://{{hostname}}/api/v1/{{domain}}/{{resource}}
```

### Key Endpoints

| Domain | Resource | Operations |
|--------|----------|------------|
| `/commons/persons` | Person | CRUD, multi_read |
| `/commons/locations` | Location | CRUD, hierarchy |
| `/commons/labor_categories` | Labor Category | CRUD |
| `/commons/cost_centers` | Cost Center | CRUD |
| `/timekeeping/pay_codes` | Pay Code | CRUD |
| `/timekeeping/work_rules` | Work Rule | CRUD |
| `/scheduling/shifts` | Shift | CRUD |
| `/scheduling/schedule_patterns` | Schedule Pattern | CRUD |
| `/attendance/policies` | Attendance Policy | CRUD |
| `/forecasting/labor_standards` | Labor Standard | CRUD |

---

## Part 5: XLR8 Integration Recommendations

### 1. Separate Domain Models
Maintain distinct models for Pro and WFM:
```
vendor_models/
  ukg_pro/
    hub_registry.json
    spoke_patterns.json
  ukg_wfm/
    hub_registry.json
    spoke_patterns.json
```

### 2. Product Detection
When data is uploaded, detect which product:
- **Pro indicators:** Earnings, Deductions, Tax codes, BRIT structure
- **WFM indicators:** Pay Codes, Punches, Schedules, Labor Categories

### 3. Shared Entity Mapping
For the 3 shared concepts, normalize:
```python
# When Pro job_code_code detected, map to unified job_code
# When WFM job_code detected, map to unified job_code
```

### 4. Spoke Pattern Application
Apply product-specific spoke patterns based on detection.

---

## Deliverables

| File | Description |
|------|-------------|
| `ukg_wfm_dimensions_schema_v1.json` | Full hub definitions with domains |
| `ukg_unified_vocabulary.json` | Combined Pro + WFM vocabulary |
| `UKG_WFM_DIMENSIONS_EXTRACTION.md` | This document |

---

## Next Steps

1. **Deploy to Reference Library** - Load WFM schema into XLR8
2. **Build Spoke Patterns** - Extract column→hub mappings from sample data
3. **Test Detection** - Upload WFM data and verify hub detection
4. **Move to Next Vendor** - UKG Ready, Workday, Dayforce, Oracle, SAP
