"""
XLR8 Intelligence Engine - Reality Gatherer
============================================

Gathers REALITY truths - what actually exists in the customer's data.

This is the most important gatherer as Reality is the ground truth
against which everything else is compared.

Storage: DuckDB
Source: Customer uploaded data (employees, payroll, transactions, etc.)

Deploy to: backend/utils/intelligence/gatherers/reality.py
"""

import logging
from typing import Dict, List, Optional, Any

from .base import DuckDBGatherer
from ..types import Truth, TruthType

logger = logging.getLogger(__name__)


class RealityGatherer(DuckDBGatherer):
    """
    Gathers Reality truths from DuckDB.
    
    Reality represents what actually exists in the customer's data:
    - Employee records
    - Payroll transactions
    - Time entries
    - Historical data
    
    This gatherer:
    1. Takes a question and analysis context
    2. Generates SQL (via SQL generator)
    3. Executes against DuckDB
    4. Returns Truth objects with full provenance
    """
    
    truth_type = TruthType.REALITY
    
    def __init__(self, project_name: str, project_id: str = None,
                 structured_handler=None, schema: Dict = None,
                 sql_generator=None, pattern_cache=None):
        """
        Initialize Reality gatherer.
        
        Args:
            project_name: Project code
            project_id: Project UUID
            structured_handler: DuckDB handler
            schema: Schema metadata (tables, columns)
            sql_generator: SQL generator instance
            pattern_cache: Optional SQL pattern cache for learning
        """
        super().__init__(project_name, project_id, structured_handler)
        self.schema = schema or {}
        self.sql_generator = sql_generator
        self.pattern_cache = pattern_cache
        
        # Track last executed SQL for provenance
        self.last_executed_sql: Optional[str] = None
        self.last_smart_assumption: Optional[str] = None
    
    def gather(self, question: str, context: Dict[str, Any]) -> List[Truth]:
        """
        Gather Reality truths for the question.
        
        Args:
            question: User's question
            context: Analysis context with domains, tables, filters, etc.
            
        Returns:
            List of Truth objects
        """
        self.log_gather_start(question)
        
        if not self.handler or not self.schema:
            logger.warning("[GATHER-REALITY] No handler or schema available")
            return []
        
        truths = []
        
        try:
            # Generate SQL
            sql_result = self._generate_sql(question, context)
            
            if not sql_result:
                return truths
            
            # Handle clarification requests
            if sql_result.get('query_type') == 'validation_clarification':
                # Store clarification for caller to handle
                context['pending_clarification'] = sql_result.get('clarification')
                logger.warning("[GATHER-REALITY] Validation needs clarification")
                return truths
            
            sql = sql_result.get('sql')
            if not sql:
                return truths
            
            # Store smart assumption if present
            if sql_result.get('smart_assumption'):
                self.last_smart_assumption = sql_result['smart_assumption']
            
            # Execute SQL with retry
            rows = self._execute_with_retry(sql, sql_result, max_attempts=3)
            
            if rows:
                truth = self._create_reality_truth(rows, sql, sql_result)
                truths.append(truth)
                
                # Learn successful pattern
                if self.pattern_cache and sql_result.get('source') == 'llm':
                    self.pattern_cache.learn_pattern(question, sql, success=True)
        
        except Exception as e:
            logger.error(f"[GATHER-REALITY] Error: {e}")
        
        self.log_gather_result(truths)
        return truths
    
    def _generate_sql(self, question: str, context: Dict) -> Optional[Dict]:
        """Generate SQL for the question."""
        # Check cache first
        if self.pattern_cache:
            cached = self.pattern_cache.find_matching_pattern(question)
            if cached and cached.get('sql'):
                logger.warning("[GATHER-REALITY] Cache hit!")
                return {
                    'sql': cached['sql'],
                    'source': 'cache',
                    'query_type': cached.get('query_type', 'list')
                }
        
        # CHECK IF QUERY RESOLVER ALREADY PROVIDED CONTEXT
        resolver = context.get('resolver')
        if resolver and resolver.get('resolved') and resolver.get('sql'):
            logger.warning(f"[GATHER-REALITY] Using QueryResolver context: {resolver.get('explanation')}")
            
            # Log reality context if present
            reality_ctx = resolver.get('reality_context')
            if reality_ctx:
                breakdowns = reality_ctx.get('breakdowns', {})
                logger.warning(f"[GATHER-REALITY] Reality context has {len(breakdowns)} breakdowns")
            
            # Check for workforce snapshot
            structured = resolver.get('structured_output')
            if structured and structured.get('type') == 'workforce_snapshot':
                logger.warning(f"[GATHER-REALITY] Workforce snapshot detected")
            
            return {
                'sql': resolver['sql'],
                'source': 'resolver',
                'query_type': 'count' if 'COUNT' in resolver['sql'].upper() else 'list',
                'table': resolver.get('table_name'),
                'explanation': resolver.get('explanation'),
                'resolution_path': resolver.get('resolution_path'),
                'reality_context': resolver.get('reality_context'),  # v2: Include breakdowns
                'structured_output': resolver.get('structured_output'),  # v3: Workforce snapshot etc.
                'total_count': resolver.get('total_count')  # v5: Real count for LIST queries
            }
        
        # TRY QUERY RESOLVER (if not already tried at engine level)
        if not resolver:
            try:
                from ..query_resolver import QueryResolver
                
                project = context.get('project') or context.get('project_name')
                if project and self.handler:
                    logger.warning(f"[GATHER-REALITY] Trying QueryResolver for project={project}")
                    qr = QueryResolver(self.handler)
                    resolved = qr.resolve(question, project)
                    
                    if resolved.success and resolved.sql:
                        logger.warning(f"[GATHER-REALITY] QueryResolver SUCCESS: {resolved.explanation}")
                        logger.warning(f"[GATHER-REALITY] Resolution path: {resolved.resolution_path}")
                        return {
                            'sql': resolved.sql,
                            'source': 'resolver',
                            'query_type': 'count' if 'COUNT' in resolved.sql.upper() else 'list',
                            'table': resolved.table_name,
                            'explanation': resolved.explanation,
                            'resolution_path': resolved.resolution_path
                        }
                    else:
                        logger.warning(f"[GATHER-REALITY] QueryResolver fallback: {resolved.explanation or 'No match'}")
            except Exception as e:
                logger.warning(f"[GATHER-REALITY] QueryResolver error (falling back): {e}")
                import traceback
                logger.warning(f"[GATHER-REALITY] Traceback: {traceback.format_exc()}")
        
        # FALLBACK: Generate via SQL generator (LLM + TableSelector)
        if self.sql_generator:
            result = self.sql_generator.generate(question, context)
            if result:
                result['source'] = 'llm'
                # Pass through JOIN detection debug if available
                if hasattr(self.sql_generator, '_join_detection_debug'):
                    result['_join_debug'] = self.sql_generator._join_detection_debug
                return result
        
        return None
    
    def _execute_with_retry(self, sql: str, sql_info: Dict, 
                           max_attempts: int = 3) -> List[Dict]:
        """Execute SQL with retry and error fixing."""
        for attempt in range(max_attempts):
            try:
                rows = self.handler.query(sql)
                self.last_executed_sql = sql
                return rows
                
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"[GATHER-REALITY] Attempt {attempt + 1} failed: {error_msg}")
                
                # Try to fix SQL
                if self.sql_generator and attempt < max_attempts - 1:
                    fixed = self.sql_generator.fix_from_error(
                        sql, error_msg, 
                        sql_info.get('all_columns', set())
                    )
                    if fixed and fixed != sql:
                        sql = fixed
                        continue
                break
        
        return []
    
    def _create_reality_truth(self, rows: List[Dict], sql: str, 
                              sql_info: Dict) -> Truth:
        """Create a Truth object from query results."""
        columns = list(rows[0].keys()) if rows else []
        table_name = sql_info.get('table', 'query')
        query_type = sql_info.get('query_type', 'list')
        reality_context = sql_info.get('reality_context')
        structured_output = sql_info.get('structured_output')
        resolution_path = sql_info.get('resolution_path', [])  # Provenance
        explanation = sql_info.get('explanation', '')
        total_count = sql_info.get('total_count')  # v5: Real count for LIST queries
        
        # Get display name from schema
        display_name = self._get_display_name(table_name)
        
        # Use real total_count if available, otherwise use len(rows)
        actual_total = total_count if total_count is not None else len(rows)
        
        # Log what we're creating
        if structured_output and structured_output.get('type') == 'workforce_snapshot':
            logger.warning(f"[GATHER-REALITY] Creating Truth with WORKFORCE SNAPSHOT")
        elif reality_context:
            breakdowns = reality_context.get('breakdowns', {})
            logger.warning(f"[GATHER-REALITY] Creating Truth: "
                          f"query_type={query_type}, rows={len(rows)}, total={actual_total}, "
                          f"breakdowns={list(breakdowns.keys())}")
        else:
            logger.warning(f"[GATHER-REALITY] Creating Truth: "
                          f"query_type={query_type}, rows={len(rows)}, total={actual_total}")
        
        return self.create_truth(
            source_name=display_name,
            content={
                'sql': sql,
                'columns': columns,
                'rows': rows,
                'total': actual_total,  # v5: Use real count, not limited rows
                'rows_returned': len(rows),  # v5: How many rows we're actually returning
                'query_type': query_type,
                'table': table_name,
                'display_name': display_name,
                'is_targeted_query': True,
                'reality_context': reality_context,  # v2: Include breakdowns for synthesis
                'structured_output': structured_output,  # v3: Workforce snapshot etc.
                'resolution_path': resolution_path,  # v4: Provenance - step by step lookups
                'explanation': explanation  # v4: Human readable explanation
            },
            location=f"Query: {sql}",
            confidence=0.98,
            row_count=len(rows),
            column_count=len(columns)
        )
    
    def _get_display_name(self, table_name: str) -> str:
        """Look up display name from schema."""
        if self.schema and self.schema.get('tables'):
            for t in self.schema.get('tables', []):
                if t.get('table_name') == table_name:
                    return t.get('display_name') or table_name
        return table_name
