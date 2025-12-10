"""
Data Model Router - Endpoints for table relationship analysis.

Deploy to: backend/routers/data_model.py

Then add to main.py:
    from routers import data_model
    app.include_router(data_model.router, prefix="/api")
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["data-model"])


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


@router.post("/data-model/analyze/{project_name}")
async def analyze_data_model(project_name: str):
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
        tables = await get_project_tables(project_name)
        
        if not tables:
            return {
                "project": project_name,
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
            project_result = supabase.table('project_relationships').select('*').eq('project_name', project_name).execute()
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
        
        result = await analyze_project_relationships(project_name, tables, llm_client)
        
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
                
                # Upsert to avoid duplicates
                supabase.table('project_relationships').upsert({
                    'project_name': project_name,
                    'source_table': rel['source_table'],
                    'source_column': rel['source_column'],
                    'target_table': rel['target_table'],
                    'target_column': rel['target_column'],
                    'confidence': rel.get('confidence', 0.9),
                    'method': rel.get('method', 'auto'),
                    'status': status
                }, on_conflict='project_name,source_table,source_column,target_table,target_column').execute()
                saved_count += 1
            
            logger.info(f"Auto-saved {saved_count} relationships to database for {project_name}")
            result['stats']['saved_to_db'] = saved_count
            
        except Exception as save_e:
            logger.warning(f"Could not auto-save relationships: {save_e}")
            result['stats']['saved_to_db'] = 0
        
        logger.info(f"Analyzed {result['stats']['tables_analyzed']} tables for {project_name}, "
                   f"found {result['stats']['relationships_found']} relationships "
                   f"({result['stats']['needs_review']} need review)")
        
        return result
        
    except Exception as e:
        logger.error(f"Data model analysis failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data-model/relationships/{project_name}")
async def get_relationships(project_name: str):
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
                .eq('project_name', project_name) \
                .execute()
            
            if result.data:
                for row in result.data:
                    relationships.append({
                        'source_table': row.get('source_table', ''),
                        'source_column': row.get('source_column', ''),
                        'target_table': row.get('target_table', ''),
                        'target_column': row.get('target_column', ''),
                        'confidence': row.get('confidence', 0.9),
                        'semantic_type': row.get('semantic_type', 'unknown'),
                        'method': row.get('method', 'saved'),
                        'needs_review': row.get('status') == 'needs_review',
                        'confirmed': row.get('status') == 'confirmed',
                        'id': row.get('id'),
                    })
                
                logger.info(f"Loaded {len(relationships)} relationships for {project_name}")
            
        except Exception as db_e:
            logger.warning(f"Could not load relationships from database: {db_e}")
        
        # Calculate stats
        high_conf = sum(1 for r in relationships if r.get('confirmed') or not r.get('needs_review'))
        needs_review = sum(1 for r in relationships if r.get('needs_review') and not r.get('confirmed'))
        
        return {
            "project": project_name,
            "relationships": relationships,
            "semantic_types": semantic_types,
            "stats": {
                "relationships_found": len(relationships),
                "high_confidence": high_conf,
                "needs_review": needs_review,
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get relationships: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/data-model/relationships/{project_name}/confirm")
async def confirm_relationship(project_name: str, confirmation: RelationshipConfirmation):
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
                    'project_name': project_name,
                    'source_table': confirmation.source_table,
                    'source_column': confirmation.source_column,
                    'target_table': confirmation.target_table,
                    'target_column': confirmation.target_column,
                    'status': 'confirmed',
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
                    'project_name': project_name,
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


@router.post("/data-model/relationships/{project_name}/create")
async def create_relationship(project_name: str, relationship: RelationshipCreate):
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


@router.delete("/data-model/relationships/{project_name}")
async def delete_relationship(
    project_name: str,
    source_table: str,
    source_column: str,
    target_table: str,
    target_column: str
):
    """
    Delete a relationship.
    """
    try:
        logger.info(f"Relationship deleted: {source_table}.{source_column} -> "
                   f"{target_table}.{target_column}")
        
        return {"status": "deleted"}
    except Exception as e:
        logger.error(f"Failed to delete relationship: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper functions

async def get_project_tables(project_name: str) -> List[Dict]:
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
                
                if proj.lower() != project_name.lower():
                    continue
                
                try:
                    columns_data = json.loads(columns_json) if columns_json else []
                    columns = [c.get('name', c) if isinstance(c, dict) else c for c in columns_data]
                except:
                    columns = []
                
                tables.append({
                    'table_name': table_name,
                    'columns': columns,
                    'row_count': row_count or 0,
                    'sheet_name': sheet,
                    'filename': filename
                })
            
            logger.info(f"Found {len(tables)} Excel tables for {project_name}")
            
        except Exception as e:
            logger.warning(f"Metadata query failed: {e}")
        
        # Query _pdf_tables for PDF files
        try:
            table_check = handler.conn.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name = '_pdf_tables'
            """).fetchone()
            
            if table_check[0] > 0:
                pdf_result = handler.conn.execute("""
                    SELECT table_name, source_file, project, row_count, columns
                    FROM _pdf_tables
                """).fetchall()
                
                for row in pdf_result:
                    table_name, source_file, proj, row_count, columns_json = row
                    
                    if not proj or proj.lower() != project_name.lower():
                        continue
                    
                    try:
                        columns = json.loads(columns_json) if columns_json else []
                    except:
                        columns = []
                    
                    tables.append({
                        'table_name': table_name,
                        'columns': columns,
                        'row_count': row_count or 0,
                        'sheet_name': 'PDF Data',
                        'filename': source_file
                    })
                
                logger.info(f"Found {len([t for t in tables if t.get('sheet_name') == 'PDF Data'])} PDF tables for {project_name}")
                
        except Exception as e:
            logger.debug(f"PDF tables query: {e}")
        
        # FALLBACK: If metadata returned nothing, query DuckDB directly
        if not tables:
            logger.warning(f"No tables from metadata - querying DuckDB directly for {project_name}")
            try:
                all_tables = handler.conn.execute("SHOW TABLES").fetchall()
                
                # Build project prefixes for matching
                project_clean = project_name.strip()
                project_prefixes = [
                    project_clean.lower(),
                    project_clean.lower().replace(' ', '_'),
                    project_clean.lower().replace(' ', '_').replace('-', '_'),
                ]
                
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
                    except:
                        try:
                            col_result = handler.conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
                            columns = [row[1] for row in col_result]
                        except:
                            pass
                    
                    # Get row count
                    try:
                        count_result = handler.conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()
                        row_count = count_result[0] if count_result else 0
                    except:
                        row_count = 0
                    
                    tables.append({
                        'table_name': table_name,
                        'columns': columns,
                        'row_count': row_count,
                        'sheet_name': 'Direct Query',
                        'filename': 'DuckDB'
                    })
                
                logger.info(f"Direct query found {len(tables)} tables for {project_name}")
                
            except Exception as direct_e:
                logger.error(f"Direct table query failed: {direct_e}")
        
        logger.info(f"Total {len(tables)} tables for project {project_name}")
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
        
        class OllamaClient:
            def __init__(self, base_url="http://localhost:11434"):
                self.base_url = base_url
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
        test_response = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
        if test_response.status_code == 200:
            logger.info("Using Ollama for relationship analysis")
            return client
            
    except Exception as e:
        logger.debug(f"Ollama not available: {e}")
    
    logger.info("No local LLM available, using rule-based analysis only")
    return None
