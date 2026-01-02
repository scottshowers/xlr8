"""
XLR8 COMPLIANCE ENGINE v3.0 - READS FROM _column_mappings
=========================================================

THE RIGHT WAY:
- READS semantic types from _column_mappings (populated at upload)
- NO runtime scoring or string matching
- Uses DERIVED_FIELDS for calculated values (age from birth_date)

This is how compliance should work:
1. Rule says: check if employees over age 50 with wages > $145K...
2. Engine looks up "age" → finds birth_date semantic type → knows to calculate age
3. Engine looks up "wages" → finds fica_wages semantic type → maps to actual column
4. Generates SQL with actual column names
5. Runs SQL and produces findings

Deploy to: backend/utils/compliance_engine.py
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
# DERIVED FIELDS - Calculated from source columns
# =============================================================================

DERIVED_FIELDS = {
    'age': {
        'source_semantic_types': ['birth_date', 'date_of_birth', 'dob'],
        'calculation': "EXTRACT(YEAR FROM AGE(CURRENT_DATE, {column}))",
        'duckdb_calculation': "DATE_DIFF('year', {column}, CURRENT_DATE)",
        'description': 'Age in years calculated from birth date'
    },
    'tenure': {
        'source_semantic_types': ['hire_date', 'start_date', 'employment_date'],
        'calculation': "EXTRACT(YEAR FROM AGE(CURRENT_DATE, {column}))",
        'duckdb_calculation': "DATE_DIFF('year', {column}, CURRENT_DATE)",
        'description': 'Years of service calculated from hire date'
    },
    'years_of_service': {
        'source_semantic_types': ['hire_date', 'start_date', 'employment_date'],
        'calculation': "EXTRACT(YEAR FROM AGE(CURRENT_DATE, {column}))",
        'duckdb_calculation': "DATE_DIFF('year', {column}, CURRENT_DATE)",
        'description': 'Years of service calculated from hire date'
    },
}

# Field name to semantic type mapping
# When a rule asks for "Social Security FICA wages", look for these semantic types
FIELD_TO_SEMANTIC = {
    'age': ['age', 'birth_date', 'date_of_birth'],
    'wages': ['wages', 'fica_wages', 'ss_wages', 'gross_wages', 'amount'],
    'fica_wages': ['fica_wages', 'ss_wages', 'social_security_wages'],
    'social_security_wages': ['fica_wages', 'ss_wages', 'social_security_wages'],
    'employee_type': ['employee_type', 'employee_type_code'],
    'contribution': ['contribution', 'contribution_type', 'deduction_code'],
    'contribution_type': ['contribution_type', 'deduction_code', 'deductionbenefit_code'],
    'plan_type': ['plan_type', 'deductionbenefit_code'],
    'deduction': ['deduction_code', 'deductionbenefit_code'],
    'earnings': ['earnings_code', 'earning_code'],
    'tax': ['tax_code'],
    'location': ['location', 'location_code'],
    'job': ['job_code'],
    'department': ['department_code', 'org_level'],
}


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ComplianceCheck:
    """A single compliance check to run."""
    check_id: str
    rule_id: str
    rule_title: str
    sql_query: str
    description: str
    expected_result: str
    field_mappings: Dict[str, str] = field(default_factory=dict)
    severity: str = "medium"
    category: str = "general"


@dataclass 
class Finding:
    """An auditor-quality finding following the Five C's framework."""
    finding_id: str
    title: str
    severity: str
    category: str
    condition: Dict[str, Any]
    criteria: Dict[str, Any]
    cause: Dict[str, Any]
    consequence: Dict[str, Any]
    corrective_action: Dict[str, Any]
    evidence: Dict[str, Any]
    rule_id: str
    source_document: str
    source_page: Optional[int] = None
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
# COLUMN MAPPER - Reads from _column_mappings
# =============================================================================

class ColumnMapper:
    """
    Maps rule fields to actual database columns using _column_mappings.
    
    NO RUNTIME SCORING - just reads what was computed at upload time.
    """
    
    def __init__(self, db_handler=None):
        self.db_handler = db_handler
        self._mappings_cache: Dict[str, Dict] = {}
        self._columns_cache: Dict[str, List] = {}
    
    def load_semantic_mappings(self, project: str) -> Dict[Tuple[str, str], str]:
        """
        Load all semantic type mappings for a project.
        
        Returns:
            Dict of (table_name, column_name) -> semantic_type
        """
        if project in self._mappings_cache:
            return self._mappings_cache[project]
        
        mappings = {}
        
        if not self.db_handler or not hasattr(self.db_handler, 'conn'):
            logger.warning("[COMPLIANCE] No db_handler for semantic mappings")
            return mappings
        
        try:
            project_prefix = project[:8].lower() if project else ''
            
            # Load from _column_mappings
            result = self.db_handler.conn.execute("""
                SELECT table_name, original_column, semantic_type, confidence
                FROM _column_mappings
                WHERE LOWER(table_name) LIKE ? || '%'
                  AND semantic_type IS NOT NULL
                  AND semantic_type != 'NONE'
            """, [project_prefix]).fetchall()
            
            for row in result:
                table_name, column_name, sem_type, confidence = row
                mappings[(table_name, column_name)] = sem_type
            
            self._mappings_cache[project] = mappings
            logger.warning(f"[COMPLIANCE] Loaded {len(mappings)} semantic mappings for {project}")
            
        except Exception as e:
            logger.error(f"[COMPLIANCE] Failed to load semantic mappings: {e}")
        
        return mappings
    
    def load_all_columns(self, project: str) -> List[Dict]:
        """Load all columns for a project with their profiles."""
        if project in self._columns_cache:
            return self._columns_cache[project]
        
        columns = []
        
        if not self.db_handler or not hasattr(self.db_handler, 'conn'):
            return columns
        
        try:
            project_prefix = project[:8].lower() if project else ''
            
            result = self.db_handler.conn.execute("""
                SELECT table_name, column_name, inferred_type, distinct_values
                FROM _column_profiles
                WHERE LOWER(table_name) LIKE ? || '%'
            """, [project_prefix]).fetchall()
            
            for row in result:
                columns.append({
                    'table_name': row[0],
                    'column_name': row[1],
                    'inferred_type': row[2],
                    'distinct_values': row[3]
                })
            
            self._columns_cache[project] = columns
            logger.warning(f"[COMPLIANCE] Loaded {len(columns)} columns for {project}")
            
        except Exception as e:
            logger.error(f"[COMPLIANCE] Failed to load columns: {e}")
        
        return columns
    
    def find_column_for_field(self, field_name: str, project: str) -> Optional[Dict]:
        """
        Find the best column match for a rule field.
        
        1. Check if field maps to a semantic type
        2. Look for columns with that semantic type
        3. Handle derived fields (age → birth_date)
        
        Returns:
            Dict with table_name, column_name, and optional calculation
        """
        field_norm = self._normalize(field_name)
        
        # Load mappings
        semantic_mappings = self.load_semantic_mappings(project)
        all_columns = self.load_all_columns(project)
        
        # Step 1: Get semantic types to look for
        target_semantic_types = self._get_target_semantic_types(field_norm)
        
        # Step 2: Check if this is a derived field
        derived_info = DERIVED_FIELDS.get(field_norm)
        if derived_info:
            target_semantic_types.extend(derived_info['source_semantic_types'])
        
        # Step 3: Find columns with matching semantic types
        for (table_name, col_name), sem_type in semantic_mappings.items():
            if sem_type.lower() in [t.lower() for t in target_semantic_types]:
                result = {
                    'table_name': table_name,
                    'column_name': col_name,
                    'semantic_type': sem_type,
                    'match_reason': f'semantic_type:{sem_type}'
                }
                
                # Add calculation for derived fields
                if derived_info:
                    result['calculation'] = derived_info['duckdb_calculation'].format(column=col_name)
                    result['is_derived'] = True
                
                logger.warning(f"[COMPLIANCE] Field '{field_name}' → {table_name}.{col_name} (semantic:{sem_type})")
                return result
        
        # Step 4: Fallback - exact column name match
        for col in all_columns:
            col_norm = self._normalize(col['column_name'])
            if col_norm == field_norm:
                logger.warning(f"[COMPLIANCE] Field '{field_name}' → {col['table_name']}.{col['column_name']} (exact_name)")
                return {
                    'table_name': col['table_name'],
                    'column_name': col['column_name'],
                    'match_reason': 'exact_name'
                }
        
        logger.warning(f"[COMPLIANCE] Field '{field_name}' → NO MATCH (looked for semantic types: {target_semantic_types})")
        return None
    
    def _normalize(self, text: str) -> str:
        """Normalize field name."""
        if not text:
            return ''
        text = text.lower().strip()
        text = re.sub(r'[\s\-\.]+', '_', text)
        return text
    
    def _get_target_semantic_types(self, field_norm: str) -> List[str]:
        """Get semantic types to look for based on field name."""
        # Check explicit mapping first
        for key, types in FIELD_TO_SEMANTIC.items():
            if key in field_norm or field_norm in key:
                return list(types)
        
        # Return field itself as potential semantic type
        return [field_norm]


# =============================================================================
# COMPLIANCE ENGINE
# =============================================================================

class ComplianceEngine:
    """
    Runs compliance checks against customer data.
    
    READS from _column_mappings - no runtime scoring.
    """
    
    def __init__(self, db_handler=None, chroma_client=None):
        self.db_handler = db_handler
        self.chroma_client = chroma_client
        self.column_mapper = ColumnMapper(db_handler)
        self._rules_cache: List[Dict] = []
    
    def load_rules(self) -> List[Dict]:
        """Load compliance rules from ChromaDB standards."""
        if self._rules_cache:
            return self._rules_cache
        
        try:
            # Try to load from standards_processor
            try:
                from backend.utils.standards_processor import StandardsProcessor
                processor = StandardsProcessor(chroma_client=self.chroma_client)
                self._rules_cache = processor.get_all_rules()
            except ImportError:
                from utils.standards_processor import StandardsProcessor
                processor = StandardsProcessor(chroma_client=self.chroma_client)
                self._rules_cache = processor.get_all_rules()
            
            logger.warning(f"[COMPLIANCE] Loaded {len(self._rules_cache)} rules")
            
        except Exception as e:
            logger.error(f"[COMPLIANCE] Failed to load rules: {e}")
            self._rules_cache = []
        
        return self._rules_cache
    
    def run_compliance_scan(self, project_id: str) -> Dict:
        """
        Run all compliance rules against a project.
        
        Returns:
            Dict with check results and findings
        """
        logger.warning(f"[COMPLIANCE] Starting scan for {project_id}")
        
        result = {
            'project_id': project_id,
            'rules_checked': 0,
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'errors': 0,
            'findings_count': 0,
            'findings': [],
            'check_results': []
        }
        
        # Load rules
        rules = self.load_rules()
        if not rules:
            logger.warning("[COMPLIANCE] No rules to check")
            return result
        
        # Get schema for SQL generation
        schema = self._get_schema(project_id)
        if not schema.get('tables'):
            logger.warning(f"[COMPLIANCE] No schema found for {project_id}")
            for rule in rules:
                result['check_results'].append({
                    'rule_id': rule.get('rule_id', 'unknown'),
                    'rule_title': rule.get('title', 'Unknown Rule'),
                    'status': 'skipped',
                    'message': 'No schema available for project'
                })
                result['skipped'] += 1
            result['rules_checked'] = len(rules)
            return result
        
        logger.warning(f"[COMPLIANCE] Checking {len(rules)} rules against {len(schema['tables'])} tables")
        
        # Check each rule
        for rule in rules:
            rule_id = rule.get('rule_id', 'unknown')
            rule_title = rule.get('title', 'Unknown Rule')
            
            rule_result = {
                'rule_id': rule_id,
                'rule_title': rule_title,
                'status': 'pending',
                'message': '',
                'field_mappings': {},
                'sql': None,
                'row_count': None
            }
            
            try:
                # Extract fields from rule
                fields = self._extract_rule_fields(rule)
                
                if not fields:
                    rule_result['status'] = 'skipped'
                    rule_result['message'] = 'No fields defined in rule'
                    result['skipped'] += 1
                    result['check_results'].append(rule_result)
                    continue
                
                # Map fields to columns
                field_mappings = {}
                unmapped_fields = []
                
                for field in fields:
                    mapping = self.column_mapper.find_column_for_field(field, project_id)
                    if mapping:
                        field_mappings[field] = mapping
                    else:
                        unmapped_fields.append(field)
                
                rule_result['field_mappings'] = {
                    k: f"{v['table_name']}.{v['column_name']}" 
                    for k, v in field_mappings.items()
                }
                
                if not field_mappings:
                    rule_result['status'] = 'skipped'
                    rule_result['message'] = f'No matching columns for fields: {", ".join(fields)}'
                    result['skipped'] += 1
                    result['check_results'].append(rule_result)
                    continue
                
                if unmapped_fields:
                    logger.warning(f"[COMPLIANCE] Rule {rule_id}: unmapped fields: {unmapped_fields}")
                
                # Generate SQL
                check = self._generate_check_sql(rule, field_mappings, schema)
                
                if not check or not check.sql_query:
                    rule_result['status'] = 'skipped'
                    rule_result['message'] = 'Could not generate SQL for rule'
                    result['skipped'] += 1
                    result['check_results'].append(rule_result)
                    continue
                
                rule_result['sql'] = check.sql_query
                
                # Execute SQL
                try:
                    query_result = self.db_handler.query(check.sql_query)
                    rows = query_result.get('rows', [])
                    rule_result['row_count'] = len(rows)
                    
                    if len(rows) == 0:
                        rule_result['status'] = 'passed'
                        rule_result['message'] = 'No violations found'
                        result['passed'] += 1
                    else:
                        rule_result['status'] = 'failed'
                        rule_result['message'] = f'{len(rows)} potential violations found'
                        result['failed'] += 1
                        
                        # Create finding
                        finding = self._create_finding(rule, rows, field_mappings)
                        if finding:
                            result['findings'].append(finding.to_dict())
                            result['findings_count'] += 1
                    
                except Exception as sql_e:
                    rule_result['status'] = 'error'
                    rule_result['message'] = f'SQL execution failed: {str(sql_e)}'
                    result['errors'] += 1
                    logger.error(f"[COMPLIANCE] SQL error for {rule_id}: {sql_e}")
                
            except Exception as e:
                rule_result['status'] = 'error'
                rule_result['message'] = f'Check failed: {str(e)}'
                result['errors'] += 1
                logger.error(f"[COMPLIANCE] Error checking rule {rule_id}: {e}")
            
            result['check_results'].append(rule_result)
        
        result['rules_checked'] = len(rules)
        
        logger.warning(f"[COMPLIANCE] Scan complete: {result['passed']} passed, "
                       f"{result['failed']} failed, {result['skipped']} skipped, "
                       f"{result['errors']} errors")
        
        return result
    
    def _get_schema(self, project_id: str) -> Dict:
        """Get schema for a project."""
        if not self.db_handler:
            return {'tables': []}
        
        try:
            # Case-insensitive lookup
            raw_schema = self.db_handler.get_schema(project_id)
            
            if not raw_schema and hasattr(self.db_handler, 'conn'):
                # Try case-insensitive
                result = self.db_handler.conn.execute("""
                    SELECT table_name, display_name, columns
                    FROM _schema_metadata 
                    WHERE LOWER(project) = LOWER(?) AND is_current = TRUE
                """, [project_id]).fetchall()
                
                raw_schema = {}
                for row in result:
                    table_name, display_name, columns_json = row
                    try:
                        columns = json.loads(columns_json) if columns_json else []
                    except:
                        columns = []
                    raw_schema[table_name] = {
                        'display_name': display_name,
                        'columns': columns
                    }
            
            if not raw_schema:
                return {'tables': []}
            
            tables = []
            for table_name, table_info in raw_schema.items():
                columns = table_info.get('columns', [])
                if columns and isinstance(columns[0], str):
                    columns = [{'column_name': c} for c in columns]
                
                tables.append({
                    'table_name': table_name,
                    'display_name': table_info.get('display_name', table_name),
                    'columns': columns
                })
            
            return {'tables': tables}
            
        except Exception as e:
            logger.error(f"[COMPLIANCE] Failed to get schema: {e}")
            return {'tables': []}
    
    def _extract_rule_fields(self, rule: Dict) -> List[str]:
        """Extract all field names from a rule."""
        fields = set()
        
        # Extract from applies_to
        applies_to = rule.get('applies_to', {})
        for condition in applies_to.get('conditions', []):
            if 'field' in condition:
                fields.add(condition['field'])
        
        # Extract from requirement
        requirement = rule.get('requirement', {})
        for check in requirement.get('checks', []):
            if 'field' in check:
                fields.add(check['field'])
        
        return list(fields)
    
    def _generate_check_sql(self, rule: Dict, field_mappings: Dict, schema: Dict) -> Optional[ComplianceCheck]:
        """Generate SQL to check a rule."""
        try:
            from utils.llm_orchestrator import LLMOrchestrator
        except ImportError:
            from backend.utils.llm_orchestrator import LLMOrchestrator
        
        # Build mapping text for prompt
        mapping_lines = []
        for field, info in field_mappings.items():
            col_ref = f"{info['table_name']}.{info['column_name']}"
            if info.get('is_derived'):
                col_ref = info['calculation']
            mapping_lines.append(f"- '{field}' → {col_ref}")
        
        mapping_text = "\n".join(mapping_lines)
        
        # Build table list
        tables_used = list(set(info['table_name'] for info in field_mappings.values()))
        tables_text = ", ".join(tables_used)
        
        prompt = f"""Generate a DuckDB SQL query to check this compliance rule.

RULE: {rule.get('title', 'Unknown')}
DESCRIPTION: {rule.get('description', '')}

FIELD MAPPINGS (use these exact column references):
{mapping_text}

TABLES AVAILABLE: {tables_text}

APPLIES TO CONDITIONS:
{json.dumps(rule.get('applies_to', {}), indent=2)}

REQUIREMENT CHECKS:
{json.dumps(rule.get('requirement', {}), indent=2)}

Generate a SELECT query that returns rows that VIOLATE the requirement.
If the rule cannot be checked with available columns, respond with just: CANNOT_CHECK

SQL:"""

        try:
            orchestrator = LLMOrchestrator()
            result = orchestrator.generate_sql(prompt, schema_columns=set())
            
            if not result.get('success') or not result.get('sql'):
                return None
            
            sql = result['sql']
            
            if 'CANNOT_CHECK' in sql.upper():
                return None
            
            if not sql.strip().upper().startswith(('SELECT', 'WITH')):
                return None
            
            return ComplianceCheck(
                check_id=f"CHK_{rule.get('rule_id', 'unknown')}",
                rule_id=rule.get('rule_id', ''),
                rule_title=rule.get('title', ''),
                sql_query=sql,
                description=f"Check for: {rule.get('title', '')}",
                expected_result="No rows = compliant",
                field_mappings={k: f"{v['table_name']}.{v['column_name']}" for k, v in field_mappings.items()},
                severity=rule.get('severity', 'medium'),
                category=rule.get('category', 'general')
            )
            
        except Exception as e:
            logger.error(f"[COMPLIANCE] SQL generation failed: {e}")
            return None
    
    def _create_finding(self, rule: Dict, violations: List, field_mappings: Dict) -> Optional[Finding]:
        """Create a finding from rule violations."""
        try:
            return Finding(
                finding_id=f"FND_{rule.get('rule_id', 'unknown')}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                title=f"Non-compliance: {rule.get('title', 'Unknown Rule')}",
                severity=rule.get('severity', 'medium'),
                category=rule.get('category', 'general'),
                condition={
                    'description': f"{len(violations)} records do not meet the requirement",
                    'sample_count': min(5, len(violations)),
                    'total_count': len(violations)
                },
                criteria={
                    'rule': rule.get('title', ''),
                    'description': rule.get('description', ''),
                    'requirement': rule.get('requirement', {})
                },
                cause={
                    'description': 'Records found that do not meet compliance criteria',
                    'field_mappings': {k: f"{v['table_name']}.{v['column_name']}" for k, v in field_mappings.items()}
                },
                consequence={
                    'description': rule.get('consequence', 'Potential compliance violation')
                },
                corrective_action={
                    'description': rule.get('corrective_action', 'Review and remediate affected records')
                },
                evidence={
                    'sample_violations': violations[:5],
                    'total_violations': len(violations),
                    'query_used': 'See check_results for SQL'
                },
                rule_id=rule.get('rule_id', ''),
                source_document=rule.get('source_document', 'Unknown'),
                source_page=rule.get('source_page')
            )
        except Exception as e:
            logger.error(f"[COMPLIANCE] Failed to create finding: {e}")
            return None


# =============================================================================
# MODULE-LEVEL ACCESS
# =============================================================================

_engine_instance = None

def get_compliance_engine(db_handler=None, chroma_client=None) -> ComplianceEngine:
    """Get or create the compliance engine instance."""
    global _engine_instance
    
    if _engine_instance is None or db_handler is not None:
        _engine_instance = ComplianceEngine(db_handler, chroma_client)
    
    return _engine_instance


def run_compliance_check(project_id: str, db_handler=None, chroma_client=None) -> Dict:
    """Run compliance check for a project."""
    engine = get_compliance_engine(db_handler, chroma_client)
    return engine.run_compliance_scan(project_id)
