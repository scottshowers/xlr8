# Phase 6: API Connectivity

**Goal:** Pull live data from customer instances across multiple enterprise products.

**Status:** NOT STARTED  
**Estimated Hours:** 18-25  
**Prerequisites:** Phase 5 (Multi-Product Schemas) must be complete

---

## Component Overview

| # | Component | Hours | Status | Description |
|---|-----------|-------|--------|-------------|
| 6.1 | Credential Management | 2-3 | NOT STARTED | Secure multi-product credential storage |
| 6.2 | Connector Framework | 3-4 | NOT STARTED | Abstract connector interface |
| 6.3 | UKG Connectors | 3-4 | NOT STARTED | Pro RaaS, WFM, Ready |
| 6.4 | Workday Connector | 3-4 | NOT STARTED | HCM and Financials |
| 6.5 | SAP Connectors | 3-4 | NOT STARTED | SuccessFactors, S/4HANA |
| 6.6 | Salesforce Connector | 2-3 | NOT STARTED | CRM |
| 6.7 | Oracle Connectors | 2-3 | NOT STARTED | HCM Cloud, ERP Cloud |

---

## Component 6.1: Credential Management

**Goal:** Secure storage and retrieval of API credentials for multiple products.

### Credential Types

| Auth Type | Products | Required Fields |
|-----------|----------|-----------------|
| OAuth 2.0 | Workday, Salesforce | client_id, client_secret, token_url, refresh_token |
| API Key | Various | api_key, api_secret |
| Basic Auth | Legacy systems | username, password |
| Certificate | SAP | cert_file, key_file, passphrase |
| RaaS Token | UKG Pro | api_key, username, password, customer_api_key |

### Credential Structure

```python
@dataclass
class ProductCredential:
    """Credentials for a product instance."""
    credential_id: str
    project_id: str            # XLR8 project
    product_id: str            # From Product Registry
    instance_url: str          # Customer's instance URL
    
    auth_type: str             # oauth2, api_key, basic, certificate, raas
    
    # Encrypted storage
    credentials: Dict[str, str]  # Encrypted credential fields
    
    # Metadata
    created_at: datetime
    expires_at: Optional[datetime]
    last_used: Optional[datetime]
    status: str                # active, expired, revoked
```

### Credential Manager

```python
class CredentialManager:
    """Secure credential storage and retrieval."""
    
    def store_credential(self, credential: ProductCredential) -> str:
        """Store encrypted credential, return credential_id."""
        pass
    
    def get_credential(self, credential_id: str) -> ProductCredential:
        """Retrieve and decrypt credential."""
        pass
    
    def refresh_token(self, credential_id: str) -> ProductCredential:
        """Refresh OAuth token if needed."""
        pass
    
    def list_credentials(self, project_id: str) -> List[ProductCredential]:
        """List all credentials for a project."""
        pass
    
    def revoke_credential(self, credential_id: str):
        """Revoke and delete a credential."""
        pass
```

### Security Requirements

- All credentials encrypted at rest (AES-256)
- Encryption key from environment variable or secrets manager
- No credentials in logs
- Automatic token refresh for OAuth
- Credential rotation support

---

## Component 6.2: Connector Framework

**Goal:** Abstract interface for connecting to any enterprise product.

### Connector Interface

```python
from abc import ABC, abstractmethod

class BaseConnector(ABC):
    """Abstract base class for all product connectors."""
    
    def __init__(self, credential: ProductCredential, schema: ProductSchema):
        self.credential = credential
        self.schema = schema
        self.session = None
    
    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to the product."""
        pass
    
    @abstractmethod
    def disconnect(self):
        """Close connection."""
        pass
    
    @abstractmethod
    def test_connection(self) -> Dict:
        """Test connection and return status."""
        pass
    
    @abstractmethod
    def get_entity(self, entity: str, filters: Dict = None) -> List[Dict]:
        """Retrieve entity data with optional filters."""
        pass
    
    @abstractmethod
    def get_entity_schema(self, entity: str) -> Dict:
        """Get schema/metadata for an entity."""
        pass
    
    @abstractmethod
    def execute_query(self, query: str) -> List[Dict]:
        """Execute a product-specific query."""
        pass
    
    # Optional methods
    def bulk_export(self, entity: str, filters: Dict = None) -> str:
        """Start bulk export job, return job ID."""
        raise NotImplementedError("Bulk export not supported")
    
    def get_bulk_status(self, job_id: str) -> Dict:
        """Check bulk export job status."""
        raise NotImplementedError("Bulk export not supported")
```

### Connector Factory

```python
class ConnectorFactory:
    """Factory for creating product connectors."""
    
    CONNECTOR_MAP = {
        'ukg_pro': UKGProConnector,
        'ukg_wfm': UKGWFMConnector,
        'ukg_ready': UKGReadyConnector,
        'workday_hcm': WorkdayConnector,
        'workday_fins': WorkdayConnector,
        'salesforce': SalesforceConnector,
        'sap_sf': SAPSuccessFactorsConnector,
        'sap_s4': SAPS4HANAConnector,
        'oracle_hcm': OracleHCMConnector,
        'oracle_erp': OracleERPConnector,
    }
    
    @classmethod
    def create(cls, product_id: str, credential: ProductCredential, 
               schema: ProductSchema) -> BaseConnector:
        """Create appropriate connector for product."""
        connector_class = cls.CONNECTOR_MAP.get(product_id)
        if not connector_class:
            raise ValueError(f"No connector available for {product_id}")
        return connector_class(credential, schema)
```

### Query Translation

```python
class QueryTranslator:
    """Translate universal queries to product-specific queries."""
    
    def translate(self, 
                  universal_query: str,
                  source_product: str,
                  target_product: str) -> str:
        """
        Translate a query from one product's terminology to another.
        Uses vocabulary normalization from Phase 5.
        """
        pass
    
    def translate_filters(self, 
                          filters: Dict,
                          target_product: str) -> Dict:
        """Translate filter field names and values."""
        pass
```

---

## Component 6.3: UKG Connectors

**Goal:** Connect to UKG Pro, WFM, and Ready instances.

### UKG Pro (RaaS)

```python
class UKGProConnector(BaseConnector):
    """Connector for UKG Pro using Report-as-a-Service (RaaS)."""
    
    BASE_URL = "https://service4.ultipro.com"
    
    def connect(self) -> bool:
        """Authenticate with UKG Pro."""
        # Use BI token authentication
        pass
    
    def execute_raas_report(self, report_path: str, params: Dict = None) -> List[Dict]:
        """Execute a RaaS report."""
        pass
    
    def list_available_reports(self) -> List[str]:
        """List reports available to this credential."""
        pass
    
    # Standard reports
    def get_employees(self, filters: Dict = None) -> List[Dict]:
        """Get employee data via standard report."""
        pass
    
    def get_earnings(self, pay_period: str) -> List[Dict]:
        """Get earnings data for a pay period."""
        pass
```

### UKG WFM (Dimensions)

```python
class UKGWFMConnector(BaseConnector):
    """Connector for UKG Workforce Management (Dimensions)."""
    
    def connect(self) -> bool:
        """Authenticate with UKG WFM API."""
        pass
    
    def get_timecards(self, date_range: Tuple[date, date]) -> List[Dict]:
        """Get timecard data."""
        pass
    
    def get_schedules(self, date_range: Tuple[date, date]) -> List[Dict]:
        """Get schedule data."""
        pass
    
    def get_accruals(self, as_of_date: date = None) -> List[Dict]:
        """Get accrual balances."""
        pass
```

### UKG Ready

```python
class UKGReadyConnector(BaseConnector):
    """Connector for UKG Ready (formerly Kronos Workforce Ready)."""
    
    def connect(self) -> bool:
        """Authenticate with UKG Ready API."""
        pass
    
    def get_entity(self, entity: str, filters: Dict = None) -> List[Dict]:
        """Generic entity retrieval."""
        pass
```

---

## Component 6.4: Workday Connector

**Goal:** Connect to Workday HCM and Financials.

### Workday API Types

| API | Use Case |
|-----|----------|
| REST API | Modern integration, JSON-based |
| SOAP API | Legacy, full functionality |
| RaaS | Report-as-a-Service for bulk data |
| Prism Analytics | Advanced analytics data |

### Implementation

```python
class WorkdayConnector(BaseConnector):
    """Connector for Workday HCM and Financials."""
    
    def connect(self) -> bool:
        """Authenticate with Workday (OAuth 2.0)."""
        pass
    
    def get_workers(self, filters: Dict = None) -> List[Dict]:
        """Get worker data."""
        pass
    
    def get_organizations(self) -> List[Dict]:
        """Get organization hierarchy."""
        pass
    
    def execute_report(self, report_name: str, params: Dict = None) -> List[Dict]:
        """Execute a Workday report."""
        pass
    
    # Financials-specific
    def get_journal_entries(self, date_range: Tuple[date, date]) -> List[Dict]:
        """Get journal entries (Financials)."""
        pass
    
    def get_suppliers(self) -> List[Dict]:
        """Get supplier master data (Financials)."""
        pass
```

---

## Component 6.5: SAP Connectors

**Goal:** Connect to SAP SuccessFactors and S/4HANA.

### SAP SuccessFactors

```python
class SAPSuccessFactorsConnector(BaseConnector):
    """Connector for SAP SuccessFactors."""
    
    def connect(self) -> bool:
        """Authenticate with SuccessFactors (OAuth or Basic)."""
        pass
    
    def get_entity(self, entity: str, filters: Dict = None) -> List[Dict]:
        """OData entity retrieval."""
        pass
    
    def get_employees(self, filters: Dict = None) -> List[Dict]:
        """Get employee data from Employee Central."""
        pass
```

### SAP S/4HANA

```python
class SAPS4HANAConnector(BaseConnector):
    """Connector for SAP S/4HANA."""
    
    def connect(self) -> bool:
        """Authenticate with S/4HANA."""
        pass
    
    def execute_bapi(self, bapi_name: str, params: Dict) -> Dict:
        """Execute a BAPI function."""
        pass
    
    def get_entity(self, entity: str, filters: Dict = None) -> List[Dict]:
        """OData entity retrieval."""
        pass
```

---

## Component 6.6: Salesforce Connector

**Goal:** Connect to Salesforce CRM.

```python
class SalesforceConnector(BaseConnector):
    """Connector for Salesforce CRM."""
    
    def connect(self) -> bool:
        """Authenticate with Salesforce (OAuth 2.0)."""
        pass
    
    def execute_soql(self, query: str) -> List[Dict]:
        """Execute a SOQL query."""
        pass
    
    def get_entity(self, entity: str, filters: Dict = None) -> List[Dict]:
        """Get standard or custom object data."""
        pass
    
    def bulk_query(self, query: str) -> str:
        """Start bulk API query job."""
        pass
    
    # Common entities
    def get_accounts(self, filters: Dict = None) -> List[Dict]:
        pass
    
    def get_contacts(self, filters: Dict = None) -> List[Dict]:
        pass
    
    def get_opportunities(self, filters: Dict = None) -> List[Dict]:
        pass
```

---

## Component 6.7: Oracle Connectors

**Goal:** Connect to Oracle HCM Cloud and ERP Cloud.

```python
class OracleHCMConnector(BaseConnector):
    """Connector for Oracle HCM Cloud."""
    
    def connect(self) -> bool:
        """Authenticate with Oracle HCM Cloud."""
        pass
    
    def get_entity(self, entity: str, filters: Dict = None) -> List[Dict]:
        """REST API entity retrieval."""
        pass
    
    def execute_hcm_extract(self, extract_name: str) -> str:
        """Run HCM Extract job."""
        pass


class OracleERPConnector(BaseConnector):
    """Connector for Oracle ERP Cloud."""
    
    def connect(self) -> bool:
        """Authenticate with Oracle ERP Cloud."""
        pass
    
    def get_entity(self, entity: str, filters: Dict = None) -> List[Dict]:
        """REST API entity retrieval."""
        pass
```

---

## Integration with Intelligence Engine

### Live Data Gathering

```python
class LiveDataGatherer:
    """Gather live data from connected products."""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.credentials = CredentialManager().list_credentials(project_id)
    
    def gather(self, question: str, analysis: Dict) -> List[Truth]:
        """
        Gather live data relevant to the question.
        
        1. Detect which products are relevant
        2. Create connectors for those products
        3. Execute queries
        4. Return as Truth objects
        """
        pass
```

### Adding to Five Truths

| Truth Type | Live Data Source |
|------------|------------------|
| Reality | Live query results from connected products |
| Configuration | Live config table data |

---

## File Structure

```
/backend/utils/connectors/
├── __init__.py
├── base.py                # 6.2 - BaseConnector, ConnectorFactory
├── credentials.py         # 6.1 - CredentialManager
├── query_translator.py    # Query translation
├── ukg/
│   ├── __init__.py
│   ├── pro.py             # 6.3 - UKG Pro RaaS
│   ├── wfm.py             # 6.3 - UKG WFM
│   └── ready.py           # 6.3 - UKG Ready
├── workday/
│   ├── __init__.py
│   └── connector.py       # 6.4 - Workday HCM/FINS
├── sap/
│   ├── __init__.py
│   ├── successfactors.py  # 6.5 - SAP SF
│   └── s4hana.py          # 6.5 - SAP S/4
├── salesforce/
│   ├── __init__.py
│   └── connector.py       # 6.6 - Salesforce
└── oracle/
    ├── __init__.py
    ├── hcm.py             # 6.7 - Oracle HCM
    └── erp.py             # 6.7 - Oracle ERP
```

---

## Security Considerations

1. **Credential Security**
   - Encrypt all credentials at rest
   - Use environment variables for encryption keys
   - Support for external secrets managers (AWS Secrets Manager, HashiCorp Vault)

2. **API Rate Limiting**
   - Respect vendor rate limits
   - Implement backoff strategies
   - Queue long-running requests

3. **Data Privacy**
   - PII handling per customer requirements
   - Audit logging of all API calls
   - Data retention policies

4. **Network Security**
   - HTTPS only
   - Certificate validation
   - IP whitelisting support

---

## Success Criteria

**Phase Complete When:**
1. Credential management working securely
2. At least 3 connectors fully implemented and tested
3. Live data flows into Intelligence Engine as Reality truths
4. Query translation working between products
5. Error handling and retry logic robust

---

## Version History

| Date | Change |
|------|--------|
| 2026-01-12 | Phase 6 created (expanded from original Phase 5) |
