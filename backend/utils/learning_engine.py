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
            }
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
