#!/usr/bin/env python3
"""
Seed Demo Projects
==================
Creates realistic-looking demo projects for XLR8 demos.

Usage:
    python scripts/seed_demo_projects.py

Projects created:
1. Meridian Healthcare Systems - HCM Implementation (UKG Pro)
2. Cobalt Financial Group - Year-End (Workday HCM + Workday Financials)
3. Pinnacle Manufacturing - Migration (ADP WFN → UKG Pro)
4. Horizon Retail Partners - Assessment (Dayforce)
"""

import os
import sys
import json
import httpx
from datetime import datetime, timedelta

API_BASE = os.getenv("API_BASE", "https://hcmpact-xlr8-production.up.railway.app")

DEMO_PROJECTS = [
    {
        "name": "Meridian Healthcare Systems - Implementation",
        "customer": "Meridian Healthcare Systems",
        "type": "Implementation",
        "product": "UKG Pro",
        "systems": ["ukg-pro"],
        "domains": ["hcm"],
        "engagement_type": "implementation",
        "target_go_live": (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d"),
        "lead_name": "Sarah Chen",
        "notes": "12,000 employees across 45 locations. Converting from legacy Kronos system. Go-live aligned with Q2 payroll cycle.",
        "demo_stats": {
            "employees": "12,847",
            "locations": "45",
            "annual_payroll": "$892M",
            "departments": "127",
            "findings": {"total": 47, "critical": 6, "warning": 18, "info": 23},
            "progress": 68
        }
    },
    {
        "name": "Cobalt Financial Group - Year-End",
        "customer": "Cobalt Financial Group",
        "type": "Year-End",
        "product": "Workday HCM",
        "systems": ["workday-hcm", "workday-financials"],
        "domains": ["hcm", "finance"],
        "engagement_type": "year-end",
        "target_go_live": "2026-01-31",
        "lead_name": "Marcus Williams",
        "notes": "Year-end readiness for dual HCM/Finance environment. Focus on W-2 compliance and GL reconciliation. Audit deadline Feb 15.",
        "demo_stats": {
            "employees": "3,421",
            "locations": "12",
            "annual_payroll": "$478M",
            "departments": "34",
            "findings": {"total": 31, "critical": 4, "warning": 12, "info": 15},
            "progress": 82
        }
    },
    {
        "name": "Pinnacle Manufacturing - Migration",
        "customer": "Pinnacle Manufacturing Inc",
        "type": "Migration",
        "product": "UKG Pro",
        "systems": ["ukg-pro", "adp-wfn"],
        "domains": ["hcm"],
        "engagement_type": "migration",
        "target_go_live": (datetime.now() + timedelta(days=120)).strftime("%Y-%m-%d"),
        "lead_name": "Jennifer Park",
        "notes": "ADP Workforce Now to UKG Pro migration. Union environment with complex time rules. Parallel payroll planned for 2 cycles.",
        "demo_stats": {
            "employees": "8,234",
            "locations": "28",
            "annual_payroll": "$612M",
            "departments": "89",
            "findings": {"total": 62, "critical": 11, "warning": 24, "info": 27},
            "progress": 45
        }
    },
    {
        "name": "Horizon Retail Partners - Assessment",
        "customer": "Horizon Retail Partners",
        "type": "Assessment",
        "product": "Ceridian Dayforce",
        "systems": ["ceridian-dayforce"],
        "domains": ["hcm"],
        "engagement_type": "assessment",
        "target_go_live": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
        "lead_name": "David Torres",
        "notes": "Health check after 18 months post-implementation. Suspected configuration drift and unused features. Optimize before year-end.",
        "demo_stats": {
            "employees": "22,156",
            "locations": "312",
            "annual_payroll": "$1.2B",
            "departments": "45",
            "findings": {"total": 89, "critical": 8, "warning": 31, "info": 50},
            "progress": 23
        }
    }
]


def create_project(project_data: dict) -> dict:
    """Create a single demo project via API."""
    
    demo_stats = project_data.pop("demo_stats", {})
    
    # Store demo_stats in notes for retrieval
    if demo_stats:
        project_data["notes"] = f"{project_data.get('notes', '')}\n\n[DEMO_STATS]{json.dumps(demo_stats)}[/DEMO_STATS]"
    
    print(f"Creating: {project_data['name']}...")
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{API_BASE}/api/projects/create",
                json=project_data
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"  ✓ Created: {result.get('project', {}).get('id')}")
                return result
            else:
                print(f"  ✗ Failed: {response.status_code} - {response.text[:200]}")
                return None
                
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return None


def main():
    print("=" * 60)
    print("XLR8 Demo Project Seeder")
    print("=" * 60)
    print(f"API: {API_BASE}")
    print(f"Projects to create: {len(DEMO_PROJECTS)}")
    print("=" * 60)
    
    created = 0
    for project in DEMO_PROJECTS:
        result = create_project(project.copy())
        if result:
            created += 1
    
    print("=" * 60)
    print(f"Done! Created {created}/{len(DEMO_PROJECTS)} projects")
    print("=" * 60)


if __name__ == "__main__":
    main()
