"""
PLAYBOOK FRAMEWORK - Query Service
===================================

Handles loading playbook definitions from various sources.

Sources:
- DuckDB: Vendor-prescribed playbooks parsed from uploaded docs
- Stored: XLR8-defined playbooks stored in config
- Generated: Playbooks created from consultant intent

Author: XLR8 Team
Created: January 18, 2026
"""

import os
import re
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from .definitions import (
    PlaybookDefinition, PlaybookType, StepDefinition, EngineConfig
)

logger = logging.getLogger(__name__)

# DuckDB path
DUCKDB_PATH = "/data/structured_data.duckdb"


class QueryService:
    """
    Service for loading playbook definitions from various sources.
    
    Responsibilities:
    - Load vendor playbooks from DuckDB (parsed uploaded docs)
    - Load XLR8-defined playbooks from stored config
    - Parse step requirements and analysis configs
    """
    
    def __init__(self, duckdb_path: str = DUCKDB_PATH):
        self.duckdb_path = duckdb_path
        self._conn = None
        self._cache: Dict[str, PlaybookDefinition] = {}
    
    def _get_connection(self):
        """Get DuckDB connection."""
        if self._conn is not None:
            return self._conn
        
        try:
            import duckdb
            if os.path.exists(self.duckdb_path):
                self._conn = duckdb.connect(self.duckdb_path, read_only=True)
                return self._conn
        except Exception as e:
            logger.error(f"[QUERY] Failed to connect to DuckDB: {e}")
        
        return None
    
    # =========================================================================
    # VENDOR PLAYBOOK LOADING (Year-End style)
    # =========================================================================
    
    def load_vendor_playbook(
        self, 
        playbook_id: str,
        force_refresh: bool = False
    ) -> Optional[PlaybookDefinition]:
        """
        Load a vendor-prescribed playbook from DuckDB.
        
        This replaces the hardcoded Year-End parsing with a generic approach.
        """
        cache_key = f"vendor:{playbook_id}"
        
        if not force_refresh and cache_key in self._cache:
            return self._cache[cache_key]
        
        conn = self._get_connection()
        if not conn:
            logger.warning(f"[QUERY] No DuckDB connection, cannot load {playbook_id}")
            return None
        
        # Find tables for this playbook
        tables = self._find_playbook_tables(conn, playbook_id)
        if not tables:
            logger.warning(f"[QUERY] No tables found for playbook {playbook_id}")
            return None
        
        # Parse steps from tables
        steps = self._parse_steps_from_tables(conn, tables)
        
        # Load expert path if exists
        expert_path = self._load_expert_path(conn, playbook_id)
        
        # Load step documents (required files per step)
        step_docs = self._load_step_documents(conn, playbook_id)
        
        # Attach required data to steps
        for step in steps:
            if step.id in step_docs:
                step.required_data = step_docs[step.id]
        
        # Create definition
        definition = PlaybookDefinition(
            id=playbook_id,
            name=self._get_playbook_name(playbook_id),
            type=PlaybookType.VENDOR,
            description=f"Vendor-prescribed playbook loaded from uploaded document",
            steps=steps,
            expert_path=expert_path,
            source_file=tables[0].get('file_name') if tables else None,
            created_at=datetime.now()
        )
        
        self._cache[cache_key] = definition
        logger.info(f"[QUERY] Loaded vendor playbook '{playbook_id}' with {len(steps)} steps")
        
        return definition
    
    def _find_playbook_tables(
        self, 
        conn, 
        playbook_id: str
    ) -> List[Dict[str, Any]]:
        """Find DuckDB tables for a playbook."""
        
        # Pattern mappings for known playbook types
        patterns = {
            'year-end': {
                'project_patterns': ['global', 'reference library', 'reference_library', '__standards__'],
                'sheet_patterns': ['before%payroll%', 'after%payroll%', 'before%final%', 'after%final%']
            }
        }
        
        config = patterns.get(playbook_id, {})
        project_patterns = config.get('project_patterns', ['global'])
        sheet_patterns = config.get('sheet_patterns', [f'%{playbook_id}%'])
        
        try:
            # Build WHERE clause for projects
            project_clauses = " OR ".join([
                f"LOWER(project) = '{p}'" if '%' not in p else f"LOWER(project) LIKE '{p}'"
                for p in project_patterns
            ])
            
            # Build WHERE clause for sheets
            sheet_clauses = " OR ".join([
                f"LOWER(sheet_name) LIKE '{s}'" for s in sheet_patterns
            ])
            
            query = f"""
                SELECT DISTINCT project, file_name, sheet_name, table_name, columns, row_count
                FROM _schema_metadata
                WHERE is_current = TRUE
                AND ({project_clauses})
                AND ({sheet_clauses})
                ORDER BY sheet_name
            """
            
            results = conn.execute(query).fetchall()
            
            tables = []
            for row in results:
                tables.append({
                    'project': row[0],
                    'file_name': row[1],
                    'sheet_name': row[2],
                    'table_name': row[3],
                    'columns': json.loads(row[4]) if row[4] else [],
                    'row_count': row[5]
                })
            
            return tables
            
        except Exception as e:
            logger.error(f"[QUERY] Error finding playbook tables: {e}")
            return []
    
    def _parse_steps_from_tables(
        self, 
        conn, 
        tables: List[Dict]
    ) -> List[StepDefinition]:
        """Parse step definitions from DuckDB tables."""
        steps = []
        seen_ids = set()
        sequence = 0
        
        for table_info in tables:
            table_name = table_info['table_name']
            sheet_name = table_info['sheet_name']
            
            # Determine phase from sheet name
            phase = 'main'
            if 'before' in sheet_name.lower():
                phase = 'before_final_payroll'
            elif 'after' in sheet_name.lower():
                phase = 'after_final_payroll'
            
            try:
                # Try to find action_id and description columns
                # Columns may be strings or dicts with 'name' key
                raw_columns = table_info.get('columns', [])
                columns = []
                for c in raw_columns:
                    if isinstance(c, dict):
                        columns.append(c.get('name', '').lower())
                    elif isinstance(c, str):
                        columns.append(c.lower())
                    else:
                        columns.append(str(c).lower())
                
                action_col = None
                desc_col = None
                
                for col in columns:
                    if 'action' in col and 'id' in col:
                        action_col = col
                    elif 'description' in col or 'action_description' in col:
                        desc_col = col
                
                if not action_col:
                    # Try without underscore
                    for col in columns:
                        if col in ['actionid', 'action', 'step', 'stepid']:
                            action_col = col
                            break
                
                if not action_col:
                    logger.warning(f"[QUERY] No action_id column found in {table_name}")
                    continue
                
                # Query the table
                select_cols = [action_col]
                if desc_col:
                    select_cols.append(desc_col)
                
                query = f"SELECT DISTINCT {', '.join(select_cols)} FROM \"{table_name}\" ORDER BY {action_col}"
                rows = conn.execute(query).fetchall()
                
                for row in rows:
                    action_id = str(row[0]).strip() if row[0] else None
                    if not action_id or action_id in seen_ids:
                        continue
                    
                    description = str(row[1]).strip() if len(row) > 1 and row[1] else ""
                    
                    # Parse step number from action_id (e.g., "2A" -> step 2)
                    step_match = re.match(r'^(\d+)', action_id)
                    step_num = step_match.group(1) if step_match else str(sequence)
                    
                    step = StepDefinition(
                        id=action_id,
                        name=f"Step {action_id}",
                        description=description,
                        sequence=sequence,
                        phase=phase
                    )
                    
                    steps.append(step)
                    seen_ids.add(action_id)
                    sequence += 1
                
            except Exception as e:
                logger.warning(f"[QUERY] Error parsing table {table_name}: {e}")
                continue
        
        return steps
    
    def _load_expert_path(
        self, 
        conn, 
        playbook_id: str
    ) -> Optional[List[str]]:
        """Load expert path sequence if it exists."""
        try:
            # Look for Fast Track sheet
            query = """
                SELECT table_name 
                FROM _schema_metadata
                WHERE is_current = TRUE
                AND (LOWER(sheet_name) LIKE '%fast%track%' OR LOWER(sheet_name) LIKE '%expert%')
                LIMIT 1
            """
            result = conn.execute(query).fetchone()
            
            if result:
                table_name = result[0]
                # Get the sequence
                seq_query = f"""
                    SELECT action_id 
                    FROM \"{table_name}\" 
                    WHERE action_id IS NOT NULL
                    ORDER BY sequence, action_id
                """
                rows = conn.execute(seq_query).fetchall()
                return [str(r[0]).strip() for r in rows if r[0]]
            
        except Exception as e:
            logger.debug(f"[QUERY] No expert path found: {e}")
        
        return None
    
    def _load_step_documents(
        self, 
        conn, 
        playbook_id: str
    ) -> Dict[str, List[str]]:
        """Load required documents per step."""
        step_docs = {}
        
        try:
            # Look for Step_Documents sheet
            query = """
                SELECT table_name 
                FROM _schema_metadata
                WHERE is_current = TRUE
                AND LOWER(sheet_name) LIKE '%step%document%'
                LIMIT 1
            """
            result = conn.execute(query).fetchone()
            
            if result:
                table_name = result[0]
                
                # Get step -> document mappings
                doc_query = f"""
                    SELECT step_number, keyword, description, required
                    FROM \"{table_name}\"
                    WHERE step_number IS NOT NULL AND keyword IS NOT NULL
                """
                rows = conn.execute(doc_query).fetchall()
                
                for row in rows:
                    step = str(row[0]).strip()
                    keyword = str(row[1]).strip()
                    
                    if step not in step_docs:
                        step_docs[step] = []
                    step_docs[step].append(keyword)
            
        except Exception as e:
            logger.debug(f"[QUERY] No step documents found: {e}")
        
        return step_docs
    
    def _get_playbook_name(self, playbook_id: str) -> str:
        """Get human-readable playbook name."""
        names = {
            'year-end': 'Year-End Checklist',
            'implementation': 'Implementation Audit',
            'quarterly': 'Quarterly Review',
        }
        return names.get(playbook_id, playbook_id.replace('-', ' ').title())
    
    # =========================================================================
    # XLR8-DEFINED PLAYBOOKS
    # =========================================================================
    
    def load_xlr8_playbook(self, playbook_id: str) -> Optional[PlaybookDefinition]:
        """Load an XLR8-defined playbook from stored configuration."""
        cache_key = f"xlr8:{playbook_id}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # TODO: Load from config file or database
        # For now, return None - these will be defined later
        
        return None
    
    # =========================================================================
    # GENERIC LOADING
    # =========================================================================
    
    def load_playbook(
        self, 
        playbook_id: str, 
        playbook_type: Optional[PlaybookType] = None
    ) -> Optional[PlaybookDefinition]:
        """
        Load a playbook by ID, auto-detecting type if not specified.
        """
        # If type specified, use it
        if playbook_type == PlaybookType.VENDOR:
            return self.load_vendor_playbook(playbook_id)
        elif playbook_type == PlaybookType.XLR8:
            return self.load_xlr8_playbook(playbook_id)
        
        # Auto-detect: try vendor first, then XLR8
        definition = self.load_vendor_playbook(playbook_id)
        if definition:
            return definition
        
        definition = self.load_xlr8_playbook(playbook_id)
        if definition:
            return definition
        
        logger.warning(f"[QUERY] Playbook '{playbook_id}' not found")
        return None
    
    def list_available_playbooks(self) -> List[Dict[str, Any]]:
        """List all available playbooks."""
        playbooks = []
        
        # Check for vendor playbooks in DuckDB
        conn = self._get_connection()
        if conn:
            try:
                # Look for known patterns
                known_types = [
                    ('year-end', 'Year-End Checklist', ['before%payroll', 'after%payroll']),
                ]
                
                for pb_id, pb_name, patterns in known_types:
                    for pattern in patterns:
                        query = f"""
                            SELECT COUNT(*) FROM _schema_metadata
                            WHERE is_current = TRUE
                            AND LOWER(sheet_name) LIKE '{pattern}'
                        """
                        count = conn.execute(query).fetchone()[0]
                        if count > 0:
                            playbooks.append({
                                'id': pb_id,
                                'name': pb_name,
                                'type': 'vendor',
                                'available': True
                            })
                            break
                
            except Exception as e:
                logger.warning(f"[QUERY] Error listing playbooks: {e}")
        
        return playbooks


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_query_service = None

def get_query_service() -> QueryService:
    """Get the singleton query service instance."""
    global _query_service
    if _query_service is None:
        _query_service = QueryService()
    return _query_service
