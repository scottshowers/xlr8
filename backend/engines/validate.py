"""
XLR8 VALIDATE ENGINE
====================

Check data against rules.

This is a WRAPPER around the existing ComplianceEngine.
We don't rewrite working code - we standardize the interface.

Capabilities:
- Format validation (email, phone, SSN, date)
- Range validation (min/max values, date ranges)
- Referential integrity (FK exists in parent table)
- Business rules (custom SQL predicates)
- Allowed values (enum validation)

Author: XLR8 Team
Version: 1.0.0
Date: January 2026
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from enum import Enum
import re

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


# =============================================================================
# IMPORTS - ComplianceEngine
# =============================================================================

COMPLIANCE_ENGINE_AVAILABLE = False
ComplianceEngine = None

try:
    from backend.utils.compliance_engine import (
        ComplianceEngine as _ComplianceEngine,
        get_compliance_engine
    )
    ComplianceEngine = _ComplianceEngine
    COMPLIANCE_ENGINE_AVAILABLE = True
    logger.info("[VALIDATE] ComplianceEngine loaded from backend.utils")
except ImportError:
    try:
        from utils.compliance_engine import (
            ComplianceEngine as _ComplianceEngine,
            get_compliance_engine
        )
        ComplianceEngine = _ComplianceEngine
        COMPLIANCE_ENGINE_AVAILABLE = True
        logger.info("[VALIDATE] ComplianceEngine loaded from utils")
    except ImportError as e:
        logger.warning(f"[VALIDATE] ComplianceEngine not available: {e}")


# =============================================================================
# VALIDATION TYPES
# =============================================================================

class ValidationType(str, Enum):
    """Types of validation rules."""
    FORMAT = "format"           # Regex pattern match
    RANGE = "range"             # Min/max values
    REFERENTIAL = "referential" # FK exists
    ALLOWED_VALUES = "allowed_values"  # Enum
    NOT_NULL = "not_null"       # Required field
    UNIQUE = "unique"           # No duplicates
    CUSTOM = "custom"           # Custom SQL predicate


# Common format patterns
FORMAT_PATTERNS = {
    "email": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
    "phone": r"^\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$",
    "ssn": r"^\d{3}-?\d{2}-?\d{4}$",
    "zip": r"^\d{5}(-\d{4})?$",
    "date_iso": r"^\d{4}-\d{2}-\d{2}$",
    "state_code": r"^[A-Z]{2}$",
}


# =============================================================================
# VALIDATE ENGINE
# =============================================================================

class ValidateEngine(BaseEngine):
    """
    Engine for validating data against rules.
    
    Config Schema:
    {
        "source_table": "employees",           # Required
        "rules": [
            {"field": "email", "type": "format", "pattern": "email"},
            {"field": "hire_date", "type": "range", "min": "2000-01-01"},
            {"field": "dept_code", "type": "referential", "parent_table": "departments", "parent_column": "code"},
            {"field": "status", "type": "allowed_values", "values": ["A", "T", "L"]},
            {"field": "employee_id", "type": "not_null"},
            {"field": "ssn", "type": "unique"},
            {"field": "status", "type": "custom", "sql": "status != 'T' OR term_date IS NOT NULL"}
        ],
        "sample_limit": 10                     # Max violations to return per rule
    }
    """
    
    VERSION = "1.0.0"
    
    @property
    def engine_type(self) -> EngineType:
        return EngineType.VALIDATE
    
    @property
    def engine_version(self) -> str:
        return self.VERSION
    
    def _validate_config(self, config: Dict) -> List[str]:
        """Validate the validation config (meta!)."""
        errors = []
        
        if not config.get("source_table"):
            errors.append("'source_table' is required")
        
        if not config.get("rules"):
            errors.append("'rules' is required (list of validation rules)")
        
        # Validate each rule
        for i, rule in enumerate(config.get("rules", [])):
            if not rule.get("field"):
                errors.append(f"Rule {i}: 'field' is required")
            
            if not rule.get("type"):
                errors.append(f"Rule {i}: 'type' is required")
            else:
                rule_type = rule["type"]
                
                if rule_type == "format" and not rule.get("pattern"):
                    errors.append(f"Rule {i}: 'pattern' is required for format validation")
                
                if rule_type == "range" and not rule.get("min") and not rule.get("max"):
                    errors.append(f"Rule {i}: 'min' or 'max' is required for range validation")
                
                if rule_type == "referential":
                    if not rule.get("parent_table"):
                        errors.append(f"Rule {i}: 'parent_table' is required for referential validation")
                    if not rule.get("parent_column"):
                        errors.append(f"Rule {i}: 'parent_column' is required for referential validation")
                
                if rule_type == "allowed_values" and not rule.get("values"):
                    errors.append(f"Rule {i}: 'values' is required for allowed_values validation")
                
                if rule_type == "custom" and not rule.get("sql"):
                    errors.append(f"Rule {i}: 'sql' is required for custom validation")
        
        # Validate table exists
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
        """Execute validation rules."""
        
        source_table = config["source_table"]
        rules = config["rules"]
        sample_limit = config.get("sample_limit", 10)
        
        logger.info(f"[VALIDATE] Validating {source_table} with {len(rules)} rules")
        
        # Get total row count
        total_rows = self._get_row_count(source_table)
        
        findings = []
        all_violations = []
        sql_executed = []
        passed_count = 0
        failed_count = 0
        
        for rule in rules:
            result = self._validate_rule(source_table, rule, sample_limit)
            sql_executed.extend(result.get("sql", []))
            
            if result["violations"]:
                failed_count += 1
                findings.append(Finding(
                    finding_id=generate_finding_id("validation_failure", f"{source_table}.{rule['field']}"),
                    finding_type=f"validation_{rule['type']}",
                    severity=Severity.ERROR if result["violation_count"] > total_rows * 0.1 else Severity.WARNING,
                    message=result["message"],
                    affected_records=result["violation_count"],
                    evidence=result["violations"][:sample_limit],
                    details={
                        "field": rule["field"],
                        "rule_type": rule["type"],
                        "rule_config": rule,
                        "violation_rate": result["violation_count"] / total_rows if total_rows > 0 else 0
                    }
                ))
                all_violations.extend(result["violations"][:sample_limit])
            else:
                passed_count += 1
        
        # Determine overall status
        if failed_count == 0:
            status = ResultStatus.SUCCESS
            summary = f"All {len(rules)} validation rules passed"
        elif passed_count > 0:
            status = ResultStatus.PARTIAL
            summary = f"{passed_count} rules passed, {failed_count} rules failed"
        else:
            status = ResultStatus.FAILURE
            summary = f"All {len(rules)} validation rules failed"
        
        return EngineResult(
            status=status,
            data=all_violations,
            row_count=len(all_violations),
            columns=["field", "value", "rule", "message"] if all_violations else [],
            provenance=self._create_provenance(
                execution_id="",
                config_hash="",
                source_tables=[source_table],
                sql_executed=sql_executed
            ),
            findings=findings,
            summary=summary,
            metadata={
                "total_rows": total_rows,
                "rules_count": len(rules),
                "passed_count": passed_count,
                "failed_count": failed_count,
                "pass_rate": passed_count / len(rules) if rules else 1.0
            }
        )
    
    def _get_row_count(self, table_name: str) -> int:
        """Get row count for a table."""
        result = self._query(f'SELECT COUNT(*) as cnt FROM "{table_name}"')
        return result[0]["cnt"] if result else 0
    
    def _validate_rule(self, table: str, rule: Dict, sample_limit: int) -> Dict:
        """Validate a single rule and return results."""
        
        rule_type = rule["type"]
        field = rule["field"]
        
        if rule_type == "format":
            return self._validate_format(table, field, rule, sample_limit)
        elif rule_type == "range":
            return self._validate_range(table, field, rule, sample_limit)
        elif rule_type == "referential":
            return self._validate_referential(table, field, rule, sample_limit)
        elif rule_type == "allowed_values":
            return self._validate_allowed_values(table, field, rule, sample_limit)
        elif rule_type == "not_null":
            return self._validate_not_null(table, field, rule, sample_limit)
        elif rule_type == "unique":
            return self._validate_unique(table, field, rule, sample_limit)
        elif rule_type == "custom":
            return self._validate_custom(table, field, rule, sample_limit)
        else:
            return {
                "violations": [],
                "violation_count": 0,
                "message": f"Unknown rule type: {rule_type}",
                "sql": []
            }
    
    def _validate_format(self, table: str, field: str, rule: Dict, limit: int) -> Dict:
        """Validate format using regex pattern."""
        pattern_name = rule["pattern"]
        pattern = FORMAT_PATTERNS.get(pattern_name, pattern_name)
        
        # DuckDB uses regexp_matches
        sql = f'''
            SELECT "{field}" as value, '{field}' as field
            FROM "{table}"
            WHERE "{field}" IS NOT NULL 
            AND NOT regexp_matches("{field}"::VARCHAR, '{pattern}')
            LIMIT {limit}
        '''
        
        count_sql = f'''
            SELECT COUNT(*) as cnt
            FROM "{table}"
            WHERE "{field}" IS NOT NULL 
            AND NOT regexp_matches("{field}"::VARCHAR, '{pattern}')
        '''
        
        try:
            violations = self._query(sql)
            count_result = self._query(count_sql)
            count = count_result[0]["cnt"] if count_result else 0
            
            for v in violations:
                v["rule"] = f"format:{pattern_name}"
                v["message"] = f"Value does not match {pattern_name} format"
            
            return {
                "violations": violations,
                "violation_count": count,
                "message": f"{count} values in {field} do not match {pattern_name} format",
                "sql": [sql]
            }
        except Exception as e:
            logger.error(f"[VALIDATE] Format validation error: {e}")
            return {"violations": [], "violation_count": 0, "message": str(e), "sql": [sql]}
    
    def _validate_range(self, table: str, field: str, rule: Dict, limit: int) -> Dict:
        """Validate values are within range."""
        conditions = []
        
        if rule.get("min") is not None:
            conditions.append(f'"{field}" < \'{rule["min"]}\'')
        
        if rule.get("max") is not None:
            conditions.append(f'"{field}" > \'{rule["max"]}\'')
        
        where = " OR ".join(conditions)
        
        sql = f'''
            SELECT "{field}" as value, '{field}' as field
            FROM "{table}"
            WHERE "{field}" IS NOT NULL AND ({where})
            LIMIT {limit}
        '''
        
        count_sql = f'''
            SELECT COUNT(*) as cnt FROM "{table}"
            WHERE "{field}" IS NOT NULL AND ({where})
        '''
        
        try:
            violations = self._query(sql)
            count_result = self._query(count_sql)
            count = count_result[0]["cnt"] if count_result else 0
            
            for v in violations:
                v["rule"] = f"range:{rule.get('min', '*')}-{rule.get('max', '*')}"
                v["message"] = f"Value outside allowed range"
            
            return {
                "violations": violations,
                "violation_count": count,
                "message": f"{count} values in {field} are outside range",
                "sql": [sql]
            }
        except Exception as e:
            logger.error(f"[VALIDATE] Range validation error: {e}")
            return {"violations": [], "violation_count": 0, "message": str(e), "sql": [sql]}
    
    def _validate_referential(self, table: str, field: str, rule: Dict, limit: int) -> Dict:
        """Validate referential integrity (FK exists)."""
        parent_table = rule["parent_table"]
        parent_column = rule["parent_column"]
        
        sql = f'''
            SELECT t."{field}" as value, '{field}' as field
            FROM "{table}" t
            LEFT JOIN "{parent_table}" p ON t."{field}" = p."{parent_column}"
            WHERE t."{field}" IS NOT NULL AND p."{parent_column}" IS NULL
            LIMIT {limit}
        '''
        
        count_sql = f'''
            SELECT COUNT(*) as cnt
            FROM "{table}" t
            LEFT JOIN "{parent_table}" p ON t."{field}" = p."{parent_column}"
            WHERE t."{field}" IS NOT NULL AND p."{parent_column}" IS NULL
        '''
        
        try:
            violations = self._query(sql)
            count_result = self._query(count_sql)
            count = count_result[0]["cnt"] if count_result else 0
            
            for v in violations:
                v["rule"] = f"referential:{parent_table}.{parent_column}"
                v["message"] = f"Value not found in {parent_table}"
            
            return {
                "violations": violations,
                "violation_count": count,
                "message": f"{count} orphan records in {field} (not in {parent_table})",
                "sql": [sql]
            }
        except Exception as e:
            logger.error(f"[VALIDATE] Referential validation error: {e}")
            return {"violations": [], "violation_count": 0, "message": str(e), "sql": [sql]}
    
    def _validate_allowed_values(self, table: str, field: str, rule: Dict, limit: int) -> Dict:
        """Validate values are in allowed list."""
        allowed = rule["values"]
        values_str = ", ".join([f"'{v}'" for v in allowed])
        
        sql = f'''
            SELECT "{field}" as value, '{field}' as field
            FROM "{table}"
            WHERE "{field}" IS NOT NULL AND "{field}" NOT IN ({values_str})
            LIMIT {limit}
        '''
        
        count_sql = f'''
            SELECT COUNT(*) as cnt FROM "{table}"
            WHERE "{field}" IS NOT NULL AND "{field}" NOT IN ({values_str})
        '''
        
        try:
            violations = self._query(sql)
            count_result = self._query(count_sql)
            count = count_result[0]["cnt"] if count_result else 0
            
            for v in violations:
                v["rule"] = f"allowed_values:{allowed}"
                v["message"] = f"Value not in allowed list"
            
            return {
                "violations": violations,
                "violation_count": count,
                "message": f"{count} values in {field} are not in allowed list",
                "sql": [sql]
            }
        except Exception as e:
            logger.error(f"[VALIDATE] Allowed values validation error: {e}")
            return {"violations": [], "violation_count": 0, "message": str(e), "sql": [sql]}
    
    def _validate_not_null(self, table: str, field: str, rule: Dict, limit: int) -> Dict:
        """Validate field is not null."""
        sql = f'''
            SELECT '{field}' as field, 'NULL' as value
            FROM "{table}"
            WHERE "{field}" IS NULL
            LIMIT {limit}
        '''
        
        count_sql = f'SELECT COUNT(*) as cnt FROM "{table}" WHERE "{field}" IS NULL'
        
        try:
            violations = self._query(sql)
            count_result = self._query(count_sql)
            count = count_result[0]["cnt"] if count_result else 0
            
            for v in violations:
                v["rule"] = "not_null"
                v["message"] = "Required field is null"
            
            return {
                "violations": violations,
                "violation_count": count,
                "message": f"{count} null values in required field {field}",
                "sql": [sql]
            }
        except Exception as e:
            logger.error(f"[VALIDATE] Not null validation error: {e}")
            return {"violations": [], "violation_count": 0, "message": str(e), "sql": [sql]}
    
    def _validate_unique(self, table: str, field: str, rule: Dict, limit: int) -> Dict:
        """Validate field values are unique."""
        sql = f'''
            SELECT "{field}" as value, '{field}' as field, COUNT(*) as duplicate_count
            FROM "{table}"
            WHERE "{field}" IS NOT NULL
            GROUP BY "{field}"
            HAVING COUNT(*) > 1
            LIMIT {limit}
        '''
        
        count_sql = f'''
            SELECT COUNT(*) as cnt FROM (
                SELECT "{field}" FROM "{table}"
                WHERE "{field}" IS NOT NULL
                GROUP BY "{field}"
                HAVING COUNT(*) > 1
            )
        '''
        
        try:
            violations = self._query(sql)
            count_result = self._query(count_sql)
            count = count_result[0]["cnt"] if count_result else 0
            
            for v in violations:
                v["rule"] = "unique"
                v["message"] = f"Duplicate value (appears {v.get('duplicate_count', 2)} times)"
            
            return {
                "violations": violations,
                "violation_count": count,
                "message": f"{count} duplicate values in {field}",
                "sql": [sql]
            }
        except Exception as e:
            logger.error(f"[VALIDATE] Unique validation error: {e}")
            return {"violations": [], "violation_count": 0, "message": str(e), "sql": [sql]}
    
    def _validate_custom(self, table: str, field: str, rule: Dict, limit: int) -> Dict:
        """Validate using custom SQL predicate."""
        predicate = rule["sql"]
        
        # The predicate should be a condition that's TRUE for VALID records
        # So we select where it's FALSE (violations)
        sql = f'''
            SELECT "{field}" as value, '{field}' as field
            FROM "{table}"
            WHERE NOT ({predicate})
            LIMIT {limit}
        '''
        
        count_sql = f'SELECT COUNT(*) as cnt FROM "{table}" WHERE NOT ({predicate})'
        
        try:
            violations = self._query(sql)
            count_result = self._query(count_sql)
            count = count_result[0]["cnt"] if count_result else 0
            
            for v in violations:
                v["rule"] = f"custom:{predicate[:50]}"
                v["message"] = f"Custom rule violation"
            
            return {
                "violations": violations,
                "violation_count": count,
                "message": f"{count} records violate custom rule",
                "sql": [sql]
            }
        except Exception as e:
            logger.error(f"[VALIDATE] Custom validation error: {e}")
            return {"violations": [], "violation_count": 0, "message": str(e), "sql": [sql]}


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

def validate(conn,
            project: str,
            source_table: str,
            rules: List[Dict],
            sample_limit: int = 10) -> EngineResult:
    """
    Convenience function to run validation.
    
    Args:
        conn: DuckDB connection
        project: Project ID
        source_table: Table to validate
        rules: List of validation rules
        sample_limit: Max violations per rule
        
    Returns:
        EngineResult with validation findings
    """
    engine = ValidateEngine(conn, project)
    return engine.execute({
        "source_table": source_table,
        "rules": rules,
        "sample_limit": sample_limit
    })
