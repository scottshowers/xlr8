"""
XLR8 Context Graph Builder
==========================

Clean integration layer between RelationshipDetector and DuckDB storage.

Replaces the complex compute_context_graph() in structured_data_handler.py
with a simple, schema-driven approach.

Author: XLR8 Team
Version: 2.0.0
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def build_context_graph(conn, project: str, system: str = None) -> Dict[str, Any]:
    """
    Build the context graph for a project using schema-driven relationship detection.
    
    This replaces the complex compute_context_graph() with a cleaner approach:
    1. Use RelationshipDetector to find hubs and relationships
    2. Store results in _column_mappings
    3. Sync to entity registry (optional)
    
    Args:
        conn: DuckDB connection
        project: Project/customer ID (UUID or name)
        system: Optional system name (e.g., "ukg_pro"). Auto-detects if not provided.
        
    Returns:
        Dict with stats: {hubs, spokes, semantic_types, ...}
    """
    logger.warning(f"[CONTEXT-GRAPH-V2] Building context graph for {project} (SCHEMA-DRIVEN)")
    
    try:
        # Step 1: Detect relationships using schema-driven detector
        from backend.utils.intelligence.relationship_detector_v2 import detect_relationships
        
        results = detect_relationships(conn, project, system)
        
        hubs = results.get('hubs', [])
        relationships = results.get('relationships', [])
        stats = results.get('stats', {})
        
        logger.warning(f"[CONTEXT-GRAPH-V2] Detection complete: {len(hubs)} hubs, {len(relationships)} relationships")
        
        # Step 2: Clear old spoke mappings (clean slate)
        conn.execute("""
            UPDATE _column_mappings 
            SET hub_table = NULL, hub_column = NULL, hub_cardinality = NULL,
                spoke_cardinality = NULL, coverage_pct = NULL, is_subset = NULL,
                is_hub = FALSE
            WHERE project = ? AND is_hub = FALSE
        """, [project])
        logger.info(f"[CONTEXT-GRAPH-V2] Cleared old spoke mappings")
        
        # Step 3: Store hubs
        hub_count = 0
        for hub in hubs:
            _upsert_column_mapping(
                conn=conn,
                project=project,
                file_name=hub.get('table', ''),  # Use table as file placeholder
                table_name=hub['table'],
                column_name=hub['column'],
                semantic_type=f"{hub['hub_type']}_code",
                confidence=0.95,
                is_hub=True,
                hub_cardinality=hub.get('cardinality', 0),
                is_discovered=True  # Schema-driven detection
            )
            hub_count += 1
        
        # Step 4: Store relationships (spokes)
        spoke_count = 0
        for rel in relationships:
            _upsert_column_mapping(
                conn=conn,
                project=project,
                file_name=rel['spoke_table'],  # Use table as file placeholder
                table_name=rel['spoke_table'],
                column_name=rel['spoke_column'],
                semantic_type=f"{rel['hub_type']}_code",
                confidence=0.90 if rel['match_method'] == 'schema' else 0.85,
                is_hub=False,
                hub_table=rel['hub_table'],
                hub_column=rel['hub_column'],
                hub_cardinality=0,  # Will be populated from hub
                spoke_cardinality=0,  # Skip query
                coverage_pct=rel['coverage_pct'],
                is_subset=rel['is_valid'],
                is_discovered=True
            )
            spoke_count += 1
        
        conn.execute("CHECKPOINT")
        
        # Step 5: Store hubs and relationships in dedicated tables for faster queries
        _store_context_graph_tables(conn, project, hubs, relationships)
        
        # Step 6: Sync to entity registry (optional, non-fatal)
        _sync_entity_registry(project, hubs, relationships)
        
        result = {
            'hubs': hub_count,
            'spokes': spoke_count,
            'semantic_types': len(set(h['hub_type'] for h in hubs)),
            'discovered_types': hub_count,  # All are discovered in v2
            'total_relationships': len(relationships),
            'system': stats.get('system', 'auto')
        }
        
        logger.warning(f"[CONTEXT-GRAPH-V2] Complete: {hub_count} hubs, {spoke_count} spokes")
        return result
        
    except Exception as e:
        logger.error(f"[CONTEXT-GRAPH-V2] Failed: {e}")
        import traceback
        traceback.print_exc()
        return {'hubs': 0, 'spokes': 0, 'error': str(e)}


def _upsert_column_mapping(
    conn,
    project: str,
    file_name: str,
    table_name: str,
    column_name: str,
    semantic_type: str,
    confidence: float = 0.85,
    is_hub: bool = False,
    hub_table: str = None,
    hub_column: str = None,
    hub_cardinality: int = None,
    spoke_cardinality: int = None,
    coverage_pct: float = None,
    is_subset: bool = None,
    is_discovered: bool = False
):
    """Upsert a column mapping with hub/spoke info."""
    try:
        # Check if exists
        existing = conn.execute("""
            SELECT id FROM _column_mappings 
            WHERE project = ? AND table_name = ? AND original_column = ?
        """, [project, table_name, column_name]).fetchone()
        
        if existing:
            # Update
            conn.execute("""
                UPDATE _column_mappings SET
                    semantic_type = ?,
                    confidence = ?,
                    is_hub = ?,
                    hub_table = ?,
                    hub_column = ?,
                    hub_cardinality = ?,
                    spoke_cardinality = ?,
                    coverage_pct = ?,
                    is_subset = ?,
                    is_discovered = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE project = ? AND table_name = ? AND original_column = ?
            """, [
                semantic_type, confidence, is_hub,
                hub_table, hub_column, hub_cardinality,
                spoke_cardinality, coverage_pct, is_subset, is_discovered,
                project, table_name, column_name
            ])
        else:
            # Insert
            conn.execute("""
                INSERT INTO _column_mappings 
                (project, file_name, table_name, original_column, semantic_type, confidence,
                 is_hub, hub_table, hub_column, hub_cardinality, spoke_cardinality, 
                 coverage_pct, is_subset, is_discovered)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                project, file_name or '', table_name, column_name, semantic_type, confidence,
                is_hub, hub_table, hub_column, hub_cardinality, spoke_cardinality,
                coverage_pct, is_subset, is_discovered
            ])
    except Exception as e:
        logger.debug(f"[CONTEXT-GRAPH-V2] Mapping upsert error: {e}")


def _store_context_graph_tables(conn, project: str, hubs: list, relationships: list):
    """
    Store hubs and relationships in dedicated tables for faster querying.
    Creates/updates _context_graph_hubs and _context_graph_relationships.
    """
    try:
        # Clear existing data for this project (tables may have old schema)
        try:
            conn.execute("DROP TABLE IF EXISTS _context_graph_hubs")
            conn.execute("DROP TABLE IF EXISTS _context_graph_relationships")
        except:
            pass
        
        # Ensure tables exist (no explicit id - DuckDB handles rowid internally)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS _context_graph_hubs (
                project VARCHAR,
                table_name VARCHAR,
                key_column VARCHAR,
                hub_type VARCHAR,
                entity_type VARCHAR,
                domain VARCHAR,
                cardinality INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS _context_graph_relationships (
                project VARCHAR,
                spoke_table VARCHAR,
                spoke_column VARCHAR,
                hub_table VARCHAR,
                hub_column VARCHAR,
                hub_type VARCHAR,
                coverage_pct FLOAT,
                match_method VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Clear existing data for this project
        conn.execute("DELETE FROM _context_graph_hubs WHERE project = ?", [project])
        conn.execute("DELETE FROM _context_graph_relationships WHERE project = ?", [project])
        
        # Insert hubs
        for hub in hubs:
            conn.execute("""
                INSERT INTO _context_graph_hubs 
                (project, table_name, key_column, hub_type, entity_type, domain, cardinality)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [
                project,
                hub['table'],
                hub['column'],
                hub['hub_type'],
                hub.get('entity_type', hub['hub_type']),
                hub.get('domain', 'Configuration'),
                hub.get('cardinality', 0)
            ])
        
        # Insert relationships
        for rel in relationships:
            conn.execute("""
                INSERT INTO _context_graph_relationships 
                (project, spoke_table, spoke_column, hub_table, hub_column, hub_type, 
                 coverage_pct, match_method)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                project,
                rel['spoke_table'],
                rel['spoke_column'],
                rel['hub_table'],
                rel['hub_column'],
                rel['hub_type'],
                rel['coverage_pct'],
                rel['match_method']
            ])
        
        conn.execute("CHECKPOINT")
        logger.info(f"[CONTEXT-GRAPH-V2] Stored {len(hubs)} hubs, {len(relationships)} relationships to tables")
        
    except Exception as e:
        logger.warning(f"[CONTEXT-GRAPH-V2] Failed to store to tables: {e}")


def _sync_entity_registry(project: str, hubs: list, relationships: list):
    """Sync to entity registry (Supabase) - non-fatal if it fails."""
    try:
        from backend.utils.entity_registry import get_entity_registry
        registry = get_entity_registry()
        
        if registry and registry.supabase:
            # Convert to format expected by registry
            hub_data = [
                {
                    'table_name': h['table'],
                    'key_column': h['column'],
                    'semantic_type': f"{h['hub_type']}_code",
                    'cardinality': h.get('cardinality', 0),
                    'file_name': h['table'],
                    'is_discovered': True
                }
                for h in hubs
            ]
            
            rel_data = [
                {
                    'hub': {
                        'table_name': r['hub_table'],
                        'key_column': r['hub_column'],
                        'semantic_type': f"{r['hub_type']}_code"
                    },
                    'spoke_table': r['spoke_table'],
                    'spoke_column': r['spoke_column'],
                    'file_name': r['spoke_table'],
                    'coverage_pct': r['coverage_pct']
                }
                for r in relationships
            ]
            
            hub_registered = registry.register_duckdb_hubs_batch(hub_data, project)
            spoke_registered = registry.register_duckdb_spokes_batch(rel_data, project)
            logger.info(f"[ENTITY_REGISTRY] Batch registered {hub_registered} hubs, {spoke_registered} spokes")
        else:
            logger.debug("[ENTITY_REGISTRY] Supabase not available")
            
    except ImportError:
        logger.debug("[ENTITY_REGISTRY] Module not available")
    except Exception as e:
        logger.warning(f"[ENTITY_REGISTRY] Sync failed (non-fatal): {e}")
