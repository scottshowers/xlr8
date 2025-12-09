"""
API Connections Router - UKG Pro/WFM/Ready Integration
======================================================

Endpoints:
- POST /api/connections - Create/save connection
- GET /api/connections/{project} - List connections for project
- POST /api/connections/{id}/test - Test a connection
- DELETE /api/connections/{id} - Delete a connection
- GET /api/connections/{id}/reports - List available reports
- GET /api/connections/{id}/reports/{path}/parameters - Get report parameters
- POST /api/connections/{id}/reports/execute - Execute a report

Deploy to: backend/routers/api_connections.py

Add to main.py:
    from routers import api_connections
    app.include_router(api_connections.router, prefix="/api", tags=["connections"])
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(tags=["connections"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class ConnectionCreate(BaseModel):
    """Create a new API connection."""
    project_name: str
    provider: str  # ukg_pro, ukg_wfm, ukg_ready
    connection_name: str = "Default"
    base_url: str
    customer_api_key: str
    web_services_key: Optional[str] = None
    username: str
    password: str


class ConnectionUpdate(BaseModel):
    """Update an existing connection."""
    connection_name: Optional[str] = None
    base_url: Optional[str] = None
    customer_api_key: Optional[str] = None
    web_services_key: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None


class ConnectionResponse(BaseModel):
    """Connection info (without sensitive data)."""
    id: str
    project_name: str
    provider: str
    connection_name: str
    base_url: str
    status: str
    last_connected_at: Optional[str] = None
    last_error: Optional[str] = None


class ReportExecuteRequest(BaseModel):
    """Request to execute a report."""
    report_path: str
    parameters: Dict[str, Any] = {}
    target_table: Optional[str] = None  # Table name to save results


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_supabase():
    """Get Supabase client."""
    try:
        from utils.supabase_client import get_supabase_client
    except ImportError:
        from backend.utils.supabase_client import get_supabase_client
    return get_supabase_client()


def get_raas_client(connection_data: Dict):
    """Create RaaS client from connection data."""
    try:
        from services.ukg_pro_raas import UKGProRaaSClient, UKGCredentials
    except ImportError:
        from backend.services.ukg_pro_raas import UKGProRaaSClient, UKGCredentials
    
    credentials = UKGCredentials(
        base_url=connection_data['base_url'],
        customer_api_key=connection_data['customer_api_key'],
        web_services_key=connection_data.get('web_services_key', ''),
        username=connection_data['username'],
        password=connection_data['password']
    )
    return UKGProRaaSClient(credentials)


async def get_connection_by_id(connection_id: str) -> Dict:
    """Get connection from database by ID."""
    supabase = get_supabase()
    result = supabase.table('api_connections').select('*').eq('id', connection_id).single().execute()
    if not result.data:
        raise HTTPException(404, "Connection not found")
    return result.data


# =============================================================================
# CONNECTION MANAGEMENT
# =============================================================================

@router.post("/connections")
async def create_connection(conn: ConnectionCreate):
    """
    Create a new API connection.
    
    Saves credentials securely and tests the connection.
    """
    logger.info(f"[CONNECTIONS] Creating {conn.provider} connection for {conn.project_name}")
    
    try:
        supabase = get_supabase()
        
        # Check for existing connection
        existing = supabase.table('api_connections') \
            .select('id') \
            .eq('project_name', conn.project_name) \
            .eq('provider', conn.provider) \
            .eq('connection_name', conn.connection_name) \
            .execute()
        
        if existing.data:
            raise HTTPException(400, f"Connection '{conn.connection_name}' already exists for this project")
        
        # Save connection
        result = supabase.table('api_connections').insert({
            'project_name': conn.project_name,
            'provider': conn.provider,
            'connection_name': conn.connection_name,
            'base_url': conn.base_url,
            'customer_api_key': conn.customer_api_key,
            'web_services_key': conn.web_services_key,
            'username': conn.username,
            'password': conn.password,
            'status': 'pending'
        }).execute()
        
        if not result.data:
            raise HTTPException(500, "Failed to save connection")
        
        connection_id = result.data[0]['id']
        
        # Test the connection
        test_result = await test_connection(connection_id)
        
        return {
            "id": connection_id,
            "status": "created",
            "test_result": test_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CONNECTIONS] Create failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/connections/{project_name}")
async def list_connections(project_name: str):
    """List all API connections for a project."""
    try:
        supabase = get_supabase()
        
        result = supabase.table('api_connections') \
            .select('id, project_name, provider, connection_name, base_url, status, last_connected_at, last_error') \
            .eq('project_name', project_name) \
            .execute()
        
        return {
            "project": project_name,
            "connections": result.data or []
        }
        
    except Exception as e:
        logger.error(f"[CONNECTIONS] List failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/connections/detail/{connection_id}")
async def get_connection(connection_id: str):
    """Get connection details (without password)."""
    try:
        supabase = get_supabase()
        
        result = supabase.table('api_connections') \
            .select('id, project_name, provider, connection_name, base_url, username, status, last_connected_at, last_error, created_at') \
            .eq('id', connection_id) \
            .single() \
            .execute()
        
        if not result.data:
            raise HTTPException(404, "Connection not found")
        
        return result.data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CONNECTIONS] Get failed: {e}")
        raise HTTPException(500, str(e))


@router.put("/connections/{connection_id}")
async def update_connection(connection_id: str, update: ConnectionUpdate):
    """Update connection settings."""
    try:
        supabase = get_supabase()
        
        # Build update dict (only include non-None fields)
        update_data = {}
        if update.connection_name is not None:
            update_data['connection_name'] = update.connection_name
        if update.base_url is not None:
            update_data['base_url'] = update.base_url
        if update.customer_api_key is not None:
            update_data['customer_api_key'] = update.customer_api_key
        if update.web_services_key is not None:
            update_data['web_services_key'] = update.web_services_key
        if update.username is not None:
            update_data['username'] = update.username
        if update.password is not None:
            update_data['password'] = update.password
        
        if not update_data:
            raise HTTPException(400, "No fields to update")
        
        result = supabase.table('api_connections') \
            .update(update_data) \
            .eq('id', connection_id) \
            .execute()
        
        return {"status": "updated", "id": connection_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CONNECTIONS] Update failed: {e}")
        raise HTTPException(500, str(e))


@router.delete("/connections/{connection_id}")
async def delete_connection(connection_id: str):
    """Delete a connection."""
    try:
        supabase = get_supabase()
        
        supabase.table('api_connections').delete().eq('id', connection_id).execute()
        
        return {"status": "deleted", "id": connection_id}
        
    except Exception as e:
        logger.error(f"[CONNECTIONS] Delete failed: {e}")
        raise HTTPException(500, str(e))


# =============================================================================
# CONNECTION TESTING
# =============================================================================

@router.post("/connections/{connection_id}/test")
async def test_connection(connection_id: str):
    """
    Test an API connection.
    
    Updates the connection status based on result.
    """
    logger.info(f"[CONNECTIONS] Testing connection {connection_id}")
    
    try:
        conn_data = await get_connection_by_id(connection_id)
        supabase = get_supabase()
        
        if conn_data['provider'] == 'ukg_pro':
            # Test UKG Pro RaaS connection
            client = get_raas_client(conn_data)
            try:
                success, message = await client.test_connection()
            finally:
                await client.close()
            
            # Update connection status
            supabase.table('api_connections').update({
                'status': 'active' if success else 'error',
                'last_connected_at': datetime.now().isoformat() if success else None,
                'last_error': None if success else message
            }).eq('id', connection_id).execute()
            
            return {
                "connection_id": connection_id,
                "success": success,
                "message": message
            }
        
        else:
            # TODO: Add WFM and Ready testing
            return {
                "connection_id": connection_id,
                "success": False,
                "message": f"Provider {conn_data['provider']} not yet supported"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CONNECTIONS] Test failed: {e}")
        
        # Update status to error
        try:
            supabase = get_supabase()
            supabase.table('api_connections').update({
                'status': 'error',
                'last_error': str(e)
            }).eq('id', connection_id).execute()
        except:
            pass
        
        raise HTTPException(500, str(e))


# =============================================================================
# REPORT DISCOVERY
# =============================================================================

@router.get("/connections/{connection_id}/reports")
async def list_reports(connection_id: str, path: str = "/content"):
    """
    List available reports for a connection.
    
    Args:
        connection_id: The connection to use
        path: Report folder path (default: /content for root)
    """
    logger.info(f"[CONNECTIONS] Listing reports for {connection_id}")
    
    try:
        conn_data = await get_connection_by_id(connection_id)
        
        if conn_data['provider'] != 'ukg_pro':
            raise HTTPException(400, "Report listing only supported for UKG Pro")
        
        client = get_raas_client(conn_data)
        try:
            reports = await client.get_report_list(path)
        finally:
            await client.close()
        
        return {
            "connection_id": connection_id,
            "path": path,
            "reports": [
                {
                    "path": r.path,
                    "name": r.name,
                    "description": r.description
                }
                for r in reports
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CONNECTIONS] List reports failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/connections/{connection_id}/reports/parameters")
async def get_report_parameters(connection_id: str, report_path: str):
    """
    Get parameters required by a report.
    
    Args:
        connection_id: The connection to use
        report_path: Full path to the report
    """
    logger.info(f"[CONNECTIONS] Getting parameters for {report_path}")
    
    try:
        conn_data = await get_connection_by_id(connection_id)
        
        if conn_data['provider'] != 'ukg_pro':
            raise HTTPException(400, "Parameters only supported for UKG Pro")
        
        client = get_raas_client(conn_data)
        try:
            params = await client.get_report_parameters(report_path)
        finally:
            await client.close()
        
        return {
            "connection_id": connection_id,
            "report_path": report_path,
            "parameters": [
                {
                    "name": p.name,
                    "display_name": p.display_name,
                    "data_type": p.data_type,
                    "required": p.required,
                    "default_value": p.default_value
                }
                for p in params
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CONNECTIONS] Get parameters failed: {e}")
        raise HTTPException(500, str(e))


# =============================================================================
# REPORT EXECUTION
# =============================================================================

@router.post("/connections/{connection_id}/execute")
async def execute_report(connection_id: str, request: ReportExecuteRequest):
    """
    Execute a report and optionally save to DuckDB.
    
    Returns the data and optionally stores it as a new table.
    """
    logger.info(f"[CONNECTIONS] Executing report {request.report_path}")
    
    try:
        conn_data = await get_connection_by_id(connection_id)
        supabase = get_supabase()
        
        if conn_data['provider'] != 'ukg_pro':
            raise HTTPException(400, "Report execution only supported for UKG Pro")
        
        # Log execution start
        exec_record = supabase.table('raas_executions').insert({
            'connection_id': connection_id,
            'status': 'running',
            'parameters_used': request.parameters,
            'target_table': request.target_table
        }).execute()
        
        execution_id = exec_record.data[0]['id'] if exec_record.data else None
        
        # Execute the report
        client = get_raas_client(conn_data)
        try:
            result = await client.execute_report(
                request.report_path,
                request.parameters,
                output_format="csv"
            )
        finally:
            await client.close()
        
        # Update execution record
        if execution_id:
            supabase.table('raas_executions').update({
                'completed_at': datetime.now().isoformat(),
                'status': 'completed' if result.success else 'failed',
                'row_count': result.row_count,
                'error_message': result.error
            }).eq('id', execution_id).execute()
        
        if not result.success:
            raise HTTPException(500, f"Report execution failed: {result.error}")
        
        # Save to DuckDB if target table specified
        table_name = None
        if request.target_table and result.data:
            table_name = await save_to_duckdb(
                conn_data['project_name'],
                request.target_table,
                result.columns,
                result.data
            )
        
        return {
            "success": True,
            "connection_id": connection_id,
            "report_path": request.report_path,
            "row_count": result.row_count,
            "columns": result.columns,
            "execution_time_ms": result.execution_time_ms,
            "saved_to_table": table_name,
            "preview": result.data[:10] if result.data else []  # First 10 rows for preview
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CONNECTIONS] Execute failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(500, str(e))


async def save_to_duckdb(project_name: str, table_name: str, columns: List[str], data: List[Dict]) -> str:
    """
    Save report data to DuckDB.
    
    Creates a new table with the report data, prefixed with 'pro_'.
    """
    try:
        from utils.structured_data_handler import get_structured_handler
    except ImportError:
        from backend.utils.structured_data_handler import get_structured_handler
    
    handler = get_structured_handler()
    
    # Ensure table name is prefixed and sanitized
    if not table_name.startswith('pro_'):
        table_name = f"pro_{table_name}"
    
    table_name = table_name.lower().replace(' ', '_').replace('-', '_')
    full_table_name = f"{project_name}_{table_name}"
    
    # Build CREATE TABLE statement
    col_defs = []
    for col in columns:
        safe_col = col.replace(' ', '_').replace('-', '_').replace('.', '_')
        col_defs.append(f'"{safe_col}" TEXT')
    
    create_sql = f'CREATE OR REPLACE TABLE "{full_table_name}" ({", ".join(col_defs)})'
    
    # Execute create
    handler.conn.execute(create_sql)
    
    # Insert data
    if data:
        placeholders = ', '.join(['?' for _ in columns])
        insert_sql = f'INSERT INTO "{full_table_name}" VALUES ({placeholders})'
        
        for row in data:
            values = [row.get(col, '') for col in columns]
            handler.conn.execute(insert_sql, values)
    
    logger.info(f"[CONNECTIONS] Saved {len(data)} rows to {full_table_name}")
    
    return full_table_name


# =============================================================================
# SAVED REPORTS
# =============================================================================

@router.post("/connections/{connection_id}/reports/save")
async def save_report_config(
    connection_id: str,
    report_path: str,
    report_name: str,
    target_table: str = None,
    parameters: Dict[str, Any] = None
):
    """Save a report configuration for easy re-execution."""
    try:
        supabase = get_supabase()
        
        result = supabase.table('raas_reports').upsert({
            'connection_id': connection_id,
            'report_path': report_path,
            'report_name': report_name,
            'target_table_name': target_table,
            'parameters': parameters or {}
        }).execute()
        
        return {
            "status": "saved",
            "report_id": result.data[0]['id'] if result.data else None
        }
        
    except Exception as e:
        logger.error(f"[CONNECTIONS] Save report config failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/connections/{connection_id}/reports/saved")
async def list_saved_reports(connection_id: str):
    """List saved report configurations for a connection."""
    try:
        supabase = get_supabase()
        
        result = supabase.table('raas_reports') \
            .select('*') \
            .eq('connection_id', connection_id) \
            .execute()
        
        return {
            "connection_id": connection_id,
            "saved_reports": result.data or []
        }
        
    except Exception as e:
        logger.error(f"[CONNECTIONS] List saved reports failed: {e}")
        raise HTTPException(500, str(e))
