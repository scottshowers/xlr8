"""
XLR8 COMPLIANCE ENGINE v2.0
===========================

Runs extracted rules against customer data to identify compliance gaps.
Uses INTELLIGENT FIELD MATCHING - same scoring patterns as TableSelector.

v2.0 CHANGES:
- Added FieldMatcher class for intelligent column matching
- No longer relies on LLM to guess field→column mappings
- Uses TableSelector-style scoring: name match, value match, type match
- Provides explicit field mappings to LLM for SQL generation
- Much better skip messages when fields can't be mapped

The engine:
1. Takes a rule (from standards_processor)
2. Extracts all fields from applies_to and requirement
3. Uses FieldMatcher to find best column matches for each field
4. Passes explicit field→column mappings to LLM
5. Executes generated SQL against DuckDB
6. Generates auditor-quality findings

Deploy to: backend/utils/compliance_engine.py

Author: XLR8 Team
Version: 2.0.0 - Uses FieldMatcher pattern
"""

import os
import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple, Set
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
    
    # Field mappings used
    field_mappings: Dict[str, str] = field(default_factory=dict)
    
    # Metadata
    severity: str = "medium"
    category: str = "general"


@dataclass 
class Finding:
    """
    An auditor-quality finding following the Five C's framework.
    """
    finding_id: str
    title: str
    severity: str  # low, medium, high, critical
    category: str
    
    # THE FIVE C's
    condition: Dict[str, Any]
    criteria: Dict[str, Any]
    cause: Dict[str, Any]
    consequence: Dict[str, Any]
    corrective_action: Dict[str, Any]
    
    # EVIDENCE
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
# FIELD MATCHER - TableSelector-style scoring for columns
# =============================================================================

class FieldMatcher:
    """
    Matches rule fields to actual database columns.
    
    Uses the same scoring patterns as TableSelector:
    - Name matching (fuzzy, singular/plural)
    - Value matching (checks column profiles for matching values)
    - Type matching (numeric fields to numeric columns, etc.)
    
    This is the core fix for compliance - we can't rely on LLM to guess mappings.
    """
    
    # Common synonyms for field matching
    FIELD_SYNONYMS = {
        'age': ['age', 'birth', 'dob', 'date_of_birth', 'birthday', 'born'],
        'wage': ['wage', 'wages', 'salary', 'earnings', 'compensation', 'pay', 'income'],
        'fica': ['fica', 'social_security', 'ss', 'oasdi', 'medicare'],
        'contribution': ['contribution', 'contrib', 'deferral', 'deduction'],
        'roth': ['roth', 'after_tax', 'aftertax'],
        'employee': ['employee', 'emp', 'ee', 'worker', 'staff', 'associate'],
        'number': ['number', 'num', 'no', 'id', 'identifier', 'code'],
        'name': ['name', 'first_name', 'last_name', 'full_name'],
        'tax': ['tax', 'withholding', 'deduction'],
        'type': ['type', 'category', 'class', 'kind'],
    }
    
    def __init__(self, db_handler=None):
        self.db_handler = db_handler
        self._column_cache: Dict[str, List[Dict]] = {}
        self._profile_cache: Dict[str, Dict] = {}
    
    def get_all_columns(self, project_id: str) -> List[Dict]:
        """Get all columns for a project with their metadata."""
        if project_id in self._column_cache:
            return self._column_cache[project_id]
        
        if not self.db_handler or not hasattr(self.db_handler, 'conn'):
            return []
        
        columns = []
        try:
            # Get columns from _column_profiles which has more info
            project_prefix = project_id[:8].lower() if project_id else ''
            
            result = self.db_handler.conn.execute("""
                SELECT table_name, column_name, inferred_type, distinct_values, filter_category
                FROM _column_profiles
                WHERE LOWER(table_name) LIKE ? || '%'
            """, [project_prefix]).fetchall()
            
            for row in result:
                columns.append({
                    'table_name': row[0],
                    'column_name': row[1],
                    'inferred_type': row[2],
                    'distinct_values': row[3],
                    'filter_category': row[4]
                })
            
            self._column_cache[project_id] = columns
            logger.warning(f"[FIELD-MATCH] Loaded {len(columns)} columns for project {project_id}")
            
        except Exception as e:
            logger.error(f"[FIELD-MATCH] Failed to load columns: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        return columns
    
    def _normalize(self, text: str) -> str:
        """Normalize text for matching."""
        if not text:
            return ''
        # Lowercase, replace separators with underscores
        text = text.lower().strip()
        text = re.sub(r'[\s\-\.]+', '_', text)
        # Remove common noise words
        text = re.sub(r'^(the|a|an)_', '', text)
        return text
    
    def _get_synonyms(self, word: str) -> Set[str]:
        """Get all synonyms for a word."""
        word = word.lower()
        synonyms = {word}
        
        # Check if word matches any synonym group
        for key, syn_list in self.FIELD_SYNONYMS.items():
            if word in syn_list or key in word:
                synonyms.update(syn_list)
        
        # Add singular/plural variants
        if word.endswith('s') and len(word) > 3:
            synonyms.add(word[:-1])
        else:
            synonyms.add(word + 's')
        
        return synonyms
    
    def score_column(self, field_name: str, column: Dict) -> Tuple[int, str]:
        """
        Score how well a column matches a field name.
        
        Returns (score, reason).
        Higher scores = better match.
        """
        field_norm = self._normalize(field_name)
        col_name = self._normalize(column.get('column_name', ''))
        
        if not field_norm or not col_name:
            return 0, "empty"
        
        score = 0
        reasons = []
        
        # Split into words
        field_words = set(field_norm.split('_'))
        col_words = set(col_name.split('_'))
        
        # Get synonyms for all field words
        field_synonyms = set()
        for word in field_words:
            field_synonyms.update(self._get_synonyms(word))
        
        # =================================================================
        # NAME MATCHING
        # =================================================================
        
        # Exact match (very rare but perfect)
        if field_norm == col_name:
            score += 200
            reasons.append("exact_match")
        
        # Field is substring of column
        elif field_norm in col_name:
            score += 150
            reasons.append("field_in_col")
        
        # Column is substring of field (less ideal)
        elif col_name in field_norm:
            score += 100
            reasons.append("col_in_field")
        
        # Word-level matching
        else:
            # Direct word matches
            direct_matches = field_words & col_words
            if direct_matches:
                score += 50 * len(direct_matches)
                reasons.append(f"word_match:{','.join(direct_matches)}")
            
            # Synonym matches
            synonym_matches = field_synonyms & col_words
            if synonym_matches:
                score += 30 * len(synonym_matches)
                reasons.append(f"synonym:{','.join(synonym_matches)}")
        
        # =================================================================
        # TYPE MATCHING
        # =================================================================
        
        inferred_type = (column.get('inferred_type') or '').lower()
        
        # If field looks numeric, boost numeric columns
        numeric_indicators = {'amount', 'rate', 'count', 'total', 'sum', 'wage', 'salary', 'age', 'years'}
        if any(ind in field_norm for ind in numeric_indicators):
            if inferred_type in ('numeric', 'integer', 'float', 'decimal', 'number'):
                score += 30
                reasons.append("type_numeric")
        
        # If field looks like date, boost date columns
        date_indicators = {'date', 'birth', 'hired', 'start', 'end', 'effective'}
        if any(ind in field_norm for ind in date_indicators):
            if inferred_type in ('date', 'datetime', 'timestamp'):
                score += 30
                reasons.append("type_date")
        
        # =================================================================
        # VALUE MATCHING (check if field value appears in column data)
        # =================================================================
        
        distinct_values = column.get('distinct_values')
        if distinct_values:
            try:
                values = json.loads(distinct_values) if isinstance(distinct_values, str) else distinct_values
                for val_info in (values or [])[:20]:  # Check top 20 values
                    val = str(val_info.get('value', val_info) if isinstance(val_info, dict) else val_info).lower()
                    
                    # Check if any field word appears in values
                    for word in field_words:
                        if len(word) >= 3 and word in val:
                            score += 40
                            reasons.append(f"value_match:{word}")
                            break
            except (json.JSONDecodeError, TypeError):
                pass
        
        reason = '+'.join(reasons) if reasons else 'no_match'
        return score, reason
    
    def match_field(self, field_name: str, columns: List[Dict], min_score: int = 30) -> Optional[Dict]:
        """
        Find the best matching column for a field.
        
        Returns column dict with added 'match_score' and 'match_reason'.
        Returns None if no column scores above min_score.
        """
        best_match = None
        best_score = 0
        best_reason = ""
        
        for col in columns:
            score, reason = self.score_column(field_name, col)
            if score > best_score and score >= min_score:
                best_score = score
                best_match = col.copy()
                best_reason = reason
        
        if best_match:
            best_match['match_score'] = best_score
            best_match['match_reason'] = best_reason
            logger.warning(f"[FIELD-MATCH] '{field_name}' → {best_match['table_name']}.{best_match['column_name']} "
                         f"(score={best_score}, {best_reason})")
        else:
            logger.warning(f"[FIELD-MATCH] '{field_name}' → NO MATCH (best score below {min_score})")
        
        return best_match
    
    def match_rule_fields(self, rule: Dict, project_id: str) -> Dict[str, Dict]:
        """
        Extract all fields from a rule and find their best column matches.
        
        Returns: {field_name: column_info} for all matched fields
        """
        columns = self.get_all_columns(project_id)
        if not columns:
            logger.warning(f"[FIELD-MATCH] No columns found for project {project_id}")
            return {}
        
        # Extract fields from rule
        fields_to_match = set()
        
        # From applies_to.conditions
        applies_to = rule.get('applies_to', {})
        for condition in applies_to.get('conditions', []):
            if 'field' in condition:
                fields_to_match.add(condition['field'])
        
        # From requirement.checks
        requirement = rule.get('requirement', {})
        for check in requirement.get('checks', []):
            if 'field' in check:
                fields_to_match.add(check['field'])
        
        logger.warning(f"[FIELD-MATCH] Rule {rule.get('rule_id')} has {len(fields_to_match)} fields: {fields_to_match}")
        
        # Match each field
        mappings = {}
        for field_name in fields_to_match:
            match = self.match_field(field_name, columns)
            if match:
                mappings[field_name] = match
        
        return mappings


# =============================================================================
# LLM INTEGRATION
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
        result, success = orchestrator._call_claude(
            prompt=prompt,
            system_prompt=system_prompt or "You are a compliance analyst.",
            operation="compliance_check"
        )
        
        if success:
            return result
        else:
            logger.error(f"[COMPLIANCE] LLM call failed: {result}")
            return ""
    
    except Exception as e:
        logger.error(f"[COMPLIANCE] LLM call failed: {e}")
        return ""


# =============================================================================
# SQL GENERATION - Now with field mappings!
# =============================================================================

SQL_GENERATION_PROMPT = """Generate a SQL query to find records that VIOLATE this compliance rule.

RULE:
Title: {rule_title}
Description: {rule_description}

FIELD MAPPINGS (rule field → actual database column):
{field_mappings}

APPLIES TO:
{applies_to}

REQUIREMENT:
{requirement}

AVAILABLE TABLES:
{tables}

---

Generate DuckDB-compatible SQL that:
1. Uses the EXACT column names from the field mappings
2. Returns records that VIOLATE the rule (non-compliant)
3. Includes relevant identifier columns (employee_number, name, etc.)
4. Limits to 100 rows

Return ONLY the SQL query, nothing else.
If the rule cannot be checked with the mapped columns, respond with: CANNOT_CHECK

IMPORTANT:
- Use TRY_CAST for numeric comparisons
- Use ILIKE for text matching
- For age calculations: DATEDIFF('year', birth_date_column, CURRENT_DATE)
"""


def generate_compliance_sql(
    rule: Dict,
    schema: Dict,
    profiles: Dict,
    field_mappings: Dict[str, Dict]
) -> Optional[ComplianceCheck]:
    """
    Generate SQL to check compliance with a rule.
    
    Now uses pre-computed field mappings instead of hoping LLM guesses correctly.
    """
    
    if not field_mappings:
        logger.warning(f"[COMPLIANCE] No field mappings for rule {rule.get('rule_id')}")
        return None
    
    # Format field mappings for prompt
    mapping_text = ""
    for field_name, col_info in field_mappings.items():
        mapping_text += f"- '{field_name}' → {col_info['table_name']}.{col_info['column_name']}\n"
    
    # Format tables
    tables_text = ""
    for table in schema.get("tables", [])[:10]:  # Limit to 10 tables
        table_name = table.get("table_name", "")
        columns = table.get("columns", [])
        col_names = [c.get("column_name", c) if isinstance(c, dict) else c for c in columns[:20]]
        tables_text += f"\nTable: {table_name}\nColumns: {', '.join(col_names)}\n"
    
    # Build prompt
    prompt = SQL_GENERATION_PROMPT.format(
        rule_title=rule.get("title", "Unknown"),
        rule_description=rule.get("description", ""),
        field_mappings=mapping_text,
        applies_to=json.dumps(rule.get("applies_to", {}), indent=2),
        requirement=json.dumps(rule.get("requirement", {}), indent=2),
        tables=tables_text
    )
    
    # Use LLMOrchestrator.generate_sql()
    orchestrator = _get_orchestrator()
    if not orchestrator:
        logger.error("[COMPLIANCE] No LLM orchestrator available")
        return None
    
    # Get all column names for validation
    all_columns = set()
    for col_info in field_mappings.values():
        all_columns.add(col_info['column_name'])
    for table in schema.get("tables", []):
        for col in table.get("columns", []):
            col_name = col.get("column_name", col) if isinstance(col, dict) else col
            all_columns.add(col_name)
    
    result = orchestrator.generate_sql(prompt, schema_columns=all_columns)
    
    if not result.get('success') or not result.get('sql'):
        logger.warning(f"[COMPLIANCE] SQL generation failed for rule {rule.get('rule_id')}: {result.get('error')}")
        return None
    
    sql = result.get('sql', '')
    
    # Check if LLM said it can't check this rule
    if 'CANNOT_CHECK' in sql.upper() or not sql.strip().upper().startswith(('SELECT', 'WITH')):
        logger.warning(f"[COMPLIANCE] Rule {rule.get('rule_id')} cannot be checked with available columns")
        return None
    
    return ComplianceCheck(
        check_id=f"CHK_{rule.get('rule_id', 'unknown')}",
        rule_id=rule.get("rule_id", ""),
        rule_title=rule.get("title", ""),
        sql_query=sql,
        description=f"Check for violations of: {rule.get('title', 'rule')}",
        expected_result="Records returned indicate non-compliance",
        field_mappings={k: f"{v['table_name']}.{v['column_name']}" for k, v in field_mappings.items()},
        severity=rule.get("severity", "medium"),
        category=rule.get("category", "general")
    )


# =============================================================================
# FINDING GENERATION
# =============================================================================

FINDING_PROMPT = """Generate an auditor-quality finding based on these compliance check results.

RULE:
{rule}

CHECK RESULTS:
- Records returned: {record_count}
- Sample violations: {sample_records}
- Field mappings used: {field_mappings}

SOURCE DOCUMENT: {source_document}

---

Generate a finding in this JSON format:
{{
  "title": "Clear, specific title",
  "severity": "{severity}",
  
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
    """Generate an auditor-quality finding from check results."""
    
    if not results:
        return None
    
    sample_records = json.dumps(results[:5], indent=2, default=str)
    
    prompt = FINDING_PROMPT.format(
        rule=json.dumps(rule, indent=2),
        record_count=len(results),
        sample_records=sample_records,
        field_mappings=json.dumps(check.field_mappings, indent=2),
        source_document=source_document,
        severity=rule.get("severity", "medium"),
        current_date=datetime.now().strftime("%Y-%m-%d")
    )
    
    response = _call_llm(prompt, "You are a senior compliance auditor preparing findings for executive review.")
    
    if not response:
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
            title=data.get("title", rule.get("title", "Compliance Finding")),
            severity=data.get("severity", rule.get("severity", "medium")),
            category=rule.get("category", "general"),
            condition=data.get("condition", {"summary": f"{len(results)} violations found"}),
            criteria=data.get("criteria", {"requirement": rule.get("description", "")}),
            cause=data.get("cause", {"likely_reason": "To be investigated"}),
            consequence=data.get("consequence", {"risk_level": "To be assessed"}),
            corrective_action=data.get("corrective_action", {"immediate": "Review findings"}),
            evidence={
                "record_count": len(results),
                "sample_records": results[:5],
                "sql_query": check.sql_query,
                "field_mappings": check.field_mappings
            },
            rule_id=rule.get("rule_id", ""),
            source_document=source_document
        )
        
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"[COMPLIANCE] Failed to parse finding response: {e}")
        return _generate_basic_finding(rule, check, results, source_document)


def _generate_basic_finding(
    rule: Dict,
    check: ComplianceCheck,
    results: List[Dict],
    source_document: str
) -> Finding:
    """Generate a basic finding without LLM."""
    
    finding_id = f"FND_{rule.get('rule_id', 'unknown')}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    return Finding(
        finding_id=finding_id,
        title=f"Non-compliance: {rule.get('title', 'Unknown Rule')}",
        severity=rule.get("severity", "medium"),
        category=rule.get("category", "general"),
        condition={
            "summary": f"{len(results)} records violate this rule",
            "details": check.description,
            "data_as_of": datetime.now().strftime("%Y-%m-%d")
        },
        criteria={
            "standard": source_document,
            "requirement": rule.get("description", "See rule details"),
            "source_text": rule.get("source_text", "")
        },
        cause={
            "likely_reason": "Configuration or data does not meet requirements",
            "contributing_factors": ["Missing configuration", "Data quality issues"]
        },
        consequence={
            "risk_level": rule.get("severity", "medium"),
            "business_impact": "Potential compliance issues",
            "regulatory_impact": "Review required"
        },
        corrective_action={
            "immediate": "Review flagged records",
            "steps": [
                "Review sample violations",
                "Identify root cause",
                "Update configuration or data",
                "Re-run compliance check"
            ],
            "responsible_party": "Compliance team",
            "timeline": "Within 30 days"
        },
        evidence={
            "record_count": len(results),
            "sample_records": results[:5],
            "sql_query": check.sql_query,
            "field_mappings": check.field_mappings
        },
        rule_id=rule.get("rule_id", ""),
        source_document=source_document
    )


# =============================================================================
# COMPLIANCE ENGINE CLASS
# =============================================================================

class ComplianceEngine:
    """
    Main compliance engine that orchestrates rule checking.
    
    v2.0: Uses FieldMatcher for intelligent column matching.
    """
    
    def __init__(self, db_handler=None):
        self.db_handler = db_handler
        self.field_matcher = FieldMatcher(db_handler)
        self._schema_cache: Dict[str, Dict] = {}
        self._profile_cache: Dict[str, Dict] = {}
        self._last_check_results: List[Dict] = []
    
    def set_db_handler(self, handler):
        """Set the database handler."""
        self.db_handler = handler
        self.field_matcher.db_handler = handler
    
    def get_schema(self, project_id: str) -> Dict:
        """Get schema for a project."""
        if project_id in self._schema_cache:
            return self._schema_cache[project_id]
        
        if not self.db_handler:
            logger.warning("[COMPLIANCE] No db_handler - cannot get schema")
            return {"tables": []}
        
        try:
            raw_schema = self.db_handler.get_schema(project_id)
            
            tables = []
            for table_name, table_info in raw_schema.items():
                columns = table_info.get("columns", [])
                if columns and isinstance(columns[0], str):
                    columns = [{"column_name": c} for c in columns]
                
                tables.append({
                    "table_name": table_name,
                    "display_name": table_info.get("display_name", table_name),
                    "columns": columns,
                    "row_count": table_info.get("row_count", 0)
                })
            
            schema = {"tables": tables}
            self._schema_cache[project_id] = schema
            logger.warning(f"[COMPLIANCE] Loaded schema for {project_id}: {len(tables)} tables")
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
            if hasattr(self.db_handler, 'conn') and self.db_handler.conn:
                project_prefix = project_id[:8].lower() if project_id else ''
                result = self.db_handler.conn.execute("""
                    SELECT column_name, distinct_values, inferred_type, filter_category
                    FROM _column_profiles
                    WHERE LOWER(table_name) LIKE ? || '%'
                    LIMIT 200
                """, [project_prefix]).fetchall()
                
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
                logger.warning(f"[COMPLIANCE] Loaded {len(profiles)} column profiles for {project_id}")
                return profiles
                
        except Exception as e:
            logger.error(f"[COMPLIANCE] Failed to get profiles: {e}")
        
        return {}
    
    def run_check(self, check: ComplianceCheck, project_id: str) -> List[Dict]:
        """Execute a compliance check and return violations."""
        if not self.db_handler or not check.sql_query:
            return []
        
        try:
            results = self.db_handler.conn.execute(check.sql_query).fetchall()
            columns = [desc[0] for desc in self.db_handler.conn.description]
            
            violations = []
            for row in results[:100]:
                violations.append(dict(zip(columns, row)))
            
            logger.warning(f"[COMPLIANCE] Check {check.check_id}: {len(violations)} violations found")
            return violations
            
        except Exception as e:
            logger.error(f"[COMPLIANCE] SQL execution failed for {check.check_id}: {e}")
            raise
    
    def check_rule(self, rule: Dict, project_id: str) -> Optional[Finding]:
        """Check a single rule against project data."""
        schema = self.get_schema(project_id)
        profiles = self.get_profiles(project_id)
        
        if not schema.get("tables"):
            return None
        
        # Get field mappings using FieldMatcher
        field_mappings = self.field_matcher.match_rule_fields(rule, project_id)
        
        if not field_mappings:
            logger.warning(f"[COMPLIANCE] No field mappings found for rule {rule.get('rule_id')}")
            return None
        
        check = generate_compliance_sql(rule, schema, profiles, field_mappings)
        
        if not check:
            return None
        
        try:
            results = self.run_check(check, project_id)
            if results:
                return generate_finding(rule, check, results, rule.get("source_document", "Standards"))
        except Exception as e:
            logger.error(f"[COMPLIANCE] Check execution failed: {e}")
        
        return None
    
    def run_compliance_scan(
        self,
        project_id: str,
        rules: List[Dict] = None,
        domain: str = None
    ) -> List[Finding]:
        """Run a full compliance scan against a project."""
        
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
        
        logger.warning(f"[COMPLIANCE] Starting scan of {project_id} with {len(rules)} rules")
        
        # Pre-load schema and profiles
        schema = self.get_schema(project_id)
        profiles = self.get_profiles(project_id)
        
        if not schema.get("tables"):
            logger.error(f"[COMPLIANCE] No schema available for project {project_id}")
            self._last_check_results = [{
                'rule_id': r.get('rule_id', 'unknown'),
                'rule_title': r.get('title', 'Untitled'),
                'status': 'skipped',
                'message': 'No schema available for project'
            } for r in rules]
            return []
        
        findings = []
        check_results = []
        
        for rule in rules:
            rule_result = {
                'rule_id': rule.get('rule_id', 'unknown'),
                'rule_title': rule.get('title', 'Untitled'),
                'status': 'pending',
                'sql_generated': None,
                'sql_error': None,
                'result_count': None,
                'message': None,
                'field_mappings': None
            }
            
            try:
                # Get field mappings using FieldMatcher
                field_mappings = self.field_matcher.match_rule_fields(rule, project_id)
                
                if not field_mappings:
                    rule_result['status'] = 'skipped'
                    rule_result['message'] = 'No matching columns found for rule fields'
                    
                    # Extract fields for better error message
                    fields = set()
                    for cond in rule.get('applies_to', {}).get('conditions', []):
                        if 'field' in cond:
                            fields.add(cond['field'])
                    for check in rule.get('requirement', {}).get('checks', []):
                        if 'field' in check:
                            fields.add(check['field'])
                    
                    if fields:
                        rule_result['message'] = f"No matching columns for fields: {', '.join(fields)}"
                    
                    check_results.append(rule_result)
                    continue
                
                rule_result['field_mappings'] = {k: f"{v['table_name']}.{v['column_name']}" 
                                                  for k, v in field_mappings.items()}
                
                # Generate SQL check
                check = generate_compliance_sql(rule, schema, profiles, field_mappings)
                
                if not check or not check.sql_query:
                    rule_result['status'] = 'skipped'
                    rule_result['message'] = 'Could not generate SQL for this rule'
                    check_results.append(rule_result)
                    continue
                
                rule_result['sql_generated'] = check.sql_query
                
                # Run the check
                try:
                    results = self.run_check(check, project_id)
                    rule_result['result_count'] = len(results)
                    
                    if results:
                        rule_result['status'] = 'failed'
                        rule_result['message'] = f'{len(results)} violations found'
                        finding = generate_finding(rule, check, results, rule.get("source_document", "Standards"))
                        if finding:
                            findings.append(finding)
                    else:
                        rule_result['status'] = 'passed'
                        rule_result['message'] = 'No violations found'
                        
                except Exception as sql_err:
                    rule_result['status'] = 'error'
                    rule_result['sql_error'] = str(sql_err)
                    rule_result['message'] = f'SQL execution failed: {sql_err}'
                    
            except Exception as e:
                rule_result['status'] = 'error'
                rule_result['message'] = f'Check failed: {e}'
                logger.error(f"[COMPLIANCE] Error checking rule {rule.get('rule_id')}: {e}")
            
            check_results.append(rule_result)
        
        self._last_check_results = check_results
        
        # Summary logging
        passed = len([r for r in check_results if r['status'] == 'passed'])
        failed = len([r for r in check_results if r['status'] == 'failed'])
        skipped = len([r for r in check_results if r['status'] == 'skipped'])
        errors = len([r for r in check_results if r['status'] == 'error'])
        
        logger.warning(f"[COMPLIANCE] Scan complete: {passed} passed, {failed} failed, {skipped} skipped, {errors} errors")
        
        return findings


# =============================================================================
# SINGLETON
# =============================================================================

_compliance_engine: Optional[ComplianceEngine] = None

def get_compliance_engine() -> ComplianceEngine:
    """Get the singleton compliance engine with proper DB handler."""
    global _compliance_engine
    if _compliance_engine is None:
        try:
            from utils.structured_data_handler import get_structured_handler
        except ImportError:
            from backend.utils.structured_data_handler import get_structured_handler
        
        handler = get_structured_handler()
        _compliance_engine = ComplianceEngine(db_handler=handler)
        logger.info("[COMPLIANCE] Engine initialized with StructuredDataHandler")
    return _compliance_engine


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def run_compliance_check(
    project_id: str,
    domain: str = None
) -> List[Dict]:
    """Run a compliance check on a project."""
    engine = get_compliance_engine()
    findings = engine.run_compliance_scan(project_id, domain=domain)
    return [f.to_dict() for f in findings]


def run_compliance_scan(
    project_id: str,
    rules: List[Dict] = None,
    domain: str = None
) -> Dict:
    """
    Run a compliance scan with specific rules.
    
    Returns dict with:
        - findings: List of finding dicts
        - check_results: Per-rule status details
    """
    engine = get_compliance_engine()
    findings = engine.run_compliance_scan(project_id, rules=rules, domain=domain)
    
    check_results = getattr(engine, '_last_check_results', [])
    
    return {
        'findings': [f.to_dict() for f in findings] if findings else [],
        'check_results': check_results
    }


def check_single_rule(
    rule: Dict,
    project_id: str,
    db_handler = None
) -> Optional[Dict]:
    """Check a single rule against project data."""
    engine = get_compliance_engine()
    
    if db_handler:
        engine.set_db_handler(db_handler)
    
    finding = engine.check_rule(rule, project_id)
    return finding.to_dict() if finding else None
