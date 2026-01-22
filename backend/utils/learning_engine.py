"""
XLR8 Learning Engine - Self-Improving AI System
================================================

PHILOSOPHY:
- Every Claude call is a learning opportunity
- Every user correction makes us smarter
- Data never leaves our pipeline
- Reduce external dependency over time

COMPONENTS:
1. TrainingDataCollector - Captures Claude's good outputs
2. FeedbackLoop - Learns from user corrections
3. RulesEngine - Deterministic patterns (no LLM needed)
4. KnowledgeCache - Semantic retrieval of past analyses
5. ModelTrainer - Fine-tunes local models

INTEGRATION:
- PlaybookFramework uses LearningHook which calls get_learning_system()
- record_feedback() supports both old and new signatures
- get_patterns() returns suppressions for playbook scans

Author: XLR8 Team
Version: 2.0.0 - Playbook Integration
"""

import os
import re
import json
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# =============================================================================
# STORAGE PATHS
# =============================================================================

# Use /data if available, otherwise fall back to local ./data directory
DATA_DIR = Path(os.getenv("XLR8_DATA_DIR", "/data"))

# Try to create in /data, fall back to local if permissions fail
try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
except PermissionError:
    DATA_DIR = Path("./data")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    logger.warning(f"[LEARNING] Using local data directory: {DATA_DIR}")

TRAINING_DIR = DATA_DIR / "training"
FEEDBACK_DIR = DATA_DIR / "feedback"
RULES_DIR = DATA_DIR / "rules"
CACHE_DIR = DATA_DIR / "knowledge_cache"

# Ensure directories exist
for d in [TRAINING_DIR, FEEDBACK_DIR, RULES_DIR, CACHE_DIR]:
    try:
        d.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.warning(f"[LEARNING] Could not create {d}: {e}")


# =============================================================================
# 1. TRAINING DATA COLLECTOR
# =============================================================================

class TrainingDataCollector:
    """
    Captures Claude's outputs as training data for local model fine-tuning.
    
    Every time Claude produces a good result:
    1. Store the input (document + prompt)
    2. Store the output (Claude's analysis)
    3. Store metadata (action_id, quality score, etc.)
    
    Later: Use this data to fine-tune Mistral/Llama
    """
    
    def __init__(self):
        self.training_file = TRAINING_DIR / "claude_outputs.jsonl"
        self.stats_file = TRAINING_DIR / "stats.json"
        self._load_stats()
    
    def _load_stats(self):
        """Load collection statistics"""
        if self.stats_file.exists():
            with open(self.stats_file, 'r') as f:
                self.stats = json.load(f)
        else:
            self.stats = {
                'total_collected': 0,
                'by_action': {},
                'by_quality': {'high': 0, 'medium': 0, 'low': 0},
                'started': datetime.now().isoformat()
            }
    
    def _save_stats(self):
        with open(self.stats_file, 'w') as f:
            json.dump(self.stats, f, indent=2)
    
    def collect(self, 
                input_text: str, 
                prompt: str,
                output: Dict,
                action_id: str,
                quality_score: str = 'medium',  # high/medium/low
                user_approved: bool = False):
        """
        Collect a Claude output as training data.
        
        Args:
            input_text: The document content sent to Claude
            prompt: The full prompt used
            output: Claude's JSON response
            action_id: Which Year-End action this was for
            quality_score: Assessed quality of the response
            user_approved: Whether user confirmed this was good
        """
        # Create training example
        example = {
            'id': hashlib.md5(f"{input_text[:500]}{datetime.now().isoformat()}".encode()).hexdigest()[:12],
            'timestamp': datetime.now().isoformat(),
            'action_id': action_id,
            'input_hash': hashlib.md5(input_text.encode()).hexdigest()[:16],
            'input_length': len(input_text),
            'prompt': prompt[:2000],  # Truncate long prompts
            'input_sample': input_text[:1000],  # Sample for reference
            'output': output,
            'quality': quality_score,
            'user_approved': user_approved,
            'model': 'claude-sonnet-4'
        }
        
        # Append to JSONL file (one JSON object per line)
        with open(self.training_file, 'a') as f:
            f.write(json.dumps(example) + '\n')
        
        # Update stats
        self.stats['total_collected'] += 1
        self.stats['by_action'][action_id] = self.stats['by_action'].get(action_id, 0) + 1
        self.stats['by_quality'][quality_score] = self.stats['by_quality'].get(quality_score, 0) + 1
        self._save_stats()
        
        logger.info(f"[LEARNING] Collected training example for {action_id} (quality={quality_score})")
        
        return example['id']
    
    def get_examples_for_action(self, action_id: str, limit: int = 10) -> List[Dict]:
        """Get recent training examples for a specific action (for few-shot prompting)"""
        examples = []
        
        if not self.training_file.exists():
            return examples
        
        with open(self.training_file, 'r') as f:
            for line in f:
                try:
                    ex = json.loads(line.strip())
                    if ex.get('action_id') == action_id and ex.get('quality') in ['high', 'medium']:
                        examples.append(ex)
                except Exception:
                    continue
        
        # Return most recent, highest quality first
        examples.sort(key=lambda x: (x.get('user_approved', False), x.get('quality') == 'high', x.get('timestamp', '')), reverse=True)
        return examples[:limit]
    
    def get_stats(self) -> Dict:
        """Get collection statistics"""
        return {
            **self.stats,
            'training_file_size_mb': self.training_file.stat().st_size / 1024 / 1024 if self.training_file.exists() else 0
        }
    
    def export_for_finetuning(self, min_quality: str = 'medium', output_path: str = None) -> str:
        """
        Export training data in format suitable for fine-tuning.
        
        Returns path to exported file in Alpaca/ShareGPT format.
        """
        output_path = output_path or str(TRAINING_DIR / "finetune_data.json")
        
        quality_levels = {'high': 2, 'medium': 1, 'low': 0}
        min_level = quality_levels.get(min_quality, 1)
        
        finetune_data = []
        
        if self.training_file.exists():
            with open(self.training_file, 'r') as f:
                for line in f:
                    try:
                        ex = json.loads(line.strip())
                        if quality_levels.get(ex.get('quality'), 0) >= min_level:
                            # Convert to Alpaca format
                            finetune_data.append({
                                'instruction': f"Analyze this document for Year-End action {ex.get('action_id')}",
                                'input': ex.get('input_sample', ''),
                                'output': json.dumps(ex.get('output', {}))
                            })
                    except Exception:
                        continue
        
        with open(output_path, 'w') as f:
            json.dump(finetune_data, f, indent=2)
        
        logger.info(f"[LEARNING] Exported {len(finetune_data)} examples to {output_path}")
        return output_path


# =============================================================================
# 2. FEEDBACK LOOP
# =============================================================================

class FeedbackLoop:
    """
    Learns from user corrections to improve future analyses.
    
    When user:
    - Changes status from AI suggestion
    - Edits findings
    - Marks issues as false positives
    - Adds missing issues
    
    We capture this as feedback and use it to:
    1. Improve prompts
    2. Train local models
    3. Generate rules
    """
    
    def __init__(self):
        self.feedback_file = FEEDBACK_DIR / "corrections.jsonl"
        self.patterns_file = FEEDBACK_DIR / "learned_patterns.json"
        self.playbook_feedback_file = FEEDBACK_DIR / "playbook_feedback.jsonl"
        self._load_patterns()
    
    def _load_patterns(self):
        """Load learned patterns from feedback"""
        if self.patterns_file.exists():
            with open(self.patterns_file, 'r') as f:
                self.patterns = json.load(f)
        else:
            self.patterns = {
                'false_positives': [],  # Issues AI flagged that weren't real
                'missed_issues': [],     # Issues AI should have caught
                'status_corrections': {},  # AI said X, user changed to Y
                'learned_rules': [],      # Auto-generated rules
                'discarded_findings': [],  # Findings user discarded (for suppression)
                'kept_findings': []        # Findings user explicitly kept (positive signal)
            }
    
    def _save_patterns(self):
        with open(self.patterns_file, 'w') as f:
            json.dump(self.patterns, f, indent=2)
    
    def record_correction(self,
                         action_id: str,
                         correction_type: str,  # 'status', 'issue_removed', 'issue_added', 'finding_edited'
                         original_value: Any,
                         corrected_value: Any,
                         context: str = None):
        """
        Record a user correction for learning.
        """
        feedback = {
            'id': hashlib.md5(f"{action_id}{datetime.now().isoformat()}".encode()).hexdigest()[:12],
            'timestamp': datetime.now().isoformat(),
            'action_id': action_id,
            'correction_type': correction_type,
            'original': original_value,
            'corrected': corrected_value,
            'context': context[:500] if context else None
        }
        
        # Append to feedback file
        with open(self.feedback_file, 'a') as f:
            f.write(json.dumps(feedback) + '\n')
        
        # Update patterns
        if correction_type == 'issue_removed':
            # AI flagged something that wasn't an issue
            self.patterns['false_positives'].append({
                'issue': original_value,
                'action_id': action_id,
                'timestamp': feedback['timestamp']
            })
        elif correction_type == 'issue_added':
            # AI missed an issue
            self.patterns['missed_issues'].append({
                'issue': corrected_value,
                'action_id': action_id,
                'timestamp': feedback['timestamp']
            })
        elif correction_type == 'status':
            key = f"{original_value}_to_{corrected_value}"
            self.patterns['status_corrections'][key] = self.patterns['status_corrections'].get(key, 0) + 1
        
        self._save_patterns()
        self._maybe_generate_rules()
        
        logger.info(f"[LEARNING] Recorded correction for {action_id}: {correction_type}")
    
    def record_playbook_feedback(
        self,
        project_id: str,
        context: str,  # format: "playbook_id:action_id"
        finding: str,
        feedback: str,  # 'keep', 'discard', 'modify'
        reason: Optional[str] = None
    ):
        """
        Record feedback from playbook UI (keep/discard decisions).
        
        This is the method called by LearningHook.record_feedback().
        """
        playbook_id = context.split(':')[0] if ':' in context else 'unknown'
        action_id = context.split(':')[1] if ':' in context else context
        
        feedback_record = {
            'id': hashlib.md5(f"{finding}{datetime.now().isoformat()}".encode()).hexdigest()[:12],
            'timestamp': datetime.now().isoformat(),
            'project_id': project_id,
            'playbook_id': playbook_id,
            'action_id': action_id,
            'finding': finding,
            'feedback': feedback,
            'reason': reason
        }
        
        # Append to playbook feedback file
        with open(self.playbook_feedback_file, 'a') as f:
            f.write(json.dumps(feedback_record) + '\n')
        
        # Update patterns based on feedback type
        if feedback == 'discard':
            # User discarded this finding - add to suppression list
            # Normalize for pattern matching
            normalized = self._normalize_finding(finding)
            self.patterns['discarded_findings'].append({
                'finding': finding,
                'normalized': normalized,
                'playbook_id': playbook_id,
                'action_id': action_id,
                'reason': reason,
                'timestamp': feedback_record['timestamp']
            })
            # Also record as false positive for rule generation
            self.patterns['false_positives'].append({
                'issue': finding,
                'action_id': action_id,
                'timestamp': feedback_record['timestamp']
            })
            logger.info(f"[LEARNING] Recorded DISCARD for: {finding[:50]}...")
            
        elif feedback == 'keep':
            # User kept this finding - positive signal
            normalized = self._normalize_finding(finding)
            self.patterns['kept_findings'].append({
                'finding': finding,
                'normalized': normalized,
                'playbook_id': playbook_id,
                'action_id': action_id,
                'timestamp': feedback_record['timestamp']
            })
            logger.info(f"[LEARNING] Recorded KEEP for: {finding[:50]}...")
        
        self._save_patterns()
        self._maybe_generate_rules()
    
    def _normalize_finding(self, finding: str) -> str:
        """Normalize a finding for pattern matching."""
        # Replace numbers with placeholder
        normalized = re.sub(r'\d+', 'N', finding.lower())
        # Remove extra whitespace
        normalized = ' '.join(normalized.split())
        # Truncate for matching
        return normalized[:100]
    
    def _maybe_generate_rules(self):
        """
        Auto-generate rules from patterns.
        
        If we see the same correction 3+ times, create a rule.
        """
        # Check for repeated false positives
        fp_counts = {}
        for fp in self.patterns['false_positives']:
            issue = fp.get('issue', '')
            if isinstance(issue, str):
                # Normalize the issue text
                normalized = re.sub(r'\d+', 'N', issue.lower())[:100]
                fp_counts[normalized] = fp_counts.get(normalized, 0) + 1
        
        # Create rules for issues flagged 3+ times as false positives
        for issue_pattern, count in fp_counts.items():
            if count >= 3:
                rule = {
                    'type': 'suppress_issue',
                    'pattern': issue_pattern,
                    'reason': f'Flagged as false positive {count} times',
                    'created': datetime.now().isoformat()
                }
                if rule not in self.patterns['learned_rules']:
                    self.patterns['learned_rules'].append(rule)
                    logger.info(f"[LEARNING] Auto-generated rule: suppress '{issue_pattern}'")
        
        # Also generate suppressions from discarded findings
        discard_counts = {}
        for df in self.patterns.get('discarded_findings', []):
            normalized = df.get('normalized', '')
            if normalized:
                discard_counts[normalized] = discard_counts.get(normalized, 0) + 1
        
        for pattern, count in discard_counts.items():
            if count >= 2:  # Lower threshold for explicit discards
                rule = {
                    'type': 'suppress_issue',
                    'pattern': pattern,
                    'reason': f'Explicitly discarded {count} times',
                    'created': datetime.now().isoformat()
                }
                if rule not in self.patterns['learned_rules']:
                    self.patterns['learned_rules'].append(rule)
                    logger.info(f"[LEARNING] Auto-generated rule from discard: suppress '{pattern}'")
        
        self._save_patterns()
    
    def get_suppression_patterns(self) -> List[str]:
        """Get patterns of issues that should be suppressed"""
        return [r['pattern'] for r in self.patterns['learned_rules'] if r.get('type') == 'suppress_issue']
    
    def should_suppress_issue(self, issue: str) -> bool:
        """Check if an issue should be suppressed based on learned patterns"""
        normalized = re.sub(r'\d+', 'N', issue.lower())[:100]
        return normalized in self.get_suppression_patterns()
    
    def get_patterns_for_playbook(self, project_id: str, playbook_id: str) -> Dict[str, Any]:
        """
        Get learned patterns formatted for playbook suppression.
        
        Returns format expected by LearningHook.apply_learned_suppressions()
        """
        suppressions = self.get_suppression_patterns()
        
        # Also include recently discarded findings for this playbook
        recent_discards = [
            df['normalized'] for df in self.patterns.get('discarded_findings', [])
            if df.get('playbook_id') == playbook_id
        ]
        
        # Combine unique suppressions
        all_suppressions = list(set(suppressions + recent_discards))
        
        return {
            'suppressions': all_suppressions,
            'preferences': {
                'total_kept': len(self.patterns.get('kept_findings', [])),
                'total_discarded': len(self.patterns.get('discarded_findings', []))
            }
        }


# =============================================================================
# 3. RULES ENGINE
# =============================================================================

class RulesEngine:
    """
    Deterministic rules that don't need LLM.
    
    As we learn patterns, we convert them to rules:
    - FEIN format validation
    - Rate range checks
    - Required field presence
    - Known value lookups
    
    Rules are FAST and FREE - no API calls.
    """
    
    def __init__(self):
        self.rules_file = RULES_DIR / "validation_rules.json"
        self._load_rules()
    
    def _load_rules(self):
        """Load validation rules"""
        if self.rules_file.exists():
            with open(self.rules_file, 'r') as f:
                self.rules = json.load(f)
        else:
            # Default rules - these don't need LLM
            self.rules = {
                'fein_format': {
                    'pattern': r'^\d{2}-\d{7}$',
                    'error': 'FEIN must be format XX-XXXXXXX'
                },
                'sui_rate_range': {
                    'min': 0.0006,
                    'max': 0.12,
                    'error': 'SUI rate outside normal range (0.06% - 12%)'
                },
                'fica_rate_2024': {
                    'social_security': 0.062,
                    'medicare': 0.0145,
                    'ss_wage_base': 168600
                },
                'state_abbreviations': [
                    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
                    'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
                    'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
                    'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
                    'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC'
                ],
                'required_w2_fields': [
                    'employer_name', 'employer_address', 'employer_fein',
                    'employee_ssn', 'employee_name', 'employee_address',
                    'wages_tips_compensation', 'federal_tax_withheld'
                ]
            }
            self._save_rules()
    
    def _save_rules(self):
        with open(self.rules_file, 'w') as f:
            json.dump(self.rules, f, indent=2)
    
    def validate_fein(self, fein: str) -> Tuple[bool, Optional[str]]:
        """Validate FEIN format"""
        pattern = self.rules['fein_format']['pattern']
        if re.match(pattern, fein):
            return True, None
        return False, self.rules['fein_format']['error']
    
    def validate_sui_rate(self, rate: float) -> Tuple[bool, Optional[str]]:
        """Validate SUI rate is in normal range"""
        rule = self.rules['sui_rate_range']
        if rule['min'] <= rate <= rule['max']:
            return True, None
        return False, f"{rule['error']} (got {rate*100:.2f}%)"
    
    def validate_state(self, state: str) -> Tuple[bool, Optional[str]]:
        """Validate state abbreviation"""
        if state.upper() in self.rules['state_abbreviations']:
            return True, None
        return False, f"Invalid state abbreviation: {state}"
    
    def run_all_validations(self, data: Dict) -> List[Dict]:
        """
        Run all applicable validations on extracted data.
        Returns list of issues found.
        """
        issues = []
        
        # FEIN validation
        if 'fein' in data:
            valid, error = self.validate_fein(data['fein'])
            if not valid:
                issues.append({'field': 'fein', 'error': error, 'value': data['fein']})
        
        # SUI rate validation
        for key, value in data.items():
            if 'sui' in key.lower() and 'rate' in key.lower():
                try:
                    rate = float(str(value).replace('%', '')) / 100
                    valid, error = self.validate_sui_rate(rate)
                    if not valid:
                        issues.append({'field': key, 'error': error, 'value': value})
                except Exception:
                    pass
        
        # State validation
        if 'state' in data:
            valid, error = self.validate_state(data['state'])
            if not valid:
                issues.append({'field': 'state', 'error': error, 'value': data['state']})
        
        return issues
    
    def add_rule(self, rule_name: str, rule_config: Dict):
        """Add a new validation rule (learned from patterns)"""
        self.rules[rule_name] = rule_config
        self._save_rules()
        logger.info(f"[LEARNING] Added new rule: {rule_name}")


# =============================================================================
# 3B. TERM MAPPING ENGINE
# =============================================================================

# Term mapping storage paths
TERM_MAPPING_DIR = DATA_DIR / "term_mappings"
try:
    TERM_MAPPING_DIR.mkdir(parents=True, exist_ok=True)
except Exception as e:
    logger.warning(f"[LEARNING] Could not create term mapping dir: {e}")

# Universal patterns - learned across all vendors
UNIVERSAL_COLUMN_PATTERNS = {
    # Employment status
    'active_employee': {
        'column_patterns': ['employmentstatus', 'empstatus', 'status', 'employment_status', 'workerstatus'],
        'value_patterns': ['A', 'Active', 'ACT', '1', 'ACTIVE'],
        'mapping_type': 'filter_value',
        'display_term': 'active'
    },
    'terminated_employee': {
        'column_patterns': ['employmentstatus', 'empstatus', 'status', 'employment_status'],
        'value_patterns': ['T', 'Terminated', 'TERM', 'TRM', 'Inactive'],
        'mapping_type': 'filter_value',
        'display_term': 'terminated'
    },
    'leave_employee': {
        'column_patterns': ['employmentstatus', 'empstatus', 'status'],
        'value_patterns': ['L', 'Leave', 'LOA', 'OnLeave'],
        'mapping_type': 'filter_value',
        'display_term': 'on leave'
    },
    
    # Employment type
    'full_time': {
        'column_patterns': ['fulltimeorparttime', 'ftpt', 'employeetype', 'emptype', 'full_time_part_time'],
        'value_patterns': ['F', 'FT', 'Full', 'Full-Time', 'FullTime'],
        'mapping_type': 'filter_value',
        'display_term': 'full time'
    },
    'part_time': {
        'column_patterns': ['fulltimeorparttime', 'ftpt', 'employeetype', 'emptype'],
        'value_patterns': ['P', 'PT', 'Part', 'Part-Time', 'PartTime'],
        'mapping_type': 'filter_value',
        'display_term': 'part time'
    },
    
    # Dates
    'hire_date': {
        'column_patterns': ['hiredate', 'hire_date', 'dateofhire', 'startdate', 'employmentstartdate', 'originalhiredate'],
        'mapping_type': 'date_column',
        'display_term': 'hired'
    },
    'termination_date': {
        'column_patterns': ['terminationdate', 'termdate', 'enddate', 'separationdate', 'lastdayworked'],
        'mapping_type': 'date_column',
        'display_term': 'terminated'
    },
    'birth_date': {
        'column_patterns': ['birthdate', 'dateofbirth', 'dob'],
        'mapping_type': 'date_column',
        'display_term': 'born'
    },
    
    # Names
    'first_name': {
        'column_patterns': ['firstname', 'first_name', 'givenname', 'fname'],
        'mapping_type': 'display_column',
        'display_term': 'first name'
    },
    'last_name': {
        'column_patterns': ['lastname', 'last_name', 'surname', 'familyname', 'lname'],
        'mapping_type': 'display_column',
        'display_term': 'last name'
    },
    
    # Compensation
    'salary': {
        'column_patterns': ['annualsalary', 'annual_salary', 'salary', 'basesalary', 'basecompensation', 'yearlysalary'],
        'mapping_type': 'measure_column',
        'display_term': 'salary'
    },
    'hourly_rate': {
        'column_patterns': ['hourlypayrate', 'hourlyrate', 'payrate', 'hourly_rate'],
        'mapping_type': 'measure_column',
        'display_term': 'hourly rate'
    },
    
    # Location
    'state': {
        'column_patterns': ['addressstate', 'state', 'statecode', 'workstate', 'work_state'],
        'mapping_type': 'filter_column',
        'display_term': 'state'
    },
    'city': {
        'column_patterns': ['addresscity', 'city', 'workcity'],
        'mapping_type': 'filter_column',
        'display_term': 'city'
    },
    'country': {
        'column_patterns': ['addresscountry', 'country', 'countrycode', 'workcountry'],
        'mapping_type': 'filter_column',
        'display_term': 'country'
    }
}

# Lookup table patterns - tables that are code/description reference tables
UNIVERSAL_LOOKUP_PATTERNS = {
    'location': {
        'table_patterns': ['location', 'locations', 'work_location', 'worklocation'],
        'fk_patterns': ['locationcode', 'location_code', 'loccode', 'worklocationcode'],
        'display_term': 'location'
    },
    'job': {
        'table_patterns': ['job', 'jobs', 'position', 'positions', 'jobtitle'],
        'fk_patterns': ['jobcode', 'job_code', 'jobid', 'positioncode', 'jobtitlecode'],
        'display_term': 'job'
    },
    'department': {
        'table_patterns': ['department', 'departments', 'dept', 'org_level', 'orglevel'],
        'fk_patterns': ['departmentcode', 'deptcode', 'orglevel'],
        'display_term': 'department'
    },
    'company': {
        'table_patterns': ['company', 'companies', 'legal_entity', 'legalentity'],
        'fk_patterns': ['companycode', 'companyid', 'legalentitycode'],
        'display_term': 'company'
    },
    'pay_group': {
        'table_patterns': ['paygroup', 'pay_group', 'paygroups'],
        'fk_patterns': ['paygroupcode', 'pay_group_code', 'paygroup'],
        'display_term': 'pay group'
    }
}


class TermMappingEngine:
    """
    Discovers, stores, and manages term mappings for natural language queries.
    
    FLOW:
    1. discover_mappings() - Auto-discovers from schema → pending
    2. get_pending() - Review what was discovered
    3. approve() / reject() - Human decision
    4. Approved mappings → used by QueryEngine
    5. Patterns learned → used for future vendors
    
    CROSS-VENDOR LEARNING:
    - When you approve a mapping for UKG, we learn the pattern
    - When we see similar schema in Workday, we propose the same mapping
    - Confidence increases with each approval
    """
    
    def __init__(self):
        self.pending_file = TERM_MAPPING_DIR / "pending_mappings.json"
        self.approved_file = TERM_MAPPING_DIR / "approved_mappings.json"
        self.learned_file = TERM_MAPPING_DIR / "learned_patterns.json"
        self._load_data()
    
    def _load_data(self):
        """Load all term mapping data."""
        # Pending mappings awaiting review
        if self.pending_file.exists():
            with open(self.pending_file, 'r') as f:
                self.pending = json.load(f)
        else:
            self.pending = {}  # keyed by project_id
        
        # Approved mappings (used by QueryEngine)
        if self.approved_file.exists():
            with open(self.approved_file, 'r') as f:
                self.approved = json.load(f)
        else:
            self.approved = {}  # keyed by project_id
        
        # Learned patterns (cross-vendor)
        if self.learned_file.exists():
            with open(self.learned_file, 'r') as f:
                self.learned = json.load(f)
        else:
            self.learned = {
                'column_patterns': dict(UNIVERSAL_COLUMN_PATTERNS),
                'lookup_patterns': dict(UNIVERSAL_LOOKUP_PATTERNS),
                'vendor_mappings': {},  # vendor -> product -> concept -> mapping
                'approval_counts': {}   # concept -> count of approvals
            }
    
    def _save_pending(self):
        with open(self.pending_file, 'w') as f:
            json.dump(self.pending, f, indent=2)
    
    def _save_approved(self):
        with open(self.approved_file, 'w') as f:
            json.dump(self.approved, f, indent=2)
    
    def _save_learned(self):
        with open(self.learned_file, 'w') as f:
            json.dump(self.learned, f, indent=2)
    
    def discover_mappings(self, conn, project_id: str, vendor: str = None, product: str = None) -> List[Dict]:
        """
        Auto-discover potential term mappings from database schema.
        
        Returns list of discovered mappings (stored as pending).
        """
        logger.warning(f"[TERM-DISCOVERY] Starting discovery for {project_id}")
        
        discovered = []
        
        # Get all tables for this project
        tables = self._get_project_tables(conn, project_id)
        logger.warning(f"[TERM-DISCOVERY] Found {len(tables)} tables")
        
        # Phase 1: Find lookup tables (code + description pattern)
        lookup_tables = self._find_lookup_tables(conn, tables)
        logger.warning(f"[TERM-DISCOVERY] Found {len(lookup_tables)} potential lookup tables")
        
        # Phase 2: Find filter columns (status, type, etc.)
        filter_mappings = self._find_filter_columns(conn, tables, vendor, product)
        discovered.extend(filter_mappings)
        
        # Phase 3: Find date columns
        date_mappings = self._find_date_columns(tables)
        discovered.extend(date_mappings)
        
        # Phase 4: Find display columns (names)
        display_mappings = self._find_display_columns(tables)
        discovered.extend(display_mappings)
        
        # Phase 5: Find measure columns (salary, etc.)
        measure_mappings = self._find_measure_columns(tables)
        discovered.extend(measure_mappings)
        
        # Phase 6: Find lookup relationships
        lookup_mappings = self._find_lookup_relationships(conn, tables, lookup_tables)
        discovered.extend(lookup_mappings)
        
        # Store as pending
        self.pending[project_id] = {
            'vendor': vendor,
            'product': product,
            'discovered_at': datetime.now().isoformat(),
            'mappings': discovered
        }
        self._save_pending()
        
        logger.warning(f"[TERM-DISCOVERY] Complete: {len(discovered)} potential mappings found")
        return discovered
    
    def _get_project_tables(self, conn, project_id: str) -> List[Dict]:
        """Get all tables with their columns for this project."""
        tables = []
        
        try:
            all_tables = conn.execute("SHOW TABLES").fetchall()
        except:
            return tables
        
        for (table_name,) in all_tables:
            if project_id not in table_name:
                continue
            
            try:
                cols = conn.execute(f'DESCRIBE "{table_name}"').fetchall()
                columns = [{'name': c[0], 'type': c[1] if len(c) > 1 else 'VARCHAR'} for c in cols]
                
                count_result = conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()
                row_count = count_result[0] if count_result else 0
                
                tables.append({
                    'name': table_name,
                    'columns': columns,
                    'row_count': row_count
                })
            except Exception as e:
                logger.warning(f"[TERM-DISCOVERY] Could not describe {table_name}: {e}")
        
        return tables
    
    def _find_lookup_tables(self, conn, tables: List[Dict]) -> List[Dict]:
        """Find tables that look like lookup/reference tables."""
        lookup_tables = []
        
        for table in tables:
            col_names_lower = [c['name'].lower() for c in table['columns']]
            
            has_code = any(c in col_names_lower for c in ['code', 'id', 'key'])
            has_description = any(c in col_names_lower for c in ['description', 'name', 'desc', 'title'])
            is_small = table['row_count'] < 1000
            
            if has_code and has_description and is_small:
                code_col = next((c['name'] for c in table['columns'] 
                               if c['name'].lower() in ['code', 'id', 'key']), None)
                desc_col = next((c['name'] for c in table['columns'] 
                               if c['name'].lower() in ['description', 'name', 'desc', 'title']), None)
                
                if code_col and desc_col:
                    lookup_tables.append({
                        'table': table['name'],
                        'code_column': code_col,
                        'description_column': desc_col,
                        'row_count': table['row_count']
                    })
        
        return lookup_tables
    
    def _find_filter_columns(self, conn, tables: List[Dict], vendor: str, product: str) -> List[Dict]:
        """Find columns that can be used for filtering."""
        mappings = []
        patterns = self.learned['column_patterns']
        
        for table in tables:
            if table['row_count'] < 100:
                continue
            
            for col in table['columns']:
                col_lower = col['name'].lower()
                
                for concept, pattern in patterns.items():
                    if pattern.get('mapping_type') != 'filter_value':
                        continue
                    
                    for p in pattern.get('column_patterns', []):
                        if p in col_lower or col_lower == p:
                            # Get distinct values
                            try:
                                values = conn.execute(f'''
                                    SELECT DISTINCT "{col['name']}" 
                                    FROM "{table['name']}" 
                                    WHERE "{col['name']}" IS NOT NULL 
                                    LIMIT 20
                                ''').fetchall()
                                distinct_values = [str(v[0]) for v in values if v[0]]
                                
                                # Match against expected values
                                matching_value = None
                                for expected in pattern.get('value_patterns', []):
                                    if any(expected.lower() == v.lower() for v in distinct_values):
                                        matching_value = next(v for v in distinct_values 
                                                           if v.lower() == expected.lower())
                                        break
                                
                                if matching_value:
                                    # Check if we've seen this before (higher confidence)
                                    confidence = 0.7
                                    approval_count = self.learned['approval_counts'].get(concept, 0)
                                    if approval_count > 0:
                                        confidence = min(0.95, 0.7 + (approval_count * 0.05))
                                    
                                    mappings.append({
                                        'concept': concept,
                                        'display_term': pattern['display_term'],
                                        'mapping_type': 'filter_value',
                                        'source_table': table['name'],
                                        'source_column': col['name'],
                                        'filter_value': matching_value,
                                        'all_values': distinct_values[:10],
                                        'confidence': confidence
                                    })
                                    logger.warning(f"[TERM-DISCOVERY] Filter: '{pattern['display_term']}' -> {col['name']} = '{matching_value}'")
                            except Exception as e:
                                pass
                            break
        
        return mappings
    
    def _find_date_columns(self, tables: List[Dict]) -> List[Dict]:
        """Find date columns."""
        mappings = []
        patterns = self.learned['column_patterns']
        
        for table in tables:
            if table['row_count'] < 100:
                continue
            
            for col in table['columns']:
                col_lower = col['name'].lower()
                col_type = col['type'].upper()
                is_date_type = any(t in col_type for t in ['DATE', 'TIME', 'TIMESTAMP'])
                
                for concept, pattern in patterns.items():
                    if pattern.get('mapping_type') != 'date_column':
                        continue
                    
                    for p in pattern.get('column_patterns', []):
                        if p in col_lower or col_lower == p:
                            confidence = 0.9 if is_date_type else 0.6
                            mappings.append({
                                'concept': concept,
                                'display_term': pattern['display_term'],
                                'mapping_type': 'date_column',
                                'source_table': table['name'],
                                'source_column': col['name'],
                                'confidence': confidence
                            })
                            logger.warning(f"[TERM-DISCOVERY] Date: '{pattern['display_term']}' -> {col['name']}")
                            break
        
        return mappings
    
    def _find_display_columns(self, tables: List[Dict]) -> List[Dict]:
        """Find columns for displaying results (names)."""
        mappings = []
        patterns = self.learned['column_patterns']
        
        for table in tables:
            if table['row_count'] < 100:
                continue
            
            col_name_map = {c['name'].lower(): c['name'] for c in table['columns']}
            
            for concept, pattern in patterns.items():
                if pattern.get('mapping_type') != 'display_column':
                    continue
                
                for p in pattern.get('column_patterns', []):
                    if p in col_name_map:
                        mappings.append({
                            'concept': concept,
                            'display_term': pattern['display_term'],
                            'mapping_type': 'display_column',
                            'source_table': table['name'],
                            'source_column': col_name_map[p],
                            'confidence': 0.85
                        })
                        logger.warning(f"[TERM-DISCOVERY] Display: '{pattern['display_term']}' -> {col_name_map[p]}")
                        break
        
        return mappings
    
    def _find_measure_columns(self, tables: List[Dict]) -> List[Dict]:
        """Find numeric columns for aggregations."""
        mappings = []
        patterns = self.learned['column_patterns']
        
        for table in tables:
            if table['row_count'] < 100:
                continue
            
            for col in table['columns']:
                col_lower = col['name'].lower()
                col_type = col['type'].upper()
                is_numeric = any(t in col_type for t in ['INT', 'DECIMAL', 'NUMERIC', 'FLOAT', 'DOUBLE'])
                
                for concept, pattern in patterns.items():
                    if pattern.get('mapping_type') != 'measure_column':
                        continue
                    
                    for p in pattern.get('column_patterns', []):
                        if p in col_lower or col_lower == p:
                            confidence = 0.85 if is_numeric else 0.5
                            mappings.append({
                                'concept': concept,
                                'display_term': pattern['display_term'],
                                'mapping_type': 'measure_column',
                                'source_table': table['name'],
                                'source_column': col['name'],
                                'confidence': confidence
                            })
                            logger.warning(f"[TERM-DISCOVERY] Measure: '{pattern['display_term']}' -> {col['name']}")
                            break
        
        return mappings
    
    def _find_lookup_relationships(self, conn, tables: List[Dict], lookup_tables: List[Dict]) -> List[Dict]:
        """Find foreign key relationships to lookup tables."""
        mappings = []
        patterns = self.learned['lookup_patterns']
        
        for table in tables:
            if table['row_count'] < 100:
                continue
            
            for col in table['columns']:
                col_lower = col['name'].lower()
                
                for concept, pattern in patterns.items():
                    for fk_pattern in pattern.get('fk_patterns', []):
                        if fk_pattern in col_lower or col_lower in fk_pattern:
                            # Find matching lookup table
                            for lookup in lookup_tables:
                                lookup_name_lower = lookup['table'].lower()
                                for table_pattern in pattern.get('table_patterns', []):
                                    if table_pattern in lookup_name_lower:
                                        mappings.append({
                                            'concept': concept,
                                            'display_term': pattern['display_term'],
                                            'mapping_type': 'lookup',
                                            'source_table': table['name'],
                                            'source_column': col['name'],
                                            'lookup_table': lookup['table'],
                                            'lookup_key_column': lookup['code_column'],
                                            'lookup_display_column': lookup['description_column'],
                                            'confidence': 0.75
                                        })
                                        logger.warning(f"[TERM-DISCOVERY] Lookup: '{pattern['display_term']}' -> {col['name']} -> {lookup['table']}")
        
        return mappings
    
    def get_pending(self, project_id: str = None) -> Dict:
        """Get pending mappings for review."""
        if project_id:
            return self.pending.get(project_id, {'mappings': []})
        return self.pending
    
    def get_approved(self, project_id: str) -> List[Dict]:
        """Get approved mappings for a project (used by QueryEngine)."""
        return self.approved.get(project_id, [])
    
    def approve(self, project_id: str, mapping_index: int, approved_by: str = 'system') -> bool:
        """
        Approve a pending mapping.
        
        1. Move from pending to approved
        2. Learn the pattern for future vendors
        """
        if project_id not in self.pending:
            return False
        
        pending_data = self.pending[project_id]
        mappings = pending_data.get('mappings', [])
        
        if mapping_index >= len(mappings):
            return False
        
        mapping = mappings[mapping_index]
        mapping['approved_at'] = datetime.now().isoformat()
        mapping['approved_by'] = approved_by
        
        # Add to approved
        if project_id not in self.approved:
            self.approved[project_id] = []
        self.approved[project_id].append(mapping)
        
        # Learn from this approval
        self._learn_from_approval(mapping, pending_data.get('vendor'), pending_data.get('product'))
        
        # Remove from pending
        mappings.pop(mapping_index)
        
        self._save_pending()
        self._save_approved()
        
        logger.warning(f"[TERM-APPROVAL] Approved: {mapping.get('display_term')} for {project_id}")
        return True
    
    def approve_all(self, project_id: str, min_confidence: float = 0.8, approved_by: str = 'system') -> int:
        """Approve all pending mappings above confidence threshold."""
        if project_id not in self.pending:
            return 0
        
        approved_count = 0
        pending_data = self.pending[project_id]
        mappings = pending_data.get('mappings', [])
        
        # Work backwards to safely remove items
        for i in range(len(mappings) - 1, -1, -1):
            if mappings[i].get('confidence', 0) >= min_confidence:
                if self.approve(project_id, i, approved_by):
                    approved_count += 1
        
        return approved_count
    
    def reject(self, project_id: str, mapping_index: int, rejected_by: str = 'system') -> bool:
        """Reject a pending mapping."""
        if project_id not in self.pending:
            return False
        
        mappings = self.pending[project_id].get('mappings', [])
        if mapping_index >= len(mappings):
            return False
        
        mapping = mappings.pop(mapping_index)
        self._save_pending()
        
        logger.warning(f"[TERM-APPROVAL] Rejected: {mapping.get('display_term')} for {project_id}")
        return True
    
    def _learn_from_approval(self, mapping: Dict, vendor: str, product: str):
        """Learn from an approved mapping for cross-vendor reuse."""
        concept = mapping.get('concept')
        if not concept:
            return
        
        # Update approval count
        self.learned['approval_counts'][concept] = self.learned['approval_counts'].get(concept, 0) + 1
        
        # Add column pattern if new
        if concept in self.learned['column_patterns']:
            patterns = self.learned['column_patterns'][concept]
            new_col = mapping.get('source_column', '').lower()
            if new_col and new_col not in patterns.get('column_patterns', []):
                patterns['column_patterns'].append(new_col)
            
            new_val = mapping.get('filter_value')
            if new_val and new_val not in patterns.get('value_patterns', []):
                patterns.setdefault('value_patterns', []).append(new_val)
        
        # Store vendor-specific mapping
        if vendor and product:
            if vendor not in self.learned['vendor_mappings']:
                self.learned['vendor_mappings'][vendor] = {}
            if product not in self.learned['vendor_mappings'][vendor]:
                self.learned['vendor_mappings'][vendor][product] = {}
            
            self.learned['vendor_mappings'][vendor][product][concept] = {
                'source_column': mapping.get('source_column'),
                'filter_value': mapping.get('filter_value'),
                'lookup_table': mapping.get('lookup_table')
            }
        
        self._save_learned()
        logger.warning(f"[TERM-LEARNING] Learned pattern for '{concept}' (approval #{self.learned['approval_counts'][concept]})")
    
    def get_stats(self) -> Dict:
        """Get term mapping statistics."""
        total_pending = sum(len(p.get('mappings', [])) for p in self.pending.values())
        total_approved = sum(len(a) for a in self.approved.values())
        
        return {
            'pending_projects': len(self.pending),
            'pending_mappings': total_pending,
            'approved_projects': len(self.approved),
            'approved_mappings': total_approved,
            'learned_concepts': len(self.learned.get('approval_counts', {})),
            'vendor_mappings': len(self.learned.get('vendor_mappings', {}))
        }
    
    def sync_to_duckdb(self, conn, project_id: str) -> int:
        """
        Sync approved mappings to DuckDB _term_mappings table.
        
        This makes them available to QueryEngine.
        Returns count of mappings synced.
        """
        approved = self.get_approved(project_id)
        if not approved:
            return 0
        
        # Create table if not exists
        conn.execute("""
            CREATE TABLE IF NOT EXISTS _term_mappings (
                id INTEGER PRIMARY KEY,
                project VARCHAR,
                term VARCHAR,
                term_lower VARCHAR,
                source_table VARCHAR,
                employee_column VARCHAR,
                lookup_table VARCHAR,
                lookup_key_column VARCHAR,
                lookup_display_column VARCHAR,
                lookup_filter VARCHAR,
                mapping_type VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Clear existing for this project
        conn.execute("DELETE FROM _term_mappings WHERE project = ?", [project_id])
        
        synced = 0
        for mapping in approved:
            try:
                term = mapping.get('display_term', '')
                mapping_id = hash(f"{project_id}_{term}_{synced}") % 2147483647
                
                conn.execute("""
                    INSERT INTO _term_mappings 
                    (id, project, term, term_lower, source_table, employee_column,
                     lookup_table, lookup_key_column, lookup_display_column, lookup_filter, mapping_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    mapping_id,
                    project_id,
                    term,
                    term.lower(),
                    mapping.get('source_table'),
                    mapping.get('source_column'),
                    mapping.get('lookup_table'),
                    mapping.get('lookup_key_column'),
                    mapping.get('lookup_display_column'),
                    None,  # lookup_filter
                    mapping.get('mapping_type')
                ])
                synced += 1
            except Exception as e:
                logger.warning(f"[TERM-SYNC] Failed to sync mapping {term}: {e}")
        
        conn.execute("CHECKPOINT")
        logger.warning(f"[TERM-SYNC] Synced {synced} mappings to DuckDB for {project_id}")
        return synced


# =============================================================================
# 4. KNOWLEDGE CACHE
# =============================================================================

class KnowledgeCache:
    """
    Semantic cache of past analyses.
    
    When a similar document comes in:
    1. Check if we've analyzed something like this before
    2. If yes, use cached analysis (no LLM call!)
    3. If no, analyze and cache for future
    
    Uses document fingerprinting + semantic similarity.
    """
    
    def __init__(self):
        self.cache_file = CACHE_DIR / "analysis_cache.json"
        self._load_cache()
    
    def _load_cache(self):
        if self.cache_file.exists():
            with open(self.cache_file, 'r') as f:
                self.cache = json.load(f)
        else:
            self.cache = {}
    
    def _save_cache(self):
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2)
    
    def _fingerprint(self, text: str, action_id: str) -> str:
        """
        Create a fingerprint for cache lookup.
        
        Combines:
        - Action ID
        - Key patterns found (FEIN, rates, etc.)
        - Document structure (not full content)
        """
        # Extract key values for fingerprint
        feins = re.findall(r'\d{2}-\d{7}', text)
        rates = re.findall(r'\d{1,2}\.\d{2,4}\s*%', text)
        states = re.findall(r'\b[A-Z]{2}\b', text)
        
        # Create deterministic fingerprint
        fp_parts = [
            action_id,
            ','.join(sorted(set(feins))[:3]),
            ','.join(sorted(set(rates))[:5]),
            ','.join(sorted(set(states))[:5]),
            str(len(text) // 1000)  # Rough length bucket
        ]
        
        return hashlib.md5('|'.join(fp_parts).encode()).hexdigest()[:16]
    
    def get(self, text: str, action_id: str) -> Optional[Dict]:
        """Get cached analysis if available"""
        fp = self._fingerprint(text, action_id)
        
        if fp in self.cache:
            cached = self.cache[fp]
            # Check age - invalidate after 30 days
            cached_time = datetime.fromisoformat(cached.get('cached_at', '2000-01-01'))
            age_days = (datetime.now() - cached_time).days
            
            if age_days < 30:
                logger.info(f"[CACHE] Hit for {action_id} (age={age_days}d)")
                return cached.get('analysis')
            else:
                logger.info(f"[CACHE] Expired for {action_id} (age={age_days}d)")
        
        return None
    
    def set(self, text: str, action_id: str, analysis: Dict):
        """Cache an analysis result"""
        fp = self._fingerprint(text, action_id)
        
        self.cache[fp] = {
            'action_id': action_id,
            'analysis': analysis,
            'cached_at': datetime.now().isoformat(),
            'text_sample': text[:200]
        }
        
        self._save_cache()
        logger.info(f"[CACHE] Stored analysis for {action_id}")
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        return {
            'total_cached': len(self.cache),
            'cache_size_kb': self.cache_file.stat().st_size / 1024 if self.cache_file.exists() else 0
        }


# =============================================================================
# 5. INTEGRATED LEARNING SYSTEM
# =============================================================================

class LearningSystem:
    """
    Integrates all learning components.
    
    Usage:
        learning = LearningSystem()
        
        # Before analysis
        cached = learning.get_cached_analysis(text, action_id)
        if cached:
            return cached  # No LLM call needed!
        
        # After Claude analysis
        learning.learn_from_claude(text, prompt, output, action_id)
        
        # When user corrects (old signature)
        learning.record_feedback(action_id, 'status', 'complete', 'in_progress')
        
        # When user keeps/discards in playbook (new signature via LearningHook)
        learning.record_feedback(
            project_id='xxx', 
            context='year-end:2A',
            finding='Some finding text',
            feedback='discard',
            reason='Not applicable'
        )
        
        # Get stats
        stats = learning.get_stats()
    """
    
    def __init__(self):
        self.collector = TrainingDataCollector()
        self.feedback = FeedbackLoop()
        self.rules = RulesEngine()
        self.cache = KnowledgeCache()
        self.term_mappings = TermMappingEngine()
    
    def get_cached_analysis(self, text: str, action_id: str) -> Optional[Dict]:
        """Check if we have a cached analysis"""
        return self.cache.get(text, action_id)
    
    def learn_from_claude(self, 
                         input_text: str, 
                         prompt: str, 
                         output: Dict, 
                         action_id: str,
                         quality: str = 'medium'):
        """Learn from a Claude response"""
        # Collect for fine-tuning
        self.collector.collect(input_text, prompt, output, action_id, quality)
        
        # Cache for future
        self.cache.set(input_text, action_id, output)
    
    def record_feedback(self, *args, **kwargs):
        """
        Record user feedback - supports BOTH signatures:
        
        OLD (direct call):
            record_feedback(action_id, correction_type, original, corrected, context=None)
        
        NEW (from LearningHook):
            record_feedback(project_id=, context=, finding=, feedback=, reason=)
        """
        # Detect which signature is being used
        if kwargs.get('project_id') is not None or kwargs.get('finding') is not None:
            # NEW signature from LearningHook
            self.feedback.record_playbook_feedback(
                project_id=kwargs.get('project_id', ''),
                context=kwargs.get('context', ''),
                finding=kwargs.get('finding', ''),
                feedback=kwargs.get('feedback', 'keep'),
                reason=kwargs.get('reason')
            )
        elif len(args) >= 4:
            # OLD signature: action_id, correction_type, original, corrected, context
            self.feedback.record_correction(
                action_id=args[0],
                correction_type=args[1],
                original_value=args[2],
                corrected_value=args[3],
                context=args[4] if len(args) > 4 else kwargs.get('context')
            )
        else:
            logger.warning(f"[LEARNING] Invalid record_feedback call: args={args}, kwargs={kwargs}")
    
    def get_patterns(self, project_id: str, playbook_id: str) -> Dict[str, Any]:
        """
        Get learned patterns for playbook suppression.
        
        This is called by LearningHook.get_learned_patterns().
        
        Returns:
            {
                'suppressions': ['pattern1', 'pattern2', ...],
                'preferences': {...}
            }
        """
        return self.feedback.get_patterns_for_playbook(project_id, playbook_id)
    
    def validate_extraction(self, extracted_data: Dict) -> List[Dict]:
        """Run rule-based validation (no LLM)"""
        return self.rules.run_all_validations(extracted_data)
    
    def should_suppress_issue(self, issue: str) -> bool:
        """Check if issue should be suppressed based on learned patterns"""
        return self.feedback.should_suppress_issue(issue)
    
    def get_few_shot_examples(self, action_id: str, limit: int = 3) -> List[Dict]:
        """Get examples for few-shot prompting"""
        return self.collector.get_examples_for_action(action_id, limit)
    
    def get_examples_for_action(self, action_id: str, limit: int = 3) -> List[Dict]:
        """Get examples for an action (alias for get_few_shot_examples)"""
        return self.collector.get_examples_for_action(action_id, limit)
    
    # =========================================================================
    # TERM MAPPING METHODS
    # =========================================================================
    
    def discover_term_mappings(self, conn, project_id: str, vendor: str = None, product: str = None) -> List[Dict]:
        """
        Auto-discover term mappings from schema.
        Returns list of pending mappings for review.
        """
        return self.term_mappings.discover_mappings(conn, project_id, vendor, product)
    
    def get_pending_term_mappings(self, project_id: str = None) -> Dict:
        """Get pending term mappings for review."""
        return self.term_mappings.get_pending(project_id)
    
    def get_approved_term_mappings(self, project_id: str) -> List[Dict]:
        """Get approved term mappings (used by QueryEngine)."""
        return self.term_mappings.get_approved(project_id)
    
    def approve_term_mapping(self, project_id: str, mapping_index: int, approved_by: str = 'system') -> bool:
        """Approve a specific pending term mapping."""
        return self.term_mappings.approve(project_id, mapping_index, approved_by)
    
    def approve_all_term_mappings(self, project_id: str, min_confidence: float = 0.8, approved_by: str = 'system') -> int:
        """Approve all term mappings above confidence threshold."""
        return self.term_mappings.approve_all(project_id, min_confidence, approved_by)
    
    def reject_term_mapping(self, project_id: str, mapping_index: int, rejected_by: str = 'system') -> bool:
        """Reject a pending term mapping."""
        return self.term_mappings.reject(project_id, mapping_index, rejected_by)
    
    def sync_term_mappings_to_duckdb(self, conn, project_id: str) -> int:
        """Sync approved term mappings to DuckDB for QueryEngine to use."""
        return self.term_mappings.sync_to_duckdb(conn, project_id)
    
    def get_stats(self) -> Dict:
        """Get comprehensive learning statistics"""
        return {
            'training_data': self.collector.get_stats(),
            'cache': self.cache.get_stats(),
            'feedback_patterns': {
                'false_positives': len(self.feedback.patterns.get('false_positives', [])),
                'missed_issues': len(self.feedback.patterns.get('missed_issues', [])),
                'learned_rules': len(self.feedback.patterns.get('learned_rules', [])),
                'discarded_findings': len(self.feedback.patterns.get('discarded_findings', [])),
                'kept_findings': len(self.feedback.patterns.get('kept_findings', []))
            },
            'term_mappings': self.term_mappings.get_stats()
        }
    
    def export_for_finetuning(self) -> str:
        """Export data for fine-tuning local model"""
        return self.collector.export_for_finetuning(min_quality='medium')


# =============================================================================
# SINGLETON
# =============================================================================

_learning_system: Optional[LearningSystem] = None

def get_learning_system() -> LearningSystem:
    """Get or create singleton learning system"""
    global _learning_system
    if _learning_system is None:
        _learning_system = LearningSystem()
    return _learning_system
