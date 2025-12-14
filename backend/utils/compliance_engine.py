"""
XLR8 COMPLIANCE ENGINE
======================

Runs extracted rules against customer data to identify compliance gaps.
Uses LLM to intelligently map rules to actual schema - NO HARDCODING.

The engine:
1. Takes a rule (from standards_processor)
2. Gets the customer's schema and column profiles (from P1)
3. Uses LLM to generate appropriate SQL checks
4. Executes checks against DuckDB
5. Generates auditor-quality findings

Deploy to: backend/utils/compliance_engine.py

Author: XLR8 Team
Version: 1.0.0 - P4 Standards Layer
"""

import os
import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ComplianceCheck:
    """A single compliance check to run."""
    check_id: str
    rule_id: str
    rule_title: str
    
    # The generated check
    sql_query: str
    description: str
    
    # Expected vs actual
    expected_result: str  # "no rows", "all rows match", "count = 0", etc.
    
    # Metadata
    severity: str = "medium"
    category: str = "general"


@dataclass 
class Finding:
    """
    An auditor-quality finding following the Five C's framework.
    This is the core deliverable of P4.
    """
    finding_id: str
    title: str
    severity: str  # low, medium, high, critical
    category: str
    
    # THE FIVE C's
    condition: Dict[str, Any]      # What we found
    criteria: Dict[str, Any]       # What it should be (the standard)
    cause: Dict[str, Any]          # Why it happened (likely reasons)
    consequence: Dict[str, Any]    # Risk/impact (renamed from 'effect')
    corrective_action: Dict[str, Any]  # Specific steps to fix (renamed from 'recommendation')
    
    # EVIDENCE - The proof
    evidence: Dict[str, Any]
    
    # Source tracking
    rule_id: str
    source_document: str
    source_page: Optional[int] = None
    
    # Metadata
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return {
            "finding_id": self.finding_id,
            "title": self.title,
            "severity": self.severity,
            "category": self.category,
            "condition": self.condition,
            "criteria": self.criteria,
            "cause": self.cause,
            "consequence": self.consequence,
            "corrective_action": self.corrective_action,
            "evidence": self.evidence,
            "rule_id": self.rule_id,
            "source_document": self.source_document,
            "source_page": self.source_page,
            "generated_at": self.generated_at
        }


# =============================================================================
# LLM INTEGRATION - Uses LLMOrchestrator like standards_processor
# =============================================================================

_orchestrator = None

def _get_orchestrator():
    """Get or create LLMOrchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        try:
            try:
                from utils.llm_orchestrator import LLMOrchestrator
            except ImportError:
                from backend.utils.llm_orchestrator import LLMOrchestrator
            _orchestrator = LLMOrchestrator()
            logger.info("[COMPLIANCE] LLMOrchestrator initialized")
        except Exception as e:
            logger.error(f"[COMPLIANCE] Could not load LLMOrchestrator: {e}")
            return None
    return _orchestrator


def _call_llm(prompt: str, system_prompt: str = None) -> str:
    """Call LLM using LLMOrchestrator."""
    orchestrator = _get_orchestrator()
    
    if not orchestrator:
        logger.error("[COMPLIANCE] No LLM available")
        return ""
    
    try:
        # Use Claude for compliance analysis (text extraction, not SQL)
        result, success = orchestrator._call_claude(
            prompt=prompt,
            system_prompt=system_prompt or "You are a compliance analyst.",
            operation="compliance_check"
        )
        
        if success:
            logger.info(f"[COMPLIANCE] LLM response: {len(result)} chars")
            return result
        else:
            logger.error(f"[COMPLIANCE] LLM call failed: {result}")
            return ""
    
    except Exception as e:
        logger.error(f"[COMPLIANCE] LLM call failed: {e}")
        return ""


# =============================================================================
# SQL GENERATION
# =============================================================================

SQL_GENERATION_SYSTEM = """You are an expert SQL analyst. Your job is to translate compliance rules into SQL queries that can identify non-compliant records.

You will be given:
1. A compliance rule (what must be true)
2. The actual database schema (tables and columns that exist)
3. Column profiles (sample values, data types)

Generate SQL that:
- Uses only columns that ACTUALLY EXIST in the schema
- Handles data type conversions properly (TRY_CAST for safety)
- Returns the specific records that VIOLATE the rule
- Is compatible with DuckDB SQL syntax

Output ONLY valid JSON with the SQL query and explanation."""


SQL_GENERATION_PROMPT = """Generate a SQL query to find records that VIOLATE this compliance rule.

RULE:
Title: {rule_title}
Description: {rule_description}
Applies To: {applies_to}
Requirement: {requirement}

AVAILABLE SCHEMA:
{schema}

COLUMN PROFILES (sample values):
{profiles}

---

Return JSON in this exact format:
{{
  "sql_query": "SELECT ... FROM ... WHERE ...",
  "description": "What this query checks for",
  "expected_compliant": "Description of what compliant records look like",
  "violation_meaning": "What it means if records are returned"
}}

IMPORTANT:
- Query should return records that VIOLATE the rule (non-compliant)
- Use only columns that exist in the schema
- Use TRY_CAST for numeric comparisons
- Use ILIKE for text matching
- Return relevant columns for evidence (employee_number, name, etc.)
- Limit to 100 rows for performance

Return ONLY the JSON, no other text."""


def generate_compliance_sql(
    rule: Dict,
    schema: Dict,
    profiles: Dict
) -> Optional[ComplianceCheck]:
    """
    Generate SQL to check compliance with a rule.
    
    Uses LLM to intelligently map rule requirements to actual schema.
    """
    
    # Format schema for prompt
    schema_text = ""
    for table in schema.get("tables", []):
        table_name = table.get("table_name", "")
        columns = table.get("columns", [])
        col_list = ", ".join([c.get("column_name", "") for c in columns[:20]])  # Limit columns
        schema_text += f"\nTable: {table_name}\nColumns: {col_list}\n"
    
    # Format profiles for prompt
    profile_text = ""
    for col_name, profile in list(profiles.items())[:30]:  # Limit profiles
        distinct = profile.get("distinct_values", [])[:5]
        profile_text += f"\n{col_name}: {distinct}"
    
    prompt = SQL_GENERATION_PROMPT.format(
        rule_title=rule.get("title", ""),
        rule_description=rule.get("description", ""),
        applies_to=json.dumps(rule.get("applies_to", {})),
        requirement=json.dumps(rule.get("requirement", {})),
        schema=schema_text[:4000],
        profiles=profile_text[:2000]
    )
    
    response = _call_llm(prompt, SQL_GENERATION_SYSTEM)
    
    if not response:
        return None
    
    try:
        # Parse JSON from response
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            data = json.loads(json_match.group())
        else:
            logger.warning("[COMPLIANCE] No JSON found in SQL generation response")
            return None
        
        return ComplianceCheck(
            check_id=f"CHK_{rule.get('rule_id', 'unknown')}",
            rule_id=rule.get("rule_id", ""),
            rule_title=rule.get("title", ""),
            sql_query=data.get("sql_query", ""),
            description=data.get("description", ""),
            expected_result=data.get("violation_meaning", "Records returned indicate non-compliance"),
            severity=rule.get("severity", "medium"),
            category=rule.get("category", "general")
        )
        
    except Exception as e:
        logger.error(f"[COMPLIANCE] Failed to parse SQL generation response: {e}")
        return None


# =============================================================================
# FINDING GENERATION
# =============================================================================

FINDING_SYSTEM = """You are a senior compliance auditor preparing findings for executive review.

Your findings must follow the Five C's framework:
1. CONDITION - What we found (specific, quantified)
2. CRITERIA - What it should be (the standard/requirement)
3. CAUSE - Why it likely happened (root cause analysis)
4. CONSEQUENCE - Business/regulatory impact
5. CORRECTIVE ACTION - Specific steps to remediate

Be specific. Use numbers. Cite the source standard.
Write like a Big 4 audit firm - professional, thorough, actionable."""


FINDING_PROMPT = """Generate an auditor-quality finding based on these compliance check results.

RULE:
{rule}

CHECK RESULTS:
- Records returned: {record_count}
- Sample violations: {sample_records}

SOURCE DOCUMENT: {source_document}

---

Generate a finding in this JSON format:
{{
  "title": "Clear, specific title",
  "severity": "low|medium|high|critical",
  
  "condition": {{
    "summary": "What we found - specific and quantified",
    "details": "Additional context",
    "data_as_of": "{current_date}"
  }},
  
  "criteria": {{
    "standard": "Name of the standard/regulation",
    "requirement": "The specific requirement",
    "source_text": "Quote from the source document"
  }},
  
  "cause": {{
    "likely_reason": "Most probable root cause",
    "contributing_factors": ["Factor 1", "Factor 2"]
  }},
  
  "consequence": {{
    "risk_level": "Description of risk",
    "business_impact": "Impact on operations",
    "regulatory_impact": "Compliance/legal implications"
  }},
  
  "corrective_action": {{
    "immediate": "What to do now",
    "steps": ["Step 1", "Step 2", "Step 3"],
    "responsible_party": "Who should do this",
    "timeline": "Suggested timeline"
  }}
}}

Be specific and actionable. Return ONLY the JSON."""


def generate_finding(
    rule: Dict,
    check: ComplianceCheck,
    results: List[Dict],
    source_document: str
) -> Optional[Finding]:
    """
    Generate an auditor-quality finding from check results.
    """
    
    if not results:
        return None  # No finding if compliant
    
    # Prepare sample records (limit for prompt)
    sample_records = json.dumps(results[:5], indent=2, default=str)
    
    prompt = FINDING_PROMPT.format(
        rule=json.dumps(rule, indent=2),
        record_count=len(results),
        sample_records=sample_records,
        source_document=source_document,
        current_date=datetime.now().strftime("%Y-%m-%d")
    )
    
    response = _call_llm(prompt, FINDING_SYSTEM)
    
    if not response:
        # Generate basic finding without LLM
        return _generate_basic_finding(rule, check, results, source_document)
    
    try:
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            data = json.loads(json_match.group())
        else:
            return _generate_basic_finding(rule, check, results, source_document)
        
        finding_id = f"FND_{rule.get('rule_id', 'unknown')}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        return Finding(
            finding_id=finding_id,
            title=data.get("title", check.rule_title),
            severity=data.get("severity", rule.get("severity", "medium")),
            category=rule.get("category", "general"),
            condition=data.get("condition", {}),
            criteria=data.get("criteria", {}),
            cause=data.get("cause", {}),
            consequence=data.get("consequence", {}),
            corrective_action=data.get("corrective_action", {}),
            evidence={
                "affected_records": results[:20],  # Limit evidence
                "total_count": len(results),
                "sql_query": check.sql_query
            },
            rule_id=rule.get("rule_id", ""),
            source_document=source_document,
            source_page=rule.get("source_page")
        )
        
    except Exception as e:
        logger.error(f"[COMPLIANCE] Failed to generate finding: {e}")
        return _generate_basic_finding(rule, check, results, source_document)


def _generate_basic_finding(
    rule: Dict,
    check: ComplianceCheck,
    results: List[Dict],
    source_document: str
) -> Finding:
    """Generate a basic finding when LLM is unavailable."""
    
    finding_id = f"FND_{rule.get('rule_id', 'unknown')}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    return Finding(
        finding_id=finding_id,
        title=f"Non-compliance: {check.rule_title}",
        severity=rule.get("severity", "medium"),
        category=rule.get("category", "general"),
        condition={
            "summary": f"{len(results)} records do not comply with requirement",
            "details": check.description,
            "data_as_of": datetime.now().strftime("%Y-%m-%d")
        },
        criteria={
            "standard": source_document,
            "requirement": rule.get("description", ""),
            "source_text": rule.get("source_text", "")
        },
        cause={
            "likely_reason": "Requires investigation",
            "contributing_factors": []
        },
        consequence={
            "risk_level": rule.get("severity", "medium"),
            "business_impact": "Review required",
            "regulatory_impact": "Potential non-compliance"
        },
        corrective_action={
            "immediate": "Review affected records",
            "steps": ["Identify root cause", "Remediate data", "Verify correction"],
            "responsible_party": "Data owner",
            "timeline": "As soon as practical"
        },
        evidence={
            "affected_records": results[:20],
            "total_count": len(results),
            "sql_query": check.sql_query
        },
        rule_id=rule.get("rule_id", ""),
        source_document=source_document,
        source_page=rule.get("source_page")
    )


# =============================================================================
# COMPLIANCE ENGINE
# =============================================================================

class ComplianceEngine:
    """
    The main compliance checking engine.
    
    Orchestrates:
    1. Getting rules from the registry
    2. Getting schema/profiles from the database
    3. Generating SQL checks
    4. Running checks against data
    5. Generating findings
    """
    
    def __init__(self, db_handler=None):
        self.db_handler = db_handler
        self._schema_cache: Dict[str, Dict] = {}
        self._profile_cache: Dict[str, Dict] = {}
    
    def set_db_handler(self, handler):
        """Set the database handler."""
        self.db_handler = handler
    
    def get_schema(self, project_id: str) -> Dict:
        """Get schema for a project."""
        if project_id in self._schema_cache:
            return self._schema_cache[project_id]
        
        if not self.db_handler:
            return {"tables": []}
        
        try:
            # Get schema from handler
            if hasattr(self.db_handler, 'get_schema'):
                schema = self.db_handler.get_schema(project_id)
            else:
                schema = {"tables": []}
            
            self._schema_cache[project_id] = schema
            return schema
            
        except Exception as e:
            logger.error(f"[COMPLIANCE] Failed to get schema: {e}")
            return {"tables": []}
    
    def get_profiles(self, project_id: str) -> Dict:
        """Get column profiles for a project."""
        if project_id in self._profile_cache:
            return self._profile_cache[project_id]
        
        if not self.db_handler:
            return {}
        
        try:
            # Try to get profiles from _column_profiles table
            if hasattr(self.db_handler, 'conn') and self.db_handler.conn:
                result = self.db_handler.conn.execute(f"""
                    SELECT column_name, distinct_values, data_type, filter_category
                    FROM _column_profiles
                    WHERE table_name LIKE '{project_id[:8].lower()}%'
                    LIMIT 200
                """).fetchall()
                
                profiles = {}
                for row in result:
                    col_name = row[0]
                    try:
                        distinct = json.loads(row[1]) if row[1] else []
                    except:
                        distinct = []
                    profiles[col_name] = {
                        "distinct_values": distinct,
                        "data_type": row[2],
                        "filter_category": row[3]
                    }
                
                self._profile_cache[project_id] = profiles
                return profiles
                
        except Exception as e:
            logger.warning(f"[COMPLIANCE] Failed to get profiles: {e}")
        
        return {}
    
    def run_check(self, check: ComplianceCheck, project_id: str) -> List[Dict]:
        """Run a compliance check and return results."""
        if not self.db_handler or not check.sql_query:
            return []
        
        try:
            if hasattr(self.db_handler, 'conn') and self.db_handler.conn:
                result = self.db_handler.conn.execute(check.sql_query).fetchall()
                
                # Get column names
                description = self.db_handler.conn.description
                columns = [d[0] for d in description] if description else []
                
                # Convert to list of dicts
                records = []
                for row in result:
                    record = {}
                    for i, val in enumerate(row):
                        col = columns[i] if i < len(columns) else f"col_{i}"
                        record[col] = val
                    records.append(record)
                
                return records
                
        except Exception as e:
            logger.error(f"[COMPLIANCE] Check execution failed: {e}")
            logger.error(f"[COMPLIANCE] SQL was: {check.sql_query}")
        
        return []
    
    def check_rule(
        self, 
        rule: Dict, 
        project_id: str,
        source_document: str = "Standards"
    ) -> Optional[Finding]:
        """
        Check a single rule against project data.
        
        Returns a Finding if non-compliant, None if compliant.
        """
        
        # Get schema and profiles
        schema = self.get_schema(project_id)
        profiles = self.get_profiles(project_id)
        
        if not schema.get("tables"):
            logger.warning(f"[COMPLIANCE] No schema available for {project_id}")
            return None
        
        # Generate SQL check
        check = generate_compliance_sql(rule, schema, profiles)
        
        if not check or not check.sql_query:
            logger.warning(f"[COMPLIANCE] Could not generate SQL for rule {rule.get('rule_id')}")
            return None
        
        logger.info(f"[COMPLIANCE] Running check: {check.description}")
        
        # Run the check
        results = self.run_check(check, project_id)
        
        if not results:
            logger.info(f"[COMPLIANCE] Rule {rule.get('rule_id')}: COMPLIANT")
            return None
        
        logger.info(f"[COMPLIANCE] Rule {rule.get('rule_id')}: {len(results)} violations found")
        
        # Generate finding
        finding = generate_finding(rule, check, results, source_document)
        
        return finding
    
    def run_compliance_scan(
        self,
        project_id: str,
        rules: List[Dict] = None,
        domain: str = None
    ) -> List[Finding]:
        """
        Run a full compliance scan against a project.
        
        Args:
            project_id: The project to scan
            rules: Specific rules to check (optional)
            domain: Filter rules by domain (optional)
        
        Returns:
            List of findings for non-compliant items
        """
        
        # Get rules from registry if not provided
        if rules is None:
            try:
                from backend.utils.standards_processor import get_rule_registry
            except ImportError:
                try:
                    from utils.standards_processor import get_rule_registry
                except ImportError:
                    logger.error("[COMPLIANCE] Standards processor not available")
                    return []
            
            try:
                registry = get_rule_registry()
                
                if domain:
                    rules = [r.to_dict() for r in registry.get_rules_by_domain(domain)]
                else:
                    rules = [r.to_dict() for r in registry.get_all_rules()]
                    
            except Exception as e:
                logger.error(f"[COMPLIANCE] Failed to get rules: {e}")
                return []
        
        if not rules:
            logger.warning("[COMPLIANCE] No rules to check")
            return []
        
        logger.info(f"[COMPLIANCE] Starting scan of {project_id} with {len(rules)} rules")
        
        findings = []
        
        for rule in rules:
            try:
                finding = self.check_rule(
                    rule, 
                    project_id,
                    source_document=rule.get("source_document", "Standards")
                )
                
                if finding:
                    findings.append(finding)
                    
            except Exception as e:
                logger.error(f"[COMPLIANCE] Error checking rule {rule.get('rule_id')}: {e}")
        
        logger.info(f"[COMPLIANCE] Scan complete: {len(findings)} findings")
        
        return findings


# =============================================================================
# SINGLETON
# =============================================================================

_compliance_engine: Optional[ComplianceEngine] = None

def get_compliance_engine() -> ComplianceEngine:
    """Get the singleton compliance engine."""
    global _compliance_engine
    if _compliance_engine is None:
        _compliance_engine = ComplianceEngine()
    return _compliance_engine


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def run_compliance_check(
    project_id: str,
    domain: str = None
) -> List[Dict]:
    """
    Run a compliance check on a project.
    
    Returns list of findings as dicts.
    """
    engine = get_compliance_engine()
    findings = engine.run_compliance_scan(project_id, domain=domain)
    return [f.to_dict() for f in findings]


def run_compliance_scan(
    project_id: str,
    rules: List[Dict] = None,
    domain: str = None
) -> List[Dict]:
    """
    Run a compliance scan with specific rules.
    
    Args:
        project_id: The project to scan
        rules: List of rule dicts to check
        domain: Optional domain filter
    
    Returns list of findings as dicts.
    """
    engine = get_compliance_engine()
    findings = engine.run_compliance_scan(project_id, rules=rules, domain=domain)
    return [f.to_dict() for f in findings]


def check_single_rule(
    rule: Dict,
    project_id: str,
    db_handler = None
) -> Optional[Dict]:
    """
    Check a single rule against project data.
    
    Returns finding dict if non-compliant, None if compliant.
    """
    engine = get_compliance_engine()
    
    if db_handler:
        engine.set_db_handler(db_handler)
    
    finding = engine.check_rule(rule, project_id)
    return finding.to_dict() if finding else None
