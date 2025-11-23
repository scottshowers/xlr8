from fastapi import APIRouter, HTTPException
import sys

sys.path.insert(0, '/app')
sys.path.insert(0, '/data')

from utils.database.supabase_client import get_supabase

router = APIRouter()

FUNCTIONAL_AREAS = [
    "Payroll", "Time & Attendance", "Benefits", "HR", 
    "Recruiting", "Learning", "Performance", "Compensation"
]

@router.get("/projects")
async def get_projects():
    try:
        supabase = get_supabase()
        if not supabase:
            return {"projects": []}
        result = supabase.table("projects").select("*").execute()
        return {"projects": result.data}
    except Exception as e:
        return {"projects": []}

@router.get("/functional-areas")
async def get_functional_areas():
    return {"functional_areas": FUNCTIONAL_AREAS}
