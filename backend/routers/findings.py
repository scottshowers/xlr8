"""
Findings Router
===============

API endpoints for the Findings Dashboard.
Auto-surfaces analysis results without user queries.

Created: January 14, 2026 - Phase 4A.4
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from utils.cost_equivalent import get_project_cost_equivalent, calculate_cost_equivalent
from utils.duckdb_manager import duckdb_manager

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# MODELS
# =============================================================================

class FindingSeverity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class FindingCategory(str, Enum):
    DATA_QUALITY = "data_quality"
    CONFIGURATION = "configuration"
    COMPLIANCE = "compliance"
    COVERAGE = "coverage"
    PATTERN = "pattern"


class Finding(BaseModel):
    """A single finding from analysis."""
    id: str
    severity: FindingSeverity
    category: FindingCategory
    title: str
    subtitle: Optional[str] = None
    description: str
    impact_explanation: Optional[str] = None
    impact_value: Optional[str] = None  # e.g., "$4,500" or "127 employees"
    affected_count: int = 0
    affected_table: Optional[str] = None
    affected_percentage: Optional[float] = None
    effort_estimate: Optional[str] = None  # e.g., "2-4 hours"
    recommended_actions: List[str] = []
    status: str = "open"  # open, acknowledged, resolved
    detected_at: str = ""


class FindingsSummary(BaseModel):
    """Summary stats for findings dashboard."""
    total: int = 0
    critical: int = 0
    warning: int = 0
    info: int = 0
    by_category: Dict[str, int] = {}


class FindingsResponse(BaseModel):
    """Response for findings endpoint."""
    project: str
    findings: List[Finding]
    summary: FindingsSummary
    cost_equivalent: Dict[str, Any]
    generated_at: str


# =============================================================================
# FINDING GENERATORS
# =============================================================================

def generate_data_quality_findings(project_name: str) -> List[Finding]:
    """
    Generate findings from data quality analysis.
    Looks at column profiles for nulls, duplicates, outliers.
    """
    findings = []
    
    try:
        handler = duckdb_manager.get_handler(project_name)
        if not handler:
            return findings
        
        # Get all column profiles
        try:
            profiles = handler.conn.execute("""
                SELECT * FROM _column_profiles 
                WHERE project = ?
            """, [project_name]).fetchall()
            
            columns = handler.conn.execute(
                "DESCRIBE _column_profiles"
            ).fetchall()
            col_names = [c[0] for c in columns]
        except Exception:
            # Table might not exist
            return findings
        
        for row in profiles:
            profile = dict(zip(col_names, row))
            table_name = profile.get('table_name', '')
            column_name = profile.get('column_name', '')
            
            # Skip metadata tables
            if table_name.startswith('_'):
                continue
            
            # High null percentage finding
            null_pct = profile.get('null_percentage', 0) or 0
            if null_pct > 50:
                findings.append(Finding(
                    id=f"null_{table_name}_{column_name}",
                    severity=FindingSeverity.CRITICAL if null_pct > 80 else FindingSeverity.WARNING,
                    category=FindingCategory.DATA_QUALITY,
                    title=f"High null rate in {column_name}",
                    subtitle=f"{table_name}",
                    description=f"Column '{column_name}' has {null_pct:.0f}% null values. This may indicate missing data or import issues.",
                    impact_explanation="Missing data can affect analysis accuracy and reporting completeness.",
                    affected_count=int(profile.get('null_count', 0) or 0),
                    affected_table=table_name,
                    affected_percentage=null_pct,
                    effort_estimate="1-2 hours",
                    recommended_actions=[
                        f"Review source data for {column_name}",
                        "Check if column should be required",
                        "Consider data enrichment or default values"
                    ],
                    detected_at=datetime.now().isoformat()
                ))
            
            # Low cardinality on expected high-cardinality columns
            distinct_count = profile.get('distinct_count', 0) or 0
            total_count = profile.get('total_count', 0) or 1
            cardinality_pct = (distinct_count / total_count) * 100 if total_count > 0 else 0
            
            # Potential ID columns with duplicates
            if any(kw in column_name.lower() for kw in ['id', 'number', 'code', 'key']):
                if cardinality_pct < 95 and distinct_count > 1 and total_count > 100:
                    dup_count = total_count - distinct_count
                    findings.append(Finding(
                        id=f"dup_{table_name}_{column_name}",
                        severity=FindingSeverity.WARNING,
                        category=FindingCategory.DATA_QUALITY,
                        title=f"Potential duplicates in {column_name}",
                        subtitle=f"{table_name}",
                        description=f"Column '{column_name}' appears to be an identifier but has {dup_count:,} potential duplicates ({100-cardinality_pct:.1f}% duplicate rate).",
                        impact_explanation="Duplicate identifiers can cause data integrity issues and incorrect aggregations.",
                        affected_count=int(dup_count),
                        affected_table=table_name,
                        effort_estimate="2-4 hours",
                        recommended_actions=[
                            "Verify if duplicates are expected",
                            "Check for data import issues",
                            "Review primary key constraints"
                        ],
                        detected_at=datetime.now().isoformat()
                    ))
        
    except Exception as e:
        logger.error(f"Error generating data quality findings: {e}")
    
    return findings


def generate_coverage_findings(project_name: str) -> List[Finding]:
    """
    Generate findings from truth coverage analysis.
    Identifies missing documentation for key topics.
    """
    findings = []
    
    try:
        handler = duckdb_manager.get_handler(project_name)
        if not handler:
            return findings
        
        # Get table classifications to understand what domains exist
        try:
            classifications = handler.conn.execute("""
                SELECT DISTINCT domain, hub_table 
                FROM _table_classifications 
                WHERE project = ?
            """, [project_name]).fetchall()
        except Exception:
            return findings
        
        # Check for common gaps based on domains found
        domains_found = set(c[0] for c in classifications if c[0])
        
        # Check if key domains are missing reference docs
        from utils.chroma_manager import chroma_manager
        
        for domain in domains_found:
            # Check reference collection for this domain
            try:
                collection = chroma_manager.get_collection(project_name, 'reference')
                if collection:
                    results = collection.query(
                        query_texts=[domain],
                        n_results=1
                    )
                    # If no relevant docs found
                    if not results['documents'] or not results['documents'][0]:
                        findings.append(Finding(
                            id=f"coverage_ref_{domain}",
                            severity=FindingSeverity.INFO,
                            category=FindingCategory.COVERAGE,
                            title=f"No reference docs for {domain}",
                            subtitle="Coverage gap",
                            description=f"No vendor documentation or best practices found for the '{domain}' domain. Consider uploading relevant reference materials.",
                            impact_explanation="Missing reference documentation limits the platform's ability to provide best practice recommendations.",
                            effort_estimate="30 min",
                            recommended_actions=[
                                f"Upload vendor documentation for {domain}",
                                "Add implementation guides or best practices"
                            ],
                            detected_at=datetime.now().isoformat()
                        ))
            except Exception as e:
                logger.debug(f"Error checking coverage for {domain}: {e}")
                continue
        
    except Exception as e:
        logger.error(f"Error generating coverage findings: {e}")
    
    return findings


def generate_pattern_findings(project_name: str) -> List[Finding]:
    """
    Generate findings from pattern analysis.
    Looks for anomalies, distributions, and business rule violations.
    """
    findings = []
    
    try:
        handler = duckdb_manager.get_handler(project_name)
        if not handler:
            return findings
        
        tables = handler.list_tables()
        
        for table_name in tables:
            if table_name.startswith('_'):
                continue
            
            try:
                # Get row count
                count_result = handler.conn.execute(
                    f'SELECT COUNT(*) FROM "{table_name}"'
                ).fetchone()
                row_count = count_result[0] if count_result else 0
                
                # Small table warning
                if 0 < row_count < 10:
                    findings.append(Finding(
                        id=f"small_table_{table_name}",
                        severity=FindingSeverity.INFO,
                        category=FindingCategory.PATTERN,
                        title=f"Small dataset: {table_name}",
                        subtitle=f"{row_count} rows",
                        description=f"Table '{table_name}' has only {row_count} rows. Statistical analysis may be limited.",
                        impact_explanation="Small sample sizes reduce confidence in pattern detection and aggregations.",
                        affected_count=row_count,
                        affected_table=table_name,
                        effort_estimate="15 min",
                        recommended_actions=[
                            "Verify this is the complete dataset",
                            "Consider if more data is available"
                        ],
                        detected_at=datetime.now().isoformat()
                    ))
                
                # Check for date columns with future dates
                columns = handler.conn.execute(
                    f'DESCRIBE "{table_name}"'
                ).fetchall()
                
                for col in columns:
                    col_name = col[0]
                    col_type = str(col[1]).lower()
                    
                    if 'date' in col_type or 'timestamp' in col_type:
                        try:
                            future_count = handler.conn.execute(f'''
                                SELECT COUNT(*) FROM "{table_name}" 
                                WHERE "{col_name}" > CURRENT_DATE + INTERVAL '1 year'
                            ''').fetchone()[0]
                            
                            if future_count > 0:
                                findings.append(Finding(
                                    id=f"future_date_{table_name}_{col_name}",
                                    severity=FindingSeverity.WARNING,
                                    category=FindingCategory.DATA_QUALITY,
                                    title=f"Future dates in {col_name}",
                                    subtitle=f"{table_name}",
                                    description=f"Found {future_count:,} records with dates more than 1 year in the future. This may indicate data entry errors.",
                                    affected_count=future_count,
                                    affected_table=table_name,
                                    effort_estimate="1-2 hours",
                                    recommended_actions=[
                                        "Review records with future dates",
                                        "Check for data import formatting issues"
                                    ],
                                    detected_at=datetime.now().isoformat()
                                ))
                        except Exception:
                            continue
                
            except Exception as e:
                logger.debug(f"Error analyzing {table_name}: {e}")
                continue
        
    except Exception as e:
        logger.error(f"Error generating pattern findings: {e}")
    
    return findings


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/{project_name}/findings", response_model=FindingsResponse)
async def get_project_findings(
    project_name: str,
    severity: Optional[str] = Query(None, description="Filter by severity"),
    category: Optional[str] = Query(None, description="Filter by category"),
    status: Optional[str] = Query(None, description="Filter by status")
):
    """
    Get all findings for a project.
    
    Findings are auto-generated from:
    - Data quality analysis (nulls, duplicates, outliers)
    - Coverage analysis (missing documentation)
    - Pattern analysis (anomalies, distributions)
    """
    try:
        # Generate all findings
        all_findings = []
        all_findings.extend(generate_data_quality_findings(project_name))
        all_findings.extend(generate_coverage_findings(project_name))
        all_findings.extend(generate_pattern_findings(project_name))
        
        # Apply filters
        filtered = all_findings
        if severity:
            filtered = [f for f in filtered if f.severity.value == severity]
        if category:
            filtered = [f for f in filtered if f.category.value == category]
        if status:
            filtered = [f for f in filtered if f.status == status]
        
        # Sort by severity (critical first)
        severity_order = {'critical': 0, 'warning': 1, 'info': 2}
        filtered.sort(key=lambda f: severity_order.get(f.severity.value, 99))
        
        # Generate summary
        summary = FindingsSummary(
            total=len(all_findings),
            critical=len([f for f in all_findings if f.severity == FindingSeverity.CRITICAL]),
            warning=len([f for f in all_findings if f.severity == FindingSeverity.WARNING]),
            info=len([f for f in all_findings if f.severity == FindingSeverity.INFO]),
            by_category={
                cat.value: len([f for f in all_findings if f.category == cat])
                for cat in FindingCategory
            }
        )
        
        # Get cost equivalent
        cost_equiv = get_project_cost_equivalent(project_name)
        
        return FindingsResponse(
            project=project_name,
            findings=filtered,
            summary=summary,
            cost_equivalent=cost_equiv,
            generated_at=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error getting findings for {project_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_name}/cost-equivalent")
async def get_cost_equivalent(
    project_name: str,
    hourly_rate: float = Query(250.0, description="Consultant hourly rate")
):
    """
    Get cost equivalent calculation for a project.
    
    Shows what the equivalent manual analysis would cost.
    """
    try:
        result = get_project_cost_equivalent(project_name, hourly_rate)
        return result
    except Exception as e:
        logger.error(f"Error calculating cost equivalent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_name}/findings/{finding_id}/acknowledge")
async def acknowledge_finding(project_name: str, finding_id: str):
    """Mark a finding as acknowledged."""
    # For now, findings are generated on-the-fly
    # In future, store acknowledgments in database
    return {"success": True, "finding_id": finding_id, "status": "acknowledged"}


@router.post("/{project_name}/findings/{finding_id}/resolve")
async def resolve_finding(project_name: str, finding_id: str):
    """Mark a finding as resolved."""
    return {"success": True, "finding_id": finding_id, "status": "resolved"}
