"""
Projects Router - Complete CRUD
Fixed to use correct ProjectModel methods: get_all(), create(), update(), delete()
Updated: January 4, 2026 - Added systems, domains, functional_areas, engagement_type support
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import sys
import logging

sys.path.insert(0, '/app')
sys.path.insert(0, '/data')

from utils.database.models import ProjectModel

logger = logging.getLogger(__name__)

router = APIRouter()


class ProjectCreate(BaseModel):
    """Schema for creating a project"""
    name: str
    customer: str
    product: Optional[str] = None  # UKG Pro, WFM Dimensions, UKG Ready
    type: str = "Implementation"  # Frontend sends 'type'
    start_date: Optional[str] = None
    notes: Optional[str] = None
    playbooks: Optional[List[str]] = []  # Array of playbook IDs
    # New scope fields
    systems: Optional[List[str]] = []  # Array of system codes
    domains: Optional[List[str]] = []  # Array of domain codes
    functional_areas: Optional[List[dict]] = []  # Array of {domain, area} objects
    engagement_type: Optional[str] = None  # Engagement type code


class ProjectUpdate(BaseModel):
    """Schema for updating a project"""
    name: Optional[str] = None
    customer: Optional[str] = None
    product: Optional[str] = None
    type: Optional[str] = None
    start_date: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    playbooks: Optional[List[str]] = None  # Array of playbook IDs
    # New scope fields
    systems: Optional[List[str]] = None  # Array of system codes
    domains: Optional[List[str]] = None  # Array of domain codes
    functional_areas: Optional[List[dict]] = None  # Array of {domain, area} objects
    engagement_type: Optional[str] = None  # Engagement type code


@router.get("/list")
async def list_projects():
    """Get all projects"""
    try:
        # ✅ Correct method: get_all() not list_all()
        projects = ProjectModel.get_all(status='active')
        
        # Format for frontend
        formatted = []
        for proj in projects:
            # Extract type and notes from metadata
            metadata = proj.get('metadata', {})
            
            formatted.append({
                'id': proj.get('id'),
                'name': proj.get('name'),
                'customer': proj.get('customer'),  # ✅ Column is 'customer' not 'client_name'
                'product': metadata.get('product', ''),
                'type': metadata.get('type', 'Implementation'),
                'start_date': proj.get('start_date'),
                'status': proj.get('status', 'active'),
                'notes': metadata.get('notes', ''),
                'playbooks': metadata.get('playbooks', []),
                # Scope fields
                'systems': metadata.get('systems', []),
                'domains': metadata.get('domains', []),
                'functional_areas': metadata.get('functional_areas', []),
                'engagement_type': metadata.get('engagement_type', ''),
                # Other fields
                'is_active': proj.get('is_active', False),
                'created_at': proj.get('created_at'),
                'updated_at': proj.get('updated_at'),
                'created_by': proj.get('created_by'),
                'metadata': metadata
            })
        
        # Return array directly (frontend expects this)
        return formatted
        
    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create")
async def create_project(project: ProjectCreate):
    """Create a new project"""
    try:
        logger.info(f"Creating project: {project.name}")
        
        # ✅ Correct parameters matching models.py create() signature
        new_project = ProjectModel.create(
            name=project.name,
            client_name=project.customer,      # Maps to 'customer' column
            project_type=project.type,         # Stored in metadata.type
            notes=project.notes or "",         # Stored in metadata.notes
            product=project.product or ""      # Stored in metadata.product
        )
        
        if not new_project:
            raise HTTPException(status_code=500, detail="Failed to create project")
        
        # ✅ Update metadata with all additional fields
        existing_metadata = new_project.get('metadata', {})
        
        if project.playbooks:
            existing_metadata['playbooks'] = project.playbooks
        if project.systems:
            existing_metadata['systems'] = project.systems
        if project.domains:
            existing_metadata['domains'] = project.domains
        if project.functional_areas:
            existing_metadata['functional_areas'] = project.functional_areas
        if project.engagement_type:
            existing_metadata['engagement_type'] = project.engagement_type
        
        # Save updated metadata
        ProjectModel.update(new_project['id'], metadata=existing_metadata)
        new_project['metadata'] = existing_metadata
        
        # Extract metadata for response
        metadata = new_project.get('metadata', {})
        
        return {
            "success": True,
            "project": {
                'id': new_project.get('id'),
                'name': new_project.get('name'),
                'customer': new_project.get('customer'),
                'product': metadata.get('product', ''),
                'type': metadata.get('type', 'Implementation'),
                'notes': metadata.get('notes', ''),
                'playbooks': metadata.get('playbooks', []),
                'systems': metadata.get('systems', []),
                'domains': metadata.get('domains', []),
                'functional_areas': metadata.get('functional_areas', []),
                'engagement_type': metadata.get('engagement_type', ''),
                'status': new_project.get('status', 'active'),
                'created_at': new_project.get('created_at')
            },
            "message": f"Project '{project.name}' created successfully"
        }
        
    except Exception as e:
        logger.error(f"Error creating project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{project_id}")
async def update_project(project_id: str, updates: ProjectUpdate):
    """Update project"""
    try:
        logger.info(f"Updating project {project_id}")
        
        # Build update dict
        update_dict = {}
        
        # Direct column updates
        if updates.name is not None:
            update_dict['name'] = updates.name
        
        if updates.customer is not None:
            update_dict['customer'] = updates.customer
        
        if updates.status is not None:
            update_dict['status'] = updates.status
        
        if updates.start_date is not None:
            update_dict['start_date'] = updates.start_date
        
        # Metadata updates - check if ANY metadata field is being updated
        metadata_fields_present = any([
            updates.type is not None,
            updates.notes is not None,
            updates.product is not None,
            updates.playbooks is not None,
            updates.systems is not None,
            updates.domains is not None,
            updates.functional_areas is not None,
            updates.engagement_type is not None,
        ])
        
        if metadata_fields_present:
            # Get existing project to merge metadata
            existing = ProjectModel.get_by_id(project_id)
            if existing:
                existing_metadata = existing.get('metadata', {})
                
                if updates.type is not None:
                    existing_metadata['type'] = updates.type
                
                if updates.notes is not None:
                    existing_metadata['notes'] = updates.notes
                
                if updates.product is not None:
                    existing_metadata['product'] = updates.product
                
                if updates.playbooks is not None:
                    existing_metadata['playbooks'] = updates.playbooks
                
                # New scope fields
                if updates.systems is not None:
                    existing_metadata['systems'] = updates.systems
                
                if updates.domains is not None:
                    existing_metadata['domains'] = updates.domains
                
                if updates.functional_areas is not None:
                    existing_metadata['functional_areas'] = updates.functional_areas
                
                if updates.engagement_type is not None:
                    existing_metadata['engagement_type'] = updates.engagement_type
                
                update_dict['metadata'] = existing_metadata
        
        # Perform update
        updated = ProjectModel.update(project_id, **update_dict)
        
        if not updated:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Format response
        metadata = updated.get('metadata', {})
        
        return {
            "success": True,
            "project": {
                'id': updated.get('id'),
                'name': updated.get('name'),
                'customer': updated.get('customer'),
                'product': metadata.get('product', ''),
                'type': metadata.get('type', 'Implementation'),
                'notes': metadata.get('notes', ''),
                'playbooks': metadata.get('playbooks', []),
                'systems': metadata.get('systems', []),
                'domains': metadata.get('domains', []),
                'functional_areas': metadata.get('functional_areas', []),
                'engagement_type': metadata.get('engagement_type', ''),
                'status': updated.get('status', 'active'),
                'updated_at': updated.get('updated_at')
            },
            "message": "Project updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """Delete project (soft delete)"""
    try:
        logger.info(f"Deleting project {project_id}")
        
        # ✅ Correct method: delete()
        success = ProjectModel.delete(project_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return {
            "success": True,
            "message": "Project deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}")
async def get_project(project_id: str):
    """Get single project by ID"""
    try:
        project = ProjectModel.get_by_id(project_id)
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Format response
        metadata = project.get('metadata', {})
        
        return {
            'id': project.get('id'),
            'name': project.get('name'),
            'customer': project.get('customer'),
            'product': metadata.get('product', ''),
            'type': metadata.get('type', 'Implementation'),
            'notes': metadata.get('notes', ''),
            'playbooks': metadata.get('playbooks', []),  # ✅ Include playbooks
            'status': project.get('status', 'active'),
            'start_date': project.get('start_date'),
            'created_at': project.get('created_at'),
            'updated_at': project.get('updated_at')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class RecalcRequest(BaseModel):
    """Schema for recalc request"""
    what: Optional[List[str]] = ["terms", "entities", "joins"]


@router.post("/{project_id}/reprofile")
async def reprofile_project_columns(project_id: str):
    """
    Re-run filter category detection on existing column profiles.
    
    This is needed when column profiles were created before the term index
    was implemented. It re-analyzes distinct values to detect:
    - location columns (state codes)
    - status columns (employment status)
    - company, organization, job, pay_type, employee_type columns
    
    After reprofiling, run /recalc to populate the term index.
    
    Args:
        project_id: Project ID
        
    Returns:
        Reprofile statistics
    """
    try:
        from utils.structured_data_handler import StructuredDataHandler
        import json
        
        logger.info(f"Reprofiling columns for project {project_id}")
        
        handler = StructuredDataHandler()
        conn = handler.conn
        
        # Get all column profiles for this project
        profiles = conn.execute("""
            SELECT table_name, column_name, distinct_count, distinct_values, inferred_type
            FROM _column_profiles
            WHERE project = ?
        """, [project_id]).fetchall()
        
        stats = {
            'total_columns': len(profiles),
            'reprofiled': 0,
            'location': 0,
            'status': 0,
            'company': 0,
            'organization': 0,
            'job': 0,
            'pay_type': 0,
            'employee_type': 0,
            'skipped': 0
        }
        
        for row in profiles:
            table_name, column_name, distinct_count, distinct_values_json, inferred_type = row
            
            # Skip if no distinct values or too many
            if not distinct_values_json or not distinct_count or distinct_count > 500:
                stats['skipped'] += 1
                continue
            
            try:
                distinct_values = json.loads(distinct_values_json) if isinstance(distinct_values_json, str) else distinct_values_json
            except:
                stats['skipped'] += 1
                continue
            
            if not distinct_values:
                stats['skipped'] += 1
                continue
            
            # Build a profile dict for _detect_filter_category
            profile = {
                'distinct_count': distinct_count,
                'inferred_type': inferred_type,
                'filter_category': None,
                'filter_priority': 0
            }
            
            # Run filter category detection
            updated_profile = handler._detect_filter_category(column_name, profile, distinct_values, project_id)
            
            if updated_profile.get('filter_category'):
                # Update the profile in the database
                conn.execute("""
                    UPDATE _column_profiles 
                    SET filter_category = ?, filter_priority = ?
                    WHERE project = ? AND table_name = ? AND column_name = ?
                """, [
                    updated_profile['filter_category'],
                    updated_profile.get('filter_priority', 0),
                    project_id,
                    table_name,
                    column_name
                ])
                
                stats['reprofiled'] += 1
                category = updated_profile['filter_category']
                if category in stats:
                    stats[category] += 1
                
                logger.debug(f"[REPROFILE] {table_name}.{column_name} → {category}")
        
        conn.commit()
        
        logger.info(f"Reprofiled {stats['reprofiled']} columns for {project_id}: {stats}")
        
        return {
            "success": True,
            "project_id": project_id,
            "stats": stats,
            "message": f"Reprofiled {stats['reprofiled']} columns. Run /recalc to populate term index."
        }
        
    except Exception as e:
        logger.error(f"Error reprofiling columns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/recalc")
async def recalc_project_indexes(project_id: str, request: RecalcRequest = None):
    """
    Recalculate load-time indexes for a project without re-uploading files.
    
    This endpoint rebuilds:
    - Term index (for deterministic query resolution)
    - Entity tables (for table selection)
    - Join priorities (for deterministic JOIN key selection)
    
    Args:
        project_id: Project ID
        request: Optional - what to recalculate (default: all)
        
    Returns:
        Recalc statistics
    """
    try:
        from utils.structured_data_handler import StructuredDataHandler
        from backend.utils.intelligence.term_index import recalc_term_index
        
        what = request.what if request else ["terms", "entities", "joins"]
        
        logger.info(f"Recalculating indexes for project {project_id}: {what}")
        
        # Get handler
        handler = StructuredDataHandler()
        
        results = {}
        
        if "all" in what or "terms" in what or "entities" in what or "joins" in what:
            # Run full recalc
            stats = recalc_term_index(handler.conn, project_id)
            results = stats
        
        return {
            "success": True,
            "project_id": project_id,
            "recalculated": what,
            "stats": results,
            "message": "Index recalculation complete"
        }
        
    except ImportError as e:
        logger.warning(f"Term index module not available: {e}")
        return {
            "success": False,
            "error": "Term index module not available",
            "message": "This feature requires the term_index module to be installed"
        }
    except Exception as e:
        logger.error(f"Error recalculating indexes: {e}")
        raise HTTPException(status_code=500, detail=str(e))
