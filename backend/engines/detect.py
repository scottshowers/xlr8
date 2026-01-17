"""
XLR8 DETECT ENGINE
==================

Find patterns in data: duplicates, orphans, outliers, anomalies.

This wraps detection logic from ProjectIntelligence.
We don't rewrite working code - we standardize the interface.

Capabilities:
- Duplicate detection (same value in key columns)
- Orphan detection (FK with no parent)
- Outlier detection (values outside statistical norms)
- Anomaly detection (business rule violations)
- Pattern matching (regex, date logic)

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
    Severity,
    generate_finding_id
)

logger = logging.getLogger(__name__)


class DetectionType(str, Enum):
    """Types of detection patterns."""
    DUPLICATE = "duplicate"
    ORPHAN = "orphan"
    OUTLIER = "outlier"
    ANOMALY = "anomaly"
    PATTERN = "pattern"


class DetectEngine(BaseEngine):
    """
    Engine for detecting patterns in data.
    
    Config Schema:
    {
        "source_table": "employees",
        "patterns": [
            {"type": "duplicate", "columns": ["ssn"]},
            {"type": "orphan", "column": "dept_code", "parent_table": "departments", "parent_column": "code"},
            {"type": "outlier", "column": "salary", "method": "zscore", "threshold": 3},
            {"type": "anomaly", "rule": "status = 'T' AND term_date IS NULL", "message": "Terminated without term date"}
        ],
        "sample_limit": 10
    }
    """
    
    VERSION = "1.0.0"
    
    @property
    def engine_type(self) -> EngineType:
        return EngineType.DETECT
    
    @property
    def engine_version(self) -> str:
        return self.VERSION
    
    def _validate_config(self, config: Dict) -> List[str]:
        errors = []
        
        if not config.get("source_table"):
            errors.append("'source_table' is required")
        
        if not config.get("patterns"):
            errors.append("'patterns' is required")
        
        for i, p in enumerate(config.get("patterns", [])):
            if not p.get("type"):
                errors.append(f"Pattern {i}: 'type' is required")
            elif p["type"] == "duplicate" and not p.get("columns"):
                errors.append(f"Pattern {i}: 'columns' required for duplicate")
            elif p["type"] == "orphan" and not all(k in p for k in ["column", "parent_table", "parent_column"]):
                errors.append(f"Pattern {i}: orphan requires column, parent_table, parent_column")
            elif p["type"] == "outlier" and not p.get("column"):
                errors.append(f"Pattern {i}: 'column' required for outlier")
            elif p["type"] == "anomaly" and not p.get("rule"):
                errors.append(f"Pattern {i}: 'rule' required for anomaly")
        
        if config.get("source_table") and not self._table_exists(config["source_table"]):
            errors.append(f"Table '{config['source_table']}' does not exist")
        
        return errors
    
    def _table_exists(self, table_name: str) -> bool:
        try:
            self.conn.execute(f"SELECT 1 FROM \"{table_name}\" LIMIT 1")
            return True
        except:
            return False
    
    def _execute(self, config: Dict) -> EngineResult:
        source_table = config["source_table"]
        patterns = config["patterns"]
        sample_limit = config.get("sample_limit", 10)
        
        logger.info(f"[DETECT] Scanning {source_table} with {len(patterns)} patterns")
        
        findings = []
        all_detections = []
        sql_executed = []
        
        for pattern in patterns:
            result = self._detect_pattern(source_table, pattern, sample_limit)
            sql_executed.extend(result.get("sql", []))
            
            if result["matches"]:
                findings.append(Finding(
                    finding_id=generate_finding_id(f"detect_{pattern['type']}", source_table),
                    finding_type=f"detect_{pattern['type']}",
                    severity=self._get_severity(pattern, result["match_count"]),
                    message=result["message"],
                    affected_records=result["match_count"],
                    evidence=result["matches"][:sample_limit],
                    details={"pattern": pattern}
                ))
                all_detections.extend(result["matches"][:sample_limit])
        
        status = ResultStatus.SUCCESS if not findings else ResultStatus.PARTIAL
        summary = f"Found {len(findings)} issues" if findings else "No issues detected"
        
        return EngineResult(
            status=status,
            data=all_detections,
            row_count=len(all_detections),
            columns=list(all_detections[0].keys()) if all_detections else [],
            provenance=self._create_provenance(
                execution_id="", config_hash="",
                source_tables=[source_table],
                sql_executed=sql_executed
            ),
            findings=findings,
            summary=summary,
            metadata={"patterns_checked": len(patterns), "patterns_matched": len(findings)}
        )
    
    def _get_severity(self, pattern: Dict, count: int) -> Severity:
        if pattern.get("severity"):
            return Severity(pattern["severity"])
        if pattern["type"] == "duplicate" and any(k in str(pattern.get("columns", [])).lower() for k in ["ssn", "ein", "id"]):
            return Severity.ERROR
        if pattern["type"] == "orphan":
            return Severity.ERROR
        if pattern["type"] == "anomaly":
            return Severity.ERROR
        return Severity.WARNING
    
    def _detect_pattern(self, table: str, pattern: Dict, limit: int) -> Dict:
        p_type = pattern["type"]
        
        if p_type == "duplicate":
            return self._detect_duplicates(table, pattern, limit)
        elif p_type == "orphan":
            return self._detect_orphans(table, pattern, limit)
        elif p_type == "outlier":
            return self._detect_outliers(table, pattern, limit)
        elif p_type == "anomaly":
            return self._detect_anomaly(table, pattern, limit)
        elif p_type == "pattern":
            return self._detect_regex(table, pattern, limit)
        
        return {"matches": [], "match_count": 0, "message": f"Unknown: {p_type}", "sql": []}
    
    def _detect_duplicates(self, table: str, pattern: Dict, limit: int) -> Dict:
        columns = pattern["columns"]
        cols_str = ", ".join([f'"{c}"' for c in columns])
        
        sql = f'''
            SELECT {cols_str}, COUNT(*) as duplicate_count
            FROM "{table}"
            WHERE {" AND ".join([f'"{c}" IS NOT NULL' for c in columns])}
            GROUP BY {cols_str}
            HAVING COUNT(*) > 1
            ORDER BY COUNT(*) DESC
            LIMIT {limit}
        '''
        
        count_sql = f'''
            SELECT SUM(cnt) as total FROM (
                SELECT COUNT(*) as cnt FROM "{table}"
                WHERE {" AND ".join([f'"{c}" IS NOT NULL' for c in columns])}
                GROUP BY {cols_str} HAVING COUNT(*) > 1
            )
        '''
        
        try:
            matches = self._query(sql)
            count_result = self._query(count_sql)
            count = int(count_result[0]["total"] or 0) if count_result else 0
            
            return {
                "matches": matches,
                "match_count": count,
                "message": f"{count} duplicate records on {columns}",
                "sql": [sql]
            }
        except Exception as e:
            logger.error(f"[DETECT] Duplicate error: {e}")
            return {"matches": [], "match_count": 0, "message": str(e), "sql": [sql]}
    
    def _detect_orphans(self, table: str, pattern: Dict, limit: int) -> Dict:
        column = pattern["column"]
        parent_table = pattern["parent_table"]
        parent_column = pattern["parent_column"]
        
        sql = f'''
            SELECT t."{column}", t.*
            FROM "{table}" t
            LEFT JOIN "{parent_table}" p ON t."{column}" = p."{parent_column}"
            WHERE t."{column}" IS NOT NULL AND p."{parent_column}" IS NULL
            LIMIT {limit}
        '''
        
        count_sql = f'''
            SELECT COUNT(*) as cnt FROM "{table}" t
            LEFT JOIN "{parent_table}" p ON t."{column}" = p."{parent_column}"
            WHERE t."{column}" IS NOT NULL AND p."{parent_column}" IS NULL
        '''
        
        try:
            matches = self._query(sql)
            count_result = self._query(count_sql)
            count = count_result[0]["cnt"] if count_result else 0
            
            return {
                "matches": matches,
                "match_count": count,
                "message": f"{count} orphan records in {column}",
                "sql": [sql]
            }
        except Exception as e:
            logger.error(f"[DETECT] Orphan error: {e}")
            return {"matches": [], "match_count": 0, "message": str(e), "sql": [sql]}
    
    def _detect_outliers(self, table: str, pattern: Dict, limit: int) -> Dict:
        column = pattern["column"]
        method = pattern.get("method", "zscore")
        threshold = pattern.get("threshold", 3)
        
        if method == "zscore":
            sql = f'''
                WITH stats AS (
                    SELECT AVG("{column}") as mean_val, STDDEV("{column}") as std_val
                    FROM "{table}" WHERE "{column}" IS NOT NULL
                )
                SELECT t.*, ABS((t."{column}" - s.mean_val) / NULLIF(s.std_val, 0)) as zscore
                FROM "{table}" t, stats s
                WHERE "{column}" IS NOT NULL
                AND ABS((t."{column}" - s.mean_val) / NULLIF(s.std_val, 0)) > {threshold}
                ORDER BY zscore DESC
                LIMIT {limit}
            '''
        else:  # IQR
            sql = f'''
                WITH q AS (
                    SELECT PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY "{column}") as q1,
                           PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY "{column}") as q3
                    FROM "{table}" WHERE "{column}" IS NOT NULL
                )
                SELECT t.* FROM "{table}" t, q
                WHERE "{column}" IS NOT NULL
                AND (t."{column}" < q.q1 - {threshold}*(q.q3-q.q1) OR t."{column}" > q.q3 + {threshold}*(q.q3-q.q1))
                LIMIT {limit}
            '''
        
        try:
            matches = self._query(sql)
            return {
                "matches": matches,
                "match_count": len(matches),
                "message": f"{len(matches)} outliers in {column} ({method})",
                "sql": [sql]
            }
        except Exception as e:
            logger.error(f"[DETECT] Outlier error: {e}")
            return {"matches": [], "match_count": 0, "message": str(e), "sql": [sql]}
    
    def _detect_anomaly(self, table: str, pattern: Dict, limit: int) -> Dict:
        rule = pattern["rule"]
        message = pattern.get("message", f"Anomaly: {rule}")
        
        sql = f'SELECT * FROM "{table}" WHERE {rule} LIMIT {limit}'
        count_sql = f'SELECT COUNT(*) as cnt FROM "{table}" WHERE {rule}'
        
        try:
            matches = self._query(sql)
            count_result = self._query(count_sql)
            count = count_result[0]["cnt"] if count_result else 0
            
            return {
                "matches": matches,
                "match_count": count,
                "message": f"{count} records: {message}",
                "sql": [sql]
            }
        except Exception as e:
            logger.error(f"[DETECT] Anomaly error: {e}")
            return {"matches": [], "match_count": 0, "message": str(e), "sql": [sql]}
    
    def _detect_regex(self, table: str, pattern: Dict, limit: int) -> Dict:
        column = pattern["column"]
        regex = pattern["pattern"]
        
        sql = f'''
            SELECT * FROM "{table}"
            WHERE "{column}" IS NOT NULL AND regexp_matches("{column}"::VARCHAR, '{regex}')
            LIMIT {limit}
        '''
        
        try:
            matches = self._query(sql)
            return {
                "matches": matches,
                "match_count": len(matches),
                "message": f"{len(matches)} pattern matches in {column}",
                "sql": [sql]
            }
        except Exception as e:
            logger.error(f"[DETECT] Regex error: {e}")
            return {"matches": [], "match_count": 0, "message": str(e), "sql": [sql]}


def detect(conn, project: str, source_table: str, patterns: List[Dict], sample_limit: int = 10) -> EngineResult:
    """Convenience function to run detection."""
    engine = DetectEngine(conn, project)
    return engine.execute({
        "source_table": source_table,
        "patterns": patterns,
        "sample_limit": sample_limit
    })
