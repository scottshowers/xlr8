"""
UKG Pro API Connector Router
============================

Handles connections to UKG Pro REST APIs for pulling configuration and employee data.

Endpoints:
- POST /api/ukg/test-connection - Test API credentials
- GET /api/ukg/code-tables - Get list of all code tables
- GET /api/ukg/code-tables/{table_name} - Get specific code table data
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import httpx
import base64
import logging

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
