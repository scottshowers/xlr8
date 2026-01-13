# ADP Streamline - Domain Model Extraction
**Date:** January 10, 2026  
**Vendor:** ADP  
**Source:** ADP website, product documentation, GetApp reviews  

---

## Executive Summary

| Metric | Count |
|--------|-------|
| **Total Hubs** | 61 |
| **Core Hubs** | 22 |
| **Domains** | 14 |
| **Product Focus** | Multi-country payroll aggregation - 140+ countries |

**Key Insight:** ADP Streamline is a **global payroll aggregation platform** using ADP's in-country partner network. The **StreamOnline portal** provides centralized visibility. Connects with **ADP GlobalView** for full HCM capabilities.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       ADP STREAMLINE                            │
│              Multi-Country Payroll Aggregation                  │
│                      140+ Countries                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
             ┌──────────────┐    ┌──────────────┐
             │ STREAMONLINE │    │   DATA HUB   │
             │    Portal    │    │              │
             │              │    │ HR System    │
             │ Dashboard    │    │ Sync         │
             │ Monitoring   │    │ Standardize  │
             │ Alerts       │    │              │
             └──────────────┘    └──────────────┘
                              │
    ┌─────────────────────────┼─────────────────────────┐
    │                         │                         │
    ▼                         ▼                         ▼
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│ IN-COUNTRY  │       │ IN-COUNTRY  │       │ IN-COUNTRY  │
│ PARTNER     │       │ PARTNER     │       │ PARTNER     │
│ (Country A) │       │ (Country B) │       │ (Country C) │
│             │       │             │       │             │
│ Local       │       │ Local       │       │ Local       │
│ Expertise   │       │ Expertise   │       │ Expertise   │
└─────────────┘       └─────────────┘       └─────────────┘
```

---

## Support Model

| Role | Responsibility |
|------|----------------|
| **Global Implementation Coordinator** | Project oversight, milestone tracking |
| **Service Relationship Manager** | Strategic initiatives, single point of contact |
| **In-Country Partner** | Local payroll processing, legislation monitoring |

---

## Key Differentiators

1. **140+ Countries** - Extensive global coverage
2. **In-Country Partner Network** - Local expertise on the ground
3. **StreamOnline Portal** - Centralized payroll visibility
4. **Legislative Bulletins** - Proactive law change notifications
5. **ISAE 3402 Certified** - Audit-ready security
6. **ADP GlobalView Integration** - Full HCM when needed
7. **Web-Based Interface** - No software installation required

---

## Domain Highlights

### In-Country Partner (5 hubs)
Local payroll specialist network with dedicated support roles

### StreamOnline (4 hubs)
Business process management portal with dashboards and alerts

### Data Hub (4 hubs)
HR system synchronization and data standardization

### Analytics (8 hubs)
Comprehensive reporting including HR modeling

---

## Related ADP Products

| Product | Description |
|---------|-------------|
| **ADP GlobalView** | Full global HCM suite (enterprise) |
| **ADP Celergo** | Alternative multi-country payroll |
| **ADP Workforce Now Global** | Mid-market global payroll integration |
| **ADP Workforce Now** | Domestic HCM (US/Canada) |

---

## Deliverables

| File | Description |
|------|-------------|
| `adp_streamline_schema_v1.json` | Full hub definitions (61 hubs) |
| `ADP_STREAMLINE_EXTRACTION.md` | This document |

---

## ADP Product Family Summary

| Product | Hubs | Focus |
|---------|------|-------|
| ADP WFN | 138 | HCM (domestic) |
| **ADP Streamline** | **61** | **Global Payroll Aggregation** |
| ADP GlobalView | - | Enterprise Global HCM |
| ADP Celergo | - | Multi-country Payroll |
| **ADP TOTAL** | **199** | **2 products extracted** |
