"""
UKG Pro API Connector Router
============================

Handles connections to UKG Pro REST APIs for pulling configuration and employee data.

Endpoints:
- POST /api/ukg/test-connection - Test API credentials
- GET /api/ukg/code-tables - Get list of all code tables
- GET /api/ukg/code-tables/{table_name} - Get specific code table data
- POST /api/ukg/sync-config/{project_id} - Sync all config tables to DuckDB
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import httpx
import base64
import logging
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ukg", tags=["ukg-connector"])


class UKGCredentials(BaseModel):
    """Credentials for connecting to UKG Pro API"""
    hostname: str  # e.g., "service5.ultipro.com"
    customer_api_key: str  # 5 character key
    username: str  # Service account username
    password: str  # Service account password
    user_api_key: str  # User API key for the service account


class UKGTestResult(BaseModel):
    """Result of a connection test"""
    success: bool
    message: str
    status_code: Optional[int] = None
    data: Optional[Any] = None
    error: Optional[str] = None


class SyncResult(BaseModel):
    """Result of a sync operation"""
    success: bool
    tables_synced: int
    tables_failed: int
    total_rows: int
    details: List[Dict[str, Any]]
    errors: List[str]


def build_auth_headers(creds: UKGCredentials) -> Dict[str, str]:
    """Build the authentication headers for UKG Pro API"""
    # Basic auth: base64(username:password)
    basic_auth = base64.b64encode(f"{creds.username}:{creds.password}".encode()).decode()
    
    return {
        "Authorization": f"Basic {basic_auth}",
        "US-Customer-Api-Key": creds.customer_api_key,
        "Api-Key": creds.user_api_key,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }


@router.get("/browse", response_class=HTMLResponse)
async def browse_ukg_data(
    username: str,
    password: str,
    user_api_key: str,
    hostname: str = "service5.ultipro.com",
    customer_api_key: str = "OTA4F"
):
    """
    Nice HTML view of all available code tables.
    /api/ukg/browse?username=XXX&password=XXX&user_api_key=XXX
    """
    from fastapi.responses import HTMLResponse
    
    creds = UKGCredentials(
        hostname=hostname,
        customer_api_key=customer_api_key,
        username=username,
        password=password,
        user_api_key=user_api_key
    )
    
    url = f"https://{creds.hostname}/configuration/v1/code-tables"
    headers = build_auth_headers(creds)
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code == 200:
                tables = response.json()
                
                # Build nice HTML
                rows = ""
                for i, table in enumerate(tables, 1):
                    name = table.get('name', table) if isinstance(table, dict) else table
                    rows += f"<tr><td>{i}</td><td>{name}</td></tr>"
                
                html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>UKG Pro Code Tables</title>
                    <style>
                        body {{ font-family: -apple-system, sans-serif; max-width: 900px; margin: 40px auto; padding: 20px; }}
                        h1 {{ color: #28a745; }}
                        .count {{ background: #d4edda; padding: 10px 20px; border-radius: 8px; display: inline-block; margin-bottom: 20px; }}
                        table {{ width: 100%; border-collapse: collapse; }}
                        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
                        th {{ background: #f8f9fa; }}
                        tr:hover {{ background: #f5f5f5; }}
                    </style>
                </head>
                <body>
                    <h1>✅ UKG Pro Code Tables</h1>
                    <div class="count">Found <strong>{len(tables)}</strong> code tables available</div>
                    <table>
                        <tr><th>#</th><th>Table Name</th></tr>
                        {rows}
                    </table>
                </body>
                </html>
                """
                return HTMLResponse(content=html)
            else:
                return HTMLResponse(content=f"<h1>Error {response.status_code}</h1><pre>{response.text}</pre>")
                
    except Exception as e:
        return HTMLResponse(content=f"<h1>Error</h1><pre>{str(e)}</pre>")


@router.get("/quick-test")
async def quick_test_ukg_connection(
    username: str,
    password: str,
    user_api_key: str,
    hostname: str = "service5.ultipro.com",
    customer_api_key: str = "OTA4F"
):
    """
    Quick test - just hit this URL with query params:
    /api/ukg/quick-test?username=XXX&password=XXX&user_api_key=XXX
    """
    creds = UKGCredentials(
        hostname=hostname,
        customer_api_key=customer_api_key,
        username=username,
        password=password,
        user_api_key=user_api_key
    )
    return await test_ukg_connection(creds)


@router.post("/test-connection", response_model=UKGTestResult)
async def test_ukg_connection(creds: UKGCredentials):
    """
    Test connection to UKG Pro API.
    
    Attempts to fetch the code-tables list to verify credentials work.
    """
    logger.info(f"Testing UKG connection to {creds.hostname}")
    
    url = f"https://{creds.hostname}/configuration/v1/code-tables"
    headers = build_auth_headers(creds)
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Count how many code tables we got
                    table_count = len(data) if isinstance(data, list) else "unknown"
                    return UKGTestResult(
                        success=True,
                        message=f"Connected successfully! Found {table_count} code tables.",
                        status_code=response.status_code,
                        data=data[:10] if isinstance(data, list) else data  # Return first 10 as sample
                    )
                except Exception as e:
                    return UKGTestResult(
                        success=True,
                        message="Connected but couldn't parse JSON response",
                        status_code=response.status_code,
                        data=response.text[:500]
                    )
            elif response.status_code == 401:
                return UKGTestResult(
                    success=False,
                    message="Authentication failed - check username/password/API keys",
                    status_code=response.status_code,
                    error=response.text[:500]
                )
            elif response.status_code == 403:
                return UKGTestResult(
                    success=False,
                    message="Forbidden - service account may not have 'Company Configuration Integration' permission",
                    status_code=response.status_code,
                    error=response.text[:500]
                )
            else:
                return UKGTestResult(
                    success=False,
                    message=f"Unexpected response: {response.status_code}",
                    status_code=response.status_code,
                    error=response.text[:500]
                )
                
    except httpx.TimeoutException:
        return UKGTestResult(
            success=False,
            message="Connection timed out - check hostname",
            error="Timeout after 30 seconds"
        )
    except httpx.ConnectError as e:
        return UKGTestResult(
            success=False,
            message="Could not connect - check hostname",
            error=str(e)
        )
    except Exception as e:
        logger.error(f"UKG connection test failed: {e}")
        return UKGTestResult(
            success=False,
            message="Connection failed",
            error=str(e)
        )


@router.post("/code-tables")
async def get_code_tables(creds: UKGCredentials):
    """Get list of all available code tables"""
    url = f"https://{creds.hostname}/configuration/v1/code-tables"
    headers = build_auth_headers(creds)
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=response.text
                )
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/code-tables/{table_name}")
async def get_code_table_data(table_name: str, creds: UKGCredentials):
    """
    Get data from a specific code table.
    
    table_name examples: marital-status, employee-type, job-family, etc.
    """
    url = f"https://{creds.hostname}/configuration/v1/{table_name}"
    headers = build_auth_headers(creds)
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code == 200:
                return {"success": True, "table": table_name, "data": response.json()}
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=response.text
                )
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/employees")
async def get_employees(creds: UKGCredentials, page: int = 1, per_page: int = 100):
    """
    Get employee person details.
    
    This pulls from /personnel/v1/person-details
    """
    url = f"https://{creds.hostname}/personnel/v1/person-details"
    headers = build_auth_headers(creds)
    params = {"page": page, "per_page": per_page}
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "page": page,
                    "per_page": per_page,
                    "count": len(data) if isinstance(data, list) else "unknown",
                    "data": data
                }
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=response.text
                )
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# SYNC ALL CONFIG TABLES - BACKGROUND JOB
# =============================================================================

import uuid
from datetime import datetime

# In-memory job tracking (would use Redis in production)
_sync_jobs: Dict[str, Dict] = {}


def get_supabase():
    """Get Supabase client."""
    try:
        from utils.database.supabase_client import get_supabase as _get_supabase
        return _get_supabase()
    except ImportError:
        from backend.utils.database.supabase_client import get_supabase as _get_supabase
        return _get_supabase()


async def get_connection_creds(project_id: str) -> Optional[Dict]:
    """Get saved UKG Pro credentials for a project."""
    try:
        supabase = get_supabase()
        result = supabase.table('api_connections') \
            .select('*') \
            .eq('project_name', project_id) \
            .eq('provider', 'ukg_pro') \
            .single() \
            .execute()
        return result.data
    except Exception as e:
        logger.error(f"Failed to get connection: {e}")
        return None


async def fetch_all_pages(client: httpx.AsyncClient, url: str, headers: Dict, job_id: str = None) -> List[Dict]:
    """Fetch all pages from a paginated endpoint."""
    all_data = []
    page = 1
    per_page = 100
    
    while True:
        try:
            params = {"page": page, "per_page": per_page}
            response = await client.get(url, headers=headers, params=params, timeout=30.0)
            
            if response.status_code != 200:
                logger.warning(f"[UKG-SYNC] {url} returned {response.status_code}")
                break
            
            data = response.json()
            
            if not data:
                break
                
            if isinstance(data, list):
                all_data.extend(data)
                if len(data) < per_page:
                    break
                page += 1
            else:
                # Single object response
                all_data = [data] if data else []
                break
                
            # Safety limit
            if page > 100:
                break
                
            # Polite delay - don't hammer UKG
            await asyncio.sleep(0.5)
            
        except Exception as e:
            logger.error(f"[UKG-SYNC] Error fetching {url}: {e}")
            break
    
    return all_data


async def save_to_duckdb(project_id: str, table_name: str, data: List[Dict]) -> int:
    """Save data to DuckDB using the existing structured data handler."""
    if not data:
        return 0
        
    try:
        import pandas as pd
        from utils.structured_data_handler import get_structured_handler
        
        # Flatten nested objects if needed
        flat_data = []
        for row in data:
            flat_row = {}
            for k, v in row.items():
                if isinstance(v, dict):
                    for k2, v2 in v.items():
                        flat_row[f"{k}_{k2}"] = str(v2) if v2 is not None else None
                elif isinstance(v, list):
                    flat_row[k] = str(v)
                else:
                    flat_row[k] = v
            flat_data.append(flat_row)
        
        df = pd.DataFrame(flat_data)
        
        # Sanitize table name
        safe_table = table_name.replace('-', '_').replace(' ', '_').lower()
        full_table_name = f"{project_id}_api_{safe_table}"
        
        # Use the existing structured data handler
        handler = get_structured_handler()
        
        handler.conn.execute(f'DROP TABLE IF EXISTS "{full_table_name}"')
        handler.conn.register("temp_df", df)
        handler.conn.execute(f'CREATE TABLE "{full_table_name}" AS SELECT * FROM temp_df')
        handler.conn.unregister("temp_df")
        
        # v5.2 FIX: Persist to disk! Without this, data is lost on process restart
        handler.conn.execute("CHECKPOINT")
        
        logger.info(f"[UKG-SYNC] Saved {len(df)} rows to {full_table_name}")
        return len(df)
        
    except Exception as e:
        logger.error(f"[UKG-SYNC] DuckDB save failed for {table_name}: {e}")
        raise


async def run_sync_job(job_id: str, project_id: str, conn_data: Dict):
    """Background task to run the actual sync."""
    global _sync_jobs
    
    job = _sync_jobs[job_id]
    job['status'] = 'running'
    job['started_at'] = datetime.now().isoformat()
    
    hostname = conn_data.get('hostname', '')
    creds = UKGCredentials(
        hostname=hostname,
        customer_api_key=conn_data.get('customer_api_key', ''),
        username=conn_data.get('username', ''),
        password=conn_data.get('password', ''),
        user_api_key=conn_data.get('user_api_key', '')
    )
    headers = build_auth_headers(creds)
    
    results = []
    errors = []
    total_rows = 0
    tables_synced = 0
    tables_failed = 0
    
    try:
        async with httpx.AsyncClient() as client:
            # =====================================================
            # STEP 1: Discover all available code tables
            # =====================================================
            job['current_step'] = 'Discovering code tables...'
            logger.info(f"[UKG-SYNC] [{job_id}] Discovering available code tables...")
            
            code_tables_url = f"https://{hostname}/configuration/v1/code-tables"
            try:
                response = await client.get(code_tables_url, headers=headers, timeout=30.0)
                if response.status_code == 200:
                    available_tables = response.json()
                    logger.info(f"[UKG-SYNC] [{job_id}] Found {len(available_tables)} code tables")
                    job['total_tables'] = len(available_tables) + 17  # +10 config + +7 reality endpoints
                else:
                    available_tables = []
                    errors.append(f"Could not fetch code tables list: HTTP {response.status_code}")
            except Exception as e:
                available_tables = []
                errors.append(f"Could not fetch code tables list: {str(e)}")
            
            # =====================================================
            # STEP 2: Pull each code table
            # =====================================================
            table_index = 0
            for table_info in available_tables:
                # Handle different response formats from code-tables endpoint
                if isinstance(table_info, dict):
                    # Format: {'codeTable': 'GENDER', 'url': 'https://...'}
                    table_name = table_info.get('codeTable') or table_info.get('name') or table_info.get('tableName')
                    table_url = table_info.get('url')
                else:
                    table_name = str(table_info)
                    table_url = None
                
                if not table_name or table_name == 'None':
                    continue
                
                table_index += 1
                job['current_step'] = f'Pulling {table_name}...'
                job['tables_processed'] = table_index
                logger.info(f"[UKG-SYNC] [{job_id}] [{table_index}/{len(available_tables)}] Pulling {table_name}...")
                
                # Use the provided URL if available, otherwise construct it
                if table_url:
                    url = table_url
                else:
                    url = f"https://{hostname}/configuration/v1/code-tables/{table_name}"
                
                try:
                    data = await fetch_all_pages(client, url, headers, job_id)
                    
                    if data:
                        rows = await save_to_duckdb(project_id, table_name, data)
                        total_rows += rows
                        tables_synced += 1
                        results.append({
                            "table": table_name,
                            "rows": rows,
                            "success": True,
                            "type": "configuration"
                        })
                    else:
                        results.append({
                            "table": table_name,
                            "rows": 0,
                            "success": True,
                            "type": "configuration",
                            "note": "empty"
                        })
                        
                except Exception as e:
                    tables_failed += 1
                    error_msg = str(e)
                    errors.append(f"{table_name}: {error_msg}")
                    results.append({
                        "table": table_name,
                        "rows": 0,
                        "success": False,
                        "error": error_msg
                    })
                
                # Update job progress
                job['tables_synced'] = tables_synced
                job['total_rows'] = total_rows
                
                # Polite delay between tables
                await asyncio.sleep(1.0)
            
            # =====================================================
            # STEP 3: Pull CONFIGURATION master data
            # These are the lookup tables that transactional data references
            # e.g., jobs, org_levels, locations - NOT the simple code tables
            # =====================================================
            config_endpoints = [
                {"name": "jobs", "path": "/configuration/v1/jobs"},
                {"name": "org_levels", "path": "/configuration/v1/org-levels"},
                {"name": "locations", "path": "/configuration/v1/locations"},
                {"name": "company_details", "path": "/configuration/v1/company-details"},
                {"name": "pay_group_pay_period", "path": "/personnel/v1/pay-group-pay-period"},
                {"name": "earnings", "path": "/configuration/v1/earnings"},
                {"name": "deductions", "path": "/configuration/v1/deductions"},
                {"name": "positions", "path": "/configuration/v1/positions"},
                {"name": "shift_codes", "path": "/configuration/v1/shift-codes"},
                {"name": "tax_groups", "path": "/configuration/v1/tax-groups"},
            ]
            
            for endpoint in config_endpoints:
                table_index += 1
                job['current_step'] = f'Pulling config: {endpoint["name"]}...'
                job['tables_processed'] = table_index
                logger.info(f"[UKG-SYNC] [{job_id}] Pulling config: {endpoint['name']}...")
                
                url = f"https://{hostname}{endpoint['path']}"
                
                try:
                    data = await fetch_all_pages(client, url, headers, job_id)
                    
                    if data:
                        rows = await save_to_duckdb(project_id, endpoint['name'], data)
                        total_rows += rows
                        tables_synced += 1
                        results.append({
                            "table": endpoint['name'],
                            "rows": rows,
                            "success": True,
                            "type": "configuration_master"
                        })
                        logger.info(f"[UKG-SYNC] [{job_id}] {endpoint['name']}: {rows} rows")
                    else:
                        results.append({
                            "table": endpoint['name'],
                            "rows": 0,
                            "success": True,
                            "type": "configuration_master",
                            "note": "empty or no permission"
                        })
                        
                except Exception as e:
                    tables_failed += 1
                    error_msg = str(e)
                    errors.append(f"{endpoint['name']}: {error_msg}")
                    results.append({
                        "table": endpoint['name'],
                        "rows": 0,
                        "success": False,
                        "error": error_msg
                    })
                
                job['tables_synced'] = tables_synced
                job['total_rows'] = total_rows
                
                # Polite delay
                await asyncio.sleep(0.5)
            
            # =====================================================
            # STEP 4: Pull employee/personnel data (REALITY)
            # =====================================================
            reality_endpoints = [
                {"name": "person_details", "path": "/personnel/v1/person-details"},
                {"name": "employment_details", "path": "/personnel/v1/employment-details"},
                {"name": "compensation_details", "path": "/personnel/v1/compensation-details"},
                {"name": "employee_deductions", "path": "/personnel/v1/emp-deductions"},
                {"name": "pto_plans", "path": "/personnel/v1/pto-plans"},
                {"name": "contacts", "path": "/personnel/v1/contacts"},
                {"name": "direct_deposit", "path": "/payroll/v1/direct-deposit"},
            ]
            
            for endpoint in reality_endpoints:
                table_index += 1
                job['current_step'] = f'Pulling {endpoint["name"]}...'
                job['tables_processed'] = table_index
                logger.info(f"[UKG-SYNC] [{job_id}] Pulling {endpoint['name']}...")
                
                url = f"https://{hostname}{endpoint['path']}"
                
                try:
                    data = await fetch_all_pages(client, url, headers, job_id)
                    
                    if data:
                        rows = await save_to_duckdb(project_id, endpoint['name'], data)
                        total_rows += rows
                        tables_synced += 1
                        results.append({
                            "table": endpoint['name'],
                            "rows": rows,
                            "success": True,
                            "type": "reality"
                        })
                    else:
                        results.append({
                            "table": endpoint['name'],
                            "rows": 0,
                            "success": True,
                            "type": "reality",
                            "note": "empty or no permission"
                        })
                        
                except Exception as e:
                    tables_failed += 1
                    error_msg = str(e)
                    errors.append(f"{endpoint['name']}: {error_msg}")
                    results.append({
                        "table": endpoint['name'],
                        "rows": 0,
                        "success": False,
                        "error": error_msg
                    })
                
                job['tables_synced'] = tables_synced
                job['total_rows'] = total_rows
                
                # Polite delay
                await asyncio.sleep(1.0)
        
        # Update last sync time in Supabase
        try:
            supabase = get_supabase()
            supabase.table('api_connections') \
                .update({'last_pull_at': datetime.now().isoformat()}) \
                .eq('project_name', project_id) \
                .eq('provider', 'ukg_pro') \
                .execute()
        except Exception as e:
            logger.warning(f"[UKG-SYNC] Could not update last_pull_at: {e}")
        
        # Mark job complete
        job['status'] = 'completed'
        job['completed_at'] = datetime.now().isoformat()
        job['success'] = tables_failed < tables_synced
        job['tables_synced'] = tables_synced
        job['tables_failed'] = tables_failed
        job['total_rows'] = total_rows
        job['results'] = results
        job['errors'] = errors
        job['current_step'] = 'Complete!'
        
        logger.info(f"[UKG-SYNC] [{job_id}] COMPLETE: {tables_synced} tables, {total_rows} rows, {tables_failed} failures")
        
        # =====================================================
        # STEP 5: Post-sync - Register tables and profile columns
        # This enables the intelligence layer to find and query these tables
        # =====================================================
        job['current_step'] = 'Post-processing: registering tables and profiling columns...'
        logger.info(f"[UKG-SYNC] [{job_id}] Starting post-sync processing...")
        
        try:
            from utils.structured_data_handler import get_structured_handler
            handler = get_structured_handler()
            
            # Get all synced table names
            synced_tables = [r['table'] for r in results if r.get('success') and r.get('rows', 0) > 0]
            
            for table_info in results:
                if not table_info.get('success') or table_info.get('rows', 0) == 0:
                    continue
                    
                table_name = f"{project_id}_api_{table_info['table'].replace('-', '_').replace(' ', '_').lower()}"
                display_name = f"API: {table_info['table']}"
                row_count = table_info.get('rows', 0)
                truth_type = 'configuration' if table_info.get('type') == 'config' else 'reality'
                
                # Derive entity_type from API endpoint name (e.g., "jobs" → "jobs", "person_details" → "person_details")
                entity_type = table_info['table'].replace('-', '_').replace(' ', '_').lower()
                
                try:
                    # Register in _schema_metadata (DELETE + INSERT since no unique constraint on table_name)
                    handler.conn.execute("""
                        DELETE FROM _schema_metadata WHERE table_name = ?
                    """, [table_name])
                    
                    handler.conn.execute("""
                        INSERT INTO _schema_metadata 
                        (project, file_name, sheet_name, table_name, row_count, is_current, display_name, truth_type, category, columns, entity_type)
                        VALUES (?, ?, 'Sheet1', ?, ?, TRUE, ?, ?, 'api', '[]', ?)
                    """, [project_id, display_name, table_name, row_count, display_name, truth_type, entity_type])
                    
                    # Profile columns
                    handler.profile_columns_fast(project_id, table_name)
                    
                except Exception as profile_err:
                    logger.warning(f"[UKG-SYNC] Could not profile {table_name}: {profile_err}")
            
            # Recalc term index
            try:
                from backend.utils.intelligence.term_index import recalc_term_index
                recalc_term_index(handler.conn, project_id)
                logger.info(f"[UKG-SYNC] [{job_id}] Term index recalculated")
            except Exception as term_err:
                logger.warning(f"[UKG-SYNC] Could not recalc term index: {term_err}")
            
            # v5.2: Auto-compute context graph after sync
            try:
                job['current_step'] = 'Computing context graph...'
                handler.compute_context_graph(project_id)
                logger.info(f"[UKG-SYNC] [{job_id}] Context graph computed")
            except Exception as cg_err:
                logger.warning(f"[UKG-SYNC] Could not compute context graph: {cg_err}")
            
            # v5.2 FIX: Final checkpoint to persist ALL changes (schema, profiles, context graph)
            try:
                handler.conn.execute("CHECKPOINT")
                logger.info(f"[UKG-SYNC] [{job_id}] Final checkpoint completed - data persisted")
            except Exception as ckpt_err:
                logger.warning(f"[UKG-SYNC] Checkpoint warning: {ckpt_err}")
            
            logger.info(f"[UKG-SYNC] [{job_id}] Post-sync processing complete")
            job['current_step'] = 'Complete (with profiling)!'
            
        except Exception as post_err:
            logger.error(f"[UKG-SYNC] [{job_id}] Post-sync processing failed: {post_err}")
            job['errors'].append(f"Post-sync profiling failed: {post_err}")
        
    except Exception as e:
        logger.error(f"[UKG-SYNC] [{job_id}] Job failed: {e}")
        job['status'] = 'failed'
        job['error'] = str(e)
        job['completed_at'] = datetime.now().isoformat()


class SyncJobResponse(BaseModel):
    """Response when starting a sync job"""
    job_id: str
    status: str
    message: str


class SyncStatusResponse(BaseModel):
    """Response for sync job status"""
    job_id: str
    status: str
    current_step: Optional[str] = None
    tables_processed: Optional[int] = None
    total_tables: Optional[int] = None
    tables_synced: Optional[int] = None
    tables_failed: Optional[int] = None
    total_rows: Optional[int] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    success: Optional[bool] = None
    errors: Optional[List[str]] = None


@router.post("/sync-config/{project_id}", response_model=SyncJobResponse)
async def start_sync(project_id: str):
    """
    Start a background sync job to pull ALL UKG Pro data.
    
    Returns a job_id that can be polled for status.
    """
    global _sync_jobs
    
    logger.info(f"[UKG-SYNC] Starting sync job for project {project_id}")
    
    # Get saved credentials
    conn_data = await get_connection_creds(project_id)
    if not conn_data:
        raise HTTPException(404, "No UKG Pro connection found for this project. Set up connection first.")
    
    hostname = conn_data.get('hostname', '')
    if not hostname:
        raise HTTPException(400, "Connection missing hostname")
    
    # Check if there's already a running job for this project
    for jid, job in _sync_jobs.items():
        if job.get('project_id') == project_id and job.get('status') == 'running':
            return SyncJobResponse(
                job_id=jid,
                status='already_running',
                message='A sync is already in progress for this project'
            )
    
    # Create job
    job_id = str(uuid.uuid4())[:8]
    _sync_jobs[job_id] = {
        'project_id': project_id,
        'status': 'queued',
        'created_at': datetime.now().isoformat(),
        'current_step': 'Starting...',
        'tables_processed': 0,
        'total_tables': 0,
        'tables_synced': 0,
        'total_rows': 0,
    }
    
    # Start background task
    asyncio.create_task(run_sync_job(job_id, project_id, conn_data))
    
    return SyncJobResponse(
        job_id=job_id,
        status='started',
        message='Sync job started. Poll /api/ukg/sync-status/{job_id} for progress.'
    )


@router.get("/sync-status/{job_id}", response_model=SyncStatusResponse)
async def get_sync_status(job_id: str):
    """
    Get the status of a sync job.
    """
    global _sync_jobs
    
    job = _sync_jobs.get(job_id)
    if not job:
        raise HTTPException(404, f"Job {job_id} not found")
    
    return SyncStatusResponse(
        job_id=job_id,
        status=job.get('status', 'unknown'),
        current_step=job.get('current_step'),
        tables_processed=job.get('tables_processed'),
        total_tables=job.get('total_tables'),
        tables_synced=job.get('tables_synced'),
        tables_failed=job.get('tables_failed'),
        total_rows=job.get('total_rows'),
        started_at=job.get('started_at'),
        completed_at=job.get('completed_at'),
        success=job.get('success'),
        errors=job.get('errors'),
    )
