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
        import json
        
        what = request.what if request else ["terms", "entities", "joins"]
        
        logger.info(f"Recalculating indexes for project {project_id}: {what}")
        
        # Get handler
        handler = StructuredDataHandler()
        
        # Diagnostic: Check what profiles exist with filter_category
        diag_profiles = handler.conn.execute("""
            SELECT filter_category, COUNT(*) as cnt,
                   SUM(CASE WHEN distinct_values IS NOT NULL THEN 1 ELSE 0 END) as with_values
            FROM _column_profiles
            WHERE project = ? AND filter_category IS NOT NULL
            GROUP BY filter_category
        """, [project_id]).fetchall()
        
        diagnostics = {
            'profiles_by_category': {row[0]: {'count': row[1], 'with_values': row[2]} for row in diag_profiles}
        }
        
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
            "diagnostics": diagnostics,
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


@router.get("/{project_id}/term-index")
async def get_term_index_contents(project_id: str, term: str = None, limit: int = 50):
    """
    Diagnostic endpoint to see what's in the term index.
    
    Args:
        project_id: Project ID
        term: Optional term to search for
        limit: Max results to return
        
    Returns:
        Term index contents
    """
    try:
        from utils.structured_data_handler import StructuredDataHandler
        
        handler = StructuredDataHandler()
        conn = handler.conn
        
        if term:
            # Search for specific term
            results = conn.execute("""
                SELECT term, term_type, table_name, column_name, operator, match_value, 
                       domain, entity, confidence, source
                FROM _term_index
                WHERE project = ? AND term LIKE ?
                ORDER BY confidence DESC
                LIMIT ?
            """, [project_id, f'%{term.lower()}%', limit]).fetchall()
        else:
            # Get sample of all terms
            results = conn.execute("""
                SELECT term, term_type, table_name, column_name, operator, match_value, 
                       domain, entity, confidence, source
                FROM _term_index
                WHERE project = ?
                ORDER BY term
                LIMIT ?
            """, [project_id, limit]).fetchall()
        
        # Also get location column profiles
        location_profiles = conn.execute("""
            SELECT table_name, column_name, distinct_count, distinct_values
            FROM _column_profiles
            WHERE project = ? AND filter_category = 'location'
            LIMIT 10
        """, [project_id]).fetchall()
        
        return {
            "success": True,
            "project_id": project_id,
            "search_term": term,
            "terms": [
                {
                    "term": r[0],
                    "term_type": r[1],
                    "table": r[2],
                    "column": r[3],
                    "operator": r[4],
                    "match_value": r[5],
                    "domain": r[6],
                    "entity": r[7],
                    "confidence": r[8],
                    "source": r[9]
                }
                for r in results
            ],
            "location_profiles": [
                {
                    "table": r[0],
                    "column": r[1],
                    "distinct_count": r[2],
                    "sample_values": r[3][:200] if r[3] else None
                }
                for r in location_profiles
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting term index: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/resolve-terms")
async def resolve_terms_test(project_id: str, question: str):
    """
    Test endpoint for the full term resolution flow.
    
    This tests:
    1. Term Index fast path (known terms like "texas")
    2. MetadataReasoner fallback (unknown terms like "401k")
    3. EVOLUTION 3: Numeric expression parsing ("above 75000")
    4. EVOLUTION 8: GROUP BY handling for dimensional queries
    5. SQL Assembly from resolved terms
    
    Args:
        project_id: Project ID
        question: Question to parse and resolve (e.g., "employees in Texas with 401k")
        
    Returns:
        Resolution results including terms, matches, and assembled SQL
    """
    try:
        from utils.structured_data_handler import StructuredDataHandler
        from backend.utils.intelligence.term_index import TermIndex
        from backend.utils.intelligence.sql_assembler import SQLAssembler, QueryIntent
        from backend.utils.intelligence.query_resolver import parse_intent
        import re
        
        handler = StructuredDataHandler()
        conn = handler.conn
        
        # Step 1: Parse intent
        parsed = parse_intent(question)
        
        # Step 2: Tokenize - EVOLUTION 3: Also extract numeric phrases
        words = [w.strip().lower() for w in re.split(r'\s+', question) if w.strip()]
        
        # EVOLUTION 8: Detect GROUP BY dimension EARLY
        group_by_dimension = None
        group_by_patterns = [
            r'\bby\s+(\w+)',           # "by state", "by department"
            r'\bper\s+(\w+)',          # "per location", "per employee"
            r'\bfor each\s+(\w+)',     # "for each state"
            r'\bbroken down by\s+(\w+)', # "broken down by region"
            r'\bgrouped by\s+(\w+)',   # "grouped by status"
        ]
        phrase_words = set()
        for pattern in group_by_patterns:
            match = re.search(pattern, question.lower())
            if match:
                group_by_dimension = match.group(1)
                phrase_words.add(group_by_dimension)
                phrase_words.add('by')
                phrase_words.add('per')
                break
        
        # EVOLUTION 8: Detect COUNT intent keywords
        count_intent_phrases = ['headcount', 'head count', 'count', 'how many', 'number of', 'total employees', 'total people']
        question_lower = question.lower()
        detected_count = any(kw in question_lower for kw in count_intent_phrases)
        
        # Only exclude count-related words if this IS a count query
        if detected_count:
            count_noise_words = ['headcount', 'head', 'count', 'how', 'many', 'number', 'total', 'of']
            for kw in count_noise_words:
                if kw in question_lower:
                    phrase_words.add(kw)
        
        # Extract numeric phrases like "above 75000", "between 20 and 40"
        numeric_phrase_patterns = [
            r'(?:above|over|more than|greater than)\s+[\$]?\d[\d,]*[kKmM]?',
            r'(?:below|under|less than)\s+[\$]?\d[\d,]*[kKmM]?',
            r'(?:at least|minimum)\s+[\$]?\d[\d,]*[kKmM]?',
            r'(?:at most|maximum)\s+[\$]?\d[\d,]*[kKmM]?',
            r'between\s+[\$]?\d[\d,]*[kKmM]?\s+and\s+[\$]?\d[\d,]*[kKmM]?',
        ]
        numeric_phrases = []
        for pattern in numeric_phrase_patterns:
            found = re.findall(pattern, question.lower())
            numeric_phrases.extend(found)
        
        # Remove GROUP BY dimension from regular term resolution
        if phrase_words:
            words = [w for w in words if w not in phrase_words]
        
        # ======================================================================
        # EVOLUTION 9: Pre-filter superlative keywords BEFORE term resolution
        # ======================================================================
        # This prevents "top", "newest", "hires", etc. from being searched as terms
        superlative_prefilter = {'top', 'bottom', 'highest', 'lowest', 'oldest', 'newest', 
                                'most', 'least', 'best', 'worst', 'paid', 'earner', 'earners',
                                'hires', 'hire', 'hired', 'recent', 'earliest', 'latest',
                                'youngest', 'tenure', 'seniority'}
        words = [w for w in words if w not in superlative_prefilter]
        # Also filter standalone numbers that are likely limits (e.g., "5" in "top 5")
        words = [w for w in words if not w.isdigit()]
        
        terms_to_resolve = words + numeric_phrases
        
        term_index = TermIndex(conn, project_id)
        
        # EVOLUTION 3: Use enhanced resolution if available
        if hasattr(term_index, 'resolve_terms_enhanced'):
            term_matches = term_index.resolve_terms_enhanced(terms_to_resolve, detect_numeric=True, full_question=question)
        else:
            term_matches = term_index.resolve_terms(terms_to_resolve)
        
        # EVOLUTION 8: Resolve GROUP BY dimension to a column
        group_by_column = None
        if group_by_dimension:
            # Look up concept terms for the dimension
            dim_matches = term_index.resolve_terms([group_by_dimension])
            concept_matches = [m for m in dim_matches if m.term_type == 'concept']
            
            if concept_matches:
                # Prefer matches from employee/personal tables
                employee_matches = [m for m in concept_matches 
                                   if m.entity == 'employee' or 'personal' in m.table_name.lower()]
                best_match = employee_matches[0] if employee_matches else concept_matches[0]
                group_by_column = f"{best_match.table_name}.{best_match.column_name}"
            else:
                # Fallback to hardcoded synonyms
                dimension_synonyms = {
                    'state': 'stateprovince', 'states': 'stateprovince', 'province': 'stateprovince',
                    'department': 'department', 'dept': 'department',
                    'location': 'location_code', 'status': 'employee_status',
                    'company': 'company_code', 'job': 'job_code',
                }
                if group_by_dimension in dimension_synonyms:
                    group_by_column = dimension_synonyms[group_by_dimension]
        
        # EVOLUTION 8: Only exclude the GROUP BY dimension from WHERE clause, keep other concepts
        if group_by_dimension:
            # Exclude the GROUP BY dimension concept from filters (it's used for grouping, not filtering)
            filter_matches = [m for m in term_matches 
                             if not (m.term_type == 'concept' and m.term.lower() == group_by_dimension.lower())]
        else:
            # No GROUP BY - keep all term matches including concepts
            filter_matches = term_matches
        
        # ======================================================================
        # EVOLUTION 9: Superlative Detection
        # ======================================================================
        # Detect patterns like "highest paid", "top 5 earners", "oldest employees"
        order_by_column = None
        order_direction = 'DESC'
        result_limit = 100
        
        # Superlative patterns: (keyword, direction)
        superlative_keywords = {
            'highest': 'DESC', 'top': 'DESC', 'most': 'DESC', 'best': 'DESC',
            'greatest': 'DESC', 'largest': 'DESC', 'maximum': 'DESC', 'max': 'DESC',
            'lowest': 'ASC', 'bottom': 'ASC', 'least': 'ASC', 'worst': 'ASC',
            'smallest': 'ASC', 'minimum': 'ASC', 'min': 'ASC',
            'oldest': 'ASC', 'newest': 'DESC', 'youngest': 'DESC',
            'earliest': 'ASC', 'latest': 'DESC', 'recent': 'DESC',
        }
        
        # Column mappings: (target word → column name)
        superlative_columns = {
            'paid': 'annual_salary', 'salary': 'annual_salary', 'salaries': 'annual_salary',
            'earner': 'annual_salary', 'earners': 'annual_salary', 'earning': 'annual_salary',
            'pay': 'annual_salary', 'compensation': 'annual_salary', 'wage': 'annual_salary',
            'old': 'last_hire_date', 'oldest': 'last_hire_date',
            'new': 'last_hire_date', 'newest': 'last_hire_date',
            'young': 'last_hire_date', 'youngest': 'last_hire_date',
            'tenure': 'last_hire_date', 'seniority': 'last_hire_date',
            'hired': 'last_hire_date', 'hire': 'last_hire_date', 'hires': 'last_hire_date',
            'recent': 'last_hire_date', 'earliest': 'last_hire_date', 'latest': 'last_hire_date',
        }
        
        detected_superlative = None
        for keyword, direction in superlative_keywords.items():
            if keyword in question_lower:
                detected_superlative = keyword
                order_direction = direction
                
                # Check if keyword itself maps to a column (e.g., "oldest" → hire_date)
                if keyword in superlative_columns:
                    order_by_column = superlative_columns[keyword]
                break
        
        # If superlative found but no column yet, look for target words
        if detected_superlative and not order_by_column:
            for target, col in superlative_columns.items():
                if target in question_lower:
                    order_by_column = col
                    break
        
        # Extract limit from "top N" or "bottom N" patterns
        if detected_superlative:
            limit_match = re.search(r'\b(top|bottom|highest|lowest)\s+(\d+)\b', question_lower)
            if limit_match:
                result_limit = int(limit_match.group(2))
            else:
                # Default to 10 for superlative queries
                result_limit = 10
            
            # Remove superlative words from term resolution to avoid bad matches
            superlative_noise = ['top', 'bottom', 'highest', 'lowest', 'oldest', 'newest', 
                                'most', 'least', 'best', 'worst', 'paid', 'earner', 'earners',
                                'hires', 'hire', 'hired', 'recent', 'earliest', 'latest',
                                'youngest', 'oldest', 'tenure', 'seniority']
            filter_matches = [m for m in filter_matches 
                            if m.term.lower() not in superlative_noise]
            
            if order_by_column:
                logger.info(f"[EVOLUTION 9] Superlative detected: {detected_superlative} → ORDER BY {order_by_column} {order_direction} LIMIT {result_limit}")
        
        # EVOLUTION 9: Infer domain from superlative column if not already set
        # "top 5 newest hires" implies employee domain even without "employees" keyword
        if order_by_column and (not parsed.domain or parsed.domain.value == 'unknown'):
            if order_by_column in ('last_hire_date', 'original_hire_date', 'seniority_date'):
                # Hire-related → employee domain
                from backend.utils.intelligence.query_resolver import EntityDomain
                parsed.domain = EntityDomain.EMPLOYEES
                logger.info(f"[EVOLUTION 9] Inferred EMPLOYEES domain from superlative column: {order_by_column}")
        
        # Step 3: Assemble SQL
        intent_map = {
            'count': QueryIntent.COUNT,
            'list': QueryIntent.LIST,
            'sum': QueryIntent.SUM,
            'compare': QueryIntent.COMPARE,
        }
        assembler_intent = intent_map.get(parsed.intent.value, QueryIntent.LIST)
        
        # Override to COUNT if we detected count keywords
        if detected_count:
            assembler_intent = QueryIntent.COUNT
        
        assembler = SQLAssembler(conn, project_id)
        assembled = assembler.assemble(
            intent=assembler_intent,
            term_matches=filter_matches,
            domain=parsed.domain.value if parsed.domain else None,
            group_by_column=group_by_column,
            order_by=order_by_column,
            order_direction=order_direction,
            limit=result_limit
        )
        
        # Step 4: Execute SQL (if valid)
        execution_result = None
        if assembled.success and assembled.sql:
            try:
                result = conn.execute(assembled.sql).fetchall()
                columns = [desc[0] for desc in conn.description]
                execution_result = {
                    "success": True,
                    "row_count": len(result),
                    "columns": columns,
                    "sample_rows": [dict(zip(columns, row)) for row in result[:5]]
                }
            except Exception as sql_err:
                execution_result = {
                    "success": False,
                    "error": str(sql_err)
                }
        
        return {
            "success": True,
            "project_id": project_id,
            "question": question,
            "parsed_intent": parsed.intent.value,
            "parsed_domain": parsed.domain.value if parsed.domain else None,
            "input_words": words,
            "numeric_phrases": numeric_phrases,
            "group_by_dimension": group_by_dimension,
            "group_by_column": group_by_column,
            "terms_resolved": terms_to_resolve,
            "term_matches": [
                {
                    "term": m.term,
                    "table": m.table_name,
                    "column": m.column_name,
                    "operator": m.operator,
                    "match_value": m.match_value,
                    "domain": m.domain,
                    "confidence": m.confidence,
                    "term_type": m.term_type,
                    "source": getattr(m, 'source', None)
                }
                for m in term_matches
            ],
            "assembly": {
                "success": assembled.success,
                "error": assembled.error,
                "sql": assembled.sql,
                "tables": assembled.tables,
                "primary_table": assembled.primary_table,
                "filters": assembled.filters,
                "group_by_column": group_by_column,
                "joins": [
                    {"table1": j.table1, "col1": j.column1, "table2": j.table2, "col2": j.column2}
                    for j in assembled.joins
                ] if assembled.joins else []
            },
            "execution": execution_result
        }
        
    except Exception as e:
        logger.error(f"Error resolving terms: {e}")
        raise HTTPException(status_code=500, detail=str(e))
