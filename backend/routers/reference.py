"""
XLR8 REFERENCE TRUTH API
========================

API endpoints for:
- Systems (UKG Pro, Workday, SAP, etc.)
- Domains (HCM, Finance, Compliance, etc.)
- Functional Areas (Payroll, Benefits, GL, AP, etc.)
- Detection (auto-detect from files)
- Project Context (get/set/confirm)

A project can have MULTIPLE systems, domains, and functional areas.

Author: XLR8 Team
Version: 1.0.0
Deploy to: backend/routers/reference.py
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["reference"])


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class SystemResponse(BaseModel):
    id: str
    code: str
    name: str
    vendor: str
    domain_code: Optional[str] = None
    domain_name: Optional[str] = None
    additional_domains: List[str] = []
    description: Optional[str] = None


class DomainResponse(BaseModel):
    id: str
    code: str
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    display_order: int = 0


class FunctionalAreaResponse(BaseModel):
    id: str
    code: str
    name: str
    description: Optional[str] = None
    domain_code: str
    domain_name: str
    display_order: int = 0


class EngagementTypeResponse(BaseModel):
    code: str
    name: str
    description: str


class DetectionRequest(BaseModel):
    filename: Optional[str] = None
    columns: Optional[List[str]] = None
    values: Optional[Dict[str, List[str]]] = None
    sheet_names: Optional[List[str]] = None


class DetectedItem(BaseModel):
    code: str
    name: Optional[str] = None
    confidence: float


class DetectionResponse(BaseModel):
    systems: List[DetectedItem] = []
    domains: List[DetectedItem] = []
    functional_areas: List[Dict] = []
    primary_system: Optional[DetectedItem] = None
    primary_domain: Optional[DetectedItem] = None
    match_count: int = 0
    columns_analyzed: int = 0
    detection_time_ms: int = 0


class ProjectContextResponse(BaseModel):
    id: Optional[str] = None
    name: str
    systems: List[str] = []
    domains: List[str] = []
    functional_areas: List[Dict] = []
    engagement_type: Optional[str] = None
    context_confirmed: bool = False
    detected_context: Optional[Dict] = None


class ConfirmContextRequest(BaseModel):
    system_codes: Optional[List[str]] = Field(None, description="List of system codes")
    domain_codes: Optional[List[str]] = Field(None, description="List of domain codes")
    functional_areas: Optional[List[Dict]] = Field(None, description="List of {domain, area} dicts")
    engagement_type: Optional[str] = Field(None, description="Engagement type code")


class SignatureCreateRequest(BaseModel):
    pattern: str
    pattern_type: str = Field(..., description="file_name, column_name, column_value, sheet_name")
    detects_system_code: Optional[str] = None
    detects_domain_code: Optional[str] = None
    detects_functional_area_code: Optional[str] = None
    confidence: float = 0.80
    priority: int = 0
    description: Optional[str] = None
    example: Optional[str] = None


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_supabase():
    """Get Supabase client."""
    try:
        from utils.database.supabase_client import get_supabase as _get_supabase
        return _get_supabase()
    except ImportError:
        try:
            from backend.utils.database.supabase_client import get_supabase as _get_supabase
            return _get_supabase()
        except ImportError:
            return None


def get_detection_service():
    """Get detection service."""
    try:
        from utils.detection_service import get_detection_service as _get_service
        return _get_service()
    except ImportError:
        try:
            from backend.utils.detection_service import get_detection_service as _get_service
            return _get_service()
        except ImportError:
            return None


# =============================================================================
# SYSTEM ENDPOINTS
# =============================================================================

@router.get("/systems", response_model=List[SystemResponse])
async def get_systems(
    domain: Optional[str] = Query(None, description="Filter by primary domain code"),
    vendor: Optional[str] = Query(None, description="Filter by vendor name")
):
    """
    Get all available systems.
    
    Optionally filter by domain (hcm, finance, etc.) or vendor (UKG, Workday, etc.)
    """
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=500, detail="Database unavailable")
    
    try:
        query = supabase.table('v_systems').select('*')
        
        if domain:
            query = query.eq('domain_code', domain)
        
        result = query.execute()
        
        systems = []
        for row in (result.data or []):
            if vendor and row.get('vendor', '').lower() != vendor.lower():
                continue
            systems.append(SystemResponse(
                id=row.get('id', ''),
                code=row.get('code', ''),
                name=row.get('name', ''),
                vendor=row.get('vendor', ''),
                domain_code=row.get('domain_code'),
                domain_name=row.get('domain_name'),
                additional_domains=row.get('additional_domains') or [],
                description=row.get('description')
            ))
        
        return sorted(systems, key=lambda s: s.name)
        
    except Exception as e:
        logger.error(f"[REFERENCE] Get systems failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/systems/{code}", response_model=SystemResponse)
async def get_system(code: str):
    """Get a specific system by code."""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=500, detail="Database unavailable")
    
    try:
        result = supabase.table('v_systems').select('*').eq('code', code).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail=f"System '{code}' not found")
        
        row = result.data[0]
        return SystemResponse(
            id=row.get('id', ''),
            code=row.get('code', ''),
            name=row.get('name', ''),
            vendor=row.get('vendor', ''),
            domain_code=row.get('domain_code'),
            domain_name=row.get('domain_name'),
            additional_domains=row.get('additional_domains') or [],
            description=row.get('description')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[REFERENCE] Get system failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vendors")
async def get_vendors():
    """Get list of unique vendors."""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=500, detail="Database unavailable")
    
    try:
        result = supabase.table('systems').select('vendor').eq('is_active', True).execute()
        
        vendors = sorted(set(row['vendor'] for row in (result.data or []) if row.get('vendor')))
        
        return {"vendors": vendors}
        
    except Exception as e:
        logger.error(f"[REFERENCE] Get vendors failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# DOMAIN ENDPOINTS
# =============================================================================

@router.get("/domains", response_model=List[DomainResponse])
async def get_domains():
    """Get all available domains."""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=500, detail="Database unavailable")
    
    try:
        result = supabase.table('domains').select('*').eq('is_active', True).order('display_order').execute()
        
        return [
            DomainResponse(
                id=row.get('id', ''),
                code=row.get('code', ''),
                name=row.get('name', ''),
                description=row.get('description'),
                icon=row.get('icon'),
                color=row.get('color'),
                display_order=row.get('display_order', 0)
            )
            for row in (result.data or [])
        ]
        
    except Exception as e:
        logger.error(f"[REFERENCE] Get domains failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/domains/{code}", response_model=DomainResponse)
async def get_domain(code: str):
    """Get a specific domain by code."""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=500, detail="Database unavailable")
    
    try:
        result = supabase.table('domains').select('*').eq('code', code).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail=f"Domain '{code}' not found")
        
        row = result.data[0]
        return DomainResponse(
            id=row.get('id', ''),
            code=row.get('code', ''),
            name=row.get('name', ''),
            description=row.get('description'),
            icon=row.get('icon'),
            color=row.get('color'),
            display_order=row.get('display_order', 0)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[REFERENCE] Get domain failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# FUNCTIONAL AREA ENDPOINTS
# =============================================================================

@router.get("/functional-areas", response_model=List[FunctionalAreaResponse])
async def get_functional_areas(
    domain: Optional[str] = Query(None, description="Filter by domain code")
):
    """Get all functional areas, optionally filtered by domain."""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=500, detail="Database unavailable")
    
    try:
        query = supabase.table('v_functional_areas').select('*')
        
        if domain:
            query = query.eq('domain_code', domain)
        
        result = query.order('display_order').execute()
        
        return [
            FunctionalAreaResponse(
                id=row.get('id', ''),
                code=row.get('code', ''),
                name=row.get('name', ''),
                description=row.get('description'),
                domain_code=row.get('domain_code', ''),
                domain_name=row.get('domain_name', ''),
                display_order=row.get('display_order', 0)
            )
            for row in (result.data or [])
        ]
        
    except Exception as e:
        logger.error(f"[REFERENCE] Get functional areas failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/functional-areas/grouped")
async def get_functional_areas_grouped():
    """Get functional areas grouped by domain."""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=500, detail="Database unavailable")
    
    try:
        result = supabase.table('v_functional_areas').select('*').order('display_order').execute()
        
        grouped = {}
        for row in (result.data or []):
            domain = row.get('domain_code', 'other')
            if domain not in grouped:
                grouped[domain] = {
                    'domain_code': domain,
                    'domain_name': row.get('domain_name', domain),
                    'areas': []
                }
            grouped[domain]['areas'].append({
                'code': row.get('code'),
                'name': row.get('name'),
                'description': row.get('description')
            })
        
        return {"grouped": list(grouped.values())}
        
    except Exception as e:
        logger.error(f"[REFERENCE] Get grouped functional areas failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ENGAGEMENT TYPE ENDPOINTS
# =============================================================================

@router.get("/engagement-types", response_model=List[EngagementTypeResponse])
async def get_engagement_types():
    """Get available engagement types for projects."""
    service = get_detection_service()
    if service:
        types = service.get_engagement_types()
        return [EngagementTypeResponse(**t) for t in types]
    
    # Fallback
    return [
        EngagementTypeResponse(code='implementation', name='New Implementation', description='Net-new system implementation'),
        EngagementTypeResponse(code='support', name='Ongoing Support', description='Production support and maintenance'),
        EngagementTypeResponse(code='compliance', name='Compliance Review', description='Regulatory compliance assessment'),
    ]


# =============================================================================
# DETECTION ENDPOINTS
# =============================================================================

@router.post("/detect", response_model=DetectionResponse)
async def detect_context(request: DetectionRequest):
    """
    Detect systems, domains, and functional areas from file characteristics.
    
    Provide any combination of:
    - filename: Name of uploaded file
    - columns: List of column names
    - values: Dict of column_name -> sample values
    - sheet_names: List of Excel sheet names
    """
    service = get_detection_service()
    if not service:
        raise HTTPException(status_code=500, detail="Detection service unavailable")
    
    try:
        result = service.detect(
            filename=request.filename,
            columns=request.columns,
            values=request.values,
            sheet_names=request.sheet_names
        )
        
        return DetectionResponse(
            systems=[DetectedItem(**s) for s in result.systems],
            domains=[DetectedItem(**d) for d in result.domains],
            functional_areas=result.functional_areas,
            primary_system=DetectedItem(**result.primary_system) if result.primary_system else None,
            primary_domain=DetectedItem(**result.primary_domain) if result.primary_domain else None,
            match_count=len(result.all_matches),
            columns_analyzed=result.columns_analyzed,
            detection_time_ms=result.detection_time_ms
        )
        
    except Exception as e:
        logger.error(f"[REFERENCE] Detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# PROJECT CONTEXT ENDPOINTS
# =============================================================================

@router.get("/projects/{project_id}/context", response_model=ProjectContextResponse)
async def get_project_context(project_id: str):
    """Get the detected/confirmed context for a project."""
    service = get_detection_service()
    if not service:
        raise HTTPException(status_code=500, detail="Detection service unavailable")
    
    try:
        context = service.get_project_context(project_id)
        
        if not context:
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
        
        return ProjectContextResponse(
            id=context.get('id'),
            name=context.get('name', project_id),
            systems=context.get('systems') or [],
            domains=context.get('domains') or [],
            functional_areas=context.get('functional_areas') or [],
            engagement_type=context.get('engagement_type'),
            context_confirmed=context.get('context_confirmed', False),
            detected_context=context.get('detected_context')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[REFERENCE] Get project context failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/context/confirm")
async def confirm_project_context(project_id: str, request: ConfirmContextRequest):
    """
    Confirm or override the detected project context.
    
    Call this when user confirms the auto-detected context or manually
    selects different systems/domains.
    """
    service = get_detection_service()
    if not service:
        raise HTTPException(status_code=500, detail="Detection service unavailable")
    
    try:
        success = service.confirm_project_context(
            project_id=project_id,
            system_codes=request.system_codes,
            domain_codes=request.domain_codes,
            functional_areas=request.functional_areas,
            engagement_type=request.engagement_type
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to confirm context")
        
        return {"status": "success", "message": "Project context confirmed"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[REFERENCE] Confirm context failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/detect")
async def run_project_detection(project_id: str):
    """
    Run detection for a project based on its existing uploaded files.
    
    Queries the project's tables and columns from DuckDB,
    runs detection, and updates the project context.
    """
    service = get_detection_service()
    if not service:
        raise HTTPException(status_code=500, detail="Detection service unavailable")
    
    try:
        # Get DuckDB handler
        try:
            from utils.structured_data_handler import StructuredDataHandler
        except ImportError:
            from backend.utils.structured_data_handler import StructuredDataHandler
        
        handler = StructuredDataHandler()
        
        # Get all tables for project
        tables_result = handler.conn.execute(f"""
            SELECT table_name, display_name, file_name
            FROM _schema_metadata
            WHERE project = '{project_id}'
        """).fetchall()
        
        if not tables_result:
            raise HTTPException(status_code=404, detail=f"No tables found for project '{project_id}'")
        
        # Collect all columns and file names
        all_columns = []
        file_names = set()
        
        for table_name, display_name, file_name in tables_result:
            if file_name:
                file_names.add(file_name)
            
            try:
                cols = handler.conn.execute(f"PRAGMA table_info('{table_name}')").fetchall()
                for col in cols:
                    all_columns.append(col[1])
            except:
                pass
        
        # Run detection
        result = service.detect(
            filename=list(file_names)[0] if file_names else None,
            columns=all_columns
        )
        
        # Update project context
        service.update_project_context(project_id, result)
        
        return {
            "status": "success",
            "detection": result.to_dict(),
            "files_analyzed": list(file_names),
            "columns_analyzed": len(all_columns)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[REFERENCE] Project detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# DETECTION SIGNATURE ADMIN ENDPOINTS
# =============================================================================

@router.get("/admin/signatures")
async def get_signatures(
    pattern_type: Optional[str] = Query(None, description="Filter by pattern type"),
    system_code: Optional[str] = Query(None, description="Filter by system"),
    domain_code: Optional[str] = Query(None, description="Filter by domain"),
    limit: int = Query(100, description="Max results")
):
    """Get detection signatures (admin view)."""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=500, detail="Database unavailable")
    
    try:
        query = supabase.table('v_detection_signatures').select('*')
        
        if pattern_type:
            query = query.eq('pattern_type', pattern_type)
        if system_code:
            query = query.eq('system_code', system_code)
        if domain_code:
            query = query.eq('domain_code', domain_code)
        
        result = query.limit(limit).execute()
        
        return {
            "signatures": result.data or [],
            "count": len(result.data or [])
        }
        
    except Exception as e:
        logger.error(f"[REFERENCE] Get signatures failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/signatures")
async def create_signature(request: SignatureCreateRequest):
    """Create a new detection signature."""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=500, detail="Database unavailable")
    
    try:
        data = {
            'pattern': request.pattern,
            'pattern_type': request.pattern_type,
            'confidence': request.confidence,
            'priority': request.priority,
            'description': request.description,
            'example': request.example
        }
        
        # Look up IDs from codes
        if request.detects_system_code:
            sys_result = supabase.table('systems').select('id').eq('code', request.detects_system_code).execute()
            if sys_result.data:
                data['detects_system_id'] = sys_result.data[0]['id']
            else:
                raise HTTPException(status_code=400, detail=f"System '{request.detects_system_code}' not found")
        
        if request.detects_domain_code:
            dom_result = supabase.table('domains').select('id').eq('code', request.detects_domain_code).execute()
            if dom_result.data:
                data['detects_domain_id'] = dom_result.data[0]['id']
            else:
                raise HTTPException(status_code=400, detail=f"Domain '{request.detects_domain_code}' not found")
        
        if request.detects_functional_area_code:
            fa_result = supabase.table('functional_areas').select('id').eq('code', request.detects_functional_area_code).execute()
            if fa_result.data:
                data['detects_functional_area_id'] = fa_result.data[0]['id']
            else:
                raise HTTPException(status_code=400, detail=f"Functional area '{request.detects_functional_area_code}' not found")
        
        result = supabase.table('detection_signatures').insert(data).execute()
        
        if result.data:
            return {"status": "success", "id": result.data[0]['id']}
        
        raise HTTPException(status_code=500, detail="Insert failed")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[REFERENCE] Create signature failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/admin/signatures/{signature_id}")
async def delete_signature(signature_id: str):
    """Delete (deactivate) a detection signature."""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=500, detail="Database unavailable")
    
    try:
        supabase.table('detection_signatures').update({'is_active': False}).eq('id', signature_id).execute()
        return {"status": "success", "message": "Signature deactivated"}
        
    except Exception as e:
        logger.error(f"[REFERENCE] Delete signature failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# STATS ENDPOINT
# =============================================================================

@router.get("/stats")
async def get_reference_stats():
    """Get counts of reference data."""
    supabase = get_supabase()
    if not supabase:
        raise HTTPException(status_code=500, detail="Database unavailable")
    
    try:
        systems = supabase.table('systems').select('id', count='exact').eq('is_active', True).execute()
        domains = supabase.table('domains').select('id', count='exact').eq('is_active', True).execute()
        func_areas = supabase.table('functional_areas').select('id', count='exact').eq('is_active', True).execute()
        signatures = supabase.table('detection_signatures').select('id', count='exact').eq('is_active', True).execute()
        
        return {
            "systems": systems.count or 0,
            "domains": domains.count or 0,
            "functional_areas": func_areas.count or 0,
            "detection_signatures": signatures.count or 0
        }
        
    except Exception as e:
        logger.error(f"[REFERENCE] Get stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
