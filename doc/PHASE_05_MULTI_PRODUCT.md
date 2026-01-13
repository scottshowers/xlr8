# Phase 5: Multi-Product Schemas

**Goal:** Expand XLR8 beyond HCM to support FINS, ERP, CRM, and other enterprise products.

**Status:** NOT STARTED  
**Estimated Hours:** 15-20

---

## Component Overview

| # | Component | Hours | Status | Description |
|---|-----------|-------|--------|-------------|
| 5.1 | Schema Loader | 3-4 | NOT STARTED | Load schemas for HCM, FINS, ERP, CRM, etc. |
| 5.2 | Product Registry | 2-3 | NOT STARTED | Product type definitions (functions, vendors, versions) |
| 5.3 | Domain Alignment | 4-5 | NOT STARTED | Map product entities to universal domains |
| 5.4 | Vocabulary Normalization | 3-4 | NOT STARTED | Cross-product term mapping |
| 5.5 | Hub Type Expansion | 2-3 | NOT STARTED | Extend BRIT beyond HCM hub types |

---

## Component 5.1: Schema Loader

**Goal:** Load and parse schemas from multiple product types.

### Supported Products

| Category | Products | Schema Source |
|----------|----------|---------------|
| HCM | UKG Pro, UKG WFM, UKG Ready, Workday HCM, SAP SuccessFactors | Existing + new |
| FINS | Workday Financials, SAP FI/CO, Oracle Financials, NetSuite | New |
| ERP | SAP S/4HANA, Oracle ERP Cloud, Microsoft Dynamics | New |
| CRM | Salesforce, HubSpot, Microsoft Dynamics CRM | New |
| SCM | SAP SCM, Oracle SCM, Coupa | New |

### Schema Structure

```python
@dataclass
class ProductSchema:
    """Schema definition for a product."""
    product_id: str           # e.g., "workday_fins"
    product_name: str         # e.g., "Workday Financials"
    vendor: str               # e.g., "Workday"
    category: str             # e.g., "FINS"
    version: str              # e.g., "2024.1"
    
    tables: List[TableSchema]
    relationships: List[Relationship]
    vocabularies: Dict[str, List[str]]
    
    # Metadata
    loaded_at: datetime
    source_file: str
```

### Implementation

```python
class SchemaLoader:
    """Load and parse product schemas."""
    
    SCHEMA_DIR = "/mnt/skills/schemas"  # Or configurable path
    
    def load_product(self, product_id: str) -> ProductSchema:
        """Load schema for a specific product."""
        pass
    
    def load_all(self) -> Dict[str, ProductSchema]:
        """Load all available product schemas."""
        pass
    
    def discover_schemas(self) -> List[str]:
        """Find available schema files."""
        pass
```

---

## Component 5.2: Product Registry

**Goal:** Central registry of product types, vendors, and capabilities.

### Product Taxonomy

```
Enterprise Software
├── HCM (Human Capital Management)
│   ├── Core HR
│   ├── Payroll
│   ├── Time & Attendance
│   ├── Benefits
│   ├── Recruiting
│   └── Learning
├── FINS (Financials)
│   ├── General Ledger
│   ├── Accounts Payable
│   ├── Accounts Receivable
│   ├── Fixed Assets
│   └── Cash Management
├── ERP (Enterprise Resource Planning)
│   ├── Manufacturing
│   ├── Inventory
│   ├── Procurement
│   └── Project Management
├── CRM (Customer Relationship Management)
│   ├── Sales
│   ├── Marketing
│   ├── Service
│   └── Commerce
└── SCM (Supply Chain Management)
    ├── Planning
    ├── Logistics
    ├── Warehouse
    └── Transportation
```

### Product Definition

```python
@dataclass
class ProductDefinition:
    """Definition of a product type."""
    product_id: str
    vendor: str
    category: str              # HCM, FINS, ERP, CRM, SCM
    functions: List[str]       # Core HR, Payroll, GL, etc.
    
    # API capabilities
    api_type: str              # REST, SOAP, GraphQL, RaaS
    auth_methods: List[str]    # OAuth2, API Key, Basic, etc.
    
    # Schema info
    schema_version: str
    schema_file: str
    
    # Feature flags
    supports_bulk: bool
    supports_streaming: bool
    supports_webhooks: bool
```

### Registry Implementation

```python
class ProductRegistry:
    """Central registry of supported products."""
    
    def register_product(self, definition: ProductDefinition):
        """Register a new product."""
        pass
    
    def get_product(self, product_id: str) -> ProductDefinition:
        """Get product definition by ID."""
        pass
    
    def list_by_category(self, category: str) -> List[ProductDefinition]:
        """List all products in a category."""
        pass
    
    def list_by_vendor(self, vendor: str) -> List[ProductDefinition]:
        """List all products from a vendor."""
        pass
```

---

## Component 5.3: Domain Alignment

**Goal:** Map product-specific entities to universal domains for cross-product analysis.

### Universal Domains

| Domain | Description | Example Entities |
|--------|-------------|------------------|
| People | Individuals in any context | Employee, Customer, Vendor, Contact |
| Organization | Organizational structures | Company, Department, Cost Center, Business Unit |
| Finance | Financial transactions | Invoice, Payment, Journal Entry, Budget |
| Time | Time-based records | Timesheet, Schedule, Calendar, Period |
| Compensation | Pay and benefits | Earnings, Deductions, Benefits, Bonuses |
| Assets | Physical and digital assets | Equipment, Inventory, Fixed Assets |
| Transactions | Business transactions | Order, Shipment, Receipt, Transfer |
| Documents | Business documents | Contract, Agreement, Policy, Report |

### Entity Mapping

```python
@dataclass
class EntityMapping:
    """Maps a product entity to a universal domain."""
    product_id: str
    product_entity: str        # e.g., "EMPLOYEE" in UKG
    universal_domain: str      # e.g., "People"
    universal_entity: str      # e.g., "Employee"
    
    # Field mappings
    field_mappings: Dict[str, str]  # product_field -> universal_field
    
    # Confidence
    mapping_type: str          # exact, semantic, inferred
    confidence: float
```

### Domain Aligner

```python
class DomainAligner:
    """Align product entities to universal domains."""
    
    def align_entity(self, product_id: str, entity: str) -> EntityMapping:
        """Map a product entity to universal domain."""
        pass
    
    def find_cross_product_matches(self, domain: str, entity: str) -> List[EntityMapping]:
        """Find equivalent entities across products."""
        pass
    
    def get_join_paths(self, source_product: str, target_product: str) -> List[JoinPath]:
        """Find how to join data across products."""
        pass
```

---

## Component 5.4: Vocabulary Normalization

**Goal:** Normalize terminology across products for consistent querying.

### Vocabulary Challenges

| Product | Their Term | Universal Term |
|---------|-----------|----------------|
| UKG Pro | "Company" | "Legal Entity" |
| Workday | "Company" | "Legal Entity" |
| SAP | "Company Code" | "Legal Entity" |
| Oracle | "Legal Entity" | "Legal Entity" |

| Product | Their Term | Universal Term |
|---------|-----------|----------------|
| UKG | "Earning Code" | "Pay Component" |
| Workday | "Earning" | "Pay Component" |
| SAP | "Wage Type" | "Pay Component" |

### Vocabulary Structure

```python
@dataclass
class VocabularyMapping:
    """Cross-product vocabulary mapping."""
    universal_term: str
    universal_definition: str
    
    product_terms: Dict[str, str]  # product_id -> their term
    
    # Synonyms and related terms
    synonyms: List[str]
    related_terms: List[str]
```

### Normalizer Implementation

```python
class VocabularyNormalizer:
    """Normalize terms across products."""
    
    def normalize(self, product_id: str, term: str) -> str:
        """Convert product-specific term to universal term."""
        pass
    
    def denormalize(self, universal_term: str, product_id: str) -> str:
        """Convert universal term to product-specific term."""
        pass
    
    def find_synonyms(self, term: str) -> List[str]:
        """Find all synonyms across products."""
        pass
    
    def suggest_mapping(self, product_id: str, term: str) -> List[VocabularyMapping]:
        """Suggest vocabulary mappings for unknown terms."""
        pass
```

---

## Component 5.5: Hub Type Expansion

**Goal:** Extend BRIT hub types beyond HCM to support all product categories.

### Current BRIT (HCM-focused)

~70+ hub types including:
- Demographics, Earnings, Deductions, Taxes, Time, Organization, Benefits, Recruiting, Learning

### Expanded BRIT

| Category | New Hub Types |
|----------|---------------|
| FINS | GL_Account, Journal_Entry, Invoice, Payment, Vendor_Master, Customer_Master, Budget, Cost_Center_Hierarchy |
| ERP | Material_Master, Bill_of_Materials, Production_Order, Inventory_Location, Purchase_Order, Sales_Order |
| CRM | Account, Contact, Opportunity, Lead, Campaign, Case, Quote, Contract |
| SCM | Supplier, Item, Warehouse, Shipment, Route, Carrier, Demand_Plan |

### Hub Definition Structure

```python
@dataclass
class HubDefinition:
    """Extended hub type definition."""
    hub_type: str
    category: str              # HCM, FINS, ERP, CRM, SCM
    
    # Schema
    core_fields: List[str]
    optional_fields: List[str]
    
    # Relationships
    parent_hubs: List[str]
    child_hubs: List[str]
    related_hubs: List[str]
    
    # Product mappings
    product_mappings: Dict[str, str]  # product_id -> table_name
    
    # Behavior
    is_config_table: bool
    is_transaction_table: bool
    temporal_type: str         # snapshot, effective_dated, transaction
```

---

## Integration Points

### With Existing Components

| Component | Integration |
|-----------|-------------|
| Term Index | Include multi-product vocabularies |
| Chunk Classifier | Detect product type from documents |
| Truth Router | Route by product category |
| Hub Scoring | Score across multiple product schemas |

### With Phase 6 (API Connectivity)

| Handoff | Description |
|---------|-------------|
| Product Registry → Connector Factory | Registry tells connectors which product to connect to |
| Schema → API Mapping | Schema defines what fields to request |
| Vocabulary → Query Translation | Normalize queries before sending to product API |

---

## File Structure

```
/backend/utils/products/
├── __init__.py
├── schema_loader.py       # 5.1
├── product_registry.py    # 5.2
├── domain_aligner.py      # 5.3
├── vocabulary_normalizer.py # 5.4
├── hub_definitions.py     # 5.5
└── types.py               # Shared types

/data/schemas/
├── hcm/
│   ├── ukg_pro.json
│   ├── ukg_wfm.json
│   ├── workday_hcm.json
│   └── sap_sf.json
├── fins/
│   ├── workday_fins.json
│   ├── sap_fico.json
│   └── oracle_fins.json
├── erp/
│   ├── sap_s4.json
│   └── oracle_erp.json
└── crm/
    ├── salesforce.json
    └── dynamics_crm.json
```

---

## Success Criteria

**Phase Complete When:**
1. Schemas loaded for 3+ products per category
2. Universal domain mappings for all major entities
3. Vocabulary normalization working cross-product
4. Hub types extended to cover FINS, ERP, CRM basics
5. Term index queries work across products

---

## Version History

| Date | Change |
|------|--------|
| 2026-01-12 | Phase 5 created |
