"""
FK Detector - Foreign Key Detection Using Actual Data Values
=============================================================

Detects FK relationships by comparing actual VALUES between tables,
not just column names.

Algorithm:
1. Find all "key-like" columns (ending in _code, _id, Code, Id, etc.)
2. For each key column in a "spoke" table, check if values exist in a "hub" table
3. Calculate coverage: what % of spoke values exist in hub?
4. If coverage > threshold, it's a FK relationship

This is REAL FK detection - based on data, not guesses.

Deploy to: backend/utils/fk_detector.py
"""

import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


def detect_foreign_keys(conn, customer_id: str, min_coverage: float = 50.0) -> List[Dict[str, Any]]:
    """
    Detect FK relationships by comparing actual data values.
    
    Args:
        conn: DuckDB connection
        customer_id: Customer UUID (table prefix)
        min_coverage: Minimum % of spoke values that must exist in hub (default 50%)
        
    Returns:
        List of detected FK relationships with coverage stats
    """
    logger.info(f"[FK-DETECT] Starting FK detection for {customer_id}")
    
    # Get all tables for this customer
    prefix = customer_id[:8]
    all_tables = conn.execute("SHOW TABLES").fetchall()
    customer_tables = [t[0] for t in all_tables 
                       if (t[0].startswith(prefix) or t[0].startswith(customer_id)) 
                       and not t[0].startswith('_')]
    
    logger.info(f"[FK-DETECT] Found {len(customer_tables)} tables to analyze")
    
    if not customer_tables:
        return []
    
    # Step 1: Build index of all key columns and their distinct values
    # key_columns[normalized_col_name] = [(table_name, col_name, values_set, cardinality)]
    key_columns = defaultdict(list)
    
    # Patterns that indicate a key column
    KEY_PATTERNS = ['_code', '_id', 'code', 'id', '_no', '_num', '_key']
    
    for table_name in customer_tables:
        try:
            # Get columns
            columns = conn.execute(f"PRAGMA table_info('{table_name}')").fetchall()
            
            for col_info in columns:
                col_name = col_info[1]
                if not col_name or col_name.startswith('_'):
                    continue
                
                col_lower = col_name.lower()
                
                # Check if this looks like a key column
                is_key_col = any(p in col_lower for p in KEY_PATTERNS)
                if not is_key_col:
                    continue
                
                # Get distinct values (limit to 10000 for performance)
                try:
                    values_result = conn.execute(f'''
                        SELECT DISTINCT LOWER(TRIM(CAST("{col_name}" AS VARCHAR))) as val
                        FROM "{table_name}"
                        WHERE "{col_name}" IS NOT NULL 
                          AND TRIM(CAST("{col_name}" AS VARCHAR)) != ''
                        LIMIT 10000
                    ''').fetchall()
                    
                    values_set = {r[0] for r in values_result if r[0]}
                    cardinality = len(values_set)
                    
                    if cardinality > 0:
                        # Normalize column name for grouping
                        col_normalized = col_lower.replace('_', '').replace(' ', '')
                        key_columns[col_normalized].append({
                            'table': table_name,
                            'column': col_name,
                            'values': values_set,
                            'cardinality': cardinality
                        })
                        
                except Exception as e:
                    logger.debug(f"[FK-DETECT] Error getting values for {table_name}.{col_name}: {e}")
                    
        except Exception as e:
            logger.debug(f"[FK-DETECT] Error analyzing {table_name}: {e}")
    
    logger.info(f"[FK-DETECT] Found {len(key_columns)} unique key column patterns")
    
    # Step 2: For each column pattern, find hub (highest cardinality) and spokes
    foreign_keys = []
    
    for col_pattern, tables_with_col in key_columns.items():
        if len(tables_with_col) < 2:
            continue  # Need at least 2 tables to have a relationship
        
        # Sort by cardinality descending - highest is likely the hub
        tables_with_col.sort(key=lambda x: x['cardinality'], reverse=True)
        
        # Hub is the one with most distinct values
        hub = tables_with_col[0]
        hub_values = hub['values']
        
        # Check each other table as potential spoke
        for spoke in tables_with_col[1:]:
            spoke_values = spoke['values']
            
            if not spoke_values:
                continue
            
            # Calculate overlap: how many spoke values exist in hub?
            overlap = spoke_values & hub_values
            coverage_pct = (len(overlap) / len(spoke_values)) * 100 if spoke_values else 0
            
            # Also check if spoke is subset of hub
            is_subset = spoke_values <= hub_values
            
            if coverage_pct >= min_coverage:
                foreign_keys.append({
                    'source_table': spoke['table'],
                    'source_column': spoke['column'],
                    'target_table': hub['table'],
                    'target_column': hub['column'],
                    'source_cardinality': spoke['cardinality'],
                    'target_cardinality': hub['cardinality'],
                    'overlap_count': len(overlap),
                    'coverage_pct': round(coverage_pct, 1),
                    'is_subset': is_subset,
                    'column_pattern': col_pattern
                })
                
                logger.debug(f"[FK-DETECT] Found FK: {spoke['table']}.{spoke['column']} → {hub['table']}.{hub['column']} ({coverage_pct:.0f}%)")
    
    # Sort by coverage descending
    foreign_keys.sort(key=lambda x: x['coverage_pct'], reverse=True)
    
    logger.info(f"[FK-DETECT] Detected {len(foreign_keys)} FK relationships")
    
    return foreign_keys


def generate_fk_report(fk_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate a human-readable report of FK detection results."""
    
    if not fk_results:
        return {
            'total_fks': 0,
            'summary': 'No foreign key relationships detected',
            'by_hub': {},
            'high_confidence': [],
            'low_confidence': []
        }
    
    # Group by target (hub) table
    by_hub = defaultdict(list)
    for fk in fk_results:
        hub_key = f"{fk['target_table']}.{fk['target_column']}"
        by_hub[hub_key].append(fk)
    
    # Separate high vs low confidence
    high_confidence = [fk for fk in fk_results if fk['coverage_pct'] >= 80]
    low_confidence = [fk for fk in fk_results if fk['coverage_pct'] < 80]
    
    return {
        'total_fks': len(fk_results),
        'high_confidence_count': len(high_confidence),
        'low_confidence_count': len(low_confidence),
        'hub_count': len(by_hub),
        'by_hub': {k: len(v) for k, v in by_hub.items()},
        'high_confidence': high_confidence[:20],  # Top 20
        'low_confidence': low_confidence[:10]
    }


def update_column_mappings(conn, customer_id: str, fk_results: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Update _column_mappings table with detected FK relationships.
    
    Returns:
        Stats about updates made
    """
    if not fk_results:
        return {'updated': 0, 'skipped': 0}
    
    updated = 0
    skipped = 0
    
    for fk in fk_results:
        try:
            # Check if mapping exists
            existing = conn.execute('''
                SELECT id FROM _column_mappings 
                WHERE project = ? AND table_name = ? AND column_name = ?
            ''', [customer_id, fk['source_table'], fk['source_column']]).fetchone()
            
            if existing:
                # Update existing
                conn.execute('''
                    UPDATE _column_mappings 
                    SET hub_table = ?, hub_column = ?, hub_cardinality = ?,
                        spoke_cardinality = ?, coverage_pct = ?, is_subset = ?,
                        is_hub = FALSE
                    WHERE project = ? AND table_name = ? AND column_name = ?
                ''', [
                    fk['target_table'], fk['target_column'], fk['target_cardinality'],
                    fk['source_cardinality'], fk['coverage_pct'], fk['is_subset'],
                    customer_id, fk['source_table'], fk['source_column']
                ])
                updated += 1
            else:
                # Insert new
                conn.execute('''
                    INSERT INTO _column_mappings 
                    (project, table_name, column_name, hub_table, hub_column, 
                     hub_cardinality, spoke_cardinality, coverage_pct, is_subset, is_hub)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, FALSE)
                ''', [
                    customer_id, fk['source_table'], fk['source_column'],
                    fk['target_table'], fk['target_column'],
                    fk['target_cardinality'], fk['source_cardinality'],
                    fk['coverage_pct'], fk['is_subset']
                ])
                updated += 1
                
        except Exception as e:
            logger.debug(f"[FK-DETECT] Error updating mapping: {e}")
            skipped += 1
    
    try:
        conn.execute("CHECKPOINT")
    except Exception:
        pass
    
    return {'updated': updated, 'skipped': skipped}


def detect_and_apply(conn, customer_id: str, min_coverage: float = 50.0) -> Dict[str, Any]:
    """
    Convenience function: detect FKs and apply to column mappings.
    
    Returns:
        Combined results
    """
    fk_results = detect_foreign_keys(conn, customer_id, min_coverage)
    report = generate_fk_report(fk_results)
    update_stats = update_column_mappings(conn, customer_id, fk_results)
    
    return {
        'detection': report,
        'updates': update_stats,
        'foreign_keys': fk_results
    }
