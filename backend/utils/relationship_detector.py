"""
RELATIONSHIP DETECTOR v6.0 - CONTEXT GRAPH
===========================================

THE BREAKTHROUGH: Hub/spoke relationships instead of O(n²) pairwise matching.

For each semantic type (company_code, job_code, etc.):
- HUB: Table with MAX cardinality (Component Company has 13 company_codes)
- SPOKES: Tables that reference the hub (Employee uses 6 of those 13)

This is THE THING. The whole platform is about context.

When user asks "W2 analysis":
- W2 = US tax = country_code='US'
- Graph tells us: 2 companies are US
- Graph tells us: X employees in those companies
- No O(n²) matching required

Deploy to: backend/utils/relationship_detector.py
"""

import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


async def analyze_project_relationships(project: str, tables: List[Dict], handler=None) -> Dict:
    """
    Detect relationships using the CONTEXT GRAPH.
    
    This replaces O(n²) pairwise matching with:
    1. Compute the context graph (hub/spoke for each semantic type)
    2. Return hub→spoke relationships
    
    The context graph is computed from:
    - _column_mappings: semantic types for each column
    - _column_profiles: cardinality and values for each column
    
    Args:
        project: Project name
        tables: List of table dicts (for compatibility, not used)
        handler: DuckDB handler (REQUIRED)
        
    Returns:
        Dict with 'relationships' list and stats
    """
    logger.warning(f"[RELATIONSHIP-V6] Starting CONTEXT GRAPH detection for {project}")
    
    # Get handler if not provided
    if handler is None:
        try:
            from utils.structured_data_handler import get_structured_handler
            handler = get_structured_handler()
        except ImportError:
            from backend.utils.structured_data_handler import get_structured_handler
            handler = get_structured_handler()
    
    if not handler:
        logger.error("[RELATIONSHIP-V6] No database handler available")
        return _empty_result()
    
    # Step 1: Compute the context graph
    # This finds hubs and spokes for each semantic type
    graph_stats = handler.compute_context_graph(project)
    
    if graph_stats.get('error'):
        logger.error(f"[RELATIONSHIP-V6] Graph computation failed: {graph_stats['error']}")
        return _empty_result()
    
    logger.warning(f"[RELATIONSHIP-V6] Graph computed: {graph_stats['hubs']} hubs, {graph_stats['spokes']} spokes")
    
    # Step 2: Get the graph as relationships
    graph = handler.get_context_graph(project)
    
    # Step 3: Convert to relationship format (for compatibility with existing code)
    relationships = []
    
    for rel in graph.get('relationships', []):
        # Each spoke→hub is a relationship
        confidence = _calculate_confidence(rel)
        needs_review = confidence < 0.8 or not rel.get('is_valid_fk', False)
        
        relationships.append({
            'source_table': rel['spoke_table'],
            'source_column': rel['spoke_column'],
            'target_table': rel['hub_table'],
            'target_column': rel['hub_column'],
            'confidence': confidence,
            'relationship_type': 'foreign_key' if rel.get('is_valid_fk') else 'reference',
            'match_type': f"context_graph:{rel['semantic_type']}",
            'value_overlap': rel.get('coverage_pct', 0),
            'semantic_type': rel['semantic_type'],
            'hub_cardinality': rel.get('hub_cardinality', 0),
            'spoke_cardinality': rel.get('spoke_cardinality', 0),
            'is_valid_fk': rel.get('is_valid_fk', False),
            'needs_review': needs_review,
            'confirmed': False,
        })
    
    # Sort by confidence
    relationships.sort(key=lambda r: r['confidence'], reverse=True)
    
    high_conf = sum(1 for r in relationships if r['confidence'] >= 0.9)
    med_conf = sum(1 for r in relationships if 0.7 <= r['confidence'] < 0.9)
    
    logger.warning(f"[RELATIONSHIP-V6] Found {len(relationships)} relationships "
                   f"({high_conf} high confidence, {med_conf} medium)")
    
    return {
        'relationships': relationships,
        'semantic_types': [h['semantic_type'] for h in graph.get('hubs', [])],
        'stats': {
            'total': len(relationships),
            'high_confidence': high_conf,
            'needs_review': sum(1 for r in relationships if r.get('needs_review')),
            'hubs': graph_stats.get('hubs', 0),
            'semantic_types': graph_stats.get('semantic_types', 0),
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
            'hubs': 0,
        }
    }


def _calculate_confidence(rel: Dict) -> float:
    """
    Calculate relationship confidence from context graph data.
    
    Factors:
    - is_valid_fk: All spoke values exist in hub (high confidence)
    - coverage_pct: Higher coverage = more confidence
    - spoke_cardinality: More values = more reliable match
    """
    confidence = 0.5  # Base
    
    # Valid FK = high confidence
    if rel.get('is_valid_fk'):
        confidence = 0.9
    
    # Boost for high coverage
    coverage = rel.get('coverage_pct', 0)
    if coverage >= 50:
        confidence = min(0.95, confidence + 0.1)
    elif coverage >= 25:
        confidence = min(0.90, confidence + 0.05)
    
    # Boost for meaningful cardinality
    spoke_card = rel.get('spoke_cardinality', 0)
    if spoke_card >= 5:
        confidence = min(0.98, confidence + 0.03)
    
    return round(confidence, 2)


# =============================================================================
# LEGACY COMPATIBILITY
# =============================================================================

def get_semantic_types(project: str, handler=None) -> Dict:
    """Legacy function - semantic types now in _column_mappings."""
    if not handler:
        return {}
    
    try:
        result = handler.conn.execute("""
            SELECT table_name, original_column, semantic_type
            FROM _column_mappings
            WHERE project = ?
              AND semantic_type IS NOT NULL
              AND semantic_type != 'NONE'
        """, [project[:8].lower()]).fetchall()
        
        return {(row[0], row[1]): row[2] for row in result}
    except Exception:
        return {}


def get_column_values(project: str, handler=None) -> Dict:
    """Legacy function - values now in _column_profiles."""
    if not handler:
        return {}
    
    try:
        import json
        result = handler.conn.execute("""
            SELECT table_name, column_name, distinct_values
            FROM _column_profiles
            WHERE LOWER(table_name) LIKE ? || '%'
              AND distinct_values IS NOT NULL
        """, [project[:8].lower()]).fetchall()
        
        values = {}
        for row in result:
            table_name, col_name, vals_json = row
            if vals_json:
                try:
                    vals = json.loads(vals_json) if isinstance(vals_json, str) else vals_json
                    if isinstance(vals, list):
                        values[(table_name, col_name)] = {str(v).lower() for v in vals if v}
                except Exception:
                    pass
        return values
    except Exception:
        return {}


def build_column_index(project: str, semantic_types: Dict, 
                       column_values: Dict, handler=None) -> Dict:
    """Legacy function - context graph handles this now."""
    return {}
