"""
XLR8 INTEGRATIONS ROUTER - API Connections
==========================================

Manages system connections and API data pulls.

Endpoints:
  GET  /api/integrations/systems - List all available systems
  GET  /api/integrations/systems/{id} - Get system details
  GET  /api/integrations/systems/{id}/endpoints - Get system endpoints
  
  POST /api/integrations/connections - Save connection credentials
  GET  /api/integrations/connections/{project} - Get project connections
  POST /api/integrations/connections/{project}/test - Test connection
  POST /api/integrations/connections/{project}/pull - Pull data from API

Deploy to: backend/routers/integrations_router.py

Add to main.py:
    from backend.routers import integrations_router
    app.include_router(integrations_router.router, prefix="/api/integrations", tags=["integrations"])

Created: January 17, 2026
"""

import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# MODELS
# =============================================================================

class ConnectionCredentials(BaseModel):
    """Credentials for a system connection."""
    customer_id: str
    system_id: str
    credentials: Dict[str, str]  # Encrypted in production


class ConnectionTestRequest(BaseModel):
    """Request to test a connection."""
    system_id: str
    credentials: Dict[str, str]


class DataPullRequest(BaseModel):
    """Request to pull data from an API."""
    system_id: str
    endpoints: List[str]  # List of endpoint IDs to pull


# =============================================================================
# SYSTEM LIBRARY ENDPOINTS
# =============================================================================

@router.get("/systems")
async def list_systems():
    """
    List all available systems organized by domain.
    
    Returns systems with their status (ready, coming_soon, etc.)
    """
    try:
        from backend.integrations.system_library import (
            get_all_systems, 
            SYSTEMS_BY_DOMAIN,
            to_dict
        )
    except ImportError:
        from integrations.system_library import (
            get_all_systems,
            SYSTEMS_BY_DOMAIN,
            to_dict
        )
    
    systems = get_all_systems()
    
    # Organize by domain
    by_domain = {}
    for domain, system_ids in SYSTEMS_BY_DOMAIN.items():
        by_domain[domain] = []
    
    for system in systems:
        if system.domain in by_domain:
            by_domain[system.domain].append(to_dict(system))
    
    return {
        "systems": [to_dict(s) for s in systems],
        "by_domain": by_domain,
        "domains": list(SYSTEMS_BY_DOMAIN.keys())
    }


@router.get("/systems/{system_id}")
async def get_system(system_id: str):
    """
    Get details for a specific system.
    
    Includes auth fields needed and available endpoints.
    """
    try:
        from backend.integrations.system_library import get_system, to_dict
    except ImportError:
        from integrations.system_library import get_system, to_dict
    
    system = get_system(system_id)
    if not system:
        raise HTTPException(status_code=404, detail=f"System {system_id} not found")
    
    return to_dict(system)


@router.get("/systems/{system_id}/endpoints")
async def get_system_endpoints(system_id: str, truth_bucket: Optional[str] = None):
    """
    Get available endpoints for a system.
    
    Optionally filter by truth bucket (reality, configuration, etc.)
    """
    try:
        from backend.integrations.system_library import (
            get_system_endpoints, 
            TruthBucket
        )
    except ImportError:
        from integrations.system_library import (
            get_system_endpoints,
            TruthBucket
        )
    
    bucket = None
    if truth_bucket:
        try:
            bucket = TruthBucket(truth_bucket)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid truth bucket: {truth_bucket}. Valid: reality, configuration, intent, reference, regulatory"
            )
    
    endpoints = get_system_endpoints(system_id, bucket)
    
    return {
        "system_id": system_id,
        "truth_bucket_filter": truth_bucket,
        "endpoints": [
            {
                "id": e.id,
                "name": e.name,
                "description": e.description,
                "path": e.path,
                "method": e.method,
                "truth_bucket": e.truth_bucket.value,
            }
            for e in endpoints
        ],
        "count": len(endpoints)
    }


# =============================================================================
# CONNECTION MANAGEMENT
# =============================================================================

def get_supabase():
    """Get Supabase client."""
    try:
        from utils.database.supabase_client import get_supabase as _get_supabase
        return _get_supabase()
    except ImportError:
        from backend.utils.database.supabase_client import get_supabase as _get_supabase
        return _get_supabase()


@router.post("/connections")
async def save_connection(request: ConnectionCredentials):
    """
    Save connection credentials for a project.
    
    Stores in Supabase api_connections table.
    """
    try:
        from backend.integrations.system_library import get_system
    except ImportError:
        from integrations.system_library import get_system
    
    system = get_system(request.system_id)
    if not system:
        raise HTTPException(status_code=404, detail=f"System {request.system_id} not found")
    
    # Validate required fields
    required_fields = [f["name"] for f in system.auth_fields if f.get("required")]
    missing = [f for f in required_fields if f not in request.credentials]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required credentials: {missing}"
        )
    
    try:
        supabase = get_supabase()
        
        # Check for existing connection
        existing = supabase.table('api_connections') \
            .select('id') \
            .eq('customer_id', request.customer_id) \
            .eq('provider', request.system_id) \
            .execute()
        
        if existing.data:
            # Update existing
            result = supabase.table('api_connections').update({
                'hostname': request.credentials.get('hostname', ''),
                'customer_api_key': request.credentials.get('customer_api_key', ''),
                'username': request.credentials.get('username', ''),
                'password': request.credentials.get('password', ''),
                'user_api_key': request.credentials.get('user_api_key', ''),
                'status': 'saved',
            }).eq('id', existing.data[0]['id']).execute()
            connection_id = existing.data[0]['id']
        else:
            # Create new
            result = supabase.table('api_connections').insert({
                'customer_id': request.customer_id,
                'provider': request.system_id,
                'connection_name': system.name,
                'hostname': request.credentials.get('hostname', ''),
                'customer_api_key': request.credentials.get('customer_api_key', ''),
                'username': request.credentials.get('username', ''),
                'password': request.credentials.get('password', ''),
                'user_api_key': request.credentials.get('user_api_key', ''),
                'status': 'saved',
            }).execute()
            connection_id = result.data[0]['id'] if result.data else None
        
        logger.info(f"[INTEGRATIONS] Saved connection for {request.system_id} in project {request.customer_id}")
        
        return {
            "success": True,
            "message": f"Connection saved for {system.name}",
            "connection_id": connection_id
        }
        
    except Exception as e:
        logger.error(f"[INTEGRATIONS] Save connection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/connections/{customer_id}")
async def get_project_connections(customer_id: str):
    """
    Get all connections for a project.
    """
    try:
        from backend.integrations.system_library import get_system
    except ImportError:
        from integrations.system_library import get_system
    
    try:
        supabase = get_supabase()
        
        result = supabase.table('api_connections') \
            .select('id, customer_id, provider, connection_name, hostname, username, status, created_at, last_connected_at') \
            .eq('customer_id', customer_id) \
            .execute()
        
        connections = []
        for conn in (result.data or []):
            system = get_system(conn.get('provider', ''))
            connections.append({
                "id": conn['id'],
                "system_id": conn['provider'],
                "system_name": system.name if system else conn.get('connection_name', conn['provider']),
                "hostname": conn.get('hostname', ''),
                "username": conn.get('username', ''),
                "status": conn.get('status', 'unknown'),
                "created_at": conn.get('created_at'),
                "last_tested": conn.get('last_connected_at'),
                "domain": system.domain if system else "HCM",
            })
        
        return {
            "customer_id": customer_id,
            "connections": connections,
            "count": len(connections)
        }
        
    except Exception as e:
        logger.error(f"[INTEGRATIONS] Get connections failed: {e}")
        # Return empty on error
        return {
            "customer_id": customer_id,
            "connections": [],
            "count": 0
        }


@router.post("/connections/{customer_id}/test")
async def test_connection(customer_id: str, request: ConnectionTestRequest):
    """
    Test a connection by making a simple API call.
    """
    try:
        from backend.integrations.system_library import get_system, ConnectionStatus
    except ImportError:
        from integrations.system_library import get_system, ConnectionStatus
    
    system = get_system(request.system_id)
    if not system:
        raise HTTPException(status_code=404, detail=f"System {request.system_id} not found")
    
    if system.status != ConnectionStatus.READY:
        return {
            "success": False,
            "system_id": request.system_id,
            "error": f"{system.name} is not yet available for connection (status: {system.status.value})"
        }
    
    # For UKG Pro, actually test the connection
    if request.system_id == "ukg_pro":
        try:
            result = await _test_ukg_pro_connection(request.credentials)
            
            # Update connection status in Supabase
            try:
                supabase = get_supabase()
                supabase.table('api_connections') \
                    .update({
                        'status': 'connected' if result['success'] else 'failed',
                        'last_connected_at': datetime.now().isoformat() if result['success'] else None,
                        'last_error': result.get('error') if not result['success'] else None,
                    }) \
                    .eq('customer_id', customer_id) \
                    .eq('provider', request.system_id) \
                    .execute()
            except Exception as e:
                logger.warning(f"[INTEGRATIONS] Could not update connection status: {e}")
            
            return result
        except Exception as e:
            logger.error(f"[INTEGRATIONS] UKG Pro test failed: {e}")
            return {
                "success": False,
                "system_id": request.system_id,
                "error": str(e)
            }
    
    # For other systems, return mock success
    return {
        "success": True,
        "system_id": request.system_id,
        "message": f"Connection test simulated for {system.name} (not yet implemented)"
    }


async def _test_ukg_pro_connection(credentials: Dict[str, str]) -> Dict:
    """
    Test UKG Pro connection by hitting a simple endpoint.
    """
    import httpx
    import base64
    
    # Build auth header
    hostname = credentials.get("hostname", "service5.ultipro.com")
    username = credentials.get("username", "")
    password = credentials.get("password", "")
    user_api_key = credentials.get("user_api_key", "")
    customer_api_key = credentials.get("customer_api_key", "")
    
    # UKG uses Basic auth with username:password
    auth_string = f"{username}:{password}"
    auth_bytes = base64.b64encode(auth_string.encode()).decode()
    
    headers = {
        "Authorization": f"Basic {auth_bytes}",
        "US-Customer-Api-Key": customer_api_key,
        "Api-Key": user_api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    
    # Test endpoint - code-tables is usually accessible
    test_url = f"https://{hostname}/configuration/v1/code-tables"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(test_url, headers=headers, timeout=30.0)
            
            if response.status_code == 200:
                data = response.json()
                table_count = len(data) if isinstance(data, list) else "unknown"
                return {
                    "success": True,
                    "system_id": "ukg_pro",
                    "message": f"Successfully connected to UKG Pro. Found {table_count} code tables.",
                    "details": {
                        "status_code": response.status_code,
                        "table_count": table_count
                    }
                }
            elif response.status_code == 401:
                return {
                    "success": False,
                    "system_id": "ukg_pro",
                    "error": "Authentication failed - check username/password/API keys",
                    "details": {"status_code": 401}
                }
            elif response.status_code == 403:
                return {
                    "success": False,
                    "system_id": "ukg_pro",
                    "error": "Forbidden - service account may need 'Company Configuration Integration' permission",
                    "details": {"status_code": 403}
                }
            else:
                return {
                    "success": False,
                    "system_id": "ukg_pro",
                    "error": f"Unexpected response: {response.status_code}",
                    "details": {
                        "status_code": response.status_code,
                        "response": response.text[:500] if response.text else None
                    }
                }
        except httpx.TimeoutException:
            return {
                "success": False,
                "system_id": "ukg_pro",
                "error": "Connection timed out - check hostname"
            }
        except httpx.ConnectError as e:
            return {
                "success": False,
                "system_id": "ukg_pro",
                "error": f"Could not connect - check hostname: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "system_id": "ukg_pro",
                "error": str(e)
            }


# =============================================================================
# DATA PULL
# =============================================================================

@router.post("/connections/{customer_id}/pull")
async def pull_data(customer_id: str, request: DataPullRequest):
    """
    Pull data from connected system into XLR8.
    
    Endpoints are pulled in sequence, data is stored in DuckDB
    with appropriate truth bucket classification.
    """
    try:
        from backend.integrations.system_library import get_system, get_system_endpoints, ConnectionStatus
    except ImportError:
        from integrations.system_library import get_system, get_system_endpoints, ConnectionStatus
    
    system = get_system(request.system_id)
    if not system:
        raise HTTPException(status_code=404, detail=f"System {request.system_id} not found")
    
    if system.status != ConnectionStatus.READY:
        raise HTTPException(
            status_code=400,
            detail=f"{system.name} is not yet available for data pull"
        )
    
    # Get connection credentials
    key = f"{customer_id}:{request.system_id}"
    connection = _connections.get(key)
    if not connection:
        raise HTTPException(
            status_code=400,
            detail=f"No connection saved for {system.name} in this project. Save credentials first."
        )
    
    # Validate requested endpoints
    available_endpoints = {e.id: e for e in system.endpoints}
    invalid_endpoints = [e for e in request.endpoints if e not in available_endpoints]
    if invalid_endpoints:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid endpoints: {invalid_endpoints}"
        )
    
    # Pull each endpoint
    results = []
    for endpoint_id in request.endpoints:
        endpoint = available_endpoints[endpoint_id]
        
        try:
            if request.system_id == "ukg_pro":
                result = await _pull_ukg_pro_endpoint(
                    customer_id=customer_id,
                    endpoint=endpoint,
                    credentials=connection["credentials"]
                )
            else:
                result = {
                    "endpoint_id": endpoint_id,
                    "success": False,
                    "error": f"Pull not implemented for {system.name}"
                }
            
            results.append(result)
            
        except Exception as e:
            logger.error(f"[INTEGRATIONS] Pull failed for {endpoint_id}: {e}")
            results.append({
                "endpoint_id": endpoint_id,
                "success": False,
                "error": str(e)
            })
    
    # Update last pull time
    connection["last_pull"] = datetime.now().isoformat()
    
    successful = sum(1 for r in results if r.get("success"))
    
    return {
        "customer_id": customer_id,
        "system_id": request.system_id,
        "endpoints_requested": len(request.endpoints),
        "endpoints_successful": successful,
        "results": results
    }


async def _pull_ukg_pro_endpoint(customer_id: str, endpoint, credentials: Dict[str, str]) -> Dict:
    """
    Pull data from a UKG Pro endpoint and store in DuckDB.
    """
    import httpx
    import base64
    
    # Build auth header
    hostname = credentials.get("hostname", "service5.ultipro.com")
    username = credentials.get("username", "")
    password = credentials.get("password", "")
    user_api_key = credentials.get("user_api_key", "")
    customer_api_key = credentials.get("customer_api_key", "")
    
    auth_string = f"{username}:{password}"
    auth_bytes = base64.b64encode(auth_string.encode()).decode()
    
    headers = {
        "Authorization": f"Basic {auth_bytes}",
        "US-Customer-Api-Key": customer_api_key,
        "Api-Key": user_api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    
    url = f"https://{hostname}{endpoint.path}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=60.0)
            
            if response.status_code != 200:
                return {
                    "endpoint_id": endpoint.id,
                    "success": False,
                    "error": f"API returned {response.status_code}",
                    "response": response.text[:500] if response.text else None
                }
            
            data = response.json()
            
            # Store in DuckDB
            row_count = await _store_in_duckdb(
                customer_id=customer_id,
                endpoint_id=endpoint.id,
                truth_bucket=endpoint.truth_bucket.value,
                data=data
            )
            
            return {
                "endpoint_id": endpoint.id,
                "success": True,
                "rows_imported": row_count,
                "truth_bucket": endpoint.truth_bucket.value,
                "table_name": f"{customer_id}_api_{endpoint.id}"
            }
            
        except Exception as e:
            return {
                "endpoint_id": endpoint.id,
                "success": False,
                "error": str(e)
            }


async def _store_in_duckdb(customer_id: str, endpoint_id: str, truth_bucket: str, data: Any) -> int:
    """
    Store API response data in DuckDB.
    """
    import duckdb
    import pandas as pd
    
    # Normalize data to list of records
    if isinstance(data, dict):
        # Check common wrapper patterns
        for key in ["items", "data", "results", "records", "employees", "workers"]:
            if key in data and isinstance(data[key], list):
                records = data[key]
                break
        else:
            records = [data]  # Single record
    elif isinstance(data, list):
        records = data
    else:
        records = [{"value": data}]
    
    if not records:
        return 0
    
    # Convert to DataFrame
    df = pd.DataFrame(records)
    
    # Build table name
    table_name = f"{customer_id}_api_{endpoint_id}"
    
    # Connect to project database
    db_path = f"/app/data/duckdb/{customer_id}.duckdb"
    
    try:
        conn = duckdb.connect(db_path)
        
        # Drop existing table and create new
        conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
        conn.register("temp_df", df)
        conn.execute(f'CREATE TABLE "{table_name}" AS SELECT * FROM temp_df')
        
        row_count = len(df)
        
        logger.info(f"[INTEGRATIONS] Stored {row_count} rows in {table_name} (bucket: {truth_bucket})")
        
        conn.close()
        
        return row_count
        
    except Exception as e:
        logger.error(f"[INTEGRATIONS] DuckDB storage failed: {e}")
        raise
