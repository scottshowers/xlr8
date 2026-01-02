"""
Relationship Detector v3 - VALUE-BASED relationship detection.

THE RIGHT WAY: Compare actual column VALUES, not just column names.

Uses _column_profiles.distinct_values to find columns with overlapping values.
If Column A has values ['USA', 'CAN', 'GBR'] and Column B has ['USA', 'CAN', 'MEX'],
they share 66% of values = potential JOIN relationship.

This is how real data profiling works.
"""

import json
import logging
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

# Minimum overlap percentage to consider a relationship
MIN_OVERLAP_PERCENT = 20  # At least 20% of values must match

# Maximum distinct values for a column to be considered a "key" column
# Columns with too many values (like names, descriptions) aren't good join keys
MAX_DISTINCT_VALUES = 500

# Minimum distinct values - single-value columns aren't useful for joins
MIN_DISTINCT_VALUES = 2

# Confidence thresholds based on overlap
CONFIDENCE_EXCELLENT = 0.80  # 80%+ overlap
CONFIDENCE_GOOD = 0.50       # 50-79% overlap  
CONFIDENCE_WEAK = 0.20       # 20-49% overlap

# Skip columns with these patterns (descriptions, names, free text)
SKIP_COLUMN_PATTERNS = [
    '_desc', 'description', '_name', '_text', '_comment', '_note',
    '_address', '_street', '_city', '_message', '_reason',
]

# Prioritize columns with these patterns (likely join keys)
KEY_COLUMN_PATTERNS = [
    '_id', '_code', '_num', '_number', '_key', '_type',
    'emp', 'company', 'dept', 'job', 'location', 'earn', 'deduct', 'tax',
]


# =============================================================================
# MAIN FUNCTION
# =============================================================================

async def analyze_project_relationships(project: str, tables: List[Dict], llm_client = None) -> Dict:
    """
    Detect relationships between tables by comparing actual column VALUES.
    
    Args:
        project: Project name for filtering
        tables: List of table dicts with 'name'/'table_name' and 'columns'
        llm_client: Not used in v3 (kept for API compatibility)
        
    Returns:
        Dict with 'relationships' list and stats
    """
    logger.info(f"[RELATIONSHIP-V3] Analyzing {len(tables)} tables using VALUE-BASED detection")
    
    # Get column profiles from DuckDB
    column_values = get_column_values(project)
    
    if not column_values:
        logger.warning("[RELATIONSHIP-V3] No column profiles found - run upload first to populate _column_profiles")
        return {
            'relationships': [],
            'semantic_types': [],
            'unmatched_columns': [],
            'stats': {
                'tables_analyzed': len(tables),
                'columns_with_values': 0,
                'relationships_found': 0,
                'high_confidence': 0,
                'needs_review': 0,
                'method': 'value_based_v3',
                'error': 'No column profiles found. Upload data to populate _column_profiles.distinct_values'
            }
        }
    
    logger.info(f"[RELATIONSHIP-V3] Found {len(column_values)} columns with value profiles")
    
    # Group columns by table
    tables_columns = defaultdict(dict)
    for (table_name, col_name), values in column_values.items():
        tables_columns[table_name][col_name] = values
    
    logger.info(f"[RELATIONSHIP-V3] {len(tables_columns)} tables have profiled columns")
    
    # Find relationships by comparing values across tables
    relationships = []
    comparisons = 0
    
    table_names = list(tables_columns.keys())
    
    for i, table_a in enumerate(table_names):
        cols_a = tables_columns[table_a]
        
        for table_b in table_names[i+1:]:
            cols_b = tables_columns[table_b]
            
            # Compare each column pair between the two tables
            for col_a, values_a in cols_a.items():
                for col_b, values_b in cols_b.items():
                    comparisons += 1
                    
                    # Calculate value overlap
                    overlap_info = calculate_value_overlap(values_a, values_b)
                    
                    if overlap_info['overlap_percent'] >= MIN_OVERLAP_PERCENT:
                        confidence = get_confidence(overlap_info['overlap_percent'])
                        
                        relationships.append({
                            'source_table': table_a,
                            'source_column': col_a,
                            'target_table': table_b,
                            'target_column': col_b,
                            'confidence': confidence,
                            'match_rate': overlap_info['overlap_percent'],
                            'matching_values': overlap_info['matching_count'],
                            'source_distinct': overlap_info['source_count'],
                            'target_distinct': overlap_info['target_count'],
                            'sample_matches': overlap_info['sample_matches'][:5],
                            'method': 'value_overlap',
                            'verification_status': get_status(overlap_info['overlap_percent']),
                            'needs_review': overlap_info['overlap_percent'] < 80,
                            'confirmed': False,
                        })
    
    logger.info(f"[RELATIONSHIP-V3] Made {comparisons} comparisons, found {len(relationships)} relationships")
    
    # Sort by confidence/match_rate descending
    relationships.sort(key=lambda x: x['match_rate'], reverse=True)
    
    # Deduplicate (keep highest confidence for each table pair)
    relationships = deduplicate_relationships(relationships)
    
    # Limit per table pair
    relationships = limit_per_pair(relationships, max_per_pair=5)
    
    # Stats
    high_conf = sum(1 for r in relationships if r['confidence'] >= CONFIDENCE_EXCELLENT)
    medium_conf = sum(1 for r in relationships if CONFIDENCE_GOOD <= r['confidence'] < CONFIDENCE_EXCELLENT)
    low_conf = sum(1 for r in relationships if r['confidence'] < CONFIDENCE_GOOD)
    
    logger.info(f"[RELATIONSHIP-V3] Final: {len(relationships)} relationships ({high_conf} excellent, {medium_conf} good, {low_conf} weak)")
    
    return {
        'relationships': relationships,
        'semantic_types': [],  # Not used in v3 - kept for API compatibility
        'unmatched_columns': [],  # Not used in v3 - kept for API compatibility
        'stats': {
            'tables_analyzed': len(tables),
            'tables_with_profiles': len(tables_columns),
            'columns_with_values': len(column_values),
            'comparisons_made': comparisons,
            'relationships_found': len(relationships),
            'high_confidence': high_conf,
            'medium_confidence': medium_conf,
            'low_confidence': low_conf,
            'needs_review': sum(1 for r in relationships if r.get('needs_review')),
            'method': 'value_based_v3',
        }
    }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_column_values(project: str = None) -> Dict[Tuple[str, str], Set[str]]:
    """
    Get column values from _column_profiles.distinct_values.
    
    Returns dict of (table_name, column_name) -> set of values
    """
    try:
        from utils.structured_data_handler import get_structured_handler
        handler = get_structured_handler()
        
        # Query _column_profiles for columns with distinct_values
        if project:
            query = """
                SELECT table_name, column_name, distinct_values, distinct_count
                FROM _column_profiles
                WHERE distinct_values IS NOT NULL 
                  AND distinct_values != '[]'
                  AND distinct_values != 'null'
                  AND LOWER(table_name) LIKE LOWER(?) || '%'
            """
            results = handler.conn.execute(query, [project]).fetchall()
        else:
            query = """
                SELECT table_name, column_name, distinct_values, distinct_count
                FROM _column_profiles
                WHERE distinct_values IS NOT NULL 
                  AND distinct_values != '[]'
                  AND distinct_values != 'null'
            """
            results = handler.conn.execute(query).fetchall()
        
        column_values = {}
        
        for row in results:
            table_name = row[0]
            col_name = row[1]
            distinct_values_json = row[2]
            distinct_count = row[3] or 0
            
            # Skip columns with too many or too few distinct values
            if distinct_count > MAX_DISTINCT_VALUES or distinct_count < MIN_DISTINCT_VALUES:
                continue
            
            # Skip description/text columns
            col_lower = col_name.lower()
            if any(pattern in col_lower for pattern in SKIP_COLUMN_PATTERNS):
                continue
            
            # Parse distinct values
            try:
                if isinstance(distinct_values_json, str):
                    values_list = json.loads(distinct_values_json)
                else:
                    values_list = distinct_values_json
                
                if not values_list:
                    continue
                
                # Extract just the values (distinct_values is list of [value, count] pairs or just values)
                if isinstance(values_list[0], list):
                    values = set(str(v[0]) for v in values_list if v[0] is not None)
                else:
                    values = set(str(v) for v in values_list if v is not None)
                
                if len(values) >= MIN_DISTINCT_VALUES:
                    column_values[(table_name, col_name)] = values
                    
            except (json.JSONDecodeError, TypeError, IndexError) as e:
                logger.debug(f"[RELATIONSHIP-V3] Could not parse values for {table_name}.{col_name}: {e}")
                continue
        
        return column_values
        
    except Exception as e:
        logger.error(f"[RELATIONSHIP-V3] Failed to get column values: {e}")
        return {}


def calculate_value_overlap(values_a: Set[str], values_b: Set[str]) -> Dict:
    """
    Calculate overlap between two sets of values.
    
    Returns overlap statistics.
    """
    if not values_a or not values_b:
        return {
            'overlap_percent': 0,
            'matching_count': 0,
            'source_count': len(values_a) if values_a else 0,
            'target_count': len(values_b) if values_b else 0,
            'sample_matches': [],
        }
    
    # Find intersection
    matching = values_a & values_b
    matching_count = len(matching)
    
    # Calculate overlap as percentage of the SMALLER set
    # This handles cases where one table has a subset of another's values
    smaller_count = min(len(values_a), len(values_b))
    overlap_percent = round((matching_count / smaller_count) * 100, 1) if smaller_count > 0 else 0
    
    return {
        'overlap_percent': overlap_percent,
        'matching_count': matching_count,
        'source_count': len(values_a),
        'target_count': len(values_b),
        'sample_matches': list(matching)[:10],
    }


def get_confidence(overlap_percent: float) -> float:
    """Convert overlap percentage to confidence score (0-1)."""
    if overlap_percent >= 80:
        return round(overlap_percent / 100, 2)
    elif overlap_percent >= 50:
        return round(0.5 + (overlap_percent - 50) / 100, 2)
    else:
        return round(overlap_percent / 100, 2)


def get_status(overlap_percent: float) -> str:
    """Get verification status based on overlap."""
    if overlap_percent >= 80:
        return 'good'
    elif overlap_percent >= 50:
        return 'partial'
    elif overlap_percent >= 20:
        return 'weak'
    else:
        return 'none'


def deduplicate_relationships(relationships: List[Dict]) -> List[Dict]:
    """Remove duplicate relationships, keeping highest confidence."""
    seen = {}
    
    for rel in relationships:
        # Create canonical key for the column pair
        key = tuple(sorted([
            f"{rel['source_table']}.{rel['source_column']}",
            f"{rel['target_table']}.{rel['target_column']}"
        ]))
        
        if key not in seen or rel['match_rate'] > seen[key]['match_rate']:
            seen[key] = rel
    
    return list(seen.values())


def limit_per_pair(relationships: List[Dict], max_per_pair: int = 5) -> List[Dict]:
    """Limit relationships per table pair to avoid noise."""
    pair_counts = defaultdict(int)
    limited = []
    
    for rel in relationships:
        pair = tuple(sorted([rel['source_table'], rel['target_table']]))
        
        if pair_counts[pair] < max_per_pair:
            limited.append(rel)
            pair_counts[pair] += 1
    
    return limited


# =============================================================================
# TEST A SPECIFIC RELATIONSHIP
# =============================================================================

def test_relationship(table_a: str, col_a: str, table_b: str, col_b: str, project: str = None) -> Dict:
    """
    Test a specific relationship by comparing actual values.
    
    Returns detailed match statistics with sample data.
    """
    try:
        from utils.structured_data_handler import get_structured_handler
        handler = get_structured_handler()
        
        # Get distinct values from both columns
        query_a = f'SELECT DISTINCT "{col_a}" FROM "{table_a}" WHERE "{col_a}" IS NOT NULL LIMIT 1000'
        query_b = f'SELECT DISTINCT "{col_b}" FROM "{table_b}" WHERE "{col_b}" IS NOT NULL LIMIT 1000'
        
        try:
            values_a = set(str(row[0]) for row in handler.conn.execute(query_a).fetchall())
            values_b = set(str(row[0]) for row in handler.conn.execute(query_b).fetchall())
        except Exception as e:
            return {'error': f'Query failed: {e}'}
        
        # Calculate overlap
        matching = values_a & values_b
        only_in_a = values_a - values_b
        only_in_b = values_b - values_a
        
        smaller = min(len(values_a), len(values_b))
        overlap_percent = round((len(matching) / smaller) * 100, 1) if smaller > 0 else 0
        
        # Get sample rows from each table
        sample_a_query = f'SELECT * FROM "{table_a}" LIMIT 10'
        sample_b_query = f'SELECT * FROM "{table_b}" LIMIT 10'
        
        try:
            sample_a = [dict(zip([d[0] for d in handler.conn.execute(sample_a_query).description], row)) 
                       for row in handler.conn.execute(sample_a_query).fetchall()]
            sample_b = [dict(zip([d[0] for d in handler.conn.execute(sample_b_query).description], row))
                       for row in handler.conn.execute(sample_b_query).fetchall()]
        except:
            sample_a = []
            sample_b = []
        
        # Get row counts
        try:
            count_a = handler.conn.execute(f'SELECT COUNT(*) FROM "{table_a}"').fetchone()[0]
            count_b = handler.conn.execute(f'SELECT COUNT(*) FROM "{table_b}"').fetchone()[0]
        except:
            count_a = 0
            count_b = 0
        
        return {
            'table_a': table_a,
            'table_b': table_b,
            'join_column_a': col_a,
            'join_column_b': col_b,
            'table_a_columns': [d[0] for d in handler.conn.execute(f'SELECT * FROM "{table_a}" LIMIT 1').description] if sample_a else [],
            'table_b_columns': [d[0] for d in handler.conn.execute(f'SELECT * FROM "{table_b}" LIMIT 1').description] if sample_b else [],
            'table_a_sample': sample_a,
            'table_b_sample': sample_b,
            'statistics': {
                'match_rate_percent': overlap_percent,
                'matching_keys': len(matching),
                'orphans_in_a': len(only_in_a),
                'orphans_in_b': len(only_in_b),
                'table_a_rows': count_a,
                'table_b_rows': count_b,
                'distinct_values_a': len(values_a),
                'distinct_values_b': len(values_b),
                'orphan_samples_from_a': list(only_in_a)[:10],
                'orphan_samples_from_b': list(only_in_b)[:10],
                'matching_samples': list(matching)[:10],
            },
            'verification': {
                'status': get_status(overlap_percent),
                'confidence': get_confidence(overlap_percent),
                'message': get_verification_message(overlap_percent),
            }
        }
        
    except Exception as e:
        logger.error(f"[RELATIONSHIP-V3] Test failed: {e}")
        return {'error': str(e)}


def get_verification_message(overlap_percent: float) -> str:
    """Get human-readable verification message."""
    if overlap_percent >= 80:
        return f"Strong relationship with {overlap_percent}% match. Safe to use for JOINs."
    elif overlap_percent >= 50:
        return f"Partial relationship with {overlap_percent}% match. Review orphan values."
    elif overlap_percent >= 20:
        return f"Weak relationship: Only {overlap_percent}% match. Review if these tables should be joined."
    else:
        return f"No matching keys found. These tables may not be related via {overlap_percent}% match."
