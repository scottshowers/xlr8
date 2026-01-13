# CRM Domain Model Extraction
**Date:** January 10, 2026  
**Session Focus:** Customer Relationship Management platforms

---

## Executive Summary

| Product | Vendor | Hubs | Market Tier | Focus |
|---------|--------|------|-------------|-------|
| **Salesforce** | Salesforce | 94 | Enterprise | Multi-cloud CRM leader |
| **Dynamics 365 Sales/CE** | Microsoft | 77 | Enterprise | Dataverse + Power Platform |
| **HubSpot** | HubSpot | 54 | SMB/Mid | All-in-one inbound |
| **Zoho CRM** | Zoho | 50 | SMB/Mid | Zoho One ecosystem |
| **Freshsales** | Freshworks | 29 | SMB | Freddy AI, built-in phone |
| **Pipedrive** | Pipedrive | 25 | SMB | Pipeline-centric |
| **TOTAL** | | **329** | | |

---

## Market Segmentation

### Enterprise CRM (77-94 hubs)
| Product | Hubs | Key Differentiator |
|---------|------|-------------------|
| Salesforce | 94 | #1 CRM, multi-cloud, AppExchange |
| Dynamics 365 | 77 | Microsoft ecosystem, Field Service |

### Mid-Market CRM (50-54 hubs)
| Product | Hubs | Key Differentiator |
|---------|------|-------------------|
| HubSpot | 54 | Free tier, inbound marketing heritage |
| Zoho CRM | 50 | Affordable, Zoho One suite |

### SMB CRM (25-29 hubs)
| Product | Hubs | Key Differentiator |
|---------|------|-------------------|
| Freshsales | 29 | Freddy AI, built-in phone/email |
| Pipedrive | 25 | Visual pipeline, sales-focused |

---

## Cross-Platform Coverage Analysis

### Core CRM Objects (Present in ALL platforms)
- Lead
- Contact
- Account/Company/Organization
- Deal/Opportunity
- Activity (Task, Call, Email, Meeting)
- Note

### Mid-Market+ Features
- Quote/Proposal
- Product Catalog
- Pipeline (multiple)
- Workflow Automation
- Custom Objects/Fields

### Enterprise Features
- Territory Management
- Forecasting
- Field Service
- Knowledge Base
- Entitlements/SLAs
- Multi-currency

---

## Detection Patterns

### Salesforce
- Look for: Opportunity, Case, Campaign, Custom__c suffix
- API: `/services/data/v{version}/sobjects/`

### Dynamics 365
- Look for: Incident (=Case), Bookable Resource, systemuser
- API: Dataverse OData

### HubSpot
- Look for: objectTypeId (0-1=Contact, 0-2=Company, 0-3=Deal, 0-5=Ticket)
- API: `/crm/v3/objects/`

### Zoho CRM
- Look for: Module names (Leads, Deals, Accounts)
- Blueprint for process automation

### Pipedrive
- Look for: Person (not Contact), Organization (not Account)
- Pipeline/Stage focus

### Freshsales
- Look for: Freddy AI references, Sales Sequences
- Part of Freshworks ecosystem

---

## API Comparison

| Product | API Type | Auth | Rate Limits |
|---------|----------|------|-------------|
| Salesforce | REST/SOAP | OAuth 2.0 | Per-org limits |
| Dynamics 365 | OData | Azure AD | Per-user limits |
| HubSpot | REST | OAuth/API Key | 100/10s (free), higher paid |
| Zoho CRM | REST | OAuth 2.0 | Credits-based |
| Pipedrive | REST | API Token | 100/10s |
| Freshsales | REST | API Key | Tier-based |

---

## Deliverables

| File | Description |
|------|-------------|
| `salesforce_schema_v1.json` | Salesforce (94 hubs) |
| `dynamics_crm_schema_v1.json` | Dynamics 365 Sales/CE (77 hubs) |
| `hubspot_schema_v1.json` | HubSpot (54 hubs) |
| `zoho_crm_schema_v1.json` | Zoho CRM (50 hubs) |
| `freshsales_schema_v1.json` | Freshsales (29 hubs) |
| `pipedrive_schema_v1.json` | Pipedrive (25 hubs) |
| `CRM_EXTRACTION.md` | This summary |

---

## Running Grand Totals

| Category | Products | Hubs |
|----------|----------|------|
| HCM | 23 | 3,020 |
| Finance/ERP | 7 | 727 |
| CRM | 6 | 329 |
| **GRAND TOTAL** | **36** | **4,076** |

