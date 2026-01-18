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
    EngineConfig, TableResolution
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
        """
        Resolve placeholders in engine config using hybrid strategy:
        1. Check step_progress.resolved_tables for manual overrides
        2. Try term_index resolution
        3. Fall back to matched_files
        """
        resolved = {}
        
        for key, value in config.items():
            if isinstance(value, str) and value.startswith('{{') and value.endswith('}}'):
                placeholder = value[2:-2]  # e.g., 'w_2_data'
                resolved_table = None
                
                # Strategy 1: Check for manual override or cached resolution
                if step_progress and placeholder in step_progress.resolved_tables:
                    resolution = step_progress.resolved_tables[placeholder]
                    if resolution.resolved_table:
                        resolved_table = resolution.resolved_table
                        logger.info(f"[EXEC] Placeholder '{placeholder}' resolved from cache/manual: {resolved_table}")
                
                # Strategy 2: Try term_index
                if not resolved_table:
                    resolved_table = self._resolve_via_term_index(placeholder)
                    if resolved_table:
                        logger.info(f"[EXEC] Placeholder '{placeholder}' resolved via term_index: {resolved_table}")
                
                # Strategy 3: Fall back to matched_files
                if not resolved_table and step_progress and step_progress.matched_files:
                    resolved_table = self._resolve_via_matched_files(placeholder, step_progress.matched_files)
                    if resolved_table:
                        logger.info(f"[EXEC] Placeholder '{placeholder}' resolved via matched_files: {resolved_table}")
                
                # Use resolved table or keep placeholder
                resolved[key] = resolved_table if resolved_table else value
                if not resolved_table:
                    logger.warning(f"[EXEC] Could not resolve placeholder '{placeholder}'")
                    
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
    
    def _resolve_via_term_index(self, placeholder: str) -> Optional[str]:
        """Try to resolve a placeholder using term_index."""
        conn = self._get_connection()
        if not conn:
            return None
        
        try:
            # Import term_index
            try:
                from utils.intelligence.term_index import TermIndex
            except ImportError:
                from backend.utils.intelligence.term_index import TermIndex
            
            term_index = TermIndex(conn, self.project)
            
            # Convert placeholder to search terms (w_2_data → ['w-2', 'w2'])
            search_terms = self._placeholder_to_terms(placeholder)
            
            matches = term_index.resolve_terms(search_terms)
            if matches:
                # Return the highest confidence match
                best_match = max(matches, key=lambda m: m.confidence)
                return best_match.table_name
                
        except Exception as e:
            logger.warning(f"[EXEC] term_index resolution failed for '{placeholder}': {e}")
        
        return None
    
    def _resolve_via_matched_files(self, placeholder: str, matched_files: List[str]) -> Optional[str]:
        """Try to resolve a placeholder using matched files."""
        # Convert placeholder to likely filename patterns
        patterns = self._placeholder_to_patterns(placeholder)
        
        for filename in matched_files:
            filename_lower = filename.lower()
            for pattern in patterns:
                if pattern in filename_lower:
                    # Found a matching file - convert to table name
                    return self._file_to_table(filename)
        
        return None
    
    def _placeholder_to_terms(self, placeholder: str) -> List[str]:
        """Convert a placeholder to search terms for term_index."""
        # 'w_2_data' → ['w-2', 'w2', 'w 2']
        # 'employee_data' → ['employee']
        
        # Remove common suffixes
        base = placeholder.replace('_data', '').replace('_table', '').replace('_report', '')
        
        terms = []
        
        # Add with underscores converted to various formats
        terms.append(base.replace('_', '-'))  # w_2 → w-2
        terms.append(base.replace('_', ''))   # w_2 → w2
        terms.append(base.replace('_', ' '))  # w_2 → w 2
        terms.append(base)                     # w_2
        
        return terms
    
    def _placeholder_to_patterns(self, placeholder: str) -> List[str]:
        """Convert a placeholder to filename search patterns."""
        base = placeholder.replace('_data', '').replace('_table', '').replace('_report', '')
        
        patterns = []
        patterns.append(base.replace('_', '-'))
        patterns.append(base.replace('_', ''))
        patterns.append(base.replace('_', ' '))
        patterns.append(base)
        
        return patterns
    
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


    # =========================================================================
    # TABLE RESOLUTION
    # =========================================================================
    
    def resolve_step_placeholders(
        self,
        step: StepDefinition,
        step_progress: Optional[StepProgress]
    ) -> Dict[str, TableResolution]:
        """
        Auto-resolve all placeholders in a step's analysis configs.
        
        Returns dict of placeholder → TableResolution for UI display.
        Consultant can then override any of these.
        """
        resolutions = {}
        
        # Extract all placeholders from analysis configs
        placeholders = self._extract_placeholders(step.analysis)
        
        for placeholder in placeholders:
            # Skip if already manually set
            if step_progress and placeholder in step_progress.resolved_tables:
                existing = step_progress.resolved_tables[placeholder]
                if existing.manually_set:
                    resolutions[placeholder] = existing
                    continue
            
            # Try hybrid resolution
            resolution = self._auto_resolve_placeholder(placeholder, step_progress)
            resolutions[placeholder] = resolution
        
        return resolutions
    
    def _extract_placeholders(self, configs: List[EngineConfig]) -> List[str]:
        """Extract all placeholders from engine configs."""
        placeholders = []
        
        def extract_from_dict(d: Dict):
            for value in d.values():
                if isinstance(value, str) and value.startswith('{{') and value.endswith('}}'):
                    placeholder = value[2:-2]
                    if placeholder not in placeholders:
                        placeholders.append(placeholder)
                elif isinstance(value, dict):
                    extract_from_dict(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            extract_from_dict(item)
        
        for config in configs:
            extract_from_dict(config.config)
        
        return placeholders
    
    def _auto_resolve_placeholder(
        self, 
        placeholder: str,
        step_progress: Optional[StepProgress]
    ) -> TableResolution:
        """
        Auto-resolve a single placeholder using hybrid strategy.
        Returns TableResolution with alternatives for UI.
        """
        resolution = TableResolution(placeholder=placeholder)
        alternatives = []
        
        # Strategy 1: term_index
        term_table = self._resolve_via_term_index(placeholder)
        if term_table:
            resolution.resolved_table = term_table
            resolution.resolution_method = 'term_index'
            resolution.confidence = 0.8
        
        # Strategy 2: matched_files (use as alternative or primary)
        if step_progress and step_progress.matched_files:
            file_table = self._resolve_via_matched_files(placeholder, step_progress.matched_files)
            if file_table:
                if not resolution.resolved_table:
                    resolution.resolved_table = file_table
                    resolution.resolution_method = 'matched_files'
                    resolution.confidence = 0.7
                elif file_table != resolution.resolved_table:
                    alternatives.append(file_table)
        
        # Get more alternatives from available tables
        more_alternatives = self._find_alternative_tables(placeholder)
        for alt in more_alternatives:
            if alt not in alternatives and alt != resolution.resolved_table:
                alternatives.append(alt)
        
        resolution.alternatives = alternatives[:5]  # Limit to 5
        
        return resolution
    
    def _find_alternative_tables(self, placeholder: str) -> List[str]:
        """Find tables that might match a placeholder."""
        conn = self._get_connection()
        if not conn:
            return []
        
        alternatives = []
        patterns = self._placeholder_to_patterns(placeholder)
        
        try:
            # Search _schema_metadata for matching tables
            for pattern in patterns:
                results = conn.execute("""
                    SELECT DISTINCT table_name 
                    FROM _schema_metadata 
                    WHERE is_current = TRUE
                    AND (
                        LOWER(table_name) LIKE ? 
                        OR LOWER(file_name) LIKE ?
                    )
                    LIMIT 5
                """, [f"%{pattern}%", f"%{pattern}%"]).fetchall()
                
                for row in results:
                    if row[0] not in alternatives:
                        alternatives.append(row[0])
                
                if len(alternatives) >= 5:
                    break
                    
        except Exception as e:
            logger.warning(f"[EXEC] Failed to find alternative tables for '{placeholder}': {e}")
        
        return alternatives
    
    def get_available_tables(self, filter_pattern: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all available tables for manual selection dropdown.
        
        Returns list of {table_name, file_name, row_count, columns} dicts.
        """
        conn = self._get_connection()
        if not conn:
            return []
        
        try:
            # Check if project_id column exists for newer schema
            has_project_id = False
            try:
                cols = [row[1] for row in conn.execute("PRAGMA table_info(_schema_metadata)").fetchall()]
                has_project_id = 'project_id' in cols
            except Exception:
                pass
            
            # Build WHERE clause for project filtering
            # Try project_id first (UUID), fall back to project name
            project_filter_sql = ""
            project_params = []
            
            if has_project_id and self.project:
                # Try to match by project_id (UUID) OR project name (for backward compat)
                project_filter_sql = "AND (project_id = ? OR LOWER(project) = LOWER(?))"
                project_params = [self.project, self.project]
            elif self.project:
                project_filter_sql = "AND LOWER(project) = LOWER(?)"
                project_params = [self.project]
            
            # Build query with optional filter
            if filter_pattern:
                results = conn.execute(f"""
                    SELECT table_name, file_name, row_count
                    FROM _schema_metadata 
                    WHERE is_current = TRUE
                    {project_filter_sql}
                    AND (
                        LOWER(table_name) LIKE ? 
                        OR LOWER(file_name) LIKE ?
                    )
                    ORDER BY file_name
                    LIMIT 50
                """, project_params + [f"%{filter_pattern.lower()}%", f"%{filter_pattern.lower()}%"]).fetchall()
            else:
                results = conn.execute(f"""
                    SELECT table_name, file_name, row_count
                    FROM _schema_metadata 
                    WHERE is_current = TRUE
                    {project_filter_sql}
                    ORDER BY file_name
                    LIMIT 50
                """, project_params).fetchall()
            
            tables = []
            for row in results:
                tables.append({
                    'table_name': row[0],
                    'file_name': row[1],
                    'row_count': row[2]
                })
            
            logger.info(f"[EXEC] Found {len(tables)} tables for project '{self.project}'")
            return tables
            
        except Exception as e:
            logger.error(f"[EXEC] Failed to get available tables: {e}")
            return []
    
    def set_table_resolution(
        self,
        instance_id: str,
        step_id: str,
        placeholder: str,
        table_name: str
    ) -> TableResolution:
        """
        Manually set/override a table resolution.
        
        This is called when the consultant picks a different table.
        """
        resolution = TableResolution(
            placeholder=placeholder,
            resolved_table=table_name,
            resolution_method='manual',
            confidence=1.0,
            manually_set=True
        )
        
        # Persist to progress_service
        progress_service = get_progress_service()
        progress_service.set_resolved_table(instance_id, step_id, placeholder, resolution)
        
        logger.info(f"[EXEC] Manual table resolution: {placeholder} → {table_name}")
        
        return resolution


# =============================================================================
# SINGLETON/FACTORY
# =============================================================================

_execution_services: Dict[str, ExecutionService] = {}

def get_execution_service(project: str) -> ExecutionService:
    """Get execution service for a project."""
    if project not in _execution_services:
        _execution_services[project] = ExecutionService(project)
    return _execution_services[project]
