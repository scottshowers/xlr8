"""
Vacuum Extractor v2 - Intelligent Section & Column Detection
=============================================================

Philosophy: Parse now, understand later, learn forever.

Enhanced with:
- Section detection (Employee Info, Earnings, Taxes, Deductions, Pay Info)
- Column classification (Hours, Amount, Code, Rate, YTD, etc.)
- Pattern-based learning from confirmed mappings
- Vendor signature recognition

Author: XLR8 Team
"""

import os
import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

# PDF extraction
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

# Excel/CSV extraction
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

# DuckDB for storage
try:
    import duckdb
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False

logger = logging.getLogger(__name__)

# Database path
VACUUM_DB_PATH = "/data/vacuum_extracts.duckdb"


# =============================================================================
# ENUMS AND DATA CLASSES
# =============================================================================

class SectionType(Enum):
    """Standard payroll register sections"""
    EMPLOYEE_INFO = "employee_info"
    EARNINGS = "earnings"
    TAXES = "taxes"
    DEDUCTIONS = "deductions"
    PAY_INFO = "pay_info"
    UNKNOWN = "unknown"


class ColumnType(Enum):
    """Standard column types within sections"""
    # Universal
    CODE = "code"
    DESCRIPTION = "description"
    
    # Employee Info
    EMPLOYEE_ID = "employee_id"
    EMPLOYEE_NAME = "employee_name"
    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"
    SSN = "ssn"
    DEPARTMENT = "department"
    LOCATION = "location"
    JOB_TITLE = "job_title"
    PAY_RATE = "pay_rate"
    HIRE_DATE = "hire_date"
    TERM_DATE = "term_date"
    CHECK_DATE = "check_date"
    PAY_PERIOD_START = "pay_period_start"
    PAY_PERIOD_END = "pay_period_end"
    
    # Earnings
    EARNING_CODE = "earning_code"
    EARNING_DESC = "earning_description"
    HOURS_CURRENT = "hours_current"
    HOURS_YTD = "hours_ytd"
    RATE = "rate"
    AMOUNT_CURRENT = "amount_current"
    AMOUNT_YTD = "amount_ytd"
    
    # Taxes
    TAX_CODE = "tax_code"
    TAX_DESC = "tax_description"
    TAXABLE_WAGES = "taxable_wages"
    TAX_AMOUNT_CURRENT = "tax_amount_current"
    TAX_AMOUNT_YTD = "tax_amount_ytd"
    TAX_ER_CURRENT = "tax_er_current"
    TAX_ER_YTD = "tax_er_ytd"
    
    # Deductions
    DEDUCTION_CODE = "deduction_code"
    DEDUCTION_DESC = "deduction_description"
    DEDUCTION_ELECTION = "deduction_election"
    DEDUCTION_EE_CURRENT = "deduction_ee_current"
    DEDUCTION_EE_YTD = "deduction_ee_ytd"
    DEDUCTION_ER_CURRENT = "deduction_er_current"
    DEDUCTION_ER_YTD = "deduction_er_ytd"
    
    # Pay Info
    GROSS_PAY = "gross_pay"
    NET_PAY = "net_pay"
    CHECK_NUMBER = "check_number"
    DIRECT_DEPOSIT = "direct_deposit"
    
    # Unknown
    UNKNOWN = "unknown"


@dataclass
class DetectedSection:
    """Result of section detection"""
    section_type: SectionType
    confidence: float
    start_row: int
    end_row: int
    signals_matched: List[str]


@dataclass
class ColumnClassification:
    """Result of column classification"""
    column_index: int
    header: str
    detected_type: ColumnType
    confidence: float
    signals_matched: List[str]
    sample_values: List[str]


# =============================================================================
# SEED DATA - Your 100+ implementations in code
# =============================================================================

# Section detection keywords and patterns
SECTION_PATTERNS = {
    SectionType.EMPLOYEE_INFO: {
        'keywords': [
            'employee', 'emp info', 'employee information', 'emp #', 'emp no',
            'ee info', 'associate', 'worker', 'staff', 'personnel',
            'ssn', 'social security', 'hire date', 'department', 'location',
            'pay rate', 'hourly rate', 'salary'
        ],
        'header_patterns': [
            r'emp\s*(loyee)?\s*(id|#|no|number)',
            r'(first|last)\s*name',
            r'ssn|social\s*sec',
            r'hire\s*date',
            r'dept|department',
        ],
        'weight': 1.0
    },
    SectionType.EARNINGS: {
        'keywords': [
            'earnings', 'earning', 'earn', 'wages', 'pay',
            'regular', 'overtime', 'ot', 'holiday', 'vacation', 'sick', 'pto',
            'bonus', 'commission', 'shift', 'differential', 'premium',
            'hours', 'hrs', 'rate', 'amount'
        ],
        'header_patterns': [
            r'earn\s*(ing)?\s*(code|type|desc)',
            r'(curr|current|this)\s*(period)?\s*(hrs|hours|amt|amount)',
            r'ytd\s*(hrs|hours|amt|amount)',
            r'(reg|regular|ot|overtime)\s*(hrs|hours|pay|amt)?',
        ],
        'required_columns': ['code_or_desc', 'amount'],  # Must have these
        'weight': 1.0
    },
    SectionType.TAXES: {
        'keywords': [
            'tax', 'taxes', 'withholding', 'withhold',
            'federal', 'state', 'local', 'city', 'county',
            'fit', 'sit', 'lit', 'fed', 'fica', 'medicare', 'social security',
            'sui', 'sdi', 'futa', 'suta', 'oasdi',
            'taxable', 'subject'
        ],
        'header_patterns': [
            r'tax\s*(code|type|desc)',
            r'fed(eral)?\s*(tax|w/h|withhold)',
            r'state\s*(tax|w/h|withhold)',
            r'fica|medicare|soc\s*sec',
            r'taxable\s*(wages|gross)',
        ],
        'weight': 1.0
    },
    SectionType.DEDUCTIONS: {
        'keywords': [
            'deduction', 'deductions', 'ded', 'deds',
            '401k', '401(k)', '403b', 'retirement', 'pension',
            'medical', 'dental', 'vision', 'health', 'insurance', 'ins',
            'hsa', 'fsa', 'flex', 'flexible',
            'life', 'ltd', 'std', 'disability',
            'garnish', 'garnishment', 'child support', 'levy',
            'union', 'dues', 'parking', 'charity'
        ],
        'header_patterns': [
            r'ded(uction)?\s*(code|type|desc)',
            r'(ee|er|employee|employer)\s*(amt|amount|ded)',
            r'election|percent|%',
            r'401\s*k|retirement|pension',
            r'(medical|dental|vision|health)\s*(ins)?',
        ],
        'weight': 1.0
    },
    SectionType.PAY_INFO: {
        'keywords': [
            'net pay', 'net', 'take home',
            'gross pay', 'gross', 'total gross',
            'check', 'cheque', 'direct deposit', 'dd', 'ach',
            'pay summary', 'payment', 'total'
        ],
        'header_patterns': [
            r'net\s*(pay|amt|amount)?',
            r'gross\s*(pay|amt|amount)?',
            r'(check|cheque)\s*(#|no|number|amt|amount)?',
            r'direct\s*dep(osit)?',
            r'total\s*(pay|net|gross)',
        ],
        'weight': 0.8  # Slightly lower - often embedded in other sections
    }
}

# Column detection patterns
COLUMN_PATTERNS = {
    # === EMPLOYEE INFO COLUMNS ===
    ColumnType.EMPLOYEE_ID: {
        'header_keywords': ['employee id', 'emp id', 'emp #', 'emp no', 'employee number', 
                           'employee #', 'ee id', 'ee #', 'associate id', 'worker id', 
                           'badge', 'file #', 'file no', 'clock #'],
        'header_patterns': [r'emp\s*(loyee)?\s*(id|#|no|num)', r'ee\s*(id|#)', r'badge'],
        'value_patterns': [r'^\d{3,10}$', r'^[A-Z]{1,3}\d{3,8}$'],  # Numeric or alpha-numeric
        'value_characteristics': {'min_length': 2, 'max_length': 15, 'mostly_alphanumeric': True},
        'section_affinity': [SectionType.EMPLOYEE_INFO],
        'weight': 1.0
    },
    ColumnType.EMPLOYEE_NAME: {
        'header_keywords': ['employee name', 'emp name', 'name', 'associate name', 'worker name', 
                           'full name', 'employee'],
        'header_patterns': [r'^name$', r'emp\s*(loyee)?\s*name', r'full\s*name'],
        'value_patterns': [r'^[A-Za-z\s\-\'\,\.]+$'],  # Alpha with spaces, hyphens, apostrophes
        'value_characteristics': {'has_spaces': True, 'mixed_case': True, 'min_length': 3},
        'section_affinity': [SectionType.EMPLOYEE_INFO],
        'weight': 1.0
    },
    ColumnType.FIRST_NAME: {
        'header_keywords': ['first name', 'first', 'fname', 'given name'],
        'header_patterns': [r'first\s*name', r'^first$', r'^fname$'],
        'value_patterns': [r'^[A-Za-z\-\']+$'],
        'value_characteristics': {'no_spaces': True, 'mixed_case': True},
        'section_affinity': [SectionType.EMPLOYEE_INFO],
        'weight': 1.0
    },
    ColumnType.LAST_NAME: {
        'header_keywords': ['last name', 'last', 'lname', 'surname', 'family name'],
        'header_patterns': [r'last\s*name', r'^last$', r'^lname$', r'surname'],
        'value_patterns': [r'^[A-Za-z\-\']+$'],
        'value_characteristics': {'no_spaces': True, 'mixed_case': True},
        'section_affinity': [SectionType.EMPLOYEE_INFO],
        'weight': 1.0
    },
    ColumnType.SSN: {
        'header_keywords': ['ssn', 'social security', 'ss#', 'ss #', 'soc sec', 'social sec'],
        'header_patterns': [r'ssn', r'ss\s*#', r'soc(ial)?\s*sec'],
        'value_patterns': [r'^\d{3}-\d{2}-\d{4}$', r'^\d{9}$', r'^XXX-XX-\d{4}$', r'^\*{3}-\*{2}-\d{4}$'],
        'value_characteristics': {'length': 11, 'has_dashes': True},
        'section_affinity': [SectionType.EMPLOYEE_INFO],
        'weight': 1.0,
        'is_pii': True
    },
    ColumnType.DEPARTMENT: {
        'header_keywords': ['department', 'dept', 'dept code', 'dept #', 'dept name', 
                           'division', 'div', 'cost center', 'cc', 'org', 'org unit'],
        'header_patterns': [r'dep(t|artment)', r'div(ision)?', r'cost\s*cent(er|re)', r'^cc$'],
        'value_patterns': [r'^\d{2,6}$', r'^[A-Z]{2,4}\d*$'],
        'section_affinity': [SectionType.EMPLOYEE_INFO],
        'weight': 0.9
    },
    ColumnType.HIRE_DATE: {
        'header_keywords': ['hire date', 'hired', 'start date', 'date hired', 'doh', 
                           'employment date', 'original hire'],
        'header_patterns': [r'hire\s*d(ate|t)?', r'start\s*d(ate|t)?', r'^doh$'],
        'value_patterns': [r'\d{1,2}/\d{1,2}/\d{2,4}', r'\d{4}-\d{2}-\d{2}'],
        'value_characteristics': {'is_date': True},
        'section_affinity': [SectionType.EMPLOYEE_INFO],
        'weight': 1.0
    },
    ColumnType.CHECK_DATE: {
        'header_keywords': ['check date', 'pay date', 'payment date', 'paid date', 'chk date'],
        'header_patterns': [r'(check|chk|pay|payment)\s*d(ate|t)?'],
        'value_patterns': [r'\d{1,2}/\d{1,2}/\d{2,4}', r'\d{4}-\d{2}-\d{2}'],
        'value_characteristics': {'is_date': True},
        'section_affinity': [SectionType.EMPLOYEE_INFO, SectionType.PAY_INFO],
        'weight': 1.0
    },
    
    # === EARNINGS COLUMNS ===
    ColumnType.EARNING_CODE: {
        'header_keywords': ['earning code', 'earn code', 'e/c', 'pay code', 'pay type', 
                           'type', 'code', 'earn type'],
        'header_patterns': [r'earn(ing)?\s*(code|type)', r'e/c', r'^code$', r'pay\s*(code|type)'],
        'value_patterns': [r'^[A-Z]{2,6}$', r'^[A-Z]{1,3}\d{1,2}$', r'^\d{1,4}$'],
        'value_characteristics': {'max_length': 10, 'mostly_uppercase': True},
        'section_affinity': [SectionType.EARNINGS],
        'weight': 1.0
    },
    ColumnType.EARNING_DESC: {
        'header_keywords': ['earning description', 'earn desc', 'description', 'earn name', 
                           'pay description', 'earnings'],
        'header_patterns': [r'earn(ing)?\s*desc', r'^desc(ription)?$', r'^earnings$'],
        'value_keywords': ['regular', 'overtime', 'holiday', 'vacation', 'sick', 'pto', 
                          'bonus', 'commission', 'shift'],
        'section_affinity': [SectionType.EARNINGS],
        'weight': 1.0
    },
    ColumnType.HOURS_CURRENT: {
        'header_keywords': ['hours', 'hrs', 'current hours', 'curr hrs', 'this period hours',
                           'period hours', 'regular hours', 'reg hrs'],
        'header_patterns': [r'(curr|current|this|period)?\s*(hrs|hours)', r'reg\s*(hrs|hours)?'],
        'value_patterns': [r'^\d{1,3}(\.\d{1,2})?$'],
        'value_characteristics': {'is_numeric': True, 'typical_range': (0, 200)},
        'section_affinity': [SectionType.EARNINGS],
        'position_hints': ['before_ytd_hours', 'after_code'],
        'weight': 1.0
    },
    ColumnType.HOURS_YTD: {
        'header_keywords': ['ytd hours', 'ytd hrs', 'year to date hours', 'ytd', 
                           'annual hours', 'total hours'],
        'header_patterns': [r'ytd\s*(hrs|hours)', r'(year|annual)\s*to\s*date\s*(hrs|hours)?'],
        'value_patterns': [r'^\d{1,5}(\.\d{1,2})?$'],
        'value_characteristics': {'is_numeric': True, 'typical_range': (0, 3000)},
        'section_affinity': [SectionType.EARNINGS],
        'position_hints': ['after_current_hours'],
        'weight': 1.0
    },
    ColumnType.RATE: {
        'header_keywords': ['rate', 'hourly rate', 'pay rate', 'hr rate', 'rate/hr'],
        'header_patterns': [r'(hourly|pay|hr)?\s*rate', r'rate\s*/?hr'],
        'value_patterns': [r'^\$?\d{1,4}(\.\d{2,4})?$'],
        'value_characteristics': {'is_currency': True, 'typical_range': (7, 500)},
        'section_affinity': [SectionType.EARNINGS, SectionType.EMPLOYEE_INFO],
        'weight': 0.9
    },
    ColumnType.AMOUNT_CURRENT: {
        'header_keywords': ['amount', 'amt', 'current amount', 'curr amt', 'this period',
                           'current', 'period amount', 'earnings'],
        'header_patterns': [r'(curr|current|this|period)?\s*(amt|amount)', r'^amount$', r'^amt$'],
        'value_patterns': [r'^\$?\-?\d{1,7}(\.\d{2})?$', r'^\(\$?\d+(\.\d{2})?\)$'],
        'value_characteristics': {'is_currency': True},
        'section_affinity': [SectionType.EARNINGS, SectionType.TAXES, SectionType.DEDUCTIONS],
        'position_hints': ['before_ytd_amount'],
        'weight': 1.0
    },
    ColumnType.AMOUNT_YTD: {
        'header_keywords': ['ytd amount', 'ytd amt', 'year to date', 'ytd', 'annual',
                           'ytd earnings', 'total'],
        'header_patterns': [r'ytd\s*(amt|amount)?', r'(year|annual)\s*to\s*date'],
        'value_patterns': [r'^\$?\-?\d{1,8}(\.\d{2})?$'],
        'value_characteristics': {'is_currency': True, 'larger_than_current': True},
        'section_affinity': [SectionType.EARNINGS, SectionType.TAXES, SectionType.DEDUCTIONS],
        'position_hints': ['after_current_amount'],
        'weight': 1.0
    },
    
    # === TAX COLUMNS ===
    ColumnType.TAX_CODE: {
        'header_keywords': ['tax code', 'tax type', 'tax', 'code'],
        'header_patterns': [r'tax\s*(code|type)', r'^tax$'],
        'value_keywords': ['fit', 'sit', 'fed', 'federal', 'state', 'fica', 'medicare', 
                          'oasdi', 'sui', 'sdi', 'futa', 'suta'],
        'value_characteristics': {'max_length': 20},
        'section_affinity': [SectionType.TAXES],
        'weight': 1.0
    },
    ColumnType.TAX_DESC: {
        'header_keywords': ['tax description', 'tax name', 'description'],
        'header_patterns': [r'tax\s*desc', r'^desc(ription)?$'],
        'value_keywords': ['federal withholding', 'state withholding', 'fica', 
                          'social security', 'medicare', 'unemployment'],
        'section_affinity': [SectionType.TAXES],
        'weight': 1.0
    },
    ColumnType.TAXABLE_WAGES: {
        'header_keywords': ['taxable wages', 'taxable', 'subject wages', 'taxable gross',
                           'subject', 'wages'],
        'header_patterns': [r'taxable\s*(wages|gross)?', r'subject\s*(wages)?'],
        'value_patterns': [r'^\$?\d{1,8}(\.\d{2})?$'],
        'value_characteristics': {'is_currency': True},
        'section_affinity': [SectionType.TAXES],
        'weight': 1.0
    },
    ColumnType.TAX_AMOUNT_CURRENT: {
        'header_keywords': ['tax amount', 'current tax', 'tax', 'amount', 'withholding'],
        'header_patterns': [r'(curr|current)?\s*(tax)?\s*(amt|amount|w/?h)'],
        'value_patterns': [r'^\$?\d{1,6}(\.\d{2})?$'],
        'value_characteristics': {'is_currency': True},
        'section_affinity': [SectionType.TAXES],
        'weight': 1.0
    },
    ColumnType.TAX_ER_CURRENT: {
        'header_keywords': ['employer tax', 'er tax', 'er amount', 'employer', 'company'],
        'header_patterns': [r'(er|employer|company)\s*(tax|amt|amount)?'],
        'value_patterns': [r'^\$?\d{1,6}(\.\d{2})?$'],
        'value_characteristics': {'is_currency': True},
        'section_affinity': [SectionType.TAXES],
        'weight': 1.0
    },
    
    # === DEDUCTION COLUMNS ===
    ColumnType.DEDUCTION_CODE: {
        'header_keywords': ['deduction code', 'ded code', 'code', 'd/c'],
        'header_patterns': [r'ded(uction)?\s*(code|type)', r'd/c', r'^code$'],
        'value_patterns': [r'^[A-Z]{2,6}$', r'^\d{1,4}$'],
        'section_affinity': [SectionType.DEDUCTIONS],
        'weight': 1.0
    },
    ColumnType.DEDUCTION_DESC: {
        'header_keywords': ['deduction description', 'ded desc', 'description', 'deduction'],
        'header_patterns': [r'ded(uction)?\s*desc', r'^desc(ription)?$', r'^deduction$'],
        'value_keywords': ['401k', 'medical', 'dental', 'vision', 'health', 'hsa', 'fsa',
                          'life', 'ltd', 'std', 'retirement', 'union', 'garnish'],
        'section_affinity': [SectionType.DEDUCTIONS],
        'weight': 1.0
    },
    ColumnType.DEDUCTION_ELECTION: {
        'header_keywords': ['election', 'percent', '%', 'rate', 'ee election', 'employee election'],
        'header_patterns': [r'election', r'percent', r'^%$', r'ee\s*%'],
        'value_patterns': [r'^\d{1,3}(\.\d{1,2})?%?$', r'^\$\d+(\.\d{2})?$'],
        'value_characteristics': {'is_percentage_or_currency': True},
        'section_affinity': [SectionType.DEDUCTIONS],
        'weight': 1.0
    },
    ColumnType.DEDUCTION_EE_CURRENT: {
        'header_keywords': ['ee amount', 'employee amount', 'ee current', 'ee ded', 
                           'employee', 'ee'],
        'header_patterns': [r'(ee|employee)\s*(amt|amount|ded|curr)?'],
        'value_patterns': [r'^\$?\d{1,6}(\.\d{2})?$'],
        'value_characteristics': {'is_currency': True},
        'section_affinity': [SectionType.DEDUCTIONS],
        'weight': 1.0
    },
    ColumnType.DEDUCTION_ER_CURRENT: {
        'header_keywords': ['er amount', 'employer amount', 'er current', 'er ded',
                           'employer', 'company', 'er'],
        'header_patterns': [r'(er|employer|company)\s*(amt|amount|ded|curr)?'],
        'value_patterns': [r'^\$?\d{1,6}(\.\d{2})?$'],
        'value_characteristics': {'is_currency': True},
        'section_affinity': [SectionType.DEDUCTIONS],
        'weight': 1.0
    },
    
    # === PAY INFO COLUMNS ===
    ColumnType.GROSS_PAY: {
        'header_keywords': ['gross pay', 'gross', 'total gross', 'gross earnings', 
                           'total earnings'],
        'header_patterns': [r'gross\s*(pay|earnings|amt)?', r'total\s*gross'],
        'value_patterns': [r'^\$?\d{1,8}(\.\d{2})?$'],
        'value_characteristics': {'is_currency': True, 'large_value': True},
        'section_affinity': [SectionType.PAY_INFO, SectionType.EMPLOYEE_INFO],
        'weight': 1.0
    },
    ColumnType.NET_PAY: {
        'header_keywords': ['net pay', 'net', 'take home', 'net amount', 'net check'],
        'header_patterns': [r'net\s*(pay|amt|amount|check)?', r'take\s*home'],
        'value_patterns': [r'^\$?\d{1,8}(\.\d{2})?$'],
        'value_characteristics': {'is_currency': True},
        'section_affinity': [SectionType.PAY_INFO],
        'weight': 1.0
    },
    ColumnType.CHECK_NUMBER: {
        'header_keywords': ['check number', 'check #', 'check no', 'chk #', 'voucher',
                           'payment #', 'document #'],
        'header_patterns': [r'(check|chk|voucher|payment|doc)\s*(#|no|num)'],
        'value_patterns': [r'^\d{4,12}$'],
        'value_characteristics': {'is_numeric': True},
        'section_affinity': [SectionType.PAY_INFO],
        'weight': 1.0
    },
    ColumnType.DIRECT_DEPOSIT: {
        'header_keywords': ['direct deposit', 'dd amount', 'dd', 'ach', 'bank deposit'],
        'header_patterns': [r'direct\s*dep(osit)?', r'^dd$', r'^ach$'],
        'value_patterns': [r'^\$?\d{1,8}(\.\d{2})?$'],
        'value_characteristics': {'is_currency': True},
        'section_affinity': [SectionType.PAY_INFO],
        'weight': 1.0
    }
}


# =============================================================================
# MAIN CLASS
# =============================================================================

class VacuumExtractor:
    """
    Enhanced Vacuum Extractor with intelligent section/column detection.
    """
    
    def __init__(self, db_path: str = VACUUM_DB_PATH):
        """Initialize vacuum extractor with DuckDB storage"""
        if not DUCKDB_AVAILABLE:
            raise ImportError("DuckDB required for vacuum extractor")
        
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        
        # Try to connect, auto-recover from corruption
        try:
            self.conn = duckdb.connect(db_path)
            self._init_tables()
        except Exception as e:
            error_msg = str(e)
            if 'WAL' in error_msg or 'Failure while replaying' in error_msg or 'INTERNAL Error' in error_msg:
                logger.warning(f"Database corrupted, resetting: {e}")
                self._reset_corrupted_database(db_path)
                self.conn = duckdb.connect(db_path)
                self._init_tables()
            else:
                raise
        
        self._seed_patterns()
        logger.info(f"VacuumExtractor v2 initialized with {db_path}")
    
    def _reset_corrupted_database(self, db_path: str):
        """Delete corrupted database files to start fresh"""
        import glob
        
        # Close any existing connection
        try:
            if hasattr(self, 'conn') and self.conn:
                self.conn.close()
        except:
            pass
        
        # Delete all related files
        patterns = [
            db_path,
            f"{db_path}.wal",
            f"{db_path}.tmp",
            f"{db_path}-journal",
        ]
        
        for pattern in patterns:
            for filepath in glob.glob(pattern):
                try:
                    os.remove(filepath)
                    logger.info(f"Removed corrupted file: {filepath}")
                except Exception as e:
                    logger.warning(f"Could not remove {filepath}: {e}")
    
    def _init_tables(self):
        """Create database tables for extracts, patterns, and learning.
        Auto-migrates existing v1 tables to v2 schema.
        """
        
        # Check if raw_extracts exists and needs migration
        self._migrate_raw_extracts()
        
        # ===== CREATE NEW TABLES (idempotent) =====
        
        # Section patterns - learned signals for section detection
        self.conn.execute("CREATE SEQUENCE IF NOT EXISTS section_pattern_seq START 1")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS section_patterns (
                id INTEGER DEFAULT nextval('section_pattern_seq'),
                section_type VARCHAR NOT NULL,
                signal_type VARCHAR NOT NULL,
                signal_value VARCHAR NOT NULL,
                weight FLOAT DEFAULT 1.0,
                times_confirmed INTEGER DEFAULT 0,
                times_rejected INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP,
                source VARCHAR DEFAULT 'seed'
            )
        """)
        
        # Column patterns - learned signals for column classification
        self.conn.execute("CREATE SEQUENCE IF NOT EXISTS column_pattern_seq START 1")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS column_patterns (
                id INTEGER DEFAULT nextval('column_pattern_seq'),
                column_type VARCHAR NOT NULL,
                signal_type VARCHAR NOT NULL,
                signal_value VARCHAR NOT NULL,
                weight FLOAT DEFAULT 1.0,
                times_confirmed INTEGER DEFAULT 0,
                times_rejected INTEGER DEFAULT 0,
                section_affinity JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP,
                source VARCHAR DEFAULT 'seed'
            )
        """)
        
        # Vendor signatures - recognized vendor formats
        self.conn.execute("CREATE SEQUENCE IF NOT EXISTS vendor_sig_seq START 1")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS vendor_signatures (
                id INTEGER DEFAULT nextval('vendor_sig_seq'),
                vendor_name VARCHAR,
                report_type VARCHAR,
                header_signature VARCHAR,
                section_layout JSON,
                column_map JSON,
                times_matched INTEGER DEFAULT 1,
                confidence FLOAT DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_matched TIMESTAMP,
                source VARCHAR DEFAULT 'learned'
            )
        """)
        
        # Confirmed mappings - learning from user confirmations
        self.conn.execute("CREATE SEQUENCE IF NOT EXISTS mapping_seq START 1")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS confirmed_mappings (
                id INTEGER DEFAULT nextval('mapping_seq'),
                source_header VARCHAR NOT NULL,
                source_header_normalized VARCHAR,
                target_column_type VARCHAR NOT NULL,
                section_type VARCHAR,
                confidence FLOAT DEFAULT 1.0,
                times_used INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP,
                vendor_hint VARCHAR
            )
        """)
        
        self.conn.commit()
        logger.info("Vacuum v2 database tables initialized")
    
    def _migrate_raw_extracts(self):
        """Auto-migrate raw_extracts table from v1 to v2 schema"""
        
        # Check if table exists
        tables = self.conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_name = 'raw_extracts'"
        ).fetchall()
        
        if not tables:
            # Table doesn't exist - create fresh with v2 schema
            logger.info("Creating new raw_extracts table with v2 schema")
            self.conn.execute("CREATE SEQUENCE IF NOT EXISTS extract_seq START 1")
            self.conn.execute("""
                CREATE TABLE raw_extracts (
                    id INTEGER DEFAULT nextval('extract_seq'),
                    source_file VARCHAR NOT NULL,
                    project VARCHAR,
                    file_type VARCHAR,
                    page_num INTEGER,
                    table_index INTEGER,
                    raw_headers JSON,
                    raw_data JSON,
                    row_count INTEGER,
                    column_count INTEGER,
                    extraction_method VARCHAR,
                    confidence FLOAT,
                    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR DEFAULT 'raw',
                    mapped_to VARCHAR,
                    notes VARCHAR,
                    detected_section VARCHAR,
                    section_confidence FLOAT,
                    column_classifications JSON,
                    is_continuation BOOLEAN DEFAULT FALSE,
                    continues_from INTEGER
                )
            """)
            return
        
        # Table exists - check for missing columns and add them
        logger.info("Checking raw_extracts for v2 columns...")
        
        existing_columns = set()
        try:
            result = self.conn.execute("DESCRIBE raw_extracts").fetchall()
            existing_columns = {row[0] for row in result}
        except Exception as e:
            logger.warning(f"Could not describe raw_extracts: {e}")
            return
        
        # V2 columns to add
        v2_columns = [
            ("detected_section", "VARCHAR"),
            ("section_confidence", "FLOAT"),
            ("column_classifications", "JSON"),
            ("is_continuation", "BOOLEAN DEFAULT FALSE"),
            ("continues_from", "INTEGER"),
        ]
        
        for col_name, col_type in v2_columns:
            if col_name not in existing_columns:
                try:
                    self.conn.execute(f"ALTER TABLE raw_extracts ADD COLUMN {col_name} {col_type}")
                    logger.info(f"  Added column: {col_name}")
                except Exception as e:
                    logger.warning(f"  Could not add {col_name}: {e}")
            else:
                logger.debug(f"  Column exists: {col_name}")
        
        self.conn.commit()
        logger.info("raw_extracts migration complete")
    
    def _seed_patterns(self):
        """Seed the pattern tables with initial knowledge"""
        
        # Check if already seeded
        count = self.conn.execute("SELECT COUNT(*) FROM section_patterns").fetchone()[0]
        if count > 0:
            logger.info(f"Patterns already seeded ({count} section patterns)")
            return
        
        logger.info("Seeding pattern tables...")
        
        # Seed section patterns
        for section_type, patterns in SECTION_PATTERNS.items():
            # Keywords
            for keyword in patterns.get('keywords', []):
                self.conn.execute("""
                    INSERT INTO section_patterns (section_type, signal_type, signal_value, weight, source)
                    VALUES (?, 'keyword', ?, ?, 'seed')
                """, [section_type.value, keyword.lower(), patterns.get('weight', 1.0)])
            
            # Header patterns (regex)
            for pattern in patterns.get('header_patterns', []):
                self.conn.execute("""
                    INSERT INTO section_patterns (section_type, signal_type, signal_value, weight, source)
                    VALUES (?, 'header_pattern', ?, ?, 'seed')
                """, [section_type.value, pattern, patterns.get('weight', 1.0)])
        
        # Seed column patterns
        for column_type, patterns in COLUMN_PATTERNS.items():
            # Header keywords
            for keyword in patterns.get('header_keywords', []):
                self.conn.execute("""
                    INSERT INTO column_patterns (column_type, signal_type, signal_value, weight, section_affinity, source)
                    VALUES (?, 'header_keyword', ?, ?, ?, 'seed')
                """, [column_type.value, keyword.lower(), patterns.get('weight', 1.0),
                      json.dumps([s.value for s in patterns.get('section_affinity', [])])])
            
            # Header patterns (regex)
            for pattern in patterns.get('header_patterns', []):
                self.conn.execute("""
                    INSERT INTO column_patterns (column_type, signal_type, signal_value, weight, section_affinity, source)
                    VALUES (?, 'header_pattern', ?, ?, ?, 'seed')
                """, [column_type.value, pattern, patterns.get('weight', 1.0),
                      json.dumps([s.value for s in patterns.get('section_affinity', [])])])
            
            # Value patterns (regex)
            for pattern in patterns.get('value_patterns', []):
                self.conn.execute("""
                    INSERT INTO column_patterns (column_type, signal_type, signal_value, weight, section_affinity, source)
                    VALUES (?, 'value_pattern', ?, ?, ?, 'seed')
                """, [column_type.value, pattern, patterns.get('weight', 0.8),
                      json.dumps([s.value for s in patterns.get('section_affinity', [])])])
            
            # Value keywords (for descriptions)
            for keyword in patterns.get('value_keywords', []):
                self.conn.execute("""
                    INSERT INTO column_patterns (column_type, signal_type, signal_value, weight, section_affinity, source)
                    VALUES (?, 'value_keyword', ?, ?, ?, 'seed')
                """, [column_type.value, keyword.lower(), patterns.get('weight', 0.7),
                      json.dumps([s.value for s in patterns.get('section_affinity', [])])])
        
        self.conn.commit()
        
        count = self.conn.execute("SELECT COUNT(*) FROM section_patterns").fetchone()[0]
        col_count = self.conn.execute("SELECT COUNT(*) FROM column_patterns").fetchone()[0]
        logger.info(f"Seeded {count} section patterns, {col_count} column patterns")

    # =========================================================================
    # SECTION DETECTION
    # =========================================================================
    
    def detect_section(self, headers: List[str], data: List[List[str]], 
                       extract_id: int = None) -> DetectedSection:
        """
        Detect what type of section this table represents.
        
        Uses multiple signals:
        1. Header keywords (strongest signal)
        2. Header patterns (regex matches)
        3. Value patterns (what the data looks like)
        4. Learned patterns (from confirmed mappings)
        """
        scores = {section: 0.0 for section in SectionType}
        signals = {section: [] for section in SectionType}
        
        # Normalize headers for matching
        headers_lower = [h.lower().strip() for h in headers]
        headers_joined = ' '.join(headers_lower)
        
        # Get patterns from database
        section_patterns = self.conn.execute("""
            SELECT section_type, signal_type, signal_value, weight, times_confirmed
            FROM section_patterns
            ORDER BY weight DESC
        """).fetchall()
        
        for row in section_patterns:
            section_type = SectionType(row[0])
            signal_type = row[1]
            signal_value = row[2]
            weight = row[3]
            times_confirmed = row[4]
            
            # Boost weight based on confirmations
            effective_weight = weight * (1 + (times_confirmed * 0.1))
            
            matched = False
            
            if signal_type == 'keyword':
                # Check if keyword appears in any header
                if signal_value in headers_joined:
                    matched = True
                    scores[section_type] += effective_weight
                    signals[section_type].append(f"header_keyword:{signal_value}")
                
                # Also check in data values (first few rows)
                if not matched and data:
                    sample_values = ' '.join([str(cell).lower() for row in data[:5] for cell in row])
                    if signal_value in sample_values:
                        matched = True
                        scores[section_type] += effective_weight * 0.5  # Lower weight for value match
                        signals[section_type].append(f"value_keyword:{signal_value}")
            
            elif signal_type == 'header_pattern':
                # Regex match against headers
                try:
                    pattern = re.compile(signal_value, re.IGNORECASE)
                    for h in headers_lower:
                        if pattern.search(h):
                            matched = True
                            scores[section_type] += effective_weight
                            signals[section_type].append(f"header_pattern:{signal_value}")
                            break
                except re.error:
                    pass
        
        # Additional heuristics based on data characteristics
        self._apply_data_heuristics(headers, data, scores, signals)
        
        # Find best match
        best_section = max(scores, key=scores.get)
        best_score = scores[best_section]
        
        # Calculate confidence (normalize by number of signals possible)
        max_possible = sum(1 for row in section_patterns if row[0] == best_section.value)
        confidence = min(1.0, best_score / max(max_possible * 0.3, 1))
        
        # If confidence is too low, mark as unknown
        if confidence < 0.2:
            best_section = SectionType.UNKNOWN
            confidence = 0.0
        
        return DetectedSection(
            section_type=best_section,
            confidence=round(confidence, 3),
            start_row=0,
            end_row=len(data),
            signals_matched=signals[best_section][:10]  # Top 10 signals
        )
    
    def _apply_data_heuristics(self, headers: List[str], data: List[List[str]],
                                scores: Dict[SectionType, float], 
                                signals: Dict[SectionType, List[str]]):
        """Apply heuristics based on actual data values"""
        
        if not data or not data[0]:
            return
        
        # Sample first 10 rows
        sample = data[:10]
        
        for col_idx, header in enumerate(headers):
            col_values = [row[col_idx] if col_idx < len(row) else '' for row in sample]
            col_values = [str(v).strip() for v in col_values if str(v).strip()]
            
            if not col_values:
                continue
            
            # Check for SSN pattern -> Employee Info
            ssn_pattern = re.compile(r'^\d{3}-\d{2}-\d{4}$|^\d{9}$|^[X\*]{3}-[X\*]{2}-\d{4}$')
            if any(ssn_pattern.match(v) for v in col_values):
                scores[SectionType.EMPLOYEE_INFO] += 2.0
                signals[SectionType.EMPLOYEE_INFO].append("ssn_pattern_detected")
            
            # Check for small numeric values (0-200) -> likely hours (Earnings)
            try:
                numeric_vals = [float(v.replace(',', '').replace('$', '')) 
                               for v in col_values if v.replace(',', '').replace('.', '').replace('-', '').replace('$', '').isdigit()]
                if numeric_vals:
                    avg_val = sum(numeric_vals) / len(numeric_vals)
                    if 0 < avg_val < 200:
                        # Could be hours
                        if any(h in header.lower() for h in ['hr', 'hour']):
                            scores[SectionType.EARNINGS] += 1.5
                            signals[SectionType.EARNINGS].append(f"hours_range_col:{col_idx}")
            except:
                pass
            
            # Check for tax keywords in values
            tax_keywords = ['federal', 'state', 'fica', 'medicare', 'oasdi', 'fit', 'sit', 
                           'sui', 'sdi', 'futa', 'suta', 'withhold']
            for v in col_values:
                v_lower = v.lower()
                if any(kw in v_lower for kw in tax_keywords):
                    scores[SectionType.TAXES] += 1.0
                    signals[SectionType.TAXES].append(f"tax_value:{v[:20]}")
                    break
            
            # Check for deduction keywords in values
            ded_keywords = ['401k', '401(k)', 'medical', 'dental', 'vision', 'hsa', 'fsa',
                           'health', 'insurance', 'retirement', 'pension', 'union', 'garnish']
            for v in col_values:
                v_lower = v.lower()
                if any(kw in v_lower for kw in ded_keywords):
                    scores[SectionType.DEDUCTIONS] += 1.0
                    signals[SectionType.DEDUCTIONS].append(f"deduction_value:{v[:20]}")
                    break
            
            # Check for earning keywords in values
            earn_keywords = ['regular', 'overtime', 'ot', 'holiday', 'vacation', 'sick', 
                            'pto', 'bonus', 'commission']
            for v in col_values:
                v_lower = v.lower()
                if any(kw in v_lower for kw in earn_keywords):
                    scores[SectionType.EARNINGS] += 1.0
                    signals[SectionType.EARNINGS].append(f"earning_value:{v[:20]}")
                    break

    # =========================================================================
    # COLUMN CLASSIFICATION
    # =========================================================================
    
    def classify_columns(self, headers: List[str], data: List[List[str]], 
                         section_type: SectionType = None) -> List[ColumnClassification]:
        """
        Classify each column in the table.
        
        Uses:
        1. Header keyword matching
        2. Header regex patterns
        3. Value patterns (what the actual data looks like)
        4. Section context (if provided)
        5. Position hints (YTD usually after current)
        """
        classifications = []
        
        # Get column patterns from database
        if section_type and section_type != SectionType.UNKNOWN:
            # Prioritize patterns for this section
            patterns = self.conn.execute("""
                SELECT column_type, signal_type, signal_value, weight, section_affinity
                FROM column_patterns
                ORDER BY 
                    CASE WHEN section_affinity LIKE ? THEN 0 ELSE 1 END,
                    weight DESC
            """, [f'%{section_type.value}%']).fetchall()
        else:
            patterns = self.conn.execute("""
                SELECT column_type, signal_type, signal_value, weight, section_affinity
                FROM column_patterns
                ORDER BY weight DESC
            """).fetchall()
        
        # Also get learned mappings
        learned_mappings = self._get_learned_mappings()
        
        for col_idx, header in enumerate(headers):
            header_lower = header.lower().strip()
            header_normalized = re.sub(r'[^a-z0-9\s]', '', header_lower)
            
            # Get sample values for this column
            col_values = []
            for row in data[:20]:  # Sample first 20 rows
                if col_idx < len(row):
                    val = str(row[col_idx]).strip()
                    if val:
                        col_values.append(val)
            
            # Score each possible column type
            type_scores = {}
            type_signals = {}
            
            # First check learned mappings (highest priority)
            if header_lower in learned_mappings:
                mapping = learned_mappings[header_lower]
                type_scores[mapping['column_type']] = 10.0 + mapping['times_used'] * 0.5
                type_signals[mapping['column_type']] = [f"learned:{mapping['times_used']}x"]
            
            # Then check pattern database
            for row in patterns:
                col_type = row[0]
                signal_type = row[1]
                signal_value = row[2]
                weight = row[3]
                section_affinity = json.loads(row[4]) if row[4] else []
                
                # Boost if section matches
                if section_type and section_type.value in section_affinity:
                    weight *= 1.5
                
                matched = False
                
                if signal_type == 'header_keyword':
                    if signal_value in header_lower or signal_value in header_normalized:
                        matched = True
                        
                elif signal_type == 'header_pattern':
                    try:
                        if re.search(signal_value, header_lower, re.IGNORECASE):
                            matched = True
                    except re.error:
                        pass
                
                elif signal_type == 'value_pattern' and col_values:
                    try:
                        pattern = re.compile(signal_value)
                        matches = sum(1 for v in col_values if pattern.match(v))
                        if matches >= len(col_values) * 0.5:  # At least 50% match
                            matched = True
                            weight *= (matches / len(col_values))
                    except re.error:
                        pass
                
                elif signal_type == 'value_keyword' and col_values:
                    matches = sum(1 for v in col_values if signal_value in v.lower())
                    if matches >= len(col_values) * 0.3:  # At least 30% match
                        matched = True
                        weight *= (matches / len(col_values))
                
                if matched:
                    if col_type not in type_scores:
                        type_scores[col_type] = 0
                        type_signals[col_type] = []
                    type_scores[col_type] += weight
                    type_signals[col_type].append(f"{signal_type}:{signal_value[:20]}")
            
            # Apply value-based heuristics
            self._apply_column_value_heuristics(col_values, header_lower, type_scores, type_signals)
            
            # Determine best match
            if type_scores:
                best_type = max(type_scores, key=type_scores.get)
                best_score = type_scores[best_type]
                
                # Calculate confidence
                confidence = min(1.0, best_score / 5.0)  # Normalize
                
                # If very low confidence, mark as unknown
                if confidence < 0.15:
                    best_type = ColumnType.UNKNOWN.value
                    confidence = 0.0
                    type_signals[best_type] = []
                
                detected_type = ColumnType(best_type)
                signals_matched = type_signals.get(best_type, [])[:5]
            else:
                detected_type = ColumnType.UNKNOWN
                confidence = 0.0
                signals_matched = []
            
            classifications.append(ColumnClassification(
                column_index=col_idx,
                header=header,
                detected_type=detected_type,
                confidence=round(confidence, 3),
                signals_matched=signals_matched,
                sample_values=col_values[:3]
            ))
        
        # Apply positional heuristics (YTD after current, etc.)
        classifications = self._apply_positional_heuristics(classifications)
        
        return classifications
    
    def _get_learned_mappings(self) -> Dict[str, Dict]:
        """Get confirmed mappings from learning table"""
        results = self.conn.execute("""
            SELECT source_header_normalized, target_column_type, times_used
            FROM confirmed_mappings
            WHERE times_used >= 1
            ORDER BY times_used DESC
        """).fetchall()
        
        return {
            row[0]: {'column_type': row[1], 'times_used': row[2]}
            for row in results
        }
    
    def _apply_column_value_heuristics(self, values: List[str], header: str,
                                        scores: Dict[str, float], 
                                        signals: Dict[str, List[str]]):
        """Apply heuristics based on actual column values"""
        
        if not values:
            return
        
        # Detect SSN
        ssn_pattern = re.compile(r'^\d{3}-\d{2}-\d{4}$|^\d{9}$|^[X\*]{3}-[X\*]{2}-\d{4}$')
        ssn_matches = sum(1 for v in values if ssn_pattern.match(v))
        if ssn_matches >= len(values) * 0.7:
            col_type = ColumnType.SSN.value
            scores[col_type] = scores.get(col_type, 0) + 5.0
            signals[col_type] = signals.get(col_type, []) + ['ssn_format_detected']
        
        # Detect dates
        date_pattern = re.compile(r'^\d{1,2}/\d{1,2}/\d{2,4}$|^\d{4}-\d{2}-\d{2}$')
        date_matches = sum(1 for v in values if date_pattern.match(v))
        if date_matches >= len(values) * 0.7:
            # It's a date - figure out which one based on header
            if any(kw in header for kw in ['hire', 'start', 'doh']):
                col_type = ColumnType.HIRE_DATE.value
            elif any(kw in header for kw in ['check', 'pay', 'paid']):
                col_type = ColumnType.CHECK_DATE.value
            elif any(kw in header for kw in ['term', 'end', 'sep']):
                col_type = ColumnType.TERM_DATE.value
            else:
                col_type = ColumnType.CHECK_DATE.value  # Default
            scores[col_type] = scores.get(col_type, 0) + 3.0
            signals[col_type] = signals.get(col_type, []) + ['date_format_detected']
        
        # Detect currency values
        currency_pattern = re.compile(r'^\$?-?\d{1,3}(,\d{3})*(\.\d{2})?$|^\(\$?\d+(\.\d{2})?\)$')
        currency_matches = sum(1 for v in values if currency_pattern.match(v.replace(' ', '')))
        
        # Detect purely numeric
        numeric_values = []
        for v in values:
            try:
                clean = v.replace('$', '').replace(',', '').replace('(', '-').replace(')', '')
                numeric_values.append(float(clean))
            except:
                pass
        
        # If we have numeric values, check ranges
        if len(numeric_values) >= len(values) * 0.5:
            avg_val = sum(abs(v) for v in numeric_values) / len(numeric_values)
            max_val = max(abs(v) for v in numeric_values)
            
            # Hours range: 0-200 typically
            if 0 < avg_val < 100 and max_val < 250:
                if 'ytd' in header:
                    col_type = ColumnType.HOURS_YTD.value
                else:
                    col_type = ColumnType.HOURS_CURRENT.value
                scores[col_type] = scores.get(col_type, 0) + 1.5
                signals[col_type] = signals.get(col_type, []) + ['hours_range']
            
            # Rate range: typically $7-$500/hr
            elif 5 < avg_val < 200 and 'rate' in header:
                col_type = ColumnType.RATE.value
                scores[col_type] = scores.get(col_type, 0) + 2.0
                signals[col_type] = signals.get(col_type, []) + ['rate_range']
    
    def _apply_positional_heuristics(self, classifications: List[ColumnClassification]) -> List[ColumnClassification]:
        """Apply position-based heuristics (YTD usually follows Current, etc.)"""
        
        for i, col in enumerate(classifications):
            # If this column is unknown but previous was current amount/hours,
            # and this one looks numeric, it might be YTD
            if col.detected_type == ColumnType.UNKNOWN and i > 0:
                prev = classifications[i - 1]
                
                # Previous was current hours -> this might be YTD hours
                if prev.detected_type == ColumnType.HOURS_CURRENT:
                    if col.sample_values and any(v.replace(',', '').replace('.', '').isdigit() 
                                                  for v in col.sample_values):
                        # Check if values are larger (YTD > current)
                        try:
                            prev_vals = [float(v.replace(',', '')) for v in prev.sample_values if v]
                            curr_vals = [float(v.replace(',', '')) for v in col.sample_values if v]
                            if prev_vals and curr_vals and sum(curr_vals) > sum(prev_vals):
                                col.detected_type = ColumnType.HOURS_YTD
                                col.confidence = 0.6
                                col.signals_matched.append('positional:after_current_hours')
                        except:
                            pass
                
                # Previous was current amount -> this might be YTD amount
                if prev.detected_type == ColumnType.AMOUNT_CURRENT:
                    if col.sample_values:
                        col.detected_type = ColumnType.AMOUNT_YTD
                        col.confidence = 0.5
                        col.signals_matched.append('positional:after_current_amount')
        
        return classifications

    # =========================================================================
    # MAIN EXTRACTION FLOW
    # =========================================================================
    
    def vacuum_file(self, file_path: str, project: str = None) -> Dict[str, Any]:
        """
        Main entry point - extract EVERYTHING from a file with intelligent detection.
        
        Returns summary of what was found, including section/column classifications.
        """
        file_name = os.path.basename(file_path)
        file_ext = file_name.split('.')[-1].lower()
        
        result = {
            'source_file': file_name,
            'project': project,
            'file_type': file_ext,
            'tables_found': 0,
            'total_rows': 0,
            'extracts': [],
            'errors': [],
            'detected_report_type': None,
            'vendor_match': None
        }
        
        try:
            if file_ext == 'pdf':
                extracts = self._vacuum_pdf(file_path, file_name, project)
            elif file_ext in ['xlsx', 'xls']:
                extracts = self._vacuum_excel(file_path, file_name, project)
            elif file_ext == 'csv':
                extracts = self._vacuum_csv(file_path, file_name, project)
            else:
                result['errors'].append(f"Unsupported file type: {file_ext}")
                return result
            
            # For each extract, run intelligent detection
            for extract in extracts:
                extract_id = extract.get('id')
                headers = extract.get('headers', [])
                
                # Get full data for this extract
                full_extract = self.get_extract_by_id(extract_id)
                data = full_extract.get('raw_data', []) if full_extract else []
                
                # Detect section type
                section_result = self.detect_section(headers, data, extract_id)
                extract['detected_section'] = section_result.section_type.value
                extract['section_confidence'] = section_result.confidence
                extract['section_signals'] = section_result.signals_matched
                
                # Classify columns
                col_results = self.classify_columns(headers, data, section_result.section_type)
                extract['column_classifications'] = [
                    {
                        'index': c.column_index,
                        'header': c.header,
                        'detected_type': c.detected_type.value,
                        'confidence': c.confidence,
                        'signals': c.signals_matched,
                        'samples': c.sample_values
                    }
                    for c in col_results
                ]
                
                # Update database with detection results
                self._update_extract_detection(extract_id, section_result, col_results)
            
            result['extracts'] = extracts
            result['tables_found'] = len(extracts)
            result['total_rows'] = sum(e.get('row_count', 0) for e in extracts)
            
            # Try to match vendor signature
            result['vendor_match'] = self._match_vendor_signature(extracts)
            
            # Determine overall report type
            result['detected_report_type'] = self._detect_report_type(extracts)
            
            logger.info(f"Vacuumed {file_name}: {result['tables_found']} tables, "
                       f"{result['total_rows']} rows, type={result['detected_report_type']}")
            
        except Exception as e:
            logger.error(f"Vacuum extraction error: {e}", exc_info=True)
            result['errors'].append(str(e))
        
        return result
    
    def _update_extract_detection(self, extract_id: int, section: DetectedSection, 
                                   columns: List[ColumnClassification]):
        """Update extract record with detection results"""
        col_data = [
            {
                'index': c.column_index,
                'header': c.header,
                'type': c.detected_type.value,
                'confidence': c.confidence
            }
            for c in columns
        ]
        
        try:
            self.conn.execute("""
                UPDATE raw_extracts 
                SET detected_section = ?,
                    section_confidence = ?,
                    column_classifications = ?
                WHERE id = ?
            """, [section.section_type.value, section.confidence, 
                  json.dumps(col_data), extract_id])
            self.conn.commit()
        except Exception as e:
            # V1 schema - detection columns not available yet
            logger.warning(f"Could not save detection results (v1 schema?): {e}")
    
    def _match_vendor_signature(self, extracts: List[Dict]) -> Optional[Dict]:
        """Try to match extracted data against known vendor signatures"""
        if not extracts:
            return None
        
        # Create signature from headers
        all_headers = []
        for ext in extracts:
            all_headers.extend(ext.get('headers', []))
        
        if not all_headers:
            return None
        
        # Normalize and hash
        headers_normalized = sorted([h.lower().strip() for h in all_headers])
        signature = ','.join(headers_normalized[:50])  # First 50 headers
        
        # Check for matches
        result = self.conn.execute("""
            SELECT vendor_name, report_type, confidence, column_map
            FROM vendor_signatures
            WHERE header_signature = ?
            ORDER BY times_matched DESC
            LIMIT 1
        """, [signature]).fetchone()
        
        if result:
            return {
                'vendor': result[0],
                'report_type': result[1],
                'confidence': result[2],
                'column_map': json.loads(result[3]) if result[3] else {}
            }
        
        return None
    
    def _detect_report_type(self, extracts: List[Dict]) -> str:
        """Determine overall report type based on sections found"""
        sections_found = set()
        for ext in extracts:
            section = ext.get('detected_section')
            if section and section != 'unknown':
                sections_found.add(section)
        
        # Pay register has earnings, taxes, deductions
        pay_register_sections = {'earnings', 'taxes', 'deductions'}
        if pay_register_sections.issubset(sections_found):
            return 'pay_register'
        
        # Census/employee list has primarily employee info
        if 'employee_info' in sections_found and len(sections_found) <= 2:
            return 'census'
        
        # Benefits summary
        if 'deductions' in sections_found and 'earnings' not in sections_found:
            return 'benefits_summary'
        
        # Tax summary
        if 'taxes' in sections_found and len(sections_found) == 1:
            return 'tax_summary'
        
        return 'unknown'
    
    # =========================================================================
    # FILE TYPE SPECIFIC EXTRACTION (from v1, enhanced)
    # =========================================================================
    
    def _vacuum_pdf(self, file_path: str, file_name: str, project: str) -> List[Dict]:
        """Extract all tables from PDF"""
        if not PDFPLUMBER_AVAILABLE:
            raise ImportError("pdfplumber required for PDF extraction")
        
        extracts = []
        
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                try:
                    # Extract all tables on this page
                    tables = page.extract_tables()
                    
                    for table_idx, table in enumerate(tables):
                        if not table or len(table) < 2:
                            continue
                        
                        # First row as headers (might be wrong - detection will help)
                        raw_headers = table[0]
                        headers = [str(h).strip() if h else f'col_{i}' 
                                   for i, h in enumerate(raw_headers)]
                        data = table[1:]
                        
                        # Clean up data
                        cleaned_data = []
                        for row in data:
                            cleaned_row = [str(cell).strip() if cell else '' for cell in row]
                            # Skip completely empty rows
                            if any(cell for cell in cleaned_row):
                                cleaned_data.append(cleaned_row)
                        
                        if not cleaned_data:
                            continue
                        
                        # Calculate header confidence
                        confidence = self._calculate_header_confidence(headers, cleaned_data)
                        
                        # Store in database
                        extract_id = self._store_extract(
                            source_file=file_name,
                            project=project,
                            file_type='pdf',
                            page_num=page_num,
                            table_index=table_idx,
                            headers=headers,
                            data=cleaned_data,
                            method='pdfplumber',
                            confidence=confidence
                        )
                        
                        extracts.append({
                            'id': extract_id,
                            'page': page_num,
                            'table_index': table_idx,
                            'headers': headers,
                            'row_count': len(cleaned_data),
                            'column_count': len(headers),
                            'confidence': confidence,
                            'preview': cleaned_data[:3]
                        })
                        
                except Exception as e:
                    logger.warning(f"Error extracting page {page_num}: {e}")
                    continue
        
        # Detect and handle multi-page tables
        extracts = self._handle_continuation_tables(extracts, file_name, project)
        
        return extracts
    
    def _vacuum_excel(self, file_path: str, file_name: str, project: str) -> List[Dict]:
        """Extract all sheets from Excel"""
        if not PANDAS_AVAILABLE:
            raise ImportError("pandas required for Excel extraction")
        
        extracts = []
        excel_file = pd.ExcelFile(file_path)
        
        for sheet_idx, sheet_name in enumerate(excel_file.sheet_names):
            try:
                # Try to find the best header row
                best_df = None
                best_header_row = 0
                min_unnamed = float('inf')
                
                for header_row in range(15):  # Check first 15 rows
                    try:
                        df = pd.read_excel(file_path, sheet_name=sheet_name, 
                                          header=header_row, nrows=100)
                        unnamed = sum(1 for c in df.columns if str(c).startswith('Unnamed'))
                        if unnamed < min_unnamed and len(df.columns) >= 2:
                            min_unnamed = unnamed
                            best_df = df
                            best_header_row = header_row
                            if unnamed == 0:
                                break
                    except:
                        continue
                
                if best_df is None:
                    continue
                
                # Read full data with best header row
                df = pd.read_excel(file_path, sheet_name=sheet_name, header=best_header_row)
                df = df.dropna(how='all').dropna(axis=1, how='all')
                
                if df.empty:
                    continue
                
                headers = [str(c).strip() for c in df.columns]
                data = df.fillna('').astype(str).values.tolist()
                
                confidence = self._calculate_header_confidence(headers, data)
                
                extract_id = self._store_extract(
                    source_file=file_name,
                    project=project,
                    file_type='excel',
                    page_num=sheet_idx,
                    table_index=0,
                    headers=headers,
                    data=data,
                    method='pandas',
                    confidence=confidence,
                    notes=f"Sheet: {sheet_name}, Header row: {best_header_row}"
                )
                
                extracts.append({
                    'id': extract_id,
                    'page': sheet_idx,
                    'sheet_name': sheet_name,
                    'table_index': 0,
                    'headers': headers,
                    'row_count': len(data),
                    'column_count': len(headers),
                    'confidence': confidence,
                    'preview': data[:3]
                })
                
            except Exception as e:
                logger.warning(f"Error extracting sheet {sheet_name}: {e}")
                continue
        
        return extracts
    
    def _vacuum_csv(self, file_path: str, file_name: str, project: str) -> List[Dict]:
        """Extract data from CSV"""
        if not PANDAS_AVAILABLE:
            raise ImportError("pandas required for CSV extraction")
        
        extracts = []
        
        try:
            # Try to detect delimiter
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                sample = f.read(2000)
            
            # Count potential delimiters
            delimiters = [',', '\t', '|', ';']
            best_delim = ','
            max_count = 0
            for d in delimiters:
                count = sample.count(d)
                if count > max_count:
                    max_count = count
                    best_delim = d
            
            df = pd.read_csv(file_path, delimiter=best_delim, encoding='utf-8', 
                            on_bad_lines='skip')
            df = df.dropna(how='all').dropna(axis=1, how='all')
            
            if df.empty:
                return extracts
            
            headers = [str(c).strip() for c in df.columns]
            data = df.fillna('').astype(str).values.tolist()
            
            confidence = self._calculate_header_confidence(headers, data)
            
            extract_id = self._store_extract(
                source_file=file_name,
                project=project,
                file_type='csv',
                page_num=0,
                table_index=0,
                headers=headers,
                data=data,
                method='pandas',
                confidence=confidence
            )
            
            extracts.append({
                'id': extract_id,
                'page': 0,
                'table_index': 0,
                'headers': headers,
                'row_count': len(data),
                'column_count': len(headers),
                'confidence': confidence,
                'preview': data[:3]
            })
            
        except Exception as e:
            logger.error(f"CSV extraction error: {e}")
        
        return extracts
    
    def _calculate_header_confidence(self, headers: List[str], data: List[List]) -> float:
        """Calculate confidence that headers are correct"""
        score = 1.0
        
        if not headers:
            return 0.0
        
        # Penalize unnamed columns
        unnamed = sum(1 for h in headers if 'unnamed' in h.lower() or h.startswith('col_'))
        score -= (unnamed / len(headers)) * 0.3
        
        # Penalize very short headers
        short = sum(1 for h in headers if len(h) < 2)
        score -= (short / len(headers)) * 0.2
        
        # Penalize if headers look like data (all numeric)
        numeric = sum(1 for h in headers if h.replace('.', '').replace('-', '').replace(',', '').isdigit())
        score -= (numeric / len(headers)) * 0.3
        
        # Bonus for recognizable HR/payroll terms
        hr_terms = ['employee', 'emp', 'name', 'id', 'date', 'amount', 'hours', 'rate', 
                   'dept', 'code', 'tax', 'earn', 'ded', 'gross', 'net', 'pay', 'ssn']
        matches = sum(1 for h in headers if any(term in h.lower() for term in hr_terms))
        score += (matches / len(headers)) * 0.2
        
        return max(0.0, min(1.0, score))
    
    def _handle_continuation_tables(self, extracts: List[Dict], file_name: str, 
                                     project: str) -> List[Dict]:
        """Detect and merge tables that continue across pages"""
        if len(extracts) < 2:
            return extracts
        
        merged_extracts = []
        skip_indices = set()
        
        for i, current in enumerate(extracts):
            if i in skip_indices:
                continue
            
            merged = current.copy()
            
            # Look for continuations
            for j in range(i + 1, len(extracts)):
                if j in skip_indices:
                    continue
                    
                next_table = extracts[j]
                
                # Check if this is a continuation (same headers, consecutive pages)
                if (current['headers'] == next_table['headers'] and 
                    next_table['page'] == current['page'] + 1):
                    
                    # Mark as continuation
                    skip_indices.add(j)
                    merged['row_count'] += next_table['row_count']
                    merged['continues_to'] = next_table['id']
                    
                    # Update database - try v2 columns first
                    try:
                        self.conn.execute("""
                            UPDATE raw_extracts SET is_continuation = TRUE, continues_from = ?
                            WHERE id = ?
                        """, [current['id'], next_table['id']])
                    except Exception as e:
                        # V1 schema - skip continuation marking
                        logger.debug(f"Continuation columns not available: {e}")
                    
                    # Merge the data
                    full_current = self.get_extract_by_id(current['id'])
                    full_next = self.get_extract_by_id(next_table['id'])
                    if full_current and full_next:
                        merged_data = full_current.get('raw_data', []) + full_next.get('raw_data', [])
                        self.conn.execute("""
                            UPDATE raw_extracts SET raw_data = ?, row_count = ?
                            WHERE id = ?
                        """, [json.dumps(merged_data), len(merged_data), current['id']])
                    
                    current = next_table  # Continue checking for more pages
            
            merged_extracts.append(merged)
        
        self.conn.commit()
        return merged_extracts

    # =========================================================================
    # LEARNING & FEEDBACK
    # =========================================================================
    
    def confirm_section(self, extract_id: int, section_type: str, 
                        user_corrected: bool = False) -> bool:
        """
        User confirms or corrects section detection.
        Updates learning weights.
        """
        extract = self.get_extract_by_id(extract_id)
        if not extract:
            return False
        
        headers = extract.get('raw_headers', [])
        headers_lower = [h.lower() for h in headers]
        
        if user_corrected:
            # User corrected our detection - decrease weights for what we thought
            old_section = extract.get('detected_section')
            if old_section:
                # Find which patterns led us astray
                self.conn.execute("""
                    UPDATE section_patterns 
                    SET times_rejected = times_rejected + 1,
                        weight = weight * 0.95
                    WHERE section_type = ?
                    AND signal_type = 'keyword'
                    AND EXISTS (
                        SELECT 1 FROM unnest(?) AS h 
                        WHERE LOWER(signal_value) = h OR h LIKE '%' || LOWER(signal_value) || '%'
                    )
                """, [old_section, headers_lower])
        
        # Increase weights for confirmed section
        self.conn.execute("""
            UPDATE section_patterns 
            SET times_confirmed = times_confirmed + 1,
                weight = LEAST(weight * 1.05, 2.0),
                last_used = CURRENT_TIMESTAMP
            WHERE section_type = ?
            AND signal_type = 'keyword'
        """, [section_type])
        
        # Update the extract
        try:
            self.conn.execute("""
                UPDATE raw_extracts 
                SET detected_section = ?, section_confidence = 1.0
                WHERE id = ?
            """, [section_type, extract_id])
        except Exception as e:
            logger.warning(f"Could not update extract section (v1 schema?): {e}")
        
        self.conn.commit()
        logger.info(f"Section confirmed for extract {extract_id}: {section_type}")
        return True
    
    def confirm_column(self, extract_id: int, column_index: int, 
                       column_type: str, user_corrected: bool = False) -> bool:
        """
        User confirms or corrects column classification.
        Updates learning tables.
        """
        extract = self.get_extract_by_id(extract_id)
        if not extract:
            return False
        
        headers = extract.get('raw_headers', [])
        if column_index >= len(headers):
            return False
        
        header = headers[column_index]
        header_normalized = header.lower().strip()
        section_type = extract.get('detected_section')
        
        # Store confirmed mapping
        existing = self.conn.execute("""
            SELECT id FROM confirmed_mappings 
            WHERE source_header_normalized = ? AND target_column_type = ?
        """, [header_normalized, column_type]).fetchone()
        
        if existing:
            self.conn.execute("""
                UPDATE confirmed_mappings 
                SET times_used = times_used + 1, last_used = CURRENT_TIMESTAMP
                WHERE id = ?
            """, [existing[0]])
        else:
            self.conn.execute("""
                INSERT INTO confirmed_mappings 
                (source_header, source_header_normalized, target_column_type, section_type)
                VALUES (?, ?, ?, ?)
            """, [header, header_normalized, column_type, section_type])
        
        # Update column pattern weights
        if user_corrected:
            # Decrease weight for incorrect patterns
            old_classifications = extract.get('column_classifications', [])
            for col in old_classifications:
                if col.get('index') == column_index:
                    old_type = col.get('type')
                    if old_type and old_type != column_type:
                        self.conn.execute("""
                            UPDATE column_patterns 
                            SET times_rejected = times_rejected + 1,
                                weight = weight * 0.95
                            WHERE column_type = ?
                            AND signal_type = 'header_keyword'
                            AND LOWER(signal_value) = ?
                        """, [old_type, header_normalized])
        
        # Increase weight for confirmed type
        self.conn.execute("""
            UPDATE column_patterns 
            SET times_confirmed = times_confirmed + 1,
                weight = LEAST(weight * 1.05, 2.0),
                last_used = CURRENT_TIMESTAMP
            WHERE column_type = ?
        """, [column_type])
        
        # Update the extract's column classifications
        col_class = extract.get('column_classifications', [])
        if col_class:
            try:
                if isinstance(col_class, str):
                    col_class = json.loads(col_class)
                for col in col_class:
                    if col.get('index') == column_index:
                        col['type'] = column_type
                        col['confidence'] = 1.0
                        col['confirmed'] = True
                        break
                self.conn.execute("""
                    UPDATE raw_extracts SET column_classifications = ? WHERE id = ?
                """, [json.dumps(col_class), extract_id])
            except:
                pass
        
        self.conn.commit()
        logger.info(f"Column {column_index} confirmed as {column_type} for extract {extract_id}")
        return True
    
    def learn_vendor_signature(self, extracts: List[Dict], vendor_name: str, 
                                report_type: str = 'pay_register') -> bool:
        """
        Learn a vendor signature from confirmed extracts.
        """
        if not extracts:
            return False
        
        # Build signature from headers
        all_headers = []
        section_layout = []
        column_map = {}
        
        for ext in extracts:
            headers = ext.get('headers', [])
            all_headers.extend(headers)
            
            section = ext.get('detected_section')
            if section:
                section_layout.append(section)
            
            col_class = ext.get('column_classifications', [])
            for col in col_class:
                if col.get('confidence', 0) > 0.7 or col.get('confirmed'):
                    column_map[col['header']] = col.get('type')
        
        # Create signature
        headers_normalized = sorted([h.lower().strip() for h in all_headers])
        signature = ','.join(headers_normalized[:50])
        
        # Check if exists
        existing = self.conn.execute("""
            SELECT id FROM vendor_signatures WHERE header_signature = ?
        """, [signature]).fetchone()
        
        if existing:
            self.conn.execute("""
                UPDATE vendor_signatures 
                SET times_matched = times_matched + 1,
                    last_matched = CURRENT_TIMESTAMP,
                    vendor_name = COALESCE(vendor_name, ?),
                    column_map = ?
                WHERE id = ?
            """, [vendor_name, json.dumps(column_map), existing[0]])
        else:
            self.conn.execute("""
                INSERT INTO vendor_signatures 
                (vendor_name, report_type, header_signature, section_layout, column_map)
                VALUES (?, ?, ?, ?, ?)
            """, [vendor_name, report_type, signature, 
                  json.dumps(section_layout), json.dumps(column_map)])
        
        self.conn.commit()
        logger.info(f"Learned vendor signature: {vendor_name}")
        return True
    
    # =========================================================================
    # CRUD OPERATIONS
    # =========================================================================
    
    def _store_extract(self, source_file: str, project: str, file_type: str,
                       page_num: int, table_index: int, headers: List[str],
                       data: List[List], method: str, confidence: float,
                       notes: str = None) -> int:
        """Store extracted data in database"""
        
        self.conn.execute("""
            INSERT INTO raw_extracts 
            (source_file, project, file_type, page_num, table_index, 
             raw_headers, raw_data, row_count, column_count, 
             extraction_method, confidence, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            source_file, project, file_type, page_num, table_index,
            json.dumps(headers), json.dumps(data), len(data), len(headers),
            method, confidence, notes
        ])
        
        self.conn.commit()
        
        # Get the ID of inserted row
        result = self.conn.execute("""
            SELECT MAX(id) FROM raw_extracts WHERE source_file = ?
        """, [source_file]).fetchone()
        
        return result[0] if result else 0
    
    def get_extract_by_id(self, extract_id: int) -> Optional[Dict]:
        """Get single extract by ID"""
        result = self.conn.execute("""
            SELECT * FROM raw_extracts WHERE id = ?
        """, [extract_id]).fetchone()
        
        if not result:
            return None
        
        columns = [desc[0] for desc in self.conn.description]
        extract = dict(zip(columns, result))
        
        # Parse JSON fields
        if extract.get('raw_headers'):
            try:
                extract['raw_headers'] = json.loads(extract['raw_headers'])
            except:
                pass
        if extract.get('raw_data'):
            try:
                extract['raw_data'] = json.loads(extract['raw_data'])
            except:
                pass
        if extract.get('column_classifications'):
            try:
                extract['column_classifications'] = json.loads(extract['column_classifications'])
            except:
                pass
        
        return extract
    
    def get_extracts(self, project: str = None, source_file: str = None) -> List[Dict]:
        """Get all extracts, optionally filtered"""
        query = "SELECT * FROM raw_extracts WHERE 1=1"
        params = []
        
        if project:
            query += " AND project = ?"
            params.append(project)
        
        if source_file:
            query += " AND source_file = ?"
            params.append(source_file)
        
        query += " ORDER BY source_file, page_num, table_index"
        
        result = self.conn.execute(query, params).fetchall()
        columns = [desc[0] for desc in self.conn.description]
        
        extracts = []
        for row in result:
            extract = dict(zip(columns, row))
            if extract.get('raw_headers'):
                try:
                    extract['raw_headers'] = json.loads(extract['raw_headers'])
                except:
                    pass
            if extract.get('raw_data'):
                try:
                    extract['raw_data'] = json.loads(extract['raw_data'])
                except:
                    pass
            if extract.get('column_classifications'):
                try:
                    extract['column_classifications'] = json.loads(extract['column_classifications'])
                except:
                    pass
            extracts.append(extract)
        
        return extracts
    
    def get_files_summary(self, project: str = None) -> List[Dict]:
        """Get summary of all vacuumed files"""
        
        # Try v2 query first
        try:
            query = """
                SELECT 
                    source_file,
                    project,
                    file_type,
                    COUNT(*) as table_count,
                    SUM(row_count) as total_rows,
                    MIN(extracted_at) as first_extracted,
                    AVG(confidence) as avg_confidence,
                    GROUP_CONCAT(DISTINCT detected_section) as sections_found
                FROM raw_extracts
            """
            
            if project:
                query += " WHERE project = ?"
                params = [project]
            else:
                params = []
            
            query += " GROUP BY source_file, project, file_type ORDER BY first_extracted DESC"
            
            result = self.conn.execute(query, params).fetchall()
            
            return [
                {
                    'source_file': row[0],
                    'project': row[1],
                    'file_type': row[2],
                    'table_count': row[3],
                    'total_rows': row[4],
                    'first_extracted': row[5],
                    'avg_confidence': round(row[6], 2) if row[6] else 0,
                    'sections_found': row[7].split(',') if row[7] else []
                }
                for row in result
            ]
        except Exception as e:
            # Fall back to v1-compatible query (no detected_section column)
            logger.warning(f"Falling back to v1 query: {e}")
            
            query = """
                SELECT 
                    source_file,
                    project,
                    file_type,
                    COUNT(*) as table_count,
                    SUM(row_count) as total_rows,
                    MIN(extracted_at) as first_extracted,
                    AVG(confidence) as avg_confidence
                FROM raw_extracts
            """
            
            if project:
                query += " WHERE project = ?"
                params = [project]
            else:
                params = []
            
            query += " GROUP BY source_file, project, file_type ORDER BY first_extracted DESC"
            
            result = self.conn.execute(query, params).fetchall()
            
            return [
                {
                    'source_file': row[0],
                    'project': row[1],
                    'file_type': row[2],
                    'table_count': row[3],
                    'total_rows': row[4],
                    'first_extracted': row[5],
                    'avg_confidence': round(row[6], 2) if row[6] else 0,
                    'sections_found': []  # Not available in v1
                }
                for row in result
            ]
    
    def delete_file_extracts(self, source_file: str, project: str = None) -> int:
        """Delete all extracts for a file"""
        if project:
            result = self.conn.execute("""
                DELETE FROM raw_extracts WHERE source_file = ? AND project = ?
            """, [source_file, project])
        else:
            result = self.conn.execute("""
                DELETE FROM raw_extracts WHERE source_file = ?
            """, [source_file])
        
        self.conn.commit()
        return result.rowcount
    
    def delete_all_extracts(self) -> int:
        """Delete all extracts (reset)"""
        result = self.conn.execute("DELETE FROM raw_extracts")
        self.conn.commit()
        return result.rowcount
    
    def get_pattern_stats(self) -> Dict:
        """Get statistics on learned patterns"""
        section_count = self.conn.execute(
            "SELECT COUNT(*) FROM section_patterns"
        ).fetchone()[0]
        
        column_count = self.conn.execute(
            "SELECT COUNT(*) FROM column_patterns"
        ).fetchone()[0]
        
        mapping_count = self.conn.execute(
            "SELECT COUNT(*) FROM confirmed_mappings"
        ).fetchone()[0]
        
        vendor_count = self.conn.execute(
            "SELECT COUNT(*) FROM vendor_signatures"
        ).fetchone()[0]
        
        top_mappings = self.conn.execute("""
            SELECT source_header, target_column_type, times_used
            FROM confirmed_mappings
            ORDER BY times_used DESC
            LIMIT 10
        """).fetchall()
        
        return {
            'section_patterns': section_count,
            'column_patterns': column_count,
            'confirmed_mappings': mapping_count,
            'vendor_signatures': vendor_count,
            'top_mappings': [
                {'header': r[0], 'type': r[1], 'times_used': r[2]}
                for r in top_mappings
            ]
        }
    
    def export_learning_data(self) -> Dict:
        """Export all learning data for backup/transfer"""
        return {
            'section_patterns': self.conn.execute(
                "SELECT * FROM section_patterns WHERE source != 'seed'"
            ).fetchall(),
            'column_patterns': self.conn.execute(
                "SELECT * FROM column_patterns WHERE source != 'seed'"
            ).fetchall(),
            'confirmed_mappings': self.conn.execute(
                "SELECT * FROM confirmed_mappings"
            ).fetchall(),
            'vendor_signatures': self.conn.execute(
                "SELECT * FROM vendor_signatures"
            ).fetchall()
        }
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_vacuum_extractor: Optional[VacuumExtractor] = None

def get_vacuum_extractor() -> VacuumExtractor:
    """Get or create singleton extractor"""
    global _vacuum_extractor
    if _vacuum_extractor is None:
        _vacuum_extractor = VacuumExtractor()
    return _vacuum_extractor
