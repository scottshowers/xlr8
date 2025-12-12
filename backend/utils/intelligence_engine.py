"""
XLR8 INTELLIGENCE ENGINE v4.9
============================

Deploy to: backend/utils/intelligence_engine.py

DOMAIN-AGNOSTIC: No hardcoded business logic.
All domain knowledge comes from:
- Column profiles (actual data values)
- Learning module (patterns from past usage)
- Uploaded standards documents

v4.9 CHANGES:
- Fixed ARE bug: Common English words no longer detected as filter codes
- Added COMMON_ENGLISH_BLOCKLIST (language-level, not domain-specific)
- Word boundary matching for filter detection
- REMOVED all hardcoded domain patterns (states, status codes, pay types, etc.)
"""

import os
import re
import json
import logging
import requests
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

# LOAD VERIFICATION
logger.warning("[INTELLIGENCE_ENGINE] ====== v4.9 DOMAIN-AGNOSTIC + ARE BUG FIX ======")


# =============================================================================
# COMMON ENGLISH WORDS BLOCKLIST
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
    'all', 'each', 'every', 'both', 'many', 'much', 'more', 'most', 'some',
    
    # Question words
    'who', 'what', 'when', 'where', 'why', 'how', 'which',
    
    # Pronouns  
    'you', 'your', 'they', 'them', 'their', 'she', 'her', 'hers', 'we', 'us',
    
    # Prepositions
    'for', 'from', 'with', 'into', 'over', 'under', 'after', 'before', 'by', 'at', 'in', 'on', 'to',
    
    # Articles and conjunctions
    'the', 'and', 'but', 'yet', 'nor', 'for', 'so', 'or',
    
    # Common query words
    'total', 'count', 'list', 'show', 'find', 'give', 'tell', 'need',
    'only', 'just', 'also', 'even', 'still', 'again', 'then', 'than',
    'first', 'last', 'next', 'this', 'that', 'these', 'those',
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Truth:
    """A piece of information from one source of truth."""
    source_type: str
    source_name: str
    content: Any
    confidence: float
    location: str


@dataclass  
class Conflict:
    """A detected conflict between sources of truth."""
    description: str
    reality: Optional[Truth] = None
    intent: Optional[Truth] = None
    best_practice: Optional[Truth] = None
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
class SynthesizedAnswer:
    """A complete answer synthesized from all sources."""
    question: str
    answer: str
    confidence: float
    from_reality: List[Truth] = field(default_factory=list)
    from_intent: List[Truth] = field(default_factory=list)
    from_best_practice: List[Truth] = field(default_factory=list)
    conflicts: List[Conflict] = field(default_factory=list)
    insights: List[Insight] = field(default_factory=list)
    structured_output: Optional[Dict] = None
    reasoning: List[str] = field(default_factory=list)
    executed_sql: Optional[str] = None


@dataclass
class ClarificationNeeded:
    """Represents a clarification question to ask the user."""
    question: str
    options: List[Dict[str, Any]]
    reason: str
    category: str = ""
    column: str = ""


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _is_word_boundary_match(text: str, word: str) -> bool:
    """
    Check if word appears in text with word boundaries (not as substring).
    
    Examples:
        "how many employees are there" contains word "are" -> True
        "compare the data" contains word "are" -> False (part of "compare")
    """
    pattern = r'\b' + re.escape(word) + r'\b'
    return bool(re.search(pattern, text, re.IGNORECASE))


def _is_blocklisted(word: str) -> bool:
    """Check if word is in the common English blocklist."""
    return word.lower() in COMMON_ENGLISH_BLOCKLIST


# =============================================================================
# INTELLIGENCE ENGINE CLASS
# =============================================================================

class IntelligenceEngine:
    """
    Universal Analysis Engine - Domain Agnostic
    
    Understands data structure, relationships, and quality issues.
    Does NOT hardcode domain-specific logic. All domain knowledge comes from:
    - Column profiles (actual data values)
    - Learning module (patterns from past usage)
    - Uploaded standards documents
    """
    
    def __init__(self, project: str, db_handler=None, rag_handler=None, learning_module=None):
        self.project = project
        self.db_handler = db_handler
        self.rag_handler = rag_handler
        self.learning_module = learning_module
        
        # Filter intelligence from column profiles
        self.filter_candidates: Dict[str, List[Dict]] = {}
        
        # Cache for schema info
        self._schema_cache: Dict[str, Any] = {}
        self._table_cache: List[str] = []
        
        logger.info(f"[INTELLIGENCE] Initialized for project: {project}")
    
    def load_filter_candidates(self, candidates: Dict[str, List[Dict]]):
        """Load filter candidates from column profiles (Phase 2)."""
        self.filter_candidates = candidates
        logger.info(f"[INTELLIGENCE] Loaded filter candidates: {list(candidates.keys())}")
    
    def _detect_filter_in_question(self, q_lower: str, category: str, candidates: List[Dict]) -> Optional[str]:
        """
        Check if user specified a filter value in their question.
        Returns the detected value or None.
        
        DOMAIN-AGNOSTIC: Detection is based purely on:
        1. Actual values from column profiles
        2. Word boundary matching (not substring)
        3. Common English blocklist filtering
        
        No hardcoded business patterns.
        """
        if not candidates:
            return None
        
        # Check if any value from the data appears in the question
        for candidate in candidates:
            values = candidate.get('values', [])
            
            for value in values:
                value_str = str(value).strip()
                value_lower = value_str.lower()
                
                # Skip very short values (1-2 chars) - too many false positives
                if len(value_str) <= 2:
                    continue
                
                # Skip blocklisted common English words
                if _is_blocklisted(value_lower):
                    logger.debug(f"[FILTER-DETECT] Skipping blocklisted word: {value_str}")
                    continue
                
                # Check for word boundary match (not substring)
                if _is_word_boundary_match(q_lower, value_lower):
                    logger.warning(f"[FILTER-DETECT] Found {category} value '{value}' in question (word boundary match)")
                    return value
        
        return None
    
    def _is_filter_relevant(self, category: str, q_lower: str, candidates: List[Dict]) -> bool:
        """
        Determine if a filter category is relevant to this question.
        Returns True if we should ASK about this filter.
        
        DOMAIN-AGNOSTIC logic:
        - Check if user explicitly asks for breakdown by this category
        - Check if question mentions the category name
        - Use learning module for patterns (if available)
        """
        # Check if asking for breakdown by this category
        breakdown_patterns = [
            f'by {category}', f'per {category}', f'each {category}',
            f'breakdown by {category}', f'group by {category}',
            f'for each {category}', f'which {category}'
        ]
        
        if any(pattern in q_lower for pattern in breakdown_patterns):
            return True
        
        # Check learning module for patterns (if available)
        if self.learning_module:
            learned_relevance = self.learning_module.is_filter_relevant(category, q_lower)
            if learned_relevance is not None:
                return learned_relevance
        
        # Default: only ask if multiple distinct values exist and it's a "totals" question
        if candidates:
            distinct_count = len(candidates[0].get('values', []))
            is_totals_question = any(w in q_lower for w in ['total', 'count', 'how many', 'number of'])
            
            # If many distinct values and asking for totals, might need clarification
            if distinct_count > 1 and distinct_count <= 20 and is_totals_question:
                return True
        
        return False
    
    def analyze_question(self, question: str) -> Dict[str, Any]:
        """
        Analyze a question and determine:
        1. What filters to auto-apply (detected in question)
        2. What clarification to ask (if any)
        3. What type of query this is
        
        Returns analysis dict with detected_filters, needs_clarification, etc.
        """
        q_lower = question.lower().strip()
        
        result = {
            'question': question,
            'detected_filters': {},
            'needs_clarification': False,
            'clarification': None,
            'query_type': 'general',
            'reasoning': []
        }
        
        # Detect query type
        if any(w in q_lower for w in ['how many', 'count', 'total', 'number of']):
            result['query_type'] = 'count'
        elif any(w in q_lower for w in ['list', 'show', 'who', 'which']):
            result['query_type'] = 'list'
        elif any(w in q_lower for w in ['average', 'mean', 'sum', 'min', 'max']):
            result['query_type'] = 'aggregate'
        
        # Check each filter category
        for category, candidates in self.filter_candidates.items():
            if not candidates:
                continue
            
            # Try to detect filter value in question
            detected = self._detect_filter_in_question(q_lower, category, candidates)
            
            if detected:
                result['detected_filters'][category] = {
                    'value': detected,
                    'source': 'auto_detected'
                }
                result['reasoning'].append(f"Auto-detected {category}='{detected}' in question")
            elif self._is_filter_relevant(category, q_lower, candidates):
                # Need to ask clarification
                if not result['needs_clarification']:
                    result['needs_clarification'] = True
                    result['clarification'] = self._build_clarification(category, candidates)
                    result['reasoning'].append(f"Need clarification for {category}")
        
        return result
    
    def _build_clarification(self, category: str, candidates: List[Dict]) -> ClarificationNeeded:
        """
        Build a clarification question for a filter category.
        Options come from actual data values - no hardcoded options.
        """
        options = []
        column_name = ""
        
        # Build from actual data values
        for candidate in candidates[:1]:  # Use first candidate column
            column_name = candidate.get('column', '')
            values = candidate.get('values', [])
            distribution = candidate.get('distribution', {})
            
            for value in values[:15]:  # Limit to 15 options
                count = distribution.get(str(value), 0)
                options.append({
                    'value': value,
                    'label': str(value),
                    'count': count
                })
            
            # Add "All" option
            total = sum(distribution.values()) if distribution else 0
            options.append({
                'value': 'ALL',
                'label': f'All (no filter)',
                'count': total
            })
        
        # Generate question text
        question = f"Which {category} would you like to filter by?"
        if column_name:
            question = f"Filter by {column_name}?"
        
        return ClarificationNeeded(
            question=question,
            options=options,
            reason=f"Multiple {category} values available in data",
            category=category,
            column=column_name
        )
    
    def apply_filter(self, category: str, value: str) -> Dict[str, Any]:
        """
        Apply a filter value for a category.
        Returns the SQL WHERE clause component.
        """
        candidates = self.filter_candidates.get(category, [])
        if not candidates:
            return {'success': False, 'error': f'No filter candidates for {category}'}
        
        # Find the column for this category
        column = candidates[0].get('column', '')
        if not column:
            return {'success': False, 'error': f'No column found for {category}'}
        
        if value == 'ALL':
            return {
                'success': True,
                'where_clause': None,  # No filter
                'description': f'All {category}s (no filter)'
            }
        
        return {
            'success': True,
            'where_clause': f"{column} = '{value}'",
            'description': f'{category} = {value}'
        }
    
    def get_schema_context(self) -> str:
        """Get schema context for SQL generation."""
        if not self.db_handler:
            return ""
        
        tables = self.db_handler.list_tables(self.project)
        
        context_parts = []
        for table_info in tables:
            table_name = table_info.get('table_name', '')
            columns = table_info.get('columns', [])
            
            col_strs = []
            for col in columns:
                if isinstance(col, dict):
                    col_strs.append(f"{col.get('name', '')} ({col.get('type', 'VARCHAR')})")
                else:
                    col_strs.append(str(col))
            
            context_parts.append(f"Table: {table_name}\nColumns: {', '.join(col_strs)}")
        
        return "\n\n".join(context_parts)
    
    def generate_sql(self, question: str, filters: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Generate SQL for a question using LLM.
        Applies any filters that were detected or specified.
        """
        schema_context = self.get_schema_context()
        
        # Build filter context
        filter_clauses = []
        if filters:
            for category, value in filters.items():
                if value != 'ALL':
                    result = self.apply_filter(category, value)
                    if result.get('where_clause'):
                        filter_clauses.append(result['where_clause'])
        
        filter_context = ""
        if filter_clauses:
            filter_context = f"\n\nRequired filters (MUST be in WHERE clause):\n" + "\n".join(f"- {f}" for f in filter_clauses)
        
        # Build prompt for LLM
        prompt = f"""Generate a SQL query for DuckDB to answer this question:
Question: {question}

Available tables and columns:
{schema_context}
{filter_context}

Rules:
1. Return ONLY the SQL query, no explanation
2. Use proper DuckDB syntax
3. Include all required filters in WHERE clause
4. For counts, use COUNT(*)
5. For lists, LIMIT to 100 rows

SQL:"""
        
        # Call LLM (DeepSeek or fallback)
        sql = self._call_llm_for_sql(prompt)
        
        return {
            'sql': sql,
            'filters_applied': filters or {},
            'prompt_used': prompt
        }
    
    def _call_llm_for_sql(self, prompt: str) -> str:
        """Call local LLM (DeepSeek) for SQL generation."""
        ollama_url = os.environ.get('OLLAMA_API_URL', 'http://localhost:11434')
        
        try:
            response = requests.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": "deepseek-coder-v2:16b",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 500
                    }
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                sql = result.get('response', '').strip()
                # Clean up SQL
                sql = sql.replace('```sql', '').replace('```', '').strip()
                return sql
            else:
                logger.error(f"Ollama error: {response.status_code}")
                return ""
                
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return ""
    
    def execute_query(self, sql: str) -> Dict[str, Any]:
        """Execute a SQL query and return results."""
        if not self.db_handler:
            return {'success': False, 'error': 'No database handler'}
        
        try:
            df = self.db_handler.query_to_dataframe(sql)
            
            return {
                'success': True,
                'data': df.to_dict('records'),
                'columns': list(df.columns),
                'row_count': len(df),
                'sql': sql
            }
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'sql': sql
            }
    
    def answer_question(self, question: str, context: Dict = None) -> SynthesizedAnswer:
        """
        Main entry point: Answer a question using all available intelligence.
        
        Flow:
        1. Analyze question for filters
        2. Check if clarification needed
        3. Generate and execute SQL
        4. Synthesize answer
        """
        context = context or {}
        
        # Analyze the question
        analysis = self.analyze_question(question)
        
        # If clarification needed and not provided, return with clarification
        if analysis['needs_clarification'] and 'clarification_response' not in context:
            return SynthesizedAnswer(
                question=question,
                answer="",
                confidence=0.0,
                reasoning=analysis['reasoning'],
                structured_output={
                    'needs_clarification': True,
                    'clarification': analysis['clarification'].__dict__ if analysis['clarification'] else None
                }
            )
        
        # Apply filters (detected + from clarification response)
        filters = analysis['detected_filters'].copy()
        if 'clarification_response' in context:
            # Merge in clarification responses
            for cat, val in context['clarification_response'].items():
                filters[cat] = {'value': val, 'source': 'user_response'}
        
        # Generate SQL
        filter_values = {k: v['value'] for k, v in filters.items()}
        sql_result = self.generate_sql(question, filter_values)
        
        if not sql_result.get('sql'):
            return SynthesizedAnswer(
                question=question,
                answer="I couldn't generate a query for this question.",
                confidence=0.3,
                reasoning=["SQL generation failed"]
            )
        
        # Execute query
        query_result = self.execute_query(sql_result['sql'])
        
        if not query_result.get('success'):
            return SynthesizedAnswer(
                question=question,
                answer=f"Query failed: {query_result.get('error', 'Unknown error')}",
                confidence=0.2,
                reasoning=[f"Query execution failed: {query_result.get('error')}"],
                executed_sql=sql_result['sql']
            )
        
        # Synthesize answer
        answer = self._synthesize_answer(question, query_result, filters)
        answer.executed_sql = sql_result['sql']
        answer.reasoning = analysis['reasoning']
        
        return answer
    
    def _synthesize_answer(self, question: str, query_result: Dict, filters: Dict) -> SynthesizedAnswer:
        """Synthesize a human-readable answer from query results."""
        data = query_result.get('data', [])
        row_count = query_result.get('row_count', 0)
        columns = query_result.get('columns', [])
        
        # Build filter description
        filter_desc = ""
        if filters:
            filter_parts = []
            for cat, info in filters.items():
                val = info.get('value', info) if isinstance(info, dict) else info
                if val != 'ALL':
                    filter_parts.append(f"{cat}={val}")
            if filter_parts:
                filter_desc = f" (filtered by {', '.join(filter_parts)})"
        
        # Generate answer based on query type
        q_lower = question.lower()
        
        if 'count' in columns or any(w in q_lower for w in ['how many', 'count', 'total']):
            # Count query
            if data and len(data) > 0:
                count_val = data[0].get('count', data[0].get(columns[0], 'Unknown'))
                answer = f"There are {count_val} records{filter_desc}."
            else:
                answer = f"No records found{filter_desc}."
        elif row_count == 0:
            answer = f"No results found{filter_desc}."
        elif row_count == 1:
            answer = f"Found 1 result{filter_desc}: {data[0]}"
        else:
            answer = f"Found {row_count} results{filter_desc}."
            if row_count <= 10:
                answer += f"\n\nResults:\n" + "\n".join(str(r) for r in data)
        
        return SynthesizedAnswer(
            question=question,
            answer=answer,
            confidence=0.85,
            structured_output={
                'data': data,
                'row_count': row_count,
                'columns': columns,
                'filters': filters
            }
        )


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def get_intelligence_engine(project: str, db_handler=None, rag_handler=None, 
                           learning_module=None) -> IntelligenceEngine:
    """Factory function to create an IntelligenceEngine instance."""
    return IntelligenceEngine(
        project=project,
        db_handler=db_handler,
        rag_handler=rag_handler,
        learning_module=learning_module
    )
