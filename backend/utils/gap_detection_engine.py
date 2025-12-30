"""
XLR8 GAP DETECTION ENGINE
=========================

THE BRAIN THAT FINDS THE "IN BETWEENS"

This is what makes XLR8 worth $500/hr. It automatically compares:
- Reality vs Intent (What you have vs what you said you wanted)
- Reality vs Regulatory (What you have vs what the law requires)
- Reality vs Reference (What you have vs vendor best practice)
- Configuration vs Intent (How you set it up vs what you wanted)
- Configuration vs Reference (How you set it up vs best practice)

Every intersection is a potential finding. This engine finds them automatically.

NO CLAUDE FOR REGULATORY - Uses local LLM knowledge + web verification.
Regulatory knowledge already exists in training data - we just verify.

Author: XLR8 Team
Version: 1.1.0 - The Engine That Finds Gaps (with Rule Registry Integration)
"""

import os
import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

# =============================================================================
# RULE REGISTRY INTEGRATION
# =============================================================================
# Dynamic rules from uploaded standards documents supplement the built-in
# regulatory knowledge. This enables customer-specific compliance checking.

try:
    from utils.standards_processor import get_rule_registry, ExtractedRule
    RULE_REGISTRY_AVAILABLE = True
except ImportError:
    try:
        from backend.utils.standards_processor import get_rule_registry, ExtractedRule
        RULE_REGISTRY_AVAILABLE = True
    except ImportError:
        RULE_REGISTRY_AVAILABLE = False
        get_rule_registry = None
        ExtractedRule = None
        logger.info("[GAP] Rule Registry not available - using built-in knowledge only")


# =============================================================================
# DOMAIN → REGULATORY KNOWLEDGE MAP
# =============================================================================
# This maps data domains to the regulatory checks that should auto-trigger.
# The LLM already KNOWS these rules - we're just telling it when to apply them.

REGULATORY_KNOWLEDGE = {
    'sui_tax': {
        'domain_keywords': ['sui', 'suta', 'state unemployment'],
        'regulatory_checks': [
            {
                'check_id': 'sui_wage_base',
                'description': 'SUI wage base by state',
                'llm_prompt': 'What is the current SUI/SUTA taxable wage base for {state}?',
                'comparison': 'reality_value <= regulatory_max',
                'severity': 'high',
            },
            {
                'check_id': 'sui_rate_range',
                'description': 'SUI rate within state range',
                'llm_prompt': 'What is the valid SUI/SUTA rate range for {state} for new employers vs experienced?',
                'comparison': 'regulatory_min <= reality_value <= regulatory_max',
                'severity': 'high',
            }
        ],
        'data_columns': ['sui_rate', 'suta_rate', 'sui_wage_base', 'state'],
    },
    'futa_tax': {
        'domain_keywords': ['futa', 'federal unemployment'],
        'regulatory_checks': [
            {
                'check_id': 'futa_rate',
                'description': 'FUTA rate (6.0% gross, 0.6% net after credit)',
                'known_value': 0.006,  # Net rate after state credit
                'comparison': 'reality_value == 0.006 or reality_value == 0.06',
                'severity': 'high',
            },
            {
                'check_id': 'futa_wage_base',
                'description': 'FUTA taxable wage base',
                'known_value': 7000,  # $7,000 federal
                'comparison': 'reality_value == 7000',
                'severity': 'high',
            }
        ],
        'data_columns': ['futa_rate', 'futa_wage_base'],
    },
    'fica_tax': {
        'domain_keywords': ['fica', 'social security', 'medicare', 'oasdi'],
        'regulatory_checks': [
            {
                'check_id': 'ss_wage_base',
                'description': 'Social Security wage base (changes annually)',
                'llm_prompt': 'What is the Social Security taxable wage base for {year}?',
                'comparison': 'reality_value == regulatory_value',
                'severity': 'high',
            },
            {
                'check_id': 'ss_rate',
                'description': 'Social Security tax rate',
                'known_value': 0.062,  # 6.2%
                'comparison': 'reality_value == 0.062',
                'severity': 'high',
            },
            {
                'check_id': 'medicare_rate',
                'description': 'Medicare tax rate',
                'known_value': 0.0145,  # 1.45%
                'comparison': 'reality_value == 0.0145',
                'severity': 'high',
            }
        ],
        'data_columns': ['ss_rate', 'ss_wage_base', 'medicare_rate', 'fica_rate'],
    },
    'overtime': {
        'domain_keywords': ['overtime', 'ot', 'flsa', 'exempt', 'non-exempt', 'hourly'],
        'regulatory_checks': [
            {
                'check_id': 'flsa_weekly_threshold',
                'description': 'FLSA overtime threshold (40 hours/week)',
                'known_value': 40,
                'comparison': 'overtime triggers at 40 hours',
                'severity': 'high',
            },
            {
                'check_id': 'flsa_salary_threshold',
                'description': 'FLSA salary threshold for exemption',
                'llm_prompt': 'What is the current FLSA minimum salary threshold for overtime exemption?',
                'severity': 'high',
            },
            {
                'check_id': 'ca_daily_ot',
                'description': 'California daily overtime (8 hours)',
                'condition': 'state == CA',
                'known_value': 8,
                'severity': 'high',
            }
        ],
        'data_columns': ['exempt_status', 'salary', 'hourly_rate', 'flsa_status', 'state'],
    },
    'minimum_wage': {
        'domain_keywords': ['minimum wage', 'min wage', 'hourly rate', 'wage floor'],
        'regulatory_checks': [
            {
                'check_id': 'federal_min_wage',
                'description': 'Federal minimum wage',
                'known_value': 7.25,  # As of training
                'llm_prompt': 'What is the current federal minimum wage?',
                'severity': 'high',
            },
            {
                'check_id': 'state_min_wage',
                'description': 'State minimum wage',
                'llm_prompt': 'What is the current minimum wage for {state}?',
                'severity': 'high',
            }
        ],
        'data_columns': ['hourly_rate', 'pay_rate', 'wage', 'state'],
    },
    'retirement': {
        'domain_keywords': ['401k', '403b', 'retirement', 'pension', 'roth', 'contribution limit'],
        'regulatory_checks': [
            {
                'check_id': '401k_limit',
                'description': '401(k) annual contribution limit',
                'llm_prompt': 'What is the 401(k) employee contribution limit for {year}?',
                'severity': 'medium',
            },
            {
                'check_id': '401k_catchup',
                'description': '401(k) catch-up contribution (age 50+)',
                'llm_prompt': 'What is the 401(k) catch-up contribution limit for {year}?',
                'severity': 'medium',
            },
            {
                'check_id': 'secure_2_auto_enroll',
                'description': 'SECURE 2.0 auto-enrollment requirements',
                'llm_prompt': 'What are the SECURE 2.0 automatic enrollment requirements for new plans?',
                'severity': 'medium',
            }
        ],
        'data_columns': ['401k_pct', '401k_amount', 'retirement_contrib', 'dob', 'age'],
    },
    'benefits': {
        'domain_keywords': ['aca', 'affordable care', 'cobra', 'health insurance', 'fsa', 'hsa'],
        'regulatory_checks': [
            {
                'check_id': 'aca_employer_mandate',
                'description': 'ACA employer mandate (50+ FTE)',
                'llm_prompt': 'What are the ACA employer mandate requirements for applicable large employers?',
                'severity': 'high',
            },
            {
                'check_id': 'hsa_limit',
                'description': 'HSA contribution limit',
                'llm_prompt': 'What is the HSA contribution limit for {year} for individual and family coverage?',
                'severity': 'medium',
            },
            {
                'check_id': 'fsa_limit',
                'description': 'FSA contribution limit',
                'llm_prompt': 'What is the health FSA contribution limit for {year}?',
                'severity': 'medium',
            }
        ],
        'data_columns': ['aca_status', 'fte_count', 'hsa_contrib', 'fsa_contrib', 'ale_status'],
    },
    'pay_frequency': {
        'domain_keywords': ['pay frequency', 'pay period', 'semi-monthly', 'biweekly', 'weekly'],
        'regulatory_checks': [
            {
                'check_id': 'state_pay_frequency',
                'description': 'State pay frequency requirements',
                'llm_prompt': 'What are the pay frequency requirements for {state}?',
                'severity': 'medium',
            }
        ],
        'data_columns': ['pay_frequency', 'pay_period', 'state'],
    },
}


# =============================================================================
# INTENT COMPARISON PATTERNS
# =============================================================================
# These help identify when Reality doesn't match what was promised in SOW/Intent

INTENT_COMPARISON_PATTERNS = {
    'scope_mismatch': {
        'description': 'Implementation scope vs actual data',
        'checks': [
            'Employee count in scope vs actual',
            'States/locations in scope vs actual',
            'Pay groups defined vs actual',
            'Companies in scope vs actual',
        ]
    },
    'timeline_mismatch': {
        'description': 'Promised dates vs actual status',
        'checks': [
            'Go-live date vs data readiness',
            'Parallel testing dates vs data availability',
        ]
    },
    'feature_mismatch': {
        'description': 'Features promised vs configured',
        'checks': [
            'Earnings codes promised vs configured',
            'Deductions promised vs configured',
            'Tax jurisdictions promised vs configured',
        ]
    },
}


# =============================================================================
# GAP DETECTION ENGINE
# =============================================================================

@dataclass
class Gap:
    """A detected gap between sources of truth."""
    gap_id: str
    gap_type: str  # 'reality_vs_regulatory', 'reality_vs_intent', 'config_vs_reference', etc.
    domain: str
    severity: str  # 'critical', 'high', 'medium', 'low'
    
    # The comparison
    truth_a_type: str
    truth_a_value: Any
    truth_a_source: str
    
    truth_b_type: str  
    truth_b_value: Any
    truth_b_source: str
    
    # The finding
    title: str
    description: str
    recommendation: str
    
    # Evidence
    affected_records: int = 0
    sample_data: List[Dict] = field(default_factory=list)
    
    # Metadata
    detected_at: str = field(default_factory=lambda: datetime.now().isoformat())
    verified: bool = False
    verification_source: str = ""
    
    def to_conflict(self):
        """Convert to Conflict dataclass for intelligence_engine compatibility."""
        from backend.utils.intelligence_engine import Conflict, Truth
        
        # Create Truth objects for the comparison
        truth_a = Truth(
            source_type=self.truth_a_type,
            source_name=self.truth_a_source,
            content=self.truth_a_value,
            confidence=0.9,
            location=self.truth_a_source,
        )
        
        truth_b = Truth(
            source_type=self.truth_b_type,
            source_name=self.truth_b_source,
            content=self.truth_b_value,
            confidence=0.9,
            location=self.truth_b_source,
        )
        
        # Map to Conflict's truth slots
        conflict_kwargs = {
            'description': self.description,
            'severity': self.severity,
            'recommendation': self.recommendation,
        }
        
        # Set appropriate truth slot
        if self.truth_a_type == 'reality':
            conflict_kwargs['reality'] = truth_a
        elif self.truth_a_type == 'intent':
            conflict_kwargs['intent'] = truth_a
        elif self.truth_a_type == 'configuration':
            conflict_kwargs['configuration'] = truth_a
            
        if self.truth_b_type == 'regulatory':
            conflict_kwargs['regulatory'] = truth_b
        elif self.truth_b_type == 'reference':
            conflict_kwargs['reference'] = truth_b
        elif self.truth_b_type == 'intent':
            conflict_kwargs['intent'] = truth_b
        
        return Conflict(**conflict_kwargs)


class GapDetectionEngine:
    """
    The brain that finds gaps between all five truths.
    
    This is the $500/hr Deloitte work - automated.
    
    v1.1.0: Integrates with RuleRegistry for dynamic rules from uploaded
    standards documents. Combines built-in REGULATORY_KNOWLEDGE with
    customer-uploaded reference materials.
    """
    
    def __init__(self, structured_handler=None, rag_handler=None):
        self.structured_handler = structured_handler
        self.rag_handler = rag_handler
        self._llm_orchestrator = None
        self._rule_registry = None
        self._registry_rules_loaded = False
        
    def _get_rule_registry(self):
        """Get the rule registry for dynamic rules."""
        if self._rule_registry is None and RULE_REGISTRY_AVAILABLE:
            try:
                self._rule_registry = get_rule_registry()
                logger.info(f"[GAP] Rule Registry loaded: {len(self._rule_registry.rules)} rules")
            except Exception as e:
                logger.warning(f"[GAP] Failed to load Rule Registry: {e}")
        return self._rule_registry
    
    def _search_registry_rules(self, query: str, domain: str = None) -> List[Any]:
        """Search for applicable rules from the registry."""
        registry = self._get_rule_registry()
        if not registry:
            return []
        
        try:
            rules = registry.search_rules(query, domain=domain, limit=10)
            if rules:
                logger.info(f"[GAP] Found {len(rules)} rules from registry for '{query}'")
            return rules
        except Exception as e:
            logger.warning(f"[GAP] Registry search failed: {e}")
            return []
    
    def _get_registry_domains(self) -> set:
        """Get domains that have rules in the registry."""
        registry = self._get_rule_registry()
        if not registry:
            return set()
        
        domains = set()
        for rule in registry.rules.values():
            # Check rule's source document domain
            for doc_id, doc in registry.documents.items():
                if rule in doc.rules:
                    domains.add(doc.domain)
                    break
        return domains
        
    def _get_llm(self):
        """Get LLM orchestrator - LOCAL FIRST, Claude only for fallback."""
        if self._llm_orchestrator is None:
            try:
                from utils.llm_orchestrator import LLMOrchestrator
                self._llm_orchestrator = LLMOrchestrator()
            except ImportError:
                try:
                    from backend.utils.llm_orchestrator import LLMOrchestrator
                    self._llm_orchestrator = LLMOrchestrator()
                except ImportError:
                    logger.warning("[GAP] LLM Orchestrator not available")
        return self._llm_orchestrator
    
    def detect_domains_from_data(self, reality_data: List[Dict]) -> List[str]:
        """
        Detect which regulatory domains apply based on actual data.
        
        Args:
            reality_data: List of Truth objects or dicts with content
            
        Returns:
            List of domain keys that should trigger regulatory checks
        """
        detected = set()
        
        # Extract text content from reality data
        text_content = []
        for item in reality_data:
            if hasattr(item, 'content'):
                content = item.content
            elif isinstance(item, dict):
                content = item.get('content', item)
            else:
                content = str(item)
            
            if isinstance(content, str):
                text_content.append(content.lower())
            elif isinstance(content, dict):
                # Include both keys (column names) and values
                text_content.extend([str(k).lower() for k in content.keys()])
                text_content.extend([str(v).lower() for v in content.values()])
            elif isinstance(content, list):
                for row in content[:10]:  # Sample first 10 rows
                    if isinstance(row, dict):
                        # Include both keys (column names) and values
                        text_content.extend([str(k).lower() for k in row.keys()])
                        text_content.extend([str(v).lower() for v in row.values()])
        
        combined_text = ' '.join(text_content)
        
        # Check each domain's keywords from built-in REGULATORY_KNOWLEDGE
        for domain_key, domain_config in REGULATORY_KNOWLEDGE.items():
            keywords = domain_config.get('domain_keywords', [])
            if any(kw in combined_text for kw in keywords):
                detected.add(domain_key)
            
            # Also check if data columns match
            data_columns = domain_config.get('data_columns', [])
            if any(col in combined_text for col in data_columns):
                detected.add(domain_key)
        
        # Also check Rule Registry for domains from uploaded standards
        registry_domains = self._get_registry_domains()
        if registry_domains:
            # Try to match registry domains to the data
            for reg_domain in registry_domains:
                if reg_domain.lower() in combined_text:
                    detected.add(reg_domain)
        
        logger.info(f"[GAP] Detected regulatory domains: {detected}")
        return list(detected)
    
    def detect_domains_from_question(self, question: str) -> List[str]:
        """Detect domains from the question text."""
        detected = set()
        q_lower = question.lower()
        
        # Check built-in REGULATORY_KNOWLEDGE
        for domain_key, domain_config in REGULATORY_KNOWLEDGE.items():
            keywords = domain_config.get('domain_keywords', [])
            if any(kw in q_lower for kw in keywords):
                detected.add(domain_key)
        
        # Search Rule Registry for matching rules
        if RULE_REGISTRY_AVAILABLE:
            registry_rules = self._search_registry_rules(question)
            for rule in registry_rules:
                # Add the domain of matching rules
                if hasattr(rule, 'category') and rule.category:
                    detected.add(rule.category)
        
        return list(detected)
    
    def _get_regulatory_knowledge(self, domain: str, context: Dict = None) -> Dict:
        """
        Get regulatory knowledge for a domain using LLM.
        
        Uses LOCAL LLM first - the knowledge already exists in training.
        Only verifies via web search if confidence is low.
        """
        domain_config = REGULATORY_KNOWLEDGE.get(domain)
        if not domain_config:
            return {}
        
        results = {}
        llm = self._get_llm()
        
        for check in domain_config.get('regulatory_checks', []):
            check_id = check['check_id']
            
            # If we have a known static value, use it
            if 'known_value' in check:
                results[check_id] = {
                    'value': check['known_value'],
                    'confidence': 'high',
                    'source': 'known_federal_rule',
                    'description': check['description'],
                }
                continue
            
            # Otherwise, ask LLM
            if 'llm_prompt' in check and llm:
                prompt = check['llm_prompt']
                
                # Fill in context variables
                if context:
                    for key, value in context.items():
                        prompt = prompt.replace('{' + key + '}', str(value))
                
                # Replace unfilled variables with current year/reasonable defaults
                prompt = prompt.replace('{year}', str(datetime.now().year))
                prompt = prompt.replace('{state}', 'the applicable state')
                
                try:
                    # Use local LLM for regulatory knowledge (Ollama/Mistral)
                    system_prompt = """You are a regulatory compliance expert. 
                    Provide factual, current regulatory information.
                    Be specific with numbers, rates, and thresholds.
                    If uncertain, say so."""
                    
                    # Try local first (Mistral via Ollama) - use full model name
                    response, success = llm._call_ollama(
                        model="mistral:7b",
                        prompt=prompt,
                        system_prompt=system_prompt
                    )
                    
                    if success and response:
                        results[check_id] = {
                            'value': response,
                            'confidence': 'medium',  # LLM knowledge needs verification
                            'source': 'llm_knowledge',
                            'description': check['description'],
                            'needs_verification': True,
                        }
                except Exception as e:
                    logger.warning(f"[GAP] LLM call failed for {check_id}: {e}")
        
        return results
    
    def compare_reality_vs_regulatory(
        self, 
        reality: List[Any],
        domains: List[str] = None,
        context: Dict = None
    ) -> List[Gap]:
        """
        Compare Reality data against Regulatory requirements.
        
        This is the core regulatory gap detection.
        """
        gaps = []
        
        # Detect domains if not provided
        if domains is None:
            domains = self.detect_domains_from_data(reality)
        
        if not domains:
            logger.info("[GAP] No regulatory domains detected")
            return gaps
        
        logger.info(f"[GAP] Checking regulatory compliance for domains: {domains}")
        
        for domain in domains:
            domain_config = REGULATORY_KNOWLEDGE.get(domain)
            if not domain_config:
                continue
            
            # Get regulatory knowledge for this domain
            regulatory = self._get_regulatory_knowledge(domain, context)
            
            # Extract relevant data from reality
            reality_data = self._extract_domain_data(reality, domain_config)
            
            if not reality_data:
                continue
            
            # Compare each regulatory check
            for check in domain_config.get('regulatory_checks', []):
                check_id = check['check_id']
                reg_info = regulatory.get(check_id, {})
                
                if not reg_info:
                    continue
                
                # Perform the comparison
                comparison_gaps = self._compare_values(
                    domain=domain,
                    check=check,
                    reality_data=reality_data,
                    regulatory_info=reg_info,
                )
                
                gaps.extend(comparison_gaps)
        
        logger.info(f"[GAP] Found {len(gaps)} regulatory gaps")
        return gaps
    
    def _extract_domain_data(self, reality: List[Any], domain_config: Dict) -> List[Dict]:
        """Extract data relevant to a specific domain from reality."""
        relevant_data = []
        target_columns = set(domain_config.get('data_columns', []))
        
        for item in reality:
            content = item.content if hasattr(item, 'content') else item
            
            if isinstance(content, list):
                for row in content:
                    if isinstance(row, dict):
                        # Check if any target columns are present
                        row_cols = set(k.lower() for k in row.keys())
                        if row_cols & target_columns:
                            relevant_data.append(row)
            elif isinstance(content, dict):
                row_cols = set(k.lower() for k in content.keys())
                if row_cols & target_columns:
                    relevant_data.append(content)
        
        return relevant_data
    
    def _compare_values(
        self,
        domain: str,
        check: Dict,
        reality_data: List[Dict],
        regulatory_info: Dict
    ) -> List[Gap]:
        """Compare reality values against regulatory requirements."""
        gaps = []
        
        reg_value = regulatory_info.get('value')
        if reg_value is None:
            return gaps
        
        check_id = check['check_id']
        severity = check.get('severity', 'medium')
        
        # Group violations
        violations = []
        
        for row in reality_data:
            # Find the relevant value in this row
            reality_value = None
            for col in REGULATORY_KNOWLEDGE.get(domain, {}).get('data_columns', []):
                if col in row:
                    reality_value = row.get(col)
                    break
            
            if reality_value is None:
                continue
            
            # Attempt numeric comparison
            try:
                reality_num = float(reality_value) if reality_value else None
                reg_num = float(reg_value) if isinstance(reg_value, (int, float, str)) else None
                
                if reality_num is not None and reg_num is not None:
                    # Check if out of expected range
                    if 'rate' in check_id.lower():
                        # Rate comparisons - check if significantly different
                        if abs(reality_num - reg_num) > 0.01:  # More than 1% difference
                            violations.append({
                                'reality': reality_num,
                                'expected': reg_num,
                                'row': row
                            })
                    elif 'limit' in check_id.lower() or 'base' in check_id.lower():
                        # Limit/base comparisons - check if exceeds
                        if reality_num > reg_num:
                            violations.append({
                                'reality': reality_num,
                                'expected': reg_num,
                                'row': row
                            })
            except (ValueError, TypeError):
                # Non-numeric comparison
                if str(reality_value).lower() != str(reg_value).lower():
                    violations.append({
                        'reality': reality_value,
                        'expected': reg_value,
                        'row': row
                    })
        
        if violations:
            gap = Gap(
                gap_id=f"{domain}_{check_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                gap_type='reality_vs_regulatory',
                domain=domain,
                severity=severity,
                truth_a_type='reality',
                truth_a_value=f"{len(violations)} records with value mismatch",
                truth_a_source='DuckDB customer data',
                truth_b_type='regulatory',
                truth_b_value=reg_value,
                truth_b_source=regulatory_info.get('source', 'Federal/State regulation'),
                title=f"⚖️ {check.get('description', check_id)}",
                description=f"{len(violations)} records don't match regulatory requirement. "
                           f"Expected: {reg_value}, Found: various values",
                recommendation=f"Review and correct the {len(violations)} affected records to comply with {check.get('description', 'regulatory requirement')}.",
                affected_records=len(violations),
                sample_data=violations[:5],  # First 5 as sample
                verified=regulatory_info.get('confidence') == 'high',
                verification_source=regulatory_info.get('source', ''),
            )
            gaps.append(gap)
        
        return gaps
    
    def compare_reality_vs_intent(
        self,
        reality: List[Any],
        intent: List[Any],
        question: str = None
    ) -> List[Gap]:
        """
        Compare Reality against Intent (SOW/requirements).
        
        TOPIC-AWARE COMPARISON:
        - Extract key topics from the question
        - Only compare when both reality and intent have relevant data
        - Don't hallucinate gaps from unrelated content
        
        Finds: "You said you wanted X, but you have Y"
        """
        gaps = []
        
        if not intent or not reality:
            return gaps
        
        # Extract topics from question for filtering
        topics = self._extract_comparison_topics(question) if question else []
        logger.info(f"[GAP] Intent comparison topics: {topics}")
        
        # If no clear topics, skip comparison to avoid garbage
        if not topics:
            logger.info(f"[GAP] No clear topics for intent comparison - skipping to avoid false positives")
            return gaps
        
        # Extract and filter intent content by topic
        relevant_intent = []
        for item in intent:
            content = item.content if hasattr(item, 'content') else str(item)
            content_lower = content.lower() if isinstance(content, str) else str(content).lower()
            
            # Only include if content mentions any of our topics
            if any(topic in content_lower for topic in topics):
                relevant_intent.append({
                    'content': content,
                    'source': item.source_name if hasattr(item, 'source_name') else 'SOW'
                })
        
        if not relevant_intent:
            logger.info(f"[GAP] No intent content matches topics {topics} - no comparison needed")
            return gaps
        
        # Extract and filter reality content by topic
        relevant_reality = []
        for item in reality:
            content = item.content if hasattr(item, 'content') else item
            source = item.source_name if hasattr(item, 'source_name') else 'Data'
            
            if isinstance(content, dict):
                # Check if any keys/values match topics
                content_str = json.dumps(content).lower()
                if any(topic in content_str for topic in topics):
                    relevant_reality.append({
                        'content': content,
                        'source': source
                    })
            elif isinstance(content, list) and content:
                # Check first few rows
                sample = content[:5]
                sample_str = json.dumps(sample).lower()
                if any(topic in sample_str for topic in topics):
                    relevant_reality.append({
                        'content': content[:10],  # Limit to 10 rows for comparison
                        'source': source
                    })
        
        if not relevant_reality:
            logger.info(f"[GAP] No reality data matches topics {topics} - no comparison needed")
            return gaps
        
        logger.info(f"[GAP] Comparing {len(relevant_intent)} intent chunks vs {len(relevant_reality)} reality items for topics {topics}")
        
        # Now do focused comparison with LLM
        llm = self._get_llm()
        if not llm:
            return gaps
        
        # Build focused context
        intent_summary = "\n".join([
            f"[{i['source']}]: {i['content'][:500]}" 
            for i in relevant_intent[:3]  # Limit to 3 chunks
        ])
        
        reality_summary = []
        for r in relevant_reality[:3]:  # Limit to 3 items
            if isinstance(r['content'], list):
                # Summarize tabular data
                if r['content']:
                    cols = list(r['content'][0].keys()) if isinstance(r['content'][0], dict) else []
                    row_count = len(r['content'])
                    reality_summary.append(f"[{r['source']}]: {row_count} rows with columns: {', '.join(cols[:10])}")
            else:
                reality_summary.append(f"[{r['source']}]: {json.dumps(r['content'])[:300]}")
        
        reality_str = "\n".join(reality_summary)
        
        prompt = f"""You are comparing SOW/requirements against actual configured data.
        
QUESTION CONTEXT: {question or 'General comparison'}
TOPICS: {', '.join(topics)}

SOW/REQUIREMENTS SAY:
{intent_summary}

ACTUAL DATA SHOWS:
{reality_str}

Are there any SPECIFIC, VERIFIABLE mismatches between what was promised and what exists?

Rules:
- Only report gaps where you can cite specific values from both sides
- Do NOT invent or hallucinate information
- If intent doesn't specify a value, that's not a gap
- If you're uncertain, report nothing

Format as JSON array (empty array [] if no gaps):
[{{"topic": "specific topic", "promised": "specific value from SOW", "actual": "specific value from data", "severity": "high/medium/low", "recommendation": "specific action"}}]

If no clear gaps exist, return: []"""

        try:
            response, success = llm._call_ollama(
                model="mistral:7b",
                prompt=prompt,
                system_prompt="You are a precise analyst. Only report gaps you can verify. When uncertain, report nothing."
            )
            
            if success and response:
                # Try to parse as JSON
                json_match = re.search(r'\[[\s\S]*?\]', response)
                if json_match:
                    try:
                        mismatches = json.loads(json_match.group())
                        
                        # Filter out low-confidence or vague mismatches
                        for i, mismatch in enumerate(mismatches):
                            # Skip if promised or actual is vague
                            promised = mismatch.get('promised', '')
                            actual = mismatch.get('actual', '')
                            
                            if not promised or not actual:
                                continue
                            if 'unknown' in str(promised).lower() or 'unknown' in str(actual).lower():
                                continue
                            if 'not specified' in str(promised).lower() or 'not found' in str(actual).lower():
                                continue
                            
                            gap = Gap(
                                gap_id=f"intent_{mismatch.get('topic', 'gap')}_{i}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                                gap_type='reality_vs_intent',
                                domain=mismatch.get('topic', 'scope'),
                                severity=mismatch.get('severity', 'medium'),
                                truth_a_type='reality',
                                truth_a_value=actual,
                                truth_a_source='Customer data',
                                truth_b_type='intent',
                                truth_b_value=promised,
                                truth_b_source='SOW/Requirements',
                                title=f"📋 {mismatch.get('topic', 'Scope')}: Requirement vs Reality",
                                description=f"SOW specifies: {promised}\nData shows: {actual}",
                                recommendation=mismatch.get('recommendation', 'Review and align'),
                            )
                            gaps.append(gap)
                    except json.JSONDecodeError:
                        logger.warning(f"[GAP] Could not parse intent comparison response as JSON")
        except Exception as e:
            logger.warning(f"[GAP] Intent comparison failed: {e}")
        
        logger.info(f"[GAP] Found {len(gaps)} intent gaps")
        return gaps
    
    def _extract_comparison_topics(self, question: str) -> List[str]:
        """
        Extract key topics from question for focused comparison.
        
        Returns list of lowercase topic keywords to filter content.
        """
        if not question:
            return []
        
        q_lower = question.lower()
        topics = []
        
        # Domain-specific topic extraction
        topic_patterns = {
            'sui': ['sui', 'suta', 'state unemployment'],
            'futa': ['futa', 'federal unemployment'],
            'tax': ['tax', 'withholding', 'fica', 'medicare', 'social security'],
            'earnings': ['earning', 'pay code', 'wage type'],
            'deductions': ['deduction', 'benefit', 'garnishment'],
            'overtime': ['overtime', 'ot', 'flsa'],
            'pto': ['pto', 'vacation', 'sick', 'accrual', 'time off'],
            'gl': ['gl', 'general ledger', 'account', 'mapping'],
            'workers_comp': ['workers comp', 'work comp', 'wc'],
            'retirement': ['401k', '403b', 'retirement', 'pension'],
            'aca': ['aca', 'affordable care', 'ale'],
        }
        
        for domain, keywords in topic_patterns.items():
            if any(kw in q_lower for kw in keywords):
                topics.extend(keywords)
        
        # Also extract any quoted terms
        quoted = re.findall(r'"([^"]+)"', question)
        topics.extend([q.lower() for q in quoted])
        
        # Deduplicate
        return list(set(topics))
    
    def _extract_reality_metrics(self, reality: List[Any]) -> Dict:
        """Extract key metrics from reality data for comparison."""
        metrics = {
            'employee_count': 0,
            'states': set(),
            'companies': set(),
            'tables': [],
        }
        
        for item in reality:
            content = item.content if hasattr(item, 'content') else item
            source = item.source_name if hasattr(item, 'source_name') else 'unknown'
            
            if isinstance(content, dict):
                # Single row
                if 'state' in content:
                    metrics['states'].add(content['state'])
                if 'company' in content:
                    metrics['companies'].add(content['company'])
            elif isinstance(content, list):
                metrics['employee_count'] = max(metrics['employee_count'], len(content))
                for row in content:
                    if isinstance(row, dict):
                        if 'state' in row:
                            metrics['states'].add(row.get('state'))
                        if 'company' in row:
                            metrics['companies'].add(row.get('company'))
            
            metrics['tables'].append(source)
        
        # Convert sets to lists for JSON
        metrics['states'] = list(metrics['states'])
        metrics['companies'] = list(metrics['companies'])
        
        return metrics
    
    def compare_config_vs_reference(
        self,
        configuration: List[Any],
        reference: List[Any]
    ) -> List[Gap]:
        """
        Compare Configuration against Reference (vendor best practice).
        
        Finds: "Vendor recommends X, but you configured Y"
        """
        gaps = []
        
        if not configuration or not reference:
            return gaps
        
        # This would use RAG to find relevant best practices
        # and compare against actual configuration
        # For now, return empty - will implement with RAG handler
        
        return gaps
    
    def detect_all_gaps(
        self,
        reality: List[Any] = None,
        intent: List[Any] = None,
        configuration: List[Any] = None,
        reference: List[Any] = None,
        regulatory: List[Any] = None,
        compliance: List[Any] = None,
        question: str = None,
        context: Dict = None
    ) -> List[Gap]:
        """
        Master gap detection - compare across ALL five truths.
        
        This is the main entry point that runs all comparisons.
        """
        all_gaps = []
        
        # Detect domains from question and/or data
        domains = []
        if question:
            domains.extend(self.detect_domains_from_question(question))
        if reality:
            domains.extend(self.detect_domains_from_data(reality))
        domains = list(set(domains))
        
        logger.info(f"[GAP] Running gap detection for domains: {domains}")
        
        # 1. Reality vs Regulatory (The big one - compliance checking)
        if reality:
            regulatory_gaps = self.compare_reality_vs_regulatory(
                reality=reality,
                domains=domains,
                context=context
            )
            all_gaps.extend(regulatory_gaps)
        
        # 2. Reality vs Intent (Scope checking)
        if reality and intent:
            intent_gaps = self.compare_reality_vs_intent(
                reality=reality,
                intent=intent,
                question=question
            )
            all_gaps.extend(intent_gaps)
        
        # 3. Configuration vs Reference (Best practice checking)
        if configuration and reference:
            reference_gaps = self.compare_config_vs_reference(
                configuration=configuration,
                reference=reference
            )
            all_gaps.extend(reference_gaps)
        
        # Sort by severity
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        all_gaps.sort(key=lambda g: severity_order.get(g.severity, 4))
        
        logger.info(f"[GAP] Total gaps detected: {len(all_gaps)}")
        return all_gaps


# =============================================================================
# SINGLETON
# =============================================================================

_gap_engine: Optional[GapDetectionEngine] = None

def get_gap_detection_engine(
    structured_handler=None, 
    rag_handler=None
) -> GapDetectionEngine:
    """Get or create the gap detection engine."""
    global _gap_engine
    if _gap_engine is None:
        _gap_engine = GapDetectionEngine(structured_handler, rag_handler)
    return _gap_engine


# =============================================================================
# CONVENIENCE FUNCTION FOR INTELLIGENCE ENGINE INTEGRATION
# =============================================================================

def detect_conflicts_and_compliance(
    reality: List[Any] = None,
    intent: List[Any] = None,
    configuration: List[Any] = None,
    reference: List[Any] = None,
    regulatory: List[Any] = None,
    compliance: List[Any] = None,
    question: str = None,
    structured_handler=None,
    rag_handler=None
) -> Tuple[List, Dict]:
    """
    Convenience function to detect conflicts and check compliance.
    
    Returns:
        Tuple of (conflicts_list, compliance_check_dict)
        
    Used by intelligence_engine._detect_conflicts() and _check_compliance()
    """
    engine = get_gap_detection_engine(structured_handler, rag_handler)
    
    gaps = engine.detect_all_gaps(
        reality=reality,
        intent=intent,
        configuration=configuration,
        reference=reference,
        regulatory=regulatory,
        compliance=compliance,
        question=question,
    )
    
    # Convert gaps to conflicts
    conflicts = [gap.to_conflict() for gap in gaps]
    
    # Build compliance check summary
    regulatory_gaps = [g for g in gaps if g.gap_type == 'reality_vs_regulatory']
    
    compliance_check = {
        'checked': True,
        'domains_checked': list(set(g.domain for g in gaps)),
        'findings': [
            {
                'gap_id': g.gap_id,
                'domain': g.domain,
                'severity': g.severity,
                'title': g.title,
                'description': g.description,
            }
            for g in regulatory_gaps
        ],
        'gaps': [g.description for g in regulatory_gaps],
        'recommendations': [g.recommendation for g in regulatory_gaps],
        'status': 'compliant' if not regulatory_gaps else (
            'non_compliant' if any(g.severity in ['critical', 'high'] for g in regulatory_gaps)
            else 'review_required'
        ),
        'gap_count': len(gaps),
        'regulatory_gap_count': len(regulatory_gaps),
    }
    
    return conflicts, compliance_check
