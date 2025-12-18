"""
DOMAIN INFERENCE ENGINE
========================

Analyzes project data to intelligently infer what domains/categories
of data are present. NO HARDCODING - learns from actual data patterns.

This is the foundation for auto-selecting expert context.

Flow:
1. Query _column_profiles and _schema_metadata for the project
2. Analyze patterns in column names, table names, filter_categories, values
3. Score each potential domain based on evidence strength
4. Store detected domains in project metadata
5. Return ranked domains with confidence scores

Author: XLR8 Team
Version: 1.0.0
"""

import logging
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


# =============================================================================
# DOMAIN PATTERNS - Evidence patterns for domain detection
# These are STARTING patterns - the system learns and refines over time
# =============================================================================

# Each domain has patterns that indicate its presence
# Weights are starting points - learning will adjust these
DOMAIN_EVIDENCE_PATTERNS = {
    'payroll': {
        'column_patterns': [
            (r'employee.*num|emp.*num|ee.*num|emp.*id|employee.*id', 0.3),
            (r'earnings|pay|wage|salary|compensation', 0.4),
            (r'deduction|ded.*code|withholding', 0.4),
            (r'gross.*pay|net.*pay|ytd', 0.5),
            (r'check.*num|check.*date|pay.*date|pay.*period', 0.4),
            (r'hours.*worked|reg.*hours|ot.*hours|overtime', 0.3),
            (r'rate|hourly.*rate|pay.*rate', 0.3),
        ],
        'table_patterns': [
            (r'earning|pay.*register|payroll|compensation', 0.5),
            (r'deduction|withholding', 0.4),
            (r'check.*history|pay.*history', 0.4),
        ],
        'filter_categories': {
            'status': 0.2,
            'employee_type': 0.3,
            'pay_type': 0.4,
            'company': 0.2,
        },
        'value_patterns': [
            (r'^(A|T|L|P|I)$', 'status', 0.2),  # Employment status codes
            (r'^(REG|OT|HOL|VAC|SICK)$', 'pay_type', 0.3),  # Earning codes
        ],
    },
    
    'tax': {
        'column_patterns': [
            (r'tax|withhold|feder|state.*tax|local.*tax', 0.5),
            (r'fein|ein|ssn|social.*security', 0.4),
            (r'sui|suta|futa|fica', 0.5),
            (r'w2|w4|1099|940|941', 0.5),
            (r'exempt|taxable|tax.*code', 0.3),
        ],
        'table_patterns': [
            (r'tax|withhold|w2|1099', 0.5),
        ],
        'filter_categories': {
            'location': 0.3,  # Tax jurisdictions
        },
        'value_patterns': [
            (r'^\d{2}-\d{7}$', None, 0.5),  # FEIN format
            (r'^\d{3}-\d{2}-\d{4}$', None, 0.3),  # SSN format
        ],
    },
    
    'benefits': {
        'column_patterns': [
            (r'benefit|coverage|enrollment|plan', 0.4),
            (r'medical|dental|vision|health', 0.4),
            (r'hsa|fsa|401k|403b|retirement|pension', 0.5),
            (r'premium|contribution|employer.*match', 0.4),
            (r'dependent|beneficiary|coverage.*level', 0.3),
            (r'effective.*date|term.*date|open.*enrollment', 0.3),
        ],
        'table_patterns': [
            (r'benefit|enrollment|coverage|plan', 0.5),
            (r'dependent|beneficiary', 0.4),
        ],
        'filter_categories': {},
        'value_patterns': [
            (r'^(EE|EE\+SP|EE\+CH|FAM)$', None, 0.4),  # Coverage levels
        ],
    },
    
    'time': {
        'column_patterns': [
            (r'punch|clock|time.*in|time.*out|swipe', 0.5),
            (r'schedule|shift|roster', 0.4),
            (r'attendance|absent|tardy|leave', 0.4),
            (r'accrual|pto|vacation|sick.*time', 0.4),
            (r'work.*date|worked.*hours|total.*hours', 0.3),
        ],
        'table_patterns': [
            (r'time|punch|attendance|schedule|shift', 0.5),
            (r'accrual|leave|pto', 0.4),
        ],
        'filter_categories': {},
        'value_patterns': [],
    },
    
    'hr': {
        'column_patterns': [
            (r'hire.*date|term.*date|start.*date|end.*date', 0.3),
            (r'department|dept|division|cost.*center', 0.3),
            (r'position|job.*title|job.*code|occupation', 0.3),
            (r'supervisor|manager|reports.*to', 0.3),
            (r'address|city|state|zip|phone|email', 0.2),
            (r'birth.*date|dob|age|gender|ethnicity', 0.2),
        ],
        'table_patterns': [
            (r'employee|worker|person|staff', 0.3),
            (r'department|organization|org.*unit', 0.3),
            (r'position|job|role', 0.3),
        ],
        'filter_categories': {
            'status': 0.3,
            'company': 0.2,
            'organization': 0.3,
            'location': 0.2,
            'employee_type': 0.3,
            'job': 0.3,
        },
        'value_patterns': [],
    },
    
    'gl': {
        'column_patterns': [
            (r'account|acct|gl.*code|chart.*account', 0.5),
            (r'debit|credit|dr|cr', 0.5),
            (r'journal|entry|posting|transaction', 0.4),
            (r'ledger|balance|period|fiscal', 0.4),
            (r'cost.*center|profit.*center|segment', 0.3),
        ],
        'table_patterns': [
            (r'gl|general.*ledger|journal|account|ledger', 0.5),
            (r'chart.*account|coa', 0.5),
        ],
        'filter_categories': {
            'company': 0.3,
        },
        'value_patterns': [
            (r'^\d{4,}-\d{2,}-\d{2,}', None, 0.3),  # GL account format
        ],
    },
    
    'recruiting': {
        'column_patterns': [
            (r'applicant|candidate|requisition', 0.5),
            (r'interview|offer|hire.*status', 0.4),
            (r'resume|application|job.*posting', 0.4),
            (r'source|referral|recruiter', 0.3),
        ],
        'table_patterns': [
            (r'applicant|candidate|recruit|requisition', 0.5),
        ],
        'filter_categories': {},
        'value_patterns': [],
    },
}


@dataclass
class DomainScore:
    """Score for a detected domain."""
    domain: str
    confidence: float  # 0.0 to 1.0
    evidence: List[str] = field(default_factory=list)
    evidence_count: int = 0
    
    def to_dict(self) -> Dict:
        return {
            'domain': self.domain,
            'confidence': round(self.confidence, 3),
            'evidence_count': self.evidence_count,
            'evidence': self.evidence[:5],  # Top 5 evidence items
        }


@dataclass 
class DomainInferenceResult:
    """Result of domain inference for a project."""
    project_id: str
    project_name: str
    domains: List[DomainScore]
    primary_domain: Optional[str]
    analyzed_at: datetime
    tables_analyzed: int
    columns_analyzed: int
    
    def to_dict(self) -> Dict:
        return {
            'project_id': self.project_id,
            'project_name': self.project_name,
            'domains': [d.to_dict() for d in self.domains],
            'primary_domain': self.primary_domain,
            'analyzed_at': self.analyzed_at.isoformat(),
            'tables_analyzed': self.tables_analyzed,
            'columns_analyzed': self.columns_analyzed,
        }


class DomainInferenceEngine:
    """
    Analyzes project data to infer what domains are present.
    
    Uses pattern matching on column names, table names, filter categories,
    and value patterns to score each potential domain.
    
    Results are stored in project metadata and used for auto-selecting
    expert context in chat.
    """
    
    def __init__(self, structured_handler=None):
        """
        Initialize the engine.
        
        Args:
            structured_handler: Optional DuckDB handler. If not provided,
                               will try to get one.
        """
        self.handler = structured_handler
        self._ensure_handler()
    
    def _ensure_handler(self):
        """Get structured handler if not provided."""
        if self.handler is None:
            try:
                from utils.structured_data_handler import get_structured_handler
                self.handler = get_structured_handler()
            except ImportError:
                try:
                    from backend.utils.structured_data_handler import get_structured_handler
                    self.handler = get_structured_handler()
                except ImportError:
                    logger.warning("[DOMAIN] Structured handler not available")
    
    def infer_domains(self, project: str, project_id: str = None) -> Optional[DomainInferenceResult]:
        """
        Infer domains present in a project's data.
        
        Args:
            project: Project name
            project_id: Optional project UUID for metadata storage
            
        Returns:
            DomainInferenceResult with scored domains
        """
        if not self.handler or not self.handler.conn:
            logger.warning("[DOMAIN] No database connection available")
            return None
        
        try:
            logger.info(f"[DOMAIN] Starting inference for project: {project}")
            
            # Initialize scores for all domains
            domain_scores: Dict[str, DomainScore] = {
                domain: DomainScore(domain=domain, confidence=0.0)
                for domain in DOMAIN_EVIDENCE_PATTERNS.keys()
            }
            
            # Gather evidence from multiple sources
            tables_analyzed, columns_analyzed = self._analyze_column_profiles(
                project, domain_scores
            )
            self._analyze_table_names(project, domain_scores)
            self._analyze_filter_categories(project, domain_scores)
            self._analyze_value_patterns(project, domain_scores)
            
            # Normalize scores to 0-1 range
            self._normalize_scores(domain_scores)
            
            # Sort by confidence, filter low scores
            ranked_domains = sorted(
                [d for d in domain_scores.values() if d.confidence > 0.1],
                key=lambda x: x.confidence,
                reverse=True
            )
            
            # Determine primary domain
            primary = ranked_domains[0].domain if ranked_domains else None
            
            result = DomainInferenceResult(
                project_id=project_id or project,
                project_name=project,
                domains=ranked_domains,
                primary_domain=primary,
                analyzed_at=datetime.now(),
                tables_analyzed=tables_analyzed,
                columns_analyzed=columns_analyzed,
            )
            
            # Store in project metadata if project_id provided
            if project_id:
                self._store_domains(project_id, result)
            
            logger.info(f"[DOMAIN] Inference complete: primary={primary}, "
                       f"detected {len(ranked_domains)} domains")
            
            return result
            
        except Exception as e:
            logger.error(f"[DOMAIN] Inference failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _analyze_column_profiles(
        self, 
        project: str, 
        scores: Dict[str, DomainScore]
    ) -> Tuple[int, int]:
        """
        Analyze column profiles for domain patterns.
        
        Returns (tables_analyzed, columns_analyzed)
        """
        try:
            result = self.handler.conn.execute("""
                SELECT table_name, column_name, inferred_type, 
                       filter_category, distinct_values
                FROM _column_profiles
                WHERE project = ?
            """, [project]).fetchall()
            
            if not result:
                logger.warning(f"[DOMAIN] No column profiles found for {project}")
                return 0, 0
            
            tables = set()
            columns_count = 0
            
            for row in result:
                table_name, col_name, inferred_type, filter_cat, distinct_vals = row
                tables.add(table_name)
                columns_count += 1
                
                col_lower = col_name.lower() if col_name else ''
                
                # Check each domain's column patterns
                for domain, patterns in DOMAIN_EVIDENCE_PATTERNS.items():
                    for pattern, weight in patterns.get('column_patterns', []):
                        if re.search(pattern, col_lower, re.IGNORECASE):
                            scores[domain].confidence += weight
                            scores[domain].evidence_count += 1
                            scores[domain].evidence.append(f"column:{col_name}")
            
            return len(tables), columns_count
            
        except Exception as e:
            logger.warning(f"[DOMAIN] Column analysis failed: {e}")
            return 0, 0
    
    def _analyze_table_names(self, project: str, scores: Dict[str, DomainScore]):
        """Analyze table names for domain patterns."""
        try:
            result = self.handler.conn.execute("""
                SELECT DISTINCT table_name 
                FROM _schema_metadata
                WHERE project = ?
            """, [project]).fetchall()
            
            for (table_name,) in result:
                if not table_name:
                    continue
                    
                table_lower = table_name.lower()
                
                for domain, patterns in DOMAIN_EVIDENCE_PATTERNS.items():
                    for pattern, weight in patterns.get('table_patterns', []):
                        if re.search(pattern, table_lower, re.IGNORECASE):
                            scores[domain].confidence += weight
                            scores[domain].evidence_count += 1
                            scores[domain].evidence.append(f"table:{table_name}")
                            
        except Exception as e:
            logger.warning(f"[DOMAIN] Table analysis failed: {e}")
    
    def _analyze_filter_categories(self, project: str, scores: Dict[str, DomainScore]):
        """Analyze filter categories present in the data."""
        try:
            result = self.handler.conn.execute("""
                SELECT filter_category, COUNT(*) as cnt
                FROM _column_profiles
                WHERE project = ? AND filter_category IS NOT NULL
                GROUP BY filter_category
            """, [project]).fetchall()
            
            for filter_cat, count in result:
                if not filter_cat:
                    continue
                
                # Each domain can get a boost from certain filter categories
                for domain, patterns in DOMAIN_EVIDENCE_PATTERNS.items():
                    cat_weights = patterns.get('filter_categories', {})
                    if filter_cat in cat_weights:
                        weight = cat_weights[filter_cat] * min(count / 5, 1.0)
                        scores[domain].confidence += weight
                        scores[domain].evidence_count += 1
                        scores[domain].evidence.append(f"filter:{filter_cat}({count})")
                        
        except Exception as e:
            logger.warning(f"[DOMAIN] Filter category analysis failed: {e}")
    
    def _analyze_value_patterns(self, project: str, scores: Dict[str, DomainScore]):
        """Analyze actual values for domain-specific patterns."""
        try:
            # Get columns with categorical values
            result = self.handler.conn.execute("""
                SELECT column_name, distinct_values, filter_category
                FROM _column_profiles
                WHERE project = ? 
                  AND distinct_values IS NOT NULL
                  AND inferred_type = 'categorical'
                LIMIT 50
            """, [project]).fetchall()
            
            import json
            
            for col_name, distinct_json, filter_cat in result:
                if not distinct_json:
                    continue
                
                try:
                    values = json.loads(distinct_json) if isinstance(distinct_json, str) else distinct_json
                    if not isinstance(values, list):
                        continue
                    
                    # Check value patterns for each domain
                    for domain, patterns in DOMAIN_EVIDENCE_PATTERNS.items():
                        for pattern, expected_cat, weight in patterns.get('value_patterns', []):
                            # If expected_cat specified, only check matching columns
                            if expected_cat and filter_cat != expected_cat:
                                continue
                            
                            matches = sum(1 for v in values[:20] if v and re.match(pattern, str(v)))
                            if matches > 0:
                                match_ratio = matches / min(len(values), 20)
                                actual_weight = weight * match_ratio
                                scores[domain].confidence += actual_weight
                                scores[domain].evidence_count += 1
                                scores[domain].evidence.append(f"values:{col_name}")
                                
                except (json.JSONDecodeError, TypeError):
                    continue
                    
        except Exception as e:
            logger.warning(f"[DOMAIN] Value pattern analysis failed: {e}")
    
    def _normalize_scores(self, scores: Dict[str, DomainScore]):
        """Normalize confidence scores to 0-1 range."""
        max_score = max((s.confidence for s in scores.values()), default=1.0)
        
        if max_score > 0:
            for score in scores.values():
                # Apply diminishing returns - prevents runaway scores
                raw = score.confidence / max_score
                # Sigmoid-like transformation for smoother distribution
                score.confidence = raw / (1 + raw * 0.5)
    
    def _store_domains(self, project_id: str, result: DomainInferenceResult):
        """Store inferred domains in project metadata."""
        try:
            from utils.database.models import ProjectModel
        except ImportError:
            try:
                from backend.utils.database.models import ProjectModel
            except ImportError:
                logger.warning("[DOMAIN] Cannot import ProjectModel")
                return
        
        try:
            # Get existing project
            project = ProjectModel.get_by_id(project_id)
            if not project:
                logger.warning(f"[DOMAIN] Project {project_id} not found")
                return
            
            # Update metadata with domains
            metadata = project.get('metadata', {}) or {}
            metadata['detected_domains'] = result.to_dict()
            metadata['domain_inference_at'] = result.analyzed_at.isoformat()
            
            ProjectModel.update(project_id, metadata=metadata)
            logger.info(f"[DOMAIN] Stored domains in project {project_id}")
            
        except Exception as e:
            logger.warning(f"[DOMAIN] Failed to store domains: {e}")
    
    def get_project_domains(self, project_id: str) -> Optional[Dict]:
        """
        Get previously inferred domains for a project.
        
        Args:
            project_id: Project UUID
            
        Returns:
            Domain inference result dict or None
        """
        try:
            from utils.database.models import ProjectModel
        except ImportError:
            try:
                from backend.utils.database.models import ProjectModel
            except ImportError:
                return None
        
        try:
            project = ProjectModel.get_by_id(project_id)
            if project:
                metadata = project.get('metadata', {}) or {}
                return metadata.get('detected_domains')
            return None
        except Exception as e:
            logger.warning(f"[DOMAIN] Failed to get domains: {e}")
            return None


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_engine_instance = None

def get_domain_engine(handler=None) -> DomainInferenceEngine:
    """Get or create domain inference engine singleton."""
    global _engine_instance
    if _engine_instance is None or handler is not None:
        _engine_instance = DomainInferenceEngine(handler)
    return _engine_instance


def infer_project_domains(project: str, project_id: str = None, handler=None) -> Optional[Dict]:
    """
    Convenience function to infer domains for a project.
    
    Args:
        project: Project name
        project_id: Optional project UUID
        handler: Optional DuckDB handler
        
    Returns:
        Domain inference result dict
    """
    engine = get_domain_engine(handler)
    result = engine.infer_domains(project, project_id)
    return result.to_dict() if result else None


def get_primary_domain(project_id: str) -> Optional[str]:
    """
    Get the primary domain for a project.
    
    Args:
        project_id: Project UUID
        
    Returns:
        Primary domain name or None
    """
    engine = get_domain_engine()
    domains = engine.get_project_domains(project_id)
    if domains:
        return domains.get('primary_domain')
    return None
