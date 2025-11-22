"""Projects API Router"""
from fastapi import APIRouter, HTTPException
import sys

sys.path.insert(0, '/app')
sys.path.insert(0, '/data')

from utils.database.supabase_client import get_supabase_client
from utils.functional_areas import FUNCTIONAL_AREAS

router = APIRouter()

@router.get("/projects")
async def get_projects():
    try:
        supabase = get_supabase_client()
        result = supabase.table("projects").select("*").execute()
        return {"projects": result.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/functional-areas")
async def get_functional_areas():
    return {"functional_areas": FUNCTIONAL_AREAS}
