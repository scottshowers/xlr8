"""
Data Model Router - Endpoints for table relationship analysis.

Deploy to: backend/routers/data_model.py

Then add to main.py:
    from routers import data_model
    app.include_router(data_model.router, prefix="/api")
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["data-model"])


def _get_read_handler():
    """Get a read-only DuckDB handler for API endpoints.
    
    Creates a NEW connection each time - safe for concurrent access.
    ALWAYS close when done: handler.close()
    """
    try:
        try:
            from utils.structured_data_handler import get_read_handler
        except ImportError:
            from backend.utils.structured_data_handler import get_read_handler
        return get_read_handler()
    except Exception:
        return None


def _get_write_handler():
    """Get the write handler for operations that modify data."""
    try:
        try:
            from utils.structured_data_handler import get_structured_handler
        except ImportError:
            from backend.utils.structured_data_handler import get_structured_handler
        return get_structured_handler()
    except Exception:
        return None


class RelationshipConfirmation(BaseModel):
    """Request to confirm or reject a relationship."""
    source_table: str
    source_column: str
    target_table: str
    target_column: str
    confirmed: bool


class RelationshipCreate(BaseModel):
    """Request to manually create a relationship."""
    source_table: str
    source_column: str
    target_table: str
    target_column: str
    relationship_type: str = "key"  # key, semantic, manual


@router.post("/data-model/analyze/{customer_id}")
async def analyze_data_model(customer_id: str):
    """
    Auto-detect relationships between tables in a project.
    
    INTELLIGENT APPROACH:
    1. Load global mappings (cross-customer knowledge)
    2. Load project-specific confirmed relationships
    3. Run analysis with global knowledge
    4. Only flag as "needs review" what's truly unknown
    """
    try:
        # Get tables from DuckDB via structured data handler
        tables = await get_project_tables(customer_id)
        
        if not tables:
            return {
                "project": customer_id,
                "relationships": [],
                "semantic_types": [],
                "unmatched_columns": [],
                "stats": {
                    "tables_analyzed": 0,
                    "columns_analyzed": 0,
                    "relationships_found": 0,
                    "needs_review": 0
                },
                "message": "No tables found for project. Upload data files first."
            }
        
        # Load global mappings from Supabase (cross-customer learning)
        global_mappings = {}
        project_confirmed = []
        
        try:
            try:
                from utils.database.supabase_client import get_supabase
            except ImportError:
                from utils.database.supabase_client import get_supabase
            supabase = get_supabase()
            
            # Get global mappings
            global_result = supabase.table('global_column_mappings').select('*').execute()
            if global_result.data:
                for row in global_result.data:
                    key = (row['column_pattern_1'], row['column_pattern_2'])
                    global_mappings[key] = row['confidence']
                    # Also add reverse
                    global_mappings[(row['column_pattern_2'], row['column_pattern_1'])] = row['confidence']
                logger.info(f"Loaded {len(global_result.data)} global mappings")
            
            # Get project-specific confirmed relationships
            project_result = supabase.table('project_relationships').select('*').eq('customer_id', customer_id).execute()
            if project_result.data:
                project_confirmed = project_result.data
                logger.info(f"Loaded {len(project_confirmed)} project-specific relationships")
                
        except Exception as db_e:
            logger.warning(f"Could not load from database: {db_e}")
        
        # Get local LLM client (optional)
        llm_client = get_llm_client()
        
        # Run analysis with global knowledge
        try:
            from utils.relationship_detector import analyze_project_relationships
        except ImportError:
            from backend.utils.relationship_detector import analyze_project_relationships
        
        result = await analyze_project_relationships(customer_id, tables, llm_client)
        
        # Apply global mappings - auto-confirm known relationships
        if global_mappings:
            for rel in result.get('relationships', []):
                col1 = rel['source_column'].lower().replace(' ', '_')
                col2 = rel['target_column'].lower().replace(' ', '_')
                
                # Check if this pair is in global mappings
                if (col1, col2) in global_mappings or (col2, col1) in global_mappings:
                    rel['needs_review'] = False
                    rel['confidence'] = max(rel['confidence'], 0.95)
                    rel['method'] = 'global'
        
        # Apply project-specific confirmed relationships
        if project_confirmed:
            confirmed_pairs = set()
            rejected_pairs = set()
            
            for pc in project_confirmed:
                pair = (pc['source_column'], pc['target_column'])
                if pc['status'] == 'confirmed':
                    confirmed_pairs.add(pair)
                    confirmed_pairs.add((pair[1], pair[0]))  # Reverse
                elif pc['status'] == 'rejected':
                    rejected_pairs.add(pair)
                    rejected_pairs.add((pair[1], pair[0]))
            
            # Filter out rejected and auto-confirm previously confirmed
            filtered_rels = []
            for rel in result.get('relationships', []):
                pair = (rel['source_column'], rel['target_column'])
                
                if pair in rejected_pairs:
                    continue  # Skip rejected
                
                if pair in confirmed_pairs:
                    rel['needs_review'] = False
                    rel['confirmed'] = True
                
                filtered_rels.append(rel)
            
            result['relationships'] = filtered_rels
        
        # Recalculate stats
        result['stats']['high_confidence'] = sum(1 for r in result['relationships'] if not r.get('needs_review'))
        result['stats']['needs_review'] = sum(1 for r in result['relationships'] if r.get('needs_review'))
        result['stats']['global_mappings_applied'] = len(global_mappings)
        
        # AUTO-SAVE all relationships to database
        try:
            try:
                from utils.database.supabase_client import get_supabase
            except ImportError:
                from utils.database.supabase_client import get_supabase
            supabase = get_supabase()
            
            saved_count = 0
            for rel in result['relationships']:
                # Determine status
                if rel.get('confirmed'):
                    status = 'confirmed'
                elif rel.get('needs_review'):
                    status = 'needs_review'
                else:
                    status = 'auto_confirmed'  # High confidence, no review needed
                
                # Handle both field name conventions (from_table vs source_table)
                source_table = rel.get('source_table') or rel.get('from_table', '')
                source_column = rel.get('source_column') or rel.get('from_column', '')
                target_table = rel.get('target_table') or rel.get('to_table', '')
                target_column = rel.get('target_column') or rel.get('to_column', '')
                
                if not source_table or not target_table:
                    continue
                
                # Upsert to avoid duplicates
                supabase.table('project_relationships').upsert({
                    'customer_id': customer_id,
                    'source_table': source_table,
                    'source_column': source_column,
                    'target_table': target_table,
                    'target_column': target_column,
                    'confidence': rel.get('confidence', 0.9),
                    'method': rel.get('method', 'auto'),
                    'semantic_type': rel.get('semantic_type'),
                    'status': status
                }, on_conflict='customer_id,source_table,source_column,target_table,target_column').execute()
                saved_count += 1
            
            logger.info(f"Auto-saved {saved_count} relationships to database for {customer_id}")
            result['stats']['saved_to_db'] = saved_count
            
        except Exception as save_e:
            logger.warning(f"Could not auto-save relationships: {save_e}")
            result['stats']['saved_to_db'] = 0
        
        logger.info(f"Analyzed {result['stats']['tables_analyzed']} tables for {customer_id}, "
                   f"found {result['stats']['relationships_found']} relationships "
                   f"({result['stats']['needs_review']} need review)")
        
        return result
        
    except Exception as e:
        logger.error(f"Data model analysis failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data-model/relationships/{customer_id}")
async def get_relationships(customer_id: str):
    """
    Get stored relationships for a project.
    
    Returns previously analyzed/confirmed relationships from Supabase.
    """
    try:
        relationships = []
        semantic_types = []
        
        # Load from Supabase
        try:
            try:
                from utils.database.supabase_client import get_supabase
            except ImportError:
                from utils.database.supabase_client import get_supabase
            
            supabase = get_supabase()
            
            # Get all relationships for this project
            result = supabase.table('project_relationships') \
                .select('*') \
                .eq('customer_id', customer_id) \
                .execute()
            
            if result.data:
                for row in result.data:
                    # Read boolean fields directly (saved by upload_enrichment)
                    # Fall back to status string field for backward compatibility
                    needs_review = row.get('needs_review')
                    confirmed = row.get('confirmed')
                    
                    # If boolean fields are None, check status string
                    if needs_review is None:
                        needs_review = row.get('status') == 'needs_review'
                    if confirmed is None:
                        confirmed = row.get('status') == 'confirmed'
                    
                    relationships.append({
                        'source_table': row.get('source_table', ''),
                        'source_column': row.get('source_column', ''),
                        'target_table': row.get('target_table', ''),
                        'target_column': row.get('target_column', ''),
                        'confidence': row.get('confidence', 0.9),
                        'semantic_type': row.get('semantic_type', 'unknown'),
                        'method': row.get('method', 'saved'),
                        'needs_review': bool(needs_review),
                        'confirmed': bool(confirmed),
                        'id': row.get('id'),
                    })
                
                logger.info(f"Loaded {len(relationships)} relationships for {customer_id}")
            
        except Exception as db_e:
            logger.warning(f"Could not load relationships from database: {db_e}")
        
        # Calculate stats
        high_conf = sum(1 for r in relationships if r.get('confirmed') or not r.get('needs_review'))
        needs_review = sum(1 for r in relationships if r.get('needs_review') and not r.get('confirmed'))
        
        # Get table/column stats from DuckDB directly
        tables_count = 0
        columns_count = 0
        try:
            tables = await get_project_tables(customer_id)
            tables_count = len(tables)
            columns_count = sum(len(t.get('columns', [])) for t in tables)
            logger.info(f"Stats for {customer_id}: {tables_count} tables, {columns_count} columns")
        except Exception as stats_e:
            logger.warning(f"Could not get table stats: {stats_e}")
        
        return {
            "project": customer_id,
            "relationships": relationships,
            "semantic_types": semantic_types,
            "stats": {
                "tables_analyzed": tables_count,
                "columns_analyzed": columns_count,
                "relationships_found": len(relationships),
                "high_confidence": high_conf,
                "needs_review": needs_review,
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get relationships: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data-model/context-graph/{customer_id}")
async def get_context_graph(customer_id: str):
    """
    Get the context graph showing hub/spoke relationships.
    
    THE CONTEXT GRAPH is the intelligence layer:
    - HUB: Table with max cardinality for a semantic type (source of truth)
    - SPOKE: Table that references the hub
    
    Example: company_code
    - HUB: component_company (13 unique values)
    - SPOKE: employee (6 values, 46% coverage)
    - SPOKE: payroll (6 values, 46% coverage)
    """
    try:
        try:
            from utils.structured_data_handler import get_structured_handler
        except ImportError:
            from backend.utils.structured_data_handler import get_structured_handler
        
        handler = get_structured_handler()
        
        # Get the context graph
        graph = handler.get_context_graph(customer_id)
        
        # Also get summary stats
        hubs = graph.get('hubs', [])
        relationships = graph.get('relationships', [])
        
        # Group spokes by hub for easier viewing
        by_semantic_type = {}
        for hub in hubs:
            st = hub['semantic_type']
            by_semantic_type[st] = {
                'hub': hub,
                'spokes': [r for r in relationships if r['semantic_type'] == st]
            }
        
        return {
            "project": customer_id,
            "summary": {
                "hub_count": len(hubs),
                "spoke_count": len(relationships),
                "semantic_types": list(by_semantic_type.keys())
            },
            "hubs": hubs,
            "relationships": relationships,
            "by_semantic_type": by_semantic_type
        }
        
    except Exception as e:
        logger.error(f"Failed to get context graph: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/data-model/context-graph/{customer_id}/compute")
async def compute_context_graph(customer_id: str):
    """
    Force recomputation of the context graph for a project.
    
    Use this when:
    - Upload was interrupted before graph computation
    - Data changed outside normal upload flow
    - Need to refresh hub/spoke detection
    """
    try:
        try:
            from utils.structured_data_handler import get_structured_handler
        except ImportError:
            from backend.utils.structured_data_handler import get_structured_handler
        
        handler = get_structured_handler()
        
        # Run context graph computation
        result = handler.compute_context_graph(customer_id)
        
        return {
            "success": True,
            "project": customer_id,
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Failed to compute context graph: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/data-model/detect-fk/{customer_id}")
async def detect_foreign_keys_endpoint(customer_id: str, apply: bool = False):
    """
    Detect FK relationships using ACTUAL DATA, not fuzzy name matching.
    
    This is the NEW, CORRECT approach:
    1. Find columns with same name in reality + config tables
    2. Verify with actual data: are reality values a subset of config values?
    3. Return real metrics (coverage_pct, is_subset, cardinalities)
    
    Args:
        customer_id: Customer/project identifier
        apply: If True, update _column_mappings with verified FKs
        
    Returns:
        Detailed FK detection report with all relationships found
    """
    try:
        try:
            from utils.structured_data_handler import get_structured_handler
            from backend.utils.fk_detector import detect_foreign_keys, update_column_mappings, generate_fk_report
        except ImportError:
            from backend.utils.structured_data_handler import get_structured_handler
            from backend.utils.fk_detector import detect_foreign_keys, update_column_mappings, generate_fk_report
        
        handler = get_structured_handler()
        
        # Run FK detection
        fk_results = detect_foreign_keys(handler.conn, customer_id)
        
        # Generate human-readable report
        report = generate_fk_report(fk_results)
        
        # Optionally apply to column mappings
        update_stats = None
        if apply:
            update_stats = update_column_mappings(handler.conn, customer_id, fk_results)
        
        return {
            "success": True,
            "customer_id": customer_id,
            "applied": apply,
            "stats": fk_results.get('stats', {}),
            "fk_relationships": fk_results.get('fk_relationships', []),
            "pk_columns": fk_results.get('pk_columns', []),
            "update_stats": update_stats,
            "report": report,
            "errors": fk_results.get('errors', [])
        }
        
    except Exception as e:
        logger.error(f"Failed to detect FKs: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/data-model/relationships/{customer_id}/confirm")
async def confirm_relationship(customer_id: str, confirmation: RelationshipConfirmation):
    """
    Confirm or reject a suggested relationship.
    
    When confirmed:
    1. Saves to project_relationships table
    2. Adds to global_column_mappings (cross-customer learning!)
    
    When rejected:
    Records to avoid re-suggesting for this project.
    """
    try:
        logger.info(f"Relationship {'confirmed' if confirmation.confirmed else 'rejected'}: "
                   f"{confirmation.source_table}.{confirmation.source_column} -> "
                   f"{confirmation.target_table}.{confirmation.target_column}")
        
        # Save to Supabase for persistence and learning
        try:
            try:
                from utils.database.supabase_client import get_supabase
            except ImportError:
                from utils.database.supabase_client import get_supabase
            supabase = get_supabase()
            
            if confirmation.confirmed:
                # Save to project_relationships
                supabase.table('project_relationships').upsert({
                    'customer_id': customer_id,
                    'source_table': confirmation.source_table,
                    'source_column': confirmation.source_column,
                    'target_table': confirmation.target_table,
                    'target_column': confirmation.target_column,
                    'status': 'confirmed',
                    'confirmed': True,
                    'needs_review': False,
                    'method': 'manual'
                }).execute()
                
                # Add to GLOBAL mappings (future customers get auto-match!)
                supabase.rpc('add_global_mapping', {
                    'p_col1': confirmation.source_column,
                    'p_col2': confirmation.target_column
                }).execute()
                
                logger.info(f"✅ Saved to global mappings: {confirmation.source_column} <-> {confirmation.target_column}")
            else:
                # Save rejection to avoid re-suggesting
                supabase.table('project_relationships').upsert({
                    'customer_id': customer_id,
                    'source_table': confirmation.source_table,
                    'source_column': confirmation.source_column,
                    'target_table': confirmation.target_table,
                    'target_column': confirmation.target_column,
                    'status': 'rejected',
                    'method': 'manual'
                }).execute()
                
        except Exception as db_e:
            logger.warning(f"Could not save to database (will work locally): {db_e}")
        
        return {
            "status": "updated",
            "confirmed": confirmation.confirmed,
            "global_learning": confirmation.confirmed,  # Indicates saved to global
            "relationship": {
                "source_table": confirmation.source_table,
                "source_column": confirmation.source_column,
                "target_table": confirmation.target_table,
                "target_column": confirmation.target_column
            }
        }
    except Exception as e:
        logger.error(f"Failed to confirm relationship: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/data-model/relationships/{rel_id}")
async def update_relationship(rel_id: int, updates: dict):
    """
    Update a relationship's column mappings.
    
    Used when user wants to change from_column or to_column.
    """
    try:
        from utils.database.supabase_client import get_supabase
        supabase = get_supabase()
        
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")
        
        # Build update payload
        update_data = {}
        if "from_column" in updates:
            update_data["source_column"] = updates["from_column"]
        if "to_column" in updates:
            update_data["target_column"] = updates["to_column"]
        
        if not update_data:
            return {"status": "no_changes"}
        
        # Update the relationship
        result = supabase.table('project_relationships') \
            .update(update_data) \
            .eq('id', rel_id) \
            .execute()
        
        if result.data:
            logger.info(f"Relationship {rel_id} updated: {update_data}")
            return {"status": "updated", "id": rel_id, "updates": update_data}
        else:
            raise HTTPException(status_code=404, detail="Relationship not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update relationship: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/data-model/relationships/{customer_id}/create")
async def create_relationship(customer_id: str, relationship: RelationshipCreate):
    """
    Manually create a relationship between columns.
    """
    try:
        logger.info(f"Manual relationship created: "
                   f"{relationship.source_table}.{relationship.source_column} -> "
                   f"{relationship.target_table}.{relationship.target_column}")
        
        return {
            "status": "created",
            "relationship": {
                "source_table": relationship.source_table,
                "source_column": relationship.source_column,
                "target_table": relationship.target_table,
                "target_column": relationship.target_column,
                "type": relationship.relationship_type,
                "confirmed": True,
                "method": "manual",
                "confidence": 1.0
            }
        }
    except Exception as e:
        logger.error(f"Failed to create relationship: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/data-model/relationships/{customer_id}")
async def delete_relationship(
    customer_id: str,
    source_table: str,
    source_column: str,
    target_table: str,
    target_column: str
):
    """
    Delete a relationship.
    """
    try:
        from utils.database.supabase_client import get_supabase
        supabase = get_supabase()
        
        if supabase:
            # Delete from Supabase
            result = supabase.table('project_relationships') \
                .delete() \
                .eq('customer_id', customer_id) \
                .eq('source_table', source_table) \
                .eq('source_column', source_column) \
                .eq('target_table', target_table) \
                .eq('target_column', target_column) \
                .execute()
            
            deleted_count = len(result.data or [])
            logger.info(f"Relationship deleted: {source_table}.{source_column} -> "
                       f"{target_table}.{target_column} ({deleted_count} rows)")
        
        return {"status": "deleted"}
    except Exception as e:
        logger.error(f"Failed to delete relationship: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/data-model/relationships/{customer_id}/all")
async def delete_all_relationships(customer_id: str, confirm: bool = False):
    """
    Delete ALL relationships for a project.
    Requires confirm=true.
    """
    if not confirm:
        raise HTTPException(status_code=400, detail="Must set confirm=true to delete all relationships")
    
    try:
        from utils.database.supabase_client import get_supabase
        supabase = get_supabase()
        
        deleted_count = 0
        if supabase:
            result = supabase.table('project_relationships') \
                .delete() \
                .eq('customer_id', customer_id) \
                .execute()
            deleted_count = len(result.data or [])
            logger.warning(f"⚠️ Deleted ALL {deleted_count} relationships for project {customer_id}")
        
        return {"status": "deleted", "count": deleted_count, "project": customer_id}
    except Exception as e:
        logger.error(f"Failed to delete all relationships: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper functions

async def get_project_tables(customer_id: str) -> List[Dict]:
    """
    Get table schemas for a project - tries metadata first, falls back to direct DuckDB query.
    """
    import json
    
    try:
        from utils.structured_data_handler import get_structured_handler
    except ImportError:
        try:
            from backend.utils.structured_data_handler import get_structured_handler
        except ImportError:
            logger.error("Cannot import get_structured_handler")
            return []
    
    try:
        handler = get_structured_handler()
        tables = []
        
        # Query _schema_metadata for Excel files
        try:
            metadata_result = handler.conn.execute("""
                SELECT table_name, project, file_name, sheet_name, columns, row_count
                FROM _schema_metadata 
                WHERE is_current = TRUE
            """).fetchall()
            
            for row in metadata_result:
                table_name, proj, filename, sheet, columns_json, row_count = row
                
                if proj.lower() != customer_id.lower():
                    continue
                
                try:
                    columns_data = json.loads(columns_json) if columns_json else []
                    columns = [c.get('name', c) if isinstance(c, dict) else c for c in columns_data]
                except Exception:
                    columns = []
                
                tables.append({
                    'table_name': table_name,
                    'columns': columns,
                    'row_count': row_count or 0,
                    'sheet_name': sheet,
                    'filename': filename
                })
            
            logger.info(f"Found {len(tables)} tables for {customer_id}")
            
        except Exception as e:
            logger.warning(f"Metadata query failed: {e}")
        
        # Note: PDF tables are now in _schema_metadata (via store_dataframe)
        # No separate _pdf_tables query needed
        
        # ALWAYS check DuckDB for API-synced tables (they won't be in _schema_metadata)
        try:
            all_tables = handler.conn.execute("SHOW TABLES").fetchall()
            
            # Build project prefixes for matching
            project_clean = customer_id.strip()
            api_prefix = f"{project_clean.lower()}_api_"
            
            for (table_name,) in all_tables:
                # Only look for API tables here
                if not table_name.lower().startswith(api_prefix):
                    continue
                
                # Skip if already in tables list
                if any(t['table_name'] == table_name for t in tables):
                    continue
                
                # Get columns
                columns = []
                try:
                    result = handler.conn.execute(f'SELECT * FROM "{table_name}" LIMIT 0')
                    columns = [desc[0] for desc in result.description]
                except Exception:
                    try:
                        col_result = handler.conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
                        columns = [row[1] for row in col_result]
                    except Exception as e:
                        logger.debug(f"Suppressed: {e}")
                
                # Get row count
                try:
                    count_result = handler.conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()
                    row_count = count_result[0] if count_result else 0
                except Exception:
                    row_count = 0
                
                # Extract clean table name for display
                display_name = table_name.replace(api_prefix, '').replace(project_clean.lower() + '_api_', '')
                
                tables.append({
                    'table_name': table_name,
                    'columns': columns,
                    'row_count': row_count,
                    'sheet_name': 'API Sync',
                    'filename': f'UKG Pro: {display_name}',
                    'source': 'api'
                })
            
            logger.info(f"Found {len([t for t in tables if t.get('source') == 'api'])} API tables for {customer_id}")
            
        except Exception as api_e:
            logger.warning(f"API table query failed: {api_e}")
        
        # FALLBACK: If metadata returned nothing, query DuckDB directly for non-API tables
        if not tables:
            logger.warning(f"No tables from metadata - querying DuckDB directly for {customer_id}")
            try:
                all_tables = handler.conn.execute("SHOW TABLES").fetchall()
                
                # Build project prefixes for matching
                # Tables use first 8 chars of UUID (no hyphens) as prefix
                project_clean = customer_id.strip()
                project_prefixes = [
                    project_clean.lower(),
                    project_clean.lower().replace(' ', '_'),
                    project_clean.lower().replace(' ', '_').replace('-', '_'),
                    # Handle UUID-based customer IDs: extract first 8 chars without hyphens
                    project_clean.replace('-', '')[:8].lower() if '-' in project_clean else None,
                    # Also match full UUID with hyphens (for API-synced tables)
                    project_clean.lower() + '_api_' if '-' in project_clean else None,
                ]
                project_prefixes = [p for p in project_prefixes if p]
                
                for (table_name,) in all_tables:
                    # Skip system tables
                    if table_name.startswith('_'):
                        continue
                    
                    # Check if matches project
                    table_lower = table_name.lower()
                    if not any(table_lower.startswith(prefix) for prefix in project_prefixes if prefix):
                        continue
                    
                    # Get columns
                    columns = []
                    try:
                        result = handler.conn.execute(f'SELECT * FROM "{table_name}" LIMIT 0')
                        columns = [desc[0] for desc in result.description]
                    except Exception:
                        try:
                            col_result = handler.conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
                            columns = [row[1] for row in col_result]
                        except Exception as e:
                            logger.debug(f"Suppressed: {e}")
                    
                    # Get row count
                    try:
                        count_result = handler.conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()
                        row_count = count_result[0] if count_result else 0
                    except Exception:
                        row_count = 0
                    
                    tables.append({
                        'table_name': table_name,
                        'columns': columns,
                        'row_count': row_count,
                        'sheet_name': 'Direct Query',
                        'filename': 'DuckDB'
                    })
                
                logger.info(f"Direct query found {len(tables)} tables for {customer_id}")
                
            except Exception as direct_e:
                logger.error(f"Direct table query failed: {direct_e}")
        
        logger.info(f"Total {len(tables)} tables for project {customer_id}")
        return tables
        
    except Exception as e:
        logger.error(f"Failed to get tables: {e}")
        return []


def get_llm_client():
    """
    Get local LLM client for ambiguous relationship analysis.
    
    Returns None if not available (analysis continues without LLM).
    """
    try:
        # Try to get local LLM from orchestrator
        from utils.llm_orchestrator import get_local_client
        client = get_local_client()
        if client:
            return client
    except ImportError:
        logger.debug("llm_orchestrator not available")
    except Exception as e:
        logger.debug(f"Could not get local LLM: {e}")
    
    # Try Ollama directly
    try:
        import httpx
        import os
        
        ollama_host = os.getenv("OLLAMA_HOST", os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
        
        class OllamaClient:
            def __init__(self, base_url=None):
                self.base_url = base_url or ollama_host
                self.model = "mistral"  # or llama3.1
            
            def generate(self, prompt: str, max_tokens: int = 1000) -> str:
                response = httpx.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"num_predict": max_tokens}
                    },
                    timeout=60.0
                )
                if response.status_code == 200:
                    return response.json().get("response", "")
                return ""
        
        # Test connection
        client = OllamaClient()
        test_response = httpx.get(f"{ollama_host}/api/tags", timeout=2.0)
        if test_response.status_code == 200:
            logger.info("Using Ollama for relationship analysis")
            return client
            
    except Exception as e:
        logger.debug(f"Ollama not available: {e}")
    
    logger.info("No local LLM available, using rule-based analysis only")
    return None


# =============================================================================
# PROJECT LISTING & RELATIONSHIP VIEW ENDPOINTS
# =============================================================================

@router.get("/data-model/projects")
async def list_projects_with_data():
    """
    List all projects that have uploaded data with table counts.
    
    Returns projects derived from:
    - _schema_metadata (Excel files)
    - _pdf_tables (PDF files)
    - Table name prefixes
    """
    try:
        from utils.structured_data_handler import get_structured_handler
    except ImportError:
        try:
            from backend.utils.structured_data_handler import get_structured_handler
        except ImportError:
            raise HTTPException(status_code=500, detail="Cannot load structured handler")
    
    try:
        handler = get_structured_handler()
        projects = {}
        
        # Method 1: Get projects from _schema_metadata
        try:
            result = handler.conn.execute("""
                SELECT project, COUNT(*) as table_count, SUM(row_count) as total_rows
                FROM _schema_metadata 
                WHERE is_current = TRUE AND project IS NOT NULL
                GROUP BY project
            """).fetchall()
            
            for row in result:
                proj_name = row[0]
                if proj_name:
                    projects[proj_name] = {
                        'name': proj_name,
                        'table_count': row[1],
                        'row_count': row[2] or 0,
                        'source': 'metadata'
                    }
        except Exception as e:
            logger.debug(f"Metadata query failed: {e}")
        
        # Method 2: Get projects from table prefixes
        try:
            all_tables = handler.conn.execute("SHOW TABLES").fetchall()
            prefix_projects = {}
            
            for (table_name,) in all_tables:
                if table_name.startswith('_'):
                    continue  # Skip system tables
                
                if '__' in table_name:
                    prefix = table_name.split('__')[0]
                    if prefix not in prefix_projects:
                        prefix_projects[prefix] = {'tables': [], 'rows': 0}
                    prefix_projects[prefix]['tables'].append(table_name)
                    
                    try:
                        count = handler.conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]
                        prefix_projects[prefix]['rows'] += count
                    except Exception:
                        pass
            
            # Merge with projects dict
            for prefix, info in prefix_projects.items():
                if prefix not in projects:
                    projects[prefix] = {
                        'name': prefix,
                        'table_count': len(info['tables']),
                        'row_count': info['rows'],
                        'source': 'prefix'
                    }
                else:
                    # Update if prefix has more tables
                    if len(info['tables']) > projects[prefix]['table_count']:
                        projects[prefix]['table_count'] = len(info['tables'])
                        projects[prefix]['row_count'] = info['rows']
                        
        except Exception as e:
            logger.warning(f"Table prefix scan failed: {e}")
        
        # Sort by row count descending
        sorted_projects = sorted(projects.values(), key=lambda x: x['row_count'], reverse=True)
        
        return {
            "projects": sorted_projects,
            "total_projects": len(sorted_projects),
            "total_tables": sum(p['table_count'] for p in sorted_projects),
            "total_rows": sum(p['row_count'] for p in sorted_projects)
        }
        
    except Exception as e:
        logger.error(f"Failed to list projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/data-model/analyze-all")
async def analyze_all_projects():
    """
    Analyze relationships for ALL projects with data.
    
    Use with caution - this will analyze every project.
    """
    try:
        # First get all projects
        projects_response = await list_projects_with_data()
        projects = projects_response.get('projects', [])
        
        results = []
        for proj in projects:
            proj_name = proj['name']
            try:
                result = await analyze_data_model(proj_name)
                results.append({
                    'project': proj_name,
                    'relationships_found': result.get('stats', {}).get('relationships_found', 0),
                    'saved_to_db': result.get('stats', {}).get('saved_to_db', 0),
                    'status': 'success'
                })
            except Exception as e:
                results.append({
                    'project': proj_name,
                    'status': 'error',
                    'error': str(e)
                })
        
        successful = sum(1 for r in results if r['status'] == 'success')
        total_rels = sum(r.get('relationships_found', 0) for r in results)
        
        return {
            "projects_analyzed": len(results),
            "successful": successful,
            "total_relationships_found": total_rels,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Analyze-all failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data-model/relationships-summary")
async def get_all_relationships_summary():
    """
    Get a summary of all relationships across all projects.
    """
    try:
        from utils.database.supabase_client import get_supabase
    except ImportError:
        try:
            from backend.utils.database.supabase_client import get_supabase
        except ImportError:
            raise HTTPException(status_code=500, detail="Supabase not available")
    
    try:
        supabase = get_supabase()
        
        # Get all relationships grouped by project
        # Use * to handle varying column schemas
        result = supabase.table('project_relationships') \
            .select('*') \
            .execute()
        
        if not result.data:
            return {
                "total_relationships": 0,
                "projects": [],
                "by_semantic_type": {},
                "message": "No relationships stored. Run /data-model/analyze/{project} to detect relationships."
            }
        
        # Group by project
        by_project = {}
        by_semantic_type = {}
        
        for row in result.data:
            proj = row.get('customer_id', 'unknown')
            if proj not in by_project:
                by_project[proj] = {
                    'project': proj,
                    'relationship_count': 0,
                    'confirmed': 0,
                    'needs_review': 0,
                    'avg_confidence': 0,
                    'confidences': []
                }
            
            by_project[proj]['relationship_count'] += 1
            by_project[proj]['confidences'].append(row.get('confidence', 0.8))
            
            if row.get('status') == 'confirmed':
                by_project[proj]['confirmed'] += 1
            elif row.get('status') == 'needs_review':
                by_project[proj]['needs_review'] += 1
            
            sem_type = row.get('semantic_type', 'unknown')
            if sem_type:
                by_semantic_type[sem_type] = by_semantic_type.get(sem_type, 0) + 1
        
        # Calculate averages
        for proj_data in by_project.values():
            confs = proj_data.pop('confidences')
            proj_data['avg_confidence'] = round(sum(confs) / len(confs), 2) if confs else 0
        
        return {
            "total_relationships": len(result.data),
            "projects": list(by_project.values()),
            "by_semantic_type": by_semantic_type
        }
        
    except Exception as e:
        logger.error(f"Failed to get relationships summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# RELATIONSHIP TESTING / VERIFICATION
# =============================================================================

class TestRelationshipRequest(BaseModel):
    """Request to test a relationship between two tables."""
    table_a: str
    table_b: str
    project: str
    sample_limit: int = 10


@router.post("/data-model/test-relationship")
async def test_relationship(request: TestRelationshipRequest):
    """
    Test and verify a relationship between two tables.
    
    Shows:
    - Detected relationship (if any)
    - Sample data from each table
    - Sample JOIN results
    - Match statistics (matches, orphans, overlap)
    
    Use this to VERIFY relationships are correct before trusting them.
    """
    try:
        from utils.structured_data_handler import get_structured_handler
    except ImportError:
        try:
            from backend.utils.structured_data_handler import get_structured_handler
        except ImportError:
            raise HTTPException(status_code=500, detail="Cannot load structured handler")
    
    table_a = request.table_a
    table_b = request.table_b
    project = request.project
    limit = request.sample_limit
    
    result = {
        "table_a": table_a,
        "table_b": table_b,
        "project": project,
        "relationship": None,
        "join_column_a": None,
        "join_column_b": None,
        "table_a_sample": [],
        "table_b_sample": [],
        "join_sample": [],
        "statistics": {},
        "verification": {
            "status": "unknown",
            "message": ""
        }
    }
    
    try:
        handler = get_structured_handler()
        
        # Step 1: Look up detected relationship from Supabase
        relationship = None
        try:
            from utils.database.supabase_client import get_supabase
        except ImportError:
            from backend.utils.database.supabase_client import get_supabase
        
        try:
            supabase = get_supabase()
            
            # Check both directions (A→B and B→A)
            rel_result = supabase.table('project_relationships') \
                .select('*') \
                .eq('customer_id', project) \
                .or_(
                    f"and(source_table.ilike.%{table_a}%,target_table.ilike.%{table_b}%),"
                    f"and(source_table.ilike.%{table_b}%,target_table.ilike.%{table_a}%)"
                ) \
                .execute()
            
            if rel_result.data:
                relationship = rel_result.data[0]
                result["relationship"] = relationship
                
                # Determine join columns based on direction
                if table_a.lower() in relationship['source_table'].lower():
                    result["join_column_a"] = relationship['source_column']
                    result["join_column_b"] = relationship['target_column']
                else:
                    result["join_column_a"] = relationship['target_column']
                    result["join_column_b"] = relationship['source_column']
                    
        except Exception as db_e:
            logger.warning(f"Could not query relationships: {db_e}")
        
        # Step 2: Get columns for both tables
        try:
            cols_a = [row[0] for row in handler.conn.execute(f'DESCRIBE "{table_a}"').fetchall()]
            cols_b = [row[0] for row in handler.conn.execute(f'DESCRIBE "{table_b}"').fetchall()]
            result["table_a_columns"] = cols_a
            result["table_b_columns"] = cols_b
        except Exception as e:
            result["verification"]["status"] = "error"
            result["verification"]["message"] = f"Could not describe tables: {e}"
            return result
        
        # Step 3: Sample data from each table
        try:
            # Sample from table A
            sample_cols_a = cols_a[:8]  # First 8 columns
            col_str_a = ', '.join(f'"{c}"' for c in sample_cols_a)
            rows_a = handler.conn.execute(f'SELECT {col_str_a} FROM "{table_a}" LIMIT {limit}').fetchall()
            result["table_a_sample"] = [dict(zip(sample_cols_a, row)) for row in rows_a]
            
            # Sample from table B
            sample_cols_b = cols_b[:8]
            col_str_b = ', '.join(f'"{c}"' for c in sample_cols_b)
            rows_b = handler.conn.execute(f'SELECT {col_str_b} FROM "{table_b}" LIMIT {limit}').fetchall()
            result["table_b_sample"] = [dict(zip(sample_cols_b, row)) for row in rows_b]
            
        except Exception as e:
            logger.warning(f"Sample query failed: {e}")
        
        # Step 4: If we have join columns, test the JOIN
        join_col_a = result["join_column_a"]
        join_col_b = result["join_column_b"]
        
        if not join_col_a or not join_col_b:
            # Try to auto-detect common columns
            common = set(c.lower() for c in cols_a) & set(c.lower() for c in cols_b)
            if common:
                # Prefer code/id columns
                for c in common:
                    if 'code' in c or 'id' in c:
                        join_col_a = next((x for x in cols_a if x.lower() == c), None)
                        join_col_b = next((x for x in cols_b if x.lower() == c), None)
                        break
                if not join_col_a:
                    c = list(common)[0]
                    join_col_a = next((x for x in cols_a if x.lower() == c), None)
                    join_col_b = next((x for x in cols_b if x.lower() == c), None)
                
                result["join_column_a"] = join_col_a
                result["join_column_b"] = join_col_b
                result["relationship_source"] = "auto-detected (common column)"
        
        if join_col_a and join_col_b:
            # Step 5: Run JOIN and get sample
            try:
                # Select key columns from both tables
                select_a = [f'a."{c}"' for c in cols_a[:4]]
                select_b = [f'b."{c}" AS "b_{c}"' for c in cols_b[:4] if c.lower() != join_col_b.lower()]
                select_str = ', '.join(select_a + select_b)
                
                join_sql = f'''
                    SELECT {select_str}
                    FROM "{table_a}" a
                    LEFT JOIN "{table_b}" b ON a."{join_col_a}" = b."{join_col_b}"
                    LIMIT {limit}
                '''
                
                join_rows = handler.conn.execute(join_sql).fetchall()
                join_cols = [c.split('.')[-1].strip('"') for c in (select_a + select_b)]
                result["join_sample"] = [dict(zip(join_cols, row)) for row in join_rows]
                result["join_sql"] = join_sql.strip()
                
            except Exception as e:
                result["join_error"] = str(e)
            
            # Step 6: Calculate match statistics
            try:
                # Count total in A
                count_a = handler.conn.execute(f'SELECT COUNT(*) FROM "{table_a}"').fetchone()[0]
                
                # Count total in B
                count_b = handler.conn.execute(f'SELECT COUNT(*) FROM "{table_b}"').fetchone()[0]
                
                # Count distinct values in join columns
                distinct_a = handler.conn.execute(f'SELECT COUNT(DISTINCT "{join_col_a}") FROM "{table_a}"').fetchone()[0]
                distinct_b = handler.conn.execute(f'SELECT COUNT(DISTINCT "{join_col_b}") FROM "{table_b}"').fetchone()[0]
                
                # Count matches (A values that exist in B)
                match_sql = f'''
                    SELECT COUNT(DISTINCT a."{join_col_a}")
                    FROM "{table_a}" a
                    INNER JOIN "{table_b}" b ON a."{join_col_a}" = b."{join_col_b}"
                '''
                matches = handler.conn.execute(match_sql).fetchone()[0]
                
                # Count orphans in A (values not in B)
                orphan_a_sql = f'''
                    SELECT COUNT(DISTINCT a."{join_col_a}")
                    FROM "{table_a}" a
                    LEFT JOIN "{table_b}" b ON a."{join_col_a}" = b."{join_col_b}"
                    WHERE b."{join_col_b}" IS NULL AND a."{join_col_a}" IS NOT NULL
                '''
                orphans_a = handler.conn.execute(orphan_a_sql).fetchone()[0]
                
                # Count orphans in B (values not in A)
                orphan_b_sql = f'''
                    SELECT COUNT(DISTINCT b."{join_col_b}")
                    FROM "{table_b}" b
                    LEFT JOIN "{table_a}" a ON b."{join_col_b}" = a."{join_col_a}"
                    WHERE a."{join_col_a}" IS NULL AND b."{join_col_b}" IS NOT NULL
                '''
                orphans_b = handler.conn.execute(orphan_b_sql).fetchone()[0]
                
                # Sample orphan values from A
                orphan_sample_sql = f'''
                    SELECT DISTINCT a."{join_col_a}"
                    FROM "{table_a}" a
                    LEFT JOIN "{table_b}" b ON a."{join_col_a}" = b."{join_col_b}"
                    WHERE b."{join_col_b}" IS NULL AND a."{join_col_a}" IS NOT NULL
                    LIMIT 5
                '''
                orphan_samples_a = [row[0] for row in handler.conn.execute(orphan_sample_sql).fetchall()]
                
                match_rate = round(matches / distinct_a * 100, 1) if distinct_a > 0 else 0
                
                result["statistics"] = {
                    "table_a_rows": count_a,
                    "table_b_rows": count_b,
                    "table_a_distinct_keys": distinct_a,
                    "table_b_distinct_keys": distinct_b,
                    "matching_keys": matches,
                    "match_rate_percent": match_rate,
                    "orphans_in_a": orphans_a,
                    "orphans_in_b": orphans_b,
                    "orphan_samples_from_a": orphan_samples_a
                }
                
                # Verification verdict
                if match_rate >= 80:
                    result["verification"]["status"] = "good"
                    result["verification"]["message"] = f"Strong relationship: {match_rate}% of {table_a} keys found in {table_b}"
                elif match_rate >= 50:
                    result["verification"]["status"] = "partial"
                    result["verification"]["message"] = f"Partial relationship: {match_rate}% match. {orphans_a} orphan keys in {table_a}"
                elif match_rate > 0:
                    result["verification"]["status"] = "weak"
                    result["verification"]["message"] = f"Weak relationship: Only {match_rate}% match. Review if these tables should be joined."
                else:
                    result["verification"]["status"] = "none"
                    result["verification"]["message"] = f"No matching keys found. These tables may not be related via {join_col_a}↔{join_col_b}"
                    
            except Exception as e:
                result["statistics_error"] = str(e)
        
        else:
            result["verification"]["status"] = "no_join_column"
            result["verification"]["message"] = "No relationship detected and no common columns found. Tables may not be related."
        
        return result
        
    except Exception as e:
        logger.error(f"Test relationship failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data-model/table-preview/{project}/{table_name}")
async def preview_table(project: str, table_name: str, limit: int = 20):
    """
    Preview a table's data and structure.
    
    Quick way to see what's in a table before testing relationships.
    """
    try:
        from utils.structured_data_handler import get_structured_handler
    except ImportError:
        try:
            from backend.utils.structured_data_handler import get_structured_handler
        except ImportError:
            raise HTTPException(status_code=500, detail="Cannot load structured handler")
    
    try:
        handler = get_structured_handler()
        
        # Get columns
        cols = [row[0] for row in handler.conn.execute(f'DESCRIBE "{table_name}"').fetchall()]
        
        # Get row count
        count = handler.conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]
        
        # Get sample data
        col_str = ', '.join(f'"{c}"' for c in cols[:12])  # First 12 columns
        rows = handler.conn.execute(f'SELECT {col_str} FROM "{table_name}" LIMIT {limit}').fetchall()
        sample = [dict(zip(cols[:12], row)) for row in rows]
        
        # Get value distribution for key-like columns
        distributions = {}
        for col in cols:
            if any(x in col.lower() for x in ['code', 'id', 'type', 'status']):
                try:
                    dist = handler.conn.execute(f'''
                        SELECT "{col}", COUNT(*) as cnt 
                        FROM "{table_name}" 
                        WHERE "{col}" IS NOT NULL
                        GROUP BY "{col}" 
                        ORDER BY cnt DESC 
                        LIMIT 10
                    ''').fetchall()
                    distributions[col] = [{"value": row[0], "count": row[1]} for row in dist]
                except Exception:
                    pass
        
        return {
            "table": table_name,
            "project": project,
            "columns": cols,
            "row_count": count,
            "sample_data": sample,
            "key_distributions": distributions
        }
        
    except Exception as e:
        logger.error(f"Table preview failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/data-model/split-column")
async def split_column(request: Request):
    """
    Split a column into two new columns based on a pattern.
    
    Supports:
    - first_word: Split after first word (space)
    - newline: Split at newline character
    - delimiter: Split at specific character
    - position: Split at fixed character position
    
    Creates new columns, preserves original (can be deleted separately).
    """
    try:
        from utils.structured_data_handler import get_structured_handler
    except ImportError:
        try:
            from backend.utils.structured_data_handler import get_structured_handler
        except ImportError:
            raise HTTPException(status_code=500, detail="Cannot load structured handler")
    
    try:
        body = await request.json()
        project = body.get('project')
        table_name = body.get('table_name')
        column_name = body.get('column_name')
        split_type = body.get('split_type')  # first_word, newline, delimiter, position
        split_value = body.get('split_value')  # delimiter char or position int
        new_column_names = body.get('new_column_names', ['left', 'right'])
        
        if not all([table_name, column_name, split_type]):
            raise HTTPException(status_code=400, detail="Missing required fields: table_name, column_name, split_type")
        
        if len(new_column_names) != 2:
            raise HTTPException(status_code=400, detail="new_column_names must have exactly 2 values")
        
        left_col = new_column_names[0]
        right_col = new_column_names[1]
        
        handler = get_structured_handler()
        
        # Verify table and column exist
        try:
            cols = [row[0] for row in handler.conn.execute(f'DESCRIBE "{table_name}"').fetchall()]
            if column_name not in cols:
                raise HTTPException(status_code=404, detail=f"Column '{column_name}' not found in table")
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Table not found: {e}")
        
        # Build the split expression based on type
        if split_type == 'first_word':
            # Split at first space
            left_expr = f"TRIM(SPLIT_PART(CAST(\"{column_name}\" AS VARCHAR), ' ', 1))"
            right_expr = f"TRIM(SUBSTR(CAST(\"{column_name}\" AS VARCHAR), LENGTH(SPLIT_PART(CAST(\"{column_name}\" AS VARCHAR), ' ', 1)) + 2))"
        
        elif split_type == 'newline':
            # Split at newline
            left_expr = f"TRIM(SPLIT_PART(CAST(\"{column_name}\" AS VARCHAR), CHR(10), 1))"
            right_expr = f"TRIM(SUBSTR(CAST(\"{column_name}\" AS VARCHAR), POSITION(CHR(10) IN CAST(\"{column_name}\" AS VARCHAR)) + 1))"
        
        elif split_type == 'delimiter':
            delim = split_value or ' '
            # Escape single quotes in delimiter
            delim_escaped = delim.replace("'", "''")
            left_expr = f"TRIM(SPLIT_PART(CAST(\"{column_name}\" AS VARCHAR), '{delim_escaped}', 1))"
            right_expr = f"TRIM(SUBSTR(CAST(\"{column_name}\" AS VARCHAR), POSITION('{delim_escaped}' IN CAST(\"{column_name}\" AS VARCHAR)) + 1))"
        
        elif split_type == 'position':
            pos = int(split_value) if split_value else 0
            if pos <= 0:
                raise HTTPException(status_code=400, detail="Position must be > 0")
            left_expr = f"TRIM(SUBSTR(CAST(\"{column_name}\" AS VARCHAR), 1, {pos}))"
            right_expr = f"TRIM(SUBSTR(CAST(\"{column_name}\" AS VARCHAR), {pos + 1}))"
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown split_type: {split_type}")
        
        # Add the new columns
        try:
            # Add left column
            handler.conn.execute(f'ALTER TABLE "{table_name}" ADD COLUMN "{left_col}" VARCHAR')
            handler.conn.execute(f'UPDATE "{table_name}" SET "{left_col}" = {left_expr}')
            
            # Add right column
            handler.conn.execute(f'ALTER TABLE "{table_name}" ADD COLUMN "{right_col}" VARCHAR')
            handler.conn.execute(f'UPDATE "{table_name}" SET "{right_col}" = {right_expr}')
            
            # Get row count
            row_count = handler.conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]
            
            logger.info(f"[DATA-MODEL] Split column '{column_name}' into '{left_col}' and '{right_col}' in {table_name} ({row_count} rows)")
            
            return {
                "success": True,
                "table_name": table_name,
                "original_column": column_name,
                "new_columns": [left_col, right_col],
                "split_type": split_type,
                "rows_affected": row_count
            }
            
        except Exception as sql_err:
            logger.error(f"[DATA-MODEL] SQL error splitting column: {sql_err}")
            raise HTTPException(status_code=500, detail=f"Failed to split column: {sql_err}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[DATA-MODEL] Split column failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
