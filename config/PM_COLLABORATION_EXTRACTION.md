# Project Management & Collaboration Extraction
**Date:** January 10, 2026

---

## Project Management Summary

| Product | Vendor | Hubs | Focus |
|---------|--------|------|-------|
| **Jira** | Atlassian | 47 | Agile/software development |
| **Asana** | Asana | 29 | Work management, goals |
| **ClickUp** | ClickUp | 28 | All-in-one productivity |
| **Smartsheet** | Smartsheet | 26 | Enterprise spreadsheet |
| **Monday.com** | Monday | 23 | Work OS, flexible boards |
| **Basecamp** | 37signals | 21 | Simple PM + communication |
| **Wrike** | Wrike | 20 | Enterprise work management |
| **Trello** | Atlassian | 16 | Simple kanban |
| **PM TOTAL** | | **210** | 8 products |

---

## Collaboration Summary

| Product | Vendor | Hubs | Focus |
|---------|--------|------|-------|
| **Microsoft Teams** | Microsoft | 33 | Hub for M365 |
| **Slack** | Salesforce | 26 | Team messaging |
| **Notion** | Notion | 24 | Docs + databases |
| **Confluence** | Atlassian | 18 | Team wiki |
| **COLLAB TOTAL** | | **101** | 4 products |

---

## Market Positioning

### Project Management Tiers

**Enterprise PM (26-47 hubs)**
- Jira: Dev teams standard, JQL, Service Management
- Smartsheet: Spreadsheet paradigm, resource mgmt
- Wrike: Cross-tagging, proofing

**Mid-Market PM (21-29 hubs)**
- Asana: Portfolios, goals, multiple views
- ClickUp: All-in-one, generous free tier
- Monday.com: Work OS positioning, highly flexible

**SMB PM (16-21 hubs)**
- Basecamp: Simple, flat pricing
- Trello: Visual kanban, Power-Ups

### Collaboration Tiers

**Enterprise (26-33 hubs)**
- Teams: M365 native, meetings, SharePoint
- Slack: Channels, 2600+ integrations

**Knowledge/Docs (18-24 hubs)**
- Notion: Blocks + databases
- Confluence: Wiki, Jira integration

---

## Cross-Platform Entities

### Core PM Objects (all platforms)
- Project/Board
- Task/Item/Card/Issue
- User/Member
- Comment

### Core Collab Objects (all platforms)
- Workspace/Team
- Channel/Space
- Message
- User

---

## Detection Patterns

| Product | Key Identifiers |
|---------|-----------------|
| Jira | Issue types (Epic, Story, Bug), JQL, Sprint |
| Asana | gid format, Section, Portfolio |
| Monday | Board, Pulse (legacy), Column values |
| Trello | Card, List, Power-Up |
| Slack | Channel ID (C...), User ID (U...), ts timestamp |
| Teams | Graph API, Team/Channel GUIDs |
| Notion | UUID format, Block types |

---

## Deliverables

### Project Management
| File | Hubs |
|------|------|
| `jira_schema_v1.json` | 47 |
| `asana_schema_v1.json` | 29 |
| `clickup_schema_v1.json` | 28 |
| `smartsheet_schema_v1.json` | 26 |
| `monday_schema_v1.json` | 23 |
| `basecamp_schema_v1.json` | 21 |
| `wrike_schema_v1.json` | 20 |
| `trello_schema_v1.json` | 16 |

### Collaboration
| File | Hubs |
|------|------|
| `teams_schema_v1.json` | 33 |
| `slack_schema_v1.json` | 26 |
| `notion_schema_v1.json` | 24 |
| `confluence_schema_v1.json` | 18 |

---

## Running Grand Totals

| Category | Products | Hubs |
|----------|----------|------|
| HCM | 23 | 3,020 |
| Finance/ERP | 7 | 727 |
| CRM | 6 | 329 |
| Project Management | 8 | 210 |
| Collaboration | 4 | 101 |
| **GRAND TOTAL** | **48** | **4,387** |

