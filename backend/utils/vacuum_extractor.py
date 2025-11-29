"""
Vacuum Extractor - Core extraction engine for pay register processing
======================================================================
Deploy to: backend/utils/vacuum_extractor.py

This is the main extraction class that:
- Opens PDFs/Excel/CSV files
- Extracts tables with intelligent detection
- Classifies sections (earnings, taxes, deductions, etc.)
- Classifies columns within each section
- Stores extracts in Supabase
- Learns from user corrections

Author: XLR8 Team
"""

import os
import sys
import json
import logging
import re
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime

# PDF extraction
try:
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# Excel extraction
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

# Supabase
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS AND DATA CLASSES
# =============================================================================

class SectionType(Enum):
    """Types of sections in a pay register"""
    EMPLOYEE_INFO = "employee_info"
    EARNINGS = "earnings"
    TAXES = "taxes"
    DEDUCTIONS = "deductions"
    PAY_INFO = "pay_info"
    UNKNOWN = "unknown"


class ColumnType(Enum):
    """Types of columns within sections"""
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
    
    # Earnings
    EARNING_CODE = "earning_code"
    EARNING_DESCRIPTION = "earning_description"
    HOURS_CURRENT = "hours_current"
    HOURS_YTD = "hours_ytd"
    RATE = "rate"
    AMOUNT_CURRENT = "amount_current"
    AMOUNT_YTD = "amount_ytd"
    
    # Taxes
    TAX_CODE = "tax_code"
    TAX_DESCRIPTION = "tax_description"
    TAXABLE_WAGES = "taxable_wages"
    TAX_AMOUNT_CURRENT = "tax_amount_current"
    TAX_AMOUNT_YTD = "tax_amount_ytd"
    TAX_ER_CURRENT = "tax_er_current"
    TAX_ER_YTD = "tax_er_ytd"
    
    # Deductions
    DEDUCTION_CODE = "deduction_code"
    DEDUCTION_DESCRIPTION = "deduction_description"
    DEDUCTION_EE_CURRENT = "deduction_ee_current"
    DEDUCTION_EE_YTD = "deduction_ee_ytd"
    DEDUCTION_ER_CURRENT = "deduction_er_current"
    DEDUCTION_ER_YTD = "deduction_er_ytd"
    
    # Pay Info
    GROSS_PAY = "gross_pay"
    NET_PAY = "net_pay"
    CHECK_NUMBER = "check_number"
    DIRECT_DEPOSIT = "direct_deposit"
    
    # Generic
    CODE = "code"
    DESCRIPTION = "description"
    UNKNOWN = "unknown"


@dataclass
class SectionDetectionResult:
    """Result of section detection"""
    section_type: SectionType
    confidence: float
    signals_matched: List[str] = field(default_factory=list)


@dataclass
class ColumnClassificationResult:
    """Result of column classification"""
    column_index: int
    header: str
    detected_type: ColumnType
    confidence: float
    signals_matched: List[str] = field(default_factory=list)


# =============================================================================
# DETECTION PATTERNS
# =============================================================================

SECTION_PATTERNS = {
    SectionType.EARNINGS: {
        'headers': [r'earning', r'hours', r'rate', r'regular', r'overtime', r'ot\b', r'pay\s*code'],
        'codes': ['REG', 'REGULAR', 'OT', 'OVERTIME', 'HOL', 'HOLIDAY', 'VAC', 'VACATION', 
                  'SICK', 'PTO', 'BONUS', 'COMMISSION', 'GROSS'],
        'weight': 1.0
    },
    SectionType.TAXES: {
        'headers': [r'tax', r'federal', r'state', r'fica', r'medicare', r'soc\s*sec', r'withhold'],
        'codes': ['FED', 'FEDERAL', 'FWT', 'FICA', 'SS', 'SOCSEC', 'MED', 'MEDICARE',
                  'STATE', 'SIT', 'SWT', 'LOCAL', 'CITY', 'FUTA', 'SUTA'],
        'weight': 1.0
    },
    SectionType.DEDUCTIONS: {
        'headers': [r'deduction', r'401k', r'medical', r'dental', r'vision', r'health', r'insurance'],
        'codes': ['401K', '401', 'MEDICAL', 'DENTAL', 'VISION', 'HEALTH', 'LIFE', 
                  'HSA', 'FSA', 'UNION', 'DUES', 'GARNISH', 'LOAN', 'FLEX'],
        'weight': 1.0
    },
    SectionType.EMPLOYEE_INFO: {
        'headers': [r'employee', r'name', r'id\b', r'ssn', r'department', r'dept', r'location', 
                    r'hire\s*date', r'job\s*title', r'position'],
        'codes': [],
        'weight': 0.8
    },
    SectionType.PAY_INFO: {
        'headers': [r'gross\s*pay', r'net\s*pay', r'total', r'check', r'direct\s*deposit', r'dd\b'],
        'codes': [],
        'weight': 0.9
    }
}

COLUMN_PATTERNS = {
    # Employee Info columns
    ColumnType.EMPLOYEE_ID: [r'emp.*id', r'employee.*#', r'emp.*#', r'ee.*id', r'^id$'],
    ColumnType.EMPLOYEE_NAME: [r'employee.*name', r'^name$', r'full.*name'],
    ColumnType.FIRST_NAME: [r'first.*name', r'fname', r'^first$'],
    ColumnType.LAST_NAME: [r'last.*name', r'lname', r'^last$', r'surname'],
    ColumnType.SSN: [r'ssn', r'soc.*sec', r'social'],
    ColumnType.DEPARTMENT: [r'dept', r'department', r'division'],
    ColumnType.LOCATION: [r'location', r'loc\b', r'site', r'branch'],
    ColumnType.JOB_TITLE: [r'job.*title', r'title', r'position', r'job.*code'],
    ColumnType.HIRE_DATE: [r'hire.*date', r'start.*date', r'employed'],
    
    # Earnings columns
    ColumnType.EARNING_CODE: [r'earn.*code', r'pay.*code', r'^code$', r'^type$'],
    ColumnType.EARNING_DESCRIPTION: [r'earn.*desc', r'description', r'^desc$'],
    ColumnType.HOURS_CURRENT: [r'cur.*hrs', r'cur.*hours', r'^hours$', r'period.*hrs'],
    ColumnType.HOURS_YTD: [r'ytd.*hrs', r'ytd.*hours', r'year.*hours'],
    ColumnType.RATE: [r'^rate$', r'pay.*rate', r'hourly', r'hrly'],
    ColumnType.AMOUNT_CURRENT: [r'cur.*amt', r'cur.*amount', r'^amount$', r'period.*amt', r'current$'],
    ColumnType.AMOUNT_YTD: [r'ytd.*amt', r'ytd.*amount', r'ytd$', r'year.*to.*date'],
    
    # Tax columns
    ColumnType.TAX_CODE: [r'tax.*code', r'^code$'],
    ColumnType.TAX_DESCRIPTION: [r'tax.*desc', r'description'],
    ColumnType.TAXABLE_WAGES: [r'taxable', r'wages', r'subject'],
    ColumnType.TAX_AMOUNT_CURRENT: [r'cur.*tax', r'tax.*cur', r'ee.*cur', r'employee.*cur', r'current$'],
    ColumnType.TAX_AMOUNT_YTD: [r'ytd.*tax', r'tax.*ytd', r'ee.*ytd', r'employee.*ytd', r'ytd$'],
    ColumnType.TAX_ER_CURRENT: [r'er.*cur', r'employer.*cur', r'co.*cur', r'company.*cur'],
    ColumnType.TAX_ER_YTD: [r'er.*ytd', r'employer.*ytd', r'co.*ytd', r'company.*ytd'],
    
    # Deduction columns
    ColumnType.DEDUCTION_CODE: [r'ded.*code', r'^code$'],
    ColumnType.DEDUCTION_DESCRIPTION: [r'ded.*desc', r'description'],
    ColumnType.DEDUCTION_EE_CURRENT: [r'ee.*cur', r'employee.*cur', r'current$', r'^amount$'],
    ColumnType.DEDUCTION_EE_YTD: [r'ee.*ytd', r'employee.*ytd', r'ytd$'],
    ColumnType.DEDUCTION_ER_CURRENT: [r'er.*cur', r'employer.*cur', r'co.*cur'],
    ColumnType.DEDUCTION_ER_YTD: [r'er.*ytd', r'employer.*ytd', r'co.*ytd'],
    
    # Pay Info columns
    ColumnType.GROSS_PAY: [r'gross', r'total.*earn'],
    ColumnType.NET_PAY: [r'net', r'take.*home'],
    ColumnType.CHECK_NUMBER: [r'check.*#', r'check.*num', r'chk'],
    ColumnType.DIRECT_DEPOSIT: [r'direct.*dep', r'dd\b', r'ach'],
}


# =============================================================================
# VACUUM EXTRACTOR CLASS
# =============================================================================

class VacuumExtractor:
    """
    Main extraction engine for pay register documents.
    Handles PDF, Excel, and CSV files with intelligent section/column detection.
    """
    
    def __init__(self):
        self.supabase: Optional[Client] = None
        self._init_supabase()
        
    def _init_supabase(self):
        """Initialize Supabase connection"""
        if not SUPABASE_AVAILABLE:
            logger.warning("Supabase not available")
            return
            
        url = os.environ.get('SUPABASE_URL')
        key = os.environ.get('SUPABASE_SERVICE_KEY') or os.environ.get('SUPABASE_KEY')
        
        if url and key:
            try:
                self.supabase = create_client(url, key)
                logger.info("Supabase connected for vacuum extractor")
            except Exception as e:
                logger.error(f"Failed to connect to Supabase: {e}")
    
    # =========================================================================
    # MAIN EXTRACTION METHODS
    # =========================================================================
    
    def vacuum_file(self, file_path: str, project: Optional[str] = None) -> Dict[str, Any]:
        """
        Main entry point - extract all tables from a file with intelligent detection.
        
        Returns:
            Dict with tables_found, total_rows, extracts, errors, etc.
        """
        result = {
            'success': True,
            'tables_found': 0,
            'total_rows': 0,
            'extracts': [],
            'errors': [],
            'detected_report_type': None,
            'vendor_match': None
        }
        
        filename = os.path.basename(file_path)
        file_ext = filename.split('.')[-1].lower()
        
        try:
            # Extract based on file type
            if file_ext == 'pdf':
                tables = self._extract_pdf(file_path)
            elif file_ext in ['xlsx', 'xls']:
                tables = self._extract_excel(file_path)
            elif file_ext == 'csv':
                tables = self._extract_csv(file_path)
            else:
                result['errors'].append(f"Unsupported file type: {file_ext}")
                result['success'] = False
                return result
            
            # Process each table
            for i, table in enumerate(tables):
                headers = table.get('headers', [])
                data = table.get('data', [])
                
                if not data:
                    continue
                
                # Detect section type
                section_result = self.detect_section(headers, data)
                
                # Classify columns
                column_results = self.classify_columns(headers, data, section_result.section_type)
                
                # Store extract
                extract_id = self._store_extract(
                    source_file=filename,
                    project=project,
                    table_index=i,
                    headers=headers,
                    data=data,
                    section_result=section_result,
                    column_results=column_results,
                    page_number=table.get('page_number')
                )
                
                result['extracts'].append({
                    'id': extract_id,
                    'table_index': i,
                    'row_count': len(data),
                    'column_count': len(headers),
                    'detected_section': section_result.section_type.value,
                    'section_confidence': section_result.confidence,
                    'column_classifications': [
                        {
                            'index': c.column_index,
                            'header': c.header,
                            'type': c.detected_type.value,
                            'confidence': c.confidence
                        }
                        for c in column_results
                    ]
                })
                
                result['tables_found'] += 1
                result['total_rows'] += len(data)
                
        except Exception as e:
            logger.error(f"Error extracting {filename}: {e}", exc_info=True)
            result['errors'].append(str(e))
            result['success'] = False
        
        return result
    
    # =========================================================================
    # FILE TYPE EXTRACTORS
    # =========================================================================
    
    def _extract_pdf(self, file_path: str) -> List[Dict]:
        """Extract tables from PDF"""
        if not PDF_AVAILABLE:
            raise RuntimeError("pdfplumber not installed")
        
        tables = []
        
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                page_tables = page.extract_tables()
                
                for table in page_tables:
                    if not table or len(table) < 2:
                        continue
                    
                    # First row as headers, rest as data
                    headers = [str(h).strip() if h else f'Column_{i}' 
                              for i, h in enumerate(table[0])]
                    data = [
                        [str(cell).strip() if cell else '' for cell in row]
                        for row in table[1:]
                    ]
                    
                    tables.append({
                        'headers': headers,
                        'data': data,
                        'page_number': page_num + 1
                    })
        
        return tables
    
    def _extract_excel(self, file_path: str) -> List[Dict]:
        """Extract tables from Excel"""
        if not PANDAS_AVAILABLE:
            raise RuntimeError("pandas not installed")
        
        tables = []
        
        # Read all sheets
        xlsx = pd.ExcelFile(file_path)
        for sheet_name in xlsx.sheet_names:
            df = pd.read_excel(xlsx, sheet_name=sheet_name)
            
            if df.empty:
                continue
            
            headers = [str(col) for col in df.columns]
            data = df.fillna('').astype(str).values.tolist()
            
            tables.append({
                'headers': headers,
                'data': data,
                'sheet_name': sheet_name
            })
        
        return tables
    
    def _extract_csv(self, file_path: str) -> List[Dict]:
        """Extract table from CSV"""
        if not PANDAS_AVAILABLE:
            raise RuntimeError("pandas not installed")
        
        df = pd.read_csv(file_path)
        
        headers = [str(col) for col in df.columns]
        data = df.fillna('').astype(str).values.tolist()
        
        return [{
            'headers': headers,
            'data': data
        }]
    
    # =========================================================================
    # DETECTION METHODS
    # =========================================================================
    
    def detect_section(self, headers: List[str], data: List[List[str]], 
                       extract_id: Optional[int] = None) -> SectionDetectionResult:
        """Detect what type of section this table represents"""
        scores = {section: 0.0 for section in SectionType}
        signals = {section: [] for section in SectionType}
        
        # Combine headers and first few data rows for analysis
        header_text = ' '.join(headers).lower()
        sample_data = ' '.join(
            ' '.join(row) for row in data[:5]
        ).upper()
        
        for section, patterns in SECTION_PATTERNS.items():
            # Check header patterns
            for pattern in patterns['headers']:
                if re.search(pattern, header_text, re.I):
                    scores[section] += 0.3 * patterns['weight']
                    signals[section].append(f"header:{pattern}")
            
            # Check for known codes in data
            for code in patterns['codes']:
                if code in sample_data:
                    scores[section] += 0.2 * patterns['weight']
                    signals[section].append(f"code:{code}")
        
        # Find best match
        best_section = max(scores, key=scores.get)
        best_score = scores[best_section]
        
        # Require minimum confidence
        if best_score < 0.2:
            best_section = SectionType.UNKNOWN
            best_score = 0.0
        
        return SectionDetectionResult(
            section_type=best_section,
            confidence=min(best_score, 1.0),
            signals_matched=signals[best_section]
        )
    
    def classify_columns(self, headers: List[str], data: List[List[str]], 
                        section_type: SectionType) -> List[ColumnClassificationResult]:
        """Classify each column based on header and data patterns"""
        results = []
        
        for i, header in enumerate(headers):
            header_lower = header.lower()
            
            # Get sample values for this column
            sample_values = [row[i] for row in data[:10] if i < len(row)]
            
            best_type = ColumnType.UNKNOWN
            best_score = 0.0
            best_signals = []
            
            # Check against patterns
            for col_type, patterns in COLUMN_PATTERNS.items():
                score = 0.0
                signals = []
                
                for pattern in patterns:
                    if re.search(pattern, header_lower, re.I):
                        score += 0.5
                        signals.append(f"header:{pattern}")
                
                # Check data patterns
                score += self._score_column_data(sample_values, col_type) * 0.5
                
                if score > best_score:
                    best_score = score
                    best_type = col_type
                    best_signals = signals
            
            results.append(ColumnClassificationResult(
                column_index=i,
                header=header,
                detected_type=best_type,
                confidence=min(best_score, 1.0),
                signals_matched=best_signals
            ))
        
        return results
    
    def _score_column_data(self, values: List[str], col_type: ColumnType) -> float:
        """Score how well values match expected column type"""
        if not values:
            return 0.0
        
        # Define value patterns for different types
        value_patterns = {
            ColumnType.SSN: r'^\d{3}-?\d{2}-?\d{4}$',
            ColumnType.EMPLOYEE_ID: r'^\d{4,10}$',
            ColumnType.HIRE_DATE: r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$',
            ColumnType.HOURS_CURRENT: r'^\d{1,3}\.\d{1,2}$',
            ColumnType.RATE: r'^\d{1,4}\.\d{2,4}$',
            ColumnType.AMOUNT_CURRENT: r'^\$?[\d,]+\.\d{2}$',
            ColumnType.AMOUNT_YTD: r'^\$?[\d,]+\.\d{2}$',
        }
        
        if col_type in value_patterns:
            pattern = value_patterns[col_type]
            matches = sum(1 for v in values if re.match(pattern, v.strip()))
            return matches / len(values)
        
        return 0.0
    
    # =========================================================================
    # STORAGE METHODS
    # =========================================================================
    
    def _store_extract(self, source_file: str, project: Optional[str], 
                       table_index: int, headers: List[str], data: List[List[str]],
                       section_result: SectionDetectionResult,
                       column_results: List[ColumnClassificationResult],
                       page_number: Optional[int] = None) -> Optional[int]:
        """Store extract in database"""
        if not self.supabase:
            logger.warning("No database connection, extract not stored")
            return None
        
        try:
            record = {
                'source_file': source_file,
                'project': project,
                'table_index': table_index,
                'page_number': page_number,
                'raw_headers': headers,
                'raw_data': data,
                'row_count': len(data),
                'column_count': len(headers),
                'detected_section': section_result.section_type.value,
                'section_confidence': section_result.confidence,
                'section_signals': section_result.signals_matched,
                'column_classifications': [
                    {
                        'index': c.column_index,
                        'header': c.header,
                        'type': c.detected_type.value,
                        'confidence': c.confidence,
                        'signals': c.signals_matched
                    }
                    for c in column_results
                ],
                'created_at': datetime.utcnow().isoformat()
            }
            
            result = self.supabase.table('vacuum_extracts').insert(record).execute()
            
            if result.data:
                return result.data[0].get('id')
            return None
            
        except Exception as e:
            logger.error(f"Error storing extract: {e}")
            return None
    
    # =========================================================================
    # QUERY METHODS
    # =========================================================================
    
    def get_files_summary(self, project: Optional[str] = None) -> List[Dict]:
        """Get summary of all vacuumed files"""
        if not self.supabase:
            return []
        
        try:
            query = self.supabase.table('vacuum_extracts').select(
                'source_file, project, row_count, created_at'
            )
            
            if project:
                query = query.eq('project', project)
            
            result = query.execute()
            
            # Group by file
            files = {}
            for row in result.data or []:
                fname = row['source_file']
                if fname not in files:
                    files[fname] = {
                        'source_file': fname,
                        'project': row.get('project'),
                        'table_count': 0,
                        'total_rows': 0,
                        'created_at': row.get('created_at')
                    }
                files[fname]['table_count'] += 1
                files[fname]['total_rows'] += row.get('row_count', 0)
            
            return list(files.values())
            
        except Exception as e:
            logger.error(f"Error getting files summary: {e}")
            return []
    
    def get_extracts(self, project: Optional[str] = None, 
                     source_file: Optional[str] = None) -> List[Dict]:
        """Get extracts with optional filters"""
        if not self.supabase:
            return []
        
        try:
            query = self.supabase.table('vacuum_extracts').select('*')
            
            if project:
                query = query.eq('project', project)
            if source_file:
                query = query.eq('source_file', source_file)
            
            result = query.order('created_at', desc=True).execute()
            return result.data or []
            
        except Exception as e:
            logger.error(f"Error getting extracts: {e}")
            return []
    
    def get_extract_by_id(self, extract_id: int) -> Optional[Dict]:
        """Get a single extract by ID"""
        if not self.supabase:
            return None
        
        try:
            result = self.supabase.table('vacuum_extracts').select('*').eq(
                'id', extract_id
            ).single().execute()
            return result.data
            
        except Exception as e:
            logger.error(f"Error getting extract {extract_id}: {e}")
            return None
    
    # =========================================================================
    # CONFIRMATION & LEARNING METHODS
    # =========================================================================
    
    def confirm_section(self, extract_id: int, section_type: str, 
                       user_corrected: bool = False) -> bool:
        """Confirm or correct section detection"""
        if not self.supabase:
            return False
        
        try:
            update = {
                'detected_section': section_type,
                'section_confirmed': True,
                'section_user_corrected': user_corrected
            }
            
            self.supabase.table('vacuum_extracts').update(update).eq(
                'id', extract_id
            ).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Error confirming section: {e}")
            return False
    
    def confirm_column(self, extract_id: int, column_index: int, 
                       column_type: str, user_corrected: bool = False) -> bool:
        """Confirm or correct column classification"""
        if not self.supabase:
            return False
        
        try:
            # Get current classifications
            extract = self.get_extract_by_id(extract_id)
            if not extract:
                return False
            
            classifications = extract.get('column_classifications', [])
            
            # Update the specific column
            for c in classifications:
                if c.get('index') == column_index:
                    c['type'] = column_type
                    c['confirmed'] = True
                    c['user_corrected'] = user_corrected
                    break
            
            # Save back
            self.supabase.table('vacuum_extracts').update({
                'column_classifications': classifications
            }).eq('id', extract_id).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Error confirming column: {e}")
            return False
    
    def _update_extract_detection(self, extract_id: int, 
                                   section_result: SectionDetectionResult,
                                   column_results: List[ColumnClassificationResult]) -> bool:
        """Update extract with new detection results"""
        if not self.supabase:
            return False
        
        try:
            update = {
                'detected_section': section_result.section_type.value,
                'section_confidence': section_result.confidence,
                'section_signals': section_result.signals_matched,
                'column_classifications': [
                    {
                        'index': c.column_index,
                        'header': c.header,
                        'type': c.detected_type.value,
                        'confidence': c.confidence,
                        'signals': c.signals_matched
                    }
                    for c in column_results
                ]
            }
            
            self.supabase.table('vacuum_extracts').update(update).eq(
                'id', extract_id
            ).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating detection: {e}")
            return False
    
    def learn_vendor_signature(self, extracts: List[Dict], vendor_name: str,
                               report_type: str) -> bool:
        """Learn vendor signature from confirmed extracts"""
        # Placeholder - full implementation would store patterns
        logger.info(f"Learning vendor signature: {vendor_name} ({report_type})")
        return True
    
    def learn_column_mapping(self, source_header: str, target_column_type: str,
                            section_type: str, source_file: str) -> bool:
        """Learn column mapping for future files"""
        # Placeholder - full implementation would store mappings
        logger.info(f"Learning mapping: {source_header} -> {target_column_type}")
        return True
    
    def get_pattern_stats(self) -> Dict[str, Any]:
        """Get statistics on learned patterns"""
        return {
            'vendor_signatures': 0,
            'column_mappings': 0,
            'section_patterns': len(SECTION_PATTERNS)
        }
    
    def export_learning_data(self) -> Dict[str, Any]:
        """Export all learned patterns"""
        return {
            'vendor_signatures': [],
            'column_mappings': [],
            'exported_at': datetime.utcnow().isoformat()
        }
    
    # =========================================================================
    # DELETE METHODS
    # =========================================================================
    
    def delete_file_extracts(self, source_file: str, project: Optional[str] = None) -> int:
        """Delete all extracts for a file"""
        if not self.supabase:
            return 0
        
        try:
            query = self.supabase.table('vacuum_extracts').delete().eq(
                'source_file', source_file
            )
            
            if project:
                query = query.eq('project', project)
            
            result = query.execute()
            return len(result.data) if result.data else 0
            
        except Exception as e:
            logger.error(f"Error deleting extracts: {e}")
            return 0
    
    def delete_all_extracts(self) -> int:
        """Delete all extracts"""
        if not self.supabase:
            return 0
        
        try:
            # Get count first
            count_result = self.supabase.table('vacuum_extracts').select(
                'id', count='exact'
            ).execute()
            count = count_result.count or 0
            
            # Delete all
            self.supabase.table('vacuum_extracts').delete().neq('id', 0).execute()
            
            return count
            
        except Exception as e:
            logger.error(f"Error deleting all extracts: {e}")
            return 0
    
    # =========================================================================
    # MAPPING METHODS
    # =========================================================================
    
    def apply_section_mapping(self, extract_id: int, section_type: str,
                              column_map: Dict[str, str],
                              header_metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Apply column mapping to create structured output"""
        extract = self.get_extract_by_id(extract_id)
        if not extract:
            return {'success': False, 'error': 'Extract not found'}
        
        # Mark as mapped
        if self.supabase:
            self.supabase.table('vacuum_extracts').update({
                'mapping_applied': True,
                'mapped_section': section_type,
                'column_mapping': column_map,
                'header_metadata': header_metadata
            }).eq('id', extract_id).execute()
        
        return {'success': True, 'extract_id': extract_id}
    
    def extract_header_metadata(self, source_file: str) -> Dict[str, str]:
        """Extract header metadata (company, pay period, etc.) from file"""
        # Placeholder - would analyze first page of PDF for metadata
        return {
            'company': '',
            'pay_period_start': '',
            'pay_period_end': '',
            'check_date': ''
        }


# =============================================================================
# SINGLETON & FACTORY
# =============================================================================

_extractor_instance: Optional[VacuumExtractor] = None

def get_vacuum_extractor() -> VacuumExtractor:
    """Get or create the vacuum extractor singleton"""
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = VacuumExtractor()
    return _extractor_instance


# =============================================================================
# APPLY PATCH FOR COLUMN SPLITTING
# =============================================================================

# Try multiple import paths for the patch
for import_path in ['backend.utils.vacuum_extractor_patch', 'utils.vacuum_extractor_patch']:
    try:
        patch_module = __import__(import_path, fromlist=['patch_vacuum_extractor'])
        patch_module.patch_vacuum_extractor(VacuumExtractor)
        logger.info(f"Vacuum extractor patched from {import_path}")
        break
    except ImportError:
        continue
else:
    logger.warning("vacuum_extractor_patch not found, column splitting may not work")
