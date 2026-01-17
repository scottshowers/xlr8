"""
XLR8 AGGREGATE ENGINE
=====================

Summarize data by dimensions with measures.

This is a WRAPPER around the existing SQLAssembler.
SQLAssembler is battle-scarred but working - we don't touch its internals.
We just put a clean interface on it.

Capabilities:
- COUNT, SUM, AVG, MIN, MAX
- GROUP BY any dimension
- Multi-table JOINs (via SQLAssembler)
- Filters from term resolution

Author: XLR8 Team
Version: 1.0.0
Date: January 2026
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from enum import Enum

from .base import (
    BaseEngine,
    EngineType,
    EngineResult,
    ResultStatus,
    Finding,
    Severity
)

logger = logging.getLogger(__name__)


# =============================================================================
# IMPORTS - SQLAssembler and TermIndex
# =============================================================================

SQL_ASSEMBLER_AVAILABLE = False
SQLAssembler = None
QueryIntent = None
TermIndex = None

try:
    from backend.utils.intelligence.sql_assembler import (
        SQLAssembler as _SQLAssembler,
        QueryIntent as _QueryIntent
    )
    SQLAssembler = _SQLAssembler
    QueryIntent = _QueryIntent
    SQL_ASSEMBLER_AVAILABLE = True
    logger.info("[AGGREGATE] SQLAssembler loaded from backend.utils.intelligence")
except ImportError:
    try:
        from utils.intelligence.sql_assembler import (
            SQLAssembler as _SQLAssembler,
            QueryIntent as _QueryIntent
        )
        SQLAssembler = _SQLAssembler
        QueryIntent = _QueryIntent
        SQL_ASSEMBLER_AVAILABLE = True
        logger.info("[AGGREGATE] SQLAssembler loaded from utils.intelligence")
    except ImportError as e:
        logger.warning(f"[AGGREGATE] SQLAssembler not available: {e}")

try:
    from backend.utils.intelligence.term_index import TermIndex as _TermIndex
    TermIndex = _TermIndex
    logger.info("[AGGREGATE] TermIndex loaded from backend.utils.intelligence")
except ImportError:
    try:
        from utils.intelligence.term_index import TermIndex as _TermIndex
        TermIndex = _TermIndex
        logger.info("[AGGREGATE] TermIndex loaded from utils.intelligence")
    except ImportError as e:
        logger.warning(f"[AGGREGATE] TermIndex not available: {e}")


# =============================================================================
# AGGREGATE CONFIG TYPES
# =============================================================================

class AggregateFunction(str, Enum):
    """Supported aggregation functions."""
    COUNT = "COUNT"
    SUM = "SUM"
    AVG = "AVG"
    MIN = "MIN"
    MAX = "MAX"


# =============================================================================
# AGGREGATE ENGINE
# =============================================================================

class AggregateEngine(BaseEngine):
    """
    Engine for aggregating data with GROUP BY.
    
    Wraps SQLAssembler - doesn't rewrite its logic.
    
    Config Schema:
    {
        "source_table": "employees",              # Required OR use "question"
        "question": "count employees by state",   # Alternative to explicit config
        
        # Explicit config (used if no question):
        "measures": [
            {"function": "COUNT"},
            {"function": "SUM", "column": "salary"}
        ],
        "dimensions": ["state", "department"],    # GROUP BY columns
        "filters": [                              # Optional WHERE clauses
            {"column": "status", "operator": "=", "value": "A"}
        ],
        "order_by": "count DESC",                 # Optional
        "limit": 100                              # Optional
    }
    
    Two modes:
    1. Question mode: Pass natural language, we resolve via TermIndex
    2. Config mode: Pass explicit measures/dimensions/filters
    """
    
    VERSION = "1.0.0"
    
    @property
    def engine_type(self) -> EngineType:
        return EngineType.AGGREGATE
    
    @property
    def engine_version(self) -> str:
        return self.VERSION
    
    def _validate_config(self, config: Dict) -> List[str]:
        """Validate aggregate configuration."""
        errors = []
        
        if not SQL_ASSEMBLER_AVAILABLE:
            errors.append("SQLAssembler is not available")
            return errors
        
        # Must have either question or source_table
        if not config.get("question") and not config.get("source_table"):
            errors.append("Either 'question' or 'source_table' is required")
        
        # If explicit config, validate measures
        if config.get("measures"):
            for i, measure in enumerate(config["measures"]):
                func = measure.get("function", "").upper()
                if func not in [f.value for f in AggregateFunction]:
                    errors.append(f"Measure {i}: Invalid function '{func}'")
                
                # SUM/AVG/MIN/MAX require a column
                if func in ["SUM", "AVG", "MIN", "MAX"] and not measure.get("column"):
                    errors.append(f"Measure {i}: {func} requires a 'column'")
        
        # Validate source table exists if specified
        if config.get("source_table"):
            if not self._table_exists(config["source_table"]):
                errors.append(f"Table '{config['source_table']}' does not exist")
        
        return errors
    
    def _table_exists(self, table_name: str) -> bool:
        """Check if a table exists."""
        try:
            self.conn.execute(f"SELECT 1 FROM \"{table_name}\" LIMIT 1")
            return True
        except:
            return False
    
    def _execute(self, config: Dict) -> EngineResult:
        """Execute the aggregation."""
        
        # Determine mode
        if config.get("question"):
            return self._execute_question_mode(config)
        else:
            return self._execute_config_mode(config)
    
    def _execute_question_mode(self, config: Dict) -> EngineResult:
        """
        Execute using natural language question.
        Uses TermIndex + SQLAssembler (existing flow).
        """
        question = config["question"]
        logger.info(f"[AGGREGATE] Question mode: {question[:80]}...")
        
        if not TermIndex:
            return self._error_result(
                execution_id="",
                config_hash="",
                error="TermIndex not available for question mode"
            )
        
        # Get term index and resolve terms
        term_index = TermIndex(self.conn, self.project)
        
        # Tokenize question (simple split for now)
        tokens = question.lower().split()
        
        # Resolve terms
        term_matches = term_index.resolve_terms_enhanced(
            tokens, 
            detect_numeric=True,
            full_question=question
        )
        
        logger.info(f"[AGGREGATE] Resolved {len(term_matches)} term matches")
        
        # Detect GROUP BY from question
        group_by_column = self._detect_group_by(question)
        
        # Detect intent
        intent = self._detect_intent(question)
        
        # Build SQL via SQLAssembler
        assembler = SQLAssembler(self.conn, self.project)
        
        try:
            result = assembler.assemble(
                intent=intent,
                term_matches=term_matches,
                group_by_column=group_by_column
            )
        except Exception as e:
            logger.error(f"[AGGREGATE] SQLAssembler error: {e}")
            return self._error_result(
                execution_id="",
                config_hash="",
                error=f"SQL assembly failed: {e}"
            )
        
        if not result or not result.get("sql"):
            return self._error_result(
                execution_id="",
                config_hash="",
                error="SQLAssembler returned no SQL"
            )
        
        # Execute SQL
        sql = result["sql"]
        logger.info(f"[AGGREGATE] Executing: {sql[:200]}...")
        
        try:
            data = self._query(sql)
        except Exception as e:
            return self._error_result(
                execution_id="",
                config_hash="",
                error=f"SQL execution failed: {e}"
            )
        
        # Determine columns
        columns = list(data[0].keys()) if data else []
        
        return EngineResult(
            status=ResultStatus.SUCCESS if data else ResultStatus.NO_DATA,
            data=data,
            row_count=len(data),
            columns=columns,
            provenance=self._create_provenance(
                execution_id="",
                config_hash="",
                source_tables=[result.get("primary_table", "unknown")],
                sql_executed=[sql],
                warnings=result.get("warnings", [])
            ),
            sql=sql,
            summary=f"{len(data)} rows returned" if data else "No data found",
            metadata={
                "intent": intent.value if hasattr(intent, 'value') else str(intent),
                "primary_table": result.get("primary_table"),
                "term_matches": len(term_matches),
                "group_by": group_by_column
            }
        )
    
    def _execute_config_mode(self, config: Dict) -> EngineResult:
        """
        Execute using explicit configuration.
        Builds SQL directly without TermIndex.
        """
        source_table = config["source_table"]
        measures = config.get("measures", [{"function": "COUNT"}])
        dimensions = config.get("dimensions", [])
        filters = config.get("filters", [])
        order_by = config.get("order_by")
        limit = config.get("limit", 1000)
        
        logger.info(f"[AGGREGATE] Config mode: {source_table}, "
                   f"{len(measures)} measures, {len(dimensions)} dimensions")
        
        # Build SQL
        sql = self._build_sql(source_table, measures, dimensions, filters, order_by, limit)
        
        logger.info(f"[AGGREGATE] Executing: {sql[:200]}...")
        
        try:
            data = self._query(sql)
        except Exception as e:
            return self._error_result(
                execution_id="",
                config_hash="",
                error=f"SQL execution failed: {e}"
            )
        
        columns = list(data[0].keys()) if data else []
        
        return EngineResult(
            status=ResultStatus.SUCCESS if data else ResultStatus.NO_DATA,
            data=data,
            row_count=len(data),
            columns=columns,
            provenance=self._create_provenance(
                execution_id="",
                config_hash="",
                source_tables=[source_table],
                sql_executed=[sql]
            ),
            sql=sql,
            summary=f"{len(data)} rows returned" if data else "No data found",
            metadata={
                "mode": "config",
                "measures": measures,
                "dimensions": dimensions
            }
        )
    
    def _build_sql(self,
                   source_table: str,
                   measures: List[Dict],
                   dimensions: List[str],
                   filters: List[Dict],
                   order_by: Optional[str],
                   limit: int) -> str:
        """Build SQL from explicit config."""
        
        # SELECT clause
        select_parts = []
        
        # Add dimensions
        for dim in dimensions:
            select_parts.append(f'"{dim}"')
        
        # Add measures
        for measure in measures:
            func = measure["function"].upper()
            col = measure.get("column")
            alias = measure.get("alias", func.lower())
            
            if func == "COUNT":
                if col:
                    select_parts.append(f'COUNT("{col}") as {alias}')
                else:
                    select_parts.append(f'COUNT(*) as {alias}')
            else:
                select_parts.append(f'{func}("{col}") as {alias}')
        
        sql = f'SELECT {", ".join(select_parts)}'
        sql += f'\nFROM "{source_table}"'
        
        # WHERE clause
        if filters:
            where_parts = []
            for f in filters:
                col = f["column"]
                op = f.get("operator", "=")
                val = f["value"]
                
                if isinstance(val, str):
                    where_parts.append(f'"{col}" {op} \'{val}\'')
                else:
                    where_parts.append(f'"{col}" {op} {val}')
            
            sql += f'\nWHERE {" AND ".join(where_parts)}'
        
        # GROUP BY clause
        if dimensions:
            dim_cols = ", ".join([f'"{d}"' for d in dimensions])
            sql += f'\nGROUP BY {dim_cols}'
        
        # ORDER BY clause
        if order_by:
            sql += f'\nORDER BY {order_by}'
        elif dimensions:
            # Default: order by first measure descending
            first_measure = measures[0]
            alias = first_measure.get("alias", first_measure["function"].lower())
            sql += f'\nORDER BY {alias} DESC'
        
        # LIMIT
        sql += f'\nLIMIT {limit}'
        
        return sql
    
    def _detect_group_by(self, question: str) -> Optional[str]:
        """Detect GROUP BY column from question."""
        q_lower = question.lower()
        
        # Pattern: "by <dimension>"
        patterns = [
            (' by ', ['state', 'department', 'location', 'company', 'status', 
                      'job', 'pay', 'type', 'code', 'category', 'group', 'division',
                      'region', 'country', 'city', 'manager', 'supervisor']),
            (' per ', ['state', 'department', 'location', 'company', 'employee']),
            (' for each ', ['state', 'department', 'location', 'company']),
        ]
        
        for keyword, dimensions in patterns:
            if keyword in q_lower:
                # Find what comes after the keyword
                idx = q_lower.find(keyword) + len(keyword)
                rest = q_lower[idx:].split()[0] if idx < len(q_lower) else ""
                
                # Check if it matches a known dimension
                for dim in dimensions:
                    if rest.startswith(dim) or dim in rest:
                        return rest.rstrip('s')  # Remove trailing 's'
        
        return None
    
    def _detect_intent(self, question: str) -> 'QueryIntent':
        """Detect query intent from question."""
        q_lower = question.lower()
        
        # Check for aggregation keywords
        if any(kw in q_lower for kw in ['sum', 'total']):
            return QueryIntent.SUM
        elif any(kw in q_lower for kw in ['average', 'avg', 'mean']):
            return QueryIntent.AVG
        elif any(kw in q_lower for kw in ['minimum', 'min', 'lowest']):
            return QueryIntent.MIN
        elif any(kw in q_lower for kw in ['maximum', 'max', 'highest']):
            return QueryIntent.MAX
        elif any(kw in q_lower for kw in ['count', 'how many', 'number of']):
            return QueryIntent.COUNT
        elif any(kw in q_lower for kw in ['list', 'show', 'get', 'find', 'who']):
            return QueryIntent.LIST
        
        # Default to COUNT for "by" questions
        if ' by ' in q_lower:
            return QueryIntent.COUNT
        
        return QueryIntent.LIST


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def aggregate(conn,
             project: str,
             source_table: str = None,
             question: str = None,
             measures: List[Dict] = None,
             dimensions: List[str] = None,
             filters: List[Dict] = None,
             order_by: str = None,
             limit: int = 1000) -> EngineResult:
    """
    Convenience function to run an aggregation.
    
    Use EITHER question OR explicit config (source_table + measures + dimensions).
    
    Args:
        conn: DuckDB connection
        project: Project ID
        source_table: Table to aggregate (config mode)
        question: Natural language question (question mode)
        measures: List of {"function": "COUNT|SUM|AVG|MIN|MAX", "column": "col_name"}
        dimensions: List of GROUP BY columns
        filters: List of {"column": "col", "operator": "=", "value": "val"}
        order_by: ORDER BY clause
        limit: Max rows
        
    Returns:
        EngineResult with aggregated data
    """
    engine = AggregateEngine(conn, project)
    
    config = {}
    
    if question:
        config["question"] = question
    else:
        config["source_table"] = source_table
        config["measures"] = measures or [{"function": "COUNT"}]
        config["dimensions"] = dimensions or []
        config["filters"] = filters or []
        if order_by:
            config["order_by"] = order_by
        config["limit"] = limit
    
    return engine.execute(config)
