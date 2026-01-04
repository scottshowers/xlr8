"""
RELATIONSHIP DETECTOR v4.0 - SEMANTIC-FIRST DETECTION
======================================================

THE RIGHT WAY:
1. Match columns by NAME or SEMANTIC TYPE first
2. Validate with value overlap from _column_profiles
3. NO pure value matching - that's how we got country_code → home_company_code

This detector READS from:
- _column_mappings: semantic types assigned at upload (job_code, employee_number, etc.)
- _column_profiles: distinct values for validation

It WRITES to:
- _table_relationships (via project_intelligence)

Deploy to: backend/utils/relationship_detector.py
"""

import json
import logging
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

# Minimum value overlap to VALIDATE a relationship (not to find one)
MIN_VALIDATION_OVERLAP = 10  # At least 10% overlap to confirm

# Confidence thresholds
CONFIDENCE_EXACT_NAME = 0.95      # job_code ↔ job_code
CONFIDENCE_SEMANTIC_MATCH = 0.85  # both tagged as "job_code" semantic type
CONFIDENCE_SUFFIX_MATCH = 0.75    # home_company_code ↔ company_code
CONFIDENCE_VALUE_VALIDATED = 0.90 # Name match + value overlap

# Known column name equivalences (prefix stripping)
# home_company_code should match company_code
STRIP_PREFIXES = ['home_', 'source_', 'target_', 'from_', 'to_', 'primary_', 'secondary_']

# Columns that should NEVER be relationship keys (too generic)
BLACKLIST_COLUMNS = {
    'id', 'row_id', 'index', 'created_at', 'updated_at', 'timestamp',
    'description', 'name', 'notes', 'comment', 'comments', 'text',
    'address', 'street', 'city', 'state', 'country', 'country_code',  # country_code is NOT a join key!
    'status', 'flag', 'active', 'deleted', 'is_active', 'is_deleted',
}

# Columns that are LIKELY relationship keys
KEY_PATTERNS = [
    '_code', '_id', '_num', '_number', '_key', '_type',
    'employee_number', 'company_code', 'job_code', 'location_code',
    'department_code', 'earning_code', 'deduction_code', 'tax_code',
    'pay_group', 'org_level',
]


# =============================================================================
# MAIN FUNCTION
# =============================================================================

async def analyze_project_relationships(project: str, tables: List[Dict], llm_client=None) -> Dict:
    """
    Detect relationships between tables using SEMANTIC-FIRST matching.
    
    Algorithm:
    1. Load semantic types from _column_mappings
    2. Load column values from _column_profiles  
    3. For each table pair:
       a. Find columns with MATCHING NAMES (exact or after prefix stripping)
       b. Find columns with MATCHING SEMANTIC TYPES
       c. Validate matches with value overlap
    4. Return relationships sorted by confidence
    
    Args:
        project: Project name
        tables: List of table dicts (for API compatibility)
        llm_client: Not used in v4
        
    Returns:
        Dict with 'relationships' list and stats
    """
    logger.warning(f"[RELATIONSHIP-V4] Starting SEMANTIC-FIRST detection for {project}")
    
    # Load semantic types from _column_mappings
    semantic_types = get_semantic_types(project)
    logger.warning(f"[RELATIONSHIP-V4] Loaded {len(semantic_types)} semantic type mappings")
    
    # Load column values from _column_profiles
    column_values = get_column_values(project)
    logger.warning(f"[RELATIONSHIP-V4] Loaded {len(column_values)} column value profiles")
    
    # Build column index by table
    tables_columns = build_column_index(project, semantic_types, column_values)
    logger.warning(f"[RELATIONSHIP-V4] Built index for {len(tables_columns)} tables")
    
    if not tables_columns:
        return empty_result(len(tables), "No column data found")
    
    # Find relationships
    relationships = []
    comparisons = 0
    
    table_names = list(tables_columns.keys())
    
    for i, table_a in enumerate(table_names):
        cols_a = tables_columns[table_a]
        
        for table_b in table_names[i+1:]:
            cols_b = tables_columns[table_b]
            
            # Find matching columns between these tables
            matches = find_column_matches(table_a, cols_a, table_b, cols_b, column_values)
            comparisons += 1
            
            for match in matches:
                relationships.append({
                    'source_table': table_a,
                    'source_column': match['col_a'],
                    'target_table': table_b,
                    'target_column': match['col_b'],
                    'confidence': match['confidence'],
                    'match_type': match['match_type'],
                    'match_rate': match.get('value_overlap', 0),
                    'semantic_type': match.get('semantic_type'),
                    'method': 'semantic_first_v4',
                    'verification_status': get_status(match['confidence']),
                    'needs_review': match['confidence'] < 0.8,
                    'confirmed': False,
                })
    
    # Sort by confidence
    relationships.sort(key=lambda x: x['confidence'], reverse=True)
    
    # Deduplicate
    relationships = deduplicate_relationships(relationships)
    
    # Limit per table pair
    relationships = limit_per_pair(relationships, max_per_pair=3)
    
    # Stats
    high_conf = sum(1 for r in relationships if r['confidence'] >= 0.85)
    medium_conf = sum(1 for r in relationships if 0.7 <= r['confidence'] < 0.85)
    
    logger.warning(f"[RELATIONSHIP-V4] Found {len(relationships)} relationships "
                   f"({high_conf} high confidence, {medium_conf} medium)")
    
    return {
        'relationships': relationships,
        'semantic_types': list(set(semantic_types.values())),
        'unmatched_columns': [],
        'stats': {
            'tables_analyzed': len(tables),
            'tables_with_columns': len(tables_columns),
            'semantic_mappings': len(semantic_types),
            'column_profiles': len(column_values),
            'comparisons_made': comparisons,
            'relationships_found': len(relationships),
            'high_confidence': high_conf,
            'medium_confidence': medium_conf,
            'method': 'semantic_first_v4',
        }
    }


# =============================================================================
# DATA LOADING
# =============================================================================

def get_semantic_types(project: str) -> Dict[Tuple[str, str], str]:
    """
    Load semantic types from _column_mappings table.
    
    Returns:
        Dict of (table_name, column_name) -> semantic_type
    """
    semantic_types = {}
    
    try:
        from utils.structured_data_handler import get_handler
        handler = get_handler()
        
        if not handler or not hasattr(handler, 'conn'):
            logger.warning("[RELATIONSHIP-V4] No handler available for semantic types")
            return semantic_types
        
        project_prefix = project[:8].lower() if project else ''
        
        result = handler.conn.execute("""
            SELECT table_name, original_column, semantic_type, confidence
            FROM _column_mappings
            WHERE LOWER(table_name) LIKE ? || '%'
              AND semantic_type IS NOT NULL
              AND semantic_type != 'NONE'
              AND confidence >= 0.7
        """, [project_prefix]).fetchall()
        
        for row in result:
            table_name, column_name, sem_type, confidence = row
            semantic_types[(table_name, column_name)] = sem_type
            
    except Exception as e:
        logger.warning(f"[RELATIONSHIP-V4] Failed to load semantic types: {e}")
    
    return semantic_types


def get_column_values(project: str) -> Dict[Tuple[str, str], Set[str]]:
    """
    Load distinct values from _column_profiles table.
    
    Returns:
        Dict of (table_name, column_name) -> set of values
    """
    column_values = {}
    
    try:
        from utils.structured_data_handler import get_handler
        handler = get_handler()
        
        if not handler or not hasattr(handler, 'conn'):
            return column_values
        
        project_prefix = project[:8].lower() if project else ''
        
        result = handler.conn.execute("""
            SELECT table_name, column_name, distinct_values, distinct_count
            FROM _column_profiles
            WHERE LOWER(table_name) LIKE ? || '%'
              AND distinct_count >= 2
              AND distinct_count <= 500
        """, [project_prefix]).fetchall()
        
        for row in result:
            table_name, column_name, values_json, distinct_count = row
            
            # Skip blacklisted columns
            col_lower = column_name.lower()
            if col_lower in BLACKLIST_COLUMNS:
                continue
            
            # Parse values
            if values_json:
                try:
                    values = json.loads(values_json) if isinstance(values_json, str) else values_json
                    if isinstance(values, list):
                        # Convert to lowercase strings for comparison
                        column_values[(table_name, column_name)] = {
                            str(v).lower().strip() for v in values if v is not None
                        }
                except Exception:
                    pass
                    
    except Exception as e:
        logger.warning(f"[RELATIONSHIP-V4] Failed to load column values: {e}")
    
    return column_values


def build_column_index(project: str, semantic_types: Dict, column_values: Dict) -> Dict[str, List[Dict]]:
    """
    Build an index of columns by table, enriched with semantic info.
    
    Returns:
        Dict of table_name -> list of column dicts
    """
    tables_columns = defaultdict(list)
    
    try:
        from utils.structured_data_handler import get_handler
        handler = get_handler()
        
        if not handler or not hasattr(handler, 'conn'):
            return dict(tables_columns)
        
        project_prefix = project[:8].lower() if project else ''
        
        # Get all columns from schema
        result = handler.conn.execute("""
            SELECT DISTINCT table_name, column_name
            FROM _column_profiles
            WHERE LOWER(table_name) LIKE ? || '%'
        """, [project_prefix]).fetchall()
        
        for row in result:
            table_name, column_name = row
            col_lower = column_name.lower()
            
            # Skip blacklisted
            if col_lower in BLACKLIST_COLUMNS:
                continue
            
            # Check if this is likely a key column
            is_key = any(pattern in col_lower for pattern in KEY_PATTERNS)
            
            col_info = {
                'name': column_name,
                'normalized': normalize_column_name(column_name),
                'semantic_type': semantic_types.get((table_name, column_name)),
                'has_values': (table_name, column_name) in column_values,
                'is_likely_key': is_key,
            }
            
            tables_columns[table_name].append(col_info)
            
    except Exception as e:
        logger.warning(f"[RELATIONSHIP-V4] Failed to build column index: {e}")
    
    return dict(tables_columns)


# =============================================================================
# MATCHING LOGIC
# =============================================================================

def normalize_column_name(name: str) -> str:
    """Normalize column name for comparison (strip prefixes, lowercase)."""
    name = name.lower().strip()
    
    # Strip known prefixes
    for prefix in STRIP_PREFIXES:
        if name.startswith(prefix):
            name = name[len(prefix):]
            break
    
    return name


def find_column_matches(table_a: str, cols_a: List[Dict], 
                        table_b: str, cols_b: List[Dict], 
                        column_values: Dict) -> List[Dict]:
    """
    Find matching columns between two tables.
    
    Priority:
    1. Exact name match (job_code ↔ job_code)
    2. Normalized name match (home_company_code ↔ company_code)
    3. Semantic type match (both tagged as "job_code")
    
    Then validate with value overlap.
    """
    matches = []
    
    for col_a in cols_a:
        # Only consider likely key columns
        if not col_a['is_likely_key']:
            continue
            
        for col_b in cols_b:
            if not col_b['is_likely_key']:
                continue
            
            match = None
            
            # 1. Exact name match
            if col_a['name'].lower() == col_b['name'].lower():
                match = {
                    'col_a': col_a['name'],
                    'col_b': col_b['name'],
                    'confidence': CONFIDENCE_EXACT_NAME,
                    'match_type': 'exact_name',
                }
            
            # 2. Normalized name match (after stripping prefixes)
            elif col_a['normalized'] == col_b['normalized']:
                match = {
                    'col_a': col_a['name'],
                    'col_b': col_b['name'],
                    'confidence': CONFIDENCE_SUFFIX_MATCH,
                    'match_type': 'normalized_name',
                }
            
            # 3. Semantic type match
            elif (col_a['semantic_type'] and col_b['semantic_type'] and 
                  col_a['semantic_type'] == col_b['semantic_type']):
                match = {
                    'col_a': col_a['name'],
                    'col_b': col_b['name'],
                    'confidence': CONFIDENCE_SEMANTIC_MATCH,
                    'match_type': 'semantic_type',
                    'semantic_type': col_a['semantic_type'],
                }
            
            # If we found a match, validate with value overlap
            if match:
                values_a = column_values.get((table_a, col_a['name']))
                values_b = column_values.get((table_b, col_b['name']))
                
                if values_a and values_b:
                    overlap_info = calculate_value_overlap(values_a, values_b)
                    match['value_overlap'] = overlap_info['overlap_percent']
                    
                    # Boost confidence if values also match well
                    if overlap_info['overlap_percent'] >= 50:
                        match['confidence'] = min(0.98, match['confidence'] + 0.05)
                        match['match_type'] += '+value_validated'
                    elif overlap_info['overlap_percent'] < 10 and match['match_type'] == 'normalized_name':
                        # Low value overlap on a normalized match - reduce confidence
                        match['confidence'] = max(0.5, match['confidence'] - 0.15)
                        match['match_type'] += '+low_value_overlap'
                
                matches.append(match)
    
    return matches


def calculate_value_overlap(values_a: Set[str], values_b: Set[str]) -> Dict:
    """Calculate detailed value overlap between two columns."""
    if not values_a or not values_b:
        return {
            'overlap_percent': 0,
            'matching_count': 0,
            'source_count': len(values_a) if values_a else 0,
            'target_count': len(values_b) if values_b else 0,
            'sample_matches': [],
        }
    
    # Find intersection
    intersection = values_a & values_b
    
    # Calculate overlap as percentage of smaller set
    smaller_size = min(len(values_a), len(values_b))
    overlap_percent = (len(intersection) / smaller_size * 100) if smaller_size > 0 else 0
    
    return {
        'overlap_percent': round(overlap_percent, 1),
        'matching_count': len(intersection),
        'source_count': len(values_a),
        'target_count': len(values_b),
        'sample_matches': list(intersection)[:5],
    }


# =============================================================================
# HELPERS
# =============================================================================

def get_status(confidence: float) -> str:
    """Get verification status based on confidence."""
    if confidence >= 0.9:
        return 'verified'
    elif confidence >= 0.75:
        return 'likely'
    else:
        return 'needs_review'


def deduplicate_relationships(relationships: List[Dict]) -> List[Dict]:
    """Remove duplicate relationships, keeping highest confidence."""
    seen = {}
    
    for rel in relationships:
        # Create key from table pair (order-independent) and columns
        tables = tuple(sorted([rel['source_table'], rel['target_table']]))
        cols = tuple(sorted([rel['source_column'], rel['target_column']]))
        key = (tables, cols)
        
        if key not in seen or rel['confidence'] > seen[key]['confidence']:
            seen[key] = rel
    
    return list(seen.values())


def limit_per_pair(relationships: List[Dict], max_per_pair: int = 3) -> List[Dict]:
    """Limit relationships per table pair to avoid noise."""
    pair_counts = defaultdict(int)
    result = []
    
    for rel in relationships:
        tables = tuple(sorted([rel['source_table'], rel['target_table']]))
        
        if pair_counts[tables] < max_per_pair:
            result.append(rel)
            pair_counts[tables] += 1
    
    return result


def empty_result(table_count: int, error: str = None) -> Dict:
    """Return empty result structure."""
    return {
        'relationships': [],
        'semantic_types': [],
        'unmatched_columns': [],
        'stats': {
            'tables_analyzed': table_count,
            'relationships_found': 0,
            'method': 'semantic_first_v4',
            'error': error,
        }
    }
