"""
UKG Pro RaaS Service - Report as a Service Integration
=======================================================

Handles:
- Authentication (OAuth + Web Services)
- Report discovery (GetReportList)
- Report parameter retrieval
- Report execution
- CSV/XML parsing

Deploy to: backend/services/ukg_pro_raas.py
"""

import os
import csv
import io
import base64
import logging
import httpx
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class UKGCredentials:
    """UKG Pro connection credentials."""
    base_url: str
    customer_api_key: str
    web_services_key: str
    username: str
    password: str
    access_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None


@dataclass
class ReportInfo:
    """Information about an available report."""
    path: str
    name: str
    description: str = ""
    owner: str = ""
    report_type: str = ""


@dataclass
class ReportParameter:
    """A parameter required by a report."""
    name: str
    display_name: str
    data_type: str  # String, Date, Integer, etc.
    required: bool = False
    default_value: Any = None
    allowed_values: List[str] = None


@dataclass
class ExecutionResult:
    """Result of executing a report."""
    success: bool
    row_count: int = 0
    columns: List[str] = None
    data: List[Dict] = None
    raw_content: str = None
    error: str = None
    execution_time_ms: int = 0


# =============================================================================
# UKG PRO RAAS CLIENT
# =============================================================================

class UKGProRaaSClient:
    """
    Client for UKG Pro Report as a Service (RaaS) API.
    
    Usage:
        client = UKGProRaaSClient(credentials)
        
        # Test connection
        if await client.test_connection():
            # List reports
            reports = await client.get_report_list()
            
            # Get report parameters
            params = await client.get_report_parameters(report_path)
            
            # Execute report
            result = await client.execute_report(report_path, {"AsOfDate": "2024-01-01"})
    """
    
    # RaaS SOAP endpoints
    RAAS_WSDL = "/services/BIDataService"
    
    # SOAP namespaces
    NAMESPACES = {
        'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
        'ns': 'http://www.ultipro.com/dataservices/bidata/2',
    }
    
    def __init__(self, credentials: UKGCredentials):
        self.credentials = credentials
        self.base_url = credentials.base_url.rstrip('/')
        
        # Ensure https
        if not self.base_url.startswith('http'):
            self.base_url = f"https://{self.base_url}"
        
        # HTTP client with reasonable timeouts
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, read=120.0),  # 2 min read timeout for large reports
            follow_redirects=True
        )
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    def _get_auth_header(self) -> str:
        """Build the Basic Auth header for RaaS."""
        # RaaS uses: CustomerApiKey + Username + Password encoded together
        # Format: US-{CustomerApiKey}-{WebServicesKey}:{Username}:{Password}
        auth_string = f"{self.credentials.username}:{self.credentials.password}"
        encoded = base64.b64encode(auth_string.encode()).decode()
        return f"Basic {encoded}"
    
    def _build_soap_envelope(self, body_content: str) -> str:
        """Build a SOAP envelope with the given body content."""
        return f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" 
               xmlns:ns="http://www.ultipro.com/dataservices/bidata/2">
    <soap:Header>
        <ns:ClientAccessKey>{self.credentials.customer_api_key}</ns:ClientAccessKey>
        <ns:UserAccessKey>{self.credentials.web_services_key}</ns:UserAccessKey>
    </soap:Header>
    <soap:Body>
        {body_content}
    </soap:Body>
</soap:Envelope>"""
    
    async def _soap_request(self, action: str, body: str) -> Tuple[bool, str]:
        """Make a SOAP request to the RaaS endpoint."""
        url = f"{self.base_url}{self.RAAS_WSDL}"
        
        headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': f'"http://www.ultipro.com/dataservices/bidata/2/IBIDataService/{action}"',
            'Authorization': self._get_auth_header(),
            'US-Customer-Api-Key': self.credentials.customer_api_key,
        }
        
        envelope = self._build_soap_envelope(body)
        
        try:
            logger.info(f"[RAAS] POST {url} Action={action}")
            response = await self.client.post(url, content=envelope, headers=headers)
            
            if response.status_code == 200:
                return True, response.text
            else:
                logger.error(f"[RAAS] Error {response.status_code}: {response.text[:500]}")
                return False, f"HTTP {response.status_code}: {response.text[:200]}"
                
        except Exception as e:
            logger.error(f"[RAAS] Request failed: {e}")
            return False, str(e)
    
    async def test_connection(self) -> Tuple[bool, str]:
        """
        Test the connection to UKG Pro RaaS.
        
        Returns:
            (success, message) tuple
        """
        try:
            # Try to get the report list - simplest test
            body = """<ns:GetReportList>
                <ns:request>
                    <ns:ReportPath>/content</ns:ReportPath>
                </ns:request>
            </ns:GetReportList>"""
            
            success, response = await self._soap_request("GetReportList", body)
            
            if success:
                # Check if we got a valid response
                if "GetReportListResponse" in response or "ReportPath" in response:
                    return True, "Connection successful"
                elif "Fault" in response or "Error" in response:
                    # Parse error from response
                    error = self._extract_soap_fault(response)
                    return False, f"Authentication failed: {error}"
                else:
                    return True, "Connection successful (empty report list)"
            else:
                return False, response
                
        except Exception as e:
            logger.error(f"[RAAS] Connection test failed: {e}")
            return False, str(e)
    
    def _extract_soap_fault(self, xml_response: str) -> str:
        """Extract error message from SOAP fault."""
        try:
            root = ET.fromstring(xml_response)
            # Look for faultstring
            for elem in root.iter():
                if 'faultstring' in elem.tag.lower():
                    return elem.text or "Unknown error"
                if 'message' in elem.tag.lower():
                    return elem.text or "Unknown error"
            return "Unknown SOAP fault"
        except:
            return xml_response[:200]
    
    async def get_report_list(self, path: str = "/content") -> List[ReportInfo]:
        """
        Get list of available reports.
        
        Args:
            path: Report folder path (default: /content for root)
            
        Returns:
            List of ReportInfo objects
        """
        body = f"""<ns:GetReportList>
            <ns:request>
                <ns:ReportPath>{path}</ns:ReportPath>
            </ns:request>
        </ns:GetReportList>"""
        
        success, response = await self._soap_request("GetReportList", body)
        
        if not success:
            logger.error(f"[RAAS] GetReportList failed: {response}")
            return []
        
        return self._parse_report_list(response)
    
    def _parse_report_list(self, xml_response: str) -> List[ReportInfo]:
        """Parse the GetReportList response."""
        reports = []
        
        try:
            root = ET.fromstring(xml_response)
            
            # Find all report entries
            for elem in root.iter():
                if 'ReportPath' in elem.tag or 'ReportName' in elem.tag:
                    # Found a report entry - look for siblings
                    parent = None
                    for p in root.iter():
                        if elem in list(p):
                            parent = p
                            break
                    
                    if parent is not None:
                        path = ""
                        name = ""
                        desc = ""
                        
                        for child in parent:
                            tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                            if tag == 'ReportPath':
                                path = child.text or ""
                            elif tag == 'ReportName':
                                name = child.text or ""
                            elif tag == 'ReportDescription':
                                desc = child.text or ""
                        
                        if path or name:
                            reports.append(ReportInfo(
                                path=path,
                                name=name or path.split('/')[-1],
                                description=desc
                            ))
            
            # Deduplicate
            seen = set()
            unique_reports = []
            for r in reports:
                key = r.path or r.name
                if key not in seen:
                    seen.add(key)
                    unique_reports.append(r)
            
            logger.info(f"[RAAS] Found {len(unique_reports)} reports")
            return unique_reports
            
        except Exception as e:
            logger.error(f"[RAAS] Failed to parse report list: {e}")
            return []
    
    async def get_report_parameters(self, report_path: str) -> List[ReportParameter]:
        """
        Get parameters required by a report.
        
        Args:
            report_path: Full path to the report
            
        Returns:
            List of ReportParameter objects
        """
        body = f"""<ns:GetReportParameters>
            <ns:request>
                <ns:ReportPath>{report_path}</ns:ReportPath>
            </ns:request>
        </ns:GetReportParameters>"""
        
        success, response = await self._soap_request("GetReportParameters", body)
        
        if not success:
            logger.error(f"[RAAS] GetReportParameters failed: {response}")
            return []
        
        return self._parse_report_parameters(response)
    
    def _parse_report_parameters(self, xml_response: str) -> List[ReportParameter]:
        """Parse the GetReportParameters response."""
        params = []
        
        try:
            root = ET.fromstring(xml_response)
            
            for elem in root.iter():
                tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                
                if tag == 'ReportParameter' or tag == 'Parameter':
                    name = ""
                    display = ""
                    data_type = "String"
                    required = False
                    default = None
                    
                    for child in elem:
                        child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                        if child_tag == 'Name':
                            name = child.text or ""
                        elif child_tag == 'DisplayName':
                            display = child.text or ""
                        elif child_tag == 'DataType':
                            data_type = child.text or "String"
                        elif child_tag == 'Required':
                            required = child.text and child.text.lower() == 'true'
                        elif child_tag == 'DefaultValue':
                            default = child.text
                    
                    if name:
                        params.append(ReportParameter(
                            name=name,
                            display_name=display or name,
                            data_type=data_type,
                            required=required,
                            default_value=default
                        ))
            
            logger.info(f"[RAAS] Found {len(params)} parameters")
            return params
            
        except Exception as e:
            logger.error(f"[RAAS] Failed to parse parameters: {e}")
            return []
    
    async def execute_report(
        self,
        report_path: str,
        parameters: Dict[str, Any] = None,
        output_format: str = "csv"
    ) -> ExecutionResult:
        """
        Execute a report and return the data.
        
        Args:
            report_path: Full path to the report
            parameters: Dict of parameter name -> value
            output_format: 'csv', 'xml', or 'json'
            
        Returns:
            ExecutionResult with parsed data
        """
        start_time = datetime.now()
        
        # Build parameters XML
        params_xml = ""
        if parameters:
            for name, value in parameters.items():
                params_xml += f"""
                <ns:ReportParameter>
                    <ns:Name>{name}</ns:Name>
                    <ns:Value>{value}</ns:Value>
                </ns:ReportParameter>"""
        
        # Determine delimiter for output
        delimiter = "," if output_format == "csv" else ""
        
        body = f"""<ns:ExecuteReport>
            <ns:request>
                <ns:ReportPath>{report_path}</ns:ReportPath>
                <ns:ReportParameters>{params_xml}
                </ns:ReportParameters>
                <ns:Delimiter>{delimiter}</ns:Delimiter>
            </ns:request>
        </ns:ExecuteReport>"""
        
        success, response = await self._soap_request("ExecuteReport", body)
        
        execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        if not success:
            return ExecutionResult(
                success=False,
                error=response,
                execution_time_ms=execution_time
            )
        
        # Parse the response based on format
        if output_format == "csv":
            return self._parse_csv_response(response, execution_time)
        else:
            return self._parse_xml_response(response, execution_time)
    
    def _parse_csv_response(self, xml_response: str, execution_time: int) -> ExecutionResult:
        """Parse CSV data from ExecuteReport response."""
        try:
            root = ET.fromstring(xml_response)
            
            # Find the report content (usually base64 encoded or raw CSV)
            content = None
            
            for elem in root.iter():
                tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if tag in ['ReportOutput', 'ReportData', 'Content', 'ReportStream']:
                    content = elem.text
                    break
            
            if not content:
                # Try to find any element with CSV-like content
                for elem in root.iter():
                    if elem.text and ',' in elem.text and '\n' in elem.text:
                        content = elem.text
                        break
            
            if not content:
                return ExecutionResult(
                    success=False,
                    error="No report content found in response",
                    execution_time_ms=execution_time
                )
            
            # Try to decode if base64
            try:
                decoded = base64.b64decode(content).decode('utf-8')
                content = decoded
            except:
                pass  # Not base64, use as-is
            
            # Parse CSV
            reader = csv.DictReader(io.StringIO(content))
            rows = list(reader)
            columns = reader.fieldnames or []
            
            logger.info(f"[RAAS] Parsed {len(rows)} rows, {len(columns)} columns")
            
            return ExecutionResult(
                success=True,
                row_count=len(rows),
                columns=columns,
                data=rows,
                raw_content=content,
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            logger.error(f"[RAAS] Failed to parse CSV response: {e}")
            return ExecutionResult(
                success=False,
                error=f"Parse error: {str(e)}",
                execution_time_ms=execution_time
            )
    
    def _parse_xml_response(self, xml_response: str, execution_time: int) -> ExecutionResult:
        """Parse XML data from ExecuteReport response."""
        try:
            root = ET.fromstring(xml_response)
            
            # Find data rows
            rows = []
            columns = set()
            
            for elem in root.iter():
                tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if tag in ['Row', 'Record', 'DataRow']:
                    row = {}
                    for child in elem:
                        child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                        row[child_tag] = child.text
                        columns.add(child_tag)
                    if row:
                        rows.append(row)
            
            return ExecutionResult(
                success=True,
                row_count=len(rows),
                columns=list(columns),
                data=rows,
                raw_content=xml_response,
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            logger.error(f"[RAAS] Failed to parse XML response: {e}")
            return ExecutionResult(
                success=False,
                error=f"Parse error: {str(e)}",
                execution_time_ms=execution_time
            )


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def test_ukg_connection(
    base_url: str,
    customer_api_key: str,
    web_services_key: str,
    username: str,
    password: str
) -> Tuple[bool, str]:
    """
    Test a UKG Pro connection with the given credentials.
    
    Returns:
        (success, message) tuple
    """
    credentials = UKGCredentials(
        base_url=base_url,
        customer_api_key=customer_api_key,
        web_services_key=web_services_key,
        username=username,
        password=password
    )
    
    client = UKGProRaaSClient(credentials)
    try:
        return await client.test_connection()
    finally:
        await client.close()


async def execute_ukg_report(
    credentials: UKGCredentials,
    report_path: str,
    parameters: Dict[str, Any] = None
) -> ExecutionResult:
    """
    Execute a UKG Pro report and return the data.
    """
    client = UKGProRaaSClient(credentials)
    try:
        return await client.execute_report(report_path, parameters)
    finally:
        await client.close()
