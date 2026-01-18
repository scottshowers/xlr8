"""
PLAYBOOK FRAMEWORK - Execution Service
=======================================

Handles running analysis (engines) against playbook steps.

Responsibilities:
- Execute engine configs for a step
- Collect findings with provenance
- Synthesize results into observations
- Support re-analysis with AI context

Author: XLR8 Team
Created: January 18, 2026
"""

import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime

from .definitions import (
    PlaybookDefinition, PlaybookInstance, StepDefinition,
    StepProgress, Finding, StepStatus, FindingStatus, FindingSeverity,
    EngineConfig
)
from .progress_service import get_progress_service

logger = logging.getLogger(__name__)


class ExecutionService:
    """
    Service for executing analysis against playbook steps.
    
    Uses the universal engines (aggregate, compare, validate, detect, map)
    to analyze data and produce findings.
    """
    
    def __init__(self, project: str):
        self.project = project
        self._conn = None
        self._engines = None
    
    def _get_connection(self):
        """Get DuckDB connection for this project."""
        if self._conn:
            return self._conn
        
        # Use the structured_handler singleton - this is the pattern used everywhere else
        try:
            from utils.structured_data_handler import get_structured_handler
            handler = get_structured_handler()
            self._conn = handler.conn
            logger.info(f"[EXEC] Got connection from structured_handler (utils)")
            return self._conn
        except ImportError:
            pass
        
        try:
            from backend.utils.structured_data_handler import get_structured_handler
            handler = get_structured_handler()
            self._conn = handler.conn
            logger.info(f"[EXEC] Got connection from structured_handler (backend.utils)")
            return self._conn
        except ImportError:
            pass
        
        # Fallback: direct connection
        try:
            import duckdb
            import os
            
            duckdb_path = "/data/structured_data.duckdb"
            if os.path.exists(duckdb_path):
                self._conn = duckdb.connect(duckdb_path)
                logger.info(f"[EXEC] Direct connection to DuckDB at {duckdb_path}")
                return self._conn
            else:
                logger.error(f"[EXEC] DuckDB file not found at {duckdb_path}")
                if os.path.exists("/data"):
                    files = os.listdir("/data")
                    logger.error(f"[EXEC] /data contains: {files[:10]}")
                else:
                    logger.error("[EXEC] /data directory does not exist")
        except Exception as e:
            logger.error(f"[EXEC] Failed to connect to DuckDB: {e}")
            import traceback
            logger.error(f"[EXEC] Traceback: {traceback.format_exc()}")
        
        return None
    
    def _get_engines(self):
        """Load engine modules."""
        if self._engines:
            return self._engines
        
        try:
            from backend.engines import (
                AggregateEngine, CompareEngine, ValidateEngine,
                DetectEngine, MapEngine
            )
            self._engines = {
                'aggregate': AggregateEngine,
                'compare': CompareEngine,
                'validate': ValidateEngine,
                'detect': DetectEngine,
                'map': MapEngine
            }
            logger.info(f"[EXEC] Loaded engines from backend.engines: {list(self._engines.keys())}")
        except ImportError as e1:
            logger.warning(f"[EXEC] Failed to import from backend.engines: {e1}")
            try:
                from engines import (
                    AggregateEngine, CompareEngine, ValidateEngine,
                    DetectEngine, MapEngine
                )
                self._engines = {
                    'aggregate': AggregateEngine,
                    'compare': CompareEngine,
                    'validate': ValidateEngine,
                    'detect': DetectEngine,
                    'map': MapEngine
                }
                logger.info(f"[EXEC] Loaded engines from engines: {list(self._engines.keys())}")
            except ImportError as e2:
                logger.error(f"[EXEC] Failed to import from engines: {e2}")
                logger.error("[EXEC] Engines module not available from either path")
                import traceback
                logger.error(f"[EXEC] Traceback: {traceback.format_exc()}")
                return None
        
        return self._engines
    
    # =========================================================================
    # STEP EXECUTION
    # =========================================================================
    
    def execute_step(
        self,
        instance: PlaybookInstance,
        step: StepDefinition,
        force_refresh: bool = False,
        ai_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute analysis for a playbook step.
        
        Args:
            instance: The playbook instance
            step: The step definition
            force_refresh: Clear previous findings before running
            ai_context: Additional context for AI analysis
            
        Returns:
            Dict with execution results
        """
        step_id = step.id
        progress_service = get_progress_service()
        
        logger.info(f"[EXEC] Executing step {step_id} for project {self.project}")
        
        # Check if blocked
        step_progress = instance.progress.get(step_id)
        if step_progress and step_progress.missing_data:
            logger.warning(f"[EXEC] Step {step_id} is blocked - missing data: {step_progress.missing_data}")
            return {
                'success': False,
                'step_id': step_id,
                'status': 'blocked',
                'message': f"Missing required data: {', '.join(step_progress.missing_data)}"
            }
        
        # Clear previous findings if force refresh
        if force_refresh:
            progress_service.clear_findings(instance.id, step_id)
        
        # Update status to in progress
        progress_service.update_step_status(instance.id, step_id, StepStatus.IN_PROGRESS)
        
        # Store AI context if provided
        if ai_context:
            progress_service.update_step_status(
                instance.id, step_id, StepStatus.IN_PROGRESS, 
                ai_context=ai_context
            )
        
        # Execute each analysis config
        all_findings = []
        engine_results = []
        
        for engine_config in step.analysis:
            result = self._execute_engine(engine_config, step_progress, ai_context)
            engine_results.append(result)
            
            if result.get('findings'):
                all_findings.extend(result['findings'])
        
        # Add findings to progress
        if all_findings:
            progress_service.add_findings(instance.id, step_id, all_findings)
        
        # Determine suggested status
        has_critical = any(f.severity == FindingSeverity.CRITICAL for f in all_findings)
        has_issues = len(all_findings) > 0
        
        suggested_status = StepStatus.COMPLETE
        if has_critical:
            suggested_status = StepStatus.IN_PROGRESS  # Needs attention
        
        return {
            'success': True,
            'step_id': step_id,
            'status': 'complete',
            'findings_count': len(all_findings),
            'suggested_status': suggested_status.value,
            'engine_results': engine_results,
            'findings': [self._finding_to_dict(f) for f in all_findings]
        }
    
    def _execute_engine(
        self,
        config: EngineConfig,
        step_progress: Optional[StepProgress],
        ai_context: Optional[str]
    ) -> Dict[str, Any]:
        """Execute a single engine config."""
        engines = self._get_engines()
        conn = self._get_connection()
        
        # Detailed error reporting
        if not engines and not conn:
            logger.error("[EXEC] Both engines and connection unavailable")
            return {
                'success': False,
                'engine': config.engine,
                'error': 'Both engines module and DuckDB connection unavailable'
            }
        elif not engines:
            logger.error("[EXEC] Engines module not available")
            return {
                'success': False,
                'engine': config.engine,
                'error': 'Engines module import failed - check backend.engines path'
            }
        elif not conn:
            logger.error("[EXEC] DuckDB connection not available")
            return {
                'success': False,
                'engine': config.engine,
                'error': 'DuckDB connection failed - /data/structured_data.duckdb not found or not accessible'
            }
        
        engine_class = engines.get(config.engine)
        if not engine_class:
            return {
                'success': False,
                'engine': config.engine,
                'error': f"Unknown engine: {config.engine}"
            }
        
        try:
            # Create engine instance
            engine = engine_class(conn, self.project)
            
            # Resolve table placeholders if we have matched files
            resolved_config = self._resolve_config(config.config, step_progress)
            
            # Execute
            result = engine.execute(resolved_config)
            
            # Convert engine findings to framework findings
            findings = self._convert_findings(config.engine, result)
            
            return {
                'success': True,
                'engine': config.engine,
                'row_count': result.row_count if hasattr(result, 'row_count') else 0,
                'sql': result.sql if hasattr(result, 'sql') else None,
                'findings': findings,
                'summary': result.summary if hasattr(result, 'summary') else None
            }
            
        except Exception as e:
            logger.error(f"[EXEC] Engine {config.engine} failed: {e}")
            return {
                'success': False,
                'engine': config.engine,
                'error': str(e)
            }
    
    def _resolve_config(
        self, 
        config: Dict[str, Any], 
        step_progress: Optional[StepProgress]
    ) -> Dict[str, Any]:
        """Resolve placeholders in engine config."""
        resolved = {}
        
        for key, value in config.items():
            if isinstance(value, str) and value.startswith('{{') and value.endswith('}}'):
                # Placeholder - try to resolve from matched files
                placeholder = value[2:-2]
                
                if step_progress and step_progress.matched_files:
                    # Try to find a matching table
                    for matched_file in step_progress.matched_files:
                        # Convert filename to likely table name
                        # This is simplified - real implementation needs table lookup
                        resolved[key] = self._file_to_table(matched_file)
                        break
                    else:
                        resolved[key] = value  # Keep placeholder if no match
                else:
                    resolved[key] = value
            elif isinstance(value, dict):
                resolved[key] = self._resolve_config(value, step_progress)
            elif isinstance(value, list):
                resolved[key] = [
                    self._resolve_config(item, step_progress) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                resolved[key] = value
        
        return resolved
    
    def _file_to_table(self, filename: str) -> str:
        """Convert a filename to a DuckDB table name."""
        # This needs to query _schema_metadata to find the actual table
        conn = self._get_connection()
        if not conn:
            return filename
        
        try:
            # Look for table matching this filename
            result = conn.execute("""
                SELECT table_name 
                FROM _schema_metadata 
                WHERE file_name LIKE ? 
                AND is_current = TRUE
                LIMIT 1
            """, [f"%{filename}%"]).fetchone()
            
            if result:
                return result[0]
        except Exception as e:
            logger.warning(f"[EXEC] Could not find table for {filename}: {e}")
        
        return filename
    
    def _convert_findings(
        self, 
        engine: str, 
        result: Any
    ) -> List[Finding]:
        """Convert engine results to framework findings."""
        findings = []
        
        if not hasattr(result, 'findings') or not result.findings:
            return findings
        
        for i, engine_finding in enumerate(result.findings):
            # Determine severity
            severity = FindingSeverity.MEDIUM
            if isinstance(engine_finding, dict):
                sev_str = engine_finding.get('severity', 'medium').lower()
                try:
                    severity = FindingSeverity(sev_str)
                except ValueError:
                    pass
                
                message = engine_finding.get('message', str(engine_finding))
                details = engine_finding
            else:
                message = str(engine_finding)
                details = {'raw': engine_finding}
            
            finding = Finding(
                id=str(uuid.uuid4()),
                step_id='',  # Will be set by caller
                engine=engine,
                severity=severity,
                message=message,
                details=details,
                source_table=getattr(result, 'source_table', None),
                sql_query=getattr(result, 'sql', None),
                status=FindingStatus.ACTIVE
            )
            
            findings.append(finding)
        
        return findings
    
    def _finding_to_dict(self, finding: Finding) -> Dict[str, Any]:
        """Convert Finding to dict for JSON serialization."""
        return {
            'id': finding.id,
            'step_id': finding.step_id,
            'engine': finding.engine,
            'severity': finding.severity.value,
            'message': finding.message,
            'details': finding.details,
            'source_table': finding.source_table,
            'sql_query': finding.sql_query,
            'status': finding.status.value
        }
    
    # =========================================================================
    # BATCH EXECUTION
    # =========================================================================
    
    def execute_all_steps(
        self,
        instance: PlaybookInstance,
        playbook: PlaybookDefinition,
        skip_blocked: bool = True
    ) -> Dict[str, Any]:
        """
        Execute all steps in a playbook.
        
        Args:
            instance: The playbook instance
            playbook: The playbook definition
            skip_blocked: Skip steps that are blocked (missing data)
            
        Returns:
            Dict with overall execution results
        """
        results = []
        total_findings = 0
        skipped = 0
        failed = 0
        
        for step in playbook.steps:
            step_progress = instance.progress.get(step.id)
            
            # Check if blocked
            if skip_blocked and step_progress and step_progress.missing_data:
                results.append({
                    'step_id': step.id,
                    'status': 'skipped',
                    'reason': 'blocked'
                })
                skipped += 1
                continue
            
            # Execute step
            result = self.execute_step(instance, step)
            results.append(result)
            
            if result.get('success'):
                total_findings += result.get('findings_count', 0)
            else:
                failed += 1
        
        return {
            'success': failed == 0,
            'total_steps': len(playbook.steps),
            'executed': len(playbook.steps) - skipped,
            'skipped': skipped,
            'failed': failed,
            'total_findings': total_findings,
            'results': results
        }


# =============================================================================
# SINGLETON/FACTORY
# =============================================================================

_execution_services: Dict[str, ExecutionService] = {}

def get_execution_service(project: str) -> ExecutionService:
    """Get execution service for a project."""
    if project not in _execution_services:
        _execution_services[project] = ExecutionService(project)
    return _execution_services[project]
