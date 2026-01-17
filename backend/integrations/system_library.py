"""
XLR8 SYSTEM LIBRARY - Vendor API Definitions
=============================================

Defines all supported systems, their schemas, API endpoints,
and how they map to XLR8's Five Truths.

Deploy to: backend/integrations/system_library.py

Created: January 17, 2026
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


class TruthBucket(Enum):
    """XLR8's Five Truths for data classification."""
    REALITY = "reality"           # What actually exists (employees, transactions)
    INTENT = "intent"             # What should happen (policies, rules)
    CONFIGURATION = "configuration"  # How system is set up (codes, settings)
    REFERENCE = "reference"       # External standards (regulations, benchmarks)
    REGULATORY = "regulatory"     # Compliance requirements


class ConnectionStatus(Enum):
    """System connection availability."""
    READY = "ready"               # Fully implemented, ready to use
    BETA = "beta"                 # Working but may have issues
    COMING_SOON = "coming_soon"   # Schema ready, API not implemented
    PLANNED = "planned"           # On roadmap


class AuthType(Enum):
    """Authentication methods."""
    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    BASIC = "basic"
    API_KEY_PLUS_BASIC = "api_key_plus_basic"  # UKG style


@dataclass
class APIEndpoint:
    """Definition of a single API endpoint."""
    id: str
    name: str
    description: str
    path: str
    method: str = "GET"
    truth_bucket: TruthBucket = TruthBucket.REALITY
    response_type: str = "json"
    pagination: bool = True
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemDefinition:
    """Complete definition of a vendor system."""
    id: str
    name: str
    vendor: str
    domain: str  # HCM, CRM, ERP, etc.
    description: str
    status: ConnectionStatus
    logo_url: Optional[str] = None
    
    # Authentication
    auth_type: AuthType = AuthType.API_KEY
    auth_fields: List[Dict[str, str]] = field(default_factory=list)
    base_url_template: str = ""  # e.g., "https://{customer}.ultipro.com"
    
    # Endpoints
    endpoints: List[APIEndpoint] = field(default_factory=list)
    
    # Schema reference (ChromaDB collection)
    schema_collection: Optional[str] = None


# =============================================================================
# UKG PRO - FULL IMPLEMENTATION
# =============================================================================

UKG_PRO = SystemDefinition(
    id="ukg_pro",
    name="UKG Pro",
    vendor="UKG",
    domain="HCM",
    description="Enterprise HCM suite for HR, Payroll, Talent, and Time",
    status=ConnectionStatus.READY,
    logo_url="/images/vendors/ukg.png",
    
    auth_type=AuthType.API_KEY_PLUS_BASIC,
    auth_fields=[
        {"name": "customer_api_key", "label": "Customer API Key", "type": "password", "required": True},
        {"name": "user_api_key", "label": "User API Key", "type": "password", "required": True},
        {"name": "username", "label": "Service Account Username", "type": "text", "required": True},
        {"name": "password", "label": "Service Account Password", "type": "password", "required": True},
        {"name": "customer_subdomain", "label": "Customer Subdomain", "type": "text", "required": True, 
         "help": "Your subdomain from login URL (e.g., 'acme' from acme.ultipro.com)"},
    ],
    base_url_template="https://service4.ultipro.com",
    
    schema_collection="ukg_pro_schema",
    
    endpoints=[
        # =====================
        # REALITY - Employee Data
        # =====================
        APIEndpoint(
            id="person_details",
            name="Person Details",
            description="Employee personal information (name, SSN, DOB, address)",
            path="/personnel/v1/person-details",
            truth_bucket=TruthBucket.REALITY,
        ),
        APIEndpoint(
            id="employment_details",
            name="Employment Details",
            description="Job, department, hire date, status, supervisor",
            path="/personnel/v1/employment-details",
            truth_bucket=TruthBucket.REALITY,
        ),
        APIEndpoint(
            id="compensation_details",
            name="Compensation Details",
            description="Salary, pay rate, pay frequency",
            path="/personnel/v1/compensation-details",
            truth_bucket=TruthBucket.REALITY,
        ),
        APIEndpoint(
            id="employee_deductions",
            name="Employee Deductions",
            description="Active deductions and benefits for employees",
            path="/personnel/v1/emp-deductions",
            truth_bucket=TruthBucket.REALITY,
        ),
        APIEndpoint(
            id="direct_deposit",
            name="Direct Deposit",
            description="Employee bank account information",
            path="/payroll/v1/direct-deposit",
            truth_bucket=TruthBucket.REALITY,
        ),
        APIEndpoint(
            id="contacts",
            name="Emergency Contacts",
            description="Employee emergency contacts and dependents",
            path="/personnel/v1/contacts",
            truth_bucket=TruthBucket.REALITY,
        ),
        APIEndpoint(
            id="pto_plans",
            name="PTO Plans",
            description="Employee PTO balances and accruals",
            path="/personnel/v1/pto-plans",
            truth_bucket=TruthBucket.REALITY,
        ),
        
        # =====================
        # REALITY - Payroll
        # =====================
        APIEndpoint(
            id="pay_register",
            name="Pay Register",
            description="Payroll run details and check data",
            path="/payroll/v1/pay-register",
            truth_bucket=TruthBucket.REALITY,
        ),
        APIEndpoint(
            id="earnings_history",
            name="Earnings History",
            description="Historical earnings by employee",
            path="/payroll/v1/earnings-history",
            truth_bucket=TruthBucket.REALITY,
        ),
        APIEndpoint(
            id="deduction_history",
            name="Deduction History",
            description="Historical deductions by employee",
            path="/payroll/v1/payroll-deductions-history",
            truth_bucket=TruthBucket.REALITY,
        ),
        
        # =====================
        # CONFIGURATION - Setup
        # =====================
        APIEndpoint(
            id="earnings_config",
            name="Earnings Codes",
            description="Earning code definitions and setup",
            path="/configuration/v1/earnings",
            truth_bucket=TruthBucket.CONFIGURATION,
        ),
        APIEndpoint(
            id="jobs_config",
            name="Job Codes",
            description="Job code definitions",
            path="/configuration/v1/jobs",
            truth_bucket=TruthBucket.CONFIGURATION,
        ),
        APIEndpoint(
            id="locations_config",
            name="Locations",
            description="Work location definitions",
            path="/configuration/v1/locations",
            truth_bucket=TruthBucket.CONFIGURATION,
        ),
        APIEndpoint(
            id="org_levels",
            name="Organization Levels",
            description="Org structure configuration",
            path="/configuration/v1/org-levels",
            truth_bucket=TruthBucket.CONFIGURATION,
        ),
        APIEndpoint(
            id="tax_groups",
            name="Tax Groups",
            description="Tax group configuration",
            path="/configuration/v1/tax-groups",
            truth_bucket=TruthBucket.CONFIGURATION,
        ),
        APIEndpoint(
            id="deduction_plans",
            name="Deduction/Benefit Plans",
            description="Benefit plan definitions",
            path="/configuration/v1/code-tables",
            params={"tableName": "deductionBenefitPlans"},
            truth_bucket=TruthBucket.CONFIGURATION,
        ),
        APIEndpoint(
            id="pay_groups",
            name="Pay Groups",
            description="Pay group definitions",
            path="/configuration/v1/pay-groups",
            truth_bucket=TruthBucket.CONFIGURATION,
        ),
        APIEndpoint(
            id="company_details",
            name="Company Details",
            description="Company-level configuration",
            path="/configuration/v1/company-details",
            truth_bucket=TruthBucket.CONFIGURATION,
        ),
        APIEndpoint(
            id="employee_types",
            name="Employee Types",
            description="Employee type definitions (FT, PT, etc.)",
            path="/configuration/v1/employee-types",
            truth_bucket=TruthBucket.CONFIGURATION,
        ),
    ]
)


# =============================================================================
# WORKDAY - COMING SOON (Schema Ready)
# =============================================================================

WORKDAY = SystemDefinition(
    id="workday",
    name="Workday",
    vendor="Workday",
    domain="HCM",
    description="Cloud-based enterprise HR and Finance",
    status=ConnectionStatus.COMING_SOON,
    logo_url="/images/vendors/workday.png",
    
    auth_type=AuthType.OAUTH2,
    auth_fields=[
        {"name": "tenant_url", "label": "Tenant URL", "type": "text", "required": True},
        {"name": "client_id", "label": "Client ID", "type": "text", "required": True},
        {"name": "client_secret", "label": "Client Secret", "type": "password", "required": True},
        {"name": "refresh_token", "label": "Refresh Token", "type": "password", "required": True},
    ],
    base_url_template="https://{tenant}.workday.com",
    
    schema_collection="workday_schema",
    
    endpoints=[
        APIEndpoint(id="workers", name="Workers", description="Employee data", path="/workers", truth_bucket=TruthBucket.REALITY),
        APIEndpoint(id="organizations", name="Organizations", description="Org structure", path="/organizations", truth_bucket=TruthBucket.CONFIGURATION),
        APIEndpoint(id="compensation", name="Compensation", description="Pay data", path="/compensation", truth_bucket=TruthBucket.REALITY),
    ]
)


# =============================================================================
# ADP WORKFORCE NOW - COMING SOON (Schema Ready)
# =============================================================================

ADP_WFN = SystemDefinition(
    id="adp_wfn",
    name="ADP Workforce Now",
    vendor="ADP",
    domain="HCM",
    description="Mid-market HR, Payroll, and Talent solution",
    status=ConnectionStatus.COMING_SOON,
    logo_url="/images/vendors/adp.png",
    
    auth_type=AuthType.OAUTH2,
    auth_fields=[
        {"name": "client_id", "label": "Client ID", "type": "text", "required": True},
        {"name": "client_secret", "label": "Client Secret", "type": "password", "required": True},
        {"name": "cert_path", "label": "Certificate Path", "type": "text", "required": True},
    ],
    base_url_template="https://api.adp.com",
    
    schema_collection="adp_wfn_schema",
    
    endpoints=[
        APIEndpoint(id="workers", name="Workers", description="Employee data", path="/hr/v2/workers", truth_bucket=TruthBucket.REALITY),
        APIEndpoint(id="pay_statements", name="Pay Statements", description="Payroll data", path="/payroll/v1/pay-statements", truth_bucket=TruthBucket.REALITY),
    ]
)


# =============================================================================
# PAYCOM - COMING SOON (Schema Ready)
# =============================================================================

PAYCOM = SystemDefinition(
    id="paycom",
    name="Paycom",
    vendor="Paycom",
    domain="HCM",
    description="Single-database HR and Payroll platform",
    status=ConnectionStatus.COMING_SOON,
    logo_url="/images/vendors/paycom.png",
    
    auth_type=AuthType.API_KEY,
    auth_fields=[
        {"name": "api_key", "label": "API Key", "type": "password", "required": True},
        {"name": "client_code", "label": "Client Code", "type": "text", "required": True},
    ],
    base_url_template="https://api.paycom.com",
    
    schema_collection="paycom_schema",
    
    endpoints=[
        APIEndpoint(id="employees", name="Employees", description="Employee data", path="/employees", truth_bucket=TruthBucket.REALITY),
        APIEndpoint(id="payroll", name="Payroll", description="Payroll data", path="/payroll", truth_bucket=TruthBucket.REALITY),
    ]
)


# =============================================================================
# SALESFORCE - COMING SOON (Schema Ready)
# =============================================================================

SALESFORCE = SystemDefinition(
    id="salesforce",
    name="Salesforce",
    vendor="Salesforce",
    domain="CRM",
    description="Cloud CRM and customer engagement platform",
    status=ConnectionStatus.COMING_SOON,
    logo_url="/images/vendors/salesforce.png",
    
    auth_type=AuthType.OAUTH2,
    auth_fields=[
        {"name": "instance_url", "label": "Instance URL", "type": "text", "required": True},
        {"name": "client_id", "label": "Consumer Key", "type": "text", "required": True},
        {"name": "client_secret", "label": "Consumer Secret", "type": "password", "required": True},
        {"name": "username", "label": "Username", "type": "text", "required": True},
        {"name": "password", "label": "Password + Security Token", "type": "password", "required": True},
    ],
    base_url_template="https://{instance}.salesforce.com",
    
    schema_collection="salesforce_schema",
    
    endpoints=[
        APIEndpoint(id="accounts", name="Accounts", description="Customer accounts", path="/services/data/v58.0/sobjects/Account", truth_bucket=TruthBucket.REALITY),
        APIEndpoint(id="contacts", name="Contacts", description="Contact records", path="/services/data/v58.0/sobjects/Contact", truth_bucket=TruthBucket.REALITY),
        APIEndpoint(id="opportunities", name="Opportunities", description="Sales opportunities", path="/services/data/v58.0/sobjects/Opportunity", truth_bucket=TruthBucket.REALITY),
    ]
)


# =============================================================================
# SYSTEM LIBRARY REGISTRY
# =============================================================================

SYSTEM_LIBRARY: Dict[str, SystemDefinition] = {
    "ukg_pro": UKG_PRO,
    "workday": WORKDAY,
    "adp_wfn": ADP_WFN,
    "paycom": PAYCOM,
    "salesforce": SALESFORCE,
}

# Group by domain
SYSTEMS_BY_DOMAIN: Dict[str, List[str]] = {
    "HCM": ["ukg_pro", "workday", "adp_wfn", "paycom"],
    "CRM": ["salesforce"],
    "ERP": [],  # Future: SAP, Oracle, NetSuite
    "Finance": [],  # Future: QuickBooks, Xero
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_system(system_id: str) -> Optional[SystemDefinition]:
    """Get a system definition by ID."""
    return SYSTEM_LIBRARY.get(system_id)


def get_systems_by_domain(domain: str) -> List[SystemDefinition]:
    """Get all systems in a domain."""
    system_ids = SYSTEMS_BY_DOMAIN.get(domain, [])
    return [SYSTEM_LIBRARY[sid] for sid in system_ids if sid in SYSTEM_LIBRARY]


def get_all_systems() -> List[SystemDefinition]:
    """Get all system definitions."""
    return list(SYSTEM_LIBRARY.values())


def get_ready_systems() -> List[SystemDefinition]:
    """Get only systems that are ready for connection."""
    return [s for s in SYSTEM_LIBRARY.values() if s.status == ConnectionStatus.READY]


def get_system_endpoints(system_id: str, truth_bucket: Optional[TruthBucket] = None) -> List[APIEndpoint]:
    """Get endpoints for a system, optionally filtered by truth bucket."""
    system = SYSTEM_LIBRARY.get(system_id)
    if not system:
        return []
    
    if truth_bucket:
        return [e for e in system.endpoints if e.truth_bucket == truth_bucket]
    return system.endpoints


def to_dict(system: SystemDefinition) -> Dict:
    """Convert system definition to dictionary for API response."""
    return {
        "id": system.id,
        "name": system.name,
        "vendor": system.vendor,
        "domain": system.domain,
        "description": system.description,
        "status": system.status.value,
        "logo_url": system.logo_url,
        "auth_type": system.auth_type.value,
        "auth_fields": system.auth_fields,
        "endpoints": [
            {
                "id": e.id,
                "name": e.name,
                "description": e.description,
                "truth_bucket": e.truth_bucket.value,
            }
            for e in system.endpoints
        ]
    }
