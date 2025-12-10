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
        
        logger.warning(f"[SQL-CACHE] Looking for pattern key: {pattern_key} (intent={signature['intent']}, filters={signature['filters']})")
        logger.warning(f"[SQL-CACHE] Available keys: {list(self.patterns.keys())}")
        
        if pattern_key in self.patterns:
            cached = self.patterns[pattern_key]
            
            # Build SQL from template with current params
            sql = cached['sql_template']
            
            # Substitute parameters - DON'T add quotes, template already has them
            for param, value in signature['params'].items():
                placeholder = f'{{{param}}}'
                if placeholder in sql:
                    sql = sql.replace(placeholder, str(value))
            
            logger.warning(f"[SQL-CACHE] Pattern hit! Key={pattern_key}, successes={cached.get('success_count', 0)}")
            
            return {
                'sql': sql,
                'pattern_key': pattern_key,
                'confidence': cached.get('confidence', 0.9),
                'success_count': cached.get('success_count', 0),
                'source': 'pattern_cache'
            }
        
        logger.warning(f"[SQL-CACHE] No pattern match for key={pattern_key}")
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
        logger.warning(f"[SQL-CACHE] Learned pattern {pattern_key}, total successes: {self.patterns[pattern_key]['success_count']}")
    
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
    Generate bootstrap SQL patterns based on actual schema AND data values.
    
    Uses LLM to interpret what values mean - no hardcoding.
    """
    patterns = {}
    
    # Helper to generate consistent pattern keys
    def make_key(intent, entities, filters):
        sig_key = f"{intent}|{','.join(sorted(entities))}|{','.join(sorted(filters))}"
        return hashlib.md5(sig_key.encode()).hexdigest()[:12]
    
    # Find key tables
    tables = schema.get('tables', [])
    company_table = None
    personal_table = None
    
    for t in tables:
        name = t.get('table_name', '').lower()
        if 'company' in name and 'master' not in name and 'tax' not in name:
            company_table = t.get('table_name')
        if 'personal' in name:
            personal_table = t.get('table_name')
    
    if not company_table or not personal_table:
        return patterns
    
    # Find key columns
    def get_columns_for_table(table_name):
        for t in tables:
            if t.get('table_name') == table_name:
                cols = t.get('columns', [])
                if cols and isinstance(cols[0], dict):
                    return [str(c.get('name', c)).lower() for c in cols]
                else:
                    return [str(c).lower() for c in cols]
        return []
    
    company_cols = get_columns_for_table(company_table)
    personal_cols = get_columns_for_table(personal_table)
    
    rate_col = next((c for c in company_cols if 'hourly' in c and 'rate' in c), 'hourly_pay_rate')
    ptft_col = next((c for c in personal_cols if 'fullpart' in c or 'part_time' in c), 'fullpart_time_code')
    emp_num_col = 'employee_number'
    
    # INTELLIGENT: Query actual values and use LLM to interpret them
    pt_value = None
    ft_value = None
    
    try:
        from utils.structured_data_handler import get_structured_handler
        handler = get_structured_handler()
        
        # Get distinct values
        distinct_query = f'SELECT DISTINCT "{ptft_col}" FROM "{personal_table}" LIMIT 20'
        rows, cols = handler.execute_query(distinct_query)
        
        if rows:
            values = [str(r.get(ptft_col, '')).strip() for r in rows if r.get(ptft_col)]
            logger.warning(f"[SQL-CACHE] Found PT/FT values in data: {values}")
            
            if values:
                values_upper = [v.upper() for v in values]
                
                # FAST PATH: Common obvious patterns - no LLM needed
                # Industry standard: P=Part-time, F=Full-time
                if 'P' in values_upper and 'F' in values_upper:
                    pt_value = next(v for v in values if v.upper() == 'P')
                    ft_value = next(v for v in values if v.upper() == 'F')
                    logger.warning(f"[SQL-CACHE] Fast match (P/F): PT='{pt_value}', FT='{ft_value}'")
                elif 'PT' in values_upper and 'FT' in values_upper:
                    pt_value = next(v for v in values if v.upper() == 'PT')
                    ft_value = next(v for v in values if v.upper() == 'FT')
                    logger.warning(f"[SQL-CACHE] Fast match (PT/FT): PT='{pt_value}', FT='{ft_value}'")
                elif any('PART' in v.upper() for v in values) and any('FULL' in v.upper() for v in values):
                    pt_value = next(v for v in values if 'PART' in v.upper())
                    ft_value = next(v for v in values if 'FULL' in v.upper())
                    logger.warning(f"[SQL-CACHE] Fast match (Part/Full): PT='{pt_value}', FT='{ft_value}'")
                else:
                    # SLOW PATH: Use LLM for ambiguous values
                    try:
                        import httpx
                        import os
                        
                        prompt = f"""Column "{ptft_col}" contains these distinct values: {values}

Which value represents PART-TIME employees and which represents FULL-TIME employees?

Reply with ONLY two lines, nothing else:
PT_VALUE: <exact value>
FT_VALUE: <exact value>"""
                        
                        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
                        
                        response = httpx.post(
                            f"{ollama_host}/api/generate",
                            json={
                                "model": "mistral",
                                "prompt": prompt,
                                "stream": False,
                                "options": {"num_predict": 50}
                            },
                            timeout=30.0
                        )
                        
                        if response.status_code == 200:
                            result = response.json().get("response", "")
                            for line in result.strip().split('\n'):
                                line_upper = line.upper().strip()
                                if line_upper.startswith('PT_VALUE:'):
                                    pt_value = line.split(':', 1)[1].strip()
                                elif line_upper.startswith('FT_VALUE:'):
                                    ft_value = line.split(':', 1)[1].strip()
                            logger.warning(f"[SQL-CACHE] LLM interpreted: PT='{pt_value}', FT='{ft_value}'")
                    except Exception as llm_e:
                        logger.warning(f"[SQL-CACHE] LLM interpretation failed: {llm_e}")
    except Exception as e:
        logger.warning(f"[SQL-CACHE] Could not query PT/FT values: {e}")
    
    # Always create basic pattern
    key_count_all = make_key('count', ['employees'], [])
    patterns[key_count_all] = {
        'sql_template': f'SELECT COUNT(*) as count FROM "{personal_table}"',
        'signature': {'intent': 'count', 'entities': ['employees'], 'filters': [], 'key': key_count_all},
        'success_count': 10,
        'confidence': 0.98,
        'created': datetime.now().isoformat(),
        'example_question': 'How many employees are there?'
    }
    
    # List employees with high rate (doesn't need PT/FT)
    key_list = make_key('list', ['employees'], ['rate_gt'])
    patterns[key_list] = {
        'sql_template': f'''SELECT p."{emp_num_col}", DECRYPT(c."{rate_col}") as pay_rate
FROM "{company_table}" c
JOIN "{personal_table}" p ON c."{emp_num_col}" = p."{emp_num_col}"
WHERE DECRYPT_FLOAT(c."{rate_col}") > {{rate_threshold}}
LIMIT 100''',
        'signature': {'intent': 'list', 'entities': ['employees'], 'filters': ['rate_gt'], 'key': key_list},
        'success_count': 5,
        'confidence': 0.90,
        'created': datetime.now().isoformat(),
        'example_question': 'List employees making over $40/hr'
    }
    
    # If we determined PT/FT values, create those patterns
    if pt_value and ft_value:
        # List PT employees with rates (the missing pattern!)
        key_list_pt = make_key('list', ['employees'], ['pt_status'])
        patterns[key_list_pt] = {
            'sql_template': f'''SELECT p."{emp_num_col}", p."{ptft_col}", DECRYPT(c."{rate_col}") as pay_rate
FROM "{company_table}" c
JOIN "{personal_table}" p ON c."{emp_num_col}" = p."{emp_num_col}"
WHERE p."{ptft_col}" = '{pt_value}'
LIMIT 100''',
            'signature': {'intent': 'list', 'entities': ['employees'], 'filters': ['pt_status'], 'key': key_list_pt},
            'success_count': 10,
            'confidence': 0.95,
            'created': datetime.now().isoformat(),
            'example_question': 'Show me part-time employees with their rates'
        }
        
        # List PT employees with rate threshold
        key_list_pt_rate = make_key('list', ['employees'], ['pt_status', 'rate_gt'])
        patterns[key_list_pt_rate] = {
            'sql_template': f'''SELECT p."{emp_num_col}", p."{ptft_col}", DECRYPT(c."{rate_col}") as pay_rate
FROM "{company_table}" c
JOIN "{personal_table}" p ON c."{emp_num_col}" = p."{emp_num_col}"
WHERE p."{ptft_col}" = '{pt_value}'
AND DECRYPT_FLOAT(c."{rate_col}") > {{rate_threshold}}
LIMIT 100''',
            'signature': {'intent': 'list', 'entities': ['employees'], 'filters': ['pt_status', 'rate_gt'], 'key': key_list_pt_rate},
            'success_count': 10,
            'confidence': 0.95,
            'created': datetime.now().isoformat(),
            'example_question': 'Show me PT employees making over $40/hr'
        }
        
        # Count PT employees with rate threshold
        key1 = make_key('count', ['employees'], ['pt_status', 'rate_gt'])
        patterns[key1] = {
            'sql_template': f'''SELECT COUNT(*) as count
FROM "{company_table}" c
JOIN "{personal_table}" p ON c."{emp_num_col}" = p."{emp_num_col}"
WHERE DECRYPT_FLOAT(c."{rate_col}") > {{rate_threshold}}
AND p."{ptft_col}" = '{pt_value}' ''',
            'signature': {'intent': 'count', 'entities': ['employees'], 'filters': ['pt_status', 'rate_gt'], 'key': key1},
            'success_count': 10,
            'confidence': 0.95,
            'created': datetime.now().isoformat(),
            'example_question': 'How many PT employees make over $35/hr?'
        }
        
        # Count FT employees with rate threshold  
        key2 = make_key('count', ['employees'], ['ft_status', 'rate_gt'])
        patterns[key2] = {
            'sql_template': f'''SELECT COUNT(*) as count
FROM "{company_table}" c
JOIN "{personal_table}" p ON c."{emp_num_col}" = p."{emp_num_col}"
WHERE DECRYPT_FLOAT(c."{rate_col}") > {{rate_threshold}}
AND p."{ptft_col}" = '{ft_value}' ''',
            'signature': {'intent': 'count', 'entities': ['employees'], 'filters': ['ft_status', 'rate_gt'], 'key': key2},
            'success_count': 10,
            'confidence': 0.95,
            'created': datetime.now().isoformat(),
            'example_question': 'How many FT employees make over $50/hr?'
        }
        
        # Count PT employees (no rate filter)
        key4 = make_key('count', ['employees'], ['pt_status'])
        patterns[key4] = {
            'sql_template': f'''SELECT COUNT(*) as count FROM "{personal_table}" WHERE "{ptft_col}" = '{pt_value}' ''',
            'signature': {'intent': 'count', 'entities': ['employees'], 'filters': ['pt_status'], 'key': key4},
            'success_count': 10,
            'confidence': 0.95,
            'created': datetime.now().isoformat(),
            'example_question': 'How many part-time employees?'
        }
    else:
        logger.warning(f"[SQL-CACHE] Could not determine PT/FT values, skipping employment type patterns")
    
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
    
    # Check if we need to regenerate
    needs_regenerate = len(cache.patterns) == 0
    
    if not needs_regenerate and cache.patterns:
        # Check if patterns use old format (without DECRYPT)
        for pattern in cache.patterns.values():
            sql = pattern.get('sql_template', '')
            if 'ILIKE' in sql or '{employment_type}' in sql:
                logger.warning(f"[SQL-CACHE] Old pattern format detected (ILIKE), regenerating")
                cache.patterns = {}
                needs_regenerate = True
                break
            # Check for TRY_CAST instead of DECRYPT_FLOAT (need to upgrade)
            if 'TRY_CAST' in sql and 'rate' in sql.lower():
                logger.warning(f"[SQL-CACHE] Old pattern format detected (TRY_CAST), upgrading to DECRYPT")
                cache.patterns = {}
                needs_regenerate = True
                break
        
        # Regenerate if missing key patterns (should have 7+ now)
        if not needs_regenerate and len(cache.patterns) < 7:
            logger.warning(f"[SQL-CACHE] Only {len(cache.patterns)} patterns (expecting 7+), regenerating")
            cache.patterns = {}
            needs_regenerate = True
    
    if needs_regenerate:
        bootstrap = get_bootstrap_patterns(project, schema)
        cache.patterns.update(bootstrap)
        cache._save_cache()
        logger.warning(f"[SQL-CACHE] Bootstrapped {len(bootstrap)} patterns for {project}")
    
    return cache
