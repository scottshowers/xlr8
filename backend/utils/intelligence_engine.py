"""
XLR8 INTELLIGENCE ENGINE v5.20.0 - CONSULTATIVE SYNTHESIS
============================================================

Deploy to: backend/utils/intelligence_engine.py

FIVE TRUTHS ARCHITECTURE:
-------------------------
Customer Truths (project-scoped):
  1. REALITY - What the data shows (DuckDB queries)
  2. INTENT - Customer goals, SOWs, requirements
  3. CONFIGURATION - System setup, code tables, mappings

Reference Library Truths (global-scoped):
  4. REFERENCE - Product docs, how-to guides, implementation standards
  5. REGULATORY - Laws, IRS rules, state/federal mandates
  (+ COMPLIANCE - Audit requirements, SOC 2, internal controls)

CONSULTATIVE SYNTHESIS LAYER:
-----------------------------
The synthesis layer transforms raw data retrieval into world-class consultative
answers. It triangulates across all Five Truths, detecting alignments/conflicts,
and uses LLM to generate responses that:
  - Lead with the direct answer
  - Note where sources agree or conflict
  - Provide "so-what" context (implications, risks)
  - Signal confidence levels
  - End with actionable next steps

UPDATES:
- v5.20.0: CONSULTATIVE SYNTHESIS - LLM-powered response generation:
           * Added ConsultativeSynthesizer integration
           * Triangulates across Five Truths before answering
           * Uses Mistral (local) with Claude fallback
           * Adds "so-what" context and confidence signaling
           * Falls back to template formatting if LLM unavailable
- v5.19.0: COLUMN VALUE MATCHING - Table selection checks column VALUES:
           * Queries _column_profiles.distinct_values during table scoring
           * "show me SUI rates" matches tables where type_of_tax contains "SUI"
           * +80 score boost when query word matches a stored column value
           * Connects config validation valid_values to query routing
- v5.18.0: SQLCODER OPTIMIZATION - Major SQL generation overhaul:
           * Added _build_create_table_schema() - SQLCoder's training format
           * Added _is_simple_query() - detect single-table queries
           * Added _check_sql_columns() - validate LLM output
           * Simple queries now use CREATE TABLE format with exact column types
           * Only sends #1 scored table for simple queries (not 5)
           * Gets actual column types from DuckDB PRAGMA table_info
           * Includes sample data for column disambiguation
           * Falls back to multi-table flow for complex queries
- v5.17.0: FIVE TRUTHS ARCHITECTURE - Complete overhaul:
           * Added CONFIGURATION truth type (customer system setup)
           * Split "best practice" into REFERENCE, REGULATORY, COMPLIANCE
           * Added _gather_configuration() method
           * Added _gather_reference_library() returning 3 truth types
           * Added _check_compliance() for auto-compliance checking
           * Added ComplianceRule dataclass for structured rules
           * Updated _synthesize_answer() for all 5 truths
           * Updated _generate_consultative_response() with 5 truth sections
           * Added TRUTH_TYPES constant with taxonomy
           * Removed "best practice" terminology entirely
- v5.16.2: CONFIG QUESTION FIX - "how many ale groups" no longer triggers
           employee clarification. Added config_entity_patterns check to
           _is_employee_question() - if question mentions config entities
           (ale group, pay group, earnings, deductions, etc.), it's NOT
           an employee question even if it uses "how many" or "count".
- v5.16.1: PLURAL HANDLING - Fixed direct name match to handle plurals.
           "ale groups" now matches "ale_group" by trying singular forms.
           Also expanded skip-words list to avoid false matches.
- v5.16.0: DIRECT NAME MATCH - Critical fix for simple "show me X" queries.
           When question contains "ale group", tables with "ale_group" in name
           get +100 boost. Two-word matches (+100), three-word matches (+120).
           This ensures "what ale groups are setup?" finds ale_group_information
           instead of random tables like earnings_accumulation.
- v5.15.1: GROUPINGS IN INTELLIGENCE - Critical groupings now used throughout:
           - SQL hints include KEY GROUPING DIMENSIONS for LLM
           - Expanded by_patterns for filter detection (pay_group, union, FLSA, etc.)
           - Customer org terminology matching (e.g., "by division" → org_level_1)
           - Expanded clarification questions for all grouping types
- v5.15.0: CRITICAL GROUPINGS - Registry of core workforce dimensions:
           Country, Company/FEIN, Org Levels (1-4), Pay Groups, Earning Groups,
           Deduction Groups, Tax Groups, Union (National/Local), FLSA, 
           Hourly/Salary, FT/PT. Used for dashboards, filtering, SQL hints.
           Added get_resolved_groupings() and get_dashboard_groupings() methods.
- v5.14.2: ORG MAPPING - Loads customer org structure from Organization config table
- v5.14.1: DATA QUALITY CHECKS - Detects corrupted column headers (nan/unnamed)
- v5.14.0: CONFIG VALIDATION IMPROVEMENTS
- v5.13.0: CONFIG VALIDATION FRAMEWORK - Extended validation to non-rate domains
- v5.12.0: DOMAIN-AGNOSTIC VALIDATION - VALIDATION_CONFIG registry for all tax domains
- v5.11: LOCATION + GROUP BY FIX
        - Fixed table selection: "location" keyword now boosts tables with location columns
        - Fixed GROUP BY query handling: Now displays as table, not single count value
        - Tables with stateprovince/state/city get +40 boost for location questions
- v5.10: SMART FILTER INJECTION - checks if filter column exists in selected table
         before injecting. Prevents "column not found" errors when LLM picks
         wrong table for GROUP BY queries.
- v5.9: FIXED "All employees (3 total)" - was showing distinct status values count,
        now shows actual employee count from distribution sum.
        Removed Claude synthesis to avoid API costs - uses cleaner fallback formatting.
- v5.8: FIXED table selection - deprioritizes lookup tables (ethnic_co, org_level_, etc.)
        Prioritizes main data tables with many columns and rows.
- v5.7: CONSULTATIVE SYNTHESIS - Uses LLM to generate natural, helpful responses
        instead of raw data dumps. Adds context, insights, professional tone.
- v5.6: FIXED table alias collision - now uses sheet_name from metadata
- v5.5: FIXED table alias extraction for long/truncated table names
- v5.4: Location column validation
- v5.3: US state name→code fallback
- v5.2: FULLY DATA-DRIVEN filters
- v5.1: Filter override logic
- v5.0: Fixed state detection
- v4.9: ARE bug fix

SIMPLIFIED:
- Only asks ONE clarification: active/terminated/all employees
- Only when the question is about employees
- Everything else: just query the data
- LLM used for SQL generation only (where it adds value)
"""

import os
import re
import json
import logging
import requests
from requests.auth import HTTPBasicAuth
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)

# LOAD VERIFICATION - this line proves the new file is loaded
logger.warning("[INTELLIGENCE_ENGINE] ====== v5.20.0 CONSULTATIVE SYNTHESIS ======")

# CONSULTATIVE SYNTHESIS - Import the synthesizer
try:
    from backend.utils.consultative_synthesis import ConsultativeSynthesizer
    SYNTHESIS_AVAILABLE = True
    logger.info("[INTELLIGENCE_ENGINE] ConsultativeSynthesizer loaded successfully")
except ImportError:
    try:
        from utils.consultative_synthesis import ConsultativeSynthesizer
        SYNTHESIS_AVAILABLE = True
        logger.info("[INTELLIGENCE_ENGINE] ConsultativeSynthesizer loaded (alt path)")
    except ImportError:
        SYNTHESIS_AVAILABLE = False
        logger.warning("[INTELLIGENCE_ENGINE] ConsultativeSynthesizer not available - using template fallback")


# =============================================================================
# COMMON ENGLISH WORDS BLOCKLIST (ARE BUG FIX)
# Language-level filtering - these words should NEVER be treated as data codes
# even if they match values in the data (e.g., "ARE" is UAE but also "are")
# =============================================================================
COMMON_ENGLISH_BLOCKLIST = {
    # Common verbs
    'are', 'was', 'were', 'been', 'being', 'have', 'has', 'had', 'having',
    'can', 'could', 'may', 'might', 'must', 'shall', 'should', 'will', 'would',
    'get', 'got', 'let', 'put', 'say', 'see', 'use', 'try', 'ask', 'run',
    'set', 'add', 'end', 'own', 'pay', 'cut', 'win', 'hit', 'buy', 'sit',
    'do', 'did', 'does', 'done', 'go', 'goes', 'went', 'gone', 'come', 'came',
    
    # Common nouns/adjectives
    'the', 'and', 'for', 'not', 'all', 'one', 'two', 'new', 'now', 'old',
    'any', 'day', 'way', 'man', 'men', 'our', 'out', 'her', 'him', 'his',
    'who', 'how', 'its', 'job', 'few', 'top', 'low', 'big', 'lot', 'per',
    'each', 'every', 'both', 'many', 'much', 'more', 'most', 'some',
    
    # Question words
    'what', 'when', 'where', 'why', 'which',
    
    # Pronouns  
    'you', 'your', 'they', 'them', 'their', 'she', 'hers', 'we', 'us',
    
    # Prepositions
    'from', 'with', 'into', 'over', 'under', 'after', 'before', 'by', 'at', 'in', 'on', 'to',
    
    # Articles and conjunctions
    'but', 'yet', 'nor', 'so', 'or',
    
    # Common query words
    'total', 'count', 'list', 'show', 'find', 'give', 'tell', 'need',
    'only', 'just', 'also', 'even', 'still', 'again', 'then', 'than',
    'first', 'last', 'next', 'this', 'that', 'these', 'those',
}


def _is_word_boundary_match(text: str, word: str) -> bool:
    """
    Check if word appears in text with word boundaries (not as substring).
    Prevents "are" matching in "compare", etc.
    """
    pattern = r'\b' + re.escape(word) + r'\b'
    return bool(re.search(pattern, text, re.IGNORECASE))


def _is_blocklisted(word: str) -> bool:
    """Check if word is in the common English blocklist."""
    return word.lower() in COMMON_ENGLISH_BLOCKLIST


# =============================================================================
# VALIDATION CONFIGURATION REGISTRY
# Domain-agnostic validation rules for tax rates, deductions, etc.
# =============================================================================
VALIDATION_CONFIG = {
    # =========== RATE-BASED VALIDATIONS ===========
    'sui': {
        'name': 'SUI/SUTA Rates',
        'validation_type': 'rate',
        'keywords': ['sui', 'suta', 'state unemployment'],
        'table_patterns': ['tax_information', 'tax_groups', 'sui', 'suta'],
        'rate_range': (0.001, 0.20),  # 0.1% to 20% as decimal
        'rate_range_pct': (0.1, 20),  # Same as percentage
        'scope_cols': ['company', 'fein', 'state'],
        'high_rate_entities': ['MA', 'PA', 'RI', 'CT', 'MN', 'NJ', 'WV', 'AK', 'MI'],
        'high_rate_max': 0.22,  # 22% for high-rate states
        'zero_severity': 'medium',  # 0% can be valid (excellent experience)
        'temporal_check': True,
        'annual_update': True,
        'description': 'State Unemployment Insurance rates',
    },
    'futa': {
        'name': 'FUTA Rates',
        'validation_type': 'rate',
        'keywords': ['futa', 'federal unemployment'],
        'table_patterns': ['tax_information', 'tax_groups', 'futa'],
        'rate_range': (0.006, 0.06),  # 0.6% to 6% as decimal
        'rate_range_pct': (0.6, 6.0),
        'scope_cols': ['company', 'fein'],
        'high_rate_entities': [],
        'high_rate_max': 0.06,
        'zero_severity': 'high',  # 0% FUTA is almost always wrong
        'temporal_check': True,
        'annual_update': True,
        'description': 'Federal Unemployment Tax rates',
    },
    'workers_comp': {
        'name': 'Workers Compensation',
        'validation_type': 'rate',
        'keywords': ['workers comp', 'work comp', 'wc', 'wcb', 'workers compensation'],
        'table_patterns': ['workers_comp', 'wc_', 'comp_rate'],
        'rate_range': (0.001, 0.35),  # 0.1% to 35% - wide range due to hazardous classes
        'rate_range_pct': (0.1, 35.0),
        'scope_cols': ['company', 'state', 'class_code', 'wc_code'],
        'high_rate_entities': [],  # All states can have high rates for hazardous jobs
        'high_rate_max': 0.50,  # 50% max for extreme hazard classes
        'zero_severity': 'high',  # 0% WC is usually wrong
        'temporal_check': True,
        'annual_update': True,
        'description': 'Workers Compensation insurance rates',
    },
    'state_withholding': {
        'name': 'State Withholding',
        'validation_type': 'rate',
        'keywords': ['state withholding', 'sit', 'state income tax', 'state tax rate'],
        'table_patterns': ['tax_information', 'withholding', 'sit'],
        'rate_range': (0.0, 0.15),  # 0% to 15% (some states have no income tax)
        'rate_range_pct': (0.0, 15.0),
        'scope_cols': ['company', 'state'],
        'high_rate_entities': ['CA', 'NY', 'NJ', 'OR', 'MN', 'HI'],
        'high_rate_max': 0.15,
        'zero_severity': 'low',  # 0% valid for no-income-tax states
        'temporal_check': False,  # Tax tables, not employer-specific
        'annual_update': False,
        'description': 'State income tax withholding rates',
    },
    'local_tax': {
        'name': 'Local Tax',
        'validation_type': 'rate',
        'keywords': ['local tax', 'city tax', 'county tax', 'municipal tax', 'lit'],
        'table_patterns': ['local_tax', 'city_tax', 'municipal'],
        'rate_range': (0.0, 0.05),  # 0% to 5%
        'rate_range_pct': (0.0, 5.0),
        'scope_cols': ['company', 'state', 'locality', 'jurisdiction'],
        'high_rate_entities': [],
        'high_rate_max': 0.05,
        'zero_severity': 'low',  # Many localities have no local tax
        'temporal_check': False,
        'annual_update': False,
        'description': 'Local/municipal tax rates',
    },
    
    # =========== CONFIGURATION VALIDATIONS (Non-Rate) ===========
    'earnings': {
        'name': 'Earnings Codes',
        'validation_type': 'config',
        'keywords': ['earnings', 'earning code', 'pay code', 'earning setup', 'earnings configured',
                     'earnigs', 'earings', 'earning'],  # Common typos
        'table_patterns': ['earnings_nan', 'earnings_can', 'earnings_info_can', 'earnings_info_nan'],  # Specific config tables only
        'table_exclude_patterns': ['country_code', 'block_tax', 'employee', 'testing', 'groups', 'local'],  # Not config tables
        'scope_cols': ['company'],
        'checks': [
            {'name': 'duplicates', 'description': 'Duplicate earning codes with different settings'},
            {'name': 'missing_taxability', 'description': 'Earnings without tax treatment defined'},
            {'name': 'missing_w2', 'description': 'Taxable earnings without W-2 box mapping'},
            {'name': 'inactive_in_use', 'description': 'Inactive codes still assigned to employees'},
            {'name': 'missing_gl', 'description': 'Earnings without GL account mapping'},
        ],
        'required_columns': ['code', 'description', 'status'],
        'description': 'Earning code configuration and setup',
    },
    'deductions': {
        'name': 'Deduction Plans',
        'validation_type': 'config',
        'keywords': ['deduction', 'deduction code', 'benefit plan', 'deduction setup', 'deductions configured'],
        'table_patterns': ['deduction_benefit', 'deductions_nan', 'deductions_can', 'benefit_plan'],
        'table_exclude_patterns': ['employee', 'testing', 'groups'],  # Not config tables
        'scope_cols': ['company'],
        'checks': [
            {'name': 'missing_vendor', 'description': 'Deductions without vendor/payee setup'},
            {'name': 'missing_limits', 'description': 'Pre-tax deductions without annual limits'},
            {'name': 'arrears_not_set', 'description': 'Deductions without arrears handling configured'},
            {'name': 'missing_eligibility', 'description': 'Benefits without eligibility rules'},
            {'name': 'inactive_enrolled', 'description': 'Inactive plans with enrolled employees'},
        ],
        'required_columns': ['code', 'description', 'status'],
        'description': 'Deduction and benefit plan configuration',
    },
    'gl_mapping': {
        'name': 'GL Mapping',
        'validation_type': 'config',
        'keywords': ['gl', 'general ledger', 'gl mapping', 'account mapping', 'gl configured', 'chart of accounts'],
        'table_patterns': ['general_ledger', 'gl_', 'account_map', 'gl_rules'],
        'scope_cols': ['company'],
        'checks': [
            {'name': 'unmapped_earnings', 'description': 'Earnings without GL account assigned'},
            {'name': 'unmapped_deductions', 'description': 'Deductions without GL account assigned'},
            {'name': 'unmapped_taxes', 'description': 'Taxes without GL account assigned'},
            {'name': 'invalid_accounts', 'description': 'Mappings to non-existent accounts'},
            {'name': 'missing_segments', 'description': 'Account strings missing required segments'},
        ],
        'required_columns': ['account', 'type'],
        'description': 'General Ledger account mapping',
    },
    'tax_jurisdictions': {
        'name': 'Tax Jurisdictions',
        'validation_type': 'config',
        'keywords': ['tax jurisdiction', 'jurisdiction setup', 'state setup', 'tax setup', 'jurisdiction configured'],
        'table_patterns': ['tax_', 'jurisdiction', 'state_tax'],
        'scope_cols': ['company', 'state'],
        'checks': [
            {'name': 'missing_states', 'description': 'States with employees but no tax setup'},
            {'name': 'missing_local', 'description': 'Localities requiring tax not configured'},
            {'name': 'missing_tax_id', 'description': 'Jurisdictions without employer tax ID'},
            {'name': 'expired_registration', 'description': 'Tax registrations that may need renewal'},
        ],
        'required_columns': ['state', 'tax_type'],
        'description': 'Tax jurisdiction setup and registration',
    },
}


# =============================================================================
# CRITICAL GROUPINGS - Core dimensions for dashboards, filtering, and analysis
# These are the key ways customers segment their workforce data
# =============================================================================
CRITICAL_GROUPINGS = {
    # Geographic
    'country': {
        'name': 'Country',
        'category': 'geographic',
        'column_patterns': ['country', 'country_code', 'country_name'],
        'config_table_patterns': ['country'],
        'dashboard_priority': 1,  # Higher = more important for default dashboard
        'description': 'Geographic country segmentation',
    },
    
    # Legal Entity
    'company': {
        'name': 'Company',
        'category': 'legal_entity',
        'column_patterns': ['company', 'company_code', 'home_company', 'fein', 'legal_entity'],
        'config_table_patterns': ['company', 'legal_entity'],
        'dashboard_priority': 2,
        'aliases': ['company code', 'FEIN', 'legal entity'],
        'description': 'Legal entity / employer identification',
    },
    
    # Organizational Hierarchy (dynamic - loaded from org_mapping)
    'org_level_1': {
        'name': 'Org Level 1',  # Will be overridden by customer terminology
        'category': 'organization',
        'column_patterns': ['org_level_1', 'org_level1', 'division'],
        'config_table_patterns': ['organization'],
        'dashboard_priority': 3,
        'dynamic_name': True,  # Name comes from org_mapping
        'description': 'Top-level organization unit',
    },
    'org_level_2': {
        'name': 'Org Level 2',
        'category': 'organization',
        'column_patterns': ['org_level_2', 'org_level2', 'department'],
        'config_table_patterns': ['organization'],
        'dashboard_priority': 4,
        'dynamic_name': True,
        'description': 'Second-level organization unit',
    },
    'org_level_3': {
        'name': 'Org Level 3',
        'category': 'organization',
        'column_patterns': ['org_level_3', 'org_level3', 'cost_center'],
        'config_table_patterns': ['organization'],
        'dashboard_priority': 5,
        'dynamic_name': True,
        'description': 'Third-level organization unit',
    },
    'org_level_4': {
        'name': 'Org Level 4',
        'category': 'organization',
        'column_patterns': ['org_level_4', 'org_level4'],
        'config_table_patterns': ['organization'],
        'dashboard_priority': 6,
        'dynamic_name': True,
        'description': 'Fourth-level organization unit',
    },
    
    # Payroll Processing
    'pay_group': {
        'name': 'Pay Group',
        'category': 'payroll',
        'column_patterns': ['pay_group', 'paygroup', 'pay_group_code'],
        'config_table_patterns': ['pay_group', 'paygroup'],
        'dashboard_priority': 7,
        'description': 'Payroll processing group',
    },
    
    # Compensation Groups
    'earning_group': {
        'name': 'Earning Group',
        'category': 'compensation',
        'column_patterns': ['earning_group', 'earnings_group', 'earn_group'],
        'config_table_patterns': ['earnings_groups', 'earning_group'],
        'dashboard_priority': 10,
        'description': 'Earnings code grouping for reporting',
    },
    'deduction_group': {
        'name': 'Deduction Group',
        'category': 'compensation',
        'column_patterns': ['deduction_group', 'ded_group', 'benefit_group'],
        'config_table_patterns': ['deduction_group', 'benefit_group'],
        'dashboard_priority': 11,
        'description': 'Deduction/benefit grouping for reporting',
    },
    
    # Tax
    'tax_group': {
        'name': 'Tax Group',
        'category': 'tax',
        'column_patterns': ['tax_group', 'tax_group_code'],
        'config_table_patterns': ['tax_group'],
        'dashboard_priority': 12,
        'description': 'Tax processing group',
    },
    
    # Labor Relations
    'union_national': {
        'name': 'National Union',
        'category': 'labor',
        'column_patterns': ['national_union', 'union_code', 'union_national'],
        'config_table_patterns': ['union', 'labor'],
        'dashboard_priority': 13,
        'description': 'National union affiliation',
    },
    'union_local': {
        'name': 'Local Union',
        'category': 'labor',
        'column_patterns': ['local_union', 'union_local', 'local_code'],
        'config_table_patterns': ['union', 'labor'],
        'dashboard_priority': 14,
        'description': 'Local union affiliation',
    },
    
    # Regulatory / Classification
    'flsa': {
        'name': 'FLSA Status',
        'category': 'regulatory',
        'column_patterns': ['flsa', 'flsa_status', 'exempt', 'exempt_status', 'flsa_code'],
        'config_table_patterns': ['flsa'],
        'dashboard_priority': 8,
        'valid_values': ['Exempt', 'Non-Exempt', 'E', 'N'],
        'description': 'Fair Labor Standards Act classification',
    },
    'pay_type': {
        'name': 'Hourly/Salary',
        'category': 'classification',
        'column_patterns': ['pay_type', 'hourly_salary', 'salary_type', 'compensation_type'],
        'config_table_patterns': [],
        'dashboard_priority': 9,
        'valid_values': ['Hourly', 'Salary', 'H', 'S'],
        'aliases': ['hourly/salary', 'hourly vs salary'],
        'description': 'Compensation basis (hourly or salaried)',
    },
    'ft_pt': {
        'name': 'Full-Time/Part-Time',
        'category': 'classification',
        'column_patterns': ['ft_pt', 'full_part', 'employee_type', 'work_schedule_type', 'fte_status'],
        'config_table_patterns': [],
        'dashboard_priority': 9,
        'valid_values': ['Full-Time', 'Part-Time', 'FT', 'PT', 'F', 'P'],
        'aliases': ['FT/PT', 'full-time/part-time'],
        'description': 'Full-time or part-time status',
    },
}


def _get_grouping_column(grouping_key: str, available_columns: List[str]) -> Optional[str]:
    """
    Find the actual column name for a grouping dimension.
    Returns the first matching column from available_columns.
    """
    config = CRITICAL_GROUPINGS.get(grouping_key)
    if not config:
        return None
    
    col_lower_map = {c.lower(): c for c in available_columns}
    
    for pattern in config.get('column_patterns', []):
        pattern_lower = pattern.lower()
        # Exact match
        if pattern_lower in col_lower_map:
            return col_lower_map[pattern_lower]
        # Partial match
        for col_lower, col_orig in col_lower_map.items():
            if pattern_lower in col_lower:
                return col_orig
    
    return None


def _detect_validation_domain(question: str) -> Optional[Dict]:
    """
    Detect which validation domain applies to the question.
    Returns the config dict or None if not a validation question.
    """
    q_lower = question.lower()
    
    for domain_key, config in VALIDATION_CONFIG.items():
        for keyword in config['keywords']:
            if keyword in q_lower:
                logger.info(f"[VALIDATION] Detected domain: {domain_key} (keyword: {keyword})")
                return {'key': domain_key, **config}
    
    return None


# =============================================================================
# TRUTH TYPE TAXONOMY
# =============================================================================
# The Five Sources of Truth for Implementation Analysis

TRUTH_TYPES = {
    # Customer-specific truths
    'reality': 'Customer data in DuckDB - what actually exists',
    'intent': 'Customer goals, SOWs, requirements - what they want',
    'configuration': 'Customer system setup, code tables, mappings - how they configured it',
    
    # Global/Reference Library truths
    'reference': 'Product docs, how-to guides, implementation standards',
    'regulatory': 'Laws, IRS rules, state/federal mandates - legal requirements',
    'compliance': 'Audit requirements, SOC 2, internal controls - what must be proven',
}

# Which truth types are customer-specific vs global
CUSTOMER_TRUTH_TYPES = ['intent', 'configuration']
GLOBAL_TRUTH_TYPES = ['reference', 'regulatory', 'compliance']

# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Truth:
    """A piece of information from one source of truth."""
    source_type: str  # One of: reality, intent, configuration, reference, regulatory, compliance
    source_name: str
    content: Any
    confidence: float
    location: str
    metadata: Dict = field(default_factory=dict)  # Additional context


@dataclass  
class Conflict:
    """A detected conflict between sources of truth."""
    description: str
    reality: Optional[Truth] = None
    intent: Optional[Truth] = None
    configuration: Optional[Truth] = None
    reference: Optional[Truth] = None
    regulatory: Optional[Truth] = None
    compliance: Optional[Truth] = None
    severity: str = "medium"
    recommendation: str = ""


@dataclass
class Insight:
    """A proactive insight discovered while processing."""
    type: str
    title: str
    description: str
    data: Any
    severity: str
    action_required: bool = False


@dataclass
class ComplianceRule:
    """A structured rule extracted from regulatory/compliance documents."""
    rule_id: str
    source_doc: str
    source_page: str
    condition: str  # Human readable condition
    condition_sql: Optional[str]  # SQL-translatable condition if possible
    requirement: str  # What must be true
    effective_date: Optional[str]
    severity: str = "high"  # high, medium, low
    category: str = "regulatory"  # regulatory, compliance, reference


@dataclass
class SynthesizedAnswer:
    """A complete answer synthesized from all sources."""
    question: str
    answer: str
    confidence: float
    # Customer truths
    from_reality: List[Truth] = field(default_factory=list)
    from_intent: List[Truth] = field(default_factory=list)
    from_configuration: List[Truth] = field(default_factory=list)
    # Global truths (Reference Library)
    from_reference: List[Truth] = field(default_factory=list)
    from_regulatory: List[Truth] = field(default_factory=list)
    from_compliance: List[Truth] = field(default_factory=list)
    # Analysis
    conflicts: List[Conflict] = field(default_factory=list)
    insights: List[Insight] = field(default_factory=list)
    compliance_check: Optional[Dict] = None  # Results of auto-compliance checking
    structured_output: Optional[Dict] = None
    reasoning: List[str] = field(default_factory=list)
    executed_sql: Optional[str] = None


class IntelligenceMode(Enum):
    SEARCH = "search"
    ANALYZE = "analyze"
    COMPARE = "compare"
    VALIDATE = "validate"
    CONFIGURE = "configure"
    INTERVIEW = "interview"
    WORKFLOW = "workflow"
    POPULATE = "populate"
    REPORT = "report"


# =============================================================================
# SEMANTIC PATTERNS (for column matching only)
# =============================================================================

SEMANTIC_TYPES = {
    'employee_id': [
        r'^emp.*id', r'^ee.*num', r'^employee.*number', r'^worker.*id',
        r'^person.*id', r'^emp.*num', r'^emp.*no$', r'^ee.*id',
        r'^employee.*id', r'^staff.*id', r'^associate.*id', r'^emp.*key',
    ],
    'company_code': [
        r'^comp.*code', r'^co.*code', r'^company.*id', r'^org.*code',
        r'^entity.*code', r'^legal.*entity', r'^business.*unit',
        r'^company$', r'^comp$',
    ],
}


# =============================================================================
# INTELLIGENCE ENGINE
# =============================================================================

class IntelligenceEngine:
    """The brain of XLR8."""
    
    def __init__(self, project_name: str, project_id: str = None):
        self.project = project_name
        self.project_id = project_id  # UUID for RAG filtering
        self.structured_handler = None
        self.rag_handler = None
        self.schema = {}
        self.relationships = []
        self.conversation_history = []
        self.confirmed_facts = {}
        self.pending_questions = []
        self.conversation_context = {}
        self.last_executed_sql = None
        self.filter_candidates = {}  # Detected filter dimensions
        
        # Consultative synthesis - LLM-powered response generation
        self._synthesizer = None
        self._last_reality = []
        self._last_intent = []
        self._last_configuration = []
        self._last_reference = []
        self._last_regulatory = []
        self._last_compliance = []
        
        if SYNTHESIS_AVAILABLE:
            try:
                self._synthesizer = ConsultativeSynthesizer(
                    ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
                    claude_api_key=os.getenv("CLAUDE_API_KEY"),
                    model_preference="auto"  # Mistral first, Claude fallback
                )
                logger.info("[INTELLIGENCE_ENGINE] ConsultativeSynthesizer initialized")
            except Exception as e:
                logger.warning(f"[INTELLIGENCE_ENGINE] Synthesizer init failed: {e}")
    
    def load_context(
        self, 
        structured_handler=None, 
        rag_handler=None,
        schema: Dict = None,
        relationships: List[Dict] = None
    ):
        """Load data context for this project."""
        self.structured_handler = structured_handler
        self.rag_handler = rag_handler
        self.schema = schema or {}
        self.relationships = relationships or []
        
        # Extract filter candidates for intelligent clarification
        self.filter_candidates = self.schema.get('filter_candidates', {})
        if self.filter_candidates:
            logger.warning(f"[INTELLIGENCE] Filter candidates loaded: {list(self.filter_candidates.keys())}")
        
        # Load customer org structure mapping (org_level_X → customer terminology)
        self.org_mapping = {}
        self._load_org_mapping()
        
        # Log available dashboard groupings
        if self.schema:
            dashboard_groups = self.get_dashboard_groupings()
            if dashboard_groups:
                group_names = [g['name'] for g in dashboard_groups[:8]]  # Top 8
                logger.warning(f"[INTELLIGENCE] Dashboard groupings available: {group_names}")
    
    def _load_org_mapping(self):
        """
        Load customer-specific org level definitions.
        
        The Organization tab in UKG config reports has 2 vertical tables:
        1. Top table: Maps org_level_1 → "Division", org_level_2 → "Department", etc.
        2. Bottom table: Valid values for each org level
        
        This mapping allows us to:
        - Use customer's terminology in responses ("by Department" not "by org_level_2")
        - Generate correct SQL with meaningful column references
        - Build dashboards using customer's org structure
        """
        if not self.structured_handler:
            return
        
        try:
            # Find organization table
            tables = self.schema.get('tables', [])
            org_table = None
            for t in tables:
                tname = t.get('table_name', '').lower()
                if 'organization' in tname and 'validation' in tname:
                    org_table = t.get('table_name')
                    break
            
            if not org_table:
                logger.info("[ORG-MAPPING] No organization config table found")
                return
            
            # Query for org level definitions (typically in first few rows)
            # Look for patterns like: org_level_1, Division, org_level_2, Department
            try:
                rows = self.structured_handler.query(f'''
                    SELECT * FROM "{org_table}" LIMIT 20
                ''')
                
                if not rows:
                    return
                
                # Parse org level mappings from the data
                # Common patterns:
                # - Column named "org_level" or "level" with values like "org_level_1"
                # - Adjacent column with the customer name like "Division"
                # - Or horizontal: org_level_1_name = "Division" in columns
                
                for row in rows:
                    for key, value in row.items():
                        key_lower = str(key).lower()
                        value_str = str(value).strip() if value else ''
                        
                        # Pattern 1: org_level_X in value, look for name in adjacent columns
                        if value_str.lower().startswith('org_level_'):
                            level_num = value_str.lower().replace('org_level_', '')
                            # Find the name in other columns
                            for k2, v2 in row.items():
                                if k2 != key and v2 and isinstance(v2, str) and len(v2) > 1:
                                    v2_clean = v2.strip()
                                    if v2_clean and not v2_clean.lower().startswith('org_level'):
                                        self.org_mapping[f'org_level_{level_num}'] = v2_clean
                                        break
                        
                        # Pattern 2: Column name contains org_level, value is the customer name
                        if 'org_level' in key_lower and value_str and not value_str.lower().startswith('org_level'):
                            level_match = re.search(r'org_level_?(\d+)', key_lower)
                            if level_match:
                                level_num = level_match.group(1)
                                self.org_mapping[f'org_level_{level_num}'] = value_str
                
                if self.org_mapping:
                    logger.warning(f"[ORG-MAPPING] Loaded customer org structure: {self.org_mapping}")
                else:
                    logger.info("[ORG-MAPPING] Could not parse org level mappings from organization table")
                    
            except Exception as e:
                logger.warning(f"[ORG-MAPPING] Error querying organization table: {e}")
                
        except Exception as e:
            logger.warning(f"[ORG-MAPPING] Error loading org mapping: {e}")
    
    def get_resolved_groupings(self) -> Dict[str, Dict]:
        """
        Get all critical groupings resolved with customer terminology.
        
        Returns dict with grouping key → resolved config including:
        - Actual column names found in data
        - Customer-specific names (from org_mapping)
        - Dashboard priority
        
        Used for:
        - Building customer dashboards
        - Natural language → SQL translation
        - Filter dropdowns
        - GROUP BY hints
        """
        resolved = {}
        
        # Get available columns from schema
        available_columns = []
        for table in self.schema.get('tables', []):
            for col in table.get('columns', []):
                col_name = col.get('name') if isinstance(col, dict) else str(col)
                available_columns.append(col_name)
        
        for grouping_key, config in CRITICAL_GROUPINGS.items():
            resolved_config = config.copy()
            
            # Find actual column in data
            actual_col = _get_grouping_column(grouping_key, available_columns)
            resolved_config['actual_column'] = actual_col
            resolved_config['available'] = actual_col is not None
            
            # Override name with customer terminology if available
            if config.get('dynamic_name') and hasattr(self, 'org_mapping'):
                customer_name = self.org_mapping.get(grouping_key)
                if customer_name:
                    resolved_config['customer_name'] = customer_name
                    resolved_config['name'] = customer_name  # Override default
            
            resolved[grouping_key] = resolved_config
        
        return resolved
    
    def get_dashboard_groupings(self) -> List[Dict]:
        """
        Get groupings available for dashboard display, sorted by priority.
        Only returns groupings that have actual columns in the data.
        
        Returns list of dicts with:
        - key: grouping key
        - name: display name (customer terminology if available)
        - column: actual column name
        - category: grouping category
        """
        resolved = self.get_resolved_groupings()
        
        dashboard_groupings = []
        for key, config in resolved.items():
            if config.get('available'):
                dashboard_groupings.append({
                    'key': key,
                    'name': config.get('customer_name', config.get('name')),
                    'column': config.get('actual_column'),
                    'category': config.get('category'),
                    'priority': config.get('dashboard_priority', 99),
                })
        
        # Sort by priority (lower = higher priority)
        dashboard_groupings.sort(key=lambda x: x['priority'])
        
        return dashboard_groupings
    
    def ask(
        self, 
        question: str,
        mode: IntelligenceMode = None,
        context: Dict = None
    ) -> SynthesizedAnswer:
        """Main entry point - ask the engine a question."""
        logger.warning(f"[INTELLIGENCE] Question: {question[:100]}...")
        logger.warning(f"[INTELLIGENCE] Current confirmed_facts: {self.confirmed_facts}")
        logger.warning(f"[INTELLIGENCE] Available filter categories: {list(self.filter_candidates.keys())}")
        
        q_lower = question.lower()
        
        # Check for export request
        export_keywords = ['export', 'download', 'excel', 'csv', 'spreadsheet', 'get the data', 'full data']
        is_export_request = any(kw in q_lower for kw in export_keywords)
        
        if is_export_request and hasattr(self, '_last_validation_export') and self._last_validation_export:
            logger.warning(f"[INTELLIGENCE] Export request detected - returning export data")
            export_data = self._last_validation_export
            domain_key = export_data.get('domain_key', 'validation')
            
            return SynthesizedAnswer(
                question=question,
                answer=f"📥 **Export Ready**\n\nI've prepared {export_data['total_records']} records for download.",
                confidence=0.95,
                structured_output={
                    'type': 'export_ready',
                    'export_data': export_data,
                    'filename_suggestion': f"{domain_key}_validation_{self.project or 'export'}.xlsx"
                },
                reasoning=['Export requested for validation data']
            )
        
        # Simple analysis
        mode = mode or self._detect_mode(q_lower)
        is_employee_question = self._is_employee_question(q_lower)
        logger.warning(f"[INTELLIGENCE] is_employee_question: {is_employee_question}")
        
        # Check if this is a VALIDATION question about config (not employee data)
        # These should NOT ask about employee status - they're about rates/setup
        validation_keywords = ['correct', 'valid', 'right', 'properly', 'configured', 
                              'issue', 'problem', 'check', 'verify', 'audit', 'review',
                              'accurate', 'wrong', 'error', 'mistake', 'setup', 'setting']
        
        # All config domains that should bypass employee status clarification
        config_domains = [
            # Rate-based domains
            'workers comp', 'work comp', 'sui ', 'suta', 'futa', 'tax rate', 
            'withholding', 'wc rate', 'workers compensation', 'local tax',
            # Config-based domains (with common typos)
            'earnings', 'earning code', 'pay code', 'earning setup', 'earnigs', 'earings', 'earning',
            'deduction', 'benefit plan', 'deduction setup', 'deductions',
            'gl', 'general ledger', 'gl mapping', 'account mapping',
            'tax jurisdiction', 'jurisdiction setup', 'state setup',
        ]
        
        is_validation_question = any(kw in q_lower for kw in validation_keywords)
        is_config_domain = any(cd in q_lower for cd in config_domains)
        
        # Override employee detection for config/validation questions
        if is_validation_question and is_config_domain:
            is_employee_question = False
            logger.warning(f"[INTELLIGENCE] Overriding is_employee_question=False for config validation question")
        
        # INTELLIGENT CLARIFICATION
        # For employee questions, determine which filters need clarification
        if is_employee_question:
            needed_clarifications = self._get_needed_clarifications(q_lower)
            logger.warning(f"[INTELLIGENCE] Needed clarifications: {needed_clarifications}")
            
            if needed_clarifications:
                # Build clarification question for first needed filter
                first_filter = needed_clarifications[0]
                return self._request_filter_clarification(question, first_filter)
        
        logger.warning(f"[INTELLIGENCE] Proceeding with facts: {self.confirmed_facts}")
        
        # Gather the Five Truths
        analysis = {'domains': self._detect_domains(q_lower), 'mode': mode}
        
        # REALITY - What the data shows
        reality = self._gather_reality(question, analysis)
        logger.info(f"[INTELLIGENCE] Reality gathered: {len(reality)} truths")
        
        # Check if we have a pending validation clarification
        if hasattr(self, '_pending_validation_clarification') and self._pending_validation_clarification:
            clarification = self._pending_validation_clarification
            self._pending_validation_clarification = None  # Clear it
            logger.warning(f"[INTELLIGENCE] Returning validation clarification")
            return clarification
        
        # CUSTOMER TRUTHS - Intent and Configuration
        # SKIP intent for validation questions - RAG pulls unrelated docs (earnings codes for SUI questions, etc.)
        if is_validation_question:
            intent = []
            logger.warning(f"[INTELLIGENCE] Skipping intent gathering for validation question - focus on Reality data only")
        else:
            intent = self._gather_intent(question, analysis)
        configuration = self._gather_configuration(question, analysis)
        
        # GLOBAL TRUTHS - Reference Library (reference, regulatory, compliance)
        # SKIP for validation questions - focus on Reality data only
        if is_validation_question:
            reference, regulatory, compliance = [], [], []
            logger.warning(f"[INTELLIGENCE] Skipping reference library for validation question")
        else:
            reference, regulatory, compliance = self._gather_reference_library(question, analysis)
        
        # Detect conflicts across all truth sources
        # SKIP for validation questions - gap detection pulls unrelated docs and produces garbage
        if is_validation_question:
            conflicts = []
            logger.warning(f"[INTELLIGENCE] Skipping gap detection for validation question")
        else:
            conflicts = self._detect_conflicts(reality, intent, configuration, reference, regulatory, compliance)
        insights = self._run_proactive_checks(analysis)
        
        # Auto-compliance check if we have regulatory rules
        compliance_check = None
        if regulatory:
            compliance_check = self._check_compliance(reality, configuration, regulatory)
        
        # Store truths for synthesizer access
        self._last_reality = reality
        self._last_intent = intent
        self._last_configuration = configuration
        self._last_reference = reference
        self._last_regulatory = regulatory
        self._last_compliance = compliance
        
        answer = self._synthesize_answer(
            question=question,
            mode=mode,
            reality=reality,
            intent=intent,
            configuration=configuration,
            reference=reference,
            regulatory=regulatory,
            compliance=compliance,
            conflicts=conflicts,
            insights=insights,
            compliance_check=compliance_check,
            context=context
        )
        
        self.conversation_history.append({
            'question': question,
            'answer_preview': answer.answer[:200] if answer.answer else '',
            'mode': mode.value if mode else 'search',
            'timestamp': datetime.now().isoformat()
        })
        
        return answer
    
    def _is_employee_question(self, q_lower: str) -> bool:
        """
        Check if question is about employees/people.
        
        CRITICAL: Questions about configuration entities (earnings, deductions, 
        pay groups, ale groups, etc.) should NOT trigger employee clarification
        even if they use "how many" or "count".
        """
        # First check: Is this about a config/setup entity? If so, NOT an employee question
        config_entity_patterns = [
            'ale group', 'ale_group', 'pay group', 'pay_group', 'tax group', 'tax_group',
            'earning', 'deduction', 'benefit', 'job code', 'job_code', 'location',
            'company', 'department', 'org level', 'bank', 'gl ', 'general ledger',
            'accrual', 'pto', 'union', 'shift', 'schedule', 'change reason',
            'termination reason', 'setup', 'configured', 'configuration', 'config',
            'setting', 'code', 'table', 'lookup', 'rate', 'rule', 'mapping'
        ]
        
        if any(pattern in q_lower for pattern in config_entity_patterns):
            return False  # Config question - don't ask about employees
        
        # Second check: Does it mention employees/people explicitly?
        employee_words = [
            'employee', 'employees', 'worker', 'workers', 'staff', 
            'people', 'person', 'who ', 'headcount', 'roster', 'census',
            'hire', 'hired', 'terminated', 'active', 'employment'
        ]
        
        # "how many" and "count" alone don't make it an employee question
        # They need to be combined with employee-related context
        if any(w in q_lower for w in employee_words):
            return True
        
        return False
    
    def _detect_status_in_question(self, q_lower: str) -> Optional[str]:
        """
        Check if user specified employee status in their question.
        Returns the detected status ('active', 'termed', 'all') or None.
        """
        # Active patterns
        if any(p in q_lower for p in ['active only', 'active employees', 'only active', 'current employees']):
            return 'active'
        
        # Terminated patterns
        if any(p in q_lower for p in ['terminated', 'termed', 'inactive', 'former employees']):
            return 'termed'
        
        # All patterns
        if any(p in q_lower for p in ['all employees', 'everyone', 'all staff', 'all workers', 'total employees']):
            return 'all'
        
        return None
    
    def _get_needed_clarifications(self, q_lower: str) -> List[str]:
        """
        Determine which filter categories need clarification for this question.
        
        Returns list of filter category names that need clarification.
        """
        needed = []
        
        logger.warning(f"[CLARIFICATION] Checking needed. confirmed_facts={self.confirmed_facts}, filter_candidates={list(self.filter_candidates.keys())}")
        
        # Check each available filter category
        for category in self.filter_candidates.keys():
            # ALWAYS detect first - user may be overriding a previous value
            detected = self._detect_filter_in_question(category, q_lower)
            
            if detected:
                # User specified in THIS question - set/override it
                if category in self.confirmed_facts and self.confirmed_facts[category] != detected:
                    logger.warning(f"[INTELLIGENCE] Overriding {category}: {self.confirmed_facts[category]} → {detected}")
                else:
                    logger.warning(f"[INTELLIGENCE] Detected {category} in question: {detected}")
                self.confirmed_facts[category] = detected
                continue
            
            # Not detected in question - check if already confirmed
            if category in self.confirmed_facts:
                logger.warning(f"[CLARIFICATION] Skipping {category} - already confirmed as {self.confirmed_facts[category]}")
                continue
            
            # Check if this filter is relevant to the question
            if self._is_filter_relevant(category, q_lower):
                needed.append(category)
        
        # Sort by priority (status first, then company, etc.)
        priority_order = ['status', 'company', 'organization', 'location', 'employee_type', 'pay_type', 'job']
        needed.sort(key=lambda x: priority_order.index(x) if x in priority_order else 99)
        
        logger.warning(f"[CLARIFICATION] Needed clarifications: {needed}")
        return needed
    
    def _detect_filter_in_question(self, category: str, q_lower: str) -> Optional[str]:
        """
        Check if user specified a filter value in their question.
        Returns the detected value or None.
        
        This is the SMART DETECTION that auto-applies filters without asking.
        """
        if category == 'status':
            return self._detect_status_in_question(q_lower)
        
        # Get filter candidates for this category
        candidates = self.filter_candidates.get(category, [])
        if not candidates:
            return None
        
        # LOCATION DETECTION - Fully data-driven from lookups and profile values
        if category == 'location':
            # STEP 1: Try to find location from lookups (DATA-DRIVEN)
            lookup_match = self._find_value_in_lookups(q_lower, 'location')
            if lookup_match:
                logger.warning(f"[FILTER-DETECT] Found location '{lookup_match}' from lookup")
                return lookup_match
            
            # STEP 2: Check actual values in data from filter_candidates
            for candidate in candidates:
                values = candidate.get('values', [])
                for value in values:
                    value_str = str(value).strip()
                    value_lower = value_str.lower()
                    
                    # Skip very short values and blocklisted common words
                    if len(value_str) < 2 or _is_blocklisted(value_lower):
                        continue
                    
                    # Check if value appears in question with word boundary
                    if _is_word_boundary_match(q_lower, value_lower):
                        logger.warning(f"[FILTER-DETECT] Found location value '{value_str}' in question")
                        return value_str
                    
                    # Also check for the code's description from lookups
                    description = self._get_lookup_description('location', value_str)
                    if description and _is_word_boundary_match(q_lower, description.lower()):
                        logger.warning(f"[FILTER-DETECT] Found location '{description}' → code '{value_str}'")
                        return value_str
            
            # STEP 3: US State name→code mapping (universal knowledge fallback)
            # This is acceptable because US state abbreviations are standardized
            state_code = self._detect_us_state_in_question(q_lower)
            if state_code:
                logger.warning(f"[FILTER-DETECT] Found US state → '{state_code}' via standard mapping")
                return state_code
            
            return None
        
        # COMPANY DETECTION - Data-driven from lookups and profile values
        if category == 'company':
            # Try lookups first
            lookup_match = self._find_value_in_lookups(q_lower, 'company')
            if lookup_match:
                logger.warning(f"[FILTER-DETECT] Found company '{lookup_match}' from lookup")
                return lookup_match
            
            # Fall back to actual values in data
            for candidate in candidates:
                values = candidate.get('values', [])
                for value in values:
                    value_str = str(value).strip()
                    value_lower = value_str.lower()
                    if len(value_str) >= 3 and not _is_blocklisted(value_lower):
                        if _is_word_boundary_match(q_lower, value_lower):
                            logger.warning(f"[FILTER-DETECT] Found company '{value_str}' in question")
                            return value_str
                        # Check description from lookups
                        description = self._get_lookup_description('company', value_str)
                        if description and _is_word_boundary_match(q_lower, description.lower()):
                            logger.warning(f"[FILTER-DETECT] Found company '{description}' → code '{value_str}'")
                            return value_str
        
        # PAY TYPE DETECTION - Data-driven from lookups and profile values
        if category == 'pay_type':
            # Try lookups first
            lookup_match = self._find_value_in_lookups(q_lower, 'pay_type')
            if lookup_match:
                logger.warning(f"[FILTER-DETECT] Found pay_type '{lookup_match}' from lookup")
                return lookup_match
            
            # Fall back to actual values in data
            for candidate in candidates:
                values = candidate.get('values', [])
                for value in values:
                    value_str = str(value).strip()
                    value_lower = value_str.lower()
                    if len(value_str) >= 1 and not _is_blocklisted(value_lower):
                        if _is_word_boundary_match(q_lower, value_lower):
                            logger.warning(f"[FILTER-DETECT] Found pay_type '{value_str}' in question")
                            return value_str
                        # Check description from lookups
                        description = self._get_lookup_description('pay_type', value_str)
                        if description and _is_word_boundary_match(q_lower, description.lower()):
                            logger.warning(f"[FILTER-DETECT] Found pay_type '{description}' → code '{value_str}'")
                            return value_str
        
        # EMPLOYEE TYPE DETECTION - Data-driven from lookups and profile values
        if category == 'employee_type':
            # Try lookups first
            lookup_match = self._find_value_in_lookups(q_lower, 'employee_type')
            if lookup_match:
                logger.warning(f"[FILTER-DETECT] Found employee_type '{lookup_match}' from lookup")
                return lookup_match
            
            # Fall back to actual values in data
            for candidate in candidates:
                values = candidate.get('values', [])
                for value in values:
                    value_str = str(value).strip()
                    value_lower = value_str.lower()
                    if len(value_str) >= 1 and not _is_blocklisted(value_lower):
                        if _is_word_boundary_match(q_lower, value_lower):
                            logger.warning(f"[FILTER-DETECT] Found employee_type '{value_str}' in question")
                            return value_str
                        # Check description from lookups
                        description = self._get_lookup_description('employee_type', value_str)
                        if description and _is_word_boundary_match(q_lower, description.lower()):
                            logger.warning(f"[FILTER-DETECT] Found employee_type '{description}' → code '{value_str}'")
                            return value_str
        
        # GENERIC: Check any category against lookups and actual values
        # Try lookups first
        lookup_match = self._find_value_in_lookups(q_lower, category)
        if lookup_match:
            logger.warning(f"[FILTER-DETECT] Found {category} '{lookup_match}' from lookup")
            return lookup_match
        
        # Fall back to actual values in data
        for candidate in candidates:
            values = candidate.get('values', [])
            for value in values:
                value_str = str(value).strip()
                value_lower = value_str.lower()
                if len(value_str) > 2 and not _is_blocklisted(value_lower):
                    if _is_word_boundary_match(q_lower, value_lower):
                        logger.warning(f"[FILTER-DETECT] Found {category} value '{value_str}' in question")
                        return value_str
        
        return None
    
    def _is_filter_relevant(self, category: str, q_lower: str) -> bool:
        """
        Determine if a filter category is relevant to this question.
        Returns True if we should ASK about this filter (not auto-detected).
        
        Smart logic:
        - Status: Always relevant for employee questions (unless "all")
        - Company: Ask if "by company" or multiple companies exist and asking totals
        - Location: Ask if "by location/state" mentioned
        - Others: Only if explicitly requested with "by X"
        """
        # Status is almost always relevant for employee questions
        if category == 'status':
            # Skip if user said "all employees" or similar
            if any(p in q_lower for p in ['all employees', 'all staff', 'everyone', 'all workers']):
                self.confirmed_facts['status'] = 'all'
                return False
            return True
        
        # Check for "by X" patterns that trigger clarification
        # These align with CRITICAL_GROUPINGS - the key workforce dimensions
        by_patterns = {
            # Geographic / Legal Entity
            'company': ['by company', 'per company', 'each company', 'by entity', 'by legal entity', 'by fein'],
            'location': ['by location', 'by state', 'per state', 'by site', 'each location', 'by region', 'by country'],
            
            # Organization (dynamic - may use customer terminology)
            'organization': ['by department', 'by org', 'by cost center', 'per department', 'by division', 
                           'by org level', 'by business unit'],
            
            # Classification
            'pay_type': ['by pay type', 'hourly vs salary', 'hourly and salary', 'hourly or salary'],
            'employee_type': ['by employee type', 'by worker type', 'regular vs temp', 'by ft/pt', 
                            'full-time vs part-time', 'full time or part time'],
            
            # Payroll / Compensation Groups
            'pay_group': ['by pay group', 'per pay group', 'by paygroup'],
            'earning': ['by earning group', 'by earnings group', 'by earn group'],
            'deduction': ['by deduction group', 'by benefit group', 'by ded group'],
            
            # Tax / Labor
            'tax_group': ['by tax group', 'per tax group'],
            'union': ['by union', 'by local union', 'by national union', 'union vs non-union'],
            
            # Regulatory
            'flsa': ['by flsa', 'exempt vs non-exempt', 'by exempt status'],
        }
        
        patterns = by_patterns.get(category, [])
        if any(p in q_lower for p in patterns):
            # Check if we have multiple values to ask about
            candidates = self.filter_candidates.get(category, [])
            if candidates:
                distinct_count = candidates[0].get('distinct_count', 0)
                if distinct_count > 1:
                    logger.warning(f"[FILTER-RELEVANT] {category} relevant due to 'by X' pattern, {distinct_count} values")
                    return True
        
        # Also check customer-specific org terminology from org_mapping
        # e.g., if user says "by division" and org_level_1 = "Division"
        if category == 'organization' and hasattr(self, 'org_mapping') and self.org_mapping:
            for level_col, customer_name in self.org_mapping.items():
                customer_pattern = f"by {customer_name.lower()}"
                if customer_pattern in q_lower:
                    logger.warning(f"[FILTER-RELEVANT] Matched customer org term '{customer_name}' ({level_col})")
                    return True
        
        return False
    
    def _find_value_in_lookups(self, q_lower: str, lookup_type: str) -> Optional[str]:
        """
        Search lookups for a value mentioned in the question.
        Returns the code if found, None otherwise.
        
        DATA-DRIVEN: Uses lookups from _intelligence_lookups table.
        """
        if not self.structured_handler or not hasattr(self.structured_handler, 'conn'):
            return None
        
        try:
            # Load lookups for this type
            lookups = self.structured_handler.conn.execute("""
                SELECT code_column, lookup_data_json
                FROM _intelligence_lookups
                WHERE project_name = ? AND lookup_type = ?
            """, [self.project, lookup_type]).fetchall()
            
            for code_col, lookup_json in lookups:
                if not lookup_json:
                    continue
                    
                lookup_data = json.loads(lookup_json)
                
                # Check each code→description pair
                for code, description in lookup_data.items():
                    code_lower = str(code).lower()
                    desc_lower = str(description).lower() if description else ''
                    
                    # Check if description appears in question
                    if desc_lower and len(desc_lower) > 2:
                        if _is_word_boundary_match(q_lower, desc_lower):
                            return code
                    
                    # Check if code appears in question (for longer codes)
                    if len(code_lower) > 2 and not _is_blocklisted(code_lower):
                        if _is_word_boundary_match(q_lower, code_lower):
                            return code
            
            return None
            
        except Exception as e:
            logger.debug(f"[LOOKUP] Failed to search lookups: {e}")
            return None
    
    def _get_lookup_description(self, lookup_type: str, code: str) -> Optional[str]:
        """
        Get the description for a code from lookups.
        
        DATA-DRIVEN: Uses lookups from _intelligence_lookups table.
        """
        if not self.structured_handler or not hasattr(self.structured_handler, 'conn') or not code:
            return None
        
        try:
            lookups = self.structured_handler.conn.execute("""
                SELECT lookup_data_json
                FROM _intelligence_lookups
                WHERE project_name = ? AND lookup_type = ?
            """, [self.project, lookup_type]).fetchall()
            
            code_upper = str(code).upper().strip()
            
            for (lookup_json,) in lookups:
                if not lookup_json:
                    continue
                    
                lookup_data = json.loads(lookup_json)
                
                # Try exact match first
                if code_upper in lookup_data:
                    return lookup_data[code_upper]
                
                # Try case-insensitive
                for k, v in lookup_data.items():
                    if str(k).upper().strip() == code_upper:
                        return v
            
            return None
            
        except Exception as e:
            logger.debug(f"[LOOKUP] Failed to get description: {e}")
            return None
    
    def _detect_us_state_in_question(self, q_lower: str) -> Optional[str]:
        """
        Detect US state names in question and return state code.
        
        This is UNIVERSAL KNOWLEDGE fallback - US state abbreviations are standardized.
        Used only when data-driven lookups don't find a match.
        """
        # US States - full name to code mapping
        us_states = {
            'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR',
            'california': 'CA', 'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE',
            'florida': 'FL', 'georgia': 'GA', 'hawaii': 'HI', 'idaho': 'ID',
            'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA', 'kansas': 'KS',
            'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
            'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS',
            'missouri': 'MO', 'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV',
            'new hampshire': 'NH', 'new jersey': 'NJ', 'new mexico': 'NM', 'new york': 'NY',
            'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH', 'oklahoma': 'OK',
            'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
            'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT',
            'vermont': 'VT', 'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV',
            'wisconsin': 'WI', 'wyoming': 'WY'
        }
        
        for state_name, state_code in us_states.items():
            if _is_word_boundary_match(q_lower, state_name):
                return state_code
        
        return None

    def _request_filter_clarification(self, question: str, category: str) -> SynthesizedAnswer:
        """
        Build a clarification question for a specific filter category.
        Uses actual values from profile data.
        """
        # Get candidates for this category
        candidates = self.filter_candidates.get(category, [])
        
        if category == 'status':
            return self._request_employee_status_clarification(question)
        
        # Build options from profile data
        options = self._build_filter_options(category, candidates)
        
        if not options:
            # Skip this category if we can't build options
            return self._continue_without_filter(question, category)
        
        # Category-specific question text - aligned with CRITICAL_GROUPINGS
        question_text = {
            # Geographic / Legal Entity
            'company': "Which company should I include?",
            'location': "Which location(s)?",
            
            # Organization
            'organization': "Which department/organization?",
            
            # Classification
            'pay_type': "Which pay type?",
            'employee_type': "Which employee type?",
            'job': "Which job family/code?",
            
            # Payroll / Compensation Groups
            'pay_group': "Which pay group?",
            'earning': "Which earning group?",
            'deduction': "Which deduction/benefit group?",
            
            # Tax / Labor
            'tax_group': "Which tax group?",
            'union': "Which union?",
            
            # Regulatory
            'flsa': "Which FLSA status (Exempt/Non-Exempt)?",
        }.get(category, f"Which {category}?")
        
        return SynthesizedAnswer(
            question=question,
            answer="",
            confidence=0.0,
            structured_output={
                'type': 'clarification_needed',
                'filter_category': category,
                'questions': [{
                    'id': category,
                    'text': question_text,
                    'type': 'single_select',
                    'options': options
                }],
                'detected_domains': ['employees']
            },
            reasoning=f"Need to clarify {category} filter"
        )
    
    def _build_filter_options(self, category: str, candidates: List[Dict]) -> List[Dict]:
        """Build filter options from profile data."""
        if not candidates:
            return []
        
        # Use first candidate (highest priority)
        candidate = candidates[0]
        values = candidate.get('values', [])
        distribution = candidate.get('distribution', {})
        total_count = candidate.get('total_count', 0)
        
        if not values:
            return []
        
        options = []
        for value in values[:10]:  # Limit to 10 options
            count = distribution.get(str(value), 0)
            label = f"{value} ({count:,})" if count else str(value)
            options.append({
                'id': str(value).lower().replace(' ', '_'),
                'label': label,
                'value': value
            })
        
        # Add "All" option
        options.append({
            'id': 'all',
            'label': f'All ({total_count:,} total)'
        })
        
        return options
    
    def _continue_without_filter(self, question: str, category: str) -> SynthesizedAnswer:
        """Continue processing without this filter (skip clarification)."""
        self.confirmed_facts[category] = 'all'
        return self.ask(question)  # Recursive call to continue
    
    def _request_employee_status_clarification(self, question: str) -> SynthesizedAnswer:
        """Ask for employee status clarification using ACTUAL values from filter_candidates."""
        
        # Get status options from filter_candidates (smarter selection)
        status_options = self._get_status_options_from_filter_candidates()
        
        if not status_options:
            # Fallback to generic options if no profile data
            status_options = [
                {'id': 'active', 'label': 'Active only', 'default': True},
                {'id': 'termed', 'label': 'Terminated only'},
                {'id': 'all', 'label': 'All employees'}
            ]
        
        return SynthesizedAnswer(
            question=question,
            answer="",
            confidence=0.0,
            structured_output={
                'type': 'clarification_needed',
                'questions': [{
                    'id': 'status',  # Use 'status' consistently (was 'employee_status')
                    'question': 'Which employees should I include?',
                    'type': 'radio',
                    'options': status_options
                }],
                'original_question': question,
                'detected_mode': 'search',
                'detected_domains': ['employees']
            },
            reasoning=['Need to know which employees to include']
        )
    
    def _get_status_options_from_filter_candidates(self) -> List[Dict]:
        """
        Get employee status options from filter_candidates.
        Prioritizes columns from employee-level tables (lower row counts).
        """
        status_candidates = self.filter_candidates.get('status', [])
        
        if not status_candidates:
            return []
        
        # Find the BEST status column:
        # 1. Prefer employment_status_code/employment_status over others
        # 2. Prefer tables with ~14k rows (employee-level) over 60k+ (transaction-level)
        best_candidate = None
        
        for candidate in status_candidates:
            col_name = candidate.get('column_name', candidate.get('column', '')).lower()
            total_count = candidate.get('distinct_count', candidate.get('total_count', 0))
            col_type = candidate.get('inferred_type', candidate.get('type', ''))
            
            # Skip transaction tables (too many rows per employee)
            if total_count > 20000:
                continue
            
            # Prefer employment_status columns
            if 'employment_status' in col_name:
                best_candidate = candidate
                break
            
            # termination_date is good but harder to show counts
            if col_type == 'date' and 'termination' in col_name:
                if not best_candidate:
                    best_candidate = candidate
                continue
            
            # Any categorical status column from employee-level table
            if not best_candidate and col_type == 'categorical':
                best_candidate = candidate
        
        if not best_candidate:
            # Fallback to first candidate
            best_candidate = status_candidates[0] if status_candidates else None
        
        if not best_candidate:
            return []
        
        col_name = best_candidate.get('column_name', best_candidate.get('column'))
        table_name = best_candidate.get('table_name', best_candidate.get('table', ''))
        logger.warning(f"[CLARIFICATION] Using status column: {col_name} from {table_name.split('__')[-1]}")
        
        col_type = best_candidate.get('inferred_type', best_candidate.get('type', ''))
        
        # Handle termination_date (date type)
        if col_type == 'date':
            total = best_candidate.get('distinct_count', best_candidate.get('total_count', 0))
            null_count = best_candidate.get('null_count', 0)
            active_count = null_count  # null termination_date = active
            termed_count = total - null_count
            
            return [
                {'id': 'active', 'label': f'Active only ({active_count:,} employees)', 'default': True},
                {'id': 'termed', 'label': f'Terminated only ({termed_count:,} employees)'},
                {'id': 'all', 'label': f'All employees ({total:,} total)'}
            ]
        
        # Handle categorical status column (A/T codes)
        values = best_candidate.get('distinct_values', best_candidate.get('values', []))
        distribution = best_candidate.get('value_distribution', best_candidate.get('distribution', {}))
        
        # FIXED: Use sum of distribution (employee count) not distinct_count (number of status codes)
        total = sum(distribution.values()) if distribution else best_candidate.get('total_count', 0)
        
        # Map codes to active/termed
        active_codes = ['A', 'ACTIVE', 'ACT']
        termed_codes = ['T', 'TERMINATED', 'TERM', 'I', 'INACTIVE']
        leave_codes = ['L', 'LEAVE', 'LOA']
        
        active_count = sum(distribution.get(v, 0) for v in values if str(v).upper() in active_codes)
        termed_count = sum(distribution.get(v, 0) for v in values if str(v).upper() in termed_codes)
        leave_count = sum(distribution.get(v, 0) for v in values if str(v).upper() in leave_codes)
        
        options = []
        if active_count > 0:
            options.append({'id': 'active', 'label': f'Active only ({active_count:,} employees)', 'default': True})
        if termed_count > 0:
            options.append({'id': 'termed', 'label': f'Terminated only ({termed_count:,} employees)'})
        if leave_count > 0:
            options.append({'id': 'leave', 'label': f'On Leave ({leave_count:,} employees)'})
        options.append({'id': 'all', 'label': f'All employees ({total:,} total)'})
        
        return options
    
    def _get_status_options_from_profiles(self) -> List[Dict]:
        """
        Get employee status options from actual profile data.
        This is the key Phase 2 feature - data-driven clarification.
        """
        if not self.schema:
            return []
        
        tables = self.schema.get('tables', [])
        
        # Look for status-related columns in the profiles
        status_patterns = ['status', 'employment_status', 'emp_status', 'employee_status', 
                          'employment_status_code', 'termination_date', 'term_date']
        
        for table in tables:
            categorical_cols = table.get('categorical_columns', [])
            column_profiles = table.get('column_profiles', {})
            
            # Check categorical columns for status-like values
            for cat_col in categorical_cols:
                col_name = cat_col.get('column', '').lower()
                
                # Is this a status column?
                if any(pattern in col_name for pattern in status_patterns):
                    values = cat_col.get('values', [])
                    distribution = cat_col.get('distribution', {})
                    
                    if values:
                        return self._build_status_options(values, distribution, col_name)
            
            # Also check column_profiles directly
            for col_name, profile in column_profiles.items():
                col_lower = col_name.lower()
                if any(pattern in col_lower for pattern in status_patterns):
                    if profile.get('is_categorical') and profile.get('distinct_values'):
                        values = profile['distinct_values']
                        distribution = profile.get('value_distribution', {})
                        return self._build_status_options(values, distribution, col_name)
        
        return []
    
    def _build_status_options(self, values: List[str], distribution: Dict, col_name: str) -> List[Dict]:
        """Build clarification options from actual data values."""
        options = []
        
        # Common status code mappings
        status_labels = {
            'A': 'Active', 'T': 'Terminated', 'L': 'Leave', 'I': 'Inactive',
            'ACTIVE': 'Active', 'TERMED': 'Terminated', 'TERM': 'Terminated',
            'LOA': 'Leave of Absence', 'LEAVE': 'Leave', 'INACTIVE': 'Inactive',
            'REG': 'Regular', 'TEMP': 'Temporary', 'PART': 'Part-time',
            'FT': 'Full-time', 'PT': 'Part-time'
        }
        
        # Build options with counts
        active_values = []
        termed_values = []
        other_values = []
        
        for val in values:
            val_upper = str(val).upper().strip()
            count = distribution.get(val, distribution.get(str(val), 0))
            
            # Categorize
            if val_upper in ['A', 'ACTIVE', 'ACT']:
                active_values.append((val, count))
            elif val_upper in ['T', 'TERMINATED', 'TERM', 'TERMED', 'I', 'INACTIVE']:
                termed_values.append((val, count))
            else:
                other_values.append((val, count))
        
        # Build options with actual counts
        if active_values:
            active_count = sum(c for _, c in active_values)
            active_codes = ', '.join(v for v, _ in active_values)
            options.append({
                'id': 'active',
                'label': f'Active only ({active_count:,} employees)',
                'codes': active_codes,
                'default': True
            })
        
        if termed_values:
            termed_count = sum(c for _, c in termed_values)
            termed_codes = ', '.join(v for v, _ in termed_values)
            options.append({
                'id': 'termed',
                'label': f'Terminated only ({termed_count:,} employees)',
                'codes': termed_codes
            })
        
        # Add "All" option with total
        total_count = sum(distribution.values()) if distribution else 0
        options.append({
            'id': 'all',
            'label': f'All employees ({total_count:,} total)'
        })
        
        # If we couldn't categorize well, show raw values
        if not active_values and not termed_values and other_values:
            options = []
            for val, count in sorted(other_values, key=lambda x: -x[1])[:5]:
                label = status_labels.get(str(val).upper(), str(val))
                options.append({
                    'id': str(val).lower(),
                    'label': f'{label} ({count:,})',
                    'code': val
                })
            options.append({'id': 'all', 'label': f'All ({total_count:,} total)'})
        
        logger.info(f"[CLARIFICATION] Built {len(options)} options from {col_name}: {[o['id'] for o in options]}")
        return options
    
    # =========================================================================
    # ANALYTICAL CLARIFICATION SYSTEM
    # Smart validation: analyze data first, ask intelligent questions
    # =========================================================================
    
    def _analyze_validation_scope(
        self, 
        question: str, 
        validation_table: str,
        validation_columns: List[str]
    ) -> Dict:
        """
        Analyze validation data to understand scope BEFORE asking questions.
        
        A real consultant looks at the data first, then asks smart questions.
        
        Returns:
            {
                'needs_clarification': bool,
                'clarification': SynthesizedAnswer or None,
                'analysis': dict with findings,
                'smart_assumption': str or None,
                'scope_filter': dict or None
            }
        """
        q_lower = question.lower()
        result = {
            'needs_clarification': False,
            'clarification': None,
            'analysis': {},
            'smart_assumption': None,
            'scope_filter': None
        }
        
        # Detect validation domain
        domain_config = _detect_validation_domain(question)
        domain_name = domain_config.get('name', 'rates') if domain_config else 'rates'
        
        # Check if we already have a confirmed validation scope
        scope_confirm = self.confirmed_facts.get('validation_scope_confirm')
        scope_company = self.confirmed_facts.get('validation_scope_company')
        
        logger.warning(f"[ANALYTICAL] Checking scope - confirm={scope_confirm}, company={scope_company}")
        
        if scope_confirm == 'yes':
            # User confirmed single-company focus - get the stored context
            if hasattr(self, '_validation_scope_context'):
                ctx = self._validation_scope_context
                result['scope_filter'] = {
                    'column': ctx.get('company_col'),
                    'value': ctx.get('primary_code')
                }
                result['smart_assumption'] = f"Reviewing {domain_name} for **{ctx.get('primary_name', ctx.get('primary_code'))}**"
                logger.warning(f"[ANALYTICAL] Applying confirmed scope filter: {result['scope_filter']}")
            return result
        elif scope_confirm == 'no_all':
            # User wants to review all companies
            result['smart_assumption'] = f"Reviewing {domain_name} for **all companies**"
            logger.warning(f"[ANALYTICAL] User requested all companies review")
            return result
        elif scope_company and scope_company != '__all__':
            # User selected a specific company from multi-company list
            col = getattr(self, '_validation_company_col', 'component_company_code')
            result['scope_filter'] = {
                'column': col,
                'value': scope_company
            }
            result['smart_assumption'] = f"Reviewing {domain_name} for selected company"
            logger.warning(f"[ANALYTICAL] User selected company: {scope_company}, filter col: {col}")
            return result
        elif scope_company == '__all__':
            result['smart_assumption'] = f"Reviewing {domain_name} for **all companies**"
            logger.warning(f"[ANALYTICAL] User selected all companies")
            return result
        
        # Check if this is a validation-worthy question using the domain config
        if not domain_config:
            # Also check for generic tax/rate validation
            is_tax = any(kw in q_lower for kw in ['tax', 'rate', 'fein', 'ein', 'correct', 'valid'])
            if not is_tax:
                return result
        
        # Get keywords to filter for this domain
        domain_keywords = domain_config.get('keywords', ['sui', 'suta']) if domain_config else ['sui', 'suta']
        domain_key = domain_config.get('key', '') if domain_config else ''
        
        # For workers comp, the whole table IS WC - don't filter by keywords
        is_non_tax_domain = domain_key in ['workers_comp', 'state_withholding', 'local_tax']
        
        # Analyze the data to understand the scope
        try:
            # Find company/FEIN column
            company_cols = [c for c in validation_columns if any(
                x in c.lower() for x in ['company_code', 'company_name', 'fein', 'ein', 'id_number']
            )]
            
            # Find tax code column (for filtering) - but not for WC domains
            tax_code_cols = []
            if not is_non_tax_domain:
                tax_code_cols = [c for c in validation_columns if any(
                    x in c.lower() for x in ['tax_code', 'tax_desc', 'type_of_tax']
                )]
            
            # Find rate column
            rate_cols = [c for c in validation_columns if any(
                x in c.lower() for x in ['rate', 'contribution', 'percent']
            )]
            
            # Build keyword filter for SQL (only for tax domains)
            keyword_patterns = [kw.upper() for kw in domain_keywords] if not is_non_tax_domain else []
            
            # Analyze by company/FEIN
            if company_cols:
                company_col = company_cols[0]
                name_col = next((c for c in company_cols if 'name' in c.lower()), company_col)
                
                # Get breakdown by company with domain-specific record count
                if tax_code_cols and keyword_patterns:
                    like_clauses = ' OR '.join(f'UPPER("{tax_code_cols[0]}") LIKE \'%{kw}%\'' for kw in keyword_patterns)
                    sql = f'''
                        SELECT "{company_col}" as code, 
                               "{name_col}" as name,
                               COUNT(*) as total_records,
                               COUNT(CASE WHEN {like_clauses} THEN 1 END) as domain_records
                        FROM "{validation_table}"
                        GROUP BY "{company_col}", "{name_col}"
                        ORDER BY domain_records DESC
                    '''
                else:
                    # For non-tax domains (workers comp, etc.), all records ARE domain records
                    sql = f'''
                        SELECT "{company_col}" as code,
                               "{name_col}" as name, 
                               COUNT(*) as total_records,
                               COUNT(*) as domain_records
                        FROM "{validation_table}"
                        GROUP BY "{company_col}", "{name_col}"
                        ORDER BY total_records DESC
                    '''
                
                rows = self.structured_handler.query(sql)
                
                if rows:
                    result['analysis']['companies'] = rows
                    
                    # Smart analysis - domain-agnostic
                    companies_with_records = [r for r in rows if r.get('domain_records', 0) > 0]
                    companies_without_records = [r for r in rows if r.get('domain_records', 0) == 0]
                    
                    if len(companies_with_records) == 1 and len(companies_without_records) > 0:
                        # Only one company has records - ASK if that's the right scope
                        main_company = companies_with_records[0]
                        fein = main_company.get('code', '')
                        name = main_company.get('name', fein)
                        record_count = main_company.get('domain_records', 0)
                        
                        # Format FEIN nicely if it looks like one
                        fein_display = fein
                        if fein and len(str(fein).replace('-', '')) == 9:
                            fein_clean = str(fein).replace('-', '')
                            fein_display = f"{fein_clean[:2]}-{fein_clean[2:]}"
                        
                        result['needs_clarification'] = True
                        
                        # Store context for when user confirms
                        self._validation_scope_context = {
                            'company_col': company_col,
                            'primary_code': fein,
                            'primary_name': name,
                            'record_count': record_count
                        }
                        self._validation_company_col = company_col
                        
                        result['clarification'] = SynthesizedAnswer(
                            question=question,
                            answer="",
                            confidence=0.0,
                            structured_output={
                                'type': 'clarification_needed',
                                'questions': [{
                                    'id': 'validation_scope_confirm',
                                    'question': (
                                        f"I found **{name}** (FEIN {fein_display}) has {record_count} {domain_name} configured, "
                                        f"while {len(companies_without_records)} other company/companies have none. "
                                        f"Is it safe to assume this is the only FEIN needing review?"
                                    ),
                                    'type': 'radio',
                                    'options': [
                                        {'id': 'yes', 'label': f'Yes, just review {name}', 'default': True},
                                        {'id': 'no_all', 'label': f'No, review all companies (some may need setup)'},
                                        {'id': 'no_other', 'label': 'No, let me specify which company'}
                                    ]
                                }],
                                'original_question': question,
                                'detected_mode': 'validate',
                                'context': {
                                    'primary_company': {'code': fein, 'name': name, 'record_count': record_count},
                                    'companies_without_records': [{'code': c.get('code'), 'name': c.get('name')} for c in companies_without_records]
                                }
                            },
                            reasoning=[f"Found {len(companies_with_records)} company with {domain_name}, {len(companies_without_records)} without"]
                        )
                        
                    elif len(companies_with_records) > 1:
                        # Multiple companies with records - need clarification but be smart about it
                        result['needs_clarification'] = True
                        
                        # Store context for when user selects
                        self._validation_company_col = company_col
                        
                        options = []
                        for comp in companies_with_records:
                            options.append({
                                'id': str(comp.get('code')),
                                'label': f"{comp.get('name', comp.get('code'))} ({comp.get('domain_records')} {domain_name})"
                            })
                        options.append({
                            'id': '__all__',
                            'label': f"Review all {len(companies_with_records)} companies"
                        })
                        
                        summary = ", ".join(
                            f"{c.get('name', c.get('code'))} ({c.get('domain_records')} rates)"
                            for c in companies_with_records[:3]
                        )
                        if len(companies_with_records) > 3:
                            summary += f" and {len(companies_with_records) - 3} more"
                        
                        result['clarification'] = SynthesizedAnswer(
                            question=question,
                            answer="",
                            confidence=0.0,
                            structured_output={
                                'type': 'clarification_needed',
                                'questions': [{
                                    'id': 'validation_scope_company',
                                    'question': f"I found {domain_name} for multiple companies: {summary}. Which would you like me to review?",
                                    'type': 'radio',
                                    'options': options
                                }],
                                'original_question': question,
                                'detected_mode': 'validate'
                            },
                            reasoning=[f"Multiple companies have {domain_name} configured"]
                        )
                    
                    elif len(companies_with_records) == 0 and len(companies_without_records) > 0:
                        # No records found at all - that's the finding!
                        result['analysis']['finding'] = 'no_records'
                        result['smart_assumption'] = (
                            f"⚠️ **No {domain_name} found** for any of the {len(companies_without_records)} companies. "
                            f"This may be a configuration issue."
                        )
            
            # Analyze rate values if we have them
            if rate_cols and not result.get('needs_clarification'):
                rate_col = rate_cols[0]
                
                # Build keyword filter for rate stats query
                if tax_code_cols and keyword_patterns:
                    like_clauses = ' OR '.join(f'UPPER("{tax_code_cols[0]}") LIKE \'%{kw}%\'' for kw in keyword_patterns)
                    where_clause = f"WHERE {like_clauses}"
                else:
                    where_clause = ""
                
                # Get rate statistics
                sql = f'''
                    SELECT 
                        COUNT(*) as total,
                        COUNT(CASE WHEN "{rate_col}" IS NULL OR "{rate_col}" = '' OR "{rate_col}" = 0 THEN 1 END) as zero_or_null,
                        MIN(CAST("{rate_col}" AS DOUBLE)) as min_rate,
                        MAX(CAST("{rate_col}" AS DOUBLE)) as max_rate,
                        AVG(CAST("{rate_col}" AS DOUBLE)) as avg_rate
                    FROM "{validation_table}"
                    {where_clause}
                '''
                try:
                    stats = self.structured_handler.query(sql)
                    if stats:
                        result['analysis']['rate_stats'] = stats[0]
                except:
                    pass
                    
        except Exception as e:
            logger.warning(f"[ANALYTICAL] Scope analysis failed: {e}")
        
        return result
    
    def _analyze_temporal_context(
        self, 
        rows: List[Dict], 
        golive_date: Optional[str] = None
    ) -> List[Dict]:
        """
        Analyze data for temporal issues - stale rates, missing updates, etc.
        
        Returns list of temporal findings.
        """
        findings = []
        
        if not rows:
            return findings
        
        # Look for date columns
        date_cols = []
        for key in rows[0].keys():
            key_lower = key.lower()
            if any(d in key_lower for d in ['date', 'effective', 'changed', 'updated', 'created']):
                date_cols.append(key)
        
        if not date_cols:
            return findings
        
        from datetime import datetime, timedelta
        
        # Analyze effective dates
        effective_col = next((c for c in date_cols if 'effective' in c.lower()), date_cols[0])
        
        # Find entity column for grouping
        entity_col = None
        for key in rows[0].keys():
            key_lower = key.lower()
            if any(e in key_lower for e in ['state', 'jurisdiction', 'tax_code', 'desc']):
                entity_col = key
                break
        
        # Analyze dates
        now = datetime.now()
        current_year = now.year
        
        stale_entities = []  # Not updated this year
        old_entities = []    # 2+ years old
        recent_entities = [] # Updated this year
        
        for row in rows:
            eff_date_str = row.get(effective_col)
            entity = row.get(entity_col, 'Unknown') if entity_col else 'Record'
            
            if not eff_date_str:
                continue
            
            try:
                # Parse date
                if isinstance(eff_date_str, str):
                    eff_date = None
                    for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%Y-%m-%dT%H:%M:%S']:
                        try:
                            eff_date = datetime.strptime(eff_date_str[:10], fmt[:10])
                            break
                        except:
                            continue
                    if not eff_date:
                        continue
                else:
                    eff_date = eff_date_str
                
                year_diff = current_year - eff_date.year
                
                if year_diff >= 2:
                    old_entities.append({'entity': entity, 'date': eff_date_str, 'years_old': year_diff})
                elif year_diff == 1:
                    stale_entities.append({'entity': entity, 'date': eff_date_str})
                else:
                    recent_entities.append({'entity': entity, 'date': eff_date_str})
                    
            except Exception as e:
                continue
        
        # Generate findings
        if old_entities:
            findings.append({
                'type': 'error',
                'severity': 'high',
                'title': f'{len(old_entities)} Rates Over 2 Years Old',
                'message': f"SUI rates change annually. These haven't been updated in 2+ years.",
                'entities': old_entities[:5],
                'action': 'Update immediately with current state unemployment rate notices'
            })
        
        if stale_entities:
            findings.append({
                'type': 'warning', 
                'severity': 'medium',
                'title': f'{len(stale_entities)} Rates From Last Year',
                'message': f"These rates may need {current_year} updates.",
                'entities': stale_entities[:5],
                'action': f'Verify against {current_year} state unemployment rate notices'
            })
        
        if recent_entities:
            findings.append({
                'type': 'success',
                'severity': 'low', 
                'title': f'{len(recent_entities)} Rates Updated This Year',
                'message': f"Recently updated - verify they match your rate notices.",
                'entities': recent_entities[:3]
            })
        
        return findings
    
    def _validate_rate_values(self, rows: List[Dict], domain_config: Dict = None) -> List[Dict]:
        """
        Validate rate values against domain-specific ranges.
        
        Uses VALIDATION_CONFIG to determine valid ranges for each domain.
        Works for SUI, FUTA, Workers Comp, and any other rate-based validation.
        
        Args:
            rows: Data rows to validate
            domain_config: Config dict from VALIDATION_CONFIG (or uses SUI defaults)
        """
        findings = []
        
        if not rows:
            return findings
        
        # Default to SUI config if not specified
        if not domain_config:
            domain_config = VALIDATION_CONFIG.get('sui', {})
        
        domain_name = domain_config.get('name', 'Rate')
        domain_key = domain_config.get('key', 'sui')
        rate_min, rate_max = domain_config.get('rate_range', (0.001, 0.20))
        high_rate_entities = domain_config.get('high_rate_entities', [])
        high_rate_max = domain_config.get('high_rate_max', rate_max * 1.1)
        zero_severity = domain_config.get('zero_severity', 'medium')
        
        # Find rate column
        rate_col = None
        for key in rows[0].keys():
            key_lower = key.lower()
            if any(r in key_lower for r in ['rate', 'contribution', 'percent']):
                rate_col = key
                break
        
        if not rate_col:
            return findings
        
        # Find entity column (state/tax code/class)
        entity_col = None
        for key in rows[0].keys():
            key_lower = key.lower()
            if any(e in key_lower for e in ['state', 'jurisdiction', 'tax_code', 'desc', 'class', 'code']):
                entity_col = key
                break
        
        issues = []
        valid_rates = []
        zero_rates = []
        
        for row in rows:
            rate_val = row.get(rate_col)
            entity = row.get(entity_col, 'Unknown') if entity_col else 'Record'
            
            if rate_val is None or rate_val == '':
                issues.append({'entity': entity, 'issue': 'Missing rate', 'value': 'blank'})
                continue
            
            try:
                rate = float(rate_val)
                
                # Check if this is a high-rate entity (state/class)
                is_high_rate = any(st in str(entity).upper() for st in high_rate_entities) if high_rate_entities else False
                max_threshold = high_rate_max if is_high_rate else rate_max
                
                if rate == 0:
                    zero_rates.append({'entity': entity, 'value': '0%'})
                elif rate > 1:
                    # Stored as percentage (e.g., 2.5 = 2.5%)
                    pct_max = max_threshold * 100
                    if rate > pct_max:
                        issues.append({'entity': entity, 'issue': 'Rate unusually high', 'value': f'{rate}%'})
                    else:
                        valid_rates.append({'entity': entity, 'value': f'{rate}%', 'raw': rate})
                else:
                    # Stored as decimal (e.g., 0.025 = 2.5%)
                    pct = rate * 100
                    if rate > max_threshold:
                        issues.append({'entity': entity, 'issue': 'Rate unusually high', 'value': f'{pct:.2f}%'})
                    elif rate < 0.0001 and rate > 0:
                        issues.append({'entity': entity, 'issue': 'Rate suspiciously low', 'value': f'{pct:.4f}%'})
                    else:
                        valid_rates.append({'entity': entity, 'value': f'{pct:.2f}%', 'raw': rate})
                    
            except (ValueError, TypeError):
                issues.append({'entity': entity, 'issue': 'Invalid format', 'value': str(rate_val)})
        
        # Generate findings with domain-specific messaging
        if issues:
            findings.append({
                'type': 'error',
                'severity': 'high',
                'title': f'{len(issues)} {domain_name} Issues',
                'message': 'Found rates that need review',
                'details': issues[:10],
                'action': f'Verify against your {domain_name.lower()} notices'
            })
        
        if zero_rates:
            zero_messages = {
                'sui': 'Zero SUI rates - verify this is intentional (excellent experience rating)',
                'futa': 'Zero FUTA rates are almost always incorrect',
                'workers_comp': 'Zero WC rates - verify exemption status',
                'state_withholding': 'Zero state withholding - may be valid for no-income-tax states',
                'local_tax': 'Zero local tax - may be valid if no local tax applies',
            }
            zero_message = zero_messages.get(domain_key, f'Zero {domain_name} rates found')
            
            findings.append({
                'type': 'warning' if zero_severity in ['medium', 'low'] else 'error',
                'severity': zero_severity,
                'title': f'{len(zero_rates)} Zero Rates',
                'message': zero_message,
                'details': zero_rates[:5],
                'action': 'Confirm 0% is correct or enter actual rate'
            })
        
        if valid_rates:
            rates = [r['raw'] for r in valid_rates]
            if max(rates) < 1:
                min_pct, max_pct = min(rates) * 100, max(rates) * 100
            else:
                min_pct, max_pct = min(rates), max(rates)
            
            findings.append({
                'type': 'success',
                'severity': 'info',
                'title': f'{len(valid_rates)} Rates Valid',
                'message': f'Rates range from {min_pct:.2f}% to {max_pct:.2f}%',
                'action': f'Verify against your {domain_name.lower()} notices'
            })
        
        return findings
    
    def _validate_config(self, rows: List[Dict], domain_config: Dict) -> List[Dict]:
        """
        Validate configuration data (earnings, deductions, GL, etc.) - non-rate validation.
        
        Checks for completeness, consistency, and common setup issues.
        
        Args:
            rows: Data rows to validate
            domain_config: Config dict from VALIDATION_CONFIG
        """
        findings = []
        
        if not rows:
            findings.append({
                'type': 'warning',
                'severity': 'high',
                'title': 'No Records Found',
                'message': f"No {domain_config.get('name', 'configuration')} data found",
                'action': 'Verify data has been uploaded or configured'
            })
            return findings
        
        domain_key = domain_config.get('key', '')
        domain_name = domain_config.get('name', 'Configuration')
        checks = domain_config.get('checks', [])
        
        # Get column names
        columns = list(rows[0].keys()) if rows else []
        col_lower_map = {c.lower(): c for c in columns}
        
        # DATA QUALITY CHECK: Detect corrupted/garbage column names
        # If columns are "nan", "nan_1", "nan_2"... or "unnamed", "unnamed_1" the header parsing failed
        nan_cols = [c for c in columns if c.lower().startswith('nan') or c.lower() == 'nan']
        unnamed_cols = [c for c in columns if 'unnamed' in c.lower()]
        bad_cols = nan_cols + unnamed_cols
        
        if len(bad_cols) > 3:
            col_type = 'nan' if len(nan_cols) > len(unnamed_cols) else 'unnamed'
            findings.append({
                'type': 'error',
                'severity': 'high',
                'title': '⚠️ Data Quality Issue: Column Headers Missing',
                'message': f"Found {len(bad_cols)} columns with invalid names ('{col_type}') - header row was not parsed correctly during upload",
                'action': 'Re-upload the source file. Check for merged cells, multiple header rows, or non-standard formatting.',
                'details': [{'entity': 'Sample columns', 'issue': 'Invalid names', 'value': ', '.join(columns[:5])}]
            })
            # Still try to validate what we can, but flag the issue prominently
        
        # DATA QUALITY CHECK: Row count sanity
        expected_min_rows = domain_config.get('expected_min_rows', 50)  # Most config tables have 50+ rows
        if len(rows) < expected_min_rows and len(rows) < 30:
            # Check if first row looks like headers (common parsing issue)
            first_row_values = list(rows[0].values()) if rows else []
            looks_like_header = any(isinstance(v, str) and len(v) > 10 and ' ' in v for v in first_row_values[:5])
            
            if looks_like_header:
                findings.append({
                    'type': 'warning',
                    'severity': 'medium',
                    'title': 'Possible Data Truncation',
                    'message': f"Only {len(rows)} rows found. First row may contain actual headers that weren't detected.",
                    'action': 'Verify source file has correct header row format',
                    'details': [{'entity': 'First row sample', 'issue': 'May be headers', 'value': str(first_row_values[:3])[:100]}]
                })
        
        # Find key columns
        code_col = None
        desc_col = None
        status_col = None
        
        for col in columns:
            c_lower = col.lower()
            if 'code' in c_lower and not code_col:
                code_col = col
            if any(d in c_lower for d in ['desc', 'name', 'title']) and not desc_col:
                desc_col = col
            if 'status' in c_lower or 'active' in c_lower:
                status_col = col
        
        # Run domain-specific checks
        if domain_key == 'earnings':
            findings.extend(self._validate_earnings(rows, columns, code_col, desc_col, status_col))
        elif domain_key == 'deductions':
            findings.extend(self._validate_deductions(rows, columns, code_col, desc_col, status_col))
        elif domain_key == 'gl_mapping':
            findings.extend(self._validate_gl_mapping(rows, columns))
        elif domain_key == 'tax_jurisdictions':
            findings.extend(self._validate_tax_jurisdictions(rows, columns))
        else:
            # Generic config validation
            findings.extend(self._validate_generic_config(rows, columns, code_col, desc_col, status_col, domain_name))
        
        # Add summary if no issues found
        if not findings or all(f.get('type') == 'success' for f in findings):
            findings.append({
                'type': 'success',
                'severity': 'info',
                'title': f'{len(rows)} Records Validated',
                'message': f'{domain_name} appears correctly configured',
                'action': 'Review detailed data to confirm'
            })
        
        return findings
    
    def _validate_earnings(self, rows: List[Dict], columns: List[str], code_col: str, desc_col: str, status_col: str) -> List[Dict]:
        """Validate earnings code configuration."""
        findings = []
        
        # Check for duplicates
        if code_col:
            codes = [r.get(code_col) for r in rows if r.get(code_col)]
            duplicates = [c for c in set(codes) if codes.count(c) > 1]
            if duplicates:
                findings.append({
                    'type': 'warning',
                    'severity': 'medium',
                    'title': f'{len(duplicates)} Duplicate Codes',
                    'message': 'Same code appears multiple times - may be intentional (by company) or error',
                    'details': [{'entity': d, 'issue': 'Duplicate code', 'value': f'{codes.count(d)} occurrences'} for d in duplicates[:5]],
                    'action': 'Verify duplicates are intentional (e.g., different companies)'
                })
        
        # Check for missing descriptions
        if desc_col:
            missing_desc = [r for r in rows if not r.get(desc_col)]
            if missing_desc:
                findings.append({
                    'type': 'warning',
                    'severity': 'low',
                    'title': f'{len(missing_desc)} Missing Descriptions',
                    'message': 'Earnings without descriptions are harder to identify',
                    'details': [{'entity': r.get(code_col, 'Unknown'), 'issue': 'No description', 'value': ''} for r in missing_desc[:5]],
                    'action': 'Add descriptions for clarity'
                })
        
        # Check for taxability columns
        tax_cols = [c for c in columns if any(t in c.lower() for t in ['tax', 'subject', 'exempt', 'fit', 'sit', 'fica'])]
        if not tax_cols:
            findings.append({
                'type': 'warning',
                'severity': 'medium',
                'title': 'Taxability Not Visible',
                'message': 'Tax treatment columns not found in this view',
                'action': 'Verify tax settings in earnings configuration'
            })
        
        # Check for inactive codes (if status column exists)
        if status_col:
            inactive = [r for r in rows if str(r.get(status_col, '')).lower() in ['inactive', 'i', 'n', 'no', '0', 'false']]
            active = [r for r in rows if r not in inactive]
            findings.append({
                'type': 'info',
                'severity': 'info',
                'title': f'{len(active)} Active, {len(inactive)} Inactive',
                'message': f'Earnings code status breakdown',
            })
        
        return findings
    
    def _validate_deductions(self, rows: List[Dict], columns: List[str], code_col: str, desc_col: str, status_col: str) -> List[Dict]:
        """Validate deduction/benefit plan configuration."""
        findings = []
        
        # Check for vendor/payee columns
        vendor_cols = [c for c in columns if any(v in c.lower() for v in ['vendor', 'payee', 'carrier', 'provider'])]
        if vendor_cols:
            vendor_col = vendor_cols[0]
            missing_vendor = [r for r in rows if not r.get(vendor_col)]
            if missing_vendor:
                findings.append({
                    'type': 'warning',
                    'severity': 'medium',
                    'title': f'{len(missing_vendor)} Missing Vendors',
                    'message': 'Deductions without vendor may not remit correctly',
                    'details': [{'entity': r.get(code_col, 'Unknown'), 'issue': 'No vendor', 'value': ''} for r in missing_vendor[:5]],
                    'action': 'Add vendor/payee for proper remittance'
                })
        
        # Check for limit columns
        limit_cols = [c for c in columns if any(l in c.lower() for l in ['limit', 'max', 'annual', 'goal'])]
        if limit_cols:
            limit_col = limit_cols[0]
            no_limit = [r for r in rows if not r.get(limit_col) or r.get(limit_col) == 0]
            # Pre-tax deductions typically need limits
            pretax_cols = [c for c in columns if 'pretax' in c.lower() or 'pre_tax' in c.lower()]
            if pretax_cols and no_limit:
                findings.append({
                    'type': 'info',
                    'severity': 'low',
                    'title': f'{len(no_limit)} Without Limits',
                    'message': 'Some deductions have no annual limit set',
                    'action': 'Verify pre-tax deductions have appropriate IRS limits'
                })
        
        # Check for duplicates
        if code_col:
            codes = [r.get(code_col) for r in rows if r.get(code_col)]
            duplicates = [c for c in set(codes) if codes.count(c) > 1]
            if duplicates:
                findings.append({
                    'type': 'warning',
                    'severity': 'medium',
                    'title': f'{len(duplicates)} Duplicate Codes',
                    'message': 'Same deduction code appears multiple times',
                    'details': [{'entity': d, 'issue': 'Duplicate', 'value': f'{codes.count(d)}x'} for d in duplicates[:5]],
                    'action': 'Verify duplicates are for different companies'
                })
        
        return findings
    
    def _validate_gl_mapping(self, rows: List[Dict], columns: List[str]) -> List[Dict]:
        """Validate GL mapping configuration."""
        findings = []
        
        # Find account column
        acct_cols = [c for c in columns if any(a in c.lower() for a in ['account', 'acct', 'gl_', 'ledger'])]
        
        if not acct_cols:
            findings.append({
                'type': 'warning',
                'severity': 'medium',
                'title': 'Account Column Not Found',
                'message': 'Could not identify GL account column',
                'action': 'Verify GL mapping data structure'
            })
            return findings
        
        acct_col = acct_cols[0]
        
        # Check for blank accounts
        blank_accounts = [r for r in rows if not r.get(acct_col) or str(r.get(acct_col)).strip() == '']
        if blank_accounts:
            # Try to find what's unmapped
            type_col = next((c for c in columns if 'type' in c.lower() or 'code' in c.lower()), None)
            findings.append({
                'type': 'error',
                'severity': 'high',
                'title': f'{len(blank_accounts)} Unmapped Items',
                'message': 'Items without GL accounts will not post to ledger',
                'details': [{'entity': r.get(type_col, f'Row {i}'), 'issue': 'No GL account', 'value': ''} for i, r in enumerate(blank_accounts[:5])],
                'action': 'Assign GL accounts to all payroll items'
            })
        
        # Check account format consistency
        accounts = [str(r.get(acct_col, '')) for r in rows if r.get(acct_col)]
        if accounts:
            # Check if all accounts have similar structure
            separators = ['-', '.', '_', ' ']
            sep_counts = {s: sum(1 for a in accounts if s in a) for s in separators}
            main_sep = max(sep_counts, key=sep_counts.get) if any(sep_counts.values()) else None
            
            if main_sep and sep_counts[main_sep] > 0:
                segment_counts = [len(a.split(main_sep)) for a in accounts if main_sep in a]
                if segment_counts and len(set(segment_counts)) > 1:
                    findings.append({
                        'type': 'warning',
                        'severity': 'medium',
                        'title': 'Inconsistent Account Format',
                        'message': f'Account segment counts vary ({min(segment_counts)} to {max(segment_counts)} segments)',
                        'action': 'Verify account string structure is consistent'
                    })
        
        # Count mapped records
        mapped = len(rows) - len(blank_accounts)
        if mapped > 0:
            findings.append({
                'type': 'success',
                'severity': 'info',
                'title': f'{mapped} Items Mapped',
                'message': 'GL accounts assigned',
            })
        
        return findings
    
    def _validate_tax_jurisdictions(self, rows: List[Dict], columns: List[str]) -> List[Dict]:
        """Validate tax jurisdiction setup."""
        findings = []
        
        # Find state column
        state_cols = [c for c in columns if any(s in c.lower() for s in ['state', 'jurisdiction', 'province'])]
        
        if not state_cols:
            findings.append({
                'type': 'warning',
                'severity': 'medium',
                'title': 'State Column Not Found',
                'message': 'Could not identify jurisdiction column',
            })
            return findings
        
        state_col = state_cols[0]
        states = set(r.get(state_col) for r in rows if r.get(state_col))
        
        # Find tax ID columns
        id_cols = [c for c in columns if any(i in c.lower() for i in ['id', 'ein', 'fein', 'account', 'registration'])]
        
        if id_cols:
            id_col = id_cols[0]
            missing_id = [r for r in rows if r.get(state_col) and not r.get(id_col)]
            if missing_id:
                findings.append({
                    'type': 'warning',
                    'severity': 'medium',
                    'title': f'{len(missing_id)} Missing Tax IDs',
                    'message': 'Jurisdictions without employer tax ID',
                    'details': [{'entity': r.get(state_col), 'issue': 'No tax ID', 'value': ''} for r in missing_id[:5]],
                    'action': 'Add employer tax registration numbers'
                })
        
        findings.append({
            'type': 'info',
            'severity': 'info',
            'title': f'{len(states)} Jurisdictions Configured',
            'message': f'Tax setup found for: {", ".join(sorted(list(states)[:10]))}{"..." if len(states) > 10 else ""}',
        })
        
        return findings
    
    def _validate_generic_config(self, rows: List[Dict], columns: List[str], code_col: str, desc_col: str, status_col: str, domain_name: str) -> List[Dict]:
        """Generic configuration validation for unknown domain types."""
        findings = []
        
        # Basic completeness check
        if code_col:
            blank_codes = [r for r in rows if not r.get(code_col)]
            if blank_codes:
                findings.append({
                    'type': 'warning',
                    'severity': 'medium',
                    'title': f'{len(blank_codes)} Records Without Code',
                    'message': 'Some records missing identifier',
                    'action': 'Review records without codes'
                })
        
        # Status breakdown if available
        if status_col:
            status_values = {}
            for r in rows:
                status = str(r.get(status_col, 'Unknown'))
                status_values[status] = status_values.get(status, 0) + 1
            
            status_summary = ', '.join(f'{v}: {c}' for v, c in sorted(status_values.items(), key=lambda x: -x[1])[:5])
            findings.append({
                'type': 'info',
                'severity': 'info',
                'title': 'Status Breakdown',
                'message': status_summary,
            })
        
        return findings
    
    def _format_consultant_response(
        self, 
        question: str,
        rows: List[Dict],
        temporal_findings: List[Dict],
        rate_findings: List[Dict],
        smart_assumption: Optional[str],
        table_name: str,
        domain_config: Dict = None
    ) -> str:
        """
        Format findings like a real consultant - lead with the answer.
        Also stores export data for download capability.
        """
        parts = []
        
        # Get domain name for export
        domain_name = domain_config.get('name', 'Validation') if domain_config else 'Validation'
        domain_key = domain_config.get('key', 'validation') if domain_config else 'validation'
        
        # Smart assumption first if we made one
        if smart_assumption:
            parts.append(smart_assumption)
            parts.append("")
        
        total_records = len(rows)
        all_findings = temporal_findings + rate_findings
        
        errors = [f for f in all_findings if f.get('severity') == 'high']
        warnings = [f for f in all_findings if f.get('severity') == 'medium']
        good = [f for f in all_findings if f.get('severity') in ['low', 'info']]
        
        # Lead with the verdict
        if errors:
            parts.append(f"🔴 **{len(errors)} issues found that need attention**")
        elif warnings:
            parts.append(f"🟡 **Rates look okay but {len(warnings)} items should be verified**")
        elif good:
            parts.append(f"✅ **Rates appear correctly configured** ({total_records} checked)")
        else:
            parts.append(f"ℹ️ **{total_records} rate records reviewed**")
        
        parts.append("")
        
        # Errors first
        for finding in errors:
            parts.append(f"**{finding['title']}**")
            parts.append(f"{finding['message']}")
            if finding.get('details'):
                for detail in finding['details'][:5]:
                    parts.append(f"  • {detail.get('entity')}: {detail.get('issue')} ({detail.get('value')})")
            if finding.get('action'):
                parts.append(f"  → *{finding['action']}*")
            parts.append("")
        
        # Then warnings
        for finding in warnings:
            parts.append(f"**{finding['title']}**")
            parts.append(f"{finding['message']}")
            if finding.get('entities'):
                entities = finding['entities'][:3]
                entity_list = ", ".join(e.get('entity', str(e)) if isinstance(e, dict) else str(e) for e in entities)
                if len(finding['entities']) > 3:
                    entity_list += f" (+{len(finding['entities']) - 3} more)"
                parts.append(f"  • Affected: {entity_list}")
            if finding.get('action'):
                parts.append(f"  → *{finding['action']}*")
            parts.append("")
        
        # Good news brief
        if good and not errors:
            for finding in good:
                parts.append(f"✓ {finding['title']}: {finding['message']}")
        
        # Store export data for later retrieval
        self._last_validation_export = {
            'rows': rows,
            'columns': list(rows[0].keys()) if rows else [],
            'findings': all_findings,
            'table_name': table_name,
            'sql': getattr(self, 'last_executed_sql', None),
            'total_records': total_records,
            'domain_name': domain_name,
            'domain_key': domain_key
        }
        
        # Offer the data with export hint
        parts.append("")
        parts.append(f"📊 **{total_records} records available** - say \"export\" or \"download\" to get the full data")
        
        return "\n".join(parts)
    
    def _get_status_column_and_codes(self, status_filter: str) -> Tuple[Optional[str], List[str]]:
        """
        Get the actual column name and codes to use for filtering.
        Returns (column_name, [list of codes])
        """
        if not self.schema:
            return None, []
        
        tables = self.schema.get('tables', [])
        status_patterns = ['status', 'employment_status', 'emp_status', 'employee_status', 'employment_status_code']
        
        for table in tables:
            categorical_cols = table.get('categorical_columns', [])
            column_profiles = table.get('column_profiles', {})
            
            for cat_col in categorical_cols:
                col_name = cat_col.get('column', '')
                col_lower = col_name.lower()
                
                if any(pattern in col_lower for pattern in status_patterns):
                    values = cat_col.get('values', [])
                    
                    # Find matching codes based on status_filter
                    if status_filter == 'active':
                        codes = [v for v in values if str(v).upper() in ['A', 'ACTIVE', 'ACT']]
                    elif status_filter == 'termed':
                        codes = [v for v in values if str(v).upper() in ['T', 'TERMINATED', 'TERM', 'TERMED', 'I', 'INACTIVE']]
                    else:
                        # Check if filter matches a specific code
                        codes = [v for v in values if str(v).lower() == status_filter.lower()]
                    
                    if codes:
                        return col_name, codes
            
            # Also check column_profiles
            for col_name, profile in column_profiles.items():
                col_lower = col_name.lower()
                if any(pattern in col_lower for pattern in status_patterns):
                    values = profile.get('distinct_values', [])
                    
                    if status_filter == 'active':
                        codes = [v for v in values if str(v).upper() in ['A', 'ACTIVE', 'ACT']]
                    elif status_filter == 'termed':
                        codes = [v for v in values if str(v).upper() in ['T', 'TERMINATED', 'TERM', 'TERMED', 'I', 'INACTIVE']]
                    else:
                        codes = [v for v in values if str(v).lower() == status_filter.lower()]
                    
                    if codes:
                        return col_name, codes
        
        return None, []
    
    def _build_filter_instructions(self, relevant_tables: List[Dict]) -> str:
        """
        Build SQL filter instructions from confirmed_facts and filter_candidates.
        Uses profile data to generate accurate WHERE clauses.
        """
        filters = []
        
        # STATUS FILTER
        status_filter = self.confirmed_facts.get('status')
        logger.warning(f"[SQL-GEN] Building filters. status={status_filter}, all_facts={self.confirmed_facts}")
        
        if status_filter and status_filter != 'all':
            # Use SAME logic as _get_status_options_from_filter_candidates to pick column
            status_candidates = self.filter_candidates.get('status', [])
            best_candidate = None
            
            for candidate in status_candidates:
                col_name = candidate.get('column_name', candidate.get('column', '')).lower()
                total_count = candidate.get('distinct_count', candidate.get('total_count', 0))
                col_type = candidate.get('inferred_type', candidate.get('type', ''))
                
                # Skip transaction tables (too many rows per employee)
                if total_count > 20000:
                    continue
                
                # Prefer employment_status columns (categorical with A/T codes)
                if 'employment_status' in col_name:
                    best_candidate = candidate
                    break
                
                # termination_date is fallback
                if col_type == 'date' and 'termination' in col_name:
                    if not best_candidate:
                        best_candidate = candidate
                    continue
                
                # Any categorical status column from employee-level table
                if not best_candidate and col_type == 'categorical':
                    best_candidate = candidate
            
            if not best_candidate and status_candidates:
                best_candidate = status_candidates[0]
            
            if best_candidate:
                col_name = best_candidate.get('column_name', best_candidate.get('column'))
                col_type = best_candidate.get('inferred_type', best_candidate.get('type'))
                values = best_candidate.get('distinct_values', best_candidate.get('values', []))
                
                logger.warning(f"[SQL-GEN] Status candidate: col={col_name}, type={col_type}")
                
                if col_type == 'date':  # termination_date
                    if status_filter == 'active':
                        filters.append(f"({col_name} IS NULL OR {col_name} = '' OR CAST({col_name} AS VARCHAR) = '')")
                    elif status_filter == 'termed':
                        filters.append(f"({col_name} IS NOT NULL AND {col_name} != '' AND CAST({col_name} AS VARCHAR) != '')")
                else:  # categorical status code
                    # Find matching codes
                    if status_filter == 'active':
                        codes = [v for v in values if str(v).upper() in ['A', 'ACTIVE', 'ACT']]
                    elif status_filter == 'termed':
                        codes = [v for v in values if str(v).upper() in ['T', 'TERMINATED', 'TERM', 'TERMED', 'I', 'INACTIVE']]
                    elif status_filter == 'leave':
                        codes = [v for v in values if str(v).upper() in ['L', 'LEAVE', 'LOA']]
                    else:
                        codes = [v for v in values if str(v).lower() == status_filter.lower()]
                    
                    if codes:
                        codes_str = ', '.join(f"'{c}'" for c in codes)
                        filters.append(f"{col_name} IN ({codes_str})")
                    else:
                        logger.warning(f"[SQL-GEN] No matching codes for status={status_filter} in values={values}")
            else:
                # Last resort fallback: look for termination_date in tables
                for table in relevant_tables:
                    columns = table.get('columns', [])
                    for col in columns:
                        col_name = col.get('name', str(col)) if isinstance(col, dict) else str(col)
                        if 'termination_date' in col_name.lower():
                            if status_filter == 'active':
                                filters.append(f"({col_name} IS NULL OR {col_name} = '')")
                            elif status_filter == 'termed':
                                filters.append(f"({col_name} IS NOT NULL AND {col_name} != '')")
                            break
        
        # COMPANY FILTER
        company_filter = self.confirmed_facts.get('company')
        if company_filter and company_filter != 'all':
            company_candidates = self.filter_candidates.get('company', [])
            if company_candidates:
                col_name = company_candidates[0].get('column_name', company_candidates[0].get('column'))
                filters.append(f"{col_name} = '{company_filter}'")
        
        # LOCATION FILTER
        location_filter = self.confirmed_facts.get('location')
        if location_filter and location_filter != 'all':
            location_candidates = self.filter_candidates.get('location', [])
            
            # Find a VALID location column (reject routing numbers, bank fields, etc.)
            # This is a safety net for cached profiles from before the profiler fix
            location_positive = ['state', 'province', 'stateprovince', 'location', 'region', 'city', 'county', 'country', 'site', 'geo']
            location_negative = ['routing', 'bank', 'account', 'aba', 'swift', 'transit', 'branch_number', 'bsb']
            
            valid_col = None
            valid_table = None
            
            # First try filter_candidates
            for candidate in location_candidates:
                col_name = candidate.get('column_name', candidate.get('column', ''))
                col_lower = col_name.lower()
                
                # Skip if column name contains invalid patterns
                if any(neg in col_lower for neg in location_negative):
                    logger.warning(f"[SQL-GEN] Skipping invalid location column: {col_name}")
                    continue
                
                # Prefer columns with location-related names
                if any(pos in col_lower for pos in location_positive):
                    valid_col = col_name
                    valid_table = candidate.get('table_name', candidate.get('table'))
                    break
                
                # Accept as fallback if no obvious red flags
                if not valid_col:
                    valid_col = col_name
                    valid_table = candidate.get('table_name', candidate.get('table'))
            
            # Fallback: search schema for state/province columns if no valid candidate
            if not valid_col and self.schema:
                for table_name, table_info in self.schema.items():
                    columns = table_info.get('columns', [])
                    for col in columns:
                        col_lower = col.lower() if isinstance(col, str) else str(col).lower()
                        if any(pos in col_lower for pos in ['state', 'province', 'stateprovince']):
                            valid_col = col
                            valid_table = table_name
                            logger.warning(f"[SQL-GEN] Found location column from schema: {table_name}.{col}")
                            break
                    if valid_col:
                        break
            
            if valid_col:
                filters.append(f"{valid_col} = '{location_filter}'")
                logger.warning(f"[SQL-GEN] Location filter: {valid_col} = '{location_filter}'")
            else:
                logger.warning(f"[SQL-GEN] No valid location column found, skipping location filter")
        
        # PAY TYPE FILTER
        pay_type_filter = self.confirmed_facts.get('pay_type')
        if pay_type_filter and pay_type_filter != 'all':
            pay_candidates = self.filter_candidates.get('pay_type', [])
            if pay_candidates:
                col_name = pay_candidates[0].get('column_name', pay_candidates[0].get('column'))
                values = pay_candidates[0].get('distinct_values', pay_candidates[0].get('values', []))
                # Map common terms to actual codes
                if pay_type_filter in ['hourly', 'h']:
                    codes = [v for v in values if str(v).upper() in ['H', 'HOURLY']]
                elif pay_type_filter in ['salary', 'salaried', 's']:
                    codes = [v for v in values if str(v).upper() in ['S', 'SALARY', 'SALARIED']]
                else:
                    codes = [pay_type_filter]
                if codes:
                    codes_str = ', '.join(f"'{c}'" for c in codes)
                    filters.append(f"{col_name} IN ({codes_str})")
        
        # EMPLOYEE TYPE FILTER
        emp_type_filter = self.confirmed_facts.get('employee_type')
        if emp_type_filter and emp_type_filter != 'all':
            emp_candidates = self.filter_candidates.get('employee_type', [])
            if emp_candidates:
                col_name = emp_candidates[0].get('column_name', emp_candidates[0].get('column'))
                values = emp_candidates[0].get('distinct_values', emp_candidates[0].get('values', []))
                # Map common terms
                if emp_type_filter in ['regular', 'reg']:
                    codes = [v for v in values if str(v).upper() in ['REG', 'REGULAR']]
                elif emp_type_filter in ['temp', 'temporary']:
                    codes = [v for v in values if str(v).upper() in ['TMP', 'TEMP', 'TEMPORARY']]
                elif emp_type_filter in ['contractor', 'contract']:
                    codes = [v for v in values if str(v).upper() in ['CON', 'CTR', 'CONTRACTOR']]
                else:
                    codes = [emp_type_filter]
                if codes:
                    codes_str = ', '.join(f"'{c}'" for c in codes)
                    filters.append(f"{col_name} IN ({codes_str})")
        
        # Build final filter string
        if filters:
            return "WHERE " + " AND ".join(filters)
        
        return ""
    
    def _fix_state_names_in_sql(self, sql: str) -> str:
        """
        Strip location/state filters from LLM-generated SQL.
        
        We handle location filters via data-driven injection from confirmed_facts.
        The LLM sometimes adds its own (wrong) location filters like ILIKE '%Texas%'.
        We strip these and let our filter injection handle it properly.
        """
        # Only strip if we have a confirmed location filter (we'll inject the right one)
        location_filter = self.confirmed_facts.get('location')
        if not location_filter or location_filter == 'all':
            return sql
        
        # Common location column patterns to strip (LLM might use any of these)
        location_col_patterns = [
            'stateprovince', 'state_province', 'state', 'province', 
            'work_state', 'home_state', 'location', 'work_location'
        ]
        
        modified = sql
        
        for col_name in location_col_patterns:
            # Strip patterns like: column ILIKE '%anything%'
            # This removes the LLM's location filter so our injection can add the correct one
            
            # Pattern 0: WHERE col ILIKE '...' AND ... → WHERE ...
            pattern0 = rf"WHERE\s+{re.escape(col_name)}\s+ILIKE\s+'%?[^']+%?'\s*AND\s*"
            modified = re.sub(pattern0, 'WHERE ', modified, flags=re.IGNORECASE)
            
            # Pattern 1: ... AND col ILIKE '...' AND ... → ... AND ...
            pattern1 = rf"{re.escape(col_name)}\s+ILIKE\s+'%?[^']+%?'\s*AND\s*"
            modified = re.sub(pattern1, '', modified, flags=re.IGNORECASE)
            
            # Pattern 2: ... AND col ILIKE '...' (at end) → ...
            pattern2 = rf"\s*AND\s+{re.escape(col_name)}\s+ILIKE\s+'%?[^']+%?'"
            modified = re.sub(pattern2, '', modified, flags=re.IGNORECASE)
            
            # Pattern 3: WHERE col = 'StateName' AND ... → WHERE ...
            pattern3 = rf"WHERE\s+{re.escape(col_name)}\s*=\s*'[A-Za-z\s]+'\s*AND\s*"
            modified = re.sub(pattern3, 'WHERE ', modified, flags=re.IGNORECASE)
            
            # Pattern 4: ... AND col = 'StateName' (at end) → ...  
            pattern4 = rf"\s*AND\s+{re.escape(col_name)}\s*=\s*'[A-Za-z\s]+'"
            modified = re.sub(pattern4, '', modified, flags=re.IGNORECASE)
            
            # Pattern 5: WHERE col ILIKE '...' (standalone, no AND) → WHERE 1=1
            pattern5 = rf"WHERE\s+{re.escape(col_name)}\s+ILIKE\s+'%?[^']+%?'\s*$"
            modified = re.sub(pattern5, 'WHERE 1=1 ', modified, flags=re.IGNORECASE)
        
        if modified != sql:
            logger.warning(f"[SQL-FIX] Stripped LLM location filter, will use confirmed_facts['location']={location_filter}")
        
        if modified != sql:
            logger.warning(f"[SQL-FIX] Before: {sql[:150]}")
            logger.warning(f"[SQL-FIX] After: {modified[:150]}")
        
        return modified
    
    def _can_inject_filter(self, sql: str, filter_instructions: str, all_columns: set) -> bool:
        """
        Check if the filter column exists in the TABLE BEING QUERIED (FROM clause).
        
        This prevents errors like "employment_status_code not found" when
        the LLM selects a table that doesn't have that column.
        """
        # Extract column name from filter instructions
        # e.g., "WHERE employment_status_code IN ('A')" → "employment_status_code"
        col_match = re.search(r'(\w+)\s+IN\s+\(', filter_instructions, re.IGNORECASE)
        if not col_match:
            col_match = re.search(r'(\w+)\s*=\s*', filter_instructions, re.IGNORECASE)
        
        if not col_match:
            # Can't determine column, allow injection (will fail gracefully if wrong)
            return True
        
        filter_col = col_match.group(1).lower()
        
        # Extract table name from FROM clause - this is the ACTUAL table being queried
        from_match = re.search(r'FROM\s+"?([^"\s]+)"?\s+AS\s+(\w+)', sql, re.IGNORECASE)
        if not from_match:
            from_match = re.search(r'FROM\s+"?([^"\s]+)"?', sql, re.IGNORECASE)
        
        if not from_match:
            logger.warning(f"[SQL-GEN] Could not find FROM table, allowing injection")
            return True
        
        from_table = from_match.group(1).strip('"').lower()
        logger.warning(f"[SQL-GEN] FROM table: {from_table[-50:]}")
        
        # Look up this specific table's columns from schema
        if self.schema:
            for table in self.schema.get('tables', []):
                t_name = table.get('table_name', '').lower()
                
                # Match the table name
                if t_name == from_table or from_table in t_name or t_name in from_table:
                    cols = table.get('columns', [])
                    col_names = []
                    for c in cols:
                        if isinstance(c, dict):
                            col_names.append(c.get('name', '').lower())
                        else:
                            col_names.append(str(c).lower())
                    
                    if filter_col in col_names:
                        logger.warning(f"[SQL-GEN] Filter column '{filter_col}' FOUND in FROM table")
                        return True
                    else:
                        logger.warning(f"[SQL-GEN] Filter column '{filter_col}' NOT in FROM table (has: {col_names[:5]}...)")
                        return False
        
        # Couldn't verify - don't inject to be safe
        logger.warning(f"[SQL-GEN] Could not verify table schema, skipping injection to be safe")
        return False
    
    def _inject_where_clause(self, sql: str, filter_clause: str) -> str:
        """
        Inject a WHERE clause into SQL that may or may not already have one.
        
        This is the data-driven approach: LLM generates structure, we inject filters.
        """
        # Clean up filter_clause - remove leading WHERE if present
        conditions = filter_clause.strip()
        if conditions.upper().startswith('WHERE '):
            conditions = conditions[6:].strip()
        
        if not conditions:
            logger.warning(f"[FILTER-INJECT] No conditions to inject")
            return sql
        
        logger.warning(f"[FILTER-INJECT] Injecting: {conditions}")
        logger.warning(f"[FILTER-INJECT] SQL length before: {len(sql)}")
        
        # Strip trailing semicolon - we'll add it back at the end
        had_semicolon = sql.rstrip().endswith(';')
        sql = sql.rstrip().rstrip(';').rstrip()
        
        sql_upper = sql.upper()
        
        # Check if SQL already has WHERE
        where_match = re.search(r'\bWHERE\b', sql, re.IGNORECASE)
        
        if where_match:
            # Has WHERE - add with AND after existing conditions
            logger.warning(f"[FILTER-INJECT] Found existing WHERE at position {where_match.start()}")
            where_pos = where_match.end()
            
            # Find the end of existing WHERE conditions
            end_keywords = ['GROUP BY', 'ORDER BY', 'LIMIT', 'HAVING']
            end_pos = len(sql)
            
            for keyword in end_keywords:
                kw_match = re.search(rf'\b{keyword}\b', sql[where_pos:], re.IGNORECASE)
                if kw_match:
                    candidate_pos = where_pos + kw_match.start()
                    if candidate_pos < end_pos:
                        end_pos = candidate_pos
            
            # Insert AND + conditions before end_pos
            sql = sql[:end_pos].rstrip() + f" AND {conditions} " + sql[end_pos:]
        
        else:
            # No WHERE - find where to insert
            logger.warning(f"[FILTER-INJECT] No existing WHERE found")
            
            # Insert before GROUP BY, ORDER BY, LIMIT, or at end
            insert_keywords = ['GROUP BY', 'ORDER BY', 'LIMIT', 'HAVING']
            insert_pos = len(sql)
            
            for keyword in insert_keywords:
                kw_match = re.search(rf'\b{keyword}\b', sql, re.IGNORECASE)
                if kw_match and kw_match.start() < insert_pos:
                    insert_pos = kw_match.start()
                    logger.warning(f"[FILTER-INJECT] Found {keyword} at {insert_pos}")
            
            logger.warning(f"[FILTER-INJECT] Insert position: {insert_pos}")
            
            # Insert WHERE clause
            before = sql[:insert_pos].rstrip()
            after = sql[insert_pos:].lstrip()
            
            logger.warning(f"[FILTER-INJECT] Before part ends with: ...{before[-50:] if len(before) > 50 else before}")
            logger.warning(f"[FILTER-INJECT] After part: {after[:50] if after else 'EMPTY'}")
            
            if after:
                sql = f"{before} WHERE {conditions} {after}"
            else:
                sql = f"{before} WHERE {conditions}"
        
        # Add semicolon back if it was there
        sql = sql.strip()
        if had_semicolon and not sql.endswith(';'):
            sql = sql + ';'
        
        logger.warning(f"[FILTER-INJECT] SQL length after: {len(sql)}")
        return sql
    
    def _detect_mode(self, q_lower: str) -> IntelligenceMode:
        """Detect the appropriate intelligence mode."""
        if any(w in q_lower for w in ['validate', 'check', 'verify', 'issues', 'problems']):
            return IntelligenceMode.VALIDATE
        if any(w in q_lower for w in ['configure', 'set up', 'setup']):
            return IntelligenceMode.CONFIGURE
        if any(w in q_lower for w in ['compare', 'versus', 'vs', 'difference']):
            return IntelligenceMode.COMPARE
        if any(w in q_lower for w in ['report', 'summary', 'overview']):
            return IntelligenceMode.REPORT
        if any(w in q_lower for w in ['analyze', 'trend', 'pattern']):
            return IntelligenceMode.ANALYZE
        return IntelligenceMode.SEARCH
    
    def _detect_domains(self, q_lower: str) -> List[str]:
        """Detect which data domains are relevant."""
        domains = []
        
        if any(w in q_lower for w in ['employee', 'worker', 'staff', 'people', 'who', 'how many', 'count']):
            domains.append('employees')
        if any(w in q_lower for w in ['earn', 'pay', 'salary', 'wage', 'rate', 'hour', '$', 'compensation']):
            domains.append('earnings')
        if any(w in q_lower for w in ['deduction', 'benefit', '401k', 'insurance', 'health']):
            domains.append('deductions')
        if any(w in q_lower for w in ['tax', 'withhold', 'federal', 'state']):
            domains.append('taxes')
        if any(w in q_lower for w in ['job', 'position', 'title', 'department']):
            domains.append('jobs')
        
        return domains if domains else ['general']
    
    def _select_relevant_tables(self, tables: List[Dict], q_lower: str) -> List[Dict]:
        """
        Select only tables relevant to the question.
        This keeps the SQL prompt small and focused.
        
        IMPORTANT: Always includes tables containing filter_candidate columns
        so the LLM can build proper JOINs for compound queries.
        
        PRIORITY: Main data tables over lookup/reference tables.
        """
        if not tables:
            return []
        
        # First, identify tables that contain filter_candidate columns
        # These MUST be included for compound queries to work
        filter_candidate_tables = set()
        if self.filter_candidates:
            for category, candidates in self.filter_candidates.items():
                for cand in candidates:
                    table_name = cand.get('table_name', cand.get('table', ''))
                    if table_name:
                        filter_candidate_tables.add(table_name.lower())
        
        logger.info(f"[SQL-GEN] Filter candidate tables: {filter_candidate_tables}")
        
        # Lookup/reference table indicators (should be deprioritized)
        LOOKUP_INDICATORS = [
            '_codes', '_lookup', '_ref', '_types', '_ethnic', 
            '_status', '_category', '_mapping', 'ethnic_co',
            'org_level_', 'scheduled_', 'supervisor'
        ]
        
        # Priority keywords for table selection
        # KEY: table name pattern -> question keywords that should boost it
        table_keywords = {
            'personal': ['employee', 'employees', 'person', 'people', 'who', 'name', 'ssn', 'birth', 'hire', 'termination', 'termed', 'terminated', 'active', 'location', 'state', 'city', 'address'],
            'company': ['company', 'organization', 'org', 'entity', 'legal'],
            'job': ['job', 'position', 'title', 'department', 'dept'],
            'earnings': ['earn', 'earning', 'pay code', 'salary', 'wage', 'compensation', 'earning code', 'earnings setup', 'earnings configured', 'earnigs', 'earings'],
            'deductions': ['deduction', 'benefit', '401k', 'insurance', 'health', 'benefit plan', 'deduction code', 'deduction setup'],
            'tax': ['tax', 'sui', 'suta', 'futa', 'fein', 'ein', 'withhold', 'federal', 'state tax', 'fica', 'w2', 'w-2', '941', '940'],
            'workers_comp': ['workers comp', 'work comp', 'wc', 'workers compensation', 'wcb', 'class code', 'experience mod'],
            'general_ledger': ['gl', 'general ledger', 'ledger', 'account mapping', 'gl mapping', 'chart of accounts', 'gl rules'],
            'gl_': ['gl', 'general ledger', 'account', 'ledger mapping'],
            'time': ['time', 'hours', 'attendance', 'schedule'],
            'address': ['address', 'zip', 'postal'],
            'rate': ['rate', 'rates', 'percentage', 'percent'],
            'config': ['config', 'configuration', 'setup', 'setting', 'correct', 'valid', 'validation'],
            'master': ['master', 'setup', 'configuration'],
            'jurisdiction': ['jurisdiction', 'tax jurisdiction', 'state setup', 'registration'],
        }
        
        # Columns that indicate location data (boost tables with these)
        LOCATION_COLUMNS = ['stateprovince', 'state', 'city', 'location', 'region', 'site', 'work_location', 'home_state']
        
        # Score each table
        scored_tables = []
        for table in tables:
            table_name = table.get('table_name', '').lower()
            columns = table.get('columns', [])
            row_count = table.get('row_count', 0)
            
            score = 0
            
            # ============================================================
            # CRITICAL: DIRECT NAME MATCH - Highest priority boost
            # If user asks about "ale group" and table contains "ale_group",
            # that table MUST win. This handles simple "show me X" queries.
            # ============================================================
            # Extract potential table-name terms from question
            # "what ale groups have been setup" -> ["ale", "groups", "ale_group", "ale_groups"]
            words = re.findall(r'\b[a-z]+\b', q_lower)
            
            # Common words to skip (wouldn't meaningfully identify a table)
            skip_words = {'the', 'and', 'for', 'are', 'have', 'been', 'what', 'which', 'show', 
                         'list', 'all', 'get', 'setup', 'set', 'how', 'many', 'config', 'table',
                         'tell', 'give', 'find', 'display', 'view', 'see', 'configured', 'exist',
                         'exists', 'there', 'any', 'our', 'the', 'this', 'that', 'with', 'has'}
            
            # Build n-grams and convert to snake_case for matching
            name_match_found = False
            for i in range(len(words)):
                word = words[i]
                
                # Single word matches (for short table names like "pto", "unions")
                if len(word) >= 3 and word not in skip_words:
                    # Try exact match and singular form (remove trailing 's')
                    word_singular = word.rstrip('s') if len(word) > 3 and word.endswith('s') else word
                    
                    if word in table_name or word_singular in table_name:
                        score += 30  # Moderate boost for single word match
                        name_match_found = True
                
                # Two-word combinations (e.g., "ale group" -> "ale_group")
                if i < len(words) - 1:
                    word2 = words[i+1]
                    two_word = f"{word}_{word2}"
                    two_word_alt = f"{word}{word2}"  # Also try without underscore
                    
                    # Also try singular forms
                    word2_singular = word2.rstrip('s') if len(word2) > 3 and word2.endswith('s') else word2
                    two_word_singular = f"{word}_{word2_singular}"
                    two_word_alt_singular = f"{word}{word2_singular}"
                    
                    matches_two = (two_word in table_name or two_word_alt in table_name or
                                   two_word_singular in table_name or two_word_alt_singular in table_name)
                    
                    if matches_two:
                        score += 100  # MASSIVE boost - this is almost certainly the right table
                        name_match_found = True
                        matched = two_word if two_word in table_name else (two_word_singular if two_word_singular in table_name else two_word_alt)
                        logger.warning(f"[SQL-GEN] DIRECT NAME MATCH: '{matched}' in {table_name[-40:]} (+100)")
                
                # Three-word combinations (e.g., "job change reasons" -> "job_change_reasons")
                if i < len(words) - 2:
                    word2 = words[i+1]
                    word3 = words[i+2]
                    three_word = f"{word}_{word2}_{word3}"
                    word3_singular = word3.rstrip('s') if len(word3) > 3 and word3.endswith('s') else word3
                    three_word_singular = f"{word}_{word2}_{word3_singular}"
                    
                    if three_word in table_name or three_word_singular in table_name:
                        score += 120  # Even bigger boost for 3-word match
                        name_match_found = True
                        logger.warning(f"[SQL-GEN] DIRECT NAME MATCH: '{three_word}' in {table_name[-40:]} (+120)")
            
            # DEPRIORITIZE lookup/reference tables
            is_lookup = any(indicator in table_name for indicator in LOOKUP_INDICATORS)
            if is_lookup:
                score -= 30  # Significant penalty for lookup tables
                logger.info(f"[SQL-GEN] Deprioritizing lookup table: {table_name[-40:]}")
            
            # DEPRIORITIZE tables with very few columns (likely lookups)
            if len(columns) <= 3:
                score -= 20
            
            # CRITICAL: Boost tables that have filter_candidate columns
            if table_name in filter_candidate_tables:
                score += 50  # Very high score to ensure inclusion
                logger.info(f"[SQL-GEN] Boosting table {table_name[-40:]} (has filter candidates)")
            
            # Check if table name matches any keyword patterns
            for pattern, keywords in table_keywords.items():
                if pattern in table_name:
                    # Check if any keyword is in the question
                    if any(kw in q_lower for kw in keywords):
                        score += 10
                    else:
                        score += 1  # Table exists but question doesn't directly ask about it
            
            # STRONG BOOST: Tax-specific questions should strongly prefer tax tables
            tax_question_terms = ['sui', 'suta', 'futa', 'fein', 'ein', 'tax rate', 'withholding', 'w2', 'w-2', '941', '940']
            if any(term in q_lower for term in tax_question_terms):
                if 'tax' in table_name:
                    score += 60  # Very strong boost
                    logger.warning(f"[SQL-GEN] Strong tax boost for: {table_name[-40:]}")
            
            # STRONG BOOST: Workers Comp questions should prefer workers_comp tables
            wc_question_terms = ['workers comp', 'work comp', 'wc rate', 'workers compensation', 'wcb']
            if any(term in q_lower for term in wc_question_terms):
                if any(wc in table_name for wc in ['workers_comp', 'work_comp', 'wc_']):
                    score += 70  # Very strong boost for WC tables
                    logger.warning(f"[SQL-GEN] Strong WC boost for: {table_name[-40:]}")
            
            # STRONG BOOST: Earnings questions should prefer earnings tables
            earnings_question_terms = ['earnings', 'earning code', 'pay code', 'earning setup', 'earnings configured',
                                       'earnigs', 'earings', 'earning']  # Common typos
            if any(term in q_lower for term in earnings_question_terms):
                if any(e in table_name for e in ['earnings', 'earning', 'pay_code']):
                    score += 70  # Very strong boost
                    logger.warning(f"[SQL-GEN] Strong earnings boost for: {table_name[-40:]}")
            
            # STRONG BOOST: Deduction questions should prefer deduction tables
            deduction_question_terms = ['deduction', 'benefit plan', 'deduction setup', 'deductions configured']
            if any(term in q_lower for term in deduction_question_terms):
                if any(d in table_name for d in ['deduction', 'benefit', 'ded_']):
                    score += 70  # Very strong boost
                    logger.warning(f"[SQL-GEN] Strong deduction boost for: {table_name[-40:]}")
            
            # STRONG BOOST: GL questions should prefer GL tables
            gl_question_terms = ['gl', 'general ledger', 'gl mapping', 'account mapping', 'chart of accounts']
            if any(term in q_lower for term in gl_question_terms):
                if any(g in table_name for g in ['general_ledger', 'gl_', 'account_map', 'ledger']):
                    score += 70  # Very strong boost
                    logger.warning(f"[SQL-GEN] Strong GL boost for: {table_name[-40:]}")
            
            # STRONG BOOST: Configuration/validation questions should prefer config tables
            config_question_terms = ['correct', 'configured', 'valid', 'setup', 'setting', 'configuration']
            if any(term in q_lower for term in config_question_terms):
                if any(cfg in table_name for cfg in ['config', 'validation', 'master', 'setting']):
                    score += 50  # Strong boost for config tables
                    logger.warning(f"[SQL-GEN] Config boost for: {table_name[-40:]}")
            
            # Boost "personal" table for general employee questions - but NOT lookup variants
            if 'personal' in table_name and not is_lookup:
                if any(kw in q_lower for kw in ['employee', 'how many', 'count', 'who']):
                    score += 25
            
            # Boost tables with high row counts (they're likely the main tables)
            if row_count > 1000:
                score += 10
            elif row_count > 100:
                score += 5
            elif row_count < 50:
                score -= 5  # Likely a lookup table
            
            # Boost tables with many columns (main data tables)
            if len(columns) > 15:
                score += 10
            elif len(columns) > 8:
                score += 5
            
            # SMART BOOST: If question asks about location, boost tables that HAVE location columns
            if any(loc_word in q_lower for loc_word in ['location', 'state', 'by state', 'by location', 'geographic']):
                col_names = [c.get('name', '').lower() if isinstance(c, dict) else str(c).lower() for c in columns]
                if any(loc_col in ' '.join(col_names) for loc_col in LOCATION_COLUMNS):
                    score += 40  # Big boost for tables with actual location data
                    logger.warning(f"[SQL-GEN] Boosting table {table_name[-40:]} - has location columns")
            
            # =================================================================
            # CRITICAL: Check column VALUES, not just column NAMES
            # This is what allows "show me SUI rates" to find the tax table
            # even though "SUI" is a VALUE in type_of_tax, not a column name
            # =================================================================
            try:
                if self.structured_handler and self.structured_handler.conn:
                    # Get distinct values from column profiles for this table
                    # NOTE: Column is 'distinct_values' not 'top_values_json'
                    value_profiles = self.structured_handler.conn.execute("""
                        SELECT column_name, distinct_values
                        FROM _column_profiles 
                        WHERE LOWER(table_name) = LOWER(?)
                        AND distinct_values IS NOT NULL
                        AND distinct_values != '[]'
                    """, [table.get('table_name', '')]).fetchall()
                    
                    for col_name, distinct_values_json in value_profiles:
                        if not distinct_values_json:
                            continue
                        try:
                            distinct_values = json.loads(distinct_values_json)
                            # Check if any query word matches a column value
                            for val_info in distinct_values:
                                val = str(val_info.get('value', '')).lower() if isinstance(val_info, dict) else str(val_info).lower()
                                if not val or len(val) < 2:
                                    continue
                                # Check if this value appears in the query
                                for word in words:
                                    if len(word) >= 2 and word not in skip_words:
                                        if word == val or word in val or val in word:
                                            score += 80  # MAJOR boost - query matches a column value
                                            logger.warning(f"[SQL-GEN] VALUE MATCH: '{word}' matches value '{val}' in {table_name[-40:]}.{col_name} (+80)")
                                            break
                        except (json.JSONDecodeError, TypeError):
                            pass
            except Exception as e:
                logger.debug(f"[SQL-GEN] Column value check failed for {table_name}: {e}")
            
            scored_tables.append((score, table))
            logger.debug(f"[SQL-GEN] Table {table_name[-30:]} score={score} (rows={row_count}, cols={len(columns)}, lookup={is_lookup})")
        
        # Sort by score descending
        scored_tables.sort(key=lambda x: -x[0])
        
        # Log top tables for debugging
        for score, t in scored_tables[:5]:
            logger.warning(f"[SQL-GEN] Candidate: {t.get('table_name', '')[-40:]} score={score}")
        
        # Take top 5 tables (increased from 3 to handle compound queries)
        relevant = [t for score, t in scored_tables[:5] if score > 0]
        
        # If no relevant tables found, just use first table
        if not relevant:
            relevant = [tables[0]]
        
        logger.info(f"[SQL-GEN] Selected {len(relevant)} relevant tables")
        
        return relevant
    
    def _build_create_table_schema(self, table_name: str, short_alias: str = None) -> Tuple[str, set]:
        """
        Build CREATE TABLE schema from DuckDB for SQLCoder.
        
        SQLCoder was trained on CREATE TABLE statements, so this format
        dramatically improves column accuracy vs our old format.
        
        Returns:
            (schema_string, set_of_valid_columns)
        """
        try:
            # Get exact column info from DuckDB
            col_info = self.structured_handler.conn.execute(
                f'PRAGMA table_info("{table_name}")'
            ).fetchall()
            
            if not col_info:
                return "", set()
            
            # Build CREATE TABLE statement
            alias = short_alias or table_name.split('_')[-1]
            columns = []
            valid_cols = set()
            
            for row in col_info:
                col_name = row[1]  # name at index 1
                col_type = row[2]  # type at index 2
                
                # Skip junk columns
                col_lower = col_name.lower()
                if col_lower in ['nan', 'none', ''] or col_lower.startswith('unnamed'):
                    continue
                    
                valid_cols.add(col_name)
                
                # Simplify type for LLM (don't need precision details)
                simple_type = col_type.split('(')[0].upper()
                if simple_type in ['VARCHAR', 'TEXT', 'STRING']:
                    simple_type = 'TEXT'
                elif simple_type in ['INTEGER', 'INT', 'BIGINT', 'SMALLINT']:
                    simple_type = 'INTEGER'
                elif simple_type in ['FLOAT', 'DOUBLE', 'DECIMAL', 'NUMERIC', 'REAL']:
                    simple_type = 'DECIMAL'
                elif simple_type in ['BOOLEAN', 'BOOL']:
                    simple_type = 'BOOLEAN'
                elif 'DATE' in simple_type or 'TIME' in simple_type:
                    simple_type = 'DATE'
                
                columns.append(f"    {col_name} {simple_type}")
            
            # Get sample values for key columns (helps disambiguation)
            sample_comment = ""
            try:
                sample_rows = self.structured_handler.query(
                    f'SELECT * FROM "{table_name}" LIMIT 3'
                )
                if sample_rows:
                    # Pick 3-4 interesting columns for sample
                    sample_cols = list(sample_rows[0].keys())[:4]
                    sample_vals = []
                    for col in sample_cols:
                        vals = [str(r.get(col, ''))[:20] for r in sample_rows if r.get(col)]
                        if vals:
                            sample_vals.append(f"{col}='{vals[0]}'")
                    if sample_vals:
                        sample_comment = f"\n-- Sample: {', '.join(sample_vals[:3])}"
            except:
                pass
            
            schema = f"CREATE TABLE {alias} (\n" + ",\n".join(columns) + "\n);" + sample_comment
            
            return schema, valid_cols
            
        except Exception as e:
            logger.error(f"[SQL-GEN] Error building CREATE TABLE schema: {e}")
            return "", set()
    
    def _is_simple_query(self, question: str) -> bool:
        """
        Detect if question is a simple single-table query.
        
        Simple queries: show X, list X, count X, what are the X
        Complex queries: compare X to Y, join X with Y, X by Y from multiple tables
        """
        q_lower = question.lower()
        
        # Simple patterns - single table operations
        simple_patterns = [
            r'^show\s+(me\s+)?(the\s+)?',      # "show me the sui rates"
            r'^list\s+(all\s+)?(the\s+)?',     # "list all earnings codes"
            r'^what\s+are\s+(the\s+)?',        # "what are the deductions"
            r'^give\s+me\s+(the\s+)?',         # "give me the tax codes"
            r'^display\s+(the\s+)?',           # "display the rates"
            r'^get\s+(me\s+)?(the\s+)?',       # "get the configuration"
        ]
        
        # Complex patterns - likely need multiple tables or complex logic
        complex_patterns = [
            r'\bcompare\b',                     # compare X to Y
            r'\bjoin\b',                        # explicit join request
            r'\bcross.?reference\b',            # cross-reference
            r'\bvs\.?\b',                       # X vs Y
            r'\bversus\b',                      # X versus Y
            r'\bfrom\s+\w+\s+and\s+',          # from X and Y
            r'\bbetween\s+\w+\s+and\s+',       # between X and Y
        ]
        
        # Check complex first (takes priority)
        for pattern in complex_patterns:
            if re.search(pattern, q_lower):
                return False
        
        # Check simple
        for pattern in simple_patterns:
            if re.search(pattern, q_lower):
                return True
        
        # Default to simple for short questions
        return len(question.split()) <= 8

    def _check_sql_columns(self, sql: str, valid_columns: set) -> List[str]:
        """
        Check SQL for columns not in the valid set.
        
        Returns list of invalid column names found.
        """
        if not valid_columns:
            return []
        
        # Extract potential column references (simplified)
        # Look for words that could be columns (after SELECT, in WHERE, etc.)
        invalid = []
        
        # Common SQL keywords to skip
        sql_keywords = {
            'select', 'from', 'where', 'and', 'or', 'not', 'in', 'is', 'null',
            'like', 'ilike', 'as', 'on', 'join', 'left', 'right', 'inner', 'outer',
            'group', 'by', 'order', 'asc', 'desc', 'limit', 'offset', 'having',
            'count', 'sum', 'avg', 'min', 'max', 'distinct', 'case', 'when', 'then',
            'else', 'end', 'cast', 'nulls', 'last', 'first', 'true', 'false',
            'between', 'exists', 'all', 'any', 'union', 'except', 'intersect',
            'coalesce', 'upper', 'lower', 'trim', 'substring', 'concat'
        }
        
        # Create lowercase valid columns set for case-insensitive matching
        valid_lower = {c.lower() for c in valid_columns}
        
        # Find all word-like tokens
        tokens = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', sql)
        
        for token in tokens:
            token_lower = token.lower()
            # Skip SQL keywords
            if token_lower in sql_keywords:
                continue
            # Skip if it matches a valid column (case-insensitive)
            if token_lower in valid_lower:
                continue
            # Skip table aliases (short names)
            if len(token) < 4:
                continue
            # Skip if it's clearly a value (in quotes nearby)
            if token_lower.startswith('t_'):  # table alias prefix
                continue
                
            # Potential invalid column
            # But only flag if it looks like a column reference (has underscore or specific patterns)
            if '_' in token or token_lower.endswith('_code') or token_lower.endswith('_id'):
                if token_lower not in valid_lower:
                    invalid.append(token)
        
        return list(set(invalid))[:5]  # Limit to 5

    def _generate_sql_for_question(self, question: str, analysis: Dict) -> Optional[Dict]:
        """Generate SQL query using LLMOrchestrator with SMART table selection."""
        logger.warning(f"[SQL-GEN] v5.18.0 - Starting SQL generation")
        logger.warning(f"[SQL-GEN] confirmed_facts: {self.confirmed_facts}")
        
        if not self.structured_handler or not self.schema:
            return None
        
        tables = self.schema.get('tables', [])
        if not tables:
            return None
        
        # Get LLMOrchestrator
        try:
            try:
                from utils.llm_orchestrator import LLMOrchestrator
            except ImportError:
                from backend.utils.llm_orchestrator import LLMOrchestrator
            
            orchestrator = LLMOrchestrator()
        except Exception as e:
            logger.error(f"[SQL-GEN] Could not load LLMOrchestrator: {e}")
            return None
        
        # SMART TABLE SELECTION - only include relevant tables
        q_lower = question.lower()
        relevant_tables = self._select_relevant_tables(tables, q_lower)
        
        # SIMPLE QUERY OPTIMIZATION: Use CREATE TABLE format for single-table queries
        # This dramatically improves SQLCoder accuracy by matching its training format
        is_simple = self._is_simple_query(question)
        logger.warning(f"[SQL-GEN] Simple query detection: {is_simple} for '{question[:50]}...'")
        
        if is_simple and relevant_tables:
            # For simple queries, use ONLY the top-scored table with proper CREATE TABLE format
            primary_table_info = relevant_tables[0]
            primary_full_name = primary_table_info.get('table_name', '')
            
            # Extract short alias for the primary table
            short_alias = primary_full_name.split('_')[-2] + '_' + primary_full_name.split('_')[-1] \
                if '_' in primary_full_name else primary_full_name[-20:]
            # Clean alias - no numbers at start
            if short_alias and short_alias[0].isdigit():
                short_alias = 't_' + short_alias
            short_alias = short_alias[:25]  # Keep it short
            
            # Build CREATE TABLE schema (SQLCoder's training format)
            create_table_schema, valid_columns = self._build_create_table_schema(
                primary_full_name, short_alias
            )
            
            if create_table_schema and valid_columns:
                logger.warning(f"[SQL-GEN] Using CREATE TABLE format with {len(valid_columns)} columns")
                
                # Store for post-processing
                self._table_aliases = {short_alias: primary_full_name}
                
                # Build focused prompt
                prompt = f"""### Task
Generate a SQL query to answer: {question}

### Database Schema
{create_table_schema}

### Rules
- Use ONLY columns from the schema above
- Table name: {short_alias}
- For text search, use ILIKE '%term%'
- Return all relevant columns

### Answer
Given the schema, here is the SQL query:
```sql
SELECT"""
                
                logger.warning(f"[SQL-GEN] Simple query prompt ({len(prompt)} chars)")
                
                result = orchestrator.generate_sql(prompt, valid_columns)
                
                if result.get('success') and result.get('sql'):
                    sql = result['sql'].strip()
                    
                    # Clean markdown
                    if '```' in sql:
                        sql = re.sub(r'```sql\s*', '', sql, flags=re.IGNORECASE)
                        sql = re.sub(r'```\s*$', '', sql)
                        sql = sql.replace('```', '').strip()
                    
                    # Prepend SELECT if needed (SQLCoder prompt ends with SELECT)
                    if not sql.upper().startswith('SELECT') and not sql.upper().startswith('WITH'):
                        sql = 'SELECT ' + sql
                    
                    logger.warning(f"[SQL-GEN] Simple query SQL: {sql[:100]}...")
                    
                    # Expand alias to full table name
                    sql = re.sub(
                        rf'\bFROM\s+{re.escape(short_alias)}\b(?!\s+AS)',
                        f'FROM "{primary_full_name}" AS {short_alias}',
                        sql, flags=re.IGNORECASE
                    )
                    
                    # Validate columns exist
                    invalid_cols = self._check_sql_columns(sql, valid_columns)
                    if not invalid_cols:
                        return {
                            'sql': sql,
                            'table': short_alias,
                            'query_type': 'simple',
                            'all_columns': valid_columns
                        }
                    else:
                        logger.warning(f"[SQL-GEN] Simple query had invalid cols: {invalid_cols}, falling back")
        
        # FALLBACK: Complex query handling (multiple tables, existing logic)
        # Build COMPACT schema with SHORT ALIASES
        tables_info = []
        all_columns = set()
        primary_table = None
        table_aliases = {}  # Map short alias to full name
        used_aliases = set()  # Track used aliases to avoid duplicates
        
        def extract_short_alias(table_info: dict, used: set) -> str:
            """Extract a meaningful short alias from table info.
            
            Priority:
            1. Use sheet_name from metadata (most reliable)
            2. Extract from table_name as fallback
            
            IMPORTANT: SQL aliases cannot start with a number!
            """
            full_table_name = table_info.get('table_name', '')
            
            def ensure_valid_alias(alias: str) -> str:
                """Ensure alias doesn't start with a number (invalid SQL)."""
                if alias and alias[0].isdigit():
                    return 't_' + alias  # Prefix with 't_' if starts with number
                return alias
            
            # BEST: Use sheet_name from metadata if available
            sheet_name = table_info.get('sheet_name', '')
            if sheet_name:
                # Clean up sheet name for SQL alias
                clean_sheet = re.sub(r'[^\w]', '_', sheet_name.lower()).strip('_')
                clean_sheet = re.sub(r'_+', '_', clean_sheet)  # Remove double underscores
                clean_sheet = ensure_valid_alias(clean_sheet)
                if clean_sheet and len(clean_sheet) <= 30:
                    if clean_sheet not in used:
                        return clean_sheet
                    # If duplicate, append a number
                    for suffix in range(2, 10):
                        candidate = f"{clean_sheet}{suffix}"
                        if candidate not in used:
                            return candidate
            
            # FALLBACK: Check for __ delimiter (old format)
            if '__' in full_table_name:
                candidate = full_table_name.split('__')[-1]
                candidate = ensure_valid_alias(candidate)
                if candidate and candidate not in used:
                    return candidate
            
            # FALLBACK: Use last meaningful segment after splitting
            parts = full_table_name.split('_')
            if len(parts) >= 2:
                # Try last 2-3 parts for uniqueness
                for i in range(2, min(5, len(parts))):
                    candidate = '_'.join(parts[-i:])
                    candidate = ensure_valid_alias(candidate)
                    if len(candidate) <= 25 and candidate not in used:
                        return candidate
            
            # Last resort: truncated name with index
            base = full_table_name[:15]
            base = ensure_valid_alias(base)
            if base not in used:
                return base
            for suffix in range(2, 100):
                candidate = f"{base}_{suffix}"
                if candidate not in used:
                    return candidate
            
            return ensure_valid_alias(full_table_name)  # Give up, use full name
        
        for i, table in enumerate(relevant_tables):
            table_name = table.get('table_name', '')
            columns = table.get('columns', [])
            if columns and isinstance(columns[0], dict):
                col_names = [c.get('name', str(c)) for c in columns]
            else:
                col_names = [str(c) for c in columns] if columns else []
            row_count = table.get('row_count', 0)
            
            all_columns.update(col_names)
            
            # Create SHORT alias - use sheet_name from metadata when available
            short_name = extract_short_alias(table, used_aliases)
            used_aliases.add(short_name)
            table_aliases[short_name] = table_name
            
            logger.warning(f"[SQL-GEN] Table alias: {short_name} → {table_name}")
            
            # First relevant table is "primary"
            if i == 0:
                primary_table = short_name
            
            # Only include sample for primary table
            sample_str = ""
            if i == 0:
                try:
                    rows = self.structured_handler.query(f'SELECT * FROM "{table_name}" LIMIT 2')
                    cols = list(rows[0].keys()) if rows else []
                    if rows and cols:
                        samples = []
                        for col in cols[:4]:  # Limit to 4 columns
                            vals = set(str(row.get(col, ''))[:15] for row in rows if row.get(col))
                            if vals:
                                samples.append(f"    {col}: {', '.join(list(vals)[:2])}")
                        sample_str = "\n  Sample:\n" + "\n".join(samples[:4]) if samples else ""
                except:
                    pass
            
            # Compact column list
            col_str = ', '.join(col_names[:15])
            if len(col_names) > 15:
                col_str += f" (+{len(col_names) - 15} more)"
            
            # Use SHORT name in schema
            tables_info.append(f"Table: {short_name}\n  Columns: {col_str}\n  Rows: {row_count}{sample_str}")
        
        # Store aliases for SQL post-processing
        self._table_aliases = table_aliases
        
        schema_text = '\n\n'.join(tables_info)
        
        # SIMPLIFIED relationships - only between relevant tables
        relationships_text = ""
        if self.relationships and len(relevant_tables) > 1:
            relevant_table_names = {t.get('table_name', '') for t in relevant_tables}
            rel_lines = []
            for rel in self.relationships[:10]:
                src_table = rel.get('source_table', '')
                tgt_table = rel.get('target_table', '')
                if src_table in relevant_table_names and tgt_table in relevant_table_names:
                    src = f"{src_table.split('__')[-1]}.{rel.get('source_column')}"
                    tgt = f"{tgt_table.split('__')[-1]}.{rel.get('target_column')}"
                    rel_lines.append(f"  {src} → {tgt}")
            if rel_lines:
                relationships_text = "\n\nJOIN ON:\n" + "\n".join(rel_lines[:5])
        
        # BUILD FILTER INSTRUCTIONS FROM CONFIRMED FACTS (for post-injection)
        filter_instructions = self._build_filter_instructions(relevant_tables)
        logger.warning(f"[SQL-GEN] filter_instructions: {filter_instructions if filter_instructions else 'NONE'}")
        
        # BUILD SEMANTIC HINTS from filter_candidates
        # This tells the LLM which columns to use for specific purposes
        # For simple queries, only include columns from the primary table
        semantic_hints = []
        
        # Get primary table name for filtering
        primary_table_full = relevant_tables[0].get('table_name', '') if relevant_tables else ''
        primary_table_short = primary_table_full.split('__')[-1] if '__' in primary_table_full else primary_table_full
        
        # Check if this is a simple "by X" query (should avoid JOINs)
        is_simple_query = bool(re.search(r'\bshow\s+\w+.*\bby\s+\w+', q_lower)) or bool(re.search(r'\bhow many\b', q_lower))
        
        if self.filter_candidates:
            for category, candidates in self.filter_candidates.items():
                if not candidates:
                    continue
                    
                if category == 'status':
                    # Status can have multiple useful columns - list them all
                    date_cols = []
                    code_cols = []
                    for cand in candidates:
                        col_name = cand.get('column_name', cand.get('column', ''))
                        col_type = cand.get('inferred_type', cand.get('type', ''))
                        table_name = cand.get('table_name', cand.get('table', ''))
                        short_table = table_name.split('__')[-1] if '__' in table_name else table_name
                        col_lower = col_name.lower()
                        logger.warning(f"[SQL-GEN] Status candidate column: {col_name} in {short_table} (type={col_type})")
                        # Check if this is a termination date column
                        is_term_date = (
                            col_type == 'date' or
                            'termination' in col_lower or 
                            'term_date' in col_lower or
                            'term_dt' in col_lower or
                            'termdate' in col_lower or
                            col_lower == 'term_date' or
                            col_lower.endswith('_term_date')
                        )
                        if is_term_date:
                            date_cols.append((f"{short_table}.{col_name}", col_lower))
                        else:
                            # Prioritize employment_status columns
                            priority = 0
                            if 'employment_status' in col_lower:
                                priority = 100
                            elif 'emp_status' in col_lower:
                                priority = 90
                            elif col_lower == 'status' or col_lower.endswith('_status'):
                                priority = 50
                            code_cols.append((f"{short_table}.{col_name}", priority))
                    
                    if date_cols:
                        semantic_hints.append(f"- For termination dates/timing: use {date_cols[0][0]}")
                    if code_cols:
                        # Sort by priority descending, pick best
                        code_cols.sort(key=lambda x: -x[1])
                        semantic_hints.append(f"- For employee status (active/termed): use {code_cols[0][0]}")
                else:
                    # Other categories - find column in primary table if possible
                    best = candidates[0]
                    col_name = best.get('column_name', best.get('column', ''))
                    table_name = best.get('table_name', best.get('table', ''))
                    short_table = table_name.split('__')[-1] if '__' in table_name else table_name
                    
                    # For simple queries, prefer columns in the primary table
                    if is_simple_query and short_table and short_table != primary_table_short:
                        # Try to find same column in primary table
                        found_in_primary = False
                        for cand in candidates:
                            cand_table = cand.get('table_name', cand.get('table', ''))
                            cand_short = cand_table.split('__')[-1] if '__' in cand_table else cand_table
                            if cand_short == primary_table_short:
                                col_name = cand.get('column_name', cand.get('column', ''))
                                short_table = cand_short
                                found_in_primary = True
                                break
                        
                        if not found_in_primary:
                            logger.warning(f"[SQL-GEN] Skipping hint for {category} - column not in primary table {primary_table_short}")
                            continue
                    
                    full_col = f"{short_table}.{col_name}" if short_table else col_name
                    
                    if category == 'location':
                        semantic_hints.append(f"- For location/state: use {full_col}")
                    elif category == 'company':
                        semantic_hints.append(f"- For company: use {full_col}")
                    elif category == 'organization':
                        semantic_hints.append(f"- For org/department: use {full_col}")
                    elif category == 'pay_type':
                        semantic_hints.append(f"- For pay type (hourly/salary): use {full_col}")
                    elif category == 'employee_type':
                        semantic_hints.append(f"- For employee type (regular/temp): use {full_col}")
                    elif category == 'job':
                        semantic_hints.append(f"- For job/position: use {full_col}")
        
        # Add customer-specific org level mappings if available
        if hasattr(self, 'org_mapping') and self.org_mapping:
            org_hints = []
            for level_col, customer_name in self.org_mapping.items():
                org_hints.append(f"- '{customer_name}' = {level_col} (customer terminology)")
            if org_hints:
                semantic_hints.append("CUSTOMER ORG STRUCTURE:")
                semantic_hints.extend(org_hints)
                logger.warning(f"[SQL-GEN] Added {len(org_hints)} customer org mappings")
        
        # Add CRITICAL GROUPINGS - key dimensions for analysis
        # These are the meaningful ways to slice workforce data
        grouping_hints = []
        resolved_groupings = self.get_resolved_groupings() if hasattr(self, 'get_resolved_groupings') else {}
        
        for key, config in resolved_groupings.items():
            if config.get('available') and config.get('actual_column'):
                col = config['actual_column']
                name = config.get('customer_name', config.get('name', key))
                category = config.get('category', '')
                
                # Build contextual hint
                if category == 'organization':
                    grouping_hints.append(f"- GROUP BY '{name}': use {col}")
                elif category == 'classification':
                    valid_vals = config.get('valid_values', [])
                    if valid_vals:
                        grouping_hints.append(f"- '{name}' ({col}): valid values {valid_vals[:4]}")
                    else:
                        grouping_hints.append(f"- GROUP BY '{name}': use {col}")
                elif category in ['geographic', 'legal_entity', 'payroll', 'tax']:
                    grouping_hints.append(f"- GROUP BY '{name}': use {col}")
        
        if grouping_hints:
            semantic_hints.append("KEY GROUPING DIMENSIONS (for GROUP BY, breakdowns, dashboards):")
            semantic_hints.extend(grouping_hints[:12])  # Limit to avoid prompt bloat
            logger.warning(f"[SQL-GEN] Added {len(grouping_hints)} critical grouping hints")
        
        semantic_text = ""
        column_mappings = {}  # Generic term → actual column for post-processing
        if semantic_hints:
            # Add note about automatic status filtering
            semantic_hints.insert(0, "NOTE: Status filtering (active/termed) is applied automatically - do not add WHERE clauses for it")
            semantic_text = "\n\nCOLUMN USAGE:\n" + "\n".join(semantic_hints)
            logger.warning(f"[SQL-GEN] Semantic hints: {len(semantic_hints)} column mappings added")
            for hint in semantic_hints:
                logger.warning(f"[SQL-GEN] Hint: {hint}")
                
                # Extract column mappings from hints (these are TABLE-SPECIFIC, not global)
                # Format: "- For location/state: use table.actual_column"
                if ': use ' in hint:
                    full_col = hint.split(': use ')[-1].strip()
                    actual_col = full_col.split('.')[-1] if '.' in full_col else full_col
                    
                    # Map based on hint text
                    hint_lower = hint.lower()
                    if 'location' in hint_lower or 'state' in hint_lower:
                        column_mappings['location'] = actual_col
                        column_mappings['state'] = actual_col
                        column_mappings['site'] = actual_col
                    elif 'company' in hint_lower:
                        column_mappings['company'] = actual_col
                    elif 'org' in hint_lower or 'department' in hint_lower:
                        column_mappings['organization'] = actual_col
                        column_mappings['department'] = actual_col
                        column_mappings['dept'] = actual_col
                        column_mappings['org'] = actual_col
                    elif 'employee type' in hint_lower:
                        column_mappings['employee_type'] = actual_col
                    elif 'pay type' in hint_lower:
                        column_mappings['pay_type'] = actual_col
                    elif 'job' in hint_lower or 'position' in hint_lower:
                        column_mappings['job'] = actual_col
        
        if column_mappings:
            logger.warning(f"[SQL-GEN] Column mappings from hints: {column_mappings}")
        
        # Store for use in SQL post-processing
        self._column_mappings = column_mappings
        
        # Build query hints based on question patterns
        query_hints = []
        
        # "Show X by Y" pattern - simple aggregation, no JOINs needed
        if re.search(r'\bshow\s+\w+\s+\w*\s*by\s+\w+', q_lower) or re.search(r'\bby\s+(job|state|location|company|month|year)\b', q_lower):
            query_hints.append(f"Use simple aggregation: SELECT column, COUNT(*) FROM {primary_table} GROUP BY column")
            query_hints.append("Do NOT use JOINs for simple counts")
            
            # Add ORDER BY hints
            if 'month' in q_lower or 'year' in q_lower or 'date' in q_lower:
                query_hints.append("ORDER BY the date/month column ASC for chronological order")
            else:
                query_hints.append("ORDER BY COUNT(*) DESC to show highest counts first")
        
        # COUNT hint
        if 'how many' in q_lower or 'count' in q_lower:
            query_hints.append(f"For COUNT, use: SELECT COUNT(*) FROM \"{primary_table}\"")
        
        # GROUP BY hint - detect "by X" patterns
        group_by_patterns = [
            (r'\bby\s+month\b', 'GROUP BY month - use strftime(\'%Y-%m\', TRY_CAST(date_column AS DATE)) to get YYYY-MM format'),
            (r'\bby\s+year\b', 'GROUP BY year - use EXTRACT(YEAR FROM date_column)'),
            (r'\bby\s+(state|location)\b', 'GROUP BY location/state column'),
            (r'\bby\s+(company|org)\b', 'GROUP BY company/organization column'),
            (r'\bby\s+(department|dept)\b', 'GROUP BY department/org column'),
        ]
        
        for pattern, hint in group_by_patterns:
            if re.search(pattern, q_lower):
                query_hints.append(hint)
                logger.warning(f"[SQL-GEN] Detected GROUP BY pattern: {pattern}")
        
        # VALIDATION/CORRECTNESS QUESTIONS - Smart consultant analysis
        # Questions like "are the rates correct?" need intelligent analysis, not just data dump
        validation_keywords = ['correct', 'valid', 'right', 'properly', 'configured', 
                               'issue', 'problem', 'check', 'verify', 'audit', 'review',
                               'accurate', 'wrong', 'error', 'mistake']
        is_validation_question = any(kw in q_lower for kw in validation_keywords)
        logger.warning(f"[SQL-GEN] Validation check: is_validation={is_validation_question}, q='{q_lower[:50]}', tables={len(relevant_tables) if relevant_tables else 0}")
        
        if is_validation_question and relevant_tables:
            # For validation questions, be a smart consultant
            primary_full = relevant_tables[0].get('table_name', '')
            if primary_full:
                logger.warning(f"[SQL-GEN] VALIDATION QUESTION - smart consultant analysis")
                
                # Detect domain to check if we need multiple tables
                domain_config = _detect_validation_domain(question)
                validation_type = domain_config.get('validation_type', 'rate') if domain_config else 'rate'
                
                # For CONFIG domains (earnings, deductions, GL), find ALL matching tables
                config_multi_table_domains = ['earnings', 'deductions', 'gl_mapping']
                domain_key = domain_config.get('key', '') if domain_config else ''
                
                matching_tables = []
                if validation_type == 'config' and domain_key in config_multi_table_domains:
                    # Find all tables that match this domain from the full table list
                    table_patterns = domain_config.get('table_patterns', [])
                    exclude_patterns = domain_config.get('table_exclude_patterns', [])
                    
                    for table in tables:
                        tname = table.get('table_name', '').lower()
                        # Must match at least one include pattern
                        matched_pattern = None
                        for p in table_patterns:
                            if p in tname:
                                matched_pattern = p
                                break
                        
                        if matched_pattern:
                            # Must NOT match any exclude pattern
                            excluded_by = None
                            for ex in exclude_patterns:
                                if ex in tname:
                                    excluded_by = ex
                                    break
                            
                            if excluded_by:
                                logger.info(f"[SQL-GEN] Excluded table {tname[-50:]} (matched '{excluded_by}')")
                            else:
                                matching_tables.append(table)
                                logger.info(f"[SQL-GEN] Matched table {tname[-50:]} (pattern '{matched_pattern}')")
                    
                    logger.warning(f"[SQL-GEN] Config domain '{domain_key}' - found {len(matching_tables)} matching tables")
                
                if not matching_tables:
                    matching_tables = [relevant_tables[0]]
                
                # Get columns from first table (assume similar structure)
                primary_cols = matching_tables[0].get('columns', [])
                col_names = [c.get('name', str(c)) if isinstance(c, dict) else str(c) for c in primary_cols]
                
                # For multiple tables, ask which region to analyze
                if len(matching_tables) > 1:
                    # Check if user already confirmed a region scope
                    region_scope = self.confirmed_facts.get('validation_region_scope')
                    
                    if region_scope:
                        # User already selected - filter to that table
                        if region_scope == '__all__':
                            # User wants all - build UNION query
                            common_cols = set(col_names)
                            for table in matching_tables[1:]:
                                table_cols = [c.get('name', str(c)) if isinstance(c, dict) else str(c) for c in table.get('columns', [])]
                                common_cols &= set(table_cols)
                            
                            if common_cols:
                                col_names = list(common_cols)[:20]
                                select_cols = ', '.join(f'"{c}"' for c in col_names)
                                
                                union_parts = []
                                for table in matching_tables:
                                    tname = table.get('table_name', '')
                                    source_label = tname.split('_')[-1] if '_' in tname else tname[-10:]
                                    union_parts.append(f'SELECT {select_cols}, \'{source_label}\' as _source FROM "{tname}"')
                                
                                sql = ' UNION ALL '.join(union_parts)
                                logger.warning(f"[SQL-GEN] Built UNION query for {len(matching_tables)} tables (user confirmed all)")
                                
                                return {
                                    'sql': sql,
                                    'table': f"{len(matching_tables)} {domain_key} tables",
                                    'query_type': 'validation',
                                    'all_columns': col_names + ['_source'],
                                    'validation_bypass': True,
                                    'smart_assumption': f"Reviewing {domain_config.get('name', domain_key)} across all regions"
                                }
                        else:
                            # User selected specific region - find that table
                            for table in matching_tables:
                                tname = table.get('table_name', '')
                                if region_scope in tname.lower():
                                    matching_tables = [table]
                                    primary_cols = table.get('columns', [])
                                    col_names = [c.get('name', str(c)) if isinstance(c, dict) else str(c) for c in primary_cols]
                                    logger.warning(f"[SQL-GEN] User selected region '{region_scope}' - using table {tname}")
                                    break
                    else:
                        # Need to ask user which region to review
                        # Extract region identifiers from table names
                        region_labels = {
                            'nan': 'US Only',
                            'can': 'Canada Only', 
                            'usa': 'US Only',
                            'us': 'US Only',
                            'ca': 'Canada Only',
                            'uk': 'UK Only',
                            'mex': 'Mexico Only',
                            'info': 'Config Info',
                        }
                        
                        # Dedupe by suffix - combine tables with same region
                        region_tables = {}  # suffix -> list of tables
                        for table in matching_tables:
                            tname = table.get('table_name', '').lower()
                            suffix = tname.split('_')[-1] if '_' in tname else ''
                            
                            if suffix not in region_tables:
                                region_tables[suffix] = []
                            region_tables[suffix].append(table)
                        
                        # Build options from deduplicated regions
                        table_regions = []
                        for suffix, tables in region_tables.items():
                            # Sum row counts for all tables with this suffix
                            total_rows = sum(t.get('row_count', 0) for t in tables)
                            
                            # Get nice label
                            label = region_labels.get(suffix, suffix.upper() if suffix else 'Unknown')
                            
                            # Use first table as representative
                            table_regions.append({
                                'id': suffix,
                                'label': f"{label} ({total_rows:,} records)" if total_rows else label,
                                'table': tables[0].get('table_name', ''),
                                'all_tables': [t.get('table_name', '') for t in tables]
                            })
                        
                        # Build options
                        options = [{'id': r['id'], 'label': r['label']} for r in table_regions]
                        options.append({'id': '__all__', 'label': f'Review all data sets ({len(matching_tables)} tables combined)'})
                        
                        region_summary = ', '.join(r['label'].split(' (')[0] for r in table_regions)
                        
                        logger.warning(f"[SQL-GEN] Multiple region tables found - asking for clarification")
                        
                        # Store table info for when user responds
                        self._validation_region_tables = {r['id']: r['table'] for r in table_regions}
                        
                        return {
                            'sql': None,
                            'table': None,
                            'query_type': 'validation_clarification',
                            'clarification': SynthesizedAnswer(
                                question=question,
                                answer="",
                                confidence=0.0,
                                structured_output={
                                    'type': 'clarification_needed',
                                    'questions': [{
                                        'id': 'validation_region_scope',
                                        'question': f"I found {domain_config.get('name', domain_key)} data for multiple regions: {region_summary}. Which would you like me to review?",
                                        'type': 'radio',
                                        'options': options
                                    }],
                                    'original_question': question,
                                    'detected_mode': 'validate'
                                },
                                reasoning=[f"Found {len(matching_tables)} region-specific tables for {domain_key}"]
                            ),
                            'all_columns': col_names
                        }
                
                # Single table path (original logic)
                primary_full = matching_tables[0].get('table_name', '')
                
                # Run smart scope analysis - look at the data before asking questions
                scope_analysis = self._analyze_validation_scope(
                    question=question,
                    validation_table=primary_full,
                    validation_columns=col_names
                )
                
                # If we need clarification (multiple companies with data), ask smart question
                if scope_analysis.get('needs_clarification') and scope_analysis.get('clarification'):
                    logger.warning(f"[SQL-GEN] Smart clarification needed")
                    # Store for return - the ask() method will handle this
                    self._pending_validation_clarification = scope_analysis['clarification']
                    return {
                        'sql': None,
                        'table': primary_full,
                        'query_type': 'validation_clarification',
                        'clarification': scope_analysis['clarification'],
                        'all_columns': all_columns
                    }
                
                # Build query with smart scope
                select_cols = ', '.join(f'"{c}"' for c in col_names[:20])  # Include more columns for analysis
                sql = f'SELECT {select_cols} FROM "{primary_full}"'
                
                # Apply scope filter if we made a smart assumption
                scope_filter = scope_analysis.get('scope_filter')
                
                # Also filter to relevant domain type
                filter_parts = []
                
                # Detect if this is a workers comp question (different filtering needed)
                is_wc_question = any(wc in q_lower for wc in ['workers comp', 'work comp', 'wc', 'workers compensation'])
                
                if is_wc_question:
                    # Workers comp doesn't need tax_code filtering - the whole table is WC
                    # Just apply scope filter if any
                    logger.warning(f"[SQL-GEN] Workers Comp validation - no tax code filter needed")
                else:
                    # Tax-based validation - filter by tax type
                    question_keywords = ['sui', 'suta', 'futa', 'fit', 'fica', 'soc', 'med', 'w2', '401k', 'fein', 
                                        'sit', 'local', 'city', 'county', 'municipal']
                    filter_terms = [kw.upper() for kw in question_keywords if kw in q_lower]
                    
                    if filter_terms:
                        code_cols = [c for c in col_names if any(x in c.lower() for x in ['code', 'type', 'desc', 'tax'])]
                        if code_cols:
                            for term in filter_terms:
                                for col in code_cols[:2]:
                                    filter_parts.append(f'UPPER("{col}") LIKE \'%{term}%\'')
                
                if scope_filter:
                    filter_parts.append(f'"{scope_filter["column"]}" = \'{scope_filter["value"]}\'')
                    logger.warning(f"[SQL-GEN] Applied scope filter: {scope_filter}")
                
                if filter_parts:
                    sql += f" WHERE ({' OR '.join(filter_parts[:6])})"  # Combine with OR for tax codes
                    if scope_filter:
                        # If we have both tax filter AND scope, use AND for scope
                        tax_filters = [f for f in filter_parts if 'LIKE' in f]
                        scope_filters = [f for f in filter_parts if 'LIKE' not in f]
                        if tax_filters and scope_filters:
                            sql = f'SELECT {select_cols} FROM "{primary_full}" WHERE ({" OR ".join(tax_filters)}) AND ({" AND ".join(scope_filters)})'
                
                logger.warning(f"[SQL-GEN] Validation SQL: {sql[:200]}...")
                logger.warning(f"[SQL-GEN] Returning validation result with query_type=validation")
                
                return {
                    'sql': sql,
                    'table': primary_full.split('__')[-1] if '__' in primary_full else primary_full,
                    'query_type': 'validation',
                    'all_columns': all_columns,
                    'validation_bypass': True,
                    'smart_assumption': scope_analysis.get('smart_assumption'),
                    'scope_analysis': scope_analysis.get('analysis', {})
                }
        
        # Format all hints
        query_hint = ""
        if query_hints:
            query_hint = "\n\nHINTS:\n" + "\n".join(f"- {h}" for h in query_hints)
        
        prompt = f"""SCHEMA:
{schema_text}{relationships_text}{semantic_text}
{query_hint}

QUESTION: {question}

RULES:
1. Use ONLY columns from SCHEMA - never invent columns
2. DO NOT add WHERE for status/active/termed - filters injected automatically
3. For "show X by Y" queries: SELECT Y, COUNT(*) FROM table GROUP BY Y
4. For breakdowns/groupings, prefer KEY GROUPING DIMENSIONS listed above
5. Keep queries SIMPLE - avoid JOINs unless absolutely needed
6. ILIKE for text matching

SQL:"""
        
        logger.warning(f"[SQL-GEN] Calling orchestrator ({len(prompt)} chars, {len(relevant_tables)} tables)")
        
        result = orchestrator.generate_sql(prompt, all_columns)
        
        if result.get('success') and result.get('sql'):
            sql = result['sql'].strip()
            
            # Clean markdown
            if '```' in sql:
                sql = re.sub(r'```sql\s*', '', sql, flags=re.IGNORECASE)
                sql = re.sub(r'```\s*$', '', sql)
                sql = sql.replace('```', '').strip()
            
            logger.warning(f"[SQL-GEN] LLM raw output: {sql[:200]}")
            
            # EXPAND short aliases to full table names WITH alias preservation
            # (?!\.) prevents matching table.column references like personal.termination_date
            if hasattr(self, '_table_aliases') and self._table_aliases:
                for short_name, full_name in self._table_aliases.items():
                    # Replace FROM short_name → FROM "full_name" AS short_name
                    sql = re.sub(
                        rf'\bFROM\s+{re.escape(short_name)}\b(?!\.)(?!\s+AS)',
                        f'FROM "{full_name}" AS {short_name}',
                        sql,
                        flags=re.IGNORECASE
                    )
                    sql = re.sub(
                        rf'\bFROM\s+"{re.escape(short_name)}"(?!\.)(?!\s+AS)',
                        f'FROM "{full_name}" AS {short_name}',
                        sql,
                        flags=re.IGNORECASE
                    )
                    # Replace JOIN short_name → JOIN "full_name" AS short_name
                    sql = re.sub(
                        rf'\bJOIN\s+{re.escape(short_name)}\b(?!\.)(?!\s+AS)',
                        f'JOIN "{full_name}" AS {short_name}',
                        sql,
                        flags=re.IGNORECASE
                    )
                    sql = re.sub(
                        rf'\bJOIN\s+"{re.escape(short_name)}"(?!\.)(?!\s+AS)',
                        f'JOIN "{full_name}" AS {short_name}',
                        sql,
                        flags=re.IGNORECASE
                    )
                logger.warning(f"[SQL-GEN] After alias expansion: {sql[:200]}")
            
            # FIX GENERIC COLUMN NAMES - LLM often uses "location" instead of actual column
            # Use the mappings we built from semantic hints (table-specific), validate against selected table's columns
            if hasattr(self, '_column_mappings') and self._column_mappings and all_columns:
                # all_columns contains actual columns from selected tables
                all_columns_lower = {c.lower() for c in all_columns}
                
                for generic_term, actual_col in self._column_mappings.items():
                    # Only replace if:
                    # 1. The generic term appears in the SQL as a column
                    # 2. The actual column EXISTS in the selected table(s)
                    # 3. They're different
                    if generic_term.lower() != actual_col.lower():
                        if actual_col.lower() in all_columns_lower:
                            pattern = rf'\b{re.escape(generic_term)}\b(?!\w)'
                            if re.search(pattern, sql, re.IGNORECASE):
                                old_sql = sql
                                sql = re.sub(pattern, actual_col, sql, flags=re.IGNORECASE)
                                if sql != old_sql:
                                    logger.warning(f"[SQL-GEN] Fixed column name: {generic_term} → {actual_col}")
                        else:
                            # Column doesn't exist in selected table - check if generic term is valid
                            if generic_term.lower() in all_columns_lower:
                                logger.warning(f"[SQL-GEN] Keeping '{generic_term}' - mapped column '{actual_col}' not in selected tables")
                            else:
                                logger.warning(f"[SQL-GEN] Neither '{generic_term}' nor '{actual_col}' in selected tables - LLM may have wrong column")
            
            # STRIP LLM-generated status filters (we inject the correct one ourselves)
            # The LLM often ignores our "don't add status WHERE" instruction
            status_filter_patterns = [
                r"\bWHERE\s+\w*\.?employment_status_code\s*=\s*'[^']*'\s*",  # WHERE x.employment_status_code = 'TERM'
                r"\bAND\s+\w*\.?employment_status_code\s*=\s*'[^']*'\s*",    # AND x.employment_status_code = 'TERM'
                r"\bWHERE\s+\w*\.?employment_status\s*=\s*'[^']*'\s*",       # WHERE employment_status = 'X'
                r"\bAND\s+\w*\.?employment_status\s*=\s*'[^']*'\s*",
            ]
            for pattern in status_filter_patterns:
                if re.search(pattern, sql, re.IGNORECASE):
                    logger.warning(f"[SQL-GEN] Stripping LLM-generated status filter")
                    # If it was the only WHERE clause, remove it entirely
                    sql = re.sub(pattern, 'WHERE ', sql, count=1, flags=re.IGNORECASE)
                    # Clean up "WHERE AND" or "WHERE WHERE" that might result
                    sql = re.sub(r'\bWHERE\s+WHERE\b', 'WHERE', sql, flags=re.IGNORECASE)
                    sql = re.sub(r'\bWHERE\s+AND\b', 'WHERE', sql, flags=re.IGNORECASE)
                    sql = re.sub(r'\bWHERE\s+GROUP\b', 'GROUP', sql, flags=re.IGNORECASE)
                    sql = re.sub(r'\bWHERE\s+ORDER\b', 'ORDER', sql, flags=re.IGNORECASE)
                    sql = re.sub(r'\bWHERE\s*$', '', sql, flags=re.IGNORECASE)
            
            # INJECT FILTER CLAUSE (data-driven, not LLM-generated)
            # BUT ONLY if the filter column exists in the selected table
            logger.warning(f"[SQL-GEN] About to inject, filter_instructions={filter_instructions}")
            if filter_instructions:
                # Check if the filter column exists in the SQL's FROM table
                can_inject = self._can_inject_filter(sql, filter_instructions, all_columns)
                if can_inject:
                    sql = self._inject_where_clause(sql, filter_instructions)
                    logger.warning(f"[SQL-GEN] After filter injection: {sql[:200]}")
                else:
                    logger.warning(f"[SQL-GEN] Skipping filter injection - column not in selected table")
            
            # FIX STATE NAME PATTERNS - convert "Texas" to "TX" etc in ILIKE clauses
            sql = self._fix_state_names_in_sql(sql)
            
            # FIX DuckDB syntax: MONTH(x) → EXTRACT(MONTH FROM x)
            sql = re.sub(r'\bMONTH\s*\(\s*([^)]+)\s*\)', r'EXTRACT(MONTH FROM \1)', sql, flags=re.IGNORECASE)
            sql = re.sub(r'\bYEAR\s*\(\s*([^)]+)\s*\)', r'EXTRACT(YEAR FROM \1)', sql, flags=re.IGNORECASE)
            sql = re.sub(r'\bDAY\s*\(\s*([^)]+)\s*\)', r'EXTRACT(DAY FROM \1)', sql, flags=re.IGNORECASE)
            
            # FIX: Wrap columns with "date" in name in TRY_CAST for DATE_TRUNC and EXTRACT
            # This handles VARCHAR date columns that DuckDB can't process directly
            # Match any column name containing 'date' (case insensitive)
            # DATE_TRUNC('month', xxx_date) → DATE_TRUNC('month', TRY_CAST(xxx_date AS DATE))
            sql = re.sub(
                r"DATE_TRUNC\s*\(\s*'(\w+)'\s*,\s*(\w*date\w*)\s*\)",
                r"DATE_TRUNC('\1', TRY_CAST(\2 AS DATE))",
                sql, flags=re.IGNORECASE
            )
            # Also handle table.column format: DATE_TRUNC('month', personal.termination_date)
            sql = re.sub(
                r"DATE_TRUNC\s*\(\s*'(\w+)'\s*,\s*(\w+\.\w*date\w*)\s*\)",
                r"DATE_TRUNC('\1', TRY_CAST(\2 AS DATE))",
                sql, flags=re.IGNORECASE
            )
            
            # Wrap strftime on date columns in TRY_CAST (in case LLM used strftime directly)
            # strftime('%Y-%m', termination_date) → strftime('%Y-%m', TRY_CAST(termination_date AS DATE))
            sql = re.sub(
                r"strftime\s*\(\s*'([^']+)'\s*,\s*(\w*date\w*)\s*\)",
                r"strftime('\1', TRY_CAST(\2 AS DATE))",
                sql, flags=re.IGNORECASE
            )
            sql = re.sub(
                r"strftime\s*\(\s*'([^']+)'\s*,\s*(\w+\.\w*date\w*)\s*\)",
                r"strftime('\1', TRY_CAST(\2 AS DATE))",
                sql, flags=re.IGNORECASE
            )
            
            # EXTRACT(MONTH FROM xxx_date) → EXTRACT(MONTH FROM TRY_CAST(xxx_date AS DATE))
            sql = re.sub(
                r"EXTRACT\s*\(\s*(\w+)\s+FROM\s+(\w*date\w*)\s*\)",
                r"EXTRACT(\1 FROM TRY_CAST(\2 AS DATE))",
                sql, flags=re.IGNORECASE
            )
            # Also handle table.column format
            sql = re.sub(
                r"EXTRACT\s*\(\s*(\w+)\s+FROM\s+(\w+\.\w*date\w*)\s*\)",
                r"EXTRACT(\1 FROM TRY_CAST(\2 AS DATE))",
                sql, flags=re.IGNORECASE
            )
            
            # UPGRADE: Convert EXTRACT(MONTH FROM x) to strftime('%Y-%m', x) for year-month grouping
            # This gives us "2024-01" instead of just "1" which is much more useful
            if 'by month' in q_lower or 'per month' in q_lower:
                # Replace EXTRACT(MONTH FROM TRY_CAST(x AS DATE)) with strftime('%Y-%m', TRY_CAST(x AS DATE))
                sql = re.sub(
                    r"EXTRACT\s*\(\s*MONTH\s+FROM\s+TRY_CAST\s*\(\s*([^)]+)\s+AS\s+DATE\s*\)\s*\)",
                    r"strftime('%Y-%m', TRY_CAST(\1 AS DATE))",
                    sql, flags=re.IGNORECASE
                )
                # Also convert DATE_TRUNC('month', x) to strftime('%Y-%m', x)
                sql = re.sub(
                    r"DATE_TRUNC\s*\(\s*'month'\s*,\s*TRY_CAST\s*\(\s*([^)]+)\s+AS\s+DATE\s*\)\s*\)",
                    r"strftime('%Y-%m', TRY_CAST(\1 AS DATE))",
                    sql, flags=re.IGNORECASE
                )
                logger.warning("[SQL-GEN] Upgraded to strftime('%Y-%m') for year-month grouping")
            
            logger.warning(f"[SQL-GEN] Generated: {sql[:150]}")
            
            # AUTO-FIX: If question asks "by X" but SQL has no GROUP BY, add it
            sql_upper = sql.upper()
            if 'GROUP BY' not in sql_upper:
                # Check if question expects grouping
                group_match = re.search(r'\bby\s+(month|year|state|location|company|department)\b', q_lower)
                if group_match:
                    group_type = group_match.group(1)
                    logger.warning(f"[SQL-GEN] Question expects GROUP BY {group_type} but SQL has none - checking for aggregation")
                    
                    # Find if there's an alias we can GROUP BY
                    # Look for "AS month" or "AS termination_month" etc.
                    alias_match = re.search(rf'\bAS\s+(\w*{group_type}\w*)', sql, re.IGNORECASE)
                    if alias_match:
                        alias = alias_match.group(1)
                        # Add GROUP BY before ORDER BY or at end
                        if 'ORDER BY' in sql_upper:
                            sql = re.sub(r'\bORDER BY\b', f'GROUP BY {alias} ORDER BY', sql, flags=re.IGNORECASE)
                        else:
                            sql = sql.rstrip(';') + f' GROUP BY {alias}'
                        logger.warning(f"[SQL-GEN] Auto-added: GROUP BY {alias}")
            
            # AUTO-FIX: Add ORDER BY if missing for aggregate queries
            sql_upper = sql.upper()
            logger.warning(f"[SQL-GEN] ORDER BY check: GROUP BY={('GROUP BY' in sql_upper)}, ORDER BY missing={('ORDER BY' not in sql_upper)}")
            if 'GROUP BY' in sql_upper and 'ORDER BY' not in sql_upper:
                # For month/year queries, order chronologically
                logger.warning(f"[SQL-GEN] Checking month/year: month={('month' in q_lower)}, year={('year' in q_lower)}")
                if 'month' in q_lower or 'year' in q_lower:
                    # Find the month/date alias or column
                    month_match = re.search(r'\bAS\s+(\w*month\w*)', sql, re.IGNORECASE)
                    logger.warning(f"[SQL-GEN] Month alias match: {month_match.group(1) if month_match else 'None'}")
                    if month_match:
                        sql = sql.rstrip(';') + f' ORDER BY {month_match.group(1)} ASC'
                        logger.warning(f"[SQL-GEN] Auto-added: ORDER BY {month_match.group(1)} ASC (chronological)")
                else:
                    # For other groupings, order by count descending
                    # Only capture alias if AS keyword is present, otherwise use COUNT(*)
                    count_match = re.search(r'COUNT\s*\([^)]*\)(?:\s+AS\s+(\w+))?', sql, re.IGNORECASE)
                    if count_match:
                        count_alias = count_match.group(1) if count_match.group(1) else 'COUNT(*)'
                        sql = sql.rstrip(';') + f' ORDER BY {count_alias} DESC'
                        logger.warning(f"[SQL-GEN] Auto-added: ORDER BY {count_alias} DESC (highest first)")
            
            logger.warning(f"[SQL-GEN] Final SQL: {sql[-100:]}")
            
            # Detect query type
            sql_upper = sql.upper()
            has_group_by = 'GROUP BY' in sql_upper
            
            # GROUP BY queries return multiple rows - they're 'list' type even if they have COUNT
            if has_group_by:
                query_type = 'group'  # Special type for grouped aggregations
            elif 'COUNT(' in sql_upper and not has_group_by:
                query_type = 'count'
            elif 'SUM(' in sql_upper and not has_group_by:
                query_type = 'sum'
            elif 'AVG(' in sql_upper and not has_group_by:
                query_type = 'average'
            else:
                query_type = 'list'
            
            table_match = re.search(r'FROM\s+"?([^"\s]+)"?', sql, re.IGNORECASE)
            table_name = table_match.group(1) if table_match else 'unknown'
            
            return {
                'sql': sql,
                'table': table_name,
                'query_type': query_type,
                'all_columns': all_columns
            }
        
        return None
    
    def _try_fix_sql_from_error(self, sql: str, error_msg: str, all_columns: set) -> Optional[str]:
        """Try to fix SQL based on error message."""
        from difflib import SequenceMatcher
        
        # Fix 1: VARCHAR column used with date functions - add TRY_CAST
        if 'date_part' in error_msg.lower() and 'VARCHAR' in error_msg:
            # Find EXTRACT(... FROM column_name) patterns and wrap in TRY_CAST
            pattern = r"EXTRACT\s*\(\s*(\w+)\s+FROM\s+(\w+)\s*\)"
            match = re.search(pattern, sql, re.IGNORECASE)
            if match:
                part = match.group(1)  # MONTH, YEAR, etc.
                col = match.group(2)   # column name
                fixed_sql = re.sub(
                    pattern,
                    f"EXTRACT({part} FROM TRY_CAST({col} AS DATE))",
                    sql,
                    flags=re.IGNORECASE
                )
                logger.info(f"[SQL-FIX] Added TRY_CAST for date extraction on {col}")
                return fixed_sql
        
        # Fix 2: Column not found errors
        patterns = [
            r'does not have a column named "([^"]+)"',
            r'Referenced column "([^"]+)" not found',
            r'column "([^"]+)" not found',
        ]
        
        bad_col = None
        for pattern in patterns:
            match = re.search(pattern, error_msg, re.IGNORECASE)
            if match:
                bad_col = match.group(1)
                break
        
        if not bad_col:
            return None
        
        logger.info(f"[SQL-FIX] Bad column from error: {bad_col}")
        
        # NEW: Parse DuckDB's candidate bindings from error message
        # e.g., Candidate bindings: "tax_group_country_code", "tax_group_code", ...
        candidates = []
        candidate_match = re.search(r'Candidate bindings:\s*([^\n]+)', error_msg)
        if candidate_match:
            candidate_str = candidate_match.group(1)
            # Extract quoted column names
            candidates = re.findall(r'"([^"]+)"', candidate_str)
            logger.info(f"[SQL-FIX] DuckDB suggests: {candidates[:5]}")
        
        # Build a mapping of ALL potentially bad columns in the SQL
        # by scanning for column-like tokens not in candidates
        fixed_sql = sql
        made_fixes = False
        
        # Extract all potential column references from SQL
        # Look for word_word patterns that might be column names
        potential_cols = re.findall(r'\b([a-z][a-z0-9_]*(?:_[a-z0-9]+)+)\b', sql.lower())
        potential_cols = list(set(potential_cols))  # unique
        
        # Valid columns (from candidates or all_columns)
        valid_cols = set(c.lower() for c in candidates) | set(c.lower() for c in all_columns)
        
        for pot_col in potential_cols:
            if pot_col in valid_cols:
                continue  # Already valid
            
            # Try to find a match
            best_score = 0.5  # Threshold
            best_match = None
            
            # First check candidates (higher priority)
            for candidate in candidates:
                score = SequenceMatcher(None, pot_col, candidate.lower()).ratio()
                if score > best_score:
                    best_score = score
                    best_match = candidate
            
            # Then check all_columns
            if not best_match:
                for col in all_columns:
                    score = SequenceMatcher(None, pot_col, col.lower()).ratio()
                    if score > best_score:
                        best_score = score
                        best_match = col
            
            if best_match:
                logger.info(f"[SQL-FIX] {pot_col} → {best_match} (score: {best_score:.2f})")
                fixed_sql = re.sub(r'\b' + re.escape(pot_col) + r'\b', f'"{best_match}"', fixed_sql, flags=re.IGNORECASE)
                made_fixes = True
        
        # Also fix the specific bad_col from the error if not already fixed
        if bad_col.lower() not in valid_cols:
            best_score = 0.4
            best_match = None
            
            for candidate in candidates:
                score = SequenceMatcher(None, bad_col.lower(), candidate.lower()).ratio()
                if score > best_score:
                    best_score = score
                    best_match = candidate
            
            if best_match:
                logger.info(f"[SQL-FIX] Error column: {bad_col} → {best_match} (score: {best_score:.2f})")
                fixed_sql = re.sub(r'\b' + re.escape(bad_col) + r'\b', f'"{best_match}"', fixed_sql, flags=re.IGNORECASE)
                made_fixes = True
        
        if made_fixes:
            return fixed_sql
        
        return None
    
    def _gather_reality(self, question: str, analysis: Dict) -> List[Truth]:
        """Gather REALITY - what the customer's DATA shows."""
        if not self.structured_handler or not self.schema:
            return []
        
        truths = []
        domains = analysis.get('domains', ['general'])
        
        # Pattern cache
        pattern_cache = None
        try:
            from utils.sql_pattern_cache import initialize_patterns
            if self.project:
                pattern_cache = initialize_patterns(self.project, self.schema)
        except:
            try:
                from backend.utils.sql_pattern_cache import initialize_patterns
                if self.project:
                    pattern_cache = initialize_patterns(self.project, self.schema)
            except:
                pass
        
        try:
            sql = None
            sql_source = None
            sql_info = None
            
            # Check cache
            if pattern_cache:
                cached = pattern_cache.find_matching_pattern(question)
                if cached and cached.get('sql'):
                    sql = cached['sql']
                    sql_source = 'cache'
                    logger.warning("[SQL] Cache hit!")
            
            # Generate if no cache
            if not sql:
                sql_info = self._generate_sql_for_question(question, analysis)
                if sql_info:
                    # Check if this is a clarification request
                    if sql_info.get('query_type') == 'validation_clarification':
                        # Store the clarification so ask() can return it
                        if sql_info.get('clarification'):
                            self._pending_validation_clarification = sql_info['clarification']
                            logger.warning(f"[SQL] Stored region clarification for ask() to return")
                        # Return empty truths - the clarification will be handled by ask()
                        logger.warning(f"[SQL] Validation needs clarification, returning for ask() to handle")
                        return truths
                    
                    sql = sql_info['sql']
                    sql_source = 'llm'
                    
                    # Store smart assumption for validation questions
                    if sql_info.get('smart_assumption'):
                        self._last_smart_assumption = sql_info['smart_assumption']
                        logger.warning(f"[SQL] Stored smart assumption: {self._last_smart_assumption[:50]}...")
            
            # Execute
            if sql:
                for attempt in range(3):
                    try:
                        rows = self.structured_handler.query(sql)
                        cols = list(rows[0].keys()) if rows else []
                        self.last_executed_sql = sql
                        
                        if rows:
                            table_name = sql_info.get('table', 'query') if sql_info else 'query'
                            q_type = sql_info.get('query_type', 'list') if sql_info else 'list'
                            
                            # Look up display_name from schema for better source_name
                            display_name = table_name
                            if self.schema and self.schema.get('tables'):
                                for t in self.schema.get('tables', []):
                                    if t.get('table_name') == table_name:
                                        display_name = t.get('display_name') or table_name
                                        break
                            
                            logger.warning(f"[GATHER-REALITY] Creating Truth with query_type={q_type}, rows={len(rows)}")
                            
                            truths.append(Truth(
                                source_type='reality',
                                source_name=display_name,
                                content={
                                    'sql': sql,
                                    'columns': cols,
                                    'rows': rows,
                                    'total': len(rows),
                                    'query_type': q_type,
                                    'table': table_name,
                                    'display_name': display_name,
                                    'is_targeted_query': True
                                },
                                confidence=0.98,
                                location=f"Query: {sql}"
                            ))
                            
                            if pattern_cache and sql_source == 'llm':
                                pattern_cache.learn_pattern(question, sql, success=True)
                            
                            return truths
                        break
                        
                    except Exception as e:
                        error_msg = str(e)
                        logger.warning(f"[SQL] Failed attempt {attempt + 1}: {error_msg}")
                        
                        if sql_info and attempt < 2:
                            fixed = self._try_fix_sql_from_error(sql, error_msg, sql_info.get('all_columns', set()))
                            if fixed and fixed != sql:
                                sql = fixed
                                continue
                        break
        
        except Exception as e:
            logger.error(f"Error gathering reality: {e}")
        
        return truths
    
    def _gather_intent(self, question: str, analysis: Dict) -> List[Truth]:
        """
        Gather INTENT - what customer's DOCUMENTS say.
        
        Searches for customer documentation including:
        - intent: SOWs, requirements, meeting notes
        - configuration: Code lists, mappings (when stored as documents)
        
        Excludes reference/standards materials (those are global best practices).
        
        TRIPLE FALLBACK STRATEGY:
        1. Search by truth_type + project_id (ideal)
        2. Search by project_id only (docs without truth_type)
        3. Search ALL docs, filter manually (legacy docs)
        """
        logger.warning(f"[GATHER_INTENT] Starting - rag_handler={'SET' if self.rag_handler else 'NONE'}, project={self.project}, project_id={self.project_id}")
        
        if not self.rag_handler:
            logger.warning(f"[GATHER_INTENT] No RAG handler - returning empty")
            return []
        
        truths = []
        
        try:
            collection_name = self._get_document_collection_name()
            logger.warning(f"[GATHER_INTENT] Collection name: {collection_name}")
            if not collection_name:
                logger.warning(f"[GATHER_INTENT] No collection found - returning empty")
                return []
            
            all_results = []
            
            # =================================================================
            # FALLBACK 1: Search by truth_type + project_id (ideal path)
            # =================================================================
            if self.project_id:
                customer_truth_types = ['intent', 'configuration']
                for truth_type in customer_truth_types:
                    try:
                        logger.warning(f"[GATHER_INTENT] Fallback 1: truth_type={truth_type}, project_id={self.project_id}")
                        results = self.rag_handler.search(
                            collection_name=collection_name,
                            query=question,
                            n_results=5,
                            truth_type=truth_type,
                            project_id=self.project_id
                        )
                        logger.warning(f"[GATHER_INTENT] Fallback 1 ({truth_type}): {len(results)} results")
                        all_results.extend(results)
                    except Exception as e:
                        logger.warning(f"[GATHER_INTENT] Fallback 1 ({truth_type}) failed: {e}")
            
            # =================================================================
            # FALLBACK 2: Search by project_id only (no truth_type filter)
            # For docs uploaded without truth_type classification
            # =================================================================
            if not all_results and self.project_id:
                try:
                    logger.warning(f"[GATHER_INTENT] Fallback 2: project_id only, no truth_type filter")
                    results = self.rag_handler.search(
                        collection_name=collection_name,
                        query=question,
                        n_results=10,
                        project_id=self.project_id
                        # No truth_type filter
                    )
                    logger.warning(f"[GATHER_INTENT] Fallback 2: {len(results)} results")
                    # Filter out reference/global docs manually
                    for r in results:
                        metadata = r.get('metadata', {})
                        tt = metadata.get('truth_type', '')
                        is_global = metadata.get('is_global', False)
                        pid = metadata.get('project_id', '')
                        # Exclude reference docs and global docs
                        if tt != 'reference' and not is_global and pid != 'Global/Universal':
                            all_results.append(r)
                    logger.warning(f"[GATHER_INTENT] Fallback 2 after filtering: {len(all_results)} results")
                except Exception as e:
                    logger.warning(f"[GATHER_INTENT] Fallback 2 failed: {e}")
            
            # =================================================================
            # FALLBACK 3: Search ALL docs, filter by project name
            # For legacy docs that might have project name instead of UUID
            # =================================================================
            if not all_results:
                try:
                    logger.warning(f"[GATHER_INTENT] Fallback 3: No filters, searching ALL docs")
                    results = self.rag_handler.search(
                        collection_name=collection_name,
                        query=question,
                        n_results=20
                        # No filters at all
                    )
                    logger.warning(f"[GATHER_INTENT] Fallback 3: {len(results)} total results")
                    
                    # Log what we found for diagnostics
                    seen_projects = set()
                    seen_truth_types = set()
                    for r in results:
                        metadata = r.get('metadata', {})
                        seen_projects.add(metadata.get('project_id', 'NONE'))
                        seen_truth_types.add(metadata.get('truth_type', 'NONE'))
                    logger.warning(f"[GATHER_INTENT] Fallback 3 found project_ids: {seen_projects}")
                    logger.warning(f"[GATHER_INTENT] Fallback 3 found truth_types: {seen_truth_types}")
                    
                    # Filter to just this project (by name OR UUID) and non-reference
                    for r in results:
                        metadata = r.get('metadata', {})
                        tt = metadata.get('truth_type', '')
                        is_global = metadata.get('is_global', False)
                        pid = metadata.get('project_id', '')
                        
                        # Check if this doc belongs to our project (by UUID or name)
                        is_our_project = (
                            pid == self.project_id or  # UUID match
                            pid == self.project or      # Name match (legacy)
                            (self.project and self.project.lower() in str(pid).lower())  # Partial match
                        )
                        
                        # Exclude reference and global, include our project
                        if tt != 'reference' and not is_global and pid != 'Global/Universal':
                            if is_our_project or not pid:  # Include if our project OR no project set
                                all_results.append(r)
                    
                    logger.warning(f"[GATHER_INTENT] Fallback 3 after filtering: {len(all_results)} results")
                except Exception as e:
                    logger.warning(f"[GATHER_INTENT] Fallback 3 failed: {e}")
            
            logger.warning(f"[GATHER_INTENT] Total results after all fallbacks: {len(all_results)}")
            
            # Sort by relevance (distance) and take top results
            all_results.sort(key=lambda x: x.get('distance', 1.0))
            
            for result in all_results[:10]:  # Limit to top 10
                metadata = result.get('metadata', {})
                distance = result.get('distance', 1.0)
                doc = result.get('document', '')
                
                truths.append(Truth(
                    source_type='intent',
                    source_name=metadata.get('filename', 'Document'),
                    content=doc,
                    confidence=max(0.3, 1.0 - distance) if distance else 0.7,
                    location=f"Page {metadata.get('page', '?')}"
                ))
            
            logger.warning(f"[GATHER_INTENT] Returning {len(truths)} truths")
        
        except Exception as e:
            logger.error(f"Error gathering intent: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        return truths
    
    def _get_document_collection_name(self) -> Optional[str]:
        """Find the document collection name."""
        if not self.rag_handler:
            return None
        
        if hasattr(self, '_doc_collection_name'):
            return self._doc_collection_name
        
        try:
            collections = self.rag_handler.list_collections()
            for name in ['hcmpact_docs', 'documents', 'hcm_docs', 'xlr8_docs']:
                if name in collections:
                    self._doc_collection_name = name
                    return name
            
            for name in collections:
                if 'doc' in name.lower():
                    self._doc_collection_name = name
                    return name
            
            if collections:
                self._doc_collection_name = collections[0]
                return collections[0]
        except:
            pass
        
        return None
    
    def _gather_configuration(self, question: str, analysis: Dict) -> List[Truth]:
        """
        Gather CONFIGURATION - customer's system setup, code tables, mappings.
        
        Configuration docs include:
        - Earnings codes
        - Deduction codes  
        - Tax jurisdictions
        - Org structure
        - Pay groups
        
        These are customer-specific (filtered by project_id).
        """
        logger.warning(f"[GATHER_CONFIG] Starting - rag_handler={'SET' if self.rag_handler else 'NONE'}, project={self.project}, project_id={self.project_id}")
        
        if not self.rag_handler:
            logger.warning(f"[GATHER_CONFIG] No RAG handler - returning empty")
            return []
        
        truths = []
        
        try:
            collection_name = self._get_document_collection_name()
            logger.warning(f"[GATHER_CONFIG] Collection name: {collection_name}")
            if not collection_name:
                logger.warning(f"[GATHER_CONFIG] No collection found - returning empty")
                return []
            
            # Search for configuration docs (customer-specific)
            if self.project_id:
                try:
                    logger.warning(f"[GATHER_CONFIG] Searching truth_type=configuration, project_id={self.project_id}")
                    results = self.rag_handler.search(
                        collection_name=collection_name,
                        query=question,
                        n_results=10,
                        truth_type='configuration',
                        project_id=self.project_id
                    )
                    logger.warning(f"[GATHER_CONFIG] Found {len(results)} results")
                    
                    for result in results:
                        metadata = result.get('metadata', {})
                        distance = result.get('distance', 1.0)
                        doc = result.get('document', '')
                        
                        truths.append(Truth(
                            source_type='configuration',
                            source_name=metadata.get('filename', 'Configuration Document'),
                            content=doc,
                            confidence=max(0.3, 1.0 - distance) if distance else 0.7,
                            location=f"Page {metadata.get('page', '?')}",
                            metadata=metadata
                        ))
                except Exception as e:
                    logger.warning(f"[GATHER_CONFIG] Search failed: {e}")
            
            logger.warning(f"[GATHER_CONFIG] Returning {len(truths)} truths")
        
        except Exception as e:
            logger.error(f"Error gathering configuration: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        return truths
    
    def _gather_reference_library(self, question: str, analysis: Dict) -> Tuple[List[Truth], List[Truth], List[Truth]]:
        """
        Gather from REFERENCE LIBRARY - global docs split by type.
        
        Returns:
            Tuple of (reference, regulatory, compliance) truth lists
            
        Types:
        - reference: Product docs, how-to guides, implementation standards
        - regulatory: Laws, IRS rules, state/federal mandates
        - compliance: Audit requirements, SOC 2, internal controls
        
        All are global (no project filter).
        """
        logger.warning(f"[GATHER_REFLIB] Starting - rag_handler={'SET' if self.rag_handler else 'NONE'}")
        
        reference_truths = []
        regulatory_truths = []
        compliance_truths = []
        
        if not self.rag_handler:
            logger.warning(f"[GATHER_REFLIB] No RAG handler - returning empty")
            return reference_truths, regulatory_truths, compliance_truths
        
        try:
            collection_name = self._get_document_collection_name()
            logger.warning(f"[GATHER_REFLIB] Collection name: {collection_name}")
            if not collection_name:
                logger.warning(f"[GATHER_REFLIB] No collection found - returning empty")
                return reference_truths, regulatory_truths, compliance_truths
            
            # Search each global truth type
            for truth_type, truth_list in [
                ('reference', reference_truths),
                ('regulatory', regulatory_truths),
                ('compliance', compliance_truths)
            ]:
                try:
                    logger.warning(f"[GATHER_REFLIB] Searching truth_type={truth_type}")
                    results = self.rag_handler.search(
                        collection_name=collection_name,
                        query=question,
                        n_results=5,
                        truth_type=truth_type
                        # No project_id - these are global
                    )
                    logger.warning(f"[GATHER_REFLIB] {truth_type}: {len(results)} results")
                    
                    for result in results:
                        metadata = result.get('metadata', {})
                        distance = result.get('distance', 1.0)
                        doc = result.get('document', '')
                        
                        truth_list.append(Truth(
                            source_type=truth_type,
                            source_name=metadata.get('filename', f'{truth_type.title()} Document'),
                            content=doc,
                            confidence=max(0.3, 1.0 - distance) if distance else 0.7,
                            location=f"Page {metadata.get('page', '?')}",
                            metadata=metadata
                        ))
                except Exception as e:
                    logger.warning(f"[GATHER_REFLIB] Search for {truth_type} failed: {e}")
            
            # FALLBACK: If no results, try legacy 'reference' type that might have all docs
            total_found = len(reference_truths) + len(regulatory_truths) + len(compliance_truths)
            if total_found == 0:
                logger.warning(f"[GATHER_REFLIB] No typed results, trying fallback search for any global docs")
                try:
                    # Search without truth_type, filter for global docs
                    results = self.rag_handler.search(
                        collection_name=collection_name,
                        query=question,
                        n_results=15
                        # No filters
                    )
                    logger.warning(f"[GATHER_REFLIB] Fallback returned {len(results)} results")
                    
                    # Log what we found
                    seen_truth_types = set()
                    seen_projects = set()
                    for r in results:
                        m = r.get('metadata', {})
                        seen_truth_types.add(m.get('truth_type', 'NONE'))
                        seen_projects.add(m.get('project_id', 'NONE'))
                    logger.warning(f"[GATHER_REFLIB] Fallback found truth_types: {seen_truth_types}")
                    logger.warning(f"[GATHER_REFLIB] Fallback found project_ids: {seen_projects}")
                    
                    for result in results:
                        metadata = result.get('metadata', {})
                        distance = result.get('distance', 1.0)
                        doc = result.get('document', '')
                        
                        # Check if this is a global doc
                        pid = metadata.get('project_id', '')
                        is_global = metadata.get('is_global', False)
                        tt = metadata.get('truth_type', '')
                        
                        if is_global or pid == 'Global/Universal' or pid == '' or tt in ['reference', 'regulatory', 'compliance']:
                            # Classify based on truth_type if present
                            if tt == 'regulatory':
                                regulatory_truths.append(Truth(
                                    source_type='regulatory',
                                    source_name=metadata.get('filename', 'Regulatory Document'),
                                    content=doc,
                                    confidence=max(0.3, 1.0 - distance) if distance else 0.7,
                                    location=f"Page {metadata.get('page', '?')}",
                                    metadata=metadata
                                ))
                            elif tt == 'compliance':
                                compliance_truths.append(Truth(
                                    source_type='compliance',
                                    source_name=metadata.get('filename', 'Compliance Document'),
                                    content=doc,
                                    confidence=max(0.3, 1.0 - distance) if distance else 0.7,
                                    location=f"Page {metadata.get('page', '?')}",
                                    metadata=metadata
                                ))
                            else:
                                # Default to reference
                                reference_truths.append(Truth(
                                    source_type='reference',
                                    source_name=metadata.get('filename', 'Reference Document'),
                                    content=doc,
                                    confidence=max(0.3, 1.0 - distance) if distance else 0.7,
                                    location=f"Page {metadata.get('page', '?')}",
                                    metadata=metadata
                                ))
                    
                    logger.warning(f"[GATHER_REFLIB] After fallback: reference={len(reference_truths)}, regulatory={len(regulatory_truths)}, compliance={len(compliance_truths)}")
                    
                except Exception as e:
                    logger.warning(f"[GATHER_REFLIB] Fallback search failed: {e}")
            
            logger.warning(f"[GATHER_REFLIB] Final: reference={len(reference_truths)}, regulatory={len(regulatory_truths)}, compliance={len(compliance_truths)}")
        
        except Exception as e:
            logger.error(f"Error gathering reference library: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        return reference_truths, regulatory_truths, compliance_truths
    
    def _check_compliance(self, reality: List[Truth], configuration: List[Truth], regulatory: List[Truth]) -> Optional[Dict]:
        """
        Auto-check compliance by comparing regulatory rules against reality and configuration.
        
        This is the $500/hr Deloitte work - automated.
        Uses the Gap Detection Engine to compare across all five truths.
        
        Returns:
            Dict with compliance status, gaps identified, and recommendations
        """
        try:
            from backend.utils.gap_detection_engine import detect_conflicts_and_compliance
        except ImportError:
            try:
                from utils.gap_detection_engine import detect_conflicts_and_compliance
            except ImportError:
                logger.warning("[INTEL] Gap detection engine not available")
                return {
                    'checked': False,
                    'error': 'Gap detection engine not available',
                    'findings': [],
                    'gaps': [],
                    'status': 'review_required'
                }
        
        try:
            # Use the gap detection engine
            _, compliance_check = detect_conflicts_and_compliance(
                reality=reality,
                configuration=configuration,
                regulatory=regulatory,
                question=self.conversation_history[-1].get('question', '') if self.conversation_history else '',
                structured_handler=self.structured_handler,
                rag_handler=self.rag_handler,
            )
            
            logger.info(f"[INTEL] Compliance check: {compliance_check.get('status')} - {compliance_check.get('gap_count', 0)} gaps found")
            return compliance_check
            
        except Exception as e:
            logger.error(f"[INTEL] Compliance check failed: {e}")
            return {
                'checked': True,
                'error': str(e),
                'findings': [],
                'gaps': [],
                'status': 'review_required'
            }
    
    def _detect_conflicts(self, reality, intent, configuration, reference, regulatory, compliance) -> List[Conflict]:
        """
        Detect conflicts across all truth sources using the Gap Detection Engine.
        
        This is the brain that finds the "in betweens":
        - Reality vs Intent (What you have vs what you wanted)
        - Reality vs Regulatory (What you have vs what the law requires)
        - Configuration vs Reference (How you set it up vs best practice)
        """
        try:
            from backend.utils.gap_detection_engine import detect_conflicts_and_compliance
        except ImportError:
            try:
                from utils.gap_detection_engine import detect_conflicts_and_compliance
            except ImportError:
                logger.warning("[INTEL] Gap detection engine not available")
                return []
        
        try:
            conflicts, _ = detect_conflicts_and_compliance(
                reality=reality,
                intent=intent,
                configuration=configuration,
                reference=reference,
                regulatory=regulatory,
                compliance=compliance,
                question=self.conversation_history[-1].get('question', '') if self.conversation_history else '',
                structured_handler=self.structured_handler,
                rag_handler=self.rag_handler,
            )
            
            logger.info(f"[INTEL] Detected {len(conflicts)} conflicts across truth sources")
            return conflicts
            
        except Exception as e:
            logger.error(f"[INTEL] Conflict detection failed: {e}")
            return []
    
    def _run_proactive_checks(self, analysis: Dict) -> List[Insight]:
        insights = []
        
        if not self.structured_handler:
            return insights
        
        try:
            tables = self.schema.get('tables', [])
            domains = analysis.get('domains', ['general'])
            
            if 'employees' in domains or domains == ['general']:
                for table in tables:
                    table_name = table.get('table_name', '')
                    if any(c in table_name.lower() for c in ['personal', 'employee']):
                        try:
                            sql = f'SELECT COUNT(*) as cnt FROM "{table_name}" WHERE ssn IS NULL OR ssn = \'\''
                            result = self.structured_handler.conn.execute(sql).fetchone()
                            if result and result[0] > 0:
                                insights.append(Insight(
                                    type='anomaly',
                                    title='Missing SSN',
                                    description=f'{result[0]} employees missing SSN',
                                    data={'count': result[0]},
                                    severity='high',
                                    action_required=True
                                ))
                        except:
                            pass
                        break
        except:
            pass
        
        return insights
    
    def _synthesize_answer(
        self,
        question: str,
        mode: IntelligenceMode,
        reality: List[Truth],
        intent: List[Truth],
        configuration: List[Truth],
        reference: List[Truth],
        regulatory: List[Truth],
        compliance: List[Truth],
        conflicts: List[Conflict],
        insights: List[Insight],
        compliance_check: Optional[Dict] = None,
        context: Dict = None
    ) -> SynthesizedAnswer:
        """Synthesize a CONSULTATIVE answer from all Five Truths using LLM."""
        reasoning = []
        
        # Gather data context (REALITY)
        data_context = []
        query_type = 'list'
        result_value = None
        result_rows = []
        result_columns = []
        executed_sql = None
        
        if reality:
            for truth in reality[:3]:
                if isinstance(truth.content, dict) and 'rows' in truth.content:
                    rows = truth.content['rows']
                    cols = truth.content['columns']
                    query_type = truth.content.get('query_type', 'list')
                    executed_sql = truth.content.get('sql', '')
                    
                    logger.warning(f"[SYNTHESIZE] Processing reality with query_type={query_type}, rows={len(rows)}")
                    
                    if query_type == 'count' and rows:
                        result_value = list(rows[0].values())[0] if rows[0] else 0
                        data_context.append(f"COUNT RESULT: {result_value}")
                    elif query_type in ['sum', 'average'] and rows:
                        result_value = list(rows[0].values())[0] if rows[0] else 0
                        data_context.append(f"{query_type.upper()} RESULT: {result_value}")
                    elif query_type == 'group' and rows:
                        # GROUP BY query - show as table
                        result_rows = rows[:20]
                        result_columns = cols
                        data_context.append(f"Grouped results: {len(rows)} groups with columns: {', '.join(cols[:8])}")
                    else:
                        result_rows = rows[:20]
                        result_columns = cols
                        data_context.append(f"Found {len(rows)} rows with columns: {', '.join(cols[:8])}")
                        # Add sample data
                        for row in rows[:5]:
                            row_str = " | ".join(f"{k}: {v}" for k, v in list(row.items())[:5])
                            data_context.append(f"  {row_str}")
            reasoning.append(f"Found {len(reality)} data results (Reality)")
        
        # Gather CUSTOMER document context (Intent + Configuration)
        doc_context = []
        if intent:
            for truth in intent[:2]:
                doc_context.append(f"Customer Intent ({truth.source_name}): {str(truth.content)[:200]}")
            reasoning.append(f"Found {len(intent)} customer intent documents")
        
        if configuration:
            for truth in configuration[:2]:
                doc_context.append(f"Configuration ({truth.source_name}): {str(truth.content)[:200]}")
            reasoning.append(f"Found {len(configuration)} configuration documents")
        
        # Gather REFERENCE LIBRARY context (Reference + Regulatory + Compliance)
        reflib_context = []
        if reference:
            for truth in reference[:2]:
                reflib_context.append(f"Reference ({truth.source_name}): {str(truth.content)[:200]}")
            reasoning.append(f"Found {len(reference)} reference documents")
        
        if regulatory:
            for truth in regulatory[:2]:
                reflib_context.append(f"Regulatory ({truth.source_name}): {str(truth.content)[:200]}")
            reasoning.append(f"Found {len(regulatory)} regulatory documents")
        
        if compliance:
            for truth in compliance[:2]:
                reflib_context.append(f"Compliance ({truth.source_name}): {str(truth.content)[:200]}")
            reasoning.append(f"Found {len(compliance)} compliance documents")
        
        # Build filters context
        filters_applied = []
        if self.confirmed_facts:
            for key, val in self.confirmed_facts.items():
                if val and val != 'all':
                    filters_applied.append(f"{key}={val}")
        
        # Generate CONSULTATIVE response using LLM
        answer_text = self._generate_consultative_response(
            question=question,
            query_type=query_type,
            result_value=result_value,
            result_rows=result_rows,
            result_columns=result_columns,
            data_context=data_context,
            doc_context=doc_context,
            reflib_context=reflib_context,
            filters_applied=filters_applied,
            insights=insights,
            conflicts=conflicts,
            compliance_check=compliance_check
        )
        
        # Calculate confidence
        confidence = 0.5
        if reality:
            confidence += 0.2
        if intent:
            confidence += 0.1
        if configuration:
            confidence += 0.05
        if reference:
            confidence += 0.05
        if regulatory:
            confidence += 0.05
        if compliance:
            confidence += 0.05
        
        return SynthesizedAnswer(
            question=question,
            answer=answer_text,
            confidence=min(confidence, 0.95),
            from_reality=reality,
            from_intent=intent,
            from_configuration=configuration,
            from_reference=reference,
            from_regulatory=regulatory,
            from_compliance=compliance,
            conflicts=conflicts,
            insights=insights,
            compliance_check=compliance_check,
            structured_output=None,
            reasoning=reasoning,
            executed_sql=executed_sql or self.last_executed_sql
        )
    
    def _generate_consultative_response(
        self,
        question: str,
        query_type: str,
        result_value: Any,
        result_rows: List[Dict],
        result_columns: List[str],
        data_context: List[str],
        doc_context: List[str],
        reflib_context: List[str],
        filters_applied: List[str],
        insights: List[Insight],
        conflicts: List[Conflict] = None,
        compliance_check: Optional[Dict] = None
    ) -> str:
        """
        Generate a CONSULTATIVE response using LLM synthesis.
        
        v5.20.0: Now uses ConsultativeSynthesizer for intelligent triangulation
        across Five Truths. Falls back to template formatting if LLM fails.
        
        The Five Truths:
        1. REALITY - What the data actually shows (DuckDB)
        2. INTENT - What the customer's documents say they want
        3. CONFIGURATION - How the customer has configured the system
        4. REFERENCE - Product docs, implementation standards
        5. REGULATORY - Laws, IRS rules, compliance requirements
        
        A world-class consultant synthesizes all five, noting conflicts and providing actionable insights.
        """
        
        # =====================================================================
        # TRY LLM SYNTHESIS FIRST (v5.20.0)
        # =====================================================================
        if self._synthesizer:
            try:
                # Build structured data for synthesizer
                structured_data = {
                    'rows': result_rows or [],
                    'columns': result_columns or [],
                    'query_type': query_type,
                    'sql': getattr(self, 'last_executed_sql', ''),
                }
                
                # Handle count/sum/avg values
                if query_type in ['count', 'sum', 'average'] and result_value is not None:
                    structured_data['rows'] = [{'result': result_value}]
                    structured_data['columns'] = ['result']
                
                # Call synthesizer with all Five Truths
                answer = self._synthesizer.synthesize(
                    question=question,
                    reality=self._last_reality,
                    intent=self._last_intent,
                    configuration=self._last_configuration,
                    reference=self._last_reference,
                    regulatory=self._last_regulatory,
                    conflicts=conflicts,
                    insights=insights,
                    structured_data=structured_data
                )
                
                logger.info(f"[CONSULTATIVE] Synthesis: method={answer.synthesis_method}, confidence={answer.confidence:.0%}")
                return answer.answer
                
            except Exception as e:
                logger.error(f"[CONSULTATIVE] Synthesis failed: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        # =====================================================================
        # FALLBACK: TEMPLATE-BASED RESPONSE
        # =====================================================================
        parts = []
        
        # Get filter context
        status_filter = self.confirmed_facts.get('status', '')
        
        # =================================================================
        # TRUTH 1: REALITY (Data Results)
        # =================================================================
        if query_type == 'count' and result_value is not None:
            # Ensure count is an integer for formatting
            try:
                count = int(result_value)
            except (ValueError, TypeError):
                count = result_value
                # Can't use :, format on non-integers
                if status_filter == 'active':
                    parts.append(f"📊 **Reality:** You have **{count}** active employees in your current workforce.")
                elif status_filter == 'termed':
                    parts.append(f"📊 **Reality:** Your data shows **{count}** terminated employees.")
                else:
                    parts.append(f"📊 **Reality:** Found **{count}** employees matching your criteria.")
            else:
                # count is an integer, use comma formatting
                if status_filter == 'active':
                    parts.append(f"📊 **Reality:** You have **{count:,} active employees** in your current workforce.")
                elif status_filter == 'termed':
                    parts.append(f"📊 **Reality:** Your data shows **{count:,} terminated employees**.")
                elif status_filter == 'all':
                    parts.append(f"📊 **Reality:** Your data contains **{count:,} total employee records** across all statuses.")
                else:
                    parts.append(f"📊 **Reality:** Found **{count:,}** employees matching your criteria.")
                    
                # Add percentage context if we have distribution data
                if self.filter_candidates.get('status'):
                    for cand in self.filter_candidates['status']:
                        dist = cand.get('value_distribution', {})
                        if dist:
                            total = sum(dist.values())
                            if total > 0 and count != total:
                                pct = (count / total) * 100
                                parts.append(f"\n*({pct:.1f}% of {total:,} total records)*")
                            break
                        
        elif query_type in ['sum', 'average'] and result_value is not None:
            try:
                val = float(result_value)
                parts.append(f"📊 **Reality:** {query_type.title()} = **{val:,.2f}**")
            except (ValueError, TypeError):
                parts.append(f"📊 **Reality:** {query_type.title()} = **{result_value}**")
        
        elif query_type == 'group' and result_rows:
            # GROUP BY results - show as breakdown table
            row_count = len(result_rows)
            parts.append(f"📊 **Reality:** Breakdown by {result_columns[0] if result_columns else 'category'}:\n")
            
            if result_columns:
                display_cols = result_columns[:4]  # Show fewer cols for group results
                header = " | ".join(display_cols)
                parts.append(f"| {header} |")
                parts.append("|" + "---|" * len(display_cols))
                
                for row in result_rows[:15]:  # Show more rows for breakdowns
                    vals = []
                    for c in display_cols:
                        v = row.get(c, '')
                        # Format counts with commas
                        if isinstance(v, (int, float)) and c.lower() in ['count', 'count(*)', 'total']:
                            vals.append(f"{int(v):,}")
                        else:
                            vals.append(str(v)[:30])
                    parts.append(f"| {' | '.join(vals)} |")
                    
                if row_count > 15:
                    parts.append(f"\n*Showing top 15 of {row_count:,} groups*")
        
        elif query_type == 'validation' and result_rows:
            # VALIDATION QUERY - Run smart consultant analysis
            row_count = len(result_rows)
            logger.warning(f"[CONSULTATIVE] VALIDATION PATH TRIGGERED for {row_count} rows")
            
            # Detect validation domain from question
            domain_config = _detect_validation_domain(question)
            if not domain_config:
                # Fallback to SUI if no specific domain detected
                domain_config = {'key': 'sui', **VALIDATION_CONFIG.get('sui', {})}
            
            validation_type = domain_config.get('validation_type', 'rate')
            logger.warning(f"[CONSULTATIVE] Using validation domain: {domain_config.get('name', 'Unknown')} (type: {validation_type})")
            
            # Run appropriate validation based on type
            temporal_findings = []
            validation_findings = []
            
            if validation_type == 'rate':
                # Rate-based validation (SUI, FUTA, WC, etc.)
                if domain_config.get('temporal_check', True):
                    temporal_findings = self._analyze_temporal_context(result_rows)
                validation_findings = self._validate_rate_values(result_rows, domain_config)
            else:
                # Config-based validation (Earnings, Deductions, GL, etc.)
                validation_findings = self._validate_config(result_rows, domain_config)
            
            # Get smart assumption if we made one
            smart_assumption = getattr(self, '_last_smart_assumption', None)
            
            # Find table name from SQL
            table_name = domain_config.get('name', 'configuration')
            if hasattr(self, 'last_executed_sql') and self.last_executed_sql:
                import re
                match = re.search(r'FROM\s+"?([^"\s]+)"?', self.last_executed_sql, re.IGNORECASE)
                if match:
                    table_name = match.group(1).split('_')[-1] if '_' in match.group(1) else match.group(1)
            
            # Format as consultant response
            consultant_response = self._format_consultant_response(
                question=question,
                rows=result_rows,
                temporal_findings=temporal_findings,
                rate_findings=validation_findings,  # Works for both rate and config findings
                smart_assumption=smart_assumption,
                table_name=table_name,
                domain_config=domain_config
            )
            
            parts.append(consultant_response)
            
        elif result_rows:
            row_count = len(result_rows)
            parts.append(f"📊 **Reality:** Found **{row_count:,}** matching records\n")
            
            if result_columns:
                display_cols = result_columns[:6]
                header = " | ".join(display_cols)
                parts.append(f"| {header} |")
                parts.append("|" + "---|" * len(display_cols))
                
                for row in result_rows[:12]:
                    vals = [str(row.get(c, ''))[:25] for c in display_cols]
                    parts.append(f"| {' | '.join(vals)} |")
                    
                if row_count > 12:
                    parts.append(f"\n*Showing first 12 of {row_count:,} results*")
        else:
            parts.append("📊 **Reality:** No data found matching your criteria.")
        
        # =================================================================
        # TRUTH 2: CUSTOMER INTENT (SOWs, Requirements)  
        # =================================================================
        intent_docs = [d for d in doc_context if 'Customer Intent' in d]
        if intent_docs:
            parts.append("\n\n📋 **Customer Intent:**")
            for doc in intent_docs[:2]:
                # Extract the content part
                content = doc.split('): ', 1)[-1] if '): ' in doc else doc
                parts.append(f"- {content[:300]}")
        
        # =================================================================
        # TRUTH 3: CONFIGURATION (Code Tables, Mappings)
        # =================================================================
        config_docs = [d for d in doc_context if 'Configuration' in d]
        if config_docs:
            parts.append("\n\n⚙️ **Configuration:**")
            for doc in config_docs[:2]:
                content = doc.split('): ', 1)[-1] if '): ' in doc else doc
                parts.append(f"- {content[:300]}")
        
        # =================================================================
        # TRUTH 4: REFERENCE (Product Docs, Standards)
        # =================================================================
        ref_docs = [d for d in reflib_context if 'Reference' in d]
        if ref_docs:
            parts.append("\n\n📚 **Reference:**")
            for doc in ref_docs[:2]:
                content = doc.split('): ', 1)[-1] if '): ' in doc else doc
                parts.append(f"- {content[:300]}")
        
        # =================================================================
        # TRUTH 5: REGULATORY (Laws, IRS Rules, Mandates)
        # =================================================================
        reg_docs = [d for d in reflib_context if 'Regulatory' in d]
        if reg_docs:
            parts.append("\n\n⚖️ **Regulatory:**")
            for doc in reg_docs[:2]:
                content = doc.split('): ', 1)[-1] if '): ' in doc else doc
                parts.append(f"- {content[:300]}")
        
        # =================================================================
        # COMPLIANCE CHECK RESULTS
        # =================================================================
        comp_docs = [d for d in reflib_context if 'Compliance' in d]
        if comp_docs:
            parts.append("\n\n🔒 **Compliance:**")
            for doc in comp_docs[:2]:
                content = doc.split('): ', 1)[-1] if '): ' in doc else doc
                parts.append(f"- {content[:300]}")
        
        if compliance_check and compliance_check.get('findings'):
            parts.append("\n\n🚨 **Compliance Findings:**")
            for finding in compliance_check['findings'][:5]:
                parts.append(f"- {finding}")
        
        if compliance_check and compliance_check.get('gaps'):
            parts.append("\n\n⚠️ **Compliance Gaps:**")
            for gap in compliance_check['gaps'][:5]:
                parts.append(f"- {gap}")
        
        # =================================================================
        # INSIGHTS & CONFLICTS
        # =================================================================
        if insights:
            parts.append("\n\n---\n💡 **Insights:**")
            for insight in insights[:3]:
                icon = '🔴' if insight.severity == 'high' else '🟡' if insight.severity == 'medium' else '💡'
                parts.append(f"\n{icon} **{insight.title}**: {insight.description}")
        
        # Display conflicts from gap detection
        if conflicts:
            parts.append("\n\n---\n⚖️ **Cross-Truth Analysis:**")
            for conflict in conflicts[:5]:
                severity_icon = '🔴' if conflict.severity == 'critical' or conflict.severity == 'high' else '🟡' if conflict.severity == 'medium' else '💡'
                parts.append(f"\n{severity_icon} {conflict.description}")
                if conflict.recommendation:
                    parts.append(f"   → *{conflict.recommendation}*")
        
        # =================================================================
        # FOLLOW-UP SUGGESTIONS (Data-Driven from actual schema)
        # =================================================================
        if query_type == 'count' and result_value is not None and self.schema:
            suggestions = self._generate_data_driven_suggestions()
            if suggestions:
                parts.append("\n\n---\n**Next Steps:**")
                for suggestion in suggestions[:3]:
                    parts.append(f"- {suggestion}")
        
        return "\n".join(parts)
    
    def _generate_data_driven_suggestions(self) -> List[str]:
        """Generate follow-up suggestions based on actual columns in the schema."""
        suggestions = []
        
        if not self.schema:
            return suggestions
        
        tables = self.schema.get('tables', [])
        if not tables:
            return suggestions
        
        # Collect all column names from all tables
        all_columns = set()
        for table in tables:
            cols = table.get('columns', [])
            for col in cols:
                if isinstance(col, dict):
                    all_columns.add(col.get('name', '').lower())
                else:
                    all_columns.add(str(col).lower())
        
        # Check filter_candidates for what's actually available
        available_filters = list(self.filter_candidates.keys()) if self.filter_candidates else []
        
        # Location-based suggestions
        location_cols = [c for c in all_columns if any(x in c for x in ['location', 'state', 'city', 'region', 'site'])]
        if location_cols or 'location' in available_filters:
            suggestions.append('"Show breakdown by location" - see geographic distribution')
        
        # Organization/department suggestions
        org_cols = [c for c in all_columns if any(x in c for x in ['department', 'dept', 'org', 'division', 'cost_center', 'business_unit'])]
        if org_cols or 'organization' in available_filters:
            suggestions.append('"Break down by department" - understand org structure')
        
        # Job/position suggestions
        job_cols = [c for c in all_columns if any(x in c for x in ['job', 'position', 'title', 'role'])]
        if job_cols or 'job' in available_filters:
            suggestions.append('"Show by job title" - see role distribution')
        
        # Pay type suggestions
        pay_cols = [c for c in all_columns if any(x in c for x in ['hourly', 'salary', 'exempt', 'pay_type', 'fullpart', 'full_part'])]
        if pay_cols or 'pay_type' in available_filters:
            suggestions.append('"How many are hourly vs salary?" - workforce composition')
        
        # Employee type suggestions
        emp_type_cols = [c for c in all_columns if any(x in c for x in ['employee_type', 'emp_type', 'regular', 'temp', 'contractor'])]
        if emp_type_cols or 'employee_type' in available_filters:
            suggestions.append('"Show regular vs temporary" - employment types')
        
        # Company suggestions (for multi-company)
        company_cols = [c for c in all_columns if any(x in c for x in ['company', 'entity', 'legal_entity'])]
        if company_cols or 'company' in available_filters:
            suggestions.append('"Break down by company" - multi-entity view')
        
        # If status is 'termed', suggest termination analysis
        if self.confirmed_facts.get('status') == 'termed':
            term_cols = [c for c in all_columns if any(x in c for x in ['termination', 'term_date', 'separation'])]
            if term_cols:
                suggestions = [
                    '"Show terminations by month" - identify trends',
                    '"Which departments had most terminations?" - attrition hotspots'
                ]
        
        return suggestions
    
    def clear_clarifications(self):
        """Clear confirmed facts."""
        self.confirmed_facts = {}
