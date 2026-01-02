"""
XLR8 DETECTION SERVICE
======================

Detects system of record, domain, and functional areas from uploaded files.
Uses detection_signatures from Supabase to match against:
- File names
- Column names  
- Column values
- Sheet names

A project can have MULTIPLE systems, domains, and functional areas.
Example: UKG Pro (HCM) + UKG Dimensions (Time) + SAP S/4HANA (Finance)

Results are stored in project context and used for:
- Scoping semantic type matching
- Selecting applicable standards/rules
- Providing domain-specific consultative insight

Author: XLR8 Team
Version: 1.0.0
Deploy to: backend/utils/detection_service.py
"""

import re
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class DetectionMatch:
    """A single detection match from a signature."""
    signature_id: str
    pattern: str
    pattern_type: str
    matched_against: str
    confidence: float
    
    system_code: Optional[str] = None
    system_name: Optional[str] = None
    domain_code: Optional[str] = None
    domain_name: Optional[str] = None
    functional_area_code: Optional[str] = None
    functional_area_name: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            'signature_id': self.signature_id,
            'pattern': self.pattern,
            'pattern_type': self.pattern_type,
            'matched_against': self.matched_against,
            'confidence': self.confidence,
            'system_code': self.system_code,
            'domain_code': self.domain_code,
            'functional_area_code': self.functional_area_code
        }


@dataclass
class DetectionResult:
    """
    Complete detection result for a file or project.
    
    A project can have multiple systems, domains, and functional areas.
    Results are sorted by confidence (highest first).
    """
    # All detected systems
    systems: List[Dict] = field(default_factory=list)
    
    # All detected domains
    domains: List[Dict] = field(default_factory=list)
    
    # All detected functional areas
    functional_areas: List[Dict] = field(default_factory=list)
    
    # All matches for debugging/transparency
    all_matches: List[DetectionMatch] = field(default_factory=list)
    
    # Metadata
    file_name: Optional[str] = None
    columns_analyzed: int = 0
    detection_time_ms: int = 0
    
    @property
    def primary_system(self) -> Optional[Dict]:
        """Get highest-confidence system."""
        return self.systems[0] if self.systems else None
    
    @property
    def primary_domain(self) -> Optional[Dict]:
        """Get highest-confidence domain."""
        return self.domains[0] if self.domains else None
    
    def to_dict(self) -> Dict:
        return {
            'systems': self.systems,
            'domains': self.domains,
            'functional_areas': self.functional_areas,
            'primary_system': self.primary_system,
            'primary_domain': self.primary_domain,
            'match_count': len(self.all_matches),
            'columns_analyzed': self.columns_analyzed,
            'detection_time_ms': self.detection_time_ms
        }


@dataclass
class DetectionSignature:
    """A detection signature loaded from database."""
    id: str
    pattern: str
    pattern_type: str
    confidence: float
    priority: int
    
    system_code: Optional[str] = None
    system_name: Optional[str] = None
    domain_code: Optional[str] = None
    domain_name: Optional[str] = None
    functional_area_code: Optional[str] = None
    functional_area_name: Optional[str] = None
    
    description: Optional[str] = None
    example: Optional[str] = None
    
    _compiled_pattern: Any = None
    
    def compile(self) -> None:
        """Pre-compile regex pattern for performance."""
        if self._compiled_pattern is None:
            try:
                self._compiled_pattern = re.compile(self.pattern, re.IGNORECASE)
            except re.error:
                self._compiled_pattern = False  # Mark as invalid regex
    
    def matches(self, text: str) -> bool:
        """Check if pattern matches text."""
        if not text:
            return False
        
        # Try compiled regex
        if self._compiled_pattern:
            try:
                if self._compiled_pattern.search(text):
                    return True
            except:
                pass
        elif self._compiled_pattern is None:
            # Not yet compiled, try now
            try:
                if re.search(self.pattern, text, re.IGNORECASE):
                    return True
            except re.error:
                pass
        
        # Fall back to case-insensitive substring match
        if self.pattern.lower() in text.lower():
            return True
        
        return False


# =============================================================================
# FALLBACK SEED DATA
# =============================================================================
# Used when Supabase is unavailable

FALLBACK_DOMAINS = [
    {'code': 'hcm', 'name': 'Human Capital Management'},
    {'code': 'finance', 'name': 'Finance & ERP'},
    {'code': 'compliance', 'name': 'Governance, Risk & Compliance'},
]

FALLBACK_SYSTEMS = [
    {'code': 'ukg_pro', 'name': 'UKG Pro', 'vendor': 'UKG', 'domain_code': 'hcm'},
    {'code': 'workday_hcm', 'name': 'Workday HCM', 'vendor': 'Workday', 'domain_code': 'hcm'},
    {'code': 'adp_wfn', 'name': 'ADP Workforce Now', 'vendor': 'ADP', 'domain_code': 'hcm'},
    {'code': 'sap_s4hana', 'name': 'SAP S/4HANA', 'vendor': 'SAP', 'domain_code': 'finance'},
    {'code': 'netsuite', 'name': 'NetSuite', 'vendor': 'Oracle', 'domain_code': 'finance'},
]

FALLBACK_SIGNATURES = [
    # UKG Pro
    {'pattern': '(?i)ultipro|ukg.*pro', 'pattern_type': 'file_name', 'system_code': 'ukg_pro', 'confidence': 0.95},
    {'pattern': '(?i)configuration.?validation', 'pattern_type': 'file_name', 'system_code': 'ukg_pro', 'confidence': 0.90},
    {'pattern': '(?i)^home_company_code$', 'pattern_type': 'column_name', 'system_code': 'ukg_pro', 'confidence': 0.90},
    {'pattern': '(?i)^coid$|^eeid$', 'pattern_type': 'column_name', 'system_code': 'ukg_pro', 'confidence': 0.85},
    
    # Workday
    {'pattern': '(?i)workday|^wd_', 'pattern_type': 'file_name', 'system_code': 'workday_hcm', 'confidence': 0.95},
    {'pattern': '(?i)^worker_id$', 'pattern_type': 'column_name', 'system_code': 'workday_hcm', 'confidence': 0.85},
    
    # HCM Domain
    {'pattern': '(?i)employee_id|emp_id|emplid|pernr', 'pattern_type': 'column_name', 'domain_code': 'hcm', 'confidence': 0.90},
    {'pattern': '(?i)hire_date|term_date|termination_date', 'pattern_type': 'column_name', 'domain_code': 'hcm', 'confidence': 0.90},
    {'pattern': '(?i)fica|federal_tax|state_tax', 'pattern_type': 'column_name', 'domain_code': 'hcm', 'confidence': 0.95},
    {'pattern': '(?i)gross_pay|net_pay', 'pattern_type': 'column_name', 'domain_code': 'hcm', 'confidence': 0.90},
    
    # Finance Domain
    {'pattern': '(?i)^debit$|^credit$|gl_account', 'pattern_type': 'column_name', 'domain_code': 'finance', 'confidence': 0.90},
    {'pattern': '(?i)vendor_id|invoice_number', 'pattern_type': 'column_name', 'domain_code': 'finance', 'confidence': 0.85},
]


# =============================================================================
# DETECTION SERVICE
# =============================================================================

class DetectionService:
    """
    Detects system, domain, and functional areas from file/column patterns.
    
    Usage:
        service = DetectionService()
        
        # Detect from file + columns
        result = service.detect(
            filename="UKG_Pro_Employees.xlsx",
            columns=["employee_id", "hire_date", "fica_wages", "401k_pct"]
        )
        
        # Update project context
        service.update_project_context(project_id, result)
        
        # Get available systems for UI
        systems = service.get_all_systems()
    """
    
    def __init__(self):
        # Signature cache
        self._signatures: List[DetectionSignature] = []
        self._signatures_loaded_at: Optional[datetime] = None
        self._cache_ttl_seconds: int = 300  # 5 minutes
        
        # Reference data cache
        self._systems: Dict[str, Dict] = {}
        self._domains: Dict[str, Dict] = {}
        self._functional_areas: Dict[str, Dict] = {}
        self._reference_loaded: bool = False
    
    def _get_supabase(self):
        """Get Supabase client."""
        try:
            from utils.database.supabase_client import get_supabase
            return get_supabase()
        except ImportError:
            try:
                from backend.utils.database.supabase_client import get_supabase
                return get_supabase()
            except ImportError:
                logger.warning("[DETECTION] Supabase not available")
                return None
    
    def _is_cache_valid(self) -> bool:
        """Check if signature cache is still valid."""
        if not self._signatures or not self._signatures_loaded_at:
            return False
        age = datetime.now() - self._signatures_loaded_at
        return age.total_seconds() < self._cache_ttl_seconds
    
    def _load_signatures(self) -> bool:
        """Load detection signatures from Supabase or fallback."""
        if self._is_cache_valid():
            return True
        
        supabase = self._get_supabase()
        
        if supabase:
            try:
                result = supabase.table('v_detection_signatures').select('*').execute()
                
                self._signatures = []
                for row in (result.data or []):
                    sig = DetectionSignature(
                        id=row.get('id', ''),
                        pattern=row.get('pattern', ''),
                        pattern_type=row.get('pattern_type', 'file_name'),
                        confidence=float(row.get('confidence', 0.8)),
                        priority=int(row.get('priority', 0)),
                        system_code=row.get('system_code'),
                        system_name=row.get('system_name'),
                        domain_code=row.get('domain_code'),
                        domain_name=row.get('domain_name'),
                        functional_area_code=row.get('functional_area_code'),
                        functional_area_name=row.get('functional_area_name'),
                        description=row.get('description'),
                        example=row.get('example')
                    )
                    sig.compile()
                    self._signatures.append(sig)
                
                self._signatures.sort(key=lambda s: (s.priority, s.confidence), reverse=True)
                self._signatures_loaded_at = datetime.now()
                logger.info(f"[DETECTION] Loaded {len(self._signatures)} signatures from Supabase")
                return True
                
            except Exception as e:
                logger.warning(f"[DETECTION] Supabase load failed: {e}, using fallback")
        
        # Use fallback signatures
        self._signatures = []
        for i, sig_data in enumerate(FALLBACK_SIGNATURES):
            sig = DetectionSignature(
                id=f"fallback_{i}",
                pattern=sig_data['pattern'],
                pattern_type=sig_data['pattern_type'],
                confidence=sig_data.get('confidence', 0.8),
                priority=sig_data.get('priority', 0),
                system_code=sig_data.get('system_code'),
                domain_code=sig_data.get('domain_code'),
                functional_area_code=sig_data.get('functional_area_code')
            )
            sig.compile()
            self._signatures.append(sig)
        
        self._signatures_loaded_at = datetime.now()
        logger.info(f"[DETECTION] Loaded {len(self._signatures)} fallback signatures")
        return True
    
    def _load_reference_data(self) -> bool:
        """Load systems, domains, functional areas for lookups."""
        if self._reference_loaded:
            return True
        
        supabase = self._get_supabase()
        
        if supabase:
            try:
                # Load systems
                result = supabase.table('v_systems').select('*').execute()
                for row in (result.data or []):
                    self._systems[row['code']] = row
                
                # Load domains
                result = supabase.table('domains').select('*').eq('is_active', True).execute()
                for row in (result.data or []):
                    self._domains[row['code']] = row
                
                # Load functional areas
                result = supabase.table('v_functional_areas').select('*').execute()
                for row in (result.data or []):
                    key = f"{row.get('domain_code', '')}.{row['code']}"
                    self._functional_areas[key] = row
                    # Also index by code alone for simple lookups
                    self._functional_areas[row['code']] = row
                
                self._reference_loaded = True
                logger.info(f"[DETECTION] Loaded {len(self._systems)} systems, "
                           f"{len(self._domains)} domains, {len(self._functional_areas)} functional areas")
                return True
                
            except Exception as e:
                logger.warning(f"[DETECTION] Reference data load failed: {e}, using fallback")
        
        # Use fallback data
        for d in FALLBACK_DOMAINS:
            self._domains[d['code']] = d
        for s in FALLBACK_SYSTEMS:
            self._systems[s['code']] = s
        
        self._reference_loaded = True
        logger.info(f"[DETECTION] Loaded fallback reference data")
        return True
    
    # =========================================================================
    # DETECTION METHODS
    # =========================================================================
    
    def detect(
        self,
        filename: str = None,
        columns: List[str] = None,
        values: Dict[str, List[str]] = None,
        sheet_names: List[str] = None
    ) -> DetectionResult:
        """
        Detect systems, domains, and functional areas from file characteristics.
        
        Args:
            filename: Name of uploaded file
            columns: List of column names
            values: Dict of column_name -> sample values
            sheet_names: List of Excel sheet names
        
        Returns:
            DetectionResult with all detected context
        """
        start_time = datetime.now()
        
        self._load_signatures()
        self._load_reference_data()
        
        all_matches: List[DetectionMatch] = []
        
        # Match against filename
        if filename:
            all_matches.extend(self._match_against('file_name', filename))
        
        # Match against column names
        if columns:
            for col in columns:
                all_matches.extend(self._match_against('column_name', col))
        
        # Match against column values
        if values:
            for col_name, col_values in values.items():
                for val in col_values[:10]:  # Limit to first 10 values
                    all_matches.extend(self._match_against('column_value', str(val)))
        
        # Match against sheet names
        if sheet_names:
            for sheet in sheet_names:
                all_matches.extend(self._match_against('sheet_name', sheet))
        
        # Aggregate matches
        result = self._aggregate_matches(all_matches)
        result.file_name = filename
        result.columns_analyzed = len(columns) if columns else 0
        result.detection_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        return result
    
    def detect_from_filename(self, filename: str) -> DetectionResult:
        """Quick detection from filename only."""
        return self.detect(filename=filename)
    
    def detect_from_columns(self, columns: List[str]) -> DetectionResult:
        """Detection from column names only."""
        return self.detect(columns=columns)
    
    def _match_against(self, pattern_type: str, text: str) -> List[DetectionMatch]:
        """Match signatures of a specific type against text."""
        matches = []
        
        for sig in self._signatures:
            if sig.pattern_type != pattern_type:
                continue
            
            if sig.matches(text):
                matches.append(DetectionMatch(
                    signature_id=sig.id,
                    pattern=sig.pattern,
                    pattern_type=pattern_type,
                    matched_against=text,
                    confidence=sig.confidence,
                    system_code=sig.system_code,
                    system_name=sig.system_name,
                    domain_code=sig.domain_code,
                    domain_name=sig.domain_name,
                    functional_area_code=sig.functional_area_code,
                    functional_area_name=sig.functional_area_name
                ))
        
        return matches
    
    def _aggregate_matches(self, matches: List[DetectionMatch]) -> DetectionResult:
        """Aggregate all matches to determine detected context."""
        result = DetectionResult(all_matches=matches)
        
        if not matches:
            return result
        
        # Aggregate scores
        system_scores: Dict[str, float] = defaultdict(float)
        system_names: Dict[str, str] = {}
        
        domain_scores: Dict[str, float] = defaultdict(float)
        domain_names: Dict[str, str] = {}
        
        func_area_scores: Dict[str, float] = defaultdict(float)
        func_area_info: Dict[str, Dict] = {}
        
        for match in matches:
            if match.system_code:
                system_scores[match.system_code] += match.confidence
                if match.system_name:
                    system_names[match.system_code] = match.system_name
            
            if match.domain_code:
                domain_scores[match.domain_code] += match.confidence
                if match.domain_name:
                    domain_names[match.domain_code] = match.domain_name
            
            if match.functional_area_code:
                func_area_scores[match.functional_area_code] += match.confidence
                func_area_info[match.functional_area_code] = {
                    'name': match.functional_area_name,
                    'domain_code': match.domain_code
                }
        
        # Collect systems above threshold
        THRESHOLD = 0.5
        for sys_code, score in sorted(system_scores.items(), key=lambda x: x[1], reverse=True):
            if score >= THRESHOLD:
                result.systems.append({
                    'code': sys_code,
                    'name': system_names.get(sys_code) or self._systems.get(sys_code, {}).get('name'),
                    'confidence': min(score, 1.0)
                })
                
                # Infer domain from system
                sys_info = self._systems.get(sys_code, {})
                if sys_info.get('domain_code') and sys_info['domain_code'] not in domain_scores:
                    domain_scores[sys_info['domain_code']] = score * 0.8
                    domain_names[sys_info['domain_code']] = sys_info.get('domain_name')
        
        # Collect domains above threshold
        for dom_code, score in sorted(domain_scores.items(), key=lambda x: x[1], reverse=True):
            if score >= THRESHOLD:
                result.domains.append({
                    'code': dom_code,
                    'name': domain_names.get(dom_code) or self._domains.get(dom_code, {}).get('name'),
                    'confidence': min(score, 1.0)
                })
        
        # Collect functional areas above threshold
        for fa_code, score in sorted(func_area_scores.items(), key=lambda x: x[1], reverse=True):
            if score >= THRESHOLD:
                info = func_area_info.get(fa_code, {})
                result.functional_areas.append({
                    'code': fa_code,
                    'name': info.get('name'),
                    'domain_code': info.get('domain_code'),
                    'confidence': min(score, 1.0)
                })
        
        return result
    
    # =========================================================================
    # PROJECT CONTEXT METHODS
    # =========================================================================
    
    def update_project_context(self, project_id: str, detection: DetectionResult) -> bool:
        """
        Update project with detected context.
        
        Stores in projects.detected_context and updates systems/domains/functional_areas arrays.
        """
        supabase = self._get_supabase()
        if not supabase:
            logger.warning("[DETECTION] Cannot update project - no database")
            return False
        
        try:
            detected_context = {
                'systems': detection.systems,
                'domains': detection.domains,
                'functional_areas': detection.functional_areas,
                'last_detected': datetime.now().isoformat(),
                'detection_source': 'auto',
                'match_count': len(detection.all_matches)
            }
            
            system_codes = [s['code'] for s in detection.systems]
            domain_codes = [d['code'] for d in detection.domains]
            func_areas = [
                {'domain': fa.get('domain_code'), 'area': fa['code']}
                for fa in detection.functional_areas
            ]
            
            update_data = {
                'detected_context': detected_context,
                'systems': system_codes,
                'domains': domain_codes,
                'functional_areas': func_areas
            }
            
            supabase.table('projects').update(update_data).eq('name', project_id).execute()
            
            # Update junction tables
            self._update_junction_tables(project_id, detection, supabase)
            
            logger.info(f"[DETECTION] Updated {project_id}: systems={system_codes}, domains={domain_codes}")
            return True
            
        except Exception as e:
            logger.error(f"[DETECTION] Update failed: {e}")
            return False
    
    def _update_junction_tables(self, project_id: str, detection: DetectionResult, supabase) -> None:
        """Update junction tables for relational queries."""
        try:
            # Get project UUID
            project_result = supabase.table('projects').select('id').eq('name', project_id).execute()
            if not project_result.data:
                return
            
            project_uuid = project_result.data[0]['id']
            
            # Update project_systems
            for i, sys in enumerate(detection.systems):
                sys_result = supabase.table('systems').select('id').eq('code', sys['code']).execute()
                if sys_result.data:
                    try:
                        supabase.table('project_systems').upsert({
                            'project_id': project_uuid,
                            'system_id': sys_result.data[0]['id'],
                            'is_primary': i == 0,
                            'detected_confidence': sys.get('confidence', 0.0),
                            'confirmed': False
                        }, on_conflict='project_id,system_id').execute()
                    except Exception as e:
                        logger.debug(f"[DETECTION] Junction upsert error: {e}")
            
            # Update project_functional_areas
            for fa in detection.functional_areas:
                fa_result = supabase.table('functional_areas').select('id').eq('code', fa['code']).execute()
                if fa_result.data:
                    try:
                        supabase.table('project_functional_areas').upsert({
                            'project_id': project_uuid,
                            'functional_area_id': fa_result.data[0]['id'],
                            'detected_confidence': fa.get('confidence', 0.0),
                            'confirmed': False,
                            'in_scope': True
                        }, on_conflict='project_id,functional_area_id').execute()
                    except Exception as e:
                        logger.debug(f"[DETECTION] Junction upsert error: {e}")
                        
        except Exception as e:
            logger.warning(f"[DETECTION] Junction table update failed: {e}")
    
    def get_project_context(self, project_id: str) -> Optional[Dict]:
        """Get detected context for a project."""
        supabase = self._get_supabase()
        if not supabase:
            return None
        
        try:
            result = supabase.table('projects').select(
                'id, name, systems, domains, functional_areas, '
                'detected_context, context_confirmed, engagement_type'
            ).eq('name', project_id).execute()
            
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(f"[DETECTION] Get context failed: {e}")
            return None
    
    def confirm_project_context(
        self,
        project_id: str,
        system_codes: List[str] = None,
        domain_codes: List[str] = None,
        functional_areas: List[Dict] = None,
        engagement_type: str = None
    ) -> bool:
        """
        Confirm or override detected project context.
        
        Args:
            project_id: Project name
            system_codes: List of system codes (e.g., ["ukg_pro", "ukg_dimensions"])
            domain_codes: List of domain codes (e.g., ["hcm", "finance"])
            functional_areas: List of dicts (e.g., [{"domain": "hcm", "area": "payroll"}])
            engagement_type: Type of engagement (e.g., "implementation", "support")
        """
        supabase = self._get_supabase()
        if not supabase:
            return False
        
        try:
            self._load_reference_data()
            
            # Get current context
            current = supabase.table('projects').select('detected_context').eq('name', project_id).execute()
            detected_context = current.data[0].get('detected_context', {}) if current.data else {}
            
            update_data = {'context_confirmed': True}
            
            if system_codes is not None:
                update_data['systems'] = system_codes
                detected_context['systems'] = [
                    {
                        'code': code,
                        'name': self._systems.get(code, {}).get('name', code),
                        'confidence': 1.0,
                        'confirmed': True
                    }
                    for code in system_codes
                ]
            
            if domain_codes is not None:
                update_data['domains'] = domain_codes
                detected_context['domains'] = [
                    {
                        'code': code,
                        'name': self._domains.get(code, {}).get('name', code),
                        'confidence': 1.0,
                        'confirmed': True
                    }
                    for code in domain_codes
                ]
            
            if functional_areas is not None:
                update_data['functional_areas'] = functional_areas
                detected_context['functional_areas'] = [
                    {
                        'code': fa['area'],
                        'domain_code': fa['domain'],
                        'confidence': 1.0,
                        'confirmed': True
                    }
                    for fa in functional_areas
                ]
            
            if engagement_type:
                update_data['engagement_type'] = engagement_type
            
            detected_context['confirmed_at'] = datetime.now().isoformat()
            update_data['detected_context'] = detected_context
            
            supabase.table('projects').update(update_data).eq('name', project_id).execute()
            
            logger.info(f"[DETECTION] Confirmed context for {project_id}")
            return True
            
        except Exception as e:
            logger.error(f"[DETECTION] Confirm failed: {e}")
            return False
    
    # =========================================================================
    # REFERENCE DATA ACCESSORS
    # =========================================================================
    
    def get_all_systems(self, domain_code: str = None) -> List[Dict]:
        """Get all available systems, optionally filtered by domain."""
        self._load_reference_data()
        
        systems = list(self._systems.values())
        
        if domain_code:
            systems = [s for s in systems if s.get('domain_code') == domain_code]
        
        return sorted(systems, key=lambda s: s.get('name', ''))
    
    def get_all_domains(self) -> List[Dict]:
        """Get all available domains."""
        self._load_reference_data()
        return sorted(self._domains.values(), key=lambda d: d.get('display_order', 0))
    
    def get_functional_areas(self, domain_code: str = None) -> List[Dict]:
        """Get functional areas, optionally filtered by domain."""
        self._load_reference_data()
        
        # Only get entries that have domain_code (skip the code-only indexed ones)
        areas = [fa for fa in self._functional_areas.values() if fa.get('domain_code')]
        
        if domain_code:
            areas = [fa for fa in areas if fa.get('domain_code') == domain_code]
        
        return sorted(areas, key=lambda fa: fa.get('display_order', 0))
    
    def get_system_by_code(self, code: str) -> Optional[Dict]:
        """Get system info by code."""
        self._load_reference_data()
        return self._systems.get(code)
    
    def get_domain_by_code(self, code: str) -> Optional[Dict]:
        """Get domain info by code."""
        self._load_reference_data()
        return self._domains.get(code)
    
    def get_engagement_types(self) -> List[Dict]:
        """Get available engagement types."""
        return [
            {'code': 'implementation', 'name': 'New Implementation', 'description': 'Net-new system implementation'},
            {'code': 'conversion', 'name': 'Data Conversion', 'description': 'Converting from another system'},
            {'code': 'module_add', 'name': 'Module Addition', 'description': 'Adding modules to existing system'},
            {'code': 'upgrade', 'name': 'System Upgrade', 'description': 'Upgrading existing system version'},
            {'code': 'support', 'name': 'Ongoing Support', 'description': 'Production support and maintenance'},
            {'code': 'compliance', 'name': 'Compliance Review', 'description': 'Regulatory compliance assessment'},
            {'code': 'optimization', 'name': 'System Optimization', 'description': 'Performance and configuration optimization'},
            {'code': 'audit', 'name': 'System Audit', 'description': 'Configuration or data audit'},
            {'code': 'integration', 'name': 'Integration Project', 'description': 'Third-party integration'},
            {'code': 'other', 'name': 'Other', 'description': 'Other engagement type'}
        ]


# =============================================================================
# MODULE-LEVEL CONVENIENCE
# =============================================================================

_service_instance: Optional[DetectionService] = None


def get_detection_service() -> DetectionService:
    """Get or create the global DetectionService instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = DetectionService()
    return _service_instance


def detect_context(
    filename: str = None,
    columns: List[str] = None,
    values: Dict[str, List[str]] = None
) -> DetectionResult:
    """Convenience function for detection."""
    return get_detection_service().detect(filename=filename, columns=columns, values=values)


def update_project_context(project_id: str, detection: DetectionResult) -> bool:
    """Convenience function to update project context."""
    return get_detection_service().update_project_context(project_id, detection)


def get_project_context(project_id: str) -> Optional[Dict]:
    """Convenience function to get project context."""
    return get_detection_service().get_project_context(project_id)
