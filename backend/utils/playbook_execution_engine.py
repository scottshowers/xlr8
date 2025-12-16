"""
PLAYBOOK EXECUTION ENGINE
=========================

Runs playbooks using rules from linked standards.

Flow:
1. Load playbook config
2. Get linked standards
3. Pull rules from those standards
4. Execute each step
5. For compliance steps → run rules against project data
6. Generate findings
7. Produce deliverables

This connects P4 (Standards) with Playbooks.
"""

import os
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class PlaybookRule:
    """A rule extracted from a linked standard."""
    rule_id: str
    title: str
    description: str
    applies_to: Dict[str, Any]
    requirement: Dict[str, Any]
    check_type: str  # data, config, process
    suggested_sql_pattern: Optional[str]
    category: str
    severity: str
    source_document: str
    source_page: Optional[int]


@dataclass
class Finding:
    """A compliance finding (Five C's format)."""
    finding_id: str
    rule_id: str
    title: str
    severity: str
    category: str
    
    # Five C's
    condition: str      # What we found
    criteria: str       # What the standard says
    cause: str          # Why this happened
    consequence: str    # Risk/impact
    corrective_action: str  # How to fix
    
    # Evidence
    evidence: Dict[str, Any]
    affected_count: int = 0
    
    # Source
    source_document: str = ""
    source_page: Optional[int] = None


@dataclass
class StepResult:
    """Result of executing a playbook step."""
    step_number: str
    step_name: str
    status: str  # running, completed, failed, skipped
    started_at: str
    completed_at: Optional[str] = None
    
    # What happened
    rules_checked: int = 0
    findings: List[Finding] = field(default_factory=list)
    outputs: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class PlaybookRunResult:
    """Complete result of a playbook execution."""
    run_id: str
    playbook_id: str
    project_id: str
    status: str  # running, completed, failed
    
    started_at: str
    completed_at: Optional[str] = None
    
    # Summary
    total_rules_checked: int = 0
    violations_found: int = 0
    warnings_found: int = 0
    
    # Details
    step_results: Dict[str, StepResult] = field(default_factory=dict)
    all_findings: List[Finding] = field(default_factory=list)
    
    # Deliverables generated
    deliverables: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# SUPABASE CLIENT
# =============================================================================

_supabase = None

def _get_supabase():
    global _supabase
    if _supabase is None:
        try:
            from supabase import create_client
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
            if url and key:
                _supabase = create_client(url, key)
        except Exception as e:
            logger.warning(f"[PLAYBOOK-ENGINE] Supabase not available: {e}")
    return _supabase


# =============================================================================
# LOAD PLAYBOOK & RULES
# =============================================================================

def get_playbook_config(playbook_id: str) -> Optional[Dict]:
    """Load playbook configuration from Supabase."""
    supabase = _get_supabase()
    if not supabase:
        return None
    
    try:
        result = supabase.table("playbook_configs")\
            .select("*")\
            .eq("playbook_id", playbook_id)\
            .eq("is_active", True)\
            .single()\
            .execute()
        return result.data
    except Exception as e:
        logger.error(f"[PLAYBOOK-ENGINE] Failed to load playbook {playbook_id}: {e}")
        return None


def get_linked_standards(playbook_id: str) -> List[Dict]:
    """Get standards linked to this playbook."""
    supabase = _get_supabase()
    if not supabase:
        return []
    
    try:
        result = supabase.table("playbook_standards")\
            .select("*, standards(*)")\
            .eq("playbook_id", playbook_id)\
            .execute()
        return result.data or []
    except Exception as e:
        logger.error(f"[PLAYBOOK-ENGINE] Failed to get linked standards: {e}")
        return []


def get_rules_for_playbook(playbook_id: str) -> List[PlaybookRule]:
    """Get all active rules from standards linked to this playbook."""
    supabase = _get_supabase()
    if not supabase:
        return []
    
    try:
        # Use the helper function we created
        result = supabase.rpc("get_playbook_rules", {"p_playbook_id": playbook_id}).execute()
        
        rules = []
        for row in (result.data or []):
            rules.append(PlaybookRule(
                rule_id=row.get("rule_id", ""),
                title=row.get("title", ""),
                description=row.get("description", ""),
                applies_to=row.get("applies_to", {}),
                requirement=row.get("requirement", {}),
                check_type=row.get("check_type", "data"),
                suggested_sql_pattern=row.get("suggested_sql_pattern"),
                category=row.get("category", "general"),
                severity=row.get("severity", "medium"),
                source_document=row.get("source_document", ""),
                source_page=row.get("source_page")
            ))
        
        logger.info(f"[PLAYBOOK-ENGINE] Loaded {len(rules)} rules for playbook {playbook_id}")
        return rules
        
    except Exception as e:
        logger.error(f"[PLAYBOOK-ENGINE] Failed to get rules: {e}")
        return []


# =============================================================================
# COMPLIANCE CHECK EXECUTION
# =============================================================================

def _get_project_schema(project_id: str) -> Dict[str, Any]:
    """Get schema info for a project from DuckDB/profiles."""
    # Import the intelligence service to get schema
    try:
        from services.project_intelligence_service import ProjectIntelligenceService
        service = ProjectIntelligenceService(project_id)
        return service.get_schema_summary()
    except Exception as e:
        logger.warning(f"[PLAYBOOK-ENGINE] Could not get schema: {e}")
        return {}


def _generate_check_sql(rule: PlaybookRule, schema: Dict) -> Optional[str]:
    """
    Use LLM to generate SQL that checks this rule against the schema.
    
    This is where the magic happens - the LLM maps abstract rules
    to concrete SQL against the customer's actual data structure.
    """
    try:
        # Try to import the LLM orchestrator
        try:
            from services.llm_orchestrator import LLMOrchestrator
        except ImportError:
            from backend.services.llm_orchestrator import LLMOrchestrator
        
        llm = LLMOrchestrator()
        
        prompt = f"""You are a compliance SQL generator. Generate a SQL query that finds records violating this rule.

RULE: {rule.title}
DESCRIPTION: {rule.description}

APPLIES TO:
{json.dumps(rule.applies_to, indent=2)}

REQUIREMENT:
{json.dumps(rule.requirement, indent=2)}

SUGGESTED PATTERN (if any): {rule.suggested_sql_pattern or 'None'}

AVAILABLE SCHEMA:
{json.dumps(schema, indent=2)}

Generate a SELECT query that returns records that VIOLATE this rule (non-compliant records).
The query should:
1. Select identifying columns (employee_id, name, etc.)
2. Select the columns being checked
3. Filter to show only violations
4. Include a 'violation_reason' column explaining why each record fails

Return ONLY the SQL query, no explanation.
If you cannot generate a meaningful check for this rule against this schema, return: SELECT 'SKIP' as status
"""
        
        result = llm.generate(prompt, max_tokens=1000)
        sql = result.strip()
        
        # Clean up markdown if present
        if sql.startswith("```"):
            sql = sql.split("```")[1]
            if sql.startswith("sql"):
                sql = sql[3:]
        sql = sql.strip()
        
        return sql if sql and "SKIP" not in sql else None
        
    except Exception as e:
        logger.error(f"[PLAYBOOK-ENGINE] SQL generation failed for rule {rule.rule_id}: {e}")
        return None


def _execute_check(project_id: str, sql: str) -> List[Dict]:
    """Execute a compliance check SQL against project data."""
    try:
        # Get DuckDB connection for project
        try:
            from services.duckdb_service import get_duckdb_connection
        except ImportError:
            from backend.services.duckdb_service import get_duckdb_connection
        
        conn = get_duckdb_connection(project_id)
        if not conn:
            return []
        
        result = conn.execute(sql).fetchall()
        columns = [desc[0] for desc in conn.description]
        
        return [dict(zip(columns, row)) for row in result]
        
    except Exception as e:
        logger.error(f"[PLAYBOOK-ENGINE] Check execution failed: {e}")
        return []


def run_compliance_check(
    rule: PlaybookRule, 
    project_id: str, 
    schema: Dict
) -> Optional[Finding]:
    """
    Run a single compliance check for a rule.
    
    Returns a Finding if violations found, None if compliant.
    """
    # Generate SQL for this rule
    sql = _generate_check_sql(rule, schema)
    if not sql:
        logger.info(f"[PLAYBOOK-ENGINE] Skipping rule {rule.rule_id} - no applicable check")
        return None
    
    logger.info(f"[PLAYBOOK-ENGINE] Running check for rule: {rule.title}")
    logger.debug(f"[PLAYBOOK-ENGINE] SQL: {sql[:200]}...")
    
    # Execute check
    violations = _execute_check(project_id, sql)
    
    if not violations:
        logger.info(f"[PLAYBOOK-ENGINE] Rule {rule.rule_id}: COMPLIANT")
        return None
    
    # Generate finding
    finding = Finding(
        finding_id=f"F-{uuid.uuid4().hex[:8]}",
        rule_id=rule.rule_id,
        title=rule.title,
        severity=rule.severity,
        category=rule.category,
        condition=f"Found {len(violations)} record(s) that do not comply with this requirement.",
        criteria=rule.description,
        cause="Configuration or data does not match the standard requirements.",
        consequence=_get_consequence(rule.severity),
        corrective_action=json.dumps(rule.requirement.get("action", "Review and update affected records.")),
        evidence={
            "violation_count": len(violations),
            "sample_records": violations[:10],  # First 10 for evidence
            "sql_used": sql
        },
        affected_count=len(violations),
        source_document=rule.source_document,
        source_page=rule.source_page
    )
    
    logger.info(f"[PLAYBOOK-ENGINE] Rule {rule.rule_id}: {len(violations)} VIOLATIONS")
    return finding


def _get_consequence(severity: str) -> str:
    """Get consequence text based on severity."""
    consequences = {
        "critical": "Non-compliance may result in regulatory penalties, failed audits, or significant financial impact.",
        "high": "May cause compliance issues or operational problems if not addressed before effective date.",
        "medium": "Should be addressed to ensure full compliance and avoid potential issues.",
        "low": "Recommended improvement for best practices compliance."
    }
    return consequences.get(severity, consequences["medium"])


# =============================================================================
# PLAYBOOK EXECUTION
# =============================================================================

def execute_playbook(
    playbook_id: str,
    project_id: str,
    run_by: str = "system"
) -> PlaybookRunResult:
    """
    Execute a playbook against a project.
    
    Flow:
    1. Load playbook config
    2. Get linked standards and rules
    3. Get project schema
    4. Execute each step
    5. For compliance steps, run rule checks
    6. Collect findings
    7. Generate deliverables
    8. Save run results
    """
    run_id = f"RUN-{uuid.uuid4().hex[:12]}"
    started_at = datetime.now().isoformat()
    
    result = PlaybookRunResult(
        run_id=run_id,
        playbook_id=playbook_id,
        project_id=project_id,
        status="running",
        started_at=started_at
    )
    
    logger.info(f"[PLAYBOOK-ENGINE] Starting playbook {playbook_id} for project {project_id}")
    
    try:
        # 1. Load playbook config
        config = get_playbook_config(playbook_id)
        if not config:
            result.status = "failed"
            logger.error(f"[PLAYBOOK-ENGINE] Playbook not found: {playbook_id}")
            return result
        
        # 2. Get rules from linked standards
        rules = get_rules_for_playbook(playbook_id)
        logger.info(f"[PLAYBOOK-ENGINE] Loaded {len(rules)} rules from linked standards")
        
        # 3. Get project schema
        schema = _get_project_schema(project_id)
        
        # 4. Execute steps
        steps = config.get("steps", [])
        
        for step_config in steps:
            step_num = step_config.get("step_number", "?")
            step_name = step_config.get("step_name", "Unnamed Step")
            
            step_result = StepResult(
                step_number=step_num,
                step_name=step_name,
                status="running",
                started_at=datetime.now().isoformat()
            )
            
            logger.info(f"[PLAYBOOK-ENGINE] Executing step {step_num}: {step_name}")
            
            # Check if this is a compliance step
            step_type = step_config.get("step_type", "manual")
            
            if step_type == "compliance" or "compliance" in step_name.lower():
                # Run all applicable rules
                for rule in rules:
                    finding = run_compliance_check(rule, project_id, schema)
                    if finding:
                        step_result.findings.append(finding)
                        result.all_findings.append(finding)
                        
                        if finding.severity in ["critical", "high"]:
                            result.violations_found += 1
                        else:
                            result.warnings_found += 1
                    
                    step_result.rules_checked += 1
                    result.total_rules_checked += 1
            
            # Mark step complete
            step_result.status = "completed"
            step_result.completed_at = datetime.now().isoformat()
            result.step_results[step_num] = step_result
        
        # 5. Generate deliverables summary
        result.deliverables = {
            "compliance_summary": {
                "total_rules": result.total_rules_checked,
                "violations": result.violations_found,
                "warnings": result.warnings_found,
                "compliant": result.total_rules_checked - result.violations_found - result.warnings_found
            },
            "findings_by_severity": _group_findings_by_severity(result.all_findings),
            "findings_by_category": _group_findings_by_category(result.all_findings)
        }
        
        # 6. Mark complete
        result.status = "completed"
        result.completed_at = datetime.now().isoformat()
        
        # 7. Save to database
        _save_run_result(result)
        
        logger.info(f"[PLAYBOOK-ENGINE] Playbook complete. "
                   f"Rules: {result.total_rules_checked}, "
                   f"Violations: {result.violations_found}, "
                   f"Warnings: {result.warnings_found}")
        
        return result
        
    except Exception as e:
        logger.error(f"[PLAYBOOK-ENGINE] Playbook execution failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        result.status = "failed"
        return result


def _group_findings_by_severity(findings: List[Finding]) -> Dict[str, int]:
    """Group findings by severity."""
    groups = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in findings:
        groups[f.severity] = groups.get(f.severity, 0) + 1
    return groups


def _group_findings_by_category(findings: List[Finding]) -> Dict[str, int]:
    """Group findings by category."""
    groups = {}
    for f in findings:
        groups[f.category] = groups.get(f.category, 0) + 1
    return groups


def _save_run_result(result: PlaybookRunResult):
    """Save playbook run result to Supabase."""
    supabase = _get_supabase()
    if not supabase:
        return
    
    try:
        # Convert to dict
        data = {
            "run_id": result.run_id,
            "playbook_id": result.playbook_id,
            "project_id": result.project_id,
            "status": result.status,
            "started_at": result.started_at,
            "completed_at": result.completed_at,
            "total_rules_checked": result.total_rules_checked,
            "violations_found": result.violations_found,
            "warnings_found": result.warnings_found,
            "step_results": {k: {
                "step_number": v.step_number,
                "step_name": v.step_name,
                "status": v.status,
                "rules_checked": v.rules_checked,
                "findings_count": len(v.findings)
            } for k, v in result.step_results.items()},
            "findings": [
                {
                    "finding_id": f.finding_id,
                    "rule_id": f.rule_id,
                    "title": f.title,
                    "severity": f.severity,
                    "category": f.category,
                    "condition": f.condition,
                    "criteria": f.criteria,
                    "corrective_action": f.corrective_action,
                    "affected_count": f.affected_count
                }
                for f in result.all_findings
            ]
        }
        
        supabase.table("playbook_runs").upsert(data).execute()
        logger.info(f"[PLAYBOOK-ENGINE] Saved run result: {result.run_id}")
        
    except Exception as e:
        logger.error(f"[PLAYBOOK-ENGINE] Failed to save run result: {e}")


# =============================================================================
# LINK MANAGEMENT API
# =============================================================================

def link_standard_to_playbook(
    playbook_id: str, 
    standard_id: int,
    usage_type: str = "compliance"
) -> bool:
    """Link a standard to a playbook."""
    supabase = _get_supabase()
    if not supabase:
        return False
    
    try:
        # Insert link
        supabase.table("playbook_standards").upsert({
            "playbook_id": playbook_id,
            "standard_id": standard_id,
            "usage_type": usage_type
        }).execute()
        
        # Update shortcut array on playbook_configs
        config = supabase.table("playbook_configs")\
            .select("linked_standard_ids")\
            .eq("playbook_id", playbook_id)\
            .single()\
            .execute()
        
        current_ids = config.data.get("linked_standard_ids", []) or []
        if standard_id not in current_ids:
            current_ids.append(standard_id)
            supabase.table("playbook_configs")\
                .update({"linked_standard_ids": current_ids})\
                .eq("playbook_id", playbook_id)\
                .execute()
        
        logger.info(f"[PLAYBOOK-ENGINE] Linked standard {standard_id} to playbook {playbook_id}")
        return True
        
    except Exception as e:
        logger.error(f"[PLAYBOOK-ENGINE] Failed to link standard: {e}")
        return False


def unlink_standard_from_playbook(playbook_id: str, standard_id: int) -> bool:
    """Unlink a standard from a playbook."""
    supabase = _get_supabase()
    if not supabase:
        return False
    
    try:
        # Remove link
        supabase.table("playbook_standards")\
            .delete()\
            .eq("playbook_id", playbook_id)\
            .eq("standard_id", standard_id)\
            .execute()
        
        # Update shortcut array
        config = supabase.table("playbook_configs")\
            .select("linked_standard_ids")\
            .eq("playbook_id", playbook_id)\
            .single()\
            .execute()
        
        current_ids = config.data.get("linked_standard_ids", []) or []
        if standard_id in current_ids:
            current_ids.remove(standard_id)
            supabase.table("playbook_configs")\
                .update({"linked_standard_ids": current_ids})\
                .eq("playbook_id", playbook_id)\
                .execute()
        
        return True
        
    except Exception as e:
        logger.error(f"[PLAYBOOK-ENGINE] Failed to unlink standard: {e}")
        return False


def get_available_standards() -> List[Dict]:
    """Get all standards available for linking."""
    supabase = _get_supabase()
    if not supabase:
        return []
    
    try:
        result = supabase.table("standards")\
            .select("id, document_id, filename, title, domain")\
            .eq("is_active", True)\
            .execute()
        return result.data or []
    except Exception as e:
        logger.error(f"[PLAYBOOK-ENGINE] Failed to get standards: {e}")
        return []
