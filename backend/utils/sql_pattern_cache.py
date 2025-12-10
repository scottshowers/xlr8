"""
XLR8 SQL Pattern Cache
======================

PURPOSE:
Stop regenerating SQL for every query. Learn from successes.

HOW IT WORKS:
1. User asks "how many PT employees make over $35/hr"
2. Check pattern cache - no match
3. Generate SQL via LLM (expensive, unreliable)
4. SQL executes successfully
5. Extract pattern: COUNT + employee_type=PT + rate>threshold
6. Cache: pattern → working SQL template

NEXT TIME:
1. User asks "how many FT employees make over $50/hr"
2. Check pattern cache - MATCH!
3. Substitute: PT→FT, 35→50
4. Execute directly - NO LLM CALL

PATTERNS WE LEARN:
- COUNT queries with filters
- LIST queries with conditions
- Aggregations (SUM, AVG)
- Multi-table joins that work

Deploy to: backend/utils/sql_pattern_cache.py
"""

import os
import re
import json
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# Storage
DATA_DIR = Path(os.getenv("XLR8_DATA_DIR", "/data"))
try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
except PermissionError:
    DATA_DIR = Path("./data")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

SQL_CACHE_DIR = DATA_DIR / "sql_patterns"
SQL_CACHE_DIR.mkdir(parents=True, exist_ok=True)


class SQLPatternCache:
    """
    Learns and reuses successful SQL query patterns.
    
    A 'pattern' is:
    - Query intent (count, list, sum, avg)
    - Entities involved (employees, earnings, deductions)
    - Filter types (status, rate threshold, date range)
    - Tables/joins needed
    
    The cache stores:
    - Pattern signature → SQL template
    - Parameter positions for substitution
    - Success count (patterns that work more get prioritized)
    """
    
    def __init__(self, project: str = None):
        self.project = project
        self.cache_file = SQL_CACHE_DIR / f"patterns_{project or 'global'}.json"
        self._load_cache()
        
        # Common query patterns we can detect
        self.intent_patterns = {
            'count_employees': r'how many|count|number of.*(employee|worker|people|staff)',
            'count_pt': r'(how many|count).*(pt|part.?time)',
            'count_ft': r'(how many|count).*(ft|full.?time)',
            'list_employees': r'(list|show|display|get).*(employee|worker|people)',
            'rate_threshold': r'(more than|over|above|greater|exceed|>)\s*\$?\s*(\d+)',
            'sum_earnings': r'(total|sum).*(earning|pay|wage)',
            'avg_rate': r'(average|avg|mean).*(rate|pay|salary)',
        }
    
    def _load_cache(self):
        """Load cached patterns"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    self.patterns = json.load(f)
            except:
                self.patterns = {}
        else:
            self.patterns = {}
    
    def _save_cache(self):
        """Save patterns to disk"""
        with open(self.cache_file, 'w') as f:
            json.dump(self.patterns, f, indent=2)
    
    def _extract_pattern_signature(self, question: str) -> Dict[str, Any]:
        """
        Extract a pattern signature from a natural language question.
        
        Returns dict with:
        - intent: count, list, sum, avg
        - entities: employees, earnings, deductions
        - filters: pt/ft, rate_threshold, etc.
        - params: extracted values (threshold amounts, etc.)
        """
        q_lower = question.lower()
        
        signature = {
            'intent': 'unknown',
            'entities': [],
            'filters': [],
            'params': {}
        }
        
        # Detect intent
        if re.search(r'how many|count|number of', q_lower):
            signature['intent'] = 'count'
        elif re.search(r'list|show|display|get all', q_lower):
            signature['intent'] = 'list'
        elif re.search(r'total|sum of', q_lower):
            signature['intent'] = 'sum'
        elif re.search(r'average|avg|mean', q_lower):
            signature['intent'] = 'avg'
        
        # Detect entities
        if re.search(r'employee|worker|staff|people|person', q_lower):
            signature['entities'].append('employees')
        if re.search(r'earning|pay(?!roll)|wage|compensation', q_lower):
            signature['entities'].append('earnings')
        if re.search(r'deduction|benefit|401k|insurance', q_lower):
            signature['entities'].append('deductions')
        if re.search(r'tax|withhold|federal|state', q_lower):
            signature['entities'].append('taxes')
        
        # Detect filters
        if re.search(r'\bpt\b|part.?time', q_lower):
            signature['filters'].append('pt_status')
            signature['params']['employment_type'] = 'PT'
        if re.search(r'\bft\b|full.?time', q_lower):
            signature['filters'].append('ft_status')
            signature['params']['employment_type'] = 'FT'
        if re.search(r'active', q_lower):
            signature['filters'].append('active_status')
        if re.search(r'terminated|termed|inactive', q_lower):
            signature['filters'].append('terminated_status')
        
        # Extract rate threshold
        rate_match = re.search(r'(?:more than|over|above|greater than|>|exceed)\s*\$?\s*(\d+(?:\.\d+)?)', q_lower)
        if rate_match:
            signature['filters'].append('rate_gt')
            signature['params']['rate_threshold'] = float(rate_match.group(1))
        
        rate_lt_match = re.search(r'(?:less than|under|below|<)\s*\$?\s*(\d+(?:\.\d+)?)', q_lower)
        if rate_lt_match:
            signature['filters'].append('rate_lt')
            signature['params']['rate_threshold'] = float(rate_lt_match.group(1))
        
        # Create hash for lookup
        sig_key = f"{signature['intent']}|{','.join(sorted(signature['entities']))}|{','.join(sorted(signature['filters']))}"
        signature['key'] = hashlib.md5(sig_key.encode()).hexdigest()[:12]
        
        return signature
    
    def find_matching_pattern(self, question: str) -> Optional[Dict]:
        """
        Find a cached SQL pattern that matches this question.
        
        Returns:
        {
            'sql_template': 'SELECT COUNT(*) FROM ... WHERE {employment_type}...',
            'params': {'rate_threshold': 35.0, 'employment_type': 'PT'},
            'confidence': 0.95,
            'success_count': 12
        }
        """
        signature = self._extract_pattern_signature(question)
        pattern_key = signature['key']
        
        if pattern_key in self.patterns:
            cached = self.patterns[pattern_key]
            
            # Build SQL from template with current params
            sql = cached['sql_template']
            
            # Substitute parameters
            for param, value in signature['params'].items():
                placeholder = f'{{{param}}}'
                if placeholder in sql:
                    if isinstance(value, str):
                        sql = sql.replace(placeholder, f"'{value}'")
                    else:
                        sql = sql.replace(placeholder, str(value))
            
            logger.info(f"[SQL-CACHE] Pattern hit! Key={pattern_key}, successes={cached.get('success_count', 0)}")
            
            return {
                'sql': sql,
                'pattern_key': pattern_key,
                'confidence': cached.get('confidence', 0.9),
                'success_count': cached.get('success_count', 0),
                'source': 'pattern_cache'
            }
        
        logger.info(f"[SQL-CACHE] No pattern match for key={pattern_key}")
        return None
    
    def learn_pattern(self, question: str, sql: str, success: bool = True):
        """
        Learn from a successful SQL execution.
        
        Extracts pattern from question, templatizes SQL, stores for reuse.
        """
        if not success:
            return
        
        signature = self._extract_pattern_signature(question)
        pattern_key = signature['key']
        
        # Templatize the SQL - replace specific values with placeholders
        sql_template = sql
        
        # Replace rate thresholds with placeholder
        if 'rate_threshold' in signature['params']:
            threshold = signature['params']['rate_threshold']
            # Handle various formats: 35, 35.0, 35.00
            sql_template = re.sub(
                rf'(?<=[<>=])\s*{int(threshold)}(?:\.0+)?(?!\d)',
                ' {rate_threshold}',
                sql_template
            )
            sql_template = re.sub(
                rf'(?<=[<>=])\s*{threshold}(?!\d)',
                ' {rate_threshold}',
                sql_template
            )
        
        # Replace PT/FT with placeholder
        if 'employment_type' in signature['params']:
            emp_type = signature['params']['employment_type']
            sql_template = re.sub(
                rf"'{emp_type}'",
                "'{employment_type}'",
                sql_template,
                flags=re.IGNORECASE
            )
            sql_template = re.sub(
                rf'%{emp_type.lower()}%',
                '%{employment_type}%',
                sql_template,
                flags=re.IGNORECASE
            )
        
        # Update or create pattern
        if pattern_key in self.patterns:
            self.patterns[pattern_key]['success_count'] += 1
            self.patterns[pattern_key]['last_used'] = datetime.now().isoformat()
            # If this SQL is different but works, might be better
            if len(sql_template) < len(self.patterns[pattern_key]['sql_template']):
                self.patterns[pattern_key]['sql_template'] = sql_template
        else:
            self.patterns[pattern_key] = {
                'sql_template': sql_template,
                'signature': signature,
                'success_count': 1,
                'created': datetime.now().isoformat(),
                'last_used': datetime.now().isoformat(),
                'confidence': 0.85,  # Starts lower, increases with successes
                'example_question': question
            }
        
        # Increase confidence with more successes
        if self.patterns[pattern_key]['success_count'] > 5:
            self.patterns[pattern_key]['confidence'] = 0.95
        elif self.patterns[pattern_key]['success_count'] > 2:
            self.patterns[pattern_key]['confidence'] = 0.90
        
        self._save_cache()
        logger.info(f"[SQL-CACHE] Learned pattern {pattern_key}, total successes: {self.patterns[pattern_key]['success_count']}")
    
    def record_failure(self, question: str):
        """Record a pattern failure (reduce confidence or remove)"""
        signature = self._extract_pattern_signature(question)
        pattern_key = signature['key']
        
        if pattern_key in self.patterns:
            self.patterns[pattern_key]['confidence'] *= 0.8  # Reduce confidence
            self.patterns[pattern_key]['failure_count'] = self.patterns[pattern_key].get('failure_count', 0) + 1
            
            # If too many failures, remove pattern
            if self.patterns[pattern_key]['confidence'] < 0.5:
                del self.patterns[pattern_key]
                logger.warning(f"[SQL-CACHE] Removed unreliable pattern {pattern_key}")
            
            self._save_cache()
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        return {
            'total_patterns': len(self.patterns),
            'total_successes': sum(p.get('success_count', 0) for p in self.patterns.values()),
            'high_confidence': sum(1 for p in self.patterns.values() if p.get('confidence', 0) > 0.9),
            'patterns': [
                {
                    'key': k,
                    'intent': v.get('signature', {}).get('intent'),
                    'success_count': v.get('success_count', 0),
                    'confidence': v.get('confidence', 0),
                    'example': v.get('example_question', '')[:50]
                }
                for k, v in self.patterns.items()
            ]
        }


# =============================================================================
# PRE-BUILT PATTERNS (Bootstrap)
# =============================================================================

def get_bootstrap_patterns(project: str, schema: Dict) -> Dict[str, Dict]:
    """
    Generate bootstrap SQL patterns based on actual schema.
    
    These are KNOWN GOOD patterns that we seed the cache with.
    No LLM needed - these are crafted SQL templates.
    """
    patterns = {}
    
    # Find key tables
    tables = schema.get('tables', [])
    company_table = None
    personal_table = None
    earnings_table = None
    
    for t in tables:
        name = t.get('table_name', '').lower()
        if 'company' in name and 'master' not in name and 'tax' not in name:
            company_table = t.get('table_name')
        if 'personal' in name:
            personal_table = t.get('table_name')
        if 'earning' in name:
            earnings_table = t.get('table_name')
    
    if not company_table or not personal_table:
        return patterns
    
    # Find key columns
    company_cols = [str(c).lower() for c in tables[[t.get('table_name') for t in tables].index(company_table)].get('columns', [])]
    personal_cols = [str(c).lower() for c in tables[[t.get('table_name') for t in tables].index(personal_table)].get('columns', [])]
    
    rate_col = next((c for c in company_cols if 'hourly' in c and 'rate' in c), 'hourly_pay_rate')
    ptft_col = next((c for c in personal_cols if 'fullpart' in c or 'part_time' in c), 'fullpart_time_code')
    emp_num_col = 'employee_number'
    
    # Pattern 1: Count PT employees with rate threshold
    patterns['count_pt_rate'] = {
        'sql_template': f'''SELECT COUNT(*) as count
FROM "{company_table}" c
JOIN "{personal_table}" p ON c."{emp_num_col}" = p."{emp_num_col}"
WHERE TRY_CAST(c."{rate_col}" AS FLOAT) > {{rate_threshold}}
AND p."{ptft_col}" ILIKE '%{{employment_type}}%' ''',
        'signature': {
            'intent': 'count',
            'entities': ['employees'],
            'filters': ['pt_status', 'rate_gt'],
            'key': 'count_pt_rate'
        },
        'success_count': 10,  # Bootstrap with high confidence
        'confidence': 0.95,
        'created': datetime.now().isoformat(),
        'example_question': 'How many PT employees make over $35/hr?'
    }
    
    # Pattern 2: Count FT employees with rate threshold
    patterns['count_ft_rate'] = {
        'sql_template': f'''SELECT COUNT(*) as count
FROM "{company_table}" c
JOIN "{personal_table}" p ON c."{emp_num_col}" = p."{emp_num_col}"
WHERE TRY_CAST(c."{rate_col}" AS FLOAT) > {{rate_threshold}}
AND p."{ptft_col}" ILIKE '%{{employment_type}}%' ''',
        'signature': {
            'intent': 'count',
            'entities': ['employees'],
            'filters': ['ft_status', 'rate_gt'],
            'key': 'count_ft_rate'
        },
        'success_count': 10,
        'confidence': 0.95,
        'created': datetime.now().isoformat(),
        'example_question': 'How many FT employees make over $50/hr?'
    }
    
    # Pattern 3: Count all employees
    patterns['count_all_emp'] = {
        'sql_template': f'''SELECT COUNT(*) as count
FROM "{personal_table}"''',
        'signature': {
            'intent': 'count',
            'entities': ['employees'],
            'filters': [],
            'key': 'count_all_emp'
        },
        'success_count': 10,
        'confidence': 0.98,
        'created': datetime.now().isoformat(),
        'example_question': 'How many employees are there?'
    }
    
    # Pattern 4: Count PT employees
    patterns['count_pt_emp'] = {
        'sql_template': f'''SELECT COUNT(*) as count
FROM "{personal_table}"
WHERE "{ptft_col}" ILIKE '%PT%' ''',
        'signature': {
            'intent': 'count',
            'entities': ['employees'],
            'filters': ['pt_status'],
            'key': 'count_pt_emp'
        },
        'success_count': 10,
        'confidence': 0.95,
        'created': datetime.now().isoformat(),
        'example_question': 'How many part-time employees?'
    }
    
    # Pattern 5: List employees with high rate
    patterns['list_high_rate'] = {
        'sql_template': f'''SELECT p."{emp_num_col}", c."{rate_col}"
FROM "{company_table}" c
JOIN "{personal_table}" p ON c."{emp_num_col}" = p."{emp_num_col}"
WHERE TRY_CAST(c."{rate_col}" AS FLOAT) > {{rate_threshold}}
LIMIT 100''',
        'signature': {
            'intent': 'list',
            'entities': ['employees'],
            'filters': ['rate_gt'],
            'key': 'list_high_rate'
        },
        'success_count': 5,
        'confidence': 0.90,
        'created': datetime.now().isoformat(),
        'example_question': 'List employees making over $40/hr'
    }
    
    return patterns


# =============================================================================
# SINGLETON & INITIALIZATION
# =============================================================================

_pattern_caches: Dict[str, SQLPatternCache] = {}

def get_sql_pattern_cache(project: str) -> SQLPatternCache:
    """Get or create pattern cache for project"""
    if project not in _pattern_caches:
        _pattern_caches[project] = SQLPatternCache(project)
    return _pattern_caches[project]


def initialize_patterns(project: str, schema: Dict):
    """
    Initialize pattern cache with bootstrap patterns.
    
    Call this when a project is first loaded with its schema.
    """
    cache = get_sql_pattern_cache(project)
    
    # Only bootstrap if cache is empty
    if len(cache.patterns) == 0:
        bootstrap = get_bootstrap_patterns(project, schema)
        cache.patterns.update(bootstrap)
        cache._save_cache()
        logger.info(f"[SQL-CACHE] Bootstrapped {len(bootstrap)} patterns for {project}")
    
    return cache
