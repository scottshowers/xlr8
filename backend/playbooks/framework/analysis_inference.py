"""
PLAYBOOK FRAMEWORK - Analysis Inference
========================================

Deterministic engine config inference using existing term_index.

This module bridges playbook steps to engine configs WITHOUT LLM calls.
It leverages the intelligence already built at upload time:
- _term_index: Maps keywords to tables/columns
- _column_profiles: Semantic types, domains, filter categories
- extract_keywords(): Already extracts keywords from step descriptions

ARCHITECTURE:
1. Parse action verb from step description → engine type
2. Resolve keywords via term_index → target tables/columns  
3. Generate appropriate EngineConfig based on engine type + resolved data

Author: XLR8 Team
Created: January 18, 2026
"""

import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from .definitions import EngineConfig

logger = logging.getLogger(__name__)

# =============================================================================
# ACTION VERB → ENGINE TYPE MAPPING
# =============================================================================

# Ordered by specificity - first match wins
ACTION_PATTERNS: List[Tuple[str, str]] = [
    # Validation patterns
    (r'\b(verify|validate|confirm|ensure|check.*accuracy|check.*complete)', 'validate'),
    (r'\b(review.*accuracy|review.*correct|accurate|correct)', 'validate'),
    
    # Detection patterns  
    (r'\b(find|identify|look for|check for|locate|detect)', 'detect'),
    (r'\b(duplicate|orphan|missing|outstanding|arrears)', 'detect'),
    
    # Comparison patterns
    (r'\b(compare|reconcile|match|difference|variance|vs\.?|versus)', 'compare'),
    (r'\b(year.over.year|period.over.period|prior)', 'compare'),
    
    # Aggregation patterns (review/run reports)
    (r'\b(run.*report|print.*report|generate.*report|pull.*report)', 'aggregate'),
    (r'\b(review|summarize|total|count|list)', 'aggregate'),
    
    # Mapping patterns
    (r'\b(map|convert|transform|migrate|update.*code)', 'map'),
]

# Fallback: if no pattern matches, use validate (most common for checklists)
DEFAULT_ENGINE = 'validate'


# =============================================================================
# KEYWORD EXTRACTION (matches playbook_parser.py)
# =============================================================================

# Key terms that indicate data domains - aligned with playbook_parser.extract_keywords
KEY_TERMS = [
    # Tax
    'tax', 'fein', 'ein', 'sui', 'suta', 'sdi', 'withholding', 'exempt',
    'w-2', 'w2', '1099', '1099-misc', '1099-nec', '1099-r',
    
    # Payroll
    'earnings', 'deduction', 'benefit', 'arrears', 'outstanding', 'check',
    'adjustment', 'reconcile', 'payroll',
    
    # Benefits
    '401k', '401(k)', 'retirement', 'pension',
    'healthcare', 'medical', 'dental', 'vision', 'hsa', 'fsa',
    'workers comp', 'work comp',
    
    # Employee data
    'ssn', 'social security', 'address', 'employee',
    
    # Compliance
    'ale', 'affordable care', 'aca', '1095', 'healthcare reporting',
    
    # Special
    'tip', 'tips', 'gross receipts',
    'puerto rico', 'virgin islands', 'guam',
    'third party sick', 'tps',
    
    # Company
    'company', 'fein', 'state tax', 'federal',
]


def extract_keywords(text: str) -> List[str]:
    """
    Extract keywords for data matching.
    Mirrors playbook_parser.extract_keywords() for consistency.
    """
    keywords = []
    text_lower = text.lower()
    
    for term in KEY_TERMS:
        if term in text_lower:
            keywords.append(term)
    
    return keywords


# =============================================================================
# VALIDATION RULE INFERENCE
# =============================================================================

# Column name patterns → validation rule types
VALIDATION_PATTERNS: Dict[str, Dict[str, Any]] = {
    # Format validations
    r'(ssn|social.*sec)': {'type': 'format', 'pattern': 'ssn'},
    r'(email)': {'type': 'format', 'pattern': 'email'},
    r'(phone|tel)': {'type': 'format', 'pattern': 'phone'},
    r'(zip|postal)': {'type': 'format', 'pattern': 'zip'},
    
    # Not-null validations (required fields)
    r'(fein|ein|tax.*id)': {'type': 'not_null'},
    r'(employee.*id|emp.*no|person.*id)': {'type': 'not_null'},
    r'(company.*code|co.*code)': {'type': 'not_null'},
    
    # Date validations
    r'(date|_dt$|_date$)': {'type': 'range', 'min': '1900-01-01', 'max': '2100-12-31'},
    
    # Status validations
    r'(status|_sts$)': {'type': 'allowed_values', 'values': ['A', 'T', 'L', 'P']},
}


def infer_validation_rules(column_name: str, semantic_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Infer validation rules for a column based on name/semantic type.
    """
    rules = []
    col_lower = column_name.lower()
    
    for pattern, rule_template in VALIDATION_PATTERNS.items():
        if re.search(pattern, col_lower, re.IGNORECASE):
            rule = {'field': column_name, **rule_template}
            rules.append(rule)
            break  # One rule per column for now
    
    # Default: not_null check if no specific pattern matched
    if not rules:
        rules.append({'field': column_name, 'type': 'not_null'})
    
    return rules


# =============================================================================
# DETECTION PATTERN INFERENCE
# =============================================================================

def infer_detection_patterns(
    description: str,
    columns: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Infer detection patterns based on step description and available columns.
    """
    patterns = []
    desc_lower = description.lower()
    
    # Duplicate detection
    if any(word in desc_lower for word in ['duplicate', 'unique', 'distinct']):
        # Find likely unique columns (IDs, SSNs, etc.)
        for col in columns:
            col_name = col.get('column_name', '').lower()
            if any(pat in col_name for pat in ['id', 'ssn', 'number', 'code']):
                patterns.append({
                    'type': 'duplicate',
                    'columns': [col['column_name']]
                })
                break
    
    # Orphan detection
    if any(word in desc_lower for word in ['orphan', 'missing', 'invalid']):
        patterns.append({
            'type': 'anomaly',
            'rule': 'employee_id IS NULL OR employee_id = \'\'',
            'message': 'Records with missing employee reference'
        })
    
    # Outstanding/arrears detection
    if any(word in desc_lower for word in ['outstanding', 'arrears', 'balance']):
        patterns.append({
            'type': 'anomaly',
            'rule': 'balance > 0 OR amount_due > 0',
            'message': 'Records with outstanding balances'
        })
    
    # Default: look for nulls in key fields
    if not patterns:
        patterns.append({
            'type': 'anomaly',
            'rule': '1=0',  # Placeholder - will be refined
            'message': 'General data quality check'
        })
    
    return patterns


# =============================================================================
# MAIN INFERENCE FUNCTION
# =============================================================================

def infer_engine_type(description: str) -> str:
    """
    Determine the appropriate engine type from step description.
    """
    desc_lower = description.lower()
    
    for pattern, engine in ACTION_PATTERNS:
        if re.search(pattern, desc_lower, re.IGNORECASE):
            logger.debug(f"[INFERENCE] Matched pattern '{pattern}' → engine '{engine}'")
            return engine
    
    logger.debug(f"[INFERENCE] No pattern matched, using default '{DEFAULT_ENGINE}'")
    return DEFAULT_ENGINE


def infer_analysis_configs(
    step_id: str,
    description: str,
    keywords: List[str],
    conn,
    project: str
) -> List[EngineConfig]:
    """
    Generate engine configs for a playbook step using term_index resolution.
    
    Args:
        step_id: The step identifier (e.g., "2A")
        description: The step description text
        keywords: Pre-extracted keywords from the description
        conn: DuckDB connection
        project: Project ID for term_index lookup
        
    Returns:
        List of EngineConfig objects ready for execution
    """
    configs = []
    
    if not description:
        return configs
    
    # 1. Determine engine type from action verb
    engine_type = infer_engine_type(description)
    logger.info(f"[INFERENCE] Step {step_id}: engine_type={engine_type}, keywords={keywords[:5]}")
    
    # 2. Try to resolve keywords via term_index
    resolved_tables = {}
    
    try:
        from backend.utils.intelligence.term_index import TermIndex
        term_index = TermIndex(conn, project)
        
        # Resolve each keyword
        for keyword in keywords:
            matches = term_index.resolve_terms([keyword])
            for match in matches:
                table = match.table_name
                if table not in resolved_tables:
                    resolved_tables[table] = {
                        'columns': [],
                        'keywords': []
                    }
                resolved_tables[table]['columns'].append({
                    'column_name': match.column_name,
                    'operator': match.operator,
                    'match_value': match.match_value,
                    'domain': match.domain,
                    'confidence': match.confidence
                })
                resolved_tables[table]['keywords'].append(keyword)
        
        logger.info(f"[INFERENCE] Step {step_id}: resolved {len(resolved_tables)} tables from keywords")
        
    except ImportError:
        logger.warning("[INFERENCE] term_index not available - using keyword-only inference")
    except Exception as e:
        logger.warning(f"[INFERENCE] term_index resolution failed: {e}")
    
    # 3. Generate configs based on engine type
    if resolved_tables:
        # We have resolved data - generate specific configs
        for table_name, table_info in resolved_tables.items():
            config = _generate_config_for_table(
                engine_type=engine_type,
                table_name=table_name,
                columns=table_info['columns'],
                description=description,
                step_id=step_id
            )
            if config:
                configs.append(config)
    else:
        # No resolution - generate placeholder config with semantic reference
        config = _generate_placeholder_config(
            engine_type=engine_type,
            keywords=keywords,
            description=description,
            step_id=step_id
        )
        if config:
            configs.append(config)
    
    logger.info(f"[INFERENCE] Step {step_id}: generated {len(configs)} engine configs")
    return configs


def _generate_config_for_table(
    engine_type: str,
    table_name: str,
    columns: List[Dict],
    description: str,
    step_id: str
) -> Optional[EngineConfig]:
    """
    Generate an EngineConfig for a specific resolved table.
    """
    # Use semantic placeholder for table - will be resolved at runtime
    # This allows the same config to work across different projects
    table_ref = f"{{{{{table_name}}}}}"
    
    if engine_type == 'validate':
        # Generate validation rules for each column
        rules = []
        for col in columns[:5]:  # Limit to 5 columns per config
            col_rules = infer_validation_rules(col['column_name'])
            rules.extend(col_rules)
        
        if not rules:
            return None
        
        return EngineConfig(
            engine='validate',
            config={
                'source_table': table_ref,
                'rules': rules,
                'sample_limit': 10
            },
            description=f"Validate {table_name}: {description[:50]}..."
        )
    
    elif engine_type == 'detect':
        patterns = infer_detection_patterns(description, columns)
        
        return EngineConfig(
            engine='detect',
            config={
                'source_table': table_ref,
                'patterns': patterns,
                'sample_limit': 10
            },
            description=f"Detect issues in {table_name}: {description[:50]}..."
        )
    
    elif engine_type == 'aggregate':
        # Generate aggregation config
        group_cols = [col['column_name'] for col in columns[:3]]
        
        return EngineConfig(
            engine='aggregate',
            config={
                'source_table': table_ref,
                'operation': 'count',
                'group_by': group_cols if group_cols else None
            },
            description=f"Summarize {table_name}: {description[:50]}..."
        )
    
    elif engine_type == 'compare':
        # Comparison requires two tables - generate placeholder
        return EngineConfig(
            engine='compare',
            config={
                'source_table': table_ref,
                'compare_to': '{{prior_period}}',  # Semantic placeholder
                'key_columns': [col['column_name'] for col in columns[:2]],
                'compare_columns': [col['column_name'] for col in columns]
            },
            description=f"Compare {table_name}: {description[:50]}..."
        )
    
    elif engine_type == 'map':
        return EngineConfig(
            engine='map',
            config={
                'source_table': table_ref,
                'mappings': {}  # To be populated by user or schema
            },
            description=f"Map {table_name}: {description[:50]}..."
        )
    
    return None


def _generate_placeholder_config(
    engine_type: str,
    keywords: List[str],
    description: str,
    step_id: str
) -> Optional[EngineConfig]:
    """
    Generate a placeholder config when no specific table was resolved.
    Uses semantic placeholders based on keywords.
    """
    if not keywords:
        return None
    
    # Create semantic table reference from primary keyword
    primary_keyword = keywords[0].replace(' ', '_').replace('-', '_')
    table_ref = f"{{{{{primary_keyword}_data}}}}"
    
    if engine_type == 'validate':
        return EngineConfig(
            engine='validate',
            config={
                'source_table': table_ref,
                'rules': [
                    {'field': '*', 'type': 'not_null'}  # Wildcard - validate all
                ],
                'sample_limit': 10
            },
            description=f"Validate {primary_keyword} data: {description[:50]}..."
        )
    
    elif engine_type == 'aggregate':
        return EngineConfig(
            engine='aggregate',
            config={
                'source_table': table_ref,
                'operation': 'count'
            },
            description=f"Review {primary_keyword} data: {description[:50]}..."
        )
    
    elif engine_type == 'detect':
        return EngineConfig(
            engine='detect',
            config={
                'source_table': table_ref,
                'patterns': [
                    {'type': 'anomaly', 'rule': '1=1', 'message': 'General scan'}
                ],
                'sample_limit': 10
            },
            description=f"Check {primary_keyword} data: {description[:50]}..."
        )
    
    return None


# =============================================================================
# BATCH INFERENCE
# =============================================================================

def infer_configs_for_playbook(
    steps: List[Dict[str, Any]],
    conn,
    project: str
) -> Dict[str, List[EngineConfig]]:
    """
    Generate engine configs for all steps in a playbook.
    
    Args:
        steps: List of step dicts with 'id', 'description', etc.
        conn: DuckDB connection
        project: Project ID
        
    Returns:
        Dict mapping step_id → List[EngineConfig]
    """
    configs_by_step = {}
    
    for step in steps:
        step_id = step.get('id') or step.get('action_id')
        description = step.get('description', '')
        
        # Extract keywords if not already provided
        keywords = step.get('keywords') or extract_keywords(description)
        
        configs = infer_analysis_configs(
            step_id=step_id,
            description=description,
            keywords=keywords,
            conn=conn,
            project=project
        )
        
        configs_by_step[step_id] = configs
    
    total_configs = sum(len(c) for c in configs_by_step.values())
    logger.info(f"[INFERENCE] Generated {total_configs} configs for {len(steps)} steps")
    
    return configs_by_step
