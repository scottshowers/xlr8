# UKG One View - Domain Model Extraction
**Date:** January 10, 2026  
**Vendor:** UKG  
**Source:** UKG website, NelsonHall analysis, press releases  

---

## Executive Summary

| Metric | Count |
|--------|-------|
| **Total Hubs** | 69 |
| **Core Hubs** | 27 |
| **Domains** | 15 |
| **Product Focus** | Multi-country payroll aggregation - 160+ countries |

**Key Insight:** UKG One View is a **global payroll aggregation platform** - not a full HCM. It unifies payroll data from multiple in-country providers into a single view. Integrates with UKG Pro/Ready for complete HCM+Global Payroll solution.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       UKG ONE VIEW                               │
│         Multi-Country Payroll Aggregation Platform              │
│           160+ Countries | 120+ Currencies | 20+ Languages       │
└─────────────────────────────────────────────────────────────────┘
                              │
    ┌─────────────────────────┼─────────────────────────┐
    │                         │                         │
    ▼                         ▼                         ▼
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   CONNECT   │       │   DIRECT    │       │  ADVANCED   │
│             │       │             │       │             │
│ Aggregate   │       │ Sync +      │       │ Full E2E    │
│ Data        │       │ Validate    │       │ Control     │
│ Unified View│       │ Calculations│       │ + Automation│
└─────────────┘       └─────────────┘       └─────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
       ┌──────────┐    ┌──────────┐    ┌──────────┐
       │ MANAGED  │    │ PAYMENTS │    │ UKG PRO/ │
       │ SERVICES │    │          │    │  READY   │
       │          │    │Cross-    │    │          │
       │Outsourced│    │Border    │    │HCM + WFM │
       └──────────┘    └──────────┘    └──────────┘
```

---

## Product Tiers

| Tier | Description |
|------|-------------|
| **One View Connect** | Data aggregation, unified view across all providers |
| **One View Direct** | Single process for calculation sync and validation |
| **One View Advanced** | Full end-to-end control with automation |
| **One View Managed Services** | Outsourced payroll processing in 160+ countries |
| **One View Payments** | Cross-border money movement, 120+ currencies |

---

## Key Differentiators

1. **Bring Your Own Provider** - Works with existing in-country payroll vendors
2. **AI Perpetual Validation** - Real-time error detection before issues occur
3. **Single Pane of Glass** - One unified view regardless of provider mix
4. **160+ Countries** - Broadest coverage in global payroll
5. **NelsonHall Leader** - 2024 Leader in Multi-country Payroll
6. **Global Payroll Supplier of Year** - Global Payroll Association award

---

## Domain Highlights

### Global Payroll Core (6 hubs)
Multi-country payroll aggregation with provider management

### Validation (5 hubs)  
AI-powered perpetual validation with proactive alerts

### Payments (6 hubs)
Cross-border money movement in 120+ currencies

### Analytics (8 hubs)
Real-time global payroll reporting and metrics

---

## Integration with UKG Suite

When combined with UKG Pro or UKG Ready:
- Scheduling → Time → Payroll → Pay Slips (end-to-end)
- Single vendor for global HCM + payroll
- 120 currencies, 20+ languages, 160+ countries

---

## Deliverables

| File | Description |
|------|-------------|
| `ukg_oneview_schema_v1.json` | Full hub definitions (69 hubs) |
| `UKG_ONEVIEW_EXTRACTION.md` | This document |

---

## UKG Product Family Summary

| Product | Hubs | Focus |
|---------|------|-------|
| UKG WFM | 113 | Workforce Management |
| UKG Pro | 105 | Enterprise HCM |
| UKG Ready | 104 | SMB HCM |
| **UKG One View** | **69** | **Global Payroll Aggregation** |
| UKG Ben Admin (Prime) | - | Benefits (via PlanSource) |
| **UKG TOTAL** | **391** | **4 products** |
