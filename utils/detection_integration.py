"""
XLR8 DETECTION INTEGRATION
==========================

Integrates detection_service into the upload flow.
Runs after files are processed to detect systems, domains, and functional areas.

Called from upload.py after column profiling completes.

Author: XLR8 Team
Version: 1.0.0
Deploy to: utils/detection_integration.py
"""

import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


def run_project_detection(
    project: str,
    project_id: Optional[str],
    filename: str,
    handler=None,
    job_id: Optional[str] = None
) -> Optional[Dict]:
    """
    Run detection for a project based on uploaded file and existing data.
    
    This is called during the upload flow after files are loaded into DuckDB.
    It detects:
    - System of record (UKG Pro, Workday, SAP, etc.)
    - Domain (HCM, Finance, Compliance, etc.)
    - Functional areas (Payroll, Benefits, GL, AP, etc.)
    
    Args:
        project: Project name
        project_id: Project UUID (optional)
        filename: Name of uploaded file
        handler: DuckDB handler
        job_id: Processing job ID for progress updates
        
    Returns:
        Detection result dict or None
    """
    try:
        # Import detection service
        try:
            from utils.detection_service import get_detection_service, DetectionResult
        except ImportError:
            from backend.utils.detection_service import get_detection_service, DetectionResult
        
        # Update progress if job_id provided
        if job_id:
            try:
                from models.processing_job import ProcessingJobModel
                ProcessingJobModel.update_progress(job_id, 76, "Detecting system context...")
            except Exception:
                pass
        
        service = get_detection_service()
        
        # Collect all columns from the project
        all_columns = []
        all_filenames = set()
        
        if filename:
            all_filenames.add(filename)
        
        # Query DuckDB for project tables and columns
        if handler and hasattr(handler, 'conn') and handler.conn:
            try:
                # Get all tables for project
                tables = handler.conn.execute(f"""
                    SELECT table_name, file_name
                    FROM _schema_metadata
                    WHERE project = '{project}'
                """).fetchall()
                
                for table_name, file_name in tables:
                    if file_name:
                        all_filenames.add(file_name)
                    
                    # Get columns for this table
                    try:
                        cols = handler.conn.execute(f"PRAGMA table_info('{table_name}')").fetchall()
                        for col in cols:
                            col_name = col[1]  # Column name is index 1
                            if col_name and not col_name.startswith('_'):
                                all_columns.append(col_name)
                    except Exception as col_err:
                        logger.debug(f"[DETECTION] Could not get columns for {table_name}: {col_err}")
                
            except Exception as query_err:
                logger.warning(f"[DETECTION] Could not query project tables: {query_err}")
        
        # Also try to get columns from _column_profiles
        if handler and hasattr(handler, 'conn') and handler.conn:
            try:
                profiles = handler.conn.execute(f"""
                    SELECT column_name
                    FROM _column_profiles
                    WHERE project = '{project}'
                """).fetchall()
                
                for (col_name,) in profiles:
                    if col_name and col_name not in all_columns:
                        all_columns.append(col_name)
                        
            except Exception as prof_err:
                logger.debug(f"[DETECTION] Could not query column profiles: {prof_err}")
        
        if not all_columns and not all_filenames:
            logger.info(f"[DETECTION] No data to analyze for project {project}")
            return None
        
        # Run detection
        logger.info(f"[DETECTION] Analyzing {len(all_columns)} columns, {len(all_filenames)} files for {project}")
        
        result = service.detect(
            filename=list(all_filenames)[0] if all_filenames else None,
            columns=all_columns
        )
        
        # Update project context in Supabase
        if result.systems or result.domains or result.functional_areas:
            service.update_project_context(project, result)
            
            logger.info(f"[DETECTION] Detected for {project}: "
                       f"systems={[s['code'] for s in result.systems]}, "
                       f"domains={[d['code'] for d in result.domains]}, "
                       f"functional_areas={len(result.functional_areas)}")
        else:
            logger.info(f"[DETECTION] No systems/domains detected for {project}")
        
        # Update progress
        if job_id:
            try:
                from models.processing_job import ProcessingJobModel
                if result.primary_system:
                    msg = f"Detected: {result.primary_system.get('name', 'Unknown')}"
                elif result.primary_domain:
                    msg = f"Detected: {result.primary_domain.get('name', 'Unknown')} data"
                else:
                    msg = "Context analyzed"
                ProcessingJobModel.update_progress(job_id, 77, msg)
            except Exception:
                pass
        
        return result.to_dict()
        
    except ImportError as ie:
        logger.info(f"[DETECTION] Detection service not available: {ie}")
        return None
    except Exception as e:
        logger.warning(f"[DETECTION] Detection failed: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return None


def get_project_detection_summary(project: str) -> Optional[Dict]:
    """
    Get a summary of detected context for a project.
    
    Returns:
        Dict with systems, domains, functional_areas, or None
    """
    try:
        try:
            from utils.detection_service import get_detection_service
        except ImportError:
            from backend.utils.detection_service import get_detection_service
        
        service = get_detection_service()
        context = service.get_project_context(project)
        
        if not context:
            return None
        
        return {
            'systems': context.get('systems', []),
            'domains': context.get('domains', []),
            'functional_areas': context.get('functional_areas', []),
            'engagement_type': context.get('engagement_type'),
            'confirmed': context.get('context_confirmed', False),
            'detected_context': context.get('detected_context', {})
        }
        
    except Exception as e:
        logger.debug(f"[DETECTION] Could not get project summary: {e}")
        return None


def format_detection_for_chat(project: str) -> Optional[str]:
    """
    Format detected context as a string for chat context.
    
    Returns a human-readable summary of what systems/domains were detected.
    """
    summary = get_project_detection_summary(project)
    
    if not summary:
        return None
    
    parts = []
    
    # Systems
    systems = summary.get('systems', [])
    if systems:
        if isinstance(systems[0], dict):
            sys_names = [s.get('name', s.get('code', '?')) for s in systems]
        else:
            sys_names = systems
        parts.append(f"Systems: {', '.join(sys_names)}")
    
    # Domains
    domains = summary.get('domains', [])
    if domains:
        if isinstance(domains[0], dict):
            dom_names = [d.get('name', d.get('code', '?')) for d in domains]
        else:
            dom_names = domains
        parts.append(f"Domains: {', '.join(dom_names)}")
    
    # Functional areas
    func_areas = summary.get('functional_areas', [])
    if func_areas:
        if isinstance(func_areas[0], dict):
            fa_names = [f.get('name', f.get('area', f.get('code', '?'))) for f in func_areas]
        else:
            fa_names = [str(f) for f in func_areas]
        if len(fa_names) > 5:
            parts.append(f"Functional Areas: {', '.join(fa_names[:5])}... ({len(fa_names)} total)")
        else:
            parts.append(f"Functional Areas: {', '.join(fa_names)}")
    
    # Engagement type
    engagement = summary.get('engagement_type')
    if engagement:
        parts.append(f"Engagement: {engagement}")
    
    if not parts:
        return None
    
    return " | ".join(parts)


def detect_from_file_characteristics(
    filename: str,
    columns: List[str] = None,
    sheet_names: List[str] = None
) -> Optional[Dict]:
    """
    Quick detection from file characteristics without needing full project context.
    
    Useful for upload preview or file classification.
    
    Args:
        filename: File name
        columns: List of column names (optional)
        sheet_names: Excel sheet names (optional)
        
    Returns:
        Detection result dict
    """
    try:
        try:
            from utils.detection_service import get_detection_service
        except ImportError:
            from backend.utils.detection_service import get_detection_service
        
        service = get_detection_service()
        result = service.detect(
            filename=filename,
            columns=columns,
            sheet_names=sheet_names
        )
        
        return result.to_dict()
        
    except Exception as e:
        logger.debug(f"[DETECTION] Quick detection failed: {e}")
        return None
