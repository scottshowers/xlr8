"""
Data Quality Service
====================

Proactive Data Quality Alerts - Don't just answer, NOTICE things.

A world-class consultant doesn't just answer the question asked.
They notice data quality issues and surface them proactively.

Alert Categories:
- INTEGRITY: Data consistency issues (status mismatches, orphan records)
- COMPLETENESS: Missing data (null hire dates, empty required fields)
- DUPLICATES: Duplicate key values (SSN, employee ID)
- ANOMALIES: Statistical outliers (negative salaries, future dates)

Usage:
    service = DataQualityService("my_project")
    alerts = service.run_checks(handler, tables)
    summary = service.get_summary()
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Try to import project intelligence for pre-computed findings
try:
    from backend.utils.project_intelligence import get_project_intelligence
    PROJECT_INTELLIGENCE_AVAILABLE = True
except ImportError:
    try:
        from utils.project_intelligence import get_project_intelligence
        PROJECT_INTELLIGENCE_AVAILABLE = True
    except ImportError:
        PROJECT_INTELLIGENCE_AVAILABLE = False
        get_project_intelligence = None


class DataQualityService:
    """
    Proactive Data Quality Alerts - Don't just answer, NOTICE things.
    
    A world-class consultant doesn't just answer the question asked.
    They notice data quality issues and surface them proactively.
    """
    
    # Quality checks to run
    QUALITY_CHECKS = [
        {
            'id': 'status_mismatch',
            'name': 'Status/Date Mismatch',
            'description': 'Employees with termination date but active status',
            'category': 'INTEGRITY',
            'severity': 'warning',
            'sql_template': '''
                SELECT COUNT(*) as count
                FROM "{table}"
                WHERE {status_col} = 'A' 
                AND {term_date_col} IS NOT NULL 
                AND {term_date_col} != ''
            ''',
            'required_columns': ['status', 'termination_date']
        },
        {
            'id': 'missing_hire_date',
            'name': 'Missing Hire Dates',
            'description': 'Records missing hire date',
            'category': 'COMPLETENESS',
            'severity': 'info',
            'sql_template': '''
                SELECT COUNT(*) as count,
                       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM "{table}"), 1) as pct
                FROM "{table}"
                WHERE {hire_date_col} IS NULL OR {hire_date_col} = ''
            ''',
            'required_columns': ['hire_date']
        },
        {
            'id': 'duplicate_ssn',
            'name': 'Duplicate SSN',
            'description': 'Multiple records with same SSN',
            'category': 'DUPLICATES',
            'severity': 'critical',
            'sql_template': '''
                SELECT COUNT(*) as count
                FROM (
                    SELECT {ssn_col}, COUNT(*) as cnt
                    FROM "{table}"
                    WHERE {ssn_col} IS NOT NULL AND {ssn_col} != ''
                    GROUP BY {ssn_col}
                    HAVING COUNT(*) > 1
                )
            ''',
            'required_columns': ['ssn']
        },
        {
            'id': 'duplicate_employee_id',
            'name': 'Duplicate Employee ID',
            'description': 'Multiple records with same Employee ID',
            'category': 'DUPLICATES',
            'severity': 'critical',
            'sql_template': '''
                SELECT COUNT(*) as count
                FROM (
                    SELECT {emp_id_col}, COUNT(*) as cnt
                    FROM "{table}"
                    WHERE {emp_id_col} IS NOT NULL AND {emp_id_col} != ''
                    GROUP BY {emp_id_col}
                    HAVING COUNT(*) > 1
                )
            ''',
            'required_columns': ['employee_id']
        },
        {
            'id': 'future_hire_date',
            'name': 'Future Hire Dates',
            'description': 'Hire dates in the future',
            'category': 'ANOMALIES',
            'severity': 'warning',
            'sql_template': '''
                SELECT COUNT(*) as count
                FROM "{table}"
                WHERE TRY_CAST({hire_date_col} AS DATE) > CURRENT_DATE
            ''',
            'required_columns': ['hire_date']
        },
        {
            'id': 'negative_pay',
            'name': 'Negative Pay Rates',
            'description': 'Negative hourly or salary values',
            'category': 'ANOMALIES',
            'severity': 'critical',
            'sql_template': '''
                SELECT COUNT(*) as count
                FROM "{table}"
                WHERE TRY_CAST({pay_col} AS DOUBLE) < 0
            ''',
            'required_columns': ['pay_rate']
        }
    ]
    
    # Column name mappings (what we look for → what it might be called)
    COLUMN_MAPPINGS = {
        'status': ['employment_status', 'emp_status', 'status', 'employee_status', 'active_flag'],
        'termination_date': ['termination_date', 'term_date', 'termdate', 'end_date', 'separation_date'],
        'hire_date': ['hire_date', 'hiredate', 'start_date', 'original_hire_date', 'employment_date'],
        'ssn': ['ssn', 'social_security', 'social_security_number', 'ss_number'],
        'employee_id': ['employee_id', 'emp_id', 'empid', 'employee_number', 'ee_id', 'emplid'],
        'pay_rate': ['hourly_rate', 'pay_rate', 'salary', 'annual_salary', 'hourly_pay_rate', 'compensation']
    }
    
    def __init__(self, project: str):
        self.project = project
        self.alerts: List[Dict] = []
    
    def _find_column(self, columns: List[str], column_type: str) -> Optional[str]:
        """Find matching column name for a column type."""
        patterns = self.COLUMN_MAPPINGS.get(column_type, [])
        columns_lower = [c.lower() for c in columns]
        
        for pattern in patterns:
            for i, col_lower in enumerate(columns_lower):
                if pattern in col_lower:
                    return columns[i]  # Return original case
        
        return None
    
    def run_checks(self, handler, tables: List[Dict]) -> List[Dict]:
        """
        Get quality alerts - tries intelligence service first, falls back to SQL checks.
        
        Phase 3.5: Consumes pre-computed findings from ProjectIntelligenceService
        when available, avoiding redundant SQL execution.
        
        Args:
            handler: DuckDB handler
            tables: List of table info dicts with 'table_name' and 'columns'
            
        Returns:
            List of alert dicts
        """
        self.alerts = []
        
        # PHASE 3.5: Try intelligence service first (pre-computed on upload)
        if PROJECT_INTELLIGENCE_AVAILABLE and handler and get_project_intelligence:
            try:
                logger.warning(f"[DATA_QUALITY] Attempting to load from intelligence service for {self.project}")
                intelligence = get_project_intelligence(self.project, handler)
                if intelligence and intelligence.findings:
                    logger.warning(f"[DATA_QUALITY] Found {len(intelligence.findings)} findings in intelligence")
                    # Convert intelligence findings to alert format
                    for finding in intelligence.findings:
                        alert = {
                            'id': finding.finding_type,
                            'name': finding.title,
                            'category': finding.category,
                            'severity': finding.severity,
                            'table': finding.table_name.split('__')[-1] if finding.table_name else '',
                            'count': finding.affected_count,
                            'percentage': finding.affected_percentage,
                            'description': finding.description,
                            'details': f"{finding.affected_count:,} records affected" if finding.affected_count else finding.description,
                            'evidence_sql': finding.evidence_sql
                        }
                        self.alerts.append(alert)
                    
                    # Sort by severity
                    severity_order = {'critical': 0, 'warning': 1, 'info': 2}
                    self.alerts.sort(key=lambda x: severity_order.get(x.get('severity', 'info'), 3))
                    
                    logger.warning(f"[DATA_QUALITY] Loaded {len(self.alerts)} alerts from intelligence service")
                    return self.alerts
                else:
                    logger.warning(f"[DATA_QUALITY] No findings in intelligence, falling back to SQL checks")
            except Exception as e:
                logger.warning(f"[DATA_QUALITY] Intelligence service unavailable, falling back: {e}")
        
        # FALLBACK: Run SQL checks directly (original behavior)
        if not handler or not handler.conn:
            return self.alerts
        
        for table_info in tables:
            table_name = table_info.get('table_name', '')
            columns = table_info.get('columns', [])
            
            if not columns:
                continue
            
            for check in self.QUALITY_CHECKS:
                self._run_check(handler, table_name, columns, check)
        
        # Sort by severity
        severity_order = {'critical': 0, 'warning': 1, 'info': 2}
        self.alerts.sort(key=lambda x: severity_order.get(x.get('severity', 'info'), 3))
        
        return self.alerts
    
    def _run_check(self, handler, table_name: str, columns: List[str], check: Dict) -> None:
        """Run a single quality check."""
        try:
            # Find required columns
            col_mappings = {}
            for required_col in check['required_columns']:
                found_col = self._find_column(columns, required_col)
                if not found_col:
                    return  # Skip if required column not found
                col_mappings[f'{required_col}_col'] = found_col
            
            # Build SQL
            sql = check['sql_template'].format(
                table=table_name,
                **col_mappings
            )
            
            # Execute
            result = handler.conn.execute(sql).fetchone()
            
            if result and result[0]:
                count = result[0]
                pct = result[1] if len(result) > 1 else None
                
                if count > 0:
                    alert = {
                        'id': check['id'],
                        'name': check['name'],
                        'category': check['category'],
                        'severity': check['severity'],
                        'table': table_name.split('__')[-1],  # Remove project prefix
                        'count': count,
                        'percentage': pct,
                        'description': check['description'],
                        'details': f"{count:,} records affected" + (f" ({pct}%)" if pct else "")
                    }
                    self.alerts.append(alert)
                    
        except Exception as e:
            logger.debug(f"[DATA_QUALITY] Check {check['id']} failed on {table_name}: {e}")
    
    def get_summary(self) -> Dict:
        """Get summary of all alerts."""
        if not self.alerts:
            return {'status': 'clean', 'message': '✅ No data quality issues detected'}
        
        critical = len([a for a in self.alerts if a['severity'] == 'critical'])
        warning = len([a for a in self.alerts if a['severity'] == 'warning'])
        info = len([a for a in self.alerts if a['severity'] == 'info'])
        
        if critical > 0:
            status = 'critical'
            emoji = '🚨'
        elif warning > 0:
            status = 'warning'
            emoji = '⚠️'
        else:
            status = 'info'
            emoji = 'ℹ️'
        
        return {
            'status': status,
            'message': f"{emoji} {len(self.alerts)} data quality issue(s) detected",
            'critical': critical,
            'warning': warning,
            'info': info,
            'alerts': self.alerts
        }
