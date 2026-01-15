"""
Cost Equivalent Calculator
==========================

Estimates consultant hours for equivalent manual analysis.
Used to demonstrate platform value by showing what the analysis
would cost if done manually.

Created: January 14, 2026 - Phase 4A.3
"""

from typing import Optional
import logging

logger = logging.getLogger(__name__)


def calculate_cost_equivalent(
    record_count: int,
    table_count: int,
    column_count: int = 0,
    document_count: int = 0,
    hourly_rate: float = 250.0
) -> dict:
    """
    Estimate consultant hours for equivalent manual analysis.
    
    Assumptions (conservative):
    - 500 records/hour for data review
    - 2 hours per table for schema analysis
    - 0.5 hours per 10 columns for field mapping
    - 1 hour per 1000 records for pattern detection
    - 0.5 hours per document for document review
    
    Args:
        record_count: Total number of data records
        table_count: Number of tables/files analyzed
        column_count: Total columns across all tables
        document_count: Number of documents processed
        hourly_rate: Consultant hourly rate (default $250)
    
    Returns:
        dict with hours, cost, and breakdown
    """
    # Data review: scanning through records
    data_review_hours = record_count / 500 if record_count > 0 else 0
    
    # Schema analysis: understanding table structure
    schema_hours = table_count * 2
    
    # Field mapping: analyzing columns
    field_mapping_hours = (column_count / 10) * 0.5 if column_count > 0 else 0
    
    # Pattern detection: finding anomalies, gaps, issues
    pattern_hours = record_count / 1000 if record_count > 0 else 0
    
    # Document review: reading and extracting from docs
    document_hours = document_count * 0.5
    
    # Total
    total_hours = (
        data_review_hours + 
        schema_hours + 
        field_mapping_hours + 
        pattern_hours + 
        document_hours
    )
    
    # Minimum 1 hour if any work was done
    if total_hours > 0 and total_hours < 1:
        total_hours = 1
    
    total_cost = total_hours * hourly_rate
    
    return {
        "hours": round(total_hours, 1),
        "cost": round(total_cost, 0),
        "hourly_rate": hourly_rate,
        "breakdown": {
            "data_review": round(data_review_hours, 1),
            "schema_analysis": round(schema_hours, 1),
            "field_mapping": round(field_mapping_hours, 1),
            "pattern_detection": round(pattern_hours, 1),
            "document_review": round(document_hours, 1),
        },
        "inputs": {
            "record_count": record_count,
            "table_count": table_count,
            "column_count": column_count,
            "document_count": document_count,
        }
    }


def get_project_cost_equivalent(project_name: str, hourly_rate: float = 250.0) -> dict:
    """
    Calculate cost equivalent for an entire project based on its data.
    
    Args:
        project_name: Project name to analyze
        hourly_rate: Consultant hourly rate
    
    Returns:
        dict with hours, cost, breakdown, and project stats
    """
    from utils.duckdb_manager import duckdb_manager
    
    try:
        handler = duckdb_manager.get_handler(project_name)
        if not handler:
            return {"hours": 0, "cost": 0, "error": "Project not found"}
        
        # Get table stats
        tables = handler.list_tables()
        table_count = len(tables)
        
        total_records = 0
        total_columns = 0
        
        for table_name in tables:
            # Skip metadata tables
            if table_name.startswith('_'):
                continue
            
            try:
                # Get row count
                result = handler.conn.execute(
                    f'SELECT COUNT(*) as cnt FROM "{table_name}"'
                ).fetchone()
                total_records += result[0] if result else 0
                
                # Get column count
                cols = handler.conn.execute(
                    f"DESCRIBE \"{table_name}\""
                ).fetchall()
                total_columns += len(cols)
            except Exception as e:
                logger.warning(f"Error getting stats for {table_name}: {e}")
                continue
        
        # Get document count from ChromaDB
        document_count = 0
        try:
            from utils.chroma_manager import chroma_manager
            for truth_type in ['intent', 'reference', 'regulatory']:
                collection = chroma_manager.get_collection(project_name, truth_type)
                if collection:
                    document_count += collection.count()
        except Exception as e:
            logger.warning(f"Error getting document count: {e}")
        
        # Calculate
        result = calculate_cost_equivalent(
            record_count=total_records,
            table_count=table_count,
            column_count=total_columns,
            document_count=document_count,
            hourly_rate=hourly_rate
        )
        
        result["project"] = project_name
        
        return result
        
    except Exception as e:
        logger.error(f"Error calculating cost equivalent: {e}")
        return {"hours": 0, "cost": 0, "error": str(e)}
