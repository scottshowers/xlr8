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
import uuid
import re
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ukg", tags=["ukg-connector"])


def extract_org_level_mappings(conn, project_id: str):
    """
    Extract org level mappings from the org_levels configuration table.
    
    UKG Pro stores organization hierarchy levels (District, Department, etc.) 
    in a config table with (level, levelDescription) pairs. We need to know:
    - level=1, levelDescription="District" → employee column "orgLevel1"
    - level=2, levelDescription="Department" → employee column "orgLevel2"
    
    This creates a _term_mappings table that QueryEngine uses to understand
    questions like "how many employees by department".
    """
    try:
        # Find the org_levels table for this project
        org_levels_table = f"{project_id}_api_org_levels"
        
        # Check if table exists
        tables = conn.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_name = ?
        """, [org_levels_table]).fetchall()
        
        if not tables:
            logger.warning(f"[ORG-MAPPING] No org_levels table found for {project_id}")
            return
        
        # Get distinct level mappings
        try:
            mappings = conn.execute(f"""
                SELECT DISTINCT level, levelDescription
                FROM "{org_levels_table}"
                WHERE level IS NOT NULL AND levelDescription IS NOT NULL
                ORDER BY level
            """).fetchall()
        except Exception as e:
            # Try alternate column names
            logger.warning(f"[ORG-MAPPING] Standard columns not found, trying alternates: {e}")
            try:
                mappings = conn.execute(f"""
                    SELECT DISTINCT level, "levelDescription"
                    FROM "{org_levels_table}"
                    WHERE level IS NOT NULL
                    ORDER BY level
                """).fetchall()
            except:
                logger.warning(f"[ORG-MAPPING] Could not read org_levels structure")
                return
        
        if not mappings:
            logger.warning(f"[ORG-MAPPING] No level mappings found in {org_levels_table}")
            return
        
        logger.info(f"[ORG-MAPPING] Found {len(mappings)} org level mappings")
        
        # Create _term_mappings table if not exists
        conn.execute("""
            CREATE TABLE IF NOT EXISTS _term_mappings (
                id INTEGER PRIMARY KEY,
                project VARCHAR,
                term VARCHAR,
                term_lower VARCHAR,
                employee_column VARCHAR,
                lookup_table VARCHAR,
                lookup_key_column VARCHAR,
                lookup_display_column VARCHAR,
                lookup_filter VARCHAR,
                mapping_type VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Clear old mappings for this project
        conn.execute("DELETE FROM _term_mappings WHERE project = ?", [project_id])
        
        # Insert mappings
        for level, level_desc in mappings:
            if not level_desc:
                continue
                
            term = level_desc.strip()
            term_lower = term.lower()
            employee_column = f"orgLevel{level}"
            
            # Generate a unique ID
            mapping_id = hash(f"{project_id}_{term_lower}_{level}") % 2147483647
            
            conn.execute("""
                INSERT INTO _term_mappings 
                (id, project, term, term_lower, employee_column, lookup_table, 
                 lookup_key_column, lookup_display_column, lookup_filter, mapping_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                mapping_id,
                project_id,
                term,
                term_lower,
                employee_column,
                org_levels_table,
                'code',
                'description',
                f'level = {level}',
                'org_level'
            ])
            
            logger.info(f"[ORG-MAPPING] Mapped '{term}' → {employee_column} (level={level})")
        
        conn.commit()
        logger.info(f"[ORG-MAPPING] Successfully created {len(mappings)} term mappings for {project_id}")
        
    except Exception as e:
        logger.error(f"[ORG-MAPPING] Failed to extract org level mappings: {e}")
        import traceback
        logger.error(traceback.format_exc())


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

# In-memory job tracking (would use Redis in production)
_sync_jobs: Dict[str, Dict] = {}


def to_snake_case(name: str) -> str:
    """
    Convert API names to snake_case for consistency with schema.
    
    Handles:
    - ALLCAPS: EMPLOYEETYPE → employee_type
    - camelCase: employeeType → employee_type  
    - PascalCase: EmployeeType → employee_type
    - Already snake: employee_type → employee_type
    - Kebab-case: employee-type → employee_type
    """
    if not name:
        return name
    
    # Replace hyphens and spaces with underscores
    name = name.replace('-', '_').replace(' ', '_')
    
    # Handle ALLCAPS: EMPLOYEETYPE → EMPLOYEE_TYPE first
    # Insert underscore before each capital that follows a lowercase
    # or before a capital that's followed by lowercase (for runs like "XMLParser")
    if name.isupper():
        # Pure ALLCAPS - need to detect word boundaries
        # Common patterns: EMPLOYEETYPE, MARITALSTATUS, COBRATYPE
        # Use a simple heuristic: known suffixes
        suffixes = ['TYPE', 'STATUS', 'CODE', 'GROUP', 'LEVEL', 'RATE', 'PLAN', 
                    'BRANCH', 'ERA', 'PREFIX', 'SUFFIX', 'SOURCE', 'REASON']
        for suffix in suffixes:
            if name.endswith(suffix) and len(name) > len(suffix):
                name = name[:-len(suffix)] + '_' + suffix
                break
    
    # Handle camelCase and PascalCase
    # Insert underscore before uppercase letters that follow lowercase
    name = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', name)
    
    # Handle sequences of caps followed by lowercase (e.g., XMLParser → XML_Parser)
    name = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', name)
    
    return name.lower()


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


def parse_link_header(link_header: str) -> Optional[str]:
    """Parse RFC 5988 Link header to find 'next' URL."""
    if not link_header:
        return None
    
    # Link header format: <url>; rel="next", <url>; rel="last"
    for part in link_header.split(','):
        part = part.strip()
        if 'rel="next"' in part or "rel='next'" in part:
            # Extract URL between < and >
            start = part.find('<')
            end = part.find('>')
            if start != -1 and end != -1:
                return part[start + 1:end]
    return None


async def fetch_all_pages(client: httpx.AsyncClient, url: str, headers: Dict, job_id: str = None) -> List[Dict]:
    """Fetch all pages from a paginated endpoint.
    
    Tries pagination strategies:
    1. RFC 5988 Link headers (preferred)
    2. Page parameter increment (fallback)
    3. Stops if duplicate data detected
    """
    all_data = []
    current_url = url
    page_count = 0
    max_pages = 200  # Safety limit
    max_retries = 2
    
    # Track if we need to use page-based pagination
    use_page_param = False
    base_url = url.split('?')[0]
    base_params = {}
    if '?' in url:
        param_str = url.split('?')[1]
        for p in param_str.split('&'):
            if '=' in p:
                k, v = p.split('=', 1)
                base_params[k] = v
    
    # Track data signatures to detect duplicates
    last_data_signature = None
    
    while current_url and page_count < max_pages:
        retry_count = 0
        page_count += 1
        
        while retry_count <= max_retries:
            try:
                logger.warning(f"[UKG-SYNC] Fetching page {page_count}: {current_url}")
                response = await client.get(current_url, headers=headers)
                
                if response.status_code == 429:
                    # Rate limited - wait and retry
                    retry_after = int(response.headers.get('Retry-After', 30))
                    logger.warning(f"[UKG-SYNC] Rate limited, waiting {retry_after}s...")
                    await asyncio.sleep(retry_after)
                    retry_count += 1
                    continue
                
                if response.status_code == 400:
                    # Bad request - might be invalid parameter
                    logger.warning(f"[UKG-SYNC] 400 error: {response.text[:200]}")
                    # If it's complaining about per_page, try without it
                    if 'per_page' in response.text.lower() or 'per_Page' in response.text:
                        if 'per_page' in base_params:
                            del base_params['per_page']
                            param_str = '&'.join(f"{k}={v}" for k, v in base_params.items())
                            current_url = f"{base_url}?{param_str}" if param_str else base_url
                            logger.warning(f"[UKG-SYNC] Retrying without per_page: {current_url}")
                            continue
                    return all_data
                
                if response.status_code != 200:
                    logger.warning(f"[UKG-SYNC] {current_url[:80]} returned {response.status_code}: {response.text[:200]}")
                    return all_data
                
                # Log ALL response headers for debugging pagination
                logger.warning(f"[UKG-SYNC] Response headers: {dict(response.headers)}")
                
                data = response.json()
                
                if not data:
                    logger.warning(f"[UKG-SYNC] Page {page_count}: No data returned, stopping")
                    return all_data
                    
                if isinstance(data, list):
                    page_size = len(data)
                    
                    # Create a signature of this page's data to detect duplicates
                    # Use first and last item IDs/keys if available
                    if data:
                        first_item = str(data[0])[:100] if data else ""
                        last_item = str(data[-1])[:100] if data else ""
                        data_signature = f"{page_size}:{first_item}:{last_item}"
                        
                        if data_signature == last_data_signature:
                            logger.warning(f"[UKG-SYNC] Page {page_count}: DUPLICATE DATA DETECTED - same as previous page, stopping")
                            return all_data
                        
                        last_data_signature = data_signature
                    
                    all_data.extend(data)
                    logger.warning(f"[UKG-SYNC] Page {page_count}: {page_size} rows (total: {len(all_data)})")
                    
                    # If we got less than expected page size, we're probably done
                    expected_size = int(base_params.get('per_page', 100))
                    if page_size < expected_size:
                        logger.warning(f"[UKG-SYNC] Got {page_size} rows (less than {expected_size}), assuming last page")
                        return all_data
                else:
                    # Single object response
                    logger.warning(f"[UKG-SYNC] Got single object response, not a list")
                    return [data] if data else []
                
                # Check for next page via Link header first
                link_header = response.headers.get('Link', '')
                if link_header:
                    logger.warning(f"[UKG-SYNC] Page {page_count} Link header: '{link_header}'")
                    next_url = parse_link_header(link_header)
                    
                    if next_url:
                        logger.warning(f"[UKG-SYNC] Found next URL from Link header")
                        current_url = next_url
                    else:
                        logger.warning(f"[UKG-SYNC] No 'next' in Link header, stopping")
                        return all_data
                else:
                    # No Link header - try page parameter pagination
                    # Only continue if we got a full page (might be more data)
                    expected_size = int(base_params.get('per_page', 100))
                    if page_size >= expected_size:
                        # Got full page, try next page
                        next_page = page_count + 1
                        base_params['page'] = str(next_page)
                        param_str = '&'.join(f"{k}={v}" for k, v in base_params.items())
                        current_url = f"{base_url}?{param_str}"
                        logger.warning(f"[UKG-SYNC] No Link header, trying page {next_page}: {current_url}")
                    else:
                        # Got partial page, we're done
                        logger.warning(f"[UKG-SYNC] No Link header and partial page ({page_size} < {expected_size}), stopping")
                        return all_data
                    
                # Polite delay - don't hammer UKG
                await asyncio.sleep(0.5)
                break  # Success - exit retry loop
                
            except httpx.TimeoutException as e:
                retry_count += 1
                logger.warning(f"[UKG-SYNC] Timeout on page {page_count} (attempt {retry_count}/{max_retries+1}): {e}")
                if retry_count > max_retries:
                    logger.error(f"[UKG-SYNC] Giving up after {max_retries+1} attempts")
                    return all_data
                await asyncio.sleep(5)  # Wait before retry
                
            except Exception as e:
                logger.error(f"[UKG-SYNC] Error on page {page_count}: {e}")
                return all_data
        
        # If we exhausted retries, exit
        if retry_count > max_retries:
            break
    
    if page_count >= max_pages:
        logger.warning(f"[UKG-SYNC] Hit max page limit ({max_pages})")
    
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
        
        # Sanitize table name - convert to snake_case for schema consistency
        safe_table = to_snake_case(table_name)
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
    
    # Get sync configuration for this project
    sync_config = await get_sync_config(project_id)
    logger.info(f"[UKG-SYNC] [{job_id}] Loaded sync config: {len(sync_config)} endpoints configured")
    
    try:
        # Global timeout for entire sync: 15 minutes max
        # Individual requests: 60s (UKG can be slow)
        timeout = httpx.Timeout(60.0, connect=10.0)
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            # =====================================================
            # STEP 1: Discover all available code tables
            # =====================================================
            job['current_step'] = 'Discovering code tables...'
            job['last_heartbeat'] = datetime.now().isoformat()
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
                job['last_heartbeat'] = datetime.now().isoformat()
                logger.info(f"[UKG-SYNC] [{job_id}] [{table_index}/{len(available_tables)}] Pulling {table_name}...")
                
                # Use the provided URL if available, otherwise construct it
                if table_url:
                    url = table_url if '?' in table_url else f"{table_url}?page=1&per_page=500"
                else:
                    url = f"https://{hostname}/configuration/v1/code-tables/{table_name}?page=1&per_page=500"
                
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
                job['last_heartbeat'] = datetime.now().isoformat()
                logger.info(f"[UKG-SYNC] [{job_id}] Pulling config: {endpoint['name']}...")
                
                url = f"https://{hostname}{endpoint['path']}?page=1&per_page=500"
                
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
            # Uses sync_config to determine which endpoints and filters
            # =====================================================
            
            # Build list of enabled endpoints from config
            enabled_endpoints = []
            for endpoint_name, endpoint_config in sync_config.items():
                if endpoint_config.get('enabled', True) and endpoint_name in REALITY_ENDPOINT_PATHS:
                    enabled_endpoints.append({
                        "name": endpoint_name,
                        "path": REALITY_ENDPOINT_PATHS[endpoint_name],
                        "config": endpoint_config
                    })
            
            logger.info(f"[UKG-SYNC] [{job_id}] Will pull {len(enabled_endpoints)} reality endpoints")
            
            for endpoint in enabled_endpoints:
                table_index += 1
                endpoint_name = endpoint["name"]
                endpoint_config = endpoint["config"]
                
                job['current_step'] = f'Pulling {endpoint_name}...'
                job['tables_processed'] = table_index
                job['last_heartbeat'] = datetime.now().isoformat()
                logger.info(f"[UKG-SYNC] [{job_id}] Pulling {endpoint_name}...")
                
                # Build URL with filter parameters
                base_url = f"https://{hostname}{endpoint['path']}"
                filter_params = build_filter_params(endpoint_name, sync_config)
                
                if filter_params is None:
                    # Endpoint disabled
                    logger.info(f"[UKG-SYNC] [{job_id}] Skipping disabled endpoint: {endpoint_name}")
                    continue
                
                # Add filter params to URL (always include per_page)
                if filter_params:
                    param_str = '&'.join(f"{k}={v}" for k, v in filter_params.items())
                    url = f"{base_url}?{param_str}"
                    logger.warning(f"[UKG-SYNC] [{job_id}] Fetching with params: {filter_params}")
                else:
                    # Even with no filters, add page and per_page for efficiency
                    url = f"{base_url}?page=1&per_page=500"
                    logger.warning(f"[UKG-SYNC] [{job_id}] Fetching with default page=1&per_page=500")
                
                try:
                    data = await fetch_all_pages(client, url, headers, job_id)
                    
                    if data:
                        rows = await save_to_duckdb(project_id, endpoint_name, data)
                        total_rows += rows
                        tables_synced += 1
                        results.append({
                            "table": endpoint_name,
                            "rows": rows,
                            "success": True,
                            "type": "reality",
                            "filters": filter_params
                        })
                    else:
                        results.append({
                            "table": endpoint_name,
                            "rows": 0,
                            "success": True,
                            "type": "reality",
                            "note": "empty or no permission"
                        })
                        
                except Exception as e:
                    tables_failed += 1
                    error_msg = str(e)
                    errors.append(f"{endpoint_name}: {error_msg}")
                    results.append({
                        "table": endpoint_name,
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
        
        # Track sync stats (but don't mark complete yet - post-processing still needed)
        job['tables_synced'] = tables_synced
        job['tables_failed'] = tables_failed
        job['total_rows'] = total_rows
        job['results'] = results
        job['errors'] = errors
        job['current_step'] = 'Data sync complete, starting post-processing...'
        job['last_heartbeat'] = datetime.now().isoformat()
        
        logger.info(f"[UKG-SYNC] [{job_id}] DATA SYNC COMPLETE: {tables_synced} tables, {total_rows} rows, {tables_failed} failures")
        
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
                
                # Convert API table name to snake_case for schema consistency
                safe_name = to_snake_case(table_info['table'])
                table_name = f"{project_id}_api_{safe_name}"
                display_name = f"API: {table_info['table']}"
                row_count = table_info.get('rows', 0)
                truth_type = 'reality' if table_info.get('type') == 'reality' else 'configuration'
                
                # entity_type matches hub names in schema (snake_case)
                # EMPLOYEETYPE → employee_type, person_details → person_details
                entity_type = safe_name
                
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
            
            # v5.3: Extract org level mappings from config tables
            try:
                job['current_step'] = 'Extracting org level mappings...'
                extract_org_level_mappings(handler.conn, project_id)
                logger.info(f"[UKG-SYNC] [{job_id}] Org level mappings extracted")
            except Exception as org_err:
                logger.warning(f"[UKG-SYNC] Could not extract org level mappings: {org_err}")
            
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
            job['current_step'] = 'Complete!'
            job['status'] = 'completed'
            job['completed_at'] = datetime.now().isoformat()
            job['success'] = tables_failed < tables_synced
            
        except Exception as post_err:
            logger.error(f"[UKG-SYNC] [{job_id}] Post-sync processing failed: {post_err}")
            import traceback
            logger.error(f"[UKG-SYNC] [{job_id}] Traceback: {traceback.format_exc()}")
            job['errors'].append(f"Post-sync profiling failed: {post_err}")
            job['status'] = 'completed_with_errors'
            job['completed_at'] = datetime.now().isoformat()
            job['success'] = False
            job['current_step'] = f'Completed with errors: {post_err}'
        
    except Exception as e:
        import traceback
        logger.error(f"[UKG-SYNC] [{job_id}] Job failed: {e}")
        logger.error(f"[UKG-SYNC] [{job_id}] Traceback: {traceback.format_exc()}")
        job['status'] = 'failed'
        job['error'] = str(e)
        job['completed_at'] = datetime.now().isoformat()
        job['current_step'] = f'FAILED: {e}'


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
    last_heartbeat: Optional[str] = None
    success: Optional[bool] = None
    errors: Optional[List[str]] = None


# =============================================================================
# SYNC CONFIGURATION
# =============================================================================

class EndpointConfig(BaseModel):
    """Configuration for a single endpoint"""
    enabled: bool = True
    statuses: List[str] = ["A"]  # A=Active, L=Leave, T=Terminated
    term_cutoff_date: Optional[str] = "2025-01-01"  # For terminated employees

class SyncConfig(BaseModel):
    """Full sync configuration for a project"""
    endpoint_configs: Dict[str, EndpointConfig] = {}

# Default endpoint configurations
DEFAULT_SYNC_CONFIG = {
    "person_details": {
        "enabled": True,
        "statuses": ["A", "L", "T"],
        "term_cutoff_date": "2025-01-01"
    },
    "employment_details": {
        "enabled": True,
        "statuses": ["A", "L", "T"],
        "term_cutoff_date": "2025-01-01"
    },
    "compensation_details": {
        "enabled": True,
        "statuses": ["A", "L", "T"],
        "term_cutoff_date": "2025-01-01"
    },
    "employee_job_history": {
        "enabled": True,
        "statuses": ["A", "L", "T"],
        "term_cutoff_date": "2025-01-01"
    },
    "employee_changes": {
        "enabled": True,
        "statuses": [],  # Uses rolling 6 months, not status filter
        "term_cutoff_date": None  # Rolling 6 months computed at sync time
    },
    "employee_demographic_details": {
        "enabled": True,
        "statuses": ["A", "L", "T"],
        "term_cutoff_date": "2025-01-01"
    },
    "employee_education": {
        "enabled": True,
        "statuses": ["A", "L", "T"],
        "term_cutoff_date": "2025-01-01"
    },
    "contacts": {
        "enabled": True,
        "statuses": ["A", "L", "T"],
        "term_cutoff_date": "2025-01-01"
    },
    "pto_plans": {
        "enabled": True,
        "statuses": ["A", "L"],
        "term_cutoff_date": None  # No terms for PTO
    }
}

# Endpoint path mapping
REALITY_ENDPOINT_PATHS = {
    "person_details": "/personnel/v1/person-details",
    "employment_details": "/personnel/v1/employment-details",
    "compensation_details": "/personnel/v1/compensation-details",
    "employee_job_history": "/personnel/v1/employee-job-history-details",
    "employee_changes": "/personnel/v1/employee-changes",
    "employee_demographic_details": "/personnel/v1/employee-demographic-details",
    "employee_education": "/personnel/v1/employee-education",
    "contacts": "/personnel/v1/contacts",
    "pto_plans": "/personnel/v1/pto-plans",
}


@router.get("/sync-settings/{project_id}")
async def get_sync_settings(project_id: str):
    """Get sync configuration for a customer. Returns defaults if none saved."""
    try:
        supabase = get_supabase()
        result = supabase.table('ukg_sync_config') \
            .select('*') \
            .eq('customer_id', project_id) \
            .execute()
        
        if result.data and len(result.data) > 0:
            config = result.data[0].get('endpoint_configs', {})
            # Merge with defaults to ensure all endpoints are present
            merged = {**DEFAULT_SYNC_CONFIG}
            for k, v in config.items():
                if k in merged:
                    merged[k].update(v)
                else:
                    merged[k] = v
            return {"customer_id": project_id, "endpoint_configs": merged}
        else:
            return {"customer_id": project_id, "endpoint_configs": DEFAULT_SYNC_CONFIG}
    except Exception as e:
        logger.warning(f"[UKG-SYNC] Could not fetch sync config: {e}, using defaults")
        return {"customer_id": project_id, "endpoint_configs": DEFAULT_SYNC_CONFIG}


@router.post("/sync-settings/{project_id}")
async def save_sync_settings(project_id: str, config: SyncConfig):
    """Save sync configuration for a customer."""
    try:
        supabase = get_supabase()
        
        # Convert Pydantic models to dicts
        config_dict = {k: v.dict() if hasattr(v, 'dict') else v for k, v in config.endpoint_configs.items()}
        
        # Upsert the config
        result = supabase.table('ukg_sync_config') \
            .upsert({
                'customer_id': project_id,
                'endpoint_configs': config_dict
            }, on_conflict='customer_id') \
            .execute()
        
        return {"success": True, "message": "Sync settings saved"}
    except Exception as e:
        logger.error(f"[UKG-SYNC] Failed to save sync config: {e}")
        raise HTTPException(500, f"Failed to save sync settings: {str(e)}")


async def get_sync_config(project_id: str) -> Dict:
    """Get sync config for use in sync job."""
    try:
        supabase = get_supabase()
        result = supabase.table('ukg_sync_config') \
            .select('endpoint_configs') \
            .eq('customer_id', project_id) \
            .execute()
        
        if result.data and len(result.data) > 0:
            saved = result.data[0].get('endpoint_configs', {})
            # Merge with defaults
            merged = {**DEFAULT_SYNC_CONFIG}
            for k, v in saved.items():
                if k in merged:
                    merged[k] = {**merged[k], **v}
                else:
                    merged[k] = v
            return merged
        return DEFAULT_SYNC_CONFIG
    except Exception as e:
        logger.warning(f"[UKG-SYNC] Could not fetch sync config: {e}, using defaults")
        return DEFAULT_SYNC_CONFIG


def build_filter_params(endpoint_name: str, config: Dict) -> Dict[str, str]:
    """Build query parameters for filtering employee data."""
    params = {}
    endpoint_config = config.get(endpoint_name, {})
    
    if not endpoint_config.get('enabled', True):
        return None  # Signal to skip this endpoint
    
    # Always request max page size for efficiency (except for endpoints that don't support it)
    if endpoint_name not in ['employee_changes']:
        params['page'] = '1'  # Start at page 1
        params['per_page'] = '500'  # UKG default is 100, max varies by endpoint
    
    statuses = endpoint_config.get('statuses', [])
    term_cutoff = endpoint_config.get('term_cutoff_date')
    
    # Special handling for employee_changes - rolling 6 months
    if endpoint_name == 'employee_changes':
        six_months_ago = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
        params['startDate'] = six_months_ago
        return params
    
    # Build status filter
    # UKG uses employmentStatus parameter
    # IMPORTANT: Do NOT combine terminationDate with other statuses - it will exclude active employees!
    # If user wants A,L,T with term cutoff, we'd need multiple API calls (not implemented yet)
    if statuses:
        # For now, just filter by status without terminationDate
        # This means we get ALL terminated employees, not just recent ones
        # TODO: Implement multi-call approach for filtered terminated employees
        params['employmentStatus'] = ','.join(statuses)
        
        # Log a warning if they have term_cutoff configured but we're ignoring it
        if 'T' in statuses and term_cutoff:
            logger.warning(f"[UKG-SYNC] terminationDate filter disabled - would exclude active employees. Getting all terminated.")
    
    return params


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
        last_heartbeat=job.get('last_heartbeat'),
        success=job.get('success'),
        errors=job.get('errors'),
    )
