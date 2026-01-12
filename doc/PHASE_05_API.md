# Phase 5: API Connectivity

**Status:** NOT STARTED  
**Total Estimated Hours:** 8-12  
**Dependencies:** Core engine complete (Phases 1-4)  
**Last Updated:** January 11, 2026

---

## Objective

Pull live data from customer UKG instances instead of relying solely on uploaded files. This transforms XLR8 from "analyze what you upload" to "connect and analyze live."

---

## Background

### Current State

Data acquisition is manual:
1. Customer exports data from UKG
2. Customer uploads files to XLR8
3. XLR8 processes and analyzes

Limitations:
- Data staleness (days/weeks old)
- Manual effort required
- Export format variations
- Missing real-time insights

### Target State

Direct API integration:
1. Customer connects UKG credentials
2. XLR8 pulls data directly via API
3. Real-time or scheduled refresh
4. Consistent data format

Benefits:
- Current data always
- Reduced customer effort
- Standardized ingestion
- Scheduled analysis runs

---

## Component Overview

| # | Component | Hours | Description |
|---|-----------|-------|-------------|
| 5.1 | Credential Management | 2-3 | Secure storage and handling |
| 5.2 | UKG Pro RaaS Connector | 3-4 | Reports-as-a-Service integration |
| 5.3 | UKG WFM Connector | 2-3 | Workforce Management API |
| 5.4 | UKG Ready Connector | 1-2 | Ready/Kronos API |

---

## UKG API Landscape

### UKG Pro APIs

| API | Type | Use Case |
|-----|------|----------|
| RaaS (Reports as a Service) | SOAP/REST | Pre-built reports, bulk data |
| Foundation API | REST | Core HR data, employees |
| Time Management | REST | Timesheets, schedules |
| Benefits | REST | Enrollment, deductions |

### UKG WFM (Dimensions) APIs

| API | Type | Use Case |
|-----|------|----------|
| Data API | REST | Timecards, schedules |
| People API | REST | Employee records |
| Reporting API | REST | Ad-hoc queries |

### UKG Ready APIs

| API | Type | Use Case |
|-----|------|----------|
| Core API | REST | HR, Payroll, Time |
| Reporting | REST | Standard reports |

---

## Component 5.1: Credential Management

**Goal:** Securely store and use API credentials.

### Credential Model

```python
@dataclass
class UKGCredentials:
    """UKG API credentials."""
    credential_id: str           # Our internal ID
    project_id: str              # Associated XLR8 project
    platform: str                # 'pro', 'wfm', 'ready'
    
    # Connection details
    api_endpoint: str            # Customer's UKG URL
    username: str                # API username
    api_key: str                 # Encrypted API key
    company_short_name: str      # UKG company identifier
    
    # OAuth tokens (if applicable)
    access_token: Optional[str]
    refresh_token: Optional[str]
    token_expires: Optional[datetime]
    
    # Status
    is_valid: bool
    last_tested: datetime
    last_error: Optional[str]
    
    # Audit
    created_at: datetime
    created_by: str
    updated_at: datetime
```

### Secure Storage

```python
class CredentialStore:
    """Secure credential storage using Supabase."""
    
    def __init__(self, supabase_client):
        self.client = supabase_client
        self.encryption_key = os.environ['CREDENTIAL_ENCRYPTION_KEY']
    
    def store_credential(self, cred: UKGCredentials) -> str:
        """Store credential with encryption."""
        encrypted = {
            'credential_id': cred.credential_id,
            'project_id': cred.project_id,
            'platform': cred.platform,
            'api_endpoint': cred.api_endpoint,
            'username': cred.username,
            'api_key': self._encrypt(cred.api_key),
            'company_short_name': cred.company_short_name,
            'access_token': self._encrypt(cred.access_token) if cred.access_token else None,
            'refresh_token': self._encrypt(cred.refresh_token) if cred.refresh_token else None,
            'token_expires': cred.token_expires.isoformat() if cred.token_expires else None,
            'is_valid': cred.is_valid,
            'last_tested': cred.last_tested.isoformat(),
            'created_at': datetime.utcnow().isoformat(),
        }
        
        result = self.client.table('ukg_credentials').insert(encrypted).execute()
        return result.data[0]['credential_id']
    
    def get_credential(self, credential_id: str) -> UKGCredentials:
        """Retrieve and decrypt credential."""
        result = self.client.table('ukg_credentials')\
            .select('*')\
            .eq('credential_id', credential_id)\
            .single()\
            .execute()
        
        data = result.data
        return UKGCredentials(
            credential_id=data['credential_id'],
            project_id=data['project_id'],
            platform=data['platform'],
            api_endpoint=data['api_endpoint'],
            username=data['username'],
            api_key=self._decrypt(data['api_key']),
            company_short_name=data['company_short_name'],
            access_token=self._decrypt(data['access_token']) if data['access_token'] else None,
            refresh_token=self._decrypt(data['refresh_token']) if data['refresh_token'] else None,
            token_expires=datetime.fromisoformat(data['token_expires']) if data['token_expires'] else None,
            is_valid=data['is_valid'],
            last_tested=datetime.fromisoformat(data['last_tested']),
            last_error=data.get('last_error'),
            created_at=datetime.fromisoformat(data['created_at']),
            created_by=data.get('created_by', ''),
            updated_at=datetime.fromisoformat(data.get('updated_at', data['created_at']))
        )
    
    def _encrypt(self, value: str) -> str:
        """Encrypt sensitive value."""
        if not value:
            return None
        from cryptography.fernet import Fernet
        f = Fernet(self.encryption_key)
        return f.encrypt(value.encode()).decode()
    
    def _decrypt(self, value: str) -> str:
        """Decrypt sensitive value."""
        if not value:
            return None
        from cryptography.fernet import Fernet
        f = Fernet(self.encryption_key)
        return f.decrypt(value.encode()).decode()
```

### Connection Testing

```python
class ConnectionTester:
    """Test API credentials before storing."""
    
    async def test_connection(self, cred: UKGCredentials) -> Dict:
        """
        Test credentials against UKG API.
        
        Returns:
            {'valid': bool, 'error': str or None, 'details': dict}
        """
        connector = self._get_connector(cred.platform)
        
        try:
            result = await connector.test_auth(
                endpoint=cred.api_endpoint,
                username=cred.username,
                api_key=cred.api_key,
                company=cred.company_short_name
            )
            
            if result['success']:
                return {
                    'valid': True,
                    'error': None,
                    'details': {
                        'company_name': result.get('company_name'),
                        'api_version': result.get('version'),
                        'available_reports': result.get('reports', [])
                    }
                }
            else:
                return {
                    'valid': False,
                    'error': result.get('error', 'Authentication failed'),
                    'details': {}
                }
                
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'details': {}
            }
```

---

## Component 5.2: UKG Pro RaaS Connector

**Goal:** Pull reports from UKG Pro via Reports-as-a-Service.

### RaaS Overview

UKG Pro RaaS provides:
- Pre-built standard reports
- Custom reports (BI Publisher)
- Bulk data extraction
- SOAP or REST interface

### Standard Reports Available

| Report Name | Data Contents | Use Case |
|-------------|---------------|----------|
| Employee Demographics | Basic HR data | Headcount, status |
| Compensation Summary | Pay rates, salaries | Compensation analysis |
| Deduction Register | Active deductions | Benefits analysis |
| Tax Setup | Tax configurations | Tax compliance |
| Earnings Summary | YTD earnings | Payroll analysis |
| Org Hierarchy | Company structure | Org analysis |

### RaaS Connector Implementation

```python
class UKGProRaaSConnector:
    """Connect to UKG Pro via Reports-as-a-Service."""
    
    RAAS_ENDPOINTS = {
        'prod': 'https://service4.ultipro.com/services/BIDataService',
        'test': 'https://service4.ultipro.com/services/BIDataService',
    }
    
    def __init__(self, credentials: UKGCredentials):
        self.credentials = credentials
        self.endpoint = credentials.api_endpoint or self.RAAS_ENDPOINTS['prod']
    
    async def test_auth(self, **kwargs) -> Dict:
        """Test authentication."""
        try:
            # Make a simple API call to verify credentials
            reports = await self.list_reports()
            return {
                'success': True,
                'reports': [r['name'] for r in reports],
                'version': 'RaaS v2'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def list_reports(self) -> List[Dict]:
        """List available reports."""
        # SOAP request to get report catalog
        soap_body = self._build_list_reports_request()
        response = await self._soap_request(soap_body)
        return self._parse_report_list(response)
    
    async def execute_report(self, 
                            report_path: str,
                            parameters: Dict = None) -> Dict:
        """
        Execute a RaaS report.
        
        Args:
            report_path: UKG report path (e.g., '/content/folder/Reports/ReportName')
            parameters: Report parameters (dates, company codes, etc.)
            
        Returns:
            Dict with 'data' (list of dicts) and 'metadata'
        """
        soap_body = self._build_execute_request(report_path, parameters)
        response = await self._soap_request(soap_body)
        
        # Parse response
        data = self._parse_report_data(response)
        
        return {
            'report_path': report_path,
            'row_count': len(data),
            'data': data,
            'executed_at': datetime.utcnow().isoformat(),
            'parameters': parameters
        }
    
    async def pull_employee_demographics(self) -> Dict:
        """Pull standard employee demographics report."""
        return await self.execute_report(
            report_path='/content/folder/Reports/Standard/Employee Demographics',
            parameters={
                'companyCode': self.credentials.company_short_name,
                'asOfDate': datetime.now().strftime('%Y-%m-%d')
            }
        )
    
    async def pull_deductions(self) -> Dict:
        """Pull deduction data."""
        return await self.execute_report(
            report_path='/content/folder/Reports/Standard/Deduction Register',
            parameters={
                'companyCode': self.credentials.company_short_name
            }
        )
    
    async def pull_earnings(self, year: int = None) -> Dict:
        """Pull earnings data."""
        year = year or datetime.now().year
        return await self.execute_report(
            report_path='/content/folder/Reports/Standard/Earnings Summary',
            parameters={
                'companyCode': self.credentials.company_short_name,
                'year': year
            }
        )
    
    def _build_soap_headers(self) -> str:
        """Build SOAP authentication headers."""
        return f"""
        <wsse:Security>
            <wsse:UsernameToken>
                <wsse:Username>{self.credentials.username}</wsse:Username>
                <wsse:Password>{self.credentials.api_key}</wsse:Password>
            </wsse:UsernameToken>
        </wsse:Security>
        """
    
    async def _soap_request(self, body: str) -> str:
        """Make SOAP request to RaaS."""
        import aiohttp
        
        headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': 'http://www.ultipro.com/services/bidata/ExecuteReport'
        }
        
        envelope = f"""<?xml version="1.0" encoding="utf-8"?>
        <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
            <soap:Header>
                {self._build_soap_headers()}
            </soap:Header>
            <soap:Body>
                {body}
            </soap:Body>
        </soap:Envelope>
        """
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.endpoint,
                data=envelope,
                headers=headers
            ) as response:
                return await response.text()
```

### Data Normalization

```python
class RaaSDataNormalizer:
    """Normalize RaaS data to XLR8 format."""
    
    COLUMN_MAPPINGS = {
        'EmployeeNumber': 'employee_number',
        'FirstName': 'first_name',
        'LastName': 'last_name',
        'StateProvince': 'state_province',
        'EmployeeStatus': 'employee_status',
        'HireDate': 'hire_date',
        'TerminationDate': 'termination_date',
        # ... more mappings
    }
    
    def normalize(self, raas_data: List[Dict], report_type: str) -> List[Dict]:
        """Normalize RaaS data to standard format."""
        normalized = []
        
        for row in raas_data:
            norm_row = {}
            for raas_col, value in row.items():
                # Map column name
                norm_col = self.COLUMN_MAPPINGS.get(raas_col, raas_col.lower())
                
                # Normalize value
                norm_value = self._normalize_value(norm_col, value)
                
                norm_row[norm_col] = norm_value
            
            normalized.append(norm_row)
        
        return normalized
    
    def _normalize_value(self, column: str, value: Any) -> Any:
        """Normalize value based on column type."""
        if value is None:
            return None
        
        # Date columns
        if column.endswith('_date') or column in ('hire_date', 'termination_date'):
            return self._parse_date(value)
        
        # Status columns - uppercase
        if 'status' in column:
            return str(value).upper()
        
        # State columns - uppercase 2-letter
        if column in ('state_province', 'state', 'work_state'):
            return self._normalize_state(value)
        
        return value
```

---

## Component 5.3: UKG WFM Connector

**Goal:** Pull time and attendance data from UKG Dimensions (WFM).

### WFM API Overview

```python
class UKGWFMConnector:
    """Connect to UKG Workforce Management (Dimensions)."""
    
    def __init__(self, credentials: UKGCredentials):
        self.credentials = credentials
        self.base_url = credentials.api_endpoint  # e.g., https://company.prd.mykronos.com
        self.access_token = None
    
    async def authenticate(self):
        """Get OAuth2 token."""
        auth_url = f"{self.base_url}/api/authentication/access_token"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(auth_url, json={
                'username': self.credentials.username,
                'password': self.credentials.api_key
            }) as response:
                data = await response.json()
                self.access_token = data['access_token']
                return self.access_token
    
    async def get_employees(self) -> List[Dict]:
        """Get employee list."""
        await self._ensure_authenticated()
        
        url = f"{self.base_url}/api/v1/commons/persons"
        headers = {'Authorization': f'Bearer {self.access_token}'}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                return await response.json()
    
    async def get_timecards(self, 
                           start_date: date,
                           end_date: date) -> List[Dict]:
        """Get timecard data for date range."""
        await self._ensure_authenticated()
        
        url = f"{self.base_url}/api/v1/timekeeping/timecards"
        headers = {'Authorization': f'Bearer {self.access_token}'}
        params = {
            'startDate': start_date.isoformat(),
            'endDate': end_date.isoformat()
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                return await response.json()
    
    async def get_schedules(self,
                           start_date: date,
                           end_date: date) -> List[Dict]:
        """Get schedule data."""
        await self._ensure_authenticated()
        
        url = f"{self.base_url}/api/v1/scheduling/schedule"
        headers = {'Authorization': f'Bearer {self.access_token}'}
        params = {
            'startDate': start_date.isoformat(),
            'endDate': end_date.isoformat()
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                return await response.json()
```

---

## Component 5.4: UKG Ready Connector

**Goal:** Pull HR and payroll data from UKG Ready.

```python
class UKGReadyConnector:
    """Connect to UKG Ready (formerly Kronos Workforce Ready)."""
    
    def __init__(self, credentials: UKGCredentials):
        self.credentials = credentials
        self.base_url = 'https://secure.saashr.com/ta/rest/v1'
    
    async def authenticate(self) -> str:
        """Get API session token."""
        auth_url = f"{self.base_url}/login"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(auth_url, json={
                'credentials': {
                    'username': self.credentials.username,
                    'password': self.credentials.api_key,
                    'company': self.credentials.company_short_name
                }
            }) as response:
                data = await response.json()
                return data['token']
    
    async def get_employees(self, token: str) -> List[Dict]:
        """Get employee data."""
        url = f"{self.base_url}/company/{self.credentials.company_short_name}/employees"
        headers = {'Authentication': f'Bearer {token}'}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                return await response.json()
    
    async def get_payroll_summary(self, 
                                  token: str,
                                  pay_period: str) -> List[Dict]:
        """Get payroll summary for period."""
        url = f"{self.base_url}/company/{self.credentials.company_short_name}/payroll/{pay_period}"
        headers = {'Authentication': f'Bearer {token}'}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                return await response.json()
```

---

## API Data Integration Flow

```python
class APIDataIntegrator:
    """Integrate API data into XLR8 pipeline."""
    
    async def sync_from_api(self, 
                           project_id: str,
                           credential_id: str) -> Dict:
        """
        Pull data from UKG API and load into XLR8.
        
        Returns:
            {'tables_updated': [...], 'rows_loaded': {...}, 'errors': [...]}
        """
        # Get credentials
        cred = self.credential_store.get_credential(credential_id)
        
        # Get appropriate connector
        connector = self._get_connector(cred.platform, cred)
        
        # Pull data by type
        results = {
            'tables_updated': [],
            'rows_loaded': {},
            'errors': []
        }
        
        # Pull demographics
        try:
            demographics = await connector.pull_employee_demographics()
            normalized = self.normalizer.normalize(demographics['data'], 'demographics')
            self._load_to_duckdb(project_id, 'api_employees', normalized)
            results['tables_updated'].append('api_employees')
            results['rows_loaded']['api_employees'] = len(normalized)
        except Exception as e:
            results['errors'].append(f"Demographics: {e}")
        
        # Pull deductions
        try:
            deductions = await connector.pull_deductions()
            normalized = self.normalizer.normalize(deductions['data'], 'deductions')
            self._load_to_duckdb(project_id, 'api_deductions', normalized)
            results['tables_updated'].append('api_deductions')
            results['rows_loaded']['api_deductions'] = len(normalized)
        except Exception as e:
            results['errors'].append(f"Deductions: {e}")
        
        # Trigger re-profiling
        await self.trigger_reprofile(project_id)
        
        return results
```

---

## Scheduling

```python
class APISyncScheduler:
    """Schedule periodic API syncs."""
    
    async def setup_schedule(self,
                            project_id: str,
                            credential_id: str,
                            frequency: str = 'daily') -> str:
        """
        Set up scheduled API sync.
        
        Args:
            frequency: 'hourly', 'daily', 'weekly'
        """
        schedule_id = str(uuid.uuid4())
        
        schedule = {
            'schedule_id': schedule_id,
            'project_id': project_id,
            'credential_id': credential_id,
            'frequency': frequency,
            'next_run': self._calculate_next_run(frequency),
            'is_active': True,
            'created_at': datetime.utcnow().isoformat()
        }
        
        await self.store_schedule(schedule)
        
        return schedule_id
    
    async def run_scheduled_syncs(self):
        """Run all due scheduled syncs (called by cron)."""
        due_schedules = await self.get_due_schedules()
        
        for schedule in due_schedules:
            try:
                integrator = APIDataIntegrator()
                result = await integrator.sync_from_api(
                    schedule['project_id'],
                    schedule['credential_id']
                )
                
                await self.record_sync_result(schedule['schedule_id'], result)
                await self.update_next_run(schedule['schedule_id'])
                
            except Exception as e:
                await self.record_sync_error(schedule['schedule_id'], str(e))
```

---

## Security Considerations

### Credential Security
- API keys encrypted at rest (Fernet)
- Tokens never logged
- Short-lived access tokens where possible
- Credential rotation reminders

### API Security
- HTTPS only
- Request signing where supported
- Rate limiting respected
- Audit logging of all API calls

### Data Security
- API data tagged with source
- Clear provenance tracking
- Refresh timestamps visible
- User consent for API access

---

## Testing Strategy

### Unit Tests
- Credential encryption/decryption
- Data normalization
- SOAP message building
- OAuth flow

### Integration Tests
- UKG sandbox connections
- Report execution
- Data normalization
- Error handling

### Mock Testing
- Mock UKG responses
- Error condition simulation
- Rate limit handling

---

## Success Criteria

### Phase Complete When:
1. Credentials stored securely
2. UKG Pro RaaS connector working
3. WFM connector working (if needed)
4. Ready connector working (if needed)
5. Scheduled sync operational

### Quality Gates:
- Zero credential exposure in logs
- 95%+ sync success rate
- Data matches manual exports
- Sub-5min full sync time

---

## Version History

| Date | Change |
|------|--------|
| 2026-01-11 | Initial detailed phase doc created |
