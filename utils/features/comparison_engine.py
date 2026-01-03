"""
Comparison Engine - Domain-Agnostic Data Comparison
====================================================

Compares any two DuckDB tables and returns structured findings.
Used by Playbooks, Chat, BI, Analytics.

No LLM. Pure SQL. Real results.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timezone
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class ComparisonResult:
    """Result of comparing two data sources."""
    
    # Core findings
    only_in_a: List[Dict[str, Any]]       # Rows in A but not B
    only_in_b: List[Dict[str, Any]]       # Rows in B but not A
    mismatches: List[Dict[str, Any]]      # Rows with value differences
    matches: int                          # Count of matching rows
    
    # Provenance (required)
    source_a: str
    source_b: str
    source_a_rows: int
    source_b_rows: int
    join_keys: List[str]
    compared_columns: List[str]
    project_id: Optional[str]
    comparison_id: str
    executed_at: str
    
    # Summary
    @property
    def summary(self) -> str:
        parts = []
        if self.matches:
            parts.append(f"{self.matches} matched")
        if self.mismatches:
            parts.append(f"{len(self.mismatches)} mismatches")
        if self.only_in_a:
            parts.append(f"{len(self.only_in_a)} only in source A")
        if self.only_in_b:
            parts.append(f"{len(self.only_in_b)} only in source B")
        return ", ".join(parts) if parts else "No differences found"
    
    @property 
    def match_rate(self) -> float:
        total = self.matches + len(self.mismatches) + len(self.only_in_a) + len(self.only_in_b)
        return self.matches / total if total > 0 else 1.0
    
    @property
    def has_differences(self) -> bool:
        return bool(self.mismatches or self.only_in_a or self.only_in_b)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "only_in_a": self.only_in_a,
            "only_in_b": self.only_in_b,
            "mismatches": self.mismatches,
            "matches": self.matches,
            "match_rate": self.match_rate,
            "summary": self.summary,
            "has_differences": self.has_differences,
            "provenance": {
                "source_a": self.source_a,
                "source_b": self.source_b,
                "source_a_rows": self.source_a_rows,
                "source_b_rows": self.source_b_rows,
                "join_keys": self.join_keys,
                "compared_columns": self.compared_columns,
                "project_id": self.project_id,
                "comparison_id": self.comparison_id,
                "executed_at": self.executed_at
            }
        }


class ComparisonEngine:
    """
    Compares two DuckDB tables and returns structured differences.
    
    Features:
    - Auto-detects join keys from common columns
    - Finds rows only in A, only in B, and mismatches
    - Full provenance on all results
    - Works with any table structure (domain-agnostic)
    """
    
    def __init__(self, structured_handler=None):
        """
        Initialize with a StructuredDataHandler instance.
        
        Args:
            structured_handler: Optional handler. If not provided,
                               will import and create one.
        """
        self.handler = structured_handler
        
    def _get_handler(self):
        """Lazy-load handler if not provided."""
        if self.handler is None:
            from utils.structured_data_handler import get_structured_handler
            self.handler = get_structured_handler()
        return self.handler
    
    def _get_table_columns(self, table_name: str) -> List[str]:
        """Get column names for a table."""
        handler = self._get_handler()
        result = handler.query(f"PRAGMA table_info('{table_name}')")
        return [row['name'] for row in result]
    
    def _get_row_count(self, table_name: str) -> int:
        """Get row count for a table."""
        handler = self._get_handler()
        result = handler.query(f"SELECT COUNT(*) as cnt FROM \"{table_name}\"")
        return result[0]['cnt'] if result else 0
    
    def _detect_join_keys(self, cols_a: List[str], cols_b: List[str]) -> List[str]:
        """
        Auto-detect likely join keys from common columns.
        
        Priority:
        1. Columns with 'id', 'code', 'key', 'number' in name
        2. Columns with 'name' in name
        3. First common column as fallback
        """
        common = set(cols_a) & set(cols_b)
        
        # Remove internal columns
        common = {c for c in common if not c.startswith('_')}
        
        if not common:
            return []
        
        # Priority keywords for join keys
        key_patterns = ['_id', 'id_', 'code', 'key', 'number', 'num', 'ein', 'ssn', 'fein']
        name_patterns = ['name', 'description', 'desc']
        
        join_keys = []
        
        # First pass: ID/code columns
        for col in common:
            col_lower = col.lower()
            if any(p in col_lower for p in key_patterns):
                join_keys.append(col)
        
        # Second pass: name columns (if no ID cols found)
        if not join_keys:
            for col in common:
                col_lower = col.lower()
                if any(p in col_lower for p in name_patterns):
                    join_keys.append(col)
        
        # Fallback: first common column
        if not join_keys:
            join_keys = [sorted(common)[0]]
        
        return join_keys
    
    def compare(
        self,
        table_a: str,
        table_b: str,
        join_keys: List[str] = None,
        compare_columns: List[str] = None,
        project_id: str = None,
        limit: int = 100
    ) -> ComparisonResult:
        """
        Compare two tables and return differences.
        
        Args:
            table_a: First table name
            table_b: Second table name
            join_keys: Columns to join on (auto-detected if not provided)
            compare_columns: Columns to compare values (all common if not provided)
            project_id: Project context for provenance
            limit: Max rows to return per category (only_in_a, only_in_b, mismatches)
        
        Returns:
            ComparisonResult with all findings and provenance
        """
        handler = self._get_handler()
        executed_at = datetime.now(timezone.utc).isoformat()
        
        # Generate comparison ID
        comparison_id = hashlib.sha256(
            f"{table_a}:{table_b}:{executed_at}".encode()
        ).hexdigest()[:12]
        
        logger.info(f"[COMPARE] Starting comparison: {table_a} vs {table_b}")
        
        # Get columns for both tables
        cols_a = self._get_table_columns(table_a)
        cols_b = self._get_table_columns(table_b)
        
        logger.warning(f"[COMPARE] Table A columns ({len(cols_a)}): {cols_a}")
        logger.warning(f"[COMPARE] Table B columns ({len(cols_b)}): {cols_b}")
        
        # Auto-detect join keys if not provided
        if not join_keys:
            join_keys = self._detect_join_keys(cols_a, cols_b)
            logger.warning(f"[COMPARE] Auto-detected join keys: {join_keys}")
        
        if not join_keys:
            raise ValueError(f"No common columns found between {table_a} and {table_b}")
        
        # DIAGNOSTIC: Show sample values from join key columns
        for key in join_keys[:2]:
            sample_a = handler.query(f'SELECT DISTINCT "{key}" FROM "{table_a}" LIMIT 5')
            sample_b = handler.query(f'SELECT DISTINCT "{key}" FROM "{table_b}" LIMIT 5')
            logger.warning(f"[COMPARE] Sample {key} values in A: {[r[key] for r in sample_a]}")
            logger.warning(f"[COMPARE] Sample {key} values in B: {[r[key] for r in sample_b]}")
        
        # Determine columns to compare (common columns minus join keys)
        common_cols = set(cols_a) & set(cols_b)
        logger.warning(f"[COMPARE] Common columns: {common_cols}")
        
        if compare_columns:
            compare_columns = [c for c in compare_columns if c in common_cols]
        else:
            compare_columns = [c for c in common_cols if c not in join_keys and not c.startswith('_')]
        
        logger.warning(f"[COMPARE] Comparing {len(compare_columns)} value columns: {compare_columns}")
        
        # Get row counts
        rows_a = self._get_row_count(table_a)
        rows_b = self._get_row_count(table_b)
        logger.warning(f"[COMPARE] Row counts: A={rows_a}, B={rows_b}")
        
        # Build join condition
        join_cond = " AND ".join([f"a.\"{k}\" = b.\"{k}\"" for k in join_keys])
        key_select = ", ".join([f"a.\"{k}\"" for k in join_keys])
        key_select_b = ", ".join([f"b.\"{k}\"" for k in join_keys])
        
        # 1. Find rows only in A (not in B)
        only_in_a_sql = f"""
            SELECT {', '.join([f'a."{c}"' for c in cols_a[:20]])}
            FROM "{table_a}" a
            LEFT JOIN "{table_b}" b ON {join_cond}
            WHERE b."{join_keys[0]}" IS NULL
            LIMIT {limit}
        """
        only_in_a = handler.query(only_in_a_sql)
        logger.warning(f"[COMPARE] Only in A: {len(only_in_a)}")
        
        # 2. Find rows only in B (not in A)
        only_in_b_sql = f"""
            SELECT {', '.join([f'b."{c}"' for c in cols_b[:20]])}
            FROM "{table_b}" b
            LEFT JOIN "{table_a}" a ON {join_cond}
            WHERE a."{join_keys[0]}" IS NULL
            LIMIT {limit}
        """
        only_in_b = handler.query(only_in_b_sql)
        logger.info(f"[COMPARE] Only in B: {len(only_in_b)}")
        
        # 3. Find mismatches (same key, different values)
        mismatches = []
        if compare_columns:
            # Build mismatch condition
            mismatch_conds = []
            for col in compare_columns[:10]:  # Limit to 10 columns for performance
                mismatch_conds.append(
                    f"(a.\"{col}\" IS DISTINCT FROM b.\"{col}\")"
                )
            
            mismatch_where = " OR ".join(mismatch_conds)
            
            # Select key columns plus mismatched values
            select_parts = [f"a.\"{k}\" as key_{k}" for k in join_keys]
            for col in compare_columns[:10]:
                select_parts.append(f"a.\"{col}\" as a_{col}")
                select_parts.append(f"b.\"{col}\" as b_{col}")
            
            mismatch_sql = f"""
                SELECT {', '.join(select_parts)}
                FROM "{table_a}" a
                INNER JOIN "{table_b}" b ON {join_cond}
                WHERE {mismatch_where}
                LIMIT {limit}
            """
            
            raw_mismatches = handler.query(mismatch_sql)
            
            # Format mismatches into readable structure
            for row in raw_mismatches:
                keys = {k: row.get(f"key_{k}") for k in join_keys}
                differences = []
                for col in compare_columns[:10]:
                    a_val = row.get(f"a_{col}")
                    b_val = row.get(f"b_{col}")
                    if a_val != b_val:
                        differences.append({
                            "column": col,
                            "value_a": a_val,
                            "value_b": b_val
                        })
                if differences:
                    mismatches.append({
                        "keys": keys,
                        "differences": differences
                    })
            
            logger.info(f"[COMPARE] Mismatches: {len(mismatches)}")
        
        # 4. Count matches
        match_sql = f"""
            SELECT COUNT(*) as cnt
            FROM "{table_a}" a
            INNER JOIN "{table_b}" b ON {join_cond}
        """
        match_result = handler.query(match_sql)
        matches = match_result[0]['cnt'] if match_result else 0
        
        # Subtract mismatches from match count
        matches = max(0, matches - len(mismatches))
        logger.info(f"[COMPARE] Matches: {matches}")
        
        return ComparisonResult(
            only_in_a=only_in_a,
            only_in_b=only_in_b,
            mismatches=mismatches,
            matches=matches,
            source_a=table_a,
            source_b=table_b,
            source_a_rows=rows_a,
            source_b_rows=rows_b,
            join_keys=join_keys,
            compared_columns=compare_columns,
            project_id=project_id,
            comparison_id=comparison_id,
            executed_at=executed_at
        )


# Module-level instance for convenience
_engine = None

def get_comparison_engine(handler=None) -> ComparisonEngine:
    """Get or create a ComparisonEngine instance."""
    global _engine
    if _engine is None or handler is not None:
        _engine = ComparisonEngine(handler)
    return _engine


def compare(
    table_a: str,
    table_b: str,
    join_keys: List[str] = None,
    compare_columns: List[str] = None,
    project_id: str = None,
    limit: int = 100,
    handler=None
) -> ComparisonResult:
    """
    Convenience function to compare two tables.
    
    Example:
        from utils.features.comparison_engine import compare
        
        result = compare("tax_verification", "master_profile")
        logger.debug(f"Debug output: {result.summary}")
        logger.debug(f"Debug output: {result.mismatches}")
    """
    engine = get_comparison_engine(handler)
    return engine.compare(
        table_a=table_a,
        table_b=table_b,
        join_keys=join_keys,
        compare_columns=compare_columns,
        project_id=project_id,
        limit=limit
    )
