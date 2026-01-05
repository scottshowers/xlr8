"""
RELATIONSHIP DETECTOR v5.0 - SCORING-BASED DETECTION
======================================================

Uses TableSelector-style scoring for relationship detection:
1. Domain scoring: Tables in same domain get boosted
2. Semantic type scoring: Columns with matching semantic types
3. Name scoring: Exact and normalized name matches
4. Value validation: Actual data overlap confirms relationships
5. Penalties: Same-table, low overlap, blacklisted columns

This version USES our profiling data properly instead of simple name matching.

Deploy to: backend/utils/relationship_detector.py
"""

import json
import logging
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


# =============================================================================
# SCORING CONFIGURATION
# =============================================================================

# Relationship scores (similar to TableSelector)
SCORE_EXACT_NAME = 100         # job_code ↔ job_code
SCORE_NORMALIZED_NAME = 70     # home_company_code ↔ company_code (after prefix strip)
SCORE_SEMANTIC_MATCH = 80      # Both tagged as "job_code" semantic type
SCORE_DOMAIN_MATCH = 50        # Tables are in same domain (earnings ↔ earnings)
SCORE_VALUE_OVERLAP_HIGH = 40  # 50%+ value overlap
SCORE_VALUE_OVERLAP_MED = 20   # 20-50% value overlap

# Penalties
PENALTY_SAME_TABLE = -1000     # NEVER relate columns in same table
PENALTY_LOW_VALUE_OVERLAP = -30  # <10% value overlap
PENALTY_BLACKLISTED = -500     # Column is in blacklist
PENALTY_NOT_KEY = -20          # Column doesn't look like a key

# Thresholds
MIN_SCORE_THRESHOLD = 80       # Minimum score to consider relationship valid
MIN_VALUE_OVERLAP = 10         # Minimum % overlap to validate (10%)
MAX_RELATIONSHIPS = 500        # Cap to avoid performance issues

# Known column name prefixes to strip for matching
STRIP_PREFIXES = ['home_', 'source_', 'target_', 'from_', 'to_', 'primary_', 
                  'secondary_', 'old_', 'new_', 'prev_', 'current_']

# Columns that should NEVER be relationship keys
BLACKLIST_COLUMNS = {
    'id', 'row_id', 'index', 'created_at', 'updated_at', 'timestamp',
    'description', 'name', 'notes', 'comment', 'comments', 'text',
    'address', 'street', 'city', 'state', 'country', 'country_code',
    'status', 'flag', 'active', 'deleted', 'is_active', 'is_deleted',
    'sort_order', 'display_order', 'sequence', 'row_number',
}

# Column name patterns that indicate relationship keys
KEY_PATTERNS = [
    '_code', '_id', '_num', '_number', '_key', '_type',
    'employee_number', 'company_code', 'job_code', 'location_code',
    'department_code', 'earning_code', 'deduction_code', 'tax_code',
    'pay_group', 'org_level', 'cost_center', 'gl_account',
]


# =============================================================================
# MAIN FUNCTION
# =============================================================================

async def analyze_project_relationships(project: str, tables: List[Dict], handler=None) -> Dict:
    """
    Detect relationships using SCORING-BASED matching (like TableSelector).
    
    Algorithm:
    1. Load all profiling data (semantic types, values, domains)
    2. For each column pair across different tables:
       - Calculate relationship SCORE
       - Include only if score >= threshold
    3. Validate with value overlap
    4. Return sorted by confidence
    
    Args:
        project: Project name
        tables: List of table dicts (for compatibility)
        handler: DuckDB handler
        
    Returns:
        Dict with 'relationships' list and stats
    """
    logger.warning(f"[RELATIONSHIP-V5] Starting SCORING-BASED detection for {project}")
    
    # Get handler if not provided
    if handler is None:
        try:
            from utils.structured_data_handler import get_structured_handler
            handler = get_structured_handler()
        except ImportError:
            from backend.utils.structured_data_handler import get_structured_handler
            handler = get_structured_handler()
    
    if not handler or not hasattr(handler, 'conn'):
        logger.error("[RELATIONSHIP-V5] No database handler available")
        return _empty_result()
    
    # Load all profiling data
    semantic_types = _load_semantic_types(project, handler)
    logger.warning(f"[RELATIONSHIP-V5] Loaded {len(semantic_types)} semantic type mappings")
    
    column_values = _load_column_values(project, handler)
    logger.warning(f"[RELATIONSHIP-V5] Loaded {len(column_values)} column value profiles")
    
    table_domains = _load_table_domains(project, handler)
    logger.warning(f"[RELATIONSHIP-V5] Loaded {len(table_domains)} table domain mappings")
    
    # Build column index with all metadata
    columns_by_table = _build_column_index(project, semantic_types, column_values, handler)
    logger.warning(f"[RELATIONSHIP-V5] Built index for {len(columns_by_table)} tables")
    
    # Find relationships using scoring
    relationships = _find_relationships_scored(
        columns_by_table, 
        column_values, 
        table_domains
    )
    
    # Sort by confidence descending
    relationships.sort(key=lambda r: r['confidence'], reverse=True)
    
    # Cap at max
    if len(relationships) > MAX_RELATIONSHIPS:
        logger.warning(f"[RELATIONSHIP-V5] Capping {len(relationships)} relationships to {MAX_RELATIONSHIPS}")
        relationships = relationships[:MAX_RELATIONSHIPS]
    
    high_conf = sum(1 for r in relationships if r['confidence'] >= 0.9)
    med_conf = sum(1 for r in relationships if 0.7 <= r['confidence'] < 0.9)
    
    logger.warning(f"[RELATIONSHIP-V5] Found {len(relationships)} relationships "
                   f"({high_conf} high confidence, {med_conf} medium)")
    
    return {
        'relationships': relationships,
        'semantic_types': list(set(semantic_types.values())),
        'stats': {
            'total': len(relationships),
            'high_confidence': high_conf,
            'needs_review': med_conf,
            'tables_analyzed': len(columns_by_table),
            'semantic_mappings': len(semantic_types),
            'value_profiles': len(column_values),
        }
    }


def _empty_result() -> Dict:
    """Return empty result structure."""
    return {
        'relationships': [],
        'semantic_types': [],
        'stats': {
            'total': 0,
            'high_confidence': 0,
            'needs_review': 0,
        }
    }


# =============================================================================
# DATA LOADING
# =============================================================================

def _load_semantic_types(project: str, handler) -> Dict[Tuple[str, str], str]:
    """Load semantic types from _column_mappings."""
    semantic_types = {}
    
    try:
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
        logger.warning(f"[RELATIONSHIP-V5] Failed to load semantic types: {e}")
    
    return semantic_types


def _load_column_values(project: str, handler) -> Dict[Tuple[str, str], Set[str]]:
    """Load distinct values from _column_profiles.distinct_values."""
    column_values = {}
    
    try:
        project_prefix = project[:8].lower() if project else ''
        
        # Use distinct_values which stores actual column VALUES
        result = handler.conn.execute("""
            SELECT table_name, column_name, distinct_values, distinct_count
            FROM _column_profiles
            WHERE LOWER(table_name) LIKE ? || '%'
              AND distinct_values IS NOT NULL
              AND distinct_count >= 2
              AND distinct_count <= 1000
        """, [project_prefix]).fetchall()
        
        for row in result:
            table_name, column_name, values_json, distinct_count = row
            
            col_lower = column_name.lower()
            if col_lower in BLACKLIST_COLUMNS:
                continue
            
            if values_json:
                try:
                    values = json.loads(values_json) if isinstance(values_json, str) else values_json
                    if isinstance(values, list):
                        # Extract values (handles both simple lists and dict format)
                        val_set = set()
                        for v in values:
                            if isinstance(v, dict):
                                val = str(v.get('value', '')).lower().strip()
                            else:
                                val = str(v).lower().strip()
                            if val and len(val) >= 1:
                                val_set.add(val)
                        if val_set:
                            column_values[(table_name, column_name)] = val_set
                except Exception:
                    pass
                    
    except Exception as e:
        logger.warning(f"[RELATIONSHIP-V5] Failed to load column values: {e}")
    
    return column_values


def _load_table_domains(project: str, handler) -> Dict[str, str]:
    """Load table domain classifications from _schema_metadata."""
    table_domains = {}
    
    try:
        project_prefix = project[:8].lower() if project else ''
        
        # Try to get domain from truth_type or detected_domain
        result = handler.conn.execute("""
            SELECT table_name, truth_type
            FROM _schema_metadata
            WHERE LOWER(table_name) LIKE ? || '%'
              AND is_current = TRUE
        """, [project_prefix]).fetchall()
        
        for row in result:
            table_name, truth_type = row
            if truth_type:
                table_domains[table_name] = truth_type.lower()
                
    except Exception as e:
        logger.warning(f"[RELATIONSHIP-V5] Failed to load table domains: {e}")
    
    return table_domains


def _build_column_index(project: str, semantic_types: Dict, 
                        column_values: Dict, handler) -> Dict[str, List[Dict]]:
    """Build index of columns by table with all metadata."""
    tables_columns = defaultdict(list)
    
    try:
        project_prefix = project[:8].lower() if project else ''
        
        result = handler.conn.execute("""
            SELECT DISTINCT table_name, column_name
            FROM _column_profiles
            WHERE LOWER(table_name) LIKE ? || '%'
        """, [project_prefix]).fetchall()
        
        for row in result:
            table_name, column_name = row
            col_lower = column_name.lower()
            
            # Skip system columns
            if col_lower.startswith('_'):
                continue
            
            # Check if likely a key column
            is_key = any(pattern in col_lower for pattern in KEY_PATTERNS)
            is_blacklisted = col_lower in BLACKLIST_COLUMNS
            
            col_info = {
                'name': column_name,
                'normalized': _normalize_column_name(column_name),
                'semantic_type': semantic_types.get((table_name, column_name)),
                'has_values': (table_name, column_name) in column_values,
                'is_likely_key': is_key,
                'is_blacklisted': is_blacklisted,
            }
            
            tables_columns[table_name].append(col_info)
            
    except Exception as e:
        logger.warning(f"[RELATIONSHIP-V5] Failed to build column index: {e}")
    
    return dict(tables_columns)


def _normalize_column_name(name: str) -> str:
    """Normalize column name by stripping known prefixes."""
    name = name.lower().strip()
    
    for prefix in STRIP_PREFIXES:
        if name.startswith(prefix):
            name = name[len(prefix):]
            break
    
    return name


# =============================================================================
# RELATIONSHIP SCORING
# =============================================================================

def _find_relationships_scored(columns_by_table: Dict[str, List[Dict]],
                                column_values: Dict[Tuple[str, str], Set[str]],
                                table_domains: Dict[str, str]) -> List[Dict]:
    """
    Find relationships using scoring-based matching.
    
    For each column pair:
    1. Calculate base score from name/semantic matching
    2. Apply domain bonus if tables are in same domain
    3. Validate with value overlap
    4. Apply penalties as needed
    5. Include if total score >= threshold
    """
    relationships = []
    seen_pairs = set()  # Avoid duplicates
    
    table_names = list(columns_by_table.keys())
    
    for i, table_a in enumerate(table_names):
        cols_a = columns_by_table[table_a]
        domain_a = table_domains.get(table_a, 'unknown')
        
        for j, table_b in enumerate(table_names):
            # Skip if same table or already processed reverse
            if i >= j:
                continue
            
            cols_b = columns_by_table[table_b]
            domain_b = table_domains.get(table_b, 'unknown')
            
            # Check domain match
            same_domain = (domain_a == domain_b and domain_a != 'unknown')
            
            # Score each column pair
            for col_a in cols_a:
                for col_b in cols_b:
                    score, match_type = _score_column_pair(
                        col_a, col_b, same_domain
                    )
                    
                    # Skip if below threshold
                    if score < MIN_SCORE_THRESHOLD:
                        continue
                    
                    # Validate with value overlap
                    values_a = column_values.get((table_a, col_a['name']))
                    values_b = column_values.get((table_b, col_b['name']))
                    
                    overlap_pct = 0
                    if values_a and values_b:
                        overlap_pct = _calculate_overlap(values_a, values_b)
                        
                        # Apply value-based scoring adjustments
                        if overlap_pct >= 50:
                            score += SCORE_VALUE_OVERLAP_HIGH
                            match_type += '+value_high'
                        elif overlap_pct >= 20:
                            score += SCORE_VALUE_OVERLAP_MED
                            match_type += '+value_med'
                        elif overlap_pct < MIN_VALUE_OVERLAP and match_type.startswith('normalized'):
                            # Low overlap on a weak match - penalize
                            score += PENALTY_LOW_VALUE_OVERLAP
                            match_type += '+low_overlap'
                    
                    # Final threshold check
                    if score < MIN_SCORE_THRESHOLD:
                        continue
                    
                    # Avoid duplicate pairs
                    pair_key = tuple(sorted([
                        f"{table_a}.{col_a['name']}",
                        f"{table_b}.{col_b['name']}"
                    ]))
                    if pair_key in seen_pairs:
                        continue
                    seen_pairs.add(pair_key)
                    
                    # Convert score to confidence (0-1 range)
                    confidence = min(0.98, score / 150)  # 150 max realistic score
                    
                    relationships.append({
                        'source_table': table_a,
                        'source_column': col_a['name'],
                        'target_table': table_b,
                        'target_column': col_b['name'],
                        'confidence': round(confidence, 2),
                        'relationship_type': 'one-to-many',
                        'match_type': match_type,
                        'value_overlap': overlap_pct,
                        'semantic_type': col_a.get('semantic_type') or col_b.get('semantic_type'),
                        'score': score,
                    })
    
    return relationships


def _score_column_pair(col_a: Dict, col_b: Dict, same_domain: bool) -> Tuple[int, str]:
    """
    Calculate relationship score for a column pair.
    
    Returns (score, match_type)
    """
    score = 0
    match_type = ''
    
    # Apply penalties first
    if col_a.get('is_blacklisted') or col_b.get('is_blacklisted'):
        return (PENALTY_BLACKLISTED, 'blacklisted')
    
    if not col_a.get('is_likely_key'):
        score += PENALTY_NOT_KEY
    if not col_b.get('is_likely_key'):
        score += PENALTY_NOT_KEY
    
    # 1. Exact name match (highest)
    if col_a['name'].lower() == col_b['name'].lower():
        score += SCORE_EXACT_NAME
        match_type = 'exact_name'
    
    # 2. Normalized name match (after prefix strip)
    elif col_a['normalized'] == col_b['normalized']:
        score += SCORE_NORMALIZED_NAME
        match_type = 'normalized_name'
    
    # 3. Semantic type match
    elif (col_a.get('semantic_type') and col_b.get('semantic_type') and 
          col_a['semantic_type'] == col_b['semantic_type']):
        score += SCORE_SEMANTIC_MATCH
        match_type = 'semantic_type'
    
    else:
        # No match
        return (0, 'no_match')
    
    # Domain bonus
    if same_domain and match_type:
        score += SCORE_DOMAIN_MATCH
        match_type += '+domain'
    
    return (score, match_type)


def _calculate_overlap(values_a: Set[str], values_b: Set[str]) -> int:
    """Calculate percentage overlap between two value sets."""
    if not values_a or not values_b:
        return 0
    
    intersection = values_a & values_b
    smaller_set = min(len(values_a), len(values_b))
    
    if smaller_set == 0:
        return 0
    
    return int((len(intersection) / smaller_set) * 100)


# =============================================================================
# LEGACY COMPATIBILITY
# =============================================================================

# Keep these for backward compatibility with existing code

def get_semantic_types(project: str, handler=None) -> Dict[Tuple[str, str], str]:
    """Legacy wrapper for _load_semantic_types."""
    return _load_semantic_types(project, handler)


def get_column_values(project: str, handler=None) -> Dict[Tuple[str, str], Set[str]]:
    """Legacy wrapper for _load_column_values."""
    return _load_column_values(project, handler)


def build_column_index(project: str, semantic_types: Dict, 
                       column_values: Dict, handler=None) -> Dict[str, List[Dict]]:
    """Legacy wrapper for _build_column_index."""
    return _build_column_index(project, semantic_types, column_values, handler)
