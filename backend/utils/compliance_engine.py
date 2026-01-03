"""
XLR8 COMPLIANCE ENGINE v4.0 - Uses Semantic Vocabulary
=======================================================

THE RIGHT WAY:
- Uses semantic_vocabulary.py for ALL type matching
- READS semantic types from _column_mappings (populated at upload)
- NO hardcoded field mappings
- Handles derived fields via vocabulary (age from birth_date)

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
# COLUMN MAPPER - Uses Semantic Vocabulary
# =============================================================================

class ColumnMapper:
    """
    Maps rule fields to actual database columns using:
    1. semantic_vocabulary.py for type definitions
    2. _column_mappings for actual column->type assignments
    
    NO HARDCODED MAPPINGS.
    """
    
    def __init__(self, db_handler=None):
        self.db_handler = db_handler
        self._semantic_mappings: Dict[Tuple[str, str], str] = {}  # (table, col) -> semantic_type
        self._columns_by_type: Dict[str, List[Tuple[str, str]]] = {}  # semantic_type -> [(table, col), ...]
        self._loaded_project: str = ""
    
    def load_project_mappings(self, project: str) -> bool:
        """Load semantic mappings from _column_mappings for a project."""
        if project == self._loaded_project and self._semantic_mappings:
            return True
        
        self._semantic_mappings = {}
        self._columns_by_type = {}
        
        if not self.db_handler or not hasattr(self.db_handler, 'conn'):
            logger.warning("[COMPLIANCE] No db_handler available")
            return False
        
        try:
            project_prefix = project[:8].lower() if project else ''
            
            # Load from _column_mappings (case-insensitive)
            result = self.db_handler.conn.execute("""
                SELECT table_name, original_column, semantic_type, confidence
                FROM _column_mappings
                WHERE LOWER(table_name) LIKE ? || '%'
                  AND semantic_type IS NOT NULL
                  AND semantic_type != 'NONE'
                  AND confidence >= 0.6
            """, [project_prefix]).fetchall()
            
            for row in result:
                table_name, column_name, sem_type, confidence = row
                self._semantic_mappings[(table_name, column_name)] = sem_type
                
                # Build reverse index
                if sem_type not in self._columns_by_type:
                    self._columns_by_type[sem_type] = []
                self._columns_by_type[sem_type].append((table_name, column_name))
            
            self._loaded_project = project
            logger.warning(f"[COMPLIANCE] Loaded {len(self._semantic_mappings)} semantic mappings, "
                           f"{len(self._columns_by_type)} unique types")
            return True
            
        except Exception as e:
            logger.error(f"[COMPLIANCE] Failed to load mappings: {e}")
            return False
    
    def find_column_for_field(self, rule_field: str, project: str) -> Optional[Dict]:
        """
        Find the best column match for a rule field using semantic vocabulary.
        
        1. Normalize rule_field to canonical semantic type
        2. Look for columns with that type in _column_mappings
        3. Handle derived fields (age -> birth_date with calculation)
        
        Returns:
            Dict with table_name, column_name, and optional calculation
        """
        # Ensure mappings loaded
        self.load_project_mappings(project)
        
        # Import vocabulary
        try:
            from backend.utils.semantic_vocabulary import (
                find_semantic_type, 
                get_derivation_source,
                match_rule_field_to_column
            )
        except ImportError:
            from utils.semantic_vocabulary import (
                find_semantic_type,
                get_derivation_source,
                match_rule_field_to_column
            )
        
        # Step 1: Find canonical semantic type for rule field
        type_result = find_semantic_type(rule_field)
        if not type_result:
            logger.warning(f"[COMPLIANCE] Field '{rule_field}' has no known semantic type")
            return None
        
        rule_type, type_confidence = type_result
        logger.info(f"[COMPLIANCE] Field '{rule_field}' -> semantic type '{rule_type.name}' (conf: {type_confidence})")
        
        # Step 2: Look for direct match - columns with this semantic type
        if rule_type.name in self._columns_by_type:
            columns = self._columns_by_type[rule_type.name]
            if columns:
                table_name, col_name = columns[0]  # Take first match
                logger.warning(f"[COMPLIANCE] Field '{rule_field}' -> {table_name}.{col_name} (direct match)")
                return {
                    'table_name': table_name,
                    'column_name': col_name,
                    'semantic_type': rule_type.name,
                    'match_reason': 'direct_semantic_match',
                    'confidence': type_confidence
                }
        
        # Step 3: Check if this is a derived field (e.g., age from birth_date)
        derivation = get_derivation_source(rule_type.name)
        if derivation:
            source_type, derivation_sql = derivation
            logger.info(f"[COMPLIANCE] Field '{rule_field}' is derived from '{source_type.name}'")
            
            # Look for columns with the source type
            if source_type.name in self._columns_by_type:
                columns = self._columns_by_type[source_type.name]
                if columns:
                    table_name, col_name = columns[0]
                    sql = derivation_sql.format(column=col_name) if derivation_sql else None
                    logger.warning(f"[COMPLIANCE] Field '{rule_field}' -> derived from {table_name}.{col_name}")
                    return {
                        'table_name': table_name,
                        'column_name': col_name,
                        'semantic_type': source_type.name,
                        'match_reason': 'derived_field',
                        'calculation': sql,
                        'is_derived': True,
                        'derives_to': rule_type.name,
                        'confidence': type_confidence * 0.9
                    }
        
        # Step 4: Try matching against all column types using vocabulary
        for (table_name, col_name), col_sem_type in self._semantic_mappings.items():
            matches, conf, deriv_sql = match_rule_field_to_column(rule_field, col_sem_type)
            if matches and conf > 0.6:
                result = {
                    'table_name': table_name,
                    'column_name': col_name,
                    'semantic_type': col_sem_type,
                    'match_reason': 'vocabulary_match',
                    'confidence': conf
                }
                if deriv_sql:
                    result['calculation'] = deriv_sql.format(column=col_name)
                    result['is_derived'] = True
                
                logger.warning(f"[COMPLIANCE] Field '{rule_field}' -> {table_name}.{col_name} (vocab match)")
                return result
        
        logger.warning(f"[COMPLIANCE] Field '{rule_field}' -> NO MATCH FOUND")
        return None


# =============================================================================
# COMPLIANCE ENGINE
# =============================================================================

class ComplianceEngine:
    """
    Runs compliance checks against customer data.
    Uses semantic_vocabulary.py for all type matching.
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
        """Run all compliance rules against a project."""
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
            'check_results': [],
            'semantic_types_found': list(self.column_mapper._columns_by_type.keys()) if self.column_mapper._columns_by_type else []
        }
        
        # Load mappings for this project
        self.column_mapper.load_project_mappings(project_id)
        
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
                
                # Map fields to columns using vocabulary
                field_mappings = {}
                unmapped_fields = []
                
                for field_name in fields:
                    mapping = self.column_mapper.find_column_for_field(field_name, project_id)
                    if mapping:
                        field_mappings[field_name] = mapping
                    else:
                        unmapped_fields.append(field_name)
                
                rule_result['field_mappings'] = {
                    k: f"{v['table_name']}.{v['column_name']}" + 
                       (f" (calc: {v.get('calculation', '')[:30]}...)" if v.get('is_derived') else "")
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
            raw_schema = None
            
            if hasattr(self.db_handler, 'conn'):
                result = self.db_handler.conn.execute("""
                    SELECT table_name, display_name, columns
                    FROM _schema_metadata 
                    WHERE LOWER(project) = LOWER(?) AND is_current = TRUE
                """, [project_id]).fetchall()
                
                if result:
                    raw_schema = {}
                    for row in result:
                        table_name, display_name, columns_json = row
                        try:
                            columns = json.loads(columns_json) if columns_json else []
                        except Exception:
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
            # Also check for semantic_type if present
            if 'semantic_type' in condition:
                fields.add(condition['semantic_type'])
        
        # Extract from requirement
        requirement = rule.get('requirement', {})
        for check in requirement.get('checks', []):
            if 'field' in check:
                fields.add(check['field'])
            if 'semantic_type' in check:
                fields.add(check['semantic_type'])
        
        return list(fields)
    
    def _generate_check_sql(self, rule: Dict, field_mappings: Dict, schema: Dict) -> Optional[ComplianceCheck]:
        """Generate SQL to check a rule."""
        try:
            from utils.llm_orchestrator import LLMOrchestrator
        except ImportError:
            from backend.utils.llm_orchestrator import LLMOrchestrator
        
        # Build mapping text for prompt - include calculations for derived fields
        mapping_lines = []
        for field_name, info in field_mappings.items():
            if info.get('is_derived') and info.get('calculation'):
                col_ref = info['calculation']
                mapping_lines.append(f"- '{field_name}' → {col_ref} (calculated from {info['table_name']}.{info['column_name']})")
            else:
                col_ref = f"{info['table_name']}.{info['column_name']}"
                mapping_lines.append(f"- '{field_name}' → {col_ref}")
        
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
