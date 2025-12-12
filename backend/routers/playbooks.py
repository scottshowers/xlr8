"""
PLAYBOOKS ROUTER - Thin layer using PlaybookFramework
======================================================

This router delegates to the PlaybookFramework for core operations.
Playbook-specific customization comes from registered playbook definitions.

Endpoints:
- GET /playbooks/{type}/structure - Get playbook structure
- GET /playbooks/{type}/progress/{project_id} - Get progress
- POST /playbooks/{type}/progress/{project_id} - Update progress
- POST /playbooks/{type}/scan/{project_id}/{action_id} - Scan for action
- GET /playbooks/{type}/export/{project_id} - Export as XLSX

Author: XLR8 Team
Version: 4.0.0 - Framework Integration
Date: December 2025
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
import json
import io
import os
import re
from datetime import datetime
from pathlib import Path

# Excel generation
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/playbooks", tags=["playbooks"])


# =============================================================================
# FRAMEWORK IMPORTS
# =============================================================================

try:
    from backend.utils.playbook_framework import (
        PlaybookEngine,
        PlaybookDefinition,
        PlaybookRegistry,
        PLAYBOOK_REGISTRY,
        PROGRESS_MANAGER,
        ActionStatus,
        LearningHook,
        get_playbook_engine,
    )
    FRAMEWORK_AVAILABLE = True
    logger.info("[PLAYBOOKS] Framework imported successfully")
except ImportError:
    try:
        from utils.playbook_framework import (
            PlaybookEngine,
            PlaybookDefinition,
            PlaybookRegistry,
            PLAYBOOK_REGISTRY,
            PROGRESS_MANAGER,
            ActionStatus,
            LearningHook,
            get_playbook_engine,
        )
        FRAMEWORK_AVAILABLE = True
        logger.info("[PLAYBOOKS] Framework imported (alt path)")
    except ImportError as e:
        FRAMEWORK_AVAILABLE = False
        logger.warning(f"[PLAYBOOKS] Framework not available: {e}")

# Year-End specific config
try:
    from backend.playbooks.year_end_playbook import (
        get_year_end_config,
        register_year_end_playbook,
        YEAR_END_CONSULTATIVE_PROMPTS,
        YEAR_END_DEPENDENT_GUIDANCE,
    )
    YEAR_END_CONFIG = get_year_end_config()
except ImportError:
    try:
        from playbooks.year_end_playbook import (
            get_year_end_config,
            register_year_end_playbook,
            YEAR_END_CONSULTATIVE_PROMPTS,
            YEAR_END_DEPENDENT_GUIDANCE,
        )
        YEAR_END_CONFIG = get_year_end_config()
    except ImportError:
        YEAR_END_CONFIG = {}
        logger.warning("[PLAYBOOKS] Year-End config not available")


# =============================================================================
# LEGACY SUPPORT - For backward compatibility during transition
# =============================================================================

# In-memory progress (fallback if framework unavailable)
PLAYBOOK_PROGRESS: Dict[str, Dict[str, Any]] = {}

# Cached structure
PLAYBOOK_CACHE: Dict[str, Any] = {}


def get_supabase():
    """Get Supabase client."""
    try:
        from utils.supabase_client import get_supabase_client
        return get_supabase_client()
    except Exception:
        return None


# =============================================================================
# STRUCTURE PARSING - Load playbook from uploaded document
# =============================================================================

async def get_year_end_structure() -> Dict[str, Any]:
    """
    Get Year-End playbook structure.
    
    Parses from uploaded Year-End Checklist document.
    """
    cache_key = "year-end-2025"
    
    if cache_key in PLAYBOOK_CACHE:
        return PLAYBOOK_CACHE[cache_key]
    
    try:
        from backend.utils.playbook_parser import parse_year_end_checklist
    except ImportError:
        from utils.playbook_parser import parse_year_end_checklist
    
    structure = parse_year_end_checklist()
    
    if structure:
        PLAYBOOK_CACHE[cache_key] = structure
        logger.info(f"[STRUCTURE] Cached Year-End structure: {len(structure.get('steps', []))} steps")
    
    return structure


def invalidate_year_end_cache():
    """Invalidate cache when new document uploaded."""
    if "year-end-2025" in PLAYBOOK_CACHE:
        del PLAYBOOK_CACHE["year-end-2025"]
        logger.info("[CACHE] Year-End structure cache invalidated")


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class ProgressUpdate(BaseModel):
    status: str
    notes: Optional[str] = None


class FeedbackRequest(BaseModel):
    finding_text: str
    feedback: str  # 'keep', 'discard', 'modify'
    reason: Optional[str] = None


class EntityConfigRequest(BaseModel):
    primary_entity: Optional[str] = None
    fein: Optional[str] = None
    company_name: Optional[str] = None


class QuickSuppressRequest(BaseModel):
    finding_text: str
    reason: str
    suppress_type: str = 'acknowledge'
    fein: Optional[str] = None


# =============================================================================
# CORE ENDPOINTS
# =============================================================================

@router.get("/year-end/structure")
async def get_playbook_structure():
    """Get Year-End playbook structure."""
    try:
        structure = await get_year_end_structure()
        if not structure:
            raise HTTPException(status_code=404, detail="Year-End structure not found")
        return structure
    except Exception as e:
        logger.exception(f"Failed to get structure: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/year-end/progress/{project_id}")
async def get_progress(project_id: str):
    """Get progress for a project."""
    try:
        if FRAMEWORK_AVAILABLE:
            progress = PROGRESS_MANAGER.get_raw_progress("year-end", project_id)
        else:
            progress = PLAYBOOK_PROGRESS.get(project_id, {})
        
        return {
            "project_id": project_id,
            "progress": progress
        }
    except Exception as e:
        logger.exception(f"Failed to get progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/year-end/progress/{project_id}")
async def update_progress(project_id: str, action_id: str, update: ProgressUpdate):
    """Update progress for an action."""
    try:
        if FRAMEWORK_AVAILABLE:
            engine = get_playbook_engine("year-end")
            if engine:
                result = engine.update_status(
                    project_id, action_id, update.status, update.notes
                )
                return result
        
        # Fallback
        if project_id not in PLAYBOOK_PROGRESS:
            PLAYBOOK_PROGRESS[project_id] = {}
        
        existing = PLAYBOOK_PROGRESS[project_id].get(action_id, {})
        existing["status"] = update.status
        if update.notes is not None:
            existing["notes"] = update.notes
        PLAYBOOK_PROGRESS[project_id][action_id] = existing
        
        return {"success": True, "status": update.status}
        
    except Exception as e:
        logger.exception(f"Failed to update progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/year-end/scan/{project_id}/{action_id}")
async def scan_for_action(project_id: str, action_id: str):
    """
    Scan documents for a specific action.
    
    This is the main scan endpoint - delegates to framework.
    """
    logger.info(f"[SCAN] {action_id} in project {project_id[:8]}")
    
    try:
        if FRAMEWORK_AVAILABLE:
            engine = get_playbook_engine("year-end")
            if engine:
                # Ensure structure is loaded into engine
                structure = await get_year_end_structure()
                if structure:
                    # Update engine's playbook with parsed structure
                    _sync_structure_to_engine(engine, structure)
                
                result = await engine.scan_action(project_id, action_id)
                return result.to_dict()
        
        # Fallback to legacy implementation
        return await _legacy_scan(project_id, action_id)
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Scan failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _sync_structure_to_engine(engine: PlaybookEngine, structure: Dict):
    """
    Sync parsed structure to engine's playbook definition.
    
    The structure comes from parsing the uploaded document.
    """
    try:
        from backend.utils.playbook_framework import StepDefinition, ActionDefinition, ActionType
    except ImportError:
        from utils.playbook_framework import StepDefinition, ActionDefinition, ActionType
    
    steps = []
    for step_data in structure.get('steps', []):
        actions = []
        for action_data in step_data.get('actions', []):
            action_type_str = action_data.get('action_type', 'recommended')
            try:
                action_type = ActionType(action_type_str)
            except ValueError:
                action_type = ActionType.RECOMMENDED
            
            action = ActionDefinition(
                action_id=action_data['action_id'],
                description=action_data.get('description', ''),
                action_type=action_type,
                reports_needed=action_data.get('reports_needed', []),
                due_date=action_data.get('due_date'),
                quarter_end=action_data.get('quarter_end', False),
                keywords=YEAR_END_CONFIG.get('action_keywords', {}).get(
                    action_data['action_id'], {}
                ).get('keywords', []),
                categories=YEAR_END_CONFIG.get('action_keywords', {}).get(
                    action_data['action_id'], {}
                ).get('categories', []),
                guidance=YEAR_END_CONFIG.get('dependent_guidance', {}).get(
                    action_data['action_id']
                ),
                consultative_prompt=YEAR_END_CONFIG.get('consultative_prompts', {}).get(
                    action_data['action_id']
                ),
            )
            actions.append(action)
        
        step = StepDefinition(
            step_number=step_data['step_number'],
            step_name=step_data.get('step_name', ''),
            phase=step_data.get('phase', 'before_final_payroll'),
            actions=actions
        )
        steps.append(step)
    
    engine.playbook.steps = steps
    # Rebuild dependencies from new structure
    try:
        from backend.utils.playbook_framework import InheritanceManager
    except ImportError:
        from utils.playbook_framework import InheritanceManager
    engine.dependencies = InheritanceManager.build_dependencies(engine.playbook)


async def _legacy_scan(project_id: str, action_id: str) -> Dict:
    """Legacy scan implementation for backward compatibility."""
    # This would contain the old scan logic
    # For now, return a placeholder
    return {
        "found": False,
        "documents": [],
        "findings": None,
        "suggested_status": "not_started",
        "message": "Framework not available, using legacy mode"
    }


# =============================================================================
# FEEDBACK ENDPOINT - Learning integration
# =============================================================================

@router.post("/year-end/feedback/{project_id}/{action_id}")
async def record_feedback(
    project_id: str, 
    action_id: str, 
    request: FeedbackRequest
):
    """Record user feedback on a finding."""
    try:
        if FRAMEWORK_AVAILABLE:
            engine = get_playbook_engine("year-end")
            if engine:
                success = engine.record_feedback(
                    project_id=project_id,
                    action_id=action_id,
                    finding_text=request.finding_text,
                    feedback=request.feedback,
                    reason=request.reason
                )
                return {"success": success}
        
        # Fallback - just acknowledge
        return {"success": True, "message": "Feedback noted (learning not active)"}
        
    except Exception as e:
        logger.error(f"[FEEDBACK] Error: {e}")
        return {"success": False, "message": str(e)}


# =============================================================================
# DOCUMENT CHECKLIST ENDPOINT
# =============================================================================

@router.get("/year-end/document-checklist/{project_id}")
async def get_document_checklist(project_id: str):
    """Get document checklist with upload status."""
    try:
        from utils.rag_handler import RAGHandler
        from backend.utils.playbook_parser import (
            load_step_documents, 
            match_documents_to_step, 
            get_duckdb_connection
        )
    except ImportError:
        from utils.rag_handler import RAGHandler
        from utils.playbook_parser import (
            load_step_documents, 
            match_documents_to_step, 
            get_duckdb_connection
        )
    
    uploaded_files = set()
    
    # Get files from ChromaDB
    try:
        rag = RAGHandler()
        collection = rag.client.get_or_create_collection(name="documents")
        results = collection.get(include=["metadatas"], limit=1000)
        
        for metadata in results.get("metadatas", []):
            doc_project = metadata.get("project_id", "")
            doc_project_name = metadata.get("project", "")
            
            is_global = doc_project_name.lower() in ('global', '__global__')
            is_this_project = doc_project == project_id or doc_project.startswith(project_id[:8])
            
            if is_global or is_this_project:
                filename = metadata.get("source", metadata.get("filename", ""))
                if filename:
                    uploaded_files.add(filename)
    except Exception as e:
        logger.debug(f"ChromaDB query failed: {e}")
    
    # Get files from DuckDB
    try:
        conn = get_duckdb_connection()
        if conn:
            # Excel files
            result = conn.execute("""
                SELECT DISTINCT file_name, project FROM _schema_metadata
                WHERE file_name IS NOT NULL
            """).fetchall()
            for row in result:
                filename, proj = row
                if proj and (proj.lower() == 'global' or project_id[:8].lower() in proj.lower()):
                    uploaded_files.add(filename)
            
            # PDF tables
            try:
                result = conn.execute("""
                    SELECT DISTINCT source_file, project FROM _pdf_tables
                    WHERE source_file IS NOT NULL
                """).fetchall()
                for row in result:
                    filename, proj = row
                    if proj and (proj.lower() == 'global' or project_id[:8].lower() in proj.lower()):
                        uploaded_files.add(filename)
            except Exception:
                pass
            
            conn.close()
    except Exception as e:
        logger.debug(f"DuckDB query failed: {e}")
    
    # Build step checklists
    step_checklists = []
    try:
        step_documents = load_step_documents()
        if step_documents:
            for step_num, docs in sorted(step_documents.items()):
                result = match_documents_to_step(docs, list(uploaded_files))
                step_checklists.append({
                    'step_number': step_num,
                    'matched': result['matched'],
                    'missing': result['missing'],
                    'stats': result['stats']
                })
    except Exception as e:
        logger.debug(f"Could not load step documents: {e}")
    
    return {
        "project_id": project_id,
        "uploaded_files": sorted(list(uploaded_files)),
        "step_checklists": step_checklists,
        "stats": {
            "files_in_project": len(uploaded_files)
        }
    }


# =============================================================================
# EXPORT ENDPOINT
# =============================================================================

@router.get("/year-end/export/{project_id}")
async def export_playbook(project_id: str):
    """Export playbook progress as Excel."""
    try:
        structure = await get_year_end_structure()
        
        if FRAMEWORK_AVAILABLE:
            progress = PROGRESS_MANAGER.get_raw_progress("year-end", project_id)
        else:
            progress = PLAYBOOK_PROGRESS.get(project_id, {})
        
        # Create workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Year-End Checklist"
        
        # Styles
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # Headers
        headers = [
            "Action ID", "Step", "Type", "Description", "Due Date",
            "Owner", "Quarter End", "Reports Needed", "Docs Found",
            "Found Files", "Analysis Tab", "Status", "Findings", "Issues", "Notes"
        ]
        
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = thin_border
        
        # Data rows
        row = 2
        for step in structure.get('steps', []):
            for action in step.get('actions', []):
                action_id = action['action_id']
                action_progress = progress.get(action_id, {})
                
                ws.cell(row=row, column=1, value=action_id)
                ws.cell(row=row, column=2, value=f"Step {step['step_number']}")
                ws.cell(row=row, column=3, value=action.get('action_type', 'Recommended'))
                ws.cell(row=row, column=4, value=action.get('description', ''))
                ws.cell(row=row, column=5, value=action.get('due_date', 'N/A'))
                ws.cell(row=row, column=6, value='')  # Owner
                ws.cell(row=row, column=7, value='Yes' if action.get('quarter_end') else 'No')
                ws.cell(row=row, column=8, value=', '.join(action.get('reports_needed', [])))
                
                docs_found = action_progress.get('documents_found', [])
                ws.cell(row=row, column=9, value='Yes' if docs_found else 'No')
                ws.cell(row=row, column=10, value=', '.join(docs_found[:3]))
                ws.cell(row=row, column=11, value='')  # Analysis tab
                
                status = action_progress.get('status', 'not_started')
                ws.cell(row=row, column=12, value=status.replace('_', ' ').title())
                
                findings = action_progress.get('findings', {})
                ws.cell(row=row, column=13, value=findings.get('summary', '') if findings else '')
                ws.cell(row=row, column=14, value='\n'.join(findings.get('issues', [])) if findings else '')
                ws.cell(row=row, column=15, value=action_progress.get('notes', ''))
                
                for col in range(1, 16):
                    ws.cell(row=row, column=col).border = thin_border
                
                row += 1
        
        # Set column widths
        widths = [10, 10, 12, 50, 15, 15, 12, 40, 10, 40, 20, 12, 50, 50, 30]
        for i, width in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = width
        
        # Save to bytes
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = f"Year_End_Checklist_{project_id[:8]}_{datetime.now().strftime('%Y%m%d')}.xlsx"
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.exception(f"Export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ENTITY CONFIGURATION ENDPOINTS
# =============================================================================

@router.get("/year-end/entity-config/{project_id}")
async def get_entity_config(project_id: str):
    """Get entity configuration for a project."""
    try:
        from utils.database.models import EntityConfigModel
        config = EntityConfigModel.get(project_id, "year-end")
        return {"config": config}
    except ImportError:
        return {"config": None, "message": "Entity config not available"}
    except Exception as e:
        logger.error(f"[ENTITY] Get config error: {e}")
        return {"config": None, "error": str(e)}


@router.post("/year-end/entity-config/{project_id}")
async def set_entity_config(project_id: str, request: EntityConfigRequest):
    """Set entity configuration for a project."""
    try:
        from utils.database.models import EntityConfigModel
        result = EntityConfigModel.set(
            project_id=project_id,
            playbook_type="year-end",
            primary_entity=request.primary_entity,
            fein=request.fein,
            company_name=request.company_name
        )
        return {"success": True, "config": result}
    except ImportError:
        return {"success": False, "message": "Entity config not available"}
    except Exception as e:
        logger.error(f"[ENTITY] Set config error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# SUPPRESSION ENDPOINTS
# =============================================================================

@router.get("/year-end/suppressions/{project_id}")
async def get_suppressions(project_id: str):
    """Get suppression rules for a project."""
    try:
        from utils.database.models import FindingSuppressionModel
        rules = FindingSuppressionModel.get_active(project_id, "year-end")
        return {"rules": rules}
    except ImportError:
        return {"rules": [], "message": "Suppression not available"}
    except Exception as e:
        logger.error(f"[SUPPRESS] Get rules error: {e}")
        return {"rules": [], "error": str(e)}


@router.post("/year-end/suppress/quick/{project_id}/{action_id}")
async def quick_suppress(
    project_id: str, 
    action_id: str, 
    request: QuickSuppressRequest
):
    """Quick suppress from UI."""
    try:
        from utils.database.models import FindingSuppressionModel
        result = FindingSuppressionModel.create(
            project_id=project_id,
            playbook_type="year-end",
            action_id=action_id,
            suppression_type=request.suppress_type,
            finding_text=request.finding_text,
            reason=request.reason,
            fein_filter=[request.fein] if request.fein else None
        )
        if result:
            return {"success": True, "rule_id": result['id']}
        return {"success": False}
    except ImportError:
        return {"success": False, "message": "Suppression not available"}
    except Exception as e:
        logger.error(f"[SUPPRESS] Quick suppress error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# LEARNING ENDPOINTS
# =============================================================================

@router.get("/year-end/learning/stats")
async def get_learning_stats():
    """Get learning system statistics."""
    if not FRAMEWORK_AVAILABLE:
        return {"success": False, "message": "Framework not available"}
    
    if not LearningHook.is_available():
        return {"success": False, "message": "Learning system not active"}
    
    try:
        try:
            from backend.utils.learning_engine import get_learning_system
        except ImportError:
            from utils.learning_engine import get_learning_system
        
        learning = get_learning_system()
        return {
            "success": True,
            "stats": learning.get_stats()
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# SCAN ALL ENDPOINT
# =============================================================================

@router.post("/year-end/scan-all/{project_id}")
async def scan_all_actions(project_id: str):
    """Scan all actions for a project (non-blocking)."""
    try:
        structure = await get_year_end_structure()
        
        results = {}
        for step in structure.get('steps', []):
            for action in step.get('actions', []):
                action_id = action['action_id']
                try:
                    result = await scan_for_action(project_id, action_id)
                    results[action_id] = {
                        "success": True,
                        "status": result.get('suggested_status', 'not_started')
                    }
                except Exception as e:
                    results[action_id] = {
                        "success": False,
                        "error": str(e)
                    }
        
        return {
            "project_id": project_id,
            "results": results,
            "scanned": len(results)
        }
        
    except Exception as e:
        logger.exception(f"Scan all failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# HEALTH CHECK
# =============================================================================

@router.get("/health")
async def playbooks_health():
    """Health check for playbooks router."""
    return {
        "status": "healthy",
        "framework_available": FRAMEWORK_AVAILABLE,
        "year_end_config_loaded": bool(YEAR_END_CONFIG),
        "learning_available": FRAMEWORK_AVAILABLE and LearningHook.is_available()
    }
