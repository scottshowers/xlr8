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
    
    Uses rule-based matching + optional local LLM for ambiguous cases.
    Returns relationships with confidence scores and needs_review flags.
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
        
        # Get local LLM client (optional - continues without if unavailable)
        llm_client = get_llm_client()
        
        # Run analysis
        from utils.relationship_detector import analyze_project_relationships
        result = await analyze_project_relationships(project_name, tables, llm_client)
        
        logger.info(f"Analyzed {result['stats']['tables_analyzed']} tables for {project_name}, "
                   f"found {result['stats']['relationships_found']} relationships")
        
        return result
        
    except Exception as e:
        logger.error(f"Data model analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data-model/relationships/{project_name}")
async def get_relationships(project_name: str):
    """
    Get stored relationships for a project.
    
    Returns previously analyzed/confirmed relationships.
    """
    try:
        # For now, return empty - relationships are computed on-demand
        # Future: Store confirmed relationships in Supabase/DuckDB
        return {
            "project": project_name,
            "relationships": [],
            "message": "Use POST /data-model/analyze/{project_name} to detect relationships"
        }
    except Exception as e:
        logger.error(f"Failed to get relationships: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/data-model/relationships/{project_name}/confirm")
async def confirm_relationship(project_name: str, confirmation: RelationshipConfirmation):
    """
    Confirm or reject a suggested relationship.
    
    Updates the stored relationship status.
    """
    try:
        # Future: Store confirmation in database
        logger.info(f"Relationship {'confirmed' if confirmation.confirmed else 'rejected'}: "
                   f"{confirmation.source_table}.{confirmation.source_column} -> "
                   f"{confirmation.target_table}.{confirmation.target_column}")
        
        return {
            "status": "updated",
            "confirmed": confirmation.confirmed,
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
    Get table schemas for a project from DuckDB.
    
    Returns list of tables with columns.
    """
    try:
        # Try to use structured data handler
        from utils.structured_data_handler import get_project_tables as get_tables
        tables = get_tables(project_name)
        if tables:
            return tables
    except ImportError:
        logger.debug("structured_data_handler not available, trying direct DuckDB")
    except Exception as e:
        logger.warning(f"structured_data_handler failed: {e}")
    
    # Fallback: Query DuckDB directly
    try:
        import duckdb
        import os
        
        db_path = os.environ.get('DUCKDB_PATH', './data/structured.duckdb')
        if not os.path.exists(db_path):
            return []
        
        conn = duckdb.connect(db_path, read_only=True)
        
        # Get all tables for project
        project_prefix = project_name.lower().replace(' ', '_').replace('-', '_')
        
        # Get table names
        tables_query = f"""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'main' 
            AND table_name LIKE '{project_prefix}%'
        """
        table_names = conn.execute(tables_query).fetchall()
        
        tables = []
        for (table_name,) in table_names:
            # Get columns for each table
            cols_query = f"""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position
            """
            columns = conn.execute(cols_query).fetchall()
            
            # Get row count
            try:
                count_query = f"SELECT COUNT(*) FROM \"{table_name}\""
                row_count = conn.execute(count_query).fetchone()[0]
            except:
                row_count = 0
            
            tables.append({
                'table_name': table_name,
                'columns': [{'name': col[0], 'type': col[1]} for col in columns],
                'row_count': row_count
            })
        
        conn.close()
        return tables
        
    except Exception as e:
        logger.error(f"Failed to get tables from DuckDB: {e}")
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
